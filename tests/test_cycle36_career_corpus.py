"""The career corpus must refuse for the right reason, and name the taxonomy field.

Reading the wrong key is how this tool first failed: the cycle33 taxonomy
returns ``role`` and the disposition filter read ``role_code``, so all 27,174
episodes that reached the role test looked unmapped and the corpus was
reported as carrying no usable role at all. The taxonomy in fact resolves
"OC/QB", "DC", "WR", "GA" and "head coach" perfectly well, and 15,993
episodes survive to candidate once the right field is read.

The refusal order also matters. Each episode is refused for the FIRST thing
missing -- employer, then role, then interval -- so the counts partition the
corpus instead of double-counting a row that is missing two things.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle33.role_taxonomy import (  # noqa: E402
    assignments_from_title,
)

_SPEC = importlib.util.spec_from_file_location(
    "c36_career_corpus",
    ROOT / "tools" / "cycle36" / "c36_05d_career_corpus.py",
)
corpus = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(corpus)


class TaxonomyFieldTests(unittest.TestCase):
    def test_the_taxonomy_names_the_field_role_not_role_code(self) -> None:
        assignments = assignments_from_title("head coach")
        self.assertEqual(assignments[0]["role"], "head_coach")
        self.assertNotIn("role_code", assignments[0])

    def test_the_corpus_abbreviations_resolve(self) -> None:
        """These are the titles the cached pages actually carry."""

        for title, expected in (
            ("OC/QB", "offensive_coordinator"),
            ("DC", "defensive_coordinator"),
            ("WR", "wide_receivers"),
            ("GA", "graduate_assistant"),
        ):
            with self.subTest(title=title):
                roles = [a["role"] for a in assignments_from_title(title)]
                self.assertIn(expected, roles)

    def test_an_unmapped_title_is_not_a_specific_role(self) -> None:
        roles = [a["role"] for a in assignments_from_title("UNKNOWN")]
        self.assertEqual(roles, ["unmapped_title_review_required"])


class QualifierDetectionTests(unittest.TestCase):
    """The upstream parser leaks an employer qualifier into the title."""

    def test_a_bare_state_code_is_flagged(self) -> None:
        self.assertTrue(corpus.looks_like_an_employer_qualifier("TX"))
        self.assertTrue(corpus.looks_like_an_employer_qualifier("(CA)"))

    def test_a_real_title_is_not_flagged(self) -> None:
        for title in ("head coach", "OC/QB", "defensive coordinator", "GA"):
            with self.subTest(title=title):
                self.assertFalse(corpus.looks_like_an_employer_qualifier(title))

    def test_an_empty_title_is_not_flagged(self) -> None:
        self.assertFalse(corpus.looks_like_an_employer_qualifier(""))
        self.assertFalse(corpus.looks_like_an_employer_qualifier(None))


class RequestIdentityTests(unittest.TestCase):
    def test_it_uses_the_projects_canonical_digest(self) -> None:
        """A hand-rolled json.dumps would address a different cache file."""

        from aggie_analytics.cycle30.hashing import sha256_json

        self.assertEqual(
            corpus.request_identity("/teams", {"year": 2020}),
            sha256_json({"endpoint": "/teams", "parameters": {"year": 2020}}),
        )


class DispositionOrderTests(unittest.TestCase):
    def test_the_states_are_distinct(self) -> None:
        states = {
            corpus.NO_EMPLOYER,
            corpus.EMPLOYER_AMBIGUOUS,
            corpus.NO_ROLE,
            corpus.NO_INTERVAL,
            corpus.CANDIDATE,
        }
        self.assertEqual(len(states), 5)

    def test_the_candidate_state_says_it_is_not_joined(self) -> None:
        self.assertIn("NOT_JOINED", corpus.CANDIDATE)


if __name__ == "__main__":
    unittest.main()
