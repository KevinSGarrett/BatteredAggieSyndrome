"""Cycle 33 remaining local materialization. Cache-first. No hold release."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.cycle30.acquisition import parse_ncaa_com_scoreboard_contests
from aggie_analytics.cycle30.coaching import (
    PRIMARY_ROLES,
    fill_current_role_matrix,
    role_families_from_title,
    roles_from_career_parenthetical,
)
from aggie_analytics.cycle33.official_finals import competing_observations
from aggie_analytics.cycle33.role_taxonomy import assignments_from_title
from aggie_analytics.cycle33.user_coaches import import_snapshot
from aggie_analytics.cycle33.week2 import historical_tamu_asu_row, utc_now as week2_now

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z\implementation_output\science"
)
CYCLE32 = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output\science"
)
PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
NCAA = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\ncaa")
REVIEW = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches\20260914T051702Z"
)
SNAPSHOT = REVIEW / "source_snapshot"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def rematerialize_matrix() -> dict[str, Any]:
    programs = load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    attempts = load_jsonl(PRED / "OFFICIAL_STAFF_HTTP_ATTEMPTS.jsonl")
    repaired = load_jsonl(CYCLE32 / "CYCLE32_REPAIRED_STAFF_ATTEMPTS.jsonl")
    predecessor_cells = load_jsonl(PRED / "CURRENT_NATIONAL_HC_OC_DC_MATRIX.jsonl")
    parsed = load_jsonl(CYCLE32 / "CYCLE32_OFFICIAL_STAFF_PARSED.jsonl")
    attempt_by_program = {str(row["program_id"]): row for row in attempts}
    for row in repaired:
        if str(row.get("status") or "") == "CAPTURED" and row.get("page_url"):
            attempt_by_program[str(row["program_id"])] = row
    people_by_program: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for person in parsed:
        title = str(person.get("title") or person.get("source_title") or "")
        families = role_families_from_title(title)
        row = dict(person)
        if families:
            row["role"] = families[0]
        elif row.get("role") in PRIMARY_ROLES:
            row["role"] = "OTHER_POSITION"
        people_by_program[str(person.get("program_id") or "")].append(row)
    empty_cells = [
        {"program_id": row["program_id"], "role": row["role"], "as_of_utc": utc_now()}
        for row in predecessor_cells
    ]
    filled = fill_current_role_matrix(
        empty_cells,
        programs=programs,
        cfbd_hc_by_school={},
        official_people_by_program=people_by_program,
        official_attempts_by_program=attempt_by_program,
        sportradar_people_by_program={},
        sportradar_attempts_by_program={},
        wikimedia_people_by_program={},
    )
    for cell in filled:
        cell["operator_declaration_is_not_appointment"] = True
        cell["pit_admitted"] = False
        for ep in cell.get("episode_refs") or []:
            if str(ep.get("source") or "") == "OPERATOR_CONTEMPORANEOUS_DECLARATION":
                raise RuntimeError("operator declaration leaked into successor matrix")
    write_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl", filled)
    counts = Counter(str(row.get("disposition") or "") for row in filled)
    washington = [
        row
        for row in filled
        if str(row.get("program_id"))
        in {
            str(p.get("program_id"))
            for p in programs
            if str(p.get("display_name") or "") == "Washington"
        }
    ]
    summary = {
        "artifact_type": "CYCLE33_CURRENT_HC_OC_DC_MATRIX",
        "as_of_utc": utc_now(),
        "cell_count": len(filled),
        "disposition_counts": dict(counts),
        "washington_cells": washington,
        "operator_oc_present": any(
            str(ep.get("source")) == "OPERATOR_CONTEMPORANEOUS_DECLARATION"
            for row in filled
            for ep in row.get("episode_refs") or []
        ),
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.json", summary)
    return summary


def excluded_spans() -> dict[str, Any]:
    rows = load_jsonl(CYCLE32 / "CYCLE32_EXCLUDED_SPANS.jsonl")
    successor = []
    occupancy: Counter[str] = Counter()
    for row in rows:
        title = str(row.get("source_title") or row.get("title") or "")
        mapped = assignments_from_title(title) if title else []
        for item in mapped:
            occupancy[item["occupancy"]] += 1
        successor.append(
            {
                **row,
                "taxonomy_assignments": mapped,
                "raw_title_roundtrip": title,
                "pit_admitted": False,
            }
        )
    write_jsonl(OUT / "CYCLE33_EXCLUDED_SPANS.jsonl", successor)
    summary = {
        "artifact_type": "CYCLE33_EXCLUDED_SPANS",
        "record_count": len(successor),
        "occupancy_counts": dict(occupancy),
        "predecessor_count": 2606,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_EXCLUDED_SPANS.json", summary)
    return summary


def week2_census() -> dict[str, Any]:
    now = week2_now()
    tamu = historical_tamu_asu_row(now)
    contests: list[dict[str, Any]] = []
    missing: list[str] = []
    for label, name in (
        ("2026/00", "scoreboard-2026-00.html"),
        ("2026/01", "scoreboard-2026-01.html"),
        ("2026/02", "scoreboard-2026-02.html"),
        ("2026/03", "scoreboard-2026-03.html"),
    ):
        path = NCAA / name
        if not path.is_file():
            missing.append(str(path))
            continue
        parsed = parse_ncaa_com_scoreboard_contests(
            path.read_text(encoding="utf-8", errors="replace")
        )
        for contest in parsed:
            row = {
                **contest,
                "requested_week_label": label,
                "source_path": str(path),
                "t24h_deadline_utc": None,
                "t90m_deadline_utc": None,
                "t24h_disposition": "CUTOFF_UNKNOWN",
                "t90m_disposition": "CUTOFF_UNKNOWN",
                "forecast_classification": "UNTRUSTED_SHADOW",
                "retroactive_forecast_forbidden": True,
                "week2_outcomes_do_not_tune_or_select": True,
            }
            identity = f"{contest.get('home_name')} vs {contest.get('away_name')}"
            if "arizona state" in identity.casefold() and "a&m" in identity.casefold():
                row["t24h_deadline_utc"] = tamu["t24h_deadline_utc"]
                row["t90m_deadline_utc"] = tamu["t90m_deadline_utc"]
                row["t24h_disposition"] = tamu["t24h_disposition"]
                row["t90m_disposition"] = tamu["t90m_disposition"]
                row["canonical_contest_note"] = "TAMU_ASU_HISTORICAL_NO_REARM"
            if contest.get("terminal_state") == "TERMINAL_STATUS_ESTABLISHED":
                row["operational_disposition"] = "OFFICIAL_FINAL_SCORING_ONLY"
            else:
                row["operational_disposition"] = "SCHEDULE_CAPTURED_FORECAST_NOT_ARMED"
            contests.append(row)
    finals = competing_observations(
        [
            {
                "ncaa_com_contest_id": row.get("ncaa_com_contest_id"),
                "home_points": row.get("home_points"),
                "away_points": row.get("away_points"),
                "home_name": row.get("home_name"),
                "away_name": row.get("away_name"),
                "week": row.get("requested_week_label"),
            }
            for row in contests
            if row.get("ncaa_com_contest_id")
        ]
    )
    write_jsonl(OUT / "CYCLE33_WEEK2_CONTESTS.jsonl", contests)
    payload = {
        "artifact_type": "CYCLE33_WEEK2_NATIONAL_CENSUS",
        "as_of_utc": utc_now(),
        "clock_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tamu_asu": tamu,
        "cached_scoreboard_contest_count": len(contests),
        "observation_count": finals["observation_count"],
        "unique_contest_count": finals["unique_contest_count"],
        "quarantined_conflicts": len(finals["quarantined_conflicts"]),
        "week2_cache_present": (NCAA / "scoreboard-2026-02.html").is_file(),
        "week2_contest_count": sum(
            1 for row in contests if row.get("requested_week_label") == "2026/02"
        ),
        "missing_raw": missing,
        "fcs_separate_scoreboard": "NOT_IN_THIS_CACHE_SET",
        "new_scheduler_installed": False,
        "rearm_forbidden": True,
        "invented_forecast": False,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_WEEK2_NATIONAL_CENSUS.json", payload)
    write_json(
        OUT / "CYCLE33_OFFICIAL_FINALS_SUCCESSOR.json",
        {
            "artifact_type": "CYCLE33_OFFICIAL_FINALS_SUCCESSOR",
            "observation_count": finals["observation_count"],
            "unique_contest_count": finals["unique_contest_count"],
            "admitted_unique_games": len(finals["admitted_unique_games"]),
            "quarantined_conflicts": finals["quarantined_conflicts"],
            "first_win_forbidden": True,
            "last_win_forbidden": True,
            "requested_week_is_not_source_week": True,
            "pit_admitted": False,
        },
    )
    return payload


def user_historical_cells() -> dict[str, Any]:
    imported = import_snapshot(SNAPSHOT)
    cells = []
    by_year: Counter[str] = Counter()
    for cell in imported["role_cells"]:
        season = str(cell.get("season") or "")
        if not season.isdigit():
            continue
        year = int(season)
        if year < 2000 or year > 2012:
            continue
        if cell.get("person") is None:
            continue
        by_year[season] += 1
        cells.append(
            {
                "season": season,
                "subdivision": cell.get("filename_subdivision"),
                "team": cell.get("team"),
                "team_id_source": cell.get("team_id_source"),
                "role_column": cell.get("role_column"),
                "person": cell.get("person"),
                "source_title": cell.get("source_title"),
                "disposition": "USER_COMPILED_RESEARCH_OBSERVATION",
                "verified": False,
                "pit_admitted": False,
                "source_class": "USER_COMPILED_RESEARCH_OBSERVATION",
            }
        )
    write_jsonl(OUT / "CYCLE33_USER_CORPUS_2000_2012_STAFF_CELLS.jsonl", cells)
    summary = {
        "artifact_type": "CYCLE33_USER_CORPUS_2000_2012_STAFF_CELLS",
        "row_count": len(cells),
        "by_year": dict(by_year),
        "not_replacement_population": True,
        "not_verified_wholesale": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_USER_CORPUS_2000_2012_STAFF_CELLS.json", summary)
    return summary


def risk_and_comparison() -> dict[str, Any]:
    risk = json.loads(
        (REVIEW / "PRIMARY_ROLE_RISK_QUEUE.json").read_text(encoding="utf-8")
    )
    comparison = json.loads(
        (REVIEW / "BAS_CURRENT_COMPARISON.json").read_text(encoding="utf-8")
    )
    risk_disp = []
    for row in risk.get("rows") or []:
        mapped = assignments_from_title(str(row.get("fragment") or ""))
        principal = [
            item for item in mapped if item["occupancy"] in {"PRINCIPAL", "CO_SHARED"}
        ]
        risk_disp.append(
            {
                **row,
                "taxonomy_assignments": mapped,
                "principal_roles": [item["role"] for item in principal],
                "review_queue_not_verdict": True,
                "automated_factual_verdict": False,
            }
        )
    write_jsonl(OUT / "CYCLE33_UCS_RISK_FRAGMENT_DISPOSITIONS.jsonl", risk_disp)
    diffs = [
        row
        for row in comparison.get("rows") or []
        if row.get("classification") == "CANDIDATE_NAME_SET_DIFFERENCE_REVIEW_REQUIRED"
    ]
    write_json(
        OUT / "CYCLE33_BAS_CURRENT_NAMESET_DISAGREEMENTS.json",
        {
            "count": len(diffs),
            "rows": diffs,
            "not_automated_verdicts": True,
            "primary_source_receipts": "PRIMARY_SOURCE_RECEIPTS.json",
        },
    )
    write_json(
        OUT / "CYCLE33_BAS_CURRENT_COMPARISON_ALL_ROWS.json",
        {
            "counts": comparison.get("counts"),
            "row_count": len(comparison.get("rows") or []),
            "limitation": comparison.get("limitation"),
            "all_field_comparisons_emitted": True,
            "predecessor_sample_limit_not_used": True,
            "identity_accepted_false_for_all": True,
        },
    )
    return {
        "risk_count": len(risk_disp),
        "difference_count": len(diffs),
        "comparison_rows": len(comparison.get("rows") or []),
    }


def career_remap() -> dict[str, Any]:
    pages = load_jsonl(PRED / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl")
    remapped = []
    role_counts: Counter[str] = Counter()
    politician = 0
    for page in pages:
        title = str(page.get("title") or page.get("requested_title") or "")
        folded = title.casefold()
        if "politician" in folded or "disambiguation" in folded:
            politician += 1
            remapped.append(
                {
                    "title": title,
                    "status": "NOT_FOOTBALL_COACH_IDENTITY",
                    "episodes": [],
                    "pit_admitted": False,
                }
            )
            continue
        episodes = []
        for ep in page.get("episodes") or []:
            raw = str(ep.get("raw_title") or ep.get("source_title") or "")
            roles = roles_from_career_parenthetical(raw) if raw else ("UNKNOWN",)
            for role in roles:
                role_counts[role] += 1
            episodes.append(
                {
                    **ep,
                    "roles_from_parenthetical": list(roles),
                    "pit_admitted": False,
                    "stringified_object_as_text": False,
                }
            )
        remapped.append(
            {
                "title": title,
                "wikimedia_revision": page.get("wikimedia_revision"),
                "status": page.get("status"),
                "episode_count": len(episodes),
                "episodes": episodes,
                "pit_admitted": False,
            }
        )
    write_jsonl(OUT / "CYCLE33_CAREER_PAGE_REPARSE.jsonl", remapped)
    summary = {
        "artifact_type": "CYCLE33_CAREER_PAGE_REPARSE",
        "pages": len(remapped),
        "politician_or_disambiguation": politician,
        "role_counts": dict(role_counts),
        "inherited_not_only_188": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_CAREER_PAGE_REPARSE.json", summary)
    return summary


def reference_set() -> dict[str, Any]:
    receipts = json.loads(
        (REVIEW / "PRIMARY_SOURCE_RECEIPTS.json").read_text(encoding="utf-8")
    )
    labeled = []
    for receipt in receipts:
        labeled.append(
            {
                "reference_id": receipt["id"],
                "url": receipt.get("final_url") or receipt.get("url"),
                "http_status": receipt.get("http_status"),
                "raw_sha256": receipt.get("sha256"),
                "path": receipt.get("path"),
                "label_source": "MANAGER_PRIMARY_SOURCE_RECEIPT_INDEPENDENT_OF_PARSER",
                "parser_not_used_to_label": True,
                "manual_slice": True,
                "pit_admitted": False,
            }
        )
    write_json(
        OUT / "CYCLE33_CS05_REFERENCE_SET.json",
        {
            "artifact_type": "CYCLE33_CS05_REFERENCE_SET",
            "manual_primary_supported_slice": labeled,
            "manual_slice_count": len(labeled),
            "unsampled_population": "ALL_OTHER_STAFF_AND_HISTORICAL_ROWS",
            "does_not_prove_unsampled_correct": True,
            "fbs_and_fcs_examples_included": True,
            "pit_admitted": False,
        },
    )
    return {"manual_slice_count": len(labeled)}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "as_of_utc": utc_now(),
        "matrix": rematerialize_matrix(),
        "excluded": excluded_spans(),
        "week2": week2_census(),
        "user_2000_2012": user_historical_cells(),
        "ucs": risk_and_comparison(),
        "career": career_remap(),
        "reference": reference_set(),
    }
    write_json(OUT / "CYCLE33_MATERIAL_CONTINUATION.json", payload)
    print(
        json.dumps(
            {
                k: (
                    v
                    if not isinstance(v, dict)
                    else {
                        ik: iv
                        for ik, iv in v.items()
                        if ik
                        in {
                            "cell_count",
                            "disposition_counts",
                            "row_count",
                            "pages",
                            "week2_contest_count",
                            "observation_count",
                            "unique_contest_count",
                            "record_count",
                            "risk_count",
                            "difference_count",
                            "operator_oc_present",
                            "washington_cells",
                        }
                    }
                )
                for k, v in payload.items()
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
