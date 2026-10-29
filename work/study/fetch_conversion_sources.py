"""Acquire pinned conversion SOURCE for provenance review; never execute it."""
import json
from pathlib import Path
from acquire import SOURCES,fetch

BASE=Path(__file__).resolve().parent
tree=json.loads((BASE/'sources/openbind_inference_tree.json').read_text())
for model in ('boltz','protenix'):
    filename=f'Py_convert_{model}_to_of3_fmt.py'
    if filename not in {row['path'] for row in tree['tree']}:raise ValueError('Unknown source path')
    key=f'openbind_{model}_conversion_source'
    SOURCES[key]=(f'https://raw.githubusercontent.com/OmeirK/cofolding_evaluation/{tree["sha"]}/{filename}',f'sources/{filename}.txt',2_000_000)
    fetch(key)
