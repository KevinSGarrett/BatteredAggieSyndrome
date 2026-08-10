from __future__ import annotations

"""Prepare a content-addressed source-selection sample from validated official A&M note pages."""

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def bound_path(root: Path, relative: str, expected_sha256: str) -> Path:
    path = root / Path(*relative.split("/"))
    if not path.is_file():
        raise RuntimeError(f"bound source artifact is absent: {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"bound source hash mismatch: {path} expected={expected_sha256} actual={actual}")
    return path


def normalized_prefix(value: str, maximum: int) -> str:
    return re.sub(r"\s+", " ", value).strip()[:maximum]


def write_immutable(path: Path, payload: bytes) -> None:
    if path.is_file():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable source-sample collision: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        if temporary.is_file():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "configs" / "tamu_availability_source_sample.json",
    )
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = config["source_candidate"]
    manifest_path = bound_path(
        data_root, source["candidate_manifest_relative_path"], source["candidate_manifest_sha256"]
    )
    validation_path = bound_path(
        data_root, source["candidate_validation_relative_path"], source["candidate_validation_report_sha256"]
    )
    page_path = bound_path(data_root, source["page_payload_relative_path"], source["page_payload_sha256"])
    evidence_path = bound_path(
        data_root, source["evidence_payload_relative_path"], source["evidence_payload_sha256"]
    )
    candidate_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if candidate_manifest["dataset_identity"] != source["candidate_identity"]:
        raise RuntimeError("availability candidate identity mismatch")
    if candidate_manifest["acquisition_identity"] != source["acquisition_identity"]:
        raise RuntimeError("availability acquisition identity mismatch")
    if candidate_manifest["acquisition_manifest_sha256"] != source["acquisition_manifest_sha256"]:
        raise RuntimeError("availability acquisition manifest mismatch")
    if validation.get("status") != "PASS" or validation.get("checks_failed") != 0:
        raise RuntimeError("availability candidate has not passed independent validation")
    if len(validation.get("replay", {}).get("byte_identical_rebuilds", {})) != 2:
        raise RuntimeError("availability candidate lacks both byte-identical replay bindings")

    page_rows = pq.read_table(page_path).to_pylist()
    evidence_rows = pq.read_table(evidence_path).to_pylist()
    pages = {row["document_page_id"]: row for row in page_rows}
    evidence = {row["evidence_page_id"]: row for row in evidence_rows}
    if len(pages) != len(page_rows) or len(evidence) != len(evidence_rows):
        raise RuntimeError("duplicate source-page identity")

    output_rows: list[dict[str, Any]] = []
    for case in config["cases"]:
        selection = case["expected_selection_class"]
        if selection == "NO_SIGNAL_NEGATIVE_PAGE":
            row = pages.get(case["row_id"])
            if row is None:
                raise RuntimeError(f"configured negative page is absent: {case['row_id']}")
            if row["availability_signal_types"]:
                raise RuntimeError(f"configured negative page contains a scanner signal: {case['row_id']}")
            excerpt = normalized_prefix(row["page_text"], int(config["excerpt_policy"]["negative_max_characters"]))
            disposition = "NO_INJURY_OR_AVAILABILITY_SIGNAL_IN_COMPLETE_PAGE"
            signal_types: list[str] = []
        else:
            row = evidence.get(case["row_id"])
            if row is None:
                raise RuntimeError(f"configured evidence page is absent: {case['row_id']}")
            expected_disposition = {
                "EXPLICIT_CONTEXT_SIGNAL_PAGE": "EXPLICIT_AVAILABILITY_CONTEXT_PAGE_CANDIDATE",
                "INJURY_MENTION_REVIEW_PAGE": "INJURY_MENTION_PAGE_REVIEW",
            }.get(selection)
            if row["disposition"] != expected_disposition:
                raise RuntimeError(f"source-selection class mismatch: {case['case_id']}")
            excerpt = "\n\n".join(row["matched_contexts"])
            disposition = row["disposition"]
            signal_types = row["availability_signal_types"]
        if not excerpt:
            raise RuntimeError(f"empty source-selection excerpt: {case['case_id']}")
        if (
            row["season"] != case["season"]
            or row["document_label"] != case["document_label"]
            or row["page_number"] != case["page_number"]
        ):
            raise RuntimeError(f"source-selection metadata mismatch: {case['case_id']}")
        if row["historical_publication_time_state"] != "UNKNOWN":
            raise RuntimeError("historical publication time was promoted")
        if row["target_game_outcome_eligibility"] != "EXCLUDED_UNTIL_CHRONOLOGICAL_VALIDATION":
            raise RuntimeError("target-game evidence was admitted")
        if row["canonical_or_pit_admission"]:
            raise RuntimeError("source page gained canonical/PIT authority")
        output_rows.append(
            {
                "case_id": case["case_id"],
                "category": "official_availability_source_selection",
                "source_selection_class": selection,
                "source_disposition": disposition,
                "season": row["season"],
                "document_label": row["document_label"],
                "page_number": row["page_number"],
                "document_page_id": row["document_page_id"],
                "evidence_page_id": row.get("evidence_page_id"),
                "source_url": row["source_url"],
                "source_payload_sha256": row["source_response_sha256"],
                "source_capture_manifest_sha256": row["source_capture_manifest_sha256"],
                "source_page_text_sha256": row["page_text_sha256"],
                "source_locator": f"pdf-page:{row['page_number']}",
                "source_excerpt": excerpt,
                "source_excerpt_sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
                "availability_signal_types": signal_types,
                "historical_publication_time_state": "UNKNOWN",
                "target_game_outcome_eligibility": "EXCLUDED_UNTIL_CHRONOLOGICAL_VALIDATION",
                "team_scope_state": row.get("team_scope_state", "NOT_APPLICABLE_NO_SIGNAL_NEGATIVE"),
                "temporal_scope_state": row.get("temporal_scope_state", "NOT_APPLICABLE_NO_SIGNAL_NEGATIVE"),
                "player_identity_state": row.get("player_identity_state", "NOT_APPLICABLE_NO_SIGNAL_NEGATIVE"),
                "fact_gold_state": "NOT_ADJUDICATED",
                "canonical_or_pit_admission": False,
                "openai_execution_admission": True,
            }
        )

    case_ids = [row["case_id"] for row in output_rows]
    if len(case_ids) != len(set(case_ids)):
        raise RuntimeError("duplicate source-selection case identity")
    jsonl = b"".join(canonical_bytes(row) + b"\n" for row in output_rows)
    manifest_core = {
        "schema_version": 1,
        "artifact_type": "tamu_official_availability_source_selection_sample",
        "sample_id": config["sample_id"],
        "jira_unit": config["jira_unit"],
        "authority": config["authority"],
        "config_sha256": sha256_file(config_path),
        "producer_sha256": sha256_file(Path(__file__).resolve()),
        "source_candidate_identity": source["candidate_identity"],
        "source_candidate_manifest_sha256": source["candidate_manifest_sha256"],
        "source_candidate_validation_report_sha256": source["candidate_validation_report_sha256"],
        "sample_payload_sha256": hashlib.sha256(jsonl).hexdigest(),
        "sample_payload_bytes": len(jsonl),
        "sample_count": len(output_rows),
        "selection_class_counts": dict(sorted(Counter(row["source_selection_class"] for row in output_rows).items())),
        "seasons": sorted({row["season"] for row in output_rows}),
        "case_ids": sorted(case_ids),
        "authority_invariants": config["authority_invariants"],
        "final_disposition": "CANDIDATE_ONLY_OPENAI_SOURCE_TRIAGE_ADMITTED_FACT_GOLD_TIMESTAMP_IDENTITY_CUTOFF_CANONICAL_AND_PIT_USE_NOT_ADMITTED",
    }
    sample_identity = stable_hash(manifest_core)
    output_root = data_root / "openai" / "evals" / "sha256" / sample_identity / "tamu_availability_source_sample"
    payload_path = output_root / "source_selection_sample.jsonl"
    output_manifest_path = output_root / "manifest.json"
    write_immutable(payload_path, jsonl)
    output_manifest = {
        **manifest_core,
        "sample_identity": sample_identity,
        "issued_at_utc": validation["issued_at_utc"],
    }
    manifest_payload = json.dumps(output_manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    write_immutable(output_manifest_path, manifest_payload)
    print(
        json.dumps(
            {
                "sample_identity": sample_identity,
                "payload_path": str(payload_path),
                "payload_sha256": sha256_file(payload_path),
                "manifest_path": str(output_manifest_path),
                "manifest_sha256": sha256_file(output_manifest_path),
                "sample_count": len(output_rows),
                "selection_class_counts": manifest_core["selection_class_counts"],
                "seasons": manifest_core["seasons"],
                "openai_execution_admission": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
