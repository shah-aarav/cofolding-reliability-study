"""Selective-prediction evaluation primitives; real held-out evaluation is not enabled."""
import math
import numpy as np

def validate(labels,scores,identifiers):
    labels=np.asarray(labels)
    scores=np.asarray(scores,dtype=float)
    identifiers=np.asarray(identifiers,dtype=str)
    if labels.ndim!=1 or scores.shape!=labels.shape or identifiers.shape!=labels.shape or len(labels)==0:
        raise ValueError('Expected equally sized nonempty vectors')
    if not np.isin(labels,[0,1]).all() or not np.isfinite(scores).all():
        raise ValueError('Labels must be binary and scores finite')
    if len(set(identifiers))!=len(identifiers):
        raise ValueError('Duplicate scientific observations need explicit clone identifiers')
    return labels.astype(int),scores,identifiers

def retained_error(labels,scores,identifiers,coverage=0.5):
    labels,scores,identifiers=validate(labels,scores,identifiers)
    if not 0<coverage<=1:raise ValueError('Coverage must lie in (0,1]')
    count=math.ceil(coverage*len(labels))
    # Ranking and tie breaks have no dependence on correctness labels.
    retained=np.lexsort((identifiers,-scores))[:count]
    return {'error':float(1-labels[retained].mean()),'retained_count':count,
            'actual_coverage':count/len(labels),'retained_indices':retained}

def threshold_error(labels,probabilities,identifiers,threshold=0.9):
    labels,probabilities,identifiers=validate(labels,probabilities,identifiers)
    if not 0<=threshold<=1 or ((probabilities<0)|(probabilities>1)).any():
        raise ValueError('Expected probabilities and threshold in [0,1]')
    retained=probabilities>=threshold
    return {'coverage':float(retained.mean()),'retained_count':int(retained.sum()),
            'error':float(1-labels[retained].mean()) if retained.any() else None}

def paired_group_bootstrap(labels,baseline,augmented,identifiers,groups,coverage=0.5,replicates=2000,seed=20261026):
    labels,baseline,identifiers=validate(labels,baseline,identifiers)
    _,augmented,_=validate(labels,augmented,identifiers)
    groups=np.asarray(groups,dtype=str)
    if groups.shape!=labels.shape:raise ValueError('Missing group assignments')
    if any(not group.strip() or group in ('None','nan') for group in groups):raise ValueError('Empty/null group assignments')
    unique=sorted(set(groups))
    if len(unique)<2:raise ValueError('At least two groups required for group bootstrap')
    if replicates<20:raise ValueError('Too few bootstrap replicates')
    members={group:np.flatnonzero(groups==group) for group in unique}
    tie_rank={identifier:rank for rank,identifier in enumerate(sorted(identifiers))}
    base=retained_error(labels,baseline,identifiers,coverage)
    aug=retained_error(labels,augmented,identifiers,coverage)
    estimates=[]
    rng=np.random.default_rng(seed)
    for _ in range(replicates):
        draw=rng.choice(unique,size=len(unique),replace=True)
        indices=np.concatenate([members[group] for group in draw])
        # Repeatedly sampled groups receive clone IDs. Do not deduplicate them:
        # that would erase the resampling weights and invalidate the bootstrap.
        # Encode the ORIGINAL lexical rank first, not ID+suffix: a suffix can
        # reorder prefix-related IDs such as "a" and "a!". Widths derive from
        # this replicate so lexical and numeric rank order always agree.
        rank_width=len(str(len(identifiers)))
        clone_width=len(str(len(indices)))
        clone_ids=np.array([f'{tie_rank[identifiers[index]]:0{rank_width}d}:{j:0{clone_width}d}' for j,index in enumerate(indices)])
        b=retained_error(labels[indices],baseline[indices],clone_ids,coverage)['error']
        a=retained_error(labels[indices],augmented[indices],clone_ids,coverage)['error']
        estimates.append(100*(b-a))
    lower,upper=np.percentile(estimates,[2.5,97.5])
    return {'effect_percentage_points':100*(base['error']-aug['error']),
            'baseline_error':base['error'],'augmented_error':aug['error'],
            'retained_count':base['retained_count'],'actual_coverage':base['actual_coverage'],
            'ci95_percentage_points':[float(lower),float(upper)],'groups':len(unique),
            'systems':len(labels),'bootstrap_replicates':replicates,'seed':seed,
            'uncertainty_scope':'conditional on fitted rules; resample whole related-protein groups; recompute retention each replicate'}
