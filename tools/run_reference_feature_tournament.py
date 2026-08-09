from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.feature_tournament import FeatureTournamentEvidence,research_disposition

def main():
    ap=argparse.ArgumentParser();ap.add_argument("evidence",type=Path)
    a=ap.parse_args();e=FeatureTournamentEvidence(**json.loads(a.evidence.read_text()))
    print(json.dumps({"family_id":e.family_id,"research_disposition":research_disposition(e)},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
