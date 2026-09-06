"""Live checkpoint owners must come from confirmed processes, not saved PIDs."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from aggie_analytics.operations.contest_checkpoint_ledger import (
    T24H,
    T90M,
    build_lease_and_restart_plan,
    cycle27_live_owners,
)
from aggie_analytics.operations.cycle27_live_owner_inventory import (
    AM_T90_NATIONAL_DUPLICATE,
    build_live_owner_inventory,
    cutoff_from_checkpoint,
    sanitize_command_line,
)


class Cycle27LiveOwnerInventoryTests(unittest.TestCase):
    def test_hardcoded_cycle27_live_owners_are_empty(self) -> None:
        self.assertEqual(cycle27_live_owners(), [])

    def test_sanitize_drops_unrecognized_arguments(self) -> None:
        command = (
            r"powershell.exe -NoProfile -File C:\ops\run_t24h_cluster_capture.ps1 "
            r"-Checkpoint SAT_T24H_20260905T0800Z -TargetUtc 2026-09-05T07:15:00Z "
            r"-CutoffUtc 2026-09-05T08:00:00Z -ApiToken SECRET"
        )
        sanitized = sanitize_command_line(command)
        self.assertEqual(sanitized["script"], "run_t24h_cluster_capture.ps1")
        self.assertEqual(sanitized["checkpoint"], "SAT_T24H_20260905T0800Z")
        self.assertNotIn("SECRET", sanitized.values())
        self.assertNotIn("ApiToken", str(sanitized))

    def test_stale_saved_pid_is_not_an_owner(self) -> None:
        contests = [
            {
                "ncaa_contest_id": "6590890",
                "kickoff_bound_utc": "2026-09-05T16:00:00Z",
                "t24h_cutoff_utc": "2026-09-04T16:00:00Z",
                "t90m_cutoff_utc": "2026-09-05T14:30:00Z",
            }
        ]
        inventory = build_live_owner_inventory(
            processes=[
                {
                    "pid": 29368,
                    "command_line": (
                        "powershell.exe -File run_t90m_cluster_capture.ps1 "
                        "-Checkpoint SAT_T90M_20260905T1430Z "
                        "-TargetUtc 2026-09-05T13:45:00Z "
                        "-CutoffUtc 2026-09-05T14:30:00Z"
                    ),
                }
            ],
            contests=contests,
            now=datetime(2026, 9, 5, 2, 40, tzinfo=timezone.utc),
        )
        pids = inventory["do_not_kill_pids"]
        self.assertIn(29368, pids)
        self.assertNotIn(14180, pids)
        owner = inventory["current_owners"]["sat_t90m_20260905t1430z"]
        self.assertEqual(owner["primary_pid"], 29368)
        self.assertEqual(owner["liveness"], "CONFIRMED_PROCESS_COMMAND_LINE")

    def test_am_t90_national_duplicate_is_not_launched(self) -> None:
        inventory = build_live_owner_inventory(
            processes=[
                {
                    "pid": 99999,
                    "command_line": (
                        "powershell.exe -File run_t90m_cluster_capture.ps1 "
                        f"-Checkpoint {AM_T90_NATIONAL_DUPLICATE}"
                    ),
                },
                {
                    "pid": 21076,
                    "command_line": (
                        "powershell.exe -File run_scheduled_am_t90m_capture.ps1 "
                        "-TargetUtc 2026-09-05T20:45:00Z"
                    ),
                },
                {
                    "pid": 25740,
                    "command_line": "powershell.exe -File run_am_t90m_failover.ps1",
                },
            ]
        )
        self.assertEqual(
            inventory["skipped_am_t90_national_duplicates"][0]["pid"], 99999
        )
        am = inventory["current_owners"]["am_t90m"]
        self.assertEqual(am["primary_pid"], 21076)
        self.assertEqual(am["failover_pid"], 25740)
        names = [row["name"] for row in inventory["live_owners"]]
        self.assertNotIn(AM_T90_NATIONAL_DUPLICATE, names)

    def test_lease_plan_does_not_emit_stale_hardcoded_pids(self) -> None:
        contest = {
            "ncaa_contest_id": "6618941",
            "kickoff_bound_utc": "2026-09-06T08:00:00Z",
            "t24h_cutoff_utc": "2026-09-05T08:00:00Z",
            "t90m_cutoff_utc": "2026-09-06T06:30:00Z",
        }
        inventory = build_live_owner_inventory(
            processes=[
                {
                    "pid": 8836,
                    "command_line": (
                        "powershell.exe -File run_t24h_cluster_capture.ps1 "
                        "-Checkpoint SAT_T24H_20260905T0800Z"
                    ),
                }
            ],
            contests=[contest],
        )
        plan = build_lease_and_restart_plan(
            ledger={
                "contests": [contest],
                "sunday_monday_ownership_plan": {"sunday": [], "monday": []},
                "do_not_kill_pids": [],
            },
            now=datetime(2026, 9, 5, 2, 40, tzinfo=timezone.utc),
            live_inventory=inventory,
        )
        self.assertEqual(plan["do_not_kill_pids"], [8836])
        self.assertNotIn(28372, plan["do_not_kill_pids"])
        self.assertEqual(
            plan["current_owners"]["sat_t24h_20260905t0800z"]["primary_pid"], 8836
        )
        self.assertEqual(
            cutoff_from_checkpoint("SAT_T24H_20260905T0800Z"), "2026-09-05T08:00:00Z"
        )
        self.assertEqual(inventory["live_owners"][0]["kind"], T24H)
        self.assertEqual(inventory["live_owners"][0]["contest_ids"], ["6618941"])
        self.assertNotEqual(inventory["live_owners"][0]["kind"], T90M)
        self.assertEqual(
            plan["live_inventory_source"], "CONFIRMED_PROCESS_COMMAND_LINE"
        )


if __name__ == "__main__":
    unittest.main()
