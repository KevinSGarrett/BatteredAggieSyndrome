from __future__ import annotations
import csv,sys,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"src"))
from tools.validate_player_intelligence import validate
from aggie_analytics.player_intelligence import (
    AvailabilityScenario,expected_lineup_value,expected_replacement_gap,
    AvailabilityEvidence,EvidenceTier,eligible_evidence,noncoverage_state,
    competition_strength_delta,fixed_conference_penalty,
    ProspectPrior,eligible_for_transfer_production_model
)

class PlayerIntelligenceGovernanceTests(unittest.TestCase):
    def test_registry_contract(self):
        self.assertEqual([],validate(ROOT))

    def test_scenario_lineup_and_gap_are_abstract(self):
        scenarios=(
            AvailabilityScenario("full",.6,10,1.0,1.0,6,0.0,.5),
            AvailabilityScenario("out",.4,10,0.0,0.0,6,1.0,1.0),
        )
        self.assertAlmostEqual(8.4,expected_lineup_value(scenarios))
        self.assertAlmostEqual(1.6,expected_replacement_gap(10,1.0,scenarios))

    def test_scenario_probabilities_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            expected_lineup_value((AvailabilityScenario("x",.7,10,1,1,5,0),))

    def test_noncoverage_never_becomes_healthy(self):
        self.assertEqual("UNKNOWN",noncoverage_state(policy_covered=False,usable_evidence_present=False))
        self.assertEqual("UNKNOWN",noncoverage_state(policy_covered=True,usable_evidence_present=False))

    def test_evidence_cutoff(self):
        t=datetime(2026,8,8,tzinfo=timezone.utc)
        ev=AvailabilityEvidence("e","p",t,EvidenceTier.OFFICIAL_CONFERENCE_REPORT,"QUESTIONABLE",True,"r1")
        self.assertFalse(eligible_evidence(ev,t-timedelta(seconds=1)))
        self.assertTrue(eligible_evidence(ev,t))

    def test_fixed_transfer_penalty_forbidden(self):
        self.assertEqual(5,competition_strength_delta(70,75))
        with self.assertRaises(RuntimeError):
            fixed_conference_penalty("SEC","Sun Belt")

    def test_zero_snap_prospect_does_not_use_transfer_model(self):
        p=ProspectPrior("p","QB",datetime(2026,8,8,tzinfo=timezone.utc),50,15,("recruit",),0)
        self.assertEqual(0,p.college_snaps_known)
        self.assertFalse(eligible_for_transfer_production_model(0))
        self.assertTrue(eligible_for_transfer_production_model(1))

    def test_candidates_still_unpromoted(self):
        with (ROOT/"governance/FEATURE_CANDIDATE_SEEDS.csv").open(newline="",encoding="utf-8") as f:
            r=list(csv.DictReader(f))
        self.assertEqual(736,len(r))
        self.assertTrue(all(x["initial_lifecycle_state"]=="EXPERIMENTAL" and x["production_approved"]=="false" for x in r))

if __name__=="__main__": unittest.main()
