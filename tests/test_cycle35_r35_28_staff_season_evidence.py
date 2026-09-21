"""R35-28 (Cycle #35 continuation, 20260921T055921Z), section 3.

"For each confirmed current staff episode, inspect the source's staff-season
label... Bind the season only when supported. Keep genuinely unspecified
episodes unspecified... Do not simply assign all `CURRENT` episodes to 2026."

Every case below is one a looser first version got wrong. It allowed up to
three arbitrary words between a year and "staff", which matched biography
prose and other sports' headings, and it bound three captures to 2019, 2022
and 2025 on that basis -- wrong seasons that would have been written into the
release as evidenced facts. They were caught only by reading the non-2026
results by hand, which is why each is pinned here.
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

from r35_28_staff_season_evidence import (  # noqa: E402
    AMBIGUOUS,
    BOUND,
    NO_EVIDENCE,
    STAFF_LABEL,
    find_labels,
    names_another_sport,
    season_evidence,
)

REAL_ARTIFACT = (
    Path("C:/BatteredAggieSyndrome.data/ops/cycle35/runs")
    / "20260921T055921Z_implementation"
    / "CYCLE35_STAFF_SEASON_EVIDENCE.json"
)


def capture(root: Path, body: str) -> Path:
    path = root / "capture.html"
    path.write_text(body, encoding="utf-8")
    return path


class LabelPatternTests(unittest.TestCase):
    def test_real_season_labels_are_recognised(self) -> None:
        for text in (
            "2026 Football Staff",
            "2026 Football Coaching Staff",
            "2026 Coaching Staff",
            "2026 Staff Directory",
            "2026 Football Staff Directory",
        ):
            with self.subTest(text=text):
                self.assertIsNotNone(STAFF_LABEL.search(text))

    def test_biography_prose_is_not_a_season_label(self) -> None:
        """"...since 2019 on staff" bound a whole capture to 2019 before the
        pattern was tightened."""
        for text in (
            "2019 on staff",
            "joined the staff in 2019",
            "has been on staff since 2019",
            "2022 University of Miami staff",
        ):
            with self.subTest(text=text):
                self.assertIsNone(STAFF_LABEL.search(text))

    def test_another_sports_heading_is_not_football_season_evidence(self) -> None:
        """These sites host every sport. A women's basketball heading says
        nothing about the football staff season."""
        body = "<h2>2025 Women's Basketball Coaching Staff</h2>"
        self.assertEqual(find_labels(body, STAFF_LABEL, "STAFF_SEASON_LABEL"), [])
        self.assertTrue(names_another_sport(body, body.index("2025"), body.index("2025") + 4))

    def test_a_football_heading_is_not_suppressed_by_a_distant_other_sport(
        self,
    ) -> None:
        body = "<h2>2026 Football Staff</h2>" + ("x" * 500) + "<h2>2025 Baseball Staff</h2>"
        found = find_labels(body, STAFF_LABEL, "STAFF_SEASON_LABEL")
        self.assertEqual([f["season"] for f in found], [2026])

    def test_a_year_outside_the_plausible_range_is_ignored(self) -> None:
        self.assertEqual(
            find_labels("1999 Coaching Staff", STAFF_LABEL, "STAFF_SEASON_LABEL"), []
        )


class SeasonEvidenceTests(unittest.TestCase):
    def test_a_unanimous_label_binds(self) -> None:
        with TemporaryDirectory() as tmp:
            path = capture(Path(tmp), "<h1>2026 Football Staff</h1><p>2026 Coaching Staff</p>")
            record = season_evidence(path)
        self.assertEqual(record["state"], BOUND)
        self.assertEqual(record["bound_season"], 2026)
        self.assertIn("not from when it was retrieved", record["detail"])

    def test_disagreeing_labels_bind_nothing_and_report_their_shape(self) -> None:
        """Both real ambiguous captures show one year twice near the top and
        another once far later. The shape is recorded; the choice is not
        made, because deciding from layout is a guess about the page."""
        with TemporaryDirectory() as tmp:
            body = (
                "<h1>2026 Football Staff</h1>" + ("x" * 400)
                + "<h2>2026 Football Staff</h2>" + ("y" * 400)
                + "<p>joined the 2019 coaching staff</p>"
            )
            record = season_evidence(capture(Path(tmp), body))
        self.assertEqual(record["state"], AMBIGUOUS)
        self.assertIsNone(record["bound_season"])
        shape = record["disagreement_shape"]
        self.assertEqual(shape["2026"]["matches"], 2)
        self.assertEqual(shape["2019"]["matches"], 1)
        self.assertGreater(shape["2019"]["first_offset"], shape["2026"]["last_offset"])

    def test_a_capture_with_no_label_stays_unspecified(self) -> None:
        with TemporaryDirectory() as tmp:
            record = season_evidence(capture(Path(tmp), "<h1>Coaches</h1><p>Bob Smith</p>"))
        self.assertEqual(record["state"], NO_EVIDENCE)
        self.assertIsNone(record["bound_season"])
        self.assertIn("retrieval time cannot supply one", record["detail"])

    def test_a_roster_year_never_substitutes_for_a_staff_label(self) -> None:
        """A page can carry a 2026 roster beside a staff list it never dates.
        Corroboration is reported, but it does not bind."""
        with TemporaryDirectory() as tmp:
            record = season_evidence(
                capture(Path(tmp), "<h1>Coaches</h1><p>2026 Football Roster</p>")
            )
        self.assertEqual(record["state"], NO_EVIDENCE)
        self.assertIsNone(record["bound_season"])
        self.assertEqual(record["corroboration"]["roster_label_years"], [2026])

    def test_an_unreadable_capture_is_not_treated_as_unlabelled(self) -> None:
        record = season_evidence(Path("C:/no/such/capture.html"))
        self.assertEqual(record["state"], "CAPTURE_UNREADABLE")
        self.assertIsNone(record["bound_season"])


class RealExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        if not REAL_ARTIFACT.is_file():
            self.skipTest("the season evidence artifact has not been generated")
        self.result = json.loads(REAL_ARTIFACT.read_text(encoding="utf-8"))

    def test_no_capture_is_bound_to_a_season_by_retrieval_time(self) -> None:
        """Every binding must come from a label the page carries. The three
        bindings the loose pattern produced -- 2019, 2022, 2025 -- were all
        prose or another sport, and none survives."""
        for raw, ev in self.result["evidence"].items():
            if ev.get("bound_season") is None:
                continue
            with self.subTest(capture=raw[-24:]):
                self.assertTrue(ev["staff_label_matches"])
                self.assertEqual(ev["staff_label_years"], [ev["bound_season"]])

    def test_captures_without_evidence_stay_unbound(self) -> None:
        unbound = [
            ev
            for ev in self.result["evidence"].values()
            if ev["state"] in (NO_EVIDENCE, AMBIGUOUS)
        ]
        self.assertTrue(unbound)
        for ev in unbound:
            self.assertIsNone(ev["bound_season"])

    def test_the_states_account_for_every_capture(self) -> None:
        states = self.result["captures_by_state"]
        self.assertEqual(sum(states.values()), self.result["distinct_captures"])
        rows = self.result["rebuild_rows_by_capture_state"]
        self.assertEqual(sum(rows.values()), self.result["rebuild_row_count"])


if __name__ == "__main__":
    unittest.main()
