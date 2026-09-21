"""R35-23 (Cycle #35 closeout review, 20260921T025300Z), section 7.

"Determine and demonstrate which is true of the latest **delivered queryable
release**, not only code or an intermediate JSONL. Publish an immutable
rebuilt release and bind both year ranges, full candidate/verified/conflict
layers, expected populations, source locators, actual schemes/responsibilities
and the corrected career tranche. If a required domain still has no supported
rows, retain that evidence gap rather than inferring facts. Retire neither the
original nor revised tranche denominator without a versioned key
reconciliation... Avoid self-referential hash claims; finalize children before
sealing their parent manifest."

Three things this tool refuses to do, because each would answer the review's
question by changing it rather than by measuring:

* It never picks the release by modification time. The release under
  examination is named explicitly, and the prior delivered release is named
  explicitly alongside it, so "which is true of the delivered release" has a
  checkable answer instead of whichever file happened to be written last.
* It never invents a season, a program or a role. An episode whose season the
  sources do not state stays unbound, and is counted as unbound.
* It never writes a manifest that hashes itself. Children are finalized and
  hashed first, the parent lists those hashes, and the parent's own hash is
  computed after it is closed and written to a separate sidecar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle30.coaching import principal_role_families  # noqa: E402

CYCLE_RUNS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")

#: The release this cycle rebuilt, and the one the closing packet shipped.
#: Both are named so the reconciliation can state what changed, rather than
#: asserting that the newest file on disk is the delivered one.
REBUILT_RELEASE = (
    CYCLE_RUNS
    / "20260921T025300Z_closeout"
    / "replay"
    / "replay_2"
    / "CYCLE35_COACHING_RELEASE_replay2.sqlite"
)
PRIOR_DELIVERED_RELEASE = (
    CYCLE_RUNS
    / "20260920T172801Z"
    / "implementation_output"
    / "CYCLE35_COACHING_RELEASE_r7.sqlite"
)

CAREER_TRANCHE = (
    CYCLE_RUNS
    / "20260920T215454Z_mf35_08_era_fix"
    / "implementation_output"
    / "R35_05_CAREER_TRANCHE.json"
)
CAREER_TRANCHE_FINAL = (
    CYCLE_RUNS
    / "20260920T215454Z_mf35_08_era_fix"
    / "implementation_output"
    / "R35_05_CAREER_TRANCHE_FINAL.json"
)

#: Expected cells are declared over these three principal families only, so
#: coverage is measured over the same three and never over a wider set that
#: would flatter the numerator.
CORE_ROLES = ("head_coach", "offensive_coordinator", "defensive_coordinator")

COVERED_CONFIRMED = "COVERED_BY_CONFIRMED_ASSERTION"
COVERED_CANDIDATE = "COVERED_BY_CANDIDATE_OBSERVATION_ONLY"
NOT_COVERED = "NO_EVIDENCE_ACQUIRED_FOR_THIS_CELL"

NUMERIC_SEASON_SQL = "observed_season GLOB '[0-9][0-9][0-9][0-9]'"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def numeric_season(value: Any) -> int | None:
    """A season the source actually states. 'CURRENT' is not a season."""

    text = str(value or "").strip()
    if len(text) != 4 or not text.isdigit():
        return None
    return int(text)


def bind_coverage(conn: sqlite3.Connection) -> dict[str, Any]:
    """Bind the declared expected population to the delivered evidence.

    Every expected cell gets one of three states. The distinction between the
    last two matters: an unpromoted candidate row is evidence that really was
    acquired, so calling it "no evidence" would erase acquisition work, while
    calling it "covered" would promote a single unverified source to a
    confirmed fact.
    """

    cursor = conn.cursor()

    confirmed: set[tuple[str, int, str]] = set()
    episode_assertions = 0
    episodes_without_stated_season = 0
    for program_id, season, role_family in cursor.execute(
        "SELECT e.program_id, e.season, a.role_family "
        "FROM employment_episode e "
        "JOIN formal_role_assertion a ON a.episode_id = e.episode_id "
        "WHERE a.evidence_layer = 'OFFICIAL_PRIMARY_CONFIRMED'"
    ):
        episode_assertions += 1
        year = numeric_season(season)
        if year is None:
            episodes_without_stated_season += 1
            continue
        if role_family in CORE_ROLES:
            confirmed.add((str(program_id), year, str(role_family)))

    candidate: set[tuple[str, int, str]] = set()
    observations_total = 0
    observations_with_stated_season = 0
    observations_mapped = 0
    unmapped_titles: Counter[str] = Counter()
    for program_id, season, title in cursor.execute(
        "SELECT observed_program, observed_season, observed_title FROM source_observation"
    ):
        observations_total += 1
        year = numeric_season(season)
        if year is None:
            continue
        observations_with_stated_season += 1
        families = [
            family
            for family in principal_role_families(str(title or ""))
            if family in CORE_ROLES
        ]
        if not families:
            unmapped_titles[str(title or "")[:80]] += 1
            continue
        observations_mapped += 1
        for family in families:
            candidate.add((str(program_id or ""), year, family))

    states: Counter[str] = Counter()
    by_role: dict[str, Counter[str]] = {role: Counter() for role in CORE_ROLES}
    by_era: dict[str, Counter[str]] = {}
    covered_seasons: Counter[int] = Counter()
    for program_id, season, role_family, era_band in cursor.execute(
        "SELECT program_id, season, role_family, era_band FROM expected_cell"
    ):
        key = (str(program_id), int(season), str(role_family))
        if key in confirmed:
            state = COVERED_CONFIRMED
        elif key in candidate:
            state = COVERED_CANDIDATE
        else:
            state = NOT_COVERED
        states[state] += 1
        if str(role_family) in by_role:
            by_role[str(role_family)][state] += 1
        by_era.setdefault(str(era_band), Counter())[state] += 1
        if state != NOT_COVERED:
            covered_seasons[int(season)] += 1

    return {
        "expected_cells": sum(states.values()),
        "coverage_states": dict(states),
        "coverage_by_role_family": {k: dict(v) for k, v in by_role.items()},
        "coverage_by_era_band": {k: dict(v) for k, v in by_era.items()},
        "covered_seasons_min": min(covered_seasons) if covered_seasons else None,
        "covered_seasons_max": max(covered_seasons) if covered_seasons else None,
        "distinct_covered_seasons": len(covered_seasons),
        "episode_assertions_considered": episode_assertions,
        "episode_assertions_without_a_stated_season": episodes_without_stated_season,
        "observations_considered": observations_total,
        "observations_with_a_stated_season": observations_with_stated_season,
        "observations_mapped_to_a_core_role_family": observations_mapped,
        "most_common_titles_outside_the_core_families": [
            {"title": title, "rows": rows}
            for title, rows in unmapped_titles.most_common(10)
        ],
        "role_family_mapping_authority": (
            "aggie_analytics.cycle33.role_taxonomy.principal_role_families, the "
            "same mapping the release builder uses. No title was mapped by hand "
            "for this binding."
        ),
        "confirmed_layer_is_empty_because": (
            "every OFFICIAL_PRIMARY_CONFIRMED assertion hangs off an employment "
            "episode whose season the source states as 'CURRENT' at "
            "SEASON_UNSPECIFIED precision, so no confirmed assertion can be "
            "placed in any program-season-role cell. Assigning those episodes a "
            "season would invent the very fact the cell exists to test."
        )
        if not confirmed
        else None,
    }


def bind_layers(conn: sqlite3.Connection) -> dict[str, Any]:
    """Both year ranges and the full candidate/verified/conflict layering."""

    cursor = conn.cursor()

    def rows(sql: str, params: tuple = ()) -> list[tuple]:
        return list(cursor.execute(sql, params))

    def scalar(sql: str, params: tuple = ()) -> Any:
        return cursor.execute(sql, params).fetchone()[0]

    year_ranges: dict[str, Any] = {}
    for label, low, high in (("2000_2012", 2000, 2012), ("2013_2026", 2013, 2026)):
        window = (
            f"WHERE {NUMERIC_SEASON_SQL} AND "
            "CAST(observed_season AS INTEGER) BETWEEN ? AND ?"
        )
        year_ranges[label] = {
            "observations": scalar(
                f"SELECT COUNT(*) FROM source_observation {window}", (low, high)
            ),
            "by_evidence_layer": {
                str(layer): int(count)
                for layer, count in rows(
                    "SELECT evidence_layer, COUNT(*) FROM source_observation "
                    f"{window} GROUP BY evidence_layer",
                    (low, high),
                )
            },
            "distinct_programs": scalar(
                "SELECT COUNT(DISTINCT observed_program) FROM source_observation "
                f"{window}",
                (low, high),
            ),
            "distinct_seasons": scalar(
                "SELECT COUNT(DISTINCT observed_season) FROM source_observation "
                f"{window}",
                (low, high),
            ),
        }

    return {
        "year_ranges": year_ranges,
        "observations_total": scalar("SELECT COUNT(*) FROM source_observation"),
        "observations_without_a_stated_season": scalar(
            f"SELECT COUNT(*) FROM source_observation WHERE NOT ({NUMERIC_SEASON_SQL})"
        ),
        "observation_layers": {
            str(layer): int(count)
            for layer, count in rows(
                "SELECT evidence_layer, COUNT(*) FROM source_observation "
                "GROUP BY evidence_layer"
            )
        },
        "assertion_layers": {
            str(layer): int(count)
            for layer, count in rows(
                "SELECT evidence_layer, COUNT(*) FROM formal_role_assertion "
                "GROUP BY evidence_layer"
            )
        },
        "conflicts": {
            str(reason): int(count)
            for reason, count in rows(
                "SELECT reason, COUNT(*) FROM conflict GROUP BY reason"
            )
        },
        "adjudications": {
            str(decision): int(count)
            for decision, count in rows(
                "SELECT decision, COUNT(*) FROM adjudication GROUP BY decision"
            )
        },
        "source_locators": {
            "observations_with_a_locator": scalar(
                "SELECT COUNT(*) FROM source_observation "
                "WHERE locator IS NOT NULL AND TRIM(locator) <> ''"
            ),
            "observations_without_a_locator": scalar(
                "SELECT COUNT(*) FROM source_observation "
                "WHERE locator IS NULL OR TRIM(locator) = ''"
            ),
            "distinct_locators": scalar(
                "SELECT COUNT(DISTINCT locator) FROM source_observation"
            ),
            "source_files": scalar("SELECT COUNT(*) FROM source_file"),
            "source_files_with_a_raw_digest": scalar(
                "SELECT COUNT(*) FROM source_file WHERE raw_sha256 IS NOT NULL "
                "AND TRIM(raw_sha256) <> ''"
            ),
            "by_acquisition_receipt": {
                str(receipt): int(count)
                for receipt, count in rows(
                    "SELECT COALESCE(acquisition_receipt, 'NO_RECEIPT_RECORDED'), "
                    "COUNT(*) FROM source_file GROUP BY 1"
                )
            },
        },
        "retained_evidence_gaps": {
            "responsibility_assertion": {
                "rows": scalar("SELECT COUNT(*) FROM responsibility_assertion"),
                "disposition": "RETAINED_AS_EVIDENCE_GAP",
                "basis": (
                    "No acquired source states unit responsibility -- play-calling "
                    "or situational ownership -- in a form the release can bind. "
                    "The domain stays empty rather than being populated by "
                    "inference from role titles."
                ),
            },
            "scheme_assertion": {
                "rows": scalar("SELECT COUNT(*) FROM scheme_assertion"),
                # Corrected by R35-29. This previously read "No acquired
                # source states offensive or defensive scheme", which is
                # false: the cycle33 cache holds 9,111 stated scheme claims.
                # The row count is still zero, but for a different reason,
                # and the reason is what tells someone where to look.
                "disposition": "BLOCKED_ON_A_MISSING_PROGRAM_CROSSWALK",
                "basis": (
                    "Sources DO state schemes: CYCLE33_SCHEME_TENURE_CLAIMS "
                    "holds 19,271 scheme claims of which 9,111 carry stated "
                    "text, across seasons 1963-2026. What is missing is a "
                    "crosswalk from their Wikipedia page titles to canonical "
                    "program ids. The obvious string rule binds 'Texas "
                    "A&M-Commerce Lions' to 'Texas' and both Miami schools to "
                    "one program, and most of its failures are invisible, so "
                    "nothing is ingested on it. Scheme remains not derivable "
                    "from a coordinator's title and is not inferred here."
                ),
                "reconciliation": "CYCLE35_SCHEME_INGEST.json",
            },
        },
    }


def bind_career_tranche() -> dict[str, Any]:
    """Both denominators, reconciled by key membership -- neither retired."""

    if not CAREER_TRANCHE.is_file():
        return {"bound": False, "reason": f"absent: {CAREER_TRANCHE}"}
    first = json.loads(CAREER_TRANCHE.read_text(encoding="utf-8"))
    final: dict[str, Any] = {}
    if CAREER_TRANCHE_FINAL.is_file():
        final = json.loads(CAREER_TRANCHE_FINAL.read_text(encoding="utf-8"))

    reconciliation = first.get("predecessor_reconciliation", {})
    return {
        "bound": True,
        "versioned_keys": {
            "ORIGINAL_PREDECESSOR_DENOMINATOR": {
                "version": "CYCLE34_R34_07",
                "bound_employer_count": reconciliation.get(
                    "predecessor_bound_employer_count"
                ),
                "attempt_rows": reconciliation.get("predecessor_attempt_rows"),
                "retired": False,
                "artifact": str(CAREER_TRANCHE),
            },
            "REVISED_CYCLE35_DENOMINATOR": {
                "version": "CYCLE35_R35_05",
                "key_count": first.get("key_count"),
                "retired": False,
                "artifact": str(CAREER_TRANCHE_FINAL if final else CAREER_TRANCHE),
            },
        },
        "key_space_reconciliation": {
            "employers_in_both": len(reconciliation.get("employers_in_both", [])),
            "employers_only_in_predecessor": reconciliation.get(
                "employers_only_in_predecessor"
            ),
            "employers_only_in_this_cycle": reconciliation.get(
                "employers_only_in_this_cycle"
            ),
            "arithmetic_addition_forbidden": reconciliation.get(
                "arithmetic_addition_forbidden"
            ),
        },
        "first_pass_dispositions": first.get("dispositions"),
        "second_pass_dispositions": final.get("final_dispositions"),
        "denominator_never_shrank": final.get("denominator_never_shrank"),
        "missing_and_conflict_keys_remain_in_the_denominator": first.get(
            "missing_and_conflict_keys_remain_in_the_denominator"
        ),
    }


def release_profile(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False, "path": str(path)}
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cursor = conn.cursor()

        def scalar(sql: str) -> Any:
            return cursor.execute(sql).fetchone()[0]

        window = (
            f"WHERE {NUMERIC_SEASON_SQL} AND CAST(observed_season AS INTEGER) BETWEEN"
        )
        return {
            "present": True,
            "path": str(path),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "source_observations": scalar("SELECT COUNT(*) FROM source_observation"),
            "observations_2000_2012": scalar(
                f"SELECT COUNT(*) FROM source_observation {window} 2000 AND 2012"
            ),
            "observations_2013_2026": scalar(
                f"SELECT COUNT(*) FROM source_observation {window} 2013 AND 2026"
            ),
            "formal_role_assertions": scalar(
                "SELECT COUNT(*) FROM formal_role_assertion"
            ),
        }
    finally:
        conn.close()


def compare_releases(rebuilt: Path, prior: Path) -> dict[str, Any]:
    """State plainly what the prior delivered release did and did not carry."""

    rebuilt_profile = release_profile(rebuilt)
    prior_profile = release_profile(prior)
    finding = None
    if rebuilt_profile.get("present") and prior_profile.get("present"):
        finding = (
            "The release the closing packet delivered carries "
            f"{prior_profile['observations_2013_2026']:,} observations in "
            "2013-2026, so the ledger entry saying those rows were not "
            "cell-ingested was ACCURATE about that release. The rebuild "
            f"published here carries {rebuilt_profile['observations_2013_2026']:,}. "
            "The entry is resolved by publishing the rebuild, not by the entry "
            "having been wrong."
        )
    return {
        "published_rebuild": rebuilt_profile,
        "prior_delivered_release": prior_profile,
        "finding": finding,
        "selection_basis": (
            "Both releases are named explicitly in this tool. Neither was chosen "
            "by modification time, because the newest file on disk is whichever "
            "rebuild ran last and says nothing about what was delivered."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the rebuilt release.")
    parser.add_argument("--release", type=Path, default=REBUILT_RELEASE)
    parser.add_argument("--prior-release", type=Path, default=PRIOR_DELIVERED_RELEASE)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.release.is_file():
        print(f"no release database at {args.release}", file=sys.stderr)
        return 2

    out_dir: Path = args.out_dir
    published = out_dir / "published_release"
    published.mkdir(parents=True, exist_ok=True)

    # The published copy is made first and never rewritten afterwards, so its
    # digest is the digest of exactly what a consumer would download.
    immutable = published / "CYCLE35_COACHING_RELEASE_PUBLISHED.sqlite"
    shutil.copy2(args.release, immutable)
    release_digest = sha256_file(immutable)

    conn = sqlite3.connect(f"file:{immutable}?mode=ro", uri=True)
    try:
        coverage = bind_coverage(conn)
        layers = bind_layers(conn)
    finally:
        conn.close()

    generated = datetime.now(timezone.utc).isoformat()
    children = {
        "CYCLE35_RELEASE_COVERAGE_BINDING.json": {
            "artifact_type": "CYCLE35_RELEASE_COVERAGE_BINDING",
            "generated_at_utc": generated,
            "release_sha256": release_digest,
            **coverage,
        },
        "CYCLE35_RELEASE_LAYER_BINDING.json": {
            "artifact_type": "CYCLE35_RELEASE_LAYER_BINDING",
            "generated_at_utc": generated,
            "release_sha256": release_digest,
            **layers,
        },
        "CYCLE35_CAREER_TRANCHE_KEY_RECONCILIATION.json": {
            "artifact_type": "CYCLE35_CAREER_TRANCHE_KEY_RECONCILIATION",
            "generated_at_utc": generated,
            **bind_career_tranche(),
        },
        "CYCLE35_DELIVERED_RELEASE_COMPARISON.json": {
            "artifact_type": "CYCLE35_DELIVERED_RELEASE_COMPARISON",
            "generated_at_utc": generated,
            **compare_releases(immutable, args.prior_release),
        },
    }

    # Children are written and closed BEFORE the parent is composed, so every
    # digest the parent carries belongs to a file that will not change again.
    child_digests: dict[str, Any] = {}
    for name, payload in children.items():
        path = out_dir / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        child_digests[name] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }

    manifest = {
        "artifact_type": "CYCLE35_PUBLISHED_RELEASE_MANIFEST",
        "generated_at_utc": generated,
        "published_release": {
            "path": str(immutable),
            "sha256": release_digest,
            "bytes": immutable.stat().st_size,
            "rebuilt_from": str(args.release),
        },
        "children": child_digests,
        "sealing_order": (
            "The published database is copied and hashed first, then every child "
            "artifact is written and hashed, then this manifest is composed from "
            "those digests. This manifest does not contain its own hash; that is "
            "recorded in the sidecar named below."
        ),
        "own_digest_sidecar": "CYCLE35_PUBLISHED_RELEASE_MANIFEST.sha256",
        "authorization": {
            "status": "IN_PROGRESS_LOCAL_WORK_REMAINS",
            "published_means": (
                "immutably written and digest-bound in the cycle run tree so its "
                "contents can be checked"
            ),
            "published_does_not_mean": (
                "merged, canonically activated, scientifically accepted, or "
                "released under any hold. None of those is authorized."
            ),
        },
    }
    manifest_path = out_dir / "CYCLE35_PUBLISHED_RELEASE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    sidecar = out_dir / "CYCLE35_PUBLISHED_RELEASE_MANIFEST.sha256"
    sidecar.write_text(
        f"{sha256_file(manifest_path)}  CYCLE35_PUBLISHED_RELEASE_MANIFEST.json\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "published_release_sha256": release_digest,
                "expected_cells": coverage["expected_cells"],
                "coverage_states": coverage["coverage_states"],
                "year_ranges": {
                    key: value["observations"]
                    for key, value in layers["year_ranges"].items()
                },
                "children_sealed": len(child_digests),
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
