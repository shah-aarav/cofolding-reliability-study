"""Acquire checksum-verified experimental archive, quarantined until protocol freeze.

This script does not enumerate members, extract coordinates or compute outcomes.
"""
import json
from pathlib import Path
from acquire import SOURCES,EXPECTED_MD5,fetch

BASE=Path(__file__).resolve().parent
release=json.loads((BASE/'sources/rnp_record.json').read_text())
entry=next(r for r in release['files'] if r['key']=='ground_truth.tar.gz')
key='rnp_reference_archive_quarantined'
SOURCES[key]=(entry['links']['self'],'data/rnp/reference_ground_truth_unopened.tar.gz',450_000_000)
algorithm,digest=entry['checksum'].split(':',1)
if algorithm!='md5':raise ValueError('Unexpected release checksum algorithm')
EXPECTED_MD5[key]=digest
if __name__=='__main__':fetch(key)
