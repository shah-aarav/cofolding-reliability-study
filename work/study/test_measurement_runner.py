import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import measure_rnp_features as runner


class MeasurementRunnerTests(unittest.TestCase):
    def test_current_bounded_run_not_expired_calendar_and_batched_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);(base/'manifests').mkdir();(base/'data/rnp').mkdir(parents=True)
            plans=[{'system_id':f's{i}'} for i in range(3)]
            audit=[{'system_id':r['system_id'],'model':model,'status':'input_plan_unresolved'}
                   for r in plans for model in ('protenix','boltz2')]
            for name,rows in [('rnp_input_correspondence_plans.jsonl',plans),('rnp_raw_correspondence_audit.jsonl',audit),('rnp_native_reconciliation.jsonl',[])]:
                (base/'manifests'/name).write_text(''.join(json.dumps(r)+'\n' for r in rows))
            for name in ('measure_rnp_features.py','agreement_features.py','chemical_maps.py','geometry.py',
                         'predictor_templates.py','predicted_environment.py','validity.py','structure_io.py'):
                (base/name).write_text('synthetic code identity')
            with patch.object(runner,'BASE',base),patch.object(runner,'guard') as budget,contextlib.redirect_stdout(io.StringIO()):
                runner.main(max_hours=.01)
            state=json.loads((base/'manifests/rnp_feature_measurement_status.json').read_text())
            self.assertEqual(state['status'],'completed_full_manifest_measurement_pass')
            self.assertEqual(state['status_counts'],{'anchor_prerequisites_unresolved':3})
            self.assertLessEqual(budget.call_count,2)

    def test_unbounded_or_nonpositive_runtime_rejected(self):
        for hours in (0,-1,25,float('inf'),float('nan'),True):
            with self.assertRaises(ValueError):runner.main(max_hours=hours)
