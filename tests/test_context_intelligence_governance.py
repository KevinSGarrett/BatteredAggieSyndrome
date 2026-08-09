from __future__ import annotations
import csv,sys,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/"src"))
from tools.validate_context_intelligence import validate
from aggie_analytics.context_intelligence import (
    CoachRoleEpisode,eligible_role,coach_residual,manual_coach_bonus,
    WeatherForecastEvidence,forecast_eligible,haversine_km,home_residual,
    hidden_yards,expected_possessions_baseline,crew_feature_eligible,strict_prior_opponent_value,
)
from aggie_analytics.context_intelligence.mechanics import OpponentObservation,referee_bias_bonus

class ContextIntelligenceTests(unittest.TestCase):
    def test_registry_contract(self):
        self.assertEqual([],validate(ROOT))
    def test_role_bitemporal_eligibility(self):
        t=datetime(2026,8,8,tzinfo=timezone.utc)
        ep=CoachRoleEpisode("c","OC",t,t+timedelta(days=365),t-timedelta(days=1),"offense",True)
        self.assertTrue(eligible_role(ep,cutoff=t,target_time=t+timedelta(days=1)))
        self.assertFalse(eligible_role(ep,cutoff=t-timedelta(days=2),target_time=t+timedelta(days=1)))
    def test_coach_residual_is_abstract_and_manual_bonus_forbidden(self):
        self.assertEqual(3.0,coach_residual(10.0,7.0))
        with self.assertRaises(RuntimeError): manual_coach_bonus(3)
    def test_weather_forecast_requires_known_run(self):
        t=datetime(2026,8,8,tzinfo=timezone.utc)
        e=WeatherForecastEvidence("w",t-timedelta(hours=2),t-timedelta(hours=1),t+timedelta(days=1),t-timedelta(minutes=10))
        self.assertTrue(forecast_eligible(e,t))
        self.assertFalse(forecast_eligible(e,t-timedelta(hours=1,minutes=30)))
    def test_haversine_and_home_residual_are_reference_only(self):
        self.assertGreater(haversine_km(30.61,-96.34,29.76,-95.37),100)
        self.assertEqual(4.0,home_residual(7,3))
    def test_mechanics_reference_functions(self):
        self.assertEqual(30,hidden_yards(10,5,15))
        self.assertEqual(11,expected_possessions_baseline([10,12],[11,11]))
    def test_officiating_fails_closed_and_bias_bonus_forbidden(self):
        t=datetime(2026,8,8,tzinfo=timezone.utc)
        self.assertFalse(crew_feature_eligible(assignment_first_known_at=None,cutoff=t))
        self.assertTrue(crew_feature_eligible(assignment_first_known_at=t-timedelta(hours=1),cutoff=t))
        with self.assertRaises(RuntimeError): referee_bias_bonus("x","y")
    def test_opponent_value_is_strict_prior(self):
        t=datetime(2026,8,8,tzinfo=timezone.utc)
        obs=[OpponentObservation(1,t-timedelta(days=2)),OpponentObservation(2,t),OpponentObservation(3,t+timedelta(days=1))]
        self.assertEqual(1,strict_prior_opponent_value(obs,t))
    def test_w10_candidates_remain_unpromoted(self):
        with (ROOT/"governance/FEATURE_CANDIDATE_SEEDS.csv").open(newline="",encoding="utf-8") as f:
            r=list(csv.DictReader(f))
        self.assertEqual(736,len(r))
        self.assertTrue(all(x["initial_lifecycle_state"]=="EXPERIMENTAL" and x["production_approved"]=="false" for x in r))

if __name__=="__main__": unittest.main()
