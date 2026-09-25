"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-13-AC04: the BAS-local C01 staff projection refuses what it cannot
honestly project.

The review found that the Cycle #36 adapter accepted mixed cutoffs, unknown
and future known-at instants and empty evidence, and that its membership
consumer accepted an empty mapping. Its checks looked at the SET of values
across all assertions, so one well-formed assertion hid a malformed one.

These tests do not need the released wheel -- the composition tool runs the
adapter's output through it. They pin the adapter's own refusals, so a
defect cannot survive merely because the owner schema happens to catch it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.c01_boundary import (  # noqa: E402
    BOUNDARY_VERSION,
    C01_UTC_Z,
    PREDECESSOR_BOUNDARY_VERSION,
    ProjectionRefused,
    RoleScope,
    StaffAssertion,
    project_to_staff_snapshot,
    read_only_membership_consumer,
    refuse_source_scheme_as_realized_state,
)

CUTOFF = "2026-09-09T18:08:43Z"


def assertion(**overrides) -> StaffAssertion:
    base = dict(
        assertion_id="fixture-1",
        person_id="synthetic-person-1",
        person_display_name="Synthetic Person One",
        program_id="synthetic-team-1",
        season=2026,
        roles=(RoleScope("head_coach", "TEAM", (), "PRINCIPAL"),),
        source_title="Synthetic Head Coach",
        source_system="SYNTHETIC-FIXTURE",
        evidence_refs=("synthetic://evidence/1",),
        known_at_utc="2026-09-01T12:00:00Z",
        point_in_time_cutoff=CUTOFF,
    )
    base.update(overrides)
    return StaffAssertion(**base)


def other(**overrides) -> StaffAssertion:
    fields = dict(
        assertion_id="fixture-2",
        person_id="synthetic-person-2",
        roles=(RoleScope("defensive_coordinator", "DEFENSE", (), "PRINCIPAL"),),
        evidence_refs=("synthetic://evidence/2",),
    )
    fields.update(overrides)
    return assertion(**fields)


def project(assertions, **kwargs):
    call = {"object_id": "synthetic-snapshot", "ruleset_id": "synthetic-ruleset"}
    call.update(kwargs)
    return project_to_staff_snapshot(assertions, **call)


class PositiveControls(unittest.TestCase):
    def test_a_well_formed_pair_projects(self) -> None:
        result = project([assertion(), other()])
        self.assertEqual(sorted(result["document"]["value"]["coach_ids"]),
                         ["synthetic-person-1", "synthetic-person-2"])

    def test_the_emitted_instants_use_the_released_z_form(self) -> None:
        document = project([assertion()])["document"]
        self.assertRegex(document["known_at"], C01_UTC_Z)
        self.assertRegex(document["point_in_time_cutoff"], C01_UTC_Z)

    def test_an_offset_form_utc_instant_is_normalised_not_refused(self) -> None:
        """V37-03: +00:00 is UTC, and the owner schema wants it spelled Z."""

        document = project(
            [assertion(known_at_utc="2026-09-01T12:00:00+00:00",
                       point_in_time_cutoff="2026-09-09T18:08:43+00:00")]
        )["document"]
        self.assertEqual(document["known_at"], "2026-09-01T12:00:00Z")
        self.assertEqual(document["point_in_time_cutoff"], CUTOFF)

    def test_known_at_equal_to_the_cutoff_is_allowed(self) -> None:
        project([assertion(known_at_utc=CUTOFF)])

    def test_the_version_names_the_repair(self) -> None:
        self.assertEqual(project([assertion()])["boundary_version"], BOUNDARY_VERSION)
        self.assertNotEqual(BOUNDARY_VERSION, PREDECESSOR_BOUNDARY_VERSION)


class CutoffAndKnownAtTests(unittest.TestCase):
    def test_mixed_cutoffs_are_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(), other(point_in_time_cutoff="2026-09-10T00:00:00Z")])

    def test_one_missing_known_at_is_refused_even_beside_a_good_one(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(), other(known_at_utc=None)])

    def test_known_at_after_the_cutoff_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(known_at_utc="2026-09-10T00:00:00Z")])

    def test_a_naive_timestamp_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(known_at_utc="2026-09-01T12:00:00")])

    def test_a_non_utc_offset_is_refused_not_converted(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(known_at_utc="2026-09-01T07:00:00-05:00")])

    def test_an_unparseable_instant_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(known_at_utc="yesterday")])


class EvidenceRightsParentTests(unittest.TestCase):
    def test_empty_evidence_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(evidence_refs=())])

    def test_a_blank_evidence_string_is_not_evidence(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(evidence_refs=("   ",))])

    def test_one_assertion_without_evidence_is_not_rescued_by_another(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(), other(evidence_refs=())])

    def test_missing_rights_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(rights="")])

    def test_missing_parent_program_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(program_id="")])

    def test_missing_person_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(person_id="")])


class ConflictTests(unittest.TestCase):
    def test_an_unresolved_conflict_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(conflicts_with=("fixture-9",))])

    def test_one_role_over_two_different_intervals_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([
                assertion(source_effective_start="2024-01-01", source_effective_end="2024-12-31"),
                assertion(assertion_id="fixture-1b", evidence_refs=("synthetic://e/1b",),
                          source_effective_start="2025-01-01", source_effective_end="2025-12-31"),
            ])

    def test_the_same_role_over_the_same_interval_twice_is_not_a_conflict(self) -> None:
        project([
            assertion(source_effective_start="2025-01-01", source_effective_end="2025-12-31"),
            assertion(assertion_id="fixture-1b", evidence_refs=("synthetic://e/1b",),
                      source_effective_start="2025-01-01", source_effective_end="2025-12-31"),
        ])

    def test_an_unknown_reason_outside_the_released_enum_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project([assertion(unknown_reason="MADE_UP")])


class IdentifierTests(unittest.TestCase):
    def test_identifiers_the_released_schema_rejects_are_refused_first(self) -> None:
        for kwargs in ({"object_id": "O"}, {"object_id": "o"}, {"ruleset_id": "r"},
                       {"ruleset_id": "-leading-dash"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ProjectionRefused):
                    project([assertion()], **kwargs)


class MembershipConsumerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.good = project([assertion(), other()])

    def test_a_real_projection_is_admitted(self) -> None:
        self.assertTrue(read_only_membership_consumer(self.good)["admitted"])

    def test_an_empty_mapping_is_refused(self) -> None:
        """The exact case the review reproduced."""

        result = read_only_membership_consumer({})
        self.assertFalse(result["admitted"])
        self.assertNotIn("team_id", result)

    def test_a_foreign_boundary_version_is_refused(self) -> None:
        stale = dict(self.good, boundary_version=PREDECESSOR_BOUNDARY_VERSION)
        self.assertFalse(read_only_membership_consumer(stale)["admitted"])

    def test_a_document_with_no_people_is_refused(self) -> None:
        empty = dict(self.good)
        empty["document"] = dict(self.good["document"],
                                 value={"team_id": "t", "coach_ids": []})
        self.assertFalse(read_only_membership_consumer(empty)["admitted"])

    def test_a_document_with_no_team_is_refused(self) -> None:
        teamless = dict(self.good)
        teamless["document"] = dict(self.good["document"],
                                    value={"team_id": "", "coach_ids": ["p"]})
        self.assertFalse(read_only_membership_consumer(teamless)["admitted"])

    def test_a_non_mapping_is_refused(self) -> None:
        for value in (None, [], "projection", 7):
            with self.subTest(value=repr(value)):
                self.assertFalse(read_only_membership_consumer(value)["admitted"])


class SeparationTests(unittest.TestCase):
    def test_a_source_scheme_is_never_an_f10_state(self) -> None:
        for target in ("intelligence/TeamSchemeSnapshotV1",
                       "intelligence/CoachStateSnapshotV1",
                       "intelligence/StaffRegimeSnapshotV1"):
            with self.subTest(target=target):
                with self.assertRaises(ProjectionRefused):
                    refuse_source_scheme_as_realized_state(
                        {"source_text": "runs the Air Raid"}, target
                    )

    def test_the_refusal_does_not_depend_on_evidence_tier(self) -> None:
        with self.assertRaises(ProjectionRefused):
            refuse_source_scheme_as_realized_state(
                {"source_text": "official: runs a 4-3", "evidence_tier": "OFFICIAL"},
                "intelligence/TeamSchemeSnapshotV1",
            )

    def test_a_context_contract_is_not_an_f10_state(self) -> None:
        refuse_source_scheme_as_realized_state(
            {"source_text": "anything"}, "context/StaffSnapshotV1"
        )


if __name__ == "__main__":
    unittest.main()
