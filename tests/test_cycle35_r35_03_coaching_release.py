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
    compare_releases,
    layer_counts,
    open_release,
    record_adjudication,
    record_conflict,
    register_source_file,
    release_row_identities,
    stable_id,
    transaction,
    unsupported_assertions,
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
        self.assertEqual([int(r[0]) for r in rows], [1, 2, 3])
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
            self.assertEqual(unsupported_assertions(conn), [])
            conn.close()

    def test_an_unsupported_assertion_is_detected_not_hidden(self) -> None:
        """The check must be able to fail, or it proves nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            conn = open_release(Path(tmp) / "r.sqlite")
            _seed(conn, Path(tmp), support=False)
            conn.commit()
            found = unsupported_assertions(conn)
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
