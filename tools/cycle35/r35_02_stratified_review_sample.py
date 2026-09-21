"""R35-02: a review sample actually stratified across the declared dimensions.

The pack requires manual semantic review stratified across FBS/FCS,
platforms, qualifiers and historic/current. The first sample stratified only
on (platform, era, disposition) and produced 7 rows -- too thin, and blind
to subdivision and title qualifier, which are exactly where a role-admission
parser is most likely to be wrong.

This re-derives strata from the rebuild rows plus the canonical population
(which supplies FBS/FCS) and draws a deterministic sample across the full
cross-product that actually occurs. It also reports which declared dimension
CANNOT be stratified from this dataset and why, rather than quietly
producing a sample that looks complete.

Nothing here labels a row correct. Parser output cannot grade its own gold
sample; every row is emitted PENDING_HUMAN_ADJUDICATION.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUTS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
MEMBERSHIP = (
    OUTPUTS / "CURRENT_2026_PROGRAMS.jsonl",
    OUTPUTS / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl",
    OUTPUTS / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl",
)

PER_STRATUM = 2


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def subdivision_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for path in MEMBERSHIP:
        for row in read_jsonl(path):
            pid = str(row.get("program_id") or "")
            classification = str(row.get("classification") or "").lower()
            if pid and classification in {"fbs", "fcs"}:
                index.setdefault(pid, classification)
    return index


def qualifier_bucket(qualifier: str) -> str:
    """Collapse 19 raw qualifier combinations into review-relevant buckets.

    A per-combination stratum would produce a sample larger than the review
    it is meant to make feasible, so qualifiers are bucketed by the property
    that actually changes admission: whether the title carries a modifier
    that must NOT be elevated to a principal role.
    """

    text = (qualifier or "").casefold()
    if text in {"", "none"}:
        return "NO_QUALIFIER"
    # Token-boundary matching, not substring. `"co" in text` is True for
    # "coordinator", "coach" and "quality control", which collapsed 614 of
    # 880 rows into the shared/interim bucket and destroyed the
    # stratification this sample exists to provide. Same class of error as
    # the substring-name bug repaired in R35-02, found in my own bucketing.
    tokens = {token for token in re.split(r"[^a-z0-9]+", text) if token}
    if tokens & {"co", "interim", "acting"}:
        return "SHARED_OR_INTERIM"
    if tokens & {"assistant", "associate", "deputy"}:
        return "SUBORDINATE_MODIFIER"
    if "coordinator" in tokens:
        return "COORDINATOR"
    if "head" in tokens:
        return "HEAD"
    return "OTHER_MODIFIER"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)

    rows = read_jsonl(Path(args.rows))
    subdivisions = subdivision_index()

    enriched: list[dict[str, Any]] = []
    for row in rows:
        strata = row.get("strata") or {}
        enriched.append(
            {
                **row,
                "subdivision": subdivisions.get(
                    str(row.get("program_id") or ""), "UNRESOLVED_SUBDIVISION"
                ),
                "qualifier_bucket": qualifier_bucket(strata.get("qualifier", "")),
            }
        )

    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in enriched:
        strata = row.get("strata") or {}
        buckets[
            (
                row["subdivision"],
                str(strata.get("platform")),
                row["qualifier_bucket"],
                str(row.get("disposition")),
            )
        ].append(row)

    sample: list[dict[str, Any]] = []
    for key in sorted(buckets):
        chosen = sorted(buckets[key], key=lambda r: str(r.get("episode_key")))
        for row in chosen[:PER_STRATUM]:
            sample.append(
                {
                    "stratum": {
                        "subdivision": key[0],
                        "platform": key[1],
                        "qualifier_bucket": key[2],
                        "disposition": key[3],
                    },
                    "stratum_population": len(buckets[key]),
                    "episode_key": row.get("episode_key"),
                    "person": row.get("person"),
                    "source_title": row.get("source_title"),
                    "program_id": row.get("program_id"),
                    "recorded_role_claim_supported": row.get(
                        "recorded_role_claim_supported"
                    ),
                    "rebuilt_role_claim_supported": row.get(
                        "rebuilt_role_claim_supported"
                    ),
                    "rebuilt_record_person": row.get("rebuilt_record_person"),
                    "rebuilt_record_title": row.get("rebuilt_record_title"),
                    "raw_path": row.get("raw_path"),
                    "manual_semantic_review": "PENDING_HUMAN_ADJUDICATION",
                }
            )

    dimension_counts = {
        "subdivision": dict(Counter(r["subdivision"] for r in enriched)),
        "platform": dict(
            Counter(str((r.get("strata") or {}).get("platform")) for r in enriched)
        ),
        "qualifier_bucket": dict(Counter(r["qualifier_bucket"] for r in enriched)),
        "era": dict(
            Counter(str((r.get("strata") or {}).get("era")) for r in enriched)
        ),
        "disposition": dict(Counter(str(r.get("disposition")) for r in enriched)),
    }

    result = {
        "artifact_type": "CYCLE35_R35_02_STRATIFIED_MANUAL_REVIEW_SAMPLE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_rows": str(Path(args.rows)),
        "population_rows": len(enriched),
        "strata_dimensions": [
            "subdivision (FBS/FCS)",
            "platform",
            "qualifier_bucket",
            "disposition",
        ],
        "distinct_strata": len(buckets),
        "sample_rows": len(sample),
        "per_stratum_cap": PER_STRATUM,
        "dimension_counts": dimension_counts,
        "dimensions_not_stratifiable": [
            {
                "dimension": "historic/current",
                "reason": (
                    "Every one of these 880 episode references comes from a "
                    "current-season official staff capture, so the dataset "
                    "contains exactly one era value. Historic staff rows exist "
                    "in the user research corpus, which is registered but not "
                    "cell-ingested this cycle, so a historic stratum cannot be "
                    "drawn from this population. Reported rather than faked."
                ),
            }
        ],
        "sample": sample,
        "parser_does_not_grade_its_own_sample": True,
        "note": (
            "Every row requires human semantic adjudication. A stratum with a "
            "large population and a two-row sample is a sampling decision, "
            "not a completeness claim."
        ),
    }
    (out_dir / "R35_02_STRATIFIED_REVIEW_SAMPLE.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "population_rows": len(enriched),
            "distinct_strata": len(buckets),
            "sample_rows": len(sample),
            "subdivision": dimension_counts["subdivision"],
            "qualifier_bucket": dimension_counts["qualifier_bucket"],
            "platform": dimension_counts["platform"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
