from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_2001_season_index import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    PINNED_BAT609_GATE_IDENTITY,
    PINNED_BAT613_GATE_IDENTITY,
    PINNED_INVENTORY_IDENTITY,
    SEASON,
    build_objects,
    compute_code_identity,
    compute_gate_identity,
    lake_is_ready,
    parse_season_game_rows,
    validate_artifact,
)
from aggie_analytics.data.tamu_official_historical_archive import persist_capture  # noqa: E402


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = lake_is_ready(DATA_ROOT, REPO_ROOT)
OFFICIAL_2001_URL = "https://files.12thman.com/history/football/years/2001.html"

FIXTURE_HTML = (
    "<html><body><table id='yearly-stats'>"
    "<tr><th>Date</th><th>Opponent</th><th>Location</th><th>Result</th><th>Box Score</th></tr>"
    "<tr><td>Aug 30</td><td>Arkansas State</td><td>College Station</td><td>W, 20-0</td>"
    "<td><a href='../stats/2001-2002/ta01-asu.html'>Box Score</a></td></tr>"
    "<tr><td>Sep 6</td><td>Utah</td><td>College Station</td><td>W, 28-26</td>"
    "<td><a href='../stats/2001-2002/ta02-utah.html'>Box Score</a></td></tr>"
    "</table></body></html>"
).encode("utf-8")

MISSING_BOX_HTML = (
    "<html><body><table>"
    "<tr><th>Date</th><th>Opponent</th><th>Box Score</th></tr>"
    "<tr><td>Aug 30</td><td>Arkansas State</td><td></td></tr>"
    "</table></body></html>"
).encode("utf-8")

AMBIGUOUS_HTML = (
    "<html><body><table>"
    "<tr><th>Date</th><th>Opponent</th><th>Box Score</th></tr>"
    "<tr><td></td><td>Unknown Opponent</td>"
    "<td><a href='../stats/2001-2002/ta03-unk.html'>Box Score</a></td></tr>"
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


class Official2001UrlAndFixtureTests(unittest.TestCase):
    def test_guessed_year_url_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(AuthorityViolation, "guessed|non-official"):
                build_objects(
                    body=FIXTURE_HTML,
                    capture=_capture("https://files.12thman.com/history/football/years/2002.html", FIXTURE_HTML),
                    repo_root=REPO_ROOT,
                    data_root=Path(tmp),
                )

    def test_fixture_discovers_source_ordered_rows_and_box_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stored = persist_capture(
                Path(tmp),
                {
                    **_capture(OFFICIAL_2001_URL, FIXTURE_HTML),
                    "page_family": "season_index",
                },
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
                    "https://files.12thman.com/history/football/stats/2001-2002/ta01-asu.html",
                    "https://files.12thman.com/history/football/stats/2001-2002/ta02-utah.html",
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
                objects["gate"]["upstream_identities"]["bat609_gate_identity"],
                PINNED_BAT609_GATE_IDENTITY,
            )
            self.assertEqual(objects["gate"]["game_rows"][0]["source_opponent"], "Arkansas State")
            self.assertEqual(objects["gate"]["game_rows"][0]["source_row_order"], 1)
            self.assertIsNone(objects["gate"]["game_rows"][0]["ncaa_contest_id"])
            self.assertEqual(objects["gate"]["season"], 2001)
            self.assertEqual(objects["gate"]["jira_key"], "BAT-621")
            self.assertEqual(
                objects["gate"]["upstream_identities"]["bat613_gate_identity"],
                PINNED_BAT613_GATE_IDENTITY,
            )
            self.assertEqual(objects["gate"]["validator_code_identity"], compute_code_identity(REPO_ROOT))

    def test_missing_box_link_is_counted_not_invented(self) -> None:
        parsed = parse_season_game_rows(
            body=MISSING_BOX_HTML,
            page_url=OFFICIAL_2001_URL,
            raw_sha256=hashlib.sha256(MISSING_BOX_HTML).hexdigest(),
        )
        self.assertEqual(parsed["counts"]["scheduled_games"], 1)
        self.assertEqual(parsed["counts"]["missing_links"], 1)
        self.assertEqual(parsed["counts"]["box_score_urls"], 0)
        self.assertIsNone(parsed["game_rows"][0]["box_score_url"])
        self.assertEqual(parsed["game_rows"][0]["link_disposition"], "MISSING")

    def test_ambiguous_date_is_preserved(self) -> None:
        parsed = parse_season_game_rows(
            body=AMBIGUOUS_HTML,
            page_url=OFFICIAL_2001_URL,
            raw_sha256=hashlib.sha256(AMBIGUOUS_HTML).hexdigest(),
        )
        self.assertEqual(parsed["game_rows"][0]["source_date"], "")
        self.assertEqual(parsed["game_rows"][0]["source_opponent"], "Unknown Opponent")
        self.assertEqual(parsed["counts"]["scheduled_games"], 1)


class Compact2001GateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2001 gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8"))

    def test_protected_lane_opened_fails_without_rebuild(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )

    def test_changed_parent_index_fails_without_rebuild(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "changed parent index"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(
                    self.gate,
                    discovery_parent_url="https://files.12thman.com/history/football/history/other.html",
                ),
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
        self.assertEqual(self.gate["official_index_url"], OFFICIAL_2001_URL)
        self.assertEqual(self.gate["upstream_identities"]["bat609_gate_identity"], PINNED_BAT609_GATE_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat613_gate_identity"], PINNED_BAT613_GATE_IDENTITY)

    def test_stale_code_identity_fails_without_rebuild(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "stale code identity"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, validator_code_identity="0" * 64),
                require_rebuild=False,
            )

    def test_changed_code_with_stale_code_identity(self) -> None:
        with mock.patch(
            "aggie_analytics.data.tamu_official_2001_season_index.compute_code_identity",
            return_value="0" * 64,
        ):
            with self.assertRaisesRegex(AuthorityViolation, "stale code identity"):
                validate_artifact(
                    repo_root=REPO_ROOT,
                    data_root=DATA_ROOT,
                    gate=self.gate,
                    require_rebuild=False,
                )

    def test_bat613_identity_rewrite_fails_without_rebuild(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat613_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-613 2002 gate identity rewritten"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, upstream_identities=upstream),
                require_rebuild=False,
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


@unittest.skipUnless(LAKE_READY, "external BAT-621 2001 capture is not mounted")
class Official2001CaptureTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["inventory_identity"], PINNED_INVENTORY_IDENTITY)
        self.assertGreaterEqual(int(result["scheduled_games"] or 0), 1)
        self.assertGreaterEqual(int(result["box_score_url_count"] or 0), 0)


if __name__ == "__main__":
    unittest.main()
