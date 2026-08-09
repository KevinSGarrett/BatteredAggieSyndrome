from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.replay_engine import ReplayInput,ReplayPlan,verify_local_inputs

def main():
    ap=argparse.ArgumentParser();ap.add_argument("plan",type=Path);ap.add_argument("resolver",type=Path)
    a=ap.parse_args();d=json.loads(a.plan.read_text());d["inputs"]=[ReplayInput(**x) for x in d["inputs"]];p=ReplayPlan(**d)
    resolver={k:Path(v) for k,v in json.loads(a.resolver.read_text()).items()}
    f=verify_local_inputs(p,resolver)
    if f:[print("-",x) for x in f];return 1
    print("PASS");return 0
if __name__=="__main__":raise SystemExit(main())
