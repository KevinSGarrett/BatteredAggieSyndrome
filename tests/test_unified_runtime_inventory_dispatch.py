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
from aggie_analytics.assistive_plane.cursor_backend import CursorApiError
from aggie_analytics.assistive_plane.inventory_runtime import (
    BGE_DOWNSTREAM_CONSUMER_VERSION,
    CURSOR_IMPLEMENTATION_SCHEMA_SHA256,
    CURSOR_IMPLEMENTATION_TASK_FORMAT,
    CURSOR_SCHEMA_SHA256,
    CURSOR_TASK_FORMAT,
    CPU_LINE_HASH_DOWNSTREAM_CONSUMER_VERSION,
    CPU_LINE_HASH_SCHEMA_SHA256,
    CPU_LINE_HASH_TASK_FORMAT,
    CPU_TEXT_DEDUP_SCHEMA_SHA256,
    CPU_TEXT_DEDUP_TASK_FORMAT,
    OPENROUTER_TASK_FORMAT,
    RuntimeInventoryConfig,
    RuntimeInventoryRefresher,
)
from aggie_analytics.assistive_plane.orchestration import (
    ATOMIC_EXECUTABLE,
    CAMPAIGN_OWNER,
    ReadyWorkUnit,
    validate_work_unit_roles,
)
from aggie_analytics.assistive_plane.provider_adapters import ProviderAdapterResult
from aggie_analytics.assistive_plane.scheduler_runtime import (
    InventoryScheduler,
    SchedulerConfig,
    cursor_submission_retry_policy,
)
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

    def test_cursor_rate_limit_is_bounded_retry_not_terminal_global_failure(self) -> None:
        self.assertEqual(
            (True, 300), cursor_submission_retry_policy(CursorApiError(429), 1)
        )
        self.assertEqual(
            (False, 300), cursor_submission_retry_policy(CursorApiError(429), 3)
        )
        self.assertEqual(
            (False, 60), cursor_submission_retry_policy(CursorApiError(400), 1)
        )

    def test_schema_valid_semantic_candidate_is_not_auto_accepted_as_useful(self) -> None:
        result = ProviderAdapterResult(
            remote_identity="cursor-run",
            result={
                "authority": "CANDIDATE_ONLY",
                "canonical_writes": 0,
                "protected_decisions": 0,
                "run": {"result": "nonempty candidate findings"},
            },
            disposition="REVIEW_ONLY",
            validation_errors=(),
            actual_cost_usd="0.10",
            resource={"provider_calls": 1},
        )
        disposition, reason = InventoryScheduler._candidate_review_disposition("cursor", result)
        self.assertEqual("REVIEW_ONLY", disposition)
        self.assertEqual("VALID_CANDIDATE_REQUIRES_DISTINCT_VALUE_REVIEW", reason)

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
        self.assertEqual(
            {"ROUTED_TO_ASSISTIVE_PLANE": 2},
            self.state.status()["pre_routing_dispositions"],
        )

        second = self.refresher.refresh(now=self.now + timedelta(minutes=3))
        self.assertNotEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        self.assertTrue(Path(first["snapshot_path"]).is_file())
        self.assertTrue(Path(second["snapshot_path"]).is_file())
        refreshed = json.loads(Path(second["snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual(
            (self.now + timedelta(minutes=3)).isoformat().replace("+00:00", "Z"),
            refreshed["producer_watermarks"]["sources"]["historical_snapshot_registry"]["scanned_at"],
        )
        self.assertNotIn("historical_runtime", refreshed["producer_watermarks"]["sources"])
        refreshed_pointer = json.loads(self.current.read_text(encoding="utf-8"))
        self.assertNotEqual(pointer["refreshed_at"], refreshed_pointer["refreshed_at"])

    def test_semantic_discovery_isolates_one_malformed_source(self) -> None:
        malformed = self.manifests / "quarantine/c/run.json"
        malformed.parent.mkdir(parents=True)
        malformed.write_text('{"season":', encoding="utf-8")

        discovered = self.refresher._discover(self.now)

        self.assertEqual(2, len(discovered))
        with self.state.transaction() as connection:
            isolated = connection.execute(
                "SELECT COUNT(*) FROM controller_events WHERE event_type=?",
                ("SEMANTIC_DISCOVERY_SOURCE_ISOLATED",),
            ).fetchone()[0]
        self.assertEqual(1, isolated)

    def test_semantic_discovery_does_not_use_unbounded_rglob(self) -> None:
        with patch.object(Path, "rglob", side_effect=AssertionError("unbounded traversal")):
            discovered = self.refresher._discover(self.now)

        self.assertEqual(2, len(discovered))

    def test_refresh_reloads_external_semantics_and_versions_material_transition(self) -> None:
        semantic_module = self.root / "semantic_materializer.py"
        semantic_module.write_text(
            """
import hashlib
from pathlib import Path

def external_evidence_identity(root: Path):
    files = sorted(root.rglob('*.json')) if root.is_dir() else []
    return {'present': root.is_dir(), 'file_count': len(files), 'manifest_sha256': hashlib.sha256(str(len(files)).encode()).hexdigest()}

def openrouter_semantic_evidence(root: Path, policy):
    return {**external_evidence_identity(root), 'routes': [], 'state': 'PAID_PILOT_IN_PROGRESS_NOT_OPERATIONAL'}

def cursor_semantic_evidence(root: Path):
    return external_evidence_identity(root)

def local_qwen_semantic_evidence(root: Path, readiness):
    return {**external_evidence_identity(root), 'routes': []}

def cpu_worker_semantic_evidence(root: Path):
    return {
        **external_evidence_identity(root),
        'qualified': True,
        'qualifications': [{
            'tasks': ['CANONICAL_JSON', 'EXACT_TEXT_DEDUP', 'LINE_HASH_MANIFEST'],
            'evidence_sha256': 'b' * 64,
            'readiness_evidence_sha256': 'c' * 64,
        }],
    }
""".strip(),
            encoding="utf-8",
        )
        policy = self.root / "policy.json"
        readiness = self.root / "readiness.json"
        policy.write_text("{}", encoding="utf-8")
        readiness.write_text("{}", encoding="utf-8")
        assistive = self.root / "external/assistive"
        (assistive / "openrouter").mkdir(parents=True)
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                semantic_materializer_path=semantic_module,
                semantic_policy_path=policy,
                semantic_readiness_path=readiness,
                external_assistive_root=assistive,
            ),
        )

        first = refresher.refresh(now=self.now)
        (assistive / "openrouter/transition.json").write_text("{}", encoding="utf-8")
        second = refresher.refresh(now=self.now + timedelta(minutes=1))

        self.assertNotEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        snapshot = json.loads(Path(second["snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual(1, snapshot["external_evidence"]["openrouter"]["file_count"])
        self.assertEqual(second["runtime_material_identity"], snapshot["runtime_material_identity"])

    def test_operational_demand_is_independent_of_empty_packet_queue(self) -> None:
        policy = self.root / "policy.json"
        readiness = self.root / "readiness.json"
        materializer = self.root / "materializer.py"
        assistive = self.root / "external/assistive"
        assistive.mkdir(parents=True)
        policy.write_text(
            json.dumps(
                {
                    "execution_minimums": {
                        "cursor": {"units": 10, "effort_points": 40, "accepted_useful": 6},
                        "openrouter": {"units": 20, "effort_points": 60, "accepted_useful": 12},
                    }
                }
            ),
            encoding="utf-8",
        )
        readiness.write_text("{}", encoding="utf-8")
        materializer.write_text("# test fixture\n", encoding="utf-8")
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                semantic_materializer_path=materializer,
                semantic_policy_path=policy,
                semantic_readiness_path=readiness,
                external_assistive_root=assistive,
            ),
        )
        snapshot = {
            "external_evidence": {
                "cursor": {
                    "unique_jobs": 10,
                    "accepted_useful": 10,
                    "controller_routed_units": 0,
                },
                "openrouter": {"requests": 25, "accepted_useful": 9},
            }
        }
        demand = refresher._operational_demand(snapshot, [], {})
        self.assertEqual(["cursor", "openrouter"], demand["unmet_without_packets"])
        self.assertEqual(10, demand["providers"]["cursor"]["deficits"]["units"])
        self.assertEqual(10, demand["providers"]["cursor"]["manual_or_external_units"])
        self.assertEqual(20, demand["providers"]["openrouter"]["deficits"]["units"])
        self.assertEqual(12, demand["providers"]["openrouter"]["deficits"]["accepted_useful"])

    def test_operational_campaign_demand_survives_release_rotation(self) -> None:
        policy = self.root / "policy.json"
        readiness = self.root / "readiness.json"
        materializer = self.root / "materializer.py"
        assistive = self.root / "external/assistive"
        assistive.mkdir(parents=True)
        policy.write_text(
            json.dumps(
                {
                    "execution_minimums": {
                        "cursor": {"units": 10, "effort_points": 40, "accepted_useful": 0}
                    }
                }
            ),
            encoding="utf-8",
        )
        readiness.write_text("{}", encoding="utf-8")
        materializer.write_text("# test fixture\n", encoding="utf-8")
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                semantic_materializer_path=materializer,
                semantic_policy_path=policy,
                semantic_readiness_path=readiness,
                external_assistive_root=assistive,
            ),
        )

        def provider_summary(*, current_release_only: bool = False) -> dict[str, object]:
            return {
                "cursor": {
                    "closed_runs": 0 if current_release_only else 10,
                    "closed_effort_points": 0 if current_release_only else 40,
                    "review_dispositions": {},
                    "useful_work": {"accepted_useful_outputs": 0},
                    "pending_downstream_review": 0,
                }
            }

        with patch.object(self.state, "provider_run_summary", side_effect=provider_summary):
            demand = refresher._operational_demand({"external_evidence": {}}, [], {})

        cursor = demand["providers"]["cursor"]
        self.assertFalse(cursor["unmet"])
        self.assertEqual(10, cursor["observed_units"])
        self.assertEqual(0, cursor["current_release_closed_units"])
        self.assertEqual([], demand["unmet_without_packets"])

    def test_watchdog_fails_when_campaign_debt_has_no_execution_packets(self) -> None:
        now = self.now
        self.state.acquire_leader("watchdog-test", "a" * 40, ttl_seconds=300, now=now)
        inventory = self.root / "inventory-current.json"
        inventory.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "artifact_type": "UNIFIED_ASSISTIVE_RUNTIME_INVENTORY",
                    "generated_at": now.isoformat().replace("+00:00", "Z"),
                    "route_decisions": [],
                    "operational_demand": {
                        "enabled": True,
                        "unmet_without_packets": ["openrouter"],
                    },
                }
            ),
            encoding="utf-8",
        )
        scheduler = self.root / "scheduler.json"
        scheduler.write_text(
            json.dumps(
                {
                    "observed_at": now.isoformat().replace("+00:00", "Z"),
                    "result": "PASS",
                    "dispatched_units": 0,
                    "provider_calls": 0,
                    "idle_units": [],
                    "operational_completion": "INCOMPLETE",
                }
            ),
            encoding="utf-8",
        )
        report = ReadOnlyWatchdog(
            self.state.database,
            inventory_path=inventory,
            scheduler_report_path=scheduler,
            expected_build_commit="a" * 40,
        ).inspect(now=now)
        self.assertEqual("FAIL", report["operational_result"])
        self.assertIn(
            "AUTHORIZED_CAMPAIGN_BACKLOG_HAS_NO_EXECUTABLE_PACKETS:openrouter",
            report["operational_findings"],
        )
        self.assertEqual(["openrouter"], report["unmet_campaigns_without_packets"])

    def test_continuous_compiler_materializes_live_historical_openrouter_work(self) -> None:
        policy = self.root / "policy.json"
        readiness = self.root / "readiness.json"
        materializer = self.root / "materializer.py"
        assistive = self.root / "external/assistive"
        source_root = self.root / "external/runtime"
        progress = source_root / "BAT-554/2014/progress.json"
        progress.parent.mkdir(parents=True)
        progress.write_text(
            json.dumps({"season": 2014, "teams_visited": 200, "unresolved": 17}),
            encoding="utf-8",
        )
        historical_snapshot = self.manifests / "snap_2014_live.json"
        historical_snapshot.write_text(
            json.dumps(
                {
                    "dataset": "ncaa_team_season_discovery",
                    "snapshot_id": "snap_2014_live",
                    "source_id": "SRC-015",
                    "raw_sha256": "1" * 64,
                    "retrieved_at": "2026-08-13T02:00:00Z",
                    "schema_fields": ["team_season_ids", "contest_ids"],
                    "metadata": {"jira_key": "BAT-554", "candidate_only": True},
                }
            ),
            encoding="utf-8",
        )
        reconciliation = self.root / "reconciliation/historical_expansion/checkpoint.json"
        reconciliation.parent.mkdir(parents=True)
        reconciliation.write_text(
            json.dumps(
                {
                    "artifact_type": "RECONCILIATION_CHECKPOINT",
                    "unresolved": 2907,
                    "reconciliation": {
                        "unresolved_reason_counts": {
                            "contest_mismatch": 5,
                            "missing_team_id": 12,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        feature = self.root / "reconciliation/feature_engineering/candidate.json"
        feature.parent.mkdir(parents=True)
        feature.write_text(
            json.dumps({"artifact_type": "FEATURE_CANDIDATE", "pit_eligible": False}),
            encoding="utf-8",
        )
        assistive.mkdir(parents=True)
        policy.write_text(
            json.dumps(
                {
                    "execution_minimums": {
                        "openrouter": {"units": 20, "effort_points": 60, "accepted_useful": 12}
                    }
                }
            ),
            encoding="utf-8",
        )
        readiness.write_text("{}", encoding="utf-8")
        materializer.write_text("# test fixture\n", encoding="utf-8")
        task_registry = self.root / "openrouter-task-registry.json"
        task_registry.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tasks": {
                        "schema_drift_review": {"jira_unit": "POST-SUBTASK-200"},
                        "reconciliation_ranking": {"jira_unit": "POST-SUBTASK-200"},
                        "independent_review": {"jira_unit": "POST-SUBTASK-199"},
                    },
                }
            ),
            encoding="utf-8",
        )
        queue = self.root / "provider-work/requests"
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=queue,
                semantic_materializer_path=materializer,
                semantic_policy_path=policy,
                semantic_readiness_path=readiness,
                openrouter_task_registry_path=task_registry,
                external_assistive_root=assistive,
                continuous_source_root=source_root,
            ),
        )
        route = {
            "provider": "openrouter",
            "task_format": OPENROUTER_TASK_FORMAT,
            "task_id": "schema_drift_review",
            "schema_sha256": "6" * 64,
            "request_schema_version": "v1",
            "provider_policy_version": "openrouter-assistive-development-plane-v2-paid-authorization",
            "model": "qwen/qwen3-coder-next",
            "reasoning_effort": "none",
            "readiness_supported_state": "READY",
            "evidence_verified": True,
            "readiness_evidence_sha256": "7" * 64,
            "route_evidence_sha256": "8" * 64,
            "budget_evidence_sha256": "9" * 64,
            "budget_released_stage_usd": "5.00",
            "budget_remaining_usd": "4.00",
        }
        routes = [
            {**route, "task_id": task_id, "schema_sha256": token * 64}
            for task_id, token in (
                ("schema_drift_review", "6"),
                ("reconciliation_ranking", "5"),
                ("independent_review", "4"),
            )
        ]
        snapshot = {
            "git": {"head": "a" * 40, "origin_main": "a" * 40},
            "external_evidence": {
                "openrouter": {
                    "requests": 25,
                    "accepted_useful": 9,
                    "routes": routes,
                }
            },
        }
        demand = refresher._operational_demand(snapshot, [], {})
        created = refresher._materialize_continuous_openrouter_work(snapshot, demand)
        self.assertEqual(3, len(created))
        packets = [json.loads(Path(item["packet_path"]).read_text(encoding="utf-8")) for item in created]
        self.assertEqual(
            {"schema_drift_review", "reconciliation_ranking", "independent_review"},
            {packet["task_id"] for packet in packets},
        )
        self.assertTrue(all(packet["prompt_version"] == "continuous-real-bas-evidence-v2" for packet in packets))
        self.assertTrue(all(packet["base_commit"] == "a" * 40 for packet in packets))
        jira_by_task = {packet["task_id"]: packet["jira_unit"] for packet in packets}
        self.assertEqual("POST-SUBTASK-199", jira_by_task["independent_review"])
        self.assertEqual("POST-SUBTASK-200", jira_by_task["schema_drift_review"])
        self.assertEqual("POST-SUBTASK-200", jira_by_task["reconciliation_ranking"])
        reconciliation_packet = next(
            packet for packet in packets if packet["task_id"] == "reconciliation_ranking"
        )
        reconciliation_evidence = json.loads(reconciliation_packet["evidence_excerpts"][0])
        self.assertEqual(
            ["contest_mismatch", "missing_team_id"],
            reconciliation_evidence["reconciliation_candidate_binding_v1"]["candidate_ids"],
        )
        discovered = refresher._discover_provider_work(snapshot, self.now)
        self.assertEqual(3, len(discovered))
        self.assertTrue(all(item[1].disposition.value == "OPENROUTER" for item in discovered))

    def test_ready_canonical_jira_unit_becomes_granular_cursor_and_openrouter_work(self) -> None:
        project = self.root / "project"
        issue = project / "jira/records/issues/subtasks/POST-SUBTASK-900_ready.json"
        issue.parent.mkdir(parents=True)
        issue.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "local_id": "POST-SUBTASK-900",
                    "jira_key": "BAT-900",
                    "priority": "P1",
                    "ready": True,
                    "workflow_state": "READY",
                    "execution_mode": "ATOMIC_EXECUTION",
                    "blocked_reason": "",
                    "objective": "Implement a bounded parser correction",
                    "scope": "Correct parser behavior and preserve negative evidence.",
                    "acceptance_criteria": ["Targeted parser test passes"],
                    "allowed_modification_paths": ["src/parser.py", "tests/test_parser.py"],
                    "files_expected_to_be_touched": ["src/parser.py", "tests/test_parser.py"],
                    "files_to_inspect": ["src/parser.py", "tests/test_parser.py"],
                    "expected_outputs": [],
                    "required_tests": [{"path": "tests/test_parser.py"}],
                    "dependencies": [],
                    "operational_jira": {"status_raw": "To Do"},
                }
            ),
            encoding="utf-8",
        )
        build_commit = "a" * 40
        release = self.root / "releases" / build_commit
        release.mkdir(parents=True)
        registry = self.root / "openrouter-task-registry.json"
        registry.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tasks": {
                        "independent_review": {"jira_unit": "POST-SUBTASK-199"},
                    },
                }
            ),
            encoding="utf-8",
        )
        queue = self.root / "provider-work/requests"
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=queue,
                release_root=release,
                build_commit=build_commit,
                project_root=project,
                openrouter_task_registry_path=registry,
            ),
        )
        route = {
            "provider": "openrouter",
            "task_format": OPENROUTER_TASK_FORMAT,
            "task_id": "independent_review",
            "schema_sha256": "6" * 64,
            "request_schema_version": "v1",
            "provider_policy_version": "policy-v1",
            "model": "qwen/qwen3-coder-next",
            "reasoning_effort": "none",
            "readiness_supported_state": "READY",
            "evidence_verified": True,
            "readiness_evidence_sha256": "7" * 64,
            "route_evidence_sha256": "8" * 64,
            "budget_evidence_sha256": "9" * 64,
            "budget_released_stage_usd": "5.00",
            "budget_remaining_usd": "4.00",
        }
        snapshot = {
            "git": {"head": build_commit, "origin_main": build_commit},
            "external_evidence": {
                "openrouter": {"requests": 0, "accepted_useful": 0, "routes": [route]},
                "cursor": {
                    "present": True,
                    "manifest_sha256": "5" * 64,
                    "unique_jobs": 4,
                    "settled_usd": "1.00",
                },
            },
        }
        demand = {
            "providers": {
                "openrouter": {"unmet": True, "active_execution_packets": 0, "pending_review_results": 0},
                "cursor": {"unmet": True, "active_execution_packets": 0, "pending_review_results": 0},
            }
        }
        openrouter = refresher._materialize_continuous_openrouter_work(snapshot, demand)
        cursor = refresher._materialize_continuous_cursor_work(snapshot, demand)
        self.assertEqual(1, len(openrouter))
        self.assertEqual(1, len(cursor))
        packets = [
            json.loads(Path(item["packet_path"]).read_text(encoding="utf-8"))
            for item in [*openrouter, *cursor]
        ]
        self.assertTrue(all(packet["source_jira_unit"] == "BAT-900" for packet in packets))
        discovered = refresher._discover_provider_work(snapshot, self.now)
        self.assertEqual({"BAT-900"}, {unit.jira_unit for unit, _, _ in discovered})
        self.assertEqual({"OPENROUTER", "CURSOR"}, {decision.disposition.value for _, decision, _ in discovered})

    def test_jira_ready_scan_is_cached_within_refresh_and_invalidated_between_refreshes(self) -> None:
        project = self.root / "project"
        issue = project / "jira/records/issues/tasks/TASK-900_ready.json"
        issue.parent.mkdir(parents=True)
        payload = {
            "local_id": "TASK-900",
            "jira_key": "BAT-900",
            "priority": "P1",
            "ready": True,
            "workflow_state": "READY",
            "execution_mode": "ATOMIC_EXECUTION",
            "blocked_reason": "",
            "acceptance_criteria": ["evidence exists"],
            "expected_outputs": ["artifact.json"],
            "operational_jira": {"status_raw": "To Do"},
        }
        issue.write_text(json.dumps(payload), encoding="utf-8")
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                project_root=project,
            ),
        )
        first = refresher._jira_ready_records()
        self.assertEqual("BAT-900", first[0][1]["jira_key"])
        issue.unlink()
        self.assertEqual(first, refresher._jira_ready_records())
        refresher._jira_ready_cache = None
        self.assertEqual([], refresher._jira_ready_records())

    def test_reviewed_cursor_jira_unit_materializes_bounded_implementation_packet(
        self,
    ) -> None:
        project = self.root / "project"
        issue = project / "jira/records/issues/tasks/TASK-900_ready.json"
        issue.parent.mkdir(parents=True)
        issue.write_text(
            json.dumps(
                {
                    "local_id": "TASK-900",
                    "jira_key": "BAT-900",
                    "priority": "P1",
                    "ready": True,
                    "workflow_state": "READY",
                    "execution_mode": "ATOMIC_EXECUTION",
                    "blocked_reason": "",
                    "objective": "Materialize the bounded gate evidence",
                    "scope": "Update only the admitted artifact",
                    "allowed_modification_paths": ["artifacts/gate.json"],
                    "required_tests": [
                        {"path": "tests/test_gate.py"},
                        {"path": "MANUAL"},
                    ],
                    "acceptance_criteria": ["gate is deterministic"],
                    "expected_outputs": ["artifacts/gate.json"],
                    "operational_jira": {"status_raw": "To Do"},
                }
            ),
            encoding="utf-8",
        )
        queue = self.root / "provider-work/requests"
        review_packet = self.root / "review-packet.json"
        review_packet.write_bytes(
            canonical_json_bytes(
                {
                    "schema_version": 1,
                    "provider": "cursor",
                    "task_format": CURSOR_TASK_FORMAT,
                    "source_jira_unit": "BAT-900",
                    "base_commit": "a" * 40,
                    "starting_ref": "a" * 40,
                    "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
                }
            )
            + b"\n"
        )
        review_packet_sha256 = hashlib.sha256(review_packet.read_bytes()).hexdigest()
        result = self.root / "review-result.json"
        result.write_bytes(
            canonical_json_bytes(
                {
                    "schema_version": 1,
                    "artifact_type": "GOVERNED_PROVIDER_CANDIDATE_RESULT",
                    "provider": "cursor",
                    "work_unit_id": "AUTO-CURSOR-REVIEW",
                    "attempt_id": "b" * 64,
                    "authority": "CANDIDATE_ONLY",
                    "disposition": "REVIEW_ONLY",
                    "validation_errors": [],
                    "result": {
                        "authority": "CANDIDATE_ONLY",
                        "canonical_writes": 0,
                        "protected_decisions": 0,
                        "run": {
                            "result": "Implement the exact admitted artifact and preserve negative findings."
                        },
                    },
                }
            )
            + b"\n"
        )
        result_sha256 = hashlib.sha256(result.read_bytes()).hexdigest()
        stamp = self.now.isoformat().replace("+00:00", "Z")
        with self.state.transaction() as connection:
            connection.execute(
                "INSERT INTO work_units(work_unit_id,identity_sha256,jira_identity,effort_points,current_state,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                ("AUTO-CURSOR-REVIEW", "a" * 64, "BAT-900", 5, "CLOSED", stamp, stamp),
            )
            connection.execute(
                "INSERT INTO dispatch_attempts(attempt_id,work_unit_id,provider,route_identity,state,started_at,completed_at) VALUES(?,?,?,?,?,?,?)",
                ("b" * 64, "AUTO-CURSOR-REVIEW", "cursor", "c" * 64, "CLOSED", stamp, stamp),
            )
            connection.execute(
                "INSERT INTO provider_runs(provider_run_id,attempt_id,provider,remote_identity,request_sha256,status,resource_json,started_at,completed_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "d" * 64,
                    "b" * 64,
                    "cursor",
                    "agent:run",
                    "e" * 64,
                    "SETTLED",
                    json.dumps(
                        {
                            "packet_path": str(review_packet),
                            "packet_sha256": review_packet_sha256,
                        }
                    ),
                    stamp,
                    stamp,
                ),
            )
            connection.execute(
                "INSERT INTO execution_artifacts(artifact_id,work_unit_id,attempt_id,artifact_type,path,sha256,bytes,recorded_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    "f" * 64,
                    "AUTO-CURSOR-REVIEW",
                    "b" * 64,
                    "PROVIDER_REQUEST_RESPONSE",
                    str(result),
                    result_sha256,
                    result.stat().st_size,
                    stamp,
                ),
            )
            connection.execute(
                "INSERT INTO reviews(review_id,work_unit_id,attempt_id,reviewer,disposition,evidence_sha256,review_seconds,recorded_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    "1" * 64,
                    "AUTO-CURSOR-REVIEW",
                    "b" * 64,
                    "DURABLE_QUEUE",
                    "REVIEW_ONLY",
                    "2" * 64,
                    0.0,
                    stamp,
                ),
            )
        self.state.record_downstream_review_disposition(
            attempt_id="b" * 64,
            disposition="ACCEPTED",
            downstream_consumer="CURSOR_CANDIDATE_CODE_REVIEW_QUEUE",
            reason="VALIDATED_CANDIDATE_REVIEW",
            consumed_artifact_identity="3" * 64,
            changed_project_artifact=True,
            now=self.now,
        )
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=queue,
                project_root=project,
            ),
        )

        review_candidates = self.state.cursor_review_candidates(limit=32)
        with patch.object(
            self.state,
            "cursor_review_candidates",
            return_value=review_candidates + review_candidates,
        ):
            created = refresher._materialize_cursor_implementation_work(
                snapshot={"git": {"head": "a" * 40, "origin_main": "a" * 40}},
                release_commit="a" * 40,
                limit=2,
            )

        self.assertEqual(1, len(created))
        packet = json.loads(
            Path(created[0]["packet_path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(CURSOR_IMPLEMENTATION_TASK_FORMAT, packet["task_format"])
        self.assertEqual(CURSOR_IMPLEMENTATION_SCHEMA_SHA256, packet["schema_sha256"])
        self.assertEqual(["artifacts/gate.json"], packet["allowed_paths"])
        self.assertEqual(["tests/test_gate.py"], packet["required_tests"])
        self.assertEqual(["AUTO-CURSOR-REVIEW"], packet["dependencies"])
        self.assertEqual(result_sha256, packet["source_review_result_sha256"])

    def test_cursor_packet_survives_submit_poll_and_restart_safe_completion(self) -> None:
        current_payload = json.loads(self.current.read_text(encoding="utf-8"))
        current_payload["external_evidence"]["cursor"] = {
            "present": True,
            "manifest_sha256": "7" * 64,
            "unique_jobs": 10,
            "settled_usd": "5.00",
        }
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        packet = {
            "schema_version": 1,
            "provider": "cursor",
            "task_format": CURSOR_TASK_FORMAT,
            "jira_unit": "POST-SUBTASK-202",
            "schema_sha256": CURSOR_SCHEMA_SHA256,
            "source_hashes": ["8" * 64],
            "dependencies": [],
            "pre_routing_effort_points": 5,
            "scope": "Controller-routed exact-base repository review",
            "repository_url": "https://github.com/KevinSGarrett/BatteredAggieSyndrome.git",
            "starting_ref": "a" * 40,
            "base_commit": "a" * 40,
            "model": "gpt-5.3-codex",
            "reasoning": "medium",
            "fast": False,
            "work_on_current_branch": False,
            "auto_create_pr": False,
            "max_reservation_usd": "2.00",
            "prompt": "Review scheduler liveness without modifying files.",
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        (provider_root / "cursor.json").write_bytes(canonical_json_bytes(packet) + b"\n")
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
        refresher.refresh(now=self.now)

        class FakeCursorAdapter:
            def __init__(self) -> None:
                self.submits = 0
                self.polls = 0

            def submit(self, _packet):
                self.submits += 1
                return {
                    "job_id": "9" * 64,
                    "agent_id": "bc-controller-test",
                    "request_path": "cursor-request",
                    "request_sha256": "a" * 64,
                    "provider_calls": 1,
                }

            def poll(self, _packet, _handle):
                self.polls += 1
                return ProviderAdapterResult(
                    remote_identity="bc-controller-test:run-1",
                    result={
                        "authority": "CANDIDATE_ONLY",
                        "canonical_writes": 0,
                        "protected_decisions": 0,
                        "dispatch_origin": "PERSISTENT_CONTROLLER",
                    },
                    disposition="REVIEW_ONLY",
                    validation_errors=(),
                    actual_cost_usd="0.25",
                    resource={"agent_id": "bc-controller-test", "run_id": "run-1"},
                )

        adapter = FakeCursorAdapter()
        scheduler = InventoryScheduler(
            self.state,
            SchedulerConfig(
                inventory_current_path=self.current,
                evidence_root=self.root / "runtime/evidence",
                inventory_max_age_seconds=300,
                cycle_interval_seconds=60,
                owner_id="cursor-controller-test",
                max_dispatch_per_cycle=1,
            ),
            adapters={"cursor": adapter},
        )
        first = scheduler.evaluate(now=self.now)
        self.assertEqual(1, first["dispatched_units"])
        self.assertEqual(1, first["provider_calls"])
        self.assertEqual(1, adapter.submits)
        inflight = self.state.inflight_provider_runs("cursor")
        self.assertEqual(1, len(inflight))

        second = scheduler.evaluate(now=self.now + timedelta(seconds=61))
        self.assertEqual(1, adapter.submits)
        self.assertEqual(1, adapter.polls)
        self.assertEqual("RESULT_REVIEW_QUEUED", second["cursor_polls"][0]["state"])
        self.assertEqual(
            "AWAITING_REVIEW",
            second["eligible_unit_classifications"][str(inflight[0]["work_unit_id"])]["category"],
        )
        self.assertNotIn(
            str(inflight[0]["work_unit_id"]),
            {item["work_unit_id"] for item in second["unexplained_idle_units"]},
        )
        self.assertEqual([], self.state.inflight_provider_runs("cursor"))
        states = self.state.work_unit_states({str(inflight[0]["work_unit_id"])})
        self.assertEqual("CLOSED", states[str(inflight[0]["work_unit_id"])] )

    def test_continuous_compilers_emit_real_cursor_cpu_bge_and_openai_units(self) -> None:
        source_root = self.root / "external/runtime"
        progress = source_root / "BAT-554/2015/progress.json"
        progress.parent.mkdir(parents=True)
        progress.write_text(json.dumps({"season": 2015, "teams_visited": 321}), encoding="utf-8")
        (self.manifests / "snap_2015_live.json").write_text(
            json.dumps(
                {
                    "dataset": "ncaa_team_season_discovery",
                    "snapshot_id": "snap_2015_live",
                    "source_id": "SRC-015",
                    "raw_sha256": "2" * 64,
                    "retrieved_at": "2026-08-13T02:00:00Z",
                    "schema_fields": ["team_season_ids", "contest_ids"],
                    "metadata": {"jira_key": "BAT-554", "candidate_only": True},
                }
            ),
            encoding="utf-8",
        )
        reconciliation_root = self.root / "reconciliation/historical_expansion"
        reconciliation_root.mkdir(parents=True)
        for index in range(3):
            (reconciliation_root / f"checkpoint-{index}.json").write_text(
                json.dumps(
                    {
                        "artifact_type": "HISTORICAL_RECONCILIATION",
                        "decision_unit": f"BAT-554-{index}",
                        "negative_findings": [f"missing-{index}"],
                    }
                ),
                encoding="utf-8",
            )
        quarantine = self.root / "quarantine/schema/record.json"
        quarantine.parent.mkdir(parents=True)
        quarantine.write_text(
            json.dumps({"artifact_type": "SCHEMA_QUARANTINE", "reason": "FIELD_DRIFT"}),
            encoding="utf-8",
        )
        build_commit = "a" * 40
        release = self.root / "releases" / build_commit
        schema = release / "schemas/openai/assistive_candidate.schema.json"
        schema.parent.mkdir(parents=True)
        schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
        openai_task_registry = release / "configs/openai_task_registry.json"
        openai_task_registry.parent.mkdir(parents=True)
        openai_task_registry.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "tasks": {
                        "quarantine_schema_classification": {
                            "jira_unit": "POST-SUBTASK-164",
                            "candidate_destination": "QUARANTINE",
                            "allowed_models": ["gpt-5.6-luna", "gpt-5.6-terra"],
                            "allocation_by_model": {
                                "gpt-5.6-luna": "LUNA_HARD_VOLUME",
                                "gpt-5.6-terra": "TERRA_COMPLEX",
                            },
                        },
                        "gamebook_schema_mapping": {
                            "jira_unit": "POST-SUBTASK-168",
                            "candidate_destination": "REVIEW",
                            "allowed_models": ["gpt-5.6-terra"],
                            "allocation_by_model": {"gpt-5.6-terra": "TERRA_COMPLEX"},
                        },
                        "entity_review": {
                            "jira_unit": "POST-SUBTASK-163",
                            "candidate_destination": "REVIEW",
                            "allowed_models": ["gpt-5.6-terra"],
                            "allocation_by_model": {"gpt-5.6-terra": "TERRA_COMPLEX"},
                        },
                        "assistive_model_evaluation": {
                            "jira_unit": "POST-SUBTASK-161",
                            "candidate_destination": "CANDIDATE",
                            "allowed_models": ["gpt-5.6-luna"],
                            "allocation_by_model": {"gpt-5.6-luna": "CROSS_MODEL_QA"},
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        for relative in (
            "src/aggie_analytics/assistive_plane/inventory_runtime.py",
            "src/aggie_analytics/assistive_plane/scheduler_runtime.py",
        ):
            target = release / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"# {relative}\n", encoding="utf-8")
        queue = self.root / "provider-work/requests"
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=queue,
                release_root=release,
                build_commit=build_commit,
                openai_task_registry_path=openai_task_registry,
                continuous_source_root=source_root,
                bge_downstream_consumer_contract_version="test-semantic-review-routing-v1",
            ),
        )
        demand = {
            "providers": {
                provider: {"unmet": True, "active_execution_packets": 0, "pending_review_results": 0}
                for provider in (
                    "cursor", "remote_cpu_worker", "ollama_local", "openai_direct"
                )
            }
        }
        cursor = refresher._materialize_continuous_cursor_work(
            {"git": {"head": build_commit, "origin_main": build_commit}}, demand
        )
        cpu = refresher._materialize_continuous_cpu_work({}, demand)
        bge = refresher._materialize_continuous_bge_work(demand)
        openai = refresher._materialize_continuous_openai_work(demand)
        self.assertEqual(2, len(cursor))
        self.assertEqual(1, len(cpu))
        self.assertEqual(2, len(bge))
        self.assertEqual(2, len(openai))
        packets = [
            json.loads(Path(item["packet_path"]).read_text(encoding="utf-8"))
            for item in [*cursor, *cpu, *bge, *openai]
        ]
        self.assertEqual(
            {"cursor", "remote_cpu_worker", "ollama_local", "openai_direct"},
            {packet["provider"] for packet in packets},
        )
        self.assertTrue(all(packet["authority"] == "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES" for packet in packets))
        cpu_packet = next(packet for packet in packets if packet["provider"] == "remote_cpu_worker")
        self.assertEqual("LINE_HASH_MANIFEST", cpu_packet["task"])
        self.assertGreaterEqual(cpu_packet["input_metrics"]["records"], 1)
        self.assertEqual(
            cpu_packet["input_metrics"]["records"], len(cpu_packet["source_hashes"])
        )
        self.assertEqual(
            "HISTORICAL_MANIFEST_PROVENANCE_AND_REPLAY_VALIDATION",
            cpu_packet["downstream_consumer"],
        )
        self.assertEqual(
            CPU_LINE_HASH_DOWNSTREAM_CONSUMER_VERSION,
            cpu_packet["downstream_consumer_contract_version"],
        )
        self.assertEqual(
            {"quarantine_schema_classification", "entity_review"},
            {
                packet["job"]["task_name"]
                for packet in packets
                if packet["provider"] == "openai_direct"
            },
        )
        self.assertTrue(
            all(
                packet["job"]["max_output_tokens"] >= 2400
                for packet in packets
                if packet["provider"] == "openai_direct"
            )
        )
        self.assertTrue(
            all(
                f'disposition {packet["job"]["destination"]}' in packet["job"]["prompt"]
                for packet in packets
                if packet["provider"] == "openai_direct"
            )
        )

    def test_cpu_manifest_producer_prioritizes_largest_natural_tranche(self) -> None:
        for index in range(5):
            (self.manifests / f"snap_large_{index}.json").write_text(
                json.dumps(
                    {
                        "dataset": "large_historical_dataset",
                        "snapshot_id": f"snap_large_{index}",
                        "raw_sha256": str(index + 1) * 64,
                    }
                ),
                encoding="utf-8",
            )
        (self.manifests / "snap_small.json").write_text(
            json.dumps(
                {
                    "dataset": "a_small_dataset",
                    "snapshot_id": "snap_small",
                    "raw_sha256": "f" * 64,
                }
            ),
            encoding="utf-8",
        )
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=self.root / "provider-work/requests",
            ),
        )
        packet_record = refresher._materialize_continuous_cpu_work(
            {},
            {
                "providers": {
                    "remote_cpu_worker": {
                        "unmet": True,
                        "active_execution_packets": 0,
                        "pending_review_results": 0,
                    }
                }
            },
        )[0]
        packet = json.loads(Path(packet_record["packet_path"]).read_text(encoding="utf-8"))
        self.assertEqual(
            "large_historical_dataset", packet["source_defined_tranche"]["dataset"]
        )
        self.assertEqual(5, packet["input_metrics"]["records"])

    def test_cpu_manifest_producer_replenishes_by_dataset_after_terminal_tranche(self) -> None:
        for dataset, suffix in (("alpha_dataset", "a"), ("beta_dataset", "b")):
            (self.manifests / f"snap_{suffix}.json").write_text(
                json.dumps(
                    {
                        "dataset": dataset,
                        "snapshot_id": f"snap_{suffix}",
                        "source_id": "SRC-TEST",
                        "raw_sha256": suffix * 64,
                        "retrieved_at": "2026-08-13T02:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=self.root / "provider-work/requests",
            ),
        )
        demand = {
            "providers": {
                "remote_cpu_worker": {
                    "unmet": True,
                    "active_execution_packets": 0,
                    "pending_review_results": 0,
                }
            }
        }
        first = refresher._materialize_continuous_cpu_work({}, demand)
        self.assertEqual(1, len(first))
        first_packet = json.loads(Path(first[0]["packet_path"]).read_text(encoding="utf-8"))
        self.assertEqual("alpha_dataset", first_packet["source_defined_tranche"]["dataset"])
        first_work_unit = "AUTO-CPU-LINE-HASH-" + first[0]["packet_sha256"][:20]

        def terminal_first(work_unit_ids: set[str]) -> dict[str, str]:
            return {item: "CLOSED" for item in work_unit_ids if item == first_work_unit}

        with patch.object(self.state, "work_unit_states", side_effect=terminal_first):
            second = refresher._materialize_continuous_cpu_work({}, demand)
        self.assertEqual(1, len(second))
        second_packet = json.loads(Path(second[0]["packet_path"]).read_text(encoding="utf-8"))
        self.assertEqual("beta_dataset", second_packet["source_defined_tranche"]["dataset"])

    def test_cursor_readiness_uses_released_budget_stage_from_live_policy(self) -> None:
        packet = {
            "provider": "cursor",
            "task_format": CURSOR_TASK_FORMAT,
            "model": "gpt-5.3-codex",
            "reasoning": "medium",
        }
        evidence = {
            "present": True,
            "unique_jobs": 10,
            "manifest_sha256": "a" * 64,
            "settled_usd": "25.00",
            "budget_hard_limit_usd": "200.00",
            "budget_released_stage_usd": "60.00",
        }
        self.assertIsNotNone(
            RuntimeInventoryRefresher._provider_readiness(
                {"external_evidence": {"cursor": evidence}}, packet
            )
        )
        evidence["budget_released_stage_usd"] = "20.00"
        self.assertIsNone(
            RuntimeInventoryRefresher._provider_readiness(
                {"external_evidence": {"cursor": evidence}}, packet
            )
        )

    def test_live_manifests_replenish_bge_and_openai_gamebook_work(self) -> None:
        for index in range(3):
            (self.manifests / f"snap_live_{index}.json").write_text(
                json.dumps(
                    {
                        "dataset": "ncaa_team_season_discovery",
                        "snapshot_id": f"snap_live_{index}",
                        "source_id": "SRC-015",
                        "raw_sha256": str(index + 1) * 64,
                        "retrieved_at": f"2026-08-13T02:0{index}:00Z",
                        "row_count": index + 1,
                        "schema_fields": ["team_season_ids", "contest_ids"],
                        "metadata": {"selected_route_id": "scrapfly"},
                    }
                ),
                encoding="utf-8",
            )
        raw = (
            b"<html><body><table><tr><th>Quarter</th><th>Clock</th><th>Play</th></tr>"
            + b"<tr><td>1</td><td>14:51</td><td>Kickoff returned 22 yards</td></tr>" * 5
            + b"</table></body></html>"
        )
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        raw_path = self.root / f"raw/SRC-015/ncaa_contest_play_by_play/{raw_sha256}.html"
        raw_path.parent.mkdir(parents=True)
        raw_path.write_bytes(raw)
        manifest = {
            "dataset": "ncaa_contest_play_by_play",
            "snapshot_id": "snap_gamebook_live",
            "source_id": "SRC-015",
            "source_uri": "https://stats.ncaa.org/contests/1/play_by_play",
            "relative_path": raw_path.relative_to(self.root).as_posix(),
            "raw_sha256": raw_sha256,
            "retrieved_at": "2026-08-13T02:05:00Z",
            "row_count": 1,
            "schema_fields": [],
            "metadata": {"selected_route_id": "scrapfly"},
        }
        (self.manifests / "snap_gamebook_live.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        build_commit = "a" * 40
        release = self.root / "releases" / build_commit
        schema = release / "schemas/openai/assistive_candidate.schema.json"
        schema.parent.mkdir(parents=True)
        schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
        registry = release / "configs/openai_task_registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "tasks": {
                        "gamebook_schema_mapping": {
                            "jira_unit": "POST-SUBTASK-168",
                            "candidate_destination": "REVIEW",
                            "allowed_models": ["gpt-5.6-terra"],
                            "allocation_by_model": {"gpt-5.6-terra": "TERRA_COMPLEX"},
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=self.root / "provider-work/requests",
                release_root=release,
                build_commit=build_commit,
                openai_task_registry_path=registry,
                bge_downstream_consumer_contract_version="test-semantic-review-routing-v1",
            ),
        )
        demand = {
            "providers": {
                "ollama_local": {"unmet": True, "active_execution_packets": 0},
                "openai_direct": {"unmet": True, "active_execution_packets": 0},
            }
        }
        bge = refresher._materialize_continuous_bge_work(demand)
        openai = refresher._materialize_continuous_openai_work(demand)
        self.assertEqual(2, len(bge))
        self.assertEqual(1, len(openai))
        openai_packet = json.loads(Path(openai[0]["packet_path"]).read_text(encoding="utf-8"))
        self.assertEqual("gamebook_schema_mapping", openai_packet["job"]["task_name"])
        self.assertEqual("POST-SUBTASK-168", openai_packet["jira_unit"])
        self.assertEqual("gpt-5.6-terra", openai_packet["job"]["model"])
        self.assertEqual(raw_sha256, openai_packet["job"]["source_capture_sha256"])
        self.assertIn("Quarter", openai_packet["job"]["source_excerpt"])

    def test_bge_continuous_work_fails_closed_without_downstream_consumer(self) -> None:
        demand = {
            "providers": {
                "ollama_local": {
                    "unmet": True,
                    "active_execution_packets": 0,
                    "pending_review_results": 0,
                }
            }
        }
        self.assertEqual([], self.refresher._materialize_continuous_bge_work(demand))

    def test_feature_evidence_replenishes_openai_without_historical_directory(self) -> None:
        feature_root = self.root / "reconciliation/feature_engineering"
        feature_root.mkdir(parents=True)
        feature = feature_root / "preliminary-negative-result.json"
        feature.write_text(
            json.dumps(
                {
                    "artifact_type": "PRELIMINARY_UNPROTECTED_FEATURE_RESULT",
                    "decision": "REJECT_CANDIDATE",
                    "negative_findings": ["NO_STABLE_CHRONOLOGICAL_LIFT"],
                    "protected_claim": False,
                }
            ),
            encoding="utf-8",
        )
        build_commit = "a" * 40
        release = self.root / "releases" / build_commit
        schema = release / "schemas/openai/assistive_candidate.schema.json"
        schema.parent.mkdir(parents=True)
        schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
        registry = release / "configs/openai_task_registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "tasks": {
                        "assistive_model_evaluation": {
                            "jira_unit": "POST-SUBTASK-161",
                            "candidate_destination": "CANDIDATE",
                            "allowed_models": ["gpt-5.6-luna"],
                            "allocation_by_model": {"gpt-5.6-luna": "CROSS_MODEL_QA"},
                        },
                        "gamebook_schema_mapping": {
                            "jira_unit": "POST-SUBTASK-168",
                            "candidate_destination": "REVIEW",
                            "allowed_models": ["gpt-5.6-terra"],
                            "allocation_by_model": {"gpt-5.6-terra": "TERRA_COMPLEX"},
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=self.root / "provider-work/requests",
                release_root=release,
                build_commit=build_commit,
                openai_task_registry_path=registry,
            ),
        )
        packets = refresher._materialize_continuous_openai_work(
            {"providers": {"openai_direct": {"unmet": True, "active_execution_packets": 0}}}
        )
        self.assertEqual(1, len(packets))
        packet = json.loads(Path(packets[0]["packet_path"]).read_text(encoding="utf-8"))
        self.assertEqual("assistive_model_evaluation", packet["job"]["task_name"])
        self.assertEqual("gpt-5.6-luna", packet["job"]["model"])
        self.assertEqual("CANDIDATE", packet["job"]["destination"])
        self.assertIn("PRELIMINARY_UNPROTECTED_FEATURE_RESULT", packet["job"]["source_excerpt"])

    def test_valid_cross_provider_result_replenishes_openai_once_by_content_identity(self) -> None:
        build_commit = "a" * 40
        release = self.root / "releases" / build_commit
        schema_path = release / "schemas/openai/assistive_candidate.schema.json"
        schema_path.parent.mkdir(parents=True)
        schema_value = {"type": "object"}
        schema_path.write_text(json.dumps(schema_value), encoding="utf-8")
        registry = release / "configs/openai_task_registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "tasks": {
                        "assistive_model_evaluation": {
                            "jira_unit": "POST-SUBTASK-161",
                            "candidate_destination": "CANDIDATE",
                            "allowed_models": ["gpt-5.6-luna"],
                            "allocation_by_model": {"gpt-5.6-luna": "CROSS_MODEL_QA"},
                        },
                        "gamebook_schema_mapping": {
                            "jira_unit": "POST-SUBTASK-168",
                            "candidate_destination": "REVIEW",
                            "allowed_models": ["gpt-5.6-terra"],
                            "allocation_by_model": {"gpt-5.6-terra": "TERRA_COMPLEX"},
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        provider_result = {
            "schema_version": 1,
            "artifact_type": "GOVERNED_PROVIDER_CANDIDATE_RESULT",
            "provider": "openrouter",
            "work_unit_id": "AUTO-OR-real-bas-work",
            "attempt_id": "attempt-1",
            "remote_identity": "generation-1",
            "authority": "CANDIDATE_ONLY",
            "disposition": "REVIEW_ONLY",
            "validation_errors": [],
            "actual_cost_usd": "0.001",
            "resource": {"provider_calls": 1},
            "result": {
                "authority": "CANDIDATE_ONLY",
                "canonical_writes": 0,
                "protected_decisions": 0,
                "candidate": "review this evidence-backed reconciliation ranking",
            },
        }
        report_data = canonical_json_bytes(provider_result) + b"\n"
        report_sha256 = hashlib.sha256(report_data).hexdigest()
        report = (
            self.root
            / "orchestrator/evidence/provider-results/sha256"
            / report_sha256
            / "report.json"
        )
        report.parent.mkdir(parents=True)
        report.write_bytes(report_data)
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=self.root / "provider-work/requests",
                release_root=release,
                build_commit=build_commit,
                openai_task_registry_path=registry,
            ),
        )
        demand = {
            "providers": {
                "openai_direct": {"unmet": True, "active_execution_packets": 0}
            }
        }

        first = refresher._materialize_continuous_openai_work(demand)
        second = refresher._materialize_continuous_openai_work(demand)

        self.assertEqual(1, len(first))
        self.assertEqual(first, second)
        packet = json.loads(Path(first[0]["packet_path"]).read_text(encoding="utf-8"))
        self.assertEqual("assistive_model_evaluation", packet["job"]["task_name"])
        self.assertEqual("continuous-cross-provider-candidate-qa-v1", packet["job"]["prompt_version"])
        self.assertEqual(report_sha256, packet["job"]["source_capture_sha256"])
        self.assertEqual("gpt-5.6-luna", packet["job"]["model"])
        self.assertEqual("low", packet["job"]["reasoning_effort"])
        self.assertEqual("CANDIDATE", packet["job"]["destination"])
        self.assertEqual(
            "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES", packet["authority"]
        )
        self.assertNotIn("remote_identity", packet["job"]["source_excerpt"])
        work_unit_id = "AUTO-OAI-" + first[0]["packet_sha256"][:20]
        with patch.object(
            self.state,
            "work_unit_states",
            side_effect=lambda identities: {
                identity: "CLOSED" for identity in identities if identity == work_unit_id
            },
        ):
            self.assertEqual([], refresher._materialize_continuous_openai_work(demand))
        watermarks = refresher._producer_watermarks(self.now)
        self.assertEqual(
            1,
            watermarks["sources"]["provider_result_queue"]["eligible_file_count"],
        )
        self.assertEqual(
            "PASS", watermarks["sources"]["provider_result_queue"]["scan_status"]
        )

    def test_cross_provider_openai_feed_rejects_self_loops_and_invalid_authority(self) -> None:
        build_commit = "a" * 40
        release = self.root / "releases" / build_commit
        schema = release / "schemas/openai/assistive_candidate.schema.json"
        schema.parent.mkdir(parents=True)
        schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
        registry = release / "configs/openai_task_registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "tasks": {
                        "assistive_model_evaluation": {
                            "jira_unit": "POST-SUBTASK-161",
                            "candidate_destination": "CANDIDATE",
                            "allowed_models": ["gpt-5.6-luna"],
                            "allocation_by_model": {"gpt-5.6-luna": "CROSS_MODEL_QA"},
                        },
                        "gamebook_schema_mapping": {
                            "jira_unit": "POST-SUBTASK-168",
                            "candidate_destination": "REVIEW",
                            "allowed_models": ["gpt-5.6-terra"],
                            "allocation_by_model": {"gpt-5.6-terra": "TERRA_COMPLEX"},
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        result_root = self.root / "orchestrator/evidence/provider-results/sha256"
        for provider, authority, validation_errors in (
            ("openai_direct", "CANDIDATE_ONLY", []),
            ("openrouter", "CANONICAL", []),
            ("cursor", "CANDIDATE_ONLY", ["INVALID_RESULT"]),
        ):
            value = {
                "schema_version": 1,
                "artifact_type": "GOVERNED_PROVIDER_CANDIDATE_RESULT",
                "provider": provider,
                "work_unit_id": f"unit-{provider}",
                "authority": authority,
                "disposition": "REVIEW_ONLY",
                "validation_errors": validation_errors,
                "result": {
                    "authority": "CANDIDATE_ONLY",
                    "canonical_writes": 0,
                    "protected_decisions": 0,
                },
            }
            data = canonical_json_bytes(value) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            path = result_root / digest / "report.json"
            path.parent.mkdir(parents=True)
            path.write_bytes(data)
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=self.root / "provider-work/requests",
                release_root=release,
                build_commit=build_commit,
                openai_task_registry_path=registry,
            ),
        )
        packets = refresher._materialize_continuous_openai_work(
            {
                "providers": {
                    "openai_direct": {"unmet": True, "active_execution_packets": 0}
                }
            }
        )
        self.assertEqual([], packets)

    def test_one_continuous_producer_failure_does_not_block_other_producers(self) -> None:
        cursor_packet = {
            "provider": "cursor",
            "source_relative_path": "source.py",
            "source_sha256": "1" * 64,
            "packet_path": str(self.root / "candidate.json"),
            "packet_sha256": "2" * 64,
        }
        with (
            patch.object(
                self.refresher,
                "_materialize_continuous_openrouter_work",
                side_effect=RuntimeError("malformed exact packet"),
            ),
            patch.object(
                self.refresher,
                "_materialize_continuous_cursor_work",
                return_value=[cursor_packet],
            ),
            patch.object(self.refresher, "_materialize_continuous_cpu_work", return_value=[]),
            patch.object(self.refresher, "_materialize_continuous_bge_work", return_value=[]),
            patch.object(self.refresher, "_materialize_continuous_openai_work", return_value=[]),
        ):
            report = self.refresher.refresh(now=self.now)
        snapshot = json.loads(Path(report["snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual([cursor_packet], snapshot["continuous_packets"])
        producer_findings = [
            item for item in snapshot["provider_work_findings"]
            if item.get("disposition") == "EXACT_PRODUCER_FAILED_UNRELATED_PRODUCERS_CONTINUE"
        ]
        self.assertEqual(1, len(producer_findings))
        self.assertEqual("openrouter", producer_findings[0]["provider"])

    def test_semantic_refresh_configuration_is_all_or_none(self) -> None:
        with self.assertRaisesRegex(ValueError, "RUNTIME_INVENTORY_SEMANTIC_REFRESH_CONFIG_INCOMPLETE"):
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                semantic_materializer_path=self.root / "semantic.py",
            ).validate()

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
        observed_compiler_commits: list[str] = []

        def capture_cursor_snapshot(snapshot, _demand):
            observed_compiler_commits.append(refresher._snapshot_release_commit(snapshot))
            return []

        with patch.object(
            refresher,
            "_materialize_continuous_cursor_work",
            side_effect=capture_cursor_snapshot,
        ):
            report = refresher.refresh(now=self.now)
        snapshot = json.loads(Path(report["snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual([build_commit], observed_compiler_commits)
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
        self.assertEqual(2, status["useful_work_summary"]["raw_activity"])
        self.assertEqual(0, status["useful_work_summary"]["downstream_consumed_outputs"])
        self.assertEqual(0, status["useful_work_summary"]["accepted_useful_outputs"])
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
            "PACKET_QUARANTINED_UNRELATED_PROVIDER_WORK_CONTINUES",
            snapshot["provider_work_findings"][0]["disposition"],
        )
        self.assertFalse((provider_root / "invalid.json").exists())
        self.assertTrue(Path(snapshot["provider_work_findings"][0]["quarantine_path"]).is_file())

    def test_byte_identical_provider_packets_share_one_active_capacity_slot(self) -> None:
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        packet = {
            "schema_version": 1,
            "provider": "remote_cpu_worker",
            "task": "LINE_HASH_MANIFEST",
            "task_format": CPU_LINE_HASH_TASK_FORMAT,
            "jira_unit": "BAT-563",
            "schema_sha256": CPU_LINE_HASH_SCHEMA_SHA256,
            "source_hashes": ["5" * 64],
            "dependencies": [],
            "pre_routing_effort_points": 3,
            "scope": "One real bounded historical manifest tranche",
            "payload": {"lines": ["season=2022", "status=complete"]},
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        data = canonical_json_bytes(packet) + b"\n"
        (provider_root / "duplicate-a.json").write_bytes(data)
        (provider_root / "duplicate-b.json").write_bytes(data)
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
        discovered = refresher._discover_provider_work(
            json.loads(self.current.read_text(encoding="utf-8")), self.now
        )
        self.assertEqual(1, len(discovered))
        self.assertTrue(discovered[0][0].work_unit_id.startswith("AUTO-CPU-LINE-HASH-"))

    def test_duplicate_packet_flood_does_not_hide_a_later_distinct_packet(self) -> None:
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        packet = {
            "schema_version": 1,
            "provider": "remote_cpu_worker",
            "task": "LINE_HASH_MANIFEST",
            "task_format": CPU_LINE_HASH_TASK_FORMAT,
            "jira_unit": "BAT-563",
            "schema_sha256": CPU_LINE_HASH_SCHEMA_SHA256,
            "source_hashes": ["5" * 64],
            "dependencies": [],
            "pre_routing_effort_points": 3,
            "scope": "One real bounded historical manifest tranche",
            "payload": {"lines": ["season=2022", "status=complete"]},
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        duplicate_data = canonical_json_bytes(packet) + b"\n"
        (provider_root / "z-duplicate.json").write_bytes(duplicate_data)
        (provider_root / "y-duplicate.json").write_bytes(duplicate_data)
        distinct_packet = {
            **packet,
            "source_hashes": ["6" * 64],
            "payload": {"lines": ["season=2023", "status=complete"]},
        }
        (provider_root / "a-distinct.json").write_bytes(
            canonical_json_bytes(distinct_packet) + b"\n"
        )
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

        with patch(
            "aggie_analytics.assistive_plane.inventory_runtime.MAX_PROVIDER_WORK_SCAN_UNITS",
            2,
        ):
            discovered = refresher._discover_provider_work(
                json.loads(self.current.read_text(encoding="utf-8")), self.now
            )

        self.assertEqual(2, len(discovered))
        self.assertEqual(2, len({item[0].identity for item in discovered}))

    def test_stale_cursor_packet_is_terminalized_and_replaced_for_current_release(self) -> None:
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        release_commit = "9" * 40
        stale_commit = "8" * 40
        release_root = self.root / "releases" / release_commit
        review_source = release_root / "src/aggie_analytics/assistive_plane/inventory_runtime.py"
        review_source.parent.mkdir(parents=True)
        review_source.write_text("# current release review target\n", encoding="utf-8")
        policy_path = self.root / "policy.json"
        policy_path.write_text(
            json.dumps(
                {
                    "execution_minimums": {
                        "cursor": {
                            "new_controller_routed_units": 10,
                            "effort_points": 40,
                            "accepted_useful": 6,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        semantic_module_path = self.root / "semantic.py"
        semantic_module_path.write_text("# not loaded by this focused test\n", encoding="utf-8")
        readiness_path = self.root / "readiness.json"
        readiness_path.write_text("{}", encoding="utf-8")
        external_assistive_root = self.root / "external/assistive"
        external_assistive_root.mkdir(parents=True)
        stale_packet = {
            "schema_version": 1,
            "provider": "cursor",
            "task_format": CURSOR_TASK_FORMAT,
            "jira_unit": "POST-SUBTASK-202",
            "schema_sha256": CURSOR_SCHEMA_SHA256,
            "source_hashes": ["1" * 64, sha256_value({"release_commit": stale_commit})],
            "dependencies": [],
            "pre_routing_effort_points": 5,
            "scope": "Stale exact-base Cursor review",
            "repository_url": "https://github.com/KevinSGarrett/BatteredAggieSyndrome.git",
            "starting_ref": stale_commit,
            "base_commit": stale_commit,
            "model": "gpt-5.3-codex",
            "reasoning": "medium",
            "fast": False,
            "work_on_current_branch": False,
            "auto_create_pr": False,
            "max_reservation_usd": "2.00",
            "prompt": "Review the stale release without making changes.",
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        stale_data = canonical_json_bytes(stale_packet) + b"\n"
        stale_digest = hashlib.sha256(stale_data).hexdigest()
        stale_path = provider_root / "continuous/sha256" / stale_digest[:2] / f"{stale_digest}.json"
        stale_path.parent.mkdir(parents=True)
        stale_path.write_bytes(stale_data)
        stale_work_unit_id = "AUTO-CURSOR-" + stale_digest[:20]
        self.state.register_work_unit(
            work_unit_id=stale_work_unit_id,
            identity_sha256="2" * 64,
            jira_identity="POST-SUBTASK-202",
            effort_points=5,
            actor="test",
            now=self.now,
        )
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                provider_work_root=provider_root,
                release_root=release_root,
                build_commit=release_commit,
                semantic_materializer_path=semantic_module_path,
                semantic_policy_path=policy_path,
                semantic_readiness_path=readiness_path,
                external_assistive_root=external_assistive_root,
            ),
        )
        snapshot = {
            "git": {"deployed_head": release_commit},
            "external_evidence": {
                "cursor": {
                    "present": True,
                    "unique_jobs": 10,
                    "settled_usd": "1.00",
                    "manifest_sha256": "3" * 64,
                }
            },
        }

        self.assertEqual([], refresher._discover_provider_work(snapshot, self.now))
        self.assertFalse(stale_path.exists())
        self.assertEqual(
            "QUARANTINED",
            self.state.work_unit_states({stale_work_unit_id})[stale_work_unit_id],
        )
        finding = refresher._provider_packet_findings[0]
        self.assertEqual(stale_work_unit_id, finding["work_unit_id"])
        self.assertEqual("QUARANTINED", finding["work_unit_state_disposition"])

        demand = refresher._operational_demand(
            snapshot,
            [
                {
                    "work_unit_id": stale_work_unit_id,
                    "disposition": "CURSOR",
                    "provider": "cursor",
                }
            ],
            {stale_work_unit_id: "ATOMIC_EXECUTABLE"},
        )
        self.assertEqual(0, demand["providers"]["cursor"]["active_execution_packets"])
        replacement = refresher._materialize_continuous_cursor_work(snapshot, demand)
        self.assertEqual(1, len(replacement))
        replacement_packet = json.loads(
            Path(replacement[0]["packet_path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(release_commit, replacement_packet["base_commit"])
        self.assertNotEqual(stale_digest, replacement[0]["packet_sha256"])
        admitted = refresher._discover_provider_work(
            snapshot, self.now + timedelta(seconds=1)
        )
        self.assertEqual(1, len(admitted))
        self.assertTrue(admitted[0][0].work_unit_id.startswith("AUTO-CURSOR-"))

    def test_execution_packet_revision_identity_binds_source_commit_and_supersession(self) -> None:
        packet_root = self.root / "packets"
        packet_root.mkdir()
        old_commit = "8" * 40
        current_commit = "9" * 40

        def reference(commit: str, scope: str) -> tuple[str, dict[str, object]]:
            packet = {
                "schema_version": 1,
                "provider": "cursor",
                "task_format": CURSOR_TASK_FORMAT,
                "jira_unit": "POST-SUBTASK-202",
                "source_jira_unit": "BAT-479",
                "base_commit": commit,
                "starting_ref": commit,
                "scope": scope,
            }
            data = canonical_json_bytes(packet) + b"\n"
            digest = hashlib.sha256(data).hexdigest()
            path = packet_root / f"{digest}.json"
            path.write_bytes(data)
            work_unit_id = "AUTO-CURSOR-" + digest[:20]
            metadata = RuntimeInventoryRefresher._execution_packet_revision_metadata(
                {"packet_path": str(path), "packet_sha256": digest},
                current_commit,
            )
            return work_unit_id, metadata

        old_id, old_reference = reference(old_commit, "review before main transition")
        new_id, new_reference = reference(current_commit, "review after main transition")
        duplicate_id, duplicate_reference = reference(
            current_commit, "review after main transition"
        )

        self.assertEqual(old_commit, old_reference["source_commit"])
        self.assertEqual(current_commit, new_reference["source_commit"])
        self.assertEqual(new_id, duplicate_id)
        self.assertEqual(new_reference, duplicate_reference)
        self.assertEqual(
            old_reference["revision_family_identity"],
            new_reference["revision_family_identity"],
        )

        supersessions = RuntimeInventoryRefresher._derive_revision_supersessions(
            execution_packets={old_id: old_reference, new_id: new_reference},
            execution_states={old_id: "CLOSED"},
            release_commit=current_commit,
            prior=[],
            observed_at="2026-08-14T07:31:30Z",
        )
        self.assertEqual(1, len(supersessions))
        self.assertEqual(old_id, supersessions[0]["superseded_work_unit_id"])
        self.assertEqual(new_id, supersessions[0]["superseding_work_unit_id"])
        self.assertEqual(old_commit, supersessions[0]["superseded_source_commit"])
        self.assertEqual(current_commit, supersessions[0]["superseding_source_commit"])
        self.assertEqual(
            supersessions,
            RuntimeInventoryRefresher._derive_revision_supersessions(
                execution_packets={old_id: old_reference, new_id: new_reference},
                execution_states={old_id: "CLOSED"},
                release_commit=current_commit,
                prior=supersessions,
                observed_at="2026-08-14T08:00:00Z",
            ),
        )

    def test_prior_release_packet_does_not_rewrite_immutable_pre_routing_decision(self) -> None:
        current_commit = "a" * 40
        prior_commit = "8" * 40
        packet = {
            "schema_version": 1,
            "provider": "openrouter",
            "task_format": OPENROUTER_TASK_FORMAT,
            "jira_unit": "BAT-560",
            "schema_sha256": "1" * 64,
            "base_commit": prior_commit,
            "scope": "Prior-release packet retained only for durable reconciliation",
        }
        packet_bytes = canonical_json_bytes(packet) + b"\n"
        packet_sha256 = hashlib.sha256(packet_bytes).hexdigest()
        packet_path = self.root / "prior-release-packet.json"
        packet_path.write_bytes(packet_bytes)
        work_unit_id = "AUTO-OR-" + packet_sha256[:20]
        unit = {
            "work_unit_id": work_unit_id,
            "jira_unit": "BAT-560",
            "task_format": OPENROUTER_TASK_FORMAT,
            "schema_sha256": "1" * 64,
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            "source_hashes": [packet_sha256],
            "dependencies": [],
            "pre_routing_effort_points": 3,
            "scope": packet["scope"],
        }
        unit["identity"] = hashlib.sha256(
            canonical_json_bytes({key: value for key, value in unit.items() if key != "identity"})
        ).hexdigest()
        base = json.loads(self.current.read_text(encoding="utf-8"))
        base["work_units"].append(unit)
        base["work_unit_roles"][work_unit_id] = ATOMIC_EXECUTABLE
        base["route_decisions"].append(
            {
                "work_unit_id": work_unit_id,
                "work_unit_identity": unit["identity"],
                "disposition": "OPENROUTER",
                "provider": "openrouter",
                "model": "qwen/qwen3-coder-next",
                "reason": "EXACT_ROUTE_READY_AND_GRANULAR_PACKET_MATERIALIZED",
                "decided_at": self.now.isoformat().replace("+00:00", "Z"),
            }
        )
        base["execution_packets"] = {
            work_unit_id: {
                "packet_path": str(packet_path),
                "packet_sha256": packet_sha256,
                "source_commit": prior_commit,
            }
        }
        role_units = [
            ReadyWorkUnit(**{key: value for key, value in item.items() if key != "identity"})
            for item in base["work_units"]
        ]
        base["work_unit_role_validation"] = validate_work_unit_roles(
            role_units, base["work_unit_roles"]
        )
        self.current.write_bytes(canonical_json_bytes(base) + b"\n")
        existing_decision = self.state.record_pre_routing_decision(
            decision={
                "work_unit_id": work_unit_id,
                "jira_identity": "BAT-560",
                "repository_identity": "KevinSGarrett/BatteredAggieSyndrome",
                "source_commit": prior_commit,
                "task_category": OPENROUTER_TASK_FORMAT,
                "effort_points": 3,
                "candidate_routes": ["openrouter"],
                "selected_route": "openrouter",
                "route_identity": sha256_value({"legacy_route_identity": packet_sha256}),
                "budget_admission": "PROVIDER_BUDGET_ADMITTED",
                "packet_identity": packet_sha256,
                "lease_identity": None,
                "disposition": "ROUTED_TO_ASSISTIVE_PLANE",
                "reason_code": "EXACT_ROUTE_READY_AND_GRANULAR_PACKET_MATERIALIZED",
                "evidence_sha256": unit["identity"],
                "discovered_at": self.now.isoformat().replace("+00:00", "Z"),
            },
            now=self.now,
        )

        refreshed = self.refresher.refresh(now=self.now + timedelta(minutes=1))

        self.assertEqual("PASS", refreshed["result"])
        with self.state.transaction() as connection:
            decisions = connection.execute(
                "SELECT decision_sha256 FROM pre_routing_decisions WHERE work_unit_id=?",
                (work_unit_id,),
            ).fetchall()
        self.assertEqual([existing_decision], [row["decision_sha256"] for row in decisions])
        snapshot = json.loads(Path(refreshed["snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual(current_commit, snapshot["git"]["head"])
        self.assertEqual(
            prior_commit,
            snapshot["execution_packets"][work_unit_id]["source_commit"],
        )

    def test_prior_release_review_debt_does_not_suppress_current_release_generation(self) -> None:
        policy_path = self.root / "policy.json"
        readiness_path = self.root / "readiness.json"
        materializer_path = self.root / "materializer.py"
        external_assistive_root = self.root / "external/assistive"
        external_assistive_root.mkdir(parents=True)
        readiness_path.write_text("{}", encoding="utf-8")
        materializer_path.write_text("# test fixture\n", encoding="utf-8")
        policy_path.write_text(
            json.dumps(
                {
                    "execution_minimums": {
                        "cursor": {
                            "new_controller_routed_units": 10,
                            "effort_points": 40,
                            "accepted_useful": 6,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=self.current,
                snapshot_root=self.root / "inventory/runtime",
                packet_root=self.root / "orchestrator",
                manifests_root=self.manifests,
                semantic_materializer_path=materializer_path,
                semantic_policy_path=policy_path,
                semantic_readiness_path=readiness_path,
                external_assistive_root=external_assistive_root,
            ),
        )
        lifetime = {
            "cursor": {
                "closed_runs": 1,
                "closed_effort_points": 5,
                "pending_downstream_review": 1,
                "useful_work": {"accepted_useful_outputs": 0},
            }
        }
        current_release = {
            "cursor": {
                "closed_runs": 0,
                "closed_effort_points": 0,
                "pending_downstream_review": 0,
                "review_dispositions": {},
            }
        }
        with patch.object(
            self.state,
            "provider_run_summary",
            side_effect=[lifetime, current_release],
        ):
            demand = refresher._operational_demand(
                {"external_evidence": {"cursor": {"unique_jobs": 1}}},
                [],
                {},
            )
        self.assertEqual(0, demand["providers"]["cursor"]["pending_review_results"])
        self.assertIn("cursor", demand["unmet_without_packets"])

    def test_stale_cursor_review_cannot_authorize_current_release_implementation(self) -> None:
        old_commit = "8" * 40
        current_commit = "9" * 40
        review = {
            "task_format": CURSOR_TASK_FORMAT,
            "source_jira_unit": "BAT-479",
            "base_commit": old_commit,
            "starting_ref": old_commit,
        }
        self.assertFalse(
            RuntimeInventoryRefresher._cursor_review_matches_release(
                review, current_commit
            )
        )
        review["base_commit"] = current_commit
        review["starting_ref"] = current_commit
        self.assertTrue(
            RuntimeInventoryRefresher._cursor_review_matches_release(
                review, current_commit
            )
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
            refresher._discover_provider_work_batch(current_payload, self.now)

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
            refresher._discover_provider_work_batch(current_payload, self.now)

        current_payload["external_evidence"]["cpu_worker"]["qualifications"][0]["tasks"].append(
            "EXACT_TEXT_DEDUP"
        )
        packets[1]["task_format"] = CPU_LINE_HASH_TASK_FORMAT
        (provider_root / "cpu-text-1.json").write_bytes(canonical_json_bytes(packets[1]) + b"\n")
        with self.assertRaisesRegex(ValueError, "CPU_PROVIDER_PACKET_INVALID"):
            refresher._discover_provider_work_batch(current_payload, self.now)

    def test_cpu_line_hash_tranche_is_consumed_by_provenance_workflow(self) -> None:
        provider_root = self.root / "provider_work/requests"
        provider_root.mkdir(parents=True)
        packet = {
            "schema_version": 1,
            "provider": "remote_cpu_worker",
            "task": "LINE_HASH_MANIFEST",
            "task_format": CPU_LINE_HASH_TASK_FORMAT,
            "jira_unit": "BAT-563",
            "schema_sha256": CPU_LINE_HASH_SCHEMA_SHA256,
            "source_hashes": ["5" * 64, "6" * 64],
            "dependencies": [],
            "pre_routing_effort_points": 3,
            "scope": "Bounded historical provenance tranche",
            "downstream_consumer": "HISTORICAL_MANIFEST_PROVENANCE_AND_REPLAY_VALIDATION",
            "downstream_consumer_contract_version": CPU_LINE_HASH_DOWNSTREAM_CONSUMER_VERSION,
            "delegation_preference_reason": "BOUNDED_FIXED_FUNCTION_REMOTE_CPU_BATCH",
            "input_metrics": {"documents": 2, "records": 2, "bytes": 32},
            "payload": {"lines": ["season=2022", "status=complete"]},
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        packet_data = canonical_json_bytes(packet) + b"\n"
        packet_digest = hashlib.sha256(packet_data).hexdigest()
        (provider_root / "line-hash.json").write_bytes(packet_data)
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
        refresher.refresh(now=self.now)
        key_path = self.root / "consumer-secret.bin"
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
            client.last_local_replay_seconds = 0.002
            return response, destination

        downstream_root = self.root / "reconciliation/assistive_consumed"
        scheduler = InventoryScheduler(
            self.state,
            SchedulerConfig(
                inventory_current_path=self.current,
                evidence_root=self.root / "runtime/evidence",
                inventory_max_age_seconds=300,
                cycle_interval_seconds=3600,
                owner_id="consumer-controller-test",
                cpu_worker_endpoint="https://comfy-v4-cpu-01.tail9b05ab.ts.net",
                cpu_worker_storage_root=self.root / "cpu_worker",
                cpu_worker_signing_key_path=key_path,
                downstream_artifact_root=downstream_root,
                max_dispatch_per_cycle=3,
            ),
        )
        legacy_packet = dict(packet)
        legacy_packet.pop("downstream_consumer_contract_version")
        self.assertIsNone(
            scheduler._consume_cpu_line_hash_result(
                packet=legacy_packet,
                response={"result": {"line_count": 0, "line_sha256": []}},
                work_unit_id="legacy-work-unit",
                attempt_id="legacy-attempt",
                validation_sha256="0" * 64,
            )
        )
        with patch.object(CpuWorkerClient, "submit", local_submit):
            report = scheduler.evaluate(now=self.now)
        work_unit_id = "AUTO-CPU-LINE-HASH-" + packet_digest[:20]
        dispatched = next(item for item in report["dispatched"] if item["work_unit_id"] == work_unit_id)
        self.assertEqual("ACCEPTED", dispatched["review_disposition"])
        consumption = dispatched["downstream_consumption"]
        self.assertEqual(2, consumption["records"])
        self.assertTrue(Path(consumption["artifact_path"]).is_file())
        self.assertEqual(
            consumption["artifact_sha256"],
            hashlib.sha256(Path(consumption["artifact_path"]).read_bytes()).hexdigest(),
        )
        status = self.state.status()
        self.assertEqual(1, status["useful_work_summary"]["downstream_consumed_outputs"])
        self.assertEqual(0, status["useful_work_summary"]["accepted_useful_outputs"])
        self.assertEqual(0.0, status["useful_work_summary"]["measured_net_time_saved_seconds"])
        watchdog = ReadOnlyWatchdog(self.state.database).inspect(now=self.now + timedelta(seconds=2))
        self.assertEqual(1, watchdog["useful_work_summary"]["downstream_consumed_output"])
        self.assertEqual(0, watchdog["useful_work_summary"]["accepted_useful_offload"])
        with closing(self.state.connect()) as connection:
            useful = connection.execute(
                "SELECT direct_baseline_seconds,orchestration_seconds FROM useful_work_evidence "
                "WHERE work_unit_id=?",
                (work_unit_id,),
            ).fetchone()
        self.assertEqual(0.002, useful["direct_baseline_seconds"])
        self.assertGreaterEqual(useful["orchestration_seconds"], 0.0)

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
                refresher._discover_provider_work_batch(current_payload, self.now)

    def test_closed_content_addressed_packet_skips_stale_route_validation(self) -> None:
        current_payload = json.loads(self.current.read_text(encoding="utf-8"))
        current_payload["external_evidence"]["openai"] = {
            "present": True,
            "manifest_sha256": "1" * 64,
        }
        provider_root = self.root / "provider_work/requests/sha256"
        packet = {
            "schema_version": 1,
            "provider": "openai_direct",
            "task_format": "governed_openai_candidate_v1",
            "jira_unit": "POST-SUBTASK-168",
            "schema_sha256": "5" * 64,
            "source_hashes": ["6" * 64],
            "job": {"model": "gpt-5-nano"},
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        data = canonical_json_bytes(packet) + b"\n"
        digest = hashlib.sha256(data).hexdigest()
        provider_root.mkdir(parents=True)
        (provider_root / f"{digest}.json").write_bytes(data)
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

        closed = {"AUTO-OAI-" + digest[:20]: "CLOSED"}
        current_payload["external_evidence"]["openai"] = {"present": False}
        with patch.object(self.state, "work_unit_states", return_value=closed):
            self.assertEqual([], refresher._discover_provider_work(current_payload, self.now))

    def test_active_content_addressed_packet_still_fails_closed(self) -> None:
        current_payload = json.loads(self.current.read_text(encoding="utf-8"))
        provider_root = self.root / "provider_work/requests/sha256"
        provider_root.mkdir(parents=True)
        packet = {
            "schema_version": 1,
            "provider": "openai_direct",
            "task_format": "governed_openai_candidate_v1",
            "jira_unit": "POST-SUBTASK-168",
            "schema_sha256": "5" * 64,
            "source_hashes": ["6" * 64],
            "job": {"model": "gpt-5-nano"},
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
        }
        data = canonical_json_bytes(packet) + b"\n"
        digest = hashlib.sha256(data).hexdigest()
        (provider_root / f"{digest}.json").write_bytes(data)
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

        with patch.object(self.state, "work_unit_states", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "PROVIDER_EXACT_ROUTE_NOT_READY"):
                refresher._discover_provider_work_batch(current_payload, self.now)

    def test_content_addressed_packet_hash_mismatch_fails_closed(self) -> None:
        current_payload = json.loads(self.current.read_text(encoding="utf-8"))
        provider_root = self.root / "provider_work/requests/sha256"
        provider_root.mkdir(parents=True)
        (provider_root / f"{'0' * 64}.json").write_text("{}\n", encoding="utf-8")
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

        self.assertEqual([], refresher._discover_provider_work(current_payload, self.now))
        self.assertIn(
            "CONTENT_ADDRESS_MISMATCH",
            refresher._provider_packet_findings[0]["finding"],
        )
        self.assertTrue(Path(refresher._provider_packet_findings[0]["quarantine_path"]).is_file())

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
            "downstream_consumer_contract_version": BGE_DOWNSTREAM_CONSUMER_VERSION,
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
                if self.provider == "ollama_local":
                    result = {
                        "schema_version": 1,
                        "artifact_type": "BGE_M3_CANDIDATE_RETRIEVAL",
                        "query_sha256": hashlib.sha256(b"Texas A&M").hexdigest(),
                        "rankings": [{"candidate_id": "a", "score": 0.987}],
                        "model": "bge-m3:latest",
                        "model_digest": "7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab",
                        "task_format": "embedding_dedup_semantic_candidate_retrieval",
                        "authority": "CANDIDATE_ONLY",
                        "canonical_writes": 0,
                        "protected_decisions": 0,
                    }
                else:
                    result = {
                        "authority": "CANDIDATE_ONLY",
                        "canonical_writes": 0,
                        "protected_decisions": 0,
                        "provider": self.provider,
                    }
                return ProviderAdapterResult(
                    remote_identity=f"{self.provider}-run",
                    result=result,
                    disposition="REVIEW_ONLY", validation_errors=(), actual_cost_usd=self.cost,
                    resource={"tokens": 17},
                )

        scheduler = InventoryScheduler(self.state, SchedulerConfig(
            inventory_current_path=self.current, evidence_root=self.root / "runtime/evidence",
            inventory_max_age_seconds=300, cycle_interval_seconds=3600,
            owner_id="provider-controller-test", max_dispatch_per_cycle=2,
            downstream_artifact_root=self.root / "reconciliation/assistive_consumed",
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
            downstream = connection.execute(
                "SELECT disposition,downstream_consumer,changed_project_artifact,"
                "net_time_saved_seconds FROM downstream_review_dispositions"
            ).fetchall()
            self.assertEqual(1, len(downstream))
            self.assertEqual("UNUSED", downstream[0]["disposition"])
            self.assertEqual("BGE_RECONCILIATION_REVIEW_ROUTING", downstream[0]["downstream_consumer"])
            self.assertEqual(0, downstream[0]["changed_project_artifact"])
            self.assertEqual(0.0, downstream[0]["net_time_saved_seconds"])
        artifacts = list(
            (self.root / "reconciliation/assistive_consumed/bge-reconciliation-review-routing/sha256")
            .rglob("report.json")
        )
        self.assertEqual(1, len(artifacts))

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
            refresher._discover_provider_work_batch(current_payload, self.now)
        current_payload["deployed_release"]["build_commit"] = "a" * 40

        current_payload["external_evidence"]["openrouter"]["routes"][0]["budget_remaining_usd"] = "0.00"
        with self.assertRaisesRegex(RuntimeError, "EXACT_ROUTE_NOT_READY"):
            refresher._discover_provider_work_batch(current_payload, self.now)

        packet["base_commit"] = "b" * 40
        packet["identity_hashes"]["source_sha256"] = sha256_value(tuple(packet["source_hashes"]))
        (provider_root / "openrouter.json").write_bytes(canonical_json_bytes(packet) + b"\n")
        with self.assertRaisesRegex(ValueError, "OPENROUTER_PACKET_INVALID"):
            refresher._discover_provider_work_batch(current_payload, self.now)

        packet["base_commit"] = "a" * 40
        packet["identity_hashes"]["source_sha256"] = "9" * 64
        (provider_root / "openrouter.json").write_bytes(canonical_json_bytes(packet) + b"\n")
        current_payload["external_evidence"]["openrouter"]["routes"][0]["budget_remaining_usd"] = "1.23"
        with self.assertRaisesRegex(ValueError, "IDENTITY_HASH_MISMATCH"):
            refresher._discover_provider_work_batch(current_payload, self.now)

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
