"""Cycle #37 - Attempt #2: the packet builder decides one headline and labels with it (no placeholder state)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("_c37_packet", ROOT / "tools" / "cycle37" / "build_worker_packet.py")
PACKET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKET)


class PacketHeadlineTests(unittest.TestCase):
    def test_headline_follows_the_operating_policy(self) -> None:
        self.assertEqual(PACKET.decide_headline(True, True), "IN_PROGRESS_LOCAL_WORK_REMAINS")
        self.assertEqual(PACKET.decide_headline(True, False), "IN_PROGRESS_LOCAL_WORK_REMAINS")
        self.assertEqual(PACKET.decide_headline(False, True), "BLOCKED_INCOMPLETE")
        self.assertEqual(PACKET.decide_headline(False, False), "IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED")

    def test_label_matches_the_protocol_identity_label(self) -> None:
        self.assertEqual(PACKET.identity_label("BLOCKED_INCOMPLETE"),
                         "Cycle #37 — Attempt #2 — BLOCKED_INCOMPLETE")

    def test_catch_all_is_split_into_accountable_items(self) -> None:
        unfinished = [
            {"id": "UF-01", "kind": "LOCAL_DATA_PROCESSING", "catch_all": True, "owner": "worker",
             "criterion_ids": ["R-1"], "lane_ids": ["LANE_A"], "finding_ids": ["W-1"], "next_action": "generic",
             "alternatives_and_reason": "x"},
            {"id": "UF-02", "kind": "ACCESS", "owner": "user", "criterion_ids": ["R-2"], "lane_ids": [],
             "finding_ids": [], "next_action": "permit", "alternatives_and_reason": "y"},
        ]
        split = PACKET.split_local_catch_all(
            unfinished, status={"R-1": "IN_PROGRESS", "LANE_A": "FAIL", "W-1": "OPEN_ASSIGNED"},
            why={"R-1": "rerun the reparse", "LANE_A": "red", "W-1": "fix it"})
        ids = [item["id"] for item in split]
        self.assertEqual(ids, ["UF-01::R-1", "UF-01::LANE_A", "UF-01::W-1", "UF-02"])
        first = split[0]
        self.assertEqual(first["criterion_ids"], ["R-1"])
        self.assertEqual(first["next_action"], "R-1 (IN_PROGRESS): rerun the reparse")
        self.assertIn("VERIFIED_LOCAL", first["closure_check_positive"])
        self.assertIn("still routes R-1", first["closure_check_negative"])
        self.assertNotIn("catch_all", first)
        self.assertEqual(split[1]["lane_ids"], ["LANE_A"])
        self.assertIn("PASS", split[1]["closure_check_positive"])
        empty = PACKET.split_local_catch_all([{**unfinished[0], "criterion_ids": [], "lane_ids": [],
                                               "finding_ids": []}], status={}, why={})
        self.assertEqual(empty, [])

    def test_builder_writes_no_placeholder_state(self) -> None:
        source = (ROOT / "tools" / "cycle37" / "build_worker_packet.py").read_text(encoding="utf-8")
        self.assertNotIn('"ACTUAL_STATE"', source)
        self.assertNotIn("- ACTUAL_STATE", source)


if __name__ == "__main__":
    unittest.main()
