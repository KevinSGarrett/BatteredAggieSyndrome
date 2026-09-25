"""The independent season reader must disagree with a wrong producer.

A checker that agrees with everything proves nothing. These tests feed it
records whose recorded season is right, wrong, absent and unlocatable, and
require a distinct state for each. They also pin the property that makes the
checker independent: it imports nothing from the producer module.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_SPEC = importlib.util.spec_from_file_location(
    "c36_independent_season_review",
    ROOT / "tools" / "cycle36" / "c36_03_independent_season_review.py",
)
reader = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(reader)

PAGE = (
    "<html><body>"
    "<h1>2026 Football Coaching Staff</h1>"
    "<table><tr><td>A Person</td><td>Head Coach</td></tr></table>"
    "<h1>2025 Football Coaching Staff</h1>"
    "<table><tr><td>B Person</td><td>Head Coach</td></tr></table>"
    "</body></html>"
)
HIDDEN = (
    "<html><body>"
    "<!-- 2026 Football Coaching Staff -->"
    '<script>var t="2026 Football Coaching Staff";</script>'
    "<table><tr><td>A Person</td></tr></table>"
    "</body></html>"
)


def offset(needle: str, page: str = PAGE) -> int:
    return page.index(needle)


class ReaderTests(unittest.TestCase):
    def test_agrees_with_a_correct_season(self) -> None:
        result = reader.check_record(PAGE, offset("A Person"), 2026)
        self.assertEqual(result["state"], reader.AGREES)
        self.assertEqual(result["reader_season"], 2026)

    def test_disagrees_with_a_wrong_season(self) -> None:
        result = reader.check_record(PAGE, offset("A Person"), 2025)
        self.assertEqual(result["state"], reader.DISAGREES_SEASON)
        self.assertEqual(result["reader_season"], 2026)

    def test_each_section_dates_its_own_records(self) -> None:
        self.assertEqual(
            reader.check_record(PAGE, offset("B Person"), 2025)["state"],
            reader.AGREES,
        )
        self.assertEqual(
            reader.check_record(PAGE, offset("B Person"), 2026)["state"],
            reader.DISAGREES_SEASON,
        )

    def test_a_year_only_in_a_comment_or_script_is_not_a_heading(self) -> None:
        result = reader.check_record(HIDDEN, offset("A Person", HIDDEN), 2026)
        self.assertEqual(result["state"], reader.DISAGREES_UNBOUND)
        self.assertIsNone(result["reader_season"])

    def test_both_unbound_agrees_about_the_absence(self) -> None:
        result = reader.check_record(HIDDEN, offset("A Person", HIDDEN), None)
        self.assertEqual(result["state"], reader.BOTH_UNBOUND)

    def test_the_reader_reports_when_it_finds_what_the_producer_missed(self) -> None:
        result = reader.check_record(PAGE, offset("A Person"), None)
        self.assertEqual(result["state"], reader.PRODUCER_UNBOUND_READER_FINDS)
        self.assertEqual(result["reader_season"], 2026)

    def test_a_record_with_no_offset_is_not_checkable(self) -> None:
        self.assertEqual(
            reader.check_record(PAGE, None, 2026)["state"], reader.NOT_CHECKABLE
        )

    def test_masking_preserves_offsets(self) -> None:
        masked = reader.masked(HIDDEN)
        self.assertEqual(len(masked), len(HIDDEN))
        self.assertEqual(masked.index("A Person"), HIDDEN.index("A Person"))
        self.assertNotIn("2026", masked)

    def test_it_imports_nothing_from_the_producer(self) -> None:
        """The docstring may NAME the producer; the code may not import it."""

        source = (
            ROOT / "tools" / "cycle36" / "c36_03_independent_season_review.py"
        ).read_text(encoding="utf-8")
        imports = [
            line
            for line in source.splitlines()
            if line.startswith(("import ", "from "))
        ]
        self.assertFalse(
            [line for line in imports if "aggie_analytics" in line],
            imports,
        )

    def test_strata_separate_core_from_non_core_and_unmapped(self) -> None:
        core = reader.stratum(
            {"classification": "fbs", "role_codes": ["head_coach"], "page_url": "https://teams.vendor-one.test/x"}
        )
        other = reader.stratum(
            {"classification": "fbs", "role_codes": ["quarterbacks"], "page_url": "https://teams.vendor-one.test/x"}
        )
        unmapped = reader.stratum(
            {
                "classification": "fcs",
                "role_codes": ["unmapped_title_review_required"],
                "page_url": "https://teams.vendor-two.test/x",
            }
        )
        self.assertEqual(core[1], "CORE")
        self.assertEqual(other[1], "NON_CORE")
        self.assertEqual(unmapped[1], "UNMAPPED")
        # The platform key is the host's second-level label, which is what
        # identifies the site vendor these athletics pages are built on.
        self.assertEqual(core[2], "vendor-one")
        self.assertEqual(unmapped[2], "vendor-two")


class DecodingContractTests(unittest.TestCase):
    """Both readers must decode from bytes, or every offset is a lie.

    A capture with CRLF line endings loses one character per line through
    ``read_text`` on Windows. That shifted 78 records past the heading that
    governs them and produced 78 disagreements that belonged to the reader.
    """

    def setUp(self) -> None:
        import tempfile

        self.holder = tempfile.TemporaryDirectory()
        self.path = Path(self.holder.name) / "capture.html"
        crlf = (
            "<html>\r\n<body>\r\n"
            + "<p>padding</p>\r\n" * 200
            + "<h1>2026 Football Coaching Staff</h1>\r\n"
            + "<table><tr><td>A Person</td></tr></table>\r\n"
            + "</body>\r\n</html>\r\n"
        )
        self.path.write_bytes(crlf.encode("utf-8"))

    def tearDown(self) -> None:
        self.holder.cleanup()

    def test_read_text_shifts_offsets_and_read_bytes_does_not(self) -> None:
        from_bytes = self.path.read_bytes().decode("utf-8", errors="replace")
        through_text = self.path.read_text(encoding="utf-8", errors="replace")
        self.assertGreater(len(from_bytes), len(through_text))
        self.assertNotEqual(
            from_bytes.index("A Person"), through_text.index("A Person")
        )

    def test_the_reader_agrees_when_it_decodes_like_the_producer(self) -> None:
        from_bytes = self.path.read_bytes().decode("utf-8", errors="replace")
        offset = from_bytes.index("A Person")
        self.assertEqual(
            reader.check_record(from_bytes, offset, 2026)["state"], reader.AGREES
        )

    def test_a_translated_decode_would_report_a_false_disagreement(self) -> None:
        from_bytes = self.path.read_bytes().decode("utf-8", errors="replace")
        through_text = self.path.read_text(encoding="utf-8", errors="replace")
        producer_offset = from_bytes.index("A Person")
        # The producer's offset read against the translated document points
        # past the heading's governed span.
        self.assertNotEqual(
            reader.check_record(through_text, producer_offset, 2026)["state"],
            reader.AGREES,
        )

    def test_the_tool_decodes_from_bytes(self) -> None:
        source = (
            ROOT / "tools" / "cycle36" / "c36_03_independent_season_review.py"
        ).read_text(encoding="utf-8")
        self.assertIn('read_bytes().decode("utf-8", errors="replace")', source)
        self.assertNotIn(
            'path.read_text(encoding="utf-8", errors="replace")', source
        )



class EveryLabelledRowIsCheckedTests(unittest.TestCase):
    """Coverage is over what the binder labelled, not over one evidence tier.

    The evidence tier records whether the CAPTURE matched a declared
    acquisition receipt. It says nothing about where the season came from.
    A first version of the checker selected only OFFICIAL_HTML_RECORD_BOUND
    and so read 5,123 of 16,428 labelled rows, leaving two thirds of every
    bound season unchecked while the artifact said "every admitted
    season-support tuple".
    """

    def _rows(self, tmp: Path) -> Path:
        capture = tmp / "capture.html"
        capture.write_bytes(PAGE.encode("utf-8"))
        offset = PAGE.index("A Person")
        rows = [
            {
                "evidence_tier": "OFFICIAL_HTML_RECORD_BOUND",
                "capture_path": str(capture),
                "person_body_offset": offset,
                "season": 2026,
                "season_parser_version": "BAS-SOURCE-SCOPED-SEASON-v36.1",
                "page_url": "https://example.edu/staff",
            },
            {
                "evidence_tier": "CANDIDATE_FROM_UNBOUND_CAPTURE",
                "capture_path": str(capture),
                "person_body_offset": offset,
                "season": 2026,
                "season_parser_version": "BAS-SOURCE-SCOPED-SEASON-v36.1",
                "page_url": "cache://deadbeef",
            },
            {
                "evidence_tier": "CANDIDATE_FROM_UNBOUND_CAPTURE",
                "capture_path": str(capture),
                "person_body_offset": None,
                "season": None,
                "season_parser_version": "BAS-SOURCE-SCOPED-SEASON-v36.1",
                "page_url": "cache://deadbeef",
            },
            {
                "evidence_tier": "CANDIDATE_FROM_UNBOUND_CAPTURE",
                "capture_path": str(capture),
                "person_body_offset": offset,
                "season": 2026,
                "season_parser_version": None,
                "page_url": "cache://deadbeef",
            },
        ]
        path = tmp / "rows.jsonl"
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        return path

    def test_candidate_tier_rows_are_read_too(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            artifact = reader.build(tmp / "out", self._rows(tmp), 1)
        # Three rows carry a parser version; the fourth does not and is not
        # this checker's business.
        self.assertEqual(artifact["rows_the_binder_labelled"], 3)
        self.assertEqual(artifact["rows_examined"], 3)
        self.assertTrue(artifact["every_labelled_row_examined"])
        tiers = artifact["states_by_evidence_tier"]
        self.assertIn("CANDIDATE_FROM_UNBOUND_CAPTURE", tiers)
        self.assertEqual(
            tiers["CANDIDATE_FROM_UNBOUND_CAPTURE"][reader.AGREES], 1
        )
        self.assertEqual(tiers["OFFICIAL_HTML_RECORD_BOUND"][reader.AGREES], 1)

    def test_a_row_without_an_offset_is_counted_not_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            artifact = reader.build(tmp / "out", self._rows(tmp), 1)
        self.assertEqual(artifact["rows_not_comparable"], 1)
        self.assertEqual(artifact["rows_compared"], 2)
        self.assertEqual(artifact["states"][reader.NOT_CHECKABLE], 1)
        # It must never reach the human-readable sample: it has no excerpt.
        self.assertTrue(
            all(
                row["state"] != reader.NOT_CHECKABLE
                for row in artifact["stratified_sample"]
            )
        )

    def test_a_capture_without_a_url_is_not_given_an_invented_platform(self) -> None:
        self.assertEqual(
            reader.stratum({"page_url": "cache://deadbeef"})[2],
            "CAPTURE_WITHOUT_A_RECORDED_URL",
        )

    def test_the_manager_season_cases_are_carried(self) -> None:
        cases = reader.manager_season_cases()
        self.assertEqual(cases["case_count"], 5)
        self.assertTrue(
            cases["independent_reader_agrees_with_every_manager_expectation"]
        )
        wrong = [c for c in cases["cases"] if c["cycle35_producer_was_wrong"]]
        self.assertEqual(len(wrong), 4)


if __name__ == "__main__":
    unittest.main()
