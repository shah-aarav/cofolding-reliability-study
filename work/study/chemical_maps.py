"""Exact graph-approved heavy-atom mappings; no coordinate-derived identity.

Templates and atom-name correspondence must be traced to verified predictor
inputs or a declared chemical component dictionary. Do not infer these from the
experimental pose. Failure/ambiguity is explicit, never a favorable atom order.
"""
from dataclasses import dataclass
from rdkit import Chem
import numpy as np

@dataclass
class NamedTemplate:
    molecule:object
    atom_names:tuple
    source:str

def checked_template(molecule,atom_names,source):
    if molecule is None or not source:raise ValueError('Chemical template/source missing')
    molecule=Chem.Mol(molecule)
    molecule.RemoveAllConformers()  # A template is chemistry, never a hidden pose.
    Chem.SanitizeMol(molecule)
    if any(atom.GetAtomicNum()==1 for atom in molecule.GetAtoms()):
        raise ValueError('Supply an explicitly indexed heavy-atom template, not implicit H removal')
    names=tuple(atom_names)
    if len(names)!=molecule.GetNumAtoms() or len(set(names))!=len(names) or any(not isinstance(n,str) or not n for n in names):
        raise ValueError('Template atom names must uniquely cover every heavy atom')
    return NamedTemplate(molecule,names,str(source))

def template_coordinates(template,atoms):
    atoms=[a for a in atoms if a.element not in ('H','D')]
    lookup={a.atom_name:a for a in atoms}
    if len(lookup)!=len(atoms) or set(lookup)!=set(template.atom_names):
        raise ValueError('Coordinate atoms do not exactly match verified heavy-atom template names')
    for i,name in enumerate(template.atom_names):
        if lookup[name].element!=template.molecule.GetAtomWithIdx(i).GetSymbol().upper():
            raise ValueError('Coordinate/template atom element mismatch')
    result=np.array([lookup[name].position for name in template.atom_names],dtype=float)
    if not np.isfinite(result).all():raise ValueError('Nonfinite ligand coordinates')
    return result

def exact_symmetry_maps(moving,fixed,max_maps=4096):
    """Return moving-template atom indices in fixed-template order.

    Exhaustive within a declared cap; do not silently minimize over a truncated
    mapping set. Exact isomeric graph identity rejects charge/stereo/isotope or
    aromaticity differences rather than silently normalizing them.
    """
    if type(max_maps) is not int or max_maps<1:raise ValueError('Invalid mapping cap')
    identity=lambda template:Chem.MolToSmiles(template.molecule,canonical=True,isomericSmiles=True)
    if identity(moving)!=identity(fixed):raise ValueError('Ligand chemical identities differ')
    matches=moving.molecule.GetSubstructMatches(fixed.molecule,uniquify=False,useChirality=True,maxMatches=max_maps+1)
    if len(matches)>max_maps:raise ValueError('Chemical automorphism count exceeds exhaustive mapping cap')
    if not matches:raise ValueError('No chirality-preserving exact atom correspondence')
    count=fixed.molecule.GetNumAtoms()
    if any(len(m)!=count or sorted(m)!=list(range(count)) for m in matches):raise ValueError('Chemical match is not bijective')
    return tuple(sorted(set(matches)))

def stereochemistry_flags(template):
    centers=Chem.FindMolChiralCenters(template.molecule,includeUnassigned=True,useLegacyImplementation=False)
    return {'assigned_tetrahedral_centers':sum(label!='?' for _,label in centers),
            'unassigned_tetrahedral_centers':sum(label=='?' for _,label in centers),
            'note':'Input graph stereochemistry only; coordinate stereochemistry validity is a separate check.'}
