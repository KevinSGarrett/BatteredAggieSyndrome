from __future__ import annotations

import unittest
from pathlib import Path

from tools.build_week_zero_2026_official_final_acquisition_blocked import (
    build_blocked_gate,
    canonical_hash,
)


class WeekZeroOfficialFinalAcquisitionBlockedTests(unittest.TestCase):
    def test_blocked_gate_is_deterministically_hashed(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        capture = {
            "capture_identity": "c" * 64,
            "issued_at_utc": "2026-08-30T00:00:00Z",
            "captures": [
                {
                    "game_date": "2026-08-27",
                    "state": "TECHNICALLY_UNAVAILABLE",
                    "failure_condition": "HTTP_403",
                    "source_uri": "https://stats.ncaa.org/contests/livestream_scoreboards",
                    "request_identity_sha256": "a" * 64,
                    "attempts": [{"attempt": 1, "condition": "HTTP_403", "route_id": "direct_http"}],
                },
                {
                    "game_date": "2026-08-28",
                    "state": "TECHNICALLY_UNAVAILABLE",
                    "failure_condition": "HTTP_403",
                    "source_uri": "https://stats.ncaa.org/contests/livestream_scoreboards",
                    "request_identity_sha256": "b" * 64,
                    "attempts": [{"attempt": 1, "condition": "HTTP_403", "route_id": "direct_http"}],
                },
                {
                    "game_date": "2026-08-29",
                    "state": "TECHNICALLY_UNAVAILABLE",
                    "failure_condition": "HTTP_403",
                    "source_uri": "https://stats.ncaa.org/contests/livestream_scoreboards",
                    "request_identity_sha256": "d" * 64,
                    "attempts": [{"attempt": 1, "condition": "HTTP_403", "route_id": "direct_http"}],
                },
            ],
        }
        gate = build_blocked_gate(
            repo_root=repo_root,
            data_root=Path(r"C:\BatteredAggieSyndrome.data"),
            capture_manifest=capture,
            issued_at_utc="2026-08-30T00:05:00Z",
        )
        self.assertEqual(gate["gate_identity"], canonical_hash(gate))
        self.assertEqual(
            gate["result"],
            "FAIL_CLOSED_OFFICIAL_FINAL_ACQUISITION_BLOCKED",
        )
        value = gate["state_protection"]["scored_row_count"]
        self.assertTrue(value is None or int(value) >= 0)
        self.assertFalse(gate["negative_findings"]["unofficial_source_substitution_performed"])

    def test_non_blocked_capture_is_rejected(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        capture = {
            "capture_identity": "c" * 64,
            "issued_at_utc": "2026-08-30T00:00:00Z",
            "captures": [{"game_date": "2026-08-29", "state": "CAPTURED"}],
        }
        with self.assertRaises(ValueError):
            build_blocked_gate(
                repo_root=repo_root,
                data_root=Path(r"C:\BatteredAggieSyndrome.data"),
                capture_manifest=capture,
                issued_at_utc="2026-08-30T00:05:00Z",
            )


if __name__ == "__main__":
    unittest.main()
