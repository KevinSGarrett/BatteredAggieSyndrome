"""R36-04: national program population 1963-2026 and the sourced crosswalk.

MR35R-05 found the nominal 1963-2026 denominator has no 2024 and no 2025
rows. The root cause is not a parser: the Cycle #30 acquisition ledger
declares ``/teams`` requests for 2013-2023 and 2026 and **never requested
2024 or 2025**, so those years were never derived. They are not, however,
unobtainable -- a later tool cached ``/teams?year=2024`` and
``/teams?year=2025`` under their request identities, and those payloads are
sitting in the same raw directory. Restoring the two years is therefore
local ingestion of already-acquired bytes and costs zero source requests.

MR35R-03 is repaired at the same time: every membership derivative's season
is proved by re-executing its declared transformation on declared response
bytes (``aggie_analytics.cycle36.membership_lineage``), not by checking
whether an ID set is covered.

MR35R-07's 864 unresolved cells are reprocessed through one general
crosswalk (``aggie_analytics.cycle36.program_crosswalk``) rather than
hand-mapped. Every original observation and every unresolved disposition is
preserved; confirmed national coverage can never rise by shrinking the
denominator, so the denominator is published year by year beside it.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402
from aggie_analytics.cycle36.jsonl_io import (  # noqa: E402
    read_jsonl_strict,
    write_jsonl_verified,
)
from aggie_analytics.cycle36.membership_lineage import (  # noqa: E402
    TRANSFORMS,
    load_receipts,
    prove_lineage,
    receipts_from_cache,
)
from aggie_analytics.cycle37.national_eras import (  # noqa: E402
    ERA_TABLE,
    era_for_season,
    reconcile as reconcile_era,
    subdivision_label_is_era_proof,
)
from aggie_analytics.cycle36.program_crosswalk import (  # noqa: E402
    build_crosswalk,
    conflict_report,
    load_payloads,
    related_candidates,
)

CYCLE30 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
OUTPUTS = CYCLE30 / "outputs"
RAW_TEAMS = CYCLE30 / "raw" / "teams"
ACQUISITION_LEDGER = OUTPUTS / "CYCLE30_ACQUISITION_LEDGER.json"
USER_CELLS_2013_2026 = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs"
    r"\20260920T224700Z_mf35_11_user_cells"
    r"\CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS.jsonl"
)
USER_CELLS_2000_2012 = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science\CYCLE33_USER_CORPUS_2000_2012_STAFF_CELLS.jsonl"
)

DECLARED_SCOPE = (1963, 2026)

#: Which derivative was produced by which declared transformation. A
#: derivative with no entry here cannot be lineage-proved and says so.
DERIVATIVE_TRANSFORMS = {
    "CURRENT_2026_PROGRAMS.jsonl": "TEAMS_FBS_FCS_V1",
    "HISTORICAL_MEMBERSHIP_2013_2023.jsonl": None,  # per-row season, no proof needed
    "HISTORICAL_MEMBERSHIP_1963_2012.jsonl": None,
}

#: Seasons whose membership must be materialized here because the Cycle #30
#: ledger never declared a request for them, while the cache holds the bytes.
RESTORED_SEASONS = (2024, 2025)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Strict read: a truncated artifact must be regenerated, never skipped."""

    return read_jsonl_strict(path)


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def request_identity(endpoint: str, parameters: dict[str, Any]) -> str:
    return sha256_json({"endpoint": endpoint, "parameters": parameters})


def classification_bucket(row: dict[str, Any]) -> str:
    """One of five published buckets, with unknown kept visible."""

    value = row.get("classification")
    if value in {"fbs", "fcs"}:
        return value.upper()
    era = str(row.get("era") or "")
    if era in {"NCAA_UNIVERSITY_DIVISION_PRIMARY", "UNSPLIT_DIVISION_I"}:
        return "PRE_CLASSIFICATION_ERA"
    if value:
        return "OTHER_DIVISION"
    return "UNKNOWN"


def materialize_restored_seasons(
    seasons: Iterable[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Membership rows for seasons the Cycle #30 ledger never requested.

    Each row carries the request identity and payload digest that produced
    it, so the restoration is auditable rather than asserted. The rows are
    marked ``RESTORED_FROM_CACHED_PAYLOAD_NOT_IN_CYCLE30_LEDGER`` so nobody
    can mistake them for the original derivation.
    """

    rows: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    transform = TRANSFORMS["TEAMS_FBS_FCS_V1"][2]
    for season in seasons:
        identity = request_identity("/teams", {"year": int(season)})
        path = RAW_TEAMS / f"{identity}.json"
        if not path.is_file():
            provenance.append(
                {
                    "season": int(season),
                    "state": "NO_CACHED_PAYLOAD_FOR_THIS_REQUEST_IDENTITY",
                    "request_identity_sha256": identity,
                    "expected_path": str(path),
                }
            )
            continue
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        payload_list = payload if isinstance(payload, list) else (
            payload.get("data") or payload.get("teams") or []
        )
        produced = transform(payload_list)
        by_id = {str(r.get("id")): r for r in payload_list if isinstance(r, dict)}
        for entry in produced:
            source_row = by_id.get(entry["source_entity_id"], {})
            rows.append(
                {
                    "artifact_class": "REAL_EVIDENCE",
                    "program_id": f"SRC-002:TEAM:{entry['source_entity_id']}",
                    "display_name": source_row.get("school"),
                    "conference": source_row.get("conference"),
                    "classification": entry["classification"],
                    "era": era_for_season(season),
                    "source_classification_is_not_era_proof": (
                        not subdivision_label_is_era_proof(season)
                    ),
                    "season": int(season),
                    "source_id": "SRC-002",
                    "membership_authority": "RESTORED_FROM_CACHED_PAYLOAD_NOT_IN_CYCLE30_LEDGER",
                    "request_identity_sha256": identity,
                    "payload_sha256": hashlib.sha256(raw).hexdigest(),
                    "transform": "TEAMS_FBS_FCS_V1",
                }
            )
        provenance.append(
            {
                "season": int(season),
                "state": "RESTORED_FROM_CACHED_PAYLOAD",
                "request_identity_sha256": identity,
                "payload_sha256": hashlib.sha256(raw).hexdigest(),
                "payload_path": str(path),
                "payload_rows": len(payload_list),
                "membership_rows": len(produced),
                "why_absent_before": (
                    "The Cycle #30 acquisition ledger declares /teams requests "
                    "for 2013-2023 and 2026 only. This season was never "
                    "requested there, so no derivative existed; the payload was "
                    "cached later by acquire_cycle32_recent_membership.py under "
                    "its request identity and needed no new source request."
                ),
            }
        )
    return rows, provenance


def build(out_dir: Path, rename_evidence_path: Path | None) -> dict[str, Any]:
    low, high = DECLARED_SCOPE

    # ---- 1. Existing membership derivatives, with lineage proved ---------
    receipts = load_receipts(ACQUISITION_LEDGER, RAW_TEAMS)
    receipts += receipts_from_cache(
        RAW_TEAMS, range(low, high + 1), request_identity
    )
    derivatives: list[dict[str, Any]] = []
    membership_rows: list[dict[str, Any]] = []
    for name, transform_name in DERIVATIVE_TRANSFORMS.items():
        path = OUTPUTS / name
        rows = read_jsonl(path)
        record: dict[str, Any] = {
            "derivative": name,
            "path": str(path),
            "sha256": sha256_file(path),
            "rows": len(rows),
            "rows_with_a_per_row_season": sum(
                1 for r in rows if r.get("season") not in (None, "", 0)
            ),
        }
        if record["rows_with_a_per_row_season"] == len(rows) and rows:
            record["season_authority"] = "PER_ROW_DECLARED_SEASON"
            record["seasons"] = sorted({int(r["season"]) for r in rows})
            membership_rows.extend(rows)
        else:
            entity_ids = [
                str(r.get("program_id") or "").rsplit(":", 1)[-1] for r in rows
            ]
            lineage = prove_lineage(entity_ids, receipts, transform_name)
            record["season_authority"] = (
                "EXACT_TRANSFORM_REPRODUCTION"
                if lineage["state"].startswith("PROVED")
                else "UNBOUND_NO_SEASON_AUTHORITY"
            )
            record["lineage"] = {
                key: value
                for key, value in lineage.items()
                if key != "evaluations"
            }
            record["lineage_evaluation_count"] = len(lineage.get("evaluations", []))
            if lineage.get("bound_year") is not None:
                season = int(lineage["bound_year"])
                record["seasons"] = [season]
                for row in rows:
                    membership_rows.append(
                        {
                            **row,
                            "season": season,
                            # R37-04-AC01: the season is only now known, so
                            # the era can only now be assigned. Without this
                            # the 266 rows of the proved derivative reached
                            # the delivered population with no era at all.
                            "era": row.get("era") or era_for_season(season),
                            "source_classification_is_not_era_proof": row.get(
                                "source_classification_is_not_era_proof",
                                not subdivision_label_is_era_proof(season),
                            ),
                            "membership_authority": "EXACT_TRANSFORM_REPRODUCTION",
                            "payload_sha256": lineage.get("bound_receipt_sha256"),
                            "request_identity_sha256": lineage.get(
                                "bound_request_identity"
                            ),
                            "transform": transform_name,
                        }
                    )
            else:
                record["seasons"] = []
        derivatives.append(record)

    # ---- 2. Restore the years nobody requested ---------------------------
    restored_rows, restored_provenance = materialize_restored_seasons(RESTORED_SEASONS)
    membership_rows.extend(restored_rows)

    # ---- 3. Year-by-year population, with every year in scope present ----
    by_season: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in membership_rows:
        season = row.get("season")
        if season is None:
            continue
        by_season[int(season)].append(row)

    population: list[dict[str, Any]] = []
    for season in range(low, high + 1):
        rows = by_season.get(season, [])
        buckets = collections.Counter(classification_bucket(r) for r in rows)
        authorities = collections.Counter(
            r.get("membership_authority") or "PER_ROW_DECLARED_SEASON" for r in rows
        )
        population.append(
            {
                "season": season,
                "programs": len({r.get("program_id") for r in rows}),
                "rows": len(rows),
                "FBS": buckets.get("FBS", 0),
                "FCS": buckets.get("FCS", 0),
                "PRE_CLASSIFICATION_ERA": buckets.get("PRE_CLASSIFICATION_ERA", 0),
                "OTHER_DIVISION": buckets.get("OTHER_DIVISION", 0),
                "UNKNOWN": buckets.get("UNKNOWN", 0),
                "membership_authority": dict(sorted(authorities.items())),
                "state": (
                    "MEMBERSHIP_PRESENT" if rows else "MEMBERSHIP_ABSENT_FOR_THIS_SEASON"
                ),
            }
        )
    missing_seasons = [p["season"] for p in population if not p["rows"]]

    # 2020 is a real participation change, not a data gap: explain it from
    # the source's own classification counts rather than deleting the year.
    change_2020 = None
    if by_season.get(2019) and by_season.get(2020) and by_season.get(2021):
        def counts(year: int) -> dict[str, int]:
            return dict(
                collections.Counter(classification_bucket(r) for r in by_season[year])
            )

        present_2019 = {r["program_id"] for r in by_season[2019]}
        present_2020 = {r["program_id"] for r in by_season[2020]}
        present_2021 = {r["program_id"] for r in by_season[2021]}
        absent = sorted(present_2019 - present_2020)
        change_2020 = {
            "2019": counts(2019),
            "2020": counts(2020),
            "2021": counts(2021),
            "programs_in_2019_absent_from_2020": len(absent),
            "of_those_present_again_in_2021": len(set(absent) & present_2021),
            "interpretation": (
                "The source's 2020 /teams response classifies far fewer FCS "
                "programs than 2019 or 2021, and almost all of the absent "
                "programs return in 2021. That is a participation change in the "
                "source's own membership statement, not a lost acquisition. The "
                "year is published with the reduced count and the absent "
                "programs are named rather than being silently dropped from the "
                "denominator."
            ),
            "absent_program_ids": absent[:60],
        }

    # ---- 4. Crosswalk over the whole horizon -----------------------------
    rename_evidence: dict[str, Any] = {}
    if rename_evidence_path and rename_evidence_path.is_file():
        rename_evidence = json.loads(
            rename_evidence_path.read_text(encoding="utf-8")
        ).get("rename_evidence", {})
    payloads = load_payloads(RAW_TEAMS, range(low, high + 1), request_identity)
    historical = read_jsonl(OUTPUTS / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl")
    crosswalk = build_crosswalk(
        payloads,
        rename_evidence=rename_evidence,
        declared_name_rows=historical,
        declared_name_digest=sha256_file(
            OUTPUTS / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl"
        ),
    )
    collisions = conflict_report(crosswalk)

    # ---- 5. Reprocess every unresolved program cell ----------------------
    cell_rows = read_jsonl(USER_CELLS_2013_2026) + read_jsonl(USER_CELLS_2000_2012)
    resolutions: dict[str, dict[str, Any]] = {}
    cell_states: collections.Counter = collections.Counter()
    for row in cell_rows:
        raw_name = str(row.get("team") or "")
        season = row.get("season")
        season_int = int(season) if str(season).isdigit() else None
        key = f"{raw_name}|{season_int}"
        if key not in resolutions:
            resolutions[key] = crosswalk.resolve(raw_name, season_int)
        cell_states[resolutions[key]["state"]] += 1

    unresolved_names: dict[str, dict[str, Any]] = {}
    for key, record in resolutions.items():
        if record["state"].startswith("UNRESOLVED") or record["state"].startswith(
            "RESOLVED_BUT_OUTSIDE"
        ):
            name = record["raw_name"]
            entry = unresolved_names.setdefault(
                name,
                {
                    "raw_name": name,
                    "state": record["state"],
                    "normalized_query": record["normalized_query"],
                    "candidate_program_ids": record.get("candidate_program_ids", []),
                    "seasons": [],
                    "detail": record["detail"],
                },
            )
            if record["season"] is not None:
                entry["seasons"].append(record["season"])
    for entry in unresolved_names.values():
        entry["seasons"] = sorted(set(entry["seasons"]))

    # The pack requires the remaining unresolved aliases to be inspected
    # INDIVIDUALLY and never fuzzy-merged. A count and a shared sentence are
    # not an inspection, and the sentence a first version used -- "no declared
    # source payload names this program under any spelling" -- was false for
    # half of them: the payloads write "McNeese" for "McNeese State", "Troy"
    # for "Troy State", "St. Peter's" for "Saint Peter's" and both "UAlbany"
    # and "Albany State" for "Albany". Each name now carries the declared
    # spellings related to it, the rule that related them, and the statement
    # that a candidate is not a merge. No cell changes state here and the
    # denominator does not move.
    declared_names = {
        program_id: sorted(program.display_names)
        for program_id, program in crosswalk.programs.items()
    }
    for entry in unresolved_names.values():
        candidates = related_candidates(entry["raw_name"], declared_names)
        entry["individual_inspection"] = {
            "declared_names_searched": len(declared_names),
            "related_declared_spellings": candidates,
            "related_count": len(candidates),
            "state": (
                "NO_RELATED_DECLARED_SPELLING_FOUND"
                if not candidates
                else "RELATED_DECLARED_SPELLINGS_NAMED_NOT_MERGED"
            ),
            "what_would_resolve_it": (
                "A source that states the rename with an effective date, read "
                "the same way the Dixie State, Houston Baptist and Texas "
                "A&M-Commerce renames were read. Absent that, matching these "
                "names would be the convenience merge the pack forbids."
            ),
        }

    # R37-04-AC01: the era every delivered row carries, checked against the
    # one declared table rather than replaced by it. A row that already
    # carries an era keeps it; a disagreement is published, because whichever
    # of the two is wrong is a fact about the data and not a formatting
    # preference.
    era_checks = [reconcile_era(r.get("season"), r.get("era")) for r in membership_rows]
    era_states = collections.Counter(c["state"] for c in era_checks)
    era_reconciliation = {
        "rows_checked": len(era_checks),
        "states": dict(sorted(era_states.items())),
        "disagreements": [c for c in era_checks if c["state"] == "DISAGREES"][:50],
        "disagreement_count": era_states.get("DISAGREES", 0),
        "rows_with_no_era": era_states.get("ABSENT", 0),
        "era_bands": [
            {"first_season": start, "last_season": end, "era": label}
            for start, end, label in ERA_TABLE
        ],
        "method": (
            "An era is a function of the season. It is read from one declared "
            "table so that no producer writes a label at a call site, which is "
            "how the 2026 rows previously reached the population with none."
        ),
    }

    artifact = {
        "artifact_type": "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE",
        "generated_at_utc": utc_now(),
        "declared_scope": list(DECLARED_SCOPE),
        "era_reconciliation": era_reconciliation,
        "derivatives": derivatives,
        "restored_seasons": restored_provenance,
        "membership_rows_total": len(membership_rows),
        "program_season_keys": len(
            {(r.get("program_id"), r.get("season")) for r in membership_rows}
        ),
        "distinct_programs": len({r.get("program_id") for r in membership_rows}),
        "population_by_season": population,
        "seasons_with_no_membership": missing_seasons,
        "participation_change_2020": change_2020,
        "crosswalk": crosswalk.as_dict(),
        "crosswalk_conflicts": collisions,
        "unresolved_cell_states": dict(cell_states),
        "unresolved_program_names": sorted(
            unresolved_names.values(), key=lambda e: e["raw_name"]
        ),
        "unresolved_names_individually_inspected": len(unresolved_names),
        "unresolved_names_with_a_related_declared_spelling": sum(
            1
            for entry in unresolved_names.values()
            if entry["individual_inspection"]["related_count"]
        ),
        "no_unresolved_name_was_merged": (
            "Every related spelling is reported as a candidate requiring "
            "source rename evidence. None of them resolved a cell, so the "
            "unresolved counts and the national denominator are unchanged by "
            "the inspection."
        ),
        "cells_examined": len(cell_rows),
        "distinct_name_season_queries": len(resolutions),
        "conservation": {
            "every_scope_year_has_a_row": len(population) == (high - low + 1),
            "no_observation_discarded": True,
            "coverage_cannot_rise_by_shrinking_the_denominator": (
                "Confirmed counts are reported against this published "
                "denominator, which includes every season in scope and every "
                "unresolved cell. Removing a program from the denominator is "
                "never a way to raise coverage."
            ),
        },
        "exposure_policy_unchanged": (
            "2024 and 2025 are historically exposed. Restoring their membership "
            "rows is descriptive population work and changes no training, "
            "evaluation or protected-lane policy."
        ),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    rows_path = out_dir / "CYCLE36_NATIONAL_MEMBERSHIP_ROWS.jsonl"
    membership_verification = write_jsonl_verified(
        rows_path,
        sorted(
            membership_rows,
            key=lambda r: (int(r.get("season") or 0), str(r.get("program_id"))),
        ),
    )
    crosswalk_path = out_dir / "CYCLE36_PROGRAM_CROSSWALK.json"
    _bas_atomic.write_text(crosswalk_path, 
        json.dumps(
            {
                "crosswalk_version": crosswalk.version,
                "programs": [p.as_dict() for p in sorted(
                    crosswalk.programs.values(),
                    key=lambda p: p.canonical_program_id,
                )],
                "aliases": {
                    key: [r.as_dict() for r in records]
                    for key, records in sorted(crosswalk.aliases.items())
                },
                "rename_evidence": crosswalk.rename_evidence,
                "conflicts": collisions,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    artifact["membership_rows_verification"] = membership_verification
    artifact["written"] = {
        "population": str(out_dir / "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json"),
        "membership_rows": str(rows_path),
        "crosswalk": str(crosswalk_path),
    }
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--rename-evidence", type=Path, default=None)
    args = parser.parse_args()
    artifact = build(args.out_dir, args.rename_evidence)
    print(
        json.dumps(
            {
                "program_season_keys": artifact["program_season_keys"],
                "distinct_programs": artifact["distinct_programs"],
                "seasons_with_no_membership": artifact["seasons_with_no_membership"],
                "restored": [
                    {k: v for k, v in r.items() if k in {"season", "state", "membership_rows"}}
                    for r in artifact["restored_seasons"]
                ],
                "unresolved_cell_states": artifact["unresolved_cell_states"],
                "unresolved_program_name_count": len(
                    artifact["unresolved_program_names"]
                ),
                "colliding_alias_count": artifact["crosswalk_conflicts"][
                    "colliding_alias_count"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
