"""Cycle 27 contest/checkpoint ledger: 91 contests, Saturday retained."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.operations.contest_checkpoint_ledger import (
    EmptyUniverseWithoutAuthority,
    EVIDENCE_CAPTURED,
    WEEK1_CONTEST_COUNT,
    build_cycle27_ledger,
    default_receipt_paths,
    evaluate_checkpoint_state,
    load_c26_ledger,
    load_valid_receipts,
    require_contest_universe,
)

REPO = Path(__file__).resolve().parents[1]
OPS26 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle26")
ART26 = REPO / "artifacts" / "scientific_integrity" / "cycle26"
LEDGER_PATHS = (
    REPO
    / "artifacts"
    / "scientific_integrity"
    / "cycle27"
    / "CYCLE27_CONTEST_CHECKPOINT_LEDGER.json",
)
OPS_LEDGER = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle27")
    / "CYCLE27_CONTEST_CHECKPOINT_LEDGER.json"
)
AFTER_SATURDAY_CUTOFF = datetime(2026, 9, 4, 18, 0, tzinfo=timezone.utc)
SATURDAY_T24_CLUSTER = {
    "6590890",
    "6593811",
    "6594325",
    "6601384",
    "6611692",
    "6611873",
    "6613128",
    "6617023",
    "6620636",
    "6620944",
}


class Cycle27ContestCheckpointLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c26 = load_c26_ledger(OPS26, ART26)
        self.receipts = load_valid_receipts(default_receipt_paths(OPS26, ART26))

    def test_empty_universe_without_authority_fails(self) -> None:
        with self.assertRaises(EmptyUniverseWithoutAuthority) as raised:
            require_contest_universe([])
        self.assertIn("EMPTY_UNIVERSE_WITHOUT_AUTHORITY", str(raised.exception))
        with self.assertRaises(EmptyUniverseWithoutAuthority):
            require_contest_universe(
                [],
                empty_universe_authority={"empty_universe_authorized": True},
            )
        with self.assertRaises(EmptyUniverseWithoutAuthority):
            build_cycle27_ledger(
                c26_ledger={"contests": []},
                receipts=self.receipts,
                now=AFTER_SATURDAY_CUTOFF,
            )

    def test_authorized_empty_universe_is_explicit(self) -> None:
        rows = require_contest_universe(
            [],
            empty_universe_authority={
                "empty_universe_authorized": True,
                "authority_identity": "test-empty-universe",
            },
        )
        self.assertEqual(rows, [])

    def test_universe_has_91_contests(self) -> None:
        ledger = build_cycle27_ledger(
            c26_ledger=self.c26,
            receipts=self.receipts,
            now=AFTER_SATURDAY_CUTOFF,
        )
        self.assertEqual(ledger["contest_count"], WEEK1_CONTEST_COUNT)
        self.assertEqual(len(ledger["contests"]), WEEK1_CONTEST_COUNT)
        ids = [row["ncaa_contest_id"] for row in ledger["contests"]]
        self.assertEqual(len(set(ids)), WEEK1_CONTEST_COUNT)

    def test_saturday_remains_completed_after_clock_passes(self) -> None:
        ledger = build_cycle27_ledger(
            c26_ledger=self.c26,
            receipts=self.receipts,
            now=AFTER_SATURDAY_CUTOFF,
        )
        by_id = {row["ncaa_contest_id"]: row for row in ledger["contests"]}
        for contest_id in SATURDAY_T24_CLUSTER:
            row = by_id[contest_id]
            self.assertEqual(row["t24h_state"], EVIDENCE_CAPTURED)
            self.assertGreaterEqual(row["t24h"]["cutoff_utc"], "2026-09-04T16:00:00Z")
            self.assertTrue(
                row["t24h"]["completed_valid_receipt_retained_after_cutoff"]
            )
            self.assertNotEqual(row["t24h_state"], "MISSED_CUTOFF_NO_BACKFILL")
        self.assertGreaterEqual(ledger["saturday_t24h_completed_count"], 10)
        self.assertTrue(ledger["do_not_recompute_saturday_as_missed"])
        self.assertEqual(by_id["6591259"]["t90m_state"], EVIDENCE_CAPTURED)
        self.assertNotEqual(by_id["6591259"]["t90m_state"], "MISSED_CUTOFF_NO_BACKFILL")

    def test_evaluate_after_cutoff_keeps_timely_receipt(self) -> None:
        contest = {
            "ncaa_contest_id": "6590890",
            "kickoff_bound_utc": "2026-09-05T16:00:00Z",
            "t24h_cutoff_utc": "2026-09-04T16:00:00Z",
            "t90m_cutoff_utc": "2026-09-05T14:30:00Z",
            "abstention_reasons": [],
        }
        result = evaluate_checkpoint_state(
            now=AFTER_SATURDAY_CUTOFF,
            contest=contest,
            kind="T24H",
            receipts=self.receipts,
            live_owners=[],
        )
        self.assertEqual(result["state"], EVIDENCE_CAPTURED)

    def test_early_receipt_does_not_cover_later_contest_window(self) -> None:
        contest = {
            "ncaa_contest_id": "6609172",
            "kickoff_bound_utc": "2026-09-05T23:00:00Z",
            "t24h_cutoff_utc": "2026-09-04T23:00:00Z",
            "t90m_cutoff_utc": "2026-09-05T21:30:00Z",
            "abstention_reasons": [],
        }
        saturday = {
            "kind": "T24H",
            "issued_at_utc": "2026-09-04T15:20:10Z",
            "earliest_cutoff_utc": "2026-09-04T16:00:00Z",
            "coverage": "REMAINING_WINDOW",
            "artifact_type": "CYCLE26_SEP5_SATURDAY_T24H_FREEZE_RECEIPT",
            "forecast_frozen": False,
        }
        result = evaluate_checkpoint_state(
            now=AFTER_SATURDAY_CUTOFF,
            contest=contest,
            kind="T24H",
            receipts=[saturday],
            live_owners=[],
        )
        self.assertNotEqual(result["state"], EVIDENCE_CAPTURED)
        self.assertNotIn(
            "CYCLE26_SEP5_SATURDAY_T24H_FREEZE_RECEIPT", result["joined_receipts"]
        )

    def test_written_artifacts_cover_91_and_saturday(self) -> None:
        paths = list(LEDGER_PATHS)
        if OPS_LEDGER.is_file():
            paths.append(OPS_LEDGER)
        self.assertTrue(paths, "repository ledger artifact is required")
        for path in paths:
            self.assertTrue(path.is_file(), path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["contest_count"], WEEK1_CONTEST_COUNT)
            by_id = {row["ncaa_contest_id"]: row for row in payload["contests"]}
            for contest_id in SATURDAY_T24_CLUSTER:
                self.assertEqual(by_id[contest_id]["t24h_state"], EVIDENCE_CAPTURED)
            self.assertIn("sunday_monday_ownership_plan", payload)
            self.assertTrue(payload["sunday_monday_ownership_plan"]["sunday"])
            self.assertTrue(payload["sunday_monday_ownership_plan"]["monday"])


if __name__ == "__main__":
    unittest.main()
