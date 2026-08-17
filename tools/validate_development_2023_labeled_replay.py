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
    FORBIDDEN_FEATURE_FIELDS,
    GATE_RELATIVE,
    PASS_RESULT,
    ProtectedOutcomeDenied,
    SUPERSEDED_KICKOFF_LABEL_IDENTITY,
    assert_feature_surface,
    assert_no_protected_outcomes,
    compute_gate_identity,
    rebuild_expected,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, ProtectedOutcomeDenied, FileNotFoundError, AssertionError) as exc:
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
        description="Independently validate the 2023 labeled development replay."
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
        manifest_path = (
            data_root
            / "manifests"
            / "development_2023_matrix"
            / "sha256"
            / expected["matrix_identity"]
            / "development_2023_labeled_replay_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        def _validate(tampered_gate: dict[str, Any], tampered_manifest: dict[str, Any] | None = None) -> Any:
            return validate_artifact(
                data_root=data_root,
                repo_root=repo_root,
                require_rebuild=True,
                gate=tampered_gate,
                manifest=tampered_manifest if tampered_manifest is not None else manifest,
                expected=expected,
            )

        folds = json.loads(json.dumps(gate["folds"]))
        folds[1]["train_row_count"] = int(folds[1]["train_row_count"]) + 7
        mutations.append(
            expect_rejection(
                "changed_train_row_count",
                lambda: _validate(_mutated_gate(gate, folds=folds)),
            )
        )
        membership_folds = json.loads(json.dumps(gate["folds"]))
        membership_folds[1]["membership"]["train_membership_sha256"] = "a" * 64
        mutations.append(
            expect_rejection(
                "changed_fold_membership",
                lambda: _validate(_mutated_gate(gate, folds=membership_folds)),
            )
        )
        cutoff_folds = json.loads(json.dumps(gate["folds"]))
        cutoff_folds[1]["fold_evaluation_cutoff_utc"] = "2099-01-01T00:00:00Z"
        mutations.append(
            expect_rejection(
                "changed_fold_cutoff",
                lambda: _validate(_mutated_gate(gate, folds=cutoff_folds)),
            )
        )
        same_game_folds = json.loads(json.dumps(gate["folds"]))
        same_game_folds[0]["same_game_excluded"] = False
        mutations.append(
            expect_rejection(
                "changed_same_game_proof",
                lambda: _validate(_mutated_gate(gate, folds=same_game_folds)),
            )
        )
        metrics = json.loads(json.dumps(gate["metrics"]))
        metrics["prior_only"]["brier"] = 0.01
        mutations.append(
            expect_rejection(
                "changed_metric",
                lambda: _validate(_mutated_gate(gate, metrics=metrics)),
            )
        )
        incremental = dict(gate["incremental_play_drive_result"])
        incremental["brier_delta_plus_minus_prior"] = -0.5
        mutations.append(
            expect_rejection(
                "changed_incremental_result",
                lambda: _validate(_mutated_gate(gate, incremental_play_drive_result=incremental)),
            )
        )
        authority = dict(gate["authority"])
        authority["champion_or_production_promotion"] = True
        mutations.append(
            expect_rejection(
                "promotion_authority_changed_to_true",
                lambda: _validate(_mutated_gate(gate, authority=authority)),
            )
        )
        nonclaims = dict(gate["scientific_nonclaims"])
        nonclaims["protected_performance_claimed"] = True
        mutations.append(
            expect_rejection(
                "protected_performance_claim_changed_to_true",
                lambda: _validate(_mutated_gate(gate, scientific_nonclaims=nonclaims)),
            )
        )
        identities = dict(gate["input_identities"])
        identities["bat565_label_dataset_identity"] = SUPERSEDED_KICKOFF_LABEL_IDENTITY
        mutations.append(
            expect_rejection(
                "altered_bat565_parent_identity",
                lambda: _validate(_mutated_gate(gate, input_identities=identities)),
            )
        )
        substituted = json.loads(json.dumps(manifest))
        substituted["payloads"][0]["sha256"] = "2" * 64
        payloads = json.loads(json.dumps(gate["payloads"]))
        payloads[0]["sha256"] = "2" * 64
        mutations.append(
            expect_rejection(
                "substituted_matrix_payload",
                lambda: _validate(_mutated_gate(gate, payloads=payloads), substituted),
            )
        )
        omitted = json.loads(json.dumps(manifest))
        omitted["payloads"] = list(manifest["payloads"][1:])
        mutations.append(
            expect_rejection(
                "omitted_payload",
                lambda: _validate(_mutated_gate(gate), omitted),
            )
        )
        mutations.append(
            expect_rejection(
                "altered_result_classification",
                lambda: _validate(_mutated_gate(gate, result="PASS_PRODUCTION_READY")),
            )
        )
        forged = _mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        if forged["gate_identity"] == gate["gate_identity"]:
            raise AssertionError("forged terminal state failed to recompute a distinct outer identity")
        mutations.append(
            expect_rejection(
                "forged_completion_after_identity_recompute",
                lambda: _validate(forged),
            )
        )
        mutations.append(
            expect_rejection(
                "protected_year_insertion",
                lambda: assert_no_protected_outcomes(
                    [{"season": 2024, "target_game_id": "g"}], context="mutation"
                ),
            )
        )
        mutations.append(
            expect_rejection(
                "feature_surface_outcome_leak",
                lambda: assert_feature_surface([{"season": 2023, "result": "WIN", "row_id": "r"}]),
            )
        )
        if result.get("result") != "PASS" or result.get("supersedes") is None:
            raise AssertionError("active replay must supersede the kickoff-time identity")
        if PASS_RESULT != "PASS_DEVELOPMENT_ONLY_2023_LABELED_REPLAY":
            raise AssertionError("pass result constant drifted")
        if FORBIDDEN_FEATURE_FIELDS & {"result"} != {"result"}:
            raise AssertionError("forbidden feature set lost result")
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
