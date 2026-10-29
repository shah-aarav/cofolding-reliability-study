"""Inventory full-cohort candidates using inputs/metadata, never outcome values."""
import csv
import hashlib
import io
import json
import tarfile
from collections import defaultdict
from pathlib import Path
from storage import guard

BASE = Path(__file__).resolve().parent

def collect_score_index(archive):
    summaries = {}
    indices = {}
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith('.csv'):
                continue
            if member.size > 100_000_000:
                raise ValueError('Unexpected score table size')
            name = Path(member.name).stem
            counts = defaultdict(int)
            methods = set()
            top = {}
            with io.TextIOWrapper(tar.extractfile(member), encoding='utf-8-sig') as handle:
                reader = csv.DictReader(handle)
                columns = reader.fieldnames
                count = 0
                for row in reader:
                    # Outcome and reference-guided fields are deliberately never accessed.
                    target = row['target']
                    methods.add(row.get('method', ''))
                    counts[target] += 1
                    count += 1
                    raw_score = row.get('ranking_score', '')
                    try:
                        score = float(raw_score)
                    except (ValueError, TypeError):
                        continue
                    if not (-float('inf') < score < float('inf')):
                        continue
                    selection = (row.get('seed',''), row.get('sample',''))
                    value = {'seed': selection[0], 'sample': selection[1], 'ranking_score': score}
                    previous = top.get(target)
                    if previous is None or (-score, selection) < (-previous['ranking_score'], (previous['seed'], previous['sample'])):
                        top[target] = value
            summaries[name] = {'rows':count, 'targets':len(counts), 'method_labels':sorted(methods), 'schema':columns, 'selection_status':'provisional native ranking; tie rule and raw provenance require verification'}
            indices[name] = {'counts':counts, 'top':top}
    return summaries, indices

def main():
    guard(20_000_000)
    inputs = json.loads((BASE/'data/rnp/inputs.json').read_text(encoding='utf-8'))
    annotations = defaultdict(list)
    with (BASE/'data/rnp/annotations.csv').open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            annotations[row['system_id']].append(row)
    summaries, indices = collect_score_index(BASE/'data/rnp/predictions.tar.gz')
    common = sorted(set(indices['boltz2']['counts']) & set(indices['protenix']['counts']))
    out = BASE/'manifests'
    out.mkdir(exist_ok=True)
    with (out/'candidates.jsonl').open('w',encoding='utf-8') as handle:
        for target in common:
            source = inputs.get(target, {})
            seqs = source.get('sequences', {})
            seqhash = hashlib.sha256(json.dumps(sorted(seqs.values()),separators=(',',':')).encode()).hexdigest()
            proper = [r for r in annotations.get(target,[]) if r.get('ligand_is_proper','').lower() in ('true','1')]
            record = {'system_id':target,'input_present':target in inputs,'annotation_rows':len(annotations.get(target,[])), 'proper_ligand_rows':len(proper),'proper_ligand_smiles':sorted(set(r.get('ligand_smiles','') for r in proper)), 'input_sequences':seqs, 'input_smiles':source.get('smiles',[]),'input_ccd_codes':source.get('ccd_codes',[]),'identical_sequence_hash':seqhash,'grouping_status':'exact-sequence hash only; not final sequence-family grouping','protenix_selection':indices['protenix']['top'].get(target),'boltz2_selection':indices['boltz2']['top'].get(target),'eligibility':'candidate only; raw coordinate and chemical mapping pending'}
            handle.write(json.dumps(record)+'\n')
    summary = {'input_systems':len(inputs),'annotated_systems':len(annotations),'unannotated_input_ids':sorted(set(inputs)-set(annotations)), 'protenix_boltz2_candidate_intersection':len(common),'score_tables':summaries,'accuracy_labels_examined':False,'final_eligible_count':None,'model_versions_compatible':None}
    (out/'cohort_audit.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='score_tables'},indent=2))
    print(json.dumps(guard()))

if __name__ == '__main__':
    main()
