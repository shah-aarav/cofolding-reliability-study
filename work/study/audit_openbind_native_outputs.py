"""Full external acquisition/native-selection audit; no experimental labels."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from collect_openbind import rank_native
from chain_mapping import polymer_sequences
from structure_io import read_atoms,chain_inventory
from storage import guard

BASE=Path(__file__).resolve().parent

def main():
    guard(30_000_000)
    cohort=json.loads((BASE/'manifests/openbind_cohort_audit.json').read_text())
    targets=cohort['raw_target_ids']
    counts=Counter()
    sequences=set()
    output=BASE/'manifests/openbind_native_verified.jsonl'
    part=output.with_name(output.name+'.part')
    with part.open('w',encoding='utf-8') as handle:
        for model in ('boltz2','protenix'):
            scope='run_boltz2_monomer' if model=='boltz2' else 'run_protenix_monomer_no-pair'
            for target in targets:
                folder=BASE/'data/openbind/native_top'/model
                meta_path=folder/(target+'.json');coordinate_path=folder/(target+'.cif')
                row={'model':model,'source_target_id':target,'experimental_outcomes_examined':False,'chemical_eligibility_verified':False}
                if not meta_path.exists() or not coordinate_path.exists():row['status']='not_acquired_at_checkpoint'
                else:
                    try:
                        meta=json.loads(meta_path.read_text())
                        if meta['model']!=model or meta['source_target_id']!=target:raise ValueError('Stored metadata identity mismatch')
                        confidences=meta['raw_confidences']
                        keys={(r['seed'],r['sample']) for r in confidences}
                        if len(confidences)!=25 or len(keys)!=25 or len({s for s,n in keys})!=5:raise ValueError('Incomplete/duplicated raw sample design')
                        if any({n for s,n in keys if s==seed}!=set(map(str,range(5))) for seed,sample in keys):raise ValueError('Incomplete seed samples')
                        selected=rank_native(model,[(r['seed'],r['sample'],r['confidence']) for r in confidences])
                        if selected!=meta['selection']:raise ValueError('Stored selected pose differs from recomputed raw native top')
                        if not meta['coordinate_member']['name'].startswith(f'{scope}/results/{target}/'):raise ValueError('Archive run scope mismatch')
                        raw=coordinate_path.read_bytes()
                        if hashlib.sha256(raw).hexdigest()!=meta['coordinate_integrity']['sha256']:raise ValueError('Retained coordinate digest mismatch')
                        row.update(status='native_acquisition_verified',native_selection=selected,coordinate_bytes=len(raw),
                                   coordinate_sha256=meta['coordinate_integrity']['sha256'],raw_sample_count=25,
                                   coordinate_path=str(coordinate_path.relative_to(BASE)))
                        try:
                            atoms=read_atoms(coordinate_path)
                            inventory=chain_inventory(atoms)
                            protein=polymer_sequences(coordinate_path)
                            row.update(structure_parse_status='strict_atoms_and_polymer_sequences_parsed',
                                       protein_sequences=protein,chain_heavy_atom_counts={k:v['heavy_atoms'] for k,v in inventory.items()},
                                       predicted_chain_entities={k:v['entities'] for k,v in inventory.items()})
                            sequences.update(protein.values())
                        except Exception as e:row.update(structure_parse_status='requires_review',structure_error=f'{type(e).__name__}: {e}')
                    except Exception as e:row.update(status='native_acquisition_audit_error',error=f'{type(e).__name__}: {e}')
                counts[model+'/'+row['status']]+=1
                handle.write(json.dumps(row)+'\n')
                if handle.tell()>28_000_000:raise RuntimeError('External native audit exceeds local cap')
    os.replace(part,output)
    summary={'raw_targets':len(targets),'model_target_pairs':2*len(targets),'status_counts':dict(counts),
             'unique_declared_protein_sequences_among_parsed_predictions':len(sequences),'experimental_outcomes_examined':False,
             'chemical_eligibility_verified':False,'final_eligible_count':None,
             'warning':'Acquisition/ranking verification is not chemical eligibility, model compatibility, independent-compound counting or accuracy evaluation.'}
    path=BASE/'manifests/openbind_native_verification_summary.json'
    path.write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
