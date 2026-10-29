import unittest
from audit_chemical_overlap import describe


class ChemicalOverlapTests(unittest.TestCase):
    def test_acyclic_empty_scaffolds_not_an_identity(self):
        self.assertIsNone(describe('CCO')[1])
        self.assertIsNone(describe('CCN')[1])
        self.assertNotEqual(describe('CCO')[0],describe('CCN')[0])

    def test_exact_identity_preserves_stereo_and_charge(self):
        self.assertNotEqual(describe('C[C@H](O)F')[0],describe('C[C@@H](O)F')[0])
        self.assertNotEqual(describe('CN')[0],describe('C[NH3+]')[0])
        with self.assertRaises(ValueError):describe('[Zn+2]')
        self.assertEqual(describe('CCO')[0],describe('OCC')[0])


if __name__=='__main__':unittest.main()
