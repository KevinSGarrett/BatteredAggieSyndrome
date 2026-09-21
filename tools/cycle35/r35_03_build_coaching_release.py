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
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aggie_analytics.cycle33.role_taxonomy import assignments_from_title  # noqa: E402
from r35_27_national_population_authority import (  # noqa: E402
    AUTHORITY_RECEIPT,
    build as build_population_authority,
)
from r35_28_staff_season_evidence import (  # noqa: E402
    BOUND as SEASON_BOUND,
    season_evidence,
)
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
    stats = {
        "files": [],
        "programs": 0,
        "expected_cells": 0,
        "rows_missing_season": 0,
        "rows_dated_by_declared_receipt_authority": 0,
    }
    seen_programs: set[str] = set()
    population_authority = {
        record["path"]: record
        for record in (build_population_authority().get("membership_files") or [])
    }
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
        # MF35-05 repair: a row's season must be PROVED, never assumed. The
        # builder previously dated any seasonless row to the CURRENT year,
        # which is the fabrication that finding named, and the repair was to
        # skip such rows entirely.
        #
        # Skipping them entirely also dropped the whole 2026 membership file,
        # because it carries no per-row season -- so the national denominator
        # silently stopped at 2023 while the same release held 10,510
        # observations labelled 2026. R35-27 resolves the missing half: a
        # file with no per-row season is bound to a season only when exactly
        # one declared /teams request's cached payload accounts for every
        # program in it. That is the request's declared authority, proved by
        # content. It is not the wall clock, and an unproved file still binds
        # nothing.
        file_authority = population_authority.get(str(path))
        fallback_season = None
        if file_authority and file_authority.get("authority") == AUTHORITY_RECEIPT:
            seasons = file_authority.get("seasons") or []
            fallback_season = int(seasons[0]) if seasons else None
            stats["files"][-1]["season_authority"] = file_authority["authority"]
            stats["files"][-1]["bound_season"] = fallback_season
            stats["files"][-1]["bound_receipt_sha256"] = (
                file_authority.get("receipt_linkage") or {}
            ).get("bound_receipt_sha256")

        for row in rows:
            program_id = str(row.get("program_id") or "")
            if not program_id:
                continue
            raw_season = row.get("season")
            if raw_season in (None, "", 0):
                if fallback_season is None:
                    stats["rows_missing_season"] += 1
                    continue
                season = fallback_season
                stats["rows_dated_by_declared_receipt_authority"] += 1
            else:
                season = int(raw_season)
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
    # One evidence read per capture, not per row: 880 rows share 266 pages.
    season_by_capture: dict[str, dict[str, Any]] = {}
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
        # The season used to come from `strata.era`, which is the literal
        # string "CURRENT" for every official-staff row -- so no confirmed
        # assertion could be placed in a program-season-role cell. It now
        # comes from what the capture says about itself, and stays
        # unspecified when the capture says nothing.
        if raw_path not in season_by_capture:
            season_by_capture[raw_path] = season_evidence(Path(raw_path))
        evidence = season_by_capture[raw_path]
        if evidence.get("state") == SEASON_BOUND and evidence.get("bound_season"):
            season = str(evidence["bound_season"])
            date_precision = "SEASON_FROM_CAPTURE_STAFF_LABEL"
            stats["EPISODE_SEASON_BOUND_BY_STAFF_LABEL"] += 1
        else:
            season = str(row.get("strata", {}).get("era") or "")
            date_precision = "SEASON_UNSPECIFIED"
            stats["EPISODE_SEASON_UNSPECIFIED_" + str(evidence.get("state"))] += 1
        observation_id = add_observation(
            conn,
            source_file_id=source_file_id,
            locator=str(row.get("rebuilt_record_selector") or row.get("episode_key")),
            parser_identity=PARSER_IDENTITY,
            observed_person=person,
            observed_title=title,
            observed_program=program_id,
            # MF35 follow-up (20260920T224700Z): the independent entailment
            # checker verifies subject/program/SEASON binding against what
            # the observation itself recorded, not just against the
            # episode's own claim. This previously never recorded a season
            # at all, so no observation could ever attest to the episode's
            # season -- fixed by recording the same season value used below
            # for the episode, since both come from the same source row.
            observed_season=season,
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
            source_program_id=program_id,
        )
        episode_id = add_episode(
            conn,
            person_id=person_id,
            program_id=program_id,
            season=season,
            date_precision=date_precision,
            evidence_layer=LAYER_OFFICIAL,
        )
        # MF35-05 repair: `principal_role_families(title)` only names the
        # HC/OC/DC bucket a title falls into, with no qualifiers and no
        # position-specific detail. Taking `families[0]` and stuffing the
        # REST of that bucket list into `qualifiers` lost real, already-
        # parsed structure -- a title reading "Assistant Head Coach/Co-
        # Defensive Coordinator/Inside Linebackers" has three real
        # assignments (assistant head coach, a CO-shared DC seat, and an
        # inside linebackers position role) and a real CO qualifier on the
        # DC seat, none of which `families[1:]` (itself just OTHER FAMILY
        # NAMES, not qualifiers) could represent.
        # `assignments_from_title` is the module's own lossless parser:
        # one `formal_role_assertion` row per assignment it finds, each
        # with its own qualifiers and occupancy-derived principal_role_blocked.
        assignments = assignments_from_title(title)
        if not assignments:
            add_role(
                conn,
                episode_id=episode_id,
                role_family="UNSPECIFIED_ASSISTANT",
                exact_title_text=title,
                qualifiers=[],
                evidence_layer=LAYER_OFFICIAL,
                principal_role_blocked=True,
                supporting_observations=[observation_id],
            )
        else:
            for assignment in assignments:
                add_role(
                    conn,
                    episode_id=episode_id,
                    role_family=assignment["role"],
                    exact_title_text=title,
                    qualifiers=assignment["qualifiers"],
                    evidence_layer=LAYER_OFFICIAL,
                    principal_role_blocked=assignment["occupancy"]
                    not in ("PRINCIPAL", "CO_SHARED"),
                    supporting_observations=[observation_id],
                )
        stats["PROMOTED_OFFICIAL"] += 1
        stats["ROLE_ASSIGNMENTS_EMITTED"] += len(assignments) or 1
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



#: The ONLY artifact_type ingest_career_tranche() may consume. A career
#: tranche moves through two distinct, differently-shaped stages:
#: r35_05_career_tranche.py's first pass (artifact_type
#: CYCLE35_R35_05_CAREER_TRANCHE, field "keys", resolved cache-first only)
#: and r35_05_resolve_missing_keys.py's second pass (artifact_type
#: CYCLE35_R35_05_CAREER_TRANCHE_SECOND_PASS, field "final_keys", the
#: MISSING keys re-attempted from an independent evidence surface). This
#: ingester is documented -- and was always intended -- to consume only the
#: resolved second-pass artifact.
CAREER_TRANCHE_SECOND_PASS_ARTIFACT_TYPE = "CYCLE35_R35_05_CAREER_TRANCHE_SECOND_PASS"

#: Dispositions the second-pass tranche is allowed to declare per key. An
#: unrecognized disposition is a contract violation, not a value to pass
#: through uninterpreted.
_CAREER_KEY_KNOWN_DISPOSITIONS = frozenset(
    {
        "ACCEPTED_SINGLE_SOURCE",
        "ACCEPTED_CORROBORATED",
        "CONFLICT",
        "MISSING_NO_EVIDENCE",
        "AMBIGUOUS",
        "NOT_ATTEMPTED_BUDGET_EXHAUSTED",
    }
)

_CAREER_KEY_REQUIRED_FIELDS = (
    "key_id",
    "program_id",
    "season",
    "role",
    "disposition",
    "display_name",
)


def validate_career_tranche_contract(payload: Any) -> list[str]:
    """Every reason this payload may not be trusted as a resolved
    second-pass career tranche. An empty list means the contract holds.

    Cycle #35 manager follow-up (20260920T224700Z): ingest_career_tranche
    previously read `payload.get("final_keys") or []` with no check that
    the payload was actually the artifact this ingester is documented to
    consume. Feeding it the FIRST-PASS artifact (which has "keys", not
    "final_keys") silently ingested zero rows while still returning
    "INGESTED_AS_REVISION_BOUND_CANDIDATES" -- a success-shaped state for a
    payload that was never usable. This function is what makes that
    silence impossible: a missing or wrong-stage required list is a named,
    returned violation, never a default to [].
    """

    reasons: list[str] = []
    if not isinstance(payload, dict):
        return [f"PAYLOAD_NOT_AN_OBJECT: got {type(payload).__name__}"]

    artifact_type = payload.get("artifact_type")
    if artifact_type != CAREER_TRANCHE_SECOND_PASS_ARTIFACT_TYPE:
        reasons.append(
            "WRONG_STAGE_ARTIFACT_TYPE: expected "
            f"{CAREER_TRANCHE_SECOND_PASS_ARTIFACT_TYPE!r}, got {artifact_type!r}. "
            "This ingester consumes the RESOLVED second-pass tranche only; "
            "run r35_05_resolve_missing_keys.py on the first-pass output "
            "before feeding it here."
        )

    has_keys = "keys" in payload
    has_final_keys = "final_keys" in payload
    if has_keys and has_final_keys:
        reasons.append(
            "AMBIGUOUS_DUAL_FIELD_PAYLOAD: payload declares both 'keys' "
            "and 'final_keys'. The real producer schema never emits both "
            "in one artifact; refusing to guess which one is authoritative."
        )
    elif has_keys and not has_final_keys:
        reasons.append(
            "FIRST_PASS_FIELD_PRESENT_NOT_SECOND_PASS: payload has 'keys' "
            "but no 'final_keys' -- this is the shape of the first-pass "
            "predeclaration/resolution artifact, not the resolved "
            "second-pass tranche."
        )
    elif not has_final_keys:
        reasons.append(
            "MISSING_REQUIRED_FIELD_FINAL_KEYS: payload has no 'final_keys' "
            "field. A missing required list must never silently default to "
            "an empty ingest."
        )

    if reasons:
        # The top-level field shape is already broken; per-key schema
        # checks below would just add noise about a field that may not
        # even be present or list-shaped.
        return reasons

    final_keys = payload.get("final_keys")
    if not isinstance(final_keys, list):
        return [f"FINAL_KEYS_NOT_A_LIST: got {type(final_keys).__name__}"]

    declared_count = payload.get("key_count")
    if declared_count is not None and declared_count != len(final_keys):
        reasons.append(
            f"DECLARED_COUNT_MISMATCH: key_count={declared_count!r} but "
            f"final_keys has {len(final_keys)} entries."
        )

    seen: dict[str, Any] = {}
    for index, key in enumerate(final_keys):
        if not isinstance(key, dict):
            reasons.append(f"KEY_NOT_AN_OBJECT: index {index} is {type(key).__name__}")
            continue
        missing = [
            field
            for field in _CAREER_KEY_REQUIRED_FIELDS
            if key.get(field) in (None, "")
        ]
        if missing:
            reasons.append(
                f"KEY_MISSING_REQUIRED_FIELDS: index {index} "
                f"(key_id={key.get('key_id')!r}) missing {missing}"
            )
            continue
        disposition = str(key.get("disposition"))
        if disposition not in _CAREER_KEY_KNOWN_DISPOSITIONS:
            reasons.append(
                f"KEY_UNKNOWN_DISPOSITION: key_id={key.get('key_id')!r} "
                f"disposition={disposition!r}"
            )
        key_id = str(key.get("key_id"))
        if key_id in seen:
            if seen[key_id] != key:
                reasons.append(
                    f"DUPLICATE_KEY_ID_CONFLICTING_CONTENT: key_id={key_id!r}"
                )
            # An identical replayed row under the same key_id is not itself
            # a contract violation -- see the idempotent-replay tests.
        else:
            seen[key_id] = key
    return reasons


#: A wikitext infobox parameter label, e.g. "| oc_year =". The career
#: tranche extractor reads the value of a named infobox field; when that
#: field is EMPTY it can run on and capture the next parameter's label
#: instead. Two keys reached canonical_person that way -- K29 (Towson 2007)
#: and K47 (Butler 2009), both dispositioned ACCEPTED_SINGLE_SOURCE with
#: resolved_people = ["| oc_year ="], while off_coach is empty in both
#: cached sources. An empty field is MISSING evidence, not a person.
_INFOBOX_PARAMETER_LABEL = re.compile(r"^\|?\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*$")
_WIKITEXT_MARKUP = ("{{", "}}", "[[", "]]", "|")


def person_name_is_bindable(value: Any) -> bool:
    """Whether a resolved value can be bound as a person at all.

    Deliberately narrow: it rejects what is demonstrably extractor residue,
    not what merely looks unusual. A real name never starts with a pipe and
    never consists of a bare `parameter =` label. Anything rejected here is
    reported with its raw value rather than dropped, because an empty source
    field and a name we failed to parse need different fixes.
    """

    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    if _INFOBOX_PARAMETER_LABEL.match(text):
        return False
    return not any(token in text for token in _WIKITEXT_MARKUP)


def ingest_career_tranche(conn: sqlite3.Connection, tranche_path: Path) -> dict[str, Any]:
    """The resolved career tranche, as revision-bound candidates.

    These are retrospective Wikimedia assertions, so they enter at
    CANDIDATE_SINGLE_SOURCE and never at an official layer. A CONFLICT key
    produces a conflict row with BOTH occupants preserved; neither wins.

    A wrong-stage or malformed tranche file does NOT raise: it is one
    optional input among several independent sources in the same build
    transaction (membership, staff, the Cycle #34 transcription, the user
    corpus), and this ingester already treats "no career tranche supplied"
    as a valid, non-corrupting state (`CAREER_TRANCHE_NOT_PRESENT`) rather
    than aborting the release. "supplied but invalid" gets the same
    treatment -- ingest nothing from it, but never abort the other
    sources' already-valid data over one bad optional file. What MUST
    change is that the rejection is unmissable: `state` is explicitly
    `REJECTED_INVALID_CONTRACT` with every violation named, never the
    same success-shaped state a real ingest gets.
    """

    if not tranche_path.is_file():
        return {"state": "CAREER_TRANCHE_NOT_PRESENT"}
    payload = json.loads(tranche_path.read_text(encoding="utf-8"))
    contract_violations = validate_career_tranche_contract(payload)
    if contract_violations:
        return {
            "state": "REJECTED_INVALID_CONTRACT",
            "contract_violations": contract_violations,
            "artifact_type_found": (
                payload.get("artifact_type") if isinstance(payload, dict) else None
            ),
            "tranche_sha256": hashlib.sha256(tranche_path.read_bytes()).hexdigest(),
        }
    source_file_id = register_source_file(
        conn,
        tranche_path,
        source_class="WIKIMEDIA_REVISION_BOUND_RETROSPECTIVE",
        rights_state="PUBLIC_WIKIMEDIA_CC_BY_SA_ATTRIBUTION_REQUIRED",
        acquisition_receipt="CYCLE35_R35_05_CAREER_TRANCHE",
    )
    stats: Counter = Counter()
    seen_key_ids: set[str] = set()
    for key in payload["final_keys"]:
        key_id = str(key.get("key_id"))
        if key_id in seen_key_ids:
            # A duplicate/replayed key within one payload: content-identity
            # already proven by validate_career_tranche_contract (a
            # conflicting duplicate would have been rejected above), so
            # this is a harmless replay -- count it, do not double-ingest.
            stats["DUPLICATE_KEY_ID_IN_PAYLOAD_SKIPPED"] += 1
            continue
        seen_key_ids.add(key_id)
        disposition = str(key.get("disposition"))
        declared_people = list(key.get("resolved_people") or [])
        people = [p for p in declared_people if person_name_is_bindable(p)]
        rejected = [p for p in declared_people if not person_name_is_bindable(p)]
        if rejected:
            # The key's own source carried no usable name. Record the
            # correction against the declared disposition rather than
            # letting an extractor artifact stand as an accepted person.
            stats["KEY_VALUES_REJECTED_AS_NOT_A_NAME"] += 1
            stats.setdefault("rejected_values", []).append(
                {
                    "key_id": key_id,
                    "declared_disposition": disposition,
                    "corrected_disposition": "MISSING_NO_EVIDENCE"
                    if not people
                    else disposition,
                    "rejected_values": rejected,
                    "reason": "SOURCE_VALUE_IS_A_WIKITEXT_PARAMETER_LABEL_NOT_A_NAME",
                }
            )
            if not people:
                disposition = "MISSING_NO_EVIDENCE"
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
            source_program_id=program_id,
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
            # exact_title_text must equal the linked observation's own
            # observed_title (set to `role` below) for the entailment check
            # to hold -- `second_pass_parameter` is provenance (which
            # infobox parameter matched, e.g. "hc"), not the asserted title
            # text, and using it here previously created a mismatch the
            # entailment checker would have flagged as unentailed.
            exact_title_text=role,
            qualifiers=[],
            evidence_layer=LAYER_CANDIDATE,
            supporting_observations=observation_ids,
        )
        stats["PROMOTED_CANDIDATE"] += 1
    out = dict(stats)
    # A contract-valid payload with genuinely zero resolvable keys (every
    # key MISSING_NO_EVIDENCE, or a payload with an empty final_keys list)
    # must report that plainly -- never the same success-shaped state a
    # real multi-row ingest gets, which is exactly what let a wrong-stage
    # payload masquerade as a successful ingest before this repair.
    out["state"] = (
        "INGESTED_AS_REVISION_BOUND_CANDIDATES"
        if stats["OBSERVATIONS"] > 0
        else "CONTRACT_VALID_BUT_ZERO_KEYS_RESOLVED"
    )
    out["contract_validated"] = True
    out["final_keys_count"] = len(payload["final_keys"])
    out["tranche_sha256"] = hashlib.sha256(tranche_path.read_bytes()).hexdigest()
    return out



USER_CORPUS_CELLS = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
    r"\CYCLE33_USER_CORPUS_2000_2012_STAFF_CELLS.jsonl"
)
#: MF35-11 (Cycle #35 manager follow-up, 20260920T224700Z): the 2013-2026
#: rows were always parsed by the same import_snapshot() the 2000-2012 file
#: came from; they were only ever filtered out downstream, not
#: unavailable. See tools/cycle35/r35_11_user_corpus_2013_2026_cells.py.
USER_CORPUS_CELLS_2013_2026 = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs"
    r"\20260920T224700Z_mf35_11_user_cells"
    r"\CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS.jsonl"
)


def ingest_user_corpus_cells(
    conn: sqlite3.Connection,
    *,
    cells_path: Path = USER_CORPUS_CELLS,
    acquisition_receipt: str = "CYCLE33_USER_CORPUS_2000_2012_STAFF_CELLS",
) -> dict[str, Any]:
    """The user research corpus at CELL grain, for whichever year range
    `cells_path` names.

    MF35-11 (Cycle #35 manager follow-up, 20260920T224700Z): registering 54
    files proved the population exists; it did not make a single row
    queryable, and this function originally only ever read the 2000-2012
    file -- ingesting all years requires calling it once per available
    cell file, not registering more source files. Every cell enters as
    USER_COMPILED_RESEARCH_OBSERVATION at CANDIDATE layer -- every one
    carries `verified: false` from its own producer, so nothing here is
    promoted, and a cell whose program cannot be resolved against the
    canonical population is retained UNRESOLVED rather than dropped.
    """

    if not cells_path.is_file():
        return {"state": "USER_CORPUS_CELLS_NOT_PRESENT", "cells_path": str(cells_path)}
    source_file_id = register_source_file(
        conn,
        cells_path,
        source_class="USER_COMPILED_RESEARCH_OBSERVATION",
        rights_state="PRIVATE_USER_RESEARCH_NOT_REDISTRIBUTABLE",
        acquisition_receipt=acquisition_receipt,
    )
    crosswalk = build_crosswalk(
        read_jsonl(OUTPUTS / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl")
        + read_jsonl(OUTPUTS / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl")
        + read_jsonl(OUTPUTS / "CURRENT_2026_PROGRAMS.jsonl")
    )
    stats: Counter = Counter()
    unresolved_names: Counter = Counter()
    for row in read_jsonl(cells_path):
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
            user_cells_2000_2012 = ingest_user_corpus_cells(conn)
            user_cells_2013_2026 = ingest_user_corpus_cells(
                conn,
                cells_path=USER_CORPUS_CELLS_2013_2026,
                acquisition_receipt="CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS",
            )
            user_cells = {
                "2000_2012": user_cells_2000_2012,
                "2013_2026": user_cells_2013_2026,
                "combined_observations": (
                    user_cells_2000_2012.get("OBSERVATIONS", 0)
                    + user_cells_2013_2026.get("OBSERVATIONS", 0)
                ),
                "years_covered": "2000-2026" if (
                    user_cells_2000_2012.get("state") == "INGESTED_AT_CELL_GRAIN_AS_CANDIDATES"
                    and user_cells_2013_2026.get("state") == "INGESTED_AT_CELL_GRAIN_AS_CANDIDATES"
                ) else "PARTIAL_SEE_PER_RANGE_STATE",
            }
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
            "user_corpus_cells": {
                "2000_2012": {
                    k: v for k, v in user_cells["2000_2012"].items()
                    if k != "top_unresolved_program_names"
                },
                "2013_2026": {
                    k: v for k, v in user_cells["2013_2026"].items()
                    if k != "top_unresolved_program_names"
                },
                "combined_observations": user_cells["combined_observations"],
                "years_covered": user_cells["years_covered"],
            },
            "career_tranche": career,
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
