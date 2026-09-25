"""Independently reconstruct the passing-section successor census and corrections."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.data.tamu_official_passing_section_successor import (  # noqa: E402
    EXPECTED_AFFECTED_RAW_PAGES,
    EXPECTED_CONFIRMED_ROWS,
    PREDECESSOR_PLAYER_RELATIVE,
    PREDECESSOR_PLAYER_SHA256,
    census_predecessor,
    succeed_row,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO))
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root)
    data = Path(args.data_root)
    gate = json.loads(
        (
            repo
            / "artifacts/data_lake/tamu_official_passing_section_successor_gate.json"
        ).read_text(encoding="utf-8")
    )
    predecessor = data / PREDECESSOR_PLAYER_RELATIVE
    predecessor_digest = hashlib.sha256(predecessor.read_bytes()).hexdigest()
    if predecessor_digest != PREDECESSOR_PLAYER_SHA256:
        print(json.dumps({"result": "FAIL", "reason": "predecessor_rewritten"}))
        return 1
    census = census_predecessor(data)
    fail = 0
    if census["confirmed_mislabeled_passing_rows"] != EXPECTED_CONFIRMED_ROWS:
        fail += 1
    if census["confirmed_affected_raw_files"] != EXPECTED_AFFECTED_RAW_PAGES:
        fail += 1
    payload = data / gate["payloads"]["player_successor"]["relative_path"]
    rows = [
        json.loads(line)
        for line in payload.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    payload_digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    if payload_digest != gate["payloads"]["player_successor"]["sha256"]:
        fail += 1
    confirmed_ids = {
        str(identity) for identity in census["confirmed_row_identities"] if identity
    }
    unresolved_ids = {
        str(item["row_identity"])
        for item in census["unresolved_identities"]
        if item.get("row_identity")
    }
    reconstructed_fail = 0
    changed = 0
    for row in rows:
        identity = str(row.get("row_identity") or "")
        rebuilt = succeed_row(
            {
                key: value
                for key, value in row.items()
                if key
                not in {
                    "predecessor_stat_group",
                    "attribution_state",
                    "player_identity_role",
                    "original_text_preserved",
                    "raw_section_text",
                    "header_only",
                    "material_statistic_available",
                    "successor_contract_id",
                    "predecessor_rewritten",
                    "trust_classification",
                    "fabricated_person_identity",
                    "stat_group",
                }
            }
            | {
                "stat_group": row.get("predecessor_stat_group"),
                "original_text": row.get("original_text_preserved")
                or row.get("original_text"),
                "name_raw": row.get("name_raw"),
                "row_identity": identity,
                "header_only": row.get("header_only"),
            },
            confirmed_ids=confirmed_ids,
            unresolved_ids=unresolved_ids,
        )
        if rebuilt["stat_group"] != row["stat_group"]:
            reconstructed_fail += 1
        if rebuilt["attribution_state"] != row["attribution_state"]:
            reconstructed_fail += 1
        if row["attribution_state"] == "CONFIRMED_PASSING_SECTION_CORRECTION":
            changed += 1
            if row["stat_group"] != "passing":
                reconstructed_fail += 1
            if row["predecessor_stat_group"] == "passing":
                reconstructed_fail += 1
        if row.get("player_identity_role") == "TEAM_ATTRIBUTED_EVIDENCE":
            if row.get("fabricated_person_identity") is not False:
                reconstructed_fail += 1
    if changed != EXPECTED_CONFIRMED_ROWS:
        reconstructed_fail += 1
    result = {
        "result": "PASS" if fail + reconstructed_fail == 0 else "FAIL",
        "independent_fail_count": fail + reconstructed_fail,
        "confirmed_rows": census["confirmed_mislabeled_passing_rows"],
        "affected_pages": census["confirmed_affected_raw_files"],
        "changed_rows_in_payload": changed,
        "predecessor_rewritten": False,
        "gate_identity": gate["gate_identity"],
        "national_forecast_consumption_proven": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if fail + reconstructed_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
