"""Reproduce reviewed SMILES atom-name rules, without predicting any coordinates.

Protenix v0.3.4/v1.0.0: per-element counters in parsed SMILES atom order.
Boltz v2.0.3: element + canonical atom rank on the explicit-H molecule, then H
removal. Input SMILES order is preserved, NEVER replaced by canonical SMILES.
RDKit version sensitivity still needs audit against saved raw input caches.
"""
from collections import Counter
from rdkit import Chem,rdBase
from chemical_maps import checked_template

PARSER_SOURCES={
 'protenix':'https://github.com/bytedance/Protenix/blob/74f9f909b1b5cbb33a4eec920bd2484924493340/protenix/data/json_parser.py',
 'boltz2':'https://github.com/jwohlwend/boltz/blob/01594f4713266f553e94bf8477306360667f0d99/src/boltz/data/parse/schema.py'}

def smiles_template(model,smiles,input_source):
    if model not in PARSER_SOURCES or not input_source:raise ValueError('Verified predictor/input source required')
    molecule=Chem.MolFromSmiles(smiles)
    if molecule is None:raise ValueError('Invalid input SMILES')
    if any(atom.GetAtomicNum()==1 for atom in molecule.GetAtoms()):raise ValueError('Explicit/isotopic hydrogen input needs a separate audited policy')
    molecule=Chem.AddHs(molecule)
    if model=='protenix':
        counts=Counter()
        names=[]
        for atom in molecule.GetAtoms():
            element=atom.GetSymbol().upper()
            counts[element]+=1
            names.append(f'{element}{counts[element]}')
    else:
        ranks=Chem.CanonicalRankAtoms(molecule)
        names=[atom.GetSymbol().upper()+str(rank+1) for atom,rank in zip(molecule.GetAtoms(),ranks)]
    for atom,name in zip(molecule.GetAtoms(),names):atom.SetProp('name',name)
    molecule=Chem.RemoveHs(molecule,sanitize=False)
    names=[atom.GetProp('name') for atom in molecule.GetAtoms()]
    return checked_template(molecule,names,f'{input_source}; naming={PARSER_SOURCES[model]}; rdkit={rdBase.rdkitVersion}')

def named_graph_signature(template):
    atoms=sorted((name,atom.GetSymbol(),atom.GetFormalCharge(),atom.GetIsotope()) for name,atom in zip(template.atom_names,template.molecule.GetAtoms()))
    bonds=sorted((min(template.atom_names[b.GetBeginAtomIdx()],template.atom_names[b.GetEndAtomIdx()]),
                  max(template.atom_names[b.GetBeginAtomIdx()],template.atom_names[b.GetEndAtomIdx()]),str(b.GetBondType()))
                 for b in template.molecule.GetBonds())
    return {'atoms':atoms,'bonds':bonds}
