"""R36-03/04: lineage is exact reproduction, and identity is never guessed.

The two probes the manager used against the Cycle #35 prover are the
negative controls here: a one-ID derivative must not be "proved" by a
two-row payload, and adding an unrelated cached year must not change an
existing derivative's authority.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.membership_lineage import (  # noqa: E402
    PROVED,
    REFUSED_AMBIGUOUS,
    REFUSED_NO_RECEIPT,
    REFUSED_NO_TRANSFORM,
    Receipt,
    prove_lineage,
)
from aggie_analytics.cycle30.hashing import sha256_json  # noqa: E402
from aggie_analytics.cycle36.program_crosswalk import (  # noqa: E402
    ABSENT,
    AMBIGUOUS,
    CANDIDATE_TIGHT_CONTAINMENT,
    CANDIDATE_TOKEN_SUBSET,
    CANDIDATE_VARIANT,
    OUT_OF_POPULATION,
    RESOLVED,
    build_crosswalk,
    conflict_report,
    normalize_name,
    normalize_name_tight,
    related_candidates,
)


def _payload(rows: list[dict]) -> tuple[Path, str, tempfile.TemporaryDirectory]:
    holder = tempfile.TemporaryDirectory()
    path = Path(holder.name) / "payload.json"
    raw = json.dumps(rows).encode("utf-8")
    path.write_bytes(raw)
    return path, hashlib.sha256(raw).hexdigest(), holder


def _authentic_identity(year: int) -> str:
    """The identity the Cycle #30 ledger's cache-hit branch actually writes.

    The fixture used to carry ``f"request-{year}"``. MF36-05 is precisely
    that a receipt carrying a string like that proved a derivative's lineage,
    so the fixture is now an identity that recomputes from its own request
    and the invented string is a negative control below.
    """

    return sha256_json({"path": "/teams", "parameters": {"year": year}})


def _receipt(year: int, rows: list[dict]):
    path, digest, holder = _payload(rows)
    return (
        Receipt(
            endpoint="/teams",
            parameters={"year": year},
            declared_digest=digest,
            request_identity=_authentic_identity(year),
            cached_path=str(path),
            actual_digest=digest,
            retrieved_at_utc="2026-09-09T18:08:43Z",
            http_status=200,
            payload_rows=len(rows),
        ),
        holder,
    )


class LineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._holders = []

    def tearDown(self) -> None:
        for holder in self._holders:
            holder.cleanup()

    def receipt(self, year: int, rows: list[dict]) -> Receipt:
        receipt, holder = _receipt(year, rows)
        self._holders.append(holder)
        return receipt

    def test_exact_reproduction_proves_the_year(self) -> None:
        rows = [
            {"id": 1, "classification": "fbs"},
            {"id": 2, "classification": "fcs"},
            {"id": 3, "classification": "iii"},
        ]
        result = prove_lineage(["1", "2"], [self.receipt(2026, rows)], "TEAMS_FBS_FCS_V1")
        self.assertEqual(result["state"], PROVED)
        self.assertEqual(result["bound_year"], 2026)

    def test_a_subset_is_not_lineage(self) -> None:
        """The manager's first probe: one ID against a two-row payload."""

        rows = [{"id": 1, "classification": "fbs"}, {"id": 2, "classification": "fbs"}]
        result = prove_lineage(["1"], [self.receipt(2026, rows)], "TEAMS_FBS_FCS_V1")
        self.assertEqual(result["state"], REFUSED_NO_RECEIPT)
        self.assertIsNone(result["bound_year"])

    def test_unrelated_cached_year_does_not_change_authority(self) -> None:
        """The manager's second probe, inverted: authority must be stable."""

        rows = [{"id": 1, "classification": "fbs"}, {"id": 2, "classification": "fcs"}]
        other = [{"id": 7, "classification": "fbs"}, {"id": 8, "classification": "fcs"}]
        alone = prove_lineage(["1", "2"], [self.receipt(2026, rows)], "TEAMS_FBS_FCS_V1")
        with_extra = prove_lineage(
            ["1", "2"],
            [self.receipt(2026, rows), self.receipt(2025, other)],
            "TEAMS_FBS_FCS_V1",
        )
        self.assertEqual(alone["state"], PROVED)
        self.assertEqual(with_extra["state"], PROVED)
        self.assertEqual(alone["bound_year"], with_extra["bound_year"])

    def test_two_different_years_reproducing_is_ambiguous(self) -> None:
        rows = [{"id": 1, "classification": "fbs"}]
        result = prove_lineage(
            ["1"],
            [self.receipt(2025, rows), self.receipt(2026, list(rows))],
            "TEAMS_FBS_FCS_V1",
        )
        self.assertEqual(result["state"], REFUSED_AMBIGUOUS)
        self.assertIsNone(result["bound_year"])

    def test_same_year_twice_still_proves_the_season(self) -> None:
        """Byte-identical requests of one year leave the season certain."""

        rows = [{"id": 1, "classification": "fbs"}]
        result = prove_lineage(
            ["1"],
            [self.receipt(2026, rows), self.receipt(2026, list(rows))],
            "TEAMS_FBS_FCS_V1",
        )
        self.assertEqual(result["state"], PROVED)
        self.assertEqual(result["bound_year"], 2026)
        self.assertFalse(result["request_identity_unique"])

    def test_missing_transform_refuses(self) -> None:
        rows = [{"id": 1, "classification": "fbs"}]
        result = prove_lineage(["1"], [self.receipt(2026, rows)], None)
        self.assertEqual(result["state"], REFUSED_NO_TRANSFORM)

    def test_declared_digest_without_bytes_cannot_reproduce(self) -> None:
        receipt = Receipt(
            endpoint="/teams",
            parameters={"year": 2026},
            declared_digest="0" * 64,
            request_identity=_authentic_identity(2026),
            cached_path=None,
            actual_digest=None,
            retrieved_at_utc=None,
            http_status=200,
            payload_rows=0,
        )
        result = prove_lineage(["1"], [receipt], "TEAMS_FBS_FCS_V1")
        self.assertEqual(result["state"], REFUSED_NO_RECEIPT)

    def test_one_extra_row_in_the_file_is_a_named_residual(self) -> None:
        rows = [{"id": 1, "classification": "fbs"}]
        result = prove_lineage(["1", "99"], [self.receipt(2026, rows)], "TEAMS_FBS_FCS_V1")
        self.assertEqual(result["state"], REFUSED_NO_RECEIPT)
        residual = result["evaluations"][0]["comparison"]
        self.assertEqual(residual["in_file_not_in_transform_output"], ["99"])


PAYLOADS = {
    2021: (
        "digest-2021",
        [
            {
                "id": 3101,
                "school": "Utah Tech",
                "mascot": "Trailblazers",
                "classification": "fcs",
                "alternateNames": ["Dixie State", "UTU"],
            },
            {
                "id": 2837,
                "school": "East Texas A&M",
                "mascot": "Lions",
                "classification": "ii",
                "alternateNames": ["Texas A&M-Commerce", "ETAM"],
            },
            {
                "id": 245,
                "school": "Texas A&M",
                "mascot": "Aggies",
                "classification": "fbs",
                "alternateNames": ["TA&M"],
            },
            {
                "id": 399,
                "school": "UAlbany",
                "mascot": "Great Danes",
                "classification": "fcs",
                "alternateNames": ["SUNY Albany", "Albany"],
            },
            {
                "id": 2013,
                "school": "Albany State",
                "mascot": "Golden Rams",
                "classification": "ii",
                "alternateNames": ["Albany"],
            },
            {
                "id": 62,
                "school": "Hawai'i",
                "mascot": "Rainbow Warriors",
                "classification": "fbs",
                "alternateNames": [],
            },
        ],
    )
}


class CrosswalkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.crosswalk = build_crosswalk(PAYLOADS)

    def test_rename_resolves_to_one_stable_identity(self) -> None:
        for spelling in ("Dixie State", "Utah Tech"):
            with self.subTest(spelling=spelling):
                record = self.crosswalk.resolve(spelling, 2021)
                self.assertEqual(record["state"], RESOLVED)
                self.assertEqual(record["canonical_program_id"], "SRC-002:TEAM:3101")

    def test_commerce_is_never_merged_into_college_station(self) -> None:
        commerce = self.crosswalk.resolve("Texas A&M-Commerce", 2021)
        station = self.crosswalk.resolve("Texas A&M", 2021)
        self.assertEqual(commerce["candidate_program_ids"], ["SRC-002:TEAM:2837"])
        self.assertEqual(station["canonical_program_id"], "SRC-002:TEAM:245")
        self.assertNotEqual(
            commerce["candidate_program_ids"][0], station["canonical_program_id"]
        )

    def test_commerce_outside_the_football_population_is_not_counted(self) -> None:
        record = self.crosswalk.resolve("East Texas A&M", 2021)
        self.assertEqual(record["state"], OUT_OF_POPULATION)

    def test_albany_stays_ambiguous(self) -> None:
        record = self.crosswalk.resolve("Albany", 2021)
        self.assertEqual(record["state"], AMBIGUOUS)
        self.assertIsNone(record["canonical_program_id"])
        self.assertEqual(
            record["candidate_program_ids"],
            ["SRC-002:TEAM:2013", "SRC-002:TEAM:399"],
        )

    def test_unknown_name_is_absent_not_nearest_match(self) -> None:
        record = self.crosswalk.resolve("Louisiana-Monroe", 2011)
        self.assertEqual(record["state"], ABSENT)
        self.assertIsNone(record["canonical_program_id"])

    def test_team_season_title_shape_is_stripped_before_matching(self) -> None:
        record = self.crosswalk.resolve("2021 Utah Tech Trailblazers football team", 2021)
        self.assertEqual(record["canonical_program_id"], "SRC-002:TEAM:3101")

    def test_orthographic_variant_matches_hawaii(self) -> None:
        record = self.crosswalk.resolve("Hawaii", 2021)
        self.assertEqual(record["state"], RESOLVED)
        self.assertEqual(
            record["match_basis"], "ORTHOGRAPHIC_VARIANT_PUNCTUATION_REMOVED"
        )

    def test_conflicts_are_published_not_silently_resolved(self) -> None:
        report = conflict_report(self.crosswalk)
        colliding = {row["normalized_alias"] for row in report["collisions"]}
        self.assertIn("albany", colliding)

    def test_normalizers_do_not_drop_tokens(self) -> None:
        self.assertEqual(normalize_name("Texas A&M-Commerce"), "texas a m commerce")
        self.assertEqual(normalize_name_tight("Hawai'i"), "hawaii")
        self.assertNotEqual(
            normalize_name_tight("Texas A&M"), normalize_name_tight("Texas A&M-Commerce")
        )

    def test_resolution_is_not_a_membership_claim(self) -> None:
        record = self.crosswalk.resolve("Utah Tech", 1999)
        self.assertEqual(record["state"], RESOLVED)
        self.assertFalse(record["season_membership_observed"])


class UnresolvedNameInspectionTests(unittest.TestCase):
    """An unresolved name must be inspected, and inspection is not a merge.

    The failed-lookup state used to be named
    UNRESOLVED_NAME_ABSENT_FROM_EVERY_DECLARED_SOURCE_PAYLOAD, which claimed
    the payloads never name the program. They do: "McNeese" for "McNeese
    State", "St. Peter's" for "Saint Peter's". These tests pin the corrected
    name and the reporting rules that replaced the claim.
    """

    DECLARED = {
        "P-MCNEESE": ["McNeese"],
        "P-NWMO": ["Northwest Missouri State"],
        "P-MOSTATE": ["Missouri State"],
        "P-EASTERN": ["Eastern"],
        "P-LOUISIANA": ["Louisiana"],
        "P-STPETER": ["St. Peter's"],
        "P-UALBANY": ["UAlbany"],
        "P-FAIRFIELD-ABSENT": ["Wofford"],
        "P-BAR": ["Bar State"],
    }

    def test_state_name_claims_only_what_the_lookup_tested(self) -> None:
        self.assertEqual(ABSENT, "UNRESOLVED_NO_DECLARED_NAME_MATCHES_THIS_QUERY")
        self.assertNotIn("ABSENT_FROM_EVERY", ABSENT)

    def test_token_subset_names_the_related_spelling(self) -> None:
        found = related_candidates("McNeese State", self.DECLARED)
        self.assertEqual([c["declared_name"] for c in found], ["McNeese"])
        self.assertEqual(found[0]["basis"], CANDIDATE_TOKEN_SUBSET)
        self.assertEqual(
            found[0]["disposition"],
            "CANDIDATE_REQUIRES_SOURCE_RENAME_EVIDENCE_NOT_MERGED",
        )

    def test_a_different_compass_prefix_is_not_a_candidate(self) -> None:
        """Northwest Missouri State is not Southwest Missouri State."""

        names = [
            c["declared_name"]
            for c in related_candidates("Southwest Missouri State", self.DECLARED)
        ]
        self.assertIn("Missouri State", names)
        self.assertNotIn("Northwest Missouri State", names)

    def test_containment_must_align_to_an_end(self) -> None:
        """"Eastern" sits inside "Southeastern Louisiana" across a boundary."""

        names = [
            c["declared_name"]
            for c in related_candidates("Southeastern Louisiana", self.DECLARED)
        ]
        self.assertNotIn("Eastern", names)
        self.assertIn("Louisiana", names)

    def test_suffix_containment_relates_albany_to_ualbany(self) -> None:
        found = related_candidates("Albany", self.DECLARED)
        self.assertEqual([c["declared_name"] for c in found], ["UAlbany"])
        self.assertEqual(found[0]["basis"], CANDIDATE_TIGHT_CONTAINMENT)

    def test_saint_and_st_are_reported_but_never_resolved(self) -> None:
        found = related_candidates("Saint Peter's", self.DECLARED)
        self.assertEqual([c["declared_name"] for c in found], ["St. Peter's"])
        self.assertEqual(found[0]["basis"], CANDIDATE_VARIANT)
        # The expansion widens reporting only. Resolution still refuses it.
        crosswalk = build_crosswalk([])
        self.assertEqual(crosswalk.resolve("Saint Peter's")["state"], ABSENT)

    def test_a_shared_generic_token_is_not_a_candidate(self) -> None:
        self.assertEqual(related_candidates("Foo State", {"P-BAR": ["Bar State"]}), [])

    def test_a_name_with_no_relation_reports_nothing(self) -> None:
        self.assertEqual(related_candidates("Canisius", self.DECLARED), [])


if __name__ == "__main__":
    unittest.main()
