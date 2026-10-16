r"""National 2023 game context over the 788 accepted FBS targets (BAT-729 bounded context contribution, Cycle #58
TP58-A01).

Every rule lives here, and the committed context data contract ``configs/national_game_context_2023_contract.json``
must equal these constants (the builder refuses otherwise). The reader pins that contract's SHA-256, the accepted parent
identities and the SHA-256 of every retained raw input (:data:`ANCHORS`).

Inputs, each resolved under an explicitly named data root at the contract's relative locator, refused unless its bytes
hash to the pinned SHA-256 (nothing here is acquired; no source request is made):

* the accepted BAT-711 history-prefix database aba0384f (targets, their two oriented views and each view's accepted
  eligible same-season prior pool and exclusions; the 788 targets of season 2023 are the complete denominator);
* the accepted BAT-710 parent population database 3baff07f (the 2023 contest rows: participants, dates, site and the
  documented CFBD game identifiers of every target, and every earlier same-season contest of each participant);
* the accepted C38 participant identity bindings (``org_id`` -> ``cfbd_team_id`` under the documented
  NAME_CONFIRMED_BY_SCHEDULE or SCHEDULE_FINGERPRINT_ONLY rule; never equal numeric IDs, names or fuzzy matching);
* the retained 2023 CFBD FBS game capture ebf9ea17 (one documented game row per target);
* the retained 2023 CFBD team-season bytes 5daa333c and venue reference bytes dfc8daff, observed in September 2026
  (later-observed reference geography: never historically effective, never a PIT or itinerary claim);
* the accepted, unchanged C56 national retrospective reference ad01a42f (content fe303a90): only its 2023 score block,
  each block's index columns verified against its own content; nothing is refit or re-scored.

Derived records (one immutable, create-only, content-addressed release; every row stays in the denominator):

1. **contest context** (one per target, in the accepted history's target order): the accepted parent role
   (HOME_A/HOME_B/NEUTRAL) and the provider's separate site/venue claim with their agreement kept explicit; the
   documented provider join (participants through the bindings, the provider start instant as a claim only, a declared
   local-date compatibility window, no timezone inference); the provider venue and its later-observed reference
   coordinate; the game-level strata assignments.
2. **team context** (two oriented views per target): each team's own binding, parent and provider roles, the calendar
   interval since its latest strictly earlier eligible same-season contest (``calendar_interval_days`` = date
   difference, ``intervening_calendar_days`` = difference minus one; an empty pool is null with
   NO_ELIGIBLE_SAME_SEASON_PRIOR, never zero or a previous season; several genuine keys on the latest date are exposed
   as AMBIGUOUS_LATEST_PRIOR, never chosen by input order), its own later-observed reference origin and the spherical
   great-circle reference distance from that origin to the game venue in integer metres (never an opponent's origin;
   a neutral venue never becomes either team's home; the home team's distance may be nonzero).
3. **context witnesses**: one record per decision-bearing source per subject (history target and view, parent contest,
   identity binding, provider game row, provider team location, venue reference row, frozen reference score) plus the
   pinned source clocks, each with its exact raw members, locator, state and reason (absent sources keep a null raw value
   and their reason).
4. **score strata**: the frozen C56 2023 game-grain score of every target and model counted once per family (ALL, the
   accepted site class, the minimum of the two qualified calendar intervals and the maximum of the two qualified
   reference distances) in fixed bins; exact rational Brier and decimal-string log-loss sums for the probability
   models, exact absolute and squared error for the ridge margin model (never a probability or Brier score); each
   family partitions the 788 games of every model; descriptive exposed-2023 slices only.
5. **census**: state counts of every grain.

Every record carries RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED and predictive skill NOT_ESTABLISHED.
Reference distance is geometry, not travel; the calendar interval is not physiological rest; strata are not effects,
a blind test, calibration, model selection or a skill claim.

The reader (:class:`GameContext`) refuses with a stable code unless the location, the run manifest, the database
bytes, the schema, every meta claim, the complete membership and multiplicity of every table, every record, the
census, the content identity and the contract-defined database identity document equal what it re-derives from the
pinned inputs. Identity documents compare as canonical bytes (13.0, booleans and extra members never equal the
contract document). The query (:meth:`GameContext.query`) serves the contest-context, team-context, context-witness and
context-score-summary grains with exact intersecting selectors and paging; an unknown valid selection serves no row,
the summary included; other seasons are reported as not yet audited.
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import math
import os
import random
import re
import sqlite3
import zlib
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics import readonly_sqlite
from aggie_analytics.cycle30.site_context import haversine_km
from aggie_analytics.retrospective_baseline import benchmark as bm

canonical_json_bytes = bm.canonical_json_bytes
canonical_line = bm.canonical_line
sha256_bytes = bm.sha256_bytes
sha256_file = bm.sha256_file
rational = bm.rational
decimal_text = bm.decimal_text
is_int = bm.is_int
_io_path = bm._io_path
manifest_path_for = bm.manifest_path_for
IDENTITY_RE = bm.IDENTITY_RE

# --------------------------------------------------------------------------------------------- identity and scope

POPULATION = "national_game_context_2023"
DB_FILE = "national_game_context.sqlite"
CONTRACT_ID = "BAT-729-NATIONAL-GAME-CONTEXT-2023-V1.0"
CONTRACT_REL = "configs/national_game_context_2023_contract.json"
CONTENT_SCHEMA = "BAS-GAME-CONTEXT-CONTENT-1"
DATABASE_SCHEMA = "BAS-GAME-CONTEXT-DATABASE-1"
DB_SCHEMA = "BAS-GAME-CONTEXT-DB-1"
PAYLOAD_SCHEMA = "BAS-GAME-CONTEXT-PAYLOAD-1"
SEASON = 2023
VIEWS = ("A", "B")
INPUT_NAMES = ("history", "population", "identity_bindings", "provider_games", "provider_teams", "venue_reference",
               "reference")

LABELS = {
    "evidence_label": "RETROSPECTIVE_RESEARCH",
    "trust_state": "UNTRUSTED_SHADOW",
    "pit_eligibility": "PIT_NOT_ADMITTED",
    "predictive_skill": "NOT_ESTABLISHED",
    "temporal_basis": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME",
    "forecast_status": "NOT_A_FORECAST",
    "geography_authority": "LATER_OBSERVED_REFERENCE_GEOGRAPHY_NOT_HISTORICALLY_EFFECTIVE",
    "distance_meaning": "REFERENCE_GEOMETRY_NOT_ACTUAL_TRAVEL",
    "calendar_meaning": "CALENDAR_INTERVAL_NOT_PHYSIOLOGICAL_REST",
    "site_meaning": "ACCEPTED_PARENT_ROLE_AND_PROVIDER_CLAIM_KEPT_SEPARATE_NO_HOME_EFFECT",
    "strata_meaning": "DESCRIPTIVE_EXPOSED_2023_SLICES_NOT_CAUSAL_NOT_BLIND_NOT_SKILL",
}
RECORD_LABELS = {k: LABELS[k] for k in ("evidence_label", "trust_state", "pit_eligibility", "predictive_skill")}
CONTEXT_LABELS = {**RECORD_LABELS, **{k: LABELS[k] for k in ("geography_authority", "distance_meaning",
                                                             "calendar_meaning")}}
STRATA_LABELS = {**RECORD_LABELS, "strata_meaning": LABELS["strata_meaning"]}

#: The five frozen C56 models with their metric and output kinds and the SHA-256 of their frozen definitions (the C56
#: reference's ``model_sha256``); the ridge model is a margin model and never receives a probability or Brier score.
MODELS: dict[str, dict[str, str]] = {
    "NULL_HALF_V1": {"metric_kind": "PROBABILITY", "output_kind": "WIN_PROBABILITY",
                     "model_sha256": "c9f511c047ef9a24ff5873021660e2592e0fd6fa69865418696cbd2cdff6fe04"},
    "SMOOTHED_HISTORY_ODDS_V1": {"metric_kind": "PROBABILITY", "output_kind": "WIN_PROBABILITY",
                                 "model_sha256": "340128c116d4e5902f582827c0400bb63d8417973d63cd815481fc985126cbfa"},
    "SITE_BLIND_ELO_REFERENCE_V1": {"metric_kind": "PROBABILITY", "output_kind": "WIN_PROBABILITY",
                                    "model_sha256": "8ed6384a46a630eb32d833ca508bbc6dca61e6e6fa4300f3e38fc8bf7eb7c73a"},
    "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1": {
        "metric_kind": "PROBABILITY", "output_kind": "WIN_PROBABILITY",
        "model_sha256": "eb074c84ad3e50fd268d354904f6b11c23f6c3fc844b743fc112917adafd8bc5"},
    "PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1": {
        "metric_kind": "MARGIN", "output_kind": "EXPECTED_MARGIN_ONLY_NO_PROBABILITY",
        "model_sha256": "619cbf736dad1f86efed4791b6537ccad11e546c24ab09de0a9c861797b64d30"},
}
MODEL_IDS = tuple(MODELS)
MARGIN_MODELS = tuple(m for m, d in MODELS.items() if d["metric_kind"] == "MARGIN")

ACCEPTED_BINDING_RULES = ("NAME_CONFIRMED_BY_SCHEDULE", "SCHEDULE_FINGERPRINT_ONLY")
PRIOR_RULE = "SAME_SEASON_DATE_STRICTLY_BEFORE_TARGET_DATE"

BINDING = {
    "input": "identity_bindings",
    "rule": "each target participant org_id maps to exactly one accepted C38 binding row whose cfbd_team_id is a digit "
            "string and whose rule is NAME_CONFIRMED_BY_SCHEDULE or SCHEDULE_FINGERPRINT_ONLY; otherwise the side is "
            "UNSUPPORTED with its reason",
    "accepted_rules": list(ACCEPTED_BINDING_RULES),
    "never": "equal numeric IDs, team names, abbreviations or fuzzy matching",
}
PROVIDER_JOIN = {
    "documented_game_ids": "the accepted target's cfbd_game_ids (equal to the parent contest row's); exactly one is "
                           "required",
    "game_row": "the single capture row whose integer id equals that identifier; a duplicated id is ambiguous",
    "participants": "the unordered pair of the row's integer homeId and awayId equals the two bound cfbd_team_id values",
    "season": "the row's integer season equals 2023",
    "field_shapes": "id, season, homeId and awayId are JSON integers, neutralSite and startTimeTBD booleans, startDate "
                    "a string; any other shape is PROVIDER_FIELD_MALFORMED with the raw witness kept",
    "site_claim": "neutralSite true is a NEUTRAL claim; false claims HOME for the side whose binding equals homeId; the "
                  "claim is kept separate from the accepted parent role and their agreement is explicit",
    "start": "startDate is a provider start claim (never an actual kickoff, never a timezone)",
}
DATE_WINDOW = {
    "rule": "the provider start instant is compatible with the accepted parent local date D when it lies in "
            "[D 00:00 at UTC+14:00, D 24:00 at UTC-12:00), i.e. [D-1 10:00Z, D+1 12:00Z); no timezone is inferred",
    "lower_offset_hours": -14,
    "upper_offset_hours": 36,
    "pattern": "YYYY-MM-DDTHH:MM:SS[.ffffff]Z",
}
COORDINATES = {
    "types": "a JSON integer or binary64 number, never a boolean, string or null",
    "finite": True,
    "latitude_degrees": [-90, 90],
    "longitude_degrees": [-180, 180],
    "authority": "later-observed reference geography from the retained provider bytes (September 2026 cache "
                 "observation); not historically effective and never PIT evidence",
}
DISTANCE = {
    "method": "SPHERICAL_GREAT_CIRCLE_HAVERSINE",
    "radius_m": "6371008.8",
    "formula": "2 * R * asin(min(1, sqrt(sin^2(dphi / 2) + cos(phi1) * cos(phi2) * sin^2(dlambda / 2))))",
    "longitude_wrap": "dlambda is the raw longitude difference; sin^2(dlambda / 2) is 2*pi periodic, so the "
                      "antimeridian needs no special case",
    "implementation": "aggie_analytics.cycle30.site_context.haversine_km (IUGG mean radius 6371.0088 km) times 1000",
    "rounding": "NEAREST_INTEGER_METRE_ROUND_HALF_EVEN_OF_THE_EXACT_BINARY64_VALUE",
    "unit": "metre",
    "legs": "each oriented team's own later-observed reference origin (its provider team location) to the game's "
            "later-observed venue coordinate; identical coordinates give 0",
    "unsupported": "null with the reason when either coordinate is not qualified; never zero-filled",
}
CALENDAR = {
    "prior_rule": PRIOR_RULE,
    "pool": "the accepted history view's contributing contests (the accepted eligible same-season prior pool); its "
            "contributing and excluded keys must partition the parent's earlier same-season contests of that team",
    "calendar_interval_days": "target date minus the latest eligible prior date, in days",
    "intervening_calendar_days": "calendar_interval_days minus one",
    "empty_pool": "null intervals with NO_ELIGIBLE_SAME_SEASON_PRIOR; never zero, never a previous season",
    "tie": "several eligible prior keys on the latest date: AMBIGUOUS_LATEST_PRIOR with every key and null intervals; "
           "never input order",
    "not_strictly_earlier": "the team's other same-season parent contests dated on or after the target date (or "
                            "undated) are never eligible and are counted",
    "never": "physiological rest, all played games or travel",
}
SITE_CLASSES = {"HOME_A": "NON_NEUTRAL_HOME_AWAY", "HOME_B": "NON_NEUTRAL_HOME_AWAY", "NEUTRAL": "NEUTRAL"}
CALENDAR_BINS = (("DAYS_1_6", 1, 6), ("DAYS_7", 7, 7), ("DAYS_8_13", 8, 13), ("DAYS_14_PLUS", 14, None))
DISTANCE_BINS = (("M_0_499999", 0, 499_999), ("M_500000_1499999", 500_000, 1_499_999),
                 ("M_1500000_PLUS", 1_500_000, None))
FAMILIES: dict[str, tuple[str, ...]] = {
    "ALL": ("ALL",),
    "SITE": ("NEUTRAL", "NON_NEUTRAL_HOME_AWAY", "UNSUPPORTED"),
    "MIN_CALENDAR": tuple(b[0] for b in CALENDAR_BINS) + ("NO_PRIOR", "UNSUPPORTED"),
    "MAX_DISTANCE": tuple(b[0] for b in DISTANCE_BINS) + ("UNSUPPORTED",),
}
FAMILY_IDS = tuple(FAMILIES)
STRATA = {
    "families": {k: list(v) for k, v in FAMILIES.items()},
    "site": "the accepted parent site: NEUTRAL, or HOME_A/HOME_B as NON_NEUTRAL_HOME_AWAY; anything else UNSUPPORTED",
    "min_calendar": "both views QUALIFIED_CALENDAR_INTERVAL: the bin of the smaller interval; else any "
                    "AMBIGUOUS_LATEST_PRIOR: UNSUPPORTED; else NO_PRIOR",
    "max_distance": "both views QUALIFIED_REFERENCE_DISTANCE: the bin of the larger distance; else UNSUPPORTED",
    "calendar_bins": [list(b) for b in CALENDAR_BINS],
    "distance_bins_m": [list(b) for b in DISTANCE_BINS],
    "weighting": "each target's single frozen A-oriented C56 score per model, once per family (mirrored oriented rows "
                 "never double-weight a score)",
    "metrics": {"PROBABILITY": "exact rational Brier total and mean; log-loss total and mean as the exact sum of the "
                               "frozen decimal strings (convention copied)",
                "MARGIN": "exact rational absolute and squared error totals, MAE and MSE; no probability, Brier or "
                          "log loss"},
    "empty_stratum": "the canonical summary keeps every declared stratum (zero games, null means); a game selection "
                     "keeps only strata holding a selected game",
    "reading": "descriptive exposed-2023 slices; not causal, not a blind test, no significance, calibration, model "
               "selection or skill claim; null and adverse results retained",
}
SOURCES = ("ACCEPTED_HISTORY_TARGET", "ACCEPTED_PARENT_CONTEST", "PROVIDER_GAME", "VENUE_REFERENCE",
           "ACCEPTED_HISTORY_VIEW", "IDENTITY_BINDING", "PROVIDER_TEAM_LOCATION", "FROZEN_REFERENCE_SCORE",
           "SOURCE_RECEIPT")
CONTEST_SOURCES = SOURCES[:4]
VIEW_SOURCES = SOURCES[4:7]
CLOCK_SOURCES = ("provider_games", "provider_teams", "venue_reference")
#: The decision-bearing fields each witness source supports (fixed per source; SOURCE_RECEIPT per clock).
WITNESS_SUPPORTS: dict[str, tuple[str, ...]] = {
    "ACCEPTED_HISTORY_TARGET": ("contest_key", "season", "contest_date", "a_key", "b_key", "parent_site",
                                "provider_documented_game_ids"),
    "ACCEPTED_PARENT_CONTEST": ("contest_date", "a_key", "b_key", "parent_site", "parent_neutral_site_text",
                                "provider_documented_game_ids"),
    "PROVIDER_GAME": ("provider_game_id", "provider_site_claim", "provider_neutral_site", "provider_start_claim_utc",
                      "provider_date_state", "venue_id", "provider_venue_name"),
    "VENUE_REFERENCE": ("venue_reference_name", "venue_latitude", "venue_longitude", "venue_coordinate_state"),
    "ACCEPTED_HISTORY_VIEW": ("eligible_prior_count", "excluded_prior_count", "latest_prior_date",
                              "calendar_interval_days", "calendar_state"),
    "IDENTITY_BINDING": ("cfbd_team_id", "binding_rule", "binding_state"),
    "PROVIDER_TEAM_LOCATION": ("origin_location_id", "origin_latitude", "origin_longitude", "origin_state"),
    "FROZEN_REFERENCE_SCORE": ("context-score-summary",),
    "SOURCE_RECEIPT:provider_games": ("provider_game_retrieved_at_utc",),
    "SOURCE_RECEIPT:provider_teams": ("origin_observed_at_utc",),
    "SOURCE_RECEIPT:venue_reference": ("venue_observed_at_utc",),
}
GAME_WITNESS_KEYS = ("id", "season", "week", "seasonType", "startDate", "startTimeTBD", "neutralSite", "homeId",
                     "homeTeam", "awayId", "awayTeam", "venueId", "venue")
SCORE_WITNESS_KEYS = ("model_id", "model_sha256", "metric_kind", "orientation", "score_state", "unscored_reason",
                      "sample_state", "brier", "log_loss", "log_loss_convention", "absolute_error", "squared_error")
PARENT_COLUMNS = ("contest_key", "season", "term", "contest_date", "site", "neutral_site_text", "contest_status",
                  "disposition", "reconciliation_state", "a_key", "b_key", "a_org_id", "b_org_id", "a_team_name",
                  "b_team_name", "cfbd_game_ids")
#: The exact members of every record kind (TP58 section 3 semantic field schemas; an extra or missing member refuses).
RECORD_FIELDS: dict[str, tuple[str, ...]] = {
    "contests": (
        "record_type", "contest_key", "ncaa_contest_id", "season", "term", "contest_date",
        "a_key", "a_org_id", "a_team_name", "a_division_label", "b_key", "b_org_id", "b_team_name", "b_division_label",
        "classification_pair", "parent_site", "parent_neutral_site_text", "site_class",
        "provider_documented_game_ids", "provider_game_id", "provider_join_state", "provider_join_reason",
        "provider_home_side", "provider_neutral_site", "provider_site_claim", "site_agreement",
        "provider_start_claim_utc", "provider_start_time_tbd", "provider_date_state",
        "provider_utc_date_minus_parent_date_days", "provider_season_type", "provider_week",
        "provider_game_retrieved_at_utc", "venue_id", "provider_venue_name", "venue_reference_name",
        "venue_name_state", "venue_latitude", "venue_longitude", "venue_coordinate_state", "venue_coordinate_reason",
        "venue_observed_at_utc", "venue_clock_kind",
        "min_calendar_interval_days", "min_calendar_state", "min_calendar_stratum",
        "max_reference_distance_m", "max_distance_state", "max_distance_stratum",
        "witness_keys", *CONTEXT_LABELS),
    "teams": (
        "record_type", "contest_key", "season", "contest_date", "view", "team_key", "team_org_id", "team_name",
        "team_division_label", "opponent_key", "opponent_name", "parent_site", "parent_role_for_team",
        "provider_role_for_team", "provider_site_claim_for_team",
        "cfbd_team_id", "binding_rule", "binding_state", "binding_reason",
        "prior_rule", "eligible_prior_count", "excluded_prior_count", "excluded_prior_reasons",
        "excluded_prior_contest_keys", "not_strictly_earlier_contests", "latest_prior_date",
        "latest_prior_contest_keys", "calendar_interval_days", "intervening_calendar_days", "calendar_state",
        "origin_location_id", "origin_location_name", "origin_latitude", "origin_longitude", "origin_state",
        "origin_reason", "origin_observed_at_utc", "origin_clock_kind",
        "venue_id", "venue_coordinate_state", "reference_distance_m", "distance_state", "distance_reason",
        "distance_method", "origin_is_game_venue", "witness_keys", *CONTEXT_LABELS),
    "witnesses": (
        "record_type", "witness_key", "subject_kind", "contest_key", "view", "team_key", "model_id", "source",
        "locator", "supports", "raw", "raw_sha256", "state", "reason", *RECORD_LABELS),
    "census": (
        "record_type", "season", "contests", "team_views", "witnesses", "strata_rows", "contest_states",
        "team_states", "witness_sources", "witness_states", "unsupported_reasons", "distance_m",
        "calendar_interval_days", *RECORD_LABELS),
}
STRATA_COMMON_FIELDS = (
    "record_type", "family", "stratum", "model_id", "model_sha256", "metric_kind", "output_kind", "games",
    "score_records", "scored_games", "unscored_games", "unscored_by_reason", "scored_by_sample_state",
    "member_contest_keys_sha256", "member_score_lines_sha256", "reading", *STRATA_LABELS)
STRATA_METRIC_FIELDS = {
    "PROBABILITY": ("brier_total", "brier_total_decimal", "brier_mean", "brier_mean_decimal", "log_loss_total",
                    "log_loss_total_decimal", "log_loss_mean", "log_loss_mean_decimal", "log_loss_convention",
                    "log_loss_basis"),
    "MARGIN": ("absolute_error_total", "absolute_error_total_decimal", "mae", "mae_decimal", "squared_error_total",
               "squared_error_total_decimal", "mse", "mse_decimal"),
}
PROBABILITY_ONLY_FIELDS = ("brier_total", "brier_mean", "brier_total_decimal", "brier_mean_decimal", "log_loss_total",
                           "log_loss_mean", "log_loss_total_decimal", "log_loss_mean_decimal", "probability",
                           "probability_a", "win_probability")
SELECTORS = {
    "season": "an integer; 2023 is the audited season, any other season is NOT_YET_AUDITED with no row",
    "contest": "an exact accepted contest key ncaa:<1-12 digits> (bare digits read as ncaa:<digits>); every grain; a "
               "well-formed key outside the release selects no row",
    "team": "an exact accepted organization key org:<1-12 digits> (bare digits read as org:<digits>); contest and "
            "summary grains: either participant; team grain: the view's own team; witness grain: the contest "
            "witnesses of its games and its own view witnesses; no names",
    "orientation": "A or B; team-context and context-witness grains only",
    "source": "one declared witness source; context-witness grain only",
    "model": "one of the five frozen model IDs; context-score-summary and context-witness grains only",
    "family": "ALL, SITE, MIN_CALENDAR or MAX_DISTANCE; context-score-summary grain only",
    "paging": "--limit (default 50, non-negative), --offset (non-negative) or --all; exact totals in payload order",
    "intersection": "selectors intersect; an unknown or disjoint valid selection serves no row (the summary "
                    "included); malformed or inapplicable selectors are refused before any file is read",
    "pit": "--require-pit is always refused",
}
SCOPE = {
    "season": SEASON,
    "population": "the 788 accepted 2023 FBS targets of the accepted history (FCS opponents included as participants) "
                  "and their 1,576 oriented views",
    "horizon": "retrospective calendar and site context with later-observed reference geography; no PIT, forecast, "
               "itinerary, timezone, crowd, home-field or travel effect",
    "not_audited": "every other season, national FCS/lower-division contests as targets and deeper history",
}

# --------------------------------------------------------------------------------------------- anchors

#: The pinned production authority: the committed contract, every accepted or retained input (relative locator under
#: the explicitly named data root, SHA-256 and identities), the source clocks read from the acquisition receipts at build
#: time, and the expected complete denominator.
ANCHORS: dict[str, Any] = {
    "contract_id": CONTRACT_ID,
    "contract_sha256": "91f1f4e0b3a62ff3f76cd4167f42175f5b0bb9548fa2311df7ca592252c204b7",
    "inputs": {
        "history": {
            "relative_path": "canonical/national_history_prefix_2016_2023/sha256/"
                             "aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b/national_history.sqlite",
            "sha256": "e137208cb3e9fec55c9b68e6af5c61e036ea7ea60a8973d9be9c35c358b17060",
            "database_identity": "aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b",
            "content_identity": "58c2bf7d6e9c70c2ba2a9e4dd583a89ace10062cc49aafe00d2f9675c84afe63",
            "contract_sha256": "2646a5cbe9a1daff7135671b85c98239b250d493c53c4bc066f57805e1e4f76c"},
        "population": {
            "relative_path": "canonical/national_di_population_2016_2025/sha256/"
                             "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27/national_population.sqlite",
            "sha256": "9c517af94b9e0c7105627397b8a8cd9f9fc0ee806493c126c842c5018c5ba172",
            "database_identity": "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27",
            "contract_sha256": "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903"},
        "identity_bindings": {
            "relative_path": "canonical/national_di_population_2016_2025/sha256/"
                             "711e9dfcc35a181d51206099f41aa576424fc30ed61600811ab464074fb8f81e/identity_bindings.jsonl.gz",
            "sha256": "5d15acf7c12b94d5e7ad5fa2d22c60192aad0b4d6a48cecd66cab6835596dee9",
            "header_contract_sha256": "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903"},
        "provider_games": {
            "relative_path": "raw/SRC-002/games/sha256_ebf9ea175c3332102dd4555fd8cd126cbd2cbc6cef4aebe95c6c5ae7af1dea03.json",
            "sha256": "ebf9ea175c3332102dd4555fd8cd126cbd2cbc6cef4aebe95c6c5ae7af1dea03"},
        "provider_teams": {
            "relative_path": "ops/cycle30_work/raw/teams/194b170d1efaabbd3ea327ce7a1605f093cfa5f5391bd2a3ebfb39e297590619.json",
            "sha256": "5daa333ccc54b5890dd495744a959782af0fbb0cc6179217cb162cd904785281"},
        "venue_reference": {
            "relative_path": "ops/cycle30_work/raw/venues/86af256ba80c8b9961950607800057c188f4aec7034c4ac774f4dcf9475bfc93.json",
            "sha256": "dfc8daff311f5ffea668c613aef61bbd213ea0c08cd13e9c1e8f583a480fb9bf"},
        "reference": {
            "relative_path": "canonical/national_retrospective_reference_2016_2023/sha256/"
                             "ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8/"
                             "national_retrospective_reference.sqlite",
            "sha256": "17a0776587eb30918903dc0d38c736958b1984feb4b40379bbfc80425035785d",
            "database_identity": "ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8",
            "content_identity": "fe303a90d8753956b914d3c7c2adfe2d33d9816bfb45689b0361f8e36e2e6cc0",
            "contract_sha256": "3cfeff255bb29801b482b02611ad2c72c725d069e9f89d3911e86711af34bb31"},
    },
    "source_clocks": {
        "provider_games": {
            "receipt_relative_path": "manifests/captures/SRC-002/cap_2c82aa5161f3ad63b5abb3c3.json",
            "receipt_sha256": "6598b949b38fc707831002bc202bbf060ff7faeaceea178fb1748b8d8dbea4f3",
            "receipt_kind": "SRC-002 capture manifest",
            "capture_id": "cap_2c82aa5161f3ad63b5abb3c3", "request_id": "req_93d6738739a9e0d462795deb",
            "source_uri": "https://api.collegefootballdata.com/games?classification=fbs&year=2023",
            "parameters": {"classification": "fbs", "year": "2023"}, "http_status": 200, "status": "SUCCESS",
            "response_sha256": "ebf9ea175c3332102dd4555fd8cd126cbd2cbc6cef4aebe95c6c5ae7af1dea03", "row_count": 910,
            "retrieved_at_utc": "2026-08-09T16:57:56Z",
            "clock_kind": "PROVIDER_CAPTURE_RETRIEVED_AT_NOT_PUBLICATION_OR_KNOWN_AT"},
        "provider_teams": {
            "receipt_relative_path": "ops/cycle30_work/outputs/CYCLE30_ACQUISITION_LEDGER.json",
            "receipt_sha256": "dd29ab5a2fb1bb3169ef10b1ec6f02438e5c8b4fae5adbef88d6baaa082c9258",
            "receipt_kind": "C30 acquisition ledger attempts 41 and 42",
            "ledger_attempts": [41, 42], "route": "/teams",
            "parameters": [{"classification": "fbs", "year": 2023}, {"classification": "fcs", "year": 2023}],
            "http_status": 200, "status": "CACHE_HIT",
            "response_sha256": "5daa333ccc54b5890dd495744a959782af0fbb0cc6179217cb162cd904785281", "row_count": 671,
            "retrieved_at_utc": "2026-09-09T18:08:44Z",
            "clock_kind": "C30_LEDGER_CACHE_HIT_RECORDED_AT_NOT_ORIGINAL_RETRIEVAL_NOT_HISTORICAL",
            "observation": "both classification requests returned the same bytes; the year parameter does not make "
                           "the location fields historically effective"},
        "venue_reference": {
            "receipt_relative_path": "ops/cycle30_work/outputs/CYCLE30_ACQUISITION_LEDGER.json",
            "receipt_sha256": "dd29ab5a2fb1bb3169ef10b1ec6f02438e5c8b4fae5adbef88d6baaa082c9258",
            "receipt_kind": "C30 acquisition ledger attempt 0",
            "ledger_attempts": [0], "route": "/venues", "parameters": [{}], "http_status": 200, "status": "CACHE_HIT",
            "response_sha256": "dfc8daff311f5ffea668c613aef61bbd213ea0c08cd13e9c1e8f583a480fb9bf", "row_count": 852,
            "retrieved_at_utc": "2026-09-09T18:08:43Z",
            "clock_kind": "C30_LEDGER_CACHE_HIT_RECORDED_AT_NOT_ORIGINAL_RETRIEVAL_NOT_HISTORICAL",
            "observation": "a current venue list without season parameters; later-observed reference geography"},
    },
    "expected": {"contests": 788, "team_views": 1576, "witnesses": 11823, "strata_rows": 70,
                 "target_keys_sha256": "1c3ee9a03235c5e6c254b96593a8a4665b338bf74a2a78c856bd9480146928a5"},
}

#: The canonical context this checkout pins (identities and counts only; the values stay in the private data root),
#: packaged with artifacts/data_lake/national_game_context_2023_gate.json. The identities are deterministic and were
#: first produced by a scratch build of this contract; the create-only canonical build must reproduce exactly them (the
#: mounted genuine test skips while the canonical release or the data root is absent).
CONTEXT_PROFILE: dict[str, Any] | None = {
    "database_identity": "1abf6ea5aa5c2fe02015664f6aaa5af1eff867e53835d9a1e875f98294065243",
    "content_identity": "c940707acc3a97b9c7908c93d80c13a3f83252d63c6a23d82c6ce466c049284c",
    "database_sha256": "10d10f5700987b3ef87b87b1ebad856815b856f3e8044a1f66cad725f4b7a690",
    "contract_sha256": "91f1f4e0b3a62ff3f76cd4167f42175f5b0bb9548fa2311df7ca592252c204b7",
    "contests": 788,
    "team_views": 1576,
    "witnesses": 11823,
    "strata_rows": 70,
}

GRAINS = {"contest-context": "contests", "team-context": "teams", "context-witness": "witnesses",
          "context-score-summary": "strata"}
CONTEST_KEY_RE = re.compile(r"ncaa:[0-9]{1,12}\Z")
TEAM_KEY_RE = re.compile(r"org:[0-9]{1,12}\Z")
START_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z\Z")
ISO_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
MANIFEST_LOCATION_CODES = {readonly_sqlite.LOCATION_UNSUPPORTED: "CONTEXT_MANIFEST_LOCATION_UNSUPPORTED",
                           readonly_sqlite.LOCATION_NOT_LITERAL: "CONTEXT_MANIFEST_LOCATION_NOT_LITERAL"}
SUMMARY_SELECTION_RULE = ("SELECTED_TARGET_GAMES: the accepted 2023 targets whose contest key equals --contest and/or "
                          "with --team as either participant; every family and stratum re-derived over exactly those "
                          "games' frozen A-oriented scores, each game once; a stratum without a selected game has no "
                          "row")


class ContextError(ValueError):
    """A refused build input or a refused context release; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise ContextError(code, message)


#: Natural grains, record keys, ordering, payloads, database layout and the exact identity documents.
LAYOUT = {
    "grains": {"contests": "one record per accepted 2023 target (contest_key)",
               "teams": "two oriented records per target (contest_key|view, views A then B)",
               "witnesses": "fixed multiplicity per target: ACCEPTED_HISTORY_TARGET, ACCEPTED_PARENT_CONTEST, "
                            "PROVIDER_GAME, VENUE_REFERENCE; per view A then B: ACCEPTED_HISTORY_VIEW, "
                            "IDENTITY_BINDING, PROVIDER_TEAM_LOCATION; per model: FROZEN_REFERENCE_SCORE; then one "
                            "SOURCE_RECEIPT per pinned source clock (witness_key)",
               "strata": "one record per family, stratum and model in the declared order (family|stratum|model_id)",
               "census": "one record"},
    "ordering": "the accepted history's target order (its targets.ord) for every per-target table; input order never "
                "matters",
    "witness_key": "<contest_key or SOURCE>|<view or ->|<source>[|<model_id or clock name>]",
    "witness_supports": {k: list(v) for k, v in WITNESS_SUPPORTS.items()},
    "payloads": ["contests.jsonl.gz", "teams.jsonl.gz", "witnesses.jsonl.gz", "strata.jsonl.gz", "census.json"],
    "serialization": "canonical JSON lines (sorted keys, separators ',' ':', UTF-8, no ASCII escaping); gzip level 6 "
                     "mtime 0; one zlib level-9 block per table in the database",
    "database": {"ddl": [list(d) for d in (
        ("table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"),
        ("table", "blocks", "CREATE TABLE blocks (ord INTEGER PRIMARY KEY, record_table TEXT NOT NULL, "
                            "segment TEXT NOT NULL, records INTEGER NOT NULL, first_key TEXT, last_key TEXT, "
                            "lines_sha256 TEXT NOT NULL, block BLOB NOT NULL)"))],
                 "block_layout": [["contests", str(SEASON)], ["teams", str(SEASON)], ["witnesses", str(SEASON)],
                                  ["strata", "GLOBAL"], ["census", "GLOBAL"]],
                 "page_size": 4096, "journal_mode": "OFF", "file": DB_FILE},
    "identity_documents": {
        "content": ["schema", "stage", "population", "contract_id", "contract_sha256", "inputs", "source_clocks",
                    "rules_sha256", "payload_schema", "outputs", "uncompressed_sha256", "row_counts"],
        "database": ["schema", "stage", "population", "contract_sha256", "content_identity", "db_schema_version",
                     "outputs", "table_counts"],
        "identity": "SHA-256 of the canonical JSON bytes of the document; compared as canonical bytes, never by "
                    "Python equality (13.0, booleans and extra members differ)",
        "location": "<root>/canonical/national_game_context_2023/sha256/<identity>/; manifest at "
                    "<root>/manifests/national_game_context_2023/sha256/<identity>/run_manifest.json; create-only "
                    "(identical rebuild ALREADY_PRESENT_IDENTICAL, differing bytes REFUSED_IMMUTABLE_COLLISION)"},
}


def rules_document() -> dict[str, Any]:
    """Every frozen rule the contract restates (the meta ``rules`` claim and the content document's rules digest)."""
    return {"labels": LABELS, "layout": LAYOUT, "models": MODELS, "binding": BINDING, "provider_join": PROVIDER_JOIN,
            "date_window": DATE_WINDOW, "coordinates": COORDINATES, "distance": DISTANCE, "calendar": CALENDAR,
            "site_classes": SITE_CLASSES, "strata": STRATA, "sources": list(SOURCES),
            "game_witness_keys": list(GAME_WITNESS_KEYS), "score_witness_keys": list(SCORE_WITNESS_KEYS),
            "parent_columns": list(PARENT_COLUMNS),
            "record_fields": {k: list(v) for k, v in RECORD_FIELDS.items()},
            "strata_fields": {"common": list(STRATA_COMMON_FIELDS),
                              **{k: list(v) for k, v in STRATA_METRIC_FIELDS.items()}},
            "selectors": SELECTORS, "scope": SCOPE}


def rules_sha256() -> str:
    return sha256_bytes(canonical_json_bytes(rules_document()))


def target_keys_sha256(keys: Iterable[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


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
        raise ContextError(f"{code_prefix}_LOCATION_{suffix}", exc.detail) from exc


def resolve_inputs(data_root: Path, anchors: dict[str, Any]) -> dict[str, Path]:
    """Each pinned input under the explicitly named data root, refused unless present with its pinned SHA-256. The root
    and every resolved location pass the BAT-717 literal local-file policy before any filesystem access."""
    root = Path(_literal(Path(data_root), "CONTEXT_DATA_ROOT"))
    if not _io_path(root).is_dir():
        _refuse("CONTEXT_DATA_ROOT_MISSING", f"no data root directory at {data_root}")
    paths: dict[str, Path] = {}
    for name in INPUT_NAMES:
        spec = anchors["inputs"][name]
        location = Path(_literal(root / Path(*spec["relative_path"].split("/")), "CONTEXT_INPUT"))
        if not _io_path(location).is_file():
            _refuse("CONTEXT_INPUT_MISSING", f"{name}: no file at {location}")
        actual = sha256_file(_io_path(location))
        if actual != spec["sha256"]:
            _refuse("CONTEXT_INPUT_TAMPERED", f"{name}: bytes hash to {actual}, the contract pins {spec['sha256']}")
        paths[name] = location
    return paths


def _connect(path: Path) -> sqlite3.Connection:
    try:
        return readonly_sqlite.connect_readonly(path, immutable=True)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise ContextError("CONTEXT_INPUT_LOCATION_" + ("UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED
                                                        else "NOT_LITERAL"), exc.detail) from exc


def _json_file(path: Path) -> Any:
    try:
        return json.loads(_io_path(path).read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContextError("CONTEXT_INPUT_MALFORMED", f"{path}: {exc}") from exc


def load_inputs(data_root: Path, anchors: dict[str, Any], *, input_order: str = "natural") -> dict[str, Any]:
    """Every pinned input, verified and parsed; ``input_order`` permutes every loaded collection before derivation (the
    derivation indexes by key and orders canonically, so no variant may change a byte)."""
    paths = resolve_inputs(data_root, anchors)
    specs = anchors["inputs"]
    try:
        conn = _connect(paths["history"])
        try:
            meta = dict(conn.execute("SELECT key, value FROM meta"))
            targets = [(int(r[0]), json.loads(r[1])) for r in conn.execute(
                "SELECT ord, record FROM targets WHERE season = ? ORDER BY ord", (SEASON,))]
            views = [(int(r[0]), json.loads(r[1])) for r in conn.execute(
                "SELECT ord, record FROM history WHERE season = ? ORDER BY ord", (SEASON,))]
        finally:
            conn.close()
        if (meta.get("content_identity"), meta.get("contract_sha256"), meta.get("prior_rule")) != \
                (specs["history"]["content_identity"], specs["history"]["contract_sha256"], PRIOR_RULE):
            _refuse("CONTEXT_INPUT_MALFORMED", "the history meta names another content, contract or prior rule")
        conn = _connect(paths["population"])
        try:
            parent = [dict(zip(PARENT_COLUMNS, r)) for r in conn.execute(
                f"SELECT {', '.join(PARENT_COLUMNS)} FROM contest WHERE season = ?", (SEASON,))]
        finally:
            conn.close()
        lines = gzip.decompress(_io_path(paths["identity_bindings"]).read_bytes()).decode("utf-8").split("\n")
        header = json.loads(lines[0])
        if not isinstance(header, dict) or (header.get("_header") or {}).get("contract_sha256") != \
                specs["identity_bindings"]["header_contract_sha256"]:
            _refuse("CONTEXT_INPUT_MALFORMED", "the identity bindings header names another population contract")
        bindings = [(number, json.loads(line)) for number, line in enumerate(lines[1:], start=2) if line]
        conn = _connect(paths["reference"])
        try:
            rmeta = dict(conn.execute("SELECT key, value FROM meta"))
            blocks = conn.execute("SELECT records, first_key, last_key, lines_sha256, block FROM blocks WHERE "
                                  "record_table = 'scores' AND segment = ?", (str(SEASON),)).fetchall()
        finally:
            conn.close()
    except (sqlite3.DatabaseError, OSError, UnicodeDecodeError, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, ContextError):
            raise
        raise ContextError("CONTEXT_INPUT_MALFORMED", f"{type(exc).__name__}: {exc}") from exc
    if (rmeta.get("content_identity"), rmeta.get("contract_sha256")) != \
            (specs["reference"]["content_identity"], specs["reference"]["contract_sha256"]):
        _refuse("CONTEXT_INPUT_MALFORMED", "the reference meta names another content or contract")
    if len(blocks) != 1:
        _refuse("CONTEXT_REFERENCE_MALFORMED", f"{len(blocks)} reference score blocks for {SEASON}")
    records, first_key, last_key, lines_sha, blob = blocks[0]
    try:
        data = zlib.decompress(blob)
        score_lines = data.decode("utf-8").split("\n")
    except (zlib.error, TypeError, UnicodeDecodeError) as exc:
        raise ContextError("CONTEXT_REFERENCE_MALFORMED", f"score block does not decompress: {exc}") from exc
    if score_lines[-1] != "" or sha256_bytes(data) != lines_sha or records != len(score_lines) - 1:
        _refuse("CONTEXT_REFERENCE_MALFORMED", "the reference score block index differs from its content")
    try:
        scores = [(line, json.loads(line)) for line in score_lines[:-1]]
    except ValueError as exc:
        raise ContextError("CONTEXT_REFERENCE_MALFORMED", str(exc)) from exc
    games, teams, venues = (_json_file(paths[n]) for n in ("provider_games", "provider_teams", "venue_reference"))
    for name, value in (("provider_games", games), ("provider_teams", teams), ("venue_reference", venues)):
        if not isinstance(value, list) or not all(isinstance(r, dict) for r in value):
            _refuse("CONTEXT_INPUT_MALFORMED", f"{name} is not a list of objects")
    order = input_order
    return {"paths": paths, "history_meta": meta, "targets": _ordered(targets, order), "views": _ordered(views, order),
            "parent": _ordered(parent, order), "bindings": _ordered(bindings, order),
            "games": _ordered(list(enumerate(games)), order), "teams": _ordered(list(enumerate(teams)), order),
            "venues": _ordered(list(enumerate(venues)), order), "scores": _ordered(scores, order),
            "score_block": {"records": records, "first_key": first_key, "last_key": last_key,
                            "lines_sha256": lines_sha}}


# --------------------------------------------------------------------------------------------- derivation helpers

def _coordinate(value: Any, bound: float) -> float | int | None:
    """A qualified coordinate: a JSON integer or binary64 number (never a boolean or string), finite, within +/-bound."""
    if type(value) not in (int, float):
        return None
    if not math.isfinite(value) or not -bound <= value <= bound:
        return None
    return value


def reference_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """The declared spherical great-circle reference distance in metres, rounded half-even to an integer metre."""
    value = haversine_km(lat1, lon1, lat2, lon2) * 1000.0
    return int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def parse_start(text: Any) -> dt.datetime | None:
    if not isinstance(text, str) or not START_RE.match(text):
        return None
    try:
        return dt.datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError:
        return None


def date_state(start: Any, parent_date: str) -> tuple[str, str | None, int | None]:
    """(state, reason, UTC date minus parent date in days) under the declared local-date compatibility window."""
    instant = parse_start(start)
    if instant is None:
        return "UNSUPPORTED", "PROVIDER_START_MALFORMED", None
    day = dt.date.fromisoformat(parent_date)
    base = dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc)
    lower = base + dt.timedelta(hours=DATE_WINDOW["lower_offset_hours"])
    upper = base + dt.timedelta(hours=DATE_WINDOW["upper_offset_hours"])
    offset = (instant.date() - day).days
    if lower <= instant < upper:
        return "COMPATIBLE_WITH_PARENT_LOCAL_DATE", None, offset
    return "INCOMPATIBLE_WITH_PARENT_LOCAL_DATE", "PROVIDER_START_OUTSIDE_PARENT_DATE_WINDOW", offset


def calendar_bin(days: int) -> str:
    for name, low, high in CALENDAR_BINS:
        if days >= low and (high is None or days <= high):
            return name
    _refuse("CONTEXT_CALENDAR_INVALID", f"interval {days} outside every bin")
    return ""


def distance_bin(metres: int) -> str:
    for name, low, high in DISTANCE_BINS:
        if metres >= low and (high is None or metres <= high):
            return name
    _refuse("CONTEXT_DISTANCE_INVALID", f"distance {metres} outside every bin")
    return ""


def _valid_date(text: Any) -> bool:
    if not isinstance(text, str) or not ISO_DATE_RE.match(text):
        return False
    try:
        return dt.date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


def _index(items: list[tuple[Any, dict[str, Any]]], key: Any) -> dict[Any, list[tuple[Any, dict[str, Any]]]]:
    out: dict[Any, list[tuple[Any, dict[str, Any]]]] = {}
    for position, row in items:
        k = key(row)
        if k is not None:
            out.setdefault(k, []).append((position, row))
    for value in out.values():
        value.sort(key=lambda pr: pr[0])
    return out


def _provider_id(row: dict[str, Any], name: str = "id") -> str | None:
    value = row.get(name)
    return str(value) if is_int(value) else None


def _counts(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = row.get(field)
        key = "null" if value is None else str(value)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


# --------------------------------------------------------------------------------------------- per-target derivation

def _binding(org_id: Any, index: dict[Any, list[tuple[Any, dict[str, Any]]]]) -> dict[str, Any]:
    found = index.get(org_id, []) if isinstance(org_id, str) else []
    if not found:
        return {"state": "UNSUPPORTED", "reason": "NO_ACCEPTED_PARTICIPANT_BINDING", "line": None, "row": None,
                "cfbd": None, "rule": None}
    line, row = found[0]
    if len(found) > 1:
        return {"state": "UNSUPPORTED", "reason": "BINDING_DUPLICATED", "line": line, "row": row, "cfbd": None,
                "rule": None}
    cfbd, rule = row.get("cfbd_team_id"), row.get("rule")
    if not (isinstance(cfbd, str) and cfbd.isdigit()) or rule not in ACCEPTED_BINDING_RULES:
        return {"state": "UNSUPPORTED", "reason": "BINDING_NOT_CONFIRMED", "line": line, "row": row, "cfbd": None,
                "rule": rule if isinstance(rule, str) else None}
    return {"state": "BOUND", "reason": None, "line": line, "row": row, "cfbd": cfbd, "rule": rule}


def _game_shape_ok(row: dict[str, Any]) -> bool:
    return (all(is_int(row.get(k)) for k in ("id", "season", "homeId", "awayId")) and
            isinstance(row.get("neutralSite"), bool) and isinstance(row.get("startTimeTBD"), bool) and
            isinstance(row.get("startDate"), str))


def _provider(target: dict[str, Any], sides: dict[str, dict[str, Any]],
              games: dict[Any, list[tuple[Any, dict[str, Any]]]]) -> dict[str, Any]:
    ids = target.get("cfbd_game_ids")
    out: dict[str, Any] = {"documented": ids if isinstance(ids, list) else None, "game_id": None, "position": None,
                           "row": None, "state": "UNSUPPORTED", "reason": None, "home_side": None}
    if not isinstance(ids, list) or not all(isinstance(x, str) and x.isdigit() for x in ids):
        out["reason"] = "DOCUMENTED_GAME_IDS_MALFORMED"
        return out
    if not ids:
        out["reason"] = "NO_DOCUMENTED_PROVIDER_GAME"
        return out
    if len(ids) > 1:
        out["reason"] = "MULTIPLE_DOCUMENTED_PROVIDER_GAMES"
        return out
    out["game_id"] = ids[0]
    found = games.get(ids[0], [])
    if not found:
        out["reason"] = "PROVIDER_GAME_ABSENT_FROM_CAPTURE"
        return out
    out["position"], out["row"] = found[0]
    row = out["row"]
    if len(found) > 1:
        out["reason"] = "PROVIDER_GAME_ID_DUPLICATED"
        return out
    if not _game_shape_ok(row):
        out["reason"] = "PROVIDER_FIELD_MALFORMED"
        return out
    if row["season"] != SEASON:
        out["reason"] = "PROVIDER_SEASON_DIFFERS"
        return out
    if any(sides[v]["state"] != "BOUND" for v in VIEWS) or sides["A"]["cfbd"] == sides["B"]["cfbd"]:
        out["reason"] = "PARTICIPANT_BINDING_UNSUPPORTED"
        return out
    if {str(row["homeId"]), str(row["awayId"])} != {sides["A"]["cfbd"], sides["B"]["cfbd"]}:
        out["reason"] = "PROVIDER_PARTICIPANTS_DIFFER"
        return out
    out.update(state="JOINED", home_side="A" if str(row["homeId"]) == sides["A"]["cfbd"] else "B")
    return out


def _venue(provider: dict[str, Any], date: str, venues: dict[Any, list[tuple[Any, dict[str, Any]]]]
           ) -> dict[str, Any]:
    row = provider["row"]
    out: dict[str, Any] = {"venue_id": None, "position": None, "row": None, "state": "UNSUPPORTED", "reason": None,
                           "lat": None, "lon": None}
    if provider["state"] != "JOINED":
        out["reason"] = "PROVIDER_JOIN_UNSUPPORTED"
        return out
    vid = row.get("venueId")
    if vid is None:
        out["reason"] = "PROVIDER_VENUE_ID_ABSENT"
        return out
    if not is_int(vid):
        out["reason"] = "PROVIDER_VENUE_ID_MALFORMED"
        return out
    out["venue_id"] = vid
    found = venues.get(vid, [])
    if not found:
        out["reason"] = "VENUE_REFERENCE_ROW_ABSENT"
        return out
    out["position"], out["row"] = found[0]
    if len(found) > 1:
        out["reason"] = "VENUE_REFERENCE_ROW_DUPLICATED"
        return out
    if date != "COMPATIBLE_WITH_PARENT_LOCAL_DATE":
        out["reason"] = "PROVIDER_DATE_INCOMPATIBLE"
        return out
    lat, lon = _coordinate(out["row"].get("latitude"), 90), _coordinate(out["row"].get("longitude"), 180)
    if lat is None or lon is None:
        out["reason"] = "VENUE_COORDINATE_INVALID"
        return out
    out.update(state="QUALIFIED_REFERENCE_COORDINATE", lat=lat, lon=lon)
    return out


def _origin(side: dict[str, Any], teams: dict[Any, list[tuple[Any, dict[str, Any]]]]) -> dict[str, Any]:
    out: dict[str, Any] = {"position": None, "row": None, "state": "UNSUPPORTED", "reason": None, "lat": None,
                           "lon": None, "location_id": None, "location_name": None}
    if side["state"] != "BOUND":
        out["reason"] = "PARTICIPANT_BINDING_UNSUPPORTED"
        return out
    found = teams.get(side["cfbd"], [])
    if not found:
        out["reason"] = "PROVIDER_TEAM_ROW_ABSENT"
        return out
    out["position"], out["row"] = found[0]
    if len(found) > 1:
        out["reason"] = "PROVIDER_TEAM_ROW_DUPLICATED"
        return out
    location = out["row"].get("location")
    if not isinstance(location, dict):
        out["reason"] = "ORIGIN_LOCATION_ABSENT"
        return out
    out["location_id"] = location.get("id") if is_int(location.get("id")) else None
    out["location_name"] = location.get("name") if isinstance(location.get("name"), str) else None
    lat, lon = _coordinate(location.get("latitude"), 90), _coordinate(location.get("longitude"), 180)
    if lat is None or lon is None:
        out["reason"] = "ORIGIN_COORDINATE_INVALID"
        return out
    out.update(state="QUALIFIED_REFERENCE_ORIGIN", lat=lat, lon=lon)
    return out


def _calendar(view: dict[str, Any], target: dict[str, Any], parent: dict[str, dict[str, Any]],
              by_team: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """The team's accepted eligible same-season prior pool, re-verified against the parent rows (each prior's season,
    date, participant and the contributing/excluded partition of the team's earlier parent contests)."""
    history = view.get("team_history")
    if not isinstance(history, dict) or not isinstance(history.get("contributing"), list) or \
            not isinstance(history.get("excluded_inputs"), list):
        _refuse("CONTEXT_INPUT_MALFORMED", f"{target['contest_key']}/{view.get('view')}: no history pool")
    team, date = view["team_key"], target["contest_date"]
    contributing, excluded = history["contributing"], history["excluded_inputs"]
    for item in contributing + excluded:
        if not isinstance(item, dict) or not isinstance(item.get("contest_key"), str) or \
                not _valid_date(item.get("contest_date")):
            _refuse("CONTEXT_INPUT_MALFORMED", f"{target['contest_key']}/{view.get('view')}: malformed prior item")
        row = parent.get(item["contest_key"])
        if row is None or row["season"] != SEASON or row["contest_date"] != item["contest_date"] or \
                not item["contest_date"] < date or team not in (row["a_key"], row["b_key"]):
            _refuse("CONTEXT_HISTORY_LINEAGE_MISMATCH", f"{target['contest_key']}/{view.get('view')}: prior "
                                                        f"{item['contest_key']} is not an earlier parent contest of "
                                                        f"{team}")
    contributing_keys = [c["contest_key"] for c in contributing]
    excluded_keys = [e["contest_key"] for e in excluded]
    earlier = {r["contest_key"] for r in by_team.get(team, []) if isinstance(r["contest_date"], str) and
               r["contest_date"] < date}
    if len(set(contributing_keys)) != len(contributing_keys) or set(contributing_keys) & set(excluded_keys) or \
            set(contributing_keys) | set(excluded_keys) != earlier:
        _refuse("CONTEXT_HISTORY_LINEAGE_MISMATCH", f"{target['contest_key']}/{view.get('view')}: the accepted pool "
                                                    "does not partition the team's earlier parent contests")
    not_earlier = sum(1 for r in by_team.get(team, []) if r["contest_key"] != target["contest_key"] and
                      not (isinstance(r["contest_date"], str) and r["contest_date"] < date))
    reasons: dict[str, int] = {}
    for item in excluded:
        for reason in item.get("reasons") or []:
            reasons[str(reason)] = reasons.get(str(reason), 0) + 1
    out: dict[str, Any] = {"eligible_prior_count": len(contributing), "excluded_prior_count": len(excluded),
                           "excluded_prior_reasons": dict(sorted(reasons.items())),
                           "excluded_prior_contest_keys": sorted(excluded_keys),
                           "not_strictly_earlier_contests": not_earlier, "latest_prior_date": None,
                           "latest_prior_contest_keys": [], "calendar_interval_days": None,
                           "intervening_calendar_days": None}
    if not contributing:
        out["calendar_state"] = "NO_ELIGIBLE_SAME_SEASON_PRIOR"
        return out
    latest = max(c["contest_date"] for c in contributing)
    at_latest = sorted(c["contest_key"] for c in contributing if c["contest_date"] == latest)
    out.update(latest_prior_date=latest, latest_prior_contest_keys=at_latest)
    if len(at_latest) > 1:
        out["calendar_state"] = "AMBIGUOUS_LATEST_PRIOR"
        return out
    days = (dt.date.fromisoformat(date) - dt.date.fromisoformat(latest)).days
    out.update(calendar_state="QUALIFIED_CALENDAR_INTERVAL", calendar_interval_days=days,
               intervening_calendar_days=days - 1)
    return out


def _witness(key: str, subject: str, source: str, *, contest_key: str | None, view: str | None, team_key: str | None,
             model_id: str | None, locator: dict[str, Any], supports: list[str], raw: Any, raw_sha256: str | None,
             state: str, reason: str | None) -> dict[str, Any]:
    return {"record_type": "game_context_witness", "witness_key": key, "subject_kind": subject,
            "contest_key": contest_key, "view": view, "team_key": team_key, "model_id": model_id, "source": source,
            "locator": locator, "supports": supports, "raw": raw, "raw_sha256": raw_sha256, "state": state,
            "reason": reason, **RECORD_LABELS}


def witness_key(contest_key: str | None, view: str | None, source: str, model_id: str | None = None) -> str:
    base = f"{contest_key or 'SOURCE'}|{view or '-'}|{source}"
    return f"{base}|{model_id}" if model_id else base


def _parent_role(parent_site: str, view: str) -> str:
    if parent_site == "NEUTRAL":
        return "NEUTRAL"
    if parent_site in ("HOME_A", "HOME_B"):
        return "HOME" if parent_site == f"HOME_{view}" else "AWAY"
    return "UNSUPPORTED"


def _check_parent(target: dict[str, Any], row: dict[str, Any] | None) -> None:
    if row is None:
        _refuse("CONTEXT_PARENT_MISMATCH", f"{target.get('contest_key')}: no parent contest row")
    try:
        documented = json.loads(row["cfbd_game_ids"]) if isinstance(row["cfbd_game_ids"], str) else None
    except ValueError:
        documented = None
    pairs = (("contest_date", "contest_date"), ("parent_site", "site"), ("a_key", "a_key"), ("b_key", "b_key"),
             ("a_org_id", "a_org_id"), ("b_org_id", "b_org_id"), ("neutral_site_text", "neutral_site_text"),
             ("season", "season"))
    differing = [mine for mine, theirs in pairs if target.get(mine) != row.get(theirs)]
    if documented != target.get("cfbd_game_ids"):
        differing.append("cfbd_game_ids")
    if differing:
        _refuse("CONTEXT_PARENT_MISMATCH", f"{target.get('contest_key')}: the history target differs from the parent "
                                           f"on {differing}")


def _derive_target(ord_: int, target: dict[str, Any], views: dict[str, tuple[int, dict[str, Any]]],
                   ctx: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    anchors, specs = ctx["anchors"], ctx["anchors"]["inputs"]
    clocks = anchors["source_clocks"]
    key = target["contest_key"]
    _check_parent(target, ctx["parent"].get(key))
    sides = {v: _binding(target.get(f"{v.lower()}_org_id"), ctx["bindings"]) for v in VIEWS}
    provider = _provider(target, sides, ctx["games"])
    row = provider["row"] if provider["state"] == "JOINED" else None
    if row is not None:
        d_state, d_reason, offset = date_state(row["startDate"], target["contest_date"])
        claim = "NEUTRAL" if row["neutralSite"] else f"HOME_{provider['home_side']}"
        agreement = "AGREE" if claim == target["parent_site"] else "DISAGREE"
    else:
        d_state, d_reason, offset, claim, agreement = "UNSUPPORTED", provider["reason"], None, None, "UNSUPPORTED"
    venue = _venue(provider, d_state, ctx["venues"])
    origins = {v: _origin(sides[v], ctx["teams"]) for v in VIEWS}
    calendars = {v: _calendar(views[v][1], target, ctx["parent"], ctx["by_team"]) for v in VIEWS}
    distances: dict[str, dict[str, Any]] = {}
    for v in VIEWS:
        o = origins[v]
        if venue["state"] == "QUALIFIED_REFERENCE_COORDINATE" and o["state"] == "QUALIFIED_REFERENCE_ORIGIN":
            distances[v] = {"m": reference_distance_m(o["lat"], o["lon"], venue["lat"], venue["lon"]),
                            "state": "QUALIFIED_REFERENCE_DISTANCE", "reason": None}
        else:
            reason = ("VENUE_AND_ORIGIN_UNSUPPORTED" if venue["state"] != "QUALIFIED_REFERENCE_COORDINATE" and
                      o["state"] != "QUALIFIED_REFERENCE_ORIGIN" else "VENUE_UNSUPPORTED"
                      if venue["state"] != "QUALIFIED_REFERENCE_COORDINATE" else "ORIGIN_UNSUPPORTED")
            distances[v] = {"m": None, "state": "UNSUPPORTED", "reason": reason}
    site_class = SITE_CLASSES.get(target.get("parent_site"), "UNSUPPORTED")
    cal_states = [calendars[v]["calendar_state"] for v in VIEWS]
    if all(s == "QUALIFIED_CALENDAR_INTERVAL" for s in cal_states):
        min_days = min(calendars[v]["calendar_interval_days"] for v in VIEWS)
        min_state, min_stratum = "QUALIFIED", calendar_bin(min_days)
    elif "AMBIGUOUS_LATEST_PRIOR" in cal_states:
        min_days, min_state, min_stratum = None, "UNSUPPORTED", "UNSUPPORTED"
    else:
        min_days, min_state, min_stratum = None, "NO_PRIOR", "NO_PRIOR"
    if all(distances[v]["state"] == "QUALIFIED_REFERENCE_DISTANCE" for v in VIEWS):
        max_m = max(distances[v]["m"] for v in VIEWS)
        max_state, max_stratum = "QUALIFIED", distance_bin(max_m)
    else:
        max_m, max_state, max_stratum = None, "UNSUPPORTED", "UNSUPPORTED"

    # ---- witnesses (fixed order and multiplicity: 4 contest, 3 per view, 1 per model)
    parent_row = ctx["parent"][key]
    w: list[dict[str, Any]] = []
    w.append(_witness(witness_key(key, None, "ACCEPTED_HISTORY_TARGET"), "CONTEST", "ACCEPTED_HISTORY_TARGET",
                      contest_key=key, view=None, team_key=None, model_id=None,
                      locator={"input": "history", "sha256": specs["history"]["sha256"], "table": "targets",
                               "ord": ord_, "key": key},
                      supports=list(WITNESS_SUPPORTS["ACCEPTED_HISTORY_TARGET"]),
                      raw=target, raw_sha256=sha256_bytes(canonical_json_bytes(target)), state="ACCEPTED_TARGET",
                      reason=None))
    w.append(_witness(witness_key(key, None, "ACCEPTED_PARENT_CONTEST"), "CONTEST", "ACCEPTED_PARENT_CONTEST",
                      contest_key=key, view=None, team_key=None, model_id=None,
                      locator={"input": "population", "sha256": specs["population"]["sha256"], "table": "contest",
                               "key": key},
                      supports=list(WITNESS_SUPPORTS["ACCEPTED_PARENT_CONTEST"]),
                      raw=parent_row, raw_sha256=sha256_bytes(canonical_json_bytes(parent_row)),
                      state="PARENT_AGREES_WITH_HISTORY_TARGET", reason=None))
    game_row = provider["row"]
    w.append(_witness(witness_key(key, None, "PROVIDER_GAME"), "CONTEST", "PROVIDER_GAME", contest_key=key, view=None,
                      team_key=None, model_id=None,
                      locator={"input": "provider_games", "sha256": specs["provider_games"]["sha256"],
                               "json_pointer": None if provider["position"] is None else f"/{provider['position']}",
                               "key": provider["game_id"]},
                      supports=list(WITNESS_SUPPORTS["PROVIDER_GAME"]),
                      raw=None if game_row is None else {k: game_row.get(k) for k in GAME_WITNESS_KEYS if k in game_row},
                      raw_sha256=None if game_row is None else sha256_bytes(canonical_json_bytes(game_row)),
                      state=provider["state"], reason=provider["reason"]))
    w.append(_witness(witness_key(key, None, "VENUE_REFERENCE"), "CONTEST", "VENUE_REFERENCE", contest_key=key,
                      view=None, team_key=None, model_id=None,
                      locator={"input": "venue_reference", "sha256": specs["venue_reference"]["sha256"],
                               "json_pointer": None if venue["position"] is None else f"/{venue['position']}",
                               "key": venue["venue_id"]},
                      supports=list(WITNESS_SUPPORTS["VENUE_REFERENCE"]),
                      raw=venue["row"], raw_sha256=None if venue["row"] is None else
                      sha256_bytes(canonical_json_bytes(venue["row"])),
                      state=venue["state"], reason=venue["reason"]))
    team_records: list[dict[str, Any]] = []
    view_witness_keys: dict[str, list[str]] = {}
    for v in VIEWS:
        vord, vrec = views[v]
        side, origin, cal, dist = sides[v], origins[v], calendars[v], distances[v]
        prefix = v.lower()
        other = "b" if v == "A" else "a"
        history = vrec["team_history"]
        keys_v = [witness_key(key, v, s) for s in VIEW_SOURCES]
        view_witness_keys[v] = keys_v
        w.append(_witness(keys_v[0], "TEAM_VIEW", "ACCEPTED_HISTORY_VIEW", contest_key=key, view=v,
                          team_key=target[f"{prefix}_key"], model_id=None,
                          locator={"input": "history", "sha256": specs["history"]["sha256"], "table": "history",
                                   "ord": vord, "key": f"{key}|{v}"},
                          supports=list(WITNESS_SUPPORTS["ACCEPTED_HISTORY_VIEW"]),
                          raw={"prior_rule": vrec.get("prior_rule"), "history_state": history.get("history_state"),
                               "contributing": history["contributing"], "excluded_inputs": history["excluded_inputs"]},
                          raw_sha256=sha256_bytes(canonical_json_bytes(vrec)), state=cal["calendar_state"],
                          reason=None))
        w.append(_witness(keys_v[1], "TEAM_VIEW", "IDENTITY_BINDING", contest_key=key, view=v,
                          team_key=target[f"{prefix}_key"], model_id=None,
                          locator={"input": "identity_bindings", "sha256": specs["identity_bindings"]["sha256"],
                                   "line": side["line"], "key": target.get(f"{prefix}_org_id")},
                          supports=list(WITNESS_SUPPORTS["IDENTITY_BINDING"]),
                          raw=side["row"], raw_sha256=None if side["row"] is None else
                          sha256_bytes(canonical_json_bytes(side["row"])),
                          state=side["state"], reason=side["reason"]))
        team_row = origin["row"]
        w.append(_witness(keys_v[2], "TEAM_VIEW", "PROVIDER_TEAM_LOCATION", contest_key=key, view=v,
                          team_key=target[f"{prefix}_key"], model_id=None,
                          locator={"input": "provider_teams", "sha256": specs["provider_teams"]["sha256"],
                                   "json_pointer": None if origin["position"] is None else
                                   f"/{origin['position']}/location", "key": side["cfbd"]},
                          supports=list(WITNESS_SUPPORTS["PROVIDER_TEAM_LOCATION"]),
                          raw=None if team_row is None else {"id": team_row.get("id"), "school": team_row.get("school"),
                                                             "location": team_row.get("location")},
                          raw_sha256=None if team_row is None else sha256_bytes(canonical_json_bytes(team_row)),
                          state=origin["state"], reason=origin["reason"]))
        provider_role = None if row is None else ("HOME_DESIGNATED" if provider["home_side"] == v else
                                                  "AWAY_DESIGNATED")
        provider_claim = None if row is None else ("NEUTRAL" if row["neutralSite"] else
                                                   "HOME" if provider["home_side"] == v else "AWAY")
        record = {
            "record_type": "game_context_team", "contest_key": key, "season": target["season"],
            "contest_date": target["contest_date"], "view": v, "team_key": target[f"{prefix}_key"],
            "team_org_id": target[f"{prefix}_org_id"], "team_name": target[f"{prefix}_team_name"],
            "team_division_label": target[f"{prefix}_division_label"], "opponent_key": target[f"{other}_key"],
            "opponent_name": target[f"{other}_team_name"], "parent_site": target["parent_site"],
            "parent_role_for_team": _parent_role(target["parent_site"], v), "provider_role_for_team": provider_role,
            "provider_site_claim_for_team": provider_claim, "cfbd_team_id": side["cfbd"], "binding_rule": side["rule"],
            "binding_state": side["state"], "binding_reason": side["reason"], "prior_rule": PRIOR_RULE,
            **{k: cal[k] for k in ("eligible_prior_count", "excluded_prior_count", "excluded_prior_reasons",
                                   "excluded_prior_contest_keys", "not_strictly_earlier_contests",
                                   "latest_prior_date", "latest_prior_contest_keys", "calendar_interval_days",
                                   "intervening_calendar_days", "calendar_state")},
            "origin_location_id": origin["location_id"], "origin_location_name": origin["location_name"],
            "origin_latitude": origin["lat"], "origin_longitude": origin["lon"], "origin_state": origin["state"],
            "origin_reason": origin["reason"],
            "origin_observed_at_utc": clocks["provider_teams"]["retrieved_at_utc"] if team_row is not None else None,
            "origin_clock_kind": clocks["provider_teams"]["clock_kind"] if team_row is not None else None,
            "venue_id": venue["venue_id"], "venue_coordinate_state": venue["state"],
            "reference_distance_m": dist["m"], "distance_state": dist["state"], "distance_reason": dist["reason"],
            "distance_method": DISTANCE["method"],
            "origin_is_game_venue": (origin["location_id"] == venue["venue_id"]
                                     if origin["location_id"] is not None and venue["venue_id"] is not None else None),
            "witness_keys": keys_v + [witness_key(key, None, "PROVIDER_GAME"), witness_key(key, None,
                                                                                            "VENUE_REFERENCE")],
            **CONTEXT_LABELS}
        team_records.append(record)
    score_keys = []
    for model_id in MODEL_IDS:
        line, score = ctx["scores"][(key, model_id)]
        wk = witness_key(key, None, "FROZEN_REFERENCE_SCORE", model_id)
        score_keys.append(wk)
        w.append(_witness(wk, "CONTEST", "FROZEN_REFERENCE_SCORE", contest_key=key, view=None, team_key=None,
                          model_id=model_id,
                          locator={"input": "reference", "sha256": specs["reference"]["sha256"],
                                   "record_table": "scores", "segment": str(SEASON), "key": f"{key}|{model_id}"},
                          supports=list(WITNESS_SUPPORTS["FROZEN_REFERENCE_SCORE"]),
                          raw={k: score[k] for k in SCORE_WITNESS_KEYS if k in score},
                          raw_sha256=sha256_bytes(line.encode("utf-8")), state=score["score_state"],
                          reason=score.get("unscored_reason")))
    venue_row = venue["row"]
    contest = {
        "record_type": "game_context_contest", "contest_key": key, "ncaa_contest_id": target["ncaa_contest_id"],
        "season": target["season"], "term": target["term"], "contest_date": target["contest_date"],
        **{f"{p}_{f}": target[f"{p}_{f}"] for p in ("a", "b") for f in ("key", "org_id", "team_name",
                                                                       "division_label")},
        "classification_pair": target["classification_pair"], "parent_site": target["parent_site"],
        "parent_neutral_site_text": target.get("neutral_site_text"), "site_class": site_class,
        "provider_documented_game_ids": provider["documented"], "provider_game_id": provider["game_id"],
        "provider_join_state": provider["state"], "provider_join_reason": provider["reason"],
        "provider_home_side": provider["home_side"],
        "provider_neutral_site": None if row is None else row["neutralSite"], "provider_site_claim": claim,
        "site_agreement": agreement, "provider_start_claim_utc": None if row is None else row["startDate"],
        "provider_start_time_tbd": None if row is None else row["startTimeTBD"], "provider_date_state": d_state,
        "provider_utc_date_minus_parent_date_days": offset,
        "provider_season_type": None if row is None else row.get("seasonType"),
        "provider_week": None if row is None else row.get("week"),
        "provider_game_retrieved_at_utc": clocks["provider_games"]["retrieved_at_utc"] if game_row is not None else None,
        "venue_id": venue["venue_id"], "provider_venue_name": None if row is None else row.get("venue"),
        "venue_reference_name": None if venue_row is None else venue_row.get("name"),
        "venue_name_state": ("UNSUPPORTED" if venue_row is None or row is None else
                             "EQUAL" if venue_row.get("name") == row.get("venue") else "DIFFERS"),
        "venue_latitude": venue["lat"], "venue_longitude": venue["lon"], "venue_coordinate_state": venue["state"],
        "venue_coordinate_reason": venue["reason"],
        "venue_observed_at_utc": clocks["venue_reference"]["retrieved_at_utc"] if venue_row is not None else None,
        "venue_clock_kind": clocks["venue_reference"]["clock_kind"] if venue_row is not None else None,
        "min_calendar_interval_days": min_days, "min_calendar_state": min_state, "min_calendar_stratum": min_stratum,
        "max_reference_distance_m": max_m, "max_distance_state": max_state, "max_distance_stratum": max_stratum,
        "witness_keys": [witness_key(key, None, s) for s in CONTEST_SOURCES] + view_witness_keys["A"] +
                        view_witness_keys["B"] + score_keys,
        **CONTEXT_LABELS}
    return contest, team_records, w


# --------------------------------------------------------------------------------------------- strata and census

def _fraction(value: Any, what: str) -> Fraction:
    if isinstance(value, dict) and set(value) == {"numerator", "denominator"} and is_int(value["numerator"]) and \
            is_int(value["denominator"]) and value["denominator"] > 0:
        return Fraction(value["numerator"], value["denominator"])
    _refuse("CONTEXT_REFERENCE_MALFORMED", f"{what} is not an exact rational")
    return Fraction(0)


def _decimal_fraction(value: Any, what: str) -> Fraction:
    try:
        if isinstance(value, str):
            number = Decimal(value)
            if number.is_finite():
                return Fraction(number)
    except (InvalidOperation, ValueError):
        pass
    _refuse("CONTEXT_REFERENCE_MALFORMED", f"{what} is not a finite decimal string")
    return Fraction(0)


def _mean(total: Fraction, count: int) -> tuple[dict[str, int] | None, str | None]:
    if not count:
        return None, None
    value = total / count
    return rational(value), decimal_text(value)


def stratum_of(family: str, contest: dict[str, Any]) -> str:
    if family == "ALL":
        return "ALL"
    if family == "SITE":
        return contest["site_class"]
    if family == "MIN_CALENDAR":
        return contest["min_calendar_stratum"]
    return contest["max_distance_stratum"]


def strata_rows(contests: list[dict[str, Any]], scores: dict[tuple[str, str], tuple[str, dict[str, Any]]],
                selected: set[str] | None = None) -> list[dict[str, Any]]:
    """Every family, stratum and model in the frozen order over the given games' single A-oriented frozen scores; a
    selection keeps only strata holding a selected game."""
    chosen = contests if selected is None else [c for c in contests if c["contest_key"] in selected]
    rows: list[dict[str, Any]] = []
    for family, strata in FAMILIES.items():
        for stratum in strata:
            members = [c for c in chosen if stratum_of(family, c) == stratum]
            if selected is not None and not members:
                continue
            for model_id in MODEL_IDS:
                model = MODELS[model_id]
                pairs = [scores[(c["contest_key"], model_id)] for c in members]
                scored = [r for _l, r in pairs if r.get("score_state") == "SCORED"]
                unscored: dict[str, int] = {}
                for _l, r in pairs:
                    if r.get("score_state") != "SCORED":
                        reason = str(r.get("unscored_reason"))
                        unscored[reason] = unscored.get(reason, 0) + 1
                samples: dict[str, int] = {}
                for r in scored:
                    samples[str(r.get("sample_state"))] = samples.get(str(r.get("sample_state")), 0) + 1
                row: dict[str, Any] = {
                    "record_type": "game_context_score_stratum", "family": family, "stratum": stratum,
                    "model_id": model_id, "model_sha256": model["model_sha256"], "metric_kind": model["metric_kind"],
                    "output_kind": model["output_kind"], "games": len(members), "score_records": len(pairs),
                    "scored_games": len(scored), "unscored_games": len(pairs) - len(scored),
                    "unscored_by_reason": dict(sorted(unscored.items())),
                    "scored_by_sample_state": dict(sorted(samples.items())),
                    "member_contest_keys_sha256": sha256_bytes("\n".join(c["contest_key"] for c in members)
                                                               .encode("utf-8")),
                    "member_score_lines_sha256": sha256_bytes("\n".join(line for line, _r in pairs).encode("utf-8")),
                    "reading": STRATA["reading"], **STRATA_LABELS}
                if model["metric_kind"] == "PROBABILITY":
                    brier = sum((_fraction(r.get("brier"), "brier") for r in scored), Fraction(0))
                    log = sum((_decimal_fraction(r.get("log_loss"), "log_loss") for r in scored), Fraction(0))
                    brier_mean, brier_mean_text = _mean(brier, len(scored))
                    log_mean, log_mean_text = _mean(log, len(scored))
                    conventions = sorted({str(r.get("log_loss_convention")) for r in scored})
                    row.update(brier_total=rational(brier), brier_total_decimal=decimal_text(brier),
                               brier_mean=brier_mean, brier_mean_decimal=brier_mean_text,
                               log_loss_total=rational(log), log_loss_total_decimal=decimal_text(log),
                               log_loss_mean=log_mean, log_loss_mean_decimal=log_mean_text,
                               log_loss_convention=conventions[0] if len(conventions) == 1 else None,
                               log_loss_basis="EXACT_SUM_OF_FROZEN_DECIMAL_STRINGS")
                else:
                    absolute = sum((_fraction(r.get("absolute_error"), "absolute_error") for r in scored), Fraction(0))
                    squared = sum((_fraction(r.get("squared_error"), "squared_error") for r in scored), Fraction(0))
                    mae, mae_text = _mean(absolute, len(scored))
                    mse, mse_text = _mean(squared, len(scored))
                    row.update(absolute_error_total=rational(absolute),
                               absolute_error_total_decimal=decimal_text(absolute), mae=mae, mae_decimal=mae_text,
                               squared_error_total=rational(squared), squared_error_total_decimal=decimal_text(squared),
                               mse=mse, mse_decimal=mse_text)
                rows.append(row)
    return rows


def census_record(contests: list[dict[str, Any]], teams: list[dict[str, Any]], witnesses: list[dict[str, Any]],
                  strata: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: dict[str, dict[str, int]] = {}
    for table, rows, fields in (("contests", contests, ("provider_join_reason", "venue_coordinate_reason")),
                                ("teams", teams, ("binding_reason", "origin_reason", "distance_reason"))):
        for field in fields:
            reasons[f"{table}.{field}"] = _counts(rows, field)
    distances = [t["reference_distance_m"] for t in teams if t["reference_distance_m"] is not None]
    intervals = [t["calendar_interval_days"] for t in teams if t["calendar_interval_days"] is not None]
    by_source: dict[str, dict[str, int]] = {}
    for s in SOURCES:
        by_source[s] = _counts([x for x in witnesses if x["source"] == s], "state")
    return {"record_type": "game_context_census", "season": SEASON, "contests": len(contests),
            "team_views": len(teams), "witnesses": len(witnesses), "strata_rows": len(strata),
            "contest_states": {f: _counts(contests, f) for f in (
                "parent_site", "site_class", "provider_join_state", "provider_date_state", "site_agreement",
                "venue_name_state", "venue_coordinate_state", "min_calendar_state", "min_calendar_stratum",
                "max_distance_state", "max_distance_stratum", "classification_pair")},
            "team_states": {f: _counts(teams, f) for f in (
                "binding_state", "binding_rule", "parent_role_for_team", "provider_role_for_team",
                "provider_site_claim_for_team", "calendar_state", "origin_state", "distance_state",
                "origin_is_game_venue", "team_division_label")},
            "witness_sources": _counts(witnesses, "source"), "witness_states": by_source,
            "unsupported_reasons": reasons,
            "distance_m": {"qualified": len(distances), "zero": sum(1 for d in distances if d == 0),
                           "min": min(distances) if distances else None,
                           "max": max(distances) if distances else None},
            "calendar_interval_days": {"qualified": len(intervals), "min": min(intervals) if intervals else None,
                                       "max": max(intervals) if intervals else None},
            **RECORD_LABELS}


def source_witnesses(anchors: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for name in CLOCK_SOURCES:
        clock = anchors["source_clocks"][name]
        out.append(_witness(witness_key(None, None, "SOURCE_RECEIPT", name), "SOURCE", "SOURCE_RECEIPT",
                            contest_key=None, view=None, team_key=None, model_id=None,
                            locator={"input": "source_clocks", "receipt_relative_path": clock["receipt_relative_path"],
                                     "receipt_sha256": clock["receipt_sha256"], "key": name},
                            supports=list(WITNESS_SUPPORTS[f"SOURCE_RECEIPT:{name}"]),
                            raw=clock, raw_sha256=sha256_bytes(canonical_json_bytes(clock)),
                            state="PINNED_SOURCE_CLOCK", reason=None))
    return out


def derive(inputs: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    """Every record of every table from the pinned inputs, in the contract order (input order never matters)."""
    targets = sorted(inputs["targets"], key=lambda pair: pair[0])
    keys = [t.get("contest_key") for _o, t in targets]
    if len(set(keys)) != len(keys) or not all(isinstance(k, str) for k in keys):
        _refuse("CONTEXT_INPUT_MALFORMED", "duplicate or non-string history target keys")
    views: dict[str, dict[str, tuple[int, dict[str, Any]]]] = {}
    for ord_, record in inputs["views"]:
        k, v = record.get("target_contest_key"), record.get("view")
        if v in views.get(k, {}):
            _refuse("CONTEXT_INPUT_MALFORMED", f"duplicate history view {k}/{v}")
        views.setdefault(k, {})[v] = (ord_, record)
    parent: dict[str, dict[str, Any]] = {}
    by_team: dict[str, list[dict[str, Any]]] = {}
    for row in inputs["parent"]:
        if row["contest_key"] in parent:
            _refuse("CONTEXT_INPUT_MALFORMED", f"duplicate parent contest {row['contest_key']}")
        parent[row["contest_key"]] = row
        for side in ("a_key", "b_key"):
            if isinstance(row[side], str):
                by_team.setdefault(row[side], []).append(row)
    scores: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
    for line, record in inputs["scores"]:
        pair = (record.get("contest_key"), record.get("model_id"))
        if pair in scores:
            _refuse("CONTEXT_REFERENCE_MALFORMED", f"duplicate reference score {pair}")
        model = MODELS.get(record.get("model_id"))
        if model is None or record.get("orientation") != "A" or record.get("season") != SEASON or \
                record.get("metric_kind") != model["metric_kind"] or record.get("model_sha256") != model["model_sha256"]:
            _refuse("CONTEXT_REFERENCE_MALFORMED", f"reference score {pair} is not a single A-oriented frozen "
                                                   f"{SEASON} score of a declared model")
        scores[pair] = (line, record)
    expected_pairs = {(k, m) for k in keys for m in MODEL_IDS}
    if set(scores) != expected_pairs:
        _refuse("CONTEXT_REFERENCE_KEYS_MISMATCH", f"{len(set(scores) - expected_pairs)} extra and "
                                                   f"{len(expected_pairs - set(scores))} missing reference scores")
    ctx = {"anchors": anchors, "parent": parent, "by_team": by_team, "scores": scores,
           "bindings": _index(inputs["bindings"], lambda r: r.get("org_id") if isinstance(r.get("org_id"), str)
                              else None),
           "games": _index(inputs["games"], _provider_id),
           "teams": _index(inputs["teams"], _provider_id),
           "venues": _index(inputs["venues"], lambda r: r.get("id") if is_int(r.get("id")) else None)}
    contests: list[dict[str, Any]] = []
    teams: list[dict[str, Any]] = []
    witnesses: list[dict[str, Any]] = []
    for ord_, target in targets:
        if set(views.get(target["contest_key"], {})) != set(VIEWS):
            _refuse("CONTEXT_INPUT_MALFORMED", f"{target['contest_key']}: the history does not hold views A and B")
        contest, team_records, w = _derive_target(ord_, target, views[target["contest_key"]], ctx)
        contests.append(contest)
        teams.extend(team_records)
        witnesses.extend(w)
    witnesses.extend(source_witnesses(anchors))
    strata = strata_rows(contests, scores)
    for family in FAMILY_IDS:
        for model_id in MODEL_IDS:
            total = sum(r["games"] for r in strata if r["family"] == family and r["model_id"] == model_id)
            if total != len(contests):
                _refuse("CONTEXT_STRATA_PARTITION_INVALID", f"{family}/{model_id}: {total} games != {len(contests)}")
    census = census_record(contests, teams, witnesses, strata)
    expected = anchors["expected"]
    counts = {"contests": len(contests), "team_views": len(teams), "witnesses": len(witnesses),
              "strata_rows": len(strata)}
    if counts != {k: expected[k] for k in counts}:
        _refuse("CONTEXT_POPULATION_COUNT_MISMATCH", f"{counts} != {expected}")
    if target_keys_sha256(keys) != expected["target_keys_sha256"]:
        _refuse("CONTEXT_TARGET_KEYS_MISMATCH", "the accepted 2023 target keys differ from the contract's complete "
                                                "expected key list")
    for table, rows in (("contests", contests), ("teams", teams), ("witnesses", witnesses), ("census", [census])):
        for r in rows:
            if tuple(r) != RECORD_FIELDS[table]:
                raise AssertionError(f"{table} record members differ from RECORD_FIELDS")
    return {"contests": contests, "teams": teams, "witnesses": witnesses, "strata": strata, "census": census,
            "scores": scores, "keys": keys}


# --------------------------------------------------------------------------------------------- payloads and identity

RECORD_TABLES = ("contests", "teams", "witnesses", "strata")
TARGET_TABLES = ("contests", "teams", "witnesses")


def record_lines(derived: dict[str, Any]) -> dict[str, list[str]]:
    if "lines" in derived:
        return derived["lines"]
    return {table: [canonical_line(r) for r in derived[table]] for table in RECORD_TABLES}


def target_chunk(derived: dict[str, Any], keys: Iterable[str]) -> bytes:
    """The checkpoint unit: every per-target record line of the given targets, table by table (deterministic)."""
    wanted = set(keys)
    lines = []
    for table in TARGET_TABLES:
        lines += [f"{table}\t{line}" for record, line in zip(derived[table], record_lines(derived)[table])
                  if record["contest_key"] in wanted]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _gzip(data: bytes) -> bytes:
    return gzip.compress(data, compresslevel=6, mtime=0)


def payloads(derived: dict[str, Any]) -> dict[str, bytes]:
    lines = record_lines(derived)
    out = {f"{table}.jsonl.gz": _gzip("".join(line + "\n" for line in lines[table]).encode("utf-8"))
           for table in RECORD_TABLES}
    out["census.json"] = (canonical_line(derived["census"]) + "\n").encode("utf-8")
    return out


def uncompressed_sha256(derived: dict[str, Any]) -> dict[str, str]:
    lines = record_lines(derived)
    return {f"{table}.jsonl": sha256_bytes("".join(line + "\n" for line in lines[table]).encode("utf-8"))
            for table in RECORD_TABLES}


def row_counts(derived: dict[str, Any]) -> dict[str, int]:
    return {**{f"{table}.jsonl.gz": len(derived[table]) for table in RECORD_TABLES}, "census.json": 1}


def inputs_claim(anchors: dict[str, Any]) -> dict[str, Any]:
    return {name: dict(anchors["inputs"][name]) for name in INPUT_NAMES}


def content_document(contract_sha256: str, anchors: dict[str, Any], payload_bytes: dict[str, bytes],
                     counts: dict[str, int], lines_sha256: dict[str, str]) -> dict[str, Any]:
    return {"schema": CONTENT_SCHEMA, "stage": "game-context-content", "population": POPULATION,
            "contract_id": anchors["contract_id"], "contract_sha256": contract_sha256,
            "inputs": inputs_claim(anchors), "source_clocks": anchors["source_clocks"],
            "rules_sha256": rules_sha256(), "payload_schema": PAYLOAD_SCHEMA,
            "outputs": {name: sha256_bytes(data) for name, data in sorted(payload_bytes.items())},
            "uncompressed_sha256": dict(sorted(lines_sha256.items())), "row_counts": dict(sorted(counts.items()))}


def database_document(contract_sha256: str, content_identity: str, database_sha256: str,
                      table_counts: dict[str, int]) -> dict[str, Any]:
    return {"schema": DATABASE_SCHEMA, "stage": "game-context-database", "population": POPULATION,
            "contract_sha256": contract_sha256, "content_identity": content_identity, "db_schema_version": DB_SCHEMA,
            "outputs": {DB_FILE: database_sha256}, "table_counts": dict(table_counts)}


def meta_values(document: dict[str, Any], content_identity: str, census: dict[str, Any],
                anchors: dict[str, Any]) -> dict[str, str]:
    return {"schema_version": DB_SCHEMA, "contract_id": document["contract_id"],
            "contract_sha256": document["contract_sha256"], "content_identity": content_identity,
            "payload_sha256": canonical_line(document["outputs"]),
            "uncompressed_sha256": canonical_line(document["uncompressed_sha256"]),
            "row_counts": canonical_line(document["row_counts"]), "inputs": canonical_line(inputs_claim(anchors)),
            "source_clocks": canonical_line(anchors["source_clocks"]), "labels": canonical_line(LABELS),
            "rules": canonical_line(rules_document()), "census_sha256": sha256_bytes(canonical_json_bytes(census))}


#: The exact database schema: one zlib block (level 9) per record table, with its record count, first/last record key
#: and the SHA-256 of its uncompressed JSONL lines.
DDL = tuple(tuple(d) for d in LAYOUT["database"]["ddl"])
TABLES = ("meta", "blocks")
BLOCK_LAYOUT = tuple(tuple(b) for b in LAYOUT["database"]["block_layout"])


def record_key(table: str, record: dict[str, Any]) -> str:
    if table == "contests":
        return str(record.get("contest_key"))
    if table == "teams":
        return f"{record.get('contest_key')}|{record.get('view')}"
    if table == "witnesses":
        return str(record.get("witness_key"))
    if table == "strata":
        return f"{record.get('family')}|{record.get('stratum')}|{record.get('model_id')}"
    return "census"


def block_rows(derived: dict[str, Any]) -> list[tuple[Any, ...]]:
    lines = record_lines(derived)
    rows = []
    for ord_, (table, segment) in enumerate(BLOCK_LAYOUT):
        if table == "census":
            records, chosen = [derived["census"]], [canonical_line(derived["census"])]
        else:
            records, chosen = list(derived[table]), list(lines[table])
        data = "".join(line + "\n" for line in chosen).encode("utf-8")
        rows.append((ord_, table, segment, len(records), record_key(table, records[0]) if records else None,
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

#: Which refusal a differing record member gets (first match in this order).
RECORD_FIELD_CODES = (
    ("pit_eligibility", "CONTEXT_PIT_CLAIM_INVALID"),
    ("evidence_label", "CONTEXT_LABEL_CLAIM_INVALID"), ("trust_state", "CONTEXT_LABEL_CLAIM_INVALID"),
    ("predictive_skill", "CONTEXT_LABEL_CLAIM_INVALID"), ("geography_authority", "CONTEXT_LABEL_CLAIM_INVALID"),
    ("distance_meaning", "CONTEXT_LABEL_CLAIM_INVALID"), ("calendar_meaning", "CONTEXT_LABEL_CLAIM_INVALID"),
    ("strata_meaning", "CONTEXT_LABEL_CLAIM_INVALID"), ("reading", "CONTEXT_LABEL_CLAIM_INVALID"),
    ("provider_game_retrieved_at_utc", "CONTEXT_SOURCE_CLOCK_MISMATCH"),
    ("venue_observed_at_utc", "CONTEXT_SOURCE_CLOCK_MISMATCH"), ("venue_clock_kind", "CONTEXT_SOURCE_CLOCK_MISMATCH"),
    ("origin_observed_at_utc", "CONTEXT_SOURCE_CLOCK_MISMATCH"), ("origin_clock_kind", "CONTEXT_SOURCE_CLOCK_MISMATCH"),
    ("season", "CONTEXT_DATE_MISMATCH"), ("term", "CONTEXT_DATE_MISMATCH"), ("contest_date", "CONTEXT_DATE_MISMATCH"),
    ("ncaa_contest_id", "CONTEXT_PARTICIPANT_MISMATCH"),
    ("a_key", "CONTEXT_PARTICIPANT_MISMATCH"), ("b_key", "CONTEXT_PARTICIPANT_MISMATCH"),
    ("a_org_id", "CONTEXT_PARTICIPANT_MISMATCH"), ("b_org_id", "CONTEXT_PARTICIPANT_MISMATCH"),
    ("a_team_name", "CONTEXT_PARTICIPANT_MISMATCH"), ("b_team_name", "CONTEXT_PARTICIPANT_MISMATCH"),
    ("a_division_label", "CONTEXT_PARTICIPANT_MISMATCH"), ("b_division_label", "CONTEXT_PARTICIPANT_MISMATCH"),
    ("classification_pair", "CONTEXT_PARTICIPANT_MISMATCH"), ("view", "CONTEXT_PARTICIPANT_MISMATCH"),
    ("team_key", "CONTEXT_PARTICIPANT_MISMATCH"), ("team_org_id", "CONTEXT_PARTICIPANT_MISMATCH"),
    ("team_name", "CONTEXT_PARTICIPANT_MISMATCH"), ("team_division_label", "CONTEXT_PARTICIPANT_MISMATCH"),
    ("opponent_key", "CONTEXT_PARTICIPANT_MISMATCH"), ("opponent_name", "CONTEXT_PARTICIPANT_MISMATCH"),
    ("parent_site", "CONTEXT_SITE_MISMATCH"), ("parent_neutral_site_text", "CONTEXT_SITE_MISMATCH"),
    ("parent_role_for_team", "CONTEXT_SITE_MISMATCH"), ("site_class", "CONTEXT_SITE_MISMATCH"),
    ("cfbd_team_id", "CONTEXT_BINDING_MISMATCH"), ("binding_rule", "CONTEXT_BINDING_MISMATCH"),
    ("binding_state", "CONTEXT_BINDING_MISMATCH"), ("binding_reason", "CONTEXT_BINDING_MISMATCH"),
    ("provider_documented_game_ids", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_game_id", "CONTEXT_PROVIDER_CLAIM_MISMATCH"), ("provider_join_state", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_join_reason", "CONTEXT_PROVIDER_CLAIM_MISMATCH"), ("provider_home_side", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_neutral_site", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_site_claim", "CONTEXT_PROVIDER_CLAIM_MISMATCH"), ("site_agreement", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_start_claim_utc", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_start_time_tbd", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_date_state", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_utc_date_minus_parent_date_days", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_season_type", "CONTEXT_PROVIDER_CLAIM_MISMATCH"), ("provider_week", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_role_for_team", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("provider_site_claim_for_team", "CONTEXT_PROVIDER_CLAIM_MISMATCH"),
    ("prior_rule", "CONTEXT_CALENDAR_MISMATCH"), ("eligible_prior_count", "CONTEXT_CALENDAR_MISMATCH"),
    ("excluded_prior_count", "CONTEXT_CALENDAR_MISMATCH"), ("excluded_prior_reasons", "CONTEXT_CALENDAR_MISMATCH"),
    ("excluded_prior_contest_keys", "CONTEXT_CALENDAR_MISMATCH"),
    ("not_strictly_earlier_contests", "CONTEXT_CALENDAR_MISMATCH"), ("latest_prior_date", "CONTEXT_CALENDAR_MISMATCH"),
    ("latest_prior_contest_keys", "CONTEXT_CALENDAR_MISMATCH"), ("calendar_interval_days", "CONTEXT_CALENDAR_MISMATCH"),
    ("intervening_calendar_days", "CONTEXT_CALENDAR_MISMATCH"), ("calendar_state", "CONTEXT_CALENDAR_MISMATCH"),
    ("min_calendar_interval_days", "CONTEXT_CALENDAR_MISMATCH"), ("min_calendar_state", "CONTEXT_CALENDAR_MISMATCH"),
    ("origin_location_id", "CONTEXT_GEOGRAPHY_MISMATCH"), ("origin_location_name", "CONTEXT_GEOGRAPHY_MISMATCH"),
    ("origin_latitude", "CONTEXT_GEOGRAPHY_MISMATCH"), ("origin_longitude", "CONTEXT_GEOGRAPHY_MISMATCH"),
    ("origin_state", "CONTEXT_GEOGRAPHY_MISMATCH"), ("origin_reason", "CONTEXT_GEOGRAPHY_MISMATCH"),
    ("venue_id", "CONTEXT_GEOGRAPHY_MISMATCH"), ("provider_venue_name", "CONTEXT_GEOGRAPHY_MISMATCH"),
    ("venue_reference_name", "CONTEXT_GEOGRAPHY_MISMATCH"), ("venue_name_state", "CONTEXT_GEOGRAPHY_MISMATCH"),
    ("venue_latitude", "CONTEXT_GEOGRAPHY_MISMATCH"), ("venue_longitude", "CONTEXT_GEOGRAPHY_MISMATCH"),
    ("venue_coordinate_state", "CONTEXT_GEOGRAPHY_MISMATCH"), ("venue_coordinate_reason", "CONTEXT_GEOGRAPHY_MISMATCH"),
    ("reference_distance_m", "CONTEXT_DISTANCE_MISMATCH"), ("distance_state", "CONTEXT_DISTANCE_MISMATCH"),
    ("distance_reason", "CONTEXT_DISTANCE_MISMATCH"), ("distance_method", "CONTEXT_DISTANCE_MISMATCH"),
    ("origin_is_game_venue", "CONTEXT_DISTANCE_MISMATCH"), ("max_reference_distance_m", "CONTEXT_DISTANCE_MISMATCH"),
    ("max_distance_state", "CONTEXT_DISTANCE_MISMATCH"),
    ("min_calendar_stratum", "CONTEXT_STRATUM_ASSIGNMENT_MISMATCH"),
    ("max_distance_stratum", "CONTEXT_STRATUM_ASSIGNMENT_MISMATCH"),
    ("source", "CONTEXT_WITNESS_LOCATOR_MISMATCH"), ("locator", "CONTEXT_WITNESS_LOCATOR_MISMATCH"),
    ("subject_kind", "CONTEXT_WITNESS_LOCATOR_MISMATCH"), ("raw", "CONTEXT_WITNESS_RAW_MISMATCH"),
    ("raw_sha256", "CONTEXT_WITNESS_RAW_MISMATCH"), ("supports", "CONTEXT_WITNESS_STATE_MISMATCH"),
    ("state", "CONTEXT_WITNESS_STATE_MISMATCH"), ("reason", "CONTEXT_WITNESS_STATE_MISMATCH"),
    ("model_id", "CONTEXT_MODEL_MISMATCH"), ("model_sha256", "CONTEXT_MODEL_MISMATCH"),
    ("metric_kind", "CONTEXT_MODEL_MISMATCH"), ("output_kind", "CONTEXT_MODEL_MISMATCH"),
    ("games", "CONTEXT_STRATUM_COUNT_MISMATCH"), ("score_records", "CONTEXT_STRATUM_COUNT_MISMATCH"),
    ("scored_games", "CONTEXT_STRATUM_COUNT_MISMATCH"), ("unscored_games", "CONTEXT_STRATUM_COUNT_MISMATCH"),
    ("unscored_by_reason", "CONTEXT_STRATUM_COUNT_MISMATCH"), ("scored_by_sample_state", "CONTEXT_STRATUM_COUNT_MISMATCH"),
    ("member_contest_keys_sha256", "CONTEXT_STRATUM_MEMBERSHIP_MISMATCH"),
    ("member_score_lines_sha256", "CONTEXT_STRATUM_MEMBERSHIP_MISMATCH"),
    ("witness_keys", "CONTEXT_LINEAGE_MISMATCH"),
    ("mae", "CONTEXT_SCORE_METRIC_MISMATCH"), ("mae_decimal", "CONTEXT_SCORE_METRIC_MISMATCH"),
    ("mse", "CONTEXT_SCORE_METRIC_MISMATCH"), ("mse_decimal", "CONTEXT_SCORE_METRIC_MISMATCH"),
)
FIELD_CODE_PREFIXES = (("brier_", "CONTEXT_SCORE_METRIC_MISMATCH"), ("log_loss_", "CONTEXT_SCORE_METRIC_MISMATCH"),
                       ("absolute_error_", "CONTEXT_SCORE_METRIC_MISMATCH"),
                       ("squared_error_", "CONTEXT_SCORE_METRIC_MISMATCH"))
TABLE_LABELS = {"contests": "CONTEST", "teams": "TEAM", "witnesses": "WITNESS", "strata": "STRATUM"}
#: Record identity members the checks before the comparison hash or use as mapping keys: a present one must be a JSON
#: string (refused with its own code before any key is computed).
IDENTITY_MEMBERS = {"contests": ("contest_key",), "teams": ("contest_key", "view"), "witnesses": ("witness_key",),
                    "strata": ("family", "stratum", "model_id"), "census": ()}


def _field_code(differing: set[str]) -> str:
    for field, code in RECORD_FIELD_CODES:
        if field in differing:
            return code
    for field in sorted(differing):
        for prefix, code in FIELD_CODE_PREFIXES:
            if field.startswith(prefix):
                return code
    return "CONTEXT_RECORD_MISMATCH"


def strata_fields(record: dict[str, Any]) -> tuple[str, ...] | None:
    kind = MODELS.get(record.get("model_id"), {}).get("metric_kind")
    if kind is None:
        return None
    return STRATA_COMMON_FIELDS + STRATA_METRIC_FIELDS[kind]


class GameContext:
    """A verified, read-only handle on one content-addressed national 2023 game-context release.

    Construction refuses (ContextError with a stable code) unless the release location, run manifest identity, database
    bytes, schema and meta claims verify, every pinned input verifies under the explicitly named data root, and every
    record of every table, the census, the content identity and the contract-defined database identity document equal
    what is re-derived from those inputs. Complete membership and multiplicity are checked before any record is compared;
    each refusal is checked in a fixed order so that every forgery is refused for its own cause."""

    def __init__(self, database: Path, *, data_root: Path, manifest: Path | None = None,
                 expect_identity: str | None = None, anchors: dict[str, Any] | None = None) -> None:
        self.anchors = anchors if anchors is not None else ANCHORS
        self.binding = self._verify_location_and_manifest(database, manifest, expect_identity)
        document = self.binding["identity_document"]
        if document.get("contract_sha256") != self.anchors["contract_sha256"]:
            _refuse("CONTEXT_CONTRACT_MISMATCH", f"the release names contract {document.get('contract_sha256')}, the "
                                                 f"reader binds {self.anchors['contract_sha256']}")
        inputs = load_inputs(Path(data_root), self.anchors)
        try:
            self.conn = readonly_sqlite.connect_readonly(database)
        except readonly_sqlite.DatabaseLocationError as exc:
            raise ContextError(exc.code, exc.detail) from exc
        try:
            self._verify_database(inputs)
        except sqlite3.DatabaseError as exc:
            self.conn.close()
            raise ContextError("CONTEXT_SCHEMA_UNSUPPORTED", str(exc)) from exc
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
            raise ContextError(exc.code, exc.detail) from exc
        db = Path(database)
        if not _io_path(db).is_file():
            _refuse("CONTEXT_DATABASE_MISSING", f"no context database file at {db}")
        absolute = Path(os.path.abspath(db))
        if absolute.name != DB_FILE or absolute.parent.parent.name != "sha256" or \
                absolute.parent.parent.parent.name != POPULATION:
            _refuse("CONTEXT_LOCATION_INVALID", f"the release must sit at <root>/{POPULATION}/sha256/<id>/{DB_FILE}")
        identity = absolute.parent.name
        if not IDENTITY_RE.match(identity):
            _refuse("CONTEXT_LOCATION_INVALID", f"directory name {identity!r} is not an identity")
        if manifest is None:
            manifest_path = manifest_path_for(db)
        else:
            try:
                manifest_path = Path(readonly_sqlite.literal_path(manifest))
            except readonly_sqlite.DatabaseLocationError as exc:
                code = MANIFEST_LOCATION_CODES.get(exc.code, exc.code)
                raise ContextError(code, f"--manifest {manifest}: {exc.detail}") from exc
        if not _io_path(manifest_path).is_file():
            _refuse("CONTEXT_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
        try:
            doc = json.loads(_io_path(manifest_path).read_text(encoding="utf-8"))
            identity_document = doc["identity_document"]
            computed = sha256_bytes(canonical_json_bytes(identity_document))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ContextError("CONTEXT_MANIFEST_MALFORMED", str(exc)) from exc
        if computed != identity or doc.get("identity") != identity:
            _refuse("CONTEXT_IDENTITY_MISMATCH", f"manifest identity document hashes to {computed}, directory is "
                                                 f"{identity}, the manifest names {doc.get('identity')!r}")
        if not isinstance(identity_document, dict) or \
                (identity_document.get("stage"), identity_document.get("schema"),
                 identity_document.get("db_schema_version"), identity_document.get("population")) != \
                ("game-context-database", DATABASE_SCHEMA, DB_SCHEMA, POPULATION):
            _refuse("CONTEXT_SCHEMA_UNSUPPORTED", "not a national game-context database manifest")
        outputs = identity_document.get("outputs")
        if outputs is not None and not isinstance(outputs, dict):
            _refuse("CONTEXT_IDENTITY_DOCUMENT_MISMATCH", "the manifest identity document's outputs is not an object")
        expected_sha = (outputs or {}).get(DB_FILE)
        actual_sha = sha256_file(_io_path(db))
        if expected_sha != actual_sha:
            _refuse("CONTEXT_DATABASE_TAMPERED", f"release bytes hash to {actual_sha}, manifest names {expected_sha}")
        if expect_identity is not None and expect_identity != identity:
            _refuse("STALE_CONTEXT_IDENTITY", f"expected {expect_identity}, found {identity}")
        return {"identity": identity, "sha256": actual_sha, "manifest": str(manifest_path),
                "identity_document": identity_document}

    # ---- schema, meta claims and the complete re-derivation
    def _verify_database(self, inputs: dict[str, Any]) -> None:
        a = self.anchors
        master = sorted((str(r[0]), str(r[1]), r[2]) for r in self.conn.execute(
            "SELECT type, name, sql FROM sqlite_master"))
        if master != sorted(DDL):
            _refuse("CONTEXT_SCHEMA_UNSUPPORTED", "the release schema differs from the contract")
        meta_rows = [(str(r[0]), r[1]) for r in self.conn.execute("SELECT key, value FROM meta ORDER BY rowid")]
        meta = dict(meta_rows)
        if len(meta) != len(meta_rows):
            _refuse("CONTEXT_META_MISMATCH", "duplicate meta keys")
        if meta.get("schema_version") != DB_SCHEMA:
            _refuse("CONTEXT_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}")
        if meta.get("contract_sha256") != a["contract_sha256"] or meta.get("contract_id") != a["contract_id"]:
            _refuse("CONTEXT_CONTRACT_MISMATCH", "the release meta names another contract")
        claims = {name: _json_or_none(meta.get(name)) for name in ("inputs", "source_clocks", "labels", "rules")}
        if claims["labels"] != LABELS:
            labels = claims["labels"] if isinstance(claims["labels"], dict) else {}
            code = ("CONTEXT_PIT_CLAIM_INVALID" if labels.get("pit_eligibility") != LABELS["pit_eligibility"] or
                    labels.get("temporal_basis") != LABELS["temporal_basis"] else "CONTEXT_LABEL_CLAIM_INVALID")
            _refuse(code, "the release declares labels other than the contract's")
        if canonical_json_bytes(claims["inputs"]) != canonical_json_bytes(inputs_claim(a)):
            _refuse("CONTEXT_PARENT_MISMATCH", "the release was built from other inputs")
        if canonical_json_bytes(claims["source_clocks"]) != canonical_json_bytes(a["source_clocks"]):
            _refuse("CONTEXT_SOURCE_CLOCK_MISMATCH", "the release declares other source clocks")
        if canonical_json_bytes(claims["rules"]) != canonical_json_bytes(rules_document()):
            _refuse("CONTEXT_RULES_CLAIM_INVALID", "the release declares other rules")
        counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        # value equality keeps a fractional, string or boolean count here; an integral float count is equal by value
        # and is refused last by the canonical-bytes identity-document rule
        if counts != self.binding["identity_document"].get("table_counts"):
            _refuse("CONTEXT_COUNT_MISMATCH",
                    f"table counts {counts} != {self.binding['identity_document'].get('table_counts')}")
        present = self._read_blocks()
        derived = derive(inputs, a)
        lines = record_lines(derived)
        for table in RECORD_TABLES:
            self._compare(table, present[table], lines[table], derived[table])
        if len(present["census"]) != 1:
            _refuse("CONTEXT_CENSUS_MISMATCH", f"the census block holds {len(present['census'])} records")
        if present["census"][0][0] != canonical_line(derived["census"]):
            _refuse("CONTEXT_CENSUS_MISMATCH", "the stored census differs from its records")
        content_payloads = payloads(derived)
        document = content_document(a["contract_sha256"], a, content_payloads, row_counts(derived),
                                    uncompressed_sha256(derived))
        content_identity = sha256_bytes(canonical_json_bytes(document))
        if meta.get("content_identity") != content_identity or \
                self.binding["identity_document"].get("content_identity") != content_identity:
            _refuse("CONTEXT_CONTENT_IDENTITY_MISMATCH", f"the re-derived content identity is {content_identity}")
        expected_meta = meta_values(document, content_identity, derived["census"], a)
        if meta != expected_meta:
            _refuse("CONTEXT_META_MISMATCH", "meta differs on " + str(sorted(
                k for k in set(meta) | set(expected_meta) if meta.get(k) != expected_meta.get(k))))
        identity_document = self.binding["identity_document"]
        expected_document = database_document(a["contract_sha256"], content_identity, self.binding["sha256"], counts)
        expected_bytes = canonical_json_bytes(expected_document)
        if canonical_json_bytes(identity_document) != expected_bytes:
            differing = sorted(k for k in set(identity_document) | set(expected_document)
                               if k not in identity_document or k not in expected_document
                               or canonical_json_bytes(identity_document[k]) !=
                               canonical_json_bytes(expected_document[k]))
            _refuse("CONTEXT_IDENTITY_DOCUMENT_MISMATCH",
                    f"the manifest identity document is not the contract-defined database document (differs on "
                    f"{differing})")
        database_identity = sha256_bytes(expected_bytes)
        if database_identity != self.binding["identity"]:
            _refuse("CONTEXT_IDENTITY_DOCUMENT_MISMATCH", f"the location names {self.binding['identity']}, the "
                                                          f"contract-defined document is {database_identity}")
        self.database_identity = database_identity
        self.content_identity = content_identity
        self.meta = meta
        self.derived = derived
        self.participants = {c["contest_key"]: (c["a_key"], c["b_key"]) for c in derived["contests"]}

    def _read_blocks(self) -> dict[str, list[tuple[str, dict[str, Any]]]]:
        """Every block's index columns against its own content, then each record's JSON type, identity member types,
        exact member set (extra or missing members refuse), the ridge no-probability rule and the per-family strata
        partition -- before any comparison with the re-derived records."""
        rows = [tuple(r) for r in self.conn.execute(
            "SELECT ord, record_table, segment, records, first_key, last_key, lines_sha256, block FROM blocks "
            "ORDER BY ord")]
        present: dict[str, list[tuple[str, dict[str, Any]]]] = {t: [] for t in (*RECORD_TABLES, "census")}
        layout = []
        for ord_, table, segment, records, first_key, last_key, lines_sha, blob in rows:
            if table not in present:
                _refuse("CONTEXT_SCHEMA_UNSUPPORTED", f"block {ord_} names table {table!r}")
            try:
                data = zlib.decompress(blob)
                lines = data.decode("utf-8").split("\n")
            except (zlib.error, TypeError, UnicodeDecodeError) as exc:
                raise ContextError("CONTEXT_INDEX_MISMATCH", f"block {ord_} does not decompress: {exc}") from exc
            if lines[-1] != "":
                _refuse("CONTEXT_INDEX_MISMATCH", f"block {ord_} does not end with a newline")
            parsed = []
            for line in lines[:-1]:
                try:
                    record = json.loads(line)
                except ValueError as exc:
                    raise ContextError("CONTEXT_RECORD_TYPE_INVALID", f"block {ord_} holds a non-JSON line") from exc
                if not isinstance(record, dict):
                    _refuse("CONTEXT_RECORD_TYPE_INVALID", f"block {ord_} holds a non-object line")
                for name in IDENTITY_MEMBERS[table]:
                    if name in record and not isinstance(record[name], str):
                        _refuse("CONTEXT_RECORD_TYPE_INVALID", f"{table} record: {name} is a JSON "
                                                               f"{type(record[name]).__name__}, not a string")
                parsed.append((line, record))
            keys = [record_key(table, r) for _l, r in parsed]
            if sha256_bytes(data) != lines_sha or records != len(parsed) or \
                    first_key != (keys[0] if keys else None) or last_key != (keys[-1] if keys else None):
                _refuse("CONTEXT_INDEX_MISMATCH", f"block {ord_} index columns differ from its content")
            layout.append((table, segment))
            present[table] += parsed
        if layout != list(BLOCK_LAYOUT):
            _refuse("CONTEXT_INDEX_MISMATCH", "the blocks do not follow the contract layout")
        for _line, record in present["strata"]:
            if record.get("model_id") in MARGIN_MODELS and any(k in record for k in PROBABILITY_ONLY_FIELDS):
                _refuse("CONTEXT_RIDGE_PROBABILITY_INVENTED", f"stratum {record_key('strata', record)}: the ridge "
                                                              "margin model serves no probability or Brier score")
        for table in (*RECORD_TABLES, "census"):
            for _line, record in present[table]:
                want = strata_fields(record) if table == "strata" else RECORD_FIELDS[table]
                if want is None:
                    _refuse("CONTEXT_MODEL_MISMATCH", f"stratum {record_key(table, record)} names an undeclared model")
                if set(record) != set(want):
                    extra, missing = sorted(set(record) - set(want)), sorted(set(want) - set(record))
                    _refuse("CONTEXT_RECORD_SHAPE_INVALID", f"{table} record {record_key(table, record)}: extra "
                                                            f"members {extra[:4]}, missing {missing[:4]}")
        expected_games = self.anchors["expected"]["contests"]
        for family in FAMILY_IDS:
            for model_id in MODEL_IDS:
                games = [r.get("games") for _l, r in present["strata"]
                         if r.get("family") == family and r.get("model_id") == model_id]
                if not all(is_int(g) and g >= 0 for g in games):
                    _refuse("CONTEXT_COUNT_TYPE_INVALID", f"{family}/{model_id}: a stratum game count is not a "
                                                          "non-negative JSON integer")
                total = sum(games)
                if total == 2 * expected_games:
                    _refuse("CONTEXT_MIRROR_DOUBLE_COUNT", f"{family}/{model_id}: {total} games is every target "
                                                           "counted in both orientations")
                if total != expected_games:
                    _refuse("CONTEXT_STRATA_PARTITION_INVALID", f"{family}/{model_id}: strata hold {total} games, not "
                                                                f"the {expected_games} targets")
        return present

    @staticmethod
    def _compare(table: str, present: list[tuple[str, dict[str, Any]]], expected: list[str],
                 wanted_records: list[dict[str, Any]]) -> None:
        label = TABLE_LABELS[table]
        keys = [record_key(table, r) for _l, r in present]
        if len(keys) != len(set(keys)):
            _refuse("CONTEXT_DUPLICATE_ROW", f"{table} repeats a record key")
        wanted = [record_key(table, r) for r in wanted_records]
        missing = sorted(set(wanted) - set(keys))
        if missing:
            _refuse(f"CONTEXT_{label}_ROW_MISSING", f"{len(missing)} expected {table} records absent, e.g. "
                                                    f"{missing[:3]}")
        extra = sorted(set(keys) - set(wanted))
        if extra:
            _refuse(f"CONTEXT_{label}_ROW_EXTRA", f"{len(extra)} {table} records outside the accepted population, "
                                                  f"e.g. {extra[:3]}")
        if keys != wanted:
            _refuse("CONTEXT_ORDER_MISMATCH", f"{table} is not in the contract order")
        for (line, got), want_line, want in zip(present, expected, wanted_records):
            if line == want_line:
                continue
            differing = {f for f in set(want) | set(got)
                         if f not in want or f not in got or canonical_json_bytes(got[f]) != canonical_json_bytes(want[f])}
            _refuse(_field_code(differing), f"{table} {record_key(table, want)} differs on {sorted(differing)[:6]}")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "GameContext":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- serving
    @staticmethod
    def filters(grain: str, *, season: Any = None, contest: Any = None, team: Any = None, orientation: Any = None,
                source: Any = None, model: Any = None, family: Any = None) -> dict[str, Any]:
        """Validate a selection before any file is read: an unknown grain, a malformed or an inapplicable selector is
        refused with its own code (SELECTORS)."""
        if grain not in GRAINS:
            _refuse("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}")
        filters: dict[str, Any] = {}
        if season is not None:
            if not is_int(season):
                _refuse("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if contest is not None:
            text = str(contest).strip()
            text = f"ncaa:{text}" if text.isascii() and text.isdigit() else text
            if not CONTEST_KEY_RE.match(text):
                _refuse("CONTEST_KEY_INVALID", f"contest must be an accepted contest key ncaa:<digits>, got "
                                               f"{contest!r}")
            filters["contest"] = text
        if team is not None:
            text = str(team).strip()
            text = f"org:{text}" if text.isascii() and text.isdigit() else text
            if not TEAM_KEY_RE.match(text):
                _refuse("TEAM_INVALID", f"team must be an accepted organization key org:<digits>, got {team!r}")
            filters["team"] = text
        if orientation is not None:
            if grain not in ("team-context", "context-witness"):
                _refuse("FILTER_NOT_APPLICABLE", "orientation applies to the team-context and context-witness grains")
            if orientation not in VIEWS:
                _refuse("ORIENTATION_INVALID", f"orientation must be A or B, got {orientation!r}")
            filters["orientation"] = orientation
        if source is not None:
            if grain != "context-witness":
                _refuse("FILTER_NOT_APPLICABLE", "source applies to the context-witness grain only")
            if source not in SOURCES:
                _refuse("SOURCE_UNKNOWN", f"source must be one of {list(SOURCES)}")
            filters["source"] = source
        if model is not None:
            if grain not in ("context-score-summary", "context-witness"):
                _refuse("FILTER_NOT_APPLICABLE", "model applies to the context-score-summary and context-witness "
                                                 "grains")
            if model not in MODEL_IDS:
                _refuse("MODEL_UNKNOWN", f"model must be one of {list(MODEL_IDS)}")
            filters["model"] = model
        if family is not None:
            if grain != "context-score-summary":
                _refuse("FILTER_NOT_APPLICABLE", "family applies to the context-score-summary grain only")
            if family not in FAMILY_IDS:
                _refuse("FAMILY_UNKNOWN", f"family must be one of {list(FAMILY_IDS)}")
            filters["family"] = family
        return filters

    def query(self, grain: str, *, season: Any = None, contest: Any = None, team: Any = None, orientation: Any = None,
              source: Any = None, model: Any = None, family: Any = None, limit: int | None = 50, offset: int = 0,
              all_rows: bool = False) -> dict[str, Any]:
        filters = self.filters(grain, season=season, contest=contest, team=team, orientation=orientation,
                               source=source, model=model, family=family)
        if not is_int(offset) or offset < 0:
            _refuse("NEGATIVE_OFFSET", "offset must be a zero or positive integer")
        if limit is not None and (not is_int(limit) or limit < 0):
            _refuse("NEGATIVE_LIMIT", "limit must be a zero or positive integer")
        census = self.derived["census"]
        result: dict[str, Any] = {
            "context_identity": self.database_identity, "content_identity": self.content_identity,
            "contract_id": self.anchors["contract_id"], "contract_sha256": self.anchors["contract_sha256"],
            "inputs": {name: {k: v for k, v in spec.items() if k != "relative_path"}
                       for name, spec in self.anchors["inputs"].items()},
            "grain": grain, "filters": filters, "offset": offset, "limit": None if all_rows else limit, **LABELS,
            "denominators": {k: census[k] for k in ("contests", "team_views", "witnesses", "strata_rows")},
            "verification": {"contests_verified": len(self.derived["contests"]),
                             "team_views_verified": len(self.derived["teams"]),
                             "witnesses_verified": len(self.derived["witnesses"]),
                             "strata_rows_verified": len(self.derived["strata"]),
                             "pinned_inputs_verified": list(INPUT_NAMES), "records_rederived": True,
                             "content_identity_rederived": True, "database_document_rederived": True}}
        if "season" in filters and filters["season"] != SEASON:
            result.update(season_scope_state="SEASON_NOT_YET_AUDITED", total=0, returned=0, rows=[],
                          next_offset=None, note=f"only the {SEASON} season is audited in this release; no row is "
                                                 "fabricated for another season")
            return result
        if grain == "context-score-summary" and ("contest" in filters or "team" in filters):
            chosen = {c["contest_key"] for c in self.derived["contests"] if self._match("contest-context", c, {
                k: v for k, v in filters.items() if k in ("contest", "team")})}
            records = strata_rows(self.derived["contests"], self.derived["scores"], chosen)
            result["summary_selection"] = {"rule": SUMMARY_SELECTION_RULE, "selected_games": len(chosen)}
        else:
            records = self.derived[GRAINS[grain]]
        rows = [r for r in records if self._match(grain, r, filters)]
        total = len(rows)
        page = rows[offset:] if all_rows else rows[offset:offset + (limit or 0)]
        result.update(season_scope_state=f"RETROSPECTIVE_{SEASON}", total=total, returned=len(page), rows=page,
                      next_offset=offset + len(page) if offset + len(page) < total else None)
        return result

    def _match(self, grain: str, record: dict[str, Any], filters: dict[str, Any]) -> bool:
        if grain == "context-score-summary":
            if "model" in filters and record["model_id"] != filters["model"]:
                return False
            return "family" not in filters or record["family"] == filters["family"]
        if "contest" in filters and record.get("contest_key") != filters["contest"]:
            return False
        if grain == "contest-context":
            return "team" not in filters or filters["team"] in (record["a_key"], record["b_key"])
        if grain == "team-context":
            if "team" in filters and record["team_key"] != filters["team"]:
                return False
            return "orientation" not in filters or record["view"] == filters["orientation"]
        if "source" in filters and record["source"] != filters["source"]:
            return False
        if "model" in filters and record["model_id"] != filters["model"]:
            return False
        if "orientation" in filters and record["view"] != filters["orientation"]:
            return False
        if "team" in filters:
            if record["subject_kind"] == "TEAM_VIEW":
                return record["team_key"] == filters["team"]
            if record["subject_kind"] == "CONTEST":
                return filters["team"] in self.participants.get(record["contest_key"], ())
            return False
        return True


def _json_or_none(text: Any) -> Any:
    try:
        return json.loads(text) if isinstance(text, (str, bytes)) else None
    except ValueError:
        return None
