import unittest
from collect_openbind import rank_native

class NativeSelectionTests(unittest.TestCase):
    def test_native_only_ranking_and_stable_ties(self):
        rows=[('20','1',{'ranking_score':.9,'reference_rmsd':0}),
              ('10','2',{'ranking_score':.9,'reference_rmsd':99}),
              ('10','0',{'ranking_score':.9}),('5','0',{'ranking_score':.8})]
        result=rank_native('protenix',rows)
        self.assertEqual((result['seed'],result['sample']),('10','0'))
        self.assertEqual(result['tied_top_count'],3)
        self.assertEqual(rank_native('protenix',list(reversed(rows))),result)
    def test_invalid_confidence_is_not_silently_dropped(self):
        for value in (None,True,float('nan'),float('inf'),'0.8'):
            with self.assertRaises(ValueError):rank_native('boltz2',[('1','0',{'confidence_score':value})])
    def test_boltz_uses_native_score_not_iptm(self):
        result=rank_native('boltz2',[('1','0',{'confidence_score':.8,'iptm':1}),('1','1',{'confidence_score':.9,'iptm':0})])
        self.assertEqual(result['sample'],'1')

if __name__=='__main__':unittest.main()
