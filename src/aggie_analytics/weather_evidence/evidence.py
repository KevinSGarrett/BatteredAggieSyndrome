r"""National observed-weather evidence 2024 (BAT-731 bounded contribution to BAT-417/BAT-419, Cycle #60 TP60-A01).

Every rule lives here, and the committed data contract ``configs/national_observed_weather_evidence_2024_contract.json``
must equal these constants (the builder refuses otherwise). The reader pins that contract's SHA-256, every retained
input's SHA-256, every raw station-year capture and the canonical release profile (:data:`ANCHORS`, generated into
:mod:`.anchors`).

Inputs, each resolved under an explicitly named data root at the contract's relative locator and refused unless its
bytes hash to the pinned SHA-256 (nothing here is acquired; no source request is made). Parquet is read only through the
pinned Polars decoder (imported by :func:`load_inputs` alone); every decode, ranking, selection, join and rule below is
plain Python over the decoded values:

* the accepted BAT-710 parent population 3baff07f (every season-2024 contest of the national FBS/FCS denominator with its
  participants, site, date and status; scores are never read);
* the accepted C48 alias reconciliation c1e83fda (its 2024 parent and provider reconciliation records: the explicit
  promoted one-to-one participant/date relation is the only authority that associates a provider game with a parent
  contest);
* the retained SRC-002 2024 FBS games capture (920 rows, the provider scheduled start and TBD flag) and its receipt;
* the retained 920-row observed-weather pilot 47dea7e7 (decoded through the pinned decoder; every original field is
  preserved), its run and capture manifests, the original game-coordinate and rank-one station-candidate payloads and
  the 2024 coverage acquisition manifest;
* the 157 raw NOAA ISD global-hourly station-year CSVs (1,251,673,376 bytes), streamed in place, never copied;
* the official NOAA/NCEI ISD format document that defines the scaled fields, sentinels, quality codes and report types.

Derived records (one immutable, create-only, content-addressed release; every row stays in its grain):

1. **contest-weather** -- exactly one record per accepted 2024 parent contest (1,672): participant/site/date
   provenance (no score), the alias disposition, the relation state (promoted one-to-one, candidate not promoted, or no
   provider row outside the FBS route), zero or one associated pilot row, the candidate station and its reference
   status, the associated nearest observation and every unsupported reason. Missing evidence stays null; never a zero
   temperature, a default or a no-weather assertion.
2. **pilot-weather** -- exactly one record per original pilot row (920, the 38 unpromoted rows included): every original
   field under ``original_``, the exact provider-capture join, the verified association clock, the relation decision,
   the independently reconstructed before/after/nearest candidates (``verified_``), their discrepancy disposition, the
   official quality/report meanings, missing-candidate reasons and the witness keys of the selected raw rows.
3. **station-year** -- all 157 captures: station/year/file identity, raw/request/capture hashes, the CSV header and
   schema, data/duplicate/malformed rows, report types, decoded, sentinel and quality-code counts, raw precipitation
   presence, observation span, candidate station metadata (reference only) and source clocks and rights.
4. **source-witness** -- the complete ordered witnesses: every pinned input, parent contract and raw file, and every raw
   CSV row the reconstruction selected (file SHA-256 and CSV row number, the governed raw field strings, the row's own
   decode, the full duplicate-timestamp ranking and the pilot selections that cite it). No raw body enters Git or the
   package.
5. **census** -- counts of every grain and state, recomputed by the reader.

Observation rules (the frozen pilot contract's rules, restated and reproduced from the raw rows, never from the pilot's
chosen fields): a station-year file must hold only its station and calendar year; TMP/DEW (tenths of a degree Celsius,
sentinel +9999), SLP (tenths of a hectopascal, sentinel 99999), VIS (metres, sentinel 999999) and WND (direction degrees
with sentinel 999; speed tenths of a metre per second with sentinel 9999) decode to null at a sentinel, an empty or a
non-integer value, keeping the raw string and the quality code; a scaled integer without a finite binary64 value has no
decode and is refused (``WEATHER_DECODE_MISMATCH``); precipitation AA groups stay raw text (never an hourly
total). Among rows sharing a timestamp the row with the most decoded common fields wins, then the lower report type,
source code and row number. The before candidate is the latest observation at or before the association clock, the
after candidate the earliest at or after it (one row when exactly equal), and the nearest is the before candidate when
its distance is not greater (earlier wins a tie). Only the kickoff calendar year's file is searched; no maximum time
distance, acceptance threshold, quality promotion or alternate station exists.

Every record carries RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED and predictive skill NOT_ESTABLISHED. A
station measurement is not a stadium condition, the provider scheduled start is not the actual kickoff, current catalog
venues and roof flags are not historically effective facts, and observed 2024 weather is not a forecast input.

The reader (:class:`WeatherEvidence`) needs no data root: it refuses with a stable code unless the location, the run
manifest, the database bytes, the schema, every meta claim, every record's exact members and JSON types, the complete
expected collection of every grain, every rule that can be re-derived from the records themselves (raw-row decoding,
duplicate ranking, candidate order, distances and the tie rule, discrepancy and reason derivations, foreign keys and
associations, the pinned source authorities and clocks, and the census), the content document, the contract-defined
database identity document and the pinned canonical profile all verify. The query (:meth:`WeatherEvidence.query`)
serves the four grains with exact intersecting selectors and paging.
"""
from __future__ import annotations

import bisect
import csv
import io
import json
import math
import os
import random
import re
import sqlite3
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics import readonly_sqlite
from aggie_analytics.retrospective_baseline import benchmark as bm

canonical_json_bytes = bm.canonical_json_bytes
canonical_line = bm.canonical_line
sha256_bytes = bm.sha256_bytes
sha256_file = bm.sha256_file
is_int = bm.is_int
_io_path = bm._io_path
manifest_path_for = bm.manifest_path_for
#: A SHA-256 identity (``\Z``: a trailing newline is never part of an identity).
IDENTITY_RE = re.compile(r"[0-9a-f]{64}\Z")

# --------------------------------------------------------------------------------------------- identity and scope

POPULATION = "national_observed_weather_evidence_2024"
DB_FILE = "national_observed_weather_evidence.sqlite"
CONTRACT_ID = "BAT-731-NATIONAL-OBSERVED-WEATHER-EVIDENCE-2024-V1.0"
CONTRACT_REL = "configs/national_observed_weather_evidence_2024_contract.json"
CONTENT_SCHEMA = "BAS-WEATHER-EVIDENCE-CONTENT-1"
DATABASE_SCHEMA = "BAS-WEATHER-EVIDENCE-DATABASE-1"
DB_SCHEMA = "BAS-WEATHER-EVIDENCE-DB-1"
PAYLOAD_SCHEMA = "BAS-WEATHER-EVIDENCE-PAYLOAD-1"
FOOTBALL_SEASON = 2024
CALENDAR_YEARS = (2024, 2025)
WEATHER_SOURCE_ID = "SRC-029"
PROVIDER_SOURCE_ID = "SRC-002"
PARENT_SOURCE_ID = "SRC-015"

LABELS = {
    "evidence_label": "RETROSPECTIVE_RESEARCH",
    "trust_state": "UNTRUSTED_SHADOW",
    "pit_eligibility": "PIT_NOT_ADMITTED",
    "predictive_skill": "NOT_ESTABLISHED",
    "observation_kind": "OBSERVED_STATION_RECORD_NOT_FORECAST",
    "station_authority": "CANDIDATE_STATION_MEASUREMENT_NOT_STADIUM_CONDITION",
    "association_clock": "PROVIDER_SCHEDULED_TIME_NOT_OFFICIAL_ACTUAL_KICKOFF",
    "venue_authority": "CURRENT_CATALOG_REFERENCE_NOT_HISTORICAL_EFFECTIVE_VENUE_OR_ROOF",
    "exposure": "EXPOSED_NOT_PROTECTED",
}
BASE_LABEL_KEYS = ("evidence_label", "trust_state", "pit_eligibility", "predictive_skill")
GRAIN_LABEL_KEYS = {
    "contests": (*BASE_LABEL_KEYS, "observation_kind", "station_authority", "association_clock", "venue_authority",
                 "exposure"),
    "pilots": (*BASE_LABEL_KEYS, "observation_kind", "station_authority", "association_clock", "venue_authority",
               "exposure"),
    "station_years": (*BASE_LABEL_KEYS, "observation_kind", "station_authority"),
    "witnesses": BASE_LABEL_KEYS,
    "census": BASE_LABEL_KEYS,
}

# --------------------------------------------------------------------------------------------- frozen observation rules

#: The frozen original pilot contract's selection (noaa_isd_game_observation_shadow_contract.json), restated exactly.
ORIGINAL_SELECTION = {
    "temporal_candidates": ["LATEST_AT_OR_BEFORE_KICKOFF", "EARLIEST_AT_OR_AFTER_KICKOFF", "NEAREST_ABSOLUTE_TO_KICKOFF"],
    "maximum_time_delta_minutes": None,
    "automatic_station_acceptance": False,
    "automatic_observation_acceptance": False,
    "dome_observation_feature_eligibility": False,
    "tie_break": "EARLIER_OBSERVATION_WINS",
    "duplicate_timestamp_ranking": "MOST_DECODED_COMMON_FIELDS_THEN_REPORT_TYPE_SOURCE_AND_ROW_NUMBER_ASCENDING",
    "quality_flag_policy": "PRESERVE_NOAA_FLAGS_AND_DECODE_SENTINELS_TO_NULL",
    "station_rank": 1,
    "calendar_year_file": "THE_UTC_KICKOFF_CALENDAR_YEAR_FILE_ONLY",
    "row_number": "ONE_BASED_CSV_LINE_NUMBER_WITH_THE_HEADER_AS_LINE_1",
}
#: Scaled mandatory fields (official ISD format document, mandatory data section).
DECODING = {
    "TMP": {"field": "temperature_c", "unit": "DEGREES_CELSIUS", "scale": 10, "sentinel": "9999"},
    "DEW": {"field": "dew_point_c", "unit": "DEGREES_CELSIUS", "scale": 10, "sentinel": "9999"},
    "VIS": {"field": "visibility_m", "unit": "METERS", "scale": 1, "sentinel": "999999"},
    "SLP": {"field": "sea_level_pressure_hpa", "unit": "HECTOPASCALS", "scale": 10, "sentinel": "99999"},
    "WND": {"direction_field": "wind_direction_degrees", "direction_unit": "ANGULAR_DEGREES", "direction_sentinel": "999",
            "speed_field": "wind_speed_mps", "speed_unit": "METERS_PER_SECOND", "speed_scale": 10, "speed_sentinel": "9999",
            "calm": "TYPE_C_OR_TYPE_9_WITH_SPEED_0000_IS_CALM_SPEED_ZERO_DIRECTION_NULL",
            "variable": "DIRECTION_999_WITH_TYPE_V_IS_VARIABLE_DIRECTION_NULL"},
    "precipitation": "RAW_AA_FIELDS_ONLY_NOT_NUMERICALLY_AGGREGATED",
    "missing": "SENTINEL_EMPTY_OR_NON_INTEGER_VALUE_IS_NULL_WITH_RAW_STRING_AND_QUALITY_CODE_PRESERVED",
}
#: Official quality code meanings (ISD format document, mandatory data section and its interactive-QC note).
QUALITY_MEANINGS = {
    "0": "PASSED_GROSS_LIMITS_CHECK",
    "1": "PASSED_ALL_QUALITY_CONTROL_CHECKS",
    "2": "SUSPECT",
    "3": "ERRONEOUS",
    "4": "PASSED_GROSS_LIMITS_CHECK_NCEI_SOURCE",
    "5": "PASSED_ALL_QUALITY_CONTROL_CHECKS_NCEI_SOURCE",
    "6": "SUSPECT_NCEI_SOURCE",
    "7": "ERRONEOUS_NCEI_SOURCE",
    "9": "PASSED_GROSS_LIMITS_CHECK_IF_ELEMENT_PRESENT",
    "A": "FLAGGED_SUSPECT_ACCEPTED_AS_GOOD_VALUE",
    "C": "AWOS_WHOLE_DEGREE_TEMPERATURE_ACCEPTED_AS_VALID",
    "I": "INSERTED_BY_VALIDATOR",
    "M": "MANUAL_CHANGE_FROM_NWS_OR_FAA_INFORMATION",
    "P": "REPLACED_BY_VALIDATOR_NOT_ORIGINALLY_SUSPECT",
    "R": "REPLACED_WITH_NCEI_COMPUTED_VALUE",
    "U": "REPLACED_WITH_EDITED_VALUE",
}
QUALITY_ABSENT = "QUALITY_CODE_ABSENT"
QUALITY_UNDOCUMENTED = "UNDOCUMENTED_QUALITY_CODE"
SUSPECT_OR_ERRONEOUS = ("2", "3", "6", "7")
#: Official geophysical report type meanings (ISD format document, control data section POS 42-46).
REPORT_TYPE_MEANINGS = {
    "AERO": "AEROLOGICAL_REPORT", "AUST": "DATASET_FROM_AUSTRALIA", "AUTO": "AUTOMATIC_STATION_REPORT",
    "BOGUS": "BOGUS_REPORT", "BRAZ": "DATASET_FROM_BRAZIL", "COOPD": "US_COOPERATIVE_SUMMARY_OF_DAY",
    "COOPS": "US_COOPERATIVE_SOIL_TEMPERATURE", "CRB": "CLIMATE_REFERENCE_BOOK_CDMP",
    "CRN05": "CLIMATE_REFERENCE_NETWORK_5_MINUTE", "CRN15": "CLIMATE_REFERENCE_NETWORK_15_MINUTE",
    "FM-12": "SYNOP_FIXED_LAND_STATION", "FM-13": "SHIP_SEA_STATION", "FM-14": "SYNOP_MOBIL_LAND_STATION",
    "FM-15": "METAR_AVIATION_ROUTINE", "FM-16": "SPECI_AVIATION_SPECIAL", "FM-18": "BUOY",
    "GREEN": "DATASET_FROM_GREENLAND", "MESOH": "MESONET_HYDROLOGICAL", "MESOS": "MESONET",
    "MESOW": "MESONET_SNOW", "MEXIC": "DATASET_FROM_MEXICO", "NSRDB": "NATIONAL_SOLAR_RADIATION_DATA_BASE",
    "PCP15": "US_15_MINUTE_PRECIPITATION", "PCP60": "US_60_MINUTE_PRECIPITATION",
    "S-S-A": "SYNOPTIC_AIRWAYS_AUTO_MERGED", "SA-AU": "AIRWAYS_AUTO_MERGED", "SAO": "AIRWAYS_REPORT",
    "SAOSP": "AIRWAYS_SPECIAL_REPORT", "SHEF": "STANDARD_HYDROLOGIC_EXCHANGE_FORMAT",
    "SMARS": "SUPPLEMENTARY_AIRWAYS_STATION", "SOD": "SUMMARY_OF_DAY_NOT_INSTANTANEOUS",
    "SOM": "SUMMARY_OF_MONTH_NOT_INSTANTANEOUS", "SURF": "SURFACE_RADIATION_NETWORK",
    "SY-AE": "SYNOPTIC_AERO_MERGED", "SY-AU": "SYNOPTIC_AUTO_MERGED", "SY-MT": "SYNOPTIC_METAR_MERGED",
    "SY-SA": "SYNOPTIC_AIRWAYS_MERGED", "WBO": "WEATHER_BUREAU_OFFICE", "WNO": "WASHINGTON_NAVAL_OBSERVATORY",
    "99999": "MISSING_REPORT_TYPE",
}
REPORT_TYPE_UNDOCUMENTED = "UNDOCUMENTED_REPORT_TYPE"
SUMMARY_REPORT_TYPES = ("COOPD", "SOD", "SOM")
#: The governed raw columns a selected-row witness keeps (plus every non-empty AA* precipitation column).
WITNESS_COLUMNS = ("STATION", "DATE", "SOURCE", "LATITUDE", "LONGITUDE", "ELEVATION", "NAME", "REPORT_TYPE",
                   "CALL_SIGN", "QUALITY_CONTROL", "WND", "VIS", "TMP", "DEW", "SLP")
QUALITY_VARIABLES = ("temperature", "dew_point", "wind_direction", "wind_speed", "visibility", "sea_level_pressure")
#: The six decoded common fields counted by the duplicate ranking.
COMMON_FIELDS = ("temperature_c", "dew_point_c", "visibility_m", "sea_level_pressure_hpa", "wind_direction_degrees",
                 "wind_speed_mps")
#: The decoded observation fields of a row (the pilot's ``nearest_*`` suffixes, in its order).
OBSERVATION_FIELDS = (
    ("observed_at_utc", "s?"), ("report_type", "s?"), ("source_code", "s?"), ("source_row_number", "i?"),
    ("decoded_common_field_count", "i?"), ("temperature_c", "f?"), ("temperature_quality", "s?"),
    ("dew_point_c", "f?"), ("dew_point_quality", "s?"), ("wind_direction_degrees", "i?"),
    ("wind_direction_quality", "s?"), ("wind_type_code", "s?"), ("wind_speed_mps", "f?"), ("wind_speed_quality", "s?"),
    ("visibility_m", "f?"), ("visibility_quality", "s?"), ("sea_level_pressure_hpa", "f?"),
    ("sea_level_pressure_quality", "s?"), ("precipitation_raw_json", "s?"), ("raw_tmp", "s?"), ("raw_dew", "s?"),
    ("raw_wnd", "s?"), ("raw_vis", "s?"), ("raw_slp", "s?"))
OBSERVATION_NAMES = tuple(name for name, _t in OBSERVATION_FIELDS)
#: The 59 original pilot columns in their Parquet order with their exact JSON types (nullable as stored).
ORIGINAL_PILOT_FIELDS = (
    ("schema_version", "s?"), ("classification", "s?"), ("football_season", "i?"), ("source_game_id", "s?"),
    ("canonical_game_id_candidate", "s?"), ("kickoff_at_utc", "s?"), ("home_team", "s?"), ("away_team", "s?"),
    ("venue_id", "s?"), ("venue_name", "s?"), ("venue_dome", "b?"), ("calendar_year", "i?"), ("station_id", "s?"),
    ("station_name", "s?"), ("station_latitude", "f?"), ("station_longitude", "f?"), ("distance_km", "f?"),
    ("station_file_id", "s?"), ("station_rank", "i?"), ("station_acceptance_state", "s?"),
    ("station_snapshot_id", "s?"), ("station_raw_sha256", "s?"), ("station_request_identity_sha256", "s?"),
    ("before_observed_at_utc", "s?"), ("before_delta_minutes", "f?"), ("after_observed_at_utc", "s?"),
    ("after_delta_minutes", "f?"), ("nearest_observation_state", "s?"), ("nearest_absolute_delta_minutes", "f?"),
    ("observed_weather_substitution", "b?"), ("historical_pit_eligible", "b?"), ("training_feature_eligible", "b?"),
    ("protected_eligible", "b?"), ("dome_observation_feature_eligible", "b?"),
    *((f"nearest_{name}", code) for name, code in OBSERVATION_FIELDS), ("row_lineage_sha256", "s?"))
ORIGINAL_NAMES = tuple(name for name, _t in ORIGINAL_PILOT_FIELDS)
ORIGINAL_TYPES = dict(ORIGINAL_PILOT_FIELDS)
#: The governed observation fields the reconstruction re-derives (``verified_<field>`` beside ``original_<field>``).
GOVERNED_FIELDS = ("before_observed_at_utc", "before_delta_minutes", "after_observed_at_utc", "after_delta_minutes",
                   "nearest_observation_state", "nearest_absolute_delta_minutes",
                   *(f"nearest_{name}" for name in OBSERVATION_NAMES))
#: Original constants of every pilot row (the frozen pilot contract; never promoted).
ORIGINAL_CONSTANTS = {"schema_version": "1.0.0",
                      "classification": "PRELIMINARY_UNPROTECTED_OBSERVED_GAME_TIME_SHADOW_CANDIDATE",
                      "football_season": FOOTBALL_SEASON, "station_rank": 1,
                      "station_acceptance_state": "CANDIDATE_REVIEW_REQUIRED"}
#: Original eligibility flags; each must stay false (forecast substitution, PIT/training/protected, dome feature).
ORIGINAL_FALSE_FLAGS = {"observed_weather_substitution": "WEATHER_FORECAST_CLAIM_INVALID",
                        "historical_pit_eligible": "WEATHER_PIT_CLAIM_INVALID",
                        "training_feature_eligible": "WEATHER_PIT_CLAIM_INVALID",
                        "protected_eligible": "WEATHER_PIT_CLAIM_INVALID",
                        "dome_observation_feature_eligible": "WEATHER_ROOF_CLAIM_INVALID"}
#: Original fields the reconstruction re-derives besides the governed observation fields.
CHECKED_ORIGINAL_FIELDS = ("calendar_year", "station_file_id", "station_snapshot_id", "station_raw_sha256",
                           "station_request_identity_sha256", "row_lineage_sha256", "kickoff_at_utc", "home_team",
                           "away_team", "venue_id", "venue_name", "venue_dome", "canonical_game_id_candidate",
                           "station_name", "station_latitude", "station_longitude", "distance_km")
#: Parent contest fields projected exactly (never a score, margin or result).
PARENT_FIELDS = (("contest_key", "s"), ("ncaa_contest_id", "s?"), ("season", "i"), ("term", "s"),
                 ("contest_date", "s"), ("contest_status", "s"), ("competitive", "i?"), ("site", "s"),
                 ("neutral_site_text", "s?"), ("classification_pair", "s"), ("a_key", "s?"), ("a_team_name", "s?"),
                 ("a_division_label", "s?"), ("a_membership", "s?"), ("b_key", "s?"), ("b_team_name", "s?"),
                 ("b_division_label", "s?"), ("b_membership", "s?"), ("disposition", "s"),
                 ("disposition_reason", "s?"), ("reconciliation_state", "s?"), ("exposure", "s?"))
PARENT_COLUMNS = tuple(name for name, _t in PARENT_FIELDS)
#: Fields that would carry an outcome; none may appear in any record.
FORBIDDEN_FIELDS = ("a_points", "b_points", "home_points", "away_points", "homePoints", "awayPoints", "points",
                    "score", "scores", "margin", "result", "winner", "outcome", "mirror_scores_observed",
                    "homeLineScores", "awayLineScores", "excitementIndex", "homePostgameWinProbability",
                    "awayPostgameWinProbability", "homePostgameElo", "awayPostgameElo", "attendance")

RELATION_STATES = ("PROMOTED_ONE_TO_ONE", "CANDIDATE_NOT_PROMOTED", "NO_PROVIDER_ROW")
SUPPORT_STATES = ("ASSOCIATED_CANDIDATE_STATION_OBSERVATION", "ASSOCIATED_NO_OBSERVATION",
                  "UNSUPPORTED_RELATION_NOT_PROMOTED", "UNSUPPORTED_NO_PROVIDER_ROW")
PROVIDER_JOIN_STATES = ("EXACT_CAPTURED_PROVIDER_GAME", "PROVIDER_GAME_NOT_CAPTURED")
CLOCK_AGREEMENT_STATES = ("AGREE", "DIFFER", "NOT_COMPARABLE")
RECONSTRUCTION_STATES = ("REPRODUCED_EXACT", "DISCREPANT")
MISSING_REASONS = {"before": "NO_EARLIER_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE",
                   "after": "NO_LATER_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE"}
WITNESS_KINDS = ("INPUT", "PARENT_CONTRACT", "RAW_FILE", "SELECTED_RAW_ROW")
SELECTION_ROLES = ("BEFORE", "AFTER", "NEAREST")
#: Every unsupported reason a contest or pilot record may carry (a closed vocabulary; each one is re-derived).
UNSUPPORTED_REASONS = (
    "NO_PROMOTED_ONE_TO_ONE_PROVIDER_RELATION", "NO_PROVIDER_ROW_OUTSIDE_FBS_ROUTE",
    "PROVIDER_CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE", "ALIAS_FIELD_CONFLICT_RETAINED",
    "PARENT_CONTEST_NOT_COMPLETED", "PROMOTED_RELATION_WITHOUT_PILOT_ROW", "PROVIDER_GAME_NOT_CAPTURED",
    "STATION_MEASUREMENT_NOT_STADIUM_CONDITION", "CANDIDATE_STATION_NOT_ACCEPTED",
    "PROVIDER_SCHEDULED_TIME_NOT_ACTUAL_KICKOFF", "CATALOG_VENUE_AND_ROOF_NOT_HISTORICAL_EFFECTIVE",
    "OBSERVED_RECORD_NOT_FORECAST_NOT_PIT", "CATALOG_DOME_FLAG_ROOF_STATE_UNKNOWN", "PROVIDER_START_TIME_TBD",
    "ASSOCIATION_CLOCK_DIFFERS_FROM_PROVIDER_CAPTURE", "NO_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE",
    "NO_EARLIER_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE", "NO_LATER_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE",
    "NEAREST_OBSERVATION_IS_SUMMARY_NOT_INSTANTANEOUS", "NEAREST_OBSERVATION_HAS_NO_DECODED_COMMON_FIELD",
    "NEAREST_VALUE_FLAGGED_SUSPECT_OR_ERRONEOUS", "ORIGINAL_PILOT_FIELD_DISCREPANCY")
GENERAL_ASSOCIATION_REASONS = ("STATION_MEASUREMENT_NOT_STADIUM_CONDITION", "CANDIDATE_STATION_NOT_ACCEPTED",
                               "PROVIDER_SCHEDULED_TIME_NOT_ACTUAL_KICKOFF",
                               "CATALOG_VENUE_AND_ROOF_NOT_HISTORICAL_EFFECTIVE", "OBSERVED_RECORD_NOT_FORECAST_NOT_PIT")
NEAREST_SUMMARY = ("temperature_c", "temperature_quality", "dew_point_c", "dew_point_quality", "wind_direction_degrees",
                   "wind_direction_quality", "wind_type_code", "wind_speed_mps", "wind_speed_quality", "visibility_m",
                   "visibility_quality", "sea_level_pressure_hpa", "sea_level_pressure_quality",
                   "precipitation_raw_json")

# --------------------------------------------------------------------------------------------- record shapes

_LABEL_TYPES = {k: "s" for k in LABELS}


def _labels_types(table: str) -> dict[str, str]:
    return {"record_type": "s", **{k: "s" for k in GRAIN_LABEL_KEYS[table]}}


FIELD_TYPES: dict[str, dict[str, str]] = {
    "contests": {
        **_labels_types("contests"),
        **{name: code for name, code in PARENT_FIELDS if name not in ("disposition", "disposition_reason",
                                                                      "reconciliation_state", "exposure")},
        "contest_calendar_year": "i", "parent_disposition": "s", "parent_disposition_reason": "s?",
        "parent_reconciliation_state": "s?", "parent_exposure": "s?",
        "alias_disposition": "s", "alias_disposition_reason": "s?", "alias_route_scope": "s?",
        "alias_field_conflicts": "ls", "alias_candidate_provider_row_keys": "ls",
        "alias_relation_provider_row_key": "s?", "alias_relation_provider_game_id": "s?",
        "relation_state": "s", "provider_row_key": "s?", "provider_game_id": "s?", "pilot_key": "s?",
        "weather_support_state": "s", "station_year_key": "s?", "station_id": "s?", "station_name": "s?",
        "station_distance_km": "f?", "station_elevation_m": "f?", "association_clock_utc": "s?",
        "provider_start_time_tbd": "b?", "nearest_observed_at_utc": "s?", "nearest_absolute_delta_minutes": "f?",
        "nearest_report_type": "s?", "nearest_report_meaning": "s?", "before_present": "b?", "after_present": "b?",
        **{name: ORIGINAL_TYPES[f"nearest_{name}"] for name in NEAREST_SUMMARY},
        "reference_venue_id": "s?", "reference_venue_name": "s?", "reference_venue_dome": "b?",
        "unsupported_reasons": "ls"},
    "pilots": {
        **_labels_types("pilots"), "pilot_key": "s", "original_row_index": "i",
        **{f"original_{name}": code for name, code in ORIGINAL_PILOT_FIELDS},
        "provider_join_state": "s", "provider_row_key": "s?", "provider_game_id": "s?",
        "provider_scheduled_start_utc": "s?", "provider_start_time_tbd": "b?", "provider_neutral_site": "b?",
        "provider_venue_id": "s?", "provider_venue_name": "s?", "provider_season_type": "s?", "provider_week": "i?",
        "kickoff_clock_agreement": "s", "relation_state": "s", "relation_disposition": "s?",
        "relation_disposition_reason": "s?", "contest_key": "s?", "candidate_contest_key": "s?",
        "station_year_key": "s",
        **{f"verified_{name}": ORIGINAL_TYPES[name] for name in GOVERNED_FIELDS},
        "verified_before_source_row_number": "i?", "verified_after_source_row_number": "i?",
        "reconstruction_state": "s", "discrepant_fields": "ls",
        "before_witness_key": "s?", "after_witness_key": "s?", "nearest_witness_key": "s?",
        "before_missing_reason": "s?", "after_missing_reason": "s?", "adjacent_calendar_year_captured": "b",
        "nearest_report_meaning": "s?",
        **{f"{v}_quality_meaning": "s?" for v in QUALITY_VARIABLES},
        "nearest_precipitation_groups": "i?", "unsupported_reasons": "ls"},
    "station_years": {
        **_labels_types("station_years"), "station_year_key": "s", "calendar_year": "i", "station_id": "s",
        "station_file_id": "s", "raw_relative_path": "s", "raw_sha256": "s", "raw_bytes": "i",
        "request_identity_sha256": "s", "snapshot_id": "s", "source_uri": "s", "capture_reuse_state": "s?",
        "header_columns": "ls", "header_sha256": "s", "data_rows": "i", "malformed_rows": "i",
        "distinct_timestamps": "i", "duplicate_timestamp_rows": "i", "station_value_check": "s",
        "calendar_year_check": "s", "first_observed_at_utc": "s?", "last_observed_at_utc": "s?",
        "report_type_rows": "di", "decoded_rows": "di", "sentinel_rows": "di", "quality_code_rows": "ddi",
        "precipitation_rows": "i", "csv_station_names": "ls", "csv_coordinates": "ls",
        "candidate_station_name": "s?", "candidate_station_latitude": "f?", "candidate_station_longitude": "f?",
        "candidate_station_elevation_m": "f?", "candidate_station_icao": "s?", "candidate_station_country": "s?",
        "candidate_station_state": "s?", "candidate_station_begin": "s?", "candidate_station_end": "s?",
        "candidate_venue_ids": "ls", "station_reference_state": "s", "pilot_keys": "ls", "pilot_rows": "i",
        "observation_clock": "s", "capture_manifest_issued_at_utc": "s", "acquisition_issued_at_utc": "s?",
        "source_publication_time": "s", "rights_source_id": "s", "rights_decision_id": "s",
        "raw_redistribution": "s"},
    "witnesses": {
        **_labels_types("witnesses"), "witness_key": "s", "witness_kind": "s", "relative_path": "s?",
        "sha256": "s?", "bytes": "i?", "role": "s?", "rows": "i?", "dataset_identity": "s?", "issued_at_utc": "s?",
        "source_id": "s?", "station_year_key": "s?", "station_id": "s?", "source_row_number": "i?",
        "raw_row_sha256": "s?", "raw_fields": "dss?",
        **{f"row_{name}": code for name, code in OBSERVATION_FIELDS
           if name not in ("source_row_number", "raw_tmp", "raw_dew", "raw_wnd", "raw_vis", "raw_slp")},
        "timestamp_candidates": "lc?", "selected_by": "ls"},
    "census": {
        **_labels_types("census"), "contests": "i", "pilots": "i", "station_years": "i", "witnesses": "i",
        "selected_raw_rows": "i", "contests_by_relation_state": "di", "contests_by_support_state": "di",
        "contests_by_calendar_year": "di", "contests_by_classification_pair": "di", "promoted_relations": "i",
        "unpromoted_relations": "i", "parents_without_promoted_weather": "i", "pilots_by_calendar_year": "di",
        "pilots_by_reconstruction_state": "di", "pilots_by_kickoff_clock_agreement": "di",
        "pilots_by_nearest_report_type": "di", "within_30_minutes": "i", "within_30_and_promoted": "i",
        "within_30_not_promoted": "i", "promoted_not_within_30": "i", "before_missing": "i", "after_missing": "i",
        "adjacent_calendar_year_captured": "i", "dome_reference_rows": "i", "provider_start_time_tbd": "i",
        "suspect_or_erroneous_nearest": "i", "summary_nearest": "i", "discrepant_pilots": "i", "raw_rows": "i",
        "raw_bytes": "i", "raw_report_type_rows": "di", "raw_duplicate_timestamp_rows": "i",
        "raw_malformed_rows": "i"},
}
RECORD_FIELDS = {table: tuple(types) for table, types in FIELD_TYPES.items()}
RECORD_TYPES = {"contests": "CONTEST_WEATHER", "pilots": "PILOT_WEATHER", "station_years": "STATION_YEAR",
                "witnesses": "SOURCE_WITNESS", "census": "CENSUS"}
RECORD_TABLES = ("contests", "pilots", "station_years", "witnesses")
KEY_FIELDS = {"contests": "contest_key", "pilots": "pilot_key", "station_years": "station_year_key",
              "witnesses": "witness_key"}
TABLE_LABELS = {"contests": "CONTEST", "pilots": "PILOT", "station_years": "STATION_YEAR", "witnesses": "WITNESS"}
ORDERING = {
    "contests": "contest_date, contest_key",
    "pilots": "original kickoff_at_utc, source_game_id (the original pilot's order; original_row_index)",
    "station_years": "calendar_year, station_id",
    "witnesses": "inputs in contract order, parent contracts in contract order, raw files in station-year order, then "
                 "selected raw rows by station-year order and CSV row number",
}

# --------------------------------------------------------------------------------------------- layout and serving

SEGMENTS = {"contests": ("2024", "2025"), "pilots": ("2024", "2025"), "station_years": ("2024", "2025"),
            "witnesses": ("SOURCE", "2024", "2025")}
LAYOUT = {
    "grains": {"contests": "one record per accepted 2024 parent contest (contest_key = ncaa:<id>, or the parent's "
                           "nolink:2024:<date>:org:<a>|org:<b> key of a contest without an NCAA contest ID)",
               "pilots": "one record per original pilot row (pilot_key = the SRC-002 source_game_id)",
               "station_years": "one record per retained capture (<calendar_year>|<station_id>)",
               "witnesses": "INPUT|<name>, CONTRACT|<path>, RAW|<station-year>, ROW|<station-year>|<csv row>",
               "census": "one record"},
    "ordering": ORDERING,
    "serialization": "canonical JSON lines (sorted keys, separators ',' ':', UTF-8, no ASCII escaping); one zlib "
                     "level-9 block per table segment in the database; no separate payload files",
    "segments": {"contests": "contest_calendar_year", "pilots": "original_calendar_year",
                 "station_years": "calendar_year", "witnesses": "SOURCE for inputs, contracts and raw files; the "
                                                                  "station-year calendar year for selected rows"},
    "database": {"ddl": [list(d) for d in (
        ("table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"),
        ("table", "blocks", "CREATE TABLE blocks (ord INTEGER PRIMARY KEY, record_table TEXT NOT NULL, "
                            "segment TEXT NOT NULL, records INTEGER NOT NULL, first_key TEXT, last_key TEXT, "
                            "lines_sha256 TEXT NOT NULL, block BLOB NOT NULL)"))],
                 "block_layout": [*[[t, s] for t in RECORD_TABLES for s in SEGMENTS[t]], ["census", "GLOBAL"]],
                 "page_size": 4096, "journal_mode": "OFF", "file": DB_FILE},
    "identity_documents": {
        "content": ["schema", "stage", "population", "contract_id", "contract_sha256", "inputs", "parent_contracts",
                    "rules_sha256", "payload_schema", "row_counts", "lines_sha256", "blocks"],
        "database": ["schema", "stage", "population", "contract_sha256", "content_identity", "db_schema_version",
                     "outputs", "table_counts"],
        "identity": "SHA-256 of the canonical JSON bytes of the document; compared as canonical bytes, never by "
                    "Python equality (13.0, booleans and extra members differ)",
        "location": "<root>/canonical/national_observed_weather_evidence_2024/sha256/<database identity>/"
                    "national_observed_weather_evidence.sqlite; manifest at <root>/manifests/"
                    "national_observed_weather_evidence_2024/sha256/<database identity>/run_manifest.json with members "
                    "identity, identity_document, content_identity, content_document and provenance; create-only "
                    "(identical rebuild ALREADY_PRESENT_IDENTICAL, differing bytes REFUSED_IMMUTABLE_COLLISION)"},
    "checkpoint_unit": "one station-year capture: its station-year record, the selections of every pilot row it "
                       "serves and their selected raw-row witnesses; contests, the other witnesses and the census "
                       "follow",
}
GRAINS = {"contest-weather": "contests", "pilot-weather": "pilots", "station-year": "station_years",
          "source-witness": "witnesses"}
#: TP60 section 4: the complete allowed-selector matrix; any other selector on a grain is refused (FILTER_NOT_APPLICABLE).
SELECTOR_MATRIX = {
    "contest-weather": ["season", "contest", "provider_game", "station"],
    "pilot-weather": ["season", "contest", "provider_game", "station"],
    "station-year": ["season", "station"],
    "source-witness": ["season", "station"],
}
SELECTORS = {
    "season": "an integer football season; the release covers 2024 only (calendar 2024 and the 11 January 2025 "
              "games); any other season serves no row with SEASON_OUTSIDE_RELEASE",
    "contest": "an exact parent contest key ncaa:<1-12 digits> or nolink:2024:<YYYY-MM-DD>:org:<digits>|org:<digits> "
               "(bare digits are refused: an NCAA number never equals a provider number); contest grain: "
               "contest_key; pilot grain: the promoted contest_key only (never the unpromoted candidate)",
    "provider_game": "an exact SRC-002 provider game ID (1-12 digits); contest grain: the promoted provider_game_id "
                     "only; pilot grain: provider_game_id",
    "station": "an exact NOAA ISD station identity NNNNNN-NNNNN (USAF-WBAN); contest grain: the associated station; "
               "pilot grain: the original station_id; station-year: station_id; witness: the selected row's or raw "
               "file's station (inputs and contracts carry none)",
    "paging": "--limit (default 50, non-negative), --offset (non-negative) or --all; exact totals in record order",
    "intersection": "selectors intersect; an unknown or disjoint valid selection serves no row; malformed or "
                    "inapplicable selectors are refused before any file is read",
    "pit": "--require-pit is always refused; no historical as-of selector is offered",
    "matrix": SELECTOR_MATRIX,
}
SCOPE = {
    "population": "all 1,672 accepted 2024 parent contests (FBS/FCS and recorded outside-division opponents), all 920 "
                  "retained observed-weather pilot rows and all 157 retained NOAA ISD station-year captures (11 "
                  "football-season-2024 games dated in calendar 2025 included)",
    "horizon": "retrospective research on observed station records; no forecast vintage, PIT admission, actual "
               "kickoff, actual stadium condition, historical effective venue or roof state, model use or predictive "
               "skill",
    "not_audited": "other seasons, alternate or non-rank-one stations, forecast weather, travel/rest/time-zone "
                   "context and every other domain (BAT-417/BAT-419 remain open)",
}
#: TP60 section 4 error semantics: every refusal is exit 2 with one JSON line {"refused": CODE, "error": text} on
#: stderr and no row; checks run in a fixed order so each forgery is refused for its own cause.
REFUSALS = {
    "exit_code": 2,
    "stderr": "one JSON object with members refused (the code) and error (the text); nothing on stdout",
    "selection": ["ARGUMENT_INVALID", "UNKNOWN_GRAIN", "FILTER_NOT_APPLICABLE", "SEASON_INVALID", "CONTEST_INVALID",
                  "PROVIDER_GAME_INVALID", "STATION_INVALID", "LIMIT_INVALID", "OFFSET_INVALID", "NEGATIVE_LIMIT",
                  "NEGATIVE_OFFSET", "WEATHER_PIT_NOT_ADMITTED", "STALE_WEATHER_IDENTITY"],
    "location": ["DATABASE_LOCATION_UNSUPPORTED", "DATABASE_LOCATION_NOT_LITERAL",
                 "WEATHER_MANIFEST_LOCATION_UNSUPPORTED", "WEATHER_MANIFEST_LOCATION_NOT_LITERAL",
                 "WEATHER_DATABASE_MISSING", "WEATHER_LOCATION_INVALID", "WEATHER_MANIFEST_MISSING",
                 "WEATHER_DATABASE_UNREADABLE"],
    "manifest_and_identity": ["WEATHER_MANIFEST_MALFORMED", "WEATHER_IDENTITY_MISMATCH", "WEATHER_SCHEMA_UNSUPPORTED",
                              "WEATHER_IDENTITY_DOCUMENT_MISMATCH", "WEATHER_DATABASE_TAMPERED",
                              "WEATHER_CONTRACT_MISMATCH", "WEATHER_CONTENT_IDENTITY_MISMATCH",
                              "WEATHER_PROFILE_MISMATCH"],
    "meta": ["WEATHER_META_MISMATCH", "WEATHER_META_MALFORMED", "WEATHER_PIT_CLAIM_INVALID",
             "WEATHER_LABEL_CLAIM_INVALID", "WEATHER_PARENT_MISMATCH", "WEATHER_RULES_CLAIM_INVALID",
             "WEATHER_COUNT_MISMATCH"],
    "blocks_and_records": ["WEATHER_INDEX_MISMATCH", "WEATHER_RECORD_TYPE_INVALID", "WEATHER_RECORD_MALFORMED",
                           "WEATHER_FORBIDDEN_FIELD_PRESENT", "WEATHER_RECORD_SHAPE_INVALID",
                           "WEATHER_FIELD_TYPE_INVALID", "WEATHER_RECORD_NOT_CANONICAL"],
    "collections": ["WEATHER_DUPLICATE_ROW", "WEATHER_ORDER_MISMATCH",
                    *[f"WEATHER_{label}_{kind}" for label in TABLE_LABELS.values()
                      for kind in ("ROW_MISSING", "ROW_EXTRA", "KEYS_MISMATCH")]],
    "rules": ["WEATHER_KEY_INVALID", "WEATHER_SEASON_OUT_OF_RANGE", "WEATHER_CALENDAR_YEAR_MISMATCH",
              "WEATHER_STATION_YEAR_MISMATCH", "WEATHER_STATION_YEAR_COUNT_INVALID", "WEATHER_SOURCE_CLOCK_MISMATCH",
              "WEATHER_RIGHTS_MISMATCH", "WEATHER_WITNESS_MISMATCH", "WEATHER_TRANSPLANT", "WEATHER_DECODE_MISMATCH",
              "WEATHER_DUPLICATE_RANKING_INVALID", "WEATHER_WITNESS_LINK_MISMATCH", "WEATHER_FORECAST_CLAIM_INVALID",
              "WEATHER_ROOF_CLAIM_INVALID", "WEATHER_ORIGINAL_ALTERED", "WEATHER_ORIGINAL_CLAIM_INVALID",
              "WEATHER_PROVIDER_JOIN_MISMATCH", "WEATHER_RELATION_MISMATCH", "WEATHER_DELTA_MISMATCH",
              "WEATHER_CANDIDATE_ORDER_INVALID", "WEATHER_TIE_RULE_VIOLATED", "WEATHER_NEAREST_MISMATCH",
              "WEATHER_MISSING_REASON_INVALID", "WEATHER_DISCREPANCY_MISMATCH", "WEATHER_MEANING_MISMATCH",
              "WEATHER_UNSUPPORTED_REASON_MISMATCH", "WEATHER_PARENT_FIELD_MISMATCH", "WEATHER_ASSOCIATION_MISMATCH",
              "WEATHER_SUPPORT_STATE_INVALID", "WEATHER_CENSUS_MISMATCH"],
    "malformed_json_reasons": ["JSON_LONE_SURROGATE", "JSON_NESTING_TOO_DEEP", "JSON_NONFINITE_NUMBER",
                               "JSON_INTEGER_TOO_LONG"],
    "build_inputs": ["WEATHER_DATA_ROOT_MISSING", "WEATHER_DATA_ROOT_LOCATION_UNSUPPORTED",
                     "WEATHER_DATA_ROOT_LOCATION_NOT_LITERAL", "WEATHER_INPUT_LOCATION_UNSUPPORTED",
                     "WEATHER_INPUT_LOCATION_NOT_LITERAL", "WEATHER_INPUT_MISSING", "WEATHER_INPUT_TAMPERED",
                     "WEATHER_INPUT_UNREADABLE", "WEATHER_INPUT_MALFORMED", "WEATHER_INPUT_POPULATION_DRIFT",
                     "WEATHER_DECODER_UNAVAILABLE", "WEATHER_CAPTURE_MISMATCH", "WEATHER_RAW_IDENTITY_MISMATCH"],
}

# --------------------------------------------------------------------------------------------- refusals


class WeatherError(ValueError):
    """A refused build input or a refused weather evidence release; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise WeatherError(code, message)


#: Malformed data at the reader's untrusted JSON boundaries (block records, meta claims, the run manifest): an escaped
#: lone surrogate decodes but is not Unicode text, and nesting can exceed the JSON decoder or encoder depth. Each boundary
#: refuses it with its own code and one of these reasons, never with a traceback (the C58/C59 boundary rule).
JSON_LONE_SURROGATE = "JSON_LONE_SURROGATE"
JSON_NESTING_TOO_DEEP = "JSON_NESTING_TOO_DEEP"
JSON_NONFINITE_NUMBER = "JSON_NONFINITE_NUMBER"
JSON_INTEGER_TOO_LONG = "JSON_INTEGER_TOO_LONG"


def _nesting_refusal(code: str, where: str) -> WeatherError:
    return WeatherError(code, f"{where}: {JSON_NESTING_TOO_DEEP} (deeper than the JSON decoder or encoder accepts)")


def _untrusted_canonical(value: Any, code: str, where: str) -> bytes:
    try:
        return canonical_json_bytes(value)
    except UnicodeEncodeError as exc:
        raise WeatherError(code, f"{where}: {JSON_LONE_SURROGATE} (U+{ord(exc.object[exc.start]):04X} is not "
                                 "Unicode text)") from exc
    except RecursionError as exc:
        raise _nesting_refusal(code, where) from exc


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
    """Decode JSON from the release: NaN, Infinity, a float literal beyond binary64 range and an integer beyond the
    interpreter's digit limit are malformed data refused with ``code`` and their reason (never accepted, never a
    traceback); other syntax errors are refused with ``non_json_code`` (default ``code``)."""
    try:
        return json.loads(text, parse_float=_finite_float, parse_constant=_no_constant)
    except _InvalidNumber as exc:
        raise WeatherError(code, f"{where}: {JSON_NONFINITE_NUMBER} ({exc})") from exc
    except RecursionError as exc:
        raise _nesting_refusal(code, where) from exc
    except ValueError as exc:
        if "integer string conversion" in str(exc) or "Exceeds the limit" in str(exc):
            raise WeatherError(code, f"{where}: {JSON_INTEGER_TOO_LONG}") from exc
        raise WeatherError(non_json_code or code, f"{where}: not JSON ({exc})") from exc


def _json_or_none(text: Any, name: str = "") -> Any:
    """A meta claim's JSON value, or None when it is not JSON text (the claim's own rule then refuses it); malformed
    numbers and nesting beyond the decoder's depth are malformed meta (WEATHER_META_MALFORMED)."""
    if not isinstance(text, (str, bytes)):
        return None
    try:
        return loads_untrusted(text, "WEATHER_META_MALFORMED", f"meta {name}", non_json_code="NOT_JSON")
    except WeatherError as exc:
        if exc.code == "NOT_JSON":
            return None
        raise


def rules_document() -> dict[str, Any]:
    """Every frozen rule the contract restates (the meta ``rules`` claim and the content document's rules digest)."""
    return {"labels": LABELS, "grain_labels": {k: list(v) for k, v in GRAIN_LABEL_KEYS.items()}, "layout": LAYOUT,
            "original_selection": ORIGINAL_SELECTION, "decoding": DECODING, "quality_meanings": QUALITY_MEANINGS,
            "quality_absent": QUALITY_ABSENT, "quality_undocumented": QUALITY_UNDOCUMENTED,
            "suspect_or_erroneous": list(SUSPECT_OR_ERRONEOUS), "report_type_meanings": REPORT_TYPE_MEANINGS,
            "report_type_undocumented": REPORT_TYPE_UNDOCUMENTED, "summary_report_types": list(SUMMARY_REPORT_TYPES),
            "witness_columns": list(WITNESS_COLUMNS), "common_fields": list(COMMON_FIELDS),
            "observation_fields": [list(f) for f in OBSERVATION_FIELDS],
            "original_pilot_fields": [list(f) for f in ORIGINAL_PILOT_FIELDS], "governed_fields": list(GOVERNED_FIELDS),
            "original_constants": ORIGINAL_CONSTANTS, "original_false_flags": ORIGINAL_FALSE_FLAGS,
            "checked_original_fields": list(CHECKED_ORIGINAL_FIELDS), "parent_fields": [list(f) for f in PARENT_FIELDS],
            "forbidden_fields": list(FORBIDDEN_FIELDS), "relation_states": list(RELATION_STATES),
            "support_states": list(SUPPORT_STATES), "provider_join_states": list(PROVIDER_JOIN_STATES),
            "clock_agreement_states": list(CLOCK_AGREEMENT_STATES),
            "reconstruction_states": list(RECONSTRUCTION_STATES), "missing_reasons": MISSING_REASONS,
            "witness_kinds": list(WITNESS_KINDS), "selection_roles": list(SELECTION_ROLES),
            "unsupported_reasons": list(UNSUPPORTED_REASONS),
            "general_association_reasons": list(GENERAL_ASSOCIATION_REASONS), "nearest_summary": list(NEAREST_SUMMARY),
            "season": FOOTBALL_SEASON, "calendar_years": list(CALENDAR_YEARS),
            "sources": {"weather": WEATHER_SOURCE_ID, "provider": PROVIDER_SOURCE_ID, "parent": PARENT_SOURCE_ID},
            "field_types": FIELD_TYPES, "record_types": RECORD_TYPES, "selectors": SELECTORS, "refusals": REFUSALS,
            "scope": SCOPE}


def rules_sha256() -> str:
    return sha256_bytes(canonical_json_bytes(rules_document()))


def keys_sha256(keys: Iterable[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


from aggie_analytics.weather_evidence.anchors import ANCHORS, WEATHER_PROFILE  # noqa: E402

# --------------------------------------------------------------------------------------------- shared decoding


def parse_utc(text: str) -> datetime:
    """An ISO timestamp as UTC (a naive ISD DATE is UTC by the format definition)."""
    value = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def station_file_id(station_id: str) -> str:
    parts = str(station_id).split("-")
    if len(parts) != 2 or len(parts[0]) != 6 or len(parts[1]) != 5 or not all(p.isascii() and p.isdigit()
                                                                               for p in parts):
        _refuse("WEATHER_KEY_INVALID", f"invalid NOAA ISD station identity {station_id!r}")
    return "".join(parts)


#: The least integer magnitude without a finite binary64 value: the largest finite double (2**1024 - 2**971) plus half its
#: last unit rounds up to 2**1024, so converting a decoded raw integer to binary64 raises OverflowError from here up. A
#: scaled raw field (TMP, DEW, VIS, SLP, WND speed) at or beyond it has no decode under the frozen rules: the decoding
#: boundary refuses it (C60-CONT-01, MF60A01-01) instead of letting the conversion overflow.
BINARY64_INTEGER_BOUND = 2 ** 1024 - 2 ** 970


def _binary64_scaled(value: int, divisor: float, name: str, where: str) -> float:
    """``value / divisor`` for a decoded raw integer. An integer with no finite binary64 value cannot be the decoded
    value of any record, so it is refused as a raw decoding mismatch (``WEATHER_DECODE_MISMATCH``), never converted."""
    if not -BINARY64_INTEGER_BOUND < value < BINARY64_INTEGER_BOUND:
        _refuse("WEATHER_DECODE_MISMATCH", f"{where}: raw {name} is a {value.bit_length()}-bit integer with no finite "
                                           "binary64 value")
    return value / divisor


def _scaled(raw: str, sentinel: str, divisor: float, name: str, where: str) -> tuple[float | None, str]:
    parts = str(raw or "").split(",")
    value_text = parts[0] if parts else ""
    quality = parts[1] if len(parts) > 1 else ""
    if not value_text or value_text in (sentinel, f"+{sentinel}", f"-{sentinel}"):
        return None, quality
    try:
        value = int(value_text)
    except ValueError:
        return None, quality
    return _binary64_scaled(value, divisor, name, where), quality


def decode_row(fields: dict[str, str], row_number: int | None, where: str | None = None) -> dict[str, Any]:
    """The decoded observation of one raw row (the frozen pilot decoding; plain Python). A scaled value whose integer
    has no finite binary64 value is refused (``WEATHER_DECODE_MISMATCH``); ``where`` names the row in that refusal."""
    where = where or f"raw row {row_number}"
    temperature, temperature_quality = _scaled(fields.get("TMP"), "9999", 10.0, "TMP", where)
    dew_point, dew_point_quality = _scaled(fields.get("DEW"), "9999", 10.0, "DEW", where)
    visibility, visibility_quality = _scaled(fields.get("VIS"), "999999", 1.0, "VIS", where)
    pressure, pressure_quality = _scaled(fields.get("SLP"), "99999", 10.0, "SLP", where)
    wind = str(fields.get("WND") or "").split(",")
    direction = speed = None
    if len(wind) >= 4:
        if wind[0] and wind[0] != "999":
            try:
                direction = int(wind[0])
            except ValueError:
                direction = None
        if wind[3] and wind[3] != "9999":
            try:
                speed_value = int(wind[3])
            except ValueError:
                speed_value = None
            speed = None if speed_value is None else _binary64_scaled(speed_value, 10.0, "WND speed", where)
    precipitation = {key: value for key, value in sorted(fields.items()) if key.startswith("AA") and value}
    decoded = sum(v is not None for v in (temperature, dew_point, visibility, pressure, direction, speed))
    return {"observed_at_utc": utc_text(parse_utc(str(fields.get("DATE") or ""))),
            "report_type": str(fields.get("REPORT_TYPE") or ""), "source_code": str(fields.get("SOURCE") or ""),
            "source_row_number": row_number, "decoded_common_field_count": decoded,
            "temperature_c": temperature, "temperature_quality": temperature_quality,
            "dew_point_c": dew_point, "dew_point_quality": dew_point_quality,
            "wind_direction_degrees": direction, "wind_direction_quality": wind[1] if len(wind) > 1 else "",
            "wind_type_code": wind[2] if len(wind) > 2 else "", "wind_speed_mps": speed,
            "wind_speed_quality": wind[4] if len(wind) > 4 else "", "visibility_m": visibility,
            "visibility_quality": visibility_quality, "sea_level_pressure_hpa": pressure,
            "sea_level_pressure_quality": pressure_quality,
            "precipitation_raw_json": json.dumps(precipitation, sort_keys=True, separators=(",", ":")),
            "raw_tmp": str(fields.get("TMP") or ""), "raw_dew": str(fields.get("DEW") or ""),
            "raw_wnd": str(fields.get("WND") or ""), "raw_vis": str(fields.get("VIS") or ""),
            "raw_slp": str(fields.get("SLP") or "")}


def ranking_key(decoded_count: int, report_type: str, source_code: str, row_number: int) -> tuple[Any, ...]:
    """The frozen duplicate-timestamp ranking: most decoded common fields, then report type, source and row number."""
    return (-int(decoded_count), report_type, source_code, int(row_number))


def quality_meaning(code: Any) -> str | None:
    if code is None:
        return None
    if code == "":
        return QUALITY_ABSENT
    return QUALITY_MEANINGS.get(code, QUALITY_UNDOCUMENTED)


def report_meaning(report_type: Any) -> str | None:
    if report_type is None:
        return None
    return REPORT_TYPE_MEANINGS.get(str(report_type).strip(), REPORT_TYPE_UNDOCUMENTED)


def precipitation_groups(text: Any) -> int | None:
    if text is None:
        return None
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return len(value) if isinstance(value, dict) else None


def lineage_sha256(source_game_id: Any, kickoff: Any, station_id: Any, raw_sha: Any, nearest_at: Any) -> str:
    """The original pilot's row lineage digest (its stable_hash over the five lineage members)."""
    return sha256_bytes(json.dumps({"source_game_id": source_game_id, "kickoff_at_utc": kickoff,
                                    "station_id": station_id, "station_raw_sha256": raw_sha,
                                    "nearest_observed_at_utc": nearest_at}, sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=False).encode("utf-8"))


def select_candidates(timestamps: list[datetime], kickoff: datetime) -> tuple[int | None, int | None, int | None]:
    """The frozen before/after/nearest selection over sorted best-observation timestamps (indices)."""
    if not timestamps:
        return None, None, None
    position = bisect.bisect_left(timestamps, kickoff)
    if position < len(timestamps) and timestamps[position] == kickoff:
        before = after = position
    else:
        before = position - 1 if position > 0 else None
        after = position if position < len(timestamps) else None
    if before is None:
        nearest = after
    elif after is None:
        nearest = before
    else:
        before_delta = abs((kickoff - timestamps[before]).total_seconds())
        after_delta = abs((timestamps[after] - kickoff).total_seconds())
        nearest = before if before_delta <= after_delta else after
    return before, after, nearest


def minutes(seconds: float) -> float:
    return seconds / 60.0


def pilot_reasons(pilot: dict[str, Any]) -> list[str]:
    """Every unsupported reason of one pilot record, derived from its own fields (re-derived by the reader)."""
    reasons = set(GENERAL_ASSOCIATION_REASONS)
    if pilot["provider_join_state"] != "EXACT_CAPTURED_PROVIDER_GAME":
        reasons.add("PROVIDER_GAME_NOT_CAPTURED")
    if pilot["relation_state"] != "PROMOTED_ONE_TO_ONE":
        reasons.add("NO_PROMOTED_ONE_TO_ONE_PROVIDER_RELATION")
    if pilot["relation_disposition"] == "CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE":
        reasons.add("PROVIDER_CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE")
    if pilot["relation_disposition"] == "RECONCILED_FIELD_CONFLICT":
        reasons.add("ALIAS_FIELD_CONFLICT_RETAINED")
    if pilot["original_venue_dome"] is True:
        reasons.add("CATALOG_DOME_FLAG_ROOF_STATE_UNKNOWN")
    if pilot["provider_start_time_tbd"] is True:
        reasons.add("PROVIDER_START_TIME_TBD")
    if pilot["kickoff_clock_agreement"] != "AGREE":
        reasons.add("ASSOCIATION_CLOCK_DIFFERS_FROM_PROVIDER_CAPTURE")
    if pilot["verified_nearest_observation_state"] != "PRESENT":
        reasons.add("NO_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE")
    if pilot["verified_before_observed_at_utc"] is None:
        reasons.add("NO_EARLIER_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE")
    if pilot["verified_after_observed_at_utc"] is None:
        reasons.add("NO_LATER_OBSERVATION_IN_KICKOFF_CALENDAR_YEAR_FILE")
    report = pilot["verified_nearest_report_type"]
    if report is not None and str(report).strip() in SUMMARY_REPORT_TYPES:
        reasons.add("NEAREST_OBSERVATION_IS_SUMMARY_NOT_INSTANTANEOUS")
    if pilot["verified_nearest_decoded_common_field_count"] == 0:
        reasons.add("NEAREST_OBSERVATION_HAS_NO_DECODED_COMMON_FIELD")
    if any(pilot[f"verified_nearest_{v}_quality"] in SUSPECT_OR_ERRONEOUS for v in QUALITY_VARIABLES):
        reasons.add("NEAREST_VALUE_FLAGGED_SUSPECT_OR_ERRONEOUS")
    if pilot["reconstruction_state"] != "REPRODUCED_EXACT":
        reasons.add("ORIGINAL_PILOT_FIELD_DISCREPANCY")
    return sorted(reasons)


def contest_reasons(contest: dict[str, Any], pilot: dict[str, Any] | None) -> list[str]:
    """Every unsupported reason of one contest record (re-derived by the reader)."""
    reasons: set[str] = set()
    if contest["relation_state"] != "PROMOTED_ONE_TO_ONE":
        reasons.add("NO_PROMOTED_ONE_TO_ONE_PROVIDER_RELATION")
    if contest["relation_state"] == "NO_PROVIDER_ROW":
        reasons.add("NO_PROVIDER_ROW_OUTSIDE_FBS_ROUTE")
    if contest["alias_disposition"] == "CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE":
        reasons.add("PROVIDER_CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE")
    if contest["alias_disposition"] == "RECONCILED_FIELD_CONFLICT":
        reasons.add("ALIAS_FIELD_CONFLICT_RETAINED")
    if contest["contest_status"] != "COMPLETED":
        reasons.add("PARENT_CONTEST_NOT_COMPLETED")
    if contest["relation_state"] == "PROMOTED_ONE_TO_ONE":
        if pilot is None:
            reasons.add("PROMOTED_RELATION_WITHOUT_PILOT_ROW")
        else:
            reasons |= set(pilot["unsupported_reasons"])
    return sorted(reasons)


# --------------------------------------------------------------------------------------------- inputs

def _ordered(items: list[Any], order: str) -> list[Any]:
    """Input order variants for the determinism proof: natural, reverse or shuffle:<seed>."""
    if order == "natural":
        return list(items)
    if order == "reverse":
        return list(reversed(items))
    if order.startswith("shuffle:") and order[len("shuffle:"):].isdigit():
        out = list(items)
        random.Random(int(order[len("shuffle:"):])).shuffle(out)
        return out
    _refuse("ARGUMENT_INVALID", f"input order must be natural, reverse or shuffle:<seed>, got {order!r}")
    return []


def _literal(path: Path, code_prefix: str) -> str:
    try:
        return readonly_sqlite.literal_path(path)
    except readonly_sqlite.DatabaseLocationError as exc:
        suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
        raise WeatherError(f"{code_prefix}_LOCATION_{suffix}", exc.detail) from exc


def resolve_inputs(data_root: Path, anchors: dict[str, Any]) -> dict[str, Path]:
    """Each pinned input and raw station-year capture under the explicitly named data root, refused unless present
    with its pinned SHA-256 and byte count. The root and every resolved location pass the BAT-717 literal local-file
    policy before any access."""
    root = Path(_literal(Path(data_root), "WEATHER_DATA_ROOT"))
    if not _io_path(root).is_dir():
        _refuse("WEATHER_DATA_ROOT_MISSING", f"no data root directory at {data_root}")
    paths: dict[str, Path] = {}
    specs = [(name, spec, "WEATHER_INPUT_TAMPERED") for name, spec in anchors["inputs"].items()]
    specs += [(f"raw:{key}", spec, "WEATHER_RAW_IDENTITY_MISMATCH") for key, spec in anchors["raw"].items()]
    for name, spec, code in specs:
        location = Path(_literal(root / Path(*spec["relative_path"].split("/")), "WEATHER_INPUT"))
        if not _io_path(location).is_file():
            _refuse("WEATHER_INPUT_MISSING", f"{name}: no file at {location}")
        size = _io_path(location).stat().st_size
        actual = sha256_file(_io_path(location))
        if actual != spec["sha256"] or size != spec["bytes"]:
            _refuse(code, f"{name}: bytes hash to {actual} ({size} bytes), the contract pins {spec['sha256']} "
                          f"({spec['bytes']} bytes)")
        paths[name] = location
    return paths


def _polars() -> Any:
    try:
        import polars  # noqa: PLC0415 - the pinned optional Parquet decoder, imported only to decode inputs
    except ImportError as exc:
        raise WeatherError("WEATHER_DECODER_UNAVAILABLE", "decoding the retained Parquet inputs needs the pinned "
                                                           "polars 1.43.2 decoder") from exc
    if polars.__version__ != "1.43.2":
        _refuse("WEATHER_DECODER_UNAVAILABLE", f"polars {polars.__version__} is not the pinned decoder 1.43.2")
    return polars


def _json_file(path: Path, name: str) -> Any:
    try:
        return json.loads(_io_path(path).read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise WeatherError("WEATHER_INPUT_MALFORMED", f"{name}: {exc}") from exc


def _connect(path: Path) -> sqlite3.Connection:
    try:
        return readonly_sqlite.connect_readonly(_io_path(path), immutable=True)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise WeatherError("WEATHER_INPUT_LOCATION_UNSUPPORTED", exc.detail) from exc
    except sqlite3.Error as exc:
        raise WeatherError("WEATHER_INPUT_UNREADABLE", str(exc)) from exc


def _pilot_rows(path: Path) -> list[dict[str, Any]]:
    """The exact original pilot rows in their stored order (decoder only; columns checked against the contract)."""
    pl = _polars()
    try:
        frame = pl.read_parquet(_io_path(path))
    except Exception as exc:  # noqa: BLE001 - any decoder failure is a malformed input
        raise WeatherError("WEATHER_INPUT_MALFORMED", f"pilot payload: {exc}") from exc
    if tuple(frame.columns) != ORIGINAL_NAMES:
        _refuse("WEATHER_INPUT_MALFORMED", f"pilot columns differ from the frozen 59: {frame.columns}")
    return frame.to_dicts()


def _game_coordinates(path: Path) -> dict[str, dict[str, Any]]:
    """The original game-coordinate payload's season-2024 game fields (decoder only), one per source game."""
    pl = _polars()
    try:
        frame = pl.read_parquet(_io_path(path), columns=[
            "season", "source_game_id", "canonical_game_id_candidate", "kickoff_at_utc", "home_team", "away_team",
            "venue_id_candidate", "venue_name_current_catalog", "venue_dome_current_catalog"])
    except Exception as exc:  # noqa: BLE001
        raise WeatherError("WEATHER_INPUT_MALFORMED", f"game coordinates: {exc}") from exc
    out: dict[str, dict[str, Any]] = {}
    for row in frame.to_dicts():
        if row["season"] != FOOTBALL_SEASON:
            continue
        game = {"canonical_game_id_candidate": row["canonical_game_id_candidate"],
                "kickoff_at_utc": row["kickoff_at_utc"], "home_team": row["home_team"], "away_team": row["away_team"],
                "venue_id": row["venue_id_candidate"], "venue_name": row["venue_name_current_catalog"],
                "venue_dome": row["venue_dome_current_catalog"]}
        prior = out.setdefault(row["source_game_id"], game)
        if prior != game:
            _refuse("WEATHER_INPUT_MALFORMED", f"game coordinates disagree for game {row['source_game_id']}")
    return out


def _parents(path: Path) -> list[dict[str, Any]]:
    conn = _connect(path)
    try:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(
            f"SELECT {', '.join(PARENT_COLUMNS)} FROM contest WHERE season = ?", (FOOTBALL_SEASON,))]
    except sqlite3.Error as exc:
        raise WeatherError("WEATHER_INPUT_MALFORMED", f"parent population: {exc}") from exc
    finally:
        conn.close()
    return rows


def _alias(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    conn = _connect(path)
    try:
        parents = {ck: {**json.loads(rec), "_provider_row_key_column": pk} for ck, pk, rec in conn.execute(
            "SELECT contest_key, provider_row_key, record FROM parent_reconciliation WHERE season = ? ORDER BY ord",
            (FOOTBALL_SEASON,))}
        providers = {pk: json.loads(rec) for pk, rec in conn.execute(
            "SELECT provider_row_key, record FROM provider_reconciliation WHERE season = ? ORDER BY ord",
            (FOOTBALL_SEASON,))}
    except (sqlite3.Error, ValueError) as exc:
        raise WeatherError("WEATHER_INPUT_MALFORMED", f"alias reconciliation: {exc}") from exc
    finally:
        conn.close()
    return parents, providers


def _number(text: Any) -> float | None:
    value = str(text or "").strip()
    if not value:
        return None
    try:
        out = float(value)
    except ValueError:
        return None
    return out if math.isfinite(out) else None


def _station_candidates(path: Path) -> dict[str, dict[str, Any]]:
    """Season-2024 rank-one station candidates (the pilot's join): one metadata row per station, its venues and the
    venue-to-station distance of each venue."""
    out: dict[str, dict[str, Any]] = {}
    try:
        with _io_path(path).open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("season") != str(FOOTBALL_SEASON) or row.get("station_rank") != "1":
                    continue
                meta = {"name": row["station_name"] or None, "latitude": _number(row["station_latitude"]),
                        "longitude": _number(row["station_longitude"]),
                        "elevation_m": _number(row["station_elevation_m"]), "icao": row["station_icao"] or None,
                        "country": row["station_country"] or None, "state": row["station_state"] or None,
                        "begin": row["station_begin"] or None, "end": row["station_end"] or None}
                entry = out.setdefault(row["station_id"], {"meta": meta, "venues": set(), "distance": {}})
                if entry["meta"] != meta:
                    _refuse("WEATHER_INPUT_MALFORMED", f"station candidates disagree for {row['station_id']}")
                entry["venues"].add(row["venue_id"])
                entry["distance"][row["venue_id"]] = _number(row["distance_km"])
    except (OSError, KeyError, csv.Error) as exc:
        raise WeatherError("WEATHER_INPUT_MALFORMED", f"station candidates: {exc}") from exc
    return out


def load_inputs(data_root: Path, anchors: dict[str, Any], *, input_order: str = "natural") -> dict[str, Any]:
    """Verify and read every pinned input (raw station-year files are verified here and streamed later)."""
    paths = resolve_inputs(Path(data_root), anchors)
    parents = _parents(paths["population_database"])
    alias_parents, alias_providers = _alias(paths["alias_database"])
    provider = _json_file(paths["provider_games_2024"], "provider games 2024")
    receipt = _json_file(paths["provider_games_2024_receipt"], "provider capture receipt")
    pilot = _pilot_rows(paths["pilot_payload"])
    run_manifest = _json_file(paths["pilot_run_manifest"], "pilot run manifest")
    capture = _json_file(paths["pilot_capture_manifest"], "pilot capture manifest")
    acquisition = _json_file(paths["acquisition_2024"], "2024 acquisition manifest")
    games = _game_coordinates(paths["game_coordinates"])
    stations = _station_candidates(paths["station_candidates"])
    expected = anchors["expected"]
    if len(parents) != expected["contests"] or len(pilot) != expected["pilots"] or \
            len(capture.get("captures") or []) != expected["station_years"] or not isinstance(provider, list) or \
            len(provider) != expected["provider_rows"]:
        _refuse("WEATHER_INPUT_POPULATION_DRIFT", f"parents {len(parents)}, pilot {len(pilot)}, captures "
                                                  f"{len(capture.get('captures') or [])}, provider rows "
                                                  f"{len(provider) if isinstance(provider, list) else None}")
    if run_manifest.get("payload", {}).get("sha256") != anchors["inputs"]["pilot_payload"]["sha256"] or \
            run_manifest.get("capture_manifest_identity") != capture.get("capture_manifest_identity") or \
            receipt.get("response_sha256") != anchors["inputs"]["provider_games_2024"]["sha256"]:
        _refuse("WEATHER_CAPTURE_MISMATCH", "the pilot manifests or the provider receipt name other bytes")
    captures: dict[str, dict[str, Any]] = {}
    for cap in capture["captures"]:
        key = f"{cap['calendar_year']}|{cap['station_id']}"
        pinned = anchors["raw"].get(key)
        if pinned is None or any(cap.get(k) != pinned[k] for k in ("raw_relative_path", "raw_sha256", "raw_bytes",
                                                                    "request_identity_sha256", "snapshot_id",
                                                                    "source_uri", "station_file_id", "station_id",
                                                                    "calendar_year", "capture_reuse_state")):
            _refuse("WEATHER_CAPTURE_MISMATCH", f"capture {key} differs from the pinned raw map")
        captures[key] = cap
    if sorted(captures) != sorted(anchors["raw"]):
        _refuse("WEATHER_CAPTURE_MISMATCH", "the capture manifest and the pinned raw map name different station-years")
    acquired = {c["raw_sha256"] for c in acquisition.get("captures") or []}
    return {"paths": paths, "parents": _ordered(parents, input_order), "alias_parents": alias_parents,
            "alias_providers": alias_providers, "provider": provider, "receipt": receipt,
            "pilot": pilot, "pilot_order": _ordered(list(range(len(pilot))), input_order),
            "run_manifest": run_manifest, "capture": capture, "captures": captures, "acquisition": acquisition,
            "acquired_raw": acquired, "games": games, "stations": stations,
            "station_year_order": _ordered(sorted(captures, key=_station_year_sort), input_order)}


def _station_year_sort(key: str) -> tuple[int, str]:
    year, station = key.split("|", 1)
    return int(year), station


# --------------------------------------------------------------------------------------------- raw station-years

def _read_rows(path: Path) -> Iterable[tuple[int, list[str], list[str]]]:
    """(1-based CSV row number with the header as row 1, the header, the row's fields) for every data row."""
    with _io_path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        for number, row in enumerate(reader, start=2):
            yield number, header, row


def _mapped(header: list[str], row: list[str]) -> dict[str, str]:
    """The DictReader view of a row: header-mapped values, a missing trailing field as the empty string."""
    return {name: (row[i] if i < len(row) else "") for i, name in enumerate(header)}


def _variables(decoded: dict[str, Any]) -> dict[str, tuple[Any, str]]:
    return {"temperature": (decoded["temperature_c"], decoded["temperature_quality"]),
            "dew_point": (decoded["dew_point_c"], decoded["dew_point_quality"]),
            "wind_direction": (decoded["wind_direction_degrees"], decoded["wind_direction_quality"]),
            "wind_speed": (decoded["wind_speed_mps"], decoded["wind_speed_quality"]),
            "visibility": (decoded["visibility_m"], decoded["visibility_quality"]),
            "sea_level_pressure": (decoded["sea_level_pressure_hpa"], decoded["sea_level_pressure_quality"])}


def _sentinel_hits(fields: dict[str, str]) -> dict[str, bool]:
    def value(name: str) -> str:
        return str(fields.get(name) or "").split(",")[0]
    wind = str(fields.get("WND") or "").split(",")
    return {"temperature": value("TMP") in ("9999", "+9999", "-9999"),
            "dew_point": value("DEW") in ("9999", "+9999", "-9999"),
            "visibility": value("VIS") in ("999999", "+999999", "-999999"),
            "sea_level_pressure": value("SLP") in ("99999", "+99999", "-99999"),
            "wind_direction": len(wind) >= 4 and wind[0] == "999",
            "wind_speed": len(wind) >= 4 and wind[3] == "9999"}


def process_station_year(key: str, path: Path, capture: dict[str, Any], pilots: list[dict[str, Any]],
                         stations: dict[str, dict[str, Any]], acquired: set[str], captured_keys: set[str],
                         anchors: dict[str, Any]) -> dict[str, Any]:
    """One station-year capture streamed twice in place: the census and the best observation per timestamp, then the
    raw rows the selections of its pilot rows cite (their full duplicate ranking included)."""
    year, station = key.split("|", 1)
    file_id = station_file_id(station)
    best: dict[str, tuple[tuple[Any, ...], int]] = {}
    header: list[str] = []
    rows = malformed = precipitation = 0
    report_types: dict[str, int] = {}
    decoded_rows = {v: 0 for v in QUALITY_VARIABLES}
    sentinel_rows = {v: 0 for v in QUALITY_VARIABLES}
    quality_rows: dict[str, dict[str, int]] = {v: {} for v in QUALITY_VARIABLES}
    names: set[str] = set()
    coordinates: set[str] = set()
    station_values: set[str] = set()
    years: set[str] = set()
    for number, header, row in _read_rows(path):
        rows += 1
        if len(row) != len(header):
            malformed += 1
        fields = _mapped(header, row)
        station_values.add(fields.get("STATION", ""))
        years.add(str(fields.get("DATE", ""))[:4])
        names.add(fields.get("NAME", ""))
        coordinates.add(",".join(fields.get(c, "") for c in ("LATITUDE", "LONGITUDE", "ELEVATION")))
        decoded = decode_row(fields, number)
        report_types[decoded["report_type"]] = report_types.get(decoded["report_type"], 0) + 1
        if any(k.startswith("AA") and v for k, v in fields.items()):
            precipitation += 1
        for variable, (value, quality) in _variables(decoded).items():
            if value is not None:
                decoded_rows[variable] += 1
            quality_rows[variable][quality] = quality_rows[variable].get(quality, 0) + 1
        for variable, hit in _sentinel_hits(fields).items():
            if hit:
                sentinel_rows[variable] += 1
        stamp = decoded["observed_at_utc"]
        rank = ranking_key(decoded["decoded_common_field_count"], decoded["report_type"], decoded["source_code"],
                           number)
        current = best.get(stamp)
        if current is None or rank < current[0]:
            best[stamp] = (rank, number)
    ordered = sorted(best)
    times = [parse_utc(s) for s in ordered]
    selections: dict[str, dict[str, Any]] = {}
    needed: dict[str, list[tuple[str, str]]] = {}
    for pilot in pilots:
        kickoff = parse_utc(pilot["kickoff_at_utc"])
        before, after, nearest = select_candidates(times, kickoff)
        chosen = {"BEFORE": before, "AFTER": after, "NEAREST": nearest}
        selections[pilot["source_game_id"]] = {role: (None if index is None else ordered[index])
                                               for role, index in chosen.items()}
        for role, index in chosen.items():
            if index is not None:
                needed.setdefault(ordered[index], []).append((pilot["source_game_id"], role))
    witness_rows: dict[str, dict[str, Any]] = {}
    if needed:
        candidates: dict[str, list[tuple[tuple[Any, ...], int]]] = {s: [] for s in needed}
        raw_rows: dict[int, tuple[list[str], dict[str, str]]] = {}
        wanted = {best[s][1] for s in needed}
        for number, header_row, row in _read_rows(path):
            fields = _mapped(header_row, row)
            decoded = decode_row(fields, number)
            stamp = decoded["observed_at_utc"]
            if stamp in candidates:
                candidates[stamp].append((ranking_key(decoded["decoded_common_field_count"], decoded["report_type"],
                                                      decoded["source_code"], number), number))
            if number in wanted:
                raw_rows[number] = (row, fields)
        for stamp, citing in needed.items():
            number = best[stamp][1]
            row, fields = raw_rows[number]
            decoded = decode_row(fields, number)
            ranking = sorted(candidates[stamp])
            witness_rows[stamp] = {
                "source_row_number": number,
                "raw_row_sha256": sha256_bytes(canonical_json_bytes(row)),
                "raw_fields": {**{c: fields[c] for c in WITNESS_COLUMNS if c in fields},
                               **{c: v for c, v in fields.items() if c.startswith("AA") and v}},
                "decoded": decoded,
                "timestamp_candidates": [{"source_row_number": n, "decoded_common_field_count": -r[0],
                                          "report_type": r[1], "source_code": r[2]} for r, n in ranking],
                "selected_by": sorted(f"{g}:{role}" for g, role in citing)}
    meta = (stations.get(station) or {}).get("meta") or {}
    adjacent = {"before": f"{int(year) - 1}|{station}" in captured_keys,
                "after": f"{int(year) + 1}|{station}" in captured_keys}
    record = {
        "record_type": RECORD_TYPES["station_years"], **{k: LABELS[k] for k in GRAIN_LABEL_KEYS["station_years"]},
        "station_year_key": key, "calendar_year": int(year), "station_id": station, "station_file_id": file_id,
        "raw_relative_path": capture["raw_relative_path"], "raw_sha256": capture["raw_sha256"],
        "raw_bytes": capture["raw_bytes"], "request_identity_sha256": capture["request_identity_sha256"],
        "snapshot_id": capture["snapshot_id"], "source_uri": capture["source_uri"],
        "capture_reuse_state": capture.get("capture_reuse_state"), "header_columns": list(header),
        "header_sha256": sha256_bytes(",".join(header).encode("utf-8")), "data_rows": rows,
        "malformed_rows": malformed, "distinct_timestamps": len(best), "duplicate_timestamp_rows": rows - len(best),
        "station_value_check": "ALL_ROWS_EQUAL_FILE_ID" if station_values == {file_id} else "STATION_VALUE_MISMATCH",
        "calendar_year_check": "ALL_ROWS_IN_CALENDAR_YEAR" if years == {year} else "CALENDAR_YEAR_MISMATCH",
        "first_observed_at_utc": ordered[0] if ordered else None, "last_observed_at_utc": ordered[-1] if ordered
        else None, "report_type_rows": report_types, "decoded_rows": decoded_rows, "sentinel_rows": sentinel_rows,
        "quality_code_rows": quality_rows, "precipitation_rows": precipitation,
        "csv_station_names": sorted(names), "csv_coordinates": sorted(coordinates),
        "candidate_station_name": meta.get("name"), "candidate_station_latitude": meta.get("latitude"),
        "candidate_station_longitude": meta.get("longitude"), "candidate_station_elevation_m": meta.get("elevation_m"),
        "candidate_station_icao": meta.get("icao"), "candidate_station_country": meta.get("country"),
        "candidate_station_state": meta.get("state"), "candidate_station_begin": meta.get("begin"),
        "candidate_station_end": meta.get("end"),
        "candidate_venue_ids": sorted({p["venue_id"] for p in pilots if p.get("venue_id") is not None}),
        "station_reference_state": "CANDIDATE_REVIEW_REQUIRED",
        "pilot_keys": sorted(p["source_game_id"] for p in pilots), "pilot_rows": len(pilots),
        "observation_clock": "ISD_DATE_UTC_PER_ROW",
        "capture_manifest_issued_at_utc": anchors["clocks"]["capture_manifest_issued_at_utc"],
        "acquisition_issued_at_utc": anchors["clocks"]["acquisition_issued_at_utc"]
        if capture["raw_sha256"] in acquired else None, "source_publication_time": "NOT_ESTABLISHED",
        "rights_source_id": WEATHER_SOURCE_ID, "rights_decision_id": anchors["rights"][WEATHER_SOURCE_ID]["decision_id"],
        "raw_redistribution": anchors["rights"][WEATHER_SOURCE_ID]["redistribution_policy"]}
    return {"key": key, "record": record, "selections": selections, "witness_rows": witness_rows,
            "adjacent": adjacent}


# --------------------------------------------------------------------------------------------- derivation

def _provider_index(provider: list[dict[str, Any]]) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for ordinal, game in enumerate(provider):
        if game.get("season") == FOOTBALL_SEASON:
            index.setdefault(str(game.get("id")), []).append(ordinal)
    return index


def _witness_input(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    return {"witness_key": f"INPUT|{name}", "witness_kind": "INPUT", "relative_path": spec["relative_path"],
            "sha256": spec["sha256"], "bytes": spec["bytes"], "role": spec["role"], "rows": spec["rows"],
            "dataset_identity": spec["dataset_identity"], "issued_at_utc": spec["issued_at_utc"],
            "source_id": spec["source_id"]}


def _witness_record(base: dict[str, Any]) -> dict[str, Any]:
    out = {"record_type": RECORD_TYPES["witnesses"], **{k: LABELS[k] for k in GRAIN_LABEL_KEYS["witnesses"]}}
    out.update({f: None for f in FIELD_TYPES["witnesses"] if f not in out})
    out["selected_by"] = []
    out.update(base)
    return out


def _row_witness(key: str, stamp_entry: dict[str, Any]) -> dict[str, Any]:
    decoded = stamp_entry["decoded"]
    number = stamp_entry["source_row_number"]
    return _witness_record({
        "witness_key": f"ROW|{key}|{number}", "witness_kind": "SELECTED_RAW_ROW", "station_year_key": key,
        "station_id": key.split("|", 1)[1], "source_row_number": number,
        "raw_row_sha256": stamp_entry["raw_row_sha256"], "raw_fields": stamp_entry["raw_fields"],
        **{f"row_{name}": decoded[name] for name, _c in OBSERVATION_FIELDS
           if name not in ("source_row_number", "raw_tmp", "raw_dew", "raw_wnd", "raw_vis", "raw_slp")},
        "timestamp_candidates": stamp_entry["timestamp_candidates"], "selected_by": stamp_entry["selected_by"]})


def derive_station_years(inputs: dict[str, Any], anchors: dict[str, Any], keys: list[str] | None = None
                         ) -> dict[str, dict[str, Any]]:
    """Every (or the named) station-year capture processed in the input order (the checkpoint unit)."""
    by_pair: dict[str, list[dict[str, Any]]] = {}
    for index in inputs["pilot_order"]:
        row = inputs["pilot"][index]
        by_pair.setdefault(f"{row['calendar_year']}|{row['station_id']}", []).append(row)
    captured = set(inputs["captures"])
    out: dict[str, dict[str, Any]] = {}
    for key in inputs["station_year_order"]:
        if keys is not None and key not in keys:
            continue
        pilots = sorted(by_pair.get(key, []), key=lambda r: (r["kickoff_at_utc"], r["source_game_id"]))
        out[key] = process_station_year(key, inputs["paths"][f"raw:{key}"], inputs["captures"][key], pilots,
                                        inputs["stations"], inputs["acquired_raw"], captured, anchors)
    return out


def derive(inputs: dict[str, Any], anchors: dict[str, Any],
           station_years: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Every record of the four grains and the census (plain Python over the verified inputs)."""
    processed = station_years if station_years is not None else derive_station_years(inputs, anchors)
    if sorted(processed) != sorted(inputs["captures"]):
        _refuse("WEATHER_CAPTURE_MISMATCH", "not every station-year capture was processed")
    provider_index = _provider_index(inputs["provider"])
    parent_keys = {p["contest_key"] for p in inputs["parents"]}
    pilots: list[dict[str, Any]] = []
    for index, row in enumerate(inputs["pilot"]):
        key = f"{row['calendar_year']}|{row['station_id']}"
        sy = processed[key]
        chosen = sy["selections"][row["source_game_id"]]
        witness_by_stamp = sy["witness_rows"]
        kickoff = parse_utc(row["kickoff_at_utc"])

        def obs(stamp: str | None) -> dict[str, Any] | None:
            return None if stamp is None else witness_by_stamp[stamp]["decoded"]
        before, after, nearest = obs(chosen["BEFORE"]), obs(chosen["AFTER"]), obs(chosen["NEAREST"])
        verified = {
            "before_observed_at_utc": before["observed_at_utc"] if before else None,
            "before_delta_minutes": minutes((kickoff - parse_utc(before["observed_at_utc"])).total_seconds())
            if before else None,
            "after_observed_at_utc": after["observed_at_utc"] if after else None,
            "after_delta_minutes": minutes((parse_utc(after["observed_at_utc"]) - kickoff).total_seconds())
            if after else None,
            "nearest_observation_state": "PRESENT" if nearest else "MISSING",
            "nearest_absolute_delta_minutes": minutes(abs((parse_utc(nearest["observed_at_utc"]) -
                                                           kickoff).total_seconds())) if nearest else None,
            **{f"nearest_{name}": (nearest[name] if nearest else None) for name in OBSERVATION_NAMES}}
        game_ordinals = provider_index.get(row["source_game_id"], [])
        game = inputs["provider"][game_ordinals[0]] if len(game_ordinals) == 1 else None
        provider_row_key = f"src002:{FOOTBALL_SEASON}:{game_ordinals[0]:04d}" if game is not None else None
        rec = inputs["alias_providers"].get(provider_row_key) if provider_row_key else None
        if rec is not None and (str(rec.get("provider_game_id")) != row["source_game_id"] or
                                (rec.get("capture") or {}).get("sha256") != anchors["inputs"]["provider_games_2024"][
                                    "sha256"] or rec.get("row_ordinal") != game_ordinals[0]):
            _refuse("WEATHER_CAPTURE_MISMATCH", f"provider row {provider_row_key} names another game or capture")
        relation = (rec or {}).get("relation") or {}
        promoted = relation.get("promoted") is True and relation.get("one_to_one") is True and \
            relation.get("contest_key") in parent_keys
        if rec is None:
            relation_state = "NO_PROVIDER_ROW"
        else:
            relation_state = "PROMOTED_ONE_TO_ONE" if promoted else "CANDIDATE_NOT_PROMOTED"
        start = game.get("startDate") if game is not None else None
        agreement = "NOT_COMPARABLE" if start is None or row["kickoff_at_utc"] is None else (
            "AGREE" if start == row["kickoff_at_utc"] else "DIFFER")
        discrepant = [f for f in GOVERNED_FIELDS if not _same(row[f], verified[f])]
        coordinates = inputs["games"].get(row["source_game_id"]) or {}
        candidate = inputs["stations"].get(row["station_id"]) or {}
        expected_checks = {
            "calendar_year": kickoff.year, "station_file_id": station_file_id(row["station_id"]),
            "station_snapshot_id": sy["record"]["snapshot_id"], "station_raw_sha256": sy["record"]["raw_sha256"],
            "station_request_identity_sha256": sy["record"]["request_identity_sha256"],
            "row_lineage_sha256": lineage_sha256(row["source_game_id"], row["kickoff_at_utc"], row["station_id"],
                                                 sy["record"]["raw_sha256"], verified["nearest_observed_at_utc"]),
            "kickoff_at_utc": coordinates.get("kickoff_at_utc"), "home_team": coordinates.get("home_team"),
            "away_team": coordinates.get("away_team"), "venue_id": coordinates.get("venue_id"),
            "venue_name": coordinates.get("venue_name"), "venue_dome": coordinates.get("venue_dome"),
            "canonical_game_id_candidate": coordinates.get("canonical_game_id_candidate"),
            "station_name": (candidate.get("meta") or {}).get("name"),
            "station_latitude": (candidate.get("meta") or {}).get("latitude"),
            "station_longitude": (candidate.get("meta") or {}).get("longitude"),
            "distance_km": (candidate.get("distance") or {}).get(row["venue_id"])}
        # original constants and eligibility flags are not discrepancies to serve: the reader refuses a release whose
        # pilot carries another constant or a true flag (they are claims, never corrected values)
        discrepant += [f for f in CHECKED_ORIGINAL_FIELDS if not _same(row[f], expected_checks[f])]
        adjacent = (verified["before_observed_at_utc"] is None and sy["adjacent"]["before"]) or \
            (verified["after_observed_at_utc"] is None and sy["adjacent"]["after"])
        pilot = {
            "record_type": RECORD_TYPES["pilots"], **{k: LABELS[k] for k in GRAIN_LABEL_KEYS["pilots"]},
            "pilot_key": row["source_game_id"], "original_row_index": index,
            **{f"original_{name}": row[name] for name in ORIGINAL_NAMES},
            "provider_join_state": "EXACT_CAPTURED_PROVIDER_GAME" if game is not None else
            "PROVIDER_GAME_NOT_CAPTURED", "provider_row_key": provider_row_key,
            "provider_game_id": str(game["id"]) if game is not None else None, "provider_scheduled_start_utc": start,
            "provider_start_time_tbd": game.get("startTimeTBD") if game is not None else None,
            "provider_neutral_site": game.get("neutralSite") if game is not None else None,
            "provider_venue_id": str(game["venueId"]) if game is not None and game.get("venueId") is not None
            else None, "provider_venue_name": game.get("venue") if game is not None else None,
            "provider_season_type": game.get("seasonType") if game is not None else None,
            "provider_week": game.get("week") if game is not None else None,
            "kickoff_clock_agreement": agreement, "relation_state": relation_state,
            "relation_disposition": (rec or {}).get("disposition"),
            "relation_disposition_reason": (rec or {}).get("disposition_reason"),
            "contest_key": relation.get("contest_key") if promoted else None,
            "candidate_contest_key": relation.get("contest_key") if not promoted else None,
            "station_year_key": key, **{f"verified_{name}": verified[name] for name in GOVERNED_FIELDS},
            "verified_before_source_row_number": before["source_row_number"] if before else None,
            "verified_after_source_row_number": after["source_row_number"] if after else None,
            "reconstruction_state": "REPRODUCED_EXACT" if not discrepant else "DISCREPANT",
            "discrepant_fields": sorted(set(discrepant)),
            "before_witness_key": f"ROW|{key}|{before['source_row_number']}" if before else None,
            "after_witness_key": f"ROW|{key}|{after['source_row_number']}" if after else None,
            "nearest_witness_key": f"ROW|{key}|{nearest['source_row_number']}" if nearest else None,
            "before_missing_reason": None if before else MISSING_REASONS["before"],
            "after_missing_reason": None if after else MISSING_REASONS["after"],
            "adjacent_calendar_year_captured": bool(adjacent),
            "nearest_report_meaning": report_meaning(verified["nearest_report_type"]),
            **{f"{v}_quality_meaning": quality_meaning(verified[f"nearest_{v}_quality"]) for v in QUALITY_VARIABLES},
            "nearest_precipitation_groups": precipitation_groups(verified["nearest_precipitation_raw_json"]),
            "unsupported_reasons": []}
        pilot["unsupported_reasons"] = pilot_reasons(pilot)
        pilots.append(pilot)
    pilots.sort(key=lambda p: p["original_row_index"])
    pilot_by_contest = {p["contest_key"]: p for p in pilots if p["contest_key"] is not None}
    station_records = {k: v["record"] for k, v in processed.items()}
    contests: list[dict[str, Any]] = []
    for parent in inputs["parents"]:
        alias = inputs["alias_parents"].get(parent["contest_key"])
        if alias is None:
            _refuse("WEATHER_INPUT_MALFORMED", f"no alias reconciliation record for {parent['contest_key']}")
        pilot = pilot_by_contest.get(parent["contest_key"])
        candidates = sorted((alias.get("candidates") or {}).get("dated_provider_rows") or [])
        relation = alias.get("relation") or {}
        promoted = relation.get("promoted") is True and relation.get("one_to_one") is True
        if relation and relation.get("provider_row_key") != alias["_provider_row_key_column"]:
            _refuse("WEATHER_INPUT_MALFORMED", f"alias parent {parent['contest_key']} relation names another row")
        if promoted:
            relation_state = "PROMOTED_ONE_TO_ONE"
        elif relation:
            relation_state = "CANDIDATE_NOT_PROMOTED"
        else:
            relation_state = "NO_PROVIDER_ROW"
        # both sides of the accepted relation must agree: the parent's promoted relation names exactly the provider
        # row whose own promoted relation names this parent (and that row's pilot game)
        if (relation_state == "PROMOTED_ONE_TO_ONE") != (pilot is not None) or \
                (pilot is not None and (pilot["provider_row_key"] != relation.get("provider_row_key") or
                                        pilot["provider_game_id"] != str(relation.get("provider_game_id")))):
            _refuse("WEATHER_INPUT_MALFORMED", f"the parent and provider sides of the relation of "
                                               f"{parent['contest_key']} disagree")
        associated = pilot is not None
        sy = station_records.get(pilot["station_year_key"]) if associated else None
        present = associated and pilot["verified_nearest_observation_state"] == "PRESENT"
        contest = {
            "record_type": RECORD_TYPES["contests"], **{k: LABELS[k] for k in GRAIN_LABEL_KEYS["contests"]},
            **{name: parent[name] for name in PARENT_COLUMNS if name not in ("disposition", "disposition_reason",
                                                                            "reconciliation_state", "exposure")},
            "contest_calendar_year": int(str(parent["contest_date"])[:4]),
            "parent_disposition": parent["disposition"], "parent_disposition_reason": parent["disposition_reason"],
            "parent_reconciliation_state": parent["reconciliation_state"], "parent_exposure": parent["exposure"],
            "alias_disposition": alias["disposition"], "alias_disposition_reason": alias.get("disposition_reason"),
            "alias_route_scope": alias.get("route_scope"),
            "alias_field_conflicts": sorted(str(x) for x in alias.get("field_conflicts") or []),
            "alias_candidate_provider_row_keys": candidates,
            "alias_relation_provider_row_key": relation.get("provider_row_key"),
            "alias_relation_provider_game_id": None if relation.get("provider_game_id") is None else
            str(relation.get("provider_game_id")), "relation_state": relation_state,
            "provider_row_key": pilot["provider_row_key"] if associated else None,
            "provider_game_id": pilot["provider_game_id"] if associated else None,
            "pilot_key": pilot["pilot_key"] if associated else None,
            "weather_support_state": ("ASSOCIATED_CANDIDATE_STATION_OBSERVATION" if present else
                                      "ASSOCIATED_NO_OBSERVATION") if associated else (
                "UNSUPPORTED_RELATION_NOT_PROMOTED" if relation_state == "CANDIDATE_NOT_PROMOTED" else
                "UNSUPPORTED_NO_PROVIDER_ROW"),
            "station_year_key": pilot["station_year_key"] if associated else None,
            "station_id": pilot["original_station_id"] if associated else None,
            "station_name": pilot["original_station_name"] if associated else None,
            "station_distance_km": pilot["original_distance_km"] if associated else None,
            "station_elevation_m": sy["candidate_station_elevation_m"] if sy else None,
            "association_clock_utc": pilot["provider_scheduled_start_utc"]
            if associated and pilot["kickoff_clock_agreement"] == "AGREE" else None,
            "provider_start_time_tbd": pilot["provider_start_time_tbd"] if associated else None,
            "nearest_observed_at_utc": pilot["verified_nearest_observed_at_utc"] if present else None,
            "nearest_absolute_delta_minutes": pilot["verified_nearest_absolute_delta_minutes"] if present else None,
            "nearest_report_type": pilot["verified_nearest_report_type"] if present else None,
            "nearest_report_meaning": pilot["nearest_report_meaning"] if present else None,
            "before_present": (pilot["verified_before_observed_at_utc"] is not None) if associated else None,
            "after_present": (pilot["verified_after_observed_at_utc"] is not None) if associated else None,
            **{name: (pilot[f"verified_nearest_{name}"] if present else None) for name in NEAREST_SUMMARY},
            "reference_venue_id": pilot["original_venue_id"] if associated else None,
            "reference_venue_name": pilot["original_venue_name"] if associated else None,
            "reference_venue_dome": pilot["original_venue_dome"] if associated else None,
            "unsupported_reasons": []}
        contest["unsupported_reasons"] = contest_reasons(contest, pilot)
        contests.append(contest)
    contests.sort(key=lambda c: _order_key("contests", c))
    station_list = [station_records[k] for k in sorted(station_records, key=_station_year_sort)]
    witnesses = [_witness_record(_witness_input(name, spec)) for name, spec in anchors["inputs"].items()]
    witnesses += [_witness_record({"witness_key": f"CONTRACT|{rel}", "witness_kind": "PARENT_CONTRACT",
                                   "relative_path": rel, "sha256": sha, "role": "PARENT_CONTRACT"})
                  for rel, sha in anchors["parent_contracts"].items()]
    witnesses += [_witness_record({"witness_key": f"RAW|{key}", "witness_kind": "RAW_FILE",
                                   "relative_path": spec["raw_relative_path"], "sha256": spec["raw_sha256"],
                                   "bytes": spec["raw_bytes"], "role": "RAW_NOAA_ISD_STATION_YEAR_CSV",
                                   "rows": station_records[key]["data_rows"], "dataset_identity": None,
                                   "issued_at_utc": anchors["clocks"]["capture_manifest_issued_at_utc"],
                                   "source_id": WEATHER_SOURCE_ID, "station_year_key": key,
                                   "station_id": key.split("|", 1)[1]})
                  for key, spec in sorted(anchors["raw"].items(), key=lambda kv: _station_year_sort(kv[0]))]
    row_witnesses = []
    for key in sorted(processed, key=_station_year_sort):
        for entry in processed[key]["witness_rows"].values():
            row_witnesses.append(_row_witness(key, entry))
    row_witnesses.sort(key=lambda w: (_station_year_sort(w["station_year_key"]), w["source_row_number"]))
    witnesses += row_witnesses
    derived = {"contests": contests, "pilots": pilots, "station_years": station_list, "witnesses": witnesses}
    derived["census"] = census_record(derived)
    return derived


def _same(a: Any, b: Any) -> bool:
    """Exact JSON equality: the same type (a boolean is never an integer, an integer never a float) and value."""
    return type(a) is type(b) and a == b if not isinstance(a, (dict, list)) else \
        canonical_json_bytes(a) == canonical_json_bytes(b)


def _counts(values: Iterable[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        key = str(value)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def census_record(derived: dict[str, Any]) -> dict[str, Any]:
    contests, pilots, stations = derived["contests"], derived["pilots"], derived["station_years"]
    promoted = {p["pilot_key"] for p in pilots if p["relation_state"] == "PROMOTED_ONE_TO_ONE"}
    within = {p["pilot_key"] for p in pilots if p["verified_nearest_absolute_delta_minutes"] is not None
              and p["verified_nearest_absolute_delta_minutes"] <= 30.0}
    raw_types: dict[str, int] = {}
    for s in stations:
        for t, n in s["report_type_rows"].items():
            raw_types[t] = raw_types.get(t, 0) + n
    return {
        "record_type": RECORD_TYPES["census"], **{k: LABELS[k] for k in GRAIN_LABEL_KEYS["census"]},
        "contests": len(contests), "pilots": len(pilots), "station_years": len(stations),
        "witnesses": len(derived["witnesses"]),
        "selected_raw_rows": sum(1 for w in derived["witnesses"] if w["witness_kind"] == "SELECTED_RAW_ROW"),
        "contests_by_relation_state": _counts(c["relation_state"] for c in contests),
        "contests_by_support_state": _counts(c["weather_support_state"] for c in contests),
        "contests_by_calendar_year": _counts(c["contest_calendar_year"] for c in contests),
        "contests_by_classification_pair": _counts(c["classification_pair"] for c in contests),
        "promoted_relations": sum(1 for c in contests if c["relation_state"] == "PROMOTED_ONE_TO_ONE"),
        "unpromoted_relations": sum(1 for p in pilots if p["relation_state"] != "PROMOTED_ONE_TO_ONE"),
        "parents_without_promoted_weather": sum(1 for c in contests if c["pilot_key"] is None),
        "pilots_by_calendar_year": _counts(p["original_calendar_year"] for p in pilots),
        "pilots_by_reconstruction_state": _counts(p["reconstruction_state"] for p in pilots),
        "pilots_by_kickoff_clock_agreement": _counts(p["kickoff_clock_agreement"] for p in pilots),
        "pilots_by_nearest_report_type": _counts(p["verified_nearest_report_type"] for p in pilots),
        "within_30_minutes": len(within), "within_30_and_promoted": len(within & promoted),
        "within_30_not_promoted": len(within - promoted), "promoted_not_within_30": len(promoted - within),
        "before_missing": sum(1 for p in pilots if p["verified_before_observed_at_utc"] is None),
        "after_missing": sum(1 for p in pilots if p["verified_after_observed_at_utc"] is None),
        "adjacent_calendar_year_captured": sum(1 for p in pilots if p["adjacent_calendar_year_captured"]),
        "dome_reference_rows": sum(1 for p in pilots if p["original_venue_dome"] is True),
        "provider_start_time_tbd": sum(1 for p in pilots if p["provider_start_time_tbd"] is True),
        "suspect_or_erroneous_nearest": sum(1 for p in pilots
                                            if "NEAREST_VALUE_FLAGGED_SUSPECT_OR_ERRONEOUS" in p["unsupported_reasons"]),
        "summary_nearest": sum(1 for p in pilots
                               if "NEAREST_OBSERVATION_IS_SUMMARY_NOT_INSTANTANEOUS" in p["unsupported_reasons"]),
        "discrepant_pilots": sum(1 for p in pilots if p["reconstruction_state"] != "REPRODUCED_EXACT"),
        "raw_rows": sum(s["data_rows"] for s in stations), "raw_bytes": sum(s["raw_bytes"] for s in stations),
        "raw_report_type_rows": dict(sorted(raw_types.items())),
        "raw_duplicate_timestamp_rows": sum(s["duplicate_timestamp_rows"] for s in stations),
        "raw_malformed_rows": sum(s["malformed_rows"] for s in stations)}


# --------------------------------------------------------------------------------------------- serialization

def record_key(table: str, record: dict[str, Any]) -> str:
    if table == "census":
        return "census"
    return str(record.get(KEY_FIELDS[table]))


def record_lines(derived: dict[str, Any]) -> dict[str, list[str]]:
    if "lines" not in derived:
        derived["lines"] = {table: [canonical_line(r) for r in derived[table]] for table in RECORD_TABLES}
        derived["lines"]["census"] = [canonical_line(derived["census"])]
    return derived["lines"]


def segment_of(table: str, record: dict[str, Any]) -> str:
    if table == "contests":
        return str(record["contest_calendar_year"])
    if table == "pilots":
        return str(record["original_calendar_year"])
    if table == "station_years":
        return str(record["calendar_year"])
    if table == "witnesses":
        if record["witness_kind"] != "SELECTED_RAW_ROW":
            return "SOURCE"
        return str(record["station_year_key"]).split("|", 1)[0]
    return "GLOBAL"


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
    grouped[("census", "GLOBAL")] = ([derived["census"]], lines["census"])
    return [(table, segment, *grouped.get((table, segment), ([], []))) for table, segment in BLOCK_LAYOUT]


def lines_sha256(lines: list[str]) -> str:
    return sha256_bytes("".join(line + "\n" for line in lines).encode("utf-8"))


def row_counts(derived: dict[str, Any]) -> dict[str, int]:
    return {**{table: len(derived[table]) for table in RECORD_TABLES}, "census": 1}


def inputs_claim(anchors: dict[str, Any]) -> dict[str, Any]:
    return {"inputs": anchors["inputs"], "raw": anchors["raw"], "clocks": anchors["clocks"],
            "rights": anchors["rights"], "expected": anchors["expected"]}


def content_document(anchors: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
    lines = record_lines(derived)
    return {"schema": CONTENT_SCHEMA, "stage": "weather-evidence-content", "population": POPULATION,
            "contract_id": anchors["contract_id"], "contract_sha256": anchors["contract_sha256"],
            "inputs": inputs_claim(anchors), "parent_contracts": anchors["parent_contracts"],
            "rules_sha256": rules_sha256(), "payload_schema": PAYLOAD_SCHEMA, "row_counts": row_counts(derived),
            "lines_sha256": {table: lines_sha256(lines[table]) for table in (*RECORD_TABLES, "census")},
            "blocks": [[table, segment, len(block), lines_sha256(block)]
                       for table, segment, _records, block in block_lines(derived)]}


def database_document(contract_sha256: str, content_identity: str, database_sha256: str,
                      table_counts: dict[str, int]) -> dict[str, Any]:
    return {"schema": DATABASE_SCHEMA, "stage": "weather-evidence-database", "population": POPULATION,
            "contract_sha256": contract_sha256, "content_identity": content_identity, "db_schema_version": DB_SCHEMA,
            "outputs": {DB_FILE: database_sha256}, "table_counts": dict(table_counts)}


def meta_values(anchors: dict[str, Any], content_identity: str, derived: dict[str, Any]) -> dict[str, str]:
    return {"schema_version": DB_SCHEMA, "contract_id": anchors["contract_id"],
            "contract_sha256": anchors["contract_sha256"], "content_identity": content_identity,
            "inputs": canonical_line(inputs_claim(anchors)), "parent_contracts": canonical_line(anchors["parent_contracts"]),
            "labels": canonical_line(LABELS), "rules": canonical_line(rules_document()),
            "row_counts": canonical_line(row_counts(derived)),
            "census_sha256": sha256_bytes(canonical_json_bytes(derived["census"]))}


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


# --------------------------------------------------------------------------------------------- the reader

_NONE = type(None)
#: Exact JSON types per field code (``type(value) in allowed``: a boolean is never an integer, an integer never a float).
_SCALAR_TYPES = {"s": (str,), "s?": (str, _NONE), "i": (int,), "i?": (int, _NONE), "b": (bool,), "b?": (bool, _NONE),
                 "f": (float,), "f?": (float, _NONE), "n": (_NONE,)}
_CANDIDATE_TYPES = {"source_row_number": int, "decoded_common_field_count": int, "report_type": str,
                    "source_code": str}


def _candidate_list(value: Any) -> bool:
    return type(value) is list and all(
        type(item) is dict and set(item) == set(_CANDIDATE_TYPES) and
        all(type(item[k]) is t for k, t in _CANDIDATE_TYPES.items()) for item in value)


_TYPE_CHECKS = {
    **{code: (lambda allowed: (lambda v: type(v) in allowed))(allowed) for code, allowed in _SCALAR_TYPES.items()},
    "ls": lambda v: type(v) is list and all(type(x) is str for x in v),
    "di": lambda v: type(v) is dict and all(type(k) is str and type(x) is int for k, x in v.items()),
    "ddi": lambda v: type(v) is dict and all(type(k) is str and type(x) is dict and
                                             all(type(a) is str and type(b) is int for a, b in x.items())
                                             for k, x in v.items()),
    "dss?": lambda v: v is None or (type(v) is dict and all(type(k) is str and type(x) is str for k, x in v.items())),
    "lc?": lambda v: v is None or _candidate_list(v),
}
CONTEST_KEY_RE = re.compile(r"(?:ncaa:[0-9]{1,12}|nolink:2024:[0-9]{4}-[0-9]{2}-[0-9]{2}:org:[0-9]{1,12}\|"
                            r"org:[0-9]{1,12})\Z")
PROVIDER_GAME_RE = re.compile(r"[0-9]{1,12}\Z")
STATION_RE = re.compile(r"[0-9]{6}-[0-9]{5}\Z")
STATION_YEAR_RE = re.compile(r"(2024|2025)\|([0-9]{6}-[0-9]{5})\Z")
PROVIDER_ROW_RE = re.compile(r"src002:2024:[0-9]{4}\Z")
MANIFEST_MEMBERS = ("content_document", "content_identity", "identity", "identity_document", "provenance")


class WeatherEvidence:
    """A verified, read-only handle on one content-addressed national observed-weather evidence release.

    Construction refuses (WeatherError with a stable code) unless the release location, run manifest, database bytes,
    schema, meta claims, every record's exact members and JSON types, the complete expected collection of every grain,
    every rule re-derivable from the records, the content document, the contract-defined database identity document
    and (when the anchors pin one) the canonical profile verify. Each refusal is checked in a fixed order so that every
    forgery is refused for its own cause."""

    def __init__(self, database: Path, *, manifest: Path | None = None, expect_identity: str | None = None,
                 anchors: dict[str, Any] | None = None) -> None:
        self.anchors = anchors if anchors is not None else {**ANCHORS, "profile": WEATHER_PROFILE}
        self.binding = self._verify_location_and_manifest(database, manifest, expect_identity)
        document = self.binding["identity_document"]
        if document.get("contract_sha256") != self.anchors["contract_sha256"]:
            _refuse("WEATHER_CONTRACT_MISMATCH", f"the release names contract {document.get('contract_sha256')}, "
                                                 f"the reader binds {self.anchors['contract_sha256']}")
        try:
            location = readonly_sqlite.literal_path(database)
            self.conn = readonly_sqlite.connect_readonly(_io_path(Path(location)), immutable=False)
        except readonly_sqlite.DatabaseLocationError as exc:
            raise WeatherError(exc.code, exc.detail) from exc
        except sqlite3.Error as exc:
            raise WeatherError("WEATHER_DATABASE_UNREADABLE", str(exc)) from exc
        try:
            self._verify_database()
        except sqlite3.DatabaseError as exc:
            self.conn.close()
            raise WeatherError("WEATHER_SCHEMA_UNSUPPORTED", str(exc)) from exc
        except BaseException:
            self.conn.close()
            raise

    # ---- outer identity
    @staticmethod
    def _verify_location_and_manifest(database: Path, manifest: Path | None,
                                      expect_identity: str | None) -> dict[str, Any]:
        try:
            readonly_sqlite.literal_path(database)
        except readonly_sqlite.DatabaseLocationError as exc:
            raise WeatherError(exc.code, exc.detail) from exc
        manifest_path = None
        if manifest is not None:
            try:
                manifest_path = Path(readonly_sqlite.literal_path(manifest))
            except readonly_sqlite.DatabaseLocationError as exc:
                suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
                raise WeatherError(f"WEATHER_MANIFEST_LOCATION_{suffix}", f"--manifest {manifest}: "
                                                                         f"{exc.detail}") from exc
        db = Path(database)
        if not _io_path(db).is_file():
            _refuse("WEATHER_DATABASE_MISSING", f"no weather evidence database file at {db}")
        absolute = Path(os.path.abspath(db))
        if absolute.name != DB_FILE or absolute.parent.parent.name != "sha256" or \
                absolute.parent.parent.parent.name != POPULATION:
            _refuse("WEATHER_LOCATION_INVALID", f"the release must sit at <root>/{POPULATION}/sha256/<id>/{DB_FILE}")
        identity = absolute.parent.name
        if not IDENTITY_RE.match(identity):
            _refuse("WEATHER_LOCATION_INVALID", f"directory name {identity!r} is not an identity")
        if manifest_path is None:
            manifest_path = manifest_path_for(db)
        if not _io_path(manifest_path).is_file():
            _refuse("WEATHER_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
        try:
            raw = _io_path(manifest_path).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise WeatherError("WEATHER_MANIFEST_MALFORMED", str(exc)) from exc
        doc = loads_untrusted(raw, "WEATHER_MANIFEST_MALFORMED", "run manifest")
        if not isinstance(doc, dict):
            _refuse("WEATHER_MANIFEST_MALFORMED", "the run manifest is not a JSON object")
        if sorted(doc) != sorted(MANIFEST_MEMBERS):
            _refuse("WEATHER_MANIFEST_MALFORMED", f"run manifest members {sorted(doc)} differ from "
                                                  f"{list(MANIFEST_MEMBERS)}")
        # Every member (the free-form provenance included) must be Unicode text the canonical encoder accepts.
        _untrusted_canonical(doc, "WEATHER_MANIFEST_MALFORMED", "run manifest")
        identity_document = doc["identity_document"]
        computed = sha256_bytes(_untrusted_canonical(identity_document, "WEATHER_MANIFEST_MALFORMED",
                                                     "run manifest identity document"))
        _untrusted_canonical(doc["content_document"], "WEATHER_MANIFEST_MALFORMED", "run manifest content document")
        if computed != identity or doc.get("identity") != identity:
            _refuse("WEATHER_IDENTITY_MISMATCH", f"manifest identity document hashes to {computed}, directory is "
                                                 f"{identity}, the manifest names {doc.get('identity')!r}")
        if not isinstance(identity_document, dict) or \
                (identity_document.get("stage"), identity_document.get("schema"),
                 identity_document.get("db_schema_version"), identity_document.get("population")) != \
                ("weather-evidence-database", DATABASE_SCHEMA, DB_SCHEMA, POPULATION):
            _refuse("WEATHER_SCHEMA_UNSUPPORTED", "not a national observed-weather evidence database manifest")
        outputs = identity_document.get("outputs")
        if not isinstance(outputs, dict):
            _refuse("WEATHER_IDENTITY_DOCUMENT_MISMATCH", "the manifest identity document's outputs is not an object")
        actual_sha = sha256_file(_io_path(db))
        if outputs.get(DB_FILE) != actual_sha:
            _refuse("WEATHER_DATABASE_TAMPERED", f"release bytes hash to {actual_sha}, manifest names "
                                                 f"{outputs.get(DB_FILE)}")
        if expect_identity is not None and expect_identity != identity:
            _refuse("STALE_WEATHER_IDENTITY", f"expected {expect_identity}, found {identity}")
        return {"identity": identity, "sha256": actual_sha, "manifest": str(manifest_path),
                "identity_document": identity_document, "content_document": doc["content_document"],
                "content_identity_claim": doc.get("content_identity"), "provenance": doc.get("provenance")}

    # ---- schema, meta claims, records, rules and identities
    def _verify_database(self) -> None:
        a = self.anchors
        master = sorted((str(r[0]), str(r[1]), r[2]) for r in self.conn.execute(
            "SELECT type, name, sql FROM sqlite_master"))
        if master != sorted(DDL):
            _refuse("WEATHER_SCHEMA_UNSUPPORTED", "the release schema differs from the contract")
        meta_rows = [(str(r[0]), r[1]) for r in self.conn.execute("SELECT key, value FROM meta ORDER BY rowid")]
        meta = dict(meta_rows)
        if len(meta) != len(meta_rows):
            _refuse("WEATHER_META_MISMATCH", "duplicate meta keys")
        if meta.get("schema_version") != DB_SCHEMA:
            _refuse("WEATHER_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}")
        if meta.get("contract_sha256") != a["contract_sha256"] or meta.get("contract_id") != a["contract_id"]:
            _refuse("WEATHER_CONTRACT_MISMATCH", "the release meta names another contract")
        claims = {name: _json_or_none(meta.get(name), name) for name in ("inputs", "parent_contracts", "labels",
                                                                         "rules")}
        if claims["labels"] != LABELS:
            labels = claims["labels"] if isinstance(claims["labels"], dict) else {}
            code = "WEATHER_PIT_CLAIM_INVALID" if labels.get("pit_eligibility") != LABELS["pit_eligibility"] else \
                "WEATHER_LABEL_CLAIM_INVALID"
            _refuse(code, "the release declares labels other than the contract's")
        if _untrusted_canonical(claims["inputs"], "WEATHER_META_MALFORMED", "meta inputs") != \
                canonical_json_bytes(inputs_claim(a)):
            _refuse("WEATHER_PARENT_MISMATCH", "the release was built from other inputs or expectations")
        if _untrusted_canonical(claims["parent_contracts"], "WEATHER_META_MALFORMED", "meta parent_contracts") != \
                canonical_json_bytes(a["parent_contracts"]):
            _refuse("WEATHER_PARENT_MISMATCH", "the release names other parent contracts")
        if _untrusted_canonical(claims["rules"], "WEATHER_META_MALFORMED", "meta rules") != \
                canonical_json_bytes(rules_document()):
            _refuse("WEATHER_RULES_CLAIM_INVALID", "the release declares other rules")
        counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        if counts != self.binding["identity_document"].get("table_counts"):
            _refuse("WEATHER_COUNT_MISMATCH",
                    f"table counts {counts} != {self.binding['identity_document'].get('table_counts')}")
        present = self._read_blocks()
        records = {table: [r for _l, r in present[table]] for table in (*RECORD_TABLES, "census")}
        self._verify_collections(records)
        self._verify_rules(records)
        derived = {table: records[table] for table in RECORD_TABLES}
        derived["census"] = records["census"][0]
        derived["lines"] = {table: [line for line, _r in present[table]] for table in (*RECORD_TABLES, "census")}
        document = content_document(a, derived)
        content_identity = sha256_bytes(canonical_json_bytes(document))
        if _untrusted_canonical(self.binding["content_document"], "WEATHER_MANIFEST_MALFORMED",
                                "content document") != canonical_json_bytes(document) or \
                self.binding["content_identity_claim"] != content_identity or \
                meta.get("content_identity") != content_identity or \
                self.binding["identity_document"].get("content_identity") != content_identity:
            _refuse("WEATHER_CONTENT_IDENTITY_MISMATCH", f"the rebuilt content identity is {content_identity}")
        expected_meta = meta_values(a, content_identity, derived)
        if meta != expected_meta:
            _refuse("WEATHER_META_MISMATCH", "meta differs on " + str(sorted(
                k for k in set(meta) | set(expected_meta) if meta.get(k) != expected_meta.get(k))))
        identity_document = self.binding["identity_document"]
        expected_document = database_document(a["contract_sha256"], content_identity, self.binding["sha256"], counts)
        expected_bytes = canonical_json_bytes(expected_document)
        if canonical_json_bytes(identity_document) != expected_bytes:
            differing = sorted(k for k in set(identity_document) | set(expected_document)
                               if k not in identity_document or k not in expected_document
                               or canonical_json_bytes(identity_document[k]) !=
                               canonical_json_bytes(expected_document[k]))
            _refuse("WEATHER_IDENTITY_DOCUMENT_MISMATCH", f"the manifest identity document is not the "
                                                          f"contract-defined database document (differs on "
                                                          f"{differing})")
        database_identity = sha256_bytes(expected_bytes)
        if database_identity != self.binding["identity"]:
            _refuse("WEATHER_IDENTITY_DOCUMENT_MISMATCH", f"the location names {self.binding['identity']}, the "
                                                          f"contract-defined document is {database_identity}")
        profile = a.get("profile")
        if profile is not None and (profile.get("content_identity"), profile.get("database_identity")) != \
                (content_identity, database_identity):
            _refuse("WEATHER_PROFILE_MISMATCH", f"the release ({database_identity} / {content_identity}) is not the "
                                                f"pinned canonical profile ({profile.get('database_identity')} / "
                                                f"{profile.get('content_identity')})")
        self.database_identity = database_identity
        self.content_identity = content_identity
        self.meta = meta
        self.records = derived
        self.census = derived["census"]

    def _read_blocks(self) -> dict[str, list[tuple[str, dict[str, Any]]]]:
        rows = [tuple(r) for r in self.conn.execute(
            "SELECT ord, record_table, segment, records, first_key, last_key, lines_sha256, block FROM blocks "
            "ORDER BY ord")]
        present: dict[str, list[tuple[str, dict[str, Any]]]] = {t: [] for t in (*RECORD_TABLES, "census")}
        self.segments: dict[str, list[str]] = {}
        layout = []
        for ord_, table, segment, records, first_key, last_key, lines_sha, blob in rows:
            if table not in present:
                _refuse("WEATHER_SCHEMA_UNSUPPORTED", f"block {ord_} names table {table!r}")
            try:
                data = zlib.decompress(blob)
                lines = data.decode("utf-8").split("\n")
            except (zlib.error, TypeError, UnicodeDecodeError) as exc:
                raise WeatherError("WEATHER_INDEX_MISMATCH", f"block {ord_} does not decompress: {exc}") from exc
            if lines[-1] != "":
                _refuse("WEATHER_INDEX_MISMATCH", f"block {ord_} does not end with a newline")
            parsed = []
            for line in lines[:-1]:
                record = loads_untrusted(line, "WEATHER_RECORD_MALFORMED", f"block {ord_} ({table})",
                                         non_json_code="WEATHER_RECORD_TYPE_INVALID")
                if not isinstance(record, dict):
                    _refuse("WEATHER_RECORD_TYPE_INVALID", f"block {ord_} holds a non-object line")
                if table != "census":
                    key = record.get(KEY_FIELDS[table])
                    if not isinstance(key, str):
                        _refuse("WEATHER_RECORD_TYPE_INVALID", f"{table} record: {KEY_FIELDS[table]} is not a string")
                parsed.append((line, record))
            keys = [record_key(table, r) for _l, r in parsed]
            if sha256_bytes(data) != lines_sha or records != len(parsed) or \
                    first_key != (keys[0] if keys else None) or last_key != (keys[-1] if keys else None):
                _refuse("WEATHER_INDEX_MISMATCH", f"block {ord_} index columns differ from its content")
            self.segments.setdefault(table, []).extend(segment for _p in parsed)
            layout.append((table, segment))
            present[table] += parsed
        if layout != list(BLOCK_LAYOUT):
            _refuse("WEATHER_INDEX_MISMATCH", "the blocks do not follow the contract layout")
        forbidden = set(FORBIDDEN_FIELDS)
        for table in (*RECORD_TABLES, "census"):
            types = FIELD_TYPES[table]
            scalar = [(f, _SCALAR_TYPES[c]) for f, c in types.items() if c in _SCALAR_TYPES]
            compound = [(f, c) for f, c in types.items() if c not in _SCALAR_TYPES]
            for line, record in present[table]:
                where = f"{table} record {record_key(table, record)}"
                leaked = sorted(forbidden & set(record))
                if leaked:
                    _refuse("WEATHER_FORBIDDEN_FIELD_PRESENT", f"{where} carries forbidden members {leaked[:4]}")
                if set(record) != set(types):
                    extra, missing = sorted(set(record) - set(types)), sorted(set(types) - set(record))
                    _refuse("WEATHER_RECORD_SHAPE_INVALID", f"{where}: extra members {extra[:4]}, missing "
                                                            f"{missing[:4]}")
                for field, code in scalar:
                    if type(record[field]) not in code:
                        _refuse("WEATHER_FIELD_TYPE_INVALID", f"{where}: {field} is a JSON "
                                                              f"{type(record[field]).__name__}, the contract "
                                                              f"declares {types[field]}")
                for field, code in compound:
                    if not _TYPE_CHECKS[code](record[field]):
                        _refuse("WEATHER_FIELD_TYPE_INVALID", f"{where}: {field} is a JSON "
                                                              f"{type(record[field]).__name__}, the contract "
                                                              f"declares {code}")
                if line != _untrusted_canonical(record, "WEATHER_RECORD_MALFORMED", where).decode("utf-8"):
                    _refuse("WEATHER_RECORD_NOT_CANONICAL", f"{where} is not its canonical JSON line")
            for (line, record), segment in zip(present[table], self.segments.get(table, [])):
                if table != "census" and segment_of_untrusted(table, record) != segment:
                    _refuse("WEATHER_INDEX_MISMATCH", f"{table} record {record_key(table, record)} sits in segment "
                                                      f"{segment}")
        return present

    def _verify_collections(self, records: dict[str, list[dict[str, Any]]]) -> None:
        """Complete membership and multiplicity of every grain against the contract's expected collection, then the
        contract order, then the exact key sequence."""
        expected = self.anchors["expected"]
        for table in RECORD_TABLES:
            label = TABLE_LABELS[table]
            keys = [record_key(table, r) for r in records[table]]
            if len(keys) != len(set(keys)):
                _refuse("WEATHER_DUPLICATE_ROW", f"{table} repeats a record key")
            listed = expected.get(f"{table}_keys")
            if table == "witnesses":
                listed_source = expected["source_witness_keys"]
                source = [k for k in keys if not k.startswith("ROW|")]
                missing = sorted(set(listed_source) - set(source))
                if missing:
                    _refuse("WEATHER_WITNESS_ROW_MISSING", f"{len(missing)} expected source witnesses absent, e.g. "
                                                           f"{missing[:3]}")
                extra = sorted(set(source) - set(listed_source))
                if extra:
                    _refuse("WEATHER_WITNESS_ROW_EXTRA", f"{len(extra)} source witnesses outside the expected "
                                                         f"collection, e.g. {extra[:3]}")
            if listed is not None:
                missing = sorted(set(listed) - set(keys))
                if missing:
                    _refuse(f"WEATHER_{label}_ROW_MISSING", f"{len(missing)} expected {table} keys absent, e.g. "
                                                            f"{missing[:3]}")
                extra = sorted(set(keys) - set(listed))
                if extra:
                    _refuse(f"WEATHER_{label}_ROW_EXTRA", f"{len(extra)} {table} keys outside the expected "
                                                          f"collection, e.g. {extra[:3]}")
            if table in expected and len(keys) < expected[table]:
                _refuse(f"WEATHER_{label}_ROW_MISSING", f"{expected[table] - len(keys)} expected {table} records "
                                                        "absent")
            if table in expected and len(keys) > expected[table]:
                _refuse(f"WEATHER_{label}_ROW_EXTRA", f"{len(keys) - expected[table]} {table} records outside the "
                                                      "expected collection")
            try:
                sources = source_order(self.anchors)
                order = [_order_key(table, r, sources) for r in records[table]]
            except (KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
                raise WeatherError("WEATHER_ORDER_MISMATCH", f"{table} order key cannot be formed: {exc}") from exc
            if order != sorted(order):
                _refuse("WEATHER_ORDER_MISMATCH", f"{table} is not in the contract order")
            if f"{table}_keys_sha256" in expected and keys_sha256(keys) != expected[f"{table}_keys_sha256"]:
                _refuse(f"WEATHER_{label}_KEYS_MISMATCH", f"the {table} key sequence differs from the contract's "
                                                          "expected collection")

    # ---- rules
    def _verify_rules(self, records: dict[str, list[dict[str, Any]]]) -> None:
        """Every rule the records themselves can re-derive, in a fixed order."""
        a = self.anchors
        for table in (*RECORD_TABLES, "census"):
            want = RECORD_TYPES[table]
            for record in records[table]:
                if record["record_type"] != want:
                    _refuse("WEATHER_RECORD_TYPE_INVALID", f"{table} record {record_key(table, record)} is a "
                                                           f"{record['record_type']!r}")
                for k in GRAIN_LABEL_KEYS[table]:
                    if record[k] != LABELS[k]:
                        _refuse("WEATHER_PIT_CLAIM_INVALID" if k == "pit_eligibility" else
                                "WEATHER_LABEL_CLAIM_INVALID", f"{table} record {record_key(table, record)}: {k} "
                                                               f"is {record[k]!r}")
        stations = {s["station_year_key"]: s for s in records["station_years"]}
        witnesses = {w["witness_key"]: w for w in records["witnesses"]}
        pilots = {p["pilot_key"]: p for p in records["pilots"]}
        contests = {c["contest_key"]: c for c in records["contests"]}
        self._verify_keys(records)
        self._verify_station_years(records["station_years"])
        self._verify_witnesses(records["witnesses"], stations, pilots)
        self._verify_pilots(records["pilots"], stations, witnesses, contests)
        self._verify_contests(records["contests"], pilots, stations)
        derived = {table: records[table] for table in RECORD_TABLES}
        expected = census_record(derived)
        if canonical_json_bytes(records["census"][0]) != canonical_json_bytes(expected):
            differing = sorted(k for k in expected if canonical_json_bytes(records["census"][0].get(k)) !=
                               canonical_json_bytes(expected[k]))
            _refuse("WEATHER_CENSUS_MISMATCH", f"the census differs from its records on {differing[:6]}")
        census_expected = a["expected"].get("census")
        if census_expected is not None:
            for key, value in census_expected.items():
                if canonical_json_bytes(records["census"][0].get(key)) != canonical_json_bytes(value):
                    _refuse("WEATHER_CENSUS_MISMATCH", f"census {key} differs from the contract's expectation")

    @staticmethod
    def _verify_keys(records: dict[str, list[dict[str, Any]]]) -> None:
        for c in records["contests"]:
            key = c["contest_key"]
            if c["ncaa_contest_id"] is not None:
                ok = key == f"ncaa:{c['ncaa_contest_id']}"
            else:
                ok = key == f"nolink:{c['season']}:{c['contest_date']}:{c['a_key']}|{c['b_key']}"
            if not CONTEST_KEY_RE.match(key) or not ok:
                _refuse("WEATHER_KEY_INVALID", f"contest key {key!r}")
        for p in records["pilots"]:
            if not PROVIDER_GAME_RE.match(p["pilot_key"]) or p["pilot_key"] != p["original_source_game_id"]:
                _refuse("WEATHER_KEY_INVALID", f"pilot key {p['pilot_key']!r}")
        for s in records["station_years"]:
            match = STATION_YEAR_RE.match(s["station_year_key"])
            if not match or s["station_year_key"] != f"{s['calendar_year']}|{s['station_id']}":
                _refuse("WEATHER_KEY_INVALID", f"station-year key {s['station_year_key']!r}")
        for w in records["witnesses"]:
            kind, key = w["witness_kind"], w["witness_key"]
            if kind not in WITNESS_KINDS:
                _refuse("WEATHER_KEY_INVALID", f"witness kind {kind!r}")
            prefix = {"INPUT": "INPUT|", "PARENT_CONTRACT": "CONTRACT|", "RAW_FILE": "RAW|",
                      "SELECTED_RAW_ROW": "ROW|"}[kind]
            if not key.startswith(prefix):
                _refuse("WEATHER_KEY_INVALID", f"witness key {key!r} is not a {kind} key")
            if kind == "SELECTED_RAW_ROW" and key != f"ROW|{w['station_year_key']}|{w['source_row_number']}":
                _refuse("WEATHER_KEY_INVALID", f"witness key {key!r} names another row")

    def _verify_station_years(self, stations: list[dict[str, Any]]) -> None:
        a = self.anchors
        clocks, rights = a["clocks"], a["rights"][WEATHER_SOURCE_ID]
        for s in stations:
            key = s["station_year_key"]
            if s["calendar_year"] not in CALENDAR_YEARS:
                _refuse("WEATHER_SEASON_OUT_OF_RANGE", f"station-year {key} calendar year {s['calendar_year']}")
            if s["station_file_id"] != s["station_id"].replace("-", ""):
                _refuse("WEATHER_STATION_YEAR_MISMATCH", f"station-year {key} file id")
            pinned = a["raw"].get(key)
            if pinned is None or any(s[f] != pinned[g] for f, g in (
                    ("raw_relative_path", "raw_relative_path"), ("raw_sha256", "raw_sha256"),
                    ("raw_bytes", "raw_bytes"), ("request_identity_sha256", "request_identity_sha256"),
                    ("snapshot_id", "snapshot_id"), ("source_uri", "source_uri"),
                    ("capture_reuse_state", "capture_reuse_state"))):
                _refuse("WEATHER_STATION_YEAR_MISMATCH", f"station-year {key} differs from its pinned capture")
            if s["capture_manifest_issued_at_utc"] != clocks["capture_manifest_issued_at_utc"] or \
                    s["acquisition_issued_at_utc"] not in (None, clocks["acquisition_issued_at_utc"]) or \
                    (s["acquisition_issued_at_utc"] is not None) != (pinned["raw_sha256"] in a["expected"][
                        "acquisition_raw_sha256"]) or \
                    s["observation_clock"] != "ISD_DATE_UTC_PER_ROW" or s["source_publication_time"] != \
                    "NOT_ESTABLISHED":
                _refuse("WEATHER_SOURCE_CLOCK_MISMATCH", f"station-year {key} source clocks differ from the pins")
            if s["rights_source_id"] != WEATHER_SOURCE_ID or s["rights_decision_id"] != rights["decision_id"] or \
                    s["raw_redistribution"] != rights["redistribution_policy"]:
                _refuse("WEATHER_RIGHTS_MISMATCH", f"station-year {key} rights differ from the pins")
            if s["station_reference_state"] != "CANDIDATE_REVIEW_REQUIRED":
                _refuse("WEATHER_ORIGINAL_CLAIM_INVALID", f"station-year {key} promotes its candidate station")
            counts_ok = (
                min(s["data_rows"], s["malformed_rows"], s["distinct_timestamps"], s["duplicate_timestamp_rows"],
                    s["precipitation_rows"], s["pilot_rows"]) >= 0 and
                sum(s["report_type_rows"].values()) == s["data_rows"] and
                s["duplicate_timestamp_rows"] == s["data_rows"] - s["distinct_timestamps"] and
                s["malformed_rows"] <= s["data_rows"] and s["precipitation_rows"] <= s["data_rows"] and
                all(sum(q.values()) == s["data_rows"] for q in s["quality_code_rows"].values()) and
                sorted(s["quality_code_rows"]) == sorted(QUALITY_VARIABLES) and
                sorted(s["decoded_rows"]) == sorted(QUALITY_VARIABLES) and
                sorted(s["sentinel_rows"]) == sorted(QUALITY_VARIABLES) and
                all(0 <= s["decoded_rows"][v] <= s["data_rows"] and 0 <= s["sentinel_rows"][v] <= s["data_rows"]
                    for v in QUALITY_VARIABLES) and
                s["header_sha256"] == sha256_bytes(",".join(s["header_columns"]).encode("utf-8")) and
                s["pilot_rows"] == len(s["pilot_keys"]) and s["pilot_keys"] == sorted(s["pilot_keys"]) and
                ((s["first_observed_at_utc"] is None) == (s["distinct_timestamps"] == 0)) and
                (s["first_observed_at_utc"] is None or s["first_observed_at_utc"] <= s["last_observed_at_utc"]) and
                s["station_value_check"] in ("ALL_ROWS_EQUAL_FILE_ID", "STATION_VALUE_MISMATCH") and
                s["calendar_year_check"] in ("ALL_ROWS_IN_CALENDAR_YEAR", "CALENDAR_YEAR_MISMATCH"))
            if not counts_ok:
                _refuse("WEATHER_STATION_YEAR_COUNT_INVALID", f"station-year {key} counts are inconsistent")
            for stamp in (s["first_observed_at_utc"], s["last_observed_at_utc"]):
                if stamp is not None and not str(stamp).startswith(f"{s['calendar_year']}-"):
                    _refuse("WEATHER_CALENDAR_YEAR_MISMATCH", f"station-year {key} observation outside its year")

    def _verify_witnesses(self, witnesses: list[dict[str, Any]], stations: dict[str, dict[str, Any]],
                          pilots: dict[str, dict[str, Any]]) -> None:
        a = self.anchors
        inputs = a["inputs"]
        for w in witnesses:
            kind, key = w["witness_kind"], w["witness_key"]
            if kind == "INPUT":
                name = key.split("|", 1)[1]
                spec = inputs.get(name)
                want = _witness_record(_witness_input(name, spec)) if spec else None
                if want is None or canonical_json_bytes(w) != canonical_json_bytes(want):
                    _refuse("WEATHER_WITNESS_MISMATCH", f"input witness {key} differs from the pinned input")
            elif kind == "PARENT_CONTRACT":
                rel = key.split("|", 1)[1]
                want = _witness_record({"witness_key": key, "witness_kind": kind, "relative_path": rel,
                                        "sha256": a["parent_contracts"].get(rel), "role": "PARENT_CONTRACT"})
                if rel not in a["parent_contracts"] or canonical_json_bytes(w) != canonical_json_bytes(want):
                    _refuse("WEATHER_WITNESS_MISMATCH", f"contract witness {key} differs from the pin")
            elif kind == "RAW_FILE":
                sk = key.split("|", 1)[1]
                spec, station = a["raw"].get(sk), stations.get(sk)
                if spec is None or station is None:
                    _refuse("WEATHER_WITNESS_MISMATCH", f"raw witness {key} names no pinned capture")
                want = _witness_record({"witness_key": key, "witness_kind": kind,
                                        "relative_path": spec["raw_relative_path"], "sha256": spec["raw_sha256"],
                                        "bytes": spec["raw_bytes"], "role": "RAW_NOAA_ISD_STATION_YEAR_CSV",
                                        "rows": station["data_rows"], "dataset_identity": None,
                                        "issued_at_utc": a["clocks"]["capture_manifest_issued_at_utc"],
                                        "source_id": WEATHER_SOURCE_ID, "station_year_key": sk,
                                        "station_id": sk.split("|", 1)[1]})
                if canonical_json_bytes(w) != canonical_json_bytes(want):
                    _refuse("WEATHER_WITNESS_MISMATCH", f"raw witness {key} differs from its capture")
            else:
                self._verify_row_witness(w, stations, pilots)

    def _verify_row_witness(self, w: dict[str, Any], stations: dict[str, dict[str, Any]],
                            pilots: dict[str, dict[str, Any]]) -> None:
        key = w["witness_key"]
        station = stations.get(w["station_year_key"])
        if station is None or w["station_id"] != station["station_id"]:
            _refuse("WEATHER_TRANSPLANT", f"row witness {key} names no captured station-year")
        nulls = ("relative_path", "sha256", "bytes", "role", "rows", "dataset_identity", "issued_at_utc", "source_id")
        if any(w[f] is not None for f in nulls) or w["raw_fields"] is None or w["timestamp_candidates"] is None or \
                w["raw_row_sha256"] is None or not IDENTITY_RE.match(w["raw_row_sha256"]):
            _refuse("WEATHER_WITNESS_MISMATCH", f"row witness {key} members are not a selected-row witness")
        fields = w["raw_fields"]
        if fields.get("STATION") != station["station_file_id"] or \
                not str(fields.get("DATE", "")).startswith(f"{station['calendar_year']}-"):
            _refuse("WEATHER_TRANSPLANT", f"row witness {key} raw station/date is not its station-year")
        extra = sorted(c for c in fields if c not in WITNESS_COLUMNS and not c.startswith("AA"))
        if extra or any(c.startswith("AA") and not v for c, v in fields.items()) or \
                any(c not in station["header_columns"] for c in fields):
            _refuse("WEATHER_WITNESS_MISMATCH", f"row witness {key} raw columns {extra or sorted(fields)[:4]}")
        try:
            decoded = decode_row(fields, w["source_row_number"], f"row witness {key}")
        except WeatherError:
            raise  # a scaled raw integer without a finite binary64 value: refused by the decoding boundary itself
        except (ValueError, TypeError) as exc:
            raise WeatherError("WEATHER_DECODE_MISMATCH", f"row witness {key} raw DATE does not decode: {exc}") from exc
        for name, _code in OBSERVATION_FIELDS:
            if name in ("source_row_number", "raw_tmp", "raw_dew", "raw_wnd", "raw_vis", "raw_slp"):
                continue
            if not _same(w[f"row_{name}"], decoded[name]):
                _refuse("WEATHER_DECODE_MISMATCH", f"row witness {key}: {name} {w[f'row_{name}']!r} is not the "
                                                   f"decode {decoded[name]!r} of its raw fields")
        ranking = w["timestamp_candidates"]
        rows = [c["source_row_number"] for c in ranking]
        keys = [ranking_key(c["decoded_common_field_count"], c["report_type"], c["source_code"], c["source_row_number"])
                for c in ranking]
        first = ranking[0] if ranking else None
        if not ranking or len(set(rows)) != len(rows) or keys != sorted(keys) or \
                first["source_row_number"] != w["source_row_number"] or \
                first["decoded_common_field_count"] != w["row_decoded_common_field_count"] or \
                first["report_type"] != w["row_report_type"] or first["source_code"] != w["row_source_code"] or \
                len(ranking) > station["data_rows"]:
            _refuse("WEATHER_DUPLICATE_RANKING_INVALID", f"row witness {key} is not the best-ranked row of its "
                                                         "timestamp")
        cited = set()
        for entry in w["selected_by"]:
            game, _sep, role = entry.partition(":")
            pilot = pilots.get(game)
            if pilot is None or role not in SELECTION_ROLES or \
                    pilot[f"{role.lower()}_witness_key"] != key:
                _refuse("WEATHER_WITNESS_LINK_MISMATCH", f"row witness {key} cites {entry!r}")
            cited.add(entry)
        if not cited or w["selected_by"] != sorted(cited):
            _refuse("WEATHER_WITNESS_LINK_MISMATCH", f"row witness {key} selections are not its pilot citations")

    def _verify_pilots(self, pilots: list[dict[str, Any]], stations: dict[str, dict[str, Any]],
                       witnesses: dict[str, dict[str, Any]], contests: dict[str, dict[str, Any]]) -> None:
        a = self.anchors
        expected = a["expected"]
        originals = []
        assignment = []
        clocks = []
        relations = []
        for index, p in enumerate(pilots):
            key = p["pilot_key"]
            if p["original_row_index"] != index:
                _refuse("WEATHER_KEY_INVALID", f"pilot {key} original_row_index {p['original_row_index']}")
            for name, flag_code in ORIGINAL_FALSE_FLAGS.items():
                if p[f"original_{name}"] is not False:
                    _refuse(flag_code, f"pilot {key}: original {name} is {p[f'original_{name}']!r}")
            for name, value in ORIGINAL_CONSTANTS.items():
                if not _same(p[f"original_{name}"], value):
                    _refuse("WEATHER_ORIGINAL_CLAIM_INVALID", f"pilot {key}: original {name}")
            originals.append(canonical_line({name: p[f"original_{name}"] for name in ORIGINAL_NAMES}))
            assignment.append(f"{key}|{p['station_year_key']}")
            clocks.append(f"{key}|{p['provider_scheduled_start_utc']}|{p['provider_start_time_tbd']}")
            relations.append(f"{key}|{p['provider_row_key']}|{p['relation_state']}|{p['contest_key']}|"
                             f"{p['candidate_contest_key']}")
        if keys_sha256(originals) != expected["pilot_originals_sha256"]:
            _refuse("WEATHER_ORIGINAL_ALTERED", "the original pilot fields differ from the pinned original rows")
        if keys_sha256(assignment) != expected["pilot_station_year_sha256"]:
            _refuse("WEATHER_TRANSPLANT", "a pilot row names another station-year than its original capture")
        if keys_sha256(clocks) != expected["provider_clock_sha256"]:
            _refuse("WEATHER_SOURCE_CLOCK_MISMATCH", "the provider scheduled starts differ from the pinned capture")
        if keys_sha256(relations) != expected["pilot_relation_sha256"]:
            _refuse("WEATHER_RELATION_MISMATCH", "the pilot relations differ from the accepted C48 relations")
        for p in pilots:
            self._verify_pilot(p, stations, witnesses, contests)

    def _verify_pilot(self, p: dict[str, Any], stations: dict[str, dict[str, Any]],
                      witnesses: dict[str, dict[str, Any]], contests: dict[str, dict[str, Any]]) -> None:
        key = p["pilot_key"]
        kickoff_text = p["original_kickoff_at_utc"]
        try:
            kickoff = parse_utc(kickoff_text)
        except (ValueError, TypeError) as exc:
            raise WeatherError("WEATHER_ORIGINAL_ALTERED", f"pilot {key} kickoff does not parse") from exc
        if p["original_calendar_year"] not in CALENDAR_YEARS:
            _refuse("WEATHER_SEASON_OUT_OF_RANGE", f"pilot {key} calendar year")
        station = stations.get(p["station_year_key"])
        if station is None or p["station_year_key"] != f"{p['original_calendar_year']}|{p['original_station_id']}" \
                or key not in station["pilot_keys"]:
            _refuse("WEATHER_TRANSPLANT", f"pilot {key} station-year {p['station_year_key']!r}")
        if p["provider_join_state"] not in PROVIDER_JOIN_STATES or \
                (p["provider_join_state"] == "EXACT_CAPTURED_PROVIDER_GAME") != (p["provider_game_id"] is not None) or \
                (p["provider_game_id"] is not None and (p["provider_game_id"] != key or
                                                        not PROVIDER_ROW_RE.match(p["provider_row_key"] or ""))):
            _refuse("WEATHER_PROVIDER_JOIN_MISMATCH", f"pilot {key} provider join")
        start = p["provider_scheduled_start_utc"]
        agreement = "NOT_COMPARABLE" if start is None else ("AGREE" if start == kickoff_text else "DIFFER")
        if p["kickoff_clock_agreement"] != agreement:
            _refuse("WEATHER_SOURCE_CLOCK_MISMATCH", f"pilot {key} association clock agreement")
        if p["relation_state"] not in RELATION_STATES or \
                (p["relation_state"] == "PROMOTED_ONE_TO_ONE") != (p["contest_key"] is not None) or \
                (p["relation_state"] == "PROMOTED_ONE_TO_ONE" and p["candidate_contest_key"] is not None) or \
                (p["contest_key"] is not None and (contests.get(p["contest_key"]) or {}).get("pilot_key") != key):
            _refuse("WEATHER_RELATION_MISMATCH", f"pilot {key} relation")
        # ---- the reconstructed candidates from their raw-row witnesses
        observed: dict[str, dict[str, Any] | None] = {}
        for role in ("before", "after", "nearest"):
            wkey = p[f"{role}_witness_key"]
            if wkey is None:
                observed[role] = None
                continue
            w = witnesses.get(wkey)
            if w is None or w["witness_kind"] != "SELECTED_RAW_ROW" or w["station_year_key"] != p["station_year_key"]:
                _refuse("WEATHER_TRANSPLANT", f"pilot {key} {role} witness {wkey!r} is not a row of its station-year")
            if f"{key}:{role.upper()}" not in w["selected_by"]:
                _refuse("WEATHER_WITNESS_LINK_MISMATCH", f"pilot {key} {role} witness does not cite it")
            observed[role] = w
        before, after, nearest = observed["before"], observed["after"], observed["nearest"]
        for role, w in (("before", before), ("after", after)):
            stamp = p[f"verified_{role}_observed_at_utc"]
            if (w is None) != (stamp is None) or (w is not None and (w["row_observed_at_utc"] != stamp or
                                                                     p[f"verified_{role}_source_row_number"] !=
                                                                     w["source_row_number"])) or \
                    (w is None and p[f"verified_{role}_source_row_number"] is not None):
                _refuse("WEATHER_NEAREST_MISMATCH", f"pilot {key} {role} candidate differs from its witness")
        try:
            before_delta = minutes((kickoff - parse_utc(before["row_observed_at_utc"])).total_seconds()) \
                if before else None
            after_delta = minutes((parse_utc(after["row_observed_at_utc"]) - kickoff).total_seconds()) \
                if after else None
        except (ValueError, TypeError) as exc:
            raise WeatherError("WEATHER_DECODE_MISMATCH", f"pilot {key} candidate time does not parse") from exc
        if not _same(p["verified_before_delta_minutes"], before_delta) or \
                not _same(p["verified_after_delta_minutes"], after_delta):
            _refuse("WEATHER_DELTA_MISMATCH", f"pilot {key} candidate distances differ from their timestamps")
        if (before_delta is not None and before_delta < 0) or (after_delta is not None and after_delta < 0) or \
                (before is not None and after is not None and before["source_row_number"] != after["source_row_number"]
                 and (before_delta == 0 or after_delta == 0)):
            _refuse("WEATHER_CANDIDATE_ORDER_INVALID", f"pilot {key} candidates are not before/after the clock")
        if before is None:
            want_nearest = after
        elif after is None:
            want_nearest = before
        else:
            want_nearest = before if abs(before_delta) <= abs(after_delta) else after
        if (want_nearest is None) != (nearest is None) or \
                (nearest is not None and nearest["witness_key"] != want_nearest["witness_key"]):
            _refuse("WEATHER_TIE_RULE_VIOLATED", f"pilot {key} nearest is not the earlier-wins nearest candidate")
        nearest_delta = None if nearest is None else (before_delta if nearest is before else after_delta)
        if nearest is not None and before is not None and after is not None and \
                before["witness_key"] == after["witness_key"]:
            nearest_delta = 0.0 if before_delta == 0 else nearest_delta
        if p["verified_nearest_observation_state"] != ("PRESENT" if nearest else "MISSING") or \
                not _same(p["verified_nearest_absolute_delta_minutes"],
                          None if nearest_delta is None else abs(nearest_delta)):
            _refuse("WEATHER_DELTA_MISMATCH", f"pilot {key} nearest distance or state")
        for name, _code in OBSERVATION_FIELDS:
            got = p[f"verified_nearest_{name}"]
            if nearest is None:
                want = None
            elif name == "source_row_number":
                want = nearest["source_row_number"]
            elif name.startswith("raw_"):
                want = nearest["raw_fields"].get(name[4:].upper(), "")
            else:
                want = nearest[f"row_{name}"]
            if not _same(got, want):
                _refuse("WEATHER_NEAREST_MISMATCH", f"pilot {key}: verified nearest {name} {got!r} is not its "
                                                    f"witness's {want!r}")
        for role in ("before", "after"):
            want = None if p[f"verified_{role}_observed_at_utc"] is not None else MISSING_REASONS[role]
            if p[f"{role}_missing_reason"] != want:
                _refuse("WEATHER_MISSING_REASON_INVALID", f"pilot {key} {role} missing reason")
        raw = self.anchors["raw"]
        year, station_id = p["original_calendar_year"], p["original_station_id"]
        adjacent = (p["verified_before_observed_at_utc"] is None and f"{year - 1}|{station_id}" in raw) or \
            (p["verified_after_observed_at_utc"] is None and f"{year + 1}|{station_id}" in raw)
        if p["adjacent_calendar_year_captured"] is not bool(adjacent):
            _refuse("WEATHER_MISSING_REASON_INVALID", f"pilot {key} adjacent calendar-year capture flag")
        # ---- discrepancies against the original pilot
        discrepant = [f for f in GOVERNED_FIELDS if not _same(p[f"original_{f}"], p[f"verified_{f}"])]
        checks = {"calendar_year": kickoff.year, "station_file_id": station_id.replace("-", ""),
                  "station_snapshot_id": station["snapshot_id"], "station_raw_sha256": station["raw_sha256"],
                  "station_request_identity_sha256": station["request_identity_sha256"],
                  "row_lineage_sha256": lineage_sha256(p["original_source_game_id"], kickoff_text, station_id,
                                                       station["raw_sha256"], p["verified_nearest_observed_at_utc"])}
        discrepant += [f for f, v in checks.items() if not _same(p[f"original_{f}"], v)]
        claimed = set(p["discrepant_fields"])
        derivable = set(GOVERNED_FIELDS) | set(checks)
        if {f for f in claimed if f in derivable} != set(discrepant) or \
                not claimed <= set(GOVERNED_FIELDS) | set(CHECKED_ORIGINAL_FIELDS) or \
                p["discrepant_fields"] != sorted(claimed) or \
                p["reconstruction_state"] != ("REPRODUCED_EXACT" if not claimed else "DISCREPANT"):
            _refuse("WEATHER_DISCREPANCY_MISMATCH", f"pilot {key} discrepancy disposition differs from the "
                                                    "original/verified comparison")
        if p["nearest_report_meaning"] != report_meaning(p["verified_nearest_report_type"]) or \
                any(p[f"{v}_quality_meaning"] != quality_meaning(p[f"verified_nearest_{v}_quality"])
                    for v in QUALITY_VARIABLES) or \
                p["nearest_precipitation_groups"] != precipitation_groups(p["verified_nearest_precipitation_raw_json"]):
            _refuse("WEATHER_MEANING_MISMATCH", f"pilot {key} official meanings differ from its codes")
        if p["unsupported_reasons"] != pilot_reasons(p):
            _refuse("WEATHER_UNSUPPORTED_REASON_MISMATCH", f"pilot {key} unsupported reasons differ from its fields")

    def _verify_contests(self, contests: list[dict[str, Any]], pilots: dict[str, dict[str, Any]],
                         stations: dict[str, dict[str, Any]]) -> None:
        a = self.anchors
        expected = a["expected"]
        parents, relations = [], []
        for c in contests:
            key = c["contest_key"]
            if c["season"] != FOOTBALL_SEASON:
                _refuse("WEATHER_SEASON_OUT_OF_RANGE", f"contest {key} season {c['season']}")
            try:
                year = int(str(c["contest_date"])[:4])
            except ValueError as exc:
                raise WeatherError("WEATHER_CALENDAR_YEAR_MISMATCH", f"contest {key} date") from exc
            if c["contest_calendar_year"] != year or year not in CALENDAR_YEARS:
                _refuse("WEATHER_CALENDAR_YEAR_MISMATCH", f"contest {key} calendar year")
            parents.append(canonical_line({name: c[name] for name in PARENT_COLUMNS
                                           if name not in ("disposition", "disposition_reason",
                                                           "reconciliation_state", "exposure")} |
                                          {"disposition": c["parent_disposition"],
                                           "disposition_reason": c["parent_disposition_reason"],
                                           "reconciliation_state": c["parent_reconciliation_state"],
                                           "exposure": c["parent_exposure"]}))
            relations.append(f"{key}|{c['alias_disposition']}|{c['alias_disposition_reason']}|"
                             f"{c['alias_route_scope']}|{','.join(c['alias_field_conflicts'])}|"
                             f"{','.join(c['alias_candidate_provider_row_keys'])}|"
                             f"{c['alias_relation_provider_row_key']}|{c['alias_relation_provider_game_id']}|"
                             f"{c['relation_state']}|{c['provider_row_key']}|{c['pilot_key']}")
        if keys_sha256(parents) != expected["contest_parents_sha256"]:
            _refuse("WEATHER_PARENT_FIELD_MISMATCH", "the contest participant/site/date fields differ from the "
                                                     "accepted parent")
        if keys_sha256(relations) != expected["contest_relation_sha256"]:
            _refuse("WEATHER_RELATION_MISMATCH", "the contest relations differ from the accepted C48 reconciliation")
        for c in contests:
            key = c["contest_key"]
            pilot = pilots.get(c["pilot_key"]) if c["pilot_key"] is not None else None
            if c["relation_state"] not in RELATION_STATES or \
                    (c["relation_state"] == "PROMOTED_ONE_TO_ONE") != (pilot is not None) or \
                    (pilot is not None and (pilot["contest_key"] != key or
                                            pilot["provider_row_key"] != c["provider_row_key"] or
                                            pilot["provider_game_id"] != c["provider_game_id"] or
                                            c["provider_row_key"] != c["alias_relation_provider_row_key"] or
                                            c["provider_game_id"] != c["alias_relation_provider_game_id"])) or \
                    (pilot is None and (c["provider_row_key"] is not None or c["provider_game_id"] is not None)) or \
                    (c["relation_state"] == "CANDIDATE_NOT_PROMOTED") != \
                    (pilot is None and c["alias_relation_provider_row_key"] is not None) or \
                    (c["relation_state"] == "NO_PROVIDER_ROW") != (c["alias_relation_provider_row_key"] is None):
                _refuse("WEATHER_RELATION_MISMATCH", f"contest {key} relation")
            present = pilot is not None and pilot["verified_nearest_observation_state"] == "PRESENT"
            if pilot is not None:
                support = "ASSOCIATED_CANDIDATE_STATION_OBSERVATION" if present else "ASSOCIATED_NO_OBSERVATION"
            elif c["relation_state"] == "CANDIDATE_NOT_PROMOTED":
                support = "UNSUPPORTED_RELATION_NOT_PROMOTED"
            else:
                support = "UNSUPPORTED_NO_PROVIDER_ROW"
            if c["weather_support_state"] != support:
                _refuse("WEATHER_SUPPORT_STATE_INVALID", f"contest {key} support state {c['weather_support_state']!r}")
            station = stations.get(pilot["station_year_key"]) if pilot is not None else None
            want = {
                "station_year_key": pilot["station_year_key"] if pilot else None,
                "station_id": pilot["original_station_id"] if pilot else None,
                "station_name": pilot["original_station_name"] if pilot else None,
                "station_distance_km": pilot["original_distance_km"] if pilot else None,
                "station_elevation_m": station["candidate_station_elevation_m"] if station else None,
                "association_clock_utc": pilot["provider_scheduled_start_utc"]
                if pilot and pilot["kickoff_clock_agreement"] == "AGREE" else None,
                "provider_start_time_tbd": pilot["provider_start_time_tbd"] if pilot else None,
                "nearest_observed_at_utc": pilot["verified_nearest_observed_at_utc"] if present else None,
                "nearest_absolute_delta_minutes": pilot["verified_nearest_absolute_delta_minutes"] if present else None,
                "nearest_report_type": pilot["verified_nearest_report_type"] if present else None,
                "nearest_report_meaning": pilot["nearest_report_meaning"] if present else None,
                "before_present": (pilot["verified_before_observed_at_utc"] is not None) if pilot else None,
                "after_present": (pilot["verified_after_observed_at_utc"] is not None) if pilot else None,
                **{name: (pilot[f"verified_nearest_{name}"] if present else None) for name in NEAREST_SUMMARY},
                "reference_venue_id": pilot["original_venue_id"] if pilot else None,
                "reference_venue_name": pilot["original_venue_name"] if pilot else None,
                "reference_venue_dome": pilot["original_venue_dome"] if pilot else None}
            differing = sorted(f for f, v in want.items() if not _same(c[f], v))
            if differing:
                _refuse("WEATHER_ASSOCIATION_MISMATCH", f"contest {key} association fields {differing[:4]} differ "
                                                        "from its associated pilot (unsupported fields stay null)")
            if c["unsupported_reasons"] != contest_reasons(c, pilot):
                _refuse("WEATHER_UNSUPPORTED_REASON_MISMATCH", f"contest {key} unsupported reasons")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "WeatherEvidence":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- serving
    @staticmethod
    def filters(grain: str, *, season: Any = None, contest: Any = None, provider_game: Any = None,
                station: Any = None) -> dict[str, Any]:
        """Validate a selection before any file is read: an unknown grain, a malformed or an inapplicable selector is
        refused with its own code (SELECTOR_MATRIX)."""
        if grain not in GRAINS:
            _refuse("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}")
        allowed = SELECTOR_MATRIX[grain]
        filters: dict[str, Any] = {}
        for name, value in (("season", season), ("contest", contest), ("provider_game", provider_game),
                            ("station", station)):
            if value is not None and name not in allowed:
                _refuse("FILTER_NOT_APPLICABLE", f"{name} does not apply to the {grain} grain (allowed: {allowed})")
        if season is not None:
            if not is_int(season):
                _refuse("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if contest is not None:
            text = contest if isinstance(contest, str) else None
            if text is None or not CONTEST_KEY_RE.match(text):
                _refuse("CONTEST_INVALID", f"contest must be an exact parent contest key ncaa:<digits> or "
                                           f"nolink:2024:<date>:org:<digits>|org:<digits>, got {contest!r}")
            filters["contest"] = text
        if provider_game is not None:
            text = provider_game if isinstance(provider_game, str) else None
            if text is None or not PROVIDER_GAME_RE.match(text):
                _refuse("PROVIDER_GAME_INVALID", f"provider game must be an exact SRC-002 game ID (digits), got "
                                                 f"{provider_game!r}")
            filters["provider_game"] = text
        if station is not None:
            text = station if isinstance(station, str) else None
            if text is None or not STATION_RE.match(text):
                _refuse("STATION_INVALID", f"station must be an exact NOAA ISD station identity NNNNNN-NNNNN, got "
                                           f"{station!r}")
            filters["station"] = text
        return filters

    def source_time(self) -> dict[str, Any]:
        clocks = self.anchors["clocks"]
        return {"observation_clock": "ISD_DATE_UTC_PER_ROW (each observation's own UTC time; not a publication or "
                                     "known-at time)",
                "association_clock": "PROVIDER_SCHEDULED_TIME_NOT_OFFICIAL_ACTUAL_KICKOFF",
                "provider_capture_known_at_utc": clocks["provider_capture_known_at_utc"],
                "capture_manifest_issued_at_utc": clocks["capture_manifest_issued_at_utc"],
                "acquisition_issued_at_utc": clocks["acquisition_issued_at_utc"],
                "pilot_issued_at_utc": clocks["pilot_issued_at_utc"],
                "source_publication_time": "NOT_ESTABLISHED",
                "release_provenance_issued_at_utc": (self.binding.get("provenance") or {}).get("issued_at_utc")
                if isinstance(self.binding.get("provenance"), dict) else None,
                "release_provenance_note": "the run manifest's provenance build clock; not identity-bound"}

    def query(self, grain: str, *, season: Any = None, contest: Any = None, provider_game: Any = None,
              station: Any = None, limit: int | None = 50, offset: int = 0, all_rows: bool = False) -> dict[str, Any]:
        filters = self.filters(grain, season=season, contest=contest, provider_game=provider_game, station=station)
        if not is_int(offset) or offset < 0:
            _refuse("NEGATIVE_OFFSET", "offset must be a zero or positive integer")
        if limit is not None and (not is_int(limit) or limit < 0):
            _refuse("NEGATIVE_LIMIT", "limit must be a zero or positive integer")
        table = GRAINS[grain]
        census = self.census
        result: dict[str, Any] = {
            "release_identity": self.database_identity, "content_identity": self.content_identity,
            "contract_id": self.anchors["contract_id"], "contract_sha256": self.anchors["contract_sha256"],
            "population": POPULATION, "grain": grain, "filters": filters, "offset": offset,
            "limit": None if all_rows else limit, **LABELS, "source_time": self.source_time(),
            "denominators": {k: census[k] for k in ("contests", "pilots", "station_years", "witnesses")},
            "relation_counts": {k: census[k] for k in ("promoted_relations", "unpromoted_relations",
                                                       "parents_without_promoted_weather")},
            "verification": {f"{t}_verified": len(self.records[t]) for t in RECORD_TABLES} | {
                "records_verified": True, "content_identity_rebuilt": True, "database_document_rebuilt": True,
                "profile_pinned": self.anchors.get("profile") is not None}}
        if "season" in filters and filters["season"] != FOOTBALL_SEASON:
            result.update(season_scope_state="SEASON_OUTSIDE_RELEASE", total=0, returned=0, rows=[], next_offset=None,
                          note=f"the release covers football season {FOOTBALL_SEASON} only; no row is fabricated for "
                               "another season")
            return result
        rows = [r for r in self.records[table] if self._match(grain, r, filters)]
        total = len(rows)
        page = rows[offset:] if all_rows else rows[offset:offset + (limit or 0)]
        result.update(season_scope_state="RETROSPECTIVE_SEASON_2024", total=total, returned=len(page), rows=page,
                      next_offset=offset + len(page) if offset + len(page) < total else None)
        return result

    @staticmethod
    def _match(grain: str, record: dict[str, Any], filters: dict[str, Any]) -> bool:
        if "contest" in filters:
            if grain == "contest-weather" and record["contest_key"] != filters["contest"]:
                return False
            if grain == "pilot-weather" and record["contest_key"] != filters["contest"]:
                return False
        if "provider_game" in filters and record["provider_game_id"] != filters["provider_game"]:
            return False
        if "station" in filters:
            value = record["original_station_id"] if grain == "pilot-weather" else record["station_id"]
            if value != filters["station"]:
                return False
        return True


def segment_of_untrusted(table: str, record: dict[str, Any]) -> str | None:
    """The segment a possibly malformed record would sit in (None when its segment field is not a valid value)."""
    try:
        if table == "contests":
            value = record.get("contest_calendar_year")
            return str(value) if type(value) is int else None
        if table == "pilots":
            value = record.get("original_calendar_year")
            return str(value) if type(value) is int else None
        if table == "station_years":
            value = record.get("calendar_year")
            return str(value) if type(value) is int else None
        if table == "witnesses":
            if record.get("witness_kind") != "SELECTED_RAW_ROW":
                return "SOURCE"
            value = record.get("station_year_key")
            return str(value).split("|", 1)[0] if isinstance(value, str) else None
    except (AttributeError, TypeError):
        return None
    return "GLOBAL"


def source_order(anchors: dict[str, Any]) -> dict[str, int]:
    """The contract order of the input and parent-contract witnesses (their position in the pinned anchors)."""
    keys = [f"INPUT|{n}" for n in anchors["inputs"]] + [f"CONTRACT|{rel}" for rel in anchors["parent_contracts"]]
    return {key: index for index, key in enumerate(keys)}


def _order_key(table: str, record: dict[str, Any], sources: dict[str, int] | None = None) -> tuple[Any, ...]:
    if table == "contests":
        return (str(record["contest_date"]), str(record["contest_key"]))
    if table == "pilots":
        return (record["original_kickoff_at_utc"], record["pilot_key"])
    if table == "station_years":
        return (record["calendar_year"], record["station_id"])
    if table == "witnesses":
        kind = record["witness_kind"]
        rank = WITNESS_KINDS.index(kind)
        if kind == "SELECTED_RAW_ROW":
            year, station = str(record["station_year_key"]).split("|", 1)
            return (rank, int(year), station, int(record["source_row_number"]))
        if kind == "RAW_FILE":
            year, station = str(record["station_year_key"]).split("|", 1)
            return (rank, int(year), station, 0)
        return (rank, (sources or {}).get(record["witness_key"], 10 ** 6), "", 0)
    return (0,)
