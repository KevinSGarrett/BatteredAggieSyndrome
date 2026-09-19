"""Rebuild C33C-affected successors. Does not overwrite CYCLE33_STARTING_STACK."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from complete_cycle33_remaining import scoring_successor  # noqa: E402
from exhaust_cycle33_remaining import (  # noqa: E402
    career_joins,
    locatable_spans,
    starting_stack,
    week2,
)


def main() -> int:
    stack = starting_stack()
    print(
        "starting",
        stack.get("artifact_type"),
        stack.get("cycle33_head"),
        flush=True,
    )
    census = week2()
    print(
        "week2",
        census.get("observation_count"),
        census.get("unique_contest_ids"),
        flush=True,
    )
    career = career_joins()
    print("career", career.get("state_counts"), flush=True)
    spans = locatable_spans()
    print(
        "spans",
        spans.get("confirmed_episode_count"),
        spans.get("role_claim_supported_episodes"),
        spans.get("quarantined_or_partial_cells"),
        flush=True,
    )
    finals = scoring_successor()
    print(
        "finals",
        finals.get("observation_count"),
        finals.get("unique_contest_count"),
        finals.get("admitted_unique_games"),
        finals.get("quarantined_conflicts"),
        finals.get("nonfinal_contests"),
        finals.get("scored_unique_frozen_games"),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
