from __future__ import annotations
import tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from aggie_analytics.modeling.runtime import FeatureVector, ModelArtifact
from aggie_analytics.modeling.baselines import ConstantProbabilityBaseline, LinearLogisticBaseline, EloProbabilityBaseline, BoostingAdapterSpec, OptionalBoostingRuntime
from aggie_analytics.modeling.joint import IndependentPoissonScoreRuntime
from aggie_analytics.modeling.coherence import derive_summary, bas_severity_probabilities
from aggie_analytics.modeling.calibration import IdentityCalibrator, LogisticCalibrator
from aggie_analytics.modeling.ensemble import WeightedProbabilityEnsemble
from aggie_analytics.modeling.registry import LocalModelRegistry
from aggie_analytics.modeling.forecast import ForecastSnapshot
from aggie_analytics.modeling.contracts import UncertaintySignal
from aggie_analytics.tamu.state import TamuStateOverlay
from aggie_analytics.tamu.specialization import no_adjustment_signal, SpecializationSignal
from aggie_analytics.tamu.runtime import TamuForecastAdapter
from aggie_analytics.bas.runtime import BasProbabilityForecast
from aggie_analytics.player_intelligence.advanced_state import AdvancedPregameState

UTC=timezone.utc
TRAIN=datetime(2023,12,31,tzinfo=UTC)
CUT=datetime(2024,9,1,tzinfo=UTC)

def artifact(target='win_probability',family='logistic'):
    return ModelArtifact('model-1','v1',family,target,('x',),'{}' if False else {'alpha':1},'train-snapshot',TRAIN)

def row(**values):
    base={'x':1.0,'team_elo':1600.0,'opponent_elo':1500.0,'expected_team_points':31.0,'expected_opponent_points':24.0}; base.update(values)
    return FeatureVector('game-1',CUT,'feat-1',base,('raw-1','pit-1'))

class W20ModelStarterTests(unittest.TestCase):
    def test_artifact_is_deterministic_and_blocks_protected_training_claim(self):
        a=artifact(); self.assertEqual(a.artifact_sha256,a.artifact_sha256)
        bad=ModelArtifact('m','v','f','t',('x',),{},'d',TRAIN,protected_results_used=True)
        with self.assertRaises(ValueError): bad.validate()
    def test_training_cutoff_precedes_forecast(self):
        late=ModelArtifact('m','v','f','t',('x',),{},'d',CUT)
        with self.assertRaises(ValueError): ConstantProbabilityBaseline(late,.5).predict(row())
    def test_constant_logistic_and_elo_baselines_are_functional(self):
        r=row()
        self.assertAlmostEqual(ConstantProbabilityBaseline(artifact(),.6).predict(r).value,.6)
        p=LinearLogisticBaseline(artifact(),{'x':1.0},0).predict(r).value; self.assertGreater(p,.5)
        e=EloProbabilityBaseline(artifact()).predict(r).value; self.assertGreater(e,.5)
    def test_optional_boosting_boundary_does_not_force_dependency(self):
        spec=BoostingAdapterSpec('xgboost','binary:logistic',('x',),{})
        rt=OptionalBoostingRuntime(artifact(family='boosting'),spec)
        self.assertFalse(rt.available)
        with self.assertRaises(RuntimeError): rt.predict(row())
        rt2=OptionalBoostingRuntime(artifact(family='boosting'),spec,lambda xs:.7)
        self.assertAlmostEqual(rt2.predict(row()).value,.7)
    def test_joint_score_distribution_is_normalized_and_coherent(self):
        d=IndependentPoissonScoreRuntime(artifact('joint_score','poisson'),max_score=45).predict_distribution(row())
        s=derive_summary(d)
        self.assertAlmostEqual(sum(x.probability for x in d.outcomes),1.0,places=9)
        self.assertAlmostEqual(s['expected_margin'],s['expected_team_score']-s['expected_opponent_score'])
        self.assertAlmostEqual(s['win_probability']+s['loss_probability'],1.0,places=9)
        b=bas_severity_probabilities(d,7.0); self.assertGreaterEqual(b['ge_3'],b['ge_7']); self.assertGreaterEqual(b['ge_7'],b['ge_14'])
    def test_calibration_and_ensemble_starters(self):
        self.assertEqual(IdentityCalibrator().calibrate(.3),.3)
        self.assertTrue(0<LogisticCalibrator(1.0,0.0).calibrate(.3)<1)
        self.assertAlmostEqual(WeightedProbabilityEnsemble('ens',(0.25,0.75)).combine([.2,.6]),.5)
    def test_registry_is_content_addressed_and_cannot_mark_promoted(self):
        with tempfile.TemporaryDirectory() as td:
            reg=LocalModelRegistry(Path(td)); rec=reg.register(artifact())
            self.assertTrue(Path(rec.artifact_metadata_path).exists())
            rec2=reg.register(artifact()); self.assertEqual(rec.artifact_sha256,rec2.artifact_sha256)
            with self.assertRaises(ValueError): reg.register(artifact(),status='PROMOTED')
    def test_tamu_no_adjustment_reference_is_mandatory(self):
        state=TamuStateOverlay('TAMU',CUT,'nat-state','pit-state',{'qb':'qb-1'},{'availability':.2})
        a=TamuForecastAdapter(state,no_adjustment_signal(),'national-forecast-1'); a.validate(); self.assertEqual(a.candidate_adjustment,0.0)
    def test_tamu_candidate_remains_nonproduction(self):
        state=TamuStateOverlay('TAMU',CUT,'nat-state','pit-state',{}, {})
        sig=SpecializationSignal('cand','margin',2.0,.25,.5)
        a=TamuForecastAdapter(state,sig,'national-ref'); self.assertAlmostEqual(a.candidate_adjustment,.5)
    def test_bas_forecast_requires_nested_probabilities_and_lineage(self):
        b=BasProbabilityForecast('game-1','anchor-1',.4,.3,.2,.1,'hash',('joint-1',)); b.validate()
        with self.assertRaises(ValueError): BasProbabilityForecast('game-1','a',.2,.3,.1,.05,'h',('x',)).validate()
    def test_forecast_snapshot_derives_public_outputs_from_joint_distribution(self):
        art=artifact('joint_score','poisson'); dist=IndependentPoissonScoreRuntime(art,max_score=40).predict_distribution(row())
        snap=ForecastSnapshot('snap','game-1','feat-1',art.artifact_sha256,dist,7.0,(UncertaintySignal('availability','AVAILABILITY','STARTER'),),
                              'tamu-state','TAMU-SP-00',('feat-1','model-1'))
        out=snap.public_summary(); self.assertIn('win_probability',out); self.assertIn('bas_ge_7',out)
    def test_w19_validator_is_forward_compatible(self):
        from tools.validate_w19_foundation import validate
        self.assertEqual([], validate(Path(__file__).resolve().parents[1]))

    def test_advanced_pregame_state_requires_pit_lineage(self):
        s=AdvancedPregameState('g',CUT,'p','a','t','c','m','feat',('pit',),{'x':1}); s.validate()
        with self.assertRaises(ValueError): AdvancedPregameState('g',CUT,'p','a','t','c','m','',(),{'x':1}).validate()

if __name__=='__main__': unittest.main()
