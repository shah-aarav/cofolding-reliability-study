"""Reconstruct reviewed RnP input-building order WITHOUT experimental assignment.

Boltz groups identical sequence/SMILES strings before expanding explicit chain
IDs. This can reorder ligand confidence indices relative to the original input
array even when the selected proper ligand occurs only once. Verify against raw
processed record or CIF provenance before using these plans as final features.
"""
from collections import OrderedDict
import string

def rnp_input_roles(input_sequences,input_smiles):
    total=len(input_sequences)+len(input_smiles)
    if not input_sequences or total>26:raise ValueError('Reviewed author input builder requires 1+ proteins and at most 26 chains')
    original=[]
    for index,(chain,sequence) in enumerate(input_sequences.items()):
        original.append({'kind':'protein','original_input_chain':chain,'sequence':sequence,
                         'declared_input_chain_id':string.ascii_uppercase[index],'input_order':index})
    for ligand_index,smiles in enumerate(input_smiles):
        index=len(input_sequences)+ligand_index
        original.append({'kind':'ligand','input_ligand_index':ligand_index,'smiles':smiles,
                         'declared_input_chain_id':string.ascii_uppercase[index],'input_order':index})
    protenix=[{**row,'confidence_chain_index':i,'input_entity_id':str(i+1)} for i,row in enumerate(original)]
    grouped=OrderedDict()
    for row in original:
        identity=(row['kind'],row.get('sequence',row.get('smiles')))
        grouped.setdefault(identity,[]).append(row)
    boltz=[]
    for entity_index,rows in enumerate(grouped.values()):
        for row in sorted(rows,key=lambda x:x['declared_input_chain_id']):
            boltz.append({**row,'confidence_chain_index':len(boltz),'input_entity_index':entity_index})
    return {'protenix':protenix,'boltz2':boltz}

def confidence_roles(role_rows,proper_input_ligand_index):
    proteins=[row['confidence_chain_index'] for row in role_rows if row['kind']=='protein']
    ligand=[row['confidence_chain_index'] for row in role_rows if row.get('input_ligand_index')==proper_input_ligand_index]
    if len(ligand)!=1:raise ValueError('Proper input ligand role unresolved')
    return proteins,ligand[0]
