"""Conservative input-sequence relatedness audit. No outcome access or split fitting.

Systems sharing any identical receptor chain are connected. Other chains are
connected when the best BLOSUM62 local alignment has >=30% exact identity over
ALL alignment columns (including gaps) and aligned residue pairs cover >=70%
of the shorter chain. This is an operational
alignment-based grouping, not evolutionary independence or a final frozen split.
Short input chains (<40 aa) are recorded and require a separate policy review.
"""
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'deps'))
import hashlib
import argparse
import json
import time
from collections import defaultdict
from Bio import Align
from Bio.Align import substitution_matrices
from storage import guard

class UnionFind:
    def __init__(self,values): self.parent={x:x for x in values}
    def find(self,x):
        while self.parent[x]!=x:
            self.parent[x]=self.parent[self.parent[x]]
            x=self.parent[x]
        return x
    def union(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.parent[max(a,b)]=min(a,b)

def alignment_stats(alignment,first,second):
    identities=0
    pairs=0
    for (a,b),(c,d) in zip(*alignment.aligned):
        if b-a!=d-c:raise ValueError('Unexpected unequal aligned blocks')
        pairs+=int(b-a)
        identities+=sum(x==y for x,y in zip(first[a:b],second[c:d]))
    import numpy as np
    steps=np.diff(alignment.coordinates,axis=1)
    columns=int(np.max(steps,axis=0).sum())
    return {'identity':identities/columns if columns else 0,'shorter_coverage':pairs/min(len(first),len(second)),
            'aligned_pairs':pairs,'alignment_columns':columns,'identities':identities}

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--recheck-existing-edges',type=Path)
    args=parser.parse_args()
    guard(30_000_000)
    rows=[json.loads(line) for line in (BASE/'manifests/candidates.jsonl').read_text().splitlines()]
    sequence_systems=defaultdict(set)
    short=[]
    invalid=[]
    for row in rows:
        for chain,raw in row['input_sequences'].items():
            sequence=raw.upper()
            if len(sequence)<40:
                short.append({'system_id':row['system_id'],'chain':chain,'length':len(sequence)})
                continue
            if not set(sequence)<=set('ACDEFGHIKLMNPQRSTVWYBXZ'):
                invalid.append({'system_id':row['system_id'],'chain':chain,'length':len(sequence),'unexpected':sorted(set(sequence)-set('ACDEFGHIKLMNPQRSTVWYBXZ'))})
                continue
            sequence_systems[sequence].add(row['system_id'])
    uf=UnionFind(row['system_id'] for row in rows)
    sequences=sorted(sequence_systems)
    representatives={}
    for sequence,systems in sequence_systems.items():
        systems=sorted(systems)
        representatives[sequence]=systems[0]
        for system in systems[1:]:uf.union(systems[0],system)
    aligner=Align.PairwiseAligner()
    aligner.mode='local'
    aligner.substitution_matrix=substitution_matrices.load('BLOSUM62')
    aligner.open_gap_score=-10
    aligner.extend_gap_score=-0.5
    compared=0
    edges=0
    start=time.monotonic()
    total=len(sequences)*(len(sequences)-1)//2
    sequence_hashes={sequence:hashlib.sha256(sequence.encode()).hexdigest() for sequence in sequences}
    recheck=None
    if args.recheck_existing_edges:
        # Safe monotone acceleration of this specific denominator correction:
        # including gap columns can only lower identity, so only edges from the
        # completed gap-excluding scan can survive. Same sequences, aligner,
        # scoring and coverage are required. This is NOT a generic search shortcut.
        original=[json.loads(line) for line in args.recheck_existing_edges.read_text().splitlines()]
        recheck={tuple(sorted((edge['sequence_sha256_a'],edge['sequence_sha256_b']))) for edge in original}
        known=set(sequence_hashes.values())
        if any(a not in known or b not in known for a,b in recheck):raise ValueError('Cached edge contains unknown sequence')
    edges_path=BASE/'manifests/sequence_edges.jsonl'
    with edges_path.open('w',encoding='utf-8') as output:
        for i,first in enumerate(sequences):
            for second in sequences[:i]:
                if recheck is not None and tuple(sorted((sequence_hashes[first],sequence_hashes[second]))) not in recheck:
                    continue
                alignments=aligner.align(first,second)
                if alignments.score<=0:
                    stats={'identity':0,'shorter_coverage':0}
                else:
                    stats=alignment_stats(alignments[0],first,second)
                compared+=1
                if stats['identity']>=0.30 and stats['shorter_coverage']>=0.70:
                    uf.union(representatives[first],representatives[second])
                    output.write(json.dumps({'sequence_sha256_a':sequence_hashes[first],'sequence_sha256_b':sequence_hashes[second],**stats})+'\n')
                    edges+=1
                if compared%1000==0:
                    if output.tell()>20_000_000:raise RuntimeError('Edge inventory budget exhausted')
                    progress={'pairs_compared':compared,'pairs_total':total,'edges':edges,'elapsed_seconds':round(time.monotonic()-start,1)}
                    (BASE/'manifests/sequence_group_progress.json').write_text(json.dumps(progress),encoding='utf-8')
                    print(json.dumps(progress),flush=True)
    groups=defaultdict(list)
    for row in rows:groups[uf.find(row['system_id'])].append(row['system_id'])
    with (BASE/'manifests/sequence_groups_draft.jsonl').open('w',encoding='utf-8') as handle:
        for systems in sorted(groups.values(),key=lambda x:(-len(x),sorted(x))):
            systems=sorted(systems)
            group_id=hashlib.sha256('\n'.join(systems).encode()).hexdigest()[:20]
            for system in systems:handle.write(json.dumps({'system_id':system,'group_id':group_id,'group_size':len(systems),'status':'draft input-sequence relatedness; short-chain policy pending; no split assigned'})+'\n')
    summary={'systems':len(rows),'unique_receptor_chains_ge40aa':len(sequences),'pairs_aligned_this_run':compared,
             'all_possible_pairs':total,'cached_edge_recheck':str(args.recheck_existing_edges) if args.recheck_existing_edges else None,
             'identity_denominator':'all alignment columns including gaps','nonidentical_sequence_edges':edges,'system_components':len(groups),'largest_component_sizes':sorted(map(len,groups.values()),reverse=True)[:20],'short_chains':short,'invalid_chains':invalid,'elapsed_seconds':round(time.monotonic()-start,1),'accuracy_outcomes_examined':False,'split_frozen':False,'caveat':'best local BLOSUM62 alignment; any-chain conservative components; not proof of evolutionary independence'}
    (BASE/'manifests/sequence_group_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('short_chains','invalid_chains')},indent=2))

if __name__=='__main__':run()
