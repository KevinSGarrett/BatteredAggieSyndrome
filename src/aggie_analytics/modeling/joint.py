from __future__ import annotations
from dataclasses import dataclass
from math import exp, fsum, isfinite, lgamma, log
from .contracts import JointScoreDistribution, ScoreOutcome
from .runtime import FeatureVector, ModelArtifact, assert_training_precedes_prediction


def _poisson_pmf(k:int, lam:float)->float:
    if not isfinite(lam) or lam<=0: raise ValueError('Poisson rate must be finite and positive')
    return exp(-lam+k*log(lam)-lgamma(k+1))

@dataclass
class IndependentPoissonScoreRuntime:
    artifact: ModelArtifact
    team_lambda_feature: str='expected_team_points'
    opponent_lambda_feature: str='expected_opponent_points'
    max_score: int=70
    overtime_team_win_probability: float=0.5
    def predict_distribution(self,row:FeatureVector)->JointScoreDistribution:
        assert_training_precedes_prediction(self.artifact,row)
        if isinstance(self.max_score, bool) or not isinstance(self.max_score, int) or self.max_score<1:
            raise ValueError('max_score must be a positive integer')
        lt=float(row.values[self.team_lambda_feature]); lo=float(row.values[self.opponent_lambda_feature])
        team=[_poisson_pmf(k,lt) for k in range(self.max_score+1)]
        opp=[_poisson_pmf(k,lo) for k in range(self.max_score+1)]
        # Only numerical-scale tail mass may be folded into terminal support.
        # A materially truncated distribution would estimate censored scores.
        for marginal in (team, opp):
            tail = 1-fsum(marginal)
            if tail > 1e-9 or tail < -1e-9:
                raise ValueError('POISSON_TAIL_TRUNCATION: increase max_score to cover the requested rates')
            # Put floating-point normalization noise on the largest cell so an
            # extremely small terminal probability can never become negative.
            index = len(marginal)-1 if tail >= 0 else max(range(len(marginal)), key=marginal.__getitem__)
            marginal[index] += tail
        outcomes=tuple(ScoreOutcome(a,b,pa*pb) for a,pa in enumerate(team) for b,pb in enumerate(opp))
        dist=JointScoreDistribution(
            distribution_id=f'{self.artifact.model_id}:{self.artifact.model_version}:{row.game_id}',
            model_id=self.artifact.model_id, model_version=self.artifact.model_version,
            forecast_cutoff=row.forecast_cutoff, outcomes=outcomes,
            overtime_team_win_probability=self.overtime_team_win_probability)
        dist.validate(); return dist
