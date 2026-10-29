"""Preserve hash-addressed active feature inputs before later reconciliation.

This records provenance; it neither freezes a scientific protocol nor authorizes
evaluation. Source changes are rejected, never re-labelled as the old snapshot.
"""
import hashlib
import json
import os
from pathlib import Path
from protocol_gate import inside
from storage import guard

BASE=Path(__file__).resolve().parent


def verified_bytes(path,expected,max_bytes=25_000_000):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>max_bytes:raise ValueError('Missing/oversized snapshot source')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Source changed; cannot reconstruct original bound snapshot')
    return raw


def main():
    guard(30_000_000)
    state_path=BASE/'manifests/rnp_feature_measurement_status.json'
    state=json.loads(state_path.read_text());sources=state['sources']
    identity=state['source_snapshot_sha256']
    if len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity):raise ValueError('Invalid snapshot identifier')
    wanted={'manifests/rnp_input_correspondence_plans.jsonl':sources['input_plan_sha256'],
            'manifests/rnp_raw_correspondence_audit.jsonl':sources['correspondence_snapshot_sha256'],
            'manifests/rnp_native_reconciliation.jsonl':sources['native_ranking_snapshot_sha256']}
    wanted.update(sources['code_sha256'])
    directory=BASE/'manifests/feature_input_snapshots'/identity;directory.mkdir(parents=True,exist_ok=True)
    artifacts={};total=0
    for relative,expected in wanted.items():
        raw=verified_bytes(inside(BASE,relative),expected)
        total+=len(raw)
        if total>28_000_000:raise RuntimeError('Snapshot total budget exceeded')
        filename=expected+'_'+Path(relative).name
        output=directory/filename
        if output.exists():verified_bytes(output,expected)
        else:
            part=output.with_suffix(output.suffix+'.part');part.write_bytes(raw);os.replace(part,output)
        artifacts[relative]={'sha256':expected,'snapshot_filename':filename}
    report={'source_snapshot_sha256':identity,'artifacts':artifacts,'total_source_bytes':total,
            'experimental_outcomes_examined':False,'protocol_frozen':False,
            'purpose':'Reconstruct feature source snapshot after live manifests are reconciled; not scientific freeze.'}
    part=directory/'manifest.json.part';part.write_text(json.dumps(report,indent=2));os.replace(part,directory/'manifest.json')
    print(json.dumps({'snapshot':str(directory),'artifacts':len(artifacts),'bytes':total,'protocol_frozen':False}))


if __name__=='__main__':main()
