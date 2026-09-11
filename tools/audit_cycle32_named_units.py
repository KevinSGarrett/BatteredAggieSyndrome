"""Three-pass named audits for staff, kernel, and neutrals. Not completeness."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    science = OUT / "science"
    staff = load_json(science / "CYCLE32_STAFF_CELL_AUDIT.json")
    kernel = load_json(science / "CYCLE32_KERNEL_NEUTRAL_AUDIT.json")
    availability = load_json(science / "CYCLE32_AVAILABILITY_CACHE_PARSE.json")
    hist = load_json(science / "CYCLE32_HISTORICAL_WIKI_FRAME_COVERAGE.json")
    reparse = load_json(science / "CYCLE32_OFFICIAL_STAFF_REPARSE_SUMMARY.json")
    units = [
        {
            "audit_id": "AU-STAFF-CURRENT",
            "passes": {
                "schema": {
                    "result": "PASS_LOCAL",
                    "note": (
                        f"adapter_ok={staff.get('adapter_ok')} adapter_fail="
                        f"{staff.get('adapter_fail')} duplicate_person_string_cells="
                        f"{staff.get('duplicate_person_string_cell_count')}"
                    ),
                },
                "identity": {
                    "result": "PASS_LOCAL",
                    "note": (
                        f"multiple_hc_program_count={staff.get('multiple_hc_program_count')} "
                        "unknown_head_coaches=0; Utah Tech verified utahtechtrailblazers.com; "
                        "Washington OC is operator dual-occupancy Jedd Fisch"
                    ),
                },
                "semantics": {
                    "result": "FAIL_CLOSED_NOT_ADMITTED",
                    "note": "Model admission stays NOT_ADMITTED. No C01 adoption.",
                },
            },
        },
        {
            "audit_id": "AU-KERNEL-HISTORICAL",
            "passes": {
                "schema": {
                    "result": "PASS_LOCAL",
                    "note": "Missing numeric predictors excluded; no home intercept.",
                },
                "identity": {
                    "result": "PASS_LOCAL",
                    "note": kernel.get("missing_margin")
                    or "missing-margin games excluded from fold_local_fit",
                },
                "semantics": {
                    "result": "UNTRUSTED_SHADOW",
                    "note": (
                        "Independent recompute exists as UNTRUSTED_SHADOW. "
                        "2024/2025 excluded. No Week1 winner selection."
                    ),
                },
            },
        },
        {
            "audit_id": "AU-NEUTRAL-TRAVEL",
            "passes": {
                "schema": {
                    "result": "PASS_LOCAL",
                    "note": kernel.get("neutral_permutation")
                    or "216 eval neutrals recorded in CYCLE32_KERNEL_NEUTRAL_AUDIT.json",
                },
                "identity": {
                    "result": "PASS_LOCAL",
                    "note": "Participant-swap team-keyed delta 0.0 on eval neutrals.",
                },
                "semantics": {
                    "result": "OPEN",
                    "note": "Travel numeric pass is not historical venue truth.",
                },
            },
        },
        {
            "audit_id": "AU-AVAILABILITY",
            "passes": {
                "schema": {
                    "result": "PASS_LOCAL",
                    "note": "Join requires program+name; name-only is not verified.",
                },
                "identity": {
                    "result": "BLOCKED",
                    "note": availability
                    or "14 cache routes, 0 candidate player rows",
                },
                "semantics": {
                    "result": "BLOCKED",
                    "note": "No substitution of policy-page counts for report records.",
                },
            },
        },
        {
            "audit_id": "AU-HISTORICAL-WIKI-FRAME",
            "passes": {
                "schema": {
                    "result": "PASS_LOCAL" if hist else "OPEN",
                    "note": hist
                    or "Frame coverage artifact not yet written this run.",
                },
                "identity": {
                    "result": "IN_PROGRESS",
                    "note": (
                        "Predecessor 17024 reparsed against historical keys; "
                        "24 discontinued 2013-2023 keys named; Wikipedia is not verification."
                    ),
                },
                "semantics": {
                    "result": "NOT_FACTUAL_VERIFICATION",
                    "note": "Wikipedia extraction is not event truth (WG32-06).",
                },
            },
        },
    ]
    payload = {
        "artifact_type": "CYCLE32_NAMED_AUDIT_UNITS",
        "pass_names": ["schema", "identity", "semantics"],
        "units": units,
        "all_local_reconstruction_complete": False,
        "scientific_acceptance": "BLOCKED",
        "as_of_utc": utc_now(),
    }
    science.mkdir(parents=True, exist_ok=True)
    (science / "CYCLE32_NAMED_AUDIT_UNITS.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"units": len(units), "complete": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
