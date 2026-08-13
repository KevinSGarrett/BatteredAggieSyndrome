from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.assistive_plane.orchestration import (
    ATOMIC_EXECUTABLE,
    CAMPAIGN_OWNER,
    QUALIFICATION_RECORD,
    ReadyWorkUnit,
    RoutingDisposition,
    validate_work_unit_roles,
)


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "materialize_unified_assistive_inventory.py"
SPEC = importlib.util.spec_from_file_location("materialize_unified_assistive_inventory", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("FAILED_TO_LOAD_MATERIALIZER_MODULE")
MATERIALIZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATERIALIZER)


class UnifiedInventoryMaterializerRouteIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        readiness_path = Path(__file__).resolve().parents[1] / "configs" / "assistive_route_readiness.json"
        cls.readiness = json.loads(readiness_path.read_text(encoding="utf-8"))

    def qwen_item(self) -> dict[str, str]:
        return {
            "work_unit_id": "POST-SUBTASK-203::qwen2.5-coder-shadow-v1",
            "disposition": "LOCAL_QWEN",
            "provider": "local_qwen",
            "model": "qwen2.5-coder:7b-instruct-q4_K_M",
            "task_format": "bounded_code_review_test_generation_parser_scaffolding",
            "model_digest": "dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364",
            "prompt_version": "local-coder-shadow-v1",
            "schema_version": "1",
            "schema_sha256": "fd5ed573e9990a40674b28032a2b4fb63659c62423479c554188149826ea362c",
            "policy_version": "unified-assistive-execution-plane-v2-operational-correction",
            "execution_surface": "ollama-loopback-isolated-candidate-worktree",
            "reason": "test",
        }

    def bge_item(self) -> dict[str, str]:
        return {
            "work_unit_id": "POST-SUBTASK-203::bge-m3-embedding-shadow-v1",
            "disposition": "LOCAL_QWEN",
            "provider": "local_qwen",
            "model": "bge-m3:latest",
            "task_format": "embedding_dedup_semantic_candidate_retrieval",
            "model_digest": "7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab",
            "prompt_version": "embedding-shadow-v1",
            "schema_version": "1",
            "schema_sha256": "fd5ed573e9990a40674b28032a2b4fb63659c62423479c554188149826ea362c",
            "policy_version": "unified-assistive-execution-plane-v2-operational-correction",
            "execution_surface": "ollama-loopback",
            "reason": "test",
        }

    def test_roles_require_exact_coverage_and_separate_campaigns_from_execution(self) -> None:
        units = [
            ReadyWorkUnit(
                work_unit_id="CAMPAIGN",
                jira_unit="BAT-560",
                task_format="campaign",
                schema_sha256="a" * 64,
                authority="CODEX_FINAL_IMPLEMENTATION",
                source_hashes=("b" * 64,),
                dependencies=(),
                pre_routing_effort_points=1,
                scope="durable campaign owner",
            ),
            ReadyWorkUnit(
                work_unit_id="PACKET",
                jira_unit="BAT-560",
                task_format="candidate",
                schema_sha256="c" * 64,
                authority="CANDIDATE_ONLY",
                source_hashes=("d" * 64,),
                dependencies=(),
                pre_routing_effort_points=1,
                scope="atomic executable packet",
            ),
        ]
        report = validate_work_unit_roles(
            units,
            {"CAMPAIGN": CAMPAIGN_OWNER, "PACKET": ATOMIC_EXECUTABLE},
        )
        self.assertEqual(1, report["counts_by_role"][CAMPAIGN_OWNER])
        self.assertEqual(1, report["counts_by_role"][ATOMIC_EXECUTABLE])
        self.assertEqual(0, report["counts_by_role"][QUALIFICATION_RECORD])
        with self.assertRaisesRegex(ValueError, "MISSING_WORK_UNIT_ROLE:PACKET"):
            validate_work_unit_roles(units, {"CAMPAIGN": CAMPAIGN_OWNER})

    def test_exact_qwen_rejection_and_bge_ready_resolve_correctly(self) -> None:
        qwen_route = MATERIALIZER.route_readiness_for(self.qwen_item(), self.readiness)
        self.assertIsNotNone(qwen_route)
        self.assertEqual("NOT_READY", qwen_route["state"])
        qwen_disposition, *_ = MATERIALIZER.derive_decision(
            self.qwen_item(),
            {"workflow_state": "IN_PROGRESS"},
            {"budgets": {}},
            self.readiness,
        )
        self.assertEqual(RoutingDisposition.SUSPENDED_REJECTED_ROUTE, qwen_disposition)

        bge_route = MATERIALIZER.route_readiness_for(self.bge_item(), self.readiness)
        self.assertIsNotNone(bge_route)
        self.assertEqual("READY", bge_route["state"])
        bge_disposition, *_ = MATERIALIZER.derive_decision(
            self.bge_item(),
            {"workflow_state": "IN_PROGRESS"},
            {"budgets": {}},
            self.readiness,
        )
        self.assertEqual(RoutingDisposition.LOCAL_QWEN, bge_disposition)

    def test_changed_identity_fields_cannot_inherit_ready_or_not_ready(self) -> None:
        for field, changed in (
            ("prompt_version", "changed-prompt"),
            ("schema_version", "2"),
            ("schema_sha256", "0" * 64),
            ("model_digest", "f" * 64),
            ("policy_version", "unified-assistive-execution-plane-v999"),
            ("execution_surface", "different-surface"),
        ):
            qwen_item = self.qwen_item()
            qwen_item[field] = changed
            self.assertIsNone(MATERIALIZER.route_readiness_for(qwen_item, self.readiness), field)
            qwen_disposition, *_ = MATERIALIZER.derive_decision(
                qwen_item, {"workflow_state": "IN_PROGRESS"}, {"budgets": {}}, self.readiness
            )
            self.assertEqual(RoutingDisposition.CAPABILITY_BLOCKED, qwen_disposition, field)

            bge_item = self.bge_item()
            bge_item[field] = changed
            self.assertIsNone(MATERIALIZER.route_readiness_for(bge_item, self.readiness), field)
            bge_disposition, *_ = MATERIALIZER.derive_decision(
                bge_item, {"workflow_state": "IN_PROGRESS"}, {"budgets": {}}, self.readiness
            )
            self.assertEqual(RoutingDisposition.CAPABILITY_BLOCKED, bge_disposition, field)

    def test_incomplete_route_identity_fails_closed(self) -> None:
        item = self.bge_item()
        item.pop("execution_surface")
        with self.assertRaisesRegex(RuntimeError, "ROUTE_IDENTITY_INCOMPLETE"):
            MATERIALIZER.route_readiness_for(item, self.readiness)

    def test_ambiguous_route_identity_fails_closed(self) -> None:
        readiness = copy.deepcopy(self.readiness)
        readiness["routes"].append(copy.deepcopy(readiness["routes"][-1]))
        with self.assertRaisesRegex(RuntimeError, "ROUTE_READINESS_NOT_UNIQUE"):
            MATERIALIZER.route_readiness_for(self.bge_item(), readiness)

    @staticmethod
    def write_content_addressed(root: Path, category: str, payload: dict[str, object]) -> str:
        data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        digest = hashlib.sha256(data).hexdigest()
        path = root / category / digest[:2] / f"{digest}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return digest

    def test_semantic_local_evidence_admits_only_exact_passed_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            readiness = {"routes": [copy.deepcopy(self.readiness["routes"][-1])]}
            route = readiness["routes"][0]
            digest = self.write_content_addressed(
                root,
                "evals",
                {
                    "model": route["resolved_model"],
                    "model_digest": route["model_digest"],
                    "qualification_disposition": "PASS_CANDIDATE_RETRIEVAL_ONLY",
                    "canonical_or_protected_authority": False,
                    "metrics": {"canonical_writes": 0, "protected_decisions": 0},
                },
            )
            route["evidence_sha256"] = digest
            evidence = MATERIALIZER.local_qwen_semantic_evidence(root, readiness)
            self.assertEqual(1, evidence["ready_exact_routes"])
            self.assertEqual("READY", evidence["routes"][0]["evidence_supported_state"])

            changed = copy.deepcopy(readiness)
            changed["routes"][0]["model_digest"] = "f" * 64
            rejected = MATERIALIZER.local_qwen_semantic_evidence(root, changed)
            self.assertEqual(0, rejected["ready_exact_routes"])
            self.assertEqual("NOT_READY", rejected["routes"][0]["evidence_supported_state"])

    def test_cpu_worker_semantics_require_exact_replay_and_no_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_content_addressed(
                root,
                "readiness",
                {
                    "qualification_id": "BAT-563-private-cpu-worker-v2-corrected-architecture",
                    "readiness_disposition": "READY_FOR_LIVE_QUALIFICATION",
                    "blockers": [],
                    "passed_gates": [
                        "cleanup",
                        "coordinator_grant",
                        "live_replay",
                        "minimal_bundle_hash_match",
                        "private_https",
                        "restart_recovery",
                        "restricted_service_identity",
                        "signed_envelope",
                    ],
                    "canonical_writes": 0,
                    "protected_decisions": 0,
                    "prototype_direct_http_disabled": True,
                    "public_funnel_configured_by_project": False,
                    "peer": {
                        "dns_name": "comfy-v4-cpu-01.tail9b05ab.ts.net",
                        "windows_hostname": "comfy-v4-cpu-01",
                        "os": "windows",
                        "durable_ip_identity": False,
                        "node_id": "node",
                    },
                },
            )
            self.write_content_addressed(
                root,
                "qualifications",
                {
                    "qualification_disposition": "PASS",
                    "qualification_id": "BAT-563-private-cpu-worker-v2-corrected-architecture",
                    "qualification_run_id": "a" * 64,
                    "authority": "DETERMINISTIC_NO_CANONICAL_OR_PROTECTED_WRITES",
                    "canonical_writes": 0,
                    "protected_decisions": 0,
                    "signing_key_recorded": False,
                    "worker_identity": {
                        "node_id": "node",
                        "dns_name": "comfy-v4-cpu-01.tail9b05ab.ts.net",
                        "windows_hostname": "comfy-v4-cpu-01",
                        "os": "windows",
                        "durable_ip_identity": False,
                    },
                    "tranches": [
                        {"task": "CANONICAL_JSON", "byte_identical_replay": True},
                        {"task": "LINE_HASH_MANIFEST", "byte_identical_replay": True},
                        {"task": "EXACT_TEXT_DEDUP", "byte_identical_replay": True},
                    ],
                },
            )
            evidence = MATERIALIZER.cpu_worker_semantic_evidence(root)
            self.assertTrue(evidence["qualified"])
            self.assertEqual(3, evidence["qualifications"][0]["tranche_count"])

    def test_cursor_semantics_preserve_transitional_origin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_content_addressed(
                root,
                "dispositions",
                {
                    "job_id": "job-1",
                    "agent_id": "agent-1",
                    "candidate_only": True,
                    "canonical_authority": False,
                    "accepted_useful_results": 1,
                    "modified_results": 0,
                    "provider_usage": {"actual_usd": "0.25"},
                },
            )
            evidence = MATERIALIZER.cursor_semantic_evidence(root)
            self.assertEqual(1, evidence["accepted_useful"])
            self.assertEqual(0, evidence["controller_routed_units"])
            self.assertEqual(1, evidence["transitional_or_manual_units"])

    @staticmethod
    def openrouter_policy(
        *,
        accepted_useful: int = 12,
        units: int = 20,
        categories: int = 3,
    ) -> dict[str, object]:
        return {
            "budgets": {
                "openrouter": {
                    "hard_limit_usd": "25.00",
                    "released_stage_usd": "5.00",
                }
            },
            "execution_minimums": {
                "openrouter": {
                    "accepted_useful": accepted_useful,
                    "units": units,
                    "categories": categories,
                }
            }
        }

    @staticmethod
    def write_openrouter_summary(
        root: Path,
        *,
        accepted: int,
        modified: int,
        request_count: int,
        missing_evidence: dict[str, object] | None = None,
    ) -> None:
        route = {
            "provider": "openrouter",
            "task_format": "governed_openrouter_candidate_v1",
            "task_id": "independent_review",
            "schema_sha256": "6" * 64,
            "request_schema_version": "v1",
            "provider_policy_version": "policy-v1",
            "model": "qwen/qwen3-coder-next",
            "reasoning_effort": "none",
            "request_count": request_count,
            "complete_evidence_count": request_count,
            "accepted_useful_count": accepted + modified,
            "readiness_supported_state": "READY",
            "evidence_verified": True,
            "evidence_sha256": "7" * 64,
        }
        summary = {
            "schema_version": 1,
            "artifact_type": "OPENROUTER_DETERMINISTIC_CAMPAIGN_SUMMARY",
            "request_count": request_count,
            "counts_by_category": {
                "independent_review": 1,
                "reconciliation_ranking": 1,
                "schema_drift_review": 1,
            },
            "counts_by_disposition": {
                "accepted": accepted,
                "modified": modified,
                "review_only": 0,
                "quarantined": 1,
                "rejected": 1,
            },
            "total_cost_usd": "0.10000000",
            "provider_reconciled": True,
            "missing_evidence": missing_evidence or {},
            "routes": [route],
        }
        data = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        digest = hashlib.sha256(data).hexdigest()
        artifact = root / "evals/campaign_summaries/sha256" / digest[:2] / digest / "artifact.json"
        artifact.parent.mkdir(parents=True)
        artifact.write_bytes(data)
        pointer = {"artifact_path": str(artifact), "artifact_sha256": digest}
        current = root / "evals/campaign_summaries/current.json"
        current.parent.mkdir(parents=True, exist_ok=True)
        current.write_text(json.dumps(pointer), encoding="utf-8")
        usage = root / "usage/ledger.json"
        usage.parent.mkdir(parents=True, exist_ok=True)
        usage.write_text(
            json.dumps(
                {
                    "settled_usd": "0.10000000",
                    "provider_reconciliation": {
                        "status": "PROVIDER_TOTAL_RECONCILED",
                        "provider_total_usd": "0.10000000",
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_openrouter_semantics_keep_pilot_nonoperational_but_exact_route_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_openrouter_summary(
                root,
                accepted=5,
                modified=2,
                request_count=20,
                missing_evidence={"old-request": ["review"]},
            )
            evidence = MATERIALIZER.openrouter_semantic_evidence(
                root, self.openrouter_policy()
            )
            self.assertEqual("PAID_PILOT_IN_PROGRESS_NOT_OPERATIONAL", evidence["state"])
            self.assertFalse(evidence["operationally_admitted"])
            self.assertEqual("READY", evidence["routes"][0]["readiness_supported_state"])
            self.assertIn("OPENROUTER_ACCEPTED_USEFUL_BELOW_POLICY_THRESHOLD", evidence["findings"])
            self.assertIn("OPENROUTER_PARTIAL_HISTORICAL_REVIEW_EVIDENCE", evidence["findings"])

    def test_openrouter_semantics_require_reconciled_budget_and_exact_summary_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_openrouter_summary(root, accepted=10, modified=2, request_count=20)
            admitted = MATERIALIZER.openrouter_semantic_evidence(root, self.openrouter_policy())
            self.assertEqual("OPERATIONALLY_ADMITTED", admitted["state"])
            self.assertTrue(admitted["operationally_admitted"])

            ledger = json.loads((root / "usage/ledger.json").read_text(encoding="utf-8"))
            ledger["settled_usd"] = "0.20000000"
            (root / "usage/ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
            rejected = MATERIALIZER.openrouter_semantic_evidence(root, self.openrouter_policy())
            self.assertFalse(rejected["operationally_admitted"])
            self.assertEqual("NOT_READY", rejected["routes"][0]["readiness_supported_state"])
            self.assertIn("OPENROUTER_PROVIDER_USAGE_NOT_RECONCILED", rejected["findings"])


if __name__ == "__main__":
    unittest.main()
