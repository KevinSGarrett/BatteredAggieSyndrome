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

from aggie_analytics.data.tamu_official_2006_season_index import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    PINNED_BAT588_GATE_IDENTITY,
    PINNED_INVENTORY_IDENTITY,
    SEASON,
    build_objects,
    compute_gate_identity,
    lake_is_ready,
    parse_season_game_rows,
    validate_artifact,
)
from aggie_analytics.data.tamu_official_historical_archive import persist_capture  # noqa: E402


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = lake_is_ready(DATA_ROOT, REPO_ROOT)
OFFICIAL_2006_URL = "https://files.12thman.com/history/football/years/2006.html"

FIXTURE_HTML = (
    "<html><body><table id='yearly-stats'>"
    "<tr><th>Date</th><th>Opponent</th><th>Location</th><th>Result</th><th>Box Score</th></tr>"
    "<tr><td>Sep 2</td><td>The Citadel</td><td>College Station</td><td>W, 35-3</td>"
    "<td><a href='../stats/2006-2007/ta01-cit.html'>Box Score</a></td></tr>"
    "<tr><td>Sep 9</td><td>Louisiana-Lafayette</td><td>College Station</td><td>W, 51-7</td>"
    "<td><a href='../stats/2006-2007/ta02-ull.html'>Box Score</a></td></tr>"
    "</table></body></html>"
).encode("utf-8")

MISSING_BOX_HTML = (
    "<html><body><table>"
    "<tr><th>Date</th><th>Opponent</th><th>Box Score</th></tr>"
    "<tr><td>Sep 2</td><td>The Citadel</td><td></td></tr>"
    "</table></body></html>"
).encode("utf-8")


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


def _capture(url: str, body: bytes, relative: str = "raw/fixture.html") -> dict:
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
        "source_season": SEASON,
        "status": 200,
        "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "url": url,
    }


class Official2006UrlAndFixtureTests(unittest.TestCase):
    def test_guessed_year_url_is_rejected(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "guessed|non-official"):
            build_objects(
                body=FIXTURE_HTML,
                capture=_capture("https://files.12thman.com/history/football/years/2007.html", FIXTURE_HTML),
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
            )

    def test_fixture_discovers_source_ordered_rows_and_box_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stored = persist_capture(
                Path(tmp),
                {
                    **_capture(OFFICIAL_2006_URL, FIXTURE_HTML),
                    "page_family": "season_index",
                },
                FIXTURE_HTML,
            )
            objects = build_objects(
                body=FIXTURE_HTML,
                capture=stored,
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
            )
            self.assertEqual(
                objects["gate"]["box_score_urls"],
                [
                    "https://files.12thman.com/history/football/stats/2006-2007/ta01-cit.html",
                    "https://files.12thman.com/history/football/stats/2006-2007/ta02-ull.html",
                ],
            )
            self.assertEqual(objects["gate"]["counts"]["scheduled_games"], 2)
            self.assertEqual(objects["gate"]["counts"]["box_score_urls"], 2)
            self.assertEqual(objects["gate"]["counts"]["duplicate_links"], 0)
            self.assertEqual(objects["gate"]["counts"]["malformed_links"], 0)
            self.assertEqual(objects["gate"]["counts"]["missing_links"], 0)
            self.assertEqual(objects["gate"]["counts"]["ncaa_contest_ids_created"], 0)
            self.assertEqual(objects["gate"]["counts"]["games_admitted_to_union"], 0)
            self.assertEqual(objects["gate"]["inventory_identity"], PINNED_INVENTORY_IDENTITY)
            self.assertEqual(
                objects["gate"]["upstream_identities"]["bat588_gate_identity"],
                PINNED_BAT588_GATE_IDENTITY,
            )
            self.assertEqual(objects["gate"]["game_rows"][0]["source_opponent"], "The Citadel")
            self.assertEqual(objects["gate"]["game_rows"][0]["source_row_order"], 1)
            self.assertIsNone(objects["gate"]["game_rows"][0]["ncaa_contest_id"])

    def test_missing_box_link_is_counted_not_invented(self) -> None:
        parsed = parse_season_game_rows(
            body=MISSING_BOX_HTML,
            page_url=OFFICIAL_2006_URL,
            raw_sha256=hashlib.sha256(MISSING_BOX_HTML).hexdigest(),
        )
        self.assertEqual(parsed["counts"]["scheduled_games"], 1)
        self.assertEqual(parsed["counts"]["missing_links"], 1)
        self.assertEqual(parsed["counts"]["box_score_urls"], 0)
        self.assertIsNone(parsed["game_rows"][0]["box_score_url"])
        self.assertEqual(parsed["game_rows"][0]["link_disposition"], "MISSING")


class Compact2006GateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2006 gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8"))

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
        urls.append(urls[0])
        with self.assertRaisesRegex(AuthorityViolation, "duplicate admitted"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, box_score_urls=urls),
                require_rebuild=False,
            )

    def test_ci_path_validates_without_external_history_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = validate_artifact(
                repo_root=REPO_ROOT,
                data_root=Path(tmp),
                require_rebuild=False,
            )
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(
            result["gate_identity"],
            "d1f765a73abf0107fcf200562590bfd0212a521df47f9c6b27bb336ad737635c",
        )

    def test_invented_ncaa_id_fails_without_rebuild(self) -> None:
        rows = json.loads(json.dumps(self.gate["game_rows"]))
        rows[0]["ncaa_contest_id"] = "1234567"
        with self.assertRaisesRegex(AuthorityViolation, "NCAA contest"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, game_rows=rows),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-594 2006 capture is not mounted")
class Official2006CaptureTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["inventory_identity"], PINNED_INVENTORY_IDENTITY)
        self.assertEqual(int(result["scheduled_games"] or 0), 13)
        self.assertEqual(int(result["box_score_url_count"] or 0), 13)


if __name__ == "__main__":
    unittest.main()
