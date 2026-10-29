"""Sequential full-manifest reference-free feature engineering, never evaluation.

Every candidate receives a status, including missing acquisition. Partial files
are not a pilot cohort, final eligibility or permission to evaluate outcomes.
Only independently native-ranked/input-correspondence-verified predictions enter
measurement. No interface accepts correctness labels or experimental structures.
"""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
from agreement_features import measure_agreement
from predictor_templates import smiles_template
from predicted_environment import environment_molecule
from storage import guard
from structure_io import read_atoms,explicit_chain
from validity import reference_free_validity

BASE=Path(__file__).resolve().parent


def hashed_json_lines(path):
    raw=path.read_bytes()
    return [json.loads(line) for line in raw.splitlines()],hashlib.sha256(raw).hexdigest()


def checked_atoms(audit):
    path=(BASE/audit['coordinate_path']).resolve()
    if not path.is_relative_to((BASE/'data/rnp/selected_coordinates').resolve()):raise ValueError('Prediction source path escaped root')
    if path.stat().st_size>25_000_000:raise ValueError('Prediction exceeds byte budget')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=audit['coordinate_sha256']:raise ValueError('Prediction checksum changed')
    return read_atoms(path)


def main(max_hours=2):
    if isinstance(max_hours,bool) or not isinstance(max_hours,(int,float)) or not math.isfinite(max_hours) or not 0<max_hours<=24:
        raise ValueError('Explicit finite runtime between0 and24hours required')
    cutoff=time.monotonic()+max_hours*3600
    guard(50_000_000)
    plans,plan_hash=hashed_json_lines(BASE/'manifests/rnp_input_correspondence_plans.jsonl')
    audit,audit_hash=hashed_json_lines(BASE/'manifests/rnp_raw_correspondence_audit.jsonl')
    native,native_hash=hashed_json_lines(BASE/'manifests/rnp_native_reconciliation.jsonl')
    audit={(r['system_id'],r['model']):r for r in audit}
    native={(r['system_id'],r['model']):r for r in native}
    modules=['measure_rnp_features.py','agreement_features.py','chemical_maps.py','geometry.py',
             'predictor_templates.py','predicted_environment.py','validity.py','structure_io.py']
    code_hashes={name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in modules}
    source={'input_plan_sha256':plan_hash,'correspondence_snapshot_sha256':audit_hash,
            'native_ranking_snapshot_sha256':native_hash,'code_sha256':code_hashes}
    source_hash=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()
    output=BASE/'data/rnp/reference_free_features';output.mkdir(exist_ok=True)
    counts=Counter()
    state=BASE/'manifests/rnp_feature_measurement_status.json'
    def checkpoint(status):
        result={'status':status,'time_utc':datetime.now(timezone.utc).isoformat(),'candidate_systems':len(plans),
                'status_counts':dict(counts),'source_snapshot_sha256':source_hash,'sources':source,
                'experimental_outcomes_examined':False,'protocol_frozen':False,'final_eligible_count':None,
                'warning':'Unlabeled engineering measurements on available verified inputs; not accuracy results or a scientific pilot.'}
        part=state.with_suffix('.part');part.write_text(json.dumps(result,indent=2));os.replace(part,state)
        print(json.dumps({k:v for k,v in result.items() if k!='sources'}),flush=True)
    checkpoint('running')
    for index,plan in enumerate(plans):
        if time.monotonic()>=cutoff:checkpoint('runtime_limit');return
        # Reserve each bounded batch before any writes. Each case is capped at
        #500KB, with1MB for status metadata. No downloads occur in this worker.
        if index%50==0:guard(min(50,len(plans)-index)*500_000+1_000_000)
        target=plan['system_id'];path=output/(target+'.json')
        if path.exists():
            old=json.loads(path.read_text())
            if old.get('source_snapshot_sha256')==source_hash:
                counts[old['status']]+=1;continue
        row={'system_id':target,'source_snapshot_sha256':source_hash,
             'experimental_outcomes_examined':False,'protocol_frozen':False,
             'final_coordinate_eligibility':False,'scientific_accuracy_result':None}
        anchor=audit[(target,'protenix')];second=audit[(target,'boltz2')]
        if anchor['status']!='input_roles_and_proper_atom_names_verified':
            row.update(status='anchor_prerequisites_unresolved',anchor_correspondence_status=anchor['status'])
        else:
            try:
                atoms=checked_atoms(anchor)
                roles=plan['input_roles']['protenix'];chains=anchor['input_order_to_output_chain']
                proteins={chains[str(r['input_order'])] for r in roles if r['kind']=='protein'}
                ligand_role=next(r for r in roles if r.get('input_ligand_index')==plan['proper_ligand_input_index'])
                template=smiles_template('protenix',ligand_role['smiles'],'RnP released exact input SMILES; verified raw correspondence')
                environment=environment_molecule(atoms,proteins,anchor['proper_ligand_chain'],'input-entity map; exact polymer sequence verification')
                validity=reference_free_validity(template,explicit_chain(atoms,anchor['proper_ligand_chain']),environment)
                row.update(anchor_coordinate_sha256=anchor['coordinate_sha256'],
                           anchor_native_ranking=native[(target,'protenix')]['native_selection'],
                           anchor_reference_free_validity=validity,
                           full_native_confidence_fields_available=native[(target,'protenix')]['full_raw_confidence_fields_available'])
                if second['status']=='input_roles_and_proper_atom_names_verified':
                    try:
                        other=checked_atoms(second)
                        other_roles=plan['input_roles']['boltz2'];other_chains=second['input_order_to_output_chain']
                        first_protein={r['original_input_chain']:other_chains[str(r['input_order'])] for r in other_roles if r['kind']=='protein'}
                        fixed_protein={r['original_input_chain']:chains[str(r['input_order'])] for r in roles if r['kind']=='protein'}
                        if set(first_protein)!=set(fixed_protein):raise ValueError('Input-defined receptor chain identities differ')
                        pairs=[(first_protein[k],fixed_protein[k]) for k in sorted(first_protein)]
                        second_template=smiles_template('boltz2',ligand_role['smiles'],'RnP released exact input SMILES; verified raw correspondence')
                        agreement=measure_agreement(other,atoms,pairs,second['proper_ligand_chain'],anchor['proper_ligand_chain'],
                                                    second_template,template,'reviewed predictor input ordering; exact raw sequences/entities/atom names')
                        row.update(agreement=agreement,second_native_ranking=native[(target,'boltz2')]['native_selection'],
                                   second_coordinate_sha256=second['coordinate_sha256'],status='anchor_and_agreement_measured')
                    except Exception as error:
                        row.update(status='anchor_measured_agreement_unresolved',agreement_error=f'{type(error).__name__}: {error}')
                else:
                    row.update(status='anchor_measured_second_prerequisites_unresolved',second_correspondence_status=second['status'])
            except Exception as error:row.update(status='measurement_unresolved',reason=f'{type(error).__name__}: {error}')
        encoded=json.dumps(row,indent=2)
        if len(encoded.encode())>500_000:raise RuntimeError('Per-system feature record exceeds cap')
        part=path.with_suffix('.part');part.write_text(encoded);os.replace(part,path)
        counts[row['status']]+=1
        if sum(counts.values())%10==0:checkpoint('running')
    checkpoint('completed_full_manifest_measurement_pass')


if __name__=='__main__':main()
