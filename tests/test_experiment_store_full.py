import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import tempfile
import unittest
from pathlib import Path
from aggie_analytics.experimentation.store import ExperimentStore
from aggie_analytics.experimentation.queue import make_event

class ExperimentStoreFullTests(unittest.TestCase):
    def make_store(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        store=ExperimentStore(Path(td.name)/"experiments.sqlite")
        store.initialize()
        return store

    def test_add_and_get_stable_experiment(self):
        s=self.make_store()
        spec={"target":"margin","split":"SPLIT-DEV-SEL","config":{"depth":4}}
        eid=s.add_experiment(spec)
        self.assertTrue(eid.startswith("EXP-"))
        self.assertEqual(s.add_experiment(spec),eid)
        got=s.get_experiment(eid)
        self.assertEqual(got.experiment_id,eid)
        self.assertEqual(got.payload["target"],"margin")
        self.assertEqual(s.integrity_check(),[])

    def test_queue_chain_enforced(self):
        s=self.make_store()
        eid=s.add_experiment({"target":"win","split":"SPLIT-DEV-HIST"})
        e0=make_event(experiment_id=eid,state="PROPOSED",actor_role="research_agent",reason="x",event_index=0)
        s.append_queue_event(e0)
        e1=make_event(experiment_id=eid,state="APPROVED",actor_role="research_governor",reason="ok",event_index=1,previous_event_hash=e0["event_hash"])
        s.append_queue_event(e1)
        self.assertEqual([x["state"] for x in s.queue_history(eid)],["PROPOSED","APPROVED"])
        bad=make_event(experiment_id=eid,state="QUEUED",actor_role="scheduler",reason="bad",event_index=3,previous_event_hash=e1["event_hash"])
        with self.assertRaises(ValueError): s.append_queue_event(bad)

    def test_results_append_by_attempt(self):
        s=self.make_store(); eid=s.add_experiment({"target":"margin","split":"SPLIT-DEV-SEL"})
        rid=s.add_result({"experiment_id":eid,"attempt":1,"metrics":{"mae":7.1}})
        self.assertTrue(rid.startswith("RES-"))
        with self.assertRaises(Exception):
            s.add_result({"experiment_id":eid,"attempt":1,"metrics":{"mae":7.0}})
