import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import tempfile,unittest
from pathlib import Path
from aggie_analytics.experimentation.artifacts_v2 import ArtifactRecord,record_local_artifact

class ArtifactPolicyFullTests(unittest.TestCase):
    def test_model_binary_not_repo_embeddable(self):
        r=ArtifactRecord("A","E",1,"MODEL_BINARY","x","0"*64,10,"INTERNAL",True)
        with self.assertRaises(ValueError): r.validate()
    def test_restricted_not_repo_embeddable(self):
        r=ArtifactRecord("A","E",1,"REPORT","x","0"*64,10,"RESTRICTED",True)
        with self.assertRaises(ValueError): r.validate()
    def test_record(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"r.txt";p.write_text("ok")
            r=record_local_artifact(p,experiment_id="E",attempt=1,class_name="REPORT",repo_embeddable=True)
            self.assertTrue(r.artifact_id.startswith("ART-"))
