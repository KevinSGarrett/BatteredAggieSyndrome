"""R35-03 tests for MR34-05: the release must be source-driven and replayable.

The Cycle #34 delivery's `verified` flags came from tuples typed into the
ingester. These tests pin the properties that make that impossible here:
every promoted assertion names a supporting observation, a predecessor's
claim cannot be inherited as verification, a failed import leaves no partial
release, identities are content-addressed so replay reproduces them, and a
predecessor is never unlinked to free a filename.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.cycle35.coaching_release import (
    LAYER_CANDIDATE,
    LAYER_OFFICIAL,
    SCHEMA_VERSION,
    CoachingReleaseError,
    add_episode,
    add_observation,
    add_role,
    append_release_manifest,
    apply_migrations,
    assertions_missing_evidence_link,
    assertions_not_entailed_by_linked_observations,
    compare_releases,
    layer_counts,
    open_release,
    person_identity_adjudications,
    person_identity_merge_candidates,
    record_adjudication,
    record_conflict,
    record_person_identity_adjudication,
    register_source_file,
    release_row_identities,
    stable_id,
    transaction,
    upsert_person,
    upsert_program,
)


def _seed(conn, tmp: Path, *, support: bool = True) -> dict[str, str]:
    source = tmp / "staff.html"
    source.write_text("<table><tr><td>A Coach</td><td>Head Coach</td></tr></table>",
                      encoding="utf-8")
    source_file_id = register_source_file(
        conn, source, source_class="OFFICIAL_STAFF_HTML", rights_state="PRIVATE"
    )
    observation_id = add_observation(
        conn,
        source_file_id=source_file_id,
        locator="tr[0]",
        parser_identity="TEST",
        observed_person="A Coach",
        observed_title="Head Coach",
        observed_program="P:1",
        observed_season="2026",
    )
    upsert_program(conn, "P:1", display_name="Example State", season=2026)
    person_id = upsert_person(conn, "A Coach", identity_basis="TEST")
    episode_id = add_episode(
        conn,
        person_id=person_id,
        program_id="P:1",
        season="2026",
        date_precision="SEASON",
        evidence_layer=LAYER_OFFICIAL,
    )
    assertion_id = add_role(
        conn,
        episode_id=episode_id,
        role_family="head_coach",
        exact_title_text="Head Coach",
        qualifiers=[],
        evidence_layer=LAYER_OFFICIAL,
        supporting_observations=[observation_id] if support else [],
    )
    return {
        "source_file_id": source_file_id,
        "observation_id": observation_id,
        "episode_id": episode_id,
        "assertion_id": assertion_id,
    }


class SchemaTests(unittest.TestCase):
    def test_migrations_are_idempotent(self) -> None:
        conn = sqlite3.connect(":memory:")
        first = apply_migrations(conn)
        second = apply_migrations(conn)
        self.assertEqual(first, [version for version, _ in _versions()])
        self.assertEqual(second, [])
        rows = conn.execute("SELECT version FROM schema_migration ORDER BY 1").fetchall()
        self.assertEqual([int(r[0]) for r in rows], [1, 2, 3, 4])
        self.assertEqual(max(int(r[0]) for r in rows), SCHEMA_VERSION)

    def test_open_release_refuses_to_overwrite_a_predecessor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "release.sqlite"
            conn = open_release(path)
            conn.close()
            before = path.read_bytes()
            with self.assertRaises(CoachingReleaseError):
                open_release(path)
            # The predecessor's bytes are untouched by the refused call.
            self.assertEqual(path.read_bytes(), before)


def _versions():
    from aggie_analytics.cycle35.coaching_release import MIGRATIONS

    return MIGRATIONS


class SourceDrivenTests(unittest.TestCase):
    def test_every_promoted_assertion_names_a_supporting_observation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            _seed(conn, Path(tmp), support=True)
            conn.commit()
            self.assertEqual(assertions_missing_evidence_link(conn), [])
            conn.close()

    def test_an_unsupported_assertion_is_detected_not_hidden(self) -> None:
        """The check must be able to fail, or it proves nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            _seed(conn, Path(tmp), support=False)
            conn.commit()
            found = assertions_missing_evidence_link(conn)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["role_family"], "head_coach")
            conn.close()

    def test_lineage_is_written_for_each_support_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            ids = _seed(conn, Path(tmp))
            conn.commit()
            row = conn.execute(
                "SELECT * FROM lineage WHERE downstream_id = ?", (ids["assertion_id"],)
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["upstream_id"], ids["observation_id"])
            self.assertEqual(row["relation"], "SUPPORTED_BY")
            conn.close()

    def test_source_file_hash_is_computed_from_real_bytes(self) -> None:
        import hashlib

        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            source = Path(tmp) / "x.html"
            source.write_bytes(b"hello")
            register_source_file(
                conn, source, source_class="TEST", rights_state="TEST"
            )
            conn.commit()
            row = conn.execute("SELECT raw_sha256, bytes FROM source_file").fetchone()
            self.assertEqual(row["raw_sha256"], hashlib.sha256(b"hello").hexdigest())
            self.assertEqual(row["bytes"], 5)
            conn.close()


class SemanticEntailmentTests(unittest.TestCase):
    """MF35-03: a link existing (`assertions_missing_evidence_link`) is a
    different, weaker claim than the linked observation actually entailing
    the asserted fact (`assertions_not_entailed_by_linked_observations`).
    These tests exercise the second check directly and prove it is
    independent of the first."""

    def test_entailed_assertion_passes_both_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            _seed(conn, Path(tmp), support=True)
            conn.commit()
            self.assertEqual(assertions_missing_evidence_link(conn), [])
            self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
            conn.close()

    def test_title_text_diverged_from_every_linked_observation_is_detected(self) -> None:
        """The manager's exact MF35-03 reproduction shape: the assertion's
        `exact_title_text` was changed in place while its `assertion_support`
        link was left untouched. The link still exists -- only the stronger
        entailment check may catch this."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            ids = _seed(conn, Path(tmp), support=True)
            conn.execute(
                "UPDATE formal_role_assertion SET exact_title_text = ? "
                "WHERE assertion_id = ?",
                ("Special Teams Coordinator", ids["assertion_id"]),
            )
            conn.commit()
            # The link itself is untouched -- the weaker check sees nothing
            # wrong, exactly reproducing the manager's finding.
            self.assertEqual(assertions_missing_evidence_link(conn), [])
            found = assertions_not_entailed_by_linked_observations(conn)
            self.assertEqual(len(found), 1)
            self.assertIn(
                "EXACT_TITLE_TEXT_NOT_OBSERVED_IN_ANY_LINKED_OBSERVATION",
                found[0]["reasons"],
            )
            conn.close()

    def test_role_family_not_derivable_from_title_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            ids = _seed(conn, Path(tmp), support=True)
            # The title text still matches its observation, but the stored
            # classification no longer matches what that title derives to.
            conn.execute(
                "UPDATE formal_role_assertion SET role_family = ? "
                "WHERE assertion_id = ?",
                ("offensive_coordinator", ids["assertion_id"]),
            )
            conn.commit()
            found = assertions_not_entailed_by_linked_observations(conn)
            self.assertEqual(len(found), 1)
            self.assertIn(
                "ROLE_FAMILY_NOT_DERIVABLE_FROM_EXACT_TITLE_TEXT",
                found[0]["reasons"],
            )
            conn.close()

    def test_title_with_no_classifiable_family_is_not_flagged_by_absence(self) -> None:
        """A title the HC/OC/DC classifier has no opinion about must not be
        treated as a role_family mismatch -- the classifier returning
        nothing is not evidence the stored family is wrong."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            source = Path(tmp) / "staff2.html"
            source.write_text(
                "<table><tr><td>B Coach</td><td>Strength Coach</td></tr></table>",
                encoding="utf-8",
            )
            source_file_id = register_source_file(
                conn, source, source_class="OFFICIAL_STAFF_HTML", rights_state="PRIVATE"
            )
            observation_id = add_observation(
                conn,
                source_file_id=source_file_id,
                locator="tr[0]",
                parser_identity="TEST",
                observed_person="B Coach",
                observed_title="Strength Coach",
                observed_program="P:1",
                observed_season="2026",
            )
            upsert_program(conn, "P:1", display_name="Example State", season=2026)
            person_id = upsert_person(conn, "B Coach", identity_basis="TEST")
            episode_id = add_episode(
                conn,
                person_id=person_id,
                program_id="P:1",
                season="2026",
                date_precision="SEASON",
                evidence_layer=LAYER_OFFICIAL,
            )
            add_role(
                conn,
                episode_id=episode_id,
                role_family="UNSPECIFIED_ASSISTANT",
                exact_title_text="Strength Coach",
                qualifiers=[],
                evidence_layer=LAYER_OFFICIAL,
                supporting_observations=[observation_id],
            )
            conn.commit()
            self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
            conn.close()

    def test_position_specific_role_family_is_not_judged_by_the_hc_oc_dc_classifier(self) -> None:
        """MF35-05: a title can classify as principal DC by
        `principal_role_families` AND separately name a position-specific
        assignment (e.g. inside linebackers) that classifier has no opinion
        about. A `formal_role_assertion` row for THAT position-specific
        role_family, linked to the same observation, must not be flagged --
        the classifier's silence on "inside_linebackers" is not evidence of
        a mismatch."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            title = "Assistant Head Coach/Inside Linebackers Coach/Co-Defensive Coordinator"
            source = Path(tmp) / "staff3.html"
            source.write_text(f"<table><tr><td>Mike Weick</td><td>{title}</td></tr></table>",
                              encoding="utf-8")
            source_file_id = register_source_file(
                conn, source, source_class="OFFICIAL_STAFF_HTML", rights_state="PRIVATE"
            )
            observation_id = add_observation(
                conn, source_file_id=source_file_id, locator="tr[0]",
                parser_identity="TEST", observed_person="Mike Weick",
                observed_title=title, observed_program="P:1", observed_season="2026",
            )
            upsert_program(conn, "P:1", display_name="Example State", season=2026)
            person_id = upsert_person(conn, "Mike Weick", identity_basis="TEST")
            episode_id = add_episode(
                conn, person_id=person_id, program_id="P:1", season="2026",
                date_precision="SEASON", evidence_layer=LAYER_OFFICIAL,
            )
            add_role(
                conn, episode_id=episode_id, role_family="inside_linebackers",
                exact_title_text=title, qualifiers=["CO"],
                evidence_layer=LAYER_OFFICIAL, supporting_observations=[observation_id],
            )
            add_role(
                conn, episode_id=episode_id, role_family="defensive_coordinator",
                exact_title_text=title, qualifiers=["CO"],
                evidence_layer=LAYER_OFFICIAL, supporting_observations=[observation_id],
            )
            conn.commit()
            self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
            conn.close()


class PersonIdentityAdjudicationTests(unittest.TestCase):
    """MF35-04: `upsert_person` keys identity on (name, identity_basis), so
    the same real person recorded from two source classes splits into two
    `canonical_person` rows -- and a genuinely different person who shares a
    name is indistinguishable from that split by `person_id` alone. These
    tests exercise the adjudication mechanism this repair adds: detecting
    candidates with real evidence signals, and recording (never inferring)
    a decision.
    """

    def _split_person(
        self, conn, tmp: Path, name: str, *, program_a: str, season_a: str,
        program_b: str, season_b: str, role_family: str = "defensive_coordinator",
    ) -> tuple[str, str]:
        """Two `canonical_person` rows for the same name, one per identity
        basis, each with one episode -- reproducing the exact
        OFFICIAL_STAFF_SAME_RECORD_BINDING / WIKIMEDIA_TEAM_SEASON_INFOBOX
        split the manager found in the real r7 release for Erik Chinander,
        Kirk Ciarrocca and Ted Roof."""

        upsert_program(conn, program_a, display_name=program_a, season=2026)
        upsert_program(conn, program_b, display_name=program_b, season=2026)
        official_id = upsert_person(
            conn, name, identity_basis="OFFICIAL_STAFF_SAME_RECORD_BINDING"
        )
        wiki_id = upsert_person(
            conn, name, identity_basis="WIKIMEDIA_TEAM_SEASON_INFOBOX"
        )
        ep_a = add_episode(
            conn, person_id=official_id, program_id=program_a, season=season_a,
            date_precision="SEASON", evidence_layer=LAYER_OFFICIAL,
        )
        add_role(
            conn, episode_id=ep_a, role_family=role_family,
            exact_title_text="Defensive Coordinator", qualifiers=[],
            evidence_layer=LAYER_OFFICIAL,
        )
        ep_b = add_episode(
            conn, person_id=wiki_id, program_id=program_b, season=season_b,
            date_precision="SEASON", evidence_layer=LAYER_CANDIDATE,
        )
        add_role(
            conn, episode_id=ep_b, role_family=role_family,
            exact_title_text="defensive_coordinator", qualifiers=[],
            evidence_layer=LAYER_CANDIDATE,
        )
        return official_id, wiki_id

    def test_true_alias_continuity_is_surfaced_without_being_merged(self) -> None:
        """The exact real-world pattern the manager found for Erik
        Chinander: OFFICIAL basis has him at Boise State (season CURRENT),
        WIKIMEDIA basis has him at Nebraska (season 2022) -- same role
        family, different programs, non-overlapping seasons. This is
        consistent with one person's career, but the function must still
        report it as a CANDIDATE with evidence, never as an automatic
        merge."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            official_id, wiki_id = self._split_person(
                conn, Path(tmp), "Erik Chinander",
                program_a="P:BOISE_STATE", season_a="CURRENT",
                program_b="P:NEBRASKA", season_b="2022",
            )
            conn.commit()
            candidates = person_identity_merge_candidates(conn)
            self.assertEqual(len(candidates), 1)
            candidate = candidates[0]
            self.assertEqual(candidate["canonical_name"], "Erik Chinander")
            self.assertEqual({candidate["left_person_id"], candidate["right_person_id"]},
                              {official_id, wiki_id})
            self.assertTrue(candidate["role_families_overlap"])
            self.assertFalse(candidate["overlapping_season_different_program"])
            self.assertEqual(candidate["shared_program_ids"], [])
            # No decision has been made -- the pair does not appear as
            # MERGED or DISTINCT anywhere just because it was detected.
            self.assertEqual(person_identity_adjudications(conn), [])
            conn.close()

    def test_false_namesake_is_distinguished_by_overlapping_conflicting_seasons(self) -> None:
        """Two same-named people who are NOT the same person: both have an
        episode in the exact same season at different programs, which a
        single real person cannot do. This must be flagged distinctly from
        the true-continuity case above."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            self._split_person(
                conn, Path(tmp), "John Namesake",
                program_a="P:SCHOOL_A", season_a="2020",
                program_b="P:SCHOOL_B", season_b="2020",
            )
            conn.commit()
            candidates = person_identity_merge_candidates(conn)
            self.assertEqual(len(candidates), 1)
            self.assertTrue(candidates[0]["overlapping_season_different_program"])
            conn.close()

    def test_shared_program_is_reported_as_the_strongest_signal(self) -> None:
        """The exact real-world pattern the manager found for Kirk
        Ciarrocca: both identities describe the SAME program (Rutgers)."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            self._split_person(
                conn, Path(tmp), "Kirk Ciarrocca",
                program_a="P:RUTGERS", season_a="CURRENT",
                program_b="P:RUTGERS", season_b="2026",
                role_family="offensive_coordinator",
            )
            conn.commit()
            candidates = person_identity_merge_candidates(conn)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["shared_program_ids"], ["P:RUTGERS"])
            conn.close()

    def test_same_name_same_basis_is_not_a_candidate(self) -> None:
        """upsert_person already collapses this case to one person_id -- it
        must not appear as a split candidate at all."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            upsert_person(conn, "Same Basis Coach", identity_basis="OFFICIAL_STAFF_SAME_RECORD_BINDING")
            upsert_person(conn, "Same Basis Coach", identity_basis="OFFICIAL_STAFF_SAME_RECORD_BINDING")
            conn.commit()
            self.assertEqual(person_identity_merge_candidates(conn), [])
            conn.close()

    def test_recording_a_decision_removes_the_pair_from_future_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            official_id, wiki_id = self._split_person(
                conn, Path(tmp), "Ted Roof",
                program_a="P:BOSTON_COLLEGE", season_a="CURRENT",
                program_b="P:NC_STATE", season_b="2018",
            )
            conn.commit()
            self.assertEqual(len(person_identity_merge_candidates(conn)), 1)

            record_person_identity_adjudication(
                conn,
                left_person_id=official_id,
                right_person_id=wiki_id,
                decision="UNRESOLVED_IDENTITY",
                decided_by="TEST",
                basis="same name and non-contradictory career timeline; no "
                "independent source-bound identifier available to confirm",
            )
            conn.commit()
            self.assertEqual(person_identity_merge_candidates(conn), [])
            recorded = person_identity_adjudications(conn)
            self.assertEqual(len(recorded), 1)
            self.assertEqual(recorded[0]["decision"], "UNRESOLVED_IDENTITY")
            conn.close()

    def test_merged_same_person_decision_is_recorded_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            official_id, wiki_id = self._split_person(
                conn, Path(tmp), "A Coach",
                program_a="P:X", season_a="CURRENT", program_b="P:X", season_b="2026",
            )
            conn.commit()
            record_person_identity_adjudication(
                conn, left_person_id=official_id, right_person_id=wiki_id,
                decision="MERGED_SAME_PERSON", decided_by="TEST",
                basis="same program, coincident season, independently corroborated",
            )
            conn.commit()
            recorded = person_identity_adjudications(conn)
            self.assertEqual(recorded[0]["decision"], "MERGED_SAME_PERSON")
            conn.close()

    def test_unknown_decision_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            with self.assertRaises(CoachingReleaseError):
                record_person_identity_adjudication(
                    conn, left_person_id="a", right_person_id="b",
                    decision="PROBABLY_THE_SAME_GUY", decided_by="TEST",
                    basis="vibes",
                )
            conn.close()

    def test_empty_basis_is_rejected(self) -> None:
        """A decision without a stated basis is exactly the "same name alone"
        reasoning the manager's finding warned against."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            with self.assertRaises(CoachingReleaseError):
                record_person_identity_adjudication(
                    conn, left_person_id="a", right_person_id="b",
                    decision="MERGED_SAME_PERSON", decided_by="TEST", basis="   ",
                )
            conn.close()

    def test_no_split_no_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            _seed(conn, Path(tmp))
            conn.commit()
            self.assertEqual(person_identity_merge_candidates(conn), [])
            conn.close()

    def test_same_name_same_basis_no_program_context_still_collapses(self) -> None:
        """The default (no source_program_id given) is unchanged: this is
        the safe backward-compatible behavior when a caller has no
        distinguishing context to offer."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            first = upsert_person(conn, "Test Namesake", identity_basis="TEST")
            second = upsert_person(conn, "Test Namesake", identity_basis="TEST")
            conn.commit()
            self.assertEqual(first, second)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM canonical_person").fetchone()[0], 1
            )
            conn.close()

    def test_same_name_same_basis_different_program_produces_two_people(self) -> None:
        """MF35-04 follow-up (20260920T224700Z): the manager's exact
        reproduction -- upsert_person keyed only on (name, identity_basis)
        made two DIFFERENT real people sharing a name under the same basis
        structurally impossible to represent separately. This is the fix:
        two calls with the SAME name and basis, but a DIFFERENT
        source_program_id, must now produce two distinct person_ids."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            first = upsert_person(
                conn, "Test Namesake", identity_basis="TEST",
                source_program_id="P:SCHOOL_A",
            )
            second = upsert_person(
                conn, "Test Namesake", identity_basis="TEST",
                source_program_id="P:SCHOOL_B",
            )
            conn.commit()
            self.assertNotEqual(first, second)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM canonical_person").fetchone()[0], 2
            )
            conn.close()

    def test_same_name_same_program_still_collapses(self) -> None:
        """The SAME real person re-observed at the SAME program (e.g. a
        second scrape of the same roster) must still collapse to one id --
        program-scoping must not fragment ordinary re-observation."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            first = upsert_person(
                conn, "A Coach", identity_basis="TEST", source_program_id="P:1"
            )
            second = upsert_person(
                conn, "A Coach", identity_basis="TEST", source_program_id="P:1"
            )
            conn.commit()
            self.assertEqual(first, second)
            conn.close()

    def test_same_basis_different_program_namesake_is_a_merge_candidate(self) -> None:
        """A genuinely represented namesake pair must now surface through
        the SAME candidate-detection path already used for cross-basis
        pairs -- MF35-04's mechanism, extended, not replaced."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            upsert_program(conn, "P:SCHOOL_A", display_name="School A")
            upsert_program(conn, "P:SCHOOL_B", display_name="School B")
            a = upsert_person(
                conn, "Test Namesake", identity_basis="TEST",
                source_program_id="P:SCHOOL_A",
            )
            b = upsert_person(
                conn, "Test Namesake", identity_basis="TEST",
                source_program_id="P:SCHOOL_B",
            )
            add_episode(
                conn, person_id=a, program_id="P:SCHOOL_A", season="2020",
                date_precision="SEASON", evidence_layer=LAYER_OFFICIAL,
            )
            add_episode(
                conn, person_id=b, program_id="P:SCHOOL_B", season="2021",
                date_precision="SEASON", evidence_layer=LAYER_OFFICIAL,
            )
            conn.commit()
            candidates = person_identity_merge_candidates(conn)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(
                {candidates[0]["left_person_id"], candidates[0]["right_person_id"]},
                {a, b},
            )
            self.assertEqual(
                candidates[0]["left_identity_basis"], candidates[0]["right_identity_basis"]
            )
            conn.close()

    def test_same_basis_overlapping_season_different_program_is_flagged_conflicting(
        self,
    ) -> None:
        """The real 'Tim Beck' pattern found in a full national rebuild:
        two same-basis identities with an episode in the EXACT SAME season
        at DIFFERENT programs -- real people cannot hold two simultaneous
        jobs, so this must be flagged as a genuine conflict signal, not
        silently treated the same as an ordinary career move."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            upsert_program(conn, "P:A", display_name="A")
            upsert_program(conn, "P:B", display_name="B")
            a = upsert_person(
                conn, "Tim Beck", identity_basis="TEST", source_program_id="P:A"
            )
            b = upsert_person(
                conn, "Tim Beck", identity_basis="TEST", source_program_id="P:B"
            )
            add_episode(
                conn, person_id=a, program_id="P:A", season="2020",
                date_precision="SEASON", evidence_layer=LAYER_OFFICIAL,
            )
            add_episode(
                conn, person_id=b, program_id="P:B", season="2020",
                date_precision="SEASON", evidence_layer=LAYER_OFFICIAL,
            )
            conn.commit()
            candidates = person_identity_merge_candidates(conn)
            self.assertEqual(len(candidates), 1)
            self.assertTrue(candidates[0]["overlapping_season_different_program"])
            conn.close()

    def test_same_basis_candidate_adjudication_removes_it_from_future_candidates(
        self,
    ) -> None:
        """The SAME adjudication mechanism already proven for cross-basis
        pairs works identically for same-basis pairs -- confirming this is
        an extension, not a parallel, disconnected mechanism."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            a = upsert_person(
                conn, "Test Namesake", identity_basis="TEST",
                source_program_id="P:SCHOOL_A",
            )
            b = upsert_person(
                conn, "Test Namesake", identity_basis="TEST",
                source_program_id="P:SCHOOL_B",
            )
            conn.commit()
            self.assertEqual(len(person_identity_merge_candidates(conn)), 1)
            record_person_identity_adjudication(
                conn, left_person_id=a, right_person_id=b,
                decision="DISTINCT_NAMESAKES", decided_by="TEST",
                basis="Two different real coaches confirmed by an independent "
                "biographical source; not the same person.",
            )
            conn.commit()
            self.assertEqual(person_identity_merge_candidates(conn), [])
            conn.close()

    def test_builder_end_to_end_produces_distinct_namesakes_at_different_programs(
        self,
    ) -> None:
        """MF35-04 explicitly requires exercising this through the builder
        and consumer, not only helper-unit tests: two rows in a real
        rebuild-rows JSONL file naming the same person at different
        programs must now resolve to two distinct canonical_person rows
        via the actual ingest_reparsed_staff production code path."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            raw_html = tmp / "staff.html"
            raw_html.write_text("<table></table>", encoding="utf-8")
            rows = [
                {
                    "raw_path": str(raw_html), "person": "Test Namesake",
                    "program_id": "P:SCHOOL_A", "source_title": "Head Coach",
                    "rebuilt_record_selector": "tr[0]",
                    "rebuilt_record_title": "Head Coach",
                    "episode_key": "k1", "strata": {"era": "CURRENT"},
                    "rebuilt_role_claim_supported": True,
                    "rebuilt_person_record_bound": True,
                    "disposition": "RETAINED_SUPPORTED",
                },
                {
                    "raw_path": str(raw_html), "person": "Test Namesake",
                    "program_id": "P:SCHOOL_B", "source_title": "Head Coach",
                    "rebuilt_record_selector": "tr[1]",
                    "rebuilt_record_title": "Head Coach",
                    "episode_key": "k2", "strata": {"era": "CURRENT"},
                    "rebuilt_role_claim_supported": True,
                    "rebuilt_person_record_bound": True,
                    "disposition": "RETAINED_SUPPORTED",
                },
            ]
            rebuild_rows = tmp / "rebuild_rows.jsonl"
            rebuild_rows.write_text(
                "\n".join(json.dumps(r) for r in rows), encoding="utf-8"
            )
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from tools.cycle35.r35_03_build_coaching_release import ingest_reparsed_staff

            conn = open_release(tmp / "release.sqlite")
            ingest_reparsed_staff(conn, rebuild_rows)
            conn.commit()
            people = conn.execute(
                "SELECT person_id FROM canonical_person WHERE canonical_name = ?",
                ("Test Namesake",),
            ).fetchall()
            self.assertEqual(len(people), 2)
            candidates = person_identity_merge_candidates(conn)
            self.assertEqual(len(candidates), 1)
            conn.close()


class VerificationLayerTests(unittest.TestCase):
    def test_a_predecessor_claim_is_held_not_inherited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            ids = _seed(conn, Path(tmp))
            conflict_id = record_conflict(
                conn,
                subject_kind="source_observation",
                subject_key=ids["observation_id"],
                reason="PREDECESSOR_CLAIMED_VERIFIED_WITHOUT_ROW_LEVEL_RECEIPT",
            )
            record_adjudication(
                conn,
                conflict_id=conflict_id,
                decision="HELD_AT_CANDIDATE_LAYER",
                decided_by="TEST",
                basis="no per-row receipt",
            )
            conn.commit()
            decision = conn.execute(
                "SELECT decision FROM adjudication WHERE conflict_id = ?",
                (conflict_id,),
            ).fetchone()["decision"]
            self.assertEqual(decision, "HELD_AT_CANDIDATE_LAYER")
            conn.close()

    def test_unknown_evidence_layer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            with self.assertRaises(CoachingReleaseError):
                add_episode(
                    conn,
                    person_id=None,
                    program_id=None,
                    season=None,
                    date_precision="SEASON",
                    evidence_layer="TOTALLY_VERIFIED_TRUST_ME",
                )
            conn.close()

    def test_layers_are_counted_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            ids = _seed(conn, Path(tmp))
            add_observation(
                conn,
                source_file_id=ids["source_file_id"],
                locator="tr[1]",
                parser_identity="TEST",
                observed_person="B Coach",
                observed_title="OC",
                evidence_layer=LAYER_CANDIDATE,
            )
            conn.commit()
            counts = layer_counts(conn)["source_observation"]
            self.assertEqual(counts[LAYER_CANDIDATE], 1)
            conn.close()


class TransactionTests(unittest.TestCase):
    def test_a_failed_import_leaves_no_partial_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            with self.assertRaises(RuntimeError):
                with transaction(conn):
                    upsert_program(conn, "P:1", display_name="Half", season=2026)
                    raise RuntimeError("import failed midway")
            count = conn.execute("SELECT COUNT(*) FROM canonical_program").fetchone()[0]
            self.assertEqual(count, 0)
            conn.close()

    def test_a_successful_import_commits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            with transaction(conn):
                upsert_program(conn, "P:1", display_name="Whole", season=2026)
            count = conn.execute("SELECT COUNT(*) FROM canonical_program").fetchone()[0]
            self.assertEqual(count, 1)
            conn.close()


class DeterminismTests(unittest.TestCase):
    def test_identities_are_content_addressed_not_sequential(self) -> None:
        self.assertEqual(stable_id("x", "a", 1), stable_id("x", "a", 1))
        self.assertNotEqual(stable_id("x", "a", 1), stable_id("x", "a", 2))
        self.assertTrue(stable_id("x", "a").startswith("x:"))

    def test_none_and_empty_string_are_distinguishable_in_an_identity(self) -> None:
        self.assertEqual(stable_id("x", None), stable_id("x", None))
        self.assertEqual(stable_id("x", ""), stable_id("x", None))

    def test_replay_reproduces_the_same_row_identities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            identities = []
            for name in ("a", "b"):
                conn = open_release(Path(tmp) / (name + ".sqlite"))
                with transaction(conn):
                    _seed(conn, Path(tmp))
                identities.append(release_row_identities(conn))
                conn.close()
            comparison = compare_releases(identities[0], identities[1])
            self.assertTrue(comparison["identical"], comparison["differences"])

    def test_different_inputs_produce_different_identities(self) -> None:
        """The comparison must be able to detect a real difference."""
        with tempfile.TemporaryDirectory() as tmp:
            conn_a = open_release(Path(tmp) / "a.sqlite")
            with transaction(conn_a):
                _seed(conn_a, Path(tmp))
            left = release_row_identities(conn_a)
            conn_a.close()

            conn_b = open_release(Path(tmp) / "b.sqlite")
            with transaction(conn_b):
                _seed(conn_b, Path(tmp))
                upsert_program(conn_b, "P:2", display_name="Other", season=2026)
            right = release_row_identities(conn_b)
            conn_b.close()

            comparison = compare_releases(left, right)
            self.assertFalse(comparison["identical"])
            self.assertEqual(comparison["differences"][0]["table"], "canonical_program")

    def test_a_non_key_field_mutation_is_detected_not_just_the_primary_key(self) -> None:
        """MF35-03: the manager cloned a real release and changed one role's
        `exact_title_text`, `role_family` and `evidence_layer` in place --
        same `assertion_id`, different scientific content. The prior
        `release_row_identities` hashed only the primary-key column and
        reported the two releases identical. It must not anymore."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            ids = _seed(conn, Path(tmp))
            conn.commit()
            left = release_row_identities(conn)

            conn.execute(
                "UPDATE formal_role_assertion SET exact_title_text = ?, "
                "role_family = ?, evidence_layer = ? WHERE assertion_id = ?",
                (
                    "Defensive Coordinator",
                    "defensive_coordinator",
                    LAYER_CANDIDATE,
                    ids["assertion_id"],
                ),
            )
            conn.commit()
            right = release_row_identities(conn)
            conn.close()

            comparison = compare_releases(left, right)
            self.assertFalse(comparison["identical"])
            tables_changed = {d["table"] for d in comparison["differences"]}
            self.assertIn("formal_role_assertion", tables_changed)
            # The count did not change -- only content did. A PK-only
            # comparison would have reported this pair as identical.
            changed = next(
                d for d in comparison["differences"]
                if d["table"] == "formal_role_assertion"
            )
            self.assertEqual(changed["left_count"], changed["right_count"])

    def test_assertion_support_table_is_covered_by_identities(self) -> None:
        """A mutation confined entirely to the link table (no assertion row
        touched at all) must still be detectable -- this table was
        previously omitted from `release_row_identities` altogether."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            ids = _seed(conn, Path(tmp))
            conn.commit()
            self.assertIn("assertion_support", release_row_identities(conn))
            left = release_row_identities(conn)

            other_source = Path(tmp) / "other.html"
            other_source.write_text("<p>other</p>", encoding="utf-8")
            other_file_id = register_source_file(
                conn, other_source, source_class="TEST", rights_state="TEST"
            )
            other_observation_id = add_observation(
                conn,
                source_file_id=other_file_id,
                locator="tr[9]",
                parser_identity="TEST",
                observed_person="A Coach",
                observed_title="Different Title",
            )
            conn.execute(
                "INSERT INTO assertion_support (assertion_id, assertion_table, "
                "observation_id) VALUES (?,?,?)",
                (ids["assertion_id"], "formal_role_assertion", other_observation_id),
            )
            conn.commit()
            right = release_row_identities(conn)
            conn.close()

            comparison = compare_releases(left, right)
            self.assertFalse(comparison["identical"])
            self.assertIn(
                "assertion_support",
                {d["table"] for d in comparison["differences"]},
            )

    def test_person_alias_table_is_covered_by_identities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            _seed(conn, Path(tmp))
            conn.commit()
            self.assertIn("person_alias", release_row_identities(conn))
            left = release_row_identities(conn)

            upsert_person(
                conn,
                "A Coach",
                identity_basis="TEST",
                aliases=[("A. Coach", "ABBREVIATED")],
            )
            conn.commit()
            right = release_row_identities(conn)
            conn.close()

            comparison = compare_releases(left, right)
            self.assertFalse(comparison["identical"])
            self.assertIn(
                "person_alias", {d["table"] for d in comparison["differences"]}
            )


class ManifestTests(unittest.TestCase):
    def test_manifest_is_append_only_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            append_release_manifest(path, {"release_id": "a"})
            append_release_manifest(path, {"release_id": "b"})
            append_release_manifest(path, {"release_id": "a"})
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["release_count"], 2)
            self.assertEqual(
                [row["release_id"] for row in manifest["releases"]], ["a", "b"]
            )

    def test_manifest_kind_mismatch_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps({"kind": "SOMETHING_ELSE"}), encoding="utf-8")
            with self.assertRaises(CoachingReleaseError):
                append_release_manifest(path, {"release_id": "a"})


if __name__ == "__main__":
    unittest.main()
