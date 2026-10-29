"""Stream full RNP coordinate archive; retain bounded candidate top poses/metadata only.

Uses conservative filename matching. Unmatched layouts remain unresolved rather than
selecting structures using experimental correctness. No tar.extract() is used.
"""
import hashlib
import json
import os
import re
import tarfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from storage import guard
from stream_inventory import BoundedReader, safe_member
from resilient_stream import ReconnectingStream

BASE=Path(__file__).resolve().parent
MAX_RETAINED=2_000_000_000
MAX_MEMBER=25_000_000
MODELS={'boltz2','protenix'}

def number(value):
    try: return str(int(float(value)))
    except (ValueError,TypeError,OverflowError): return str(value)

def selected_pose(relative, selection):
    seeds=re.findall(r'seed[_-]?(\d+)',relative,re.I)
    samples=re.findall(r'(?:sample|model)[_-]?(\d+)',relative,re.I)
    # Author extraction code uses {target}/{numeric_seed}/boltz_results_input/...
    # for Boltz, whereas Protenix spells out seed_N. Keep this constrained to
    # the FIRST directory under the verified system; do not match arbitrary digits.
    parts=PurePosixPath(relative).parts
    if not seeds and len(parts)>1 and parts[0].isdigit():
        seeds=[parts[0]]
    return bool(seeds and samples and number(selection['seed']) in seeds and number(selection['sample']) in samples)

def run(max_hours=12):
    if not 0<max_hours<=24:raise ValueError('Acquisition runtime must be bounded to 0..24 hours')
    guard(MAX_RETAINED+20_000_000)
    rows=[json.loads(line) for line in (BASE/'manifests/candidates.jsonl').read_text().splitlines()]
    candidates={row['system_id']:row for row in rows}
    reconciliation=BASE/'manifests/rnp_native_reconciliation.jsonl'
    if reconciliation.exists():
        for native in map(json.loads,reconciliation.read_text().splitlines()):
            if native.get('expected_5x5_raw_design_complete') and native.get('native_selection'):
                candidates[native['system_id']][native['model']+'_selection']=native['native_selection']
    output=BASE/'data/rnp/selected_coordinates'
    output.mkdir(parents=True,exist_ok=True)
    retained=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    cutoff=time.time()+max_hours*3600
    remaining=max(1,cutoff-time.time())
    reader=None
    source_stream=None
    archive_verified=False
    count=0
    saved=0
    status='running'
    last=time.monotonic()
    url='https://zenodo.org/api/records/18366081/files/prediction_files.tar.gz/content'
    summary_path=BASE/'manifests/coordinate_collection_status.json'
    def checkpoint(error=None):
        record={'status':status,'members_visited':count,'new_files_saved':saved,'retained_coordinate_bytes':retained,'compressed_network_bytes':reader.bytes_read if reader else 0,'time_utc':datetime.now(timezone.utc).isoformat(),'url':url,'error':error,'archive_checksum_verified':archive_verified,'http_reconnections':source_stream.reconnects if source_stream else 0,'note':'Restart cannot restore an exited gzip decompressor. Live connections can resume at exact compressed offsets; saved members have SHA256 hashes.'}
        part=summary_path.with_suffix('.json.part')
        part.write_text(json.dumps(record,indent=2),encoding='utf-8')
        os.replace(part,summary_path)
        print(json.dumps(record),flush=True)
    try:
        with ReconnectingStream(url,39_542_625_062,cutoff) as response, (BASE/'manifests/selected_coordinate_inventory.jsonl').open('a',encoding='utf-8') as inventory:
            source_stream=response
            reader=BoundedReader(response,40_000_000_000,max_seconds=remaining)
            with tarfile.open(fileobj=reader,mode='r|gz') as archive:
                for member in archive:
                    count+=1
                    if time.time()>=cutoff: raise TimeoutError('Morning cutoff reached')
                    if time.monotonic()-last>60:
                        checkpoint()
                        last=time.monotonic()
                    if not safe_member(member.name): raise ValueError('Unsafe archive path')
                    parts=PurePosixPath(member.name).parts
                    if 'prediction_files' not in parts: continue
                    index=parts.index('prediction_files')
                    tail=parts[index+1:]
                    if len(tail)<3: continue
                    model,target=tail[:2]
                    if model not in MODELS or target not in candidates or not member.isfile(): continue
                    relative='/'.join(tail[2:])
                    suffix=PurePosixPath(relative).suffix.lower()
                    selection=candidates[target].get(model+'_selection')
                    is_pose=suffix in ('.cif','.pdb') and selection and selected_pose(relative,selection)
                    # Preserve small native confidence files for ALL samples, so
                    # native-top selection can be checked independently of which
                    # samples appear in the experimental scoring tables.
                    base_name=PurePosixPath(relative).name.lower()
                    is_metadata=(suffix in ('.json','.csv') and member.size<=1_000_000 and
                                 ('ranking' in base_name or 'summary_confidence' in base_name or
                                  'confidence_input_model_' in base_name or
                                  (selection and selected_pose(relative,selection))))
                    record={'archive_member':member.name,'size':member.size,'model':model,'system_id':target,'selected_pose_match':bool(is_pose),'metadata':bool(is_metadata)}
                    if (is_pose or is_metadata) and 0<member.size<=MAX_MEMBER:
                        filename=hashlib.sha256(relative.encode()).hexdigest()[:16]+'_'+PurePosixPath(relative).name
                        dest=output/model/target/filename
                        if dest.exists():
                            record['status']='already_exists'
                        else:
                            if retained+member.size>MAX_RETAINED: raise RuntimeError('Retained coordinate budget exhausted')
                            guard(member.size+1_000_000)
                            dest.parent.mkdir(parents=True,exist_ok=True)
                            part=dest.with_name(dest.name+'.part')
                            sha=hashlib.sha256()
                            copied=0
                            try:
                                with archive.extractfile(member) as source,part.open('wb') as sink:
                                    while True:
                                        block=source.read(min(1024*1024,member.size-copied+1))
                                        if not block: break
                                        copied+=len(block)
                                        if copied>member.size or copied>MAX_MEMBER: raise RuntimeError('Archive member size limit exceeded')
                                        sink.write(block)
                                        sha.update(block)
                                if copied!=member.size: raise RuntimeError('Incomplete archive member')
                                os.replace(part,dest)
                            finally:
                                if part.exists(): part.unlink()
                            retained+=copied
                            saved+=1
                            record.update(status='saved',sha256=sha.hexdigest(),local_path=str(dest.relative_to(BASE)))
                    else:
                        record['status']='not_selected_or_unresolved_filename'
                    inventory.write(json.dumps(record)+'\n')
                    inventory.flush()
                    if inventory.tell()>50_000_000: raise RuntimeError('Inventory log budget exhausted')
            # TAR end markers can precede gzip padding/trailer. Hash all source
            # bytes before claiming the published archive checksum was verified.
            while reader.read(1024*1024):pass
            if response.position!=39_542_625_062 or response.md5.hexdigest()!='67df7db937fb28e9cf6056fcd39f9878':
                raise ValueError('Complete compressed source MD5 mismatch')
            archive_verified=True
            status='completed_tar_stream'
    except Exception as e:
        status='stopped_with_error'
        checkpoint(f'{type(e).__name__}: {e}')
        raise
    else:
        checkpoint()

if __name__=='__main__': run()
