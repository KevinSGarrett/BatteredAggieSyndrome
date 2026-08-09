
from __future__ import annotations
from collections import defaultdict
import random
from .contracts import JointScoreDistribution, ScoreOutcome, SimulationScenario

def mix_joint_distributions(weighted: list[tuple[SimulationScenario, JointScoreDistribution]], *,
                            distribution_id: str, model_id: str, model_version: str) -> JointScoreDistribution:
    if not weighted:
        raise ValueError("at least one scenario distribution is required")
    total_weight=sum(float(s.weight) for s,_ in weighted)
    if abs(total_weight-1.0)>1e-9:
        raise ValueError("scenario weights must sum to one")
    mass: dict[tuple[int,int],float]=defaultdict(float)
    cutoff=None
    # To mix tie mass coherently, every member must either have no ties or the same explicit OT resolver.
    ot_values=set()
    for scenario,dist in weighted:
        scenario.validate(); dist.validate()
        if cutoff is None: cutoff=dist.forecast_cutoff
        if dist.forecast_cutoff != cutoff:
            raise ValueError("scenario distributions must share the forecast cutoff")
        tie_mass=sum(x.probability for x in dist.outcomes if x.team_score==x.opponent_score)
        if tie_mass>dist.tolerance: ot_values.add(float(dist.overtime_team_win_probability))
        for x in dist.outcomes:
            mass[(x.team_score,x.opponent_score)] += float(scenario.weight)*float(x.probability)
    if len(ot_values)>1:
        raise ValueError("scenario members with tie mass must share overtime resolver for simple mixture")
    outcomes=tuple(ScoreOutcome(a,b,p) for (a,b),p in sorted(mass.items()))
    result=JointScoreDistribution(distribution_id,model_id,model_version,cutoff,outcomes,
                                  next(iter(ot_values)) if ot_values else None)
    result.validate()
    return result

def sample_score_outcomes(dist: JointScoreDistribution, n: int, seed: int) -> list[tuple[int,int]]:
    dist.validate()
    if n < 0: raise ValueError("n must be nonnegative")
    rng=random.Random(seed)
    support=[(x.team_score,x.opponent_score) for x in dist.outcomes]
    weights=[float(x.probability) for x in dist.outcomes]
    return rng.choices(support,weights=weights,k=n)
