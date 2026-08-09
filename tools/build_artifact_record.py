from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.artifacts_v2 import record_local_artifact

def main():
    ap=argparse.ArgumentParser();ap.add_argument("path",type=Path);ap.add_argument("--experiment-id",required=True);ap.add_argument("--attempt",type=int,default=1);ap.add_argument("--class-name",required=True);ap.add_argument("--sensitivity",default="INTERNAL");ap.add_argument("--repo-embeddable",action="store_true")
    a=ap.parse_args();r=record_local_artifact(a.path,experiment_id=a.experiment_id,attempt=a.attempt,class_name=a.class_name,sensitivity=a.sensitivity,repo_embeddable=a.repo_embeddable)
    print(json.dumps(r.__dict__,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
