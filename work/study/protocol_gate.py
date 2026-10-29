"""Hash-bound protocol gate for later real outcome evaluation.

This is a workflow safeguard, not access control or proof of scientific validity.
No freeze has been created for the current unfinished study. Synthetic tests may
exercise analysis functions without authorizing real held-out evaluation.
"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

REQUIRED=('research_question','eligibility_definition','native_selection_definition','chemical_mapping_definition',
          'receptor_mapping_definition','outcome_definition','grouping_definition','validation_definition',
          'feature_sets','primary_comparison','primary_operating_point','missingness_policy',
          'uncertainty_definition','model_provenance','external_validation_scope','assistance_disclosure')

def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def inside(root,relative):
    root=Path(root).resolve()
    relative=Path(relative)
    if relative.is_absolute():raise ValueError('Protocol paths must be relative to the declared study root')
    path=(root/relative).resolve()
    if path==root or not path.is_relative_to(root):raise ValueError('Protocol path escapes study root')
    return path

def canonical_digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def build_freeze(root,spec,bound_paths,readiness):
    """Construct only after actual readiness evidence exists; never infer it.

    Readiness booleans are explicit operator attestations. They do not replace
    source/eligibility artifacts, which must also be bound by file hashes.
    """
    missing=[key for key in REQUIRED if key not in spec or not spec[key]]
    if missing:raise ValueError('Unresolved protocol fields: '+', '.join(missing))
    expected=('native_top_verified','input_chemical_mapping_verified','model_provenance_resolved',
              'eligibility_and_groups_fixed','held_out_outcomes_not_examined')
    if any(readiness.get(key) is not True for key in expected):raise ValueError('Study is not ready for protocol freeze')
    if not bound_paths or len(set(bound_paths))!=len(bound_paths):raise ValueError('Need unique explicit bound artifacts')
    files={str(path):sha256_file(inside(root,path)) for path in sorted(bound_paths)}
    payload={'schema_version':1,'frozen_utc':datetime.now(timezone.utc).isoformat(),'specification':spec,
             'readiness_attestations':readiness,'bound_files':files,
             'warning':'Hash binding is a workflow safeguard, not proof of valid design or independent authorship.'}
    return {'payload':payload,'sha256':canonical_digest(payload)}

def verify_freeze(root,freeze):
    if freeze.get('sha256')!=canonical_digest(freeze.get('payload')):raise ValueError('Frozen protocol digest mismatch')
    payload=freeze['payload']
    if payload.get('schema_version')!=1 or not payload.get('bound_files'):raise ValueError('Invalid protocol freeze schema')
    for relative,expected in payload['bound_files'].items():
        path=inside(root,relative)
        if not path.is_file() or sha256_file(path)!=expected:raise ValueError('Frozen artifact changed/missing: '+relative)
    return payload

def require_frozen_protocol(root,filename='manifests/frozen_protocol.json'):
    path=inside(root,filename)
    if not path.is_file():raise RuntimeError('Real held-out evaluation blocked: no frozen protocol exists')
    return verify_freeze(root,json.loads(path.read_text(encoding='utf-8')))
