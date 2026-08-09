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
        self.assertEqual(len(self.registry.decisions),62)
        raw=self.path.read_text(encoding='utf-8')
        for marker in ('SCRAPFLY_API_TOKEN=','SCRAPERAPI_API_TOKEN=','GITHUB_TOKEN=','CFBD_API_KEY='):
            self.assertNotIn(marker,raw)

    def test_acquisition_fails_closed_for_unknown_or_unapproved_sources(self):
        self.assertEqual(
            self.registry.require('SRC-002',SourceRightsAction.ACQUIRE_PRODUCTION).source_id,
            'SRC-002',
        )
        with self.assertRaisesRegex(SourceRightsDenied,'SOURCE_RIGHTS_SOURCE_UNKNOWN'):
            self.registry.require('SRC-999',SourceRightsAction.ACQUIRE_PRODUCTION)
        with self.assertRaisesRegex(SourceRightsDenied,'SOURCE_RIGHTS_DENIED:SRC-006'):
            self.registry.require('SRC-006',SourceRightsAction.ACQUIRE_EXPERIMENTAL)
        with self.assertRaisesRegex(SourceRightsDenied,'SOURCE_RIGHTS_DENIED:SRC-047:ACQUIRE_PRODUCTION'):
            self.registry.require('SRC-047',SourceRightsAction.ACQUIRE_PRODUCTION)
        self.registry.require('SRC-047',SourceRightsAction.ACQUIRE_EXPERIMENTAL)

    def test_access_and_redistribution_are_independent(self):
        cfbd=self.registry.require('SRC-002',SourceRightsAction.ACQUIRE_PRODUCTION)
        self.assertTrue(cfbd.production_acquisition_allowed)
        self.assertFalse(cfbd.raw_export_allowed)
        with self.assertRaisesRegex(SourceRightsDenied,'SOURCE_RIGHTS_DENIED:SRC-002:EXPORT_RAW'):
            self.registry.require('SRC-002',SourceRightsAction.EXPORT_RAW)
        open_meteo_payload=next(
            row for row in json.loads(self.path.read_text(encoding='utf-8'))['sources']
            if row['source_id']=='SRC-003'
        )
        self.assertEqual(open_meteo_payload['provider_raw_redistribution_permission'],'PERMITTED_WITH_ATTRIBUTION')
        self.assertFalse(open_meteo_payload['raw_export_allowed'])

    def test_registry_rejects_unsafe_mutations(self):
        payload=json.loads(self.path.read_text(encoding='utf-8'))
        payload['sources'][0]['lane_disposition']='EXPERIMENTAL_APPROVED'
        payload['sources'][0]['production_acquisition_allowed']=True
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unsafe.json'
            path.write_text(json.dumps(payload),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'SOURCE_RIGHTS_UNSAFE_PRODUCTION_PROMOTION'):
                SourceRightsRegistry.load(path,verify_inputs=False)
if __name__=='__main__':unittest.main()
