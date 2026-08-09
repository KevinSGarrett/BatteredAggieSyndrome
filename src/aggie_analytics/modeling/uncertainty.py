
from __future__ import annotations
from .contracts import UncertaintySignal

KNOWN_CATEGORIES={
    "ALEATORIC_GAME","EPISTEMIC_MODEL","DATA_QUALITY","AVAILABILITY","WEATHER",
    "OPPONENT_STRENGTH","REGIME_STATE","TAMU_SPECIALIZATION","MODEL_DISAGREEMENT"
}

def validate_uncertainty_signals(signals: list[UncertaintySignal]) -> bool:
    names=set()
    for signal in signals:
        if not signal.name: raise ValueError("uncertainty signal name is required")
        if signal.name in names: raise ValueError("duplicate uncertainty signal")
        names.add(signal.name)
        if signal.category not in KNOWN_CATEGORIES:
            raise ValueError(f"unknown uncertainty category: {signal.category}")
        if signal.magnitude is not None and not signal.calibrated:
            raise ValueError("numeric uncertainty magnitude may not be presented as calibrated when calibrated=False")
    return True
