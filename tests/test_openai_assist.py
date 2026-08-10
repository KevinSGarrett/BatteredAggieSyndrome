from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from aggie_analytics.openai_assist.budget import BudgetError, UsageLedger
from aggie_analytics.openai_assist.contracts import Priority, ProcessingMode, TokenEstimate
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
from tools.validate_openai_assist import (
    _unsupported_structured_output_keywords,
    validate as validate_openai_assist,
)


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
            allocation="TERRA_COMPLEX",
            destination="CANDIDATE",
            max_output_tokens=256,
            priority=Priority.NORMAL,
        )

    def test_repository_contract_validator_passes(self):
        self.assertEqual([], validate_openai_assist(ROOT))

    def test_policy_budget_is_exact_and_model_effort_is_bounded(self):
        policy = AssistivePolicy.load(ROOT)
        self.assertEqual(Decimal("100.00"), policy.budget_limit)
        policy.validate_route("gpt-5-nano", "minimal")
        policy.validate_route("gpt-4o-mini", "none")
        policy.validate_route("gpt-5.6-luna", "none")
        with self.assertRaises(PolicyError):
            policy.validate_route("gpt-5.6-luna", "high")
        with self.assertRaises(PolicyError):
            policy.validate_route("gpt-5.6-sol", "none")

    def test_rebalanced_caps_and_long_context_pricing_are_enforced(self):
        policy = AssistivePolicy.load(ROOT)
        budget = policy.payload["budget"]
        self.assertEqual("15.00", budget["model_caps"]["gpt-5.6-terra"]["base_usd"])
        self.assertEqual("25.00", budget["model_caps"]["gpt-5.6-terra"]["reserve_max_usd"])
        self.assertEqual("10.00", budget["model_caps"]["gpt-5.6-sol"]["base_usd"])
        self.assertEqual("17.00", budget["model_caps"]["gpt-5.6-sol"]["reserve_max_usd"])
        estimate = policy.estimate_cost(
            "gpt-5.6-terra",
            ProcessingMode.SYNCHRONOUS,
            TokenEstimate(300_000, 0, 1_000),
        )
        self.assertEqual(Decimal("1.218"), estimate.amount_usd)

    def test_budget_stages_and_model_caps_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            policy = AssistivePolicy.load(ROOT)
            ledger = UsageLedger(policy, Path(raw))
            self.assertEqual("10.000000", ledger.summary()["stage_limit_usd"])
            with self.assertRaises(BudgetError):
                ledger.reserve(
                    request_id="stage-overrun",
                    allocation="NANO_BATCH",
                    model="gpt-5-nano",
                    estimated_max_usd=Decimal("10.01"),
                    priority="NORMAL",
                    jira_unit="POST-SUBTASK-164",
                    admission_review_id="review-1",
                )
            ledger.release_stage(
                Decimal("30.00"), evidence_id="BAT-518/BAT-519", reason="PASSING_PILOT"
            )
            self.assertEqual("30.000000", ledger.summary()["stage_limit_usd"])
            with self.assertRaisesRegex(BudgetError, "model cap exceeded"):
                ledger.reserve(
                    request_id="terra-base-overrun",
                    allocation="TERRA_COMPLEX",
                    model="gpt-5.6-terra",
                    estimated_max_usd=Decimal("14.50"),
                    priority="HIGH",
                    jira_unit="POST-SUBTASK-164",
                    admission_review_id="review-2",
                )

    def test_non_reasoning_route_omits_reasoning_parameter(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = self._temporary_repo(Path(raw))
            controller = _TestController(repo, _FakeClient({}))
            base = self._job(repo)
            job = AssistiveJob(
                **{
                    **base.__dict__,
                    "model": "gpt-4o-mini",
                    "reasoning_effort": "none",
                    "allocation": "FOUR_O_MINI_AB",
                }
            )
            prepared = controller.prepare(job, ProcessingMode.SYNCHRONOUS)
            self.assertNotIn("reasoning", prepared["body"])

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
                allocation="CONTROLLER_SETUP",
                model="gpt-5-nano",
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
                    allocation="CONTROLLER_SETUP",
                    model="gpt-5-nano",
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
        self.assertGreater(report.abstention_facts, 0)
        self.assertGreater(report.merge_decisions, 0)
        self.assertGreater(report.entity_top_k_cases, 0)

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

    def test_evaluation_measures_repeated_runs_across_prediction_artifacts(self):
        predictions = ROOT / "fixtures" / "openai_assist" / "eval_predictions.jsonl"
        report = evaluate(
            ROOT / "fixtures" / "openai_assist" / "eval_gold.jsonl",
            [predictions, predictions],
            self._schema(),
        )
        self.assertEqual(8, report.repeated_run_groups)
        self.assertEqual(1.0, report.repeated_run_consistency)

    def test_provider_unsupported_array_keywords_are_rejected_locally(self):
        self.assertEqual(
            ["$.properties.items.maxItems"],
            _unsupported_structured_output_keywords(
                {"properties": {"items": {"type": "array", "maxItems": 1}}}
            ),
        )

    def test_candidate_review_disposition_is_valid_for_candidate_job(self):
        capture = "a" * 64
        candidate = {
            "task_id": "assistive_model_evaluation",
            "source_capture_sha256": capture,
            "disposition": "REVIEW",
            "facts": [],
            "conflicts": [],
            "notes": [],
        }
        controller = object.__new__(AssistiveController)
        controller.policy = SimpleNamespace(
            payload={
                "authority": {
                    "allowed_destinations": ["CANDIDATE", "REVIEW", "QUARANTINE", "REJECTED"]
                }
            }
        )
        job = AssistiveJob(
            task_name="assistive_model_evaluation",
            jira_unit="POST-SUBTASK-161",
            source_url="file:test",
            source_capture_sha256=capture,
            source_excerpt="test",
            prompt="test",
            prompt_version="test",
            schema_path=SCHEMA_PATH,
            schema_version="1",
            model="gpt-5.6-luna",
            reasoning_effort="none",
            allocation="CROSS_MODEL_QA",
            destination="CANDIDATE",
        )
        response = {"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(candidate)}]}]}
        parsed, errors = controller._validate_candidate(response, self._schema(), job)
        self.assertEqual("REVIEW", parsed["disposition"])
        self.assertEqual([], errors)

    def test_empirical_comparison_and_gamebook_pilot_preserve_authority_boundaries(self):
        comparison = json.loads(
            (ROOT / "artifacts" / "openai_assist" / "model_comparison.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(0.0, comparison["combined_final_metrics"]["unsupported_fact_rate"])
        self.assertEqual(0.0, comparison["combined_final_metrics"]["false_merge_rate"])
        self.assertEqual(1.0, comparison["combined_final_metrics"]["repeated_run_consistency"])
        self.assertEqual("SHADOW_CANDIDATE_ONLY", comparison["authority"])
        pilot = json.loads(
            (ROOT / "artifacts" / "openai_assist" / "gamebook_pilot.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(0.0, pilot["results"]["unsupported_fact_rate"])
        self.assertEqual(1.0, pilot["results"]["strict_schema_rate"])
        self.assertEqual(1.0, pilot["results"]["field_precision"])
        self.assertEqual(1.0, pilot["results"]["field_recall"])
        self.assertEqual(1.0, pilot["results"]["evidence_accuracy"])
        self.assertEqual(0.0, pilot["results"]["cross_model_disagreement_rate"])
        self.assertFalse(pilot["route_decision"]["canonical_write_authority"])
        self.assertEqual("PASS", pilot["acceptance_matrix"][0]["disposition"])
        self.assertEqual(
            set(pilot["gold"]["required_domains"]), set(pilot["gold"]["covered_domains"])
        )
        self.assertEqual("ELIGIBLE_NOT_SUBMITTED", pilot["route_decision"]["batch_status"])
        self.assertEqual(97.815594, pilot["project_usage_after_pilot"]["remaining_usd"])

    def test_entity_review_pilot_preserves_abstention_and_no_merge_authority(self):
        pilot = json.loads(
            (ROOT / "artifacts" / "openai_assist" / "entity_review_pilot.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("SHADOW_REVIEW_ONLY_NO_MERGE_AUTHORITY", pilot["authority"])
        self.assertEqual(36, pilot["results"]["completed_predictions"])
        self.assertEqual(36, pilot["results"]["review_destination"])
        self.assertEqual(1.0, pilot["results"]["strict_schema_rate"])
        self.assertEqual(1.0, pilot["results"]["field_precision"])
        self.assertEqual(1.0, pilot["results"]["field_recall"])
        self.assertEqual(1.0, pilot["results"]["evidence_accuracy"])
        self.assertEqual(1.0, pilot["results"]["correct_abstention_rate"])
        self.assertEqual(1.0, pilot["results"]["entity_top_k_recall"])
        self.assertEqual(0.0, pilot["results"]["unsupported_fact_rate"])
        self.assertEqual(0.0, pilot["results"]["false_merge_rate"])
        self.assertEqual(0.0, pilot["results"]["candidate_set_error_rate"])
        self.assertEqual(0, pilot["results"]["canonical_writes"])
        self.assertEqual(0.0, pilot["results"]["review_time_saved_seconds"])
        self.assertFalse(pilot["route_decision"]["merge_authority"])
        self.assertFalse(pilot["route_decision"]["terra_or_sol_incremental_accuracy_in_this_pilot"])
        self.assertEqual("ELIGIBLE_NOT_SUBMITTED", pilot["route_decision"]["batch_status"])
        self.assertEqual(97.334148, pilot["project_usage_after_pilot"]["remaining_usd"])
        self.assertEqual("PASS", pilot["acceptance_matrix"][0]["disposition"])

    def test_depth_chart_pilot_preflight_includes_meaningful_terra_and_sol_without_pit_authority(self):
        config = json.loads(
            (ROOT / "configs" / "openai_depth_chart_pilot.json").read_text(encoding="utf-8")
        )
        self.assertEqual(7, len(config["samples"]))
        routes = {route["model"]: route for route in config["routes"]}
        self.assertEqual(
            {"gpt-5-nano", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"},
            set(routes),
        )
        self.assertEqual("low", routes["gpt-5.6-terra"]["reasoning_effort"])
        self.assertEqual("medium", routes["gpt-5.6-sol"]["reasoning_effort"])
        self.assertEqual("UNKNOWN", config["source_candidate"]["historical_publication_time_state"])
        self.assertFalse(config["source_candidate"]["canonical_or_pit_admission"])
        prompt_path = ROOT / config["prompt"]["path"]
        self.assertEqual(config["prompt"]["sha256"], hashlib.sha256(prompt_path.read_bytes()).hexdigest())
        report = json.loads(
            (ROOT / "artifacts" / "openai_assist" / "depth_chart_pilot.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("PASS", report["comparison_plan"]["preflight_result"])
        self.assertEqual(28, report["comparison_plan"]["request_count"])
        self.assertEqual(28, report["comparison_plan"]["request_id_count"])
        self.assertEqual(0, report["comparison_plan"]["live_api_calls"])
        self.assertEqual("0.000000", report["comparison_plan"]["actual_cost_usd"])
        self.assertFalse(report["admission"]["availability_or_injury_truth"])
        self.assertFalse(report["admission"]["historical_publication_time"])
        self.assertFalse(report["admission"]["pit_state"])
        self.assertFalse(report["admission"]["training_features"])
        self.assertFalse(report["admission"]["protected_evaluation"])


if __name__ == "__main__":
    unittest.main()
