"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-08: the kernel reconstruction re-states the producer's declared prior
rule and field meanings, and the label audit refuses forged admissions. Each
case pins one declared rule on synthetic games; none is a claim about a real
contest.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load(name: str):
    path = ROOT / "tools" / "cycle37" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


kr = _load("r37_08_kernel_reconciliation")
audit = _load("r37_08_label_consumer_audit")

from aggie_analytics.scientific_reference import cycle33_pit  # noqa: E402

T0 = datetime(2018, 9, 15, 19, 0, tzinfo=timezone.utc)


def game(gid: str, start: datetime, home: str = "A", away: str = "B", hp: int = 21, ap: int = 14,
         season: int = 2018, precision: str = kr.UNKNOWN) -> "kr.Game":
    return kr.Game(gid, season, start, precision, home, away, hp, ap, False, "TEST")


def team_features(games: list, target: "kr.Game", team: str = "A") -> dict:
    return kr.features(kr.team_histories(games)[team], target)[0]


class PriorRuleTests(unittest.TestCase):
    def test_an_unknown_precision_target_needs_36_hours(self) -> None:
        target = game("T", T0)
        close = game("P1", T0 - timedelta(hours=30), away="C")
        clear = game("P2", T0 - timedelta(hours=40), away="D")
        self.assertEqual(team_features([target, close], target)["pit_prior_games_played"], 0)
        self.assertEqual(team_features([target, clear], target)["pit_prior_games_played"], 1)

    def test_an_instant_target_needs_12_hours(self) -> None:
        target = game("T", T0, precision=kr.INSTANT, season=2026)
        prior = game("P", T0 - timedelta(hours=13), away="C", precision=kr.INSTANT, season=2026)
        late = game("Q", T0 - timedelta(hours=11), away="D", precision=kr.INSTANT, season=2026)
        self.assertEqual(team_features([target, prior, late], target)["pit_prior_games_played"], 1)

    def test_the_target_never_counts_itself(self) -> None:
        target = game("T", T0)
        features, admitted, _ = kr.features(kr.team_histories([target])["A"], target)
        self.assertEqual(features["pit_prior_games_played"], 0)
        self.assertEqual(admitted, [])

    def test_prior_season_win_rate_is_the_previous_season(self) -> None:
        target = game("T", T0)
        last_year = [game(f"L{i}", T0 - timedelta(days=300 + i), away=f"X{i}", hp=0, ap=7, season=2017)
                     for i in range(3)]
        this_year = game("C", T0 - timedelta(days=7), away="Y", hp=30, ap=0)
        features = team_features([target, *last_year, this_year], target)
        self.assertEqual(features["pit_prior_season_win_rate"], 0.0)
        self.assertEqual(features["pit_season_to_date_games"], 1)
        self.assertEqual(features["pit_season_to_date_win_rate"], 1.0)

    def test_a_tie_is_a_game_without_a_win(self) -> None:
        target = game("T", T0)
        tie = game("P", T0 - timedelta(days=7), away="C", hp=10, ap=10)
        win = game("Q", T0 - timedelta(days=14), away="D", hp=20, ap=10)
        features = team_features([target, tie, win], target)
        self.assertEqual(features["pit_prior_games_played"], 2)
        self.assertEqual(features["pit_prior_win_rate"], 0.5)


class PopulationTests(unittest.TestCase):
    def raw(self, **overrides) -> dict:
        base = {"canonical_game_id": "SRC-002:GAME:1", "season": 2018, "completed": True,
                "home_classification": "fbs", "away_classification": "fbs", "home_points": 21,
                "away_points": 14, "start_date_utc_text": "2018-09-15T19:00:00.000Z",
                "home_team_source_id": 1, "away_team_source_id": 2}
        return {**base, **overrides}

    def test_the_declared_filter(self) -> None:
        self.assertIsNotNone(kr.historical_game(self.raw()))
        for overrides in ({"away_classification": "fcs"}, {"completed": False}, {"season": 2024},
                          {"season": 2005}, {"home_points": None}, {"start_date_utc_text": "2018-09-15"}):
            with self.subTest(overrides=overrides):
                self.assertIsNone(kr.historical_game(self.raw(**overrides)))

    def test_every_exclusion_has_a_declared_reason(self) -> None:
        self.assertIsNone(kr.exclusion_reason(self.raw()))
        self.assertEqual(kr.exclusion_reason(self.raw(away_classification="fcs")), "CROSS_DIVISION_FBS_VS_NON_FBS")
        self.assertEqual(kr.exclusion_reason(self.raw(season=2025)), "SEASON_OUTSIDE_2006_2023")
        self.assertEqual(kr.exclusion_reason(self.raw(completed=False)), "NOT_COMPLETED")
        self.assertEqual(kr.exclusion_reason(self.raw(away_points=None)), "SCORE_MISSING")

    def test_partitions_follow_the_declared_folds(self) -> None:
        self.assertEqual(kr.partition(2013), "TRAIN_2013_2019")
        self.assertEqual(kr.partition(2023), "EVAL_2020_2023")
        self.assertEqual(kr.partition(2012), "PRIOR_WINDOW_2006_2012_NO_FOLD")
        self.assertEqual(kr.partition(2026), "FREEZE_2026_NO_FOLD")

    def test_a_naive_instant_is_not_accepted(self) -> None:
        self.assertIsNone(kr.parse_utc("2018-09-15T19:00:00"))
        self.assertEqual(kr.parse_utc("2018-09-15T19:00:00.000Z"), T0)


class PitEvidenceTests(unittest.TestCase):
    def priors(self, *ids: str) -> list:
        return [kr.Prior(T0, gid, 2018, 1, 0, T0) for gid in ids]

    def test_each_evidence_state(self) -> None:
        cutoff = T0 + timedelta(days=30)
        before, after = T0 + timedelta(days=1), T0 + timedelta(days=60)
        self.assertEqual(kr.pit_evidence([], cutoff, {}), kr.VACUOUS)
        self.assertEqual(kr.pit_evidence(self.priors("A", "B"), cutoff, {"A": before}), kr.SOME_PRIOR_UNBOUND)
        self.assertEqual(kr.pit_evidence(self.priors("A", "B"), cutoff, {"A": before, "B": after}),
                         kr.SOME_PRIOR_KNOWN_AFTER_CUTOFF)
        self.assertEqual(kr.pit_evidence(self.priors("A"), cutoff, {"A": cutoff}), kr.SOME_PRIOR_KNOWN_AFTER_CUTOFF)
        self.assertEqual(kr.pit_evidence(self.priors("A"), cutoff, {"A": before}), kr.ALL_PRIORS_KNOWN_BEFORE_CUTOFF)


class LabelAuditTests(unittest.TestCase):
    def test_an_undeclared_or_stale_consumer_is_reported(self) -> None:
        declared = next(iter(audit.DECLARED))
        result = audit.reconcile_declarations({declared: ["1: x"], "tools/new_consumer.py": ["2: y"]})
        self.assertFalse(result["complete"])
        self.assertEqual(result["undeclared_consumers"], ["tools/new_consumer.py"])
        self.assertEqual(result["declared_but_no_longer_naming_a_token"], sorted(set(audit.DECLARED) - {declared}))

    def test_every_declared_role_is_known(self) -> None:
        roles = {audit.PRODUCER, audit.PRIOR_PRODUCER, audit.GATE, audit.REFERENCE_OWN_CLASS, audit.COUNT,
                 audit.FIT_BY_SEASON, audit.OTHER_ARTIFACT, audit.VALIDATOR}
        self.assertTrue(all(role in roles for role, _ in audit.DECLARED.values()))

    def test_each_gate_refuses_the_forged_controls_and_admits_the_positive_one(self) -> None:
        historical = {"canonical_game_id": "SRC-002:GAME:9", "season": 2013, "site_class": "NON_NEUTRAL",
                      "ordinary_home_exposure": 1.0, "authority_class": "RETROSPECTIVE_BOUNDED_CANDIDATE",
                      "home_features": {key: 1 for key in kr.FIELDS},
                      "away_features": {key: 1 for key in kr.FIELDS}}
        results = audit.probe([], historical)
        for name, result in results.items():
            with self.subTest(gate=name):
                self.assertTrue(result["passes"], result["forged_controls"])
                self.assertEqual(result["synthetic_positive_control"], "ADMITTED")


class ReferenceTemporalTests(unittest.TestCase):
    def row(self, **overrides) -> dict:
        base = {"canonical_game_id": "G", "season": 2013, "source_id": "S", "receipt_sha256": "a" * 64,
                "classification": "OBSERVED_PUBLICATION", "evidence_class": "SOURCE_PUBLICATION",
                "effective_utc": "2013-08-30T12:00:00Z", "known_at_utc": "2013-08-30T13:00:00Z",
                "source_publication_utc": "2013-08-30T12:30:00Z", "target_cutoff_utc": "2013-08-31T16:00:00Z"}
        return {**base, **overrides}

    def test_in_time_authority_is_admitted(self) -> None:
        self.assertTrue(cycle33_pit.independent_row_class(self.row())["independently_proven"])

    def test_temporal_forgeries_are_refused(self) -> None:
        for overrides, reason in (
            ({"source_publication_utc": "2099-01-01T00:00:00Z", "known_at_utc": "2099-01-01T00:00:00Z"},
             "PUBLICATION_IN_THE_FUTURE"),
            ({"source_publication_utc": "2014-01-01T00:00:00Z", "known_at_utc": "2014-01-01T00:00:00Z"},
             "PUBLICATION_NOT_BEFORE_CUTOFF"),
            ({"target_cutoff_utc": None}, "NO_TARGET_CUTOFF"),
            ({"known_at_utc": "2013-08-30T12:00:00Z"}, "KNOWN_AT_PRECEDES_PUBLICATION"),
            ({"source_publication_utc": "2013-08-30T12:30:00"}, "PUBLICATION_NOT_AN_AWARE_INSTANT"),
            ({"effective_utc": "2013-09-02T00:00:00Z"}, "EFFECTIVE_AFTER_CUTOFF"),
        ):
            with self.subTest(reason=reason):
                verdict = cycle33_pit.independent_row_class(self.row(**overrides))
                self.assertFalse(verdict["independently_proven"])
                self.assertIn(reason, verdict["failed_predicates"])


if __name__ == "__main__":
    unittest.main()
