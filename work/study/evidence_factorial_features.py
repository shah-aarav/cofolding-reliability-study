"""Outcome-free fixed-anchor support contrasts for the proposed factorial.

Inputs are measured anchor-to-opinion agreement, NOT experimental accuracy.
No pairwise RMSD is inferred from two anchor distances. Source/runner flags are
attestations to be backed by upstream artifacts, not proof provided by this code.
"""
import math
import re
from statistics import mean
from build_evidence_experiment_plan import BLOCKS

CELLS={'P0a':('protenix','V0'),'P0b':('protenix','V0'),'P1b':('protenix','V1'),
       'B0b':('boltz2','V0'),'B1b':('boltz2','V1')}
ARMS={'PP_shared':('P0a','P0b'),'PP_diverse':('P0a','P1b'),
      'PB_shared':('P0a','B0b'),'PB_diverse':('P0a','B1b')}


def finite(value,minimum=None,maximum=None):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Expected finite numeric measurement')
    if minimum is not None and value<minimum or maximum is not None and value>maximum:
        raise ValueError('Measurement outside declared range')
    return float(value)


def hash_id(value):
    if not isinstance(value,str) or re.fullmatch('[0-9a-f]{64}',value) is None:
        raise ValueError('Explicit artifact SHA256 required')
    return value


def summarize(records,expected_blocks=5):
    if type(expected_blocks) is not int or expected_blocks<1:raise ValueError('Prespecified positive block count required')
    cells={};identities=set();anchors=set()
    if expected_blocks>len(BLOCKS):raise ValueError('No prespecified seed schedule for requested blocks')
    required={'block','cell','model','view_sha256','system_input_sha256','anchor_coordinate_sha256',
              'native_selection_verified','experimental_reference_used','diffusion_seed',
              'anchor_ligand_rmsd','anchor_contact_jaccard','native_confidence'}
    for row in records:
        if set(row)!=required:raise ValueError('Unexpected/missing fields; pass only the declared outcome-free measurements')
        if row.get('experimental_reference_used') is not False or row.get('native_selection_verified') is not True:
            raise ValueError('Reference-free native-selection provenance required')
        if 'correctness' in row or 'outcome' in row:raise ValueError('Do not pass correctness labels to feature construction')
        block=row['block'];cell=row['cell']
        if type(block) is not int or not 0<=block<expected_blocks or cell not in CELLS:
            raise ValueError('Unexpected block/cell')
        if (block,cell) in cells:raise ValueError('Duplicate factorial cell')
        if row['model']!=CELLS[cell][0]:raise ValueError('Predictor identity does not match factorial cell')
        if row['diffusion_seed']!=BLOCKS[block][0 if cell=='P0a' else 1]:
            raise ValueError('Actual seed differs from prespecified experiment plan')
        identities.add(hash_id(row['system_input_sha256']));anchors.add(hash_id(row['anchor_coordinate_sha256']))
        hash_id(row['view_sha256'])
        if type(row['diffusion_seed']) is not int:raise ValueError('Actual integer diffusion seed required')
        copied=dict(row)
        copied['anchor_ligand_rmsd']=finite(row['anchor_ligand_rmsd'],0)
        copied['native_confidence']=finite(row['native_confidence'])  # A native score is not necessarily a probability.
        if row['anchor_contact_jaccard'] is not None:
            copied['anchor_contact_jaccard']=finite(row['anchor_contact_jaccard'],0,1)
        cells[(block,cell)]=copied
    if len(identities)!=1 or len(anchors)!=1:raise ValueError('Input or fixed anchor changed between cells')
    if len(cells)!=expected_blocks*len(CELLS):raise ValueError('Incomplete factorial; do not silently average available cells')
    profiles=[]
    for block in range(expected_blocks):
        rows={cell:cells[(block,cell)] for cell in CELLS}
        if len({rows[c]['view_sha256'] for c in ('P0a','P0b','B0b')})!=1:
            raise ValueError('Shared-evidence cells do not share the declared view')
        if rows['P1b']['view_sha256']!=rows['B1b']['view_sha256'] or rows['P1b']['view_sha256']==rows['P0a']['view_sha256']:
            raise ValueError('Diversified view assignment mismatch')
        if len({rows[c]['diffusion_seed'] for c in ('P0b','P1b','B0b','B1b')})!=1 or rows['P0a']['diffusion_seed']==rows['P0b']['diffusion_seed']:
            raise ValueError('Paired seed design changed')
        profile={}
        for arm,(first,second) in ARMS.items():
            profile[arm+'_anchor_distance_burden']=max(rows[first]['anchor_ligand_rmsd'],rows[second]['anchor_ligand_rmsd'])
            contacts=[rows[first]['anchor_contact_jaccard'],rows[second]['anchor_contact_jaccard']]
            profile[arm+'_anchor_contact_support']=min(contacts) if all(v is not None for v in contacts) else None
        for prefix in ('PP','PB'):
            shared=profile[prefix+'_shared_anchor_contact_support'];diverse=profile[prefix+'_diverse_anchor_contact_support']
            profile[prefix+'_contact_evidence_fragility']=None if shared is None or diverse is None else shared-diverse
            profile[prefix+'_distance_evidence_fragility']=profile[prefix+'_diverse_anchor_distance_burden']-profile[prefix+'_shared_anchor_distance_burden']
        p=profile['PP_contact_evidence_fragility'];b=profile['PB_contact_evidence_fragility']
        profile['contact_fragility_model_interaction']=None if p is None or b is None else b-p
        for cell in CELLS:profile[cell+'_native_confidence']=rows[cell]['native_confidence']
        profiles.append(profile)
    features={key:mean([p[key] for p in profiles]) if all(p[key] is not None for p in profiles) else None for key in profiles[0]}
    missing={key:sum(p[key] is None for p in profiles) for key in profiles[0]}
    return {'features':features,'blocks_with_missing_measurement':missing,'blocks_expected':expected_blocks,
            'system_input_sha256':next(iter(identities)),'anchor_coordinate_sha256':next(iter(anchors)),
            'experimental_reference_used':False,'scientific_accuracy_result':None,
            'information_scope':'Fragility contrasts are deterministic transforms of absolute support, not extra predictive information beyond those components. Test the new evidence views, not a supposedly information-creating subtraction.',
            'definition':'Support=min of two anchor-contact Jaccards; distance burden=max of two receptor-aligned anchor distances; positive fragility=less support after evidence diversification.',
            'limitation':'Anchor support is not direct opinion-opinion agreement. Provided view/native provenance needs upstream verification. No correctness or causal memorization conclusion.'}
