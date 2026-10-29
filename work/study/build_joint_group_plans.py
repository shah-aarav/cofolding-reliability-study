"""Input-only feasibility of jointly receptor/chemical-cold grouping.

No split assignment, outcomes or final eligibility. Unknown chemistry cannot
establish chemical separation; preserve its missingness explicitly.
"""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from build_external_input_groups import group_keys
from storage import guard

BASE=Path(__file__).resolve().parent


def joint_plans(rows):
    rows=sorted(rows,key=lambda r:r['system_id'])
    ids=[r['system_id'] for r in rows]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate system ID')
    for row in rows:
        if not isinstance(row['receptor_group'],str) or not row['receptor_group']:
            raise ValueError('Draft receptor group required for every candidate')
        identity=row['identity'];scaffold=row['scaffold']
        if identity is not None and (not isinstance(identity,str) or not identity):raise ValueError('Invalid chemical identity')
        if scaffold is not None and (not isinstance(scaffold,str) or not scaffold or identity is None):raise ValueError('Invalid scaffold')
    identity_scaffolds={}
    for row in rows:
        if row['identity'] is None:continue
        if row['identity'] in identity_scaffolds and identity_scaffolds[row['identity']]!=row['scaffold']:
            raise ValueError('Same chemical identity has conflicting scaffolds')
        identity_scaffolds[row['identity']]=row['scaffold']
    def partition(scaffold_mode):
        parent={i:i for i in ids};first={}
        def find(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        for row in rows:
            keys=[('receptor',row['receptor_group'])]
            if row['identity'] is not None:
                exact,scaffold=group_keys(row['identity'],row['scaffold'])
                keys.append(('chemical',scaffold if scaffold_mode else exact))
            for key in keys:
                if key in first:
                    a,b=find(row['system_id']),find(first[key]);parent[max(a,b)]=min(a,b)
                else:first[key]=row['system_id']
        components={}
        for i in ids:components.setdefault(find(i),[]).append(i)
        prefix='joint_scaffold_' if scaffold_mode else 'joint_exact_'
        return {i:prefix+hashlib.sha256(json.dumps(members).encode()).hexdigest()
                for members in components.values() for i in members}
    exact,scaffold=partition(False),partition(True)
    return [{**row,'joint_exact_group':exact[row['system_id']],
             'joint_scaffold_group':scaffold[row['system_id']],
             'chemical_group_status':'input_identity_available' if row['identity'] else 'unresolved_not_proven_chemically_cold',
             'split_assigned':False,'final_eligible':False,'experimental_outcomes_examined':False} for row in rows]


def main():
    guard(8_000_000)
    paths={'receptor_groups':BASE/'manifests/sequence_groups_draft.jsonl',
           'chemical_inventory':BASE/'manifests/chemical_inventory.jsonl'}
    raw={key:path.read_bytes() for key,path in paths.items()}
    chemistry={r['system_id']:r for r in map(json.loads,raw['chemical_inventory'].splitlines())}
    rows=[]
    for row in map(json.loads,raw['receptor_groups'].splitlines()):
        chemical=chemistry[row['system_id']];identity=scaffold=None
        if 'single_identity_single_input_match' in chemical['flags']:
            values=chemical['proper_identity_input_indices']
            if len(values)!=1 or len(next(iter(values.values())))!=1:raise ValueError('Ambiguous proper input identity')
            index=next(iter(values.values()))[0];entry=chemical['input_ligands'][index]
            if not entry['parse_ok']:raise ValueError('Unexpected unparsed matched input')
            identity=entry['canonical_isomeric_smiles'];scaffold=entry['murcko_scaffold'] or None
        rows.append({'system_id':row['system_id'],'receptor_group':row['group_id'],'identity':identity,'scaffold':scaffold})
    plans=joint_plans(rows)
    encoded=''.join(json.dumps(row)+'\n' for row in plans).encode()
    if len(encoded)>6_000_000:raise ValueError('Joint group manifest cap exceeded')
    output=BASE/'manifests/joint_group_plans_draft.jsonl';part=output.with_suffix('.part')
    part.write_bytes(encoded);os.replace(part,output)
    def counts(key,known_only):
        sizes=Counter(row[key] for row in plans if not known_only or row['identity'] is not None)
        return {'groups':len(sizes),'largest':max(sizes.values(),default=0),'sizes_descending':sorted(sizes.values(),reverse=True)}
    summary={'candidate_systems':len(plans),'systems_with_unresolved_chemistry':sum(r['identity'] is None for r in plans),
             'group_sizes_all_candidates':{k:counts(k,False) for k in ('receptor_group','joint_exact_group','joint_scaffold_group')},
             'group_sizes_known_chemistry_only':{k:counts(k,True) for k in ('receptor_group','joint_exact_group','joint_scaffold_group')},
             'source_sha256':{key:hashlib.sha256(value).hexdigest() for key,value in raw.items()},
             'manifest_sha256':hashlib.sha256(encoded).hexdigest(),'protocol_frozen':False,'experimental_outcomes_examined':False,
             'warning':'Transitive joint-group feasibility only, no split assigned. Unknown chemistry does not establish separation. Receptor groups and short-chain policy remain draft; exact graphs have no salt/charge/tautomer normalization. Do not count groups as proven independent biological units or select grouping from test accuracy.'}
    (BASE/'manifests/joint_group_summary_draft.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({**summary,'group_sizes_all_candidates':{k:{x:y for x,y in v.items() if x!='sizes_descending'} for k,v in summary['group_sizes_all_candidates'].items()},
                      'group_sizes_known_chemistry_only':{k:{x:y for x,y in v.items() if x!='sizes_descending'} for k,v in summary['group_sizes_known_chemistry_only'].items()}},indent=2))


if __name__=='__main__':main()
