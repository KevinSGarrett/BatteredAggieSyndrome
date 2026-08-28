"""Freeze prospective 2026 national shadow forecasts from immutable captures.

This command performs no network access. It reads a capture manifest produced by
``acquire_2026_prospective_schedule.py``, refits the admissible Phase 6 candidates
on the admitted national development population, freezes one pregame snapshot per
still-eligible contest, and publishes a compact repository gate plus external
content-addressed payloads.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    binding_identity,
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import (  # noqa: E402
    iso_utc,
    load_alias_population,
    parse_utc,
)
from aggie_analytics.modeling.national_expectation_baselines import elo_ratings  # noqa: E402
from aggie_analytics.modeling.prospective_shadow_forecasts import (  # noqa: E402
    CONTRACT_RELATIVE,
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    base_rate,
    build_forecast_bundle,
    build_gate,
    dataset_manifest,
    load_contract,
    load_matrix_rows,
    training_population,
    validate_artifact,
)

PAYLOAD_ROOT = "canonical/prospective_2026_shadow_forecasts"
CODE_MODULES = (
    "src/aggie_analytics/modeling/prospective_shadow_forecasts.py",
    "src/aggie_analytics/modeling/national_expectation_baselines.py",
    "src/aggie_analytics/data/prospective_shadow_cohort.py",
    "tools/build_prospective_2026_shadow_forecasts.py",
)


def write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    body = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body.encode("utf-8"))
    return sha256_file(path)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--capture-manifest", type=Path, required=True)
    result.add_argument("--alias-payload", type=Path, required=True)
    result.add_argument("--execution-time-utc", required=True)
    result.add_argument("--issued-at-utc", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    contract = load_contract(repo_root)
    execution_time = parse_utc(args.execution_time_utc)
    issued_at = parse_utc(args.issued_at_utc)
    if execution_time > datetime.now(timezone.utc):
        raise ValueError("execution time must not be in the future")

    bound = contract["bound_predecessors"]
    baseline_contract = json.loads(
        (repo_root / bound["baseline_contract_relative_path"]).read_text(encoding="utf-8-sig")
    )
    matrix_gate = json.loads(
        (repo_root / bound["matrix_gate_relative_path"]).read_text(encoding="utf-8-sig")
    )

    capture_manifest = json.loads(args.capture_manifest.resolve().read_text(encoding="utf-8-sig"))
    captures = [row for row in capture_manifest["captures"] if row["state"] == "CAPTURED"]
    documents = {
        capture["game_date"]: (data_root / capture["raw_relative_path"]).read_text(
            encoding="utf-8", errors="replace"
        )
        for capture in captures
    }
    population = load_alias_population(
        args.alias_payload.resolve(),
        minimum_most_recent_season=2020,
    )

    features = load_matrix_rows(data_root, matrix_gate, "national_development_matrix_features.jsonl")
    labels = load_matrix_rows(data_root, matrix_gate, "national_development_matrix_labels.jsonl")
    training, label_index = training_population(
        features,
        labels,
        last_admitted_season=int(contract["forecast"]["last_admitted_training_season"]),
        sealed_seasons=contract["forecast"]["sealed_seasons_excluded_from_training"],
    )
    elo_hyperparameters = next(
        item for item in baseline_contract["candidates"] if item["candidate_id"] == "national_elo"
    )["hyperparameters"]
    ratings = elo_ratings(training, label_index, hyperparameters=elo_hyperparameters)
    probability = base_rate(training, label_index)
    fitted = {
        "national_base_rate": {"probability": probability},
        "national_elo": {"ratings": ratings, "hyperparameters": dict(elo_hyperparameters)},
    }
    fitted_summary = {
        "national_base_rate": {
            "training_rows": len(training),
            "training_win_rate": round(probability, 8),
        },
        "national_elo": {
            "training_rows": len(training),
            "rated_teams": len(ratings),
            "hyperparameters": dict(elo_hyperparameters),
            "rating_basis": contract["forecast"]["candidate_admissibility"][1][
                "declared_rating_staleness"
            ],
        },
    }
    model_identity = stable_hash(
        {
            "base_rate": round(probability, 12),
            "elo_hyperparameters": dict(elo_hyperparameters),
            "elo_ratings": {team: round(value, 9) for team, value in sorted(ratings.items())},
            "last_admitted_training_season": contract["forecast"]["last_admitted_training_season"],
            "training_rows": len(training),
        }
    )
    feature_identity = stable_hash(
        {
            "matrix_dataset_identity": matrix_gate["dataset_identity"],
            "scopes": sorted(
                str(item["required_feature_scope"])
                for item in contract["forecast"]["candidate_admissibility"]
                if item["admissibility"] == "ADMISSIBLE_FOR_PROSPECTIVE_SHADOW_USE"
            ),
        }
    )
    code_identity = stable_hash(
        {relative: sha256_file(repo_root / relative) for relative in CODE_MODULES}
    )

    bundle = build_forecast_bundle(
        contract=contract,
        baseline_contract=baseline_contract,
        captures=captures,
        documents=documents,
        population=population,
        fitted=fitted,
        model_identity=model_identity,
        feature_identity=feature_identity,
        code_identity=code_identity,
        execution_time=execution_time,
    )

    payload_entries: list[dict[str, Any]] = []
    for name, role, rows in (
        (
            "prospective_2026_shadow_snapshots.jsonl",
            "PROSPECTIVE_2026_SHADOW_SNAPSHOT_ROWS",
            bundle["contests"],
        ),
        (
            "prospective_2026_shadow_forecasts.jsonl",
            "PROSPECTIVE_2026_SHADOW_FORECAST_ROWS",
            bundle["forecasts"],
        ),
    ):
        pending = data_root / PAYLOAD_ROOT / "pending" / name
        digest = write_jsonl(pending, rows)
        final_relative = f"{PAYLOAD_ROOT}/sha256/{digest}/{name}"
        final_path = data_root / final_relative
        final_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(pending, final_path)
        payload_entries.append(
            {
                "name": name,
                "relative_path": final_relative,
                "role": role,
                "rows": len(rows),
                "bytes": final_path.stat().st_size,
                "sha256": digest,
            }
        )

    manifest = dataset_manifest(contract=contract, bundle=bundle, payloads=payload_entries)
    manifest_relative = (
        "manifests/prospective_2026_shadow_forecasts/sha256/"
        f"{manifest['dataset_identity']}/prospective_2026_shadow_forecast_manifest.json"
    )
    manifest_path = data_root / manifest_relative
    write_json(manifest_path, manifest)

    gate = build_gate(
        contract=contract,
        contract_sha256=sha256_file(repo_root / CONTRACT_RELATIVE),
        bundle=bundle,
        manifest_relative_path=manifest_relative,
        manifest_sha256=sha256_file(manifest_path),
        dataset_identity=manifest["dataset_identity"],
        predecessor_sha256={
            "baseline_gate_sha256": sha256_file(repo_root / bound["baseline_gate_relative_path"]),
            "cohort_gate_sha256": sha256_file(repo_root / bound["cohort_gate_relative_path"]),
            "matrix_gate_sha256": sha256_file(repo_root / bound["matrix_gate_relative_path"]),
            "spine_gate_sha256": sha256_file(repo_root / bound["spine_gate_relative_path"]),
        },
        model_identity=model_identity,
        feature_identity=feature_identity,
        code_identity=code_identity,
        fitted_summary=fitted_summary,
    )
    gate = {
        **gate,
        "capture_identity": capture_manifest["capture_identity"],
        "issued_at_utc": iso_utc(issued_at),
        "producer": {"python": sys.version.split()[0], "platform": platform.platform()},
    }
    gate["gate_identity"] = binding_identity(gate, "gate_identity")
    write_json(repo_root / GATE_RELATIVE, gate)

    verification = validate_artifact(repo_root, data_root)
    write_json(
        repo_root / EVIDENCE_RELATIVE,
        {
            "schema_version": gate["schema_version"],
            "artifact_type": "PROSPECTIVE_2026_NATIONAL_SHADOW_FORECAST_REPLAY",
            "contract_id": gate["contract_id"],
            "decision_unit": gate["decision_unit"],
            "jira_key": gate["jira_key"],
            "gate_identity": gate["gate_identity"],
            "capture_identity": capture_manifest["capture_identity"],
            "execution_time_utc": gate["execution_time_utc"],
            "independent_validation": verification,
            "issued_at_utc": iso_utc(issued_at),
        },
    )
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "dataset_identity": manifest["dataset_identity"],
                "population_counts": gate["population_counts"],
                "contest_state_counts": gate["contest_state_counts"],
                "forecast_state_counts": gate["forecast_state_counts"],
                "frozen_forecast_contests": len(gate["frozen_forecast_contest_ids"]),
                "independent_validation": verification["result"],
                "findings": verification["findings"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if verification["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
