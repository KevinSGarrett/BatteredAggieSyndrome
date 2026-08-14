from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.assistive_plane.controller_state import ControllerState, rfc3339
from aggie_analytics.assistive_plane.review_runtime import (
    DownstreamReviewConfig,
    DownstreamReviewConsumer,
)


class AssistiveDownstreamReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.evidence = self.root / "evidence"
        self.state = ControllerState(self.root / "state.sqlite3")
        self.state.initialize()
        self.attempt_id = "b" * 64
        self.work_unit_id = "AUTO-CURSOR-TEST"
        self.result_path = self.evidence / "provider-results/result.json"
        self.result_path.parent.mkdir(parents=True)
        self.result_path.write_text(
            json.dumps(
                {
                    "artifact_type": "GOVERNED_PROVIDER_CANDIDATE_RESULT",
                    "authority": "CANDIDATE_ONLY",
                    "result": {"findings": ["bounded discovery defect"]},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        self.result_sha256 = hashlib.sha256(self.result_path.read_bytes()).hexdigest()
        stamp = rfc3339(datetime(2026, 8, 14, tzinfo=timezone.utc))
        with self.state.transaction() as connection:
            connection.execute(
                "INSERT INTO work_units(work_unit_id,identity_sha256,jira_identity,effort_points,current_state,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (self.work_unit_id, "a" * 64, "BAT-560", 5, "CLOSED", stamp, stamp),
            )
            connection.execute(
                "INSERT INTO dispatch_attempts(attempt_id,work_unit_id,provider,route_identity,state,started_at,completed_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (self.attempt_id, self.work_unit_id, "cursor", "c" * 64, "CLOSED", stamp, stamp),
            )
            connection.execute(
                "INSERT INTO provider_runs(provider_run_id,attempt_id,provider,remote_identity,request_sha256,status,resource_json,started_at,completed_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                ("d" * 64, self.attempt_id, "cursor", "agent:run", "e" * 64, "SETTLED", "{}", stamp, stamp),
            )
            connection.execute(
                "INSERT INTO execution_artifacts(artifact_id,work_unit_id,attempt_id,artifact_type,path,sha256,bytes,recorded_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    "f" * 64,
                    self.work_unit_id,
                    self.attempt_id,
                    "PROVIDER_REQUEST_RESPONSE",
                    str(self.result_path),
                    self.result_sha256,
                    self.result_path.stat().st_size,
                    stamp,
                ),
            )
            connection.execute(
                "INSERT INTO reviews(review_id,work_unit_id,attempt_id,reviewer,disposition,evidence_sha256,review_seconds,recorded_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                ("1" * 64, self.work_unit_id, self.attempt_id, "DURABLE_QUEUE", "REVIEW_ONLY", "2" * 64, 0.0, stamp),
            )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _registry(self, *, include: bool = True) -> Path:
        entries = []
        if include:
            entries.append(
                {
                    "provider": "cursor",
                    "work_unit_id": self.work_unit_id,
                    "attempt_id": self.attempt_id,
                    "result_artifact_sha256": self.result_sha256,
                    "disposition": "MODIFIED",
                    "downstream_consumer": "MERGED_BOOTSTRAP_REPAIR",
                    "consumed_artifact_identity": "3" * 64,
                    "merged_commit": "4" * 40,
                    "changed_project_artifact": True,
                    "net_time_saved_seconds": 0.0,
                    "duplicated_by_codex": False,
                    "review_seconds": 0.25,
                    "reason": "EXACT_FINDING_WAS_MODIFIED_AND_MERGED_WITH_NO_BASELINE_TIMING",
                }
            )
        registry = self.root / "registry.json"
        registry.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "artifact_type": "ASSISTIVE_DOWNSTREAM_ADOPTION_REGISTRY",
                    "authority": "CODEX_FINAL_INTEGRATION_ONLY",
                    "default_disposition": "PENDING_NO_REGISTERED_CONSUMER",
                    "entries": entries,
                }
            ),
            encoding="utf-8",
        )
        return registry

    def _consumer(self, *, include: bool = True) -> DownstreamReviewConsumer:
        release = self.root / "releases" / ("4" * 40)
        release.mkdir(parents=True, exist_ok=True)
        (release / "RELEASE_MANIFEST.json").write_text(
            json.dumps(
                {"build_commit": "4" * 40, "source_tree_sha256": "3" * 64}
            ),
            encoding="utf-8",
        )
        return DownstreamReviewConsumer(
            self.state,
            DownstreamReviewConfig(
                registry_path=self._registry(include=include),
                evidence_root=self.evidence,
                releases_root=self.root / "releases",
            ),
        )

    def test_exact_registered_result_is_consumed_without_time_savings_credit(self) -> None:
        report = self._consumer().process(
            now=datetime(2026, 8, 14, 1, tzinfo=timezone.utc)
        )

        self.assertEqual(1, report["processed"])
        self.assertEqual(0, report["deferred"])
        self.assertEqual("MODIFIED", report["applied"][0]["disposition"])
        self.assertFalse(report["applied"][0]["accepted_useful_offload_credit"])
        self.assertTrue(Path(report["applied"][0]["decision_path"]).is_file())
        summary = self.state.provider_run_summary()["cursor"]
        self.assertEqual(0, summary["pending_downstream_review"])
        self.assertEqual(0, summary["useful_work"]["accepted_useful_outputs"])
        self.assertEqual(
            {"MODIFIED": 1}, self.state.status()["downstream_review_dispositions"]
        )

    def test_unregistered_result_remains_pending(self) -> None:
        report = self._consumer(include=False).process()

        self.assertEqual(0, report["processed"])
        self.assertEqual(1, report["deferred"])
        self.assertEqual(
            "PENDING_NO_REGISTERED_DOWNSTREAM_CONSUMER",
            report["deferred_candidates"][0]["reason"],
        )
        self.assertEqual(1, self.state.provider_run_summary()["cursor"]["pending_downstream_review"])

    def test_tampered_result_fails_closed_without_disposition(self) -> None:
        consumer = self._consumer()
        self.result_path.write_text("tampered", encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "DOWNSTREAM_REVIEW_RESULT_HASH_MISMATCH"):
            consumer.process()

        self.assertEqual(1, self.state.provider_run_summary()["cursor"]["pending_downstream_review"])

    def test_consumed_release_identity_mismatch_fails_closed(self) -> None:
        consumer = self._consumer()
        release_manifest = self.root / "releases" / ("4" * 40) / "RELEASE_MANIFEST.json"
        release_manifest.write_text(
            json.dumps({"build_commit": "4" * 40, "source_tree_sha256": "9" * 64}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            RuntimeError, "DOWNSTREAM_REVIEW_CONSUMED_RELEASE_IDENTITY_MISMATCH"
        ):
            consumer.process()

        self.assertEqual(1, self.state.provider_run_summary()["cursor"]["pending_downstream_review"])


if __name__ == "__main__":
    unittest.main()
