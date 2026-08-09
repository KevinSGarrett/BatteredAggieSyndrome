from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.store import ExperimentStore

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--db",type=Path,required=True)
    sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("add");p.add_argument("spec",type=Path)
    p=sub.add_parser("get");p.add_argument("experiment_id")
    p=sub.add_parser("list");p.add_argument("--limit",type=int,default=100)
    sub.add_parser("check")
    a=ap.parse_args();s=ExperimentStore(a.db);s.initialize()
    if a.cmd=="add":
        print(s.add_experiment(json.loads(a.spec.read_text(encoding="utf-8"))));return 0
    if a.cmd=="get":
        r=s.get_experiment(a.experiment_id);print(json.dumps(None if r is None else {"experiment_id":r.experiment_id,"payload":r.payload,"created_at":r.created_at},indent=2));return 0 if r else 2
    if a.cmd=="list":
        print(json.dumps([{"experiment_id":r.experiment_id,"payload":r.payload,"created_at":r.created_at} for r in s.list_experiments(a.limit)],indent=2));return 0
    f=s.integrity_check()
    if f:[print("-",x) for x in f];return 1
    print("PASS");return 0
if __name__=="__main__":raise SystemExit(main())
