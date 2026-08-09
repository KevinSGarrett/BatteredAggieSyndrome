import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import tempfile,unittest
from pathlib import Path
from aggie_analytics.experimentation.locks import FileLock

class LockFullTests(unittest.TestCase):
    def test_exclusive_lock(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"l"
            with FileLock(p,owner="a",purpose="x") as a:
                with self.assertRaises(RuntimeError): FileLock(p,owner="b",purpose="x").acquire()
                self.assertEqual(a.read_existing()["owner"],"a")
            self.assertFalse(p.exists())
