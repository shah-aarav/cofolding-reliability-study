"""Full input-only atom-naming compatibility audit across isolated RDKit versions."""
import argparse
import hashlib
import json
from pathlib import Path
from rdkit import rdBase,Chem
from predictor_templates import smiles_template,named_graph_signature
from storage import guard

BASE=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--compare',action='store_true')
    args=parser.parse_args()
    if args.compare:
        tables={version:{r['input_smiles_sha256']:r for r in map(json.loads,(BASE/'manifests'/f'template_names_rdkit_{version}.jsonl').read_text().splitlines())}
                for version in ('2024.09.6','2026.09.1')}
        if set(tables['2024.09.6'])!=set(tables['2026.09.1']):raise ValueError('Compatibility inventories differ in input identities')
        differences=[]
        identical={model:0 for model in ('protenix','boltz2')}
        unresolved=[]
        for key in sorted(tables['2024.09.6']):
            a,b=(tables[version][key] for version in ('2024.09.6','2026.09.1'))
            if 'error' in a or 'error' in b:
                unresolved.append({'input_smiles_sha256':key,'old_error':a.get('error'),'new_error':b.get('error')});continue
            for model in identical:
                if a['named_graphs'][model]==b['named_graphs'][model]:identical[model]+=1
                else:differences.append({'input_smiles_sha256':key,'model':model})
        summary={'unique_input_smiles':len(tables['2024.09.6']),'identical_named_graph_counts':identical,'differences':differences,
                 'unresolved':unresolved,'outcomes_examined':False,
                 'caveat':'The 2024.09.6 version is reported by the benchmark analysis environment, not independently established for every predictor run. This audit tests naming stability, not full model provenance.'}
        (BASE/'manifests/template_naming_compatibility.json').write_text(json.dumps(summary,indent=2))
        print(json.dumps(summary,indent=2));return
    guard(15_000_000)
    rows=[json.loads(line) for line in (BASE/'manifests/candidates.jsonl').read_text().splitlines()]
    smiles=sorted({s for row in rows for s in row['input_smiles']})
    out=BASE/'manifests'/f'template_names_rdkit_{rdBase.rdkitVersion}.jsonl'
    errors=0
    with out.open('w',encoding='utf-8') as handle:
        for text in smiles:
            row={'input_smiles_sha256':hashlib.sha256(text.encode()).hexdigest(),'rdkit_version':rdBase.rdkitVersion}
            try:
                templates={model:smiles_template(model,text,'released input inventory') for model in ('protenix','boltz2')}
                row['named_graphs']={model:named_graph_signature(template) for model,template in templates.items()}
                row['canonical_isomeric_smiles']=Chem.MolToSmiles(templates['protenix'].molecule,canonical=True,isomericSmiles=True)
            except Exception as e:row['error']=f'{type(e).__name__}: {e}';errors+=1
            handle.write(json.dumps(row)+'\n')
            if handle.tell()>12_000_000:raise RuntimeError('Template compatibility inventory exceeded budget')
    print(json.dumps({'rdkit_version':rdBase.rdkitVersion,'unique_input_smiles':len(smiles),'errors':errors,'manifest_bytes':out.stat().st_size}))

if __name__=='__main__':main()
