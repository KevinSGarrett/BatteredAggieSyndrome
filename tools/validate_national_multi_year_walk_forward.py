"""Independently validate the 2018-2023 national walk-forward.

The validator is read-only. When a data root is mounted it re-runs the whole walk-forward and
proves the committed prediction payload reproduces byte for byte, and that no fold's training
partition contains a row from its own evaluation season or later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.modeling.national_multi_year_walk_forward import (  # noqa: E402
    GATE_RELATIVE,
    MATRIX_GATE_RELATIVE,
    WalkForwardViolation,
    canonical_json_bytes,
    load_candidates,
    load_contract,
    read_json,
    read_jsonl,
    run_walk_forward,
    summarize_candidates,
    validate_artifact,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_national_multi_year_walk_forward import matrix_dir, require  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    summary = validate_artifact(repo_root)
    gate = read_json(repo_root / GATE_RELATIVE)
    checks: list[dict[str, object]] = []

    data_root = args.data_root.resolve() if args.data_root else None
    if data_root is None or not data_root.exists():
        checks.append({"check": "FULL_REPLAY", "state": "SKIP_DATA_ROOT_ABSENT"})
        print(json.dumps({**summary, "checks": checks}, indent=2, sort_keys=True))
        return 0

    contract = load_contract(repo_root)
    candidates, candidate_sha = load_candidates(repo_root, contract)
    if candidate_sha != gate["candidate_set_sha256"]:
        raise WalkForwardViolation("the frozen candidate set no longer hashes to the committed value")
    checks.append({"check": "CANDIDATE_SET_PRESERVED", "state": "PASS"})

    matrix_gate = read_json(repo_root / MATRIX_GATE_RELATIVE)
    base = matrix_dir(data_root, matrix_gate["dataset_identity"])
    matrix = read_jsonl(require(base / "national_development_matrix_features.jsonl"))
    labels = read_jsonl(require(base / "national_development_matrix_labels.jsonl"))

    predictions, folds = run_walk_forward(
        matrix=matrix, labels=labels, candidates=candidates, contract=contract
    )
    digest = hashlib.sha256(
        b"".join(canonical_json_bytes(row) + b"\n" for row in predictions)
    ).hexdigest()
    if digest != gate["payload"]["sha256"]:
        raise WalkForwardViolation("the committed prediction payload does not reproduce")
    checks.append({"check": "PREDICTIONS_REPRODUCE_FROM_THE_MATRIX", "state": "PASS"})

    seasons_by_row = {
        (row["canonical_game_id"], row["canonical_team_id"]): int(row["season"]) for row in matrix
    }
    for fold in folds:
        season = fold["evaluation_season"]
        training = [row for row in matrix if int(row["season"]) < season]
        if any(int(row["season"]) >= season for row in training):
            raise WalkForwardViolation(f"fold {fold['fold_id']} training partition is contaminated")
    checks.append({"check": "NO_FOLD_TRAINED_ON_ITS_OWN_SEASON_OR_LATER", "state": "PASS"})

    scored_seasons = {seasons_by_row[(r["canonical_game_id"], r["canonical_team_id"])] for r in predictions}
    forbidden = set(contract["evaluation"]["forbidden_seasons"])
    if forbidden & scored_seasons:
        raise WalkForwardViolation("a forbidden season row was scored")
    checks.append({"check": "NO_FORBIDDEN_SEASON_ROW_WAS_SCORED", "state": "PASS"})

    replayed = summarize_candidates(predictions, candidates, contract)
    committed = {row["candidate_id"]: row["aggregate"]["brier"] for row in gate["candidate_metrics"]}
    for row in replayed:
        if committed.get(row["candidate_id"]) != row["aggregate"]["brier"]:
            raise WalkForwardViolation(
                f"candidate {row['candidate_id']} does not reproduce its committed Brier score"
            )
    checks.append({"check": "EVERY_CANDIDATE_METRIC_REPRODUCES", "state": "PASS"})

    print(json.dumps({**summary, "checks": checks}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
