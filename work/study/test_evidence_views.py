import random
import unittest
from evidence_views import aligned_sequence,build_views


class EvidenceViewsTests(unittest.TestCase):
    def fixture(self):
        rng=random.Random(8)
        return [{'sequence':''.join(rng.choice('ACDEFGHIKLMNPQRSTVWY') for _ in range(20)),
                 'cluster_id':f'c{i}'} for i in range(30)]+[{'sequence':'A'*20,'cluster_id':'query'}]

    def test_depth_disjointness_query_and_order_invariance(self):
        rows=self.fixture();query='A'*20
        first=build_views(query,rows,8,42,'a'*64)
        second=build_views(query,list(reversed(rows)),8,42,'a'*64)
        self.assertEqual(first,second)
        a,b=first['views']
        self.assertEqual(len(a['sequences']),9)
        self.assertEqual(a['sequences'][0],b['sequences'][0])
        self.assertFalse(set(a['cluster_ids'])&set(b['cluster_ids']))
        self.assertFalse(set(a['sequences'][1:])&set(b['sequences'][1:]))
        self.assertNotEqual(a['view_sha256'],b['view_sha256'])

    def test_not_enough_clusters_duplicates_and_invalid_alignment_fail(self):
        rows=self.fixture()
        with self.assertRaises(ValueError):build_views('A'*20,rows,16,42,'a'*64)
        with self.assertRaises(ValueError):build_views('A'*20,rows+[dict(rows[0],cluster_id='other')],8,42,'a'*64)
        with self.assertRaises(ValueError):build_views('A'*21,rows,8,42,'a'*64)
        with self.assertRaises(ValueError):build_views('A'*20,rows,8,42,'unknown')

    def test_a3m_insertions_and_query_copies_do_not_inflate_depth(self):
        self.assertEqual(aligned_sequence('AaC.d-D'),'AC-D')
        rows=self.fixture()+[{'sequence':'A'*20,'cluster_id':'query'}]
        result=build_views('A'*20,rows,8,42,'a'*64)
        self.assertEqual(result['available_nonquery_clusters'],30)
        self.assertEqual(result['excluded_query_rows'],2)

    def test_entire_query_cluster_excluded_and_source_query_cluster_required(self):
        rows=self.fixture()+[{'sequence':'A'*19+'C','cluster_id':'query'}]
        result=build_views('A'*20,rows,8,42,'a'*64)
        self.assertEqual(result['available_nonquery_clusters'],30)
        self.assertEqual(result['excluded_query_cluster_homolog_rows'],1)
        self.assertEqual(result,build_views('A'*20,list(reversed(rows)),8,42,'a'*64))
        for view in result['views']:self.assertNotIn('query',view['cluster_ids'])
        with self.assertRaises(ValueError):build_views('A'*20,self.fixture()[:-1],8,42,'a'*64)
        with self.assertRaises(ValueError):build_views('A'*20,rows+[{'sequence':'A'*20,'cluster_id':'different'}],8,42,'a'*64)
        with self.assertRaises(ValueError):build_views('A'*20,rows+[{'sequence':'A'*19+'C','cluster_id':'other'}],8,42,'a'*64)
