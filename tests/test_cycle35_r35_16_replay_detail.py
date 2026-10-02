"""Cycle #35 continuation (20260921T055921Z), section 5.

The replay lane's detail used to be hardcoded prose ending "(26 of 26
rows)". After the decision-time repair the replay finds zero differences, so
that sentence became false -- and false in the direction that matters, since
a packet reporting a divergence that no longer exists misleads exactly as
much as one hiding a divergence that does.

r35_14 already states the principle: "A lane that states a result no longer
checks it." These tests hold the replay lane to it. The detail must change
when the artifact changes, must report absence as absence, and must never
drop the sentence explaining that the column is still compared -- because
"zero differences" is only meaningful if something is still looking.
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

from r35_16_validation_packet_successor import replay_detail  # noqa: E402


def artifact(tmp: str, payload: dict) -> Path:
    path = Path(tmp) / "CYCLE35_DETERMINISTIC_RELEASE_REPLAY.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


IDENTICAL = {
    "tables_compared": [f"t{n}" for n in range(15)],
    "comparison": {"difference_count": 0, "column_level_diffs": []},
}

DIFFERING = {
    "tables_compared": [f"t{n}" for n in range(15)],
    "comparison": {
        "difference_count": 1,
        "column_level_diffs": [
            {"table": "adjudication", "columns_differing": {"decided_at_utc": 26}}
        ],
    },
}


class DerivedDetailTests(unittest.TestCase):
    def test_an_identical_replay_reports_zero_differences(self) -> None:
        with TemporaryDirectory() as tmp:
            detail = replay_detail(artifact(tmp, IDENTICAL))
        self.assertIn("IDENTICAL", detail)
        self.assertIn("15 content tables", detail)
        self.assertNotIn("26 of 26", detail)

    def test_a_differing_replay_names_the_column_and_the_row_count(self) -> None:
        """The lane must still be able to go red, and say what differed."""

        with TemporaryDirectory() as tmp:
            detail = replay_detail(artifact(tmp, DIFFERING))
        self.assertIn("adjudication.decided_at_utc differs on 26 rows", detail)
        self.assertIn("1 difference", detail)
        self.assertNotIn("IDENTICAL", detail)

    def test_the_detail_changes_with_the_artifact(self) -> None:
        with TemporaryDirectory() as tmp:
            first = replay_detail(artifact(tmp, IDENTICAL))
            second = replay_detail(artifact(tmp, DIFFERING))
        self.assertNotEqual(first, second)

    def test_an_absent_artifact_reports_its_absence(self) -> None:
        detail = replay_detail(Path("no") / "such" / "file.json")
        self.assertIn("NOT RUN AT THIS HEAD", detail)
        self.assertNotIn("IDENTICAL", detail)

    def test_an_unreadable_artifact_establishes_nothing(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{not json", encoding="utf-8")
            detail = replay_detail(path)
        self.assertIn("establishes nothing", detail)


class ExclusionNoteTests(unittest.TestCase):
    """Zero differences only means something if the column is still compared."""

    def test_every_branch_says_the_column_is_still_compared(self) -> None:
        with TemporaryDirectory() as tmp:
            details = [
                replay_detail(artifact(tmp, IDENTICAL)),
                replay_detail(artifact(tmp, DIFFERING)),
                replay_detail(Path(tmp) / "absent.json"),
            ]
        for detail in details:
            self.assertIn("INCIDENTAL_EXCLUDED_COLUMNS stays empty", detail)

    def test_the_zero_is_attributed_to_the_repair_not_to_an_exclusion(self) -> None:
        with TemporaryDirectory() as tmp:
            detail = replay_detail(artifact(tmp, IDENTICAL))
        self.assertIn("not because the comparison stopped looking", detail)

    def test_differing_file_bytes_are_explained_rather_than_claimed_as_a_defect(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            detail = replay_detail(artifact(tmp, IDENTICAL))
        self.assertIn("SQLite page layout is not a scientific fact", detail)
        self.assertIn("schema_migration.applied_at_utc", detail)


if __name__ == "__main__":
    unittest.main()
