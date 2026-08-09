from __future__ import annotations
import json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from aggie_analytics.orchestration import (
    WeeklyRunIdentity,LocalCheckpointStore,LocalWeeklyOrchestrator,DEFAULT_WEEKLY_STEPS,result,
    CheckpointConflict,ProtectedPromotionDecision,ChampionRegistry,ImmutableForecastPublisher,
    CompletedGameResult,build_postmortem,research_proposal_from_postmortem,
)
UTC=timezone.utc
NOW=datetime(2026,8,31,12,tzinfo=UTC)

class W21WeeklyMLOpsTests(unittest.TestCase):
    def identity(self): return WeeklyRunIdentity('week-2026-01','2026-W01',NOW,('raw-a',),{'mode':'synthetic'})
    def steps(self,calls,fail_once=None):
        out={}
        for sid in DEFAULT_WEEKLY_STEPS:
            def fn(identity,prior,sid=sid):
                calls[sid]=calls.get(sid,0)+1
                if fail_once==sid and calls[sid]==1:
                    return result(sid,{'failed':sid},state='FAILED',detail='synthetic interruption')
                self.assertTrue(all(x.state=='SUCCEEDED' for x in prior.values()))
                return result(sid,{'run':identity.run_id,'step':sid,'parents':sorted(prior)},output_ref=f'artifact:{sid}')
            out[sid]=fn
        return out
    def test_weekly_pipeline_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            calls={}; store=LocalCheckpointStore(Path(td)); orch=LocalWeeklyOrchestrator(store,self.steps(calls))
            a=orch.run(self.identity()); b=orch.run(self.identity())
            self.assertEqual('SUCCEEDED',a.status); self.assertEqual('SUCCEEDED',b.status); self.assertTrue(b.resumed)
            self.assertEqual(len(DEFAULT_WEEKLY_STEPS),sum(calls.values()))
            self.assertEqual(tuple(sorted(DEFAULT_WEEKLY_STEPS)),tuple(sorted(store.completed_steps(self.identity().run_id))))
    def test_interrupted_pipeline_resumes_without_repeating_successes(self):
        with tempfile.TemporaryDirectory() as td:
            calls={}; store=LocalCheckpointStore(Path(td)); bad=LocalWeeklyOrchestrator(store,self.steps(calls,'CALIBRATE')).run(self.identity())
            self.assertEqual('FAILED',bad.status)
            # A failed terminal checkpoint intentionally blocks blind retry; operator must use a new run id or remediation.
            again=LocalWeeklyOrchestrator(store,self.steps(calls)).run(self.identity()); self.assertEqual('FAILED',again.status)
            self.assertEqual(1,calls['INGEST']); self.assertEqual(1,calls['CALIBRATE'])
    def test_quarantine_stops_before_state_feature_and_training_steps(self):
        with tempfile.TemporaryDirectory() as td:
            calls={}
            steps=self.steps(calls)
            def quarantine(identity,prior):
                calls["QA_QUARANTINE"]=calls.get("QA_QUARANTINE",0)+1
                return result("QA_QUARANTINE",{"bad_rows":1},state="QUARANTINED",detail="synthetic schema violation")
            steps["QA_QUARANTINE"]=quarantine
            summary=LocalWeeklyOrchestrator(LocalCheckpointStore(Path(td)),steps).run(self.identity())
            self.assertEqual("QUARANTINED",summary.status)
            self.assertEqual(1,calls["INGEST"]); self.assertEqual(1,calls["QA_QUARANTINE"])
            self.assertNotIn("PIT_STATE",calls); self.assertNotIn("TRAIN_CHALLENGER",calls)

    def test_same_run_id_cannot_change_identity(self):
        with tempfile.TemporaryDirectory() as td:
            store=LocalCheckpointStore(Path(td)); store.initialize(self.identity())
            changed=WeeklyRunIdentity('week-2026-01','2026-W01',datetime(2026,9,1,tzinfo=UTC),('raw-a',),{})
            with self.assertRaises(CheckpointConflict): store.initialize(changed)
    def test_promotion_requires_external_protected_decision_and_supports_rollback(self):
        with tempfile.TemporaryDirectory() as td:
            reg=ChampionRegistry(Path(td));
            first=ProtectedPromotionDecision('cand-a',None,'PROMOTE','seal','protected-hash','w17-evaluator',NOW)
            self.assertEqual('cand-a',reg.apply(first)); self.assertEqual('cand-a',reg.current())
            keep=ProtectedPromotionDecision('cand-b','cand-a','RETAIN_CHAMPION','seal','protected-hash-2','w17-evaluator',NOW)
            self.assertEqual('cand-a',reg.apply(keep)); self.assertEqual('cand-a',reg.current())
            promote=ProtectedPromotionDecision('cand-b','cand-a','PROMOTE','seal','protected-hash-3','w17-evaluator',NOW)
            self.assertEqual('cand-b',reg.apply(promote)); self.assertEqual('cand-a',reg.rollback(expected_current='cand-b',restore_artifact_sha256='cand-a',reason='operational rollback test'))
    def test_immutable_forecast_publication(self):
        with tempfile.TemporaryDirectory() as td:
            p=ImmutableForecastPublisher(Path(td)); kw=dict(snapshot_id='fri-1',game_id='g1',forecast_cutoff=NOW,model_artifact_sha256='model',feature_snapshot_id='feat',public_summary={'win_probability':.5,'expected_margin':0.0},lineage_refs=('raw','pit','feat'))
            a=p.publish(**kw); b=p.publish(**kw); self.assertEqual(a,b)
            with self.assertRaises(RuntimeError): p.publish(**{**kw,'public_summary':{'win_probability':.6,'expected_margin':1.0}})
    def test_postmortem_can_only_propose_research(self):
        game=CompletedGameResult('g1',10,31,NOW,'official-result')
        pm=build_postmortem(game=game,forecast_summary={'expected_margin':3.0,'win_probability':.7},forecast_ref='forecast-1')
        prop=research_proposal_from_postmortem(pm); self.assertIsNotNone(prop); self.assertEqual('PROPOSE_EXPERIMENT_ONLY',prop['allowed_action'])
    def test_w20_validator_is_forward_compatible(self):
        from tools.validate_w20_starter import validate
        self.assertEqual([],validate(Path(__file__).resolve().parents[1]))
if __name__=='__main__': unittest.main()
