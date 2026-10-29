"""Acquire pinned official parser SOURCE for naming review; do not execute it."""
import json
from pathlib import Path
from acquire import SOURCES,fetch

BASE=Path(__file__).resolve().parent
tree=json.loads((BASE/'sources/protenix_source_tree.json').read_text())
for path in ('protenix/data/inference/json_parser.py','protenix/data/inference/json_to_feature.py','protenix/data/utils.py'):
    if path not in {r['path'] for r in tree['tree']}:raise ValueError('Source missing from pinned tree')
    key='protenix_source_'+Path(path).stem
    SOURCES[key]=(f'https://raw.githubusercontent.com/bytedance/Protenix/{tree["sha"]}/{path}',f'sources/{key}.py.txt',2_000_000)
    fetch(key)

SOURCES['protenix_release_tags']=('https://api.github.com/repos/bytedance/Protenix/tags?per_page=100','sources/protenix_release_tags.json',2_000_000)
fetch('protenix_release_tags')
tags=json.loads((BASE/'sources/protenix_release_tags.json').read_text())
for version in ('v0.3.4','v1.0.0'):
    tag=next(row for row in tags if row['name']==version)
    key='protenix_tree_'+version
    SOURCES[key]=(f'https://api.github.com/repos/bytedance/Protenix/git/trees/{tag["commit"]["sha"]}?recursive=1',f'sources/{key}.json',5_000_000)
    fetch(key)
    tree_path=BASE/f'sources/{key}.json'
    if tree_path.exists():
        version_tree=json.loads(tree_path.read_text())
        parser_paths=[row['path'] for row in version_tree['tree'] if row['path'].endswith('/json_parser.py')]
        if len(parser_paths)!=1:raise ValueError('Versioned parser path ambiguous')
        key='protenix_parser_'+version
        SOURCES[key]=(f'https://raw.githubusercontent.com/bytedance/Protenix/{version_tree["sha"]}/{parser_paths[0]}',f'sources/{key}.py.txt',2_000_000)
        fetch(key)
        if 'runner/dumper.py' in {row['path'] for row in version_tree['tree']}:
            key='protenix_dumper_'+version
            SOURCES[key]=(f'https://raw.githubusercontent.com/bytedance/Protenix/{version_tree["sha"]}/runner/dumper.py',f'sources/{key}.py.txt',2_000_000)
            fetch(key)
rnp=json.loads((BASE/'sources/rnp_repository_tree.json').read_text())
path='examples/inputs/protenix/8c3u__1__1.A__1.C.json'
if path in {row['path'] for row in rnp['tree']}:
    SOURCES['rnp_protenix_raw_input']=(f'https://raw.githubusercontent.com/plinder-org/runs-n-poses/{rnp["sha"]}/{path}','data/development_fixtures/rnp_protenix_raw_input.json',2_000_000)
    fetch('rnp_protenix_raw_input')
