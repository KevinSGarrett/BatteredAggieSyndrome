"""Independently validate the first national point-in-time eligible feature slice.

The validator is read-only. When a data root is mounted it fully re-derives the slice from
the spine and proves the committed payload hash, the same-game exclusion and future-append
invariance hold on the real population rather than only on fixtures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.national_pit_eligible_slice import (  # noqa: E402
    ELIGIBLE,
    ELIGIBLE_NO_PRIOR,
    GATE_RELATIVE,
    PitSliceViolation,
    build_rows,
    load_authority,
    load_contract,
    payload_lines,
    read_json,
    validate_artifact,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_national_pit_eligible_slice import load_inputs  # noqa: E402

INVARIANCE_CUTOFF_SEASON = 2015


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    summary = validate_artifact(repo_root)
    gate = read_json(repo_root / GATE_RELATIVE)
    checks: list[dict[str, object]] = []

    data_root = args.data_root.resolve() if args.data_root else None
    if data_root is None or not data_root.exists():
        checks.append({"check": "FULL_REDERIVATION", "state": "SKIP_DATA_ROOT_ABSENT"})
        print(json.dumps({**summary, "checks": checks}, indent=2, sort_keys=True))
        return 0

    contract = load_contract(repo_root)
    policy = load_authority(repo_root)["conservative_bound_policy"]
    inputs = load_inputs(repo_root, data_root)
    rows = build_rows(
        inputs["observations"], inputs["outcomes"], inputs["starts"], contract, policy
    )

    digest = hashlib.sha256(payload_lines(rows)).hexdigest()
    if digest != gate["payload"]["sha256"]:
        raise PitSliceViolation("the committed payload hash does not reproduce from the spine")
    checks.append({"check": "PAYLOAD_REPRODUCES_FROM_SPINE", "state": "PASS"})

    by_key = {(row["canonical_team_id"], row["canonical_game_id"]): row for row in rows}
    outcome_keys = {
        (str(row["canonical_team_id"]), str(row["canonical_game_id"]))
        for row in inputs["outcomes"]
    }
    if not outcome_keys.issuperset(
        {key for key, row in by_key.items() if row["row_verdict"] == ELIGIBLE}
    ):
        raise PitSliceViolation("an eligible row has no outcome reference")
    checks.append({"check": "EVERY_ELIGIBLE_ROW_HAS_AN_OUTCOME_REFERENCE", "state": "PASS"})

    truncated_observations = [
        row for row in inputs["observations"] if int(row["season"]) <= INVARIANCE_CUTOFF_SEASON
    ]
    truncated_outcomes = [
        row for row in inputs["outcomes"] if int(row["season"]) <= INVARIANCE_CUTOFF_SEASON
    ]
    truncated = build_rows(
        truncated_observations, truncated_outcomes, inputs["starts"], contract, policy
    )
    truncated_by_key = {
        (row["canonical_team_id"], row["canonical_game_id"]): row for row in truncated
    }
    drifted = [
        key
        for key, row in truncated_by_key.items()
        if row["season"] <= INVARIANCE_CUTOFF_SEASON - 1 and by_key.get(key) != row
    ]
    if drifted:
        raise PitSliceViolation(
            f"{len(drifted)} rows changed when later seasons were appended, so the slice is not"
            " future-append invariant"
        )
    checks.append(
        {
            "check": "FUTURE_APPEND_INVARIANCE",
            "cutoff_season": INVARIANCE_CUTOFF_SEASON,
            "compared_rows": sum(
                1
                for row in truncated_by_key.values()
                if row["season"] <= INVARIANCE_CUTOFF_SEASON - 1
            ),
            "state": "PASS",
        }
    )

    eligible_rows = [
        row for row in rows if row["row_verdict"] in {ELIGIBLE, ELIGIBLE_NO_PRIOR}
    ]
    starts = inputs["starts"]
    if any(not starts.get(row["canonical_game_id"]) for row in eligible_rows):
        raise PitSliceViolation("an admitted row has no start evidence")
    checks.append({"check": "EVERY_ADMITTED_ROW_HAS_START_EVIDENCE", "state": "PASS"})

    print(json.dumps({**summary, "checks": checks}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
