"""R35-22 (Cycle #35 closeout review, 20260921T025300Z), section 7:
"Generate one coherent current evidence graph across run directories...
Resolve every evidence reference to a real path/hash... The current packet
has 26 unfinished entries, 22 labeled local, yet lists only five owner
decisions as if no local work remained. Some entries are stale and others
remain real. Reconcile each entry with delivered evidence; do not simply
delete the list or relabel its contents."
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

from r35_22_evidence_graph import (  # noqa: E402
    CATEGORY_DATA_GAP,
    CATEGORY_RESOLVED_HERE,
    CATEGORY_RELEASE_AUTHORITY,
    CATEGORY_STALE,
    CYCLE_RUNS,
    index_artifacts,
    query_release,
    reconcile_items,
    resolve_evidence,
)


class ArtifactIndexTests(unittest.TestCase):
    def test_an_artifact_is_found_in_any_run_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run_a").mkdir()
            (root / "run_b").mkdir()
            (root / "run_a" / "THING.json").write_text("{}", encoding="utf-8")
            (root / "run_b" / "OTHER.json").write_text("{}", encoding="utf-8")
            index = index_artifacts(root)
        self.assertEqual(index["artifact_count"], 2)
        self.assertIn("THING.json", index["by_name"])
        self.assertEqual(sorted(index["directories"]), ["run_a", "run_b"])

    def test_vendored_trees_are_not_indexed_as_cycle_evidence(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            vendored = root / "run" / "wheel_venv" / "Lib" / "site-packages"
            vendored.mkdir(parents=True)
            (vendored / "THING.json").write_text("{}", encoding="utf-8")
            index = index_artifacts(root)
        self.assertEqual(index["artifact_count"], 0)


class EvidenceResolutionTests(unittest.TestCase):
    def test_a_reference_resolves_across_directories_not_just_one(self) -> None:
        """The packet's own sha map only looked in its own output
        directory, so almost every reference resolved to null."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "elsewhere").mkdir()
            (root / "elsewhere" / "EVIDENCE.json").write_text("{}", encoding="utf-8")
            index = index_artifacts(root)
            resolved = resolve_evidence({"R35-01": {"evidence": ["EVIDENCE.json"]}}, index)
        entry = resolved["by_unit"]["R35-01"][0]
        self.assertTrue(entry["resolved"])
        self.assertIsNotNone(entry["sha256"])
        self.assertEqual(resolved["dangling_count"], 0)

    def test_a_genuinely_missing_reference_is_reported_as_dangling(self) -> None:
        with TemporaryDirectory() as tmp:
            index = index_artifacts(Path(tmp))
            resolved = resolve_evidence({"R35-01": {"evidence": ["ABSENT.json"]}}, index)
        self.assertEqual(resolved["dangling_count"], 1)
        self.assertFalse(resolved["by_unit"]["R35-01"][0]["resolved"])

    def test_a_parenthetical_annotation_does_not_break_resolution(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run").mkdir()
            (root / "run" / "EVIDENCE.json").write_text("{}", encoding="utf-8")
            index = index_artifacts(root)
            resolved = resolve_evidence(
                {"R35-01": {"evidence": ["EVIDENCE.json (fresh re-run)"]}}, index
            )
        self.assertTrue(resolved["by_unit"]["R35-01"][0]["resolved"])


class ReconciliationTests(unittest.TestCase):
    EMPTY_INDEX = {"by_name": {}, "directories": {}, "artifact_count": 0}

    CELLS_ITEM = {
        "requirement": "R35-03",
        "kind": "LOCAL_WORK_REMAINING",
        "blocker": "The corpus covers 2000-2012 only; 2013-2026 user rows are not cell-ingested.",
    }

    def test_an_entry_is_not_judged_when_there_is_nothing_to_judge_it_against(
        self,
    ) -> None:
        unchecked = reconcile_items(
            [dict(self.CELLS_ITEM)], self.EMPTY_INDEX, {"queried": False}
        )
        self.assertEqual(unchecked[0]["category"], "REAL_LOCAL_WORK_REMAINING")

    def test_an_entry_accurate_when_written_is_resolved_here_not_called_stale(
        self,
    ) -> None:
        """The packet's release carried 73 rows in 2013-2026, so the entry was
        right. Labelling it stale would brand an accurate entry a mistake and
        take credit for evidence that did not exist when it was written."""
        checked = reconcile_items(
            [dict(self.CELLS_ITEM)],
            self.EMPTY_INDEX,
            {
                "queried": True,
                "database": "published.sqlite",
                "observations_2013_2026": 86105,
                "prior_delivered_observations_2013_2026": 73,
            },
        )
        self.assertEqual(checked[0]["category"], CATEGORY_RESOLVED_HERE)
        self.assertIn("86,105", checked[0]["finding"])
        self.assertIn("ACCURATE", checked[0]["finding"])

    def test_an_entry_contradicted_by_pre_existing_evidence_is_called_stale(
        self,
    ) -> None:
        """The Jira readback predates this review, so nothing done here
        settles that entry -- it was already wrong."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run").mkdir()
            (root / "run" / "CYCLE35_JIRA_LIVE_READBACK.json").write_text(
                json.dumps(
                    {
                        "issues": [{"key": "BAT-1"}, {"key": "BAT-2"}],
                        "generated_at_utc": "2026-09-20T19:40:12Z",
                    }
                ),
                encoding="utf-8",
            )
            index = index_artifacts(root)
            # Inside the temporary root: reconciliation re-reads each artifact
            # rather than trusting the index, so the files must still be there.
            out = reconcile_items(
                [
                    {
                        "requirement": "R35-13",
                        "kind": "LOCAL_WORK_REMAINING",
                        "blocker": "No live Jira readback performed this cycle.",
                    }
                ],
                index,
                {"queried": False},
            )
        self.assertEqual(out[0]["category"], CATEGORY_STALE)
        self.assertIn("2 issues", out[0]["finding"])

    def test_a_release_authority_item_is_not_called_local_work(self) -> None:
        items = [
            {
                "requirement": "R35-10",
                "kind": "EXTERNAL_AUTHORITY",
                "blocker": "Canonical activation requires CYCLE33-APPROVAL-LAKE-SUCCESSOR-001.",
            }
        ]
        out = reconcile_items(items, self.EMPTY_INDEX, {"queried": False})
        self.assertEqual(out[0]["category"], CATEGORY_RELEASE_AUTHORITY)

    def test_a_data_gap_is_not_called_an_implementation_gap(self) -> None:
        items = [
            {
                "requirement": "R35-03",
                "kind": "LOCAL_WORK_REMAINING",
                "blocker": "responsibility_assertion and scheme_assertion have zero rows; "
                "no source explicitly evidenced either this cycle.",
            }
        ]
        out = reconcile_items(
            items,
            self.EMPTY_INDEX,
            {
                "queried": True,
                "database": "x.sqlite",
                "responsibility_assertions": 0,
                "scheme_assertions": 0,
            },
        )
        self.assertEqual(out[0]["category"], CATEGORY_DATA_GAP)

    def test_every_item_is_retained_none_deleted(self) -> None:
        items = [
            {"requirement": f"R35-{n:02d}", "kind": "LOCAL_WORK_REMAINING", "blocker": f"item {n}"}
            for n in range(1, 11)
        ]
        out = reconcile_items(items, self.EMPTY_INDEX, {"queried": False})
        self.assertEqual(len(out), len(items))
        self.assertEqual(
            [x["blocker"] for x in out], [x["blocker"] for x in items]
        )

    def test_an_unrecognised_item_keeps_the_conservative_local_default(self) -> None:
        out = reconcile_items(
            [{"requirement": "R35-99", "kind": "LOCAL_WORK_REMAINING", "blocker": "something new"}],
            self.EMPTY_INDEX,
            {"queried": False},
        )
        self.assertEqual(out[0]["category"], "REAL_LOCAL_WORK_REMAINING")


class RealCycleEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        if not CYCLE_RUNS.is_dir():
            self.skipTest("cycle run root is not mounted")

    def test_the_real_cycle_has_artifacts_in_many_run_directories(self) -> None:
        index = index_artifacts(CYCLE_RUNS)
        self.assertGreater(index["artifact_count"], 50)
        self.assertGreater(len(index["directories"]), 5)

    def test_the_delivered_release_carries_both_year_ranges(self) -> None:
        candidates = sorted(
            (p for p in CYCLE_RUNS.rglob("*.sqlite") if "site-packages" not in str(p)),
            key=lambda p: p.stat().st_mtime,
        )
        if not candidates:
            self.skipTest("no delivered release database is present")
        release = query_release(candidates[-1])
        self.assertTrue(release["queried"])
        self.assertGreater(release["observations_2000_2012"], 0)
        self.assertGreater(release["observations_2013_2026"], 0)

    def test_the_delivered_release_has_no_garbled_wikitext_names(self) -> None:
        candidates = sorted(
            (p for p in CYCLE_RUNS.rglob("*.sqlite") if "site-packages" not in str(p)),
            key=lambda p: p.stat().st_mtime,
        )
        if not candidates:
            self.skipTest("no delivered release database is present")
        release = query_release(candidates[-1])
        self.assertEqual(release["garbled_wikitext_names"], 0)


if __name__ == "__main__":
    unittest.main()
