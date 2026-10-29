import unittest
from confidence import native_features

class ConfidenceTests(unittest.TestCase):
    def test_proper_ligand_plddt_uses_input_index(self):
        result=native_features('protenix',{'chain_plddt':[.9,.4,.99]},1,0)
        self.assertEqual(result['input_ligand_chain_plddt'],.4)
        with self.assertRaises(ValueError):native_features('protenix',{'chain_plddt':[.9]},1,0)
    def test_asymmetric_pairs_use_input_ligand_order(self):
        data={'ranking_score':.8,'chain_pair_iptm':[[1,.2,.3],[.4,1,.5],[.6,.7,1]],'ranking_score_rmsd':.999,'rmsd':0}
        values=native_features('protenix',data,2,0)
        self.assertEqual(values['ranking_score'],.8)
        self.assertEqual(values['protein_to_ligand_iptm_mean'],.4)
        self.assertAlmostEqual(values['ligand_to_protein_iptm_mean'],.65)
        self.assertNotIn('rmsd',values)
        self.assertNotIn('ranking_score_rmsd',values)

    def test_boltz_dictionary_pairs_and_native_score(self):
        values=native_features('boltz2',{'confidence_score':.6,'pair_chains_iptm':{'0':{'1':.4},'1':{'0':.7}}},1,0)
        self.assertEqual(values['ranking_score'],.6)
        self.assertEqual(values['protein_to_ligand_iptm_mean'],.4)
        self.assertEqual(values['ligand_to_protein_iptm_mean'],.7)

    def test_bad_chain_order_and_missingness_are_explicit(self):
        with self.assertRaises(ValueError):native_features('protenix',{'chain_pair_iptm':[[1]]},1,0)
        values=native_features('protenix',{'ranking_score':float('nan')},1,0)
        self.assertIsNone(values['ranking_score'])
        self.assertIsNone(values['protein_to_ligand_iptm_mean'])

if __name__=='__main__':unittest.main(verbosity=2)
