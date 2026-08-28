from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash  # noqa: E402
from aggie_analytics.data.tamu_official_historical_archive import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    NETWORK_ACCESS_FORBIDDEN_ERROR,
    PASS_CLASSIFICATION,
    PROTECTED_LANE,
    SOURCE_ID,
    WMT_ACQUISITION_IDENTITY,
    compute_gate_identity,
    discover_box_score_urls,
    direct_http_get,
    load_json,
    parse_roster_rows,
    pdf_capture_disposition,
    validate_artifact,
    validate_official_url,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = (DATA_ROOT / "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/season_index").is_dir()


def _season_page(season: int = 2010, folder: str = "2010-2011", ext: str = "html") -> bytes:
    links = []
    for index, slug in enumerate(
        ("sfa", "lat", "fiu", "osu", "ark", "miz", "ku", "ttu", "ou", "bu", "nu", "ut", "lsu"),
        start=1,
    ):
        links.append(f'<a href="../stats/{folder}/ta{index:02d}-{slug}.{ext}">Box Score</a>')
        links.append(f'<a href="../recaps/{folder}/ta{index:02d}-{slug}.html">Recap</a>')
    return (
        f"<html><body><h2>Football: {season} Season Stats</h2>"
        + "".join(links)
        + "</body></html>"
    ).encode("utf-8")


def _roster_page(season: int = 2010) -> bytes:
    return f"""<html><body><h2 class="seasontitle">{season} Roster</h2>
    <table><tr><th>No.</th><th>Name</th><th>Position</th></tr>
    <tr><td>8</td><td>Tannehill, Ryan</td><td>QB</td></tr>
    <tr><td>2</td><td>Gray, Cyrus</td><td>RB</td></tr>
    <tr><td>2</td><td>Hunter, Justin</td><td>WR</td></tr>
    </table></body></html>""".encode("utf-8")


def _mutated(gate: dict, **changes) -> dict:
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    if "captures" in changes or "counts" in changes or "discovered_box_score_urls" in changes or "page_identities" in changes:
        tampered["acquisition_identity"] = stable_hash(
            {
                "captures": tampered.get("captures"),
                "counts": tampered.get("counts"),
                "discovered_box_score_urls": tampered.get("discovered_box_score_urls"),
                "page_identities": tampered.get("page_identities"),
            }
        )
        tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class OfficialHistoricalArchiveTests(unittest.TestCase):
    def test_nonofficial_host_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            validate_official_url("https://stats.ncaa.org/contests/999999/box_score")

    def test_box_score_hrefs_are_parsed_not_guessed(self) -> None:
        urls = discover_box_score_urls(
            _season_page(),
            "https://files.12thman.com/history/football/years/2010.html",
            2010,
        )
        self.assertEqual(13, len(urls))
        self.assertTrue(urls[0].endswith("/ta01-sfa.html"))
        with self.assertRaises(AuthorityViolation):
            discover_box_score_urls(
                _season_page(folder="2011-2012", ext="htm"),
                "https://files.12thman.com/history/football/years/2010.html",
                2010,
            )

    def test_recap_is_not_a_box_score(self) -> None:
        body = b'<html><body><h2>Football: 2010 Season Stats</h2><a href="../recaps/2010-2011/ta01-sfa.html">Box Score</a></body></html>'
        with self.assertRaises(AuthorityViolation):
            discover_box_score_urls(body, "https://files.12thman.com/history/football/years/2010.html", 2010)

    def test_duplicate_jersey_numbers_remain_candidates(self) -> None:
        rows = parse_roster_rows(_roster_page(), 2010)
        self.assertEqual(3, len(rows))
        self.assertEqual(["8", "2", "2"], [row["jersey_raw"] for row in rows])
        self.assertTrue(all(row["availability"] == "NOT_ESTABLISHED" for row in rows))
        self.assertTrue(all(row["identity_status"] == "SOURCE_PLAYER_CANDIDATE" for row in rows))

    def test_pdf_wrapper_is_not_pdf_content(self) -> None:
        self.assertEqual(
            "PDF_WRAPPER_NOT_PDF_CONTENT",
            pdf_capture_disposition(
                "https://12thman.com/documents/1f488230-3dd2-41a8-89e2-acc2f040c7f8.pdf",
                b"<!DOCTYPE html><html><body>viewer</body></html>",
                "text/html",
                200,
            ),
        )

    def test_committed_gate_is_src014_not_ncaa(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        self.assertEqual(SOURCE_ID, gate["source_id"])
        self.assertEqual(PASS_CLASSIFICATION, gate["classification"])
        self.assertEqual(PROTECTED_LANE, gate["protected_lane"])
        self.assertEqual(0, gate["counts"]["ncaa_contest_ids_created"])
        self.assertEqual(13, gate["counts"]["box_scores_captured_2010"])
        self.assertEqual(13, gate["counts"]["box_scores_captured_2011"])
        self.assertEqual(WMT_ACQUISITION_IDENTITY, gate["preserved_wmt_identities"]["acquisition_identity"])
        self.assertTrue(all(item.get("historical_publication_time") is None for item in gate["captures"]))

    def test_truthful_gate_validates(self) -> None:
        result = validate_artifact(
            data_root=DATA_ROOT if LAKE_READY else Path(tempfile.mkdtemp()),
            repo_root=ROOT,
            require_rebuild=LAKE_READY,
        )
        self.assertEqual("PASS", result["result"])

    def test_changed_box_count_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        counts = json.loads(json.dumps(gate["counts"]))
        counts["box_scores_captured_2010"] = 999
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, counts=counts))

    def test_fabricated_box_url_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        urls = json.loads(json.dumps(gate["discovered_box_score_urls"]))
        urls["2010"][0] = "https://files.12thman.com/history/football/stats/2010-2011/ta99-zzz.html"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                data_root=DATA_ROOT,
                repo_root=ROOT,
                require_rebuild=False,
                gate=_mutated(gate, discovered_box_score_urls=urls),
            )

    def test_changed_timestamp_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        captures = json.loads(json.dumps(gate["captures"]))
        captures[0]["timestamp"] = "1999-01-01T00:00:00Z"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, captures=captures))

    def test_changed_raw_hash_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        captures = json.loads(json.dumps(gate["captures"]))
        captures[0]["raw_sha256"] = "00" * 32
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, captures=captures))

    def test_pdf_wrapper_reclassified_as_success_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        captures = json.loads(json.dumps(gate["captures"]))
        counts = json.loads(json.dumps(gate["counts"]))
        for item in captures:
            if item["page_family"] == "documents":
                item["parser_disposition"] = "VERIFIED_OFFICIAL_DOCUMENT"
        counts["documents_captured"] = 2
        counts["pdf_wrappers_rejected"] = 0
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                data_root=DATA_ROOT,
                repo_root=ROOT,
                require_rebuild=False,
                gate=_mutated(gate, captures=captures, counts=counts),
            )

    def test_ncaa_contest_id_invention_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        counts = json.loads(json.dumps(gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, counts=counts))

    def test_protected_lane_opened_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                data_root=DATA_ROOT,
                repo_root=ROOT,
                require_rebuild=False,
                gate=_mutated(gate, protected_lane="OPEN"),
            )

    def test_forged_completion_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                data_root=DATA_ROOT,
                repo_root=ROOT,
                require_rebuild=False,
                gate=_mutated(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"),
            )

    def test_unmounted_compact_still_binds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = validate_artifact(data_root=Path(tmp), repo_root=ROOT, require_rebuild=False)
        self.assertEqual("NOT_MOUNTED", result["external_reconstruction"])

    def test_network_forbidden_env_blocks_live_http(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, NETWORK_ACCESS_FORBIDDEN_ERROR):
            with patch.dict(os.environ, {"AGGIE_ANALYTICS_NETWORK_FORBIDDEN": "1"}, clear=False):
                direct_http_get("https://files.12thman.com/history/football/years/2010.html")


if __name__ == "__main__":
    unittest.main()
