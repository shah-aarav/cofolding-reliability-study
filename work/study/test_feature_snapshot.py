import hashlib
from pathlib import Path
import tempfile
import unittest
from snapshot_feature_inputs import verified_bytes


class SnapshotTests(unittest.TestCase):
    def test_changed_hash_and_budget_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic'
            path.write_bytes(b'input-only fixture')
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(verified_bytes(path,sha),b'input-only fixture')
            with self.assertRaises(ValueError):verified_bytes(path,'0'*64)
            with self.assertRaises(ValueError):verified_bytes(path,sha,max_bytes=1)
