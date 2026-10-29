"""Predicted heavy-atom environment for distance/volume validity checks.

No geometry is optimized and no bonds are inferred. Protein/cofactor roles come
from explicit verified chain roles. This mirrors a protein PDB loaded with
proximity bonding disabled, while avoiding PDB chain-name/precision truncation.
"""
from rdkit import Chem

def environment_molecule(atoms,protein_chains,excluded_ligand_chain,role_source):
    protein_chains=set(protein_chains)
    if not role_source or not protein_chains or excluded_ligand_chain in protein_chains:
        raise ValueError('Explicit nonoverlapping predicted environment roles required')
    all_chains={a.chain for a in atoms}
    if not protein_chains<=all_chains or excluded_ligand_chain not in all_chains:raise ValueError('Declared environment chain missing')
    selected=[a for a in atoms if a.chain!=excluded_ligand_chain and a.element not in ('H','D')]
    if not selected:raise ValueError('Empty predicted environment')
    molecule=Chem.RWMol()
    residues={}
    for index,record in enumerate(selected):
        atom=Chem.Atom(record.element.capitalize())
        atom.SetNoImplicit(True)
        identity=(record.chain,record.sequence_id,record.auth_sequence_id,record.residue)
        if identity not in residues:residues[identity]=len(residues)+1
        info=Chem.AtomPDBResidueInfo()
        info.SetName(record.atom_name.rjust(4))
        info.SetResidueName(record.residue)
        info.SetResidueNumber(residues[identity])
        info.SetChainId(record.chain)
        info.SetIsHeteroAtom(record.chain not in protein_chains)
        info.SetSerialNumber(index+1)
        atom.SetMonomerInfo(info)
        molecule.AddAtom(atom)
    molecule=molecule.GetMol()
    conformer=Chem.Conformer(len(selected))
    conformer.Set3D(True)
    for index,record in enumerate(selected):conformer.SetAtomPosition(index,record.position)
    molecule.AddConformer(conformer,assignId=True)
    molecule.SetProp('_Name','predicted_environment_no_inferred_bonds')
    molecule.SetProp('role_source',role_source)
    molecule.UpdatePropertyCache(strict=False)
    return molecule
