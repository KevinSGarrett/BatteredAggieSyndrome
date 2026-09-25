"""R35-03 tests for the rebuilt independent entailment checker.

The Cycle #35 manager follow-up (20260920T224700Z) reproduced four
synthetic counterexamples the prior `assertions_not_entailed_by_linked_
observations` missed entirely:

1. Source title "Director of Athletic Performance", asserted role
   head_coach -- an unclassifiable title silently authorizing a principal
   role.
2. Source title "Head Coach", asserted role quarterbacks -- a position
   role the prior HC/OC/DC-only check never covered.
3. Source person A/program A/season 2020, linked to assert an episode for
   person B/program B/season 2026, same title text -- the prior check
   never verified subject/program/season binding at all, only title text.
4. Source title "Defensive Coordinator", asserted qualifier "CO" with no
   textual support for it.

The manager also found the checks did not reject promotion from
candidate-only evidence to OFFICIAL_PRIMARY_CONFIRMED, and criticized the
prior check for reusing the ingest-time classifier (`principal_role_
families`), which cannot independently catch a bug the producer and
checker would otherwise share.

The rebuilt checker: (a) is implemented without importing anything from
`aggie_analytics.cycle33.role_taxonomy` -- its own hand-curated keyword
reference, deliberately separate from the ingest pipeline's classifier;
(b) verifies subject/program/season binding against the assertion's own
episode, not just title text; (c) checks qualifier plausibility
independently; (d) requires an OFFICIAL_PRIMARY_CONFIRMED assertion to be
backed by at least one observation from a source class capable of primary
confirmation.
"""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from aggie_analytics.cycle35.coaching_release import (
    LAYER_CANDIDATE,
    LAYER_OFFICIAL,
    add_episode,
    add_observation,
    add_role,
    apply_migrations,
    assertions_not_entailed_by_linked_observations,
    register_source_file,
    upsert_person,
    upsert_program,
)

REAL_FILE = Path(__file__).resolve()


def _ram() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)
    return conn


def _build(
    conn: sqlite3.Connection,
    *,
    title: str,
    role: str,
    qualifiers: tuple = (),
    observed_person: str = "Person A",
    observed_program: str = "P:A",
    observed_season: str = "2020",
    subject_person: str | None = None,
    subject_program: str = "P:A",
    subject_season: str = "2020",
    source_class: str = "OFFICIAL_STAFF_HTML",
    assertion_layer: str = LAYER_OFFICIAL,
    alias: tuple[str, str] | None = None,
) -> str:
    """Builds one assertion linked to one observation, with every binding
    dimension independently controllable, so a probe can diverge exactly
    one dimension at a time from a genuinely valid baseline."""

    subject_person = subject_person if subject_person is not None else observed_person
    source = register_source_file(
        conn, REAL_FILE, source_class=source_class, rights_state="PRIVATE"
    )
    obs = add_observation(
        conn,
        source_file_id=source,
        locator="probe:" + title + ":" + observed_person,
        parser_identity="TEST",
        observed_person=observed_person,
        observed_title=title,
        observed_program=observed_program,
        observed_season=observed_season,
        evidence_layer=LAYER_CANDIDATE,
    )
    person_id = upsert_person(
        conn, subject_person, identity_basis="TEST",
        aliases=[alias] if alias else (),
    )
    upsert_program(conn, subject_program, display_name=subject_program)
    episode_id = add_episode(
        conn, person_id=person_id, program_id=subject_program, season=subject_season,
        date_precision="SEASON", evidence_layer=assertion_layer,
    )
    return add_role(
        conn, episode_id=episode_id, role_family=role, exact_title_text=title,
        qualifiers=list(qualifiers), evidence_layer=assertion_layer,
        supporting_observations=[obs],
    )


class PositiveControlTests(unittest.TestCase):
    """A genuinely valid assertion must never be flagged."""

    def test_simple_head_coach_is_entailed(self) -> None:
        conn = _ram()
        _build(conn, title="Head Coach", role="head_coach")
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()

    def test_position_role_is_entailed(self) -> None:
        conn = _ram()
        _build(conn, title="Quarterbacks Coach", role="quarterbacks")
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()

    def test_qualified_co_shared_role_is_entailed(self) -> None:
        conn = _ram()
        _build(
            conn, title="Co-Defensive Coordinator", role="defensive_coordinator",
            qualifiers=("CO",),
        )
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()

    def test_alias_bound_subject_is_entailed(self) -> None:
        """The observation names the source-published name; the canonical
        person is resolved through a recorded alias, not an exact string
        match on the canonical name."""
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach",
            observed_person="Bob Surace", subject_person="Robert Surace",
            alias=("Bob Surace", "NICKNAME"),
        )
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()

    def test_wikimedia_source_at_candidate_layer_is_entailed(self) -> None:
        """A non-official source is fine for a CANDIDATE-layer claim -- the
        source-authority check only applies at OFFICIAL_PRIMARY_CONFIRMED."""
        conn = _ram()
        _build(
            conn, title="head_coach", role="head_coach",
            source_class="WIKIMEDIA_REVISION_BOUND_RETROSPECTIVE",
            assertion_layer=LAYER_CANDIDATE,
        )
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()


class UnsupportedTitleControlTests(unittest.TestCase):
    """The manager's exact counterexamples 1 and 2: a title with no
    recognizable coaching-role language, or one role's title claimed for a
    different, unrelated role."""

    def test_unclassifiable_title_cannot_authorize_head_coach(self) -> None:
        conn = _ram()
        _build(conn, title="Director of Athletic Performance", role="head_coach")
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertEqual(len(findings), 1)
        self.assertIn(
            "ROLE_FAMILY_NOT_DERIVABLE_FROM_EXACT_TITLE_TEXT", findings[0]["reasons"]
        )
        conn.close()

    def test_head_coach_title_cannot_authorize_quarterbacks(self) -> None:
        conn = _ram()
        _build(conn, title="Head Coach", role="quarterbacks")
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertEqual(len(findings), 1)
        self.assertIn(
            "ROLE_FAMILY_NOT_DERIVABLE_FROM_EXACT_TITLE_TEXT", findings[0]["reasons"]
        )
        conn.close()

    def test_unmapped_placeholder_role_is_never_flagged(self) -> None:
        """The honest "could not classify" placeholder is not itself a
        substantive claim needing textual support."""
        conn = _ram()
        _build(
            conn, title="Director of Athletic Performance",
            role="unmapped_title_review_required",
        )
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()


class SchoolSeasonSwapTests(unittest.TestCase):
    """The manager's exact counterexample 3, plus every individual
    dimension of subject binding tested in isolation."""

    def test_wrong_person_program_and_season_together(self) -> None:
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach",
            observed_person="Person A", observed_program="P:A", observed_season="2020",
            subject_person="Person B", subject_program="P:B", subject_season="2026",
        )
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertEqual(len(findings), 1)
        self.assertIn(
            "SUBJECT_PROGRAM_SEASON_NOT_ENTAILED_BY_ANY_LINKED_OBSERVATION",
            findings[0]["reasons"],
        )
        conn.close()

    def test_wrong_program_alone_is_caught(self) -> None:
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach",
            observed_program="P:A", subject_program="P:DIFFERENT",
        )
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertIn(
            "SUBJECT_PROGRAM_SEASON_NOT_ENTAILED_BY_ANY_LINKED_OBSERVATION",
            findings[0]["reasons"],
        )
        conn.close()

    def test_wrong_season_alone_is_caught(self) -> None:
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach",
            observed_season="2019", subject_season="2020",
        )
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertIn(
            "SUBJECT_PROGRAM_SEASON_NOT_ENTAILED_BY_ANY_LINKED_OBSERVATION",
            findings[0]["reasons"],
        )
        conn.close()

    def test_wrong_person_alone_is_caught(self) -> None:
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach",
            observed_person="Person A", subject_person="Person Z",
        )
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertIn(
            "SUBJECT_PROGRAM_SEASON_NOT_ENTAILED_BY_ANY_LINKED_OBSERVATION",
            findings[0]["reasons"],
        )
        conn.close()


class QualifierChangeTests(unittest.TestCase):
    """The manager's exact counterexample 4, plus a genuine qualifier
    match to prove the check is not just always-reject."""

    def test_unsupported_co_qualifier_is_caught(self) -> None:
        conn = _ram()
        _build(
            conn, title="Defensive Coordinator", role="defensive_coordinator",
            qualifiers=("CO",),
        )
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertIn(
            "QUALIFIERS_NOT_DERIVABLE_FROM_EXACT_TITLE_TEXT", findings[0]["reasons"]
        )
        conn.close()

    def test_unsupported_interim_qualifier_is_caught(self) -> None:
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach", qualifiers=("INTERIM",),
        )
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertIn(
            "QUALIFIERS_NOT_DERIVABLE_FROM_EXACT_TITLE_TEXT", findings[0]["reasons"]
        )
        conn.close()

    def test_supported_interim_qualifier_is_not_flagged(self) -> None:
        conn = _ram()
        _build(
            conn, title="Interim Head Coach", role="head_coach", qualifiers=("INTERIM",),
        )
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()

    def test_abbreviated_assistant_qualifier_is_recognized(self) -> None:
        """A real-corpus abbreviation ("Asst.") must be recognized, not
        just the unabbreviated word."""
        conn = _ram()
        _build(
            conn, title="Asst. Head Coach", role="assistant_head_coach",
            qualifiers=("ASSISTANT",),
        )
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()


class NameCollisionTests(unittest.TestCase):
    """Two different people, same title/role/program, must each be
    checked against THEIR OWN observation -- one person's valid evidence
    must not silently validate a different person's assertion."""

    def test_two_distinct_people_each_entailed_by_their_own_observation(self) -> None:
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach",
            observed_person="Coach One", subject_person="Coach One",
            observed_program="P:X", subject_program="P:X", subject_season="2020",
        )
        _build(
            conn, title="Head Coach", role="head_coach",
            observed_person="Coach Two", subject_person="Coach Two",
            observed_program="P:Y", subject_program="P:Y", subject_season="2020",
        )
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()

    def test_namesake_collision_does_not_launder_a_wrong_binding(self) -> None:
        """Two different canonical people happen to share a display name
        via distinct identity_basis rows; an assertion for one must not be
        satisfiable by an observation naming the SAME text but bound (by
        program/season) to the other."""
        conn = _ram()
        source = register_source_file(
            conn, REAL_FILE, source_class="OFFICIAL_STAFF_HTML", rights_state="PRIVATE"
        )
        # Observation actually describes "John Smith" at P:REAL in 2020.
        obs = add_observation(
            conn, source_file_id=source, locator="real",
            parser_identity="TEST", observed_person="John Smith",
            observed_title="Head Coach", observed_program="P:REAL",
            observed_season="2020", evidence_layer=LAYER_CANDIDATE,
        )
        # A DIFFERENT canonical "John Smith" (different identity_basis) is
        # asserted at a DIFFERENT program in the SAME season, incorrectly
        # linked to the observation above.
        person_id = upsert_person(conn, "John Smith", identity_basis="OTHER_BASIS")
        upsert_program(conn, "P:WRONG", display_name="P:WRONG")
        episode_id = add_episode(
            conn, person_id=person_id, program_id="P:WRONG", season="2020",
            date_precision="SEASON", evidence_layer=LAYER_OFFICIAL,
        )
        add_role(
            conn, episode_id=episode_id, role_family="head_coach",
            exact_title_text="Head Coach", qualifiers=[], evidence_layer=LAYER_OFFICIAL,
            supporting_observations=[obs],
        )
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertEqual(len(findings), 1)
        self.assertIn(
            "SUBJECT_PROGRAM_SEASON_NOT_ENTAILED_BY_ANY_LINKED_OBSERVATION",
            findings[0]["reasons"],
        )
        conn.close()


class SourceLayerEscalationTests(unittest.TestCase):
    """The manager's explicit additional point: these checks must reject
    promotion from candidate-only evidence to OFFICIAL_PRIMARY_CONFIRMED."""

    def test_wikimedia_source_cannot_back_an_official_claim(self) -> None:
        conn = _ram()
        _build(
            conn, title="head_coach", role="head_coach",
            source_class="WIKIMEDIA_REVISION_BOUND_RETROSPECTIVE",
            assertion_layer=LAYER_OFFICIAL,
        )
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertEqual(len(findings), 1)
        self.assertIn("EVIDENCE_LAYER_EXCEEDS_SOURCE_AUTHORITY", findings[0]["reasons"])
        conn.close()

    def test_user_compiled_source_cannot_back_an_official_claim(self) -> None:
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach",
            source_class="USER_COMPILED_RESEARCH_OBSERVATION",
            assertion_layer=LAYER_OFFICIAL,
        )
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertIn("EVIDENCE_LAYER_EXCEEDS_SOURCE_AUTHORITY", findings[0]["reasons"])
        conn.close()

    def test_synthetic_probe_source_cannot_back_an_official_claim(self) -> None:
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach",
            source_class="SYNTHETIC_MANAGER_PROBE", assertion_layer=LAYER_OFFICIAL,
        )
        findings = assertions_not_entailed_by_linked_observations(conn)
        self.assertIn("EVIDENCE_LAYER_EXCEEDS_SOURCE_AUTHORITY", findings[0]["reasons"])
        conn.close()

    def test_official_source_can_back_an_official_claim(self) -> None:
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach",
            source_class="OFFICIAL_STAFF_HTML", assertion_layer=LAYER_OFFICIAL,
        )
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()

    def test_official_source_can_back_a_candidate_claim(self) -> None:
        """The authority ceiling only binds OFFICIAL claims; an official
        source backing a merely-candidate assertion is not itself wrong."""
        conn = _ram()
        _build(
            conn, title="Head Coach", role="head_coach",
            source_class="OFFICIAL_STAFF_HTML", assertion_layer=LAYER_CANDIDATE,
        )
        self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()


class RealDataCalibrationTests(unittest.TestCase):
    """A regression sample of the exact real title patterns found while
    calibrating the independent keyword reference against a full national
    rebuild, so future keyword-map edits cannot silently regress them."""

    _REAL_POSITIVE_TITLES = (
        ("Head Football Coach", "head_coach", ()),
        ("Off. Coordinator, Quarterbacks", "offensive_coordinator", ()),
        ("Off. Coordinator, Quarterbacks", "quarterbacks", ()),
        ("Swette Family Endowed Football Coach", "head_coach", ()),
        ("Assoc. Head Coach / OC / QB", "offensive_coordinator", ("ASSOCIATE",)),
        ("Assoc. Head Coach / OC / QB", "quarterbacks", ("ASSOCIATE",)),
        ("Co-Offensive Coordinator/Wide Recievers", "wide_receivers", ("CO",)),
        ("Assistant Coach - Def. Coor./Safeties", "defensive_coordinator", ()),
        ("Assistant Coach - Def. Coor./Safeties", "safeties", ()),
        ("Bradford M. Freeman Director of Football", "head_coach", ()),
        ("Andrew Luck Director of Offense", "offensive_coordinator", ()),
        (
            "Willie Shaw Director of Defense & Defensive Backs Coach",
            "defensive_coordinator",
            (),
        ),
        ("Offensive Coordinator (WR/Recruiting Coordinator)", "wide_receivers", ()),
        (
            "Defensive Coordinator / Safeties Coach / Passing Game Coordinator",
            "pass_game_coordinator",
            (),
        ),
        ("Assoc. Head Coach/Def. Coordinator/OLB", "outside_linebackers", ()),
    )

    def test_every_real_calibration_title_is_entailed(self) -> None:
        for title, role, qualifiers in self._REAL_POSITIVE_TITLES:
            with self.subTest(title=title, role=role):
                conn = _ram()
                _build(conn, title=title, role=role, qualifiers=qualifiers)
                self.assertEqual(
                    assertions_not_entailed_by_linked_observations(conn), []
                )
                conn.close()


if __name__ == "__main__":
    unittest.main()
