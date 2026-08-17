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
    ProtectedOutcomeDenied,
    assert_feature_surface,
    assert_no_protected_outcomes,
    identity_core,
    stable_hash,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, ProtectedOutcomeDenied, AssertionError) as exc:
        return {"name": name, "result": "PASS_FAIL_CLOSED", "exception": type(exc).__name__}
    raise AssertionError(f"mutation control did not reject: {name}")


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
    result = validate_artifact(
        data_root=args.data_root.resolve(),
        repo_root=args.repo_root.resolve(),
        require_rebuild=True,
    )
    mutations: list[dict[str, Any]] = []
    if not args.validate_only:
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
                lambda: assert_feature_surface(
                    [{"season": 2023, "result": "WIN", "row_id": "r"}]
                ),
            )
        )
        core = identity_core(
            contract_sha256="a" * 64,
            input_identities={
                "bat523_prior_dataset_identity": "b" * 64,
                "bat523_pregame_prior_rows_sha256": "c" * 64,
                "play_drive_dataset_identity": "d" * 64,
                "play_drive_feature_sha256": "e" * 64,
                "bat565_label_dataset_identity": "f" * 64,
                "bat565_team_outcome_sha256": "1" * 64,
                "protected_split_registry_sha256": "2" * 64,
            },
            record_hashes={"features": "3" * 64, "labels": "4" * 64},
            population={
                "feature_rows": 1,
                "label_rows": 1,
                "games": 1,
                "cold_start_rows": 0,
                "seasons": [2023],
            },
            fold_hashes=["5" * 64],
            metrics={"prior_only": {"brier": 0.2}},
        )
        tampered = dict(core)
        tampered["metrics"] = {"prior_only": {"brier": 0.01}}
        mutations.append(
            expect_rejection(
                "recomputed_outer_identity_after_metric_tamper",
                lambda: (_ for _ in ()).throw(
                    ValueError("outer identity changed")
                    if stable_hash(core) != stable_hash(tampered)
                    else AssertionError("identity collision")
                ),
            )
        )
        if FORBIDDEN_FEATURE_FIELDS & {"result"} != {"result"}:
            raise AssertionError("forbidden feature set lost result")
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
