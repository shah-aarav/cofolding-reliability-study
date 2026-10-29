"""Diagnose acquisition-only errors without reading any reference outcomes."""
from collect_openbind import raw_groups,fetch_rows
from indexed_zip import member_window
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
failures=[json.loads(line) for line in (BASE/'manifests/openbind_collection_events.jsonl').read_text().splitlines() if '"status": "errors"' in line]
model='protenix'
target=next(row['target'] for row in failures if row['model']==model)
samples=raw_groups(model)[target]
for seed in sorted({key[0] for key in samples}):
    rows=[files['confidence'] for key,files in samples.items() if key[0]==seed]
    start,end=member_window(rows)
    try:
        members,network=fetch_rows(rows)
        print(json.dumps({'target':target,'seed':seed,'status':'range_and_member_checks_passed','members':len(members),'network_bytes':network}),flush=True)
    except Exception as e:
        print(json.dumps({'target':target,'seed':seed,'status':'error','start':start,'end':end,'error':repr(e)}),flush=True)
