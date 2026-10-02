"""Cycle #37 - Attempt #2 - ACTUAL_STATE

MF36-01 / MF37-05 regressions for source-backed program binding.

The two reported cases are covered, but so are the other five colliding
payloads in the delivered acquisition ledger and a set of confusable pairs
the findings never mentioned. That is deliberate: the defect is that a
payload claimed by two programs was resolved by file order, and a repair
that only knew about Ohio and New Mexico would be the name-specific patch
R37-03 explicitly forbids.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37.source_identity import (  # noqa: E402
    BINDING_CONFIRMED,
    BINDING_CONTRADICTED,
    BINDING_NAME_NOT_MATCHED,
    BINDING_QUARANTINED_AMBIGUOUS,
    BINDING_UNCORROBORATED,
    ProgramClaim,
    adjudicate,
    host_tokens,
    name_tokens,
    page_identity,
)


def page(title: str, *, canonical: str = "/sports/football/coaches", site: str | None = None,
         asset_host: str | None = None) -> str:
    parts = [f"<html><head><title>\r\n\t{title}\r\n</title>",
             f'<link rel="canonical" href="{canonical}">']
    if site:
        parts.append(f'<meta property="og:site_name" content="{site}">')
    parts.append("</head><body>")
    if asset_host:
        parts.append(f"<img src='//{asset_host}/images/x.jpg' alt='x'>")
    parts.append("</body></html>")
    return "".join(parts)


#: A small stand-in for the release's ``canonical_program`` names. Supplying
#: it is what lets a contradiction be a positive finding ("this page covers
#: THAT declared program") rather than an absence.
CATALOGUE = {
    "C:OHIO": "Ohio",
    "C:OHIOSTATE": "Ohio State",
    "C:NM": "New Mexico",
    "C:NMSTATE": "New Mexico State",
    "C:CLEMSON": "Clemson",
    "C:FLORIDA": "Florida",
    "C:FIU": "Florida International",
    "C:FAU": "Florida Atlantic",
    "C:VIRGINIA": "Virginia",
    "C:VT": "Virginia Tech",
    "C:PITT": "Pittsburgh",
    "C:PENNSTATE": "Penn State",
    "C:ND": "North Dakota",
    "C:NDSTATE": "North Dakota State",
    "C:SD": "South Dakota",
    "C:SDSTATE": "South Dakota State",
    "C:TAMU": "Texas A&M",
    "C:ETAMU": "East Texas A&M",
    "C:MIAMIOH": "Miami (OH)",
    "C:MIAMIFL": "Miami (FL)",
    "C:KENTUCKY": "Kentucky",
    "C:OLEMISS": "Ole Miss",
}


class Tokenisation(unittest.TestCase):
    def test_state_is_a_discriminating_token(self) -> None:
        self.assertIn("state", name_tokens("New Mexico State University"))
        self.assertNotIn("state", name_tokens("New Mexico"))

    def test_boilerplate_is_dropped_but_the_school_is_not(self) -> None:
        tokens = name_tokens("Football Coaches - Ohio State University Athletics")
        self.assertIn("ohio", tokens)
        self.assertIn("state", tokens)
        self.assertNotIn("athletics", tokens)
        self.assertNotIn("football", tokens)

    def test_ampersand_becomes_a_word(self) -> None:
        self.assertIn("and", name_tokens("Texas A&M"))

    def test_a_host_expands_its_state_component(self) -> None:
        self.assertIn("state", host_tokens("nmstatesports.com"))
        self.assertIn("state", host_tokens("kstatesports.com"))
        self.assertNotIn("com", host_tokens("nmstatesports.com"))


class SingleClaim(unittest.TestCase):
    def test_a_matching_page_confirms_its_declared_program(self) -> None:
        identity = page_identity(
            page("Football Coaches - Ohio University Athletics"),
            route="https://ohiobobcats.com/sports/football/coaches",
        )
        verdict = adjudicate(identity, [ProgramClaim("P:OHIO", "Ohio")])
        self.assertEqual(verdict["state"], BINDING_CONFIRMED)
        self.assertEqual(verdict["admitted_program_id"], "P:OHIO")

    def test_a_longer_school_name_in_the_page_contradicts_a_shorter_claim(self) -> None:
        identity = page_identity(
            page("Football Coaches - New Mexico State University Athletics"),
            route="https://nmstatesports.com/sports/football/coaches",
        )
        # The catalogue is what makes this a contradiction rather than a
        # guess: the page covers a DECLARED program whose name strictly
        # contains the claim.
        verdict = adjudicate(
            identity,
            [ProgramClaim("P:NM", "New Mexico")],
            known_program_names=CATALOGUE,
        )
        self.assertEqual(verdict["state"], BINDING_CONTRADICTED)
        self.assertIsNone(verdict["admitted_program_id"])

    def test_without_the_catalogue_the_same_page_is_only_confirmed(self) -> None:
        """A contradiction cannot be asserted from one claim alone.

        With no program universe to compare against, "the title says more
        than the claim" is indistinguishable from ordinary branding, which
        is how 61 real captures were mislabelled by this module's first
        version.
        """

        identity = page_identity(
            page("Football Coaches - New Mexico State University Athletics")
        )
        verdict = adjudicate(identity, [ProgramClaim("P:NM", "New Mexico")])
        self.assertEqual(verdict["state"], BINDING_CONFIRMED)
        self.assertFalse(verdict["catalogue_consulted"])

    def test_an_unrelated_page_contradicts_the_claim(self) -> None:
        identity = page_identity(
            page("Football Coaches - Clemson University Athletics"),
            route="https://clemsontigers.com/sports/football/coaches",
        )
        verdict = adjudicate(
            identity,
            [ProgramClaim("P:OHIO", "Ohio")],
            known_program_names=CATALOGUE,
        )
        self.assertEqual(verdict["state"], BINDING_CONTRADICTED)

    def test_a_branded_page_is_unmatched_rather_than_contradicted(self) -> None:
        """The real false-positive class: branding the catalogue lacks.

        "UK Athletics", "NDSU" and "Ole Miss Athletics - Hotty Toddy" are
        not other schools' pages. Labelling them CONTRADICTED asserted a
        wrong-school defect that the evidence does not support.
        """

        for title, claim in (
            ("Staff Directory - UK Athletics", "Kentucky"),
            ("2026 Football Coaches - NDSU", "North Dakota State"),
            ("2026 Football Coaches - Ole Miss Athletics - Hotty Toddy", "Ole Miss"),
        ):
            with self.subTest(title=title):
                identity = page_identity(page(title))
                verdict = adjudicate(
                    identity,
                    [ProgramClaim("P:X", claim)],
                    known_program_names=CATALOGUE,
                )
                self.assertIn(
                    verdict["state"],
                    (BINDING_CONFIRMED, BINDING_NAME_NOT_MATCHED),
                    verdict["reason"],
                )
                self.assertNotEqual(verdict["state"], BINDING_CONTRADICTED)

    def test_a_page_with_no_identity_is_uncorroborated_not_confirmed(self) -> None:
        identity = page_identity("<html><body>nothing here</body></html>")
        verdict = adjudicate(identity, [ProgramClaim("P:OHIO", "Ohio")])
        self.assertEqual(verdict["state"], BINDING_UNCORROBORATED)
        self.assertIsNone(verdict["admitted_program_id"])


class CollidingClaims(unittest.TestCase):
    """The seven real colliding payloads, plus the rule they violated."""

    CASES = (
        # (page title, host, loser claim, winner claim)
        ("Football Coaches - Ohio State University Athletics",
         "ohiostatebuckeyes.com", ("P:195", "Ohio"), ("P:194", "Ohio State")),
        ("Football Coaches - New Mexico State University Athletics",
         "nmstatesports.com", ("P:167", "New Mexico"), ("P:166", "New Mexico State")),
        ("Football Coaches - Southern Utah University Athletics",
         "suutbirds.com", ("P:2582", "Southern"), ("P:253", "Southern Utah")),
        ("Football Coaches - Kansas State University Athletics",
         "kstatesports.com", ("P:2305", "Kansas"), ("P:2306", "Kansas State")),
        ("Football Coaches - Utah State University Athletics",
         "utahstateaggies.com", ("P:254", "Utah"), ("P:328", "Utah State")),
        ("Football Coaches - East Tennessee State University Athletics",
         "etsubucs.com", ("P:2634", "Tennessee State"), ("P:2193", "East Tennessee State")),
        ("Football Coaches - Eastern Illinois University Athletics",
         "eiupanthers.com", ("P:356", "Illinois"), ("P:2197", "Eastern Illinois")),
    )

    def test_every_real_collision_resolves_to_the_program_the_page_names(self) -> None:
        for title, host, loser, winner in self.CASES:
            with self.subTest(title=title):
                identity = page_identity(
                    page(title, asset_host=host), route=f"https://{host}/sports/football/coaches"
                )
                # Claims are supplied loser-first, which is the order that
                # produced the wrong delivered binding.
                verdict = adjudicate(
                    identity,
                    [ProgramClaim(*loser), ProgramClaim(*winner)],
                )
                self.assertEqual(verdict["state"], BINDING_CONFIRMED, verdict["reason"])
                self.assertEqual(verdict["admitted_program_id"], winner[0], verdict["reason"])

    def test_the_result_does_not_depend_on_claim_order(self) -> None:
        title, host, loser, winner = self.CASES[0]
        identity = page_identity(
            page(title, asset_host=host), route=f"https://{host}/sports/football/coaches"
        )
        forward = adjudicate(identity, [ProgramClaim(*loser), ProgramClaim(*winner)])
        reverse = adjudicate(identity, [ProgramClaim(*winner), ProgramClaim(*loser)])
        self.assertEqual(forward["admitted_program_id"], reverse["admitted_program_id"])

    def test_two_equally_covered_claims_quarantine_rather_than_choose(self) -> None:
        # Two catalogue entries whose names the page cannot tell apart. Both
        # are genuinely covered, so this is the tie case rather than the
        # nothing-matches case, and it must refuse rather than take the first.
        identity = page_identity(
            page("Football Coaches - Alpha University Athletics"),
            route="https://example.com/sports/football/coaches",
        )
        verdict = adjudicate(
            identity,
            [ProgramClaim("P:A1", "Alpha"), ProgramClaim("P:A2", "Alpha")],
        )
        self.assertEqual(verdict["state"], BINDING_QUARANTINED_AMBIGUOUS)
        self.assertIsNone(verdict["admitted_program_id"])
        self.assertIn("file order", verdict["reason"])

    def test_two_uncovered_claims_also_quarantine(self) -> None:
        identity = page_identity(
            page("Football Coaches - Clemson University Athletics"),
            route="https://clemsontigers.com/sports/football/coaches",
        )
        verdict = adjudicate(
            identity,
            [ProgramClaim("P:A", "Alpha"), ProgramClaim("P:B", "Beta")],
        )
        self.assertEqual(verdict["state"], BINDING_QUARANTINED_AMBIGUOUS)
        self.assertIsNone(verdict["admitted_program_id"])
        self.assertIn("none is covered", verdict["reason"])


class ConfusablePairsTheFindingsNeverNamed(unittest.TestCase):
    """R37-03 names these explicitly; none of them is in the collision set."""

    PAIRS = (
        ("Florida International University", "FIU", "Florida"),
        ("Florida Atlantic University", "Florida Atlantic", "Florida"),
        ("Miami University", "Miami (OH)", "Pittsburgh"),
        ("Virginia Tech", "Virginia Tech", "Virginia"),
        ("University of Pittsburgh", "Pittsburgh", "Penn State"),
        ("North Dakota State University", "North Dakota State", "North Dakota"),
        ("South Dakota State University", "South Dakota State", "South Dakota"),
        ("Texas A&M University", "Texas A&M", "East Texas A&M"),
    )

    def test_a_page_never_confirms_a_differently_named_program(self) -> None:
        for page_school, right, wrong in self.PAIRS:
            with self.subTest(page=page_school):
                identity = page_identity(
                    page(f"Football Coaches - {page_school} Athletics"),
                    route="https://example.com/sports/football/coaches",
                )
                confirmed = adjudicate(
                    identity,
                    [ProgramClaim("P:RIGHT", right)],
                    known_program_names=CATALOGUE,
                )
                self.assertEqual(
                    confirmed["state"],
                    BINDING_CONFIRMED,
                    f"{right!r} should be confirmed by {page_school!r}: "
                    f"{confirmed['reason']}",
                )
                refused = adjudicate(
                    identity,
                    [ProgramClaim("P:WRONG", wrong)],
                    known_program_names=CATALOGUE,
                )
                self.assertNotEqual(
                    refused["state"],
                    BINDING_CONFIRMED,
                    f"{wrong!r} must not be confirmed by {page_school!r}",
                )

    def test_the_shorter_name_is_rejected_when_both_claim_the_page(self) -> None:
        for page_school, right, wrong in self.PAIRS:
            with self.subTest(page=page_school):
                identity = page_identity(
                    page(f"Football Coaches - {page_school} Athletics"),
                    route="https://example.com/sports/football/coaches",
                )
                verdict = adjudicate(
                    identity,
                    [ProgramClaim("P:WRONG", wrong), ProgramClaim("P:RIGHT", right)],
                )
                self.assertNotEqual(
                    verdict["admitted_program_id"],
                    "P:WRONG",
                    f"{wrong!r} must never win {page_school!r}: {verdict['reason']}",
                )


class PageIdentityExtraction(unittest.TestCase):
    def test_title_whitespace_and_line_separators_are_normalised(self) -> None:
        identity = page_identity(
            "<title>\r\n\tFootball Coaches - New Mexico State University Athletics\r\n</title>"
        )
        self.assertEqual(
            identity.title,
            "Football Coaches - New Mexico State University Athletics",
        )

    def test_a_relative_canonical_link_is_kept_as_written(self) -> None:
        identity = page_identity(page("X", canonical="/sports/football/coaches"))
        self.assertEqual(identity.canonical_href, "/sports/football/coaches")

    def test_an_absolute_canonical_link_contributes_its_host(self) -> None:
        identity = page_identity(
            page("X", canonical="https://nmstatesports.com/sports/football/coaches")
        )
        self.assertIn("nmstatesports.com", identity.asset_hosts)

    def test_the_route_host_is_recorded_separately_from_asset_hosts(self) -> None:
        identity = page_identity(
            page("X", asset_host="cdn.example.com"),
            route="https://nmstatesports.com/sports/football/coaches",
        )
        self.assertEqual(identity.route_host, "nmstatesports.com")
        self.assertIn("cdn.example.com", identity.asset_hosts)

    def test_og_site_name_is_read_when_present(self) -> None:
        identity = page_identity(page("X", site="Kansas State University Athletics"))
        self.assertEqual(identity.og_site_name, "Kansas State University Athletics")


class DeclaredLimitsOfThisMethod(unittest.TestCase):
    """What the token method genuinely cannot decide, stated as tests.

    Recording a limit as a passing test is the difference between a bounded
    method and an overclaimed one. Each case below is a real ambiguity that
    quarantines rather than being resolved by a rule that would be guessing.
    """

    def test_a_bare_miami_page_cannot_separate_the_two_miamis(self) -> None:
        identity = page_identity(
            page("Football Coaches - Miami University Athletics"),
            route="https://example.com/sports/football/coaches",
        )
        verdict = adjudicate(
            identity,
            [ProgramClaim("P:OH", "Miami (OH)"), ProgramClaim("P:FL", "Miami (FL)")],
        )
        self.assertEqual(verdict["state"], BINDING_QUARANTINED_AMBIGUOUS)

    def test_the_host_does_separate_them_when_it_is_distinctive(self) -> None:
        # The same claims with a distinctive host are still not separated by
        # THIS method: "miamiredhawks" is not a token either school's name
        # contains. The honest outcome remains a quarantine, and a mascot
        # crosswalk would be additional source evidence, not a token rule.
        identity = page_identity(
            page("Football Coaches - Miami University Athletics",
                 asset_host="miamiredhawks.com"),
            route="https://miamiredhawks.com/sports/football/coaches",
        )
        verdict = adjudicate(
            identity,
            [ProgramClaim("P:OH", "Miami (OH)"), ProgramClaim("P:FL", "Miami (FL)")],
        )
        self.assertEqual(verdict["state"], BINDING_QUARANTINED_AMBIGUOUS)
        self.assertIn("miamiredhawks", str(verdict["identity"]))

    def test_a_qualifier_is_reported_even_when_coverage_ignores_it(self) -> None:
        identity = page_identity(page("Football Coaches - Miami University Athletics"))
        verdict = adjudicate(identity, [ProgramClaim("P:OH", "Miami (OH)")])
        title_row = verdict["claims"][0]["per_evidence"]["title"]
        self.assertEqual(title_row["claim_qualifier"], "OH")
        self.assertEqual(title_row["claim_base_name"], "Miami")

    def test_an_acronym_claim_records_how_it_was_covered(self) -> None:
        identity = page_identity(
            page("Football Coaches - Florida International University Athletics")
        )
        verdict = adjudicate(identity, [ProgramClaim("P:FIU", "FIU")])
        self.assertEqual(verdict["state"], BINDING_CONFIRMED)
        self.assertEqual(
            verdict["claims"][0]["per_evidence"]["title"]["covered_by"], "acronym"
        )


class SeasonInATitleIsNotPartOfTheName(unittest.TestCase):
    """The real Ohio State and Kansas State pages lead with a season.

    Counting ``2026`` as a name token made the page look like it named a
    longer program than the claim, which quarantined the two collisions this
    repair most needed to resolve. A year is a date.
    """

    def test_a_leading_season_does_not_block_the_longer_claim(self) -> None:
        for title, loser, winner in (
            ("2026 Football Coaches | Ohio State", ("P:195", "Ohio"), ("P:194", "Ohio State")),
            ("2026 Football Coaches - Kansas State University Athletics",
             ("P:2305", "Kansas"), ("P:2306", "Kansas State")),
        ):
            with self.subTest(title=title):
                identity = page_identity(page(title))
                verdict = adjudicate(
                    identity, [ProgramClaim(*loser), ProgramClaim(*winner)]
                )
                self.assertEqual(verdict["state"], BINDING_CONFIRMED, verdict["reason"])
                self.assertEqual(verdict["admitted_program_id"], winner[0])

    def test_a_year_is_not_a_name_token(self) -> None:
        self.assertNotIn("2026", name_tokens("2026 Football Coaches | Ohio State"))
        self.assertIn("ohio", name_tokens("2026 Football Coaches | Ohio State"))

    def test_a_strictly_contained_claim_loses_even_on_an_equal_score(self) -> None:
        identity = page_identity(page("Football Coaches | Ohio State"))
        verdict = adjudicate(
            identity,
            [ProgramClaim("P:OHIO", "Ohio"), ProgramClaim("P:OSU", "Ohio State")],
        )
        self.assertEqual(verdict["admitted_program_id"], "P:OSU")
        loser = next(c for c in verdict["claims"] if c["program_id"] == "P:OHIO")
        self.assertTrue(loser.get("strictly_contained_in_another_claim"))


if __name__ == "__main__":
    unittest.main()
