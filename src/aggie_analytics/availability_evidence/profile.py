r"""The builtin fixed profile and frozen qualification rules of the C37 2026 availability source-assertion query (BAT-733).

``C37_2026_AVAILABILITY_ASSERTIONS_V1`` is the only trust authority of :mod:`aggie_analytics.availability_evidence`:
the exact whole-file SHA-256 and size of the existing Cycle 37 corrected national release database, its three closed
availability tables (ordered columns, permitted SQLite storage classes, JSON-text and Boolean columns, keys and row
counts), the five small report/posting witness files at their frozen relative data-root locations (SHA-256 and size),
the retained offline witnesses (31 roster and 13 policy captures and the 2026 schedule, bound but not re-read at query
time) and the frozen population counts of every natural grain. No caller manifest, environment variable or network
location can supply or replace any of it; a caller's ``--expect-sha256`` only adds a constraint.

:data:`RULES` freezes the response authority labels, the original-record decoding, the per-row qualification classes,
the source-cell comparison fields, the posting-claim witness rule, the cutoff clock classes, the selector applicability
matrix and grammars, the ordering, the paging bounds and the refusal codes. :data:`RULES_SHA256` is the SHA-256 of its
canonical JSON; the reader recomputes it before serving and refuses any difference (``QUALIFICATION_RULES_MISMATCH``).
:data:`CONTRACT_DOCUMENT` is the governed contract ``configs/availability_evidence_2026_contract.json`` (its committed
bytes must equal :func:`render_contract`).

Everything here is a historical source/parser assertion boundary: ``HISTORICAL_SOURCE_AND_PARSER_ASSERTIONS_ONLY``,
``FIXED_2026_CAPTURED_REPORT_OPPORTUNITY_SLICE``, no availability state, ``pit_admission=NOT_ADMITTED``,
``model_feature_admission=NOT_ADMITTED``, ``healthy_default=false``, predictive skill NOT_ESTABLISHED.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

PROFILE_ID = "C37_2026_AVAILABILITY_ASSERTIONS_V1"
CONTRACT_ID = "BAT-733-C37-2026-AVAILABILITY-ASSERTIONS-V1"
CONTRACT_REL = "configs/availability_evidence_2026_contract.json"
QUALIFICATION_SCHEMA = "BAS-AVAILABILITY-EVIDENCE-QUALIFICATION-1"
RESPONSE_SCHEMA = "BAS-AVAILABILITY-EVIDENCE-RESPONSE-1"
GRAINS = ("statement", "opportunity", "policy", "profile")
STAGES = ("initial_status", "update_1_status", "update_2_status", "game_day_status")
STAGE_COLUMNS = {"initial_status": "Initial Status", "update_1_status": "Update 1 Status",
                 "update_2_status": "Update 2 Status", "game_day_status": "Game Day Status"}
SOURCE_HEADER = ("Team", "Date", "Opponent", "Number", "Player", "Initial Status", "Update 1 Status", "Update 2 Status",
                 "Game Day Status")

AUTHORITY = {
    "evidence_class": "HISTORICAL_SOURCE_AND_PARSER_ASSERTIONS_ONLY",
    "slice": "FIXED_2026_CAPTURED_REPORT_OPPORTUNITY_SLICE",
    "availability_state_asserted": False,
    "pit_admission": "NOT_ADMITTED",
    "model_feature_admission": "NOT_ADMITTED",
    "healthy_default": False,
    "predictive_skill": "NOT_ESTABLISHED",
}

# --------------------------------------------------------------------------------------------- the fixed database

TABLES: dict[str, dict[str, Any]] = {
    "statement": {
        "table": "availability_statement_successor",
        "data_grain": "SOURCE_ROW_STAGE_ASSERTION",
        "columns": {
            "availability_row_id": ["integer"], "conference": ["text"], "contest": ["text"], "contest_label": ["text"],
            "effective_utc": ["null"], "embedded_in": ["null", "text"], "exact_status_text": ["text"],
            "identity": ["text"], "identity_version": ["text"], "jersey": ["text"], "label": ["text"],
            "no_medical_detail": ["integer"], "normalized_status": ["null", "text"],
            "out_does_not_imply_injury": ["integer"], "pit_admitted": ["integer"], "player_name": ["text"],
            "presence": ["text"], "program": ["text"], "program_as_written": ["text"],
            "publication_basis": ["null", "text"], "publication_time_established": ["integer"],
            "publication_utc": ["null", "text"], "quarantined": ["integer"], "report_vintage_retrieval_utc": ["text"],
            "rights_state": ["text"], "season_out_carried_from": ["null"], "source_locator": ["text"],
            "source_sha256": ["text"], "source_url": ["null", "text"], "stage": ["text"]},
        "json_columns": {"contest": "object", "identity": "object"},
        "boolean_columns": ["no_medical_detail", "out_does_not_imply_injury", "pit_admitted",
                            "publication_time_established", "quarantined"],
        "key": "availability_row_id",
        "rows": 1592,
        "order": ["availability_row_id"],
    },
    "opportunity": {
        "table": "availability_opportunity",
        "data_grain": "RETAINED_SCHEDULE_RECORD_OCCURRENCE_X_PROGRAM_SIDE",
        "columns": {
            "absent_players": ["text"], "canonical_contest_id": ["text"], "classification": ["null", "text"],
            "conference": ["null", "text"], "conference_game": ["integer"], "governing_policy": ["null", "text"],
            "kickoff_before_as_of": ["integer"], "kickoff_utc": ["text"], "label": ["text"],
            "policy_covers_2026": ["null", "text"], "program": ["text"], "report_expectation": ["text"],
            "side": ["text"], "state": ["text"], "statements_ingested": ["integer"], "team_id": ["integer"]},
        "json_columns": {},
        "boolean_columns": ["conference_game", "kickoff_before_as_of"],
        "key": None,
        "business_key": ["canonical_contest_id", "team_id", "side"],
        "occurrence_key": ["database_sha256", "table", "original_sqlite_rowid"],
        "rows": 3474,
        "order": ["canonical_contest_id", "team_id", "side", "original_sqlite_rowid"],
    },
    "policy": {
        "table": "availability_policy",
        "data_grain": "RETAINED_POLICY_OBSERVATION",
        "columns": {
            "absence_rule": ["text"], "absence_rule_applies_only_to": ["text"], "conference": ["text"],
            "covers_2026": ["text"], "first_report_contest_date": ["null", "text"], "format": ["text"],
            "label": ["text"], "non_conference": ["text"], "policy_id": ["text"], "policy_season": ["integer", "null"],
            "quotes": ["text"], "quotes_verified_in_extracted_text": ["text"], "schedule": ["text"], "scope": ["text"],
            "source_kind": ["text"], "source_path": ["text"], "source_sha256": ["text"], "supersedes": ["null", "text"],
            "url": ["text"], "version_as_stated": ["null", "text"], "vocabulary_gameday": ["text"],
            "vocabulary_observed_in_ingested_reports": ["null", "text"], "vocabulary_pregame": ["text"]},
        "json_columns": {"quotes": "list", "quotes_verified_in_extracted_text": "object", "schedule": "list",
                         "vocabulary_gameday": "list", "vocabulary_observed_in_ingested_reports": "list",
                         "vocabulary_pregame": "list"},
        "boolean_columns": [],
        "key": "policy_id",
        "rows": 13,
        "order": ["policy_id"],
    },
}

#: The exact report/posting witnesses verified before any grain is served (TP62 section 4), at frozen POSIX paths
#: relative to the caller's literal ``--data-root``.
WITNESSES: dict[str, dict[str, Any]] = {
    "SEC_RAW_CAPTURE": {
        "relative_path": "ops/cycle34/20260919T_R34_receipts/r34_12_browser_capture/"
                         "sec_official_availability_raw_20260920T054326Z.txt",
        "sha256": "7006a61eda1a172e0198363a3899ff66ddeae3b6d52783c34d56231ac8ddac67", "bytes": 4764,
        "role": "PRIMARY_REPORT_CAPTURE", "format": "TAB_SEPARATED_TEXT_TABLE", "conference": "SEC",
        "locator_prefix": "row", "player_rows": 63, "source_url": None, "embedded_in": None,
        "retrieval_observation_utc": "2026-09-20T05:43:26+00:00",
        "retrieval_observation_basis": "RETAINED_CAPTURE_RECEIPT_TIME_NOT_EMBEDDED_IN_THE_CAPTURE"},
    "ACC_ARCHIVE": {
        "relative_path": "ops/cycle37/attempts/REWORK-20260922T171601Z/private/acquisition/availability/"
                         "bfd5b51508cad4d2fdc918a4ac5ab3af0ba8fa2b980fb46a844eb52cd8d7b49c.bin",
        "sha256": "bfd5b51508cad4d2fdc918a4ac5ab3af0ba8fa2b980fb46a844eb52cd8d7b49c", "bytes": 507827,
        "role": "PRIMARY_REPORT_CAPTURE", "format": "RENDERED_JSON_ROWS", "conference": "ACC",
        "locator_prefix": "rows", "player_rows": 218,
        "source_url": "https://app.hdintelligence.com/?source=ACC&sport=Football&conf=ACC&type=archive",
        "embedded_in": "https://theacc.com/sports/2025/8/28/availability-reporting-football-archive.aspx",
        "retrieval_observation_utc": "2026-09-23T10:44:03.913Z",
        "retrieval_observation_basis": "CAPTURE_EMBEDDED_RENDERED_UTC"},
    "BIG12_ARCHIVE": {
        "relative_path": "ops/cycle37/attempts/REWORK-20260922T171601Z/private/acquisition/availability/"
                         "07a9bdadee51c46fcc588174c148758e017c2be7235c4967205ebd5349ef430c.bin",
        "sha256": "07a9bdadee51c46fcc588174c148758e017c2be7235c4967205ebd5349ef430c", "bytes": 149859,
        "role": "PRIMARY_REPORT_CAPTURE", "format": "RENDERED_JSON_ROWS", "conference": "Big 12",
        "locator_prefix": "rows", "player_rows": 54,
        "source_url": "https://app.hdintelligence.com/?source=B12&sport=Football&conf=B12&type=archive",
        "embedded_in": "https://big12sports.com/sports/2025/8/21/FBReportArchive.aspx",
        "retrieval_observation_utc": "2026-09-23T10:44:35.512Z",
        "retrieval_observation_basis": "CAPTURE_EMBEDDED_RENDERED_UTC"},
    "BIGTEN_ARCHIVE": {
        "relative_path": "ops/cycle37/attempts/REWORK-20260922T171601Z/private/acquisition/availability/"
                         "660569f36bcd8825e8ab68307a1e619f565c9e2ae507e2c54b7619f6a4c13384.bin",
        "sha256": "660569f36bcd8825e8ab68307a1e619f565c9e2ae507e2c54b7619f6a4c13384", "bytes": 165189,
        "role": "PRIMARY_REPORT_CAPTURE", "format": "RENDERED_JSON_ROWS", "conference": "Big Ten",
        "locator_prefix": "rows", "player_rows": 63,
        "source_url": "https://app.hdintelligence.com/?source=B10&sport=Football&conf=B10&type=archive",
        "embedded_in": "https://bigten.org/fb/article/60323/",
        "retrieval_observation_utc": "2026-09-23T10:45:16.941Z",
        "retrieval_observation_basis": "CAPTURE_EMBEDDED_RENDERED_UTC"},
    "ACC_CURRENT_POSTING": {
        "relative_path": "ops/cycle37/attempts/REWORK-20260922T171601Z/private/acquisition/availability/"
                         "b8953b637350f5e367170fa9e125d4b125489944b18c9e319768fc5525171e98.bin",
        "sha256": "b8953b637350f5e367170fa9e125d4b125489944b18c9e319768fc5525171e98", "bytes": 2059,
        "role": "LATER_POSTING_VIEW_CAPTURE", "format": "RENDERED_JSON_CARDS", "conference": "ACC",
        "locator_prefix": None, "player_rows": None,
        "source_url": "https://app.hdintelligence.com/?source=ACC&sport=Football&conf=ACC&type=report",
        "embedded_in": "https://theacc.com/sports/2025/8/28/availability-reporting-football.aspx",
        "retrieval_observation_utc": "2026-09-23T10:42:51.193Z",
        "retrieval_observation_basis": "CAPTURE_EMBEDDED_RENDERED_UTC"},
}
PRIMARY_WITNESSES = ("SEC_RAW_CAPTURE", "ACC_ARCHIVE", "BIG12_ARCHIVE", "BIGTEN_ARCHIVE")
POSTING_WITNESS = "ACC_CURRENT_POSTING"

#: Bound offline qualification inputs (TP62 section 4): not re-read or re-hashed at query time; their proof is the
#: retained offline qualification, never a present-query raw audit.
OFFLINE_WITNESSES = {
    "roster_witnesses": 31, "policy_witnesses": 13,
    "schedule": {"relative_path": "ops/cycle30_work/outputs/CFBD_GAMES_TRANCHE.jsonl",
                 "sha256": "7072f260d0cd373602e8121d5d875ae3e9d722c3dc8735f56390845e7b32aac2", "season": 2026},
    "proof": "RETAINED_OFFLINE_EVIDENCE_NOT_PRESENT_QUERY_RAW_AUDIT",
}

PROFILE: dict[str, Any] = {
    "profile_id": PROFILE_ID,
    "database": {
        "sha256": "757d4b5f0649d60943c4594d6e0c22b7c930f5ef3acf9f675b4f93f328a7d331", "bytes": 236834816,
        "content_addressed_directory_key": "67d2ce357dc36d5a13a8edc94d0ffa9fc27115768817b1ee1ac9dff567757671",
        "directory_key_meaning": "A_DIFFERENT_RETAINED_IDENTITY_NEVER_A_SUBSTITUTE_FOR_THE_FILE_SHA256",
        "release": "CYCLE37_CORRECTED_NATIONAL_RELEASE"},
    "tables": TABLES,
    "witnesses": WITNESSES,
    "offline_witnesses": OFFLINE_WITNESSES,
    "report_season": 2026,
    "schedule_season": 2026,
    "retained_opportunity_as_of_utc": "2026-09-23T10:45:16.941Z",
    #: The frozen population at every natural grain (each re-derived from the verified records before serving).
    "population": {
        "statements": 1592, "source_player_rows": 398, "source_cells": 1592,
        "statements_by_conference": {"ACC": 872, "Big 12": 216, "Big Ten": 252, "SEC": 252},
        "statements_by_stage": {stage: 398 for stage in STAGES},
        "presence": {"PUBLISHED_EMPTY": 179, "PUBLISHED_VALUE": 1413},
        "source_empty_representations": {"normalized_null": 129, "normalized_unknown_sec": 50},
        "status_texts": {"-": 179, "Available": 105, "Doubtful": 65, "Exempt": 3, "Game Time Decision": 23,
                         "Out": 899, "Probable": 138, "Questionable": 180},
        "effective_time_known": 0, "pit_admitted": 0, "publication_claims": 19,
        "source_person_id_prefixes": {"CFBD": 276, "OFFICIAL": 1276, "null": 40},
        "joint_person_contest": {"RETAINED_PERSON_AND_CONTEST_CLAIMS": 1512, "PERSON_CLAIM_UNRESOLVED": 40,
                                 "CONTEST_CLAIM_NOT_QUALIFIED": 40, "PERSON_UNRESOLVED_AND_CONTEST_NOT_QUALIFIED": 0},
        "identity_states": {"RESOLVED_NAME_AND_JERSEY_AGREE": 1548, "RESOLVED_UNIQUE_NAME_JERSEY_NOT_STATED": 4,
                            "UNRESOLVED_JERSEY_SHARED_BY_SEVERAL_PLAYERS": 8,
                            "UNRESOLVED_NAME_AND_JERSEY_POINT_AT_DIFFERENT_PLAYERS": 8,
                            "UNRESOLVED_NO_ROSTER_ROW_MATCHES": 24},
        "contest_states": {"CONTEST_BOUND": 1552, "CONTEST_LABEL_NAMES_THE_PROGRAM_ITSELF": 40},
        "quarantined": 40,
        "opportunity_occurrences": 3474, "opportunity_distinct_business_keys": 3220,
        "opportunity_singleton_business_keys": 2966, "opportunity_duplicate_business_key_groups": 254,
        "schedule_record_occurrences": 1737, "schedule_distinct_game_ids": 1610, "schedule_duplicate_game_ids": 127,
        "opportunity_states": {"REPORT_STATEMENTS_INGESTED": 43, "UNKNOWN_NOT_HEALTHY": 3431},
        "policy_expected_occurrences": 989, "policy_expected_before_as_of_occurrences": 89,
        "policy_expected_ingested_occurrences": 31,
        "distinct_key_inventory": {"opportunity_states": {"REPORT_STATEMENTS_INGESTED": 43, "UNKNOWN_NOT_HEALTHY": 3177},
                                   "policy_expected": 974, "policy_expected_before_as_of": 77,
                                   "policy_expected_ingested": 31},
        "policies": 13,
    },
}

# --------------------------------------------------------------------------------------------- frozen rules

RULES: dict[str, Any] = {
    "schema": QUALIFICATION_SCHEMA,
    "response_schema": RESPONSE_SCHEMA,
    "authority": AUTHORITY,
    "grains": list(GRAINS),
    "original_record": {
        "rule": "Every column of the original table row in its original order. JSON-text columns are decoded with "
                "strict JSON (no NaN/Infinity, no duplicate member names, depth at most 32) into the declared object "
                "or list type (null stays null); Boolean columns accept only the integers 0 and 1 and are served as "
                "false/true; every other value keeps its exact SQLite storage class (integer, text or null). Nested "
                "values are never flattened and integers, floats and Booleans are never coerced into one another. "
                "The table's union columns and nulls are the retained table representation, not a claim that a "
                "JSONL source object carried every key.",
        "json_max_depth": 32,
        "source_occurrence": "opportunity rows only: {database_sha256, table, original_sqlite_rowid}, a wrapper "
                             "identifying the occurrence in the pinned database bytes; never inserted into "
                             "original_record and never a declared source column",
    },
    "statement_qualification": {
        "source_cell": {
            "verified": "VERIFIED_RETAINED_SOURCE_CELL",
            "disputed": "DISPUTED_AGAINST_PINNED_WITNESS",
            "locator": r"^(row|rows)\[([1-9][0-9]{0,5})\]\.(initial_status|update_1_status|update_2_status|game_day_status)$",
            "compared_fields": ["source_sha256", "locator_prefix", "locator_stage", "stage", "conference",
                                "report_vintage_retrieval_utc", "source_url", "embedded_in", "program_as_written",
                                "date_as_written", "contest_label", "opponent_as_written", "jersey", "player_name",
                                "exact_status_text", "presence"],
            "field_rules": {
                "program_as_written": "equals the raw Team cell",
                "date_as_written": "contest.date_as_written equals the ISO date of the raw Date cell (M/D/YY or "
                                   "'Ddd, Mon D, YYYY' with a consistent weekday)",
                "contest_label": "equals '<month>/<day>/<two-digit year> <raw Opponent>' (the retained producer "
                                 "label form)",
                "opponent_as_written": "only when the contest claim carries it: equals the raw Opponent without a "
                                       "leading 'vs. ' or 'at '",
                "jersey": "equals the raw Number cell (an empty cell is an empty string)",
                "player_name": "equals the raw Player cell",
                "exact_status_text": "equals the raw stage cell",
                "presence": "PUBLISHED_EMPTY exactly when the raw stage cell is '-', otherwise PUBLISHED_VALUE",
                "conference": "equals the witness conference",
                "report_vintage_retrieval_utc": "equals the witness retrieval observation text",
                "source_url": "equals the witness source URL (null for the SEC capture)",
                "embedded_in": "equals the witness embedding page (null for the SEC capture)",
                "locator_stage": "the locator's stage token equals the row's stage",
                "locator_prefix": "row for the SEC capture, rows for the rendered JSON archives"},
            "source_empty": "a raw '-' cell is SOURCE_EMPTY_CELL whichever original normalized representation "
                            "(null or SEC UNKNOWN) the producer stored; the originals are served unchanged",
            "consequence_of_dispute": "ORIGINAL_RETAINED_UNCHANGED_DISPUTE_VISIBLE_WITH_COMPETING_WITNESS_TEXT",
        },
        "stage_time": "SOURCE_COLUMN_ONLY_PUBLICATION_INSTANT_UNKNOWN",
        "publication": {
            "witnessed": "SOURCE_POSTING_CLAIM_WITNESSED_IN_LATER_CAPTURE",
            "unknown": "PUBLICATION_TIME_UNKNOWN",
            "disputed": "DISPUTED_AGAINST_PINNED_WITNESS",
            "rule": "An original publication_time_established claim is witnessed only when the later posting capture "
                    "holds an INITIAL REPORT card for the row's initial_status stage whose game date (card footer and "
                    "page heading year) equals the contest date, whose team column equals program_as_written and "
                    "lists exactly one entry '<position> #<jersey> <player>' under the heading equal to the "
                    "upper-cased status text, whose 'Report posted on <Weekday>, <Month> <D> at <h>:<mm><am|pm> ET' "
                    "line has a consistent weekday and converts (US Eastern time, daylight time from the second "
                    "Sunday of March 2:00 to the first Sunday of November 2:00) to publication_utc, and whose capture "
                    "time is later than the claim. Every other row is PUBLICATION_TIME_UNKNOWN.",
            "authority": "SOURCE_REPORTED_POSTING_CLAIM_NOT_FIRST_KNOWN_NOT_VERSION_SEAL_NOT_PIT",
            "update_cards": "an UPDATE REPORT card would be listed as a card kind; none is invented",
        },
        "effective_time": "EFFECTIVE_TIME_UNKNOWN",
        "first_known": "FIRST_KNOWN_NOT_ESTABLISHED",
        "identity": {
            "resolved": "RETAINED_PARSER_IDENTITY_CLAIM",
            "unresolved": "the original UNRESOLVED_* state is served as the reason",
            "scope": {"CFBD": "PROVIDER_SCOPED_PERSON_ID", "OFFICIAL": "SOURCE_SCOPED_ROSTER_ROW_ID"},
            "global_person_identity": "NOT_QUALIFIED",
            "roster_witness_proof": OFFLINE_WITNESSES["proof"],
        },
        "contest": {
            "bound": "RETAINED_PARSER_CONTEST_CLAIM",
            "self_opponent": "CONTEST_NOT_QUALIFIED_SELF_OPPONENT",
            "schedule_witness_proof": OFFLINE_WITNESSES["proof"],
        },
        "joint": ["RETAINED_PERSON_AND_CONTEST_CLAIMS", "PERSON_CLAIM_UNRESOLVED", "CONTEST_CLAIM_NOT_QUALIFIED",
                  "PERSON_UNRESOLVED_AND_CONTEST_NOT_QUALIFIED"],
        "quarantine_flag": "IDENTITY_ONLY_FLAG_NOT_WHOLE_ROW_QUALIFICATION",
        "status": {
            "meaning": "SOURCE_STATEMENT_LITERAL_NOT_INDEPENDENT_HEALTH_OR_AVAILABILITY_STATE",
            "available": "A_SOURCE_AVAILABLE_STATEMENT_IS_NOT_AN_INDEPENDENTLY_ESTABLISHED_HEALTHY_PERSON",
            "exempt": "EXEMPT_IS_NEITHER_AVAILABLE_NOR_OUT_NOR_A_MEDICAL_CAUSE",
            "source_empty": "SOURCE_EMPTY_CELL_NOT_HEALTH_NOT_AVAILABILITY_NOT_REPORT_COMPLETENESS",
        },
    },
    "opportunity_qualification": {
        "occurrence": {"singleton": "SINGLETON_BUSINESS_KEY",
                       "exact_duplicate": "EXACT_DUPLICATE_ASSERTION_OF_THE_SAME_BUSINESS_KEY",
                       "nonidentical_repeat": "NONIDENTICAL_BUSINESS_KEY_REPEAT",
                       "meaning": "DUPLICATE_ASSERTIONS_ARE_NOT_DIFFERENT_GAMES_SOURCES_VERSIONS_OR_COVERAGE"},
        "denominator": "RETAINED_FIXED_AS_OF_DENOMINATOR_ASSERTION",
        "not_current": "RETAINED_AS_OF_2026-09-23T10:45:16.941Z_NOT_CURRENT_COVERAGE",
        "state": {"UNKNOWN_NOT_HEALTHY": "NO_REPORT_STATEMENT_INGESTED_UNKNOWN_NOT_HEALTHY",
                  "REPORT_STATEMENTS_INGESTED": "SOURCE_STAGE_ASSERTIONS_INGESTED_NOT_REPORT_COMPLETENESS"},
        "statements_ingested": "A_COUNT_OF_RETAINED_SOURCE_STAGE_ASSERTIONS_FOR_THE_CONTEST_AND_PROGRAM_NOT_PEOPLE_OR_REPORTS",
        "policy": {"present": "POLICY_OBSERVATION_NOT_REPORT_COMPLETENESS_PROOF", "absent": "NO_GOVERNING_POLICY_HELD"},
        "schedule_witness_proof": OFFLINE_WITNESSES["proof"],
    },
    "policy_qualification": {
        "state": "POLICY_OBSERVATION_NOT_REPORT_COMPLETENESS_PROOF",
        "witness_proof": OFFLINE_WITNESSES["proof"],
        "quotes": "RETAINED_PRODUCER_QUOTE_VERIFICATION_CLAIM",
        "absence_rule": "APPLIES_ONLY_TO_AN_ACTUAL_COMPLETE_CURRENT_REPORT_NEVER_TO_A_MISSING_PARTIAL_OR_STALE_ONE",
        "coverage": "ORIGINAL_POLICY_COVERAGE_CLAIM_NOT_NATIONAL_COMPLETENESS",
        "policy_season": {"stated": "ORIGINAL_POLICY_SEASON", "unstated": "POLICY_SEASON_UNSTATED"},
    },
    "cutoff": {
        "grammar": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{1,6})?)?(Z|[+-][0-9]{2}:[0-9]{2})$",
        "relations": ["BEFORE", "AT", "AFTER", "UNKNOWN"],
        "clocks": ["PRIMARY_CAPTURE_RETRIEVAL_OBSERVATION", "LATER_POSTING_CAPTURE_OBSERVATION",
                   "SOURCE_REPORTED_POSTING_CLAIM", "EFFECTIVE_TIME", "FIRST_KNOWN_TIME"],
        "rule": "A comparison only: every selected row is kept; no version, stage, last value or forecast input is "
                "selected; a date-only, naive or local-time value is refused.",
    },
    "temporal_state_refusals": {"--as-of": "AS_OF_STATE_NOT_SUPPORTED", "--current": "CURRENT_STATE_NOT_SUPPORTED",
                                "--latest": "CURRENT_STATE_NOT_SUPPORTED", "--require-pit": "PIT_NOT_ADMITTED",
                                "--forecast-input": "FORECAST_ADMISSION_NOT_SUPPORTED"},
    "selectors": {
        "--statement-id": {"grains": ["statement"], "grammar": "^[1-9][0-9]{0,18}$", "match": "availability_row_id"},
        "--policy-id": {"grains": ["opportunity", "policy"], "grammar": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
                        "match": {"opportunity": "governing_policy", "policy": "policy_id"}},
        "--team": {"grains": ["statement", "opportunity"], "grammar": "LITERAL_TEXT", "match": "program"},
        "--conference": {"grains": ["statement", "opportunity", "policy"], "grammar": "LITERAL_TEXT",
                         "match": "conference"},
        "--season": {"grains": ["statement", "opportunity"], "grammar": "^[0-9]{4}$",
                     "match": {"statement": "contest.season", "opportunity": "SCHEDULE_SEASON_2026"}},
        "--policy-season": {"grains": ["policy"], "grammar": "^[0-9]{4}$", "match": "policy_season"},
        "--contest": {"grains": ["statement", "opportunity"], "grammar": "^SRC-002:GAME:[0-9]{1,18}$",
                      "match": {"statement": "contest.canonical_contest_id", "opportunity": "canonical_contest_id"}},
        "--person-id": {"grains": ["statement"], "grammar": "^(CFBD:[0-9]{1,18}|OFFICIAL:[^:]{1,100}:[0-9]{4}:[0-9]{1,6})$",
                        "match": "identity.canonical_player_id"},
        "--published-name": {"grains": ["statement"], "grammar": "LITERAL_TEXT", "match": "player_name"},
        "--source-sha256": {"grains": ["statement", "policy"], "grammar": "^[0-9a-f]{64}$",
                            "match": {"statement": "source_sha256", "policy": "source_sha256"}},
        "--stage": {"grains": ["statement"], "grammar": "ENUM", "values": list(STAGES), "match": "stage"},
        "--reported-status": {"grains": ["statement"], "grammar": "LITERAL_TEXT", "match": "exact_status_text"},
        "--presence": {"grains": ["statement"], "grammar": "ENUM", "values": ["PUBLISHED_EMPTY", "PUBLISHED_VALUE"],
                       "match": "presence"},
        "--identity-state": {"grains": ["statement"], "grammar": "ENUM",
                             "values": sorted(PROFILE["population"]["identity_states"]), "match": "identity.state"},
        "--contest-state": {"grains": ["statement"], "grammar": "ENUM",
                            "values": sorted(PROFILE["population"]["contest_states"]), "match": "contest.state"},
        "--cutoff": {"grains": ["statement"], "grammar": "CUTOFF", "match": "NONE_COMPARISON_ONLY"},
    },
    "literal_text": "Exact, case-sensitive, code-point equality with the retained value: no substring, fuzzy, case or "
                    "whitespace folding, alias or numeric equivalence. A malformed value (empty, leading or trailing "
                    "white space, a control character, a lone surrogate or more than 200 characters) is "
                    "INVALID_SELECTOR.",
    "domains": "A well-formed value not represented in the fixed profile's domain for that selector is "
               "KEY_NOT_IN_PROFILE (team: programs of the statement and opportunity tables; conference: every "
               "retained conference; contest: every retained contest claim; source-sha256: statement and policy "
               "source digests and the posting witness; person-id, published-name, statement-id, reported-status: "
               "the statement table; policy-id: the policy table and every retained governing-policy claim); a "
               "foreign season is SEASON_NOT_IN_PROFILE. Represented values whose intersection is empty succeed with "
               "rows=[], total_count=0 and an explicit empty-match disposition.",
    "paging": {"default_limit": 100, "min_limit": 1, "max_limit": 1000, "max_offset": 9223372036854775807,
               "grammar": "^[0-9]{1,19}$", "all_excludes_explicit_paging": True,
               "rule": "Paging applies after filtering; an offset beyond the filtered population returns rows=[] with "
                       "the exact filtered total."},
    "ordering": {"statement": ["availability_row_id"],
                 "opportunity": ["canonical_contest_id", "team_id", "side", "original_sqlite_rowid"],
                 "policy": ["policy_id"], "profile": ["SINGLETON"],
                 "collation": "Python code-point order for text, numeric order for integers; null sorts first"},
    "refusals": {
        "request": ["ARGUMENT_INVALID", "PROFILE_UNKNOWN", "SELECTOR_NOT_APPLICABLE", "INVALID_SELECTOR",
                    "KEY_NOT_IN_PROFILE", "SEASON_NOT_IN_PROFILE", "PAGING_INVALID", "AS_OF_STATE_NOT_SUPPORTED",
                    "CURRENT_STATE_NOT_SUPPORTED", "PIT_NOT_ADMITTED", "FORECAST_ADMISSION_NOT_SUPPORTED",
                    "DATABASE_LOCATION_UNSUPPORTED", "DATABASE_LOCATION_NOT_LITERAL", "DATA_ROOT_LOCATION_UNSUPPORTED",
                    "EXPECTED_SHA256_MISMATCH"],
        "integrity": ["DATABASE_MISSING", "DATA_ROOT_MISSING", "WITNESS_MISSING", "DATABASE_IDENTITY_MISMATCH",
                      "WITNESS_IDENTITY_MISMATCH", "WITNESS_FORMAT_INVALID", "SCHEMA_MISMATCH", "RECORD_INVALID",
                      "POPULATION_MISMATCH", "INPUT_CHANGED_DURING_SESSION", "QUALIFICATION_RULES_MISMATCH",
                      "PROFILE_INTEGRITY_MISMATCH", "QUALIFICATION_AUDIT_MISMATCH"],
        "exit_codes": {"request": 2, "integrity": 3},
        "rule": "A request refusal is exit 2; an input integrity failure is exit 3 and is never a scientific "
                "unsupported-result answer. Network, device and namespace spellings and every malformed or "
                "inapplicable selector are refused before any filesystem access; the whole-file database SHA-256 is "
                "checked before any record is interpreted, so a coordinated record/schema forgery refuses as "
                "DATABASE_IDENTITY_MISMATCH.",
    },
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def rules_sha256(rules: dict[str, Any] | None = None) -> str:
    return hashlib.sha256(canonical_bytes(RULES if rules is None else rules)).hexdigest()


def profile_sha256(profile: dict[str, Any] | None = None) -> str:
    return hashlib.sha256(canonical_bytes(PROFILE if profile is None else profile)).hexdigest()


#: The frozen rules and builtin profile identities, as literals: the reader recomputes both before serving and refuses
#: any difference (QUALIFICATION_RULES_MISMATCH / PROFILE_INTEGRITY_MISMATCH).
RULES_SHA256 = "4a99cfc76f76c45b219f47cef4dd688aa179b0911adaa2b03927746174efb96a"
PROFILE_SHA256 = "4ebc6c01cc13396f33668b40ca390aa34d5c8a841492b0b0a69ca5549a37b27b"

CONTRACT_DOCUMENT: dict[str, Any] = {
    "contract_id": CONTRACT_ID,
    "jira_key": "BAT-733",
    "plan": "TP62-A01 (Cycle #62 — Attempt #1)",
    "profile": PROFILE,
    "rules": RULES,
    "rules_sha256": RULES_SHA256,
    "console_script": "bas-availability-evidence-query",
    "module": "aggie_analytics.availability_evidence.query",
}


def render_contract() -> str:
    """The exact committed bytes of configs/availability_evidence_2026_contract.json."""
    return json.dumps(CONTRACT_DOCUMENT, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
