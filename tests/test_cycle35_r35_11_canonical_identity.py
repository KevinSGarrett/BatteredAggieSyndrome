"""R35-11 (Cycle #35 manager follow-up, 20260920T224700Z): "finish permitted
availability processing through actual status statement, canonical
player/roster, contest and vintage. Name hits, roster membership and no
report are not injury/health facts."

`resolve_canonical_player`, `resolve_canonical_contest` and
`stage_vintage_ordinal` join a parsed availability assertion (name +
jersey + a free-text contest label, no source athlete_id) to real local
roster and game evidence -- conservatively: an ambiguous or conflicting
match is quarantined, never guessed, because a wrong player identity
attached to a real injury-report row is worse than an honestly unresolved
one.

`test_jersey_number_zero_is_not_discarded_as_falsy` reproduces a real bug
found while calibrating against the real Alabama 2026 roster slice: an
earlier `_normalize_jersey` used `value or ""`, which treats jersey 0 (a
real, increasingly common number) as absent, silently sending every
jersey-#0 player through the wrong resolution path.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle35.availability import (  # noqa: E402
    QUARANTINE_AMBIGUOUS_CONTEST_MATCH,
    QUARANTINE_AMBIGUOUS_ROSTER_MATCH,
    QUARANTINE_CONTEST_SEASON_CONTRADICTS_LABEL,
    QUARANTINE_GIVEN_NAME_CONTRADICTS,
    QUARANTINE_JERSEY_NAME_CONFLICT,
    QUARANTINE_ROSTER_ROW_HAS_NO_IDENTIFIER,
    RESOLVED_CONTEST_MATCH,
    RESOLVED_JERSEY_AND_NAME_MATCH,
    RESOLVED_JERSEY_COLLISION_BROKEN_BY_NAME,
    ROSTER_NOT_LOCALLY_AVAILABLE,
    UNRESOLVED_CONTEST_LABEL_DATE_INVALID,
    UNRESOLVED_CONTEST_LABEL_UNPARSEABLE,
    UNRESOLVED_NAME_ONLY_NOT_CORROBORATED,
    UNRESOLVED_NO_CONTEST_MATCH,
    UNRESOLVED_NO_ROSTER_MATCH,
    enrich_assertion_identities,
    parse_contest_label,
    resolve_canonical_contest,
    resolve_canonical_player,
    season_of_calendar_date,
    stage_vintage_ordinal,
)


def _roster_index(rows):
    """Roster fixtures carry a source id, as the production builder now
    does: a bare provider integer is not a canonical player identity."""

    index: dict[str, list[dict]] = {}
    for row in rows:
        row.setdefault("source_id", "SRC-002")
        index.setdefault(row["team"], []).append(row)
    return index


class ResolveCanonicalPlayerTests(unittest.TestCase):
    def test_program_absent_from_roster_index_is_not_locally_available(self) -> None:
        res = resolve_canonical_player(
            program="Kentucky", player_name="Some Player", jersey="#4",
            roster_index=_roster_index([{"team": "Alabama", "id": "1", "last_name": "X", "jersey": 4}]),
        )
        self.assertIsNone(res["canonical_player_id"])
        self.assertEqual(res["identity_state"], ROSTER_NOT_LOCALLY_AVAILABLE)

    def test_jersey_and_name_both_agree_resolves(self) -> None:
        index = _roster_index([
            {"team": "Alabama", "id": "504059", "last_name": "Williams", "jersey": 45},
        ])
        res = resolve_canonical_player(
            program="Alabama", player_name="Jay Williams", jersey="#45", roster_index=index
        )
        self.assertEqual(res["canonical_player_id"], "SRC-002:PLAYER:504059")
        self.assertEqual(res["identity_state"], RESOLVED_JERSEY_AND_NAME_MATCH)

    def test_jersey_matches_but_name_conflicts_is_quarantined_not_guessed(self) -> None:
        index = _roster_index([
            {"team": "Alabama", "id": "504059", "last_name": "Williams", "jersey": 45},
        ])
        res = resolve_canonical_player(
            program="Alabama", player_name="Somebody Else", jersey="#45", roster_index=index
        )
        self.assertIsNone(res["canonical_player_id"])
        self.assertEqual(res["identity_state"], QUARANTINE_JERSEY_NAME_CONFLICT)

    def test_jersey_number_zero_is_not_discarded_as_falsy(self) -> None:
        """Regression: `value or ""` in an earlier version treated the real
        jersey number 0 as absent, so a #0 player could never match by
        jersey at all and would silently fall through to a weaker
        resolution path (or worse, collide unnoticed)."""
        index = _roster_index([
            {"team": "Alabama", "id": "5141426", "last_name": "Dear", "jersey": 0},
        ])
        res = resolve_canonical_player(
            program="Alabama", player_name="AK Dear", jersey="#0", roster_index=index
        )
        self.assertEqual(res["canonical_player_id"], "SRC-002:PLAYER:5141426")
        self.assertEqual(res["identity_state"], RESOLVED_JERSEY_AND_NAME_MATCH)

    def test_shared_jersey_with_distinct_surnames_is_broken_by_name_evidence(self) -> None:
        """The real Alabama 2026 roster has two players wearing #0, with
        DIFFERENT surnames. An earlier version quarantined this before the
        name evidence was consulted, which the manager's closeout review
        showed was unsupported: calling such an identity irresolvable
        ignores evidence that does separate the candidates."""
        index = _roster_index([
            {"team": "Alabama", "id": "5141426", "last_name": "Dear", "jersey": 0},
            {"team": "Alabama", "id": "4870970", "last_name": "Pierre", "jersey": 0},
        ])
        res = resolve_canonical_player(
            program="Alabama", player_name="AK Dear", jersey="#0", roster_index=index
        )
        self.assertEqual(res["canonical_player_id"], "SRC-002:PLAYER:5141426")
        self.assertEqual(
            res["identity_state"], RESOLVED_JERSEY_COLLISION_BROKEN_BY_NAME
        )

    def test_shared_jersey_with_the_same_surname_stays_quarantined(self) -> None:
        """When the available evidence genuinely does NOT separate the
        candidates, the row must still be retained as unresolved."""
        index = _roster_index([
            {"team": "Alabama", "id": "1", "last_name": "Smith", "jersey": 0},
            {"team": "Alabama", "id": "2", "last_name": "Smith", "jersey": 0},
        ])
        res = resolve_canonical_player(
            program="Alabama", player_name="Smith", jersey="#0", roster_index=index
        )
        self.assertIsNone(res["canonical_player_id"])
        self.assertEqual(res["identity_state"], QUARANTINE_AMBIGUOUS_ROSTER_MATCH)

    def test_name_only_match_is_not_promoted_to_a_canonical_id(self) -> None:
        """A surname alone does not identify a person on a roster. The
        candidate is retained for audit but no canonical id is assigned."""
        index = _roster_index([
            {"team": "Alabama", "id": "5141426", "last_name": "Dear", "jersey": 12},
        ])
        res = resolve_canonical_player(
            program="Alabama", player_name="AK Dear", jersey="", roster_index=index
        )
        self.assertIsNone(res["canonical_player_id"])
        self.assertEqual(res["identity_state"], UNRESOLVED_NAME_ONLY_NOT_CORROBORATED)
        self.assertEqual(
            res["identity_evidence"]["name_only_candidate_ids"],
            ["SRC-002:PLAYER:5141426"],
        )

    def test_no_match_at_all_is_unresolved_not_fabricated(self) -> None:
        index = _roster_index([
            {"team": "Alabama", "id": "1", "last_name": "Someone", "jersey": 99},
        ])
        res = resolve_canonical_player(
            program="Alabama", player_name="Nobody Here", jersey="#7", roster_index=index
        )
        self.assertIsNone(res["canonical_player_id"])
        self.assertEqual(res["identity_state"], UNRESOLVED_NO_ROSTER_MATCH)

    def test_multi_word_last_name_with_suffix_still_matches(self) -> None:
        """Regression: CFBD folds a generational suffix into last_name
        itself ("Kinsler IV", "Lincoln Jr."). An earlier version checked
        the full multi-word string for set membership against single-word
        name tokens, which can never match, silently quarantining every
        real player whose roster last name carries a suffix."""
        index = _roster_index([
            {"team": "Ole Miss", "id": "4870782", "last_name": "Kinsler IV", "jersey": 61},
        ])
        res = resolve_canonical_player(
            program="Ole Miss", player_name="Tommy Kinsler IV", jersey="#61", roster_index=index
        )
        self.assertEqual(res["canonical_player_id"], "SRC-002:PLAYER:4870782")
        self.assertEqual(res["identity_state"], RESOLVED_JERSEY_AND_NAME_MATCH)

    def test_resolution_never_touches_status_fields(self) -> None:
        """Roster membership is not an injury/health fact -- this function
        must not have any status/presence keys in its return shape at
        all."""
        index = _roster_index([{"team": "Alabama", "id": "1", "last_name": "X", "jersey": 4}])
        res = resolve_canonical_player(
            program="Alabama", player_name="X Y", jersey="#4", roster_index=index
        )
        self.assertNotIn("status", res)
        self.assertNotIn("presence", res)


class ManagerCloseoutCounterexampleTests(unittest.TestCase):
    """The four identity defects the manager reproduced at head 1cce008b
    (CLOSEOUT_PROBES.json, review 20260921T025300Z), each paired with the
    positive control that must keep working after the repair."""

    ALICE = {
        "team": "Example", "id": "PLAYER_ALICE", "source_id": "SRC-002",
        "first_name": "Alice", "last_name": "Smith", "jersey": 12,
    }

    def test_positive_control_matching_given_name_still_resolves(self) -> None:
        res = resolve_canonical_player(
            program="Example", player_name="Alice Smith", jersey="12",
            roster_index=_roster_index([dict(self.ALICE)]),
        )
        self.assertEqual(res["canonical_player_id"], "SRC-002:PLAYER:PLAYER_ALICE")
        self.assertEqual(res["identity_state"], RESOLVED_JERSEY_AND_NAME_MATCH)

    def test_contradictory_given_name_does_not_resolve(self) -> None:
        """"Bob Smith" resolved to roster person "Alice Smith" because the
        matcher checked surname tokens only."""
        res = resolve_canonical_player(
            program="Example", player_name="Bob Smith", jersey="12",
            roster_index=_roster_index([dict(self.ALICE)]),
        )
        self.assertIsNone(res["canonical_player_id"])
        self.assertEqual(res["identity_state"], QUARANTINE_GIVEN_NAME_CONTRADICTS)

    def test_a_given_initial_is_compatible_not_contradictory(self) -> None:
        """Rejecting contradictions must not become blanket fuzziness in
        the other direction: an initial is real, supporting evidence."""
        res = resolve_canonical_player(
            program="Example", player_name="A. Smith", jersey="12",
            roster_index=_roster_index([dict(self.ALICE)]),
        )
        self.assertEqual(res["canonical_player_id"], "SRC-002:PLAYER:PLAYER_ALICE")
        self.assertEqual(
            res["identity_evidence"]["given_name_evidence"], "COMPATIBLE_INITIAL"
        )

    def test_missing_roster_id_never_becomes_the_string_none(self) -> None:
        """A matching roster row with a missing id was returned as
        canonical_player_id="None" with a RESOLVED state."""
        res = resolve_canonical_player(
            program="Example", player_name="Alice Smith", jersey="12",
            roster_index=_roster_index([
                {"team": "Example", "id": None, "last_name": "Smith", "jersey": 12}
            ]),
        )
        self.assertIsNone(res["canonical_player_id"])
        self.assertNotEqual(res["canonical_player_id"], "None")
        self.assertEqual(
            res["identity_state"], QUARANTINE_ROSTER_ROW_HAS_NO_IDENTIFIER
        )

    def test_other_non_identifier_tokens_are_also_rejected(self) -> None:
        for bogus in ("", "   ", "null", "NaN", "N/A", "none"):
            with self.subTest(bogus=bogus):
                res = resolve_canonical_player(
                    program="Example", player_name="Alice Smith", jersey="12",
                    roster_index=_roster_index([
                        {"team": "Example", "id": bogus, "last_name": "Smith", "jersey": 12}
                    ]),
                )
                self.assertIsNone(res["canonical_player_id"])
                self.assertEqual(
                    res["identity_state"], QUARANTINE_ROSTER_ROW_HAS_NO_IDENTIFIER
                )

    def test_jersey_collision_is_broken_by_full_identity_evidence(self) -> None:
        res = resolve_canonical_player(
            program="Example", player_name="Alice Smith", jersey="12",
            roster_index=_roster_index([
                dict(self.ALICE),
                {"team": "Example", "id": "PLAYER_JONES", "first_name": "Bo",
                 "last_name": "Jones", "jersey": 12},
            ]),
        )
        self.assertEqual(res["canonical_player_id"], "SRC-002:PLAYER:PLAYER_ALICE")
        self.assertEqual(
            res["identity_state"], RESOLVED_JERSEY_COLLISION_BROKEN_BY_NAME
        )

    def test_jersey_collision_with_contradictory_given_names_stays_unresolved(self) -> None:
        """Same surname, same jersey, both given names contradicting the
        published one: genuinely irresolvable, and retained as such."""
        res = resolve_canonical_player(
            program="Example", player_name="Carol Smith", jersey="12",
            roster_index=_roster_index([
                dict(self.ALICE),
                {"team": "Example", "id": "P2", "first_name": "Bob",
                 "last_name": "Smith", "jersey": 12},
            ]),
        )
        self.assertIsNone(res["canonical_player_id"])
        self.assertEqual(res["identity_state"], QUARANTINE_GIVEN_NAME_CONTRADICTS)

    def test_wrong_explicit_year_is_not_overridden_by_the_declared_season(self) -> None:
        """"9/20/25 vs Opponent" resolved to a 2026 contest because the
        parser matched the year and then discarded it."""
        games = {("example", "opponent", 2026, 9, 20): [{"canonical_game_id": "GAME_2026"}]}
        res = resolve_canonical_contest(
            program="Example", contest_label="9/20/25 vs Opponent", season=2026,
            games_index=games,
        )
        self.assertIsNone(res["canonical_contest_id"])
        self.assertEqual(
            res["contest_resolution_state"],
            QUARANTINE_CONTEST_SEASON_CONTRADICTS_LABEL,
        )
        self.assertEqual(res["contest_evidence"]["label_season"], 2025)
        self.assertEqual(res["contest_evidence"]["caller_declared_season"], 2026)

    def test_positive_control_correct_year_still_resolves(self) -> None:
        games = {("example", "opponent", 2026, 9, 20): [{"canonical_game_id": "GAME_2026"}]}
        res = resolve_canonical_contest(
            program="Example", contest_label="9/20/26 vs Opponent", season=2026,
            games_index=games,
        )
        self.assertEqual(res["canonical_contest_id"], "GAME_2026")
        self.assertEqual(res["contest_resolution_state"], RESOLVED_CONTEST_MATCH)


class ContestSeasonBoundaryTests(unittest.TestCase):
    def test_season_of_calendar_date_handles_the_postseason_crossover(self) -> None:
        self.assertEqual(season_of_calendar_date(2026, 9), 2026)
        self.assertEqual(season_of_calendar_date(2026, 12), 2026)
        # January and February belong to the PREVIOUS season's postseason.
        self.assertEqual(season_of_calendar_date(2027, 1), 2026)
        self.assertEqual(season_of_calendar_date(2027, 2), 2026)
        self.assertEqual(season_of_calendar_date(2027, 3), 2027)

    def test_a_january_bowl_date_resolves_to_the_prior_season(self) -> None:
        games = {("example", "opponent", 2027, 1, 10): [{"canonical_game_id": "BOWL"}]}
        res = resolve_canonical_contest(
            program="Example", contest_label="1/10/27 vs Opponent", season=2026,
            games_index=games,
        )
        self.assertEqual(res["canonical_contest_id"], "BOWL")

    def test_a_january_date_in_the_declared_season_year_contradicts(self) -> None:
        """1/10/26 is season 2025's postseason, not season 2026."""
        res = resolve_canonical_contest(
            program="Example", contest_label="1/10/26 vs Opponent", season=2026,
            games_index={("example", "opponent", 2026, 1, 10): [{"canonical_game_id": "X"}]},
        )
        self.assertEqual(
            res["contest_resolution_state"],
            QUARANTINE_CONTEST_SEASON_CONTRADICTS_LABEL,
        )

    def test_an_impossible_calendar_date_is_rejected(self) -> None:
        for label in ("2/30/26 vs Opponent", "13/01/26 vs Opponent", "9/31/26 vs Opponent"):
            with self.subTest(label=label):
                res = resolve_canonical_contest(
                    program="Example", contest_label=label, season=2026, games_index={},
                )
                self.assertIsNone(res["canonical_contest_id"])
                self.assertIn(
                    res["contest_resolution_state"],
                    {
                        UNRESOLVED_CONTEST_LABEL_DATE_INVALID,
                        UNRESOLVED_CONTEST_LABEL_UNPARSEABLE,
                    },
                )

    def test_a_repeated_opponent_in_one_season_is_disambiguated_by_date(self) -> None:
        """Regular-season meeting and a conference-championship rematch."""
        games = {
            ("example", "opponent", 2026, 9, 20): [{"canonical_game_id": "REGULAR"}],
            ("example", "opponent", 2026, 12, 6): [{"canonical_game_id": "TITLE"}],
        }
        first = resolve_canonical_contest(
            program="Example", contest_label="9/20/26 vs Opponent", season=2026,
            games_index=games,
        )
        second = resolve_canonical_contest(
            program="Example", contest_label="12/6/26 vs Opponent", season=2026,
            games_index=games,
        )
        self.assertEqual(first["canonical_contest_id"], "REGULAR")
        self.assertEqual(second["canonical_contest_id"], "TITLE")

    def test_a_true_duplicate_observation_of_one_game_is_not_ambiguous(self) -> None:
        """The same canonical game id listed twice is one contest, not two
        competing candidates."""
        games = {
            ("example", "opponent", 2026, 9, 20): [
                {"canonical_game_id": "SAME"},
                {"canonical_game_id": "SAME"},
            ]
        }
        res = resolve_canonical_contest(
            program="Example", contest_label="9/20/26 vs Opponent", season=2026,
            games_index=games,
        )
        self.assertEqual(res["canonical_contest_id"], "SAME")
        self.assertEqual(res["contest_resolution_state"], RESOLVED_CONTEST_MATCH)


class ParseContestLabelTests(unittest.TestCase):
    def test_at_qualifier(self) -> None:
        self.assertEqual(
            parse_contest_label("9/12/26 at Kentucky"),
            {
                "year": 2026,
                "month": 9,
                "day": 12,
                "date_valid": True,
                "label_season": 2026,
                "qualifier": "at",
                "opponent_raw": "Kentucky",
            },
        )

    def test_vs_dot_qualifier(self) -> None:
        parsed = parse_contest_label("9/19/26 vs. Georgia")
        self.assertEqual(parsed["qualifier"], "vs")
        self.assertEqual(parsed["opponent_raw"], "Georgia")

    def test_unparseable_label_returns_none(self) -> None:
        self.assertIsNone(parse_contest_label("TBD"))
        self.assertIsNone(parse_contest_label(""))


class ResolveCanonicalContestTests(unittest.TestCase):
    def _games_index(self, entries):
        index: dict[tuple, list[dict]] = {}
        for team, opponent, month, day, game_id in entries:
            index.setdefault((team, opponent, 2026, month, day), []).append(
                {"canonical_game_id": game_id}
            )
        return index

    def test_real_alabama_kentucky_shape_resolves(self) -> None:
        index = self._games_index(
            [("alabama", "kentucky", 9, 12, "SRC-002:GAME:401856674")]
        )
        res = resolve_canonical_contest(
            program="Alabama", contest_label="9/12/26 at Kentucky", season=2026,
            games_index=index,
        )
        self.assertEqual(res["canonical_contest_id"], "SRC-002:GAME:401856674")
        self.assertEqual(res["contest_resolution_state"], RESOLVED_CONTEST_MATCH)

    def test_unparseable_label_is_its_own_state(self) -> None:
        res = resolve_canonical_contest(
            program="Alabama", contest_label="TBD", season=2026, games_index={}
        )
        self.assertEqual(
            res["contest_resolution_state"], UNRESOLVED_CONTEST_LABEL_UNPARSEABLE
        )

    def test_no_local_game_is_unresolved_not_fabricated(self) -> None:
        res = resolve_canonical_contest(
            program="Alabama", contest_label="9/12/26 at Kentucky", season=2026,
            games_index={},
        )
        self.assertEqual(res["contest_resolution_state"], UNRESOLVED_NO_CONTEST_MATCH)
        self.assertIsNone(res["canonical_contest_id"])

    def test_ambiguous_local_games_are_quarantined(self) -> None:
        index = self._games_index([
            ("alabama", "kentucky", 9, 12, "SRC-002:GAME:1"),
            ("alabama", "kentucky", 9, 12, "SRC-002:GAME:2"),
        ])
        res = resolve_canonical_contest(
            program="Alabama", contest_label="9/12/26 at Kentucky", season=2026,
            games_index=index,
        )
        self.assertEqual(
            res["contest_resolution_state"], QUARANTINE_AMBIGUOUS_CONTEST_MATCH
        )


class StageVintageOrdinalTests(unittest.TestCase):
    def test_ordinal_is_positional_not_temporal(self) -> None:
        self.assertEqual(stage_vintage_ordinal("initial_status"), 0)
        self.assertEqual(stage_vintage_ordinal("update_1_status"), 1)
        self.assertEqual(stage_vintage_ordinal("update_2_status"), 2)
        self.assertEqual(stage_vintage_ordinal("game_day_status"), 3)

    def test_unknown_stage_is_none_not_fabricated(self) -> None:
        self.assertIsNone(stage_vintage_ordinal("not_a_real_stage"))


class EnrichAssertionIdentitiesTests(unittest.TestCase):
    def test_enrichment_adds_fields_without_mutating_the_original(self) -> None:
        assertion = {
            "program": "Alabama",
            "contest_label": "9/12/26 at Kentucky",
            "player_name": "Jay Williams",
            "jersey": "#45",
            "stage": "update_1_status",
            "status": "QUESTIONABLE",
            "presence": "PUBLISHED_VALUE",
        }
        roster_index = _roster_index([
            {"team": "Alabama", "id": "504059", "last_name": "Williams", "jersey": 45},
        ])
        games_index = {
            ("alabama", "kentucky", 2026, 9, 12): [
                {"canonical_game_id": "SRC-002:GAME:401856674"}
            ],
        }
        out = enrich_assertion_identities(
            assertion,
            program_id_by_name={"Alabama": "SRC-002:TEAM:333"},
            roster_index=roster_index,
            games_index=games_index,
            season=2026,
        )
        self.assertNotIn("canonical_player_id", assertion)
        self.assertEqual(out["canonical_player_id"], "SRC-002:PLAYER:504059")
        self.assertEqual(out["canonical_program_id"], "SRC-002:TEAM:333")
        self.assertEqual(out["canonical_contest_id"], "SRC-002:GAME:401856674")
        self.assertEqual(out["stage_vintage_ordinal"], 1)
        # The availability statement itself must be untouched by enrichment.
        self.assertEqual(out["status"], "QUESTIONABLE")
        self.assertEqual(out["presence"], "PUBLISHED_VALUE")


if __name__ == "__main__":
    unittest.main()
