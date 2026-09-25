"""R35-25 (Cycle #35 closeout review, 20260921T025300Z), section 7:
"...produce a single entry point, updated final report, requirement/finding
dispositions, national coverage, source manifest, plan/Jira trace and
validation accounting. Avoid self-referential hash claims; finalize children
before sealing their parent manifest."
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_25_single_entry_point import (  # noqa: E402
    SECTIONS,
    STATUS,
    build,
    newest_by_name,
    resolve_sections,
)

REAL_ENTRY_POINT = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
    / "20260921T025300Z_closeout"
    / "CYCLE35_SINGLE_ENTRY_POINT.json"
)


def populate(root: Path, names: list[str], *, directory: str = "run") -> None:
    target = root / directory
    target.mkdir(parents=True, exist_ok=True)
    for name in names:
        (target / name).write_text(f"content of {name}", encoding="utf-8")


class IndexTests(unittest.TestCase):
    def test_the_newest_copy_of_a_name_wins(self) -> None:
        """A tool re-run into a new directory must not leave the entry point
        pointing at the superseded copy."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            populate(root, ["A.json"], directory="old")
            populate(root, ["A.json"], directory="new")
            new_path = root / "new" / "A.json"
            import os

            os.utime(new_path, (2_000_000_000, 2_000_000_000))
            index = newest_by_name(root)
        self.assertEqual(index["A.json"], new_path)

    def test_vendored_trees_are_not_indexed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            populate(root, ["A.json"], directory="run/wheel_venv/Lib/site-packages")
            index = newest_by_name(root)
        self.assertNotIn("A.json", index)


class SectionResolutionTests(unittest.TestCase):
    def test_a_missing_required_artifact_is_reported_not_omitted(self) -> None:
        """A short report and a complete one must not look alike."""
        resolved = resolve_sections({})
        self.assertEqual(
            len(resolved["missing_required"]),
            sum(1 for _, _, required in SECTIONS if required),
        )
        for section in resolved["sections"].values():
            self.assertEqual(section["state"], "MISSING")
            self.assertIsNotNone(section["artifact"])

    def test_a_bound_section_carries_a_path_and_a_digest(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            name = SECTIONS[0][1]
            populate(root, [name])
            resolved = resolve_sections(newest_by_name(root))
            section = resolved["sections"][SECTIONS[0][0]]
            self.assertEqual(section["state"], "BOUND")
            self.assertEqual(
                section["sha256"],
                hashlib.sha256((root / "run" / name).read_bytes()).hexdigest(),
            )

    def test_every_section_name_is_unique(self) -> None:
        keys = [key for key, _, _ in SECTIONS]
        self.assertEqual(len(keys), len(set(keys)))


class BuildTests(unittest.TestCase):
    def test_an_incomplete_entry_point_says_so(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            populate(root, [SECTIONS[0][1]])
            result = build(root)
        self.assertFalse(result["complete"])
        self.assertTrue(result["missing_required"])
        self.assertEqual(result["bound_count"], 1)

    def test_a_complete_entry_point_binds_every_section(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            populate(root, [name for _, name, _ in SECTIONS])
            result = build(root)
        self.assertTrue(result["complete"])
        self.assertEqual(result["bound_count"], len(SECTIONS))
        self.assertEqual(result["missing_required"], [])

    def test_the_status_is_not_upgraded_by_completeness(self) -> None:
        """Binding every artifact says the artifacts exist. It says nothing
        about whether the work they describe was accepted."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            populate(root, [name for _, name, _ in SECTIONS])
            result = build(root)
        self.assertEqual(result["status"], STATUS)
        self.assertEqual(result["status"], "IN_PROGRESS_LOCAL_WORK_REMAINS")

    def test_the_forbidden_actions_are_enumerated_not_summarised(self) -> None:
        with TemporaryDirectory() as tmp:
            result = build(Path(tmp))
        not_authorized = result["authorization"]["not_authorized"]
        for action in (
            "merge",
            "canonical activation",
            "C01 self-adoption",
            "protected-lane activation",
            "paid AI/API review or new subscription",
            "Done transition",
            "hold release",
            "BAT-523 completion",
            "force-push",
            "secret disclosure",
            "dirty All-22 mutation",
            "scientific acceptance",
        ):
            self.assertIn(action, not_authorized)


class SealingTests(unittest.TestCase):
    def test_the_entry_point_does_not_hash_itself(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "cycle"
            out = Path(tmp) / "out"
            populate(root, [name for _, name, _ in SECTIONS])
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "cycle35" / "r35_25_single_entry_point.py"),
                    "--cycle-root", str(root),
                    "--out-dir", str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            entry = out / "CYCLE35_SINGLE_ENTRY_POINT.json"
            own = hashlib.sha256(entry.read_bytes()).hexdigest()
            self.assertNotIn(own, entry.read_text(encoding="utf-8"))
            sidecar = (out / "CYCLE35_SINGLE_ENTRY_POINT.sha256").read_text(
                encoding="utf-8"
            )
            self.assertTrue(sidecar.startswith(own))

    def test_an_incomplete_entry_point_exits_non_zero(self) -> None:
        """An entry point missing a required section is not a usable entry
        point, and a pipeline must be able to notice."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "cycle"
            root.mkdir()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "cycle35" / "r35_25_single_entry_point.py"),
                    "--cycle-root", str(root),
                    "--out-dir", str(Path(tmp) / "out"),
                ],
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 1)


class RealEntryPointTests(unittest.TestCase):
    def setUp(self) -> None:
        if not REAL_ENTRY_POINT.is_file():
            self.skipTest("the entry point has not been sealed")
        self.result = json.loads(REAL_ENTRY_POINT.read_text(encoding="utf-8"))

    def test_every_bound_artifact_still_matches_its_recorded_digest(self) -> None:
        """A digest that no longer matches means a child was rewritten after
        the parent was sealed."""
        for key, section in self.result["sections"].items():
            if section["state"] != "BOUND":
                continue
            path = Path(section["path"])
            with self.subTest(section=key):
                self.assertTrue(path.is_file(), path)
                self.assertEqual(
                    section["sha256"],
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )

    def test_the_real_entry_point_is_complete(self) -> None:
        self.assertTrue(self.result["complete"])
        self.assertEqual(self.result["missing_required"], [])

    def test_the_real_entry_point_still_carries_the_hold(self) -> None:
        self.assertEqual(self.result["status"], "IN_PROGRESS_LOCAL_WORK_REMAINS")


if __name__ == "__main__":
    unittest.main()
