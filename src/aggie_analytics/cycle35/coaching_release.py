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
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

SCHEMA_VERSION = 5
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
    (
        4,
        """
        CREATE TABLE person_identity_adjudication (
            adjudication_id  TEXT PRIMARY KEY,
            left_person_id   TEXT NOT NULL REFERENCES canonical_person(person_id),
            right_person_id  TEXT NOT NULL REFERENCES canonical_person(person_id),
            decision         TEXT NOT NULL,
            decided_by       TEXT NOT NULL,
            basis            TEXT NOT NULL,
            decided_at_utc   TEXT NOT NULL
        );
        CREATE INDEX idx_person_ident_left ON person_identity_adjudication(left_person_id);
        CREATE INDEX idx_person_ident_right ON person_identity_adjudication(right_person_id);
        """,
    ),
    (
        5,
        # An adjudication now says what KIND of time it carries. Rows that
        # already exist keep their value and are labelled as the build-clock
        # readings they are -- erasing them would destroy the evidence that
        # the fault was there, and relabelling them as event times would
        # assert something nobody decided.
        """
        ALTER TABLE adjudication ADD COLUMN decision_time_basis TEXT NOT NULL
            DEFAULT 'LEGACY_BUILD_CLOCK_NOT_AN_EVENT_TIME';
        ALTER TABLE person_identity_adjudication ADD COLUMN decision_time_basis
            TEXT NOT NULL DEFAULT 'LEGACY_BUILD_CLOCK_NOT_AN_EVENT_TIME';
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
    source_program_id: str | None = None,
) -> str:
    """Resolve or create the canonical_person this call's evidence refers to.

    Cycle #35 manager follow-up (20260920T224700Z): identity was previously
    keyed on (name, identity_basis) alone, so two DIFFERENT real people
    sharing a name under the SAME basis were structurally incapable of
    being represented as distinct rows -- every call collapsed to one
    person_id, and no merge-candidate could ever surface because nothing
    ever produced two rows to compare in the first place.

    `source_program_id` -- the program THIS call's evidence associates the
    person with -- is now part of the identity. A genuine namesake at a
    DIFFERENT program now gets a genuinely different person_id, which
    `person_identity_merge_candidates` can surface as a real candidate pair
    needing adjudication, the same mechanism already used across basis
    values now also applied within one. This does not fragment a real
    person's multi-program career by design: each ingestion pass generally
    observes a given person once per run (a snapshot at their current
    position, or one retrospective key), so the common case -- one person,
    one call -- is unaffected; a person's OWN later career move is exactly
    the kind of fact `record_person_identity_adjudication` is for, not
    something this function may silently assume either way.
    """

    person_id = stable_id(
        "person", canonical_name.casefold(), identity_basis, source_program_id or ""
    )
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


def add_scheme_assertion(
    conn: sqlite3.Connection,
    *,
    program_id: str | None,
    season: str | None,
    side: str,
    exact_source_text: str,
    normalized_family: str | None,
    normalization_version: str,
    valid_from: str | None = None,
    valid_to: str | None = None,
    evidence_layer: str = LAYER_CANDIDATE,
) -> str:
    """Record a scheme a source STATED, at the layer that source warrants.

    The exact source text is kept verbatim -- "[[Spread offense|Pro spread]]"
    is what the page said, and the normalised family is a reading of it, not
    a replacement for it. A scheme is never inferred from a coach's
    reputation and never promoted above the layer its source supports.
    """

    if evidence_layer not in EVIDENCE_LAYERS:
        raise CoachingReleaseError("unknown evidence layer: " + str(evidence_layer))
    if not str(exact_source_text or "").strip():
        raise CoachingReleaseError(
            "a scheme assertion needs the exact text its source stated"
        )
    if side not in {"OFFENSE", "DEFENSE"}:
        raise CoachingReleaseError("scheme side must be OFFENSE or DEFENSE")
    scheme_id = stable_id(
        "scheme", program_id, season, side, exact_source_text, normalization_version
    )
    conn.execute(
        "INSERT OR IGNORE INTO scheme_assertion (scheme_id, program_id, season, "
        "side, exact_source_text, normalized_family, normalization_version, "
        "valid_from, valid_to, evidence_layer) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            scheme_id,
            program_id,
            season,
            side,
            exact_source_text,
            normalized_family,
            normalization_version,
            valid_from,
            valid_to,
            evidence_layer,
        ),
    )
    return scheme_id


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


#: What kind of time an adjudication row carries. The distinction exists
#: because an adjudication is not always a decision made at a moment: a
#: standing rule applied by the build was settled when the rule was written,
#: so there is no event time for the run to record. Reading the clock there
#: does not find one, it invents one -- and an invented time is exactly what
#: made two builds of the same sources disagree.
OPERATOR_STATED_EVENT_TIME = "OPERATOR_STATED_EVENT_TIME"
STANDING_RULE_NO_EVENT_TIME = "STANDING_RULE_NO_EVENT_TIME"
#: Written only by migration 5, onto rows a previous build already stamped.
#: New code never produces it.
LEGACY_BUILD_CLOCK_NOT_AN_EVENT_TIME = "LEGACY_BUILD_CLOCK_NOT_AN_EVENT_TIME"

DECISION_TIME_BASES = frozenset(
    {
        OPERATOR_STATED_EVENT_TIME,
        STANDING_RULE_NO_EVENT_TIME,
        LEGACY_BUILD_CLOCK_NOT_AN_EVENT_TIME,
    }
)


def _decision_time(decided_at_utc: str | None) -> tuple[str, str]:
    """(decided_at_utc, decision_time_basis) for a decision being recorded.

    A caller that states a time is stating an event time. A caller that
    states none is applying a standing rule, and no time is manufactured on
    its behalf -- which is the whole repair. The build clock is deliberately
    unreachable from here.
    """

    stated = (decided_at_utc or "").strip()
    if stated:
        return stated, OPERATOR_STATED_EVENT_TIME
    return "", STANDING_RULE_NO_EVENT_TIME


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
    decided_at, time_basis = _decision_time(decided_at_utc)
    conn.execute(
        "INSERT OR IGNORE INTO adjudication (adjudication_id, conflict_id, decision, "
        "decided_by, basis, decided_at_utc, decision_time_basis) VALUES (?,?,?,?,?,?,?)",
        (
            adjudication_id,
            conflict_id,
            decision,
            decided_by,
            basis,
            decided_at,
            time_basis,
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


#: What an expected cell's coverage can be, once the release has its
#: evidence. UNSETTLED is what `add_expected_cell` writes at creation time,
#: before anything has been ingested; a release still carrying it has not
#: had `settle_expected_cell_coverage` run over it, and that is a different
#: statement from "nothing is covered".
COVERAGE_UNSETTLED = "EXPECTED_NOT_YET_COVERED"
COVERAGE_CONFIRMED = "COVERED_BY_CONFIRMED_ASSERTION"
COVERAGE_CANDIDATE = "COVERED_BY_CANDIDATE_OBSERVATION_ONLY"
COVERAGE_NONE = "NO_EVIDENCE_ACQUIRED_FOR_THIS_CELL"


def stated_season(value: Any) -> int | None:
    """A season a source actually states. "CURRENT" is not a season."""

    text = str(value or "").strip()
    return int(text) if len(text) == 4 and text.isdigit() else None


def settle_expected_cell_coverage(
    conn: sqlite3.Connection,
    *,
    role_families: Callable[[str], Iterable[str]],
    core_roles: Iterable[str],
) -> dict[str, int]:
    """Write each expected cell's coverage into the release itself.

    `add_expected_cell` writes COVERAGE_UNSETTLED when the cell is created,
    because at that moment no evidence has been ingested yet. Without this
    pass the release ships still saying so, while the coverage it really
    has is computed later and written to a file beside it -- so the
    database and its companion artifact answer the same question
    differently, and the database is the one that gets shipped.

    Three states, and the middle one has to keep existing. An unpromoted
    candidate row is evidence that really was acquired: calling it "no
    evidence" would erase acquisition work, and calling it "covered" would
    promote a single unverified source to a confirmed fact.

    `role_families` is injected so this module does not depend on a
    particular title taxonomy. Callers pass the same mapping the builder
    uses; nothing here maps a title by hand.
    """

    core = frozenset(core_roles)
    cursor = conn.cursor()

    confirmed: set[tuple[str, int, str]] = set()
    for program_id, season, role_family in cursor.execute(
        "SELECT e.program_id, e.season, a.role_family FROM employment_episode e "
        "JOIN formal_role_assertion a ON a.episode_id = e.episode_id "
        "WHERE a.evidence_layer = ?",
        (LAYER_OFFICIAL,),
    ):
        year = stated_season(season)
        if year is not None and role_family in core:
            confirmed.add((str(program_id), year, str(role_family)))

    candidate: set[tuple[str, int, str]] = set()
    for program_id, season, title in cursor.execute(
        "SELECT observed_program, observed_season, observed_title FROM source_observation"
    ):
        year = stated_season(season)
        if year is None:
            continue
        for family in role_families(str(title or "")):
            if family in core:
                candidate.add((str(program_id or ""), year, str(family)))

    settled: dict[str, int] = {
        COVERAGE_CONFIRMED: 0,
        COVERAGE_CANDIDATE: 0,
        COVERAGE_NONE: 0,
    }
    updates: list[tuple[str, str]] = []
    for cell_id, program_id, season, role_family in cursor.execute(
        "SELECT expected_cell_id, program_id, season, role_family FROM expected_cell"
    ).fetchall():
        key = (str(program_id), int(season), str(role_family))
        if key in confirmed:
            state = COVERAGE_CONFIRMED
        elif key in candidate:
            state = COVERAGE_CANDIDATE
        else:
            state = COVERAGE_NONE
        settled[state] += 1
        updates.append((state, str(cell_id)))

    conn.executemany(
        "UPDATE expected_cell SET coverage_state = ? WHERE expected_cell_id = ?",
        updates,
    )
    return settled


#: Decisions `record_person_identity_adjudication` accepts. UNRESOLVED_IDENTITY
#: is a first-class outcome, not a placeholder for a decision not yet made --
#: it is what an adjudicator records when the available evidence genuinely
#: does not settle the question either way.
PERSON_IDENTITY_DECISIONS = frozenset(
    {"MERGED_SAME_PERSON", "DISTINCT_NAMESAKES", "UNRESOLVED_IDENTITY"}
)


def person_identity_merge_candidates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Pairs of `canonical_person` rows that share a name but were split by
    `upsert_person`'s (name, identity_basis) keying -- with the evidence an
    adjudicator needs, never a verdict.

    MF35-04: `upsert_person` is content-addressed on `(canonical_name.casefold(),
    identity_basis, source_program_id)`, so the SAME real person recorded
    once from an official staff page and once from a wiki infobox -- or
    twice under the SAME basis at two different programs -- gets two
    different `person_id`s, and a genuinely different person who happens to
    share a name is indistinguishable from either split by `person_id`
    alone. Neither case may be resolved by this function -- same name is
    not proof of either answer. What it CAN compute from the data already
    on hand:

    * `shared_program_ids` -- programs where both identities have an
      episode. A single person coaching the same program under two source
      classes in the same or adjacent seasons is strong same-person
      evidence; this function reports the fact and lets the caller judge it.
    * `overlapping_season_different_program` -- both identities have an
      episode in the EXACT SAME season string at DIFFERENT programs. Real
      people cannot hold two simultaneous on-field coordinator jobs, so this
      is evidence pointing toward DISTINCT_NAMESAKES (or a data error in one
      side), not toward a merge.
    * `role_families_overlap` -- whether the two identities share any
      `role_family` value across their episodes, which is at least
      consistent with (not proof of) one coordinator's career.

    Pairs already recorded in `person_identity_adjudication` (in either
    left/right order) are excluded -- an adjudicator's decision is not
    re-litigated by simply re-running this query.
    """

    people = conn.execute(
        "SELECT person_id, canonical_name, identity_basis FROM canonical_person"
    ).fetchall()
    by_name: dict[str, list[sqlite3.Row]] = {}
    for row in people:
        key = " ".join(str(row["canonical_name"] or "").split()).casefold()
        by_name.setdefault(key, []).append(row)

    decided_pairs: set[frozenset[str]] = set()
    for row in conn.execute(
        "SELECT left_person_id, right_person_id FROM person_identity_adjudication"
    ):
        decided_pairs.add(frozenset((row["left_person_id"], row["right_person_id"])))

    def episodes_for(person_id: str) -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT program_id, season, role_family "
            "FROM employment_episode e "
            "LEFT JOIN formal_role_assertion a ON a.episode_id = e.episode_id "
            "WHERE e.person_id = ?",
            (person_id,),
        ).fetchall()

    candidates: list[dict[str, Any]] = []
    for rows in by_name.values():
        if len(rows) < 2:
            continue
        # Any 2+ distinct person_id rows sharing a normalized name are a
        # candidate pair -- whether they differ by identity_basis, by
        # source_program_id within one basis, or both. Before
        # source_program_id was part of the identity, two same-basis rows
        # could never coexist (upsert_person always collapsed them), so
        # this used to only fire across bases; that is no longer true, and
        # restricting it to cross-basis pairs would silently exclude the
        # exact case this repair exists to catch.
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                left, right = rows[i], rows[j]
                pair_key = frozenset((left["person_id"], right["person_id"]))
                if pair_key in decided_pairs:
                    continue
                left_episodes = episodes_for(left["person_id"])
                right_episodes = episodes_for(right["person_id"])
                left_programs = {e["program_id"] for e in left_episodes if e["program_id"]}
                right_programs = {e["program_id"] for e in right_episodes if e["program_id"]}
                left_families = {e["role_family"] for e in left_episodes if e["role_family"]}
                right_families = {e["role_family"] for e in right_episodes if e["role_family"]}
                overlapping_season_conflict = any(
                    le["season"] == re["season"] and le["program_id"] != re["program_id"]
                    for le in left_episodes
                    for re in right_episodes
                    if le["season"] and re["season"]
                )
                candidates.append(
                    {
                        "left_person_id": left["person_id"],
                        "right_person_id": right["person_id"],
                        "canonical_name": left["canonical_name"],
                        "left_identity_basis": left["identity_basis"],
                        "right_identity_basis": right["identity_basis"],
                        "shared_program_ids": sorted(left_programs & right_programs),
                        "role_families_overlap": bool(left_families & right_families),
                        "overlapping_season_different_program": overlapping_season_conflict,
                    }
                )
    return candidates


def record_person_identity_adjudication(
    conn: sqlite3.Connection,
    *,
    left_person_id: str,
    right_person_id: str,
    decision: str,
    decided_by: str,
    basis: str,
    decided_at_utc: str | None = None,
) -> str:
    """Record a human/operator decision about a candidate pair.

    MF35-04: this is the only way a merge or a namesake determination enters
    the release -- nothing in this module infers or applies either decision
    on its own. `left_person_id`/`right_person_id` are recorded in the order
    given; a decision is order-independent for lookup (see
    `person_identity_merge_candidates`'s use of `frozenset`).
    """

    if decision not in PERSON_IDENTITY_DECISIONS:
        raise CoachingReleaseError("unknown person identity decision: " + str(decision))
    if not basis or not basis.strip():
        raise CoachingReleaseError("a person identity decision requires a stated basis")
    adjudication_id = stable_id(
        "pident", left_person_id, right_person_id, decision, decided_by, basis
    )
    decided_at, time_basis = _decision_time(decided_at_utc)
    conn.execute(
        "INSERT OR IGNORE INTO person_identity_adjudication (adjudication_id, "
        "left_person_id, right_person_id, decision, decided_by, basis, "
        "decided_at_utc, decision_time_basis) VALUES (?,?,?,?,?,?,?,?)",
        (
            adjudication_id,
            left_person_id,
            right_person_id,
            decision,
            decided_by,
            basis,
            decided_at,
            time_basis,
        ),
    )
    return adjudication_id


def person_identity_adjudications(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every recorded person-identity decision, for audit and reporting."""

    # Ordered by identity, not by time: a standing-rule decision has no
    # event time, so decided_at_utc no longer orders these rows at all.
    rows = conn.execute(
        "SELECT * FROM person_identity_adjudication ORDER BY adjudication_id"
    ).fetchall()
    return [dict(row) for row in rows]


#: Columns excluded from `release_row_identities`'s content hash, per table,
#: because they are proven to be non-scientific SQLite/runtime artifacts
#: rather than believed facts. Empty for every table in this schema: no
#: table below has an autoincrement rowid or a column this module writes
#: from wall-clock time on every build. `adjudication.decided_at_utc` looks
#: like a candidate but is NOT excluded -- who decided what, and when, is
#: part of the adjudication record itself, not incidental noise. A column
#: may be added here only when it is independently shown to be incidental;
#: this set must never be used to make a real disagreement disappear.
#:
#: That column used to differ on 26 rows between builds, and this is where
#: the fix did NOT go. The rows differed because they recorded a build clock
#: reading as though it were a decision time; they were repaired by not
#: recording a time nobody had (see `_decision_time`), so the comparison
#: still looks at the column and now finds it equal. Excluding it would have
#: silenced the report while leaving the fabricated value in the release.
INCIDENTAL_EXCLUDED_COLUMNS: dict[str, frozenset[str]] = {}

#: Every table `release_row_identities` compares, with the column(s) that
#: uniquely and deterministically order its rows. MF35-03: this now also
#: covers `assertion_support` and `person_alias`, the two link/alias tables
#: the prior version omitted entirely -- a mutation confined to either of
#: those tables previously produced no detectable difference at all.
_CONTENT_TABLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("source_file", ("source_file_id",)),
    ("source_observation", ("observation_id",)),
    ("canonical_program", ("program_id",)),
    ("canonical_person", ("person_id",)),
    ("person_alias", ("person_id", "alias")),
    ("employment_episode", ("episode_id",)),
    ("formal_role_assertion", ("assertion_id",)),
    ("responsibility_assertion", ("responsibility_id",)),
    ("scheme_assertion", ("scheme_id",)),
    ("assertion_support", ("assertion_id", "assertion_table", "observation_id")),
    ("conflict", ("conflict_id",)),
    ("adjudication", ("adjudication_id",)),
    ("expected_cell", ("expected_cell_id",)),
    ("lineage", ("lineage_id",)),
    ("person_identity_adjudication", ("adjudication_id",)),
)


def release_row_identities(conn: sqlite3.Connection) -> dict[str, Any]:
    """The scientific CONTENT identities of this release, for replay comparison.

    MF35-03 repair: this previously hashed only each table's primary-key
    column, sorted -- so a row whose non-key scientific fields changed (an
    `exact_title_text`, a `role_family`, an `evidence_layer`) kept the exact
    same identity, and a manager RAM-clone-and-mutate test proved
    `compare_releases` reported the two releases identical when they were
    not. Every column of every row is now part of the hash (see
    `INCIDENTAL_EXCLUDED_COLUMNS`, currently empty, for the only mechanism
    that may exclude a column, and only when it is proven incidental), and
    `assertion_support`/`person_alias` are now covered.

    Two builds of the same inputs must still produce the same identities,
    which is why every row is serialized in a fixed column order and sorted
    by its own natural key -- SQLite's row iteration order is not a promise.
    """

    identities: dict[str, Any] = {}
    cursor = conn.cursor()
    for table, sort_columns in _CONTENT_TABLES:
        cursor.execute(f"PRAGMA table_info({table})")  # noqa: S608
        all_columns = [str(row[1]) for row in cursor.fetchall()]
        excluded = INCIDENTAL_EXCLUDED_COLUMNS.get(table, frozenset())
        columns = [c for c in all_columns if c not in excluded]
        column_list = ", ".join(columns)
        cursor.execute(f"SELECT {column_list} FROM {table}")  # noqa: S608
        rows = [list(row) for row in cursor.fetchall()]
        sort_index = [columns.index(c) for c in sort_columns]
        rows.sort(key=lambda r: ["" if r[i] is None else str(r[i]) for i in sort_index])
        identities[table] = {
            "count": len(rows),
            "columns": columns,
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


def assertions_missing_evidence_link(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Promoted assertions with no supporting observation LINK at all.

    This is the query that makes "source-driven" checkable rather than
    aspirational: if any row appears here, something was asserted that no
    source is even linked to, and the release is not what it claims to be.

    MF35-03 (naming correction): this function was previously named
    `unsupported_assertions`, which overstated what it proves. It proves a
    LINK exists in `assertion_support` -- nothing about whether the linked
    observation's own content actually entails the asserted fact. A manager
    counterexample mutated an assertion's `exact_title_text`/`role_family`
    while leaving its `assertion_support` row untouched; this check
    correctly found nothing wrong, because by ITS definition nothing was.
    Use `assertions_not_entailed_by_linked_observations` for the stronger,
    independent claim.
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


def _normalize_name(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


#: Independent role-family keyword reference. Deliberately NOT derived from
#: or calling into `aggie_analytics.cycle33.role_taxonomy` (the module the
#: ingest pipeline's own classifier -- `assignments_from_title` -- uses): a
#: shared bug between producer and checker would otherwise agree with
#: itself and never surface. This is hand-curated from the role families
#: actually observed in a real national release, using plain domain
#: knowledge, not by reading role_taxonomy.py's pattern library. It is
#: deliberately simpler and more conservative than that library -- it does
#: not need to reproduce every abbreviation or synonym, only to answer,
#: independently, whether the literal title text contains unambiguous
#: language consistent with the specific role being claimed.
#: Hint phrases below 4 characters are matched as whole words (`\bqb\b`),
#: not bare substrings -- see `_hint_matches`. Longer phrases are matched as
#: plain substrings.
_HEAD_COACH_HINTS = (
    "head coach",
    "head football coach",
    "director of football",
    "chair in football",
    "endowed football coach",
)
_INDEPENDENT_ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "head_coach": _HEAD_COACH_HINTS,
    "assistant_head_coach": _HEAD_COACH_HINTS,
    "offensive_coordinator": (
        "offensive coordinator", "off. coor", "off. coordinator",
        "director of offense", "oc",
    ),
    "defensive_coordinator": (
        "defensive coordinator", "def. coor", "def. coordinator",
        "director of defense", "dc",
    ),
    "special_teams_coordinator": ("special teams",),
    "run_game_coordinator": ("run game", "running game"),
    "pass_game_coordinator": ("pass game", "passing game"),
    "quarterbacks": ("quarterback", "qb"),
    "running_backs": ("running back",),
    "fullbacks": ("fullback",),
    "wide_receivers": ("wide receiver", "wide reciever", "wr"),
    "receivers": ("receiver", "reciever"),
    "tight_ends": ("tight end",),
    "offensive_line": ("offensive line",),
    "linebackers": ("linebacker",),
    "inside_linebackers": ("inside linebacker", "ilb"),
    "outside_linebackers": ("outside linebacker", "olb"),
    "defensive_line": ("defensive line",),
    "defensive_tackles": ("defensive tackle",),
    "defensive_ends": ("defensive end",),
    "defensive_backs": ("defensive back",),
    "cornerbacks": ("cornerback",),
    "safeties": ("safet",),  # stem: matches both "safety" and "safeties"
    "nickels": ("nickel",),
    "secondary": ("secondary",),
    "special_teams_staff": ("special teams",),
    "player_personnel": ("player personnel", "personnel", "recruiting"),
    "recruiting_staff": ("recruiting",),
    "sports_performance": (
        "sports performance", "athletic performance", "strength", "conditioning",
    ),
    "chief_of_staff": ("chief of staff",),
    "athletic_director": ("athletic director",),
}


def _hint_matches(hint: str, text: str) -> bool:
    """Short hints (<=3 chars, e.g. "qb", "oc", "dc", "olb") are matched as
    whole words so they cannot accidentally fire inside an unrelated longer
    word; longer phrase hints are matched as plain substrings."""

    if len(hint) <= 3:
        return re.search(r"\b" + re.escape(hint) + r"\b", text) is not None
    return hint in text

#: role_family values that are themselves honest "could not classify"
#: placeholders (assigned when a title genuinely matched nothing), never a
#: substantive claim that needs its own textual support.
_UNCLASSIFIED_ROLE_PLACEHOLDERS = frozenset(
    {"UNSPECIFIED_ASSISTANT", "unmapped_title_review_required", "assistant_unspecified"}
)


def _independent_role_plausible(role_family: str, title_lowered: str) -> bool:
    if role_family in _UNCLASSIFIED_ROLE_PLACEHOLDERS:
        return True
    # Some evidence sources (e.g. an infobox reporting a structured
    # "head_coach: <name>" field rather than a prose title) record the
    # observed "title" as the role code itself, underscores and all. A
    # role trivially equal to its own label is not a claim that needs
    # separate textual corroboration; normalize both sides the same way
    # before comparing or keyword-matching.
    normalized_title = title_lowered.replace("_", " ")
    normalized_role = str(role_family).replace("_", " ").casefold()
    if normalized_title.strip() == normalized_role.strip():
        return True
    hints = _INDEPENDENT_ROLE_KEYWORDS.get(role_family, (normalized_role,))
    return any(_hint_matches(hint, normalized_title) for hint in hints)


#: Independent qualifier keyword reference. Same independence rationale as
#: `_INDEPENDENT_ROLE_KEYWORDS`: implemented as plain substring checks
#: rather than role_taxonomy.py's compiled regex patterns, so the two
#: implementations can disagree instead of failing the same way together.
_INDEPENDENT_QUALIFIER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "CO": ("co-", "co defensive", "co offensive", "co head", "co-defensive", "co-offensive"),
    "INTERIM": ("interim",),
    "ACTING": ("acting",),
    "ASSISTANT": ("assistant", "asst.", "asst "),
    "ASSOCIATE": ("associate", "assoc.", "assoc "),
    "DEPUTY": ("deputy",),
    "SENIOR": ("senior", "sr.", "sr "),
    "VOLUNTEER": ("volunteer",),
    "GRADUATE": ("graduate",),
    "STUDENT": ("student",),
}


def _independent_qualifier_plausible(qualifier: str, title_lowered: str) -> bool:
    hints = _INDEPENDENT_QUALIFIER_KEYWORDS.get(qualifier)
    if hints is None:
        # An unrecognized qualifier code has no keyword to check against --
        # that is itself suspicious, not something to wave through silently.
        return False
    return any(hint in title_lowered for hint in hints)


#: source_class values capable of supporting an OFFICIAL_PRIMARY_CONFIRMED
#: assertion. A retrospective, user-compiled, or predecessor-transcription
#: source can be a real CANDIDATE or CORROBORATED contribution, but it is
#: not a primary source confirming the fact, and an assertion may not claim
#: stronger evidence than what actually backs it.
_OFFICIAL_CAPABLE_SOURCE_CLASSES = frozenset({"OFFICIAL_STAFF_HTML"})


def assertions_not_entailed_by_linked_observations(
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """Linked assertions whose content is NOT actually entailed by any of
    their linked observations, checked against an independently
    implemented reference -- not the ingest pipeline's own classifier.

    MF35-03 / Cycle #35 manager follow-up (20260920T224700Z): a row in
    `assertion_support` proves a relationship LINK exists; it does not
    prove the linked observation's own recorded text supports the specific
    fact the assertion claims, and reusing the ingest-time classifier
    cannot independently catch a producer bug both would share. This now
    checks the complete fact the finding named:

    * literal title entailment -- `exact_title_text` must equal, once
      whitespace-normalized, at least one linked observation's own
      `observed_title`.
    * subject/program/season binding -- among the title-matching
      observations, at least one must ALSO name the SAME person (by
      canonical name or a recorded alias), the same program_id and the
      same season as the assertion's own episode. A linked observation
      about a different person, program or season proves nothing about
      THIS assertion, however similar its title text reads.
    * role-family plausibility -- the claimed `role_family` must be
      independently plausible from the title text (see
      `_independent_role_plausible`), covering position roles as well as
      HC/OC/DC, and explicitly rejecting a specific role claim when the
      title carries no recognizable coaching-role language at all. An
      honest "could not classify" placeholder role is never itself
      flagged.
    * qualifier plausibility -- every claimed qualifier (e.g. "CO") must
      be independently detectable in the title text; a qualifier with no
      textual support is a claim the release cannot back.
    * evidence-layer authority -- an assertion recorded at
      OFFICIAL_PRIMARY_CONFIRMED must be supported by at least one
      subject-matching observation whose OWN source file is of a class
      capable of primary confirmation (see
      `_OFFICIAL_CAPABLE_SOURCE_CLASSES`); a retrospective or user-compiled
      source cannot promote itself to official authority by being linked.

    An assertion with NO linked observation at all is out of scope here --
    that is `assertions_missing_evidence_link`'s claim, not this one's.
    """

    rows = conn.execute(
        """
        SELECT a.assertion_id, a.role_family, a.exact_title_text,
               a.qualifiers, a.evidence_layer AS assertion_evidence_layer,
               e.episode_id, e.person_id, e.program_id, e.season,
               o.observation_id, o.observed_title, o.observed_person,
               o.observed_program, o.observed_season,
               sf.source_class
        FROM formal_role_assertion a
        JOIN employment_episode e ON e.episode_id = a.episode_id
        JOIN assertion_support s
          ON s.assertion_id = a.assertion_id
         AND s.assertion_table = 'formal_role_assertion'
        JOIN source_observation o ON o.observation_id = s.observation_id
        LEFT JOIN source_file sf ON sf.source_file_id = o.source_file_id
        """
    ).fetchall()

    names_by_person: dict[str, set[str]] = {}
    for row in conn.execute("SELECT person_id, canonical_name FROM canonical_person"):
        names_by_person.setdefault(str(row["person_id"]), set()).add(
            _normalize_name(row["canonical_name"])
        )
    for row in conn.execute("SELECT person_id, alias FROM person_alias"):
        names_by_person.setdefault(str(row["person_id"]), set()).add(
            _normalize_name(row["alias"])
        )

    by_assertion: dict[str, dict[str, Any]] = {}
    links: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        assertion_id = str(row["assertion_id"])
        by_assertion[assertion_id] = {
            "assertion_id": assertion_id,
            "role_family": row["role_family"],
            "exact_title_text": row["exact_title_text"],
            "qualifiers": row["qualifiers"],
            "evidence_layer": row["assertion_evidence_layer"],
            "person_id": row["person_id"],
            "program_id": row["program_id"],
            "season": row["season"],
        }
        links.setdefault(assertion_id, []).append(row)

    findings: list[dict[str, Any]] = []
    for assertion_id, assertion in by_assertion.items():
        exact_title_text = str(assertion["exact_title_text"] or "").strip()
        observations = links.get(assertion_id, [])
        reasons: list[str] = []

        title_matching = [
            o for o in observations
            if str(o["observed_title"] or "").strip() == exact_title_text
        ]
        if not title_matching:
            reasons.append("EXACT_TITLE_TEXT_NOT_OBSERVED_IN_ANY_LINKED_OBSERVATION")
            findings.append({**assertion, "reasons": reasons})
            continue

        person_names = names_by_person.get(str(assertion["person_id"]), set())
        subject_matching = [
            o for o in title_matching
            if _normalize_name(o["observed_person"]) in person_names
            and str(o["observed_program"] or "") == str(assertion["program_id"] or "")
            and str(o["observed_season"] or "") == str(assertion["season"] or "")
        ]
        if not subject_matching:
            reasons.append(
                "SUBJECT_PROGRAM_SEASON_NOT_ENTAILED_BY_ANY_LINKED_OBSERVATION"
            )
            # A title match with the wrong subject says nothing reliable
            # about role/qualifier plausibility for THIS assertion either,
            # so those checks fall back to whatever title-matching evidence
            # exists rather than evidence already proven to be about
            # someone/something else.
            evidence_for_role_checks = title_matching
        else:
            evidence_for_role_checks = subject_matching

        title_lowered = exact_title_text.casefold()
        role_family = str(assertion["role_family"] or "")
        if not _independent_role_plausible(role_family, title_lowered):
            reasons.append("ROLE_FAMILY_NOT_DERIVABLE_FROM_EXACT_TITLE_TEXT")

        try:
            claimed_qualifiers = json.loads(assertion.get("qualifiers") or "[]")
        except (TypeError, ValueError):
            claimed_qualifiers = []
        unsupported_qualifiers = [
            q for q in claimed_qualifiers
            if not _independent_qualifier_plausible(str(q), title_lowered)
        ]
        if unsupported_qualifiers:
            reasons.append("QUALIFIERS_NOT_DERIVABLE_FROM_EXACT_TITLE_TEXT")

        if assertion["evidence_layer"] == LAYER_OFFICIAL:
            official_capable = any(
                o["source_class"] in _OFFICIAL_CAPABLE_SOURCE_CLASSES
                for o in evidence_for_role_checks
            )
            if not official_capable:
                reasons.append("EVIDENCE_LAYER_EXCEEDS_SOURCE_AUTHORITY")

        if reasons:
            findings.append({**assertion, "reasons": reasons})
    return findings


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
