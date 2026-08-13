from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from email.message import Message
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.bypass import find_direct_endpoint_bypasses
from aggie_analytics.assistive_plane.cpu_worker_backend import CpuWorkerIdentity
from aggie_analytics.assistive_plane.cursor_backend import (
    CursorApiError,
    CursorBackend,
    CursorCloudClient,
    CursorRunPolicy,
    cursor_agent_identity,
    load_cursor_key,
)
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
from tools.cursor_assist import inspect as inspect_cursor


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
        key = RouteKey(
            "cursor",
            "gpt-5.3-codex",
            "catalog-model-id",
            "patch",
            "cursor-safety-v1",
            "1",
            "c" * 64,
            "v2",
            "cursor-cloud-agent",
        )
        registry = ReadinessRegistry([RouteReadiness(key, ReadinessState.READY, "d" * 64, "qualified")])
        self.assertEqual(registry.require(key).state, ReadinessState.READY)
        with self.assertRaisesRegex(ValueError, "ROUTE_READINESS_NOT_ESTABLISHED"):
            registry.require(replace(key, task_format="review"))

    def test_empirical_rejection_is_exact_and_cannot_be_inherited(self) -> None:
        payload = __import__("json").loads(
            (ROOT / "configs/assistive_route_readiness.json").read_text(encoding="utf-8")
        )
        entries = []
        for item in payload["routes"]:
            if item["model_digest"].startswith("UNRESOLVED_"):
                continue
            key_fields = {
                name: item[name]
                for name in (
                    "provider", "resolved_model", "model_digest", "task_format",
                    "prompt_version", "schema_version", "schema_sha256",
                    "policy_version", "execution_surface",
                )
            }
            entries.append(
                RouteReadiness(
                    RouteKey(**key_fields),
                    ReadinessState(item["state"]),
                    item["evidence_sha256"],
                    item["reason"],
                )
            )
        registry = ReadinessRegistry(entries)
        rejected = entries[0].key
        with self.assertRaisesRegex(ValueError, "ROUTE_NOT_READY:NOT_READY"):
            registry.require(rejected)
        for changed in (
            replace(rejected, resolved_model="another-model"),
            replace(rejected, task_format="bounded-code-review"),
            replace(rejected, prompt_version="new-prompt"),
            replace(rejected, schema_version="2"),
            replace(rejected, model_digest="f" * 64),
        ):
            with self.assertRaisesRegex(ValueError, "ROUTE_READINESS_NOT_ESTABLISHED"):
                registry.require(changed)
        self.assertFalse(payload["human_status_override_allowed"])

    def test_cursor_policy_fails_closed(self) -> None:
        backend = CursorBackend(CursorRunPolicy(reasoning="medium"))
        payload = backend.build_create_payload(prompt="bounded", repository_url="https://github.com/example/project", starting_ref="abc")
        self.assertEqual(payload["model"]["id"], "gpt-5.3-codex")
        self.assertFalse(payload["workOnCurrentBranch"])
        self.assertFalse(payload["autoCreatePR"])

    def test_cursor_payload_can_bind_idempotent_agent_identity(self) -> None:
        payload = CursorBackend(CursorRunPolicy(reasoning="low")).build_create_payload(
            prompt="bounded",
            repository_url="https://github.com/example/project",
            starting_ref="a" * 40,
            agent_id="bc-00000000-0000-0000-0000-000000000001",
        )
        self.assertEqual("bc-00000000-0000-0000-0000-000000000001", payload["agentId"])
        self.assertEqual("a" * 40, payload["repos"][0]["startingRef"])

    def test_cursor_agent_identity_is_deterministic_uuid_v5(self) -> None:
        first = cursor_agent_identity("a" * 64)
        self.assertEqual(first, cursor_agent_identity("a" * 64))
        self.assertNotEqual(first, cursor_agent_identity("b" * 64))
        self.assertRegex(first, r"^bc-[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
        with self.assertRaisesRegex(ValueError, "CURSOR_JOB_IDENTITY_INVALID"):
            cursor_agent_identity("not-a-hash")

    def test_cursor_followup_inherits_safety_policy(self) -> None:
        payload = CursorBackend(CursorRunPolicy(reasoning="low")).build_followup_payload(prompt="commit existing changes")
        self.assertEqual({"prompt": {"text": "commit existing changes"}, "mode": "agent"}, payload)
        self.assertNotIn("model", payload)
        self.assertNotIn("autoCreatePR", payload)
        with self.assertRaisesRegex(ValueError, "CURSOR_FOLLOWUP_PROMPT_REQUIRED"):
            CursorBackend(CursorRunPolicy(reasoning="low")).build_followup_payload(prompt=" ")

    def test_cursor_inspection_requires_bound_agent_job_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "CURSOR_AGENT_JOB_IDENTITY_MISMATCH"):
            inspect_cursor("bc-00000000-0000-5000-8000-000000000000", "a" * 64)

    def test_cursor_client_preserves_only_structured_safe_error_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            env = Path(raw) / ".env"
            env.write_text("CURSOR_API_TOKEN=example\n", encoding="utf-8")
            headers = Message()
            headers["X-Request-ID"] = "request-123"
            body = BytesIO(
                b'{"error":{"code":"validation_error","message":"model selection is invalid",'
                b'"helpUrl":"https://cursor.com/docs","provider":"cursor"},"ignored":"secret"}'
            )
            failure = HTTPError("https://api.cursor.com/v1/agents", 400, "bad request", headers, body)
            with patch("urllib.request.urlopen", side_effect=failure):
                with self.assertRaises(CursorApiError) as caught:
                    CursorCloudClient(env).request("POST", "/agents", {"prompt": {"text": "bounded"}})
        self.assertEqual(400, caught.exception.status)
        self.assertEqual("validation_error", caught.exception.code)
        self.assertEqual("model selection is invalid", caught.exception.message)
        self.assertEqual("request-123", caught.exception.request_id)
        self.assertNotIn("secret", str(caught.exception))

    def test_cursor_credential_loader_requires_one_nonempty_value(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            env = Path(raw) / ".env"
            env.write_text("CURSOR_API_TOKEN=example\n", encoding="utf-8")
            self.assertTrue(load_cursor_key(env))
            env.write_text("CURSOR_API_TOKEN=one\nCURSOR_API_TOKEN=two\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                load_cursor_key(env)
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
        CpuWorkerIdentity(
            "comfy-v4-cpu-01.tail9b05ab.ts.net.",
            "windows",
            True,
            node_id="nUxabVWSHb11CNTRL",
        ).validate()
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
