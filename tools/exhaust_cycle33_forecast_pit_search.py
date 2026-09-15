"""Search authorized archives for forecast packets and producer PIT labels.

Does not manufacture receipts, backfill forecasts, or convert retrieval
time into historical known-at. Distinguishes none-eligible-in-set from
global absence.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle33.forecast_inventory import (  # noqa: E402
    SEARCH_ROOTS,
    inventory_forecast_files,
)
from aggie_analytics.cycle33.pit_recompute import (  # noqa: E402
    producer_proven_without_receipt,
    recompute_pit_population,
)

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
KERNEL = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs\PIT_KERNEL_ROWS.jsonl"
)
RECEIPT_HINTS = ("receipt", "known_at", "publication", "freeze", "checkpoint")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def search_receipt_mentions(identities: list[str]) -> list[dict[str, Any]]:
    wanted = {item for item in identities if item}
    hits: list[dict[str, Any]] = []
    if not wanted:
        return hits
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
                continue
            name = path.name.casefold()
            if not any(hint in name for hint in RECEIPT_HINTS):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            matched = [item for item in wanted if item in text]
            if not matched:
                continue
            hits.append(
                {
                    "path": str(path),
                    "matched_identities": matched[:20],
                    "bytes": path.stat().st_size,
                    "searched_root": str(root),
                    "receipt_not_promoted": True,
                }
            )
            if len(hits) >= 200:
                return hits
    return hits


def blocked_consumers() -> list[dict[str, str]]:
    return [
        {
            "consumer": "cycle33.scoring_successor.score_unique_frozen_games",
            "enforced_state": "UNTRUSTED_SHADOW_OR_ABSTAIN",
        },
        {
            "consumer": "cycle33.pit_recompute.recompute_pit_population",
            "enforced_state": "independently_proven_count=0",
        },
        {
            "consumer": "cycle30.kernel_model.fold_local_fit",
            "enforced_state": "UNTRUSTED_SHADOW / scientific-trust hold",
        },
        {
            "consumer": "fitted model selection",
            "enforced_state": "RETAIN_PROTECTED_LANE_BLOCKED",
        },
    ]


def main() -> int:
    inventory = inventory_forecast_files()
    packets = []
    for row in inventory.get("files") or []:
        packets.append(
            {
                "artifact_path": row.get("path"),
                "searched_root": row.get("searched_root"),
                "bytes": row.get("bytes"),
                "eligibility_verdict": row.get("eligibility_verdict"),
                "failed_predicates": row.get("failed_predicates"),
                "eligibility_proof_present": row.get("eligibility_proof_present"),
                "top_level_keys": row.get("top_level_keys"),
                "freeze_token_present": row.get("freeze_token_present"),
            }
        )
    kernel_rows = load_jsonl(KERNEL)
    proven_labels = producer_proven_without_receipt(kernel_rows)
    recompute = recompute_pit_population(kernel_rows) if kernel_rows else {}
    identities = [
        str(row.get("canonical_game_id") or "")
        for row in proven_labels
        if row.get("canonical_game_id")
    ]
    receipt_hits = search_receipt_mentions(identities)
    payload = {
        "artifact_type": "CYCLE33_FORECAST_PIT_ARCHIVE_SEARCH",
        "as_of_utc": utc_now(),
        "forecast": {
            **{k: inventory.get(k) for k in (
                "file_count",
                "eligibility_proof_count",
                "missing_roots",
                "roots_searched",
                "inspected_set_scope",
                "none_eligible_in_inspected_set_is_not_global_absence",
            )},
            "packets": packets,
            "eligible_in_inspected_set": int(
                inventory.get("eligibility_proof_count") or 0
            ),
            "global_absence_not_claimed": True,
        },
        "producer_proven_pit_labels": {
            "kernel_path": str(KERNEL),
            "kernel_row_count": len(kernel_rows),
            "producer_proven_count": len(proven_labels),
            "independently_proven_count": recompute.get(
                "independently_proven_count"
            ),
            "rows": proven_labels,
            "receipt_archive_hits": receipt_hits,
            "receipts_found_with_required_predicates": False,
            "failed_predicate_reason_counts": recompute.get(
                "failed_predicate_reason_counts"
            ),
        },
        "blocked_consumers": blocked_consumers(),
        "no_receipts_manufactured": True,
        "retrieval_time_is_not_historical_known_at": True,
        "previous_scoring_not_overwritten": True,
        "pit_admitted": False,
        "hold": "SCIENTIFIC_OPERATOR_HOLD_ACTIVE",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "CYCLE33_FORECAST_PIT_ARCHIVE_SEARCH.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "forecast_packets": len(packets),
                "eligible": payload["forecast"]["eligible_in_inspected_set"],
                "producer_proven_labels": len(proven_labels),
                "independently_proven": recompute.get(
                    "independently_proven_count"
                ),
                "receipt_hits": len(receipt_hits),
                "roots_searched": inventory.get("roots_searched"),
                "missing_roots": inventory.get("missing_roots"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
