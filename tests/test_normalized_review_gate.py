"""Latest-head review gate: missing SHA, later failure, and duplicates."""

from __future__ import annotations

import unittest

from aggie_analytics.governance.normalized_review_gate import (
    evaluate_latest_head_checks,
)


HEAD = "3fcc710438a75f15abc23392c6136ac077f25e7b"


class NormalizedReviewGateShaTests(unittest.TestCase):
    def test_missing_sha_is_not_filled_from_requested_head(self) -> None:
        result = evaluate_latest_head_checks(
            head_sha=HEAD,
            checks=[
                {"name": "codex-review", "conclusion": "success"},
                {"name": "codecov/patch", "head_sha": HEAD, "conclusion": "success"},
            ],
        )
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(
                "REQUIRED_CHECK_MISSING_HEAD_SHA:codex-review" in item
                for item in result["findings"]
            )
        )
        observed = result["observed"]["codex-review"]
        self.assertTrue(observed is None or observed.get("head_sha") != HEAD)

    def test_later_failed_attempt_beats_older_success(self) -> None:
        result = evaluate_latest_head_checks(
            head_sha=HEAD,
            checks=[
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "completed_at": "2026-09-04T15:00:00Z",
                    "id": 1,
                },
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "failure",
                    "completed_at": "2026-09-04T15:22:00Z",
                    "id": 2,
                },
                {
                    "name": "codecov/patch",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "completed_at": "2026-09-04T15:23:00Z",
                    "id": 3,
                },
            ],
        )
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["observed"]["codex-review"]["classified"], "REJECTED_NOT_SUCCESS"
        )
        self.assertTrue(
            any("REQUIRED_CHECK_NOT_SUCCESS" in item for item in result["findings"])
        )

    def test_ambiguous_duplicate_latest_attempts_fail(self) -> None:
        result = evaluate_latest_head_checks(
            head_sha=HEAD,
            checks=[
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "completed_at": "2026-09-04T15:22:00Z",
                    "id": 1,
                },
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "failure",
                    "completed_at": "2026-09-04T15:22:00Z",
                    "id": 2,
                },
                {
                    "name": "codecov/patch",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "completed_at": "2026-09-04T15:23:00Z",
                    "id": 3,
                },
            ],
        )
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(
                "REQUIRED_CHECK_AMBIGUOUS_DUPLICATE:codex-review" in item
                for item in result["findings"]
            )
        )

    def test_pending_latest_attempt_blocks(self) -> None:
        result = evaluate_latest_head_checks(
            head_sha=HEAD,
            checks=[
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "status": "in_progress",
                    "completed_at": "2026-09-04T15:22:00Z",
                    "id": 1,
                },
                {
                    "name": "codecov/patch",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "status": "completed",
                    "completed_at": "2026-09-04T15:23:00Z",
                    "id": 2,
                },
            ],
        )
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(
                "REQUIRED_CHECK_NOT_COMPLETED:codex-review" in item
                for item in result["findings"]
            )
        )

    def test_newer_in_progress_rerun_beats_older_success(self) -> None:
        result = evaluate_latest_head_checks(
            head_sha=HEAD,
            checks=[
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "status": "completed",
                    "completed_at": "2026-09-04T15:00:00Z",
                    "started_at": "2026-09-04T14:59:00Z",
                    "id": 1,
                },
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "",
                    "status": "in_progress",
                    "completed_at": "",
                    "started_at": "2026-09-04T15:30:00Z",
                    "id": 2,
                },
                {
                    "name": "codecov/patch",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "status": "completed",
                    "completed_at": "2026-09-04T15:23:00Z",
                    "id": 3,
                },
            ],
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["observed"]["codex-review"]["status"], "in_progress")
        self.assertTrue(
            any(
                "REQUIRED_CHECK_NOT_COMPLETED:codex-review" in item
                for item in result["findings"]
            )
        )

    def test_queued_rerun_without_timestamps_beats_older_success(self) -> None:
        result = evaluate_latest_head_checks(
            head_sha=HEAD,
            checks=[
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "status": "completed",
                    "completed_at": "2026-09-04T15:00:00Z",
                    "id": 1,
                },
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "",
                    "status": "queued",
                    "id": 2,
                },
                {
                    "name": "codecov/patch",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "status": "completed",
                    "completed_at": "2026-09-04T15:23:00Z",
                    "id": 3,
                },
            ],
        )
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(
                "REQUIRED_CHECK_NOT_COMPLETED:codex-review" in item
                for item in result["findings"]
            )
        )


if __name__ == "__main__":
    unittest.main()
