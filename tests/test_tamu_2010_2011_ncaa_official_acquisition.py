from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.data.tamu_2010_2011_ncaa_official_acquisition import (  # noqa: E402
    AUBURN_SEEDS,
    CONTRACT_ID,
    HONEST_NEGATIVE,
    PASS_CLASSIFICATION,
    PROTECTED_LANE,
    TAMU_SEEDS,
    AuthorityViolation,
    compute_gate_identity,
    decide_disposition,
    expected_authority,
    expected_gate_document,
    expected_scientific_nonclaims,
    load_contract,
    load_transport_contract,
    reconcile_target,
    validate_artifact,
)


def _target(*, season: int, opponent: str, game_date: str, ncaa_date: str | None = None) -> dict[str, object]:
    return {
        "season": season,
        "game_date": game_date,
        "opponent_name": opponent,
        "phase3_reconciliation_state": "EXACT_DATE_SCORE_OPPONENT_CANDIDATE",
        "phase3_ncaa_contest_exposure": "LEGACY_SCHEDULE_ROW_NO_CONTEST_ID",
        "ncaa_game_date": ncaa_date or game_date,
        "ncaa_opponent_display_name": opponent,
        "ncaa_opponent_team_season_id": TAMU_SEEDS[str(season)],
        "ncaa_source_row_sha256": f"{season}-{opponent}",
        "contest_id": None,
        "name_only_promotion": False,
        "name_only_unpromoted": False,
        "endpoint_attempts": [],
    }


def _synthetic_core() -> dict[str, object]:
    targets = [_target(season=2010, opponent="SFA", game_date="2010-09-04")]
    targets.extend(
        _target(season=2010, opponent=f"Opp{index}", game_date=f"2010-09-{index:02d}") for index in range(5, 17)
    )
    targets.extend(
        _target(season=2011, opponent=f"Opp{index}", game_date=f"2011-09-{index:02d}") for index in range(4, 17)
    )
    return {
        "schema_version": "aggie.data.tamu_2010_2011_ncaa_official_acquisition.v1",
        "artifact_type": "TAMU_2010_2011_NCAA_OFFICIAL_ACQUISITION_MANIFEST",
        "decision_unit": "POST-TASK-TAMU-2010-2011-NCAA-OFFICIAL-ACQUISITION-001",
        "jira_key": "BAT-571",
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "run_id": "BAT-571-TAMU-2010-2011-NCAA-OFFICIAL-V1",
        "bat_554_policy": "RELATES_ONLY_DO_NOT_REOPEN",
        "tamu_seeds": dict(TAMU_SEEDS),
        "excluded_auburn_seeds": sorted(AUBURN_SEEDS),
        "phase3_identities": {
            "matrix_identity": "1e191204aea9c008e708f367fd36352298a3af8b129af6d0fb03b11247c3fffa",
            "gate_identity": "6a88922c727a34772224ef176aebd4930815dde533893204cbca42402376da93",
        },
        "discovery_identities": {"2010": "aa" * 32, "2011": "bb" * 32},
        "disposition": HONEST_NEGATIVE,
        "counts": {
            "phase3_targets": 26,
            "games_2010": 13,
            "games_2011": 13,
            "contest_ids_2010": 0,
            "contest_ids_2011": 0,
            "contest_ids_present": 0,
            "contest_ids_fabricated": 0,
            "name_only_promotions": 0,
            "name_only_unpromoted": 1,
            "endpoint_attempts": 0,
            "legacy_schedule_records_2010": 13,
            "legacy_schedule_records_2011": 13,
            "disposition": HONEST_NEGATIVE,
        },
        "targets": targets,
        "admissions": {
            "acquisition_admission": "CANDIDATE_ONLY",
            "disposition": HONEST_NEGATIVE,
            "pregame_availability": "BLOCKED",
            "protected_lane": PROTECTED_LANE,
            "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
            "bat_554": "RELATES_ONLY_DO_NOT_REOPEN",
        },
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "contest_ids_fabricated": False,
        "protected_lane": PROTECTED_LANE,
    }


def _synthetic_expected() -> dict[str, object]:
    contract = load_contract(ROOT)
    core = _synthetic_core()
    return {
        "contract": contract,
        "core": core,
        "acquisition_identity": "cc" * 32,
        "gate": expected_gate_document(contract=contract, core=core, acquisition_identity="cc" * 32),
    }


class ContractTests(unittest.TestCase):
    def test_contract_pins_tamu_and_excludes_auburn(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(contract["contract_id"], CONTRACT_ID)
        self.assertEqual(contract["tamu_seeds"], TAMU_SEEDS)
        self.assertEqual(set(contract["excluded_auburn_seeds"]), AUBURN_SEEDS)
        self.assertEqual(contract["bat_554_policy"], "RELATES_ONLY_DO_NOT_REOPEN")
        self.assertFalse(contract["authority"]["contest_id_fabrication"])
        self.assertFalse(contract["authority"]["bat_554_reopen"])
        self.assertNotIn("136982", contract["tamu_seeds"].values())
        self.assertNotIn("16591", contract["tamu_seeds"].values())

    def test_transport_contract_stays_auburn_national_sample(self) -> None:
        contract = load_contract(ROOT)
        transport = load_transport_contract(ROOT, contract)
        self.assertEqual(transport["jira_key"], "BAT-554")
        self.assertEqual(transport["discovery"]["seed_team_season_ids"]["2010"], "136982")
        self.assertEqual(transport["discovery"]["seed_team_season_ids"]["2011"], "16591")


class ReconciliationTests(unittest.TestCase):
    def test_date_match_keeps_contest_id_null(self) -> None:
        phase3 = {
            "season": 2010,
            "game_date": "2010-09-04",
            "opponent_name": "SFA",
            "reconciliation_state": "EXACT_DATE_SCORE_CANDIDATE_WITH_EXPLICIT_CONFLICT",
            "ncaa_contest_exposure": "LEGACY_SCHEDULE_ROW_NO_CONTEST_ID",
            "name_only_promotion": False,
        }
        ncaa = [
            {
                "game_date": "2010-09-04",
                "opponent_display_name": "SFA",
                "opponent_team_season_id": "1",
                "source_row_sha256": "abc",
                "contest_id": None,
            }
        ]
        row = reconcile_target(phase3, ncaa)
        self.assertIsNone(row["contest_id"])
        self.assertFalse(row["name_only_promotion"])
        self.assertFalse(row["name_only_unpromoted"])

    def test_name_only_is_not_promoted_and_does_not_invent_contest_id(self) -> None:
        phase3 = {
            "season": 2011,
            "game_date": "2011-11-25",
            "opponent_name": "Texas",
            "reconciliation_state": "UNRESOLVED_NAME_ONLY_NOT_PROMOTED",
            "ncaa_contest_exposure": "NAME_ONLY_CANDIDATE_NOT_PROMOTED",
            "name_only_promotion": False,
        }
        ncaa = [
            {
                "game_date": "2011-11-24",
                "opponent_display_name": "Texas",
                "opponent_team_season_id": "2",
                "source_row_sha256": "def",
                "contest_id": None,
            }
        ]
        row = reconcile_target(phase3, ncaa)
        self.assertIsNone(row["contest_id"])
        self.assertFalse(row["name_only_promotion"])
        self.assertTrue(row["name_only_unpromoted"])

    def test_legacy_row_with_contest_id_is_rejected(self) -> None:
        phase3 = {
            "season": 2010,
            "game_date": "2010-09-04",
            "opponent_name": "SFA",
            "reconciliation_state": "EXACT_DATE_SCORE_OPPONENT_CANDIDATE",
            "ncaa_contest_exposure": "LEGACY_SCHEDULE_ROW_NO_CONTEST_ID",
            "name_only_promotion": False,
        }
        ncaa = [{"game_date": "2010-09-04", "opponent_display_name": "SFA", "contest_id": "999999"}]
        with self.assertRaises(AuthorityViolation):
            reconcile_target(phase3, ncaa)

    def test_honest_negative_when_legacy_schema_and_empty_contest_ids(self) -> None:
        discoveries = {
            2010: {"link_schema": "LEGACY_SCHEDULE_RESULT_ROW", "contest_ids": []},
            2011: {"link_schema": "LEGACY_SCHEDULE_RESULT_ROW", "contest_ids": []},
        }
        self.assertEqual(decide_disposition(discoveries), HONEST_NEGATIVE)


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

    def test_auburn_seed_rejected(self) -> None:
        seeds = dict(self.gate["tamu_seeds"])
        seeds["2010"] = "136982"
        self._reject(self._mutated_gate(tamu_seeds=seeds))

    def test_invented_contest_ids_rejected(self) -> None:
        counts = dict(self.gate["counts"])
        counts["contest_ids_2010"] = 13
        counts["contest_ids_present"] = 13
        self._reject(self._mutated_gate(counts=counts))

    def test_bat_554_reopen_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["bat_554_reopen"] = True
        self._reject(self._mutated_gate(authority=authority))

    def test_completeness_and_pit_and_protected_claims_rejected(self) -> None:
        for key in ("completeness_claim", "historical_pit_admission", "protected_outcome_authority"):
            authority = dict(self.gate["authority"])
            authority[key] = True
            self._reject(self._mutated_gate(authority=authority))

    def test_forged_terminal_after_rehash_rejected(self) -> None:
        self._reject(self._mutated_gate(result="FORGED_DONE", classification="PRODUCTION_CHAMPION"))


class LiveArtifactTests(unittest.TestCase):
    def test_live_rebuild_when_payloads_present(self) -> None:
        data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        html_2010 = data_root / (
            "raw/SRC-015/ncaa_team_season_discovery/"
            "3cdb205a98242b335cc742a81ddbc66f4352bf0ce68387130d17534e5f3712d7.html"
        )
        html_2011 = data_root / (
            "raw/SRC-015/ncaa_team_season_discovery/"
            "aa332e8213295ca49a09899d72e5549484d81c1dc566599064c9ac0d0096dac3.html"
        )
        try:
            import polars  # noqa: F401
        except ImportError:
            self.skipTest("optional data-engineering environment is not mounted")
        if not html_2010.is_file() or not html_2011.is_file():
            self.skipTest("external TAMU NCAA team-page payloads are not mounted")
        from aggie_analytics.data.tamu_2010_2011_ncaa_official_acquisition import rebuild_expected

        expected = rebuild_expected(data_root=data_root, repo_root=ROOT, allow_live=False)
        self.assertEqual(expected["core"]["counts"]["phase3_targets"], 26)
        self.assertEqual(expected["core"]["counts"]["contest_ids_2010"], 0)
        self.assertEqual(expected["core"]["counts"]["contest_ids_2011"], 0)
        self.assertEqual(expected["core"]["disposition"], HONEST_NEGATIVE)
        self.assertFalse(expected["core"]["contest_ids_fabricated"])
        texas_2011 = [
            row
            for row in expected["core"]["targets"]
            if int(row["season"]) == 2011 and row["opponent_name"] == "Texas"
        ]
        self.assertEqual(len(texas_2011), 1)
        self.assertTrue(texas_2011[0]["name_only_unpromoted"])
        self.assertFalse(texas_2011[0]["name_only_promotion"])
        self.assertIsNone(texas_2011[0]["contest_id"])
        gate = ROOT / "artifacts" / "data_lake" / "tamu_2010_2011_ncaa_official_acquisition_gate.json"
        if not gate.is_file():
            self.skipTest("acquisition gate has not been materialized yet")
        validated = validate_artifact(data_root=data_root, repo_root=ROOT, require_rebuild=True)
        self.assertEqual(validated["result"], "PASS")
        self.assertEqual(validated["disposition"], HONEST_NEGATIVE)


if __name__ == "__main__":
    unittest.main()
