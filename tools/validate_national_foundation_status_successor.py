"""Independently reconstruct SRC-002:GAME:312472199 structured-status restore."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.data.national_foundation_status_successor import (  # noqa: E402
    FALSE_QUARANTINE_GAME_ID,
    PREDECESSOR_NORMALIZED_RELATIVE,
    PREDECESSOR_NORMALIZED_SHA256,
    PREDECESSOR_QUARANTINE_RELATIVE,
    PREDECESSOR_QUARANTINE_SHA256,
    classify_status_successor,
    load_false_quarantine_source_row,
    outcome_result,
    restore_false_quarantine,
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
            repo / "artifacts/data_lake/national_foundation_status_successor_gate.json"
        ).read_text(encoding="utf-8")
    )
    fail = 0
    quarantine_digest = hashlib.sha256(
        (data / PREDECESSOR_QUARANTINE_RELATIVE).read_bytes()
    ).hexdigest()
    normalized_digest = hashlib.sha256(
        (data / PREDECESSOR_NORMALIZED_RELATIVE).read_bytes()
    ).hexdigest()
    if quarantine_digest != PREDECESSOR_QUARANTINE_SHA256:
        fail += 1
    if normalized_digest != PREDECESSOR_NORMALIZED_SHA256:
        fail += 1
    source_row, _capture = load_false_quarantine_source_row(
        data_root=data, repo_root=repo
    )
    classified = classify_status_successor(source_row)
    restored = restore_false_quarantine(source_row)
    if classified["disposition"] != "RESTORE_FALSE_SUBSTRING_QUARANTINE":
        fail += 1
    if classified["completed_flag"] is not True:
        fail += 1
    if restored["normalized_game"]["canonical_game_id"] != FALSE_QUARANTINE_GAME_ID:
        fail += 1
    home = int(restored["normalized_game"]["home_points"])
    away = int(restored["normalized_game"]["away_points"])
    if restored["outcome_label"]["outcome_result"] != outcome_result(home, away):
        fail += 1
    if restored["outcome_label"]["point_margin_home_minus_away"] != home - away:
        fail += 1
    game_path = data / gate["payloads"]["restored_normalized_game"]["relative_path"]
    saved = json.loads(game_path.read_text(encoding="utf-8").splitlines()[0])
    if saved["home_points"] != restored["normalized_game"]["home_points"]:
        fail += 1
    if saved["away_points"] != restored["normalized_game"]["away_points"]:
        fail += 1
    string_completed = dict(source_row)
    string_completed["completed"] = "false"
    if classify_status_successor(string_completed)["completed_flag"] is True:
        fail += 1
    result = {
        "result": "PASS" if fail == 0 else "FAIL",
        "independent_fail_count": fail,
        "gate_identity": gate["gate_identity"],
        "canonical_game_id": FALSE_QUARANTINE_GAME_ID,
        "home_points": home,
        "away_points": away,
        "outcome_result": restored["outcome_label"]["outcome_result"],
        "predecessor_rewritten": False,
        "pit_feature_eligible": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
