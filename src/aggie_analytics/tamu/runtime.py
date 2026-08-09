from __future__ import annotations
from dataclasses import dataclass
from .state import TamuStateOverlay
from .specialization import SpecializationSignal

@dataclass(frozen=True)
class TamuForecastAdapter:
    state:TamuStateOverlay
    specialization:SpecializationSignal
    national_forecast_ref:str
    def validate(self)->None:
        if self.state.team_id.upper() not in {'TAMU','TEXAS_A&M','TEXAS A&M'}: raise ValueError('adapter is Texas A&M scoped')
        if self.specialization.production_selected: raise ValueError('W20 starter cannot preselect specialization')
        if not self.national_forecast_ref: raise ValueError('national no-adjustment reference is required')
    @property
    def candidate_adjustment(self)->float:
        self.validate(); return self.specialization.shrunk_adjustment
