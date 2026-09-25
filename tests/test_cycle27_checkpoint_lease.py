"""Cycle 27 atomic checkpoint lease: stale recovery, collision, expiry, START."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aggie_analytics.operations.checkpoint_lease import (
    acquire,
    lease_action_is_completion,
    recover_stale,
    release,
)


class CheckpointLeaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.common = dict(
            checkpoint="FRI_T90M_TEST",
            owner="CYCLE27_FRIDAY_T90M",
            run_id="run-a",
            ttl_seconds=60,
            heartbeat_seconds=10,
            pid=40708,
            lease_root=self.root,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def lock_path(self) -> Path:
        return self.root / "FRI_T90M_TEST" / "LOCK" / "lease.json"

    def test_acquire_is_start_not_completion(self) -> None:
        result = acquire(**self.common, pid_alive=lambda _pid: False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "ACQUIRED")
        self.assertFalse(lease_action_is_completion(result["action"]))
        self.assertFalse(result["lease"]["completion"])
        self.assertIn("start_identity", result["lease"])

    def test_live_collision_holds_existing_owner(self) -> None:
        first = acquire(**self.common, pid_alive=lambda _pid: True)
        self.assertEqual(first["action"], "ACQUIRED")
        second = acquire(
            **(self.common | {"run_id": "run-b", "pid": 41416}),
            pid_alive=lambda _pid: True,
        )
        self.assertFalse(second["ok"])
        self.assertEqual(second["action"], "HELD_BY_LIVE_OWNER")
        self.assertTrue(self.lock_path().is_file())

    def test_reused_pid_different_run_is_not_renew(self) -> None:
        acquire(**self.common, pid_alive=lambda _pid: True)
        reused = acquire(
            **(self.common | {"run_id": "run-b"}),
            pid_alive=lambda _pid: True,
        )
        self.assertFalse(reused["ok"])
        self.assertEqual(reused["action"], "HELD_BY_LIVE_OWNER")
        existing = json.loads(self.lock_path().read_text(encoding="utf-8"))
        self.assertEqual(existing["run_id"], "run-a")

    def test_same_run_renews(self) -> None:
        acquire(**self.common, pid_alive=lambda _pid: True)
        renewed = acquire(**self.common, pid_alive=lambda _pid: True)
        self.assertTrue(renewed["ok"])
        self.assertEqual(renewed["action"], "RENEWED")
        self.assertFalse(lease_action_is_completion(renewed["action"]))

    def test_stale_pid_is_not_deleted_unconditionally(self) -> None:
        acquire(**self.common, pid_alive=lambda _pid: True)
        payload = json.loads(self.lock_path().read_text(encoding="utf-8"))
        payload["expires_at_unix"] = 1
        self.lock_path().write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        stale = acquire(
            **(self.common | {"run_id": "run-b", "pid": 99999}),
            pid_alive=lambda _pid: False,
            now_unix=10_000,
        )
        self.assertFalse(stale["ok"])
        self.assertEqual(stale["action"], "STALE_OWNER_REQUIRES_VERIFIED_RECOVERY")
        self.assertTrue(stale["expired"])
        self.assertFalse(stale["pid_alive"])
        self.assertTrue(self.lock_path().is_file())
        denied = recover_stale(
            checkpoint="FRI_T90M_TEST",
            evidence={"verified_pid_dead": True, "verified_expired": True},
            lease_root=self.root,
        )
        self.assertEqual(denied["action"], "RECOVERY_DENIED_OPERATOR")
        self.assertTrue(self.lock_path().is_file())

    def test_expiry_with_live_pid_still_requires_recovery(self) -> None:
        acquire(**self.common, pid_alive=lambda _pid: True)
        payload = json.loads(self.lock_path().read_text(encoding="utf-8"))
        payload["expires_at_unix"] = 1
        self.lock_path().write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        expired = acquire(
            **(self.common | {"run_id": "run-b", "pid": 41416}),
            pid_alive=lambda _pid: True,
            now_unix=10_000,
        )
        self.assertEqual(expired["action"], "STALE_OWNER_REQUIRES_VERIFIED_RECOVERY")
        self.assertTrue(expired["pid_alive"])
        self.assertTrue(expired["expired"])
        self.assertTrue(self.lock_path().is_file())

    def test_verified_recovery_then_acquire(self) -> None:
        acquire(**self.common, pid_alive=lambda _pid: True)
        payload = json.loads(self.lock_path().read_text(encoding="utf-8"))
        payload["expires_at_unix"] = 1
        self.lock_path().write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        recovered = recover_stale(
            checkpoint="FRI_T90M_TEST",
            evidence={
                "verified_pid_dead": True,
                "verified_expired": True,
                "operator": "CYCLE27_CURSOR_AGENT",
            },
            lease_root=self.root,
        )
        self.assertEqual(recovered["action"], "RECOVERED_STALE")
        self.assertFalse(self.lock_path().exists())
        second = acquire(
            **(self.common | {"run_id": "run-b", "pid": 41416}),
            pid_alive=lambda _pid: False,
        )
        self.assertEqual(second["action"], "ACQUIRED")

    def test_release_owner_mismatch(self) -> None:
        acquire(**self.common, pid_alive=lambda _pid: True)
        refused = release(
            checkpoint="FRI_T90M_TEST",
            run_id="other",
            pid=40708,
            lease_root=self.root,
        )
        self.assertEqual(refused["action"], "REFUSED_RELEASE_OWNER_MISMATCH")
        self.assertTrue(self.lock_path().is_file())

    def test_default_root_is_injectable_not_required(self) -> None:
        with patch("aggie_analytics.operations.checkpoint_lease.LEASE_ROOT", self.root):
            result = acquire(
                checkpoint="X",
                owner="o",
                run_id="r",
                ttl_seconds=30,
                heartbeat_seconds=5,
                pid=1,
                pid_alive=lambda _pid: False,
            )
        self.assertEqual(result["action"], "ACQUIRED")
        self.assertTrue((self.root / "X" / "LOCK" / "lease.json").is_file())


if __name__ == "__main__":
    unittest.main()
