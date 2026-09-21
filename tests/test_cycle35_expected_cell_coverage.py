"""Cycle #35 continuation (20260921T055921Z), section 6 -- newly discovered.

R35-30 read the delivered database and found expected_cell.coverage_state
saying EXPECTED_NOT_YET_COVERED for all 36,582 rows, while the coverage
artifact written beside it reports 13,474 cells covered by a candidate
observation.

Neither number was wrong. `add_expected_cell` writes the placeholder when
the cell is created -- correctly, since no evidence has been ingested at
that moment -- and nothing revisited it, while the real coverage was
computed later into a JSON file. The database is the thing that ships, so
the database is what has to say what it covers.

These tests pin the rule rather than the totals, and the one that matters
most is the middle state: an unpromoted candidate observation is neither
"covered" nor "no evidence acquired", and collapsing it either way loses a
real distinction.
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle35.coaching_release import (  # noqa: E402
    COVERAGE_CANDIDATE,
    COVERAGE_CONFIRMED,
    COVERAGE_NONE,
    COVERAGE_UNSETTLED,
    LAYER_CANDIDATE,
    LAYER_OFFICIAL,
    apply_migrations,
    settle_expected_cell_coverage,
    stated_season,
)

CORE = ("head_coach", "offensive_coordinator", "defensive_coordinator")


def titles(text: str) -> list[str]:
    """A trivial mapper, so these tests are about coverage, not taxonomy."""

    return [text] if text in CORE else []


def fresh() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)
    return conn


def a_cell(conn: sqlite3.Connection, program: str, season: int, role: str) -> None:
    conn.execute(
        "INSERT INTO expected_cell (expected_cell_id, program_id, season, "
        "role_family, era_band, coverage_state) VALUES (?,?,?,?,?,?)",
        (f"cell:{program}:{season}:{role}", program, season, role, "ERA", COVERAGE_UNSETTLED),
    )


def an_observation(
    conn: sqlite3.Connection, program: str, season: str, title: str, ident: str
) -> None:
    conn.execute(
        "INSERT INTO source_observation (observation_id, source_file_id, locator, "
        "parser_identity, observed_person, observed_title, observed_program, "
        "observed_season, evidence_layer) VALUES (?,?,?,?,?,?,?,?,?)",
        (ident, "sf", "loc", "p", "Someone", title, program, season, LAYER_CANDIDATE),
    )


def a_confirmed_assertion(
    conn: sqlite3.Connection, program: str, season: str, role: str, ident: str
) -> None:
    conn.execute(
        "INSERT INTO canonical_person (person_id, canonical_name, identity_basis) "
        "VALUES (?,?,?)",
        (f"p:{ident}", "Someone", "TEST"),
    )
    conn.execute(
        "INSERT INTO employment_episode (episode_id, person_id, program_id, season, "
        "date_precision, evidence_layer) VALUES (?,?,?,?,?,?)",
        (f"e:{ident}", f"p:{ident}", program, season, "SEASON", LAYER_OFFICIAL),
    )
    conn.execute(
        "INSERT INTO formal_role_assertion (assertion_id, episode_id, role_family, "
        "exact_title_text, qualifiers, principal_role_blocked, evidence_layer) "
        "VALUES (?,?,?,?,?,?,?)",
        (f"a:{ident}", f"e:{ident}", role, role, "", 0, LAYER_OFFICIAL),
    )


def settle(conn: sqlite3.Connection) -> dict[str, int]:
    return settle_expected_cell_coverage(conn, role_families=titles, core_roles=CORE)


def state_of(conn: sqlite3.Connection, cell_id: str) -> str:
    return conn.execute(
        "SELECT coverage_state FROM expected_cell WHERE expected_cell_id = ?", (cell_id,)
    ).fetchone()[0]


class StatedSeasonTests(unittest.TestCase):
    def test_current_is_not_a_season(self) -> None:
        self.assertIsNone(stated_season("CURRENT"))

    def test_a_four_digit_year_is(self) -> None:
        self.assertEqual(stated_season("2019"), 2019)

    def test_nothing_else_is(self) -> None:
        for value in (None, "", "19", "20199", "SEASON_UNSPECIFIED", "20a9"):
            with self.subTest(value=value):
                self.assertIsNone(stated_season(value))


class CoverageRuleTests(unittest.TestCase):
    def test_a_cell_with_no_evidence_reads_no_evidence(self) -> None:
        conn = fresh()
        a_cell(conn, "texas_am", 2019, "head_coach")
        settle(conn)
        self.assertEqual(state_of(conn, "cell:texas_am:2019:head_coach"), COVERAGE_NONE)

    def test_a_candidate_observation_covers_at_the_candidate_layer_only(self) -> None:
        """The state that must keep existing. Acquired evidence, unpromoted."""

        conn = fresh()
        a_cell(conn, "texas_am", 2019, "head_coach")
        an_observation(conn, "texas_am", "2019", "head_coach", "o1")
        settle(conn)
        self.assertEqual(
            state_of(conn, "cell:texas_am:2019:head_coach"), COVERAGE_CANDIDATE
        )

    def test_a_confirmed_assertion_covers_at_the_confirmed_layer(self) -> None:
        conn = fresh()
        a_cell(conn, "texas_am", 2019, "head_coach")
        a_confirmed_assertion(conn, "texas_am", "2019", "head_coach", "x")
        settle(conn)
        self.assertEqual(
            state_of(conn, "cell:texas_am:2019:head_coach"), COVERAGE_CONFIRMED
        )

    def test_confirmed_outranks_candidate_for_the_same_cell(self) -> None:
        conn = fresh()
        a_cell(conn, "texas_am", 2019, "head_coach")
        an_observation(conn, "texas_am", "2019", "head_coach", "o1")
        a_confirmed_assertion(conn, "texas_am", "2019", "head_coach", "x")
        settle(conn)
        self.assertEqual(
            state_of(conn, "cell:texas_am:2019:head_coach"), COVERAGE_CONFIRMED
        )


class SeasonDisciplineTests(unittest.TestCase):
    """The MF35-05 line: an episode with no stated season is in no year."""

    def test_a_confirmed_assertion_without_a_season_covers_nothing(self) -> None:
        conn = fresh()
        a_cell(conn, "texas_am", 2019, "head_coach")
        a_confirmed_assertion(conn, "texas_am", "CURRENT", "head_coach", "x")
        settle(conn)
        self.assertEqual(state_of(conn, "cell:texas_am:2019:head_coach"), COVERAGE_NONE)

    def test_an_observation_without_a_season_covers_nothing(self) -> None:
        conn = fresh()
        a_cell(conn, "texas_am", 2019, "head_coach")
        an_observation(conn, "texas_am", "CURRENT", "head_coach", "o1")
        settle(conn)
        self.assertEqual(state_of(conn, "cell:texas_am:2019:head_coach"), COVERAGE_NONE)

    def test_evidence_does_not_leak_across_seasons(self) -> None:
        conn = fresh()
        a_cell(conn, "texas_am", 2019, "head_coach")
        a_cell(conn, "texas_am", 2020, "head_coach")
        an_observation(conn, "texas_am", "2019", "head_coach", "o1")
        settle(conn)
        self.assertEqual(
            state_of(conn, "cell:texas_am:2019:head_coach"), COVERAGE_CANDIDATE
        )
        self.assertEqual(state_of(conn, "cell:texas_am:2020:head_coach"), COVERAGE_NONE)

    def test_evidence_does_not_leak_across_programs_or_roles(self) -> None:
        conn = fresh()
        a_cell(conn, "texas_am", 2019, "head_coach")
        a_cell(conn, "lsu", 2019, "head_coach")
        a_cell(conn, "texas_am", 2019, "offensive_coordinator")
        an_observation(conn, "texas_am", "2019", "head_coach", "o1")
        settle(conn)
        self.assertEqual(state_of(conn, "cell:lsu:2019:head_coach"), COVERAGE_NONE)
        self.assertEqual(
            state_of(conn, "cell:texas_am:2019:offensive_coordinator"), COVERAGE_NONE
        )

    def test_a_title_outside_the_core_families_covers_nothing(self) -> None:
        conn = fresh()
        a_cell(conn, "texas_am", 2019, "head_coach")
        an_observation(conn, "texas_am", "2019", "Director of Player Personnel", "o1")
        settle(conn)
        self.assertEqual(state_of(conn, "cell:texas_am:2019:head_coach"), COVERAGE_NONE)


class SettlementTests(unittest.TestCase):
    def test_no_cell_is_left_unsettled(self) -> None:
        """A shipped release must not still carry the creation placeholder."""

        conn = fresh()
        for season in (2019, 2020, 2021):
            a_cell(conn, "texas_am", season, "head_coach")
        an_observation(conn, "texas_am", "2020", "head_coach", "o1")
        settle(conn)
        remaining = conn.execute(
            "SELECT COUNT(*) FROM expected_cell WHERE coverage_state = ?",
            (COVERAGE_UNSETTLED,),
        ).fetchone()[0]
        self.assertEqual(remaining, 0)

    def test_the_returned_counts_match_the_column(self) -> None:
        conn = fresh()
        for season in (2019, 2020, 2021):
            a_cell(conn, "texas_am", season, "head_coach")
        an_observation(conn, "texas_am", "2020", "head_coach", "o1")
        a_confirmed_assertion(conn, "texas_am", "2021", "head_coach", "x")
        counts = settle(conn)
        from_column = {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT coverage_state, COUNT(*) FROM expected_cell GROUP BY 1"
            )
        }
        self.assertEqual({k: v for k, v in counts.items() if v}, from_column)

    def test_settling_twice_gives_the_same_answer(self) -> None:
        conn = fresh()
        a_cell(conn, "texas_am", 2019, "head_coach")
        an_observation(conn, "texas_am", "2019", "head_coach", "o1")
        self.assertEqual(settle(conn), settle(conn))


if __name__ == "__main__":
    unittest.main()
