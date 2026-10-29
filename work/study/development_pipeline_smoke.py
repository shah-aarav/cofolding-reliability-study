"""End-to-end feature plumbing on a public AUTHOR FORMAT EXAMPLE.

Not a scientific pilot, accuracy estimate or frozen feature selection. The Boltz
repository example's model version is unconfirmed; do not label it Boltz-2 or
count the unconfirmed Boltz example as a study observation. The system ID DOES
overlap the raw main candidate list: this is not independent validation. Only
file-format/feature plumbing is checked, never experimental correctness.
"""
import json
from pathlib import Path
from agreement_features import measure_agreement
from chain_mapping import polymer_sequences,paired_input_chain_map
from confidence import native_features_indices
from predictor_templates import smiles_template
from predicted_environment import environment_molecule
from structure_io import read_atoms,explicit_chain
from validity import reference_free_validity

BASE=Path(__file__).resolve().parent

def main():
    system='8c3u__1__1.A__1.C'
    candidates={r['system_id'] for r in map(json.loads,(BASE/'manifests/candidates.jsonl').read_text().splitlines())}
    overlaps=system in candidates
    fixture=BASE/'data/development_fixtures'
    raw=json.loads((fixture/'rnp_protenix_raw_input.json').read_text())[0]
    sequence=raw['sequences'][0]['proteinChain']['sequence']
    smiles=raw['sequences'][1]['ligand']['ligand']
    first_path=fixture/'rnp_boltz_example_coordinates.cif'
    second_path=fixture/'rnp_protenix_coordinates.cif'
    first,second=read_atoms(first_path),read_atoms(second_path)
    pairs=paired_input_chain_map({'input_protein':sequence},polymer_sequences(first_path),polymer_sequences(second_path))
    first_template=smiles_template('boltz2',smiles,'pinned author example input; naming-rule compatibility test only, model version unconfirmed')
    second_template=smiles_template('protenix',smiles,'pinned author Protenix input JSON')
    first_nonprotein={a.chain for a in first}-{a for a,b in pairs}
    second_nonprotein={a.chain for a in second}-{b for a,b in pairs}
    if len(first_nonprotein)!=1 or len(second_nonprotein)!=1:raise ValueError('Expected single-ligand development example')
    ligand_first,ligand_second=next(iter(first_nonprotein)),next(iter(second_nonprotein))
    agreement=measure_agreement(first,second,pairs,ligand_first,ligand_second,first_template,second_template,
                                'exact declared example protein sequence and exact SMILES templates; no experimental assignment')
    native=native_features_indices('protenix',json.loads((fixture/'rnp_protenix_confidence.json').read_text()),[0],1)
    environment=environment_molecule(second,{b for a,b in pairs},ligand_second,'single protein/ligand declared in pinned example input JSON')
    validity=reference_free_validity(second_template,explicit_chain(second,ligand_second),environment)
    report={'system_id':system,'purpose':'implementation plumbing only; not independent validation','main_cohort_overlap':overlaps,
            'boltz_example_version':'unconfirmed; NOT counted as a Boltz-2 study prediction',
            'native_top_selection_for_this_example':False,'experimental_outcomes_examined':False,
            'agreement_features':agreement,'anchor_native_features':native,'anchor_reference_free_validity':validity,
            'scientific_accuracy_or_effect_estimate':None}
    (BASE/'manifests/development_pipeline_smoke.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'status':'development_feature_pipeline_completed','matched_protein_ca_atoms':agreement['agreement']['receptor_ca_correspondences'],
                      'ligand_heavy_atoms':second_template.molecule.GetNumAtoms(),'validity_checks_returned':len(validity['checks']),
                      'missing_validity_checks':validity['missing_checks'],'experimental_outcomes_examined':False},indent=2))

if __name__=='__main__':main()
