import unittest
from audit_feature_records import verify_record


class FeatureRecordTests(unittest.TestCase):
    def test_unresolved_never_becomes_scientific_result(self):
        row={'system_id':'synthetic','source_snapshot_sha256':'inputhash','status':'anchor_prerequisites_unresolved',
             'experimental_outcomes_examined':False,'protocol_frozen':False,'final_coordinate_eligibility':False,
             'scientific_accuracy_result':None}
        verify_record(row,'synthetic','inputhash',{})
        with self.assertRaises(ValueError):verify_record(row,'other','inputhash',{})
        row['scientific_accuracy_result']=.9
        with self.assertRaises(ValueError):verify_record(row,'synthetic','inputhash',{})


if __name__=='__main__':unittest.main()
