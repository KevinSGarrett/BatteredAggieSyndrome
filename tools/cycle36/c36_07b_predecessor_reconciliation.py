"""R36-03/07: exact retained / changed / quarantined lists against Cycle #35.

The season repair changes what the release asserts, so the release must say
which of the predecessor's rows survived it. This tool joins the Cycle #35
delivered database (``release_r4``) row by row against the Cycle #36
successor and puts every predecessor assertion in exactly one bucket:

* ``RETAINED_SAME_SEASON`` -- the same person, program and role, with the
  same season;
* ``CHANGED_SEASON`` -- the predecessor asserted a season and the repaired
  binder reads a different one;
* ``QUARANTINED_SEASON_WITHDRAWN`` -- the predecessor asserted a season and
  no rendered heading governs the record, so that season is withdrawn;
* ``BOTH_LEAVE_THE_SEASON_UNSPECIFIED`` -- the predecessor recorded
  ``CURRENT``, which asserts no season, and the successor also binds none.
  That is agreement about an unknown, not a withdrawal;
* ``SEASON_NEWLY_BOUND_BY_THE_SUCCESSOR`` -- the predecessor recorded
  ``CURRENT`` and the successor supplies a season. An addition, not a change;
* ``NOT_PRESENT_IN_SUCCESSOR`` -- the assertion has no counterpart at all;
* and, counted separately, rows the predecessor never had.

Downstream invalidation follows from the buckets: anything reading a changed
or quarantined season must be recomputed, and the affected program-seasons
are listed so a consumer can be pointed at them rather than told "some rows
changed".

The predecessor database is opened read-only and is never modified.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
import sys
import unicodedata
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]

PREDECESSOR = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs"
    r"\20260921T055921Z_implementation\release_r4"
    r"\CYCLE35_COACHING_RELEASE_coverage.sqlite"
)

RETAINED = "RETAINED_SAME_SEASON"
CHANGED = "CHANGED_SEASON"
QUARANTINED = "QUARANTINED_SEASON_WITHDRAWN"
ABSENT = "NOT_PRESENT_IN_SUCCESSOR"
BOTH_UNSPECIFIED = "BOTH_LEAVE_THE_SEASON_UNSPECIFIED"
NEWLY_BOUND = "SEASON_NEWLY_BOUND_BY_THE_SUCCESSOR"

#: States that mean a consumer of the predecessor must recompute. Agreement
#: about an unknown, and a season the successor newly supplies, are not
#: invalidations: the first changes nothing and the second only adds.
INVALIDATING = (CHANGED, QUARANTINED, ABSENT)

#: The predecessor stores role families and the successor stores taxonomy
#: role codes. Both come from the same Cycle #33 taxonomy, so the
#: correspondence is the identity on a casefolded family -- which a first
#: version of this tool got wrong by mapping only three UPPERCASE names,
#: turning every one of 1,499 predecessor rows into NOT_PRESENT. A join that
#: silently drops what it cannot map is worse than no join, so the mapping is
#: explicit and the unmapped families are counted.
CORE_FAMILIES = ("head_coach", "offensive_coordinator", "defensive_coordinator")


def role_code_for(family: str) -> str | None:
    """The successor role code a predecessor family corresponds to."""

    code = str(family or "").strip().casefold()
    return code or None

_PUNCT = re.compile(r"[^a-z0-9]+")


def normalize_person(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", _PUNCT.sub(" ", text.casefold())).strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def build(
    out_dir: Path,
    successor: Path,
    predecessor: Path,
    capture_inventory: Path | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "artifact_type": "CYCLE36_PREDECESSOR_RECONCILIATION",
        "generated_at_utc": utc_now(),
        "predecessor": {
            "path": str(predecessor),
            "exists": predecessor.is_file(),
            "sha256": sha256_file(predecessor),
        },
        "successor": {
            "path": str(successor),
            "exists": successor.is_file(),
            "sha256": sha256_file(successor),
        },
        "role_family_correspondence": (
            "identity on the casefolded family; both databases use the "
            "Cycle #33 taxonomy vocabulary"
        ),
        "core_families": list(CORE_FAMILIES),
    }
    if not predecessor.is_file() or not successor.is_file():
        record["state"] = "ONE_OR_BOTH_DATABASES_ABSENT"
        return record

    before = sha256_file(predecessor)
    old = read_only(predecessor)
    new = read_only(successor)
    try:
        predecessor_rows = [
            dict(row)
            for row in old.execute(
                "SELECT a.assertion_id, a.role_family, a.evidence_layer, "
                "e.program_id, e.season, p.canonical_name "
                "FROM formal_role_assertion AS a "
                "JOIN employment_episode AS e ON e.episode_id = a.episode_id "
                "JOIN canonical_person AS p ON p.person_id = e.person_id"
            )
        ]
        successor_index: dict[tuple[str, str, str], set[Any]] = (
            collections.defaultdict(set)
        )
        successor_rows = 0
        for row in new.execute(
            "SELECT o.program_id, o.person, o.season, a.role_code "
            "FROM staff_observation AS o "
            "JOIN staff_role_assignment AS a "
            "  ON a.observation_id = o.observation_id "
            "WHERE o.program_id IS NOT NULL"
        ):
            successor_rows += 1
            successor_index[
                (
                    str(row["program_id"]),
                    normalize_person(row["person"]),
                    str(row["role_code"]),
                )
            ].add(row["season"])
    finally:
        old.close()
        new.close()
    record["predecessor_unchanged_by_this_read"] = before == sha256_file(predecessor)

    buckets: collections.Counter = collections.Counter()
    rows: list[dict[str, Any]] = []
    affected_program_seasons: set[str] = set()

    for row in predecessor_rows:
        family = str(row.get("role_family") or "")
        code = role_code_for(family)
        key = (
            str(row.get("program_id")),
            normalize_person(row.get("canonical_name")),
            str(code),
        )
        declared_season = row.get("season")
        try:
            declared_int: Any = int(declared_season)
        except (TypeError, ValueError):
            declared_int = None
        seasons = successor_index.get(key, set())
        bound = {season for season in seasons if season is not None}
        if code is None or not seasons:
            state = ABSENT
        elif declared_int is None:
            # The predecessor recorded CURRENT, which asserts no season. Both
            # leaving it unspecified is agreement, and the successor supplying
            # one is an addition -- neither is a withdrawal, and a first
            # version of this tool reported 229 of them as quarantined.
            state = NEWLY_BOUND if bound else BOTH_UNSPECIFIED
        elif declared_int in bound:
            state = RETAINED
        elif not bound:
            state = QUARANTINED
        else:
            state = CHANGED
        buckets[state] += 1
        if state in INVALIDATING:
            affected_program_seasons.add(
                f"{row.get('program_id')}|{declared_season}"
            )
        rows.append(
            {
                "predecessor_assertion_id": row.get("assertion_id"),
                "program_id": row.get("program_id"),
                "person": row.get("canonical_name"),
                "predecessor_role_family": family,
                "successor_role_code": code,
                "predecessor_season": declared_season,
                "successor_seasons": sorted(
                    (s for s in seasons if s is not None), key=lambda v: int(v)
                )
                + ([None] if None in seasons else []),
                "predecessor_evidence_layer": row.get("evidence_layer"),
                "state": state,
            }
        )

    # Why are rows absent? The successor binds a capture to a program only
    # when the capture's BYTES hash to the attempt's declared receipt
    # identity. That is stricter than the predecessor's binding, and it
    # leaves some declared attempts unbound, so their staff rows carry no
    # program and cannot match. The count is reported rather than left as an
    # unexplained residual.
    bound_programs: set[str] = set()
    declared_attempt_programs: set[str] = set()
    if capture_inventory and capture_inventory.is_file():
        for line in capture_inventory.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            row = json.loads(line)
            attempt = row.get("declared_attempt") or {}
            program = attempt.get("program_id")
            if program:
                declared_attempt_programs.add(str(program))
                if row.get("capture_state") == "BOUND_TO_A_DECLARED_ACQUISITION_ATTEMPT":
                    bound_programs.add(str(program))
    absent_programs = {
        str(row["program_id"]) for row in rows if row["state"] == ABSENT
    }
    absent_explained = (
        absent_programs - bound_programs if bound_programs else set()
    )
    absent_reasons = {
        "distinct_programs_with_an_absent_row": len(absent_programs),
        "programs_the_successor_never_bound": len(absent_explained),
        "programs_bound_but_with_a_differing_row": len(
            absent_programs - absent_explained
        ),
        "capture_inventory_read": bool(bound_programs),
        "why": (
            "The successor binds a capture to a program only when the "
            "capture's bytes hash to the declared receipt identity of an "
            "acquisition attempt. Attempts whose declared digest matches no "
            "cached file stay unbound, and their staff rows carry no program, "
            "so a predecessor assertion for those programs has nothing to "
            "match. The remainder are programs that are bound but whose "
            "person or role parsed differently."
        ),
    }

    unmapped_families = sorted(
        {
            str(row.get("role_family"))
            for row in predecessor_rows
            if role_code_for(row.get("role_family")) is None
        }
    )
    new_rows = sum(
        len(seasons) for seasons in successor_index.values()
    ) - buckets.get(RETAINED, 0)

    record.update(
        state="RECONCILED",
        predecessor_assertions=len(predecessor_rows),
        successor_role_rows=successor_rows,
        buckets=dict(buckets),
        every_predecessor_row_bucketed=sum(buckets.values()) == len(predecessor_rows),
        predecessor_families_with_no_successor_code=unmapped_families,
        core_family_rows=sum(
            1
            for row in predecessor_rows
            if role_code_for(row.get("role_family")) in CORE_FAMILIES
        ),
        new_in_cycle36_role_season_pairs=max(new_rows, 0),
        affected_program_seasons=sorted(affected_program_seasons)[:200],
        affected_program_season_count=len(affected_program_seasons),
        absent_row_reasons=absent_reasons,
        invalidating_states=list(INVALIDATING),
        invalidating_rows=sum(buckets.get(state, 0) for state in INVALIDATING),
        downstream_invalidation=(
            "Any consumer that read a CHANGED or QUARANTINED season must "
            "recompute against the successor. The affected program-seasons are "
            "listed above so a consumer can be pointed at them instead of "
            "being told that some rows changed."
        ),
        predecessor_preserved=(
            "release_r4 is opened read-only and its digest is re-checked after "
            "the read. It is not modified, moved or superseded in place."
        ),
        rows=rows,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_PREDECESSOR_RECONCILIATION.json", 
        json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--successor", type=Path, required=True)
    parser.add_argument("--predecessor", type=Path, default=PREDECESSOR)
    parser.add_argument("--capture-inventory", type=Path, default=None)
    args = parser.parse_args()
    record = build(
        args.out_dir, args.successor, args.predecessor, args.capture_inventory
    )
    print(
        json.dumps(
            {
                key: record.get(key)
                for key in (
                    "state",
                    "predecessor_assertions",
                    "successor_role_rows",
                    "buckets",
                    "every_predecessor_row_bucketed",
                    "new_in_cycle36_role_season_pairs",
                    "affected_program_season_count",
                    "absent_row_reasons",
                    "predecessor_unchanged_by_this_read",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
