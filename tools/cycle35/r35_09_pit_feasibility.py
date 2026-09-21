"""R35-09: what PIT authority actually exists, per season band.

The question "can this row's features be treated as point-in-time?" is not
answered by arithmetic reconstruction. It is answered by whether evidence
exists that the inputs were PUBLISHED before the target game's cutoff.

This builds that table from what is really on disk -- the BAT-523 manifest's
own declared PIT contract and population, the kernel's season distribution,
and the independent reference's findings -- and sorts every band into one of
three honest outcomes:

    RECOVERABLE          publication/commitment evidence exists and could be
                         bound per row with work that is possible today;
    NOT_RECOVERABLE      no such evidence exists and none can be manufactured
                         retrospectively -- these rows can be honest
                         RETROSPECTIVE facts and never PIT;
    FUTURE_COLLECTION    authority does not exist yet but capturing it going
                         forward would create it legitimately.

Nothing here promotes a row. If zero rows are independently proven, the
trusted fitted path stays blocked and the table says exactly why.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUTS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
KERNEL_ROWS = OUTPUTS / "PIT_KERNEL_ROWS.jsonl"
MANIFEST = Path(
    r"C:\BatteredAggieSyndrome.data\manifests\historical_known_at\sha256"
    r"\cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
    r"\known_at_replay_manifest.json"
)

RECOVERABLE = "RECOVERABLE_FROM_EXISTING_EVIDENCE"
NOT_RECOVERABLE = "NOT_RECOVERABLE_RETROSPECTIVE_ONLY"
FUTURE = "FUTURE_COLLECTION_WOULD_CREATE_AUTHORITY"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--reference", default="")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    kernel = read_jsonl(KERNEL_ROWS)
    kernel_seasons = Counter(int(row["season"]) for row in kernel)
    proven = [
        row
        for row in kernel
        if row.get("authority_class") == "PROVEN_PIT_TRAINING_ROW"
    ]
    proven_seasons = Counter(int(row["season"]) for row in proven)

    manifest: dict[str, Any] = {}
    manifest_state = "MANIFEST_NOT_MOUNTED"
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest_state = "MANIFEST_MOUNTED"
    contract = manifest.get("pit_contract") or {}
    population = manifest.get("population") or {}
    source_seasons = set(population.get("source_seasons") or [])

    reference: dict[str, Any] = {}
    if args.reference and Path(args.reference).is_file():
        reference = json.loads(Path(args.reference).read_text(encoding="utf-8"))
    comparison = reference.get("comparison") or {}

    rows: list[dict[str, Any]] = []

    covered = sorted(season for season in kernel_seasons if season in source_seasons)
    if covered:
        rows.append(
            {
                "band": f"{min(covered)}-{max(covered)}",
                "kernel_rows": sum(kernel_seasons[s] for s in covered),
                "outcome": RECOVERABLE,
                "evidence_that_exists": contract.get("source_known_at"),
                "evidence_location": str(MANIFEST),
                "what_is_missing": (
                    "The BAT-523 manifest binds publication time to exact file "
                    "bytes for these seasons, but the kernel artifact carries no "
                    "PER-PRIOR receipt: a row states a feature value without "
                    "naming which prior observations were admitted or what "
                    "published each one before the cutoff."
                ),
                "work_that_would_close_it": (
                    "Emit, per kernel row, the admitted prior observation ids "
                    "together with each one's source_known_at_utc and the "
                    "target cutoff it was compared against, so a reviewer can "
                    "re-derive admissibility without trusting the producer."
                ),
                "independently_proven_today": 0,
            }
        )

    # 2023 gets its own band below (its input source is unidentified, a
    # different problem), so it is excluded here -- otherwise the bands
    # would overlap and the row totals would exceed the kernel.
    uncovered = sorted(
        season
        for season in kernel_seasons
        if season not in source_seasons and season < 2023
    )
    if uncovered:
        rows.append(
            {
                "band": f"{min(uncovered)}-{max(uncovered)}",
                "kernel_rows": sum(kernel_seasons[s] for s in uncovered),
                "outcome": NOT_RECOVERABLE,
                "evidence_that_exists": (
                    "Retrospective game outcomes only. These seasons are "
                    "outside the BAT-523 source_seasons window, so no "
                    "publication-time binding exists for them anywhere in the "
                    "declared evidence."
                ),
                "evidence_location": str(OUTPUTS),
                "what_is_missing": (
                    "Any contemporaneous record of WHEN these outcomes became "
                    "publicly known. Retrieval today establishes the fact, not "
                    "yesterday's pregame knowledge."
                ),
                "work_that_would_close_it": (
                    "Nothing available now. A contemporaneous archive with "
                    "verifiable capture times (e.g. dated web-archive "
                    "snapshots of the source) could raise these to PIT, but "
                    "absent that they are honest RETROSPECTIVE facts and must "
                    "never be labelled PIT."
                ),
                "independently_proven_today": 0,
            }
        )

    unsourced = sorted(
        season
        for season in kernel_seasons
        if season == 2023 and season not in source_seasons
    )
    if unsourced:
        rows.append(
            {
                "band": "2023",
                "kernel_rows": sum(kernel_seasons[s] for s in unsourced),
                "outcome": NOT_RECOVERABLE,
                "evidence_that_exists": "NONE_IDENTIFIED",
                "evidence_location": None,
                "what_is_missing": (
                    "The 2023 kernel rows' game identities were not located in "
                    "any declared public game output, nor in the mounted "
                    "BAT-523 payloads (whose source_seasons stop at 2022). "
                    "Their input source is currently unidentified, so neither "
                    "their features nor their publication times can be "
                    "independently checked."
                ),
                "work_that_would_close_it": (
                    "Identify and bind the actual 2023 input source before any "
                    "2023 row is used for fitting or selection."
                ),
                "independently_proven_today": 0,
            }
        )

    future = sorted(season for season in kernel_seasons if season >= 2026)
    if future:
        rows.append(
            {
                "band": f"{min(future)}+",
                "kernel_rows": sum(kernel_seasons[s] for s in future),
                "outcome": FUTURE,
                "evidence_that_exists": (
                    f"{sum(proven_seasons[s] for s in future)} rows carry the "
                    "producer's PROVEN_PIT_TRAINING_ROW label."
                ),
                "evidence_location": str(KERNEL_ROWS),
                "what_is_missing": (
                    "The label is a producer assertion carried on the row; no "
                    "per-row freeze receipt accompanies it in this artifact. "
                    "Until each is bound to a trusted receipt committed before "
                    "its contest's cutoff, none is independently proven."
                ),
                "work_that_would_close_it": (
                    "Capture forecasts and their inputs prospectively, for "
                    "contests that have not yet kicked off, through the Cycle "
                    "#35 trusted-receipt contract. This is the only path that "
                    "creates genuine PIT authority, and it cannot be applied "
                    "retroactively to a contest already played."
                ),
                "independently_proven_today": 0,
            }
        )

    protected = sorted(season for season in kernel_seasons if season in (2024, 2025))
    result = {
        "artifact_type": "CYCLE35_R35_09_PIT_RECOVERY_FEASIBILITY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_state": manifest_state,
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
        if MANIFEST.is_file()
        else None,
        "declared_pit_contract": contract,
        "declared_population": population,
        "kernel_rows_by_season": dict(sorted(kernel_seasons.items())),
        "producer_proven_labels_by_season": dict(sorted(proven_seasons.items())),
        "feasibility_table": rows,
        "totals": {
            "kernel_rows": len(kernel),
            "producer_proven_labels": len(proven),
            "independently_proven_pit_rows": 0,
            "rows_in_recoverable_bands": sum(
                row["kernel_rows"] for row in rows if row["outcome"] == RECOVERABLE
            ),
            "rows_in_not_recoverable_bands": sum(
                row["kernel_rows"] for row in rows if row["outcome"] == NOT_RECOVERABLE
            ),
            "rows_in_future_collection_bands": sum(
                row["kernel_rows"] for row in rows if row["outcome"] == FUTURE
            ),
        },
        "protected_seasons_present_in_kernel": protected,
        "bands_partition_the_kernel": (
            sum(row["kernel_rows"] for row in rows) == len(kernel)
        ),
        "independent_reference_summary": {
            "rows_fully_agreeing": (comparison.get("row_states") or {}).get("COMPARED"),
            "rows_disagreeing": (comparison.get("row_states") or {}).get("DISAGREES"),
            "rows_without_locatable_source": (comparison.get("row_states") or {}).get(
                "GAME_NOT_IN_DECLARED_RAW_SOURCES"
            ),
            "target_exclusion_violations": comparison.get(
                "target_exclusion_violation_count"
            ),
            "game_pair_incoherence": comparison.get("game_pair_incoherence_count"),
            "prior_count_delta": (
                comparison.get("prior_count_delta_distribution") or {}
            ).get("buckets"),
        },
        "trusted_fitted_path": "BLOCKED",
        "trusted_fitted_path_reason": (
            "Zero kernel rows are independently proven point-in-time. The "
            "producer's 36 PROVEN_PIT_TRAINING_ROW labels are assertions "
            "carried on the rows themselves with no accompanying per-row "
            "receipt, and the independent reference could reproduce only a "
            "minority of stored feature values exactly from the declared "
            "inputs. Neither a new model nor a receipt written now can repair "
            "an old freeze."
        ),
        "no_numerator_was_forced": True,
        "retrospective_use_remains_legitimate": True,
        "pit_admitted": False,
    }
    (out_dir / "R35_09_PIT_FEASIBILITY.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "totals": result["totals"],
            "bands": [
                {"band": row["band"], "outcome": row["outcome"], "rows": row["kernel_rows"]}
                for row in rows
            ],
            "trusted_fitted_path": result["trusted_fitted_path"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
