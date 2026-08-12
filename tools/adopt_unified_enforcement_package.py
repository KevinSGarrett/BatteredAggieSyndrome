from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_ROOT = Path(
    r"C:\Users\kevin\.codex\visualizations\2026\08\12\019ff7b7-089f-7271-be5f-caa2caa4424f"
    r"\unified-assistive-execution-enforcement"
)

FILES = {
    "MAIN_SESSION_START_HERE.md": {
        "sha256": "d1576960f748072350b98925eb4f879a8a4d44237b285f2896e69da44d3403e3",
        "bytes": 10_792,
        "lines": 149,
    },
    "UNIFIED_ASSISTIVE_EXECUTION_ENFORCEMENT_MASTER_DIRECTIVE.md": {
        "sha256": "7e7d927a3e3a3efd43705a4f2dc64ff9e593cde5085fb271a6276bd8194a1813",
        "bytes": 85_031,
        "lines": 1_717,
    },
    "OPERATIONAL_ACCEPTANCE_AND_UTILIZATION_MATRIX.md": {
        "sha256": "bd0142e8df4f25bd0b8733221c232cd3009786aad4f393a71154c9f2ade61111",
        "bytes": 34_916,
        "lines": 369,
    },
    "SECOND_PASS_ASSURANCE_REPORT.md": {
        "sha256": "935e023ffb73f4d2f44bb4b744d57444af2fe41d80ee31d0c915e1627ac28826",
        "bytes": 9_875,
        "lines": 112,
    },
    "PACKAGE_MANIFEST.json": {
        "sha256": "9e9e35032c69029b100c85fa15d53beb66cbbee0a6b36641758d97e43588a243",
        "bytes": 1_586,
        "lines": 38,
    },
}

EXPECTED_FAMILIES = {
    "BUD": 8,
    "CPU": 18,
    "CTL": 22,
    "CUR": 16,
    "INV": 13,
    "JIR": 18,
    "LOC": 22,
    "OAI": 12,
    "OPS": 13,
    "OR": 12,
    "REV": 10,
    "SCH": 13,
    "SOAK": 15,
    "UTL": 12,
}

OWNERS = {
    "CTL": ("POST-SUBTASK-201", "BAT-560", "controller, database, state machine, supervision, backup, and watchdog"),
    "INV": ("POST-SUBTASK-201", "BAT-560", "live inventory and exact route readiness"),
    "SCH": ("POST-SUBTASK-201", "BAT-560", "scheduler, leases, retries, and recovery"),
    "BUD": ("POST-SUBTASK-201", "BAT-560", "provider budget and local resource admission"),
    "OPS": ("POST-SUBTASK-201", "BAT-560", "operational security, deployment, and rollback"),
    "CUR": ("POST-SUBTASK-202", "BAT-561", "Cursor safety pilots and real-work campaign"),
    "OR": ("POST-SUBTASK-200", "BAT-558", "OpenRouter staged qualification and real-work campaign"),
    "OAI": ("POST-SUBTASK-168", "BAT-525", "direct OpenAI controller integration and continuing campaign"),
    "LOC": ("POST-SUBTASK-203", "BAT-562", "local-model route qualification and campaign"),
    "CPU": ("POST-SUBTASK-204", "BAT-563", "corrected private CPU-worker deployment and campaign"),
    "REV": ("POST-SUBTASK-205", "BAT-564", "review capacity, dispositions, and accepted-value evidence"),
    "UTL": ("POST-SUBTASK-205", "BAT-564", "weighted utilization and measured savings"),
    "SOAK": ("POST-SUBTASK-205", "BAT-564", "seven-day sustained-operation gate"),
    "JIR": ("POST-STORY-058", "BAT-559", "canonical/live Jira ownership and continuing synchronization"),
}

ROW_RE = re.compile(r"^(?P<family>[A-Z]+)-(?P<number>\d{3})$")


def file_identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "lines": len(data.decode("utf-8").splitlines()),
    }


def canonical_record(local_id: str) -> tuple[Path, dict[str, Any]]:
    matches = list((ROOT / "jira/records/issues").rglob(f"{local_id}_*.json"))
    if len(matches) != 1:
        raise RuntimeError(f"CANONICAL_OWNER_NOT_UNIQUE:{local_id}:{len(matches)}")
    return matches[0], json.loads(matches[0].read_text(encoding="utf-8"))


def parse_matrix(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.startswith("|"):
            continue
        fields = [field.strip() for field in raw_line.strip().strip("|").split("|")]
        if len(fields) != 5:
            continue
        match = ROW_RE.fullmatch(fields[0])
        if not match:
            continue
        row_id = fields[0]
        if row_id in seen:
            raise RuntimeError(f"DUPLICATE_ACCEPTANCE_ROW:{row_id}")
        family = match.group("family")
        if family not in OWNERS:
            raise RuntimeError(f"UNOWNED_ACCEPTANCE_FAMILY:{family}")
        local_id, jira_key, scope = OWNERS[family]
        rows.append(
            {
                "id": row_id,
                "family": family,
                "mandatory": True,
                "requirement": fields[1],
                "exact_acceptance_condition": fields[2],
                "required_evidence": fields[3],
                "automatic_failure_examples": fields[4],
                "primary_local_id": local_id,
                "primary_jira_key": jira_key,
                "owner_scope": scope,
            }
        )
        seen.add(row_id)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, default=DEFAULT_PACKAGE_ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "configs/unified_assistive_acceptance_ownership.json",
    )
    args = parser.parse_args()

    identities: dict[str, dict[str, Any]] = {}
    for name, expected in FILES.items():
        path = args.package_root / name
        if not path.is_file():
            raise RuntimeError(f"GOVERNING_PACKAGE_FILE_MISSING:{name}")
        observed = file_identity(path)
        if observed != expected:
            raise RuntimeError(f"GOVERNING_PACKAGE_IDENTITY_MISMATCH:{name}:{observed}")
        identities[name] = observed

    rows = parse_matrix(args.package_root / "OPERATIONAL_ACCEPTANCE_AND_UTILIZATION_MATRIX.md")
    family_counts = Counter(row["family"] for row in rows)
    if len(rows) != 204 or dict(sorted(family_counts.items())) != EXPECTED_FAMILIES:
        raise RuntimeError(f"ACCEPTANCE_ROW_POPULATION_MISMATCH:{len(rows)}:{dict(family_counts)}")

    owner_records: dict[str, dict[str, Any]] = {}
    for local_id, jira_key, scope in sorted(set(OWNERS.values())):
        path, record = canonical_record(local_id)
        if record.get("jira_key") != jira_key:
            raise RuntimeError(f"LIVE_JIRA_OWNER_MISMATCH:{local_id}:{record.get('jira_key')}:{jira_key}")
        owner_records[local_id] = {
            "jira_key": jira_key,
            "objective": record.get("objective"),
            "workflow_state": record.get("workflow_state"),
            "evidence_state": record.get("evidence_state"),
            "canonical_record": path.relative_to(ROOT).as_posix(),
            "canonical_record_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "owner_scope": scope,
        }

    payload = {
        "schema_version": 1,
        "registry_id": "unified-assistive-acceptance-ownership-v1",
        "package_identities": identities,
        "mandatory_row_count": len(rows),
        "family_counts": dict(sorted(family_counts.items())),
        "allowed_results": ["PASS", "FAIL", "BLOCKED", "INCOMPLETE"],
        "exit_zero_only_for": "PASS",
        "owner_records": owner_records,
        "rows": rows,
        "scientific_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(json.dumps({"status": "PASS", "path": str(args.output), "sha256": digest, "rows": len(rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
