import io
import unittest
from unittest.mock import patch
import numpy as np
from geometry import rigid_fit, mapped_rmsd, residue_contacts, contact_jaccard
from storage import guard, LIMIT
from stream_inventory import BoundedReader, safe_member
from collect_coordinates import selected_pose

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


if __name__=='__main__': unittest.main()

