from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.data.ncaa_contest_reconciliation import (  # noqa: E402
    parse_tamu_sidearm_schedule_page,
)
from aggie_analytics.data.tamu_official_evidence_gap_matrix import (  # noqa: E402
    AUBURN_SEEDS,
    CONTRACT_ID,
    NCAA_ENDPOINTS,
    PASS_CLASSIFICATION,
    PASS_RESULT,
    PROTECTED_LANE,
    TAMU_2010_TEAM_SEASON,
    TAMU_2011_TEAM_SEASON,
    AuthorityViolation,
    compute_gate_identity,
    compute_matrix_identity,
    empty_domains,
    expected_admissions,
    expected_authority,
    expected_gate_document,
    expected_remaining_blockers,
    expected_scientific_nonclaims,
    load_contract,
    missing_endpoint_document,
    special_path_fingerprint,
    validate_artifact,
)


def _synthetic_row(*, season: int, opponent: str, game_date: str, suffix: str) -> dict[str, object]:
    return {
        "row_identity": f"{season}-{suffix}",
        "season": season,
        "source_lane": "WMT_SIDEARM_SCHEDULE" if season in {2010, 2011} else "WMT_GAMEBOOK",
        "game_date": game_date,
        "opponent_name": opponent,
        "opponent_name_normalized": opponent.lower(),
        "venue_state": "HOME_OR_NEUTRAL_UNKNOWN",
        "source_result": "W",
        "source_team_points": 21,
        "opponent_points": 14,
        "wmt_exposure": "SCHEDULE_HTML_NO_BOXSCORE_LINK",
        "wmt_boxscore_id": None,
        "wmt_game_id": None,
        "contest_id": None,
        "boxscore_id": None,
        "contest_id_fabricated": False,
        "ncaa_team_season_id": TAMU_2010_TEAM_SEASON if season == 2010 else TAMU_2011_TEAM_SEASON if season == 2011 else None,
        "ncaa_contest_exposure": "LEGACY_SCHEDULE_ROW_NO_CONTEST_ID",
        "candidate_contest_ids": [],
        "reconciliation_state": "EXACT_DATE_SCORE_OPPONENT_CANDIDATE",
        "name_only_promotion": False,
        "conflicts": [],
        "domains": empty_domains(present=("linescore_game_info",)),
        "ncaa_endpoints": missing_endpoint_document(),
        "team_box_join_state": "NOT_JOINED_NO_SHARED_CANONICAL_GAME_ID",
        "player_box_join_state": "NOT_JOINED_NO_SHARED_CANONICAL_GAME_ID",
        "historical_known_at_state": "UNKNOWN_CAPTURE_TIME_ONLY",
        "pregame_availability": False,
        "remaining_blockers": expected_remaining_blockers(),
        "source_row_sha256": suffix,
        "source_page_raw_sha256": suffix,
    }


def _synthetic_expected() -> dict[str, object]:
    contract = load_contract(ROOT)
    rows = [
        _synthetic_row(season=2010, opponent="SFA", game_date="2010-09-04", suffix="a"),
        _synthetic_row(season=2011, opponent="SMU", game_date="2011-09-04", suffix="b"),
        _synthetic_row(season=2012, opponent="Florida", game_date="2012-09-08", suffix="c"),
    ]
    return {
        "contract": contract,
        "rows": rows,
        "ncaa_lake_notes": dict(contract["ncaa_lake_notes"]),
        "matrix_identity": compute_matrix_identity(rows),
    }


class SidearmParserTests(unittest.TestCase):
    def test_parser_uses_recap_year_for_january_bowl_and_keeps_contest_ids_none(self) -> None:
        html = """
        <table class="schedule-events-table__table">
          <tbody>
            <tr class="schedule-table-item">
              <strong class="schedule-event-default__name schedule-event-default__name--current">Texas A&amp;M</strong>
              <strong class="schedule-event-default__divider">vs.</strong>
              <strong class="schedule-event-default__name"><span>(#11)</span> LSU</strong>
              <div class="schedule-event-item-result__label">
                <strong class="schedule-event-item-result__loss"> L, </strong>
                <span class="sr-only">Loss</span> 24-41
              </div>
              <a href="/news/2011/01/7/texas-am-loses-cotton-bowl-41-24">Recap</a>
            </tr>
            <tr class="schedule-table-item">
              <strong class="schedule-event-default__name schedule-event-default__name--current">Texas A&amp;M</strong>
              <strong class="schedule-event-default__divider">at</strong>
              <strong class="schedule-event-default__name">Oklahoma St.</strong>
              <div class="schedule-event-item-result__label">
                <strong class="schedule-event-item-result__loss"> L, </strong>
                <span class="sr-only">Loss</span> 35-38
              </div>
              <a href="/news/2010/09/30/aggies-fall-to-oklahoma-state-38-35">Recap</a>
            </tr>
          </tbody>
        </table>
        """
        page, rows = parse_tamu_sidearm_schedule_page(html, season_title_year=2010, raw_sha256="abc")
        self.assertEqual(page["parsed_schedule_rows"], 2)
        self.assertEqual(page["boxscore_link_count"], 0)
        self.assertFalse(page["contest_ids_fabricated"])
        self.assertEqual(rows[0]["source_schedule_date"], "2011-01-07")
        self.assertEqual(rows[0]["opponent_team_name"], "LSU")
        self.assertEqual(rows[0]["venue_state"], "HOME_OR_NEUTRAL_UNKNOWN")
        self.assertIsNone(rows[0]["contest_id"])
        self.assertIsNone(rows[0]["boxscore_id"])
        self.assertEqual(rows[1]["venue_state"], "AWAY")
        self.assertEqual(rows[1]["source_schedule_date"], "2010-09-30")
        self.assertTrue(all(row["contest_id"] is None for row in rows))

    def test_parser_skips_rows_with_boxscore_links(self) -> None:
        html = """
        <table class="schedule-events-table__table">
          <tbody>
            <tr class="schedule-table-item">
              <strong class="schedule-event-default__divider">vs.</strong>
              <strong class="schedule-event-default__name">SFA</strong>
              <div class="schedule-event-item-result__label"><strong class="schedule-event-item-result__win"> W, </strong> 48-7</div>
              <a href="/news/2010/09/4/opener">Recap</a>
              <a href="/boxscore.aspx?id=1">Box</a>
            </tr>
          </tbody>
        </table>
        """
        page, rows = parse_tamu_sidearm_schedule_page(html, season_title_year=2010, raw_sha256="abc")
        self.assertEqual(rows, [])
        self.assertEqual(page["parsed_schedule_rows"], 0)
        self.assertEqual(page["boxscore_link_count"], 1)


class GapMatrixUnitTests(unittest.TestCase):
    def test_contract_fail_closes_authority(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(contract["contract_id"], CONTRACT_ID)
        self.assertFalse(contract["authority"]["completeness_claim"])
        self.assertFalse(contract["authority"]["contest_id_fabrication"])
        self.assertFalse(contract["authority"]["name_only_promotion"])
        self.assertFalse(contract["authority"]["protected_outcome_authority"])
        self.assertEqual(contract["ncaa_lake_notes"]["auburn_contract_seed_2010"], "136982")
        self.assertEqual(contract["ncaa_lake_notes"]["auburn_contract_seed_2011"], "16591")
        self.assertIn(contract["ncaa_lake_notes"]["auburn_contract_seed_2010"], AUBURN_SEEDS)
        self.assertNotIn(TAMU_2010_TEAM_SEASON, AUBURN_SEEDS)
        self.assertNotIn(TAMU_2011_TEAM_SEASON, AUBURN_SEEDS)

    def test_missing_endpoints_are_explicit(self) -> None:
        document = missing_endpoint_document()
        self.assertEqual(set(document), set(NCAA_ENDPOINTS))
        self.assertTrue(all(item["cache_present"] is False for item in document.values()))
        self.assertTrue(all(item["contest_id"] is None for item in document.values()))

    def test_admissions_keep_protected_lane_blocked(self) -> None:
        admissions = expected_admissions()
        self.assertEqual(admissions["protected_lane"], PROTECTED_LANE)
        self.assertEqual(admissions["pregame_availability"], "BLOCKED")


class GapMatrixMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        cls.expected = _synthetic_expected()
        cls.gate = expected_gate_document(cls.expected)

    def _mutated_gate(self, **changes: object) -> dict[str, object]:
        tampered = json.loads(json.dumps(self.gate))
        tampered.update(changes)
        tampered["gate_identity"] = compute_gate_identity(tampered)
        return tampered

    def _reject(self, gate: dict[str, object]) -> None:
        with self.assertRaises((ValueError, AuthorityViolation, FileNotFoundError)):
            validate_artifact(
                data_root=self.data_root,
                repo_root=ROOT,
                require_rebuild=True,
                gate=gate,
                expected=self.expected,
            )

    def test_honest_synthetic_gate_passes(self) -> None:
        validated = validate_artifact(
            data_root=self.data_root,
            repo_root=ROOT,
            require_rebuild=True,
            gate=self.gate,
            expected=self.expected,
        )
        self.assertEqual(validated["result"], "PASS")
        self.assertEqual(self.gate["result"], PASS_RESULT)
        self.assertEqual(self.gate["classification"], PASS_CLASSIFICATION)
        self.assertFalse(self.gate["contest_ids_fabricated"])

    def test_silent_name_only_promotion_is_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["name_only_promotion"] = True
        self._reject(self._mutated_gate(authority=authority))

    def test_swapped_opponent_is_rejected(self) -> None:
        special = json.loads(json.dumps(self.gate["special_path"]))
        special["opponents"] = list(reversed(special["opponents"]))
        self._reject(self._mutated_gate(special_path=special))

    def test_wrong_date_is_rejected(self) -> None:
        special = json.loads(json.dumps(self.gate["special_path"]))
        special["dates"] = ["1999-01-01" for _ in special["dates"]]
        self._reject(self._mutated_gate(special_path=special))

    def test_duplicate_contest_assignment_is_rejected(self) -> None:
        special = json.loads(json.dumps(self.gate["special_path"]))
        special["contest_ids"] = ["555", "555"]
        special["duplicate_contest_assignments"] = 1
        self._reject(self._mutated_gate(special_path=special))

    def test_protected_outcome_authority_is_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["protected_outcome_authority"] = True
        self._reject(self._mutated_gate(authority=authority))

    def test_capture_time_labeled_as_historical_known_at_is_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["historical_known_at_from_capture_time"] = True
        self._reject(self._mutated_gate(authority=authority))

    def test_participation_relabeled_availability_is_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["participation_as_availability"] = True
        self._reject(self._mutated_gate(authority=authority))

    def test_omitted_missing_endpoint_is_rejected(self) -> None:
        counts = dict(self.gate["counts"])
        counts["missing_ncaa_endpoints"] = 0
        self._reject(self._mutated_gate(counts=counts))

    def test_inflated_coverage_is_rejected(self) -> None:
        counts = dict(self.gate["counts"])
        counts["scheduled_games_2010_2025"] = 999
        self._reject(self._mutated_gate(counts=counts))

    def test_missing_or_substituted_payload_is_rejected(self) -> None:
        with self.assertRaises((ValueError, AuthorityViolation, FileNotFoundError)):
            validate_artifact(
                data_root=self.data_root / "_missing_gap_matrix_payload",
                repo_root=ROOT,
                require_rebuild=True,
                expected=self.expected,
            )

    def test_forged_terminal_state_after_rehash_is_rejected(self) -> None:
        forged = self._mutated_gate(result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        self.assertEqual(forged["gate_identity"], compute_gate_identity(forged))
        self.assertNotEqual(forged["gate_identity"], self.gate["gate_identity"])
        self._reject(forged)

    def test_special_path_fingerprint_has_no_contest_ids(self) -> None:
        fingerprint = special_path_fingerprint(self.expected["rows"])
        self.assertEqual(fingerprint["contest_ids"], [])
        self.assertEqual(fingerprint["duplicate_contest_assignments"], 0)
        self.assertEqual(self.gate["scientific_nonclaims"], expected_scientific_nonclaims())
        self.assertEqual(self.gate["authority"], expected_authority())


class GapMatrixLiveTests(unittest.TestCase):
    def test_live_rebuild_when_payloads_present(self) -> None:
        data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        html_2010 = data_root / (
            "raw/SRC-014/tamu_official_gamebook_equivalent/schedule_html/"
            "sha256_4fb8159c477531e7ee653125198085f96e60719ec9050355a4e2d998a08f095b.html"
        )
        gamebook = data_root / (
            "quarantine/historical_known_at/sha256/"
            "76c3b366431d5085588d07df7d8db77348ac737dc57538befe26c7080150f010/"
            "tamu_official_gamebooks/domain=game/candidate_records.parquet"
        )
        try:
            import polars  # noqa: F401
        except ImportError:
            self.skipTest("optional data-engineering environment is not mounted")
        if not html_2010.is_file() or not gamebook.is_file():
            self.skipTest("external TAMU official-evidence payloads are not mounted")
        from aggie_analytics.data.tamu_official_evidence_gap_matrix import rebuild_expected

        expected = rebuild_expected(data_root=data_root, repo_root=ROOT)
        self.assertGreaterEqual(expected["gate"]["counts"]["games_2010"], 13)
        self.assertGreaterEqual(expected["gate"]["counts"]["games_2011"], 13)
        self.assertEqual(expected["gate"]["counts"]["contest_ids_fabricated"], 0)
        self.assertEqual(expected["gate"]["counts"]["contest_ids_present"], 0)
        self.assertFalse(expected["gate"]["contest_ids_fabricated"])
        texas_2011 = [
            row
            for row in expected["rows"]
            if row["season"] == 2011 and row["opponent_name"] == "Texas"
        ]
        self.assertEqual(len(texas_2011), 1)
        self.assertEqual(texas_2011[0]["reconciliation_state"], "UNRESOLVED_NAME_ONLY_NOT_PROMOTED")
        self.assertFalse(texas_2011[0]["name_only_promotion"])
        self.assertIsNone(texas_2011[0]["contest_id"])
        self.assertEqual(expected["gate"]["admissions"]["protected_lane"], PROTECTED_LANE)
        gate = ROOT / "artifacts" / "data_lake" / "tamu_official_evidence_gap_matrix_gate.json"
        if not gate.is_file():
            self.skipTest("gap-matrix gate has not been materialized yet")
        validated = validate_artifact(data_root=data_root, repo_root=ROOT, require_rebuild=True)
        self.assertEqual(validated["result"], "PASS")


if __name__ == "__main__":
    unittest.main()
