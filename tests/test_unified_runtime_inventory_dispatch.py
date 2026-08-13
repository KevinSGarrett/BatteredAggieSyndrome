from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from aggie_analytics.assistive_plane.contracts import canonical_json_bytes
from aggie_analytics.assistive_plane.controller_state import ControllerState
from aggie_analytics.assistive_plane.cpu_worker_backend import CpuWorkerClient, execute_cpu_request
from aggie_analytics.assistive_plane.inventory_runtime import RuntimeInventoryConfig, RuntimeInventoryRefresher
from aggie_analytics.assistive_plane.orchestration import ReadyWorkInventory
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
            "work_units": [],
            "route_decisions": [],
            "validation": ReadyWorkInventory([], []).validate(),
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
        self.assertEqual(2, snapshot["validation"]["work_unit_count"])
        self.assertEqual({"REMOTE_CPU_WORKER": 2}, snapshot["validation"]["counts_by_disposition"])

        second = self.refresher.refresh(now=self.now + timedelta(minutes=3))
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        refreshed_pointer = json.loads(self.current.read_text(encoding="utf-8"))
        self.assertNotEqual(pointer["refreshed_at"], refreshed_pointer["refreshed_at"])

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

        self.state.acquire_leader("watchdog-owner", "d" * 40, now=self.now, ttl_seconds=120)
        watchdog = ReadOnlyWatchdog(
            self.state.database,
            inventory_path=self.current,
            scheduler_report_path=self.root / "runtime/evidence/current/scheduler-evaluation.json",
            expected_build_commit="d" * 40,
        )
        operational = watchdog.inspect(now=self.now + timedelta(seconds=2))
        self.assertEqual("PASS", operational["structural_result"])
        self.assertEqual("PASS", operational["operational_result"])

        refreshed = self.refresher.refresh(now=self.now + timedelta(minutes=1))
        snapshot = json.loads(Path(refreshed["snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual({"COMPLETED": 2}, snapshot["validation"]["counts_by_disposition"])

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


if __name__ == "__main__":
    unittest.main()
