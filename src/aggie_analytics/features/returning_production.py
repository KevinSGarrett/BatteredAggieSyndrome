from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


PAIR_FIELDS = {
    ("interceptions", "INT"): "defensive_interceptions_returning_share",
    ("passing", "YDS"): "passing_yards_returning_share",
    ("receiving", "REC"): "receptions_returning_share",
    ("receiving", "YDS"): "receiving_yards_returning_share",
    ("rushing", "CAR"): "rushing_carries_returning_share",
    ("rushing", "YDS"): "rushing_yards_returning_share",
}

BOUNDED_COUNT_PAIRS = {
    ("interceptions", "INT"),
    ("receiving", "REC"),
    ("rushing", "CAR"),
}


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
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError(
            "returning-production research requires the optional data-engineering environment"
        ) from exc
    return polars


def safe_share(numerator: int | float, denominator: int | float) -> float | None:
    if denominator <= 0:
        return None
    value = float(numerator) / float(denominator)
    if value < 0.0 or value > 1.0:
        raise ValueError("returning-production share is outside [0, 1]")
    return value


def signed_ratio(numerator: int | float, denominator: int | float) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def _max_known_at(values: Iterable[str | None]) -> str | None:
    present = [str(value) for value in values if value is not None]
    return max(present) if present else None


def calculate_transition_records(
    roster_rows: Iterable[Mapping[str, Any]],
    metric_rows: Iterable[Mapping[str, Any]],
    transition_seasons: Iterable[int],
    classification: str,
    partial_prior_seasons: set[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rosters: dict[tuple[int, str], set[str]] = {}
    roster_known_at: dict[tuple[int, str], list[str | None]] = {}
    team_labels: dict[str, str] = {}
    for row in roster_rows:
        key = (int(row["season"]), str(row["canonical_team_id"]))
        rosters.setdefault(key, set()).add(str(row["canonical_player_id"]))
        roster_known_at.setdefault(key, []).append(row.get("source_known_at_utc"))
        if row.get("canonical_team_label"):
            team_labels[key[1]] = str(row["canonical_team_label"])

    player_metrics: dict[tuple[int, str, str, str, str], int] = {}
    metric_known_at: dict[tuple[int, str], list[str | None]] = {}
    metric_teams: dict[int, set[str]] = {}
    for row in metric_rows:
        season = int(row["season"])
        team_id = str(row["canonical_team_id"])
        pair = (str(row["category"]), str(row["stat_type"]))
        if pair not in PAIR_FIELDS:
            raise ValueError(f"unexpected player metric category/stat pair: {pair}")
        key = (
            season,
            team_id,
            str(row["canonical_player_id"]),
            pair[0],
            pair[1],
        )
        player_metrics[key] = player_metrics.get(key, 0) + int(row["source_value"])
        metric_known_at.setdefault((season, team_id), []).append(
            row.get("source_known_at_utc")
        )
        metric_teams.setdefault(season, set()).add(team_id)
        if row.get("canonical_team_label"):
            team_labels[team_id] = str(row["canonical_team_label"])

    metrics_by_team: dict[tuple[int, str], list[tuple[str, str, str, int]]] = {}
    for (season, team_id, player_id, category, stat_type), value in player_metrics.items():
        metrics_by_team.setdefault((season, team_id), []).append(
            (player_id, category, stat_type, value)
        )

    features: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for target_season in sorted(int(value) for value in transition_seasons):
        prior_season = target_season - 1
        prior_teams = {team for season, team in rosters if season == prior_season}
        current_teams = {team for season, team in rosters if season == target_season}
        source_metric_teams = metric_teams.get(prior_season, set())
        common_teams = sorted(prior_teams & current_teams & source_metric_teams)
        component_count = 0
        missing_pairs = 0
        signed_ratios_outside_unit_interval = 0
        for team_id in common_teams:
            prior_players = rosters[(prior_season, team_id)]
            current_players = rosters[(target_season, team_id)]
            returning_players = prior_players & current_players
            departed_players = prior_players - current_players
            arrival_players = current_players - prior_players
            union_players = prior_players | current_players
            feature: dict[str, Any] = {
                "classification": classification,
                "prior_season": prior_season,
                "target_season": target_season,
                "canonical_team_id": team_id,
                "canonical_team_label": team_labels.get(team_id),
                "prior_roster_count": len(prior_players),
                "current_roster_count": len(current_players),
                "returning_roster_count": len(returning_players),
                "departed_roster_count": len(departed_players),
                "arrival_roster_count": len(arrival_players),
                "roster_retention_rate": safe_share(
                    len(returning_players), len(prior_players)
                ),
                "roster_arrival_rate": safe_share(
                    len(arrival_players), len(current_players)
                ),
                "roster_jaccard": safe_share(
                    len(returning_players), len(union_players)
                ),
                "partial_prior_metric_season": prior_season in partial_prior_seasons,
                "source_known_at_utc": _max_known_at(
                    roster_known_at[(prior_season, team_id)]
                    + roster_known_at[(target_season, team_id)]
                    + metric_known_at[(prior_season, team_id)]
                ),
                "original_transition_time_pit_eligible": False,
                "target_game_feature_eligible": False,
                "protected_eligible": False,
            }
            grouped: dict[tuple[str, str], list[tuple[str, int]]] = {}
            for player_id, category, stat_type, value in metrics_by_team[
                (prior_season, team_id)
            ]:
                grouped.setdefault((category, stat_type), []).append((player_id, value))
            for pair, field_name in sorted(PAIR_FIELDS.items()):
                values = grouped.get(pair, [])
                if not values:
                    feature[field_name] = None
                    missing_pairs += 1
                    continue
                prior_total = sum(value for _, value in values)
                returning_total = sum(
                    value for player_id, value in values if player_id in returning_players
                )
                ratio_semantics = (
                    "BOUNDED_NONNEGATIVE_COUNT_SHARE"
                    if pair in BOUNDED_COUNT_PAIRS
                    else "SIGNED_EVENT_SUM_RATIO"
                )
                returning_share = (
                    safe_share(returning_total, prior_total)
                    if pair in BOUNDED_COUNT_PAIRS
                    else signed_ratio(returning_total, prior_total)
                )
                outside_unit_interval = bool(
                    returning_share is not None
                    and (returning_share < 0.0 or returning_share > 1.0)
                )
                if outside_unit_interval:
                    signed_ratios_outside_unit_interval += 1
                feature[field_name] = returning_share
                component = {
                    "classification": classification,
                    "prior_season": prior_season,
                    "target_season": target_season,
                    "canonical_team_id": team_id,
                    "category": pair[0],
                    "stat_type": pair[1],
                    "prior_total": prior_total,
                    "returning_total": returning_total,
                    "returning_share": returning_share,
                    "ratio_semantics": ratio_semantics,
                    "outside_unit_interval": outside_unit_interval,
                    "prior_metric_players": len({player_id for player_id, _ in values}),
                    "returning_metric_players": len(
                        {player_id for player_id, _ in values if player_id in returning_players}
                    ),
                    "partial_prior_metric_season": prior_season
                    in partial_prior_seasons,
                    "source_known_at_utc": feature["source_known_at_utc"],
                    "target_game_feature_eligible": False,
                    "protected_eligible": False,
                }
                component["component_identity"] = stable_hash(component)
                components.append(component)
                component_count += 1
            feature["feature_identity"] = stable_hash(feature)
            features.append(feature)
        coverage.append(
            {
                "classification": classification,
                "prior_season": prior_season,
                "target_season": target_season,
                "prior_roster_teams": len(prior_teams),
                "current_roster_teams": len(current_teams),
                "prior_metric_teams": len(source_metric_teams),
                "common_support_teams": len(common_teams),
                "excluded_prior_current_roster_teams_without_metrics": len(
                    (prior_teams & current_teams) - source_metric_teams
                ),
                "component_rows": component_count,
                "missing_category_stat_cells": missing_pairs,
                "signed_ratios_outside_unit_interval": signed_ratios_outside_unit_interval,
                "partial_prior_metric_season": prior_season in partial_prior_seasons,
                "target_game_feature_eligible": False,
                "protected_eligible": False,
            }
        )
    features.sort(key=lambda row: (row["target_season"], row["canonical_team_id"]))
    components.sort(
        key=lambda row: (
            row["target_season"],
            row["canonical_team_id"],
            row["category"],
            row["stat_type"],
        )
    )
    return features, components, coverage


def _write_parquet(records: list[dict[str, Any]], path: Path, sort_by: list[str]) -> dict[str, Any]:
    pl = _polars()
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.DataFrame(records).sort(sort_by)
    frame.write_parquet(path, compression="zstd", statistics=True)
    return {
        "path": path.name,
        "rows": frame.height,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def materialize(
    *, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str
) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / "retrospective_returning_production_contract.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    implementation_paths = {
        "feature_module": Path(__file__).resolve(),
        "builder": repo_root / "tools" / "build_retrospective_returning_production.py",
        "validator": repo_root / "tools" / "validate_retrospective_returning_production.py",
    }
    code_identities = {
        name: {
            "repo_relative_path": str(path.relative_to(repo_root)).replace("\\", "/"),
            "sha256": sha256_file(path),
        }
        for name, path in implementation_paths.items()
    }
    source = contract["source_contract"]
    pinned = {
        "roster_manifest": (
            source["roster_manifest_relative_path"],
            source["roster_manifest_sha256"],
        ),
        "roster_payload": (
            source["roster_payload_relative_path"],
            source["roster_payload_sha256"],
        ),
        "player_metric_manifest": (
            source["player_metric_manifest_relative_path"],
            source["player_metric_manifest_sha256"],
        ),
        "player_metric_payload": (
            source["player_metric_payload_relative_path"],
            source["player_metric_payload_sha256"],
        ),
    }
    verified: dict[str, dict[str, Any]] = {}
    for name, (relative, expected_sha) in pinned.items():
        path = input_data_root / relative
        if not path.is_file() or sha256_file(path) != expected_sha:
            raise ValueError(f"pinned returning-production source drift: {name}")
        verified[name] = {
            "relative_path": relative,
            "sha256": expected_sha,
            "bytes": path.stat().st_size,
        }
    roster = pl.read_parquet(input_data_root / source["roster_payload_relative_path"])
    metrics = pl.read_parquet(input_data_root / source["player_metric_payload_relative_path"])
    required_roster = {
        "season",
        "canonical_team_id",
        "canonical_team_label",
        "canonical_player_id",
        "source_known_at_utc",
        "season_roster_membership",
        "protected_eligible",
    }
    required_metrics = {
        "season",
        "canonical_team_id",
        "canonical_team_label",
        "canonical_player_id",
        "category",
        "stat_type",
        "source_value",
        "source_known_at_utc",
        "protected_eligible",
    }
    if not required_roster.issubset(roster.columns):
        raise ValueError("roster source schema is incomplete")
    if not required_metrics.issubset(metrics.columns):
        raise ValueError("player metric source schema is incomplete")
    if roster.filter(pl.col("protected_eligible") != False).height:  # noqa: E712
        raise ValueError("roster source unexpectedly claims protected eligibility")
    if metrics.filter(pl.col("protected_eligible") != False).height:  # noqa: E712
        raise ValueError("player metric source unexpectedly claims protected eligibility")
    roster = roster.filter(pl.col("season_roster_membership") == True).unique(  # noqa: E712
        ["season", "canonical_team_id", "canonical_player_id"]
    )
    metric_pairs = {
        (str(row["category"]), str(row["stat_type"]))
        for row in metrics.select("category", "stat_type").unique().to_dicts()
    }
    if metric_pairs != set(PAIR_FIELDS):
        raise ValueError("player metric category/stat population drift")
    features, components, coverage = calculate_transition_records(
        roster.to_dicts(),
        metrics.to_dicts(),
        contract["population_contract"]["transition_seasons"],
        contract["classification"],
        set(source["partial_player_metric_seasons"]),
    )
    acceptance = contract["acceptance"]
    if len(coverage) != acceptance["expected_transition_seasons"]:
        raise ValueError("transition season count drift")
    if min(row["common_support_teams"] for row in coverage) < acceptance[
        "minimum_common_teams_per_transition"
    ]:
        raise ValueError("common-support team coverage below predeclared floor")
    if len({(row["target_season"], row["canonical_team_id"]) for row in features}) != len(
        features
    ):
        raise ValueError("duplicate team-transition feature row")
    signed_ratio_anomalies = sum(
        row["signed_ratios_outside_unit_interval"] for row in coverage
    )
    if signed_ratio_anomalies != acceptance[
        "expected_signed_yardage_ratios_outside_zero_one"
    ]:
        raise ValueError("signed-yardage ratio diagnostic count drift")
    identity_payload = {
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "code_identities": code_identities,
        "source_identities": {
            "roster": source["roster_dataset_identity"],
            "player_metric": source["player_metric_dataset_identity"],
        },
        "verified_sources": verified,
        "features": features,
        "components": components,
        "coverage": coverage,
    }
    dataset_identity = stable_hash(identity_payload)
    feature_root = (
        output_data_root
        / "features"
        / "returning_production_research"
        / "sha256"
        / dataset_identity
    )
    manifest_root = (
        output_data_root
        / "manifests"
        / "returning_production_research"
        / "sha256"
        / dataset_identity
    )
    feature_path = feature_root / "team_season_transition_features.parquet"
    component_path = feature_root / "returning_production_components.parquet"
    coverage_path = feature_root / "transition_coverage.parquet"
    payloads = [
        {
            "role": "TEAM_TRANSITION_FEATURE_RESEARCH",
            **_write_parquet(
                features,
                feature_path,
                ["target_season", "canonical_team_id"],
            ),
        },
        {
            "role": "RETURNING_PRODUCTION_COMPONENTS",
            **_write_parquet(
                components,
                component_path,
                ["target_season", "canonical_team_id", "category", "stat_type"],
            ),
        },
        {
            "role": "TRANSITION_COVERAGE",
            **_write_parquet(coverage, coverage_path, ["target_season"]),
        },
    ]
    for payload in payloads:
        payload["path"] = (
            f"features/returning_production_research/sha256/{dataset_identity}/"
            + payload["path"]
        )
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "RETROSPECTIVE_RETURNING_PRODUCTION_RESEARCH",
        "dataset_identity": dataset_identity,
        "issued_at_utc": issued_at_utc,
        "decision_unit": contract["decision_unit"],
        "parent_unit": contract["parent_unit"],
        "classification": contract["classification"],
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "code_identities": code_identities,
        "source_identities": {
            "roster": source["roster_dataset_identity"],
            "player_metric": source["player_metric_dataset_identity"],
        },
        "verified_sources": verified,
        "payloads": payloads,
        "population": {
            "feature_rows": len(features),
            "component_rows": len(components),
            "transition_rows": len(coverage),
            "target_seasons": [row["target_season"] for row in coverage],
            "common_support_teams_by_transition": {
                str(row["target_season"]): row["common_support_teams"]
                for row in coverage
            },
            "partial_prior_metric_seasons": source["partial_player_metric_seasons"],
            "missing_category_stat_cells": sum(
                row["missing_category_stat_cells"] for row in coverage
            ),
            "signed_yardage_ratios_outside_zero_one": signed_ratio_anomalies,
        },
        "feature_fields": list(PAIR_FIELDS.values()),
        "unsupported_fields": contract["feature_contract"]["unsupported_fields"],
        "authority": contract["authority"],
        "protected_nonclaims": contract["protected_nonclaims"],
        "limitations": [
            "The source was captured in May 2023, so these transitions are retrospective research and not original-transition point-in-time evidence.",
            "The 2020 player metric source is partial; the 2020-to-2021 transition remains explicitly partial.",
            "Roster membership does not establish starts, depth, snaps, availability, eligibility, or game participation.",
            "No shared-snap, target-game, training, protected, production, or forecast authority is granted.",
        ],
    }
    manifest_root.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_root / "run_manifest.json"
    manifest_path.write_bytes(canonical_json(manifest) + b"\n")
    return {
        "dataset_identity": dataset_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "payloads": payloads,
        "population": manifest["population"],
        "manifest": manifest,
    }
