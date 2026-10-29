"""Blocked, outcome-free full-cohort specifications for team-run experiments.

Does not run models, invent CLI flags, download weights/MSAs or assign final
eligibility. Every task requires verified real input/view/runner provenance.
"""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from storage import guard

BASE=Path(__file__).resolve().parent
BLOCKS=[(101,102),(211,212),(307,308),(401,402),(503,504)]
MODEL_CANDIDATES={'protenix':{'version':'1.0.0','code_commit':'4d089c7c6c10d72af2cec4c6b0586249c993a79b'},
                  'boltz2':{'version':'2.0.3','code_commit':'01594f4713266f553e94bf8477306360667f0d99'}}
BLOCKERS=['final_input_chemical_and_receptor_eligibility','verified_chain_specific_msa_pool_and_cluster_hashes',
          'actual_view_hashes_and_processed_input_roundtrip','verified_runner_container_and_weight_hashes',
          'frozen_outcome_grouping_split_and_analysis_protocol']


def system_jobs(system_id):
    if not isinstance(system_id,str) or not system_id or any(c in system_id for c in '/\\:'):
        raise ValueError('Safe explicit system ID required')
    common={'system_id':system_id,'status':'BLOCKED_SPECIFICATION_NOT_EXECUTABLE','blockers':BLOCKERS,
            'samples_per_job':5,'requested_recycles':10,'requested_sampling_steps':200,
            'templates_requested':False,'external_submission_authorized':False}
    tasks=[]
    for seed in range(9001,9006):
        tasks.append({**common,'job_id':f'{system_id}:anchor:{seed}','model':'protenix',
                      'candidate_model_provenance':MODEL_CANDIDATES['protenix'],
                      'stage':'fixed_anchor','view':'declared_full_pool','diffusion_seed':seed,
                      'selection':'global native top over all25 anchor samples; never reference geometry'})
    for block,(seed_a,seed_b) in enumerate(BLOCKS):
        cells=[('P0a','protenix','V0',seed_a),('P0b','protenix','V0',seed_b),
               ('P1b','protenix','V1',seed_b),('B0b','boltz2','V0',seed_b),('B1b','boltz2','V1',seed_b)]
        for cell,model,view,seed in cells:
            tasks.append({**common,'job_id':f'{system_id}:block{block}:{cell}',
                          'model':model,'candidate_model_provenance':MODEL_CANDIDATES[model],
                          'stage':'opinion','randomization_block':block,'cell':cell,'view':view,
                          'view_randomization_seed':701+block,'diffusion_seed':seed,
                          'requested_nonquery_cluster_rows':128,
                          'selection':'native top among this job five samples; no experimental assignment'})
    return tasks


def main():
    guard(60_000_000)
    source=BASE/'manifests/rnp_input_correspondence_plans.jsonl'
    raw=source.read_bytes();plans=[json.loads(line) for line in raw.splitlines()]
    if len({r['system_id'] for r in plans})!=len(plans):raise ValueError('Duplicate planned system IDs')
    directory=BASE/'manifests/evidence_experiment';directory.mkdir(exist_ok=True)
    jobs_path=directory/'blocked_main_jobs.jsonl';part=jobs_path.with_suffix('.part')
    cohort=[];counts=Counter();digest=hashlib.sha256();job_count=0
    with part.open('wb') as handle:
        for plan in plans:
            ready=plan['status']=='input_only_plan_constructed'
            cohort.append({'system_id':plan['system_id'],'input_plan_status':plan['status'],
                           'job_specifications':30 if ready else 0,'final_eligible':False,
                           'status':'blocked_runner_msa_protocol_verification' if ready else 'blocked_unresolved_input_chemistry'})
            counts[cohort[-1]['status']]+=1
            if not ready:continue
            for job in system_jobs(plan['system_id']):
                encoded=(json.dumps(job,separators=(',',':'))+'\n').encode()
                handle.write(encoded);digest.update(encoded);job_count+=1
                if handle.tell()>55_000_000:raise RuntimeError('Blocked job plan exceeds storage reservation')
    os.replace(part,jobs_path)
    (directory/'full_candidate_status.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in cohort))
    summary={'status':'draft_blocked_experiment_specifications_only','raw_candidate_systems':len(plans),
             'candidate_status_counts':dict(counts),'planned_prediction_jobs':job_count,
             'planned_generated_samples':job_count*5,'unique_opinion_jobs_per_block':5,
             'randomized_blocks_per_system':5,'jobs_per_input_planned_system':30,
             'arms':{'same_model_same_evidence':['P0a','P0b'],'same_model_diverse_evidence':['P0a','P1b'],
                     'different_models_same_evidence':['P0a','B0b'],'different_models_diverse_evidence':['P0a','B1b']},
             'source_input_plan_sha256':hashlib.sha256(raw).hexdigest(),'job_manifest_sha256':digest.hexdigest(),
             'draft_implementation_sha256':{name:hashlib.sha256((BASE/name).read_bytes()).hexdigest()
                 for name in ('build_evidence_experiment_plan.py','evidence_views.py','evidence_factorial_features.py')},
             'external_campaign_status':'requires independently verified chemical inputs and identical rerun configuration; no external jobs specified yet',
             'experimental_outcomes_used':False,'predictor_jobs_executed':0,'protocol_frozen':False,
             'warning':'Counts describe specifications, not feasible verified runs, GPU-hour estimates or final cohort size. Equal samples do not imply equal compute.'}
    (directory/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
