from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import importlib.util  # noqa: E402

_MODULE_PATH = ROOT / "src" / "aggie_analytics" / "validation" / "artifact_binding.py"
_SPEC = importlib.util.spec_from_file_location("artifact_binding_under_test", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"unable to load {_MODULE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
ArtifactBindingError = _MODULE.ArtifactBindingError
canonical_json = _MODULE.canonical_json
compute_identity = _MODULE.compute_identity
validate_artifact_bindings = _MODULE.validate_artifact_bindings

CANONICAL = Path("artifacts") / "pit" / "PIT_REPLAY_READINESS.json"
EVIDENCE_401 = Path("artifacts") / "jira_evidence" / "POST-SUBTASK-051.json"
EVIDENCE_569 = Path("artifacts") / "jira_evidence" / "POST-TASK-DEVELOPMENT-CANDIDATE-EVIDENCE-LEDGER-001.json"
EVIDENCE_566 = Path("artifacts") / "jira_evidence" / "POST-TASK-2023-LABELED-DEVELOPMENT-REPLAY-001.json"
CONTRACT = Path("configs") / "artifact_binding_contract.json"
CURRENT = "c7e71afce0eeef24959b7a32387ea99ffe5a559f718cd621342d9ccd7dc844cc"
STALE_NARRATIVE = "4d6c58e4dd31182f8fe2f53e3b53fae72c9df66178465112aae3693814a8395c"
STALE_REBOUND = "3af86852302fcd3f1d2946c78edc77ba38466ad5ed332ac17621b942a2aac8e3"
CYCLE17_BINDING_ID = "BAT-632-OFFICIAL-1999-STRUCTURED-DOMAINS"
CYCLE17_GATE = Path("artifacts") / "data_lake" / "tamu_official_1999_structured_domains_gate.json"
CYCLE17_EVIDENCE = Path("artifacts") / "jira_evidence" / "POST-TASK-SRC014-1999-STRUCTURED-DOMAINS-001.json"
CYCLE17_STALE_GATE = "a19c81e28ece6e7380e313c4fe8a5d8640689a917fd96590777d0749f32e3dd5"
CYCLE17_P5_BINDING_ID = "BAT-633-OFFICIAL-1999-EXPANDED-UNION"
CYCLE17_P5_GATE = Path("artifacts") / "data_lake" / "tamu_official_gamebook_union_1999_expanded_gate.json"
CYCLE17_P5_EVIDENCE = Path("artifacts") / "jira_evidence" / "POST-TASK-SRC014-1999-EXPANDED-ENRICHED-UNION-001.json"
CYCLE17_P5_STALE_GATE = "7a0542b74658ec0bb9687587cfdad308d85254bbb6cde29b651f0e2f5b16155c"
CYCLE17_P6_BINDING_ID = "BAT-634-OFFICIAL-1998-SEASON-INDEX"
CYCLE17_P6_GATE = Path("artifacts") / "data_lake" / "tamu_official_1998_season_index_gate.json"
CYCLE17_P6_EVIDENCE = Path("artifacts") / "jira_evidence" / "POST-TASK-SRC014-1998-OFFICIAL-INDEX-001.json"
CYCLE17_P6_STALE_GATE = "78ecc3b2793192cf1f850d5e8330c4333230fc65141683e746462444e42cb142"


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, (dict, list)):
        path.write_bytes(canonical_json(payload) + b"\n")
    else:
        path.write_text(str(payload), encoding="utf-8")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ArtifactBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="artifact-binding-"))
        for relative in (CANONICAL, EVIDENCE_401, EVIDENCE_569, EVIDENCE_566, CONTRACT):
            destination = self.temp / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)

    def _prepare_cycle17_binding_fixture(self) -> None:
        contract = _load(ROOT / CONTRACT)
        binding = next(
            item for item in contract["bindings"] if item["binding_id"] == CYCLE17_BINDING_ID
        )
        _write(
            self.temp / CONTRACT,
            {"schema_version": contract["schema_version"], "bindings": [binding]},
        )
        for relative in (CYCLE17_GATE, CYCLE17_EVIDENCE):
            destination = self.temp / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

    def _prepare_cycle17_p5_binding_fixture(self) -> None:
        contract = _load(ROOT / CONTRACT)
        binding = next(
            item for item in contract["bindings"] if item["binding_id"] == CYCLE17_P5_BINDING_ID
        )
        _write(
            self.temp / CONTRACT,
            {"schema_version": contract["schema_version"], "bindings": [binding]},
        )
        for relative in (CYCLE17_P5_GATE, CYCLE17_P5_EVIDENCE):
            destination = self.temp / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

    def _prepare_cycle17_p6_binding_fixture(self) -> None:
        contract = _load(ROOT / CONTRACT)
        binding = next(
            item for item in contract["bindings"] if item["binding_id"] == CYCLE17_P6_BINDING_ID
        )
        _write(
            self.temp / CONTRACT,
            {"schema_version": contract["schema_version"], "bindings": [binding]},
        )
        for relative in (CYCLE17_P6_GATE, CYCLE17_P6_EVIDENCE):
            destination = self.temp / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

    def test_current_identity_matches_everywhere(self) -> None:
        report = validate_artifact_bindings(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["bindings"][0]["identity"], CURRENT)

    def test_stale_narrative_identity_is_rejected(self) -> None:
        evidence = _load(self.temp / EVIDENCE_401)
        evidence["observable_outcome"] = (
            f"Cycle #8 rebound to {STALE_NARRATIVE} and remains RETAIN_PROTECTED_LANE_BLOCKED."
        )
        _write(self.temp / EVIDENCE_401, evidence)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn(str(EVIDENCE_401).replace("\\", "/"), str(raised.exception).replace("\\", "/"))
        self.assertIn("observable_outcome", str(raised.exception))
        self.assertIn("stale narrative identity", str(raised.exception))

    def test_stale_evidence_item_identity_is_rejected(self) -> None:
        evidence = _load(self.temp / EVIDENCE_401)
        evidence["outputs"][0]["artifact_identity"] = STALE_NARRATIVE
        _write(self.temp / EVIDENCE_401, evidence)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("outputs[0].artifact_identity", str(raised.exception))
        self.assertIn("stale current identity", str(raised.exception))

    def test_stale_nested_rebound_identity_is_rejected(self) -> None:
        evidence = _load(self.temp / EVIDENCE_569)
        evidence["bat401_rebound"]["artifact_identity"] = STALE_REBOUND
        _write(self.temp / EVIDENCE_569, evidence)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("bat401_rebound.artifact_identity", str(raised.exception))
        self.assertIn(STALE_REBOUND, str(raised.exception))

    def test_current_identity_listed_as_superseded_is_rejected(self) -> None:
        evidence = _load(self.temp / EVIDENCE_401)
        evidence["prior_superseded_identities"].append(CURRENT)
        _write(self.temp / EVIDENCE_401, evidence)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("incorrectly listed as superseded", str(raised.exception))
        self.assertTrue(
            "prior_superseded_identities" in str(raised.exception)
            or "outputs[0].artifact_identity" in str(raised.exception)
        )

    def test_superseded_identity_presented_as_current_is_rejected(self) -> None:
        evidence = _load(self.temp / EVIDENCE_569)
        evidence["outputs"][6]["artifact_identity"] = STALE_NARRATIVE
        _write(self.temp / EVIDENCE_569, evidence)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("stale current identity", str(raised.exception))
        self.assertIn(STALE_NARRATIVE, str(raised.exception))

    def test_missing_canonical_artifact_is_rejected(self) -> None:
        (self.temp / CANONICAL).unlink()
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("missing canonical artifact", str(raised.exception))
        self.assertIn(str(CANONICAL).replace("\\", "/"), str(raised.exception).replace("\\", "/"))

    def test_altered_canonical_artifact_is_rejected(self) -> None:
        payload = _load(self.temp / CANONICAL)
        payload["honesty_boundary"]["note"] = "tampered"
        payload["artifact_identity"] = compute_identity(payload, "artifact_identity")
        _write(self.temp / CANONICAL, payload)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("stale current identity", str(raised.exception))

    def test_forged_evidence_with_recomputed_outer_identity_is_rejected(self) -> None:
        evidence = _load(self.temp / EVIDENCE_401)
        evidence["outputs"][0]["artifact_identity"] = STALE_NARRATIVE
        evidence["evidence_identity"] = "pending"
        evidence["evidence_identity"] = compute_identity(evidence, "evidence_identity")
        _write(self.temp / EVIDENCE_401, evidence)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("stale current identity", str(raised.exception))
        self.assertNotIn("evidence_identity", str(raised.exception))

    def test_lane_decision_changed_to_open_is_rejected(self) -> None:
        payload = _load(self.temp / CANONICAL)
        payload["lane_decision"] = "OPEN_PROTECTED_LANE"
        payload["artifact_identity"] = compute_identity(payload, "artifact_identity")
        _write(self.temp / CANONICAL, payload)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("OPEN_PROTECTED_LANE", str(raised.exception))
        self.assertTrue(
            "lane decision" in str(raised.exception) or "required field lane_decision" in str(raised.exception)
        )

    def test_protected_or_production_claim_is_rejected(self) -> None:
        payload = _load(self.temp / CANONICAL)
        payload["claims"]["production_readiness"] = True
        payload["artifact_identity"] = compute_identity(payload, "artifact_identity")
        _write(self.temp / CANONICAL, payload)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("claims.production_readiness", str(raised.exception))
        self.assertIn("forbidden production or protected authority claim", str(raised.exception))

    def test_issue_local_id_mismatch_is_rejected(self) -> None:
        evidence = _load(self.temp / EVIDENCE_401)
        evidence["jira_key"] = "BAT-000"
        _write(self.temp / EVIDENCE_401, evidence)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("jira_key mismatch", str(raised.exception))

    def test_cycle17_stale_structured_domain_evidence_is_rejected(self) -> None:
        self._prepare_cycle17_binding_fixture()
        evidence = _load(self.temp / CYCLE17_EVIDENCE)
        evidence["current_identities"]["gate_identity"] = CYCLE17_STALE_GATE
        _write(self.temp / CYCLE17_EVIDENCE, evidence)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("current_identities.gate_identity", str(raised.exception))
        self.assertIn("stale current identity", str(raised.exception))

    def test_cycle17_stale_expanded_union_evidence_is_rejected(self) -> None:
        self._prepare_cycle17_p5_binding_fixture()
        evidence = _load(self.temp / CYCLE17_P5_EVIDENCE)
        evidence["current_identities"]["gate_identity"] = CYCLE17_P5_STALE_GATE
        _write(self.temp / CYCLE17_P5_EVIDENCE, evidence)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("current_identities.gate_identity", str(raised.exception))
        self.assertIn("stale current identity", str(raised.exception))

    def test_cycle17_stale_1998_index_evidence_is_rejected(self) -> None:
        self._prepare_cycle17_p6_binding_fixture()
        evidence = _load(self.temp / CYCLE17_P6_EVIDENCE)
        evidence["current_identities"]["gate_identity"] = CYCLE17_P6_STALE_GATE
        _write(self.temp / CYCLE17_P6_EVIDENCE, evidence)
        with self.assertRaises(ArtifactBindingError) as raised:
            validate_artifact_bindings(self.temp)
        self.assertIn("current_identities.gate_identity", str(raised.exception))
        self.assertIn("stale current identity", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
