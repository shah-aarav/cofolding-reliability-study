"""Input-only external/main receptor relatedness; not model-training novelty."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from Bio import Align
from Bio.Align import substitution_matrices
from build_sequence_groups import alignment_stats

BASE=Path(__file__).resolve().parent

def main():
    main_sequences=defaultdict(set)
    for row in map(json.loads,(BASE/'manifests/candidates.jsonl').read_text().splitlines()):
        for chain,sequence in row['input_sequences'].items():
            if len(sequence)>=40:main_sequences[sequence].add(row['system_id'])
    external=set()
    for row in map(json.loads,(BASE/'manifests/openbind_native_verified.jsonl').read_text().splitlines()):
        external.update(row.get('protein_sequences',{}).values())
    aligner=Align.PairwiseAligner()
    aligner.mode='local';aligner.substitution_matrix=substitution_matrices.load('BLOSUM62')
    aligner.open_gap_score=-10;aligner.extend_gap_score=-.5
    reports=[]
    for sequence in sorted(external):
        hits=[]
        exact=[]
        for candidate,systems in main_sequences.items():
            if candidate==sequence:exact.extend(systems)
            alignments=aligner.align(sequence,candidate)
            if alignments.score<=0:continue
            stats=alignment_stats(alignments[0],sequence,candidate)
            if stats['identity']>=.3 and stats['shorter_coverage']>=.7:
                hits.append({'main_sequence_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'main_sequence_length':len(candidate),
                             'main_system_ids':sorted(systems),**stats})
        reports.append({'external_sequence_sha256':hashlib.sha256(sequence.encode()).hexdigest(),'external_sequence_length':len(sequence),
                        'exact_main_system_ids':sorted(set(exact)),'related_main_chains':hits})
    summary={'external_unique_declared_sequences_at_checkpoint':len(external),'main_unique_input_chains_ge40aa':len(main_sequences),
             'operational_relatedness':'best local BLOSUM62; identity over all aligned columns including gaps >=30%; paired-residue coverage >=70% of shorter chain',
             'sequence_reports':reports,'experimental_outcomes_examined':False,
             'interpretation':'Tests overlap with current calibration candidates only. Does NOT establish novelty relative to predictor training, complete family independence or absence of structural/ligand overlap.'}
    (BASE/'manifests/external_receptor_overlap.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({'external_sequences':len(external),'main_sequences_compared':len(main_sequences),
                      'exact_main_systems':sum(len(r['exact_main_system_ids']) for r in reports),
                      'related_main_sequence_hits':sum(len(r['related_main_chains']) for r in reports),'experimental_outcomes_examined':False},indent=2))

if __name__=='__main__':main()
