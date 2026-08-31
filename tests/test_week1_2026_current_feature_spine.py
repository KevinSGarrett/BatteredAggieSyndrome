"""Fail-closed tests for the Week 1 2026 current-feature spine."""

from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.data.week1_2026_current_feature_spine import (
    ADMITTED_PROSPECTIVE_PREKICKOFF,
    CANDIDATE_ONLY_NOT_CONSUMED,
    CONTRACT_RELATIVE,
    FEATURE_DOMAINS,
    SOURCE_EVIDENCE_ABSENT,
    TEMPORALLY_INELIGIBLE,
    Week1FeatureSpineViolation,
    assert_future_append_invariance,
    build_spine_rows,
    index_rankings,
    index_weather_vintages,
    index_week_zero_finals,
    parse_ranking_document,
    select_forecast_period,
    summarize,
    validate_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SNAPSHOT = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)
KICKOFF = "2026-09-05T23:00:00Z"

POLL_DOCUMENT = """
<figure class="rankings-last-updated">
    Through Games AUG. 17, 2026
</figure>
<table><tbody>
<tr><td>1</td><td>Ohio State (40)</td><td>1672</td></tr>
<tr><td>T2</td><td>Texas A&amp;M</td><td>1500</td></tr>
<tr><td>T2</td><td>Missouri St.</td><td>1500</td></tr>
</tbody></table>
"""


def participant(
    *,
    source_team_id: str,
    display_name: str,
    canonical: str | None,
    orientation: str,
) -> dict:
    return {
        "orientation": orientation,
        "source_team_id": source_team_id,
        "source_display_name": display_name,
        "source_label_carried_prior_record": False,
        "canonical_team_id": canonical,
        "official_organization_id": "1234",
        "normalized_name_key": display_name.lower(),
        "resolution_state": "EXACT_NORMALIZED_NAME_RESOLVED" if canonical else "UNRESOLVED_SOURCE_ENTITY",
        "resolution_evidence": "OFFICIAL_NCAA_ORGANIZATION_RECORD_TUPLE" if canonical else None,
        "source_display_name_alias_observed": False,
        "subdivision": "FBS",
        "division_code": "11",
        "conference_id": "911",
        "conference_name": "SEC",
        "season_authority_state": "OFFICIAL_2026_SEASON_AUTHORITY_BOUND",
        "season_authority_capture_sha256": "a" * 64,
        "season_authority_retrieved_at_utc": "2026-08-31T02:00:00Z",
    }


def contest(
    *,
    contest_id: str = "700001",
    kickoff: str | None = KICKOFF,
    site_state: str = "HOME_TEAM_SITE",
    disposition: str = "ADMITTED_MODEL_ELIGIBLE",
    away: dict | None = None,
    home: dict | None = None,
) -> dict:
    away = away or participant(
        source_team_id="600001",
        display_name="Missouri St.",
        canonical="SRC-002:TEAM:2623",
        orientation="AWAY",
    )
    home = home or participant(
        source_team_id="600002",
        display_name="Texas A&M",
        canonical="SRC-002:TEAM:245",
        orientation="HOME",
    )
    return {
        "ncaa_contest_id": contest_id,
        "contest_identity": f"identity-{contest_id}",
        "season": 2026,
        "week_label": "WEEK_1",
        "requested_game_date": "2026-09-05",
        "source_published_game_date": "2026-09-05",
        "kickoff_utc_conservative_lower_bound": kickoff,
        "kickoff_time_state": "KICKOFF_TIME_PUBLISHED",
        "kickoff_utc_independently_confirmed": False,
        "neutral_site_text": "" if site_state != "NEUTRAL" else "Neutral Site",
        "site_state": site_state,
        "venue_identity": None,
        "venue_identity_state": "SOURCE_EVIDENCE_ABSENT",
        "away_team": away,
        "home_team": home,
        "participants": [away, home],
        "disposition": disposition,
        "source_capture_sha256": "b" * 64,
        "retrieved_at_utc": "2026-08-31T03:00:00Z",
    }


RANKING_CAPTURE = {
    "poll_id": "ASSOCIATED_PRESS_FBS_TOP_25",
    "capture_identity": "c" * 64,
    "raw_sha256": "d" * 64,
    "retrieved_at_utc": "2026-08-31T04:00:00Z",
    "source_uri": "https://www.ncaa.com/rankings/football/fbs/associated-press",
    "manifest_relative_path": "manifests/shadow/example/manifest.json",
}

PRIOR_EVIDENCE = {
    "candidate_gate_identity": "e" * 64,
    "absence_reason": "THE_PRIOR_OUTCOME_DOMAIN_IS_NOT_MATERIALIZED_FOR_THE_2026_POPULATION",
}


def build(
    *,
    contests=None,
    week_zero=None,
    weather=None,
    forecast_periods=None,
    rankings=None,
    snapshot=SNAPSHOT,
):
    contract = validate_contract(
        json.loads((REPO_ROOT / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig"))
    )
    contests = contests if contests is not None else [contest()]
    participants = [
        {
            "source_team_id": item["source_team_id"],
            "source_display_names": [item["source_display_name"]],
        }
        for row in contests
        for item in row["participants"]
    ]
    poll = parse_ranking_document(POLL_DOCUMENT)
    resolved_rankings = (
        rankings if rankings is not None else index_rankings(poll["entries"], participants)
    )
    return build_spine_rows(
        contract=contract,
        contests=contests,
        participants=participants,
        rankings=resolved_rankings,
        ranking_capture=RANKING_CAPTURE,
        publication_authority_text=poll["publication_authority_text"],
        week_zero=week_zero or {},
        weather=weather or {},
        forecast_periods=forecast_periods or {},
        prior_evidence=PRIOR_EVIDENCE,
        snapshot_issuance=snapshot,
    )


class ContractProtectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (REPO_ROOT / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig")
        )

    def test_published_contract_is_accepted(self) -> None:
        self.assertEqual(validate_contract(self.contract)["contract_id"], self.contract["contract_id"])

    def test_fabricated_default_cannot_be_permitted(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["missingness"]["fabricated_default_permitted"] = True
        with self.assertRaises(Week1FeatureSpineViolation):
            validate_contract(contract)

    def test_unranked_numeric_sentinel_cannot_be_permitted(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["sources"]["current_rankings"]["unranked_sentinel_forbidden"] = 99
        with self.assertRaises(Week1FeatureSpineViolation):
            validate_contract(contract)

    def test_membership_cannot_become_availability(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["sources"]["pregame_availability"]["membership_as_availability"] = True
        with self.assertRaises(Week1FeatureSpineViolation):
            validate_contract(contract)

    def test_participation_cannot_become_availability(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["sources"]["pregame_availability"]["participation_as_availability"] = True
        with self.assertRaises(Week1FeatureSpineViolation):
            validate_contract(contract)

    def test_observed_postgame_weather_cannot_be_permitted(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["sources"]["weather_vintage"]["observed_postgame_weather_permitted"] = True
        with self.assertRaises(Week1FeatureSpineViolation):
            validate_contract(contract)

    def test_prior_retraining_cannot_be_permitted(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["sources"]["frozen_prior_domain"]["retraining_permitted"] = True
        with self.assertRaises(Week1FeatureSpineViolation):
            validate_contract(contract)

    def test_same_game_target_exclusion_cannot_be_disabled(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["temporal_rules"]["same_game_target_exclusion"] = False
        with self.assertRaises(Week1FeatureSpineViolation):
            validate_contract(contract)

    def test_tamu_specific_adjustment_cannot_be_permitted(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["tamu_policy"]["tamu_specific_adjustment_applied"] = True
        with self.assertRaises(Week1FeatureSpineViolation):
            validate_contract(contract)

    def test_protected_evaluation_cannot_be_opened(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["authority"]["protected_evaluation_admission"] = True
        with self.assertRaises(Week1FeatureSpineViolation):
            validate_contract(contract)


class RankingTests(unittest.TestCase):
    def test_tied_ranks_are_preserved(self) -> None:
        poll = parse_ranking_document(POLL_DOCUMENT)
        self.assertEqual([entry["rank"] for entry in poll["entries"]], [1, 2, 2])
        self.assertEqual(
            [entry["rank_is_tied"] for entry in poll["entries"]], [False, True, True]
        )
        self.assertEqual(poll["publication_authority_text"], "Through Games AUG. 17, 2026")

    def test_repeated_rank_without_a_tie_marker_is_refused(self) -> None:
        document = POLL_DOCUMENT.replace("<td>T2</td><td>Missouri St.</td>", "<td>2</td><td>Missouri St.</td>")
        with self.assertRaises(Week1FeatureSpineViolation):
            parse_ranking_document(document)

    def test_non_monotone_rank_sequence_is_refused(self) -> None:
        document = POLL_DOCUMENT.replace("<tr><td>1</td><td>Ohio State (40)</td>", "<tr><td>9</td><td>Ohio State (40)</td>")
        with self.assertRaises(Week1FeatureSpineViolation):
            parse_ranking_document(document)

    def test_unranked_is_null_with_an_indicator_when_the_poll_is_fully_bound(self) -> None:
        poll = parse_ranking_document(POLL_DOCUMENT.replace("<tr><td>1</td><td>Ohio State (40)</td><td>1672</td></tr>", ""))
        participants = [
            {"source_team_id": "600001", "source_display_names": ["Missouri St."]},
            {"source_team_id": "600002", "source_display_names": ["Texas A&M"]},
            {"source_team_id": "600003", "source_display_names": ["Rice"]},
        ]
        rankings = index_rankings(poll["entries"], participants)
        self.assertTrue(rankings["poll_coverage_complete"])
        third = contest(
            contest_id="700002",
            away=participant(
                source_team_id="600003",
                display_name="Rice",
                canonical="SRC-002:TEAM:900",
                orientation="AWAY",
            ),
            home=participant(
                source_team_id="600004",
                display_name="Tulane",
                canonical="SRC-002:TEAM:901",
                orientation="HOME",
            ),
        )
        rows, cells = build(contests=[contest(), third], rankings=rankings)
        rice = next(row for row in rows if row["source_team_id"] == "600003")
        self.assertEqual(rice["ranked_state"], "UNRANKED")
        self.assertIsNone(rice["poll_rank"])
        cell = next(
            cell
            for cell in cells
            if cell["source_team_id"] == "600003" and cell["domain"] == "CURRENT_RANKING"
        )
        self.assertTrue(cell["value"]["unranked_indicator"])
        self.assertFalse(cell["value"]["unranked_numeric_sentinel_used"])
        self.assertNotEqual(cell["value"]["poll_rank"], 26)

    def test_unranked_is_not_asserted_while_a_poll_entry_is_unbound(self) -> None:
        poll = parse_ranking_document(POLL_DOCUMENT)
        participants = [{"source_team_id": "600002", "source_display_names": ["Texas A&M"]}]
        rankings = index_rankings(poll["entries"], participants)
        self.assertFalse(rankings["poll_coverage_complete"])
        rows, _ = build(rankings=rankings)
        away = next(row for row in rows if row["source_team_id"] == "600001")
        self.assertEqual(away["ranked_state"], "NOT_ESTABLISHED")
        self.assertEqual(away["current_ranking_state"], SOURCE_EVIDENCE_ABSENT)

    def test_an_ambiguous_poll_label_is_quarantined(self) -> None:
        poll = parse_ranking_document(POLL_DOCUMENT)
        participants = [
            {"source_team_id": "600001", "source_display_names": ["Texas A&M"]},
            {"source_team_id": "600002", "source_display_names": ["Texas A&M"]},
        ]
        rankings = index_rankings(poll["entries"], participants)
        self.assertEqual(len(rankings["conflicting_poll_entries"]), 1)


class TemporalAdmissionTests(unittest.TestCase):
    def test_snapshot_after_kickoff_is_refused(self) -> None:
        with self.assertRaises(Week1FeatureSpineViolation):
            build(snapshot=datetime(2026, 9, 6, 0, 0, 0, tzinfo=timezone.utc))

    def test_week_zero_result_is_admitted_only_after_its_official_final_capture(self) -> None:
        proof = {
            "proof_state": "ORIENTATION_PROVEN",
            "ncaa_contest_id": "650001",
            "away_canonical_team_id": "SRC-002:TEAM:245",
            "home_canonical_team_id": "SRC-002:TEAM:999",
            "away_points": 30,
            "home_points": 10,
            "kickoff_bound_utc": "2026-08-30T02:00:00Z",
            "final_capture_retrieved_at_utc": "2026-08-31T01:20:00Z",
            "official_capture_identity": "f" * 64,
            "official_raw_response_sha256": "0" * 64,
            "contest_orientation_identity": "1" * 64,
        }
        week_zero = index_week_zero_finals([proof])
        rows, cells = build(week_zero=week_zero)
        home = next(row for row in rows if row["source_team_id"] == "600002")
        self.assertEqual(home["week_zero_result_state"], ADMITTED_PROSPECTIVE_PREKICKOFF)
        cell = next(
            cell
            for cell in cells
            if cell["source_team_id"] == "600002" and cell["domain"] == "WEEK_ZERO_CURRENT_RESULT"
        )
        self.assertEqual(cell["observed_at_utc"], "2026-08-31T01:20:00Z")
        self.assertEqual(cell["value"]["wins"], 1)

    def test_week_zero_result_captured_after_the_snapshot_is_temporally_ineligible(self) -> None:
        proof = {
            "proof_state": "ORIENTATION_PROVEN",
            "ncaa_contest_id": "650001",
            "away_canonical_team_id": "SRC-002:TEAM:245",
            "home_canonical_team_id": "SRC-002:TEAM:999",
            "away_points": 30,
            "home_points": 10,
            "kickoff_bound_utc": "2026-08-30T02:00:00Z",
            "final_capture_retrieved_at_utc": "2026-09-01T01:20:00Z",
            "official_capture_identity": "f" * 64,
            "official_raw_response_sha256": "0" * 64,
            "contest_orientation_identity": "1" * 64,
        }
        rows, _ = build(week_zero=index_week_zero_finals([proof]))
        home = next(row for row in rows if row["source_team_id"] == "600002")
        self.assertEqual(home["week_zero_result_state"], TEMPORALLY_INELIGIBLE)

    def test_a_target_contest_cannot_supply_its_own_result(self) -> None:
        proof = {
            "proof_state": "ORIENTATION_PROVEN",
            "ncaa_contest_id": "700001",
            "away_canonical_team_id": "SRC-002:TEAM:245",
            "home_canonical_team_id": "SRC-002:TEAM:999",
            "away_points": 30,
            "home_points": 10,
            "kickoff_bound_utc": "2026-09-05T23:00:00Z",
            "final_capture_retrieved_at_utc": "2026-08-31T01:20:00Z",
            "official_capture_identity": "f" * 64,
            "official_raw_response_sha256": "0" * 64,
            "contest_orientation_identity": "1" * 64,
        }
        with self.assertRaises(Week1FeatureSpineViolation):
            build(week_zero=index_week_zero_finals([proof]))

    def test_future_append_invariance_refuses_evidence_from_after_the_target(self) -> None:
        rows, cells = build()
        tampered = copy.deepcopy(cells)
        for cell in tampered:
            if cell["domain"] == "CONFERENCE_AND_SUBDIVISION":
                cell["observed_at_utc"] = "2026-09-06T00:00:00Z"
        with self.assertRaises(Week1FeatureSpineViolation):
            assert_future_append_invariance(rows, tampered)

    def test_every_cell_carries_a_source_and_a_disposition(self) -> None:
        _, cells = build()
        for cell in cells:
            self.assertIn("admission_disposition", cell)
            self.assertIn("snapshot_issuance_utc", cell)
            self.assertIn("target_kickoff_bound_utc", cell)
            if cell["value"] is None:
                self.assertIsNotNone(cell["missingness_reason"])


class WeatherTests(unittest.TestCase):
    def test_only_the_period_containing_the_kickoff_bound_is_selected(self) -> None:
        periods = [
            {"startTime": "2026-09-05T21:00:00+00:00", "endTime": "2026-09-05T22:00:00+00:00"},
            {"startTime": "2026-09-05T22:00:00+00:00", "endTime": "2026-09-05T23:00:00+00:00"},
            {"startTime": "2026-09-05T23:00:00+00:00", "endTime": "2026-09-06T00:00:00+00:00"},
        ]
        chosen = select_forecast_period(periods, KICKOFF)
        self.assertEqual(chosen["startTime"], "2026-09-05T23:00:00+00:00")
        self.assertIsNone(select_forecast_period(periods[:1], KICKOFF))

    def test_a_forecast_vintage_is_candidate_only_and_never_observed_weather(self) -> None:
        vintage = {
            "canonical_team_id": "SRC-002:TEAM:245",
            "state": "CAPTURED",
            "grid_office": "HGX",
            "grid_x": 10,
            "grid_y": 20,
            "forecast_valid_interval": "2026-08-31T00:00:00+00:00/P8DT1H",
            "forecast_raw_sha256": "2" * 64,
            "forecast_raw_relative_path": "raw/example.json",
            "forecast_update_time_utc": "2026-08-31T06:00:00+00:00",
            "retrieved_at_utc": "2026-08-31T06:30:00Z",
        }
        periods = [
            {
                "startTime": "2026-09-05T23:00:00+00:00",
                "endTime": "2026-09-06T00:00:00+00:00",
                "temperature": 88,
                "temperatureUnit": "F",
                "shortForecast": "Partly Cloudy",
            }
        ]
        rows, cells = build(
            weather=index_weather_vintages([vintage]),
            forecast_periods={"SRC-002:TEAM:245": periods},
        )
        cell = next(
            cell
            for cell in cells
            if cell["domain"] == "WEATHER_VINTAGE" and cell["source_team_id"] == "600002"
        )
        self.assertEqual(cell["admission_disposition"], CANDIDATE_ONLY_NOT_CONSUMED)
        self.assertFalse(cell["value"]["observed_postgame_weather_used"])
        self.assertEqual(cell["value"]["temperature"], 88)
        for row in rows:
            self.assertEqual(row["weather_vintage_state"], CANDIDATE_ONLY_NOT_CONSUMED)

    def test_a_site_without_a_forecast_grid_is_missing_not_defaulted(self) -> None:
        _, cells = build()
        cell = next(cell for cell in cells if cell["domain"] == "WEATHER_VINTAGE")
        self.assertEqual(cell["admission_disposition"], SOURCE_EVIDENCE_ABSENT)
        self.assertIsNone(cell["value"])
        self.assertIsNotNone(cell["missingness_reason"])


class SpineStructureTests(unittest.TestCase):
    def test_exactly_two_oriented_rows_per_contest(self) -> None:
        rows, cells = build()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["orientation"] for row in rows}, {"AWAY", "HOME"})
        self.assertEqual(len(cells), 2 * len(FEATURE_DOMAINS))
        self.assertEqual(len({row["row_identity"] for row in rows}), 2)

    def test_pair_coherence_refuses_a_home_away_swap(self) -> None:
        swapped = contest()
        swapped["participants"] = [swapped["home_team"], swapped["away_team"]]
        with self.assertRaises(Week1FeatureSpineViolation):
            build(contests=[swapped])

    def test_a_contest_without_two_participants_is_refused(self) -> None:
        broken = contest()
        broken["participants"] = broken["participants"][:1]
        with self.assertRaises(Week1FeatureSpineViolation):
            build(contests=[broken])

    def test_unsupported_entity_contests_are_retained_not_dropped(self) -> None:
        unsupported = contest(
            contest_id="700003",
            disposition="UNSUPPORTED_ENTITY",
            away=participant(
                source_team_id="600009",
                display_name="Unknown Program",
                canonical=None,
                orientation="AWAY",
            ),
        )
        rows, _ = build(contests=[unsupported])
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            {row["spine_row_state"] for row in rows}, {"SPINE_ROW_UNSUPPORTED_ENTITY"}
        )
        self.assertIsNone(
            next(row for row in rows if row["source_team_id"] == "600009")["canonical_team_id"]
        )

    def test_a_later_snapshot_produces_a_new_row_identity(self) -> None:
        first, _ = build()
        second, _ = build(snapshot=datetime(2026, 8, 31, 18, 0, 0, tzinfo=timezone.utc))
        self.assertNotEqual(first[0]["row_identity"], second[0]["row_identity"])

    def test_availability_and_membership_stay_unestablished(self) -> None:
        rows, cells = build()
        for row in rows:
            self.assertEqual(row["availability_state"], "NOT_ESTABLISHED")
            self.assertEqual(row["availability_feature_count"], 0)
            self.assertFalse(row["membership_as_availability"])
            self.assertFalse(row["participation_as_availability"])
        for cell in cells:
            if cell["domain"] in ("ROSTER_MEMBERSHIP", "PREGAME_AVAILABILITY"):
                self.assertIsNone(cell["value"])
                self.assertEqual(cell["admission_disposition"], SOURCE_EVIDENCE_ABSENT)

    def test_texas_am_travels_the_same_national_path(self) -> None:
        rows, cells = build()
        tamu = next(row for row in rows if row["source_display_name"] == "Texas A&M")
        other = next(row for row in rows if row["source_display_name"] != "Texas A&M")
        self.assertFalse(tamu["tamu_specific_adjustment_applied"])
        self.assertEqual(sorted(tamu), sorted(other))
        tamu_domains = sorted(
            cell["domain"] for cell in cells if cell["source_team_id"] == tamu["source_team_id"]
        )
        other_domains = sorted(
            cell["domain"] for cell in cells if cell["source_team_id"] == other["source_team_id"]
        )
        self.assertEqual(tamu_domains, other_domains)

    def test_no_outcome_field_reaches_a_row(self) -> None:
        rows, _ = build()
        forbidden = ("points", "score", "winner", "margin", "final_status")
        for row in rows:
            self.assertFalse(row["target_outcome_fields_present"])
            for key, value in row.items():
                self.assertFalse(
                    any(marker in key for marker in forbidden),
                    msg=f"row carried an outcome-shaped field: {key}",
                )
                if "result" in key:
                    self.assertTrue(
                        key.endswith("_state"),
                        msg=f"row carried a result value rather than a result state: {key}",
                    )
                    self.assertIn(value, (ADMITTED_PROSPECTIVE_PREKICKOFF, SOURCE_EVIDENCE_ABSENT, TEMPORALLY_INELIGIBLE))

    def test_summary_counts_every_cell_once(self) -> None:
        rows, cells = build()
        summary = summarize(rows, cells)
        self.assertEqual(summary["row_count"], len(rows))
        self.assertEqual(summary["cell_count"], len(cells))
        total = sum(
            count
            for domain in summary["domain_admission_counts"].values()
            for count in domain.values()
        )
        self.assertEqual(total, len(cells))


if __name__ == "__main__":
    unittest.main()
