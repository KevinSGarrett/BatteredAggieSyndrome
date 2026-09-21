"""R35-17: reconstruct the cycle-wide append-only request ledger.

Cycle #35 closeout review (20260921T025300Z), section 6: "The final packet
resets both budgets to 0 used / 50 remaining, lists no component ledgers,
and records zero infrastructure requests. The earlier same-cycle ledger
records 7 coaching/history requests, 8 availability/context requests and
17 infrastructure readbacks, with component receipts. Those receipts were
not erased by creating a new output directory."

The defect is structural, not arithmetic: r35_15_acceptance_packet.py
globs `CYCLE35_REQUEST_LEDGER_*.json` out of its OWN `--out-dir`, so
pointing it at a fresh directory produced a ledger that reported zero
spend for the whole cycle. Spend is a property of the cycle, not of
whichever output directory the last process happened to write to.

This tool walks EVERY run directory under the cycle root, collects every
component ledger entry, deduplicates them by request identity across
directories, and reports lifetime cycle totals separately from any single
pass. It also binds the prior readback artifacts that the packet's
"no live readback was performed" statement contradicted.

Read-only: it makes no network request and never mutates a source ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

CYCLE_RUNS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")

#: Scientific budgets carry a ceiling; infrastructure readback is counted
#: separately so it can never consume a scientific allowance.
SCIENTIFIC_BUDGETS = ("coaching_history", "availability_context")
INFRASTRUCTURE_BUDGET = "infrastructure_readback"
DEFAULT_CEILING = 50

#: Directories that hold vendored third-party trees rather than cycle
#: evidence. Walking them finds site-packages copies of unrelated files.
SKIP_DIRECTORY_NAMES = frozenset(
    {"wheel_venv", "Lib", "site-packages", "Scripts", "__pycache__", ".git"}
)


def iter_component_ledgers(root: Path) -> Iterable[Path]:
    """Every component request ledger anywhere under the cycle root."""

    if not root.is_dir():
        return
    for path in sorted(root.rglob("CYCLE35_REQUEST_LEDGER_*.json")):
        if SKIP_DIRECTORY_NAMES.intersection(path.parts):
            continue
        yield path


def request_identity(entry: dict[str, Any]) -> str:
    """A stable identity for one request attempt.

    The same attempt recorded in two run directories must collapse to one
    row. Attempt number and page are part of the identity because a retry
    and a second page are genuinely separate requests that each spent
    budget -- deduplicating them away would under-count real spend.
    """

    payload = json.dumps(
        {
            "url": entry.get("url"),
            "at_utc": entry.get("at_utc"),
            "attempt": entry.get("attempt"),
            "page": entry.get("page"),
            "budget": entry.get("budget"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def collect(root: Path = CYCLE_RUNS) -> dict[str, Any]:
    """Collect and deduplicate every request entry in the cycle."""

    by_identity: dict[str, dict[str, Any]] = {}
    duplicate_hits: Counter = Counter()
    per_ledger: list[dict[str, Any]] = []

    for path in iter_component_ledgers(root):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            per_ledger.append({"path": str(path), "readable": False, "error": str(exc)})
            continue
        entries = payload.get("entries") or []
        new_here = 0
        for entry in entries:
            identity = request_identity(entry)
            if identity in by_identity:
                duplicate_hits[identity] += 1
                by_identity[identity]["seen_in"].append(str(path))
                continue
            new_here += 1
            by_identity[identity] = {
                "identity": identity,
                "entry": entry,
                "first_seen_in": str(path),
                "seen_in": [str(path)],
            }
        per_ledger.append(
            {
                "path": str(path),
                "readable": True,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "declared_entry_count": payload.get("entry_count"),
                "observed_entries": len(entries),
                "new_unique_entries": new_here,
                "declared_spent": payload.get("spent"),
                "declared_remaining": payload.get("remaining"),
            }
        )

    records = list(by_identity.values())
    spent: Counter = Counter()
    outcomes: Counter = Counter()
    retries = 0
    paginated = 0
    cache_hits = 0
    for record in records:
        entry = record["entry"]
        outcomes[str(entry.get("outcome"))] += 1
        if entry.get("spent_a_request"):
            spent[str(entry.get("budget"))] += 1
        else:
            cache_hits += 1
        if isinstance(entry.get("attempt"), int) and entry["attempt"] > 1:
            retries += 1
        if entry.get("page") not in (None, "", 1):
            paginated += 1

    budgets = {}
    for name in SCIENTIFIC_BUDGETS:
        used = spent.get(name, 0)
        budgets[name] = {
            "ceiling": DEFAULT_CEILING,
            "used_cycle_lifetime": used,
            "remaining": DEFAULT_CEILING - used,
        }

    return {
        "component_ledgers": per_ledger,
        "component_ledger_count": len([p for p in per_ledger if p.get("readable")]),
        "unique_request_entries": len(records),
        "duplicate_entries_collapsed": sum(duplicate_hits.values()),
        "budgets": budgets,
        "infrastructure_readback_requests": spent.get(INFRASTRUCTURE_BUDGET, 0),
        "cache_hits_no_request_spent": cache_hits,
        "retry_attempts_counted": retries,
        "paginated_requests_counted": paginated,
        "outcome_counts": dict(outcomes),
        "total_scientific_requests": sum(
            budgets[name]["used_cycle_lifetime"] for name in SCIENTIFIC_BUDGETS
        ),
    }


def bind_prior_readbacks(root: Path = CYCLE_RUNS) -> dict[str, Any]:
    """Locate the readback artifacts this cycle already produced.

    The final packet stated that no live Jira readback was performed this
    cycle. A readback artifact recording 11 issues already existed, so the
    correct question is freshness, not absence.
    """

    found: list[dict[str, Any]] = []
    patterns = ("*JIRA_LIVE_READBACK*.json", "*REMOTE_HEADS_REFRESHED*.json")
    for pattern in patterns:
        for path in sorted(root.rglob(pattern)):
            if SKIP_DIRECTORY_NAMES.intersection(path.parts):
                continue
            record: dict[str, Any] = {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                record["readable"] = False
                found.append(record)
                continue
            record["readable"] = True
            record["artifact_type"] = payload.get("artifact_type")
            record["generated_at_utc"] = payload.get("generated_at_utc")
            for key in ("issues", "heads", "remote_heads"):
                value = payload.get(key)
                if isinstance(value, list):
                    record[f"{key}_count"] = len(value)
            found.append(record)
    return {
        "artifacts": found,
        "artifact_count": len(found),
        "prior_readback_performed_this_cycle": bool(found),
        "note": (
            "A prior readback exists. Whether it is still current is a "
            "FRESHNESS question governed by an explicit change rule, not "
            "evidence that no readback was ever performed."
        ),
    }


def build(root: Path = CYCLE_RUNS, current_pass_dirs: tuple[str, ...] = ()) -> dict[str, Any]:
    collected = collect(root)
    readbacks = bind_prior_readbacks(root)
    current_pass = {
        "directories": list(current_pass_dirs),
        "note": (
            "Zero spend in the current pass is not zero spend for the "
            "cycle. The budgets above are cycle-lifetime figures."
        ),
    }
    return {
        "artifact_type": "CYCLE35_CYCLE_WIDE_REQUEST_LEDGER",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cycle_root": str(root),
        "run_directories_scanned": sorted(
            p.name for p in root.iterdir() if p.is_dir()
        )
        if root.is_dir()
        else [],
        **collected,
        "prior_readbacks": readbacks,
        "current_pass": current_pass,
        "paid_model_calls": 0,
        "paid_reviewer_calls": 0,
        "paid_provider_calls": 0,
        "paid_ai_review_labels_applied": 0,
        "external_workers_spawned": 0,
        "cache_first_is_not_cache_only": True,
        "budget_is_cycle_scoped_not_process_scoped": True,
        "missing_ledger_files_do_not_mean_zero_spend": True,
        "budget_exhaustion_relabelled_as_verified_data": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--cycle-root", default=str(CYCLE_RUNS))
    parser.add_argument(
        "--current-pass-dir",
        action="append",
        default=[],
        help="A run directory belonging to the CURRENT pass, so its zero or "
        "nonzero usage can be reported separately from cycle lifetime spend.",
    )
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = build(Path(args.cycle_root), tuple(args.current_pass_dir))
    (out_dir / "CYCLE35_CYCLE_WIDE_REQUEST_LEDGER.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "component_ledgers": result["component_ledger_count"],
                "unique_request_entries": result["unique_request_entries"],
                "duplicate_entries_collapsed": result["duplicate_entries_collapsed"],
                "budgets": result["budgets"],
                "infrastructure_readback_requests": result[
                    "infrastructure_readback_requests"
                ],
                "cache_hits_no_request_spent": result["cache_hits_no_request_spent"],
                "retry_attempts_counted": result["retry_attempts_counted"],
                "paginated_requests_counted": result["paginated_requests_counted"],
                "outcome_counts": result["outcome_counts"],
                "prior_readback_artifacts": result["prior_readbacks"]["artifact_count"],
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
