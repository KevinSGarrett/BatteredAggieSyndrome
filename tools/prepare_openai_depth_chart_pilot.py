from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.openai_assist.controller import AssistiveController  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _transform(value: Any, name: str | None) -> Any:
    if name is None:
        return value
    if name == "INT":
        return int(value)
    raise SystemExit(f"unsupported depth-chart gold transform: {name}")


def _verified_external_file(data_root: Path, relative: str, expected_sha256: str) -> Path:
    path = data_root / relative
    if not path.is_file():
        raise SystemExit(f"configured external depth-chart artifact is absent: {path}")
    actual = _sha(path)
    if actual != expected_sha256:
        raise SystemExit(
            f"external depth-chart artifact hash mismatch: {path} expected={expected_sha256} actual={actual}"
        )
    return path


def _expected_fact(fact: dict[str, Any], excerpt: str, row: dict[str, Any]) -> dict[str, Any]:
    status = fact.get("status", "SUPPORTED")
    if status == "SUPPORTED":
        match = re.search(fact["regex"], excerpt, flags=re.MULTILINE)
        if match is None or match.lastindex != 1:
            raise SystemExit(f"configured fact regex did not yield one group: {fact['field']}")
        return {
            "field": fact["field"],
            "value": _transform(match.group(1), fact.get("transform")),
            "status": status,
            "evidence_locators": ["text:1"],
        }
    if status == "NOT_PRESENT":
        if re.search(fact["forbid_regex"], excerpt, flags=re.MULTILINE):
            raise SystemExit(f"configured NOT_PRESENT fact has contrary page evidence: {fact['field']}")
        return {
            "field": fact["field"],
            "value": None,
            "status": status,
            "evidence_locators": [],
        }
    if status == "UNKNOWN":
        actual = row.get(fact["metadata_field"])
        if actual != fact["metadata_value"]:
            raise SystemExit(
                f"configured UNKNOWN fact metadata mismatch: {fact['field']} expected={fact['metadata_value']} actual={actual}"
            )
        return {
            "field": fact["field"],
            "value": None,
            "status": status,
            "evidence_locators": [],
        }
    raise SystemExit(f"unsupported deterministic gold status: {status}")


def main() -> int:
    config = json.loads((ROOT / "configs" / "openai_depth_chart_pilot.json").read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    data_root = controller.store.root.parent
    source = config["source_candidate"]
    payload_path = _verified_external_file(
        data_root,
        source["external_relative_path"],
        source["candidate_payload_sha256"],
    )
    manifest_path = _verified_external_file(
        data_root,
        source["candidate_manifest_relative_path"],
        source["candidate_manifest_sha256"],
    )
    validation_path = _verified_external_file(
        data_root,
        source["candidate_validation_relative_path"],
        source["candidate_validation_report_sha256"],
    )
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if source_manifest["dataset_identity"] != source["candidate_identity"]:
        raise SystemExit("depth-chart candidate manifest identity mismatch")
    if source_manifest["acquisition_identity"] != source["acquisition_identity"]:
        raise SystemExit("depth-chart acquisition identity mismatch")
    if source_manifest["acquisition_manifest_sha256"] != source["acquisition_manifest_sha256"]:
        raise SystemExit("depth-chart acquisition manifest identity mismatch")
    if source_manifest["payload"]["sha256"] != source["candidate_payload_sha256"]:
        raise SystemExit("depth-chart candidate payload binding mismatch")
    if source_validation.get("status") != "PASS" or source_validation.get("checks_failed") != 0:
        raise SystemExit("depth-chart source candidate has not passed independent validation")
    if not source_validation.get("replay", {}).get("byte_identical_rebuild"):
        raise SystemExit("depth-chart source candidate lacks byte-identical replay evidence")

    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pyarrow is required to prepare the external depth-chart pilot corpus") from exc
    rows = pq.read_table(payload_path).to_pylist()
    if len(rows) != source["candidate_rows"]:
        raise SystemExit("depth-chart candidate row count mismatch")
    by_id = {row["evidence_page_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise SystemExit("duplicate depth-chart evidence-page identity")

    gold: list[dict[str, Any]] = []
    for sample in config["samples"]:
        evidence_page_id = sample["evidence_page_id"]
        if evidence_page_id not in by_id:
            raise SystemExit(f"configured depth-chart evidence page is absent: {evidence_page_id}")
        row = by_id[evidence_page_id]
        if row["season"] != sample["season"] or row["document_label"] != sample["document_label"]:
            raise SystemExit(f"configured depth-chart sample metadata mismatch: {sample['case_id']}")
        excerpt = row["page_text"]
        capture_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        if capture_sha256 != row["page_text_sha256"]:
            raise SystemExit(f"depth-chart page-text identity mismatch: {sample['case_id']}")
        expected = [_expected_fact(fact, excerpt, row) for fact in sample["facts"]]
        fields = [fact["field"] for fact in expected]
        if len(fields) != len(set(fields)):
            raise SystemExit(f"duplicate configured depth-chart field: {sample['case_id']}")
        gold.append(
            {
                "case_id": sample["case_id"],
                "category": "official_depth_chart_document_extraction",
                "domains": ["depth_chart_document", "roster_starter_candidate"],
                "instruction": sample["instruction"],
                "season": sample["season"],
                "document_label": sample["document_label"],
                "position_group": sample["position_group"],
                "evidence_page_id": evidence_page_id,
                "source_url": row["source_url"],
                "source_payload_sha256": row["source_response_sha256"],
                "source_capture_manifest_sha256": row["source_capture_manifest_sha256"],
                "source_capture_sha256": capture_sha256,
                "source_locator": f"pdf-page:{row['page_number']}",
                "source_excerpt": excerpt,
                "historical_publication_time_state": row["historical_publication_time_state"],
                "canonical_or_pit_admission": bool(row["canonical_or_pit_admission"]),
                "expected_facts": expected,
            }
        )

    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        for row in gold
    ).encode("utf-8")
    artifact = controller.store.put_bytes("evals", payload, suffix=".tamu-depth-chart-gold.jsonl")
    manifest = controller.store.put_json(
        "evals",
        {
            "schema_version": 1,
            "artifact_type": "openai_tamu_official_depth_chart_document_gold",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "source_candidate_identity": source["candidate_identity"],
            "source_candidate_manifest_sha256": source["candidate_manifest_sha256"],
            "source_candidate_validation_report_sha256": source["candidate_validation_report_sha256"],
            "gold_sha256": artifact.sha256,
            "gold_bytes": artifact.bytes,
            "sample_count": len(gold),
            "case_ids": sorted(row["case_id"] for row in gold),
            "seasons": sorted({row["season"] for row in gold}),
            "models": [route["model"] for route in config["routes"]],
            "reasoning_efforts": {route["model"]: route["reasoning_effort"] for route in config["routes"]},
            "historical_publication_time_state": "UNKNOWN",
            "canonical_or_pit_admission": False,
            "raw_source_and_excerpts_outside_git": True,
            "final_disposition": "SHADOW_GOLD_READY_PROVIDER_CREDENTIAL_REQUIRED_FOR_COMPARISON",
        },
    )
    print(
        json.dumps(
            {
                "gold_path": str(artifact.path),
                "gold_sha256": artifact.sha256,
                "manifest_path": str(manifest.path),
                "manifest_sha256": manifest.sha256,
                "samples": len(gold),
                "seasons": sorted({row["season"] for row in gold}),
                "planned_jobs": len(gold) * len(config["routes"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
