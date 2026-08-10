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


PLAY_TYPE_CODES = {
    "Pass Completion": "PASS_COMPLETION",
    "Rush": "RUSH",
    "Punt Return": "PUNT_RETURN",
    "Blocked Field Goal": "BLOCKED_FIELD_GOAL",
    "Interception Return Touchdown": "INTERCEPTION_RETURN_TOUCHDOWN",
}


def main() -> int:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pyarrow is required to prepare the external gamebook pilot corpus") from exc

    config = json.loads((ROOT / "configs" / "openai_gamebook_pilot.json").read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    source = controller.store.root.parent / config["source"]["external_relative_path"]
    source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_sha256 != config["source"]["sha256"]:
        raise SystemExit("gamebook pilot source capture hash mismatch")
    sample_by_id = {int(sample["play_id"]): sample for sample in config["samples"]}
    columns = {"id", "text"}
    for sample in config["samples"]:
        columns.update(fact["column"] for fact in sample["facts"])
    rows = pq.read_table(source, columns=sorted(columns)).to_pylist()
    selected = {int(row["id"]): row for row in rows if int(row["id"]) in sample_by_id}
    if set(selected) != set(sample_by_id):
        raise SystemExit("one or more configured gamebook pilot play IDs are absent")

    gold: list[dict[str, Any]] = []
    for play_id, sample in sample_by_id.items():
        row = selected[play_id]
        excerpt = str(row["text"])
        capture_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        expected = []
        for spec in sample["facts"]:
            value = row[spec["column"]]
            if spec.get("transform") == "PLAY_TYPE_CODE":
                value = PLAY_TYPE_CODES[value]
            expected.append(
                {
                    "field": spec["field"],
                    "value": value,
                    "status": "SUPPORTED",
                    "evidence_locators": ["text:1"],
                }
            )
        gold.append(
            {
                "case_id": f"play-{play_id}",
                "category": sample["category"],
                "source_capture_sha256": capture_sha256,
                "source_excerpt": excerpt,
                "expected_facts": expected,
            }
        )
    payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in gold).encode("utf-8")
    artifact = controller.store.put_bytes("evals", payload, suffix=".gamebook-gold.jsonl")
    manifest = controller.store.put_json(
        "evals",
        {
            "schema_version": 1,
            "artifact_type": "openai_gamebook_pilot_gold",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "source_id": config["source"]["source_id"],
            "source_url": config["source"]["source_url"],
            "source_capture_sha256": source_sha256,
            "source_acquired_at_utc": config["source"]["acquired_at_utc"],
            "gold_sha256": artifact.sha256,
            "gold_bytes": artifact.bytes,
            "sample_count": len(gold),
            "play_ids": sorted(sample_by_id),
            "raw_source_and_excerpts_outside_git": True,
            "final_disposition": "SHADOW_GOLD_ONLY",
        },
    )
    print(json.dumps({"gold_path": str(artifact.path), "gold_sha256": artifact.sha256, "manifest_path": str(manifest.path), "manifest_sha256": manifest.sha256, "samples": len(gold)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
