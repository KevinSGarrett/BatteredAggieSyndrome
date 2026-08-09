from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class WeightedProbabilityEnsemble:
    ensemble_id: str
    weights: tuple[float,...]
    def combine(self, probabilities:Sequence[float])->float:
        if len(probabilities)!=len(self.weights) or not probabilities: raise ValueError('probabilities/weights must align')
        if any(w<0 for w in self.weights) or abs(sum(self.weights)-1)>1e-9: raise ValueError('weights must be nonnegative and sum to one')
        if any(not 0<=float(p)<=1 for p in probabilities): raise ValueError('probabilities must be in [0,1]')
        return sum(w*float(p) for w,p in zip(self.weights,probabilities))
