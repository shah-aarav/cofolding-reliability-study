import unittest
import numpy as np
from modeling import validate_partitions,grouped_oof

class ModelingTests(unittest.TestCase):
    def fixture(self):
        rng=np.random.default_rng(7)
        x=rng.normal(size=(120,3));x[::7,1]=np.nan
        y=(x[:,0]+np.nan_to_num(x[:,1])*.2>0).astype(int)
        ids=[f's{i}' for i in range(120)]
        groups=[f'g{i//4}' for i in range(120)]
        folds=np.array([(i//4)%3 for i in range(120)])
        return x,y,ids,groups,folds
    def test_group_crossing_is_rejected(self):
        with self.assertRaises(ValueError):validate_partitions(['g','g','h'],[0,1,1])
        with self.assertRaises(ValueError):validate_partitions(['g','h'],[0,2])
    def test_preprocessing_is_training_only_and_oof_complete(self):
        x,y,ids,groups,folds=self.fixture()
        result=grouped_oof(x,y,ids,groups,folds,['native','second','agreement'],
                           {'native':['native'],'second':['native','second'],'agreement':['native','second','agreement']})
        self.assertEqual(len(result['scores']),6)
        for scores in result['scores'].values():
            self.assertEqual(scores.shape,(120,))
            self.assertTrue(np.isfinite(scores).all())
        for row in result['fit_audit']:
            self.assertFalse(row['related_group_overlap'])
            if row['family']=='logistic':
                columns={'native':[0],'second':[0,1],'agreement':[0,1,2]}[row['feature_set']]
                np.testing.assert_allclose(row['training_imputation_medians'],np.nanmedian(x[folds!=row['fold']][:,columns],axis=0))
    def test_nonnested_sets_and_duplicate_systems_rejected(self):
        x,y,ids,groups,folds=self.fixture()
        with self.assertRaises(ValueError):grouped_oof(x,y,ids,groups,folds,['a','b','c'],{'a':['a'],'b':['b']})
        ids[1]=ids[0]
        with self.assertRaises(ValueError):grouped_oof(x,y,ids,groups,folds,['a','b','c'],{'a':['a']})

if __name__=='__main__':unittest.main()
