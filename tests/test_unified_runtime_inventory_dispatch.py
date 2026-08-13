from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from aggie_analytics.assistive_plane.contracts import canonical_json_bytes, sha256_value
from aggie_analytics.assistive_plane.controller_state import ControllerState
from aggie_analytics.assistive_plane.cpu_worker_backend import CpuWorkerClient, execute_cpu_request
from aggie_analytics.assistive_plane.inventory_runtime import (
    CPU_LINE_HASH_SCHEMA_SHA256,
    CPU_LINE_HASH_TASK_FORMAT,
    CPU_TEXT_DEDUP_SCHEMA_SHA256,
    CPU_TEXT_DEDUP_TASK_FORMAT,
    OPENROUTER_TASK_FORMAT,
    RuntimeInventoryConfig,
    RuntimeInventoryRefresher,
)
from aggie_analytics.assistive_plane.orchestration import CAMPAIGN_OWNER, validate_work_unit_roles, ReadyWorkUnit
from aggie_analytics.assistive_plane.provider_adapters import ProviderAdapterResult
from aggie_analytics.assistive_plane.scheduler_runtime import InventoryScheduler, SchedulerConfig
from aggie_analytics.assistive_plane.watchdog import ReadOnlyWatchdog


class UnifiedRuntimeInventoryDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.current = self.root / "inventory/current/inventory.json"
        self.manifests = self.root / "manifests"
        (self.manifests / "acquisition/a").mkdir(parents=True)
        (self.manifests / "acquisition/a/run.json").write_text(
            json.dumps({"season": 2024, "games": 10}), encoding="utf-8"
        )
        (self.manifests / "normalization/b").mkdir(parents=True)
        (self.manifests / "normalization/b/progress.json").write_text(
            json.dumps({"season": 2025, "normalized": 8}), encoding="utf-8"
        )
        self.state = ControllerState(self.root / "runtime/state/orchestrator.sqlite3")
        self.state.initialize()
        self.now = datetime(2026, 8, 13, 2, 0, tzinfo=timezone.utc)
        seed_unit = {
            "work_unit_id": "STATIC-CODEX-UNIT",
            "jira_unit": "BAT-560",
            "task_format": "controller_implementation",
            "schema_sha256": "d" * 64,
            "authority": "CODEX_FINAL_IMPLEMENTATION",
            "source_hashes": ["e" * 64],
            "dependencies": [],
            "pre_routing_effort_points": 1,
            "scope": "Static controller implementation scope",
        }
        seed_unit["identity"] = hashlib.sha256(
            canonical_json_bytes({key: value for key, value in seed_unit.items() if key != "identity"})
        ).hexdigest()
        self.seed_unit_identity = seed_unit["identity"]
        seed_role_validation = validate_work_unit_roles(
            [ReadyWorkUnit(**{key: value for key, value in seed_unit.items() if key != "identity"})],
            {"STATIC-CODEX-UNIT": CAMPAIGN_OWNER},
        )
        base = {
            "schema_version": 1,
            "generated_at": self.now.isoformat().replace("+00:00", "Z"),
            "canonical_or_protected_authority": False,
            "git": {
                "head": "a" * 40,
                "origin_main": "a" * 40,
                "status_porcelain_sha256": hashlib.sha256(b"").hexdigest(),
            },
            "external_evidence": {
                "cpu_worker": {
                    "qualified": True,
                    "qualifications": [
                        {
                            "tasks": ["CANONICAL_JSON", "EXACT_TEXT_DEDUP", "LINE_HASH_MANIFEST"],
                            "evidence_sha256": "b" * 64,
                            "readiness_evidence_sha256": "c" * 64,
                        }
                    ],
                }
            },
            "work_units": [seed_unit],
            "work_unit_roles": {"STATIC-CODEX-UNIT": CAMPAIGN_OWNER},
            "work_unit_role_validation": seed_role_validation,
            "route_decisions": [
                {
                    "work_unit_id": "STATIC-CODEX-UNIT",
                    "work_unit_identity": seed_unit["identity"],
                    "disposition": "CODEX_DETERMINISTIC",
                    "provider": "codex_deterministic",
                    "model": None,
                    "reason": "static seed",
                    "decided_at": self.now.isoformat().replace("+00:00", "Z"),
                }
            ],
            "validation": {"inventory_identity": "f" * 64},
        }
        self.current.parent.mkdir(parents=True)
        self.current.write_bytes(canonical_json_bytes(base) + b"\n")
        self.refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
            ),
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_refresh_discovers_granular_units_and_reuses_immutable_snapshot(self) -> None:
        first = self.refresher.refresh(now=self.now)
        self.assertEqual(2, first["granular_units"])
        pointer = json.loads(self.current.read_text(encoding="utf-8"))
        self.assertEqual("UNIFIED_ASSISTIVE_INVENTORY_POINTER", pointer["artifact_type"])
        snapshot = json.loads(Path(pointer["snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual(3, snapshot["validation"]["work_unit_count"])
        self.assertEqual(
            {"CODEX_DETERMINISTIC": 1, "REMOTE_CPU_WORKER": 2},
            snapshot["validation"]["counts_by_disposition"],
        )
        self.assertEqual(self.seed_unit_identity, snapshot["work_units"][0]["identity"])
        self.assertEqual(
            {"ATOMIC_EXECUTABLE": 2, "CAMPAIGN_OWNER": 1, "QUALIFICATION_RECORD": 0},
            snapshot["work_unit_role_validation"]["counts_by_role"],
        )

        second = self.refresher.refresh(now=self.now + timedelta(minutes=3))
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        refreshed_pointer = json.loads(self.current.read_text(encoding="utf-8"))
        self.assertNotEqual(pointer["refreshed_at"], refreshed_pointer["refreshed_at"])

    def test_refresh_replaces_stale_seed_git_with_exact_deployed_release_evidence(self) -> None:
        build_commit = "9" * 40
        release = self.root / "releases" / build_commit
        release.mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "build_commit": build_commit,
            "source_tree_sha256": "8" * 64,
            "files": {},
        }
        (release / "RELEASE_MANIFEST.json").write_bytes(canonical_json_bytes(manifest) + b"\n")
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                release_root=release,
                build_commit=build_commit,
            ),
        )
        report = refresher.refresh(now=self.now)
        snapshot = json.loads(Path(report["snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual(build_commit, snapshot["git"]["deployed_head"])
        self.assertEqual(build_commit, snapshot["git"]["merged_main_identity_at_release_build"])
        self.assertEqual(hashlib.sha256(b"").hexdigest(), snapshot["git"]["status_porcelain_sha256"])
        self.assertEqual(
            "IMMUTABLE_RELEASE_TREE_NO_WORKTREE_MUTATION_SURFACE",
            snapshot["git"]["status_evidence"],
        )
        self.assertNotIn("origin_main", snapshot["git"])
        self.assertEqual(build_commit, snapshot["deployed_release"]["build_commit"])
        self.assertEqual("8" * 64, snapshot["deployed_release"]["source_tree_sha256"])

    def test_cpu_qualification_requires_exact_semantic_evidence_contract(self) -> None:
        self.assertFalse(
            self.refresher._cpu_qualified(
                {"external_evidence": {"cpu_worker": {"qualified": True, "qualification_sha256": "b" * 64}}}
            )
        )
        self.assertFalse(
            self.refresher._cpu_qualified(
                {
                    "external_evidence": {
                        "cpu_worker": {
                            "qualified": True,
                            "qualifications": [
                                {
                                    "tasks": ["EXACT_TEXT_DEDUP"],
                                    "evidence_sha256": "b" * 64,
                                    "readiness_evidence_sha256": "c" * 64,
                                }
                            ],
                        }
                    }
                }
            )
        )
        self.assertFalse(
            self.refresher._cpu_qualified(
                {
                    "external_evidence": {
                        "cpu_worker": {
                            "qualified": True,
                            "qualifications": [
                                {
                                    "tasks": ["CANONICAL_JSON"],
                                    "evidence_sha256": "not-a-hash",
                                    "readiness_evidence_sha256": "c" * 64,
                                }
                            ],
                        }
                    }
                }
            )
        )

    def test_persistent_scheduler_dispatches_real_packets_and_closes_lifecycle(self) -> None:
        self.refresher.refresh(now=self.now)
        key_path = self.root / "secret.bin"
        key_path.write_bytes(b"k" * 32)

        def local_submit(client: CpuWorkerClient, job: object, request_payload: dict[str, object] | None = None):
            assert request_payload is not None
            response = execute_cpu_request(
                request_payload,
                client.signing_key,
                now=self.now + timedelta(seconds=1),
            )
            data = canonical_json_bytes({"request": request_payload, "response": response}) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            destination = client.storage_root / "results" / digest[:2] / f"{digest}.json"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            return response, destination

        scheduler = InventoryScheduler(
            self.state,
            SchedulerConfig(
                inventory_current_path=self.current,
                evidence_root=self.root / "runtime/evidence",
                inventory_max_age_seconds=300,
                cycle_interval_seconds=3600,
                owner_id="controller-test",
                cpu_worker_endpoint="https://comfy-v4-cpu-01.tail9b05ab.ts.net",
                cpu_worker_storage_root=self.root / "cpu_worker",
                cpu_worker_signing_key_path=key_path,
                max_dispatch_per_cycle=3,
            ),
        )
        with patch.object(CpuWorkerClient, "submit", local_submit):
            report = scheduler.evaluate(now=self.now)
        self.assertEqual(2, report["dispatched_units"])
        self.assertEqual(2, report["provider_calls"])
        self.assertEqual("INVENTORY_SCHEDULER_CONTROLLER_ROUTED_DISPATCH_ACTIVE", report["dispatch_engine_state"])
        status = self.state.status()
        self.assertEqual(2, status["dispatch_attempts"])
        self.assertEqual(2, status["closed_dispatch_attempts"])
        self.assertEqual({"REVIEW_ONLY": 2}, status["review_dispositions"])
        self.assertEqual(2, status["scheduler_dispatched_units"])
        with closing(self.state.connect()) as connection:
            self.assertEqual(2, connection.execute("SELECT COUNT(*) FROM route_readiness_observations").fetchone()[0])
            self.assertEqual(2, connection.execute("SELECT COUNT(*) FROM reconciliation_records").fetchone()[0])
            self.assertEqual(2, connection.execute("SELECT COUNT(*) FROM execution_artifacts WHERE artifact_type='PROVIDER_REQUEST_ENVELOPE'").fetchone()[0])

        refreshed = self.refresher.refresh(now=self.now + timedelta(seconds=1))
        no_cycle = scheduler.evaluate(now=self.now + timedelta(seconds=2))
        self.assertEqual(0, no_cycle["dispatched_units"])
        self.state.acquire_leader("watchdog-owner", "d" * 40, now=self.now, ttl_seconds=120)
        release_status = self.state.status()
        self.assertEqual(2, release_status["scheduler_provider_calls"])
        self.assertEqual(2, release_status["release_scheduler_dispatched_units"])
        self.assertEqual(2, release_status["release_scheduler_provider_calls"])
        watchdog = ReadOnlyWatchdog(
            self.state.database,
            inventory_path=self.current,
            scheduler_report_path=self.root / "runtime/evidence/current/scheduler-evaluation.json",
            expected_build_commit="d" * 40,
        )
        operational = watchdog.inspect(now=self.now + timedelta(seconds=2))
        self.assertEqual("PASS", operational["structural_result"])
        self.assertEqual("PASS", operational["operational_result"])
        self.assertEqual(2, operational["scheduler_dispatched_units"])
        self.assertEqual(2, operational["scheduler_provider_calls"])
        self.assertEqual(0, operational["scheduler_cached_or_local_reuse_dispatches"])
        self.assertEqual(0, operational["latest_scheduler_evaluation_dispatched_units"])
        self.assertNotIn("ZERO_DISPATCH_WHILE_ADMITTED_WORK_EXISTS", operational["findings"])

        with closing(self.state.connect()) as connection:
            run = connection.execute("SELECT provider_run_id, resource_json FROM provider_runs LIMIT 1").fetchone()
            resource = json.loads(run["resource_json"])
            resource["provider_calls"] = 0
            resource["cached"] = True
            connection.execute(
                "UPDATE provider_runs SET resource_json=? WHERE provider_run_id=?",
                (json.dumps(resource, sort_keys=True), run["provider_run_id"]),
            )
            connection.commit()
        cached_cycle = dict(no_cycle)
        cached_cycle["dispatched_units"] = 1
        cached_cycle["provider_calls"] = 0
        cached_cycle["dispatched"] = [
            {"work_unit_id": "CACHE-HIT", "provider_call_attempted": False}
        ]
        (self.root / "runtime/evidence/current/scheduler-evaluation.json").write_bytes(
            canonical_json_bytes(cached_cycle) + b"\n"
        )
        cached_operational = watchdog.inspect(now=self.now + timedelta(seconds=3))
        self.assertEqual("PASS", cached_operational["operational_result"])
        self.assertEqual(2, cached_operational["scheduler_dispatched_units"])
        self.assertEqual(1, cached_operational["scheduler_provider_calls"])
        self.assertEqual(1, cached_operational["scheduler_cached_or_local_reuse_dispatches"])
        self.assertEqual(
            1,
            cached_operational[
                "latest_scheduler_evaluation_cached_or_local_reuse_dispatches"
            ],
        )
        self.assertNotIn("RELEASE_PROVIDER_CALL_DISPATCH_MISMATCH", cached_operational["findings"])
        self.assertNotIn("SCHEDULER_PROVIDER_CALL_DISPATCH_MISMATCH", cached_operational["findings"])

        snapshot = json.loads(Path(refreshed["snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual(
            {"CODEX_DETERMINISTIC": 1, "COMPLETED": 2},
            snapshot["validation"]["counts_by_disposition"],
        )

    def test_transient_failure_is_durably_retried_without_duplicate_attempt_identity(self) -> None:
        self.refresher.refresh(now=self.now)
        key_path = self.root / "retry-secret.bin"
        key_path.write_bytes(b"r" * 32)
        calls = 0

        def flaky_submit(client: CpuWorkerClient, job: object, request_payload: dict[str, object] | None = None):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("bounded transient transport failure")
            assert request_payload is not None
            issued = datetime.fromisoformat(str(request_payload["issued_at_utc"]).replace("Z", "+00:00"))
            response = execute_cpu_request(request_payload, client.signing_key, now=issued + timedelta(seconds=1))
            data = canonical_json_bytes({"request": request_payload, "response": response}) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            destination = client.storage_root / "results" / digest[:2] / f"{digest}.json"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            return response, destination

        scheduler = InventoryScheduler(
            self.state,
            SchedulerConfig(
                inventory_current_path=self.current,
                evidence_root=self.root / "runtime/evidence",
                inventory_max_age_seconds=300,
                cycle_interval_seconds=3600,
                owner_id="controller-retry-test",
                cpu_worker_endpoint="https://comfy-v4-cpu-01.tail9b05ab.ts.net",
                cpu_worker_storage_root=self.root / "cpu_worker",
                cpu_worker_signing_key_path=key_path,
                max_dispatch_per_cycle=3,
            ),
        )
        with patch.object(CpuWorkerClient, "submit", flaky_submit):
            first = scheduler.evaluate(now=self.now)
            self.assertEqual(2, first["provider_calls"])
            self.assertEqual(1, len(first["failures"]))
            self.refresher.refresh(now=self.now + timedelta(seconds=61))
            second = scheduler.evaluate(now=self.now + timedelta(seconds=61))
        self.assertEqual(1, second["provider_calls"])
        self.assertEqual(3, self.state.status()["dispatch_attempts"])
        self.assertEqual(2, self.state.status()["closed_dispatch_attempts"])
        attempt_ids = []
        with closing(self.state.connect()) as connection:
            attempt_ids = [row[0] for row in connection.execute("SELECT attempt_id FROM dispatch_attempts")]
        self.assertEqual(3, len(set(attempt_ids)))


    def test_exact_bge_readiness_cannot_be_widened_by_narrative_status(self) -> None:
        packet = {
            "provider": "ollama_local", "model": "bge-m3:latest", "model_digest": "7" * 64,
            "task_format": "embedding_dedup_semantic_candidate_retrieval", "policy_version": "policy-v1",
            "prompt_version": "prompt-v1", "route_schema_version": "1", "schema_sha256": "3" * 64,
        }
        route = {
            "provider": "ollama_local", "resolved_model": "bge-m3:latest", "model_digest": "7" * 64,
            "task_format": "embedding_dedup_semantic_candidate_retrieval", "policy_version": "policy-v1",
            "prompt_version": "prompt-v1", "schema_version": "1", "schema_sha256": "3" * 64,
            "evidence_supported_state": "NOT_READY", "evidence_verified": True,
            "evidence_sha256": "8" * 64, "human_status": "READY",
        }
        snapshot = {"external_evidence": {"local_qwen": {"routes": [route]}}}
        self.assertIsNone(RuntimeInventoryRefresher._provider_readiness(snapshot, packet))
        route["evidence_supported_state"] = "READY"
        route["model_digest"] = "9" * 64
        self.assertIsNone(RuntimeInventoryRefresher._provider_readiness(snapshot, packet))
        route["model_digest"] = "7" * 64
        self.assertEqual("8" * 64, RuntimeInventoryRefresher._provider_readiness(snapshot, packet))

    def test_invalid_provider_packet_does_not_block_cpu_manifest_discovery(self) -> None:
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        (provider_root / "invalid.json").write_text('{"schema_version":99}', encoding="utf-8")
        refresher = RuntimeInventoryRefresher(self.state, RuntimeInventoryConfig(
            current_path=self.current, snapshot_root=self.root / "inventory/runtime",
            packet_root=self.root / "orchestrator", manifests_root=self.manifests,
            provider_work_root=provider_root,
        ))
        report = refresher.refresh(now=self.now)
        self.assertEqual(2, report["granular_units"])
        snapshot = json.loads(Path(report["snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual(1, len(snapshot["provider_work_findings"]))
        self.assertEqual(
            "PROVIDER_WORK_DEFERRED_CPU_AND_DETERMINISTIC_DISCOVERY_CONTINUES",
            snapshot["provider_work_findings"][0]["disposition"],
        )

    def test_selected_cpu_manifest_packet_requires_exact_qualification_and_is_routable(self) -> None:
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        packet = {
            "schema_version": 1,
            "provider": "remote_cpu_worker",
            "task": "CANONICAL_JSON",
            "task_format": "cpu_worker_canonical_manifest_v1",
            "jira_unit": "BAT-563",
            "schema_sha256": hashlib.sha256(
                b"cpu_worker_canonical_manifest_v1:value:any-json;candidate-only;exact-local-replay"
            ).hexdigest(),
            "source_hashes": ["4" * 64],
            "dependencies": [],
            "pre_routing_effort_points": 1,
            "scope": "Exact canonicalization and provenance QA for a selected historical manifest",
            "payload": {"value": {"season": 2021, "teams": 653}},
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        data = canonical_json_bytes(packet) + b"\n"
        (provider_root / "cpu.json").write_bytes(data)
        current_payload = json.loads(self.current.read_text(encoding="utf-8"))
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=provider_root,
            ),
        )
        discovered = refresher._discover_provider_work(current_payload, self.now)
        self.assertEqual(1, len(discovered))
        unit, decision, reference = discovered[0]
        self.assertTrue(unit.work_unit_id.startswith("AUTO-CPU-MANIFEST-"))
        self.assertEqual("REMOTE_CPU_WORKER", decision.disposition.value)
        self.assertEqual("remote_cpu_worker", decision.provider)
        self.assertEqual("c" * 64, reference["readiness_evidence_sha256"])

        current_payload["external_evidence"]["cpu_worker"]["qualified"] = False
        with self.assertRaisesRegex(RuntimeError, "EXACT_ROUTE_NOT_READY"):
            refresher._discover_provider_work(current_payload, self.now)

    def test_selected_cpu_text_routes_require_exact_task_format_schema_and_qualification(self) -> None:
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        packets = (
            {
                "schema_version": 1,
                "provider": "remote_cpu_worker",
                "task": "LINE_HASH_MANIFEST",
                "task_format": CPU_LINE_HASH_TASK_FORMAT,
                "jira_unit": "BAT-563",
                "schema_sha256": CPU_LINE_HASH_SCHEMA_SHA256,
                "source_hashes": ["5" * 64],
                "dependencies": [],
                "pre_routing_effort_points": 1,
                "scope": "Line-level integrity QA for a selected historical manifest",
                "payload": {"lines": ["season=2022", "status=complete"]},
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            },
            {
                "schema_version": 1,
                "provider": "remote_cpu_worker",
                "task": "EXACT_TEXT_DEDUP",
                "task_format": CPU_TEXT_DEDUP_TASK_FORMAT,
                "jira_unit": "BAT-563",
                "schema_sha256": CPU_TEXT_DEDUP_SCHEMA_SHA256,
                "source_hashes": ["6" * 64],
                "dependencies": [],
                "pre_routing_effort_points": 1,
                "scope": "Exact normalized-string candidate deduplication for historical evidence",
                "payload": {"records": [{"id": "/team/0", "text": "Texas A&M"}]},
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            },
        )
        for index, packet in enumerate(packets):
            (provider_root / f"cpu-text-{index}.json").write_bytes(canonical_json_bytes(packet) + b"\n")
        current_payload = json.loads(self.current.read_text(encoding="utf-8"))
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=provider_root,
            ),
        )

        discovered = refresher._discover_provider_work(current_payload, self.now)
        self.assertEqual(2, len(discovered))
        self.assertEqual(
            {"AUTO-CPU-LINE-HASH-", "AUTO-CPU-TEXT-DEDUP-"},
            {entry[0].work_unit_id.rsplit("-", 1)[0] + "-" for entry in discovered},
        )
        self.assertTrue(all(entry[2]["readiness_evidence_sha256"] == "c" * 64 for entry in discovered))

        current_payload["external_evidence"]["cpu_worker"]["qualifications"][0]["tasks"] = [
            "CANONICAL_JSON",
            "LINE_HASH_MANIFEST",
        ]
        with self.assertRaisesRegex(RuntimeError, "EXACT_ROUTE_NOT_READY"):
            refresher._discover_provider_work(current_payload, self.now)

        current_payload["external_evidence"]["cpu_worker"]["qualifications"][0]["tasks"].append(
            "EXACT_TEXT_DEDUP"
        )
        packets[1]["task_format"] = CPU_LINE_HASH_TASK_FORMAT
        (provider_root / "cpu-text-1.json").write_bytes(canonical_json_bytes(packets[1]) + b"\n")
        with self.assertRaisesRegex(ValueError, "CPU_PROVIDER_PACKET_INVALID"):
            refresher._discover_provider_work(current_payload, self.now)

    def test_closed_provider_packets_do_not_exhaust_active_discovery_bound(self) -> None:
        current_payload = json.loads(self.current.read_text(encoding="utf-8"))
        current_payload["external_evidence"]["openai"] = {
            "present": True,
            "manifest_sha256": "1" * 64,
        }
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        work_unit_ids: list[str] = []
        for index in range(65):
            packet = {
                "schema_version": 1,
                "provider": "openai_direct",
                "task_format": "governed_openai_candidate_v1",
                "jira_unit": "POST-SUBTASK-168",
                "schema_sha256": "5" * 64,
                "source_hashes": [f"{index:064x}"],
                "job": {"model": "gpt-5-nano"},
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            data = canonical_json_bytes(packet) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            (provider_root / f"{index:02d}.json").write_bytes(data)
            work_unit_ids.append("AUTO-OAI-" + digest[:20])
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=provider_root,
            ),
        )
        closed = {work_unit_id: "CLOSED" for work_unit_id in work_unit_ids[:-1]}
        with patch.object(self.state, "work_unit_states", return_value=closed):
            discovered = refresher._discover_provider_work(current_payload, self.now)
        self.assertEqual(1, len(discovered))
        self.assertEqual(work_unit_ids[-1], discovered[0][0].work_unit_id)

        with patch.object(self.state, "work_unit_states", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "PROVIDER_WORK_ACTIVE_BOUND_EXCEEDED"):
                refresher._discover_provider_work(current_payload, self.now)

    def test_granular_bge_and_openai_packets_traverse_durable_candidate_lifecycle(self) -> None:
        current_payload = json.loads(self.current.read_text(encoding="utf-8"))
        current_payload["external_evidence"].update({
            "openai": {"present": True, "manifest_sha256": "1" * 64},
            "local_qwen": {"routes": [{
                "provider": "ollama_local", "resolved_model": "bge-m3:latest",
                "model_digest": "7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab",
                "task_format": "embedding_dedup_semantic_candidate_retrieval",
                "policy_version": "unified-assistive-execution-plane-v2-operational-correction",
                "prompt_version": "embedding-shadow-v1", "schema_version": "1",
                "schema_sha256": "fd5ed573e9990a40674b28032a2b4fb63659c62423479c554188149826ea362c",
                "evidence_supported_state": "READY", "evidence_verified": True,
                "evidence_sha256": "2" * 64,
            }]},
        })
        self.current.write_bytes(canonical_json_bytes(current_payload) + b"\n")
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        bge_packet = {
            "schema_version": 1, "provider": "ollama_local",
            "task_format": "embedding_dedup_semantic_candidate_retrieval", "model": "bge-m3:latest",
            "model_digest": "7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab",
            "policy_version": "unified-assistive-execution-plane-v2-operational-correction",
            "prompt_version": "embedding-shadow-v1", "route_schema_version": "1",
            "jira_unit": "BAT-562", "schema_sha256": "fd5ed573e9990a40674b28032a2b4fb63659c62423479c554188149826ea362c",
            "source_hashes": ["4" * 64],
            "query": "Texas A&M", "candidates": [{"candidate_id": "a", "text": "Texas A&M Aggies"}],
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        openai_packet = {
            "schema_version": 1, "provider": "openai_direct", "task_format": "governed_openai_candidate_v1",
            "jira_unit": "POST-SUBTASK-168", "schema_sha256": "5" * 64, "source_hashes": ["6" * 64],
            "job": {"model": "gpt-5-nano"},
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        (provider_root / "bge.json").write_bytes(canonical_json_bytes(bge_packet) + b"\n")
        (provider_root / "openai.json").write_bytes(canonical_json_bytes(openai_packet) + b"\n")
        refresher = RuntimeInventoryRefresher(self.state, RuntimeInventoryConfig(
            current_path=self.current, snapshot_root=self.root / "inventory/runtime",
            packet_root=self.root / "orchestrator", manifests_root=self.manifests,
            provider_work_root=provider_root,
        ))
        self.assertEqual(4, refresher.refresh(now=self.now)["granular_units"])

        class FakeAdapter:
            def __init__(self, provider: str, cost: str) -> None:
                self.provider, self.cost = provider, cost

            def run(self, _packet: dict[str, object]) -> ProviderAdapterResult:
                return ProviderAdapterResult(
                    remote_identity=f"{self.provider}-run",
                    result={"authority": "CANDIDATE_ONLY", "canonical_writes": 0,
                            "protected_decisions": 0, "provider": self.provider},
                    disposition="REVIEW_ONLY", validation_errors=(), actual_cost_usd=self.cost,
                    resource={"tokens": 17},
                )

        scheduler = InventoryScheduler(self.state, SchedulerConfig(
            inventory_current_path=self.current, evidence_root=self.root / "runtime/evidence",
            inventory_max_age_seconds=300, cycle_interval_seconds=3600,
            owner_id="provider-controller-test", max_dispatch_per_cycle=2,
        ), adapters={
            "ollama_local": FakeAdapter("ollama_local", "0.000000"),
            "openai_direct": FakeAdapter("openai_direct", "0.000321"),
        })
        report = scheduler.evaluate(now=self.now)
        self.assertEqual(2, report["dispatched_units"])
        self.assertEqual(2, report["provider_calls"])
        self.assertEqual({"ollama_local", "openai_direct"}, {item["provider"] for item in report["dispatched"]})
        with closing(self.state.connect()) as connection:
            rows = connection.execute(
                "SELECT provider,status,resource_json FROM provider_runs WHERE provider IN ('ollama_local','openai_direct')"
            ).fetchall()
            self.assertEqual(2, len(rows))
            self.assertTrue(all(row["status"] == "SETTLED" for row in rows))
            openai = next(row for row in rows if row["provider"] == "openai_direct")
            self.assertEqual("0.000321", json.loads(openai["resource_json"])["actual_cost_usd_exact"])

    def test_openrouter_provider_packet_requires_exact_identity_and_positive_budget_evidence(self) -> None:
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        source_hashes = ["4" * 64, "5" * 64]
        packet = {
            "schema_version": 1,
            "provider": "openrouter",
            "task_format": OPENROUTER_TASK_FORMAT,
            "task_id": "independent_review",
            "jira_unit": "POST-SUBTASK-199",
            "schema_sha256": "6" * 64,
            "request_schema_version": "v1",
            "provider_policy_version": "openrouter-assistive-development-plane-v2-paid-authorization",
            "model": "qwen/qwen3-coder-next",
            "reasoning_effort": "none",
            "max_output_tokens": 256,
            "base_commit": "a" * 40,
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            "source_hashes": source_hashes,
            "prompt_version": "v1",
            "evidence_excerpts": ["bounded evidence excerpt"],
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
            "source_sha256": sha256_value(tuple(source_hashes)),
        }
        (provider_root / "openrouter.json").write_bytes(canonical_json_bytes(packet) + b"\n")
        current_payload = json.loads(self.current.read_text(encoding="utf-8"))
        current_payload["external_evidence"]["openrouter"] = {
            "routes": [
                {
                    "provider": "openrouter",
                    "task_format": OPENROUTER_TASK_FORMAT,
                    "task_id": "independent_review",
                    "schema_sha256": "6" * 64,
                    "request_schema_version": "v1",
                    "provider_policy_version": "openrouter-assistive-development-plane-v2-paid-authorization",
                    "model": "qwen/qwen3-coder-next",
                    "reasoning_effort": "none",
                    "readiness_supported_state": "READY",
                    "evidence_verified": True,
                    "readiness_evidence_sha256": "7" * 64,
                    "route_evidence_sha256": "9" * 64,
                    "budget_evidence_sha256": "8" * 64,
                    "budget_released_stage_usd": "5.00",
                    "budget_remaining_usd": "1.23",
                }
            ]
        }
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=provider_root,
            ),
        )
        discovered = refresher._discover_provider_work(current_payload, self.now)
        self.assertEqual(1, len(discovered))
        unit, decision, reference = discovered[0]
        self.assertEqual("OPENROUTER", decision.disposition.value)
        self.assertTrue(unit.work_unit_id.startswith("AUTO-OR-"))
        self.assertTrue(len(reference["readiness_evidence_sha256"]) == 64)

        current_payload["git"] = {
            "deployed_head": "a" * 40,
            "merged_main_identity_at_release_build": "a" * 40,
            "status_porcelain_sha256": hashlib.sha256(b"").hexdigest(),
            "status_evidence": "IMMUTABLE_RELEASE_TREE_NO_WORKTREE_MUTATION_SURFACE",
        }
        current_payload["deployed_release"] = {"build_commit": "a" * 40}
        discovered_from_runtime_snapshot = refresher._discover_provider_work(current_payload, self.now)
        self.assertEqual(1, len(discovered_from_runtime_snapshot))

        current_payload["deployed_release"]["build_commit"] = "b" * 40
        with self.assertRaisesRegex(RuntimeError, "RELEASE_IDENTITY_CONFLICT"):
            refresher._discover_provider_work(current_payload, self.now)
        current_payload["deployed_release"]["build_commit"] = "a" * 40

        current_payload["external_evidence"]["openrouter"]["routes"][0]["budget_remaining_usd"] = "0.00"
        with self.assertRaisesRegex(RuntimeError, "EXACT_ROUTE_NOT_READY"):
            refresher._discover_provider_work(current_payload, self.now)

        packet["base_commit"] = "b" * 40
        packet["identity_hashes"]["source_sha256"] = sha256_value(tuple(packet["source_hashes"]))
        (provider_root / "openrouter.json").write_bytes(canonical_json_bytes(packet) + b"\n")
        with self.assertRaisesRegex(ValueError, "OPENROUTER_PACKET_INVALID"):
            refresher._discover_provider_work(current_payload, self.now)

        packet["base_commit"] = "a" * 40
        packet["identity_hashes"]["source_sha256"] = "9" * 64
        (provider_root / "openrouter.json").write_bytes(canonical_json_bytes(packet) + b"\n")
        current_payload["external_evidence"]["openrouter"]["routes"][0]["budget_remaining_usd"] = "1.23"
        with self.assertRaisesRegex(ValueError, "IDENTITY_HASH_MISMATCH"):
            refresher._discover_provider_work(current_payload, self.now)

    def test_openrouter_scheduler_restart_idempotency_and_accounting_use_fake_adapter(self) -> None:
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        packet = {
            "schema_version": 1,
            "provider": "openrouter",
            "task_format": OPENROUTER_TASK_FORMAT,
            "task_id": "independent_review",
            "jira_unit": "POST-SUBTASK-199",
            "schema_sha256": "6" * 64,
            "request_schema_version": "v1",
            "provider_policy_version": "openrouter-assistive-development-plane-v2-paid-authorization",
            "model": "qwen/qwen3-coder-next",
            "reasoning_effort": "none",
            "max_output_tokens": 128,
            "base_commit": "a" * 40,
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            "source_hashes": ["4" * 64],
            "prompt_version": "v1",
            "evidence_excerpts": ["bounded evidence excerpt"],
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
        (provider_root / "openrouter.json").write_bytes(canonical_json_bytes(packet) + b"\n")
        current_payload = json.loads(self.current.read_text(encoding="utf-8"))
        current_payload["external_evidence"]["openrouter"] = {
            "routes": [
                {
                    "provider": "openrouter",
                    "task_format": OPENROUTER_TASK_FORMAT,
                    "task_id": "independent_review",
                    "schema_sha256": packet["schema_sha256"],
                    "request_schema_version": packet["request_schema_version"],
                    "provider_policy_version": packet["provider_policy_version"],
                    "model": packet["model"],
                    "reasoning_effort": packet["reasoning_effort"],
                    "readiness_supported_state": "READY",
                    "evidence_verified": True,
                    "readiness_evidence_sha256": "7" * 64,
                    "route_evidence_sha256": "9" * 64,
                    "budget_evidence_sha256": "8" * 64,
                    "budget_released_stage_usd": "5.00",
                    "budget_remaining_usd": "2.25",
                }
            ]
        }
        self.current.write_bytes(canonical_json_bytes(current_payload) + b"\n")
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=provider_root,
            ),
        )
        refreshed = refresher.refresh(now=self.now)
        self.assertEqual(3, refreshed["granular_units"])

        class FakeOpenRouterAdapter:
            def __init__(self) -> None:
                self.calls = 0

            def run(self, _packet: dict[str, object]) -> ProviderAdapterResult:
                self.calls += 1
                return ProviderAdapterResult(
                    remote_identity=f"openrouter-run-{self.calls}",
                    result={
                        "authority": "CANDIDATE_ONLY",
                        "canonical_writes": 0,
                        "protected_decisions": 0,
                        "provider": "openrouter",
                    },
                    disposition="REVIEW_ONLY",
                    validation_errors=(),
                    actual_cost_usd="0.000123",
                    resource={"provider_calls": 1, "tokens": 42},
                )

        adapter = FakeOpenRouterAdapter()
        scheduler = InventoryScheduler(
            self.state,
            SchedulerConfig(
                inventory_current_path=self.current,
                evidence_root=self.root / "runtime/evidence",
                inventory_max_age_seconds=300,
                cycle_interval_seconds=3600,
                owner_id="openrouter-controller-test",
                max_dispatch_per_cycle=1,
            ),
            adapters={"openrouter": adapter},
        )
        first = scheduler.evaluate(now=self.now)
        self.assertEqual(1, first["dispatched_units"])
        self.assertEqual(1, first["provider_calls"])
        self.assertEqual("openrouter", first["dispatched"][0]["provider"])
        self.assertEqual(1, adapter.calls)

        refreshed = refresher.refresh(now=self.now + timedelta(seconds=61))
        self.assertEqual(3, refreshed["granular_units"])
        restarted_scheduler = InventoryScheduler(
            self.state,
            SchedulerConfig(
                inventory_current_path=self.current,
                evidence_root=self.root / "runtime/evidence",
                inventory_max_age_seconds=300,
                cycle_interval_seconds=3600,
                owner_id="openrouter-controller-test",
                max_dispatch_per_cycle=1,
            ),
            adapters={"openrouter": adapter},
        )
        second = restarted_scheduler.evaluate(now=self.now + timedelta(seconds=61))
        self.assertEqual(0, second["dispatched_units"])
        self.assertEqual(0, second["provider_calls"])
        self.assertEqual(1, adapter.calls)
        status = self.state.status()
        self.assertEqual(1, status["dispatch_attempts"])
        self.assertEqual(1, status["closed_dispatch_attempts"])
        with closing(self.state.connect()) as connection:
            runs = connection.execute(
                "SELECT provider,status,resource_json FROM provider_runs WHERE provider='openrouter'"
            ).fetchall()
            self.assertEqual(1, len(runs))
            self.assertEqual("SETTLED", runs[0]["status"])
            self.assertEqual("0.000123", json.loads(runs[0]["resource_json"])["actual_cost_usd_exact"])


if __name__ == "__main__":
    unittest.main()
