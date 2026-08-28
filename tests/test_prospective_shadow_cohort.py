"""Offline tests for the prospective 2026 national shadow cohort.

Nothing here touches the network. The scoreboard fixtures are hand-built from the
official page structure so that parser, eligibility, outcome-exclusion, and
mutation behaviour can be exercised deterministically.
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.prospective_shadow_cohort import (  # noqa: E402
    COHORT_STATES,
    CONTRACT_ID,
    GATE_RELATIVE,
    LANE,
    PASS_RESULT,
    assert_no_outcome_evidence,
    build_cohort,
    classify_game,
    kickoff_bound,
    load_alias_population,
    load_contract,
    normalize_team_name,
    parse_scoreboard_document,
    resolve_participant,
    strip_record_suffix,
)

CONTRACT = load_contract(REPO_ROOT)


def scoreboard_card(
    *,
    contest_id: str,
    game_date: str,
    annotation: str,
    away: tuple[str, str],
    home: tuple[str, str],
    neutral_site: str = "",
) -> str:
    """Reproduce the official card markup, including the outcome cells we ignore."""

    neutral = (
        f'<tr><td colspan="10" valign="middle">@{neutral_site}</td></tr>' if neutral_site else ""
    )
    return f"""
<div class="card m-2" style="min-width: 360px;"><div class="card-body p-1"><div class="table-responsive"><table>
<tbody><tr><td colspan="10" valign="middle"><div class="row p-0"><div class="col-6 p-0">
{game_date} {annotation}
</div><div class="col p-0 text-right"><div class="livestream_status_{contest_id} livestream_status">
<span id="period_{contest_id}"></span><span id="clock_{contest_id}"></span></div></div></div></td></tr>
{neutral}
<tr id="contest_{contest_id}">
<td valign="middle" width="30px"><img class="logo_image" alt="{away[1]}" src="x.gif"></td>
<td valign="middle" class=" opponents_min_width" nowrap="">
<a target="TEAMS_WIN" class="skipMask" href="/teams/{away[0]}"> {away[1]} (2-1)</a></td>
<td rowspan="2" class="linescore_min_width"><table id="linescore_{contest_id}_table"><tbody>
<tr id="competitor_1_linescores"><td id="linescore_1_1">7</td></tr></tbody></table></td>
<td align="right" class="totalcol"><div id="score_1" class="p-1">31</div></td>
</tr>
<tr id="contest_{contest_id}">
<td valign="middle" width="30px"><img class="logo_image" alt="{home[1]}" src="y.gif"></td>
<td valign="middle" class=" opponents_min_width" nowrap="">
<a target="TEAMS_WIN" class="skipMask" href="/teams/{home[0]}"> {home[1]} (0-3)</a></td>
<td align="right" class="totalcol"><div id="score_2" class="p-1">10</div></td>
</tr>
</tbody></table></div></div></div>
"""


def scoreboard_document(cards: list[str], *, game_date: str) -> str:
    printable = datetime.strptime(game_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    return (
        "<html><body><form><input type=\"hidden\" name=\"game_date\" "
        f'id="change_sport_game_date" value="{printable}"></form>'
        "<!-- livestream_scoreboards --><table class=\"livestream_table\"></table>"
        + "".join(cards)
        + "</body></html>"
    )


POPULATION = {
    "texas a and m": {
        "canonical_team_id": "SRC-002:TEAM:245",
        "spine_display_name": "Texas A&M",
        "most_recent_observed_season": 2025,
        "observed_season_count": 63,
    },
    "missouri state": {
        "canonical_team_id": "SRC-002:TEAM:2623",
        "spine_display_name": "Missouri State",
        "most_recent_observed_season": 2025,
        "observed_season_count": 20,
    },
    "florida atlantic": {
        "canonical_team_id": "SRC-002:TEAM:2226",
        "spine_display_name": "Florida Atlantic",
        "most_recent_observed_season": 2025,
        "observed_season_count": 25,
    },
}


class NameNormalizationTests(unittest.TestCase):
    def test_orthographic_variants_of_one_program_fold_together(self) -> None:
        self.assertEqual(normalize_team_name("Texas A&amp;M"), normalize_team_name("Texas A&M"))
        self.assertEqual(normalize_team_name("Missouri St."), normalize_team_name("Missouri State"))
        self.assertEqual(normalize_team_name("Fla. Atlantic"), normalize_team_name("Florida Atlantic"))
        self.assertEqual(normalize_team_name("Lamar University"), normalize_team_name("Lamar"))

    def test_distinct_programs_do_not_fold_together(self) -> None:
        for left, right in (
            ("Texas A&M", "Texas"),
            ("Miami (FL)", "Miami (OH)"),
            ("Southern Miss.", "Mississippi"),
            ("Alabama A&M", "Alabama"),
        ):
            self.assertNotEqual(normalize_team_name(left), normalize_team_name(right))

    def test_a_genuine_initialism_is_not_expanded(self) -> None:
        self.assertNotEqual(normalize_team_name("NIU"), normalize_team_name("Northern Illinois"))

    def test_prior_record_suffix_is_discarded_rather_than_stored(self) -> None:
        self.assertEqual(strip_record_suffix("Texas A&amp;M (0-0)"), ("Texas A&M", True))
        self.assertEqual(strip_record_suffix("Texas A&amp;M"), ("Texas A&M", False))


class AliasPopulationTests(unittest.TestCase):
    def _write(self, rows: list[dict[str, object]]) -> Path:
        path = Path(self.enterContext(__import__("tempfile").TemporaryDirectory())) / "aliases.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return path

    def test_stale_programs_are_excluded_by_the_recency_floor(self) -> None:
        path = self._write(
            [
                {"canonical_team_id": "A", "source_team_name": "Live Program", "observed_seasons": [2019, 2024]},
                {"canonical_team_id": "B", "source_team_name": "Retired Program", "observed_seasons": [1971]},
            ]
        )
        population = load_alias_population(path, minimum_most_recent_season=2020)
        self.assertEqual(sorted(population), ["live program"])

    def test_an_ambiguous_normalized_name_is_dropped_rather_than_arbitrated(self) -> None:
        path = self._write(
            [
                {"canonical_team_id": "A", "source_team_name": "Sample St.", "observed_seasons": [2024]},
                {"canonical_team_id": "B", "source_team_name": "Sample State", "observed_seasons": [2024]},
            ]
        )
        self.assertEqual(load_alias_population(path, minimum_most_recent_season=2020), {})

    def test_an_unresolved_participant_is_reported_not_guessed(self) -> None:
        resolved = resolve_participant({"source_display_name": "NIU", "source_team_id": "1"}, POPULATION)
        self.assertIsNone(resolved["canonical_team_id"])
        self.assertEqual(resolved["resolution_state"], "UNRESOLVED_SOURCE_ENTITY")


class ParserTests(unittest.TestCase):
    def test_a_well_formed_card_yields_identity_time_site_and_participants(self) -> None:
        document = scoreboard_document(
            [
                scoreboard_card(
                    contest_id="6607349",
                    game_date="09/05/2026",
                    annotation="07:00 PM ESPN",
                    away=("622180", "Missouri St."),
                    home=("622236", "Texas A&amp;M"),
                )
            ],
            game_date="2026-09-05",
        )
        rows = parse_scoreboard_document(document, game_date="2026-09-05")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["parse_state"], "PARSED")
        self.assertEqual(row["ncaa_contest_id"], "6607349")
        self.assertEqual(row["source_published_clock_text"], "07:00 PM")
        self.assertEqual(row["source_published_broadcast_text"], "ESPN")
        self.assertEqual(row["neutral_site_text"], "")
        self.assertEqual([p["source_display_name"] for p in row["participants"]], ["Missouri St.", "Texas A&M"])

    def test_a_neutral_site_card_records_the_site_text(self) -> None:
        document = scoreboard_document(
            [
                scoreboard_card(
                    contest_id="6599634",
                    game_date="08/29/2026",
                    annotation="TBA",
                    away=("1", "Alpha"),
                    home=("2", "Beta"),
                    neutral_site="Canyon, TX",
                )
            ],
            game_date="2026-08-29",
        )
        row = parse_scoreboard_document(document, game_date="2026-08-29")[0]
        self.assertEqual(row["neutral_site_text"], "Canyon, TX")
        self.assertEqual(row["source_published_clock_text"], "TBA")

    def test_a_card_whose_header_date_contradicts_the_request_fails_closed(self) -> None:
        document = scoreboard_document(
            [
                scoreboard_card(
                    contest_id="7",
                    game_date="09/06/2026",
                    annotation="01:00 PM",
                    away=("1", "Alpha"),
                    home=("2", "Beta"),
                )
            ],
            game_date="2026-09-05",
        )
        row = parse_scoreboard_document(document, game_date="2026-09-05")[0]
        self.assertEqual(row["parse_state"], "FAIL_CLOSED_IDENTITY_MISMATCH")
        self.assertEqual(row["parse_reason"], "CARD_HEADER_DATE_DOES_NOT_MATCH_REQUESTED_DATE")

    def test_a_card_with_a_repeated_participant_fails_closed(self) -> None:
        document = scoreboard_document(
            [
                scoreboard_card(
                    contest_id="8",
                    game_date="09/05/2026",
                    annotation="01:00 PM",
                    away=("1", "Alpha"),
                    home=("1", "Alpha"),
                )
            ],
            game_date="2026-09-05",
        )
        row = parse_scoreboard_document(document, game_date="2026-09-05")[0]
        self.assertEqual(row["parse_state"], "FAIL_CLOSED_IDENTITY_MISMATCH")
        self.assertEqual(row["parse_reason"], "CARD_PARTICIPANTS_ARE_NOT_DISTINCT")

    def test_an_empty_scoreboard_yields_no_rows_rather_than_an_error(self) -> None:
        self.assertEqual(parse_scoreboard_document(scoreboard_document([], game_date="2026-08-22"), game_date="2026-08-22"), [])


class KickoffBoundTests(unittest.TestCase):
    def test_the_published_clock_converts_with_the_declared_offset(self) -> None:
        bound, state = kickoff_bound(game_date="2026-09-05", clock_text="07:00 PM", offset_seconds=-14400)
        self.assertEqual(bound, "2026-09-05T23:00:00Z")
        self.assertEqual(state, "KICKOFF_TIME_PUBLISHED")

    def test_the_declared_offset_is_the_earliest_continental_united_states_instant(self) -> None:
        eastern, _ = kickoff_bound(game_date="2026-09-05", clock_text="07:00 PM", offset_seconds=-14400)
        pacific, _ = kickoff_bound(game_date="2026-09-05", clock_text="07:00 PM", offset_seconds=-25200)
        self.assertLess(eastern, pacific)

    def test_an_unpublished_or_unrecognized_clock_produces_no_bound(self) -> None:
        self.assertEqual(kickoff_bound(game_date="2026-09-05", clock_text="TBA", offset_seconds=-14400)[1], "KICKOFF_TIME_UNPUBLISHED")
        self.assertEqual(kickoff_bound(game_date="2026-09-05", clock_text="", offset_seconds=-14400)[1], "KICKOFF_TIME_UNPUBLISHED")
        self.assertEqual(kickoff_bound(game_date="2026-09-05", clock_text="noon", offset_seconds=-14400)[1], "KICKOFF_TIME_UNRECOGNIZED")

    def test_midnight_and_noon_convert_without_a_twelve_hour_error(self) -> None:
        self.assertEqual(kickoff_bound(game_date="2026-09-05", clock_text="12:00 PM", offset_seconds=-14400)[0], "2026-09-05T16:00:00Z")
        self.assertEqual(kickoff_bound(game_date="2026-09-05", clock_text="12:30 AM", offset_seconds=-14400)[0], "2026-09-05T04:30:00Z")


def classify(contest_id: str, annotation: str, *, now: str, away: str = "Missouri St.", home: str = "Texas A&M"):
    document = scoreboard_document(
        [
            scoreboard_card(
                contest_id=contest_id,
                game_date="09/05/2026",
                annotation=annotation,
                away=("622180", away),
                home=("622236", home),
            )
        ],
        game_date="2026-09-05",
    )
    record = parse_scoreboard_document(document, game_date="2026-09-05")[0]
    return classify_game(
        record,
        contract=CONTRACT,
        population=POPULATION,
        execution_time=datetime.fromisoformat(now.replace("Z", "+00:00")),
    )


class EligibilityTests(unittest.TestCase):
    def test_a_game_far_ahead_of_the_first_checkpoint_is_precommitted(self) -> None:
        row = classify("1", "07:00 PM", now="2026-08-28T18:00:00Z")
        self.assertEqual(row["cohort_state"], "PRECOMMITTED")
        self.assertFalse(row["snapshot_eligible"])
        self.assertEqual([c["state"] for c in row["checkpoints"]], ["OPEN", "OPEN"])

    def test_a_game_inside_the_final_window_is_snapshot_eligible(self) -> None:
        row = classify("2", "07:00 PM", now="2026-09-05T20:00:00Z")
        self.assertEqual(row["cohort_state"], "SNAPSHOT_ELIGIBLE")
        self.assertTrue(row["snapshot_eligible"])

    def test_a_game_past_the_cutoff_is_missed_with_no_backfill(self) -> None:
        row = classify("3", "07:00 PM", now="2026-09-05T22:00:00Z")
        self.assertEqual(row["cohort_state"], "MISSED_CUTOFF_NO_BACKFILL")
        self.assertFalse(row["snapshot_eligible"])

    def test_a_game_already_under_way_is_never_eligible(self) -> None:
        row = classify("4", "07:00 PM", now="2026-09-06T02:00:00Z")
        self.assertEqual(row["cohort_state"], "MISSED_CUTOFF_NO_BACKFILL")
        self.assertFalse(row["snapshot_eligible"])

    def test_the_cutoff_boundary_itself_is_still_open(self) -> None:
        self.assertEqual(classify("5", "07:00 PM", now="2026-09-05T21:30:00Z")["cohort_state"], "SNAPSHOT_ELIGIBLE")
        self.assertEqual(classify("6", "07:00 PM", now="2026-09-05T21:30:01Z")["cohort_state"], "MISSED_CUTOFF_NO_BACKFILL")

    def test_an_unpublished_kickoff_abstains_rather_than_guessing(self) -> None:
        row = classify("7", "TBA", now="2026-08-28T18:00:00Z")
        self.assertEqual(row["cohort_state"], "MISSING_REQUIRED_FEATURES_ABSTAIN")
        self.assertIsNone(row["kickoff_utc_conservative_lower_bound"])
        self.assertFalse(row["snapshot_eligible"])

    def test_an_unresolved_participant_outranks_every_timing_state(self) -> None:
        row = classify("8", "07:00 PM", now="2026-08-28T18:00:00Z", away="NIU")
        self.assertEqual(row["cohort_state"], "UNSUPPORTED_ENTITY")
        self.assertEqual(row["unresolved_participant_names"], ["NIU"])

    def test_every_emitted_state_belongs_to_the_declared_vocabulary(self) -> None:
        for annotation, now, away in (
            ("07:00 PM", "2026-08-28T18:00:00Z", "Missouri St."),
            ("07:00 PM", "2026-09-05T20:00:00Z", "Missouri St."),
            ("07:00 PM", "2026-09-06T02:00:00Z", "Missouri St."),
            ("TBA", "2026-08-28T18:00:00Z", "Missouri St."),
            ("07:00 PM", "2026-08-28T18:00:00Z", "NIU"),
        ):
            self.assertIn(classify("9", annotation, now=now, away=away)["cohort_state"], COHORT_STATES)


class OutcomeExclusionTests(unittest.TestCase):
    def test_the_source_card_really_does_carry_the_outcome_we_refuse_to_read(self) -> None:
        card = scoreboard_card(
            contest_id="10",
            game_date="09/05/2026",
            annotation="07:00 PM",
            away=("622180", "Missouri St."),
            home=("622236", "Texas A&M"),
        )
        self.assertIn("score_1", card)
        self.assertIn(">31<", card)

    def test_no_emitted_field_carries_an_outcome_marker_or_a_score(self) -> None:
        row = classify("11", "07:00 PM", now="2026-08-28T18:00:00Z")
        assert_no_outcome_evidence([row])
        encoded = json.dumps(row)
        self.assertNotIn("31", encoded)
        self.assertNotIn("(2-1)", encoded)
        self.assertFalse(row["outcome_fields_extracted"])

    def test_the_outcome_guard_rejects_a_smuggled_score(self) -> None:
        with self.assertRaises(ValueError):
            assert_no_outcome_evidence([{"note": "final was 31-10"}])
        with self.assertRaises(ValueError):
            assert_no_outcome_evidence([{"score_home": 31}])


class CohortAssemblyTests(unittest.TestCase):
    def _cohort(self, *, now: str, dates: list[str] | None = None, extra_cards=None, omit_capture=None):
        window = dates or list(CONTRACT["schedule_window"]["game_dates"])
        contract = json.loads(json.dumps(CONTRACT))
        contract["schedule_window"]["game_dates"] = window
        documents = {}
        for index, game_date in enumerate(window):
            printable = datetime.strptime(game_date, "%Y-%m-%d").strftime("%m/%d/%Y")
            cards = [
                scoreboard_card(
                    contest_id=str(9000 + index),
                    game_date=printable,
                    annotation="07:00 PM",
                    away=("622180", "Missouri St."),
                    home=("622236", "Texas A&M"),
                )
            ]
            if extra_cards:
                cards.extend(extra_cards(game_date, printable))
            documents[game_date] = scoreboard_document(cards, game_date=game_date)
        captures = [
            {
                "game_date": game_date,
                "raw_relative_path": f"raw/{game_date}.html",
                "source_uri": f"https://stats.ncaa.org/x?{game_date}",
                "request_identity_sha256": f"identity-{game_date}",
                "retrieved_at_utc": now,
                "route_id": "test",
            }
            for game_date in window
            if game_date != omit_capture
        ]
        root = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        for capture in captures:
            path = root / capture["raw_relative_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(documents[capture["game_date"]], encoding="utf-8")
        return build_cohort(
            contract=contract,
            captures=captures,
            documents=documents,
            population=POPULATION,
            execution_time=datetime.fromisoformat(now.replace("Z", "+00:00")),
            data_root=root,
        )

    def test_the_cohort_covers_every_declared_date_and_counts_reconcile(self) -> None:
        cohort = self._cohort(now="2026-08-28T18:00:00Z", dates=["2026-08-27", "2026-08-28", "2026-09-05"])
        self.assertEqual(cohort["population_counts"]["declared_game_dates"], 3)
        self.assertEqual(cohort["population_counts"]["official_contests_enumerated"], 3)
        self.assertEqual(sum(cohort["state_counts"].values()), len(cohort["rows"]))
        self.assertEqual(
            cohort["population_counts"]["snapshot_eligible_contests"], len(cohort["eligible_contest_ids"])
        )
        self.assertEqual(sorted(cohort["state_counts"]), sorted(COHORT_STATES))

    def test_a_missing_declared_date_is_rejected_rather_than_silently_dropped(self) -> None:
        with self.assertRaises(ValueError):
            self._cohort(
                now="2026-08-28T18:00:00Z",
                dates=["2026-08-27", "2026-08-28"],
                omit_capture="2026-08-28",
            )

    def test_a_contest_repeated_across_two_dates_is_rejected(self) -> None:
        def duplicate(_game_date: str, _printable: str) -> list[str]:
            return [
                scoreboard_card(
                    contest_id="9999",
                    game_date=_printable,
                    annotation="07:00 PM",
                    away=("622180", "Missouri St."),
                    home=("622236", "Texas A&M"),
                )
            ]

        with self.assertRaises(ValueError):
            self._cohort(now="2026-08-28T18:00:00Z", dates=["2026-08-27", "2026-08-28"], extra_cards=duplicate)

    def test_capture_inventory_hashes_the_actual_captured_bytes(self) -> None:
        cohort = self._cohort(now="2026-08-28T18:00:00Z", dates=["2026-09-05"])
        entry = cohort["capture_inventory"][0]
        self.assertEqual(len(entry["raw_sha256"]), 64)
        self.assertGreater(entry["raw_bytes"], 0)


class ContractAndGovernanceTests(unittest.TestCase):
    def test_the_contract_pins_the_observation_only_lane(self) -> None:
        self.assertEqual(CONTRACT["contract_id"], CONTRACT_ID)
        self.assertEqual(CONTRACT["lane"], LANE)
        self.assertEqual(CONTRACT["protected_lane"], "RETAIN_PROTECTED_LANE_BLOCKED")

    def test_the_contract_refuses_promotion_and_protected_authority(self) -> None:
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
            self.assertFalse(CONTRACT["authority"][field], field)

    def test_a_contract_that_opens_protected_evaluation_is_rejected(self) -> None:
        import tempfile

        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "configs").mkdir()
        mutated = json.loads(json.dumps(CONTRACT))
        mutated["authority"]["protected_evaluation_admission"] = True
        (root / "configs/prospective_2026_shadow_cohort_contract.json").write_text(
            json.dumps(mutated), encoding="utf-8"
        )
        with self.assertRaises(ValueError):
            load_contract(root)

    def test_a_contract_that_permits_retroactive_forecasts_is_rejected(self) -> None:
        import tempfile

        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "configs").mkdir()
        mutated = json.loads(json.dumps(CONTRACT))
        mutated["eligibility"]["retroactive_forecast_permitted"] = True
        (root / "configs/prospective_2026_shadow_cohort_contract.json").write_text(
            json.dumps(mutated), encoding="utf-8"
        )
        with self.assertRaises(ValueError):
            load_contract(root)

    def test_the_declared_window_covers_week_zero_and_week_one_without_overlap(self) -> None:
        window = CONTRACT["schedule_window"]
        self.assertEqual(
            sorted(window["week_zero_dates"] + window["week_one_dates"]), sorted(window["game_dates"])
        )
        self.assertFalse(set(window["week_zero_dates"]) & set(window["week_one_dates"]))


class PublishedGateTests(unittest.TestCase):
    """Guard the committed gate when it exists; the module is usable before it does."""

    @classmethod
    def setUpClass(cls) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            raise unittest.SkipTest("prospective 2026 shadow cohort gate is not published yet")
        cls.gate = json.loads(path.read_text(encoding="utf-8-sig"))

    def test_the_gate_passes_in_the_observation_only_lane(self) -> None:
        self.assertEqual(self.gate["result"], PASS_RESULT)
        self.assertEqual(self.gate["lane"], LANE)
        self.assertEqual(self.gate["jira_key"], "BAT-656")

    def test_the_gate_state_counts_reconcile_with_its_row_count(self) -> None:
        self.assertEqual(sum(self.gate["state_counts"].values()), self.gate["row_count"])
        self.assertEqual(
            self.gate["population_counts"]["snapshot_eligible_contests"], len(self.gate["eligible_contest_ids"])
        )

    def test_the_gate_claims_no_forecast_promotion_or_conclusion(self) -> None:
        for field, value in self.gate["scientific_nonclaims"].items():
            self.assertFalse(value, field)
        self.assertFalse(self.gate["eligibility_gate"]["retroactive_forecast_created"])
        self.assertFalse(self.gate["eligibility_gate"]["games_already_started_forecast"])
        self.assertFalse(self.gate["outcome_exclusion"]["outcome_fields_extracted"])

    def test_the_gate_binds_its_predecessors_and_keeps_payloads_out_of_git(self) -> None:
        for value in self.gate["bound_predecessors"].values():
            self.assertEqual(len(value), 64)
        self.assertFalse(self.gate["manifest"]["bulk_payloads_in_git"])

    def test_no_gate_field_carries_outcome_evidence(self) -> None:
        assert_no_outcome_evidence([{"eligible_contest_ids": self.gate["eligible_contest_ids"]}])


if __name__ == "__main__":
    unittest.main()
