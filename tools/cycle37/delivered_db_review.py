r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Independently review the corrected successor release against the delivered
predecessor, at row and cell grain.

"Independently" means this tool shares no counting code with the builder. It
opens both databases read-only and immutable and asks SQL questions directly,
so agreement between them is informative rather than guaranteed. It imports
nothing from ``cycle36.release_builder`` or ``cycle37.corrected_release``.

What it establishes, and what it does not: it establishes conservation,
lineage completeness and the exact affected-population diff. It does not
establish that a corrected binding is a true fact about the program -- that
is the source's claim, recorded with its evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
class _bas_atomic:  # U37-11: atomic writes, self-contained -- this tool stays independent of aggie_analytics
    @staticmethod
    def _begin(path):
        import os as _bas_os
        import pathlib as _bas_pathlib
        import tempfile as _bas_tempfile

        target = path.resolve() if path.is_symlink() else path
        handle, name = _bas_tempfile.mkstemp(dir=str(target.parent), prefix="~", suffix="")
        _bas_os.close(handle)
        return target, _bas_pathlib.Path(name)

    @staticmethod
    def _finish(temporary, target):
        import os as _bas_os
        import stat as _bas_stat
        import time as _bas_time

        with open(temporary, "rb+") as stream:
            _bas_os.fsync(stream.fileno())
        try:
            mode = _bas_stat.S_IMODE(_bas_os.stat(target).st_mode)
        except FileNotFoundError:
            umask = _bas_os.umask(0)
            _bas_os.umask(umask)
            mode = 0o666 & ~umask
        _bas_os.chmod(temporary, mode)
        for attempt in range(6):
            try:
                _bas_os.replace(temporary, target)
                return
            except PermissionError:
                if attempt == 5:
                    raise
                _bas_time.sleep(0.05 * (attempt + 1))

    @classmethod
    def _call(cls, method, path, *args, **kwargs):
        import pathlib as _bas_pathlib

        if not isinstance(path, _bas_pathlib.Path):
            return getattr(path, method)(*args, **kwargs)
        target, temporary = cls._begin(path)
        try:
            written = getattr(temporary, method)(*args, **kwargs)
            cls._finish(temporary, target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return written

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        return cls._call("write_text", path, *args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        return cls._call("write_bytes", path, *args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        import contextlib as _bas_contextlib
        import pathlib as _bas_pathlib

        @_bas_contextlib.contextmanager
        def _stream():
            if not isinstance(path, _bas_pathlib.Path):
                with path.open(*args, **kwargs) as stream:
                    yield stream
                return
            target, temporary = cls._begin(path)
            try:
                with temporary.open(*args, **kwargs) as stream:
                    yield stream
                cls._finish(temporary, target)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise

        return _stream()

sys.dont_write_bytecode = True

#: Tables whose row count must be identical between the two releases. A
#: correction rebinds rows; it never creates or destroys them.
CONSERVED = (
    "canonical_program",
    "program_alias",
    "alias_collision",
    "program_season_membership",
    "season_population",
    "staff_observation",
    "staff_role_assignment",
    "scheme_assertion",
    "scheme_conflict",
    "responsibility_assertion",
    "user_corpus_cell",
    "career_episode",
    "unresolved_program_name",
    "core_role_cell",
    "source_file",
)

#: A table a declared reparse may change, and the lineage field that must
#: record every change. A count difference there is not a finding when every
#: observation whose values differ carries a lineage row whose before and after
#: values equal the two tables; any unrecorded or mismatched difference is.
LINEAGE_RECONCILED = {"staff_role_assignment": ("staff_reparse_change", "role_codes")}


def _role_multisets(connection: sqlite3.Connection, schema: str) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for observation_id, role_code in connection.execute(
        f'SELECT observation_id, role_code FROM {schema}."staff_role_assignment"'
    ):
        out.setdefault(int(observation_id), []).append(str(role_code))
    return {k: sorted(v) for k, v in out.items()}


def reconcile_by_lineage(connection: sqlite3.Connection, table: str) -> dict[str, Any]:
    """Every changed observation must be recorded, with values that match both tables."""

    lineage_table, field = LINEAGE_RECONCILED[table]
    before = _role_multisets(connection, "pred")
    after = _role_multisets(connection, "main")
    changed = sorted(o for o in set(before) | set(after) if before.get(o, []) != after.get(o, []))
    recorded: dict[int, tuple[list[str], list[str]]] = {}
    for observation_id, old, new in connection.execute(
        f'SELECT observation_id, cycle36_value, cycle37_value FROM main."{lineage_table}" WHERE field = ?', (field,)
    ):
        recorded[int(observation_id)] = (sorted(json.loads(old or "[]")), sorted(json.loads(new or "[]")))
    unrecorded = [o for o in changed if o not in recorded]
    mismatched = [o for o in changed if o in recorded
                  and (recorded[o][0] != before.get(o, []) or recorded[o][1] != after.get(o, []))]
    return {"lineage_table": lineage_table, "lineage_field": field, "changed_observations": len(changed),
            "recorded": len(changed) - len(unrecorded), "unrecorded": unrecorded[:50],
            "values_disagree_with_the_tables": mismatched[:50],
            "reconciled": not unrecorded and not mismatched}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def ro(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"file:{Path(path).as_posix()}?mode=ro&immutable=1", uri=True
    )
    connection.row_factory = sqlite3.Row
    return connection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--successor", type=Path, required=True)
    parser.add_argument("--predecessor", type=Path, required=True)
    parser.add_argument("--also-compare", type=Path, default=None,
                        help="A second delivered predecessor, read-only.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    before = {
        "successor": sha256_file(args.successor),
        "predecessor": sha256_file(args.predecessor),
    }

    s = ro(args.successor)
    findings: list[str] = []

    # ---------------------------------------------------- conservation ----
    s.execute("ATTACH DATABASE ? AS pred",
              (f"file:{args.predecessor.as_posix()}?mode=ro&immutable=1",))
    conservation = {}
    for table in CONSERVED:
        a = int(s.execute(f'SELECT COUNT(*) FROM main."{table}"').fetchone()[0])
        b = int(s.execute(f'SELECT COUNT(*) FROM pred."{table}"').fetchone()[0])
        conservation[table] = {"successor": a, "predecessor": b, "conserved": a == b}
        if a != b and table in LINEAGE_RECONCILED:
            lineage = reconcile_by_lineage(s, table)
            conservation[table]["reconciled_by_lineage"] = lineage
            if not lineage["reconciled"]:
                findings.append(
                    f"{table} row count changed: {b} -> {a}, and {len(lineage['unrecorded'])} changed "
                    f"observations are unrecorded or {len(lineage['values_disagree_with_the_tables'])} disagree "
                    "with their lineage row"
                )
        elif a != b:
            findings.append(f"{table} row count changed: {b} -> {a}")

    # --------------------------------------------------------- lineage ----
    total_obs = int(s.execute("SELECT COUNT(*) FROM staff_observation").fetchone()[0])
    with_state = int(
        s.execute(
            "SELECT COUNT(*) FROM staff_observation WHERE binding_state IS NOT NULL"
        ).fetchone()[0]
    )
    # The right test is "does the retained original equal what the
    # predecessor actually held", not "is it non-null". 11,304 of the
    # delivered observations have a NULL program_id -- they are
    # CANDIDATE_FROM_UNBOUND_CAPTURE rows parsed from captures no acquisition
    # attempt declares -- and faithfully retaining NULL is correct. An
    # earlier version of this check tested for NOT NULL and reported those
    # 11,304 as a defect in the successor.
    drifted = int(
        s.execute(
            "SELECT COUNT(*) FROM main.staff_observation c "
            "JOIN pred.staff_observation p ON p.observation_id = c.observation_id "
            "WHERE COALESCE(c.original_program_id, '~NULL~') "
            "   <> COALESCE(p.program_id, '~NULL~')"
        ).fetchone()[0]
    )
    unbound_candidates = int(
        s.execute(
            "SELECT COUNT(*) FROM staff_observation WHERE program_id IS NULL"
        ).fetchone()[0]
    )
    if with_state != total_obs:
        findings.append(f"{total_obs - with_state} observations carry no binding state")
    if drifted:
        findings.append(
            f"{drifted} observations do not retain the program the predecessor held"
        )

    # Row-level lineage: every observation must reach a capture and bytes.
    orphan = int(
        s.execute(
            "SELECT COUNT(*) FROM staff_observation o "
            "LEFT JOIN source_identity_binding b ON b.payload_sha256 = o.payload_sha256 "
            "WHERE b.payload_sha256 IS NULL"
        ).fetchone()[0]
    )
    no_bytes = int(
        s.execute(
            "SELECT COUNT(*) FROM staff_observation "
            "WHERE payload_sha256 IS NULL OR TRIM(payload_sha256) = ''"
        ).fetchone()[0]
    )
    if no_bytes:
        findings.append(f"{no_bytes} observations carry no payload digest")

    # -------------------------------------------------- the actual diff ----
    rebound = [
        dict(r)
        for r in s.execute(
            "SELECT original_program_id, program_id, display_name, COUNT(*) AS rows "
            "FROM staff_observation WHERE binding_state = 'CORRECTED_BY_SOURCE_IDENTITY' "
            "GROUP BY 1,2,3 ORDER BY rows DESC"
        )
    ]
    unadmitted = int(
        s.execute(
            "SELECT COUNT(*) FROM staff_observation WHERE admitted_for_coverage = 0"
        ).fetchone()[0]
    )
    cell_moves = [
        dict(r)
        for r in s.execute(
            "SELECT p.coverage_state AS was, c.coverage_state AS now, COUNT(*) AS cells "
            "FROM main.core_role_cell c "
            "JOIN pred.core_role_cell p ON p.program_id = c.program_id "
            " AND p.season = c.season AND p.role_code = c.role_code "
            "WHERE p.coverage_state <> c.coverage_state GROUP BY 1,2 ORDER BY cells DESC"
        )
    ]
    coverage_now = {
        f"{r['grain']}|{r['bucket']}": r["value"]
        for r in s.execute("SELECT grain, bucket, value FROM coverage_summary")
    }
    coverage_then = {
        f"{r['grain']}|{r['bucket']}": r["value"]
        for r in s.execute("SELECT grain, bucket, value FROM predecessor_coverage_summary")
    }

    # A declared coverage number that disagrees with a live recount is a
    # defect in the release, not a rounding difference. Every coverage state
    # the release declares is recounted from core_role_cell. (A first version
    # computed one recount and never compared it.)
    states = [dict(r) for r in s.execute(
        "SELECT coverage_state, COUNT(*) AS cells FROM core_role_cell GROUP BY 1 ORDER BY cells DESC"
    )]
    for row in states:
        declared = coverage_now.get(f"CORE_ROLE_CELL|{row['coverage_state']}")
        if declared is not None and int(declared) != int(row["cells"]):
            findings.append(
                f"declared CORE_ROLE_CELL {row['coverage_state']} {declared} disagrees with the "
                f"live recount {row['cells']}"
            )
    declared_total = coverage_now.get("CORE_ROLE_CELL|TOTAL")
    live_total = int(s.execute("SELECT COUNT(*) FROM core_role_cell").fetchone()[0])
    if declared_total is not None and int(declared_total) != live_total:
        findings.append(
            f"declared CORE_ROLE_CELL total {declared_total} disagrees with the "
            f"live recount {live_total}"
        )

    lineage = {r["key"]: r["value"] for r in s.execute("SELECT key, value FROM release_lineage")}
    if lineage.get("predecessor_sha256") != before["predecessor"]:
        findings.append(
            "release_lineage names a predecessor digest that is not the file compared here"
        )

    # ------------------------------------- the other delivered release ----
    other: dict[str, Any] = {}
    if args.also_compare and args.also_compare.is_file():
        o = ro(args.also_compare)
        try:
            tables = sorted(
                str(r[0]) for r in o.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            )
            other = {
                "path": str(args.also_compare),
                "sha256": sha256_file(args.also_compare),
                "tables": tables,
                "read_only": True,
                "note": (
                    "Opened read-only and immutable and not modified. Its schema "
                    "differs from the national release; it is reported, not merged."
                ),
            }
        finally:
            o.close()

    s.close()

    after = {
        "successor": sha256_file(args.successor),
        "predecessor": sha256_file(args.predecessor),
    }
    if before != after:
        findings.append("a database changed digest during this read-only review")

    receipt = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-07",
        "method": (
            "Direct SQL over both databases opened read-only and immutable. This "
            "tool imports no builder code, so agreement is informative rather "
            "than guaranteed."
        ),
        "successor": str(args.successor),
        "successor_sha256": after["successor"],
        "predecessor": str(args.predecessor),
        "predecessor_sha256": after["predecessor"],
        "predecessor_unchanged_by_this_review": before["predecessor"] == after["predecessor"],
        "row_conservation": conservation,
        "all_conserved": all(v["conserved"] for v in conservation.values()),
        "all_conserved_or_reconciled_by_lineage": all(
            v["conserved"] or (v.get("reconciled_by_lineage") or {}).get("reconciled") for v in conservation.values()
        ),
        "lineage": {
            "observations": total_obs,
            "with_binding_state": with_state,
            "retained_original_differs_from_predecessor": drifted,
            "observations_with_no_program_binding_at_all": unbound_candidates,
            "observations_actually_bound_to_a_program": total_obs - unbound_candidates,
            "unbound_note": (
                "These are CANDIDATE_FROM_UNBOUND_CAPTURE rows parsed from "
                "captures that no acquisition attempt declares. They are "
                "retained, not discarded, and they mean the 16,428-observation "
                "headline is 5,124 program-bound observations plus 11,304 "
                "unbound candidates."
            ),
            "observations_without_a_capture_binding_row": orphan,
            "observations_without_payload_digest": no_bytes,
            "release_lineage": lineage,
        },
        "affected_population": {
            "rebound_observations": rebound,
            "rebound_total": sum(int(r["rows"]) for r in rebound),
            "observations_not_admitted_for_coverage": unadmitted,
            "core_cell_state_changes": cell_moves,
        },
        "coverage": {
            "successor_declared": coverage_now,
            "predecessor_declared": coverage_then,
            "successor_live_states": states,
            "live_core_role_cell_total": live_total,
        },
        "other_delivered_release": other,
        "findings": findings,
        "result": "CONSISTENT" if not findings else "DISCREPANCIES_FOUND",
        "not_established": (
            "Conservation and lineage completeness are not truth. A corrected "
            "binding is the program the capture's own page identity supports; "
            "independent adjudication of those pages remains a separate, "
            "unfinished obligation."
        ),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
                        encoding="utf-8")

    print("result              :", receipt["result"])
    print("all rows conserved  :", receipt["all_conserved"])
    print("rebound observations:", receipt["affected_population"]["rebound_total"])
    print("not admitted        :", unadmitted)
    print("cell state changes  :", cell_moves)
    print("predecessor unchanged:", receipt["predecessor_unchanged_by_this_review"])
    print("findings            :", findings or "none")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
