"""R35-08 (Cycle #35 manager follow-up, 20260920T224700Z): the national
neutral/unknown-site cohort, built through actual consumer inputs.

`build_national_cohort()` was first written calling
`aggie_analytics.cycle33.neutral.travel_context(..., venue_confirmed=False,
...)` for every game -- direct interactive testing proved that call
pattern always raises `NeutralVenueError`, regardless of every other
parameter, because `venue_confirmed=False` is a precondition failure, not
a "give me the unconfirmed-venue result" request. It was rewritten to use
the narrow, precondition-free `ordinary_home_advantage(neutral_site=...)`
instead. These tests exercise the rewritten tool end to end against
temporary JSONL fixtures, so a regression back to the old, always-raising
call pattern would show up as zero rows rather than as a passing test
that never actually classified anything.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_08_national_neutral_site_cohort import (  # noqa: E402
    GAME_SOURCES,
    build_national_cohort,
    load_venue_enrichment,
    resolve_neutral_state,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


class ResolveNeutralStateTests(unittest.TestCase):
    def test_strict_true(self) -> None:
        self.assertEqual(resolve_neutral_state(True), (True, "TRUE"))

    def test_strict_false(self) -> None:
        self.assertEqual(resolve_neutral_state(False), (False, "FALSE"))

    def test_missing_value_is_unknown_not_false(self) -> None:
        """Missing neutral-site evidence must stay unknown, never be
        coerced into an ordinary-home-game default."""
        self.assertEqual(resolve_neutral_state(None), (None, "UNKNOWN"))

    def test_non_bool_value_is_unknown_not_truthy_coerced(self) -> None:
        self.assertEqual(resolve_neutral_state("true"), (None, "UNKNOWN"))
        self.assertEqual(resolve_neutral_state(1), (None, "UNKNOWN"))


class BuildNationalCohortTests(unittest.TestCase):
    """Proves the tool actually classifies rows -- the exact property the
    old travel_context()-based design failed at silently (every row would
    have landed in an exception handler instead of the output)."""

    def _build(self, rows: list[dict], venue_rows=None):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            games_path = tmp_path / "games.jsonl"
            _write_jsonl(games_path, rows)
            empty_path = tmp_path / "empty.jsonl"
            _write_jsonl(empty_path, [])
            missing_venue = tmp_path / "no_such_venue.parquet"
            return build_national_cohort(
                game_sources=(games_path, empty_path),
                venue_enrichment_parquet=missing_venue,
            )

    def test_ordinary_home_game_gets_no_forced_advantage_value(self) -> None:
        result = self._build(
            [{"id": 1, "homeId": 10, "awayId": 20, "season": 2020, "neutralSite": False}]
        )
        self.assertEqual(result["row_count"], 1)
        row = result["rows"][0]
        self.assertEqual(row["neutral_state"], "FALSE")
        self.assertIsNone(row["ordinary_home_advantage"])

    def test_confirmed_neutral_game_gets_zero_advantage(self) -> None:
        result = self._build(
            [{"id": 2, "homeId": 10, "awayId": 20, "season": 2020, "neutralSite": True}]
        )
        row = result["rows"][0]
        self.assertEqual(row["neutral_state"], "TRUE")
        self.assertEqual(row["ordinary_home_advantage"], 0.0)

    def test_missing_neutral_evidence_is_kept_as_unknown_row(self) -> None:
        """The manager's exact requirement: missing evidence must stay
        visible as unknown, not silently dropped or defaulted."""
        result = self._build(
            [{"id": 3, "homeId": 10, "awayId": 20, "season": 2020}]
        )
        self.assertEqual(result["row_count"], 1)
        row = result["rows"][0]
        self.assertEqual(row["neutral_state"], "UNKNOWN")
        self.assertIsNone(row["neutral_site"])
        self.assertIsNone(row["ordinary_home_advantage"])

    def test_row_with_no_game_id_is_skipped_and_counted(self) -> None:
        result = self._build(
            [{"homeId": 10, "awayId": 20, "season": 2020, "neutralSite": False}]
        )
        self.assertEqual(result["row_count"], 0)
        self.assertEqual(result["state_counts"]["SKIPPED_NO_GAME_ID"], 1)

    def test_row_missing_a_participant_id_is_skipped_and_counted(self) -> None:
        result = self._build(
            [{"id": 4, "homeId": 10, "season": 2020, "neutralSite": False}]
        )
        self.assertEqual(result["row_count"], 0)
        self.assertEqual(result["state_counts"]["SKIPPED_MISSING_PARTICIPANT_ID"], 1)

    def test_duplicate_game_id_across_sources_is_deduped_and_counted(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            first = tmp_path / "first.jsonl"
            second = tmp_path / "second.jsonl"
            _write_jsonl(
                first,
                [{"id": 5, "homeId": 10, "awayId": 20, "season": 2020, "neutralSite": False}],
            )
            _write_jsonl(
                second,
                [{"id": 5, "homeId": 10, "awayId": 20, "season": 2020, "neutralSite": True}],
            )
            result = build_national_cohort(
                game_sources=(first, second),
                venue_enrichment_parquet=tmp_path / "no_such_venue.parquet",
            )
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(result["state_counts"]["SKIPPED_DUPLICATE_GAME_ID"], 1)
        # The first source's copy wins; the second source's copy is not
        # silently substituted in.
        self.assertEqual(result["rows"][0]["neutral_state"], "FALSE")

    def test_travel_distance_is_always_none_with_a_disclosed_reason(self) -> None:
        result = self._build(
            [{"id": 6, "homeId": 10, "awayId": 20, "season": 2020, "neutralSite": False}]
        )
        row = result["rows"][0]
        self.assertIsNone(row["home_travel_distance"])
        self.assertIsNone(row["away_travel_distance"])
        self.assertEqual(
            row["travel_distance_unavailable_reason"], "NO_LOCAL_STADIUM_COORDINATES"
        )

    def test_no_row_is_ever_marked_pit_admitted(self) -> None:
        result = self._build(
            [{"id": 7, "homeId": 10, "awayId": 20, "season": 2020, "neutralSite": True}]
        )
        self.assertFalse(result["pit_admitted"])
        self.assertFalse(result["rows"][0]["pit_admitted"])


class VenueEnrichmentJoinTests(unittest.TestCase):
    def test_missing_parquet_reports_an_honest_not_mounted_state(self) -> None:
        by_game, stats = load_venue_enrichment(Path("does/not/exist.parquet"))
        self.assertEqual(by_game, {})
        self.assertEqual(stats["state"], "VENUE_ENRICHMENT_NOT_MOUNTED")

    def test_unmatched_game_reports_not_available_not_a_fabricated_venue(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            games_path = tmp_path / "games.jsonl"
            _write_jsonl(
                games_path,
                [{"id": 8, "homeId": 10, "awayId": 20, "season": 2020, "neutralSite": False}],
            )
            empty_path = tmp_path / "empty.jsonl"
            _write_jsonl(empty_path, [])
            result = build_national_cohort(
                game_sources=(games_path, empty_path),
                venue_enrichment_parquet=tmp_path / "no_such_venue.parquet",
            )
        row = result["rows"][0]
        self.assertIsNone(row["venue_enrichment"])
        self.assertEqual(row["venue_enrichment_authority"], "NOT_AVAILABLE")


class RealDataSmokeTests(unittest.TestCase):
    """Runs the real tool against the real declared game sources, the
    same reproduction discipline used elsewhere this session: a unit test
    is not trusted here unless it also passed against production data at
    least once."""

    def test_real_national_cohort_classifies_a_large_fraction_of_games(self) -> None:
        if not any(path.is_file() for path in GAME_SOURCES):
            self.skipTest("mounted national game sources not present")
        result = build_national_cohort()
        self.assertGreater(result["row_count"], 40000)
        self.assertEqual(min(result["seasons_covered"]), 1963)
        self.assertGreaterEqual(max(result["seasons_covered"]), 2020)
        total_classified = sum(result["neutral_state_counts"].values())
        self.assertEqual(total_classified, result["row_count"])
        # Every TRUE row must carry the zero-advantage value; nothing else
        # is fabricated as a nonzero magnitude by this tool.
        for row in result["rows"]:
            if row["neutral_state"] == "TRUE":
                self.assertEqual(row["ordinary_home_advantage"], 0.0)
            else:
                self.assertIsNone(row["ordinary_home_advantage"])
            self.assertIsNone(row["home_travel_distance"])
            self.assertIsNone(row["away_travel_distance"])
            self.assertFalse(row["pit_admitted"])


if __name__ == "__main__":
    unittest.main()
