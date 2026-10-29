"""Fetch explicit prediction-input/configuration members with member provenance.

This does not fetch reformatted ligand SDFs: source review showed that those can
have bond orders repaired using experimental chemical templates. Never execute
retrieved scripts or unpickle model-input mol caches.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
from collect_openbind import fetch_rows
from storage import guard

BASE=Path(__file__).resolve().parent

def fetch_selected(model,wanted):
    release=json.loads((BASE/'sources/openbind_record.json').read_text())
    name='zip_run_boltz2_monomer.zip' if model=='boltz2' else 'zip_run_protenix_monomer_no-pair.zip'
    entry=next(r for r in release['files'] if r['key']==name)
    rows=[]
    with gzip.open(BASE/'manifests'/f'openbind_{model}_full_zip_index.jsonl.gz','rt',encoding='utf-8') as stream:
        for line in stream:
            row=json.loads(line)
            if row['name'] in wanted:rows.append({**row,'archive_url':entry['links']['self'],'archive_size':entry['size'],
                                                'archive':name,'published_archive_checksum':entry.get('checksum')})
    if {r['name'] for r in rows}!=set(wanted):raise ValueError('Requested explicit input/configuration member missing')
    output=BASE/'data/input_provenance'/model
    output.mkdir(parents=True,exist_ok=True)
    for row in rows:
        filename=hashlib.sha256(row['name'].encode()).hexdigest()[:16]+'_'+Path(row['name']).name
        target=output/filename
        if target.exists():continue
        members,network=fetch_rows([row])
        data,proof=members[row['name']]
        guard(len(data)+1_000_000)
        part=target.with_name(target.name+'.part')
        part.write_bytes(data);os.replace(part,target)
        metadata={'member':row,'integrity':proof,'network_bytes':network,'local_path':str(target.relative_to(BASE)),
                  'used_as_instructions':False,'source_code_executed':False}
        target.with_name(target.name+'.provenance.json').write_text(json.dumps(metadata,indent=2))
        print(json.dumps({'model':model,'member':row['name'],'bytes':len(data),'local_path':str(target.relative_to(BASE))}),flush=True)

if __name__=='__main__':
    prefix='run_boltz2_monomer/results/A71EV2A-x0152a/seed_1370180479/boltz_results_A71EV2A-x0152a_inp/'
    fetch_selected('boltz2',[
        'run_boltz2_monomer/submit_boltz2.sh',prefix+'processed/records/A71EV2A-x0152a_inp.json',
        prefix+'processed/structures/A71EV2A-x0152a_inp.npz',prefix+'lightning_logs/version_0/hparams.yaml'])
