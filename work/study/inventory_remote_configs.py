"""Inventory configuration paths; never open accuracy or evaluation payloads.

Persist compressed central-directory metadata so future provenance checks do not
require another full remote-directory read. Not a downloaded full ZIP archive.
"""
import gzip
import hashlib
import json
from pathlib import Path,PurePosixPath
import zipfile
from remote_zip import RangeFile
from storage import guard
from stream_inventory import safe_member

BASE=Path(__file__).resolve().parent

def main():
    release=json.loads((BASE/'sources/openbind_record.json').read_text())
    names={'zip_run_boltz2_monomer.zip':'boltz2','zip_run_protenix_monomer_no-pair.zip':'protenix'}
    guard(120_000_000)
    for entry in release['files']:
        if entry['key'] not in names:continue
        model=names[entry['key']]
        candidates=[]
        out=BASE/'manifests'/f'openbind_{model}_full_zip_index.jsonl.gz'
        with RangeFile(entry['links']['self'],entry['size']) as remote,zipfile.ZipFile(remote) as archive,gzip.open(out,'wt',encoding='utf-8') as handle:
            for i,info in enumerate(archive.infolist()):
                if not safe_member(info.filename):raise ValueError('Unsafe remote archive member path')
                if info.is_dir():continue
                row={'name':info.filename,'size':info.file_size,'compressed_size':info.compress_size,'crc32':format(info.CRC,'08x'),
                     'header_offset':info.header_offset,'compress_type':info.compress_type,'flag_bits':info.flag_bits}
                handle.write(json.dumps(row)+'\n')
                name=PurePosixPath(info.filename).name
                suffix=PurePosixPath(name).suffix
                config=(suffix in ('.sh','.yaml','.yml') or (suffix=='.json' and
                    ('/inputs/' in info.filename or name in ('input.json','inputs.json') or name.endswith('_inp.json'))))
                if config:
                    candidates.append({**row,'archive_url':entry['links']['self'],'archive_size':entry['size'],
                                       'archive':entry['key'],'published_archive_checksum':entry.get('checksum')})
                if i%5000==0:
                    handle.flush()
                    if out.stat().st_size>55_000_000:raise RuntimeError('Compressed index exceeds local budget')
        (BASE/'manifests'/f'openbind_{model}_config_candidates.json').write_text(json.dumps(candidates,indent=2))
        digest=hashlib.sha256(out.read_bytes()).hexdigest()
        summary={'model':model,'configuration_path_candidates':len(candidates),'compressed_index_bytes':out.stat().st_size,
                 'index_sha256':digest,'network_bytes':remote.network_bytes,'contents_examined':False,
                 'archive':entry['key'],'archive_size':entry['size'],'published_archive_checksum':entry.get('checksum')}
        (BASE/'manifests'/f'openbind_{model}_config_inventory_summary.json').write_text(json.dumps(summary,indent=2))
        print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
