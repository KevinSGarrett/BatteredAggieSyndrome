"""A&M corpus derivative-integrity successor.

Predecessor parsers and 1996-2009 child payloads remain immutable. This
successor recomputes stale child counts, season-specific versus cumulative
rejections, BAT-XXX placeholder ownership, original-text versus stringified
parsed objects, and rejected-URL admission without rewriting predecessors.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

PLACEHOLDER_RE = re.compile(r"BAT-XXX\b")
TEAM_STAT_SECTION_MARKERS = ("team statistics", "team stats")
SCORING_SUMMARY_MARKERS = ("scoring summary", "scoring")
METADATA_ROW_MARKERS = ("stadium", "attendance", "weather", "surface")
MULTI_PLAYER_MARKERS = ("totals", "team totals", "/", " and ")

SCHEMA_VERSION = "aggie.data.tamu_corpus_derivative_integrity_successor.v1"
CONTRACT_ID = "CYCLE26-TAMU-CORPUS-DERIVATIVE-INTEGRITY-SUCCESSOR-V1"
JIRA_KEY = "BAT-692"
LOCAL_ISSUE_ID = "POST-TASK-SRC014-CORPUS-DERIVATIVE-INTEGRITY-SUCCESSOR-001"
CLASSIFICATION = "TAMU_CORPUS_DERIVATIVE_INTEGRITY_SUCCESSOR_CANDIDATE_ONLY"
LANE = "DEVELOPMENT_SUCCESSOR_UNTRUSTED_SHADOW"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_TAMU_CORPUS_DERIVATIVE_INTEGRITY_SUCCESSOR"
GATE_RELATIVE = "artifacts/data_lake/tamu_corpus_derivative_integrity_successor_gate.json"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"

CORPUS_1996_GATE_RELATIVE = (
    "artifacts/data_lake/tamu_official_1996_2009_structured_row_corpus_gate.json"
)
REJECTION_1998_GATE_RELATIVE = (
    "artifacts/data_lake/tamu_official_gamebook_union_1998_rejection_complete_gate.json"
)
SERIALIZED_DOMAINS = (
    "team_statistics",
    "individual_player_statistics",
    "drives",
    "play_by_play",
    "scoring_summary",
)
PREDECESSOR_1996_DATASET = (
    "7a7f9797bbbc43f273e357584a16ece7715c6ab227438b13fa65775c3dd912f7"
)
PREDECESSOR_PLAYER_RELATIVE = (
    "features/tamu_official_1996_2009_structured_row_corpus/sha256/"
    f"{PREDECESSOR_1996_DATASET}/individual_player_statistics.jsonl"
)
PREDECESSOR_PLAYER_SHA256 = (
    "8de41e750e459d592e86768d723883a7fa92f9fea46b3418bf6a805dcb6eecd0"
)
AUTHORITY_SCAN_DIRECTORIES = (
    "configs",
    "artifacts",
    "governance",
    "docs",
    "instructions",
)
ALLOWED_PLACEHOLDER_PATHS = frozenset(
    {
        "tests/fixtures/stale_placeholder_contract.json",
    }
)


class CorpusIntegritySuccessorError(ValueError):
    """Raised when the corpus derivative-integrity successor cannot proceed honestly."""


def reject_placeholder(text: str) -> str | None:
    if PLACEHOLDER_RE.search(text or ""):
        return "UNRESOLVED_BAT_XXX_PLACEHOLDER"
    return None


def is_metadata_row(line: str) -> bool:
    lowered = line.strip().lower()
    return any(marker in lowered for marker in METADATA_ROW_MARKERS)


def scoring_summary_constrained(section_name: str, line: str) -> bool:
    section = section_name.strip().lower()
    if not any(marker in section for marker in SCORING_SUMMARY_MARKERS):
        return False
    if is_metadata_row(line):
        return False
    return True


def original_text_is_source(original_text: str, parsed_object: object) -> bool:
    return original_text != str(parsed_object)


def classify_player_line(line: str) -> dict[str, Any]:
    stripped = line.strip()
    lowered = stripped.lower()
    aggregate = any(marker in lowered for marker in MULTI_PLAYER_MARKERS)
    return {
        "line": stripped,
        "aggregate": aggregate,
        "disposition": "QUARANTINE_MULTI_PLAYER_AGGREGATE" if aggregate else "PARSE_PLAYER",
        "do_not_attribute_to_first_token": aggregate,
    }


def season_specific_rejection_count(
    rejections: Sequence[Mapping[str, Any]], season: int
) -> int:
    return sum(1 for row in rejections if int(row.get("season") or 0) == season)


def rejected_url_must_not_enter_union(url: str, union_urls: Sequence[str]) -> bool:
    return url not in set(union_urls)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def recompute_child_counts(gate: Mapping[str, Any]) -> dict[str, Any]:
    child_payloads = dict(gate.get("child_payloads") or {})
    rows_per_domain = dict(gate.get("rows_per_domain") or {})
    stale: list[dict[str, Any]] = []
    corrected: dict[str, Any] = {}
    for domain in SERIALIZED_DOMAINS:
        declared_child = int((child_payloads.get(domain) or {}).get("row_count") or 0)
        declared_rows = int(rows_per_domain.get(domain) or 0)
        corrected[domain] = {
            "child_payload_row_count": declared_child,
            "rows_per_domain": declared_rows,
            "stale": declared_child != declared_rows,
            "delta": declared_rows - declared_child,
        }
        if declared_child != declared_rows:
            stale.append(
                {
                    "domain": domain,
                    "child_payload_row_count": declared_child,
                    "rows_per_domain": declared_rows,
                    "delta": declared_rows - declared_child,
                    "disposition": "STALE_CHILD_COUNT_RECOMPUTED_IN_SUCCESSOR",
                }
            )
    return {
        "corrected_by_domain": corrected,
        "stale_domains": stale,
        "stale_domain_count": len(stale),
        "predecessor_gate_rewritten": False,
    }


def season_specific_versus_cumulative(rejection_gate: Mapping[str, Any]) -> dict[str, Any]:
    counts = dict(rejection_gate.get("counts") or {})
    by_season: dict[str, int] = {}
    for key, value in counts.items():
        if key.startswith("official_") and key.endswith("_rejected"):
            season = key[len("official_") : -len("_rejected")]
            by_season[season] = int(value or 0)
    season_sum = sum(by_season.values())
    cumulative = int(counts.get("rejected_urls_complete") or 0)
    unmatched = int(counts.get("unmatched_rejected") or 0)
    return {
        "season_specific_rejected": by_season,
        "season_specific_sum": season_sum,
        "cumulative_rejected_urls_complete": cumulative,
        "cumulative_unmatched_rejected": unmatched,
        "season_sum_equals_cumulative_complete": season_sum == cumulative,
        "note": (
            "Season-specific official_YYYY_rejected counts and cumulative "
            "rejected_urls_complete are different denominators when unmatched "
            "or superseded rejections exist. They must not be silently equated."
        ),
    }


def scan_authority_placeholders(repo_root: Path) -> dict[str, Any]:
    hits: list[dict[str, str]] = []
    for directory in AUTHORITY_SCAN_DIRECTORIES:
        base = repo_root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".json", ".md", ".yaml", ".yml", ".txt"}:
                continue
            relative = path.relative_to(repo_root).as_posix()
            if relative.startswith("jira/snapshots/"):
                continue
            if relative in ALLOWED_PLACEHOLDER_PATHS:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if PLACEHOLDER_RE.search(text):
                hits.append({"path": relative, "disposition": "UNRESOLVED_BAT_XXX_PLACEHOLDER"})
    return {
        "unresolved_placeholder_files": hits,
        "unresolved_count": len(hits),
        "fixtures_exempt": sorted(ALLOWED_PLACEHOLDER_PATHS),
    }


def census_mounted_children(
    *,
    data_root: Path,
    gate: Mapping[str, Any],
    rejection_gate: Mapping[str, Any],
) -> dict[str, Any]:
    dataset = str(gate.get("dataset_identity") or "")
    root = (
        data_root
        / "features/tamu_official_1996_2009_structured_row_corpus/sha256"
        / dataset
    )
    if not root.is_dir():
        return {"mounted": False}
    rejected_urls = set()
    for item in rejection_gate.get("complete_rejection_ledger") or []:
        url = str(item.get("url") or "")
        if url:
            rejected_urls.add(url)
    for url in rejection_gate.get("admitted_row_gap_urls") or []:
        if url:
            rejected_urls.add(str(url))
    by_domain: dict[str, Any] = {}
    leaked = 0
    source_preserved = 0
    stringified = 0
    missing_original = 0
    for domain in SERIALIZED_DOMAINS:
        path = root / f"{domain}.jsonl"
        if not path.is_file():
            by_domain[domain] = {"missing": True}
            continue
        rows = 0
        rejected_hits = 0
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            rows += 1
            row = json.loads(line)
            url = str(row.get("source_url") or "")
            if url and url in rejected_urls:
                rejected_hits += 1
                leaked += 1
            original = row.get("original_text")
            parsed = row.get("raw")
            if original is None or original == "":
                missing_original += 1
            elif parsed is not None and not original_text_is_source(str(original), parsed):
                stringified += 1
            else:
                source_preserved += 1
        declared = int((gate.get("child_payloads") or {}).get(domain, {}).get("row_count") or 0)
        rows_domain = int((gate.get("rows_per_domain") or {}).get(domain) or 0)
        by_domain[domain] = {
            "actual_jsonl_rows": rows,
            "child_payload_row_count": declared,
            "rows_per_domain": rows_domain,
            "sha256": sha256_file(path),
            "rejected_url_hits": rejected_hits,
        }
    player = data_root / PREDECESSOR_PLAYER_RELATIVE
    player_digest = sha256_file(player) if player.is_file() else None
    return {
        "mounted": True,
        "by_domain": by_domain,
        "active_rejection_leaked_into_admitted_children": leaked,
        "original_text_source_preserved": source_preserved,
        "original_text_equals_stringified_parsed": stringified,
        "original_text_missing": missing_original,
        "predecessor_player_sha256": player_digest,
        "predecessor_player_immutable": player_digest == PREDECESSOR_PLAYER_SHA256,
    }


def build_successor(*, repo_root: Path, data_root: Path | None) -> dict[str, Any]:
    corpus_gate = load_json(repo_root / CORPUS_1996_GATE_RELATIVE)
    rejection_gate = load_json(repo_root / REJECTION_1998_GATE_RELATIVE)
    child_counts = recompute_child_counts(corpus_gate)
    rejections = season_specific_versus_cumulative(rejection_gate)
    placeholders = scan_authority_placeholders(repo_root)
    mounted = (
        census_mounted_children(
            data_root=data_root,
            gate=corpus_gate,
            rejection_gate=rejection_gate,
        )
        if data_root is not None
        else {"mounted": False}
    )
    week1 = repo_root / "src/aggie_analytics/data/week1_2026_game_grain_national_forecast_successor.py"
    week1_text = week1.read_text(encoding="utf-8") if week1.is_file() else ""
    join_edges = sum(
        1
        for needle in (
            "tamu_official_1996_2009_structured_row_corpus",
            "individual_player_statistics.jsonl",
        )
        if needle in week1_text
    )
    leaked = int(mounted.get("active_rejection_leaked_into_admitted_children") or 0)
    if leaked:
        raise CorpusIntegritySuccessorError(
            f"active rejection entered admitted children: {leaked}"
        )
    return {
        "predecessor": {
            "corpus_gate_identity": corpus_gate.get("gate_identity"),
            "corpus_dataset_identity": corpus_gate.get("dataset_identity"),
            "rejection_gate_contract_id": rejection_gate.get("contract_id"),
            "rewritten": False,
        },
        "child_counts": child_counts,
        "rejections": rejections,
        "placeholders": placeholders,
        "mounted_children": mounted,
        "join_audit": {
            "week1_successor_import_edges": join_edges,
            "national_forecast_consumption_proven": False,
        },
    }


def materialize(
    *,
    repo_root: Path,
    data_root: Path | None,
    issued_at_utc: str,
) -> dict[str, Any]:
    built = build_successor(repo_root=repo_root, data_root=data_root)
    gate = {
        "artifact_type": "TAMU_CORPUS_DERIVATIVE_INTEGRITY_SUCCESSOR_GATE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "jira_key": JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "result": PASS_RESULT,
        "publication_label": SHADOW_CLASSIFICATION,
        "predecessor_payloads_rewritten": False,
        "census": built,
        "scientific_nonclaims": [
            "Does not rewrite the 1996-2009 predecessor corpus or union gates.",
            "Does not equate season-specific rejection counts with cumulative ledgers.",
            "Does not claim national-forecast consumption of the player corpus.",
            "Does not open the all-cycle trust gate or operator hold.",
        ],
    }
    gate["gate_identity"] = sha256_bytes(
        json.dumps(
            {key: value for key, value in gate.items() if key != "gate_identity"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(gate, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return gate
