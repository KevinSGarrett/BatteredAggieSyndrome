"""Coaching and feature model-admission boundary for Cycle #29."""

from __future__ import annotations

from typing import Any, Mapping

from aggie_analytics.cycle29.coaching import model_admission_gate


class AdmissionError(ValueError):
    """Raised when model-admission boundaries are violated."""


def prove_coaching_not_modeled(design_columns: Mapping[str, Any]) -> dict[str, Any]:
    staff = [
        name
        for name in design_columns
        if "coach" in name.lower() or "staff" in name.lower()
    ]
    consumed = [
        name
        for name in staff
        if design_columns.get(name) not in {None, False, 0, "NOT_CONSUMED"}
    ]
    if consumed:
        raise AdmissionError(f"coaching columns consumed by model: {consumed}")
    gate = model_admission_gate()
    if gate["coaching_enters_model"]:
        raise AdmissionError("coaching model admission gate is open")
    return {**gate, "inspected_columns": list(design_columns)}


def reject_candidate_in_model(row_state: str) -> None:
    if row_state == "CANDIDATE_ONLY" or row_state == "CANDIDATE":
        raise AdmissionError("candidate coaching row cannot enter a model")
