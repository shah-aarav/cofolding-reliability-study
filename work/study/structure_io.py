"""Strict mmCIF atom reader preserving input-relevant chain and atom identities.

No nearest-pose chain selection, reference alignment, bond inference or automatic
ligand identity assignment is performed here. Ambiguous alternate conformers and
multiple models are rejected instead of silently selecting a favorable pose.
"""
from dataclasses import dataclass
from pathlib import Path
import math
import gemmi
import numpy as np

@dataclass(frozen=True)
class Atom:
    chain:str
    auth_chain:str
    entity:str
    residue:str
    sequence_id:str
    auth_sequence_id:str
    atom_name:str
    element:str
    position:tuple
    occupancy:float
    b_iso_or_equiv:float|None=None

def _column(block,name,count=None,default=None):
    values=list(block.find_values(name))
    if not values and count is not None and default is not None:return [default]*count
    if count is not None and len(values)!=count:raise ValueError('Missing/misaligned CIF column '+name)
    return values

def read_atoms(path,max_bytes=25_000_000):
    path=Path(path)
    if path.stat().st_size>max_bytes:raise ValueError('Structure exceeds reader budget')
    document=gemmi.cif.read_file(str(path))
    if len(document)!=1:raise ValueError('Exactly one mmCIF block required')
    block=document.sole_block()
    names=_column(block,'_atom_site.label_atom_id')
    count=len(names)
    if not count:raise ValueError('No atom_site records')
    columns={key:_column(block,'_atom_site.'+key,count) for key in
             ('label_asym_id','label_entity_id','label_comp_id','label_seq_id','type_symbol','Cartn_x','Cartn_y','Cartn_z')}
    for key,default in [('auth_asym_id','?'),('auth_seq_id','?'),('label_alt_id','.'),('occupancy','1'),('pdbx_PDB_model_num','1'),('B_iso_or_equiv','?')]:
        columns[key]=_column(block,'_atom_site.'+key,count,default)
    if len(set(columns['pdbx_PDB_model_num']))!=1:raise ValueError('Multiple coordinate models rejected')
    atoms=[]
    seen=set()
    for i,name in enumerate(names):
        if columns['label_alt_id'][i] not in ('.','?'):raise ValueError('Alternate atom locations require explicit policy')
        position=tuple(float(columns[key][i]) for key in ('Cartn_x','Cartn_y','Cartn_z'))
        occupancy=float(columns['occupancy'][i])
        b_raw=columns['B_iso_or_equiv'][i]
        b_value=None if b_raw in ('.','?') else float(b_raw)
        if b_value is not None and not math.isfinite(b_value):raise ValueError('Nonfinite B_iso_or_equiv value')
        if not all(math.isfinite(x) for x in position) or not math.isfinite(occupancy) or not 0<occupancy<=1:
            raise ValueError('Nonfinite/invalid atom coordinates or occupancy')
        atom=Atom(columns['label_asym_id'][i],columns['auth_asym_id'][i],columns['label_entity_id'][i],
                  columns['label_comp_id'][i],columns['label_seq_id'][i],columns['auth_seq_id'][i],
                  gemmi.cif.as_string(name),columns['type_symbol'][i].upper(),position,occupancy,b_value)
        key=(atom.chain,atom.sequence_id,atom.auth_sequence_id,atom.residue,atom.atom_name)
        if key in seen:raise ValueError('Duplicate atom identity')
        seen.add(key)
        atoms.append(atom)
    return atoms

def chain_inventory(atoms):
    result={}
    for atom in atoms:
        row=result.setdefault(atom.chain,{'entities':set(),'auth_chains':set(),'residues':set(),'elements':{},'heavy_atoms':0})
        row['entities'].add(atom.entity)
        row['auth_chains'].add(atom.auth_chain)
        row['residues'].add((atom.sequence_id,atom.auth_sequence_id,atom.residue))
        row['elements'][atom.element]=row['elements'].get(atom.element,0)+1
        row['heavy_atoms']+=atom.element not in ('H','D')
    return {chain:{**row,'entities':sorted(row['entities']),'auth_chains':sorted(row['auth_chains']),
                   'residues':sorted(row['residues'])} for chain,row in result.items()}

def coordinates(atoms):return np.asarray([a.position for a in atoms],dtype=float).reshape(-1,3)

def explicit_chain(atoms,chain):
    selected=[atom for atom in atoms if atom.chain==chain and atom.element not in ('H','D')]
    if not selected:raise ValueError('Explicit chain is missing or has no heavy atoms')
    return selected

def atom_plddt(atoms,verified_bfactor_plddt_source):
    """Only use B-column values after writer provenance confirms pLDDT encoding."""
    if not verified_bfactor_plddt_source:raise ValueError('B-column pLDDT provenance is required')
    selected=[a for a in atoms if a.element not in ('H','D')]
    if not selected or any(a.b_iso_or_equiv is None or not 0<=a.b_iso_or_equiv<=100 for a in selected):
        raise ValueError('Missing/out-of-range atom pLDDT')
    values=np.array([a.b_iso_or_equiv for a in selected])/100
    return {'heavy_atom_plddt_mean':float(values.mean()),'heavy_atom_plddt_min':float(values.min()),
            'heavy_atom_plddt_fraction_below_50':float((values<.5).mean()),'source':verified_bfactor_plddt_source}

def ca_correspondence(first,second,chain_pairs):
    """Use caller-verified sequence-equivalent chain pairs and exact label indices.

    This deliberately refuses substitutions, missing CAs and differing residue
    names; a future sequence-aligned path must supply an explicit residue map.
    """
    if not chain_pairs or len({a for a,b in chain_pairs})!=len(chain_pairs) or len({b for a,b in chain_pairs})!=len(chain_pairs):
        raise ValueError('Chain correspondence must be a nonempty bijection')
    moving=[]
    fixed=[]
    residue_map={}
    for chain_a,chain_b in chain_pairs:
        a={x.sequence_id:x for x in first if x.chain==chain_a and x.atom_name=='CA'}
        b={x.sequence_id:x for x in second if x.chain==chain_b and x.atom_name=='CA'}
        if not a or set(a)!=set(b) or any(a[k].residue!=b[k].residue for k in a):
            raise ValueError('CA residue identities differ; explicit sequence alignment required')
        for key in sorted(a,key=int):
            moving.append(a[key].position)
            fixed.append(b[key].position)
            residue_map[(chain_a,key)]=(chain_b,key)
    return np.asarray(moving),np.asarray(fixed),residue_map

def proximity_features(protein,ligand,cutoffs=(4.0,5.0),short_distance=1.2):
    """Reference-free descriptive distances, NOT a complete chemical validity test.

    Covalent ligands need separate treatment. No bond/stereochemistry validity is
    inferred from interatomic distances; cofactor selection stays explicit.
    """
    protein=[a for a in protein if a.element not in ('H','D')]
    ligand=[a for a in ligand if a.element not in ('H','D')]
    if not protein or not ligand or short_distance<=0 or any(x<=0 for x in cutoffs):raise ValueError('Invalid proximity input')
    p,l=coordinates(protein),coordinates(ligand)
    minima=np.full(len(ligand),np.inf)
    residues={cutoff:set() for cutoff in cutoffs}
    short_pairs=0
    for start in range(0,len(p),512):
        d2=((p[start:start+512,None,:]-l[None,:,:])**2).sum(axis=2)
        minima=np.minimum(minima,np.sqrt(d2.min(axis=0)))
        short_pairs+=int((d2<short_distance**2).sum())
        for cutoff in cutoffs:
            residues[cutoff].update((protein[start+i].chain,protein[start+i].sequence_id)
                                   for i in np.flatnonzero((d2<=cutoff**2).any(axis=1)))
    return {'minimum_protein_ligand_heavy_atom_distance':float(minima.min()),
            'ligand_heavy_atom_count':len(ligand),'protein_heavy_atom_count':len(protein),
            'short_distance_angstrom':short_distance,'short_distance_pair_count':short_pairs,
            'contact_residue_counts':{str(c):len(s) for c,s in residues.items()}}
