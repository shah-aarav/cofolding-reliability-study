"""Outcome-free full-candidate work queue and mapping-failure diagnostics."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from structure_io import read_atoms
from storage import guard

BASE=Path(__file__).resolve().parent


def main():
    guard(10_000_000)
    paths={key:BASE/'manifests'/name for key,name in {
        'plans':'rnp_input_correspondence_plans.jsonl','native':'rnp_native_reconciliation.jsonl',
        'mapping':'rnp_raw_correspondence_audit.jsonl'}.items()}
    raw={key:path.read_bytes() for key,path in paths.items()}
    plans={r['system_id']:r for r in map(json.loads,raw['plans'].splitlines())}
    native={(r['system_id'],r['model']):r for r in map(json.loads,raw['native'].splitlines())}
    mapping={(r['system_id'],r['model']):r for r in map(json.loads,raw['mapping'].splitlines())}
    output=[];diagnostics=[]
    for target,plan in sorted(plans.items()):
        pair={}
        for model in ('protenix','boltz2'):
            n=native[(target,model)];m=mapping[(target,model)]
            pair[model]={'native_status':n['status'],'mapping_status':m['status']}
            if 'reason' in m:pair[model]['reason']=m['reason']
            if m['status']=='raw_correspondence_unresolved':
                path=BASE/n['coordinate_path']
                if hashlib.sha256(path.read_bytes()).hexdigest()!=n['coordinate_sha256']:raise ValueError('Coordinate identity changed')
                atoms=read_atoms(path);chains=sorted({a.chain for a in atoms})
                roles=plan['input_roles'][model]
                diagnostics.append({'system_id':target,'model':model,'reason':m['reason'],
                    'coordinate_sha256':n['coordinate_sha256'],'expected_role_count':len(roles),
                    'declared_input_chain_ids':[r['declared_input_chain_id'] for r in roles],
                    'observed_chain_ids':chains,'observed_chain_count':len(chains),
                    'missing_declared_chain_ids':sorted(set(r['declared_input_chain_id'] for r in roles)-set(chains)),
                    'unexpected_chain_ids':sorted(set(chains)-set(r['declared_input_chain_id'] for r in roles)),
                    'observed_chain_entities':{chain:sorted({a.entity for a in atoms if a.chain==chain}) for chain in chains},
                    'observed_chain_residue_names':{chain:sorted({a.residue for a in atoms if a.chain==chain}) for chain in chains},
                    'mapping_repaired':False,'experimental_geometry_used':False,
                    'warning':'Declared IDs have model-specific semantics; no reference/proximity-based relabeling permitted.'})
        verified=all(r['mapping_status']=='input_roles_and_proper_atom_names_verified' for r in pair.values())
        output.append({'system_id':target,'input_plan_status':plan['status'],'models':pair,
                       'paired_input_mapping_verified':verified,'final_eligible':False,
                       'next_action':'reference_eligibility_and_protocol_then_controlled_runner_validation' if verified else 'resolve_listed_input_or_acquisition_prerequisites',
                       'experimental_outcomes_examined':False})
    sources={key:hashlib.sha256(value).hexdigest() for key,value in raw.items()}
    for name,rows in [('akshobya_full_candidate_queue.jsonl',output),('akshobya_mapping_diagnostics.jsonl',diagnostics)]:
        encoded=''.join(json.dumps(row)+'\n' for row in rows)
        if len(encoded.encode())>4_000_000:raise ValueError('Handoff queue budget exceeded')
        (BASE/'manifests'/name).write_text(encoded)
    summary={'candidates':len(output),'paired_mappings_verified':sum(r['paired_input_mapping_verified'] for r in output),
             'mapping_diagnostics':len(diagnostics),'multiplicity_patterns':dict(Counter(
                 f"{r['model']}:{r['expected_role_count']}expected/{r['observed_chain_count']}observed" for r in diagnostics)),
             'source_sha256':sources,'experimental_outcomes_examined':False,'final_eligible_count':None}
    (BASE/'manifests/akshobya_queue_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
