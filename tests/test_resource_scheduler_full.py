import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import unittest
from aggie_analytics.experimentation.scheduler import ResourceRequest,ResourcePool,QueueCandidate,can_admit,select_admissible

class SchedulerFullTests(unittest.TestCase):
    def candidate(self,eid,idx,request=None,**kw):
        base=dict(priority="MUST",dependency_ready=True,owner_wave_active=True,protected_rule_seal_valid=True,shared_contract_conflict=False)
        base.update(kw)
        return QueueCandidate(eid,request=request or ResourceRequest(),queue_index=idx,**base)

    def test_paid_compute_blocks(self):
        c=self.candidate("E",0,ResourceRequest(paid_compute=True))
        ok,reasons=can_admit(c,ResourcePool(8,32000,1,8000,100000,False))
        self.assertFalse(ok); self.assertIn("PAID_COMPUTE_NOT_APPROVED",reasons)

    def test_owner_wave_blocks(self):
        c=self.candidate("E",0,owner_wave_active=False)
        self.assertFalse(can_admit(c,ResourcePool(8,32000,1,8000,100000))[0])

    def test_bounded_selection(self):
        pool=ResourcePool(4,8000,0,0,10000)
        cs=[self.candidate(f"E{i}",i,ResourceRequest(cpu_threads=2,ram_mb=2000,disk_mb=1000)) for i in range(4)]
        selected=select_admissible(cs,pool,10)
        self.assertEqual(len(selected),2)
