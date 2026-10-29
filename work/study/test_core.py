import io
import unittest
from unittest.mock import patch
import numpy as np
from geometry import rigid_fit, mapped_rmsd, residue_contacts, contact_jaccard
from storage import guard, LIMIT
from stream_inventory import BoundedReader, safe_member
from collect_coordinates import selected_pose
from metrics import retained_error, threshold_error, paired_group_bootstrap
from build_sequence_groups import UnionFind, alignment_stats

class GeometryTests(unittest.TestCase):
    def test_rotation_translation_recovered_without_moving_ligand_independently(self):
        receptor=np.array([[0,0,0],[1,0,0],[0,2,0],[0,0,3]],dtype=float)
        rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]],dtype=float)
        shifted=receptor@rotation+np.array([7,8,9])
        r,t=rigid_fit(shifted,receptor)
        np.testing.assert_allclose(shifted@r+t,receptor,atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(r),1)
        ligand=np.array([[1,2,3],[2,3,4]],dtype=float)
        transformed=(ligand@rotation+[7,8,9])@r+t
        self.assertAlmostEqual(mapped_rmsd(transformed,ligand,[[0,1]]),0,places=12)
        self.assertAlmostEqual(mapped_rmsd(ligand+[5,0,0],ligand,[[0,1]]),5)

    def test_symmetry_and_invalid_maps(self):
        ligand=np.array([[0,0,0],[2,0,0]],dtype=float)
        self.assertEqual(mapped_rmsd(ligand[::-1],ligand,[[0,1],[1,0]]),0)
        with self.assertRaises(ValueError): mapped_rmsd(ligand,ligand,[[0,0]])

    def test_no_reflection_or_degenerate_fit(self):
        points=np.array([[0,0,0],[1,0,0],[0,2,0],[0,0,3]],dtype=float)
        mirrored=points*np.array([-1,1,1])
        r,t=rigid_fit(mirrored,points)
        self.assertGreater(np.linalg.norm(mirrored@r+t-points),0.1)
        with self.assertRaises(ValueError): rigid_fit([[0,0,0]]*3,[[1,1,1]]*3)

    def test_contacts_and_empty_sets(self):
        contacts=residue_contacts([[0,0,0],[1,0,0],[10,0,0]],['A1','A1','A2'],[[0,0,0]],2)
        self.assertEqual(contacts,{'A1'})
        self.assertEqual(contact_jaccard({'A1'},{'A1','A2'}),0.5)
        self.assertIsNone(contact_jaccard([],[]))

class StorageTests(unittest.TestCase):
    def test_guard_rejects_project_overflow(self):
        with patch('storage.used_bytes',return_value=LIMIT-1):
            with self.assertRaises(RuntimeError): guard(1)

    def test_archive_path_rejection(self):
        for path in ['../bad','/bad','C:/bad','a/../../bad','..\\bad']:
            self.assertFalse(safe_member(path))
        self.assertTrue(safe_member('prediction_files/boltz2/system/model.cif'))

    def test_stream_budget(self):
        reader=BoundedReader(io.BytesIO(b'abcdef'),4)
        self.assertEqual(reader.read(3),b'abc')
        with self.assertRaises(RuntimeError): reader.read(2)
        with self.assertRaises(ValueError): reader.read()

    def test_pose_matching_requires_seed_and_sample(self):
        selection={'seed':'42.0','sample':'2.0'}
        self.assertTrue(selected_pose('seed-42/model_2.cif',selection))
        self.assertFalse(selected_pose('seed-420/model_2.cif',selection))
        self.assertFalse(selected_pose('seed-42/model_3.cif',selection))
        self.assertFalse(selected_pose('model_2.cif',selection))
        self.assertTrue(selected_pose('42/boltz_results_input/predictions/input/input_model_2.cif',selection))
        self.assertFalse(selected_pose('420/boltz_results_input/predictions/input/input_model_2.cif',selection))

class MetricsTests(unittest.TestCase):
    def test_ties_use_id_and_never_label(self):
        first=retained_error([0,1,0],[0.5,0.5,0.5],['c','a','b'])
        second=retained_error([1,0,1],[0.5,0.5,0.5],['c','a','b'])
        np.testing.assert_array_equal(first['retained_indices'],[1,2])
        np.testing.assert_array_equal(first['retained_indices'],second['retained_indices'])
        self.assertEqual(first['retained_count'],2)

    def test_zero_threshold_coverage_has_no_error_estimate(self):
        result=threshold_error([1,0],[0.1,0.2],['a','b'],0.9)
        self.assertEqual(result['coverage'],0)
        self.assertIsNone(result['error'])

    def test_paired_effect_sign_and_reproducibility(self):
        args=([1,0,1,0],[.9,.8,.2,.1],[.9,.1,.8,.2],['a','b','c','d'],['g1','g1','g2','g2'])
        first=paired_group_bootstrap(*args,replicates=30)
        second=paired_group_bootstrap(*args,replicates=30)
        self.assertEqual(first,second)
        self.assertEqual(first['effect_percentage_points'],50)
        self.assertEqual(first['groups'],2)

    def test_invalid_observations_rejected(self):
        with self.assertRaises(ValueError):retained_error([1,0],[.1,.2],['a','a'])
        with self.assertRaises(ValueError):retained_error([1,0],[np.nan,.2],['a','b'])
        with self.assertRaises(ValueError):paired_group_bootstrap([1,0],[.1,.2],[.2,.1],['a','b'],['g','g'])
        with self.assertRaises(ValueError):paired_group_bootstrap([1,0],[.1,.2],[.2,.1],['a','b'],['','g'])

    def test_bootstrap_ties_preserve_original_prefix_id_order(self):
        # Renaming IDs to a monotonically equivalent alphabet must not alter
        # paired intervals. ID suffixing used to break this for prefix IDs.
        args=([1,0,1,0],[.5,.5,.5,.5],[.7,.7,.5,.5])
        first=paired_group_bootstrap(*args,['a','a!','b','b!'],['g1','g1','g2','g2'],replicates=100)
        second=paired_group_bootstrap(*args,['01','02','03','04'],['g1','g1','g2','g2'],replicates=100)
        self.assertEqual(first,second)

class GroupingTests(unittest.TestCase):
    def test_transitive_relatedness(self):
        groups=UnionFind(['a','b','c','d'])
        groups.union('b','c')
        groups.union('a','b')
        self.assertEqual(groups.find('a'),groups.find('c'))
        self.assertNotEqual(groups.find('a'),groups.find('d'))

    def test_identity_and_coverage_count_only_aligned_pairs(self):
        class Alignment:
            aligned=np.array([[[0,4],[5,8]],[[1,5],[5,8]]])
            coordinates=np.array([[0,4,5,8],[1,5,5,8]])
        result=alignment_stats(Alignment(),'ACDEFGHI','XACDEGHI')
        self.assertEqual(result['identities'],7)
        self.assertEqual(result['aligned_pairs'],7)
        self.assertEqual(result['identity'],7/8)
        self.assertEqual(result['alignment_columns'],8)
        self.assertEqual(result['shorter_coverage'],7/8)

if __name__=='__main__': unittest.main(verbosity=2)
