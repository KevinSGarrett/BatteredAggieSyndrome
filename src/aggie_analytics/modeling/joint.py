from __future__ import annotations
from dataclasses import dataclass
from math import exp, factorial
from .contracts import JointScoreDistribution, ScoreOutcome
from .runtime import FeatureVector, ModelArtifact, assert_training_precedes_prediction


def _poisson_pmf(k:int, lam:float)->float:
    if lam<=0: raise ValueError('Poisson rate must be positive')
    return exp(-lam)*(lam**k)/factorial(k)

@dataclass
class IndependentPoissonScoreRuntime:
    artifact: ModelArtifact
    team_lambda_feature: str='expected_team_points'
    opponent_lambda_feature: str='expected_opponent_points'
    max_score: int=70
    overtime_team_win_probability: float=0.5
    def predict_distribution(self,row:FeatureVector)->JointScoreDistribution:
        assert_training_precedes_prediction(self.artifact,row)
        if self.max_score<1: raise ValueError('max_score must be positive')
        lt=float(row.values[self.team_lambda_feature]); lo=float(row.values[self.opponent_lambda_feature])
        team=[_poisson_pmf(k,lt) for k in range(self.max_score+1)]
        opp=[_poisson_pmf(k,lo) for k in range(self.max_score+1)]
        # Fold tiny omitted upper-tail mass into the terminal support point on each marginal.
        team[-1]+=1-sum(team); opp[-1]+=1-sum(opp)
        outcomes=tuple(ScoreOutcome(a,b,pa*pb) for a,pa in enumerate(team) for b,pb in enumerate(opp))
        dist=JointScoreDistribution(
            distribution_id=f'{self.artifact.model_id}:{self.artifact.model_version}:{row.game_id}',
            model_id=self.artifact.model_id, model_version=self.artifact.model_version,
            forecast_cutoff=row.forecast_cutoff, outcomes=outcomes,
            overtime_team_win_probability=self.overtime_team_win_probability)
        dist.validate(); return dist
