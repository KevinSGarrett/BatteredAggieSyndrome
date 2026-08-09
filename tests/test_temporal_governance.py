import json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from aggie_analytics.temporal.contracts import ForecastCutoff, TemporalObservation, parse_time
from aggie_analytics.temporal.eligibility import evaluate_eligibility, evaluate_fixture, select_latest_eligible

class TemporalGovernanceTests(unittest.TestCase):
    def test_all_synthetic_cases(self):
        cases=json.loads((ROOT/"fixtures/pit/leakage_cases.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["scenario_id"]):
                got=evaluate_fixture(case)
                self.assertEqual(got.eligible, bool(case["expected_eligible"]))
                self.assertEqual(got.reason, case["expected_reason"])

    def test_future_effective_fact_can_be_known_for_future_target(self):
        cutoff=ForecastCutoff("c","FORECAST_SNAPSHOT",parse_time("2026-08-01T12:00:00Z"),parse_time("2026-10-01T00:00:00Z"),"PURE_FOOTBALL","w08-v1.0","d")
        obs=TemporalObservation.from_mapping({"observation_id":"o","source_observation_id":"s","domain":"REGULATORY_ENVIRONMENT","retrieved_at":"2026-06-01T12:01:00Z","first_known_at":"2026-06-01T12:00:00Z","valid_from":"2026-09-01T00:00:00Z","valid_to":"2027-09-01T00:00:00Z","temporal_policy_version":"w08-v1.0"})
        self.assertTrue(evaluate_eligibility(obs,cutoff).eligible)

    def test_later_revision_does_not_rewrite_earlier_snapshot(self):
        cutoff=ForecastCutoff("c","FORECAST_SNAPSHOT",parse_time("2025-10-11T15:30:00Z"),parse_time("2025-10-11T19:00:00Z"),"PURE_FOOTBALL","w08-v1.0","d")
        obs=[TemporalObservation.from_mapping(x) for x in json.loads((ROOT/"fixtures/pit/observations.json").read_text(encoding="utf-8"))[:2]]
        selected=select_latest_eligible(obs,cutoff)
        self.assertEqual(selected.observation_id,"obs_old_availability")

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError): parse_time("2025-01-01T12:00:00")

if __name__=='__main__': unittest.main()
