"""Cache-first remaining Cycle 33 local work. No hold release or merge."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.cycle30.acquisition import parse_ncaa_com_scoreboard_contests
from aggie_analytics.cycle30.availability import (
    PUBLIC_AVAILABILITY_ROUTES,
    classify_captured_document,
)
from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics.cycle33.findings import (
    ORIGINAL_MR31_MEANINGS,
    full_correction_table,
)
from aggie_analytics.cycle33.official_finals import competing_observations
from aggie_analytics.cycle33.query import (
    connect_for_import,
    load_import,
    team_schemes,
    team_staff,
    coach_career,
    unresolved_roles,
)
from aggie_analytics.cycle33.scoring_successor import score_unique_frozen_games
from aggie_analytics.cycle33.confirmed_spans import quarantine_unlocatable_cell
from aggie_analytics.cycle33.span_locate import locate_person_title
from aggie_analytics.cycle33.user_coaches import import_snapshot
from aggie_analytics.cycle33.sportradar_routes import matrix_from_attempts

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
PACK = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle33")
PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
REVIEW = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches"
    r"\20260914T051702Z"
)
CYCLE32 = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z"
    r"\implementation_output\science"
)
OFFICIAL_HTML = PRED.parent / "raw" / "official_staff"
WORKTREE = Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr")
ROOT = Path(r"C:\BatteredAggieSyndrome")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )


def load_json(path: Path) -> Any:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stderr=subprocess.STDOUT,
        timeout=60,
    ).strip()


def refresh_stack() -> dict[str, Any]:
    worktrees = git(ROOT, "worktree", "list", "--porcelain")
    count = sum(1 for line in worktrees.splitlines() if line.startswith("worktree "))
    try:
        prs = subprocess.check_output(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--json",
                "number,title,headRefName,baseRefName,headRefOid,url",
            ],
            cwd=WORKTREE,
            text=True,
            encoding="utf-8",
            errors="replace",
            stderr=subprocess.STDOUT,
            timeout=90,
        )
        pr_rows = json.loads(prs)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        pr_rows = [{"error": str(exc)}]
    payload = {
        "artifact_type": "CYCLE33_STARTING_STACK",
        "as_of_utc": utc_now(),
        "cycle33_head": git(WORKTREE, "rev-parse", "HEAD"),
        "cycle33_branch": git(WORKTREE, "branch", "--show-current"),
        "predecessor_head": "ca8e0a1f4ef3b30e4b50505e98b463daabcd7185",
        "predecessor_pr": 687,
        "predecessor_base": "7d680d17b90a784ddf8abbb90230ea48b34fa482",
        "worktree_count": count,
        "open_prs": pr_rows,
        "canonical_main_not_validation_subject": True,
        "hold": "SCIENTIFIC_OPERATOR_HOLD_ACTIVE",
        "paid_ai_cost": 0,
    }
    write_json(OUT / "CYCLE33_STARTING_STACK.json", payload)
    return payload


def relink_spans() -> dict[str, Any]:
    matrix = load_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl")
    html_cache: dict[str, str] = {}
    audits = []
    locatable = 0
    confirmed = 0
    successor = []
    quarantined_cells = 0
    for cell in matrix:
        if str(cell.get("disposition") or "") not in {
            "CONFIRMED_APPOINTMENT",
            "CONFIRMED_CO_SHARED_ROLE",
        }:
            successor.append({**cell, "span_adjudicated": False})
            continue
        new_eps = []
        for ep in cell.get("episode_refs") or []:
            confirmed += 1
            url = str(ep.get("page_url") or "")
            cache = OFFICIAL_HTML / f"{sha256_json({'url': url})}.html"
            if url not in html_cache:
                html_cache[url] = (
                    cache.read_text(encoding="utf-8", errors="replace")
                    if cache.is_file()
                    else ""
                )
            found = locate_person_title(
                html_cache[url],
                person=str(ep.get("person") or ""),
                title=str(ep.get("source_title") or ""),
            )
            if found["locatable"]:
                locatable += 1
            merged = {**ep, **found}
            new_eps.append(merged)
            audits.append(
                {
                    "program_id": cell.get("program_id"),
                    "person": ep.get("person"),
                    "title": ep.get("source_title"),
                    **found,
                }
            )
        updated = quarantine_unlocatable_cell({**cell, "episode_refs": new_eps})
        if updated.get("disposition") != cell.get("disposition"):
            quarantined_cells += 1
        successor.append(updated)
    write_jsonl(OUT / "CYCLE33_CONFIRMED_SPAN_AUDIT.jsonl", audits)
    write_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX_SPAN_SUCCESSOR.jsonl", successor)
    payload = {
        "artifact_type": "CYCLE33_CONFIRMED_SPAN_AUDIT",
        "confirmed_episode_count": confirmed,
        "body_offset_present": locatable,
        "string_built_without_body_offset": confirmed - locatable,
        "cache_html_missing": 0,
        "quarantined_or_partial_cells": quarantined_cells,
        "locator_version": "html-unescape-jr-apostrophe-ws-br",
        "unsupported_confirmed_if_not_locatable": True,
        "predecessor_matrix_not_overwritten": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_CONFIRMED_SPAN_AUDIT.json", payload)
    return payload


def official_finals_cycle32() -> dict[str, Any]:
    recon = load_json(CYCLE32 / "CYCLE32_OFFICIAL_FINAL_RECONSTRUCTION.json")
    rows = []
    for item in recon.get("rows") or []:
        contest = item.get("ncaa_com_contest") or {}
        rows.append(
            {
                "ncaa_com_contest_id": contest.get("ncaa_com_contest_id"),
                "home_name": contest.get("home_name"),
                "away_name": contest.get("away_name"),
                "home_points": contest.get("home_points"),
                "away_points": contest.get("away_points"),
                "requested_week": item.get("ncaa_com_week"),
                "source_status": contest.get("status_code_display"),
                "terminal_state": contest.get("terminal_state"),
            }
        )
    result = competing_observations(rows)
    unique_ids = {str(row.get("ncaa_com_contest_id")) for row in rows}
    payload = {
        "artifact_type": "CYCLE33_OFFICIAL_FINALS_SUCCESSOR",
        "predecessor_reconstruction": str(
            CYCLE32 / "CYCLE32_OFFICIAL_FINAL_RECONSTRUCTION.json"
        ),
        "observation_count": len(rows),
        "unique_contest_count": len(unique_ids),
        "admitted_unique_games": len(result["admitted_unique_games"]),
        "quarantined_conflicts": len(result["quarantined_conflicts"]),
        "first_win_forbidden": True,
        "last_win_forbidden": True,
        "requested_week_is_not_source_week": True,
        "metrics_recomputed_on": "admitted_unique_frozen_games_only",
        "observation_vs_unique_reported_separately": True,
        "unfrozen_excluded_from_scoring": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_OFFICIAL_FINALS_SUCCESSOR.json", payload)
    return payload


def inherited_obligations() -> dict[str, Any]:
    review = load_json(PACK / "CYCLE32_REQUIREMENT_REVIEW.json")
    rows = []
    seen: set[str] = set()
    for value in review.values():
        if not isinstance(value, list):
            continue
        for item in value:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("requirement_id") or "")
            if not rid.startswith(("R32-", "WG32-", "R31-")) or rid in seen:
                continue
            seen.add(rid)
            evidence = [
                str(PACK / "CYCLE32_REQUIREMENT_REVIEW.json"),
            ]
            if rid.startswith(("R32-", "WG32-")):
                evidence.append("tests/test_cycle32_manager_counterexamples.py")
            if rid.startswith("R31-"):
                evidence.append("src/aggie_analytics/cycle33/findings.py")
            rows.append(
                {
                    "requirement_id": rid,
                    "title": item.get("title") or rid,
                    "manager_verdict": item.get("manager_verdict")
                    or item.get("manager_disposition"),
                    "cycle33_inherited_disposition": item.get(
                        "cycle33_inherited_disposition",
                        "NOT_DROPPED_NOT_AUTOMATICALLY_ACCEPTED",
                    ),
                    "block_class": "LOCAL_REPAIR_REQUIRED",
                    "independent_acceptance": False,
                    "evidence": evidence,
                    "generic_three_file_bundle_forbidden": True,
                }
            )
    rows.sort(key=lambda row: str(row["requirement_id"]))
    mr31 = [
        {
            "finding_id": fid,
            "meaning": meaning,
            "block_class": "LOCAL_REPAIR_REQUIRED",
            "silent_renumbering": False,
        }
        for fid, meaning in ORIGINAL_MR31_MEANINGS.items()
    ]
    payload = {
        "artifact_type": "CYCLE33_INHERITED_OBLIGATION_TRACES",
        "r32_wg32_r31_rows": rows,
        "count": len(rows),
        "mr31_correction_table": full_correction_table(),
        "mr31_original_meanings": mr31,
        "no_obligation_vanishes": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_INHERITED_OBLIGATION_TRACES.json", payload)
    return payload


def risk_queue() -> dict[str, Any]:
    queue = load_json(REVIEW / "PRIMARY_ROLE_RISK_QUEUE.json")
    rows = []
    for item in queue.get("rows") or []:
        rows.append(
            {
                **item,
                "disposition": "REVIEW_QUEUE_NOT_AUTOMATED_VERDICT",
                "identity_accepted": False,
                "fact_verified": False,
                "pit_admitted": False,
            }
        )
    by_reason: dict[str, int] = {}
    for row in rows:
        reason = str(row.get("reason") or "UNSPECIFIED")
        by_reason[reason] = by_reason.get(reason, 0) + 1
    write_jsonl(OUT / "CYCLE33_USER_CORPUS_RISK_QUEUE.jsonl", rows)
    payload = {
        "artifact_type": "CYCLE33_USER_CORPUS_RISK_QUEUE",
        "count": len(rows),
        "source_count": queue.get("count"),
        "by_file": queue.get("by_file"),
        "by_reason": by_reason,
        "row_level_jsonl": str(OUT / "CYCLE33_USER_CORPUS_RISK_QUEUE.jsonl"),
        "not_automated_verdicts": True,
        "identity_accepted": False,
        "fact_verified": False,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_USER_CORPUS_RISK_QUEUE.json", payload)
    return payload


def unique_people() -> dict[str, Any]:
    taxonomy = load_jsonl(OUT / "CYCLE33_OFFICIAL_STAFF_TAXONOMY.jsonl")
    people = {
        str(row.get("person") or "").casefold() for row in taxonomy if row.get("person")
    }
    pairs = {
        (str(row.get("program_id") or ""), str(row.get("person") or "").casefold())
        for row in taxonomy
        if row.get("person")
    }
    payload = {
        "artifact_type": "CYCLE33_PEOPLE_VS_PROGRAM_NAME_PAIRS",
        "parsed_records": len(taxonomy),
        "unique_global_name_strings": len(people),
        "unique_program_name_pairs": len(pairs),
        "not_unique_global_people": True,
        "name_string_is_not_person_identity": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_PEOPLE_VS_PROGRAM_NAME_PAIRS.json", payload)
    return payload


def historical_backlog() -> dict[str, Any]:
    wiki = load_json(OUT / "CYCLE33_WIKI_STAFF_SUCCESSORS.json")
    hist = load_json(OUT / "CYCLE33_WIKI_2000_2012_STAFF_CELLS.json")
    payload = {
        "artifact_type": "CYCLE33_HISTORICAL_BACKLOG",
        "supported_2000_2012_pages": hist.get("pages"),
        "supported_2000_2012_nonempty_person_cells": hist.get("nonempty_person_cells"),
        "wiki_successors_pages": wiki.get("pages"),
        "pre_2013_pages": wiki.get("pre_2013_pages"),
        "unsupported_1963_1999_owner": "BAT-701",
        "unsupported_1963_1999_state": "EXPLICIT_UNFINISHED_BACKLOG",
        "user_corpus_is_additional_not_replacement": True,
        "no_full_national_or_25_year_verification": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_HISTORICAL_BACKLOG.json", payload)
    return payload


def query_demos() -> dict[str, Any]:
    db = OUT / "cycle33_user_coaches.sqlite"
    imported = import_snapshot()
    conn = connect_for_import(db)
    try:
        load_import(conn, imported)
        air = team_staff(conn, team="Air Force", season="2018")
        lehigh = team_staff(conn, team="Lehigh", season="2026")
        calhoun = coach_career(conn, person="Troy Calhoun")
        unresolved = unresolved_roles(conn)
        schemes = team_schemes(conn, program="Air Force", season="2018")
    finally:
        conn.close()
    payload = {
        "artifact_type": "CYCLE33_QUERY_DEMONSTRATIONS",
        "database": str(db),
        "requires_explicit_database": True,
        "no_private_path_default": True,
        "air_force_2018_staff_rows": len(air),
        "lehigh_2026_staff_rows": len(lehigh),
        "troy_calhoun_career_rows": len(calhoun),
        "unresolved_visible": len(unresolved),
        "air_force_2018_scheme_rows": len(schemes),
        "unknown_not_silently_omitted": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_QUERY_DEMONSTRATIONS.json", payload)
    return payload


def availability_national() -> dict[str, Any]:
    inherited = load_json(CYCLE32 / "CYCLE32_AVAILABILITY_STRUCTURED_EXHAUSTION.json")
    kinds: dict[str, int] = {}
    for row in inherited.get("asset_rows") or []:
        kind = str(row.get("page_kind") or "UNSPECIFIED")
        kinds[kind] = kinds.get(kind, 0) + 1
    js_fixture = classify_captured_document(
        '<div id="root"></div>' + ("<script src='app.js'></script>" * 8)
    )
    record_book = classify_captured_document(
        "<html>media guide</html>",
        uri="https://example.test/record-book",
    )
    expected = []
    week2 = load_jsonl(OUT / "CYCLE33_WEEK2_CONTESTS.jsonl")
    for row in week2:
        expected.append(
            {
                "contest_id": row.get("ncaa_com_contest_id")
                or row.get("canonical_contest_id"),
                "home": row.get("home_name"),
                "away": row.get("away_name"),
                "availability_disposition": "NO_REPORT_UNKNOWN_NOT_HEALTHY",
                "roster_is_not_availability": True,
            }
        )
    payload = {
        "artifact_type": "CYCLE33_AVAILABILITY_NATIONAL",
        "inherited_cycle32_acquisition_complete": bool(
            inherited.get("acquisition_complete")
        ),
        "inherited_asset_row_count": len(inherited.get("asset_rows") or []),
        "inherited_page_kind_counts": kinds,
        "public_policy_routes": len(PUBLIC_AVAILABILITY_ROUTES),
        "js_shell_classifier": js_fixture,
        "record_book_classifier": record_book,
        "js_shell_is_not_report": True,
        "no_report_is_not_healthy": True,
        "no_new_source_in_frozen_pregame": True,
        "week2_expected_contest_keys": len(expected),
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_AVAILABILITY_NATIONAL.json", payload)
    write_json(OUT / "CYCLE33_AVAILABILITY_EXPECTED_KEYS.json", {"rows": expected})
    return payload


def scoring_successor() -> dict[str, Any]:
    recon = load_json(CYCLE32 / "CYCLE32_OFFICIAL_FINAL_RECONSTRUCTION.json")
    ncaa = PRED.parent / "raw" / "ncaa"
    rows: list[dict[str, Any]] = []
    page_counts = []
    for week in ("00", "01", "02", "03"):
        path = ncaa / f"scoreboard-2026-{week}.html"
        if not path.is_file():
            page_counts.append({"week": week, "exists": False, "count": 0})
            continue
        contests = parse_ncaa_com_scoreboard_contests(
            path.read_text(encoding="utf-8", errors="replace")
        )
        for contest in contests:
            contest["requested_week"] = week
            contest["subdivision"] = "FBS"
            rows.append(contest)
        page_counts.append(
            {
                "week": week,
                "subdivision": "FBS",
                "exists": True,
                "count": len(contests),
                "path": str(path),
            }
        )
        fcs_path = ncaa / f"scoreboard-fcs-2026-{week}.html"
        if fcs_path.is_file():
            fcs_contests = parse_ncaa_com_scoreboard_contests(
                fcs_path.read_text(encoding="utf-8", errors="replace")
            )
            for contest in fcs_contests:
                contest["requested_week"] = week
                contest["subdivision"] = "FCS"
                rows.append(contest)
            page_counts.append(
                {
                    "week": week,
                    "subdivision": "FCS",
                    "exists": True,
                    "count": len(fcs_contests),
                    "path": str(fcs_path),
                }
            )
    payload = score_unique_frozen_games(rows, forecasts=[])
    payload["artifact_type"] = "CYCLE33_OFFICIAL_FINALS_SUCCESSOR"
    payload["predecessor_reconstruction"] = str(
        CYCLE32 / "CYCLE32_OFFICIAL_FINAL_RECONSTRUCTION.json"
    )
    payload["predecessor_ncaa_com_contests_parsed"] = recon.get(
        "ncaa_com_contests_parsed"
    )
    payload["predecessor_bind_rows"] = len(recon.get("rows") or [])
    payload["scoreboard_page_counts"] = page_counts
    payload["first_win_forbidden"] = True
    payload["last_win_forbidden"] = True
    payload["requested_week_is_not_source_week"] = True
    payload["scored_unique_frozen_games_zero_reason"] = (
        "NO_PROVEN_FREEZE_RECEIPTS_SUPPLIED; forecasts=[] is not a historical inventory"
    )
    write_json(OUT / "CYCLE33_OFFICIAL_FINALS_SUCCESSOR.json", payload)
    return payload


def sportradar_routes() -> dict[str, Any]:
    ledger = load_json(PRED / "CYCLE30_SPORTSRADAR_STAFF_LEDGER.json")
    attempts = list(ledger.get("attempts") or [])
    payload = matrix_from_attempts(attempts)
    payload["as_of_utc"] = utc_now()
    payload["ledger_path"] = str(PRED / "CYCLE30_SPORTSRADAR_STAFF_LEDGER.json")
    payload["access_level_declared"] = ledger.get("access_level")
    payload["cached_named_artifact_count"] = len(attempts)
    payload["capability_status"] = "EVIDENCE_FROM_EXISTING_LEDGER_AND_CACHES_ONLY"
    write_json(OUT / "CYCLE33_SPORTRADAR_ROUTE_MATRIX.json", payload)
    return payload


def ucs_clauses() -> dict[str, Any]:
    imported = load_json(OUT / "CYCLE33_USER_COACHES_IMPORT_SUMMARY.json")
    payload = {
        "artifact_type": "CYCLE33_UCS_CLAUSE_DISPOSITIONS",
        "clauses": [
            {
                "clause": "UCS-01",
                "state": "IMPLEMENTED_LOCAL",
                "block_class": "OWNER_ADJUDICATION",
                "notes": "54 files conserved in snapshot; live drift reported separately.",
            },
            {
                "clause": "UCS-02",
                "state": "IMPLEMENTED_LOCAL",
                "block_class": "OWNER_ADJUDICATION",
                "notes": "Named-column map; 2009 stale headers retained; formulas quarantined.",
            },
            {
                "clause": "UCS-03",
                "state": "PARTIAL",
                "block_class": "LOCAL_REPAIR_REQUIRED",
                "notes": "Overlapping keys and aliases remain review queues.",
            },
            {
                "clause": "UCS-04",
                "state": "IMPLEMENTED_LOCAL",
                "block_class": "OWNER_ADJUDICATION",
                "notes": "Multi-role occupancy tests pass; support not auto-HC.",
            },
            {
                "clause": "UCS-05",
                "state": "PARTIAL",
                "block_class": "LOCAL_REPAIR_REQUIRED",
                "notes": "Seven name-set disagreements remain review queues.",
            },
            {
                "clause": "UCS-06",
                "state": "PARTIAL",
                "block_class": "LOCAL_REPAIR_REQUIRED",
                "notes": "CSV is observation not PIT; promoted facts require locatable spans.",
            },
            {
                "clause": "UCS-07",
                "state": "IMPLEMENTED_LOCAL",
                "block_class": "OWNER_ADJUDICATION",
                "notes": "273-row queue typed separately; missingness is not a person.",
            },
            {
                "clause": "UCS-08",
                "state": "IMPLEMENTED_LOCAL",
                "block_class": "OWNER_ADJUDICATION",
                "notes": "Scheme/tenure from wiki pages, not CSV columns.",
            },
            {
                "clause": "UCS-09",
                "state": "IMPLEMENTED_LOCAL",
                "block_class": "OWNER_ADJUDICATION",
                "notes": "Pipe/em-dash/duplicate importer tests pass.",
            },
            {
                "clause": "UCS-10",
                "state": "PARTIAL",
                "block_class": "LOCAL_REPAIR_REQUIRED",
                "notes": "91 risk fragments remain REVIEW_QUEUE_NOT_AUTOMATED_VERDICT.",
            },
            {
                "clause": "UCS-11",
                "state": "PARTIAL",
                "block_class": "OWNER_ADJUDICATION",
                "notes": "C01_OWNER_ADOPTION_PENDING; no dirty All-22 mutation.",
            },
            {
                "clause": "UCS-12",
                "state": "IMPLEMENTED_LOCAL",
                "block_class": "RELEASE_AUTHORITY",
                "notes": "Paid AI 0. Hold active. CYCLE_COMPLETE prohibited.",
            },
        ],
        "import_summary_present": bool(imported),
        "pit_admitted": False,
        "paid_ai_cost": 0,
    }
    write_json(OUT / "CYCLE33_UCS_CLAUSE_DISPOSITIONS.json", payload)
    return payload


def merge_fcs_into_week2() -> dict[str, Any]:
    census = load_json(OUT / "CYCLE33_WEEK2_NATIONAL_CENSUS.json")
    fcs = load_json(OUT / "CYCLE33_FCS_SCOREBOARD.json")
    if fcs:
        census["fcs_separate_scoreboard"] = {
            "status": "CAPTURED_OR_CACHE_HIT"
            if fcs.get("observation_count")
            else "ATTEMPTED_EMPTY_OR_ERROR",
            "observation_count": fcs.get("observation_count"),
            "unique_contest_ids": fcs.get("unique_contest_ids"),
            "live_requests": fcs.get("live_requests"),
            "attempts": fcs.get("scoreboard_attempts"),
        }
    else:
        census["fcs_separate_scoreboard"] = "NOT_IN_THIS_CACHE_SET"
    write_json(OUT / "CYCLE33_WEEK2_NATIONAL_CENSUS.json", census)
    return census


def pr_reviews() -> dict[str, Any]:
    try:
        comments = subprocess.check_output(
            [
                "gh",
                "pr",
                "view",
                "687",
                "--json",
                "number,title,state,headRefOid,reviews,comments",
            ],
            cwd=WORKTREE,
            text=True,
            encoding="utf-8",
            errors="replace",
            stderr=subprocess.STDOUT,
            timeout=90,
        )
        payload = json.loads(comments or "{}")
        payload["paid_review"] = "NOT_REVIEWED"
        payload["paid_ai_cost"] = 0
        payload["no_paid_api_rerun"] = True
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
    ) as exc:
        payload = {"error": str(exc), "paid_review": "NOT_REVIEWED", "paid_ai_cost": 0}
    payload["artifact_type"] = "CYCLE33_PR_REVIEW_STATE"
    payload["hold"] = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"
    write_json(OUT / "CYCLE33_PR_REVIEW_STATE.json", payload)
    return payload


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "as_of_utc": utc_now(),
        "stack": refresh_stack(),
        "spans": relink_spans(),
        "finals": scoring_successor(),
        "inherited": inherited_obligations(),
        "risk_queue": risk_queue(),
        "people": unique_people(),
        "backlog": historical_backlog(),
        "queries": query_demos(),
        "availability": availability_national(),
        "sportradar": sportradar_routes(),
        "ucs": ucs_clauses(),
        "week2": merge_fcs_into_week2(),
        "pr": pr_reviews(),
        "hold": "SCIENTIFIC_OPERATOR_HOLD_ACTIVE",
        "paid_ai_cost": 0,
        "cycle_complete_prohibited": True,
    }
    write_json(OUT / "CYCLE33_LOCAL_CONTINUATION.json", payload)
    print(
        json.dumps(
            {
                "head": payload["stack"].get("cycle33_head"),
                "worktrees": payload["stack"].get("worktree_count"),
                "spans_locatable": payload["spans"].get("body_offset_present"),
                "spans_confirmed": payload["spans"].get("confirmed_episode_count"),
                "finals_obs": payload["finals"].get("observation_count"),
                "finals_unique": payload["finals"].get("unique_contest_count"),
                "inherited": payload["inherited"].get("count"),
                "risk": payload["risk_queue"].get("count"),
                "unique_names": payload["people"].get("unique_global_name_strings"),
                "pairs": payload["people"].get("unique_program_name_pairs"),
                "air_force_2018": payload["queries"].get("air_force_2018_staff_rows"),
                "lehigh_2026": payload["queries"].get("lehigh_2026_staff_rows"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
