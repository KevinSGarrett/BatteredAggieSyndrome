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

from aggie_analytics.experimentation.development_2023_labeled_replay import (  # noqa: E402
    ProtectedOutcomeDenied,
)
from aggie_analytics.experimentation.development_rankings_walk_forward_2023 import (  # noqa: E402
    GATE_RELATIVE,
    RankingsJoinDenied,
    compute_gate_identity,
    join_rankings,
    rebuild_expected,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, RankingsJoinDenied, ProtectedOutcomeDenied, FileNotFoundError, AssertionError) as exc:
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
        description="Independently validate the 2023 rankings-augmented development walk-forward."
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

        def _validate(tampered: dict[str, Any]) -> Any:
            return validate_artifact(
                data_root=data_root,
                repo_root=repo_root,
                require_rebuild=True,
                gate=tampered,
                expected=expected,
            )

        future = json.loads(json.dumps(expected["joined"][0]))
        future["poll_first_eligible_at_utc"] = "2099-01-01T00:00:00Z"
        future["rank"] = 1
        future["ranking_state"] = "RANKED_NUMERIC"
        mutations.append(
            expect_rejection(
                "future_poll_insertion",
                lambda: join_rankings(
                    feature_rows=[expected["joined"][0]],
                    label_rows=expected["labels"][:1],
                    rankings_rows=[
                        {
                            **future,
                            "canonical_team_id": future["team_id"],
                            "season": 2023,
                            "rank_state": "RANKED",
                        }
                    ],
                    feature_identity="0" * 64,
                    feature_payload_sha256="1" * 64,
                ),
            )
        )
        protected = json.loads(json.dumps(expected["joined"][0]))
        protected["season"] = 2025
        mutations.append(
            expect_rejection(
                "protected_outcome_insertion",
                lambda: join_rankings(
                    feature_rows=[protected],
                    label_rows=expected["labels"][:1],
                    rankings_rows=[],
                    feature_identity="0" * 64,
                    feature_payload_sha256="1" * 64,
                ),
            )
        )
        metrics = json.loads(json.dumps(gate["metrics"]))
        metrics["prior_plus_rankings"]["brier"] = 0.01
        mutations.append(
            expect_rejection(
                "result_inflation",
                lambda: _validate(_mutated_gate(gate, metrics=metrics)),
            )
        )
        coverage = json.loads(json.dumps(gate["coverage"]))
        coverage["team_rows"] = int(coverage["team_rows"]) - 1
        coverage["ranked_numeric_rows"] = int(coverage["ranked_numeric_rows"]) + 1
        mutations.append(
            expect_rejection(
                "row_substitution",
                lambda: _validate(_mutated_gate(gate, coverage=coverage)),
            )
        )
        omitted = list(gate["candidates"])[:-1]
        mutations.append(
            expect_rejection(
                "candidate_omission",
                lambda: _validate(_mutated_gate(gate, candidates=omitted)),
            )
        )
        added = list(gate["candidates"]) + ["post_hoc_stacker"]
        mutations.append(
            expect_rejection(
                "candidate_addition",
                lambda: _validate(_mutated_gate(gate, candidates=added)),
            )
        )
        authority = json.loads(json.dumps(gate["authority"]))
        authority["champion_or_production_promotion"] = True
        mutations.append(
            expect_rejection(
                "promotion_authority_forgery",
                lambda: _validate(_mutated_gate(gate, authority=authority)),
            )
        )
        forged = _mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        mutations.append(
            expect_rejection(
                "recomputed_outer_identity",
                lambda: _validate(forged),
            )
        )
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
