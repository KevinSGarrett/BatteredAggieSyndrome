from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    binding_identity,
)
from aggie_analytics.data.national_tiered_game_spine import (  # noqa: E402
    CONTRACT_ID,
    GATE_RELATIVE,
    PASS_RESULT,
    _assert_structural_invariants,
    canonical_team_id,
    compute_gate_identity,
    load_contract,
    rebuild_expected,
    resolve_tier,
    validate_artifact,
)

TIERS = load_contract(ROOT)["tiers"]


def _membership(game_id: str = "G1", **overrides: object) -> dict[str, object]:
    row = {
        "canonical_game_id": game_id,
        "tier_id": "TIER_2_ACCEPTED_SCOPED_REPLAY",
        "season": 2019,
        "season_type": "regular",
        "week": 3,
        "neutral_site": False,
        "conference_game": True,
        "venue_id": 3974,
        "home_canonical_team_id": "SRC-002:TEAM:245",
        "away_canonical_team_id": "SRC-002:TEAM:2",
        "start_date_utc_text": "2019-09-21T23:00:00.000Z",
        "start_time_tbd": False,
        "completed": True,
        "label_eligible": True,
        "label_ineligible_reason": None,
    }
    row.update(overrides)
    return row


def _pair(game_id: str = "G1", home: str = "SRC-002:TEAM:245", away: str = "SRC-002:TEAM:2"):
    base = {"canonical_game_id": game_id, "tier_id": "TIER_2_ACCEPTED_SCOPED_REPLAY", "season": 2019, "week": 3, "is_neutral_site": False}
    observations = [
        {**base, "canonical_team_id": home, "opponent_canonical_team_id": away, "is_home": True},
        {**base, "canonical_team_id": away, "opponent_canonical_team_id": home, "is_home": False},
    ]
    labels = [
        {
            "canonical_game_id": game_id,
            "canonical_team_id": home,
            "tier_id": base["tier_id"],
            "season": 2019,
            "points_for": 28,
            "points_against": 20,
            "margin": 8,
            "label_win": True,
            "label_tie": False,
        },
        {
            "canonical_game_id": game_id,
            "canonical_team_id": away,
            "tier_id": base["tier_id"],
            "season": 2019,
            "points_for": 20,
            "points_against": 28,
            "margin": -8,
            "label_win": False,
            "label_tie": False,
        },
    ]
    return observations, labels


class NationalSpineUnitTests(unittest.TestCase):
    def test_contract_pins_closed_authority_and_two_observations(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(contract["contract_id"], CONTRACT_ID)
        self.assertEqual(contract["team_observation_policy"]["observations_per_labeled_game"], 2)
        self.assertIs(contract["label_policy"]["target_game_outcome_use_admitted"], False)
        self.assertIs(
            contract["label_policy"]["capture_timestamp_treated_as_publication_time"], False
        )

    def test_tier_resolution_covers_every_declared_era(self) -> None:
        for season, expected in (
            (1963, "TIER_1_LONG_RUN_REFERENCE_CANDIDATE"),
            (2009, "TIER_1_LONG_RUN_REFERENCE_CANDIDATE"),
            (2010, "TIER_2_ACCEPTED_SCOPED_REPLAY"),
            (2022, "TIER_2_ACCEPTED_SCOPED_REPLAY"),
            (2023, "TIER_3_DEVELOPMENT_ONLY_LABELS"),
            (2024, "TIER_4_PROTECTED_SEALED"),
            (2025, "TIER_4_PROTECTED_SEALED"),
            (2026, "TIER_5_PROSPECTIVE_ABSENT"),
        ):
            with self.subTest(season=season):
                tier = resolve_tier(season, TIERS)
                assert tier is not None
                self.assertEqual(tier["tier_id"], expected)

    def test_seasons_outside_the_vocabulary_are_unresolved(self) -> None:
        self.assertIsNone(resolve_tier(1962, TIERS))
        self.assertIsNone(resolve_tier(2027, TIERS))

    def test_canonical_team_id_is_namespaced(self) -> None:
        self.assertEqual(canonical_team_id("SRC-002", 245), "SRC-002:TEAM:245")

    def test_well_formed_spine_passes_structural_invariants(self) -> None:
        observations, labels = _pair()
        _assert_structural_invariants([_membership()], observations, labels)

    def test_rejects_duplicate_game_membership(self) -> None:
        observations, labels = _pair()
        with self.assertRaisesRegex(ValueError, "duplicate canonical game membership"):
            _assert_structural_invariants([_membership(), _membership()], observations, labels)

    def test_rejects_reversed_orientation(self) -> None:
        observations, labels = _pair()
        observations[1]["is_home"] = True
        with self.assertRaisesRegex(ValueError, "non-complementary home/away orientation"):
            _assert_structural_invariants([_membership()], observations, labels)

    def test_rejects_same_game_self_observation(self) -> None:
        observations, labels = _pair(away="SRC-002:TEAM:245")
        with self.assertRaisesRegex(ValueError, "observes the same team twice"):
            _assert_structural_invariants([_membership()], observations, labels)

    def test_rejects_inconsistent_opponent_reference(self) -> None:
        observations, labels = _pair()
        observations[0]["opponent_canonical_team_id"] = "SRC-002:TEAM:999"
        with self.assertRaisesRegex(ValueError, "inconsistent opponent reference"):
            _assert_structural_invariants([_membership()], observations, labels)

    def test_rejects_a_game_without_exactly_two_observations(self) -> None:
        observations, labels = _pair()
        with self.assertRaisesRegex(ValueError, "exactly two team observations"):
            _assert_structural_invariants([_membership()], observations[:1], labels[:1])

    def test_rejects_postgame_contamination_of_a_pregame_observation(self) -> None:
        observations, labels = _pair()
        observations[0]["points_for"] = 28
        with self.assertRaisesRegex(ValueError, "carries postgame fields"):
            _assert_structural_invariants([_membership()], observations, labels)

    def test_rejects_label_margin_inconsistent_with_scores(self) -> None:
        observations, labels = _pair()
        labels[0]["margin"] = 99
        with self.assertRaisesRegex(ValueError, "margin is inconsistent"):
            _assert_structural_invariants([_membership()], observations, labels)

    def test_rejects_label_flags_inconsistent_with_margin(self) -> None:
        observations, labels = _pair()
        labels[1]["label_win"] = True
        with self.assertRaisesRegex(ValueError, "flags are inconsistent"):
            _assert_structural_invariants([_membership()], observations, labels)

    def test_rejects_labels_not_covering_observed_identities(self) -> None:
        observations, labels = _pair()
        labels[0]["canonical_team_id"] = "SRC-002:TEAM:777"
        with self.assertRaisesRegex(ValueError, "same identities"):
            _assert_structural_invariants([_membership()], observations, labels)


class NationalSpineMountedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        )
        cls.gate_path = ROOT / GATE_RELATIVE
        if not cls.gate_path.is_file() or not (cls.data_root / "canonical").is_dir():
            raise unittest.SkipTest("national tiered spine gate or data root is not mounted")
        cls.gate = json.loads(cls.gate_path.read_text(encoding="utf-8"))
        cls.expected = rebuild_expected(data_root=cls.data_root, repo_root=ROOT)
        cls.manifest = json.loads(
            (cls.data_root / cls.gate["manifest"]["relative_path"]).read_text(encoding="utf-8")
        )

    def test_independent_rebuild_validates(self) -> None:
        report = validate_artifact(
            data_root=self.data_root,
            repo_root=ROOT,
            require_rebuild=True,
            gate=self.gate,
            manifest=self.manifest,
            expected=self.expected,
        )
        self.assertEqual(report["result"], "PASS")

    def test_protected_and_prospective_tiers_carry_no_labels(self) -> None:
        by_tier = self.gate["population"]["by_tier"]
        for tier_id in ("TIER_4_PROTECTED_SEALED", "TIER_5_PROSPECTIVE_ABSENT"):
            with self.subTest(tier=tier_id):
                self.assertEqual(by_tier[tier_id]["label_eligible_games"], 0)
                self.assertEqual(by_tier[tier_id]["team_observations"], 0)
        self.assertEqual(by_tier["TIER_5_PROSPECTIVE_ABSENT"]["games"], 0)

    def test_every_labeled_game_carries_exactly_two_observations(self) -> None:
        population = self.gate["population"]
        self.assertEqual(
            population["team_observations_total"], population["label_eligible_games_total"] * 2
        )
        self.assertEqual(
            population["outcome_label_rows_total"], population["team_observations_total"]
        )

    def test_tier_counts_are_recomputed_not_summed(self) -> None:
        by_tier = self.gate["population"]["by_tier"]
        self.assertEqual(
            sum(tier["games"] for tier in by_tier.values()),
            self.gate["population"]["games_total"],
        )

    def test_development_tier_agrees_with_its_predecessor_gate(self) -> None:
        cross = self.gate["cross_check"]
        self.assertTrue(cross["tier_3_games_vs_bat565_development"]["agrees"])
        self.assertTrue(cross["tier_3_team_observations_vs_bat565_development"]["agrees"])

    def test_tier_one_gap_is_fully_explained_and_ties_agree(self) -> None:
        cross = self.gate["cross_check"]
        self.assertTrue(cross["tier_1_gap_explained_by_supplement_only_rows"]["explained"])
        self.assertTrue(cross["tier_1_cfbd_only_rows_vs_bat552"]["agrees"])
        self.assertTrue(cross["tier_1_ties_vs_bat552"]["agrees"])

    def test_unexplained_scope_difference_is_disclosed_not_hidden(self) -> None:
        cross = self.gate["cross_check"]
        self.assertFalse(cross["tier_2_games_vs_bat523_replay"]["agrees"])
        self.assertFalse(cross["tier_2_scope_difference"]["explained"])
        self.assertIs(cross["reconciliation_is_reported_not_enforced"], True)


class NationalSpineMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        )
        cls.gate_path = ROOT / GATE_RELATIVE
        if not cls.gate_path.is_file() or not (cls.data_root / "canonical").is_dir():
            raise unittest.SkipTest("national tiered spine gate or data root is not mounted")
        cls.gate = json.loads(cls.gate_path.read_text(encoding="utf-8"))
        cls.expected = rebuild_expected(data_root=cls.data_root, repo_root=ROOT)
        cls.manifest = json.loads(
            (cls.data_root / cls.gate["manifest"]["relative_path"]).read_text(encoding="utf-8")
        )

    def _forged(self, **changes: object) -> dict[str, object]:
        tampered = json.loads(json.dumps(self.gate))
        tampered.update(changes)
        tampered["gate_identity"] = compute_gate_identity(tampered)
        tampered["binding_identity"] = binding_identity(tampered, "binding_identity")
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

    def test_rejects_protected_year_labels(self) -> None:
        population = json.loads(json.dumps(self.gate["population"]))
        population["by_tier"]["TIER_4_PROTECTED_SEALED"]["label_eligible_games"] = 1854
        population["by_tier"]["TIER_4_PROTECTED_SEALED"]["team_observations"] = 3708
        self._reject(self._forged(population=population))

    def test_rejects_prospective_2026_outcomes(self) -> None:
        population = json.loads(json.dumps(self.gate["population"]))
        population["by_tier"]["TIER_5_PROSPECTIVE_ABSENT"]["team_observations"] = 2
        self._reject(self._forged(population=population))

    def test_rejects_inflated_tier_counts(self) -> None:
        population = json.loads(json.dumps(self.gate["population"]))
        population["games_total"] = int(population["games_total"]) + 10
        self._reject(self._forged(population=population))

    def test_rejects_forged_cross_check_agreement(self) -> None:
        cross = json.loads(json.dumps(self.gate["cross_check"]))
        cross["tier_2_games_vs_bat523_replay"]["agrees"] = True
        cross["tier_2_games_vs_bat523_replay"]["difference"] = 0
        self._reject(self._forged(cross_check=cross))

    def test_rejects_opened_protected_lane(self) -> None:
        self._reject(self._forged(protected_lane="OPEN_PROTECTED_LANE"))

    def test_rejects_false_readiness_claim(self) -> None:
        nonclaims = dict(self.gate["scientific_nonclaims"])
        nonclaims["historical_population_ready"] = True
        self._reject(self._forged(scientific_nonclaims=nonclaims))

    def test_rejects_coordinated_rehash_tampering(self) -> None:
        """Payload hash and manifest are changed together; only rebuild catches it."""
        manifest = json.loads(json.dumps(self.manifest))
        payloads = json.loads(json.dumps(self.gate["payloads"]))
        for entry in manifest["payloads"]:
            if entry["name"] == "national_team_outcome_labels.jsonl":
                entry["sha256"] = "1" * 64
                entry["rows"] = int(entry["rows"]) + 2
        for entry in payloads:
            if entry["name"] == "national_team_outcome_labels.jsonl":
                entry["sha256"] = "1" * 64
                entry["rows"] = int(entry["rows"]) + 2
        manifest["record_hashes"]["outcome_labels"] = "2" * 64
        self._reject(self._forged(payloads=payloads), manifest)

    def test_rejects_substituted_payload_hash(self) -> None:
        manifest = json.loads(json.dumps(self.manifest))
        manifest["payloads"][0]["sha256"] = "0" * 64
        self._reject(self.gate, manifest)

    def test_rejects_unsealed_identity(self) -> None:
        tampered = json.loads(json.dumps(self.gate))
        tampered["population"]["games_total"] = 1
        self._reject(tampered)

    def test_rejects_non_passing_result(self) -> None:
        self.assertEqual(self.gate["result"], PASS_RESULT)
        self._reject(self._forged(result="PASS_NATIONAL_POPULATION_READY"))


if __name__ == "__main__":
    unittest.main()
