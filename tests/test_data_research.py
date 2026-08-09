from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.validate_data_research import validate
class TestW06DataResearch(unittest.TestCase):
    def test_w06_data_research_contract(self):
        self.assertEqual(validate(ROOT),[])
    def test_required_w06_artifacts_exist(self):
        base=ROOT/'docs/data_research/w06'
        for name in ['DATA_UNIVERSE_MASTER.csv','DATA_DOMAIN_COVERAGE_MATRIX.csv','POINT_IN_TIME_FEASIBILITY_MATRIX.csv','SOURCE_ACCESS_LICENSE_MATRIX.csv','DATA_RESEARCH_FINDINGS.md','WAVE_06_ARCHITECTURE_IMPACT.md']:
            self.assertTrue((base/name).is_file(),name)
if __name__=='__main__':unittest.main()
