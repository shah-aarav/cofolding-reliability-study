"""Acquire official versioned Boltz parser SOURCE only; never execute it."""
from pathlib import Path
import json
from acquire import SOURCES,fetch

BASE=Path(__file__).resolve().parent
key='boltz_v2_0_3_tree'
SOURCES[key]=('https://api.github.com/repos/jwohlwend/boltz/git/trees/v2.0.3?recursive=1','sources/boltz_v2_0_3_tree.json',5_000_000)
fetch(key)
path=BASE/'sources/boltz_v2_0_3_tree.json'
if path.exists():
    tree=json.loads(path.read_text())
    for row in tree['tree']:
        if row['path'].startswith('src/boltz/data/parse/') and row['path'].endswith('.py'):
            print(row['path'])
    for name in ('yaml','schema'):
        key='boltz_v2_0_3_'+name
        SOURCES[key]=(f'https://raw.githubusercontent.com/jwohlwend/boltz/{tree["sha"]}/src/boltz/data/parse/{name}.py',f'sources/{key}.py.txt',2_000_000)
        fetch(key)
    key='boltz_v2_0_3_mmcif_writer'
    SOURCES[key]=(f'https://raw.githubusercontent.com/jwohlwend/boltz/{tree["sha"]}/src/boltz/data/write/mmcif.py',f'sources/{key}.py.txt',2_000_000)
    fetch(key)
