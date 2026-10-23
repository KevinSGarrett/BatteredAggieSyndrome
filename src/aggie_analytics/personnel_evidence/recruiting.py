r"""National recruiting evidence 2010-2017 (BAT-735 bounded contribution to BAT-414, BAT-415 and BAT-416, Cycle #64
TP64-A01): the frozen rules, record schemas, shared decisions and the verifying read-only reader of the private
create-only ``national_recruiting_evidence_2010_2017`` release.

Every rule lives here, and the committed data contract ``configs/national_recruiting_evidence_2010_2017_contract.json``
must equal these constants (the builder refuses otherwise). The reader pins that contract's SHA-256, every source input
(whole-file SHA-256 and bytes), the requested-cell and capture universe, the observation key universe (per captured
recruiting partition: row count and key-sequence digest) and, once the first authorized build has materialized it, the
canonical profile (:data:`ANCHORS`, :data:`RECRUITING_PROFILE`).

Authority. Retained private source qualification only: RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED and
predictive skill NOT_ESTABLISHED for every record and answer. The source is the provider (CFBD, SRC-002) recruiting
players array of each requested cohort year 2010-2017, retrieved on 2026-08-10; a capture clock is never historical
known-at, the cohort year is never a date, and no rating version, publication, commitment, signing, enrollment,
decommitment or portal-event time exists in the source: every historical time stays null and PIT stays false. A
canonical program correspondence names a program; it is never membership, commitment, signing, enrollment, an
effective interval or a roster fact. A person correspondence is the exact existing source-namespace slot; it is never
roster, enrollment, availability or production proof. Ratings, rankings and stars are the source's typed values as
served (scale, version and upstream independence unknown); no imputation, conversion, talent prior or class score. The
national FBS/FCS recruit universe is NOT_ESTABLISHED: the 34 requested cells (15 captured, 19 quota-missing) and the
28,093 observations are the finite retained source, not national coverage.

Grains (explicit ``bas-personnel-evidence-query --recruiting-evidence`` mode only): ``recruiting-observation`` (the
permitted typed source fields of every observation with its capture, original zero-based ordinal and whole raw row
hash), ``recruiting-qualification`` (one source/person/program/value/time disposition per observation with every
witness), ``recruiting-partition`` (all 34 requested cells), ``recruiting-source`` (every pinned source file and every
referenced core registry row) and ``recruiting-summary`` (counts and distributions over the selected observations).

The reader (:class:`RecruitingEvidence`) needs no data root: before any row is served it verifies the location, run
manifest, database bytes, schema, meta claims, every record's exact members and JSON types (an integer is never a float
or a boolean), the complete expected collection of every grain, every observation rule, the exact re-derivation of every
qualification from its observation and witnesses, of every partition and file source from the pinned contract, of every
core-row witness's identity and hashes, of the summaries and the census, the content document, the database identity
document and the pinned canonical profile.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import sqlite3
import uuid
import zlib
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics import readonly_sqlite


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_line(value: object) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def is_int(value: Any) -> bool:
    """A JSON integer: neither a boolean nor an integral float."""
    return type(value) is int


def _io_path(path: Path) -> Path:
    """A path every file API can open: the extended form beyond the classic Windows limit (never re-normalized)."""
    text = os.fspath(path)
    if os.name == "nt" and not text.startswith("\\\\?\\") and len(os.path.abspath(text)) >= 250:
        return Path("\\\\?\\" + os.path.abspath(text))
    return Path(text)


def manifest_path_for(database: Path) -> Path:
    """``<data>/canonical/<population>/sha256/<id>/<db>`` -> ``<data>/manifests/<population>/sha256/<id>/run_manifest.json``."""
    db = Path(os.path.abspath(database))
    population_root = db.parent.parent.parent
    return population_root.parent.parent / "manifests" / population_root.name / "sha256" / db.parent.name / \
        "run_manifest.json"


def keys_sha256(keys: Iterable[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


def lines_sha256(lines: list[str]) -> str:
    return sha256_bytes("".join(line + "\n" for line in lines).encode("utf-8"))


# --------------------------------------------------------------------------------------------- identity and scope

POPULATION = "national_recruiting_evidence_2010_2017"
DB_FILE = "national_recruiting_evidence.sqlite"
CONTRACT_ID = "BAT-735-NATIONAL-RECRUITING-EVIDENCE-2010-2017-V1.0"
CONTRACT_REL = "configs/national_recruiting_evidence_2010_2017_contract.json"
CONTENT_SCHEMA = "BAS-RECRUITING-EVIDENCE-CONTENT-1"
DATABASE_SCHEMA = "BAS-RECRUITING-EVIDENCE-DATABASE-1"
DB_SCHEMA = "BAS-RECRUITING-EVIDENCE-DB-1"
PAYLOAD_SCHEMA = "BAS-RECRUITING-EVIDENCE-PAYLOAD-1"
CONTENT_STAGE = "recruiting-evidence-content"
DATABASE_STAGE = "recruiting-evidence-database"
SOURCE_ID = "SRC-002"
RECRUIT_DATASET = "recruiting_players"
PORTAL_DATASET = "transfer_portal"
#: The requested datasets of the acquisition run in their canonical order (cell order: dataset, then parameters).
DATASET_ORDER = ("recruiting_players", "transfer_portal", "coaches", "coach_seasons")
RECRUIT_SEASONS = (2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017)
IDENTITY_RE = re.compile(r"[0-9a-f]{64}\Z")
SHA_RE = IDENTITY_RE
RECRUIT_ID_RE = re.compile(r"[0-9]{1,12}\Z")
ATHLETE_ID_RE = re.compile(r"-?[0-9]{1,12}\Z")
PLAYER_ID_RE = re.compile(r"player_[0-9a-f]{32}\Z")
TEAM_ID_RE = re.compile(r"team_[0-9a-f]{32}\Z")
SEASON_TEXT_RE = re.compile(r"[0-9]{4}\Z")
PAGE_TEXT_RE = re.compile(r"-?([0-9]{1,12})\Z")
CAPTURE_ID_RE = re.compile(r"cap_[0-9a-f]{24}\Z")
UTC_SECOND_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
YEAR_START_RE = re.compile(r"([0-9]{4})-01-01\Z")

LABELS = {
    "evidence_label": "RETROSPECTIVE_RESEARCH",
    "trust_state": "UNTRUSTED_SHADOW",
    "pit_eligibility": "PIT_NOT_ADMITTED",
    "predictive_skill": "NOT_ESTABLISHED",
    "evidence_authority": "RETROSPECTIVE_SOURCE_OBSERVATION_AND_CORRESPONDENCE_NOT_EVENT_HISTORY",
    "source_clock": "SRC_002_CAPTURES_RETRIEVED_2026_08_10_NOT_HISTORICAL_KNOWN_AT",
    "rights": "PRIVATE_LOCAL_RESEARCH_SRC_002_NO_RAW_PAYLOAD_REDISTRIBUTION",
    "national_coverage": "NATIONAL_FBS_FCS_RECRUIT_UNIVERSE_NOT_ESTABLISHED",
}
RECORD_LABEL_KEYS = ("evidence_label", "trust_state", "pit_eligibility", "predictive_skill")
RECORD_LABELS = {k: LABELS[k] for k in RECORD_LABEL_KEYS}

# --------------------------------------------------------------------------------------------- source schema

#: The permitted public raw members served by the observation grain (TP64 section 3), their record names and the JSON
#: kinds each may carry (absent is recorded explicitly, never confused with null). Every other raw member (city, state,
#: country, height, weight, home location) is bound only through the whole-row hash and never copied.
SERVED_FIELDS = ("id", "athleteId", "name", "recruitType", "year", "position", "school", "committedTo", "rating",
                 "ranking", "stars")
FIELD_NAMES = {"id": "source_recruit_id", "athleteId": "source_athlete_id", "name": "name",
               "recruitType": "recruit_type", "year": "cohort_year", "position": "position", "school": "school",
               "committedTo": "committed_to", "rating": "rating", "ranking": "ranking", "stars": "stars"}
RAW_KINDS = {"id": ("string",), "athleteId": ("string", "null", "absent"),
             "name": ("string", "null", "absent"), "recruitType": ("string", "null", "absent"),
             "year": ("integer", "null", "absent"), "position": ("string", "null", "absent"),
             "school": ("string", "null", "absent"), "committedTo": ("string", "null", "absent"),
             "rating": ("integer", "float", "null", "absent"), "ranking": ("integer", "null", "absent"),
             "stars": ("integer", "null", "absent")}
SOURCE_SCHEMA = {
    "row": "every element of a captured recruiting array is a JSON object",
    "kinds": RAW_KINDS,
    "id": "required ASCII decimal string of 1-12 digits (opaque: never integer-normalized)",
    "athleteId": "absent, null or an ASCII decimal string of 1-12 digits with an optional leading minus (opaque: a "
                 "signed negative spelling is a valid provider identifier, never invalidated or normalized)",
    "numbers": "a boolean is never an integer; a float must be finite; integers stay integers and floats stay floats "
               "(an integer 1 and a float 1.0 are different source values)",
    "text": "served strings are preserved exactly (Unicode, format, combining and non-BMP text included); a lone "
            "surrogate is not Unicode text and refuses the source",
    "uniqueness": "every source recruit ID and every nonnull source athlete ID is unique within the retained source "
                  "population",
    "decoding": "JSON with NaN, Infinity, a float beyond binary64 range or an integer beyond the decoder's digit limit is "
                "malformed source data (refused, never a null)",
}


def json_kind(value: Any) -> str:
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if type(value) is int:
        return "integer"
    if type(value) is float:
        return "float"
    if type(value) is str:
        return "string"
    if type(value) is list:
        return "array"
    if type(value) is dict:
        return "object"
    return type(value).__name__


def observation_key(capture_id: str, ordinal: int, recruit_id: str) -> str:
    return f"{SOURCE_ID}|{capture_id}|{ordinal}|{recruit_id}"


def identity_key_for(athlete_id: str | None, recruit_id: str) -> tuple[str, str, str]:
    """(namespace, existing registry identity key, source-mapping entity key) of one observation: the provider athlete
    namespace when an athlete ID is present, otherwise the recruit-only namespace (never a fallback between them)."""
    if athlete_id is not None:
        return "SOURCE_ATHLETE_ID", f"PLAYER|{SOURCE_ID}|{athlete_id}", athlete_id
    return "SOURCE_RECRUIT_ID_ONLY", f"PLAYER|{SOURCE_ID}|RECRUIT|{recruit_id}", f"RECRUIT:{recruit_id}"


# --------------------------------------------------------------------------------------------- registry witnesses

#: BAT-388 people registry (canonical_people_registry.csv) columns and identity constants (accepted
#: aggie_analytics.entities.people_registry; the legacy builder is lineage only, never authority).
PEOPLE_COLUMNS = (
    "schema_version", "dataset_version", "record_type", "person_type", "record_id", "canonical_id",
    "candidate_canonical_id", "identity_key", "assignment_slot", "source_system_id", "source_entity_key",
    "mapping_method", "resolution_state", "display_name", "display_name_normalized", "first_name", "last_name",
    "suffix", "team_canonical_id", "team_label", "season", "effective_from", "effective_to_exclusive", "role",
    "position", "class_year", "jersey", "height", "weight", "hometown", "origin_team_canonical_id",
    "origin_team_label", "destination_team_canonical_id", "destination_team_label", "transfer_date",
    "recruiting_rating", "recruiting_ranking", "recruiting_stars", "recruiting_school", "recruiting_type",
    "source_capture_ids", "source_payload_sha256s", "quality_state", "eligibility", "provenance_sha256",
    "record_sha256", "notes")
#: BAT-387 core registry (canonical_core_registry.csv) columns.
CORE_COLUMNS = (
    "schema_version", "dataset_version", "record_type", "entity_type", "record_id", "canonical_id",
    "candidate_canonical_id", "identity_key", "assignment_slot", "source_system_id", "source_entity_key",
    "mapping_method", "resolution_state", "relationship_type", "parent_canonical_id", "alias", "alias_normalized",
    "effective_from", "effective_to_exclusive", "season", "season_type", "week", "start_time_utc", "home_team_id",
    "away_team_id", "venue_id", "neutral_site", "game_status", "completed", "source_snapshot_ids",
    "source_payload_sha256s", "quality_state", "eligibility", "provenance_sha256", "record_sha256", "notes")
PEOPLE_NAMESPACE = "0b9087ea-43c1-5f46-a133-63cc34d403c4"
PEOPLE_OBSERVATION_NAMESPACE = "e2c44387-e588-579b-86b3-eeb22436d1d0"
CORE_NAMESPACE = "a4cfb063-a2ab-5b3d-8a9b-39af49c66e36"
CORE_RECORD_NAMESPACE = "bb6c5227-80dd-54f4-b392-a69a23aaab68"
PEOPLE_SLOT_RE = re.compile(r"people-v1:player:[0-9]{8}\Z")
TEAM_SLOT_RE = re.compile(r"core-v1:team:[0-9]{8}\Z")
ACCEPTED = "AUTO_ACCEPTED_VERIFIED"
PERSON_MAPPING_METHOD = "OPAQUE_APPEND_ONLY_ASSIGNMENT"
SOURCE_MAPPING_METHODS = ("DIRECT_SOURCE_PERSON_ID", "RECRUITING_SOURCE_ID")
ALIAS_MAPPING_METHOD = "VERIFIED_SOURCE_ID_LINKED_ALIAS"
TEAM_MAPPING_METHOD = "INTERNAL_ASSIGNMENT_LEDGER_FROM_VERIFIED_SOURCE_IDENTITY"
HASHES_VERIFIED = "RECORD_HASHES_VERIFIED"
HASH_MISMATCH = "RECORD_HASH_MISMATCH"
IDENTITY_RULES = {
    "observation_key": "SRC-002|<capture_id>|<zero-based original raw-array ordinal>|<source recruit id>",
    "namespaces": {"SOURCE_ATHLETE_ID": "PLAYER|SRC-002|<athleteId> with source-mapping entity key <athleteId>",
                   "SOURCE_RECRUIT_ID_ONLY": "PLAYER|SRC-002|RECRUIT|<recruitId> with source-mapping entity key "
                                             "RECRUIT:<recruitId>"},
    "no_fallback": "an observation with an athlete ID is never matched through its recruit-only key, nor the reverse; "
                   "no name, rating, team, position or mutable state ever defines or merges an identity",
    "person": "exactly one PERSON row (person_type player) of the existing registry carries the identity key; its "
              "record_id is its canonical_id; its assignment slot is people-v1:player:<8 digits>; canonical_id = "
              "player_ + uuid5(" + PEOPLE_NAMESPACE + ", slot).hex; mapping OPAQUE_APPEND_ONLY_ASSIGNMENT, "
              "resolution AUTO_ACCEPTED_VERIFIED; its provenance and record hashes reproduce; no other PERSON row "
              "carries its slot or canonical_id",
    "source_mapping": "exactly one SOURCE_MAPPING row with source_system_id SRC-002 and the entity key; record_id = "
                      "map_ + uuid5(" + PEOPLE_OBSERVATION_NAMESPACE + ", 'SRC-002|<entity key>|<canonical_id>').hex; "
                      "its canonical_id, identity key and slot equal the person's; method one of "
                      "DIRECT_SOURCE_PERSON_ID, RECRUITING_SOURCE_ID; resolution AUTO_ACCEPTED_VERIFIED; hashes "
                      "reproduce",
    "people_hashes": "provenance_sha256 = sha256(json.dumps(every column but the two hashes, sort_keys, separators "
                     "',' ':', ASCII escaping)); record_sha256 = the same over every column but record_sha256",
    "legacy_observation": "the existing RECRUITING_OBSERVATION row obs_ + uuid5(" + PEOPLE_OBSERVATION_NAMESPACE +
                          ", 'recruit|<capture_id>|<recruitId>').hex is a lineage witness only; its ASCII-normalized "
                          "team join is reported, never adopted",
    "unsupported": "any failed person condition keeps the keyed observation retrievable as UNSUPPORTED_SOURCE_PERSON "
                   "with every reason; no new identity is minted and no registry row is repaired",
}
PROGRAM_RULES = {
    "match": "the raw committedTo string equals a core registry TEAM_ALIAS row's alias column exactly (full string, "
             "no case folding, ASCII stripping, whitespace normalization, substring or fuzzy rule)",
    "witnesses": "every exact-label team alias row is a witness with its own source system, effective interval, "
                 "original label, record id and hashes; record_id = obs_ + uuid5(" + CORE_RECORD_NAMESPACE +
                 ", 'team-alias|<canonical>|<source>|<alias>|<alias_normalized>|<start>|<end>').hex; provenance = "
                 "sha256('|'.join(source_system_id, source_entity_key, source_snapshot_ids, source_payload_sha256s, "
                 "mapping_method, resolution_state)); record = sha256(US-joined every column but record_sha256)",
    "source_backed": "witness integrity verified, mapping VERIFIED_SOURCE_ID_LINKED_ALIAS, resolution "
                     "AUTO_ACCEPTED_VERIFIED and nonempty source system, snapshots and payload hashes",
    "decision": "EXACT_ALIAS_CORRESPONDENCE needs at least one source-backed exact witness, no witness integrity "
                "failure, exactly one distinct canonical team among all exact witnesses and exactly one verified "
                "TEAM entity record of that team (slot core-v1:team:<8 digits>, canonical_id = team_ + uuid5(" +
                CORE_NAMESPACE + ", slot).hex)",
    "states": ["EXACT_ALIAS_CORRESPONDENCE", "SOURCE_PROGRAM_LABEL_NULL", "SOURCE_PROGRAM_LABEL_ABSENT",
               "NO_EXACT_SOURCE_BACKED_ALIAS", "AMBIGUOUS_ALIAS_CANDIDATES", "ALIAS_WITNESS_INTEGRITY_FAILED",
               "TEAM_RECORD_UNSUPPORTED"],
    "meaning": "a correspondence names a program; it never proves commitment, signing, enrollment, membership, a "
               "roster, availability or an effective interval, even where an alias interval and the cohort year "
               "overlap; historical membership stays UNQUALIFIED",
}
PERSON_REASONS = ("NO_PERSON_RECORD", "MULTIPLE_PERSON_RECORDS", "PERSON_RECORD_INTEGRITY_FAILED",
                  "PERSON_RECORD_NOT_ACCEPTED", "PERSON_SLOT_INVALID", "PERSON_ID_DERIVATION_MISMATCH",
                  "PERSON_SLOT_NOT_UNIQUE", "PERSON_ID_NOT_UNIQUE", "NO_SOURCE_MAPPING", "MULTIPLE_SOURCE_MAPPINGS",
                  "SOURCE_MAPPING_INTEGRITY_FAILED", "SOURCE_MAPPING_NOT_ACCEPTED", "SOURCE_MAPPING_CONFLICT")
PERSON_STATES = ("QUALIFIED_EXISTING_SOURCE_PERSON", "UNSUPPORTED_SOURCE_PERSON")
LEGACY_STATES = ("AGREES", "DISAGREES", "ABSENT", "DUPLICATED")
LEGACY_PROGRAM_AGREEMENTS = ("SAME_TEAM", "DIFFERENT_TEAM", "LEGACY_ONLY_NOT_ADOPTED", "QUALIFIED_ONLY",
                             "BOTH_UNBOUND", "NO_LEGACY_WITNESS")
ALIAS_WITNESS_STATES = ("SOURCE_BACKED_VERIFIED", "NOT_SOURCE_BACKED", "INTEGRITY_FAILED")
TEAM_WITNESS_STATES = ("TEAM_RECORD_VERIFIED", "TEAM_RECORD_INVALID")


def _uuid_hex(namespace: str, key: str) -> str:
    return uuid.uuid5(uuid.UUID(namespace), key).hex


def person_id_for_slot(slot: Any) -> str | None:
    return f"player_{_uuid_hex(PEOPLE_NAMESPACE, slot)}" if isinstance(slot, str) and PEOPLE_SLOT_RE.match(slot) \
        else None


def team_id_for_slot(slot: Any) -> str | None:
    return f"team_{_uuid_hex(CORE_NAMESPACE, slot)}" if isinstance(slot, str) and TEAM_SLOT_RE.match(slot) else None


def mapping_record_id(entity_key: str, canonical_id: str) -> str:
    return f"map_{_uuid_hex(PEOPLE_OBSERVATION_NAMESPACE, f'{SOURCE_ID}|{entity_key}|{canonical_id}')}"


def legacy_record_id(capture_id: str, recruit_id: str) -> str:
    return f"obs_{_uuid_hex(PEOPLE_OBSERVATION_NAMESPACE, f'recruit|{capture_id}|{recruit_id}')}"


def people_row_hashes(row: dict[str, str]) -> tuple[str, str]:
    provenance = {k: row[k] for k in PEOPLE_COLUMNS if k not in ("provenance_sha256", "record_sha256")}
    record = {k: row[k] for k in PEOPLE_COLUMNS if k != "record_sha256"}
    return (sha256_bytes(json.dumps(provenance, sort_keys=True, separators=(",", ":")).encode("utf-8")),
            sha256_bytes(json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")))


def people_row_integrity(row: dict[str, str]) -> str:
    provenance, record = people_row_hashes(row)
    return HASHES_VERIFIED if (provenance, record) == (row["provenance_sha256"], row["record_sha256"]) else HASH_MISMATCH


def core_row_hashes(row: dict[str, str]) -> tuple[str, str]:
    evidence = "|".join([row["source_system_id"], row["source_entity_key"], row["source_snapshot_ids"],
                         row["source_payload_sha256s"], row["mapping_method"], row["resolution_state"]])
    payload = "\x1f".join(row[c] for c in CORE_COLUMNS if c != "record_sha256")
    return sha256_bytes(evidence.encode("utf-8")), sha256_bytes(payload.encode("utf-8"))


def _interval_year(text: str) -> tuple[bool, int | None]:
    if text == "":
        return True, None
    match = YEAR_START_RE.match(text)
    return (True, int(match.group(1))) if match else (False, None)


def alias_record_id(row: dict[str, str]) -> str | None:
    ok_from, start = _interval_year(row["effective_from"])
    ok_to, end = _interval_year(row["effective_to_exclusive"])
    if not (ok_from and ok_to):
        return None
    key = (f"team-alias|{row['canonical_id']}|{row['source_system_id']}|{row['alias']}|{row['alias_normalized']}|"
           f"{start}|{end}")
    return f"obs_{_uuid_hex(CORE_RECORD_NAMESPACE, key)}"


def alias_witness_state(row: dict[str, str]) -> str:
    provenance, record = core_row_hashes(row)
    intact = (row["record_type"] == "ALIAS" and row["entity_type"] == "team" and row["relationship_type"] == "TEAM_ALIAS"
              and bool(TEAM_ID_RE.match(row["canonical_id"])) and row["record_id"] == alias_record_id(row)
              and (provenance, record) == (row["provenance_sha256"], row["record_sha256"]))
    if not intact:
        return "INTEGRITY_FAILED"
    backed = (row["mapping_method"] == ALIAS_MAPPING_METHOD and row["resolution_state"] == ACCEPTED and
              all(row[k] for k in ("source_system_id", "source_snapshot_ids", "source_payload_sha256s")))
    return "SOURCE_BACKED_VERIFIED" if backed else "NOT_SOURCE_BACKED"


def team_witness_state(row: dict[str, str]) -> str:
    provenance, record = core_row_hashes(row)
    ok = (row["record_type"] == "ENTITY" and row["entity_type"] == "team" and row["record_id"] == row["canonical_id"]
          and team_id_for_slot(row["assignment_slot"]) == row["canonical_id"] and row["resolution_state"] == ACCEPTED
          and row["mapping_method"] == TEAM_MAPPING_METHOD
          and (provenance, record) == (row["provenance_sha256"], row["record_sha256"]))
    return "TEAM_RECORD_VERIFIED" if ok else "TEAM_RECORD_INVALID"


def person_witness(row: dict[str, str], registry_row: int, slot_count: int, canonical_count: int) -> dict[str, Any]:
    return {"registry_row": registry_row, "record_id": row["record_id"], "record_type": row["record_type"],
            "person_type": row["person_type"], "canonical_id": row["canonical_id"], "identity_key": row["identity_key"],
            "assignment_slot": row["assignment_slot"], "mapping_method": row["mapping_method"],
            "resolution_state": row["resolution_state"], "provenance_sha256": row["provenance_sha256"],
            "record_sha256": row["record_sha256"], "integrity_state": people_row_integrity(row),
            "slot_person_records": slot_count, "canonical_person_records": canonical_count}


def mapping_witness(row: dict[str, str], registry_row: int) -> dict[str, Any]:
    return {"registry_row": registry_row, "record_id": row["record_id"], "record_type": row["record_type"],
            "person_type": row["person_type"], "canonical_id": row["canonical_id"], "identity_key": row["identity_key"],
            "assignment_slot": row["assignment_slot"], "source_system_id": row["source_system_id"],
            "source_entity_key": row["source_entity_key"], "mapping_method": row["mapping_method"],
            "resolution_state": row["resolution_state"], "provenance_sha256": row["provenance_sha256"],
            "record_sha256": row["record_sha256"], "integrity_state": people_row_integrity(row)}


def legacy_witness(row: dict[str, str], registry_row: int) -> dict[str, Any]:
    return {"registry_row": registry_row, "record_id": row["record_id"], "record_type": row["record_type"],
            "canonical_id": row["canonical_id"], "identity_key": row["identity_key"],
            "assignment_slot": row["assignment_slot"], "source_system_id": row["source_system_id"],
            "source_entity_key": row["source_entity_key"], "source_capture_ids": row["source_capture_ids"],
            "source_payload_sha256s": row["source_payload_sha256s"], "team_canonical_id": row["team_canonical_id"],
            "team_label": row["team_label"], "resolution_state": row["resolution_state"],
            "record_sha256": row["record_sha256"], "integrity_state": people_row_integrity(row)}


def core_source_key(registry_row: int, record_id: str) -> str:
    return f"CORE|{registry_row}|{record_id}"


# --------------------------------------------------------------------------------------------- decisions

def person_decision(identity_key: str, entity_key: str, persons: list[dict[str, Any]],
                    mappings: list[dict[str, Any]]) -> tuple[str, list[str], str | None, str | None]:
    """(state, reasons, canonical player id, slot) from the person and source-mapping witnesses alone."""
    reasons: set[str] = set()
    person = None
    if not persons:
        reasons.add("NO_PERSON_RECORD")
    elif len(persons) > 1:
        reasons.add("MULTIPLE_PERSON_RECORDS")
    else:
        person = persons[0]
        if person["integrity_state"] != HASHES_VERIFIED:
            reasons.add("PERSON_RECORD_INTEGRITY_FAILED")
        if (person["record_type"], person["person_type"], person["identity_key"], person["mapping_method"],
                person["resolution_state"]) != ("PERSON", "player", identity_key, PERSON_MAPPING_METHOD, ACCEPTED) or \
                person["record_id"] != person["canonical_id"]:
            reasons.add("PERSON_RECORD_NOT_ACCEPTED")
        derived = person_id_for_slot(person["assignment_slot"])
        if derived is None:
            reasons.add("PERSON_SLOT_INVALID")
        elif derived != person["canonical_id"]:
            reasons.add("PERSON_ID_DERIVATION_MISMATCH")
        if person["slot_person_records"] != 1:
            reasons.add("PERSON_SLOT_NOT_UNIQUE")
        if person["canonical_person_records"] != 1:
            reasons.add("PERSON_ID_NOT_UNIQUE")
    if not mappings:
        reasons.add("NO_SOURCE_MAPPING")
    elif len(mappings) > 1:
        reasons.add("MULTIPLE_SOURCE_MAPPINGS")
    else:
        mapping = mappings[0]
        if mapping["integrity_state"] != HASHES_VERIFIED:
            reasons.add("SOURCE_MAPPING_INTEGRITY_FAILED")
        if (mapping["record_type"], mapping["person_type"], mapping["source_system_id"], mapping["source_entity_key"],
                mapping["resolution_state"]) != ("SOURCE_MAPPING", "player", SOURCE_ID, entity_key, ACCEPTED) or \
                mapping["mapping_method"] not in SOURCE_MAPPING_METHODS or \
                mapping["record_id"] != mapping_record_id(entity_key, mapping["canonical_id"]):
            reasons.add("SOURCE_MAPPING_NOT_ACCEPTED")
        if person is not None and (mapping["canonical_id"], mapping["identity_key"], mapping["assignment_slot"]) != \
                (person["canonical_id"], identity_key, person["assignment_slot"]):
            reasons.add("SOURCE_MAPPING_CONFLICT")
    if reasons:
        return "UNSUPPORTED_SOURCE_PERSON", sorted(reasons), None, None
    return "QUALIFIED_EXISTING_SOURCE_PERSON", [], person["canonical_id"], person["assignment_slot"]


def alias_view(source_key: str, registry_row: int, row: dict[str, str]) -> dict[str, Any]:
    return {"source_key": source_key, "registry_row": registry_row, "record_id": row["record_id"],
            "canonical_id": row["canonical_id"], "source_system_id": row["source_system_id"], "alias": row["alias"],
            "effective_from": row["effective_from"], "effective_to_exclusive": row["effective_to_exclusive"],
            "mapping_method": row["mapping_method"], "resolution_state": row["resolution_state"],
            "record_sha256": row["record_sha256"], "witness_state": alias_witness_state(row)}


def team_view(source_key: str, registry_row: int, row: dict[str, str]) -> dict[str, Any]:
    return {"source_key": source_key, "registry_row": registry_row, "record_id": row["record_id"],
            "canonical_id": row["canonical_id"], "assignment_slot": row["assignment_slot"],
            "identity_key": row["identity_key"], "record_sha256": row["record_sha256"],
            "witness_state": team_witness_state(row)}


def program_decision(label_state: str, aliases: list[dict[str, Any]], teams: list[dict[str, Any]]
                     ) -> tuple[str, str | None, list[str]]:
    """(state, canonical team id, candidate team ids) from the exact-label alias views and the candidate's team views."""
    if label_state == "NULL":
        return "SOURCE_PROGRAM_LABEL_NULL", None, []
    if label_state == "ABSENT":
        return "SOURCE_PROGRAM_LABEL_ABSENT", None, []
    candidates = sorted({a["canonical_id"] for a in aliases})
    states = {a["witness_state"] for a in aliases}
    if not aliases:
        return "NO_EXACT_SOURCE_BACKED_ALIAS", None, candidates
    if "INTEGRITY_FAILED" in states:
        return "ALIAS_WITNESS_INTEGRITY_FAILED", None, candidates
    if len(candidates) > 1:
        return "AMBIGUOUS_ALIAS_CANDIDATES", None, candidates
    if "SOURCE_BACKED_VERIFIED" not in states:
        return "NO_EXACT_SOURCE_BACKED_ALIAS", None, candidates
    if len(teams) != 1 or teams[0]["witness_state"] != "TEAM_RECORD_VERIFIED" or \
            teams[0]["canonical_id"] != candidates[0]:
        return "TEAM_RECORD_UNSUPPORTED", None, candidates
    return "EXACT_ALIAS_CORRESPONDENCE", candidates[0], candidates


def legacy_decision(witnesses: list[dict[str, Any]], observation: dict[str, Any], identity_key: str,
                    canonical: str | None, slot: str | None, team: str | None) -> tuple[str, str]:
    """(legacy observation state, legacy program agreement): the existing projection as a lineage witness only."""
    if not witnesses:
        return "ABSENT", "NO_LEGACY_WITNESS"
    if len(witnesses) > 1:
        return "DUPLICATED", "NO_LEGACY_WITNESS"
    w = witnesses[0]
    agrees = (w["integrity_state"] == HASHES_VERIFIED and w["record_type"] == "RECRUITING_OBSERVATION" and
              w["record_id"] == legacy_record_id(observation["capture_id"], observation["source_recruit_id"]) and
              (w["identity_key"], w["canonical_id"], w["assignment_slot"], w["source_system_id"],
               w["source_entity_key"], w["source_capture_ids"], w["source_payload_sha256s"]) ==
              (identity_key, canonical or "", slot or "", SOURCE_ID, observation["source_recruit_id"],
               observation["capture_id"], observation["capture_sha256"]))
    legacy_team = w["team_canonical_id"] or None
    if legacy_team is None and team is None:
        agreement = "BOTH_UNBOUND"
    elif legacy_team == team:
        agreement = "SAME_TEAM"
    elif team is None:
        agreement = "LEGACY_ONLY_NOT_ADOPTED"
    elif legacy_team is None:
        agreement = "QUALIFIED_ONLY"
    else:
        agreement = "DIFFERENT_TEAM"
    return ("AGREES" if agrees else "DISAGREES"), agreement


VALUE_RULES = {
    "rating": "the source value as served (integer or finite float kept as its kind); WITHIN_DECLARED_UNIT_INTERVAL "
              "when 0 <= rating <= 1, otherwise OUTSIDE_DECLARED_UNIT_INTERVAL; null and absent stay null",
    "ranking": "POSITIVE_INTEGER when ranking >= 1, otherwise NONPOSITIVE_INTEGER; null and absent stay null",
    "stars": "INTEGER_ZERO_TO_FIVE when 0 <= stars <= 5, otherwise OUTSIDE_ZERO_TO_FIVE; null and absent stay null",
    "triplet": "ALL_PRESENT, JOINT_NULL (rating, ranking and stars all null or absent) or MIXED",
    "scale": "SOURCE_AS_SERVED_SCALE_UNVERIFIED: rating system, version, publication and update times null; upstream "
             "independence of a shared provider tag NOT_ESTABLISHED; no imputation, rank-to-rating or star inference, "
             "cross-source normalization, composite class score or talent prior",
    "cohort_year": "EQUALS_REQUEST_SEASON, DIFFERS_FROM_REQUEST_SEASON, NULL or ABSENT; the cohort year is never a date",
}
TIME_FIELDS = ("historical_known_at", "commitment_time", "signing_time", "enrollment_time", "decommitment_time",
               "portal_event_time", "rating_publication_time", "rating_update_time", "effective_from", "effective_to")
TIME_RULES = {
    "clocks": "capture_known_at_utc and retrieved_at_utc are the capture receipt's 2026-08-10 retrieval clocks and "
              "provider_http_date its response Date header; they are never historical known-at or publication times",
    "historical": "every historical known-at, rating publication/update, commitment, signing, enrollment, "
                  "decommitment, portal-event and effective time is null (the source carries none); pit_eligible is "
                  "false for every observation; the cohort year never becomes January 1 or a signing day",
    "build_and_freeze": "the contract freeze time is the contract's frozen_at_utc; the build clock is the run "
                        "manifest's provenance only (never identity-bound)",
}


def value_states(observation: dict[str, Any]) -> dict[str, Any]:
    kinds = observation["source_field_kinds"]

    def state(name: str) -> str:
        kind = kinds[name]
        return "SOURCE_VALUE" if kind in ("integer", "float") else ("SOURCE_NULL" if kind == "null" else
                                                                   "SOURCE_ABSENT")
    rating, ranking, stars = observation["rating"], observation["ranking"], observation["stars"]
    present = sum(1 for name in ("rating", "ranking", "stars") if kinds[name] in ("integer", "float"))
    year_kind = kinds["year"]
    if year_kind == "integer":
        year_state = "EQUALS_REQUEST_SEASON" if observation["cohort_year"] == observation["request_season"] else \
            "DIFFERS_FROM_REQUEST_SEASON"
    else:
        year_state = "NULL" if year_kind == "null" else "ABSENT"
    return {"rating_state": state("rating"),
            "rating_domain_state": None if rating is None else
            ("WITHIN_DECLARED_UNIT_INTERVAL" if 0 <= rating <= 1 else "OUTSIDE_DECLARED_UNIT_INTERVAL"),
            "ranking_state": state("ranking"),
            "ranking_domain_state": None if ranking is None else
            ("POSITIVE_INTEGER" if ranking >= 1 else "NONPOSITIVE_INTEGER"),
            "stars_state": state("stars"),
            "stars_domain_state": None if stars is None else
            ("INTEGER_ZERO_TO_FIVE" if 0 <= stars <= 5 else "OUTSIDE_ZERO_TO_FIVE"),
            "rating_triplet_state": "ALL_PRESENT" if present == 3 else ("JOINT_NULL" if present == 0 else "MIXED"),
            "rating_scale": "SOURCE_AS_SERVED_SCALE_UNVERIFIED", "rating_system_version": None,
            "rating_upstream_independence": "NOT_ESTABLISHED", "cohort_year_state": year_state}


PERSON_MEANING = "SOURCE_PERSON_CORRESPONDENCE_ONLY_NOT_ROSTER_ENROLLMENT_AVAILABILITY_OR_PRODUCTION"
PROGRAM_MEANING = "NAMED_PROGRAM_REFERENCE_ONLY_NOT_MEMBERSHIP_COMMITMENT_SIGNING_OR_ENROLLMENT"
TIME_STATE = "HISTORICAL_EVENT_PUBLICATION_AND_EFFECTIVE_TIMES_UNKNOWN"


def qualification_record(observation: dict[str, Any], observation_line: str, capture: dict[str, Any],
                         persons: list[dict[str, Any]], mappings: list[dict[str, Any]],
                         legacies: list[dict[str, Any]], aliases: list[dict[str, Any]],
                         teams: list[dict[str, Any]]) -> dict[str, Any]:
    """The one qualification of an observation from its observation record, its capture's pinned clocks and its
    witnesses (sorted by registry row); used identically by the builder and the reader's re-derivation."""
    namespace, identity_key, entity_key = identity_key_for(observation["source_athlete_id"],
                                                           observation["source_recruit_id"])
    persons = sorted(persons, key=lambda w: w["registry_row"])
    mappings = sorted(mappings, key=lambda w: w["registry_row"])
    legacies = sorted(legacies, key=lambda w: w["registry_row"])
    aliases = sorted(aliases, key=lambda w: w["registry_row"])
    teams = sorted(teams, key=lambda w: w["registry_row"])
    person_state, reasons, canonical, slot = person_decision(identity_key, entity_key, persons, mappings)
    kinds = observation["source_field_kinds"]
    label_state = {"string": "PRESENT", "null": "NULL", "absent": "ABSENT"}[kinds["committedTo"]]
    program_state, team, candidates = program_decision(label_state, aliases, teams)
    legacy_state, agreement = legacy_decision(legacies, observation, identity_key, canonical, slot, team)
    record = {
        "record_type": "RECRUITING_QUALIFICATION", "qualification_key": observation["observation_key"],
        "observation_key": observation["observation_key"],
        "observation_record_sha256": sha256_bytes(observation_line.encode("utf-8")),
        "request_season": observation["request_season"], "capture_id": observation["capture_id"],
        "raw_row_ordinal": observation["raw_row_ordinal"], "source_recruit_id": observation["source_recruit_id"],
        "source_athlete_id": observation["source_athlete_id"], "source_namespace": namespace,
        "identity_key": identity_key, "source_mapping_entity_key": entity_key, "person_state": person_state,
        "person_reasons": reasons, "canonical_player_id": canonical, "assignment_slot": slot,
        "person_witnesses": persons, "mapping_witnesses": mappings, "person_meaning": PERSON_MEANING,
        "legacy_observation_witnesses": legacies, "legacy_observation_state": legacy_state,
        "legacy_program_agreement": agreement, "program_label": observation["committed_to"],
        "program_label_state": label_state, "program_state": program_state, "canonical_team_id": team,
        "candidate_team_ids": candidates, "alias_witnesses": aliases, "team_witnesses": teams,
        "program_meaning": PROGRAM_MEANING, "historical_membership_state": "UNQUALIFIED",
        **value_states(observation),
        "capture_known_at_utc": capture["capture_known_at_utc"], "retrieved_at_utc": capture["retrieved_at_utc"],
        "provider_http_date": capture["provider_http_date"], **{name: None for name in TIME_FIELDS},
        "pit_eligible": False, "time_state": TIME_STATE, **RECORD_LABELS}
    return record


# --------------------------------------------------------------------------------------------- record types

_NONE = type(None)
PERSON_WITNESS = {"registry_row": "i", "record_id": "s", "record_type": "s", "person_type": "s", "canonical_id": "s",
                  "identity_key": "s", "assignment_slot": "s", "mapping_method": "s", "resolution_state": "s",
                  "provenance_sha256": "s", "record_sha256": "s", "integrity_state": "s",
                  "slot_person_records": "i", "canonical_person_records": "i"}
MAPPING_WITNESS = {"registry_row": "i", "record_id": "s", "record_type": "s", "person_type": "s", "canonical_id": "s",
                   "identity_key": "s", "assignment_slot": "s", "source_system_id": "s", "source_entity_key": "s",
                   "mapping_method": "s", "resolution_state": "s", "provenance_sha256": "s", "record_sha256": "s",
                   "integrity_state": "s"}
LEGACY_WITNESS = {"registry_row": "i", "record_id": "s", "record_type": "s", "canonical_id": "s", "identity_key": "s",
                  "assignment_slot": "s", "source_system_id": "s", "source_entity_key": "s",
                  "source_capture_ids": "s", "source_payload_sha256s": "s", "team_canonical_id": "s",
                  "team_label": "s", "resolution_state": "s", "record_sha256": "s", "integrity_state": "s"}
ALIAS_WITNESS = {"source_key": "s", "registry_row": "i", "record_id": "s", "canonical_id": "s",
                 "source_system_id": "s", "alias": "s", "effective_from": "s", "effective_to_exclusive": "s",
                 "mapping_method": "s", "resolution_state": "s", "record_sha256": "s", "witness_state": "s"}
TEAM_WITNESS = {"source_key": "s", "registry_row": "i", "record_id": "s", "canonical_id": "s",
                "assignment_slot": "s", "identity_key": "s", "record_sha256": "s", "witness_state": "s"}
SUBSPECS = {"person": PERSON_WITNESS, "mapping": MAPPING_WITNESS, "legacy": LEGACY_WITNESS, "alias": ALIAS_WITNESS,
            "team": TEAM_WITNESS}
_LABEL_TYPES = {k: "s" for k in RECORD_LABEL_KEYS}
FIELD_TYPES: dict[str, dict[str, str]] = {
    "observations": {
        "record_type": "s", "observation_key": "s", "source_id": "s", "dataset": "s", "capture_id": "s",
        "request_season": "i", "raw_row_ordinal": "i", "raw_row_sha256": "s", "raw_member_names": "ls",
        "absent_served_fields": "ls", "source_field_kinds": "kinds", "source_recruit_id": "s",
        "source_athlete_id": "s?", "name": "s?", "recruit_type": "s?", "cohort_year": "i?", "position": "s?",
        "school": "s?", "committed_to": "s?", "rating": "num?", "ranking": "i?", "stars": "i?",
        "capture_sha256": "s", "receipt_sha256": "s", **_LABEL_TYPES},
    "qualifications": {
        "record_type": "s", "qualification_key": "s", "observation_key": "s", "observation_record_sha256": "s",
        "request_season": "i", "capture_id": "s", "raw_row_ordinal": "i", "source_recruit_id": "s",
        "source_athlete_id": "s?", "source_namespace": "s", "identity_key": "s", "source_mapping_entity_key": "s",
        "person_state": "s", "person_reasons": "ls", "canonical_player_id": "s?", "assignment_slot": "s?",
        "person_witnesses": "l@person", "mapping_witnesses": "l@mapping", "person_meaning": "s",
        "legacy_observation_witnesses": "l@legacy", "legacy_observation_state": "s",
        "legacy_program_agreement": "s", "program_label": "s?", "program_label_state": "s", "program_state": "s",
        "canonical_team_id": "s?", "candidate_team_ids": "ls", "alias_witnesses": "l@alias",
        "team_witnesses": "l@team", "program_meaning": "s", "historical_membership_state": "s",
        "rating_state": "s", "rating_domain_state": "s?", "ranking_state": "s", "ranking_domain_state": "s?",
        "stars_state": "s", "stars_domain_state": "s?", "rating_triplet_state": "s", "rating_scale": "s",
        "rating_system_version": "s?", "rating_upstream_independence": "s", "cohort_year_state": "s",
        "capture_known_at_utc": "s", "retrieved_at_utc": "s", "provider_http_date": "s",
        **{name: "s?" for name in TIME_FIELDS}, "pit_eligible": "b", "time_state": "s", **_LABEL_TYPES},
    "partitions": {
        "record_type": "s", "partition_key": "s", "source_id": "s", "dataset": "s", "parameters": "j",
        "season": "i?", "min_year": "i?", "max_year": "i?", "request_state": "s", "missing_reason": "s?",
        "capture_id": "s?", "endpoint_id": "s?", "source_uri": "s?", "http_status": "i?", "result": "s?",
        "capture_known_at_utc": "s?", "retrieved_at_utc": "s?", "provider_http_date": "s?",
        "response_sha256": "s?", "response_bytes": "i?", "receipt_sha256": "s?", "row_count": "i?",
        "payload_state": "s?", "release_observations": "i?", "release_scope": "s", "coverage_meaning": "s",
        **_LABEL_TYPES},
    "sources": {
        "record_type": "s", "source_key": "s", "witness_kind": "s", "role": "s", "role_meaning": "s",
        "locator_root": "s?", "relative_path": "s?", "sha256": "s?", "bytes": "i?", "capture_id": "s?",
        "dataset": "s?", "parameters": "j", "capture_known_at_utc": "s?", "retrieved_at_utc": "s?",
        "provider_http_date": "s?", "row_count": "i?", "rights_decision": "j", "frozen_at_utc": "s?",
        "registry": "s?", "registry_sha256": "s?", "registry_row": "i?", "row": "j", "integrity_state": "s?",
        "witness_state": "s?", **_LABEL_TYPES},
    "summary": {
        "record_type": "s", "summary_key": "s", "scope_kind": "s", "scope_id": "s", "observations": "i",
        "distinct_source_recruit_ids": "i", "athlete_id_observations": "i", "recruit_only_observations": "i",
        "negative_athlete_id_observations": "i", "distinct_canonical_players": "i", "distinct_canonical_teams": "i",
        "person_states": "j", "person_reasons": "j", "program_label_states": "j", "program_states": "j",
        "rating_kinds": "j", "ranking_kinds": "j", "stars_kinds": "j", "rating_triplet_states": "j",
        "rating_domain_states": "j", "ranking_domain_states": "j", "stars_domain_states": "j",
        "cohort_year_states": "j", "recruit_types": "j", "positions": "j", "legacy_observation_states": "j",
        "legacy_program_agreements": "j", "historical_times_known": "i", "pit_eligible_observations": "i",
        "reading": "s", **_LABEL_TYPES},
    "census": {"record_type": "s", "census_key": "s", "population": "j", **_LABEL_TYPES},
}
RECORD_TYPES = {"observations": "RECRUITING_OBSERVATION", "qualifications": "RECRUITING_QUALIFICATION",
                "partitions": "RECRUITING_PARTITION", "sources": "RECRUITING_SOURCE_WITNESS",
                "summary": "RECRUITING_SUMMARY", "census": "RECRUITING_CENSUS"}
RECORD_TABLES = ("observations", "qualifications", "partitions", "sources", "summary", "census")
SEASONAL_TABLES = ("observations", "qualifications")
KEY_FIELDS = {"observations": "observation_key", "qualifications": "qualification_key", "partitions": "partition_key",
              "sources": "source_key", "summary": "summary_key", "census": "census_key"}
TABLE_LABELS = {"observations": "OBSERVATION", "qualifications": "QUALIFICATION", "partitions": "PARTITION",
                "sources": "SOURCE", "summary": "SUMMARY", "census": "CENSUS"}
ORDERING = {"observations": "request season, then the zero-based original raw-array ordinal",
            "qualifications": "the order of their observations",
            "partitions": "dataset (recruiting_players, transfer_portal, coaches, coach_seasons), then the parameters "
                          "(year, or minYear then maxYear)",
            "sources": "the pinned file witnesses in contract order, then the referenced core registry rows by "
                       "registry row",
            "summary": "SELECTION|ALL, then REQUEST_SEASON|<season> ascending (only seasons of the selection)",
            "census": "one record"}
LAYOUT = {
    "grains": {"observations": "one record per retained recruiting observation (28,093 expected), keyed "
                               "SRC-002|<capture>|<ordinal>|<recruit id>",
               "qualifications": "one record per observation, same key",
               "partitions": "one record per requested dataset/parameter cell (34), keyed <dataset>|<k=v,...>",
               "sources": "FILE|<input name> per pinned input, CORE|<registry row>|<record id> per referenced core "
                          "registry row",
               "summary": "SELECTION|ALL and REQUEST_SEASON|<season>",
               "census": "census"},
    "ordering": ORDERING,
    "serialization": "canonical JSON lines (sorted keys, separators ',' ':', UTF-8, no ASCII escaping, integers and "
                     "floats kept as their JSON kinds); one zlib level-9 block per seasonal table and request season, "
                     "one GLOBAL block each for partitions, sources, summary and census",
    "database": {"ddl": [["table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"],
                         ["table", "blocks", "CREATE TABLE blocks (ord INTEGER PRIMARY KEY, record_table TEXT NOT NULL, "
                                             "segment TEXT NOT NULL, records INTEGER NOT NULL, first_key TEXT, "
                                             "last_key TEXT, lines_sha256 TEXT NOT NULL, block BLOB NOT NULL)"]],
                 "block_layout": [*[[t, str(s)] for t in SEASONAL_TABLES for s in RECRUIT_SEASONS],
                                  ["partitions", "GLOBAL"], ["sources", "GLOBAL"], ["summary", "GLOBAL"],
                                  ["census", "GLOBAL"]],
                 "page_size": 4096, "journal_mode": "OFF", "file": DB_FILE},
    "identity_documents": {
        "content": ["schema", "stage", "population", "contract_id", "contract_sha256", "inputs", "rules_sha256",
                    "payload_schema", "row_counts", "lines_sha256", "blocks"],
        "database": ["schema", "stage", "population", "contract_sha256", "content_identity", "db_schema_version",
                     "outputs", "table_counts"],
        "identity": "SHA-256 of the canonical JSON bytes of the document; compared as canonical bytes, never by Python "
                    "equality (an integral float, a boolean or an extra member differs)",
        "location": "<root>/canonical/national_recruiting_evidence_2010_2017/sha256/<database identity>/"
                    "national_recruiting_evidence.sqlite; manifest at <root>/manifests/"
                    "national_recruiting_evidence_2010_2017/sha256/<database identity>/run_manifest.json with members "
                    "identity, identity_document, content_identity, content_document and provenance; create-only "
                    "(identical rebuild ALREADY_PRESENT_IDENTICAL, differing bytes REFUSED_IMMUTABLE_COLLISION)"},
    "profile": "the first authorized canonical build derives the content and database identities; a separate commit "
               "pins exactly those values here (RECRUITING_PROFILE) and every later build must reproduce them",
    "checkpoint_unit": "a run of consecutive canonical observations (--chunk-size observations): their observation and "
                       "qualification lines; partitions, sources, summary and census follow",
}
FILE_ROLE_MEANINGS = {
    "recruiting_players": "RETAINED_PROVIDER_RECRUITING_ARRAY_PRIMARY_OBSERVATION_AUTHORITY",
    "recruiting_receipt": "RETAINED_CAPTURE_RECEIPT_CLOCK_AND_REQUEST_AUTHORITY",
    "transfer_portal": "RETAINED_EMPTY_PROVIDER_PORTAL_ARRAY_DISTINCT_CAPTURED_CELL",
    "portal_receipt": "RETAINED_CAPTURE_RECEIPT_CLOCK_AND_REQUEST_AUTHORITY",
    "acquisition_manifest": "ORIGINAL_REQUESTED_CELL_UNIVERSE_AND_QUOTA_MISSING_STATUS",
    "people_registry": "EXISTING_PERSON_AND_SOURCE_MAPPING_CLAIMS_REQUALIFIED_NOT_ORACLE",
    "people_manifest": "EXISTING_PEOPLE_REGISTRY_MANIFEST_WITNESS",
    "core_registry": "EXISTING_TEAM_ALIAS_AND_ENTITY_CLAIMS_REQUALIFIED_NOT_ORACLE",
    "core_manifest": "EXISTING_CORE_REGISTRY_MANIFEST_WITNESS",
    "rights_metadata": "SRC_002_PRIVATE_RESEARCH_RIGHTS_DECISION_NONBLOCKING_METADATA",
    "legacy_people_builder": "LEGACY_BUILDER_LINEAGE_ONLY_NOT_SCIENTIFIC_AUTHORITY",
    "contract": "FROZEN_DATA_CONTRACT",
}
CORE_ROLE_MEANINGS = {"CORE_TEAM_ALIAS_ROW": "EXACT_LABEL_TEAM_ALIAS_WITNESS_ROW",
                      "CORE_TEAM_ENTITY_ROW": "REFERENCED_TEAM_ENTITY_WITNESS_ROW"}


def input_names(inputs: dict[str, Any]) -> list[str]:
    """The pinned inputs in contract order: recruiting arrays and receipts, portal arrays and receipts, then the
    single files."""
    order = ("recruiting_players", "recruiting_receipt", "transfer_portal", "portal_receipt")
    names = []
    for group in order:
        names += sorted((n for n in inputs if n.split(":")[0] == group), key=lambda n: int(n.split(":")[1]))
    names += [n for n in ("acquisition_manifest", "people_registry", "people_manifest", "core_registry",
                          "core_manifest", "rights_metadata", "legacy_people_builder") if n in inputs]
    return names


# --------------------------------------------------------------------------------------------- partitions, sources

def cell_key(dataset: str, parameters: dict[str, Any]) -> str:
    return f"{dataset}|" + ",".join(f"{k}={parameters[k]}" for k in sorted(parameters))


def cell_order(dataset: str, parameters: dict[str, Any]) -> tuple[Any, ...]:
    rank = DATASET_ORDER.index(dataset) if dataset in DATASET_ORDER else len(DATASET_ORDER)
    return (rank, dataset, parameters.get("year", parameters.get("minYear", 0)), parameters.get("maxYear", 0),
            cell_key(dataset, parameters))


def partition_records(expected: dict[str, Any], observation_counts: dict[str, int]) -> list[dict[str, Any]]:
    """Every requested cell from the pinned cell and capture universe; a captured cell keeps its own capture id, year,
    parameters and clocks even when its payload bytes equal another cell's."""
    out = []
    for cell in expected["cells"]:
        params = cell["parameters"]
        capture = expected["captures"].get(cell["capture_id"]) if cell["capture_id"] else None
        season = params.get("year") if set(params) == {"year"} else None
        base = {"record_type": RECORD_TYPES["partitions"], "partition_key": cell["cell_key"], "source_id": SOURCE_ID,
                "dataset": cell["dataset"], "parameters": params, "season": season,
                "min_year": params.get("minYear"), "max_year": params.get("maxYear"), **RECORD_LABELS}
        if capture is None:
            base.update(request_state="NOT_CAPTURED", missing_reason=cell["missing_reason"], capture_id=None,
                        endpoint_id=None, source_uri=None, http_status=None, result=None, capture_known_at_utc=None,
                        retrieved_at_utc=None, provider_http_date=None, response_sha256=None, response_bytes=None,
                        receipt_sha256=None, row_count=None, payload_state=None, release_observations=None,
                        release_scope="NOT_CAPTURED_NO_OBSERVATIONS",
                        coverage_meaning="REQUESTED_BUT_NOT_PERFORMED_PROVIDER_QUOTA_UNKNOWN_CONTENT_NOT_EMPTY")
        else:
            served = cell["dataset"] == RECRUIT_DATASET
            base.update(request_state="CAPTURED", missing_reason=None, capture_id=cell["capture_id"],
                        endpoint_id=capture["endpoint_id"], source_uri=capture["source_uri"],
                        http_status=capture["http_status"], result=capture["result"],
                        capture_known_at_utc=capture["capture_known_at_utc"],
                        retrieved_at_utc=capture["retrieved_at_utc"],
                        provider_http_date=capture["provider_http_date"],
                        response_sha256=capture["response_sha256"], response_bytes=capture["response_bytes"],
                        receipt_sha256=capture["receipt_sha256"], row_count=capture["row_count"],
                        payload_state="NONEMPTY_ARRAY" if capture["row_count"] else "EMPTY_ARRAY",
                        release_observations=observation_counts.get(cell["capture_id"], 0) if served else 0,
                        release_scope="RECRUITING_OBSERVATIONS_SERVED" if served else "EMPTY_CAPTURE_NO_OBSERVATIONS"
                        if not capture["row_count"] else "CAPTURED_OUT_OF_RELEASE_SCOPE",
                        coverage_meaning="CAPTURED_REQUEST_CELL_NOT_NATIONAL_COVERAGE")
        out.append(base)
    return out


def file_source_records(anchors: dict[str, Any]) -> list[dict[str, Any]]:
    """Every pinned input as a file witness, plus the frozen contract itself (re-derived from the pinned anchors)."""
    expected = anchors["expected"]
    out = []
    for name in input_names(anchors["inputs"]):
        spec = anchors["inputs"][name]
        group = name.split(":")[0]
        capture = expected["captures"].get(spec.get("capture_id")) if spec.get("capture_id") else None
        out.append({"record_type": RECORD_TYPES["sources"], "source_key": f"FILE|{name}", "witness_kind": "FILE",
                    "role": name, "role_meaning": FILE_ROLE_MEANINGS[group], "locator_root": spec["locator"],
                    "relative_path": spec["relative_path"], "sha256": spec["sha256"], "bytes": spec["bytes"],
                    "capture_id": spec.get("capture_id"), "dataset": None if capture is None else capture["dataset"],
                    "parameters": None if capture is None else capture["parameters"],
                    "capture_known_at_utc": None if capture is None else capture["capture_known_at_utc"],
                    "retrieved_at_utc": None if capture is None else capture["retrieved_at_utc"],
                    "provider_http_date": None if capture is None else capture["provider_http_date"],
                    "row_count": spec.get("rows"), "rights_decision": spec.get("decision"), "frozen_at_utc": None,
                    "registry": None, "registry_sha256": None, "registry_row": None, "row": None,
                    "integrity_state": None, "witness_state": None, **RECORD_LABELS})
    out.append({"record_type": RECORD_TYPES["sources"], "source_key": "FILE|contract", "witness_kind": "FILE",
                "role": "contract", "role_meaning": FILE_ROLE_MEANINGS["contract"], "locator_root": "REPOSITORY",
                "relative_path": CONTRACT_REL, "sha256": anchors["contract_sha256"], "bytes": None, "capture_id": None,
                "dataset": None, "parameters": None, "capture_known_at_utc": None, "retrieved_at_utc": None,
                "provider_http_date": None, "row_count": None, "rights_decision": None,
                "frozen_at_utc": anchors["frozen_at_utc"], "registry": None, "registry_sha256": None,
                "registry_row": None, "row": None, "integrity_state": None, "witness_state": None, **RECORD_LABELS})
    return out


def core_source_record(registry_row: int, row: dict[str, str], kind: str, registry_sha256: str) -> dict[str, Any]:
    provenance, record = core_row_hashes(row)
    integrity = HASHES_VERIFIED if (provenance, record) == (row["provenance_sha256"], row["record_sha256"]) else \
        HASH_MISMATCH
    state = alias_witness_state(row) if kind == "CORE_TEAM_ALIAS_ROW" else team_witness_state(row)
    return {"record_type": RECORD_TYPES["sources"], "source_key": core_source_key(registry_row, row["record_id"]),
            "witness_kind": kind, "role": kind, "role_meaning": CORE_ROLE_MEANINGS[kind], "locator_root": None,
            "relative_path": None, "sha256": None, "bytes": None, "capture_id": None, "dataset": None,
            "parameters": None, "capture_known_at_utc": None, "retrieved_at_utc": None, "provider_http_date": None,
            "row_count": None, "rights_decision": None, "frozen_at_utc": None, "registry": "BAT-387_CORE_REGISTRY",
            "registry_sha256": registry_sha256, "registry_row": registry_row, "row": dict(row),
            "integrity_state": integrity, "witness_state": state, **RECORD_LABELS}


# --------------------------------------------------------------------------------------------- summary, census

def _count(values: Iterable[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        key = "null" if value is None else str(value)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


SUMMARY_READING = ("COUNTS_AND_DISTRIBUTIONS_OF_SELECTED_SOURCE_OBSERVATIONS_ONLY: no mean talent, class rank, fitted "
                   "prior, impact or skill; program and person counts are correspondence counts, not membership or "
                   "roster counts")
SUMMARY_RULES = {
    "rows": "SELECTION|ALL over the selected observations, then one REQUEST_SEASON|<season> row per request season "
            "present in the selection; an empty selection serves no row (never a zero-valued summary)",
    "selection": "every applicable supplied selector intersects the exact observation keys before aggregation and "
                 "paging; the stored summary rows are the unfiltered selection",
    "reading": SUMMARY_READING,
}


def summary_row(key: str, scope_kind: str, scope_id: str, observations: list[dict[str, Any]],
                qualifications: list[dict[str, Any]]) -> dict[str, Any]:
    return {"record_type": RECORD_TYPES["summary"], "summary_key": key, "scope_kind": scope_kind, "scope_id": scope_id,
            "observations": len(observations),
            "distinct_source_recruit_ids": len({o["source_recruit_id"] for o in observations}),
            "athlete_id_observations": sum(1 for o in observations if o["source_athlete_id"] is not None),
            "recruit_only_observations": sum(1 for o in observations if o["source_athlete_id"] is None),
            "negative_athlete_id_observations": sum(1 for o in observations if (o["source_athlete_id"] or "")
                                                    .startswith("-")),
            "distinct_canonical_players": len({q["canonical_player_id"] for q in qualifications
                                               if q["canonical_player_id"] is not None}),
            "distinct_canonical_teams": len({q["canonical_team_id"] for q in qualifications
                                             if q["canonical_team_id"] is not None}),
            "person_states": _count(q["person_state"] for q in qualifications),
            "person_reasons": _count(r for q in qualifications for r in q["person_reasons"]),
            "program_label_states": _count(q["program_label_state"] for q in qualifications),
            "program_states": _count(q["program_state"] for q in qualifications),
            "rating_kinds": _count(o["source_field_kinds"]["rating"] for o in observations),
            "ranking_kinds": _count(o["source_field_kinds"]["ranking"] for o in observations),
            "stars_kinds": _count(o["source_field_kinds"]["stars"] for o in observations),
            "rating_triplet_states": _count(q["rating_triplet_state"] for q in qualifications),
            "rating_domain_states": _count(q["rating_domain_state"] for q in qualifications),
            "ranking_domain_states": _count(q["ranking_domain_state"] for q in qualifications),
            "stars_domain_states": _count(q["stars_domain_state"] for q in qualifications),
            "cohort_year_states": _count(q["cohort_year_state"] for q in qualifications),
            "recruit_types": _count(o["recruit_type"] for o in observations),
            "positions": _count(o["position"] for o in observations),
            "legacy_observation_states": _count(q["legacy_observation_state"] for q in qualifications),
            "legacy_program_agreements": _count(q["legacy_program_agreement"] for q in qualifications),
            "historical_times_known": sum(1 for q in qualifications for name in TIME_FIELDS if q[name] is not None),
            "pit_eligible_observations": sum(1 for q in qualifications if q["pit_eligible"] is not False),
            "reading": SUMMARY_READING, **RECORD_LABELS}


def summary_rows(observations: list[dict[str, Any]], qualifications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The summary of a selection (observations and their qualifications in canonical order); none when empty."""
    if not observations:
        return []
    rows = [summary_row("SELECTION|ALL", "SELECTION", "ALL", observations, qualifications)]
    for season in sorted({o["request_season"] for o in observations}):
        obs = [o for o in observations if o["request_season"] == season]
        quals = [q for q in qualifications if q["request_season"] == season]
        rows.append(summary_row(f"REQUEST_SEASON|{season}", "REQUEST_SEASON", str(season), obs, quals))
    return rows


def census_record(records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    partitions, sources = records["partitions"], records["sources"]
    obs, quals = records["observations"], records["qualifications"]
    captured = [p for p in partitions if p["request_state"] == "CAPTURED"]
    portal = [p for p in captured if p["dataset"] == PORTAL_DATASET]
    population = {
        "requested_cells": len(partitions), "captured_cells": len(captured),
        "not_captured_cells": len(partitions) - len(captured),
        "missing_reasons": _count(p["missing_reason"] for p in partitions if p["request_state"] != "CAPTURED"),
        "captured_cells_by_dataset": _count(p["dataset"] for p in captured),
        "requested_cells_by_dataset": _count(p["dataset"] for p in partitions),
        "recruiting_captures": sum(1 for p in captured if p["dataset"] == RECRUIT_DATASET),
        "portal_captures": len(portal),
        "empty_portal_captures": sum(1 for p in portal if p["payload_state"] == "EMPTY_ARRAY"),
        "distinct_portal_capture_ids": len({p["capture_id"] for p in portal}),
        "distinct_portal_payload_sha256": len({p["response_sha256"] for p in portal}),
        "portal_rows": sum(p["row_count"] or 0 for p in portal),
        "observations": len(obs),
        "observations_by_request_season": _count(o["request_season"] for o in obs),
        "athlete_id_observations": sum(1 for o in obs if o["source_athlete_id"] is not None),
        "recruit_only_observations": sum(1 for o in obs if o["source_athlete_id"] is None),
        "negative_athlete_id_observations": sum(1 for o in obs if (o["source_athlete_id"] or "").startswith("-")),
        "person_states": _count(q["person_state"] for q in quals),
        "program_states": _count(q["program_state"] for q in quals),
        "rating_kinds": _count(o["source_field_kinds"]["rating"] for o in obs),
        "rating_triplet_states": _count(q["rating_triplet_state"] for q in quals),
        "file_source_witnesses": sum(1 for s in sources if s["witness_kind"] == "FILE"),
        "core_row_witnesses": sum(1 for s in sources if s["witness_kind"] != "FILE"),
        "historical_times_known": sum(1 for q in quals for name in TIME_FIELDS if q[name] is not None),
        "pit_eligible_observations": sum(1 for q in quals if q["pit_eligible"] is not False),
        "national_expected_universe": "NOT_ESTABLISHED",
        "coverage_reading": "34 requested cells and the captured observations are the finite retained source; they are "
                            "not a national FBS/FCS recruit, signing, enrollment or program-season universe",
    }
    return {"record_type": RECORD_TYPES["census"], "census_key": "census", "population": population, **RECORD_LABELS}


# --------------------------------------------------------------------------------------------- selection

GRAINS = {"recruiting-observation": "observations", "recruiting-qualification": "qualifications",
          "recruiting-partition": "partitions", "recruiting-source": "sources", "recruiting-summary": "summary"}
SELECTOR_NAMES = ("season", "team", "player", "recruit")
APPLICABILITY = {"recruiting-observation": ("season", "team", "player", "recruit"),
                 "recruiting-qualification": ("season", "team", "player", "recruit"),
                 "recruiting-summary": ("season", "team", "player", "recruit"),
                 "recruiting-partition": ("season",), "recruiting-source": ()}
SELECTORS = {
    "season": "string: a raw Cc control or lone surrogate refuses; only U+0020 spaces trim; four ASCII digits 1000-9999; "
              "a direct integer the same range (a boolean or float is invalid); SEASON_INVALID. It selects the "
              "captured request season; a valid unknown season selects nothing; on partitions it selects only exact "
              "single-year cells (the two minYear/maxYear coach cells have season null)",
    "team": "team_<32 lower hex> after the same control/surrogate/U+0020 rule; TEAM_INVALID; the qualified canonical "
            "program reference only (never a raw label)",
    "player": "player_<32 lower hex> after the same rule; PLAYER_INVALID; the qualified source person correspondence",
    "recruit": "1-12 ASCII digits after the same rule, kept as the exact string (no integer normalization; a leading "
               "zero is another opaque ID); RECRUIT_INVALID",
    "names": "no name selector exists; Unicode source text is served in record fields, never accepted as an ID",
    "applicability": APPLICABILITY,
    "intersection": "applicable selectors intersect exact observation keys before summaries and paging; an "
                    "inapplicable supplied selector is FILTER_NOT_APPLICABLE; nothing is silently ignored",
    "paging": "defaults limit 50, offset 0; strings: control/surrogate refuse, U+0020 trims, an optional leading minus "
              "and 1-12 ASCII digits; a direct integer of at most 12 digits; booleans and floats invalid; negatives "
              "NEGATIVE_LIMIT / NEGATIVE_OFFSET; --all with any explicit --limit or --offset is PAGING_CONFLICT; limit "
              "0 serves rows [] with the selected total and next_offset = offset when offset < total, otherwise null; "
              "positive or unbounded pages next_offset = offset + returned only while rows remain",
    "temporal": "any supplied --as-of (empty included) AS_OF_STATE_NOT_SUPPORTED; --require-pit "
                "RECRUITING_PIT_NOT_ADMITTED",
}
PRECEDENCE = ["parser_and_mode_conflict", "require_pit", "provided_as_of", "grain", "season", "team", "player",
              "recruit", "selector_applicability", "all_explicit_paging_conflict", "limit_type_then_negative",
              "offset_type_then_negative", "expected_identity_grammar", "database_literal_spelling",
              "explicit_manifest_literal_spelling", "native_local_existence_names_layout",
              "manifest_identity_hash_schema_and_complete_collection"]
REFUSALS = {
    "exit_code": 2,
    "stderr": "one JSON object with members refused (the code) and error (the text); nothing on stdout; no traceback",
    "selection": ["ARGUMENT_INVALID", "RECRUITING_MODE_CONFLICT", "RECRUITING_PIT_NOT_ADMITTED",
                  "AS_OF_STATE_NOT_SUPPORTED", "UNKNOWN_GRAIN", "SEASON_INVALID", "TEAM_INVALID", "PLAYER_INVALID",
                  "RECRUIT_INVALID", "FILTER_NOT_APPLICABLE", "PAGING_CONFLICT", "LIMIT_INVALID", "OFFSET_INVALID",
                  "NEGATIVE_LIMIT", "NEGATIVE_OFFSET", "STALE_RECRUITING_IDENTITY"],
    "location": ["RECRUITING_DATABASE_LOCATION_UNSUPPORTED", "RECRUITING_DATABASE_LOCATION_NOT_LITERAL",
                 "RECRUITING_MANIFEST_LOCATION_UNSUPPORTED", "RECRUITING_MANIFEST_LOCATION_NOT_LITERAL",
                 "RECRUITING_DATABASE_MISSING", "RECRUITING_LOCATION_INVALID", "RECRUITING_MANIFEST_MISSING",
                 "RECRUITING_DATABASE_UNREADABLE"],
    "manifest_and_identity": ["RECRUITING_MANIFEST_MALFORMED", "RECRUITING_IDENTITY_MISMATCH",
                              "RECRUITING_SCHEMA_UNSUPPORTED", "RECRUITING_IDENTITY_DOCUMENT_MISMATCH",
                              "RECRUITING_DATABASE_TAMPERED", "RECRUITING_CONTRACT_MISMATCH",
                              "RECRUITING_CONTENT_IDENTITY_MISMATCH", "RECRUITING_PROFILE_MISMATCH"],
    "meta": ["RECRUITING_META_MISMATCH", "RECRUITING_META_MALFORMED", "RECRUITING_PIT_CLAIM_INVALID",
             "RECRUITING_LABEL_CLAIM_INVALID", "RECRUITING_INPUTS_CLAIM_INVALID", "RECRUITING_RULES_CLAIM_INVALID",
             "RECRUITING_COUNT_MISMATCH"],
    "blocks_and_records": ["RECRUITING_INDEX_MISMATCH", "RECRUITING_RECORD_TYPE_INVALID", "RECRUITING_RECORD_MALFORMED",
                           "RECRUITING_RECORD_SHAPE_INVALID", "RECRUITING_FIELD_TYPE_INVALID",
                           "RECRUITING_RECORD_NOT_CANONICAL"],
    "collections": ["RECRUITING_DUPLICATE_ROW", "RECRUITING_ORDER_MISMATCH",
                    *[f"RECRUITING_{label}_{kind}" for label in TABLE_LABELS.values()
                      for kind in ("ROW_MISSING", "ROW_EXTRA", "KEYS_MISMATCH")]],
    "rules": ["RECRUITING_OBSERVATION_KEY_MISMATCH", "RECRUITING_CAPTURE_BINDING_INVALID",
              "RECRUITING_SOURCE_ID_INVALID", "RECRUITING_DUPLICATE_SOURCE_ID", "RECRUITING_OBSERVATION_KIND_MISMATCH",
              "RECRUITING_QUALIFICATION_BINDING_INVALID", "RECRUITING_TIME_CLAIM_INVALID",
              "RECRUITING_IDENTITY_KEY_MISMATCH", "RECRUITING_PERSON_CORRESPONDENCE_INVALID",
              "RECRUITING_PROGRAM_CORRESPONDENCE_INVALID", "RECRUITING_VALUE_STATE_MISMATCH",
              "RECRUITING_LEGACY_WITNESS_MISMATCH", "RECRUITING_QUALIFICATION_MISMATCH",
              "RECRUITING_PARTITION_MISMATCH", "RECRUITING_SOURCE_MISMATCH", "RECRUITING_SOURCE_CLOSURE_INVALID",
              "RECRUITING_SUMMARY_MISMATCH", "RECRUITING_CENSUS_MISMATCH"],
    "malformed_json_reasons": ["JSON_LONE_SURROGATE", "JSON_NESTING_TOO_DEEP", "JSON_NONFINITE_NUMBER",
                               "JSON_INTEGER_TOO_LONG"],
    "build_inputs": ["RECRUITING_DATA_ROOT_MISSING", "RECRUITING_DATA_ROOT_LOCATION_UNSUPPORTED",
                     "RECRUITING_DATA_ROOT_LOCATION_NOT_LITERAL", "RECRUITING_INPUT_LOCATION_UNSUPPORTED",
                     "RECRUITING_INPUT_LOCATION_NOT_LITERAL", "RECRUITING_INPUT_MISSING", "RECRUITING_INPUT_TAMPERED",
                     "RECRUITING_INPUT_MALFORMED", "RECRUITING_SOURCE_SCHEMA_INVALID",
                     "RECRUITING_SOURCE_DUPLICATE_ID", "RECRUITING_RECEIPT_MISMATCH",
                     "RECRUITING_INPUT_POPULATION_DRIFT"],
}
SCOPE = {
    "population": "every retained 2010-2017 recruiting observation of the eight captured recruiting arrays and all 34 "
                  "requested cells of the original acquisition manifest (15 captured, 19 provider-quota missing, "
                  "including seven distinct empty 2010-2016 portal captures)",
    "registry_reads": "whole registry files are hashed and scanned only for the exact identity, source-mapping, legacy "
                      "observation, team alias and team entity witnesses of these observations; no roster, game, "
                      "feature, label or 2024/2025 evaluation row is selected",
    "not_in_scope": "source acquisition, fits, features, forecasts, PIT admission, rosters, enrollment, availability, "
                    "transfer histories, talent priors, class scores, national completeness and A&M specialization",
    "foreknowledge": "the manager's readiness counts (28,093 observations, 21,194 literal program correspondences, "
                     "6,844 null and 55 unmapped labels, 890 joint-null triplets, 3/27,200/890 rating kinds, 5,339 "
                     "negative athlete IDs) were known before these rules were frozen; no blind claim is made and none "
                     "is a forced expectation",
}


class RecruitingError(ValueError):
    """A refused build input, selection or release; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise RecruitingError(code, message)


def rules_document() -> dict[str, Any]:
    """Every frozen rule as one document (deep copies: no caller can mutate the module's rules)."""
    return copy.deepcopy({
        "contract_id": CONTRACT_ID, "population": POPULATION, "labels": LABELS, "record_label_keys":
            list(RECORD_LABEL_KEYS), "source_schema": SOURCE_SCHEMA, "served_fields": list(SERVED_FIELDS),
        "field_names": FIELD_NAMES, "identity": IDENTITY_RULES, "program": PROGRAM_RULES, "values": VALUE_RULES,
        "time": TIME_RULES, "time_fields": list(TIME_FIELDS), "person_states": list(PERSON_STATES),
        "person_reasons": list(PERSON_REASONS), "legacy_states": list(LEGACY_STATES),
        "legacy_program_agreements": list(LEGACY_PROGRAM_AGREEMENTS),
        "alias_witness_states": list(ALIAS_WITNESS_STATES), "team_witness_states": list(TEAM_WITNESS_STATES),
        "people_columns": list(PEOPLE_COLUMNS), "core_columns": list(CORE_COLUMNS),
        "field_types": FIELD_TYPES, "subspecs": SUBSPECS, "record_types": RECORD_TYPES, "layout": LAYOUT,
        "summary": SUMMARY_RULES, "grains": GRAINS, "selectors": SELECTORS, "precedence": PRECEDENCE,
        "refusals": REFUSALS, "scope": SCOPE, "file_roles": FILE_ROLE_MEANINGS, "core_roles": CORE_ROLE_MEANINGS,
        "dataset_order": list(DATASET_ORDER), "recruit_seasons": list(RECRUIT_SEASONS)})


def rules_sha256() -> str:
    return sha256_bytes(canonical_json_bytes(rules_document()))


# --------------------------------------------------------------------------------------------- untrusted JSON

JSON_LONE_SURROGATE = "JSON_LONE_SURROGATE"
JSON_NESTING_TOO_DEEP = "JSON_NESTING_TOO_DEEP"
JSON_NONFINITE_NUMBER = "JSON_NONFINITE_NUMBER"
JSON_INTEGER_TOO_LONG = "JSON_INTEGER_TOO_LONG"


class _InvalidNumber(ValueError):
    pass


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise _InvalidNumber(f"{text} is not a finite binary64 number")
    return value


def _no_constant(text: str) -> Any:
    raise _InvalidNumber(f"{text} is not a JSON number")


def loads_untrusted(text: Any, code: str, where: str, non_json_code: str | None = None) -> Any:
    """Decode untrusted JSON: NaN, Infinity, a float literal beyond binary64 range and an integer beyond the
    interpreter's digit limit are malformed data refused with ``code`` and their reason (never a traceback); nesting
    beyond the decoder's depth is refused; other syntax errors are refused with ``non_json_code`` (default ``code``)."""
    try:
        return json.loads(text, parse_float=_finite_float, parse_constant=_no_constant)
    except _InvalidNumber as exc:
        raise RecruitingError(code, f"{where}: {JSON_NONFINITE_NUMBER} ({exc})") from exc
    except RecursionError as exc:
        raise RecruitingError(code, f"{where}: {JSON_NESTING_TOO_DEEP} (deeper than the decoder accepts)") from exc
    except ValueError as exc:
        if "integer string conversion" in str(exc) or "Exceeds the limit" in str(exc):
            raise RecruitingError(code, f"{where}: {JSON_INTEGER_TOO_LONG}") from exc
        raise RecruitingError(non_json_code or code, f"{where}: not JSON ({exc})") from exc


def canonical_untrusted(value: Any, code: str, where: str) -> bytes:
    try:
        return canonical_json_bytes(value)
    except UnicodeEncodeError as exc:
        raise RecruitingError(code, f"{where}: {JSON_LONE_SURROGATE} (U+{ord(exc.object[exc.start]):04X} is not "
                                    "Unicode text)") from exc
    except RecursionError as exc:
        raise RecruitingError(code, f"{where}: {JSON_NESTING_TOO_DEEP} (deeper than the encoder accepts)") from exc
    except ValueError as exc:
        raise RecruitingError(code, f"{where}: {JSON_NONFINITE_NUMBER} ({exc})") from exc


def _json_or_none(text: Any, name: str = "") -> Any:
    if not isinstance(text, (str, bytes)):
        return None
    try:
        return loads_untrusted(text, "RECRUITING_META_MALFORMED", f"meta {name}", non_json_code="NOT_JSON")
    except RecruitingError as exc:
        if exc.code == "NOT_JSON":
            return None
        raise


_SCALAR_TYPES = {"s": (str,), "s?": (str, _NONE), "i": (int,), "i?": (int, _NONE), "b": (bool,)}


def _check_type(code: str, value: Any) -> bool:
    if code in _SCALAR_TYPES:
        return type(value) in _SCALAR_TYPES[code]
    if code == "num?":
        return value is None or type(value) is int or (type(value) is float and math.isfinite(value))
    if code == "ls":
        return type(value) is list and all(type(x) is str for x in value)
    if code == "kinds":
        return type(value) is dict and set(value) == set(SERVED_FIELDS) and all(type(v) is str for v in value.values())
    if code == "j":
        return True
    if code.startswith("l@"):
        spec = SUBSPECS[code[2:]]
        return type(value) is list and all(type(item) is dict and set(item) == set(spec) and
                                           all(_check_type(c, item[k]) for k, c in spec.items()) for item in value)
    return False


# --------------------------------------------------------------------------------------------- storage

def record_key(table: str, record: dict[str, Any]) -> str:
    return str(record.get(KEY_FIELDS[table]))


def record_lines(derived: dict[str, Any]) -> dict[str, list[str]]:
    if "lines" not in derived:
        derived["lines"] = {table: [canonical_line(r) for r in derived[table]] for table in RECORD_TABLES}
    return derived["lines"]


def segment_of(table: str, record: dict[str, Any]) -> str:
    return str(record["request_season"]) if table in SEASONAL_TABLES else "GLOBAL"


BLOCK_LAYOUT = tuple(tuple(b) for b in LAYOUT["database"]["block_layout"])
DDL = tuple(tuple(d) for d in LAYOUT["database"]["ddl"])
TABLES = ("meta", "blocks")


def block_lines(derived: dict[str, Any]) -> list[tuple[str, str, list[dict[str, Any]], list[str]]]:
    lines = record_lines(derived)
    grouped: dict[tuple[str, str], tuple[list[dict[str, Any]], list[str]]] = {}
    for table in RECORD_TABLES:
        for record, line in zip(derived[table], lines[table]):
            bucket = grouped.setdefault((table, segment_of(table, record)), ([], []))
            bucket[0].append(record)
            bucket[1].append(line)
    return [(table, segment, *grouped.get((table, segment), ([], []))) for table, segment in BLOCK_LAYOUT]


def observation_chunk(derived: dict[str, Any], keys: Iterable[str]) -> bytes:
    """The checkpoint unit: every observation and qualification line of the given observations (deterministic)."""
    wanted = set(keys)
    out = []
    for table, segment, records, lines in block_lines(derived):
        if segment == "GLOBAL":
            continue
        out += [f"{table}\t{segment}\t{line}" for record, line in zip(records, lines)
                if record_key(table, record) in wanted]
    return ("\n".join(out) + "\n").encode("utf-8")


def row_counts(derived: dict[str, Any]) -> dict[str, int]:
    return {table: len(derived[table]) for table in RECORD_TABLES}


def inputs_claim(anchors: dict[str, Any]) -> dict[str, Any]:
    return {"inputs": anchors["inputs"], "expected": anchors["expected"], "frozen_at_utc": anchors["frozen_at_utc"]}


def content_document(anchors: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
    lines = record_lines(derived)
    return {"schema": CONTENT_SCHEMA, "stage": CONTENT_STAGE, "population": POPULATION,
            "contract_id": anchors["contract_id"], "contract_sha256": anchors["contract_sha256"],
            "inputs": inputs_claim(anchors), "rules_sha256": rules_sha256(), "payload_schema": PAYLOAD_SCHEMA,
            "row_counts": row_counts(derived),
            "lines_sha256": {table: lines_sha256(lines[table]) for table in RECORD_TABLES},
            "blocks": [[table, segment, len(block), lines_sha256(block)]
                       for table, segment, _records, block in block_lines(derived)]}


def database_document(contract_sha256: str, content_identity: str, database_sha256: str,
                      table_counts: dict[str, int]) -> dict[str, Any]:
    return {"schema": DATABASE_SCHEMA, "stage": DATABASE_STAGE, "population": POPULATION,
            "contract_sha256": contract_sha256, "content_identity": content_identity, "db_schema_version": DB_SCHEMA,
            "outputs": {DB_FILE: database_sha256}, "table_counts": dict(table_counts)}


def meta_values(anchors: dict[str, Any], content_identity: str, derived: dict[str, Any]) -> dict[str, str]:
    lines = record_lines(derived)
    return {"schema_version": DB_SCHEMA, "contract_id": anchors["contract_id"],
            "contract_sha256": anchors["contract_sha256"], "content_identity": content_identity,
            "inputs": canonical_line(inputs_claim(anchors)), "labels": canonical_line(LABELS),
            "rules": canonical_line(rules_document()), "row_counts": canonical_line(row_counts(derived)),
            "summary_sha256": lines_sha256(lines["summary"]), "census_sha256": lines_sha256(lines["census"])}


def block_rows(derived: dict[str, Any]) -> list[tuple[Any, ...]]:
    rows = []
    for ord_, (table, segment, records, lines) in enumerate(block_lines(derived)):
        data = "".join(line + "\n" for line in lines).encode("utf-8")
        rows.append((ord_, table, segment, len(lines), record_key(table, records[0]) if records else None,
                     record_key(table, records[-1]) if records else None, sha256_bytes(data), zlib.compress(data, 9)))
    return rows


def build_database(path: Path, derived: dict[str, Any], meta: dict[str, str]) -> dict[str, int]:
    """A fresh deterministic SQLite file: page size 4096, no journal, rows inserted in layout order, no deletes."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA journal_mode = OFF")
        for _kind, _name, ddl in DDL:
            conn.execute(ddl)
        conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", sorted(meta.items()))
        conn.executemany("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", block_rows(derived))
        conn.commit()
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
    finally:
        conn.close()
    return counts


MANIFEST_MEMBERS = ("content_document", "content_identity", "identity", "identity_document", "provenance")


# --------------------------------------------------------------------------------------------- expected collections

SUMMARY_KEYS = ["SELECTION|ALL", *[f"REQUEST_SEASON|{s}" for s in RECRUIT_SEASONS]]


def expected_counts(expected: dict[str, Any]) -> dict[str, int]:
    observations = sum(spec["rows"] for spec in expected["observations"].values())
    return {"observations": observations, "qualifications": observations, "partitions": len(expected["cells"]),
            "census": 1}


def file_source_keys(anchors: dict[str, Any]) -> list[str]:
    return [f"FILE|{name}" for name in input_names(anchors["inputs"])] + ["FILE|contract"]


# --------------------------------------------------------------------------------------------- native location

_VERBATIM_ROOT = re.compile(r"\\\\\?\\[A-Za-z]:\\")
_DRIVE_ROOT = re.compile(r"[A-Za-z]:\\")
#: Characters FindFirstFileW reads as a pattern; a component holding one keeps the spelling it was given.
_FIND_PATTERN_CHARACTERS = frozenset('*?<>"')


def _directory_entry_names(query: str) -> tuple[str, str] | None:
    """The long and 8.3 names of the one directory entry Windows resolves the last component of ``query`` to
    (FindFirstFileW: the entry's own name in its parent directory, never the target of a junction or link), or None when
    Windows cannot report it, for example below a directory the caller may traverse but not list."""
    import ctypes  # noqa: PLC0415 - Windows only
    from ctypes import wintypes  # noqa: PLC0415 - Windows only

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.FindFirstFileW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.WIN32_FIND_DATAW)]
    kernel32.FindFirstFileW.restype = wintypes.HANDLE
    kernel32.FindClose.argtypes = [wintypes.HANDLE]
    kernel32.FindClose.restype = wintypes.BOOL
    data = wintypes.WIN32_FIND_DATAW()
    handle = kernel32.FindFirstFileW(query, ctypes.byref(data))
    if handle is None or handle == wintypes.HANDLE(-1).value:
        return None
    kernel32.FindClose(handle)
    return data.cFileName, data.cAlternateFileName


def native_location(location: str) -> str:
    """The native spelling of an existing local Windows file (the accepted C61 rule, MF61A01-01; the same body as the
    accepted C63 reader's).

    ``location`` is the literal local path (:func:`aggie_analytics.readonly_sqlite.literal_path`: a drive path or its
    native extended-length form; network and device spellings were refused before any filesystem access). Each component
    after the drive becomes the name of the directory entry Windows resolves it to: an 8.3 short name becomes its long
    name and a case-equivalent spelling becomes the entry's own spelling, so the release layout and identity are
    checked on the genuine names of the file that is opened. A junction or link component keeps its own entry name (its
    target is never substituted). A component Windows cannot report, or one whose reported entry does not carry that
    spelling as its long or 8.3 name, keeps the spelling it was given (the literal rule). POSIX spellings are never
    rewritten here."""
    if os.name != "nt":
        return location
    verbatim = location.startswith("\\\\?\\")
    root_match = (_VERBATIM_ROOT if verbatim else _DRIVE_ROOT).match(location)
    if root_match is None:
        return location
    root = root_match.group(0)
    parts = location[len(root):].split("\\")
    if not all(parts):
        return location
    resolved: list[str] = []
    for part in parts:
        spelled = part
        if not _FIND_PATTERN_CHARACTERS.intersection(part):
            query = root + "\\".join([*resolved, part])
            if not verbatim and len(query) >= 250:
                query = "\\\\?\\" + query
            names = _directory_entry_names(query)
            if names is not None:
                long_name, short_name = names
                if long_name and (long_name.casefold() == part.casefold() or
                                  (short_name and short_name.casefold() == part.casefold())):
                    spelled = long_name
        resolved.append(spelled)
    return root + "\\".join(resolved)


# --------------------------------------------------------------------------------------------- selection checks

def _raw_control(text: str) -> str | None:
    """The first raw Unicode category Cc character (C0 U+0000-U+001F, DEL U+007F, C1 U+0080-U+009F) or None."""
    return next((c for c in text if ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F), None)


def _surrogate(text: str) -> str | None:
    return next((c for c in text if 0xD800 <= ord(c) <= 0xDFFF), None)


def _selector_text(value: Any, code: str, what: str) -> str:
    """A supplied string selector after the frozen boundary: a raw control or lone surrogate refuses before anything
    else; only U+0020 spaces at either end are trimmed."""
    if type(value) is not str:
        _refuse(code, f"{what} must be a string, got {type(value).__name__}")
    control = _raw_control(value)
    if control is not None:
        _refuse(code, f"{what} must not contain the raw control U+{ord(control):04X}")
    surrogate = _surrogate(value)
    if surrogate is not None:
        _refuse(code, f"{what} must be Unicode text: U+{ord(surrogate):04X} is a lone surrogate")
    return value.strip(" ")


def validate_season(value: Any) -> int:
    if type(value) is int:
        if 1000 <= value <= 9999:
            return value
        _refuse("SEASON_INVALID", f"season must be 1000-9999, got {value!r}")
    if type(value) is not str:
        _refuse("SEASON_INVALID", f"season must be four ASCII digits, got {type(value).__name__}")
    text = _selector_text(value, "SEASON_INVALID", "season")
    if not SEASON_TEXT_RE.match(text) or not 1000 <= int(text) <= 9999:
        _refuse("SEASON_INVALID", f"season must be four ASCII digits 1000-9999, got {value!r}")
    return int(text)


def validate_selection(grain: Any, *, season: Any = None, team: Any = None, player: Any = None,
                       recruit: Any = None) -> dict[str, Any]:
    """Validate a selection before any file is read, in the frozen precedence: grain, season, team, player, recruit,
    then applicability."""
    if not isinstance(grain, str) or grain not in GRAINS:
        _refuse("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}, got {grain!r}")
    out: dict[str, Any] = {}
    if season is not None:
        out["season"] = validate_season(season)
    if team is not None:
        text = _selector_text(team, "TEAM_INVALID", "team")
        if not TEAM_ID_RE.match(text):
            _refuse("TEAM_INVALID", f"team must be a canonical team_<32 lower hex> ID (no name selector), got {team!r}")
        out["team"] = text
    if player is not None:
        text = _selector_text(player, "PLAYER_INVALID", "player")
        if not PLAYER_ID_RE.match(text):
            _refuse("PLAYER_INVALID", f"player must be a canonical player_<32 lower hex> ID (no name selector), got "
                                      f"{player!r}")
        out["player"] = text
    if recruit is not None:
        text = _selector_text(recruit, "RECRUIT_INVALID", "recruit")
        if not RECRUIT_ID_RE.match(text):
            _refuse("RECRUIT_INVALID", f"recruit must be a source recruit ID of 1-12 ASCII digits, got {recruit!r}")
        out["recruit"] = text
    allowed = APPLICABILITY[grain]
    for name in SELECTOR_NAMES:
        if name in out and name not in allowed:
            _refuse("FILTER_NOT_APPLICABLE", f"--{name} does not apply to the {grain} grain (applicable: "
                                             f"{list(allowed)})")
    return out


def _page_integer(value: Any, code: str, what: str) -> int:
    if type(value) is int:
        if len(str(abs(value))) > 12:
            _refuse(code, f"{what} must have at most 12 digits, got {value!r}")
        return value
    if type(value) is not str:
        _refuse(code, f"{what} must be an integer, got {type(value).__name__}")
    text = _selector_text(value, code, what)
    if not PAGE_TEXT_RE.match(text):
        _refuse(code, f"{what} must be an integer of 1-12 ASCII digits with an optional leading minus, got {value!r}")
    return int(text)


def validate_paging(limit: Any, offset: Any, all_rows: bool, *, limit_given: bool, offset_given: bool
                    ) -> tuple[int | None, int]:
    """Frozen paging: --all never combines with an explicit --limit or --offset; then the limit's type and sign; then
    the offset's."""
    if all_rows and (limit_given or offset_given):
        _refuse("PAGING_CONFLICT", "--all returns every row and cannot be combined with an explicit --limit or --offset")
    lim = _page_integer(limit, "LIMIT_INVALID", "limit")
    if lim < 0:
        _refuse("NEGATIVE_LIMIT", "limit must be zero or positive")
    off = _page_integer(offset, "OFFSET_INVALID", "offset")
    if off < 0:
        _refuse("NEGATIVE_OFFSET", "offset must be zero or positive")
    return (None if all_rows else lim), off


def validate_expected_identity(value: Any) -> None:
    if value is not None and not (type(value) is str and IDENTITY_RE.match(value)):
        _refuse("STALE_RECRUITING_IDENTITY", "--expect-identity must be a SHA-256 identity (64 lower hex)")


def page(rows: list[Any], limit: int | None, offset: int) -> tuple[list[Any], int | None]:
    total = len(rows)
    if limit == 0:
        return [], (offset if offset < total else None)
    chunk = rows[offset:] if limit is None else rows[offset:offset + limit]
    end = offset + len(chunk)
    return chunk, (end if chunk and end < total else None)


# --------------------------------------------------------------------------------------------- the reader

_FIELD_GROUP_CODES = (
    ("RECRUITING_TIME_CLAIM_INVALID", ("capture_known_at_utc", "retrieved_at_utc", "provider_http_date",
                                       *TIME_FIELDS, "pit_eligible", "time_state")),
    ("RECRUITING_IDENTITY_KEY_MISMATCH", ("source_namespace", "identity_key", "source_mapping_entity_key")),
    ("RECRUITING_PERSON_CORRESPONDENCE_INVALID", ("person_state", "person_reasons", "canonical_player_id",
                                                  "assignment_slot", "person_witnesses", "mapping_witnesses",
                                                  "person_meaning")),
    ("RECRUITING_PROGRAM_CORRESPONDENCE_INVALID", ("program_label", "program_label_state", "program_state",
                                                   "canonical_team_id", "candidate_team_ids", "alias_witnesses",
                                                   "team_witnesses", "program_meaning",
                                                   "historical_membership_state")),
    ("RECRUITING_VALUE_STATE_MISMATCH", ("rating_state", "rating_domain_state", "ranking_state",
                                         "ranking_domain_state", "stars_state", "stars_domain_state",
                                         "rating_triplet_state", "rating_scale", "rating_system_version",
                                         "rating_upstream_independence", "cohort_year_state")),
    ("RECRUITING_LEGACY_WITNESS_MISMATCH", ("legacy_observation_witnesses", "legacy_observation_state",
                                            "legacy_program_agreement")),
)


def _core_witness_shape(stored: dict[str, Any]) -> None:
    """A core-row source witness carries one whole core registry row (every column, text) at a registry row number."""
    row = stored["row"]
    if type(row) is not dict or set(row) != set(CORE_COLUMNS) or not all(type(v) is str for v in row.values()) or \
            stored["witness_kind"] not in CORE_ROLE_MEANINGS or type(stored["registry_row"]) is not int:
        _refuse("RECRUITING_SOURCE_MISMATCH", f"{stored['source_key']}: not a core registry row witness")


class RecruitingEvidence:
    """A verified, read-only handle on one content-addressed national recruiting evidence release.

    Construction refuses (RecruitingError with a stable code) unless the release location, run manifest, database
    bytes, schema, meta claims, every record's exact members and JSON types, the complete expected collection of every
    grain, every observation rule, the exact re-derivation of every qualification, partition, file source, core-row
    witness, summary and census record, the content document, the contract-defined database identity document and (when
    the anchors pin one) the canonical profile verify. Each refusal is checked in a fixed order so that every forgery is
    refused for its own cause."""

    def __init__(self, database: Path, *, manifest: Path | None = None, expect_identity: str | None = None,
                 anchors: dict[str, Any] | None = None) -> None:
        self.anchors = anchors if anchors is not None else {**ANCHORS, "profile": RECRUITING_PROFILE}
        self.binding = self._verify_location_and_manifest(database, manifest, expect_identity)
        document = self.binding["identity_document"]
        if document.get("contract_sha256") != self.anchors["contract_sha256"]:
            _refuse("RECRUITING_CONTRACT_MISMATCH", f"the release names contract {document.get('contract_sha256')}, "
                                                    f"the reader binds {self.anchors['contract_sha256']}")
        try:
            location = readonly_sqlite.literal_path(self.binding["location"])
            self.conn = readonly_sqlite.connect_readonly(_io_path(Path(location)), immutable=False)
        except readonly_sqlite.DatabaseLocationError as exc:
            suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
            raise RecruitingError(f"RECRUITING_DATABASE_LOCATION_{suffix}", exc.detail) from exc
        except sqlite3.Error as exc:
            raise RecruitingError("RECRUITING_DATABASE_UNREADABLE", str(exc)) from exc
        try:
            self._verify_database()
        except sqlite3.DatabaseError as exc:
            self.conn.close()
            raise RecruitingError("RECRUITING_SCHEMA_UNSUPPORTED", str(exc)) from exc
        except BaseException:
            self.conn.close()
            raise

    # ---- outer identity
    @staticmethod
    def _verify_location_and_manifest(database: Path, manifest: Path | None,
                                      expect_identity: str | None) -> dict[str, Any]:
        try:
            literal = readonly_sqlite.literal_path(database)
        except readonly_sqlite.DatabaseLocationError as exc:
            suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
            raise RecruitingError(f"RECRUITING_DATABASE_LOCATION_{suffix}", exc.detail) from exc
        manifest_path = None
        if manifest is not None:
            try:
                manifest_path = Path(readonly_sqlite.literal_path(manifest))
            except readonly_sqlite.DatabaseLocationError as exc:
                suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
                raise RecruitingError(f"RECRUITING_MANIFEST_LOCATION_{suffix}", f"--manifest {manifest}: "
                                                                                f"{exc.detail}") from exc
        db = Path(database)
        if not _io_path(Path(literal) if os.name == "nt" else db).is_file():
            _refuse("RECRUITING_DATABASE_MISSING", f"no recruiting evidence database file at {db}")
        # On Windows the layout and identity are checked on the genuine names of the existing file (an 8.3 or
        # case-equivalent spelling of the same release is that release); every later read uses that one location.
        # POSIX keeps its native, case-sensitive spelling rule.
        absolute = Path(native_location(literal)) if os.name == "nt" else Path(os.path.abspath(db))
        db = absolute
        if absolute.name != DB_FILE or absolute.parent.parent.name != "sha256" or \
                absolute.parent.parent.parent.name != POPULATION:
            _refuse("RECRUITING_LOCATION_INVALID", f"the release must sit at <root>/{POPULATION}/sha256/<id>/{DB_FILE}")
        identity = absolute.parent.name
        if not IDENTITY_RE.match(identity):
            _refuse("RECRUITING_LOCATION_INVALID", f"directory name {identity!r} is not an identity")
        if manifest_path is None:
            manifest_path = manifest_path_for(db)
        if not _io_path(manifest_path).is_file():
            _refuse("RECRUITING_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
        try:
            raw = _io_path(manifest_path).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise RecruitingError("RECRUITING_MANIFEST_MALFORMED", str(exc)) from exc
        doc = loads_untrusted(raw, "RECRUITING_MANIFEST_MALFORMED", "run manifest")
        if not isinstance(doc, dict):
            _refuse("RECRUITING_MANIFEST_MALFORMED", "the run manifest is not a JSON object")
        if sorted(doc) != sorted(MANIFEST_MEMBERS):
            _refuse("RECRUITING_MANIFEST_MALFORMED", f"run manifest members {sorted(doc)} differ from "
                                                     f"{list(MANIFEST_MEMBERS)}")
        canonical_untrusted(doc, "RECRUITING_MANIFEST_MALFORMED", "run manifest")
        identity_document = doc["identity_document"]
        computed = sha256_bytes(canonical_untrusted(identity_document, "RECRUITING_MANIFEST_MALFORMED",
                                                    "run manifest identity document"))
        if computed != identity or doc.get("identity") != identity:
            _refuse("RECRUITING_IDENTITY_MISMATCH", f"manifest identity document hashes to {computed}, directory is "
                                                    f"{identity}, the manifest names {doc.get('identity')!r}")
        if not isinstance(identity_document, dict) or \
                (identity_document.get("stage"), identity_document.get("schema"),
                 identity_document.get("db_schema_version"), identity_document.get("population")) != \
                (DATABASE_STAGE, DATABASE_SCHEMA, DB_SCHEMA, POPULATION):
            _refuse("RECRUITING_SCHEMA_UNSUPPORTED", "not a national recruiting evidence database manifest")
        outputs = identity_document.get("outputs")
        if not isinstance(outputs, dict):
            _refuse("RECRUITING_IDENTITY_DOCUMENT_MISMATCH", "the manifest identity document's outputs is not an "
                                                             "object")
        actual_sha = sha256_file(_io_path(db))
        if outputs.get(DB_FILE) != actual_sha:
            _refuse("RECRUITING_DATABASE_TAMPERED", f"release bytes hash to {actual_sha}, manifest names "
                                                    f"{outputs.get(DB_FILE)}")
        if expect_identity is not None and expect_identity != identity:
            _refuse("STALE_RECRUITING_IDENTITY", f"expected {expect_identity}, found {identity}")
        return {"identity": identity, "sha256": actual_sha, "location": str(db), "manifest": str(manifest_path),
                "identity_document": identity_document, "content_document": doc["content_document"],
                "content_identity_claim": doc.get("content_identity"), "provenance": doc.get("provenance")}

    # ---- schema, meta claims, records, rules and identities
    def _verify_database(self) -> None:
        a = self.anchors
        master = sorted((str(r[0]), str(r[1]), r[2]) for r in self.conn.execute(
            "SELECT type, name, sql FROM sqlite_master"))
        if master != sorted(DDL):
            _refuse("RECRUITING_SCHEMA_UNSUPPORTED", "the release schema differs from the contract")
        meta_rows = [(str(r[0]), r[1]) for r in self.conn.execute("SELECT key, value FROM meta ORDER BY rowid")]
        meta = dict(meta_rows)
        if len(meta) != len(meta_rows):
            _refuse("RECRUITING_META_MISMATCH", "duplicate meta keys")
        if meta.get("schema_version") != DB_SCHEMA:
            _refuse("RECRUITING_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}")
        if meta.get("contract_sha256") != a["contract_sha256"] or meta.get("contract_id") != a["contract_id"]:
            _refuse("RECRUITING_CONTRACT_MISMATCH", "the release meta names another contract")
        claims = {name: _json_or_none(meta.get(name), name) for name in ("inputs", "labels", "rules")}
        if claims["labels"] != LABELS or canonical_untrusted(claims["labels"], "RECRUITING_META_MALFORMED",
                                                             "meta labels") != canonical_json_bytes(LABELS):
            labels = claims["labels"] if isinstance(claims["labels"], dict) else {}
            code = "RECRUITING_PIT_CLAIM_INVALID" if labels.get("pit_eligibility") != LABELS["pit_eligibility"] else \
                "RECRUITING_LABEL_CLAIM_INVALID"
            _refuse(code, "the release declares labels other than the contract's")
        if canonical_untrusted(claims["inputs"], "RECRUITING_META_MALFORMED", "meta inputs") != \
                canonical_json_bytes(inputs_claim(a)):
            _refuse("RECRUITING_INPUTS_CLAIM_INVALID", "the release was built from other inputs or expectations")
        if canonical_untrusted(claims["rules"], "RECRUITING_META_MALFORMED", "meta rules") != \
                canonical_json_bytes(rules_document()):
            _refuse("RECRUITING_RULES_CLAIM_INVALID", "the release declares other rules")
        counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        # value equality keeps a fractional, string or boolean count here; an integral float count is equal by value
        # and is refused last by the canonical-bytes identity-document rule
        if counts != self.binding["identity_document"].get("table_counts"):
            _refuse("RECRUITING_COUNT_MISMATCH",
                    f"table counts {counts} != {self.binding['identity_document'].get('table_counts')}")
        present = self._read_blocks()
        records = {table: [r for _l, r in present[table]] for table in RECORD_TABLES}
        lines = {table: [line for line, _r in present[table]] for table in RECORD_TABLES}
        self._verify_labels(records)
        self._verify_collections(records)
        self._verify_observations(records["observations"])
        self._verify_qualifications(records, lines)
        self._verify_partitions(records)
        self._verify_sources(records)
        self._verify_summary_and_census(records)
        derived = {table: records[table] for table in RECORD_TABLES}
        derived["lines"] = lines
        document = content_document(a, derived)
        content_identity = sha256_bytes(canonical_json_bytes(document))
        if canonical_untrusted(self.binding["content_document"], "RECRUITING_MANIFEST_MALFORMED",
                               "content document") != canonical_json_bytes(document) or \
                self.binding["content_identity_claim"] != content_identity or \
                meta.get("content_identity") != content_identity or \
                self.binding["identity_document"].get("content_identity") != content_identity:
            _refuse("RECRUITING_CONTENT_IDENTITY_MISMATCH", f"the rebuilt content identity is {content_identity}")
        expected_meta = meta_values(a, content_identity, derived)
        if meta != expected_meta:
            _refuse("RECRUITING_META_MISMATCH", "meta differs on " + str(sorted(
                k for k in set(meta) | set(expected_meta) if meta.get(k) != expected_meta.get(k))))
        identity_document = self.binding["identity_document"]
        expected_document = database_document(a["contract_sha256"], content_identity, self.binding["sha256"], counts)
        expected_bytes = canonical_json_bytes(expected_document)
        if canonical_untrusted(identity_document, "RECRUITING_MANIFEST_MALFORMED", "identity document") != \
                expected_bytes:
            differing = sorted(k for k in set(identity_document) | set(expected_document)
                               if k not in identity_document or k not in expected_document
                               or canonical_json_bytes(identity_document[k]) !=
                               canonical_json_bytes(expected_document[k]))
            _refuse("RECRUITING_IDENTITY_DOCUMENT_MISMATCH", f"the manifest identity document is not the contract-"
                                                             f"defined database document (differs on {differing})")
        database_identity = sha256_bytes(expected_bytes)
        if database_identity != self.binding["identity"]:
            _refuse("RECRUITING_IDENTITY_DOCUMENT_MISMATCH", f"the location names {self.binding['identity']}, the "
                                                             f"contract-defined document is {database_identity}")
        profile = a.get("profile")
        if profile is not None and (profile.get("content_identity"), profile.get("database_identity")) != \
                (content_identity, database_identity):
            _refuse("RECRUITING_PROFILE_MISMATCH", f"the release ({database_identity} / {content_identity}) is not the "
                                                   f"pinned canonical profile ({profile.get('database_identity')} / "
                                                   f"{profile.get('content_identity')})")
        self.database_identity = database_identity
        self.content_identity = content_identity
        self.meta = meta
        self.records = derived
        self.census = records["census"][0]["population"]
        self.qualification_by_key = {q["qualification_key"]: q for q in records["qualifications"]}

    def _read_blocks(self) -> dict[str, list[tuple[str, dict[str, Any]]]]:
        rows = [tuple(r) for r in self.conn.execute(
            "SELECT ord, record_table, segment, records, first_key, last_key, lines_sha256, block FROM blocks "
            "ORDER BY ord")]
        present: dict[str, list[tuple[str, dict[str, Any]]]] = {t: [] for t in RECORD_TABLES}
        layout = []
        for ord_, table, segment, records, first_key, last_key, lines_sha, blob in rows:
            if table not in present:
                _refuse("RECRUITING_SCHEMA_UNSUPPORTED", f"block {ord_} names table {table!r}")
            try:
                data = zlib.decompress(blob)
                lines = data.decode("utf-8").split("\n")
            except (zlib.error, TypeError, UnicodeDecodeError) as exc:
                raise RecruitingError("RECRUITING_INDEX_MISMATCH", f"block {ord_} does not decompress: {exc}") from exc
            if lines[-1] != "":
                _refuse("RECRUITING_INDEX_MISMATCH", f"block {ord_} does not end with a newline")
            parsed = []
            for line in lines[:-1]:
                record = loads_untrusted(line, "RECRUITING_RECORD_MALFORMED", f"block {ord_} ({table})",
                                         non_json_code="RECRUITING_RECORD_TYPE_INVALID")
                if not isinstance(record, dict):
                    _refuse("RECRUITING_RECORD_TYPE_INVALID", f"block {ord_} holds a non-object line")
                if not isinstance(record.get(KEY_FIELDS[table]), str):
                    _refuse("RECRUITING_RECORD_TYPE_INVALID", f"{table} record: {KEY_FIELDS[table]} is not a string")
                parsed.append((line, record))
            keys = [record_key(table, r) for _l, r in parsed]
            if sha256_bytes(data) != lines_sha or records != len(parsed) or \
                    first_key != (keys[0] if keys else None) or last_key != (keys[-1] if keys else None):
                _refuse("RECRUITING_INDEX_MISMATCH", f"block {ord_} index columns differ from its content")
            for _line, record in parsed:
                if table in SEASONAL_TABLES and str(record.get("request_season")) != segment:
                    _refuse("RECRUITING_INDEX_MISMATCH", f"block {ord_} ({table} {segment}) holds a record of "
                                                         f"season {record.get('request_season')!r}")
            layout.append((table, segment))
            present[table] += parsed
        if layout != list(BLOCK_LAYOUT):
            _refuse("RECRUITING_INDEX_MISMATCH", "the blocks do not follow the contract layout")
        for table in RECORD_TABLES:
            types = FIELD_TYPES[table]
            for line, record in present[table]:
                where = f"{table} record {record_key(table, record)}"
                if set(record) != set(types):
                    extra, missing = sorted(set(record) - set(types)), sorted(set(types) - set(record))
                    _refuse("RECRUITING_RECORD_SHAPE_INVALID", f"{where}: extra members {extra[:4]}, missing "
                                                               f"{missing[:4]}")
                for field, code in types.items():
                    if not _check_type(code, record[field]):
                        _refuse("RECRUITING_FIELD_TYPE_INVALID", f"{where}: {field} is a JSON "
                                                                 f"{json_kind(record[field])} or nested value outside "
                                                                 f"the contract type {code}")
                if line != canonical_untrusted(record, "RECRUITING_RECORD_MALFORMED", where).decode("utf-8"):
                    _refuse("RECRUITING_RECORD_NOT_CANONICAL", f"{where} is not its canonical JSON line")
        return present

    @staticmethod
    def _verify_labels(records: dict[str, list[dict[str, Any]]]) -> None:
        for table in RECORD_TABLES:
            want = RECORD_TYPES[table]
            for record in records[table]:
                if record["record_type"] != want:
                    _refuse("RECRUITING_RECORD_TYPE_INVALID", f"{table} record {record_key(table, record)} is a "
                                                              f"{record['record_type']!r}")
                for k in RECORD_LABEL_KEYS:
                    if record[k] != LABELS[k]:
                        _refuse("RECRUITING_PIT_CLAIM_INVALID" if k == "pit_eligibility" else
                                "RECRUITING_LABEL_CLAIM_INVALID", f"{table} record {record_key(table, record)}: {k} "
                                                                  f"is {record[k]!r}")

    def _verify_collections(self, records: dict[str, list[dict[str, Any]]]) -> None:
        """Membership, multiplicity, order and the pinned key universe of every grain: observation and qualification
        counts and key-sequence digests per captured partition, the exact partition and file-source keys, the closed
        summary keys and one census."""
        expected = self.anchors["expected"]
        counts = expected_counts(expected)
        listed = {"partitions": [c["cell_key"] for c in expected["cells"]],
                  "summary": SUMMARY_KEYS if records["observations"] else [], "census": ["census"]}
        for table in RECORD_TABLES:
            label = TABLE_LABELS[table]
            keys = [record_key(table, r) for r in records[table]]
            if len(keys) != len(set(keys)):
                _refuse("RECRUITING_DUPLICATE_ROW", f"{table} repeats a record key")
            if table in SEASONAL_TABLES:
                if len(keys) < counts[table]:
                    _refuse(f"RECRUITING_{label}_ROW_MISSING", f"{counts[table] - len(keys)} expected {table} absent")
                if len(keys) > counts[table]:
                    _refuse(f"RECRUITING_{label}_ROW_EXTRA", f"{len(keys) - counts[table]} {table} beyond the pinned "
                                                             "observation universe")
                order = [(r["request_season"], r["raw_row_ordinal"]) for r in records[table]]
                if order != sorted(order):
                    _refuse("RECRUITING_ORDER_MISMATCH", f"{table} is not in the contract order")
                for season, spec in sorted(expected["observations"].items()):
                    season_keys = [record_key(table, r) for r in records[table] if str(r["request_season"]) == season]
                    if len(season_keys) != spec["rows"]:
                        _refuse(f"RECRUITING_{label}_ROW_MISSING" if len(season_keys) < spec["rows"] else
                                f"RECRUITING_{label}_ROW_EXTRA", f"request season {season}: {len(season_keys)} {table} "
                                                                 f"for {spec['rows']} pinned observations")
                    if keys_sha256(season_keys) != spec["keys_sha256"]:
                        _refuse(f"RECRUITING_{label}_KEYS_MISMATCH", f"request season {season}: the {table} key "
                                                                     "sequence differs from the pinned universe")
                continue
            if table == "sources":
                files = file_source_keys(self.anchors)
                file_keys = [k for k in keys if k.startswith("FILE|")]
                missing = sorted(set(files) - set(file_keys))
                if missing:
                    _refuse("RECRUITING_SOURCE_ROW_MISSING", f"pinned file witnesses absent: {missing[:3]}")
                extra = sorted(set(file_keys) - set(files))
                if extra:
                    _refuse("RECRUITING_SOURCE_ROW_EXTRA", f"file witnesses outside the contract: {extra[:3]}")
                if keys[:len(files)] != files:
                    _refuse("RECRUITING_ORDER_MISMATCH", "file witnesses are not first in contract order")
                rows = [r["registry_row"] for r in records[table][len(files):]]
                if any(not k.startswith("CORE|") for k in keys[len(files):]) or \
                        any(type(n) is not int or n < 0 for n in rows) or rows != sorted(set(rows)):
                    _refuse("RECRUITING_ORDER_MISMATCH", "core-row witnesses are not in strictly increasing registry-row "
                                                         "order")
                continue
            want = listed[table]
            missing = sorted(set(want) - set(keys))
            if missing:
                _refuse(f"RECRUITING_{label}_ROW_MISSING", f"{len(missing)} expected {table} keys absent, e.g. "
                                                           f"{missing[:3]}")
            extra = sorted(set(keys) - set(want))
            if extra:
                _refuse(f"RECRUITING_{label}_ROW_EXTRA", f"{len(extra)} {table} keys outside the expected collection, "
                                                         f"e.g. {extra[:3]}")
            if keys != want:
                _refuse("RECRUITING_ORDER_MISMATCH", f"{table} is not in the contract order")

    def _verify_observations(self, observations: list[dict[str, Any]]) -> None:
        expected = self.anchors["expected"]
        recruits: set[str] = set()
        athletes: set[str] = set()
        for o in observations:
            key = o["observation_key"]
            spec = expected["observations"].get(str(o["request_season"]))
            capture = expected["captures"].get(o["capture_id"])
            if spec is None or capture is None or spec["capture_id"] != o["capture_id"] or \
                    (o["source_id"], o["dataset"], o["capture_sha256"], o["receipt_sha256"]) != \
                    (SOURCE_ID, RECRUIT_DATASET, capture["response_sha256"], capture["receipt_sha256"]) or \
                    not 0 <= o["raw_row_ordinal"] < spec["rows"]:
                _refuse("RECRUITING_CAPTURE_BINDING_INVALID", f"{key}: the capture, request season or ordinal is not "
                                                              "the pinned capture's")
            if key != observation_key(o["capture_id"], o["raw_row_ordinal"], o["source_recruit_id"]):
                _refuse("RECRUITING_OBSERVATION_KEY_MISMATCH", f"{key}: the key is not SRC-002|capture|ordinal|recruit")
            if not RECRUIT_ID_RE.match(o["source_recruit_id"]) or \
                    (o["source_athlete_id"] is not None and not ATHLETE_ID_RE.match(o["source_athlete_id"])) or \
                    not SHA_RE.match(o["raw_row_sha256"]):
                _refuse("RECRUITING_SOURCE_ID_INVALID", f"{key}: a source ID or the raw row digest is malformed")
            if o["source_recruit_id"] in recruits or (o["source_athlete_id"] is not None and
                                                      o["source_athlete_id"] in athletes):
                _refuse("RECRUITING_DUPLICATE_SOURCE_ID", f"{key}: a source recruit or athlete ID repeats")
            recruits.add(o["source_recruit_id"])
            if o["source_athlete_id"] is not None:
                athletes.add(o["source_athlete_id"])
            kinds = o["source_field_kinds"]
            members = o["raw_member_names"]
            absent = [name for name in SERVED_FIELDS if kinds[name] == "absent"]
            consistent = (members == sorted(set(members)) and o["absent_served_fields"] == sorted(absent) and
                          not set(absent) & set(members) and
                          set(SERVED_FIELDS) - set(absent) <= set(members))
            for name in SERVED_FIELDS:
                kind, value = kinds[name], o[FIELD_NAMES[name]]
                if kind not in RAW_KINDS[name]:
                    consistent = False
                elif kind in ("absent", "null"):
                    consistent = consistent and value is None
                else:
                    consistent = consistent and json_kind(value) == kind
            if not consistent:
                _refuse("RECRUITING_OBSERVATION_KIND_MISMATCH", f"{key}: a served value differs from its recorded "
                                                                "JSON kind or member presence")

    def _verify_qualifications(self, records: dict[str, list[dict[str, Any]]], lines: dict[str, list[str]]) -> None:
        captures = self.anchors["expected"]["captures"]
        sources = {s["source_key"]: s for s in records["sources"]}
        for observation, line, q in zip(records["observations"], lines["observations"], records["qualifications"]):
            key = q["qualification_key"]
            if (q["qualification_key"], q["observation_key"]) != (observation["observation_key"],) * 2 or \
                    q["observation_record_sha256"] != sha256_bytes(line.encode("utf-8")):
                _refuse("RECRUITING_QUALIFICATION_BINDING_INVALID", f"{key}: the qualification does not bind its "
                                                                    "observation record")
            for name in TIME_FIELDS:
                if q[name] is not None:
                    _refuse("RECRUITING_TIME_CLAIM_INVALID", f"{key}: {name} claims a historical time")
            if q["pit_eligible"] is not False:
                _refuse("RECRUITING_PIT_CLAIM_INVALID", f"{key}: pit_eligible is {q['pit_eligible']!r}")
            aliases, teams = [], []
            for view in q["alias_witnesses"]:
                row = sources.get(view["source_key"])
                if row is None or row["witness_kind"] != "CORE_TEAM_ALIAS_ROW":
                    _refuse("RECRUITING_SOURCE_CLOSURE_INVALID", f"{key}: alias witness {view['source_key']} has no "
                                                                 "core-row source witness")
                _core_witness_shape(row)
                aliases.append(alias_view(row["source_key"], row["registry_row"], row["row"]))
            for view in q["team_witnesses"]:
                row = sources.get(view["source_key"])
                if row is None or row["witness_kind"] != "CORE_TEAM_ENTITY_ROW":
                    _refuse("RECRUITING_SOURCE_CLOSURE_INVALID", f"{key}: team witness {view['source_key']} has no "
                                                                 "core-row source witness")
                _core_witness_shape(row)
                teams.append(team_view(row["source_key"], row["registry_row"], row["row"]))
            label = observation["committed_to"]
            for alias in aliases:
                if alias["alias"] != label:
                    _refuse("RECRUITING_PROGRAM_CORRESPONDENCE_INVALID", f"{key}: alias witness {alias['record_id']} "
                                                                         "is not an exact full-string label witness")
            candidates = {alias["canonical_id"] for alias in aliases}
            if teams and (len(candidates) != 1 or any(t["canonical_id"] not in candidates for t in teams)):
                _refuse("RECRUITING_PROGRAM_CORRESPONDENCE_INVALID", f"{key}: a team witness is not the entity of the "
                                                                     "single exact-alias candidate")
            _namespace, identity, entity = identity_key_for(observation["source_athlete_id"],
                                                            observation["source_recruit_id"])
            if any(w["identity_key"] != identity or w["record_type"] != "PERSON" for w in q["person_witnesses"]) or \
                    any((w["source_system_id"], w["source_entity_key"], w["record_type"]) !=
                        (SOURCE_ID, entity, "SOURCE_MAPPING") for w in q["mapping_witnesses"]):
                _refuse("RECRUITING_PERSON_CORRESPONDENCE_INVALID", f"{key}: a person or mapping witness is not an "
                                                                    "exact identity-key or entity-key selection")
            legacy_id = legacy_record_id(observation["capture_id"], observation["source_recruit_id"])
            if any(w["record_id"] != legacy_id or w["record_type"] != "RECRUITING_OBSERVATION"
                   for w in q["legacy_observation_witnesses"]):
                _refuse("RECRUITING_LEGACY_WITNESS_MISMATCH", f"{key}: a legacy witness is not this observation's "
                                                              "legacy record")
            want = qualification_record(observation, line, captures[observation["capture_id"]], q["person_witnesses"],
                                        q["mapping_witnesses"], q["legacy_observation_witnesses"], aliases, teams)
            if canonical_json_bytes(want) == canonical_json_bytes(q):
                continue
            differing = {k for k in want if canonical_json_bytes(q.get(k)) != canonical_json_bytes(want[k])}
            for code, fields in _FIELD_GROUP_CODES:
                if differing & set(fields):
                    _refuse(code, f"{key}: differs from its re-derivation on {sorted(differing & set(fields))}")
            _refuse("RECRUITING_QUALIFICATION_MISMATCH", f"{key}: differs from its re-derivation on {sorted(differing)}")

    def _verify_partitions(self, records: dict[str, list[dict[str, Any]]]) -> None:
        counts: dict[str, int] = {}
        for o in records["observations"]:
            counts[o["capture_id"]] = counts.get(o["capture_id"], 0) + 1
        for stored, want in zip(records["partitions"], partition_records(self.anchors["expected"], counts)):
            if canonical_json_bytes(stored) != canonical_json_bytes(want):
                differing = sorted(k for k in want if canonical_json_bytes(stored.get(k)) !=
                                   canonical_json_bytes(want[k]))
                _refuse("RECRUITING_PARTITION_MISMATCH", f"{stored['partition_key']}: differs from the pinned cell on "
                                                         f"{differing[:6]}")

    def _verify_sources(self, records: dict[str, list[dict[str, Any]]]) -> None:
        files = file_source_records(self.anchors)
        for stored, want in zip(records["sources"], files):
            if canonical_json_bytes(stored) != canonical_json_bytes(want):
                differing = sorted(k for k in want if canonical_json_bytes(stored.get(k)) !=
                                   canonical_json_bytes(want[k]))
                _refuse("RECRUITING_SOURCE_MISMATCH", f"{stored['source_key']}: differs from the pinned input on "
                                                      f"{differing[:6]}")
        registry_sha = self.anchors["inputs"]["core_registry"]["sha256"]
        referenced: dict[str, str] = {}
        for q in records["qualifications"]:
            for view in q["alias_witnesses"]:
                referenced[view["source_key"]] = "CORE_TEAM_ALIAS_ROW"
            for view in q["team_witnesses"]:
                referenced[view["source_key"]] = "CORE_TEAM_ENTITY_ROW"
        core = records["sources"][len(files):]
        for stored in core:
            _core_witness_shape(stored)
            want = core_source_record(stored["registry_row"], stored["row"], stored["witness_kind"], registry_sha)
            if canonical_json_bytes(stored) != canonical_json_bytes(want):
                differing = sorted(k for k in want if canonical_json_bytes(stored.get(k)) !=
                                   canonical_json_bytes(want[k]))
                _refuse("RECRUITING_SOURCE_MISMATCH", f"{stored['source_key']}: differs from its row's own identity "
                                                      f"and hashes on {differing[:6]}")
        present = {s["source_key"]: s["witness_kind"] for s in core}
        if present != referenced:
            _refuse("RECRUITING_SOURCE_CLOSURE_INVALID", "the core-row witnesses are not exactly the rows the "
                                                         "qualifications reference")

    @staticmethod
    def _verify_summary_and_census(records: dict[str, list[dict[str, Any]]]) -> None:
        want = summary_rows(records["observations"], records["qualifications"])
        for stored, rebuilt in zip(records["summary"], want):
            if canonical_json_bytes(stored) != canonical_json_bytes(rebuilt):
                _refuse("RECRUITING_SUMMARY_MISMATCH", f"{stored['summary_key']}: differs from the re-derived counts")
        if canonical_json_bytes(records["census"][0]) != canonical_json_bytes(census_record(records)):
            _refuse("RECRUITING_CENSUS_MISMATCH", "the census differs from the re-derived population")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "RecruitingEvidence":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- serving
    filters = staticmethod(validate_selection)

    def source_time(self) -> dict[str, Any]:
        captures = self.anchors["expected"]["captures"]
        return {"capture_clocks": {cid: {"capture_known_at_utc": c["capture_known_at_utc"],
                                         "retrieved_at_utc": c["retrieved_at_utc"],
                                         "provider_http_date": c["provider_http_date"]}
                                   for cid, c in sorted(captures.items())},
                "clock_kind": "RETAINED_CAPTURE_RECEIPT_RETRIEVAL_2026_08_10_NOT_HISTORICAL_KNOWN_AT",
                "historical_times": "UNKNOWN_NULL_FOR_EVERY_OBSERVATION", "pit_admitted": False,
                "contract_frozen_at_utc": self.anchors["frozen_at_utc"],
                "release_provenance_issued_at_utc": (self.binding.get("provenance") or {}).get("issued_at_utc")
                if isinstance(self.binding.get("provenance"), dict) else None,
                "release_provenance_note": "the run manifest's provenance build clock; not identity-bound"}

    def _selected(self, filters: dict[str, Any]) -> list[int]:
        out = []
        quals = self.records["qualifications"]
        for index, o in enumerate(self.records["observations"]):
            q = quals[index]
            if "season" in filters and o["request_season"] != filters["season"]:
                continue
            if "recruit" in filters and o["source_recruit_id"] != filters["recruit"]:
                continue
            if "player" in filters and q["canonical_player_id"] != filters["player"]:
                continue
            if "team" in filters and q["canonical_team_id"] != filters["team"]:
                continue
            out.append(index)
        return out

    def query(self, grain: str, *, season: Any = None, team: Any = None, player: Any = None, recruit: Any = None,
              limit: Any = 50, offset: Any = 0, all_rows: bool = False, limit_given: bool = False,
              offset_given: bool = False) -> dict[str, Any]:
        filters = validate_selection(grain, season=season, team=team, player=player, recruit=recruit)
        page_limit, page_offset = validate_paging(limit, offset, all_rows, limit_given=limit_given,
                                                  offset_given=offset_given)
        table = GRAINS[grain]
        result: dict[str, Any] = {
            "release_identity": self.database_identity, "content_identity": self.content_identity,
            "contract_id": self.anchors["contract_id"], "contract_sha256": self.anchors["contract_sha256"],
            "population": POPULATION, "grain": grain, "filters": filters, "offset": page_offset,
            "limit": page_limit, **LABELS, "source_time": self.source_time(), "denominators": self.census,
            "verification": {**{f"{t}_verified": len(self.records[t]) for t in RECORD_TABLES},
                             "records_verified": True, "qualifications_rederived": True,
                             "content_identity_rebuilt": True, "database_document_rebuilt": True,
                             "profile_pinned": self.anchors.get("profile") is not None}}
        if table in SEASONAL_TABLES or table == "summary":
            chosen = self._selected(filters)
            if table == "summary":
                obs = [self.records["observations"][i] for i in chosen]
                quals = [self.records["qualifications"][i] for i in chosen]
                rows = summary_rows(obs, quals) if filters else list(self.records["summary"])
                result["selected_observations"] = len(chosen)
            else:
                rows = [self.records[table][i] for i in chosen]
        elif table == "partitions":
            rows = [p for p in self.records["partitions"] if "season" not in filters or p["season"] == filters["season"]]
        else:
            rows = list(self.records[table])
        served, next_offset = page(rows, page_limit, page_offset)
        result.update(total=len(rows), returned=len(served), rows=served, next_offset=next_offset)
        return result


# ---- BEGIN GENERATED ANCHORS (tools/cycle64/make_recruiting_contract.py; never hand edited) ----
#: The pinned authority of the reader: the committed contract SHA-256, every pinned input (locator, relative path,
#: SHA-256, bytes) and the source key universe (requested cells, captures, per-season observation counts and key
#: digests) generated from the original sources before any qualification; never hand edited.
ANCHORS: dict[str, Any] = json.loads(r'''{
 "contract_id": "BAT-735-NATIONAL-RECRUITING-EVIDENCE-2010-2017-V1.0",
 "contract_sha256": "ee81ba6cf824d73ade7af3f3a3f831abd2ae5086f7890230b22a442544998d99",
 "expected": {
  "captures": {
   "cap_08ab140a68fa01a7f7168376": {
    "capture_id": "cap_08ab140a68fa01a7f7168376",
    "capture_known_at_utc": "2026-08-10T01:48:07Z",
    "dataset": "transfer_portal",
    "endpoint_id": "CFBD-GetTransferPortal",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/transfer_portal/2012/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
    "parameters": {
     "year": 2012
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:07 GMT",
    "receipt_bytes": 1610,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_08ab140a68fa01a7f7168376.json",
    "receipt_sha256": "1a4a0a4e89ae77d54104ed6bb1e0160047d865cb60c20fbad0c9bf660ce6cbe9",
    "response_bytes": 2,
    "response_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:07Z",
    "row_count": 0,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/player/portal?year=2012",
    "top_level_schema_fields": [],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_126c16a995cacf21b48d69ab": {
    "capture_id": "cap_126c16a995cacf21b48d69ab",
    "capture_known_at_utc": "2026-08-10T01:48:07Z",
    "dataset": "recruiting_players",
    "endpoint_id": "CFBD-GetRecruitingPlayers",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/recruiting_players/2010/sha256_9815ff35dd2d50faa2aa521e7cc57ce087497da9474ea9709bff76dfa428edce.json",
    "parameters": {
     "year": 2010
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:07 GMT",
    "receipt_bytes": 1905,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_126c16a995cacf21b48d69ab.json",
    "receipt_sha256": "f843f77f42a17d872f93ce9f720d060cad938c18eab0e3931025b47186d779a2",
    "response_bytes": 896684,
    "response_sha256": "9815ff35dd2d50faa2aa521e7cc57ce087497da9474ea9709bff76dfa428edce",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:07Z",
    "row_count": 2445,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/recruiting/players?year=2010",
    "top_level_schema_fields": [
     "athleteId",
     "city",
     "committedTo",
     "country",
     "height",
     "hometownInfo",
     "id",
     "name",
     "position",
     "ranking",
     "rating",
     "recruitType",
     "school",
     "stars",
     "stateProvince",
     "weight",
     "year"
    ],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_1442929482cbbc5acf9c0ee1": {
    "capture_id": "cap_1442929482cbbc5acf9c0ee1",
    "capture_known_at_utc": "2026-08-10T01:48:07Z",
    "dataset": "recruiting_players",
    "endpoint_id": "CFBD-GetRecruitingPlayers",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/recruiting_players/2012/sha256_a86fc2acf03f44cdff309ae48734d469fadee369f2c8b25ac330a4dc133394a3.json",
    "parameters": {
     "year": 2012
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:07 GMT",
    "receipt_bytes": 1908,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_1442929482cbbc5acf9c0ee1.json",
    "receipt_sha256": "66b2a2ec6edceb185915dc36afb77552a322272de47c35ee65b971dc8a79a75b",
    "response_bytes": 1129678,
    "response_sha256": "a86fc2acf03f44cdff309ae48734d469fadee369f2c8b25ac330a4dc133394a3",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:07Z",
    "row_count": 3086,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/recruiting/players?year=2012",
    "top_level_schema_fields": [
     "athleteId",
     "city",
     "committedTo",
     "country",
     "height",
     "hometownInfo",
     "id",
     "name",
     "position",
     "ranking",
     "rating",
     "recruitType",
     "school",
     "stars",
     "stateProvince",
     "weight",
     "year"
    ],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_21f95171e4119ae863098273": {
    "capture_id": "cap_21f95171e4119ae863098273",
    "capture_known_at_utc": "2026-08-10T01:48:08Z",
    "dataset": "recruiting_players",
    "endpoint_id": "CFBD-GetRecruitingPlayers",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/recruiting_players/2015/sha256_f708f8529c8743c399fd18393186668bcca8c60b65c49a1dbad642431d388ac7.json",
    "parameters": {
     "year": 2015
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:08 GMT",
    "receipt_bytes": 1908,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_21f95171e4119ae863098273.json",
    "receipt_sha256": "d1c15c62b93967127132fca328006a0526e22a62760651b04d683aab468ba2d5",
    "response_bytes": 1282318,
    "response_sha256": "f708f8529c8743c399fd18393186668bcca8c60b65c49a1dbad642431d388ac7",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:08Z",
    "row_count": 3516,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/recruiting/players?year=2015",
    "top_level_schema_fields": [
     "athleteId",
     "city",
     "committedTo",
     "country",
     "height",
     "hometownInfo",
     "id",
     "name",
     "position",
     "ranking",
     "rating",
     "recruitType",
     "school",
     "stars",
     "stateProvince",
     "weight",
     "year"
    ],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_3d1d412cea46422d65df5410": {
    "capture_id": "cap_3d1d412cea46422d65df5410",
    "capture_known_at_utc": "2026-08-10T01:48:07Z",
    "dataset": "transfer_portal",
    "endpoint_id": "CFBD-GetTransferPortal",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/transfer_portal/2013/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
    "parameters": {
     "year": 2013
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:07 GMT",
    "receipt_bytes": 1610,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_3d1d412cea46422d65df5410.json",
    "receipt_sha256": "d1c7f5622124f17b92a691ce8def6e2540c86573663547cd87884f831e8c49a2",
    "response_bytes": 2,
    "response_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:07Z",
    "row_count": 0,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/player/portal?year=2013",
    "top_level_schema_fields": [],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_5b1944b11cc20a36c617ba07": {
    "capture_id": "cap_5b1944b11cc20a36c617ba07",
    "capture_known_at_utc": "2026-08-10T01:48:07Z",
    "dataset": "recruiting_players",
    "endpoint_id": "CFBD-GetRecruitingPlayers",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/recruiting_players/2011/sha256_6c0f2498d2e9f3df7fd8415f3e773ac0e56df14918acf8a6ab455798fbdfa6da.json",
    "parameters": {
     "year": 2011
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:07 GMT",
    "receipt_bytes": 1905,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_5b1944b11cc20a36c617ba07.json",
    "receipt_sha256": "bfea2d33706696cea1ee82e1d82292a00af68cf173e6a0bd5aafa7cf074a478c",
    "response_bytes": 981445,
    "response_sha256": "6c0f2498d2e9f3df7fd8415f3e773ac0e56df14918acf8a6ab455798fbdfa6da",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:07Z",
    "row_count": 2682,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/recruiting/players?year=2011",
    "top_level_schema_fields": [
     "athleteId",
     "city",
     "committedTo",
     "country",
     "height",
     "hometownInfo",
     "id",
     "name",
     "position",
     "ranking",
     "rating",
     "recruitType",
     "school",
     "stars",
     "stateProvince",
     "weight",
     "year"
    ],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_74c32a321fa77d51e0c7d7b6": {
    "capture_id": "cap_74c32a321fa77d51e0c7d7b6",
    "capture_known_at_utc": "2026-08-10T01:48:08Z",
    "dataset": "transfer_portal",
    "endpoint_id": "CFBD-GetTransferPortal",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/transfer_portal/2016/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
    "parameters": {
     "year": 2016
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:08 GMT",
    "receipt_bytes": 1610,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_74c32a321fa77d51e0c7d7b6.json",
    "receipt_sha256": "08fde4d20469b62c56060f75070815c0ecb3b55dd70ef9b56af3fab0abdf2985",
    "response_bytes": 2,
    "response_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:08Z",
    "row_count": 0,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/player/portal?year=2016",
    "top_level_schema_fields": [],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_883e831cb17e35a57a517203": {
    "capture_id": "cap_883e831cb17e35a57a517203",
    "capture_known_at_utc": "2026-08-10T01:48:08Z",
    "dataset": "transfer_portal",
    "endpoint_id": "CFBD-GetTransferPortal",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/transfer_portal/2015/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
    "parameters": {
     "year": 2015
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:08 GMT",
    "receipt_bytes": 1610,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_883e831cb17e35a57a517203.json",
    "receipt_sha256": "91fd7597372a8abeb6d5ee71b6a760760615a959fada19a2e6a5b05bff4661b2",
    "response_bytes": 2,
    "response_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:08Z",
    "row_count": 0,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/player/portal?year=2015",
    "top_level_schema_fields": [],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_8b69c09f46749cbf0c410a59": {
    "capture_id": "cap_8b69c09f46749cbf0c410a59",
    "capture_known_at_utc": "2026-08-10T01:48:08Z",
    "dataset": "recruiting_players",
    "endpoint_id": "CFBD-GetRecruitingPlayers",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/recruiting_players/2014/sha256_21c06d18038f3baf1c1f67123af4c66b293bb8df02ed4dba50b8d24aed791f68.json",
    "parameters": {
     "year": 2014
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:08 GMT",
    "receipt_bytes": 1908,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_8b69c09f46749cbf0c410a59.json",
    "receipt_sha256": "04ff13e92599392600b4b26a008ae9517dfab46f73794ed9fc57eccf47d31806",
    "response_bytes": 1376497,
    "response_sha256": "21c06d18038f3baf1c1f67123af4c66b293bb8df02ed4dba50b8d24aed791f68",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:08Z",
    "row_count": 3772,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/recruiting/players?year=2014",
    "top_level_schema_fields": [
     "athleteId",
     "city",
     "committedTo",
     "country",
     "height",
     "hometownInfo",
     "id",
     "name",
     "position",
     "ranking",
     "rating",
     "recruitType",
     "school",
     "stars",
     "stateProvince",
     "weight",
     "year"
    ],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_95ef7dd6da73a3638f303af7": {
    "capture_id": "cap_95ef7dd6da73a3638f303af7",
    "capture_known_at_utc": "2026-08-10T01:48:07Z",
    "dataset": "transfer_portal",
    "endpoint_id": "CFBD-GetTransferPortal",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/transfer_portal/2010/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
    "parameters": {
     "year": 2010
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:07 GMT",
    "receipt_bytes": 1610,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_95ef7dd6da73a3638f303af7.json",
    "receipt_sha256": "ca669a76fb4c740dda01e2436898c7650efe16e1c1e5aff3521b2e431ce541e0",
    "response_bytes": 2,
    "response_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:07Z",
    "row_count": 0,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/player/portal?year=2010",
    "top_level_schema_fields": [],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_96b7e887aa16ce54914bca71": {
    "capture_id": "cap_96b7e887aa16ce54914bca71",
    "capture_known_at_utc": "2026-08-10T01:48:07Z",
    "dataset": "transfer_portal",
    "endpoint_id": "CFBD-GetTransferPortal",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/transfer_portal/2014/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
    "parameters": {
     "year": 2014
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:07 GMT",
    "receipt_bytes": 1610,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_96b7e887aa16ce54914bca71.json",
    "receipt_sha256": "65883523131177f53248be448e881713a5d21aea9578fd63152947f7d69f3f6f",
    "response_bytes": 2,
    "response_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:07Z",
    "row_count": 0,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/player/portal?year=2014",
    "top_level_schema_fields": [],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_9959459628d2527d3ab4fdaf": {
    "capture_id": "cap_9959459628d2527d3ab4fdaf",
    "capture_known_at_utc": "2026-08-10T01:48:08Z",
    "dataset": "recruiting_players",
    "endpoint_id": "CFBD-GetRecruitingPlayers",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/recruiting_players/2016/sha256_d126650ce35a886ce6e9d27196ae9699131d741f6e0475a57a0c306b55bb70ac.json",
    "parameters": {
     "year": 2016
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:08 GMT",
    "receipt_bytes": 1908,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_9959459628d2527d3ab4fdaf.json",
    "receipt_sha256": "8677a4f36ec5e31b2a0f41c80d2923814f785ea7fb92dda84d785df969cfc9da",
    "response_bytes": 1632499,
    "response_sha256": "d126650ce35a886ce6e9d27196ae9699131d741f6e0475a57a0c306b55bb70ac",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:08Z",
    "row_count": 4452,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/recruiting/players?year=2016",
    "top_level_schema_fields": [
     "athleteId",
     "city",
     "committedTo",
     "country",
     "height",
     "hometownInfo",
     "id",
     "name",
     "position",
     "ranking",
     "rating",
     "recruitType",
     "school",
     "stars",
     "stateProvince",
     "weight",
     "year"
    ],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_a3226eb4157c8aa293f77f01": {
    "capture_id": "cap_a3226eb4157c8aa293f77f01",
    "capture_known_at_utc": "2026-08-10T01:48:08Z",
    "dataset": "recruiting_players",
    "endpoint_id": "CFBD-GetRecruitingPlayers",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/recruiting_players/2017/sha256_e8347d6bc067cbcd9e9ec78b18f1d6974204e21fd1420dcf666e2591914c221c.json",
    "parameters": {
     "year": 2017
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:08 GMT",
    "receipt_bytes": 1908,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_a3226eb4157c8aa293f77f01.json",
    "receipt_sha256": "11f13e8a8a27624d647a37df45e355355d093140958fbbaf79f431a9b742bb8b",
    "response_bytes": 1725700,
    "response_sha256": "e8347d6bc067cbcd9e9ec78b18f1d6974204e21fd1420dcf666e2591914c221c",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:08Z",
    "row_count": 4710,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/recruiting/players?year=2017",
    "top_level_schema_fields": [
     "athleteId",
     "city",
     "committedTo",
     "country",
     "height",
     "hometownInfo",
     "id",
     "name",
     "position",
     "ranking",
     "rating",
     "recruitType",
     "school",
     "stars",
     "stateProvince",
     "weight",
     "year"
    ],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_bf49415cdad986ee67ce2f4c": {
    "capture_id": "cap_bf49415cdad986ee67ce2f4c",
    "capture_known_at_utc": "2026-08-10T01:48:08Z",
    "dataset": "recruiting_players",
    "endpoint_id": "CFBD-GetRecruitingPlayers",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/recruiting_players/2013/sha256_ca91d4dd6ba17945c728c3d937bb4b71f43345f8d8889fa695b4ff5c3db84972.json",
    "parameters": {
     "year": 2013
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:07 GMT",
    "receipt_bytes": 1908,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_bf49415cdad986ee67ce2f4c.json",
    "receipt_sha256": "3d7b09b9a752294cada8b5c338359867a47a6011c9d2dca3561038b73706ddab",
    "response_bytes": 1251572,
    "response_sha256": "ca91d4dd6ba17945c728c3d937bb4b71f43345f8d8889fa695b4ff5c3db84972",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:08Z",
    "row_count": 3430,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/recruiting/players?year=2013",
    "top_level_schema_fields": [
     "athleteId",
     "city",
     "committedTo",
     "country",
     "height",
     "hometownInfo",
     "id",
     "name",
     "position",
     "ranking",
     "rating",
     "recruitType",
     "school",
     "stars",
     "stateProvince",
     "weight",
     "year"
    ],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   },
   "cap_fa9bb1e9b5fdf06566e75814": {
    "capture_id": "cap_fa9bb1e9b5fdf06566e75814",
    "capture_known_at_utc": "2026-08-10T01:48:07Z",
    "dataset": "transfer_portal",
    "endpoint_id": "CFBD-GetTransferPortal",
    "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION",
    "http_status": 200,
    "immutable_path": "raw/SRC-002/bat388-people/transfer_portal/2011/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
    "parameters": {
     "year": 2011
    },
    "provider_http_date": "Mon, 10 Aug 2026 01:48:07 GMT",
    "receipt_bytes": 1610,
    "receipt_relative_path": "manifests/captures/SRC-002/cap_fa9bb1e9b5fdf06566e75814.json",
    "receipt_sha256": "69b3567939fce3b98aa508a0f48b480d985dbfd812db6f7f60974b682355f9a1",
    "response_bytes": 2,
    "response_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "result": "SUCCESS",
    "retrieved_at_utc": "2026-08-10T01:48:07Z",
    "row_count": 0,
    "run_id": "bat388-people-sources-v1",
    "source_id": "SRC-002",
    "source_uri": "https://api.collegefootballdata.com/player/portal?year=2011",
    "top_level_schema_fields": [],
    "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"
   }
  },
  "cells": [
   {
    "capture_id": "cap_126c16a995cacf21b48d69ab",
    "cell_key": "recruiting_players|year=2010",
    "dataset": "recruiting_players",
    "missing_reason": null,
    "parameters": {
     "year": 2010
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_5b1944b11cc20a36c617ba07",
    "cell_key": "recruiting_players|year=2011",
    "dataset": "recruiting_players",
    "missing_reason": null,
    "parameters": {
     "year": 2011
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_1442929482cbbc5acf9c0ee1",
    "cell_key": "recruiting_players|year=2012",
    "dataset": "recruiting_players",
    "missing_reason": null,
    "parameters": {
     "year": 2012
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_bf49415cdad986ee67ce2f4c",
    "cell_key": "recruiting_players|year=2013",
    "dataset": "recruiting_players",
    "missing_reason": null,
    "parameters": {
     "year": 2013
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_8b69c09f46749cbf0c410a59",
    "cell_key": "recruiting_players|year=2014",
    "dataset": "recruiting_players",
    "missing_reason": null,
    "parameters": {
     "year": 2014
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_21f95171e4119ae863098273",
    "cell_key": "recruiting_players|year=2015",
    "dataset": "recruiting_players",
    "missing_reason": null,
    "parameters": {
     "year": 2015
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_9959459628d2527d3ab4fdaf",
    "cell_key": "recruiting_players|year=2016",
    "dataset": "recruiting_players",
    "missing_reason": null,
    "parameters": {
     "year": 2016
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_a3226eb4157c8aa293f77f01",
    "cell_key": "recruiting_players|year=2017",
    "dataset": "recruiting_players",
    "missing_reason": null,
    "parameters": {
     "year": 2017
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "recruiting_players|year=2018",
    "dataset": "recruiting_players",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2018
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "recruiting_players|year=2019",
    "dataset": "recruiting_players",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2019
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "recruiting_players|year=2020",
    "dataset": "recruiting_players",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2020
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "recruiting_players|year=2021",
    "dataset": "recruiting_players",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2021
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "recruiting_players|year=2022",
    "dataset": "recruiting_players",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2022
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "recruiting_players|year=2023",
    "dataset": "recruiting_players",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2023
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "recruiting_players|year=2024",
    "dataset": "recruiting_players",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2024
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "recruiting_players|year=2025",
    "dataset": "recruiting_players",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2025
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": "cap_95ef7dd6da73a3638f303af7",
    "cell_key": "transfer_portal|year=2010",
    "dataset": "transfer_portal",
    "missing_reason": null,
    "parameters": {
     "year": 2010
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_fa9bb1e9b5fdf06566e75814",
    "cell_key": "transfer_portal|year=2011",
    "dataset": "transfer_portal",
    "missing_reason": null,
    "parameters": {
     "year": 2011
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_08ab140a68fa01a7f7168376",
    "cell_key": "transfer_portal|year=2012",
    "dataset": "transfer_portal",
    "missing_reason": null,
    "parameters": {
     "year": 2012
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_3d1d412cea46422d65df5410",
    "cell_key": "transfer_portal|year=2013",
    "dataset": "transfer_portal",
    "missing_reason": null,
    "parameters": {
     "year": 2013
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_96b7e887aa16ce54914bca71",
    "cell_key": "transfer_portal|year=2014",
    "dataset": "transfer_portal",
    "missing_reason": null,
    "parameters": {
     "year": 2014
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_883e831cb17e35a57a517203",
    "cell_key": "transfer_portal|year=2015",
    "dataset": "transfer_portal",
    "missing_reason": null,
    "parameters": {
     "year": 2015
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": "cap_74c32a321fa77d51e0c7d7b6",
    "cell_key": "transfer_portal|year=2016",
    "dataset": "transfer_portal",
    "missing_reason": null,
    "parameters": {
     "year": 2016
    },
    "state": "CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "transfer_portal|year=2017",
    "dataset": "transfer_portal",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2017
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "transfer_portal|year=2018",
    "dataset": "transfer_portal",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2018
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "transfer_portal|year=2019",
    "dataset": "transfer_portal",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2019
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "transfer_portal|year=2020",
    "dataset": "transfer_portal",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2020
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "transfer_portal|year=2021",
    "dataset": "transfer_portal",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2021
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "transfer_portal|year=2022",
    "dataset": "transfer_portal",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2022
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "transfer_portal|year=2023",
    "dataset": "transfer_portal",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2023
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "transfer_portal|year=2024",
    "dataset": "transfer_portal",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2024
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "transfer_portal|year=2025",
    "dataset": "transfer_portal",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "year": 2025
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "coaches|maxYear=2025,minYear=2010",
    "dataset": "coaches",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "maxYear": 2025,
     "minYear": 2010
    },
    "state": "NOT_CAPTURED"
   },
   {
    "capture_id": null,
    "cell_key": "coach_seasons|maxYear=2025,minYear=2010",
    "dataset": "coach_seasons",
    "missing_reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED",
    "parameters": {
     "maxYear": 2025,
     "minYear": 2010
    },
    "state": "NOT_CAPTURED"
   }
  ],
  "counts": {
   "captured_cells": 15,
   "not_captured_cells": 19,
   "observations": 28093,
   "requested_cells": 34
  },
  "national_expected_universe": "NOT_ESTABLISHED",
  "observations": {
   "2010": {
    "capture_id": "cap_126c16a995cacf21b48d69ab",
    "keys_sha256": "a2c669942403069cc0ca5de43efdf530880fe9e390f04818be1b3849a8008888",
    "rows": 2445
   },
   "2011": {
    "capture_id": "cap_5b1944b11cc20a36c617ba07",
    "keys_sha256": "30b64fefed92197c1eea67bf2577fe8fe171e3308c1d6a2854db8f4154d4e7cc",
    "rows": 2682
   },
   "2012": {
    "capture_id": "cap_1442929482cbbc5acf9c0ee1",
    "keys_sha256": "a7277679e87fab4075cda73da18b28a4d8ca540411188e68476185fc82d44794",
    "rows": 3086
   },
   "2013": {
    "capture_id": "cap_bf49415cdad986ee67ce2f4c",
    "keys_sha256": "4ba374b785422e6c921532f48f8d2fb1fdbb4922bddddb57bc9fc01396f5eb8d",
    "rows": 3430
   },
   "2014": {
    "capture_id": "cap_8b69c09f46749cbf0c410a59",
    "keys_sha256": "dc592ad4735fd2f2eff44187fd89035241a44802f08e09e4d0b1be772fb75a02",
    "rows": 3772
   },
   "2015": {
    "capture_id": "cap_21f95171e4119ae863098273",
    "keys_sha256": "4dc0aeede751b3db65dbc82d2353b9e450e884599f9255691ccde512a1d5e645",
    "rows": 3516
   },
   "2016": {
    "capture_id": "cap_9959459628d2527d3ab4fdaf",
    "keys_sha256": "5214723274af585bdf79f06c703496b4400a979bc232dbde929701e1cb457e7d",
    "rows": 4452
   },
   "2017": {
    "capture_id": "cap_a3226eb4157c8aa293f77f01",
    "keys_sha256": "8880a3223b089ff58a22b47f265ea85e2d58844728dfdfe8d879bfbdcefa4904",
    "rows": 4710
   }
  }
 },
 "frozen_at_utc": "2026-10-23T04:04:39Z",
 "inputs": {
  "acquisition_manifest": {
   "bytes": 35106,
   "locator": "DATA_ROOT",
   "relative_path": "manifests/acquisition/bat388-people-sources-v1/people_source_acquisition_manifest.json",
   "sha256": "fe2bfa3754fd29510a2f438f4f534b823871233a0bf0ac6c32202faad9a6cbee"
  },
  "core_manifest": {
   "bytes": 3069,
   "locator": "REPOSITORY",
   "relative_path": "artifacts/entities/canonical_core_registry_manifest.json",
   "sha256": "6293b25d58afb394d9fe37ded6da1e05aaf584302c582205d13603e9659ab6e7"
  },
  "core_registry": {
   "bytes": 42502985,
   "locator": "DATA_ROOT",
   "relative_path": "canonical/BAT-387/sha256/10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac/canonical_core_registry.csv",
   "sha256": "10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac"
  },
  "legacy_people_builder": {
   "bytes": 33275,
   "locator": "DATA_ROOT",
   "relative_path": "runtime/BAT-388/build_canonical_people_registry.py",
   "sha256": "d0c070f68b0deff129fd2674e83d00fd21e0e1409c90e0b91aedded94c418cd4"
  },
  "people_manifest": {
   "bytes": 3768,
   "locator": "REPOSITORY",
   "relative_path": "artifacts/entities/canonical_people_registry_manifest.json",
   "sha256": "2e03ea2c65c26e3eab7e14a3d5efb4a516faaa5f05942008c20af5599768df35"
  },
  "people_registry": {
   "bytes": 420562884,
   "locator": "DATA_ROOT",
   "relative_path": "canonical/BAT-388/sha256/0ab6acafbe350a4958a5fca1c02a9c51463ab8a93ecc173a57b9fd925bf2198d/canonical_people_registry.csv",
   "sha256": "0ab6acafbe350a4958a5fca1c02a9c51463ab8a93ecc173a57b9fd925bf2198d"
  },
  "portal_receipt:2010": {
   "bytes": 1610,
   "capture_id": "cap_95ef7dd6da73a3638f303af7",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_95ef7dd6da73a3638f303af7.json",
   "sha256": "ca669a76fb4c740dda01e2436898c7650efe16e1c1e5aff3521b2e431ce541e0"
  },
  "portal_receipt:2011": {
   "bytes": 1610,
   "capture_id": "cap_fa9bb1e9b5fdf06566e75814",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_fa9bb1e9b5fdf06566e75814.json",
   "sha256": "69b3567939fce3b98aa508a0f48b480d985dbfd812db6f7f60974b682355f9a1"
  },
  "portal_receipt:2012": {
   "bytes": 1610,
   "capture_id": "cap_08ab140a68fa01a7f7168376",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_08ab140a68fa01a7f7168376.json",
   "sha256": "1a4a0a4e89ae77d54104ed6bb1e0160047d865cb60c20fbad0c9bf660ce6cbe9"
  },
  "portal_receipt:2013": {
   "bytes": 1610,
   "capture_id": "cap_3d1d412cea46422d65df5410",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_3d1d412cea46422d65df5410.json",
   "sha256": "d1c7f5622124f17b92a691ce8def6e2540c86573663547cd87884f831e8c49a2"
  },
  "portal_receipt:2014": {
   "bytes": 1610,
   "capture_id": "cap_96b7e887aa16ce54914bca71",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_96b7e887aa16ce54914bca71.json",
   "sha256": "65883523131177f53248be448e881713a5d21aea9578fd63152947f7d69f3f6f"
  },
  "portal_receipt:2015": {
   "bytes": 1610,
   "capture_id": "cap_883e831cb17e35a57a517203",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_883e831cb17e35a57a517203.json",
   "sha256": "91fd7597372a8abeb6d5ee71b6a760760615a959fada19a2e6a5b05bff4661b2"
  },
  "portal_receipt:2016": {
   "bytes": 1610,
   "capture_id": "cap_74c32a321fa77d51e0c7d7b6",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_74c32a321fa77d51e0c7d7b6.json",
   "sha256": "08fde4d20469b62c56060f75070815c0ecb3b55dd70ef9b56af3fab0abdf2985"
  },
  "recruiting_players:2010": {
   "bytes": 896684,
   "capture_id": "cap_126c16a995cacf21b48d69ab",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/recruiting_players/2010/sha256_9815ff35dd2d50faa2aa521e7cc57ce087497da9474ea9709bff76dfa428edce.json",
   "rows": 2445,
   "sha256": "9815ff35dd2d50faa2aa521e7cc57ce087497da9474ea9709bff76dfa428edce"
  },
  "recruiting_players:2011": {
   "bytes": 981445,
   "capture_id": "cap_5b1944b11cc20a36c617ba07",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/recruiting_players/2011/sha256_6c0f2498d2e9f3df7fd8415f3e773ac0e56df14918acf8a6ab455798fbdfa6da.json",
   "rows": 2682,
   "sha256": "6c0f2498d2e9f3df7fd8415f3e773ac0e56df14918acf8a6ab455798fbdfa6da"
  },
  "recruiting_players:2012": {
   "bytes": 1129678,
   "capture_id": "cap_1442929482cbbc5acf9c0ee1",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/recruiting_players/2012/sha256_a86fc2acf03f44cdff309ae48734d469fadee369f2c8b25ac330a4dc133394a3.json",
   "rows": 3086,
   "sha256": "a86fc2acf03f44cdff309ae48734d469fadee369f2c8b25ac330a4dc133394a3"
  },
  "recruiting_players:2013": {
   "bytes": 1251572,
   "capture_id": "cap_bf49415cdad986ee67ce2f4c",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/recruiting_players/2013/sha256_ca91d4dd6ba17945c728c3d937bb4b71f43345f8d8889fa695b4ff5c3db84972.json",
   "rows": 3430,
   "sha256": "ca91d4dd6ba17945c728c3d937bb4b71f43345f8d8889fa695b4ff5c3db84972"
  },
  "recruiting_players:2014": {
   "bytes": 1376497,
   "capture_id": "cap_8b69c09f46749cbf0c410a59",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/recruiting_players/2014/sha256_21c06d18038f3baf1c1f67123af4c66b293bb8df02ed4dba50b8d24aed791f68.json",
   "rows": 3772,
   "sha256": "21c06d18038f3baf1c1f67123af4c66b293bb8df02ed4dba50b8d24aed791f68"
  },
  "recruiting_players:2015": {
   "bytes": 1282318,
   "capture_id": "cap_21f95171e4119ae863098273",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/recruiting_players/2015/sha256_f708f8529c8743c399fd18393186668bcca8c60b65c49a1dbad642431d388ac7.json",
   "rows": 3516,
   "sha256": "f708f8529c8743c399fd18393186668bcca8c60b65c49a1dbad642431d388ac7"
  },
  "recruiting_players:2016": {
   "bytes": 1632499,
   "capture_id": "cap_9959459628d2527d3ab4fdaf",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/recruiting_players/2016/sha256_d126650ce35a886ce6e9d27196ae9699131d741f6e0475a57a0c306b55bb70ac.json",
   "rows": 4452,
   "sha256": "d126650ce35a886ce6e9d27196ae9699131d741f6e0475a57a0c306b55bb70ac"
  },
  "recruiting_players:2017": {
   "bytes": 1725700,
   "capture_id": "cap_a3226eb4157c8aa293f77f01",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/recruiting_players/2017/sha256_e8347d6bc067cbcd9e9ec78b18f1d6974204e21fd1420dcf666e2591914c221c.json",
   "rows": 4710,
   "sha256": "e8347d6bc067cbcd9e9ec78b18f1d6974204e21fd1420dcf666e2591914c221c"
  },
  "recruiting_receipt:2010": {
   "bytes": 1905,
   "capture_id": "cap_126c16a995cacf21b48d69ab",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_126c16a995cacf21b48d69ab.json",
   "sha256": "f843f77f42a17d872f93ce9f720d060cad938c18eab0e3931025b47186d779a2"
  },
  "recruiting_receipt:2011": {
   "bytes": 1905,
   "capture_id": "cap_5b1944b11cc20a36c617ba07",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_5b1944b11cc20a36c617ba07.json",
   "sha256": "bfea2d33706696cea1ee82e1d82292a00af68cf173e6a0bd5aafa7cf074a478c"
  },
  "recruiting_receipt:2012": {
   "bytes": 1908,
   "capture_id": "cap_1442929482cbbc5acf9c0ee1",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_1442929482cbbc5acf9c0ee1.json",
   "sha256": "66b2a2ec6edceb185915dc36afb77552a322272de47c35ee65b971dc8a79a75b"
  },
  "recruiting_receipt:2013": {
   "bytes": 1908,
   "capture_id": "cap_bf49415cdad986ee67ce2f4c",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_bf49415cdad986ee67ce2f4c.json",
   "sha256": "3d7b09b9a752294cada8b5c338359867a47a6011c9d2dca3561038b73706ddab"
  },
  "recruiting_receipt:2014": {
   "bytes": 1908,
   "capture_id": "cap_8b69c09f46749cbf0c410a59",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_8b69c09f46749cbf0c410a59.json",
   "sha256": "04ff13e92599392600b4b26a008ae9517dfab46f73794ed9fc57eccf47d31806"
  },
  "recruiting_receipt:2015": {
   "bytes": 1908,
   "capture_id": "cap_21f95171e4119ae863098273",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_21f95171e4119ae863098273.json",
   "sha256": "d1c15c62b93967127132fca328006a0526e22a62760651b04d683aab468ba2d5"
  },
  "recruiting_receipt:2016": {
   "bytes": 1908,
   "capture_id": "cap_9959459628d2527d3ab4fdaf",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_9959459628d2527d3ab4fdaf.json",
   "sha256": "8677a4f36ec5e31b2a0f41c80d2923814f785ea7fb92dda84d785df969cfc9da"
  },
  "recruiting_receipt:2017": {
   "bytes": 1908,
   "capture_id": "cap_a3226eb4157c8aa293f77f01",
   "locator": "DATA_ROOT",
   "relative_path": "manifests/captures/SRC-002/cap_a3226eb4157c8aa293f77f01.json",
   "sha256": "11f13e8a8a27624d647a37df45e355355d093140958fbbaf79f431a9b742bb8b"
  },
  "rights_metadata": {
   "bytes": 38203,
   "decision": {
    "allowed_access": "PUBLIC_OR_OWNER_CREDENTIALED_FACTUAL_DATA_FOR_PRIVATE_RESEARCH",
    "attribution_decision": "PRESERVE_SOURCE_URL_TIMESTAMP_AND_PROVENANCE_METADATA",
    "dataset": "CollegeFootballData API",
    "decision_id": "PRIVATE-RESEARCH-SRC-002",
    "derived_use_decision": "ALLOW_PRIVATE_LOCAL_ANALYSIS_FEATURES_AND_MODELS",
    "local_storage_decision": "ALLOW_IMMUTABLE_RAW_AND_NORMALIZED_DATA_OUTSIDE_GIT",
    "owner_authorization_basis": "UNIVERSAL_PRIVATE_RESEARCH_ACQUISITION_2026-08-09",
    "policy_version": "UNIVERSAL_PRIVATE_RESEARCH_ACQUISITION_2026-08-09",
    "private_research_acquisition_allowed": "true",
    "provider": "Rad Sports Analytics / CollegeFootballData",
    "publication_decision": "SEPARATE_FUTURE_PUBLICATION_REVIEW_REQUIRED_NO_RAW_PAYLOAD_PUBLICATION",
    "redistribution_decision": "DO_NOT_PUBLISH_OR_REDISTRIBUTE_RAW_THIRD_PARTY_PAYLOADS",
    "retention_decision": "LOCAL_RETENTION_ALLOWED_UNDER_EXTERNAL_DATA_ROOT_AND_DISK_POLICY",
    "rights_decision": "METADATA_ONLY_NONBLOCKING",
    "rights_metadata_nonblocking": "true",
    "row_sha256": "bd9b842a178f494efec1bd89f93b3c07958a40ad7d077d197dfcdcef54cebbee",
    "source_id": "SRC-002"
   },
   "locator": "REPOSITORY",
   "relative_path": "artifacts/source_governance/tier1_rights_decisions.csv",
   "sha256": "20a3051b5836538fafea6455c16abe372a3fd1e9175a7cd882e1de7cd6541a83"
  },
  "transfer_portal:2010": {
   "bytes": 2,
   "capture_id": "cap_95ef7dd6da73a3638f303af7",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/transfer_portal/2010/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
   "rows": 0,
   "sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
  },
  "transfer_portal:2011": {
   "bytes": 2,
   "capture_id": "cap_fa9bb1e9b5fdf06566e75814",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/transfer_portal/2011/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
   "rows": 0,
   "sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
  },
  "transfer_portal:2012": {
   "bytes": 2,
   "capture_id": "cap_08ab140a68fa01a7f7168376",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/transfer_portal/2012/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
   "rows": 0,
   "sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
  },
  "transfer_portal:2013": {
   "bytes": 2,
   "capture_id": "cap_3d1d412cea46422d65df5410",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/transfer_portal/2013/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
   "rows": 0,
   "sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
  },
  "transfer_portal:2014": {
   "bytes": 2,
   "capture_id": "cap_96b7e887aa16ce54914bca71",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/transfer_portal/2014/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
   "rows": 0,
   "sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
  },
  "transfer_portal:2015": {
   "bytes": 2,
   "capture_id": "cap_883e831cb17e35a57a517203",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/transfer_portal/2015/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
   "rows": 0,
   "sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
  },
  "transfer_portal:2016": {
   "bytes": 2,
   "capture_id": "cap_74c32a321fa77d51e0c7d7b6",
   "locator": "DATA_ROOT",
   "relative_path": "raw/SRC-002/bat388-people/transfer_portal/2016/sha256_4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945.json",
   "rows": 0,
   "sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
  }
 }
}''')
#: The canonical profile of the first authorized build (None until that build is pinned by --profile).
RECRUITING_PROFILE: dict[str, Any] | None = None
# ---- END GENERATED ANCHORS ----
