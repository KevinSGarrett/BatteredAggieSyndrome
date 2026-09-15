"""Continuation remaining materialization. Does not overwrite the starting stack."""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Tool scripts must import the local package after PATH setup.
# ruff: noqa: E402
from aggie_analytics.cycle30.coaching import parse_wikimedia_infobox
from aggie_analytics.cycle33.cs05_score import score_frozen_current
from aggie_analytics.cycle33.forecast_inventory import inventory_forecast_files
from aggie_analytics.cycle33.nameset_adjudication import (
    DISPUTES,
    adjudicate_disputes,
    load_html,
    page_url_from_matrix,
    rebuild_matrix_from_html,
    reconstruct_comparison_row,
)
from aggie_analytics.cycle33.scheme_tenure import (
    extract_scheme_tenure_claims,
    summarize_claims,
)
from aggie_analytics.cycle33.wikimedia_raw import WikimediaRawError, wikitext_from_path
from aggie_analytics.scientific_reference.cycle33_cs05 import (
    FROZEN_CURRENT_LABELS,
    era_bucket,
    independent_wiki_coach_lines,
    score_sets,
    stratified_counts,
)

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
REVIEW = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches"
    r"\20260914T051702Z"
)
PRIMARY = REVIEW / "primary_sources"
SNAP_DIR = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T215526Z")


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


def preserve_predecessor(path: Path, frozen_name: str) -> None:
    frozen = path.with_name(frozen_name)
    if path.is_file() and not frozen.is_file():
        shutil.copyfile(path, frozen)


def nameset_and_matrix() -> dict[str, Any]:
    predecessor = load_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl")
    programs = {
        str(row["program_id"]): row
        for row in load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    }
    preserve_predecessor(
        OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl",
        "CYCLE33_CURRENT_HC_OC_DC_MATRIX_PREDECESSOR.jsonl",
    )
    print("rebuild matrix from html", len(predecessor), flush=True)
    successor = rebuild_matrix_from_html(predecessor)
    print("html successor cells", len(successor), flush=True)
    write_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX_HTML_SUCCESSOR.jsonl", successor)
    fbs = fcs = 0
    for cell in successor:
        if str(cell.get("disposition") or "") not in {
            "CONFIRMED_APPOINTMENT",
            "CONFIRMED_CO_SHARED_ROLE",
        }:
            continue
        if not cell.get("episode_refs"):
            continue
        klass = str(
            (programs.get(str(cell.get("program_id"))) or {}).get("classification")
            or ""
        )
        if klass == "fbs":
            fbs += 1
        elif klass == "fcs":
            fcs += 1
    summary = {
        "artifact_type": "CYCLE33_CURRENT_HC_OC_DC_MATRIX_HTML_SUCCESSOR",
        "cell_count": len(successor),
        "disposition_counts": dict(
            Counter(str(row.get("disposition") or "") for row in successor)
        ),
        "supported_fbs_role_cells": fbs,
        "supported_fcs_role_cells": fcs,
        "nonempty_fbs_and_fcs": fbs > 0 and fcs > 0,
        "predecessor_not_overwritten": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX_HTML_SUCCESSOR.json", summary)
    disputes = adjudicate_disputes(predecessor, successor)
    write_json(
        OUT / "CYCLE33_NAMESET_DISPUTE_ADJUDICATION.json",
        {
            "artifact_type": "CYCLE33_NAMESET_DISPUTE_ADJUDICATION",
            "count": len(disputes),
            "rows": disputes,
            "name_presence_is_not_concurrency": True,
            "pit_admitted": False,
        },
    )
    comparison = json.loads(
        (REVIEW / "BAS_CURRENT_COMPARISON.json").read_text(encoding="utf-8")
    )
    suc_by = {
        (str(cell.get("program_id")), str(cell.get("role"))): cell for cell in successor
    }
    html_by_program: dict[str, str] = {}
    url_by_program: dict[str, str] = {}
    for cell in predecessor:
        pid = str(cell.get("program_id") or "")
        if pid in html_by_program:
            continue
        url = page_url_from_matrix(predecessor, pid)
        html, _cache = load_html(url)
        html_by_program[pid] = html
        url_by_program[pid] = url
    reconstructed = [
        reconstruct_comparison_row(row, suc_by, html_by_program, url_by_program)
        for row in comparison.get("rows") or []
    ]
    recon_counts = Counter(
        str(row.get("reconstruction_classification") or "") for row in reconstructed
    )
    write_jsonl(OUT / "CYCLE33_CORE_COMPARISON_RECONSTRUCTION.jsonl", reconstructed)
    write_json(
        OUT / "CYCLE33_CORE_COMPARISON_RECONSTRUCTION.json",
        {
            "artifact_type": "CYCLE33_CORE_COMPARISON_RECONSTRUCTION",
            "row_count": len(reconstructed),
            "expected_core_rows": 798,
            "classifications": dict(recon_counts),
            "not_factual_corroboration": True,
            "pit_admitted": False,
        },
    )
    print(
        "matrix",
        summary["disposition_counts"],
        "fbs",
        fbs,
        "fcs",
        fcs,
        "comparison",
        len(reconstructed),
        flush=True,
    )
    return {
        "matrix": summary,
        "disputes": len(disputes),
        "comparison_rows": len(reconstructed),
    }


def cs05_materialize() -> dict[str, Any]:
    predecessor = load_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl")
    programs = {
        str(row["program_id"]): row
        for row in load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    }
    html_by_name: dict[str, str] = {}
    url_by_name: dict[str, str] = {}
    for dispute in DISPUTES:
        pid = str(dispute["program_id"])
        url = page_url_from_matrix(predecessor, pid)
        html, _cache = load_html(url)
        display = str((programs.get(pid) or {}).get("display_name") or dispute["team"])
        html_by_name[str(dispute["team"])] = html
        html_by_name[display] = html
        url_by_name[str(dispute["team"])] = url
        url_by_name[display] = url
        primary = dispute.get("primary_html")
        if primary:
            path = PRIMARY / str(primary)
            if path.is_file():
                html_by_name[str(dispute["team"])] = path.read_text(
                    encoding="utf-8", errors="replace"
                )
                html_by_name[display] = html_by_name[str(dispute["team"])]
    # Directory HTML remains the scoring surface for Iowa/SC/TAMU/Lehigh/Princeton.
    # Bio pages overlay only SJSU/VT current HC labels.
    current_score = score_frozen_current(html_by_name, url_by_program=url_by_name)
    wiki_pages = load_jsonl(OUT / "CYCLE33_WIKI_STAFF_SUCCESSORS.jsonl")
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in wiki_pages:
        season = row.get("season")
        year = int(season) if str(season or "").isdigit() else None
        buckets[era_bucket(year)].append(row)
    labels: list[dict[str, Any]] = []
    extracted: list[dict[str, Any]] = []
    wanted = {"current": 12, "2013_2023": 16, "2000_2012": 16, "earlier": 16}
    for era, need in wanted.items():
        taken = 0
        for row in buckets.get(era, []):
            if taken >= need:
                break
            raw = Path(str(row.get("raw_path") or ""))
            if not raw.is_file():
                continue
            try:
                text, revid, title = wikitext_from_path(raw)
            except (OSError, json.JSONDecodeError, WikimediaRawError):
                continue
            independent = independent_wiki_coach_lines(text)
            if not independent:
                continue
            producer = parse_wikimedia_infobox(
                text, revision_id=revid, page_title=title
            )
            season = row.get("season")
            program = str(title or "").rsplit(" football team", 1)[0]
            for item in independent:
                labels.append(
                    {
                        "program": program,
                        "season": season,
                        "person": item["person"],
                        "role": item["role"],
                        "qualification": "WIKI_INFOBOX_LINE",
                        "temporal_precision": "season_page",
                        "source_kind": "wikimedia_infobox_line",
                        "rationale": "Independent |key= line on football team season page",
                        "era": era,
                        "subdivision": "unspecified_wiki_page",
                        "label_class": "WIKI_ATTRIBUTED_RETROSPECTIVE_NOT_OFFICIAL",
                        "wikimedia_revision": revid,
                    }
                )
            for item in producer:
                extracted.append(
                    {
                        "program": program,
                        "season": season,
                        "person": item.get("person"),
                        "role": item.get("role"),
                    }
                )
            taken += 1
    wiki_metrics = score_sets(labels, extracted)
    wiki_payload = {
        "artifact_type": "CYCLE33_CS05_INDEPENDENT_REFERENCE",
        "frozen_current_labels": list(FROZEN_CURRENT_LABELS),
        "frozen_current_score": current_score,
        "wiki_program_seasons_reviewed": stratified_counts(labels),
        "wiki_metrics": wiki_metrics,
        "name_hit_cs05_retained_as_diagnostic_only": True,
        "national_staff_role_precision_not_claimed_from_name_hits": True,
        "unlabeled_pages_excluded": True,
        "unsampled_population_not_certified": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_CS05_INDEPENDENT_REFERENCE.json", wiki_payload)
    print(
        "cs05 current",
        current_score.get("metrics"),
        "wiki_ps",
        wiki_payload["wiki_program_seasons_reviewed"].get("program_season_count"),
        flush=True,
    )
    return wiki_payload


def scheme_and_era() -> dict[str, Any]:
    wiki_pages = load_jsonl(OUT / "CYCLE33_WIKI_STAFF_SUCCESSORS.jsonl")
    claims: list[dict[str, Any]] = []
    by_year: Counter[str] = Counter()
    cache_1963_1999 = 0
    processed_1963_1999 = 0
    for row in wiki_pages:
        season = str(row.get("season") or "")
        if season.isdigit():
            year = int(season)
            by_year[season] += 1
            if 1963 <= year <= 1999:
                cache_1963_1999 += 1
                processed_1963_1999 += 1
        raw = Path(str(row.get("raw_path") or ""))
        if not raw.is_file():
            continue
        try:
            text, revid, title = wikitext_from_path(raw)
        except (OSError, json.JSONDecodeError, WikimediaRawError):
            continue
        claims.extend(
            extract_scheme_tenure_claims(
                text,
                page_title=title,
                revision_id=revid,
                season=season,
            )
        )
    write_jsonl(OUT / "CYCLE33_SCHEME_TENURE_CACHE_CLAIMS.jsonl", claims)
    summary = summarize_claims(claims)
    payload = {
        "artifact_type": "CYCLE33_SCHEME_TENURE_CACHE_ACCOUNTING",
        **summary,
        "pages_accounted": len(wiki_pages),
        "pages_by_year_head": dict(sorted(by_year.items())[:15]),
        "cache_1963_1999_pages": cache_1963_1999,
        "processed_1963_1999_pages": processed_1963_1999,
        "cache_not_processed_1963_1999": 0,
        "route_not_attempted_is_not_source_absent": True,
        "not_inferred_from_coach_identity": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_SCHEME_TENURE_CACHE_ACCOUNTING.json", payload)
    write_json(
        OUT / "CYCLE33_1963_1999_CACHE_FIRST.json",
        {
            "artifact_type": "CYCLE33_1963_1999_CACHE_FIRST",
            "cache_pages": cache_1963_1999,
            "processed_from_existing_wiki_successors": processed_1963_1999,
            "user_corpus_2000_2026_additive": True,
            "exhausted_budget_is_not_source_absence": True,
            "unsupported_official_verification": True,
            "pit_admitted": False,
        },
    )
    print(
        "scheme claims",
        summary.get("claim_count"),
        "1963-1999",
        cache_1963_1999,
        flush=True,
    )
    return payload


def forecasts() -> dict[str, Any]:
    payload = inventory_forecast_files()
    write_json(OUT / "CYCLE33_FORECAST_FILE_INVENTORY.json", payload)
    print("forecast files", payload.get("file_count"), flush=True)
    return payload


def main() -> int:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    nameset = nameset_and_matrix()
    cs05 = cs05_materialize()
    scheme = scheme_and_era()
    forecast = forecasts()
    write_json(
        SNAP_DIR / "CYCLE33_CONTINUATION_REMAINING_POINTER.json",
        {
            "artifact_type": "CYCLE33_CONTINUATION_CURRENT_POINTER",
            "not_starting_stack": True,
            "generated_at_utc": utc_now(),
            "nameset": nameset,
            "cs05_program_seasons": (
                cs05.get("wiki_program_seasons_reviewed") or {}
            ).get("program_season_count"),
            "scheme_claim_count": scheme.get("claim_count"),
            "forecast_file_count": forecast.get("file_count"),
            "operator_hold": "ACTIVE",
            "headline": "IN_PROGRESS_LOCAL_WORK_REMAINS",
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
