"""Independently reconstruct the corpus derivative-integrity successor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.data.tamu_corpus_derivative_integrity_successor import (  # noqa: E402
    GATE_RELATIVE,
    build_successor,
    recompute_child_counts,
    season_specific_versus_cumulative,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO))
    parser.add_argument("--data-root", default="")
    args = parser.parse_args()
    repo = Path(args.repo_root)
    data = Path(args.data_root) if args.data_root else None
    gate = json.loads((repo / GATE_RELATIVE).read_text(encoding="utf-8"))
    rebuilt = build_successor(repo_root=repo, data_root=data)
    fail = 0
    if rebuilt["child_counts"]["stale_domain_count"] != gate["census"]["child_counts"][
        "stale_domain_count"
    ]:
        fail += 1
    if rebuilt["placeholders"]["unresolved_count"] != gate["census"]["placeholders"][
        "unresolved_count"
    ]:
        fail += 1
    if rebuilt["predecessor"]["rewritten"]:
        fail += 1
    corpus_gate = json.loads(
        (
            repo
            / "artifacts/data_lake/tamu_official_1996_2009_structured_row_corpus_gate.json"
        ).read_text(encoding="utf-8")
    )
    independent = recompute_child_counts(corpus_gate)
    if independent["stale_domain_count"] != rebuilt["child_counts"]["stale_domain_count"]:
        fail += 1
    rejection_gate = json.loads(
        (
            repo
            / "artifacts/data_lake/tamu_official_gamebook_union_1998_rejection_complete_gate.json"
        ).read_text(encoding="utf-8")
    )
    independent_rej = season_specific_versus_cumulative(rejection_gate)
    if (
        independent_rej["season_specific_sum"]
        != rebuilt["rejections"]["season_specific_sum"]
    ):
        fail += 1
    print(
        json.dumps(
            {
                "result": "PASS" if fail == 0 else "FAIL",
                "independent_fail_count": fail,
                "gate_identity": gate.get("gate_identity"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
