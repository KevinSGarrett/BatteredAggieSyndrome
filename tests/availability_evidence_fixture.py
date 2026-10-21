"""Tiny synthetic C37-shaped availability worlds for tests/test_availability_evidence.py (BAT-733, TP62-A01).

Everything here is synthetic and internal: the database, the five witness files and the profile are built in a
temporary directory and the profile is injected into the reader as a *trusted synthetic profile*; the public builtin
profile C37_2026_AVAILABILITY_ASSERTIONS_V1 is never replaced, and no row here is a real source assertion. The world
keeps the exact closed table schemas and witness formats of the fixed release: both locator prefixes (``row[N]`` in the
tab-separated SEC capture, ``rows[N]`` in the rendered JSON archives), an INITIAL REPORT posting card with two
witnessed claims and a pending card, resolved, name-only, unresolved/quarantined and self-opponent assertions, '-'
cells in both normalized representations (SEC UNKNOWN and null), Exempt and Available texts, an exact duplicate
schedule record (two duplicate opportunity business keys) and a policy with an unstated season. Its population is
declared by hand below (never computed by the reader under test).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from aggie_analytics.availability_evidence import profile as P

POSTED_TEXT = "Report posted on Tuesday, September 22 at 11:00pm ET"
POSTED_UTC = "2026-09-23T03:00:00+00:00"
POSTING_RENDERED = "2026-09-23T10:42:51.193Z"

#: (witness id, raw rows) -- Team, Date, Opponent, Number, Player, then the four stage cells.
RAW = {
    "SEC_RAW_CAPTURE": [["Alabama", "9/12/26", "at Kentucky", "#0", "AK Dear", "Questionable", "Available", "-", "Out"],
                        ["Texas A&M", "9/19/26", "vs. Kentucky", "#5", "Pat Smith", "Out", "Out", "-", "-"]],
    "ACC_ARCHIVE": [["California", "9/25/26", "vs. Clemson", "#1", "Carter Vargas", "Doubtful", "-", "-", "-"],
                    ["Clemson", "9/25/26", "at California", "#11", "Polo Anderson", "Out", "-", "-", "-"],
                    ["Louisville", "9/19/26", "vs. SMU", "", "Kris Hughes", "Out", "Exempt", "Exempt", "Exempt"]],
    "BIG12_ARCHIVE": [["Kansas", "Sat, Sep 19, 2026", "vs. Kansas", "#2", "Kory Amachree", "Out", "Out", "Out", "Out"]],
    "BIGTEN_ARCHIVE": [["Indiana", "9/25/26", "vs. Northwestern", "#0", "Carson Williams", "Out", "-", "-", "-"]],
}
#: per (witness, row): identity state, source-scoped id, contest id (None for the self-opponent label).
PEOPLE = {
    ("SEC_RAW_CAPTURE", 1): ("RESOLVED_NAME_AND_JERSEY_AGREE", "CFBD:1001", "SRC-002:GAME:100"),
    ("SEC_RAW_CAPTURE", 2): ("RESOLVED_NAME_AND_JERSEY_AGREE", "OFFICIAL:Texas A&M:2026:5", "SRC-002:GAME:500"),
    ("ACC_ARCHIVE", 1): ("RESOLVED_NAME_AND_JERSEY_AGREE", "OFFICIAL:California:2026:1", "SRC-002:GAME:200"),
    ("ACC_ARCHIVE", 2): ("RESOLVED_NAME_AND_JERSEY_AGREE", "CFBD:1002", "SRC-002:GAME:200"),
    ("ACC_ARCHIVE", 3): ("RESOLVED_UNIQUE_NAME_JERSEY_NOT_STATED", "OFFICIAL:Louisville:2026:3", "SRC-002:GAME:600"),
    ("BIG12_ARCHIVE", 1): ("RESOLVED_NAME_AND_JERSEY_AGREE", "OFFICIAL:Kansas:2026:2", None),
    ("BIGTEN_ARCHIVE", 1): ("UNRESOLVED_NO_ROSTER_ROW_MATCHES", None, "SRC-002:GAME:700"),
}
POSTING_CLAIMS = {("ACC_ARCHIVE", 1), ("ACC_ARCHIVE", 2)}
#: schedule records (contest, home, home team id, away, away team id, conference home/away, policy, expectation,
#: kickoff before as-of); the second SRC-002:GAME:200 record is an exact duplicate.
SCHEDULE = [
    ("SRC-002:GAME:100", "Kentucky", 96, "Alabama", 333, "SEC", "SEC", None, "NO_POLICY_HELD_FOR_THIS_CONFERENCE", 1),
    ("SRC-002:GAME:500", "Texas A&M", 245, "Kentucky", 96, "SEC", "SEC", None, "NO_POLICY_HELD_FOR_THIS_CONFERENCE", 1),
    ("SRC-002:GAME:200", "California", 25, "Clemson", 228, "ACC", "ACC", "ACC-FB-2026-27", "POLICY_STATES_A_REPORT", 0),
    ("SRC-002:GAME:200", "California", 25, "Clemson", 228, "ACC", "ACC", "ACC-FB-2026-27", "POLICY_STATES_A_REPORT", 0),
    ("SRC-002:GAME:400", "Delaware State", 2169, "Stony Brook", 2619, "MEAC", "Coastal Athletic", None,
     "NO_POLICY_HELD_FOR_THIS_CONFERENCE", 1),
]

POPULATION = {
    "statements": 28, "source_player_rows": 7, "source_cells": 28,
    "statements_by_conference": {"ACC": 12, "Big 12": 4, "Big Ten": 4, "SEC": 8},
    "statements_by_stage": {stage: 7 for stage in P.STAGES},
    "presence": {"PUBLISHED_EMPTY": 12, "PUBLISHED_VALUE": 16},
    "source_empty_representations": {"normalized_null": 9, "normalized_unknown_sec": 3},
    "status_texts": {"-": 12, "Available": 1, "Doubtful": 1, "Exempt": 3, "Out": 10, "Questionable": 1},
    "effective_time_known": 0, "pit_admitted": 0, "publication_claims": 2,
    "source_person_id_prefixes": {"CFBD": 8, "OFFICIAL": 16, "null": 4},
    "joint_person_contest": {"RETAINED_PERSON_AND_CONTEST_CLAIMS": 20, "PERSON_CLAIM_UNRESOLVED": 4,
                             "CONTEST_CLAIM_NOT_QUALIFIED": 4, "PERSON_UNRESOLVED_AND_CONTEST_NOT_QUALIFIED": 0},
    "identity_states": {"RESOLVED_NAME_AND_JERSEY_AGREE": 20, "RESOLVED_UNIQUE_NAME_JERSEY_NOT_STATED": 4,
                        "UNRESOLVED_NO_ROSTER_ROW_MATCHES": 4},
    "contest_states": {"CONTEST_BOUND": 24, "CONTEST_LABEL_NAMES_THE_PROGRAM_ITSELF": 4},
    "quarantined": 4,
    "opportunity_occurrences": 10, "opportunity_distinct_business_keys": 8,
    "opportunity_singleton_business_keys": 6, "opportunity_duplicate_business_key_groups": 2,
    "schedule_record_occurrences": 5, "schedule_distinct_game_ids": 4, "schedule_duplicate_game_ids": 1,
    "opportunity_states": {"REPORT_STATEMENTS_INGESTED": 6, "UNKNOWN_NOT_HEALTHY": 4},
    "policy_expected_occurrences": 4, "policy_expected_before_as_of_occurrences": 0,
    "policy_expected_ingested_occurrences": 4,
    "distinct_key_inventory": {"opportunity_states": {"REPORT_STATEMENTS_INGESTED": 4, "UNKNOWN_NOT_HEALTHY": 4},
                               "policy_expected": 2, "policy_expected_before_as_of": 0,
                               "policy_expected_ingested": 2},
    "policies": 2,
}

NORMALIZED = {"Out": "OUT", "Questionable": "QUESTIONABLE", "Available": "AVAILABLE", "Doubtful": "DOUBTFUL",
              "Exempt": "EXEMPT", "Probable": "PROBABLE", "Game Time Decision": "GAME_TIME_DECISION"}


def _iso(date_text: str) -> str:
    from aggie_analytics.availability_evidence.evidence import parse_report_date  # noqa: PLC0415
    return parse_report_date(date_text).isoformat()


def _label(date_text: str, opponent: str) -> str:
    from aggie_analytics.availability_evidence.evidence import parse_report_date  # noqa: PLC0415
    day = parse_report_date(date_text)
    return f"{day.month}/{day.day}/{day.year % 100:02d} {opponent}"


def statement_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wid in ("SEC_RAW_CAPTURE", "ACC_ARCHIVE", "BIG12_ARCHIVE", "BIGTEN_ARCHIVE"):
        spec = P.WITNESSES[wid]
        for index, raw in enumerate(RAW[wid], 1):
            state, pid, contest_id = PEOPLE[(wid, index)]
            resolved = state.startswith("RESOLVED_")
            if contest_id is None:
                contest = {"date_as_written": _iso(raw[1]), "opponent_as_written": raw[2].split(" ", 1)[1],
                           "season": 2026, "state": "CONTEST_LABEL_NAMES_THE_PROGRAM_ITSELF"}
            else:
                contest = {"canonical_contest_id": contest_id, "conference_game": True,
                           "date_as_written": _iso(raw[1]), "season": 2026, "state": "CONTEST_BOUND"}
            identity = {"canonical_player_id": pid, "confidence": "HIGH" if resolved else None, "detail": "synthetic",
                        "jersey_matches": 1, "matched_on_suffix_stripped_name_only": False, "name_matches": 1,
                        "refused_rows_of_this_program_in_another_season": 0, "refused_rows_without_a_program": 0,
                        "roster_rows_considered": 3, "season": 2026, "state": state}
            for stage in P.STAGES:
                cell = raw[P.SOURCE_HEADER.index(P.STAGE_COLUMNS[stage])]
                claim = (wid, index) in POSTING_CLAIMS and stage == "initial_status"
                rows.append({
                    "availability_row_id": len(rows) + 1, "conference": spec["conference"],
                    "contest": json.dumps(contest, sort_keys=True), "contest_label": _label(raw[1], raw[2]),
                    "effective_utc": None, "embedded_in": spec["embedded_in"], "exact_status_text": cell,
                    "identity": json.dumps(identity, sort_keys=True), "identity_version": "BAS-AVAILABILITY-IDENTITY-v37.1",
                    "jersey": raw[3], "label": "synthetic", "no_medical_detail": 1,
                    "normalized_status": ("UNKNOWN" if wid == "SEC_RAW_CAPTURE" else None) if cell == "-"
                    else NORMALIZED[cell], "out_does_not_imply_injury": 1, "pit_admitted": 0, "player_name": raw[4],
                    "presence": "PUBLISHED_EMPTY" if cell == "-" else "PUBLISHED_VALUE", "program": raw[0],
                    "program_as_written": raw[0],
                    "publication_basis": f"ACC current view: '{POSTED_TEXT}'" if claim else None,
                    "publication_time_established": 1 if claim else 0, "publication_utc": POSTED_UTC if claim else None,
                    "quarantined": 0 if resolved else 1,
                    "report_vintage_retrieval_utc": spec["retrieval_observation_utc"],
                    "rights_state": "PUBLIC_CONFERENCE_REPORT_RESEARCH_USE", "season_out_carried_from": None,
                    "source_locator": f"{spec['locator_prefix']}[{index}].{stage}", "source_sha256": None,
                    "source_url": spec["source_url"], "stage": stage, "_witness": wid})
    return rows


def opportunity_rows(statements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ingested: dict[tuple[str, str], int] = {}
    for r in statements:
        contest = json.loads(r["contest"])
        if contest.get("canonical_contest_id"):
            key = (contest["canonical_contest_id"], r["program"])
            ingested[key] = ingested.get(key, 0) + 1
    out = []
    for cid, home, home_id, away, away_id, hconf, aconf, policy, expectation, before in SCHEDULE:
        for side, program, team_id, conference in (("home", home, home_id, hconf), ("away", away, away_id, aconf)):
            count = ingested.get((cid, program), 0)
            out.append({"absent_players": "UNKNOWN_NOT_HEALTHY" if not count else "UNKNOWN: completeness not established",
                        "canonical_contest_id": cid, "classification": "fcs" if conference in ("MEAC",
                                                                                               "Coastal Athletic") else
                        "fbs", "conference": conference, "conference_game": 1, "governing_policy": policy,
                        "kickoff_before_as_of": before, "kickoff_utc": "2026-09-26T00:00:00.000Z", "label": "synthetic",
                        "policy_covers_2026": "STATED" if policy else None, "program": program,
                        "report_expectation": expectation, "side": side,
                        "state": "REPORT_STATEMENTS_INGESTED" if count else "UNKNOWN_NOT_HEALTHY",
                        "statements_ingested": count, "team_id": team_id})
    return out


def policy_rows() -> list[dict[str, Any]]:
    base = {"absence_rule_applies_only_to": "an actual, complete, current report of this conference for this contest",
            "first_report_contest_date": None, "format": "PDF", "label": "synthetic", "non_conference": "OPTIONAL",
            "quotes_verified_in_extracted_text": json.dumps({"quote": True}), "scope": "CONFERENCE_GAMES",
            "source_kind": "SYNTHETIC", "source_path": "synthetic", "supersedes": None, "url": "https://example.invalid/p",
            "version_as_stated": None, "vocabulary_gameday": json.dumps(["Available", "Out"]),
            "vocabulary_observed_in_ingested_reports": None, "vocabulary_pregame": json.dumps(["Out", "Doubtful"])}
    return [{**base, "absence_rule": "ABSENT_FROM_A_REPORT_PRESUMED_AVAILABLE", "conference": "ACC",
             "covers_2026": "STATED", "policy_id": "ACC-FB-2026-27", "policy_season": 2026,
             "quotes": json.dumps(["quote"]), "schedule": json.dumps(["initial"]), "source_sha256": "a" * 64},
            {**base, "absence_rule": "NOT_STATED", "conference": "Conference USA", "covers_2026": "PAGE_UNDATED",
             "policy_id": "CUSA-FB", "policy_season": None, "quotes": json.dumps(["other quote"]),
             "schedule": json.dumps([]), "source_sha256": "b" * 64,
             "vocabulary_observed_in_ingested_reports": json.dumps(["Out"])}]


def _archive_bytes(wid: str) -> bytes:
    spec = P.WITNESSES[wid]
    doc = {"dom": "<html>synthetic</html>", "embedded_in": spec["embedded_in"],
           "rendered_utc": spec["retrieval_observation_utc"], "rows": [list(P.SOURCE_HEADER), *RAW[wid]],
           "text": "synthetic", "url": spec["source_url"]}
    return json.dumps(doc).encode("utf-8")


def posting_bytes() -> bytes:
    spec = P.WITNESSES["ACC_CURRENT_POSTING"]
    cards = [{"text": f"INITIAL REPORT\n{POSTED_TEXT}\nOUT\nS #11 Polo Anderson\nDOUBTFUL\nRB #1 Carter Vargas\n"
                      f"FRIDAY, SEPTEMBER 25 | 10:30 PM ET | BERKELEY, CA",
              "columns": [{"team": "Clemson", "text": "OUT\nS #11 Polo Anderson"},
                          {"team": "California", "text": "DOUBTFUL\nRB #1 Carter Vargas"}]},
             {"text": "REPORT PENDING\nReport expected on Wednesday, September 23 at 8:00pm ET\n"
                      "SATURDAY, SEPTEMBER 26 | 12:00 PM ET | LOUISVILLE, KY",
              "columns": [{"team": "Wake Forest", "text": ""}, {"team": "Louisville", "text": ""}]}]
    doc = {"url": spec["source_url"], "embedded_in": spec["embedded_in"], "h1": "Games of September 25 - September 26, 2026",
           "rendered_utc": spec["retrieval_observation_utc"], "cards": cards}
    return json.dumps(doc).encode("utf-8")


def witness_bytes() -> dict[str, bytes]:
    out = {"SEC_RAW_CAPTURE": ("\t".join(P.SOURCE_HEADER) + "\n" + "".join("\t".join(r) + "\n" for r in
                                                                         RAW["SEC_RAW_CAPTURE"])).encode("utf-8")}
    for wid in ("ACC_ARCHIVE", "BIG12_ARCHIVE", "BIGTEN_ARCHIVE"):
        out[wid] = _archive_bytes(wid)
    out["ACC_CURRENT_POSTING"] = posting_bytes()
    return out


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_database(path: Path, statements: list[dict[str, Any]], opportunities: list[dict[str, Any]],
                   policies: list[dict[str, Any]], *, extra_table: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        for grain, rows in (("statement", statements), ("opportunity", opportunities), ("policy", policies)):
            spec = P.TABLES[grain]
            columns = list(spec["columns"])
            conn.execute(f'CREATE TABLE "{spec["table"]}" (' + ", ".join(f'"{c}"' for c in columns) + ")")
            conn.executemany(f'INSERT INTO "{spec["table"]}" VALUES (' + ", ".join("?" for _ in columns) + ")",
                             [[r[c] for c in columns] for r in rows])
        if extra_table:
            conn.execute('CREATE TABLE "release_identity" ("key", "value")')
            conn.execute('INSERT INTO "release_identity" VALUES (?, ?)', ("synthetic", "not a release"))
        conn.commit()
    finally:
        conn.close()


class World:
    """One synthetic world in ``root``: data root, database and the matching trusted synthetic profile."""

    def __init__(self, root: Path, *, mutate_statements=None, mutate_opportunities=None, mutate_policies=None,
                 mutate_witnesses=None) -> None:
        self.root = Path(root)
        self.data_root = self.root / "data"
        self.witnesses = witness_bytes()
        if mutate_witnesses:
            mutate_witnesses(self.witnesses)
        for wid, data in self.witnesses.items():
            target = self.data_root.joinpath(*P.WITNESSES[wid]["relative_path"].split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        statements = statement_rows()
        shas = {wid: hashlib.sha256(data).hexdigest() for wid, data in self.witnesses.items()}
        for r in statements:
            r["source_sha256"] = shas[r.pop("_witness")]
        opportunities = opportunity_rows(statements)
        policies = policy_rows()
        for rows, mutate in ((statements, mutate_statements), (opportunities, mutate_opportunities),
                             (policies, mutate_policies)):
            if mutate:
                mutate(rows)
        self.statements, self.opportunities, self.policies = statements, opportunities, policies
        self.database = self.root / "db" / "synthetic_release.sqlite"
        write_database(self.database, statements, opportunities, policies)
        self.profile = synthetic_profile(self.database, self.witnesses)


def synthetic_profile(database: Path, witnesses: dict[str, bytes], population: dict[str, Any] | None = None
                      ) -> dict[str, Any]:
    """The builtin profile's structure with the synthetic world's identities and hand-declared population."""
    prof = copy.deepcopy(P.PROFILE)
    prof["profile_id"] = "SYNTHETIC_TEST_PROFILE_NOT_PUBLIC"
    prof["database"] = {**prof["database"], "sha256": sha256_file(database), "bytes": Path(database).stat().st_size}
    for wid, data in witnesses.items():
        prof["witnesses"][wid]["sha256"] = hashlib.sha256(data).hexdigest()
        prof["witnesses"][wid]["bytes"] = len(data)
        if prof["witnesses"][wid]["player_rows"] is not None:
            prof["witnesses"][wid]["player_rows"] = len(RAW[wid])
    prof["tables"]["statement"]["rows"] = 28
    prof["tables"]["opportunity"]["rows"] = 10
    prof["tables"]["policy"]["rows"] = 2
    prof["population"] = copy.deepcopy(POPULATION if population is None else population)
    return prof


def retrust(world: World) -> dict[str, Any]:
    """A trusted synthetic profile for the world's *current* database bytes (exercises the deeper internal checks that
    the public whole-file anchor always pre-empts)."""
    prof = copy.deepcopy(world.profile)
    prof["database"]["sha256"] = sha256_file(world.database)
    prof["database"]["bytes"] = world.database.stat().st_size
    return prof
