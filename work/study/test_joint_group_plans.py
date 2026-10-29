import unittest
from build_joint_group_plans import joint_plans


class JointGroupTests(unittest.TestCase):
    def fixture(self):
        return [{'system_id':s,'receptor_group':r,'identity':i,'scaffold':c}
                for s,r,i,c in [('a','r1','c1','ring'),('b','r1','c2',None),
                                ('c','r2','c2',None),('d','r3','c3','ring'),
                                ('e','r4','c4',None),('f','r5',None,None)]]

    def test_transitive_receptor_and_chemical_connections_and_order_invariance(self):
        rows=self.fixture();result=joint_plans(rows);by={r['system_id']:r for r in result}
        self.assertEqual(result,joint_plans(list(reversed(rows))))
        self.assertEqual(by['a']['joint_exact_group'],by['c']['joint_exact_group'])
        self.assertNotEqual(by['a']['joint_exact_group'],by['d']['joint_exact_group'])
        self.assertEqual(by['a']['joint_scaffold_group'],by['d']['joint_scaffold_group'])

    def test_empty_scaffolds_not_merged_and_unknown_not_claimed_cold(self):
        by={r['system_id']:r for r in joint_plans(self.fixture())}
        self.assertNotEqual(by['b']['joint_scaffold_group'],by['e']['joint_scaffold_group'])
        self.assertEqual(by['f']['chemical_group_status'],'unresolved_not_proven_chemically_cold')
        self.assertFalse(by['f']['split_assigned'])

    def test_duplicates_missing_receptor_and_conflicting_chemical_metadata_rejected(self):
        rows=self.fixture()
        with self.assertRaises(ValueError):joint_plans(rows+[rows[0]])
        with self.assertRaises(ValueError):joint_plans([{**rows[0],'receptor_group':''}])
        with self.assertRaises(ValueError):joint_plans(rows+[{'system_id':'g','receptor_group':'r6','identity':'c2','scaffold':'ring'}])
