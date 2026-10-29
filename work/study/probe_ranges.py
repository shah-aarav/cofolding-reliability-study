"""Bounded capability probe for remote ZIP reading; never save a full ZIP."""
import hashlib
import json
import urllib.request
from pathlib import Path
from storage import guard

BASE=Path(__file__).resolve().parent

def run():
    guard(1_000_000)
    release=json.loads((BASE/'sources/openbind_record.json').read_text())
    wanted={'zip_run_boltz2_monomer.zip','zip_run_protenix_monomer_no-pair.zip'}
    results=[]
    for entry in release['files']:
        if entry['key'] not in wanted:continue
        size=entry['size']
        start=max(0,size-65536)
        url=entry['links']['self']
        record={'archive':entry['key'],'url':url,'release_bytes':size,'requested_range':f'bytes={start}-{size-1}'}
        try:
            req=urllib.request.Request(url,headers={'Range':record['requested_range'],'User-Agent':'ProteinLigandReliabilityResearch/0.1'})
            with urllib.request.urlopen(req,timeout=60) as response:
                record['http_status']=response.status
                record['content_range']=response.headers.get('Content-Range')
                record['etag']=response.headers.get('ETag')
                if response.status!=206 or record['content_range']!=f'bytes {start}-{size-1}/{size}':
                    record['range_supported']=False
                    record['note']='Did not consume response body because exact partial-content support was absent.'
                else:
                    data=response.read(65537)
                    if len(data)!=size-start:raise ValueError('Unexpected range-response size')
                    record.update(range_supported=True,transferred_bytes=len(data),tail_sha256=hashlib.sha256(data).hexdigest(),zip_end_record_present=b'PK\x05\x06' in data,zip64_locator_present=b'PK\x06\x07' in data)
        except Exception as e:
            record.update(range_supported=False,error=f'{type(e).__name__}: {e}')
        results.append(record)
        print(json.dumps(record),flush=True)
    (BASE/'manifests/openbind_range_probe.json').write_text(json.dumps(results,indent=2),encoding='utf-8')

if __name__=='__main__':run()
