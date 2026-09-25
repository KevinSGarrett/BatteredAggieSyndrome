r"""Build a corrected national release as a successor, never an overwrite.

R37-07. The delivered Cycle 36 release ``release_c36_r1`` binds 175 staff
observations to the wrong program, because the ingest resolved a payload
claimed by two programs by file order (MF36-01, MF37-05). Those bindings are
now corrected by :mod:`aggie_analytics.cycle37.source_identity`, and this
module turns that correction into a *delivered* artifact.

The shape of the repair matters as much as the repair:

* **The predecessor is never modified.** It is opened read-only and
  immutable, its digest is verified against the one the manager recorded,
  and every declared source file is rehashed before a single row is copied.
  A tampered or missing input fails the build closed rather than producing a
  release that silently rests on different bytes.
* **The successor states its own lineage.** ``release_lineage`` names the
  predecessor by path and digest, the correction ledger by digest, and the
  counts it applied. ``source_identity_binding`` carries one row per capture
  with its route, page identity, every program that claimed it, the verdict
  and the reason -- which is row-level lineage, not a file listing.
* **Nothing is erased to make the correction look clean.** A corrected
  observation keeps ``original_program_id`` beside its new one. A capture
  whose identity could not be resolved is not deleted and not silently
  re-bound: it keeps its delivered program and is marked
  ``admitted_for_coverage = 0`` with the reason, so a consumer can exclude
  it deliberately and can still see it.
* **Derived tables are recomputed, not patched.** ``core_role_cell`` is
  rebuilt with the predecessor's own SQL over the corrected rows, and the
  predecessor's coverage numbers are retained beside the new ones in
  ``predecessor_coverage_summary`` so the difference is a queryable diff
  rather than a claim in a report.

Activation is a separate decision. Building a successor grants nothing.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from aggie_analytics.cycle36.release_builder import (
    CANDIDATE,
    CONFIRMED,
    CORE_ROLES,
    NO_EVIDENCE,
    SCIENTIFIC_TABLES,
    compare_releases,
    table_digest,
)

__all__ = [
    "CORRECTED_RELEASE_VERSION",
    "CorrectedReleaseError",
    "build_corrected_release",
    "content_identity",
]

CORRECTED_RELEASE_VERSION = "BAS-CYCLE37-CORRECTED-NATIONAL-RELEASE-v37.1"
#: The same successor with the staff tables rebuilt from the R37-03 reparse.
STAFF_REPARSE_RELEASE_VERSION = "BAS-CYCLE37-CORRECTED-NATIONAL-RELEASE-v37.2-STAFF-REPARSE"

#: Coverage states are IMPORTED from the predecessor's builder, never
#: restated here. An earlier version of this module spelled them
#: ``CONFIRMED_CORE_CELL`` / ``CANDIDATE_ONLY``, which silently relabelled
#: every cell: a consumer filtering on the real constant
#: ``CONFIRMED_SOURCE_SCOPED`` would have read zero confirmed cells out of a
#: release that has hundreds. Importing is what makes the recomputed cell
#: comparable to the one it replaces.

#: Tables copied through unchanged from the predecessor.
_PASSTHROUGH = (
    "canonical_program",
    "program_alias",
    "alias_collision",
    "program_season_membership",
    "season_population",
    "staff_role_assignment",
    "scheme_assertion",
    "scheme_conflict",
    "responsibility_assertion",
    "user_corpus_cell",
    "career_episode",
    "unresolved_program_name",
    "source_file",
)

#: Tables the successor adds. They are part of the scientific content and are
#: therefore compared between replays like any other.
SUCCESSOR_TABLES = (
    "source_identity_binding",
    "release_lineage",
    "predecessor_coverage_summary",
    "observation_binding_change",
)

#: Added only when the staff tables are rebuilt from the reparse: one row per
#: changed field of a reparsed observation, so the diff is queryable.
STAFF_REPARSE_TABLES = ("staff_reparse_change",)

#: Added when cell lineage for the user corpus and the source-rights binding
#: are supplied (R37-07 AC02): file, digest, record, line range, column,
#: spreadsheet address and person span for every user cell.
LINEAGE_TABLES = ("user_corpus_cell_lineage", "source_rights")

#: Successor datasets carried beside their predecessor tables rather than over
#: them, so a query can read both: name -> rows, each with a ledger digest.
_SUCCESSOR_NAME = re.compile(r"^[a-z][a-z0-9_]{2,62}$")

#: Columns the reparse adds to ``staff_observation``.
_REPARSE_COLUMNS = (
    ("person_raw", "TEXT"), ("person_cleaning_removed", "TEXT"), ("identity_state", "TEXT"),
    ("delivered_program_id", "TEXT"), ("source_effective_season", "INTEGER"), ("announcement_date", "TEXT"),
    ("season_parser_version", "TEXT"), ("sport_scope", "TEXT"), ("sport_basis", "TEXT"),
    ("football_role_admissible", "INTEGER"), ("binding_state_record", "TEXT"), ("dom_row_selector", "TEXT"),
    ("name_char_start", "INTEGER"), ("name_byte_start", "INTEGER"), ("name_byte_end", "INTEGER"),
    ("name_bytes_verified", "INTEGER"), ("record_version", "TEXT"), ("cycle36_observation_index", "INTEGER"),
    ("reparse_diff_state", "TEXT"),
)
_ASSIGNMENT_COLUMNS = (
    ("segment", "TEXT"), ("segment_qualifiers", "TEXT"), ("qualifier_scope", "TEXT"),
    ("taxonomy_correction", "TEXT"),
)


class CorrectedReleaseError(RuntimeError):
    """A precondition of the corrected build failed. Nothing was written."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _open_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"file:{Path(path).as_posix()}?mode=ro&immutable=1", uri=True
    )
    connection.row_factory = sqlite3.Row
    return connection


def verify_predecessor(
    predecessor: Path, expected_sha256: str | None, *, verify_source_files: bool = True
) -> dict[str, Any]:
    """Prove the predecessor is the artifact we mean before reading its rows.

    A build that does not check this is a build whose output cannot be tied
    to any particular input, which is the whole property a content-addressed
    release is supposed to have.
    """

    if not Path(predecessor).is_file():
        raise CorrectedReleaseError(f"predecessor release {predecessor} does not exist")
    observed = _sha256(predecessor)
    if expected_sha256 and observed != expected_sha256:
        raise CorrectedReleaseError(
            f"predecessor {predecessor} hashes {observed}, not the recorded "
            f"{expected_sha256}; refusing to build a successor on bytes that "
            f"are not the ones reviewed"
        )
    connection = _open_readonly(predecessor)
    try:
        declared = [dict(row) for row in connection.execute("SELECT * FROM source_file")]
    finally:
        connection.close()

    checked: list[dict[str, Any]] = []
    mismatched: list[dict[str, Any]] = []
    absent: list[dict[str, Any]] = []
    if verify_source_files:
        for row in declared:
            path = Path(str(row.get("path") or ""))
            recorded = str(row.get("sha256") or "")
            if not path.is_file():
                absent.append({"path": str(path), "recorded_sha256": recorded})
                continue
            actual = _sha256(path)
            entry = {"path": str(path), "recorded_sha256": recorded, "observed_sha256": actual}
            checked.append(entry)
            if recorded and actual != recorded:
                mismatched.append(entry)
    if mismatched or absent:
        raise CorrectedReleaseError(
            f"declared inputs failed verification: {len(mismatched)} digest "
            f"mismatch(es) and {len(absent)} missing file(s). The build fails "
            f"closed; the first few are "
            f"{[row['path'] for row in (mismatched + absent)][:5]}"
        )
    return {
        "predecessor": str(predecessor),
        "predecessor_sha256": observed,
        "predecessor_sha256_matches_recorded": bool(expected_sha256) and observed == expected_sha256,
        "declared_source_files": len(declared),
        "source_files_rehashed": len(checked),
        "source_file_digest_mismatches": 0,
        "source_files_absent": 0,
    }


def content_identity(database: Path, tables: Iterable[str]) -> str:
    """The release's identity, derived from its scientific content only.

    Execution timestamps live in ``audit_execution`` and are excluded by
    construction, so two honest replays of the same inputs address the same
    identity.
    """

    accumulator = hashlib.sha256()
    for table in sorted(tables):
        accumulator.update(table.encode("utf-8"))
        accumulator.update(b"\0")
        accumulator.update(table_digest(Path(database), table).encode("ascii"))
    return accumulator.hexdigest()


def build_corrected_release(
    *,
    predecessor: Path,
    crosswalk: Mapping[str, Any],
    crosswalk_sha256: str,
    destination: Path,
    predecessor_sha256: str | None = None,
    verify_source_files: bool = True,
    audit: Mapping[str, Any] | None = None,
    staff_rows: Sequence[Mapping[str, Any]] | None = None,
    staff_rows_sha256: str | None = None,
    user_lineage: Sequence[Mapping[str, Any]] | None = None,
    source_rights: Sequence[Mapping[str, Any]] | None = None,
    lineage_sha256: str | None = None,
    successor_tables: Mapping[str, tuple[Sequence[Mapping[str, Any]], str]] | None = None,
) -> dict[str, Any]:
    """Write the corrected successor. The predecessor is only ever read.

    With ``staff_rows`` (the R37-03 reparse), ``staff_observation`` and
    ``staff_role_assignment`` are rebuilt from those rows instead of copied,
    each observation keeping the predecessor id of the row it reparses, and
    every changed field is written to ``staff_reparse_change``.
    """

    if staff_rows is not None and not staff_rows_sha256:
        raise CorrectedReleaseError("reparsed staff rows need their ledger digest")
    if (user_lineage is None) != (source_rights is None):
        raise CorrectedReleaseError("cell lineage and source rights are supplied together")
    if user_lineage is not None and not lineage_sha256:
        raise CorrectedReleaseError("cell lineage needs its ledger digest")
    version = STAFF_REPARSE_RELEASE_VERSION if staff_rows is not None else CORRECTED_RELEASE_VERSION
    tables = (*SCIENTIFIC_TABLES, *SUCCESSOR_TABLES, *(STAFF_REPARSE_TABLES if staff_rows is not None else ()),
              *(LINEAGE_TABLES if user_lineage is not None else ()),
              *sorted(successor_tables or {}))
    for name, (_, digest) in (successor_tables or {}).items():
        if not _SUCCESSOR_NAME.match(name) or name in (*SCIENTIFIC_TABLES, *SUCCESSOR_TABLES):
            raise CorrectedReleaseError(f"successor table name {name!r} is not a new, plain table name")
        if not re.fullmatch(r"[0-9a-f]{64}", str(digest or "")):
            raise CorrectedReleaseError(f"successor table {name!r} needs the SHA-256 of its ledger")

    destination = Path(destination)
    if destination.exists():
        raise CorrectedReleaseError(
            f"{destination} already exists; a content-addressed release is "
            f"never overwritten in place"
        )
    verification = verify_predecessor(
        predecessor, predecessor_sha256, verify_source_files=verify_source_files
    )

    corrections = {
        str(row["payload_sha256"]): row for row in (crosswalk.get("corrections") or [])
    }
    quarantined = {
        str(row["payload_sha256"]): row for row in (crosswalk.get("quarantined") or [])
    }

    source = _open_readonly(predecessor)
    destination.parent.mkdir(parents=True, exist_ok=True)
    target = sqlite3.connect(str(destination))
    target.row_factory = sqlite3.Row
    try:
        _copy_schema(source, target)
        _create_successor_tables(target)
        if staff_rows is None:
            _copy_passthrough(source, target)
            changes = _copy_observations(source, target, corrections, quarantined)
        else:
            _create_reparse_tables(target)
            _copy_passthrough(source, target, skip=("staff_role_assignment",))
            changes = _write_reparsed_staff(source, target, staff_rows, crosswalk)
        _write_bindings(target, crosswalk)
        if user_lineage is not None:
            _write_lineage(target, user_lineage, source_rights or [])
        for name, (rows, _) in sorted((successor_tables or {}).items()):
            _write_successor_table(target, name, rows)
        _recompute_core_cells(target)
        predecessor_coverage = [
            (str(r["grain"]), str(r["bucket"]), str(r["value"]))
            for r in source.execute("SELECT grain, bucket, value FROM coverage_summary")
        ]
        target.executemany(
            "INSERT INTO predecessor_coverage_summary(grain, bucket, value) VALUES (?,?,?)",
            predecessor_coverage,
        )
        _recompute_coverage(target)
        _copy_release_identity(source, target, version)
        target.executemany(
            "INSERT INTO release_lineage(key, value) VALUES (?,?)",
            sorted(
                {
                    "successor_release_version": version,
                    "staff_reparse_ledger_sha256": staff_rows_sha256 or "NOT_USED",
                    "user_corpus_lineage_ledger_sha256": lineage_sha256 or "NOT_USED",
                    **{f"successor_table::{name}::ledger_sha256": digest
                       for name, (_, digest) in sorted((successor_tables or {}).items())},
                    "predecessor_path": str(predecessor),
                    "predecessor_sha256": verification["predecessor_sha256"],
                    "predecessor_declared_source_files": str(
                        verification["declared_source_files"]
                    ),
                    "correction_ledger_sha256": crosswalk_sha256,
                    "corrections_applied": str(len(corrections)),
                    "captures_quarantined": str(len(quarantined)),
                    "observations_rebound": str(changes["rebound"]),
                    "observations_flagged_unadmitted": str(changes["flagged"]),
                    "activation_state": "NOT_ACTIVATED_SEPARATE_OWNER_DECISION",
                    "predecessor_modified": "false",
                }.items()
            ),
        )
        if audit:
            target.executemany(
                "INSERT INTO audit_execution(audit_key, value) VALUES (?,?)",
                [(k, json.dumps(v)) for k, v in sorted(dict(audit).items())],
            )
        target.commit()
        counts = {
            table: int(target.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }
    finally:
        target.close()
        source.close()

    identity = content_identity(destination, tables)
    return {
        "release_version": version,
        "tables": list(tables),
        "database": str(destination),
        "sha256": _sha256(destination),
        "content_identity": identity,
        "table_counts": counts,
        "predecessor_verification": verification,
        "changes": changes,
        "not_claimed": (
            "A corrected binding is not an independently verified fact about "
            "the program. It is the program the capture's own page identity "
            "supports, recorded with its evidence."
        ),
    }


def _copy_schema(source: sqlite3.Connection, target: sqlite3.Connection) -> None:
    for row in source.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"
    ):
        target.execute(str(row["sql"]))


def _create_successor_tables(target: sqlite3.Connection) -> None:
    target.executescript(
        """
        CREATE TABLE source_identity_binding (
            capture_path TEXT NOT NULL,
            request_identity TEXT,
            payload_sha256 TEXT NOT NULL,
            route TEXT,
            claim_count INTEGER NOT NULL,
            claimed_programs TEXT NOT NULL,
            previous_program_id TEXT,
            admitted_program_id TEXT,
            binding_state TEXT NOT NULL,
            binding_reason TEXT NOT NULL,
            page_title TEXT,
            page_canonical TEXT,
            page_site_name TEXT,
            route_host TEXT
        );
        CREATE TABLE release_lineage (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE predecessor_coverage_summary (
            grain TEXT NOT NULL, bucket TEXT NOT NULL, value TEXT NOT NULL);
        CREATE TABLE observation_binding_change (
            observation_id TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            from_program_id TEXT,
            to_program_id TEXT,
            change_kind TEXT NOT NULL,
            reason TEXT NOT NULL
        );
        """
    )
    # The corrected binding columns live on the observation itself so a
    # consumer reading one row sees both values without a join.
    for statement in (
        "ALTER TABLE staff_observation ADD COLUMN original_program_id TEXT",
        "ALTER TABLE staff_observation ADD COLUMN binding_state TEXT",
        "ALTER TABLE staff_observation ADD COLUMN binding_reason TEXT",
        "ALTER TABLE staff_observation ADD COLUMN admitted_for_coverage INTEGER",
    ):
        target.execute(statement)


def _copy_passthrough(source: sqlite3.Connection, target: sqlite3.Connection,
                      skip: Iterable[str] = ()) -> None:
    skipped = set(skip)
    for table in _PASSTHROUGH:
        if table in skipped:
            continue
        columns = [r[1] for r in source.execute(f'PRAGMA table_info("{table}")')]
        marks = ", ".join("?" for _ in columns)
        names = ", ".join(f'"{c}"' for c in columns)
        rows = [tuple(r) for r in source.execute(f'SELECT {names} FROM "{table}"')]
        target.executemany(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', rows)


def _copy_observations(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    corrections: Mapping[str, Any],
    quarantined: Mapping[str, Any],
) -> dict[str, int]:
    columns = [r[1] for r in source.execute('PRAGMA table_info("staff_observation")')]
    out_columns = columns + [
        "original_program_id", "binding_state", "binding_reason", "admitted_for_coverage"
    ]
    names = ", ".join(f'"{c}"' for c in out_columns)
    marks = ", ".join("?" for _ in out_columns)

    rows: list[tuple[Any, ...]] = []
    changes: list[tuple[Any, ...]] = []
    rebound = flagged = 0
    for record in source.execute("SELECT * FROM staff_observation"):
        values = {c: record[c] for c in columns}
        payload = str(values.get("payload_sha256") or "")
        original = values.get("program_id")
        state = "CONFIRMED_BY_SOURCE_IDENTITY"
        reason = "the declared program is supported by the capture's own identity"
        admitted = 1
        if payload in corrections:
            correction = corrections[payload]
            values["program_id"] = correction["to_program_id"]
            values["display_name"] = correction.get("to_display_name") or values.get("display_name")
            state = "CORRECTED_BY_SOURCE_IDENTITY"
            reason = str(correction.get("reason") or "")
            rebound += 1
            changes.append(
                (
                    str(values.get("observation_id")), payload, original,
                    correction["to_program_id"], "REBOUND", reason,
                )
            )
        elif payload in quarantined:
            entry = quarantined[payload]
            state = str(entry.get("state") or "QUARANTINED")
            reason = str(entry.get("reason") or "")
            admitted = 0
            flagged += 1
            changes.append(
                (
                    str(values.get("observation_id")), payload, original, original,
                    "FLAGGED_NOT_ADMITTED", reason,
                )
            )
        rows.append(
            tuple(values[c] for c in columns) + (original, state, reason, admitted)
        )

    target.executemany(
        f'INSERT INTO staff_observation ({names}) VALUES ({marks})', rows
    )
    target.executemany(
        "INSERT INTO observation_binding_change"
        "(observation_id, payload_sha256, from_program_id, to_program_id, change_kind, reason)"
        " VALUES (?,?,?,?,?,?)",
        changes,
    )
    return {"total": len(rows), "rebound": rebound, "flagged": flagged}


def _create_reparse_tables(target: sqlite3.Connection) -> None:
    for name, kind in _REPARSE_COLUMNS:
        target.execute(f'ALTER TABLE staff_observation ADD COLUMN "{name}" {kind}')
    for name, kind in _ASSIGNMENT_COLUMNS:
        target.execute(f'ALTER TABLE staff_role_assignment ADD COLUMN "{name}" {kind}')
    target.execute(
        "CREATE TABLE staff_reparse_change (observation_id TEXT NOT NULL, field TEXT NOT NULL, "
        "cycle36_value TEXT, cycle37_value TEXT)"
    )


def _predecessor_ids(source: sqlite3.Connection) -> dict[tuple[str, int], tuple[int, str]]:
    """(capture, ordinal within capture) -> (predecessor observation id, person).

    The predecessor numbered observations in the order its ingest wrote them,
    capture by capture, so a capture's k-th row by id is its k-th parsed row.
    """

    by_capture: dict[str, list[tuple[Any, str]]] = {}
    for row in source.execute("SELECT observation_id, capture_path, person FROM staff_observation ORDER BY rowid"):
        by_capture.setdefault(str(row["capture_path"]), []).append((row["observation_id"], str(row["person"])))
    return {(capture, index): value for capture, rows in by_capture.items() for index, value in enumerate(rows)}


def _write_reparsed_staff(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    staff_rows: Sequence[Mapping[str, Any]],
    crosswalk: Mapping[str, Any],
) -> dict[str, int]:
    """Rebuild the staff tables from reparsed rows, aligned to predecessor ids."""

    predecessor = _predecessor_ids(source)
    numeric = all(isinstance(value[0], int) for value in predecessor.values())
    next_id = max((value[0] for value in predecessor.values()), default=0) + 1 if numeric else 1
    states = {str(row.get("capture_path")): row for row in crosswalk.get("rows") or []}
    base_columns = [r[1] for r in source.execute('PRAGMA table_info("staff_observation")')]
    columns = base_columns + ["original_program_id", "binding_state", "binding_reason", "admitted_for_coverage"] + [
        name for name, _ in _REPARSE_COLUMNS]
    assignment_columns = [r[1] for r in target.execute('PRAGMA table_info("staff_role_assignment")')]
    observations, assignments, changes, binding_changes = [], [], [], []
    misaligned = new_rows = 0
    assignment_id = 0
    for row in staff_rows:
        key = (str(row["capture_path"]), int(row["observation_index"]))
        known = predecessor.get(key)
        if known is None:
            observation_id = next_id if numeric else f"R37-03-NEW-{next_id}"
            next_id += 1
            new_rows += 1
        else:
            observation_id = known[0]
            if known[1] != row.get("person_raw"):
                misaligned += 1
        binding = row.get("binding") or {}
        name = binding.get("name_span") or {}
        identity = states.get(key[0]) or {}
        state = str(row.get("identity_state") or "")
        delivered = row.get("delivered_program_id")
        program = row.get("program_id") or (delivered if state != "UNCLAIMED_CAPTURE" else None)
        sport = row.get("sport_scope") or {}
        values = {
            "observation_id": observation_id, "capture_path": key[0], "payload_sha256": row.get("payload_sha256"),
            "program_id": program, "display_name": None, "person": row.get("person"),
            "source_title": row.get("source_title"), "record_selector": binding.get("record_selector"),
            "person_body_offset": binding.get("char_offset"),
            "person_record_bound": int(bool(binding.get("person_record_bound"))),
            "role_claim_supported": int(bool(binding.get("role_claim_supported"))),
            "reject_reason": None if binding.get("person_record_bound") else binding.get("state"),
            "evidence_tier": row.get("evidence_tier"), "season": row.get("season"),
            "season_state": row.get("season_state"), "source_class": "OFFICIAL_STAFF_HTML", "pit_admitted": 0,
            "original_program_id": delivered, "binding_state": state,
            "binding_reason": str(identity.get("reason") or ""),
            "admitted_for_coverage": int(bool(row.get("admitted_for_coverage"))),
            "person_raw": row.get("person_raw"),
            "person_cleaning_removed": json.dumps(row.get("person_cleaning_removed") or []),
            "identity_state": state, "delivered_program_id": delivered,
            "source_effective_season": row.get("source_effective_season"),
            "announcement_date": row.get("announcement_date"),
            "season_parser_version": row.get("season_parser_version"), "sport_scope": sport.get("scope"),
            "sport_basis": sport.get("basis"),
            "football_role_admissible": int(bool(sport.get("football_role_admissible"))),
            "binding_state_record": binding.get("state"),
            "dom_row_selector": (binding.get("dom_row") or {}).get("selector"),
            "name_char_start": name.get("char_start"), "name_byte_start": name.get("byte_start"),
            "name_byte_end": name.get("byte_end"), "name_bytes_verified": int(bool(name.get("verified"))),
            "record_version": binding.get("record_version"), "cycle36_observation_index": key[1],
            "reparse_diff_state": (row.get("diff") or {}).get("state"),
        }
        observations.append(tuple(values.get(column) for column in columns))
        for field, change in sorted(((row.get("diff") or {}).get("changes") or {}).items()):
            changes.append((str(observation_id), field, json.dumps(change.get("cycle36")),
                            json.dumps(change.get("cycle37"))))
        if program != delivered:
            binding_changes.append((str(observation_id), str(row.get("payload_sha256") or ""), delivered, program,
                                    "REBOUND" if program else "UNBOUND", str(identity.get("reason") or "")))
        for assignment in row.get("assignments") or []:
            assignment_id += 1
            record = {
                "assignment_id": assignment_id, "observation_id": observation_id, "role_code": assignment["role"],
                "unit": assignment.get("unit"), "qualifiers": json.dumps(assignment.get("title_qualifiers") or []),
                "occupancy": assignment.get("occupancy"), "taxonomy_version": assignment.get("taxonomy_version"),
                "is_core_role": int(assignment["role"] in CORE_ROLES), "play_caller_inferred": 0,
                "segment": assignment.get("segment"),
                "segment_qualifiers": json.dumps(assignment.get("segment_qualifiers") or []),
                "qualifier_scope": assignment.get("qualifier_scope"),
                "taxonomy_correction": assignment.get("taxonomy_correction"),
            }
            assignments.append(tuple(record.get(column) for column in assignment_columns))
    if misaligned:
        raise CorrectedReleaseError(
            f"{misaligned} reparsed rows do not match the predecessor person at their aligned id; "
            "the reparse is not a row-for-row successor"
        )
    names = ", ".join(f'"{c}"' for c in columns)
    target.executemany(f"INSERT INTO staff_observation ({names}) VALUES ({', '.join('?' for _ in columns)})",
                       observations)
    anames = ", ".join(f'"{c}"' for c in assignment_columns)
    target.executemany(
        f"INSERT INTO staff_role_assignment ({anames}) VALUES ({', '.join('?' for _ in assignment_columns)})",
        assignments)
    target.executemany("INSERT INTO staff_reparse_change VALUES (?,?,?,?)", changes)
    target.executemany(
        "INSERT INTO observation_binding_change"
        "(observation_id, payload_sha256, from_program_id, to_program_id, change_kind, reason)"
        " VALUES (?,?,?,?,?,?)", binding_changes)
    return {"total": len(observations), "rebound": len(binding_changes), "flagged": 0, "new_rows": new_rows,
            "field_changes": len(changes), "assignments": len(assignments),
            "predecessor_rows_not_reparsed": len(set(predecessor) - {
                (str(r["capture_path"]), int(r["observation_index"])) for r in staff_rows})}


def _write_lineage(
    target: sqlite3.Connection,
    user_lineage: Sequence[Mapping[str, Any]],
    source_rights: Sequence[Mapping[str, Any]],
) -> None:
    """Cell lineage for every user cell, and each source class's declared rights."""

    target.executescript(
        """
        CREATE TABLE user_corpus_cell_lineage (
            user_cell_id INTEGER NOT NULL, source_class TEXT, source_file TEXT NOT NULL,
            file_sha256 TEXT NOT NULL, record_ordinal INTEGER NOT NULL, csv_line_first INTEGER,
            csv_line_last INTEGER, column_header TEXT, column_index INTEGER, spreadsheet_cell TEXT,
            cell_text_sha256 TEXT, person_char_start INTEGER, person_char_end INTEGER, segment_text TEXT,
            observation_id TEXT);
        CREATE TABLE source_rights (
            source_class TEXT PRIMARY KEY, register_source_id TEXT, state TEXT NOT NULL,
            terms_or_license TEXT, redistribution TEXT, private_research_policy TEXT,
            public_repository_suitability TEXT, local_only_recommendation TEXT, classification TEXT);
        """
    )
    rows = []
    for row in user_lineage:
        span = row.get("person_char_span") or [None, None]
        lines = row.get("csv_lines") or [None, None]
        rows.append((row["user_cell_id"], row.get("source_class"), row["source_file"], row["file_sha256"],
                     row["record_ordinal"], lines[0], lines[1], row.get("column_header"), row.get("column_index"),
                     row.get("spreadsheet_cell"), row.get("cell_text_sha256"), span[0], span[1],
                     row.get("segment_text"), row.get("observation_id")))
    target.executemany("INSERT INTO user_corpus_cell_lineage VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    target.executemany(
        "INSERT INTO source_rights VALUES (?,?,?,?,?,?,?,?,?)",
        [(r["source_class"], r.get("register_source_id"), r["state"], r.get("terms_or_license"),
          r.get("redistribution"), r.get("private_research_policy"), r.get("public_repository_suitability"),
          r.get("local_only_recommendation"), r.get("classification")) for r in source_rights])
    orphans = int(target.execute(
        "SELECT COUNT(*) FROM user_corpus_cell_lineage AS l LEFT JOIN user_corpus_cell AS c "
        "ON c.user_cell_id = l.user_cell_id WHERE c.user_cell_id IS NULL").fetchone()[0])
    uncovered = int(target.execute(
        "SELECT COUNT(*) FROM user_corpus_cell AS c LEFT JOIN user_corpus_cell_lineage AS l "
        "ON l.user_cell_id = c.user_cell_id WHERE l.user_cell_id IS NULL").fetchone()[0])
    if orphans or uncovered:
        raise CorrectedReleaseError(
            f"cell lineage does not cover the user corpus one for one: {orphans} lineage rows without a cell, "
            f"{uncovered} cells without lineage")


def _write_successor_table(target: sqlite3.Connection, name: str, rows: Sequence[Mapping[str, Any]]) -> None:
    """One table per successor ledger; nested values are stored as sorted JSON text.

    Columns are the union of the rows' keys in sorted order, so the same
    ledger always makes the same table. Nothing is dropped: a key one row has
    and another lacks is NULL in the other.
    """

    columns = sorted({key for row in rows for key in row})
    if not columns:
        target.execute(f'CREATE TABLE "{name}" (empty_ledger TEXT)')
        return
    target.execute(f'CREATE TABLE "{name}" ({", ".join(f"{chr(34)}{c}{chr(34)}" for c in columns)})')

    def cell(value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True, ensure_ascii=False)
        if isinstance(value, bool):
            return int(value)
        return value

    marks = ", ".join("?" for _ in columns)
    names = ", ".join(f'"{c}"' for c in columns)
    target.executemany(f'INSERT INTO "{name}" ({names}) VALUES ({marks})',
                       [tuple(cell(row.get(c)) for c in columns) for row in rows])


def _write_bindings(target: sqlite3.Connection, crosswalk: Mapping[str, Any]) -> None:
    rows = []
    for entry in crosswalk.get("rows") or []:
        identity = entry.get("page_identity") or {}
        claimed = entry.get("claimed_programs") or []
        rows.append(
            (
                str(entry.get("capture_path") or ""),
                entry.get("request_identity"),
                str(entry.get("payload_sha256") or ""),
                entry.get("route"),
                int(entry.get("claim_count") or 0),
                json.dumps(claimed, sort_keys=True),
                (entry.get("previous_binding") or {}).get("program_id"),
                entry.get("admitted_program_id"),
                str(entry.get("state") or ""),
                str(entry.get("reason") or ""),
                identity.get("title"),
                identity.get("canonical_href"),
                identity.get("og_site_name"),
                identity.get("route_host"),
            )
        )
    target.executemany(
        "INSERT INTO source_identity_binding(capture_path, request_identity, "
        "payload_sha256, route, claim_count, claimed_programs, previous_program_id, "
        "admitted_program_id, binding_state, binding_reason, page_title, "
        "page_canonical, page_site_name, route_host) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )


def _recompute_core_cells(target: sqlite3.Connection) -> None:
    """Rebuild the HC/OC/DC matrix over the corrected rows.

    This is the predecessor's own query, with two additions: an observation
    the identity crosswalk could not admit does not contribute evidence (it
    still exists as a row; it just does not make a cell look confirmed), and
    a cell is confirmed only by an assignment that is not
    QUALIFIED_NOT_PRINCIPAL (MF36-14). On the delivered data the second
    changes no cell: none of the 447 confirmed cells rests on qualified-only
    evidence. It closes the gap for the next build rather than repairing a
    delivered row.
    """

    target.execute("DELETE FROM core_role_cell")
    target.execute(
        """
        INSERT INTO core_role_cell(program_id, season, role_code, coverage_state,
                                   observations)
        SELECT m.program_id, m.season, r.role_code,
               CASE
                   WHEN SUM(CASE WHEN e.observation_id IS NOT NULL
                                  AND e.person_record_bound = 1
                                  AND e.role_claim_supported = 1
                                  AND e.season IS NOT NULL
                                  AND e.evidence_tier = 'OFFICIAL_HTML_RECORD_BOUND'
                                  AND e.principal_or_shared = 1
                            THEN 1 ELSE 0 END) > 0 THEN ?
                   WHEN COUNT(e.observation_id) > 0 THEN ?
                   ELSE ?
               END,
               COUNT(e.observation_id)
        FROM program_season_membership AS m
        CROSS JOIN (SELECT ? AS role_code UNION ALL SELECT ? UNION ALL SELECT ?) AS r
        LEFT JOIN (
            SELECT DISTINCT o.observation_id, o.program_id, o.season,
                   o.person_record_bound, o.role_claim_supported, o.evidence_tier,
                   a.role_code,
                   -- MF36-14: a qualified title (the source denies the principal
                   -- role) is evidence of a related job, not that the cell's role
                   -- is filled. It can make a cell a candidate, never confirm it.
                   -- The flag is a function of (observation, role), so it changes
                   -- no count.
                   EXISTS (SELECT 1 FROM staff_role_assignment AS p
                           WHERE p.observation_id = o.observation_id
                             AND p.role_code = a.role_code
                             AND p.occupancy != 'QUALIFIED_NOT_PRINCIPAL') AS principal_or_shared
            FROM staff_observation AS o
            JOIN staff_role_assignment AS a ON a.observation_id = o.observation_id
            WHERE o.admitted_for_coverage = 1
        ) AS e
               ON e.program_id = m.program_id
              AND e.season = m.season
              AND e.role_code = r.role_code
        GROUP BY m.program_id, m.season, r.role_code
        """,
        (CONFIRMED, CANDIDATE, NO_EVIDENCE, *CORE_ROLES),
    )


def _recompute_coverage(target: sqlite3.Connection) -> None:
    """Coverage numbers are SELECTs over the corrected rows, never carried."""

    target.execute("DELETE FROM coverage_summary")

    def one(sql: str, params: tuple[Any, ...] = ()) -> int:
        return int(target.execute(sql, params).fetchone()[0])

    rows = [
        ("CORE_ROLE_CELL", "TOTAL", one("SELECT COUNT(*) FROM core_role_cell")),
        ("CORE_ROLE_CELL", CONFIRMED,
         one("SELECT COUNT(*) FROM core_role_cell WHERE coverage_state = ?", (CONFIRMED,))),
        ("CORE_ROLE_CELL", CANDIDATE,
         one("SELECT COUNT(*) FROM core_role_cell WHERE coverage_state = ?", (CANDIDATE,))),
        ("CORE_ROLE_CELL", NO_EVIDENCE,
         one("SELECT COUNT(*) FROM core_role_cell WHERE coverage_state = ?", (NO_EVIDENCE,))),
        ("STAFF_OBSERVATION", "TOTAL", one("SELECT COUNT(*) FROM staff_observation")),
        ("STAFF_OBSERVATION", "ADMITTED_FOR_COVERAGE",
         one("SELECT COUNT(*) FROM staff_observation WHERE admitted_for_coverage = 1")),
        ("STAFF_OBSERVATION", "REBOUND_BY_SOURCE_IDENTITY",
         one("SELECT COUNT(*) FROM staff_observation WHERE binding_state = 'CORRECTED_BY_SOURCE_IDENTITY'")),
        ("STAFF_OBSERVATION", "NOT_ADMITTED_UNRESOLVED_IDENTITY",
         one("SELECT COUNT(*) FROM staff_observation WHERE admitted_for_coverage = 0")),
        ("PROGRAM_SEASON_MEMBERSHIP", "TOTAL",
         one("SELECT COUNT(*) FROM program_season_membership")),
        ("SOURCE_IDENTITY_BINDING", "TOTAL", one("SELECT COUNT(*) FROM source_identity_binding")),
        ("CAREER_EPISODE", "TOTAL", one("SELECT COUNT(*) FROM career_episode")),
        ("SCHEME_ASSERTION", "TOTAL", one("SELECT COUNT(*) FROM scheme_assertion")),
        ("RESPONSIBILITY_ASSERTION", "TOTAL", one("SELECT COUNT(*) FROM responsibility_assertion")),
        ("USER_CORPUS_CELL", "TOTAL", one("SELECT COUNT(*) FROM user_corpus_cell")),
        ("UNRESOLVED_PROGRAM_NAME", "TOTAL", one("SELECT COUNT(*) FROM unresolved_program_name")),
    ]
    target.executemany(
        "INSERT INTO coverage_summary(grain, bucket, value) VALUES (?,?,?)",
        [(g, b, str(v)) for g, b, v in rows],
    )


def _copy_release_identity(source: sqlite3.Connection, target: sqlite3.Connection,
                           version: str = CORRECTED_RELEASE_VERSION) -> None:
    carried = [
        (f"predecessor::{row['key']}", row["value"])
        for row in source.execute("SELECT key, value FROM release_identity")
    ]
    target.executemany(
        "INSERT INTO release_identity(key, value) VALUES (?,?)",
        [
            ("release_version", version),
            ("successor_of", "CYCLE36_NATIONAL_RELEASE release_c36_r1"),
            ("built_at_utc", datetime.now(timezone.utc).isoformat()),
            *carried,
        ],
    )


def replay_and_compare(
    *,
    predecessor: Path,
    crosswalk: Mapping[str, Any],
    crosswalk_sha256: str,
    first_root: Path,
    second_root: Path,
    predecessor_sha256: str | None = None,
    staff_rows: Sequence[Mapping[str, Any]] | None = None,
    staff_rows_sha256: str | None = None,
    user_lineage: Sequence[Mapping[str, Any]] | None = None,
    source_rights: Sequence[Mapping[str, Any]] | None = None,
    lineage_sha256: str | None = None,
    successor_tables: Mapping[str, tuple[Sequence[Mapping[str, Any]], str]] | None = None,
) -> dict[str, Any]:
    """Build twice in separate roots and compare at scientific grain."""

    results = []
    for root in (first_root, second_root):
        root = Path(root)
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        results.append(
            build_corrected_release(
                predecessor=predecessor,
                crosswalk=crosswalk,
                crosswalk_sha256=crosswalk_sha256,
                destination=root / "CYCLE37_CORRECTED_NATIONAL_RELEASE.sqlite",
                predecessor_sha256=predecessor_sha256,
                # The inputs were verified on the first build; rehashing
                # 2,140 files twice proves nothing new about determinism.
                verify_source_files=(root == Path(first_root)),
                audit={"replay_root": str(root)},
                staff_rows=staff_rows,
                staff_rows_sha256=staff_rows_sha256,
                user_lineage=user_lineage,
                source_rights=source_rights,
                lineage_sha256=lineage_sha256,
                successor_tables=successor_tables,
            )
        )
    comparison = compare_releases(
        Path(results[0]["database"]),
        Path(results[1]["database"]),
        tables=tuple(results[0]["tables"]),
    )
    return {
        "first": results[0],
        "second": results[1],
        "comparison": comparison,
        "content_identity_matches": results[0]["content_identity"] == results[1]["content_identity"],
        "file_digests_differ_is_expected": (
            "The two files may differ byte for byte: SQLite page layout and "
            "the audit clock are not scientific content. Identity is the "
            "content digest over the declared tables, and that is compared."
        ),
    }
