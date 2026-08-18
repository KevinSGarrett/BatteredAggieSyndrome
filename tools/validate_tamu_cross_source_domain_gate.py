from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_cross_source_domain_gate import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    compute_gate_identity,
    rebuild_expected,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, AuthorityViolation, FileNotFoundError, AssertionError) as exc:
        return {
            "name": name,
            "result": "PASS_FAIL_CLOSED",
            "exception": type(exc).__name__,
            "message": str(exc)[:240],
        }
    raise AssertionError(f"mutation control did not reject: {name}")


def _mutated_gate(gate: dict[str, Any], **changes: Any) -> dict[str, Any]:
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently validate the 2010-2011 Texas A&M cross-source domain gate."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    result = validate_artifact(data_root=data_root, repo_root=repo_root, require_rebuild=True)
    mutations: list[dict[str, Any]] = []
    if not args.validate_only:
        expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
        gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8"))

        def _validate(tampered_gate: dict[str, Any]) -> Any:
            return validate_artifact(
                data_root=data_root,
                repo_root=repo_root,
                require_rebuild=True,
                gate=tampered_gate,
                expected=expected,
            )

        identities = json.loads(json.dumps(gate["input_identities"]))
        identities.pop("phase3_matrix_identity", None)
        mutations.append(
            expect_rejection("missing_phase3_bind", lambda: _validate(_mutated_gate(gate, input_identities=identities)))
        )
        identities = json.loads(json.dumps(gate["input_identities"]))
        identities.pop("phase4_acquisition_identity", None)
        mutations.append(
            expect_rejection("missing_phase4_bind", lambda: _validate(_mutated_gate(gate, input_identities=identities)))
        )
        counts = json.loads(json.dumps(gate["counts"]))
        counts["verified_official"] = 26
        mutations.append(
            expect_rejection("forged_verified_official", lambda: _validate(_mutated_gate(gate, counts=counts)))
        )
        authority = json.loads(json.dumps(gate["authority"]))
        authority["participation_as_availability"] = True
        mutations.append(
            expect_rejection(
                "participation_as_availability",
                lambda: _validate(_mutated_gate(gate, authority=authority)),
            )
        )
        authority = json.loads(json.dumps(gate["authority"]))
        authority["bat_429_ready_or_done"] = True
        mutations.append(
            expect_rejection("bat_429_marked_ready", lambda: _validate(_mutated_gate(gate, authority=authority)))
        )
        mutations.append(
            expect_rejection(
                "protected_lane_opened",
                lambda: _validate(_mutated_gate(gate, protected_lane="OPEN_PROTECTED_LANE")),
            )
        )
        forged = _mutated_gate(gate, result="FORGED_VERIFIED_OFFICIAL", classification="VERIFIED_OFFICIAL")
        mutations.append(expect_rejection("forged_verified_after_rehash", lambda: _validate(forged)))
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
