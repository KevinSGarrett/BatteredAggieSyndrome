"""Cycle #29 scientific-control successor.

Does not authorize empirical skill, a champion, BAS, Aggie Excess, A&M lift,
protected-lane activation, or all-cycle scientific-trust recovery. Fitted
forecasts remain UNTRUSTED_SHADOW while the operator hold is active.
"""

from __future__ import annotations

SCHEMA_VERSION = "aggie.cycle29.scientific_control.v1"
CONTRACT_ID = "CYCLE29-SCIENTIFIC-TRUST-KERNEL-AND-NATIONAL-CENSUS-V1"
HOLD_ACTIVE = True
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
OPERATOR_HOLD = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"
