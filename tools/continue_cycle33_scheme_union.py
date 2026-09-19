"""Post-process scheme claims and name remaining unreviewed plan sections.

Does not infer missing schemes, resolve conflicts by last-win, or treat
Wikipedia family tags as official corroboration or PIT.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle33.scheme_tenure import (
    apply_scheme_normalization,
    mark_scheme_conflicts,
    summarize_claims,
)

SCI = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
PLAN_INDEX = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle32"
    r"\20260911T214000Z\PLAN_DISCOVERY_INDEX.json"
)
OFFICIAL_STAFF = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\official_staff"
)
CLAIMS_JSONL = SCI / "CYCLE33_SCHEME_TENURE_CLAIMS.jsonl"
MAX_OFFICIAL_FILES = 400
SCHEME_HINT = re.compile(
    r"off_scheme|def_scheme|base_defense|offensive scheme|defensive scheme|"
    r"air[\s\-]?raid|pro[\s\-]?style",
    re.I,
)
REMAINING_DOMAIN_TOKENS = {
    "injuries": ("injur",),
    "recruiting": ("recruit",),
    "rosters": ("roster",),
    "resources": ("resource",),
    "weather": ("weather",),
    "games": ("game_spine", "games/", "/games"),
    "plays": ("play_", "/plays", "play-by-play", "pbp"),
    "markets": ("market", "betting"),
    "officials": ("officiat", "referee", "umpire"),
    "penalties": ("penalt",),
    "transfers": ("transfer",),
    "snap_counts": ("snap",),
    "tracking": ("tracking", "player_track"),
    "depth_charts": ("depth_chart", "depth-chart", "/depth"),
    "nil": ("nil",),
    "returning_production": ("returning_production", "returning-production"),
    "special_teams_units": ("special_teams", "special-teams"),
    "tempo": ("tempo",),
    "rest": ("_rest", "/rest", "rest_", "travel_rest"),
    "travel": ("travel",),
    "altitude": ("altitude",),
    "timezone": ("timezone", "time_zone", "time-zone"),
    "high_school": ("high_school", "high-school"),
    "nfl_draft": ("nfl_draft", "draft"),
    "betting_splits": ("betting_split", "split"),
    "substitution": ("substitut",),
    "play_calling_observed": ("play_call", "play-call"),
    "film_formation": ("film", "formation"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _named_discovery_sections(
    index: Sequence[Mapping[str, Any]], tokens: tuple[str, ...]
) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for entry in index:
        path = str(entry.get("path") or "")
        headings = " ".join(str(item) for item in (entry.get("headings") or []))
        folded = f"{path} {headings}".replace("\\", "/").casefold()
        if not any(token in folded for token in tokens):
            continue
        matches.append(
            {
                "path": path,
                "semantic_review": str(entry.get("semantic_review") or "UNREVIEWED"),
                "extraction": str(
                    entry.get("extraction")
                    or "DISCOVERY_ONLY_NOT_FULL_REQUIREMENT_EXTRACTION"
                ),
            }
        )
        if len(matches) == 25:
            break
    return matches


def normalize_existing_claims() -> dict[str, Any]:
    raw = load_jsonl(CLAIMS_JSONL)
    normalized = mark_scheme_conflicts([apply_scheme_normalization(row) for row in raw])
    CLAIMS_JSONL.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in normalized) + "\n",
        encoding="utf-8",
    )
    summary = summarize_claims(normalized)
    family_counts: Counter[str] = Counter(
        str(tag.get("code"))
        for row in normalized
        for tag in row.get("family_tags") or []
    )
    conflicts = [
        {
            "page_title": row.get("page_title"),
            "season": row.get("season"),
            "field": row.get("field"),
            "source_text": row.get("source_text"),
            "conflict_texts": row.get("conflict_texts"),
        }
        for row in normalized
        if row.get("conflict_distinct_source_text")
    ]
    payload = {
        "artifact_type": "CYCLE33_SCHEME_NORMALIZATION",
        "as_of_utc": utc_now(),
        "parser_version": summary["parser_version"],
        "normalization_version": summary["normalization_version"],
        "input_claims": len(raw),
        "output_claims": len(normalized),
        "summary": summary,
        "family_tag_counts": dict(family_counts),
        "conflict_claim_count": len(conflicts),
        "conflict_group_count": len(
            {
                (row.get("page_title"), row.get("season"), row.get("field"))
                for row in conflicts
            }
        ),
        "wikipedia_is_not_official": True,
        "inferred_count": summary["inferred_count"],
        "pit_admitted": False,
    }
    write_json(SCI / "CYCLE33_SCHEME_NORMALIZATION.json", payload)
    (SCI / "CYCLE33_SCHEME_CONFLICTS.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in conflicts)
        + ("\n" if conflicts else ""),
        encoding="utf-8",
    )
    existing = load_json(SCI / "CYCLE33_SCHEME_TENURE_CLAIMS.json")
    existing["as_of_utc"] = utc_now()
    existing["claims"] = summary
    existing["normalization"] = str(SCI / "CYCLE33_SCHEME_NORMALIZATION.json")
    write_json(SCI / "CYCLE33_SCHEME_TENURE_CLAIMS.json", existing)
    return payload


def scan_official_scheme_corroboration() -> dict[str, Any]:
    files = sorted(OFFICIAL_STAFF.glob("*.html"))[:MAX_OFFICIAL_FILES]
    hits: list[dict[str, Any]] = []
    missing = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            missing += 1
            continue
        if SCHEME_HINT.search(text):
            hits.append({"path": str(path), "bytes": path.stat().st_size})
    payload = {
        "artifact_type": "CYCLE33_SCHEME_OFFICIAL_CORROBORATION_ATTEMPT",
        "as_of_utc": utc_now(),
        "official_html_files_scanned": len(files),
        "official_html_root": str(OFFICIAL_STAFF),
        "hint_hits": len(hits),
        "sample_hits": hits[:20],
        "read_errors": missing,
        "bounded_not_exhaustive": True,
        "hint_hit_is_not_program_season_scheme_join": True,
        "independently_corroborated_scheme_claims": 0,
        "disposition": (
            "SOURCE_UNAVAILABLE_AFTER_DOCUMENTED_ATTEMPTS"
            if not hits
            else "HINT_HITS_NOT_JOINED_TO_CLAIMS"
        ),
        "pit_admitted": False,
    }
    write_json(SCI / "CYCLE33_SCHEME_OFFICIAL_CORROBORATION_ATTEMPT.json", payload)
    return payload


def expand_remaining_union() -> dict[str, Any]:
    index = load_json(PLAN_INDEX)
    named = {
        domain: _named_discovery_sections(index, tokens)
        for domain, tokens in REMAINING_DOMAIN_TOKENS.items()
    }
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
        "unreviewed_named_domains": list(REMAINING_DOMAIN_TOKENS),
        "unreviewed_named_sections": named,
        "named_section_counts": {key: len(value) for key, value in named.items()},
        "domains_with_no_discovery_path_or_heading_match": [
            key for key, value in named.items() if not value
        ],
        "plan_discovery_source": str(PLAN_INDEX),
        "no_100_percent_mapped_claim": True,
        "heuristic_8111_not_semantic_acceptance": True,
        "path_token_match_is_not_section_adjudication": True,
    }
    write_json(SCI / "CYCLE33_PLAN_REMAINING_UNION.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-scheme",
        action="store_true",
        help="Refresh remaining-union naming only; do not rewrite scheme claims.",
    )
    args = parser.parse_args()
    SCI.mkdir(parents=True, exist_ok=True)
    if args.skip_scheme:
        scheme: dict[str, Any] = {}
        official = load_json(SCI / "CYCLE33_SCHEME_OFFICIAL_CORROBORATION_ATTEMPT.json")
    else:
        scheme = normalize_existing_claims()
        official = scan_official_scheme_corroboration()
    remaining = expand_remaining_union()
    summary = scheme.get("summary") or {}
    print(
        json.dumps(
            {
                "family_tagged": summary.get("family_tagged_scheme_count"),
                "unnormalized_visible": summary.get(
                    "unnormalized_visible_scheme_count"
                ),
                "conflicts": scheme.get("conflict_claim_count"),
                "official_hint_hits": official.get("hint_hits"),
                "remaining_domains": remaining["named_section_counts"],
                "domains_with_no_discovery_match": remaining[
                    "domains_with_no_discovery_path_or_heading_match"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
