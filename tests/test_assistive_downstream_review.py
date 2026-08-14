from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.assistive_plane.controller_state import ControllerState, rfc3339
from aggie_analytics.assistive_plane.review_runtime import (
    DownstreamReviewConfig,
    DownstreamReviewConsumer,
)
from aggie_analytics.assistive_plane.watchdog import ReadOnlyWatchdog


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
                (
                    self.attempt_id,
                    self.work_unit_id,
                    "cursor",
                    "c" * 64,
                    "CLOSED",
                    stamp,
                    stamp,
                ),
            )
            connection.execute(
                "INSERT INTO provider_runs(provider_run_id,attempt_id,provider,remote_identity,request_sha256,status,resource_json,started_at,completed_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "d" * 64,
                    self.attempt_id,
                    "cursor",
                    "agent:run",
                    "e" * 64,
                    "SETTLED",
                    "{}",
                    stamp,
                    stamp,
                ),
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
                (
                    "1" * 64,
                    self.work_unit_id,
                    self.attempt_id,
                    "DURABLE_QUEUE",
                    "REVIEW_ONLY",
                    "2" * 64,
                    0.0,
                    stamp,
                ),
            )
            connection.execute(
                "INSERT INTO useful_work_evidence("
                "useful_work_id,work_unit_id,attempt_id,bas_decision_unit,downstream_consumer,"
                "delegation_preference_reason,input_documents,input_bytes,input_records,candidate_count,"
                "provider,model,task_format,route_identity,wall_seconds,compute_json,direct_baseline_seconds,"
                "orchestration_seconds,review_seconds,disposition,validated,reviewed,downstream_consumed,"
                "changed_project_artifact,consumed_artifact_identity,net_time_saved_seconds,duplicated_by_codex,"
                "accepted_useful_offload,evidence_sha256,recorded_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "0" * 64,
                    self.work_unit_id,
                    self.attempt_id,
                    "TEST_CANDIDATE_REVIEW_ACCOUNTING",
                    "DURABLE_REVIEW_QUEUE_ONLY",
                    "GOVERNED_PROVIDER_CANDIDATE_REVIEW",
                    1,
                    self.result_path.stat().st_size,
                    1,
                    1,
                    "cursor",
                    "gpt-5.3-codex",
                    "governed_cursor_repository_review_v1",
                    "c" * 64,
                    1.0,
                    "{}",
                    None,
                    0.1,
                    0.0,
                    "REVIEW_ONLY",
                    1,
                    1,
                    0,
                    0,
                    None,
                    0.0,
                    0,
                    0,
                    "0" * 64,
                    stamp,
                ),
            )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _registry(
        self, *, include: bool = True, include_candidate_contract: bool = False
    ) -> Path:
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
                    "candidate_contracts": (
                        [
                            {
                                "provider": "cursor",
                                "task_category": "governed_cursor_repository_review_v1",
                                "contract_version": "candidate-review-routing-v1",
                                "downstream_consumer": "CURSOR_CANDIDATE_CODE_REVIEW_QUEUE",
                                "authority": "CANDIDATE_REVIEW_QUEUE_ONLY",
                            }
                        ]
                        if include_candidate_contract
                        else []
                    ),
                    "entries": entries,
                }
            ),
            encoding="utf-8",
        )
        return registry

    def _consumer(
        self, *, include: bool = True, include_candidate_contract: bool = False
    ) -> DownstreamReviewConsumer:
        release = self.root / "releases" / ("4" * 40)
        release.mkdir(parents=True, exist_ok=True)
        (release / "RELEASE_MANIFEST.json").write_text(
            json.dumps({"build_commit": "4" * 40, "source_tree_sha256": "3" * 64}),
            encoding="utf-8",
        )
        return DownstreamReviewConsumer(
            self.state,
            DownstreamReviewConfig(
                registry_path=self._registry(
                    include=include,
                    include_candidate_contract=include_candidate_contract,
                ),
                evidence_root=self.evidence,
                releases_root=self.root / "releases",
            ),
        )

    def _prepare_valid_candidate_contract_result(self) -> None:
        payload = {
            "schema_version": 1,
            "artifact_type": "GOVERNED_PROVIDER_CANDIDATE_RESULT",
            "authority": "CANDIDATE_ONLY",
            "provider": "cursor",
            "work_unit_id": self.work_unit_id,
            "attempt_id": self.attempt_id,
            "disposition": "REVIEW_ONLY",
            "validation_errors": [],
            "result": {
                "authority": "CANDIDATE_ONLY",
                "canonical_writes": 0,
                "protected_decisions": 0,
                "findings": ["bounded discovery defect"],
            },
        }
        self.result_path.write_text(
            json.dumps(payload, sort_keys=True), encoding="utf-8"
        )
        self.result_sha256 = hashlib.sha256(self.result_path.read_bytes()).hexdigest()
        with self.state.transaction() as connection:
            connection.execute(
                "UPDATE execution_artifacts SET sha256=?,bytes=? WHERE attempt_id=?",
                (self.result_sha256, self.result_path.stat().st_size, self.attempt_id),
            )
        self.state.record_pre_routing_decision(
            decision={
                "work_unit_id": self.work_unit_id,
                "jira_identity": "BAT-560",
                "repository_identity": "repo:test",
                "source_commit": "5" * 40,
                "task_category": "governed_cursor_repository_review_v1",
                "effort_points": 5,
                "candidate_routes": ["cursor"],
                "selected_route": "cursor",
                "route_identity": "6" * 64,
                "budget_admission": "ADMITTED",
                "packet_identity": "7" * 64,
                "lease_identity": "8" * 64,
                "disposition": "ROUTED_TO_ASSISTIVE_PLANE",
                "reason_code": "TEST_CANDIDATE_ROUTE",
                "evidence_sha256": "9" * 64,
                "discovered_at": "2026-08-14T00:00:00Z",
            },
            now=datetime(2026, 8, 14, tzinfo=timezone.utc),
        )

    def test_exact_registered_result_is_consumed_without_time_savings_credit(
        self,
    ) -> None:
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
        self.assertEqual(
            1, self.state.provider_run_summary()["cursor"]["pending_downstream_review"]
        )

    def test_candidate_like_consumer_name_cannot_bypass_consumption_evidence(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "DOWNSTREAM_ACCEPTANCE_CONSUMPTION_EVIDENCE_INCOMPLETE"
        ):
            self.state.record_downstream_review_disposition(
                attempt_id=self.attempt_id,
                disposition="ACCEPTED",
                downstream_consumer="UNREGISTERED_CANDIDATE_REVIEW_QUEUE",
                reason="UNTRUSTED_CONSUMER_MUST_FAIL_CLOSED",
                consumed_artifact_identity="3" * 64,
                changed_project_artifact=False,
            )

    def test_matching_candidate_contract_routes_result_without_useful_credit(
        self,
    ) -> None:
        self._prepare_valid_candidate_contract_result()

        report = self._consumer(include=False, include_candidate_contract=True).process(
            now=datetime(2026, 8, 14, 1, tzinfo=timezone.utc)
        )

        self.assertEqual(1, report["processed"])
        self.assertEqual(0, report["deferred"])
        self.assertEqual([], report["failures"])
        self.assertTrue(report["applied"][0]["candidate_review_queue_only"])
        self.assertEqual("REVIEW_ONLY", report["applied"][0]["disposition"])
        self.assertFalse(report["applied"][0]["accepted_useful_offload_credit"])
        decision = json.loads(
            Path(report["applied"][0]["decision_path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            "CANDIDATE_REVIEW_QUEUE_ONLY_NO_FACTUAL_CANONICAL_OR_PROTECTED_ACCEPTANCE",
            decision["authority"],
        )
        self.assertEqual(0, decision["net_time_saved_seconds"])
        self.assertFalse(decision["changed_project_artifact"])
        self.assertEqual(
            0, self.state.provider_run_summary()["cursor"]["pending_downstream_review"]
        )
        self.assertEqual(
            0,
            self.state.provider_run_summary()["cursor"]["useful_work"][
                "accepted_useful_outputs"
            ],
        )
        self.assertEqual(
            0,
            self.state.provider_run_summary()["cursor"]["useful_work"][
                "downstream_consumed_outputs"
            ],
        )
        self.assertEqual(
            1,
            self.state.provider_run_summary()["cursor"]["useful_work"][
                "candidate_review_queue_outputs"
            ],
        )
        self.assertEqual(
            {"ACCEPTED": 1},
            self.state.status()["downstream_review_dispositions"],
        )
        self.assertEqual(1, len(self.state.cursor_review_candidates(limit=8)))
        with closing(self.state.connect()) as connection:
            disposition = connection.execute(
                "SELECT changed_project_artifact,net_time_saved_seconds "
                "FROM downstream_review_dispositions WHERE attempt_id=?",
                (self.attempt_id,),
            ).fetchone()
        self.assertEqual(0, disposition["changed_project_artifact"])
        self.assertEqual(0.0, disposition["net_time_saved_seconds"])

        # Historical pre-correction candidate-queue rows claimed a changed artifact.
        # Even if such a row also claimed positive savings, its exact queue identity
        # must keep it out of consumed/useful/savings credit while preserving the
        # candidate needed by the replenishing Cursor implementation producer.
        with self.state.transaction() as connection:
            connection.execute(
                "UPDATE downstream_review_dispositions SET "
                "changed_project_artifact=1,net_time_saved_seconds=45.0 "
                "WHERE attempt_id=?",
                (self.attempt_id,),
            )
        useful = self.state.provider_run_summary()["cursor"]["useful_work"]
        self.assertEqual(0, useful["downstream_consumed_outputs"])
        self.assertEqual(1, useful["candidate_review_queue_outputs"])
        self.assertEqual(0, useful["accepted_useful_outputs"])
        self.assertEqual(0.0, useful["measured_net_time_saved_seconds"])
        watchdog = ReadOnlyWatchdog(self.state.database).inspect(
            now=datetime(2026, 8, 14, 1, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(0, watchdog["useful_work_summary"]["downstream_consumed_output"])
        self.assertEqual(1, watchdog["useful_work_summary"]["candidate_review_queue_output"])
        self.assertEqual(0, watchdog["useful_work_summary"]["accepted_useful_offload"])
        self.assertEqual(
            0.0,
            watchdog["useful_work_summary"]["measured_net_time_saved_seconds"],
        )
        self.assertNotIn(
            "USEFUL_OFFLOAD_CLAIM_EXCEEDS_CONSUMPTION_EVIDENCE",
            watchdog["operational_findings"],
        )

        # The exclusion is scoped to an explicitly nonauthoritative candidate
        # queue.  The same zero-change disposition against a real consumer is
        # still an invalid useful-work claim and must fail the independent audit.
        with self.state.transaction() as connection:
            connection.execute(
                "UPDATE downstream_review_dispositions SET "
                "downstream_consumer='REAL_DOWNSTREAM_TEST_CONSUMER',"
                "changed_project_artifact=0,net_time_saved_seconds=0 "
                "WHERE attempt_id=?",
                (self.attempt_id,),
            )
        invalid_watchdog = ReadOnlyWatchdog(self.state.database).inspect(
            now=datetime(2026, 8, 14, 1, 2, tzinfo=timezone.utc)
        )
        self.assertIn(
            "USEFUL_OFFLOAD_CLAIM_EXCEEDS_CONSUMPTION_EVIDENCE",
            invalid_watchdog["operational_findings"],
        )

    def test_invalid_candidate_contract_result_is_isolated_and_remains_pending(
        self,
    ) -> None:
        self._prepare_valid_candidate_contract_result()
        payload = json.loads(self.result_path.read_text(encoding="utf-8"))
        payload["result"]["canonical_writes"] = 1
        self.result_path.write_text(
            json.dumps(payload, sort_keys=True), encoding="utf-8"
        )
        self.result_sha256 = hashlib.sha256(self.result_path.read_bytes()).hexdigest()
        with self.state.transaction() as connection:
            connection.execute(
                "UPDATE execution_artifacts SET sha256=?,bytes=? WHERE attempt_id=?",
                (self.result_sha256, self.result_path.stat().st_size, self.attempt_id),
            )

        report = self._consumer(include=False, include_candidate_contract=True).process(
            now=datetime(2026, 8, 14, 1, tzinfo=timezone.utc)
        )

        self.assertEqual(0, report["processed"])
        self.assertEqual(1, report["deferred"])
        self.assertEqual(1, len(report["failures"]))
        self.assertIn(
            "DOWNSTREAM_CANDIDATE_RESULT_AUTHORITY_INVALID",
            report["failures"][0]["finding"],
        )
        self.assertEqual(
            1, self.state.provider_run_summary()["cursor"]["pending_downstream_review"]
        )

    def test_tampered_result_fails_closed_without_disposition(self) -> None:
        consumer = self._consumer()
        self.result_path.write_text("tampered", encoding="utf-8")

        with self.assertRaisesRegex(
            RuntimeError, "DOWNSTREAM_REVIEW_RESULT_HASH_MISMATCH"
        ):
            consumer.process()

        self.assertEqual(
            1, self.state.provider_run_summary()["cursor"]["pending_downstream_review"]
        )

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

        self.assertEqual(
            1, self.state.provider_run_summary()["cursor"]["pending_downstream_review"]
        )


if __name__ == "__main__":
    unittest.main()
