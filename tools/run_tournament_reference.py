from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aggie_analytics.experimentation.tournaments import TournamentSpec, TournamentEntry, rank_entries

def main() -> int:
    ap=argparse.ArgumentParser(description="Reference development-only tournament ranker. Never promotes.")
    ap.add_argument("tournament_json", type=Path)
    args=ap.parse_args()
    data=json.loads(args.tournament_json.read_text(encoding="utf-8"))
    spec=TournamentSpec(**data["spec"])
    entries=[TournamentEntry(**row) for row in data["entries"]]
    ranked=rank_entries(spec, entries)
    print(json.dumps({
        "tournament_id":spec.tournament_id,
        "research_only":True,
        "promotion_allowed":False,
        "ranking":[e.entry_id for e in ranked],
    },indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
