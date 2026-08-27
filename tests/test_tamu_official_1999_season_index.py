from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1999_season_index import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    OFFICIAL_SEASON_INDEX_URL,
    build_objects,
    compute_code_identity,
    compute_gate_identity,
    lake_is_ready,
    parse_season_game_rows,
    validate_artifact,
)
from aggie_analytics.data.tamu_official_historical_archive import persist_capture  # noqa: E402


DATA_ROOT = Path(
    os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
)
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT, REPO_ROOT)

FIXTURE_HTML = (
    "<html><body><table id='yearly-stats'>"
    "<tr><th>Date</th><th>Opponent</th><th>Location</th><th>Result</th><th>Box Score</th></tr>"
    "<tr><td>Sep 4</td><td>Tulsa</td><td>College Station</td><td>W, 21-7</td>"
    "<td><a href='../stats/1999-2000/tamu01.html'>Box Score</a></td></tr>"
    "<tr><td>Sep 11</td><td>Pitt</td><td>Pittsburgh</td><td>W, 27-20</td>"
    "<td><a href='../stats/1999-2000/tamu02.html'>Box Score</a></td></tr>"
    "</table></body></html>"
).encode("utf-8")

MISSING_BOX_HTML = (
    "<html><body><table>"
    "<tr><th>Date</th><th>Opponent</th><th>Box Score</th></tr>"
    "<tr><td>Sep 4</td><td>Tulsa</td><td></td></tr>"
    "</table></body></html>"
).encode("utf-8")


def _capture(url: str, body: bytes, relative: str = "raw/fixture_1999.html") -> dict:
    return {
        "content_type": "text/html",
        "historical_publication_time": None,
        "method": "GET",
        "parent_url": "https://files.12thman.com/history/football/history/index.html",
        "parser_disposition": "VERIFIED_OFFICIAL_SCHOOL_PAGE",
        "raw_byte_count": len(body),
        "raw_relative_path": relative,
        "raw_sha256": hashlib.sha256(body).hexdigest(),
        "redirect_chain": [],
        "rights_disposition": "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING",
        "source_season": 1999,
        "status": 200,
        "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "url": url,
    }


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Official1999FixtureTests(unittest.TestCase):
    def test_guessed_year_url_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(AuthorityViolation, "guessed|non-official"):
                build_objects(
                    body=FIXTURE_HTML,
                    capture=_capture(
                        "https://files.12thman.com/history/football/years/2001.html",
                        FIXTURE_HTML,
                    ),
                    repo_root=REPO_ROOT,
                    data_root=Path(tmp),
                )

    def test_fixture_discovers_source_ordered_rows_and_box_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stored = persist_capture(
                Path(tmp),
                {**_capture(OFFICIAL_SEASON_INDEX_URL, FIXTURE_HTML), "page_family": "season_index"},
                FIXTURE_HTML,
            )
            objects = build_objects(
                body=FIXTURE_HTML,
                capture=stored,
                repo_root=REPO_ROOT,
                data_root=Path(tmp),
            )
            self.assertEqual(
                objects["gate"]["box_score_urls"],
                [
                    "https://files.12thman.com/history/football/stats/1999-2000/tamu01.html",
                    "https://files.12thman.com/history/football/stats/1999-2000/tamu02.html",
                ],
            )
            self.assertEqual(objects["gate"]["counts"]["scheduled_games"], 2)
            self.assertEqual(objects["gate"]["counts"]["box_score_urls"], 2)
            self.assertEqual(objects["gate"]["counts"]["ncaa_contest_ids_created"], 0)
            self.assertEqual(objects["gate"]["counts"]["games_admitted_to_union"], 0)
            self.assertEqual(
                objects["gate"]["validator_code_identity"],
                compute_code_identity(REPO_ROOT),
            )

    def test_missing_box_link_is_counted_not_invented(self) -> None:
        parsed = parse_season_game_rows(
            body=MISSING_BOX_HTML,
            page_url=OFFICIAL_SEASON_INDEX_URL,
            raw_sha256=hashlib.sha256(MISSING_BOX_HTML).hexdigest(),
        )
        self.assertEqual(parsed["counts"]["scheduled_games"], 1)
        self.assertEqual(parsed["counts"]["missing_links"], 1)
        self.assertEqual(parsed["counts"]["box_score_urls"], 0)
        self.assertIsNone(parsed["game_rows"][0]["box_score_url"])


class Compact1999GateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("1999 gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8"))
        if self.gate.get("validator_code_identity") != compute_code_identity(REPO_ROOT):
            self.skipTest("1999 gate needs rebuild for current code identity")

    def test_protected_lane_opened_fails_without_rebuild(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )

    def test_duplicate_admitted_url_fails_without_rebuild(self) -> None:
        urls = list(self.gate["box_score_urls"])
        if urls:
            urls.append(urls[0])
        with self.assertRaisesRegex(AuthorityViolation, "duplicate admitted"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, box_score_urls=urls),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-630 1999 capture is not mounted")
class Official1999CaptureTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8"))
        if gate.get("validator_code_identity") != compute_code_identity(REPO_ROOT):
            self.skipTest("1999 gate needs rebuild for current code identity")
        result = validate_artifact(
            repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True
        )
        self.assertEqual(result["result"], "PASS")
        self.assertGreaterEqual(int(result["scheduled_games"] or 0), 1)


if __name__ == "__main__":
    unittest.main()
