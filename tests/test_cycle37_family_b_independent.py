"""Cycle #37 - Attempt #2 - ACTUAL_STATE: the independent Family B checker."""

from __future__ import annotations

import ast
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.validation.artifact_binding import compute_identity

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cycle37" / "r37_12_family_b_independent.py"


def _load():
    spec = importlib.util.spec_from_file_location("r37_12_family_b_independent", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FamilyBIndependentTests(unittest.TestCase):
    """The checker is producer-free and scans the raw corpus."""

    def test_imports_no_producer_code(self) -> None:
        tree = ast.parse(TOOL.read_text(encoding="utf-8"))
        names = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        names += [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert not [name for name in names if name.startswith("aggie_analytics")]

    def test_hash_conventions_match_the_declared_identities(self) -> None:
        independent = _load()
        value = {"b": [1, "é"], "a": {"z": None, "y": 2.5}}
        assert independent.content_hash(value) == stable_hash(value)
        gate = {"gate_identity": "x", "counts": {"n": 3}, "name": "ünïcode"}
        assert independent.gate_hash(gate) == compute_identity(gate, "gate_identity")

    def test_leak_scan_counts_raw_occurrences(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            independent = _load()
            child = tmp_path / independent.CORPUS_ROOT / ("0" * 64)
            child.mkdir(parents=True)
            rows = [{"source_url": "https://a/1.htm"}, {"note": "see https://a/1.htm"}, {"source_url": "https://a/2.htm"}]
            (child / "drives.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            found = independent.leak_scan(tmp_path, ["https://a/1.htm"])
            assert found["occurrences_by_file"] == {"drives.jsonl": 2}
            assert found["no_active_rejected_url_anywhere_in_the_corpus"] is False
            clean = independent.leak_scan(tmp_path, ["https://a/3.htm"])
            assert clean["no_active_rejected_url_anywhere_in_the_corpus"] is True

    def test_an_empty_corpus_is_not_reported_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            independent = _load()
            assert independent.leak_scan(tmp_path, ["https://a/1.htm"])[
                "no_active_rejected_url_anywhere_in_the_corpus"] is False


if __name__ == "__main__":
    unittest.main()
