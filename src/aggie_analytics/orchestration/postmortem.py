from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json

from .contracts import stable_hash


@dataclass(frozen=True)
class CompletedGameResult:
    game_id: str
    team_score: int
    opponent_score: int
    completed_at: datetime
    source_ref: str
    def validate(self):
        if not self.game_id or not self.source_ref or self.completed_at.tzinfo is None: raise ValueError("completed result identity required")
        if self.team_score < 0 or self.opponent_score < 0: raise ValueError("scores cannot be negative")


def build_postmortem(*, game: CompletedGameResult, forecast_summary: dict[str,float], forecast_ref: str) -> dict:
    game.validate()
    if not forecast_ref: raise ValueError("forecast_ref required")
    actual_margin=game.team_score-game.opponent_score
    expected_margin=float(forecast_summary["expected_margin"])
    win_prob=float(forecast_summary["win_probability"])
    actual_win=1.0 if actual_margin>0 else 0.0
    return {
        "game_id":game.game_id,"forecast_ref":forecast_ref,"result_source_ref":game.source_ref,
        "actual_margin":actual_margin,"expected_margin":expected_margin,"margin_error":actual_margin-expected_margin,
        "win_probability":win_prob,"win_probability_error":actual_win-win_prob,
        "created_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def research_proposal_from_postmortem(postmortem: dict, *, threshold: float=7.0) -> dict | None:
    if abs(float(postmortem["margin_error"])) < threshold: return None
    core={"kind":"FORECAST_ERROR_REVIEW","game_id":postmortem["game_id"],"forecast_ref":postmortem["forecast_ref"],
          "observed_margin_error":postmortem["margin_error"],"allowed_action":"PROPOSE_EXPERIMENT_ONLY"}
    return {**core,"proposal_id":"proposal-"+stable_hash(core)[:16]}
