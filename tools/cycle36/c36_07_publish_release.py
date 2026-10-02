"""R36-07: publish the national research release and exercise it read-only.

Builds the release twice from identical frozen inputs into a new immutable
directory, compares every scientific table between the two builds, validates
referential integrity and orphan records against the delivered database, and
then queries it through a temporary working directory so the query path is
exercised against the artifact rather than against the builder's memory.

The examples are deliberately national: several FBS and FCS programs, not
Texas A&M alone. Nothing here produces a score, a forecast or a causal claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.release_builder import (  # noqa: E402
    RELEASE_VERSION,
    ReleaseInputs,
    build_release,
    compare_releases,
    sha256_file,
)
from aggie_analytics import atomic_io as _bas_atomic

#: National examples spanning both subdivisions. Program ids are the source's
#: own entity ids, so the query path is exercised on real delivered rows.
NATIONAL_EXAMPLES = (
    ("SRC-002:TEAM:245", "Texas A&M", "FBS"),
    ("SRC-002:TEAM:194", "Notre Dame", "FBS"),
    ("SRC-002:TEAM:2000", "Abilene Christian", "FCS"),
    ("SRC-002:TEAM:2277", "Houston Christian (formerly Houston Baptist)", "FCS"),
    ("SRC-002:TEAM:3101", "Utah Tech (formerly Dixie State)", "FCS"),
    ("SRC-002:TEAM:2837", "East Texas A&M (formerly Texas A&M-Commerce)", "NON_FBS_FCS"),
)

QUERY_SCRIPT = r'''
import json, sqlite3, sys
db = sys.argv[1]
connection = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
connection.row_factory = sqlite3.Row
def rows(sql, params=()):
    return [dict(row) for row in connection.execute(sql, params)]
out = {
    "cwd_has_no_checkout_src": True,
    "release_identity": rows("SELECT key, value FROM release_identity"),
    "seasons_present": rows(
        "SELECT MIN(season) AS first_season, MAX(season) AS last_season,"
        " COUNT(*) AS seasons, SUM(CASE WHEN programs = 0 THEN 1 ELSE 0 END)"
        " AS seasons_without_membership FROM season_population"
    ),
    "population_2024_2025": rows(
        "SELECT season, programs, fbs, fcs FROM season_population"
        " WHERE season IN (2024, 2025) ORDER BY season"
    ),
    "roles_beyond_core": rows(
        "SELECT a.role_code, COUNT(*) AS assignments FROM staff_role_assignment AS a"
        " WHERE a.is_core_role = 0 GROUP BY a.role_code"
        " ORDER BY assignments DESC LIMIT 15"
    ),
    "co_roles_preserved": rows(
        "SELECT o.person, o.source_title, COUNT(*) AS roles"
        " FROM staff_role_assignment AS a"
        " JOIN staff_observation AS o ON o.observation_id = a.observation_id"
        " GROUP BY a.observation_id HAVING roles > 1"
        " ORDER BY roles DESC, o.person LIMIT 10"
    ),
    "unknown_season_cells": rows(
        "SELECT COUNT(*) AS observations_with_unknown_season"
        " FROM staff_observation WHERE season IS NULL"
    ),
    "uncertain_identity": rows(
        "SELECT raw_name, state FROM unresolved_program_name ORDER BY raw_name LIMIT 10"
    ),
    "source_scheme_text": rows(
        "SELECT program_id, season, side, source_text, normalized_families"
        " FROM scheme_assertion WHERE state = 'ADMITTED_CANDIDATE_SCHEME_ASSERTION'"
        " AND source_text IS NOT NULL ORDER BY season DESC, program_id LIMIT 8"
    ),
    "scheme_conflicts_including_unknown_season": rows(
        "SELECT page_title, season, conflict_texts FROM scheme_conflict"
    ),
    "current_versus_historical": rows(
        "SELECT membership_authority, COUNT(*) AS rows_"
        " FROM program_season_membership GROUP BY membership_authority"
    ),
    "effective_dated_aliases": rows(
        "SELECT program_id, original_alias, effective_start, effective_end,"
        " rename_source_url FROM program_alias"
        " WHERE effective_state = 'EFFECTIVE_INTERVAL_FROM_CITED_RENAME_SOURCE'"
        " ORDER BY program_id, original_alias"
    ),
    "user_corpus_preserved": rows(
        "SELECT source_class, COUNT(*) AS cells,"
        " SUM(CASE WHEN canonical_program_id IS NOT NULL THEN 1 ELSE 0 END)"
        " AS with_a_canonical_program, SUM(verified) AS verified"
        " FROM user_corpus_cell GROUP BY source_class"
    ),
    "user_corpus_example_rows": rows(
        "SELECT season, team_as_written, role_column, person_as_written,"
        " canonical_program_id, evidence_tier FROM user_corpus_cell"
        " WHERE canonical_program_id IS NOT NULL ORDER BY season DESC,"
        " team_as_written LIMIT 8"
    ),
    "coverage": rows("SELECT grain, bucket, value FROM coverage_summary ORDER BY grain, bucket"),
}
examples = []
for program_id, label, division in json.loads(sys.argv[2]):
    examples.append({
        "program_id": program_id,
        "label": label,
        "declared_division": division,
        "membership_seasons": rows(
            "SELECT COUNT(*) AS seasons, MIN(season) AS first, MAX(season) AS last"
            " FROM program_season_membership WHERE program_id = ?", (program_id,)
        ),
        "staff_rows": rows(
            "SELECT COUNT(*) AS observations,"
            " SUM(CASE WHEN season IS NULL THEN 1 ELSE 0 END) AS unknown_season"
            " FROM staff_observation WHERE program_id = ?", (program_id,)
        ),
        "roles": rows(
            "SELECT a.role_code, COUNT(*) AS n FROM staff_role_assignment AS a"
            " JOIN staff_observation AS o ON o.observation_id = a.observation_id"
            " WHERE o.program_id = ? GROUP BY a.role_code ORDER BY n DESC LIMIT 8",
            (program_id,),
        ),
        "core_cells": rows(
            "SELECT coverage_state, COUNT(*) AS n FROM core_role_cell"
            " WHERE program_id = ? GROUP BY coverage_state", (program_id,)
        ),
    })
out["national_examples"] = examples
print(json.dumps(out))
'''


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def integrity_checks(database: Path) -> dict[str, Any]:
    """Referential integrity, orphans and support links, against the artifact."""

    connection = sqlite3.connect(
        f"file:{database.as_posix()}?mode=ro", uri=True
    )
    try:
        def scalar(sql: str) -> int:
            return int(connection.execute(sql).fetchone()[0])

        foreign_keys = [
            dict(zip(("table", "rowid", "parent", "fkid"), row))
            for row in connection.execute("PRAGMA foreign_key_check")
        ]
        checks = {
            "pragma_foreign_key_check_violations": len(foreign_keys),
            "foreign_key_violations": foreign_keys[:20],
            "integrity_check": connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0],
            "assignments_without_an_observation": scalar(
                "SELECT COUNT(*) FROM staff_role_assignment AS a "
                "LEFT JOIN staff_observation AS o "
                "ON o.observation_id = a.observation_id "
                "WHERE o.observation_id IS NULL"
            ),
            "observations_without_any_assignment": scalar(
                "SELECT COUNT(*) FROM staff_observation AS o "
                "LEFT JOIN staff_role_assignment AS a "
                "ON a.observation_id = o.observation_id "
                "WHERE a.assignment_id IS NULL"
            ),
            "membership_rows_for_unknown_programs": scalar(
                "SELECT COUNT(*) FROM program_season_membership AS m "
                "LEFT JOIN canonical_program AS p ON p.program_id = m.program_id "
                "WHERE p.program_id IS NULL"
            ),
            "core_cells_for_unknown_programs": scalar(
                "SELECT COUNT(*) FROM core_role_cell AS c "
                "LEFT JOIN canonical_program AS p ON p.program_id = c.program_id "
                "WHERE p.program_id IS NULL"
            ),
            "aliases_for_unknown_programs": scalar(
                "SELECT COUNT(*) FROM program_alias AS a "
                "LEFT JOIN canonical_program AS p ON p.program_id = a.program_id "
                "WHERE p.program_id IS NULL"
            ),
            "admitted_schemes_without_a_program": scalar(
                "SELECT COUNT(*) FROM scheme_assertion "
                "WHERE state = 'ADMITTED_CANDIDATE_SCHEME_ASSERTION' "
                "AND program_id IS NULL"
            ),
            "admitted_schemes_without_a_season": scalar(
                "SELECT COUNT(*) FROM scheme_assertion "
                "WHERE state = 'ADMITTED_CANDIDATE_SCHEME_ASSERTION' "
                "AND season IS NULL"
            ),
            "user_corpus_cells_marked_verified": scalar(
                "SELECT COUNT(*) FROM user_corpus_cell WHERE verified = 1"
            ),
            "pit_admitted_rows_anywhere": scalar(
                "SELECT (SELECT COUNT(*) FROM staff_observation WHERE pit_admitted = 1) "
                "+ (SELECT COUNT(*) FROM scheme_assertion WHERE pit_admitted = 1) "
                "+ (SELECT COUNT(*) FROM responsibility_assertion WHERE pit_admitted = 1) "
                "+ (SELECT COUNT(*) FROM user_corpus_cell WHERE pit_admitted = 1)"
            ),
            "inferred_play_callers": scalar(
                "SELECT COUNT(*) FROM staff_role_assignment "
                "WHERE play_caller_inferred = 1"
            ),
            "declared_inputs_missing_at_build": scalar(
                "SELECT COUNT(*) FROM source_file WHERE exists_at_build = 0"
            ),
            "declared_inputs_without_a_digest": scalar(
                "SELECT COUNT(*) FROM source_file WHERE sha256 IS NULL"
            ),
        }
        checks["all_declared_inputs_rehashed"] = (
            checks["declared_inputs_missing_at_build"] == 0
            and checks["declared_inputs_without_a_digest"] == 0
        )
        checks["no_pit_admission_in_this_release"] = (
            checks["pit_admitted_rows_anywhere"] == 0
        )
        return checks
    finally:
        connection.close()


def exercise_query_path(database: Path) -> dict[str, Any]:
    """Run the read-only query script from a directory with no checkout src."""

    with tempfile.TemporaryDirectory(prefix="c36_query_") as tmp:
        script = Path(tmp) / "query_release.py"
        _bas_atomic.write_text(script, QUERY_SCRIPT, encoding="utf-8")
        environment = dict(os.environ)
        # Remove any inherited path that could re-expose the checkout.
        environment.pop("PYTHONPATH", None)
        before = sha256_file(database)
        run = subprocess.run(
            [
                sys.executable,
                "-I",
                str(script),
                str(database),
                json.dumps([list(row) for row in NATIONAL_EXAMPLES]),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=tmp,
            env=environment,
            timeout=600,
        )
        after = sha256_file(database)
        record: dict[str, Any] = {
            "working_directory": tmp,
            "interpreter_isolated": True,
            "pythonpath_removed": True,
            "exit_code": run.returncode,
            "database_unchanged_by_queries": before == after,
        }
        if run.returncode != 0:
            record["state"] = "QUERY_PATH_FAILED"
            record["stderr_tail"] = run.stderr[-2000:]
            return record
        record["state"] = "QUERY_PATH_EXECUTED"
        record["results"] = json.loads(run.stdout)
        return record


def build(out_dir: Path, inputs: ReleaseInputs) -> dict[str, Any]:
    release_dir = out_dir / "release_c36_r1"
    replay_dir = out_dir / "release_c36_replay"
    release_dir.mkdir(parents=True, exist_ok=True)
    replay_dir.mkdir(parents=True, exist_ok=True)

    primary = release_dir / "CYCLE36_NATIONAL_RELEASE.sqlite"
    replay = replay_dir / "CYCLE36_NATIONAL_RELEASE.sqlite"

    audit = {"built_at_utc": utc_now(), "builder": "c36_07_publish_release"}
    first = build_release(inputs, primary, build_label="r1", audit=audit)
    second = build_release(
        inputs,
        replay,
        build_label="replay",
        audit={"built_at_utc": utc_now(), "builder": "c36_07_publish_release"},
    )
    determinism = compare_releases(primary, replay)
    checks = integrity_checks(primary)
    query = exercise_query_path(primary)

    manifest = {
        "artifact_type": "CYCLE36_DELIVERED_RELEASE_MANIFEST",
        "generated_at_utc": utc_now(),
        "release_version": RELEASE_VERSION,
        "database": str(primary),
        "database_sha256": first["sha256"],
        "replay_database": str(replay),
        "replay_database_sha256": second["sha256"],
        "table_counts": first["table_counts"],
        "replay_table_counts": second["table_counts"],
        "coverage_from_delivered_rows": first["coverage"],
        "determinism": determinism,
        "integrity": checks,
        "query_path": query,
        "declared_inputs": [
            {
                "source_class": source_class,
                "path": str(path),
                "sha256": sha256_file(path),
                "exists": path.is_file(),
            }
            for source_class, path in inputs.as_pairs()
        ],
        "predecessor_releases_untouched": (
            "release_r4 and every earlier snapshot are left exactly as they "
            "were. This is a new immutable directory, not an overwrite."
        ),
        "no_unsupported_claims": (
            "The release carries source observations, identities, membership "
            "and stated scheme text. It contains no final score, no BAS index "
            "and no causal claim."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_DELIVERED_RELEASE_MANIFEST.json", 
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--inputs-dir", type=Path, required=True)
    args = parser.parse_args()
    base = args.inputs_dir
    inputs = ReleaseInputs(
        population=base / "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json",
        membership_rows=base / "CYCLE36_NATIONAL_MEMBERSHIP_ROWS.jsonl",
        crosswalk=base / "CYCLE36_PROGRAM_CROSSWALK.json",
        staff_observations=base / "CYCLE36_STAFF_OBSERVATION_ROWS.jsonl",
        staff_captures=base / "CYCLE36_STAFF_CAPTURE_INVENTORY.jsonl",
        scheme_assertions=base / "CYCLE36_SCHEME_ASSERTIONS.jsonl",
        scheme_conflicts=base / "CYCLE36_SCHEME_CONFLICTS.jsonl",
        responsibility_assertions=base / "CYCLE36_RESPONSIBILITY_ASSERTIONS.jsonl",
        user_corpus_cells=base / "CYCLE36_USER_CORPUS_CELLS.jsonl",
        career_episodes=base / "CYCLE36_CAREER_EPISODE_ROWS.jsonl",
    )
    manifest = build(args.out_dir, inputs)
    print(
        json.dumps(
            {
                "database_sha256": manifest["database_sha256"],
                "table_counts": manifest["table_counts"],
                "deterministic": manifest["determinism"][
                    "all_identical_at_scientific_grain"
                ],
                "integrity": {
                    key: manifest["integrity"][key]
                    for key in (
                        "pragma_foreign_key_check_violations",
                        "integrity_check",
                        "assignments_without_an_observation",
                        "membership_rows_for_unknown_programs",
                        "all_declared_inputs_rehashed",
                        "no_pit_admission_in_this_release",
                        "inferred_play_callers",
                    )
                },
                "query_path_state": manifest["query_path"]["state"],
                "database_unchanged_by_queries": manifest["query_path"][
                    "database_unchanged_by_queries"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
