from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.data.development_2023_outcomes import (  # noqa: E402
    CONTRACT_RELATIVE,
    LABEL_AVAILABILITY_POLICY,
    OUTCOME_EFFECTIVE_UNAVAILABLE_REASON,
    SUPERSEDED_CYCLE6_IDENTITY,
    SUPERSEDED_KICKOFF_IDENTITY,
    assert_complementary_team_labels,
    assert_label_chronology,
    classify_source_row,
    compute_gate_identity,
    conservative_eligibility_bound,
    expected_parent_identities,
    field_schema_sha256,
    identity_core,
    load_contract,
    materialize_team_observations,
    outcome_result,
    population_from_rows,
    stable_hash,
    team_result,
    validate_artifact,
    verify_protected_registry,
    verify_schema_reconciliation_fingerprint,
)
from aggie_analytics.validation.protected_split_authority import (  # noqa: E402
    assert_labels_cannot_override_protected_membership,
    sha256_file,
)


def _source_row(**overrides: object) -> dict[str, object]:
    row = {
        "id": 401520000,
        "season": 2023,
        "seasonType": "regular",
        "week": 1,
        "startDate": "2023-08-26T16:00:00.000Z",
        "completed": True,
        "neutralSite": False,
        "homeId": 245,
        "awayId": 99,
        "homePoints": 31,
        "awayPoints": 10,
    }
    row.update(overrides)
    return row


def _maps() -> tuple[dict[str, dict[str, str]], dict[str, str], dict[str, dict[str, object]], dict[str, dict[str, object]], dict[str, str]]:
    games = {
        "401520000": {
            "canonical_id": "game_aaa",
            "home_team_id": "team_home",
            "away_team_id": "team_away",
            "start_time_utc": "2023-08-26T16:00:00Z",
            "season": "2023",
        }
    }
    teams = {"245": "team_home", "99": "team_away"}
    spine = {
        "401520000": {
            "home_points": 31,
            "away_points": 10,
            "canonical_game_id": "game_aaa",
        }
    }
    ncaa = {
        "game_aaa": {
            "status": "AGREEMENT",
            "ncaa_contest_id": "c1",
            "official_home_points": 31,
            "official_away_points": 10,
        }
    }
    source = {
        "source_payload_sha256": "a" * 64,
        "capture_id": "cap_test",
        "capture_known_at_utc": "2026-08-09T16:57:56Z",
        "canonical_registry_sha256": "b" * 64,
    }
    return games, teams, spine, ncaa, source


def _classify(row: dict[str, object], **kwargs: object):
    games, teams, spine, ncaa, source = _maps()
    games = kwargs.get("games", games)
    teams = kwargs.get("teams", teams)
    spine = kwargs.get("spine", spine)
    ncaa = kwargs.get("ncaa", ncaa)
    source = kwargs.get("source", source)
    return classify_source_row(
        row,
        games=games,
        teams=teams,
        spine=spine,
        ncaa=ncaa,
        source=source,
        seen_source=set(kwargs.get("seen_source", set())),
        seen_canonical=set(kwargs.get("seen_canonical", set())),
    )


class Development2023OutcomeUnitTests(unittest.TestCase):
    def test_contract_authority_is_label_only(self) -> None:
        contract = load_contract(ROOT)
        self.assertTrue(contract["authority"]["development_2023_label_use"])
        self.assertFalse(contract["authority"]["pregame_feature_use"])
        self.assertFalse(contract["authority"]["protected_evaluation_admission"])
        self.assertFalse(contract["authority"]["champion_or_production_promotion"])
        self.assertEqual(contract["acceptance"]["allowed_seasons"], [2023])
        self.assertEqual(contract["acceptance"]["forbidden_seasons"], [2024, 2025])
        self.assertEqual(contract["contract_id"], "BAT-565-2023-DEVELOPMENT-OUTCOME-IDENTITY-V3")
        self.assertNotIn("available_only_after_completion", contract["label_semantics"])
        self.assertTrue(contract["label_semantics"]["source_completed_final_required"])
        self.assertFalse(contract["label_semantics"]["verified_completion_timestamp_available"])
        self.assertFalse(contract["label_semantics"]["historical_label_availability_proven"])
        self.assertEqual(
            contract["label_semantics"]["label_eligibility_basis"],
            "PRECOMMITTED_RETROSPECTIVE_POLICY_BOUND",
        )

    def test_protected_registry_pin_and_label_override_fail_closed(self) -> None:
        contract = load_contract(ROOT)
        digest = verify_protected_registry(ROOT, contract)
        self.assertEqual(digest, contract["source_contract"]["protected_split_registry_sha256"])
        self.assertEqual(
            assert_labels_cannot_override_protected_membership(ROOT, 2024, "DEVELOPMENT_ONLY"),
            "PROTECTED_TEST",
        )
        self.assertEqual(
            assert_labels_cannot_override_protected_membership(ROOT, 2025, "DEVELOPMENT_TUNE"),
            "PROTECTED_TEST",
        )

    def test_schema_reconciliation_fingerprint_still_bound(self) -> None:
        contract = load_contract(ROOT)
        verify_schema_reconciliation_fingerprint(
            ROOT, contract["source_contract"]["observed_schema_reconciliation_fingerprint"]
        )

    def test_field_schema_hash_is_sorted_keys(self) -> None:
        self.assertEqual(
            field_schema_sha256([{"b": 1, "a": 2}, {"a": 3, "b": 4}]),
            stable_hash(["a", "b"]),
        )

    def test_accepts_completed_oriented_2023_row(self) -> None:
        accepted, quarantine, ncaa = _classify(_source_row())
        self.assertIsNone(quarantine)
        assert accepted is not None
        self.assertEqual(accepted["season"], 2023)
        self.assertTrue(accepted["not_a_pregame_feature"])
        self.assertTrue(accepted["development_label_only"])
        self.assertFalse(accepted["protected_eligible"])
        self.assertEqual(accepted["ncaa_status"], "AGREEMENT")
        self.assertEqual(ncaa["exact_canonical_match"], True)
        self.assertEqual(
            accepted["label_available_after_utc"],
            conservative_eligibility_bound(accepted["start_time_utc"]),
        )
        self.assertGreater(
            accepted["label_available_after_utc"], accepted["start_time_utc"]
        )
        self.assertIsNone(accepted["outcome_effective_at_utc"])
        self.assertEqual(
            accepted["outcome_effective_unavailable_reason"],
            OUTCOME_EFFECTIVE_UNAVAILABLE_REASON,
        )
        self.assertEqual(accepted["label_availability_policy"], LABEL_AVAILABILITY_POLICY)
        self.assertEqual(accepted["outcome_observed_at_utc"], "2026-08-09T16:57:56Z")
        observations = materialize_team_observations([accepted])
        self.assertEqual(len(observations), 2)
        self.assertEqual({row["site"] for row in observations}, {"HOME", "AWAY"})
        self.assertEqual({row["result"] for row in observations}, {"WIN", "LOSS"})
        contract = {
            "source_contract": {"capture_known_at_utc": "2026-08-09T16:57:56Z"},
            "label_availability_policy": {"offset_hours": 24},
        }
        assert_label_chronology([accepted], observations, contract)
        assert_complementary_team_labels([accepted], observations)

    def test_protected_year_insertion_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            _classify(_source_row(season=2024))
        with self.assertRaises(ValueError):
            _classify(_source_row(season=2025))

    def test_incomplete_game_is_quarantined(self) -> None:
        accepted, quarantine, _ = _classify(_source_row(completed=False))
        self.assertIsNone(accepted)
        assert quarantine is not None
        self.assertEqual(quarantine["reason_code"], "INCOMPLETE_GAME")

    def test_canceled_or_suspended_game_is_quarantined(self) -> None:
        accepted, quarantine, _ = _classify(_source_row(notes="canceled"))
        self.assertIsNone(accepted)
        assert quarantine is not None
        self.assertEqual(quarantine["reason_code"], "NON_FINAL_GAME")
        accepted, quarantine, _ = _classify(_source_row(status="suspended"))
        self.assertIsNone(accepted)
        assert quarantine is not None
        self.assertEqual(quarantine["reason_code"], "NON_FINAL_GAME")

    def test_missing_scores_are_quarantined(self) -> None:
        accepted, quarantine, _ = _classify(_source_row(homePoints=None))
        self.assertIsNone(accepted)
        assert quarantine is not None
        self.assertEqual(quarantine["reason_code"], "MISSING_SCORES")

    def test_duplicate_source_game_is_quarantined(self) -> None:
        accepted, quarantine, _ = _classify(_source_row(), seen_source={"401520000"})
        self.assertIsNone(accepted)
        assert quarantine is not None
        self.assertEqual(quarantine["reason_code"], "DUPLICATE_SOURCE_GAME")

    def test_reversed_home_away_is_quarantined(self) -> None:
        accepted, quarantine, _ = _classify(_source_row(homeId=99, awayId=245))
        self.assertIsNone(accepted)
        assert quarantine is not None
        self.assertEqual(quarantine["reason_code"], "HOME_AWAY_ORIENTATION_MISMATCH")

    def test_mismatched_canonical_ids_are_quarantined(self) -> None:
        _, _, spine, ncaa, source = _maps()
        games = {
            "401520000": {
                "canonical_id": "game_aaa",
                "home_team_id": "team_home",
                "away_team_id": "team_away",
                "start_time_utc": "2023-08-26T16:00:00Z",
                "season": "2023",
            }
        }
        spine = {
            "401520000": {
                "home_points": 31,
                "away_points": 10,
                "canonical_game_id": "game_other",
            }
        }
        accepted, quarantine, _ = classify_source_row(
            _source_row(),
            games=games,
            teams={"245": "team_home", "99": "team_away"},
            spine=spine,
            ncaa=ncaa,
            source=source,
            seen_source=set(),
            seen_canonical=set(),
        )
        self.assertIsNone(accepted)
        assert quarantine is not None
        self.assertEqual(quarantine["reason_code"], "CANONICAL_ID_MISMATCH")

    def test_ncaa_score_conflict_is_quarantined(self) -> None:
        ncaa = {
            "game_aaa": {
                "status": "AGREEMENT",
                "ncaa_contest_id": "c1",
                "official_home_points": 99,
                "official_away_points": 0,
            }
        }
        accepted, quarantine, _ = _classify(_source_row(), ncaa=ncaa)
        self.assertIsNone(accepted)
        assert quarantine is not None
        self.assertEqual(quarantine["reason_code"], "NCAA_SCORE_CONFLICT")

    def test_altered_source_hash_changes_identity(self) -> None:
        left = identity_core(
            contract_sha256="c" * 64,
            source={
                "source_payload_sha256": "a" * 64,
                "capture_id": "cap",
                "canonical_registry_sha256": "b" * 64,
                "ncaa_comparisons_sha256": "d" * 64,
                "outcome_spine_completed_sha256": "e" * 64,
            },
            record_hashes={"accepted_game_outcomes": "f" * 64},
            population={
                "source_rows": 1,
                "accepted_games": 1,
                "team_observations": 2,
                "quarantine_rows": 0,
                "ties": 0,
                "ncaa_agreements": 1,
                "ncaa_missing_official_linescore": 0,
                "ncaa_no_comparison_row": 0,
            },
            classification="DEVELOPMENT_ONLY_2023_OUTCOME_LABELS",
        )
        right = dict(left)
        right["source_payload_sha256"] = "1" * 64
        self.assertNotEqual(stable_hash(left), stable_hash(right))

    def test_altered_row_hash_is_detected_after_outer_recompute(self) -> None:
        accepted, _, _ = _classify(_source_row())
        assert accepted is not None
        tampered = dict(accepted)
        tampered["home_points"] = 99
        recomputed = stable_hash({key: value for key, value in tampered.items() if key != "row_lineage_sha256"})
        self.assertNotEqual(recomputed, accepted["row_lineage_sha256"])
        outer = identity_core(
            contract_sha256="c" * 64,
            source={
                "source_payload_sha256": "a" * 64,
                "capture_id": "cap",
                "canonical_registry_sha256": "b" * 64,
                "ncaa_comparisons_sha256": "d" * 64,
                "outcome_spine_completed_sha256": "e" * 64,
            },
            record_hashes={"accepted_game_outcomes": accepted["row_lineage_sha256"]},
            population={
                "source_rows": 1,
                "accepted_games": 1,
                "team_observations": 2,
                "quarantine_rows": 0,
                "ties": 0,
                "ncaa_agreements": 1,
                "ncaa_missing_official_linescore": 0,
                "ncaa_no_comparison_row": 0,
            },
            classification="DEVELOPMENT_ONLY_2023_OUTCOME_LABELS",
        )
        tampered_outer = dict(outer)
        tampered_outer["record_hashes"] = {"accepted_game_outcomes": recomputed}
        self.assertNotEqual(stable_hash(outer), stable_hash(tampered_outer))

    def test_population_counts_are_derived(self) -> None:
        accepted, _, ncaa = _classify(_source_row())
        assert accepted is not None
        observations = materialize_team_observations([accepted])
        population = population_from_rows([accepted], observations, [], [ncaa], 1)
        self.assertEqual(population["accepted_games"], 1)
        self.assertEqual(population["team_observations"], 2)
        self.assertEqual(population["ncaa_agreements"], 1)
        self.assertEqual(outcome_result(7, 7), "TIE")
        self.assertEqual(team_result(7, 7), "TIE")

    def test_kickoff_time_label_availability_is_rejected(self) -> None:
        accepted, _, _ = _classify(_source_row())
        assert accepted is not None
        observations = materialize_team_observations([accepted])
        accepted["label_available_after_utc"] = accepted["start_time_utc"]
        accepted["conservative_eligibility_bound_utc"] = accepted["start_time_utc"]
        contract = {
            "source_contract": {"capture_known_at_utc": "2026-08-09T16:57:56Z"},
            "label_availability_policy": {"offset_hours": 24},
        }
        with self.assertRaisesRegex(ValueError, "not strictly after kickoff"):
            assert_label_chronology([accepted], observations, contract)

    def test_availability_before_kickoff_is_rejected(self) -> None:
        accepted, _, _ = _classify(_source_row())
        assert accepted is not None
        observations = materialize_team_observations([accepted])
        accepted["label_available_after_utc"] = "2023-08-26T15:00:00Z"
        accepted["conservative_eligibility_bound_utc"] = "2023-08-26T15:00:00Z"
        contract = {
            "source_contract": {"capture_known_at_utc": "2026-08-09T16:57:56Z"},
            "label_availability_policy": {"offset_hours": 24},
        }
        with self.assertRaisesRegex(ValueError, "not strictly after kickoff"):
            assert_label_chronology([accepted], observations, contract)

    def test_zero_offset_bound_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not strictly after kickoff"):
            conservative_eligibility_bound("2023-08-26T16:00:00Z", 0)
        with self.assertRaisesRegex(ValueError, "not strictly after kickoff"):
            _classify(_source_row(), source={**_maps()[4], "conservative_offset_hours": 0})

    def test_result_attached_to_non_final_game_is_rejected(self) -> None:
        accepted, _, _ = _classify(_source_row())
        assert accepted is not None
        observations = materialize_team_observations([accepted])
        accepted["completed"] = False
        contract = {
            "source_contract": {"capture_known_at_utc": "2026-08-09T16:57:56Z"},
            "label_availability_policy": {"offset_hours": 24},
        }
        with self.assertRaisesRegex(ValueError, "non-final game received a development label"):
            assert_label_chronology([accepted], observations, contract)

    def test_protected_year_row_is_rejected_by_chronology_guard(self) -> None:
        accepted, _, _ = _classify(_source_row())
        assert accepted is not None
        observations = materialize_team_observations([accepted])
        accepted["season"] = 2024
        contract = {
            "source_contract": {"capture_known_at_utc": "2026-08-09T16:57:56Z"},
            "label_availability_policy": {"offset_hours": 24},
        }
        with self.assertRaisesRegex(ValueError, "protected 2024/2025"):
            assert_label_chronology([accepted], observations, contract)
        accepted["season"] = 2025
        with self.assertRaisesRegex(ValueError, "protected 2024/2025"):
            assert_label_chronology([accepted], observations, contract)

    def test_team_opponent_label_mismatch_is_rejected(self) -> None:
        accepted, _, _ = _classify(_source_row())
        assert accepted is not None
        observations = materialize_team_observations([accepted])
        observations[0]["result"] = "WIN"
        observations[1]["result"] = "WIN"
        with self.assertRaisesRegex(ValueError, "not complementary"):
            assert_complementary_team_labels([accepted], observations)

    def test_duplicate_game_team_row_is_rejected(self) -> None:
        accepted, _, _ = _classify(_source_row())
        assert accepted is not None
        observations = materialize_team_observations([accepted])
        observations.append(dict(observations[0]))
        contract = {
            "source_contract": {"capture_known_at_utc": "2026-08-09T16:57:56Z"},
            "label_availability_policy": {"offset_hours": 24},
        }
        with self.assertRaisesRegex(ValueError, "duplicate game-team"):
            assert_label_chronology([accepted], observations, contract)

    def test_contract_file_hash_is_stable_utf8(self) -> None:
        path = ROOT / CONTRACT_RELATIVE
        self.assertTrue(path.is_file())
        self.assertEqual(len(sha256_file(path)), 64)


class Development2023OutcomeLiveRebuildTests(unittest.TestCase):
    def test_live_rebuild_when_data_root_present(self) -> None:
        data_root = Path(r"C:\BatteredAggieSyndrome.data")
        if not (
            data_root / "raw" / "SRC-002" / "games"
            / "sha256_ebf9ea175c3332102dd4555fd8cd126cbd2cbc6cef4aebe95c6c5ae7af1dea03.json"
        ).is_file():
            self.skipTest("external 2023 capture is not mounted")
        from aggie_analytics.data.development_2023_outcomes import rebuild_expected

        expected = rebuild_expected(data_root=data_root, repo_root=ROOT)
        self.assertEqual(expected["population"]["accepted_games"], 910)
        self.assertEqual(expected["population"]["team_observations"], 1820)
        self.assertEqual(expected["population"]["seasons"], [2023])
        self.assertNotIn(2024, expected["population"]["seasons"])
        self.assertNotIn(2025, expected["population"]["seasons"])
        from aggie_analytics.data.development_2023_outcomes import validate_artifact

        validated = validate_artifact(data_root=data_root, repo_root=ROOT, require_rebuild=True)
        self.assertEqual(validated["result"], "PASS")
        self.assertNotEqual(validated["dataset_identity"], SUPERSEDED_KICKOFF_IDENTITY)
        self.assertNotEqual(validated["dataset_identity"], SUPERSEDED_CYCLE6_IDENTITY)
        self.assertEqual(validated["supersedes"], SUPERSEDED_CYCLE6_IDENTITY)
        self.assertEqual(validated["also_forbids"], SUPERSEDED_KICKOFF_IDENTITY)
        self.assertEqual(expected["parent_identities"], expected_parent_identities(load_contract(ROOT)))
        for row in expected["accepted"]:
            self.assertGreater(row["label_available_after_utc"], row["start_time_utc"])
            self.assertIsNone(row["outcome_effective_at_utc"])
            self.assertEqual(row["label_availability_policy"], LABEL_AVAILABILITY_POLICY)


class Development2023OutcomeMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        source = (
            cls.data_root
            / "raw"
            / "SRC-002"
            / "games"
            / "sha256_ebf9ea175c3332102dd4555fd8cd126cbd2cbc6cef4aebe95c6c5ae7af1dea03.json"
        )
        gate_path = ROOT / "artifacts/pit/development_2023_outcome_gate.json"
        if not source.is_file() or not gate_path.is_file():
            raise unittest.SkipTest("external 2023 capture or outcome gate is not mounted")
        from aggie_analytics.data.development_2023_outcomes import rebuild_expected

        cls.expected = rebuild_expected(data_root=cls.data_root, repo_root=ROOT)
        cls.gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if cls.gate.get("dataset_identity") == SUPERSEDED_KICKOFF_IDENTITY:
            raise unittest.SkipTest("corrected BAT-565 identity has not been rematerialized yet")
        manifest_path = (
            cls.data_root
            / "manifests"
            / "development_outcomes"
            / "sha256"
            / cls.expected["dataset_identity"]
            / "development_2023_outcome_manifest.json"
        )
        if not manifest_path.is_file():
            raise unittest.SkipTest("corrected BAT-565 manifest has not been rematerialized yet")
        cls.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def _mutated_gate(self, **changes: object) -> dict[str, object]:
        tampered = json.loads(json.dumps(self.gate))
        tampered.update(changes)
        tampered["gate_identity"] = compute_gate_identity(tampered)
        return tampered

    def _reject(self, gate: dict[str, object], manifest: dict[str, object] | None = None) -> None:
        with self.assertRaises(ValueError):
            validate_artifact(
                data_root=self.data_root,
                repo_root=ROOT,
                require_rebuild=True,
                gate=gate,
                manifest=self.manifest if manifest is None else manifest,
                expected=self.expected,
            )

    def test_altered_source_identity_is_rejected(self) -> None:
        identities = dict(self.gate["input_identities"])
        identities["source_payload_sha256"] = "1" * 64
        self._reject(self._mutated_gate(input_identities=identities))

    def test_altered_parent_identity_is_rejected(self) -> None:
        identities = json.loads(json.dumps(self.gate["input_identities"]))
        identities["parent_identities"]["BAT-523_replay"] = "0" * 64
        self._reject(self._mutated_gate(input_identities=identities))

    def test_missing_payload_is_rejected(self) -> None:
        omitted = json.loads(json.dumps(self.manifest))
        omitted["payloads"] = list(self.manifest["payloads"][1:])
        self._reject(self._mutated_gate(), omitted)

    def test_substituted_payload_is_rejected(self) -> None:
        substituted = json.loads(json.dumps(self.manifest))
        substituted["payloads"][0]["sha256"] = "2" * 64
        payloads = json.loads(json.dumps(self.gate["payloads"]))
        payloads[0]["sha256"] = "2" * 64
        self._reject(self._mutated_gate(payloads=payloads), substituted)

    def test_altered_result_classification_is_rejected(self) -> None:
        self._reject(self._mutated_gate(result="PASS_PRODUCTION_READY"))
        self._reject(self._mutated_gate(classification="PROTECTED_PERFORMANCE"))

    def test_altered_completion_semantics_is_rejected(self) -> None:
        semantics = dict(self.gate["label_semantics"])
        semantics["availability_boundary_strictly_after_kickoff"] = False
        semantics["label_availability_policy"] = "GAME_START_UTC"
        self._reject(self._mutated_gate(label_semantics=semantics))

    def test_altered_protected_nonclaims_are_rejected(self) -> None:
        nonclaims = dict(self.gate["scientific_nonclaims"])
        nonclaims["protected_performance_claimed"] = True
        self._reject(self._mutated_gate(scientific_nonclaims=nonclaims))

    def test_altered_issue_completion_state_is_rejected(self) -> None:
        completion = dict(self.gate["issue_completion"])
        completion["issue_complete"] = False
        completion["workflow_state"] = "IN_PROGRESS"
        self._reject(self._mutated_gate(issue_completion=completion))

    def test_forged_terminal_state_after_identity_recompute_is_rejected(self) -> None:
        forged = self._mutated_gate(result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        self.assertNotEqual(forged["gate_identity"], self.gate["gate_identity"])
        self._reject(forged)


if __name__ == "__main__":
    unittest.main()
