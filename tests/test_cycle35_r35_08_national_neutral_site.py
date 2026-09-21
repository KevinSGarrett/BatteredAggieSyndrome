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
                [{"id": 5, "homeId": 10, "awayId": 20, "season": 2020, "neutralSite": False}],
            )
            result = build_national_cohort(
                game_sources=(first, second),
                venue_enrichment_parquet=tmp_path / "no_such_venue.parquet",
            )
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(result["state_counts"]["DUPLICATE_OBSERVATIONS_RECONCILED"], 1)
        # Identical observations deduplicate, and BOTH provenance locators
        # are retained rather than one being silently dropped.
        row = result["rows"][0]
        self.assertEqual(row["reconciliation_state"], "DEDUPLICATED_IDENTICAL_OBSERVATIONS")
        self.assertEqual(row["observation_count"], 2)
        self.assertEqual(len(row["all_observation_locators"]), 2)
        self.assertEqual(row["neutral_state"], "FALSE")

    def test_absent_travel_evidence_is_named_precisely_not_generically(self) -> None:
        """A game whose source row carries no venueId is an ACQUISITION
        gap, and must say so rather than claiming no coordinates exist
        anywhere."""
        result = self._build(
            [{"id": 6, "homeId": 10, "awayId": 20, "season": 2020, "neutralSite": False}]
        )
        row = result["rows"][0]
        self.assertIsNone(row["home_travel_km"])
        self.assertIsNone(row["away_travel_km"])
        self.assertEqual(
            row["travel_unavailable_reason"], "GAME_VENUE_ID_ABSENT_IN_SOURCE"
        )
        self.assertIsNone(row["travel_reference_authority"])

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
            self.assertFalse(row["pit_admitted"])
            # Travel is computed only where a venue actually resolves; it
            # is never invented for a row with no venue evidence.
            reason = row["travel_unavailable_reason"]
            if reason is None:
                self.assertIsNotNone(row["home_travel_km"])
                self.assertIsNotNone(row["away_travel_km"])
                self.assertEqual(
                    row["travel_reference_authority"],
                    "CURRENT_VINTAGE_TEAM_HOME_VENUE_NOT_PIT",
                )
            elif reason.startswith("GAME_VENUE_ID"):
                # No game venue resolved, so neither leg can exist.
                self.assertIsNone(row["home_travel_km"])
                self.assertIsNone(row["away_travel_km"])
            else:
                # A participant's home venue is unknown: the leg that IS
                # supported is retained rather than discarded with it.
                self.assertEqual(reason, "PARTICIPANT_HOME_VENUE_COORDINATES_UNAVAILABLE")
                self.assertTrue(
                    row["home_travel_km"] is None or row["away_travel_km"] is None
                )


if __name__ == "__main__":
    unittest.main()


class CloseoutDuplicateReconciliationTests(unittest.TestCase):
    """Cycle #35 closeout review (20260921T025300Z), section 4: the cohort
    builder silently kept the first row for a repeated game id, so a
    synthetic conflicting neutral designation changed the admitted row and
    the home-advantage result when file order was reversed.

    "Repair duplicate reconciliation so identical observations can be
    deduplicated with provenance, conflicting observations remain visible,
    and documented source/vintage authority -- not input order --
    determines resolution."
    """

    BASE = {"id": 42, "homeId": 1, "awayId": 2, "season": 2026, "neutralSite": True}

    def _run(self, first_rows, second_rows, first_name="a.jsonl", second_name="b.jsonl"):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / first_name, root / second_name
            _write_jsonl(a, first_rows)
            _write_jsonl(b, second_rows)
            missing = root / "absent"
            return build_national_cohort((a, b), missing, missing, root / "no_teams")

    def test_conflicting_neutral_designation_is_order_independent(self) -> None:
        conflicting = dict(self.BASE, neutralSite=False)
        forward = self._run([self.BASE], [conflicting])
        reverse = self._run([conflicting], [self.BASE])
        for result in (forward, reverse):
            row = result["rows"][0]
            self.assertEqual(row["neutral_state"], "UNKNOWN")
            self.assertIsNone(row["ordinary_home_advantage"])
            self.assertEqual(
                row["reconciliation_state"], "CONFLICT_UNRESOLVED_NO_AUTHORITY_BASIS"
            )
        self.assertEqual(
            forward["rows"][0]["neutral_state"], reverse["rows"][0]["neutral_state"]
        )
        self.assertEqual(
            forward["rows"][0]["ordinary_home_advantage"],
            reverse["rows"][0]["ordinary_home_advantage"],
        )

    def test_a_conflict_stays_visible_with_every_competing_observation(self) -> None:
        result = self._run([self.BASE], [dict(self.BASE, neutralSite=False)])
        self.assertEqual(result["unresolved_conflict_count"], 1)
        conflict = result["unresolved_conflicts"][0]
        self.assertEqual(len(conflict["competing_observations"]), 2)
        self.assertEqual(
            {o["neutral_site_raw"] for o in conflict["competing_observations"]},
            {True, False},
        )
        for observation in conflict["competing_observations"]:
            self.assertTrue(observation["provenance"]["locator"])
            self.assertIn("source_sha256", observation["provenance"])

    def test_identical_observations_deduplicate_and_keep_all_provenance(self) -> None:
        result = self._run([self.BASE], [dict(self.BASE)])
        row = result["rows"][0]
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(row["reconciliation_state"], "DEDUPLICATED_IDENTICAL_OBSERVATIONS")
        self.assertEqual(row["neutral_state"], "TRUE")
        self.assertEqual(sorted(row["all_observation_locators"]),
                         ["a.jsonl:line:1", "b.jsonl:line:1"])

    def test_declared_vintage_resolves_a_conflict_regardless_of_order(self) -> None:
        """A conflict between two DECLARED sources is settled by the newer
        declared acquisition vintage, not by which file was read first."""
        older = "CFBD_GAMES_1963_2012.jsonl"   # declared 2026-09-09T18:07:41Z
        newer = "CFBD_GAMES_TRANCHE.jsonl"     # declared 2026-09-09T18:08:43Z
        forward = self._run(
            [dict(self.BASE, neutralSite=True)], [dict(self.BASE, neutralSite=False)],
            first_name=older, second_name=newer,
        )
        reverse = self._run(
            [dict(self.BASE, neutralSite=False)], [dict(self.BASE, neutralSite=True)],
            first_name=newer, second_name=older,
        )
        for result in (forward, reverse):
            row = result["rows"][0]
            self.assertEqual(
                row["reconciliation_state"], "CONFLICT_RESOLVED_BY_DECLARED_VINTAGE"
            )
            self.assertEqual(row["admitted_provenance"]["source_file"], newer)
            self.assertIn("2026-09-09T18:08:43Z", row["resolved_by"])
        # Both orders admit the SAME observation.
        self.assertEqual(
            forward["rows"][0]["neutral_state"], reverse["rows"][0]["neutral_state"]
        )

    def test_an_identity_collision_on_one_game_id_is_a_visible_conflict(self) -> None:
        """Same game id, different participants: the id itself is
        contested and must not be silently resolved."""
        result = self._run(
            [self.BASE], [dict(self.BASE, homeId=99, awayId=98)]
        )
        self.assertEqual(result["unresolved_conflict_count"], 1)
        self.assertEqual(
            result["rows"][0]["reconciliation_state"],
            "CONFLICT_UNRESOLVED_NO_AUTHORITY_BASIS",
        )

    def test_a_changed_venue_on_one_game_id_is_a_visible_conflict(self) -> None:
        result = self._run(
            [dict(self.BASE, venueId=111)], [dict(self.BASE, venueId=222)]
        )
        self.assertEqual(result["unresolved_conflict_count"], 1)
        self.assertEqual(
            {
                o["venue_id"]
                for o in result["unresolved_conflicts"][0]["competing_observations"]
            },
            {111, 222},
        )

    def test_a_malformed_neutral_value_conflicting_with_a_real_one_is_visible(self) -> None:
        result = self._run([self.BASE], [dict(self.BASE, neutralSite="yes")])
        row = result["rows"][0]
        self.assertEqual(row["neutral_state"], "UNKNOWN")
        self.assertEqual(
            row["reconciliation_state"], "CONFLICT_UNRESOLVED_NO_AUTHORITY_BASIS"
        )

    def test_repeated_malformed_neutral_values_agree_and_deduplicate(self) -> None:
        """Two identical malformed values are not a conflict -- they agree.
        The result is still UNKNOWN, never coerced to a boolean."""
        result = self._run(
            [dict(self.BASE, neutralSite="yes")], [dict(self.BASE, neutralSite="yes")]
        )
        row = result["rows"][0]
        self.assertEqual(row["reconciliation_state"], "DEDUPLICATED_IDENTICAL_OBSERVATIONS")
        self.assertEqual(row["neutral_state"], "UNKNOWN")
        self.assertIsNone(row["ordinary_home_advantage"])

    def test_missing_participants_are_still_skipped_under_reconciliation(self) -> None:
        result = self._run([{"id": 7, "homeId": 1, "season": 2026}], [])
        self.assertEqual(result["row_count"], 0)
        self.assertEqual(result["state_counts"]["SKIPPED_MISSING_PARTICIPANT_ID"], 1)

    def test_neutral_counts_are_labelled_source_designated(self) -> None:
        result = self._run([self.BASE], [])
        self.assertTrue(result["neutral_counts_are_source_designated"])
        self.assertEqual(
            result["rows"][0]["neutral_authority"],
            "SOURCE_DESIGNATED_NOT_INDEPENDENTLY_CONFIRMED",
        )
        self.assertTrue(
            result["zero_missing_neutral_flags_is_not_zero_venue_or_temporal_uncertainty"]
        )
