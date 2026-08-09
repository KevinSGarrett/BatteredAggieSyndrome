from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from aggie_analytics.operations.observability import JsonlEventSink, MetricRegistry, sanitize_metadata
from aggie_analytics.operations.environment import collect_runtime_manifest
from aggie_analytics.operations.backup import create_backup, restore_backup, verify_backup
from aggie_analytics.operations.benchmark import run_benchmark
from aggie_analytics.operations.retention import retention_rule

class W23OperationsTests(unittest.TestCase):
    def test_secret_safe_structured_log(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'events.jsonl'; sink=JsonlEventSink(p)
            payload=sink.emit(event='STEP_FINISHED',component='weekly',run_id='run-1',metadata={'token':'demo','count':3,'message':'authorization: abcdefghijklmnop'})
            self.assertEqual(payload['metadata']['token'],'[REDACTED]')
            text=p.read_text(); self.assertNotIn('demo',text); self.assertIn('STEP_FINISHED',text)
    def test_metric_registry(self):
        m=MetricRegistry(); m.increment('runs_total'); m.increment('runs_total',2); m.gauge('queue_depth',4)
        self.assertEqual(m.snapshot()['counters']['runs_total'],3.0); self.assertEqual(m.snapshot()['gauges']['queue_depth'],4.0)
    def test_runtime_manifest_allowlists_environment(self):
        p=collect_runtime_manifest(packages=['fastapi','definitely-not-installed-aggie'])
        self.assertEqual(p['schema_version'],'aggie.runtime.environment.v1'); self.assertIn('manifest_sha256',p); self.assertEqual(p['packages']['definitely-not-installed-aggie'],'NOT_INSTALLED')
        self.assertTrue(set(p['safe_environment']).issubset({'AGGIE_ENV','AGGIE_LOG_LEVEL','PYTHONHASHSEED'}))
    def test_backup_restore_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/'src'; src.mkdir(); (src/'a.txt').write_text('alpha'); (src/'nested').mkdir(); (src/'nested'/'b.json').write_text('{"x":1}')
            z=root/'state.zip'; m=create_backup(src,z); self.assertEqual(len(m['entries']),2); verify_backup(z)
            dest=root/'restore'; restore_backup(z,dest); self.assertEqual((dest/'a.txt').read_text(),'alpha'); self.assertEqual((dest/'nested'/'b.json').read_text(),'{"x":1}')
    def test_backup_rejects_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/'src'; src.mkdir(); (src/'a.txt').write_text('alpha'); z=root/'state.zip'; create_backup(src,z)
            import zipfile
            with zipfile.ZipFile(z,'a') as f: f.writestr('payload/unmanifested.txt','tampered')
            with self.assertRaises((ValueError,KeyError)): verify_backup(z)
    def test_benchmark_smoke_is_honest(self):
        p=run_benchmark(profile='smoke'); self.assertFalse(p['authoritative_for_thr_011_012']); self.assertIn('workloads',p); self.assertEqual(p['profile'],'smoke')
    def test_retention_protects_immutable_history(self):
        self.assertFalse(retention_rule('PUBLISHED_FORECAST').automatic_delete_allowed); self.assertFalse(retention_rule('CHAMPION_HISTORY').automatic_delete_allowed); self.assertTrue(retention_rule('TRANSIENT_CACHE').automatic_delete_allowed)
    def test_sanitize_nested(self):
        p=sanitize_metadata({'safe':{'api_key':'abcdefghijklmnop','value':2}}); self.assertEqual(p['safe']['api_key'],'[REDACTED]'); self.assertEqual(p['safe']['value'],2)

if __name__=='__main__': unittest.main()
