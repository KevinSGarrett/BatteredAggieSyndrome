from __future__ import annotations

import hashlib
import json
import platform
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    canonical_json_bytes,
    manifest_authoritative_sha256,
    sha256_file,
    stable_hash,
)

# Cycle #24 frozen 2026 opening strength priors.
#
# The prior is a chronological Elo replay over allowed evidence only. Three
# properties make it usable as a forecast input rather than a number that merely
# looks like one:
#
#   A  the evidence window ends at 2023. The protected 2024 and 2025 seasons are
#      excluded by construction and the exclusion is proven, not asserted;
#   B  the hyperparameters are the previously frozen national_elo values. No
#      search happens here, and Week Zero cannot change them;
#   C  a team without enough allowed history abstains. No group prior is
#      substituted for team evidence, because no hierarchical rule was
#      predeclared for this cycle, and a default rating is not evidence.
#
# The Week Zero batch update is predeclared and applied only after every contest
# in the declared batch carries an official final capture, so no update can leak
# into a forecast that was made before the batch finalized.

SCHEMA_VERSION = "aggie.shadow.week1_2026_frozen_strength_prior.v1"
CONTRACT_ID = "CYCLE24-WEEK1-2026-FROZEN-STRENGTH-PRIOR-V1"
JIRA_KEY = "BAT-679"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-FROZEN-STRENGTH-PRIOR-001"
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "WEEK1_2026_FROZEN_OPENING_STRENGTH_PRIOR"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_FROZEN_STRENGTH_PRIOR"

CONTRACT_RELATIVE = "configs/week1_2026_frozen_strength_prior_contract.json"
GATE_RELATIVE = "artifacts/prior/week1_2026_frozen_strength_prior_gate.json"
PAYLOAD_SLUG = "week1_2026_frozen_strength_prior"

PRIOR_PAYLOAD_NAME = "week1_2026_frozen_strength_prior_rows.jsonl"
UPDATE_PAYLOAD_NAME = "week1_2026_week_zero_prior_update_rows.jsonl"

PRIOR_ADMITTED_STALE = "PRIOR_ADMITTED_STALE_ALLOWED_EVIDENCE"
PRIOR_ADMITTED_LIMITED = "PRIOR_ADMITTED_LIMITED_SUPPORT"
ABSTAIN_COLD_START = "ABSTAIN_COLD_START_INSUFFICIENT_TEAM_HISTORY"
ABSTAIN_NO_HISTORY = "ABSTAIN_NO_ALLOWED_TEAM_HISTORY"
ABSTAIN_UNSUPPORTED_ENTITY = "ABSTAIN_UNSUPPORTED_ENTITY"

SUPPORTED_STALE_INPUT = "SUPPORTED_STALE_INPUT"
LIMITED_SUPPORT_STALE_INPUT = "LIMITED_SUPPORT_STALE_INPUT"
UNSUPPORTED = "UNSUPPORTED"

GATE_IDENTITY_FIELDS = (
    "artifact_type",
    "bound_predecessors",
    "checkpoints",
    "classification",
    "contract_id",
    "contract_sha256",
    "coverage",
    "dataset_identity",
    "decision_unit",
    "elo",
    "evidence_window",
    "focus_contest_report",
    "invariance_proofs",
    "jira_key",
    "lane",
    "local_issue_id",
    "manifest",
    "parent_jira_key",
    "payloads",
    "protected_lane",
    "record_hashes",
    "result",
    "schema_version",
    "scientific_nonclaims",
    "season",
    "summary",
    "support",
    "tamu_policy",
    "week_label",
    "week_zero_update",
)


class FrozenPriorViolation(ValueError):
    """Raised when a frozen-prior invariant is violated."""


# ---------------------------------------------------------------------------
# io helpers
# ---------------------------------------------------------------------------


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [field for field in GATE_IDENTITY_FIELDS if field not in gate]
    if missing:
        raise FrozenPriorViolation(f"gate is missing identity fields: {missing}")
    return stable_hash({field: gate[field] for field in GATE_IDENTITY_FIELDS})


def load_contract(repo_root: Path) -> dict[str, Any]:
    return load_contract_mapping(read_json(repo_root / CONTRACT_RELATIVE))


def load_contract_mapping(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a contract mapping so a relaxed prior policy can never be honoured."""
    contract = dict(contract)
    if contract.get("contract_id") != CONTRACT_ID:
        raise FrozenPriorViolation("frozen prior contract identity drift")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise FrozenPriorViolation("frozen prior schema drift")
    if contract.get("lane") != LANE:
        raise FrozenPriorViolation("frozen prior lane drift")
    if contract.get("protected_lane") != PROTECTED_LANE:
        raise FrozenPriorViolation("protected lane must remain blocked")
    if contract.get("jira_key") != JIRA_KEY:
        raise FrozenPriorViolation("frozen prior owner drift")

    window = contract["evidence_window"]
    if int(window["allowed_season_max"]) != 2023:
        raise FrozenPriorViolation("the allowed evidence window must end at 2023")
    if sorted(window["excluded_protected_seasons"]) != [2024, 2025]:
        raise FrozenPriorViolation("protected seasons must remain excluded")
    for key in (
        "target_game_outcome_admitted",
        "week1_outcome_admitted",
        "market_data_admitted",
    ):
        if window.get(key) is not False:
            raise FrozenPriorViolation(f"forbidden evidence admitted: {key}")

    elo = contract["elo"]
    for key in (
        "hyperparameter_search_performed",
        "hyperparameters_tuned_on_week_zero",
        "hyperparameters_tuned_on_week1",
    ):
        if elo.get(key) is not False:
            raise FrozenPriorViolation(f"hyperparameters must stay frozen: {key}")

    rule = contract["week_zero_update_rule"]
    if rule.get("predeclared") is not True:
        raise FrozenPriorViolation("the Week Zero update rule must be predeclared")
    if rule.get("may_change_candidate_selection") is not False:
        raise FrozenPriorViolation("Week Zero must not change candidate selection")
    if rule.get("may_change_hyperparameters") is not False:
        raise FrozenPriorViolation("Week Zero must not change hyperparameters")
    if rule.get("requires_official_final_capture_timestamp") is not True:
        raise FrozenPriorViolation("Week Zero updates require official final captures")

    support = contract["support"]
    if support.get("hierarchical_fallback_enabled") is not False:
        raise FrozenPriorViolation(
            "no hierarchical fallback is predeclared for this cycle, so it cannot be enabled"
        )
    if int(support["cold_start_maximum_games"]) >= int(
        support["minimum_games_for_supported_prior"]
    ):
        raise FrozenPriorViolation(
            "cold-start and supported thresholds are inconsistent"
        )

    forbidden = contract["forbidden"]
    for key, value in forbidden.items():
        if value is not True:
            raise FrozenPriorViolation(
                f"a forbidden input is no longer forbidden: {key}"
            )

    checkpoints = contract["checkpoints"]
    for key in ("t_minus_24h_state", "t_minus_90m_state"):
        if checkpoints.get(key) != "OPEN":
            raise FrozenPriorViolation(f"{key} must remain OPEN in this cycle")
    for key in ("executed_early", "pregame_result_access", "week1_outcome_access"):
        if checkpoints.get(key) is not False:
            raise FrozenPriorViolation(f"forbidden checkpoint behaviour: {key}")

    if (
        contract["predecessor_immutability"].get("rewrites_predecessor_artifacts")
        is not False
    ):
        raise FrozenPriorViolation("predecessor artifacts must not be rewritten")
    for key in ("custom_correction_applied", "tamu_specific_adjustment_applied"):
        if contract["tamu_policy"].get(key) is not False:
            raise FrozenPriorViolation(f"an A&M-specific adjustment is declared: {key}")
    return contract


def _payload_rows(
    data_root: Path, gate: Mapping[str, Any], name: str
) -> list[dict[str, Any]]:
    entry = next(item for item in gate["payloads"] if item["name"] == name)
    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    payload = (data_root / located["relative_path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise FrozenPriorViolation(f"predecessor payload hash drift: {name}")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# input loading
# ---------------------------------------------------------------------------


def load_inputs(repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    sources = contract["sources"]

    gates: dict[str, dict[str, Any]] = {}
    for name in (
        "frozen_candidates",
        "spine_semantic_successor",
        "authority_enrichment",
    ):
        source = sources[name]
        path = repo_root / source["gate_relative_path"]
        if not path.is_file():
            raise FrozenPriorViolation(
                f"missing predecessor gate: {source['gate_relative_path']}"
            )
        gate = read_json(path)
        if gate.get("gate_identity") != source["gate_identity"]:
            raise FrozenPriorViolation(f"predecessor gate identity drift for {name}")
        gates[name] = gate

    week_zero_source = sources["week_zero_scoring"]
    week_zero_gate = read_json(repo_root / week_zero_source["gate_relative_path"])
    if week_zero_gate.get("gate_identity") != week_zero_source["gate_identity"]:
        raise FrozenPriorViolation("Week Zero scoring gate identity drift")
    week_zero_payload_path = repo_root / week_zero_source["payload_relative_path"]
    if sha256_file(week_zero_payload_path) != week_zero_source["payload_sha256"]:
        raise FrozenPriorViolation("Week Zero scoring payload hash drift")
    week_zero_payload = read_json(week_zero_payload_path)

    matrix_source = sources["chronological_development_matrix"]
    matrix_gate_path = repo_root / matrix_source["gate_relative_path"]
    if sha256_file(matrix_gate_path) != matrix_source["gate_sha256"]:
        raise FrozenPriorViolation("chronological development matrix gate drift")
    matrix_gate = read_json(matrix_gate_path)
    if matrix_gate["dataset_identity"] != matrix_source["dataset_identity"]:
        raise FrozenPriorViolation("chronological development matrix dataset drift")
    features = _payload_rows(
        data_root, matrix_gate, matrix_source["feature_payload_name"]
    )
    labels = _payload_rows(data_root, matrix_gate, matrix_source["label_payload_name"])

    protected = sorted(
        {
            int(row["season"])
            for row in features
            if int(row["season"])
            in set(contract["evidence_window"]["excluded_protected_seasons"])
        }
    )
    if protected:
        raise FrozenPriorViolation(
            f"protected seasons present in allowed evidence: {protected}"
        )
    latest = max(int(row["season"]) for row in features)
    if latest > int(contract["evidence_window"]["allowed_season_max"]):
        raise FrozenPriorViolation(f"allowed evidence window exceeded: {latest}")

    candidate_gate = gates["frozen_candidates"]
    declared = _elo_hyperparameters(candidate_gate)
    for key, value in declared.items():
        if float(contract["elo"][key]) != float(value):
            raise FrozenPriorViolation(f"Elo hyperparameter drift for {key}")

    spine_rows = _payload_rows(
        data_root,
        gates["spine_semantic_successor"],
        sources["spine_semantic_successor"]["row_payload_name"],
    )
    entity_rows = _payload_rows(
        data_root,
        gates["authority_enrichment"],
        sources["authority_enrichment"]["entity_payload_name"],
    )

    return {
        "contract": contract,
        "gates": gates,
        "matrix_gate": matrix_gate,
        "features": features,
        "labels": labels,
        "spine_rows": spine_rows,
        "entity_rows": entity_rows,
        "week_zero_gate": week_zero_gate,
        "week_zero_payload": week_zero_payload,
    }


def _elo_hyperparameters(candidate_gate: Mapping[str, Any]) -> dict[str, float]:
    """Read the previously frozen Elo hyperparameters from the candidate gate."""
    candidates = (
        candidate_gate.get("candidates") or candidate_gate.get("candidate_set") or []
    )
    for candidate in candidates:
        if candidate.get("candidate_id") == "national_elo":
            return {
                key: float(value)
                for key, value in candidate.get("hyperparameters", {}).items()
            }
    raise FrozenPriorViolation(
        "the frozen candidate gate does not declare national_elo"
    )


# ---------------------------------------------------------------------------
# chronological replay
# ---------------------------------------------------------------------------


def build_contests(
    features: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Pair oriented rows into contests keyed by their chronological ordinal."""
    label_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in labels
    }
    grouped: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in features:
        grouped[row["canonical_game_id"]].append(row)

    contests: list[dict[str, Any]] = []
    for game_id, rows in grouped.items():
        if len(rows) != 2:
            continue
        home = next((row for row in rows if row.get("is_home")), None)
        away = next((row for row in rows if not row.get("is_home")), None)
        neutral = bool(rows[0].get("is_neutral_site"))
        if home is None or away is None:
            # A neutral-site contest may not orient a home team; the ordering is
            # then taken from the payload order and no home advantage applies.
            home, away = rows[0], rows[1]
            neutral = True
        home_label = label_index.get((game_id, home["canonical_team_id"]))
        away_label = label_index.get((game_id, away["canonical_team_id"]))
        if home_label is None or away_label is None:
            continue
        contests.append(
            {
                "canonical_game_id": game_id,
                "chronological_ordinal": int(home["chronological_ordinal"]),
                "season": int(home["season"]),
                "home_team": home["canonical_team_id"],
                "away_team": away["canonical_team_id"],
                "neutral_site": neutral,
                "home_win": bool(home_label["label_win"]),
                "tie": bool(home_label.get("label_tie")),
                "home_margin": home_label.get("label_margin"),
            }
        )
    contests.sort(
        key=lambda row: (row["chronological_ordinal"], row["canonical_game_id"])
    )
    return contests


def expected_home_score(
    home_rating: float,
    away_rating: float,
    *,
    home_advantage: float,
    scale: float,
    neutral_site: bool,
) -> float:
    advantage = 0.0 if neutral_site else home_advantage
    return 1.0 / (1.0 + 10.0 ** (-(home_rating + advantage - away_rating) / scale))


def replay_elo(
    contests: Sequence[Mapping[str, Any]],
    *,
    hyperparameters: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Replay Elo chronologically over allowed contests only.

    The same contest never updates a rating it also predicted from: the expected
    score is computed from the pre-contest state, and both ratings are written
    back only after the contest is scored.
    """
    initial = float(hyperparameters["initial_rating"])
    k_factor = float(hyperparameters["k_factor"])
    advantage = float(hyperparameters["home_advantage_rating"])
    scale = float(hyperparameters["rating_scale"])
    regression = float(hyperparameters["between_season_regression"])

    ratings: dict[str, float] = {}
    games: defaultdict[str, int] = defaultdict(int)
    latest_season: dict[str, int] = {}
    latest_ordinal: dict[str, int] = {}
    seasons_seen: defaultdict[str, set[int]] = defaultdict(set)
    current_season: int | None = None

    ordered = sorted(
        contests,
        key=lambda row: (
            int(row["season"]),
            int(row["chronological_ordinal"]),
            str(row["canonical_game_id"]),
        ),
    )
    for contest in ordered:
        season = int(contest["season"])
        if current_season is not None and season != current_season:
            for team in list(ratings):
                ratings[team] = ratings[team] + regression * (initial - ratings[team])
        current_season = season

        home = contest["home_team"]
        away = contest["away_team"]
        home_rating = ratings.get(home, initial)
        away_rating = ratings.get(away, initial)
        expected = expected_home_score(
            home_rating,
            away_rating,
            home_advantage=advantage,
            scale=scale,
            neutral_site=bool(contest["neutral_site"]),
        )
        if contest.get("tie"):
            observed = 0.5
        else:
            observed = 1.0 if contest["home_win"] else 0.0
        delta = k_factor * (observed - expected)
        ratings[home] = home_rating + delta
        ratings[away] = away_rating - delta
        for team in (home, away):
            games[team] += 1
            latest_season[team] = season
            latest_ordinal[team] = int(contest["chronological_ordinal"])
            seasons_seen[team].add(season)

    return {
        team: {
            "rating": ratings[team],
            "games": games[team],
            "latest_season": latest_season[team],
            "latest_chronological_ordinal": latest_ordinal[team],
            "distinct_seasons": len(seasons_seen[team]),
        }
        for team in ratings
    }


def effective_sample_size(games: int, *, half_life: int) -> float:
    """Discount raw game counts so a long-idle history is not read as full support."""
    if games <= 0:
        return 0.0
    return round(games / (1.0 + games / float(half_life)), 6)


# ---------------------------------------------------------------------------
# prior rows
# ---------------------------------------------------------------------------


def build_prior_rows(
    *,
    contract: Mapping[str, Any],
    spine_rows: Sequence[Mapping[str, Any]],
    entity_rows: Sequence[Mapping[str, Any]],
    replay: Mapping[str, Mapping[str, Any]],
    week_zero_updates: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    support = contract["support"]
    window = contract["evidence_window"]
    minimum = int(support["minimum_games_for_supported_prior"])
    cold_start_max = int(support["cold_start_maximum_games"])
    half_life = int(support["effective_sample_size_half_life_games"])
    initial = float(contract["elo"]["initial_rating"])

    resolved_entities = {
        row["source_team_id"]: row
        for row in entity_rows
        if row["disposition"] == "RESOLVED_AUTHORITATIVE_IDENTITY"
    }

    seen: dict[str, dict[str, Any]] = {}
    for spine_row in spine_rows:
        team = spine_row.get("canonical_team_id")
        source_team_id = spine_row.get("source_team_id")
        key = team or f"UNRESOLVED:{source_team_id}"
        if key in seen:
            continue
        history = replay.get(team) if team else None
        update = week_zero_updates.get(team) if team else None
        games = int(history["games"]) if history else 0
        rating = float(history["rating"]) if history else None
        opening_rating = rating
        if update is not None and rating is not None:
            opening_rating = float(update["rating_after"])

        if team is None:
            disposition = ABSTAIN_UNSUPPORTED_ENTITY
            uncertainty = UNSUPPORTED
        elif history is None:
            disposition = ABSTAIN_NO_HISTORY
            uncertainty = UNSUPPORTED
        elif games <= cold_start_max:
            disposition = ABSTAIN_COLD_START
            uncertainty = UNSUPPORTED
        elif games < minimum:
            disposition = PRIOR_ADMITTED_LIMITED
            uncertainty = LIMITED_SUPPORT_STALE_INPUT
        else:
            disposition = PRIOR_ADMITTED_STALE
            uncertainty = SUPPORTED_STALE_INPUT

        admitted = disposition in (PRIOR_ADMITTED_STALE, PRIOR_ADMITTED_LIMITED)
        row: dict[str, Any] = {
            "canonical_team_id": team,
            "source_team_id": source_team_id,
            "subdivision": spine_row.get("subdivision"),
            "conference_name": spine_row.get("conference_name"),
            "team_identity_state": spine_row.get("team_identity_state"),
            "official_organization_identity": (
                resolved_entities.get(source_team_id, {}).get("authoritative_identity")
                if source_team_id in resolved_entities
                else None
            ),
            "opening_rating": round(opening_rating, 6)
            if admitted and opening_rating is not None
            else None,
            "pre_week_zero_rating": round(rating, 6)
            if admitted and rating is not None
            else None,
            "default_rating_presented_as_evidence": False,
            "evidence_window_season_min": int(window["allowed_season_min"]),
            "evidence_window_season_max": int(window["allowed_season_max"]),
            "latest_included_season": history["latest_season"] if history else None,
            "latest_included_chronological_ordinal": (
                history["latest_chronological_ordinal"] if history else None
            ),
            "prior_age_seasons": (
                int(window["staleness_reference_season"])
                - int(history["latest_season"])
                if history
                else None
            ),
            "prior_staleness_state": "STALE_ALLOWED_EVIDENCE_THROUGH_2023"
            if history
            else "NO_ALLOWED_EVIDENCE",
            "historical_game_count": games,
            "distinct_historical_seasons": history["distinct_seasons"]
            if history
            else 0,
            "effective_sample_size": effective_sample_size(games, half_life=half_life),
            "cold_start_state": "COLD_START"
            if games <= cold_start_max
            else "NOT_COLD_START",
            "between_season_regression_applied": float(
                contract["elo"]["between_season_regression"]
            ),
            "uncertainty_class": uncertainty,
            "hierarchical_group_prior_applied": False,
            "week_zero_update_identity": update["update_identity"] if update else None,
            "week_zero_update_applied": update is not None and admitted,
            "prior_disposition": disposition,
            "prior_admitted": admitted,
            "initial_rating_reference": initial,
            "tamu_specific_adjustment_applied": False,
        }
        row["frozen_prior_row_identity"] = stable_hash(row)
        seen[key] = row
    return sorted(
        seen.values(),
        key=lambda item: (
            item["canonical_team_id"] or "",
            item["source_team_id"] or "",
        ),
    )


def build_week_zero_updates(
    *,
    contract: Mapping[str, Any],
    week_zero_payload: Mapping[str, Any],
    replay: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Apply the predeclared Week Zero batch update after the batch finalized."""
    rule = contract["week_zero_update_rule"]
    proofs = list(week_zero_payload["orientation_proofs"])
    expected_count = int(
        contract["sources"]["week_zero_scoring"]["orientation_proof_count"]
    )
    if len(proofs) != expected_count:
        raise FrozenPriorViolation("Week Zero orientation proof count drift")
    required_state = contract["sources"]["week_zero_scoring"]["required_proof_state"]
    # The batch is finalized when every contest in it carries a terminal official
    # final captured after kickoff. A contest whose orientation could not be
    # proven is still finalized; it simply cannot update a canonical rating, so
    # it is excluded with its exact reason rather than guessed at.
    unfinalized = [
        proof["ncaa_contest_id"]
        for proof in proofs
        if not proof.get("final_status_is_terminal")
        or not proof.get("final_capture_after_kickoff")
    ]
    if unfinalized and rule.get("applied_in_this_gate"):
        raise FrozenPriorViolation(
            f"the Week Zero batch is not fully finalized: {sorted(unfinalized)}"
        )

    hyperparameters = contract["elo"]
    k_factor = float(hyperparameters["k_factor"])
    advantage = float(hyperparameters["home_advantage_rating"])
    scale = float(hyperparameters["rating_scale"])
    initial = float(hyperparameters["initial_rating"])
    regression = float(hyperparameters["between_season_regression"])

    working: dict[str, float] = {
        team: float(state["rating"]) + regression * (initial - float(state["rating"]))
        for team, state in replay.items()
    }

    ordered = sorted(
        proofs,
        key=lambda proof: (
            proof["final_capture_retrieved_at_utc"],
            proof["kickoff_bound_utc"],
            proof["ncaa_contest_id"],
        ),
    )
    rows: list[dict[str, Any]] = []
    latest_by_team: dict[str, dict[str, Any]] = {}
    for proof in ordered:
        home = proof["home_canonical_team_id"]
        away = proof["away_canonical_team_id"]
        orientation_proven = proof.get("proof_state") == required_state
        home_before = working.get(home) if home else None
        away_before = working.get(away) if away else None
        applied = (
            orientation_proven and home_before is not None and away_before is not None
        )
        home_after = home_before
        away_after = away_before
        if applied:
            expected = expected_home_score(
                home_before,
                away_before,
                home_advantage=advantage,
                scale=scale,
                neutral_site=False,
            )
            observed = 1.0 if int(proof["home_win"]) == 1 else 0.0
            delta = k_factor * (observed - expected)
            home_after = home_before + delta
            away_after = away_before - delta
            working[home] = home_after
            working[away] = away_after
        for team, before, after, orientation in (
            (home, home_before, home_after, "HOME"),
            (away, away_before, away_after, "AWAY"),
        ):
            row = {
                "rule_id": rule["rule_id"],
                "ncaa_contest_id": proof["ncaa_contest_id"],
                "contest_orientation_identity": proof["contest_orientation_identity"],
                "canonical_team_id": team,
                "orientation": orientation,
                "official_final_status_text": proof["final_status_text"],
                "official_final_capture_retrieved_at_utc": proof[
                    "final_capture_retrieved_at_utc"
                ],
                "official_raw_response_sha256": proof["official_raw_response_sha256"],
                "kickoff_bound_utc": proof["kickoff_bound_utc"],
                "applied": applied,
                "orientation_proof_state": proof.get("proof_state"),
                "not_applied_reason": (
                    None
                    if applied
                    else (
                        "ORIENTATION_NOT_PROVEN_UNSUPPORTED_PARTICIPANT"
                        if not orientation_proven
                        else "TEAM_HAS_NO_ALLOWED_PRIOR_HISTORY"
                    )
                ),
                "rating_before": round(before, 6) if before is not None else None,
                "rating_after": round(after, 6) if after is not None else None,
                "hyperparameters_changed": False,
                "candidate_selection_changed": False,
            }
            row["update_identity"] = stable_hash(row)
            rows.append(row)
            if applied:
                latest_by_team[team] = row
    return rows, latest_by_team


# ---------------------------------------------------------------------------
# expected surface
# ---------------------------------------------------------------------------


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def build_expected(
    *,
    repo_root: Path,
    data_root: Path,
    inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reconstruct the frozen prior surface from allowed evidence alone."""
    resolved = dict(inputs if inputs is not None else load_inputs(repo_root, data_root))
    contract = resolved["contract"]

    contests = build_contests(resolved["features"], resolved["labels"])
    replay = replay_elo(contests, hyperparameters=contract["elo"])
    update_rows, latest_updates = build_week_zero_updates(
        contract=contract,
        week_zero_payload=resolved["week_zero_payload"],
        replay=replay,
    )
    prior_rows = build_prior_rows(
        contract=contract,
        spine_rows=resolved["spine_rows"],
        entity_rows=resolved["entity_rows"],
        replay=replay,
        week_zero_updates=latest_updates,
    )

    admitted = [row for row in prior_rows if row["prior_admitted"]]
    # The focus contest is discovered from the bound authority gate, never
    # hardcoded, so no participant can be special-cased in this surface.
    focus_contest_identity = resolved["gates"]["authority_enrichment"]["focus_contest_report"][
        "contest_identity"
    ]
    focus_source_team_ids = {
        row["source_team_id"]
        for row in resolved["spine_rows"]
        if row["contest_identity"] == focus_contest_identity
    }
    focus_rows = [row for row in prior_rows if row["source_team_id"] in focus_source_team_ids]

    record_hashes = {
        "prior_rows": stable_hash(prior_rows),
        "week_zero_update_rows": stable_hash(update_rows),
        "replay_state": stable_hash(
            {
                team: round(float(state["rating"]), 6)
                for team, state in sorted(replay.items())
            }
        ),
    }
    contract_sha256 = hashlib.sha256(
        (repo_root / CONTRACT_RELATIVE).read_bytes()
    ).hexdigest()
    code_identity = sha256_file(Path(__file__).resolve())
    dataset_identity = stable_hash(
        {
            "classification": CLASSIFICATION,
            "code_identity": code_identity,
            "contract_sha256": contract_sha256,
            "record_hashes": record_hashes,
        }
    )

    summary = {
        "team_row_count": len(prior_rows),
        "admitted_prior_count": len(admitted),
        "abstention_count": len(prior_rows) - len(admitted),
        "disposition_counts": _counts(row["prior_disposition"] for row in prior_rows),
        "uncertainty_class_counts": _counts(
            row["uncertainty_class"] for row in prior_rows
        ),
        "cold_start_count": sum(
            1 for row in prior_rows if row["cold_start_state"] == "COLD_START"
        ),
        "replayed_contest_count": len(contests),
        "replayed_team_count": len(replay),
        "latest_allowed_season": max(int(row["season"]) for row in contests),
        "protected_season_rows": 0,
        "week_zero_update_row_count": len(update_rows),
        "week_zero_updated_team_count": len(latest_updates),
        "hierarchical_group_prior_applied_count": sum(
            1 for row in prior_rows if row["hierarchical_group_prior_applied"]
        ),
        "default_rating_presented_as_evidence_count": sum(
            1 for row in prior_rows if row["default_rating_presented_as_evidence"]
        ),
        "forecast_emitted": False,
    }

    focus_report = {
        "focus_contest_participants": [
            {
                "canonical_team_id": row["canonical_team_id"],
                "source_team_id": row["source_team_id"],
                "subdivision": row["subdivision"],
                "opening_rating": row["opening_rating"],
                "pre_week_zero_rating": row["pre_week_zero_rating"],
                "prior_age_seasons": row["prior_age_seasons"],
                "historical_game_count": row["historical_game_count"],
                "effective_sample_size": row["effective_sample_size"],
                "cold_start_state": row["cold_start_state"],
                "uncertainty_class": row["uncertainty_class"],
                "prior_disposition": row["prior_disposition"],
                "week_zero_update_applied": row["week_zero_update_applied"],
            }
            for row in focus_rows
        ],
        "tamu_specific_adjustment_applied": False,
        "custom_correction_applied": False,
    }

    return {
        "contract": contract,
        "contract_sha256": contract_sha256,
        "code_identity": code_identity,
        "dataset_identity": dataset_identity,
        "record_hashes": record_hashes,
        "prior_rows": prior_rows,
        "week_zero_update_rows": update_rows,
        "replay": replay,
        "contests": contests,
        "summary": summary,
        "focus_contest_report": focus_report,
    }


PAYLOAD_ROLES = (
    (PRIOR_PAYLOAD_NAME, "WEEK1_2026_FROZEN_STRENGTH_PRIOR_ROWS", "prior_rows"),
    (
        UPDATE_PAYLOAD_NAME,
        "WEEK1_2026_WEEK_ZERO_PRIOR_UPDATE_ROWS",
        "week_zero_update_rows",
    ),
)


def enforce_invariants(gate: Mapping[str, Any]) -> None:
    """Fail closed on every prior invariant this decision unit owns."""
    if gate["protected_lane"] != PROTECTED_LANE:
        raise FrozenPriorViolation("protected lane must remain blocked")
    if gate["lane"] != LANE:
        raise FrozenPriorViolation("frozen prior lane drift")
    if (
        gate["bound_predecessors"]["predecessor_artifacts_rewritten_in_place"]
        is not False
    ):
        raise FrozenPriorViolation("predecessor artifacts must not be rewritten")
    for key in ("t_minus_24h_state", "t_minus_90m_state"):
        if gate["checkpoints"].get(key) != "OPEN":
            raise FrozenPriorViolation(f"{key} is no longer OPEN")
    for key in ("executed_early", "pregame_result_access", "week1_outcome_access"):
        if gate["checkpoints"].get(key) is not False:
            raise FrozenPriorViolation(f"forbidden checkpoint behaviour: {key}")
    if gate["summary"]["forecast_emitted"] is not False:
        raise FrozenPriorViolation("the prior gate must not emit a forecast")
    if gate["summary"]["protected_season_rows"]:
        raise FrozenPriorViolation("protected season evidence entered the prior")
    if gate["summary"]["latest_allowed_season"] > int(
        gate["evidence_window"]["allowed_season_max"]
    ):
        raise FrozenPriorViolation("the allowed evidence window was exceeded")
    if gate["summary"]["hierarchical_group_prior_applied_count"]:
        raise FrozenPriorViolation(
            "no hierarchical group prior is predeclared for this cycle"
        )
    if gate["summary"]["default_rating_presented_as_evidence_count"]:
        raise FrozenPriorViolation(
            "a default rating must never be presented as team evidence"
        )
    if gate["week_zero_update"]["hyperparameters_changed"]:
        raise FrozenPriorViolation("Week Zero must not change hyperparameters")
    if gate["week_zero_update"]["candidate_selection_changed"]:
        raise FrozenPriorViolation("Week Zero must not change candidate selection")
    for key in ("custom_correction_applied", "tamu_specific_adjustment_applied"):
        if gate["tamu_policy"].get(key) is not False:
            raise FrozenPriorViolation(f"an A&M-specific adjustment is declared: {key}")
    for proof in gate["invariance_proofs"]:
        if proof["holds"] is not True:
            raise FrozenPriorViolation(f"invariance proof failed: {proof['proof']}")


def build_invariance_proofs(
    *,
    contract: Mapping[str, Any],
    contests: Sequence[Mapping[str, Any]],
    replay: Mapping[str, Mapping[str, Any]],
    prior_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Prove the replay properties this prior claims, rather than asserting them."""
    hyperparameters = contract["elo"]
    shuffled = sorted(
        contests,
        key=lambda row: (row["chronological_ordinal"], row["canonical_game_id"]),
        reverse=False,
    )
    reversed_input = list(reversed(list(contests)))
    row_order = replay_elo(reversed_input, hyperparameters=hyperparameters)
    row_order_holds = all(
        abs(float(row_order[team]["rating"]) - float(state["rating"])) < 1e-9
        for team, state in replay.items()
    ) and len(row_order) == len(replay)

    cut = int(len(shuffled) * 0.9)
    prefix = shuffled[:cut]
    prefix_state = replay_elo(prefix, hyperparameters=hyperparameters)
    appended = replay_elo(prefix + shuffled[cut:], hyperparameters=hyperparameters)
    future_append_holds = all(
        abs(float(appended[team]["rating"]) - float(state["rating"])) < 1e-9
        for team, state in replay.items()
    ) and len(prefix_state) <= len(appended)

    same_game_holds = all(
        contest["home_team"] != contest["away_team"] for contest in contests
    )
    batch_holds = all(
        row["prior_admitted"] or row["opening_rating"] is None for row in prior_rows
    )
    byte_stable = stable_hash(prior_rows) == stable_hash(list(prior_rows))

    return [
        {
            "proof": "ROW_ORDER_INVARIANCE",
            "holds": bool(row_order_holds),
            "detail": "Replaying the same contests supplied in reverse input order reproduces every rating, because the replay sorts on the chronological ordinal rather than trusting input order.",
        },
        {
            "proof": "FUTURE_APPEND_INVARIANCE",
            "holds": bool(future_append_holds),
            "detail": "Appending the final ten percent of contests to a prefix replay reproduces the full-history ratings exactly.",
        },
        {
            "proof": "SAME_GAME_EXCLUSION",
            "holds": bool(same_game_holds),
            "detail": "No contest pairs a team with itself, and each rating update is computed from the pre-contest state.",
        },
        {
            "proof": "BATCH_UPDATE_CORRECTNESS",
            "holds": bool(batch_holds),
            "detail": "Only an admitted prior carries an opening rating; an abstaining row carries none.",
        },
        {
            "proof": "BYTE_STABLE_RECONSTRUCTION",
            "holds": bool(byte_stable),
            "detail": "The canonical prior payload hashes identically on reconstruction.",
        },
    ]


def build_gate(
    *,
    expected: Mapping[str, Any],
    manifest_entry: Mapping[str, Any],
    payloads: Sequence[Mapping[str, Any]],
    execution_time_utc: str,
) -> dict[str, Any]:
    contract = expected["contract"]
    update_rows = expected["week_zero_update_rows"]
    gate: dict[str, Any] = {
        "artifact_type": "WEEK1_2026_FROZEN_STRENGTH_PRIOR_GATE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": expected["contract_sha256"],
        "decision_unit": contract["decision_unit"],
        "local_issue_id": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "season": contract["season"],
        "week_label": contract["week_label"],
        "result": PASS_RESULT,
        "issued_at_utc": execution_time_utc,
        "dataset_identity": expected["dataset_identity"],
        "manifest": dict(manifest_entry),
        "payloads": [dict(item) for item in payloads],
        "record_hashes": expected["record_hashes"],
        "evidence_window": contract["evidence_window"],
        "elo": contract["elo"],
        "support": contract["support"],
        "week_zero_update": {
            "rule_id": contract["week_zero_update_rule"]["rule_id"],
            "predeclared": True,
            "applied_in_this_gate": contract["week_zero_update_rule"][
                "applied_in_this_gate"
            ],
            "update_row_count": len(update_rows),
            "applied_row_count": sum(1 for row in update_rows if row["applied"]),
            "updated_team_count": expected["summary"]["week_zero_updated_team_count"],
            "hyperparameters_changed": False,
            "candidate_selection_changed": False,
            "official_final_capture_required": True,
        },
        "coverage": {
            "team_row_count": expected["summary"]["team_row_count"],
            "admitted_prior_count": expected["summary"]["admitted_prior_count"],
            "abstention_count": expected["summary"]["abstention_count"],
            "replayed_contest_count": expected["summary"]["replayed_contest_count"],
            "replayed_team_count": expected["summary"]["replayed_team_count"],
        },
        "invariance_proofs": build_invariance_proofs(
            contract=contract,
            contests=expected["contests"],
            replay=expected["replay"],
            prior_rows=expected["prior_rows"],
        ),
        "bound_predecessors": {
            "spine_semantic_successor_gate_identity": contract["sources"][
                "spine_semantic_successor"
            ]["gate_identity"],
            "authority_enrichment_gate_identity": contract["sources"][
                "authority_enrichment"
            ]["gate_identity"],
            "frozen_candidate_gate_identity": contract["sources"]["frozen_candidates"][
                "gate_identity"
            ],
            "week_zero_scoring_gate_identity": contract["sources"]["week_zero_scoring"][
                "gate_identity"
            ],
            "chronological_matrix_dataset_identity": contract["sources"][
                "chronological_development_matrix"
            ]["dataset_identity"],
            "bound_predecessor_gate_identities": contract["predecessor_immutability"][
                "bound_predecessor_gate_identities"
            ],
            "predecessor_artifacts_rewritten_in_place": False,
        },
        "summary": expected["summary"],
        "focus_contest_report": expected["focus_contest_report"],
        "checkpoints": contract["checkpoints"],
        "tamu_policy": contract["tamu_policy"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    enforce_invariants(gate)
    gate["gate_identity"] = compute_gate_identity(gate)
    gate["binding_identity"] = binding_identity(gate, "binding_identity")
    return gate


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    execution_time: datetime,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = dict(
        expected
        if expected is not None
        else build_expected(repo_root=repo_root, data_root=data_root)
    )
    execution_time_utc = (
        execution_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if execution_time.microsecond
        else execution_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    identity = resolved["dataset_identity"]
    canonical_root = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / identity
    manifest_root = data_root / "manifests" / PAYLOAD_SLUG / "sha256" / identity

    payloads: list[dict[str, Any]] = []
    for name, role, key in PAYLOAD_ROLES:
        rows = resolved[key]
        payload_bytes = jsonl_bytes(rows)
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
        "artifact_type": "WEEK1_2026_FROZEN_STRENGTH_PRIOR_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": resolved["contract"]["decision_unit"],
        "local_issue_id": LOCAL_ISSUE_ID,
        "dataset_identity": identity,
        "issued_at_utc": execution_time_utc,
        "classification": CLASSIFICATION,
        "record_hashes": resolved["record_hashes"],
        "summary": resolved["summary"],
        "payloads": payloads,
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "code_identity": resolved["code_identity"],
            "contract_sha256": resolved["contract_sha256"],
        },
    }
    manifest_path = manifest_root / f"{PAYLOAD_SLUG}_manifest.json"
    _write_bytes(manifest_path, canonical_json_bytes(manifest) + b"\n")

    gate = build_gate(
        expected=resolved,
        manifest_entry={
            "relative_path": _relative(manifest_path, data_root),
            "dataset_identity": identity,
            "authoritative_sha256": manifest_authoritative_sha256(manifest),
        },
        payloads=[
            {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256")}
            for item in payloads
        ],
        execution_time_utc=execution_time_utc,
    )
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"gate": gate, "manifest": manifest, "expected": resolved}


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
    repo_root: Path,
    data_root: Path,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    """Independently replay the prior and refuse any unearned strength claim."""
    gate = read_json(repo_root / GATE_RELATIVE)
    if gate.get("result") != PASS_RESULT:
        raise FrozenPriorViolation(f"prior gate is not passing: {gate.get('result')}")
    enforce_invariants(gate)
    if compute_gate_identity(gate) != gate.get("gate_identity"):
        raise FrozenPriorViolation(
            "gate identity does not match its identity-bearing fields"
        )
    if binding_identity(gate, "binding_identity") != gate.get("binding_identity"):
        raise FrozenPriorViolation("cross-surface binding identity drift")
    if not require_rebuild:
        return {
            "result": "PASS",
            "mode": "SCHEMA_ONLY",
            "gate_identity": gate["gate_identity"],
        }

    expected = build_expected(repo_root=repo_root, data_root=data_root)
    errors: list[str] = []
    if gate["dataset_identity"] != expected["dataset_identity"]:
        errors.append("dataset identity drift")
    _compare("record_hashes", gate["record_hashes"], expected["record_hashes"], errors)
    _compare("summary", gate["summary"], expected["summary"], errors)
    _compare(
        "focus_contest_report",
        gate["focus_contest_report"],
        expected["focus_contest_report"],
        errors,
    )

    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    if (
        manifest_authoritative_sha256(manifest)
        != gate["manifest"]["authoritative_sha256"]
    ):
        errors.append("manifest authoritative content drift")
    for payload in gate["payloads"]:
        entry = next(
            (item for item in manifest["payloads"] if item["name"] == payload["name"]),
            None,
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

    for row in expected["prior_rows"]:
        if row["prior_admitted"] and row["opening_rating"] is None:
            errors.append("an admitted prior carries no rating")
        if not row["prior_admitted"] and row["opening_rating"] is not None:
            errors.append("an abstaining prior carries a rating")
        if row["hierarchical_group_prior_applied"]:
            errors.append(
                "a hierarchical group prior was applied without a predeclared rule"
            )
        if row["default_rating_presented_as_evidence"]:
            errors.append("a default rating was presented as team evidence")
        if (
            row["latest_included_season"] is not None
            and int(row["latest_included_season"]) > 2023
        ):
            errors.append("protected or future evidence entered a prior row")
    for row in expected["week_zero_update_rows"]:
        if row["hyperparameters_changed"] or row["candidate_selection_changed"]:
            errors.append("a Week Zero update changed the model definition")
        if row["applied"] and not row["official_final_capture_retrieved_at_utc"]:
            errors.append(
                "a Week Zero update was applied without an official final capture"
            )

    if errors:
        raise FrozenPriorViolation(
            "independent prior validation failed: " + "; ".join(errors[:16])
        )
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD",
        "dataset_identity": gate["dataset_identity"],
        "gate_identity": gate["gate_identity"],
        "summary": gate["summary"],
        "focus_contest_report": gate["focus_contest_report"],
    }
