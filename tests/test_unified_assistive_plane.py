from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.bypass import find_direct_endpoint_bypasses
from aggie_analytics.assistive_plane.cpu_worker_backend import CpuWorkerIdentity
from aggie_analytics.assistive_plane.cursor_backend import CursorBackend, CursorRunPolicy
from aggie_analytics.assistive_plane.ollama_backend import OllamaRoutePolicy
from aggie_analytics.assistive_plane.orchestration import (
    ProviderBudget,
    ReadinessRegistry,
    ReadinessState,
    ReadyWorkInventory,
    ReadyWorkUnit,
    RouteDecision,
    RouteKey,
    RouteReadiness,
    RoutingDisposition,
    write_content_addressed_json,
)


class UnifiedAssistivePlaneTests(unittest.TestCase):
    def unit(self) -> ReadyWorkUnit:
        return ReadyWorkUnit(
            work_unit_id="work-1",
            jira_unit="POST-SUBTASK-201",
            task_format="strict_json_review",
            schema_sha256="a" * 64,
            authority="REVIEW",
            source_hashes=("b" * 64,),
            dependencies=(),
            pre_routing_effort_points=3,
            scope="review one bounded evidence packet",
        )

    def decision(self, unit: ReadyWorkUnit) -> RouteDecision:
        return RouteDecision(
            work_unit_id=unit.work_unit_id,
            work_unit_identity=unit.identity(),
            disposition=RoutingDisposition.CODEX_DETERMINISTIC,
            provider="codex_deterministic",
            model=None,
            reason="deterministic parser sufficient",
            decided_at="2026-08-12T00:00:00Z",
        )

    def test_inventory_requires_exactly_one_disposition(self) -> None:
        unit = self.unit()
        report = ReadyWorkInventory([unit], [self.decision(unit)]).validate()
        self.assertEqual(report["coverage_fraction"], 1.0)
        self.assertEqual(report["effort_points_total"], 3)
        with self.assertRaisesRegex(ValueError, "MISSING_ROUTE_DISPOSITION"):
            ReadyWorkInventory([unit], []).validate()
        with self.assertRaisesRegex(ValueError, "MULTIPLE_ROUTE_DISPOSITIONS"):
            ReadyWorkInventory([unit], [self.decision(unit), self.decision(unit)]).validate()

    def test_effort_and_pre_routing_identity_are_immutable(self) -> None:
        unit = self.unit()
        changed = replace(unit, pre_routing_effort_points=5)
        with self.assertRaisesRegex(ValueError, "PRE_ROUTING_IDENTITY_CHANGED"):
            ReadyWorkInventory([changed], [self.decision(unit)]).validate()
        with self.assertRaisesRegex(ValueError, "INVALID_PRE_ROUTING_EFFORT"):
            replace(unit, pre_routing_effort_points=4)

    def test_readiness_is_exact_route_key(self) -> None:
        key = RouteKey("cursor", "gpt-5.3-codex", "patch", "c" * 64, "v1")
        registry = ReadinessRegistry([RouteReadiness(key, ReadinessState.READY, "d" * 64, "qualified")])
        self.assertEqual(registry.require(key).state, ReadinessState.READY)
        with self.assertRaisesRegex(ValueError, "ROUTE_READINESS_NOT_ESTABLISHED"):
            registry.require(replace(key, task_format="review"))

    def test_cursor_policy_fails_closed(self) -> None:
        backend = CursorBackend(CursorRunPolicy(reasoning="medium"))
        payload = backend.build_create_payload(prompt="bounded", repository_url="https://github.com/example/project", starting_ref="abc")
        self.assertEqual(payload["model"]["id"], "gpt-5.3-codex")
        self.assertFalse(payload["workOnCurrentBranch"])
        self.assertFalse(payload["autoCreatePR"])
        for policy in [
            CursorRunPolicy(model="auto"),
            CursorRunPolicy(reasoning="high"),
            CursorRunPolicy(fast=True),
            CursorRunPolicy(work_on_current_branch=True),
            CursorRunPolicy(auto_create_pr=True),
        ]:
            with self.assertRaises(ValueError):
                policy.validate()

    def test_ollama_policy_is_loopback_and_resource_bounded(self) -> None:
        route = OllamaRoutePolicy("http://127.0.0.1:11434", "qwen2.5:7b-instruct", "845dbda0ea48")
        payload = route.build_chat_payload(messages=[{"role": "user", "content": "bounded"}], schema={"type": "object"})
        self.assertEqual(payload["options"]["num_ctx"], 4096)
        self.assertEqual(payload["keep_alive"], "0")
        with self.assertRaisesRegex(ValueError, "OLLAMA_NON_LOOPBACK_ENDPOINT"):
            replace(route, endpoint="http://0.0.0.0:11434").validate()
        with self.assertRaisesRegex(ValueError, "OLLAMA_CONCURRENCY_POLICY_VIOLATION"):
            replace(route, parallel_requests=2).validate()

    def test_cpu_worker_identity_is_exact(self) -> None:
        CpuWorkerIdentity("comfy-v4-cpu-01.tail9b05ab.ts.net.", "windows", True).validate()
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_IDENTITY_MISMATCH"):
            CpuWorkerIdentity("comfy-v3-coordinator-01.tail9b05ab.ts.net", "linux", True).validate()

    def test_budgets_are_independent_and_positive_authority_is_required(self) -> None:
        self.assertFalse(ProviderBudget("cursor", "USD", "0.00", "0.00", "0.00", None).admits_paid_work())
        self.assertFalse(ProviderBudget("cursor", "USD", "10.00", "10.00", "0.00", None).admits_paid_work())
        self.assertTrue(ProviderBudget("openai", "USD", "100.00", "30.00", "2.75", "user-authority").admits_paid_work())

    def test_content_addressed_write_replays(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = write_content_addressed_json(Path(temporary), "manifests", {"value": 1})
            second = write_content_addressed_json(Path(temporary), "manifests", {"value": 1})
            self.assertEqual(first, second)
            self.assertEqual(first[0].read_bytes(), b'{"value":1}\n')

    def test_no_direct_endpoint_bypass_in_source_tree(self) -> None:
        self.assertEqual(find_direct_endpoint_bypasses(ROOT), [])


if __name__ == "__main__":
    unittest.main()
