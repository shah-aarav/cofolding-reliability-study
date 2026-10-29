"""Retry a snapshot of logged acquisition failures, preserving full-run status."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import json
from pathlib import Path
from collect_openbind import raw_groups,collect_case

BASE=Path(__file__).resolve().parent

def main():
    events=BASE/'manifests/openbind_collection_events.jsonl'
    tasks=set()
    with events.open(encoding='utf-8') as stream:
        for line in stream:
            if not line.endswith('\n'):continue
            row=json.loads(line)
            if row['status']=='errors':tasks.add((row['model'],row['target']))
    groups={model:raw_groups(model) for model in {model for model,target in tasks}}
    with ThreadPoolExecutor(max_workers=2) as executor,(BASE/'manifests/openbind_retry_events.jsonl').open('a',encoding='utf-8') as log:
        futures={executor.submit(collect_case,model,target,groups[model][target]):(model,target) for model,target in sorted(tasks)}
        for future in as_completed(futures):
            model,target=futures[future]
            try:result=future.result()
            except Exception as e:result={'model':model,'target':target,'status':'errors','error':f'{type(e).__name__}: {e}'}
            result['time_utc']=datetime.now(timezone.utc).isoformat()
            log.write(json.dumps(result)+'\n');log.flush()
            print(json.dumps(result),flush=True)

if __name__=='__main__':main()
