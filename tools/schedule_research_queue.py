from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.scheduler import ResourceRequest,ResourcePool,QueueCandidate,select_admissible

def rr(d):return ResourceRequest(**d)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("queue",type=Path);ap.add_argument("pool",type=Path);ap.add_argument("--limit",type=int,default=1)
    a=ap.parse_args()
    pool=ResourcePool(**json.loads(a.pool.read_text()))
    rows=json.loads(a.queue.read_text())
    c=[]
    for i,d in enumerate(rows):
        d=dict(d);d["request"]=rr(d["request"]);d.setdefault("queue_index",i);c.append(QueueCandidate(**d))
    selected=select_admissible(c,pool,a.limit)
    print(json.dumps([x.experiment_id for x in selected],indent=2))
    return 0
if __name__=="__main__":raise SystemExit(main())
