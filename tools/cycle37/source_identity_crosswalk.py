r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Build the source-backed host/program identity crosswalk over the WHOLE staff
capture cache, and diff it against the delivered release.

This is the general form of MF36-01 and MF37-05. It does not look for Ohio
or New Mexico. It reads every acquisition attempt and every capture, derives
each capture's identity from its own bytes, adjudicates every program that
claims it, and reports:

* which declared bindings the capture's own identity confirms,
* which it contradicts,
* which payloads more than one program claims, and what the previous
  first-writer-wins rule did with them,
* the exact delivered rows and core cells each correction affects.

Nothing is written into the cache, the ledger or any delivered release. The
outputs are a crosswalk, a quarantine list and a diff, under the attempt's
own evidence root.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

WORKTREE = Path(__file__).resolve().parents[2]
if str(WORKTREE / "src") not in sys.path:
    sys.path.insert(0, str(WORKTREE / "src"))

from aggie_analytics.cycle37.source_identity import (  # noqa: E402
    BINDING_CONFIRMED,
    BINDING_CONTRADICTED,
    BINDING_NAME_NOT_MATCHED,
    BINDING_QUARANTINED_AMBIGUOUS,
    ProgramClaim,
    adjudicate,
    page_identity,
)
from aggie_analytics import atomic_io as _bas_atomic

CYCLE30 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
DEFAULT_CACHE = CYCLE30 / "raw" / "official_staff"
DEFAULT_ATTEMPTS = CYCLE30 / "outputs" / "OFFICIAL_STAFF_HTTP_ATTEMPTS.jsonl"
DEFAULT_LEDGER = CYCLE30 / "outputs" / "CYCLE30_OFFICIAL_STAFF_LEDGER.json"


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def program_catalogue(attempts: list[dict[str, Any]], release: Path | None) -> dict[str, str]:
    """Every program name this corpus knows about.

    Supplying the catalogue is what lets a mismatch be reported as "this is
    that declared program's page" instead of merely "the title does not say
    what I expected". Without it, ordinary branding -- "UK Athletics",
    "NDSU", "Ole Miss ... Hotty Toddy" -- reads as a wrong-school defect.
    """

    catalogue: dict[str, str] = {}
    for attempt in attempts:
        program_id = str(attempt.get("program_id") or "")
        name = str(attempt.get("display_name") or "")
        if program_id and name:
            catalogue.setdefault(program_id, name)
    if release and Path(release).is_file():
        conn = sqlite3.connect(
            f"file:{Path(release).as_posix()}?mode=ro&immutable=1", uri=True
        )
        try:
            for program_id, raw in conn.execute(
                "SELECT program_id, display_names FROM canonical_program"
            ):
                try:
                    names = json.loads(raw or "[]")
                except ValueError:
                    names = [raw]
                if isinstance(names, list) and names:
                    catalogue.setdefault(str(program_id), str(names[0]))
        finally:
            conn.close()
    return catalogue


def build(
    *,
    cache: Path,
    attempts_path: Path,
    ledger_path: Path,
    release: Path | None,
    out_dir: Path,
) -> dict[str, Any]:
    attempts = read_jsonl(attempts_path)
    catalogue = program_catalogue(attempts, release)

    # The acquisition ledger records the route actually requested for each
    # request identity. A capture file is named by request identity, so this
    # is how a capture is tied to the host that produced it even when the
    # attempt record's own page_url was resolved from somewhere else.
    route_by_request: dict[str, str] = {}
    if ledger_path.is_file():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        for row in ledger.get("attempts", []):
            identity = str(row.get("request_identity_sha256") or "")
            route = row.get("route")
            if identity and route:
                route_by_request.setdefault(identity, str(route))

    claims_by_digest: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for attempt in attempts:
        identity = str(attempt.get("receipt_identity") or "")
        if identity:
            claims_by_digest[identity].append(attempt)

    crosswalk: list[dict[str, Any]] = []
    states: collections.Counter = collections.Counter()
    corrections: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    captures_seen = 0
    bytes_seen = 0

    for path in sorted(cache.iterdir()):
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError as error:
            crosswalk.append(
                {
                    "capture_path": str(path),
                    "state": "UNREADABLE",
                    "reason": str(error),
                }
            )
            states["UNREADABLE"] += 1
            continue
        captures_seen += 1
        bytes_seen += len(data)
        digest = digest_bytes(data)
        request_identity = path.stem
        route = route_by_request.get(request_identity)

        claim_rows = claims_by_digest.get(digest, [])
        if not claim_rows:
            crosswalk.append(
                {
                    "capture_path": str(path),
                    "request_identity": request_identity,
                    "payload_sha256": digest,
                    "route": route,
                    "state": "UNCLAIMED_CAPTURE",
                    "reason": "no acquisition attempt declares this payload",
                }
            )
            states["UNCLAIMED_CAPTURE"] += 1
            continue

        text = data.decode("utf-8", errors="replace")
        identity = page_identity(text, route=route or (claim_rows[0].get("page_url")))
        verdict = adjudicate(
            identity,
            [
                ProgramClaim(
                    program_id=str(row.get("program_id")),
                    display_name=str(row.get("display_name")),
                    route=row.get("page_url"),
                )
                for row in claim_rows
            ],
            known_program_names=catalogue,
        )

        # What the predecessor's first-writer-wins rule produced, so the diff
        # is against the delivered behaviour rather than against a guess.
        previous_program = str(claim_rows[0].get("program_id"))
        previous_name = str(claim_rows[0].get("display_name"))
        admitted = verdict.get("admitted_program_id")

        row = {
            "capture_path": str(path),
            "request_identity": request_identity,
            "payload_sha256": digest,
            "bytes": len(data),
            "route": route,
            "claim_count": len(claim_rows),
            "claimed_programs": [
                {"program_id": str(r.get("program_id")), "display_name": str(r.get("display_name"))}
                for r in claim_rows
            ],
            "previous_binding": {
                "program_id": previous_program,
                "display_name": previous_name,
                "rule": "first attempt in file order (setdefault)",
            },
            "state": verdict["state"],
            "reason": verdict["reason"],
            "admitted_program_id": admitted,
            "page_identity": verdict["identity"],
            "claim_scores": verdict["claims"],
            "other_programs_the_page_covers": verdict.get(
                "other_programs_the_page_covers"
            ),
            "catalogue_consulted": verdict.get("catalogue_consulted"),
        }
        crosswalk.append(row)
        states[verdict["state"]] += 1

        if verdict["state"] == BINDING_CONFIRMED and admitted != previous_program:
            corrections.append(
                {
                    "payload_sha256": digest,
                    "capture_path": str(path),
                    "route": route,
                    "from_program_id": previous_program,
                    "from_display_name": previous_name,
                    "to_program_id": admitted,
                    "to_display_name": next(
                        (
                            c["display_name"]
                            for c in verdict["claims"]
                            if c["program_id"] == admitted
                        ),
                        None,
                    ),
                    "page_title": verdict["identity"].get("title"),
                    "reason": verdict["reason"],
                }
            )
        elif verdict["state"] in (
            BINDING_CONTRADICTED,
            BINDING_QUARANTINED_AMBIGUOUS,
            BINDING_NAME_NOT_MATCHED,
        ):
            quarantined.append(
                {
                    "payload_sha256": digest,
                    "capture_path": str(path),
                    "route": route,
                    "previous_program_id": previous_program,
                    "previous_display_name": previous_name,
                    "state": verdict["state"],
                    "reason": verdict["reason"],
                    "page_title": verdict["identity"].get("title"),
                }
            )

    # ------------------------------------------------ delivered-row impact
    impact: dict[str, Any] = {"release": str(release) if release else None}
    if release and Path(release).is_file():
        conn = sqlite3.connect(
            f"file:{Path(release).as_posix()}?mode=ro&immutable=1", uri=True
        )
        conn.row_factory = sqlite3.Row
        try:
            affected_digests = {row["payload_sha256"] for row in corrections}
            quarantine_digests = {row["payload_sha256"] for row in quarantined}
            placeholders = ",".join("?" * len(affected_digests)) or "NULL"
            observations = (
                [
                    dict(row)
                    for row in conn.execute(
                        "SELECT observation_id, payload_sha256, program_id, "
                        "display_name, person, source_title, season "
                        f"FROM staff_observation WHERE payload_sha256 IN ({placeholders})",
                        tuple(sorted(affected_digests)),
                    )
                ]
                if affected_digests
                else []
            )
            q_placeholders = ",".join("?" * len(quarantine_digests)) or "NULL"
            quarantine_rows = (
                [
                    dict(row)
                    for row in conn.execute(
                        "SELECT observation_id, payload_sha256, program_id, "
                        "display_name, person, source_title, season "
                        f"FROM staff_observation WHERE payload_sha256 IN ({q_placeholders})",
                        tuple(sorted(quarantine_digests)),
                    )
                ]
                if quarantine_digests
                else []
            )
            assignment_count = 0
            if observations:
                ids = [row["observation_id"] for row in observations]
                marks = ",".join("?" * len(ids))
                assignment_count = int(
                    conn.execute(
                        f"SELECT COUNT(*) FROM staff_role_assignment "
                        f"WHERE observation_id IN ({marks})",
                        tuple(ids),
                    ).fetchone()[0]
                )
            # Core cells whose program/season pair either loses or gains
            # evidence under the corrected bindings.
            pairs_losing = {
                (row["program_id"], row["season"]) for row in observations
            }
            pairs_gaining = set()
            by_digest = {row["payload_sha256"]: row for row in corrections}
            for row in observations:
                correction = by_digest.get(row["payload_sha256"])
                if correction:
                    pairs_gaining.add((correction["to_program_id"], row["season"]))
            cells_losing = _count_cells(conn, pairs_losing)
            cells_gaining = _count_cells(conn, pairs_gaining)
            impact.update(
                {
                    "delivered_observations_bound_to_a_corrected_capture": len(observations),
                    "delivered_role_assignments_affected": assignment_count,
                    "delivered_observations_bound_to_a_quarantined_capture": len(
                        quarantine_rows
                    ),
                    "program_season_pairs_losing_evidence": sorted(
                        [list(pair) for pair in pairs_losing], key=str
                    ),
                    "program_season_pairs_gaining_evidence": sorted(
                        [list(pair) for pair in pairs_gaining], key=str
                    ),
                    "core_role_cells_at_losing_pairs": cells_losing,
                    "core_role_cells_at_gaining_pairs": cells_gaining,
                    "affected_observation_sample": observations[:40],
                    "quarantined_observation_sample": quarantine_rows[:40],
                }
            )
        finally:
            conn.close()

    artifact = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "finding_ids": ["MF36-01", "MF37-05"],
        "requirement": "R37-03",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "capture_cache": str(cache),
            "attempt_ledger": str(attempts_path),
            "acquisition_ledger": str(ledger_path),
            "delivered_release": str(release) if release else None,
        },
        "captures_read": captures_seen,
        "capture_bytes_read": bytes_seen,
        "declared_attempt_records": len(attempts),
        "program_catalogue_size": len(catalogue),
        "distinct_claimed_payloads": len(claims_by_digest),
        "payloads_claimed_by_more_than_one_program": sum(
            1
            for rows in claims_by_digest.values()
            if len({str(r.get("program_id")) for r in rows}) > 1
        ),
        "attempt_records_discarded_by_first_writer_wins": sum(
            len(rows) - 1
            for rows in claims_by_digest.values()
            if len({str(r.get("program_id")) for r in rows}) > 1
        ),
        "binding_states": dict(states),
        "corrections": corrections,
        "correction_count": len(corrections),
        "quarantined": quarantined,
        "quarantined_count": len(quarantined),
        "delivered_impact": impact,
        "method": (
            "A declared program is a claim. It is admitted only when the "
            "capture's own title, canonical link, site name or host covers it "
            "without naming a longer program. Ties and contradictions "
            "quarantine; nothing is resolved by file order."
        ),
        "not_claimed": (
            "This crosswalk corrects bindings. It does not rebuild the "
            "delivered release, and no delivered row was modified by this "
            "tool."
        ),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "R37_03_SOURCE_IDENTITY_CROSSWALK.json", 
        json.dumps(artifact, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    with _bas_atomic.open_write(out_dir / "R37_03_SOURCE_IDENTITY_ROWS.jsonl", 
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        for row in crosswalk:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    return artifact


def _count_cells(conn: sqlite3.Connection, pairs: set[tuple[Any, Any]]) -> int:
    total = 0
    for program_id, season in pairs:
        if program_id is None:
            continue
        if season is None:
            row = conn.execute(
                "SELECT COUNT(*) FROM core_role_cell WHERE program_id = ? AND season IS NULL",
                (program_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM core_role_cell WHERE program_id = ? AND season = ?",
                (program_id, season),
            ).fetchone()
        total += int(row[0])
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--attempts", type=Path, default=DEFAULT_ATTEMPTS)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--release", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    artifact = build(
        cache=args.cache.resolve(),
        attempts_path=args.attempts.resolve(),
        ledger_path=args.ledger.resolve(),
        release=args.release.resolve() if args.release else None,
        out_dir=args.out_dir.resolve(),
    )
    print(
        json.dumps(
            {
                key: artifact[key]
                for key in (
                    "captures_read",
                    "declared_attempt_records",
                    "distinct_claimed_payloads",
                    "payloads_claimed_by_more_than_one_program",
                    "attempt_records_discarded_by_first_writer_wins",
                    "binding_states",
                    "correction_count",
                    "quarantined_count",
                )
            },
            indent=2,
        )
    )
    for row in artifact["corrections"]:
        print(
            f"  CORRECT {row['from_display_name']!r} -> {row['to_display_name']!r}  "
            f"{row['route']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
