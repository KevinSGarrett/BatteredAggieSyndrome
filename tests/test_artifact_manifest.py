import sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aggie_analytics.experimentation.artifacts import record_local_file, manifest_digest

class ArtifactTests(unittest.TestCase):
    def test_manifest_digest_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"a.txt"; p.write_text("abc",encoding="utf-8")
            r=record_local_file(p)
            self.assertEqual(manifest_digest([r]),manifest_digest([r]))
            self.assertEqual(r.size_bytes,3)
