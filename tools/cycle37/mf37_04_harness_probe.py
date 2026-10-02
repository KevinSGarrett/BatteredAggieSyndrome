r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Reproduce MF37-04 against a chosen source tree.

Two probes, both through the tool the cycle actually runs
(``tools/cycle36/c36_15_validation.py``) rather than through a copy of its
regexes:

* ``duplicate_identity`` feeds the manager's verbatim two-failure input to
  ``parse_unittest`` and reports the identities it kept.
* ``all_skipped_lane`` runs a real interpreter on a real suite in which every
  test is skipped, and reports the state ``run_lane`` assigned.

The suite and the scratch live under ``--scratch``; the source tree is only
imported.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class _bas_atomic:  # U37-11: atomic writes once this tool has imported the package itself
    @staticmethod
    def _module():
        import sys as _bas_sys

        if "aggie_analytics" not in _bas_sys.modules:
            return None  # never bind the package from another tree before the tool does
        try:
            from aggie_analytics import atomic_io
        except ImportError:
            return None
        return atomic_io

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_text(path, *args, **kwargs) if module else path.write_text(*args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_bytes(path, *args, **kwargs) if module else path.write_bytes(*args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        module = cls._module()
        return module.open_write(path, *args, **kwargs) if module else path.open(*args, **kwargs)


sys.dont_write_bytecode = True

MANAGER_DUPLICATE_IDENTITY_INPUT = (
    "ERROR: test_shared (suite_alpha.Alpha.test_shared)\n"
    "ERROR: test_shared (suite_beta.Beta.test_shared)\n"
    "Ran 2 tests in 0.01s\n"
    "FAILED (errors=2)\n"
)

ALL_SKIPPED_SUITE = (
    "import unittest\n\n"
    "class Skipped(unittest.TestCase):\n"
    "    @unittest.skip('manager negative control')\n"
    "    def test_not_executed(self):\n"
    "        raise AssertionError('never reached')\n"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True)
    parser.add_argument("--scratch", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    src = Path(args.src).resolve()
    module_path = src / "tools" / "cycle36" / "c36_15_validation.py"
    if not module_path.is_file():
        raise SystemExit(f"{module_path} does not exist")
    sys.path.insert(0, str(src / "src"))
    for name in [m for m in sys.modules if m.startswith("aggie_analytics")]:
        del sys.modules[name]

    spec = importlib.util.spec_from_file_location("c36_15_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    scratch = Path(args.scratch).resolve()
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)

    parsed = module.parse_unittest(MANAGER_DUPLICATE_IDENTITY_INPUT)
    identities = list(parsed.get("failed_or_errored_identities") or [])

    _bas_atomic.write_text(scratch / "test_all_skipped.py", ALL_SKIPPED_SUITE, encoding="utf-8")
    record = module.run_lane(
        "all_skipped_control",
        [sys.executable, "-B", "-m", "unittest", "-v", "test_all_skipped"],
        cwd=scratch,
        log_dir=scratch / "logs",
    )

    result: dict[str, Any] = {
        "label": args.label,
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "source_tree": str(src),
        "module_under_test": str(module_path),
        "module_sha256": hashlib.sha256(module_path.read_bytes()).hexdigest(),
        "python": sys.version.split()[0],
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "duplicate_identity": {
            "input": MANAGER_DUPLICATE_IDENTITY_INPUT,
            "unittest_summary_declares_errors": 2,
            "parsed_identities": identities,
            "parsed_count": parsed.get("failed_or_errored_count"),
            "expected_distinct": [
                "suite_alpha.Alpha.test_shared",
                "suite_beta.Beta.test_shared",
            ],
            "identities_conserved": sorted(identities)
            == ["suite_alpha.Alpha.test_shared", "suite_beta.Beta.test_shared"],
        },
        "all_skipped_lane": {
            "exit_code": record.get("exit_code"),
            "result": record.get("result"),
            "satisfies_acceptance": record.get("satisfies_acceptance"),
            "state_reason": record.get("state_reason"),
            "tests_run": (record.get("unittest") or {}).get("tests_run"),
            "skipped_count": (record.get("unittest") or {}).get("skipped_count"),
            "executed_test_count": (record.get("unittest") or {}).get("executed_test_count"),
            "reported_as_pass": record.get("result") == "PASS",
            "log_path": record.get("log_path"),
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out, json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("identities_conserved        =", result["duplicate_identity"]["identities_conserved"])
    print("parsed_identities           =", identities)
    print("all_skipped_lane.exit_code  =", result["all_skipped_lane"]["exit_code"])
    print("all_skipped_lane.result     =", result["all_skipped_lane"]["result"])
    print("all_skipped_reported_as_pass=", result["all_skipped_lane"]["reported_as_pass"])
    print("receipt:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
