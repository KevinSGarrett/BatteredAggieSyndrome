from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_1998_2009_structured_row_corpus_integrity import (  # noqa: E402  # pylint: disable=import-error
    GATE_RELATIVE,
    AuthorityViolation,
    compute_identity,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (AuthorityViolation, AssertionError, ValueError, FileNotFoundError) as exc:
        return {"name": name, "result": "PASS_FAIL_CLOSED", "exception": type(exc).__name__, "message": str(exc)[:240]}
    raise AssertionError(f"mutation control did not reject: {name}")


def _mutated_gate(gate: dict[str, Any], **changes: Any) -> dict[str, Any]:
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_identity(tampered, "gate_identity")
    return tampered


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate 1998-2009 corpus-integrity successor.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    result = validate_artifact(repo_root=repo_root, data_root=data_root)
    gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8-sig"))

    def _validate(tampered: dict[str, Any]) -> Any:
        return validate_artifact(repo_root=repo_root, data_root=data_root, gate=tampered)

    mutations = [
        expect_rejection("open_protected_lane", lambda: _validate(_mutated_gate(gate, protected_lane="OPEN"))),
        expect_rejection("rewrite_predecessor_identity", lambda: _validate(_mutated_gate(gate, predecessor_gate_identity="0" * 64))),
        expect_rejection("tamper_rejected_domain_proof", lambda: _validate(_mutated_gate(gate, rejected_rows_by_domain={**gate["rejected_rows_by_domain"], "drives": 1}))),
    ]
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
