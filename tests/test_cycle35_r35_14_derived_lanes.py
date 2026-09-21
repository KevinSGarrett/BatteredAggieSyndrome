"""R35-14 (Cycle #35 closeout review, 20260921T025300Z), sections 1 and 7.

Four validation lanes had their results typed into the tool by hand, and all
four had drifted from what the artifacts show: a "12 of 12 checks pass" that
could not go red, a mounted red-set recorded first as 3 and then as a
differently-populated 4, and a replay called PASS over 12 tables when the
delivered replay compares 15 and finds a column differing on 26 rows.

A lane that states a result does not check one. These read the artifact.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_14_validation_results import (  # noqa: E402
    DERIVED_LANES,
    derived_lanes,
    find_artifact,
    parse_unittest_output,
)


def write(root: Path, name: str, payload: dict) -> Path:
    path = root / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def lane(rows: list[dict], name: str) -> dict:
    return next(row for row in rows if row["lane"] == name)


class HostedCiLaneTests(unittest.TestCase):
    def test_a_red_hosted_run_is_not_reported_as_pass(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "CYCLE35_EXACT_HEAD_CI_STATUS.json",
                {
                    "all_pass": False,
                    "head_sha": "c" * 40,
                    "by_bucket": {"pass": 12, "fail": 6},
                },
            )
            row = lane(derived_lanes(root, cycle_root=root), "HOSTED_CI_PR_691")
        self.assertEqual(row["result"], "NOT_ALL_PASS")
        self.assertIn("12 of 18", row["detail"])

    def test_a_green_hosted_run_still_says_it_misses_the_mounted_lane(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                "CYCLE35_EXACT_HEAD_CI_STATUS.json",
                {"all_pass": True, "head_sha": "d" * 40, "by_bucket": {"pass": 18}},
            )
            row = lane(derived_lanes(root, cycle_root=root), "HOSTED_CI_PR_691")
        self.assertEqual(row["result"], "PASS")
        self.assertIn("cannot execute the mounted private-data lane", row["detail"])


class MountedRedSetLaneTests(unittest.TestCase):
    RECEIPT = "CYCLE35_MOUNTED_LANE_RECEIPT.json"

    def test_a_receipt_without_the_lane_is_not_a_pass(self) -> None:
        """A receipt that never ran the lane reports no failures for it.
        Rendering that as PASS is how a lane that never executed looks green.
        """
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, self.RECEIPT, {"head": "e" * 40, "lanes": [
                {"lane": "FAMILY_B_MOUNTED_EXPLICIT_ENV", "counts": {"passed": 5}}
            ]})
            row = lane(derived_lanes(root, cycle_root=root), "FULL_SUITE_MOUNTED_RED_SET")
        self.assertEqual(row["result"], "LANE_NOT_IN_RECEIPT")
        self.assertIn("is not a zero failure count", row["detail"])

    def test_errors_are_counted_under_either_spelling(self) -> None:
        """pytest prints "2 errors" but "1 error", and the receipt keeps
        whichever word the run printed."""
        for key in ("error", "errors"):
            with self.subTest(key=key):
                with TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    write(root, self.RECEIPT, {"head": "f" * 40, "lanes": [{
                        "lane": "FULL_SUITE_MOUNTED_EXPLICIT_ENV",
                        "counts": {"failed": 2, key: 2, "passed": 4238},
                        "summary_line": "2 failed, 4238 passed, 2 errors",
                        "log_path": "x.log",
                        "log_sha256": "abc",
                    }]})
                    row = lane(derived_lanes(root, cycle_root=root), "FULL_SUITE_MOUNTED_RED_SET")
                self.assertEqual(row["result"], "FAIL")
                self.assertIn("4 red", row["detail"])

    def test_a_clean_mounted_lane_passes(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, self.RECEIPT, {"head": "a" * 40, "lanes": [{
                "lane": "FULL_SUITE_MOUNTED_EXPLICIT_ENV",
                "counts": {"passed": 4240},
                "summary_line": "4240 passed",
                "log_path": "x.log",
                "log_sha256": "abc",
            }]})
            row = lane(derived_lanes(root, cycle_root=root), "FULL_SUITE_MOUNTED_RED_SET")
        self.assertEqual(row["result"], "PASS")


class ReplayLaneTests(unittest.TestCase):
    def test_a_differing_replay_is_not_reported_as_pass(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "CYCLE35_DETERMINISTIC_RELEASE_REPLAY.json", {
                "tables_compared": [f"t{n}" for n in range(15)],
                "scientific_content_identical": False,
                "scientific_content_identical_apart_from_build_clock": True,
                "comparison": {"column_level_diffs": [
                    {"table": "adjudication", "columns_differing": {"decided_at_utc": 26}}
                ]},
            })
            row = lane(derived_lanes(root, cycle_root=root), "DETERMINISTIC_RELEASE_REPLAY")
        self.assertEqual(row["result"], "DIFFERS_SEE_DETAIL")
        self.assertIn("15 tables", row["detail"])
        self.assertIn("adjudication.decided_at_utc differs on 26 rows", row["detail"])


class MissingArtifactTests(unittest.TestCase):
    def test_every_lane_reports_absence_rather_than_a_result(self) -> None:
        with TemporaryDirectory() as tmp:
            rows = derived_lanes(Path(tmp) / "empty", cycle_root=Path(tmp) / "empty")
        self.assertEqual(len(rows), len(DERIVED_LANES))
        for row in rows:
            with self.subTest(lane=row["lane"]):
                self.assertIn(row["result"], {"ARTIFACT_ABSENT", "ARTIFACT_UNREADABLE"})
                self.assertNotIn("PASS", row["result"])

    def test_an_unreadable_artifact_is_distinguished_from_a_missing_one(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CYCLE35_EXACT_HEAD_CI_STATUS.json").write_text(
                "not json", encoding="utf-8"
            )
            row = lane(derived_lanes(root, cycle_root=root), "HOSTED_CI_PR_691")
        self.assertEqual(row["result"], "ARTIFACT_UNREADABLE")

    def test_a_present_artifact_carries_its_digest(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write(
                root,
                "CYCLE35_EXACT_HEAD_CI_STATUS.json",
                {"all_pass": True, "head_sha": "b" * 40, "by_bucket": {"pass": 1}},
            )
            row = lane(derived_lanes(root, cycle_root=root), "HOSTED_CI_PR_691")
            # Inside the temporary directory: the file has to still exist to
            # be hashed for comparison.
            self.assertEqual(
                row["artifact_sha256"], hashlib.sha256(path.read_bytes()).hexdigest()
            )


class ArtifactResolutionTests(unittest.TestCase):
    def test_the_newest_copy_wins_over_the_local_one(self) -> None:
        """Preferring the local copy unconditionally picked a stale receipt
        out of the output directory over the fresh one from the lane run."""
        import os

        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            stale = out / "A.json"
            stale.write_text("{}", encoding="utf-8")
            os.utime(stale, (1_000_000_000, 1_000_000_000))
            resolved = find_artifact(out, "A.json", cycle_root=out)
        self.assertEqual(resolved, stale)


class LaneParserTests(unittest.TestCase):
    def test_a_completed_pytest_run_is_not_called_incomplete(self) -> None:
        parsed = parse_unittest_output(
            "....\n2 failed, 4238 passed, 25 skipped, 2 errors in 1308.37s (0:21:48)\n"
        )
        self.assertTrue(parsed["completed"])
        self.assertEqual(parsed["result"], "FAILED")
        self.assertEqual(parsed["counts"]["passed"], 4238)
        self.assertEqual(parsed["parser"], "pytest_summary")

    def test_unreadable_output_is_not_called_incomplete(self) -> None:
        """"The parser could not read this" and "the run did not finish" are
        different statements about different things."""
        self.assertEqual(
            parse_unittest_output("wholly unrelated text")["result"],
            "UNRECOGNISED_OUTPUT_FORMAT",
        )
        self.assertEqual(parse_unittest_output("")["result"], "DID_NOT_COMPLETE")


if __name__ == "__main__":
    unittest.main()
