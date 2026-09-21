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
    QUARANTINE_JERSEY_NAME_CONFLICT,
    RESOLVED_CONTEST_MATCH,
    RESOLVED_JERSEY_AND_NAME_MATCH,
    RESOLVED_NAME_ONLY_MATCH,
    ROSTER_NOT_LOCALLY_AVAILABLE,
    UNRESOLVED_CONTEST_LABEL_UNPARSEABLE,
    UNRESOLVED_NO_CONTEST_MATCH,
    UNRESOLVED_NO_ROSTER_MATCH,
    enrich_assertion_identities,
    parse_contest_label,
    resolve_canonical_contest,
    resolve_canonical_player,
    stage_vintage_ordinal,
)


def _roster_index(rows):
    index: dict[str, list[dict]] = {}
    for row in rows:
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
        self.assertEqual(res["canonical_player_id"], "504059")
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
        self.assertEqual(res["canonical_player_id"], "5141426")
        self.assertEqual(res["identity_state"], RESOLVED_JERSEY_AND_NAME_MATCH)

    def test_two_real_players_sharing_jersey_zero_is_quarantined(self) -> None:
        """The real Alabama 2026 roster has two players wearing #0. A
        resolver that only checked jersey number would silently pick one;
        this must refuse instead."""
        index = _roster_index([
            {"team": "Alabama", "id": "5141426", "last_name": "Dear", "jersey": 0},
            {"team": "Alabama", "id": "4870970", "last_name": "Pierre", "jersey": 0},
        ])
        res = resolve_canonical_player(
            program="Alabama", player_name="AK Dear", jersey="#0", roster_index=index
        )
        self.assertIsNone(res["canonical_player_id"])
        self.assertEqual(res["identity_state"], QUARANTINE_AMBIGUOUS_ROSTER_MATCH)

    def test_name_only_match_when_jersey_absent_or_unmatched(self) -> None:
        index = _roster_index([
            {"team": "Alabama", "id": "5141426", "last_name": "Dear", "jersey": 12},
        ])
        res = resolve_canonical_player(
            program="Alabama", player_name="AK Dear", jersey="", roster_index=index
        )
        self.assertEqual(res["canonical_player_id"], "5141426")
        self.assertEqual(res["identity_state"], RESOLVED_NAME_ONLY_MATCH)

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
        self.assertEqual(res["canonical_player_id"], "4870782")
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


class ParseContestLabelTests(unittest.TestCase):
    def test_at_qualifier(self) -> None:
        self.assertEqual(
            parse_contest_label("9/12/26 at Kentucky"),
            {"month": 9, "day": 12, "qualifier": "at", "opponent_raw": "Kentucky"},
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
            index.setdefault((team, opponent, month, day), []).append(
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
            ("alabama", "kentucky", 9, 12): [{"canonical_game_id": "SRC-002:GAME:401856674"}],
        }
        out = enrich_assertion_identities(
            assertion,
            program_id_by_name={"Alabama": "SRC-002:TEAM:333"},
            roster_index=roster_index,
            games_index=games_index,
            season=2026,
        )
        self.assertNotIn("canonical_player_id", assertion)
        self.assertEqual(out["canonical_player_id"], "504059")
        self.assertEqual(out["canonical_program_id"], "SRC-002:TEAM:333")
        self.assertEqual(out["canonical_contest_id"], "SRC-002:GAME:401856674")
        self.assertEqual(out["stage_vintage_ordinal"], 1)
        # The availability statement itself must be untouched by enrichment.
        self.assertEqual(out["status"], "QUESTIONABLE")
        self.assertEqual(out["presence"], "PUBLISHED_VALUE")


if __name__ == "__main__":
    unittest.main()
