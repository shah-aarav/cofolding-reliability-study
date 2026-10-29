"""Input-sequence chain correspondence, independent of pose geometry/reference."""
from collections import defaultdict
from pathlib import Path
import gemmi
from structure_io import read_atoms

STANDARD={'ALA':'A','ARG':'R','ASN':'N','ASP':'D','CYS':'C','GLN':'Q','GLU':'E','GLY':'G','HIS':'H','ILE':'I',
          'LEU':'L','LYS':'K','MET':'M','PHE':'F','PRO':'P','SER':'S','THR':'T','TRP':'W','TYR':'Y','VAL':'V'}

def polymer_sequences(path):
    """Read full declared polypeptide entities, not a resolved-coordinate fragment.

    Atom-site entity IDs attach entity sequences to output label-asym IDs; this
    also works for Protenix files without a struct_asym category. Modified or
    ambiguous monomers remain unresolved rather than silently canonicalized.
    """
    path=Path(path)
    atoms=read_atoms(path)
    block=gemmi.cif.read_file(str(path)).sole_block()
    entities=list(block.find_values('_entity_poly.entity_id'))
    types=list(block.find_values('_entity_poly.type'))
    if len(entities)!=len(types):raise ValueError('Inconsistent entity_poly columns')
    protein={entity for entity,kind in zip(entities,types) if gemmi.cif.as_string(kind)=='polypeptide(L)'}
    ids=list(block.find_values('_entity_poly_seq.entity_id'))
    nums=list(block.find_values('_entity_poly_seq.num'))
    names=list(block.find_values('_entity_poly_seq.mon_id'))
    if not len(ids)==len(nums)==len(names):raise ValueError('Inconsistent entity_poly_seq columns')
    residues=defaultdict(dict)
    for entity,index,residue in zip(ids,nums,names):
        if entity not in protein:continue
        index=int(index)
        residue=gemmi.cif.as_string(residue)
        if index in residues[entity] or residue not in STANDARD:raise ValueError('Ambiguous/nonstandard input polymer monomer')
        residues[entity][index]=STANDARD[residue]
    sequences={}
    for entity,sequence in residues.items():
        if sorted(sequence)!=list(range(1,len(sequence)+1)):raise ValueError('Noncontiguous declared polymer sequence')
        sequences[entity]=''.join(sequence[i] for i in sorted(sequence))
    chain_entities=defaultdict(set)
    for atom in atoms:chain_entities[atom.chain].add(atom.entity)
    result={}
    for chain,assigned in chain_entities.items():
        if len(assigned)!=1:raise ValueError('Output chain has ambiguous entity identity')
        entity=next(iter(assigned))
        if entity in protein:
            if entity not in sequences:raise ValueError('Polypeptide entity sequence missing')
            result[chain]=sequences[entity]
    if not result:raise ValueError('No declared protein chains')
    return result

def unique_input_chain_map(input_sequences,output_sequences):
    if not input_sequences or not output_sequences:raise ValueError('Missing input/output sequence declarations')
    if len(input_sequences)!=len(output_sequences):raise ValueError('Protein chain multiplicities differ')
    assignments={}
    for input_chain,sequence in input_sequences.items():
        matches=[chain for chain,candidate in output_sequences.items() if candidate==sequence]
        if len(matches)!=1:raise ValueError('Missing or sequence-equivalent ambiguous output protein chain')
        assignments[input_chain]=matches[0]
    if len(set(assignments.values()))!=len(assignments):raise ValueError('Input sequence mapping is not bijective')
    return assignments

def paired_input_chain_map(input_sequences,first_sequences,second_sequences):
    first=unique_input_chain_map(input_sequences,first_sequences)
    second=unique_input_chain_map(input_sequences,second_sequences)
    return [(first[chain],second[chain]) for chain in sorted(input_sequences)]
