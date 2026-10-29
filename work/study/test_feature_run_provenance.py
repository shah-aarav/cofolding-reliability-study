import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from feature_run_provenance import bound_bytes


class BoundProvenanceTests(unittest.TestCase):
    def test_changed_live_manifest_uses_only_verified_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);(base/'manifests').mkdir()
            relative='manifests/correspondence.jsonl';current=base/relative
            raw=b'original input-only artifact';sha=hashlib.sha256(raw).hexdigest()
            current.write_bytes(raw);state={'source_snapshot_sha256':'a'*64}
            self.assertEqual(bound_bytes(base,state,relative,sha)[0],raw)
            current.write_bytes(b'new acquisition snapshot')
            root=base/'manifests/feature_input_snapshots'/('a'*64);root.mkdir(parents=True)
            saved=root/'saved.jsonl';saved.write_bytes(raw)
            (root/'manifest.json').write_text(json.dumps({'source_snapshot_sha256':'a'*64,
                'artifacts':{relative:{'sha256':sha,'snapshot_filename':saved.name}}}))
            self.assertEqual(bound_bytes(base,state,relative,sha)[0],raw)
            saved.write_bytes(b'tampered')
            with self.assertRaises(ValueError):bound_bytes(base,state,relative,sha)

    def test_manifest_snapshot_path_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);root=base/'manifests/feature_input_snapshots'/('a'*64);root.mkdir(parents=True)
            (root/'manifest.json').write_text(json.dumps({'source_snapshot_sha256':'a'*64,
                'artifacts':{'manifests/missing':{'sha256':'b'*64,'snapshot_filename':'../outside'}}}))
            with self.assertRaises(ValueError):bound_bytes(base,{'source_snapshot_sha256':'a'*64},'manifests/missing','b'*64)
