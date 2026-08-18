from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.experimentation.development_candidate_evidence_ledger import (  # noqa: E402
    LEDGER_RELATIVE,
    LedgerValidationDenied,
    compute_ledger_identity,
    rebuild_expected,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, LedgerValidationDenied, FileNotFoundError, AssertionError, KeyError) as exc:
        return {
            "name": name,
            "result": "PASS_FAIL_CLOSED",
            "exception": type(exc).__name__,
            "message": str(exc)[:240],
        }
    raise AssertionError(f"mutation control did not reject: {name}")


def _mutated_ledger(ledger: dict[str, Any], **changes: Any) -> dict[str, Any]:
    tampered = json.loads(json.dumps(ledger))
    tampered.update(changes)
    tampered["ledger_identity"] = compute_ledger_identity(tampered)
    return tampered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently validate the identity-bound development candidate evidence ledger."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    result = validate_artifact(repo_root=repo_root)
    mutations: list[dict[str, Any]] = []
    if not args.validate_only:
        expected = rebuild_expected(repo_root)
        ledger = json.loads((repo_root / LEDGER_RELATIVE).read_text(encoding="utf-8"))

        def _validate(tampered: dict[str, Any]) -> Any:
            return validate_artifact(repo_root=repo_root, ledger=tampered, expected=expected)

        changed_metrics = json.loads(json.dumps(ledger["entries"]))
        changed_metrics[2]["team_row_metrics"]["brier"] = 0.01
        mutations.append(
            expect_rejection(
                "changed_metrics",
                lambda: _validate(_mutated_ledger(ledger, entries=changed_metrics)),
            )
        )
        changed_cohort = dict(ledger["cohort"])
        changed_cohort["team_rows"] = 1819
        mutations.append(
            expect_rejection(
                "changed_cohort",
                lambda: _validate(_mutated_ledger(ledger, cohort=changed_cohort)),
            )
        )
        omitted_negative = json.loads(json.dumps(ledger["entries"]))
        omitted_negative[1]["brier_delta_vs_prior_only"] = -0.01
        omitted_negative[1]["negative_result_preserved"] = False
        mutations.append(
            expect_rejection(
                "omitted_negative_result",
                lambda: _validate(_mutated_ledger(ledger, entries=omitted_negative)),
            )
        )
        hidden = list(ledger["candidates"])[:-1]
        mutations.append(
            expect_rejection(
                "hidden_candidate",
                lambda: _validate(_mutated_ledger(ledger, candidates=hidden)),
            )
        )
        mutations.append(
            expect_rejection(
                "altered_comparison_count",
                lambda: _validate(_mutated_ledger(ledger, comparison_count=3)),
            )
        )
        decision_without_reason = json.loads(json.dumps(ledger["entries"]))
        decision_without_reason[2]["state"] = "RETAIN_DEVELOPMENT_CANDIDATE"
        decision_without_reason[2]["reason"] = ""
        mutations.append(
            expect_rejection(
                "changed_decision_without_reason",
                lambda: _validate(_mutated_ledger(ledger, entries=decision_without_reason)),
            )
        )
        authority = dict(ledger["authority"])
        authority["champion_or_production_promotion"] = True
        mutations.append(
            expect_rejection(
                "production_protected_authority",
                lambda: _validate(_mutated_ledger(ledger, authority=authority)),
            )
        )
        mutations.append(
            expect_rejection(
                "missing_supersession_record",
                lambda: _validate(_mutated_ledger(ledger, supersession={})),
            )
        )
        mutations.append(
            expect_rejection(
                "forged_ledger_completion_after_identity_recompute",
                lambda: _validate(
                    _mutated_ledger(
                        ledger,
                        result="FORGED_DONE",
                        classification="PRODUCTION_CHAMPION",
                    )
                ),
            )
        )
    print(
        json.dumps(
            {
                "result": result["result"],
                "ledger_identity": result["ledger_identity"],
                "fold_definition_identity": result["fold_definition_identity"],
                "comparison_count": result["comparison_count"],
                "mutations": mutations,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
