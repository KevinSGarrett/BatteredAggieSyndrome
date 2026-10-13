"""Independent counterexamples for reference model boundaries; no skill claims."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import itertools
import math
import unittest

from aggie_analytics.context_intelligence.mechanics import OpponentObservation, strict_prior_opponent_value
from aggie_analytics.modeling.runtime import FeatureVector, ModelArtifact
from aggie_analytics.modeling.baselines import EloProbabilityBaseline
from aggie_analytics.modeling.joint import IndependentPoissonScoreRuntime
from aggie_analytics.modeling.contracts import JointScoreDistribution, ScoreOutcome, SimulationScenario, UncertaintySignal
from aggie_analytics.modeling.coherence import derive_summary
from aggie_analytics.modeling.simulation import mix_joint_distributions
from aggie_analytics.modeling.uncertainty import validate_uncertainty_signals
from aggie_analytics.bas import ExpectedMarginEvidence, build_tamu_bas_label
from aggie_analytics.bas.labels import performance_residual, severity_flags

T = datetime(2024, 9, 1, tzinfo=timezone.utc)
A = ModelArtifact('reference', '1', 'reference', 'win_probability', ('x',), {}, 'synthetic', T-timedelta(days=1))

def row(**values):
    return FeatureVector('synthetic-game', T, 'synthetic-features', values, ('synthetic-source',))

class Wave3ModelBoundaryTests(unittest.TestCase):
    def test_latest_prior_is_independent_of_input_order(self):
        observations = [OpponentObservation(3, T-timedelta(days=3)), OpponentObservation(8, T-timedelta(days=1)), OpponentObservation(99, T)]
        for ordering in itertools.permutations(observations):
            self.assertEqual(strict_prior_opponent_value(ordering, T), 8)
        self.assertIsNone(strict_prior_opponent_value([], T))
        self.assertIsNone(strict_prior_opponent_value([observations[-1]], T))

    def test_latest_prior_refuses_conflict_and_nonfinite_value(self):
        prior = T-timedelta(days=1)
        self.assertEqual(strict_prior_opponent_value([OpponentObservation(8, prior)]*2, T), 8)
        for values in [(8, 9), (float('nan'),), (float('inf'),), (-float('inf'),)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                strict_prior_opponent_value([OpponentObservation(v, prior) for v in values], T)

    def test_prior_times_require_explicit_timezone(self):
        for observations, cutoff in [([], T.replace(tzinfo=None)), ([OpponentObservation(1, T.replace(tzinfo=None))], T)]:
            with self.subTest(cutoff=cutoff), self.assertRaises(ValueError):
                strict_prior_opponent_value(observations, cutoff)

    def test_elo_adjustment_is_bound_to_participant_role(self):
        model = EloProbabilityBaseline(A, home_adjustment=55)
        home = model.predict(row(team_elo=1600, opponent_elo=1500, team_home_indicator=1)).value
        away = model.predict(row(team_elo=1500, opponent_elo=1600, team_home_indicator=-1)).value
        self.assertAlmostEqual(home+away, 1)
        self.assertAlmostEqual(model.predict(row(team_elo=1500, opponent_elo=1500, team_home_indicator=0)).value, .5)
        self.assertAlmostEqual(EloProbabilityBaseline(A).predict(row(team_elo=1500, opponent_elo=1500)).value, .5)
        for role in [None, 2, -2, float('nan'), True]:
            values = {'team_elo':1500, 'opponent_elo':1500}
            if role is not None: values['team_home_indicator'] = role
            with self.subTest(role=role), self.assertRaises(ValueError): model.predict(row(**values))

    def test_elo_finite_inputs_and_extreme_valid_rating(self):
        for kw in [{'scale':float('nan')}, {'scale':float('inf')}, {'home_adjustment':float('nan')}]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                EloProbabilityBaseline(A, **kw).predict(row(team_elo=1500, opponent_elo=1500, team_home_indicator=1))
        for bad in [float('nan'), float('inf'), -float('inf')]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                EloProbabilityBaseline(A).predict(row(team_elo=bad, opponent_elo=1500))
        self.assertEqual(EloProbabilityBaseline(A).predict(row(team_elo=-1e6, opponent_elo=1e6)).value, 0)

    def test_poisson_refuses_material_censoring_and_preserves_means(self):
        features = row(expected_team_points=31, expected_opponent_points=24)
        for maximum in [1, 40, 45]:
            with self.subTest(maximum=maximum), self.assertRaisesRegex(ValueError, 'POISSON_TAIL_TRUNCATION'):
                IndependentPoissonScoreRuntime(A, max_score=maximum).predict_distribution(features)
        summary = derive_summary(IndependentPoissonScoreRuntime(A, max_score=80).predict_distribution(features))
        self.assertAlmostEqual(summary['expected_team_score'], 31, places=7)
        self.assertAlmostEqual(summary['expected_opponent_score'], 24, places=7)
        self.assertAlmostEqual(summary['win_probability']+summary['loss_probability'], 1, places=9)

    def test_poisson_refuses_nonfinite_rates(self):
        for bad in [float('nan'), float('inf'), -float('inf'), 0, -1]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                IndependentPoissonScoreRuntime(A).predict_distribution(row(expected_team_points=bad, expected_opponent_points=24))

    def test_scenario_mixture_requires_same_baseline_and_unique_scenarios(self):
        d = JointScoreDistribution('d','m','1',T,(ScoreOutcome(20,10,1),))
        s = SimulationScenario('s1','baseline',.5,{}, {'e':'synthetic'})
        def mix(second):
            return mix_joint_distributions([(s,d),(second,d)],distribution_id='mix',model_id='m',model_version='1')
        self.assertEqual(mix(replace(s,scenario_id='s2')).outcomes[0].probability, 1)
        for second in [replace(s,scenario_id='s2',baseline_snapshot_id='other-game'), s]:
            with self.subTest(second=second), self.assertRaises(ValueError): mix(second)

    def test_uncertainty_claim_requires_finite_value_and_evidence_reference(self):
        valid = UncertaintySignal('weather','WEATHER','REFERENCE',.4,True,'retained-calibration-record')
        self.assertTrue(validate_uncertainty_signals([valid]))
        self.assertTrue(validate_uncertainty_signals([replace(valid,magnitude=None,calibrated=False,evidence_id=None)]))
        for bad in [replace(valid,evidence_id=None), replace(valid,evidence_id=' '), replace(valid,magnitude=float('nan')), replace(valid,magnitude=float('inf')), replace(valid,magnitude=-1), replace(valid,magnitude=True), replace(valid,calibrated='yes')]:
            with self.subTest(bad=bad), self.assertRaises(ValueError): validate_uncertainty_signals([bad])

    def test_bas_labels_refuse_nonfinite_inputs_and_overflow(self):
        expectation = ExpectedMarginEvidence('e','g','m','1','fold',7,T,T-timedelta(days=1))
        for bad in [float('nan'), float('inf'), -float('inf')]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                build_tamu_bas_label('g', 3, replace(expectation,expected_margin=bad))
            with self.subTest(actual=bad), self.assertRaises(ValueError): build_tamu_bas_label('g', bad, expectation)
        with self.assertRaises(ValueError): performance_residual(1e308,-1e308)
        for shortfall in [0,3,7,14,21,30]:
            label = build_tamu_bas_label('g',7-shortfall,expectation)
            self.assertEqual(label.shortfall, shortfall)
            self.assertEqual(list(severity_flags(7-shortfall,7).values()), [shortfall>=v for v in [3,7,14,21]])

if __name__ == '__main__': unittest.main()
