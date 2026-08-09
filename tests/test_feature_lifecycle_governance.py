from __future__ import annotations
from datetime import datetime,timezone,timedelta
import csv,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from tools.validate_feature_lifecycle import validate
from aggie_analytics.features import HistoryPoint,rolling_mean,ewma,linear_trend,opponent_adjusted_residual,matchup_difference,mutual_information_discrete,ablation_delta,stability_summary,FeatureState,LifecycleEvidence,validate_transition

class FeatureLifecycleTests(unittest.TestCase):
    def test_registry_contract(self): self.assertEqual([],validate(ROOT))
    def test_strict_prior_rolling_excludes_cutoff_game(self):
        t=datetime(2026,1,10,tzinfo=timezone.utc); pts=[HistoryPoint(t-timedelta(days=14),1,'a'),HistoryPoint(t-timedelta(days=7),3,'b'),HistoryPoint(t,100,'target')]
        self.assertEqual(2.0,rolling_mean(pts,t,2));self.assertLess(ewma(pts,t,.5),10);self.assertEqual(2.0,linear_trend(pts,t,2))
    def test_opponent_and_matchup_helpers(self):
        self.assertEqual(4.0,opponent_adjusted_residual(10,6));self.assertEqual(3.0,matchup_difference(8,5))
    def test_screening_helpers_are_descriptive_not_promotion(self):
        self.assertGreater(mutual_information_discrete([0,0,1,1],[0,0,1,1]),0)
        self.assertEqual(0.2,round(ablation_delta(.20,.40),10)); s=stability_summary([.1,-.1,.2]);self.assertEqual(3,s['folds']);self.assertAlmostEqual(2/3,s['positive_fraction'])
    def test_promotion_requires_evidence(self):
        ok,find=validate_transition(FeatureState.EXPERIMENTAL,FeatureState.SUPPORTED,LifecycleEvidence(frozenset()))
        self.assertFalse(ok);self.assertTrue(any(x.startswith('missing_promotion_evidence') for x in find))
    def test_banned_cannot_reopen_from_model_score(self):
        ok,find=validate_transition(FeatureState.BANNED,FeatureState.EXPERIMENTAL,LifecycleEvidence(frozenset({'WALK_FORWARD_INCREMENTAL_VALUE'})))
        self.assertFalse(ok);self.assertIn('banned_requires_governance_safety_correction',find)
        ok,_=validate_transition(FeatureState.BANNED,FeatureState.EXPERIMENTAL,LifecycleEvidence(frozenset(),governance_safety_correction=True));self.assertTrue(ok)
    def test_all_736_candidates_stay_experimental(self):
        with (ROOT/'governance/FEATURE_CANDIDATE_SEEDS.csv').open(newline='',encoding='utf-8') as f:r=list(csv.DictReader(f))
        self.assertEqual(736,len(r));self.assertEqual({'EXPERIMENTAL'},{x['initial_lifecycle_state'] for x in r});self.assertEqual({'false'},{x['production_approved'] for x in r})
if __name__=='__main__':unittest.main()
