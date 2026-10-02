"""Synthetic national-population parents and history-prefix builds for the BAT-711 tests (Cycle #39 TP39-A01).

Not a test module (no ``test`` prefix). The parent is built with the accepted BAT-710 population builder
(``build_query_database`` and ``materialize``), so the history producer and the independent validator read a real
parent schema. Short population directory names keep temporary paths far below the Windows path limit; the
``<root>/sha256/<id>`` layout is unchanged.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data import national_di_population as pop  # noqa: E402

CONTRACT_PATH = ROOT / "configs" / "national_history_prefix_2016_2023_contract.json"
BUILDER_PATH = ROOT / "tools" / "build_national_history_prefix.py"
VALIDATOR_PATH = ROOT / "tools" / "validate_national_history_prefix.py"
PARENT_CONTRACT_SHA = "c" * 64
M1, M2 = "1" * 64, "2" * 64

#: org id -> (display name, division label); org 3 is renamed mid-season (same organization key).
TEAMS = {"1": ("Alpha", "FBS"), "2": ("Bravo", "FBS"), "3": ("Charlie St.", "FBS"), "4": ("Delta", "FCS"),
         "5": ("Echo", "FBS"), "6": ("Foxtrot", "FCS")}


def load_tool(path: Path, name: str) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def builder() -> Any:
    return load_tool(BUILDER_PATH, "bas_history_prefix_builder")


def validator() -> Any:
    return load_tool(VALIDATOR_PATH, "bas_history_prefix_validator")


def contest(key: str, season: int, date: str, a: str, b: str, a_pts: Any, b_pts: Any, *, term: str = "FALL",
            site: str = "HOME_A", status: str = "COMPLETED", competitive: bool = True,
            disposition: str = "VERIFIED_PRESENT", state: str = "RECONCILED_2016_2023", a_name: str | None = None,
            observed: list[str] | None = None, a_key: str | None = None, b_key: str | None = None,
            b_label: str | None = None) -> dict[str, Any]:
    a_label = TEAMS[a][1]
    b_label = b_label or (TEAMS[b][1] if b in TEAMS else "NON_NCAA")
    return {"contest_key": key, "ncaa_contest_id": key.split(":", 1)[1], "season": season, "term": term,
            "contest_date": date, "site": site, "neutral_site_text": "Fixture Bowl" if site == "NEUTRAL" else None,
            "contest_status": status, "competitive": competitive, "a_org_id": a, "a_team_season_id": f"ts{a}-{season}",
            "a_team_name": a_name or TEAMS[a][0], "a_division_label": a_label, "a_membership": "DIVISION_I",
            "a_points": a_pts, "b_org_id": b if b in TEAMS else None, "b_team_season_id": f"ts{b}-{season}",
            "b_team_name": TEAMS[b][0] if b in TEAMS else b, "b_division_label": b_label,
            "b_membership": "DIVISION_I" if b in TEAMS else "NON_NCAA", "b_points": b_pts,
            "classification_pair": "-".join(sorted((a_label, b_label))), "mirror_observation_count": 2,
            "source": "NCAA_GRAPH", "cfbd_game_ids": [f"9{key.split(':')[1]}"], "reconciliation_state": state,
            "disposition": disposition, "disposition_reason": None, "exposure": "X", "conflict_fields": [],
            "flags": [], "event_labels": [], "a_key": a_key or f"org:{a}",
            "b_key": b_key or (f"org:{b}" if b in TEAMS else f"ext:{b.lower()}"),
            "contest_dates_observed": observed if observed is not None else [date], "mirror_scores_observed": None,
            "contest_statuses_observed": None, "cfbd_observation": None}


def fixture_contests() -> list[dict[str, Any]]:
    """Positive classes of TP39-A01 section 3 in one synthetic national world."""
    return [
        # 2018: FBS-FCS history, tie, neutral site, cold start, rename, doubleheader, canceled/forfeit/unscored.
        contest("ncaa:101", 2018, "2018-09-01", "1", "4", 35, 10),
        contest("ncaa:102", 2018, "2018-09-01", "2", "5", 20, 20),
        contest("ncaa:103", 2018, "2018-09-08", "1", "2", 28, 21, site="NEUTRAL"),
        contest("ncaa:104", 2018, "2018-09-08", "3", "5", 14, 17),
        contest("ncaa:113", 2018, "2018-09-15", "5", "4", 42, 7),
        contest("ncaa:105", 2018, "2018-09-15", "3", "1", 10, 31, a_name="Charlie State"),
        contest("ncaa:106", 2018, "2018-09-22", "2", "3", 13, 9),
        contest("ncaa:107", 2018, "2018-09-22", "2", "5", 17, 24),
        contest("ncaa:108", 2018, "2018-09-29", "1", "5", None, None, status="CANCELED", competitive=False,
                disposition="CANDIDATE_ONLY", state="NOT_RECONCILED_NON_COMPETITIVE"),
        contest("ncaa:109", 2018, "2018-10-06", "3", "5", 1, 0, status="FORFEIT", competitive=False),
        contest("ncaa:110", 2018, "2018-10-06", "1", "2", None, None, status="UNSCORED"),
        contest("ncaa:112", 2018, "2018-10-06", "4", "6", 27, 24),
        contest("ncaa:111", 2018, "2018-10-13", "1", "5", 24, 3),
        contest("ncaa:114", 2018, "2018-11-03", "5", "2", 30, 27),
        # 2017: invalid date, two observed dates, unstable key, identical keys, negative score, then a target.
        contest("ncaa:301", 2017, "2017-02-30", "1", "2", 10, 7),
        contest("ncaa:302", 2017, "2017-09-02", "1", "3", 21, 14, observed=["2017-09-02", "2017-09-03"]),
        contest("ncaa:304", 2017, "2017-09-09", "1", "West Tech", 45, 0),
        contest("ncaa:305", 2017, "2017-09-09", "3", "5", 7, 6, b_key="org:3"),
        contest("ncaa:306", 2017, "2017-09-09", "2", "5", -3, 10),
        contest("ncaa:303", 2017, "2017-09-16", "1", "2", 17, 14),
        # 2020-21 academic year: a January 2021 bowl and spring 2021 games keep season label 2020.
        contest("ncaa:201", 2020, "2020-10-03", "1", "2", 21, 14),
        contest("ncaa:202", 2020, "2021-01-02", "1", "5", 28, 27),
        contest("ncaa:203", 2020, "2021-03-06", "4", "6", 14, 10, term="SPRING"),
        contest("ncaa:204", 2020, "2021-03-13", "1", "4", 38, 3, term="SPRING"),
        contest("ncaa:205", 2020, "2021-04-03", "1", "2", 24, 23, term="SPRING"),
        # Protected/exposed seasons: never targets or priors.
        contest("ncaa:401", 2024, "2024-08-31", "1", "2", 31, 30, disposition="CANDIDATE_ONLY",
                state="SINGLE_SOURCE_UNRECONCILED"),
        contest("ncaa:402", 2025, "2025-08-30", "2", "5", 14, 13, disposition="CANDIDATE_ONLY",
                state="SINGLE_SOURCE_UNRECONCILED"),
    ]


def subsets_for(contests: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {"FBS_ESTIMAND_SUBSET": [c["contest_key"] for c in contests
                                    if c["a_division_label"] == "FBS" and c["b_division_label"] == "FBS"],
            "FCS_SUBSET": [c["contest_key"] for c in contests if "FCS" in (c["a_division_label"], c["b_division_label"])]}


def build_parent(base: Path, contests: list[dict[str, Any]] | None = None, *,
                 subsets: dict[str, list[str]] | None = None, meta_patch: dict[str, str] | None = None) -> dict[str, Any]:
    rows = fixture_contests() if contests is None else contests
    data = pop.build_query_database(contract_sha256=PARENT_CONTRACT_SHA, m1_identity=M1, m2_identity=M2, cells=[],
                                    contests=rows, orientations=[], subsets=subsets or subsets_for(rows), schedule=[])
    if meta_patch:
        conn = sqlite3.connect(":memory:")
        conn.deserialize(data)
        for key, value in meta_patch.items():
            conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
        conn.commit()
        data = bytes(conn.serialize())
        conn.close()
    result = pop.materialize(canonical_root=Path(base) / "canonical" / "p", manifest_root=Path(base) / "manifests" / "p",
                             stage="query-db", contract_sha256=PARENT_CONTRACT_SHA, inputs={},
                             upstream={"program-season": M1, "contest": M2}, files={pop.DB_FILE_NAME: data},
                             manifest_extra={})
    db = Path(result["data_dir"]) / pop.DB_FILE_NAME
    return {"database": db, "manifest": Path(result["manifest"]), "identity": result["identity"],
            "sqlite_sha256": pop.sha256_file(db)}


def contract_for(parent: dict[str, Any], **patch: Any) -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["parent_binding"].update({"query_db_identity": parent["identity"], "sqlite_sha256": parent["sqlite_sha256"],
                                       "contract_sha256": PARENT_CONTRACT_SHA, "contest_identity": M2,
                                       "program_season_identity": M1})
    for dotted, value in patch.items():
        node = contract
        parts = dotted.split("__")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = value
    return contract


def write_contract(path: Path, contract: dict[str, Any]) -> Path:
    Path(path).write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8", newline="\n")
    return Path(path)


def run_build(contract: Path, parent: dict[str, Any], out: Path, *extra: str) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract), "--parent-database", str(parent["database"]),
            "--output-root", str(Path(out) / "canonical" / "h"), "--manifest-root", str(Path(out) / "manifests" / "h"),
            *extra]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = builder().main(argv)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


def refusal(stderr: str) -> str | None:
    for line in stderr.splitlines():
        try:
            return json.loads(line).get("refused")
        except ValueError:
            continue
    return None


def read_payload(result: dict[str, Any], name: str) -> list[dict[str, Any]]:
    path = Path(result["content"]["data_dir"]) / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
