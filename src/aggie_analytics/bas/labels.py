from __future__ import annotations
from collections.abc import Iterable
from .contracts import BasLabel,ExpectedMarginEvidence
SEVERITY_THRESHOLDS=(3.0,7.0,14.0,21.0)
def performance_residual(actual_margin:float,expected_margin:float)->float:return float(actual_margin)-float(expected_margin)
def underperformance_shortfall(actual_margin:float,expected_margin:float)->float:return -performance_residual(actual_margin,expected_margin)
def severity_flags(actual_margin:float,expected_margin:float)->dict[str,bool]:
    s=underperformance_shortfall(actual_margin,expected_margin)
    return {"ge_3":s>=3.0,"ge_7":s>=7.0,"ge_14":s>=14.0,"ge_21":s>=21.0}
def build_tamu_bas_label(game_id:str,actual_margin:float,expectation:ExpectedMarginEvidence)->BasLabel:
    expectation.validate()
    if game_id!=expectation.target_game_id:raise ValueError("Label game must match expectation target game")
    r=performance_residual(actual_margin,expectation.expected_margin);f=severity_flags(actual_margin,expectation.expected_margin)
    return BasLabel(game_id,"TAMU",float(actual_margin),float(expectation.expected_margin),r,-r,f["ge_3"],f["ge_7"],f["ge_14"],f["ge_21"],expectation.evidence_id)
def validate_nested_probability_forecast(p_ge_3:float,p_ge_7:float,p_ge_14:float,p_ge_21:float)->bool:
    vals=(p_ge_3,p_ge_7,p_ge_14,p_ge_21)
    if any(v<0 or v>1 for v in vals):raise ValueError("probabilities must be in [0,1]")
    if not(p_ge_21<=p_ge_14<=p_ge_7<=p_ge_3):raise ValueError("BAS severity probabilities must be nested")
    return True
def descriptive_excess_rate(tamu_events:Iterable[bool],peer_events:Iterable[bool])->float:
    """Descriptive only; does not establish statistical significance."""
    a=list(tamu_events);p=list(peer_events)
    if not a or not p:raise ValueError("both samples required")
    return sum(a)/len(a)-sum(p)/len(p)
