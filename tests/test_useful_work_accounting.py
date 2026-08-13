from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.assistive_plane.controller_state import ControllerState, rfc3339
from tools.reconcile_assistive_review_backlog import reconcile


class UsefulWorkAccountingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.state = ControllerState(self.root / "state.sqlite3")
        self.state.initialize()
        stamp = rfc3339(datetime(2026, 8, 14, tzinfo=timezone.utc))
        with self.state.transaction() as connection:
            connection.execute(
                "INSERT INTO work_units(work_unit_id,identity_sha256,jira_identity,effort_points,current_state,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?)",
                ("BGE-1", "a" * 64, "BAT-562", 2, "CLOSED", stamp, stamp),
            )
            connection.execute(
                "INSERT INTO dispatch_attempts(attempt_id,work_unit_id,provider,route_identity,state,started_at,completed_at) "
                "VALUES(?,?,?,?,?,?,?)",
                ("b" * 64, "BGE-1", "ollama_local", "c" * 64, "CLOSED", stamp, stamp),
            )
            connection.execute(
                "INSERT INTO provider_runs(provider_run_id,attempt_id,provider,remote_identity,request_sha256,status,resource_json,started_at,completed_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                ("d" * 64, "b" * 64, "ollama_local", "bge-m3@sha256:test", "e" * 64, "SETTLED", "{}", stamp, stamp),
            )
            connection.execute(
                "INSERT INTO reviews(review_id,work_unit_id,attempt_id,reviewer,disposition,evidence_sha256,review_seconds,recorded_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                ("f" * 64, "BGE-1", "b" * 64, "DURABLE_QUEUE", "REVIEW_ONLY", "f" * 64, 0.0, stamp),
            )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_acceptance_requires_real_consumption_evidence(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "DOWNSTREAM_ACCEPTANCE_CONSUMPTION_EVIDENCE_INCOMPLETE"
        ):
            self.state.record_downstream_review_disposition(
                attempt_id="b" * 64,
                disposition="ACCEPTED",
                downstream_consumer="HISTORICAL_RECONCILIATION",
                reason="test",
            )

    def test_review_only_backlog_is_drained_as_unused_without_credit(self) -> None:
        report = reconcile(
            self.state,
            provider="ollama_local",
            report_root=self.root / "reports",
            apply=True,
            limit=10,
        )
        self.assertEqual(1, report["candidate_count"])
        self.assertEqual({"UNUSED": 1}, report["disposition_counts"])
        self.assertEqual(0, report["accepted_useful_offload_credit"])
        summary = self.state.provider_run_summary()["ollama_local"]
        self.assertEqual(0, summary["pending_downstream_review"])


if __name__ == "__main__":
    unittest.main()
