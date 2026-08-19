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

from aggie_analytics.data.tamu_official_2007_season_index import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    OFFICIAL_SEASON_INDEX_URL,
    PINNED_INVENTORY_IDENTITY,
    SEASON,
    build_objects,
    compute_gate_identity,
    lake_is_ready,
    validate_artifact,
)
from aggie_analytics.data.tamu_official_historical_archive import persist_capture  # noqa: E402


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = lake_is_ready(DATA_ROOT, REPO_ROOT)

FIXTURE_HTML = (
    "<html><body>"
    '<a href="../stats/2007-2008/ta01-foo.html">Box Score</a>'
    '<a href="../stats/2007-2008/ta02-bar.html">Box Score</a>'
    '<a href="teamcume.html">Cumulative Stats</a>'
    "</body></html>"
).encode("utf-8")


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Official2007UrlAndFixtureTests(unittest.TestCase):
    def test_guessed_year_url_is_rejected(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "guessed|non-official"):
            build_objects(
                body=FIXTURE_HTML,
                capture={
                    "url": "https://files.12thman.com/history/football/years/2006.html",
                    "parent_url": "https://files.12thman.com/history/football/history/index.html",
                    "source_season": SEASON,
                    "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
                    "historical_publication_time": None,
                    "parser_disposition": "VERIFIED_OFFICIAL_SCHOOL_PAGE",
                    "raw_sha256": hashlib.sha256(FIXTURE_HTML).hexdigest(),
                    "raw_byte_count": len(FIXTURE_HTML),
                    "raw_relative_path": "raw/fixture.html",
                    "status": 200,
                },
                repo_root=REPO_ROOT,
            )

    def test_fixture_discovers_only_labeled_box_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            stored = persist_capture(
                data_root,
                {
                    "url": OFFICIAL_SEASON_INDEX_URL,
                    "parent_url": "https://files.12thman.com/history/football/history/index.html",
                    "page_family": "season_index",
                    "source_season": SEASON,
                    "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
                    "historical_publication_time": None,
                    "parser_disposition": "VERIFIED_OFFICIAL_SCHOOL_PAGE",
                    "status": 200,
                    "content_type": "text/html",
                    "method": "GET",
                    "redirect_chain": [],
                    "rights_disposition": "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING",
                },
                FIXTURE_HTML,
            )
            objects = build_objects(body=FIXTURE_HTML, capture=stored, repo_root=REPO_ROOT)
            self.assertEqual(
                objects["gate"]["box_score_urls"],
                [
                    "https://files.12thman.com/history/football/stats/2007-2008/ta01-foo.html",
                    "https://files.12thman.com/history/football/stats/2007-2008/ta02-bar.html",
                ],
            )
            self.assertEqual(objects["gate"]["counts"]["games_admitted_to_union"], 0)
            self.assertEqual(objects["gate"]["inventory_identity"], PINNED_INVENTORY_IDENTITY)


class Compact2007GateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2007 gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8"))

    def test_protected_lane_opened_fails_without_rebuild(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT if LAKE_READY else REPO_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )

    def test_inventory_rewrite_fails_without_rebuild(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "inventory"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT if LAKE_READY else REPO_ROOT,
                gate=_mutated(self.gate, inventory_identity="0" * 64),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-588 2007 capture is not mounted")
class Official2007CaptureTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["inventory_identity"], PINNED_INVENTORY_IDENTITY)
        self.assertGreaterEqual(int(result["box_score_url_count"] or 0), 1)


if __name__ == "__main__":
    unittest.main()
