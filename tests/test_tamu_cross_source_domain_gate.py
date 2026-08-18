from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.data.tamu_cross_source_domain_gate import (  # noqa: E402
    ADMITTED_DECISIONS,
    BAT429_BLOCKED_REASON,
    BAT429_UNBLOCK,
    CONTEST_ROUTE_DISPOSITION,
    CONTEST_ROUTE_GATE_IDENTITY,
    CONTRACT_ID,
    DOMAIN_COLUMNS,
    NCAA_NATIONAL_IDENTITY,
    PHASE3_GATE_IDENTITY,
    PHASE3_MATRIX_IDENTITY,
    PHASE4_ACQUISITION_IDENTITY,
    PHASE4_DISPOSITION,
    PROTECTED_LANE,
    SEASON_RECON_GATE_IDENTITY,
    TEAM_SEASON_GATE_IDENTITY,
    AuthorityViolation,
    build_domain_rows,
    compute_gate_identity,
    decide_domain,
    expected_authority,
    expected_gate_document,
    expected_scientific_nonclaims,
    inspect_bat429,
    load_contract,
    load_json,
    validate_artifact,
)


def _game(**overrides: object) -> dict[str, object]:
    row = {
        "row_identity": "game-sfa-2010",
        "season": 2010,
        "game_date": "2010-09-04",
        "opponent_name": "SFA",
        "reconciliation_state": "EXACT_DATE_SCORE_OPPONENT_CANDIDATE",
        "name_only_promotion": False,
        "contest_id": None,
        "contest_id_fabricated": False,
        "pregame_availability": False,
        "conflicts": [],
    }
    row.update(overrides)
    return row


def _synthetic_games() -> list[dict[str, object]]:
    games = [_game()]
    games.extend(
        _game(row_identity=f"2010-{index}", opponent_name=f"Opp{index}", game_date=f"2010-09-{index:02d}")
        for index in range(5, 17)
    )
    games.extend(
        _game(
            row_identity=f"2011-{index}",
            season=2011,
            opponent_name=f"Opp{index}",
            game_date=f"2011-09-{index:02d}",
        )
        for index in range(4, 16)
    )
    games.append(
        _game(
            row_identity="2011-texas-name-only",
            season=2011,
            opponent_name="Texas",
            game_date="2011-11-25",
            reconciliation_state="UNRESOLVED_NAME_ONLY_NOT_PROMOTED",
        )
    )
    return games


def _synthetic_expected() -> dict[str, object]:
    contract = load_contract(ROOT)
    games = _synthetic_games()
    rows = build_domain_rows(games)
    bat_429 = inspect_bat429(ROOT)
    season_recon = load_json(ROOT / "artifacts" / "data_lake" / "tamu_2010_2011_season_reconciliation_gate.json")
    return {
        "contract": contract,
        "games": games,
        "rows": rows,
        "bat_429": bat_429,
        "season_recon": season_recon,
        "gate": expected_gate_document(
            contract=contract,
            rows=rows,
            bat_429=bat_429,
            season_recon=season_recon,
        ),
    }


class DecisionTests(unittest.TestCase):
    def test_name_only_stays_candidate_and_is_not_cross_source(self) -> None:
        game = _game(reconciliation_state="UNRESOLVED_NAME_ONLY_NOT_PROMOTED")
        admitted = decide_domain(game, "linescore_game_info")
        self.assertEqual(admitted["decision"], "CANDIDATE_ONLY")
        self.assertEqual(admitted["reason"], "SIDEARM_SCHEDULE_ONLY_NAME_ONLY_NCAA_NOT_PROMOTED")
        self.assertNotIn("ncaa_legacy", admitted["sources"])

    def test_silent_name_only_merge_is_rejected(self) -> None:
        with self.assertRaises(AuthorityViolation):
            decide_domain(_game(name_only_promotion=True), "linescore_game_info")

    def test_wrong_officials_decision_cannot_be_verified(self) -> None:
        admitted = decide_domain(_game(), "officials")
        self.assertEqual(admitted["decision"], "SOURCE_EVIDENCE_ABSENT")
        self.assertEqual(admitted["ncaa_http"], "NOT_ATTEMPTED_NO_CONTEST_ID")
        self.assertFalse(admitted["verified_official"])

    def test_participation_is_not_availability(self) -> None:
        participation = decide_domain(_game(), "participation")
        availability = decide_domain(_game(), "pregame_availability")
        self.assertEqual(participation["decision"], "SOURCE_EVIDENCE_ABSENT")
        self.assertEqual(availability["decision"], "SOURCE_EVIDENCE_ABSENT")
        self.assertFalse(participation["pregame_available"])
        self.assertFalse(availability["pregame_available"])
        with self.assertRaises(AuthorityViolation):
            decide_domain(_game(pregame_availability=True), "participation")

    def test_conflict_is_field_grain(self) -> None:
        game = _game(conflicts=["DATE_SCORE_MATCH_OPPONENT_NAME_CONFLICT"])
        self.assertEqual(decide_domain(game, "linescore_game_info")["decision"], "CONFLICT_REVIEW_REQUIRED")
        self.assertEqual(decide_domain(game, "officials")["decision"], "SOURCE_EVIDENCE_ABSENT")

    def test_every_game_domain_gets_exactly_one_admitted_decision(self) -> None:
        rows = build_domain_rows(_synthetic_games())
        self.assertEqual(len(rows), 26 * len(DOMAIN_COLUMNS))
        self.assertEqual({row["decision"] for row in rows}, {"CANDIDATE_ONLY", "SOURCE_EVIDENCE_ABSENT"})
        self.assertTrue(all(row["decision"] in ADMITTED_DECISIONS for row in rows))
        self.assertFalse(any(row["decision"].startswith("VERIFIED") for row in rows))


class MutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        cls.expected = _synthetic_expected()
        cls.gate = cls.expected["gate"]

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

    def test_missing_phase3_bind_rejected(self) -> None:
        identities = dict(self.gate["input_identities"])
        identities.pop("phase3_matrix_identity")
        self._reject(self._mutated_gate(input_identities=identities))

    def test_missing_phase4_bind_rejected(self) -> None:
        identities = dict(self.gate["input_identities"])
        identities.pop("phase4_acquisition_identity")
        self._reject(self._mutated_gate(input_identities=identities))

    def test_wrong_domain_decision_rejected(self) -> None:
        counts = dict(self.gate["counts"])
        counts["verified_official"] = 1
        counts["source_evidence_absent"] = counts["source_evidence_absent"] - 1
        self._reject(self._mutated_gate(counts=counts))

    def test_forged_verified_after_rehash_rejected(self) -> None:
        self._reject(self._mutated_gate(result="FORGED_VERIFIED_OFFICIAL", classification="VERIFIED_OFFICIAL"))

    def test_participation_as_availability_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["participation_as_availability"] = True
        self._reject(self._mutated_gate(authority=authority))

    def test_bat_429_marked_ready_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["bat_429_ready_or_done"] = True
        self._reject(self._mutated_gate(authority=authority))
        bat_429 = dict(self.gate["bat_429"])
        bat_429["ready_or_done"] = True
        bat_429["workflow_state"] = "READY"
        self._reject(self._mutated_gate(bat_429=bat_429))

    def test_protected_lane_opened_rejected(self) -> None:
        self._reject(self._mutated_gate(protected_lane="OPEN_PROTECTED_LANE"))

    def test_missing_cycle8_bind_rejected(self) -> None:
        identities = dict(self.gate["input_identities"])
        identities.pop("contest_route_gate_identity")
        self._reject(self._mutated_gate(input_identities=identities))

    def test_season_total_promoted_to_per_game_official_rejected(self) -> None:
        season_level = dict(self.gate["season_level_admissions"])
        season_level["per_game_verified_official"] = True
        self._reject(self._mutated_gate(season_level_admissions=season_level))

    def test_membership_promoted_to_availability_rejected(self) -> None:
        season_level = dict(self.gate["season_level_admissions"])
        season_level["membership_as_availability"] = True
        self._reject(self._mutated_gate(season_level_admissions=season_level))

    def test_name_only_texas_promotion_rejected(self) -> None:
        season_level = dict(self.gate["season_level_admissions"])
        season_level["texas_2011"] = "VERIFIED_CROSS_SOURCE"
        self._reject(self._mutated_gate(season_level_admissions=season_level))

    def test_forged_completion_after_rehash_rejected(self) -> None:
        self._reject(self._mutated_gate(result="FORGED_PER_GAME_OFFICIAL_COMPLETE"))


class LiveArtifactTests(unittest.TestCase):
    def test_contract_and_bat429_classification(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(contract["contract_id"], CONTRACT_ID)
        self.assertEqual(contract["identities"]["phase3_matrix_identity"], PHASE3_MATRIX_IDENTITY)
        self.assertEqual(contract["identities"]["phase3_gate_identity"], PHASE3_GATE_IDENTITY)
        self.assertEqual(contract["identities"]["phase4_acquisition_identity"], PHASE4_ACQUISITION_IDENTITY)
        self.assertEqual(
            contract["identities"]["ncaa_official_national_acquisition_identity"],
            NCAA_NATIONAL_IDENTITY,
        )
        self.assertEqual(contract["identities"]["phase4_disposition"], PHASE4_DISPOSITION)
        self.assertEqual(contract["identities"]["team_season_gate_identity"], TEAM_SEASON_GATE_IDENTITY)
        self.assertEqual(
            contract["identities"]["season_reconciliation_gate_identity"],
            SEASON_RECON_GATE_IDENTITY,
        )
        self.assertEqual(contract["identities"]["contest_route_gate_identity"], CONTEST_ROUTE_GATE_IDENTITY)
        self.assertEqual(contract["identities"]["contest_route_disposition"], CONTEST_ROUTE_DISPOSITION)
        self.assertFalse(contract["authority"]["verified_official_inflation"])
        bat_429 = inspect_bat429(ROOT)
        self.assertEqual(bat_429["blocked_reason"], BAT429_BLOCKED_REASON)
        self.assertEqual(bat_429["unblock_condition"], BAT429_UNBLOCK)
        self.assertFalse(bat_429["ready_or_done"])
        self.assertNotIn(bat_429["workflow_state"], {"READY", "Ready", "DONE", "Done"})

    def test_live_rebuild_when_payloads_present(self) -> None:
        data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        parquet = (
            data_root
            / "features"
            / "tamu_official_evidence_gap_matrix"
            / "sha256"
            / PHASE3_MATRIX_IDENTITY
            / "game_rows.parquet"
        )
        try:
            import polars  # noqa: F401
        except ImportError:
            self.skipTest("optional data-engineering environment is not mounted")
        if not parquet.is_file():
            self.skipTest("Phase 3 matrix payload is not mounted")
        from aggie_analytics.data.tamu_cross_source_domain_gate import rebuild_expected

        expected = rebuild_expected(data_root=data_root, repo_root=ROOT)
        self.assertEqual(expected["gate"]["counts"]["scheduled_games"], 26)
        self.assertEqual(expected["gate"]["counts"]["verified_official"], 0)
        self.assertEqual(expected["gate"]["phase4_disposition"], PHASE4_DISPOSITION)
        self.assertEqual(expected["gate"]["contest_route_disposition"], CONTEST_ROUTE_DISPOSITION)
        self.assertEqual(
            expected["gate"]["season_level_admissions"]["grain"],
            "SEASON_LEVEL_NOT_PER_GAME",
        )
        self.assertFalse(expected["gate"]["season_level_admissions"]["per_game_verified_official"])
        self.assertEqual(expected["gate"]["protected_lane"], PROTECTED_LANE)
        self.assertEqual(expected["gate"]["authority"], expected_authority())
        self.assertEqual(expected["gate"]["scientific_nonclaims"], expected_scientific_nonclaims())
        texas = [
            row
            for row in expected["rows"]
            if int(row["season"]) == 2011
            and row["opponent_name"] == "Texas"
            and row["domain"] == "linescore_game_info"
        ]
        self.assertEqual(len(texas), 1)
        self.assertTrue(texas[0]["name_only_unpromoted"])
        self.assertEqual(texas[0]["decision"], "CANDIDATE_ONLY")
        gate = ROOT / "artifacts" / "data_lake" / "tamu_cross_source_domain_gate.json"
        if not gate.is_file():
            self.skipTest("domain gate has not been materialized yet")
        validated = validate_artifact(data_root=data_root, repo_root=ROOT, require_rebuild=True)
        self.assertEqual(validated["result"], "PASS")
        self.assertEqual(validated["protected_lane"], PROTECTED_LANE)
        self.assertEqual(validated["counts"]["verified_official"], 0)


if __name__ == "__main__":
    unittest.main()
