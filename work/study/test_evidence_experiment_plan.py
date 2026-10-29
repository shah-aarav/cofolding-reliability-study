import unittest
from build_evidence_experiment_plan import system_jobs,BLOCKS


class ExperimentPlanTests(unittest.TestCase):
    def test_full_factorial_arms_share_only_deliberate_jobs(self):
        tasks=system_jobs('synthetic')
        self.assertEqual(len(tasks),30)
        self.assertEqual(len({j['job_id'] for j in tasks}),30)
        self.assertEqual(sum(j['samples_per_job'] for j in tasks),150)
        self.assertEqual(sum(j['stage']=='fixed_anchor' for j in tasks),5)
        for block,(a,b) in enumerate(BLOCKS):
            cells={j['cell']:j for j in tasks if j.get('randomization_block')==block}
            self.assertEqual(set(cells),{'P0a','P0b','P1b','B0b','B1b'})
            self.assertEqual(cells['P0b']['diffusion_seed'],cells['B0b']['diffusion_seed'])
            self.assertEqual(cells['P0b']['diffusion_seed'],cells['P1b']['diffusion_seed'])
            self.assertNotEqual(cells['P0a']['diffusion_seed'],cells['P0b']['diffusion_seed'])
            self.assertEqual(cells['P0a']['view'],cells['B0b']['view'])
        self.assertTrue(all(j['blockers'] and not j['external_submission_authorized'] for j in tasks))

    def test_path_injection_and_implicit_systems_rejected(self):
        for name in ('','../source','x/y','x\\y','C:foo'):
            with self.assertRaises(ValueError):system_jobs(name)
