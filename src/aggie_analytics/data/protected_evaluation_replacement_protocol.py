"""Inactive prospective protected-evaluation replacement protocol.

2024/2025 remain historically exposed and are not sealed, blind, or protected
for future model selection. The replacement lane stays inactive until explicit
user approval. BAT-401 remains Done with RETAIN_PROTECTED_LANE_BLOCKED.
"""

from __future__ import annotations

from typing import Any

EXPOSED_SEASONS = (2024, 2025)
LANE_DECISION = "RETAIN_PROTECTED_LANE_BLOCKED"
PROTOCOL_STATUS = "DESIGNED_INACTIVE"


def exposure_record() -> dict[str, Any]:
    return {
        "seasons": list(EXPOSED_SEASONS),
        "historically_exposed": True,
        "sealed": False,
        "blind": False,
        "protected_for_future_model_selection": False,
        "cannot_restore_blind_status": True,
    }


def replacement_protocol(*, user_approved_activation: bool = False) -> dict[str, Any]:
    stages = [
        "development",
        "immutable_freeze",
        "result_acquisition",
        "evaluation_authority",
        "report_release",
    ]
    active = bool(user_approved_activation)
    return {
        "protocol_status": "ACTIVE" if active else PROTOCOL_STATUS,
        "lane_decision": "OPEN" if active else LANE_DECISION,
        "stages": stages,
        "results_inaccessible_to_implementation_until_freeze": True,
        "activation_requires_explicit_user_approval": True,
        "user_approved_activation": active,
        "exposed_seasons": exposure_record(),
        "jira_keep_bat_401_done": True,
        "gap_005_remains_open": True,
    }
