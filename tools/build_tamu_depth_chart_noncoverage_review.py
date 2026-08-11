from __future__ import annotations

"""Build a replayable negative review for official A&M depth-chart page noncoverage."""

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


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0.0"


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


def verified_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"required governed source manifest is absent: {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"governed source manifest hash mismatch: expected={expected_sha256} actual={actual}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_immutable(path: Path, payload: bytes) -> None:
    if path.is_file():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable artifact collision: {path}")
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
    parser.add_argument("--data-root", type=Path, required=True, help="Authoritative external source-data root")
    parser.add_argument("--output-data-root", type=Path, help="Optional isolated replay output root")
    args = parser.parse_args()

    source_root = args.data_root.resolve()
    output_root = (args.output_data_root or args.data_root).resolve()
    config = json.loads((ROOT / "configs" / "openai_depth_chart_noncoverage_review.json").read_text(encoding="utf-8"))
    source = config["source"]
    acquisition_path = source_root / Path(*source["acquisition_manifest_relative_path"].split("/"))
    depth_manifest_path = source_root / Path(*source["depth_page_manifest_relative_path"].split("/"))
    acquisition = verified_json(acquisition_path, source["acquisition_manifest_sha256"])
    depth_manifest = verified_json(depth_manifest_path, source["depth_page_manifest_sha256"])
    if acquisition["acquisition_identity"] != source["acquisition_identity"]:
        raise RuntimeError("official-document acquisition identity mismatch")
    if depth_manifest["dataset_identity"] != source["depth_page_candidate_identity"]:
        raise RuntimeError("depth-page candidate identity mismatch")
    if depth_manifest["acquisition_identity"] != source["acquisition_identity"]:
        raise RuntimeError("depth-page candidate acquisition binding mismatch")

    documents = {row["request_id"]: row for row in acquisition["documents"]}
    target_coverage = [
        row
        for row in depth_manifest["document_coverage"]
        if row["coverage_state"] == "NO_DETERMINISTIC_DEPTH_CHART_PAGE"
    ]
    if len(target_coverage) != int(source["noncovered_documents"]):
        raise RuntimeError("configured depth-chart noncoverage population mismatch")
    season_counts = Counter(str(row["season"]) for row in target_coverage)
    if dict(sorted(season_counts.items())) != source["seasons"]:
        raise RuntimeError("configured depth-chart noncoverage seasons mismatch")

    required_heading = config["deterministic_review"]["required_heading"]
    depth_heading = re.compile(config["deterministic_review"]["forbidden_depth_heading_regex"])
    render_scale = float(config["deterministic_review"]["render_scale"])
    records: list[dict[str, Any]] = []
    image_payloads: dict[str, bytes] = {}
    for coverage in sorted(target_coverage, key=lambda row: (row["season"], row["season_ordinal"])):
        source_document = documents[coverage["source_request_id"]]
        pdf_path = source_root / Path(*source_document["immutable_path"].split("/"))
        if pdf_path.stat().st_size != int(source_document["response_bytes"]):
            raise RuntimeError(f"official PDF byte-size mismatch: {source_document['request_id']}")
        if sha256_file(pdf_path) != source_document["response_sha256"]:
            raise RuntimeError(f"official PDF hash mismatch: {source_document['request_id']}")
        lineup_pages: list[tuple[int, str]] = []
        depth_heading_pages: list[int] = []
        with fitz.open(pdf_path) as document:
            if len(document) != int(coverage["page_count"]):
                raise RuntimeError(f"official PDF page-count mismatch: {source_document['request_id']}")
            for page_index, page in enumerate(document):
                page_number = page_index + 1
                page_text = normalize_page_text(page.get_text("text"))
                if required_heading in page_text.upper():
                    lineup_pages.append((page_number, page_text))
                if depth_heading.search(page_text):
                    depth_heading_pages.append(page_number)
            if len(lineup_pages) != 1:
                raise RuntimeError(
                    f"expected exactly one starting-lineup history page: {source_document['request_id']} got={lineup_pages}"
                )
            if depth_heading_pages:
                raise RuntimeError(
                    f"explicit depth-chart heading contradicts noncoverage: {source_document['request_id']} pages={depth_heading_pages}"
                )
            page_number, page_text = lineup_pages[0]
            pixmap = document[page_number - 1].get_pixmap(
                matrix=fitz.Matrix(render_scale, render_scale),
                alpha=False,
            )
            image_payload = pixmap.tobytes("png")
        image_sha256 = sha256_bytes(image_payload)
        image_name = (
            f"season-{coverage['season']}-ordinal-{int(coverage['season_ordinal']):02d}-"
            f"page-{page_number:02d}-{source_document['response_sha256'][:12]}.png"
        )
        image_payloads[image_name] = image_payload
        records.append(
            {
                "review_record_id": "dcn_" + stable_hash(
                    {
                        "source_response_sha256": source_document["response_sha256"],
                        "page_number": page_number,
                        "page_text_sha256": sha256_bytes(page_text.encode("utf-8")),
                        "rendered_image_sha256": image_sha256,
                    }
                )[:24],
                "season": int(coverage["season"]),
                "season_ordinal": int(coverage["season_ordinal"]),
                "document_label": source_document["label"],
                "source_url": source_document["url"],
                "source_request_id": source_document["request_id"],
                "source_capture_id": source_document["capture_id"],
                "source_response_sha256": source_document["response_sha256"],
                "source_capture_manifest_sha256": source_document["capture_manifest_sha256"],
                "source_pdf_bytes": int(source_document["response_bytes"]),
                "source_pdf_pages": int(coverage["page_count"]),
                "review_page_number": page_number,
                "review_page_locator": f"pdf-page:{page_number}",
                "review_page_text_sha256": sha256_bytes(page_text.encode("utf-8")),
                "rendered_image_name": image_name,
                "rendered_image_sha256": image_sha256,
                "rendered_image_bytes": len(image_payload),
                "rendered_image_width": pixmap.width,
                "rendered_image_height": pixmap.height,
                "required_heading_present": True,
                "explicit_depth_chart_heading_present": False,
                "deterministic_classification": config["deterministic_review"]["expected_classification"],
                "historical_publication_time_state": "UNKNOWN",
                "canonical_or_pit_admission": False,
                "training_or_protected_use_admission": False,
            }
        )

    manifest_core = {
        "schema_version": SCHEMA_VERSION,
        "jira_unit": config["jira_unit"],
        "source_id": source["source_id"],
        "domain": "TAMU_OFFICIAL_DEPTH_CHART_PAGE_NONCOVERAGE_REVIEW",
        "grain": "SOURCE_DOCUMENT_REVIEW_PAGE",
        "acquisition_identity": source["acquisition_identity"],
        "acquisition_manifest_sha256": source["acquisition_manifest_sha256"],
        "depth_page_candidate_identity": source["depth_page_candidate_identity"],
        "depth_page_manifest_sha256": source["depth_page_manifest_sha256"],
        "producer_sha256": sha256_file(Path(__file__).resolve()),
        "pymupdf_version": fitz.VersionBind,
        "review_policy": config["deterministic_review"],
        "documents_reviewed": len(records),
        "season_counts": dict(sorted(Counter(str(row["season"]) for row in records).items())),
        "classification_counts": dict(
            sorted(Counter(row["deterministic_classification"] for row in records).items())
        ),
        "record_hashes": [stable_hash(row) for row in records],
        "records": records,
        "authority": {
            "source_derived_visual_review": True,
            "negative_findings_preserved": True,
            "absence_not_fabricated_into_depth_chart": True,
            "historical_publication_time_known": False,
            "canonical_or_pit_admission": False,
            "training_or_protected_use_admission": False,
            "openai_visual_candidate_qa_eligible": True,
        },
    }
    dataset_identity = stable_hash(manifest_core)
    artifact_root = (
        output_root
        / "quarantine"
        / "historical_known_at"
        / "sha256"
        / dataset_identity
        / "tamu_depth_chart_noncoverage_review"
    )
    for image_name, image_payload in sorted(image_payloads.items()):
        write_immutable(artifact_root / "page_images" / image_name, image_payload)
    rows_payload = b"".join(canonical_bytes(row) + b"\n" for row in records)
    rows_path = artifact_root / "depth_chart_noncoverage_review.jsonl"
    write_immutable(rows_path, rows_payload)
    manifest_path = (
        output_root
        / "manifests"
        / "historical_known_at"
        / "sha256"
        / dataset_identity
        / "tamu_depth_chart_noncoverage_review_manifest.json"
    )
    manifest = {
        **manifest_core,
        "dataset_identity": dataset_identity,
        "issued_at_utc": utc_now(),
        "payload": {
            "path": rows_path.relative_to(output_root).as_posix(),
            "sha256": sha256_bytes(rows_payload),
            "bytes": len(rows_payload),
            "rows": len(records),
        },
        "page_images": {
            "directory": (artifact_root / "page_images").relative_to(output_root).as_posix(),
            "count": len(image_payloads),
            "bytes": sum(len(value) for value in image_payloads.values()),
            "aggregate_identity": stable_hash(
                {name: sha256_bytes(payload) for name, payload in sorted(image_payloads.items())}
            ),
        },
    }
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        comparable = {key: value for key, value in existing.items() if key != "issued_at_utc"}
        expected = {key: value for key, value in manifest.items() if key != "issued_at_utc"}
        if comparable != expected:
            raise RuntimeError(f"immutable review manifest collision: {manifest_path}")
        manifest = existing
    else:
        write_immutable(manifest_path, json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n")

    print(
        json.dumps(
            {
                "dataset_identity": dataset_identity,
                "manifest_path": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "documents_reviewed": len(records),
                "season_counts": manifest_core["season_counts"],
                "classification_counts": manifest_core["classification_counts"],
                "page_images": manifest["page_images"],
                "historical_publication_time_state": "UNKNOWN",
                "canonical_or_pit_admission": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
