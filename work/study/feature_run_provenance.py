"""Hash-bound input lookup and immutable completed engineering-run copies.

Not a scientific protocol freeze and not authorization to evaluate outcomes.
"""
import hashlib
import json
import os
from pathlib import Path
from protocol_gate import inside
from storage import guard

BASE=Path(__file__).resolve().parent


def checked_bytes(path,expected,limit=25_000_000):
    if not path.is_file() or path.stat().st_size>limit:raise ValueError('Missing/oversized provenance artifact')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Provenance artifact hash mismatch')
    return raw


def bound_bytes(base,state,relative,expected):
    current=inside(base,relative)
    if current.is_file() and current.stat().st_size<=25_000_000:
        raw=current.read_bytes()
        if hashlib.sha256(raw).hexdigest()==expected:return raw,str(current)
    identity=state['source_snapshot_sha256']
    if len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity):raise ValueError('Invalid source snapshot ID')
    root=inside(base,'manifests/feature_input_snapshots/'+identity)
    manifest=json.loads((root/'manifest.json').read_text())
    if manifest['source_snapshot_sha256']!=identity:raise ValueError('Snapshot identity changed')
    artifact=manifest['artifacts'][relative]
    if artifact['sha256']!=expected:raise ValueError('Snapshot does not bind the expected source')
    path=inside(root,artifact['snapshot_filename'])
    return checked_bytes(path,expected),str(path)


def archive_completed_run():
    guard(30_000_000)
    state_path=BASE/'manifests/rnp_feature_measurement_status.json'
    raw_state=state_path.read_bytes();state=json.loads(raw_state)
    if state['status']!='completed_full_manifest_measurement_pass':raise ValueError('Only completed passes can be archived here')
    identity=state['source_snapshot_sha256']
    if len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity):raise ValueError('Invalid completed run identity')
    root=BASE/'data/rnp/feature_runs'/identity;root.mkdir(parents=True,exist_ok=True)
    sources=sorted((BASE/'data/rnp/reference_free_features').glob('*.json'))
    if len(sources)!=state['candidate_systems']:raise ValueError('Completed run record count mismatch')
    artifacts={};total=0
    def save(name,raw):
        nonlocal total
        total+=len(raw)
        if total>28_000_000:raise ValueError('Completed run snapshot budget exceeded')
        sha=hashlib.sha256(raw).hexdigest();target=inside(root,name)
        if target.exists():checked_bytes(target,sha)
        else:
            part=target.with_suffix(target.suffix+'.part');part.write_bytes(raw);os.replace(part,target)
        artifacts[name]={'sha256':sha,'bytes':len(raw)}
    for path in sources:
        if path.stat().st_size>500_000:raise ValueError('Feature record size cap exceeded')
        raw=path.read_bytes();row=json.loads(raw)
        if row['source_snapshot_sha256']!=identity or row['system_id']!=path.stem:raise ValueError('Mixed completed run source/target')
        if row.get('scientific_accuracy_result','missing') is not None or row.get('experimental_outcomes_examined') is not False:
            raise ValueError('Unexpected scientific result in engineering archive')
        save(path.name,raw)
    save('measurement_status.json',raw_state)
    report={'source_snapshot_sha256':identity,'records':len(sources),'artifact_bytes':total,'files':artifacts,
            'experimental_outcomes_examined':False,'protocol_frozen':False,'purpose':'Preserve complete earlier unlabeled engineering pass before a new acquisition snapshot is measured.'}
    encoded=json.dumps(report,indent=2).encode();target=root/'manifest.json'
    if target.exists():checked_bytes(target,hashlib.sha256(encoded).hexdigest())
    else:
        part=root/'manifest.json.part';part.write_bytes(encoded);os.replace(part,target)
    print(json.dumps({'archived_run':str(root),'records':len(sources),'bytes':total,'protocol_frozen':False}))


if __name__=='__main__':archive_completed_run()
