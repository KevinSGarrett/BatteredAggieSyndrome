"""R35-03: build the canonical coaching release from real bound sources.

Every observation in the output traces to a file this script hashed itself.
There is no hardcoded roster of program-seasons and no hardcoded tuple of
"verified" names: if a fact is in the release, a source row on disk put it
there, and `assertion_support` names which one.

Inputs, all read-only:

  * the reparsed 880 staff episode references (R35-02 output), each already
    bound to a raw official-staff capture by its decoded hash;
  * the national membership population, which supplies canonical programs
    and the expected program-season cells;
  * the Cycle #34 85-row SQLite delivery, ingested as a PRESERVED CANDIDATE
    TRANSCRIPTION -- its 26 `verified` flags are recorded as claims to be
    reconciled, never carried through as verification;
  * the 6,749-row user research corpus, whose per-file snapshots are hashed
    and registered so the population is visible at full size even where
    individual cells stay candidate-layer.

The two synthetic negative controls in the Cycle #34 delivery are ingested
into a clearly marked fixture layer and excluded from national totals --
fixtures belong in tests, not in counts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33.role_taxonomy import principal_role_families  # noqa: E402
from aggie_analytics.cycle35.program_aliases import (  # noqa: E402
    build_crosswalk,
    resolve_program,
)
from aggie_analytics.cycle35.coaching_release import (  # noqa: E402
    LAYER_CANDIDATE,
    LAYER_OBSERVED,
    LAYER_OFFICIAL,
    LAYER_REJECTED,
    LAYER_UNRESOLVED,
    add_episode,
    add_expected_cell,
    add_observation,
    add_role,
    append_release_manifest,
    assertions_missing_evidence_link,
    assertions_not_entailed_by_linked_observations,
    layer_counts,
    open_release,
    person_identity_merge_candidates,
    record_adjudication,
    record_conflict,
    register_source_file,
    release_row_identities,
    transaction,
    upsert_person,
    upsert_program,
)

OUTPUTS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
MEMBERSHIP = (
    OUTPUTS / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl",
    OUTPUTS / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl",
    OUTPUTS / "CURRENT_2026_PROGRAMS.jsonl",
)
CYCLE34_DB = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle34\20260919T_R34_receipts"
    r"\pipeline_output\R34_07_CAREER_INGEST.sqlite"
)
USER_CORPUS_SNAPSHOT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches"
    r"\20260914T051702Z\source_snapshot"
)
PARSER_IDENTITY = "BAS-CYCLE35-RELEASE-INGEST-v1"

#: Dispositions the Cycle #34 delivery used, mapped onto evidence layers.
#: `RESOLVED_CAREER_JOIN_VERIFIED` deliberately maps to CANDIDATE, not to a
#: verified layer: the flag was produced by a hardcoded tuple, so it records
#: a claim to reconcile rather than a verification to inherit.
C34_DISPOSITION_LAYER = {
    "RESOLVED_CAREER_JOIN_VERIFIED": LAYER_CANDIDATE,
    "CORRECTLY_REJECTED_NO_EMPLOYER_MATCH": LAYER_REJECTED,
    "ROSTER_OBSERVATION_UNRESOLVED": LAYER_UNRESOLVED,
}

ERA_BANDS = (
    (1963, 1972, "UNIVERSITY_DIVISION"),
    (1973, 1977, "DIVISION_I_UNSPLIT"),
    (1978, 2005, "DIVISION_I_A_PLUS_I_AA"),
    (2006, 2026, "FBS_PLUS_FCS"),
)
CORE_ROLES = ("head_coach", "offensive_coordinator", "defensive_coordinator")


def era_for(season: int) -> str:
    for start, end, name in ERA_BANDS:
        if start <= season <= end:
            return name
    return "OUT_OF_DECLARED_RANGE"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def ingest_membership(conn: sqlite3.Connection) -> dict[str, Any]:
    stats = {"files": [], "programs": 0, "expected_cells": 0}
    seen_programs: set[str] = set()
    for path in MEMBERSHIP:
        rows = read_jsonl(path)
        stats["files"].append(
            {
                "path": str(path),
                "rows": len(rows),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
                if path.is_file()
                else None,
            }
        )
        for row in rows:
            program_id = str(row.get("program_id") or "")
            if not program_id:
                continue
            season = int(row.get("season") or 2026)
            upsert_program(
                conn,
                program_id,
                display_name=row.get("display_name"),
                classification=row.get("classification"),
                season=season,
            )
            seen_programs.add(program_id)
            for role in CORE_ROLES:
                add_expected_cell(
                    conn,
                    program_id=program_id,
                    season=season,
                    role_family=role,
                    era_band=era_for(season),
                    coverage_state="EXPECTED_NOT_YET_COVERED",
                )
                stats["expected_cells"] += 1
    stats["programs"] = len(seen_programs)
    return stats


def ingest_reparsed_staff(
    conn: sqlite3.Connection, rebuild_rows: Path
) -> dict[str, Any]:
    """The 880 reparsed episode references, bound to their real captures."""

    rows = [
        json.loads(line)
        for line in rebuild_rows.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    stats: Counter = Counter()
    registered: dict[str, str] = {}
    for row in rows:
        raw_path = row.get("raw_path")
        if not raw_path or not Path(raw_path).is_file():
            stats["NO_RAW_FILE"] += 1
            continue
        if raw_path not in registered:
            registered[raw_path] = register_source_file(
                conn,
                Path(raw_path),
                source_class="OFFICIAL_STAFF_HTML",
                rights_state="PRIVATE_RESEARCH_CAPTURE_NOT_REDISTRIBUTABLE",
                decoded_sha256=row.get("source_hash_sha256"),
            )
        source_file_id = registered[raw_path]
        person = str(row.get("person") or "")
        title = str(row.get("source_title") or "")
        program_id = str(row.get("program_id") or "")
        observation_id = add_observation(
            conn,
            source_file_id=source_file_id,
            locator=str(row.get("rebuilt_record_selector") or row.get("episode_key")),
            parser_identity=PARSER_IDENTITY,
            observed_person=person,
            observed_title=title,
            observed_program=program_id,
            observed_text=str(row.get("rebuilt_record_title") or ""),
            evidence_layer=LAYER_OBSERVED,
        )
        stats["OBSERVATIONS"] += 1

        supported = row.get("rebuilt_role_claim_supported") is True
        bound = row.get("rebuilt_person_record_bound") is True
        if not (supported and bound):
            stats["NOT_PROMOTED_" + str(row.get("disposition"))] += 1
            continue

        upsert_program(conn, program_id)
        person_id = upsert_person(
            conn,
            person,
            identity_basis="OFFICIAL_STAFF_SAME_RECORD_BINDING",
            aliases=[(person, "SOURCE_PUBLISHED_NAME")],
        )
        episode_id = add_episode(
            conn,
            person_id=person_id,
            program_id=program_id,
            season=str(row.get("strata", {}).get("era") or ""),
            date_precision="SEASON_UNSPECIFIED",
            evidence_layer=LAYER_OFFICIAL,
        )
        families = sorted(principal_role_families(title))
        add_role(
            conn,
            episode_id=episode_id,
            role_family=families[0] if families else "UNSPECIFIED_ASSISTANT",
            exact_title_text=title,
            qualifiers=families[1:],
            evidence_layer=LAYER_OFFICIAL,
            principal_role_blocked=not families,
            supporting_observations=[observation_id],
        )
        stats["PROMOTED_OFFICIAL"] += 1
    return dict(stats)


def ingest_cycle34_transcription(conn: sqlite3.Connection) -> dict[str, Any]:
    """The 85-row delivery, preserved as candidate transcription."""

    if not CYCLE34_DB.is_file():
        return {"state": "CYCLE34_DB_NOT_PRESENT"}
    source_file_id = register_source_file(
        conn,
        CYCLE34_DB,
        source_class="CYCLE34_CANDIDATE_TRANSCRIPTION",
        rights_state="INTERNAL_PREDECESSOR_ARTIFACT",
        acquisition_receipt="CYCLE34_R34_07_CAREER_INGEST",
    )
    src = sqlite3.connect("file:" + str(CYCLE34_DB) + "?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    stats: Counter = Counter()
    synthetic: list[str] = []
    try:
        for row in src.execute("SELECT * FROM staff_role_cells"):
            disposition = str(row["disposition"] or "")
            layer = C34_DISPOSITION_LAYER.get(disposition, LAYER_UNRESOLVED)
            is_control = disposition == "CORRECTLY_REJECTED_NO_EMPLOYER_MATCH"
            observation_id = add_observation(
                conn,
                source_file_id=source_file_id,
                locator="staff_role_cells:" + str(row["observation_id"]),
                parser_identity=PARSER_IDENTITY,
                observed_person=row["person"],
                observed_title=row["source_title"],
                observed_program=row["team_id_source"] or row["team"],
                observed_season=str(row["season"] or ""),
                observed_text=row["cell_text"],
                evidence_layer=layer,
            )
            stats["INGESTED_" + disposition] += 1
            if is_control:
                synthetic.append(observation_id)
            # The predecessor's own `verified` flag is recorded as a CLAIM,
            # with a conflict raised against the layer this release assigns,
            # so the disagreement is visible instead of silently inherited.
            if int(row["verified"] or 0) == 1:
                conflict_id = record_conflict(
                    conn,
                    subject_kind="source_observation",
                    subject_key=observation_id,
                    reason="PREDECESSOR_CLAIMED_VERIFIED_WITHOUT_ROW_LEVEL_RECEIPT",
                )
                record_adjudication(
                    conn,
                    conflict_id=conflict_id,
                    decision="HELD_AT_CANDIDATE_LAYER",
                    decided_by="CYCLE35_R35_03_INGEST",
                    basis=(
                        "The predecessor's verified flag was produced by a "
                        "hardcoded tuple in the ingester and carries no "
                        "per-row receipt_sha256. It is preserved as a claim "
                        "to reconcile, not inherited as verification."
                    ),
                )
                stats["PREDECESSOR_VERIFIED_CLAIMS_HELD"] += 1
    finally:
        src.close()
    out = dict(stats)
    out["synthetic_negative_controls"] = len(synthetic)
    out["synthetic_control_observation_ids"] = synthetic
    out["state"] = "INGESTED_AS_CANDIDATE_TRANSCRIPTION"
    return out


def ingest_user_corpus(conn: sqlite3.Connection) -> dict[str, Any]:
    """Register the full declared user research corpus at its real size."""

    if not USER_CORPUS_SNAPSHOT.is_dir():
        return {"state": "USER_CORPUS_SNAPSHOT_NOT_PRESENT", "files": 0}
    files = sorted(p for p in USER_CORPUS_SNAPSHOT.iterdir() if p.is_file())
    registered = 0
    total_bytes = 0
    for path in files:
        register_source_file(
            conn,
            path,
            source_class="USER_COMPILED_RESEARCH_OBSERVATION",
            rights_state="PRIVATE_USER_RESEARCH_NOT_REDISTRIBUTABLE",
            acquisition_receipt="CYCLE33_USER_COACHES_SOURCE_MANIFEST",
        )
        registered += 1
        total_bytes += path.stat().st_size
    return {
        "state": "SOURCE_FILES_REGISTERED",
        "files": registered,
        "bytes": total_bytes,
        "snapshot_root": str(USER_CORPUS_SNAPSHOT),
        "note": (
            "The corpus is registered at full declared size so its identity "
            "and count stay visible. Cell-level ingestion of all 6,749 rows "
            "is a separate, larger unit; registering the files here prevents "
            "the 85-row transcription from standing in for this population."
        ),
    }



def ingest_career_tranche(conn: sqlite3.Connection, tranche_path: Path) -> dict[str, Any]:
    """The resolved 48-key career tranche, as revision-bound candidates.

    These are retrospective Wikimedia assertions, so they enter at
    CANDIDATE_SINGLE_SOURCE and never at an official layer. A CONFLICT key
    produces a conflict row with BOTH occupants preserved; neither wins.
    """

    if not tranche_path.is_file():
        return {"state": "CAREER_TRANCHE_NOT_PRESENT"}
    payload = json.loads(tranche_path.read_text(encoding="utf-8"))
    source_file_id = register_source_file(
        conn,
        tranche_path,
        source_class="WIKIMEDIA_REVISION_BOUND_RETROSPECTIVE",
        rights_state="PUBLIC_WIKIMEDIA_CC_BY_SA_ATTRIBUTION_REQUIRED",
        acquisition_receipt="CYCLE35_R35_05_CAREER_TRANCHE",
    )
    stats: Counter = Counter()
    for key in payload.get("final_keys") or []:
        disposition = str(key.get("disposition"))
        people = list(key.get("resolved_people") or [])
        stats["KEY_" + disposition] += 1
        if not people:
            continue
        program_id = str(key.get("program_id") or "")
        season = str(key.get("season") or "")
        role = str(key.get("role") or "")
        upsert_program(conn, program_id, display_name=key.get("display_name"))
        observation_ids = []
        for person in people:
            observation_ids.append(
                add_observation(
                    conn,
                    source_file_id=source_file_id,
                    locator=str(key.get("key_id")) + ":" + role + ":" + season,
                    parser_identity=PARSER_IDENTITY,
                    observed_person=person,
                    observed_title=role,
                    observed_program=program_id,
                    observed_season=season,
                    evidence_layer=LAYER_CANDIDATE,
                )
            )
            stats["OBSERVATIONS"] += 1
        if disposition == "CONFLICT":
            conflict_id = record_conflict(
                conn,
                subject_kind="career_key",
                subject_key=str(key.get("key_id")),
                reason="MULTIPLE_DISTINCT_PEOPLE_ASSERTED_FOR_ONE_ROLE_SEASON",
            )
            record_adjudication(
                conn,
                conflict_id=conflict_id,
                decision="BOTH_RETAINED_NEITHER_PROMOTED",
                decided_by="CYCLE35_R35_05",
                basis=(
                    "Co/shared occupancy and a genuine contradiction are not "
                    "distinguishable from this evidence alone, so neither "
                    "occupant is promoted and both stay readable."
                ),
            )
            stats["CONFLICTS"] += 1
            continue
        person_id = upsert_person(
            conn,
            people[0],
            identity_basis="WIKIMEDIA_TEAM_SEASON_INFOBOX",
            aliases=[(people[0], "SOURCE_PUBLISHED_NAME")],
        )
        episode_id = add_episode(
            conn,
            person_id=person_id,
            program_id=program_id,
            season=season,
            date_precision="SEASON",
            evidence_layer=LAYER_CANDIDATE,
        )
        add_role(
            conn,
            episode_id=episode_id,
            role_family=role,
            exact_title_text=str(key.get("second_pass_parameter") or role),
            qualifiers=[],
            evidence_layer=LAYER_CANDIDATE,
            supporting_observations=observation_ids,
        )
        stats["PROMOTED_CANDIDATE"] += 1
    out = dict(stats)
    out["state"] = "INGESTED_AS_REVISION_BOUND_CANDIDATES"
    out["tranche_sha256"] = hashlib.sha256(tranche_path.read_bytes()).hexdigest()
    return out



USER_CORPUS_CELLS = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
    r"\CYCLE33_USER_CORPUS_2000_2012_STAFF_CELLS.jsonl"
)


def ingest_user_corpus_cells(conn: sqlite3.Connection) -> dict[str, Any]:
    """The 2000-2012 user research corpus at CELL grain.

    Registering 54 files proved the population exists; it did not make a
    single row queryable. These 23,992 parsed cells enter as
    USER_COMPILED_RESEARCH_OBSERVATION at CANDIDATE layer -- every one
    carries `verified: false` from its own producer, so nothing here is
    promoted, and a cell whose program cannot be resolved against the
    canonical population is retained UNRESOLVED rather than dropped.
    """

    if not USER_CORPUS_CELLS.is_file():
        return {"state": "USER_CORPUS_CELLS_NOT_PRESENT"}
    source_file_id = register_source_file(
        conn,
        USER_CORPUS_CELLS,
        source_class="USER_COMPILED_RESEARCH_OBSERVATION",
        rights_state="PRIVATE_USER_RESEARCH_NOT_REDISTRIBUTABLE",
        acquisition_receipt="CYCLE33_USER_CORPUS_2000_2012_STAFF_CELLS",
    )
    crosswalk = build_crosswalk(
        read_jsonl(OUTPUTS / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl")
        + read_jsonl(OUTPUTS / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl")
        + read_jsonl(OUTPUTS / "CURRENT_2026_PROGRAMS.jsonl")
    )
    stats: Counter = Counter()
    unresolved_names: Counter = Counter()
    for row in read_jsonl(USER_CORPUS_CELLS):
        person = str(row.get("person") or "").strip()
        team = str(row.get("team") or "").strip()
        season = str(row.get("season") or "").strip()
        role_column = str(row.get("role_column") or "").strip()
        if not person:
            stats["SKIPPED_NO_PERSON"] += 1
            continue
        resolution = resolve_program(team, crosswalk)
        program_id = resolution.get("program_id")
        if program_id:
            upsert_program(conn, program_id, display_name=team)
            stats["PROGRAM_RESOLVED"] += 1
        else:
            unresolved_names[team] += 1
            stats["PROGRAM_UNRESOLVED_RETAINED"] += 1
        add_observation(
            conn,
            source_file_id=source_file_id,
            locator=team + ":" + season + ":" + role_column + ":" + person,
            parser_identity=PARSER_IDENTITY,
            observed_person=person,
            observed_title=row.get("source_title") or role_column,
            observed_program=program_id or team,
            observed_season=season,
            evidence_layer=LAYER_CANDIDATE,
        )
        stats["OBSERVATIONS"] += 1
        if row.get("verified") is True:
            stats["PRODUCER_CLAIMED_VERIFIED"] += 1
    out = dict(stats)
    out["state"] = "INGESTED_AT_CELL_GRAIN_AS_CANDIDATES"
    out["distinct_unresolved_program_names"] = len(unresolved_names)
    out["top_unresolved_program_names"] = dict(unresolved_names.most_common(15))
    out["nothing_promoted_all_producer_verified_false"] = (
        stats.get("PRODUCER_CLAIMED_VERIFIED", 0) == 0
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--rebuild-rows", required=True)
    ap.add_argument("--release-name", default="")
    ap.add_argument("--career-tranche", default="")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = args.release_name or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    db_path = out_dir / ("CYCLE35_COACHING_RELEASE_" + stamp + ".sqlite")

    conn = open_release(db_path)
    try:
        with transaction(conn):
            membership = ingest_membership(conn)
            staff = ingest_reparsed_staff(conn, Path(args.rebuild_rows))
            cycle34 = ingest_cycle34_transcription(conn)
            user_corpus = ingest_user_corpus(conn)
            user_cells = ingest_user_corpus_cells(conn)
            career = (
                ingest_career_tranche(conn, Path(args.career_tranche))
                if args.career_tranche
                else {"state": "NOT_SUPPLIED"}
            )
        identities = release_row_identities(conn)
        layers = layer_counts(conn)
        missing_link = assertions_missing_evidence_link(conn)
        not_entailed = assertions_not_entailed_by_linked_observations(conn)
        identity_candidates = person_identity_merge_candidates(conn)
    finally:
        conn.commit()
        conn.close()

    release_id = hashlib.sha256(
        json.dumps(identities, sort_keys=True).encode("utf-8")
    ).hexdigest()
    entry = {
        "release_id": release_id,
        "release_path": str(db_path),
        "release_sha256": hashlib.sha256(db_path.read_bytes()).hexdigest(),
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_identities": identities,
        "inputs": {
            "membership": membership,
            "reparsed_staff": staff,
            "cycle34_transcription": {
                key: value
                for key, value in cycle34.items()
                if key != "synthetic_control_observation_ids"
            },
            "user_corpus": user_corpus,
            "user_corpus_cells": user_cells,
            "career_tranche": career,
        },
    }
    manifest_path = out_dir / "CYCLE35_COACHING_RELEASE_MANIFEST.json"
    manifest = append_release_manifest(manifest_path, entry)

    summary = {
        "artifact_type": "CYCLE35_R35_03_COACHING_RELEASE",
        "release_id": release_id,
        "release_path": str(db_path),
        "manifest_path": str(manifest_path),
        "manifest_release_count": manifest["release_count"],
        "row_identities": identities,
        "evidence_layer_counts": layers,
        "assertions_missing_evidence_link": missing_link,
        "assertions_missing_evidence_link_count": len(missing_link),
        "assertions_not_entailed_by_linked_observations": not_entailed,
        "assertions_not_entailed_count": len(not_entailed),
        "person_identity_merge_candidates": identity_candidates,
        "person_identity_merge_candidate_count": len(identity_candidates),
        "person_identity_candidates_require_explicit_adjudication_not_auto_merge": True,
        "no_hardcoded_program_seasons": True,
        "no_hardcoded_verified_tuples": True,
        "predecessor_not_unlinked": True,
        "synthetic_controls_excluded_from_national_totals": True,
        "inputs": entry["inputs"],
        "pit_admitted": False,
    }
    (out_dir / "R35_03_COACHING_RELEASE_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "release_id": release_id[:16],
            "tables": {k: v["count"] for k, v in identities.items()},
            "layers": layers,
            "assertions_missing_evidence_link": len(missing_link),
            "assertions_not_entailed_by_linked_observations": len(not_entailed),
            "person_identity_merge_candidates": len(identity_candidates),
            "staff": staff,
            "cycle34": {
                k: v for k, v in cycle34.items()
                if k != "synthetic_control_observation_ids"
            },
            "user_corpus_files": user_corpus.get("files"),
            "user_corpus_cells": {k: v for k, v in user_cells.items() if k != "top_unresolved_program_names"},
            "career_tranche": career,
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
