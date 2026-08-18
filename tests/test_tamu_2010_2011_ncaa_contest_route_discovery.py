from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.tamu_ncaa_contest_route_discovery import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    PASS_CLASSIFICATION,
    PROTECTED_LANE,
    TAMU_SEEDS,
    compute_gate_identity,
    detect_conflicting_official_routes,
    extract_contest_hrefs,
    extract_official_candidates,
    load_contract,
    load_json,
    official_url,
    reject_error_or_redirect_page,
    reject_guessed_numeric_id,
    reject_opponent_date_only_identity,
    reject_third_party_as_ncaa_id,
    reject_wrong_season_contest,
    validate_artifact,
)

DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))


MODERN_FIXTURE = b"""<html><body>NCAA Texas A&amp;M 2022
<a href="/teams/544634">Schedule</a>
<a href="/contests/2276794/box_score">W 24 - 23</a>
</body></html>"""

LEGACY_FIXTURE = b"""<html><body>NCAA Texas A&amp;M Aggies (9-4)
<a href="/teams/137387">Schedule/Results</a>
<a href="/teams/137387/roster">Roster</a>
<a href="/teams/137387/season_to_date_stats">Team Statistics</a>
<table class="mytable">
<tr class="heading"><td>Schedule/Results</td></tr>
<tr class="grey_heading"><th>Date</th><th>Opponent</th><th>Result</th></tr>
<tr><td>11/25/2010</td><td><a href="/teams/137391">Texas</a></td><td>W 24 - 17</td></tr>
<tr><td>09/04/2010</td><td><a href="/teams/137374">@ SFA</a></td><td>W 48 - 7</td></tr>
</table>
</body></html>"""


class ContestRouteDiscoveryTests(unittest.TestCase):
    def test_contract_is_fail_closed(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(TAMU_SEEDS, contract["tamu_seeds"])
        self.assertEqual(PROTECTED_LANE, "RETAIN_PROTECTED_LANE_BLOCKED")
        self.assertTrue(PASS_CLASSIFICATION.endswith("CANDIDATE_ONLY"))
        self.assertEqual("href_/contests/{id}/box_score_on_official_team_page", contract["modern_comparison"]["method"])

    def test_modern_fixture_extracts_contest_ids(self) -> None:
        self.assertEqual(["2276794"], extract_contest_hrefs(MODERN_FIXTURE))

    def test_legacy_fixture_has_zero_contest_ids(self) -> None:
        self.assertEqual([], extract_contest_hrefs(LEGACY_FIXTURE))

    def test_legacy_candidates_include_opponent_and_not_guessed_contests(self) -> None:
        candidates = extract_official_candidates(LEGACY_FIXTURE, seed="137387", season=2010)
        urls = {item["url"] for item in candidates}
        self.assertIn("https://stats.ncaa.org/teams/137391", urls)
        self.assertTrue(all("/contests/" not in item["url"] for item in candidates))

    def test_guessed_numeric_id_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            reject_guessed_numeric_id("312610245", set())

    def test_opponent_date_only_identity_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            reject_opponent_date_only_identity({"ncaa_contest_id": None, "promoted_from": "opponent_date_only"})

    def test_third_party_id_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            reject_third_party_as_ncaa_id("https://www.sports-reference.com/cfb/boxscores/2010-11-25-texas.html")

    def test_wrong_season_contest_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            reject_wrong_season_contest(b"<html>NCAA 2023 bowl</html>", 2011)

    def test_error_page_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            reject_error_or_redirect_page(b"<html>Access Denied reference #</html>", 403)
        with self.assertRaises(AuthorityViolation):
            reject_error_or_redirect_page(b"<html>moved</html>", 302)

    def test_conflicting_official_routes_are_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            detect_conflicting_official_routes("2011-11-24:Texas", ["111", "222"])

    def test_zero_attempt_semantics_when_no_contest_ids(self) -> None:
        gate_path = ROOT / GATE_RELATIVE
        if not gate_path.is_file():
            self.skipTest("contest-route gate is not present")
        gate = load_json(gate_path)
        if gate.get("discovered_contest_ids"):
            self.skipTest("a contest route was discovered")
        self.assertEqual(0, gate["counts"]["contest_endpoint_attempts"])
        self.assertEqual(0, gate["counts"]["contest_ids_discovered"])

    def test_forged_success_after_rehash_is_rejected(self) -> None:
        gate_path = ROOT / GATE_RELATIVE
        if not gate_path.is_file():
            self.skipTest("contest-route gate is not present")
        gate = load_json(gate_path)
        forged = json.loads(json.dumps(gate))
        forged["result"] = "FORGED_DONE"
        forged["classification"] = "PRODUCTION_CHAMPION"
        forged["gate_identity"] = compute_gate_identity(forged)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=forged)

    def test_official_url_rejects_non_official_host(self) -> None:
        with self.assertRaises(AuthorityViolation):
            official_url("https://example.com/contests/1/box_score")


if __name__ == "__main__":
    unittest.main()
