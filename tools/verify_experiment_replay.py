from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aggie_analytics.experimentation.replay import compare_hashes

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("expected_json", type=Path)
    ap.add_argument("actual_json", type=Path)
    args=ap.parse_args()
    expected=json.loads(args.expected_json.read_text(encoding="utf-8"))
    actual=json.loads(args.actual_json.read_text(encoding="utf-8"))
    report=compare_hashes(expected,actual)
    print(json.dumps({"status":report.status,"failure_code":report.failure_code,"checks":dict(report.checks)},indent=2))
    return 0 if report.status=="VERIFIED" else 1
if __name__=="__main__": raise SystemExit(main())
