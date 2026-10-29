"""Deterministic cluster-disjoint, depth-matched MSA experimental views.

Does not download MSAs, cluster sequences, run predictors or read outcomes.
Cluster IDs must come from an independently recorded sequence-clustering job.
Disjoint clusters are an operational intervention, NOT statistical independence.
"""
import hashlib
import json
import re


def aligned_sequence(a3m):
    if not isinstance(a3m,str) or not a3m or re.search(r'[^A-Za-z.\-]',a3m):
        raise ValueError('Invalid A3M sequence characters')
    return ''.join(c for c in a3m if c.isupper() or c=='-')


def build_views(query,rows,homolog_rows,seed,source_sha256):
    if not isinstance(query,str) or not query or re.fullmatch('[A-Z]+',query) is None:
        raise ValueError('Supply the exact unaligned uppercase input query')
    if type(homolog_rows) is not int or homolog_rows<1 or type(seed) is not int:
        raise ValueError('Explicit positive depth and integer randomization seed required')
    if not isinstance(source_sha256,str) or re.fullmatch('[0-9a-f]{64}',source_sha256) is None:
        raise ValueError('Source alignment SHA256 required')
    rows=list(rows)
    query_clusters=set()
    normalized=[]
    cluster_assignment={}
    for row in rows:
        sequence=aligned_sequence(row['sequence']);cluster=row['cluster_id']
        if not isinstance(cluster,str) or not cluster:raise ValueError('Recorded cluster IDs required')
        if len(sequence)!=len(query):raise ValueError('Alignment/query length mismatch')
        if sequence in cluster_assignment and cluster_assignment[sequence]!=cluster:
            raise ValueError('Identical aligned sequences have inconsistent cluster IDs')
        cluster_assignment[sequence]=cluster
        normalized.append((row,sequence,cluster))
        if sequence==query:query_clusters.add(cluster)
    if len(query_clusters)!=1:
        raise ValueError('Include the exact query with one consistent cluster ID in source clustering metadata')
    clusters={};seen={};excluded_query=0;excluded_cluster_rows=0
    for row,sequence,cluster in normalized:
        if sequence==query:
            excluded_query+=1;continue
        if cluster in query_clusters:
            excluded_cluster_rows+=1;continue
        if sequence in seen and seen[sequence]!=cluster:raise ValueError('Identical aligned sequences have inconsistent cluster IDs')
        seen[sequence]=cluster
        # Deduplicate by aligned residues, but retain an actual source A3M row:
        # stripping insertions would alter model deletion/insertion features.
        clusters.setdefault(cluster,{}).setdefault(sequence,set()).add(row['sequence'])
    if len(clusters)<2*homolog_rows:raise ValueError('Insufficient unique homolog clusters for two disjoint matched-depth views')
    digest=lambda value:hashlib.sha256(f'{seed}\0{source_sha256}\0{value}'.encode()).hexdigest()
    selected=sorted(clusters,key=lambda c:(digest('cluster:'+c),c))[:2*homolog_rows]
    views=[]
    for ids in (selected[:homolog_rows],selected[homolog_rows:]):
        representatives=[]
        for c in ids:
            aligned=min(clusters[c],key=lambda s:(digest('row:'+c+':'+s),s))
            representatives.append(min(clusters[c][aligned],key=lambda s:(digest('raw:'+c+':'+s),s)))
        sequences=[query]+representatives
        payload={'query':query,'sequences':sequences,'cluster_ids':ids,'source_sha256':source_sha256,
                 'seed':seed,'homolog_rows':homolog_rows,'excluded_query_cluster':next(iter(query_clusters)),
                 'policy':'query-containing cluster excluded from homolog pool; one representative per other provided cluster; identical query in both views; source A3M insertions preserved; aligned-duplicate rows do not inflate depth'}
        views.append({**payload,'view_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()})
    if set(views[0]['cluster_ids'])&set(views[1]['cluster_ids']):raise AssertionError('Cluster overlap')
    return {'views':views,'available_nonquery_clusters':len(clusters),'excluded_query_rows':excluded_query,
            'excluded_query_cluster_homolog_rows':excluded_cluster_rows,
            'experimental_outcomes_used':False,'predictor_runs_performed':False,
            'limitation':'Cluster labels are supplied, not verified here. Sequence disjointness does not imply independent information or eliminate common training priors. Validate paired/chain-specific MSA semantics in each runner.'}
