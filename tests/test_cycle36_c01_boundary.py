"""R36-13: a lossy projection must declare its losses and refuse misuse.

The released ``StaffSnapshotV1`` value is ``{team_id, coach_ids}``. These
tests hold the boundary to three promises: a role-aware consumer can never
read a role out of it, a caller that says it needs a lost field gets a
refusal rather than a plausible document, and the envelope keeps everything
the projection drops.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.c01_boundary import (  # noqa: E402
    C01_CONTRACT,
    FIELD_MATRIX,
    LOST,
    REPRESENTED,
    ProjectionRefused,
    RoleScope,
    StaffAssertion,
    owner_proposal,
    project_to_staff_snapshot,
    read_only_membership_consumer,
    read_only_role_consumer,
)


def assertion(**overrides) -> StaffAssertion:
    base = dict(
        assertion_id="synthetic-1",
        person_id="synthetic-person-1",
        person_display_name="Synthetic Person One",
        program_id="synthetic-team-1",
        season=2026,
        roles=(RoleScope("head_coach", "TEAM", (), "PRINCIPAL"),),
        source_title="Synthetic Head Coach Title",
        source_system="SYNTHETIC-FIXTURE",
        evidence_refs=("synthetic://evidence/1",),
        known_at_utc="2026-09-09T18:08:43Z",
        point_in_time_cutoff="2026-09-09T18:08:43Z",
    )
    base.update(overrides)
    return StaffAssertion(**base)


class ProjectionTests(unittest.TestCase):
    def test_projection_produces_the_released_shape(self) -> None:
        result = project_to_staff_snapshot(
            [assertion()], object_id="synthetic-1", ruleset_id="synthetic-ruleset"
        )
        document = result["document"]
        self.assertEqual(document["contract"], C01_CONTRACT)
        self.assertEqual(set(document["value"]), {"team_id", "coach_ids"})
        self.assertTrue(result["projection_is_lossy"])

    def test_a_coordinator_and_a_head_coach_project_identically(self) -> None:
        """The whole point of the loss: role is not in the released value."""

        head = project_to_staff_snapshot(
            [assertion(person_id="p1")],
            object_id="synthetic-object",
            ruleset_id="synthetic-ruleset",
        )["document"]["value"]
        coordinator = project_to_staff_snapshot(
            [
                assertion(
                    person_id="p1",
                    roles=(RoleScope("offensive_coordinator", "OFFENSE"),),
                    source_title="Synthetic Offensive Coordinator",
                )
            ],
            object_id="synthetic-object",
            ruleset_id="synthetic-ruleset",
        )["document"]["value"]
        self.assertEqual(head, coordinator)

    def test_requiring_a_lost_field_is_refused(self) -> None:
        for name in ("roles", "source_title", "evidence_tier", "rights"):
            with self.subTest(field=name):
                with self.assertRaises(ProjectionRefused):
                    project_to_staff_snapshot(
                        [assertion()],
                        object_id="synthetic-object",
                        ruleset_id="synthetic-ruleset",
                        required_fields=[name],
                    )

    def test_requiring_a_represented_field_is_allowed(self) -> None:
        result = project_to_staff_snapshot(
            [assertion()],
            object_id="synthetic-object",
            ruleset_id="synthetic-ruleset",
            required_fields=["program_id", "known_at_utc", "evidence_refs"],
        )
        self.assertEqual(result["document"]["contract"], C01_CONTRACT)

    def test_two_programs_cannot_share_one_snapshot(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project_to_staff_snapshot(
                [assertion(), assertion(program_id="synthetic-team-2")],
                object_id="synthetic-object",
                ruleset_id="synthetic-ruleset",
            )

    def test_a_missing_cutoff_is_not_invented(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project_to_staff_snapshot(
                [assertion(point_in_time_cutoff=None)],
                object_id="synthetic-object",
                ruleset_id="synthetic-ruleset",
            )

    def test_an_empty_input_is_refused(self) -> None:
        with self.assertRaises(ProjectionRefused):
            project_to_staff_snapshot([], object_id="synthetic-object", ruleset_id="synthetic-ruleset")

    def test_a_conflicting_claim_is_refused_not_silently_dropped(self) -> None:
        """R37-13-AC04 reverses what this test used to pin.

        It used to assert that a claim in unresolved conflict was projected
        with the conflict quietly dropped, which is the "lossy silent field"
        the review names: the snapshot then looks unanimous. The conflict is
        still a LOST field in the matrix -- the released value still has no
        place for it -- but a claim carrying one is now refused rather than
        projected as if it had none.
        """

        with self.assertRaises(ProjectionRefused):
            project_to_staff_snapshot(
                [assertion(conflicts_with=("synthetic-2",))],
                object_id="synthetic-object",
                ruleset_id="synthetic-ruleset",
            )
        self.assertEqual(FIELD_MATRIX["conflicts_with"]["state"], LOST)


class ConsumerStubTests(unittest.TestCase):
    def setUp(self) -> None:
        self.projection = project_to_staff_snapshot(
            [
                assertion(person_id="p1"),
                assertion(
                    assertion_id="synthetic-2",
                    person_id="p2",
                    roles=(RoleScope("defensive_coordinator", "DEFENSE"),),
                    source_title="Synthetic Defensive Coordinator",
                ),
            ],
            object_id="synthetic-object",
            ruleset_id="synthetic-ruleset",
        )

    def test_role_aware_consumer_refuses(self) -> None:
        result = read_only_role_consumer(self.projection)
        self.assertFalse(result["admitted"])
        self.assertEqual(result["roles_available"], 0)
        self.assertEqual(result["people_seen"], 2)
        self.assertFalse(result["wrote_anything"])

    def test_membership_consumer_is_satisfied_and_says_its_limits(self) -> None:
        result = read_only_membership_consumer(self.projection)
        self.assertTrue(result["admitted"])
        self.assertEqual(sorted(result["people"]), ["p1", "p2"])
        self.assertIn("Membership only", result["limits"])
        self.assertFalse(result["wrote_anything"])


class MatrixTests(unittest.TestCase):
    def test_every_envelope_field_has_a_state(self) -> None:
        for name, row in FIELD_MATRIX.items():
            with self.subTest(field=name):
                self.assertIn(
                    row["state"],
                    {REPRESENTED, LOST, "PENDING_OWNER_PROPOSAL"},
                )
                self.assertTrue(row["note"])

    def test_roles_are_not_claimed_as_represented(self) -> None:
        self.assertEqual(FIELD_MATRIX["roles"]["state"], LOST)
        self.assertIsNone(FIELD_MATRIX["roles"]["c01_path"])

    def test_proposal_is_not_an_adoption(self) -> None:
        proposal = owner_proposal()
        self.assertEqual(proposal["status"], "PROPOSED_NOT_ADOPTED")
        self.assertIn("does not adopt", proposal["not_self_adopted"])


if __name__ == "__main__":
    unittest.main()
