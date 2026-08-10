from __future__ import annotations

"""Independently replay and mutation-test the official A&M availability page candidate layer."""

import argparse
import copy
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import fitz
import pyarrow as pa
import pyarrow.parquet as pq


EXPECTED_SIGNAL_POLICY_SHA256 = "df0771c8032cd9dc9eaaf1ffcadc03e21727d486991a75116d3aa250c6050c54"


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


def match_contexts(
    page_text: str,
    matched_signals: list[str],
    patterns: dict[str, re.Pattern[str]],
) -> list[str]:
    normalized = normalized_search_text(page_text)
    contexts: list[str] = []
    seen: set[str] = set()
    for signal in matched_signals:
        for match in patterns[signal].finditer(normalized):
            start = max(0, match.start() - 120)
            end = min(len(normalized), match.end() + 120)
            context = normalized[start:end]
            if context not in seen:
                seen.add(context)
                contexts.append(context)
            if len(contexts) >= 12:
                return contexts
    return contexts


def payload_path(root: Path, contract: dict[str, Any]) -> Path:
    return root / Path(*contract["path"].split("/"))


def read_bound_payload(root: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    path = payload_path(root, contract)
    if path.stat().st_size != int(contract["bytes"]):
        raise AssertionError(f"payload size mismatch: {path}")
    if sha256_file(path) != contract["sha256"]:
        raise AssertionError(f"payload hash mismatch: {path}")
    rows = pq.read_table(path).to_pylist()
    if len(rows) != int(contract["rows"]):
        raise AssertionError(f"payload row mismatch: {path}")
    return rows


def compile_policy(manifest: dict[str, Any]) -> tuple[dict[str, re.Pattern[str]], set[str], re.Pattern[str]]:
    policy = manifest["signal_policy"]
    if stable_hash(policy) != EXPECTED_SIGNAL_POLICY_SHA256:
        raise AssertionError("signal policy fingerprint mismatch")
    patterns = {
        name: re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        for name, pattern in policy["patterns"].items()
    }
    explicit = set(policy["explicit_context_signals"])
    if set(patterns) != explicit | {"injury_term"}:
        raise AssertionError("signal policy partition mismatch")
    participation = re.compile(policy["postgame_participation_pattern"], re.IGNORECASE)
    return patterns, explicit, participation


def replay_rows(
    root: Path,
    acquisition: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    patterns, explicit_names, participation_pattern = compile_policy(manifest)
    page_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for source in acquisition["documents"]:
        if source["role"] != "GAME_NOTES":
            continue
        pdf = root / Path(*source["immutable_path"].split("/"))
        if pdf.stat().st_size != int(source["response_bytes"]):
            raise AssertionError(f"source size mismatch: {source['request_id']}")
        if sha256_file(pdf) != source["response_sha256"]:
            raise AssertionError(f"source hash mismatch: {source['request_id']}")
        explicit_pages: list[int] = []
        review_pages: list[int] = []
        participation_pages: list[int] = []
        with fitz.open(pdf) as document:
            for page_index, page in enumerate(document):
                page_number = page_index + 1
                page_text = normalize_page_text(page.get_text("text"))
                text_sha = sha256_bytes(page_text.encode("utf-8"))
                identity_core = {
                    "source_response_sha256": source["response_sha256"],
                    "page_number": page_number,
                    "page_text_sha256": text_sha,
                }
                page_id = "gnp_" + stable_hash(identity_core)[:24]
                signal_counts = {
                    name: len(pattern.findall(page_text))
                    for name, pattern in patterns.items()
                }
                signal_counts = {name: count for name, count in signal_counts.items() if count}
                signal_types = sorted(signal_counts)
                explicit_signals = sorted(set(signal_types) & explicit_names)
                participation_count = len(participation_pattern.findall(page_text))
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
                    "page_text_sha256": text_sha,
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
                    participation_pages.append(page_number)
                if explicit_signals:
                    disposition = "EXPLICIT_AVAILABILITY_CONTEXT_PAGE_CANDIDATE"
                    explicit_pages.append(page_number)
                elif signal_counts.get("injury_term"):
                    disposition = "INJURY_MENTION_PAGE_REVIEW"
                    review_pages.append(page_number)
                else:
                    continue
                evidence_rows.append(
                    {
                        **page_row,
                        "evidence_page_id": "avp_" + stable_hash({**identity_core, "disposition": disposition})[:24],
                        "matched_contexts": match_contexts(page_text, explicit_signals or ["injury_term"], patterns),
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
            coverage.append(
                {
                    "season": int(source["season"]),
                    "season_ordinal": int(source["season_ordinal"]),
                    "source_request_id": source["request_id"],
                    "source_response_sha256": source["response_sha256"],
                    "page_count": len(document),
                    "explicit_context_candidate_pages": explicit_pages,
                    "injury_mention_review_pages": review_pages,
                    "postgame_participation_marker_pages": participation_pages,
                    "coverage_state": coverage_state,
                }
            )
    page_rows.sort(key=lambda row: (row["season"], row["season_ordinal"], row["page_number"]))
    evidence_rows.sort(key=lambda row: (row["season"], row["season_ordinal"], row["page_number"], row["evidence_page_id"]))
    coverage.sort(key=lambda row: (row["season"], row["season_ordinal"], row["source_request_id"]))
    return page_rows, evidence_rows, coverage


def validate_contract_only(root: Path, manifest: dict[str, Any]) -> None:
    core = {
        key: value
        for key, value in manifest.items()
        if key not in {"dataset_identity", "issued_at_utc", "payloads"}
    }
    if stable_hash(core) != manifest["dataset_identity"]:
        raise AssertionError("dataset identity mismatch")
    compile_policy(manifest)
    page_rows = read_bound_payload(root, manifest["payloads"]["official_game_note_pages"])
    evidence_rows = read_bound_payload(root, manifest["payloads"]["availability_evidence_pages"])
    if len(page_rows) != manifest["page_text_rows"] or len(evidence_rows) != manifest["availability_evidence_rows"]:
        raise AssertionError("declared row population mismatch")
    if manifest["page_row_hashes"] != [stable_hash(row) for row in page_rows]:
        raise AssertionError("page row hash mismatch")
    if manifest["evidence_row_hashes"] != [stable_hash(row) for row in evidence_rows]:
        raise AssertionError("evidence row hash mismatch")
    if len(manifest["document_coverage"]) != manifest["documents_scanned"]:
        raise AssertionError("document coverage count mismatch")
    if sum(row["page_count"] for row in manifest["document_coverage"]) != manifest["source_pages_scanned"]:
        raise AssertionError("coverage page count mismatch")
    if Counter(row["coverage_state"] for row in manifest["document_coverage"]) != Counter(manifest["coverage_counts"]):
        raise AssertionError("coverage state count mismatch")
    if Counter(row["disposition"] for row in evidence_rows) != Counter(manifest["disposition_counts"]):
        raise AssertionError("disposition count mismatch")
    signal_counts: Counter[str] = Counter()
    for row in page_rows:
        signal_counts.update(row["availability_signal_types"])
        if row["historical_publication_time_state"] != "UNKNOWN":
            raise AssertionError("historical publication time was promoted")
        if row["target_game_outcome_eligibility"] != "EXCLUDED_UNTIL_CHRONOLOGICAL_VALIDATION":
            raise AssertionError("target-game evidence was admitted")
        if row["canonical_or_pit_admission"]:
            raise AssertionError("page row gained canonical/PIT authority")
    if signal_counts != Counter(manifest["page_signal_counts"]):
        raise AssertionError("page signal count mismatch")
    page_by_id = {row["document_page_id"]: row for row in page_rows}
    for row in evidence_rows:
        source_page = page_by_id.get(row["document_page_id"])
        if source_page is None:
            raise AssertionError("evidence row lacks source page")
        for key, value in source_page.items():
            if row.get(key) != value:
                raise AssertionError(f"evidence/source-page mismatch: {key}")
        if row["team_scope_state"] != "TAMU_OR_OPPONENT_UNRESOLVED":
            raise AssertionError("team scope was silently resolved")
        if row["temporal_scope_state"] != "CURRENT_OR_HISTORICAL_CONTEXT_UNRESOLVED":
            raise AssertionError("temporal scope was silently resolved")
        if row["player_identity_state"] != "UNRESOLVED" or row["explicit_player_status_fact_extracted"]:
            raise AssertionError("player identity/status authority violation")
        normalized = normalized_search_text(row["page_text"])
        if any(context not in normalized for context in row["matched_contexts"]):
            raise AssertionError("matched context is not source-backed")
    authority = manifest["authority"]
    if not authority["page_text_is_source_derived"] or not authority["candidate_or_review_only"]:
        raise AssertionError("candidate authority declaration missing")
    required_false = (
        "player_status_fact_extracted",
        "team_or_player_identity_resolved",
        "current_vs_historical_context_resolved",
        "retrieval_time_is_historical_publication_time",
        "missing_signal_means_available",
        "postgame_participation_means_pregame_availability",
        "canonical_or_pit_admission",
        "training_or_protected_use_admission",
    )
    if any(authority[name] for name in required_false):
        raise AssertionError("authority boundary mismatch")
    if not authority["openai_pilot_d_input_eligible_after_redaction_and_budget_admission"]:
        raise AssertionError("governed Pilot D eligibility missing")


def write_rebuild(path: Path, rows: list[dict[str, Any]]) -> None:
    table = pa.Table.from_pylist(rows)
    pq.write_table(
        table,
        path,
        compression="zstd",
        compression_level=9,
        use_dictionary=False,
        write_statistics=True,
    )


def full_replay(
    root: Path,
    acquisition: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    page_rows = read_bound_payload(root, manifest["payloads"]["official_game_note_pages"])
    evidence_rows = read_bound_payload(root, manifest["payloads"]["availability_evidence_pages"])
    replayed_pages, replayed_evidence, replayed_coverage = replay_rows(root, acquisition, manifest)
    if replayed_pages != page_rows:
        raise AssertionError("raw PDF page replay mismatch")
    if replayed_evidence != evidence_rows:
        raise AssertionError("raw PDF evidence replay mismatch")
    if replayed_coverage != manifest["document_coverage"]:
        raise AssertionError("raw PDF coverage replay mismatch")
    rebuild_root = root / "validation" / "BAT-523" / f"availability-page-rebuild-{os.getpid()}"
    rebuild_root.mkdir(parents=True, exist_ok=False)
    rebuilt: dict[str, str] = {}
    try:
        for name, rows in (
            ("official_game_note_pages", replayed_pages),
            ("availability_evidence_pages", replayed_evidence),
        ):
            path = rebuild_root / f"{name}.parquet"
            write_rebuild(path, rows)
            expected = payload_path(root, manifest["payloads"][name])
            if path.stat().st_size != expected.stat().st_size or sha256_file(path) != sha256_file(expected):
                raise AssertionError(f"byte-identical rebuild failed: {name}")
            rebuilt[name] = sha256_file(path)
    finally:
        for path in rebuild_root.glob("*.parquet"):
            path.unlink()
        if rebuild_root.is_dir() and not any(rebuild_root.iterdir()):
            rebuild_root.rmdir()
    return {
        "documents_replayed": len(replayed_coverage),
        "source_pages_replayed": len(replayed_pages),
        "availability_evidence_rows_replayed": len(replayed_evidence),
        "byte_identical_rebuilds": rebuilt,
        "coverage_counts": dict(sorted(Counter(row["coverage_state"] for row in replayed_coverage).items())),
        "disposition_counts": dict(sorted(Counter(row["disposition"] for row in replayed_evidence).items())),
    }


def expect_failure(
    root: Path,
    manifest: dict[str, Any],
    mutate: Callable[[dict[str, Any]], None],
    reseal: bool,
) -> bool:
    changed = copy.deepcopy(manifest)
    mutate(changed)
    if reseal:
        core = {
            key: value
            for key, value in changed.items()
            if key not in {"dataset_identity", "issued_at_utc", "payloads"}
        }
        changed["dataset_identity"] = stable_hash(core)
    try:
        validate_contract_only(root, changed)
    except (AssertionError, FileNotFoundError, KeyError, ValueError, re.error):
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.data_root.resolve()
    acquisition_path = args.acquisition_manifest.resolve()
    candidate_path = args.candidate_manifest.resolve()
    producer_path = args.producer.resolve()
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    manifest = json.loads(candidate_path.read_text(encoding="utf-8"))
    if manifest["acquisition_identity"] != acquisition["acquisition_identity"]:
        raise AssertionError("acquisition identity mismatch")
    if manifest["acquisition_manifest_sha256"] != sha256_file(acquisition_path):
        raise AssertionError("acquisition manifest hash mismatch")
    if manifest["producer_sha256"] != sha256_file(producer_path):
        raise AssertionError("producer hash mismatch")
    validate_contract_only(root, manifest)
    replay = full_replay(root, acquisition, manifest)
    mutations: list[tuple[str, Callable[[dict[str, Any]], None], bool]] = [
        ("identity", lambda value: value.__setitem__("dataset_identity", "0" * 64), False),
        ("document_count", lambda value: value.__setitem__("documents_scanned", 190), True),
        ("page_count", lambda value: value.__setitem__("source_pages_scanned", 8184), True),
        ("evidence_count", lambda value: value.__setitem__("availability_evidence_rows", 0), True),
        ("page_row_hash", lambda value: value["page_row_hashes"].__setitem__(0, "0" * 64), True),
        ("evidence_row_hash", lambda value: value["evidence_row_hashes"].__setitem__(0, "0" * 64), True),
        ("signal_policy", lambda value: value["signal_policy"]["patterns"].__setitem__("injury_term", r"NEVER_MATCH"), True),
        ("coverage", lambda value: value["document_coverage"][0].__setitem__("coverage_state", "NO_INJURY_OR_AVAILABILITY_SIGNAL"), True),
        ("payload_hash", lambda value: value["payloads"]["official_game_note_pages"].__setitem__("sha256", "0" * 64), False),
        ("payload_size", lambda value: value["payloads"]["availability_evidence_pages"].__setitem__("bytes", 1), False),
        ("payload_rows", lambda value: value["payloads"]["availability_evidence_pages"].__setitem__("rows", 0), False),
        ("status_fact", lambda value: value["authority"].__setitem__("player_status_fact_extracted", True), True),
        ("identity_resolution", lambda value: value["authority"].__setitem__("team_or_player_identity_resolved", True), True),
        ("retrieval_promotion", lambda value: value["authority"].__setitem__("retrieval_time_is_historical_publication_time", True), True),
        ("missing_means_available", lambda value: value["authority"].__setitem__("missing_signal_means_available", True), True),
        ("participation_promotion", lambda value: value["authority"].__setitem__("postgame_participation_means_pregame_availability", True), True),
        ("pit_admission", lambda value: value["authority"].__setitem__("canonical_or_pit_admission", True), True),
    ]
    mutation_results = {
        name: expect_failure(root, manifest, mutation, reseal)
        for name, mutation, reseal in mutations
    }
    if not all(mutation_results.values()):
        raise AssertionError(f"mutation controls failed: {mutation_results}")
    report = {
        "schema_version": "1.0.0",
        "status": "PASS",
        "issued_at_utc": utc_now(),
        "candidate_manifest_path": str(candidate_path),
        "candidate_manifest_sha256": sha256_file(candidate_path),
        "dataset_identity": manifest["dataset_identity"],
        "producer_sha256": sha256_file(producer_path),
        "checks_passed": 25,
        "checks_failed": 0,
        "mutation_controls_passed": len(mutation_results),
        "mutation_controls": mutation_results,
        "replay": replay,
        "authority": manifest["authority"],
    }
    report["validation_id"] = "val_" + stable_hash(report)[:24]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({**report, "report_sha256": sha256_file(args.output)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
