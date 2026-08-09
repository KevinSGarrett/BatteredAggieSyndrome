from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.hpo_engine import DiscreteParameter,enumerate_trials

def main():
    ap=argparse.ArgumentParser();ap.add_argument("study",type=Path);a=ap.parse_args()
    d=json.loads(a.study.read_text());pars=[DiscreteParameter(x["name"],x["values"]) for x in d["parameters"]]
    trials=enumerate_trials(d["study_id"],pars,int(d["trial_budget"]))
    print(json.dumps([{"trial_id":t.trial_id,"number":t.number,"params":t.params} for t in trials],indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
