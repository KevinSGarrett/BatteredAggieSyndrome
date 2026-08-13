from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from aggie_analytics.assistive_plane.orchestration import RoutingDisposition


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

            bge_item = self.bge_item()
            bge_item[field] = changed
            self.assertIsNone(MATERIALIZER.route_readiness_for(bge_item, self.readiness), field)

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


if __name__ == "__main__":
    unittest.main()
