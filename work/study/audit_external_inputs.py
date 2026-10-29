"""Full raw-intersection Boltz input provenance, without experimental outcomes.

Reads only selected-seed processed records/molecular graphs/numeric structures.
Never unpickles caches or uses their conformers. Does not establish Protenix
input identity, chemical eligibility, reference matching or scientific accuracy.
"""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
from rdkit import Chem
from chain_mapping import polymer_sequences, STANDARD
from chemical_maps import template_coordinates
from collect_openbind import fetch_rows
from input_mol_blobs import templates_from_inert_cache_bytes
from predictor_templates import named_graph_signature
from safe_npz import read_npz_arrays
from storage import guard
from structure_io import read_atoms, explicit_chain

BASE=Path(__file__).resolve().parent
CUTOFF=datetime(2026,10,27,13,tzinfo=timezone.utc).timestamp()
CAP=100_000_000


def match_processed_input(templates, arrays, record, atoms, sequences):
    chains=arrays['chains']; residues=arrays['residues']; source_atoms=arrays['atoms']
    if len(chains)!=len(record['chains']):raise ValueError('Processed record chain count differs from NPZ')
    if len(set(str(c['name']) for c in chains))!=len(chains):raise ValueError('Duplicate processed chain names')
    if set(str(c['name']) for c in chains)!={a.chain for a in atoms}:raise ValueError('Raw output chain names differ from processed input')
    proteins={}
    ligand_chains=[]
    for chain,declared in zip(chains,record['chains']):
        name=str(chain['name'])
        if (name,int(chain['asym_id']),int(chain['entity_id']),int(chain['mol_type'])) != (
            declared['chain_name'],declared['chain_id'],declared['entity_id'],declared['mol_type']):
            raise ValueError('Record/NPZ chain identity or ordering mismatch')
        start,count=int(chain['atom_idx']),int(chain['atom_num'])
        rs,rc=int(chain['res_idx']),int(chain['res_num'])
        if min(start,count,rs,rc)<0 or start+count>len(source_atoms) or rs+rc>len(residues):
            raise ValueError('Processed chain slices exceed arrays')
        if count<1 or rc<1:raise ValueError('Empty processed chain')
        expected=list(map(str,source_atoms[start:start+count]['name']))
        observed=[a.atom_name for a in explicit_chain(atoms,name)]
        if len(set(expected))!=len(expected) and int(chain['mol_type'])==3:
            raise ValueError('Repeated atom names within nonpolymer chain')
        if Counter(expected)!=Counter(observed):raise ValueError('Raw atom names differ from processed input')
        if int(chain['mol_type'])==0:
            try:sequence=''.join(STANDARD[str(r['name'])] for r in residues[rs:rs+rc])
            except KeyError:raise ValueError('Nonstandard processed protein sequence')
            if sequences.get(name)!=sequence:raise ValueError('Processed/raw protein sequences differ')
            proteins[name]=int(chain['asym_id'])
        elif int(chain['mol_type'])==3:
            ligand_chains.append((name,int(chain['asym_id']),set(expected)))
        else:raise ValueError('Unresolved non-protein/non-ligand molecule type')
    if set(proteins)!=set(sequences):raise ValueError('Unexpected protein declaration')
    carbon=[t for t in templates if any(a.GetAtomicNum()==6 for a in t.molecule.GetAtoms())]
    if len(carbon)!=1:raise ValueError('Input does not have exactly one carbon-containing cache molecule')
    template=carbon[0]
    matches=[(name,index) for name,index,names in ligand_chains if names==set(template.atom_names)]
    if len(matches)!=1:raise ValueError('Input organic molecule chain ambiguous or absent')
    name,index=matches[0]
    template_coordinates(template,explicit_chain(atoms,name))
    return {'proper_ligand_chain':name,'ligand_confidence_index':index,
            'protein_confidence_indices':sorted(proteins.values()),
            'input_isomeric_smiles':Chem.MolToSmiles(template.molecule,canonical=True,isomericSmiles=True),
            'input_named_graph_sha256':hashlib.sha256(json.dumps(named_graph_signature(template),sort_keys=True).encode()).hexdigest(),
            'input_ligand_heavy_atoms':template.molecule.GetNumAtoms(),
            'input_constraints':record.get('inference_options'),
            'input_templates_declared':record.get('templates')}


def main():
    guard(CAP)
    output=BASE/'data/openbind/input_audit'; output.mkdir(exist_ok=True)
    native=BASE/'data/openbind/native_top/boltz2'
    metadata={p.stem:json.loads(p.read_text()) for p in sorted(native.glob('*.json'))}
    wanted={}
    for target,meta in metadata.items():
        prefix=f"run_boltz2_monomer/results/{target}/seed_{meta['selection']['seed']}/boltz_results_{target}_inp/processed/"
        for folder,suffix in [('records','.json'),('structures','.npz'),('mols','.pkl')]:
            wanted[prefix+folder+'/'+target+'_inp'+suffix]=(target,suffix)
    release=json.loads((BASE/'sources/openbind_record.json').read_text())
    archive=next(r for r in release['files'] if r['key']=='zip_run_boltz2_monomer.zip')
    rows={target:{} for target in metadata}
    with gzip.open(BASE/'manifests/openbind_boltz2_full_zip_index.jsonl.gz','rt',encoding='utf-8') as stream:
        for line in stream:
            row=json.loads(line)
            if row['name'] in wanted:
                target,suffix=wanted[row['name']]
                if suffix in rows[target]:raise ValueError('Duplicate indexed processed member')
                rows[target][suffix]={**row,'archive_url':archive['links']['self'],'archive_size':archive['size']}
    counts=Counter(); network=0
    status_path=BASE/'manifests/external_input_audit_status.json'
    if status_path.exists():
        (BASE/'manifests/external_input_audit_previous_status.json').write_text(status_path.read_text())
    def checkpoint(status,error=None):
        state={'status':status,'time_utc':datetime.now(timezone.utc).isoformat(),'targets_requested':len(metadata),
               'status_counts':dict(counts),'network_bytes_reserved_this_run':network,
               'experimental_outcomes_examined':False,'protenix_input_identity_verified':False,
               'final_eligible_count':None,'error':error}
        part=status_path.with_suffix('.part');part.write_text(json.dumps(state,indent=2));os.replace(part,status_path)
        print(json.dumps(state),flush=True)
    checkpoint('running')
    for target,meta in metadata.items():
        if time.time()>=CUTOFF:checkpoint('morning_cutoff');return
        result_path=output/(target+'.json')
        if result_path.exists():
            previous=json.loads(result_path.read_text())
            if (previous.get('status')=='boltz_processed_input_correspondence_verified'
                and previous.get('selected_seed')==meta['selection']['seed']
                and previous.get('raw_coordinate_sha256')==meta['coordinate_integrity']['sha256']):
                if all((output/p['local_name']).exists() and hashlib.sha256((output/p['local_name']).read_bytes()).hexdigest()==p['sha256'] for p in previous['processed_members']):
                    counts['verified_reused']+=1;continue
        result={'target':target,'selected_seed':meta['selection']['seed'],'experimental_outcomes_examined':False,
                'protenix_input_identity_verified':False,'chemical_eligibility_verified':False}
        try:
            if set(rows[target])!={'.json','.npz','.pkl'}:raise ValueError('Selected-seed processed input members incomplete')
            # One whole-workspace reservation before retrieval covers all three
            # <=2MB decompressed members plus a bounded metadata record. Repeating
            # a full dependency-tree scan before each member costs ~7s per scan.
            guard(8_000_000)
            if network+1_500_000>2_000_000_000:raise RuntimeError('Run network reservation cap reached')
            network+=1_500_000  # Reserve even failed requests, including three bounded attempts.
            members,reserved=fetch_rows(list(rows[target].values()),max_span=500_000)
            proofs=[]; paths={}
            for suffix,row in rows[target].items():
                data,proof=members[row['name']]
                if len(data)>2_000_000:raise ValueError('Processed member exceeds cap')
                if sum(p.stat().st_size for p in output.iterdir() if p.is_file())+len(data)>CAP:raise RuntimeError('Retained input audit cap reached')
                path=output/(target+'.processed'+suffix)
                part=path.with_suffix(path.suffix+'.part');part.write_bytes(data);os.replace(part,path)
                paths[suffix]=path
                proofs.append({'archive_member':row['name'],'local_name':path.name,**proof})
            record=json.loads(paths['.json'].read_text())
            if record['id']!=target+'_inp':raise ValueError('Processed input target ID mismatch')
            templates=templates_from_inert_cache_bytes(paths['.pkl'].read_bytes(),'selected-seed processed cache; CRC/SHA256 verified')
            arrays=read_npz_arrays(paths['.npz'],{'atoms','residues','chains'})
            coordinate=native/(target+'.cif')
            if hashlib.sha256(coordinate.read_bytes()).hexdigest()!=meta['coordinate_integrity']['sha256']:
                raise ValueError('Raw native coordinate checksum changed')
            features=match_processed_input(templates,arrays,record,read_atoms(coordinate),polymer_sequences(coordinate))
            result.update(status='boltz_processed_input_correspondence_verified',processed_members=proofs,
                          raw_coordinate_sha256=meta['coordinate_integrity']['sha256'],**features)
        except Exception as error:
            result.update(status='unresolved_input_provenance',reason=f'{type(error).__name__}: {error}')
        encoded=json.dumps(result,indent=2)
        if len(encoded.encode())>1_000_000:raise RuntimeError('Input audit metadata exceeds reservation')
        part=result_path.with_suffix('.json.part');part.write_text(encoded);os.replace(part,result_path)
        counts[result['status']]+=1
        if sum(counts.values())%10==0:checkpoint('running')
    checkpoint('completed_full_intersection_input_audit')


if __name__=='__main__':main()
