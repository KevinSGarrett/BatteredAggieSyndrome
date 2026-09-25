"""Cycle #37 - Attempt #2 - ACTUAL_STATE

The receipted fetcher refuses before touching the network when a class
ceiling is spent or a route has already failed twice. Neither test makes a
request.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_path = ROOT / "tools" / "cycle37" / "r37_fetch.py"
_spec = importlib.util.spec_from_file_location("r37_fetch", _path)
fetcher = importlib.util.module_from_spec(_spec)
sys.modules["r37_fetch"] = fetcher
_spec.loader.exec_module(fetcher)


class Refusals(unittest.TestCase):
    def ledger(self, network: dict) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="r37_fetch_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = tmp / "ledger.json"
        path.write_text(json.dumps({"network": network}), encoding="utf-8")
        return path

    def test_a_spent_ceiling_refuses(self) -> None:
        path = self.ledger({"availability_ceiling": 50, "availability_requests": 50})
        with self.assertRaises(fetcher.FetchRefused):
            fetcher.fetch("https://example.invalid/report", "availability", "test", ledger_path=path)
        self.assertEqual(json.loads(path.read_text())["network"]["availability_requests"], 50)

    def test_a_route_that_failed_twice_is_not_tried_again(self) -> None:
        url = "https://example.invalid/report?week=3"
        path = self.ledger({"coaching_ceiling": 50, "coaching_requests": 3,
                            "failed_routes": {fetcher.route_of(url): 2}})
        with self.assertRaises(fetcher.FetchRefused):
            fetcher.fetch(url, "coaching", "test", ledger_path=path)

    def test_an_unknown_class_refuses(self) -> None:
        with self.assertRaises(fetcher.FetchRefused):
            fetcher.fetch("https://example.invalid/", "paid", "test", ledger_path=self.ledger({}))


if __name__ == "__main__":
    unittest.main()
