import unittest
from measure_rnp_features import checked_atoms


class FeatureInputTests(unittest.TestCase):
    def test_only_prediction_root_is_accepted(self):
        for path in ['sources/rnp_record.json','data/rnp/reference_ground_truth_unopened.tar.gz','../../outputs/research-status.md']:
            with self.assertRaises(ValueError):
                checked_atoms({'coordinate_path':path,'coordinate_sha256':'not-a-real-checksum'})


if __name__=='__main__':unittest.main()
