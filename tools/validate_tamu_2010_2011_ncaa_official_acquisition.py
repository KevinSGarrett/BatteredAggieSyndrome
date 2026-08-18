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

from aggie_analytics.data.tamu_2010_2011_ncaa_official_acquisition import (  # noqa: E402
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
        description="Independently validate the bounded 2010-2011 Texas A&M NCAA official acquisition."
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
        expected = rebuild_expected(data_root=data_root, repo_root=repo_root, allow_live=False)
        gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8"))

        def _validate(tampered_gate: dict[str, Any]) -> Any:
            return validate_artifact(
                data_root=data_root,
                repo_root=repo_root,
                require_rebuild=True,
                gate=tampered_gate,
                expected=expected,
            )

        seeds = json.loads(json.dumps(gate["tamu_seeds"]))
        seeds["2010"] = "136982"
        mutations.append(expect_rejection("auburn_seed_as_tamu", lambda: _validate(_mutated_gate(gate, tamu_seeds=seeds))))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["contest_ids_2010"] = 13
        counts["contest_ids_present"] = 13
        mutations.append(
            expect_rejection(
                "invented_contest_ids",
                lambda: _validate(_mutated_gate(gate, counts=counts, disposition="MODERN_CONTEST_LINKS_PRESENT")),
            )
        )
        authority = json.loads(json.dumps(gate["authority"]))
        authority["bat_554_reopen"] = True
        mutations.append(expect_rejection("bat_554_reopen", lambda: _validate(_mutated_gate(gate, authority=authority))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["completeness_claim"] = True
        mutations.append(expect_rejection("completeness_claim", lambda: _validate(_mutated_gate(gate, authority=authority))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["historical_pit_admission"] = True
        mutations.append(
            expect_rejection("historical_pit_admission", lambda: _validate(_mutated_gate(gate, authority=authority)))
        )
        authority = json.loads(json.dumps(gate["authority"]))
        authority["protected_outcome_authority"] = True
        mutations.append(
            expect_rejection(
                "protected_outcome_authority",
                lambda: _validate(_mutated_gate(gate, authority=authority)),
            )
        )
        forged = _mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        mutations.append(expect_rejection("forged_terminal_state_after_rehash", lambda: _validate(forged)))
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
