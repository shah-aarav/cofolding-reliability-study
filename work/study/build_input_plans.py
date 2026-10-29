"""Whole-cohort input correspondence plans; not final coordinate eligibility."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from input_roles import rnp_input_roles,confidence_roles
from predictor_templates import smiles_template,named_graph_signature
from chemical_maps import stereochemistry_flags
from storage import guard

BASE=Path(__file__).resolve().parent

def main():
    guard(20_000_000)
    chemistry={row['system_id']:row for row in map(json.loads,(BASE/'manifests/chemical_inventory.jsonl').read_text().splitlines())}
    candidates=[json.loads(line) for line in (BASE/'manifests/candidates.jsonl').read_text().splitlines()]
    counts=Counter()
    reordered=[]
    out=BASE/'manifests/rnp_input_correspondence_plans.jsonl'
    with out.open('w',encoding='utf-8') as handle:
        for row in candidates:
            record={'system_id':row['system_id'],'status':'input_plan_unresolved','final_coordinate_eligibility':False,
                    'experimental_outcomes_examined':False,'source':'pinned author input_preparation.ipynb; raw output verification still required'}
            chem=chemistry[row['system_id']]
            try:
                if 'single_identity_single_input_match' not in chem['flags']:raise ValueError('No unique single proper input ligand identity')
                identity,indices=next(iter(chem['proper_identity_input_indices'].items()))
                index=indices[0]
                text=row['input_smiles'][index]
                roles=rnp_input_roles(row['input_sequences'],row['input_smiles'])
                record['input_roles']=roles
                record['proper_ligand_input_index']=index
                record['proper_identity']=identity
                record['templates']={}
                record['confidence_roles']={}
                for model in roles:
                    template=smiles_template(model,text,'RnP released inputs.json exact original SMILES')
                    signature=named_graph_signature(template)
                    record['templates'][model]={'atom_names':template.atom_names,'source':template.source,
                                                'named_graph_sha256':hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest(),
                                                'stereochemistry':stereochemistry_flags(template)}
                    proteins,ligand=confidence_roles(roles[model],index)
                    record['confidence_roles'][model]={'protein_indices':proteins,'ligand_index':ligand}
                record['status']='input_only_plan_constructed'
                if record['confidence_roles']['protenix']['ligand_index']!=record['confidence_roles']['boltz2']['ligand_index']:
                    reordered.append(row['system_id'])
            except Exception as e:record['reason']=f'{type(e).__name__}: {e}'
            counts[record['status']]+=1
            handle.write(json.dumps(record)+'\n')
            if handle.tell()>18_000_000:raise RuntimeError('Input correspondence plan exceeds budget')
    summary={'candidate_systems':len(candidates),'status_counts':dict(counts),'selected_ligand_confidence_index_reordered_by_boltz_grouping':len(reordered),
             'reordered_system_ids':reordered,'experimental_outcomes_examined':False,'final_eligible_count':None,
             'warning':'Input-builder reconstruction is not proof of raw-coordinate/configuration correspondence. Verify before scientific analysis.'}
    (BASE/'manifests/rnp_input_plan_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
