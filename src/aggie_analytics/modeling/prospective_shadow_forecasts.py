"""Prospective 2026 national shadow forecasts and independent postgame scoring.

A shadow forecast is only allowed to exist when three things are simultaneously
true: the contest is still far enough from its most conservative possible kickoff
instant, a pregame snapshot of the official schedule page was frozen before that
instant, and one of the candidates frozen in the Phase 6 contract can actually be
evaluated from evidence that exists before kickoff.

The third condition removes most of the frozen candidate set. Three of the five
candidates consume prior-season and season-to-date outcome aggregates that would
have to be manufactured from the sealed 2024 and 2025 seasons, so they abstain
here rather than receive invented features. What remains is an uninformative
reference and a rating carried out of the last admitted season, and both of those
are labelled with exactly that limitation.

The scorer lives in the same module but shares no state with the producer: it
reads a frozen forecast payload and an official-final payload, refuses to look at
an outcome captured before the forecast freeze, refuses a forecast created after
kickoff, and cannot promote anything.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    manifest_authoritative_sha256,
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import (
    iso_utc,
    kickoff_bound,
    load_alias_population,
    parse_scoreboard_document,
    parse_utc,
    resolve_participant,
)

SCHEMA_VERSION = "aggie.shadow.prospective_2026_forecast.v1"
CONTRACT_ID = "BAT-657-PROSPECTIVE-2026-NATIONAL-SHADOW-FORECAST-AND-SCORING-V1"
CLASSIFICATION = (
    "PROSPECTIVE_2026_NATIONAL_SHADOW_FORECAST_FREEZE_AND_INDEPENDENT_POSTGAME_SCORING"
)
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_PROSPECTIVE_2026_NATIONAL_SHADOW_FORECAST_FREEZE"
AWAITING_RESULT = "AWAITING_ELIGIBLE_OFFICIAL_FINALS"

CONTRACT_RELATIVE = "configs/prospective_2026_shadow_forecast_contract.json"
GATE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_forecast_gate.json"
SCORING_GATE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_scoring_gate.json"
EVIDENCE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_forecast_replay.json"

FORECAST_STATES = (
    "PRECOMMITTED",
    "SNAPSHOT_ELIGIBLE",
    "SNAPSHOT_FROZEN",
    "FORECAST_FROZEN",
    "AWAITING_OFFICIAL_FINAL",
    "SCORED",
    "MISSED_CUTOFF_NO_BACKFILL",
    "UNSUPPORTED_ENTITY",
    "MISSING_REQUIRED_FEATURES_ABSTAIN",
    "CANCELED_OR_SUSPENDED",
    "OFFICIAL_FINAL_UNAVAILABLE",
    "FAIL_CLOSED_IDENTITY_MISMATCH",
)

ADMISSIBLE = "ADMISSIBLE_FOR_PROSPECTIVE_SHADOW_USE"
NOT_ADMISSIBLE = "NOT_ADMISSIBLE_MISSING_REQUIRED_FEATURES"

NON_AUTHORITATIVE_MANIFEST_KEYS = frozenset({"issued_at_utc", "producer"})

CHECKPOINT_OFFSETS = {"T_MINUS_24H": 24 * 3600, "T_MINUS_90M": 90 * 60}

ROUND_DIGITS = 8


# ---------------------------------------------------------------------------
# contract
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = _read_json(Path(repo_root) / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("prospective 2026 shadow forecast contract identity mismatch")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("prospective 2026 shadow forecast contract schema mismatch")
    if contract.get("lane") != LANE:
        raise ValueError("prospective 2026 shadow forecast lane must remain observation only")
    for field in (
        "historical_pit_admission",
        "protected_training_admission",
        "protected_evaluation_admission",
        "model_selection_or_tuning",
        "champion_or_production_promotion",
        "forecast_publication",
        "canonical_entity_mutation",
        "immutable_raw_capture_mutation",
    ):
        if contract["authority"].get(field) is not False:
            raise ValueError(f"contract authority field must remain false: {field}")
    if contract["snapshot"].get("retroactive_snapshot_permitted") is not False:
        raise ValueError("contract must forbid retroactive snapshots")
    if contract["snapshot"].get("outcome_accessible_before_forecast_freeze") is not False:
        raise ValueError("contract must forbid outcome access before the forecast freeze")
    if contract["forecast"].get("post_hoc_candidate_insertion") is not False:
        raise ValueError("contract must forbid post-hoc candidate insertion")
    if contract["scoring"].get("may_promote_a_model") is not False:
        raise ValueError("contract must forbid promotion from the scorer")
    declared = sorted(
        contract["states"]["progress_states"] + contract["states"]["terminal_or_side_states"]
    )
    if declared != sorted(FORECAST_STATES):
        raise ValueError("contract state vocabulary does not match the implementation")
    return contract


def admissible_candidates(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(entry)
        for entry in contract["forecast"]["candidate_admissibility"]
        if entry["admissibility"] == ADMISSIBLE
    ]


def abstaining_candidates(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(entry)
        for entry in contract["forecast"]["candidate_admissibility"]
        if entry["admissibility"] == NOT_ADMISSIBLE
    ]


def assert_candidates_match_frozen_set(
    contract: Mapping[str, Any], baseline_contract: Mapping[str, Any]
) -> None:
    """A candidate may be dropped for missing features but never invented here."""

    frozen = {str(item["candidate_id"]) for item in baseline_contract["candidates"]}
    declared = {
        str(item["candidate_id"]) for item in contract["forecast"]["candidate_admissibility"]
    }
    inserted = sorted(declared - frozen)
    if inserted:
        raise ValueError(f"candidate identities were not frozen in Phase 6: {inserted}")
    missing = sorted(frozen - declared)
    if missing:
        raise ValueError(f"frozen candidates carry no admissibility decision: {missing}")


# ---------------------------------------------------------------------------
# candidate fitting over the admitted national population
# ---------------------------------------------------------------------------


def load_matrix_rows(
    data_root: Path, matrix_gate: Mapping[str, Any], name: str
) -> list[dict[str, Any]]:
    entry = next(item for item in matrix_gate["payloads"] if item["name"] == name)
    manifest = _read_json(Path(data_root) / matrix_gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    payload_path = Path(data_root) / located["relative_path"]
    if sha256_file(payload_path) != entry["sha256"]:
        raise ValueError(f"matrix payload hash drift: {name}")
    with payload_path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def training_population(
    features: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    *,
    last_admitted_season: int,
    sealed_seasons: Iterable[int],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    """Keep every admitted season through the last admitted one, sealed years out."""

    sealed = {int(season) for season in sealed_seasons}
    label_index = {
        (str(row["canonical_game_id"]), str(row["canonical_team_id"])): dict(row)
        for row in labels
    }
    kept: list[dict[str, Any]] = []
    for row in features:
        season = int(row["season"])
        if season > int(last_admitted_season) or season in sealed:
            continue
        key = (str(row["canonical_game_id"]), str(row["canonical_team_id"]))
        if key not in label_index:
            continue
        kept.append(dict(row))
    kept.sort(key=lambda row: int(row["chronological_ordinal"]))
    return kept, label_index


def base_rate(
    training: Sequence[Mapping[str, Any]],
    labels: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    tie_value: float = 0.5,
) -> float:
    total = 0.0
    count = 0
    for row in training:
        label = labels.get((str(row["canonical_game_id"]), str(row["canonical_team_id"])))
        if label is None:
            continue
        if label["label_tie"]:
            total += float(tie_value)
        elif label["label_win"]:
            total += 1.0
        count += 1
    if count == 0:
        raise ValueError("the admitted training population carried no labelled rows")
    return total / count


def elo_probability_for_pair(
    *,
    ratings: Mapping[str, float],
    home_team_id: str,
    away_team_id: str,
    is_neutral_site: bool,
    hyperparameters: Mapping[str, Any],
) -> float:
    initial = float(hyperparameters["initial_rating"])
    advantage = float(hyperparameters["home_advantage_rating"])
    scale = float(hyperparameters["rating_scale"])
    home = ratings.get(str(home_team_id), initial)
    away = ratings.get(str(away_team_id), initial)
    bonus = 0.0 if is_neutral_site else advantage
    return 1.0 / (1.0 + 10.0 ** (-(home + bonus - away) / scale))


def clip_probability(value: float, clip: Sequence[float]) -> float:
    low = max(float(clip[0]), 0.0)
    high = min(float(clip[1]), 1.0)
    return min(max(float(value), low), high)


# ---------------------------------------------------------------------------
# snapshot and eligibility
# ---------------------------------------------------------------------------


def checkpoint_states(
    *, kickoff: datetime | None, execution_time: datetime
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for checkpoint_id, offset in sorted(CHECKPOINT_OFFSETS.items(), key=lambda item: -item[1]):
        if kickoff is None:
            result.append(
                {
                    "checkpoint_id": checkpoint_id,
                    "deadline_utc": None,
                    "state": "NOT_EVALUATED_WITHOUT_A_PUBLISHED_CLOCK",
                }
            )
            continue
        deadline = kickoff - timedelta(seconds=offset)
        result.append(
            {
                "checkpoint_id": checkpoint_id,
                "deadline_utc": iso_utc(deadline),
                "state": "OPEN" if execution_time <= deadline else "CLOSED",
            }
        )
    return result


def snapshot_identity(
    *,
    contest_id: str,
    capture_sha256: str,
    kickoff_lower_bound: str | None,
    home_team_id: str | None,
    away_team_id: str | None,
    cutoff_checkpoint_id: str,
    frozen_at_utc: str,
) -> str:
    return stable_hash(
        {
            "away_canonical_team_id": away_team_id,
            "capture_sha256": capture_sha256,
            "cutoff_checkpoint_id": cutoff_checkpoint_id,
            "home_canonical_team_id": home_team_id,
            "kickoff_utc_conservative_lower_bound": kickoff_lower_bound,
            "ncaa_contest_id": str(contest_id),
            "snapshot_frozen_at_utc": frozen_at_utc,
        }
    )


def _pair(record: Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None]:
    home = record.get("home_team")
    away = record.get("away_team")
    return home, away


def classify_contest(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    capture: Mapping[str, Any],
    execution_time: datetime,
) -> dict[str, Any]:
    """Decide whether one contest may carry a frozen pregame snapshot."""

    contest_id = str(record.get("ncaa_contest_id") or "")
    offset = int(contract["snapshot"]["kickoff_time_basis"]["declared_offset_seconds_for_window"])
    if record.get("parse_state") != "PARSED":
        return {
            "ncaa_contest_id": contest_id,
            "forecast_state": "FAIL_CLOSED_IDENTITY_MISMATCH",
            "state_reason": record.get("parse_reason", "PARSE_FAILED"),
            "snapshot": None,
            "kickoff_utc_conservative_lower_bound": None,
            "checkpoints": [],
        }
    lower_bound, kickoff_state = kickoff_bound(
        game_date=str(record["source_published_game_date"]),
        clock_text=str(record.get("source_published_clock_text") or ""),
        offset_seconds=offset,
    )
    kickoff = parse_utc(lower_bound) if lower_bound else None
    checkpoints = checkpoint_states(kickoff=kickoff, execution_time=execution_time)
    home, away = _pair(record)
    unresolved = [
        str(participant["source_display_name"])
        for participant in record.get("participants", [])
        if participant.get("canonical_team_id") is None
    ]
    common = {
        "ncaa_contest_id": contest_id,
        "source_published_game_date": str(record["source_published_game_date"]),
        "source_published_clock_text": str(record.get("source_published_clock_text") or ""),
        "kickoff_time_state": kickoff_state,
        "kickoff_utc_conservative_lower_bound": lower_bound,
        "kickoff_utc_independently_confirmed": False,
        "checkpoints": checkpoints,
        "home_canonical_team_id": (home or {}).get("canonical_team_id"),
        "away_canonical_team_id": (away or {}).get("canonical_team_id"),
        "home_source_display_name": (home or {}).get("source_display_name"),
        "away_source_display_name": (away or {}).get("source_display_name"),
        "is_neutral_site": bool(str(record.get("neutral_site_text") or "").strip()),
        "unresolved_participant_names": sorted(unresolved),
    }
    if unresolved:
        return {
            **common,
            "forecast_state": "UNSUPPORTED_ENTITY",
            "state_reason": "AT_LEAST_ONE_PARTICIPANT_DOES_NOT_RESOLVE_TO_THE_NATIONAL_SPINE",
            "snapshot": None,
        }
    if lower_bound is None:
        return {
            **common,
            "forecast_state": "MISSING_REQUIRED_FEATURES_ABSTAIN",
            "state_reason": "NO_PUBLISHED_KICKOFF_CLOCK_SO_NO_ELIGIBILITY_DECISION_IS_POSSIBLE",
            "snapshot": None,
        }
    cutoff_id = str(contract["snapshot"]["snapshot_cutoff_checkpoint_id"])
    cutoff = next(item for item in checkpoints if item["checkpoint_id"] == cutoff_id)
    if cutoff["state"] == "CLOSED":
        return {
            **common,
            "forecast_state": "MISSED_CUTOFF_NO_BACKFILL",
            "state_reason": "EXECUTION_TIME_IS_PAST_THE_DECLARED_PREGAME_CUTOFF",
            "snapshot": None,
        }
    frozen_at = iso_utc(execution_time)
    snapshot = {
        "capture_sha256": str(capture["raw_sha256"]),
        "capture_retrieved_at_utc": str(capture["retrieved_at_utc"]),
        "cutoff_checkpoint_id": cutoff_id,
        "snapshot_frozen_at_utc": frozen_at,
        "snapshot_identity": snapshot_identity(
            contest_id=contest_id,
            capture_sha256=str(capture["raw_sha256"]),
            kickoff_lower_bound=lower_bound,
            home_team_id=common["home_canonical_team_id"],
            away_team_id=common["away_canonical_team_id"],
            cutoff_checkpoint_id=cutoff_id,
            frozen_at_utc=frozen_at,
        ),
        "outcome_read_before_freeze": False,
    }
    return {
        **common,
        "forecast_state": "SNAPSHOT_FROZEN",
        "state_reason": "SNAPSHOT_FROZEN_BEFORE_THE_DECLARED_PREGAME_CUTOFF",
        "snapshot": snapshot,
    }


# ---------------------------------------------------------------------------
# forecast freeze
# ---------------------------------------------------------------------------


def freeze_forecasts(
    *,
    contract: Mapping[str, Any],
    contests: Sequence[Mapping[str, Any]],
    fitted: Mapping[str, Any],
    model_identity: str,
    feature_identity: str,
    code_identity: str,
    execution_time: datetime,
) -> list[dict[str, Any]]:
    """Emit one frozen forecast row per admissible candidate per eligible contest."""

    clip = contract["forecast"]["probability_clip"]
    rows: list[dict[str, Any]] = []
    admissible = admissible_candidates(contract)
    abstaining = abstaining_candidates(contract)
    created_at = iso_utc(execution_time)
    for contest in contests:
        eligible = contest["forecast_state"] == "SNAPSHOT_FROZEN"
        for candidate in admissible + abstaining:
            candidate_id = str(candidate["candidate_id"])
            base = {
                "away_canonical_team_id": contest.get("away_canonical_team_id"),
                "candidate_id": candidate_id,
                "candidate_admissibility": candidate["admissibility"],
                "code_identity": code_identity,
                "created_at_utc": created_at,
                "feature_identity": feature_identity,
                "forecast_authority": LANE,
                "home_canonical_team_id": contest.get("home_canonical_team_id"),
                "is_neutral_site": bool(contest.get("is_neutral_site")),
                "kickoff_utc_conservative_lower_bound": contest.get(
                    "kickoff_utc_conservative_lower_bound"
                ),
                "model_identity": model_identity,
                "ncaa_contest_id": contest["ncaa_contest_id"],
                "orientation": contract["forecast"]["orientation"],
                "snapshot_identity": (contest.get("snapshot") or {}).get("snapshot_identity"),
                "source_published_game_date": contest["source_published_game_date"],
            }
            if not eligible:
                rows.append(
                    {
                        **base,
                        "forecast_state": contest["forecast_state"],
                        "abstention_state": contest["forecast_state"],
                        "abstention_reason": contest["state_reason"],
                        "probability_home_win": None,
                    }
                )
                continue
            if candidate["admissibility"] == NOT_ADMISSIBLE:
                rows.append(
                    {
                        **base,
                        "forecast_state": "MISSING_REQUIRED_FEATURES_ABSTAIN",
                        "abstention_state": "MISSING_REQUIRED_FEATURES_ABSTAIN",
                        "abstention_reason": candidate["reason"],
                        "probability_home_win": None,
                    }
                )
                continue
            if candidate_id == "national_base_rate":
                probability = float(fitted["national_base_rate"]["probability"])
            elif candidate_id == "national_elo":
                probability = elo_probability_for_pair(
                    ratings=fitted["national_elo"]["ratings"],
                    home_team_id=str(contest["home_canonical_team_id"]),
                    away_team_id=str(contest["away_canonical_team_id"]),
                    is_neutral_site=bool(contest.get("is_neutral_site")),
                    hyperparameters=fitted["national_elo"]["hyperparameters"],
                )
            else:
                raise ValueError(f"no prospective evaluation path for candidate: {candidate_id}")
            rows.append(
                {
                    **base,
                    "forecast_state": "FORECAST_FROZEN",
                    "abstention_state": None,
                    "abstention_reason": None,
                    "probability_home_win": round(clip_probability(probability, clip), ROUND_DIGITS),
                }
            )
    rows.sort(key=lambda row: (row["ncaa_contest_id"], row["candidate_id"]))
    return rows


def assert_no_forecast_after_kickoff(rows: Iterable[Mapping[str, Any]]) -> None:
    for row in rows:
        if row.get("probability_home_win") is None:
            continue
        kickoff = row.get("kickoff_utc_conservative_lower_bound")
        if kickoff is None:
            raise ValueError("a frozen forecast carried no kickoff bound")
        if parse_utc(str(row["created_at_utc"])) >= parse_utc(str(kickoff)):
            raise ValueError(
                f"a forecast was created at or after kickoff: {row['ncaa_contest_id']}"
            )


def assert_one_probability_per_identity(rows: Iterable[Mapping[str, Any]]) -> None:
    seen: dict[tuple[str, str, str], float | None] = {}
    for row in rows:
        key = (
            str(row["ncaa_contest_id"]),
            str(row["candidate_id"]),
            str(row.get("snapshot_identity")),
        )
        probability = row.get("probability_home_win")
        if key in seen and seen[key] != probability:
            raise ValueError(f"two probabilities under one forecast identity: {key}")
        seen[key] = probability


# ---------------------------------------------------------------------------
# independent postgame scorer
# ---------------------------------------------------------------------------


def load_official_finals(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = Path(path)
    if not payload.is_file():
        return []
    with payload.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def score_forecasts(
    *,
    contract: Mapping[str, Any],
    forecasts: Sequence[Mapping[str, Any]],
    finals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Score frozen forecasts against official finals, or report the absence."""

    if contract["scoring"]["outcome_load_permitted_before_forecast_freeze"] is not False:
        raise ValueError("the scorer refuses a contract that permits early outcome access")
    frozen = [row for row in forecasts if row["forecast_state"] == "FORECAST_FROZEN"]
    by_contest: dict[str, dict[str, Any]] = {}
    for final in finals:
        by_contest[str(final["ncaa_contest_id"])] = dict(final)

    scored: list[dict[str, Any]] = []
    states: Counter[str] = Counter()
    for row in frozen:
        contest_id = str(row["ncaa_contest_id"])
        final = by_contest.get(contest_id)
        if final is None:
            states["AWAITING_OFFICIAL_FINAL"] += 1
            continue
        status = str(final.get("official_status") or "")
        if status in {"CANCELED", "SUSPENDED"}:
            states["CANCELED_OR_SUSPENDED"] += 1
            continue
        if status != "OFFICIAL_FINAL":
            states["OFFICIAL_FINAL_UNAVAILABLE"] += 1
            continue
        observed_at = parse_utc(str(final["outcome_observed_at_utc"]))
        if observed_at < parse_utc(str(row["created_at_utc"])):
            raise ValueError(
                f"an outcome was observed before its forecast was frozen: {contest_id}"
            )
        if observed_at < parse_utc(str(row["kickoff_utc_conservative_lower_bound"])):
            raise ValueError(f"an outcome was observed before kickoff: {contest_id}")
        if str(final["home_canonical_team_id"]) != str(row["home_canonical_team_id"]):
            states["FAIL_CLOSED_IDENTITY_MISMATCH"] += 1
            continue
        observed = float(final["home_win_indicator"])
        probability = float(row["probability_home_win"])
        scored.append(
            {
                "candidate_id": row["candidate_id"],
                "ncaa_contest_id": contest_id,
                "observed_home_win": observed,
                "probability_home_win": probability,
                "snapshot_identity": row["snapshot_identity"],
            }
        )
        states["SCORED"] += 1

    metrics: dict[str, Any] = {}
    for candidate_id in sorted({row["candidate_id"] for row in scored}):
        rows = [row for row in scored if row["candidate_id"] == candidate_id]
        brier = sum((row["probability_home_win"] - row["observed_home_win"]) ** 2 for row in rows)
        log_loss = 0.0
        correct = 0
        for row in rows:
            probability = row["probability_home_win"]
            observed = row["observed_home_win"]
            log_loss -= observed * math.log(probability) + (1.0 - observed) * math.log(
                1.0 - probability
            )
            if (probability >= 0.5) == (observed >= 0.5):
                correct += 1
        metrics[candidate_id] = {
            "accuracy": round(correct / len(rows), ROUND_DIGITS),
            "brier": round(brier / len(rows), ROUND_DIGITS),
            "log_loss": round(log_loss / len(rows), ROUND_DIGITS),
            "rows": len(rows),
            "calibration_support": "INSUFFICIENT_ROWS_FOR_CALIBRATION_BINS"
            if len(rows) < 20
            else "SUPPORTED",
        }
    result = PASS_RESULT if scored else AWAITING_RESULT
    return {
        "frozen_forecast_count": len(frozen),
        "official_final_count": len(by_contest),
        "metrics": metrics,
        "result": "PASS_PROSPECTIVE_2026_NATIONAL_SHADOW_SCORING" if scored else AWAITING_RESULT,
        "scored_rows": scored,
        "state_counts": dict(sorted(states.items())),
        "promotion_performed": False,
        "tuning_performed": False,
    }


# ---------------------------------------------------------------------------
# artifact assembly
# ---------------------------------------------------------------------------


def build_forecast_bundle(
    *,
    contract: Mapping[str, Any],
    baseline_contract: Mapping[str, Any],
    captures: Sequence[Mapping[str, Any]],
    documents: Mapping[str, str],
    population: Mapping[str, Mapping[str, Any]],
    fitted: Mapping[str, Any],
    model_identity: str,
    feature_identity: str,
    code_identity: str,
    execution_time: datetime,
) -> dict[str, Any]:
    assert_candidates_match_frozen_set(contract, baseline_contract)
    if execution_time > datetime.now(timezone.utc):
        raise ValueError("execution time must not be in the future")
    contests: list[dict[str, Any]] = []
    for capture in captures:
        if not bool(capture.get("cohort_rows_admitted", True)):
            continue
        game_date = str(capture["game_date"])
        for record in parse_scoreboard_document(documents[game_date], game_date=game_date):
            if record.get("parse_state") == "PARSED":
                # The official card lists the visiting program first.
                participants = [
                    resolve_participant(participant, population)
                    for participant in record["participants"]
                ]
                record = {
                    **dict(record),
                    "participants": participants,
                    "away_team": participants[0],
                    "home_team": participants[1],
                }
            contests.append(
                classify_contest(
                    record,
                    contract=contract,
                    capture=capture,
                    execution_time=execution_time,
                )
            )
    duplicates = sorted(
        contest_id
        for contest_id, count in Counter(row["ncaa_contest_id"] for row in contests).items()
        if count > 1 and contest_id
    )
    if duplicates:
        raise ValueError(f"official contest identifiers repeated: {duplicates}")
    contests.sort(key=lambda row: (row["source_published_game_date"], row["ncaa_contest_id"]))
    forecasts = freeze_forecasts(
        contract=contract,
        contests=contests,
        fitted=fitted,
        model_identity=model_identity,
        feature_identity=feature_identity,
        code_identity=code_identity,
        execution_time=execution_time,
    )
    assert_no_forecast_after_kickoff(forecasts)
    assert_one_probability_per_identity(forecasts)
    contest_states = dict(sorted(Counter(row["forecast_state"] for row in contests).items()))
    forecast_states = dict(sorted(Counter(row["forecast_state"] for row in forecasts).items()))
    for state in FORECAST_STATES:
        contest_states.setdefault(state, 0)
        forecast_states.setdefault(state, 0)
    return {
        "contests": contests,
        "forecasts": forecasts,
        "contest_state_counts": dict(sorted(contest_states.items())),
        "forecast_state_counts": dict(sorted(forecast_states.items())),
        "execution_time_utc": iso_utc(execution_time),
        "population_counts": {
            "contests_observed": len(contests),
            "snapshots_frozen": sum(
                1 for row in contests if row["forecast_state"] == "SNAPSHOT_FROZEN"
            ),
            "forecast_rows_emitted": len(forecasts),
            "forecast_rows_frozen": sum(
                1 for row in forecasts if row["forecast_state"] == "FORECAST_FROZEN"
            ),
            "admissible_candidates": len(admissible_candidates(contract)),
            "abstaining_candidates": len(abstaining_candidates(contract)),
        },
        "capture_inventory": [
            {
                "game_date": str(capture["game_date"]),
                "raw_sha256": str(capture["raw_sha256"]),
                "raw_relative_path": str(capture["raw_relative_path"]),
                "retrieved_at_utc": str(capture["retrieved_at_utc"]),
                "date_observation_state": str(
                    capture.get("date_observation_state", "OFFICIAL_CONTESTS_PRESENT")
                ),
                "route_id": str(capture.get("route_id", "UNRECORDED")),
            }
            for capture in captures
        ],
    }


def dataset_manifest(
    *,
    contract: Mapping[str, Any],
    bundle: Mapping[str, Any],
    payloads: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "PROSPECTIVE_2026_NATIONAL_SHADOW_FORECAST_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": CLASSIFICATION,
        "lane": LANE,
        "execution_time_utc": bundle["execution_time_utc"],
        "population_counts": dict(bundle["population_counts"]),
        "contest_state_counts": dict(bundle["contest_state_counts"]),
        "forecast_state_counts": dict(bundle["forecast_state_counts"]),
        "capture_inventory": list(bundle["capture_inventory"]),
        "payloads": [dict(item) for item in payloads],
        "authority": dict(contract["authority"]),
    }
    return {**core, "dataset_identity": stable_hash(core)}


def build_gate(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    bundle: Mapping[str, Any],
    manifest_relative_path: str,
    manifest_sha256: str,
    dataset_identity: str,
    predecessor_sha256: Mapping[str, str],
    model_identity: str,
    feature_identity: str,
    code_identity: str,
    fitted_summary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "PROSPECTIVE_2026_NATIONAL_SHADOW_FORECAST_GATE",
        "classification": CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": contract_sha256,
        "decision_unit": contract["decision_unit"],
        "local_issue_id": contract["local_issue_id"],
        "jira_key": contract["jira_key"],
        "parent_jira_key": contract["parent_jira_key"],
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "execution_time_utc": bundle["execution_time_utc"],
        "bound_predecessors": dict(sorted(predecessor_sha256.items())),
        "identities": {
            "code_identity": code_identity,
            "feature_identity": feature_identity,
            "model_identity": model_identity,
        },
        "fitted_candidates": dict(fitted_summary),
        "candidate_admissibility": [
            dict(entry) for entry in contract["forecast"]["candidate_admissibility"]
        ],
        "population_counts": dict(bundle["population_counts"]),
        "contest_state_counts": dict(bundle["contest_state_counts"]),
        "forecast_state_counts": dict(bundle["forecast_state_counts"]),
        "capture_inventory": list(bundle["capture_inventory"]),
        "frozen_forecast_contest_ids": sorted(
            {
                str(row["ncaa_contest_id"])
                for row in bundle["forecasts"]
                if row["forecast_state"] == "FORECAST_FROZEN"
            }
        ),
        "eligibility_gate": {
            "retroactive_forecast_created": False,
            "games_already_started_forecast": False,
            "backfilled_after_cutoff": False,
            "snapshot_cutoff_checkpoint_id": contract["snapshot"]["snapshot_cutoff_checkpoint_id"],
            "checkpoint_ids": list(contract["snapshot"]["checkpoint_ids"]),
            "outcome_accessible_before_forecast_freeze": False,
        },
        "manifest": {
            "relative_path": manifest_relative_path,
            "sha256": manifest_sha256,
            "dataset_identity": dataset_identity,
            "bulk_payloads_in_git": False,
        },
        "authority": dict(contract["authority"]),
        "negative_findings": dict(contract["negative_findings"]),
        "scientific_nonclaims": dict(contract["scientific_nonclaims"]),
    }


def validate_artifact(repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Independently revalidate the published forecast gate against the payloads."""

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    contract = load_contract(repo_root)
    gate = _read_json(repo_root / GATE_RELATIVE)
    findings: list[str] = []
    if gate.get("result") != PASS_RESULT:
        findings.append("gate result is not the declared pass result")
    if gate.get("contract_id") != CONTRACT_ID or gate.get("lane") != LANE:
        findings.append("gate contract identity or lane mismatch")
    if gate.get("contract_sha256") != sha256_file(repo_root / CONTRACT_RELATIVE):
        findings.append("contract hash drifted from the published gate")
    if binding_identity(gate, "gate_identity") != gate.get("gate_identity"):
        findings.append("gate identity does not recompute")
    for name, relative in (
        ("cohort", contract["bound_predecessors"]["cohort_gate_relative_path"]),
        ("baseline", contract["bound_predecessors"]["baseline_gate_relative_path"]),
        ("matrix", contract["bound_predecessors"]["matrix_gate_relative_path"]),
        ("spine", contract["bound_predecessors"]["spine_gate_relative_path"]),
    ):
        recorded = gate["bound_predecessors"].get(f"{name}_gate_sha256")
        if recorded != sha256_file(repo_root / relative):
            findings.append(f"bound predecessor hash drifted: {name}")
    manifest_path = data_root / gate["manifest"]["relative_path"]
    if not manifest_path.is_file():
        findings.append("dataset manifest is absent from the external data root")
        return {"result": "FAIL", "findings": findings}
    if sha256_file(manifest_path) != gate["manifest"]["sha256"]:
        findings.append("dataset manifest hash drifted")
    manifest = _read_json(manifest_path)
    if manifest.get("dataset_identity") != gate["manifest"]["dataset_identity"]:
        findings.append("dataset identity disagrees with the gate binding")
    if manifest_authoritative_sha256(manifest) != stable_hash(
        {
            key: value
            for key, value in manifest.items()
            if key not in NON_AUTHORITATIVE_MANIFEST_KEYS
        }
    ):
        findings.append("manifest authoritative hash is not reproducible")
    forecasts: list[dict[str, Any]] = []
    for payload in manifest["payloads"]:
        payload_path = data_root / payload["relative_path"]
        if not payload_path.is_file():
            findings.append(f"payload absent: {payload['name']}")
            continue
        if sha256_file(payload_path) != payload["sha256"]:
            findings.append(f"payload hash drifted: {payload['name']}")
            continue
        rows = [
            json.loads(line)
            for line in payload_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(rows) != int(payload["rows"]):
            findings.append(f"payload row count drifted: {payload['name']}")
        if payload["role"] == "PROSPECTIVE_2026_SHADOW_FORECAST_ROWS":
            forecasts = rows
    if forecasts:
        try:
            assert_no_forecast_after_kickoff(forecasts)
            assert_one_probability_per_identity(forecasts)
        except ValueError as error:
            findings.append(str(error))
        emitted = dict(sorted(Counter(row["forecast_state"] for row in forecasts).items()))
        for state, count in emitted.items():
            if int(gate["forecast_state_counts"].get(state, 0)) != count:
                findings.append(f"forecast state count drifted: {state}")
        frozen_ids = sorted(
            {
                str(row["ncaa_contest_id"])
                for row in forecasts
                if row["forecast_state"] == "FORECAST_FROZEN"
            }
        )
        if frozen_ids != list(gate["frozen_forecast_contest_ids"]):
            findings.append("frozen forecast contest identifiers drifted")
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def build_scoring_gate(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    forecast_gate: Mapping[str, Any],
    scoring: Mapping[str, Any],
    official_final_source: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "PROSPECTIVE_2026_NATIONAL_SHADOW_SCORING_GATE",
        "classification": CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": contract_sha256,
        "decision_unit": contract["decision_unit"],
        "local_issue_id": contract["local_issue_id"],
        "jira_key": contract["jira_key"],
        "parent_jira_key": contract["parent_jira_key"],
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "result": scoring["result"],
        "bound_forecast_gate_identity": forecast_gate["gate_identity"],
        "official_final_source": official_final_source,
        "frozen_forecast_count": scoring["frozen_forecast_count"],
        "official_final_count": scoring["official_final_count"],
        "state_counts": dict(scoring["state_counts"]),
        "metrics": dict(scoring["metrics"]),
        "scorer_controls": {
            "outcome_load_before_forecast_freeze_rejected": True,
            "forecast_created_after_kickoff_rejected": True,
            "canceled_or_suspended_state_preserved": True,
            "official_final_required": True,
            "tuning_performed": False,
            "promotion_performed": False,
        },
        "authority": dict(contract["authority"]),
        "scientific_nonclaims": dict(contract["scientific_nonclaims"]),
    }
