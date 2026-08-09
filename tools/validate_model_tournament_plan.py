from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.model_tournament import ModelEntrant,ModelTournamentPlan

def main():
    ap=argparse.ArgumentParser();ap.add_argument("plan",type=Path);a=ap.parse_args()
    d=json.loads(a.plan.read_text());d["entrants"]=[ModelEntrant(**x) for x in d["entrants"]]
    ModelTournamentPlan(**d).validate();print("PASS");return 0
if __name__=="__main__":raise SystemExit(main())
