"""Input-only chemical overlap, not accuracy, exclusion or training novelty.

Reports exact isomeric identities, NONEMPTY Murcko scaffolds and diagnostic
Morgan similarity. External input acquisition can still be in progress. Never
uses experimental poses, repaired reference SDFs, labels or outcome columns.
"""
from collections import defaultdict
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
from rdkit import Chem,DataStructs
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Scaffolds import MurckoScaffold
from storage import guard

BASE=Path(__file__).resolve().parent
GENERATOR=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048,includeChirality=True)


def describe(smiles):
    mol=Chem.MolFromSmiles(smiles)
    if mol is None:raise ValueError('Invalid input chemical graph')
    if not any(a.GetAtomicNum()==6 for a in mol.GetAtoms()):raise ValueError('Nonorganic graph has no carbon')
    identity=Chem.MolToSmiles(mol,canonical=True,isomericSmiles=True)
    scaffold=MurckoScaffold.MurckoScaffoldSmiles(mol=mol,includeChirality=False)
    return identity,scaffold or None,GENERATOR.GetFingerprint(mol)


def main():
    guard(25_000_000)
    inventory_path=BASE/'manifests/chemical_inventory.jsonl'
    groups_path=BASE/'manifests/sequence_groups_draft.jsonl'
    inventory_raw,groups_raw=inventory_path.read_bytes(),groups_path.read_bytes()
    inventory=[json.loads(line) for line in inventory_raw.splitlines()]
    groups={r['system_id']:r['group_id'] for r in map(json.loads,groups_raw.splitlines())}
    identities=defaultdict(list);scaffolds=defaultdict(list);descriptors={};unresolved=[]
    for row in inventory:
        if 'single_identity_single_input_match' not in row['flags']:continue
        try:
            if len(row['proper_identity_input_indices'])!=1:raise ValueError('Proper input identity not unique')
            original=next(iter(row['proper_identity_input_indices']))
            identity,scaffold,fp=describe(original)
            identities[identity].append(row['system_id'])
            if scaffold:scaffolds[scaffold].append(row['system_id'])
            descriptors[identity]=(scaffold,fp)
        except Exception as error:unresolved.append({'system_id':row['system_id'],'reason':f'{type(error).__name__}: {error}'})
    if not descriptors:raise ValueError('No eligible input-only chemistry for overlap audit')
    order=sorted(descriptors);fingerprints=[descriptors[k][1] for k in order]
    external=[];sources={}
    for path in sorted((BASE/'data/openbind/input_audit').glob('*.json')):
        if '.processed.' in path.name:continue
        raw=path.read_bytes();row=json.loads(raw)
        if row.get('status')!='boltz_processed_input_correspondence_verified':continue
        sources[path.name]=hashlib.sha256(raw).hexdigest()
        external.append(row)
    external_ids=defaultdict(list);counts=defaultdict(int)
    output=BASE/'manifests/external_chemical_overlap.jsonl'
    part=output.with_suffix('.part')
    with part.open('w',encoding='utf-8') as handle:
        for row in external:
            result={'external_target':row['target'],'experimental_outcomes_examined':False,
                    'source':'selected-seed Boltz processed input graph; Protenix input identity not yet established'}
            try:
                identity,scaffold,fp=describe(row['input_isomeric_smiles'])
                external_ids[identity].append(row['target'])
                values=DataStructs.BulkTanimotoSimilarity(fp,fingerprints)
                maximum=max(values)
                nearest=[key for key,value in zip(order,values) if abs(value-maximum)<1e-12]
                exact=identities.get(identity,[])
                scaffold_hits=scaffolds.get(scaffold,[]) if scaffold else []
                result.update(input_identity=identity,nonempty_scaffold=scaffold,
                              exact_main_system_ids=exact,scaffold_main_system_ids=scaffold_hits,
                              maximum_morgan_tanimoto=maximum,nearest_main_input_identities=nearest[:20],
                              nearest_identity_tie_count=len(nearest),nearest_list_truncated=len(nearest)>20,
                              diagnostic_similarity_ge_0_8=maximum>=.8,status='input_overlap_measured')
                counts['external_targets_measured']+=1
                counts['external_targets_with_exact_main_input_identity']+=bool(exact)
                counts['external_targets_with_nonempty_main_scaffold']+=bool(scaffold_hits)
                counts['external_targets_with_diagnostic_similarity_ge_0_8']+=maximum>=.8
            except Exception as error:result.update(status='unresolved',reason=f'{type(error).__name__}: {error}')
            handle.write(json.dumps(result)+'\n')
            if handle.tell()>20_000_000:raise RuntimeError('Chemical overlap output budget exceeded')
    os.replace(part,output)
    def cross_group(mapping):
        return [{'chemical_key':key,'system_ids':systems,'sequence_groups':sorted({groups[s] for s in systems})}
                for key,systems in sorted(mapping.items()) if len({groups[s] for s in systems})>1]
    requested=len(list((BASE/'data/openbind/native_top/boltz2').glob('*.json')))
    summary={'time_utc':datetime.now(timezone.utc).isoformat(),'main_systems_with_single_input_identity':sum(map(len,identities.values())),
             'main_unique_input_identities':len(identities),'main_chemistry_unresolved':unresolved,
             'main_exact_identities_crossing_draft_receptor_groups':cross_group(identities),
             'main_nonempty_scaffolds_crossing_draft_receptor_groups':cross_group(scaffolds),
             'external_verified_input_targets_in_snapshot':len(external),'external_requested_target_count':requested,
             'external_input_snapshot_complete':len(external)==requested,'external_unique_input_identities':len(external_ids),
             'external_repeated_identity_targets':{k:v for k,v in external_ids.items() if len(v)>1},
             'counts':dict(counts),'source_hashes':{'main_chemical_inventory':hashlib.sha256(inventory_raw).hexdigest(),
                 'draft_sequence_groups':hashlib.sha256(groups_raw).hexdigest(),'external_input_files':sources},
             'method':'Exact RDKit canonical isomeric identity, no salt/charge/tautomer normalization; nonchiral NONEMPTY Murcko scaffold; Morgan radius2,2048bits,includeChirality=True, Tanimoto',
             'experimental_outcomes_examined':False,'final_eligible_count':None,
             'warning':'Input snapshot completeness is recorded separately, not final chemical eligibility. Similarity0.8 is a diagnostic, not a validated cutoff or exclusion. Draft receptor groups do not enforce chemical separation. No predictor-training novelty or independent-compound/family generalization claim.'}
    (BASE/'manifests/chemical_overlap_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k not in ('source_hashes','main_exact_identities_crossing_draft_receptor_groups','main_nonempty_scaffolds_crossing_draft_receptor_groups','external_repeated_identity_targets')},indent=2))


if __name__=='__main__':main()
