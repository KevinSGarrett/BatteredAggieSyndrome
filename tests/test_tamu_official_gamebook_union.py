from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.ncaa_contest_reconciliation import normalize_team_name  # noqa: E402
from aggie_analytics.data.tamu_official_gamebook_union import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    LSU_DISPOSITION,
    PASS_CLASSIFICATION,
    PROTECTED_LANE,
    TEXAS_DISPOSITION,
    WMT_DATASET_IDENTITY,
    WMT_TARGET_GAMES,
    compute_gate_identity,
    load_contract,
    load_json,
    load_official_compact_games,
    match_official_box,
    validate_artifact,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = (
    DATA_ROOT
    / "quarantine/historical_known_at/sha256/76c3b366431d5085588d07df7d8db77348ac737dc57538befe26c7080150f010/tamu_official_gamebooks/domain=game/candidate_records.parquet"
).is_file()


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


def _validate(gate: dict, *, require_rebuild: bool = False):
    return validate_artifact(
        data_root=DATA_ROOT,
        repo_root=ROOT,
        require_rebuild=require_rebuild,
        gate=gate,
    )


class UnionContractTests(unittest.TestCase):
    def test_contract_is_fail_closed(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(contract["wmt_payload_policy"], "DO_NOT_REWRITE_IN_PLACE")
        self.assertFalse(contract["authority"]["ncaa_contest_identity"])
        self.assertFalse(contract["authority"]["name_only_promotion"])
        self.assertFalse(contract["authority"]["wmt_payload_mutated_in_place"])
        self.assertTrue(PASS_CLASSIFICATION.endswith("CANDIDATE_ONLY"))
        self.assertEqual(PROTECTED_LANE, "RETAIN_PROTECTED_LANE_BLOCKED")


class MatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.official = load_official_compact_games(ROOT)

    def test_season_date_match_is_not_name_only(self) -> None:
        matched, status = match_official_box(
            {"season": 2010, "game_date": "2010-09-04", "opponent_name": "SFA"},
            self.official,
        )
        self.assertIsNotNone(matched)
        self.assertEqual(status, "MATCHED_SEASON_DATE_NOT_NAME_ONLY")
        self.assertEqual(matched["opponent_normalized"], normalize_team_name("Stephen F. Austin"))
        self.assertIsNone(matched["ncaa_contest_id"])

    def test_texas_requires_strong_tuple_not_name(self) -> None:
        matched, status = match_official_box(
            {"season": 2011, "game_date": "2011-11-25", "opponent_name": "Texas"},
            self.official,
        )
        self.assertEqual(status, TEXAS_DISPOSITION)
        self.assertEqual(matched["calendar_date"], "2011-11-24")
        self.assertEqual(matched["tamu_points"], 25)
        self.assertEqual(matched["opponent_points"], 27)

    def test_name_only_texas_without_score_tuple_does_not_invent_a_match(self) -> None:
        with self.assertRaises(AuthorityViolation):
            match_official_box(
                {"season": 2011, "game_date": "2011-11-25", "opponent_name": "Texas"},
                [item for item in self.official if item["calendar_date"] != "2011-11-24"],
            )

    def test_lsu_keeps_season_and_calendar_split(self) -> None:
        matched, status = match_official_box(
            {"season": 2010, "game_date": "2011-01-07", "opponent_name": "LSU"},
            self.official,
        )
        self.assertEqual(status, "MATCHED_SEASON_DATE_NOT_NAME_ONLY")
        self.assertEqual(matched["football_season"], 2010)
        self.assertEqual(matched["calendar_date"], "2011-01-07")
        self.assertEqual(matched["index_date_candidate"], "2010-12-31")
        self.assertEqual(matched["conflict_status"], LSU_DISPOSITION)


class UnionMutationTests(unittest.TestCase):
    def setUp(self) -> None:
        gate_path = ROOT / GATE_RELATIVE
        if not gate_path.is_file():
            self.skipTest("union gate is not present")
        self.gate = load_json(gate_path)

    def test_current_gate_validates_without_rebuild(self) -> None:
        result = _validate(self.gate, require_rebuild=False)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(self.gate["counts"]["wmt_preserved_games"], WMT_TARGET_GAMES)
        self.assertEqual(self.gate["counts"]["official_added_total"], 26)
        self.assertEqual(self.gate["wmt_layer"]["dataset_identity"], WMT_DATASET_IDENTITY)
        self.assertEqual(self.gate["texas_2011"]["disposition"], TEXAS_DISPOSITION)
        self.assertEqual(self.gate["lsu_2010"]["disposition"], LSU_DISPOSITION)

    def test_changed_union_total_is_rejected(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["union_captured_games"] = 999
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, counts=counts))

    def test_invented_ncaa_contest_id_is_rejected(self) -> None:
        games = json.loads(json.dumps(self.gate["official_games"]))
        games[0]["ncaa_contest_id"] = "999999"
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, official_games=games))

    def test_texas_name_only_is_rejected(self) -> None:
        texas = json.loads(json.dumps(self.gate["texas_2011"]))
        texas["name_only_promotion"] = True
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, texas_2011=texas))

    def test_texas_conflict_erasure_is_rejected(self) -> None:
        texas = json.loads(json.dumps(self.gate["texas_2011"]))
        texas["discrepancy_erased"] = True
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, texas_2011=texas))

    def test_lsu_silent_normalize_is_rejected(self) -> None:
        lsu = json.loads(json.dumps(self.gate["lsu_2010"]))
        lsu["silently_normalized"] = True
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, lsu_2010=lsu))

    def test_wmt_identity_rewrite_is_rejected(self) -> None:
        wmt = json.loads(json.dumps(self.gate["wmt_layer"]))
        wmt["dataset_identity"] = "00" * 32
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, wmt_layer=wmt))

    def test_protected_lane_opened_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, protected_lane="OPEN"))

    def test_forged_completion_after_rehash_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"))

    def test_rebuild_matches_when_lake_present(self) -> None:
        if not LAKE_READY:
            self.skipTest("WMT gamebook payload is not mounted")
        result = _validate(self.gate, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["external_reconstruction"], "MOUNTED")


if __name__ == "__main__":
    unittest.main()
