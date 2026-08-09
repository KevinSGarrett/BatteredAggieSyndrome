from __future__ import annotations
import csv, json, unittest
from pathlib import Path
from tools.validate_acceptance import validate

ROOT=Path(__file__).resolve().parents[1]

class AcceptanceGovernanceTests(unittest.TestCase):
    def test_acceptance_registry_valid(self):
        self.assertEqual([], validate(ROOT))

    def test_all_requirements_mapped(self):
        def ids(path,col):
            with path.open(newline='',encoding='utf-8') as f: return [r[col] for r in csv.DictReader(f)]
        self.assertEqual(set(ids(ROOT/'governance/REQUIREMENTS_INDEX.csv','requirement_id')), set(ids(ROOT/'governance/REQUIREMENT_ACCEPTANCE_MATRIX.csv','requirement_id')))

    def test_no_tbd_threshold_has_invented_value(self):
        with (ROOT/'governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv').open(newline='',encoding='utf-8') as f:
            rows=list(csv.DictReader(f))
        self.assertTrue(rows)
        for r in rows:
            if r['status'].startswith('TBD_'):
                self.assertEqual('', r['value'])

    def test_level_c_hypotheses_not_w04_verified(self):
        with (ROOT/'governance/REQUIREMENTS_INDEX.csv').open(newline='',encoding='utf-8') as f: req={r['requirement_id']:r for r in csv.DictReader(f)}
        with (ROOT/'governance/REQUIREMENT_ACCEPTANCE_MATRIX.csv').open(newline='',encoding='utf-8') as f: mat={r['requirement_id']:r for r in csv.DictReader(f)}
        for rid,r in req.items():
            if r['constraint_class']=='C':
                self.assertEqual('EXPERIMENT_REQUIRED_NONBLOCKING_UNTIL_PROMOTION',mat[rid]['acceptance_state'])

    def test_protected_controls_are_blocking(self):
        reg=json.loads((ROOT/'configs/acceptance_registry.json').read_text(encoding='utf-8'))
        controls={c['control_id']:c for c in reg['controls']}
        for cid in reg['protected_control_ids']:
            self.assertTrue(controls[cid]['release_blocking'])

    def test_w04_hydration_manifest_contains_acceptance_recovery_artifacts(self):
        manifest=json.loads((ROOT/'configs/hydration_manifest.json').read_text(encoding='utf-8'))
        sources={x['source'] for x in manifest['files']}
        required={
            'configs/acceptance_registry.json',
            'governance/ACCEPTANCE_CONTROL_CATALOG.csv',
            'governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv',
            'governance/REQUIREMENT_ACCEPTANCE_MATRIX.csv',
            'governance/W04_ADAPTIVE_REVIEW.md',
            'governance/W04_VALIDATION_REPORT.md',
        }
        self.assertTrue(required.issubset(sources))

if __name__=='__main__': unittest.main()
