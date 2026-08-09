import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import tempfile,unittest,hashlib
from pathlib import Path
from aggie_analytics.experimentation.replay_engine import ReplayInput,ReplayPlan,verify_local_inputs,compare_scalar_outputs

class ReplayEngineFullTests(unittest.TestCase):
    def test_input_hash(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x"; p.write_bytes(b"abc")
            h=hashlib.sha256(b"abc").hexdigest()
            plan=ReplayPlan("E","R","C","ENV","0"*64,[ReplayInput("x","u",h)])
            self.assertEqual(verify_local_inputs(plan,{"u":p}),[])
    def test_mismatch(self):
        self.assertTrue(compare_scalar_outputs({"x":1.0},{"x":1.2},tolerance=.1))
    def test_stochastic_requires_tolerance(self):
        with self.assertRaises(ValueError): ReplayPlan("E","R","C","ENV","0"*64,[ReplayInput("x","u","0"*64)],True,None).validate()
