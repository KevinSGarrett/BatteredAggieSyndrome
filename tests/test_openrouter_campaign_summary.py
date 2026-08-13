from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from tools.summarize_openrouter_campaign import summarize_campaign


class OpenRouterCampaignSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in (
            "requests",
            "responses",
            "quarantine",
            "manifests",
            "settlements",
            "provider",
            "reviews",
        ):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_json(self, relative_path: str, payload: object) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_summary_includes_paid_quarantine_usage_and_dedupes_reviews(self) -> None:
        self._write_json("requests/requests.json", [{"request_id": "req-1"}, {"request_id": "req-2"}])
        self._write_json(
            "responses/response.json",
            {
                "request_id": "req-1",
                "usage": {"input_tokens": 10, "output_tokens": 5, "cost": "0.001000"},
                "model": "model-alpha",
                "provider": "openrouter",
                "category": "campaign-unit",
            },
        )
        self._write_json(
            "quarantine/quarantine.json",
            {
                "request_id": "req-2",
                "usage": {"input_tokens": 4, "output_tokens": 6, "cost": "0.002000"},
                "model": "model-beta",
                "provider": "openrouter",
                "category": "campaign-unit",
                "disposition": "QUARANTINE",
            },
        )
        self._write_json(
            "manifests/manifest.json",
            [{"request_id": "req-1", "disposition": "accepted"}, {"request_id": "req-2", "disposition": "quarantined"}],
        )
        self._write_json(
            "settlements/ledger.json",
            {"settlements": {"req-1": "0.001000", "req-2": "0.002000"}},
        )
        self._write_json(
            "provider/provider.json",
            [
                {"request_id": "req-1", "cost_usd": "0.001000"},
                {"request_id": "req-2", "cost_usd": "0.002000"},
            ],
        )
        self._write_json(
            "reviews/reviews.jsonl.json",
            [
                {
                    "request_id": "req-1",
                    "review_record_id": "rev-1",
                    "review_revision": 1,
                    "reviewed_at": "2026-08-13T12:00:00Z",
                    "disposition": "accepted",
                },
                {
                    "request_id": "req-2",
                    "review_record_id": "rev-2-older",
                    "review_revision": 1,
                    "reviewed_at": "2026-08-13T12:00:00Z",
                    "disposition": "review_only",
                },
                {
                    "request_id": "req-2",
                    "review_record_id": "rev-2-newer",
                    "supersedes_review_record_id": "rev-2-older",
                    "review_revision": 2,
                    "reviewed_at": "2026-08-13T12:05:00Z",
                    "disposition": "quarantined",
                },
            ],
        )

        summary = summarize_campaign(
            requests_root=self.root / "requests",
            responses_root=self.root / "responses",
            quarantine_root=self.root / "quarantine",
            manifests_root=self.root / "manifests",
            settlements_root=self.root / "settlements",
            provider_usage_root=self.root / "provider",
            reviews_root=self.root / "reviews",
            hard_budget_usd=Decimal("1.00"),
        )

        self.assertEqual(summary["request_count"], 2)
        self.assertEqual(summary["quarantined_request_count"], 1)
        self.assertEqual(summary["input_tokens"], 14)
        self.assertEqual(summary["output_tokens"], 11)
        self.assertEqual(summary["total_cost_usd"], "0.00300000")
        self.assertEqual(summary["counts_by_disposition"]["accepted"], 1)
        self.assertEqual(summary["counts_by_disposition"]["quarantined"], 1)
        self.assertEqual(summary["counts_by_model"]["model-alpha"], 1)
        self.assertEqual(summary["counts_by_model"]["model-beta"], 1)
        self.assertEqual(summary["remaining_budget_usd"], "0.997000")

    def test_real_content_addressed_shape_infers_request_identity_and_reconciles_provider_total(self) -> None:
        request = {
            "task_id": "independent_review",
            "jira_unit": "POST-SUBTASK-199",
            "base_commit": "a" * 40,
            "authority": "INDEPENDENT_REVIEW",
            "prompt_version": "v1",
            "schema_version": "v1",
            "schema_sha256": "b" * 64,
            "source_hashes": ["c" * 64],
            "evidence_excerpts": ["bounded evidence"],
            "model": "qwen/qwen3-coder-next",
            "reasoning_effort": "none",
            "max_output_tokens": 128,
            "provider_policy_version": "policy-v1",
        }
        request_id = hashlib.sha256(
            json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        request_data = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        request_artifact_sha = hashlib.sha256(request_data).hexdigest()
        request_path = self.root / "requests/sha256" / request_artifact_sha[:2] / request_artifact_sha / "artifact.json"
        request_path.parent.mkdir(parents=True)
        request_path.write_bytes(request_data)
        self._write_json(
            "responses/response.json",
            {
                "request_id": request_id,
                "usage": {"input_tokens": 10, "output_tokens": 5, "cost": "0.001000"},
                "model_resolved": request["model"],
                "provider": "openrouter",
            },
        )
        self._write_json("quarantine/quarantine.json", [])
        self._write_json("manifests/manifest.json", {"request_id": request_id, "disposition": "CANDIDATE"})
        self._write_json(
            "settlements/ledger.json",
            {
                "settled_usd": "0.001500",
                "settlements": {request_id: "0.001000"},
                "provider_reconciliation": {
                    "status": "PROVIDER_TOTAL_RECONCILED",
                    "provider_total_usd": "0.001500",
                    "evidence_sha256": "d" * 64,
                },
            },
        )
        self._write_json("provider/provider.json", [])
        self._write_json(
            "reviews/review-report.json",
            {"rows": [{"request_id": request_id, "disposition": "ACCEPTED_REVIEW_EVIDENCE_ONLY"}]},
        )
        summary = summarize_campaign(
            requests_root=self.root / "requests",
            responses_root=self.root / "responses",
            quarantine_root=self.root / "quarantine",
            manifests_root=self.root / "manifests",
            settlements_root=self.root / "settlements",
            provider_usage_root=self.root / "provider",
            reviews_root=self.root / "reviews",
            hard_budget_usd=Decimal("1.00"),
        )
        self.assertEqual(1, summary["request_count"])
        self.assertTrue(summary["provider_reconciled"])
        self.assertEqual("0.00150000", summary["total_cost_usd"])
        self.assertEqual("READY", summary["routes"][0]["readiness_supported_state"])
        self.assertEqual(1, summary["routes"][0]["complete_evidence_count"])

    def test_identity_mismatch_fails_closed(self) -> None:
        self._write_json("requests/requests.json", [{"request_id": "req-1"}])
        self._write_json("responses/response.json", {"request_id": "req-1", "usage": {"cost": "0.001"}})
        self._write_json("quarantine/quarantine.json", [])
        self._write_json("manifests/manifest.json", [{"request_id": "req-1", "disposition": "accepted"}])
        self._write_json("settlements/ledger.json", {"settlements": {"req-1": "0.001"}})
        self._write_json("provider/provider.json", [{"request_id": "req-2", "cost_usd": "0.001"}])
        self._write_json("reviews/reviews.json", [{"request_id": "req-1", "disposition": "accepted"}])

        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            summarize_campaign(
                requests_root=self.root / "requests",
                responses_root=self.root / "responses",
                quarantine_root=self.root / "quarantine",
                manifests_root=self.root / "manifests",
                settlements_root=self.root / "settlements",
                provider_usage_root=self.root / "provider",
                reviews_root=self.root / "reviews",
                hard_budget_usd=Decimal("1.00"),
            )

    def test_cost_mismatch_fails_closed(self) -> None:
        self._write_json("requests/requests.json", [{"request_id": "req-1"}])
        self._write_json("responses/response.json", {"request_id": "req-1", "usage": {"cost": "0.001"}})
        self._write_json("quarantine/quarantine.json", [])
        self._write_json("manifests/manifest.json", [{"request_id": "req-1", "disposition": "accepted"}])
        self._write_json("settlements/ledger.json", {"settlements": {"req-1": "0.002"}})
        self._write_json("provider/provider.json", [{"request_id": "req-1", "cost_usd": "0.001"}])
        self._write_json("reviews/reviews.json", [{"request_id": "req-1", "disposition": "accepted"}])

        with self.assertRaisesRegex(RuntimeError, "cost mismatch"):
            summarize_campaign(
                requests_root=self.root / "requests",
                responses_root=self.root / "responses",
                quarantine_root=self.root / "quarantine",
                manifests_root=self.root / "manifests",
                settlements_root=self.root / "settlements",
                provider_usage_root=self.root / "provider",
                reviews_root=self.root / "reviews",
                hard_budget_usd=Decimal("1.00"),
            )


if __name__ == "__main__":
    unittest.main()
