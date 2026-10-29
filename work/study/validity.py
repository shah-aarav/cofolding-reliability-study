"""Input-template geometry plus reference-free PoseBusters checks.

This is NOT the reference-based PB-valid endpoint. It uses the predicted
receptor/cofactors, never mol_true, and preserves each original ligand geometry.
Graph validity reflects the input chemistry, not bonds newly predicted by a
cofolding model. Missing checks never become an automatic pass.
"""
import hashlib
import importlib.metadata
import inspect
import json
import numpy as np
from rdkit import Chem
from posebusters import PoseBusters
from chemical_maps import template_coordinates

def posed_template(template,atoms):
    positions=template_coordinates(template,atoms)
    mol=Chem.Mol(template.molecule)
    mol.RemoveAllConformers()
    conformer=Chem.Conformer(mol.GetNumAtoms())
    conformer.Set3D(True)
    for i,position in enumerate(positions):conformer.SetAtomPosition(i,position.tolist())
    mol.AddConformer(conformer,assignId=True)
    return mol

def coordinate_stereochemistry(template,molecule):
    expected=Chem.Mol(template.molecule)
    Chem.AssignStereochemistry(expected,cleanIt=True,force=True)
    observed=Chem.Mol(molecule)
    Chem.RemoveStereochemistry(observed)
    Chem.AssignStereochemistryFrom3D(observed,confId=0,replaceExistingTags=True)
    Chem.AssignStereochemistry(observed,cleanIt=True,force=True)
    atoms=[]
    for atom in expected.GetAtoms():
        if not atom.HasProp('_CIPCode'):continue
        other=observed.GetAtomWithIdx(atom.GetIdx())
        actual=other.GetProp('_CIPCode') if other.HasProp('_CIPCode') else None
        desired=atom.GetProp('_CIPCode')
        atoms.append({'input_atom_index':atom.GetIdx(),'expected':desired,'observed':actual,'matches':desired==actual})
    bonds=[]
    for bond in expected.GetBonds():
        desired=str(bond.GetStereo())
        if desired not in ('STEREOE','STEREOZ'):continue
        actual=str(observed.GetBondWithIdx(bond.GetIdx()).GetStereo())
        bonds.append({'input_bond_index':bond.GetIdx(),'expected':desired,'observed':actual,'matches':desired==actual})
    checks=atoms+bonds
    return {'specified_stereo_elements':len(checks),'matches_specified_input_stereo':all(c['matches'] for c in checks) if checks else None,
            'atom_checks':atoms,'bond_checks':bonds,'note':'None means no specified supported stereo element, not a positive validation.'}

def strict_binary_report(frame,expected_columns):
    if len(frame)!=1 or len(frame.columns)!=len(set(frame.columns)) or set(frame.columns)!=set(expected_columns):
        raise ValueError('PoseBusters report is empty, duplicated, incomplete or not exactly one pose')
    result={}
    missing=[]
    for column in expected_columns:
        value=frame.iloc[0][column]
        if isinstance(value,(bool,np.bool_)):result[column]=bool(value)
        else:missing.append(column)
    return {'checks':result,'missing_checks':missing,'all_checks_pass':all(result.values()) if not missing else None,
            'failed_checks':[name for name,value in result.items() if not value]}

def reference_free_validity(template,ligand_atoms,predicted_environment):
    if predicted_environment is None:raise ValueError('Predicted environment required, never silently use an experimental receptor')
    molecule=posed_template(template,ligand_atoms)
    buster=PoseBusters(config='dock',max_workers=0)
    for module in buster.config['modules']:
        if module['function']=='energy_ratio':module.setdefault('parameters',{})['num_threads']=1
    buster._initialize_modules()
    for name,args in zip(buster.fname,buster.module_args):
        if name!='loading' and 'mol_true' in args:raise ValueError('Reference-dependent module in reference-free configuration')
    config_hash=hashlib.sha256(json.dumps(buster.config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    expected=[]
    for module in buster.config['modules']:
        for name in module.get('chosen_binary_test_output',[]):
            renamed=module.get('rename_outputs',{}).get(name,name+module.get('rename_suffix',''))
            expected.append(renamed.lower().replace(' ','_'))
    frame=buster.bust(molecule,mol_true=None,mol_cond=predicted_environment,full_report=False)
    report=strict_binary_report(frame,expected)
    report.update(coordinate_stereochemistry=coordinate_stereochemistry(template,molecule),
                  posebusters_version=importlib.metadata.version('posebusters'),config_name='dock_energy_single_thread',config_sha256=config_hash,
                  chemical_template_source=template.source,experimental_reference_used=False,
                  note='Reference-free predicted-environment checks; not equivalent to experimental-receptor PB-valid benchmark labels.')
    return report
