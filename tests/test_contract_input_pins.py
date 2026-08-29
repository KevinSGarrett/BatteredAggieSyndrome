from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from validate_contract_input_pins import iter_pins, main  # noqa: E402  # pylint: disable=import-error

VALIDATOR = REPO_ROOT / "tools" / "validate_contract_input_pins.py"


def run_against(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--repo-root", str(repo_root)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class ContractInputPinTests(unittest.TestCase):
    def test_the_tracked_repository_has_no_stale_input_pins(self) -> None:
        result = run_against(REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_a_drifted_pin_is_reported_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "configs").mkdir()
            (root / "artifacts").mkdir()
            tracked = root / "artifacts" / "example_gate.json"
            tracked.write_text('{"gate_identity": "abc"}\n', encoding="utf-8")
            (root / "configs" / "example_contract.json").write_text(
                json.dumps(
                    {
                        "source_contract": {
                            "example_gate_relative_path": "artifacts/example_gate.json",
                            "example_gate_sha256": "0" * 64,
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = run_against(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("DRIFTED", result.stdout)
        self.assertIn("artifacts/example_gate.json", result.stdout)

    def test_a_missing_pinned_repository_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "configs").mkdir()
            (root / "configs" / "example_contract.json").write_text(
                json.dumps(
                    {
                        "example_gate_relative_path": "artifacts/absent_gate.json",
                        "example_gate_sha256": "0" * 64,
                    }
                ),
                encoding="utf-8",
            )
            result = run_against(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING", result.stdout)

    def test_data_root_pins_are_skipped_rather_than_failed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "configs").mkdir()
            (root / "configs" / "example_contract.json").write_text(
                json.dumps(
                    {
                        "payload_relative_path": "features/national/sha256/deadbeef/payload.parquet",
                        "payload_sha256": "0" * 64,
                    }
                ),
                encoding="utf-8",
            )
            result = run_against(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("data-root input pins skipped: 1", result.stdout)

    def test_pins_are_only_paired_when_the_path_sibling_exists(self) -> None:
        paired = {
            "thing_relative_path": "artifacts/a.json",
            "thing_sha256": "a" * 64,
            "orphan_sha256": "b" * 64,
        }
        self.assertEqual(list(iter_pins(paired)), [("artifacts/a.json", "a" * 64)])

    def test_pins_are_discovered_inside_nested_lists_and_objects(self) -> None:
        nested = {
            "sources": [
                {"one_path": "artifacts/one.json", "one_sha256": "1" * 64},
                {"deeper": {"two_relative": "configs/two.json", "two_sha256": "2" * 64}},
            ]
        }
        self.assertEqual(
            sorted(iter_pins(nested)),
            [("artifacts/one.json", "1" * 64), ("configs/two.json", "2" * 64)],
        )

    def test_windows_separators_in_a_pinned_path_are_normalized(self) -> None:
        document = {
            "thing_relative_path": "artifacts\\data_lake\\a.json",
            "thing_sha256": "a" * 64,
        }
        self.assertEqual(list(iter_pins(document)), [("artifacts/data_lake/a.json", "a" * 64)])

    def test_main_is_callable_in_process_and_agrees_with_the_subprocess(self) -> None:
        argv = sys.argv
        sys.argv = ["validate_contract_input_pins.py", "--repo-root", str(REPO_ROOT)]
        try:
            self.assertEqual(main(), 0)
        finally:
            sys.argv = argv


if __name__ == "__main__":
    unittest.main()
