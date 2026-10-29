"""Provisional full-intersection chemical grouping from input-only snapshots.

Raw target IDs are NOT presumed independent compounds. Missing provenance stays
unassigned. These draft groups are not a protocol freeze or final eligibility.
"""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from storage import guard

BASE=Path(__file__).resolve().parent


def group_keys(identity,scaffold):
    if not isinstance(identity,str) or not identity:raise ValueError('Verified chemical identity required')
    exact='chemical_'+hashlib.sha256(identity.encode()).hexdigest()
    # Do not combine unrelated acyclic compounds just because both have an
    # empty Murcko scaffold. Fall back to exact identity for those inputs.
    sensitivity=('scaffold_'+hashlib.sha256(scaffold.encode()).hexdigest()) if scaffold else exact
    return exact,sensitivity


def main():
    guard(5_000_000)
    source=BASE/'manifests/external_chemical_overlap.jsonl'
    raw=source.read_bytes()
    overlap={r['external_target']:r for r in map(json.loads,raw.splitlines())}
    targets=sorted(p.stem for p in (BASE/'data/openbind/native_top/boltz2').glob('*.json'))
    records=[]
    for target in targets:
        row={'external_target':target,'status':'awaiting_verified_input_chemistry_snapshot',
             'experimental_outcomes_examined':False,'final_eligible':False,'frozen_group_assignment':False}
        if overlap.get(target,{}).get('status')=='input_overlap_measured':
            chemical=overlap[target]
            exact,scaffold=group_keys(chemical['input_identity'],chemical['nonempty_scaffold'])
            row.update(status='draft_input_chemical_groups_assigned',exact_input_identity_group=exact,
                       nonempty_scaffold_sensitivity_group=scaffold,
                       input_identity=chemical['input_identity'],nonempty_scaffold=chemical['nonempty_scaffold'])
        records.append(row)
    output=BASE/'manifests/external_input_group_plans.jsonl'
    encoded=''.join(json.dumps(row)+'\n' for row in records)
    if len(encoded.encode())>4_000_000:raise RuntimeError('Draft group manifest budget exceeded')
    part=output.with_suffix('.part');part.write_text(encoded);os.replace(part,output)
    assigned=[r for r in records if r['status']=='draft_input_chemical_groups_assigned']
    exact=Counter(r['exact_input_identity_group'] for r in assigned)
    scaffold=Counter(r['nonempty_scaffold_sensitivity_group'] for r in assigned)
    summary={'raw_intersection_target_count':len(records),'status_counts':dict(Counter(r['status'] for r in records)),
             'exact_identity_groups_in_snapshot':len(exact),'nonempty_scaffold_sensitivity_groups_in_snapshot':len(scaffold),
             'largest_exact_group':max(exact.values(),default=0),'largest_scaffold_sensitivity_group':max(scaffold.values(),default=0),
             'input_overlap_snapshot_sha256':hashlib.sha256(raw).hexdigest(),
             'draft_group_manifest_sha256':hashlib.sha256(encoded.encode()).hexdigest(),
             'experimental_outcomes_examined':False,'protocol_frozen':False,'final_eligible_count':None,
             'warning':'Exact chemical graphs are not proven independent compounds. Snapshot lacks complete input/reference/Protenix identity verification. Shared target family remains one family. Grouping choices require final justification before outcomes.'}
    (BASE/'manifests/external_input_group_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
