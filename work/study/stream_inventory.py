"""Inspect a bounded prefix of the coordinate TAR over the network without saving it."""
import argparse
import json
import tarfile
import time
import urllib.request
from pathlib import Path
from storage import guard

class BoundedReader:
    def __init__(self, response, max_bytes, max_seconds=1800):
        self.response = response
        self.max_bytes = max_bytes
        self.bytes_read = 0
        self.started = time.monotonic()
        self.max_seconds = max_seconds

    def read(self, size=-1):
        if time.monotonic() - self.started > self.max_seconds:
            raise TimeoutError('Stream time budget exhausted')
        if size < 0:
            raise ValueError('Unbounded stream read forbidden')
        if self.bytes_read + size > self.max_bytes:
            raise RuntimeError('Compressed stream byte budget exhausted')
        chunk = self.response.read(size)
        self.bytes_read += len(chunk)
        return chunk

def safe_member(name):
    from pathlib import PurePosixPath
    path = PurePosixPath(name.replace('\\','/'))
    return not path.is_absolute() and '..' not in path.parts and ':' not in name

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--members',type=int,default=150)
    parser.add_argument('--max-compressed-mb',type=int,default=128)
    args=parser.parse_args()
    guard(5_000_000)
    base=Path(__file__).resolve().parent
    output=base/'manifests'/'coordinate_prefix_inventory.jsonl'
    output.parent.mkdir(exist_ok=True)
    url='https://zenodo.org/records/18366081/files/prediction_files.tar.gz?download=1'
    request=urllib.request.Request(url,headers={'User-Agent':'ProteinLigandReliabilityResearch/0.1'})
    count=0
    reader=None
    try:
        with urllib.request.urlopen(request,timeout=90) as response, output.open('w',encoding='utf-8') as handle:
            reader=BoundedReader(response,args.max_compressed_mb*1_000_000)
            with tarfile.open(fileobj=reader,mode='r|gz') as archive:
                for member in archive:
                    if not safe_member(member.name):
                        raise ValueError(f'Unsafe TAR path: {member.name}')
                    record={'name':member.name,'size':member.size,'regular_file':member.isfile(),'link':member.issym() or member.islnk()}
                    handle.write(json.dumps(record)+'\n')
                    if count<30:
                        print(json.dumps(record),flush=True)
                    count+=1
                    if count>=args.members:
                        break
    finally:
        print(json.dumps({'members_recorded':count,'compressed_network_bytes':reader.bytes_read if reader else 0,'local_inventory_bytes':output.stat().st_size if output.exists() else 0}),flush=True)

if __name__=='__main__':
    main()
