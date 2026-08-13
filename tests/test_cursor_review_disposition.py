from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.cursor_backend import cursor_agent_identity
from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json
from tools.record_cursor_review_disposition import record_review_disposition


class CursorReviewDispositionTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[dict[str, object], str, str]:
        job_id = "a" * 64
        agent_id = cursor_agent_identity(job_id)
        base_commit = "b" * 40
        cursor_commit = "c" * 40
        result, result_sha256 = write_content_addressed_json(
            root,
            "results",
            {
                "job_id": job_id,
                "agent_id": agent_id,
                "jira_unit": "POST-SUBTASK-202",
                "run": {
                    "status": "FINISHED",
                    "result": f"Commit SHA: {cursor_commit}",
                    "git": {"branches": [{"branch": "cursor/test"}]},
                },
            },
        )
        self.assertTrue(result.is_file())
        write_content_addressed_json(root, "requests", {"job_id": job_id, "agent_id": agent_id})
        write_content_addressed_json(
            root,
            "manifests",
            {
                "job_id": job_id,
                "agent_id": agent_id,
                "jira_unit": "POST-SUBTASK-202",
                "base_commit": base_commit,
                "model": "gpt-5.3-codex",
                "reasoning": "low",
                "fast": False,
                "auto_create_pr": False,
                "work_on_current_branch": False,
                "canonical_write_authority": False,
                "protected_decision_authority": False,
            },
        )
        settlement_payload = {
            "job_id": job_id,
            "agent_id": agent_id,
            "result_sha256": result_sha256,
            "provider_aggregate_usd": "0.25",
            "reservation_resolved": True,
            "provider_usage": {
                "runs": [{"id": "run-1"}],
                "totalUsage": {
                    "inputTokens": 10,
                    "outputTokens": 5,
                    "cacheReadTokens": 2,
                    "cacheWriteTokens": 0,
                    "totalTokens": 17,
                },
            },
        }
        write_content_addressed_json(root, "settlements", settlement_payload)
        (root / "usage").mkdir(parents=True)
        (root / "usage" / "ledger.json").write_text(
            json.dumps({"settlements": {job_id: "0.25"}}), encoding="utf-8"
        )
        review: dict[str, object] = {
            "schema_version": 1,
            "jira_unit": "POST-SUBTASK-202",
            "campaign_unit": 7,
            "job_id": job_id,
            "agent_id": agent_id,
            "cursor_branch": "cursor/test",
            "cursor_commit": cursor_commit,
            "integration_pr": 301,
            "integration_commit": "d" * 40,
            "disposition": "ACCEPTED",
            "contribution": ["bounded improvement"],
            "codex_review_edits": [],
            "negative_findings": [],
            "local_validation": {"exit_code": 0, "passed": 1, "failed": 0},
            "review_started_at_utc": "2026-08-13T00:00:00Z",
            "review_completed_at_utc": "2026-08-13T00:01:00Z",
            "measured_review_and_orchestration_minutes": 1.0,
            "direct_baseline_minutes": None,
        }
        return review, job_id, agent_id

    def test_records_evidence_bound_review_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            review, _, _ = self.fixture(root)
            first_path, first_digest, record = record_review_disposition(
                review,
                storage_root=root,
                repository=ROOT,
                ancestry_checker=lambda *_: True,
                subject_reader=lambda *_: "bounded change (#301)",
            )
            second_path, second_digest, _ = record_review_disposition(
                review,
                storage_root=root,
                repository=ROOT,
                ancestry_checker=lambda *_: True,
                subject_reader=lambda *_: "bounded change (#301)",
            )
            self.assertEqual(first_path, second_path)
            self.assertEqual(first_digest, second_digest)
            self.assertEqual("0.25", record["provider_usage"]["actual_usd"])
            self.assertEqual(1, record["accepted_useful_results"])
            self.assertEqual("TRANSITIONAL_CURSOR_CLI_CONTROLLER", record["dispatch_origin"])

    def test_rejects_unsettled_or_unintegrated_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            review, job_id, _ = self.fixture(root)
            (root / "usage" / "ledger.json").write_text(
                json.dumps({"settlements": {job_id: "0.24"}}), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "LEDGER_SETTLEMENT_MISMATCH"):
                record_review_disposition(
                    review,
                    storage_root=root,
                    repository=ROOT,
                    ancestry_checker=lambda *_: True,
                    subject_reader=lambda *_: "bounded change (#301)",
                )

    def test_reconciles_initial_and_finalize_settlements(self) -> None:
        import hashlib

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            review, job_id, _ = self.fixture(root)
            finalize_id = hashlib.sha256(f"{job_id}:finalize:v1".encode("utf-8")).hexdigest()
            (root / "usage" / "ledger.json").write_text(
                json.dumps({"settlements": {job_id: "0.20", finalize_id: "0.05"}}), encoding="utf-8"
            )
            _, _, record = record_review_disposition(
                review,
                storage_root=root,
                repository=ROOT,
                ancestry_checker=lambda *_: True,
                subject_reader=lambda *_: "bounded change (#301)",
            )
            self.assertEqual("0.25", record["provider_usage"]["actual_usd"])

            (root / "usage" / "ledger.json").write_text(
                json.dumps({"settlements": {job_id: "0.25"}}), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "INTEGRATION_NOT_ON_MAIN"):
                record_review_disposition(
                    review,
                    storage_root=root,
                    repository=ROOT,
                    ancestry_checker=lambda *_: False,
                    subject_reader=lambda *_: "bounded change (#301)",
                )

    def test_modified_disposition_requires_review_edits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            review, _, _ = self.fixture(root)
            review["disposition"] = "ACCEPTED_WITH_CODEX_REVIEW_EDITS"
            with self.assertRaisesRegex(ValueError, "MODIFIED_REQUIRES_EDITS"):
                record_review_disposition(
                    review,
                    storage_root=root,
                    repository=ROOT,
                    ancestry_checker=lambda *_: True,
                    subject_reader=lambda *_: "bounded change (#301)",
                )

    def test_rejects_conflicting_second_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            review, _, _ = self.fixture(root)
            record_review_disposition(
                review,
                storage_root=root,
                repository=ROOT,
                ancestry_checker=lambda *_: True,
                subject_reader=lambda *_: "bounded change (#301)",
            )
            review["review_completed_at_utc"] = "2026-08-13T00:02:00Z"
            with self.assertRaisesRegex(RuntimeError, "DUPLICATE_DISPOSITION_IDENTITY"):
                record_review_disposition(
                    review,
                    storage_root=root,
                    repository=ROOT,
                    ancestry_checker=lambda *_: True,
                    subject_reader=lambda *_: "bounded change (#301)",
                )


if __name__ == "__main__":
    unittest.main()
