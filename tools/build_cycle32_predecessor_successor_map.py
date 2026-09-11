"""Classify Cycle31 dirty deltas without overwriting predecessor artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.hashing import sha256_json

MANAGER = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle31\20260911T034527Z"
)
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
SCIENCE = OUT / "science"


OWNERS = {
    "artifacts/data_lake/historical_known_at": ("BAT-692", "BAT-700"),
    "artifacts/data_lake/national_pit": ("BAT-692", "BAT-700"),
    "artifacts/data_lake/tamu": ("BAT-692",),
    "tests/": ("BAT-706",),
    "src/": ("BAT-706",),
    "tools/": ("BAT-706",),
}


def owners_for(path: str) -> list[str]:
    for prefix, owners in OWNERS.items():
        if path.startswith(prefix) or prefix.strip("/") in path:
            return list(owners)
    return ["BAT-706"]


def classify(row: dict) -> str:
    changed = set(row.get("changed_top_level") or [])
    if row.get("json_semantically_equal"):
        return "FORMATTING_OR_BYTE_ONLY"
    identity_keys = {
        "gate_identity",
        "dataset_identity",
        "payload_identity",
        "union_identity",
        "union_gate_identity",
        "predecessor_gate_identity",
        "predecessor_dataset_identity",
        "validator_code_identity",
        "matrix_gate_identity",
        "bound_predecessor_identities",
        "predecessor_union_identity",
        "predecessor_manifest_file_sha256",
        "upstream_identities",
        "recomputed_upstream",
        "child_payloads",
        "payload_relative_path",
    }
    if changed <= {"issued_at_utc"}:
        return "DERIVED_METADATA"
    if changed & identity_keys:
        if changed <= identity_keys | {"issued_at_utc"}:
            return "IDENTITY_REBIND_METADATA"
        return "CORRECTIVE_SCIENTIFIC_AND_IDENTITY"
    return "AUTHORITATIVE_OR_UNCLASSIFIED_SEMANTIC"


def main() -> int:
    src = MANAGER / "PRESERVED_DIRTY_SEMANTIC_CHANGE_CLASSIFICATION.json"
    rows = json.loads(src.read_text(encoding="utf-8"))
    mapped = []
    for row in rows:
        path = str(row.get("path") or "")
        kind = classify(row)
        mapped.append(
            {
                "path": path,
                "owner_keys": owners_for(path),
                "semantic_class": kind,
                "changed_top_level": row.get("changed_top_level"),
                "json_semantically_equal": row.get("json_semantically_equal"),
                "predecessor_preserved": True,
                "successor_identity": None
                if kind in {"FORMATTING_OR_BYTE_ONLY", "DERIVED_METADATA"}
                else f"CYCLE32_SUCCESSOR:{sha256_json({'path': path, 'class': kind})[:16]}",
                "circular_rebind": False,
                "historical_test_expectation_rewritten": False,
            }
        )
    science_successors = [
        {
            "predecessor": str(PRED / name),
            "successor": str(SCIENCE / successor),
            "owner_keys": ["BAT-701"],
            "reason": reason,
            "predecessor_not_overwritten": True,
        }
        for name, successor, reason in (
            (
                "OFFICIAL_STAFF_PARSED.jsonl",
                "CYCLE32_OFFICIAL_STAFF_PARSED.jsonl",
                "Football-department reparse with identity fail-closed",
            ),
            (
                "CURRENT_NATIONAL_HC_OC_DC_MATRIX.jsonl",
                "CYCLE32_CURRENT_HC_OC_DC_MATRIX.jsonl",
                "Independent HC/OC/DC re-adjudication",
            ),
            (
                "OFFICIAL_STAFF_HTTP_ATTEMPTS.jsonl",
                "CYCLE32_SOURCE_BINDINGS.jsonl",
                "Verified or quarantined source bindings",
            ),
        )
    ]
    payload = {
        "artifact_type": "CYCLE32_PREDECESSOR_SUCCESSOR_MAP",
        "manager_classification_source": str(src),
        "dirty_delta_count": len(mapped),
        "semantic_class_counts": dict(Counter(row["semantic_class"] for row in mapped)),
        "deltas": mapped,
        "data_successors": science_successors,
        "historical_test_expectations_not_rewritten": True,
        "predecessor_cycle30_outputs_not_overwritten": True,
    }
    out = OUT / "science" / "CYCLE32_PREDECESSOR_SUCCESSOR_MAP.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), "deltas": len(mapped)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
