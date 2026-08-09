import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import unittest
from aggie_analytics.experimentation.lineage import canonical_json,content_id,assert_result_independent_identity

class LineageFullTests(unittest.TestCase):
    def test_order_independent(self):
        a={"b":2,"a":{"y":2,"x":1}}
        b={"a":{"x":1,"y":2},"b":2}
        self.assertEqual(canonical_json(a),canonical_json(b))
        self.assertEqual(content_id("EXP",a),content_id("EXP",b))

    def test_volatile_runtime_fields_do_not_change_identity(self):
        a={"target":"win","host":"A","pid":1}
        b={"target":"win","host":"B","pid":999}
        self.assertEqual(content_id("EXP",a),content_id("EXP",b))

    def test_result_fields_rejected(self):
        with self.assertRaises(ValueError):
            assert_result_independent_identity({"target":"win","metrics":{"brier":0.2}})
