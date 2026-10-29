"""Input-only audit of independently native-ranked main-cohort coordinates.

Does not read experimental outcomes, measure correctness or decide eligibility.
Protenix input entity IDs come from the reviewed v0.3.4 json_to_feature builder; no chain is
selected by proximity, atom count, experimental assignment or favorable fit.
Boltz requires its explicit declared chain IDs and is audited separately.
"""
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
from chemical_maps import template_coordinates
from chain_mapping import polymer_sequences
from predictor_templates import smiles_template, named_graph_signature
from storage import guard
from structure_io import read_atoms, explicit_chain

BASE = Path(__file__).resolve().parent


def role_chain_map(model, roles, atoms, sequences):
    chains = {atom.chain for atom in atoms}
    entities = defaultdict(set)
    chain_entities = defaultdict(set)
    for atom in atoms:
        entities[atom.entity].add(atom.chain)
        chain_entities[atom.chain].add(atom.entity)
    if any(len(values) != 1 for values in chain_entities.values()):
        raise ValueError('Output chain has inconsistent entity assignments')
    if len(chains) != len(roles):
        raise ValueError('Output/input chain multiplicities differ')
    mapped = []
    for role in roles:
        if model == 'protenix':
            matches = entities[role['input_entity_id']]
            if len(matches) != 1:
                raise ValueError('Input entity does not identify exactly one output chain')
            chain = next(iter(matches))
        elif model == 'boltz2':
            chain = role['declared_input_chain_id']
            if chain not in chains:
                raise ValueError('Declared Boltz input chain missing')
        else:
            raise ValueError('Unsupported predictor')
        if role['kind'] == 'protein':
            if sequences.get(chain) != role['sequence']:
                raise ValueError('Declared polymer does not match exact input sequence')
        elif chain in sequences:
            raise ValueError('Input ligand mapped to a protein chain')
        mapped.append(chain)
    if set(mapped) != chains or len(set(mapped)) != len(mapped):
        raise ValueError('Input/output chain assignment is not bijective')
    if set(sequences) != {chain for role, chain in zip(roles, mapped) if role['kind'] == 'protein'}:
        raise ValueError('Unexpected declared protein chains')
    return mapped


def main():
    guard(10_000_000)
    plans_path = BASE/'manifests/rnp_input_correspondence_plans.jsonl'
    native_path = BASE/'manifests/rnp_native_reconciliation.jsonl'
    # Read each atomic checkpoint once; streaming collectors may continue safely.
    plans_raw, native_raw = plans_path.read_bytes(), native_path.read_bytes()
    plans = {row['system_id']:row for row in map(json.loads, plans_raw.splitlines())}
    counts = Counter()
    output = BASE/'manifests/rnp_raw_correspondence_audit.jsonl'
    temporary = output.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        for native in map(json.loads, native_raw.splitlines()):
            row = {'system_id':native['system_id'], 'model':native['model'],
                   'experimental_outcomes_examined':False, 'final_coordinate_eligibility':False}
            plan = plans[native['system_id']]
            if native['status'] != 'raw_native_selection_verified':
                row['status'] = 'awaiting_verified_native_coordinate'
            elif plan['status'] != 'input_only_plan_constructed':
                row['status'] = 'input_plan_unresolved'
            else:
                try:
                    model = native['model']
                    path = (BASE/native['coordinate_path']).resolve()
                    if not path.is_relative_to((BASE/'data/rnp/selected_coordinates').resolve()):
                        raise ValueError('Coordinate path escaped source root')
                    if path.stat().st_size > 25_000_000:
                        raise ValueError('Coordinate byte budget exceeded')
                    if hashlib.sha256(path.read_bytes()).hexdigest() != native['coordinate_sha256']:
                        raise ValueError('Coordinate SHA256 mismatch')
                    atoms = read_atoms(path)
                    roles = plan['input_roles'][model]
                    mapped = role_chain_map(model, roles, atoms, polymer_sequences(path))
                    proper = [chain for role,chain in zip(roles,mapped)
                              if role.get('input_ligand_index') == plan['proper_ligand_input_index']]
                    if len(proper) != 1:
                        raise ValueError('Proper input ligand not unique')
                    role = next(role for role in roles if role.get('input_ligand_index') == plan['proper_ligand_input_index'])
                    template = smiles_template(model, role['smiles'], 'released exact RnP input SMILES')
                    signature = hashlib.sha256(json.dumps(named_graph_signature(template), sort_keys=True).encode()).hexdigest()
                    if signature != plan['templates'][model]['named_graph_sha256']:
                        raise ValueError('Reconstructed chemical template changed since input plan')
                    template_coordinates(template, explicit_chain(atoms, proper[0]))
                    row.update(status='input_roles_and_proper_atom_names_verified',
                               coordinate_sha256=native['coordinate_sha256'],
                               coordinate_path=native['coordinate_path'],
                               input_order_to_output_chain=dict(zip((str(role['input_order']) for role in roles),mapped)),
                               proper_ligand_chain=proper[0], proper_ligand_heavy_atoms=template.molecule.GetNumAtoms(),
                               limitation='Other ligand chemical graphs, confidence availability, covalency and reference matching not established')
                except Exception as error:
                    row.update(status='raw_correspondence_unresolved', reason=f'{type(error).__name__}: {error}')
            counts[row['status']] += 1
            handle.write(json.dumps(row)+'\n')
            if handle.tell() > 9_000_000:
                raise RuntimeError('Correspondence audit output budget exceeded')
    os.replace(temporary, output)
    summary = {'status_counts':dict(counts), 'native_checkpoint_sha256':hashlib.sha256(native_raw).hexdigest(),
               'input_plans_sha256':hashlib.sha256(plans_raw).hexdigest(),
               'experimental_outcomes_examined':False, 'final_eligible_count':None,
               'warning':'Partial acquisition checkpoint; role/name correspondence is not full chemical or scientific eligibility.'}
    (BASE/'manifests/rnp_raw_correspondence_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
