"""R35-26 (Cycle #35 closeout review, 20260921T025300Z), sections 7 and 8.

The declared unfinished list is reconciled in place and left intact. The
obligations this review surfaced that were never on it are recorded here
instead, each derived from an artifact rather than stated from memory.
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

from r35_26_newly_discovered_obligations import (  # noqa: E402
    BUILDERS,
    CLOSED_HERE,
    OPEN_LOCAL,
    UNVERIFIABLE,
    build,
    coverage_item,
    find,
    mounted_lane_item,
    recall_gap_item,
)

REAL_ARTIFACT = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
    / "20260921T025300Z_closeout"
    / "CYCLE35_NEWLY_DISCOVERED_OBLIGATIONS.json"
)


def write(root: Path, name: str, payload: dict) -> Path:
    target = root / "run"
    target.mkdir(parents=True, exist_ok=True)
    path = target / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class EvidenceDerivationTests(unittest.TestCase):
    def test_an_absent_artifact_makes_the_item_unverifiable(self) -> None:
        """An obligation stated without evidence is indistinguishable from
        one made up, so it is not stated."""
        with TemporaryDirectory() as tmp:
            result = build(Path(tmp))
        self.assertEqual(result["item_count"], len(BUILDERS))
        for entry in result["items"]:
            with self.subTest(key=entry["key"]):
                self.assertEqual(entry["state"], UNVERIFIABLE)
                self.assertIsNone(entry["finding"])

    def test_the_numbers_are_read_from_the_artifact_not_hardcoded(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "CYCLE35_RELEASE_COVERAGE_BINDING.json",
                {
                    "expected_cells": 999,
                    "coverage_states": {
                        "COVERED_BY_CONFIRMED_ASSERTION": 0,
                        "COVERED_BY_CANDIDATE_OBSERVATION_ONLY": 111,
                    },
                    "episode_assertions_without_a_stated_season": 7,
                },
            )
            entry = coverage_item(root)
        self.assertEqual(entry["state"], OPEN_LOCAL)
        self.assertIn("0 of 999", entry["finding"])
        self.assertIn("111", entry["finding"])
        self.assertIn("7", entry["finding"])

    def test_each_item_carries_the_digest_of_the_file_it_was_read_from(self) -> None:
        import hashlib

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write(
                root,
                "CYCLE35_SOURCE_SPAN_SEMANTIC_REVIEW.json",
                {
                    "rows_reviewed": 34,
                    "disagreements_by_kind": {
                        "PARSER_FOUND_NO_RECORD_BUT_BOTH_SPANS_PRESENT": 11
                    },
                },
            )
            entry = recall_gap_item(root)
            self.assertEqual(
                entry["evidence_sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        self.assertIn("11 of 34", entry["finding"])

    def test_a_lane_receipt_drives_the_mounted_finding(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "CYCLE35_MOUNTED_LANE_RECEIPT.json",
                {
                    "lanes": [
                        {
                            "lane": "FULL_SUITE_MOUNTED_EXPLICIT_ENV",
                            "exit_code": 1,
                            "summary_line": "2 failed, 4147 passed",
                            "counts": {"passed": 4147, "failed": 2},
                        },
                        {
                            "lane": "FULL_SUITE_GENUINELY_UNMOUNTED",
                            "exit_code": 0,
                            "summary_line": "3945 passed",
                            "counts": {"passed": 3945},
                        },
                    ]
                },
            )
            entry = mounted_lane_item(root)
        self.assertIn("202 more tests", entry["finding"])
        self.assertIn("exits 1", entry["finding"])
        self.assertIn("exits 0", entry["finding"])

    def test_a_fixed_defect_is_not_reported_as_open(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "CYCLE35_MOUNTED_LANE_RECEIPT.json", {"lanes": []})
            result = build(root)
        closed = [e for e in result["items"] if e["state"] == CLOSED_HERE]
        self.assertEqual(len(closed), 1)
        self.assertIn("4913ea1c", closed[0]["finding"])

    def test_the_newest_copy_of_an_artifact_is_used(self) -> None:
        import os

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "old").mkdir()
            (root / "new").mkdir()
            (root / "old" / "A.json").write_text("{}", encoding="utf-8")
            newer = root / "new" / "A.json"
            newer.write_text("{}", encoding="utf-8")
            os.utime(newer, (2_000_000_000, 2_000_000_000))
            self.assertEqual(find(root, "A.json"), newer)


class SeparationTests(unittest.TestCase):
    def test_the_artifact_explains_why_it_is_not_the_declared_list(self) -> None:
        with TemporaryDirectory() as tmp:
            result = build(Path(tmp))
        why = result["why_separate_from_the_declared_list"]
        self.assertIn("none was added, removed or reworded", why)

    def test_every_requirement_reference_is_a_real_unit_id(self) -> None:
        with TemporaryDirectory() as tmp:
            result = build(Path(tmp))
        for entry in result["items"]:
            with self.subTest(key=entry["key"]):
                self.assertRegex(entry["requirement"], r"^R35-\d{2}$")

    def test_item_keys_are_unique(self) -> None:
        with TemporaryDirectory() as tmp:
            result = build(Path(tmp))
        keys = [entry["key"] for entry in result["items"]]
        self.assertEqual(len(keys), len(set(keys)))


class RealArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        if not REAL_ARTIFACT.is_file():
            self.skipTest("the newly-discovered obligations have not been generated")
        self.result = json.loads(REAL_ARTIFACT.read_text(encoding="utf-8"))

    def test_no_real_item_is_unverifiable(self) -> None:
        unverifiable = [
            entry["key"]
            for entry in self.result["items"]
            if entry["state"] == UNVERIFIABLE
        ]
        self.assertEqual(unverifiable, [])

    def test_every_item_is_derived_from_an_artifact(self) -> None:
        self.assertTrue(self.result["every_item_is_derived_from_an_artifact"])

    def test_each_evidence_file_still_matches_its_recorded_digest(self) -> None:
        import hashlib

        for entry in self.result["items"]:
            if not entry["evidence"]:
                continue
            with self.subTest(key=entry["key"]):
                path = Path(entry["evidence"])
                self.assertTrue(path.is_file(), path)
                self.assertEqual(
                    entry["evidence_sha256"],
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )


if __name__ == "__main__":
    unittest.main()
