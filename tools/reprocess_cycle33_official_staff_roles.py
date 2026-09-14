"""Reprocess all 6,215 current parsed staff records through the Cycle 33 taxonomy.

Does not promote OTHER_POSITION into principal HC/OC/DC without source titles.
A wide HC/OC/DC table remains a presentation pivot.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.cycle33.role_taxonomy import assignments_from_title

PARSED = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z"
    r"\implementation_output\science\CYCLE32_OFFICIAL_STAFF_PARSED.jsonl"
)
DEFAULT_OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z\implementation_output\science"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    rows: list[dict[str, Any]] = []
    role_counts: Counter[str] = Counter()
    occupancy: Counter[str] = Counter()
    unique_people: set[str] = set()
    program_name_pairs: set[tuple[str, str]] = set()
    unmapped = 0
    for line in PARSED.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        title = str(row.get("source_title") or row.get("title") or "")
        mapped = assignments_from_title(title)
        primary = [
            item for item in mapped if item["occupancy"] in {"PRINCIPAL", "CO_SHARED"}
        ]
        observed = [item for item in mapped if item["occupancy"] == "OBSERVED"]
        qualified = [
            item for item in mapped if item["occupancy"] == "QUALIFIED_NOT_PRINCIPAL"
        ]
        unmapped_rows = [item for item in mapped if item["occupancy"] == "UNMAPPED"]
        for item in mapped:
            role_counts[item["role"]] += 1
            occupancy[item["occupancy"]] += 1
        if unmapped_rows and not (primary or observed or qualified):
            unmapped += 1
        person = str(row.get("person") or "")
        program = str(row.get("program_id") or row.get("display_name") or "")
        unique_people.add(person.casefold())
        program_name_pairs.add((program, person.casefold()))
        rows.append(
            {
                **row,
                "taxonomy_assignments": mapped,
                "predecessor_role": row.get("role"),
                "taxonomy_primary_roles": [item["role"] for item in primary],
                "taxonomy_observed_roles": [item["role"] for item in observed],
                "taxonomy_qualified_roles": [item["role"] for item in qualified],
                "unmapped_title_review_required": bool(unmapped_rows and not primary),
                "raw_title_roundtrip": title,
                "pit_admitted": False,
            }
        )
    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
    jsonl = DEFAULT_OUT / "CYCLE33_OFFICIAL_STAFF_TAXONOMY.jsonl"
    jsonl.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    summary = {
        "artifact_type": "CYCLE33_OFFICIAL_STAFF_TAXONOMY",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "source": str(PARSED),
        "record_count": len(rows),
        "unique_global_name_strings": len(unique_people),
        "unique_program_name_pairs": len(program_name_pairs),
        "name_string_is_not_unique_person": True,
        "predecessor_other_position": 5337,
        "taxonomy_role_counts": dict(role_counts),
        "occupancy_counts": dict(occupancy),
        "unmapped_title_count": unmapped,
        "pit_admitted": False,
        "not_principal_hc_oc_dc_promotion": True,
    }
    (DEFAULT_OUT / "CYCLE33_OFFICIAL_STAFF_TAXONOMY.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: summary[k]
                for k in ("record_count", "occupancy_counts", "unmapped_title_count")
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
