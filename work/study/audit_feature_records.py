"""Validate unlabeled feature-record provenance without evaluating correctness."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from protocol_gate import require_frozen_protocol
from storage import guard
from feature_run_provenance import bound_bytes

BASE=Path(__file__).resolve().parent


def verify_record(row,target,source_hash,correspondence):
    if row.get('system_id')!=target or row.get('source_snapshot_sha256')!=source_hash:
        raise ValueError('Feature target/source snapshot mismatch')
    for key in ('experimental_outcomes_examined','protocol_frozen','final_coordinate_eligibility'):
        if row.get(key) is not False:raise ValueError('Unexpected scientific readiness/outcome flag')
    if row.get('scientific_accuracy_result','missing') is not None:raise ValueError('Unexpected accuracy result')
    allowed={'anchor_prerequisites_unresolved','measurement_unresolved','anchor_measured_second_prerequisites_unresolved',
             'anchor_measured_agreement_unresolved','anchor_and_agreement_measured'}
    status=row.get('status')
    if status not in allowed:raise ValueError('Unknown feature status')
    if status.startswith('anchor_measured') or status=='anchor_and_agreement_measured':
        anchor=correspondence[(target,'protenix')]
        if anchor['status']!='input_roles_and_proper_atom_names_verified' or row['anchor_coordinate_sha256']!=anchor['coordinate_sha256']:
            raise ValueError('Feature anchor lacks matching verified correspondence')
        validity=row['anchor_reference_free_validity']
        if validity.get('experimental_reference_used') is not False:raise ValueError('Unexpected reference-dependent validity')
        checks=validity['checks'];missing=validity['missing_checks']
        if any(type(value) is not bool for value in checks.values()) or set(checks)&set(missing):
            raise ValueError('Invalid/mixed validity missingness')
        if len(checks)+len(missing)!=22:raise ValueError('Expected dock check count changed')
        expected=all(checks.values()) if not missing else None
        if validity['all_checks_pass'] is not expected:raise ValueError('Missing checks incorrectly treated as passing')
    if status=='anchor_and_agreement_measured':
        second=correspondence[(target,'boltz2')]
        if second['status']!='input_roles_and_proper_atom_names_verified' or row['second_coordinate_sha256']!=second['coordinate_sha256']:
            raise ValueError('Agreement lacks verified second prediction')
        if row['agreement'].get('experimental_reference_used') is not False:raise ValueError('Agreement used reference geometry')
    elif 'agreement' in row:raise ValueError('Unexpected successful agreement on unresolved status')


def main():
    guard(5_000_000)
    state_path=BASE/'manifests/rnp_feature_measurement_status.json'
    state=json.loads(state_path.read_text())
    audit_raw,provenance_path=bound_bytes(BASE,state,'manifests/rnp_raw_correspondence_audit.jsonl',
                                        state['sources']['correspondence_snapshot_sha256'])
    correspondence={(r['system_id'],r['model']):r for r in map(json.loads,audit_raw.splitlines())}
    counts=Counter();errors=[];hashes={}
    for path in sorted((BASE/'data/rnp/reference_free_features').glob('*.json')):
        if path.stat().st_size>500_000:raise ValueError('Feature record exceeds reader cap')
        raw=path.read_bytes();row=json.loads(raw)
        try:
            verify_record(row,path.stem,state['source_snapshot_sha256'],correspondence)
            hashes[path.name]=hashlib.sha256(raw).hexdigest();counts[row['status']]+=1
        except Exception as error:errors.append({'file':path.name,'error':f'{type(error).__name__}: {error}'})
    try:
        require_frozen_protocol(BASE);gate='frozen_protocol_verified'
    except (RuntimeError,ValueError) as error:gate=f'evaluation_blocked: {error}'
    report={'time_utc':datetime.now(timezone.utc).isoformat(),'feature_records_checked':sum(counts.values())+len(errors),
            'verified_status_counts':dict(counts),'errors':errors,'feature_file_sha256':hashes,
            'source_snapshot_sha256':state['source_snapshot_sha256'],'measurement_status_at_audit':state['status'],
            'correspondence_artifact_used':provenance_path,
            'evaluation_gate':gate,'experimental_outcomes_examined':False,
            'warning':'Record/schema/provenance audit only. No accuracy estimate, feature distribution or biological correctness validation.'}
    (BASE/'manifests/feature_record_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='feature_file_sha256'},indent=2))


if __name__=='__main__':main()
