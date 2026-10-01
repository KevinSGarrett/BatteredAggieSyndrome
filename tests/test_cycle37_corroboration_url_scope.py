"""Archive classification follows the URL host, not a substring elsewhere."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "corroboration_url_scope", ROOT / "tools/cycle37/r37_05_corroboration_tranche.py"
)
tranche = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(tranche)


class CitedHostTests(unittest.TestCase):
    def test_archives_are_excluded_without_excluding_lookalike_official_hosts(self) -> None:
        urls = ["https://archive.org/a", "https://web.archive.org/a",
                "https://archive.org.example.edu/a", "https://example.edu/archive.org/a",
                "https://archive.org@example.edu/a", "https://example.edu:443/a"]
        payload = {"query": {"pages": {"1": {"revisions": [
            {"slots": {"main": {"*": " ".join(urls)}}}
        ]}}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(tranche.cited_official_urls(str(path), set()), urls[2:])


if __name__ == "__main__":
    unittest.main()
