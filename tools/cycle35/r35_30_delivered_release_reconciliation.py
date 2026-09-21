"""R35-30 (Cycle #35 continuation, 20260921T055921Z), section 6.

"Reconcile existing scheme, responsibility, career, and user-corpus sources
with the delivered release. A successful private rebuild is not proof the
delivered database contains those rows."

It is not, and here it is not true either. This module opens the DELIVERED
database read-only and counts what is in it, per source family, at row
grain. Nothing here reads a rebuild, a summary JSON or a packet claim: the
delivered file is the only evidence about what was delivered.

That distinction is the whole point, because the two disagree. The closeout
wrote CYCLE35_RELEASE_COVERAGE_BINDING.json beside the release, reporting
13,474 expected cells COVERED_BY_CANDIDATE_OBSERVATION_ONLY. The delivered
database's own expected_cell.coverage_state column says
EXPECTED_NOT_YET_COVERED for all 36,582 rows. The coverage was computed
alongside the build and never written into it, so a reader who opens the
release and a reader who opens the artifact beside it get different answers
to the same question. Only one of them is the release.

What the delivered database actually holds, by the family that supplied it:

    family                              files  observations  supports
    OFFICIAL_STAFF_HTML                   266           877      1398
    USER_COMPILED_RESEARCH_OBSERVATION     56       110,042         0
    CYCLE34_CANDIDATE_TRANSCRIPTION         1            85         0

So the user corpus is 99.1% of every observation in the release and carries
none of its assertions; all 1,398 hang off official staff HTML. Scheme and
responsibility are empty, which the R35-29 reconciliation already explains
and attributes. And every employment_episode season is the literal string
"CURRENT", so no confirmed assertion sits in any particular year -- which is
why the confirmed layer contributes nothing to coverage.

None of that is a reason to distrust the rebuild. It is a reason not to
describe the delivered release using the rebuild's numbers, which is the
error this module exists to make impossible to repeat. Where a repaired
build is supplied it is reported in a separate column, never merged into
the delivered one, and the difference is stated as a difference.

This module changes nothing. It opens databases read-only and writes one
artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

#: The delivered release, named explicitly. Never chosen by modification
#: time: the newest file on disk is whichever rebuild ran last, which says
#: nothing about what was delivered.
DELIVERED_RELEASE = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs"
    r"\20260921T025300Z_closeout_release\published_release"
    r"\CYCLE35_COACHING_RELEASE_PUBLISHED.sqlite"
)

#: The coverage artifact written beside that release, whose numbers do not
#: match the release's own column.
COVERAGE_BINDING = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs"
    r"\20260921T025300Z_closeout_release\CYCLE35_RELEASE_COVERAGE_BINDING.json"
)

#: The four families section 6 names. `scheme` and `responsibility` are
#: tables rather than source classes, so they are counted as tables; the
#: other two are counted by the source class that carries them.
SOURCE_CLASS_FAMILIES = {
    "user_corpus": "USER_COMPILED_RESEARCH_OBSERVATION",
    "career": "CYCLE34_CANDIDATE_TRANSCRIPTION",
    "official_staff": "OFFICIAL_STAFF_HTML",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def open_read_only(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def _count(conn: sqlite3.Connection, table: str) -> int | None:
    if table not in _table_names(conn):
        return None
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # noqa: S608


def family_rows(conn: sqlite3.Connection) -> dict[str, Any]:
    """Per source family: files, observations, and assertions it SUPPORTS.

    The third column is the one that matters. A family can supply almost
    every observation in a release and still carry none of its assertions,
    and counting only observations would hide that completely.
    """

    files = {
        str(row["source_class"]): int(row["n"])
        for row in conn.execute(
            "SELECT source_class, COUNT(*) AS n FROM source_file GROUP BY 1"
        )
    }
    observations = {
        str(row["source_class"]): int(row["n"])
        for row in conn.execute(
            "SELECT sf.source_class AS source_class, COUNT(*) AS n "
            "FROM source_observation o JOIN source_file sf USING(source_file_id) "
            "GROUP BY 1"
        )
    }
    supports = {
        str(row["source_class"]): int(row["n"])
        for row in conn.execute(
            "SELECT sf.source_class AS source_class, COUNT(*) AS n "
            "FROM assertion_support s "
            "JOIN source_observation o USING(observation_id) "
            "JOIN source_file sf USING(source_file_id) GROUP BY 1"
        )
    }
    out: dict[str, Any] = {}
    for family, source_class in sorted(SOURCE_CLASS_FAMILIES.items()):
        out[family] = {
            "source_class": source_class,
            "source_files": files.get(source_class, 0),
            "observations": observations.get(source_class, 0),
            "assertions_supported": supports.get(source_class, 0),
        }
    for family, table in (
        ("scheme", "scheme_assertion"),
        ("responsibility", "responsibility_assertion"),
    ):
        out[family] = {"table": table, "rows": _count(conn, table)}
    return out


def coverage_as_the_release_states_it(conn: sqlite3.Connection) -> dict[str, Any]:
    """Coverage read from the release's own column, and nowhere else."""

    states = {
        str(row["coverage_state"]): int(row["n"])
        for row in conn.execute(
            "SELECT coverage_state, COUNT(*) AS n FROM expected_cell GROUP BY 1"
        )
    }
    span = conn.execute(
        "SELECT MIN(season) AS mn, MAX(season) AS mx, "
        "COUNT(DISTINCT season) AS d, COUNT(DISTINCT program_id) AS p "
        "FROM expected_cell"
    ).fetchone()
    return {
        "coverage_state_counts": states,
        "season_min": span["mn"],
        "season_max": span["mx"],
        "distinct_seasons": span["d"],
        "distinct_programs": span["p"],
    }


def episode_seasons(conn: sqlite3.Connection) -> dict[str, Any]:
    """Whether episodes carry a season at all.

    An episode whose season is the literal string "CURRENT" is not in any
    year, so nothing hanging off it can be placed in a year either.
    """

    rows = {
        str(row["season"]): int(row["n"])
        for row in conn.execute(
            "SELECT season, COUNT(*) AS n FROM employment_episode "
            "GROUP BY 1 ORDER BY n DESC LIMIT 12"
        )
    }
    numeric = int(
        conn.execute(
            "SELECT COUNT(*) FROM employment_episode WHERE season GLOB '[0-9][0-9][0-9][0-9]'"
        ).fetchone()[0]
    )
    total = _count(conn, "employment_episode") or 0
    return {
        "episodes": total,
        "with_a_numeric_season": numeric,
        "without_a_numeric_season": total - numeric,
        "season_values": rows,
    }


def adjudication_time(conn: sqlite3.Connection) -> dict[str, Any]:
    """Whether the delivered rows carry a fabricated decision time."""

    columns = {row[1] for row in conn.execute("PRAGMA table_info(adjudication)")}
    distinct = [
        str(row[0])
        for row in conn.execute("SELECT DISTINCT decided_at_utc FROM adjudication")
    ]
    stamped = [value for value in distinct if value.strip()]
    if len(stamped) == 1 and len(distinct) == 1:
        note = (
            "One timestamp across every row is the signature of a build-clock "
            "reading, not of decisions made at one moment."
        )
    elif not stamped:
        note = (
            "No row states a decision time. That is the repaired state, not a "
            "missing value: a standing rule applied by the build was settled "
            "when the rule was written, so there is no event time to record."
        )
    else:
        note = (
            f"{len(stamped)} distinct timestamps across {_count(conn, 'adjudication')} "
            "rows. Few distinct values across many rows indicates build-clock "
            "readings rather than decisions made at those moments."
        )
    return {
        "rows": _count(conn, "adjudication"),
        "has_decision_time_basis_column": "decision_time_basis" in columns,
        "distinct_decided_at_utc_values": len(distinct),
        "rows_stating_a_decision_time": len(stamped),
        "sample_value": distinct[0] if distinct else None,
        "note": note,
    }


def compare_to_the_artifact_beside_it(
    release_coverage: dict[str, Any]
) -> dict[str, Any]:
    """The release's own column against the JSON written next to it."""

    if not COVERAGE_BINDING.exists():
        return {"artifact_present": False}
    stated = json.loads(COVERAGE_BINDING.read_text(encoding="utf-8"))
    artifact_states = stated.get("coverage_states") or {}
    release_states = release_coverage["coverage_state_counts"]
    return {
        "artifact_present": True,
        "artifact": COVERAGE_BINDING.name,
        "artifact_says": artifact_states,
        "release_column_says": release_states,
        "agree": artifact_states == release_states,
        "finding": (
            "The artifact reports covered cells the release's own "
            "expected_cell.coverage_state column does not contain. Coverage "
            "was computed beside the build and never written into it, so a "
            "reader who opens the release and a reader who opens the "
            "artifact get different answers. Only one of them is the release."
        )
        if artifact_states != release_states
        else "The artifact and the release agree.",
    }


def profile(path: Path) -> dict[str, Any]:
    conn = open_read_only(path)
    try:
        return {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "schema_versions": [
                int(row[0])
                for row in conn.execute(
                    "SELECT version FROM schema_migration ORDER BY version"
                )
            ],
            "families": family_rows(conn),
            "coverage_as_the_release_states_it": coverage_as_the_release_states_it(conn),
            "episode_seasons": episode_seasons(conn),
            "adjudication_time": adjudication_time(conn),
        }
    finally:
        conn.close()


def differences(
    delivered: dict[str, Any], repaired: dict[str, Any]
) -> list[dict[str, Any]]:
    """Stated as differences, never merged into one number."""

    out: list[dict[str, Any]] = []
    for family, left in sorted(delivered["families"].items()):
        right = repaired["families"].get(family, {})
        if left != right:
            out.append(
                {
                    "dimension": "family",
                    "family": family,
                    "delivered": left,
                    "repaired": right,
                }
            )
    for key in (
        "coverage_as_the_release_states_it",
        "episode_seasons",
        "adjudication_time",
    ):
        if delivered[key] != repaired[key]:
            out.append(
                {"dimension": key, "delivered": delivered[key], "repaired": repaired[key]}
            )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile source families against the DELIVERED release."
    )
    parser.add_argument("--delivered", type=Path, default=DELIVERED_RELEASE)
    parser.add_argument(
        "--repaired",
        type=Path,
        default=None,
        help="Optional repaired build, reported separately and never merged.",
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.delivered.exists():
        raise SystemExit("delivered release not found: " + str(args.delivered))

    delivered = profile(args.delivered)
    result: dict[str, Any] = {
        "artifact_type": "CYCLE35_DELIVERED_RELEASE_RECONCILIATION",
        "question": (
            "Does the DELIVERED database contain the scheme, responsibility, "
            "career and user-corpus rows? Not: can a rebuild produce them."
        ),
        "evidence_basis": (
            "Every number below is read from the delivered database file "
            "read-only. No rebuild, summary or packet claim is consulted."
        ),
        "delivered": delivered,
        "release_vs_artifact_beside_it": compare_to_the_artifact_beside_it(
            delivered["coverage_as_the_release_states_it"]
        ),
    }

    if args.repaired is not None:
        if not args.repaired.exists():
            raise SystemExit("repaired build not found: " + str(args.repaired))
        repaired = profile(args.repaired)
        result["repaired_build_reported_separately"] = repaired
        result["differences"] = differences(delivered, repaired)
        result["what_a_difference_means"] = (
            "A row present in the repaired build and absent from the "
            "delivered one is a row the delivered release does not contain. "
            "The repaired build is not evidence about the delivered release."
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / "CYCLE35_DELIVERED_RELEASE_RECONCILIATION.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
