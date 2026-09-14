"""Score producer staff extraction against independently frozen CS-05 labels."""

from __future__ import annotations

from typing import Any, Mapping

from aggie_analytics.cycle33.nameset_adjudication import (
    adjudicate_person,
    principal_occupants,
)
from aggie_analytics.scientific_reference.cycle33_cs05 import (
    PROTOCOL_ID,
    FROZEN_CURRENT_LABELS,
    score_sets,
    stratified_counts,
)

def extracted_principal_rows(
    html: str, *, role: str, page_url: str = ""
) -> list[dict[str, str]]:
    return [
        {"person": row["person"], "role": role}
        for row in principal_occupants(html, role=role, page_url=page_url)
    ]


def score_frozen_current(
    html_by_program: Mapping[str, str],
    *,
    url_by_program: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Score only labeled current program-roles. Unlabeled pages are excluded."""

    urls = url_by_program or {}
    expected_positive = [
        row for row in FROZEN_CURRENT_LABELS if row.get("expected_principal")
    ]
    extracted: list[dict[str, str]] = []
    negatives: list[dict[str, Any]] = []
    for label in FROZEN_CURRENT_LABELS:
        program = str(label["program"])
        html = html_by_program.get(program) or ""
        if not html:
            continue
        role = str(label["role"])
        found = adjudicate_person(
            html,
            person=str(label["person"]),
            role=role,
            page_url=urls.get(program, ""),
        )
        principal = found["verdict"] == "PRINCIPAL_OR_CO_ROLE_SUPPORTED"
        if label.get("expected_principal"):
            if principal:
                extracted.append({"person": str(label["person"]), "role": role})
        else:
            negatives.append(
                {
                    "person": label["person"],
                    "role": role,
                    "expected_principal": False,
                    "extracted_principal": principal,
                    "record_title": found.get("record_title"),
                    "true_negative": not principal,
                }
            )
    by_program: dict[str, set[str]] = {}
    for label in expected_positive:
        by_program.setdefault(str(label["program"]), set()).add(str(label["role"]))
    for program, roles in by_program.items():
        html = html_by_program.get(program) or ""
        if not html:
            continue
        for role in roles:
            extracted.extend(
                extracted_principal_rows(
                    html, role=role, page_url=urls.get(program, "")
                )
            )
    # Deduplicate extracted after union of occupant scan (includes extras = FP)
    uniq: dict[tuple[str, str], dict[str, str]] = {}
    for row in extracted:
        uniq[(row["person"].casefold(), row["role"])] = row
    metrics = score_sets(expected_positive, list(uniq.values()))
    tn = sum(1 for row in negatives if row["true_negative"])
    fp_neg = sum(1 for row in negatives if not row["true_negative"])
    return {
        "artifact_type": "CYCLE33_CS05_FROZEN_CURRENT_SCORE",
        "protocol_id": PROTOCOL_ID,
        "name_hit_diagnostic_is_not_this_score": True,
        "label_boundary": "FROZEN_CURRENT_LABELS",
        "label_counts": stratified_counts(FROZEN_CURRENT_LABELS),
        "metrics": metrics,
        "negative_true_negatives": tn,
        "negative_false_positives": fp_neg,
        "negatives": negatives,
        "unsampled_population_not_certified": True,
        "pit_admitted": False,
    }
