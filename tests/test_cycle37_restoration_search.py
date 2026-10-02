"""Cycle #37 - Attempt #2 - ACTUAL_STATE

W37R-20: a search for corroborating evidence must not be able to find itself.

R37-N-AC02 turns on one question — is there any record of what the original
serialized `inventory.json` hashed to? — because MF37-07 forbids claiming
byte-exact recovery without one. The tool that asks it writes its own receipt
inside one of the roots it searches, so its first run reported "no original
digest" and its second run found the candidate digest in the first run's
receipt and reported "yes". A search that can match its own output proves
whatever it last said.

These tests pin the exclusion by path and by content marker, and pin that
running the search twice over a tree the search itself has written to gives
the same answer both times.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "cycle37" / "r37_n_restoration_candidate.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("r37n_candidate_under_test", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = load_tool()

DIGEST = "a" * 64


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)
        self.repo = self.root / "repo"
        self.data = self.root / "data"
        (self.repo / "artifacts" / "data_lake").mkdir(parents=True)
        (self.data / "ops" / "cycle37").mkdir(parents=True)
        (
            self.data / "features" / "tamu_official_historical_coverage_inventory"
        ).mkdir(parents=True)

    def search(self, own=()):
        return tool.search_for_an_original_digest(
            self.repo, self.data, DIGEST, own_outputs=tuple(own)
        )

    def write(self, relative: str, payload: object) -> Path:
        path = self.data / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


class SelfExclusionTests(Base):
    def test_a_foreign_record_of_the_digest_is_a_hit(self) -> None:
        """The positive control: the search must still be able to find one."""

        self.write("ops/cycle37/some_other_manifest.json", {"raw_sha256": DIGEST})
        result = self.search()
        self.assertTrue(result["an_original_byte_digest_was_found"])
        self.assertEqual(result["hit_count"], 1)

    def test_the_tools_own_receipt_is_excluded_by_path(self) -> None:
        receipt = self.write("ops/cycle37/receipt.json", {"candidate_sha256": DIGEST})
        result = self.search(own=[receipt])
        self.assertFalse(result["an_original_byte_digest_was_found"])
        self.assertEqual(result["own_output_exclusion_count"], 1)

    def test_a_file_under_an_excluded_directory_is_excluded(self) -> None:
        directory = self.data / "ops" / "cycle37" / "mine"
        directory.mkdir(parents=True)
        (directory / "inner.json").write_text(
            json.dumps({"candidate_sha256": DIGEST}), encoding="utf-8"
        )
        result = self.search(own=[directory])
        self.assertFalse(result["an_original_byte_digest_was_found"])

    def test_the_content_marker_excludes_a_receipt_moved_elsewhere(self) -> None:
        """Path exclusion alone is not enough if the receipt is copied."""

        self.write(
            "ops/cycle37/copied_receipt.json",
            {"acceptance": ["R37-N-AC02"], "candidate_sha256": DIGEST},
        )
        result = self.search(own=[])
        self.assertFalse(result["an_original_byte_digest_was_found"])
        self.assertEqual(result["own_output_exclusion_count"], 1)

    def test_the_answer_is_stable_across_two_runs(self) -> None:
        """The regression itself: run, write a receipt, run again."""

        first = self.search(own=[])
        receipt = self.data / "ops" / "cycle37" / "r37n_receipt.json"
        receipt.write_text(
            json.dumps({"acceptance": ["R37-N-AC02"], "candidate_sha256": DIGEST}),
            encoding="utf-8",
        )
        second = self.search(own=[receipt])
        self.assertEqual(
            first["an_original_byte_digest_was_found"],
            second["an_original_byte_digest_was_found"],
        )
        self.assertFalse(second["an_original_byte_digest_was_found"])

    def test_the_exclusion_is_reported_not_silent(self) -> None:
        receipt = self.write("ops/cycle37/receipt.json", {"candidate_sha256": DIGEST})
        result = self.search(own=[receipt])
        self.assertIn(str(receipt), result["own_outputs_excluded"])
        self.assertIn("its own candidate digest", result["why_excluded"])

    def test_the_searched_roots_are_named(self) -> None:
        result = self.search()
        self.assertEqual(len(result["roots_searched"]), 3)
        self.assertTrue(any("data_lake" in r for r in result["roots_searched"]))

    def test_an_empty_tree_finds_nothing_and_says_so(self) -> None:
        result = self.search()
        self.assertFalse(result["an_original_byte_digest_was_found"])
        self.assertEqual(result["hit_count"], 0)


class SerializerTests(unittest.TestCase):
    def test_the_serializer_is_the_producers_own(self) -> None:
        """The candidate's bytes must be what the producer would write."""

        payload = {"b": 2, "a": 1}
        self.assertEqual(
            tool.serialize(payload),
            b'{\n  "a": 1,\n  "b": 2\n}\n',
        )

    def test_the_identity_covers_exactly_four_keys(self) -> None:
        self.assertEqual(len(tool.IDENTITY_COVERED_KEYS), 4)
        self.assertIn("history_index_sha256", tool.IDENTITY_COVERED_KEYS)


if __name__ == "__main__":
    unittest.main()
