from __future__ import annotations
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"src"))
from tools.validate_feature_registry import validate
from tools.schema_discovery import scan,compare
from aggie_analytics.features import load_raw_field_registry,candidate_handoff_allowed

class FeatureRegistryGovernanceTests(unittest.TestCase):
    def test_registry_validator(self):self.assertEqual([],validate(ROOT))
    def test_1197_recon_fields_preserved(self):
        fields=load_raw_field_registry(ROOT/"governance/RAW_FIELD_REGISTRY.csv")
        self.assertEqual(1197,len(fields));self.assertTrue(all(x.pit_gateway_required for x in fields))
    def test_banned_and_review_do_not_handoff(self):
        fields=load_raw_field_registry(ROOT/"governance/RAW_FIELD_REGISTRY.csv")
        for x in fields:
            if x.normalized_temporal_class in {"POSTGAME_OR_FUTURE_BANNED","REVIEW_REQUIRED"}:self.assertFalse(candidate_handoff_allowed(x))
    def test_scanner_detects_nested_and_drift(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"a.json";p.write_text(json.dumps([{"a":1,"nested":{"b":"x"}},{"a":2,"nested":{"b":None}}]))
            old=scan(p);self.assertEqual(2,old["records_scanned"]);self.assertEqual(["a","nested.b"],[x["field_path"] for x in old["fields"]])
            p.write_text(json.dumps([{"a":"now-string","c":3}]))
            drift=compare(old,scan(p));self.assertIn("c",drift["added"]);self.assertIn("nested.b",drift["removed"]);self.assertIn("a",drift["type_changed"])
    def test_scanner_csv_missingness_is_scan_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.csv";p.write_text("a,b\n1,x\n2,\n",encoding="utf-8")
            r=scan(p);by={x["field_path"]:x for x in r["fields"]};self.assertEqual(1,by["b"]["missing"]);self.assertEqual("INTEGER",by["a"]["observed_type"])
if __name__=="__main__":unittest.main()
