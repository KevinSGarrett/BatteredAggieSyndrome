"""Cycle34 R34-07: ingest this session's real acquired career-join and
program-season data into the actual query/episode model (`query.py`'s
`staff_role_cells` table via `load_import`), instead of leaving it as
markdown receipts.

Source data: transcribed verbatim from this session's own real acquisition
receipts (`R34_11_12_ACQUISITION_RECEIPTS.md`'s 28 program-season Wikipedia
fetches, `R34_06_11_ACQUISITION_CORRECTIONS.md`'s and
`R34_06_ROUND7_JOIN_ATTEMPTS.md`'s real person-biography join attempts run
through `career_identity.join_occupant_to_pages`). Every row below traces to
a specific WebFetch receipt already on record; nothing here is invented.

READ-ONLY against the repository. Output (the sqlite database + a JSON
ingestion summary) goes ONLY under
C:\\BatteredAggieSyndrome.data\\ops\\cycle34\\...\\pipeline_output\\.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33 import query as q  # noqa: E402

OUTPUT_DIR = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle34\20260919T_R34_receipts\pipeline_output"
)
DB_PATH = OUTPUT_DIR / "R34_07_CAREER_INGEST.sqlite"
SUMMARY_PATH = OUTPUT_DIR / "R34_07_CAREER_INGEST_SUMMARY.json"

SOURCE_CLASS = "WIKIPEDIA_ATTRIBUTED_RETROSPECTIVE_OR_CURRENT"

# ---------------------------------------------------------------------------
# 28 real program-season roster fetches (R34-11), transcribed verbatim from
# R34_11_12_ACQUISITION_RECEIPTS.md rows 1-28. Each (team, season) row's
# HC/OC/DC entries become separate role_cells rows.
# ---------------------------------------------------------------------------
PROGRAM_SEASONS: list[dict[str, Any]] = [
    {"team": "Air Force", "season": "2018", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2018_Air_Force_Falcons_football_team",
     "roles": [("HC", "Troy Calhoun"), ("OC", "Mike Thiessen"), ("DC", "John Rudzinski")]},
    {"team": "Lehigh", "season": "2000", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2000_Lehigh_Mountain_Hawks_football_team",
     "roles": [("HC", "Kevin Higgins"), ("DC", "Tom Gilmore")]},
    {"team": "Idaho", "season": "2019", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2019_Idaho_Vandals_football_team",
     "roles": [("HC", "Paul Petrino"), ("OC", "Kris Cinkovich"), ("DC", "Mike Breske")]},
    {"team": "Utah", "season": "2008", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2008_Utah_Utes_football_team",
     "roles": [("HC", "Kyle Whittingham"), ("OC", "Andy Ludwig"), ("DC", "Gary Andersen")]},
    {"team": "Eastern Washington", "season": "2010", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2010_Eastern_Washington_Eagles_football_team",
     "roles": [("HC", "Beau Baldwin"), ("OC", "Aaron Best"), ("DC", "John Graham")]},
    {"team": "Texas A&M", "season": "2012", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2012_Texas_A%26M_Aggies_football_team",
     "roles": [("HC", "Kevin Sumlin"), ("OC", "Kliff Kingsbury"), ("DC", "Mark Snyder")]},
    {"team": "Appalachian State", "season": "2007", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2007_Appalachian_State_Mountaineers_football_team",
     "roles": [("HC", "Jerry Moore"), ("DC", "John Wiley")]},
    {"team": "Texas A&M", "season": "2001", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2001_Texas_A%26M_Aggies_football_team",
     "roles": [("HC", "R. C. Slocum"), ("OC", "Dino Babers"), ("DC", "Mike Hankwitz")]},
    {"team": "Montana", "season": "2003", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2003_Montana_Grizzlies_football_team",
     "roles": [("HC", "Bobby Hauck"), ("OC", "Rob Phenicie")]},
    {"team": "Colorado", "season": "2002", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2002_Colorado_Buffaloes_football_team",
     "roles": [("HC", "Gary Barnett"), ("OC", "Shawn Watson"), ("DC", "Tom McMahon"), ("DC", "Vince Okruch")]},
    {"team": "North Dakota State", "season": "2015", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2015_North_Dakota_State_Bison_football_team",
     "roles": [("HC", "Chris Klieman"), ("OC", "Tim Polasek"), ("DC", "Matt Entz")]},
    {"team": "Western Michigan", "season": "2016", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2016_Western_Michigan_Broncos_football_team",
     "roles": [("HC", "P. J. Fleck"), ("OC", "Kirk Ciarrocca"), ("DC", "Ed Pinkham")]},
    {"team": "James Madison", "season": "2017", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2017_James_Madison_Dukes_football_team",
     "roles": [("HC", "Mike Houston"), ("OC", "Donnie Kirkpatrick"), ("DC", "Bob Trott")]},
    {"team": "UAB", "season": "2014", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2014_UAB_Blazers_football_team",
     "roles": [("HC", "Bill Clark"), ("OC", "Bryant Vincent"), ("DC", "Duwan Walker")]},
    {"team": "Sam Houston", "season": "2021", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2021_Sam_Houston_Bearkats_football_team",
     "roles": [("HC", "K. C. Keeler"), ("OC", "Ryan Carty"), ("DC", "Clayton Carlin")]},
    {"team": "Sam Houston", "season": "2023", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2023_Sam_Houston_Bearkats_football_team",
     "roles": [("HC", "K. C. Keeler"), ("OC", "Brad Cornelsen"), ("DC", "Clayton Carlin"), ("DC", "Joe Morris")]},
    {"team": "South Dakota State", "season": "2022", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2022_South_Dakota_State_Jackrabbits_football_team",
     "roles": [("HC", "John Stiegelmeier"), ("OC", "Zach Lujan"), ("DC", "Jimmy Rogers")]},
    {"team": "UMass", "season": "2021", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2021_UMass_Minutemen_football_team",
     "roles": [("HC", "Walt Bell"), ("HC", "Alex Miller"), ("DC", "Tommy Restivo")]},
    {"team": "Idaho", "season": "2017", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2017_Idaho_Vandals_football_team",
     "roles": [("HC", "Paul Petrino"), ("OC", "Kris Cinkovich"), ("DC", "Mike Breske")]},
    {"team": "UAB", "season": "2017", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2017_UAB_Blazers_football_team",
     "roles": [("HC", "Bill Clark"), ("OC", "Les Koenning"), ("DC", "David Reeves")]},
    {"team": "Kansas State", "season": "2003", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2003_Kansas_State_Wildcats_football_team",
     "roles": [("HC", "Bill Snyder"), ("OC", "Del Miller"), ("OC", "Greg Peterson"), ("DC", "Bret Bielema"), ("DC", "Bob Elliott")]},
    {"team": "Youngstown State", "season": "2016", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2016_Youngstown_State_Penguins_football_team",
     "roles": [("HC", "Bo Pelini"), ("OC", "Shane Montgomery"), ("DC", "Carl Pelini")]},
    {"team": "Liberty", "season": "2019", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2019_Liberty_Flames_football_team",
     "roles": [("HC", "Hugh Freeze"), ("OC", "Kent Austin"), ("DC", "Scott Symons")]},
    {"team": "Appalachian State", "season": "2004", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2004_Appalachian_State_Mountaineers_football_team",
     "roles": [("HC", "Jerry Moore")]},
    {"team": "Texas A&M", "season": "2025", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2025_Texas_A%26M_Aggies_football_team",
     "roles": [("HC", "Mike Elko"), ("OC", "Collin Klein"), ("DC", "Jay Bateman")]},
    {"team": "North Dakota State", "season": "2025", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2025_North_Dakota_State_Bison_football_team",
     "roles": [("HC", "Tim Polasek"), ("OC", "Dan Larson"), ("DC", "Grant Olson")]},
    {"team": "Air Force", "season": "2025", "div": "FBS", "url": "https://en.wikipedia.org/wiki/2025_Air_Force_Falcons_football_team",
     "roles": [("HC", "Troy Calhoun"), ("OC", "Mike Thiessen"), ("DC", "Brian Knorr")]},
    {"team": "Lehigh", "season": "2025", "div": "FCS", "url": "https://en.wikipedia.org/wiki/2025_Lehigh_Mountain_Hawks_football_team",
     "roles": [("HC", "Kevin Cahill"), ("OC", "Dan Hunt"), ("DC", "Rich Nagy")]},
]

# ---------------------------------------------------------------------------
# Real person-biography join attempts run through
# career_identity.join_occupant_to_pages (round 5 + round 7 of this session).
# (person, employer_queried, team_key, season_key, verified_bool, note)
# team_key/season_key link a join result back to one of the PROGRAM_SEASONS
# rows above where that binding is evidenced, when applicable.
# ---------------------------------------------------------------------------
JOIN_ATTEMPTS: list[dict[str, Any]] = [
    {"person": "Troy Calhoun", "employer": "Air Force", "team": "Air Force", "season": "2018", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Kevin Higgins", "employer": "Lehigh", "team": "Lehigh", "season": "2000", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Bill Snyder", "employer": "Kansas State", "team": "Kansas State", "season": "2003", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Troy Calhoun", "employer": "Texas A&M", "team": None, "season": None, "verified": False, "outcome": "FOOTBALL_PAGE_ORG_IDENTITY_UNBOUND_TRUE_NEGATIVE"},
    {"person": "P. J. Fleck", "employer": "Western Michigan", "team": "Western Michigan", "season": "2016", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Kyle Whittingham", "employer": "Utah", "team": "Utah", "season": "2008", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Kevin Sumlin", "employer": "Texas A&M", "team": "Texas A&M", "season": "2012", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Chris Klieman", "employer": "North Dakota State", "team": "North Dakota State", "season": "2015", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Bill Clark", "employer": "UAB", "team": "UAB", "season": "2014", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Hugh Freeze", "employer": "Liberty", "team": "Liberty", "season": "2019", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "John Stiegelmeier", "employer": "South Dakota State", "team": "South Dakota State", "season": "2022", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Bobby Hauck", "employer": "Montana", "team": "Montana", "season": "2003", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Gary Barnett", "employer": "Colorado", "team": "Colorado", "season": "2002", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "K. C. Keeler", "employer": "Sam Houston", "team": "Sam Houston", "season": "2021", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "K. C. Keeler", "employer": "Sam Houston State", "team": "Sam Houston", "season": "2021", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Bo Pelini", "employer": "Youngstown State", "team": "Youngstown State", "season": "2016", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Mike Elko", "employer": "Texas A&M", "team": "Texas A&M", "season": "2025", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Walt Bell", "employer": "UMass", "team": "UMass", "season": "2021", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "Paul Petrino", "employer": "Idaho", "team": "Idaho", "season": "2019", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
    {"person": "R. C. Slocum", "employer": "Texas A&M", "team": "Texas A&M", "season": "2001", "verified": True, "outcome": "EVIDENCE_BOUND_CAREER_JOIN"},
]


def _make_role_cell(*, obs_id: str, team: str, season: str, role: str, person: str,
                     url: str, div: str, verified: bool, disposition: str) -> dict[str, Any]:
    return {
        "observation_id": obs_id,
        "canonical_claim_id": None,
        "source_file": url,
        "team": team,
        "team_id_source": team,
        "season": season,
        "role_column": role,
        "person": person,
        "source_title": f"{season} {team} football team (Wikipedia)",
        "disposition": disposition,
        "support_column": True,
        "principal_role_blocked": False,
        "source_class": SOURCE_CLASS,
        "pit_admitted": False,
        "cell_text": f"{person} ({role})",
        "source_subdivision": div,
        "verified": verified,
    }


def build_role_cells() -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    verified_pairs = {
        (a["person"], a["team"], a["season"])
        for a in JOIN_ATTEMPTS
        if a["verified"] and a["team"] and a["season"]
    }
    for row in PROGRAM_SEASONS:
        for idx, (role, person) in enumerate(row["roles"]):
            key = (person, row["team"], row["season"])
            verified = key in verified_pairs
            cells.append(
                _make_role_cell(
                    obs_id=f"R34_07_{row['team'].replace(' ', '_').replace('&', 'AND')}_{row['season']}_{role}_{idx}",
                    team=row["team"],
                    season=row["season"],
                    role=role,
                    person=person,
                    url=row["url"],
                    div=row["div"],
                    verified=verified,
                    disposition="RESOLVED_CAREER_JOIN_VERIFIED" if verified else "ROSTER_OBSERVATION_UNRESOLVED",
                )
            )
    # The one deliberate true-negative control (Troy Calhoun / Texas A&M) is
    # recorded too, as an explicitly-rejected observation -- not silently
    # dropped -- with no team/season binding (the join correctly found none).
    cells.append(
        {
            "observation_id": "R34_07_CONTROL_troy_calhoun_texas_am_rejected",
            "canonical_claim_id": None,
            "source_file": "https://en.wikipedia.org/wiki/Troy_Calhoun",
            "team": None,
            "team_id_source": None,
            "season": None,
            "role_column": None,
            "person": "Troy Calhoun",
            "source_title": "Troy Calhoun (Wikipedia biography) -- deliberate negative control",
            "disposition": "CORRECTLY_REJECTED_NO_EMPLOYER_MATCH",
            "support_column": True,
            "principal_role_blocked": False,
            "source_class": SOURCE_CLASS,
            "pit_admitted": False,
            "cell_text": "Troy Calhoun queried against Texas A&M (employer he never had) -- FOOTBALL_PAGE_ORG_IDENTITY_UNBOUND, correct rejection",
            "source_subdivision": None,
            "verified": False,
        }
    )
    return cells


def run() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = q.connect_for_import(DB_PATH)
    role_cells = build_role_cells()
    inserted = q.load_import(conn, {"role_cells": role_cells})

    # Prove it is genuinely queryable through the real query.py API, not just
    # written -- one team_staff() lookup and one coach_career() lookup, both
    # against real rows just inserted.
    conn.close()
    ro = q.connect(DB_PATH, readonly=True)
    sample_team_query = q.team_staff(ro, team="Texas A&M", season="2012")
    sample_career_query = q.coach_career(ro, person="Troy Calhoun")
    ro.close()

    verified_count = sum(1 for c in role_cells if c["verified"])
    summary = {
        "artifact_type": "CYCLE34_R34_07_CAREER_INGEST_SUMMARY",
        "method": "real_acquisition_receipts_converted_to_staff_role_cells_and_loaded_via_query.load_import",
        "database_path": str(DB_PATH),
        "rows_inserted": inserted,
        "rows_verified_career_join": verified_count,
        "rows_roster_observation_unresolved": inserted - verified_count,
        "program_seasons_source_count": len(PROGRAM_SEASONS),
        "join_attempts_source_count": len(JOIN_ATTEMPTS),
        "sample_query_team_staff_texas_am_2012": sample_team_query,
        "sample_query_coach_career_troy_calhoun": sample_career_query,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True, default=str))
