from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from math import log, sqrt
from typing import Hashable, Iterable, Sequence

def missing_fraction(values: Sequence[object | None]) -> float:
    return sum(v is None for v in values)/len(values) if values else 0.0

def variance(values: Sequence[float]) -> float:
    if not values: return 0.0
    m=sum(values)/len(values); return sum((x-m)**2 for x in values)/len(values)

def pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x)!=len(y): raise ValueError("length mismatch")
    if len(x)<2: return None
    mx=sum(x)/len(x); my=sum(y)/len(y)
    dx=[v-mx for v in x]; dy=[v-my for v in y]
    den=sqrt(sum(v*v for v in dx)*sum(v*v for v in dy))
    return sum(a*b for a,b in zip(dx,dy))/den if den else None

def mutual_information_discrete(x: Sequence[Hashable], y: Sequence[Hashable]) -> float:
    if len(x)!=len(y): raise ValueError("length mismatch")
    n=len(x)
    if n==0: return 0.0
    cx=Counter(x); cy=Counter(y); cxy=Counter(zip(x,y)); out=0.0
    for (a,b),nab in cxy.items():
        p=nab/n; px=cx[a]/n; py=cy[b]/n
        out += p*log(p/(px*py))
    return out

def ablation_delta(full_metric: float, without_family_metric: float, *, lower_is_better: bool=True) -> float:
    """Positive means the family helped under the caller's metric direction."""
    return without_family_metric-full_metric if lower_is_better else full_metric-without_family_metric

def permutation_delta(baseline_metric: float, permuted_metric: float, *, lower_is_better: bool=True) -> float:
    """Positive means permutation harmed performance, suggesting conditional value."""
    return permuted_metric-baseline_metric if lower_is_better else baseline_metric-permuted_metric

def stability_summary(deltas: Sequence[float]) -> dict[str,float|int|None]:
    if not deltas: return {'folds':0,'mean_delta':None,'positive_fraction':None,'min_delta':None,'max_delta':None}
    return {'folds':len(deltas),'mean_delta':sum(deltas)/len(deltas),'positive_fraction':sum(d>0 for d in deltas)/len(deltas),'min_delta':min(deltas),'max_delta':max(deltas)}
