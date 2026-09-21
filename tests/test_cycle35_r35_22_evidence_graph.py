"""R35-22 (Cycle #35 closeout review, 20260921T025300Z), section 7:
"Generate one coherent current evidence graph across run directories...
Resolve every evidence reference to a real path/hash... The current packet
has 26 unfinished entries, 22 labeled local, yet lists only five owner
decisions as if no local work remained. Some entries are stale and others
remain real. Reconcile each entry with delivered evidence; do not simply
delete the list or relabel its contents."
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_22_evidence_graph import (  # noqa: E402
    CATEGORY_DATA_GAP,
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

    def test_an_entry_is_only_called_stale_when_evidence_contradicts_it(self) -> None:
        item = {
            "requirement": "R35-03",
            "kind": "LOCAL_WORK_REMAINING",
            "blocker": "The corpus covers 2000-2012 only; 2013-2026 user rows are not cell-ingested.",
        }
        # With no delivered release to check, it must NOT be called stale.
        unchecked = reconcile_items([dict(item)], self.EMPTY_INDEX, {"queried": False})
        self.assertNotEqual(unchecked[0]["category"], CATEGORY_STALE)

        # With a release that actually carries the rows, it is stale.
        checked = reconcile_items(
            [dict(item)],
            self.EMPTY_INDEX,
            {"queried": True, "database": "x.sqlite", "observations_2013_2026": 86105},
        )
        self.assertEqual(checked[0]["category"], CATEGORY_STALE)
        self.assertIn("86,105", checked[0]["finding"])

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
