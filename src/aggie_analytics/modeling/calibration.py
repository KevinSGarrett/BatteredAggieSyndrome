from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Sequence

class ProbabilityCalibrator:
    calibration_id: str
    def calibrate(self,p:float)->float: raise NotImplementedError

@dataclass(frozen=True)
class IdentityCalibrator(ProbabilityCalibrator):
    calibration_id: str='CAL-IDENTITY'
    def calibrate(self,p:float)->float:
        if not 0<=p<=1: raise ValueError('probability must be in [0,1]')
        return float(p)

@dataclass(frozen=True)
class LogisticCalibrator(ProbabilityCalibrator):
    slope: float
    intercept: float
    calibration_id: str='CAL-LOGISTIC-STARTER'
    development_only: bool=True
    def calibrate(self,p:float)->float:
        if not self.development_only: raise ValueError('W20 calibration parameters must be development-only')
        if not 0<=p<=1: raise ValueError('probability must be in [0,1]')
        eps=1e-12; q=min(max(float(p),eps),1-eps); logit=math.log(q/(1-q))
        z=self.intercept+self.slope*logit
        return 1/(1+math.exp(-max(min(z,40.0),-40.0)))
