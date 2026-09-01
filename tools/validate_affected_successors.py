"""Validate dependency DAG propagation into affected successors."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def validate(repo_root: Path) -> list[str]:
    base = repo_root / "artifacts" / "scientific_integrity" / "all_cycles"
    dag = json.loads((base / "ALL_CYCLE_DEPENDENCY_DAG.json").read_text(encoding="utf-8"))
    successors = json.loads(
        (base / "ALL_CYCLE_AFFECTED_SUCCESSORS.json").read_text(encoding="utf-8")
    )
    findings: list[str] = []
    failed_nodes = {
        str(node["id"])
        for node in dag.get("nodes") or []
        if node.get("disposition") in {"FAIL", "BLOCKED_INSUFFICIENT_EVIDENCE"}
    }
    declared = {
        str(item["successor_id"])
        for item in successors.get("successors") or []
    }
    edges = dag.get("edges") or []
    for edge in edges:
        source = str(edge.get("from"))
        target = str(edge.get("to"))
        if source in failed_nodes and target not in failed_nodes:
            listed = any(
                item.get("successor_id") == target
                and source in (item.get("failed_predecessors") or [])
                for item in successors.get("successors") or []
            )
            if not listed:
                findings.append(
                    f"FAILED_PREDECESSOR_NOT_PROPAGATED:{source}->{target}"
                )
    if dag.get("circular_authority"):
        findings.append("CIRCULAR_AUTHORITY_PRESENT")
    unused = dag.get("orphaned_authority") or []
    if unused:
        findings.append(f"ORPHANED_AUTHORITY:{len(unused)}")
    _ = declared
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    findings = validate(Path(args.repo_root).resolve())
    print(
        json.dumps(
            {
                "validator": "affected_successors",
                "result": "PASS" if not findings else "FAIL",
                "findings": findings,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
