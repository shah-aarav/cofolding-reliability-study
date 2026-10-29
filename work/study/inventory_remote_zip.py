"""Inventory all OpenBind raw prediction paths without downloading full archives."""
import json
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from remote_zip import RangeFile
from storage import guard
from stream_inventory import safe_member

BASE=Path(__file__).resolve().parent

def run():
    guard(230_000_000)
    release=json.loads((BASE/'sources/openbind_record.json').read_text())
    wanted={'zip_run_boltz2_monomer.zip':'boltz2','zip_run_protenix_monomer_no-pair.zip':'protenix'}
    summaries=[]
    for entry in release['files']:
        if entry['key'] not in wanted:continue
        model=wanted[entry['key']]
        out=BASE/'manifests'/f'openbind_{model}_zip_inventory.jsonl'
        counts=Counter()
        examples=[]
        saved_entries=0
        with RangeFile(entry['links']['self'],entry['size']) as stream,zipfile.ZipFile(stream) as archive,out.open('w',encoding='utf-8') as handle:
            for info in archive.infolist():
                if not safe_member(info.filename):raise ValueError('Unsafe ZIP member path')
                suffix=PurePosixPath(info.filename).suffix.lower()
                counts[suffix]+=1
                basename=PurePosixPath(info.filename).name.lower()
                relevant=(not info.is_dir() and (
                    (suffix=='.json' and ('summary_confidence' in basename or basename.startswith('confidence_'))) or
                    (suffix=='.csv' and 'ranking' in basename) or
                    (suffix in ('.cif','.pdb') and '/predictions/' in info.filename and basename!='receptor.cif')))
                if not relevant:continue
                row={'name':info.filename,'size':info.file_size,'compressed_size':info.compress_size,'crc32':format(info.CRC,'08x'),'directory':info.is_dir(),
                     'header_offset':info.header_offset,'compress_type':info.compress_type,'flag_bits':info.flag_bits,
                     'archive':entry['key'],'archive_size':entry['size'],'archive_url':entry['links']['self'],
                     'published_archive_checksum':entry.get('checksum')}
                handle.write(json.dumps(row)+'\n')
                saved_entries+=1
                if len(examples)<15 and not info.is_dir():examples.append(info.filename)
                if handle.tell()>110_000_000:raise RuntimeError('ZIP inventory local byte budget exhausted')
            handle.flush()
            summary={'model':model,'archive':entry['key'],'remote_archive_bytes':entry['size'],'entries_scanned':len(archive.infolist()),'selected_prediction_metadata_entries_saved':saved_entries,'suffix_counts':dict(counts),'network_bytes_for_inventory':stream.network_bytes,'range_requests':stream.requests,'local_inventory_bytes':out.stat().st_size,'example_paths':examples,'whole_archive_downloaded':False,'whole_archive_md5_verified':False}
            summaries.append(summary)
            print(json.dumps(summary,indent=2),flush=True)
    (BASE/'manifests/openbind_zip_summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')

if __name__=='__main__':run()
