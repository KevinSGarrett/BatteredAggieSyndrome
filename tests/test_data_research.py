from pathlib import Path
import json
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.aggie_analytics.data.contracts import SourceRightsAction, SourceRightsDenied, SourceRightsRegistry
from tools.validate_data_research import validate
class TestW06DataResearch(unittest.TestCase):
    def test_w06_data_research_contract(self):
        self.assertEqual(validate(ROOT),[])
    def test_required_w06_artifacts_exist(self):
        base=ROOT/'docs/data_research/w06'
        for name in ['DATA_UNIVERSE_MASTER.csv','DATA_DOMAIN_COVERAGE_MATRIX.csv','POINT_IN_TIME_FEASIBILITY_MATRIX.csv','SOURCE_ACCESS_LICENSE_MATRIX.csv','DATA_RESEARCH_FINDINGS.md','WAVE_06_ARCHITECTURE_IMPACT.md']:
            self.assertTrue((base/name).is_file(),name)

class TestSourceRightsRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=ROOT/'configs/source_rights_registry.json'
        cls.registry=SourceRightsRegistry.load(cls.path)

    def test_registry_is_complete_machine_readable_and_secret_free(self):
        self.assertEqual(len(self.registry.decisions),63)
        raw=self.path.read_text(encoding='utf-8')
        for marker in ('SCRAPFLY_API_TOKEN=','SCRAPERAPI_API_TOKEN=','GITHUB_TOKEN=','CFBD_API_KEY='):
            self.assertNotIn(marker,raw)

    def test_private_acquisition_and_training_are_not_rights_gated(self):
        for source_id in self.registry.decisions:
            self.registry.require(source_id,SourceRightsAction.ACQUIRE_PRODUCTION)
            self.registry.require(source_id,SourceRightsAction.ACQUIRE_EXPERIMENTAL)
            self.registry.require(source_id,SourceRightsAction.TRAIN_LOCAL)

        unregistered=self.registry.require(
            'SRC-PUBLIC-UNREGISTERED',
            SourceRightsAction.ACQUIRE_PRODUCTION,
            publicly_accessible=True,
        )
        self.assertEqual(unregistered.lane_disposition,'PRIVATE_RESEARCH_ALLOWED')
        self.assertTrue(unregistered.local_model_training_allowed)
        with self.assertRaisesRegex(SourceRightsDenied,'SOURCE_USE_PUBLIC_ACCESS_UNCONFIRMED'):
            self.registry.require('SRC-NONPUBLIC-UNKNOWN',SourceRightsAction.ACQUIRE_PRODUCTION)

    def test_access_and_redistribution_are_independent(self):
        cfbd=self.registry.require('SRC-002',SourceRightsAction.ACQUIRE_PRODUCTION)
        self.assertTrue(cfbd.production_acquisition_allowed)
        self.assertFalse(cfbd.raw_export_allowed)
        with self.assertRaisesRegex(SourceRightsDenied,'SOURCE_USE_DENIED:SRC-002:EXPORT_RAW'):
            self.registry.require('SRC-002',SourceRightsAction.EXPORT_RAW)
        open_meteo_payload=next(
            row for row in json.loads(self.path.read_text(encoding='utf-8'))['sources']
            if row['source_id']=='SRC-003'
        )
        self.assertEqual(open_meteo_payload['provider_raw_redistribution_permission'],'PERMITTED_WITH_ATTRIBUTION')
        self.assertFalse(open_meteo_payload['raw_export_allowed'])

    def test_registry_rejects_unsafe_mutations(self):
        payload=json.loads(self.path.read_text(encoding='utf-8'))
        payload['sources'][0]['raw_export_allowed']=True
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unsafe.json'
            path.write_text(json.dumps(payload),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'SOURCE_RIGHTS_PROJECT_RAW_EXPORT_PROHIBITED'):
                SourceRightsRegistry.load(path,verify_inputs=False)

    def test_registry_rejects_reintroduced_rights_block(self):
        payload=json.loads(self.path.read_text(encoding='utf-8'))
        payload['sources'][0]['production_acquisition_allowed']=False
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'stale-rights-gate.json'
            path.write_text(json.dumps(payload),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'SOURCE_USE_PRIVATE_RESEARCH_ACQUISITION_REQUIRED'):
                SourceRightsRegistry.load(path,verify_inputs=False)
if __name__=='__main__':unittest.main()
