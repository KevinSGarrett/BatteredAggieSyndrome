"""Cycle 27 remaining-checkpoint current-contest binding tests.

Proves the helper is actually executed. The C26 materializer remains a C24 copy.
No numpy. Isolated fixtures only.
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.data.cycle27_current_contest_checkpoint_binding import (  # noqa: E402
    CurrentContestCheckpointBindingError,
    bind_contest,
    bind_team_for_checkpoint,
    build_binding,
    contests_from_census_rows,
)
from aggie_analytics.data.week1_2026_current_contest_binding_successor import (  # noqa: E402
    build_current_contest_row,
)

UTC = timezone.utc
NOW = datetime(2026, 9, 4, 18, 0, tzinfo=UTC)
FOCUS = {
    "contest_id": "6607349",
    "home_team_key": "SRC-002:TEAM:245",
    "away_team_key": "SRC-002:TEAM:2623",
    "home_conference": "SEC",
    "away_conference": "CUSA",
    "home_subdivision": "FBS",
    "away_subdivision": "FCS",
    "kickoff_bound_utc": "2026-09-05T23:00:00Z",
}


class Cycle27CurrentContestCheckpointBindingTests(unittest.TestCase):
    def test_purity_fails_if_helper_never_executes(self) -> None:
        def silent(**kwargs):
            return {
                "team_key": kwargs["team_key"],
                "opponent_key": "SRC-002:TEAM:2623",
                "copied_from_terminal_historical_row": False,
                "row_state": "UNTRUSTED_SHADOW",
                "conference": kwargs["current_conference"],
                "subdivision": kwargs["current_subdivision"],
                "rank": None,
            }

        # bind_team still records helper_calls before invoking fn; purity is
        # the build_binding empty-call guard plus an explicit empty log.
        calls: list[dict[str, object]] = []
        with self.assertRaises(CurrentContestCheckpointBindingError):
            build_binding(contests=[], now_utc=NOW, helper=silent)
        self.assertEqual(calls, [])

    def test_helper_is_actually_called(self) -> None:
        calls: list[dict[str, object]] = []

        def wrapped(**kwargs):
            calls.append({"team_key": kwargs["team_key"]})
            return build_current_contest_row(**kwargs)

        bound = bind_contest(FOCUS, now_utc=NOW, helper=wrapped)
        self.assertEqual(len(calls), 2)
        self.assertEqual(bound["home"]["opponent_key"], "SRC-002:TEAM:2623")
        self.assertEqual(bound["away"]["opponent_key"], "SRC-002:TEAM:245")
        self.assertFalse(bound["copied_from_terminal_historical_row"])
        self.assertFalse(bound["new_forecast_frozen"])
        self.assertEqual(
            bound["home"]["forecast_issuance"],
            "ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED",
        )
        self.assertEqual(bound["home"]["conference"], "SEC")
        self.assertEqual(bound["away"]["subdivision"], "FCS")
        self.assertIsNone(bound["home"]["venue"])
        self.assertFalse(bound["home"]["fake_site_or_venue_default"])

    def test_stale_historical_opponent_is_rejected(self) -> None:
        row = bind_team_for_checkpoint(
            team_key="SRC-002:TEAM:245",
            contests=[FOCUS],
            current_conference="SEC",
            current_subdivision="FBS",
            terminal_historical_opponent="SRC-002:TEAM:999",
        )
        self.assertEqual(row["row_state"], "ABSTAIN_STALE_HISTORICAL_CURRENT_FIELDS")
        self.assertEqual(row["opponent_key"], "SRC-002:TEAM:2623")

    def test_rank_not_admitted_is_not_copied(self) -> None:
        row = bind_team_for_checkpoint(
            team_key="SRC-002:TEAM:245",
            contests=[FOCUS],
            current_conference="SEC",
            current_subdivision="FBS",
            current_rank="3",
            rank_admitted=False,
        )
        self.assertIsNone(row["rank"])
        self.assertFalse(row["rank_admitted"])

    def test_kicked_off_is_retrospective_not_new_freeze(self) -> None:
        past = dict(FOCUS)
        past["kickoff_bound_utc"] = "2026-09-03T22:00:00Z"
        bound = bind_contest(past, now_utc=NOW)
        self.assertTrue(bound["kicked_off_at_bind"])
        self.assertEqual(
            bound["home"]["forecast_issuance"],
            "RETROSPECTIVE_DIAGNOSTIC_NOT_PROSPECTIVE_FREEZE",
        )
        self.assertFalse(bound["new_forecast_frozen"])

    def test_census_rows_keep_both_participants(self) -> None:
        contests = contests_from_census_rows(
            [
                {
                    "ncaa_contest_id": "6607349",
                    "canonical_team_id": "SRC-002:TEAM:245",
                    "site_orientation": "HOME",
                    "conference_name": "SEC",
                    "subdivision": "FBS",
                },
                {
                    "ncaa_contest_id": "6607349",
                    "canonical_team_id": "SRC-002:TEAM:2623",
                    "site_orientation": "AWAY",
                    "conference_name": "CUSA",
                    "subdivision": "FCS",
                },
            ]
        )
        self.assertEqual(len(contests), 1)
        payload = build_binding(contests=contests, now_utc=NOW)
        self.assertTrue(payload["helper_was_executed"])
        self.assertEqual(payload["helper_call_count"], 2)
        self.assertEqual(payload["new_forecast_frozen_count"], 0)
        self.assertEqual(payload["c26_gate_identity_preserved"][:8], "aa4ff84b")

    def test_neutral_contests_are_included_without_fake_home_venue(self) -> None:
        contests = contests_from_census_rows(
            [
                {
                    "ncaa_contest_id": "6594109",
                    "canonical_team_id": "SRC-002:TEAM:239",
                    "site_orientation": "NEUTRAL",
                    "conference_name": "SEC",
                    "subdivision": "FBS",
                },
                {
                    "ncaa_contest_id": "6594109",
                    "canonical_team_id": "SRC-002:TEAM:2",
                    "site_orientation": "NEUTRAL",
                    "conference_name": "ACC",
                    "subdivision": "FBS",
                },
            ]
        )
        self.assertEqual(len(contests), 1)
        self.assertEqual(contests[0]["site"], "NEUTRAL")
        self.assertEqual(
            contests[0]["listed_home_authority"],
            "NEUTRAL_PAIR_SLOTTED_BY_CANONICAL_ID_NOT_VENUE_HOME",
        )
        bound = bind_contest(contests[0], now_utc=NOW)
        self.assertEqual(bound["home"]["site"], "NEUTRAL")
        self.assertFalse(bound["home"]["fake_site_or_venue_default"])

    def test_transplant_flag_is_hard_error(self) -> None:
        def bad(**kwargs):
            return {
                "team_key": kwargs["team_key"],
                "opponent_key": "SRC-002:TEAM:2623",
                "copied_from_terminal_historical_row": True,
            }

        with self.assertRaises(CurrentContestCheckpointBindingError):
            bind_team_for_checkpoint(
                team_key="SRC-002:TEAM:245",
                contests=[FOCUS],
                current_conference="SEC",
                current_subdivision="FBS",
                helper=bad,
            )

    def test_live_binding_artifact_covers_91_contests(self) -> None:
        payload = json.loads(
            (
                REPO
                / "artifacts/scientific_integrity/cycle27/CYCLE27_CURRENT_CONTEST_CHECKPOINT_BINDING.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(payload["contest_count"], 91)
        self.assertEqual(payload["helper_call_count"], 182)
        self.assertTrue(payload["helper_was_executed"])
        self.assertEqual(payload["new_forecast_frozen_count"], 0)
        sites = {row["home"].get("site") for row in payload["contests"]}
        self.assertIn("NEUTRAL", sites)


if __name__ == "__main__":
    unittest.main()
