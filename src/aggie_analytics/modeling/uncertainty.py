
from __future__ import annotations
from math import isfinite
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
        if not isinstance(signal.calibrated, bool):
            raise ValueError('calibrated must be a boolean')
        if signal.calibrated and (not isinstance(signal.evidence_id, str) or not signal.evidence_id.strip()):
            raise ValueError('calibration claim requires an evidence reference; empirical acceptance is separate')
        if signal.magnitude is not None and (isinstance(signal.magnitude, bool) or not isfinite(signal.magnitude) or signal.magnitude < 0):
            raise ValueError('uncertainty magnitude must be finite and nonnegative')
        if signal.magnitude is not None and not signal.calibrated:
            raise ValueError("numeric uncertainty magnitude may not be presented as calibrated when calibrated=False")
    return True
