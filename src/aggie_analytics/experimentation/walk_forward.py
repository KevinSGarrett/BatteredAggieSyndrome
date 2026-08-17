from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.temporal.contracts import parse_time
from aggie_analytics.validation.protected_split_authority import (
    is_protected_canonical_season,
    registry_role_for_season,
)

# Development-safe chronological walk-forward runner for BAT-400.
# BAT-523 outcomes cover 2010-2022 only; 2023 label joins are a negative finding.

SCHEMA_VERSION = "aggie.experimentation.walk_forward_dry_run.v2"
CHECKPOINT_SCHEMA = "aggie.experimentation.walk_forward_checkpoint.v1"
DATASET_IDENTITY = "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
DEVELOPMENT_SEASON = 2023
PROTECTED_SEASONS = frozenset({2024, 2025})
HISTORY_OUTCOME_SEASONS = frozenset(range(2010, 2023))
FEATURE_COLUMNS = (
    "prior_games",
    "prior_win_rate",
    "prior_points_for_mean",
    "prior_points_against_mean",
)
MANIFEST_RELATIVE = (
    f"manifests/historical_known_at/sha256/{DATASET_IDENTITY}/known_at_replay_manifest.json"
)
REQUIRED_PAYLOADS = {
    "accepted_game_outcomes.parquet": {
        "rows": 10593,
        "sha256": "7fdea2ced7508e7f3b78d397bf8984325dd2b7095b05dc486335ee9c432ccb64",
        "required_columns": (
            "observation_id",
            "canonical_game_id",
            "season",
            "home_points",
            "away_points",
            "source_known_at_utc",
        ),
    },
    "team_outcome_observations.parquet": {
        "rows": 21186,
        "sha256": "8a8e057c5eb135a731e37b74587893f25e29c7f1040d7f294f38071e30a9f483",
        "required_columns": (
            "observation_id",
            "canonical_game_id",
            "season",
            "team_id",
            "source_known_at_utc",
            "completed_known_by_utc",
            "game_start_utc",
            "points_for",
            "points_against",
            "result",
        ),
    },
    "target_game_cutoffs.parquet": {
        "rows": 2764,
        "sha256": "a32b733d9f2278639fea0d4dedc3e9f33a45004f042f869cff148a4bf0faf942",
        "required_columns": (
            "game_id",
            "season",
            "start_utc",
            "home_team_id",
            "away_team_id",
            "cutoff_lead_hours",
        ),
    },
    "pregame_prior_rows.parquet": {
        "rows": 5528,
        "sha256": "23db814da58cfbf0975e99b32130c531ae8e4f26867f0ac1e5207ba36bd6d140",
        "required_columns": (
            "row_id",
            "target_game_id",
            "cutoff_utc",
            "season",
            "season_type",
            "week",
            "team_id",
            "lineage_sha256",
            "prior_games",
            "prior_win_rate",
            "prior_points_for_mean",
            "prior_points_against_mean",
            "missingness",
        ),
    },
    "pregame_prior_cells.parquet": {
        "rows": 22112,
        "sha256": "b581ebd3b4dea87edee886ff8d46b2a5dc40671fc226ed037f4c253f17704c61",
        "required_columns": (
            "cell_id",
            "row_id",
            "feature_name",
            "value",
            "lineage_sha256",
            "missingness",
        ),
    },
}
PREREQUISITE_IDENTITIES = {
    "BAT-398": {
        "path": "artifacts/pit/matrix_gate_decision.json",
        "sha256": "9f1755bba326678dee2e4daac92a693d8dc98ed9124805d5c53c88d12c5a1208",
        "decision": "BLOCK",
        "matrix_identity": "7c4b170a85d7aa8053bbbad099b8569cff6676580f18f46f375bbece8a53b3d1",
        "note": "Historical zero-row BAT-397 gate remains pinned. BAT-400 consumes BAT-523, not that empty matrix.",
    },
    "BAT-399": {
        "path": "artifacts/pit/leakage_battery_results.json",
        "artifact_identity": "2be6b713722382b2c0ea5e86f89a6e6ed57533bab3adbb0bc3cf3a77b46df13a",
        "status": "DONE",
        "downstream_eligibility": "READY",
    },
    "BAT-523": {
        "dataset_identity": DATASET_IDENTITY,
        "dataset_version": "bat523-known-at-replay-2010-2022-v2",
    },
    "BAT-526": {
        "path": "artifacts/governance/protected_split_exposure_audit.json",
        "artifact_identity": "c8667b02cd515f2689d3c298a58d00d25dbada254146a116187f9c488dc314e8",
        "classification": "HISTORICAL_PROTECTED_RESULT_EXPOSED_NO_SELECTION_OR_PROMOTION_AUTHORITY",
        "authority": "revoked_for_selection_tuning_threshold_promotion_and_protected_claims",
    },
}
AUTHORITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "decision_unit",
    "jira_key",
    "status",
    "remaining_blockers",
    "downstream_eligibility",
    "acceptance_matrix",
    "dataset_identity",
    "input_identities",
    "split_boundaries",
    "folds",
    "fold_membership_proof",
    "protected_outcomes_inaccessible",
    "protected_metrics_produced",
    "protected_evaluation_status",
    "claims",
    "development_label_status",
)
REQUIRED_ACCEPTANCE = (
    "chronological_advancement",
    "fold_local_fitting",
    "protected_accessor_denial",
    "target_game_exclusion",
    "stale_checkpoint_rejection",
    "crash_resume_equivalence",
    "deterministic_full_rerun",
    "future_append_invariance",
    "consumer_readiness_bat401",
)


class ProtectedOutcomeDenied(RuntimeError):
    """Raised when tuning code requests a protected-season outcome or metric."""


class DevelopmentLabelUnavailable(RuntimeError):
    """Raised when a 2023 tuning label is requested from BAT-523 outcomes."""


class CheckpointRejected(RuntimeError):
    """Raised when a checkpoint is stale, mismatched, or future-fitted."""


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_artifact_identity(payload: Mapping[str, Any]) -> str:
    mutable = dict(payload)
    mutable.pop("artifact_identity", None)
    return stable_hash(mutable)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _aware(value: object, key: str) -> datetime:
    parsed = parse_time(value) if not isinstance(value, datetime) else value
    if parsed is None:
        raise ValueError(f"{key} must be present")
    return parsed.astimezone(timezone.utc)


def _polars() -> Any:
    try:
        import polars
    except ModuleNotFoundError as exc:
        raise RuntimeError("polars is required to execute the BAT-400 walk-forward runner") from exc
    return polars


def resolve_data_root(explicit: Path | None, repo_root: Path) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    env = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "").strip()
    if env:
        candidates.append(Path(env))
    policy_path = repo_root / "configs" / "external_storage_policy.json"
    if policy_path.is_file():
        configured = str(_load_json(policy_path).get("current_host_data_root_windows") or "").strip()
        if configured:
            candidates.append(Path(configured))
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if not resolved.is_dir():
            continue
        try:
            resolved.relative_to(repo_root.resolve())
        except ValueError:
            return resolved
        raise ValueError(f"data root must be outside the repository: {resolved}")
    raise ValueError("unable to resolve an external data root")


def try_resolve_data_root(explicit: Path | None, repo_root: Path) -> Path | None:
    try:
        return resolve_data_root(explicit, repo_root)
    except ValueError:
        return None


def resolve_external_path(data_root: Path, raw_path: str) -> Path:
    marker = "<external-data-root>/"
    if not raw_path.startswith(marker):
        raise ValueError(f"external path must start with {marker}: {raw_path}")
    relative = raw_path[len(marker) :].replace("\\", "/")
    if not relative or relative.startswith("/") or ":" in relative.split("/", 1)[0]:
        raise ValueError(f"external path escapes the data root: {raw_path}")
    parts = Path(relative).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"external path traversal is rejected: {raw_path}")
    resolved = (data_root / relative).resolve()
    try:
        resolved.relative_to(data_root.resolve())
    except ValueError as exc:
        raise ValueError(f"external path escapes the data root: {raw_path}") from exc
    return resolved


def freeze_split_boundaries(repo_root: Path) -> dict[str, Any]:
    roles = {
        season: registry_role_for_season(repo_root, season)
        for season in (2010, 2022, 2023, 2024, 2025)
    }
    if roles[2023]["split_id"] != "SPLIT-DEV-SEL":
        raise ValueError("2023 must remain SPLIT-DEV-SEL")
    if roles[2024]["role"] != "PROTECTED_TEST" or roles[2025]["role"] != "PROTECTED_TEST":
        raise ValueError("2024-2025 must remain protected")
    if roles[2024]["tuning_allowed"] or roles[2025]["tuning_allowed"]:
        raise ValueError("protected seasons cannot allow tuning")
    return {
        "frozen_before_execution": True,
        "historical_development_inputs": "2010-2022",
        "development_fit_selection_calibration": 2023,
        "protected_inaccessible_to_tuning": [2024, 2025],
        "registry_unaltered": True,
        "roles": {
            str(season): {
                "split_id": roles[season]["split_id"],
                "role": roles[season]["role"],
                "tuning_allowed": roles[season]["tuning_allowed"],
                "threshold_setting_allowed": roles[season]["threshold_setting_allowed"],
                "protected_result_access": roles[season]["protected_result_access"],
            }
            for season in (2010, 2022, 2023, 2024, 2025)
        },
        "contaminated_bat526_metrics_authority": "REVOKED",
    }


@dataclass(frozen=True)
class FoldLocalTransform:
    means: dict[str, float]
    stds: dict[str, float]
    train_row_ids: tuple[str, ...]
    train_cutoff_utc: str
    kind: str

    @property
    def identity(self) -> str:
        return stable_hash(
            {
                "means": self.means,
                "stds": self.stds,
                "train_row_ids": list(self.train_row_ids),
                "train_cutoff_utc": self.train_cutoff_utc,
                "kind": self.kind,
            }
        )

    def transform_row(self, row: Mapping[str, Any]) -> dict[str, float | None]:
        values: dict[str, float | None] = {}
        for column in FEATURE_COLUMNS:
            raw = row[column]
            if raw is None:
                values[column] = None
                continue
            std = self.stds[column]
            values[column] = 0.0 if std == 0.0 else (float(raw) - self.means[column]) / std
        return values


def fit_fold_local_transform(
    train_rows: Sequence[Mapping[str, Any]],
    *,
    train_cutoff_utc: str,
) -> FoldLocalTransform:
    ids = tuple(str(row["row_id"]) for row in train_rows)
    if not train_rows:
        return FoldLocalTransform(
            means={column: 0.0 for column in FEATURE_COLUMNS},
            stds={column: 1.0 for column in FEATURE_COLUMNS},
            train_row_ids=ids,
            train_cutoff_utc=train_cutoff_utc,
            kind="IDENTITY_NO_PRIOR_FOLD_ROWS",
        )
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    for column in FEATURE_COLUMNS:
        values = [float(row[column]) for row in train_rows if row[column] is not None]
        if not values:
            means[column] = 0.0
            stds[column] = 1.0
            continue
        mean = sum(values) / float(len(values))
        variance = sum((value - mean) ** 2 for value in values) / float(len(values))
        means[column] = mean
        stds[column] = variance ** 0.5
    return FoldLocalTransform(
        means=means,
        stds=stds,
        train_row_ids=ids,
        train_cutoff_utc=train_cutoff_utc,
        kind="EXPANDING_WINDOW_STANDARDISER",
    )


class ProtectedOutcomeAccessor:
    """Tuning-facing outcome interface. Protected seasons cannot return labels."""

    def __init__(
        self,
        repo_root: Path,
        outcomes: Sequence[Mapping[str, Any]],
    ) -> None:
        self.repo_root = repo_root
        self._by_key: dict[tuple[int, str, str], dict[str, Any]] = {}
        for row in outcomes:
            season = int(row["season"])
            key = (season, str(row["canonical_game_id"]), str(row["team_id"]))
            self._by_key[key] = dict(row)

    def get_tuning_label(self, season: int, game_id: str, team_id: str) -> dict[str, Any]:
        season = int(season)
        if is_protected_canonical_season(self.repo_root, season):
            raise ProtectedOutcomeDenied(
                f"protected season {season} outcomes are inaccessible to tuning code"
            )
        if season != DEVELOPMENT_SEASON:
            raise DevelopmentLabelUnavailable(
                f"season {season} outcomes are historical inputs, not 2023 tuning labels"
            )
        row = self._by_key.get((season, str(game_id), str(team_id)))
        if row is None:
            raise DevelopmentLabelUnavailable(
                "2023 outcomes are absent from verified BAT-523 outcome payloads"
            )
        return {
            "season": season,
            "game_id": game_id,
            "team_id": team_id,
            "result": row["result"],
            "points_for": row["points_for"],
            "points_against": row["points_against"],
        }


class ProtectedFeatureView:
    """Exposes protected-period features without outcomes or metrics."""

    def __init__(self, rows: Sequence[Mapping[str, Any]]) -> None:
        self._rows = [dict(row) for row in rows]

    def features_for_season(self, season: int) -> list[dict[str, Any]]:
        season = int(season)
        if season not in PROTECTED_SEASONS:
            raise ValueError(f"{season} is not a protected feature season")
        exported: list[dict[str, Any]] = []
        for row in self._rows:
            if int(row["season"]) != season:
                continue
            exported.append(
                {
                    "row_id": row["row_id"],
                    "target_game_id": row["target_game_id"],
                    "cutoff_utc": row["cutoff_utc"],
                    "season": season,
                    "team_id": row["team_id"],
                    **{column: row[column] for column in FEATURE_COLUMNS},
                    "outcomes_included": False,
                    "metrics_included": False,
                }
            )
        if any("result" in item or "home_points" in item for item in exported):
            raise ProtectedOutcomeDenied("protected feature view leaked an outcome field")
        return exported


def load_verified_payloads(data_root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    if manifest.get("dataset_identity") != DATASET_IDENTITY:
        raise ValueError("BAT-523 manifest dataset identity mismatch")
    if str(manifest.get("dataset_version") or "") != "bat523-known-at-replay-2010-2022-v2":
        raise ValueError("unexpected BAT-523 dataset version")
    payload_rows = {row["name"]: row for row in manifest.get("payloads", [])}
    polars = _polars()
    frames: dict[str, Any] = {}
    identities: list[dict[str, Any]] = []
    for name, spec in REQUIRED_PAYLOADS.items():
        listed = payload_rows.get(name)
        if listed is None:
            raise ValueError(f"BAT-523 manifest missing {name}")
        path = resolve_external_path(data_root, str(listed["path"]))
        if not path.is_file():
            raise FileNotFoundError(f"missing BAT-523 payload: {path}")
        digest = sha256_file(path)
        if digest != spec["sha256"] or digest != listed["sha256"]:
            raise ValueError(f"SHA-256 mismatch for {name}")
        frame = polars.read_parquet(path)
        if frame.height != spec["rows"] or frame.height != int(listed["rows"]):
            raise ValueError(f"row-count mismatch for {name}")
        missing = [column for column in spec["required_columns"] if column not in frame.columns]
        if missing:
            raise ValueError(f"{name} missing columns: {missing}")
        frames[name] = frame
        identities.append(
            {
                "name": name,
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": digest,
                "rows": frame.height,
                "columns": list(frame.columns),
            }
        )
    return {"frames": frames, "identities": identities}


def _rows_from_frame(frame: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in frame.to_dicts()]


def build_folds(dev_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in dev_rows:
        if int(row["season"]) != DEVELOPMENT_SEASON:
            continue
        key = (str(row["season_type"]), int(row["week"]))
        grouped.setdefault(key, []).append(dict(row))
    folds: list[dict[str, Any]] = []
    for (season_type, week), rows in grouped.items():
        rows.sort(key=lambda item: (str(item["cutoff_utc"]), str(item["row_id"])))
        cutoffs = [_aware(item["cutoff_utc"], "cutoff_utc") for item in rows]
        folds.append(
            {
                "fold_id": f"2023-{season_type}-W{week:02d}",
                "season": DEVELOPMENT_SEASON,
                "season_type": season_type,
                "week": week,
                "min_cutoff_utc": min(cutoffs).isoformat().replace("+00:00", "Z"),
                "max_cutoff_utc": max(cutoffs).isoformat().replace("+00:00", "Z"),
                "rows": rows,
            }
        )
    folds.sort(key=lambda item: (item["min_cutoff_utc"], item["fold_id"]))
    for index, fold in enumerate(folds):
        fold["fold_index"] = index
        if index and fold["min_cutoff_utc"] < folds[index - 1]["max_cutoff_utc"]:
            # Same-day weeks may share a cutoff window; chronological order is by min cutoff then id.
            if fold["min_cutoff_utc"] < folds[index - 1]["min_cutoff_utc"]:
                raise ValueError("folds are not chronological")
    return folds


def _feature_hash(rows: Sequence[Mapping[str, Any]], transform: FoldLocalTransform) -> str:
    transformed = []
    for row in rows:
        transformed.append(
            {
                "row_id": row["row_id"],
                "values": transform.transform_row(row),
            }
        )
    return stable_hash(transformed)


def fold_membership(
    fold: Mapping[str, Any],
    prior_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Derive train/eval membership and same-game exclusion from observed rows."""

    eval_rows = list(fold["rows"])
    eval_game_ids = {str(row["target_game_id"]) for row in eval_rows}
    eval_row_ids = {str(row["row_id"]) for row in eval_rows}
    cutoff = str(fold["min_cutoff_utc"])
    train_rows: list[Mapping[str, Any]] = []
    excluded_candidates: list[dict[str, Any]] = []
    for row in prior_rows:
        row_id = str(row["row_id"])
        game_id = str(row["target_game_id"])
        row_cutoff = str(row["cutoff_utc"])
        reasons: list[str] = []
        if row_cutoff >= cutoff:
            reasons.append("CUTOFF_NOT_BEFORE_FOLD")
        if game_id in eval_game_ids:
            reasons.append("SAME_GAME_EXCLUDED")
        if row_id in eval_row_ids:
            reasons.append("SAME_ROW_EXCLUDED")
        if reasons:
            if "CUTOFF_NOT_BEFORE_FOLD" not in reasons:
                excluded_candidates.append(
                    {
                        "row_id": row_id,
                        "target_game_id": game_id,
                        "cutoff_utc": row_cutoff,
                        "reasons": reasons,
                    }
                )
            continue
        train_rows.append(row)
    train_rows.sort(key=lambda item: (str(item["cutoff_utc"]), str(item["row_id"])))
    excluded_candidates.sort(key=lambda item: (item["cutoff_utc"], item["row_id"]))
    train_membership = [
        {"row_id": str(row["row_id"]), "target_game_id": str(row["target_game_id"])} for row in train_rows
    ]
    eval_membership = [
        {"row_id": str(row["row_id"]), "target_game_id": str(row["target_game_id"])} for row in eval_rows
    ]
    proof = derive_membership_proof(train_membership, eval_membership)
    proof["excluded_candidates"] = excluded_candidates
    proof["same_game_excluded"] = (
        not proof["game_id_intersection"]
        and not proof["row_id_intersection"]
        and all("SAME_GAME_EXCLUDED" in item["reasons"] or "SAME_ROW_EXCLUDED" in item["reasons"] for item in excluded_candidates)
    )
    return {
        "train_rows": train_rows,
        "eval_rows": eval_rows,
        "train_membership": train_membership,
        "eval_membership": eval_membership,
        **proof,
    }


def derive_membership_proof(
    train_membership: Sequence[Mapping[str, Any]],
    eval_membership: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    train_games = {str(row["target_game_id"]) for row in train_membership}
    eval_games = {str(row["target_game_id"]) for row in eval_membership}
    train_ids = {str(row["row_id"]) for row in train_membership}
    eval_ids = {str(row["row_id"]) for row in eval_membership}
    game_intersection = sorted(train_games & eval_games)
    row_intersection = sorted(train_ids & eval_ids)
    return {
        "train_game_ids": sorted(train_games),
        "eval_game_ids": sorted(eval_games),
        "game_id_intersection": game_intersection,
        "row_id_intersection": row_intersection,
        "same_game_excluded": not game_intersection and not row_intersection,
        "train_membership_sha256": stable_hash(list(train_membership)),
        "eval_membership_sha256": stable_hash(list(eval_membership)),
    }


def execute_fold(
    fold: Mapping[str, Any],
    prior_rows: Sequence[Mapping[str, Any]],
    accessor: ProtectedOutcomeAccessor,
) -> dict[str, Any]:
    membership = fold_membership(fold, prior_rows)
    train_rows = membership["train_rows"]
    eval_rows = membership["eval_rows"]
    transform = fit_fold_local_transform(
        train_rows,
        train_cutoff_utc=fold["min_cutoff_utc"],
    )
    if list(transform.train_row_ids) != [row["row_id"] for row in membership["train_membership"]]:
        raise RuntimeError("transform fitting population drifted from derived train membership")
    denied_labels: list[str] = []
    for row in eval_rows:
        try:
            accessor.get_tuning_label(int(row["season"]), str(row["target_game_id"]), str(row["team_id"]))
            denied_labels.append("UNEXPECTED_LABEL")
        except (ProtectedOutcomeDenied, DevelopmentLabelUnavailable) as exc:
            denied_labels.append(type(exc).__name__)
    if any(item == "UNEXPECTED_LABEL" for item in denied_labels):
        raise RuntimeError("tuning interface returned a 2023/protected label that BAT-523 does not authorize")
    result = {
        "fold_id": fold["fold_id"],
        "fold_index": fold["fold_index"],
        "season": DEVELOPMENT_SEASON,
        "season_type": fold["season_type"],
        "week": fold["week"],
        "min_cutoff_utc": fold["min_cutoff_utc"],
        "max_cutoff_utc": fold["max_cutoff_utc"],
        "eval_row_count": len(eval_rows),
        "eval_row_ids": [str(row["row_id"]) for row in eval_rows],
        "eval_game_ids": list(membership["eval_game_ids"]),
        "train_row_count": len(train_rows),
        "train_row_ids": list(transform.train_row_ids),
        "train_game_ids": list(membership["train_game_ids"]),
        "membership": {
            "train": membership["train_membership"],
            "eval": membership["eval_membership"],
            "game_id_intersection": membership["game_id_intersection"],
            "row_id_intersection": membership["row_id_intersection"],
            "excluded_candidates": membership["excluded_candidates"],
            "train_membership_sha256": membership["train_membership_sha256"],
            "eval_membership_sha256": membership["eval_membership_sha256"],
        },
        "transform_kind": transform.kind,
        "transform_identity": transform.identity,
        "transform_means": transform.means,
        "eval_feature_hash": _feature_hash(eval_rows, transform),
        "tuning_labels_used": [],
        "development_metrics": None,
        "label_join_status": "ABSENT_FROM_VERIFIED_BAT523_OUTCOME_PAYLOADS",
        "label_denials": sorted(set(denied_labels)),
        "same_game_excluded": bool(membership["same_game_excluded"]),
    }
    result["fold_result_hash"] = stable_hash(
        {key: value for key, value in result.items() if key != "fold_result_hash"}
    )
    return result


def checkpoint_dir(data_root: Path, run_identity: str) -> Path:
    return data_root / "checkpoints" / "walk_forward" / run_identity


def write_checkpoint(directory: Path, payload: Mapping[str, Any]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"fold_{int(payload['fold_index']):02d}.json"
    encoded = canonical_json(payload)
    path.write_bytes(encoded)
    return path


def load_checkpoint(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_checkpoint(
    checkpoint: Mapping[str, Any],
    *,
    run_identity: str,
    dataset_identity: str,
    code_identity: str,
    fold: Mapping[str, Any],
) -> None:
    if checkpoint.get("schema_version") != CHECKPOINT_SCHEMA:
        raise CheckpointRejected("schema-incompatible checkpoint")
    if checkpoint.get("run_identity") != run_identity:
        raise CheckpointRejected("identity-mismatched checkpoint run")
    if checkpoint.get("dataset_identity") != dataset_identity:
        raise CheckpointRejected("identity-mismatched checkpoint dataset")
    if checkpoint.get("code_identity") != code_identity:
        raise CheckpointRejected("stale checkpoint code identity")
    if checkpoint.get("fold_id") != fold["fold_id"]:
        raise CheckpointRejected("checkpoint fold identity mismatch")
    if str(checkpoint.get("train_cutoff_utc")) > fold["min_cutoff_utc"]:
        raise CheckpointRejected("future-fitted checkpoint")
    if int(checkpoint.get("fold_index", -1)) != int(fold["fold_index"]):
        raise CheckpointRejected("checkpoint fold index mismatch")


def run_walk_forward(
    *,
    folds: Sequence[Mapping[str, Any]],
    prior_rows: Sequence[Mapping[str, Any]],
    accessor: ProtectedOutcomeAccessor,
    data_root: Path,
    run_identity: str,
    dataset_identity: str,
    code_identity: str,
    resume: bool = True,
    stop_after: int | None = None,
) -> list[dict[str, Any]]:
    directory = checkpoint_dir(data_root, run_identity)
    directory.mkdir(parents=True, exist_ok=True)
    completed: list[dict[str, Any]] = []
    for fold in folds:
        if stop_after is not None and int(fold["fold_index"]) >= stop_after:
            break
        path = directory / f"fold_{int(fold['fold_index']):02d}.json"
        if resume and path.is_file():
            checkpoint = load_checkpoint(path)
            validate_checkpoint(
                checkpoint,
                run_identity=run_identity,
                dataset_identity=dataset_identity,
                code_identity=code_identity,
                fold=fold,
            )
            completed.append(checkpoint["fold_result"])
            continue
        fold_result = execute_fold(fold, prior_rows, accessor)
        checkpoint = {
            "schema_version": CHECKPOINT_SCHEMA,
            "run_identity": run_identity,
            "dataset_identity": dataset_identity,
            "code_identity": code_identity,
            "fold_id": fold["fold_id"],
            "fold_index": fold["fold_index"],
            "train_cutoff_utc": fold["min_cutoff_utc"],
            "fold_result": fold_result,
        }
        write_checkpoint(directory, checkpoint)
        completed.append(fold_result)
    return completed


def prove_future_append_invariance(
    folds: Sequence[Mapping[str, Any]],
    prior_rows: Sequence[Mapping[str, Any]],
    accessor: ProtectedOutcomeAccessor,
    baseline: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    appended = list(prior_rows)
    last = folds[-1]
    appended.append(
        {
            **last["rows"][0],
            "row_id": "synthetic-future-append-row",
            "target_game_id": "synthetic-future-game",
            "cutoff_utc": "2099-12-31T00:00:00Z",
            "week": 99,
        }
    )
    mutated = [execute_fold(fold, appended, accessor) for fold in folds]
    unchanged = [
        before["fold_id"]
        for before, after in zip(baseline, mutated, strict=True)
        if before["fold_result_hash"] == after["fold_result_hash"]
        and before["eval_feature_hash"] == after["eval_feature_hash"]
    ]
    return {
        "mutation": "append synthetic row with cutoff 2099-12-31T00:00:00Z",
        "baseline_fold_hashes": [row["fold_result_hash"] for row in baseline],
        "mutated_fold_hashes": [row["fold_result_hash"] for row in mutated],
        "unchanged_fold_ids": unchanged,
        "pass": unchanged == [fold["fold_id"] for fold in folds],
    }


def prove_target_game_exclusion(
    fold: Mapping[str, Any],
    prior_rows: Sequence[Mapping[str, Any]],
    accessor: ProtectedOutcomeAccessor,
) -> dict[str, Any]:
    eval_game_ids = {str(row["target_game_id"]) for row in fold["rows"]}
    eval_row_ids = {str(row["row_id"]) for row in fold["rows"]}
    injected = list(prior_rows)
    victim = dict(fold["rows"][0])
    victim["row_id"] = "injected-same-game-prior"
    victim["cutoff_utc"] = "2010-01-01T00:00:00Z"
    injected.append(victim)
    result = execute_fold(fold, injected, accessor)
    train_row_ids = set(result["train_row_ids"])
    train_game_ids = set(result["train_game_ids"])
    leaked_rows = [row_id for row_id in train_row_ids if row_id == "injected-same-game-prior"]
    leaked_games = sorted(eval_game_ids & train_game_ids)
    leaked_row_ids = sorted(eval_row_ids & train_row_ids)
    excluded = result["membership"]["excluded_candidates"]
    injected_excluded = any(
        item["row_id"] == "injected-same-game-prior" and "SAME_GAME_EXCLUDED" in item["reasons"]
        for item in excluded
    )
    return {
        "mutation": "inject target-game row into earlier history",
        "eval_game_ids": sorted(eval_game_ids),
        "eval_row_ids": sorted(eval_row_ids),
        "train_game_ids": sorted(train_game_ids),
        "injected_row_id": "injected-same-game-prior",
        "leaked_train_row_ids": leaked_rows,
        "leaked_game_ids": leaked_games,
        "leaked_row_ids": leaked_row_ids,
        "injected_row_excluded": injected_excluded,
        "pass": (
            not leaked_rows
            and not leaked_games
            and not leaked_row_ids
            and injected_excluded
            and result["same_game_excluded"]
        ),
    }


def prove_stale_checkpoint_rejection(
    fold: Mapping[str, Any],
    *,
    run_identity: str,
    code_identity: str,
) -> dict[str, Any]:
    cases = {
        "schema": {"schema_version": "stale.v0"},
        "dataset": {"dataset_identity": "0" * 64},
        "code": {"code_identity": "1" * 64},
        "future_fitted": {"train_cutoff_utc": "2099-01-01T00:00:00Z"},
    }
    rejected: dict[str, str] = {}
    for name, override in cases.items():
        checkpoint = {
            "schema_version": CHECKPOINT_SCHEMA,
            "run_identity": run_identity,
            "dataset_identity": DATASET_IDENTITY,
            "code_identity": code_identity,
            "fold_id": fold["fold_id"],
            "fold_index": fold["fold_index"],
            "train_cutoff_utc": fold["min_cutoff_utc"],
            "fold_result": {},
        }
        checkpoint.update(override)
        try:
            validate_checkpoint(
                checkpoint,
                run_identity=run_identity,
                dataset_identity=DATASET_IDENTITY,
                code_identity=code_identity,
                fold=fold,
            )
            rejected[name] = "ACCEPTED"
        except CheckpointRejected as exc:
            rejected[name] = str(exc)
    return {
        "rejected": rejected,
        "pass": all(value != "ACCEPTED" for value in rejected.values()),
    }


def prove_protected_accessor_denial(
    accessor: ProtectedOutcomeAccessor,
    feature_view: ProtectedFeatureView,
    repo_root: Path,
) -> dict[str, Any]:
    denials: dict[str, str] = {}
    for season in sorted(PROTECTED_SEASONS):
        try:
            accessor.get_tuning_label(season, "any-game", "any-team")
            denials[str(season)] = "RETURNED_LABEL"
        except ProtectedOutcomeDenied as exc:
            denials[str(season)] = str(exc)
        features = feature_view.features_for_season(season)
        if any(item.get("outcomes_included") or item.get("metrics_included") for item in features):
            denials[f"{season}_features"] = "LEAKED_OUTCOME_OR_METRIC"
        else:
            denials[f"{season}_feature_rows"] = str(len(features))
        if not is_protected_canonical_season(repo_root, season):
            denials[f"{season}_registry"] = "NOT_PROTECTED"
    return {
        "denials": denials,
        "pass": all(
            value not in {"RETURNED_LABEL", "LEAKED_OUTCOME_OR_METRIC", "NOT_PROTECTED"}
            for key, value in denials.items()
            if not key.endswith("feature_rows")
        ),
    }


def derive_terminal_state(acceptance: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    failed = [row["criterion"] for row in acceptance if row["disposition"] != "PASS"]
    status = "DONE" if not failed else "BLOCKED"
    return {
        "status": status,
        "remaining_blockers": ["NONE"] if not failed else [f"ACCEPTANCE_FAILED:{name}" for name in failed],
        "bat401": "READY_FOR_GATE_REEVALUATION" if not failed else "BLOCKED",
    }


def consume_for_bat401(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "DEVELOPMENT_SAFE_REPLAY_DRY_RUN",
        "dataset_identity": DATASET_IDENTITY,
        "protected_outcomes_inaccessible": True,
        "protected_metrics_produced": False,
        "protected_evaluation_status": "CLOSED",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise ValueError(f"BAT-401 consumer rejected {key}")
    if payload.get("claims", {}).get("protected_performance"):
        raise ValueError("BAT-401 consumer rejected protected-performance claim")
    metrics = payload.get("development_metrics")
    if metrics not in (None, {}):
        if any(str(key).startswith(("2024", "2025")) for key in metrics):
            raise ValueError("BAT-401 consumer rejected protected metrics")
    if payload.get("artifact_identity") != compute_artifact_identity(payload):
        raise ValueError("BAT-401 consumer rejected stale artifact identity")
    return {
        "consumable": True,
        "manual_repair_required": False,
        "protected_lane_still_closed": True,
    }


def validate_fold_membership(fold: Mapping[str, Any]) -> dict[str, Any]:
    membership = fold.get("membership")
    if not isinstance(membership, Mapping):
        raise ValueError(f"{fold.get('fold_id')}: fold membership evidence is required")
    train = list(membership.get("train") or [])
    eval_rows = list(membership.get("eval") or [])
    if not eval_rows:
        raise ValueError(f"{fold.get('fold_id')}: evaluation membership cannot be empty")
    derived = derive_membership_proof(train, eval_rows)
    if membership.get("game_id_intersection") != derived["game_id_intersection"]:
        raise ValueError(f"{fold.get('fold_id')}: game-id intersection is not derived from membership")
    if membership.get("row_id_intersection") != derived["row_id_intersection"]:
        raise ValueError(f"{fold.get('fold_id')}: row-id intersection is not derived from membership")
    if membership.get("train_membership_sha256") != derived["train_membership_sha256"]:
        raise ValueError(f"{fold.get('fold_id')}: train membership hash is not derived")
    if membership.get("eval_membership_sha256") != derived["eval_membership_sha256"]:
        raise ValueError(f"{fold.get('fold_id')}: eval membership hash is not derived")
    if fold.get("same_game_excluded") is not derived["same_game_excluded"]:
        raise ValueError(f"{fold.get('fold_id')}: same_game_excluded is not derived from observed sets")
    if derived["game_id_intersection"] or derived["row_id_intersection"]:
        raise ValueError(f"{fold.get('fold_id')}: train/eval membership leaked a game or row identity")
    if fold.get("eval_row_count") != len(eval_rows) or fold.get("train_row_count") != len(train):
        raise ValueError(f"{fold.get('fold_id')}: row counts are not derived from membership")
    eval_ids = fold.get("eval_row_ids")
    train_ids = fold.get("train_row_ids")
    if isinstance(eval_ids, Mapping) and eval_ids.get("count") != len(eval_rows):
        raise ValueError(f"{fold.get('fold_id')}: bounded eval row identity count mismatch")
    if isinstance(train_ids, Mapping) and train_ids.get("count") != len(train):
        raise ValueError(f"{fold.get('fold_id')}: bounded train row identity count mismatch")
    if isinstance(eval_ids, Mapping) and eval_ids.get("sha256") != stable_hash([row["row_id"] for row in eval_rows]):
        raise ValueError(f"{fold.get('fold_id')}: bounded eval row identity hash mismatch")
    if isinstance(train_ids, Mapping) and train_ids.get("sha256") != stable_hash([row["row_id"] for row in train]):
        raise ValueError(f"{fold.get('fold_id')}: bounded train row identity hash mismatch")
    eval_games = fold.get("eval_game_ids")
    if isinstance(eval_games, Mapping) and eval_games.get("sha256") != stable_hash(derived["eval_game_ids"]):
        raise ValueError(f"{fold.get('fold_id')}: bounded eval game identity hash mismatch")
    if fold.get("train_game_ids") not in (None, derived["train_game_ids"]) and fold.get("train_game_ids") != derived["train_game_ids"]:
        if isinstance(fold.get("train_game_ids"), Mapping):
            if fold["train_game_ids"].get("sha256") != stable_hash(derived["train_game_ids"]):
                raise ValueError(f"{fold.get('fold_id')}: bounded train game identity hash mismatch")
        else:
            raise ValueError(f"{fold.get('fold_id')}: train game IDs are not derived from membership")
    excluded = membership.get("excluded_candidates") or []
    for item in excluded:
        if not item.get("reasons"):
            raise ValueError(f"{fold.get('fold_id')}: excluded candidate missing reasons")
        if "SAME_GAME_EXCLUDED" not in item["reasons"] and "SAME_ROW_EXCLUDED" not in item["reasons"]:
            raise ValueError(f"{fold.get('fold_id')}: excluded candidate lacks a same-game or same-row reason")
    return derived


def rebuild_expected_fold_authority(
    repo_root: Path,
    *,
    data_root: Path | None = None,
) -> list[dict[str, Any]]:
    resolved_root = resolve_data_root(data_root, repo_root)
    manifest = _load_json(resolved_root / MANIFEST_RELATIVE)
    loaded = load_verified_payloads(resolved_root, manifest)
    frames = loaded["frames"]
    prior_rows = _rows_from_frame(frames["pregame_prior_rows.parquet"])
    outcomes = _rows_from_frame(frames["team_outcome_observations.parquet"])
    if any(int(row["season"]) in PROTECTED_SEASONS for row in outcomes):
        raise ProtectedOutcomeDenied("BAT-523 outcome payload unexpectedly contains protected seasons")
    if any(int(row["season"]) == DEVELOPMENT_SEASON for row in outcomes):
        raise RuntimeError("unexpected 2023 outcomes in BAT-523; refuse to silently consume them without a new identity")
    accessor = ProtectedOutcomeAccessor(repo_root, outcomes)
    dev_rows = [row for row in prior_rows if int(row["season"]) == DEVELOPMENT_SEASON]
    folds = build_folds(dev_rows)
    return [execute_fold(fold, dev_rows, accessor) for fold in folds]


def validate_walk_forward_artifact(
    payload: Mapping[str, Any],
    repo_root: Path,
    *,
    expected_folds: Sequence[Mapping[str, Any]] | None = None,
    require_payload_rebuild: bool = False,
) -> None:
    missing = [field for field in AUTHORITY_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"missing authority fields: {missing}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected walk-forward schema")
    if payload.get("dataset_identity") != DATASET_IDENTITY:
        raise ValueError("dataset identity mismatch")
    if payload.get("artifact_identity") != compute_artifact_identity(payload):
        raise ValueError("artifact_identity does not match canonical payload")
    if payload.get("protected_outcomes_inaccessible") is not True:
        raise ValueError("protected outcomes must be inaccessible")
    if payload.get("protected_metrics_produced") is not False:
        raise ValueError("protected metrics must not be produced")
    if payload.get("protected_evaluation_status") != "CLOSED":
        raise ValueError("protected evaluation must remain closed")
    claims = payload.get("claims") or {}
    for key in (
        "protected_performance",
        "production_readiness",
        "champion_selection",
        "feature_promotion",
    ):
        if claims.get(key) is not False:
            raise ValueError(f"claim {key} must be false")
    folds = payload.get("folds") or []
    if not folds:
        raise ValueError("folds are required")
    cutoffs = [str(fold["min_cutoff_utc"]) for fold in folds]
    if cutoffs != sorted(cutoffs):
        raise ValueError("folds are not chronological")
    membership_proofs: list[dict[str, Any]] = []
    for previous, current in zip([None, *folds[:-1]], folds):
        derived = validate_fold_membership(current)
        membership_proofs.append(derived)
        if previous is not None:
            if current["transform_identity"] == previous["transform_identity"] and current["train_row_count"]:
                if current["train_row_ids"] != previous["train_row_ids"]:
                    raise ValueError("fold-local transform identity ignored changed history")
        if current.get("development_metrics") not in (None, {}):
            raise ValueError("fold produced unauthorized development outcome metrics")
        if current.get("tuning_labels_used") != []:
            raise ValueError("fold used tuning labels")
        if current.get("label_join_status") != "ABSENT_FROM_VERIFIED_BAT523_OUTCOME_PAYLOADS":
            raise ValueError("fold consumed a development or protected label")
        if int(current.get("season") or 0) in PROTECTED_SEASONS:
            raise ValueError("fold accessed a protected-year outcome")
    expected_proof = {
        "fold_count": len(folds),
        "eval_row_count": sum(int(fold["eval_row_count"]) for fold in folds),
        "same_game_excluded": all(fold.get("same_game_excluded") is True for fold in folds),
        "game_id_intersections": [fold["membership"]["game_id_intersection"] for fold in folds],
        "row_id_intersections": [fold["membership"]["row_id_intersection"] for fold in folds],
        "train_membership_sha256": [fold["membership"]["train_membership_sha256"] for fold in folds],
        "eval_membership_sha256": [fold["membership"]["eval_membership_sha256"] for fold in folds],
    }
    if payload.get("fold_membership_proof") != expected_proof:
        raise ValueError("fold_membership_proof is not derived from fold membership")
    acceptance = payload.get("acceptance_matrix") or []
    names = [row["criterion"] for row in acceptance]
    if names != list(REQUIRED_ACCEPTANCE):
        raise ValueError("acceptance matrix does not match required criteria")
    derived = derive_terminal_state(acceptance)
    if payload.get("status") != derived["status"]:
        raise ValueError("status is not bound to acceptance dispositions")
    if payload.get("remaining_blockers") != derived["remaining_blockers"]:
        raise ValueError("remaining_blockers are not bound to acceptance dispositions")
    eligibility = payload.get("downstream_eligibility") or {}
    if eligibility.get("BAT-401") != derived["bat401"]:
        raise ValueError("BAT-401 eligibility is not bound to acceptance dispositions")
    identities = payload.get("input_identities") or {}
    if identities.get("dataset_identity") != DATASET_IDENTITY:
        raise ValueError("input identities lost dataset binding")
    payloads = {row["name"]: row for row in identities.get("payloads", [])}
    for name, spec in REQUIRED_PAYLOADS.items():
        row = payloads.get(name)
        if row is None:
            raise ValueError(f"missing payload identity {name}")
        if row.get("sha256") != spec["sha256"] or row.get("rows") != spec["rows"]:
            raise ValueError(f"payload identity mismatch for {name}")
    consume_for_bat401(payload)
    freeze_split_boundaries(repo_root)
    rebuilt = expected_folds
    if rebuilt is None:
        data_root = try_resolve_data_root(None, repo_root)
        if data_root is None:
            if require_payload_rebuild:
                raise ValueError("independent payload reconstruction requires an external BAT-523 data root")
        else:
            rebuilt = rebuild_expected_fold_authority(repo_root, data_root=data_root)
    if rebuilt is not None:
        if len(rebuilt) != len(folds):
            raise ValueError("independently rebuilt fold count does not match the artifact")
        for actual, expected in zip(folds, rebuilt, strict=True):
            expected_bound = bound_fold_for_repository(expected)
            for field in (
                "fold_id",
                "min_cutoff_utc",
                "max_cutoff_utc",
                "eval_row_count",
                "train_row_count",
                "transform_kind",
                "transform_identity",
                "eval_feature_hash",
                "same_game_excluded",
                "membership",
            ):
                if actual.get(field) != expected_bound.get(field):
                    raise ValueError(f"{actual.get('fold_id')}: {field} does not match independent reconstruction")
            if payload.get("checkpointing", {}).get("schema_version") != CHECKPOINT_SCHEMA:
                raise ValueError("checkpoint schema is stale")
            if payload.get("proofs", {}).get("stale_checkpoint_rejection", {}).get("pass") is not True:
                raise ValueError("stale-checkpoint rejection proof is missing")


def bound_fold_for_repository(fold: Mapping[str, Any]) -> dict[str, Any]:
    """Keep bounded row/game summaries while retaining raw membership proof."""

    eval_ids = list(fold.get("eval_row_ids") or [])
    train_ids = list(fold.get("train_row_ids") or [])
    train_games = list(fold.get("train_game_ids") or [])
    eval_games = list(fold.get("eval_game_ids") or [])
    slim = dict(fold)
    slim["eval_row_ids"] = {
        "count": len(eval_ids),
        "head": eval_ids[:3],
        "tail": eval_ids[-3:],
        "sha256": stable_hash(eval_ids),
    }
    slim["train_row_ids"] = {
        "count": len(train_ids),
        "head": train_ids[:3],
        "tail": train_ids[-3:],
        "sha256": stable_hash(train_ids),
    }
    slim["eval_game_ids"] = {
        "count": len(eval_games),
        "sha256": stable_hash(eval_games),
    }
    slim["train_game_ids"] = {
        "count": len(train_games),
        "sha256": stable_hash(train_games),
    }
    return slim


def build_dry_run_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    folds_results: Sequence[Mapping[str, Any]],
    proofs: Mapping[str, Any],
    input_identities: Mapping[str, Any],
    split_boundaries: Mapping[str, Any],
    run_identity: str,
    code_identity: str,
    checkpoint_root: Path,
    resume_hashes: Mapping[str, Any],
) -> dict[str, Any]:
    acceptance = [
        {
            "criterion": name,
            "disposition": "PASS" if proofs[name]["pass"] else "FAIL",
            "evidence": name,
        }
        for name in REQUIRED_ACCEPTANCE
    ]
    derived = derive_terminal_state(acceptance)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "DEVELOPMENT_SAFE_REPLAY_DRY_RUN",
        "decision_unit": "POST-SUBTASK-050",
        "jira_key": "BAT-400",
        "historical_filename_note": (
            "Filename protected_replay_dry_run.json is historical. "
            "Protected outcomes were inaccessible and no protected metrics were produced."
        ),
        "dataset_identity": DATASET_IDENTITY,
        "run_identity": run_identity,
        "code_identity": code_identity,
        "input_identities": dict(input_identities),
        "prerequisite_identities": PREREQUISITE_IDENTITIES,
        "split_boundaries": dict(split_boundaries),
        "protected_outcomes_inaccessible": True,
        "protected_metrics_produced": False,
        "protected_evaluation_status": "CLOSED",
        "development_label_status": "ABSENT_FROM_VERIFIED_BAT523_OUTCOME_PAYLOADS",
        "development_metrics": None,
        "claims": {
            "protected_performance": False,
            "production_readiness": False,
            "champion_selection": False,
            "feature_promotion": False,
        },
        "negative_findings": [
            "BAT-523 outcome payloads contain 2010-2022 only; 2023 tuning labels cannot be joined.",
            "No 2023 outcome-based development metric was produced.",
            "2024-2025 feature rows were isolated behind a no-outcome accessor.",
            "BAT-526 2024/2025 metric comparisons have no selection or promotion authority.",
            "Protected evaluation remains closed; no replacement protected period was defined.",
        ],
        "folds": [bound_fold_for_repository(fold) for fold in folds_results],
        "fold_membership_proof": {
            "fold_count": len(folds_results),
            "eval_row_count": sum(int(fold["eval_row_count"]) for fold in folds_results),
            "same_game_excluded": all(fold.get("same_game_excluded") is True for fold in folds_results),
            "game_id_intersections": [fold["membership"]["game_id_intersection"] for fold in folds_results],
            "row_id_intersections": [fold["membership"]["row_id_intersection"] for fold in folds_results],
            "train_membership_sha256": [fold["membership"]["train_membership_sha256"] for fold in folds_results],
            "eval_membership_sha256": [fold["membership"]["eval_membership_sha256"] for fold in folds_results],
        },
        "checkpointing": {
            "root": str(checkpoint_root),
            "schema_version": CHECKPOINT_SCHEMA,
            "durable_external": True,
            "idempotent_resume": True,
            "fold_files": [f"fold_{index:02d}.json" for index in range(len(folds_results))],
        },
        "resume_evidence": dict(resume_hashes),
        "proofs": dict(proofs),
        "acceptance_matrix": acceptance,
        "status": derived["status"],
        "remaining_blockers": derived["remaining_blockers"],
        "downstream_eligibility": {
            "BAT-401": derived["bat401"],
            "reason": (
                "Development-safe dry run completed. Protected evaluation remains closed "
                "and BAT-401 must reevaluate the protected lane without republishing protected metrics."
            ),
        },
        "environment": {
            "data_root": str(data_root),
            "repo_root": str(repo_root),
        },
    }
    payload["artifact_identity"] = compute_artifact_identity(payload)
    return payload


def execute_dry_run(
    *,
    repo_root: Path,
    data_root: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    resolved_root = resolve_data_root(data_root, repo_root)
    split_boundaries = freeze_split_boundaries(repo_root)
    manifest_path = resolved_root / MANIFEST_RELATIVE
    manifest = _load_json(manifest_path)
    loaded = load_verified_payloads(resolved_root, manifest)
    frames = loaded["frames"]
    prior_rows = _rows_from_frame(frames["pregame_prior_rows.parquet"])
    outcomes = _rows_from_frame(frames["team_outcome_observations.parquet"])
    if any(int(row["season"]) in PROTECTED_SEASONS for row in outcomes):
        raise ProtectedOutcomeDenied("BAT-523 outcome payload unexpectedly contains protected seasons")
    if any(int(row["season"]) == DEVELOPMENT_SEASON for row in outcomes):
        raise RuntimeError("unexpected 2023 outcomes in BAT-523; refuse to silently consume them without a new identity")
    accessor = ProtectedOutcomeAccessor(repo_root, outcomes)
    feature_view = ProtectedFeatureView(prior_rows)
    dev_rows = [row for row in prior_rows if int(row["season"]) == DEVELOPMENT_SEASON]
    if len(dev_rows) != 1820:
        raise ValueError(f"expected 1820 2023 development rows, found {len(dev_rows)}")
    folds = build_folds(dev_rows)
    code_identity = sha256_file(Path(__file__))
    run_identity = stable_hash(
        {
            "dataset_identity": DATASET_IDENTITY,
            "code_identity": code_identity,
            "split_boundaries": split_boundaries,
            "runner": "walk_forward.v2",
        }
    )
    full_dir = checkpoint_dir(resolved_root, run_identity)
    if full_dir.exists():
        for stale in full_dir.glob("fold_*.json"):
            stale.unlink()
    full_results = run_walk_forward(
        folds=folds,
        prior_rows=dev_rows,
        accessor=accessor,
        data_root=resolved_root,
        run_identity=run_identity,
        dataset_identity=DATASET_IDENTITY,
        code_identity=code_identity,
        resume=False,
    )
    rerun_results = run_walk_forward(
        folds=folds,
        prior_rows=dev_rows,
        accessor=accessor,
        data_root=resolved_root,
        run_identity=run_identity,
        dataset_identity=DATASET_IDENTITY,
        code_identity=code_identity,
        resume=False,
    )
    crash_identity = run_identity + "-crash"
    crash_dir = checkpoint_dir(resolved_root, crash_identity)
    if crash_dir.exists():
        for stale in crash_dir.glob("fold_*.json"):
            stale.unlink()
    partial = run_walk_forward(
        folds=folds,
        prior_rows=dev_rows,
        accessor=accessor,
        data_root=resolved_root,
        run_identity=crash_identity,
        dataset_identity=DATASET_IDENTITY,
        code_identity=code_identity,
        resume=False,
        stop_after=2,
    )
    resumed = run_walk_forward(
        folds=folds,
        prior_rows=dev_rows,
        accessor=accessor,
        data_root=resolved_root,
        run_identity=crash_identity,
        dataset_identity=DATASET_IDENTITY,
        code_identity=code_identity,
        resume=True,
    )
    proofs = {
        "chronological_advancement": {
            "pass": [row["min_cutoff_utc"] for row in full_results]
            == sorted(row["min_cutoff_utc"] for row in full_results),
            "fold_ids": [row["fold_id"] for row in full_results],
            "min_cutoffs": [row["min_cutoff_utc"] for row in full_results],
        },
        "fold_local_fitting": {
            "pass": all(
                (index == 0 and row["transform_kind"] == "IDENTITY_NO_PRIOR_FOLD_ROWS")
                or (index > 0 and row["train_row_count"] > 0 and row["transform_kind"] == "EXPANDING_WINDOW_STANDARDISER")
                for index, row in enumerate(full_results)
            )
            and len({row["transform_identity"] for row in full_results}) == len(full_results),
            "transform_identities": [row["transform_identity"] for row in full_results],
        },
        "protected_accessor_denial": prove_protected_accessor_denial(accessor, feature_view, repo_root),
        "target_game_exclusion": prove_target_game_exclusion(folds[3], dev_rows, accessor),
        "stale_checkpoint_rejection": prove_stale_checkpoint_rejection(
            folds[0],
            run_identity=run_identity,
            code_identity=code_identity,
        ),
        "crash_resume_equivalence": {
            "pass": [row["fold_result_hash"] for row in resumed]
            == [row["fold_result_hash"] for row in full_results]
            and len(partial) == 2,
            "partial_folds": len(partial),
            "resumed_hashes": [row["fold_result_hash"] for row in resumed],
            "full_hashes": [row["fold_result_hash"] for row in full_results],
        },
        "deterministic_full_rerun": {
            "pass": [row["fold_result_hash"] for row in rerun_results]
            == [row["fold_result_hash"] for row in full_results],
            "first": [row["fold_result_hash"] for row in full_results],
            "second": [row["fold_result_hash"] for row in rerun_results],
        },
        "future_append_invariance": prove_future_append_invariance(
            folds,
            dev_rows,
            accessor,
            full_results,
        ),
        "consumer_readiness_bat401": {"pass": False},
    }
    artifact = build_dry_run_artifact(
        repo_root=repo_root,
        data_root=resolved_root,
        folds_results=full_results,
        proofs=proofs,
        input_identities={
            "dataset_identity": DATASET_IDENTITY,
            "manifest_path": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "payloads": loaded["identities"],
            "prerequisites": PREREQUISITE_IDENTITIES,
        },
        split_boundaries=split_boundaries,
        run_identity=run_identity,
        code_identity=code_identity,
        checkpoint_root=full_dir,
        resume_hashes=proofs["crash_resume_equivalence"],
    )
    proofs["consumer_readiness_bat401"] = {
        "pass": consume_for_bat401(artifact)["consumable"],
        "consumer": consume_for_bat401(artifact),
    }
    artifact = build_dry_run_artifact(
        repo_root=repo_root,
        data_root=resolved_root,
        folds_results=full_results,
        proofs=proofs,
        input_identities=artifact["input_identities"],
        split_boundaries=split_boundaries,
        run_identity=run_identity,
        code_identity=code_identity,
        checkpoint_root=full_dir,
        resume_hashes=proofs["crash_resume_equivalence"],
    )
    validate_walk_forward_artifact(artifact, repo_root)
    destination = output_path or (repo_root / "artifacts" / "pit" / "protected_replay_dry_run.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical_json(artifact) + b"\n")
    return artifact
