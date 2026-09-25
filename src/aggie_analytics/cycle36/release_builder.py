"""Build the Cycle #36 national research release as a queryable database.

TP36-03/04/11. Everything here comes from the repaired upstreams:

* membership and the year-by-year denominator from ``c36_04`` -- including
  the restored 2024 and 2025 seasons;
* the alias crosswalk, with its effective dates and its refused collisions;
* every staff observation from ``c36_05``, with its raw title, its versioned
  role decomposition and its record-scoped season;
* every scheme claim from ``c36_06``, admitted or retained with a reason.

Three properties the release must have, and which the builder enforces
rather than asserts:

1. **Counts come from rows.** Every coverage number is a ``SELECT`` over the
   delivered tables. A JSON beside the database cannot overrule it.
2. **Determinism at scientific grain.** The same frozen inputs produce the
   same tables. Audit timestamps live in their own table so a replay can
   compare content without being defeated by the clock.
3. **Uncertainty survives.** Unknown seasons, unresolved programs, competing
   claims, candidate tiers and out-of-population identities are rows, not
   omissions.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from aggie_analytics.cycle36.jsonl_io import read_jsonl_strict

RELEASE_VERSION = "BAS-CYCLE36-NATIONAL-RELEASE-v36.1"

#: Core roles the HC/OC/DC matrix is defined over. The broader staff
#: denominator is reported separately and never folded into this one.
CORE_ROLES = ("head_coach", "offensive_coordinator", "defensive_coordinator")

SCHEMA = """
CREATE TABLE release_identity (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE source_file (
    source_file_id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    sha256 TEXT,
    bytes INTEGER,
    source_class TEXT NOT NULL,
    exists_at_build INTEGER NOT NULL
);
CREATE TABLE canonical_program (
    program_id TEXT PRIMARY KEY,
    source_namespace TEXT NOT NULL,
    source_entity_id TEXT NOT NULL,
    display_names TEXT NOT NULL,
    in_football_population INTEGER NOT NULL
);
CREATE TABLE program_alias (
    alias_id INTEGER PRIMARY KEY,
    program_id TEXT NOT NULL REFERENCES canonical_program(program_id),
    original_alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    alias_basis TEXT NOT NULL,
    effective_state TEXT NOT NULL,
    effective_start TEXT,
    effective_end TEXT,
    rename_source_url TEXT,
    source_payload_sha256 TEXT
);
CREATE TABLE alias_collision (
    collision_id INTEGER PRIMARY KEY,
    normalized_alias TEXT NOT NULL,
    match_basis TEXT NOT NULL,
    program_ids TEXT NOT NULL,
    disposition TEXT NOT NULL
);
CREATE TABLE program_season_membership (
    membership_id INTEGER PRIMARY KEY,
    program_id TEXT NOT NULL REFERENCES canonical_program(program_id),
    season INTEGER NOT NULL,
    classification TEXT,
    classification_bucket TEXT NOT NULL,
    conference TEXT,
    era TEXT,
    membership_authority TEXT NOT NULL,
    payload_sha256 TEXT,
    request_identity_sha256 TEXT,
    UNIQUE (program_id, season)
);
CREATE TABLE season_population (
    season INTEGER PRIMARY KEY,
    programs INTEGER NOT NULL,
    fbs INTEGER NOT NULL,
    fcs INTEGER NOT NULL,
    pre_classification INTEGER NOT NULL,
    other_division INTEGER NOT NULL,
    unknown INTEGER NOT NULL,
    state TEXT NOT NULL
);
CREATE TABLE staff_observation (
    observation_id INTEGER PRIMARY KEY,
    capture_path TEXT NOT NULL,
    payload_sha256 TEXT,
    program_id TEXT,
    display_name TEXT,
    person TEXT NOT NULL,
    source_title TEXT NOT NULL,
    record_selector TEXT,
    person_body_offset INTEGER,
    person_record_bound INTEGER NOT NULL,
    role_claim_supported INTEGER NOT NULL,
    reject_reason TEXT,
    evidence_tier TEXT NOT NULL,
    season INTEGER,
    season_state TEXT NOT NULL,
    source_class TEXT NOT NULL,
    pit_admitted INTEGER NOT NULL
);
CREATE TABLE staff_role_assignment (
    assignment_id INTEGER PRIMARY KEY,
    observation_id INTEGER NOT NULL REFERENCES staff_observation(observation_id),
    role_code TEXT NOT NULL,
    unit TEXT NOT NULL,
    qualifiers TEXT NOT NULL,
    occupancy TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    is_core_role INTEGER NOT NULL,
    play_caller_inferred INTEGER NOT NULL
);
CREATE TABLE scheme_assertion (
    scheme_assertion_id INTEGER PRIMARY KEY,
    program_id TEXT,
    season INTEGER,
    side TEXT NOT NULL,
    source_text TEXT,
    normalized_families TEXT NOT NULL,
    source_disposition TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_tier TEXT NOT NULL,
    official_corroboration TEXT,
    page_title TEXT,
    wikimedia_revision TEXT,
    pit_admitted INTEGER NOT NULL,
    inferred_from_title INTEGER NOT NULL
);
CREATE TABLE scheme_conflict (
    conflict_id INTEGER PRIMARY KEY,
    page_title TEXT NOT NULL,
    season INTEGER,
    side TEXT NOT NULL,
    conflict_texts TEXT NOT NULL,
    program_resolution_state TEXT NOT NULL
);
CREATE TABLE responsibility_assertion (
    responsibility_id INTEGER PRIMARY KEY,
    person TEXT,
    program_id TEXT,
    season INTEGER,
    source_title TEXT NOT NULL,
    evidence_code TEXT NOT NULL,
    disposition TEXT NOT NULL,
    inferred_from_role_title INTEGER NOT NULL,
    pit_admitted INTEGER NOT NULL
);
CREATE TABLE core_role_cell (
    cell_id INTEGER PRIMARY KEY,
    program_id TEXT NOT NULL REFERENCES canonical_program(program_id),
    season INTEGER NOT NULL,
    role_code TEXT NOT NULL,
    coverage_state TEXT NOT NULL,
    observations INTEGER NOT NULL,
    UNIQUE (program_id, season, role_code)
);
CREATE TABLE coverage_summary (
    grain TEXT NOT NULL,
    bucket TEXT NOT NULL,
    value INTEGER NOT NULL,
    PRIMARY KEY (grain, bucket)
);
CREATE TABLE user_corpus_cell (
    user_cell_id INTEGER PRIMARY KEY,
    source_class TEXT NOT NULL,
    season INTEGER,
    team_as_written TEXT NOT NULL,
    subdivision_as_written TEXT,
    role_column TEXT,
    person_as_written TEXT,
    source_title_as_written TEXT,
    canonical_program_id TEXT,
    program_resolution_state TEXT NOT NULL,
    evidence_tier TEXT NOT NULL,
    verified INTEGER NOT NULL,
    pit_admitted INTEGER NOT NULL
);
CREATE TABLE career_episode (
    career_episode_id INTEGER PRIMARY KEY,
    span_id TEXT,
    pageid TEXT,
    page_title TEXT,
    wikidata_qid TEXT,
    wikimedia_revision TEXT,
    episode_index INTEGER NOT NULL,
    person_display_name TEXT NOT NULL,
    employer_raw TEXT NOT NULL,
    employer_resolution_state TEXT NOT NULL,
    employer_program_id TEXT,
    source_title TEXT,
    role_codes TEXT NOT NULL,
    start_year INTEGER,
    end_year INTEGER,
    ongoing INTEGER NOT NULL,
    source_year_text TEXT,
    evidence_class TEXT,
    state TEXT NOT NULL,
    flags TEXT NOT NULL,
    joined INTEGER NOT NULL,
    pit_admitted INTEGER NOT NULL
);
CREATE TABLE unresolved_program_name (
    unresolved_id INTEGER PRIMARY KEY,
    raw_name TEXT NOT NULL,
    state TEXT NOT NULL,
    seasons TEXT NOT NULL,
    candidate_program_ids TEXT NOT NULL,
    detail TEXT NOT NULL
);
CREATE TABLE audit_execution (
    audit_key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE INDEX idx_membership_season ON program_season_membership(season);
CREATE INDEX idx_observation_program_season ON staff_observation(program_id, season);
CREATE INDEX idx_assignment_role ON staff_role_assignment(role_code);
CREATE INDEX idx_scheme_program_season ON scheme_assertion(program_id, season);
CREATE INDEX idx_user_cell_program_season ON user_corpus_cell(canonical_program_id, season);
CREATE INDEX idx_career_episode_program ON career_episode(employer_program_id, start_year);
CREATE INDEX idx_career_episode_person ON career_episode(person_display_name);
"""

#: Coverage states for a core HC/OC/DC cell. Confirmed requires a
#: record-bound observation whose season is bound from the source.
CONFIRMED = "CONFIRMED_SOURCE_SCOPED"
CANDIDATE = "CANDIDATE_UNBOUND_SEASON_OR_UNBOUND_RECORD"
NO_EVIDENCE = "NO_EVIDENCE"


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


@dataclass
class ReleaseInputs:
    """Every declared input, so the release can rehash them independently."""

    population: Path
    membership_rows: Path
    crosswalk: Path
    staff_observations: Path
    staff_captures: Path
    scheme_assertions: Path
    scheme_conflicts: Path
    responsibility_assertions: Path
    user_corpus_cells: Path | None = None
    career_episodes: Path | None = None

    def as_pairs(self) -> list[tuple[str, Path]]:
        return [
            ("NATIONAL_POPULATION", self.population),
            ("NATIONAL_MEMBERSHIP_ROWS", self.membership_rows),
            ("PROGRAM_CROSSWALK", self.crosswalk),
            ("STAFF_OBSERVATIONS", self.staff_observations),
            ("STAFF_CAPTURE_INVENTORY", self.staff_captures),
            ("SCHEME_ASSERTIONS", self.scheme_assertions),
            ("SCHEME_CONFLICTS", self.scheme_conflicts),
            ("RESPONSIBILITY_ASSERTIONS", self.responsibility_assertions),
        ] + (
            [("USER_CORPUS_CELLS", self.user_corpus_cells)]
            if self.user_corpus_cells is not None
            else []
        ) + (
            [("CAREER_EPISODES", self.career_episodes)]
            if self.career_episodes is not None
            else []
        )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Strict read. A truncated input must never become a smaller release."""

    return read_jsonl_strict(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_release(
    inputs: ReleaseInputs,
    destination: Path,
    *,
    build_label: str,
    audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the release database and return the counts it actually holds."""

    if destination.exists():
        destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(destination)
    connection.executescript(SCHEMA)

    population = read_json(inputs.population)
    crosswalk = read_json(inputs.crosswalk)
    membership = read_jsonl(inputs.membership_rows)
    observations = read_jsonl(inputs.staff_observations)
    schemes = read_jsonl(inputs.scheme_assertions)
    conflicts = read_jsonl(inputs.scheme_conflicts)
    responsibilities = read_jsonl(inputs.responsibility_assertions)
    user_cells = (
        read_jsonl(inputs.user_corpus_cells)
        if inputs.user_corpus_cells is not None
        else []
    )
    career_episodes = (
        read_jsonl(inputs.career_episodes)
        if inputs.career_episodes is not None
        else []
    )

    connection.executemany(
        "INSERT INTO release_identity(key, value) VALUES (?, ?)",
        [
            ("release_version", RELEASE_VERSION),
            ("build_label", build_label),
            ("declared_scope", json.dumps(population.get("declared_scope"))),
            ("crosswalk_version", str(crosswalk.get("crosswalk_version"))),
        ],
    )

    # ---- declared inputs, rehashed here rather than trusted ---------------
    for index, (source_class, path) in enumerate(inputs.as_pairs(), start=1):
        connection.execute(
            "INSERT INTO source_file(source_file_id, path, sha256, bytes, "
            "source_class, exists_at_build) VALUES (?, ?, ?, ?, ?, ?)",
            (
                index,
                str(path),
                sha256_file(path),
                path.stat().st_size if path.is_file() else None,
                source_class,
                int(path.is_file()),
            ),
        )

    # ---- programs and aliases --------------------------------------------
    programs = crosswalk.get("programs") or []
    connection.executemany(
        "INSERT INTO canonical_program(program_id, source_namespace, "
        "source_entity_id, display_names, in_football_population) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (
                row["canonical_program_id"],
                row["source_namespace"],
                row["source_entity_id"],
                json.dumps(row.get("display_names") or []),
                int(bool(row.get("in_football_population"))),
            )
            for row in programs
        ],
    )
    known_programs = {row["canonical_program_id"] for row in programs}
    alias_rows: list[tuple] = []
    for records in (crosswalk.get("aliases") or {}).values():
        for record in records:
            if record["canonical_program_id"] not in known_programs:
                continue
            alias_rows.append(
                (
                    record["canonical_program_id"],
                    record["original_alias"],
                    record["normalized_alias"],
                    record["alias_basis"],
                    record["effective_state"],
                    record.get("effective_start"),
                    record.get("effective_end"),
                    record.get("rename_source_url"),
                    record.get("source_payload_sha256"),
                )
            )
    connection.executemany(
        "INSERT INTO program_alias(program_id, original_alias, normalized_alias, "
        "alias_basis, effective_state, effective_start, effective_end, "
        "rename_source_url, source_payload_sha256) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        alias_rows,
    )
    connection.executemany(
        "INSERT INTO alias_collision(normalized_alias, match_basis, program_ids, "
        "disposition) VALUES (?, ?, ?, ?)",
        [
            (
                row["normalized_alias"],
                row.get("match_basis", "EXACT_NORMALIZED_NAME"),
                json.dumps(row["canonical_program_ids"]),
                row["disposition"],
            )
            for row in (crosswalk.get("conflicts") or {}).get("collisions", [])
        ],
    )

    # ---- membership and the published denominator -------------------------
    def bucket(row: Mapping[str, Any]) -> str:
        value = row.get("classification")
        if value in {"fbs", "fcs"}:
            return value.upper()
        era = str(row.get("era") or "")
        if era in {"NCAA_UNIVERSITY_DIVISION_PRIMARY", "UNSPLIT_DIVISION_I"}:
            return "PRE_CLASSIFICATION_ERA"
        return "OTHER_DIVISION" if value else "UNKNOWN"

    seen_membership: set[tuple[str, int]] = set()
    membership_rows: list[tuple] = []
    for row in membership:
        program_id = row.get("program_id")
        season = row.get("season")
        if program_id is None or season is None:
            continue
        key = (program_id, int(season))
        if key in seen_membership or program_id not in known_programs:
            continue
        seen_membership.add(key)
        membership_rows.append(
            (
                program_id,
                int(season),
                row.get("classification"),
                bucket(row),
                row.get("conference"),
                row.get("era"),
                row.get("membership_authority") or "PER_ROW_DECLARED_SEASON",
                row.get("payload_sha256"),
                row.get("request_identity_sha256"),
            )
        )
    connection.executemany(
        "INSERT INTO program_season_membership(program_id, season, classification, "
        "classification_bucket, conference, era, membership_authority, "
        "payload_sha256, request_identity_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        membership_rows,
    )
    connection.executemany(
        "INSERT INTO season_population(season, programs, fbs, fcs, "
        "pre_classification, other_division, unknown, state) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row["season"],
                row["programs"],
                row["FBS"],
                row["FCS"],
                row["PRE_CLASSIFICATION_ERA"],
                row["OTHER_DIVISION"],
                row["UNKNOWN"],
                row["state"],
            )
            for row in population.get("population_by_season") or []
        ],
    )
    connection.executemany(
        "INSERT INTO unresolved_program_name(raw_name, state, seasons, "
        "candidate_program_ids, detail) VALUES (?, ?, ?, ?, ?)",
        [
            (
                row["raw_name"],
                row["state"],
                json.dumps(row.get("seasons") or []),
                json.dumps(row.get("candidate_program_ids") or []),
                row.get("detail", ""),
            )
            for row in population.get("unresolved_program_names") or []
        ],
    )

    # ---- staff observations and their role decompositions -----------------
    observation_rows: list[tuple] = []
    assignment_rows: list[tuple] = []
    for index, row in enumerate(observations, start=1):
        observation_rows.append(
            (
                index,
                row.get("capture_path"),
                row.get("payload_sha256"),
                row.get("program_id"),
                row.get("display_name"),
                row.get("person") or "",
                row.get("source_title") or "",
                row.get("record_selector"),
                row.get("person_body_offset"),
                int(bool(row.get("person_record_bound"))),
                int(bool(row.get("role_claim_supported"))),
                row.get("reject_reason"),
                row.get("evidence_tier") or "UNKNOWN",
                row.get("season"),
                row.get("season_state") or "UNKNOWN",
                row.get("source_class") or "OFFICIAL_STAFF_HTML",
                int(bool(row.get("pit_admitted"))),
            )
        )
        for assignment in row.get("assignments") or []:
            assignment_rows.append(
                (
                    index,
                    assignment.get("role", "unmapped_title_review_required"),
                    assignment.get("unit", "UNKNOWN"),
                    json.dumps(assignment.get("qualifiers") or []),
                    assignment.get("occupancy", "UNMAPPED"),
                    assignment.get("taxonomy_version", "UNKNOWN"),
                    int(assignment.get("role") in CORE_ROLES),
                    int(bool(assignment.get("play_caller_inferred"))),
                )
            )
    connection.executemany(
        "INSERT INTO staff_observation(observation_id, capture_path, payload_sha256, "
        "program_id, display_name, person, source_title, record_selector, "
        "person_body_offset, person_record_bound, role_claim_supported, "
        "reject_reason, evidence_tier, season, season_state, source_class, "
        "pit_admitted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        observation_rows,
    )
    connection.executemany(
        "INSERT INTO staff_role_assignment(observation_id, role_code, unit, "
        "qualifiers, occupancy, taxonomy_version, is_core_role, "
        "play_caller_inferred) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        assignment_rows,
    )

    # ---- schemes, conflicts and responsibility ----------------------------
    connection.executemany(
        "INSERT INTO scheme_assertion(program_id, season, side, source_text, "
        "normalized_families, source_disposition, state, evidence_tier, "
        "official_corroboration, page_title, wikimedia_revision, pit_admitted, "
        "inferred_from_title) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row.get("canonical_program_id"),
                row.get("season"),
                row.get("side") or "UNKNOWN",
                row.get("source_text"),
                json.dumps(row.get("normalized_families") or []),
                row.get("source_disposition") or "UNKNOWN",
                row.get("state") or "UNKNOWN",
                row.get("evidence_tier") or "UNKNOWN",
                row.get("official_corroboration"),
                row.get("page_title"),
                str(row.get("wikimedia_revision") or ""),
                int(bool(row.get("pit_admitted"))),
                int(bool(row.get("inferred_from_title"))),
            )
            for row in schemes
        ],
    )
    connection.executemany(
        "INSERT INTO scheme_conflict(page_title, season, side, conflict_texts, "
        "program_resolution_state) VALUES (?, ?, ?, ?, ?)",
        [
            (
                row.get("page_title") or "",
                row.get("season"),
                row.get("side") or "UNKNOWN",
                json.dumps(row.get("conflict_texts") or []),
                row.get("program_resolution_state") or "UNKNOWN",
            )
            for row in conflicts
        ],
    )
    connection.executemany(
        "INSERT INTO responsibility_assertion(person, program_id, season, "
        "source_title, evidence_code, disposition, inferred_from_role_title, "
        "pit_admitted) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row.get("person"),
                row.get("program_id"),
                row.get("season"),
                row.get("source_title") or "",
                row.get("evidence_code") or "UNKNOWN",
                row.get("disposition") or "UNKNOWN",
                int(bool(row.get("inferred_from_role_title"))),
                int(bool(row.get("pit_admitted"))),
            )
            for row in responsibilities
        ],
    )

    # ---- the user research corpus, preserved at cell grain ----------------
    connection.executemany(
        "INSERT INTO user_corpus_cell(source_class, season, team_as_written, "
        "subdivision_as_written, role_column, person_as_written, "
        "source_title_as_written, canonical_program_id, "
        "program_resolution_state, evidence_tier, verified, pit_admitted) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row.get("source_class") or "UNKNOWN",
                row.get("season"),
                row.get("team_as_written") or "",
                row.get("subdivision_as_written"),
                row.get("role_column"),
                row.get("person_as_written"),
                row.get("source_title_as_written"),
                row.get("canonical_program_id"),
                row.get("program_resolution_state") or "UNKNOWN",
                row.get("evidence_tier") or "USER_COMPILED_RESEARCH_OBSERVATION",
                int(bool(row.get("verified"))),
                int(bool(row.get("pit_admitted"))),
            )
            for row in user_cells
        ],
    )

    # ---- the cached career corpus, preserved with its disposition --------
    # Every episode is carried, including the ones refused for a named
    # reason. A release that held only the joinable episodes would make the
    # corpus look far cleaner than it is, and the refusals are the finding.
    connection.executemany(
        "INSERT INTO career_episode(span_id, pageid, page_title, wikidata_qid, "
        "wikimedia_revision, episode_index, person_display_name, employer_raw, "
        "employer_resolution_state, employer_program_id, source_title, "
        "role_codes, start_year, end_year, ongoing, source_year_text, "
        "evidence_class, state, flags, joined, pit_admitted) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                row.get("span_id"),
                str(row.get("pageid")) if row.get("pageid") is not None else None,
                row.get("page_title"),
                row.get("wikidata_qid"),
                str(row.get("wikimedia_revision"))
                if row.get("wikimedia_revision") is not None
                else None,
                int(row.get("episode_index") or 0),
                row.get("person_display_name") or "",
                row.get("employer_raw") or "",
                row.get("employer_resolution_state") or "UNKNOWN",
                row.get("employer_program_id"),
                row.get("source_title"),
                json.dumps(row.get("role_codes") or [], sort_keys=True),
                row.get("start_year"),
                row.get("end_year"),
                int(bool(row.get("ongoing"))),
                row.get("source_year_text"),
                row.get("evidence_class"),
                row.get("state") or "UNKNOWN",
                json.dumps(row.get("flags") or [], sort_keys=True),
                int(bool(row.get("joined"))),
                int(bool(row.get("pit_admitted"))),
            )
            for row in career_episodes
        ],
    )

    # ---- the core HC/OC/DC matrix, computed from the delivered rows -------
    # Every membership row crosses every core role, so a program-season with
    # no offensive-coordinator evidence gets a NO_EVIDENCE cell rather than
    # no cell at all. An omitted cell is the shape that makes a coverage
    # percentage look better than the data.
    connection.execute(
        """
        INSERT INTO core_role_cell(program_id, season, role_code, coverage_state,
                                   observations)
        SELECT m.program_id,
               m.season,
               r.role_code,
               CASE
                   WHEN SUM(CASE WHEN e.observation_id IS NOT NULL
                                  AND e.person_record_bound = 1
                                  AND e.role_claim_supported = 1
                                  AND e.season IS NOT NULL
                                  AND e.evidence_tier = 'OFFICIAL_HTML_RECORD_BOUND'
                            THEN 1 ELSE 0 END) > 0 THEN ?
                   WHEN COUNT(e.observation_id) > 0 THEN ?
                   ELSE ?
               END,
               COUNT(e.observation_id)
        FROM program_season_membership AS m
        CROSS JOIN (SELECT ? AS role_code UNION ALL SELECT ? UNION ALL SELECT ?) AS r
        LEFT JOIN (
            SELECT DISTINCT
                   o.observation_id,
                   o.program_id,
                   o.season,
                   o.person_record_bound,
                   o.role_claim_supported,
                   o.evidence_tier,
                   a.role_code
            FROM staff_observation AS o
            JOIN staff_role_assignment AS a
              ON a.observation_id = o.observation_id
        ) AS e
               ON e.program_id = m.program_id
              AND e.season = m.season
              AND e.role_code = r.role_code
        GROUP BY m.program_id, m.season, r.role_code
        """,
        (CONFIRMED, CANDIDATE, NO_EVIDENCE, *CORE_ROLES),
    )

    summaries = compute_coverage(connection)
    connection.executemany(
        "INSERT INTO coverage_summary(grain, bucket, value) VALUES (?, ?, ?)",
        [(grain, bucket_name, value) for grain, bucket_name, value in summaries],
    )
    if audit:
        connection.executemany(
            "INSERT INTO audit_execution(audit_key, value) VALUES (?, ?)",
            [(key, json.dumps(value)) for key, value in sorted(audit.items())],
        )
    connection.commit()
    counts = table_counts(connection)
    connection.close()
    return {
        "release_version": RELEASE_VERSION,
        "database": str(destination),
        "sha256": sha256_file(destination),
        "table_counts": counts,
        "coverage": {f"{grain}|{bucket_name}": value for grain, bucket_name, value in summaries},
    }


def compute_coverage(connection: sqlite3.Connection) -> list[tuple[str, str, int]]:
    """Every published coverage number, as a query over delivered rows."""

    rows: list[tuple[str, str, int]] = []

    def one(sql: str, params: Sequence[Any] = ()) -> int:
        return int(connection.execute(sql, params).fetchone()[0])

    rows.append(
        (
            "PROGRAM_SEASON",
            "DELIVERED_MEMBERSHIP_ROWS",
            one("SELECT COUNT(*) FROM program_season_membership"),
        )
    )
    rows.append(
        (
            "PROGRAM_SEASON",
            "DISTINCT_PROGRAMS",
            one("SELECT COUNT(DISTINCT program_id) FROM program_season_membership"),
        )
    )
    rows.append(
        (
            "PROGRAM_SEASON",
            "SEASONS_WITH_MEMBERSHIP",
            one("SELECT COUNT(*) FROM season_population WHERE programs > 0"),
        )
    )
    rows.append(
        (
            "PROGRAM_SEASON",
            "SEASONS_WITHOUT_MEMBERSHIP",
            one("SELECT COUNT(*) FROM season_population WHERE programs = 0"),
        )
    )
    for state in (CONFIRMED, CANDIDATE, NO_EVIDENCE):
        rows.append(
            (
                "CORE_ROLE_CELL",
                state,
                one(
                    "SELECT COUNT(*) FROM core_role_cell WHERE coverage_state = ?",
                    (state,),
                ),
            )
        )
    rows.append(
        ("CORE_ROLE_CELL", "TOTAL", one("SELECT COUNT(*) FROM core_role_cell"))
    )
    rows.append(
        (
            "STAFF_OBSERVATION",
            "TOTAL",
            one("SELECT COUNT(*) FROM staff_observation"),
        )
    )
    for tier in (
        "OFFICIAL_HTML_RECORD_BOUND",
        "OFFICIAL_HTML_STRING_LOCATED_ONLY",
        "CANDIDATE_FROM_UNBOUND_CAPTURE",
    ):
        rows.append(
            (
                "STAFF_OBSERVATION",
                tier,
                one(
                    "SELECT COUNT(*) FROM staff_observation WHERE evidence_tier = ?",
                    (tier,),
                ),
            )
        )
    rows.append(
        (
            "STAFF_OBSERVATION",
            "SEASON_BOUND",
            one("SELECT COUNT(*) FROM staff_observation WHERE season IS NOT NULL"),
        )
    )
    rows.append(
        (
            "STAFF_OBSERVATION",
            "SEASON_UNKNOWN",
            one("SELECT COUNT(*) FROM staff_observation WHERE season IS NULL"),
        )
    )
    rows.append(
        (
            "STAFF_ROLE",
            "CORE_ASSIGNMENTS",
            one("SELECT COUNT(*) FROM staff_role_assignment WHERE is_core_role = 1"),
        )
    )
    rows.append(
        (
            "STAFF_ROLE",
            "NON_CORE_ASSIGNMENTS",
            one("SELECT COUNT(*) FROM staff_role_assignment WHERE is_core_role = 0"),
        )
    )
    rows.append(
        (
            "STAFF_ROLE",
            "DISTINCT_ROLE_CODES",
            one("SELECT COUNT(DISTINCT role_code) FROM staff_role_assignment"),
        )
    )
    rows.append(
        (
            "STAFF_ROLE",
            "UNMAPPED_TITLES",
            one(
                "SELECT COUNT(*) FROM staff_role_assignment "
                "WHERE role_code = 'unmapped_title_review_required'"
            ),
        )
    )
    rows.append(
        (
            "SCHEME",
            "ADMITTED_CANDIDATE",
            one(
                "SELECT COUNT(*) FROM scheme_assertion "
                "WHERE state = 'ADMITTED_CANDIDATE_SCHEME_ASSERTION'"
            ),
        )
    )
    rows.append(
        ("SCHEME", "TOTAL_CLAIMS", one("SELECT COUNT(*) FROM scheme_assertion"))
    )
    rows.append(
        ("SCHEME", "CONFLICTS_RETAINED", one("SELECT COUNT(*) FROM scheme_conflict"))
    )
    rows.append(
        (
            "RESPONSIBILITY",
            "ADMITTED",
            one(
                "SELECT COUNT(*) FROM responsibility_assertion "
                "WHERE disposition = 'ADMITTED_EXPLICIT_SOURCE_STATEMENT'"
            ),
        )
    )
    rows.append(
        (
            "RESPONSIBILITY",
            "REJECTED_CANDIDATES",
            one(
                "SELECT COUNT(*) FROM responsibility_assertion "
                "WHERE disposition <> 'ADMITTED_EXPLICIT_SOURCE_STATEMENT'"
            ),
        )
    )
    rows.append(
        ("USER_CORPUS", "CELLS_PRESERVED", one("SELECT COUNT(*) FROM user_corpus_cell"))
    )
    rows.append(
        (
            "USER_CORPUS",
            "CELLS_WITH_A_CANONICAL_PROGRAM",
            one(
                "SELECT COUNT(*) FROM user_corpus_cell "
                "WHERE canonical_program_id IS NOT NULL"
            ),
        )
    )
    rows.append(
        (
            "USER_CORPUS",
            "CELLS_VERIFIED",
            one("SELECT COUNT(*) FROM user_corpus_cell WHERE verified = 1"),
        )
    )
    rows.append(
        (
            "CAREER",
            "EPISODES_PRESERVED",
            one("SELECT COUNT(*) FROM career_episode"),
        )
    )
    rows.append(
        (
            "CAREER",
            "EPISODES_WITH_AN_EMPLOYER_A_ROLE_AND_AN_INTERVAL",
            one(
                "SELECT COUNT(*) FROM career_episode "
                "WHERE state = 'CANDIDATE_CAREER_EPISODE_RETAINED_NOT_JOINED'"
            ),
        )
    )
    rows.append(
        (
            "CAREER",
            "EPISODES_JOINED",
            one("SELECT COUNT(*) FROM career_episode WHERE joined = 1"),
        )
    )
    rows.append(
        (
            "IDENTITY",
            "ALIAS_COLLISIONS_REFUSED",
            one("SELECT COUNT(*) FROM alias_collision"),
        )
    )
    rows.append(
        (
            "IDENTITY",
            "UNRESOLVED_PROGRAM_NAMES",
            one("SELECT COUNT(*) FROM unresolved_program_name"),
        )
    )
    rows.append(
        (
            "IDENTITY",
            "ALIASES_WITH_A_CITED_EFFECTIVE_INTERVAL",
            one(
                "SELECT COUNT(*) FROM program_alias "
                "WHERE effective_state = 'EFFECTIVE_INTERVAL_FROM_CITED_RENAME_SOURCE'"
            ),
        )
    )
    return rows


def table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    names = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    return {
        name: int(connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0])
        for name in names
    }


#: Tables whose content is the scientific claim. A replay comparison over
#: these must be identical; ``audit_execution`` and ``release_identity``
#: carry the clock and the build label and are compared separately.
SCIENTIFIC_TABLES = (
    "source_file",
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
    "core_role_cell",
    "user_corpus_cell",
    "career_episode",
    "coverage_summary",
    "unresolved_program_name",
)


def table_digest(path: Path, table: str) -> str:
    """Content digest of one table, ordered so row order cannot matter."""

    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        columns = [
            row[1]
            for row in connection.execute(f'PRAGMA table_info("{table}")')
        ]
        order = ", ".join(f'"{name}"' for name in columns)
        digest = hashlib.sha256()
        for row in connection.execute(
            f'SELECT {order} FROM "{table}" ORDER BY {order}'
        ):
            digest.update(
                json.dumps(list(row), sort_keys=True, default=str).encode("utf-8")
            )
        return digest.hexdigest()
    finally:
        connection.close()


def compare_releases(
    first: Path, second: Path, tables: Iterable[str] = SCIENTIFIC_TABLES
) -> dict[str, Any]:
    """Two builds compared at scientific-content grain, table by table."""

    comparison = {}
    for table in tables:
        left = table_digest(first, table)
        right = table_digest(second, table)
        comparison[table] = {
            "first": left,
            "second": right,
            "identical": left == right,
        }
    identical = all(row["identical"] for row in comparison.values())
    return {
        "tables_compared": len(comparison),
        "all_identical_at_scientific_grain": identical,
        "per_table": comparison,
        "excluded_tables": ["release_identity", "audit_execution"],
        "why_excluded": (
            "These carry the build label and the audit clock. They are "
            "compared as a separate, declared exclusion rather than silently "
            "dropped to make a replay look deterministic."
        ),
    }
