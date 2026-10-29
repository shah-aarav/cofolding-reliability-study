import unittest
from input_roles import rnp_input_roles,confidence_roles

class InputRoleTests(unittest.TestCase):
    def test_repeated_cofactor_reorders_other_ligand_confidence_index(self):
        roles=rnp_input_roles({'originalProtein':'ACD'},['[Zn+2]','CCO','[Zn+2]'])
        self.assertEqual([r['declared_input_chain_id'] for r in roles['boltz2']],['A','B','D','C'])
        self.assertEqual(confidence_roles(roles['protenix'],1),([0],2))
        self.assertEqual(confidence_roles(roles['boltz2'],1),([0],3))
    def test_identical_proteins_are_grouped_without_ligand_geometry(self):
        roles=rnp_input_roles({'a':'ACD','b':'EFG','c':'ACD'},['CO'])
        self.assertEqual([r['declared_input_chain_id'] for r in roles['boltz2']],['A','C','B','D'])
        self.assertEqual(confidence_roles(roles['boltz2'],0),([0,1,2],3))
    def test_unsupported_counts_and_missing_ligand_rejected(self):
        with self.assertRaises(ValueError):rnp_input_roles({},['CO'])
        with self.assertRaises(ValueError):rnp_input_roles({'a':'ACD'},['CO']*26)
        with self.assertRaises(ValueError):confidence_roles(rnp_input_roles({'a':'ACD'},['CO'])['boltz2'],1)

if __name__=='__main__':unittest.main()
