"""Bounded second stream to recover ONLY independently audited missing native tops.

Necessary because scoring CSVs can omit the true native-top sample. No full
archive is stored; no experimental outcome is examined; primary stream remains
untouched. Requests update dynamically from the earlier-running first pass.
"""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import tarfile
import time
import urllib.request
from collect_coordinates import selected_pose
from storage import guard
from stream_inventory import BoundedReader,safe_member

BASE=Path(__file__).resolve().parent
CUTOFF=datetime(2026,10,27,13,tzinfo=timezone.utc).timestamp()

def main():
    guard(512_000_000)
    requests={}
    last_reload=0
    last_checkpoint=0
    saved=0
    retained=0
    visited=0
    last_member=None
    models_seen=set()
    reader=None
    state=BASE/'manifests/rnp_recovery_stream_status.json'
    url='https://zenodo.org/records/18366081/files/prediction_files.tar.gz?download=1'
    def checkpoint(status,error=None):
        row={'status':status,'members_visited':visited,'compressed_network_bytes':reader.bytes_read if reader else 0,
             'new_files_saved':saved,'retained_bytes_this_run':retained,'requested_missing_native_tops':len(requests),
             'model_roots_seen':sorted(models_seen),'last_member':last_member,'time_utc':datetime.now(timezone.utc).isoformat(),
             'error':error,'whole_archive_checksum_verified':False,'experimental_outcomes_examined':False}
        part=state.with_name(state.name+'.part');part.write_text(json.dumps(row,indent=2));os.replace(part,state)
        print(json.dumps(row),flush=True)
    try:
        with (urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ProteinLigandReliabilityResearch/0.1 native-top-recovery'}),timeout=90) as response,
              (BASE/'manifests/rnp_recovery_inventory.jsonl').open('a',encoding='utf-8') as inventory):
            reader=BoundedReader(response,40_000_000_000,max_seconds=max(1,CUTOFF-time.time()))
            with tarfile.open(fileobj=reader,mode='r|gz') as archive:
                for member in archive:
                    visited+=1
                    last_member=member.name
                    if time.time()>=CUTOFF:raise TimeoutError('Morning cutoff reached')
                    if time.monotonic()-last_reload>=60:
                        path=BASE/'manifests/rnp_recovery_requests.json'
                        if path.exists():requests={(r['model'],r['system_id']):r['selection'] for r in json.loads(path.read_text())}
                        primary=json.loads((BASE/'manifests/coordinate_collection_status.json').read_text())['status']
                        if not requests and primary!='running':
                            checkpoint('completed_current_recovery_requests');return
                        last_reload=time.monotonic()
                    if time.monotonic()-last_checkpoint>=60:
                        checkpoint('running');last_checkpoint=time.monotonic()
                    if not safe_member(member.name):raise ValueError('Unsafe TAR member')
                    parts=PurePosixPath(member.name).parts
                    if 'prediction_files' not in parts:continue
                    index=parts.index('prediction_files')
                    tail=parts[index+1:]
                    if tail:models_seen.add(tail[0])
                    if len(tail)<3 or not member.isfile():continue
                    model,target=tail[:2]
                    selection=requests.get((model,target))
                    relative='/'.join(tail[2:])
                    if not selection or PurePosixPath(relative).suffix.lower() not in ('.cif','.pdb') or not selected_pose(relative,selection):continue
                    if not 0<member.size<=25_000_000 or retained+member.size>512_000_000:raise RuntimeError('Recovery retained-file budget exceeded')
                    output=BASE/'data/rnp/selected_coordinates'/model/target
                    filename=hashlib.sha256(relative.encode()).hexdigest()[:16]+'_'+PurePosixPath(relative).name
                    destination=output/filename
                    if destination.exists():continue
                    guard(member.size+1_000_000);output.mkdir(parents=True,exist_ok=True)
                    part=destination.with_name(destination.name+'.part')
                    digest=hashlib.sha256();copied=0
                    with archive.extractfile(member) as source,part.open('wb') as sink:
                        for block in iter(lambda:source.read(1024*1024),b''):
                            copied+=len(block)
                            if copied>member.size:raise ValueError('Oversized recovery member')
                            digest.update(block);sink.write(block)
                    if copied!=member.size:raise ValueError('Truncated recovery member')
                    os.replace(part,destination)
                    record={'archive_member':member.name,'size':member.size,'model':model,'system_id':target,'selected_pose_match':True,
                            'metadata':False,'status':'saved','sha256':digest.hexdigest(),'local_path':str(destination.relative_to(BASE)),
                            'selection_source':'independent raw prediction ranking CSV; not experimental scoring availability'}
                    inventory.write(json.dumps(record)+'\n');inventory.flush()
                    retained+=copied;saved+=1
                    checkpoint('running')
            checkpoint('completed_tar_stream')
    except Exception as e:
        checkpoint('stopped_with_error',f'{type(e).__name__}: {e}')
        raise

if __name__=='__main__':main()
