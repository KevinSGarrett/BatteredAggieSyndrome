"""Review unnormalized scheme strings and unmapped titles. No forced tags."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCI = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
CLAIMS = SCI / "CYCLE33_SCHEME_TENURE_CLAIMS.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    unnorm: Counter[str] = Counter()
    contexts: dict[str, list[dict[str, Any]]] = {}
    for line in CLAIMS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("disposition") != "SOURCE_REPORTED_UNNORMALIZED":
            continue
        text = str(row.get("source_text") or "")
        unnorm[text] += 1
        bucket = contexts.setdefault(text, [])
        if len(bucket) < 3:
            bucket.append(
                {
                    "page_title": row.get("page_title"),
                    "season": row.get("season"),
                    "field": row.get("field"),
                }
            )
    taxonomy = json.loads(
        (SCI / "CYCLE33_OFFICIAL_STAFF_TAXONOMY.json").read_text(encoding="utf-8")
    )
    payload = {
        "artifact_type": "CYCLE33_SCHEME_UNNORMALIZED_REVIEW",
        "as_of_utc": utc_now(),
        "unnormalized_claim_count": sum(unnorm.values()),
        "distinct_source_texts": len(unnorm),
        "top_values": [
            {
                "source_text": text,
                "count": count,
                "sample_context": contexts.get(text, []),
                "forced_tag": False,
                "disposition": "RETAIN_UNSUPPORTED_OR_AMBIGUOUS",
            }
            for text, count in unnorm.most_common(80)
        ],
        "no_forced_taxonomy": True,
        "wikipedia_is_not_official": True,
        "unmapped_titles_from_taxonomy": taxonomy.get("unmapped_distinct_titles"),
        "unmapped_role_counts": taxonomy.get("unmapped_role_counts"),
        "pronoun_is_not_coaching_role": True,
        "unspecified_assistant_may_be_legitimate": True,
        "pit_admitted": False,
    }
    (SCI / "CYCLE33_SCHEME_UNNORMALIZED_REVIEW.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "distinct": payload["distinct_source_texts"],
                "claims": payload["unnormalized_claim_count"],
                "top5": payload["top_values"][:5],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
