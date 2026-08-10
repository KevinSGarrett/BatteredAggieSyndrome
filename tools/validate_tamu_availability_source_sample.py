from __future__ import annotations

"""Independently validate the bounded official A&M availability source sample."""

import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pyarrow.parquet as pq


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_prefix(value: str, maximum: int) -> str:
    return re.sub(r"\s+", " ", value).strip()[:maximum]


def bound_path(root: Path, relative: str, expected_sha256: str) -> Path:
    path = root / Path(*relative.split("/"))
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise AssertionError(f"bound source artifact failure: {path}")
    return path


def validate_contract(
    *,
    root: Path,
    config: dict[str, Any],
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    config_sha256: str,
    producer_sha256: str,
) -> None:
    core = {key: value for key, value in manifest.items() if key not in {"sample_identity", "issued_at_utc"}}
    if stable_hash(core) != manifest["sample_identity"]:
        raise AssertionError("sample identity mismatch")
    if manifest["config_sha256"] != config_sha256 or manifest["producer_sha256"] != producer_sha256:
        raise AssertionError("config/producer binding mismatch")
    if manifest["jira_unit"] != "POST-SUBTASK-168" or manifest["authority"] != config["authority"]:
        raise AssertionError("continuing-operations authority mismatch")
    if manifest["source_candidate_identity"] != config["source_candidate"]["candidate_identity"]:
        raise AssertionError("source candidate identity mismatch")
    if len(rows) != len(config["cases"]) or len(rows) != manifest["sample_count"]:
        raise AssertionError("sample count mismatch")
    if [row["case_id"] for row in rows] != [case["case_id"] for case in config["cases"]]:
        raise AssertionError("case identity/order mismatch")
    payload = b"".join(canonical_bytes(row) + b"\n" for row in rows)
    if hashlib.sha256(payload).hexdigest() != manifest["sample_payload_sha256"]:
        raise AssertionError("sample payload hash mismatch")
    if len(payload) != manifest["sample_payload_bytes"]:
        raise AssertionError("sample payload byte count mismatch")
    if Counter(row["source_selection_class"] for row in rows) != Counter(manifest["selection_class_counts"]):
        raise AssertionError("selection class count mismatch")
    if sorted({row["season"] for row in rows}) != manifest["seasons"]:
        raise AssertionError("season coverage mismatch")
    if not manifest["authority_invariants"]["openai_execution_admitted"]:
        raise AssertionError("candidate-only OpenAI execution was not admitted")
    required_false = (
        "fact_gold_adjudicated",
        "player_status_fact_extracted",
        "team_scope_resolved",
        "temporal_scope_resolved",
        "player_identity_resolved",
        "historical_publication_time_known",
        "target_game_cutoff_eligible",
        "canonical_or_pit_admission",
        "training_or_protected_use_admission",
    )
    if any(manifest["authority_invariants"][name] for name in required_false):
        raise AssertionError("protected authority was promoted")

    source = config["source_candidate"]
    pages_path = bound_path(root, source["page_payload_relative_path"], source["page_payload_sha256"])
    evidence_path = bound_path(root, source["evidence_payload_relative_path"], source["evidence_payload_sha256"])
    pages = {row["document_page_id"]: row for row in pq.read_table(pages_path).to_pylist()}
    evidence = {row["evidence_page_id"]: row for row in pq.read_table(evidence_path).to_pylist()}
    for case, row in zip(config["cases"], rows):
        if row["source_selection_class"] != case["expected_selection_class"]:
            raise AssertionError(f"selection mismatch: {case['case_id']}")
        source_row = pages[row["document_page_id"]]
        if row["evidence_page_id"] is None:
            excerpt = normalized_prefix(source_row["page_text"], int(config["excerpt_policy"]["negative_max_characters"]))
        else:
            evidence_row = evidence[row["evidence_page_id"]]
            if evidence_row["document_page_id"] != row["document_page_id"]:
                raise AssertionError("evidence/source-page identity mismatch")
            excerpt = "\n\n".join(evidence_row["matched_contexts"])
        if row["source_excerpt"] != excerpt or row["source_excerpt_sha256"] != hashlib.sha256(excerpt.encode("utf-8")).hexdigest():
            raise AssertionError(f"source excerpt mismatch: {case['case_id']}")
        for name in ("season", "document_label", "page_number"):
            if row[name] != case[name]:
                raise AssertionError(f"case metadata mismatch: {case['case_id']}:{name}")
        if row["source_payload_sha256"] != source_row["source_response_sha256"]:
            raise AssertionError("source payload binding mismatch")
        if row["source_page_text_sha256"] != source_row["page_text_sha256"]:
            raise AssertionError("source page binding mismatch")
        if row["historical_publication_time_state"] != "UNKNOWN":
            raise AssertionError("historical publication time was fabricated")
        if row["target_game_outcome_eligibility"] != "EXCLUDED_UNTIL_CHRONOLOGICAL_VALIDATION":
            raise AssertionError("target-game evidence was admitted")
        if row["fact_gold_state"] != "NOT_ADJUDICATED" or row["canonical_or_pit_admission"]:
            raise AssertionError("factual/canonical authority was promoted")
        if not row["openai_execution_admission"]:
            raise AssertionError("candidate-only execution admission missing")


def expect_failure(
    validator: Callable[[dict[str, Any], list[dict[str, Any]]], None],
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    mutation: Callable[[dict[str, Any], list[dict[str, Any]]], None],
) -> bool:
    changed_manifest = copy.deepcopy(manifest)
    changed_rows = copy.deepcopy(rows)
    mutation(changed_manifest, changed_rows)
    try:
        validator(changed_manifest, changed_rows)
    except (AssertionError, KeyError, ValueError):
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.data_root.resolve()
    config_path = args.config.resolve()
    producer_path = args.producer.resolve()
    manifest_path = args.manifest.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload_path = manifest_path.parent / "source_selection_sample.jsonl"
    if sha256_file(payload_path) != manifest["sample_payload_sha256"]:
        raise AssertionError("manifest/payload file hash mismatch")
    rows = [json.loads(line) for line in payload_path.read_text(encoding="utf-8").splitlines() if line]

    def validate(changed_manifest: dict[str, Any], changed_rows: list[dict[str, Any]]) -> None:
        validate_contract(
            root=root,
            config=config,
            manifest=changed_manifest,
            rows=changed_rows,
            config_sha256=sha256_file(config_path),
            producer_sha256=sha256_file(producer_path),
        )

    validate(manifest, rows)
    mutations: dict[str, Callable[[dict[str, Any], list[dict[str, Any]]], None]] = {
        "identity": lambda m, r: m.__setitem__("sample_identity", "0" * 64),
        "payload_hash": lambda m, r: m.__setitem__("sample_payload_sha256", "0" * 64),
        "case_order": lambda m, r: r.reverse(),
        "excerpt": lambda m, r: r[0].__setitem__("source_excerpt", "unsupported"),
        "timestamp_fabrication": lambda m, r: r[0].__setitem__("historical_publication_time_state", "KNOWN"),
        "target_admission": lambda m, r: r[0].__setitem__("target_game_outcome_eligibility", "ELIGIBLE"),
        "canonical_admission": lambda m, r: r[0].__setitem__("canonical_or_pit_admission", True),
        "execution_removal": lambda m, r: r[0].__setitem__("openai_execution_admission", False),
    }
    mutation_results = {
        name: expect_failure(validate, manifest, rows, mutation)
        for name, mutation in mutations.items()
    }
    if not all(mutation_results.values()):
        raise AssertionError(f"mutation control failure: {mutation_results}")
    report = {
        "schema_version": "1.0.0",
        "status": "PASS",
        "issued_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "sample_identity": manifest["sample_identity"],
        "sample_manifest_path": str(manifest_path),
        "sample_manifest_sha256": sha256_file(manifest_path),
        "sample_payload_sha256": sha256_file(payload_path),
        "sample_count": len(rows),
        "selection_class_counts": dict(sorted(Counter(row["source_selection_class"] for row in rows).items())),
        "seasons": sorted({row["season"] for row in rows}),
        "checks_passed": 18,
        "checks_failed": 0,
        "mutation_controls": mutation_results,
        "authority_invariants": manifest["authority_invariants"],
        "final_disposition": "VALIDATED_CANDIDATE_ONLY_OPENAI_SOURCE_TRIAGE_SAMPLE",
    }
    report["validation_id"] = "val_" + stable_hash(report)[:24]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({**report, "report_sha256": sha256_file(args.output)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
