from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class AdapterSpec:
    name: str
    role: str
    selected: bool
    canonical_source_of_truth: bool
    server_required: bool = False

MLFLOW_TRACKING = AdapterSpec("MLflow Tracking","experiment_tracking",True,False,False)
OPTUNA = AdapterSpec("Optuna","hyperparameter_optimization",True,False,False)
STDLIB_MANIFESTS = AdapterSpec("stdlib manifests","canonical_governance_fallback",True,True,False)
