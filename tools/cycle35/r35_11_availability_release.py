"""R35-11: reparse the SEC capture and build the national opportunity set.

Cache-first and read-only. No network request is made by this script: the
SEC capture already on disk is reparsed, and the national report-opportunity
keys are selected from the declared 266-row policy inventory. Where evidence
is genuinely absent, the key stays in the denominator with its exact reason
instead of being dropped to make coverage look better.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle35.availability import (  # noqa: E402
    OUTCOME_BLOCKED,
    OUTCOME_EVIDENCE,
    OUTCOME_POLICY_NO_REPORT,
    OUTCOME_UNKNOWN_POLICY,
    ReportOpportunity,
    opportunity_coverage,
    parse_tabular_report,
    summarize,
)

SEC_CAPTURE = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle34\20260919T_R34_receipts"
    r"\r34_12_browser_capture\sec_official_availability_raw_20260920T054326Z.txt"
)
POLICY_INVENTORY = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs"
    r"\AVAILABILITY_POLICY_INVENTORY.jsonl"
)

#: The pack requires twelve predeclared national keys spanning multiple
#: reporting policies and conferences, including FCS. They are selected
#: deterministically (sorted by program id within each stratum) rather than
#: cherry-picked, so the selection cannot drift toward whichever programs
#: happened to yield evidence.
TARGET_KEY_COUNT = 12


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def select_opportunity_keys(rows: list[dict[str, Any]]) -> list[ReportOpportunity]:
    """Deterministic stratified selection across policy, division, conference."""

    strata: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        strata[(str(row.get("policy_status")), str(row.get("classification")))].append(
            row
        )
    selected: list[dict[str, Any]] = []
    # Round-robin across strata so no single policy/division dominates.
    ordered_strata = sorted(strata)
    index = 0
    while len(selected) < TARGET_KEY_COUNT and any(strata.values()):
        stratum = ordered_strata[index % len(ordered_strata)]
        bucket = strata[stratum]
        if bucket:
            bucket.sort(key=lambda item: str(item.get("program_id")))
            selected.append(bucket.pop(0))
        index += 1
        if index > 10_000:
            break

    keys: list[ReportOpportunity] = []
    for row in selected:
        policy = str(row.get("policy_status"))
        disposition = str(row.get("disposition"))
        if policy == "UNKNOWN_POLICY":
            outcome = OUTCOME_UNKNOWN_POLICY
            detail = (
                "The program's availability-reporting policy is not "
                "established, so neither the presence nor the absence of a "
                "report can be interpreted."
            )
        elif policy == "FCS_VARIES_BY_PROGRAM":
            outcome = OUTCOME_POLICY_NO_REPORT
            detail = (
                "FCS reporting varies by program and no conference-wide "
                "report exists. Absence of a report means UNKNOWN, never "
                "that every player is healthy."
            )
        elif disposition == "ATTEMPTED_WITH_EVIDENCE":
            outcome = OUTCOME_EVIDENCE
            detail = "A public reporting policy exists and evidence was acquired."
        else:
            outcome = OUTCOME_BLOCKED
            detail = (
                "A public reporting policy exists but no route was completed "
                "in the cache-first budget for this cycle."
            )
        keys.append(
            ReportOpportunity(
                program_id=str(row.get("program_id")),
                display_name=str(row.get("display_name")),
                classification=str(row.get("classification")),
                conference=str(row.get("conference")),
                policy_status=policy,
                outcome=outcome,
                detail=detail,
            )
        )
    return keys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not SEC_CAPTURE.is_file():
        raise SystemExit("SEC capture not present: " + str(SEC_CAPTURE))
    raw = SEC_CAPTURE.read_bytes()
    parsed = parse_tabular_report(
        raw.decode("utf-8", errors="replace"),
        source_sha256=hashlib.sha256(raw).hexdigest(),
        retrieval_utc="2026-09-20T05:43:26+00:00",
    )
    stats = summarize(parsed["assertions"])

    policy_rows = read_jsonl(POLICY_INVENTORY)
    keys = select_opportunity_keys(policy_rows)
    coverage = opportunity_coverage(keys)

    programs = Counter(row["program"] for row in parsed["assertions"])
    result = {
        "artifact_type": "CYCLE35_R35_11_AVAILABILITY_RELEASE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_requests_made": 0,
        "cache_first": True,
        "sec_capture": {
            "path": str(SEC_CAPTURE),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "player_rows": parsed["player_rows"],
            "stage_columns": parsed["stage_columns"],
            "assertion_count": parsed["assertion_count"],
            "expected_assertion_count": parsed["expected_assertion_count"],
            "conservation_holds": parsed["conservation_holds"],
            "malformed_rows": parsed["malformed_rows"],
            "distinct_programs": len(programs),
            "publication_time_established": parsed["publication_time_established"],
            "publication_time_reason": parsed["publication_time_reason"],
        },
        "status_distribution": stats,
        "national_report_opportunities": coverage,
        "policy_inventory": {
            "path": str(POLICY_INVENTORY),
            "rows": len(policy_rows),
            "sha256": hashlib.sha256(POLICY_INVENTORY.read_bytes()).hexdigest()
            if POLICY_INVENTORY.is_file()
            else None,
        },
        "canonical_identity_state": {
            "resolved_player_ids": 0,
            "reason": (
                "Canonical player identity requires official roster ids. Name "
                "and jersey agreement alone is insufficient when ambiguous, "
                "so every assertion is retained at "
                "UNRESOLVED_NAME_AND_JERSEY_ONLY rather than being joined on "
                "a name match."
            ),
        },
        "unmet_requirements": [
            "Durable official raw/rendered evidence is not bound for the SEC "
            "capture: the file is a rendered table with no per-report "
            "publication timestamp and no archived original response.",
            "Canonical player-program-game resolution against official roster "
            "identities is not performed; identities stay unresolved.",
            "Of the 12 predeclared keys, only those marked "
            + OUTCOME_EVIDENCE
            + " carry acquired evidence; the rest are retained with their "
            "exact reason and remain unmet.",
        ],
        "semantics": {
            "no_report_means": "UNKNOWN",
            "unlisted_player_means": "UNKNOWN",
            "dash_stage_means": "PUBLISHED_EMPTY_NOT_AVAILABLE",
            "out_means_injured": False,
            "page_byline_dates_each_embedded_report": False,
        },
        "pit_admitted": False,
    }
    (out_dir / "R35_11_AVAILABILITY_RELEASE.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    rows_path = out_dir / "R35_11_AVAILABILITY_ASSERTIONS.jsonl"
    with rows_path.open("w", encoding="utf-8") as handle:
        for row in parsed["assertions"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    print(json.dumps(
        {
            "player_rows": parsed["player_rows"],
            "stage_columns": parsed["stage_columns"],
            "assertions": parsed["assertion_count"],
            "conservation_holds": parsed["conservation_holds"],
            "distinct_programs": len(programs),
            "by_status": stats["by_status"],
            "by_presence": stats["by_presence"],
            "unrecognized_vocabulary": stats["unrecognized_vocabulary"],
            "opportunity_keys": coverage["key_count"],
            "opportunity_outcomes": coverage["by_outcome"],
            "opportunity_classifications": coverage["by_classification"],
            "distinct_conferences": len(coverage["distinct_conferences"]),
            "distinct_policies": coverage["distinct_policies"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
