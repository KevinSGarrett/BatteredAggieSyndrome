from __future__ import annotations
import hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from aggie_analytics.operations.observability import JsonlEventSink, MetricRegistry, sanitize_metadata
from aggie_analytics.operations.environment import UnsafeLocalRuntimePath, collect_runtime_manifest, provision_local_runtime_paths, validate_local_path_contract
from aggie_analytics.operations.backup import create_backup, restore_backup, verify_backup
from aggie_analytics.operations.benchmark import run_benchmark
from aggie_analytics.operations.retention import retention_rule
from aggie_analytics.operations.cleanup import UnsafeRecursiveDelete, safe_remove_tree, validate_recursive_delete_target

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
    def test_local_runtime_paths_are_separate_writable_and_restart_stable(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); repo=base/'repository'; data=base/'external-data'; repo.mkdir()
            p=provision_local_runtime_paths(repo_root=repo,value=data)
            self.assertTrue(p['all_absolute'] and p['all_outside_repository'] and p['all_distinct']); self.assertTrue(all(p['writable'].values())); self.assertEqual(len(set(p['roots'].values())),7)
            env=os.environ.copy(); env['AGGIE_ANALYTICS_DATA_ROOT']=str(data); env['PYTHONPATH']=str(Path(__file__).resolve().parents[1]/'src')
            code="from pathlib import Path; from aggie_analytics.operations.environment import resolve_local_runtime_paths; print('|'.join(sorted(str(x) for x in resolve_local_runtime_paths(repo_root=Path(r'%s')).values())))" % repo
            restarted=subprocess.check_output([sys.executable,'-B','-c',code],env=env,text=True).strip().split('|')
            self.assertEqual(restarted,sorted(str(x) for x in p['roots'].values()))
    def test_local_runtime_path_rejects_repository_internal_bulk_root(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repository'; repo.mkdir()
            with self.assertRaises(UnsafeLocalRuntimePath): provision_local_runtime_paths(repo_root=repo,value=repo/'bulk-data')
    def test_local_path_contract_consumer_fails_closed(self):
        path=Path(__file__).resolve().parents[1]/'artifacts'/'implementation_preflight'/'local_path_contract.json'; original=json.loads(path.read_text(encoding='utf-8'))
        activation=original['prerequisite_identities']['data_root_activation_sha256']; validate_local_path_contract(original,expected_data_root_activation_sha256=activation)
        def rehash(payload):
            canonical=dict(payload); canonical.pop('content_hash',None); payload['content_hash']['value']=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        mutations=[]
        for mutate in [
            lambda p:p.update(schema_version='0.0.0'),
            lambda p:p['roots'][1].update(alias='raw'),
            lambda p:p['validation']['repository_internal_negative_test'].update(rejected=False),
            lambda p:p['security_and_rights'].update(source_rights_approval_claimed=True),
            lambda p:p['consumer_handoff'].update(silent_unlock_allowed=True),
        ]:
            candidate=json.loads(json.dumps(original)); mutate(candidate); rehash(candidate); mutations.append(candidate)
        for candidate in mutations:
            with self.assertRaises(ValueError): validate_local_path_contract(candidate,expected_data_root_activation_sha256=activation)
        with self.assertRaises(ValueError): validate_local_path_contract(original,expected_data_root_activation_sha256='0'*64)
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

    def test_recursive_cleanup_rejects_path_default_and_repository(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td).resolve(); external=base/'external'; worktrees=external/'worktrees'; repo=worktrees/'repository'
            repo.mkdir(parents=True)
            with self.assertRaises(UnsafeRecursiveDelete):
                validate_recursive_delete_target(Path(),allowed_root=external,repo_root=repo)
            with self.assertRaises(UnsafeRecursiveDelete):
                validate_recursive_delete_target(repo,allowed_root=repo,repo_root=repo)
            with self.assertRaises(UnsafeRecursiveDelete):
                validate_recursive_delete_target(worktrees,allowed_root=external,repo_root=repo)
            with self.assertRaises(UnsafeRecursiveDelete):
                validate_recursive_delete_target(external/'runtime',allowed_root=Path(base.anchor),repo_root=repo)
            self.assertTrue(repo.exists())

    def test_recursive_cleanup_rejects_symlink_or_junction_alias(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td).resolve(); repo=base/'repository'; external=base/'external'; real=external/'runtime'/'real'; alias=external/'runtime'/'alias'
            repo.mkdir(); real.mkdir(parents=True)
            try:
                alias.symlink_to(real, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f'directory symlink unavailable: {exc}')
            with self.assertRaises(UnsafeRecursiveDelete):
                validate_recursive_delete_target(alias,allowed_root=external,repo_root=repo)
            self.assertTrue(real.exists())

    def test_recursive_cleanup_only_removes_strict_external_descendant(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td).resolve(); repo=base/'repository'; external=base/'external'; target=external/'runtime'/'task-1'
            repo.mkdir(); target.mkdir(parents=True); (target/'result.tmp').write_text('reconstructible')
            self.assertTrue(safe_remove_tree(target,allowed_root=external,repo_root=repo))
            self.assertFalse(target.exists()); self.assertTrue(external.exists()); self.assertTrue(repo.exists())
            self.assertFalse(safe_remove_tree(target,allowed_root=external,repo_root=repo))
            with self.assertRaises(UnsafeRecursiveDelete):
                safe_remove_tree(external,allowed_root=external,repo_root=repo)

if __name__=='__main__': unittest.main()
