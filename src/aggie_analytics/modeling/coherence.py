
from __future__ import annotations
from collections import defaultdict
from .contracts import JointScoreDistribution

def margin_pmf(dist: JointScoreDistribution) -> dict[int,float]:
    dist.validate()
    out: dict[int,float] = defaultdict(float)
    for x in dist.outcomes:
        out[x.team_score-x.opponent_score] += float(x.probability)
    return dict(sorted(out.items()))

def derive_summary(dist: JointScoreDistribution) -> dict[str,float]:
    dist.validate()
    et=sum(x.team_score*float(x.probability) for x in dist.outcomes)
    eo=sum(x.opponent_score*float(x.probability) for x in dist.outcomes)
    direct_win=sum(float(x.probability) for x in dist.outcomes if x.team_score>x.opponent_score)
    direct_loss=sum(float(x.probability) for x in dist.outcomes if x.team_score<x.opponent_score)
    tie=sum(float(x.probability) for x in dist.outcomes if x.team_score==x.opponent_score)
    if tie:
        ot=float(dist.overtime_team_win_probability)
        pwin=direct_win+tie*ot
        ploss=direct_loss+tie*(1.0-ot)
    else:
        pwin,ploss=direct_win,direct_loss
    return {
        "expected_team_score":et,
        "expected_opponent_score":eo,
        "expected_margin":et-eo,
        "expected_total":et+eo,
        "win_probability":pwin,
        "loss_probability":ploss,
        "tie_mass_before_overtime_resolution":tie,
    }

def bas_severity_probabilities(dist: JointScoreDistribution, bas_anchor_expected_margin: float) -> dict[str,float]:
    dist.validate()
    probs={}
    for threshold in (3,7,14,21):
        cutoff=float(bas_anchor_expected_margin)-threshold
        p=sum(float(x.probability) for x in dist.outcomes if (x.team_score-x.opponent_score) <= cutoff)
        probs[f"ge_{threshold}"]=p
    validate_bas_nesting(probs)
    return probs

def validate_bas_nesting(probs: dict[str,float]) -> bool:
    vals=[float(probs[k]) for k in ("ge_3","ge_7","ge_14","ge_21")]
    if any(v<0 or v>1 for v in vals):
        raise ValueError("BAS probabilities must be in [0,1]")
    if not(vals[3] <= vals[2] <= vals[1] <= vals[0]):
        raise ValueError("BAS severity probabilities must be nested")
    return True
