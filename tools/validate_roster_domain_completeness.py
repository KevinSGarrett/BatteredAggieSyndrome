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

from aggie_analytics.validation.roster_domain_completeness import (  # noqa: E402
    AvailabilityAdmissionDenied,
    GATE_RELATIVE,
    PayloadMountRequired,
    compute_gate_identity,
    rebuild_expected,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, AvailabilityAdmissionDenied, PayloadMountRequired, AssertionError) as exc:
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
        description="Independently validate the roster-domain completeness gate."
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

        authority = json.loads(json.dumps(gate["authority"]))
        authority["protected_evaluation_admission"] = True
        mutations.append(
            expect_rejection(
                "protected_evaluation_admission_true",
                lambda: _validate(_mutated_gate(gate, authority=authority)),
            )
        )
        champion = json.loads(json.dumps(gate["authority"]))
        champion["champion_or_production_promotion"] = True
        mutations.append(
            expect_rejection(
                "champion_or_production_promotion_true",
                lambda: _validate(_mutated_gate(gate, authority=champion)),
            )
        )
        nonclaims = json.loads(json.dumps(gate["scientific_nonclaims"]))
        nonclaims["protected_performance_claimed"] = True
        mutations.append(
            expect_rejection(
                "protected_performance_claim_true",
                lambda: _validate(_mutated_gate(gate, scientific_nonclaims=nonclaims)),
            )
        )
        admissions = json.loads(json.dumps(gate["admissions"]))
        admissions["pregame_availability"] = "ADMITTED"
        mutations.append(
            expect_rejection(
                "pregame_availability_admitted",
                lambda: _validate(_mutated_gate(gate, admissions=admissions)),
            )
        )
        blockers = [code for code in gate["remaining_blockers"] if code != "MEMBERSHIP_IS_NOT_AVAILABILITY"]
        mutations.append(
            expect_rejection(
                "missing_availability_blocker_removed",
                lambda: _validate(_mutated_gate(gate, remaining_blockers=blockers)),
            )
        )
        mutations.append(
            expect_rejection(
                "altered_classification",
                lambda: _validate(
                    _mutated_gate(gate, classification="ROSTER_AVAILABILITY_ADMITTED")
                ),
            )
        )
        reconstructed = json.loads(json.dumps(gate["reconstructed"]))
        reconstructed["a_and_m_versus_national"]["tamu_admitted_membership_rows_2004_2022"] = 999999
        mutations.append(
            expect_rejection(
                "altered_reconstructed_counts",
                lambda: _validate(_mutated_gate(gate, reconstructed=reconstructed)),
            )
        )
        mutations.append(
            expect_rejection(
                "altered_membership_filter_identity",
                lambda: _validate(_mutated_gate(gate, exact_membership_filter_identity="0" * 64)),
            )
        )
        parents = json.loads(json.dumps(gate["parent_identities"]))
        parents["BAT-546_admitted_dataset"] = "1" * 64
        mutations.append(
            expect_rejection(
                "altered_bat546_parent_identity",
                lambda: _validate(_mutated_gate(gate, parent_identities=parents)),
            )
        )
        parents_547 = json.loads(json.dumps(gate["parent_identities"]))
        parents_547["BAT-547_admitted_dataset"] = "2" * 64
        mutations.append(
            expect_rejection(
                "altered_bat547_parent_identity",
                lambda: _validate(_mutated_gate(gate, parent_identities=parents_547)),
            )
        )
        forged = _mutated_gate(
            gate,
            result="FORGED_DONE",
            classification="PRODUCTION_CHAMPION",
            issue_completion={
                **gate["issue_completion"],
                "issue_complete": True,
                "pregame_availability_still_blocked": False,
            },
        )
        mutations.append(
            expect_rejection(
                "forged_terminal_state_after_identity_recompute",
                lambda: _validate(forged),
            )
        )
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
