from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "artifacts/source_governance/source_access_smoke_results.json"
CONTRACT_PATH = ROOT / "artifacts/source_governance/credential_contract.redacted.json"
INVENTORY_PATH = ROOT / "artifacts/source_governance/source_inventory_validation.json"
SHA256_HEX_LENGTH = 64
REQUIRED_RESULT_FIELDS = {
    "api_version",
    "api_version_basis",
    "attempted",
    "blocker",
    "bulk_download",
    "credential_value_included",
    "http_status",
    "rate_limit_metadata",
    "response_body_retained",
    "response_schema_sha256",
    "retrieved_at_utc",
    "source_id",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validation_errors(payload: dict, contract: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != 2:
        errors.append("schema-version")
    if payload.get("artifact_type") != "BOUNDED_SOURCE_ACCESS_SMOKE_RESULTS":
        errors.append("artifact-type")
    producer = payload.get("producer", {})
    if len(producer.get("script_sha256", "")) != SHA256_HEX_LENGTH:
        errors.append("producer-provenance")

    identities = {item.get("path"): item.get("sha256") for item in payload.get("input_identities", [])}
    expected_identities = {
        "artifacts/source_governance/source_inventory_validation.json": _sha256(INVENTORY_PATH),
        "artifacts/source_governance/credential_contract.redacted.json": _sha256(CONTRACT_PATH),
    }
    if identities != expected_identities:
        errors.append("stale-or-incomplete-input-provenance")

    expected_ids = {item["source_id"] for item in contract["source_bindings"]}
    results = payload.get("results", [])
    actual_ids = [item.get("source_id") for item in results]
    if len(actual_ids) != len(expected_ids) or set(actual_ids) != expected_ids:
        errors.append("source-coverage")
    if len(actual_ids) != len(set(actual_ids)):
        errors.append("duplicate-source")

    for item in results:
        source_id = item.get("source_id", "UNKNOWN")
        if not REQUIRED_RESULT_FIELDS.issubset(item):
            errors.append(f"required-fields:{source_id}")
            continue
        if item["credential_value_included"] or item["response_body_retained"] or item["bulk_download"]:
            errors.append(f"security-minimization:{source_id}")
        rate_limit = item["rate_limit_metadata"]
        if not {"metadata_observed", "observed_safe_headers", "safe_header_allowlist", "unobserved_reason"}.issubset(rate_limit):
            errors.append(f"rate-limit-metadata:{source_id}")
        if item["attempted"]:
            if item["disposition"] == "TECHNICAL_SMOKE_SUCCEEDED":
                if item["http_status"] != 200 or len(item["response_schema_sha256"] or "") != SHA256_HEX_LENGTH:
                    errors.append(f"successful-probe-observations:{source_id}")
                if item["blocker"] is not None:
                    errors.append(f"stale-blocker:{source_id}")
            elif not item["blocker"]:
                errors.append(f"technical-blocker:{source_id}")
        else:
            if item["disposition"] != "TECHNICAL_VALIDATION_PENDING" or not item["blocker"]:
                errors.append(f"technical-pending:{source_id}")
            if item["http_status"] is not None or item["response_schema_sha256"] is not None:
                errors.append(f"fabricated-observation:{source_id}")

    scope = payload.get("scope", {})
    if scope.get("production_approved_source_count") != 62:
        errors.append("private-policy-coverage")
    if scope.get("production_access_ready_count") != 3 or scope.get("rights_blocked_source_count") != 0:
        errors.append("technical-readiness-summary")
    if scope.get("rights_approval_claimed") is not False:
        errors.append("unsupported-rights-approval")
    if set(scope.get("representative_smoke_source_ids", [])) != {"SRC-002", "SRC-061", "SRC-062"}:
        errors.append("bounded-smoke-scope")
    if payload.get("eligibility", {}).get("production_access_ready") is not False:
        errors.append("eligibility-boundary")
    return errors


class TestSourceAccessSmokeResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = _load(RESULTS_PATH)
        cls.contract = _load(CONTRACT_PATH)

    def test_metadata_only_smoke_contract_is_complete(self) -> None:
        self.assertEqual(_validation_errors(self.payload, self.contract), [])

    def test_three_bounded_lanes_succeeded_under_private_research_policy(self) -> None:
        attempted = {item["source_id"]: item for item in self.payload["results"] if item["attempted"]}
        self.assertEqual(set(attempted), {"SRC-002", "SRC-061", "SRC-062"})
        for result in attempted.values():
            with self.subTest(source_id=result["source_id"]):
                self.assertEqual(result["http_status"], 200)
                self.assertTrue(result["minimally_sufficient_response"])
                self.assertFalse(result["response_body_retained"])
                self.assertLessEqual(result["response_bytes_observed_not_retained"], 65536)
                self.assertIsNone(result["blocker"])

    def test_downstream_consumer_rejects_invalid_or_stale_inputs(self) -> None:
        mutations = []
        missing = copy.deepcopy(self.payload)
        missing["results"].pop()
        mutations.append(missing)
        stale = copy.deepcopy(self.payload)
        stale["input_identities"][0]["sha256"] = "0" * SHA256_HEX_LENGTH
        mutations.append(stale)
        incompatible = copy.deepcopy(self.payload)
        incompatible["schema_version"] = 99
        mutations.append(incompatible)
        technical_evidence_weakened = copy.deepcopy(self.payload)
        technical_evidence_weakened["results"][0]["blocker"] = None
        mutations.append(technical_evidence_weakened)
        provenance_missing = copy.deepcopy(self.payload)
        provenance_missing["producer"]["script_sha256"] = ""
        mutations.append(provenance_missing)
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                self.assertTrue(_validation_errors(mutation, self.contract))

    def test_security_summary_matches_per_source_evidence(self) -> None:
        security = self.payload["security_and_minimization"]
        self.assertFalse(security["credential_values_included"])
        self.assertFalse(security["response_bodies_included"])
        self.assertFalse(security["restricted_raw_data_included"])
        self.assertFalse(security["bulk_download_performed"])
        self.assertFalse(security["request_urls_included"])
        self.assertFalse(security["request_headers_included"])


if __name__ == "__main__":
    unittest.main()
