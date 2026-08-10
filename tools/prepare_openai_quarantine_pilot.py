from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.openai_assist.controller import AssistiveController  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line(path: Path, line_number: int) -> str:
    with path.open("r", encoding="utf-8") as handle:
        for index, value in enumerate(handle, 1):
            if index == line_number:
                return value.rstrip("\r\n")
    raise RuntimeError(f"missing configured line {line_number}: {path}")


def _facts(case: dict[str, Any], capture_sha256: str) -> list[dict[str, Any]]:
    evidence = [{"source_capture_sha256": capture_sha256, "locator": "line:1", "excerpt_sha256": capture_sha256}]
    return [
        {"field": "classification_code", "value": case["classification_code"], "status": "SUPPORTED", "evidence_locators": ["line:1"], "expected_evidence": evidence},
        {"field": "risk_tier", "value": case["risk_tier"], "status": "SUPPORTED", "evidence_locators": ["line:1"], "expected_evidence": evidence},
        {"field": "remediation_route", "value": case["remediation_route"], "status": "SUPPORTED", "evidence_locators": ["line:1"], "expected_evidence": evidence},
        {"field": "canonical_authority", "value": "NONE", "status": "SUPPORTED", "evidence_locators": ["line:1"], "expected_evidence": evidence},
    ]


def main() -> int:
    config = json.loads((ROOT / "configs" / "openai_quarantine_schema_pilot.json").read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    source_root = controller.store.root.parent
    excerpts: dict[str, tuple[str, str]] = {}
    verified_sources: dict[str, dict[str, Any]] = {}
    for name, spec in config["external_sources"].items():
        path = (source_root / spec["relative_path"]).resolve(strict=True)
        path.relative_to(source_root)
        actual_sha256 = _sha256(path)
        if actual_sha256 != spec["sha256"]:
            raise SystemExit(f"external quarantine source hash mismatch: {name}")
        excerpt = _line(path, int(spec["line_number"]))
        excerpts[f"external:{name}"] = (excerpt, path.as_uri())
        verified_sources[name] = {"path": str(path), "sha256": actual_sha256, "bytes": path.stat().st_size, "line_number": spec["line_number"]}
    for name, excerpt in config["synthetic_adversarial_cases"].items():
        excerpts[f"synthetic:{name}"] = (excerpt, f"file:synthetic/openai_quarantine_schema_pilot#{name}")

    gold: list[dict[str, Any]] = []
    for case in config["cases"]:
        excerpt, source_url = excerpts[case["source"]]
        capture_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        gold.append(
            {
                "case_id": case["case_id"],
                "category": case["classification_code"],
                "source_kind": case["source"].split(":", 1)[0].upper(),
                "source_url": source_url,
                "source_capture_sha256": capture_sha256,
                "source_excerpt": excerpt,
                "expected_facts": _facts(case, capture_sha256),
                "entity_merge_expected": False,
            }
        )
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in gold).encode("utf-8")
    gold_artifact = controller.store.put_bytes("evals", payload, suffix=".quarantine-schema-gold.jsonl")
    manifest = controller.store.put_json(
        "evals",
        {
            "schema_version": 1,
            "artifact_type": "openai_quarantine_schema_gold",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "case_count": len(gold),
            "real_case_count": sum(row["source_kind"] == "EXTERNAL" for row in gold),
            "synthetic_adversarial_case_count": sum(row["source_kind"] == "SYNTHETIC" for row in gold),
            "categories": [row["category"] for row in gold],
            "verified_sources": verified_sources,
            "gold_sha256": gold_artifact.sha256,
            "gold_bytes": gold_artifact.bytes,
            "canonical_writes": 0,
            "protected_truth_writes": 0,
        },
    )
    print(json.dumps({"gold_path": str(gold_artifact.path), "gold_sha256": gold_artifact.sha256, "manifest_path": str(manifest.path), "manifest_sha256": manifest.sha256, "case_count": len(gold)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
