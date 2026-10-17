r"""National personnel evidence 2004-2022 (BAT-730 bounded personnel contribution to BAT-411/BAT-415, Cycle #59 TP59-A01).

Every rule lives here, and the committed data contract ``configs/national_personnel_evidence_2004_2022_contract.json``
must equal these constants (the builder refuses otherwise). The reader pins that contract's SHA-256, every retained
input's SHA-256 and the canonical release profile (:data:`ANCHORS`, generated into :mod:`.anchors`).

Inputs, each resolved under an explicitly named data root at the contract's relative locator and refused unless its
bytes hash to the pinned SHA-256 (nothing here is acquired; no source request is made). Parquet is read only through the
pinned Polars decoder (an optional data dependency imported by :func:`load_inputs` alone); every set, sum, join and rule
below is plain Python over the decoded values:

* the retained BAT-546 season-roster membership parent 3e3da7de (154,387 admitted rows 2004-2022, its manifest and its
  separate nonadmitted quarantine of 52,386 rows), the BAT-523 candidate reconciliation 17e42ac1 (its manifest and the
  19 season files that hold each row's raw source row number) and the 19 raw cfbfastR roster captures;
* the retained BAT-542 player event metric parent c6baa76b (289,897 sparse 2014-2022 rows; 2020 partial), its manifest,
  its candidate manifest 869818c5 and the 9 raw cfbfastR player-stat captures;
* the retained BAT-415 returning-production research 4eb29ad4 (982 transitions, 5,867 components, 8 coverage rows) as
  the original to compare against -- never as the source of the recomputed values;
* the accepted BAT-710 parent population 3baff07f (every 2016-2022 contest and both participants' source divisions),
  the accepted C38 participant identity bindings (``org_id`` -> ``cfbd_team_id`` only under NAME_CONFIRMED_BY_SCHEDULE
  or SCHEDULE_FINGERPRINT_ONLY) and the BAT-387 core registry (``cfbd_team_id`` -> canonical team only through an
  accepted SRC-002 team ENTITY row with identity key TEAM|SRC-002|<id>; SRC-001 SOURCE_MAPPING rows are ESPN evidence
  and an equal numeric ID never joins).

Derived records (one immutable, create-only, content-addressed release; every row stays in its grain):

1. **roster-membership** -- an exact projection of every admitted parent row (all 30 parent fields, missing physical,
   class and position values kept null, the source clock and lineage unchanged) with its raw source row number, its
   same-season team count (multi-team player-seasons kept as distinct associations) and its census association.
2. **roster-exclusion** -- one safe keyed record per nonadmitted row: identifiers, disposition, admission state and
   lineage only (no name, team label, physical, hometown, geocode, headshot, recruiting or current-comparison payload);
   canonical identifiers stay as retained (often null) under UNRESOLVED_OR_NONADMITTED, never promoted; duplicate
   source keys are counted, never collapsed.
3. **program-season-coverage** -- every 2016-2022 program-season enumerated from both participants of every accepted
   parent contest whose source division is FBS or FCS: names, divisions and contest witnesses, the documented
   org -> CFBD -> canonical team chain with its state and reason, admitted roster presence (not completeness) and
   returning-transition presence; an unqualified chain keeps its person counts null (unknown, never zero).
4. **returning-component** -- for each same-team prior/target roster pair with prior-season metrics, the six frozen
   category/stat pairs: prior and returning numerators over canonical player sets, the ratio, its semantics and
   unit-interval flag (13 signed-yardage ratios outside [0,1] kept unclipped; count shares bounded), metric player
   counts, the partial-2020 flag and the agreement with the retained original.
5. **returning-summary** -- the 982 team transitions: prior, current, returning, departed, arrival and union counts, the
   exact rates, the six shares (absent evidence null, never zero), the partial 2020->2021 state, the original research
   identity and agreement, and the census association of both seasons (out-of-census reasons kept).
6. **source-witness** -- the complete ordered provenance of every pinned input and parent contract: locator, bytes,
   rows, dataset identity, capture, repository commit time (2023-05-05T03:50:21Z, the source clock), capture and parent
   build clocks and the private-research rights boundary.
7. **census** -- counts of every grain and state, the 8 recomputed transition coverage rows and the original agreement.

Every record carries RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED and predictive skill NOT_ESTABLISHED.
Season roster presence is not completeness, game availability, depth, starter, injury or eligibility evidence; an
arrival or departure between seasonal snapshots is not a transfer episode, effective date or cause; the parent's
development-only admission and May 2023 source clock are preserved, never extended or backcast.

The reader (:class:`PersonnelEvidence`) needs no data root: it refuses with a stable code unless the location, the run
manifest, the database bytes, the schema, every meta claim, every record's exact members and JSON types, the complete
expected collection of every grain, every rule that can be re-derived from the records themselves (returning sets,
rates, shares, foreign keys, census associations, coverage counts, duplicate diagnoses, witnesses and the census), the
content document, the contract-defined database identity document and the pinned canonical profile all verify. The
query (:meth:`PersonnelEvidence.query`) serves the six grains with exact intersecting selectors and paging.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import math
import os
import random
import re
import sqlite3
import sys
import zlib
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
IDENTITY_RE = bm.IDENTITY_RE

# --------------------------------------------------------------------------------------------- identity and scope

POPULATION = "national_personnel_evidence_2004_2022"
DB_FILE = "national_personnel_evidence.sqlite"
CONTRACT_ID = "BAT-730-NATIONAL-PERSONNEL-EVIDENCE-2004-2022-V1.0"
CONTRACT_REL = "configs/national_personnel_evidence_2004_2022_contract.json"
CONTENT_SCHEMA = "BAS-PERSONNEL-EVIDENCE-CONTENT-1"
DATABASE_SCHEMA = "BAS-PERSONNEL-EVIDENCE-DATABASE-1"
DB_SCHEMA = "BAS-PERSONNEL-EVIDENCE-DB-1"
PAYLOAD_SCHEMA = "BAS-PERSONNEL-EVIDENCE-PAYLOAD-1"

ROSTER_SEASONS = tuple(range(2004, 2023))
CENSUS_SEASONS = tuple(range(2016, 2023))
TARGET_SEASONS = tuple(range(2015, 2023))
METRIC_SEASONS = tuple(range(2014, 2023))
PARTIAL_METRIC_SEASONS = (2020,)
CENSUS_DIVISIONS = ("FBS", "FCS")
SOURCE_KNOWN_AT = "2023-05-05T03:50:21Z"
SOURCE_COMMIT = "b865176f908cb6b791dc8e14562c52676f456275"
SOURCE_REPOSITORY = "sportsdataverse/cfbfastR-data"
RETURNING_CLASSIFICATION = "DEVELOPMENT_ONLY_RETROSPECTIVE_RETURNING_PRODUCTION_RESEARCH"

LABELS = {
    "evidence_label": "RETROSPECTIVE_RESEARCH",
    "trust_state": "UNTRUSTED_SHADOW",
    "pit_eligibility": "PIT_NOT_ADMITTED",
    "predictive_skill": "NOT_ESTABLISHED",
    "forecast_status": "NOT_A_FORECAST",
    "source_clock": "SOURCE_REPOSITORY_COMMIT_2023-05-05T03:50:21Z_NOT_A_HISTORICAL_EFFECTIVE_TIME",
    "effective_grain": "SEASON_ONLY_NO_EFFECTIVE_DAY_INFERRED",
    "parent_authority": "ORIGINAL_DEVELOPMENT_ONLY_PARENT_ADMISSION_PRESERVED_NOT_EXTENDED_OR_BACKCAST",
    "membership_meaning": "SEASON_ROSTER_PRESENCE_NOT_COMPLETENESS_AVAILABILITY_DEPTH_STARTER_INJURY_OR_ELIGIBILITY",
    "exclusion_meaning": "NONADMITTED_SOURCE_EVIDENCE_NEVER_PROMOTED_OR_MERGED",
    "coverage_meaning": "RETAINED_EVIDENCE_PRESENCE_NOT_ROSTER_COMPLETENESS_UNKNOWN_COUNTS_NULL",
    "transition_meaning": "SEASONAL_SNAPSHOT_SET_DIFFERENCE_NOT_A_TRANSFER_EPISODE_EFFECTIVE_DATE_OR_CAUSE",
    "rights": "PRIVATE_RESEARCH_ONLY_NO_RAW_PAYLOAD_REDISTRIBUTION",
}
BASE_LABEL_KEYS = ("evidence_label", "trust_state", "pit_eligibility", "predictive_skill")
GRAIN_LABEL_KEYS = {
    "memberships": BASE_LABEL_KEYS + ("membership_meaning",),
    "exclusions": BASE_LABEL_KEYS + ("exclusion_meaning",),
    "program_seasons": BASE_LABEL_KEYS + ("coverage_meaning",),
    "summaries": BASE_LABEL_KEYS + ("transition_meaning",),
    "components": BASE_LABEL_KEYS + ("transition_meaning",),
    "witnesses": BASE_LABEL_KEYS + ("rights",),
    "census": BASE_LABEL_KEYS,
}

# --------------------------------------------------------------------------------------------- source schemas

#: The membership parent's physical columns, in order: the 24 admitted fields of its contract, then its six states.
MEMBERSHIP_PARENT_FIELDS = (
    "observation_id", "athlete_id", "canonical_player_id", "canonical_team_id", "canonical_team_label", "first_name",
    "last_name", "team", "position", "class_year", "jersey", "height", "weight", "home_city", "home_state",
    "home_country", "season", "source_capture_id", "source_payload_sha256", "source_commit_sha", "source_known_at_utc",
    "source_schema_sha256", "source_record_evidence_sha256", "row_lineage_sha256", "membership_effective_grain",
    "membership_effective_day_utc", "season_roster_membership", "game_time_availability", "depth_or_starter_status",
    "protected_eligible")
ADMITTED_FIELDS = MEMBERSHIP_PARENT_FIELDS[:24]
MEMBERSHIP_STATES = {"membership_effective_grain": "SEASON", "membership_effective_day_utc": None,
                     "season_roster_membership": True, "game_time_availability": False,
                     "depth_or_starter_status": False, "protected_eligible": False}
#: The candidate reconciliation's (and the nonadmitted quarantine's) physical columns, in order.
CANDIDATE_FIELDS = (
    "schema_version", "observation_id", "source_row_number", "athlete_id", "athlete_id_occurrence", "canonical_player_id",
    "canonical_membership_player_id", "canonical_team_id", "canonical_team_label",
    "canonical_membership_resolution_state", "first_name", "last_name", "team", "weight", "height", "jersey",
    "class_year", "position", "home_city", "home_state", "home_country", "home_latitude", "home_longitude",
    "home_county_fips", "recruit_ids_json", "headshot_url", "season", "source_capture_id", "source_payload_sha256",
    "source_commit_sha", "source_known_at_utc", "source_schema_sha256", "source_record_evidence_sha256",
    "current_cfbd_id_match", "current_cfbd_name_match", "current_cfbd_match_count", "current_cfbd_name_match_count",
    "current_cfbd_team_name_match_count", "current_cfbd_match_ambiguous", "current_cfbd_capture_id",
    "current_cfbd_payload_sha256", "current_cfbd_request_sha256", "current_first_name", "current_last_name",
    "current_team", "current_weight", "current_height", "current_jersey", "current_class_year", "current_position",
    "team_label_exact_match", "canonical_membership_option_count", "canonical_membership_exact_team_option_count",
    "canonical_membership_ambiguous", "upstream_independence", "admission_state", "reconciliation_disposition",
    "downstream_pit_contract", "row_lineage_sha256")
#: TP59 section 3: the only nonadmitted source members a roster-exclusion record may carry.
EXCLUSION_SOURCE_FIELDS = (
    "observation_id", "source_row_number", "season", "athlete_id", "canonical_player_id",
    "canonical_membership_player_id", "canonical_team_id", "reconciliation_disposition", "admission_state",
    "source_capture_id", "source_payload_sha256", "source_commit_sha", "source_known_at_utc", "source_schema_sha256",
    "source_record_evidence_sha256", "row_lineage_sha256")
#: The membership parent contract's forbidden admitted fields plus the outcome/state names TP59 names.
FORBIDDEN_MEMBERSHIP_FIELDS = (
    "current_cfbd_id_match", "current_cfbd_name_match", "current_cfbd_capture_id", "current_cfbd_payload_sha256",
    "current_cfbd_request_sha256", "current_first_name", "current_last_name", "current_team", "current_weight",
    "current_height", "current_jersey", "current_class_year", "current_position", "headshot_url", "home_latitude",
    "home_longitude", "home_county_fips", "recruit_ids_json", "target", "label", "outcome", "home_points",
    "away_points", "draft", "availability", "injury", "starter", "depth")
#: Every candidate member outside the exclusion allowlist (biographical, physical, hometown, geocode, headshot,
#: recruiting, current-comparison and reconciliation-internal payload) plus the membership forbidden names.
FORBIDDEN_EXCLUSION_FIELDS = tuple(sorted(
    (set(CANDIDATE_FIELDS) - set(EXCLUSION_SOURCE_FIELDS)) | set(FORBIDDEN_MEMBERSHIP_FIELDS)))
EXCLUSION_DISPOSITIONS = (
    "CANDIDATE_VERSIONED_REPOSITORY_ROSTER_SOURCE_LEVEL_ONLY", "QUARANTINE_CANONICAL_ROSTER_MEMBERSHIP_AMBIGUOUS",
    "QUARANTINE_CURRENT_ROSTER_ATHLETE_NAME_CONFLICT", "QUARANTINE_CURRENT_ROSTER_MATCH_AMBIGUOUS",
    "QUARANTINE_INVALID_VERSIONED_ROSTER_CORE")
EXCLUSION_ADMISSION_STATE = "CANDIDATE_NOT_ADMITTED"
ELIGIBLE_DISPOSITION = "CANDIDATE_CROSS_ROUTE_IDENTITY_EXACT_ROSTER_CANONICAL_PLAYER_MEMBERSHIP"
METRIC_FIELDS = (
    "observation_id", "season", "game_id", "canonical_game_id", "player_id", "canonical_player_id",
    "canonical_membership_player_id", "canonical_team_id", "canonical_team_label", "category", "stat_type",
    "aggregation", "source_value", "source_event_rows", "source_capture_id", "source_payload_sha256",
    "source_commit_sha", "source_known_at_utc", "source_schema_sha256", "source_aggregate_evidence_sha256",
    "current_capture_id", "current_payload_sha256", "current_request_sha256", "upstream_independence",
    "reconciliation_disposition", "row_lineage_sha256", "admission_state", "official_player_box_complete",
    "partial_source_season", "protected_eligible")
METRIC_DISPOSITION = "CANDIDATE_CROSS_ROUTE_PLAYER_METRIC_EXACT_CANONICAL_GAME_PLAYER_TEAM"
METRIC_ADMISSION_STATE = "DEVELOPMENT_ONLY_HISTORICAL_KNOWN_AT_PLAYER_EVENT_METRIC"
ORIGINAL_TRANSITION_FIELDS = (
    "classification", "prior_season", "target_season", "canonical_team_id", "canonical_team_label",
    "prior_roster_count", "current_roster_count", "returning_roster_count", "departed_roster_count",
    "arrival_roster_count", "roster_retention_rate", "roster_arrival_rate", "roster_jaccard",
    "partial_prior_metric_season", "source_known_at_utc", "original_transition_time_pit_eligible",
    "target_game_feature_eligible", "protected_eligible", "defensive_interceptions_returning_share",
    "passing_yards_returning_share", "receptions_returning_share", "receiving_yards_returning_share",
    "rushing_carries_returning_share", "rushing_yards_returning_share", "feature_identity")
ORIGINAL_COMPONENT_FIELDS = (
    "classification", "prior_season", "target_season", "canonical_team_id", "category", "stat_type", "prior_total",
    "returning_total", "returning_share", "ratio_semantics", "outside_unit_interval", "prior_metric_players",
    "returning_metric_players", "partial_prior_metric_season", "source_known_at_utc", "target_game_feature_eligible",
    "protected_eligible", "component_identity")
ORIGINAL_COVERAGE_FIELDS = (
    "classification", "prior_season", "target_season", "prior_roster_teams", "current_roster_teams",
    "prior_metric_teams", "common_support_teams", "excluded_prior_current_roster_teams_without_metrics",
    "component_rows", "missing_category_stat_cells", "signed_ratios_outside_unit_interval",
    "partial_prior_metric_season", "target_game_feature_eligible", "protected_eligible")
PARENT_CONTEST_COLUMNS = ("contest_key", "season", "contest_date", "disposition", "a_key", "a_org_id", "a_team_name",
                          "a_division_label", "b_key", "b_org_id", "b_team_name", "b_division_label")

# --------------------------------------------------------------------------------------------- frozen rules

#: The six frozen category/stat pairs of the original research (BAT-415 V1.1) and their share fields.
PAIR_FIELDS = (
    (("interceptions", "INT"), "defensive_interceptions_returning_share"),
    (("passing", "YDS"), "passing_yards_returning_share"),
    (("receiving", "REC"), "receptions_returning_share"),
    (("receiving", "YDS"), "receiving_yards_returning_share"),
    (("rushing", "CAR"), "rushing_carries_returning_share"),
    (("rushing", "YDS"), "rushing_yards_returning_share"),
)
PAIRS = tuple(pair for pair, _field in PAIR_FIELDS)
SHARE_FIELDS = tuple(field for _pair, field in PAIR_FIELDS)
BOUNDED_COUNT_PAIRS = (("interceptions", "INT"), ("receiving", "REC"), ("rushing", "CAR"))
BOUNDED_SEMANTICS = "BOUNDED_NONNEGATIVE_COUNT_SHARE"
SIGNED_SEMANTICS = "SIGNED_EVENT_SUM_RATIO"
RETURNING = {
    "grain": "CANONICAL_TEAM_OFFSEASON_TRANSITION (same canonical team, prior season to target season)",
    "target_seasons": list(TARGET_SEASONS),
    "roster_sets": "distinct canonical_player_id of admitted season memberships per (season, canonical_team_id); a "
                   "player on several teams counts once on each team, never twice on one",
    "common_support": "prior-season roster, target-season roster and prior-season admitted player metrics for the "
                      "same canonical team",
    "counts": {"prior_roster_count": "|prior|", "current_roster_count": "|current|",
               "returning_roster_count": "|prior & current|", "departed_roster_count": "|prior - current|",
               "arrival_roster_count": "|current - prior|", "union_roster_count": "|prior | current|"},
    "rates": {"roster_retention_rate": "returning / prior", "roster_arrival_rate": "arrival / current",
              "roster_jaccard": "returning / union"},
    "rate_arithmetic": "IEEE-754 binary64 quotient of the two integers (Python float division), as the original",
    "numerator": "sum of prior-season source_value over metric rows of the team, category and stat whose canonical "
                 "player is in the returning set",
    "denominator": "sum of prior-season source_value over every metric row of the team, category and stat",
    "share": "numerator / denominator (binary64 quotient); a denominator <= 0 is null, never a share; a pair with no "
             "prior-season metric row is absent (no component) and its summary share is null, never zero",
    "pairs": [[category, stat, field] for (category, stat), field in PAIR_FIELDS],
    "bounded_count_pairs": [list(p) for p in BOUNDED_COUNT_PAIRS],
    "semantics": {BOUNDED_SEMANTICS: "interceptions INT, receiving REC, rushing CAR: must stay within [0,1]",
                  SIGNED_SEMANTICS: "passing YDS, receiving YDS, rushing YDS: kept unclipped; outside_unit_interval "
                                    "marks values below 0 or above 1"},
    "partial": "prior season 2020 (the partial player-metric source season) marks the 2020->2021 transition partial",
    "source_known_at": "maximum source_known_at_utc over both rosters and the prior-season metrics of the team",
    "composite": "none: passing and receiving yards overlap and no empirical weights are predeclared",
    "original_identity": "feature_identity / component_identity recomputed exactly as the original research did "
                         "(SHA-256 of sorted-key, ',' ':' separated, ASCII-escaped JSON without NaN) over the "
                         "original members; equality with the retained original is reported, never forced",
}
CHAIN = {
    "binding_source": "accepted C38 identity bindings (org_id -> cfbd_team_id)",
    "accepted_binding_rules": ["NAME_CONFIRMED_BY_SCHEDULE", "SCHEDULE_FINGERPRINT_ONLY"],
    "entity_source": "BAT-387 core registry rows record_type ENTITY, entity_type team, source_system_id SRC-002",
    "identity_key": "TEAM|SRC-002|<cfbd_team_id> (exact namespace; SRC-001 SOURCE_MAPPING keys are ESPN evidence and "
                    "never join)",
    "accepted_entity": {"mapping_method": "INTERNAL_ASSIGNMENT_LEDGER_FROM_VERIFIED_SOURCE_IDENTITY",
                        "resolution_state": "AUTO_ACCEPTED_VERIFIED"},
    "season_uniqueness": "two program-seasons of one season whose chains name the same canonical team are both "
                         "AMBIGUOUS_CANONICAL_TEAM_SHARED_IN_SEASON",
    "never": ["fuzzy or normalized names", "current-name borrowing", "equal numeric IDs across namespaces",
              "unsourced person merges"],
}
CHAIN_STATES = ("QUALIFIED_EXACT_CHAIN", "UNQUALIFIED_NO_C38_BINDING_ROW", "UNQUALIFIED_C38_BINDING_NOT_ACCEPTED",
                "UNQUALIFIED_NO_SRC002_TEAM_ENTITY", "UNQUALIFIED_SRC002_ENTITY_NOT_ACCEPTED",
                "AMBIGUOUS_MULTIPLE_SRC002_TEAM_ENTITIES", "AMBIGUOUS_CANONICAL_TEAM_SHARED_IN_SEASON")
CENSUS_RULE = {
    "seasons": list(CENSUS_SEASONS),
    "source": "both participants of every contest row of the accepted parent population 2016-2022 (every "
              "disposition, kept as witnesses) whose own source division label is FBS or FCS",
    "key": "unique (season, team_key org:<ncaa_org_id>); every name, division, contest and disposition kept",
    "division_conflict": "a key seen with both FBS and FCS is DIVISION_CONFLICT with both divisions kept",
    "never": "a delivered-row denominator, national completeness, an earlier NCAA denominator or 2023-2025 rows",
    "roster_presence": "count of admitted memberships of the chain's canonical team and season; presence is not "
                       "completeness; null when the chain is not qualified (unknown, never zero)",
    "transition_presence": "a returning summary with this target season and canonical team",
}
COVERAGE_STATES = ("ROSTER_AND_RETURNING_TRANSITION", "ROSTER_WITHOUT_RETURNING_TRANSITION",
                   "NO_ADMITTED_ROSTER_ROWS", "IDENTITY_CHAIN_UNQUALIFIED", "IDENTITY_CHAIN_AMBIGUOUS")
CENSUS_ASSOCIATIONS = ("CENSUS_PROGRAM_SEASON_QUALIFIED_CHAIN", "OUTSIDE_CENSUS_SEASONS",
                       "NO_QUALIFIED_CENSUS_PROGRAM_FOR_CANONICAL_TEAM_SEASON",
                       "AMBIGUOUS_CANONICAL_TEAM_SHARED_IN_SEASON")

# --------------------------------------------------------------------------------------------- record fields

#: Field type codes: s str, s? str or null, i int, i? int or null, b bool, f float, f? float or null, n null,
#: ls list of str, di dict of str -> int, j any JSON (census members only).
_PARENT_TYPES = {
    "observation_id": "s", "athlete_id": "s", "canonical_player_id": "s", "canonical_team_id": "s",
    "canonical_team_label": "s", "first_name": "s", "last_name": "s", "team": "s", "position": "s?",
    "class_year": "i?", "jersey": "i?", "height": "i?", "weight": "i?", "home_city": "s?", "home_state": "s?",
    "home_country": "s?", "season": "i", "source_capture_id": "s", "source_payload_sha256": "s",
    "source_commit_sha": "s", "source_known_at_utc": "s", "source_schema_sha256": "s",
    "source_record_evidence_sha256": "s", "row_lineage_sha256": "s", "membership_effective_grain": "s",
    "membership_effective_day_utc": "s?", "season_roster_membership": "b", "game_time_availability": "b",
    "depth_or_starter_status": "b", "protected_eligible": "b"}


def _labels_types(table: str) -> dict[str, str]:
    return {k: "s" for k in GRAIN_LABEL_KEYS[table]}


FIELD_TYPES: dict[str, dict[str, str]] = {
    "memberships": {"record_type": "s", "membership_key": "s", **_PARENT_TYPES, "source_row_number": "i",
                    "source_witness_key": "s", "player_season_team_count": "i", "multi_team_player_season": "b",
                    "census_key": "s?", "census_association": "s", **_labels_types("memberships")},
    "exclusions": {"record_type": "s", "exclusion_key": "s", "observation_id": "s", "source_row_number": "i",
                   "season": "i", "athlete_id": "s", "athlete_id_scope": "s", "canonical_player_id": "s?",
                   "canonical_membership_player_id": "s?", "canonical_team_id": "s?", "canonical_identity_state": "s",
                   "reconciliation_disposition": "s", "admission_state": "s", "source_capture_id": "s",
                   "source_payload_sha256": "s", "source_commit_sha": "s", "source_known_at_utc": "s",
                   "source_schema_sha256": "s", "source_record_evidence_sha256": "s", "row_lineage_sha256": "s",
                   "source_witness_key": "s", "season_athlete_exclusion_rows": "i",
                   "season_athlete_admitted_rows": "i", **_labels_types("exclusions")},
    "program_seasons": {"record_type": "s", "program_season_key": "s", "season": "i", "team_key": "s", "org_id": "s",
                        "division": "s", "divisions": "ls", "team_names": "ls", "parent_contest_keys": "ls",
                        "parent_contest_count": "i", "parent_contest_dispositions": "di", "binding_rule": "s?",
                        "binding_reason": "s?", "cfbd_team_id": "s?", "core_identity_key": "s?",
                        "core_entity_record_id": "s?", "core_entity_rows": "i?", "canonical_team_id": "s?",
                        "chain_state": "s", "admitted_membership_rows": "i?", "admitted_distinct_players": "i?",
                        "multi_team_players": "i?", "nonadmitted_rows_same_canonical_team": "i?",
                        "roster_presence": "s", "returning_target_summary_key": "s?",
                        "returning_prior_summary_key": "s?", "transition_presence": "s", "roster_supported": "b",
                        "transition_supported": "b", "coverage_state": "s", "coverage_reasons": "ls",
                        **_labels_types("program_seasons")},
    "summaries": {"record_type": "s", "summary_key": "s", "classification": "s", "prior_season": "i",
                  "target_season": "i", "canonical_team_id": "s", "canonical_team_label": "s?",
                  "prior_roster_count": "i", "current_roster_count": "i", "returning_roster_count": "i",
                  "departed_roster_count": "i", "arrival_roster_count": "i", "union_roster_count": "i",
                  "roster_retention_rate": "f", "roster_arrival_rate": "f", "roster_jaccard": "f",
                  **{field: "f?" for field in SHARE_FIELDS}, "component_keys": "ls", "missing_component_pairs": "ls",
                  "partial_prior_metric_season": "b", "source_known_at_utc": "s",
                  "original_transition_time_pit_eligible": "b", "target_game_feature_eligible": "b",
                  "protected_eligible": "b", "feature_identity": "s", "original_research_agreement": "s",
                  "target_census_key": "s?", "target_census_association": "s", "prior_census_key": "s?",
                  "prior_census_association": "s", "census_scope_state": "s", **_labels_types("summaries")},
    "components": {"record_type": "s", "component_key": "s", "summary_key": "s", "classification": "s",
                   "prior_season": "i", "target_season": "i", "canonical_team_id": "s", "category": "s",
                   "stat_type": "s", "prior_total": "i", "returning_total": "i", "returning_share": "f?",
                   "ratio_semantics": "s", "outside_unit_interval": "b", "prior_metric_players": "i",
                   "returning_metric_players": "i", "prior_metric_rows": "i", "returning_metric_rows": "i",
                   "partial_prior_metric_season": "b", "source_known_at_utc": "s",
                   "target_game_feature_eligible": "b", "protected_eligible": "b", "component_identity": "s",
                   "original_research_agreement": "s", **_labels_types("components")},
    "witnesses": {"record_type": "s", "witness_key": "s", "witness_kind": "s", "name": "s", "season": "i?",
                  "role": "s", "relative_path": "s", "sha256": "s", "bytes": "i?", "rows": "i?",
                  "dataset_identity": "s?", "capture_id": "s?", "source_repository": "s?", "source_path": "s?",
                  "source_commit_sha": "s?", "source_committer_utc": "s?", "capture_acquired_at_utc": "s?",
                  "parent_issued_at_utc": "s?", "clock_kinds": "ls", "rights_source_ids": "ls", "supports": "ls",
                  "state": "s", **_labels_types("witnesses")},
    "census": {"record_type": "s", "memberships": "i", "exclusions": "i", "program_seasons": "i", "summaries": "i",
               "components": "i", "witnesses": "i", "membership_by_season": "j", "membership_distinct_players": "i",
               "membership_distinct_teams": "i", "multi_team_player_seasons": "i",
               "maximum_teams_in_player_season": "i", "membership_missingness": "j",
               "membership_census_associations": "j", "exclusion_by_season": "j", "exclusion_dispositions": "j",
               "exclusion_canonical_ids_present": "j", "exclusion_duplicate_source_keys": "j",
               "program_seasons_by_season": "j", "program_seasons_by_division": "j", "chain_states": "j",
               "coverage_by_division": "j", "summary_census_scope": "j", "transition_coverage": "j",
               "signed_ratios_outside_unit_interval": "i", "bounded_shares_outside_unit_interval": "i",
               "missing_component_cells": "i", "original_research_agreement": "j", **_labels_types("census")},
}
RECORD_FIELDS = {table: tuple(types) for table, types in FIELD_TYPES.items()}
RECORD_TYPES = {"memberships": "ROSTER_MEMBERSHIP", "exclusions": "ROSTER_EXCLUSION",
                "program_seasons": "PROGRAM_SEASON_COVERAGE", "summaries": "RETURNING_SUMMARY",
                "components": "RETURNING_COMPONENT", "witnesses": "SOURCE_WITNESS", "census": "CENSUS"}
RECORD_TABLES = ("memberships", "exclusions", "program_seasons", "summaries", "components", "witnesses")
KEY_FIELDS = {"memberships": "membership_key", "exclusions": "exclusion_key", "program_seasons": "program_season_key",
              "summaries": "summary_key", "components": "component_key", "witnesses": "witness_key"}
SEASON_FIELDS = {"memberships": "season", "exclusions": "season", "program_seasons": "season",
                 "summaries": "target_season", "components": "target_season"}
SEGMENTS = {"memberships": ROSTER_SEASONS, "exclusions": ROSTER_SEASONS, "program_seasons": CENSUS_SEASONS,
            "summaries": TARGET_SEASONS, "components": TARGET_SEASONS}
ORDERING = {
    "memberships": "season, canonical_player_id, canonical_team_id, observation_id (the parent's order)",
    "exclusions": "season, observation_id (the quarantine's order)",
    "program_seasons": "season, numeric ncaa_org_id",
    "summaries": "target_season, canonical_team_id",
    "components": "target_season, canonical_team_id, category, stat_type",
    "witnesses": "the contract's input order, then the parent contracts in contract order",
}

# --------------------------------------------------------------------------------------------- layout and serving

LAYOUT = {
    "grains": {"memberships": "one record per admitted parent row (membership_key = observation_id)",
               "exclusions": "one record per nonadmitted quarantine row (exclusion_key = observation_id)",
               "program_seasons": "one record per expected program-season (<season>|org:<id>)",
               "summaries": "one record per retained team transition (<target_season>|<canonical_team_id>)",
               "components": "one record per supported team/pair (<target_season>|<team>|<category>|<stat_type>)",
               "witnesses": "one record per pinned input (INPUT|<name>) and parent contract (CONTRACT|<path>)",
               "census": "one record"},
    "ordering": ORDERING,
    "serialization": "canonical JSON lines (sorted keys, separators ',' ':', UTF-8, no ASCII escaping); one zlib "
                     "level-9 block per table segment (season) in the database; no separate payload files",
    "database": {"ddl": [list(d) for d in (
        ("table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"),
        ("table", "blocks", "CREATE TABLE blocks (ord INTEGER PRIMARY KEY, record_table TEXT NOT NULL, "
                            "segment TEXT NOT NULL, records INTEGER NOT NULL, first_key TEXT, last_key TEXT, "
                            "lines_sha256 TEXT NOT NULL, block BLOB NOT NULL)"))],
                 "block_layout": [*[[t, str(s)] for t in ("memberships", "exclusions") for s in ROSTER_SEASONS],
                                  *[["program_seasons", str(s)] for s in CENSUS_SEASONS],
                                  *[[t, str(s)] for t in ("summaries", "components") for s in TARGET_SEASONS],
                                  ["witnesses", "GLOBAL"], ["census", "GLOBAL"]],
                 "page_size": 4096, "journal_mode": "OFF", "file": DB_FILE},
    "identity_documents": {
        "content": ["schema", "stage", "population", "contract_id", "contract_sha256", "inputs", "parent_contracts",
                    "rules_sha256", "payload_schema", "row_counts", "lines_sha256", "blocks"],
        "database": ["schema", "stage", "population", "contract_sha256", "content_identity", "db_schema_version",
                     "outputs", "table_counts"],
        "identity": "SHA-256 of the canonical JSON bytes of the document; compared as canonical bytes, never by "
                    "Python equality (13.0, booleans and extra members differ)",
        "location": "<root>/canonical/national_personnel_evidence_2004_2022/sha256/<database identity>/"
                    "national_personnel_evidence.sqlite; manifest at <root>/manifests/"
                    "national_personnel_evidence_2004_2022/sha256/<database identity>/run_manifest.json with members "
                    "identity, identity_document, content_identity, content_document and provenance; create-only "
                    "(identical rebuild ALREADY_PRESENT_IDENTICAL, differing bytes REFUSED_IMMUTABLE_COLLISION)"},
    "checkpoint_unit": "one season (2004-2022): its memberships, exclusions, program-seasons and the summaries and "
                       "components of that target season; witnesses and the census follow",
}
GRAINS = {"roster-membership": "memberships", "roster-exclusion": "exclusions",
          "program-season-coverage": "program_seasons", "returning-component": "components",
          "returning-summary": "summaries", "source-witness": "witnesses"}
#: TP59 section 4: the complete allowed-selector matrix; any other selector on a grain is refused (FILTER_NOT_APPLICABLE).
SELECTOR_MATRIX = {
    "roster-membership": ["season", "team", "program", "player"],
    "roster-exclusion": ["season", "team", "player"],
    "program-season-coverage": ["season", "team", "program"],
    "returning-component": ["season", "team", "program"],
    "returning-summary": ["season", "team", "program"],
    "source-witness": ["season"],
}
GRAIN_SEASONS = {"roster-membership": list(ROSTER_SEASONS), "roster-exclusion": list(ROSTER_SEASONS),
                 "program-season-coverage": list(CENSUS_SEASONS), "returning-component": list(TARGET_SEASONS),
                 "returning-summary": list(TARGET_SEASONS), "source-witness": list(ROSTER_SEASONS)}
SELECTORS = {
    "season": "an integer; the grain's audited seasons (membership/exclusion 2004-2022, coverage 2016-2022, returning "
              "target 2015-2022, witness capture seasons); any other season serves no row with "
              "SEASON_OUTSIDE_RELEASE",
    "team": "an exact canonical team ID team_<32 lowercase hex>; membership: canonical_team_id; exclusion: the "
            "retained nullable canonical_team_id (never an admitted association); coverage: the qualified chain's "
            "canonical team; returning grains: canonical_team_id",
    "program": "an exact source-qualified program org:<1-12 digits> (bare digits read as org:<digits>); coverage: "
               "team_key; membership: the census association; returning grains: the target season's census "
               "association; no names",
    "player": "an exact canonical player ID player_<32 lowercase hex>; membership: canonical_player_id; exclusion: "
              "the retained nullable canonical_player_id",
    "paging": "--limit (default 50, non-negative), --offset (non-negative) or --all; exact totals in record order",
    "intersection": "selectors intersect; an unknown or disjoint valid selection serves no row (transition coverage "
                    "included); malformed or inapplicable selectors are refused before any file is read",
    "pit": "--require-pit is always refused; no historical as-of selector is offered",
    "matrix": SELECTOR_MATRIX,
    "seasons": GRAIN_SEASONS,
}
SCOPE = {
    "population": "all 154,387 retained admitted season memberships and 52,386 nonadmitted rows 2004-2022, all 982 "
                  "retained returning transitions 2015-2022 with their 5,867 components, and every accepted-parent "
                  "2016-2022 FBS/FCS program-season",
    "horizon": "retrospective research on a May 2023 source; no PIT, forecast, availability, depth, starter, injury, "
               "eligibility, transfer episode, recruiting completeness or predictive skill",
    "not_audited": "2023-2025 and current rosters, an earlier NCAA program denominator, lower divisions, and every "
                   "other personnel domain (recruiting/transfer histories, availability, player value)",
}
TABLE_LABELS = {"memberships": "MEMBERSHIP", "exclusions": "EXCLUSION", "program_seasons": "PROGRAM_SEASON",
                "summaries": "SUMMARY", "components": "COMPONENT", "witnesses": "WITNESS"}
#: TP59 section 4 error semantics: every refusal is exit 2 with one JSON line {"refused": CODE, "error": text} on
#: stderr and no row; checks run in a fixed order so each forgery is refused for its own cause.
REFUSALS = {
    "exit_code": 2,
    "stderr": "one JSON object with members refused (the code) and error (the text); nothing on stdout",
    "selection": ["ARGUMENT_INVALID", "UNKNOWN_GRAIN", "FILTER_NOT_APPLICABLE", "SEASON_INVALID", "TEAM_INVALID",
                  "PROGRAM_INVALID", "PLAYER_INVALID", "LIMIT_INVALID", "OFFSET_INVALID", "NEGATIVE_LIMIT",
                  "NEGATIVE_OFFSET", "PERSONNEL_PIT_NOT_ADMITTED", "STALE_PERSONNEL_IDENTITY"],
    "location": ["DATABASE_LOCATION_UNSUPPORTED", "DATABASE_LOCATION_NOT_LITERAL",
                 "PERSONNEL_MANIFEST_LOCATION_UNSUPPORTED", "PERSONNEL_MANIFEST_LOCATION_NOT_LITERAL",
                 "PERSONNEL_DATABASE_MISSING", "PERSONNEL_LOCATION_INVALID", "PERSONNEL_MANIFEST_MISSING",
                 "PERSONNEL_DATABASE_UNREADABLE"],
    "manifest_and_identity": ["PERSONNEL_MANIFEST_MALFORMED", "PERSONNEL_IDENTITY_MISMATCH",
                              "PERSONNEL_SCHEMA_UNSUPPORTED", "PERSONNEL_IDENTITY_DOCUMENT_MISMATCH",
                              "PERSONNEL_DATABASE_TAMPERED", "PERSONNEL_CONTRACT_MISMATCH",
                              "PERSONNEL_CONTENT_IDENTITY_MISMATCH", "PERSONNEL_PROFILE_MISMATCH"],
    "meta": ["PERSONNEL_META_MISMATCH", "PERSONNEL_META_MALFORMED", "PERSONNEL_PIT_CLAIM_INVALID",
             "PERSONNEL_LABEL_CLAIM_INVALID", "PERSONNEL_PARENT_MISMATCH", "PERSONNEL_RULES_CLAIM_INVALID",
             "PERSONNEL_COUNT_MISMATCH"],
    "blocks_and_records": ["PERSONNEL_INDEX_MISMATCH", "PERSONNEL_RECORD_TYPE_INVALID", "PERSONNEL_RECORD_MALFORMED",
                           "PERSONNEL_FORBIDDEN_FIELD_PRESENT", "PERSONNEL_RECORD_SHAPE_INVALID",
                           "PERSONNEL_FIELD_TYPE_INVALID", "PERSONNEL_RECORD_NOT_CANONICAL"],
    "collections": ["PERSONNEL_DUPLICATE_ROW", "PERSONNEL_ORDER_MISMATCH",
                    *[f"PERSONNEL_{label}_{kind}" for label in TABLE_LABELS.values()
                      for kind in ("ROW_MISSING", "ROW_EXTRA", "KEYS_MISMATCH")]],
    "rules": ["PERSONNEL_FUTURE_OR_CURRENT_ROSTER", "PERSONNEL_SEASON_OUT_OF_RANGE", "PERSONNEL_KEY_MISMATCH",
              "PERSONNEL_AVAILABILITY_CLAIM_INVALID", "PERSONNEL_DEPTH_CLAIM_INVALID",
              "PERSONNEL_EFFECTIVE_DAY_INVENTED", "PERSONNEL_MEMBERSHIP_STATE_INVALID", "PERSONNEL_SOURCE_CLOCK_MISMATCH",
              "PERSONNEL_SOURCE_LINEAGE_MISMATCH", "PERSONNEL_IDENTITY_FORMAT_INVALID", "PERSONNEL_TEAM_LABEL_MISMATCH",
              "PERSONNEL_SOURCE_LOCATOR_INVALID", "PERSONNEL_DUPLICATE_NATURAL_KEY", "PERSONNEL_MULTI_TEAM_MISMATCH",
              "PERSONNEL_QUARANTINE_PROMOTED", "PERSONNEL_DISPOSITION_INVALID",
              "PERSONNEL_DUPLICATE_DIAGNOSIS_MISMATCH", "PERSONNEL_PAIR_UNDECLARED", "PERSONNEL_RATIO_SEMANTICS_INVALID",
              "PERSONNEL_ZERO_DENOMINATOR_SHARE", "PERSONNEL_BOUNDED_SHARE_OUT_OF_RANGE", "PERSONNEL_RATIO_CLIPPED",
              "PERSONNEL_RATIO_MISMATCH", "PERSONNEL_PARTIAL_SOURCE_INVALID", "PERSONNEL_METRIC_COUNT_INVALID",
              "PERSONNEL_RECORD_MISMATCH", "PERSONNEL_RETURNING_SET_MISMATCH", "PERSONNEL_RATE_MISMATCH",
              "PERSONNEL_COMPONENT_LINK_MISMATCH", "PERSONNEL_MISSING_NULL_INVALID", "PERSONNEL_SHARE_MISMATCH",
              "PERSONNEL_ORIGINAL_IDENTITY_MISMATCH", "PERSONNEL_CENSUS_ASSOCIATION_MISMATCH",
              "PERSONNEL_CHAIN_STATE_INVALID", "PERSONNEL_NAMESPACE_INVALID", "PERSONNEL_COVERAGE_COUNT_MISMATCH",
              "PERSONNEL_TRANSITION_LINK_MISMATCH", "PERSONNEL_COVERAGE_STATE_MISMATCH",
              "PERSONNEL_UNKNOWN_COUNT_INVENTED", "PERSONNEL_DIVISION_INVALID", "PERSONNEL_PARENT_WITNESS_INVALID",
              "PERSONNEL_WITNESS_MISMATCH", "PERSONNEL_CENSUS_MISMATCH"],
    "malformed_json_reasons": ["JSON_LONE_SURROGATE", "JSON_NESTING_TOO_DEEP", "JSON_NONFINITE_NUMBER",
                               "JSON_INTEGER_TOO_LONG"],
    "build_inputs": ["PERSONNEL_DATA_ROOT_MISSING", "PERSONNEL_DATA_ROOT_LOCATION_UNSUPPORTED",
                     "PERSONNEL_DATA_ROOT_LOCATION_NOT_LITERAL", "PERSONNEL_INPUT_LOCATION_UNSUPPORTED",
                     "PERSONNEL_INPUT_LOCATION_NOT_LITERAL", "PERSONNEL_INPUT_MISSING", "PERSONNEL_INPUT_TAMPERED",
                     "PERSONNEL_INPUT_UNREADABLE", "PERSONNEL_INPUT_MALFORMED", "PERSONNEL_INPUT_POPULATION_DRIFT",
                     "PERSONNEL_DECODER_UNAVAILABLE", "PERSONNEL_PARENT_CANDIDATE_MISMATCH",
                     "PERSONNEL_PARTITION_INCOMPLETE", "PERSONNEL_CAPTURE_MISMATCH"],
}

# --------------------------------------------------------------------------------------------- refusals

class PersonnelError(ValueError):
    """A refused build input or a refused personnel release; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise PersonnelError(code, message)


#: Malformed data at the reader's untrusted JSON boundaries (block records, meta claims, the run manifest): an escaped
#: lone surrogate decodes but is not Unicode text, and nesting can exceed the JSON decoder or encoder depth. Each boundary
#: refuses it with its own code and one of these reasons, never with a traceback.
JSON_LONE_SURROGATE = "JSON_LONE_SURROGATE"
JSON_NESTING_TOO_DEEP = "JSON_NESTING_TOO_DEEP"


def _nesting_refusal(code: str, where: str) -> PersonnelError:
    return PersonnelError(code, f"{where}: {JSON_NESTING_TOO_DEEP} (deeper than the JSON decoder or encoder accepts)")


def _untrusted_canonical(value: Any, code: str, where: str) -> bytes:
    try:
        return canonical_json_bytes(value)
    except UnicodeEncodeError as exc:
        raise PersonnelError(code, f"{where}: {JSON_LONE_SURROGATE} (U+{ord(exc.object[exc.start]):04X} is not "
                                   "Unicode text)") from exc
    except RecursionError as exc:
        raise _nesting_refusal(code, where) from exc


JSON_NONFINITE_NUMBER = "JSON_NONFINITE_NUMBER"
JSON_INTEGER_TOO_LONG = "JSON_INTEGER_TOO_LONG"
#: The least integer magnitude with no finite binary64 value: the largest finite double (2**1024 - 2**971) plus half its
#: last unit rounds up to 2**1024, so ``float()`` raises OverflowError from here up. JSON decodes integers exactly, so a
#: record total the reader converts to binary64 is checked against this bound before the conversion (MF59A01-01).
BINARY64_INTEGER_BOUND = 2 ** 1024 - 2 ** 970


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
    traceback); other syntax errors are refused with ``non_json_code`` (default ``code``). Integers within the digit
    limit decode exactly; one the reader later converts to binary64 is checked against
    :data:`BINARY64_INTEGER_BOUND` where it converts."""
    try:
        return json.loads(text, parse_float=_finite_float, parse_constant=_no_constant)
    except _InvalidNumber as exc:
        raise PersonnelError(code, f"{where}: {JSON_NONFINITE_NUMBER} ({exc})") from exc
    except RecursionError as exc:
        raise _nesting_refusal(code, where) from exc
    except ValueError as exc:
        if "integer string conversion" in str(exc) or "Exceeds the limit" in str(exc):
            raise PersonnelError(code, f"{where}: {JSON_INTEGER_TOO_LONG}") from exc
        raise PersonnelError(non_json_code or code, f"{where}: not JSON ({exc})") from exc


def _json_or_none(text: Any, name: str = "") -> Any:
    """A meta claim's JSON value, or None when it is not JSON text (the claim's own rule then refuses it); malformed
    numbers and nesting beyond the decoder's depth are malformed meta (PERSONNEL_META_MALFORMED)."""
    if not isinstance(text, (str, bytes)):
        return None
    try:
        return loads_untrusted(text, "PERSONNEL_META_MALFORMED", f"meta {name}", non_json_code="NOT_JSON")
    except PersonnelError as exc:
        if exc.code == "NOT_JSON":
            return None
        raise


def rules_document() -> dict[str, Any]:
    """Every frozen rule the contract restates (the meta ``rules`` claim and the content document's rules digest)."""
    return {"labels": LABELS, "grain_labels": {k: list(v) for k, v in GRAIN_LABEL_KEYS.items()}, "layout": LAYOUT,
            "membership_parent_fields": list(MEMBERSHIP_PARENT_FIELDS), "admitted_fields": list(ADMITTED_FIELDS),
            "membership_states": MEMBERSHIP_STATES, "candidate_fields": list(CANDIDATE_FIELDS),
            "exclusion_source_fields": list(EXCLUSION_SOURCE_FIELDS),
            "forbidden_membership_fields": list(FORBIDDEN_MEMBERSHIP_FIELDS),
            "forbidden_exclusion_fields": list(FORBIDDEN_EXCLUSION_FIELDS),
            "exclusion_dispositions": list(EXCLUSION_DISPOSITIONS), "eligible_disposition": ELIGIBLE_DISPOSITION,
            "metric_fields": list(METRIC_FIELDS), "metric_disposition": METRIC_DISPOSITION,
            "original_fields": {"transitions": list(ORIGINAL_TRANSITION_FIELDS),
                                "components": list(ORIGINAL_COMPONENT_FIELDS),
                                "coverage": list(ORIGINAL_COVERAGE_FIELDS)},
            "parent_contest_columns": list(PARENT_CONTEST_COLUMNS), "returning": RETURNING, "chain": CHAIN,
            "chain_states": list(CHAIN_STATES), "census": CENSUS_RULE, "coverage_states": list(COVERAGE_STATES),
            "census_associations": list(CENSUS_ASSOCIATIONS),
            "seasons": {"roster": list(ROSTER_SEASONS), "census": list(CENSUS_SEASONS),
                        "target": list(TARGET_SEASONS), "metric": list(METRIC_SEASONS),
                        "partial_metric": list(PARTIAL_METRIC_SEASONS)},
            "source": {"repository": SOURCE_REPOSITORY, "commit": SOURCE_COMMIT, "known_at_utc": SOURCE_KNOWN_AT},
            "field_types": FIELD_TYPES, "record_types": RECORD_TYPES, "selectors": SELECTORS, "refusals": REFUSALS,
            "scope": SCOPE}


def rules_sha256() -> str:
    return sha256_bytes(canonical_json_bytes(rules_document()))


def keys_sha256(keys: Iterable[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


from aggie_analytics.personnel_evidence.anchors import ANCHORS, PERSONNEL_PROFILE  # noqa: E402

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
        raise PersonnelError(f"{code_prefix}_LOCATION_{suffix}", exc.detail) from exc


def resolve_inputs(data_root: Path, anchors: dict[str, Any]) -> dict[str, Path]:
    """Each pinned input under the explicitly named data root, refused unless present with its pinned SHA-256 and byte
    count. The root and every resolved location pass the BAT-717 literal local-file policy before any access."""
    root = Path(_literal(Path(data_root), "PERSONNEL_DATA_ROOT"))
    if not _io_path(root).is_dir():
        _refuse("PERSONNEL_DATA_ROOT_MISSING", f"no data root directory at {data_root}")
    paths: dict[str, Path] = {}
    for name, spec in anchors["inputs"].items():
        location = Path(_literal(root / Path(*spec["relative_path"].split("/")), "PERSONNEL_INPUT"))
        if not _io_path(location).is_file():
            _refuse("PERSONNEL_INPUT_MISSING", f"{name}: no file at {location}")
        actual = sha256_file(_io_path(location))
        if actual != spec["sha256"]:
            _refuse("PERSONNEL_INPUT_TAMPERED", f"{name}: bytes hash to {actual}, the contract pins {spec['sha256']}")
        paths[name] = location
    return paths


def _polars() -> Any:
    try:
        import polars  # noqa: PLC0415 - the pinned optional Parquet decoder, imported only to decode inputs
    except ImportError as exc:
        raise PersonnelError("PERSONNEL_DECODER_UNAVAILABLE", "decoding the retained Parquet inputs needs the pinned "
                                                               "polars 1.43.2 decoder") from exc
    if polars.__version__ != "1.43.2":
        _refuse("PERSONNEL_DECODER_UNAVAILABLE", f"polars {polars.__version__} is not the pinned decoder 1.43.2")
    return polars


def _parquet(path: Path, fields: tuple[str, ...], name: str, rows: int | None) -> dict[str, list[Any]]:
    """The exact physical columns of one retained Parquet file, decoded to plain Python lists (decoder only)."""
    pl = _polars()
    try:
        frame = pl.read_parquet(_io_path(path))
    except Exception as exc:  # noqa: BLE001 - any decoder failure is a malformed input, never a traceback
        raise PersonnelError("PERSONNEL_INPUT_MALFORMED", f"{name}: {type(exc).__name__}: {exc}") from exc
    if tuple(frame.columns) != fields:
        _refuse("PERSONNEL_INPUT_MALFORMED", f"{name}: physical columns differ from the contract")
    if rows is not None and frame.height != rows:
        _refuse("PERSONNEL_INPUT_POPULATION_DRIFT", f"{name}: {frame.height} rows, the contract pins {rows}")
    return {column: frame.get_column(column).to_list() for column in fields}


def _rows(columns: dict[str, list[Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    data = [columns[f] for f in fields]
    return [dict(zip(fields, values)) for values in zip(*data)]


def _json_file(path: Path, name: str) -> Any:
    try:
        return json.loads(_io_path(path).read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise PersonnelError("PERSONNEL_INPUT_MALFORMED", f"{name}: {exc}") from exc


def _connect(path: Path) -> sqlite3.Connection:
    try:
        location = readonly_sqlite.literal_path(path)
        return readonly_sqlite.connect_readonly(_io_path(Path(location)), immutable=True)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise PersonnelError("PERSONNEL_INPUT_LOCATION_" + (
            "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"), exc.detail) from exc
    except sqlite3.Error as exc:
        raise PersonnelError("PERSONNEL_INPUT_UNREADABLE", f"{path}: {exc}") from exc


def input_names(anchors: dict[str, Any], prefix: str) -> list[str]:
    return [name for name in anchors["inputs"] if name.startswith(prefix)]


def load_inputs(data_root: Path, anchors: dict[str, Any], *, input_order: str = "natural") -> dict[str, Any]:
    """Every pinned input, verified, decoded and parsed; ``input_order`` permutes every loaded collection before
    derivation (the derivation indexes by key and orders canonically, so no variant may change a byte)."""
    paths = resolve_inputs(data_root, anchors)
    specs = anchors["inputs"]
    out: dict[str, Any] = {"paths": paths}
    out["memberships"] = _rows(_parquet(paths["roster_payload"], MEMBERSHIP_PARENT_FIELDS, "roster_payload",
                                        specs["roster_payload"]["rows"]), MEMBERSHIP_PARENT_FIELDS)
    out["nonadmitted"] = _rows(_parquet(paths["nonadmitted"], CANDIDATE_FIELDS, "nonadmitted",
                                        specs["nonadmitted"]["rows"]), CANDIDATE_FIELDS)
    candidates: list[dict[str, Any]] = []
    for name in input_names(anchors, "candidate_rosters_"):
        part = _rows(_parquet(paths[name], CANDIDATE_FIELDS, name, specs[name]["rows"]), CANDIDATE_FIELDS)
        if any(row["season"] != specs[name]["season"] for row in part):
            _refuse("PERSONNEL_INPUT_MALFORMED", f"{name}: a row names another season")
        candidates += part
    out["candidates"] = candidates
    metric_fields = ("observation_id", "season", "canonical_player_id", "canonical_team_id", "canonical_team_label",
                     "category", "stat_type", "source_value", "source_known_at_utc", "source_capture_id",
                     "source_payload_sha256", "reconciliation_disposition", "admission_state",
                     "partial_source_season", "protected_eligible")
    metric_columns = _parquet(paths["metric_payload"], METRIC_FIELDS, "metric_payload", specs["metric_payload"]["rows"])
    out["metrics"] = _rows(metric_columns, metric_fields)
    out["original_transitions"] = _rows(_parquet(paths["returning_transitions"], ORIGINAL_TRANSITION_FIELDS,
                                                 "returning_transitions", specs["returning_transitions"]["rows"]),
                                        ORIGINAL_TRANSITION_FIELDS)
    out["original_components"] = _rows(_parquet(paths["returning_components"], ORIGINAL_COMPONENT_FIELDS,
                                                "returning_components", specs["returning_components"]["rows"]),
                                       ORIGINAL_COMPONENT_FIELDS)
    out["original_coverage"] = _rows(_parquet(paths["returning_coverage"], ORIGINAL_COVERAGE_FIELDS,
                                              "returning_coverage", specs["returning_coverage"]["rows"]),
                                     ORIGINAL_COVERAGE_FIELDS)
    manifests = {}
    for name, spec in specs.items():
        if spec["kind"] == "JSON":
            manifests[name] = _json_file(paths[name], name)
    out["manifests"] = manifests
    try:
        conn = _connect(paths["population"])
        try:
            meta = dict(conn.execute("SELECT key, value FROM meta"))
            contests = [dict(zip(PARENT_CONTEST_COLUMNS, r)) for r in conn.execute(
                f"SELECT {', '.join(PARENT_CONTEST_COLUMNS)} FROM contest WHERE season BETWEEN ? AND ?",
                (CENSUS_SEASONS[0], CENSUS_SEASONS[-1]))]
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise PersonnelError("PERSONNEL_INPUT_MALFORMED", f"population: {exc}") from exc
    if meta.get("contract_sha256") != specs["population"]["contract_sha256"]:
        _refuse("PERSONNEL_INPUT_MALFORMED", "the population meta names another contract")
    out["contests"] = contests
    try:
        lines = gzip.decompress(_io_path(paths["identity_bindings"]).read_bytes()).decode("utf-8").split("\n")
        header = json.loads(lines[0])
        bindings = [json.loads(line) for line in lines[1:] if line]
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise PersonnelError("PERSONNEL_INPUT_MALFORMED", f"identity_bindings: {exc}") from exc
    if not isinstance(header, dict) or (header.get("_header") or {}).get("contract_sha256") != \
            specs["identity_bindings"]["contract_sha256"]:
        _refuse("PERSONNEL_INPUT_MALFORMED", "the identity bindings header names another population contract")
    if len(bindings) != specs["identity_bindings"]["rows"]:
        _refuse("PERSONNEL_INPUT_POPULATION_DRIFT", "identity bindings row count differs from the contract")
    out["bindings"] = bindings
    try:
        text = _io_path(paths["core_registry"]).read_bytes().decode("utf-8")
        registry = list(csv.DictReader(io.StringIO(text, newline="")))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise PersonnelError("PERSONNEL_INPUT_MALFORMED", f"core_registry: {exc}") from exc
    if len(registry) != specs["core_registry"]["rows"]:
        _refuse("PERSONNEL_INPUT_POPULATION_DRIFT", "core registry row count differs from the contract")
    out["entities"] = [{k: r.get(k) for k in ("record_type", "entity_type", "record_id", "canonical_id",
                                              "identity_key", "source_system_id", "source_entity_key",
                                              "mapping_method", "resolution_state")}
                       for r in registry if r.get("entity_type") == "team"]
    for key in ("memberships", "nonadmitted", "candidates", "metrics", "original_transitions", "original_components",
                "original_coverage", "contests", "bindings", "entities"):
        out[key] = _ordered(out[key], input_order)
    return out


# --------------------------------------------------------------------------------------------- derivation helpers

def original_hash(value: Any) -> str:
    """The original research's stable hash (sorted keys, ',' ':' separators, ASCII-escaped, no NaN)."""
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                                   allow_nan=False).encode("utf-8"))


def _labels(table: str) -> dict[str, str]:
    return {k: LABELS[k] for k in GRAIN_LABEL_KEYS[table]}


def _typed_equal(a: Any, b: Any) -> bool:
    """Equality that distinguishes integers, floats and booleans (canonical JSON bytes)."""
    return canonical_json_bytes(a) == canonical_json_bytes(b)


def _same(a: Any, b: Any) -> bool:
    """Fast scalar equality that distinguishes integers, floats, booleans and null (exact type and value)."""
    return type(a) is type(b) and a == b


def _counts(values: Iterable[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        key = str(value)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def summary_key(target_season: int, team_id: str) -> str:
    return f"{target_season}|{team_id}"


def component_key(target_season: int, team_id: str, category: str, stat_type: str) -> str:
    return f"{target_season}|{team_id}|{category}|{stat_type}"


def program_key(season: int, team_key: str) -> str:
    return f"{season}|{team_key}"


def share(numerator: int, denominator: int) -> float | None:
    """The original quotient: binary64 numerator / denominator; a denominator <= 0 is null."""
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def _org_sort(team_key: str) -> tuple[int, str]:
    """The contract order of program keys: the decimal value of the ``org:<digits>`` body, then the key itself.

    The reader orders untrusted keys before their program grammar is checked, so the numeric domain is validated
    before the conversion (MF59A01-01): a body is read as a number only when ``int()`` reads it exactly -- decimal
    digits (``str.isdecimal``) no longer than the interpreter's integer string conversion limit. Any other body (a
    superscript or circled digit, which ``str.isdigit`` admits but ``int()`` refuses, a digit run beyond the limit,
    or no digit at all) sorts after every numeric body, as a non-digit body always has, so the collection order and the
    program grammar refuse it by their own codes. Every key ``int()`` could read keeps its position."""
    body = team_key.split(":", 1)[-1]
    limit = sys.get_int_max_str_digits()
    if body.isdecimal() and (limit == 0 or len(body) <= limit):
        return (int(body), team_key)
    return (10 ** 13, team_key)


# --------------------------------------------------------------------------------------------- input qualification

def qualify_rosters(inputs: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    """The membership parent, its quarantine and the candidate reconciliation: exact equality of every admitted field
    with its candidate row, a complete partition of the candidates, constant states, the source clock and per-season
    capture lineage. Returns the candidate index (observation_id -> source_row_number)."""
    captures = {c["season"]: c for c in anchors["captures"]["ROSTER"]}
    expected = anchors["expected"]
    candidates: dict[str, dict[str, Any]] = {}
    for row in inputs["candidates"]:
        if row["observation_id"] in candidates:
            _refuse("PERSONNEL_INPUT_MALFORMED", f"candidate observation {row['observation_id']} repeats")
        candidates[row["observation_id"]] = row
    seen: set[str] = set()
    for m in inputs["memberships"]:
        c = candidates.get(m["observation_id"])
        if c is None:
            _refuse("PERSONNEL_PARENT_CANDIDATE_MISMATCH", f"membership {m['observation_id']} has no candidate row")
        for field in ADMITTED_FIELDS:
            if not _same(m[field], c[field]):
                _refuse("PERSONNEL_PARENT_CANDIDATE_MISMATCH", f"membership {m['observation_id']} differs from its "
                                                               f"candidate row on {field}")
        for field, value in MEMBERSHIP_STATES.items():
            if not _same(m[field], value):
                _refuse("PERSONNEL_INPUT_MALFORMED", f"membership {m['observation_id']}: {field} is {m[field]!r}")
        if c["reconciliation_disposition"] != ELIGIBLE_DISPOSITION:
            _refuse("PERSONNEL_PARENT_CANDIDATE_MISMATCH", f"membership {m['observation_id']} is not eligible")
        seen.add(m["observation_id"])
    for n in inputs["nonadmitted"]:
        c = candidates.get(n["observation_id"])
        if c is None or not all(_same(n[f], c[f]) for f in CANDIDATE_FIELDS):
            _refuse("PERSONNEL_PARENT_CANDIDATE_MISMATCH", f"nonadmitted {n['observation_id']} differs from its "
                                                           "candidate row")
        if n["observation_id"] in seen:
            _refuse("PERSONNEL_QUARANTINE_PROMOTED", f"nonadmitted {n['observation_id']} is also admitted")
        seen.add(n["observation_id"])
    if seen != set(candidates):
        _refuse("PERSONNEL_PARTITION_INCOMPLETE", f"{len(set(candidates) - seen)} candidate rows are neither admitted "
                                                  "nor quarantined")
    for row in (*inputs["memberships"], *inputs["nonadmitted"]):
        capture = captures.get(row["season"])
        if capture is None or row["source_capture_id"] != capture["capture_id"] or \
                row["source_payload_sha256"] != capture["payload_sha256"]:
            _refuse("PERSONNEL_SOURCE_LINEAGE_MISMATCH", f"{row['observation_id']}: the capture lineage differs from "
                                                         f"the pinned season {row['season']} capture")
        if row["source_known_at_utc"] != SOURCE_KNOWN_AT or row["source_commit_sha"] != SOURCE_COMMIT:
            _refuse("PERSONNEL_SOURCE_CLOCK_MISMATCH", f"{row['observation_id']}: another source clock or commit")
    if len(inputs["memberships"]) != expected["memberships"] or len(inputs["nonadmitted"]) != expected["exclusions"]:
        _refuse("PERSONNEL_INPUT_POPULATION_DRIFT", "membership or quarantine population differs from the contract")
    return {"source_row_number": {oid: row["source_row_number"] for oid, row in candidates.items()},
            "candidate_rows": len(candidates)}


def qualify_metrics(inputs: dict[str, Any], anchors: dict[str, Any]) -> None:
    captures = {c["season"]: c for c in anchors["captures"]["METRIC"]}
    for row in inputs["metrics"]:
        capture = captures.get(row["season"])
        if capture is None or row["source_capture_id"] != capture["capture_id"] or \
                row["source_payload_sha256"] != capture["payload_sha256"]:
            _refuse("PERSONNEL_SOURCE_LINEAGE_MISMATCH", f"metric {row['observation_id']}: capture lineage differs")
        if row["source_known_at_utc"] != SOURCE_KNOWN_AT:
            _refuse("PERSONNEL_SOURCE_CLOCK_MISMATCH", f"metric {row['observation_id']}: another source clock")
        if (row["category"], row["stat_type"]) not in PAIRS:
            _refuse("PERSONNEL_INPUT_MALFORMED", f"metric {row['observation_id']}: undeclared category/stat")
        if row["reconciliation_disposition"] != METRIC_DISPOSITION or row["admission_state"] != METRIC_ADMISSION_STATE \
                or row["protected_eligible"] is not False:
            _refuse("PERSONNEL_INPUT_MALFORMED", f"metric {row['observation_id']}: not an admitted metric row")
        if row["partial_source_season"] is not (row["season"] in PARTIAL_METRIC_SEASONS):
            _refuse("PERSONNEL_PARTIAL_SOURCE_INVALID", f"metric {row['observation_id']}: partial-season flag differs")
        if not is_int(row["source_value"]):
            _refuse("PERSONNEL_INPUT_MALFORMED", f"metric {row['observation_id']}: source_value is not an integer")


def qualify_manifests(inputs: dict[str, Any], anchors: dict[str, Any]) -> None:
    """Every pinned JSON manifest's dataset identity and build clock, and every capture manifest's facts, against the
    contract (read only; the clocks are distinct: source commit, capture acquisition and parent build)."""
    manifests = inputs["manifests"]
    for name, spec in anchors["inputs"].items():
        if spec["kind"] != "JSON":
            continue
        doc = manifests[name]
        if spec.get("dataset_identity") is not None and doc.get("dataset_identity") != spec["dataset_identity"]:
            _refuse("PERSONNEL_INPUT_MALFORMED", f"{name}: dataset identity differs from the contract")
        if spec.get("issued_at_utc") is not None and doc.get("issued_at_utc") != spec["issued_at_utc"]:
            _refuse("PERSONNEL_SOURCE_CLOCK_MISMATCH", f"{name}: build clock differs from the contract")
    for kind in ("ROSTER", "METRIC"):
        for capture in anchors["captures"][kind]:
            doc = manifests[capture["manifest_input"]]
            facts = {"capture_id": doc.get("capture_id"), "season": doc.get("season"),
                     "payload_sha256": (doc.get("payload") or {}).get("sha256"),
                     "commit_sha": doc.get("commit_sha"), "committer_utc": doc.get("commit_committer_date"),
                     "acquired_at_utc": doc.get("acquired_at_utc"), "source_path": doc.get("source_path"),
                     "repository": doc.get("repository")}
            want = {k: capture[k] for k in facts}
            if facts != want:
                _refuse("PERSONNEL_CAPTURE_MISMATCH", f"{capture['manifest_input']}: capture facts differ")
            if capture["committer_utc"] != SOURCE_KNOWN_AT or capture["commit_sha"] != SOURCE_COMMIT:
                _refuse("PERSONNEL_SOURCE_CLOCK_MISMATCH", f"{capture['manifest_input']}: another source commit")


# --------------------------------------------------------------------------------------------- returning production

def returning(inputs: dict[str, Any], memberships: list[dict[str, Any]]) -> dict[str, Any]:
    """The independent returning-production reconstruction over canonical player sets (TP59 section 3)."""
    rosters: dict[tuple[int, str], set[str]] = {}
    known: dict[tuple[int, str], set[str]] = {}
    labels: dict[str, set[str]] = {}
    for m in memberships:
        key = (m["season"], m["canonical_team_id"])
        rosters.setdefault(key, set()).add(m["canonical_player_id"])
        known.setdefault(key, set()).add(m["source_known_at_utc"])
        labels.setdefault(m["canonical_team_id"], set()).add(m["canonical_team_label"])
    values: dict[tuple[int, str, tuple[str, str], str], list[int]] = {}
    metric_known: dict[tuple[int, str], set[str]] = {}
    metric_teams: dict[int, set[str]] = {}
    for row in inputs["metrics"]:
        team = row["canonical_team_id"]
        key = (row["season"], team, (row["category"], row["stat_type"]), row["canonical_player_id"])
        values.setdefault(key, []).append(row["source_value"])
        metric_known.setdefault((row["season"], team), set()).add(row["source_known_at_utc"])
        metric_teams.setdefault(row["season"], set()).add(team)
        labels.setdefault(team, set()).add(row["canonical_team_label"])
    by_team_pair: dict[tuple[int, str, tuple[str, str]], dict[str, tuple[int, int]]] = {}
    for (season, team, pair, player), vals in values.items():
        by_team_pair.setdefault((season, team, pair), {})[player] = (sum(vals), len(vals))
    summaries: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for target in TARGET_SEASONS:
        prior = target - 1
        prior_teams = {t for (s, t) in rosters if s == prior}
        current_teams = {t for (s, t) in rosters if s == target}
        source_teams = metric_teams.get(prior, set())
        common = sorted(prior_teams & current_teams & source_teams)
        component_rows = missing = signed_outside = 0
        for team in common:
            prior_players = rosters[(prior, team)]
            current_players = rosters[(target, team)]
            returning_players = prior_players & current_players
            union = prior_players | current_players
            team_labels = labels.get(team, set())
            summary: dict[str, Any] = {
                "record_type": RECORD_TYPES["summaries"], "summary_key": summary_key(target, team),
                "classification": RETURNING_CLASSIFICATION, "prior_season": prior, "target_season": target,
                "canonical_team_id": team,
                "canonical_team_label": next(iter(team_labels)) if len(team_labels) == 1 else None,
                "prior_roster_count": len(prior_players), "current_roster_count": len(current_players),
                "returning_roster_count": len(returning_players),
                "departed_roster_count": len(prior_players - current_players),
                "arrival_roster_count": len(current_players - prior_players), "union_roster_count": len(union),
                "roster_retention_rate": share(len(returning_players), len(prior_players)),
                "roster_arrival_rate": share(len(current_players - prior_players), len(current_players)),
                "roster_jaccard": share(len(returning_players), len(union)),
                "partial_prior_metric_season": prior in PARTIAL_METRIC_SEASONS,
                "source_known_at_utc": max(known[(prior, team)] | known[(target, team)] | metric_known[(prior, team)]),
                "original_transition_time_pit_eligible": False, "target_game_feature_eligible": False,
                "protected_eligible": False}
            component_keys: list[str] = []
            missing_pairs: list[str] = []
            for pair, field in sorted(PAIR_FIELDS):
                players = by_team_pair.get((prior, team, pair))
                if not players:
                    summary[field] = None
                    missing_pairs.append(f"{pair[0]}|{pair[1]}")
                    missing += 1
                    continue
                prior_total = sum(v for v, _n in players.values())
                returning_total = sum(v for p, (v, _n) in players.items() if p in returning_players)
                value = share(returning_total, prior_total)
                bounded = pair in BOUNDED_COUNT_PAIRS
                if bounded and value is not None and not 0.0 <= value <= 1.0:
                    _refuse("PERSONNEL_BOUNDED_SHARE_OUT_OF_RANGE", f"{team} {target} {pair}: {value}")
                outside = value is not None and (value < 0.0 or value > 1.0)
                signed_outside += int(outside)
                summary[field] = value
                key = component_key(target, team, *pair)
                component_keys.append(key)
                components.append({
                    "record_type": RECORD_TYPES["components"], "component_key": key,
                    "summary_key": summary["summary_key"], "classification": RETURNING_CLASSIFICATION,
                    "prior_season": prior, "target_season": target, "canonical_team_id": team,
                    "category": pair[0], "stat_type": pair[1], "prior_total": prior_total,
                    "returning_total": returning_total, "returning_share": value,
                    "ratio_semantics": BOUNDED_SEMANTICS if bounded else SIGNED_SEMANTICS,
                    "outside_unit_interval": outside, "prior_metric_players": len(players),
                    "returning_metric_players": sum(1 for p in players if p in returning_players),
                    "prior_metric_rows": sum(n for _v, n in players.values()),
                    "returning_metric_rows": sum(n for p, (_v, n) in players.items() if p in returning_players),
                    "partial_prior_metric_season": prior in PARTIAL_METRIC_SEASONS,
                    "source_known_at_utc": summary["source_known_at_utc"], "target_game_feature_eligible": False,
                    "protected_eligible": False})
                component_rows += 1
            summary["component_keys"] = component_keys
            summary["missing_component_pairs"] = missing_pairs
            summaries.append(summary)
        coverage.append({"classification": RETURNING_CLASSIFICATION, "prior_season": prior, "target_season": target,
                         "prior_roster_teams": len(prior_teams), "current_roster_teams": len(current_teams),
                         "prior_metric_teams": len(source_teams), "common_support_teams": len(common),
                         "excluded_prior_current_roster_teams_without_metrics":
                             len((prior_teams & current_teams) - source_teams),
                         "component_rows": component_rows, "missing_category_stat_cells": missing,
                         "signed_ratios_outside_unit_interval": signed_outside,
                         "partial_prior_metric_season": prior in PARTIAL_METRIC_SEASONS,
                         "target_game_feature_eligible": False, "protected_eligible": False})
    summaries.sort(key=lambda r: (r["target_season"], r["canonical_team_id"]))
    components.sort(key=lambda r: (r["target_season"], r["canonical_team_id"], r["category"], r["stat_type"]))
    return {"summaries": summaries, "components": components, "coverage": coverage, "rosters": rosters}


def original_feature(summary: dict[str, Any]) -> dict[str, Any]:
    feature = {f: summary[f] for f in ORIGINAL_TRANSITION_FIELDS if f != "feature_identity"}
    feature["feature_identity"] = original_hash(feature)
    return feature


def original_component(component: dict[str, Any]) -> dict[str, Any]:
    out = {f: component[f] for f in ORIGINAL_COMPONENT_FIELDS if f != "component_identity"}
    out["component_identity"] = original_hash(out)
    return out


def _agreement(mine: dict[str, Any], original: dict[str, Any] | None, fields: tuple[str, ...]) -> str:
    if original is None:
        return "ORIGINAL_ROW_ABSENT"
    differing = [f for f in fields if not _typed_equal(mine.get(f), original.get(f))]
    return "ALL_GOVERNED_FIELDS_EQUAL" if not differing else "DIFFERS:" + ",".join(differing)


def compare_original(inputs: dict[str, Any], built: dict[str, Any]) -> dict[str, Any]:
    """Attach the original research identity and the field-by-field agreement with the retained original (reported,
    never forced): every recomputed record keeps its own values."""
    transitions = {summary_key(r["target_season"], r["canonical_team_id"]): r for r in inputs["original_transitions"]}
    components = {component_key(r["target_season"], r["canonical_team_id"], r["category"], r["stat_type"]): r
                  for r in inputs["original_components"]}
    coverage = {r["target_season"]: r for r in inputs["original_coverage"]}
    for summary in built["summaries"]:
        feature = original_feature(summary)
        summary["feature_identity"] = feature["feature_identity"]
        summary["original_research_agreement"] = _agreement(feature, transitions.get(summary["summary_key"]),
                                                            ORIGINAL_TRANSITION_FIELDS)
    for component in built["components"]:
        mine = original_component(component)
        component["component_identity"] = mine["component_identity"]
        component["original_research_agreement"] = _agreement(mine, components.get(component["component_key"]),
                                                              ORIGINAL_COMPONENT_FIELDS)
    for row in built["coverage"]:
        row["original_research_agreement"] = _agreement(row, coverage.get(row["target_season"]),
                                                        ORIGINAL_COVERAGE_FIELDS)
    unmatched = {"summaries": sorted(set(transitions) - {s["summary_key"] for s in built["summaries"]}),
                 "components": sorted(set(components) - {c["component_key"] for c in built["components"]}),
                 "coverage": sorted(str(s) for s in set(coverage) - {r["target_season"] for r in built["coverage"]})}
    return {"summaries_equal": sum(1 for s in built["summaries"]
                                   if s["original_research_agreement"] == "ALL_GOVERNED_FIELDS_EQUAL"),
            "components_equal": sum(1 for c in built["components"]
                                    if c["original_research_agreement"] == "ALL_GOVERNED_FIELDS_EQUAL"),
            "coverage_equal": sum(1 for r in built["coverage"]
                                  if r["original_research_agreement"] == "ALL_GOVERNED_FIELDS_EQUAL"),
            "original_rows_without_recomputed_record": unmatched}


# --------------------------------------------------------------------------------------------- program-season census

def enumerate_program_seasons(contests: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Both participants of every accepted parent contest 2016-2022 whose own source division is FBS or FCS."""
    out: dict[str, dict[str, Any]] = {}
    for row in contests:
        season = row["season"]
        if not is_int(season) or season not in CENSUS_SEASONS:
            continue
        for side in ("a", "b"):
            division = row[f"{side}_division_label"]
            if division not in CENSUS_DIVISIONS:
                continue
            team_key = row[f"{side}_key"]
            org_id = row[f"{side}_org_id"]
            if not isinstance(team_key, str) or team_key != f"org:{org_id}":
                _refuse("PERSONNEL_INPUT_MALFORMED", f"contest {row['contest_key']}: side {side} key {team_key!r}")
            key = program_key(season, team_key)
            entry = out.setdefault(key, {"season": season, "team_key": team_key, "org_id": str(org_id),
                                         "divisions": set(), "names": set(), "contests": set(), "dispositions": []})
            entry["divisions"].add(division)
            if row[f"{side}_team_name"] is not None:
                entry["names"].add(row[f"{side}_team_name"])
            entry["contests"].add(row["contest_key"])
            entry["dispositions"].append((row["contest_key"], row["disposition"]))
    return out


def resolve_chains(entries: dict[str, dict[str, Any]], bindings: list[dict[str, Any]],
                   entities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The documented org -> CFBD -> canonical team chain of every program-season (exact namespaces only)."""
    by_org: dict[str, list[dict[str, Any]]] = {}
    for row in bindings:
        by_org.setdefault(str(row.get("org_id")), []).append(row)
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row in entities:
        if row["record_type"] == "ENTITY" and row["entity_type"] == "team" and row["source_system_id"] == "SRC-002":
            by_key.setdefault(row["identity_key"], []).append(row)
    accepted = CHAIN["accepted_entity"]
    chains: dict[str, dict[str, Any]] = {}
    for key, entry in entries.items():
        rows = by_org.get(entry["org_id"], [])
        chain: dict[str, Any] = {"binding_rule": None, "binding_reason": None, "cfbd_team_id": None,
                                 "core_identity_key": None, "core_entity_record_id": None, "core_entity_rows": None,
                                 "canonical_team_id": None}
        if len(rows) != 1:
            chain["chain_state"] = "UNQUALIFIED_NO_C38_BINDING_ROW"
            chain["binding_reason"] = "NO_BINDING_ROW" if not rows else "MULTIPLE_BINDING_ROWS"
            chains[key] = chain
            continue
        binding = rows[0]
        chain["binding_rule"], chain["binding_reason"] = binding.get("rule"), binding.get("reason")
        cfbd = binding.get("cfbd_team_id")
        if binding.get("rule") not in CHAIN["accepted_binding_rules"] or not isinstance(cfbd, str) or \
                not cfbd.isascii() or not cfbd.isdigit():
            chain["chain_state"] = "UNQUALIFIED_C38_BINDING_NOT_ACCEPTED"
            chains[key] = chain
            continue
        chain["cfbd_team_id"] = cfbd
        identity_key = f"TEAM|SRC-002|{cfbd}"
        chain["core_identity_key"] = identity_key
        found = by_key.get(identity_key, [])
        chain["core_entity_rows"] = len(found)
        if not found:
            chain["chain_state"] = "UNQUALIFIED_NO_SRC002_TEAM_ENTITY"
        elif len(found) > 1:
            chain["chain_state"] = "AMBIGUOUS_MULTIPLE_SRC002_TEAM_ENTITIES"
        else:
            entity = found[0]
            chain["core_entity_record_id"] = entity["record_id"]
            ok = (entity["mapping_method"] == accepted["mapping_method"] and
                  entity["resolution_state"] == accepted["resolution_state"] and
                  entity["source_entity_key"] == cfbd and entity["canonical_id"] == entity["record_id"] and
                  isinstance(entity["canonical_id"], str) and entity["canonical_id"].startswith("team_"))
            if ok:
                chain["canonical_team_id"] = entity["canonical_id"]
                chain["chain_state"] = "QUALIFIED_EXACT_CHAIN"
            else:
                chain["chain_state"] = "UNQUALIFIED_SRC002_ENTITY_NOT_ACCEPTED"
        chains[key] = chain
    shared: dict[tuple[int, str], list[str]] = {}
    for key, chain in chains.items():
        if chain["chain_state"] == "QUALIFIED_EXACT_CHAIN":
            shared.setdefault((entries[key]["season"], chain["canonical_team_id"]), []).append(key)
    for keys in shared.values():
        if len(keys) > 1:
            for key in keys:
                chains[key]["chain_state"] = "AMBIGUOUS_CANONICAL_TEAM_SHARED_IN_SEASON"
    return chains


def program_season_records(entries: dict[str, dict[str, Any]], chains: dict[str, dict[str, Any]],
                           memberships: list[dict[str, Any]], exclusions: list[dict[str, Any]],
                           summaries: list[dict[str, Any]], built: dict[str, Any],
                           metric_teams: dict[int, set[str]]) -> list[dict[str, Any]]:
    rows_by: dict[tuple[int, str], int] = {}
    players_by: dict[tuple[int, str], set[str]] = {}
    multi_by: dict[tuple[int, str], set[str]] = {}
    for m in memberships:
        key = (m["season"], m["canonical_team_id"])
        rows_by[key] = rows_by.get(key, 0) + 1
        players_by.setdefault(key, set()).add(m["canonical_player_id"])
        if m["multi_team_player_season"]:
            multi_by.setdefault(key, set()).add(m["canonical_player_id"])
    nonadmitted_by: dict[tuple[int, str], int] = {}
    for e in exclusions:
        if e["canonical_team_id"] is not None:
            key = (e["season"], e["canonical_team_id"])
            nonadmitted_by[key] = nonadmitted_by.get(key, 0) + 1
    summary_keys = {s["summary_key"] for s in summaries}
    records = []
    for key in sorted(entries, key=lambda k: (entries[k]["season"], _org_sort(entries[k]["team_key"]))):
        entry, chain = entries[key], chains[key]
        season = entry["season"]
        divisions = sorted(entry["divisions"])
        record: dict[str, Any] = {
            "record_type": RECORD_TYPES["program_seasons"], "program_season_key": key, "season": season,
            "team_key": entry["team_key"], "org_id": entry["org_id"],
            "division": divisions[0] if len(divisions) == 1 else "DIVISION_CONFLICT", "divisions": divisions,
            "team_names": sorted(entry["names"]), "parent_contest_keys": sorted(entry["contests"]),
            "parent_contest_count": len(entry["contests"]),
            "parent_contest_dispositions": _counts(d for _k, d in sorted(set(entry["dispositions"]))),
            **{k: chain[k] for k in ("binding_rule", "binding_reason", "cfbd_team_id", "core_identity_key",
                                     "core_entity_record_id", "core_entity_rows")},
            "chain_state": chain["chain_state"]}
        qualified = chain["chain_state"] == "QUALIFIED_EXACT_CHAIN"
        team = chain["canonical_team_id"] if qualified else None
        record["canonical_team_id"] = chain["canonical_team_id"]
        reasons: list[str] = []
        if qualified:
            tkey = (season, team)
            rows = rows_by.get(tkey, 0)
            record.update(admitted_membership_rows=rows, admitted_distinct_players=len(players_by.get(tkey, ())),
                          multi_team_players=len(multi_by.get(tkey, ())),
                          nonadmitted_rows_same_canonical_team=nonadmitted_by.get(tkey, 0),
                          roster_presence="ADMITTED_ROSTER_ROWS_PRESENT" if rows else "NO_ADMITTED_ROSTER_ROWS")
            target = summary_key(season, team) if summary_key(season, team) in summary_keys else None
            prior = summary_key(season + 1, team) if summary_key(season + 1, team) in summary_keys else None
            record.update(returning_target_summary_key=target, returning_prior_summary_key=prior,
                          transition_presence="RETURNING_TRANSITION_PRESENT" if target else "NO_RETURNING_TRANSITION",
                          roster_supported=rows > 0, transition_supported=target is not None)
            if rows and target:
                state = "ROSTER_AND_RETURNING_TRANSITION"
            elif rows:
                state = "ROSTER_WITHOUT_RETURNING_TRANSITION"
                if rows_by.get((season - 1, team), 0) == 0:
                    reasons.append("NO_PRIOR_SEASON_ADMITTED_ROSTER_ROWS")
                if team not in metric_teams.get(season - 1, set()):
                    reasons.append("NO_PRIOR_SEASON_ADMITTED_METRIC_ROWS")
            else:
                state = "NO_ADMITTED_ROSTER_ROWS"
                reasons.append("NO_ADMITTED_MEMBERSHIP_FOR_QUALIFIED_CANONICAL_TEAM_SEASON")
        else:
            record.update(admitted_membership_rows=None, admitted_distinct_players=None, multi_team_players=None,
                          nonadmitted_rows_same_canonical_team=None, roster_presence="UNKNOWN_CHAIN_NOT_QUALIFIED",
                          returning_target_summary_key=None, returning_prior_summary_key=None,
                          transition_presence="UNKNOWN_CHAIN_NOT_QUALIFIED", roster_supported=False,
                          transition_supported=False)
            state = "IDENTITY_CHAIN_AMBIGUOUS" if chain["chain_state"].startswith("AMBIGUOUS") else \
                "IDENTITY_CHAIN_UNQUALIFIED"
            reasons.append(chain["chain_state"])
        if len(divisions) > 1:
            reasons.append("DIVISION_CONFLICT")
        record.update(coverage_state=state, coverage_reasons=reasons, **_labels("program_seasons"))
        records.append(record)
    return records


# --------------------------------------------------------------------------------------------- witnesses and census

def witness_records(anchors: dict[str, Any]) -> list[dict[str, Any]]:
    """The complete ordered provenance of every pinned input and parent contract (a pure function of the contract)."""
    capture_of: dict[str, dict[str, Any]] = {}
    for kind in ("ROSTER", "METRIC"):
        for capture in anchors["captures"][kind]:
            capture_of[capture["manifest_input"]] = capture
            capture_of[capture["payload_input"]] = capture
    out = []
    for name, spec in anchors["inputs"].items():
        capture = capture_of.get(name)
        clocks = []
        if capture is not None:
            clocks = ["SOURCE_REPOSITORY_COMMITTER_TIME", "CAPTURE_ACQUIRED_AT"]
        elif spec.get("issued_at_utc") is not None:
            clocks = ["PARENT_BUILD_ISSUED_AT"]
        out.append({
            "record_type": RECORD_TYPES["witnesses"], "witness_key": f"INPUT|{name}", "witness_kind": "INPUT",
            "name": name, "season": spec.get("season"), "role": spec["role"], "relative_path": spec["relative_path"],
            "sha256": spec["sha256"], "bytes": spec["bytes"], "rows": spec.get("rows"),
            "dataset_identity": spec.get("dataset_identity"),
            "capture_id": capture["capture_id"] if capture else None,
            "source_repository": capture["repository"] if capture else None,
            "source_path": capture["source_path"] if capture else None,
            "source_commit_sha": capture["commit_sha"] if capture else None,
            "source_committer_utc": capture["committer_utc"] if capture else None,
            "capture_acquired_at_utc": capture["acquired_at_utc"] if capture else None,
            "parent_issued_at_utc": spec.get("issued_at_utc"), "clock_kinds": clocks,
            "rights_source_ids": list(spec["rights_source_ids"]), "supports": list(spec["supports"]),
            "state": "VERIFIED_PINNED_INPUT", **_labels("witnesses")})
    for rel, sha in anchors["parent_contracts"].items():
        out.append({
            "record_type": RECORD_TYPES["witnesses"], "witness_key": f"CONTRACT|{rel}", "witness_kind": "CONTRACT",
            "name": rel, "season": None, "role": "PARENT_CONTRACT", "relative_path": rel, "sha256": sha,
            "bytes": None, "rows": None, "dataset_identity": None, "capture_id": None, "source_repository": None,
            "source_path": None, "source_commit_sha": None, "source_committer_utc": None,
            "capture_acquired_at_utc": None, "parent_issued_at_utc": None, "clock_kinds": [],
            "rights_source_ids": [], "supports": ["source-witness"], "state": "VERIFIED_PINNED_CONTRACT",
            **_labels("witnesses")})
    return out


def census_record(derived: dict[str, Any]) -> dict[str, Any]:
    members, exclusions = derived["memberships"], derived["exclusions"]
    programs, summaries, components = derived["program_seasons"], derived["summaries"], derived["components"]
    team_counts: dict[tuple[int, str], set[str]] = {}
    for m in members:
        team_counts.setdefault((m["season"], m["canonical_player_id"]), set()).add(m["canonical_team_id"])
    by_division: dict[str, dict[str, Any]] = {}
    for p in programs:
        d = by_division.setdefault(p["division"], {"program_seasons": 0, "chain_qualified": 0, "roster_supported": 0,
                                                   "transition_supported": 0, "coverage_states": {}})
        d["program_seasons"] += 1
        d["chain_qualified"] += int(p["chain_state"] == "QUALIFIED_EXACT_CHAIN")
        d["roster_supported"] += int(p["roster_supported"])
        d["transition_supported"] += int(p["transition_supported"])
        d["coverage_states"][p["coverage_state"]] = d["coverage_states"].get(p["coverage_state"], 0) + 1
    for d in by_division.values():
        d["coverage_states"] = dict(sorted(d["coverage_states"].items()))
        d["roster_gaps"] = d["program_seasons"] - d["roster_supported"]
        d["transition_gaps"] = d["program_seasons"] - d["transition_supported"]
    duplicate_keys: dict[tuple[int, str], int] = {}
    for e in exclusions:
        duplicate_keys[(e["season"], e["athlete_id"])] = duplicate_keys.get((e["season"], e["athlete_id"]), 0) + 1
    coverage = [{k: row[k] for k in (*ORIGINAL_COVERAGE_FIELDS, "original_research_agreement")}
                for row in derived["coverage"]]
    return {
        "record_type": RECORD_TYPES["census"], "memberships": len(members), "exclusions": len(exclusions),
        "program_seasons": len(programs), "summaries": len(summaries), "components": len(components),
        "witnesses": len(derived["witnesses"]),
        "membership_by_season": _counts(m["season"] for m in members),
        "membership_distinct_players": len({m["canonical_player_id"] for m in members}),
        "membership_distinct_teams": len({m["canonical_team_id"] for m in members}),
        "multi_team_player_seasons": sum(1 for teams in team_counts.values() if len(teams) > 1),
        "maximum_teams_in_player_season": max((len(t) for t in team_counts.values()), default=0),
        "membership_missingness": {f: sum(1 for m in members if m[f] is None)
                                   for f in ("position", "class_year", "jersey", "height", "weight", "home_city",
                                             "home_state", "home_country")},
        "membership_census_associations": _counts(m["census_association"] for m in members),
        "exclusion_by_season": _counts(e["season"] for e in exclusions),
        "exclusion_dispositions": _counts(e["reconciliation_disposition"] for e in exclusions),
        "exclusion_canonical_ids_present": {
            f: sum(1 for e in exclusions if e[f] is not None)
            for f in ("canonical_player_id", "canonical_membership_player_id", "canonical_team_id")},
        "exclusion_duplicate_source_keys": {"season_athlete_keys_repeated": sum(1 for n in duplicate_keys.values()
                                                                                if n > 1),
                                            "rows_in_repeated_keys": sum(n for n in duplicate_keys.values() if n > 1),
                                            "rows_with_admitted_same_season_athlete":
                                                sum(1 for e in exclusions if e["season_athlete_admitted_rows"] > 0)},
        "program_seasons_by_season": _counts(p["season"] for p in programs),
        "program_seasons_by_division": _counts(p["division"] for p in programs),
        "chain_states": _counts(p["chain_state"] for p in programs),
        "coverage_by_division": dict(sorted(by_division.items())),
        "summary_census_scope": _counts(s["census_scope_state"] for s in summaries),
        "transition_coverage": coverage,
        "signed_ratios_outside_unit_interval": sum(1 for c in components if c["outside_unit_interval"]),
        "bounded_shares_outside_unit_interval": sum(
            1 for c in components if c["ratio_semantics"] == BOUNDED_SEMANTICS and c["returning_share"] is not None
            and not 0.0 <= c["returning_share"] <= 1.0),
        "missing_component_cells": sum(len(s["missing_component_pairs"]) for s in summaries),
        "original_research_agreement": derived["original_agreement"], **_labels("census")}


# --------------------------------------------------------------------------------------------- the derivation

def associate(season: int, team: str, census_map: dict[tuple[int, str], str],
              ambiguous: set[tuple[int, str]]) -> tuple[str | None, str]:
    if season not in CENSUS_SEASONS:
        return None, "OUTSIDE_CENSUS_SEASONS"
    if (season, team) in ambiguous:
        return None, "AMBIGUOUS_CANONICAL_TEAM_SHARED_IN_SEASON"
    key = census_map.get((season, team))
    if key is None:
        return None, "NO_QUALIFIED_CENSUS_PROGRAM_FOR_CANONICAL_TEAM_SEASON"
    return key, "CENSUS_PROGRAM_SEASON_QUALIFIED_CHAIN"


def census_scope(target: int, prior: int) -> str:
    inside = (target in CENSUS_SEASONS, prior in CENSUS_SEASONS)
    return {(True, True): "TARGET_AND_PRIOR_IN_CENSUS_SEASONS", (True, False): "PRIOR_SEASON_OUTSIDE_CENSUS_SEASONS",
            (False, False): "TARGET_AND_PRIOR_OUTSIDE_CENSUS_SEASONS"}.get(inside, "TARGET_OUTSIDE_CENSUS_SEASONS")


def derive(inputs: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    """Every record of every grain from the verified inputs (plain Python; input order never matters)."""
    qualify_manifests(inputs, anchors)
    roster = qualify_rosters(inputs, anchors)
    qualify_metrics(inputs, anchors)
    srn = roster["source_row_number"]
    parent = sorted(inputs["memberships"], key=lambda m: (m["season"], m["canonical_player_id"],
                                                          m["canonical_team_id"], m["observation_id"]))
    natural = [(m["season"], m["canonical_player_id"], m["canonical_team_id"]) for m in parent]
    if len(set(natural)) != len(natural):
        _refuse("PERSONNEL_DUPLICATE_NATURAL_KEY", "the membership parent repeats a (season, player, team) key")
    team_count: dict[tuple[int, str], set[str]] = {}
    for m in parent:
        team_count.setdefault((m["season"], m["canonical_player_id"]), set()).add(m["canonical_team_id"])
    raw_input = {c["season"]: c["payload_input"] for c in anchors["captures"]["ROSTER"]}
    memberships = []
    for m in parent:
        n = len(team_count[(m["season"], m["canonical_player_id"])])
        record = {"record_type": RECORD_TYPES["memberships"], "membership_key": m["observation_id"],
                  **{f: m[f] for f in MEMBERSHIP_PARENT_FIELDS}, "source_row_number": srn[m["observation_id"]],
                  "source_witness_key": f"INPUT|{raw_input[m['season']]}", "player_season_team_count": n,
                  "multi_team_player_season": n > 1}
        memberships.append(record)
    admitted_athletes: dict[tuple[int, str], int] = {}
    for m in parent:
        admitted_athletes[(m["season"], m["athlete_id"])] = admitted_athletes.get((m["season"], m["athlete_id"]), 0) + 1
    quarantine = sorted(inputs["nonadmitted"], key=lambda r: (r["season"], r["observation_id"]))
    occurrences: dict[tuple[int, str], int] = {}
    for row in quarantine:
        occurrences[(row["season"], row["athlete_id"])] = occurrences.get((row["season"], row["athlete_id"]), 0) + 1
    exclusions = []
    for row in quarantine:
        if row["reconciliation_disposition"] not in EXCLUSION_DISPOSITIONS or \
                row["admission_state"] != EXCLUSION_ADMISSION_STATE:
            _refuse("PERSONNEL_INPUT_MALFORMED", f"nonadmitted {row['observation_id']}: undeclared disposition/state")
        exclusions.append({
            "record_type": RECORD_TYPES["exclusions"], "exclusion_key": row["observation_id"],
            **{f: row[f] for f in EXCLUSION_SOURCE_FIELDS},
            "athlete_id_scope": "SOURCE_SCOPED_ATHLETE_ID_NOT_A_CANONICAL_PERSON",
            "canonical_identity_state": "UNRESOLVED_OR_NONADMITTED",
            "source_witness_key": f"INPUT|{raw_input[row['season']]}",
            "season_athlete_exclusion_rows": occurrences[(row["season"], row["athlete_id"])],
            "season_athlete_admitted_rows": admitted_athletes.get((row["season"], row["athlete_id"]), 0),
            **_labels("exclusions")})
    built = returning(inputs, memberships)
    agreement = compare_original(inputs, built)
    metric_teams: dict[int, set[str]] = {}
    for row in inputs["metrics"]:
        metric_teams.setdefault(row["season"], set()).add(row["canonical_team_id"])
    entries = enumerate_program_seasons(inputs["contests"])
    chains = resolve_chains(entries, inputs["bindings"], inputs["entities"])
    programs = program_season_records(entries, chains, memberships, exclusions, built["summaries"], built,
                                      metric_teams)
    census_map = {(p["season"], p["canonical_team_id"]): p["program_season_key"] for p in programs
                  if p["chain_state"] == "QUALIFIED_EXACT_CHAIN"}
    ambiguous = {(p["season"], p["canonical_team_id"]) for p in programs
                 if p["chain_state"] == "AMBIGUOUS_CANONICAL_TEAM_SHARED_IN_SEASON"}
    for record in memberships:
        record["census_key"], record["census_association"] = associate(record["season"], record["canonical_team_id"],
                                                                       census_map, ambiguous)
        record.update(_labels("memberships"))
    for summary in built["summaries"]:
        target, prior, team = summary["target_season"], summary["prior_season"], summary["canonical_team_id"]
        summary["target_census_key"], summary["target_census_association"] = associate(target, team, census_map,
                                                                                       ambiguous)
        summary["prior_census_key"], summary["prior_census_association"] = associate(prior, team, census_map,
                                                                                     ambiguous)
        summary["census_scope_state"] = census_scope(target, prior)
        summary.update(_labels("summaries"))
    for component in built["components"]:
        component.update(_labels("components"))
    derived = {"memberships": memberships, "exclusions": exclusions, "program_seasons": programs,
               "summaries": [{f: s[f] for f in RECORD_FIELDS["summaries"]} for s in built["summaries"]],
               "components": [{f: c[f] for f in RECORD_FIELDS["components"]} for c in built["components"]],
               "witnesses": witness_records(anchors), "coverage": built["coverage"], "original_agreement": agreement}
    derived["memberships"] = [{f: m[f] for f in RECORD_FIELDS["memberships"]} for m in memberships]
    derived["census"] = census_record(derived)
    expected = anchors["expected"]
    for table in RECORD_TABLES:
        if len(derived[table]) != expected[table]:
            _refuse("PERSONNEL_INPUT_POPULATION_DRIFT", f"{len(derived[table])} {table} records, the contract expects "
                                                        f"{expected[table]}")
        if keys_sha256(record_key(table, r) for r in derived[table]) != expected[f"{table}_keys_sha256"]:
            _refuse("PERSONNEL_INPUT_POPULATION_DRIFT", f"the {table} key list differs from the contract")
    return derived


# --------------------------------------------------------------------------------------------- payloads and identity

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
    return str(record[SEASON_FIELDS[table]]) if table in SEASON_FIELDS else "GLOBAL"


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


def season_chunk(derived: dict[str, Any], seasons: Iterable[int]) -> bytes:
    """The checkpoint unit: every per-season record line of the given seasons, block by block (deterministic)."""
    wanted = {str(s) for s in seasons}
    out = []
    for table, segment, _records, lines in block_lines(derived):
        if segment in wanted:
            out += [f"{table}\t{segment}\t{line}" for line in lines]
    return ("\n".join(out) + "\n").encode("utf-8")


def lines_sha256(lines: list[str]) -> str:
    return sha256_bytes("".join(line + "\n" for line in lines).encode("utf-8"))


def row_counts(derived: dict[str, Any]) -> dict[str, int]:
    return {**{table: len(derived[table]) for table in RECORD_TABLES}, "census": 1}


def inputs_claim(anchors: dict[str, Any]) -> dict[str, Any]:
    return {"inputs": anchors["inputs"], "captures": anchors["captures"], "expected": anchors["expected"]}


def content_document(anchors: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
    lines = record_lines(derived)
    return {"schema": CONTENT_SCHEMA, "stage": "personnel-evidence-content", "population": POPULATION,
            "contract_id": anchors["contract_id"], "contract_sha256": anchors["contract_sha256"],
            "inputs": inputs_claim(anchors), "parent_contracts": anchors["parent_contracts"],
            "rules_sha256": rules_sha256(), "payload_schema": PAYLOAD_SCHEMA, "row_counts": row_counts(derived),
            "lines_sha256": {table: lines_sha256(lines[table]) for table in (*RECORD_TABLES, "census")},
            "blocks": [[table, segment, len(block), lines_sha256(block)]
                       for table, segment, _records, block in block_lines(derived)]}


def database_document(contract_sha256: str, content_identity: str, database_sha256: str,
                      table_counts: dict[str, int]) -> dict[str, Any]:
    return {"schema": DATABASE_SCHEMA, "stage": "personnel-evidence-database", "population": POPULATION,
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
_SCALAR_TYPES = {"s": (str,), "s?": (str, _NONE), "i": (int,), "i?": (int, _NONE), "b": (bool,), "f": (float,),
                 "f?": (float, _NONE), "n": (_NONE,)}
_TYPE_CHECKS = {
    **{code: (lambda allowed: (lambda v: type(v) in allowed))(allowed) for code, allowed in _SCALAR_TYPES.items()},
    "ls": lambda v: type(v) is list and all(type(x) is str for x in v),
    "di": lambda v: type(v) is dict and all(type(k) is str and type(x) is int for k, x in v.items()),
    "j": lambda v: True,
}
TEAM_ID_RE = re.compile(r"team_[0-9a-f]{32}\Z")
PLAYER_ID_RE = re.compile(r"player_[0-9a-f]{32}\Z")
PROGRAM_RE = re.compile(r"org:[0-9]{1,12}\Z")
MANIFEST_MEMBERS = ("content_document", "content_identity", "identity", "identity_document", "provenance")


class PersonnelEvidence:
    """A verified, read-only handle on one content-addressed national personnel evidence release.

    Construction refuses (PersonnelError with a stable code) unless the release location, run manifest, database
    bytes, schema, meta claims, every record's exact members and JSON types, the complete expected collection of every
    grain, every rule re-derivable from the records, the content document, the contract-defined database identity
    document and (when the anchors pin one) the canonical profile verify. Each refusal is checked in a fixed order so
    that every forgery is refused for its own cause."""

    def __init__(self, database: Path, *, manifest: Path | None = None, expect_identity: str | None = None,
                 anchors: dict[str, Any] | None = None) -> None:
        self.anchors = anchors if anchors is not None else {**ANCHORS, "profile": PERSONNEL_PROFILE}
        self.binding = self._verify_location_and_manifest(database, manifest, expect_identity)
        document = self.binding["identity_document"]
        if document.get("contract_sha256") != self.anchors["contract_sha256"]:
            _refuse("PERSONNEL_CONTRACT_MISMATCH", f"the release names contract {document.get('contract_sha256')}, "
                                                   f"the reader binds {self.anchors['contract_sha256']}")
        try:
            location = readonly_sqlite.literal_path(database)
            self.conn = readonly_sqlite.connect_readonly(_io_path(Path(location)), immutable=False)
        except readonly_sqlite.DatabaseLocationError as exc:
            raise PersonnelError(exc.code, exc.detail) from exc
        except sqlite3.Error as exc:
            raise PersonnelError("PERSONNEL_DATABASE_UNREADABLE", str(exc)) from exc
        try:
            self._verify_database()
        except sqlite3.DatabaseError as exc:
            self.conn.close()
            raise PersonnelError("PERSONNEL_SCHEMA_UNSUPPORTED", str(exc)) from exc
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
            raise PersonnelError(exc.code, exc.detail) from exc
        manifest_path = None
        if manifest is not None:
            try:
                manifest_path = Path(readonly_sqlite.literal_path(manifest))
            except readonly_sqlite.DatabaseLocationError as exc:
                suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
                raise PersonnelError(f"PERSONNEL_MANIFEST_LOCATION_{suffix}", f"--manifest {manifest}: "
                                                                             f"{exc.detail}") from exc
        db = Path(database)
        if not _io_path(db).is_file():
            _refuse("PERSONNEL_DATABASE_MISSING", f"no personnel evidence database file at {db}")
        absolute = Path(os.path.abspath(db))
        if absolute.name != DB_FILE or absolute.parent.parent.name != "sha256" or \
                absolute.parent.parent.parent.name != POPULATION:
            _refuse("PERSONNEL_LOCATION_INVALID", f"the release must sit at <root>/{POPULATION}/sha256/<id>/{DB_FILE}")
        identity = absolute.parent.name
        if not IDENTITY_RE.match(identity):
            _refuse("PERSONNEL_LOCATION_INVALID", f"directory name {identity!r} is not an identity")
        if manifest_path is None:
            manifest_path = manifest_path_for(db)
        if not _io_path(manifest_path).is_file():
            _refuse("PERSONNEL_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
        try:
            raw = _io_path(manifest_path).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise PersonnelError("PERSONNEL_MANIFEST_MALFORMED", str(exc)) from exc
        doc = loads_untrusted(raw, "PERSONNEL_MANIFEST_MALFORMED", "run manifest")
        if not isinstance(doc, dict):
            _refuse("PERSONNEL_MANIFEST_MALFORMED", "the run manifest is not a JSON object")
        if sorted(doc) != sorted(MANIFEST_MEMBERS):
            _refuse("PERSONNEL_MANIFEST_MALFORMED", f"run manifest members {sorted(doc)} differ from "
                                                    f"{list(MANIFEST_MEMBERS)}")
        identity_document = doc["identity_document"]
        computed = sha256_bytes(_untrusted_canonical(identity_document, "PERSONNEL_MANIFEST_MALFORMED",
                                                     "run manifest identity document"))
        _untrusted_canonical(doc["content_document"], "PERSONNEL_MANIFEST_MALFORMED", "run manifest content document")
        if computed != identity or doc.get("identity") != identity:
            _refuse("PERSONNEL_IDENTITY_MISMATCH", f"manifest identity document hashes to {computed}, directory is "
                                                   f"{identity}, the manifest names {doc.get('identity')!r}")
        if not isinstance(identity_document, dict) or \
                (identity_document.get("stage"), identity_document.get("schema"),
                 identity_document.get("db_schema_version"), identity_document.get("population")) != \
                ("personnel-evidence-database", DATABASE_SCHEMA, DB_SCHEMA, POPULATION):
            _refuse("PERSONNEL_SCHEMA_UNSUPPORTED", "not a national personnel evidence database manifest")
        outputs = identity_document.get("outputs")
        if not isinstance(outputs, dict):
            _refuse("PERSONNEL_IDENTITY_DOCUMENT_MISMATCH", "the manifest identity document's outputs is not an object")
        actual_sha = sha256_file(_io_path(db))
        if outputs.get(DB_FILE) != actual_sha:
            _refuse("PERSONNEL_DATABASE_TAMPERED", f"release bytes hash to {actual_sha}, manifest names "
                                                   f"{outputs.get(DB_FILE)}")
        if expect_identity is not None and expect_identity != identity:
            _refuse("STALE_PERSONNEL_IDENTITY", f"expected {expect_identity}, found {identity}")
        return {"identity": identity, "sha256": actual_sha, "manifest": str(manifest_path),
                "identity_document": identity_document, "content_document": doc["content_document"],
                "content_identity_claim": doc.get("content_identity"), "provenance": doc.get("provenance")}

    # ---- schema, meta claims, records, rules and identities
    def _verify_database(self) -> None:
        a = self.anchors
        master = sorted((str(r[0]), str(r[1]), r[2]) for r in self.conn.execute(
            "SELECT type, name, sql FROM sqlite_master"))
        if master != sorted(DDL):
            _refuse("PERSONNEL_SCHEMA_UNSUPPORTED", "the release schema differs from the contract")
        meta_rows = [(str(r[0]), r[1]) for r in self.conn.execute("SELECT key, value FROM meta ORDER BY rowid")]
        meta = dict(meta_rows)
        if len(meta) != len(meta_rows):
            _refuse("PERSONNEL_META_MISMATCH", "duplicate meta keys")
        if meta.get("schema_version") != DB_SCHEMA:
            _refuse("PERSONNEL_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}")
        if meta.get("contract_sha256") != a["contract_sha256"] or meta.get("contract_id") != a["contract_id"]:
            _refuse("PERSONNEL_CONTRACT_MISMATCH", "the release meta names another contract")
        claims = {name: _json_or_none(meta.get(name), name) for name in ("inputs", "parent_contracts", "labels",
                                                                         "rules")}
        if claims["labels"] != LABELS:
            labels = claims["labels"] if isinstance(claims["labels"], dict) else {}
            code = "PERSONNEL_PIT_CLAIM_INVALID" if labels.get("pit_eligibility") != LABELS["pit_eligibility"] else \
                "PERSONNEL_LABEL_CLAIM_INVALID"
            _refuse(code, "the release declares labels other than the contract's")
        if _untrusted_canonical(claims["inputs"], "PERSONNEL_META_MALFORMED", "meta inputs") != \
                canonical_json_bytes(inputs_claim(a)):
            _refuse("PERSONNEL_PARENT_MISMATCH", "the release was built from other inputs or expectations")
        if _untrusted_canonical(claims["parent_contracts"], "PERSONNEL_META_MALFORMED", "meta parent_contracts") != \
                canonical_json_bytes(a["parent_contracts"]):
            _refuse("PERSONNEL_PARENT_MISMATCH", "the release names other parent contracts")
        if _untrusted_canonical(claims["rules"], "PERSONNEL_META_MALFORMED", "meta rules") != \
                canonical_json_bytes(rules_document()):
            _refuse("PERSONNEL_RULES_CLAIM_INVALID", "the release declares other rules")
        counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        if counts != self.binding["identity_document"].get("table_counts"):
            _refuse("PERSONNEL_COUNT_MISMATCH",
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
        if _untrusted_canonical(self.binding["content_document"], "PERSONNEL_MANIFEST_MALFORMED",
                                "content document") != canonical_json_bytes(document) or \
                self.binding["content_identity_claim"] != content_identity or \
                meta.get("content_identity") != content_identity or \
                self.binding["identity_document"].get("content_identity") != content_identity:
            _refuse("PERSONNEL_CONTENT_IDENTITY_MISMATCH", f"the rebuilt content identity is {content_identity}")
        expected_meta = meta_values(a, content_identity, derived)
        if meta != expected_meta:
            _refuse("PERSONNEL_META_MISMATCH", "meta differs on " + str(sorted(
                k for k in set(meta) | set(expected_meta) if meta.get(k) != expected_meta.get(k))))
        identity_document = self.binding["identity_document"]
        expected_document = database_document(a["contract_sha256"], content_identity, self.binding["sha256"], counts)
        expected_bytes = canonical_json_bytes(expected_document)
        if canonical_json_bytes(identity_document) != expected_bytes:
            differing = sorted(k for k in set(identity_document) | set(expected_document)
                               if k not in identity_document or k not in expected_document
                               or canonical_json_bytes(identity_document[k]) !=
                               canonical_json_bytes(expected_document[k]))
            _refuse("PERSONNEL_IDENTITY_DOCUMENT_MISMATCH", f"the manifest identity document is not the "
                                                            f"contract-defined database document (differs on "
                                                            f"{differing})")
        database_identity = sha256_bytes(expected_bytes)
        if database_identity != self.binding["identity"]:
            _refuse("PERSONNEL_IDENTITY_DOCUMENT_MISMATCH", f"the location names {self.binding['identity']}, the "
                                                            f"contract-defined document is {database_identity}")
        profile = a.get("profile")
        if profile is not None and (profile.get("content_identity"), profile.get("database_identity")) != \
                (content_identity, database_identity):
            _refuse("PERSONNEL_PROFILE_MISMATCH", f"the release ({database_identity} / {content_identity}) is not the "
                                                  f"pinned canonical profile ({profile.get('database_identity')} / "
                                                  f"{profile.get('content_identity')})")
        self.database_identity = database_identity
        self.content_identity = content_identity
        self.meta = meta
        self.records = derived
        self.census = derived["census"]
        self._index()

    def _read_blocks(self) -> dict[str, list[tuple[str, dict[str, Any]]]]:
        rows = [tuple(r) for r in self.conn.execute(
            "SELECT ord, record_table, segment, records, first_key, last_key, lines_sha256, block FROM blocks "
            "ORDER BY ord")]
        present: dict[str, list[tuple[str, dict[str, Any]]]] = {t: [] for t in (*RECORD_TABLES, "census")}
        self.segments: dict[str, list[str]] = {}
        layout = []
        for ord_, table, segment, records, first_key, last_key, lines_sha, blob in rows:
            if table not in present:
                _refuse("PERSONNEL_SCHEMA_UNSUPPORTED", f"block {ord_} names table {table!r}")
            try:
                data = zlib.decompress(blob)
                lines = data.decode("utf-8").split("\n")
            except (zlib.error, TypeError, UnicodeDecodeError) as exc:
                raise PersonnelError("PERSONNEL_INDEX_MISMATCH", f"block {ord_} does not decompress: {exc}") from exc
            if lines[-1] != "":
                _refuse("PERSONNEL_INDEX_MISMATCH", f"block {ord_} does not end with a newline")
            parsed = []
            for line in lines[:-1]:
                record = loads_untrusted(line, "PERSONNEL_RECORD_MALFORMED", f"block {ord_} ({table})",
                                         non_json_code="PERSONNEL_RECORD_TYPE_INVALID")
                if not isinstance(record, dict):
                    _refuse("PERSONNEL_RECORD_TYPE_INVALID", f"block {ord_} holds a non-object line")
                if table != "census":
                    key = record.get(KEY_FIELDS[table])
                    if not isinstance(key, str):
                        _refuse("PERSONNEL_RECORD_TYPE_INVALID", f"{table} record: {KEY_FIELDS[table]} is not a string")
                parsed.append((line, record))
            keys = [record_key(table, r) for _l, r in parsed]
            if sha256_bytes(data) != lines_sha or records != len(parsed) or \
                    first_key != (keys[0] if keys else None) or last_key != (keys[-1] if keys else None):
                _refuse("PERSONNEL_INDEX_MISMATCH", f"block {ord_} index columns differ from its content")
            self.segments.setdefault(table, []).extend(segment for _p in parsed)
            layout.append((table, segment))
            present[table] += parsed
        if layout != list(BLOCK_LAYOUT):
            _refuse("PERSONNEL_INDEX_MISMATCH", "the blocks do not follow the contract layout")
        for table in (*RECORD_TABLES, "census"):
            forbidden = set(FORBIDDEN_MEMBERSHIP_FIELDS if table == "memberships" else
                            FORBIDDEN_EXCLUSION_FIELDS if table == "exclusions" else ())
            types = FIELD_TYPES[table]
            scalar = [(f, _SCALAR_TYPES[c]) for f, c in types.items() if c in _SCALAR_TYPES]
            compound = [(f, c) for f, c in types.items() if c not in _SCALAR_TYPES]
            for line, record in present[table]:
                where = f"{table} record {record_key(table, record)}"
                leaked = sorted(forbidden & set(record))
                if leaked:
                    _refuse("PERSONNEL_FORBIDDEN_FIELD_PRESENT", f"{where} carries forbidden members {leaked[:4]}")
                if set(record) != set(types):
                    extra, missing = sorted(set(record) - set(types)), sorted(set(types) - set(record))
                    _refuse("PERSONNEL_RECORD_SHAPE_INVALID", f"{where}: extra members {extra[:4]}, missing "
                                                              f"{missing[:4]}")
                for field, code in scalar:
                    if type(record[field]) not in code:
                        _refuse("PERSONNEL_FIELD_TYPE_INVALID", f"{where}: {field} is a JSON "
                                                                f"{type(record[field]).__name__}, the contract "
                                                                f"declares {types[field]}")
                for field, code in compound:
                    if not _TYPE_CHECKS[code](record[field]):
                        _refuse("PERSONNEL_FIELD_TYPE_INVALID", f"{where}: {field} is a JSON "
                                                                f"{type(record[field]).__name__}, the contract "
                                                                f"declares {code}")
                if line != _untrusted_canonical(record, "PERSONNEL_RECORD_MALFORMED", where).decode("utf-8"):
                    _refuse("PERSONNEL_RECORD_NOT_CANONICAL", f"{where} is not its canonical JSON line")
        return present

    def _verify_collections(self, records: dict[str, list[dict[str, Any]]]) -> None:
        """Complete membership and multiplicity of every grain against the contract's expected collection, then the
        contract order, then the exact key sequence."""
        expected = self.anchors["expected"]
        for table in RECORD_TABLES:
            label = TABLE_LABELS[table]
            keys = [record_key(table, r) for r in records[table]]
            if len(keys) != len(set(keys)):
                _refuse("PERSONNEL_DUPLICATE_ROW", f"{table} repeats a record key")
            listed = expected.get(f"{table}_keys")
            if listed is not None:
                missing = sorted(set(listed) - set(keys))
                if missing:
                    _refuse(f"PERSONNEL_{label}_ROW_MISSING", f"{len(missing)} expected {table} keys absent, e.g. "
                                                              f"{missing[:3]}")
                extra = sorted(set(keys) - set(listed))
                if extra:
                    _refuse(f"PERSONNEL_{label}_ROW_EXTRA", f"{len(extra)} {table} keys outside the expected "
                                                            f"collection, e.g. {extra[:3]}")
            if len(keys) < expected[table]:
                _refuse(f"PERSONNEL_{label}_ROW_MISSING", f"{expected[table] - len(keys)} expected {table} records "
                                                          "absent")
            if len(keys) > expected[table]:
                _refuse(f"PERSONNEL_{label}_ROW_EXTRA", f"{len(keys) - expected[table]} {table} records outside the "
                                                        "expected collection")
            order = [_order_key(table, r) for r in records[table]]
            if order != sorted(order):
                _refuse("PERSONNEL_ORDER_MISMATCH", f"{table} is not in the contract order")
            if keys_sha256(keys) != expected[f"{table}_keys_sha256"]:
                _refuse(f"PERSONNEL_{label}_KEYS_MISMATCH", f"the {table} key sequence differs from the contract's "
                                                            "expected collection")

    def _verify_rules(self, records: dict[str, list[dict[str, Any]]]) -> None:
        """Every rule the records themselves can re-derive, in a fixed order."""
        a = self.anchors
        expected = a["expected"]
        for table in (*RECORD_TABLES, "census"):
            want = RECORD_TYPES[table]
            for record in records[table]:
                if record["record_type"] != want:
                    _refuse("PERSONNEL_RECORD_TYPE_INVALID", f"{table} record {record_key(table, record)} is a "
                                                             f"{record['record_type']!r}")
                for k in GRAIN_LABEL_KEYS[table]:
                    if record[k] != LABELS[k]:
                        _refuse("PERSONNEL_PIT_CLAIM_INVALID" if k == "pit_eligibility" else
                                "PERSONNEL_LABEL_CLAIM_INVALID", f"{table} record {record_key(table, record)}: {k} "
                                                                f"is {record[k]!r}")
        roster_captures = {c["season"]: c for c in a["captures"]["ROSTER"]}
        members = records["memberships"]
        natural: set[tuple[int, str, str]] = set()
        teams_of: dict[tuple[int, str], set[str]] = {}
        observation_ids: set[str] = set()
        for m in members:
            where = f"membership {m['membership_key']}"
            if m["season"] not in ROSTER_SEASONS:
                _refuse("PERSONNEL_FUTURE_OR_CURRENT_ROSTER" if m["season"] > ROSTER_SEASONS[-1] else
                        "PERSONNEL_SEASON_OUT_OF_RANGE", f"{where}: season {m['season']} is outside 2004-2022")
            if m["membership_key"] != m["observation_id"]:
                _refuse("PERSONNEL_KEY_MISMATCH", f"{where}: key differs from observation_id")
            for field, value in MEMBERSHIP_STATES.items():
                if not _same(m[field], value):
                    code = {"game_time_availability": "PERSONNEL_AVAILABILITY_CLAIM_INVALID",
                            "depth_or_starter_status": "PERSONNEL_DEPTH_CLAIM_INVALID",
                            "membership_effective_day_utc": "PERSONNEL_EFFECTIVE_DAY_INVENTED",
                            "protected_eligible": "PERSONNEL_PIT_CLAIM_INVALID"}.get(field,
                                                                                    "PERSONNEL_MEMBERSHIP_STATE_INVALID")
                    _refuse(code, f"{where}: {field} is {m[field]!r}")
            if m["source_known_at_utc"] != SOURCE_KNOWN_AT or m["source_commit_sha"] != SOURCE_COMMIT:
                _refuse("PERSONNEL_SOURCE_CLOCK_MISMATCH", f"{where}: another source clock")
            capture = roster_captures.get(m["season"])
            if capture is None or (m["source_capture_id"], m["source_payload_sha256"]) != \
                    (capture["capture_id"], capture["payload_sha256"]) or \
                    m["source_witness_key"] != f"INPUT|{capture['payload_input']}":
                _refuse("PERSONNEL_SOURCE_LINEAGE_MISMATCH", f"{where}: the capture lineage differs from season "
                                                             f"{m['season']}")
            if not TEAM_ID_RE.match(m["canonical_team_id"]) or not PLAYER_ID_RE.match(m["canonical_player_id"]):
                _refuse("PERSONNEL_IDENTITY_FORMAT_INVALID", f"{where}: canonical identifiers are malformed")
            if m["team"] != m["canonical_team_label"]:
                _refuse("PERSONNEL_TEAM_LABEL_MISMATCH", f"{where}: historical team label differs from the canonical "
                                                         "label")
            if m["source_row_number"] < 0:
                _refuse("PERSONNEL_SOURCE_LOCATOR_INVALID", f"{where}: negative source row number")
            key = (m["season"], m["canonical_player_id"], m["canonical_team_id"])
            if key in natural:
                _refuse("PERSONNEL_DUPLICATE_NATURAL_KEY", f"{where}: (season, player, team) repeats")
            natural.add(key)
            observation_ids.add(m["observation_id"])
            teams_of.setdefault((m["season"], m["canonical_player_id"]), set()).add(m["canonical_team_id"])
        for m in members:
            n = len(teams_of[(m["season"], m["canonical_player_id"])])
            if m["player_season_team_count"] != n or m["multi_team_player_season"] is not (n > 1):
                _refuse("PERSONNEL_MULTI_TEAM_MISMATCH", f"membership {m['membership_key']}: same-season team count "
                                                         f"is {n}")
        admitted_athletes: dict[tuple[int, str], int] = {}
        for m in members:
            admitted_athletes[(m["season"], m["athlete_id"])] = admitted_athletes.get((m["season"], m["athlete_id"]),
                                                                                      0) + 1
        exclusions = records["exclusions"]
        occurrences: dict[tuple[int, str], int] = {}
        for e in exclusions:
            occurrences[(e["season"], e["athlete_id"])] = occurrences.get((e["season"], e["athlete_id"]), 0) + 1
        for e in exclusions:
            where = f"exclusion {e['exclusion_key']}"
            if e["exclusion_key"] != e["observation_id"]:
                _refuse("PERSONNEL_KEY_MISMATCH", f"{where}: key differs from observation_id")
            if e["observation_id"] in observation_ids or e["admission_state"] != EXCLUSION_ADMISSION_STATE or \
                    e["canonical_identity_state"] != "UNRESOLVED_OR_NONADMITTED":
                _refuse("PERSONNEL_QUARANTINE_PROMOTED", f"{where}: a nonadmitted row claims admission")
            if e["reconciliation_disposition"] not in EXCLUSION_DISPOSITIONS:
                _refuse("PERSONNEL_DISPOSITION_INVALID", f"{where}: undeclared disposition")
            if e["season"] not in ROSTER_SEASONS:
                _refuse("PERSONNEL_FUTURE_OR_CURRENT_ROSTER" if e["season"] > ROSTER_SEASONS[-1] else
                        "PERSONNEL_SEASON_OUT_OF_RANGE", f"{where}: season {e['season']}")
            if e["athlete_id_scope"] != "SOURCE_SCOPED_ATHLETE_ID_NOT_A_CANONICAL_PERSON":
                _refuse("PERSONNEL_QUARANTINE_PROMOTED", f"{where}: the source athlete ID claims a canonical scope")
            if e["source_known_at_utc"] != SOURCE_KNOWN_AT or e["source_commit_sha"] != SOURCE_COMMIT:
                _refuse("PERSONNEL_SOURCE_CLOCK_MISMATCH", f"{where}: another source clock")
            capture = roster_captures.get(e["season"])
            if capture is None or (e["source_capture_id"], e["source_payload_sha256"]) != \
                    (capture["capture_id"], capture["payload_sha256"]) or \
                    e["source_witness_key"] != f"INPUT|{capture['payload_input']}":
                _refuse("PERSONNEL_SOURCE_LINEAGE_MISMATCH", f"{where}: the capture lineage differs")
            if e["season_athlete_exclusion_rows"] != occurrences[(e["season"], e["athlete_id"])] or \
                    e["season_athlete_admitted_rows"] != admitted_athletes.get((e["season"], e["athlete_id"]), 0):
                _refuse("PERSONNEL_DUPLICATE_DIAGNOSIS_MISMATCH", f"{where}: the duplicate source-key counts differ")
        rosters: dict[tuple[int, str], set[str]] = {}
        rows_by: dict[tuple[int, str], int] = {}
        multi_by: dict[tuple[int, str], set[str]] = {}
        for m in members:
            key = (m["season"], m["canonical_team_id"])
            rosters.setdefault(key, set()).add(m["canonical_player_id"])
            rows_by[key] = rows_by.get(key, 0) + 1
            if m["multi_team_player_season"]:
                multi_by.setdefault(key, set()).add(m["canonical_player_id"])
        nonadmitted_by: dict[tuple[int, str], int] = {}
        for e in exclusions:
            if e["canonical_team_id"] is not None:
                key = (e["season"], e["canonical_team_id"])
                nonadmitted_by[key] = nonadmitted_by.get(key, 0) + 1
        components = records["components"]
        by_summary: dict[str, list[dict[str, Any]]] = {}
        signed_outside = 0
        for c in components:
            where = f"component {c['component_key']}"
            pair = (c["category"], c["stat_type"])
            if pair not in PAIRS:
                _refuse("PERSONNEL_PAIR_UNDECLARED", f"{where}: {pair} is not one of the six frozen pairs")
            if c["component_key"] != component_key(c["target_season"], c["canonical_team_id"], *pair) or \
                    c["summary_key"] != summary_key(c["target_season"], c["canonical_team_id"]) or \
                    c["prior_season"] != c["target_season"] - 1:
                _refuse("PERSONNEL_KEY_MISMATCH", f"{where}: key members differ")
            semantics = BOUNDED_SEMANTICS if pair in BOUNDED_COUNT_PAIRS else SIGNED_SEMANTICS
            if c["ratio_semantics"] != semantics:
                _refuse("PERSONNEL_RATIO_SEMANTICS_INVALID", f"{where}: {c['ratio_semantics']!r}")
            if c["prior_total"] > 0:  # the share converts both totals to binary64 (a non-positive one never converts)
                for field in ("returning_total", "prior_total"):
                    if not -BINARY64_INTEGER_BOUND < c[field] < BINARY64_INTEGER_BOUND:
                        _refuse("PERSONNEL_RECORD_MALFORMED", f"{where}: {field} {JSON_NONFINITE_NUMBER} (a "
                                                              f"{c[field].bit_length()}-bit integer has no finite "
                                                              "binary64 value)")
            value = share(c["returning_total"], c["prior_total"])
            if c["prior_total"] <= 0 and c["returning_share"] is not None:
                _refuse("PERSONNEL_ZERO_DENOMINATOR_SHARE", f"{where}: a share over a recorded non-positive "
                                                            "denominator")
            if semantics == BOUNDED_SEMANTICS and c["returning_share"] is not None and \
                    not 0.0 <= c["returning_share"] <= 1.0:
                _refuse("PERSONNEL_BOUNDED_SHARE_OUT_OF_RANGE", f"{where}: count share {c['returning_share']}")
            if not _typed_equal(c["returning_share"], value):
                code = "PERSONNEL_RATIO_CLIPPED" if value is not None and (value < 0.0 or value > 1.0) and \
                    c["returning_share"] is not None and 0.0 <= c["returning_share"] <= 1.0 else \
                    "PERSONNEL_RATIO_MISMATCH"
                _refuse(code, f"{where}: share {c['returning_share']} != {c['returning_total']}/{c['prior_total']}")
            outside = value is not None and (value < 0.0 or value > 1.0)
            if c["outside_unit_interval"] is not outside:
                _refuse("PERSONNEL_RATIO_MISMATCH", f"{where}: unit-interval flag differs")
            signed_outside += int(outside)
            if c["partial_prior_metric_season"] is not (c["prior_season"] in PARTIAL_METRIC_SEASONS):
                _refuse("PERSONNEL_PARTIAL_SOURCE_INVALID", f"{where}: partial-season flag differs")
            if not 0 <= c["returning_metric_players"] <= c["prior_metric_players"] or \
                    not 0 <= c["returning_metric_rows"] <= c["prior_metric_rows"] or \
                    c["prior_metric_players"] > c["prior_metric_rows"] or c["prior_metric_players"] < 1:
                _refuse("PERSONNEL_METRIC_COUNT_INVALID", f"{where}: metric player/row counts are inconsistent")
            if c["source_known_at_utc"] != SOURCE_KNOWN_AT:
                _refuse("PERSONNEL_SOURCE_CLOCK_MISMATCH", f"{where}: another source clock")
            if c["target_game_feature_eligible"] is not False or c["protected_eligible"] is not False:
                _refuse("PERSONNEL_PIT_CLAIM_INVALID", f"{where}: claims target-game or protected eligibility")
            if c["classification"] != RETURNING_CLASSIFICATION:
                _refuse("PERSONNEL_RECORD_MISMATCH", f"{where}: classification differs")
            by_summary.setdefault(c["summary_key"], []).append(c)
        if signed_outside != expected["signed_ratios_outside_unit_interval"]:
            _refuse("PERSONNEL_RATIO_CLIPPED" if signed_outside < expected["signed_ratios_outside_unit_interval"] else
                    "PERSONNEL_RATIO_MISMATCH", f"{signed_outside} signed ratios outside [0,1], the contract expects "
                                                f"{expected['signed_ratios_outside_unit_interval']}")
        programs = records["program_seasons"]
        census_map: dict[tuple[int, str], str] = {}
        ambiguous: set[tuple[int, str]] = set()
        for p in programs:
            if p["chain_state"] == "QUALIFIED_EXACT_CHAIN":
                census_map[(p["season"], p["canonical_team_id"])] = p["program_season_key"]
            elif p["chain_state"] == "AMBIGUOUS_CANONICAL_TEAM_SHARED_IN_SEASON":
                ambiguous.add((p["season"], p["canonical_team_id"]))
        summaries = records["summaries"]
        summary_keys = {s["summary_key"] for s in summaries}
        for s in summaries:
            where = f"summary {s['summary_key']}"
            target, prior, team = s["target_season"], s["prior_season"], s["canonical_team_id"]
            if target not in TARGET_SEASONS or prior != target - 1 or s["summary_key"] != summary_key(target, team):
                _refuse("PERSONNEL_KEY_MISMATCH", f"{where}: key members differ")
            prior_set, current_set = rosters.get((prior, team), set()), rosters.get((target, team), set())
            returning_set = prior_set & current_set
            want = {"prior_roster_count": len(prior_set), "current_roster_count": len(current_set),
                    "returning_roster_count": len(returning_set), "departed_roster_count": len(prior_set - current_set),
                    "arrival_roster_count": len(current_set - prior_set), "union_roster_count": len(prior_set |
                                                                                                   current_set)}
            differing = sorted(k for k, v in want.items() if s[k] != v)
            if differing:
                _refuse("PERSONNEL_RETURNING_SET_MISMATCH", f"{where}: {differing} differ from the membership sets")
            rates = {"roster_retention_rate": share(want["returning_roster_count"], want["prior_roster_count"]),
                     "roster_arrival_rate": share(want["arrival_roster_count"], want["current_roster_count"]),
                     "roster_jaccard": share(want["returning_roster_count"], want["union_roster_count"])}
            if any(not _typed_equal(s[k], v) for k, v in rates.items()):
                _refuse("PERSONNEL_RATE_MISMATCH", f"{where}: a roster rate differs from its counts")
            mine = {c["component_key"]: c for c in by_summary.get(s["summary_key"], [])}
            if sorted(mine) != s["component_keys"]:
                _refuse("PERSONNEL_COMPONENT_LINK_MISMATCH", f"{where}: component keys differ from its components")
            missing = []
            for pair, field in sorted(PAIR_FIELDS):
                c = mine.get(component_key(target, team, *pair))
                if c is None:
                    missing.append(f"{pair[0]}|{pair[1]}")
                    if s[field] is not None:
                        _refuse("PERSONNEL_MISSING_NULL_INVALID", f"{where}: {field} is {s[field]!r} without any "
                                                                  "prior-season metric evidence (absent is null)")
                elif not _typed_equal(s[field], c["returning_share"]):
                    _refuse("PERSONNEL_SHARE_MISMATCH", f"{where}: {field} differs from its component")
            if s["missing_component_pairs"] != missing:
                _refuse("PERSONNEL_MISSING_NULL_INVALID", f"{where}: missing pairs differ")
            if s["partial_prior_metric_season"] is not (prior in PARTIAL_METRIC_SEASONS):
                _refuse("PERSONNEL_PARTIAL_SOURCE_INVALID", f"{where}: partial-season flag differs")
            if s["original_transition_time_pit_eligible"] is not False or s["target_game_feature_eligible"] is not \
                    False or s["protected_eligible"] is not False:
                _refuse("PERSONNEL_PIT_CLAIM_INVALID", f"{where}: claims PIT, target-game or protected eligibility")
            if s["source_known_at_utc"] != SOURCE_KNOWN_AT or s["classification"] != RETURNING_CLASSIFICATION:
                _refuse("PERSONNEL_SOURCE_CLOCK_MISMATCH", f"{where}: another source clock or classification")
            if original_feature(s)["feature_identity"] != s["feature_identity"]:
                _refuse("PERSONNEL_ORIGINAL_IDENTITY_MISMATCH", f"{where}: the original research identity differs "
                                                                "from its members")
            for side, season in (("target", target), ("prior", prior)):
                if (s[f"{side}_census_key"], s[f"{side}_census_association"]) != associate(season, team, census_map,
                                                                                         ambiguous):
                    _refuse("PERSONNEL_CENSUS_ASSOCIATION_MISMATCH", f"{where}: {side} census association differs")
            if s["census_scope_state"] != census_scope(target, prior):
                _refuse("PERSONNEL_CENSUS_ASSOCIATION_MISMATCH", f"{where}: census scope differs")
        for c in components:
            if c["summary_key"] not in summary_keys:
                _refuse("PERSONNEL_COMPONENT_LINK_MISMATCH", f"component {c['component_key']} has no summary")
            if original_component(c)["component_identity"] != c["component_identity"]:
                _refuse("PERSONNEL_ORIGINAL_IDENTITY_MISMATCH", f"component {c['component_key']}: the original "
                                                                "research identity differs from its members")
        for m in members:
            if (m["census_key"], m["census_association"]) != associate(m["season"], m["canonical_team_id"],
                                                                       census_map, ambiguous):
                _refuse("PERSONNEL_CENSUS_ASSOCIATION_MISMATCH", f"membership {m['membership_key']}: census "
                                                                 "association differs")
        seen_teams: dict[tuple[int, str], list[str]] = {}
        for p in programs:
            where = f"program-season {p['program_season_key']}"
            if p["season"] not in CENSUS_SEASONS or not PROGRAM_RE.match(p["team_key"]) or \
                    p["team_key"] != f"org:{p['org_id']}" or p["program_season_key"] != program_key(p["season"],
                                                                                                    p["team_key"]):
                _refuse("PERSONNEL_KEY_MISMATCH", f"{where}: key members differ")
            if p["chain_state"] not in CHAIN_STATES:
                _refuse("PERSONNEL_CHAIN_STATE_INVALID", f"{where}: undeclared chain state")
            cfbd = p["cfbd_team_id"]
            if p["core_identity_key"] is not None and p["core_identity_key"] != f"TEAM|SRC-002|{cfbd}":
                _refuse("PERSONNEL_NAMESPACE_INVALID", f"{where}: identity key {p['core_identity_key']!r} is not the "
                                                       "exact SRC-002 namespace of its CFBD team")
            qualified = p["chain_state"] == "QUALIFIED_EXACT_CHAIN"
            if qualified:
                if p["binding_rule"] not in CHAIN["accepted_binding_rules"] or cfbd is None or \
                        p["core_identity_key"] is None or p["core_entity_rows"] != 1 or \
                        p["core_entity_record_id"] != p["canonical_team_id"] or p["canonical_team_id"] is None or \
                        not TEAM_ID_RE.match(p["canonical_team_id"]):
                    _refuse("PERSONNEL_CHAIN_STATE_INVALID", f"{where}: a qualified chain lacks its exact links")
                seen_teams.setdefault((p["season"], p["canonical_team_id"]), []).append(p["program_season_key"])
                tkey = (p["season"], p["canonical_team_id"])
                want = {"admitted_membership_rows": rows_by.get(tkey, 0),
                        "admitted_distinct_players": len(rosters.get(tkey, ())),
                        "multi_team_players": len(multi_by.get(tkey, ())),
                        "nonadmitted_rows_same_canonical_team": nonadmitted_by.get(tkey, 0)}
                if any(p[k] != v for k, v in want.items()):
                    _refuse("PERSONNEL_COVERAGE_COUNT_MISMATCH", f"{where}: roster counts differ from the memberships")
                target = summary_key(p["season"], p["canonical_team_id"])
                prior = summary_key(p["season"] + 1, p["canonical_team_id"])
                if p["returning_target_summary_key"] != (target if target in summary_keys else None) or \
                        p["returning_prior_summary_key"] != (prior if prior in summary_keys else None):
                    _refuse("PERSONNEL_TRANSITION_LINK_MISMATCH", f"{where}: returning transition links differ")
                rows = want["admitted_membership_rows"]
                has_target = p["returning_target_summary_key"] is not None
                state = "ROSTER_AND_RETURNING_TRANSITION" if rows and has_target else \
                    "ROSTER_WITHOUT_RETURNING_TRANSITION" if rows else "NO_ADMITTED_ROSTER_ROWS"
                flags = (p["roster_presence"], p["transition_presence"], p["roster_supported"],
                         p["transition_supported"], p["coverage_state"])
                if flags != ("ADMITTED_ROSTER_ROWS_PRESENT" if rows else "NO_ADMITTED_ROSTER_ROWS",
                             "RETURNING_TRANSITION_PRESENT" if has_target else "NO_RETURNING_TRANSITION",
                             rows > 0, has_target, state):
                    _refuse("PERSONNEL_COVERAGE_STATE_MISMATCH", f"{where}: coverage flags differ from the records")
            else:
                if p["canonical_team_id"] is not None and not p["chain_state"].startswith("AMBIGUOUS"):
                    _refuse("PERSONNEL_CHAIN_STATE_INVALID", f"{where}: an unqualified chain names a canonical team")
                counts = (p["admitted_membership_rows"], p["admitted_distinct_players"], p["multi_team_players"],
                          p["nonadmitted_rows_same_canonical_team"])
                if counts != (None, None, None, None):
                    _refuse("PERSONNEL_UNKNOWN_COUNT_INVENTED", f"{where}: an unqualified chain states person counts "
                                                                "(unknown is null, never zero)")
                if (p["roster_presence"], p["transition_presence"], p["roster_supported"], p["transition_supported"],
                        p["returning_target_summary_key"], p["returning_prior_summary_key"]) != \
                        ("UNKNOWN_CHAIN_NOT_QUALIFIED", "UNKNOWN_CHAIN_NOT_QUALIFIED", False, False, None, None):
                    _refuse("PERSONNEL_COVERAGE_STATE_MISMATCH", f"{where}: an unqualified chain claims support")
                state = "IDENTITY_CHAIN_AMBIGUOUS" if p["chain_state"].startswith("AMBIGUOUS") else \
                    "IDENTITY_CHAIN_UNQUALIFIED"
                if p["coverage_state"] != state:
                    _refuse("PERSONNEL_COVERAGE_STATE_MISMATCH", f"{where}: coverage state differs")
            if p["division"] not in (*CENSUS_DIVISIONS, "DIVISION_CONFLICT") or \
                    p["divisions"] != sorted(set(p["divisions"])) or not set(p["divisions"]) <= set(CENSUS_DIVISIONS) \
                    or p["division"] != (p["divisions"][0] if len(p["divisions"]) == 1 else "DIVISION_CONFLICT"):
                _refuse("PERSONNEL_DIVISION_INVALID", f"{where}: division members are inconsistent")
            if p["parent_contest_count"] != len(p["parent_contest_keys"]) or \
                    p["parent_contest_keys"] != sorted(set(p["parent_contest_keys"])) or \
                    sum(p["parent_contest_dispositions"].values()) != p["parent_contest_count"] or \
                    p["parent_contest_count"] < 1:
                _refuse("PERSONNEL_PARENT_WITNESS_INVALID", f"{where}: contest witnesses are inconsistent")
        for keys in seen_teams.values():
            if len(keys) > 1:
                _refuse("PERSONNEL_CHAIN_STATE_INVALID", f"{keys}: two qualified chains share a canonical team in one "
                                                         "season (AMBIGUOUS_CANONICAL_TEAM_SHARED_IN_SEASON)")
        for table in RECORD_TABLES:
            for record, segment in zip(records[table], self.segments.get(table, [])):
                if segment_of_untrusted(table, record) != segment:
                    _refuse("PERSONNEL_INDEX_MISMATCH", f"{table} record {record_key(table, record)} sits in block "
                                                        f"segment {segment}")
        witnesses = records["witnesses"]
        wanted = witness_records(a)
        for got, want in zip(witnesses, wanted):
            if canonical_json_bytes(got) != canonical_json_bytes(want):
                differing = sorted(k for k in want if not _typed_equal(got.get(k), want[k]))
                _refuse("PERSONNEL_WITNESS_MISMATCH", f"witness {want['witness_key']} differs on {differing[:6]}")
        census = records["census"]
        if len(census) != 1:
            _refuse("PERSONNEL_CENSUS_MISMATCH", f"the census block holds {len(census)} records")
        rebuilt = census_record({"memberships": members, "exclusions": exclusions, "program_seasons": programs,
                                 "summaries": summaries, "components": components, "witnesses": witnesses,
                                 "coverage": census[0]["transition_coverage"] if isinstance(
                                     census[0]["transition_coverage"], list) and all(
                                     isinstance(r, dict) and set(r) == {*ORIGINAL_COVERAGE_FIELDS,
                                                                        "original_research_agreement"}
                                     for r in census[0]["transition_coverage"]) else [],
                                 "original_agreement": census[0]["original_research_agreement"]})
        if _untrusted_canonical(census[0], "PERSONNEL_RECORD_MALFORMED", "census") != canonical_json_bytes(rebuilt):
            differing = sorted(k for k in rebuilt if not _typed_equal(census[0].get(k), rebuilt[k]))
            _refuse("PERSONNEL_CENSUS_MISMATCH", f"the stored census differs from its records on {differing[:6]}")
        coverage = rebuilt["transition_coverage"]
        if len(coverage) != expected["coverage_rows"] or [r["target_season"] for r in coverage] != list(TARGET_SEASONS):
            _refuse("PERSONNEL_CENSUS_MISMATCH", "the transition coverage rows differ from the contract")
        for row in coverage:
            members_of = [s for s in summaries if s["target_season"] == row["target_season"]]
            comps = [c for c in components if c["target_season"] == row["target_season"]]
            if row["common_support_teams"] != len(members_of) or row["component_rows"] != len(comps) or \
                    row["missing_category_stat_cells"] != sum(len(s["missing_component_pairs"]) for s in members_of) \
                    or row["signed_ratios_outside_unit_interval"] != sum(1 for c in comps if c["outside_unit_interval"]) \
                    or row["prior_season"] != row["target_season"] - 1 or row["partial_prior_metric_season"] is not \
                    (row["prior_season"] in PARTIAL_METRIC_SEASONS):
                _refuse("PERSONNEL_CENSUS_MISMATCH", f"transition coverage {row['target_season']} differs from its "
                                                     "records")
            if row["prior_roster_teams"] != len({t for (s, t) in rosters if s == row["prior_season"]}) or \
                    row["current_roster_teams"] != len({t for (s, t) in rosters if s == row["target_season"]}):
                _refuse("PERSONNEL_CENSUS_MISMATCH", f"transition coverage {row['target_season']} roster team counts "
                                                     "differ from the memberships")

    def _index(self) -> None:
        self.programs_by_key = {p["program_season_key"]: p for p in self.records["program_seasons"]}
        self.summary_census = {s["summary_key"]: s["target_census_key"] for s in self.records["summaries"]}

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "PersonnelEvidence":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- serving
    @staticmethod
    def filters(grain: str, *, season: Any = None, team: Any = None, program: Any = None,
                player: Any = None) -> dict[str, Any]:
        """Validate a selection before any file is read: an unknown grain, a malformed or an inapplicable selector is
        refused with its own code (SELECTOR_MATRIX)."""
        if grain not in GRAINS:
            _refuse("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}")
        allowed = SELECTOR_MATRIX[grain]
        filters: dict[str, Any] = {}
        for name, value in (("season", season), ("team", team), ("program", program), ("player", player)):
            if value is not None and name not in allowed:
                _refuse("FILTER_NOT_APPLICABLE", f"{name} does not apply to the {grain} grain (allowed: {allowed})")
        if season is not None:
            if not is_int(season):
                _refuse("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if team is not None:
            text = team if isinstance(team, str) else None
            if text is None or not TEAM_ID_RE.match(text):
                _refuse("TEAM_INVALID", f"team must be an exact canonical team ID team_<32 hex>, got {team!r}")
            filters["team"] = text
        if program is not None:
            text = program.strip() if isinstance(program, str) else None
            if text is not None and text.isascii() and text.isdigit():
                text = f"org:{text}"
            if text is None or not PROGRAM_RE.match(text):
                _refuse("PROGRAM_INVALID", f"program must be an exact source-qualified org:<digits>, got {program!r}")
            filters["program"] = text
        if player is not None:
            text = player if isinstance(player, str) else None
            if text is None or not PLAYER_ID_RE.match(text):
                _refuse("PLAYER_INVALID", f"player must be an exact canonical player ID player_<32 hex>, got "
                                          f"{player!r}")
            filters["player"] = text
        return filters

    def source_time(self) -> dict[str, Any]:
        captures = [c for kind in ("ROSTER", "METRIC") for c in self.anchors["captures"][kind]]
        return {"source_repository": SOURCE_REPOSITORY, "source_commit_sha": SOURCE_COMMIT,
                "source_repository_commit_utc": SOURCE_KNOWN_AT,
                "clock_kind": "PUBLIC_REPOSITORY_COMMITTER_TIME_NOT_A_HISTORICAL_EFFECTIVE_OR_PUBLICATION_TIME",
                "capture_acquired_at_utc": sorted({c["acquired_at_utc"] for c in captures}),
                "parent_issued_at_utc": {name: spec["issued_at_utc"] for name, spec in self.anchors["inputs"].items()
                                         if spec.get("issued_at_utc") is not None},
                "release_provenance_issued_at_utc": (self.binding.get("provenance") or {}).get("issued_at_utc")
                if isinstance(self.binding.get("provenance"), dict) else None,
                "release_provenance_note": "the run manifest's provenance build clock; not identity-bound",
                "effective_grain": LABELS["effective_grain"]}

    def query(self, grain: str, *, season: Any = None, team: Any = None, program: Any = None, player: Any = None,
              limit: int | None = 50, offset: int = 0, all_rows: bool = False) -> dict[str, Any]:
        filters = self.filters(grain, season=season, team=team, program=program, player=player)
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
            "denominators": {k: census[k] for k in ("memberships", "exclusions", "program_seasons", "summaries",
                                                    "components", "witnesses")},
            "verification": {f"{t}_verified": len(self.records[t]) for t in RECORD_TABLES} | {
                "records_verified": True, "content_identity_rebuilt": True, "database_document_rebuilt": True,
                "profile_pinned": self.anchors.get("profile") is not None}}
        if "season" in filters and filters["season"] not in GRAIN_SEASONS[grain]:
            result.update(season_scope_state="SEASON_OUTSIDE_RELEASE", total=0, returned=0, rows=[], next_offset=None,
                          note=f"the {grain} grain covers seasons {GRAIN_SEASONS[grain][0]}-"
                               f"{GRAIN_SEASONS[grain][-1]}; no row is fabricated for another season")
            if grain == "returning-summary":
                result["transition_coverage"] = []
            return result
        rows = [r for r in self.records[table] if self._match(grain, r, filters)]
        total = len(rows)
        page = rows[offset:] if all_rows else rows[offset:offset + (limit or 0)]
        result.update(season_scope_state="RETROSPECTIVE_SEASONS", total=total, returned=len(page), rows=page,
                      next_offset=offset + len(page) if offset + len(page) < total else None)
        if grain == "returning-summary":
            result["transition_coverage"] = [] if ("team" in filters or "program" in filters) else [
                r for r in census["transition_coverage"] if "season" not in filters or
                r["target_season"] == filters["season"]]
        return result

    def _match(self, grain: str, record: dict[str, Any], filters: dict[str, Any]) -> bool:
        if "season" in filters:
            season = record["season"] if grain in ("roster-membership", "roster-exclusion", "program-season-coverage",
                                                   "source-witness") else record["target_season"]
            if season != filters["season"]:
                return False
        if "team" in filters and record["canonical_team_id"] != filters["team"]:
            return False
        if "player" in filters and record["canonical_player_id"] != filters["player"]:
            return False
        if "program" in filters:
            if grain == "program-season-coverage":
                return record["team_key"] == filters["program"]
            if grain == "roster-membership":
                key = record["census_key"]
            elif grain == "returning-component":
                key = self.summary_census.get(record["summary_key"])
            else:
                key = record["target_census_key"]
            return key is not None and key.split("|", 1)[1] == filters["program"]
        return True


def segment_of_untrusted(table: str, record: dict[str, Any]) -> str | None:
    value = record.get(SEASON_FIELDS.get(table, ""), None) if table in SEASON_FIELDS else "GLOBAL"
    if table in SEASON_FIELDS:
        return str(value) if type(value) is int else None
    return value


def _order_key(table: str, record: dict[str, Any]) -> tuple[Any, ...]:
    if table == "memberships":
        return (record["season"], record["canonical_player_id"], record["canonical_team_id"], record["observation_id"])
    if table == "exclusions":
        return (record["season"], record["observation_id"])
    if table == "program_seasons":
        return (record["season"], _org_sort(record["team_key"]))
    if table == "summaries":
        return (record["target_season"], record["canonical_team_id"])
    if table == "components":
        return (record["target_season"], record["canonical_team_id"], record["category"], record["stat_type"])
    return (0,)
