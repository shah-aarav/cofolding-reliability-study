"""Input-only chemistry inventory across all candidates; no outcomes or pose labels."""
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'deps'))
import json
from collections import Counter, defaultdict
from rdkit import Chem, rdBase
from rdkit.Chem import Descriptors, Lipinski
from rdkit.Chem.Scaffolds import MurckoScaffold
from storage import guard

def describe(smiles):
    molecule=Chem.MolFromSmiles(smiles)
    if molecule is None:
        return {'original_smiles':smiles,'parse_ok':False}
    canonical=Chem.MolToSmiles(molecule,canonical=True,isomericSmiles=True)
    scaffold=MurckoScaffold.MurckoScaffoldSmiles(mol=molecule,includeChirality=False)
    return {'original_smiles':smiles,'parse_ok':True,'canonical_isomeric_smiles':canonical,
            'heavy_atoms':molecule.GetNumHeavyAtoms(),'fragments':len(Chem.GetMolFrags(molecule)),
            'formal_charge':Chem.GetFormalCharge(molecule),'molecular_weight':Descriptors.MolWt(molecule),
            'rotatable_bonds':Lipinski.NumRotatableBonds(molecule),'murcko_scaffold':scaffold or None,
            'atomic_numbers':sorted({atom.GetAtomicNum() for atom in molecule.GetAtoms()}),
            'policy':'no salt stripping, protonation normalization, stereochemistry removal or tautomer merging'}

def run():
    guard(10_000_000)
    source=BASE/'manifests/candidates.jsonl'
    out=BASE/'manifests/chemical_inventory.jsonl'
    rows=[json.loads(line) for line in source.read_text().splitlines()]
    flags=Counter()
    exact_groups=defaultdict(list)
    molecules={}
    for row in rows:
        for smiles in row['input_smiles']+row['proper_ligand_smiles']:
            if smiles not in molecules: molecules[smiles]=describe(smiles)
    with out.open('w',encoding='utf-8') as handle:
        for row in rows:
            inputs=[molecules[s] for s in row['input_smiles']]
            proper=[molecules[s] for s in row['proper_ligand_smiles']]
            local=[]
            if any(not m['parse_ok'] for m in inputs): local.append('input_smiles_parse_failure')
            if any(not m['parse_ok'] for m in proper): local.append('annotation_smiles_parse_failure')
            identities=sorted({m['canonical_isomeric_smiles'] for m in proper if m['parse_ok']})
            if not identities: local.append('no_resolved_proper_ligand_identity')
            if len(identities)>1: local.append('multiple_proper_ligand_identities')
            matches={identity:[i for i,m in enumerate(inputs) if m.get('canonical_isomeric_smiles')==identity] for identity in identities}
            if any(not indices for indices in matches.values()): local.append('proper_identity_not_in_input')
            if any(len(indices)>1 for indices in matches.values()): local.append('repeated_identical_input_ligands')
            if any(m.get('fragments',0)>1 for m in proper): local.append('multifragment_proper_ligand')
            if not row['input_sequences']: local.append('no_input_receptor_sequence')
            if len(identities)==1 and len(matches[identities[0]])==1:
                local.append('single_identity_single_input_match')
            flags.update(local)
            exact_groups[row['identical_sequence_hash']].append(row['system_id'])
            handle.write(json.dumps({'system_id':row['system_id'],'input_ligands':inputs,'annotated_proper_ligands':proper,'proper_identity_input_indices':matches,'flags':local,'status':'input chemistry audit, not final coordinate eligibility'})+'\n')
    summary={'candidate_systems':len(rows),'unique_smiles_strings_parsed':len(molecules),'rdkit_version':rdBase.rdkitVersion,
             'flags':dict(flags),'identical_receptor_sequence_set_groups':len(exact_groups),
             'largest_exact_sequence_group':max(map(len,exact_groups.values()),default=0),
             'sequence_family_groups_computed':False,'final_eligible_count':None,'outcomes_examined':False}
    (BASE/'manifests/chemical_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':run()
