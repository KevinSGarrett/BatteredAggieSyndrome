from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aggie_analytics.experimentation.governance import verify_judging_rule_seal

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path.cwd())
    args=ap.parse_args()
    findings=verify_judging_rule_seal(args.repo_root.resolve())
    if findings:
        print("FAIL"); [print("-",x) for x in findings]; return 1
    print("PASS: protected W17 judging-rule seal")
    return 0
if __name__=="__main__": raise SystemExit(main())
