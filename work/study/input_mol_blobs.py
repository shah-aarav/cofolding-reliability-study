"""Extract inert RDKit binary data from a cache WITHOUT unpickling the cache.

pickletools disassembles only: no GLOBAL/REDUCE/BUILD opcode is evaluated, no
module named in a pickle is imported, and no callable from it is invoked. Only
byte operands with RDKit's binary-molecule signature reach its molecule DATA
parser. Conformers are discarded; input atom names/chemistry are retained.
"""
import hashlib
import pickletools
from rdkit import Chem
from chemical_maps import checked_template

MAGIC=bytes.fromhex('efbeadde00000000')

def templates_from_inert_cache_bytes(raw,source,max_bytes=2_000_000,max_ops=100_000,max_molecules=64):
    if not source or len(raw)>max_bytes:raise ValueError('Missing input-cache provenance or byte budget exceeded')
    blobs=[]
    for count,(opcode,argument,position) in enumerate(pickletools.genops(raw),start=1):
        if count>max_ops:raise ValueError('Input-cache disassembly operation budget exceeded')
        if isinstance(argument,bytes) and argument.startswith(MAGIC):
            blobs.append(argument)
            if len(blobs)>max_molecules:raise ValueError('Input-cache molecule budget exceeded')
    if not blobs:raise ValueError('No inert RDKit binary molecule operands found')
    templates=[]
    for index,blob in enumerate(blobs):
        molecule=Chem.Mol(blob)  # RDKit binary graph parser, NOT pickle.loads.
        if molecule is None or not 1<=molecule.GetNumAtoms()<=512:raise ValueError('Invalid/oversized input molecular graph')
        if any(not atom.HasProp('name') for atom in molecule.GetAtoms()):raise ValueError('Input atom-name property missing')
        names=[atom.GetProp('name') for atom in molecule.GetAtoms()]
        template=checked_template(molecule,names,f'{source}#inert-rdkit-blob-{index};sha256={hashlib.sha256(blob).hexdigest()}')
        templates.append(template)
    return templates
