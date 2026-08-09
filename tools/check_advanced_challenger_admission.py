from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.advanced_challengers import ChallengerAdmissionEvidence

def main():
    ap=argparse.ArgumentParser();ap.add_argument("evidence",type=Path);a=ap.parse_args()
    e=ChallengerAdmissionEvidence(**json.loads(a.evidence.read_text()));state,reasons=e.evaluate()
    print(json.dumps({"state":state,"reasons":reasons},indent=2));return 0 if state=="ADMITTED_RESEARCH_ONLY" else 2
if __name__=="__main__":raise SystemExit(main())
