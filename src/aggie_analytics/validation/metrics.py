from __future__ import annotations
import math
from typing import Iterable, Sequence

def _pairs(y_true: Iterable[float], y_pred: Iterable[float]) -> list[tuple[float,float]]:
    pairs=list(zip(y_true,y_pred))
    if not pairs:
        raise ValueError("at least one observation is required")
    return [(float(y),float(p)) for y,p in pairs]

def brier_score(y_true: Iterable[float], probabilities: Iterable[float]) -> float:
    pairs=_pairs(y_true,probabilities)
    for y,p in pairs:
        if y not in {0.0,1.0} or not 0.0 <= p <= 1.0:
            raise ValueError("binary labels and probabilities in [0,1] required")
    return sum((p-y)**2 for y,p in pairs)/len(pairs)

def log_loss(y_true: Iterable[float], probabilities: Iterable[float], *, epsilon: float=1e-15) -> float:
    if not 0.0 < epsilon < 0.5:
        raise ValueError("epsilon must be in (0,0.5)")
    pairs=_pairs(y_true,probabilities)
    total=0.0
    for y,p in pairs:
        if y not in {0.0,1.0} or not 0.0 <= p <= 1.0:
            raise ValueError("binary labels and probabilities in [0,1] required")
        q=min(max(p,epsilon),1.0-epsilon)
        total += -(y*math.log(q)+(1.0-y)*math.log(1.0-q))
    return total/len(pairs)

def mae(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    pairs=_pairs(y_true,y_pred)
    return sum(abs(p-y) for y,p in pairs)/len(pairs)

def rmse(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    pairs=_pairs(y_true,y_pred)
    return math.sqrt(sum((p-y)**2 for y,p in pairs)/len(pairs))

def expected_calibration_error(y_true: Sequence[float], probabilities: Sequence[float], *, bin_edges: Sequence[float]) -> float:
    if len(y_true)!=len(probabilities) or not y_true:
        raise ValueError("equal non-empty inputs required")
    edges=[float(x) for x in bin_edges]
    if len(edges)<2 or edges[0] != 0.0 or edges[-1] != 1.0 or any(a>=b for a,b in zip(edges,edges[1:])):
        raise ValueError("bin_edges must be strictly increasing from 0 to 1")
    buckets=[[] for _ in range(len(edges)-1)]
    for y,p in zip(y_true,probabilities):
        y=float(y); p=float(p)
        if y not in {0.0,1.0} or not 0.0 <= p <= 1.0:
            raise ValueError("binary labels and probabilities in [0,1] required")
        idx=len(buckets)-1 if p==1.0 else next((i for i,(lo,hi) in enumerate(zip(edges,edges[1:])) if lo<=p<hi),None)
        if idx is None:
            raise ValueError("probability does not fall inside bins")
        buckets[idx].append((y,p))
    n=len(y_true); ece=0.0
    for bucket in buckets:
        if not bucket: continue
        obs=sum(y for y,_ in bucket)/len(bucket)
        pred=sum(p for _,p in bucket)/len(bucket)
        ece += len(bucket)/n * abs(obs-pred)
    return ece

def bas_probabilities_are_nested(p3: float,p7: float,p14: float,p21: float) -> bool:
    vals=[float(p3),float(p7),float(p14),float(p21)]
    return all(0.0<=x<=1.0 for x in vals) and vals[3] <= vals[2] <= vals[1] <= vals[0]
