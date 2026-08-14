from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from aggie_analytics.assistive_plane.provider_adapters import (
    BGE_MODEL_DIGEST,
    BGE_POLICY_VERSION,
    BGE_PROMPT_VERSION,
    BGE_SCHEMA_SHA256,
    BGE_SCHEMA_VERSION,
    BGE_TASK_FORMAT,
    BgeM3CandidateAdapter,
    CURSOR_IMPLEMENTATION_TASK_FORMAT,
    CURSOR_TASK_FORMAT,
    GovernedCursorAdapter,
    GovernedOpenRouterAdapter,
    OPENROUTER_TASK_FORMAT,
)
from aggie_analytics.assistive_plane.backend import FakeBackend, PermanentBackendError
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

    def test_openrouter_failed_provider_attempt_is_counted(self) -> None:
        temporary, root, policy_path = self._openrouter_root("0.25")
        self.addCleanup(temporary.cleanup)

        class FailingBackend(FakeBackend):
            def submit(self, request, schema):
                self.calls += 1
                raise PermanentBackendError("bounded failure")

        backend = FailingBackend({})
        adapter = GovernedOpenRouterAdapter(
            root,
            policy_path=policy_path,
            backend_factory=lambda _env: backend,
        )
        result = adapter.run(self._openrouter_packet(root))
        self.assertEqual("REJECTED", result.disposition)
        self.assertEqual(1, backend.calls)
        self.assertEqual(1, result.resource["provider_calls"])
        self.assertIn("PROVIDER_FAILURE", result.validation_errors[0])

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

    def test_cursor_adapter_submits_polls_and_settles_deterministic_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            (root / "configs").mkdir(parents=True)
            policy = json.loads(
                (Path(__file__).resolve().parents[1] / "configs/unified_assistive_policy.json").read_text(
                    encoding="utf-8"
                )
            )
            (root / "configs/unified_assistive_policy.json").write_text(
                json.dumps(policy), encoding="utf-8"
            )

            class FakeCursorClient:
                def __init__(self) -> None:
                    self.calls: list[tuple[str, str]] = []

                def request(self, method: str, path: str, payload=None):
                    self.calls.append((method, path))
                    if method == "POST" and path == "/agents":
                        return {"agent": {"status": "RUNNING"}}
                    if path.startswith("/agents/") and path.endswith("/usage"):
                        return {"cost": {"chargedCents": 125}, "tokens": 1234}
                    if "/runs/" in path:
                        return {"status": "FINISHED", "git": {"branchName": "cursor/test"}}
                    if path.startswith("/agents/"):
                        return {"latestRunId": "run-1", "status": "FINISHED"}
                    raise AssertionError((method, path, payload))

            client = FakeCursorClient()
            store = Path(temporary) / "cursor-store"
            adapter = GovernedCursorAdapter(root, client=client, store_root=store)
            packet = {
                "provider": "cursor",
                "task_format": CURSOR_TASK_FORMAT,
                "jira_unit": "POST-SUBTASK-202",
                "schema_sha256": "a" * 64,
                "prompt": "Review the scheduler without modifying files.",
                "repository_url": "https://github.com/KevinSGarrett/BatteredAggieSyndrome.git",
                "starting_ref": "b" * 40,
                "base_commit": "b" * 40,
                "model": "gpt-5.3-codex",
                "reasoning": "medium",
                "max_reservation_usd": "2.00",
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            handle = adapter.submit(packet)
            result = adapter.poll(packet, handle)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual("REVIEW_ONLY", result.disposition)
            self.assertEqual("cursor/test", result.resource["branch"])
            self.assertEqual("1.25", result.actual_cost_usd)
            ledger = json.loads((store / "usage/ledger.json").read_text(encoding="utf-8"))
            self.assertEqual("1.250000", ledger["settled_usd"])
            self.assertEqual({}, ledger["reservations"])
            self.assertEqual("PERSISTENT_CONTROLLER", result.result["dispatch_origin"])

    def test_cursor_implementation_result_requires_exact_allowed_path_validation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            (root / "configs").mkdir(parents=True)
            policy = json.loads(
                (
                    Path(__file__).resolve().parents[1]
                    / "configs/unified_assistive_policy.json"
                ).read_text(encoding="utf-8")
            )
            (root / "configs/unified_assistive_policy.json").write_text(
                json.dumps(policy), encoding="utf-8"
            )

            class FakeCursorClient:
                def request(self, method: str, path: str, payload=None):
                    if method == "POST" and path == "/agents":
                        return {"agent": {"status": "RUNNING"}}
                    if path.endswith("/usage"):
                        return {"cost": {"chargedCents": 75}, "tokens": 4321}
                    if "/runs/" in path:
                        return {
                            "status": "FINISHED",
                            "git": {
                                "branches": [
                                    {
                                        "branch": "cursor/implementation-test",
                                        "repoUrl": "github.com/KevinSGarrett/BatteredAggieSyndrome",
                                    }
                                ]
                            },
                        }
                    if path.startswith("/agents/"):
                        return {"latestRunId": "run-implementation", "status": "FINISHED"}
                    raise AssertionError((method, path, payload))

            def inspect(_packet, branch):
                return {
                    "schema_version": 1,
                    "artifact_type": "CURSOR_CANDIDATE_BRANCH_VALIDATION",
                    "authority": "CANDIDATE_ONLY",
                    "base_commit": "b" * 40,
                    "head_commit": "c" * 40,
                    "branch": branch,
                    "changed_paths": ["artifacts/operations/gate.json"],
                    "allowed_paths": ["artifacts/operations/gate.json"],
                    "diff_sha256": "d" * 64,
                    "diff_bytes": 100,
                    "diff_text": "bounded diff",
                    "canonical_writes": 0,
                    "protected_decisions": 0,
                }

            adapter = GovernedCursorAdapter(
                root,
                client=FakeCursorClient(),
                store_root=Path(temporary) / "cursor-store",
                branch_inspector=inspect,
            )
            packet = {
                "provider": "cursor",
                "task_format": CURSOR_IMPLEMENTATION_TASK_FORMAT,
                "jira_unit": "POST-SUBTASK-202",
                "schema_sha256": "a" * 64,
                "prompt": "Implement only the admitted artifact.",
                "repository_url": "https://github.com/KevinSGarrett/BatteredAggieSyndrome.git",
                "starting_ref": "b" * 40,
                "base_commit": "b" * 40,
                "model": "gpt-5.3-codex",
                "reasoning": "medium",
                "max_reservation_usd": "2.00",
                "allowed_paths": ["artifacts/operations/gate.json"],
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            handle = adapter.submit(packet)
            result = adapter.poll(packet, handle)

            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual("cursor/implementation-test", result.resource["branch"])
            self.assertEqual(
                ["artifacts/operations/gate.json"], result.resource["changed_paths"]
            )
            validation_path = Path(result.resource["candidate_validation_path"])
            self.assertTrue(validation_path.is_file())
            self.assertEqual(
                "d" * 64,
                json.loads(validation_path.read_text(encoding="utf-8"))["diff_sha256"],
            )

    def test_cursor_implementation_result_rejects_out_of_scope_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            (root / "configs").mkdir(parents=True)
            policy = json.loads(
                (
                    Path(__file__).resolve().parents[1]
                    / "configs/unified_assistive_policy.json"
                ).read_text(encoding="utf-8")
            )
            (root / "configs/unified_assistive_policy.json").write_text(
                json.dumps(policy), encoding="utf-8"
            )

            class FakeCursorClient:
                def request(self, method: str, path: str, payload=None):
                    if method == "POST" and path == "/agents":
                        return {"agent": {"status": "RUNNING"}}
                    if path.endswith("/usage"):
                        return {"cost": {"chargedCents": 25}, "tokens": 123}
                    if "/runs/" in path:
                        return {
                            "status": "FINISHED",
                            "git": {"branchName": "cursor/out-of-scope-test"},
                        }
                    if path.startswith("/agents/"):
                        return {"latestRunId": "run-out-of-scope"}
                    raise AssertionError((method, path, payload))

            def inspect(_packet, branch):
                return {
                    "schema_version": 1,
                    "artifact_type": "CURSOR_CANDIDATE_BRANCH_VALIDATION",
                    "authority": "CANDIDATE_ONLY",
                    "base_commit": "b" * 40,
                    "head_commit": "c" * 40,
                    "branch": branch,
                    "changed_paths": [".env"],
                    "allowed_paths": ["artifacts/operations/gate.json"],
                    "diff_sha256": "d" * 64,
                    "diff_bytes": 10,
                    "diff_text": "forbidden candidate diff",
                    "canonical_writes": 0,
                    "protected_decisions": 0,
                }

            adapter = GovernedCursorAdapter(
                root,
                client=FakeCursorClient(),
                store_root=Path(temporary) / "cursor-store",
                branch_inspector=inspect,
            )
            packet = {
                "provider": "cursor",
                "task_format": CURSOR_IMPLEMENTATION_TASK_FORMAT,
                "jira_unit": "POST-SUBTASK-202",
                "schema_sha256": "a" * 64,
                "prompt": "Implement only the admitted artifact.",
                "repository_url": "https://github.com/KevinSGarrett/BatteredAggieSyndrome.git",
                "starting_ref": "b" * 40,
                "base_commit": "b" * 40,
                "model": "gpt-5.3-codex",
                "reasoning": "medium",
                "max_reservation_usd": "2.00",
                "allowed_paths": ["artifacts/operations/gate.json"],
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            result = adapter.poll(packet, adapter.submit(packet))

            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual("REJECTED", result.disposition)
            self.assertEqual(
                ("CURSOR_IMPLEMENTATION_VALIDATION_AUTHORITY_INVALID",),
                result.validation_errors,
            )
            self.assertEqual([], result.resource["changed_paths"])
            self.assertIsNone(result.resource["candidate_validation_path"])

    def test_cursor_adapter_recovers_settled_job_without_duplicate_post(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            (root / "configs").mkdir(parents=True)
            policy = json.loads(
                (Path(__file__).resolve().parents[1] / "configs/unified_assistive_policy.json").read_text(
                    encoding="utf-8"
                )
            )
            (root / "configs/unified_assistive_policy.json").write_text(json.dumps(policy), encoding="utf-8")

            class FakeCursorClient:
                def __init__(self) -> None:
                    self.calls: list[tuple[str, str]] = []

                def request(self, method: str, path: str, payload=None):
                    self.calls.append((method, path))
                    if method == "POST":
                        raise AssertionError("settled recovery must not submit a duplicate agent")
                    if path.endswith("/usage"):
                        return {"cost": {"chargedCents": 125}, "tokens": 1234}
                    if "/runs/" in path:
                        return {"status": "FINISHED", "git": {"branchName": "cursor/recovered"}}
                    return {"latestRunId": "run-1", "status": "FINISHED"}

            packet = {
                "provider": "cursor", "task_format": CURSOR_TASK_FORMAT,
                "jira_unit": "POST-SUBTASK-202", "schema_sha256": "a" * 64,
                "prompt": "Review the scheduler without modifying files.",
                "repository_url": "https://github.com/KevinSGarrett/BatteredAggieSyndrome.git",
                "starting_ref": "b" * 40, "base_commit": "b" * 40,
                "model": "gpt-5.3-codex", "reasoning": "medium",
                "max_reservation_usd": "2.00",
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            client = FakeCursorClient()
            adapter = GovernedCursorAdapter(root, client=client, store_root=Path(temporary) / "cursor-store")
            job_id = adapter._job_identity(packet)
            adapter.ledger.reserve(job_id, Decimal("2.00"))
            adapter.ledger.settle(job_id, Decimal("1.25"))

            handle = adapter.submit(packet)
            self.assertTrue(handle["idempotent_settled_recovery"])
            self.assertEqual(0, handle["provider_calls"])
            self.assertEqual([], client.calls)
            result = adapter.poll(packet, handle)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual("cursor/recovered", result.resource["branch"])
            self.assertFalse(any(method == "POST" for method, _ in client.calls))


if __name__ == "__main__":
    unittest.main()
