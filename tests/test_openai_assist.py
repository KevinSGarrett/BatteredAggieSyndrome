from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from aggie_analytics.openai_assist.budget import BudgetError, UsageLedger
from aggie_analytics.openai_assist.contracts import Priority, ProcessingMode
from aggie_analytics.openai_assist.controller import AssistiveController, AssistiveJob, ControllerError
from aggie_analytics.openai_assist.evals import evaluate
from aggie_analytics.openai_assist.policy import AssistivePolicy, PolicyError
from aggie_analytics.openai_assist.redaction import RedactionError, assert_prompt_safe
from aggie_analytics.openai_assist.schemas import (
    SchemaContractError,
    evidence_errors,
    validate_instance,
    validate_strict_output_schema,
)
from tools.validate_openai_assist import validate as validate_openai_assist


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "openai" / "assistive_candidate.schema.json"


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, mode="json"):
        return copy.deepcopy(self.payload)


class _Responses:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **body):
        self.calls.append(body)
        return _Response(self.response)


class _FakeClient:
    def __init__(self, response):
        self.responses = _Responses(response)


class _Files:
    def __init__(self):
        self.deleted = []

    def create(self, **kwargs):
        return _Response({"id": "file_test"})

    def delete(self, file_id):
        self.deleted.append(file_id)


class _FailingBatches:
    def create(self, **kwargs):
        raise RuntimeError("simulated batch submission failure")


class _FakeBatchFailureClient:
    def __init__(self):
        self.files = _Files()
        self.batches = _FailingBatches()


class _TestController(AssistiveController):
    def __init__(self, repo_root: Path, client, secrets=()):
        self.fake_client = client
        self.fake_secrets = tuple(secrets)
        super().__init__(repo_root)

    def _client(self):
        return self.fake_client

    def _configured_secret_values(self):
        return self.fake_secrets


class OpenAIAssistTests(unittest.TestCase):
    def _schema(self):
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def _temporary_repo(self, directory: Path) -> Path:
        repo = directory / "repo"
        (repo / "configs").mkdir(parents=True)
        (repo / "schemas" / "openai").mkdir(parents=True)
        policy = json.loads((ROOT / "configs" / "openai_assist_policy.json").read_text(encoding="utf-8"))
        policy["storage"]["root"] = str(directory / "external")
        (repo / "configs" / "openai_assist_policy.json").write_text(
            json.dumps(policy), encoding="utf-8"
        )
        shutil.copy2(ROOT / "configs" / "openai_task_registry.json", repo / "configs")
        shutil.copy2(SCHEMA_PATH, repo / "schemas" / "openai")
        return repo

    def _job(self, repo: Path, excerpt: str = "Attendance: 102,733.") -> AssistiveJob:
        return AssistiveJob(
            task_name="gamebook_extraction",
            jira_unit="POST-SUBTASK-162",
            source_url="https://example.test/gamebook",
            source_capture_sha256=hashlib.sha256(excerpt.encode()).hexdigest(),
            source_excerpt=excerpt,
            prompt="Extract attendance with line evidence.",
            prompt_version="gamebook-v1",
            schema_path=repo / "schemas" / "openai" / "assistive_candidate.schema.json",
            schema_version="1",
            model="gpt-5.6-terra",
            reasoning_effort="medium",
            allocation="PROBE_PROMPT_EVAL",
            destination="CANDIDATE",
            max_output_tokens=256,
            priority=Priority.NORMAL,
        )

    def test_repository_contract_validator_passes(self):
        self.assertEqual([], validate_openai_assist(ROOT))

    def test_policy_budget_is_exact_and_model_effort_is_bounded(self):
        policy = AssistivePolicy.load(ROOT)
        self.assertEqual(Decimal("100.00"), policy.budget_limit)
        policy.validate_route("gpt-5.6-luna", "none")
        with self.assertRaises(PolicyError):
            policy.validate_route("gpt-5.6-luna", "high")
        with self.assertRaises(PolicyError):
            policy.validate_route("gpt-5.6-sol", "none")

    def test_strict_schema_requires_all_properties_and_closed_objects(self):
        validate_strict_output_schema(self._schema())
        bad = {"type": "object", "properties": {"x": {"type": "string"}}}
        with self.assertRaises(SchemaContractError):
            validate_strict_output_schema(bad)

    def test_instance_and_evidence_validation_reject_unsupported_fact(self):
        capture = "a" * 64
        candidate = {
            "task_id": "x",
            "source_capture_sha256": capture,
            "disposition": "CANDIDATE",
            "facts": [{"field": "attendance", "value": 100, "status": "SUPPORTED", "evidence": []}],
            "conflicts": [],
            "notes": [],
        }
        self.assertEqual([], validate_instance(candidate, self._schema()))
        self.assertIn("supported fact has no evidence", evidence_errors(candidate, capture_sha256=capture)[0])

    def test_redaction_rejects_keys_headers_and_env_content(self):
        for payload in [
            {"api_key": "anything"},
            {"text": "Authorization: Bearer abcdefghijklmnop"},
            {"text": "OPENAI_API_KEY=not-allowed"},
        ]:
            with self.assertRaises(RedactionError):
                assert_prompt_safe(payload)

    def test_exact_configured_secret_is_rejected_before_api_call(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = self._temporary_repo(Path(raw))
            secret = "PLACEHOLDER_OPAQUE_CREDENTIAL_VALUE"
            client = _FakeClient({})
            controller = _TestController(repo, client, secrets=(secret,))
            with self.assertRaises(RedactionError):
                controller.run_sync(self._job(repo, excerpt=secret))
            self.assertEqual([], client.responses.calls)

    def test_budget_reserves_settles_and_hard_stops(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            policy = AssistivePolicy(ROOT, json.loads(
                (ROOT / "configs" / "openai_assist_policy.json").read_text(encoding="utf-8")
            ))
            ledger = UsageLedger(policy, root)
            reservation = ledger.reserve(
                request_id="r1",
                allocation="PROBE_PROMPT_EVAL",
                estimated_max_usd=Decimal("1.00"),
                priority="NORMAL",
                jira_unit="POST-SUBTASK-162",
            )
            self.assertEqual("1.000000", ledger.summary()["committed_usd"])
            ledger.settle(reservation, actual_usd=Decimal("0.25"), usage={"input_tokens": 1})
            self.assertEqual("0.250000", ledger.summary()["settled_usd"])
            with self.assertRaises(BudgetError):
                ledger.reserve(
                    request_id="too-large",
                    allocation="PROBE_PROMPT_EVAL",
                    estimated_max_usd=Decimal("10.00"),
                    priority="NORMAL",
                    jira_unit="POST-SUBTASK-162",
                )

    def test_response_body_is_store_false_and_batch_uses_responses(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = self._temporary_repo(Path(raw))
            controller = _TestController(repo, _FakeClient({}))
            job = self._job(repo)
            prepared = controller.prepare(job, ProcessingMode.SYNCHRONOUS)
            self.assertIs(False, prepared["body"]["store"])
            self.assertEqual("json_schema", prepared["body"]["text"]["format"]["type"])
            payload, _ = controller.prepare_batch_jsonl([job])
            line = json.loads(payload)
            self.assertEqual("/v1/responses", line["url"])
            self.assertIs(False, line["body"]["store"])

    def test_batch_schema_reference_is_repository_relative_and_cannot_escape(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = self._temporary_repo(Path(raw))
            controller = _TestController(repo, _FakeClient({}))
            schema = repo / "schemas" / "openai" / "assistive_candidate.schema.json"
            reference = controller._schema_reference(schema)
            self.assertEqual("schemas/openai/assistive_candidate.schema.json", reference)
            self.assertEqual(schema.resolve(), controller._resolve_schema_reference(reference))
            with self.assertRaises(ControllerError):
                controller._resolve_schema_reference("../outside.schema.json")

    def test_batch_submission_failure_releases_budget_and_deletes_remote_input(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = self._temporary_repo(Path(raw))
            client = _FakeBatchFailureClient()
            controller = _TestController(repo, client)
            with self.assertRaisesRegex(RuntimeError, "simulated batch submission failure"):
                controller.submit_batch([self._job(repo)])
            self.assertEqual(["file_test"], client.files.deleted)
            self.assertEqual("0.000000", controller.ledger.summary()["reserved_usd"])

    def test_fake_sync_response_is_candidate_only_and_idempotently_cached(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = self._temporary_repo(Path(raw))
            job = self._job(repo)
            capture = job.source_capture_sha256
            candidate = {
                "task_id": "gamebook_extraction",
                "source_capture_sha256": capture,
                "disposition": "CANDIDATE",
                "facts": [
                    {
                        "field": "attendance",
                        "value": 102733,
                        "status": "SUPPORTED",
                        "evidence": [
                            {
                                "source_capture_sha256": capture,
                                "locator": "line:1",
                                "excerpt_sha256": capture,
                            }
                        ],
                    }
                ],
                "conflicts": [],
                "notes": [],
            }
            response = {
                "id": "resp_test",
                "model": "gpt-5.6-terra-2026-08-01",
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": json.dumps(candidate)}]}
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 10},
                },
            }
            client = _FakeClient(response)
            controller = _TestController(repo, client)
            first = controller.run_sync(job)
            second = controller.run_sync(job)
            self.assertEqual("CANDIDATE", first.disposition)
            self.assertFalse(first.cached)
            self.assertTrue(second.cached)
            self.assertEqual(1, len(client.responses.calls))
            self.assertIs(False, client.responses.calls[0]["store"])

    def test_local_evaluation_corpus_covers_required_categories(self):
        report = evaluate(
            ROOT / "fixtures" / "openai_assist" / "eval_gold.jsonl",
            ROOT / "fixtures" / "openai_assist" / "eval_predictions.jsonl",
            self._schema(),
        )
        self.assertEqual(8, report.cases)
        self.assertEqual(8, report.prediction_runs)
        self.assertEqual(1.0, report.strict_schema_rate)
        self.assertEqual(0.0, report.unsupported_fact_rate)
        self.assertEqual(0.0, report.false_merge_rate)
        self.assertEqual(0, report.repeated_run_groups)
        self.assertIsNone(report.repeated_run_consistency)
        self.assertEqual(0, report.cross_model_groups)
        self.assertIsNone(report.cross_model_disagreement_rate)

    def test_evaluation_counts_wrong_expected_fact_as_false_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            predictions = Path(tmp) / "predictions.jsonl"
            row = json.loads(
                (ROOT / "fixtures" / "openai_assist" / "eval_predictions.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()[0]
            )
            row["candidate"]["facts"][0]["value"] = 1
            predictions.write_text(json.dumps(row) + "\n", encoding="utf-8")
            report = evaluate(
                ROOT / "fixtures" / "openai_assist" / "eval_gold.jsonl",
                predictions,
                self._schema(),
            )
            self.assertLess(report.field_precision, 1.0)
            self.assertLess(report.field_recall, 1.0)


if __name__ == "__main__":
    unittest.main()
