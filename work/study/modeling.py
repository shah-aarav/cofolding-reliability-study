"""Grouped fixed-rule model fitting primitives, currently tested on SYNTHETIC data.

No real outcome file is read here. The final file-based evaluation runner must
require protocol_gate.require_frozen_protocol before loading real labels.
Hyperparameters below are implementation defaults, NOT a frozen study choice.
"""
from dataclasses import dataclass
import warnings
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

def validate_partitions(groups,folds):
    groups=np.asarray(groups,dtype=str)
    folds=np.asarray(folds)
    if groups.ndim!=1 or folds.shape!=groups.shape or not len(groups):raise ValueError('Invalid grouped partition vectors')
    if any(not g.strip() or g in ('None','nan') for g in groups):raise ValueError('Missing group IDs')
    if not np.issubdtype(folds.dtype,np.integer) or (folds<0).any():raise ValueError('Fold labels must be nonnegative integers')
    unique=np.unique(folds)
    if len(unique)<2 or set(unique)!=set(range(len(unique))):raise ValueError('Need contiguous nonempty evaluation folds')
    for group in np.unique(groups):
        if len(set(folds[groups==group]))!=1:raise ValueError('Related group crosses evaluation folds')
    return groups,folds

def estimator(family,seed=20261026):
    if family=='logistic':
        return Pipeline([('impute',SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)),
                         ('scale',StandardScaler()),
                         ('model',LogisticRegression(C=1.0,l1_ratio=0.0,solver='lbfgs',max_iter=2000,random_state=seed))])
    if family=='hist_gradient_boosting':
        # No random row-level early-stopping split: that would mix related
        # systems inside training. Any later tuning needs grouped inner folds.
        return HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=7,min_samples_leaf=15,
                                              l2_regularization=1.0,early_stopping=False,random_state=seed)
    raise ValueError('Unsupported model family')

def validate_feature_sets(columns,feature_sets):
    if len(set(columns))!=len(columns) or not columns:raise ValueError('Unique feature columns required')
    previous=set()
    if not feature_sets:raise ValueError('At least one feature set required')
    for name,features in feature_sets.items():
        current=set(features)
        if not name or not current or len(current)!=len(features) or not current<=set(columns):raise ValueError('Invalid feature-set declaration')
        if not previous<=current:raise ValueError('Comparative feature sets must be nested in declared order')
        previous=current

def grouped_oof(features,labels,identifiers,groups,folds,columns,feature_sets,
                families=('logistic','hist_gradient_boosting'),seed=20261026):
    matrix=np.asarray(features,dtype=float)
    labels=np.asarray(labels)
    identifiers=np.asarray(identifiers,dtype=str)
    groups,folds=validate_partitions(groups,folds)
    if matrix.shape!=(len(groups),len(columns)) or labels.shape!=groups.shape or identifiers.shape!=groups.shape:
        raise ValueError('Feature/cohort dimensions disagree')
    if np.isinf(matrix).any() or not np.isin(labels,[0,1]).all():raise ValueError('Infinite features or nonbinary labels')
    if len(set(identifiers))!=len(identifiers):raise ValueError('Duplicate system identifiers')
    validate_feature_sets(columns,feature_sets)
    if not families or len(set(families))!=len(families):raise ValueError('Unique model families required')
    outputs={}
    audit=[]
    with threadpool_limits(limits=1):
        for family in families:
            for name,selected in feature_sets.items():
                indices=[columns.index(column) for column in selected]
                scores=np.full(len(groups),np.nan)
                for fold in np.unique(folds):
                    test=folds==fold
                    train=~test
                    if len(np.unique(labels[train]))!=2:raise ValueError('Training partition lacks both outcome classes; do not repair folds using test outcomes')
                    fitted=estimator(family,seed)
                    with warnings.catch_warnings():
                        warnings.simplefilter('error',ConvergenceWarning)
                        fitted.fit(matrix[train][:,indices],labels[train])
                    probability=fitted.predict_proba(matrix[test][:,indices])[:,1]
                    if not np.isfinite(probability).all() or ((probability<0)|(probability>1)).any():raise ValueError('Invalid fitted probabilities')
                    scores[test]=probability
                    row={'family':family,'feature_set':name,'fold':int(fold),'training_systems':int(train.sum()),
                         'evaluation_systems':int(test.sum()),'training_groups':len(set(groups[train])),
                         'evaluation_groups':len(set(groups[test])),'related_group_overlap':False}
                    if family=='logistic':
                        # Keep training-only preprocessing facts for audit tests.
                        row['training_imputation_medians']=fitted.named_steps['impute'].statistics_.tolist()
                    audit.append(row)
                if not np.isfinite(scores).all():raise ValueError('Incomplete out-of-fold predictions')
                outputs[family+'/'+name]=scores
    return {'scores':outputs,'fit_audit':audit,'identifiers':identifiers,
            'uncertainty_scope':'OOF scores alone do not include model-training uncertainty; freeze resampling policy separately.'}
