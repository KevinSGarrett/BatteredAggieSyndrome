"""R35-24 (Cycle #35 closeout review, 20260921T025300Z), section 7:
"Complete the originally required source-span/semantic review with independent
labels and positive/negative controls. Author-side secondary checks do not
confer manager scientific acceptance. If a clause explicitly requires an
independent owner/reviewer decision, prepare its complete evidence queue
instead of relabeling every unfinished local task as external review."
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

from r35_24_source_span_review import (  # noqa: E402
    DISAGREE_NO_RECORD,
    DISAGREE_OTHER_TITLE,
    DISAGREE_UNSUPPORTED_CLAIM,
    SEMANTIC_PENDING,
    SPAN_ABSENT,
    SPAN_PRESENT,
    SPAN_UNCHECKABLE,
    build,
    disagreement_kind,
    negative_control_text,
    run_controls,
    span_verdict,
)

PAGE = (
    "<html><body><div class='staff'>"
    "<span class='name'>Ted Monachino</span>"
    "<span class='title'>Defensive Coordinator/Outside Linebackers Coach</span>"
    "</div>" + ("<p>filler paragraph for a realistic document body</p>" * 20) +
    "</body></html>"
)


def write_sample(directory: Path, rows: list[dict]) -> Path:
    path = directory / "sample.json"
    path.write_text(json.dumps({"sample": rows}), encoding="utf-8")
    return path


class SpanVerdictTests(unittest.TestCase):
    def test_a_present_string_is_located_with_an_interval(self) -> None:
        verdict = span_verdict(PAGE, "Ted Monachino")
        self.assertEqual(verdict["label"], SPAN_PRESENT)
        self.assertGreaterEqual(verdict["raw_start"], 0)
        self.assertGreater(verdict["raw_end"], verdict["raw_start"])
        self.assertIn("Ted Monachino", verdict["context"])

    def test_an_absent_string_is_reported_absent(self) -> None:
        self.assertEqual(
            span_verdict(PAGE, "Zzyzx Qvortrup-Nonexistent")["label"], SPAN_ABSENT
        )

    def test_an_unreadable_source_is_uncheckable_not_absent(self) -> None:
        """"The file could not be read" and "the string is not in the file"
        are different findings and must not collapse into one."""
        self.assertEqual(span_verdict(None, "anything")["label"], SPAN_UNCHECKABLE)


class ControlTests(unittest.TestCase):
    def test_the_negative_control_keeps_every_word_of_the_real_title(self) -> None:
        """A control that is absent because it is gibberish proves nothing. It
        has to be absent for a reason a real title would not share."""
        title = "Defensive Coordinator/Outside Linebackers Coach"
        scrambled = negative_control_text(title)
        self.assertNotEqual(scrambled, title)
        self.assertEqual(sorted(scrambled.split()), sorted(title.split()))

    def test_a_single_token_title_still_gets_an_absent_control(self) -> None:
        scrambled = negative_control_text("Coach")
        self.assertNotEqual(scrambled, "Coach")
        self.assertEqual(span_verdict(PAGE, scrambled)["label"], SPAN_ABSENT)

    def test_all_controls_pass_on_a_working_locator(self) -> None:
        controls = run_controls(
            PAGE, "Defensive Coordinator/Outside Linebackers Coach", "page.html"
        )
        self.assertTrue(all(control["passed"] for control in controls))
        self.assertEqual(
            {control["control"] for control in controls},
            {
                "POSITIVE_VERBATIM_SUBSTRING",
                "NEGATIVE_TOKEN_ORDER_SCRAMBLE",
                "NEGATIVE_ABSENT_SENTINEL_NAME",
            },
        )

    def test_an_unreadable_document_fails_its_control(self) -> None:
        controls = run_controls(None, "Head Coach", "missing.html")
        self.assertFalse(controls[0]["passed"])


class DisagreementKindTests(unittest.TestCase):
    def test_no_record_at_all_is_named_as_a_recall_gap(self) -> None:
        kind = disagreement_kind(
            {"rebuilt_record_person": None, "rebuilt_record_title": None},
            True,
            False,
        )
        self.assertEqual(kind, DISAGREE_NO_RECORD)

    def test_a_different_title_is_not_lumped_in_with_a_recall_gap(self) -> None:
        kind = disagreement_kind(
            {"rebuilt_record_person": "Ted Monachino", "rebuilt_record_title": "Other"},
            True,
            False,
        )
        self.assertEqual(kind, DISAGREE_OTHER_TITLE)

    def test_a_claim_resting_on_an_absent_span_is_its_own_finding(self) -> None:
        """This is the dangerous direction: support asserted where the bytes
        do not carry the evidence."""
        kind = disagreement_kind(
            {"rebuilt_record_person": "X", "rebuilt_record_title": "Y"}, False, True
        )
        self.assertEqual(kind, DISAGREE_UNSUPPORTED_CLAIM)

    def test_agreement_produces_no_kind(self) -> None:
        self.assertIsNone(disagreement_kind({}, True, True))
        self.assertIsNone(disagreement_kind({}, False, False))

    def test_a_row_with_no_parser_opinion_is_not_a_disagreement(self) -> None:
        self.assertIsNone(disagreement_kind({}, True, None))


class BuildTests(unittest.TestCase):
    def build_one(self, tmp: Path, **overrides) -> dict:
        page = tmp / "page.html"
        page.write_text(PAGE, encoding="utf-8")
        row = {
            "episode_key": "k1",
            "program_id": "SRC-002:TEAM:1",
            "person": "Ted Monachino",
            "source_title": "Defensive Coordinator/Outside Linebackers Coach",
            "raw_path": str(page),
            "rebuilt_role_claim_supported": True,
            "rebuilt_record_person": "Ted Monachino",
            "rebuilt_record_title": "Defensive Coordinator/Outside Linebackers Coach",
            "stratum": {"disposition": "RETAINED_SUPPORTED"},
        }
        row.update(overrides)
        return build(write_sample(tmp, [row]))

    def test_the_semantic_question_is_never_decided_here(self) -> None:
        """An author-side check cannot confer scientific acceptance, so no row
        may come back with a semantic verdict attached."""
        with TemporaryDirectory() as tmp:
            result = self.build_one(Path(tmp))
        self.assertEqual(result["semantic_review_queue"]["decided_here"], 0)
        self.assertEqual(result["semantic_review_queue"]["pending"], 1)
        self.assertEqual(result["rows"][0]["semantic_review"]["label"], SEMANTIC_PENDING)
        self.assertTrue(
            result["semantic_review_queue"][
                "author_side_checks_do_not_confer_acceptance"
            ]
        )

    def test_the_queue_carries_what_a_reviewer_needs_to_decide(self) -> None:
        with TemporaryDirectory() as tmp:
            result = self.build_one(Path(tmp))
        row = result["rows"][0]
        self.assertIsNotNone(row["raw_source"]["sha256"])
        self.assertIsNotNone(row["independent_span_label"]["person"]["raw_start"])
        self.assertIn("Ted Monachino", row["independent_span_label"]["person"]["context"])
        self.assertTrue(result["semantic_review_queue"]["queue_is_complete"])

    def test_the_span_label_does_not_come_from_the_parser(self) -> None:
        """The parser can be wrong in either direction without moving the
        independent label."""
        with TemporaryDirectory() as tmp:
            result = self.build_one(
                Path(tmp),
                rebuilt_role_claim_supported=False,
                rebuilt_record_person=None,
                rebuilt_record_title=None,
            )
        self.assertTrue(result["rows"][0]["independent_span_label"]["both_present"])
        self.assertEqual(
            result["disagreements_by_kind"], {DISAGREE_NO_RECORD: 1}
        )

    def test_a_failed_control_invalidates_the_run(self) -> None:
        """A span verdict from an instrument that cannot separate present from
        absent carries no information, so one failure fails the run."""
        with TemporaryDirectory() as tmp:
            result = self.build_one(Path(tmp), raw_path=str(Path(tmp) / "absent.html"))
        self.assertFalse(result["instrument"]["valid"])
        self.assertEqual(result["instrument"]["status"], "INVALID_CONTROLS_FAILED")
        self.assertTrue(result["instrument"]["failed_controls"])

    def test_controls_run_once_per_distinct_document_not_once_per_row(self) -> None:
        with TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_text(PAGE, encoding="utf-8")
            rows = [
                {
                    "episode_key": f"k{n}",
                    "person": "Ted Monachino",
                    "source_title": "Defensive Coordinator/Outside Linebackers Coach",
                    "raw_path": str(page),
                    "rebuilt_role_claim_supported": True,
                    "rebuilt_record_person": "Ted Monachino",
                    "rebuilt_record_title": "Defensive Coordinator/Outside Linebackers Coach",
                }
                for n in range(4)
            ]
            result = build(write_sample(Path(tmp), rows))
        self.assertEqual(result["rows_reviewed"], 4)
        self.assertEqual(result["instrument"]["documents_controlled"], 1)


class RealReviewTests(unittest.TestCase):
    ARTIFACT = (
        Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
        / "20260921T025300Z_closeout"
        / "CYCLE35_SOURCE_SPAN_SEMANTIC_REVIEW.json"
    )

    def setUp(self) -> None:
        if not self.ARTIFACT.is_file():
            self.skipTest("the source-span review has not been run")
        self.result = json.loads(self.ARTIFACT.read_text(encoding="utf-8"))

    def test_the_real_run_had_a_valid_instrument(self) -> None:
        self.assertTrue(self.result["instrument"]["valid"])
        self.assertGreater(self.result["instrument"]["control_count"], 0)

    def test_no_delivered_claim_rests_on_an_absent_span(self) -> None:
        """The direction that would matter most: support asserted where the
        raw bytes do not carry it. None were found."""
        self.assertTrue(self.result["no_claim_rests_on_an_absent_span"])
        self.assertNotIn(
            DISAGREE_UNSUPPORTED_CLAIM, self.result["disagreements_by_kind"]
        )

    def test_every_sampled_row_still_awaits_an_independent_reviewer(self) -> None:
        self.assertEqual(
            self.result["semantic_review_queue"]["pending"],
            self.result["rows_reviewed"],
        )


if __name__ == "__main__":
    unittest.main()
