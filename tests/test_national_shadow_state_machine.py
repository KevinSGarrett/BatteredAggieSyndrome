"""Mutation tests for the append-only national shadow state machine."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aggie_analytics.modeling.national_shadow_state_machine import (
    PROGRESS_STATES,
    SIDE_STATES,
    ShadowStateLedger,
    StateMachineRejection,
    Transition,
    evaluate_gap,
    load_contract,
    reevaluate_gaps,
    replay_cohort,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

NOW = datetime.now(timezone.utc)
KICKOFF = NOW + timedelta(days=5)
FROZEN_AT = NOW - timedelta(hours=1)
FINAL_AT = KICKOFF + timedelta(hours=4)

FROZEN_CANDIDATES = frozenset(
    {
        "national_base_rate",
        "national_elo",
        "prior_only",
        "national_logistic_l2",
        "national_margin_ridge",
    }
)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ledger() -> ShadowStateLedger:
    return ShadowStateLedger(frozen_candidate_ids=FROZEN_CANDIDATES)


def step(
    sequence: int,
    from_state: str,
    to_state: str,
    **overrides,
) -> Transition:
    payload = {
        "entity_id": "6607349::national_elo",
        "entity_kind": "FORECAST",
        "sequence": sequence,
        "from_state": from_state,
        "to_state": to_state,
        "at_utc": iso(FROZEN_AT),
        "source_identity": "s" * 64,
        "kickoff_utc": iso(KICKOFF),
        "snapshot_identity": "p" * 64,
        "forecast_identity": "f" * 64,
        "candidate_id": "national_elo",
    }
    payload.update(overrides)
    return Transition(**payload)


def advance_to_forecast_frozen(book: ShadowStateLedger, probability: float = 0.8) -> None:
    book.append(step(1, "PRECOMMITTED", "SNAPSHOT_ELIGIBLE"))
    book.append(step(2, "SNAPSHOT_ELIGIBLE", "SNAPSHOT_FROZEN"))
    book.append(
        step(3, "SNAPSHOT_FROZEN", "FORECAST_FROZEN", probability_home_win=probability)
    )


class Vocabulary(unittest.TestCase):
    def test_contract_matches_the_implementation(self) -> None:
        contract = load_contract(REPO_ROOT)
        self.assertEqual(tuple(contract["state_machine"]["progress_states"]), PROGRESS_STATES)
        self.assertEqual(tuple(contract["state_machine"]["terminal_or_side_states"]), SIDE_STATES)
        self.assertTrue(all(contract["state_machine"]["rejections"].values()))


class ForwardOnly(unittest.TestCase):
    def test_happy_path_reaches_awaiting_official_final(self) -> None:
        book = ledger()
        advance_to_forecast_frozen(book)
        book.append(step(4, "FORECAST_FROZEN", "AWAITING_OFFICIAL_FINAL"))
        self.assertEqual(book.current_state("6607349::national_elo"), "AWAITING_OFFICIAL_FINAL")

    def test_backward_transition_is_rejected(self) -> None:
        book = ledger()
        advance_to_forecast_frozen(book)
        with self.assertRaises(StateMachineRejection):
            book.append(step(4, "FORECAST_FROZEN", "SNAPSHOT_FROZEN"))

    def test_state_skip_is_rejected(self) -> None:
        book = ledger()
        with self.assertRaises(StateMachineRejection):
            book.append(step(1, "PRECOMMITTED", "FORECAST_FROZEN", probability_home_win=0.5))

    def test_nonmonotonic_sequence_is_rejected(self) -> None:
        book = ledger()
        book.append(step(1, "PRECOMMITTED", "SNAPSHOT_ELIGIBLE"))
        with self.assertRaises(StateMachineRejection):
            book.append(step(3, "SNAPSHOT_ELIGIBLE", "SNAPSHOT_FROZEN"))

    def test_a_terminal_state_accepts_no_further_transition(self) -> None:
        book = ledger()
        book.append(step(1, "PRECOMMITTED", "MISSED_CUTOFF_NO_BACKFILL"))
        with self.assertRaises(StateMachineRejection):
            book.append(step(2, "MISSED_CUTOFF_NO_BACKFILL", "SNAPSHOT_ELIGIBLE"))

    def test_a_declared_origin_mismatch_is_rejected(self) -> None:
        book = ledger()
        book.append(step(1, "PRECOMMITTED", "SNAPSHOT_ELIGIBLE"))
        with self.assertRaises(StateMachineRejection):
            book.append(step(2, "SNAPSHOT_FROZEN", "FORECAST_FROZEN", probability_home_win=0.5))


class ForecastIntegrity(unittest.TestCase):
    def test_retroactive_forecast_is_rejected(self) -> None:
        book = ledger()
        book.append(step(1, "PRECOMMITTED", "SNAPSHOT_ELIGIBLE"))
        book.append(step(2, "SNAPSHOT_ELIGIBLE", "SNAPSHOT_FROZEN"))
        with self.assertRaises(StateMachineRejection):
            book.append(
                step(
                    3,
                    "SNAPSHOT_FROZEN",
                    "FORECAST_FROZEN",
                    at_utc=iso(KICKOFF + timedelta(minutes=1)),
                    probability_home_win=0.7,
                )
            )

    def test_changed_probability_under_one_identity_is_rejected(self) -> None:
        book = ledger()
        advance_to_forecast_frozen(book, probability=0.8)
        book.append(step(4, "FORECAST_FROZEN", "AWAITING_OFFICIAL_FINAL"))
        second = ledger()
        second._probability[("6607349::national_elo", "f" * 64)] = 0.8  # noqa: SLF001
        second._state["6607349::national_elo"] = "SNAPSHOT_FROZEN"  # noqa: SLF001
        second._sequence["6607349::national_elo"] = 2  # noqa: SLF001
        second._kickoff["6607349::national_elo"] = (iso(KICKOFF), "s" * 64)  # noqa: SLF001
        with self.assertRaises(StateMachineRejection):
            second.append(
                step(3, "SNAPSHOT_FROZEN", "FORECAST_FROZEN", probability_home_win=0.42)
            )

    def test_changed_kickoff_without_a_new_source_identity_is_rejected(self) -> None:
        book = ledger()
        book.append(step(1, "PRECOMMITTED", "SNAPSHOT_ELIGIBLE"))
        with self.assertRaises(StateMachineRejection):
            book.append(
                step(
                    2,
                    "SNAPSHOT_ELIGIBLE",
                    "SNAPSHOT_FROZEN",
                    kickoff_utc=iso(KICKOFF + timedelta(hours=3)),
                )
            )

    def test_changed_kickoff_with_a_new_source_identity_is_accepted(self) -> None:
        book = ledger()
        book.append(step(1, "PRECOMMITTED", "SNAPSHOT_ELIGIBLE"))
        book.append(
            step(
                2,
                "SNAPSHOT_ELIGIBLE",
                "SNAPSHOT_FROZEN",
                kickoff_utc=iso(KICKOFF + timedelta(hours=3)),
                source_identity="t" * 64,
            )
        )
        self.assertEqual(book.current_state("6607349::national_elo"), "SNAPSHOT_FROZEN")

    def test_post_hoc_candidate_insertion_is_rejected(self) -> None:
        book = ledger()
        with self.assertRaises(StateMachineRejection):
            book.append(
                step(1, "PRECOMMITTED", "SNAPSHOT_ELIGIBLE", candidate_id="tamu_adapter_v1")
            )


class OutcomeAccess(unittest.TestCase):
    def test_outcome_before_the_forecast_freeze_is_rejected(self) -> None:
        book = ledger()
        advance_to_forecast_frozen(book)
        with self.assertRaises(StateMachineRejection):
            book.append(
                step(
                    4,
                    "FORECAST_FROZEN",
                    "AWAITING_OFFICIAL_FINAL",
                    outcome_observed_at_utc=iso(FROZEN_AT - timedelta(hours=2)),
                )
            )

    def test_outcome_before_kickoff_is_rejected(self) -> None:
        book = ledger()
        advance_to_forecast_frozen(book)
        with self.assertRaises(StateMachineRejection):
            book.append(
                step(
                    4,
                    "FORECAST_FROZEN",
                    "AWAITING_OFFICIAL_FINAL",
                    outcome_observed_at_utc=iso(KICKOFF - timedelta(minutes=10)),
                )
            )

    def test_scored_requires_an_official_final(self) -> None:
        book = ledger()
        advance_to_forecast_frozen(book)
        book.append(step(4, "FORECAST_FROZEN", "AWAITING_OFFICIAL_FINAL"))
        with self.assertRaises(StateMachineRejection):
            book.append(step(5, "AWAITING_OFFICIAL_FINAL", "SCORED"))

    def test_scored_is_accepted_with_a_legitimate_final(self) -> None:
        book = ledger()
        advance_to_forecast_frozen(book)
        book.append(step(4, "FORECAST_FROZEN", "AWAITING_OFFICIAL_FINAL"))
        book.append(
            step(
                5,
                "AWAITING_OFFICIAL_FINAL",
                "SCORED",
                outcome_observed_at_utc=iso(FINAL_AT),
            )
        )
        self.assertEqual(book.current_state("6607349::national_elo"), "SCORED")


class LaneInvariants(unittest.TestCase):
    def test_every_row_stays_in_the_shadow_lane(self) -> None:
        book = ledger()
        advance_to_forecast_frozen(book)
        for entry in book.entries:
            self.assertEqual(entry["lane"], "PROSPECTIVE_SHADOW_OBSERVATION_ONLY")
            self.assertEqual(entry["protected_lane"], "RETAIN_PROTECTED_LANE_BLOCKED")
            self.assertFalse(entry["promotion_performed"])
            self.assertFalse(entry["publication_performed"])
            self.assertFalse(entry["availability_inferred"])


class Replay(unittest.TestCase):
    def snapshot(self, state: str = "SNAPSHOT_FROZEN") -> dict:
        return {
            "ncaa_contest_id": "6607349",
            "source_published_game_date": "2026-09-05",
            "forecast_state": state,
            "state_reason": "SNAPSHOT_FROZEN_BEFORE_THE_DECLARED_PREGAME_CUTOFF",
            "kickoff_utc_conservative_lower_bound": iso(KICKOFF),
            "snapshot": {
                "capture_sha256": "c" * 64,
                "capture_retrieved_at_utc": iso(FROZEN_AT),
                "snapshot_frozen_at_utc": iso(FROZEN_AT),
                "snapshot_identity": "p" * 64,
                "outcome_read_before_freeze": False,
            },
        }

    def forecast(self, candidate_id: str, frozen: bool) -> dict:
        return {
            "ncaa_contest_id": "6607349",
            "candidate_id": candidate_id,
            "forecast_state": "FORECAST_FROZEN" if frozen else "MISSING_REQUIRED_FEATURES_ABSTAIN",
            "probability_home_win": 0.8 if frozen else None,
            "created_at_utc": iso(FROZEN_AT),
            "kickoff_utc_conservative_lower_bound": iso(KICKOFF),
            "snapshot_identity": "p" * 64,
            "model_identity": "m" * 64,
            "abstention_reason": None if frozen else "features unavailable",
        }

    def test_replay_reaches_awaiting_official_final_for_frozen_rows(self) -> None:
        book = replay_cohort(
            snapshots=[self.snapshot()],
            forecasts=[
                self.forecast("national_elo", True),
                self.forecast("prior_only", False),
            ],
            frozen_candidate_ids=sorted(FROZEN_CANDIDATES),
            capture_identity="a" * 64,
        )
        counts = book.state_counts()
        self.assertEqual(counts["AWAITING_OFFICIAL_FINAL"], 1)
        self.assertEqual(counts["SNAPSHOT_FROZEN"], 1)
        self.assertEqual(counts["MISSING_REQUIRED_FEATURES_ABSTAIN"], 1)
        self.assertEqual(counts["SCORED"], 0)

    def test_replay_records_a_side_state_without_a_snapshot(self) -> None:
        book = replay_cohort(
            snapshots=[self.snapshot("UNSUPPORTED_ENTITY")],
            forecasts=[],
            frozen_candidate_ids=sorted(FROZEN_CANDIDATES),
            capture_identity="a" * 64,
        )
        self.assertEqual(book.state_counts()["UNSUPPORTED_ENTITY"], 1)


class GapReevaluation(unittest.TestCase):
    GATES = {
        "foundation": {
            "eligibility_census": {"PIT_FEATURE_ELIGIBLE": 0},
            "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
            "authority": {"champion_or_production_promotion": False},
            "scientific_nonclaims": {
                "claims_bas_or_aggie_excess": False,
                "claims_production_champion": False,
            },
        },
        "domain_matrix": {
            "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
            "admission_matrix": [
                {"domain_id": "pregame_availability", "decision": "SOURCE_ABSENT"}
            ],
            "authority": {"champion_or_production_promotion": False},
            "scientific_nonclaims": {"claims_bas_or_aggie_excess": False},
        },
        "forecast": {
            "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
            "contest_state_counts": {"UNSUPPORTED_ENTITY": 17, "SNAPSHOT_FROZEN": 82},
            "forecast_state_counts": {"UNSUPPORTED_ENTITY": 85},
            "frozen_forecast_contest_ids": [str(index) for index in range(82)],
            "authority": {"champion_or_production_promotion": False},
            "scientific_nonclaims": {"claims_bas_or_aggie_excess": False},
        },
        "rehearsal": {
            "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
            "specialization": {
                "specialization_rows_emitted": 0,
                "single_game_lift_claimed": False,
                "comparator_is_mandatory_and_present": True,
            },
            "tamu_feature_availability_matrix": [
                {
                    "domain_id": "tamu_pregame_availability",
                    "availability_class": "UNAVAILABLE_ROUTE_BLOCKED",
                }
            ],
            "authority": {"champion_or_production_promotion": False},
            "scientific_nonclaims": {
                "claims_bas_or_aggie_excess": False,
                "claims_availability_from_participation": False,
            },
        },
    }

    def test_all_declared_gaps_verify_and_stay_open(self) -> None:
        contract = load_contract(REPO_ROOT)
        verdicts = reevaluate_gaps(contract, self.GATES)
        self.assertEqual(len(verdicts), 8)
        self.assertTrue(all(item["state"] == "OPEN" for item in verdicts))
        self.assertTrue(all(item["verification_holds"] for item in verdicts))

    def test_a_gap_cannot_be_closed_by_editing_prose(self) -> None:
        contract = load_contract(REPO_ROOT)
        declaration = dict(contract["gap_reevaluation"][0])
        declaration["state"] = "CLOSED"
        with self.assertRaises(ValueError):
            evaluate_gap(declaration, self.GATES)

    def test_a_promotion_claim_breaks_the_champion_verification(self) -> None:
        contract = load_contract(REPO_ROOT)
        declaration = next(
            item for item in contract["gap_reevaluation"] if item["gap_id"] == "GAP-005"
        )
        gates = {
            name: dict(value) for name, value in self.GATES.items()
        }
        gates["forecast"] = {
            **gates["forecast"],
            "authority": {"champion_or_production_promotion": True},
        }
        with self.assertRaises(ValueError):
            evaluate_gap(declaration, gates)

    def test_a_nonzero_pit_census_breaks_the_gap_002_verification(self) -> None:
        contract = load_contract(REPO_ROOT)
        declaration = next(
            item for item in contract["gap_reevaluation"] if item["gap_id"] == "GAP-002"
        )
        gates = {name: dict(value) for name, value in self.GATES.items()}
        gates["foundation"] = {
            **gates["foundation"],
            "eligibility_census": {"PIT_FEATURE_ELIGIBLE": 12},
        }
        with self.assertRaises(ValueError):
            evaluate_gap(declaration, gates)


if __name__ == "__main__":
    unittest.main()
