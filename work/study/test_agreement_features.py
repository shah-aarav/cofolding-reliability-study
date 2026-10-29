import unittest
from dataclasses import replace
import numpy as np
from rdkit import Chem
from chemical_maps import checked_template
from structure_io import Atom
from agreement_features import measure_agreement

class AgreementFeatureTests(unittest.TestCase):
    def fixture(self):
        protein=[Atom('A','A','1','ALA',str(i+1),str(i+1),'CA','C',point,1)
                 for i,point in enumerate([(0,0,0),(2,0,0),(0,2,0),(0,0,2)])]
        ligand=[Atom('B','B','2','LIG','1','1','C1','C',(1,1,1),1),
                Atom('B','B','2','LIG','1','1','O1','O',(1,1,2),1)]
        template=checked_template(Chem.MolFromSmiles('CO'),['C1','O1'],'synthetic input molecule')
        return protein+ligand,template
    def measure(self,moving,fixed,template):
        return measure_agreement(moving,fixed,[('A','A')],'B','B',template,template,'synthetic verified input')
    def test_common_rigid_transform_is_removed(self):
        atoms,template=self.fixture()
        rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]])
        moved=[replace(a,position=tuple(np.array(a.position)@rotation+[4,8,2])) for a in atoms]
        result=self.measure(moved,atoms,template)
        self.assertAlmostEqual(result['agreement']['receptor_aligned_ligand_rmsd'],0,places=12)
        self.assertEqual(result['agreement']['contact_jaccard_4A'],1)
        self.assertFalse(result['experimental_reference_used'])
    def test_ligand_pose_displacement_is_not_fitted_away(self):
        atoms,template=self.fixture()
        moved=[replace(a,position=tuple(np.array(a.position)+[10,0,0])) if a.chain=='B' else a for a in atoms]
        result=self.measure(moved,atoms,template)
        self.assertAlmostEqual(result['agreement']['receptor_aligned_ligand_rmsd'],10)
        self.assertEqual(result['agreement']['contact_jaccard_4A'],0)
    def test_missing_provenance_and_overlapping_roles_rejected(self):
        atoms,template=self.fixture()
        with self.assertRaises(ValueError):measure_agreement(atoms,atoms,[('A','A')],'B','B',template,template,'')
        with self.assertRaises(ValueError):measure_agreement(atoms,atoms,[('A','A')],'A','B',template,template,'source')

if __name__=='__main__':unittest.main()
