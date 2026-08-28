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
from aggie_analytics.data.national_pit_domain_admission_matrix import (  # noqa: E402
    CONTRACT_ID,
    GATE_RELATIVE,
    PASS_RESULT,
    _assert_no_outcome_leakage,
    _TeamState,
    build_pregame_features,
    compute_gate_identity,
    load_contract,
    lookup_prior_poll,
    rebuild_expected,
    season_type_ordinal,
    validate_artifact,
    week_ordinal,
)

CONTRACT = load_contract(ROOT)


def _membership(game_id: str, season: int, week: int, start: str, home: str, away: str):
    return {
        "canonical_game_id": game_id,
        "tier_id": "TIER_2_ACCEPTED_SCOPED_REPLAY",
        "season": season,
        "season_type": "regular",
        "week": week,
        "neutral_site": False,
        "conference_game": True,
        "venue_id": None,
        "home_canonical_team_id": home,
        "away_canonical_team_id": away,
        "start_date_utc_text": start,
        "start_time_tbd": False,
        "completed": True,
        "label_eligible": True,
        "label_ineligible_reason": None,
    }


def _pair(game_id: str, season: int, week: int, home: str, away: str, home_points: int, away_points: int):
    base = {
        "canonical_game_id": game_id,
        "tier_id": "TIER_2_ACCEPTED_SCOPED_REPLAY",
        "season": season,
        "week": week,
        "is_neutral_site": False,
    }
    observations = [
        {**base, "canonical_team_id": home, "opponent_canonical_team_id": away, "is_home": True},
        {**base, "canonical_team_id": away, "opponent_canonical_team_id": home, "is_home": False},
    ]
    labels = [
        {
            "canonical_game_id": game_id,
            "canonical_team_id": home,
            "tier_id": base["tier_id"],
            "season": season,
            "points_for": home_points,
            "points_against": away_points,
            "margin": home_points - away_points,
            "label_win": home_points > away_points,
            "label_tie": home_points == away_points,
        },
        {
            "canonical_game_id": game_id,
            "canonical_team_id": away,
            "tier_id": base["tier_id"],
            "season": season,
            "points_for": away_points,
            "points_against": home_points,
            "margin": away_points - home_points,
            "label_win": away_points > home_points,
            "label_tie": home_points == away_points,
        },
    ]
    return observations, labels


class NationalDomainMatrixUnitTests(unittest.TestCase):
    def test_contract_keeps_the_protected_lane_and_promotion_closed(self) -> None:
        self.assertEqual(CONTRACT["contract_id"], CONTRACT_ID)
        for key in (
            "historical_pit_admission",
            "protected_training_admission",
            "protected_evaluation_admission",
            "champion_or_production_promotion",
            "forecast_publication",
        ):
            self.assertFalse(CONTRACT["authority"][key])

    def test_every_admitted_feature_belongs_to_an_admitted_domain(self) -> None:
        admitted = {
            item["domain_id"] for item in CONTRACT["domains"] if item["decision"] == "ADMITTED"
        }
        for feature in CONTRACT["admitted_feature_registry"]:
            self.assertIn(feature["domain_id"], admitted)

    def test_no_admitted_domain_rests_on_a_capture_timestamp(self) -> None:
        for domain in CONTRACT["domains"]:
            if domain["decision"] == "ADMITTED":
                self.assertNotIn(
                    domain["known_at_basis"],
                    {"POSTGAME_ONLY", "UNKNOWN_RETRIEVAL_TIME_ONLY", "SOURCE_ABSENT"},
                )

    def test_week_ordinal_places_postseason_after_the_regular_season(self) -> None:
        self.assertEqual(season_type_ordinal("regular"), 0)
        self.assertEqual(season_type_ordinal("postseason"), 1)
        self.assertLess(week_ordinal(2015, "regular", 15), week_ordinal(2015, "postseason", 1))

    def test_prior_poll_lookup_never_returns_the_games_own_week(self) -> None:
        snapshots = [
            ((2015, 0, 1), {"ap": {1: 5}}),
            ((2015, 0, 2), {"ap": {1: 4}}),
            ((2015, 0, 3), {"ap": {1: 3}}),
        ]
        self.assertIsNone(lookup_prior_poll(snapshots, (2015, 0, 1)))
        self.assertEqual(lookup_prior_poll(snapshots, (2015, 0, 2)), {"ap": {1: 5}})
        self.assertEqual(lookup_prior_poll(snapshots, (2015, 0, 4)), {"ap": {1: 3}})

    def test_team_state_credits_a_tie_as_half_a_win(self) -> None:
        state = _TeamState()
        state.observe(2019, 21, 21)
        state.observe(2019, 30, 10)
        self.assertEqual(state.games, 2)
        self.assertAlmostEqual(state.win_credit, 1.5)
        self.assertEqual(state.season_to_date(2019), (2, 0.75))
        self.assertIsNone(state.prior_season_win_rate(2019))
        self.assertEqual(state.prior_season_win_rate(2020), 0.75)

    def test_first_game_of_a_team_carries_no_prior_evidence(self) -> None:
        membership = [_membership("G1", 2019, 1, "2019-08-31T00:00:00Z", "T:1", "T:2")]
        observations, labels = _pair("G1", 2019, 1, "T:1", "T:2", 30, 10)
        features, _ = build_pregame_features(
            membership=membership,
            labels=labels,
            observations=observations,
            rankings={},
            venues={},
            team_seasons={},
        )
        self.assertEqual(len(features), 2)
        for row in features:
            self.assertEqual(row["prior_games_played"], 0)
            self.assertTrue(row["prior_win_rate_missing"])
            self.assertIsNone(row["prior_win_rate"])

    def test_prior_evidence_accumulates_only_from_strictly_earlier_dates(self) -> None:
        membership = [
            _membership("G1", 2019, 1, "2019-08-31T00:00:00Z", "T:1", "T:2"),
            _membership("G2", 2019, 2, "2019-09-07T00:00:00Z", "T:1", "T:3"),
        ]
        observations, labels = _pair("G1", 2019, 1, "T:1", "T:2", 30, 10)
        more_observations, more_labels = _pair("G2", 2019, 2, "T:1", "T:3", 14, 21)
        features, _ = build_pregame_features(
            membership=membership,
            labels=labels + more_labels,
            observations=observations + more_observations,
            rankings={},
            venues={},
            team_seasons={},
        )
        second = next(
            row for row in features if row["canonical_game_id"] == "G2" and row["canonical_team_id"] == "T:1"
        )
        self.assertEqual(second["prior_games_played"], 1)
        self.assertEqual(second["prior_win_rate"], 1.0)
        self.assertEqual(second["prior_points_for_mean"], 30.0)
        self.assertEqual(second["season_to_date_games"], 1)

    def test_same_timestamp_games_never_inform_each_other(self) -> None:
        membership = [
            _membership("G1", 2019, 1, "2019-08-31T00:00:00Z", "T:1", "T:2"),
            _membership("G2", 2019, 1, "2019-08-31T00:00:00Z", "T:1", "T:3"),
        ]
        first_obs, first_labels = _pair("G1", 2019, 1, "T:1", "T:2", 30, 10)
        second_obs, second_labels = _pair("G2", 2019, 1, "T:1", "T:3", 14, 21)
        features, _ = build_pregame_features(
            membership=membership,
            labels=first_labels + second_labels,
            observations=first_obs + second_obs,
            rankings={},
            venues={},
            team_seasons={},
        )
        for row in features:
            self.assertEqual(row["prior_games_played"], 0)

    def test_leakage_guard_rejects_a_target_outcome_column(self) -> None:
        membership = [_membership("G1", 2019, 1, "2019-08-31T00:00:00Z", "T:1", "T:2")]
        observations, labels = _pair("G1", 2019, 1, "T:1", "T:2", 30, 10)
        features, _ = build_pregame_features(
            membership=membership,
            labels=labels,
            observations=observations,
            rankings={},
            venues={},
            team_seasons={},
        )
        _assert_no_outcome_leakage(features)
        contaminated = [dict(row, label_win=True) for row in features]
        with self.assertRaises(ValueError):
            _assert_no_outcome_leakage(contaminated)

    def test_unranked_teams_are_left_missing_rather_than_imputed(self) -> None:
        membership = [_membership("G1", 2015, 5, "2015-10-03T00:00:00Z", "SRC-002:TEAM:1", "SRC-002:TEAM:2")]
        observations, labels = _pair("G1", 2015, 5, "SRC-002:TEAM:1", "SRC-002:TEAM:2", 30, 10)
        features, _ = build_pregame_features(
            membership=membership,
            labels=labels,
            observations=observations,
            rankings={2015: [((2015, 0, 4), {"ap": {1: 7}})]},
            venues={},
            team_seasons={},
        )
        ranked = next(row for row in features if row["canonical_team_id"] == "SRC-002:TEAM:1")
        unranked = next(row for row in features if row["canonical_team_id"] == "SRC-002:TEAM:2")
        self.assertEqual(ranked["ap_poll_rank"], 7)
        self.assertFalse(ranked["ap_poll_rank_missing"])
        self.assertIsNone(unranked["ap_poll_rank"])
        self.assertTrue(unranked["ap_poll_rank_missing"])
        self.assertTrue(unranked["rankings_source_available"])


class NationalDomainMatrixMountedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        )
        cls.gate_path = ROOT / GATE_RELATIVE
        if not cls.gate_path.is_file() or not (cls.data_root / "canonical").is_dir():
            raise unittest.SkipTest("national domain matrix gate or data root is not mounted")
        cls.gate = json.loads(cls.gate_path.read_text(encoding="utf-8"))
        cls.expected = rebuild_expected(data_root=cls.data_root, repo_root=ROOT)

    def test_gate_survives_an_independent_rebuild(self) -> None:
        result = validate_artifact(
            data_root=self.data_root,
            repo_root=ROOT,
            require_rebuild=True,
            expected=self.expected,
        )
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["mode"], "INDEPENDENT_REBUILD")

    def test_population_matches_the_declared_spine_scope(self) -> None:
        scope = CONTRACT["population_scope"]
        population = self.gate["population"]
        self.assertEqual(population["population_games"], scope["expected_population_games"])
        self.assertEqual(
            population["population_team_rows"], scope["expected_population_team_observations"]
        )

    def test_admission_is_partial_and_explicit(self) -> None:
        population = self.gate["population"]
        self.assertTrue(population["admitted_domains"])
        self.assertTrue(population["candidate_domains"])
        self.assertTrue(population["source_absent_domains"])
        self.assertLess(len(population["admitted_domains"]), population["declared_domains"])

    def test_postgame_domains_are_never_admitted(self) -> None:
        for row in self.gate["admission_matrix"]:
            if row["known_at_basis"] == "POSTGAME_ONLY":
                self.assertNotEqual(row["decision"], "ADMITTED")
                self.assertFalse(
                    row["protected_and_training_authority"]["development_matrix_input"]
                )

    def test_roster_membership_does_not_establish_availability(self) -> None:
        roster = next(
            row for row in self.gate["admission_matrix"] if row["domain_id"] == "roster_membership"
        )
        self.assertEqual(roster["decision"], "CANDIDATE")
        availability = next(
            row
            for row in self.gate["admission_matrix"]
            if row["domain_id"] == "pregame_availability"
        )
        self.assertEqual(availability["decision"], "SOURCE_ABSENT")

    def test_provider_pregame_elo_is_quarantined(self) -> None:
        elo = next(
            row for row in self.gate["admission_matrix"] if row["domain_id"] == "provider_pregame_elo"
        )
        self.assertEqual(elo["decision"], "QUARANTINED")
        quarantined = {item["field"] for item in self.gate["quarantined_fields"]}
        self.assertIn("homePregameElo", quarantined)
        self.assertIn("awayPregameElo", quarantined)

    def test_no_admitted_feature_is_silently_filled(self) -> None:
        for feature in self.gate["admitted_feature_registry"]:
            indicator = feature["missing_indicator"]
            if indicator is None:
                continue
            report = self.gate["feature_missingness"][feature["feature_id"]]
            self.assertEqual(report["missing_indicator"], indicator)
            self.assertIsNotNone(report["missing_rate"])

    def test_tamu_is_a_small_share_of_the_national_population(self) -> None:
        share = self.gate["tamu_share"]
        self.assertTrue(share["tamu_resolves_in_population"])
        self.assertGreater(share["tamu_population_games"], 0)
        self.assertLess(share["tamu_game_share_of_population"], 0.05)
        self.assertTrue(share["valid_tamu_data_is_retained"])

    def test_the_tamu_official_archive_is_the_one_fully_skewed_domain(self) -> None:
        archive = next(
            row
            for row in self.gate["admission_matrix"]
            if row["domain_id"] == "tamu_official_structured_archive"
        )
        self.assertEqual(archive["tamu_share"]["tamu_game_share_of_domain"], 1.0)
        self.assertTrue(archive["tamu_share"]["tamu_is_overrepresented"])
        self.assertEqual(archive["decision"], "QUARANTINED")
        for row in self.gate["admission_matrix"]:
            if row["domain_id"] == "tamu_official_structured_archive":
                continue
            share = row["tamu_share"]["tamu_game_share_of_domain"]
            if share is not None:
                self.assertLess(share, 0.05)

    def test_admitted_features_cover_real_rows(self) -> None:
        priors = self.gate["feature_missingness"]["prior_win_rate"]
        self.assertGreater(priors["rows"], 90000)
        self.assertLess(priors["missing_rate"], 0.01)
        rankings = self.gate["feature_missingness"]["ap_poll_rank"]
        self.assertGreater(rankings["missing_rows"], 0)
        self.assertLess(rankings["missing_rate"], 1.0)

    def test_protected_and_prospective_authority_stays_closed(self) -> None:
        for row in self.gate["admission_matrix"]:
            authority = row["protected_and_training_authority"]
            self.assertFalse(authority["protected_training_admission"])
            self.assertFalse(authority["protected_evaluation_admission"])
        self.assertFalse(self.gate["authority"]["historical_pit_admission"])


class NationalDomainMatrixMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        )
        cls.gate_path = ROOT / GATE_RELATIVE
        if not cls.gate_path.is_file() or not (cls.data_root / "canonical").is_dir():
            raise unittest.SkipTest("national domain matrix gate or data root is not mounted")
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

    def test_rejects_admitting_a_postgame_domain(self) -> None:
        matrix = json.loads(json.dumps(self.gate["admission_matrix"]))
        for row in matrix:
            if row["domain_id"] == "plays":
                row["decision"] = "ADMITTED"
        self._reject(self._forged(admission_matrix=matrix))

    def test_rejects_an_unadmitted_domain_claiming_matrix_input(self) -> None:
        matrix = json.loads(json.dumps(self.gate["admission_matrix"]))
        for row in matrix:
            if row["domain_id"] == "roster_membership":
                row["protected_and_training_authority"]["development_matrix_input"] = True
        self._reject(self._forged(admission_matrix=matrix))

    def test_rejects_opening_protected_training_on_a_domain(self) -> None:
        matrix = json.loads(json.dumps(self.gate["admission_matrix"]))
        matrix[0]["protected_and_training_authority"]["protected_training_admission"] = True
        self._reject(self._forged(admission_matrix=matrix))

    def test_rejects_disabled_leakage_controls(self) -> None:
        checks = dict(self.gate["leakage_checks"])
        checks["same_timestamp_cohort_excluded"] = False
        self._reject(self._forged(leakage_checks=checks))

    def test_rejects_capture_timestamp_promoted_to_known_at(self) -> None:
        checks = dict(self.gate["leakage_checks"])
        checks["capture_timestamp_used_as_known_at"] = True
        self._reject(self._forged(leakage_checks=checks))

    def test_rejects_imputing_unranked_as_a_rank(self) -> None:
        checks = dict(self.gate["leakage_checks"])
        checks["unranked_imputed_as_a_rank"] = True
        self._reject(self._forged(leakage_checks=checks))

    def test_rejects_understated_missingness(self) -> None:
        missingness = json.loads(json.dumps(self.gate["feature_missingness"]))
        missingness["ap_poll_rank"]["missing_rows"] = 0
        missingness["ap_poll_rank"]["missing_rate"] = 0.0
        self._reject(self._forged(feature_missingness=missingness))

    def test_rejects_a_deflated_tamu_share(self) -> None:
        share = json.loads(json.dumps(self.gate["tamu_share"]))
        share["tamu_population_games"] = 0
        share["tamu_game_share_of_population"] = 0.0
        self._reject(self._forged(tamu_share=share))

    def test_rejects_a_registry_feature_from_an_unadmitted_domain(self) -> None:
        registry = json.loads(json.dumps(self.gate["admitted_feature_registry"]))
        registry.append(
            {
                "feature_id": "smuggled_play_rate",
                "domain_id": "plays",
                "dtype": "FLOAT",
                "missing_indicator": None,
            }
        )
        self._reject(self._forged(admitted_feature_registry=registry))

    def test_rejects_inflated_population_counts(self) -> None:
        population = json.loads(json.dumps(self.gate["population"]))
        population["population_team_rows"] = int(population["population_team_rows"]) + 10
        self._reject(self._forged(population=population))

    def test_rejects_a_false_readiness_claim(self) -> None:
        nonclaims = dict(self.gate["scientific_nonclaims"])
        nonclaims["gap_004_resolved"] = True
        self._reject(self._forged(scientific_nonclaims=nonclaims))

    def test_rejects_an_opened_protected_lane(self) -> None:
        self._reject(self._forged(protected_lane="OPEN_PROTECTED_LANE"))

    def test_rejects_a_substituted_payload_hash(self) -> None:
        manifest = json.loads(json.dumps(self.manifest))
        manifest["payloads"][0]["sha256"] = "0" * 64
        self._reject(self.gate, manifest)

    def test_rejects_coordinated_rehash_tampering(self) -> None:
        manifest = json.loads(json.dumps(self.manifest))
        payloads = json.loads(json.dumps(self.gate["payloads"]))
        for entry in manifest["payloads"] + payloads:
            if entry["name"] == "national_pregame_team_features.jsonl":
                entry["sha256"] = "1" * 64
                entry["rows"] = int(entry["rows"]) + 2
        manifest["record_hashes"]["pregame_features"] = "2" * 64
        self._reject(self._forged(payloads=payloads), manifest)

    def test_rejects_an_unsealed_identity(self) -> None:
        tampered = json.loads(json.dumps(self.gate))
        tampered["population"]["population_games"] = 1
        self._reject(tampered)

    def test_rejects_a_non_passing_result(self) -> None:
        self.assertEqual(self.gate["result"], PASS_RESULT)
        self._reject(self._forged(result="PASS_NATIONAL_ALL_DOMAINS_ADMITTED"))


if __name__ == "__main__":
    unittest.main()
