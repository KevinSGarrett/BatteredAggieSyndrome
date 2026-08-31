from __future__ import annotations

import json
import unittest
from pathlib import Path

from aggie_analytics.data.week1_2026_spine_semantic_successor import (
    ABSTAIN_MISSING_REQUIRED_FEATURES,
    ABSTAIN_UNSUPPORTED_ENTITY,
    ADMITTED_PROSPECTIVE_PREKICKOFF,
    CANDIDATE_ONLY_NOT_CONSUMED,
    COLD_START_INSUFFICIENT_TEAM_HISTORY,
    CONTRACT_RELATIVE,
    CURRENT_PRIOR_NOT_MATERIALIZED,
    FORECAST_READY,
    GATE_RELATIVE,
    NOT_IN_MODEL_TARGET,
    PARTIAL_MODEL_INPUT,
    PREDECESSOR_COMPOSITE_DOMAIN,
    PRIOR_CLASSIFICATIONS,
    PRIOR_UNRESOLVED_ENTITY,
    QUARANTINED_CONFLICT,
    READINESS_QUARANTINED_CONFLICT,
    RETIRED_PRIOR_CLASSIFICATION,
    SITE_ORIENTATION,
    SOURCE_EVIDENCE_ABSENT,
    SPINE_ROW_UNSUPPORTED_ENTITY,
    STALE_ALLOWED_HISTORY_AVAILABLE,
    SUCCESSOR_DOMAINS,
    TEAM_STRENGTH_PRIOR,
    VENUE_COORDINATES,
    VENUE_IDENTITY,
    WEATHER_VINTAGE,
    SemanticSuccessorViolation,
    build_pair_counts,
    build_successor_cells,
    classify_prior,
    compute_gate_identity,
    count_team_domain_cells,
    enforce_weather_rule,
    load_contract,
    map_partial_model_input,
    resolve_forecast_readiness,
    split_site_and_venue_cells,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def composite_cell(
    *,
    venue_identity: str | None = None,
    venue_identity_state: str = SOURCE_EVIDENCE_ABSENT,
    site_orientation: str = "HOME",
    candidate_only: bool = True,
    team: str = "SRC-002:TEAM:245",
    contest: str = "contest-1",
    orientation: str = "HOME",
) -> dict[str, object]:
    return {
        "domain": PREDECESSOR_COMPOSITE_DOMAIN,
        "admission_disposition": ADMITTED_PROSPECTIVE_PREKICKOFF,
        "canonical_team_id": team,
        "contest_identity": contest,
        "ncaa_contest_id": "6607349",
        "orientation": orientation,
        "row_identity": "row-1",
        "snapshot_issuance_utc": "2026-08-31T11:10:46.119883Z",
        "source_id": "SRC-NCAA-OFFICIAL-STATS",
        "source_team_id": "622204",
        "target_kickoff_bound_utc": "2026-09-05T23:00:00Z",
        "observed_at_utc": "2026-08-31T10:03:55Z",
        "published_at_utc": None,
        "raw_capture_sha256": "a" * 64,
        "source_observation_identity": "a" * 64,
        "conflict_state": "NONE",
        "value": {
            "site_orientation": site_orientation,
            "site_state": "HOME_TEAM_SITE",
            "neutral_site_text": "",
            "venue_identity": venue_identity,
            "venue_identity_state": venue_identity_state,
            "venue_attributes_are_candidate_only": candidate_only,
            "attendance_or_postgame_field_present": False,
        },
    }


def plain_cell(domain: str, disposition: str, **overrides: object) -> dict[str, object]:
    cell = {
        "domain": domain,
        "admission_disposition": disposition,
        "canonical_team_id": "SRC-002:TEAM:245",
        "contest_identity": "contest-1",
        "ncaa_contest_id": "6607349",
        "orientation": "HOME",
        "row_identity": "row-1",
        "snapshot_issuance_utc": "2026-08-31T11:10:46.119883Z",
        "source_id": "SRC-NCAA-OFFICIAL-STATS",
        "source_team_id": "622204",
        "target_kickoff_bound_utc": "2026-09-05T23:00:00Z",
        "conflict_state": "NONE",
        "value": {},
    }
    cell.update(overrides)
    return cell


def spine_row(**overrides: object) -> dict[str, object]:
    row = {
        "contest_identity": "contest-1",
        "ncaa_contest_id": "6607349",
        "canonical_team_id": "SRC-002:TEAM:245",
        "opponent_canonical_team_id": "SRC-002:TEAM:2623",
        "source_team_id": "622204",
        "orientation": "HOME",
        "season": 2026,
        "week_label": "WEEK_1",
        "requested_game_date": "2026-09-05",
        "kickoff_utc_conservative_lower_bound": "2026-09-05T23:00:00Z",
        "kickoff_time_state": "KICKOFF_TIME_PUBLISHED",
        "kickoff_utc_independently_confirmed": False,
        "contest_disposition": "ADMITTED_MODEL_ELIGIBLE",
        "spine_row_state": "SPINE_ROW_ADMITTED",
        "team_identity_state": "EXACT_NORMALIZED_NAME_RESOLVED",
        "subdivision": "FBS",
        "conference_name": "SEC",
        "poll_rank": None,
    }
    row.update(overrides)
    return row


class ContractTest(unittest.TestCase):
    def test_contract_loads_and_forbids_the_retired_composite_requirement(self) -> None:
        contract = load_contract(REPO_ROOT)
        self.assertEqual(len(contract["candidate_feature_requirements"]), 5)
        for requirement in contract["candidate_feature_requirements"]:
            self.assertNotIn(
                PREDECESSOR_COMPOSITE_DOMAIN, requirement["required_domains"]
            )
            self.assertNotIn(VENUE_IDENTITY, requirement["required_domains"])

    def test_contract_rejects_a_partial_input_that_may_forecast(self) -> None:
        contract = json.loads(
            (REPO_ROOT / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig")
        )
        contract["forecast_readiness"]["partial_model_input_may_emit_a_forecast"] = True
        with self.assertRaises(SemanticSuccessorViolation):
            _validate_mutated_contract(contract)

    def test_contract_rejects_reopening_the_protected_lane(self) -> None:
        contract = json.loads(
            (REPO_ROOT / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig")
        )
        contract["protected_lane"] = "OPEN"
        with self.assertRaises(SemanticSuccessorViolation):
            _validate_mutated_contract(contract)

    def test_contract_rejects_a_venue_identity_admitted_from_site_orientation(
        self,
    ) -> None:
        contract = json.loads(
            (REPO_ROOT / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig")
        )
        for item in contract["domain_split"]["successor_domains"]:
            if item["domain"] == VENUE_IDENTITY:
                item["may_be_admitted_from_site_orientation_alone"] = True
        with self.assertRaises(SemanticSuccessorViolation):
            _validate_mutated_contract(contract)


def _validate_mutated_contract(contract: dict[str, object]) -> None:
    """Run the contract gate against an in-memory mutation."""
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "configs").mkdir(parents=True)
        (root / CONTRACT_RELATIVE).write_text(
            json.dumps(contract), encoding="utf-8", newline="\n"
        )
        load_contract(root)


class DomainSplitTest(unittest.TestCase):
    def test_split_emits_three_domains(self) -> None:
        cells = split_site_and_venue_cells(composite_cell())
        self.assertEqual(
            [cell["domain"] for cell in cells],
            [SITE_ORIENTATION, VENUE_IDENTITY, VENUE_COORDINATES],
        )

    def test_site_orientation_is_admitted_without_a_venue_identity(self) -> None:
        site, identity, _ = split_site_and_venue_cells(composite_cell())
        self.assertEqual(site["admission_disposition"], ADMITTED_PROSPECTIVE_PREKICKOFF)
        self.assertEqual(identity["admission_disposition"], SOURCE_EVIDENCE_ABSENT)

    def test_venue_identity_is_never_admitted_from_site_orientation_alone(self) -> None:
        _, identity, _ = split_site_and_venue_cells(
            composite_cell(site_orientation="NEUTRAL")
        )
        self.assertEqual(identity["admission_disposition"], SOURCE_EVIDENCE_ABSENT)
        self.assertFalse(identity["value"]["admitted_from_site_orientation_alone"])

    def test_authoritative_venue_identity_is_admitted(self) -> None:
        _, identity, coordinates = split_site_and_venue_cells(
            composite_cell(
                venue_identity="VENUE:KYLE_FIELD",
                venue_identity_state="AUTHORITATIVE_VENUE_ID",
                candidate_only=False,
            )
        )
        self.assertEqual(
            identity["admission_disposition"], ADMITTED_PROSPECTIVE_PREKICKOFF
        )
        self.assertEqual(
            coordinates["admission_disposition"], ADMITTED_PROSPECTIVE_PREKICKOFF
        )

    def test_coordinates_stay_candidate_only_when_attributes_are_inferred(self) -> None:
        _, _, coordinates = split_site_and_venue_cells(
            composite_cell(
                venue_identity="VENUE:KYLE_FIELD",
                venue_identity_state="AUTHORITATIVE_VENUE_ID",
                candidate_only=True,
            )
        )
        self.assertEqual(
            coordinates["admission_disposition"], CANDIDATE_ONLY_NOT_CONSUMED
        )
        self.assertFalse(coordinates["value"]["admitted_from_inference"])

    def test_the_retired_composite_domain_never_survives(self) -> None:
        cells, _ = build_successor_cells([composite_cell()])
        self.assertNotIn(
            PREDECESSOR_COMPOSITE_DOMAIN, {cell["domain"] for cell in cells}
        )
        self.assertTrue({cell["domain"] for cell in cells} <= set(SUCCESSOR_DOMAINS))

    def test_a_venue_identity_admitted_without_an_id_is_rejected(self) -> None:
        broken = split_site_and_venue_cells(composite_cell())[1]
        broken["admission_disposition"] = ADMITTED_PROSPECTIVE_PREKICKOFF
        with self.assertRaises(SemanticSuccessorViolation):
            build_successor_cells([broken])

    def test_coordinates_admitted_without_venue_identity_are_rejected(self) -> None:
        broken = split_site_and_venue_cells(composite_cell())[2]
        broken["admission_disposition"] = ADMITTED_PROSPECTIVE_PREKICKOFF
        with self.assertRaises(SemanticSuccessorViolation):
            build_successor_cells([broken])

    def test_an_unknown_admission_disposition_is_rejected(self) -> None:
        broken = split_site_and_venue_cells(composite_cell())[0]
        broken["admission_disposition"] = "SOMETHING_INVENTED"
        with self.assertRaises(SemanticSuccessorViolation):
            build_successor_cells([broken])


class WeatherRuleTest(unittest.TestCase):
    def test_weather_is_demoted_without_authoritative_coordinates(self) -> None:
        index = {
            ("contest-1", "SRC-002:TEAM:245"): {
                WEATHER_VINTAGE: plain_cell(
                    WEATHER_VINTAGE, ADMITTED_PROSPECTIVE_PREKICKOFF
                ),
                VENUE_COORDINATES: plain_cell(
                    VENUE_COORDINATES, CANDIDATE_ONLY_NOT_CONSUMED
                ),
            }
        }
        self.assertEqual(len(enforce_weather_rule(index)), 1)

    def test_weather_survives_with_authoritative_coordinates(self) -> None:
        index = {
            ("contest-1", "SRC-002:TEAM:245"): {
                WEATHER_VINTAGE: plain_cell(
                    WEATHER_VINTAGE, ADMITTED_PROSPECTIVE_PREKICKOFF
                ),
                VENUE_COORDINATES: plain_cell(
                    VENUE_COORDINATES, ADMITTED_PROSPECTIVE_PREKICKOFF
                ),
            }
        }
        self.assertEqual(enforce_weather_rule(index), [])

    def test_weather_is_demoted_when_no_coordinate_cell_exists(self) -> None:
        index = {
            ("contest-1", "SRC-002:TEAM:245"): {
                WEATHER_VINTAGE: plain_cell(
                    WEATHER_VINTAGE, ADMITTED_PROSPECTIVE_PREKICKOFF
                )
            }
        }
        self.assertEqual(len(enforce_weather_rule(index)), 1)


class PriorSemanticsTest(unittest.TestCase):
    history = {
        "SRC-002:TEAM:245": {
            "allowed_history_row_count": 700,
            "latest_allowed_season": 2023,
        },
        "SRC-002:TEAM:999": {
            "allowed_history_row_count": 5,
            "latest_allowed_season": 2019,
        },
    }

    def test_allowed_history_is_stale_not_unknowable(self) -> None:
        state = classify_prior(
            spine_row=spine_row(),
            prior_cell=plain_cell(TEAM_STRENGTH_PRIOR, SOURCE_EVIDENCE_ABSENT),
            history=self.history,
            minimum_games=20,
        )
        self.assertEqual(state["classification"], STALE_ALLOWED_HISTORY_AVAILABLE)
        self.assertTrue(state["stale_history_available"])
        self.assertFalse(state["current_frozen_prior_materialized"])
        self.assertFalse(state["retired_classification_asserted"])

    def test_the_retired_classification_is_never_emitted(self) -> None:
        for team in ("SRC-002:TEAM:245", "SRC-002:TEAM:999", "SRC-002:TEAM:404"):
            state = classify_prior(
                spine_row=spine_row(canonical_team_id=team),
                prior_cell=plain_cell(TEAM_STRENGTH_PRIOR, SOURCE_EVIDENCE_ABSENT),
                history=self.history,
                minimum_games=20,
            )
            self.assertIn(state["classification"], PRIOR_CLASSIFICATIONS)
            self.assertNotEqual(state["classification"], RETIRED_PRIOR_CLASSIFICATION)

    def test_thin_history_is_a_cold_start(self) -> None:
        state = classify_prior(
            spine_row=spine_row(canonical_team_id="SRC-002:TEAM:999"),
            prior_cell=plain_cell(TEAM_STRENGTH_PRIOR, SOURCE_EVIDENCE_ABSENT),
            history=self.history,
            minimum_games=20,
        )
        self.assertEqual(state["classification"], COLD_START_INSUFFICIENT_TEAM_HISTORY)

    def test_absent_history_is_an_unmaterialized_current_prior(self) -> None:
        state = classify_prior(
            spine_row=spine_row(canonical_team_id="SRC-002:TEAM:404"),
            prior_cell=plain_cell(TEAM_STRENGTH_PRIOR, SOURCE_EVIDENCE_ABSENT),
            history=self.history,
            minimum_games=20,
        )
        self.assertEqual(state["classification"], CURRENT_PRIOR_NOT_MATERIALIZED)

    def test_an_unresolved_row_is_classified_by_its_own_identity(self) -> None:
        state = classify_prior(
            spine_row=spine_row(
                canonical_team_id=None, team_identity_state="UNRESOLVED_SOURCE_ENTITY"
            ),
            prior_cell=None,
            history=self.history,
            minimum_games=20,
        )
        self.assertEqual(state["classification"], PRIOR_UNRESOLVED_ENTITY)

    def test_a_resolved_row_in_an_unsupported_contest_keeps_its_knowable_history(
        self,
    ) -> None:
        state = classify_prior(
            spine_row=spine_row(spine_row_state=SPINE_ROW_UNSUPPORTED_ENTITY),
            prior_cell=plain_cell(TEAM_STRENGTH_PRIOR, SOURCE_EVIDENCE_ABSENT),
            history=self.history,
            minimum_games=20,
        )
        self.assertEqual(state["classification"], STALE_ALLOWED_HISTORY_AVAILABLE)
        self.assertTrue(state["contest_blocked_by_an_unresolved_participant"])

    def test_a_quarantined_prior_is_not_reported_as_stale(self) -> None:
        state = classify_prior(
            spine_row=spine_row(),
            prior_cell=plain_cell(TEAM_STRENGTH_PRIOR, QUARANTINED_CONFLICT),
            history=self.history,
            minimum_games=20,
        )
        self.assertEqual(state["classification"], "CURRENT_PRIOR_QUARANTINED")
        self.assertFalse(state["stale_history_available"])


class ForecastReadinessTest(unittest.TestCase):
    def test_partial_model_input_maps_to_a_missing_feature_abstention(self) -> None:
        self.assertEqual(
            map_partial_model_input(PARTIAL_MODEL_INPUT),
            ABSTAIN_MISSING_REQUIRED_FEATURES,
        )

    def test_ready_maps_to_forecast_ready(self) -> None:
        self.assertEqual(
            map_partial_model_input("READY_FOR_PREDECLARED_MODEL_INPUT"), FORECAST_READY
        )

    def test_an_unmappable_state_is_refused(self) -> None:
        with self.assertRaises(SemanticSuccessorViolation):
            map_partial_model_input("SOMETHING_ELSE")

    def test_a_missing_required_domain_abstains(self) -> None:
        outcome = resolve_forecast_readiness(
            requirement={
                "candidate_id": "prior_only",
                "required_domains": [TEAM_STRENGTH_PRIOR, SITE_ORIENTATION],
                "optional_domains": [],
            },
            contest_cells=[
                plain_cell(SITE_ORIENTATION, ADMITTED_PROSPECTIVE_PREKICKOFF),
                plain_cell(TEAM_STRENGTH_PRIOR, SOURCE_EVIDENCE_ABSENT),
            ],
            contest_rows=[spine_row()],
            ranking_surface_complete=True,
        )
        self.assertEqual(
            outcome["forecast_readiness_state"], ABSTAIN_MISSING_REQUIRED_FEATURES
        )
        self.assertEqual(outcome["missing_required_domains"], [TEAM_STRENGTH_PRIOR])
        self.assertFalse(outcome["forecast_emitted_by_this_gate"])

    def test_full_coverage_is_forecast_ready(self) -> None:
        outcome = resolve_forecast_readiness(
            requirement={
                "candidate_id": "prior_only",
                "required_domains": [TEAM_STRENGTH_PRIOR, SITE_ORIENTATION],
                "optional_domains": [],
            },
            contest_cells=[
                plain_cell(SITE_ORIENTATION, ADMITTED_PROSPECTIVE_PREKICKOFF),
                plain_cell(TEAM_STRENGTH_PRIOR, ADMITTED_PROSPECTIVE_PREKICKOFF),
            ],
            contest_rows=[spine_row()],
            ranking_surface_complete=True,
        )
        self.assertEqual(outcome["forecast_readiness_state"], FORECAST_READY)

    def test_an_unresolved_participant_abstains_on_identity(self) -> None:
        outcome = resolve_forecast_readiness(
            requirement={
                "candidate_id": "national_base_rate",
                "required_domains": [],
                "optional_domains": [],
            },
            contest_cells=[],
            contest_rows=[spine_row(spine_row_state=SPINE_ROW_UNSUPPORTED_ENTITY)],
            ranking_surface_complete=True,
        )
        self.assertEqual(
            outcome["forecast_readiness_state"], ABSTAIN_UNSUPPORTED_ENTITY
        )

    def test_a_conflict_quarantines_before_coverage_is_considered(self) -> None:
        outcome = resolve_forecast_readiness(
            requirement={
                "candidate_id": "national_base_rate",
                "required_domains": [],
                "optional_domains": [],
            },
            contest_cells=[plain_cell(TEAM_STRENGTH_PRIOR, QUARANTINED_CONFLICT)],
            contest_rows=[spine_row()],
            ranking_surface_complete=True,
        )
        self.assertEqual(
            outcome["forecast_readiness_state"], READINESS_QUARANTINED_CONFLICT
        )

    def test_an_incomplete_ranking_surface_blocks_a_ranking_dependent_candidate(
        self,
    ) -> None:
        outcome = resolve_forecast_readiness(
            requirement={
                "candidate_id": "national_logistic_l2",
                "required_domains": [SITE_ORIENTATION],
                "optional_domains": [],
                "requires_complete_ranking_semantics": True,
            },
            contest_cells=[
                plain_cell(SITE_ORIENTATION, ADMITTED_PROSPECTIVE_PREKICKOFF)
            ],
            contest_rows=[spine_row()],
            ranking_surface_complete=False,
        )
        self.assertEqual(
            outcome["forecast_readiness_state"], ABSTAIN_MISSING_REQUIRED_FEATURES
        )
        self.assertIn(
            "RANKING_SURFACE_IS_INCOMPLETE_FOR_A_RANKING_DEPENDENT_CANDIDATE",
            outcome["abstention_reasons"],
        )

    def test_a_non_target_contest_is_out_of_scope(self) -> None:
        outcome = resolve_forecast_readiness(
            requirement={
                "candidate_id": "national_base_rate",
                "required_domains": [],
                "optional_domains": [],
            },
            contest_cells=[],
            contest_rows=[spine_row(contest_disposition="UNSUPPORTED_ENTITY")],
            ranking_surface_complete=True,
        )
        self.assertEqual(outcome["forecast_readiness_state"], NOT_IN_MODEL_TARGET)


class CountSemanticsTest(unittest.TestCase):
    def test_pair_counts_separate_cells_from_distinct_domains(self) -> None:
        cells: list[dict[str, object]] = []
        for orientation, team in (
            ("HOME", "SRC-002:TEAM:245"),
            ("AWAY", "SRC-002:TEAM:2623"),
        ):
            for domain in ("CONFERENCE_AND_SUBDIVISION", SITE_ORIENTATION):
                cells.append(
                    plain_cell(
                        domain,
                        ADMITTED_PROSPECTIVE_PREKICKOFF,
                        orientation=orientation,
                        canonical_team_id=team,
                    )
                )
        pairs = build_pair_counts(
            successor_cells=cells,
            spine_rows=[spine_row(), spine_row(orientation="AWAY")],
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["admitted_team_domain_cell_count"], 4)
        self.assertEqual(pairs[0]["distinct_admitted_domain_count"], 2)
        self.assertEqual(
            pairs[0]["admitted_domain_count_by_orientation"], {"AWAY": 2, "HOME": 2}
        )
        self.assertNotIn("admitted_domain_count", pairs[0])

    def test_team_domain_cell_counts_are_named_unambiguously(self) -> None:
        counts = count_team_domain_cells(
            [
                plain_cell(SITE_ORIENTATION, ADMITTED_PROSPECTIVE_PREKICKOFF),
                plain_cell(VENUE_COORDINATES, CANDIDATE_ONLY_NOT_CONSUMED),
                plain_cell(TEAM_STRENGTH_PRIOR, SOURCE_EVIDENCE_ABSENT),
            ]
        )
        self.assertEqual(counts["admitted_team_domain_cell_count"], 1)
        self.assertEqual(counts["candidate_only_team_domain_cell_count"], 1)
        self.assertEqual(counts["missing_team_domain_cell_count"], 1)


class CommittedGateTest(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("the successor gate has not been materialized in this tree")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))

    def test_gate_identity_is_self_consistent(self) -> None:
        self.assertEqual(compute_gate_identity(self.gate), self.gate["gate_identity"])

    def test_gate_keeps_the_protected_lane_blocked_and_the_checkpoints_open(
        self,
    ) -> None:
        self.assertEqual(self.gate["protected_lane"], "RETAIN_PROTECTED_LANE_BLOCKED")
        self.assertEqual(self.gate["checkpoints"]["t_minus_24h_state"], "OPEN")
        self.assertEqual(self.gate["checkpoints"]["t_minus_90m_state"], "OPEN")

    def test_gate_emits_no_forecast_and_no_tamu_adjustment(self) -> None:
        self.assertFalse(self.gate["summary"]["forecast_emitted"])
        self.assertFalse(self.gate["tamu_policy"]["tamu_specific_adjustment_applied"])
        self.assertFalse(self.gate["tamu_policy"]["custom_correction_applied"])

    def test_gate_does_not_rewrite_its_predecessors(self) -> None:
        self.assertFalse(
            self.gate["bound_predecessors"]["predecessor_artifacts_rewritten_in_place"]
        )

    def test_no_venue_identity_is_admitted_without_evidence(self) -> None:
        counts = self.gate["summary"]["domain_admission_counts"][VENUE_IDENTITY]
        self.assertEqual(counts[ADMITTED_PROSPECTIVE_PREKICKOFF], 0)

    def test_site_orientation_is_admitted_for_every_oriented_row(self) -> None:
        counts = self.gate["summary"]["domain_admission_counts"][SITE_ORIENTATION]
        self.assertEqual(
            counts[ADMITTED_PROSPECTIVE_PREKICKOFF], self.gate["summary"]["row_count"]
        )

    def test_no_candidate_remains_in_the_nonterminal_partial_state(self) -> None:
        for states in self.gate["summary"]["forecast_readiness_counts"].values():
            self.assertNotIn(PARTIAL_MODEL_INPUT, states)

    def test_the_focus_contest_count_ambiguity_is_resolved(self) -> None:
        report = self.gate["focus_contest_report"]
        self.assertEqual(
            report["reported_four_means"],
            "FOUR_ADMITTED_TEAM_DOMAIN_CELLS_ACROSS_TWO_ORIENTED_ROWS",
        )
        self.assertEqual(report["admitted_team_domain_cell_count"], 4)
        self.assertEqual(report["distinct_admitted_domain_count"], 2)

    def test_the_prior_correction_records_a_knowable_but_stale_history(self) -> None:
        counts = self.gate["summary"]["prior_classification_counts"]
        self.assertGreater(counts[STALE_ALLOWED_HISTORY_AVAILABLE], 0)
        self.assertEqual(counts["CURRENT_PRIOR_ADMITTED"], 0)

    def test_every_correction_record_preserves_its_predecessor(self) -> None:
        self.assertEqual(len(self.gate["corrections"]), 7)
        for record in self.gate["corrections"]:
            self.assertFalse(record["predecessor_rewritten_in_place"])


if __name__ == "__main__":
    unittest.main()
