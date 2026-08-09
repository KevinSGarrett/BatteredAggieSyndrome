from __future__ import annotations
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.store import ExperimentStore

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",type=Path,required=True)
    args=ap.parse_args()
    s=ExperimentStore(args.db);s.initialize()
    findings=s.integrity_check()
    if findings:
        print("FAIL");[print("-",x) for x in findings];return 1
    print(f"PASS: initialized {args.db}")
    return 0
if __name__=="__main__":raise SystemExit(main())
