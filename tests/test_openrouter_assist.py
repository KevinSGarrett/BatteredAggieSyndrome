from __future__ import annotations

import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.backend import FakeBackend, TransientBackendError
from aggie_analytics.assistive_plane.contracts import AssistiveRequest, Authority, Disposition, sha256_value
from aggie_analytics.assistive_plane.dispatcher import AssistiveDispatcher
from aggie_analytics.assistive_plane.openrouter_backend import load_openrouter_key
from aggie_analytics.assistive_plane.openrouter_backend import OpenRouterBackend, response_output_text
from aggie_analytics.assistive_plane.redaction import contains_secret, redact
from aggie_analytics.assistive_plane.worker import validate_patch_paths


class OpenRouterAssistTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        policy = json.loads((ROOT / "configs/openrouter_assist_policy.json").read_text(encoding="utf-8"))
        policy["storage"]["root"] = str(root / "external")
        policy["budget"]["paid_hard_limit_usd"] = "0.00"
        policy["budget"]["released_stage_usd"] = "0.00"
        self.policy_path = root / "policy.json"
        self.policy_path.write_text(json.dumps(policy), encoding="utf-8")
        policy["budget"]["paid_hard_limit_usd"] = "1.00"
        policy["budget"]["released_stage_usd"] = "0.25"
        policy["budget"]["paid_calls_authorized"] = True
        self.simulated_policy_path = root / "simulated-policy.json"
        self.simulated_policy_path.write_text(json.dumps(policy), encoding="utf-8")
        self.schema = json.loads((ROOT / "schemas/assistive/independent_review.schema.json").read_text(encoding="utf-8"))
        self.output = {"verdict": "REVIEW", "findings": [], "evidence": [], "unsupported_claims": [], "recommended_checks": []}
        self.request = AssistiveRequest(
            task_id="independent_review",
            jira_unit="POST-SUBTASK-199",
            base_commit="a" * 40,
            authority=Authority.INDEPENDENT_REVIEW,
            prompt_version="v1",
            schema_version="v1",
            schema_sha256=sha256_value(self.schema),
            source_hashes=("b" * 64,),
            evidence_excerpts=("bounded evidence",),
            model="qwen/qwen3-coder-next",
            reasoning_effort="none",
            max_output_tokens=256,
            provider_policy_version="v1",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_zero_budget_rejects_before_backend(self) -> None:
        backend = FakeBackend(self.output)
        result = AssistiveDispatcher(ROOT, backend, self.policy_path).dispatch(self.request, self.schema)
        self.assertEqual(result.disposition, Disposition.REJECTED)
        self.assertEqual(result.reason, "PROVIDER_RELEASED_STAGE_EXCEEDED")
        self.assertEqual(backend.calls, 0)

    def test_secret_rejected_before_backend(self) -> None:
        backend = FakeBackend(self.output)
        request = replace(self.request, evidence_excerpts=("OPENROUTER_API_KEY=secret",))
        result = AssistiveDispatcher(ROOT, backend, self.policy_path).dispatch(request, self.schema)
        self.assertEqual(result.reason, "SECRET_DETECTED")
        self.assertEqual(backend.calls, 0)

    def test_request_identity_is_deterministic_and_evidence_bound(self) -> None:
        self.assertEqual(self.request.identity(), self.request.identity())
        self.assertNotEqual(self.request.identity(), replace(self.request, evidence_excerpts=("different",)).identity())

    def test_schema_identity_and_task_authority_fail_closed(self) -> None:
        backend = FakeBackend(self.output)
        dispatcher = AssistiveDispatcher(ROOT, backend, self.simulated_policy_path)
        self.assertEqual(
            dispatcher.dispatch(replace(self.request, schema_sha256="0" * 64), self.schema).reason,
            "SCHEMA_IDENTITY_MISMATCH",
        )
        self.assertEqual(
            dispatcher.dispatch(replace(self.request, authority=Authority.PATCH_CANDIDATE), self.schema).reason,
            "TASK_AUTHORITY_MISMATCH",
        )
        self.assertEqual(backend.calls, 0)

    def test_redaction(self) -> None:
        self.assertTrue(contains_secret("Authorization: Bearer abc"))
        self.assertNotIn("abc", redact("Authorization: Bearer abc"))

    def test_patch_scope_validation(self) -> None:
        validate_patch_paths(["src/aggie_analytics/example.py"], ["src/aggie_analytics"])
        for unsafe in ["../.env", ".git/config", "C:/BatteredAggieSyndrome/.env", "README.md"]:
            with self.assertRaises(ValueError):
                validate_patch_paths([unsafe], ["src/aggie_analytics"])

    def test_credential_loader_boolean_contract(self) -> None:
        env = Path(self.temporary.name) / ".env"
        env.write_text("OPENROUTER_API_KEY=example\n", encoding="utf-8")
        self.assertTrue(bool(load_openrouter_key(env)))
        env.write_text("OPENROUTER_API_KEY=one\nOPENROUTER_API_KEY=two\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            load_openrouter_key(env)

    def test_none_reasoning_is_not_sent_as_unsupported_parameter(self) -> None:
        backend = OpenRouterBackend(Path(self.temporary.name) / ".env")
        payload = backend._payload(self.request, self.schema)
        self.assertNotIn("reasoning", payload)
        self.assertTrue(payload["provider"]["require_parameters"])
        self.assertTrue(payload["provider"]["zdr"])

    def test_responses_wire_output_is_extracted(self) -> None:
        self.assertEqual(
            '{"verdict":"REVIEW"}',
            response_output_text({"output": [{"type": "message", "content": [{"type": "output_text", "text": '{"verdict":"REVIEW"}'}]}]}),
        )

    def test_paid_invalid_output_is_quarantined_and_settled(self) -> None:
        backend = FakeBackend({"unexpected": True})
        dispatcher = AssistiveDispatcher(ROOT, backend, self.simulated_policy_path)
        result = dispatcher.dispatch(self.request, self.schema)
        self.assertEqual(Disposition.QUARANTINE, result.disposition)
        self.assertIn("STRICT_OUTPUT_INVALID", result.reason)
        self.assertEqual(Decimal("0.000001"), dispatcher.ledger.state().settled_usd)
        self.assertEqual(Decimal("0"), dispatcher.ledger.state().reserved_usd)

    def test_fake_end_to_end_settlement_and_cache(self) -> None:
        backend = FakeBackend(self.output)
        dispatcher = AssistiveDispatcher(ROOT, backend, self.simulated_policy_path)
        first = dispatcher.dispatch(self.request, self.schema)
        second = dispatcher.dispatch(self.request, self.schema)
        self.assertEqual(first.disposition, Disposition.CANDIDATE)
        self.assertEqual(second.reason, "CACHE_HIT")
        self.assertEqual(backend.calls, 1)
        self.assertEqual(dispatcher.ledger.state().settled_usd, Decimal("0.000001"))
        self.assertEqual(dispatcher.ledger.state().reserved_usd, Decimal("0"))

    def test_released_stage_is_lower_admission_ceiling(self) -> None:
        dispatcher = AssistiveDispatcher(ROOT, FakeBackend(self.output), self.simulated_policy_path)
        dispatcher.ledger.reserve("existing", Decimal("0.249999"))
        result = dispatcher.dispatch(self.request, self.schema)
        self.assertEqual(result.disposition, Disposition.REJECTED)
        self.assertEqual(result.reason, "PROVIDER_RELEASED_STAGE_EXCEEDED")

    def test_provider_total_reconciliation_closes_orphans_conservatively(self) -> None:
        dispatcher = AssistiveDispatcher(ROOT, FakeBackend(self.output), self.simulated_policy_path)
        dispatcher.ledger.reserve("orphan", Decimal("0.01"))
        dispatcher.ledger.reconcile_provider_total(Decimal("0.02"), evidence_sha256="a" * 64)
        state = dispatcher.ledger.state()
        self.assertEqual(Decimal("0.02"), state.settled_usd)
        self.assertEqual(Decimal("0"), state.reserved_usd)

    def test_lagging_provider_total_cannot_reduce_local_settlement(self) -> None:
        dispatcher = AssistiveDispatcher(ROOT, FakeBackend(self.output), self.simulated_policy_path)
        dispatcher.ledger.reconcile_provider_total(Decimal("0.02"), evidence_sha256="a" * 64)
        dispatcher.ledger.reconcile_provider_total(Decimal("0.01"), evidence_sha256="b" * 64)
        self.assertEqual(Decimal("0.02"), dispatcher.ledger.state().settled_usd)

    def test_concurrent_reservations_are_not_lost(self) -> None:
        dispatcher = AssistiveDispatcher(ROOT, FakeBackend(self.output), self.simulated_policy_path)

        def reserve(index: int) -> None:
            dispatcher.ledger.reserve(f"concurrent-{index}", Decimal("0.01"))

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(reserve, range(20)))
        state = dispatcher.ledger.state()
        self.assertEqual(Decimal("0.20"), state.reserved_usd)
        self.assertEqual(1, dispatcher.ledger.lock_path.stat().st_size)

    def test_transient_retry_is_bounded(self) -> None:
        class FlakyBackend(FakeBackend):
            def submit(self, request, schema):
                self.calls += 1
                if self.calls < 3:
                    raise TransientBackendError("retry")
                self.calls -= 1
                return super().submit(request, schema)

        backend = FlakyBackend(self.output)
        result = AssistiveDispatcher(ROOT, backend, self.simulated_policy_path).dispatch(self.request, self.schema)
        self.assertEqual(result.disposition, Disposition.CANDIDATE)
        self.assertEqual(backend.calls, 3)


if __name__ == "__main__":
    unittest.main()
