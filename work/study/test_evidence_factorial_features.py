import copy
import unittest
from evidence_factorial_features import summarize,CELLS
from build_evidence_experiment_plan import BLOCKS


class FactorialFeatureTests(unittest.TestCase):
    def records(self):
        contacts={'P0a':.9,'P0b':.8,'P1b':.5,'B0b':.9,'B1b':.4}
        return [{'block':b,'cell':cell,'model':model,'view_sha256':('a' if view=='V0' else 'b')*64,
                 'system_input_sha256':'c'*64,'anchor_coordinate_sha256':'d'*64,
                 'native_selection_verified':True,'experimental_reference_used':False,
                 'diffusion_seed':BLOCKS[b][0 if cell=='P0a' else 1],
                 'anchor_ligand_rmsd':1.,'anchor_contact_jaccard':contacts[cell],'native_confidence':.7}
                for b in range(5) for cell,(model,view) in CELLS.items()]

    def test_exact_paired_contrasts_and_order_invariance(self):
        rows=self.records();result=summarize(rows)
        self.assertEqual(result,summarize(list(reversed(rows))))
        self.assertAlmostEqual(result['features']['PP_contact_evidence_fragility'],.3)
        self.assertAlmostEqual(result['features']['PB_contact_evidence_fragility'],.5)
        self.assertAlmostEqual(result['features']['contact_fragility_model_interaction'],.2)

    def test_missing_contacts_remain_missing_not_perfect_or_available_case_mean(self):
        rows=self.records();rows[0]['anchor_contact_jaccard']=None
        result=summarize(rows)
        self.assertIsNone(result['features']['PP_contact_evidence_fragility'])
        self.assertEqual(result['blocks_with_missing_measurement']['PP_shared_anchor_contact_support'],1)

    def test_leakage_incomplete_design_changed_anchor_view_or_seed_rejected(self):
        rows=self.records()
        with self.assertRaises(ValueError):summarize(rows[:-1])
        for key,value in [('anchor_coordinate_sha256','e'*64),('system_input_sha256','e'*64),
                          ('experimental_reference_used',True),('diffusion_seed',102),('view_sha256','b'*64),('outcome',1),('label',1)]:
            changed=copy.deepcopy(rows);changed[0][key]=value
            with self.assertRaises(ValueError):summarize(changed)
