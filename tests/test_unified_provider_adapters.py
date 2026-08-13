from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.assistive_plane.provider_adapters import (
    BGE_MODEL_DIGEST,
    BGE_POLICY_VERSION,
    BGE_PROMPT_VERSION,
    BGE_SCHEMA_SHA256,
    BGE_SCHEMA_VERSION,
    BGE_TASK_FORMAT,
    BgeM3CandidateAdapter,
    GovernedOpenRouterAdapter,
    OPENROUTER_TASK_FORMAT,
)
from aggie_analytics.assistive_plane.backend import FakeBackend
from aggie_analytics.assistive_plane.contracts import sha256_value


class UnifiedProviderAdapterTests(unittest.TestCase):
    def packet(self) -> dict[str, object]:
        return {
            "task_format": BGE_TASK_FORMAT,
            "model": "bge-m3:latest",
            "model_digest": BGE_MODEL_DIGEST,
            "policy_version": BGE_POLICY_VERSION,
            "prompt_version": BGE_PROMPT_VERSION,
            "route_schema_version": BGE_SCHEMA_VERSION,
            "schema_sha256": BGE_SCHEMA_SHA256,
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            "query": "Texas A&M",
            "candidates": [
                {"candidate_id": "aggies", "text": "Texas A&M Aggies football"},
                {"candidate_id": "other", "text": "unrelated weather station"},
            ],
        }

    def test_exact_qualified_bge_route_returns_candidate_rankings(self) -> None:
        def transport(path: str, _body: dict[str, object] | None) -> dict[str, object]:
            if path == "/api/tags":
                return {"models": [{"name": "bge-m3:latest", "digest": BGE_MODEL_DIGEST}]}
            return {"embeddings": [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]]}

        result = BgeM3CandidateAdapter(transport=transport).run(self.packet())
        self.assertEqual("aggies", result.result["rankings"][0]["candidate_id"])
        self.assertEqual("REVIEW_ONLY", result.disposition)
        self.assertEqual(0, result.result["canonical_writes"])
        self.assertEqual(0, result.result["protected_decisions"])

    def test_model_digest_change_fails_closed_before_embedding(self) -> None:
        calls = 0

        def transport(_path: str, _body: dict[str, object] | None) -> dict[str, object]:
            nonlocal calls
            calls += 1
            return {}

        packet = self.packet()
        packet["model_digest"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "BGE_EXACT_ROUTE_IDENTITY_MISMATCH:model_digest"):
            BgeM3CandidateAdapter(transport=transport).run(packet)
        self.assertEqual(0, calls)

    def test_live_digest_mismatch_fails_closed(self) -> None:
        def transport(path: str, _body: dict[str, object] | None) -> dict[str, object]:
            if path == "/api/tags":
                return {"models": [{"name": "bge-m3:latest", "digest": "0" * 64}]}
            raise AssertionError("embedding must not execute after live identity mismatch")

        with self.assertRaisesRegex(RuntimeError, "BGE_LIVE_MODEL_DIGEST_NOT_QUALIFIED"):
            BgeM3CandidateAdapter(transport=transport).run(self.packet())

    def _openrouter_root(self, released_stage_usd: str) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / "configs").mkdir(parents=True)
        (root / "schemas/assistive").mkdir(parents=True)
        task_registry = json.loads(
            (Path(__file__).resolve().parents[1] / "configs/openrouter_task_registry.json").read_text(encoding="utf-8")
        )
        (root / "configs/openrouter_task_registry.json").write_text(
            json.dumps(task_registry), encoding="utf-8"
        )
        for schema_name in (
            "candidate_patch.schema.json",
            "independent_review.schema.json",
            "reconciliation_ranking.schema.json",
            "schema_drift_review.schema.json",
            "visual_layout_triage.schema.json",
        ):
            schema_path = Path(__file__).resolve().parents[1] / "schemas/assistive" / schema_name
            (root / "schemas/assistive" / schema_name).write_text(
                schema_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
        policy = json.loads(
            (Path(__file__).resolve().parents[1] / "configs/openrouter_assist_policy.json").read_text(encoding="utf-8")
        )
        policy["storage"]["root"] = str(root / "storage")
        policy["budget"]["paid_hard_limit_usd"] = "1.00"
        policy["budget"]["released_stage_usd"] = released_stage_usd
        policy_path = root / "configs/openrouter_assist_policy.json"
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        return temporary, root, policy_path

    @staticmethod
    def _openrouter_packet(root: Path) -> dict[str, object]:
        schema = json.loads(
            (root / "schemas/assistive/independent_review.schema.json").read_text(encoding="utf-8")
        )
        packet = {
            "provider": "openrouter",
            "task_format": OPENROUTER_TASK_FORMAT,
            "task_id": "independent_review",
            "jira_unit": "POST-SUBTASK-199",
            "schema_sha256": sha256_value(schema),
            "request_schema_version": "v1",
            "provider_policy_version": "openrouter-assistive-development-plane-v2-paid-authorization",
            "model": "qwen/qwen3-coder-next",
            "reasoning_effort": "none",
            "max_output_tokens": 256,
            "base_commit": "a" * 40,
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            "source_hashes": ["b" * 64],
            "prompt_version": "v1",
            "evidence_excerpts": ["bounded evidence"],
        }
        packet["identity_hashes"] = {
            "task_sha256": sha256_value(
                {
                    "task_id": packet["task_id"],
                    "jira_unit": packet["jira_unit"],
                    "authority": packet["authority"],
                }
            ),
            "schema_sha256": sha256_value(
                {"schema_version": packet["request_schema_version"], "schema_sha256": packet["schema_sha256"]}
            ),
            "policy_sha256": sha256_value(
                {
                    "provider_policy_version": packet["provider_policy_version"],
                    "task_format": packet["task_format"],
                }
            ),
            "model_sha256": sha256_value({"model": packet["model"]}),
            "reasoning_sha256": sha256_value(
                {"reasoning_effort": packet["reasoning_effort"], "max_output_tokens": packet["max_output_tokens"]}
            ),
            "source_sha256": sha256_value(tuple(packet["source_hashes"])),
        }
        return packet

    def test_openrouter_wrong_route_fails_closed(self) -> None:
        temporary, root, policy_path = self._openrouter_root("0.25")
        self.addCleanup(temporary.cleanup)
        adapter = GovernedOpenRouterAdapter(
            root,
            policy_path=policy_path,
            backend_factory=lambda _env: FakeBackend(
                {
                    "verdict": "REVIEW",
                    "findings": [],
                    "evidence": [],
                    "unsupported_claims": [],
                    "recommended_checks": [],
                }
            ),
        )
        packet = self._openrouter_packet(root)
        packet["task_format"] = "wrong"
        with self.assertRaisesRegex(RuntimeError, "OPENROUTER_TASK_FORMAT_NOT_ADMITTED"):
            adapter.run(packet)

    def test_openrouter_budget_gate_rejects_without_provider_call(self) -> None:
        temporary, root, policy_path = self._openrouter_root("0.00")
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(
            {
                "verdict": "REVIEW",
                "findings": [],
                "evidence": [],
                "unsupported_claims": [],
                "recommended_checks": [],
            }
        )
        adapter = GovernedOpenRouterAdapter(
            root,
            policy_path=policy_path,
            backend_factory=lambda _env: backend,
        )
        result = adapter.run(self._openrouter_packet(root))
        self.assertEqual("REJECTED", result.disposition)
        self.assertEqual(0, backend.calls)
        self.assertIn("PROVIDER_RELEASED_STAGE_EXCEEDED", result.validation_errors[0])
        self.assertEqual(0, result.resource["provider_calls"])

    def test_openrouter_malformed_output_is_quarantined(self) -> None:
        temporary, root, policy_path = self._openrouter_root("0.25")
        self.addCleanup(temporary.cleanup)
        adapter = GovernedOpenRouterAdapter(
            root,
            policy_path=policy_path,
            backend_factory=lambda _env: FakeBackend({"unexpected": True}),
        )
        result = adapter.run(self._openrouter_packet(root))
        self.assertEqual("QUARANTINE", result.disposition)
        self.assertIn("STRICT_OUTPUT_INVALID", result.validation_errors[0])
        self.assertEqual(1, result.resource["provider_calls"])

    def test_openrouter_fake_provider_lifecycle_cache_and_accounting(self) -> None:
        temporary, root, policy_path = self._openrouter_root("0.25")
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(
            {
                "verdict": "REVIEW",
                "findings": [],
                "evidence": [],
                "unsupported_claims": [],
                "recommended_checks": [],
            }
        )
        adapter = GovernedOpenRouterAdapter(
            root,
            policy_path=policy_path,
            backend_factory=lambda _env: backend,
        )
        first = adapter.run(self._openrouter_packet(root))
        second = adapter.run(self._openrouter_packet(root))
        self.assertEqual("REVIEW_ONLY", first.disposition)
        self.assertEqual("REVIEW_ONLY", second.disposition)
        self.assertEqual(1, first.resource["provider_calls"])
        self.assertEqual(0, second.resource["provider_calls"])
        self.assertTrue(second.resource["cached"])
        self.assertEqual(1, backend.calls)


if __name__ == "__main__":
    unittest.main()
