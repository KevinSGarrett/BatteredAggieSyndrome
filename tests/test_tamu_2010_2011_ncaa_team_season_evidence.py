from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.tamu_ncaa_team_season_evidence import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    PASS_CLASSIFICATION,
    PROTECTED_LANE,
    TAMU_SEEDS,
    bind_team_season,
    compute_gate_identity,
    extract_official_nav_routes,
    load_json,
    official_page_uri,
    parse_header_record,
    parse_roster_tables,
    parse_schedule_table,
    parse_stat_tables,
    parse_tables,
    reject_interstitial,
    validate_artifact,
    validate_seeded_official_uri,
)

DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))


def _team_page(season: int = 2010, seed: str = "137387") -> bytes:
    return f"""<html><body>
    NCAA Texas A&amp;M Aggies ({season})
    <nav>
      <a href="/teams/{seed}">Schedule/Results</a>
      <a href="/teams/{seed}/roster">Roster</a>
      <a href="/teams/{seed}/season_to_date_stats">Team Statistics</a>
    </nav>
    <table class="mytable">
      <tr class="heading"><td>Schedule/Results</td></tr>
      <tr class="grey_heading"><th>Date</th><th>Opponent</th><th>Result</th></tr>
      <tr><td>09/04/{season}</td><td>@ SFA</td><td>W 48 - 7</td></tr>
      <tr><td>09/11/{season}</td><td>Louisiana Tech</td><td>L 10 - 16</td></tr>
    </table>
    </body></html>""".encode("utf-8")


class TeamSeasonEvidenceTests(unittest.TestCase):
    def test_seeded_routes_are_deterministic(self) -> None:
        self.assertEqual(official_page_uri("137387", "roster"), "https://stats.ncaa.org/teams/137387/roster")
        with self.assertRaises(AuthorityViolation):
            official_page_uri("136982", "roster")
        with self.assertRaises(AuthorityViolation):
            validate_seeded_official_uri("https://stats.ncaa.org/teams/137387/box_score", "137387", "roster")

    def test_nav_routes_come_from_official_team_page(self) -> None:
        routes = extract_official_nav_routes(_team_page(), "137387")
        self.assertEqual(routes["roster"], "https://stats.ncaa.org/teams/137387/roster")
        self.assertEqual(routes["season_to_date_stats"], "https://stats.ncaa.org/teams/137387/season_to_date_stats")

    def test_schedule_parses_by_headers_and_preserves_raw_strings(self) -> None:
        schedule = parse_schedule_table(parse_tables(_team_page()), 2010)
        self.assertEqual(2, schedule["row_count"])
        self.assertEqual(1, schedule["wins"])
        self.assertEqual(1, schedule["losses"])
        self.assertEqual("09/04/2010", schedule["rows"][0]["game_date_raw"])
        self.assertIsNone(schedule["rows"][0]["contest_id"])

    def test_login_page_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            reject_interstitial(b"<html>" + b"please sign in to continue " * 80)

    def test_missing_team_season_binding_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            bind_team_season(_team_page().replace(b"137387", b"000000"), "137387", 2010)

    def test_duplicate_schedule_rows_are_rejected(self) -> None:
        body = _team_page().replace(
            b"<tr><td>09/11/2010</td><td>Louisiana Tech</td><td>L 10 - 16</td></tr>",
            b"<tr><td>09/04/2010</td><td>@ SFA</td><td>W 48 - 7</td></tr>",
        )
        with self.assertRaises(AuthorityViolation):
            parse_schedule_table(parse_tables(body), 2010)

    def test_impossible_score_is_rejected(self) -> None:
        body = _team_page().replace(b"W 48 - 7", b"W 4800 - 7")
        with self.assertRaises(AuthorityViolation):
            parse_schedule_table(parse_tables(body), 2010)

    def test_roster_membership_does_not_establish_availability(self) -> None:
        body = b"""<html><body>NCAA Texas A&amp;M 137387 2010
        <table><tr class="grey_heading"><th>No</th><th>Name</th><th>Pos</th></tr>
        <tr><td>8</td><td>Jeff Fuller</td><td>WR</td></tr></table></body></html>"""
        roster = parse_roster_tables(parse_tables(body))
        self.assertEqual(1, roster["row_count"])
        self.assertEqual("NOT_ESTABLISHED", roster["pregame_availability"])
        self.assertEqual("OFFICIAL_TEAM_SEASON_MEMBERSHIP_ONLY", roster["members"][0]["authority"])

    def test_season_totals_are_not_per_game_official(self) -> None:
        body = b"""<html><body>NCAA
        <table><tr class="grey_heading"><th>Statistic</th><th>Value</th></tr>
        <tr><td>Total Offense</td><td>412</td></tr></table></body></html>"""
        stats = parse_stat_tables(parse_tables(body))
        self.assertFalse(stats["per_game_box_authority"])
        self.assertEqual("RETROSPECTIVE_UNLESS_HISTORICAL_KNOWN_AT_PROVEN", stats["tables"][0]["temporal_class"])

    def test_header_record_binds_to_aggies_not_dropdown_records(self) -> None:
        body = (
            b"<html>NCAA <li>2026-27 Football (0-0)</li>"
            b'<a href="http://www.12thman.com">Texas A&amp;M Aggies</a> (9-4)</html>'
        )
        record = parse_header_record(body)
        self.assertEqual({"wins": 9, "losses": 4, "ties": 0, "raw": record["raw"]}, record)

    def test_score_only_results_are_derived_not_invented_contest_ids(self) -> None:
        body = _team_page().replace(b"W 48 - 7", b"48 - 7").replace(b"L 10 - 16", b"10 - 16")
        schedule = parse_schedule_table(parse_tables(body), 2010)
        self.assertEqual("DERIVED_FROM_OFFICIAL_SCORE", schedule["rows"][0]["result_code_source"])
        self.assertEqual("W", schedule["rows"][0]["result_code"])
        self.assertIsNone(schedule["rows"][0]["contest_id"])

    def test_cached_official_team_pages_parse_26_games_without_contest_ids(self) -> None:
        data_root = Path(r"C:\BatteredAggieSyndrome.data")
        pages = {
            2010: data_root
            / "raw/SRC-015/ncaa_team_season_discovery/3cdb205a98242b335cc742a81ddbc66f4352bf0ce68387130d17534e5f3712d7.html",
            2011: data_root
            / "raw/SRC-015/ncaa_team_season_discovery/aa332e8213295ca49a09899d72e5549484d81c1dc566599064c9ac0d0096dac3.html",
        }
        if not all(path.is_file() for path in pages.values()):
            self.skipTest("official team-page lake payloads are not on this machine")
        for season, path in pages.items():
            body = path.read_bytes()
            seed = TAMU_SEEDS[str(season)]
            bind_team_season(body, seed, season)
            routes = extract_official_nav_routes(body, seed)
            schedule = parse_schedule_table(parse_tables(body), season)
            self.assertEqual(13, schedule["row_count"])
            self.assertTrue(all(row["contest_id"] is None for row in schedule["rows"]))
            self.assertEqual(routes["roster"], f"https://stats.ncaa.org/teams/{seed}/roster")

    def test_lane_and_seeds_remain_closed(self) -> None:
        self.assertEqual(PROTECTED_LANE, "RETAIN_PROTECTED_LANE_BLOCKED")
        self.assertEqual(TAMU_SEEDS["2010"], "137387")
        self.assertEqual(PASS_CLASSIFICATION.endswith("CANDIDATE_ONLY"), True)

    def _committed_gate(self) -> dict:
        path = ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("team-season gate is not present")
        return load_json(path)

    def _rehashed(self, gate: dict, mutator) -> dict:
        tampered = json.loads(json.dumps(gate))
        mutator(tampered)
        tampered["gate_identity"] = compute_gate_identity(tampered)
        return tampered

    def _reject(self, gate: dict) -> None:
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=True, gate=gate)

    def test_truthful_committed_gate_passes_independent_reconstruction(self) -> None:
        result = validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=True)
        self.assertEqual("PASS", result["result"])
        self.assertEqual(
            "dc06984fa17285abf6e9d32a362dd1515ff528fed82eff77254fb8abb702d91e",
            result["gate_identity"],
        )

    def test_bypass_a_changed_official_routes_attempted_after_rehash(self) -> None:
        def mutate(gate: dict) -> None:
            gate["counts"]["official_routes_attempted"] = 999

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_bypass_b_changed_2010_points_for_after_rehash(self) -> None:
        def mutate(gate: dict) -> None:
            gate["domains"]["points_for_against"]["2010"]["value"]["points_for"] = 999

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_changed_status_403_to_200_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["attempts"][0]["status"] = 200

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_changed_attempt_url_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["attempts"][0]["url"] = "https://stats.ncaa.org/teams/137387/box_score"
            gate["attempts"][0]["final_url"] = gate["attempts"][0]["url"]

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_changed_attempt_timestamp_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["attempts"][0]["timestamp"] = "1999-01-01T00:00:00Z"

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_changed_raw_hash_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            digest = "00" * 32
            gate["attempts"][0]["raw_sha256"] = digest
            gate["attempts"][0]["response_sha256"] = digest

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_missing_raw_payload_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["attempts"][0]["raw_relative_path"] = (
                "raw/SRC-015/ncaa_team_season_evidence/" + ("ab" * 32) + ".html"
            )

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_changed_season_total_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["domains"]["points_for_against"]["2011"]["value"]["points_against"] = 1

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_changed_wlt_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["domains"]["wins_losses_ties"]["2010"]["value"]["wins"] = 13

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_changed_team_season_seed_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["tamu_seeds"]["2010"] = "000000"

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_protected_lane_opened_after_rehash_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["protected_lane"] = "OPEN"
            gate["scientific_nonclaims"]["protected_lane_opened"] = True
            gate["authority"]["protected_outcome_authority"] = True

        self._reject(self._rehashed(self._committed_gate(), mutate))

    def test_completion_forged_after_rehash_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["result"] = "FORGED_DONE"
            gate["classification"] = "PRODUCTION_CHAMPION"
            gate["admissions"]["per_game_official_completion"] = True

        self._reject(self._rehashed(self._committed_gate(), mutate))


if __name__ == "__main__":
    unittest.main()
