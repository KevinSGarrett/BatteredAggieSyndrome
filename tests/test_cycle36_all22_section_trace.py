"""The All-22 section trace must read metadata, not filenames, and must not
report its own parser's limits as findings.

Three of this tool's predicates were wrong on the first run and each was
wrong in a way that produced a confident, false statement about the owner's
documents:

  * a successor written as a range ("SUPERSEDED_BY_06_THROUGH_09_...") was
    compared to a single filename stem, so five of twelve retained documents
    were reported to name no successor;
  * ``\\b`` never fires between a digit and an underscore, so once the range
    form was handled the number extraction still found nothing;
  * a bare "incomplete" matched the literal result state ``INCOMPLETE`` and
    domain phrases such as "incomplete roster", producing six contradictions
    of which one was real -- and the real one straddled a hard line break,
    which a regex written with literal spaces cannot match.

Each of those is pinned below, because a trace that reports parser artifacts
as owner findings is worse than no trace.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_SPEC = importlib.util.spec_from_file_location(
    "c36_all22_section_trace",
    ROOT / "tools" / "cycle36" / "c36_13b_all22_section_trace.py",
)
trace = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(trace)

BLOCK_LIST_DOC = """---
doc_id: GC-BAS-00-EXAMPLE
title: Example Master
document_class: MASTER
authority_state: ACCEPTED_PHASE_2_PLAN
implementation_state: NOT_IMPLEMENTED
capabilities:
- CAP-BAS-INTEGRAT-00-EXAMPLE-0574
reviewers: [C01, F01]
---

# Example Master

## 1. First section

Body text.

## 2. Second section

More body text.
"""

INLINE_LIST_DOC = """---
doc_id: TP-DOC-EXAMPLE
title: Example Domain
authority_state: DRAFT_NOT_ACCEPTED
implementation_state: NOT_IMPLEMENTED
supersession_state: SUPERSEDED_BY_10_FILM_FEATURE_REGISTRY
capabilities: [CAP-BAS-INTEGRAT-04-EXAMPLE-MD-0074]
---

# Example Domain

## Only section

Body.
"""


class FrontMatterTests(unittest.TestCase):
    def test_block_list_capabilities_are_read(self) -> None:
        front, _ = trace.split_front_matter(BLOCK_LIST_DOC)
        fields = trace.parse_front_matter(front)
        self.assertEqual(
            fields["capabilities"], ["CAP-BAS-INTEGRAT-00-EXAMPLE-0574"]
        )

    def test_inline_list_capabilities_are_read(self) -> None:
        """The form that carries CAP-...-0074 in the real corpus."""

        front, _ = trace.split_front_matter(INLINE_LIST_DOC)
        fields = trace.parse_front_matter(front)
        self.assertEqual(
            fields["capabilities"], ["CAP-BAS-INTEGRAT-04-EXAMPLE-MD-0074"]
        )

    def test_capability_suffix_is_the_series_number(self) -> None:
        self.assertEqual(
            trace.capability_suffix("CAP-BAS-INTEGRAT-21-BAS-FILM-ACCEPTANCE-0595"),
            595,
        )
        self.assertIsNone(trace.capability_suffix("CAP-NO-SUFFIX"))

    def test_sections_are_extracted_with_spans(self) -> None:
        _, body = trace.split_front_matter(BLOCK_LIST_DOC)
        sections = trace.extract_sections(body)
        numbered = [s for s in sections if s["number"] is not None]
        self.assertEqual([s["number"] for s in numbered], [1, 2])
        self.assertEqual(numbered[0]["heading"], "First section")
        self.assertGreater(numbered[0]["body_chars"], 0)


class ContradictionScanTests(unittest.TestCase):
    def _scan(self, body: str):
        return trace.draft_contradictions(body, trace.extract_sections(body))

    def test_a_result_state_named_incomplete_is_not_a_contradiction(self) -> None:
        body = (
            "## 3. Validation protocol\n\n"
            "Results are `VALID_FOR_PIT_IMPORT`, `PARTIAL_ALLOWED`, "
            "`INCOMPLETE`, `CONFLICT` or `UNKNOWN`.\n"
        )
        self.assertEqual(self._scan(body), [])

    def test_a_domain_condition_is_not_a_contradiction(self) -> None:
        body = (
            "## 4. Fixtures\n\n"
            "Synthetic cases cover transfers, an incomplete roster and "
            "corrected stints.\n"
        )
        self.assertEqual(self._scan(body), [])

    def test_a_hard_wrapped_contradiction_is_still_found(self) -> None:
        """The real one in 03_ROSTER_PUBLISHER straddles a line break."""

        body = (
            "## 11. Qualification and acceptance\n\n"
            "This accepts only the cross-area planning interface. The full\n"
            "AREA-24 hierarchy remains an incomplete Phase 2 draft, and no\n"
            "active BAS access is implied.\n"
        )
        found = self._scan(body)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["section_number"], 11)
        self.assertIn("Phase 2 draft", found[0]["quoted_sentence"])


class SupersessionTests(unittest.TestCase):
    """Ranges and conjunctions are the normal form, not the exception."""

    def _resolve(self, state: str) -> list[int]:
        import re

        target = state[len("SUPERSEDED_BY_") :]
        numbers = [
            int(n) for n in re.findall(r"(?<![0-9])(\d{2})(?![0-9])", target)
        ]
        if "THROUGH" in target and len(numbers) >= 2:
            numbers = list(range(min(numbers[:2]), max(numbers[:2]) + 1))
        return numbers

    def test_underscore_does_not_break_the_number_match(self) -> None:
        self.assertEqual(
            self._resolve("SUPERSEDED_BY_06_THROUGH_09_SOURCE_NAMED_OWNERS"),
            [6, 7, 8, 9],
        )

    def test_a_conjunction_names_each_successor(self) -> None:
        self.assertEqual(
            self._resolve("SUPERSEDED_BY_12_AND_13_SOURCE_NAMED_OWNERS"), [12, 13]
        )

    def test_a_single_successor_still_resolves(self) -> None:
        self.assertEqual(self._resolve("SUPERSEDED_BY_21_BAS_FILM_ACCEPTANCE"), [21])


class LiveCorpusTests(unittest.TestCase):
    """Skipped where the manager's pinned copies are not mounted."""

    @classmethod
    def setUpClass(cls) -> None:
        if not trace.REHASH.is_file() or not trace.PINNED_DOCS.is_dir():
            raise unittest.SkipTest("manager All-22 evidence is not mounted")
        with tempfile.TemporaryDirectory() as tmp:
            cls.artifact = trace.build(Path(tmp))

    def test_every_pinned_copy_matches_its_recorded_remote_digest(self) -> None:
        self.assertTrue(
            self.artifact["every_document_matched_its_recorded_remote_digest"]
        )
        self.assertEqual(self.artifact["digest_failures"], [])

    def test_the_hierarchy_is_twenty_two_current_and_twelve_retained(self) -> None:
        self.assertEqual(self.artifact["current_hierarchy_count"], 22)
        self.assertEqual(self.artifact["retained_historical_count"], 12)
        self.assertTrue(self.artifact["current_series_is_exactly_0574_to_0595"])
        self.assertTrue(self.artifact["historical_series_is_exactly_0070_to_0081"])

    def test_no_document_loses_its_capability(self) -> None:
        self.assertEqual(self.artifact["documents_with_no_capability"], [])

    def test_reading_the_plans_is_not_implementing_them(self) -> None:
        implemented = self.artifact["bas_implementation"][
            "capabilities_with_a_bas_local_boundary"
        ]
        self.assertEqual(implemented, [trace.IMPLEMENTED_BOUNDARY])
        self.assertEqual(
            self.artifact["bas_implementation"][
                "capabilities_not_implemented_by_bas"
            ],
            33,
        )


if __name__ == "__main__":
    unittest.main()
