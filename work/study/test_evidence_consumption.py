import copy
import unittest
from evidence_views import build_views
from evidence_consumption import row_features,verify_consumption,compare_shared


class ConsumptionTests(unittest.TestCase):
    def fixture(self):
        views=build_views('AAAA',[
            {'sequence':'AAAA','cluster_id':'q'},
            {'sequence':'AaC-Dx','cluster_id':'a'},
            {'sequence':'A.C-C','cluster_id':'b'},
            {'sequence':'CADD','cluster_id':'c'},
            {'sequence':'DAAC','cluster_id':'d'}],2,42,'a'*64)['views']
        def record(view):
            return {'schema_version':1,'protein_chain_count':1,'pairing_mode':'unpaired',
                    'templates_enabled':False,'automatic_evidence_enabled':False,
                    'input_sha256':'b'*64,'view_sha256':view['view_sha256'],
                    'processed_artifact_sha256':'c'*64,'extractor_code_sha256':'d'*64,
                    'runner_config_sha256':'e'*64,
                    'rows':[{**row_features(s),'active_columns':[True]*4} for s in view['sequences']]}
        return views,[record(v) for v in views]

    def test_insertions_query_and_semantic_identity(self):
        self.assertEqual(row_features('aA.bC-Dxy'),{'aligned_sequence':'AC-D','insertion_counts':[1,1,0,0,2]})
        views,records=self.fixture();a=verify_consumption(views[0],records[0])
        other=copy.deepcopy(records[0]);other['processed_artifact_sha256']='f'*64
        b=verify_consumption(views[0],other)
        self.assertTrue(compare_shared(a,b)['shared_normalized_record_evidence'])
        self.assertFalse(a['actual_tensor_extraction_verified'])
        with self.assertRaises(ValueError):compare_shared(a,verify_consumption(views[1],records[1]))

    def test_crop_reorder_insertions_and_hidden_evidence_rejected(self):
        views,records=self.fixture()
        variants=[]
        x=copy.deepcopy(records[0]);x['rows']=x['rows'][:-1];variants.append(x)
        x=copy.deepcopy(records[0]);x['rows'][1:]=list(reversed(x['rows'][1:]));variants.append(x)
        x=copy.deepcopy(records[0]);x['rows'][1]['insertion_counts'][0]+=1;variants.append(x)
        x=copy.deepcopy(records[0]);x['rows'][0]['active_columns'][0]=False;variants.append(x)
        for key,value in [('templates_enabled',True),('automatic_evidence_enabled',True),
                          ('protein_chain_count',2),('pairing_mode','paired'),('label',1)]:
            x=copy.deepcopy(records[0]);x[key]=value;variants.append(x)
        for item in variants:
            with self.assertRaises(ValueError):verify_consumption(views[0],item)

    def test_tampered_view_or_missing_provenance_rejected(self):
        views,records=self.fixture();view=copy.deepcopy(views[0]);view['seed']+=1
        with self.assertRaises(ValueError):verify_consumption(view,records[0])
        for key in ('input_sha256','extractor_code_sha256','processed_artifact_sha256'):
            bad=copy.deepcopy(records[0]);bad[key]='unknown'
            with self.assertRaises(ValueError):verify_consumption(views[0],bad)
