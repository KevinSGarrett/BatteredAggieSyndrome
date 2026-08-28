"""Offline tests for the prospective 2026 shadow forecast freeze and scorer.

Nothing here touches the network. Scoreboard fixtures reuse the official card
structure so that snapshot eligibility, candidate abstention, forecast identity,
and every scorer refusal can be exercised deterministically.
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.modeling.prospective_shadow_forecasts import (  # noqa: E402
    ADMISSIBLE,
    CONTRACT_ID,
    FORECAST_STATES,
    LANE,
    NOT_ADMISSIBLE,
    abstaining_candidates,
    admissible_candidates,
    assert_candidates_match_frozen_set,
    assert_no_forecast_after_kickoff,
    assert_one_probability_per_identity,
    base_rate,
    build_forecast_bundle,
    checkpoint_states,
    clip_probability,
    elo_probability_for_pair,
    load_contract,
    score_forecasts,
    snapshot_identity,
    training_population,
)
from test_prospective_shadow_cohort import (  # noqa: E402
    POPULATION,
    scoreboard_card,
    scoreboard_document,
)

CONTRACT = load_contract(REPO_ROOT)
BASELINE_CONTRACT = json.loads(
    (REPO_ROOT / "configs" / "national_expectation_baselines_and_peers_contract.json").read_text(
        encoding="utf-8-sig"
    )
)
ELO_HYPERPARAMETERS = next(
    item for item in BASELINE_CONTRACT["candidates"] if item["candidate_id"] == "national_elo"
)["hyperparameters"]

# Eligibility is a statement about the distance between now and kickoff, so the
# fixtures are anchored to the execution instant rather than to a hard-coded date.
EXECUTION_TIME = datetime.now(timezone.utc).replace(microsecond=0)
FUTURE_DATE = (EXECUTION_TIME + timedelta(days=7)).date().isoformat()
PAST_DATE = (EXECUTION_TIME - timedelta(days=7)).date().isoformat()


def capture(game_date: str) -> dict:
    return {
        "game_date": game_date,
        "raw_sha256": "a" * 64,
        "raw_relative_path": f"raw/x/{'a' * 64}.html",
        "retrieved_at_utc": iso(EXECUTION_TIME),
        "state": "CAPTURED",
        "declared_offset_seconds_for_window": -14400,
        "date_observation_state": "OFFICIAL_CONTESTS_PRESENT",
        "cohort_rows_admitted": True,
    }


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def document(
    annotation: str = "07:00 PM ESPN", *, game_date: str = "", neutral_site: str = ""
) -> str:
    game_date = game_date or FUTURE_DATE
    printable = datetime.strptime(game_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    card = scoreboard_card(
        contest_id="6607349",
        game_date=printable,
        annotation=annotation,
        away=("622345", "Missouri St."),
        home=("622300", "Texas A&M"),
        neutral_site=neutral_site,
    )
    return scoreboard_document([card], game_date=game_date)


def bundle(
    *,
    execution_time: datetime,
    annotation: str = "07:00 PM ESPN",
    game_date: str = "",
    neutral_site: str = "",
    ratings: dict[str, float] | None = None,
) -> dict:
    game_date = game_date or FUTURE_DATE
    fitted = {
        "national_base_rate": {"probability": 0.5},
        "national_elo": {
            "ratings": ratings if ratings is not None else {"SRC-002:TEAM:245": 1700.0},
            "hyperparameters": ELO_HYPERPARAMETERS,
        },
    }
    return build_forecast_bundle(
        contract=CONTRACT,
        baseline_contract=BASELINE_CONTRACT,
        captures=[capture(game_date)],
        documents={
            game_date: document(annotation, game_date=game_date, neutral_site=neutral_site)
        },
        population=POPULATION,
        fitted=fitted,
        model_identity="m" * 64,
        feature_identity="f" * 64,
        code_identity="c" * 64,
        execution_time=execution_time,
    )


class ContractTests(unittest.TestCase):
    def test_the_contract_is_observation_only_and_grants_no_promotion(self) -> None:
        self.assertEqual(CONTRACT["contract_id"], CONTRACT_ID)
        self.assertEqual(CONTRACT["lane"], LANE)
        self.assertFalse(CONTRACT["authority"]["champion_or_production_promotion"])
        self.assertFalse(CONTRACT["authority"]["forecast_publication"])
        self.assertFalse(CONTRACT["authority"]["protected_evaluation_admission"])

    def test_every_declared_state_belongs_to_the_implementation_vocabulary(self) -> None:
        declared = set(
            CONTRACT["states"]["progress_states"] + CONTRACT["states"]["terminal_or_side_states"]
        )
        self.assertEqual(declared, set(FORECAST_STATES))

    def test_the_candidate_set_is_exactly_the_phase_six_frozen_set(self) -> None:
        assert_candidates_match_frozen_set(CONTRACT, BASELINE_CONTRACT)
        self.assertEqual(len(admissible_candidates(CONTRACT)), 2)
        self.assertEqual(len(abstaining_candidates(CONTRACT)), 3)

    def test_a_candidate_that_was_never_frozen_is_rejected(self) -> None:
        smuggled = json.loads(json.dumps(CONTRACT))
        smuggled["forecast"]["candidate_admissibility"].append(
            {
                "candidate_id": "gradient_boosted_smuggle",
                "admissibility": ADMISSIBLE,
                "required_feature_scope": "NONE",
                "reason": "invented after the freeze",
            }
        )
        with self.assertRaises(ValueError):
            assert_candidates_match_frozen_set(smuggled, BASELINE_CONTRACT)

    def test_a_dropped_frozen_candidate_is_rejected(self) -> None:
        truncated = json.loads(json.dumps(CONTRACT))
        truncated["forecast"]["candidate_admissibility"] = truncated["forecast"][
            "candidate_admissibility"
        ][:2]
        with self.assertRaises(ValueError):
            assert_candidates_match_frozen_set(truncated, BASELINE_CONTRACT)

    def test_a_contract_permitting_early_outcome_access_is_rejected(self) -> None:
        loosened = json.loads(json.dumps(CONTRACT))
        loosened["scoring"]["outcome_load_permitted_before_forecast_freeze"] = True
        with self.assertRaises(ValueError):
            score_forecasts(contract=loosened, forecasts=[], finals=[])


class CheckpointTests(unittest.TestCase):
    def test_an_open_checkpoint_becomes_closed_once_its_deadline_passes(self) -> None:
        kickoff = datetime(2026, 9, 5, 23, 0, tzinfo=timezone.utc)
        early = checkpoint_states(kickoff=kickoff, execution_time=kickoff - timedelta(days=3))
        self.assertEqual({row["state"] for row in early}, {"OPEN"})
        late = checkpoint_states(kickoff=kickoff, execution_time=kickoff - timedelta(minutes=10))
        self.assertEqual({row["state"] for row in late}, {"CLOSED"})

    def test_no_checkpoint_is_evaluated_without_a_published_clock(self) -> None:
        states = checkpoint_states(kickoff=None, execution_time=datetime.now(timezone.utc))
        self.assertEqual(
            {row["state"] for row in states}, {"NOT_EVALUATED_WITHOUT_A_PUBLISHED_CLOCK"}
        )

    def test_a_snapshot_identity_changes_when_the_kickoff_changes(self) -> None:
        common = {
            "contest_id": "6607349",
            "capture_sha256": "a" * 64,
            "home_team_id": "SRC-002:TEAM:245",
            "away_team_id": "SRC-002:TEAM:2623",
            "cutoff_checkpoint_id": "T_MINUS_90M",
            "frozen_at_utc": "2026-09-04T12:00:00Z",
        }
        first = snapshot_identity(kickoff_lower_bound="2026-09-05T23:00:00Z", **common)
        second = snapshot_identity(kickoff_lower_bound="2026-09-06T00:00:00Z", **common)
        self.assertNotEqual(first, second)


class CandidateTests(unittest.TestCase):
    def test_the_base_rate_counts_a_tie_as_one_half(self) -> None:
        features = [
            {
                "canonical_game_id": "G1",
                "canonical_team_id": "A",
                "season": 2000,
                "chronological_ordinal": 1,
            },
            {
                "canonical_game_id": "G1",
                "canonical_team_id": "B",
                "season": 2000,
                "chronological_ordinal": 2,
            },
        ]
        labels = [
            {
                "canonical_game_id": "G1",
                "canonical_team_id": "A",
                "label_win": False,
                "label_tie": True,
            },
            {
                "canonical_game_id": "G1",
                "canonical_team_id": "B",
                "label_win": False,
                "label_tie": True,
            },
        ]
        training, index = training_population(
            features, labels, last_admitted_season=2023, sealed_seasons=[2024, 2025]
        )
        self.assertEqual(len(training), 2)
        self.assertAlmostEqual(base_rate(training, index), 0.5)

    def test_sealed_seasons_never_enter_the_training_population(self) -> None:
        features = [
            {
                "canonical_game_id": "G1",
                "canonical_team_id": "A",
                "season": 2024,
                "chronological_ordinal": 1,
            }
        ]
        labels = [
            {
                "canonical_game_id": "G1",
                "canonical_team_id": "A",
                "label_win": True,
                "label_tie": False,
            }
        ]
        training, _ = training_population(
            features, labels, last_admitted_season=2023, sealed_seasons=[2024, 2025]
        )
        self.assertEqual(training, [])

    def test_the_home_advantage_disappears_at_a_neutral_site(self) -> None:
        ratings = {"H": 1500.0, "A": 1500.0}
        home = elo_probability_for_pair(
            ratings=ratings,
            home_team_id="H",
            away_team_id="A",
            is_neutral_site=False,
            hyperparameters=ELO_HYPERPARAMETERS,
        )
        neutral = elo_probability_for_pair(
            ratings=ratings,
            home_team_id="H",
            away_team_id="A",
            is_neutral_site=True,
            hyperparameters=ELO_HYPERPARAMETERS,
        )
        self.assertGreater(home, 0.5)
        self.assertAlmostEqual(neutral, 0.5)

    def test_a_probability_is_clipped_away_from_certainty(self) -> None:
        self.assertEqual(clip_probability(0.0, [0.001, 0.999]), 0.001)
        self.assertEqual(clip_probability(1.0, [0.001, 0.999]), 0.999)


class ForecastFreezeTests(unittest.TestCase):
    def test_an_eligible_contest_freezes_a_snapshot_and_two_probabilities(self) -> None:
        result = bundle(execution_time=EXECUTION_TIME)
        contest = result["contests"][0]
        self.assertEqual(contest["forecast_state"], "SNAPSHOT_FROZEN")
        self.assertIsNotNone(contest["snapshot"]["snapshot_identity"])
        frozen = [
            row for row in result["forecasts"] if row["forecast_state"] == "FORECAST_FROZEN"
        ]
        self.assertEqual({row["candidate_id"] for row in frozen}, {"national_base_rate", "national_elo"})
        for row in frozen:
            self.assertGreater(row["probability_home_win"], 0.0)
            self.assertLess(row["probability_home_win"], 1.0)
            self.assertEqual(row["forecast_authority"], LANE)

    def test_the_three_unsatisfiable_candidates_abstain_explicitly(self) -> None:
        result = bundle(execution_time=EXECUTION_TIME)
        abstained = [
            row
            for row in result["forecasts"]
            if row["candidate_admissibility"] == NOT_ADMISSIBLE
        ]
        self.assertEqual(len(abstained), 3)
        for row in abstained:
            self.assertEqual(row["forecast_state"], "MISSING_REQUIRED_FEATURES_ABSTAIN")
            self.assertIsNone(row["probability_home_win"])
            self.assertTrue(row["abstention_reason"])

    def test_a_contest_past_the_cutoff_is_never_backfilled(self) -> None:
        result = bundle(execution_time=EXECUTION_TIME, game_date=PAST_DATE)
        self.assertEqual(result["contests"][0]["forecast_state"], "MISSED_CUTOFF_NO_BACKFILL")
        self.assertEqual(
            {row["forecast_state"] for row in result["forecasts"]},
            {"MISSED_CUTOFF_NO_BACKFILL"},
        )
        self.assertTrue(all(row["probability_home_win"] is None for row in result["forecasts"]))

    def test_an_unpublished_kickoff_clock_abstains_rather_than_guessing(self) -> None:
        result = bundle(execution_time=EXECUTION_TIME, annotation="TBA ESPN")
        self.assertEqual(
            result["contests"][0]["forecast_state"], "MISSING_REQUIRED_FEATURES_ABSTAIN"
        )

    def test_an_unresolved_participant_is_unsupported_rather_than_guessed(self) -> None:
        thin = {"missouri state": POPULATION["missouri state"]}
        result = build_forecast_bundle(
            contract=CONTRACT,
            baseline_contract=BASELINE_CONTRACT,
            captures=[capture(FUTURE_DATE)],
            documents={FUTURE_DATE: document()},
            population=thin,
            fitted={
                "national_base_rate": {"probability": 0.5},
                "national_elo": {"ratings": {}, "hyperparameters": ELO_HYPERPARAMETERS},
            },
            model_identity="m" * 64,
            feature_identity="f" * 64,
            code_identity="c" * 64,
            execution_time=EXECUTION_TIME,
        )
        self.assertEqual(result["contests"][0]["forecast_state"], "UNSUPPORTED_ENTITY")

    def test_a_future_execution_time_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            bundle(execution_time=datetime.now(timezone.utc) + timedelta(days=1))

    def test_no_frozen_forecast_may_be_created_at_or_after_kickoff(self) -> None:
        rows = [
            {
                "ncaa_contest_id": "1",
                "candidate_id": "national_elo",
                "created_at_utc": "2026-09-05T23:00:00Z",
                "kickoff_utc_conservative_lower_bound": "2026-09-05T23:00:00Z",
                "probability_home_win": 0.6,
                "snapshot_identity": "s",
            }
        ]
        with self.assertRaises(ValueError):
            assert_no_forecast_after_kickoff(rows)

    def test_one_identity_may_not_carry_two_probabilities(self) -> None:
        rows = [
            {
                "ncaa_contest_id": "1",
                "candidate_id": "national_elo",
                "snapshot_identity": "s",
                "probability_home_win": 0.6,
            },
            {
                "ncaa_contest_id": "1",
                "candidate_id": "national_elo",
                "snapshot_identity": "s",
                "probability_home_win": 0.7,
            },
        ]
        with self.assertRaises(ValueError):
            assert_one_probability_per_identity(rows)


class ScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.forecast = {
            "ncaa_contest_id": "6607349",
            "candidate_id": "national_elo",
            "forecast_state": "FORECAST_FROZEN",
            "created_at_utc": "2026-09-04T12:00:00Z",
            "kickoff_utc_conservative_lower_bound": "2026-09-05T23:00:00Z",
            "home_canonical_team_id": "SRC-002:TEAM:245",
            "probability_home_win": 0.75,
            "snapshot_identity": "s",
        }

    def final(self, **overrides: object) -> dict:
        base = {
            "ncaa_contest_id": "6607349",
            "official_status": "OFFICIAL_FINAL",
            "home_canonical_team_id": "SRC-002:TEAM:245",
            "home_win_indicator": 1.0,
            "outcome_observed_at_utc": "2026-09-06T04:00:00Z",
        }
        base.update(overrides)
        return base

    def test_without_any_official_final_the_scorer_waits(self) -> None:
        result = score_forecasts(contract=CONTRACT, forecasts=[self.forecast], finals=[])
        self.assertEqual(result["result"], "AWAITING_ELIGIBLE_OFFICIAL_FINALS")
        self.assertEqual(result["state_counts"], {"AWAITING_OFFICIAL_FINAL": 1})
        self.assertEqual(result["metrics"], {})

    def test_an_official_final_is_scored_without_tuning_or_promotion(self) -> None:
        result = score_forecasts(
            contract=CONTRACT, forecasts=[self.forecast], finals=[self.final()]
        )
        self.assertEqual(result["result"], "PASS_PROSPECTIVE_2026_NATIONAL_SHADOW_SCORING")
        metrics = result["metrics"]["national_elo"]
        self.assertAlmostEqual(metrics["brier"], 0.0625)
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["calibration_support"], "INSUFFICIENT_ROWS_FOR_CALIBRATION_BINS")
        self.assertFalse(result["tuning_performed"])
        self.assertFalse(result["promotion_performed"])

    def test_an_outcome_observed_before_the_freeze_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            score_forecasts(
                contract=CONTRACT,
                forecasts=[self.forecast],
                finals=[self.final(outcome_observed_at_utc="2026-09-04T11:00:00Z")],
            )

    def test_an_outcome_observed_before_kickoff_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            score_forecasts(
                contract=CONTRACT,
                forecasts=[self.forecast],
                finals=[self.final(outcome_observed_at_utc="2026-09-05T22:00:00Z")],
            )

    def test_a_canceled_contest_keeps_its_own_state(self) -> None:
        result = score_forecasts(
            contract=CONTRACT,
            forecasts=[self.forecast],
            finals=[self.final(official_status="CANCELED")],
        )
        self.assertEqual(result["state_counts"], {"CANCELED_OR_SUSPENDED": 1})
        self.assertEqual(result["result"], "AWAITING_ELIGIBLE_OFFICIAL_FINALS")

    def test_an_unfinished_contest_is_not_scored(self) -> None:
        result = score_forecasts(
            contract=CONTRACT,
            forecasts=[self.forecast],
            finals=[self.final(official_status="IN_PROGRESS")],
        )
        self.assertEqual(result["state_counts"], {"OFFICIAL_FINAL_UNAVAILABLE": 1})

    def test_a_disagreeing_home_identity_fails_closed(self) -> None:
        result = score_forecasts(
            contract=CONTRACT,
            forecasts=[self.forecast],
            finals=[self.final(home_canonical_team_id="SRC-002:TEAM:999")],
        )
        self.assertEqual(result["state_counts"], {"FAIL_CLOSED_IDENTITY_MISMATCH": 1})

    def test_an_abstained_forecast_is_never_scored(self) -> None:
        abstained = {**self.forecast, "forecast_state": "MISSING_REQUIRED_FEATURES_ABSTAIN"}
        result = score_forecasts(
            contract=CONTRACT, forecasts=[abstained], finals=[self.final()]
        )
        self.assertEqual(result["frozen_forecast_count"], 0)
        self.assertEqual(result["result"], "AWAITING_ELIGIBLE_OFFICIAL_FINALS")


if __name__ == "__main__":
    unittest.main()
