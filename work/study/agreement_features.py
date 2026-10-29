"""Reference-free two-predictor agreement after EXPLICIT input correspondence.

No experimental structure or correctness score is accepted by this interface.
Caller must independently establish chain/template provenance, never use an
experimentally favorable match to populate these arguments.
"""
import numpy as np
from chemical_maps import template_coordinates,exact_symmetry_maps
from geometry import rigid_fit,mapped_rmsd,residue_contacts,contact_jaccard
from structure_io import ca_correspondence,explicit_chain,coordinates,proximity_features

def measure_agreement(moving_atoms,fixed_atoms,chain_pairs,moving_ligand_chain,fixed_ligand_chain,
                      moving_template,fixed_template,correspondence_source,cutoffs=(4.0,5.0),max_maps=4096):
    if not isinstance(correspondence_source,str) or not correspondence_source.strip():
        raise ValueError('Input-defined correspondence provenance is required')
    first_chains={a for a,b in chain_pairs}
    second_chains={b for a,b in chain_pairs}
    if moving_ligand_chain in first_chains or fixed_ligand_chain in second_chains:
        raise ValueError('Ligand and receptor chain roles overlap')
    moving_ca,fixed_ca,residue_map=ca_correspondence(moving_atoms,fixed_atoms,chain_pairs)
    rotation,translation=rigid_fit(moving_ca,fixed_ca)
    first_ligand=explicit_chain(moving_atoms,moving_ligand_chain)
    second_ligand=explicit_chain(fixed_atoms,fixed_ligand_chain)
    first_xyz=template_coordinates(moving_template,first_ligand)
    second_xyz=template_coordinates(fixed_template,second_ligand)
    maps=exact_symmetry_maps(moving_template,fixed_template,max_maps=max_maps)
    first_protein=[a for a in moving_atoms if a.chain in first_chains and a.element not in ('H','D')]
    second_protein=[a for a in fixed_atoms if a.chain in second_chains and a.element not in ('H','D')]
    if any((a.chain,a.sequence_id) not in residue_map for a in first_protein):
        raise ValueError('Receptor heavy atom lacks verified residue correspondence')
    fixed_residues=set(residue_map.values())
    if any((a.chain,a.sequence_id) not in fixed_residues for a in second_protein):
        raise ValueError('Fixed receptor heavy atom lacks verified residue correspondence')
    features={'receptor_aligned_ligand_rmsd':mapped_rmsd(first_xyz@rotation+translation,second_xyz,maps),
              'aligned_receptor_ca_rmsd':float(np.sqrt(np.mean(((moving_ca@rotation+translation-fixed_ca)**2).sum(axis=1)))),
              'receptor_ca_correspondences':len(moving_ca),'chemical_symmetry_maps':len(maps)}
    for cutoff in cutoffs:
        first=residue_contacts(coordinates(first_protein),[(a.chain,a.sequence_id) for a in first_protein],first_xyz,cutoff)
        second=residue_contacts(coordinates(second_protein),[(a.chain,a.sequence_id) for a in second_protein],second_xyz,cutoff)
        translated={residue_map[residue] for residue in first}
        features[f'contact_jaccard_{cutoff:g}A']=contact_jaccard(translated,second)
        features[f'moving_contact_residues_{cutoff:g}A']=len(first)
        features[f'fixed_contact_residues_{cutoff:g}A']=len(second)
    return {'agreement':features,'moving_proximity':proximity_features(first_protein,first_ligand,cutoffs),
            'fixed_proximity':proximity_features(second_protein,second_ligand,cutoffs),
            'correspondence_source':correspondence_source,'moving_template_source':moving_template.source,
            'fixed_template_source':fixed_template.source,'experimental_reference_used':False,
            'limitations':'Exact residue-index CA correspondence only; no automatic chain ambiguity resolution or complete chemical-validity assessment.'}
