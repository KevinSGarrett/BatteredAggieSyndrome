"""Cache-first remaining Cycle 33 local materialization. No hold release."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.cycle30.acquisition import parse_ncaa_com_scoreboard_contests
from aggie_analytics.cycle30.coaching import parse_wikimedia_infobox
from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics.cycle30.kernel_model import (
    CANDIDATES,
    KernelModelError,
    fold_local_fit,
)
from aggie_analytics.cycle33.career_identity import join_occupant_to_pages
from aggie_analytics.cycle33.official_finals import competing_observations
from aggie_analytics.cycle33.query import (
    connect_for_import,
    load_scheme_claims,
    team_schemes,
)
from aggie_analytics.cycle33.role_taxonomy import assignments_from_title
from aggie_analytics.cycle33.span_locate import locate_person_title
from aggie_analytics.cycle33.week2 import (
    cutoffs_from_kickoff_epoch,
    historical_tamu_asu_row,
    utc_now as week2_now,
)
from aggie_analytics.cycle33.wikimedia_raw import WikimediaRawError, wikitext_from_path
from aggie_analytics.scientific_reference.cycle33 import unique_game_population

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
CENSUS = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle32\20260911T214000Z"
    r"\science\RAW_SCHEME_TENURE_REFERENCE.json"
)
WORKTREE = Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr")
ROOT = Path(r"C:\BatteredAggieSyndrome")
AVAIL32 = CYCLE32 / "CYCLE32_AVAILABILITY_STRUCTURED_EXHAUSTION.json"
KERNEL = PRED / "PIT_KERNEL_ROWS.jsonl"
PARSED = CYCLE32 / "CYCLE32_OFFICIAL_STAFF_PARSED.jsonl"
PARSER_VERSION = "BAS-WIKI-FOOTBALL-TOPLEVEL-v33.1"
OFFICIAL_HTML = PRED.parent / "raw" / "official_staff"
REMAINING_NAMED_DOMAINS = (
    "injuries",
    "recruiting",
    "rosters",
    "resources",
    "weather",
    "games",
    "plays",
    "markets",
    "officials",
    "penalties",
    "transfers",
    "snap_counts",
    "tracking",
    "depth_charts",
    "nil",
    "returning_production",
    "special_teams_units",
    "tempo",
    "rest",
    "travel",
    "altitude",
    "timezone",
    "high_school",
    "nfl_draft",
    "betting_splits",
    "substitution",
    "play_calling_observed",
    "film_formation",
)


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
        ["git", *args], cwd=cwd, text=True, stderr=subprocess.STDOUT
    ).strip()


def starting_stack() -> dict[str, Any]:
    worktrees = git(ROOT, "worktree", "list", "--porcelain")
    try:
        prs = subprocess.check_output(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--limit",
                "40",
                "--json",
                "number,headRefName,baseRefName,headRefOid,url",
            ],
            cwd=WORKTREE,
            text=True,
            stderr=subprocess.STDOUT,
        )
        pr_rows = json.loads(prs)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        pr_rows = []
    existing = OUT / "CYCLE33_STARTING_STACK.json"
    if existing.is_file():
        payload = json.loads(existing.read_text(encoding="utf-8"))
        current = {
            "artifact_type": "CYCLE33_CURRENT_STACK",
            "as_of_utc": utc_now(),
            "cycle33_head": git(WORKTREE, "rev-parse", "HEAD"),
            "cycle33_branch": git(WORKTREE, "branch", "--show-current"),
            "starting_stack_preserved": True,
            "starting_stack_path": str(existing),
            "hold": "SCIENTIFIC_OPERATOR_HOLD_ACTIVE",
        }
        write_json(OUT / "CYCLE33_CURRENT_STACK.json", current)
        return payload
    payload = {
        "artifact_type": "CYCLE33_STARTING_STACK",
        "as_of_utc": utc_now(),
        "cycle33_head": git(WORKTREE, "rev-parse", "HEAD"),
        "cycle33_branch": git(WORKTREE, "branch", "--show-current"),
        "cycle33_status": git(WORKTREE, "status", "--porcelain"),
        "predecessor_head": git(
            Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr"),
            "rev-parse",
            "HEAD",
        ),
        "canonical_main_not_validation_subject": git(ROOT, "rev-parse", "HEAD"),
        "worktree_count": sum(
            1 for line in worktrees.splitlines() if line.startswith("worktree ")
        ),
        "worktree_list": worktrees,
        "open_prs": pr_rows,
        "pythonpath_src_required": True,
        "hold": "SCIENTIFIC_OPERATOR_HOLD_ACTIVE",
        "cwd_at_run": os.getcwd(),
        "dirty_tree_digest": hashlib.sha256(
            git(WORKTREE, "status", "--porcelain=v1").encode("utf-8")
        ).hexdigest(),
    }
    write_json(OUT / "CYCLE33_STARTING_STACK.json", payload)
    return payload


def week2() -> dict[str, Any]:
    now = week2_now()
    tamu = historical_tamu_asu_row(now)
    contests: list[dict[str, Any]] = []
    files = []
    for name in (
        "scoreboard-2026-00.html",
        "scoreboard-2026-01.html",
        "scoreboard-2026-02.html",
        "scoreboard-2026-03.html",
    ):
        path = NCAA / name
        info: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
        if not path.is_file():
            files.append(info)
            continue
        parsed = parse_ncaa_com_scoreboard_contests(
            path.read_text(encoding="utf-8", errors="replace")
        )
        info["parsed_contest_count"] = len(parsed)
        files.append(info)
        for contest in parsed:
            cut = cutoffs_from_kickoff_epoch(contest.get("start_time_epoch"), now=now)
            seos = {
                str(contest.get("home_seoname") or "").casefold(),
                str(contest.get("away_seoname") or "").casefold(),
            }
            row = {
                **contest,
                **cut,
                "source_file": name,
                "forecast_classification": "UNTRUSTED_SHADOW",
                "retroactive_forecast_forbidden": True,
                "week2_outcomes_do_not_tune_or_select": True,
            }
            if seos == {"texas-am", "arizona-st"}:
                row["t24h_deadline_utc"] = tamu["t24h_deadline_utc"]
                row["t90m_deadline_utc"] = tamu["t90m_deadline_utc"]
                row["t24h_disposition"] = tamu["t24h_disposition"]
                row["t90m_disposition"] = tamu["t90m_disposition"]
                row["cutoff_source"] = "PACK_HISTORICAL_TAMU_ASU_DEADLINES"
                row["canonical_contest_note"] = "TAMU_ASU_HISTORICAL_NO_REARM"
                row["missouri_state_identity_forbidden"] = True
            status = str(contest.get("status_code_display") or "").casefold()
            if "postpon" in status or "cancel" in status:
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
    finals = competing_observations(
        [
            {
                "ncaa_com_contest_id": row.get("ncaa_com_contest_id"),
                "home_points": row.get("home_points"),
                "away_points": row.get("away_points"),
                "home_name": row.get("home_name"),
                "away_name": row.get("away_name"),
                "game_state": row.get("game_state"),
                "status_code_display": row.get("status_code_display"),
                "terminal_state": row.get("terminal_state"),
            }
            for row in contests
            if row.get("ncaa_com_contest_id")
        ]
    )
    week2_rows = [
        row for row in contests if row.get("source_file") == "scoreboard-2026-02.html"
    ]
    cutoff_counts = Counter(str(row.get("t24h_disposition")) for row in contests)
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
        "week2_contest_count": len(week2_rows),
        "t24h_disposition_counts": dict(cutoff_counts),
        "kickoff_epoch_cutoffs": True,
        "fcs_separate_scoreboard": "NOT_IN_THIS_CACHE_SET",
        "new_scheduler_installed": False,
        "rearm_forbidden": True,
        "invented_forecast": False,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_WEEK2_NATIONAL_CENSUS.json", payload)
    write_jsonl(OUT / "CYCLE33_WEEK2_CONTESTS.jsonl", contests)
    write_json(
        OUT / "CYCLE33_OFFICIAL_FINALS_SUCCESSOR.json",
        {
            "artifact_type": "CYCLE33_OFFICIAL_FINALS_SUCCESSOR",
            "observation_count": finals["observation_count"],
            "unique_contest_count": finals["unique_contest_count"],
            "admitted_unique_games": len(finals["admitted_unique_games"]),
            "quarantined_conflicts": finals["quarantined_conflicts"],
            "nonfinal_contests": len(finals.get("nonfinal_contests") or []),
            "first_win_forbidden": True,
            "last_win_forbidden": True,
            "requested_week_is_not_source_week": True,
            "metrics_recomputed_on": "admitted_unique_frozen_games_only",
            "unfrozen_excluded_from_scoring": True,
            "pit_admitted": False,
        },
    )
    return payload


def taxonomy() -> dict[str, Any]:
    rows = load_jsonl(PARSED)
    occupancy: Counter[str] = Counter()
    unmapped: Counter[str] = Counter()
    for row in rows:
        title = str(row.get("title") or row.get("source_title") or "")
        mapped = assignments_from_title(title) if title else []
        for item in mapped:
            occupancy[item["occupancy"]] += 1
            if item["occupancy"] == "UNMAPPED":
                unmapped[title] += 1
    payload = {
        "artifact_type": "CYCLE33_OFFICIAL_STAFF_TAXONOMY_SUCCESSOR",
        "parsed_records": len(rows),
        "occupancy_counts": dict(occupancy),
        "unmapped_distinct_titles": len(unmapped),
        "unmapped_titles": unmapped.most_common(),
        "predecessor_other_position": 5337,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_OFFICIAL_STAFF_TAXONOMY.json", payload)
    return payload


def wiki_staff_reparse() -> dict[str, Any]:
    jsonl_path = OUT / "CYCLE33_WIKI_STAFF_SUCCESSORS.jsonl"
    successors: list[dict[str, Any]]
    errors = 0
    if jsonl_path.is_file() and jsonl_path.stat().st_size > 0:
        successors = load_jsonl(jsonl_path)
    else:
        census = json.loads(CENSUS.read_text(encoding="utf-8"))
        rows = census.get("rows") or []
        successors = []
        seen: set[str] = set()
        for row in rows:
            raw_path = str(row.get("raw_path") or "")
            if not raw_path or raw_path in seen:
                continue
            seen.add(raw_path)
            path = Path(raw_path)
            title = str(row.get("title") or "")
            revision = str(row.get("revision") or "")
            if not path.is_file():
                errors += 1
                continue
            try:
                text, revid, page_title = wikitext_from_path(path)
            except (OSError, json.JSONDecodeError, WikimediaRawError):
                errors += 1
                continue
            episodes = parse_wikimedia_infobox(
                text, revision_id=revid or revision, page_title=page_title or title
            )
            season = None
            for token in (page_title or title).split():
                if token.isdigit() and len(token) == 4:
                    season = token
                    break
            successors.append(
                {
                    "title": page_title or title,
                    "wikimedia_revision": revid or revision,
                    "season": season,
                    "episode_count": len(episodes),
                    "episodes": episodes,
                    "parser_version": PARSER_VERSION,
                    "raw_path": raw_path,
                    "pit_admitted": False,
                }
            )
        write_jsonl(jsonl_path, successors)
    people = sum(int(row.get("episode_count") or 0) for row in successors)
    by_year: Counter[str] = Counter()
    pre2013 = 0
    for row in successors:
        season = row.get("season")
        if str(season or "").isdigit():
            by_year[str(season)] += 1
            if int(str(season)) < 2013:
                pre2013 += 1
    payload = {
        "artifact_type": "CYCLE33_WIKI_STAFF_SUCCESSORS",
        "pages": len(successors),
        "page_errors": errors,
        "episode_count": people,
        "parser_version": PARSER_VERSION,
        "pre_2013_pages": pre2013,
        "pages_by_year_sample": dict(sorted(by_year.items())[:20]),
        "not_official_verification": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_WIKI_STAFF_SUCCESSORS.json", payload)
    return payload


def _fold_name(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


def _page_is_football_career(page: Mapping[str, Any]) -> bool:
    title = str(page.get("title") or page.get("requested_title") or "")
    lowered = title.casefold()
    if (
        any(
            token in lowered
            for token in (
                "politician",
                "disambiguation",
                "mayor",
                "senator",
                "basketball",
                "baseball",
                "soccer",
            )
        )
        and "football" not in lowered
    ):
        return False
    episodes = page.get("episodes") or []
    if "football" in lowered:
        return True
    return bool(episodes) and str(page.get("status") or "") == "REVISION_BOUND"


def career_joins() -> dict[str, Any]:
    matrix = load_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl")
    pages = load_jsonl(PRED / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl")
    successor = [
        page
        for page in load_jsonl(CYCLE32 / "CYCLE32_WIKI_CAREER_PAGES_SUCCESSOR.jsonl")
        if str(page.get("status") or "") == "REVISION_BOUND"
    ]
    pages = [*pages, *successor]
    programs = {
        str(row.get("program_id")): row
        for row in load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    }
    by_title: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in pages:
        title = str(page.get("title") or page.get("requested_title") or "")
        if title:
            by_title[_fold_name(title)].append(page)
        head, sep, _rest = title.partition(" (")
        if sep:
            by_title[_fold_name(head)].append(page)
    occupants = []
    counts: Counter[str] = Counter()
    for cell in matrix:
        display = str(
            (programs.get(str(cell.get("program_id"))) or {}).get("display_name") or ""
        )
        for ep in cell.get("episode_refs") or []:
            person = str(ep.get("person") or "").strip()
            if not person:
                continue
            candidates = by_title.get(_fold_name(person)) or []
            joined = join_occupant_to_pages(
                person=person, employer=display, pages=candidates
            )
            state = str(joined["career_join_state"])
            counts[state] += 1
            occupants.append(
                {
                    "program_id": cell.get("program_id"),
                    "display_name": display,
                    "role": cell.get("role"),
                    "person": person,
                    **joined,
                    "predecessor_evidence_bound_rechecked": True,
                    "pit_admitted": False,
                }
            )
    pred_career = OUT / "CYCLE33_CURRENT_OCCUPANT_CAREER_JOINS.json"
    frozen_career = OUT / "CYCLE33_CURRENT_OCCUPANT_CAREER_JOINS_PREDECESSOR.json"
    if pred_career.is_file() and not frozen_career.is_file():
        shutil.copyfile(pred_career, frozen_career)
    predecessor_bound = 0
    if frozen_career.is_file():
        predecessor_bound = int(
            json.loads(frozen_career.read_text(encoding="utf-8")).get("matched") or 0
        )
    payload = {
        "artifact_type": "CYCLE33_CURRENT_OCCUPANT_CAREER_JOINS",
        "occupant_count": len(occupants),
        "state_counts": dict(counts),
        "matched": counts.get("EVIDENCE_BOUND_CAREER_JOIN", 0),
        "missing": counts.get("CAREER_PAGE_MISSING", 0),
        "ambiguous": counts.get("AMBIGUOUS_MULTIPLE_FOOTBALL_PAGES", 0),
        "name_only_not_accepted": counts.get("NAME_ONLY_CANDIDATE_NOT_ACCEPTED", 0),
        "employer_unverified": counts.get("FOOTBALL_PAGE_EMPLOYER_UNVERIFIED", 0),
        "same_name_only_not_accepted_as_join": True,
        "predecessor_evidence_bound_count": predecessor_bound,
        "occupants_rechecked": len(occupants),
        "empty_employer_rejected": True,
        "substring_join_forbidden": True,
        "revision_ids_are_not_people": True,
        "pit_admitted": False,
    }
    write_jsonl(OUT / "CYCLE33_CURRENT_OCCUPANT_CAREER_JOINS.jsonl", occupants)
    write_json(OUT / "CYCLE33_CURRENT_OCCUPANT_CAREER_JOINS.json", payload)
    return payload


def scheme_sqlite() -> dict[str, Any]:
    db = OUT / "cycle33_user_coaches.sqlite"
    claims_path = OUT / "CYCLE33_SCHEME_TENURE_CLAIMS.jsonl"
    if not claims_path.is_file():
        return {"loaded": 0, "missing": str(claims_path)}
    claims = load_jsonl(claims_path)
    nonempty = [row for row in claims if row.get("source_text")]
    conn = connect_for_import(db)
    try:
        loaded = load_scheme_claims(conn, nonempty)
        air = team_schemes(conn, program="Air Force", season="2018")
        sample = team_schemes(conn, program="Lehigh", season="2026")
    finally:
        conn.close()
    payload = {
        "artifact_type": "CYCLE33_SCHEME_QUERY_LOAD",
        "claims_file_rows": len(claims),
        "nonempty_loaded": loaded,
        "air_force_2018_scheme_rows": len(air),
        "lehigh_2026_scheme_rows": len(sample),
        "inferred": False,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_SCHEME_QUERY_LOAD.json", payload)
    return payload


def cs05() -> dict[str, Any]:
    receipts = json.loads(
        (REVIEW / "PRIMARY_SOURCE_RECEIPTS.json").read_text(encoding="utf-8")
    )
    matrix = load_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl")
    programs = {
        str(row.get("program_id")): row
        for row in load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    }
    labeled = []
    tp = fp = fn = 0
    for receipt in receipts:
        path = Path(receipt["path"])
        html = (
            path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
        )
        rid = str(receipt["id"])
        expected_names: list[str] = []
        if "sjsu" in rid:
            expected_names = ["Ken Niumatalolo"]
        elif "vt_head" in rid:
            expected_names = ["James Franklin"]
        elif "lehigh" in rid:
            expected_names = ["Dan Hunt"]
        elif "princeton" in rid:
            expected_names = ["E.J. Henderson", "Mike Weick"]
        hits = [name for name in expected_names if name.casefold() in html.casefold()]
        program_hits = []
        for cell in matrix:
            display = str(
                (programs.get(str(cell.get("program_id"))) or {}).get("display_name")
                or ""
            )
            if rid.startswith("sjsu") and display.casefold() != "san jose state":
                continue
            if rid.startswith("vt_head") and display.casefold() != "virginia tech":
                continue
            people = [
                str(ep.get("person") or "") for ep in cell.get("episode_refs") or []
            ]
            program_hits.extend(people)
        for name in expected_names:
            in_html = name.casefold() in html.casefold()
            in_matrix = any(name.casefold() == p.casefold() for p in program_hits)
            if in_html and in_matrix:
                tp += 1
            elif in_html and not in_matrix:
                fn += 1
            elif in_matrix and not in_html:
                fp += 1
        labeled.append(
            {
                "reference_id": rid,
                "http_status": receipt.get("http_status"),
                "html_name_hits": hits,
                "parser_not_used_to_label": True,
                "manual_slice": True,
                "pit_admitted": False,
            }
        )
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    payload = {
        "artifact_type": "CYCLE33_CS05_REFERENCE_SET",
        "manual_primary_supported_slice": labeled,
        "manual_slice_count": len(labeled),
        "named_identity_tp": tp,
        "named_identity_fp": fp,
        "named_identity_fn": fn,
        "precision": precision,
        "recall": recall,
        "unsampled_population": "ALL_OTHER_STAFF_AND_HISTORICAL_ROWS",
        "does_not_prove_unsampled_correct": True,
        "name_hit_diagnostic_only": True,
        "not_national_staff_role_precision_recall": True,
        "unknown_oc_dc_not_forced": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_CS05_REFERENCE_SET.json", payload)
    return payload


def historical_2000_2012_wiki() -> dict[str, Any]:
    path = PRED / "WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl"
    cells: list[dict[str, Any]] = []
    by_year: Counter[str] = Counter()
    pages = 0
    if path.is_file():
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                title = str(row.get("title") or "")
                season = None
                for token in title.split():
                    if token.isdigit() and len(token) == 4:
                        season = int(token)
                        break
                if season is None or season < 2000 or season > 2012:
                    continue
                pages += 1
                by_year[str(season)] += 1
                for ep in row.get("episodes") or []:
                    if not ep.get("person"):
                        continue
                    cells.append(
                        {
                            "season": season,
                            "program_id": row.get("program_id"),
                            "title": title,
                            "person": ep.get("person"),
                            "role": ep.get("role"),
                            "source_title": ep.get("source_title") or ep.get("title"),
                            "wikimedia_revision": row.get("wikimedia_revision"),
                            "disposition": "WIKI_ATTRIBUTED_RETROSPECTIVE_NOT_OFFICIAL",
                            "parser_version": PARSER_VERSION,
                            "verified": False,
                            "pit_admitted": False,
                        }
                    )
    write_jsonl(OUT / "CYCLE33_WIKI_2000_2012_STAFF_CELLS.jsonl", cells)
    payload = {
        "artifact_type": "CYCLE33_WIKI_2000_2012_STAFF_CELLS",
        "pages": pages,
        "nonempty_person_cells": len(cells),
        "by_year": dict(sorted(by_year.items())),
        "not_replacement_for_user_corpus": True,
        "not_full_national_verification": True,
        "older_than_2000_backlog_owner": "BAT-701",
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_WIKI_2000_2012_STAFF_CELLS.json", payload)
    return payload


def corroboration() -> dict[str, Any]:
    matrix = load_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl")
    wiki = load_jsonl(PRED / "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl")
    successor_wiki = OUT / "CYCLE33_WIKI_STAFF_SUCCESSORS.jsonl"
    wiki_source = (
        "CYCLE33_WIKI_STAFF_SUCCESSORS.jsonl"
        if successor_wiki.is_file()
        else "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl"
    )
    wiki_by: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for row in wiki:
        pid = str(row.get("program_id") or "")
        for ep in row.get("episodes") or []:
            role = str(ep.get("role") or "")
            person = str(ep.get("person") or "")
            if pid and role and person:
                wiki_by[pid][role].append(person)
    claims = []
    for cell in matrix:
        pid = str(cell.get("program_id") or "")
        role = str(cell.get("role") or "")
        official = [
            str(item.get("person") or "")
            for item in (cell.get("episode_refs") or [])
            if item.get("person")
        ]
        wiki_people = wiki_by.get(pid, {}).get(role, [])
        off_f = {name.casefold() for name in official}
        wiki_f = {name.casefold() for name in wiki_people}
        if not official and not wiki_people:
            support = "BOTH_ABSENT"
        elif official and not wiki_people:
            support = "OFFICIAL_ONLY_WIKI_MISSING"
        elif wiki_people and not official:
            support = "WIKI_ONLY_NOT_OFFICIAL"
        elif off_f == wiki_f:
            support = "NAME_AGREEMENT_NOT_INDEPENDENT_CORROBORATION"
        elif off_f & wiki_f:
            support = "PARTIAL_OVERLAP_CONFLICT"
        else:
            support = "CONFLICT"
        claims.append(
            {
                "program_id": pid,
                "role": role,
                "official_people": official,
                "wikipedia_people": wiki_people,
                "official_disposition": cell.get("disposition"),
                "field_support": support,
                "wikipedia_is_not_verification": True,
                "pit_admitted": False,
            }
        )
    counts: Counter[str] = Counter(row["field_support"] for row in claims)
    payload = {
        "artifact_type": "CYCLE33_WIKI_OFFICIAL_FIELD_CLAIMS",
        "cells": len(claims),
        "every_field_comparison_emitted": True,
        "sample_limit_not_used": True,
        "wikipedia_source": wiki_source,
        "predecessor_6240_snapshot_retained": True,
        "successor_parsed_records": 6215,
        "support_counts": dict(counts),
        "independent_primary_corroboration_complete": False,
        "pit_admitted": False,
    }
    write_jsonl(OUT / "CYCLE33_WIKI_OFFICIAL_FIELD_CLAIMS.jsonl", claims)
    write_json(OUT / "CYCLE33_WIKI_OFFICIAL_FIELD_CLAIMS.json", payload)
    return payload


def kernel_replay() -> dict[str, Any]:
    rows = load_jsonl(KERNEL)
    historical = [row for row in rows if 2013 <= int(row.get("season") or 0) <= 2023]
    independent = unique_game_population(historical)
    unique_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in historical:
        gid = str(row.get("canonical_game_id") or "")
        if not gid or gid in seen_ids:
            continue
        seen_ids.add(gid)
        unique_rows.append(row)
    fits = []
    fit_error = None
    try:
        for candidate in CANDIDATES:
            fit = fold_local_fit(unique_rows, candidate=candidate)
            fits.append(
                {
                    "candidate": candidate,
                    "train_games": fit["train_games"],
                    "eval_games": fit["eval_games"],
                    "excluded_train": fit["excluded_train"],
                    "excluded_eval": fit["excluded_eval"],
                    "weights": fit["weights"],
                    "consumed_columns": fit["consumed_columns"],
                    "no_winner_selected": True,
                }
            )
    except KernelModelError as exc:
        fit_error = str(exc)
    payload = {
        "artifact_type": "CYCLE33_KERNEL_REPLAY",
        "historical_rows": len(historical),
        "unique_rows_fit": len(unique_rows),
        "independent": independent,
        "fits": fits,
        "fit_error": fit_error,
        "proven_pit": 0,
        "classification": "UNTRUSTED_SHADOW",
        "week1_week2_not_used_to_tune": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_KERNEL_REPLAY.json", payload)
    return payload


def availability() -> dict[str, Any]:
    inherited = (
        json.loads(AVAIL32.read_text(encoding="utf-8")) if AVAIL32.is_file() else {}
    )
    contests = load_jsonl(OUT / "CYCLE33_WEEK2_CONTESTS.jsonl")
    expected = []
    for row in contests:
        expected.append(
            {
                "ncaa_com_contest_id": row.get("ncaa_com_contest_id"),
                "home": row.get("home_name"),
                "away": row.get("away_name"),
                "availability_disposition": "NO_REPORT_IS_UNKNOWN_NOT_HEALTHY",
                "membership_is_not_availability": True,
                "pit_admitted": False,
            }
        )
    payload = {
        "artifact_type": "CYCLE33_AVAILABILITY_NATIONAL",
        "inherited_cycle32_acquisition_complete": inherited.get("acquisition_complete"),
        "inherited_asset_row_count": len(inherited.get("asset_rows") or []),
        "week2_expected_contest_keys": len(expected),
        "js_shell_is_not_report": True,
        "no_report_is_not_healthy": True,
        "no_new_source_in_frozen_pregame": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_AVAILABILITY_NATIONAL.json", payload)
    write_jsonl(OUT / "CYCLE33_AVAILABILITY_EXPECTED_KEYS.jsonl", expected)
    return payload


def all22() -> dict[str, Any]:
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
            git_dir = child / ".git"
            item: dict[str, Any] = {"path": str(child), "git": git_dir.exists()}
            if git_dir.exists() or (child / ".git").is_file():
                try:
                    item["head"] = git(child, "rev-parse", "HEAD")
                    item["status"] = git(child, "status", "--porcelain")
                    item["dirty"] = bool(item["status"])
                except subprocess.CalledProcessError as exc:
                    item["error"] = str(exc)
            checkouts.append(item)
    payload = {
        "artifact_type": "CYCLE33_ALL22_COMPATIBILITY",
        "as_of_utc": utc_now(),
        "checkouts_observed": checkouts,
        "checkout_count": len(checkouts),
        "c01_owner_adoption": "C01_OWNER_ADOPTION_PENDING",
        "dirty_owner_work_modified": False,
        "gridiron_runtime_authorized": False,
        "staff_snapshot_v1_lossy": True,
        "stale_resume_not_executed": True,
    }
    write_json(OUT / "CYCLE33_ALL22_COMPATIBILITY.json", payload)
    return payload


def locatable_spans() -> dict[str, Any]:
    matrix = load_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl")
    html_cache: dict[str, str] = {}
    confirmed = 0
    locatable = 0
    cache_missing = 0
    string_only = 0
    audits: list[dict[str, Any]] = []
    loc_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for cell in matrix:
        if str(cell.get("disposition") or "") not in {
            "CONFIRMED_APPOINTMENT",
            "CONFIRMED_CO_SHARED_ROLE",
        }:
            continue
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
            html = html_cache[url]
            found = locate_person_title(
                html,
                person=str(ep.get("person") or ""),
                title=str(ep.get("source_title") or ""),
            )
            ep_audit = {
                "program_id": cell.get("program_id"),
                "person": ep.get("person"),
                "title": ep.get("source_title"),
                "page_url": url,
                "span_id": ep.get("span_id"),
                **found,
                "cache_path": str(cache) if cache.is_file() else None,
            }
            audits.append(ep_audit)
            if not html:
                cache_missing += 1
                string_only += 1
            elif found.get("role_claim_supported"):
                locatable += 1
            elif found.get("string_located"):
                string_only += 1
            else:
                string_only += 1
            loc_map[
                (
                    str(cell.get("program_id")),
                    str(ep.get("person")),
                    str(ep.get("source_title")),
                )
            ] = found
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
            found = loc_map.get(
                (
                    str(cell.get("program_id")),
                    str(ep.get("person")),
                    str(ep.get("source_title")),
                )
            ) or {"locatable": False}
            new_eps.append({**ep, **found})
        kept = [ep for ep in new_eps if ep.get("role_claim_supported")]
        if kept and len(kept) == len(new_eps):
            successor.append(
                {**cell, "episode_refs": new_eps, "span_adjudicated": True}
            )
        elif kept:
            successor.append(
                {
                    **cell,
                    "episode_refs": kept,
                    "quarantined_unlocatable_episodes": [
                        ep for ep in new_eps if not ep.get("role_claim_supported")
                    ],
                    "disposition": "CONFIRMED_PARTIAL_SPAN_LOCATABLE",
                    "span_adjudicated": True,
                    "pit_admitted": False,
                }
            )
            quarantined_cells += 1
        else:
            successor.append(
                {
                    **cell,
                    "episode_refs": new_eps,
                    "disposition": "SPAN_NOT_LOCATABLE_QUARANTINE",
                    "span_adjudicated": True,
                    "pit_admitted": False,
                }
            )
            quarantined_cells += 1
    pred_audit = OUT / "CYCLE33_CONFIRMED_SPAN_AUDIT.json"
    frozen = OUT / "CYCLE33_CONFIRMED_SPAN_AUDIT_PREDECESSOR.json"
    if pred_audit.is_file() and not frozen.is_file():
        shutil.copyfile(pred_audit, frozen)
    write_jsonl(OUT / "CYCLE33_CONFIRMED_SPAN_AUDIT.jsonl", audits)
    write_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX_SPAN_SUCCESSOR.jsonl", successor)
    payload = {
        "artifact_type": "CYCLE33_CONFIRMED_SPAN_AUDIT",
        "confirmed_episode_count": confirmed,
        "role_claim_supported_episodes": locatable,
        "string_located_without_same_record_role": string_only,
        "body_offset_present": locatable,
        "string_built_without_body_offset": string_only,
        "cache_html_missing": cache_missing,
        "string_built_span_with_url": confirmed,
        "quarantined_or_partial_cells": quarantined_cells,
        "predecessor_matrix_not_overwritten": str(
            OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl"
        ),
        "successor_matrix": str(
            OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX_SPAN_SUCCESSOR.jsonl"
        ),
        "note": "CONFIRMED requires same-record ROLE_CLAIM_SUPPORTED, not page-wide locatable",
        "unsupported_confirmed_if_not_locatable": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_CONFIRMED_SPAN_AUDIT.json", payload)
    return payload


def name_set_disagreements() -> dict[str, Any]:
    disagreements = json.loads(
        (OUT / "CYCLE33_BAS_CURRENT_NAMESET_DISAGREEMENTS.json").read_text(
            encoding="utf-8"
        )
    )
    receipts = {
        str(row["id"]): row
        for row in json.loads(
            (REVIEW / "PRIMARY_SOURCE_RECEIPTS.json").read_text(encoding="utf-8")
        )
    }
    rows = []
    for item in disagreements.get("rows") or []:
        team = str(item.get("team") or "").casefold()
        receipt = None
        if "san jose" in team:
            receipt = receipts.get("sjsu_head_2026")
        elif "virginia tech" in team:
            receipt = receipts.get("vt_head_2026")
        elif "lehigh" in team:
            receipt = receipts.get("lehigh_staff_2026")
        elif "princeton" in team:
            receipt = receipts.get("princeton_staff_2026")
        html = ""
        if receipt:
            path = Path(receipt["path"])
            html = (
                path.read_text(encoding="utf-8", errors="replace")
                if path.is_file()
                else ""
            )
        csv_text = str(item.get("csv_text") or "")
        csv_names = [
            part.split("—")[0].split("|")[0].strip()
            for part in csv_text.replace("–", "—").split("|")
        ]
        csv_hits = [
            name for name in csv_names if name and name.casefold() in html.casefold()
        ]
        bas_hits = [
            name
            for name in item.get("bas_people") or []
            if name and str(name).casefold() in html.casefold()
        ]
        rows.append(
            {
                **item,
                "primary_html_csv_name_hits": csv_hits,
                "primary_html_bas_name_hits": bas_hits,
                "primary_receipt_id": (receipt or {}).get("id"),
                "identity_accepted": False,
                "fact_verified": False,
                "classification": "CANDIDATE_NAME_SET_DIFFERENCE_REVIEW_REQUIRED",
                "automated_verdict_forbidden": True,
            }
        )
    payload = {
        "artifact_type": "CYCLE33_NAMESET_PRIMARY_REVIEW",
        "count": len(rows),
        "rows": rows,
        "not_automated_verdicts": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_NAMESET_PRIMARY_REVIEW.json", payload)
    return payload


def remaining_named_domains() -> dict[str, Any]:
    payload = {
        "artifact_type": "CYCLE33_PLAN_REMAINING_UNION",
        "remaining_named_not_manager_pending": True,
        "adjudicated_tranche": [
            "coaching",
            "scheme",
            "availability",
            "neutral",
            "identity",
            "c01",
        ],
        "unreviewed_named_domains": list(REMAINING_NAMED_DOMAINS),
        "no_100_percent_mapped_claim": True,
        "heuristic_8111_not_semantic_acceptance": True,
    }
    write_json(OUT / "CYCLE33_PLAN_REMAINING_UNION.json", payload)
    return payload


def claim_evidence() -> dict[str, Any]:
    payload = {
        "artifact_type": "CYCLE33_CLAIM_LEVEL_EVIDENCE",
        "generic_three_file_bundle_forbidden": True,
        "inherited": {
            "R32": "see CYCLE32_REQUIREMENT_REVIEW.json and CYCLE32 focused tests",
            "WG32": "wiki parser tests in test_cycle32_manager_counterexamples.py",
            "R31": "ORIGINAL_MR31_MEANINGS in cycle33.findings",
        },
        "rows": [
            {
                "id": "R33-03",
                "evidence": str(OUT / "CYCLE33_OFFICIAL_STAFF_TAXONOMY.json"),
            },
            {
                "id": "R33-05",
                "evidence": str(OUT / "CYCLE33_WIKI_STAFF_SUCCESSORS.json"),
            },
            {
                "id": "R33-07",
                "evidence": str(OUT / "CYCLE33_SCHEME_TENURE_CLAIMS.json"),
            },
            {
                "id": "R33-09",
                "evidence": str(OUT / "CYCLE33_WIKI_2000_2012_STAFF_CELLS.json"),
            },
            {
                "id": "R33-10",
                "evidence": str(OUT / "CYCLE33_WIKI_OFFICIAL_FIELD_CLAIMS.json"),
            },
            {"id": "R33-12", "evidence": str(OUT / "CYCLE33_KERNEL_REPLAY.json")},
            {
                "id": "R33-13",
                "evidence": str(OUT / "CYCLE33_OFFICIAL_FINALS_SUCCESSOR.json"),
            },
            {
                "id": "R33-23",
                "evidence": str(OUT / "CYCLE33_USER_COACHES_IMPORT_SUMMARY.json"),
            },
        ],
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_CLAIM_LEVEL_EVIDENCE.json", payload)
    return payload


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "as_of_utc": utc_now(),
        "starting_stack": starting_stack(),
        "week2": week2(),
        "taxonomy": taxonomy(),
        "wiki_staff": wiki_staff_reparse(),
        "career": career_joins(),
        "scheme_sqlite": scheme_sqlite(),
        "cs05": cs05(),
        "historical_2000_2012": historical_2000_2012_wiki(),
        "corroboration": corroboration(),
        "kernel": kernel_replay(),
        "availability": availability(),
        "all22": all22(),
        "spans": locatable_spans(),
        "nameset": name_set_disagreements(),
        "remaining_domains": remaining_named_domains(),
        "claim_evidence": claim_evidence(),
        "hold": "SCIENTIFIC_OPERATOR_HOLD_ACTIVE",
        "paid_ai_cost": 0,
    }
    write_json(OUT / "CYCLE33_EXHAUST_REMAINING.json", payload)
    print(
        json.dumps(
            {
                "week2_obs": payload["week2"]["observation_count"],
                "week2_unique": payload["week2"]["unique_contest_ids"],
                "taxonomy_unmapped": payload["taxonomy"]["unmapped_distinct_titles"],
                "wiki_pages": payload["wiki_staff"]["pages"],
                "career_matched": payload["career"]["matched"],
                "kernel_rows": payload["kernel"]["historical_rows"],
                "kernel_unique": payload["kernel"]["independent"]["unique_games"],
                "hist_2000_2012_cells": payload["historical_2000_2012"][
                    "nonempty_person_cells"
                ],
                "corroboration_cells": payload["corroboration"]["cells"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
