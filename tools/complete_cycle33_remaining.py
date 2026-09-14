"""Remaining Cycle 33 local materialization. Cache-first. No hold release."""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.cycle30.acquisition import parse_ncaa_com_scoreboard_contests
from aggie_analytics.cycle33.all22_adapter import compatibility_report
from aggie_analytics.cycle33.findings import BLOCK_CLASSES, full_correction_table
from aggie_analytics.cycle33.role_taxonomy import assignments_from_title
from aggie_analytics.cycle33.week2 import historical_tamu_asu_row, utc_now as week2_now

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
CYCLE32 = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z"
    r"\implementation_output\science"
)
PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
NCAA = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\ncaa")
REVIEW = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches"
    r"\20260914T051702Z"
)
PACK = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle33")
AMEND = REVIEW / "AMENDMENT_VALIDATION.json"
PLANS = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle32"
    r"\20260911T214000Z\PLAN_DISCOVERY_INDEX.json"
)
JIRA_LIVE = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle32"
    r"\20260911T214000Z\jira\LIVE_BAT_CFIP_ISSUES.json"
)
JIRA_RECEIPTS = PACK / "JIRA_UPDATE_RECEIPTS.json"
PARSED = CYCLE32 / "CYCLE32_OFFICIAL_STAFF_PARSED.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def pack_restoration() -> dict[str, Any]:
    expected = json.loads(AMEND.read_text(encoding="utf-8")).get("files") or []
    rows = []
    for item in expected:
        path = Path(item["path"])
        actual = sha256_path(path) if path.is_file() else None
        rows.append(
            {
                "path": str(path),
                "exists": path.is_file(),
                "original_sha256": item.get("sha256"),
                "restored_sha256": actual,
                "byte_identity": actual == item.get("sha256") if actual else False,
            }
        )
    return {
        "artifact_type": "CYCLE33_PACK_RESTORATION",
        "as_of_utc": utc_now(),
        "incident": "ops/cycle33 was deleted by a parallel inventory agent and restored from pack_before plus reconstructed Sept 14 companions",
        "original_byte_identity_count": sum(1 for row in rows if row["byte_identity"]),
        "files": rows,
        "column_map_required_for_importer": (
            PACK / "USER_COACHES_COLUMN_MAP.csv"
        ).is_file(),
        "hold": "SCIENTIFIC_OPERATOR_HOLD_ACTIVE",
    }


def week2_national() -> dict[str, Any]:
    now = week2_now()
    tamu = historical_tamu_asu_row(now)
    files = []
    contests: list[dict[str, Any]] = []
    for name in (
        "scoreboard-2026-00.html",
        "scoreboard-2026-01.html",
        "scoreboard-2026-02.html",
        "scoreboard-2026-03.html",
    ):
        path = NCAA / name
        info: dict[str, Any] = {
            "path": str(path),
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else 0,
        }
        if not path.is_file():
            info["disposition"] = "RAW_MISSING"
            files.append(info)
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        info["contestId_token_count"] = text.count('"contestId"')
        info["looks_like_js_shell"] = "contestId" not in text and (
            "<script" in text.casefold() or len(text) < 5000
        )
        parsed = parse_ncaa_com_scoreboard_contests(text)
        info["parsed_contest_count"] = len(parsed)
        files.append(info)
        for contest in parsed:
            label = f"{contest.get('home_name')} vs {contest.get('away_name')}"
            status = str(contest.get("status_code_display") or "").casefold()
            postponed = "postpon" in status or "cancel" in status
            row = {
                **contest,
                "source_file": name,
                "label": label,
                "postponed_or_cancelled": postponed,
                "forecast_classification": "UNTRUSTED_SHADOW",
                "retroactive_forecast_forbidden": True,
                "week2_outcomes_do_not_tune_or_select": True,
                "t24h_deadline_utc": None,
                "t90m_deadline_utc": None,
                "t24h_disposition": "CUTOFF_UNKNOWN",
                "t90m_disposition": "CUTOFF_UNKNOWN",
            }
            seos = {
                str(contest.get("home_seoname") or "").casefold(),
                str(contest.get("away_seoname") or "").casefold(),
            }
            if seos == {"texas-am", "arizona-st"}:
                row["t24h_deadline_utc"] = tamu["t24h_deadline_utc"]
                row["t90m_deadline_utc"] = tamu["t90m_deadline_utc"]
                row["t24h_disposition"] = tamu["t24h_disposition"]
                row["t90m_disposition"] = tamu["t90m_disposition"]
                row["canonical_contest_note"] = "TAMU_ASU_HISTORICAL_NO_REARM"
                row["ncaa_com_contest_id_bound"] = contest.get("ncaa_com_contest_id")
                row["missouri_state_identity_forbidden"] = True
            if postponed:
                row["operational_disposition"] = "POSTPONED_OR_CANCELLED_NO_FORECAST"
            elif contest.get("terminal_state") == "TERMINAL_STATUS_ESTABLISHED":
                row["operational_disposition"] = "OFFICIAL_FINAL_SCORING_ONLY"
            elif contest.get("game_state") == "P":
                row["operational_disposition"] = (
                    "STALE_PREGAME_CACHE_NO_RETROACTIVE_FORECAST"
                )
            else:
                row["operational_disposition"] = "SCHEDULE_CAPTURED_FORECAST_NOT_ARMED"
            contests.append(row)
    tamu_rows = [
        row
        for row in contests
        if {
            str(row.get("home_seoname") or "").casefold(),
            str(row.get("away_seoname") or "").casefold(),
        }
        == {"texas-am", "arizona-st"}
    ]
    payload = {
        "artifact_type": "CYCLE33_WEEK2_NATIONAL_CENSUS",
        "as_of_utc": utc_now(),
        "clock_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tamu_asu": tamu,
        "scoreboard_files": files,
        "observation_count": len(contests),
        "unique_contest_ids": len(
            {
                row.get("ncaa_com_contest_id")
                for row in contests
                if row.get("ncaa_com_contest_id")
            }
        ),
        "tamu_asu_rows": tamu_rows,
        "fcs_separate_scoreboard": "NOT_IN_THIS_CACHE_SET",
        "kickoff_times_in_parser": True,
        "cutoffs_unknown_except_tamu_asu_historical": True,
        "new_scheduler_installed": False,
        "rearm_forbidden": True,
        "invented_forecast": False,
        "national_week2_contest_census": (
            "PARTIAL_FROM_CACHED_NCAA_SCOREBOARDS"
            if contests
            else "INCOMPLETE_EMPTY_PARSE"
        ),
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_WEEK2_NATIONAL_CENSUS.json", payload)
    (OUT / "CYCLE33_WEEK2_CONTESTS.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in contests)
        + ("\n" if contests else ""),
        encoding="utf-8",
    )
    return payload


def unmapped_titles() -> dict[str, Any]:
    rows = load_jsonl(PARSED)
    occupancy: Counter[str] = Counter()
    unmapped: Counter[str] = Counter()
    for row in rows:
        title = str(row.get("title") or row.get("source_title") or "")
        mapped = assignments_from_title(title) if title else []
        if not mapped:
            occupancy["EMPTY"] += 1
            continue
        for item in mapped:
            occupancy[item["occupancy"]] += 1
            if item["occupancy"] == "UNMAPPED":
                unmapped[title] += 1
    payload = {
        "artifact_type": "CYCLE33_OFFICIAL_STAFF_TAXONOMY_SUCCESSOR",
        "parsed_records": len(rows),
        "occupancy_counts": dict(occupancy),
        "unmapped_distinct_titles": len(unmapped),
        "unmapped_top_40": unmapped.most_common(40),
        "predecessor_other_position": 5337,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_OFFICIAL_STAFF_TAXONOMY.json", payload)
    return payload


def all22_inventory() -> dict[str, Any]:
    roots = [
        Path(r"C:\CFB\repos"),
        Path(r"C:\All-22\repos"),
        Path(r"C:\All-22\FoundationControl"),
    ]
    checkouts = []
    for root in roots:
        if not root.exists():
            checkouts.append({"path": str(root), "exists": False})
            continue
        for child in sorted(root.iterdir()) if root.is_dir() else []:
            git = child / ".git"
            checkouts.append(
                {
                    "path": str(child),
                    "is_dir": child.is_dir(),
                    "git": git.exists(),
                }
            )
    payload = {
        "artifact_type": "CYCLE33_ALL22_COMPATIBILITY",
        "as_of_utc": utc_now(),
        "compatibility": compatibility_report(
            producer_version="StaffRoleEpisodeV1Proposed",
            consumer_version="StaffSnapshotV1",
        ),
        "checkouts_observed": checkouts,
        "c01_owner_adoption": "C01_OWNER_ADOPTION_PENDING",
        "dirty_owner_work_modified": False,
        "gridiron_runtime_authorized": False,
        "stale_resume_not_executed": True,
    }
    write_json(OUT / "CYCLE33_ALL22_COMPATIBILITY.json", payload)
    return payload


def plan_tranche() -> dict[str, Any]:
    if not PLANS.is_file():
        return {"artifact_type": "CYCLE33_PLAN_TRANCHE", "missing": str(PLANS)}
    idx = json.loads(PLANS.read_text(encoding="utf-8"))
    topics = {
        "coaching": [],
        "scheme": [],
        "availability": [],
        "neutral": [],
        "identity": [],
        "c01": [],
    }
    for entry in idx:
        path = str(entry.get("path") or "")
        low = path.casefold()
        if "coach" in low:
            topics["coaching"].append(path)
        if "scheme" in low:
            topics["scheme"].append(path)
        if "availab" in low:
            topics["availability"].append(path)
        if "neutral" in low or "travel" in low:
            topics["neutral"].append(path)
        if "identity" in low:
            topics["identity"].append(path)
        if "c01" in low or "staffsnapshot" in low or "cfip" in low:
            topics["c01"].append(path)
    payload = {
        "artifact_type": "CYCLE33_PLAN_TRANCHE",
        "plan_discovery_entries": len(idx),
        "heuristic_8111_not_semantic_acceptance": True,
        "adjudicated_tranche_paths": {k: v[:40] for k, v in topics.items()},
        "adjudicated_counts": {k: len(v) for k, v in topics.items()},
        "remaining_union": "UNREVIEWED_FULL_SYSTEM_REQUIREMENT_UNION",
        "remaining_named_not_manager_pending": True,
        "cs13_adopted_locally": True,
        "no_100_percent_mapped_claim": True,
    }
    write_json(OUT / "CYCLE33_PLAN_TRANCHE.json", payload)
    return payload


def jira_state() -> dict[str, Any]:
    receipts = (
        json.loads(JIRA_RECEIPTS.read_text(encoding="utf-8"))
        if JIRA_RECEIPTS.is_file()
        else {}
    )
    live_wanted = {}
    if JIRA_LIVE.is_file():
        live = json.loads(JIRA_LIVE.read_text(encoding="utf-8"))
        for item in live:
            key = item.get("key")
            if key in {
                "BAT-701",
                "BAT-706",
                "BAT-523",
                "BAT-401",
                "BAT-429",
                "BAT-696",
                "BAT-703",
                "BAT-704",
                "BAT-708",
            }:
                status = ((item.get("fields") or {}).get("status") or {}).get("name")
                live_wanted[key] = status
    payload = {
        "artifact_type": "CYCLE33_JIRA_STATE",
        "receipts_scope": receipts.get("scope"),
        "full_local_live_mirror_convergence": receipts.get(
            "full_local_live_mirror_convergence"
        ),
        "receipt_updates": receipts.get("updates"),
        "live_snapshot_statuses": live_wanted,
        "no_done_transition": True,
        "no_parent_completion_comment": True,
        "paid_review": "NOT_REVIEWED",
        "paid_cost": 0,
        "hold": "ACTIVE",
    }
    write_json(OUT / "CYCLE33_JIRA_STATE.json", payload)
    return payload


def sportradar_matrix() -> dict[str, Any]:
    docs = [
        Path(
            r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output\science"
        ),
        PRED,
    ]
    found = []
    for root in docs:
        if not root.is_dir():
            continue
        for path in root.glob("*sportradar*"):
            found.append({"path": str(path), "bytes": path.stat().st_size})
        for path in root.glob("*SPORTRADAR*"):
            found.append({"path": str(path), "bytes": path.stat().st_size})
    payload = {
        "artifact_type": "CYCLE33_SPORTRADAR_ROUTE_MATRIX",
        "as_of_utc": utc_now(),
        "injuries_not_inferred_from_guessed_404": True,
        "cached_named_artifacts": found,
        "capability_status": "EVIDENCE_FROM_EXISTING_CACHES_AND_PUBLIC_DOCS_ONLY",
        "unsupported_vs_unauthorized_vs_quota_not_collapsed": True,
        "no_paid_review_provider": True,
    }
    write_json(OUT / "CYCLE33_SPORTRADAR_ROUTE_MATRIX.json", payload)
    return payload


def finding_dispositions() -> dict[str, Any]:
    table = full_correction_table()
    payload = {
        "artifact_type": "CYCLE33_FINDING_DISPOSITION",
        "predecessor_cycle32_report_preserved": True,
        "silent_renumbering": False,
        "mr31_correction_table": table,
        "ucs_findings_path": str(PACK / "USER_COACHES_FINDINGS.json"),
        "block_classes": list(BLOCK_CLASSES),
        "scientific_trust_recovered": False,
    }
    write_json(OUT / "CYCLE33_FINDING_DISPOSITION.json", payload)
    return payload


def starting_stack() -> dict[str, Any]:
    payload = {
        "artifact_type": "CYCLE33_STARTING_STACK",
        "as_of_utc": utc_now(),
        "predecessor_head": "ca8e0a1f4ef3b30e4b50505e98b463daabcd7185",
        "predecessor_pr": 687,
        "predecessor_branch": "codex/BAT-706-cycle32",
        "predecessor_base": "7d680d17b90a784ddf8abbb90230ea48b34fa482",
        "cycle33_worktree": r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr",
        "cycle33_branch": "codex/BAT-706-cycle33",
        "canonical_main_not_validation_subject": "55e12a5aad3a7e843204fcba619c3cb3d3d6194d",
        "reviewed_cycle32_worktree_unmutated": r"C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr",
        "worktree_count_refresh": "see git worktree list at validation",
        "pythonpath_src_required": True,
        "hold": "SCIENTIFIC_OPERATOR_HOLD_ACTIVE",
        "cwd_at_run": os.getcwd(),
    }
    write_json(OUT / "CYCLE33_STARTING_STACK.json", payload)
    return payload


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "as_of_utc": utc_now(),
        "pack": pack_restoration(),
        "week2": week2_national(),
        "taxonomy": unmapped_titles(),
        "all22": all22_inventory(),
        "plans": plan_tranche(),
        "jira": jira_state(),
        "sportradar": sportradar_matrix(),
        "findings": finding_dispositions(),
        "starting_stack": starting_stack(),
    }
    write_json(OUT / "CYCLE33_REMAINING_CONTINUATION.json", payload)
    print(
        json.dumps(
            {
                "pack_byte_identity": payload["pack"]["original_byte_identity_count"],
                "week2_obs": payload["week2"]["observation_count"],
                "week2_unique": payload["week2"]["unique_contest_ids"],
                "taxonomy_unmapped_distinct": payload["taxonomy"][
                    "unmapped_distinct_titles"
                ],
                "occupancy": payload["taxonomy"]["occupancy_counts"],
                "plan_entries": payload["plans"].get("plan_discovery_entries"),
                "jira_convergence": payload["jira"].get(
                    "full_local_live_mirror_convergence"
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
