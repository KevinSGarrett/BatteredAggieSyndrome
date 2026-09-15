"""Cache-first availability, PIT recompute, corpus grain, and query demos."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle33.availability_cache import parse_cached_routes
from aggie_analytics.cycle33.forecast_inventory import inventory_forecast_files
from aggie_analytics.cycle33.pit_recompute import recompute_pit_population
from aggie_analytics.cycle33.query import (
    connect_readonly,
    run_query_demonstrations,
    team_schemes,
)
from aggie_analytics.cycle33.user_coaches import (
    adjudicate_risk_fragments,
    conservation_checks,
    import_snapshot,
    overlap_program_seasons,
)
from aggie_analytics.scientific_reference.cycle33_pit import reconstruct_pit

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
SNAP = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T215526Z"
)
KERNEL = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs\PIT_KERNEL_ROWS.jsonl")
RISK = OUT / "CYCLE33_USER_CORPUS_RISK_QUEUE.jsonl"
FORECAST_ROOTS = (
    Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\forecast"),
    Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\pit"),
    OUT,
)
ALL22_ROOTS = (
    Path(r"C:\CFB\repos"),
    Path(r"C:\All-22\repos"),
    Path(r"C:\All-22\FoundationControl"),
    Path(r"C:\All-22"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def availability() -> dict[str, Any]:
    payload = parse_cached_routes()
    write_json(OUT / "CYCLE33_AVAILABILITY_CACHE_PARSE.json", payload)
    return payload


def pit() -> dict[str, Any]:
    rows = load_jsonl(KERNEL)
    producer = recompute_pit_population(rows)
    independent = reconstruct_pit(rows)
    payload = {
        "artifact_type": "CYCLE33_PIT_INDEPENDENT_RECOMPUTE",
        "as_of_utc": utc_now(),
        "kernel_path": str(KERNEL),
        "producer": {
            "row_count": producer["row_count"],
            "producer_authority_class_counts": producer[
                "producer_authority_class_counts"
            ],
            "independently_proven_count": producer["independently_proven_count"],
            "failed_predicate_reason_counts": producer[
                "failed_predicate_reason_counts"
            ],
        },
        "independent": independent,
        "counts_agree": producer["independently_proven_count"]
        == independent["independently_proven_count"],
        "week1_week2_not_used_to_tune": True,
        "classification": "UNTRUSTED_SHADOW",
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_PIT_INDEPENDENT_RECOMPUTE.json", payload)
    return payload


def corpus(imported: dict[str, Any] | None = None) -> dict[str, Any]:
    imported = imported or import_snapshot()
    conservation = conservation_checks(imported)
    overlaps = overlap_program_seasons(imported)
    fragments = load_jsonl(RISK)
    risks = adjudicate_risk_fragments(fragments)
    summary = {
        "artifact_type": "CYCLE33_USER_CORPUS_CONSERVATION",
        "conservation": conservation,
        "overlaps": {
            "overlap_count": overlaps["overlap_count"],
            "named_keys": overlaps["named_keys"],
            "all_named_found": overlaps["all_named_found"],
        },
        "risk_fragments": {
            "count": risks["count"],
            "by_adjudication": risks["by_adjudication"],
            "fact_verified": False,
        },
        "import_grains": {
            "file_count": imported.get("file_count"),
            "staff_row_count": imported.get("staff_row_count"),
            "queue_row_count": imported.get("queue_row_count"),
            "physically_present_role_cells": imported.get(
                "physically_present_role_cells"
            ),
            "parsed_person_segment_count": imported.get(
                "parsed_person_segment_count"
            ),
            "emitted_role_assignment_records": imported.get(
                "emitted_role_assignment_records"
            ),
            "distinct_source_role_cell_ids": imported.get(
                "distinct_source_role_cell_ids"
            ),
            "canonical_people_count": imported.get("canonical_people_count"),
        },
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_USER_CORPUS_CONSERVATION.json", summary)
    write_json(
        OUT / "CYCLE33_USER_CORPUS_OVERLAPS.json",
        {k: overlaps[k] for k in overlaps if k != "overlaps"}
        | {"overlaps": overlaps["overlaps"]},
    )
    write_json(
        OUT / "CYCLE33_USER_CORPUS_RISK_ADJUDICATION.json",
        {
            "count": risks["count"],
            "by_adjudication": risks["by_adjudication"],
            "rows": risks["rows"],
            "fact_verified": False,
            "pit_admitted": False,
        },
    )
    return summary


def _scheme_demo_claims() -> list[dict[str, Any]]:
    keep: list[dict[str, Any]] = []
    for row in load_jsonl(OUT / "CYCLE33_SCHEME_TENURE_CLAIMS.jsonl"):
        if not (row.get("source_text") or row.get("raw_value")):
            continue
        title = str(row.get("title") or row.get("program_raw") or "")
        season = str(row.get("season") or "")
        if season == "2018" and "Air Force" in title:
            keep.append(row)
        elif season == "2026" and "Lehigh" in title:
            keep.append(row)
    return keep


def queries(imported: dict[str, Any] | None = None) -> dict[str, Any]:
    imported = imported or import_snapshot()
    scheme_claims = _scheme_demo_claims()
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "cycle33_query_demo.sqlite"
        demo = run_query_demonstrations(
            database=db, imported=imported, scheme_claims=scheme_claims
        )
        missing = Path(tmp) / "does_not_exist.sqlite"
        readonly_missing = False
        try:
            connect_readonly(missing)
        except Exception:
            readonly_missing = not missing.exists()
        demo["readonly_missing_does_not_create"] = readonly_missing
        existing = OUT / "cycle33_user_coaches.sqlite"
        if existing.is_file():
            conn = connect_readonly(existing)
            try:
                demo["existing_db_air_force_2018_scheme_rows"] = len(
                    team_schemes(conn, program="Air Force", season="2018")
                )
                demo["existing_db_lehigh_2026_scheme_rows"] = len(
                    team_schemes(conn, program="Lehigh", season="2026")
                )
            finally:
                conn.close()
        write_json(OUT / "CYCLE33_QUERY_DEMONSTRATIONS.json", demo)
        return demo


def forecasts() -> dict[str, Any]:
    payload = inventory_forecast_files(FORECAST_ROOTS)
    write_json(OUT / "CYCLE33_FORECAST_FILE_INVENTORY.json", payload)
    return payload


def all22_inventory() -> dict[str, Any]:
    checkouts: list[dict[str, Any]] = []
    for root in ALL22_ROOTS:
        item: dict[str, Any] = {"path": str(root), "exists": root.exists()}
        git_dir = root / ".git"
        item["git"] = git_dir.exists() or git_dir.is_file()
        if item["exists"] and item["git"]:
            try:
                head = subprocess.check_output(
                    ["git", "-C", str(root), "rev-parse", "HEAD"],
                    text=True,
                ).strip()
                status = subprocess.check_output(
                    ["git", "-C", str(root), "status", "--porcelain"],
                    text=True,
                )
                item["head"] = head
                item["dirty"] = bool(status.strip())
            except (OSError, subprocess.CalledProcessError) as exc:
                item["error"] = str(exc)
        elif root.is_dir():
            children = []
            for child in sorted(root.iterdir()):
                git = child / ".git"
                if not (git.exists() or git.is_file()):
                    continue
                rec: dict[str, Any] = {"path": str(child)}
                try:
                    rec["head"] = subprocess.check_output(
                        ["git", "-C", str(child), "rev-parse", "HEAD"],
                        text=True,
                    ).strip()
                    rec["dirty"] = bool(
                        subprocess.check_output(
                            ["git", "-C", str(child), "status", "--porcelain"],
                            text=True,
                        ).strip()
                    )
                except (OSError, subprocess.CalledProcessError) as exc:
                    rec["error"] = str(exc)
                children.append(rec)
            item["child_checkouts"] = children
            item["checkout_count"] = len(children)
        checkouts.append(item)
    payload = {
        "artifact_type": "CYCLE33_ALL22_CHECKOUT_INVENTORY",
        "as_of_utc": utc_now(),
        "checkouts": checkouts,
        "prior_count_11_is_not_permanent_expected": True,
        "dirty_owner_files_preserved": True,
        "c01_owner_adoption": "C01_OWNER_ADOPTION_PENDING",
        "self_approval_forbidden": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_ALL22_CHECKOUT_INVENTORY.json", payload)
    return payload


def main() -> int:
    imported = import_snapshot()
    payload = {
        "artifact_type": "CYCLE33_AVAILABILITY_PIT_CORPUS_POINTER",
        "as_of_utc": utc_now(),
        "not_starting_stack": True,
        "availability": availability(),
        "pit": pit(),
        "corpus": corpus(imported),
        "queries": queries(imported),
        "forecasts": forecasts(),
        "all22": all22_inventory(),
        "headline": "IN_PROGRESS_LOCAL_WORK_REMAINS",
        "operator_hold": "ACTIVE",
        "paid_ai": 0,
    }
    write_json(SNAP / "CYCLE33_AVAILABILITY_PIT_CORPUS_POINTER.json", payload)
    write_json(OUT / "CYCLE33_AVAILABILITY_PIT_CORPUS_SUMMARY.json", payload)
    print(json.dumps(
        {
            "availability_routes": payload["availability"].get("route_count"),
            "player_candidates": payload["availability"].get("player_candidate_count"),
            "pit_proven": payload["pit"]["independent"]["independently_proven_count"],
            "conservation": payload["corpus"]["conservation"]["conserved"],
            "named_overlaps": payload["corpus"]["overlaps"]["all_named_found"],
            "risk_count": payload["corpus"]["risk_fragments"]["count"],
            "query_fbs": payload["queries"]["historical_fbs_rows"],
            "forecast_files": payload["forecasts"]["file_count"],
            "all22_checkouts": len(payload["all22"]["checkouts"]),
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
