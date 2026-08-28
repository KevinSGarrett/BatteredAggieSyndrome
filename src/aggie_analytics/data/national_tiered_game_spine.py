from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    canonical_json_bytes,
    manifest_authoritative_sha256,
    sha256_file,
    stable_hash,
)

# Tiered national game, outcome, and team-observation spine for 1963-2023.
#
# Chronology and authority are preserved, never flattened. Protected 2024/2025
# rows carry no label and no team observation, and 2026 outcomes are absent by
# construction rather than by filtering.

SCHEMA_VERSION = "aggie.data.national_tiered_game_spine.v1"
CONTRACT_RELATIVE = "configs/national_tiered_game_spine_contract.json"
CONTRACT_ID = "BAT-652-NATIONAL-TIERED-GAME-SPINE-1963-2023-V1"
GATE_RELATIVE = "artifacts/data_lake/national_tiered_game_spine_gate.json"
PASS_RESULT = "PASS_NATIONAL_TIERED_SPINE_REFERENCE_CANDIDATE_ONLY"
CLASSIFICATION = "NATIONAL_TIERED_GAME_OUTCOME_AND_TEAM_OBSERVATION_SPINE_CANDIDATE"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"

NON_AUTHORITATIVE_MANIFEST_KEYS = frozenset({"issued_at_utc", "producer"})

GAME_MEMBERSHIP_FIELDS = (
    "canonical_game_id",
    "tier_id",
    "season",
    "season_type",
    "week",
    "neutral_site",
    "conference_game",
    "venue_id",
    "home_canonical_team_id",
    "away_canonical_team_id",
    "start_date_utc_text",
    "start_time_tbd",
    "completed",
    "label_eligible",
    "label_ineligible_reason",
)

TEAM_OBSERVATION_FIELDS = (
    "canonical_game_id",
    "canonical_team_id",
    "opponent_canonical_team_id",
    "tier_id",
    "season",
    "week",
    "is_home",
    "is_neutral_site",
)

OUTCOME_LABEL_FIELDS = (
    "canonical_game_id",
    "canonical_team_id",
    "tier_id",
    "season",
    "points_for",
    "points_against",
    "margin",
    "label_win",
    "label_tie",
)

TEAM_ALIAS_FIELDS = ("canonical_team_id", "source_team_id", "source_team_name", "observed_seasons")

GATE_IDENTITY_FIELDS = (
    "artifact_type",
    "authority",
    "classification",
    "contract_id",
    "contract_sha256",
    "cross_check",
    "dataset_identity",
    "decision_unit",
    "jira_key",
    "label_policy",
    "manifest",
    "parent_jira_key",
    "payloads",
    "population",
    "protected_lane",
    "result",
    "schema_version",
    "scientific_nonclaims",
    "source_identities",
    "tiers",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _require_file(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing pinned input: {path}")
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"pinned input SHA-256 drift: {path}")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({field: gate[field] for field in GATE_IDENTITY_FIELDS})


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = _read_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("national tiered spine contract identity drift")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("national tiered spine schema drift")
    if contract.get("protected_lane") != PROTECTED_LANE:
        raise ValueError("protected lane must remain blocked")
    authority = contract["authority"]
    if authority.get("national_tiered_spine_use") is not True:
        raise ValueError("national tiered spine authority is not enabled")
    for key in (
        "historical_pit_admission",
        "pregame_feature_use",
        "protected_training_admission",
        "protected_evaluation_admission",
        "champion_or_production_promotion",
        "protected_performance_claims",
        "forecast_publication",
        "immutable_raw_capture_mutation",
        "canonical_entity_mutation",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"national tiered spine authority is open: {key}")
    policy = contract["label_policy"]
    if policy.get("capture_timestamp_treated_as_publication_time") is not False:
        raise ValueError("capture timestamp must never be treated as publication time")
    if policy.get("target_game_outcome_use_admitted") is not False:
        raise ValueError("target-game outcome use must remain closed")
    if contract["team_observation_policy"].get("observations_per_labeled_game") != 2:
        raise ValueError("a labeled game must carry exactly two team observations")
    return contract


def resolve_tier(season: int, tiers: Iterable[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for tier in tiers:
        low, high = tier["season_range"]
        if int(low) <= season <= int(high):
            return tier
    return None


def canonical_team_id(source_id: str, source_team_id: int) -> str:
    return f"{source_id}:TEAM:{source_team_id}"


def _load_foundation_rows(data_root: Path, gate: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    entry = next(item for item in gate["payloads"] if item["name"] == name)
    manifest = _read_json(data_root / gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    path = data_root / located["relative_path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise ValueError(f"foundation payload hash drift: {name}")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    contract_bytes = (repo_root / CONTRACT_RELATIVE).read_bytes()
    source = contract["source_contract"]
    tiers = contract["tiers"]

    foundation_gate_path = repo_root / source["foundation_gate_relative_path"]
    _require_file(foundation_gate_path, source["foundation_gate_sha256"])
    foundation_gate = _read_json(foundation_gate_path)
    if foundation_gate["dataset_identity"] != source["foundation_dataset_identity"]:
        raise ValueError("foundation dataset identity drift")

    games = _load_foundation_rows(data_root, foundation_gate, "national_normalized_games.jsonl")
    outcomes = {
        row["canonical_game_id"]: row
        for row in _load_foundation_rows(
            data_root, foundation_gate, "national_game_outcome_labels.jsonl"
        )
    }

    membership: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    alias_seasons: defaultdict[tuple[str, int, str], set[int]] = defaultdict(set)
    tier_population: defaultdict[str, Counter[str]] = defaultdict(Counter)
    ineligible_reasons: Counter[str] = Counter()

    for row in games:
        season = int(row["season"])
        tier = resolve_tier(season, tiers)
        if tier is None:
            raise ValueError(f"season {season} falls outside the declared tier vocabulary")
        tier_id = tier["tier_id"]
        game_id = row["canonical_game_id"]
        source_id = row["source_id"]
        home_id = row["home_team_source_id"]
        away_id = row["away_team_source_id"]
        home_canonical = canonical_team_id(source_id, home_id) if home_id is not None else None
        away_canonical = canonical_team_id(source_id, away_id) if away_id is not None else None

        outcome = outcomes.get(game_id)
        reason: str | None = None
        if not bool(tier["label_eligible"]):
            reason = "TIER_NOT_LABEL_ELIGIBLE"
        elif not bool(row["completed"]):
            reason = "NOT_COMPLETED"
        elif outcome is None:
            reason = "NO_OUTCOME_RECORD"
        elif not bool(outcome["outcome_reference_eligible"]):
            reason = "OUTCOME_NOT_REFERENCE_ELIGIBLE"
        elif home_canonical is None or away_canonical is None:
            reason = "UNRESOLVED_TEAM_IDENTITY"
        label_eligible = reason is None
        if reason is not None:
            ineligible_reasons[reason] += 1

        membership.append(
            {
                "canonical_game_id": game_id,
                "tier_id": tier_id,
                "season": season,
                "season_type": row["season_type"],
                "week": row["week"],
                "neutral_site": row["neutral_site"],
                "conference_game": row["conference_game"],
                "venue_id": row["venue_id"],
                "home_canonical_team_id": home_canonical,
                "away_canonical_team_id": away_canonical,
                "start_date_utc_text": row["start_date_utc_text"],
                "start_time_tbd": row["start_time_tbd"],
                "completed": bool(row["completed"]),
                "label_eligible": label_eligible,
                "label_ineligible_reason": reason,
            }
        )
        tier_population[tier_id]["games"] += 1
        if label_eligible:
            tier_population[tier_id]["label_eligible_games"] += 1

        for source_team_id, name in (
            (home_id, row["home_team_name"]),
            (away_id, row["away_team_name"]),
        ):
            if source_team_id is not None:
                alias_seasons[
                    (canonical_team_id(source_id, source_team_id), source_team_id, name)
                ].add(season)

        if not label_eligible:
            continue

        assert home_canonical is not None and away_canonical is not None
        home_points = int(outcome["home_points"])
        away_points = int(outcome["away_points"])
        for canonical, opponent, is_home, points_for, points_against in (
            (home_canonical, away_canonical, True, home_points, away_points),
            (away_canonical, home_canonical, False, away_points, home_points),
        ):
            observations.append(
                {
                    "canonical_game_id": game_id,
                    "canonical_team_id": canonical,
                    "opponent_canonical_team_id": opponent,
                    "tier_id": tier_id,
                    "season": season,
                    "week": row["week"],
                    "is_home": is_home,
                    "is_neutral_site": bool(row["neutral_site"]),
                }
            )
            labels.append(
                {
                    "canonical_game_id": game_id,
                    "canonical_team_id": canonical,
                    "tier_id": tier_id,
                    "season": season,
                    "points_for": points_for,
                    "points_against": points_against,
                    "margin": points_for - points_against,
                    "label_win": points_for > points_against,
                    "label_tie": points_for == points_against,
                }
            )
        tier_population[tier_id]["team_observations"] += 2

    membership.sort(key=lambda item: (item["season"], item["canonical_game_id"]))
    observations.sort(
        key=lambda item: (item["season"], item["canonical_game_id"], not item["is_home"])
    )
    labels.sort(
        key=lambda item: (item["season"], item["canonical_game_id"], item["canonical_team_id"])
    )
    aliases = sorted(
        (
            {
                "canonical_team_id": canonical,
                "source_team_id": source_team_id,
                "source_team_name": name,
                "observed_seasons": sorted(seasons),
            }
            for (canonical, source_team_id, name), seasons in alias_seasons.items()
        ),
        key=lambda item: (item["canonical_team_id"], item["source_team_name"]),
    )

    _assert_structural_invariants(membership, observations, labels)

    population = _population(
        membership=membership,
        observations=observations,
        labels=labels,
        aliases=aliases,
        tiers=tiers,
        tier_population=tier_population,
        ineligible_reasons=ineligible_reasons,
    )
    cross_check = _cross_check(repo_root=repo_root, contract=contract, population=population)

    record_hashes = {
        "game_membership": stable_hash(membership),
        "team_observations": stable_hash(observations),
        "outcome_labels": stable_hash(labels),
        "team_aliases": stable_hash(aliases),
    }
    module_path = Path(__file__).resolve()
    dataset_identity = stable_hash(
        {
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "builder_sha256": sha256_file(module_path),
            "foundation_dataset_identity": source["foundation_dataset_identity"],
            "record_hashes": record_hashes,
            "classification": CLASSIFICATION,
        }
    )

    return {
        "contract": contract,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "code_identity": sha256_file(module_path),
        "dataset_identity": dataset_identity,
        "record_hashes": record_hashes,
        "population": population,
        "cross_check": cross_check,
        "membership": membership,
        "observations": observations,
        "labels": labels,
        "aliases": aliases,
    }


def _assert_structural_invariants(
    membership: list[Mapping[str, Any]],
    observations: list[Mapping[str, Any]],
    labels: list[Mapping[str, Any]],
) -> None:
    """Fail closed on duplicates, broken orientation, and same-game leakage."""
    game_ids = [row["canonical_game_id"] for row in membership]
    if len(game_ids) != len(set(game_ids)):
        raise ValueError("duplicate canonical game membership rows")

    by_game: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in observations:
        by_game[row["canonical_game_id"]].append(row)
    for game_id, rows in by_game.items():
        if len(rows) != 2:
            raise ValueError(f"game {game_id} does not carry exactly two team observations")
        first, second = rows
        if first["is_home"] == second["is_home"]:
            raise ValueError(f"game {game_id} has non-complementary home/away orientation")
        if first["canonical_team_id"] == second["canonical_team_id"]:
            raise ValueError(f"game {game_id} observes the same team twice")
        if first["canonical_team_id"] != second["opponent_canonical_team_id"]:
            raise ValueError(f"game {game_id} has an inconsistent opponent reference")
        if second["canonical_team_id"] != first["opponent_canonical_team_id"]:
            raise ValueError(f"game {game_id} has an inconsistent opponent reference")

    label_keys = {(row["canonical_game_id"], row["canonical_team_id"]) for row in labels}
    observation_keys = {
        (row["canonical_game_id"], row["canonical_team_id"]) for row in observations
    }
    if label_keys != observation_keys:
        raise ValueError("outcome labels and team observations do not cover the same identities")
    if len(label_keys) != len(labels):
        raise ValueError("duplicate game-team outcome labels")

    # A pregame observation row must never carry a postgame quantity.
    postgame = {"points_for", "points_against", "margin", "label_win", "label_tie", "completed"}
    for row in observations:
        leaked = postgame & set(row)
        if leaked:
            raise ValueError(f"team observation carries postgame fields: {sorted(leaked)}")

    for row in labels:
        margin = int(row["points_for"]) - int(row["points_against"])
        if int(row["margin"]) != margin:
            raise ValueError("label margin is inconsistent with its own scores")
        if bool(row["label_win"]) != (margin > 0) or bool(row["label_tie"]) != (margin == 0):
            raise ValueError("label outcome flags are inconsistent with the margin")


def _population(
    *,
    membership: list[Mapping[str, Any]],
    observations: list[Mapping[str, Any]],
    labels: list[Mapping[str, Any]],
    aliases: list[Mapping[str, Any]],
    tiers: Iterable[Mapping[str, Any]],
    tier_population: Mapping[str, Counter[str]],
    ineligible_reasons: Counter[str],
) -> dict[str, Any]:
    by_tier = {}
    for tier in tiers:
        counts = tier_population.get(tier["tier_id"], Counter())
        by_tier[tier["tier_id"]] = {
            "season_range": list(tier["season_range"]),
            "label_eligible_tier": bool(tier["label_eligible"]),
            "games": int(counts.get("games", 0)),
            "label_eligible_games": int(counts.get("label_eligible_games", 0)),
            "team_observations": int(counts.get("team_observations", 0)),
        }
    seasons = sorted({row["season"] for row in membership})
    ties = sum(1 for row in labels if row["label_tie"])
    return {
        "games_total": len(membership),
        "label_eligible_games_total": sum(1 for row in membership if row["label_eligible"]),
        "team_observations_total": len(observations),
        "outcome_label_rows_total": len(labels),
        "team_alias_rows": len(aliases),
        "distinct_canonical_teams": len({row["canonical_team_id"] for row in aliases}),
        "tie_label_rows": ties,
        "seasons": seasons,
        "season_range": [seasons[0], seasons[-1]] if seasons else [],
        "by_tier": by_tier,
        "label_ineligible_reasons": dict(sorted(ineligible_reasons.items())),
    }


def _cross_check(
    *, repo_root: Path, contract: Mapping[str, Any], population: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare recomputed tier counts with predecessor gates. Disagreement is reported, not hidden."""
    authorities = contract["cross_check_authorities"]
    replay = _read_json(repo_root / authorities["replay_gate_relative_path"])["coverage"]
    development = _read_json(repo_root / authorities["development_2023_gate_relative_path"])[
        "population"
    ]
    historical = _read_json(repo_root / authorities["historical_spine_gate_relative_path"])[
        "population"
    ]
    by_tier = population["by_tier"]

    def compare(recomputed: int, declared: int) -> dict[str, Any]:
        return {
            "recomputed": int(recomputed),
            "predecessor_declared": int(declared),
            "agrees": int(recomputed) == int(declared),
            "difference": int(recomputed) - int(declared),
        }

    historical_reconciliation = _read_json(
        repo_root / authorities["historical_spine_gate_relative_path"]
    )["reconciliation"]
    tier_1 = by_tier["TIER_1_LONG_RUN_REFERENCE_CANDIDATE"]["label_eligible_games"]
    supplement_only = int(historical_reconciliation["supplement_only_final_rows"])

    return {
        "tier_1_completed_outcomes_vs_bat552": compare(
            tier_1, historical["completed_outcomes"]
        ),
        "tier_1_cfbd_only_rows_vs_bat552": compare(tier_1, historical["cfbd_rows"]),
        "tier_1_gap_explained_by_supplement_only_rows": {
            "recomputed_plus_supplement_only": tier_1 + supplement_only,
            "predecessor_completed_outcomes": int(historical["completed_outcomes"]),
            "explained": tier_1 + supplement_only == int(historical["completed_outcomes"]),
            "explanation": (
                "This spine consumes the CFBD GAME-grain route only. BAT-552 additionally fused "
                "SportsDataverse supplement-only final rows, which accounts for the whole gap."
            ),
        },
        "tier_1_ties_vs_bat552": compare(
            population["tie_label_rows"] // 2, historical["ties"]
        ),
        "tier_2_games_vs_bat523_replay": compare(
            by_tier["TIER_2_ACCEPTED_SCOPED_REPLAY"]["label_eligible_games"],
            replay["accepted_strict_game_outcomes"],
        ),
        "tier_2_team_observations_vs_bat523_replay": compare(
            by_tier["TIER_2_ACCEPTED_SCOPED_REPLAY"]["team_observations"],
            replay["accepted_team_observations"],
        ),
        "tier_3_games_vs_bat565_development": compare(
            by_tier["TIER_3_DEVELOPMENT_ONLY_LABELS"]["label_eligible_games"],
            development["accepted_games"],
        ),
        "tier_3_team_observations_vs_bat565_development": compare(
            by_tier["TIER_3_DEVELOPMENT_ONLY_LABELS"]["team_observations"],
            development["team_observations"],
        ),
        "tier_2_scope_difference": {
            "predecessor_source_candidate_rows": int(replay["source_candidate_rows"]),
            "predecessor_quarantined_reconciliation_rows": int(
                replay["quarantined_reconciliation_rows"]
            ),
            "predecessor_held_repository_versioned_single_source": int(
                replay["held_repository_versioned_single_source"]
            ),
            "explained": False,
            "explanation": (
                "BAT-523 applied a stricter cross-source acceptance rule to a different candidate "
                "population, quarantining and holding rows this spine accepts on the CFBD route. "
                "The residual difference is not fully attributable to a single declared quantity "
                "and is recorded as an open scope difference rather than reconciled away."
            ),
        },
        "interpretation": (
            "Counts are independently recomputed from the Phase 2 normalized foundation. "
            "Predecessor gates were built from different source routes and acceptance rules, "
            "so agreement is evidence and disagreement is a recorded finding, not an error to "
            "be silently reconciled."
        ),
        "reconciliation_is_reported_not_enforced": True,
    }


def build_gate(
    *,
    expected: Mapping[str, Any],
    manifest_entry: Mapping[str, Any],
    payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    contract = expected["contract"]
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_TIERED_GAME_SPINE_GATE",
        "contract_id": CONTRACT_ID,
        "contract_sha256": expected["contract_sha256"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "parent_jira_key": contract["parent_jira_key"],
        "classification": CLASSIFICATION,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "dataset_identity": expected["dataset_identity"],
        "manifest": dict(manifest_entry),
        "payloads": payloads,
        "population": expected["population"],
        "tiers": contract["tiers"],
        "label_policy": contract["label_policy"],
        "cross_check": expected["cross_check"],
        "source_identities": {
            "foundation_gate_sha256": contract["source_contract"]["foundation_gate_sha256"],
            "foundation_dataset_identity": contract["source_contract"][
                "foundation_dataset_identity"
            ],
        },
        "authority": contract["authority"],
        "scientific_nonclaims": {
            "historical_population_ready": False,
            "gap_002_resolved": False,
            "production_model_ready": False,
            "trained_production_champion": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_result_claimed": False,
        },
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    gate["binding_identity"] = binding_identity(gate, "binding_identity")
    return gate


def materialize(*, data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    identity = expected["dataset_identity"]
    canonical_root = data_root / "canonical" / "national_tiered_game_spine" / "sha256" / identity
    manifest_root = data_root / "manifests" / "national_tiered_game_spine" / "sha256" / identity

    written = [
        ("national_game_membership.jsonl", "NATIONAL_CANONICAL_GAME_MEMBERSHIP", expected["membership"]),
        ("national_team_observations.jsonl", "NATIONAL_PREGAME_TEAM_OBSERVATIONS", expected["observations"]),
        ("national_team_outcome_labels.jsonl", "NATIONAL_TEAM_OUTCOME_LABELS", expected["labels"]),
        ("national_team_source_aliases.jsonl", "NATIONAL_TEAM_SOURCE_ALIASES", expected["aliases"]),
    ]
    payloads: list[dict[str, Any]] = []
    for name, role, rows in written:
        payload_bytes = _jsonl_bytes(rows)
        path = canonical_root / name
        _write_bytes(path, payload_bytes)
        payloads.append(
            {
                "name": name,
                "role": role,
                "relative_path": _relative(path, data_root),
                "rows": len(rows),
                "bytes": len(payload_bytes),
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_TIERED_GAME_SPINE_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "classification": CLASSIFICATION,
        "population": expected["population"],
        "cross_check": expected["cross_check"],
        "record_hashes": expected["record_hashes"],
        "payloads": payloads,
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "code_identity": expected["code_identity"],
            "contract_sha256": expected["contract_sha256"],
        },
    }
    manifest_path = manifest_root / "national_tiered_game_spine_manifest.json"
    _write_bytes(manifest_path, canonical_json_bytes(manifest) + b"\n")

    manifest_entry = {
        "relative_path": _relative(manifest_path, data_root),
        "authoritative_sha256": manifest_authoritative_sha256(manifest),
    }
    gate_payloads = [
        {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256")} for item in payloads
    ]
    gate = build_gate(expected=expected, manifest_entry=manifest_entry, payloads=gate_payloads)
    _write_bytes(repo_root / GATE_RELATIVE, canonical_json_bytes(gate) + b"\n")
    return {"gate": gate, "manifest": manifest, "expected": expected}


def _compare(path: str, actual: Any, expected: Any, errors: list[str]) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            errors.append(f"{path}: expected object")
            return
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                errors.append(f"{path}.{key}: unexpected key")
            elif key not in actual:
                errors.append(f"{path}.{key}: missing key")
            else:
                _compare(f"{path}.{key}", actual[key], expected[key], errors)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            errors.append(f"{path}: list shape mismatch")
            return
        for index, (left, right) in enumerate(zip(actual, expected)):
            _compare(f"{path}[{index}]", left, right, errors)
        return
    if actual != expected:
        errors.append(f"{path}: {actual!r} != {expected!r}")


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    gate = dict(gate if gate is not None else _read_json(repo_root / GATE_RELATIVE))
    if gate.get("result") != PASS_RESULT:
        raise ValueError(f"national tiered spine gate is not passing: {gate.get('result')}")
    if gate.get("protected_lane") != PROTECTED_LANE:
        raise ValueError("national tiered spine gate opened the protected lane")
    for key, value in gate.get("scientific_nonclaims", {}).items():
        if value is not False:
            raise ValueError(f"national tiered spine gate asserted a forbidden claim: {key}")

    tiers = {tier["tier_id"]: tier for tier in gate.get("tiers", [])}
    by_tier = gate.get("population", {}).get("by_tier", {})
    for tier_id, tier in tiers.items():
        if bool(tier["label_eligible"]):
            continue
        counts = by_tier.get(tier_id, {})
        if counts.get("label_eligible_games") or counts.get("team_observations"):
            raise ValueError(f"sealed or prospective tier carries labels: {tier_id}")
    if not require_rebuild:
        return {"result": "PASS", "mode": "SCHEMA_ONLY", "gate_identity": gate.get("gate_identity")}

    if expected is None:
        expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    manifest_path = data_root / gate["manifest"]["relative_path"]
    manifest = dict(manifest if manifest is not None else _read_json(manifest_path))

    errors: list[str] = []
    if gate["dataset_identity"] != expected["dataset_identity"]:
        errors.append("dataset identity drift")
    _compare("population", gate["population"], expected["population"], errors)
    _compare("cross_check", gate["cross_check"], expected["cross_check"], errors)
    _compare(
        "manifest.record_hashes", manifest.get("record_hashes"), expected["record_hashes"], errors
    )
    if manifest_authoritative_sha256(manifest) != gate["manifest"].get("authoritative_sha256"):
        errors.append("manifest authoritative content drift")

    for payload in gate["payloads"]:
        entry = next(
            (item for item in manifest.get("payloads", []) if item["name"] == payload["name"]), None
        )
        if entry is None:
            errors.append(f"payload missing from manifest: {payload['name']}")
            continue
        for key in ("rows", "bytes", "sha256", "role"):
            if entry[key] != payload[key]:
                errors.append(f"payload {payload['name']} {key} drift")
        path = data_root / entry["relative_path"]
        if not path.is_file():
            errors.append(f"payload absent on disk: {entry['relative_path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"payload rehash drift: {entry['relative_path']}")

    if compute_gate_identity(gate) != gate.get("gate_identity"):
        errors.append("gate identity does not match its own identity-bearing fields")
    if binding_identity(gate, "binding_identity") != gate.get("binding_identity"):
        errors.append("cross-surface binding identity drift")

    if errors:
        raise ValueError("independent national spine validation failed: " + "; ".join(errors[:16]))
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD",
        "dataset_identity": gate["dataset_identity"],
        "gate_identity": gate["gate_identity"],
    }
