"""Cycle #37 - Attempt #2 - ACTUAL_STATE

MF36-05: multiplicity, row order and request authenticity in the membership
prover.

The predecessor bound a derivative to a season when the transform's output
and the file agreed *as sets*, and it never looked at the request identity a
receipt declared. Three consequences, each a test here:

* a file whose rows are the transform's rows with one repeated was "proved";
* a file whose rows were reversed was "proved";
* a receipt carrying any string at all in ``request_identity`` was "proved".

The fourth group pins the distinction MF36-05 names but which is not a
defect: a cache filename identifies a request without attesting that one was
issued, so reproduction by cache-reconstructed receipts alone must be
labelled differently from reproduction by a declared attempt.

Every negative control has a positive control beside it. A prover that
refuses everything is not repaired.
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

from aggie_analytics.cycle30.hashing import sha256_json  # noqa: E402
from aggie_analytics.cycle36.membership_lineage import (  # noqa: E402
    ATTESTED,
    ATTESTED_NO_SUCCESS,
    BASIS_CACHE_FILENAME,
    BASIS_LEDGER,
    IDENTITY_ABSENT,
    IDENTITY_AUTHENTIC,
    IDENTITY_CONVENTIONS,
    IDENTITY_FORGED,
    LINEAGE_VERSION,
    PREDECESSOR_LINEAGE_VERSION,
    PROVED,
    PROVED_UNATTESTED,
    RECEIPT_REPRODUCES,
    RECEIPT_SET_ONLY,
    RECEIPT_UNAUTHENTIC,
    REFUSED_NO_RECEIPT,
    REFUSED_SET_MATCH_ONLY,
    UNATTESTED,
    Receipt,
    authenticate_request_identity,
    compare_rows,
    prove_lineage,
)

ENDPOINT = "/teams"
TRANSFORM = "TEAMS_FBS_FCS_V1"

PAYLOAD = [
    {"id": 1, "classification": "fbs"},
    {"id": 2, "classification": "fcs"},
    {"id": 3, "classification": "iii"},
]
EXPECTED = ["1", "2"]


def ledger_identity(year: int) -> str:
    """The identity ``acquire_cycle30_national`` writes on a cache hit."""

    return sha256_json({"path": ENDPOINT, "parameters": {"year": year}})


def cache_identity(year: int) -> str:
    """The identity its ``cache_path`` writes as the cache filename."""

    return sha256_json({"endpoint": ENDPOINT, "parameters": {"year": year}})


#: A sentinel so that ``identity=None`` means "declare no identity" rather
#: than "use the default one". The first version of this fixture used None
#: for both and the missing-identity test silently exercised the authentic
#: case instead.
_DEFAULT_IDENTITY = object()


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.path = Path(self.holder.name) / "payload.json"
        raw = json.dumps(PAYLOAD).encode("utf-8")
        self.path.write_bytes(raw)
        self.digest = hashlib.sha256(raw).hexdigest()

    def receipt(
        self,
        year: int = 2026,
        *,
        identity: object = _DEFAULT_IDENTITY,
        basis: str = BASIS_LEDGER,
        http_status: object = 200,
        retrieved: str | None = "2026-09-09T18:08:43Z",
        cached: bool = True,
    ) -> Receipt:
        return Receipt(
            endpoint=ENDPOINT,
            parameters={"year": year},
            declared_digest=self.digest,
            request_identity=(
                ledger_identity(year)
                if identity is _DEFAULT_IDENTITY
                else identity  # type: ignore[arg-type]
            ),
            cached_path=str(self.path) if cached else None,
            actual_digest=self.digest if cached else None,
            retrieved_at_utc=retrieved,
            http_status=http_status,
            payload_rows=len(PAYLOAD),
            identity_basis=basis,
        )


class PositiveControls(Base):
    def test_exact_row_reproduction_still_proves_the_season(self) -> None:
        result = prove_lineage(list(EXPECTED), [self.receipt()], TRANSFORM)
        self.assertEqual(result["state"], PROVED)
        self.assertEqual(result["bound_year"], 2026)
        self.assertEqual(result["bound_acquisition_attestation"], ATTESTED)

    def test_the_binding_convention_is_named(self) -> None:
        result = prove_lineage(list(EXPECTED), [self.receipt()], TRANSFORM)
        self.assertEqual(
            result["bound_request_identity_convention"],
            "CYCLE30_LEDGER_CACHE_HIT_PATH_PARAMETERS_V1",
        )

    def test_two_byte_identical_requests_of_one_year_still_prove(self) -> None:
        result = prove_lineage(
            list(EXPECTED), [self.receipt(), self.receipt()], TRANSFORM
        )
        self.assertEqual(result["state"], PROVED)
        self.assertFalse(result["request_identity_unique"])

    def test_an_unrelated_authentic_receipt_does_not_disturb_authority(self) -> None:
        other = Receipt(
            endpoint=ENDPOINT,
            parameters={"year": 2019},
            declared_digest="0" * 64,
            request_identity=ledger_identity(2019),
            cached_path=None,
            actual_digest=None,
            retrieved_at_utc="2026-09-09T18:08:43Z",
            http_status=200,
            payload_rows=0,
        )
        alone = prove_lineage(list(EXPECTED), [self.receipt()], TRANSFORM)
        together = prove_lineage(list(EXPECTED), [self.receipt(), other], TRANSFORM)
        self.assertEqual(alone["state"], PROVED)
        self.assertEqual(together["state"], PROVED)
        self.assertEqual(alone["bound_year"], together["bound_year"])


class MultiplicityTests(Base):
    def test_a_repeated_row_is_not_a_reproduction(self) -> None:
        result = prove_lineage(["1", "1", "2"], [self.receipt()], TRANSFORM)
        self.assertFalse(str(result["state"]).startswith("PROVED"))
        self.assertIsNone(result["bound_year"])

    def test_every_row_repeated_is_not_a_reproduction(self) -> None:
        result = prove_lineage(["1", "2", "1", "2"], [self.receipt()], TRANSFORM)
        self.assertFalse(str(result["state"]).startswith("PROVED"))

    def test_the_repeated_identifier_is_named_with_both_counts(self) -> None:
        result = prove_lineage(["1", "1", "2"], [self.receipt()], TRANSFORM)
        comparison = result["evaluations"][0]["comparison"]
        self.assertEqual(
            comparison["multiplicity_differences"],
            [{"source_entity_id": "1", "in_transform_output": 1, "in_file": 2}],
        )

    def test_a_duplicated_file_still_matches_as_a_set(self) -> None:
        """The predecessor's test, kept as the reason it was not enough."""

        comparison = compare_rows(
            [{"source_entity_id": "1"}, {"source_entity_id": "2"}], ["1", "1", "2"]
        )
        self.assertTrue(comparison["exact_set_match"])
        self.assertFalse(comparison["exact_row_reproduction"])
        self.assertTrue(comparison["set_matches_but_rows_do_not"])


class OrderTests(Base):
    def test_reversed_rows_are_not_a_reproduction(self) -> None:
        result = prove_lineage(list(reversed(EXPECTED)), [self.receipt()], TRANSFORM)
        self.assertEqual(result["state"], REFUSED_SET_MATCH_ONLY)
        self.assertIsNone(result["bound_year"])

    def test_the_first_divergent_row_index_is_reported(self) -> None:
        result = prove_lineage(list(reversed(EXPECTED)), [self.receipt()], TRANSFORM)
        self.assertEqual(
            result["evaluations"][0]["comparison"]["first_divergent_row_index"], 0
        )

    def test_a_set_only_match_is_reported_apart_from_no_match(self) -> None:
        reordered = prove_lineage(
            list(reversed(EXPECTED)), [self.receipt()], TRANSFORM
        )
        unrelated = prove_lineage(["77"], [self.receipt()], TRANSFORM)
        self.assertEqual(reordered["state"], REFUSED_SET_MATCH_ONLY)
        self.assertEqual(unrelated["state"], REFUSED_NO_RECEIPT)
        self.assertEqual(reordered["evaluations"][0]["result"], RECEIPT_SET_ONLY)

    def test_a_longer_file_reports_the_index_where_it_runs_past(self) -> None:
        comparison = compare_rows(
            [{"source_entity_id": "1"}], ["1", "2"]
        )
        self.assertEqual(comparison["first_divergent_row_index"], 1)


class RequestAuthenticityTests(Base):
    def test_an_invented_identity_cannot_prove(self) -> None:
        result = prove_lineage(
            list(EXPECTED), [self.receipt(identity="request-2026")], TRANSFORM
        )
        self.assertEqual(result["state"], REFUSED_NO_RECEIPT)
        self.assertEqual(result["evaluations"][0]["result"], RECEIPT_UNAUTHENTIC)

    def test_a_well_formed_digest_of_nothing_cannot_prove(self) -> None:
        result = prove_lineage(
            list(EXPECTED), [self.receipt(identity="f" * 64)], TRANSFORM
        )
        self.assertEqual(result["state"], REFUSED_NO_RECEIPT)

    def test_another_years_identity_cannot_prove_this_year(self) -> None:
        result = prove_lineage(
            list(EXPECTED), [self.receipt(identity=ledger_identity(2019))], TRANSFORM
        )
        self.assertEqual(result["state"], REFUSED_NO_RECEIPT)
        self.assertEqual(
            result["evaluations"][0]["receipt"]["request_identity_state"],
            IDENTITY_FORGED,
        )

    def test_a_missing_identity_cannot_prove(self) -> None:
        result = prove_lineage(list(EXPECTED), [self.receipt(identity=None)], TRANSFORM)
        self.assertEqual(result["state"], REFUSED_NO_RECEIPT)
        self.assertEqual(
            result["evaluations"][0]["receipt"]["request_identity_state"],
            IDENTITY_ABSENT,
        )

    def test_the_unauthentic_receipt_count_is_published(self) -> None:
        result = prove_lineage(
            list(EXPECTED),
            [self.receipt(identity="a"), self.receipt(identity="b"), self.receipt()],
            TRANSFORM,
        )
        self.assertEqual(result["receipts_with_unauthentic_request_identity"], 2)
        self.assertEqual(result["state"], PROVED)

    def test_identity_is_checked_before_the_bytes(self) -> None:
        """An unauthentic receipt is refused for the right reason.

        A receipt with no cached bytes AND an invented identity must report
        the identity, because that is the failure that matters: bytes can be
        re-acquired, an identity that recomputes to nothing never becomes
        this request's identity.
        """

        result = prove_lineage(
            list(EXPECTED),
            [self.receipt(identity="request-2026", cached=False)],
            TRANSFORM,
        )
        self.assertEqual(result["evaluations"][0]["result"], RECEIPT_UNAUTHENTIC)

    def test_each_named_convention_authenticates_its_own_output(self) -> None:
        for name, fn in IDENTITY_CONVENTIONS.items():
            with self.subTest(convention=name):
                declared = fn(ENDPOINT, {"year": 2026})
                check = authenticate_request_identity(
                    ENDPOINT, {"year": 2026}, declared
                )
                self.assertEqual(check["state"], IDENTITY_AUTHENTIC)
                self.assertIn(name, check["all_matching_conventions"])

    def test_the_conventions_do_not_collide(self) -> None:
        produced = {
            fn(ENDPOINT, {"year": 2026}) for fn in IDENTITY_CONVENTIONS.values()
        }
        self.assertEqual(len(produced), len(IDENTITY_CONVENTIONS))

    def test_parameters_are_part_of_the_identity(self) -> None:
        declared = sha256_json(
            {"path": ENDPOINT, "parameters": {"year": 2026, "classification": "fbs"}}
        )
        check = authenticate_request_identity(ENDPOINT, {"year": 2026}, declared)
        self.assertEqual(check["state"], IDENTITY_FORGED)


class AttestationTests(Base):
    def test_a_cache_filename_proves_under_a_weaker_state(self) -> None:
        result = prove_lineage(
            list(EXPECTED),
            [
                self.receipt(
                    identity=cache_identity(2026),
                    basis=BASIS_CACHE_FILENAME,
                    http_status=None,
                    retrieved=None,
                )
            ],
            TRANSFORM,
        )
        self.assertEqual(result["state"], PROVED_UNATTESTED)
        self.assertEqual(result["bound_year"], 2026)
        self.assertEqual(result["attested_reproducing_receipts"], 0)

    def test_the_two_proved_states_are_distinguishable(self) -> None:
        self.assertNotEqual(PROVED, PROVED_UNATTESTED)
        self.assertTrue(PROVED_UNATTESTED.startswith(PROVED))

    def test_a_declared_attempt_is_preferred_as_the_binding_receipt(self) -> None:
        cache_only = self.receipt(
            identity=cache_identity(2026),
            basis=BASIS_CACHE_FILENAME,
            http_status=None,
            retrieved=None,
        )
        result = prove_lineage(
            list(EXPECTED), [cache_only, self.receipt()], TRANSFORM
        )
        self.assertEqual(result["state"], PROVED)
        self.assertEqual(result["bound_request_identity"], ledger_identity(2026))

    def test_a_failed_declared_attempt_is_not_attested(self) -> None:
        receipt = self.receipt(http_status=500)
        self.assertEqual(receipt.attestation, ATTESTED_NO_SUCCESS)

    def test_a_non_numeric_status_is_not_a_success(self) -> None:
        receipt = self.receipt(http_status="CACHE_HIT")
        self.assertEqual(receipt.attestation, ATTESTED_NO_SUCCESS)

    def test_a_declared_attempt_without_a_time_is_not_attested(self) -> None:
        receipt = self.receipt(retrieved=None)
        self.assertEqual(receipt.attestation, ATTESTED_NO_SUCCESS)

    def test_a_cache_receipt_never_attests_however_it_is_filled_in(self) -> None:
        receipt = self.receipt(
            basis=BASIS_CACHE_FILENAME, http_status=200, retrieved="2026-01-01T00:00:00Z"
        )
        self.assertEqual(receipt.attestation, UNATTESTED)


class VersionTests(Base):
    def test_the_version_names_the_change(self) -> None:
        self.assertEqual(LINEAGE_VERSION, "BAS-MEMBERSHIP-EXACT-LINEAGE-v37.1")
        self.assertNotEqual(LINEAGE_VERSION, PREDECESSOR_LINEAGE_VERSION)

    def test_a_proved_record_carries_the_new_version(self) -> None:
        result = prove_lineage(list(EXPECTED), [self.receipt()], TRANSFORM)
        self.assertEqual(result["lineage_version"], LINEAGE_VERSION)

    def test_the_per_receipt_result_vocabulary_is_stable(self) -> None:
        result = prove_lineage(list(EXPECTED), [self.receipt()], TRANSFORM)
        self.assertEqual(result["evaluations"][0]["result"], RECEIPT_REPRODUCES)


if __name__ == "__main__":
    unittest.main()
