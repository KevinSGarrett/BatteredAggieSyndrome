"""Wave 24 end-to-end readiness and replay-safety helpers.

These helpers exercise existing production starter boundaries. They do not
claim that a historical data lake or empirical replay has been completed.
"""
from .e2e import run_synthetic_e2e, run_leakage_battery, replay_readiness_report

__all__ = ["run_synthetic_e2e", "run_leakage_battery", "replay_readiness_report"]
