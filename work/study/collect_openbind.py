"""Resumeable full-intersection native ranking from raw remote ZIP predictions.

Reads prediction-time confidence for all 25 samples, never experimental outcomes.
Retains the highest native-score pose and compact raw confidence/provenance only.
The default is the FULL raw 927-ID intersection, not a scientific pilot.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import threading
import time
from confidence import finite_number
from indexed_zip import member_window,WindowFile,read_indexed_member
from remote_zip import RangeFile
from storage import guard

BASE=Path(__file__).resolve().parent
OUTPUT=BASE/'data/openbind/native_top'
LOCK=threading.Lock()
CAP=1_500_000_000
CUTOFF=datetime(2026,10,27,13,tzinfo=timezone.utc).timestamp()

def raw_groups(model):
    groups=defaultdict(dict)
    scope='run_boltz2_monomer' if model=='boltz2' else 'run_protenix_monomer_no-pair'
    for line in (BASE/'manifests'/f'openbind_{model}_zip_inventory.jsonl').open(encoding='utf-8'):
        row=json.loads(line)
        parts=PurePosixPath(row['name']).parts
        if len(parts)<4 or parts[:2]!=(scope,'results'):continue
        target=parts[2]
        if not re.fullmatch(r'[A-Za-z0-9_.-]+',target):raise ValueError('Unsafe raw target ID')
        seed=re.search(r'/seed_(\d+)/',row['name'])
        sample=re.search(r'(?:model|sample)_(\d+)\.',parts[-1])
        if not seed or not sample:continue
        kind='confidence' if parts[-1].endswith('.json') else 'coordinates'
        key=(seed.group(1),sample.group(1))
        item=groups[target].setdefault(key,{})
        if kind in item:raise ValueError('Duplicate raw sample/kind in primary run')
        if 'header_offset' not in row:raise ValueError('Offset-enabled remote inventory required')
        item[kind]=row
    return dict(groups)

def rank_native(model,confidences):
    if model not in ('boltz2','protenix'):raise ValueError('Unsupported native predictor')
    key='confidence_score' if model=='boltz2' else 'ranking_score'
    ranked=[]
    for seed,sample,payload in confidences:
        score=finite_number(payload.get(key))
        if score is None:raise ValueError('Missing/nonfinite raw native ranking score')
        ranked.append((score,int(seed),int(sample),seed,sample))
    if not ranked:raise ValueError('No raw confidence samples')
    ranked.sort(key=lambda x:(-x[0],x[1],x[2]))
    best=ranked[0]
    return {'seed':best[3],'sample':best[4],'native_ranking_score':best[0],
            'tied_top_count':sum(x[0]==best[0] for x in ranked),
            'tie_policy':'ascending numeric seed, then ascending numeric sample; never geometry/outcome'}

def fetch_rows(rows,max_span=20_000_000):
    start,end=member_window(rows,max_span=max_span)
    first=rows[0]
    with RangeFile(first['archive_url'],first['archive_size'],max_network_bytes=max_span*3,max_read_bytes=max_span,max_attempts=3) as remote:
        remote.seek(start)
        data=remote.read(end-start)
        window=WindowFile(data,start,first['archive_size'])
        members={}
        for row in rows:
            value,proof=read_indexed_member(window,row)
            members[row['name']]=(value,proof)
    return members,remote.network_bytes

def collect_case(model,target,samples):
    if time.time()>=CUTOFF:raise TimeoutError('Morning cutoff reached')
    directory=OUTPUT/model
    meta_path=directory/(target+'.json')
    coordinate_path=directory/(target+'.cif')
    if meta_path.exists() and coordinate_path.exists():
        metadata=json.loads(meta_path.read_text())
        if hashlib.sha256(coordinate_path.read_bytes()).hexdigest()!=metadata['coordinate_integrity']['sha256']:
            raise ValueError('Existing native coordinate checksum mismatch')
        return {'model':model,'target':target,'status':'already_complete'}
    if len(samples)!=25 or len({seed for seed,sample in samples})!=5:
        raise ValueError('Raw candidate does not have expected 5-seed x5-sample design')
    by_seed=defaultdict(list)
    for (seed,sample),files in samples.items():
        if set(files)!= {'coordinates','confidence'}:raise ValueError('Unpaired raw confidence/coordinate files')
        by_seed[seed].append((sample,files['confidence']))
    confidences=[]
    provenance=[]
    network=0
    for seed,items in sorted(by_seed.items(),key=lambda x:int(x[0])):
        if {sample for sample,row in items}!=set(map(str,range(5))):raise ValueError('Incomplete seed sample indices')
        if time.time()>=CUTOFF:raise TimeoutError('Morning cutoff reached')
        members,transferred=fetch_rows([row for sample,row in items])
        network+=transferred
        for sample,row in items:
            raw,proof=members[row['name']]
            if len(raw)>1_000_000:raise ValueError('Confidence JSON exceeds cap')
            payload=json.loads(raw)
            if not isinstance(payload,dict):raise ValueError('Expected confidence object')
            confidences.append((seed,sample,payload))
            provenance.append({'seed':seed,'sample':sample,'member':row['name'],**proof})
    selected=rank_native(model,confidences)
    row=samples[(selected['seed'],selected['sample'])]['coordinates']
    members,transferred=fetch_rows([row])
    network+=transferred
    coordinates,proof=members[row['name']]
    metadata={'model':model,'source_target_id':target,'selection':selected,'raw_confidences':[
        {'seed':seed,'sample':sample,'confidence':payload} for seed,sample,payload in sorted(confidences,key=lambda r:(int(r[0]),int(r[1])))],
        'confidence_integrity':provenance,'coordinate_member':row,'coordinate_integrity':proof,
        'network_bytes_this_case':network,'acquired_utc':datetime.now(timezone.utc).isoformat(),
        'experimental_outcomes_examined':False,'chemical_eligibility_verified':False,
        'note':'Raw native global selection only. Input/chain identity and model-version compatibility still require verification.'}
    encoded=json.dumps(metadata,indent=2).encode()
    with LOCK:
        used=sum(p.stat().st_size for p in OUTPUT.rglob('*') if p.is_file()) if OUTPUT.exists() else 0
        if used+len(encoded)+len(coordinates)>CAP:raise RuntimeError('External retained-data budget exhausted')
        guard(len(encoded)+len(coordinates)+1_000_000)
        directory.mkdir(parents=True,exist_ok=True)
        for path,data in [(coordinate_path,coordinates),(meta_path,encoded)]:
            part=path.with_name(path.name+'.part')
            part.write_bytes(data)
            os.replace(part,path)
    return {'model':model,'target':target,'status':'saved','network_bytes':network,'coordinate_bytes':len(coordinates)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=3,choices=range(1,5))
    parser.add_argument('--limit',type=int,default=None,help='Implementation smoke checks only; omit for full cohort')
    args=parser.parse_args()
    guard(CAP)
    groups={model:raw_groups(model) for model in ('boltz2','protenix')}
    common=sorted(set(groups['boltz2'])&set(groups['protenix']))
    if args.limit is not None:common=common[:args.limit]
    tasks=[(model,target,groups[model][target]) for target in common for model in ('boltz2','protenix')]
    summary={'raw_target_intersection':len(set(groups['boltz2'])&set(groups['protenix'])),
             'tasks_requested':len(tasks),'finished':0,'saved':0,'already_complete':0,'errors':0,
             'network_bytes_saved_cases_this_run':0,'status':'running','outcomes_examined':False}
    ledger=BASE/'manifests/openbind_collection_events.jsonl'
    summary_path=BASE/'manifests/openbind_collection_status.json'
    with ThreadPoolExecutor(max_workers=args.workers) as executor,ledger.open('a',encoding='utf-8') as log:
        futures={executor.submit(collect_case,*task):task[:2] for task in tasks}
        for future in as_completed(futures):
            model,target=futures[future]
            try:result=future.result()
            except Exception as e:result={'model':model,'target':target,'status':'errors','error':f'{type(e).__name__}: {e}'}
            summary['finished']+=1
            summary[result['status']]+=1
            summary['network_bytes_saved_cases_this_run']+=result.get('network_bytes',0)
            result['time_utc']=datetime.now(timezone.utc).isoformat()
            log.write(json.dumps(result)+'\n');log.flush()
            summary['time_utc']=result['time_utc']
            part=summary_path.with_suffix('.json.part')
            part.write_text(json.dumps(summary,indent=2));os.replace(part,summary_path)
            print(json.dumps(result),flush=True)
            if time.time()>=CUTOFF:
                for pending in futures:pending.cancel()
                break
    summary['status']='finished_requested_tasks' if summary['finished']==len(tasks) else 'morning_cutoff'
    summary_path.write_text(json.dumps(summary,indent=2))

if __name__=='__main__':main()
