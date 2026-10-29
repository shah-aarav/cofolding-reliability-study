from pathlib import Path
import tempfile
import unittest
from protocol_gate import REQUIRED,build_freeze,verify_freeze,require_frozen_protocol,inside

class ProtocolGateTests(unittest.TestCase):
    def test_missing_freeze_blocks_real_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):require_frozen_protocol(directory)
            with self.assertRaises(ValueError):inside(directory,'../outside')
    def test_missing_decisions_or_readiness_cannot_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):build_freeze(directory,{},[],{})
            with self.assertRaises(ValueError):build_freeze(directory,{key:'synthetic' for key in REQUIRED},['file'],{})
    def test_bound_changes_and_payload_tampering_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'cohort.txt'
            path.write_text('synthetic fixture')
            ready={key:True for key in ('native_top_verified','input_chemical_mapping_verified','model_provenance_resolved',
                                        'eligibility_and_groups_fixed','held_out_outcomes_not_examined')}
            frozen=build_freeze(directory,{key:'synthetic test only' for key in REQUIRED},['cohort.txt'],ready)
            verify_freeze(directory,frozen)
            path.write_text('changed fixture')
            with self.assertRaises(ValueError):verify_freeze(directory,frozen)
            path.write_text('synthetic fixture')
            frozen['payload']['specification']['primary_comparison']='tampered'
            with self.assertRaises(ValueError):verify_freeze(directory,frozen)

if __name__=='__main__':unittest.main()
