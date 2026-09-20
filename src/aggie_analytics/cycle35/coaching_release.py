"""R35-03: a source-driven canonical coaching release.

The Cycle #34 delivery was an 85-row transcription whose `verified` flags
came from tuples typed into the ingester (`PROGRAM_SEASONS`,
`JOIN_ATTEMPTS`). A name typed into a Python literal may well be correct,
but nothing in the artifact could show *why* it was believed, and a
hand-maintained list cannot be the production authority for a national
dataset. This module replaces that with an ingestion whose every promoted
assertion traces back to a file on disk.

Design decisions that follow from the findings rather than from taste:

* **Observations and assertions are different tables.** A source observation
  records what a file said, at a locator, with the file's own hash. An
  assertion records what we believe, and names the observations supporting
  it. Collapsing the two is what makes "verified" unfalsifiable.

* **Verification is a layer, not a flag.** `evidence_layer` separates
  CANDIDATE (a source said it) from CORROBORATED (independent sources agree)
  from OFFICIAL_CONFIRMED (a primary source confirms). A boolean `verified`
  column cannot express the difference and so always overstates.

* **Conflicts are stored, not resolved by arrival order.** Two sources
  disagreeing produces a conflict row and an adjudication row; last-write
  never wins, and the losing assertion stays readable.

* **Releases are append-only and never unlink a predecessor.** Each build
  writes a NEW database keyed by its own content, and the release manifest
  grows. A predecessor's bytes are never touched.

* **Imports are deterministic.** Every identity is content-addressed from
  the source bytes and the observation's own fields, so replaying the same
  inputs produces the same row identities -- which is what makes two runs
  comparable at all.

Nothing here promotes anything to PIT, and nothing here treats retrieval
today as evidence of what was known yesterday.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

SCHEMA_VERSION = 3
RELEASE_KIND = "BAS-CYCLE35-COACHING-RELEASE"

#: Evidence layers, weakest first. A layer is a claim about corroboration,
#: never about truth.
LAYER_OBSERVED = "OBSERVED_SOURCE_ROW"
LAYER_CANDIDATE = "CANDIDATE_SINGLE_SOURCE"
LAYER_CORROBORATED = "CORROBORATED_MULTI_SOURCE"
LAYER_OFFICIAL = "OFFICIAL_PRIMARY_CONFIRMED"
LAYER_REJECTED = "REJECTED"
LAYER_QUARANTINED = "QUARANTINED_CONFLICT"
LAYER_UNRESOLVED = "UNRESOLVED"

EVIDENCE_LAYERS = (
    LAYER_OBSERVED,
    LAYER_CANDIDATE,
    LAYER_CORROBORATED,
    LAYER_OFFICIAL,
    LAYER_REJECTED,
    LAYER_QUARANTINED,
    LAYER_UNRESOLVED,
)


class CoachingReleaseError(RuntimeError):
    """Raised when a release cannot be built without losing evidence."""


MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE source_file (
            source_file_id   TEXT PRIMARY KEY,
            path             TEXT NOT NULL,
            raw_sha256       TEXT NOT NULL,
            decoded_sha256   TEXT,
            bytes            INTEGER NOT NULL,
            source_class     TEXT NOT NULL,
            rights_state     TEXT NOT NULL,
            acquisition_receipt TEXT,
            source_revision  TEXT,
            retrieved_at_utc TEXT
        );
        CREATE TABLE source_observation (
            observation_id   TEXT PRIMARY KEY,
            source_file_id   TEXT NOT NULL REFERENCES source_file(source_file_id),
            locator          TEXT NOT NULL,
            observed_text    TEXT,
            observed_person  TEXT,
            observed_title   TEXT,
            observed_program TEXT,
            observed_season  TEXT,
            parser_identity  TEXT NOT NULL,
            evidence_layer   TEXT NOT NULL,
            UNIQUE (source_file_id, locator, observed_person, observed_title)
        );
        CREATE TABLE canonical_program (
            program_id       TEXT PRIMARY KEY,
            display_name     TEXT,
            classification   TEXT,
            first_season     INTEGER,
            last_season      INTEGER
        );
        CREATE TABLE canonical_person (
            person_id        TEXT PRIMARY KEY,
            canonical_name   TEXT NOT NULL,
            identity_basis   TEXT NOT NULL
        );
        CREATE TABLE person_alias (
            person_id        TEXT NOT NULL REFERENCES canonical_person(person_id),
            alias            TEXT NOT NULL,
            alias_kind       TEXT NOT NULL,
            PRIMARY KEY (person_id, alias)
        );
        """,
    ),
    (
        2,
        """
        CREATE TABLE employment_episode (
            episode_id       TEXT PRIMARY KEY,
            person_id        TEXT REFERENCES canonical_person(person_id),
            program_id       TEXT REFERENCES canonical_program(program_id),
            season           TEXT,
            valid_from       TEXT,
            valid_to         TEXT,
            date_precision   TEXT NOT NULL,
            evidence_layer   TEXT NOT NULL,
            pit_admitted     INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE formal_role_assertion (
            assertion_id     TEXT PRIMARY KEY,
            episode_id       TEXT NOT NULL REFERENCES employment_episode(episode_id),
            role_family      TEXT NOT NULL,
            exact_title_text TEXT NOT NULL,
            qualifiers       TEXT NOT NULL,
            principal_role_blocked INTEGER NOT NULL DEFAULT 0,
            evidence_layer   TEXT NOT NULL
        );
        CREATE TABLE responsibility_assertion (
            responsibility_id TEXT PRIMARY KEY,
            episode_id       TEXT NOT NULL REFERENCES employment_episode(episode_id),
            responsibility   TEXT NOT NULL,
            exact_source_text TEXT,
            evidence_layer   TEXT NOT NULL
        );
        CREATE TABLE scheme_assertion (
            scheme_id        TEXT PRIMARY KEY,
            program_id       TEXT REFERENCES canonical_program(program_id),
            season           TEXT,
            side             TEXT NOT NULL,
            exact_source_text TEXT NOT NULL,
            normalized_family TEXT,
            normalization_version TEXT NOT NULL,
            valid_from       TEXT,
            valid_to         TEXT,
            evidence_layer   TEXT NOT NULL
        );
        CREATE TABLE assertion_support (
            assertion_id     TEXT NOT NULL,
            assertion_table  TEXT NOT NULL,
            observation_id   TEXT NOT NULL REFERENCES source_observation(observation_id),
            PRIMARY KEY (assertion_id, assertion_table, observation_id)
        );
        CREATE TABLE conflict (
            conflict_id      TEXT PRIMARY KEY,
            subject_kind     TEXT NOT NULL,
            subject_key      TEXT NOT NULL,
            reason           TEXT NOT NULL,
            left_assertion   TEXT,
            right_assertion  TEXT
        );
        CREATE TABLE adjudication (
            adjudication_id  TEXT PRIMARY KEY,
            conflict_id      TEXT NOT NULL REFERENCES conflict(conflict_id),
            decision         TEXT NOT NULL,
            decided_by       TEXT NOT NULL,
            basis            TEXT NOT NULL,
            decided_at_utc   TEXT NOT NULL
        );
        """,
    ),
    (
        3,
        """
        CREATE TABLE expected_cell (
            expected_cell_id TEXT PRIMARY KEY,
            program_id       TEXT NOT NULL,
            season           INTEGER NOT NULL,
            role_family      TEXT NOT NULL,
            era_band         TEXT NOT NULL,
            coverage_state   TEXT NOT NULL
        );
        CREATE TABLE lineage (
            lineage_id       TEXT PRIMARY KEY,
            downstream_kind  TEXT NOT NULL,
            downstream_id    TEXT NOT NULL,
            upstream_kind    TEXT NOT NULL,
            upstream_id      TEXT NOT NULL,
            relation         TEXT NOT NULL
        );
        CREATE INDEX idx_observation_file ON source_observation(source_file_id);
        CREATE INDEX idx_episode_person ON employment_episode(person_id);
        CREATE INDEX idx_episode_program ON employment_episode(program_id, season);
        CREATE INDEX idx_role_episode ON formal_role_assertion(episode_id);
        CREATE INDEX idx_support ON assertion_support(observation_id);
        """,
    ),
)


def stable_id(prefix: str, *parts: Any) -> str:
    """A deterministic, content-addressed identity.

    Replay must produce the same row identities from the same inputs, so no
    identity may come from a counter, a timestamp or an object address.
    """

    payload = "".join("" if part is None else str(part) for part in parts)
    return prefix + ":" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def apply_migrations(conn: sqlite3.Connection) -> list[int]:
    """Bring a database up to SCHEMA_VERSION, recording each step."""

    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migration ("
        " version INTEGER PRIMARY KEY, applied_at_utc TEXT NOT NULL)"
    )
    applied = {
        int(row[0]) for row in conn.execute("SELECT version FROM schema_migration")
    }
    ran: list[int] = []
    for version, script in MIGRATIONS:
        if version in applied:
            continue
        conn.executescript(script)
        conn.execute(
            "INSERT INTO schema_migration (version, applied_at_utc) VALUES (?, ?)",
            (version, datetime.now(timezone.utc).isoformat()),
        )
        ran.append(version)
    conn.commit()
    return ran


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """All-or-nothing. A partial import is a corrupted release.

    sqlite3's implicit transaction handling does not cover DDL or SELECTs,
    so the boundary is stated explicitly here rather than assumed.
    """

    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def open_release(path: Path, *, allow_existing: bool = False) -> sqlite3.Connection:
    """Open a NEW release database.

    A release is never built by unlinking its predecessor: predecessors are
    immutable, and deleting one to free a filename destroys the ability to
    compare two releases at row grain.
    """

    path = Path(path)
    if path.exists() and not allow_existing:
        raise CoachingReleaseError(
            "release path already exists; build a new release rather than "
            "overwriting or unlinking a predecessor: " + str(path)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_migrations(conn)
    return conn


def register_source_file(
    conn: sqlite3.Connection,
    path: Path,
    *,
    source_class: str,
    rights_state: str,
    acquisition_receipt: str | None = None,
    source_revision: str | None = None,
    retrieved_at_utc: str | None = None,
    decoded_sha256: str | None = None,
) -> str:
    """Record a real file, hashed here from its actual bytes."""

    path = Path(path)
    raw = path.read_bytes()
    raw_sha = hashlib.sha256(raw).hexdigest()
    source_file_id = stable_id("src", raw_sha, str(path))
    conn.execute(
        "INSERT OR IGNORE INTO source_file (source_file_id, path, raw_sha256, "
        "decoded_sha256, bytes, source_class, rights_state, acquisition_receipt, "
        "source_revision, retrieved_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            source_file_id,
            str(path),
            raw_sha,
            decoded_sha256,
            len(raw),
            source_class,
            rights_state,
            acquisition_receipt,
            source_revision,
            retrieved_at_utc,
        ),
    )
    return source_file_id


def add_observation(
    conn: sqlite3.Connection,
    *,
    source_file_id: str,
    locator: str,
    parser_identity: str,
    observed_text: str | None = None,
    observed_person: str | None = None,
    observed_title: str | None = None,
    observed_program: str | None = None,
    observed_season: str | None = None,
    evidence_layer: str = LAYER_OBSERVED,
) -> str:
    if evidence_layer not in EVIDENCE_LAYERS:
        raise CoachingReleaseError("unknown evidence layer: " + str(evidence_layer))
    observation_id = stable_id(
        "obs", source_file_id, locator, observed_person, observed_title
    )
    conn.execute(
        "INSERT OR IGNORE INTO source_observation (observation_id, source_file_id, "
        "locator, observed_text, observed_person, observed_title, observed_program, "
        "observed_season, parser_identity, evidence_layer) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            observation_id,
            source_file_id,
            locator,
            observed_text,
            observed_person,
            observed_title,
            observed_program,
            observed_season,
            parser_identity,
            evidence_layer,
        ),
    )
    return observation_id


def upsert_program(
    conn: sqlite3.Connection,
    program_id: str,
    *,
    display_name: str | None = None,
    classification: str | None = None,
    season: int | None = None,
) -> str:
    row = conn.execute(
        "SELECT first_season, last_season FROM canonical_program WHERE program_id = ?",
        (program_id,),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO canonical_program (program_id, display_name, "
            "classification, first_season, last_season) VALUES (?,?,?,?,?)",
            (program_id, display_name, classification, season, season),
        )
        return program_id
    if season is not None:
        first = row["first_season"]
        last = row["last_season"]
        conn.execute(
            "UPDATE canonical_program SET first_season = ?, last_season = ? "
            "WHERE program_id = ?",
            (
                season if first is None else min(int(first), season),
                season if last is None else max(int(last), season),
                program_id,
            ),
        )
    return program_id


def upsert_person(
    conn: sqlite3.Connection,
    canonical_name: str,
    *,
    identity_basis: str,
    aliases: Sequence[tuple[str, str]] = (),
) -> str:
    person_id = stable_id("person", canonical_name.casefold(), identity_basis)
    conn.execute(
        "INSERT OR IGNORE INTO canonical_person (person_id, canonical_name, "
        "identity_basis) VALUES (?,?,?)",
        (person_id, canonical_name, identity_basis),
    )
    for alias, kind in aliases:
        conn.execute(
            "INSERT OR IGNORE INTO person_alias (person_id, alias, alias_kind) "
            "VALUES (?,?,?)",
            (person_id, alias, kind),
        )
    return person_id


def add_episode(
    conn: sqlite3.Connection,
    *,
    person_id: str | None,
    program_id: str | None,
    season: str | None,
    date_precision: str,
    evidence_layer: str,
    valid_from: str | None = None,
    valid_to: str | None = None,
) -> str:
    if evidence_layer not in EVIDENCE_LAYERS:
        raise CoachingReleaseError("unknown evidence layer: " + str(evidence_layer))
    episode_id = stable_id("ep", person_id, program_id, season, valid_from, valid_to)
    conn.execute(
        "INSERT OR IGNORE INTO employment_episode (episode_id, person_id, "
        "program_id, season, valid_from, valid_to, date_precision, "
        "evidence_layer, pit_admitted) VALUES (?,?,?,?,?,?,?,?,0)",
        (
            episode_id,
            person_id,
            program_id,
            season,
            valid_from,
            valid_to,
            date_precision,
            evidence_layer,
        ),
    )
    return episode_id


def add_role(
    conn: sqlite3.Connection,
    *,
    episode_id: str,
    role_family: str,
    exact_title_text: str,
    qualifiers: Sequence[str],
    evidence_layer: str,
    principal_role_blocked: bool = False,
    supporting_observations: Sequence[str] = (),
) -> str:
    assertion_id = stable_id("role", episode_id, role_family, exact_title_text)
    conn.execute(
        "INSERT OR IGNORE INTO formal_role_assertion (assertion_id, episode_id, "
        "role_family, exact_title_text, qualifiers, principal_role_blocked, "
        "evidence_layer) VALUES (?,?,?,?,?,?,?)",
        (
            assertion_id,
            episode_id,
            role_family,
            exact_title_text,
            json.dumps(sorted(qualifiers)),
            1 if principal_role_blocked else 0,
            evidence_layer,
        ),
    )
    for observation_id in supporting_observations:
        link_support(conn, assertion_id, "formal_role_assertion", observation_id)
    return assertion_id


def link_support(
    conn: sqlite3.Connection,
    assertion_id: str,
    assertion_table: str,
    observation_id: str,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO assertion_support (assertion_id, assertion_table, "
        "observation_id) VALUES (?,?,?)",
        (assertion_id, assertion_table, observation_id),
    )
    conn.execute(
        "INSERT OR IGNORE INTO lineage (lineage_id, downstream_kind, downstream_id, "
        "upstream_kind, upstream_id, relation) VALUES (?,?,?,?,?,?)",
        (
            stable_id("lin", assertion_id, observation_id),
            assertion_table,
            assertion_id,
            "source_observation",
            observation_id,
            "SUPPORTED_BY",
        ),
    )


def record_conflict(
    conn: sqlite3.Connection,
    *,
    subject_kind: str,
    subject_key: str,
    reason: str,
    left_assertion: str | None = None,
    right_assertion: str | None = None,
) -> str:
    conflict_id = stable_id(
        "cfl", subject_kind, subject_key, reason, left_assertion, right_assertion
    )
    conn.execute(
        "INSERT OR IGNORE INTO conflict (conflict_id, subject_kind, subject_key, "
        "reason, left_assertion, right_assertion) VALUES (?,?,?,?,?,?)",
        (conflict_id, subject_kind, subject_key, reason, left_assertion, right_assertion),
    )
    return conflict_id


def record_adjudication(
    conn: sqlite3.Connection,
    *,
    conflict_id: str,
    decision: str,
    decided_by: str,
    basis: str,
    decided_at_utc: str | None = None,
) -> str:
    adjudication_id = stable_id("adj", conflict_id, decision, decided_by, basis)
    conn.execute(
        "INSERT OR IGNORE INTO adjudication (adjudication_id, conflict_id, decision, "
        "decided_by, basis, decided_at_utc) VALUES (?,?,?,?,?,?)",
        (
            adjudication_id,
            conflict_id,
            decision,
            decided_by,
            basis,
            decided_at_utc or datetime.now(timezone.utc).isoformat(),
        ),
    )
    return adjudication_id


def add_expected_cell(
    conn: sqlite3.Connection,
    *,
    program_id: str,
    season: int,
    role_family: str,
    era_band: str,
    coverage_state: str,
) -> str:
    cell_id = stable_id("cell", program_id, season, role_family)
    conn.execute(
        "INSERT OR IGNORE INTO expected_cell (expected_cell_id, program_id, season, "
        "role_family, era_band, coverage_state) VALUES (?,?,?,?,?,?)",
        (cell_id, program_id, season, role_family, era_band, coverage_state),
    )
    return cell_id


def release_row_identities(conn: sqlite3.Connection) -> dict[str, Any]:
    """The scientific row identities of this release, for replay comparison.

    Two builds of the same inputs must produce the same identities. Comparing
    a whole-file hash would fail on incidental byte differences and tell us
    nothing; comparing identities is what actually matters.
    """

    identities: dict[str, Any] = {}
    for table, column in (
        ("source_file", "source_file_id"),
        ("source_observation", "observation_id"),
        ("canonical_program", "program_id"),
        ("canonical_person", "person_id"),
        ("employment_episode", "episode_id"),
        ("formal_role_assertion", "assertion_id"),
        ("responsibility_assertion", "responsibility_id"),
        ("scheme_assertion", "scheme_id"),
        ("conflict", "conflict_id"),
        ("adjudication", "adjudication_id"),
        ("expected_cell", "expected_cell_id"),
        ("lineage", "lineage_id"),
    ):
        rows = sorted(
            str(row[0])
            for row in conn.execute(f"SELECT {column} FROM {table}")  # noqa: S608
        )
        identities[table] = {
            "count": len(rows),
            "identity_sha256": hashlib.sha256(
                json.dumps(rows).encode("utf-8")
            ).hexdigest(),
        }
    return identities


def layer_counts(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for table in (
        "source_observation",
        "employment_episode",
        "formal_role_assertion",
        "responsibility_assertion",
        "scheme_assertion",
    ):
        counts: dict[str, int] = {}
        for row in conn.execute(
            f"SELECT evidence_layer, COUNT(*) FROM {table} GROUP BY 1"  # noqa: S608
        ):
            counts[str(row[0])] = int(row[1])
        out[table] = counts
    return out


def unsupported_assertions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Promoted assertions with no supporting observation.

    This is the query that makes "source-driven" checkable rather than
    aspirational: if any row appears here, something was asserted that no
    source backs, and the release is not what it claims to be.
    """

    rows = conn.execute(
        """
        SELECT a.assertion_id, a.role_family, a.exact_title_text, a.evidence_layer
        FROM formal_role_assertion a
        LEFT JOIN assertion_support s
          ON s.assertion_id = a.assertion_id
         AND s.assertion_table = 'formal_role_assertion'
        WHERE s.observation_id IS NULL
        """
    ).fetchall()
    return [dict(row) for row in rows]


def append_release_manifest(
    manifest_path: Path,
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    """Append-only. A release manifest that can shrink is not a manifest."""

    manifest_path = Path(manifest_path)
    manifest: dict[str, Any]
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("kind") != RELEASE_KIND:
            raise CoachingReleaseError("release manifest kind mismatch")
    else:
        manifest = {"kind": RELEASE_KIND, "releases": []}
    existing = {row.get("release_id") for row in manifest["releases"]}
    if entry.get("release_id") in existing:
        return manifest
    manifest["releases"].append(dict(entry))
    manifest["release_count"] = len(manifest["releases"])
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def compare_releases(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> dict[str, Any]:
    """Row-identity comparison between two releases, table by table."""

    tables = sorted(set(left) | set(right))
    differences = []
    for table in tables:
        a = left.get(table) or {}
        b = right.get(table) or {}
        if a.get("identity_sha256") != b.get("identity_sha256"):
            differences.append(
                {
                    "table": table,
                    "left_count": a.get("count"),
                    "right_count": b.get("count"),
                    "left_identity": a.get("identity_sha256"),
                    "right_identity": b.get("identity_sha256"),
                }
            )
    return {
        "tables_compared": len(tables),
        "identical": not differences,
        "differences": differences,
    }
