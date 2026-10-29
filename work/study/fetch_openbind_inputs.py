"""Acquire release-pinned inputs only; experimental outputs remain unopened."""
import json
from pathlib import Path
from acquire import SOURCES,EXPECTED_MD5,fetch

BASE=Path(__file__).resolve().parent
release=json.loads((BASE/'sources/openbind_record.json').read_text())
for entry in release['files']:
    if entry['key'] not in ('A71EV2A_prepared_inputs.zip','A71EV2A_data.zip'):continue
    is_prepared=entry['key']=='A71EV2A_prepared_inputs.zip'
    key='openbind_prepared_inputs' if is_prepared else 'openbind_reference_data_quarantined'
    SOURCES[key]=(entry['links']['self'],'data/openbind/'+('prepared_inputs.zip' if is_prepared else 'reference_data_unopened.zip'),160_000_000 if is_prepared else 70_000_000)
    algorithm,digest=entry['checksum'].split(':',1)
    if algorithm!='md5':raise ValueError('Unexpected release checksum algorithm')
    EXPECTED_MD5[key]=digest
    fetch(key)
