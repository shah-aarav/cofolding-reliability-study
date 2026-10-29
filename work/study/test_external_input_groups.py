import unittest
from build_external_input_groups import group_keys


class ExternalGroupTests(unittest.TestCase):
    def test_empty_scaffolds_do_not_collapse_unrelated_acyclic_inputs(self):
        first=group_keys('CCO',None);second=group_keys('CCN',None)
        self.assertEqual(first[0],first[1])
        self.assertNotEqual(first[1],second[1])

    def test_repeated_identity_and_scaffold_groups_are_deterministic(self):
        self.assertEqual(group_keys('Cc1ccccc1','c1ccccc1'),group_keys('Cc1ccccc1','c1ccccc1'))
        self.assertEqual(group_keys('Cc1ccccc1','c1ccccc1')[1],group_keys('Oc1ccccc1','c1ccccc1')[1])
        self.assertNotEqual(group_keys('Cc1ccccc1','c1ccccc1')[0],group_keys('Oc1ccccc1','c1ccccc1')[0])
        with self.assertRaises(ValueError):group_keys('',None)


if __name__=='__main__':unittest.main()
