"""Cycle #37 - Attempt #2 - ACTUAL_STATE: failure-cause comparison (W37R-24)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cycle37" / "r37_02_cause_comparison.py"
SEP, RULE = "=" * 70, "-" * 70


def _load():
    spec = importlib.util.spec_from_file_location("r37_02_cause_comparison", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _log(*blocks: tuple[str, str, str]) -> str:
    out = ["test_a (m.C.test_a) ... ok", ""]
    for kind, identity, exception in blocks:
        name = identity.split(".")[-1].split(" ")[0]
        out += [SEP, f"{kind}: {name} ({identity})", RULE, "Traceback (most recent call last):",
                '  File "C:\\x\\m.py", line 3, in test', "    raise X", exception, ""]
    out += [RULE, "Ran 9 tests in 1.234s", "", "FAILED (errors=1)"]
    return "\n".join(out)


class CauseComparisonTests(unittest.TestCase):
    """Failure states distinguish cause, not only identity."""

    def test_states_distinguish_cause_not_only_identity(self) -> None:
        tool = _load()
        baseline = _log(("ERROR", "m.C.test_same", "ValueError: at C:\\data\\a.json digest 0123456789abcdef"),
                        ("ERROR", "m.C.test_changed", "OSError: no .git"),
                        ("FAIL", "m.C.test_fixed", "AssertionError: 1 != 2"))
        final = _log(("ERROR", "m.C.test_same", "ValueError: at C:\\other\\b.json digest fedcba9876543210"),
                     ("ERROR", "m.C.test_changed", "AssertionError: gate mismatch"),
                     ("FAIL", "m.C.test_new", "AssertionError: 3 != 4"))
        result = tool.compare(baseline, final)
        states = {row["identity"]: row["state"] for row in result["rows"]}
        assert states == {"m.C.test_same": "INHERITED_SAME_CAUSE", "m.C.test_changed": "INHERITED_DIFFERENT_CAUSE",
                          "m.C.test_fixed": "FIXED", "m.C.test_new": "INTRODUCED"}
        assert result["introduced"] == ["m.C.test_new"]
        assert result["unadjudicated_different_cause"] == ["m.C.test_changed"]

    def test_subtests_keep_their_parameters_in_the_identity(self) -> None:
        tool = _load()
        log = "\n".join([SEP, "FAIL: test_x (m.C.test_x) (unit='R35-01')", RULE, "Traceback (most recent call last):",
                         '  File "m.py", line 1, in t', "    x", "AssertionError: no", "", RULE, "Ran 1 test in 0.1s"])
        assert list(tool.failure_blocks(log)) == ["m.C.test_x (unit='R35-01')"]


if __name__ == "__main__":
    unittest.main()
