"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-07 AC02: a user cell's spreadsheet address and physical line range are
computed the way a spreadsheet and a text editor would show them, including
a record whose quoted cell spans several lines.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_path = ROOT / "tools" / "cycle37" / "r37_07_user_corpus_lineage.py"
_spec = importlib.util.spec_from_file_location("r37_07_user_corpus_lineage", _path)
tool = importlib.util.module_from_spec(_spec)
sys.modules["r37_07_user_corpus_lineage"] = tool
_spec.loader.exec_module(tool)


class Geometry(unittest.TestCase):
    def test_column_letters(self) -> None:
        self.assertEqual([tool.column_letters(i) for i in (0, 25, 26, 27, 701, 702)],
                         ["A", "Z", "AA", "AB", "ZZ", "AAA"])

    def test_a_multi_line_record_keeps_its_physical_lines(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="r37_lineage_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = tmp / "cells.csv"
        path.write_bytes("﻿Team,Head Coach\nAir Force,\"Fisher DeBerry\nnote\"\nArmy,Bob Sutton\n".encode("utf-8"))
        headers, spans = tool.record_lines(path)
        self.assertEqual(headers, ["Team", "Head Coach"])
        self.assertEqual(spans, [(2, 3), (4, 4)])


if __name__ == "__main__":
    unittest.main()
