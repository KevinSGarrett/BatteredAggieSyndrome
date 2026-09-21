"""R35-02/04/07/08 regression tests for MR34-03/04/06/08/09.

Each repair is tested with both a rejection case (the manager's
counterexample) and the positive control it must not break, because a
boundary that rejects everything is not a boundary -- it is an outage.
"""

from __future__ import annotations

import sqlite3
import unittest

from aggie_analytics.cycle33 import query as q
from aggie_analytics.cycle33.career_identity import (
    UNRESOLVED_PAGE_IDENTITY,
    join_occupant_to_pages,
    page_identity_key,
    page_own_person_evidence,
)
from aggie_analytics.cycle33.confirmed_spans import (
    ConfirmedSpanError,
    quarantine_unlocatable_cell,
    require_locatable_confirmed,
    role_support_is_confirmed,
)
from aggie_analytics.cycle33.neutral import NeutralVenueError, travel_context
from aggie_analytics.cycle33.official_finals import (
    competing_observations,
    is_eligible_official_final,
    supplied_winner_disagrees_with_scores,
    winner_from_scores,
)
from aggie_analytics.cycle33.span_locate import bind_person_role
from aggie_analytics.cycle35.program_aliases import (
    build_crosswalk,
    resolve_program,
    slug,
    unescape_source_name,
)

STAFF_HTML = (
    "<table>"
    "<tr><td>John Smithson</td><td>Head Coach</td></tr>"
    "<tr><td>Mike Elko</td><td>Head Coach</td></tr>"
    "<tr><td>Collin Klein</td><td>Offensive Coordinator</td></tr>"
    "</table>"
)

BOUND_VENUE = {
    "canonical_contest_id": "C1",
    "administrative_home_id": "TEAM:HOME",
    "administrative_away_id": "TEAM:AWAY",
    "venue_id": "VENUE:1",
    "venue_version": "v1",
    "venue_timezone": "America/Chicago",
}


# --------------------------------------------------------------- R35-02


class SubstringIdentityTests(unittest.TestCase):
    """MR34-03: `John Smith` must not be confirmed from `John Smithson`."""

    def test_substring_surname_prefix_is_not_identity(self) -> None:
        found = bind_person_role(STAFF_HTML, person="John Smith", title="Head Coach")
        self.assertFalse(found["person_record_bound"])
        with self.assertRaises(ConfirmedSpanError):
            require_locatable_confirmed(
                STAFF_HTML, person="John Smith", title="Head Coach"
            )

    def test_exact_person_still_binds(self) -> None:
        """Positive control -- the repair must not break real matching."""
        found = bind_person_role(STAFF_HTML, person="Mike Elko", title="Head Coach")
        self.assertTrue(found["person_record_bound"])
        self.assertTrue(found["role_claim_supported"])

    def test_longer_record_name_still_matches_shorter_claim_on_whole_tokens(self) -> None:
        html = "<table><tr><td>Mike Elko Jr.</td><td>Head Coach</td></tr></table>"
        found = bind_person_role(html, person="Mike Elko", title="Head Coach")
        self.assertTrue(found["person_record_bound"])

    def test_single_token_claim_is_not_an_identity(self) -> None:
        found = bind_person_role(STAFF_HTML, person="Smith", title="Head Coach")
        self.assertFalse(found["person_record_bound"])

    def test_reordered_sourced_alias_still_matches(self) -> None:
        html = "<table><tr><td>Elko, Mike</td><td>Head Coach</td></tr></table>"
        found = bind_person_role(html, person="Mike Elko", title="Head Coach")
        self.assertTrue(found["person_record_bound"])


class QuotedNicknameTests(unittest.TestCase):
    """R35-02: a defect the 880-row reparse surfaced on real data.

    `Deion "Coach Prime" Sanders` was not recognised as a name at all,
    because the title heuristic matched the word `Coach` inside the quoted
    nickname. The staff row was never extracted, so a correctly sourced,
    real head-coach appointment silently vanished from the record set.
    """

    HTML = (
        '<table><tr><td>Deion "Coach Prime" Sanders</td>'
        "<td>Head Football Coach</td></tr></table>"
    )

    def test_nickname_containing_a_title_word_is_still_a_name(self) -> None:
        from aggie_analytics.cycle33.span_locate import _name_like

        self.assertTrue(_name_like('Deion "Coach Prime" Sanders'))

    def test_a_real_title_is_still_a_title(self) -> None:
        from aggie_analytics.cycle33.span_locate import _name_like

        self.assertFalse(_name_like("Head Football Coach"))
        self.assertFalse(_name_like("Defensive Coordinator"))

    def test_the_record_now_binds_under_its_full_sourced_name(self) -> None:
        found = bind_person_role(
            self.HTML,
            person='Deion "Coach Prime" Sanders',
            title="Head Football Coach",
        )
        self.assertTrue(found["person_record_bound"])
        self.assertTrue(found["role_claim_supported"])

    def test_the_nickname_free_alias_also_binds(self) -> None:
        found = bind_person_role(
            self.HTML, person="Deion Sanders", title="Head Football Coach"
        )
        self.assertTrue(found["person_record_bound"])

    def test_a_different_person_is_still_rejected(self) -> None:
        """The alias must widen matching for one person, not for everyone."""
        found = bind_person_role(
            self.HTML, person="Deion Sandersonian", title="Head Football Coach"
        )
        self.assertFalse(found["person_record_bound"])

    def test_apostrophes_in_names_are_not_treated_as_nickname_quotes(self) -> None:
        from aggie_analytics.cycle33.span_locate import strip_quoted_nickname

        for name in ("Ka'imi O'Brien", "Hawai'i", "D'Andre O'Neal"):
            self.assertEqual(strip_quoted_nickname(name), name)

    def test_apostrophe_name_still_binds(self) -> None:
        html = "<table><tr><td>D'Andre O'Neal</td><td>Head Coach</td></tr></table>"
        found = bind_person_role(html, person="D'Andre O'Neal", title="Head Coach")
        self.assertTrue(found["person_record_bound"])


class StrictRoleSupportTests(unittest.TestCase):
    """MR34-03: only the Boolean True confirms a role."""

    def test_string_false_does_not_confirm(self) -> None:
        self.assertFalse(role_support_is_confirmed({"role_claim_supported": "false"}))

    def test_other_truthy_values_do_not_confirm(self) -> None:
        for value in ("true", 1, "yes", [1], {"a": 1}, 1.0):
            self.assertFalse(
                role_support_is_confirmed({"role_claim_supported": value}), value
            )

    def test_boolean_true_confirms(self) -> None:
        self.assertTrue(role_support_is_confirmed({"role_claim_supported": True}))

    def test_string_false_cell_is_quarantined_not_confirmed(self) -> None:
        cell = {
            "person": "A Person",
            "disposition": "CONFIRMED_APPOINTMENT",
            "episode_refs": [{"role_claim_supported": "false"}],
        }
        out = quarantine_unlocatable_cell(cell)
        self.assertEqual(out["disposition"], "SPAN_NOT_LOCATABLE_QUARANTINE")

    def test_genuinely_supported_cell_survives(self) -> None:
        cell = {
            "person": "A Person",
            "disposition": "CONFIRMED_APPOINTMENT",
            "episode_refs": [{"role_claim_supported": True}],
        }
        out = quarantine_unlocatable_cell(cell)
        self.assertEqual(out["disposition"], "CONFIRMED_APPOINTMENT")

    def test_episode_conservation_still_holds(self) -> None:
        cell = {
            "person": "A Person",
            "disposition": "CONFIRMED_APPOINTMENT",
            "episode_refs": [
                {"role_claim_supported": True},
                {"role_claim_supported": "false"},
            ],
        }
        out = quarantine_unlocatable_cell(cell)
        kept = len(out.get("episode_refs") or [])
        quarantined = len(out.get("quarantined_unlocatable_episodes") or [])
        self.assertEqual(kept + quarantined, 2)


class CareerIdentityTests(unittest.TestCase):
    """MR34-04: caller override, process-address identity, role/time binding."""

    @staticmethod
    def _alice_page():
        return {
            "wikimedia_page_id": "synthetic-alice",
            "title": "Alice Example (American football)",
            "episodes": [
                {
                    "person": "Alice Example",
                    "sport": "American football",
                    "program_raw": "Example State",
                    "role": "Offensive Coordinator",
                    "season": "2021",
                }
            ],
        }

    def test_caller_occupant_cannot_override_contrary_page_evidence(self) -> None:
        page = dict(self._alice_page(), occupant_person="Bob Example")
        out = join_occupant_to_pages(
            person="Bob Example", program_display="Example State", pages=[page]
        )
        self.assertEqual(
            out["career_join_state"], "FOOTBALL_PAGE_PERSON_IDENTITY_UNMATCHED"
        )
        self.assertTrue(out["same_name_only"])

    def test_the_page_own_person_still_joins(self) -> None:
        """Positive control."""
        out = join_occupant_to_pages(
            person="Alice Example",
            program_display="Example State",
            pages=[self._alice_page()],
        )
        self.assertEqual(out["career_join_state"], "EVIDENCE_BOUND_CAREER_JOIN")

    def test_page_own_person_evidence_excludes_caller_field(self) -> None:
        page = dict(self._alice_page(), occupant_person="Bob Example")
        evidence = page_own_person_evidence(page)
        self.assertNotIn("Bob Example", evidence)
        self.assertIn("Alice Example", evidence)

    def test_page_identity_never_uses_a_process_address(self) -> None:
        first: dict = {}
        second: dict = {}  # both retained so neither id() can be reused
        self.assertEqual(page_identity_key(first), UNRESOLVED_PAGE_IDENTITY)
        self.assertEqual(page_identity_key(second), UNRESOLVED_PAGE_IDENTITY)
        self.assertNotIn("opaque", page_identity_key(first))

    def test_role_and_season_must_be_satisfied_by_a_concrete_episode(self) -> None:
        out = join_occupant_to_pages(
            person="Alice Example",
            program_display="Example State",
            pages=[self._alice_page()],
            role="Offensive Coordinator",
            season="2021",
        )
        self.assertEqual(out["career_join_state"], "EVIDENCE_BOUND_ROLE_TIME_JOIN")
        self.assertTrue(out["role_time_bound"])
        self.assertEqual(out["matched_episode"]["role_raw"], "Offensive Coordinator")
        self.assertEqual(out["matched_episode"]["season"], "2021")

    def test_wrong_role_is_not_supported_by_any_episode(self) -> None:
        out = join_occupant_to_pages(
            person="Alice Example",
            program_display="Example State",
            pages=[self._alice_page()],
            role="Head Coach",
            season="2021",
        )
        self.assertEqual(
            out["career_join_state"], "ROLE_TIME_NOT_SUPPORTED_BY_ANY_EPISODE"
        )
        self.assertFalse(out["role_time_bound"])

    def test_wrong_season_is_not_supported_by_any_episode(self) -> None:
        out = join_occupant_to_pages(
            person="Alice Example",
            program_display="Example State",
            pages=[self._alice_page()],
            role="Offensive Coordinator",
            season="1999",
        )
        self.assertEqual(
            out["career_join_state"], "ROLE_TIME_NOT_SUPPORTED_BY_ANY_EPISODE"
        )

    def test_omitting_role_time_is_reported_not_implied(self) -> None:
        out = join_occupant_to_pages(
            person="Alice Example",
            program_display="Example State",
            pages=[self._alice_page()],
        )
        self.assertFalse(out["role_time_requested"])
        self.assertFalse(out["role_time_bound"])
        self.assertIsNone(out["matched_episode"])


# --------------------------------------------------------------- R35-04


class QueryCompletenessTests(unittest.TestCase):
    """MR34-06: no disposition may be invisible to the state views."""

    def _db(self, dispositions):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(q.SCHEMA_SQL)
        for index, disposition in enumerate(dispositions):
            conn.execute(
                "INSERT INTO staff_role_cells (observation_id, team, season, "
                "role_column, person, disposition, support_column, "
                "principal_role_blocked, source_class, pit_admitted, verified) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (f"obs-{index}", "T", "2026", "head_coach", "P",
                 disposition, 1, 0, "SRC", 0, 0),
            )
        conn.commit()
        return conn

    def test_roster_observation_unresolved_is_visible(self) -> None:
        conn = self._db(["ROSTER_OBSERVATION_UNRESOLVED"] * 57)
        self.assertEqual(len(q.unresolved_roles(conn)), 57)

    def test_an_unknown_future_state_is_over_reported_not_hidden(self) -> None:
        conn = self._db(["SOME_STATE_THIS_CODE_HAS_NEVER_SEEN"])
        self.assertEqual(len(q.unresolved_roles(conn)), 1)

    def test_verified_rows_are_not_reported_unresolved(self) -> None:
        conn = self._db(["RESOLVED_CAREER_JOIN_VERIFIED"] * 3)
        self.assertEqual(len(q.unresolved_roles(conn)), 0)
        self.assertEqual(len(q.verified_roles(conn)), 3)

    def test_states_partition_the_table(self) -> None:
        conn = self._db(
            ["RESOLVED_CAREER_JOIN_VERIFIED"] * 2
            + ["CORRECTLY_REJECTED_NO_EMPLOYER_MATCH"]
            + ["SPAN_NOT_LOCATABLE_QUARANTINE"]
            + ["SOMETHING_WITH_CONFLICT_IN_IT"]
            + ["ROSTER_OBSERVATION_UNRESOLVED"] * 4
        )
        report = q.role_state_conservation(conn)
        self.assertTrue(report["states_partition_table"])
        self.assertEqual(report["table_row_count"], report["classified_row_count"])
        self.assertEqual(report["state_counts"]["VERIFIED"], 2)
        self.assertEqual(report["state_counts"]["REJECTED"], 1)
        self.assertEqual(report["state_counts"]["QUARANTINED"], 1)
        self.assertEqual(report["state_counts"]["CONFLICTED"], 1)
        self.assertEqual(report["state_counts"]["UNRESOLVED"], 4)

    def test_separate_views_exist_for_each_negative_state(self) -> None:
        conn = self._db(
            ["CORRECTLY_REJECTED_NO_EMPLOYER_MATCH",
             "SPAN_NOT_LOCATABLE_QUARANTINE",
             "CANONICAL_CONFLICT_UNADJUDICATED"]
        )
        self.assertEqual(len(q.rejected_roles(conn)), 1)
        self.assertEqual(len(q.quarantined_roles(conn)), 1)
        self.assertEqual(len(q.conflicted_roles(conn)), 1)

    def test_row_without_a_person_is_unresolved_whatever_its_label(self) -> None:
        conn = self._db([])
        conn.execute(
            "INSERT INTO staff_role_cells (observation_id, team, season, "
            "role_column, person, disposition, support_column, "
            "principal_role_blocked, source_class, pit_admitted, verified) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("o", "T", "2026", "head_coach", None,
             "RESOLVED_CAREER_JOIN_VERIFIED", 1, 0, "SRC", 0, 1),
        )
        conn.commit()
        self.assertEqual(len(q.unresolved_roles(conn)), 1)


# --------------------------------------------------------------- R35-07


class OfficialFinalConsistencyTests(unittest.TestCase):
    """MR34-09: a row cannot contradict itself and still be an official final."""

    @staticmethod
    def _row(**overrides):
        row = {
            "ncaa_contest_id": "G1",
            "home_points": 30,
            "away_points": 10,
            "home_canonical_team_id": "H",
            "away_canonical_team_id": "A",
            "status_code_display": "Final",
            "game_state": "F",
            "terminal_state": "TERMINAL_STATUS_ESTABLISHED",
        }
        row.update(overrides)
        return row

    def test_winner_is_recomputed_from_scores(self) -> None:
        self.assertEqual(winner_from_scores(self._row()), "HOME")
        self.assertEqual(
            winner_from_scores(self._row(home_points=3, away_points=9)), "AWAY"
        )
        self.assertEqual(
            winner_from_scores(self._row(home_points=7, away_points=7)), "TIE"
        )

    def test_contradictory_winner_is_not_an_eligible_final(self) -> None:
        self.assertTrue(supplied_winner_disagrees_with_scores(self._row(winner="AWAY")))
        self.assertFalse(is_eligible_official_final(self._row(winner="AWAY")))

    def test_agreeing_winner_is_still_an_eligible_final(self) -> None:
        """Positive control."""
        self.assertFalse(supplied_winner_disagrees_with_scores(self._row(winner="HOME")))
        self.assertTrue(is_eligible_official_final(self._row(winner="HOME")))

    def test_absent_winner_label_is_not_a_contradiction(self) -> None:
        self.assertFalse(supplied_winner_disagrees_with_scores(self._row()))
        self.assertTrue(is_eligible_official_final(self._row()))

    def test_contradiction_is_retained_with_its_exact_reason(self) -> None:
        grouped = competing_observations([self._row(winner="AWAY")])
        self.assertEqual(len(grouped["admitted_unique_games"]), 0)
        inconsistent = grouped["internally_inconsistent_observations"]
        self.assertEqual(len(inconsistent), 1)
        self.assertEqual(
            inconsistent[0]["reason"], "SUPPLIED_WINNER_CONTRADICTS_SCORES"
        )
        self.assertEqual(inconsistent[0]["recomputed_winner"], ["HOME"])
        self.assertEqual(len(grouped["preserved_observations"]), 1)

    def test_tie_labelled_tie_is_consistent(self) -> None:
        row = self._row(home_points=7, away_points=7, winner="TIE")
        self.assertFalse(supplied_winner_disagrees_with_scores(row))


class ProgramAliasTests(unittest.TestCase):
    """R35-02/R35-07: aliases are declared, and ambiguity fails closed."""

    CROSSWALK = build_crosswalk(
        [
            {"program_id": "P:1", "display_name": "Arizona State"},
            {"program_id": "P:2", "display_name": "Alabama A&M"},
            {"program_id": "P:3", "display_name": "Georgia Southern"},
            {"program_id": "P:4", "display_name": "Alcorn State"},
        ]
    )

    def test_unicode_escape_in_a_publisher_name_is_decoded(self) -> None:
        self.assertEqual(unescape_source_name("Alabama A\\u0026M"), "Alabama A&M")
        self.assertEqual(slug("Alabama A\\u0026M"), "alabama-a-m")

    def test_escaped_ampersand_name_now_binds(self) -> None:
        out = resolve_program("Alabama A\\u0026M", self.CROSSWALK)
        self.assertEqual(out["resolution_state"], "RESOLVED")
        self.assertEqual(out["program_id"], "P:2")

    def test_token_abbreviation_expands(self) -> None:
        out = resolve_program("arizona-st", self.CROSSWALK)
        self.assertEqual(out["resolution_state"], "RESOLVED")
        self.assertEqual(out["program_id"], "P:1")
        self.assertEqual(out["rule"], "DECLARED_ALIAS_EXPANSION")

    def test_direct_slug_is_labelled_as_such(self) -> None:
        out = resolve_program("Georgia Southern", self.CROSSWALK)
        self.assertEqual(out["rule"], "DIRECT_SLUG")

    def test_a_program_outside_the_population_stays_unresolved(self) -> None:
        out = resolve_program("Tuskegee", self.CROSSWALK)
        self.assertEqual(
            out["resolution_state"], "UNRESOLVED_NOT_IN_DECLARED_POPULATION"
        )
        self.assertIsNone(out["program_id"])

    def test_no_fuzzy_prefix_match(self) -> None:
        """`arizona` must not silently become `Arizona State`."""
        out = resolve_program("arizona", self.CROSSWALK)
        self.assertEqual(
            out["resolution_state"], "UNRESOLVED_NOT_IN_DECLARED_POPULATION"
        )

    def test_historical_renames_resolve_to_their_canonical_program(self) -> None:
        """Documented renames found by ingesting the 2000-2012 corpus."""
        crosswalk = build_crosswalk(
            [
                {"program_id": "P:1", "display_name": "App State"},
                {"program_id": "P:2", "display_name": "Missouri State"},
                {"program_id": "P:3", "display_name": "Texas State"},
                {"program_id": "P:4", "display_name": "Troy"},
                {"program_id": "P:5", "display_name": "SE Louisiana"},
            ]
        )
        for published, expected in (
            ("Appalachian State", "P:1"),
            ("Southwest Missouri State", "P:2"),
            ("Southwest Texas State", "P:3"),
            ("Troy State", "P:4"),
            ("Southeastern Louisiana", "P:5"),
        ):
            out = resolve_program(published, crosswalk)
            self.assertEqual(out["resolution_state"], "RESOLVED", published)
            self.assertEqual(out["program_id"], expected, published)

    def test_deliberately_unresolved_names_stay_unresolved(self) -> None:
        """The invariant that matters most: an ambiguous or discontinued
        program must NOT be bound to something that merely looks close."""
        from aggie_analytics.cycle35.program_aliases import DELIBERATELY_UNRESOLVED

        crosswalk = build_crosswalk(
            [
                {"program_id": "P:1", "display_name": "UAlbany"},
                {"program_id": "P:2", "display_name": "Albany State"},
                {"program_id": "P:3", "display_name": "Robert Morris"},
                {"program_id": "P:4", "display_name": "St. John's"},
            ]
        )
        for published in ("Albany", "Morris Brown", "St. John's (NY)", "Canisius"):
            out = resolve_program(published, crosswalk)
            self.assertNotEqual(out["resolution_state"], "RESOLVED", published)
        # Each is documented with a reason rather than silently dropped.
        self.assertIn("albany", DELIBERATELY_UNRESOLVED)
        self.assertIn("morris-brown", DELIBERATELY_UNRESOLVED)
        for reason in DELIBERATELY_UNRESOLVED.values():
            self.assertTrue(reason.strip())

    def test_ambiguous_population_slug_is_excluded_not_guessed(self) -> None:
        crosswalk = build_crosswalk(
            [
                {"program_id": "P:1", "display_name": "Miami"},
                {"program_id": "P:2", "display_name": "Miami"},
            ]
        )
        self.assertIn("miami", crosswalk["ambiguous_slugs"])
        out = resolve_program("Miami", crosswalk)
        self.assertNotEqual(out["resolution_state"], "RESOLVED")


# --------------------------------------------------------------- R35-08


class TravelContextTests(unittest.TestCase):
    """MR34-08: string confirmation and null identities."""

    def test_string_false_venue_confirmation_raises(self) -> None:
        with self.assertRaises(NeutralVenueError):
            travel_context(
                {**BOUND_VENUE, "neutral_site": False},
                home_distance=1.0,
                away_distance=2.0,
                venue_confirmed="false",
                distance_method="GREAT_CIRCLE_WGS84",
            )

    def test_string_true_venue_confirmation_also_raises(self) -> None:
        """A flag must be a flag, even when the string means the right thing."""
        with self.assertRaises(NeutralVenueError):
            travel_context(
                {**BOUND_VENUE, "neutral_site": False},
                home_distance=1.0,
                away_distance=2.0,
                venue_confirmed="true",
                distance_method="GREAT_CIRCLE_WGS84",
            )

    def test_missing_identities_are_refused_not_emitted_as_null(self) -> None:
        with self.assertRaises(NeutralVenueError) as caught:
            travel_context(
                {"neutral_site": False},
                home_distance=1.0,
                away_distance=2.0,
                venue_confirmed=True,
                distance_method="GREAT_CIRCLE_WGS84",
            )
        self.assertIn("venue_id", str(caught.exception))

    def test_bound_identities_produce_a_travel_context(self) -> None:
        """Positive control."""
        row = travel_context(
            {**BOUND_VENUE, "neutral_site": False},
            home_distance=0.0,
            away_distance=250.0,
            venue_confirmed=True,
            distance_method="GREAT_CIRCLE_WGS84",
        )
        self.assertEqual(row["missing_identity_fields"], [])
        self.assertEqual(row["distance_unit"], "KILOMETRES")
        self.assertEqual(row["distance_method"], "GREAT_CIRCLE_WGS84")

    def test_distance_without_a_declared_method_is_refused(self) -> None:
        with self.assertRaises(NeutralVenueError):
            travel_context(
                {**BOUND_VENUE, "neutral_site": False},
                home_distance=10.0,
                away_distance=20.0,
                venue_confirmed=True,
            )

    def test_confirmed_neutral_has_zero_ordinary_home_advantage(self) -> None:
        row = travel_context(
            {**BOUND_VENUE, "neutral_site": True},
            home_distance=10.0,
            away_distance=10.0,
            venue_confirmed=True,
            distance_method="GREAT_CIRCLE_WGS84",
        )
        self.assertEqual(row["ordinary_home_advantage"], 0.0)

    def test_unequal_travel_at_a_neutral_venue_is_kept_separate(self) -> None:
        row = travel_context(
            {**BOUND_VENUE, "neutral_site": True},
            home_distance=100.0,
            away_distance=2500.0,
            venue_confirmed=True,
            distance_method="GREAT_CIRCLE_WGS84",
        )
        self.assertEqual(row["ordinary_home_advantage"], 0.0)
        self.assertNotEqual(row["home_travel_distance"], row["away_travel_distance"])
        self.assertTrue(row["asymmetric_travel_is_separate_feature"])

    def test_unknown_neutral_state_stays_unknown(self) -> None:
        row = travel_context(
            {**BOUND_VENUE, "neutral_site": None},
            home_distance=10.0,
            away_distance=20.0,
            venue_confirmed=True,
            distance_method="GREAT_CIRCLE_WGS84",
        )
        self.assertEqual(row["neutral_state"], "UNKNOWN")
        self.assertIsNone(row["ordinary_home_advantage"])

    def test_missing_coordinates_leave_distance_unknown_not_zero(self) -> None:
        row = travel_context(
            {**BOUND_VENUE, "neutral_site": False},
            home_distance=None,
            away_distance=None,
            venue_confirmed=True,
        )
        self.assertIsNone(row["home_travel_distance"])
        self.assertIsNone(row["away_travel_distance"])
        self.assertIsNone(row["distance_unit"])

    def test_partial_mode_reports_what_is_missing(self) -> None:
        row = travel_context(
            {"neutral_site": True},
            home_distance=None,
            away_distance=None,
            venue_confirmed=True,
            require_identities=False,
        )
        self.assertFalse(row["identities_required"])
        self.assertIn("venue_id", row["missing_identity_fields"])

    def test_negative_and_nonfinite_distances_are_still_rejected(self) -> None:
        for bad in (-1.0, float("nan"), float("inf")):
            with self.assertRaises(NeutralVenueError):
                travel_context(
                    {**BOUND_VENUE, "neutral_site": False},
                    home_distance=bad,
                    away_distance=10.0,
                    venue_confirmed=True,
                    distance_method="GREAT_CIRCLE_WGS84",
                )


if __name__ == "__main__":
    unittest.main()
