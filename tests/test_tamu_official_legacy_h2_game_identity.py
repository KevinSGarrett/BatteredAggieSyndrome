from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash  # noqa: E402  # pylint: disable=import-error
from aggie_analytics.data.tamu_official_historical_archive import sha256_file  # noqa: E402  # pylint: disable=import-error
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation  # noqa: E402  # pylint: disable=import-error
from aggie_analytics.data.tamu_official_legacy_h2_game_identity import (  # noqa: E402  # pylint: disable=import-error
    parse_legacy_game_identity,
)

DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and DATA_ROOT.exists()


class LegacyH2ParserOfflineTests(unittest.TestCase):
    def test_h2_identity_parses(self) -> None:
        body = (
            b"<html><h2>Saturday, September 6, 1997:<br>Texas A&amp;M 59, Sam Houston State 6</h2>"
            b"<pre>Score by Quarters 1 2 3 4 Score\nSAM HOUSTON STATE... 3 3 0 0 - 6\nTEXAS A&amp;M........... 7 10 28 14 - 59</pre></html>"
        )
        raw_sha = hashlib.sha256(body).hexdigest()
        parsed = parse_legacy_game_identity(
            body=body,
            url="https://files.12thman.com/history/football/stats/1997-1998/mfb_1914_97_shsu.html",
            source_season=1997,
            source_order=1,
            raw_sha256=raw_sha,
            raw_file_sha256=raw_sha,
            allowed_urls=frozenset({"https://files.12thman.com/history/football/stats/1997-1998/mfb_1914_97_shsu.html"}),
            official_index_url="https://files.12thman.com/history/football/years/1997.html",
            parent_url="https://files.12thman.com/history/football/years/1997.html",
        )
        self.assertEqual(parsed["football_season"], 1997)
        self.assertEqual(parsed["tamu_points"], 59)

    def test_parent_substitution_rejected(self) -> None:
        body = (
            b"<html><h2>Saturday, September 6, 1997:<br>Texas A&amp;M 59, Sam Houston State 6</h2>"
            b"<pre>Score by Quarters 1 2 3 4 Score\nSAM HOUSTON STATE... 3 3 0 0 - 6\nTEXAS A&amp;M........... 7 10 28 14 - 59</pre></html>"
        )
        raw_sha = hashlib.sha256(body).hexdigest()
        with self.assertRaisesRegex(AuthorityViolation, "substituted parent URL"):
            parse_legacy_game_identity(
                body=body,
                url="https://files.12thman.com/history/football/stats/1997-1998/mfb_1914_97_shsu.html",
                source_season=1997,
                source_order=1,
                raw_sha256=raw_sha,
                raw_file_sha256=raw_sha,
                allowed_urls=frozenset({"https://files.12thman.com/history/football/stats/1997-1998/mfb_1914_97_shsu.html"}),
                official_index_url="https://files.12thman.com/history/football/years/1997.html",
                parent_url="https://files.12thman.com/history/football/years/1996.html",
            )


@unittest.skipUnless(LAKE_READY, "external Cycle #18 data root is not mounted")
class LegacyH2ParserMountedTests(unittest.TestCase):
    def _parse_all(self) -> list[dict]:
        output: list[dict] = []
        for season in (1997, 1996):
            gate = json.loads((REPO_ROOT / f"artifacts/data_lake/tamu_official_{season}_season_index_gate.json").read_text(encoding="utf-8-sig"))
            allowed = frozenset(gate["box_score_urls"])
            capture_index = json.loads((DATA_ROOT / f"features/tamu_official_{season}_boxscores/capture_index.json").read_text(encoding="utf-8-sig"))
            for capture in capture_index["captures"]:
                raw_path = DATA_ROOT / capture["raw_relative_path"]
                raw_sha = sha256_file(raw_path)
                parsed = parse_legacy_game_identity(
                    body=raw_path.read_bytes(),
                    url=capture["url"],
                    source_season=season,
                    source_order=int(capture["source_order"]),
                    raw_sha256=capture["raw_sha256"],
                    raw_file_sha256=raw_sha,
                    allowed_urls=allowed,
                    official_index_url=gate["official_index_url"],
                    parent_url=capture["parent_url"],
                )
                output.append(parsed)
        return output

    def test_parses_all_mounted_pages(self) -> None:
        parsed = self._parse_all()
        self.assertEqual(len(parsed), 23)
        self.assertTrue(all(item["opponent_candidate"] for item in parsed))

    def test_deterministic_across_two_runs(self) -> None:
        first = self._parse_all()
        second = self._parse_all()
        self.assertEqual(stable_hash(first), stable_hash(second))


if __name__ == "__main__":
    unittest.main()
