"""R35-05 tests for the career-tranche stage/schema contract.

The Cycle #35 manager follow-up (20260920T224700Z) corrected an earlier
misdiagnosis in this repository: `r35_05_career_tranche.py`'s first pass
emits an artifact with field `"keys"` (artifact_type
`CYCLE35_R35_05_CAREER_TRANCHE`); `r35_05_resolve_missing_keys.py`'s second
pass, run ON that first-pass output, emits the RESOLVED artifact with field
`"final_keys"` (artifact_type `CYCLE35_R35_05_CAREER_TRANCHE_SECOND_PASS`).
`ingest_career_tranche()` in the builder is documented -- and was always
intended -- to consume only the second-pass artifact. The real, confirmed
defect was never a field-name typo: it was that feeding the ingester the
WRONG stage silently ingested zero rows while still reporting a
success-shaped state (`INGESTED_AS_REVISION_BOUND_CANDIDATES`), with no
validation distinguishing "nothing to ingest because the payload is
malformed" from "nothing to ingest because the tranche is genuinely empty"
from "40 real rows ingested."

These tests exercise `validate_career_tranche_contract()` directly and
`ingest_career_tranche()` end-to-end, using the real producer output
shapes wherever the real artifacts are present in this environment.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aggie_analytics.cycle35 import coaching_release as cr  # noqa: E402
from tools.cycle35.r35_03_build_coaching_release import (  # noqa: E402
    CAREER_TRANCHE_SECOND_PASS_ARTIFACT_TYPE,
    ingest_career_tranche,
    validate_career_tranche_contract,
)

OLD_RUN = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260920T172801Z"
    r"\implementation_output"
)
NEW_RUN = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260920T215454Z_mf35_08_era_fix"
    r"\implementation_output"
)


def _ram_release() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cr.apply_migrations(conn)
    return conn


def _valid_key(**overrides) -> dict:
    row = {
        "key_id": "K01",
        "program_id": "P:TEST",
        "season": 2020,
        "role": "head_coach",
        "disposition": "ACCEPTED_SINGLE_SOURCE",
        "display_name": "Test State",
        "resolved_people": ["Test Coach"],
        "classification": "fbs",
    }
    row.update(overrides)
    return row


def _valid_payload(keys: list[dict] | None = None) -> dict:
    keys = keys if keys is not None else [_valid_key()]
    return {
        "artifact_type": CAREER_TRANCHE_SECOND_PASS_ARTIFACT_TYPE,
        "final_keys": keys,
        "key_count": len(keys),
    }


class ContractValidationTests(unittest.TestCase):
    def test_valid_resolved_payload_has_no_violations(self) -> None:
        self.assertEqual(validate_career_tranche_contract(_valid_payload()), [])

    def test_wrong_stage_artifact_type_is_rejected(self) -> None:
        payload = {"artifact_type": "CYCLE35_R35_05_CAREER_TRANCHE", "keys": [_valid_key()]}
        violations = validate_career_tranche_contract(payload)
        self.assertTrue(any("WRONG_STAGE_ARTIFACT_TYPE" in v for v in violations))
        self.assertTrue(any("FIRST_PASS_FIELD_PRESENT" in v for v in violations))

    def test_missing_artifact_type_is_rejected(self) -> None:
        payload = {"final_keys": [_valid_key()]}
        violations = validate_career_tranche_contract(payload)
        self.assertTrue(any("WRONG_STAGE_ARTIFACT_TYPE" in v for v in violations))

    def test_missing_final_keys_field_is_rejected_not_defaulted(self) -> None:
        payload = {"artifact_type": CAREER_TRANCHE_SECOND_PASS_ARTIFACT_TYPE}
        violations = validate_career_tranche_contract(payload)
        self.assertTrue(any("MISSING_REQUIRED_FIELD_FINAL_KEYS" in v for v in violations))

    def test_ambiguous_dual_field_payload_is_rejected(self) -> None:
        payload = {
            "artifact_type": CAREER_TRANCHE_SECOND_PASS_ARTIFACT_TYPE,
            "keys": [_valid_key(key_id="A")],
            "final_keys": [_valid_key(key_id="B")],
        }
        violations = validate_career_tranche_contract(payload)
        self.assertTrue(any("AMBIGUOUS_DUAL_FIELD_PAYLOAD" in v for v in violations))

    def test_final_keys_not_a_list_is_rejected(self) -> None:
        payload = {
            "artifact_type": CAREER_TRANCHE_SECOND_PASS_ARTIFACT_TYPE,
            "final_keys": {"not": "a list"},
        }
        violations = validate_career_tranche_contract(payload)
        self.assertTrue(any("FINAL_KEYS_NOT_A_LIST" in v for v in violations))

    def test_declared_count_mismatch_is_rejected(self) -> None:
        payload = _valid_payload([_valid_key()])
        payload["key_count"] = 5
        violations = validate_career_tranche_contract(payload)
        self.assertTrue(any("DECLARED_COUNT_MISMATCH" in v for v in violations))

    def test_key_missing_required_field_is_rejected(self) -> None:
        bad_key = _valid_key()
        del bad_key["program_id"]
        payload = _valid_payload([bad_key])
        violations = validate_career_tranche_contract(payload)
        self.assertTrue(any("KEY_MISSING_REQUIRED_FIELDS" in v for v in violations))

    def test_key_unknown_disposition_is_rejected(self) -> None:
        payload = _valid_payload([_valid_key(disposition="PROBABLY_FINE")])
        violations = validate_career_tranche_contract(payload)
        self.assertTrue(any("KEY_UNKNOWN_DISPOSITION" in v for v in violations))

    def test_duplicate_key_id_conflicting_content_is_rejected(self) -> None:
        a = _valid_key(key_id="DUP")
        b = _valid_key(key_id="DUP", season=2021)
        violations = validate_career_tranche_contract(_valid_payload([a, b]))
        self.assertTrue(any("DUPLICATE_KEY_ID_CONFLICTING_CONTENT" in v for v in violations))

    def test_duplicate_key_id_identical_content_is_not_rejected(self) -> None:
        a = _valid_key(key_id="DUP")
        b = _valid_key(key_id="DUP")
        violations = validate_career_tranche_contract(_valid_payload([a, b]))
        self.assertEqual(violations, [])

    def test_payload_not_an_object_is_rejected(self) -> None:
        violations = validate_career_tranche_contract(["not", "a", "dict"])
        self.assertTrue(any("PAYLOAD_NOT_AN_OBJECT" in v for v in violations))

    def test_key_not_an_object_is_rejected(self) -> None:
        payload = _valid_payload(["not a dict"])
        violations = validate_career_tranche_contract(payload)
        self.assertTrue(any("KEY_NOT_AN_OBJECT" in v for v in violations))


class IngestEndToEndTests(unittest.TestCase):
    def _write(self, tmp: Path, payload: dict) -> Path:
        path = tmp / "tranche.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_valid_resolved_input_ingests_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), _valid_payload())
            conn = _ram_release()
            stats = ingest_career_tranche(conn, path)
            self.assertEqual(stats["state"], "INGESTED_AS_REVISION_BOUND_CANDIDATES")
            self.assertEqual(
                conn.execute("select count(*) from source_observation").fetchone()[0], 1
            )
            self.assertEqual(
                conn.execute("select count(*) from employment_episode").fetchone()[0], 1
            )
            conn.close()

    def test_wrong_stage_input_is_rejected_and_ingests_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first_pass = {
                "artifact_type": "CYCLE35_R35_05_CAREER_TRANCHE",
                "keys": [_valid_key()],
            }
            path = self._write(Path(tmp), first_pass)
            conn = _ram_release()
            stats = ingest_career_tranche(conn, path)
            self.assertEqual(stats["state"], "REJECTED_INVALID_CONTRACT")
            self.assertTrue(stats["contract_violations"])
            self.assertEqual(
                conn.execute("select count(*) from source_observation").fetchone()[0], 0
            )
            conn.close()

    def test_absent_final_keys_list_is_rejected_not_ingested_as_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                Path(tmp), {"artifact_type": CAREER_TRANCHE_SECOND_PASS_ARTIFACT_TYPE}
            )
            conn = _ram_release()
            stats = ingest_career_tranche(conn, path)
            self.assertEqual(stats["state"], "REJECTED_INVALID_CONTRACT")
            conn.close()

    def test_conflicting_dual_field_payload_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = {
                "artifact_type": CAREER_TRANCHE_SECOND_PASS_ARTIFACT_TYPE,
                "keys": [_valid_key(key_id="A")],
                "final_keys": [_valid_key(key_id="B")],
            }
            path = self._write(Path(tmp), payload)
            conn = _ram_release()
            stats = ingest_career_tranche(conn, path)
            self.assertEqual(stats["state"], "REJECTED_INVALID_CONTRACT")
            conn.close()

    def test_legitimately_empty_tranche_is_distinguished_from_rejection(self) -> None:
        """A VALID contract with zero keys (e.g. every predeclared key
        stayed MISSING) must report a distinct, honest state -- not the
        same success-shaped state a real ingest gets, and not the same
        state a contract violation gets."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), _valid_payload(keys=[]))
            conn = _ram_release()
            stats = ingest_career_tranche(conn, path)
            self.assertEqual(stats["state"], "CONTRACT_VALID_BUT_ZERO_KEYS_RESOLVED")
            self.assertNotEqual(stats["state"], "REJECTED_INVALID_CONTRACT")
            self.assertNotEqual(stats["state"], "INGESTED_AS_REVISION_BOUND_CANDIDATES")
            conn.close()

    def test_all_missing_keys_with_no_people_is_zero_observations_not_rejection(self) -> None:
        keys = [
            _valid_key(key_id="K01", disposition="MISSING_NO_EVIDENCE", resolved_people=[])
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), _valid_payload(keys))
            conn = _ram_release()
            stats = ingest_career_tranche(conn, path)
            self.assertEqual(stats["state"], "CONTRACT_VALID_BUT_ZERO_KEYS_RESOLVED")
            self.assertEqual(stats["KEY_MISSING_NO_EVIDENCE"], 1)
            conn.close()

    def test_duplicate_replayed_intake_is_idempotent(self) -> None:
        """Feeding the identical tranche file to the SAME database twice
        (e.g. an accidental double-call) must not double-insert rows --
        content-addressed identities make this naturally idempotent."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), _valid_payload())
            conn = _ram_release()
            first = ingest_career_tranche(conn, path)
            second = ingest_career_tranche(conn, path)
            self.assertEqual(first["state"], "INGESTED_AS_REVISION_BOUND_CANDIDATES")
            self.assertEqual(second["state"], "INGESTED_AS_REVISION_BOUND_CANDIDATES")
            self.assertEqual(
                conn.execute("select count(*) from source_observation").fetchone()[0], 1
            )
            self.assertEqual(
                conn.execute("select count(*) from employment_episode").fetchone()[0], 1
            )
            conn.close()

    def test_duplicate_key_id_within_one_payload_is_not_double_ingested(self) -> None:
        a = _valid_key(key_id="DUP")
        b = _valid_key(key_id="DUP")
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), _valid_payload([a, b]))
            conn = _ram_release()
            stats = ingest_career_tranche(conn, path)
            self.assertEqual(stats["state"], "INGESTED_AS_REVISION_BOUND_CANDIDATES")
            self.assertEqual(stats["DUPLICATE_KEY_ID_IN_PAYLOAD_SKIPPED"], 1)
            self.assertEqual(
                conn.execute("select count(*) from employment_episode").fetchone()[0], 1
            )
            conn.close()

    def test_conflict_key_writes_a_conflict_row_and_promotes_neither(self) -> None:
        key = _valid_key(
            disposition="CONFLICT", resolved_people=["Coach One", "Coach Two"]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), _valid_payload([key]))
            conn = _ram_release()
            stats = ingest_career_tranche(conn, path)
            self.assertEqual(stats["KEY_CONFLICT"], 1)
            self.assertEqual(stats["CONFLICTS"], 1)
            self.assertEqual(
                conn.execute("select count(*) from employment_episode").fetchone()[0], 0
            )
            self.assertEqual(
                conn.execute("select count(*) from conflict").fetchone()[0], 1
            )
            conn.close()

    def test_ingested_role_exact_title_text_matches_observed_title(self) -> None:
        """A prior version of this ingester set exact_title_text from
        second_pass_parameter (e.g. "hc"), which could diverge from the
        linked observation's own observed_title (always the role name) and
        would fail the MF35-03 entailment check. Confirms they now agree."""
        key = _valid_key(second_pass_parameter="hc")
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), _valid_payload([key]))
            conn = _ram_release()
            ingest_career_tranche(conn, path)
            self.assertEqual(cr.assertions_missing_evidence_link(conn), [])
            self.assertEqual(
                cr.assertions_not_entailed_by_linked_observations(conn), []
            )
            conn.close()

    def test_not_present_file_is_a_distinct_state_not_a_rejection(self) -> None:
        conn = _ram_release()
        stats = ingest_career_tranche(conn, Path("/does/not/exist.json"))
        self.assertEqual(stats["state"], "CAREER_TRANCHE_NOT_PRESENT")
        conn.close()


class RealProducerArtifactTests(unittest.TestCase):
    """Exercises the fix against the actual r35_05_career_tranche.py /
    r35_05_resolve_missing_keys.py output shapes, when present."""

    def test_real_first_pass_artifact_is_rejected(self) -> None:
        path = NEW_RUN / "R35_05_CAREER_TRANCHE.json"
        if not path.is_file():
            self.skipTest("real first-pass artifact not present in this environment")
        conn = _ram_release()
        stats = ingest_career_tranche(conn, path)
        self.assertEqual(stats["state"], "REJECTED_INVALID_CONTRACT")
        conn.close()

    def test_real_second_pass_final_artifact_ingests_matching_r7_counts(self) -> None:
        """The manager's exact reproduction: the OLD run's resolved FINAL
        artifact must ingest 40 observations / 36 episodes, matching the
        real predecessor r7 release's independently-stored counts."""
        path = OLD_RUN / "R35_05_CAREER_TRANCHE_FINAL.json"
        if not path.is_file():
            self.skipTest("real second-pass artifact not present in this environment")
        conn = _ram_release()
        stats = ingest_career_tranche(conn, path)
        self.assertEqual(stats["state"], "INGESTED_AS_REVISION_BOUND_CANDIDATES")
        self.assertEqual(
            conn.execute("select count(*) from source_observation").fetchone()[0], 40
        )
        self.assertEqual(
            conn.execute("select count(*) from employment_episode").fetchone()[0], 36
        )
        conn.close()

    def test_corrected_era_fixed_final_artifact_is_contract_valid(self) -> None:
        path = NEW_RUN / "R35_05_CAREER_TRANCHE_FINAL.json"
        if not path.is_file():
            self.skipTest("corrected second-pass artifact not present in this environment")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(validate_career_tranche_contract(payload), [])
        conn = _ram_release()
        stats = ingest_career_tranche(conn, path)
        self.assertEqual(stats["state"], "INGESTED_AS_REVISION_BOUND_CANDIDATES")
        self.assertEqual(cr.assertions_missing_evidence_link(conn), [])
        self.assertEqual(cr.assertions_not_entailed_by_linked_observations(conn), [])
        conn.close()


if __name__ == "__main__":
    unittest.main()
