from __future__ import annotations

"""Validate and replay the official A&M depth-chart noncoverage review."""

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def review_manifest_path(data_root: Path, identity: str) -> Path:
    return (
        data_root
        / "manifests"
        / "historical_known_at"
        / "sha256"
        / identity
        / "tamu_depth_chart_noncoverage_review_manifest.json"
    )


def contract_errors(config: dict[str, Any], manifest: dict[str, Any], data_root: Path) -> list[str]:
    errors: list[str] = []
    expected = config["deterministic_result"]
    source = config["source"]
    if manifest.get("dataset_identity") != expected["dataset_identity"]:
        errors.append("dataset identity mismatch")
    if manifest.get("acquisition_identity") != source["acquisition_identity"]:
        errors.append("acquisition identity mismatch")
    if manifest.get("acquisition_manifest_sha256") != source["acquisition_manifest_sha256"]:
        errors.append("acquisition manifest binding mismatch")
    if manifest.get("depth_page_candidate_identity") != source["depth_page_candidate_identity"]:
        errors.append("depth-page candidate identity mismatch")
    if manifest.get("depth_page_manifest_sha256") != source["depth_page_manifest_sha256"]:
        errors.append("depth-page manifest binding mismatch")
    if manifest.get("documents_reviewed") != source["noncovered_documents"]:
        errors.append("reviewed document count mismatch")
    if manifest.get("season_counts") != source["seasons"]:
        errors.append("season counts mismatch")
    expected_classification = config["deterministic_review"]["expected_classification"]
    if manifest.get("classification_counts") != {expected_classification: 25}:
        errors.append("classification counts mismatch")
    records = manifest.get("records") or []
    if len(records) != 25 or len({row.get("review_record_id") for row in records}) != 25:
        errors.append("review record population or identity mismatch")
    for index, row in enumerate(records):
        if row.get("deterministic_classification") != expected_classification:
            errors.append(f"record {index} classification mismatch")
        if row.get("required_heading_present") is not True:
            errors.append(f"record {index} lacks the required starting-lineup heading")
        if row.get("explicit_depth_chart_heading_present") is not False:
            errors.append(f"record {index} improperly asserts a depth-chart heading")
        if row.get("historical_publication_time_state") != "UNKNOWN":
            errors.append(f"record {index} fabricates historical publication time")
        if row.get("canonical_or_pit_admission") is not False:
            errors.append(f"record {index} improperly admits canonical or PIT state")
        image_path = (
            data_root
            / manifest["page_images"]["directory"]
            / row["rendered_image_name"]
        )
        if not image_path.is_file() or sha256_file(image_path) != row.get("rendered_image_sha256"):
            errors.append(f"record {index} rendered image hash mismatch")
        elif image_path.stat().st_size != row.get("rendered_image_bytes"):
            errors.append(f"record {index} rendered image byte-size mismatch")
    payload = manifest.get("payload") or {}
    payload_path = data_root / str(payload.get("path", ""))
    if payload.get("sha256") != expected["payload_sha256"]:
        errors.append("review manifest payload binding mismatch")
    if not payload_path.is_file() or sha256_file(payload_path) != expected["payload_sha256"]:
        errors.append("review payload hash mismatch")
    if payload.get("rows") != expected["payload_rows"]:
        errors.append("review payload row count mismatch")
    images = manifest.get("page_images") or {}
    if images.get("count") != expected["page_image_count"]:
        errors.append("page image count mismatch")
    if images.get("aggregate_identity") != expected["page_image_aggregate_identity"]:
        errors.append("page image aggregate identity mismatch")
    authority = manifest.get("authority") or {}
    required_authority = {
        "source_derived_visual_review": True,
        "negative_findings_preserved": True,
        "absence_not_fabricated_into_depth_chart": True,
        "historical_publication_time_known": False,
        "canonical_or_pit_admission": False,
        "training_or_protected_use_admission": False,
        "openai_visual_candidate_qa_eligible": True,
    }
    if authority != required_authority:
        errors.append("authority boundary mismatch")
    return errors


def mutation_checks(config: dict[str, Any], manifest: dict[str, Any], data_root: Path) -> dict[str, bool]:
    checks: dict[str, bool] = {}

    def rejected(name: str, mutate) -> None:
        candidate = copy.deepcopy(manifest)
        mutate(candidate)
        checks[name] = bool(contract_errors(config, candidate, data_root))

    rejected("identity", lambda value: value.__setitem__("dataset_identity", "0" * 64))
    rejected("document_count", lambda value: value.__setitem__("documents_reviewed", 24))
    rejected("classification", lambda value: value["records"][0].__setitem__("deterministic_classification", "DEPTH_CHART"))
    rejected("depth_heading", lambda value: value["records"][0].__setitem__("explicit_depth_chart_heading_present", True))
    rejected("historical_timestamp", lambda value: value["records"][0].__setitem__("historical_publication_time_state", "KNOWN"))
    rejected("pit_admission", lambda value: value["records"][0].__setitem__("canonical_or_pit_admission", True))
    rejected("payload_hash", lambda value: value["payload"].__setitem__("sha256", "0" * 64))
    rejected("image_hash", lambda value: value["records"][0].__setitem__("rendered_image_sha256", "0" * 64))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    config = json.loads((ROOT / "configs" / "openai_depth_chart_noncoverage_review.json").read_text(encoding="utf-8"))
    expected = config["deterministic_result"]
    manifest_path = review_manifest_path(data_root, expected["dataset_identity"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = contract_errors(config, manifest, data_root)
    if sha256_file(manifest_path) != expected["manifest_sha256"]:
        errors.append("review manifest hash mismatch")
    mutations = mutation_checks(config, manifest, data_root)
    if not all(mutations.values()):
        errors.append("one or more mutation controls failed open")

    # Keep the replay root short enough for Windows path-length limits while remaining under the external data root.
    runtime_root = data_root / "r"
    runtime_root.mkdir(parents=True, exist_ok=True)
    replay: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="r-", dir=runtime_root) as raw:
        replay_root = Path(raw)
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "build_tamu_depth_chart_noncoverage_review.py"),
                "--data-root",
                str(data_root),
                "--output-data-root",
                str(replay_root),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        replay_summary = json.loads(completed.stdout)
        replay_manifest_path = Path(replay_summary["manifest_path"])
        replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
        replay = {
            "dataset_identity": replay_summary["dataset_identity"],
            "payload_sha256": replay_manifest["payload"]["sha256"],
            "page_image_aggregate_identity": replay_manifest["page_images"]["aggregate_identity"],
            "byte_identical_payload": replay_manifest["payload"]["sha256"] == manifest["payload"]["sha256"],
            "byte_identical_page_images": (
                replay_manifest["page_images"]["aggregate_identity"]
                == manifest["page_images"]["aggregate_identity"]
            ),
        }
        if replay_summary["dataset_identity"] != expected["dataset_identity"]:
            errors.append("replay dataset identity mismatch")
        if not replay["byte_identical_payload"] or not replay["byte_identical_page_images"]:
            errors.append("replay payload or rendered images are not byte-identical")

    report = {
        "schema_version": "1.0.0",
        "validation_id": "val_" + hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()[:24],
        "jira_unit": config["jira_unit"],
        "dataset_identity": expected["dataset_identity"],
        "candidate_manifest_path": str(manifest_path),
        "candidate_manifest_sha256": sha256_file(manifest_path),
        "documents_reviewed": manifest["documents_reviewed"],
        "season_counts": manifest["season_counts"],
        "classification_counts": manifest["classification_counts"],
        "mutation_controls": mutations,
        "mutation_controls_passed": sum(mutations.values()),
        "replay": replay,
        "authority": manifest["authority"],
        "checks_failed": len(errors),
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({**report, "output": str(output), "output_sha256": sha256_file(output)}, indent=2, sort_keys=True))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
