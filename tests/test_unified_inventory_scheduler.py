from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aggie_analytics.assistive_plane.controller_state import ControllerState
from aggie_analytics.assistive_plane.orchestration import (
    ReadyWorkInventory,
    ReadyWorkUnit,
    RouteDecision,
    RoutingDisposition,
)
from aggie_analytics.assistive_plane.scheduler_runtime import InventoryScheduler, SchedulerConfig


class UnifiedInventorySchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.current = self.root / "inventory/current/inventory.json"
        self.state = ControllerState(self.root / "runtime/state/orchestrator.sqlite3")
        self.state.initialize()
        self.now = datetime(2026, 8, 13, 1, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_inventory(self, disposition: RoutingDisposition, *, generated_at: datetime | None = None) -> str:
        unit = ReadyWorkUnit(
            work_unit_id="UNIT-1",
            jira_unit="BAT-560",
            task_format="candidate_review",
            schema_sha256="a" * 64,
            authority="CANDIDATE_ONLY",
            source_hashes=("b" * 64,),
            dependencies=(),
            pre_routing_effort_points=3,
            scope="review one bounded real evidence packet",
        )
        decision = RouteDecision(
            work_unit_id=unit.work_unit_id,
            work_unit_identity=unit.identity(),
            disposition=disposition,
            provider="openai" if disposition is RoutingDisposition.DIRECT_OPENAI else "codex_deterministic",
            model="GOVERNED_TASK_ROUTER" if disposition is RoutingDisposition.DIRECT_OPENAI else None,
            reason="test",
            decided_at=self.now.isoformat().replace("+00:00", "Z"),
        )
        validation = ReadyWorkInventory([unit], [decision]).validate()
        payload = {
            "schema_version": 1,
            "generated_at": (generated_at or self.now).isoformat().replace("+00:00", "Z"),
            "canonical_or_protected_authority": False,
            "git": {
                "head": "c" * 40,
                "origin_main": "c" * 40,
                "status_porcelain_sha256": hashlib.sha256(b"").hexdigest(),
            },
            "work_units": [asdict(unit)],
            "route_decisions": [{**asdict(decision), "disposition": decision.disposition.value}],
            "validation": validation,
        }
        data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.current.parent.mkdir(parents=True, exist_ok=True)
        self.current.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def scheduler(self, *, interval: int = 3600, max_age: int = 300) -> InventoryScheduler:
        return InventoryScheduler(
            self.state,
            SchedulerConfig(
                inventory_current_path=self.current,
                evidence_root=self.root / "runtime/evidence",
                inventory_max_age_seconds=max_age,
                cycle_interval_seconds=interval,
            ),
        )

    def test_ready_unit_records_honest_idle_cycle_without_provider_call(self) -> None:
        inventory_sha256 = self.write_inventory(RoutingDisposition.DIRECT_OPENAI)
        report = self.scheduler().evaluate(now=self.now)
        self.assertEqual("INCOMPLETE", report["result"])
        self.assertEqual(inventory_sha256, report["inventory_sha256"])
        self.assertEqual(1, report["eligible_units"])
        self.assertEqual(0, report["provider_calls"])
        self.assertTrue(report["cycle_recorded"])
        status = self.state.status()
        self.assertEqual(1, status["scheduler_cycles"])
        self.assertEqual(0, status["scheduler_dispatched_units"])
        self.assertEqual(1, status["active_idle_intervals"])
        second = self.scheduler().evaluate(now=self.now + timedelta(minutes=5))
        self.assertFalse(second["cycle_due"])
        self.assertEqual(1, self.state.status()["scheduler_cycles"])

    def test_nonrouteable_inventory_records_no_change_with_zero_calls(self) -> None:
        self.write_inventory(RoutingDisposition.CODEX_DETERMINISTIC)
        report = self.scheduler().evaluate(now=self.now)
        self.assertEqual("PASS", report["result"])
        self.assertTrue(report["no_change"])
        self.assertEqual(0, report["provider_calls"])
        status = self.state.status()
        self.assertEqual(1, status["scheduler_no_change_cycles"])
        self.assertEqual(0, status["active_idle_intervals"])

    def test_resolved_idle_interval_can_reopen_without_primary_key_collision(self) -> None:
        self.write_inventory(RoutingDisposition.DIRECT_OPENAI)
        self.scheduler().evaluate(now=self.now)
        with self.state.connect() as connection:
            first_idle = connection.execute(
                "SELECT idle_id,resolved_at FROM idle_intervals WHERE work_unit_id=? ORDER BY opened_at ASC",
                ("UNIT-1",),
            ).fetchone()
        self.assertIsNotNone(first_idle)
        self.assertIsNone(first_idle["resolved_at"])

        self.write_inventory(RoutingDisposition.CODEX_DETERMINISTIC)
        self.scheduler().evaluate(now=self.now + timedelta(minutes=1))
        with self.state.connect() as connection:
            resolved_first = connection.execute(
                "SELECT idle_id,resolved_at FROM idle_intervals WHERE work_unit_id=? ORDER BY opened_at ASC",
                ("UNIT-1",),
            ).fetchone()
        self.assertIsNotNone(resolved_first["resolved_at"])

        self.write_inventory(RoutingDisposition.DIRECT_OPENAI)
        reopened = self.scheduler().evaluate(now=self.now + timedelta(minutes=2))
        self.assertEqual("INCOMPLETE", reopened["result"])
        self.assertEqual(0, reopened["provider_calls"])
        with self.state.connect() as connection:
            rows = connection.execute(
                "SELECT idle_id,resolved_at FROM idle_intervals WHERE work_unit_id=? ORDER BY opened_at ASC",
                ("UNIT-1",),
            ).fetchall()
        self.assertEqual(2, len(rows))
        self.assertNotEqual(rows[0]["idle_id"], rows[1]["idle_id"])
        self.assertIsNotNone(rows[0]["resolved_at"])
        self.assertIsNone(rows[1]["resolved_at"])

    def test_stale_inventory_fails_closed_and_does_not_count_cycle(self) -> None:
        self.write_inventory(
            RoutingDisposition.DIRECT_OPENAI,
            generated_at=self.now - timedelta(minutes=10),
        )
        report = self.scheduler(max_age=300).evaluate(now=self.now)
        self.assertEqual("BLOCKED", report["result"])
        self.assertEqual("SCHEDULER_INVENTORY_STALE", report["finding"])
        self.assertEqual(0, report["provider_calls"])
        self.assertEqual(0, self.state.status()["scheduler_cycles"])

    def test_inventory_validation_mismatch_fails_closed(self) -> None:
        self.write_inventory(RoutingDisposition.DIRECT_OPENAI)
        payload = json.loads(self.current.read_text(encoding="utf-8"))
        payload["validation"]["effort_points_total"] = 8
        self.current.write_text(json.dumps(payload), encoding="utf-8")
        report = self.scheduler().evaluate(now=self.now)
        self.assertEqual("BLOCKED", report["result"])
        self.assertEqual("SCHEDULER_INVENTORY_VALIDATION_MISMATCH", report["finding"])

    def test_dirty_or_non_main_inventory_cannot_dispatch(self) -> None:
        self.write_inventory(RoutingDisposition.DIRECT_OPENAI)
        payload = json.loads(self.current.read_text(encoding="utf-8"))
        payload["git"]["status_porcelain_sha256"] = "d" * 64
        self.current.write_text(json.dumps(payload), encoding="utf-8")
        report = self.scheduler().evaluate(now=self.now)
        self.assertEqual("SCHEDULER_INVENTORY_DIRTY_WORKTREE", report["finding"])
        self.assertEqual(0, self.state.status()["scheduler_cycles"])


if __name__ == "__main__":
    unittest.main()
