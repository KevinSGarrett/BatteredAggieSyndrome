"""R35-27 (Cycle #35 continuation, 20260921T055921Z), section 3.

"Reconcile every declared historical and current membership input, including
the current-program schema and effective season. Derive year membership from
its bound authority, not the current clock or a guessed default... If
membership itself is unproven, record that population uncertainty explicitly;
do not omit the year and present the narrower denominator as national
completion."

The delivered release declares expected coverage cells for 1963-2023 only,
against a pack scope of 1963-2026, while the same database holds 8,324 /
8,603 / 10,510 observations labelled 2024 / 2025 / 2026. The cause is not a
parsing bug: CURRENT_2026_PROGRAMS.jsonl carries no `season` field at all,
and the builder -- correctly, under the MF35-05 repair -- refuses to date a
row whose season the row itself does not state.

That repair removed a real fabrication: the builder used to assume the
CURRENT year for any seasonless row. This module does NOT undo it. It draws
a distinction the earlier repair collapsed:

    assuming 2026 because the wall clock says 2026        -- fabrication
    binding 2026 because the request that produced the    -- evidence
      file declared year=2026, and the file's contents
      prove it came from that request

The second is bound authority, so the binding must be PROVED, never
asserted. `prove_receipt_linkage` accepts a receipt only when that receipt's
cached payload contains every program in the file AND no other declared year
does. An ambiguous or absent linkage binds nothing.

A season inside the declared scope with no membership authority at all is
reported as declared population uncertainty, with the reason. It is never
silently dropped, and the narrower denominator is never presented as
national completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CYCLE30 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
OUTPUTS = CYCLE30 / "outputs"
RAW_TEAMS = CYCLE30 / "raw" / "teams"
ACQUISITION_LEDGER = OUTPUTS / "CYCLE30_ACQUISITION_LEDGER.json"

MEMBERSHIP_FILES = (
    OUTPUTS / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl",
    OUTPUTS / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl",
    OUTPUTS / "CURRENT_2026_PROGRAMS.jsonl",
)

#: The scope the pack declares. Seasons inside it with no membership
#: authority are reported as uncertainty, not omitted.
DECLARED_SCOPE = (1963, 2026)

AUTHORITY_PER_ROW = "PER_ROW_DECLARED_SEASON"
AUTHORITY_RECEIPT = "DECLARED_ACQUISITION_RECEIPT_YEAR"
AUTHORITY_NONE = "UNBOUND_NO_SEASON_AUTHORITY"

LINKAGE_PROVED = "PROVED_BY_CONTENT_AGAINST_A_SINGLE_DECLARED_YEAR"
LINKAGE_AMBIGUOUS = "REFUSED_MORE_THAN_ONE_DECLARED_YEAR_COVERS_THE_FILE"
LINKAGE_ABSENT = "REFUSED_NO_DECLARED_YEAR_COVERS_THE_FILE"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def team_ids(payload: Any) -> set[str]:
    if isinstance(payload, dict):
        payload = payload.get("data") or payload.get("teams") or []
    if not isinstance(payload, list):
        return set()
    return {str(row.get("id")) for row in payload if isinstance(row, dict)}


def cached_team_payloads(
    ledger_path: Path = ACQUISITION_LEDGER, raw_dir: Path = RAW_TEAMS
) -> dict[int, dict[str, Any]]:
    """Every declared /teams year bound to its cached payload by content hash.

    The ledger records a raw_sha256 per attempt but the cache filenames do
    not match it, so the binding is made by hashing each cached file rather
    than by trusting a filename.
    """

    if not ledger_path.is_file():
        return {}
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    by_digest: dict[str, set[int]] = {}
    receipts: dict[str, dict[str, Any]] = {}
    for attempt in ledger.get("attempts") or []:
        if attempt.get("route") != "/teams":
            continue
        year = (attempt.get("parameters") or {}).get("year")
        if year is None:
            continue
        digest = str(attempt.get("raw_sha256"))
        by_digest.setdefault(digest, set()).add(int(year))
        receipts[digest] = attempt

    found: dict[int, dict[str, Any]] = {}
    for path in sorted(raw_dir.glob("*.json")):
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        digest = hashlib.sha256(raw).hexdigest()
        if digest not in by_digest:
            continue
        try:
            ids = team_ids(json.loads(raw.decode("utf-8")))
        except (UnicodeDecodeError, ValueError):
            continue
        for year in by_digest[digest]:
            found[year] = {
                "year": year,
                "receipt_sha256": digest,
                "cached_payload": str(path),
                "payload_rows": len(ids),
                "program_ids": ids,
                "retrieved_at_utc": receipts[digest].get("retrieved_at_utc"),
                "status": receipts[digest].get("status"),
            }
    return found


def prove_receipt_linkage(
    program_ids: set[str], payloads: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    """Which declared year's payload demonstrably produced this file.

    Accepts only when exactly one declared year covers every program in the
    file. Two covering years would make the season ambiguous and none would
    make it unknown; either way nothing is bound, because a season that
    cannot be proved must not be written.
    """

    coverage = []
    for year in sorted(payloads):
        entry = payloads[year]
        covered = len(program_ids & entry["program_ids"])
        coverage.append(
            {
                "year": year,
                "receipt_sha256": entry["receipt_sha256"],
                "payload_rows": entry["payload_rows"],
                "covers": covered,
                "of": len(program_ids),
                "covers_all": covered == len(program_ids) and bool(program_ids),
            }
        )
    covering = [row for row in coverage if row["covers_all"]]
    if len(covering) == 1:
        state = LINKAGE_PROVED
    elif covering:
        state = LINKAGE_AMBIGUOUS
    else:
        state = LINKAGE_ABSENT
    return {
        "state": state,
        "bound_year": covering[0]["year"] if len(covering) == 1 else None,
        "bound_receipt_sha256": covering[0]["receipt_sha256"] if len(covering) == 1 else None,
        "coverage_by_declared_year": coverage,
        "why": (
            "Exactly one declared /teams year's cached payload contains every "
            "program in this file, so that request is what produced it and its "
            "declared year parameter is the file's season."
            if state == LINKAGE_PROVED
            else "No season is bound: the linkage is not uniquely proved, and a "
            "season that cannot be proved must not be written."
        ),
    }


def resolve_membership_file(
    path: Path, payloads: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    rows = read_jsonl(path)
    with_season = [r for r in rows if r.get("season") not in (None, "", 0)]
    record: dict[str, Any] = {
        "path": str(path),
        "sha256": sha256_file(path),
        "rows": len(rows),
        "rows_with_a_per_row_season": len(with_season),
    }

    if with_season and len(with_season) == len(rows):
        seasons = sorted({int(r["season"]) for r in with_season})
        record.update(
            authority=AUTHORITY_PER_ROW,
            seasons=seasons,
            season_span=[seasons[0], seasons[-1]] if seasons else None,
            detail="Every row states its own season; nothing is inferred.",
        )
        return record

    if with_season:
        record.update(
            authority=AUTHORITY_NONE,
            seasons=[],
            detail="Only some rows state a season. This file is not bound as a "
            "whole, and no row is dated from its neighbours.",
        )
        return record

    program_ids = {
        str(r.get("program_id") or "").split(":")[-1]
        for r in rows
        if r.get("program_id")
    }
    linkage = prove_receipt_linkage(program_ids, payloads)
    if linkage["state"] == LINKAGE_PROVED:
        record.update(
            authority=AUTHORITY_RECEIPT,
            seasons=[int(linkage["bound_year"])],
            season_span=[int(linkage["bound_year"])] * 2,
            receipt_linkage=linkage,
            detail=(
                "No row states a season. The season comes from the declared "
                f"year parameter of the /teams request (year="
                f"{linkage['bound_year']}, receipt "
                f"{str(linkage['bound_receipt_sha256'])[:16]}...) whose cached "
                "payload contains every program in this file. This is the "
                "request's declared authority, not the wall clock."
            ),
        )
        return record

    record.update(
        authority=AUTHORITY_NONE,
        seasons=[],
        receipt_linkage=linkage,
        detail="No row states a season and no declared request uniquely "
        "accounts for this file, so nothing is bound.",
    )
    return record


def build(
    membership_files: tuple[Path, ...] = MEMBERSHIP_FILES,
    scope: tuple[int, int] = DECLARED_SCOPE,
    ledger_path: Path = ACQUISITION_LEDGER,
    raw_dir: Path = RAW_TEAMS,
) -> dict[str, Any]:
    payloads = cached_team_payloads(ledger_path, raw_dir)
    files = [resolve_membership_file(path, payloads) for path in membership_files]

    bound_seasons: set[int] = set()
    for record in files:
        bound_seasons.update(int(season) for season in record.get("seasons") or [])

    low, high = scope
    declared = list(range(low, high + 1))
    unbound = [season for season in declared if season not in bound_seasons]

    uncertainty = []
    for season in unbound:
        has_receipt = season in payloads
        uncertainty.append(
            {
                "season": season,
                "reason": "DECLARED_YEAR_NOT_ACQUIRED"
                if not has_receipt
                else "ACQUIRED_BUT_NOT_MATERIALISED_INTO_A_MEMBERSHIP_FILE",
                "detail": (
                    "No /teams request was ever made for this season, so no "
                    "membership authority exists for it."
                    if not has_receipt
                    else "A /teams payload exists for this season but no "
                    "membership file is bound to it."
                ),
            }
        )

    return {
        "artifact_type": "CYCLE35_NATIONAL_POPULATION_AUTHORITY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "declared_scope": {"first_season": low, "last_season": high},
        "membership_files": files,
        "declared_years_acquired": sorted(payloads),
        "seasons_with_membership_authority": sorted(bound_seasons),
        "seasons_without_membership_authority": unbound,
        "population_uncertainty": uncertainty,
        "scope_is_fully_bound": not unbound,
        "coverage_denominator_is_not_national_completion": (
            "Seasons without membership authority are reported here rather "
            "than omitted. A denominator that silently spans only the bound "
            "seasons would present a narrower population as national "
            "completion."
        ),
        "season_is_never_taken_from_the_clock": (
            "A file with no per-row season is bound only when exactly one "
            "declared request's cached payload accounts for every program in "
            "it. The MF35-05 repair removed the assumption that a seasonless "
            "row belongs to the current year; nothing here restores it."
        ),
        "no_request_was_made": (
            "Every receipt read here was already cached. This module makes no "
            "network request and spends no budget."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="National population authority.")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    result = build()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / "CYCLE35_NATIONAL_POPULATION_AUTHORITY.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "declared_years_acquired": result["declared_years_acquired"],
                "seasons_with_membership_authority": (
                    f"{len(result['seasons_with_membership_authority'])} seasons"
                ),
                "seasons_without_membership_authority": result[
                    "seasons_without_membership_authority"
                ],
                "membership_authorities": {
                    Path(f["path"]).name: f["authority"] for f in result["membership_files"]
                },
                "scope_is_fully_bound": result["scope_is_fully_bound"],
                "artifact": str(out_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
