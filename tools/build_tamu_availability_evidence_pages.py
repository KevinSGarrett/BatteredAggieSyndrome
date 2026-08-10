from __future__ import annotations

"""Build immutable page text and availability-evidence candidates from official A&M game notes."""

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import pyarrow as pa
import pyarrow.parquet as pq


SCHEMA_VERSION = "1.0.0"
SIGNAL_POLICY_VERSION = "tamu-official-availability-page-signals-v1"
PATTERN_SPECS: dict[str, str] = {
    "game_time_decision": r"\bgame[- ]time decision\b",
    "injury_term": r"\binjur(?:y|ies|ed|ing)\b",
    "injury_unavailability": (
        r"\b(?:out|absent|unavailable)\b[^\n.]{0,80}\b(?:injur(?:y|ies|ed|ing)|hurt)\b"
        r"|\b(?:injur(?:y|ies|ed|ing)|hurt)\b[^\n.]{0,80}\b(?:out|absent|unavailable)\b"
    ),
    "missed_due_injury": (
        r"\bmiss(?:ed|es|ing)\b[^\n.]{0,80}\b(?:due to|with|because of|after)\b"
        r"[^\n.]{0,40}\binjur(?:y|ies|ed|ing)\b"
    ),
    "out_for_season": r"\bout (?:for|the remainder of) (?:the )?season\b",
    "practice_status": (
        r"\b(?:did not|limited in|limited at|limited during|missed) practice\b"
        r"|\bnon[- ]contact\b"
    ),
    "return_from_injury": (
        r"\breturn(?:ed|s|ing)? to (?:action|the lineup|lineup|practice)\b"
        r"[^\n.]{0,100}\binjur(?:y|ies|ed|ing)\b"
        r"|\binjur(?:y|ies|ed|ing)\b[^\n.]{0,100}"
        r"\breturn(?:ed|s|ing)? to (?:action|the lineup|lineup|practice)\b"
    ),
    "ruled_out_injury": r"\bruled out\b[^\n.]{0,80}\binjur(?:y|ies|ed|ing)\b",
    "season_ending": r"\bseason[- ]ending\b",
    "sidelined_injury": (
        r"\bsidelined\b[^\n.]{0,80}\binjur(?:y|ies|ed|ing)\b"
        r"|\binjur(?:y|ies|ed|ing)\b[^\n.]{0,80}\bsidelined\b"
    ),
    "status_with_injury_context": (
        r"\b(?:questionable|doubtful|probable|day[- ]to[- ]day)\b[^\n.]{0,80}"
        r"\b(?:injur(?:y|ies|ed|ing)|status|play)\b"
        r"|\b(?:injur(?:y|ies|ed|ing)|status)\b[^\n.]{0,80}"
        r"\b(?:questionable|doubtful|probable|day[- ]to[- ]day)\b"
    ),
}
EXPLICIT_CONTEXT_SIGNALS = tuple(sorted(set(PATTERN_SPECS) - {"injury_term"}))
PATTERNS = {name: re.compile(pattern, re.IGNORECASE | re.MULTILINE) for name, pattern in PATTERN_SPECS.items()}
POSTGAME_PARTICIPATION_RE = re.compile(r"(?<![A-Z])DNP(?![A-Z])|\bdid not play\b", re.IGNORECASE)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_page_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def normalized_search_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def match_contexts(page_text: str, matched_signals: list[str]) -> list[str]:
    normalized = normalized_search_text(page_text)
    contexts: list[str] = []
    seen: set[str] = set()
    for signal in matched_signals:
        for match in PATTERNS[signal].finditer(normalized):
            start = max(0, match.start() - 120)
            end = min(len(normalized), match.end() + 120)
            context = normalized[start:end]
            if context not in seen:
                seen.add(context)
                contexts.append(context)
            if len(contexts) >= 12:
                return contexts
    return contexts


def write_immutable_table(path: Path, rows: list[dict[str, Any]]) -> pa.Table:
    table = pa.Table.from_pylist(rows)
    if path.is_file():
        if pq.read_table(path).to_pylist() != table.to_pylist():
            raise RuntimeError(f"immutable candidate payload collision: {path}")
        return table
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        pq.write_table(
            table,
            temporary,
            compression="zstd",
            compression_level=9,
            use_dictionary=False,
            write_statistics=True,
        )
        os.replace(temporary, path)
    finally:
        if temporary.is_file():
            temporary.unlink()
    return table


def payload_contract(root: Path, path: Path, table: pa.Table) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "rows": table.num_rows,
        "schema": str(table.schema),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    args = parser.parse_args()
    root = args.data_root.resolve()
    acquisition_path = args.acquisition_manifest.resolve()
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    population = acquisition["capture_population"]
    if population["captured_documents"] != 204 or population["pending_documents"] != 0:
        raise RuntimeError("complete official game-note acquisition manifest required")

    page_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    document_coverage: list[dict[str, Any]] = []
    page_signal_counts: Counter[str] = Counter()
    disposition_counts: Counter[str] = Counter()
    for source in acquisition["documents"]:
        if source["role"] != "GAME_NOTES":
            continue
        pdf_path = root / Path(*source["immutable_path"].split("/"))
        if pdf_path.stat().st_size != int(source["response_bytes"]):
            raise RuntimeError(f"source byte-size failure: {source['request_id']}")
        if sha256_file(pdf_path) != source["response_sha256"]:
            raise RuntimeError(f"source hash failure: {source['request_id']}")
        explicit_pages: list[int] = []
        review_pages: list[int] = []
        participation_marker_pages: list[int] = []
        with fitz.open(pdf_path) as document:
            for page_index, page in enumerate(document):
                page_number = page_index + 1
                page_text = normalize_page_text(page.get_text("text"))
                page_text_sha256 = sha256_bytes(page_text.encode("utf-8"))
                evidence_core = {
                    "source_response_sha256": source["response_sha256"],
                    "page_number": page_number,
                    "page_text_sha256": page_text_sha256,
                }
                page_id = "gnp_" + stable_hash(evidence_core)[:24]
                signal_counts = {
                    name: len(pattern.findall(page_text))
                    for name, pattern in PATTERNS.items()
                }
                signal_counts = {name: count for name, count in signal_counts.items() if count}
                signal_types = sorted(signal_counts)
                explicit_signals = sorted(set(signal_types) & set(EXPLICIT_CONTEXT_SIGNALS))
                participation_count = len(POSTGAME_PARTICIPATION_RE.findall(page_text))
                page_signal_counts.update(signal_types)
                page_row = {
                    "document_page_id": page_id,
                    "season": int(source["season"]),
                    "season_ordinal": int(source["season_ordinal"]),
                    "document_label": source["label"],
                    "source_url": source["url"],
                    "source_request_id": source["request_id"],
                    "source_capture_id": source["capture_id"],
                    "source_response_sha256": source["response_sha256"],
                    "source_capture_manifest_sha256": source["capture_manifest_sha256"],
                    "source_pdf_bytes": int(source["response_bytes"]),
                    "page_number": page_number,
                    "page_text": page_text,
                    "page_text_sha256": page_text_sha256,
                    "availability_signal_types": signal_types,
                    "availability_signal_counts_json": json.dumps(signal_counts, sort_keys=True, separators=(",", ":")),
                    "explicit_context_signal_count": sum(signal_counts[name] for name in explicit_signals),
                    "injury_mention_count": signal_counts.get("injury_term", 0),
                    "postgame_participation_marker_count": participation_count,
                    "historical_publication_time_state": "UNKNOWN",
                    "target_game_outcome_eligibility": "EXCLUDED_UNTIL_CHRONOLOGICAL_VALIDATION",
                    "canonical_or_pit_admission": False,
                }
                page_rows.append(page_row)
                if participation_count:
                    participation_marker_pages.append(page_number)
                if explicit_signals:
                    disposition = "EXPLICIT_AVAILABILITY_CONTEXT_PAGE_CANDIDATE"
                    explicit_pages.append(page_number)
                elif signal_counts.get("injury_term"):
                    disposition = "INJURY_MENTION_PAGE_REVIEW"
                    review_pages.append(page_number)
                else:
                    continue
                disposition_counts[disposition] += 1
                evidence_rows.append(
                    {
                        **page_row,
                        "evidence_page_id": "avp_" + stable_hash({**evidence_core, "disposition": disposition})[:24],
                        "matched_contexts": match_contexts(page_text, explicit_signals or ["injury_term"]),
                        "disposition": disposition,
                        "team_scope_state": "TAMU_OR_OPPONENT_UNRESOLVED",
                        "temporal_scope_state": "CURRENT_OR_HISTORICAL_CONTEXT_UNRESOLVED",
                        "player_identity_state": "UNRESOLVED",
                        "explicit_player_status_fact_extracted": False,
                    }
                )
            if explicit_pages:
                coverage_state = "EXPLICIT_CONTEXT_CANDIDATE_PAGES_PRESENT"
            elif review_pages:
                coverage_state = "INJURY_MENTION_REVIEW_PAGES_ONLY"
            else:
                coverage_state = "NO_INJURY_OR_AVAILABILITY_SIGNAL"
            document_coverage.append(
                {
                    "season": int(source["season"]),
                    "season_ordinal": int(source["season_ordinal"]),
                    "source_request_id": source["request_id"],
                    "source_response_sha256": source["response_sha256"],
                    "page_count": len(document),
                    "explicit_context_candidate_pages": explicit_pages,
                    "injury_mention_review_pages": review_pages,
                    "postgame_participation_marker_pages": participation_marker_pages,
                    "coverage_state": coverage_state,
                }
            )

    page_rows.sort(key=lambda row: (row["season"], row["season_ordinal"], row["page_number"]))
    evidence_rows.sort(key=lambda row: (row["season"], row["season_ordinal"], row["page_number"], row["evidence_page_id"]))
    document_coverage.sort(key=lambda row: (row["season"], row["season_ordinal"], row["source_request_id"]))
    if len(document_coverage) != 191:
        raise RuntimeError("official weekly game-note population mismatch")
    if len(page_rows) != sum(row["page_count"] for row in document_coverage):
        raise RuntimeError("page population mismatch")

    coverage_counts = Counter(row["coverage_state"] for row in document_coverage)
    manifest_core = {
        "schema_version": SCHEMA_VERSION,
        "jira_key": "BAT-523",
        "source_id": "SRC-014",
        "domain": "TAMU_OFFICIAL_GAME_NOTE_PAGE_TEXT_AND_AVAILABILITY_EVIDENCE",
        "grain": "SOURCE_DOCUMENT_PAGE",
        "acquisition_identity": acquisition["acquisition_identity"],
        "acquisition_manifest_sha256": sha256_file(acquisition_path),
        "producer_sha256": sha256_file(Path(__file__).resolve()),
        "pymupdf_version": fitz.VersionBind,
        "signal_policy": {
            "version": SIGNAL_POLICY_VERSION,
            "patterns": PATTERN_SPECS,
            "explicit_context_signals": list(EXPLICIT_CONTEXT_SIGNALS),
            "postgame_participation_pattern": POSTGAME_PARTICIPATION_RE.pattern,
        },
        "documents_scanned": len(document_coverage),
        "source_pages_scanned": len(page_rows),
        "page_text_rows": len(page_rows),
        "availability_evidence_rows": len(evidence_rows),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "page_signal_counts": dict(sorted(page_signal_counts.items())),
        "coverage_counts": dict(sorted(coverage_counts.items())),
        "page_row_hashes": [stable_hash(row) for row in page_rows],
        "evidence_row_hashes": [stable_hash(row) for row in evidence_rows],
        "document_coverage": document_coverage,
        "authority": {
            "page_text_is_source_derived": True,
            "candidate_or_review_only": True,
            "player_status_fact_extracted": False,
            "team_or_player_identity_resolved": False,
            "current_vs_historical_context_resolved": False,
            "retrieval_time_is_historical_publication_time": False,
            "missing_signal_means_available": False,
            "postgame_participation_means_pregame_availability": False,
            "canonical_or_pit_admission": False,
            "training_or_protected_use_admission": False,
            "openai_pilot_d_input_eligible_after_redaction_and_budget_admission": True,
        },
    }
    dataset_identity = stable_hash(manifest_core)
    output_root = root / "quarantine" / "historical_known_at" / "sha256" / dataset_identity / "tamu_availability_evidence_pages"
    page_payload = output_root / "official_game_note_pages.parquet"
    evidence_payload = output_root / "availability_evidence_pages.parquet"
    page_table = write_immutable_table(page_payload, page_rows)
    evidence_table = write_immutable_table(evidence_payload, evidence_rows)
    payloads = {
        "availability_evidence_pages": payload_contract(root, evidence_payload, evidence_table),
        "official_game_note_pages": payload_contract(root, page_payload, page_table),
    }
    manifest_path = (
        root
        / "manifests"
        / "historical_known_at"
        / "sha256"
        / dataset_identity
        / "tamu_availability_evidence_pages_manifest.json"
    )
    manifest = {
        **manifest_core,
        "dataset_identity": dataset_identity,
        "issued_at_utc": utc_now(),
        "payloads": payloads,
    }
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing_core = {
            key: value
            for key, value in existing.items()
            if key not in {"dataset_identity", "issued_at_utc", "payloads"}
        }
        if existing.get("dataset_identity") != dataset_identity or existing_core != manifest_core or existing.get("payloads") != payloads:
            raise RuntimeError(f"immutable candidate manifest collision: {manifest_path}")
        manifest = existing
    else:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = manifest_path.with_name(manifest_path.name + f".tmp-{os.getpid()}")
        try:
            temporary.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            os.replace(temporary, manifest_path)
        finally:
            if temporary.is_file():
                temporary.unlink()

    print(
        json.dumps(
            {
                "dataset_identity": dataset_identity,
                "manifest_path": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "documents_scanned": len(document_coverage),
                "source_pages_scanned": len(page_rows),
                "availability_evidence_rows": len(evidence_rows),
                "disposition_counts": manifest_core["disposition_counts"],
                "coverage_counts": manifest_core["coverage_counts"],
                "page_signal_counts": manifest_core["page_signal_counts"],
                "payloads": payloads,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
