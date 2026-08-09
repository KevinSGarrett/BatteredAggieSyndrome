from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.comparison import assert_semantically_compatible,ordered_development_ranking

def main():
    ap=argparse.ArgumentParser();ap.add_argument("packets",nargs="+",type=Path);ap.add_argument("--primary-metric",required=True);ap.add_argument("--direction",choices=["min","max"],required=True)
    a=ap.parse_args()
    ps=[json.loads(p.read_text()) for p in a.packets]
    for x in ps[1:]:assert_semantically_compatible(ps[0],x)
    ranked=ordered_development_ranking(ps,primary_metric=a.primary_metric,direction=a.direction)
    print(json.dumps([{"rank":i+1,"experiment_id":p.get("experiment_id"),"value":p["metrics"][a.primary_metric]} for i,p in enumerate(ranked)],indent=2))
    return 0
if __name__=="__main__":raise SystemExit(main())
