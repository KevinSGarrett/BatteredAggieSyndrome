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

from aggie_analytics.data.tamu_official_evidence_gap_matrix import (  # noqa: E402
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
        description="Independently validate the Texas A&M official-evidence gap matrix."
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
        authority["name_only_promotion"] = True
        mutations.append(
            expect_rejection("silent_name_only_promotion", lambda: _validate(_mutated_gate(gate, authority=authority)))
        )
        special = json.loads(json.dumps(gate["special_path"]))
        swapped = list(special["opponents"])
        if len(swapped) >= 2:
            swapped[0], swapped[1] = swapped[1], swapped[0]
        special["opponents"] = swapped
        mutations.append(
            expect_rejection("swapped_opponent", lambda: _validate(_mutated_gate(gate, special_path=special)))
        )
        special_date = json.loads(json.dumps(gate["special_path"]))
        dates = list(special_date["dates"])
        if dates:
            dates[0] = "1999-01-01"
        special_date["dates"] = dates
        mutations.append(
            expect_rejection("wrong_date", lambda: _validate(_mutated_gate(gate, special_path=special_date)))
        )
        special_dup = json.loads(json.dumps(gate["special_path"]))
        special_dup["contest_ids"] = ["999999", "999999"]
        special_dup["duplicate_contest_assignments"] = 1
        mutations.append(
            expect_rejection(
                "duplicate_contest_assignment",
                lambda: _validate(_mutated_gate(gate, special_path=special_dup)),
            )
        )
        authority = json.loads(json.dumps(gate["authority"]))
        authority["protected_outcome_authority"] = True
        mutations.append(
            expect_rejection(
                "protected_outcome_authority",
                lambda: _validate(_mutated_gate(gate, authority=authority)),
            )
        )
        authority = json.loads(json.dumps(gate["authority"]))
        authority["historical_known_at_from_capture_time"] = True
        mutations.append(
            expect_rejection(
                "capture_time_labeled_historical_known_at",
                lambda: _validate(_mutated_gate(gate, authority=authority)),
            )
        )
        authority = json.loads(json.dumps(gate["authority"]))
        authority["participation_as_availability"] = True
        mutations.append(
            expect_rejection(
                "participation_relabeled_availability",
                lambda: _validate(_mutated_gate(gate, authority=authority)),
            )
        )
        counts = json.loads(json.dumps(gate["counts"]))
        counts["missing_ncaa_endpoints"] = 0
        mutations.append(
            expect_rejection("omitted_missing_endpoint", lambda: _validate(_mutated_gate(gate, counts=counts)))
        )
        counts = json.loads(json.dumps(gate["counts"]))
        counts["scheduled_games_2010_2025"] = counts["scheduled_games_2010_2025"] + 50
        mutations.append(
            expect_rejection("inflated_coverage", lambda: _validate(_mutated_gate(gate, counts=counts)))
        )
        mutations.append(
            expect_rejection(
                "missing_or_substituted_payload",
                lambda: validate_artifact(
                    data_root=data_root / "_missing_gap_matrix_payload",
                    repo_root=repo_root,
                    require_rebuild=True,
                    expected=expected,
                ),
            )
        )
        forged = _mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        mutations.append(expect_rejection("forged_terminal_state_after_rehash", lambda: _validate(forged)))
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
