"""Strict single-chain, unpaired evidence-return contract; no predictor adapter.

Checks a supplied normalized AFTER-preprocessing record against a view. Cannot
prove the record was extracted from a real tensor; source hashes must be
independently checked. Multichain/paired/masked inputs remain unsupported here.
No downloads, model runs, reference geometry or correctness labels.
"""
import hashlib
import json
import re
from evidence_views import aligned_sequence


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def row_features(a3m):
    """Canonical audit convention: counts before each column plus terminal count.

    Lowercase letters are inserted residues; dots are insertion-alignment pads.
    This is NOT an assertion about any model's native tensor representation.
    """
    sequence=aligned_sequence(a3m)
    if not sequence or len(sequence)>8192:raise ValueError('Unsupported alignment width')
    counts=[];pending=0
    for char in a3m:
        if char.islower():pending+=1
        elif char.isupper() or char=='-':counts.append(pending);pending=0
    return {'aligned_sequence':sequence,'insertion_counts':counts+[pending]}


def verify_consumption(view,record):
    required={'schema_version','protein_chain_count','pairing_mode','templates_enabled',
              'automatic_evidence_enabled','input_sha256','view_sha256','processed_artifact_sha256',
              'extractor_code_sha256','runner_config_sha256','rows'}
    if not isinstance(record,dict) or set(record)!=required:raise ValueError('Exact outcome-free consumption schema required')
    if type(record['schema_version']) is not int or record['schema_version']!=1:raise ValueError('Unknown consumption schema')
    if type(record['protein_chain_count']) is not int or record['protein_chain_count']!=1 or record['pairing_mode']!='unpaired':
        raise ValueError('Multichain/paired evidence needs a separate validated adapter')
    if record['templates_enabled'] is not False or record['automatic_evidence_enabled'] is not False:
        raise ValueError('Undeclared extra evidence invalidates this contract')
    for key in ('input_sha256','view_sha256','processed_artifact_sha256','extractor_code_sha256','runner_config_sha256'):
        if not isinstance(record[key],str) or re.fullmatch('[0-9a-f]{64}',record[key]) is None:
            raise ValueError('Actual artifact identities required')
    payload={key:value for key,value in view.items() if key!='view_sha256'}
    if digest(payload)!=view.get('view_sha256') or record['view_sha256']!=view['view_sha256']:
        raise ValueError('Requested view digest mismatch')
    sequences=view['sequences'];rows=record['rows']
    if not isinstance(rows,list) or not 2<=len(sequences)<=1024 or len(rows)!=len(sequences):
        raise ValueError('Effective row depth changed or exceeds supported scope')
    if sequences[0]!=view['query'] or len(view['cluster_ids'])!=len(sequences)-1:
        raise ValueError('View query/depth contract changed')
    expected=[row_features(row) for row in sequences]
    width=len(view['query'])
    for row,target in zip(rows,expected):
        if not isinstance(row,dict) or set(row)!={'aligned_sequence','insertion_counts','active_columns'}:
            raise ValueError('Exact normalized row fields required')
        if len(target['aligned_sequence'])!=width or row['aligned_sequence']!=target['aligned_sequence']:
            raise ValueError('Consumed alignment sequence/order changed')
        counts=row['insertion_counts'];active=row['active_columns']
        if not isinstance(counts,list) or any(type(n) is not int or n<0 for n in counts) or counts!=target['insertion_counts']:
            raise ValueError('Consumed insertion features changed')
        if not isinstance(active,list) or len(active)!=width or any(v is not True for v in active):
            raise ValueError('Cropped/masked evidence is outside the exact-view contract')
    return {'semantic_evidence_sha256':digest(expected),'input_sha256':record['input_sha256'],
            'view_sha256':view['view_sha256'],'rows':len(rows),'aligned_columns':width,
            'scope':'single_chain_unpaired_supplied_record_consistency_only',
            'actual_tensor_extraction_verified':False,'experimental_outcomes_examined':False}


def compare_shared(left,right):
    """Compare verified normalized return records, NOT claims of independence."""
    keys=('scope','semantic_evidence_sha256','input_sha256','view_sha256','rows','aligned_columns')
    if any(left.get(key) is None or left.get(key)!=right.get(key) for key in keys):
        raise ValueError('Shared-evidence records differ in input or consumed evidence')
    return {'shared_normalized_record_evidence':True,'actual_tensor_extraction_verified':False,
            'statistical_independence_claimed':False}
