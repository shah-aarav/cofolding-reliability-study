"""Full raw prediction inventory; uses paths and sizes, not confidence/outcome values."""
import json
import re
from collections import defaultdict
from pathlib import Path, PurePosixPath
from storage import guard

BASE=Path(__file__).resolve().parent

def run():
    guard(120_000_000)
    target_sets={}
    summaries={}
    for model in ('boltz2','protenix'):
        samples=defaultdict(dict)
        unresolved=0
        scope_counts=defaultdict(int)
        path=BASE/'manifests'/f'openbind_{model}_zip_inventory.jsonl'
        for line in path.open(encoding='utf-8'):
            row=json.loads(line)
            parts=PurePosixPath(row['name']).parts
            if 'results' not in parts:unresolved+=1;continue
            results_index=parts.index('results')
            target=parts[results_index+1]
            scope='/'.join(parts[:results_index])
            seed=re.search(r'(?:^|/)seed_(\d+)(?:/|$)',row['name'])
            sample=re.search(r'(?:model|sample)_(\d+)',parts[-1])
            if not seed or not sample:unresolved+=1;continue
            kind='confidence' if parts[-1].endswith('.json') else 'coordinates'
            key=(scope,target,seed.group(1),sample.group(1))
            if kind in samples[key]:raise ValueError(f'Duplicate raw {model} {kind} for {key}')
            samples[key][kind]=row
        paired={key for key,items in samples.items() if 'confidence' in items and 'coordinates' in items}
        main_scope='run_boltz2_monomer' if model=='boltz2' else 'run_protenix_monomer_no-pair'
        targets={key[1] for key in paired if key[0]==main_scope}
        for key in paired:scope_counts[key[0]]+=1
        target_sets[model]=targets
        out=BASE/'manifests'/f'openbind_{model}_samples.jsonl'
        with out.open('w',encoding='utf-8') as handle:
            for (scope,target,seed,sample),items in sorted(samples.items()):
                handle.write(json.dumps({'run_scope':scope,'primary_run_directory':scope==main_scope,'source_target_id':target,'seed':seed,'sample':sample,'raw_files':items,'status':'raw paired paths only; native-top ranking, chemistry and reference matching pending'})+'\n')
                if handle.tell()>60_000_000:raise RuntimeError('External sample manifest exceeded cap')
        summaries[model]={'unique_prediction_keys_including_run_scope':len(samples),'paired_coordinate_confidence_keys':len(paired),'paired_keys_by_run_scope':dict(scope_counts),'top_level_target_ids_with_paired_raw_outputs':len(targets),'unresolved_inventory_paths':unresolved,'manifest_bytes':out.stat().st_size}
    common=sorted(target_sets['boltz2']&target_sets['protenix'])
    summary={'models':summaries,'raw_target_intersection_count':len(common),'raw_target_ids':common,'final_eligible_complexes':None,'native_top_selection_verified':False,'accuracy_outcomes_examined':False,'note':'Raw output IDs are not proven independent compounds, reference structures, eligible complexes or matched predictor versions.'}
    (BASE/'manifests/openbind_cohort_audit.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='raw_target_ids'},indent=2))

if __name__=='__main__':run()
