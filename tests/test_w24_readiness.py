from __future__ import annotations
import csv
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.readiness import run_synthetic_e2e, run_leakage_battery, replay_readiness_report
from tools.validate_w24_readiness import validate


class W24ReadinessTests(unittest.TestCase):
    def test_cross_layer_synthetic_e2e(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_synthetic_e2e(Path(td))
            self.assertEqual('SYNTHETIC_CONTRACT_INTEGRATION_ONLY', report['scope'])
            self.assertFalse(report['empirical_historical_replay_completed'])
            self.assertTrue(all(report['checks'].values()))
            self.assertEqual('PURE_FOOTBALL', report['market_lane'])

    def test_replay_readiness_is_deterministic_and_honest(self):
        with tempfile.TemporaryDirectory() as td:
            report = replay_readiness_report(Path(td))
            self.assertTrue(report['deterministic_contract_replay'])
            self.assertFalse(report['empirical_historical_replay_completed'])
            self.assertFalse(report['protected_historical_metrics_claimed'])

    def test_cross_layer_leakage_battery(self):
        report = run_leakage_battery()
        self.assertTrue(report['all_expected'])
        self.assertEqual('TARGET_GAME_OUTPUT', report['cases']['target_game_output']['reason'])
        self.assertTrue(report['cases']['other_completed_game_output']['eligible'])

    def test_w24_source_refresh_has_current_evidence_and_new_provenance_sources(self):
        root=Path(__file__).resolve().parents[1]
        path=root/'docs/data_research/w24/SOURCE_REFRESH_DELTA.csv'
        with path.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
        ids={r['source_id'] for r in rows}
        self.assertIn('SRC-061',ids); self.assertIn('SRC-062',ids)
        raw=next(r for r in rows if r['source_id']=='SRC-061')
        self.assertEqual('UPSTREAM_PROVENANCE',raw['project_role'])
        self.assertEqual('NO',raw['independent_corroboration'])
        ensemble=next(r for r in rows if r['source_id']=='SRC-062')
        self.assertIn(ensemble['status'],{'OPTIONAL','RESEARCH_ONLY'})

    def test_architecture_challenge_classifies_major_decisions(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/'docs/architecture/W24_FINAL_ARCHITECTURE_CHALLENGE.md').read_text(encoding='utf-8')
        for state in ('KEEP','REVISE','DEFER','REJECT'):
            self.assertIn(f'**{state}**',text)
        self.assertIn('AC-038',text)
        self.assertIn('cfbfastR-cfb-raw',text)

    def test_bootstrap_readiness_check_is_non_mutating(self):
        from tools.bootstrap_readiness import check
        report=check(Path(__file__).resolve().parents[1], profile='core')
        self.assertTrue(report['python_supported'])
        self.assertTrue(report['base_import_ok'])
        self.assertTrue(report['required_files_ok'])


    def test_packaging_is_deterministic_for_same_tree(self):
        from tools.packaging import deterministic_zip_tree
        from tools.repo_integrity import sha256_file
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/'src'; src.mkdir(); (src/'b.txt').write_text('b',encoding='utf-8'); (src/'a.txt').write_text('a',encoding='utf-8')
            z1=root/'one.zip'; z2=root/'two.zip'
            deterministic_zip_tree(src,z1,root_name='fixture'); deterministic_zip_tree(src,z2,root_name='fixture')
            self.assertEqual(sha256_file(z1),sha256_file(z2))

    def test_packaging_rejects_zip_slip_member(self):
        import zipfile
        from tools.packaging import safe_zip_names
        with tempfile.TemporaryDirectory() as td:
            z=Path(td)/'bad.zip'
            with zipfile.ZipFile(z,'w') as f: f.writestr('../escape.txt','x')
            with self.assertRaises(ValueError): safe_zip_names(z)

    def test_w24_validator(self):
        self.assertEqual([], validate(Path(__file__).resolve().parents[1]))

if __name__=='__main__': unittest.main()
