"""Fetch pinned raw prediction-time fixtures, not reference or accuracy outputs."""
import json
from pathlib import Path
from acquire import SOURCES,fetch

BASE=Path(__file__).resolve().parent
tree=json.loads((BASE/'sources/openbind_inference_tree.json').read_text())
prefix='examples/boltz-2_results/A71EV2A-x4390a/seed_1370180479/boltz_results_A71EV2A-x4390a_inp/'
selected={
 'openbind_boltz_confidence':prefix+'predictions/A71EV2A-x4390a_inp/confidence_A71EV2A-x4390a_inp_model_0.json',
 'openbind_boltz_record':prefix+'processed/records/A71EV2A-x4390a_inp.json',
 'openbind_boltz_hparams':prefix+'lightning_logs/version_0/hparams.yaml',
 'openbind_boltz_coordinates':prefix+'predictions/A71EV2A-x4390a_inp/A71EV2A-x4390a_inp_model_0.cif',
}
for key,path in selected.items():
    if path not in {r['path'] for r in tree['tree']}:raise ValueError('Fixture not in pinned source tree')
    extension=Path(path).suffix
    SOURCES[key]=(f'https://raw.githubusercontent.com/OmeirK/cofolding_evaluation/{tree["sha"]}/{path}',f'data/development_fixtures/{key}{extension}',5_000_000)
    fetch(key)

tree=json.loads((BASE/'sources/rnp_repository_tree.json').read_text())
prefix='examples/outputs/boltz/8c3u__1__1.A__1.C/1372115236/boltz_results_input/predictions/input/'
for kind,filename in [('confidence','confidence_input_model_0.json'),('coordinates','input_model_0.cif')]:
    path=prefix+filename
    if path not in {row['path'] for row in tree['tree']}:raise ValueError('Pinned Boltz development example absent')
    key='rnp_boltz_example_'+kind
    SOURCES[key]=(f'https://raw.githubusercontent.com/plinder-org/runs-n-poses/{tree["sha"]}/{path}',f'data/development_fixtures/{key}{Path(filename).suffix}',5_000_000)
    fetch(key)

tree=json.loads((BASE/'sources/rnp_repository_tree.json').read_text())
for kind,fragment,suffix in [('confidence','summary_confidence_sample_0.json','.json'),('coordinates','sample_0.cif','.cif')]:
    matches=[r['path'] for r in tree['tree'] if r['path'].startswith('examples/outputs/protenix/8c3u__1__1.A__1.C/seed_1622989271/predictions/') and r['path'].endswith(fragment)]
    if len(matches)!=1:raise ValueError('Pinned Protenix fixture ambiguous')
    key='rnp_protenix_'+kind
    SOURCES[key]=(f'https://raw.githubusercontent.com/plinder-org/runs-n-poses/{tree["sha"]}/{matches[0]}',f'data/development_fixtures/{key}{suffix}',5_000_000)
    fetch(key)
