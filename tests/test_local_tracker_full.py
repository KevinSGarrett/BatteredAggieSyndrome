import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import tempfile,unittest
from pathlib import Path
from aggie_analytics.experimentation.local_tracker import JsonlTracker

class LocalTrackerFullTests(unittest.TestCase):
    def test_append(self):
        with tempfile.TemporaryDirectory() as td:
            t=JsonlTracker(Path(td)/"events.jsonl")
            t.log("A",{"x":1});t.log("B",{"x":2})
            rows=t.read();self.assertEqual([x["event_type"] for x in rows],["A","B"])
