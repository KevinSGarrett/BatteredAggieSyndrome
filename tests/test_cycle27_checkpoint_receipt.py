"""Cycle 27 checkpoint receipt binder: windows from bound cutoff, not A&M constants."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.operations.contest_checkpoint_ledger import CAPTURE_WINDOW  # noqa: E402
from aggie_analytics.operations.cycle27_checkpoint_receipt import (  # noqa: E402
    HARDCODED_FRI_WINDOW_CONSTANT,
    REQUIRED_STAGES,
    bind_checkpoint_receipt,
    classify_checkpoint_label,
    derive_capture_window_open,
    main as bind_main,
    parse_named_stages,
)

UTC = timezone.utc


def _complete_log(identities: dict[str, str]) -> str:
    lines = []
    for name in REQUIRED_STAGES:
        ident = identities.get(name, "a" * 64)
        lines.append(
            f"[2026-09-04T20:16:00.000000+00:00] START {name}: python tools/{name}.py"
        )
        if name in {"schedule", "rankings", "weather"}:
            lines.append(f"capture_identity: {ident}")
        lines.append(f"[2026-09-04T20:16:30.000000+00:00] OK {name}")
    return "\n".join(lines) + "\n"


class Cycle27CheckpointReceiptTests(unittest.TestCase):
    def test_friday_window_is_cutoff_minus_sixty_not_1945(self) -> None:
        cutoff = datetime(2026, 9, 4, 21, 0, tzinfo=UTC)
        window = derive_capture_window_open(cutoff)
        self.assertEqual(window, datetime(2026, 9, 4, 20, 0, tzinfo=UTC))
        self.assertEqual(window, cutoff - CAPTURE_WINDOW)
        self.assertNotEqual(window, HARDCODED_FRI_WINDOW_CONSTANT)

    def test_later_cluster_does_not_inherit_friday_1945_constant(self) -> None:
        cutoff = datetime(2026, 9, 4, 22, 30, tzinfo=UTC)
        window = derive_capture_window_open(cutoff)
        self.assertEqual(window, datetime(2026, 9, 4, 21, 30, tzinfo=UTC))
        with self.assertRaisesRegex(
            ValueError, "HARDCODED_CAPTURE_WINDOW_NOT_FROM_BOUND_CUTOFF"
        ):
            derive_capture_window_open(cutoff, HARDCODED_FRI_WINDOW_CONSTANT)

    def test_early_capture_is_not_t90_for_a_later_cutoff(self) -> None:
        cutoff = datetime(2026, 9, 4, 22, 30, tzinfo=UTC)
        window = derive_capture_window_open(cutoff)
        now = datetime(2026, 9, 4, 20, 15, tzinfo=UTC)
        classified = classify_checkpoint_label(
            phase="T90M",
            now=now,
            window_open=window,
            cutoff=cutoff,
            missing_stages=(),
            cohort_contest="6601163",
        )
        self.assertEqual(classified["checkpoint_label"], "RAW_CAPTURE_OUTSIDE_WINDOW")
        self.assertFalse(classified["forecast_frozen"])
        # The retired 19:45 default would have falsely labeled this T-90M.
        bogus = classify_checkpoint_label(
            phase="T90M",
            now=now,
            window_open=HARDCODED_FRI_WINDOW_CONSTANT,
            cutoff=cutoff,
            missing_stages=(),
            cohort_contest="6601163",
        )
        self.assertEqual(bogus["checkpoint_label"], "T-90M")

    def test_completion_after_cutoff_is_not_backfill(self) -> None:
        cutoff = datetime(2026, 9, 4, 21, 0, tzinfo=UTC)
        classified = classify_checkpoint_label(
            phase="T90M",
            now=cutoff + timedelta(minutes=1),
            window_open=cutoff - CAPTURE_WINDOW,
            cutoff=cutoff,
            missing_stages=(),
            cohort_contest="6594366",
        )
        self.assertEqual(classified["state"], "MISSED_CUTOFF_NO_BACKFILL")
        self.assertEqual(classified["checkpoint_label"], "LATE_RAW_CAPTURE_ONLY")
        self.assertFalse(classified["forecast_frozen"])

    def test_in_window_friday_capture_is_evidence_not_forecast(self) -> None:
        cutoff = datetime(2026, 9, 4, 21, 0, tzinfo=UTC)
        classified = classify_checkpoint_label(
            phase="T90M",
            now=datetime(2026, 9, 4, 20, 20, tzinfo=UTC),
            window_open=derive_capture_window_open(cutoff),
            cutoff=cutoff,
            missing_stages=(),
            cohort_contest="6594366",
        )
        self.assertEqual(classified["checkpoint_label"], "T-90M")
        self.assertEqual(classified["state"], "EVIDENCE_CAPTURED")
        self.assertFalse(classified["forecast_frozen"])

    def test_parse_named_stages_requires_named_ok_not_latest_mtime(self) -> None:
        text = (
            "[2026-09-04T20:16:00Z] START schedule: python tools/x.py\n"
            "capture_identity: " + ("b" * 64) + "\n"
            "[2026-09-04T20:16:10Z] OK schedule\n"
            "[2026-09-04T20:16:11Z] START weather: python tools/y.py\n"
        )
        stages = parse_named_stages(text)
        self.assertEqual(stages["schedule"]["ok"], "true")
        self.assertNotIn("ok", stages["weather"])

    def test_bind_writes_versioned_receipt_and_pointer_without_forecast(self) -> None:
        cutoff = datetime(2026, 9, 4, 21, 0, tzinfo=UTC)
        ident = "c" * 64
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / "scheduler.log"
            log_path.write_text(
                _complete_log({"schedule": ident, "rankings": ident, "weather": ident}),
                encoding="utf-8",
            )
            ledger = root / "ledger.json"
            ledger.write_text(
                json.dumps(
                    {
                        "contests": [
                            {
                                "ncaa_contest_id": "6594366",
                                "kickoff_bound_utc": "2026-09-04T22:30:00Z",
                                "t90m_cutoff_utc": "2026-09-04T21:00:00Z",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            shadow = root / "manifests" / "shadow" / "sha256" / ident
            shadow.mkdir(parents=True)
            (shadow / "bytes.bin").write_bytes(b"raw")
            first = bind_checkpoint_receipt(
                checkpoint="FRI_T90M_20260904T2100Z",
                phase="T90M",
                run_id="c27-fri-t90m-test",
                log_path=log_path,
                cutoff=cutoff,
                cohort_contest="6594366",
                now=datetime(2026, 9, 4, 20, 20, tzinfo=UTC),
                output_root=root / "ops",
                data_root=root,
                ledger_paths=[ledger],
            )
            self.assertTrue(first["verified"])
            self.assertEqual(first["checkpoint_label"], "T-90M")
            self.assertEqual(first["state"], "EVIDENCE_CAPTURED")
            payload = json.loads(Path(first["receipt"]).read_text(encoding="utf-8"))
            self.assertFalse(payload["forecast_frozen"])
            self.assertEqual(payload["capture_window_open_utc"], "2026-09-04T20:00:00Z")
            self.assertEqual(payload["earliest_cutoff_utc"], "2026-09-04T21:00:00Z")
            self.assertEqual(payload["coverage"], "EXACT_EARLIEST_CLUSTER")
            self.assertNotEqual(
                payload["capture_window_open_utc"], "2026-09-04T19:45:00Z"
            )
            pointer = json.loads(
                (
                    root
                    / "ops"
                    / "receipts"
                    / "FRI_T90M_20260904T2100Z"
                    / "LATEST.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(pointer["receipt_sha256"], first["receipt_sha256"])
            second = bind_checkpoint_receipt(
                checkpoint="FRI_T90M_20260904T2100Z",
                phase="T90M",
                run_id="c27-fri-t90m-test-2",
                log_path=log_path,
                cutoff=cutoff,
                cohort_contest="6594366",
                now=datetime(2026, 9, 4, 20, 25, tzinfo=UTC),
                output_root=root / "ops",
                data_root=root,
                ledger_paths=[ledger],
            )
            self.assertNotEqual(first["receipt_sha256"], second["receipt_sha256"])
            self.assertTrue(Path(first["receipt"]).is_file())
            self.assertTrue(Path(second["receipt"]).is_file())

    def test_main_executes_bind_against_isolated_fixture(self) -> None:
        ident = "d" * 64
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / "scheduler.log"
            log_path.write_text(
                _complete_log({"schedule": ident, "rankings": ident, "weather": ident}),
                encoding="utf-8",
            )
            ledger = root / "ledger.json"
            ledger.write_text(
                json.dumps({"contests": [{"ncaa_contest_id": "6594366"}]}),
                encoding="utf-8",
            )
            shadow = root / "manifests" / "shadow" / "sha256" / ident
            shadow.mkdir(parents=True)
            (shadow / "bytes.bin").write_bytes(b"raw")
            code = bind_main(
                [
                    "--checkpoint",
                    "FRI_T90M_20260904T2100Z",
                    "--phase",
                    "T90M",
                    "--run-id",
                    "source-anchor",
                    "--log",
                    str(log_path),
                    "--cutoff",
                    "2026-09-04T21:00:00Z",
                    "--cohort-contest",
                    "6594366",
                    "--output-root",
                    str(root / "ops"),
                    "--data-root",
                    str(root),
                    "--ledger",
                    str(ledger),
                    "--now-utc",
                    "2026-09-04T20:20:00Z",
                ]
            )
            self.assertEqual(code, 0)
            latest = json.loads(
                (
                    root
                    / "ops"
                    / "receipts"
                    / "FRI_T90M_20260904T2100Z"
                    / "LATEST.json"
                ).read_text(encoding="utf-8")
            )
            receipt = json.loads(
                Path(latest["receipt_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["checkpoint_label"], "T-90M")
            self.assertFalse(receipt["forecast_frozen"])
            self.assertEqual(
                receipt["clock_note"], "REPLAY_METADATA_NOT_ACQUISITION_CLOCK"
            )

    def test_cli_default_does_not_hardcode_1945(self) -> None:
        source = (
            REPO_ROOT
            / "src"
            / "aggie_analytics"
            / "operations"
            / "cycle27_checkpoint_receipt.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn('default="2026-09-04T19:45:00Z"', source)
        self.assertIn("cutoff_minus_capture_window_unless_explicit", source)

    def test_versioned_failover_window_matches_bound_friday_cutoff(self) -> None:
        script = (
            REPO_ROOT / "tools" / "cycle27_schedulers" / "run_friday_t90m_failover.ps1"
        )
        text = script.read_text(encoding="utf-8")
        self.assertIn("2026-09-04T20:00:00Z", text)
        self.assertNotIn("2026-09-04T19:45:00Z", text)


if __name__ == "__main__":
    unittest.main()
