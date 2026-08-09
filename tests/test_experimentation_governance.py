import sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aggie_analytics.experimentation.contracts import ExperimentSpec, ExperimentResultPacket
from aggie_analytics.experimentation.queue import validate_transition, make_event
from aggie_analytics.experimentation.governance import verify_judging_rule_seal, hpo_objective_allowed, advanced_challenger_admission

class ExperimentationGovernanceTests(unittest.TestCase):
    def spec(self, **kw):
        base=dict(hypothesis_id="HYP-056",task_id="TASK-134",candidate_family="boosted",code_ref="sha:abc",data_snapshot_id="DS-1",feature_registry_version="w10",model_config={"depth":3},split_protocol_id="SPLIT-W17-001",metric_registry_hash="m",threshold_method_hash="t",environment_fingerprint="py",random_seeds=[7],resource_budget_id="RB-LOCAL")
        base.update(kw); return ExperimentSpec(**base)
    def test_experiment_id_is_deterministic_and_config_sensitive(self):
        a=self.spec(); b=self.spec(); c=self.spec(model_config={"depth":4})
        self.assertEqual(a.experiment_id,b.experiment_id); self.assertNotEqual(a.experiment_id,c.experiment_id)
    def test_result_cannot_self_promote_or_hold_protected_metrics(self):
        ok=ExperimentResultPacket("EXP-a","A1","h",{"brier":0.2},"py","VERIFIED","ADOPT_AS_CHALLENGER","ok"); ok.validate()
        with self.assertRaises(ValueError): ExperimentResultPacket("EXP-a","A1","h",{},"py","VERIFIED","PROMOTE","bad").validate()
        with self.assertRaises(ValueError): ExperimentResultPacket("EXP-a","A1","h",{},"py","VERIFIED","REJECT","bad",protected_metrics={"x":1}).validate()
    def test_queue_research_agent_cannot_approve_or_promote(self):
        with self.assertRaises(PermissionError): validate_transition("PROPOSED","APPROVED","research_agent")
        with self.assertRaises(ValueError): validate_transition("ADOPTED_AS_CHALLENGER","PROMOTE","research_governor")
    def test_event_hash_changes_with_payload(self):
        a=make_event(experiment_id="EXP-x",state="PROPOSED",actor_role="research_agent",reason="a",event_index=0)
        b=make_event(experiment_id="EXP-x",state="PROPOSED",actor_role="research_agent",reason="b",event_index=0)
        self.assertNotEqual(a["event_hash"],b["event_hash"])
    def test_hpo_is_development_only(self):
        self.assertTrue(hpo_objective_allowed("SPLIT-DEV-HIST")); self.assertTrue(hpo_objective_allowed("SPLIT-DEV-SEL"))
        self.assertFalse(hpo_objective_allowed("SPLIT-PROTECTED")); self.assertFalse(hpo_objective_allowed("SPLIT-FORWARD"))
    def test_judging_rule_seal_verifies(self):
        self.assertEqual(verify_judging_rule_seal(ROOT),[])
    def test_advanced_transformer_blocked_without_baseline_evidence(self):
        self.assertEqual(advanced_challenger_admission(candidate_class="SEQUENCE_TRANSFORMER",baseline_empirical_evidence=False,protocol_sealed=True,resource_budget_declared=True),"BLOCKED_BASELINE_EMPIRICAL_EVIDENCE_MISSING")
    def test_baseline_extension_can_be_research_only(self):
        self.assertEqual(advanced_challenger_admission(candidate_class="SIMPLE_BASELINE_EXTENSION",baseline_empirical_evidence=False,protocol_sealed=True,resource_budget_declared=True),"ADMITTED_RESEARCH_ONLY")

if __name__=="__main__": unittest.main()
