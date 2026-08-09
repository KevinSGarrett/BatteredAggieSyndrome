from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv
import json
from typing import Any

from aggie_analytics.data.adapters import CsvSourceAdapter
from aggie_analytics.data.snapshots import RawSnapshotStore
from aggie_analytics.entities.contracts import SourceEntityKey
from aggie_analytics.entities.resolution import AliasRecord, EntityResolver
from aggie_analytics.features.factory import FeatureSpec, build_features
from aggie_analytics.modeling.forecast import ForecastSnapshot
from aggie_analytics.modeling.joint import IndependentPoissonScoreRuntime
from aggie_analytics.modeling.runtime import FeatureVector as ModelFeatureVector, ModelArtifact
from aggie_analytics.orchestration.publication import ImmutableForecastPublisher
from aggie_analytics.product.repository import PublishedSnapshotRepository
from aggie_analytics.product.service import ForecastProductService
from aggie_analytics.temporal.contracts import ForecastCutoff, TemporalObservation
from aggie_analytics.temporal.eligibility import evaluate_eligibility
from aggie_analytics.temporal.state import build_pit_state

UTC = timezone.utc


def _write_input(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["team", "expected_team_points", "expected_opponent_points"])
        writer.writeheader()
        writer.writerow({"team": "Texas A&M", "expected_team_points": "28", "expected_opponent_points": "24"})


def _fixed_times() -> tuple[datetime, datetime, datetime]:
    training = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
    cutoff = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    kickoff = datetime(2026, 8, 2, 0, 0, tzinfo=UTC)
    return training, cutoff, kickoff


def run_synthetic_e2e(root: Path) -> dict[str, Any]:
    """Exercise the real W19→W22 starter path with synthetic evidence only.

    The function intentionally does not download data or fit a model. It verifies
    contract integration, lineage preservation, temporal filtering, coherent
    forecast derivation, immutable publication and read-only product serving.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    training_time, cutoff_time, kickoff_time = _fixed_times()

    source_file = root / "input" / "synthetic_expectations.csv"
    _write_input(source_file)
    adapter = CsvSourceAdapter("SRC-SYNTHETIC-W24", "team_expectations")
    records = adapter.read(source_file)
    if len(records) != 1:
        raise AssertionError("synthetic adapter contract did not yield exactly one row")

    raw_store = RawSnapshotStore(root / "lake")
    raw = raw_store.ingest_file(
        "SRC-SYNTHETIC-W24",
        "team_expectations",
        source_file,
        retrieved_at=cutoff_time - timedelta(hours=2),
        source_uri="synthetic://w24/team_expectations",
        row_count=len(records),
        schema_fields=tuple(records[0].payload),
        metadata={"fixture_kind": "SYNTHETIC_W24_E2E"},
    )

    resolver = EntityResolver([
        AliasRecord("TEAM", "Texas A&M", "team-tamu", "SRC-SYNTHETIC-W24"),
    ])
    entity = resolver.resolve(
        SourceEntityKey("SRC-SYNTHETIC-W24", "TEAM", "Texas A&M"),
        "Texas A&M",
        "resolution-w24-tamu",
    )
    if entity.decision_state != "RESOLVED" or entity.selected_canonical_id != "team-tamu":
        raise AssertionError("synthetic team failed deterministic entity resolution")

    payload = records[0].payload
    eligible = TemporalObservation(
        observation_id="obs-w24-team-expectation",
        source_observation_id=f"{raw.snapshot_id}:1",
        domain="TEAM_EXPECTATION",
        retrieved_at=cutoff_time - timedelta(hours=2),
        first_known_at=cutoff_time - timedelta(hours=3),
        temporal_policy_version="w24-e2e-v1",
        attributes={
            "expected_team_points": float(payload["expected_team_points"]),
            "expected_opponent_points": float(payload["expected_opponent_points"]),
            "canonical_team_id": entity.selected_canonical_id,
        },
    )
    future = TemporalObservation(
        observation_id="obs-w24-future-forbidden",
        source_observation_id="future:1",
        domain="TEAM_EXPECTATION",
        retrieved_at=cutoff_time + timedelta(hours=2),
        first_known_at=cutoff_time + timedelta(hours=1),
        temporal_policy_version="w24-e2e-v1",
        attributes={"expected_team_points": 99.0, "expected_opponent_points": 0.0},
    )
    cutoff = ForecastCutoff(
        cutoff_id="w24-cutoff",
        purpose="FORECAST_SNAPSHOT",
        prediction_timestamp=cutoff_time,
        target_event_time=kickoff_time,
        forecast_lane="PURE_FOOTBALL",
        temporal_policy_version="w24-e2e-v1",
        data_snapshot_id=raw.snapshot_id,
        target_game_id="tamu-lsu-2026-w24",
    )
    state = build_pit_state((eligible, future), cutoff)
    if [o.observation_id for o in state.observations] != [eligible.observation_id]:
        raise AssertionError("future observation crossed PIT boundary")

    feature_specs = (
        FeatureSpec("expected_team_points", "TEAM_EXPECTATION", "expected_team_points"),
        FeatureSpec("expected_opponent_points", "TEAM_EXPECTATION", "expected_opponent_points"),
    )
    features = build_features(state, feature_specs)
    lineage_refs = (raw.snapshot_id, state.lineage.lineage_id, *(x.lineage_id for x in features.lineage))
    model_row = ModelFeatureVector(
        game_id=cutoff.target_game_id or "synthetic-game",
        forecast_cutoff=cutoff_time,
        feature_snapshot_id=features.state_id,
        values={k: float(v) for k, v in features.values.items()},
        lineage_refs=tuple(lineage_refs),
    )
    artifact = ModelArtifact(
        model_id="w24-independent-poisson-starter",
        model_version="synthetic-v1",
        model_family="INDEPENDENT_POISSON_STARTER",
        target="JOINT_SCORE",
        feature_names=("expected_team_points", "expected_opponent_points"),
        parameters={"max_score": 70, "overtime_team_win_probability": 0.5},
        training_data_ref="synthetic://w24/training-before-cutoff",
        training_cutoff=training_time,
        created_at=training_time + timedelta(hours=1),
        metadata={"fixture_kind": "SYNTHETIC_W24_E2E"},
    )
    runtime = IndependentPoissonScoreRuntime(artifact)
    distribution = runtime.predict_distribution(model_row)
    forecast = ForecastSnapshot(
        snapshot_id="w24-e2e-snapshot",
        game_id=model_row.game_id,
        feature_snapshot_id=model_row.feature_snapshot_id,
        model_artifact_sha256=artifact.artifact_sha256,
        distribution=distribution,
        bas_anchor_expected_margin=4.0,
        lineage_refs=tuple(lineage_refs),
    )
    summary = forecast.public_summary()
    if abs(summary["win_probability"] + summary["loss_probability"] - 1.0) > 1e-9:
        raise AssertionError("coherent win/loss probabilities do not sum to one")

    publication_root = root / "published"
    publisher = ImmutableForecastPublisher(publication_root)
    published_path = publisher.publish(
        snapshot_id=forecast.snapshot_id,
        game_id=forecast.game_id,
        forecast_cutoff=cutoff_time,
        model_artifact_sha256=artifact.artifact_sha256,
        feature_snapshot_id=model_row.feature_snapshot_id,
        public_summary=summary,
        lineage_refs=tuple(lineage_refs),
        market_lane="PURE_FOOTBALL",
        teams={"team_name": "Texas A&M", "opponent_name": "LSU"},
        source_metadata=[{"source_id": raw.source_id, "raw_snapshot_id": raw.snapshot_id, "raw_sha256": raw.raw_sha256}],
        model_metadata={"model_family": artifact.model_family, "training_cutoff": artifact.training_cutoff.isoformat()},
        data_snapshot_refs=[raw.snapshot_id],
        warnings=["SYNTHETIC_W24_READINESS_ONLY"],
        public_metadata={"readiness_scope": "CONTRACT_INTEGRATION_NOT_EMPIRICAL_REPLAY"},
    )
    published_payload = json.loads(Path(published_path).read_text(encoding="utf-8"))
    as_of = datetime.fromisoformat(published_payload["published_at"]) + timedelta(seconds=1)
    service = ForecastProductService(PublishedSnapshotRepository(publication_root))
    served = service.forecast(forecast.game_id, market_lane="PURE_FOOTBALL", now=as_of)
    if served["lineage"]["model_artifact_sha256"] != artifact.artifact_sha256:
        raise AssertionError("model lineage was not preserved through serving")
    if raw.snapshot_id not in served["lineage"]["data_snapshot_refs"]:
        raise AssertionError("raw snapshot lineage was not preserved through serving")

    return {
        "schema_version": "aggie.readiness.e2e.v1",
        "scope": "SYNTHETIC_CONTRACT_INTEGRATION_ONLY",
        "empirical_historical_replay_completed": False,
        "game_id": forecast.game_id,
        "raw_snapshot_id": raw.snapshot_id,
        "raw_sha256": raw.raw_sha256,
        "entity_decision_state": entity.decision_state,
        "pit_state_id": state.state_id,
        "pit_observation_ids": [o.observation_id for o in state.observations],
        "feature_snapshot_id": model_row.feature_snapshot_id,
        "model_artifact_sha256": artifact.artifact_sha256,
        "published_snapshot_id": forecast.snapshot_id,
        "served_snapshot_id": served["snapshot"]["snapshot_id"],
        "market_lane": served["snapshot"]["market_lane"],
        "lineage_refs": list(lineage_refs),
        "checks": {
            "adapter": True,
            "raw_snapshot": True,
            "entity_resolution": True,
            "pit_future_exclusion": True,
            "feature_construction": True,
            "model_training_precedes_prediction": True,
            "joint_score_coherence": True,
            "bas_nested": summary["bas_ge_21"] <= summary["bas_ge_14"] <= summary["bas_ge_7"] <= summary["bas_ge_3"],
            "immutable_publication": True,
            "snapshot_only_serving": served["serving_mode"] == "IMMUTABLE_PUBLISHED_SNAPSHOT_ONLY",
            "lineage_preserved": True,
        },
    }


def run_leakage_battery() -> dict[str, Any]:
    _, cutoff_time, kickoff_time = _fixed_times()
    cutoff = ForecastCutoff(
        cutoff_id="w24-leakage-cutoff",
        purpose="FORECAST_SNAPSHOT",
        prediction_timestamp=cutoff_time,
        target_event_time=kickoff_time,
        forecast_lane="PURE_FOOTBALL",
        temporal_policy_version="w24-leakage-v1",
        data_snapshot_id="synthetic-leakage",
        target_game_id="target-game",
    )
    cases = {
        "eligible_prior": TemporalObservation("obs-ok", "src-ok", "TEAM_STATE", cutoff_time-timedelta(hours=1), "w24-leakage-v1", first_known_at=cutoff_time-timedelta(hours=2), attributes={"value": 1}),
        "known_after_cutoff": TemporalObservation("obs-future", "src-future", "TEAM_STATE", cutoff_time+timedelta(minutes=1), "w24-leakage-v1", first_known_at=cutoff_time+timedelta(minutes=1), attributes={"value": 2}),
        "observed_weather": TemporalObservation("obs-weather", "src-weather", "WEATHER_OBSERVED", cutoff_time-timedelta(hours=1), "w24-leakage-v1", first_known_at=cutoff_time-timedelta(hours=1), attributes={"temperature": 75}),
        "retrospective_uncorroborated": TemporalObservation("obs-retro", "src-retro", "TEAM_STATE", cutoff_time-timedelta(days=1), "w24-leakage-v1", first_known_at=cutoff_time-timedelta(days=1), retrospective_flag=True, attributes={"value": 3}),
        "target_game_output": TemporalObservation("obs-target-output", "src-target-output", "HISTORICAL_GAME_OUTPUT", cutoff_time-timedelta(days=1), "w24-leakage-v1", first_known_at=cutoff_time-timedelta(days=1), attributes={"game_id":"target-game", "game_end_at": (cutoff_time-timedelta(days=1)).isoformat()}),
        "other_completed_game_output": TemporalObservation("obs-other-output", "src-other-output", "HISTORICAL_GAME_OUTPUT", cutoff_time-timedelta(days=1), "w24-leakage-v1", first_known_at=cutoff_time-timedelta(days=1), attributes={"game_id":"other-game", "game_end_at": (cutoff_time-timedelta(days=1)).isoformat()}),
        "weather_run_after_cutoff": TemporalObservation("obs-weather-run", "src-weather-run", "WEATHER_FORECAST", cutoff_time-timedelta(hours=1), "w24-leakage-v1", first_known_at=cutoff_time-timedelta(hours=1), attributes={"model_available_at": (cutoff_time+timedelta(minutes=5)).isoformat(), "forecast_valid_at": kickoff_time.isoformat()}),
    }
    expected = {
        "eligible_prior": (True, "ELIGIBLE"),
        "known_after_cutoff": (False, "KNOWN_AFTER_CUTOFF"),
        "observed_weather": (False, "DOMAIN_POLICY_BANNED"),
        "retrospective_uncorroborated": (False, "RETROSPECTIVE_UNCORROBORATED"),
        "target_game_output": (False, "TARGET_GAME_OUTPUT"),
        "other_completed_game_output": (True, "ELIGIBLE"),
        "weather_run_after_cutoff": (False, "KNOWN_AFTER_CUTOFF"),
    }
    results: dict[str, Any] = {}
    for name, obs in cases.items():
        got = evaluate_eligibility(obs, cutoff)
        exp = expected[name]
        if (got.eligible, got.reason) != exp:
            raise AssertionError(f"leakage case {name}: got {(got.eligible, got.reason)} expected {exp}")
        results[name] = {"eligible": got.eligible, "reason": got.reason}
    return {"schema_version":"aggie.readiness.leakage.v1", "cases":results, "all_expected":True}


def replay_readiness_report(root: Path) -> dict[str, Any]:
    """Check deterministic starter replay prerequisites without claiming empirical replay."""
    first = run_synthetic_e2e(Path(root) / "replay")
    second = run_synthetic_e2e(Path(root) / "replay")
    stable_fields = ("raw_sha256", "pit_state_id", "feature_snapshot_id", "model_artifact_sha256", "published_snapshot_id", "market_lane")
    deterministic = all(first[k] == second[k] for k in stable_fields)
    if not deterministic:
        raise AssertionError("synthetic replay contract was not deterministic")
    return {
        "schema_version":"aggie.readiness.replay.v1",
        "status":"READY_FOR_MATERIALIZED_HISTORICAL_REPLAY",
        "empirical_historical_replay_completed":False,
        "protected_historical_metrics_claimed":False,
        "deterministic_contract_replay":True,
        "stable_fields":list(stable_fields),
        "required_next_evidence":[
            "materialized point-in-time historical source snapshots",
            "protected chronological split assignments",
            "actual target labels only after each replayed game completes",
            "protected evaluation output generated outside training/research mutation paths",
        ],
    }
