"""Audit collected raw native ranks against provisional scoring-table selections.

Never reads correctness values. A missing true-top CIF is acquisition missingness,
NOT a pose failure and NOT permission to select the best remaining scored pose.
Run again after the main stream ends; partial checkpoints are not final coverage.
"""
from collections import defaultdict
import hashlib
import csv
import io
import os
from contextlib import ExitStack
from itertools import chain
import json
from pathlib import Path,PurePosixPath
import re
from collect_openbind import rank_native
from storage import guard

BASE=Path(__file__).resolve().parent

def pose_identity(relative):
    parts=PurePosixPath(relative).parts
    seeds=re.findall(r'seed[_-]?(\d+)',relative,re.I)
    samples=re.findall(r'(?:sample|model)[_-]?(\d+)',relative,re.I)
    if not seeds and len(parts)>1 and parts[0].isdigit():seeds=[parts[0]]
    if len(set(seeds))!=1 or len(set(samples))!=1:return None
    return str(int(seeds[0])),str(int(samples[0]))

def main():
    guard(20_000_000)
    source=BASE/'manifests/selected_coordinate_inventory.jsonl'
    candidates={r['system_id']:r for r in map(json.loads,(BASE/'manifests/candidates.jsonl').read_text().splitlines())}
    confidence=defaultdict(dict)
    coordinates=defaultdict(dict)
    ranking_sources=defaultdict(set)
    errors=[]
    if source.exists():
        with ExitStack() as stack:
            inventories=[source,BASE/'manifests/rnp_recovery_inventory.jsonl']
            stream=chain.from_iterable(stack.enter_context(p.open(encoding='utf-8')) for p in inventories if p.exists())
            for line in stream:
                if not line.endswith('\n'):continue
                row=json.loads(line)
                if row.get('status')!='saved' or not row.get('local_path'):continue
                path=BASE/row['local_path']
                if not path.resolve().is_relative_to((BASE/'data/rnp/selected_coordinates').resolve()):raise ValueError('Collected coordinate path escaped declared root')
                parts=PurePosixPath(row['archive_member']).parts
                start=parts.index('prediction_files')
                relative='/'.join(parts[start+3:])
                key=(row['model'],row['system_id'])
                if path.suffix.lower()=='.csv' and path.name.endswith('_ranking_scores.csv'):
                    raw=path.read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Raw ranking CSV changed since acquisition')
                    table=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
                    if set(table.fieldnames or [])!={'seed','sample','ranking_score'}:raise ValueError('Unexpected ranking CSV schema; inspect header without reading outcome columns')
                    for item in table:
                        identity=(str(int(item['seed'])),str(int(item['sample'])))
                        score=float(item['ranking_score'])
                        payload={'ranking_score' if row['model']=='protenix' else 'confidence_score':score}
                        if identity in confidence[key] and confidence[key][identity]!=payload:raise ValueError('Raw ranking sources disagree')
                        confidence[key][identity]=payload
                    ranking_sources[key].add('raw_prediction_ranking_scores.csv; SHA256 verified')
                    continue
                identity=pose_identity(relative)
                if identity is None:continue  # ranking CSV/non-pose metadata logged separately by collector
                if path.suffix.lower() in ('.cif','.pdb'):
                    if identity in coordinates[key]:raise ValueError('Ambiguous duplicate coordinate for native sample')
                    coordinates[key][identity]=row
                elif path.suffix.lower()=='.json' and ('summary_confidence' in path.name or 'confidence_input_model_' in path.name):
                    if path.stat().st_size>1_000_000:raise ValueError('Collected confidence exceeded declared budget')
                    raw=path.read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Collected confidence changed since acquisition')
                    payload=json.loads(raw)
                    if identity in confidence[key]:raise ValueError('Duplicate raw confidence sample')
                    confidence[key][identity]=payload
                    ranking_sources[key].add('raw_summary_confidence_json; SHA256 verified')
    output=[]
    counts=defaultdict(int)
    for target,candidate in sorted(candidates.items()):
        for model in ('protenix','boltz2'):
            key=(model,target)
            conf=confidence.get(key,{})
            record={'system_id':target,'model':model,'raw_native_ranking_samples':len(conf),'held_out_outcomes_examined':False}
            record['raw_native_ranking_sources']=sorted(ranking_sources.get(key,set()))
            record['full_raw_confidence_fields_available']=any('summary_confidence_json' in source for source in record['raw_native_ranking_sources'])
            if not conf:record['status']='awaiting_raw_native_ranking'
            else:
                try:
                    selected=rank_native(model,[(seed,sample,payload) for (seed,sample),payload in conf.items()])
                    identity=(selected['seed'],selected['sample'])
                    provisional=candidate[model+'_selection']
                    match=identity==(str(int(float(provisional['seed']))),str(int(float(provisional['sample']))))
                    expected=(len(conf)==25 and len({seed for seed,sample in conf})==5 and all(
                        {sample for s,sample in conf if s==seed}==set(map(str,range(5))) for seed,sample in conf))
                    record.update(native_selection=selected,expected_5x5_raw_design_complete=expected,
                                  provisional_selection_agrees=match,true_native_coordinate_retained=identity in coordinates.get(key,{}))
                    if not expected:record['status']='partial_or_unexpected_raw_sample_design'
                    elif identity not in coordinates.get(key,{}):record['status']='true_native_coordinate_needs_reacquisition'
                    else:
                        coordinate=coordinates[key][identity]
                        path=BASE/coordinate['local_path']
                        if hashlib.sha256(path.read_bytes()).hexdigest()!=coordinate['sha256']:raise ValueError('Coordinate checksum changed')
                        record.update(status='raw_native_selection_verified',coordinate_path=coordinate['local_path'],coordinate_sha256=coordinate['sha256'])
                except Exception as e:record.update(status='raw_native_audit_error',error=f'{type(e).__name__}: {e}')
            counts[record['status']]+=1
            output.append(record)
    out=BASE/'manifests/rnp_native_reconciliation.jsonl'
    part=out.with_name(out.name+'.part')
    with part.open('w',encoding='utf-8') as handle:
        for row in output:handle.write(json.dumps(row)+'\n')
    os.replace(part,out)
    recovery=[{'system_id':r['system_id'],'model':r['model'],'selection':r['native_selection']} for r in output
              if r['status']=='true_native_coordinate_needs_reacquisition' and r.get('provisional_selection_agrees') is False]
    recovery_path=BASE/'manifests/rnp_recovery_requests.json'
    part=recovery_path.with_name(recovery_path.name+'.part')
    part.write_text(json.dumps(recovery,indent=2));os.replace(part,recovery_path)
    collection=json.loads((BASE/'manifests/coordinate_collection_status.json').read_text())
    summary={'model_system_pairs':len(output),'status_counts':dict(counts),'collection_status':collection['status'],
             'held_out_outcomes_examined':False,'final_coverage_audit':collection['status']=='completed_tar_stream',
             'warning':'A complete raw ranking audit does not verify model versions, chemical identity or final eligibility.'}
    (BASE/'manifests/rnp_native_reconciliation_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
