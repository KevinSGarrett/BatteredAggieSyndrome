"""Cycle #30 scientific-control successor.

Does not authorize empirical skill, a champion, BAS, Aggie Excess, A&M lift,
protected-lane activation, merge, or all-cycle scientific-trust recovery.
Fitted forecasts remain UNTRUSTED_SHADOW while the operator hold is active.
"""

from __future__ import annotations

SCHEMA_VERSION = "aggie.cycle30.scientific_control.v1"
CONTRACT_ID = "CYCLE30-NEUTRAL-NATIONAL-KERNEL-V1"
HOLD_ACTIVE = True
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
OPERATOR_HOLD = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"
REVIEW_STATE = "READY_FOR_MANAGER_REVIEW"
PRIMARY_KERNEL_OBJECTIVE = "PRIMARY_KERNEL_OBJECTIVE"
