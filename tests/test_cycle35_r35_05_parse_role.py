"""r35_05_resolve_missing_keys.py's parse_role(): pull one coaching role's
occupant out of a Wikipedia team-season infobox, verbatim.

Regression: found while rebuilding the full national coaching release to
verify the program-scoped person-identity fix -- two canonical_person rows
came out with canonical_name literally `"| oc_year ="`, a raw wikitext
infobox line leaking through as if it were a person's name.

Root cause: the value-matching regex used `\\s*` between `=` and the
captured value. `\\s` matches `\\n`, so an infobox field with an EMPTY
value (e.g. `| oc =\n`) let that trailing `\\s*` cross the newline and the
capture group `([^\\n]+)` then greedily matched the entire NEXT infobox
line as if it were this parameter's own value. Two adjacent empty fields
-- an empty "oc" immediately followed by an empty "oc_year" -- produced
exactly the reported garbled string. Fixed by constraining the whitespace
around `=` to `[ \t]` (never `\n`), so a parameter's value can never
bleed across a line boundary.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_05_resolve_missing_keys import parse_role  # noqa: E402


class EmptyAdjacentFieldsRegressionTests(unittest.TestCase):
    def test_empty_oc_followed_by_empty_oc_year_does_not_leak_the_next_line(self) -> None:
        """The exact reported bug: real canonical_person rows carried
        canonical_name literally '| oc_year ='."""
        wikitext = (
            "{{Infobox\n"
            "| head_coach = [[Real Coach]]\n"
            "| oc =\n"
            "| oc_year =\n"
            "| def_coach = [[Another Coach]]\n"
            "}}"
        )
        self.assertEqual(parse_role(wikitext, "offensive_coordinator"), {})

    def test_empty_off_coach_followed_by_empty_oc_year_does_not_leak(self) -> None:
        """The first alias tried is 'off_coach', not 'oc' -- the same bleed
        must not happen through that alias either."""
        wikitext = (
            "{{Infobox\n"
            "| off_coach =\n"
            "| oc_year =\n"
            "}}"
        )
        self.assertEqual(parse_role(wikitext, "offensive_coordinator"), {})

    def test_empty_field_followed_by_a_populated_next_line_does_not_leak_either(self) -> None:
        """Even when the following line has a real value, it belongs to
        its OWN parameter, not to the empty one above it."""
        wikitext = (
            "{{Infobox\n"
            "| oc =\n"
            "| oc_year = 2nd\n"
            "}}"
        )
        self.assertEqual(parse_role(wikitext, "offensive_coordinator"), {})

    def test_a_single_empty_field_with_nothing_after_it_is_also_empty(self) -> None:
        wikitext = "{{Infobox\n| oc =\n}}"
        self.assertEqual(parse_role(wikitext, "offensive_coordinator"), {})


class NormalResolutionTests(unittest.TestCase):
    def test_a_real_populated_oc_field_resolves_correctly(self) -> None:
        wikitext = (
            "{{Infobox\n"
            "| head_coach = [[Some Coach]]\n"
            "| oc = [[Some Coordinator]]\n"
            "| oc_year = 2nd\n"
            "}}"
        )
        result = parse_role(wikitext, "offensive_coordinator")
        self.assertEqual(result["parameter"], "oc")
        self.assertEqual(result["resolved_person"], "Some Coordinator")

    def test_a_real_populated_off_coach_field_resolves_correctly(self) -> None:
        wikitext = "{{Infobox\n| off_coach = [[Jane Doe]]\n| oc_year = 1st\n}}"
        result = parse_role(wikitext, "offensive_coordinator")
        self.assertEqual(result["parameter"], "off_coach")
        self.assertEqual(result["resolved_person"], "Jane Doe")

    def test_oc_year_appearing_before_the_real_oc_field_is_not_confused_with_it(self) -> None:
        """A distractor field earlier in the infobox must not be picked up
        instead of the real, later parameter."""
        wikitext = "{{Infobox\n| oc_year = 3rd\n| oc = [[Correct Name]]\n}}"
        result = parse_role(wikitext, "offensive_coordinator")
        self.assertEqual(result["resolved_person"], "Correct Name")

    def test_wikilink_pipe_inside_the_value_is_not_truncated(self) -> None:
        """Existing regression this function's docstring already
        documents: a wikilink's own pipe must not be mistaken for the next
        field's delimiter."""
        wikitext = "{{Infobox\n| head_coach = [[Tom O'Brien (American football)|Tom O'Brien]]\n}}"
        result = parse_role(wikitext, "head_coach")
        self.assertEqual(result["resolved_person"], "Tom O'Brien (American football)")

    def test_head_coach_alias_hc_is_not_matched_by_this_function_for_coordinators(self) -> None:
        """Unrelated role lookups on the same wikitext must not cross-pollinate."""
        wikitext = "{{Infobox\n| head_coach = [[Head Person]]\n| oc = [[Coord Person]]\n}}"
        hc = parse_role(wikitext, "head_coach")
        oc = parse_role(wikitext, "offensive_coordinator")
        self.assertEqual(hc["resolved_person"], "Head Person")
        self.assertEqual(oc["resolved_person"], "Coord Person")


class NoMatchAtAllTests(unittest.TestCase):
    def test_a_co_coordinator_structure_with_no_single_field_returns_empty(self) -> None:
        """Real Wikipedia team-season articles sometimes use
        cooff_coach1/cooff_coach2 instead of a single off_coach/oc field.
        None of ROLE_PARAMS' aliases should match a co-coordinator field
        name by partial/embedded overlap."""
        wikitext = (
            "{{Infobox\n"
            "| cooff_coach1 = [[Coordinator One]]\n"
            "| cooc1_year = 1st\n"
            "| cooff_coach2 = [[Coordinator Two]]\n"
            "| cooc2_year = 1st\n"
            "| off_scheme = [[Spread offense|Spread]]\n"
            "}}"
        )
        self.assertEqual(parse_role(wikitext, "offensive_coordinator"), {})

    def test_no_infobox_at_all_returns_empty(self) -> None:
        self.assertEqual(parse_role("plain text with no infobox", "head_coach"), {})


if __name__ == "__main__":
    unittest.main()
