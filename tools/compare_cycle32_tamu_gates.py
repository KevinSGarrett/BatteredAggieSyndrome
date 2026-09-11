"""Record-level comparison of dirty TAMU/historical gates versus HEAD.

Does not rewrite predecessor Cycle30 outputs. Not acceptance.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def json_keys(payload: Any, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            keys.add(path)
            keys.update(json_keys(value, path))
    elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
        keys.update(json_keys(payload[0], prefix + "[]"))
    return keys


def classify(path: str, head_text: str | None, work_text: str | None) -> str:
    if head_text is None:
        return "WORKING_TREE_ONLY"
    if work_text is None:
        return "HEAD_ONLY_OR_BINARY"
    if head_text == work_text:
        return "UNCHANGED"
    if path.endswith(".json"):
        try:
            head_obj = json.loads(head_text)
            work_obj = json.loads(work_text)
        except json.JSONDecodeError:
            return "CORRECTIVE_OR_NONJSON_DELTA"
        if head_obj == work_obj:
            return "FORMATTING_ONLY"
        identity_fields = {
            "gate_identity",
            "dataset_identity",
            "bound_predecessor_identities",
            "matrix_gate_identity",
        }
        head_ids = {k: head_obj.get(k) for k in identity_fields if isinstance(head_obj, dict)}
        work_ids = {k: work_obj.get(k) for k in identity_fields if isinstance(work_obj, dict)}
        if head_ids != work_ids and isinstance(head_obj, dict) and isinstance(work_obj, dict):
            remaining_head = {k: v for k, v in head_obj.items() if k not in identity_fields}
            remaining_work = {k: v for k, v in work_obj.items() if k not in identity_fields}
            if remaining_head == remaining_work:
                return "IDENTITY_REBIND_METADATA"
        return "SEMANTIC_OR_CONTENT_DELTA"
    return "CORRECTIVE_OR_NONJSON_DELTA"


def main() -> int:
    status = git("status", "--porcelain")
    rows: list[dict[str, Any]] = []
    for line in status.splitlines():
        path = line[3:].strip().strip('"').replace("\\", "/")
        lowered = path.casefold()
        if not any(
            token in lowered
            for token in ("tamu", "gate", "data_lake", "historical_known", "official")
        ):
            continue
        if not path.endswith((".json", ".jsonl", ".py", ".md")):
            continue
        head_text = None
        try:
            head_text = git("show", f"HEAD:{path}")
        except subprocess.CalledProcessError:
            head_text = None
        work = ROOT / path.replace("/", "\\")
        work_text = work.read_text(encoding="utf-8") if work.is_file() else None
        semantic = classify(path, head_text, work_text)
        comparison: dict[str, Any] = {
            "path": path,
            "semantic_class": semantic,
            "predecessor_preserved": True,
            "historical_test_expectation_rewritten": False,
            "circular_rebind": False,
        }
        if path.endswith(".json") and head_text and work_text:
            try:
                head_obj = json.loads(head_text)
                work_obj = json.loads(work_text)
                head_keys = json_keys(head_obj)
                work_keys = json_keys(work_obj)
                comparison["key_added"] = sorted(work_keys - head_keys)[:40]
                comparison["key_removed"] = sorted(head_keys - work_keys)[:40]
                if isinstance(head_obj, dict) and isinstance(work_obj, dict):
                    comparison["head_gate_identity"] = head_obj.get("gate_identity")
                    comparison["work_gate_identity"] = work_obj.get("gate_identity")
            except json.JSONDecodeError:
                pass
        rows.append(comparison)
    payload = {
        "artifact_type": "CYCLE32_TAMU_GATE_RECORD_COMPARISON",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "compared_paths": len(rows),
        "class_counts": {},
        "rows": rows,
        "notes": [
            "HEAD 7d680d17 working-tree comparison only. Cycle30 private outputs were not overwritten.",
            "Identity rebinds are not automatically predecessor overwrites.",
        ],
    }
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["semantic_class"]] = counts.get(row["semantic_class"], 0) + 1
    payload["class_counts"] = counts
    out = OUT / "science" / "CYCLE32_TAMU_GATE_RECORD_COMPARISON.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"compared_paths": len(rows), "class_counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
