"""Immutable MR31 finding-ID correction. Cycle32 labels are a predecessor report."""

from __future__ import annotations

from typing import Any

# Cycle32 disposition reused MR31-09 onward for later Cycle32 repairs.
# Original manager-review meanings in FINDING_TO_REQUIREMENT.json remain authoritative.
# Do not silently renumber. Preserve the Cycle32 report as predecessor.
CYCLE32_DISPOSITION_LABEL_TO_ORIGINAL_MR31: dict[str, str] = {
    "MR31-01": "MR31-01",
    "MR31-02": "MR31-02",
    "MR31-03": "MR31-03",
    "MR31-04": "MR31-04",
    "MR31-05": "MR31-05",
    "MR31-08": "MR31-08",
    # Cycle32 used MR31-09 for kernel missing-numeric/label imputation.
    # Original MR31-09 is target-freeze / retrospective feature lineage.
    "MR31-09": "MR31-10",
    # Cycle32 used MR31-10 for neutral designation invariance.
    "MR31-10": "MR31-11",
    # Cycle32 used MR31-11 for official-final synthetic 21-14 / 0-99.
    "MR31-11": "MR31-12",
    # Cycle32 used MR31-12 for coordinated rehash tamper.
    "MR31-12": "MR31-13",
    # Cycle32 used MR31-13 for name-only availability join.
    "MR31-13": "MR31-15",
}

ORIGINAL_MR31_MEANINGS: dict[str, str] = {
    "MR31-01": "Tested implementation is not identified by the reported Git HEAD",
    "MR31-02": "Predecessor artifact and input identities were changed in place",
    "MR31-03": "Nine additional wrong-school source bindings reach confirmed HC cells",
    "MR31-04": "All-sports and support staff still enter football head-coach cells",
    "MR31-05": "Person/co-role repair is incomplete at materialized-data level",
    "MR31-06": "Historical coaching frame still projects current survivors backward",
    "MR31-07": "Historical season/person parse defects remain",
    "MR31-08": "Malformed unproven receipt still obtains PROVEN authority",
    "MR31-09": "Target freeze receipt still promotes retrospective feature lineage",
    "MR31-10": "Missing numerical predictors and labels still become zero",
    "MR31-11": "Neutral designation invariance still fails all tested candidates",
    "MR31-12": "Scoring repair fails open for unrecognized page layout",
    "MR31-13": "Science acceptance still trusts stale matched flag after rehash",
    "MR31-14": "Typed contract repairs leave invalid and incompatible payloads accepted",
    "MR31-15": "Availability name-only join can mark the wrong school player verified",
    "MR31-16": "Requirement union completeness measures placeholders rather than traceability",
    "MR31-17": "Named-unit three-pass completion overstates semantic work",
    "MR31-18": "Hosted checks have not validated the Cycle31 dirty repair tree",
    "MR31-19": "Completion schema and blocker accounting remain misleading",
    "MR31-20": "Cross-system plan/contract adoption is still incomplete",
}

BLOCK_CLASSES = (
    "LOCAL_REPAIR_REQUIRED",
    "SOURCE_UNAVAILABLE_AFTER_BOUNDED_ATTEMPTS",
    "OWNER_ADJUDICATION",
    "HOSTED_REVIEW",
    "RELEASE_AUTHORITY",
)


def correction_row(finding_id: str, **fields: Any) -> dict[str, Any]:
    mapped = CYCLE32_DISPOSITION_LABEL_TO_ORIGINAL_MR31.get(finding_id)
    base = {
        "finding_id": finding_id,
        "silent_renumbering": False,
        "predecessor_report_preserved": True,
        "original_mr31_id": mapped or finding_id,
        "original_meaning": ORIGINAL_MR31_MEANINGS.get(mapped or finding_id, ""),
        "cycle32_disposition_label": finding_id if mapped else None,
    }
    if mapped and mapped != finding_id:
        base["cycle32_label_was_shifted"] = True
        base["action"] = "PRESERVE_PREDECESSOR_REPORT_AND_RESTORE_ORIGINAL_MEANING"
    base.update(fields)
    return base


def full_correction_table() -> list[dict[str, Any]]:
    rows = [correction_row(fid) for fid in ORIGINAL_MR31_MEANINGS]
    for cycle32_label, original in CYCLE32_DISPOSITION_LABEL_TO_ORIGINAL_MR31.items():
        if cycle32_label != original:
            rows.append(
                {
                    "finding_id": f"CYCLE32_LABEL:{cycle32_label}",
                    "maps_to_original": original,
                    "original_meaning": ORIGINAL_MR31_MEANINGS[original],
                    "silent_renumbering": False,
                    "predecessor_report_preserved": True,
                }
            )
    return rows
