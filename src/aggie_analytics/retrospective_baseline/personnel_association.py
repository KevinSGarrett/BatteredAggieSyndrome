r"""National posthoc personnel/history association 2016-2022 (BAT-732 bounded research contribution to BAT-415, BAT-416
and BAT-423, Cycle #61 TP61-A01).

Every rule lives here, and the committed research/data contract
``configs/national_personnel_association_2016_2022_contract.json`` must equal these constants (the builder refuses
otherwise). The reader pins that contract's SHA-256, every accepted parent identity, the expected collection of every
grain and (once materialized) the canonical profile (:mod:`.personnel_association_anchors`).

Authority. This is separately authorized exploratory retrospective association research,
POSTHOC_ROSTER_ASSOCIATION_NOT_FORECAST: the C59 season roster snapshots were observed in 2023 (source repository commit
2023-05-05T03:50:21Z), after every study game, so target-season roster membership is never pregame-known availability.
Every parent ``target_game_feature_eligible``, ``protected_eligible`` and PIT flag stays false and is carried unchanged;
this permission to examine an after-the-fact association is not a training, forecast or PIT admission. Every record is
RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED, NOT_CALIBRATED and predictive skill NOT_ESTABLISHED; 2021-2022
is an already-exposed retrospective development comparison, never blind; adverse and null results are completed results.

Inputs (read only, each verified by its accepted reader and pinned): the accepted C56 national retrospective reference
release (its 2016-2022 feature records -- the same-season, strictly earlier-date history counts with target exclusion and
contributing-key lineage -- its separately governed label records and the unchanged C47 fixed-model estimate records),
verified with the accepted C39 history and C38 population databases it binds; and the accepted C59 national personnel
evidence release (its 1,760 program-season coverage records, 982 returning summaries and 5,867 components).

Derivation order (each step reads only what it names):

1. **qualification** -- every C59 program-season (FBS, FCS, qualified and unqualified chains alike): the exact chain
   state, its own ``returning_target_summary_key`` resolved to a summary of the same target season and canonical team,
   the three bounded roster rates recomputed from integer set counts (Python float division and exact rationals; the
   parent's stored rates must equal them), the signed and count-share components kept raw and unclipped with their
   semantics (never model columns), the parent eligibility flags (false) and the study involvement counts.
2. **features** -- every accepted 2016-2022 target view: both sides' history counts and contributing keys from the C56
   feature record, the smoothed history log-odds ``ell = log(2W + T + 2) - log(2L + T + 2)``, each side's roster block
   from its own same-season program-season (null, never zero, when the side has no joinable summary), the A-minus-B
   history and roster-rate differences and the common-support state (both sides joinable).
3. **fits** -- the FIT cohort is the common-support 2016-2020 games with a decisive label; each design column's scale
   is ``sqrt(fsum(0.5 * x * x) / N_fit_games)`` over its paired A and B rows (no centering; a zero scale is 1, marked
   constant); the two frozen zero-intercept lambda-1 L2 logistic fits use the accepted C56 ``reference_fit.fit_logistic``
   unchanged (paired rows of weight 1/2, Newton from zero, gradient tolerance 1e-10, at most 100 steps and 30 halvings).
   A genuine numerical failure is recorded as such, never as a fit or a null result.
4. **estimates** -- every target, model and orientation: the game-grain probability first (fixed NULL 1/2; the
   unchanged C47 smoothed exact rational, equal to the accepted C47 record; the fitted sigmoid as a decimal12 string),
   the reverse orientation its exact complement; outside common support (or after a recorded fit failure) every model
   abstains with its explicit reason.
5. **scores** -- one A-oriented score per target and model against the accepted label: Brier as an exact rational of
   the served probability and log loss with only its argument clipped to [1e-15, 1 - 1e-15]; abstained games, ties and
   missing labels stay explicitly unscored.
6. **parameters and summary** -- scales, coefficients, convergence, objective, gradient and trajectory of both fits;
   per-season and FIT/COMPARISON scope summaries per model and descriptive differences on identical keys, the primary
   one being augmented-minus-history Brier on the pooled 2021-2022 comparison partition (negative = lower descriptive
   Brier). No significance, calibration, champion, causal personnel or predictive-skill conclusion follows.

The reader (:class:`PersonnelAssociation`) needs no data root: before any row is served it verifies the location, the
run manifest, the database bytes, the schema and meta claims, every record's exact members and JSON types, the complete
expected collection of every grain, every qualification and feature rule the records can re-derive, a fresh refit and
the complete re-derivation of every estimate, score, parameter and summary record, the content document, the
contract-defined database identity document and the pinned canonical profile. The query serves six grains through the
explicit ``bas-retrospective-baseline-query --personnel-association`` mode only.

Cycle #61 -- Work round #2 -- FIRST REPAIR (C61-CONT-01): on Windows the release layout and identity are checked on the
genuine native names of the existing file (:func:`native_location`: an 8.3 short or case-equivalent spelling of the same
release serves it, MF61A01-01), and a team selector holding a lone surrogate is refused as TEAM_INVALID before any file
is read (MF61A01-02).
"""
from __future__ import annotations

import copy
import json
import math
import os
import random
import re
import sqlite3
import zlib
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics import readonly_sqlite
from aggie_analytics.retrospective_baseline import benchmark as bm
from aggie_analytics.retrospective_baseline import reference_fit as rf

canonical_json_bytes = bm.canonical_json_bytes
canonical_line = bm.canonical_line
sha256_bytes = bm.sha256_bytes
sha256_file = bm.sha256_file
is_int = bm.is_int
_io_path = bm._io_path
manifest_path_for = bm.manifest_path_for

# --------------------------------------------------------------------------------------------- identity and scope

POPULATION = "national_personnel_association_2016_2022"
DB_FILE = "national_personnel_association.sqlite"
CONTRACT_ID = "BAT-732-NATIONAL-PERSONNEL-ASSOCIATION-2016-2022-V1.0"
CONTRACT_REL = "configs/national_personnel_association_2016_2022_contract.json"
CONTENT_SCHEMA = "BAS-PERSONNEL-ASSOCIATION-CONTENT-1"
DATABASE_SCHEMA = "BAS-PERSONNEL-ASSOCIATION-DATABASE-1"
DB_SCHEMA = "BAS-PERSONNEL-ASSOCIATION-DB-1"
PAYLOAD_SCHEMA = "BAS-PERSONNEL-ASSOCIATION-PAYLOAD-1"

STUDY_SEASONS = (2016, 2017, 2018, 2019, 2020, 2021, 2022)
FIT_SEASONS = (2016, 2017, 2018, 2019, 2020)
COMPARISON_SEASONS = (2021, 2022)
PARTITIONS = {"FIT": FIT_SEASONS, "COMPARISON": COMPARISON_SEASONS}
PARTITION_IDS = tuple(PARTITIONS)
VIEWS = ("A", "B")
ROSTER_SOURCE_KNOWN_AT = "2023-05-05T03:50:21Z"
IDENTITY_RE = re.compile(r"[0-9a-f]{64}\Z")
TEAM_KEY_RE = re.compile(r"org:([1-9][0-9]{0,11})\Z")
TEAM_SELECTOR_RE = re.compile(r"(?:org:)?([0-9]{1,12})\Z")
CONTEST_SELECTOR_RE = re.compile(r"(?:ncaa:)?([0-9]{1,12})\Z")
CONTEST_KEY_RE = re.compile(r"ncaa:[0-9]{1,12}\Z")
TEAM_ID_RE = re.compile(r"team_[0-9a-f]{32}\Z")
DATE_RE = re.compile(r"(19|20)[0-9]{2}-[01][0-9]-[0-3][0-9]\Z")
DEC12_RE = re.compile(r"-?(0|[1-9][0-9]{0,15})\.[0-9]{12}\Z")
#: Count fields are bounded to their natural domain before any arithmetic (a forged huge integer is refused, never
#: converted to binary64).
COUNT_BOUND = 100_000
HISTORY_BOUND = 1_000

LABELS = {
    "evidence_label": "RETROSPECTIVE_RESEARCH",
    "association_authority": "POSTHOC_ROSTER_ASSOCIATION_NOT_FORECAST",
    "trust_state": "UNTRUSTED_SHADOW",
    "pit_eligibility": "PIT_NOT_ADMITTED",
    "calibration": "NOT_CALIBRATED",
    "predictive_skill": "NOT_ESTABLISHED",
    "forecast_status": "NOT_A_FORECAST",
    "roster_source_clock": "SOURCE_REPOSITORY_COMMIT_2023-05-05T03:50:21Z_OBSERVED_AFTER_EVERY_STUDY_GAME",
    "roster_meaning": "SEASON_ROSTER_SET_RATES_NOT_AVAILABILITY_HEALTH_DEPTH_TALENT_ELIGIBILITY_OR_TRANSFER_CHRONOLOGY",
    "history_clock": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME",
    "parent_eligibility": "PARENT_TARGET_GAME_FEATURE_PROTECTED_AND_PIT_FLAGS_UNCHANGED_FALSE",
    "comparison_2021_2022": "ALREADY_EXPOSED_RETROSPECTIVE_DEVELOPMENT_COMPARISON_NOT_BLIND",
    "fit_authority": "TP61_TWO_FROZEN_POSTHOC_RESEARCH_FITS_2016_2020_ONLY",
    "champion": "NO_CHAMPION_SELECTED",
    "causal_interpretation": "NO_CAUSAL_PERSONNEL_CONCLUSION",
    "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
    "selection": "EXPLICIT_PERSONNEL_ASSOCIATION_SELECTION_ONLY_NEVER_A_DEFAULT",
}
#: Labels every record carries (the rest are release-level labels in meta and every response).
RECORD_LABEL_KEYS = ("evidence_label", "association_authority", "trust_state", "pit_eligibility", "predictive_skill")
RECORD_LABELS = {k: LABELS[k] for k in RECORD_LABEL_KEYS}

# --------------------------------------------------------------------------------------------- models

MODEL_NULL = bm.MODEL_NULL
MODEL_SMOOTHED = bm.MODEL_SMOOTHED
MODEL_HISTORY = "POSTHOC_HISTORY_L2_V1"
MODEL_ROSTER = "POSTHOC_HISTORY_ROSTER_L2_V1"
MODEL_IDS = (MODEL_NULL, MODEL_SMOOTHED, MODEL_HISTORY, MODEL_ROSTER)
FIXED_MODELS = (MODEL_NULL, MODEL_SMOOTHED)
FITTED_MODELS = (MODEL_HISTORY, MODEL_ROSTER)
HISTORY_COLUMN = "history_log_odds_difference"
ROSTER_COLUMNS = ("roster_retention_rate_difference", "roster_jaccard_difference", "roster_arrival_rate_difference")
COLUMNS = {MODEL_HISTORY: (HISTORY_COLUMN,), MODEL_ROSTER: (HISTORY_COLUMN, *ROSTER_COLUMNS)}
RATE_FIELDS = (("roster_retention_rate", "returning_roster_count", "prior_roster_count"),
               ("roster_jaccard", "returning_roster_count", "union_roster_count"),
               ("roster_arrival_rate", "arrival_roster_count", "current_roster_count"))
SHARE_FIELDS = ("defensive_interceptions_returning_share", "passing_yards_returning_share",
                "receptions_returning_share", "receiving_yards_returning_share", "rushing_carries_returning_share",
                "rushing_yards_returning_share")
SIGNED_SHARE_FIELDS = ("passing_yards_returning_share", "receiving_yards_returning_share",
                       "rushing_yards_returning_share")
SIGNED_SEMANTICS = "SIGNED_EVENT_SUM_RATIO_UNCLIPPED_NOT_A_PROBABILITY_NOT_A_MODEL_COLUMN"
BOUNDED_SEMANTICS = "BOUNDED_NONNEGATIVE_COUNT_SHARE_NOT_A_MODEL_COLUMN"
LOG_CLIP = 1e-15
CLIP_CONVENTION = "CLIPPED_LOG_ARGUMENT_1E-15"
DESIGN = {
    "history_log_odds": "ell_s = math.log(2*wins_s + ties_s + 2) - math.log(2*losses_s + ties_s + 2) with the integer "
                        "arguments formed exactly and the two binary64 logarithms of the pinned CPython subtracted once "
                        "(the logit of the unchanged C47 smoothed q_s = (W + T/2 + 1)/(G + 2))",
    "history_counts": "the accepted C56 feature record's same-season, strictly earlier-date wins, losses, ties and games "
                      "of each side, the target excluded, with the contributing contest keys retained as lineage",
    "history_column": "ell_team - ell_opponent (one binary64 subtraction)",
    "roster_rates": "retention = returning/prior, Jaccard = returning/union, arrival = arrival/current: Python float "
                    "division of the two integers (correctly rounded), each with a positive denominator; the parent's "
                    "stored rate must equal it exactly",
    "roster_columns": "team rate minus opponent rate for retention, Jaccard and arrival, in that order (one binary64 "
                      "subtraction each)",
    "orientation": "view A is the canonical (parent a) side; view B's team-minus-opponent columns are the exact "
                   "negations of A's",
    "missing": "a side without a joinable same-season summary has a null roster block, never zeros; the game is outside "
               "common support and every model abstains",
    "excluded_from_design": ["signed passing/receiving/rushing yardage ratios", "count shares", "any composite",
                             "site", "intercept", "talent, availability, transfer, NIL, weather, film or market proxy"],
}
MODELS: dict[str, dict[str, Any]] = {
    MODEL_NULL: bm.MODELS[MODEL_NULL],
    MODEL_SMOOTHED: bm.MODELS[MODEL_SMOOTHED],
    MODEL_HISTORY: {
        "model_id": MODEL_HISTORY, "version": 1, "family": "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_POSTHOC_RESEARCH",
        "output": "WIN_PROBABILITY", "columns": list(COLUMNS[MODEL_HISTORY]),
        "formula": "p_A = sigmoid(z . beta), z the FIT-RMS-scaled A-minus-B design, zero intercept",
        "objective": "mean weighted binary cross-entropy over the paired FIT rows (weight 1/2 each) plus (1/2) "
                     "sum(beta_j^2) (lambda 1, every column)",
        "solver": {"interface": rf.VERSION, "function": "aggie_analytics.retrospective_baseline.reference_fit."
                                                         "fit_logistic (unchanged)",
                   "lambda": 1, "max_newton_steps": rf.MAX_NEWTON_STEPS, "gradient_inf_norm_tolerance": "1e-10",
                   "max_halvings": rf.MAX_HALVINGS, "start": "zero"},
        "fit_seasons": list(FIT_SEASONS), "labels_used": ["DECISIVE"], "fitted": True, "intercept": None,
        "site_variable": None, "role": "FROZEN_POSTHOC_HISTORY_CONTROL"},
    MODEL_ROSTER: {
        "model_id": MODEL_ROSTER, "version": 1, "family": "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_POSTHOC_RESEARCH",
        "output": "WIN_PROBABILITY", "columns": list(COLUMNS[MODEL_ROSTER]),
        "formula": "p_A = sigmoid(z . beta), z the FIT-RMS-scaled A-minus-B design, zero intercept",
        "objective": "mean weighted binary cross-entropy over the paired FIT rows (weight 1/2 each) plus (1/2) "
                     "sum(beta_j^2) (lambda 1, every column)",
        "solver": {"interface": rf.VERSION, "function": "aggie_analytics.retrospective_baseline.reference_fit."
                                                         "fit_logistic (unchanged)",
                   "lambda": 1, "max_newton_steps": rf.MAX_NEWTON_STEPS, "gradient_inf_norm_tolerance": "1e-10",
                   "max_halvings": rf.MAX_HALVINGS, "start": "zero"},
        "fit_seasons": list(FIT_SEASONS), "labels_used": ["DECISIVE"], "fitted": True, "intercept": None,
        "site_variable": None, "role": "FROZEN_POSTHOC_HISTORY_PLUS_ROSTER_RATE_ASSOCIATION"},
}
SCALING = {"rule": "scale_j = math.sqrt(math.fsum(0.5 * x_ij * x_ij for every paired FIT row i, A then B, in canonical "
                   "game order) / N_fit_games); no centering (odd orientation symmetry preserved); a zero scale is 1 "
                   "and the column is marked constant; z_ij = x_ij / scale_j",
           "rows": "the FIT cohort only (common-support 2016-2020 games with a DECISIVE label); never a comparison "
                   "season, never transductive",
           "shared": "both fitted models use the same history-column scale"}
FIT_RULE = {"cohort": "common-support games of 2016-2020 whose accepted label is DECISIVE",
            "rows": "per game the A row (z, y_A) and the B row (-z, 1 - y_A), each of weight 1/2",
            "failure": "a refused fit (FIT_EMPTY, FIT_RAGGED, FIT_NONFINITE_INPUT, FIT_NONFINITE, FIT_NOT_CONVERGED, "
                       "FIT_SINGULAR, FIT_BACKTRACK_EXHAUSTED) is recorded with its trajectory as the parameter state; "
                       "that model then abstains on every game (ABSTAIN_FIT_FAILED); no constant is tuned afterwards",
            "comparison_years": "never in the fit, the scales, any constant or any selection"}
ESTIMATE_RULE = {
    "game_grain": "the A-orientation probability is built first; B is its exact complement",
    "fixed": {"NULL_HALF_V1": "exactly 1/2", "SMOOTHED_HISTORY_ODDS_V1": "the unchanged C47 exact rational "
              "q_A(1-q_B)/(q_A(1-q_B)+q_B(1-q_A)), q = (2W+T+2)/(2G+4), equal to the accepted C47 estimate record"},
    "fitted": "p_A = decimal12(rf.sigmoid(rf.linear(z_A, beta))); p_B = 1 - p_A exactly in decimal; the linear predictor "
              "decimal12 and both unrounded values as repr() text are kept",
    "support": "only common-support games are estimated; every other game abstains for all four models with "
               "ABSTAIN_OUTSIDE_COMMON_SUPPORT and the sides' reasons",
    "sample_state": {"fixed": "FIXED_MODEL_NOT_FITTED", "fit": "IN_SAMPLE_FIT_2016_2020_FITTED_DATA",
                     "comparison": "OUT_OF_FIT_EXPOSED_2021_2022_COMPARISON"},
}
SCORE_RULE = {
    "orientation": "A (the canonical game); each canonical game is counted once per model",
    "brier": "(p_A served - y_A)^2 as an exact rational of the served probability (fixed models: of their exact rational)",
    "log_loss": "-math.log(clip(q)) with q the correctly rounded binary64 of the exact served probability of the "
                "observed side, clip to [1e-15, 1 - 1e-15] applied only to the argument (CLIPPED_LOG_ARGUMENT_1E-15); "
                "repr() text",
    "unscored": {"ABSTAINED_OUTSIDE_COMMON_SUPPORT": "no estimate outside common support",
                 "ABSTAINED_FIT_FAILED": "a recorded fit failure", "LABEL_TIE": "a tie is never made decisive",
                 "LABEL_MISSING": "no accepted label", "LABEL_UNSUPPORTED": "an unsupported accepted label"},
}
SUMMARY_RULE = {
    "scopes": "SEASON 2016..2022, PARTITION FIT (2016-2020) and PARTITION COMPARISON (2021-2022); no pooled in-sample "
              "plus comparison mixture",
    "per_model": "score records, scored and unscored games by reason, Brier total and mean (exact rationals with "
                 "decimal12), log loss total (math.fsum in canonical game order) and mean (repr)",
    "fit_partition": "FIT-partition rows of the fitted models are fitted-data (in-sample) summaries",
    "comparisons": [[MODEL_ROSTER, MODEL_HISTORY], [MODEL_HISTORY, MODEL_NULL], [MODEL_ROSTER, MODEL_NULL],
                    [MODEL_SMOOTHED, MODEL_NULL]],
    "primary": "POSTHOC_HISTORY_ROSTER_L2_V1 minus POSTHOC_HISTORY_L2_V1 Brier mean on PARTITION COMPARISON "
               "(pooled 2021-2022), unfiltered: negative = lower descriptive Brier, zero = equal, positive = higher",
    "common_support": "every compared model has the identical scored game keys in each scope, except that a fitted "
                      "model whose frozen fit failed abstains on every game (ABSTAINED_FIT_FAILED, zero scored games) "
                      "and its comparisons carry no difference",
    "selection": "with any season/team/contest/partition selector the rows and comparisons are re-derived over exactly "
                 "the selected canonical games' verified score records; a scope without a selected game has no row; "
                 "--model keeps that model's rows and the comparisons whose subject is that model; paging follows "
                 "the calculation",
    "no_inference": "no significance, bootstrap, calibration, champion, causal or predictive-skill conclusion",
}
NUMERIC_CONTRACT = {
    "arithmetic": "IEEE-754 binary64 in a fixed order; every reduction math.fsum; math.log, math.exp, math.log1p and "
                  "math.sqrt of the pinned CPython 3.12.10",
    "decimal12": "a served binary64 value is its exact decimal expansion rounded half-even to 12 places (negative zero "
                 "normalized) as a JSON string; complements and negations are exact decimal operations",
    "rationals": "{numerator, denominator} JSON integers in lowest terms, denominator > 0",
    "floats": "binary64 rates, log-odds and design values are JSON numbers (finite; their repr round-trips exactly)",
    "counts": "JSON integers only, within their domain; a boolean or an integral float is not a count",
    "independent_tolerance": "an independent oracle agrees within 1e-9 absolute on scales, coefficients, objective and "
                             "probabilities and within 1e-8 on gradients; keys, counts, states, identities and exact "
                             "rationals agree exactly; byte identity of rebuilds is a separate property",
    "canonical_json": "json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) as UTF-8",
}
JOIN_RULE = {
    "key": "(target season, accepted C56 team key org:<id>) -> that exact C59 program-season <season>|org:<id>",
    "chain": "the program-season's chain_state must be QUALIFIED_EXACT_CHAIN",
    "summary": "its own returning_target_summary_key must name a C59 returning summary whose target season is the "
               "same football season (the parent's label, including its 2020 semantics) and whose canonical team is "
               "the chain's canonical team",
    "never": ["fuzzy or normalized names", "name borrowing across seasons", "coincident provider or NCAA numbers",
              "nearest-year fill", "an unqualified chain", "copied current-opponent context"],
}
QUALIFICATION_STATES = ("JOINABLE_SAME_SEASON_SUMMARY", "NO_SAME_SEASON_RETURNING_SUMMARY", "CHAIN_NOT_QUALIFIED",
                        "SUMMARY_LINK_MISMATCH")
SIDE_STATES = (*QUALIFICATION_STATES, "NO_PROGRAM_SEASON")
SUPPORT_STATES = ("COMMON_SUPPORT", "OUTSIDE_COMMON_SUPPORT")

# --------------------------------------------------------------------------------------------- record fields

#: Type codes: s str, s? str|null, i int, i? int|null, b bool, f float, f? float|null, ls list of str, lf list of float,
#: lf? list of float or null, q exact rational, q? rational|null, d decimal12 string, d? decimal12|null, li list of int,
#: j any JSON value (only members re-derived wholesale), @name / @name? a nested object of that spec (or null).
_LABEL_TYPES = {k: "s" for k in RECORD_LABEL_KEYS}
SUBSPECS: dict[str, dict[str, str]] = {
    "summary_block": {
        "summary_key": "s", "prior_season": "i", "target_season": "i", "canonical_team_id": "s",
        "canonical_team_label": "s?", "prior_roster_count": "i", "current_roster_count": "i",
        "returning_roster_count": "i", "departed_roster_count": "i", "arrival_roster_count": "i",
        "union_roster_count": "i", "roster_retention_rate": "f", "roster_jaccard": "f", "roster_arrival_rate": "f",
        "roster_retention_rate_exact": "q", "roster_jaccard_exact": "q", "roster_arrival_rate_exact": "q",
        "parent_rates_equal_recomputed": "b", "partial_prior_metric_season": "b", "source_known_at_utc": "s",
        "shares": "@shares", "share_outside_unit_interval": "@share_flags", "share_semantics": "@share_semantics",
        "component_keys": "ls", "missing_component_pairs": "ls", "census_scope_state": "s",
        "target_game_feature_eligible": "b", "protected_eligible": "b", "original_transition_time_pit_eligible": "b",
        "summary_record_sha256": "s", "original_feature_identity": "s"},
    "shares": {field: "f?" for field in SHARE_FIELDS},
    "share_flags": {field: "b?" for field in SHARE_FIELDS},
    "share_semantics": {field: "s" for field in SHARE_FIELDS},
    "history": {"games": "i", "wins": "i", "losses": "i", "ties": "i", "cold_start": "b",
                "contributing_contest_keys": "ls", "log_odds": "f"},
    "roster": {"qualification_key": "s", "summary_key": "s", "prior_season": "i", "partial_prior_metric_season": "b",
               "source_known_at_utc": "s", "prior_roster_count": "i", "current_roster_count": "i",
               "returning_roster_count": "i", "arrival_roster_count": "i", "union_roster_count": "i",
               "roster_retention_rate": "f", "roster_jaccard": "f", "roster_arrival_rate": "f"},
}
FIELD_TYPES: dict[str, dict[str, str]] = {
    "qualifications": {
        "record_type": "s", "qualification_key": "s", "season": "i", "team_key": "s", "org_id": "s", "division": "s",
        "divisions": "ls", "team_names": "ls", "chain_state": "s", "canonical_team_id": "s?",
        "returning_target_summary_key": "s?", "coverage_state": "s", "roster_presence": "s",
        "transition_presence": "s", "qualification_state": "s", "qualification_reasons": "ls",
        "summary": "@summary_block?", "study_views": "i", "study_joined_views": "i", "study_common_support_games": "i",
        "study_fit_games": "i", "study_comparison_games": "i", "program_season_record_sha256": "s",
        "personnel_release_identity": "s", **_LABEL_TYPES},
    "features": {
        "record_type": "s", "feature_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
        "partition": "s", "view": "s", "team_key": "s", "team_name": "s", "team_org_id": "s", "opponent_key": "s",
        "opponent_name": "s", "opponent_org_id": "s", "team_history": "@history", "opponent_history": "@history",
        "history_log_odds_difference": "f", "team_qualification_key": "s?", "opponent_qualification_key": "s?",
        "team_side_state": "s", "opponent_side_state": "s", "team_roster": "@roster?", "opponent_roster": "@roster?",
        "roster_rate_differences": "lf?", "support_state": "s", "abstention_reasons": "ls",
        "design_history": "lf?", "design_history_roster": "lf?", "target_excluded_from_history": "b",
        "reference_feature_record_sha256": "s", "reference_identity": "s", **_LABEL_TYPES},
    "estimates": {
        "record_type": "s", "estimate_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
        "partition": "s", "model_id": "s", "model_sha256": "s", "orientation": "s", "team_key": "s",
        "team_name": "s", "opponent_key": "s", "opponent_name": "s", "estimate_state": "s", "abstention_reason": "s?",
        "sample_state": "s", "probability": "d?", "probability_exact": "q?", "opponent_probability": "d?",
        "opponent_probability_exact": "q?", "game_grain_probability_a_exact": "q?", "linear_predictor": "d?",
        "linear_predictor_repr": "s?", "probability_repr": "s?", "team_strength_q": "q?",
        "opponent_strength_q": "q?", "c47_estimate_record_sha256": "s?", "feature_record_sha256": "s",
        "game_feature_record_sha256": "s", **_LABEL_TYPES},
    "parameters": {
        "record_type": "s", "parameter_key": "s", "model_id": "s", "model_sha256": "s", "definition": "j",
        "fitted": "b", "parameter_state": "s", "columns": "ls", "coefficients": "j", "coefficients_repr": "j",
        "scales": "j", "scales_repr": "j", "constant_columns": "ls", "convergence": "j", "training": "j",
        "penalty": "j", "trajectory": "j", **_LABEL_TYPES},
    "scores": {
        "record_type": "s", "score_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
        "partition": "s", "model_id": "s", "model_sha256": "s", "orientation": "s", "a_key": "s", "b_key": "s",
        "a_team_name": "s", "b_team_name": "s", "sample_state": "s", "estimate_state": "s", "label_state": "s",
        "y_a": "i?", "score_state": "s", "unscored_reason": "s?", "probability_a": "d?", "probability_a_exact": "q?",
        "brier": "q?", "brier_decimal": "d?", "log_loss": "s?", "log_loss_convention": "s",
        "estimate_record_sha256": "s", "label_record_sha256": "s", **_LABEL_TYPES},
    "summary": {
        "record_type": "s", "summary_key": "s", "population": "j", "rows": "j", "comparisons": "j",
        "primary_comparison": "j", **_LABEL_TYPES},
}
RECORD_TYPES = {"qualifications": "PERSONNEL_QUALIFICATION", "features": "PERSONNEL_FEATURE",
                "estimates": "PERSONNEL_ESTIMATE", "parameters": "PERSONNEL_PARAMETER", "scores": "PERSONNEL_SCORE",
                "summary": "PERSONNEL_SUMMARY"}
RECORD_TABLES = ("qualifications", "features", "estimates", "parameters", "scores", "summary")
SEASONAL_TABLES = ("qualifications", "features", "estimates", "scores")
KEY_FIELDS = {"qualifications": "qualification_key", "features": "feature_key", "estimates": "estimate_key",
              "parameters": "parameter_key", "scores": "score_key", "summary": "summary_key"}
ORDERING = {
    "qualifications": "season, numeric ncaa org id",
    "features": "season, contest_date, contest_key, view (A then B)",
    "estimates": "season, contest_date, contest_key, model (NULL, SMOOTHED, HISTORY, ROSTER), orientation (A then B)",
    "parameters": "model (NULL, SMOOTHED, HISTORY, ROSTER)",
    "scores": "season, contest_date, contest_key, model",
    "summary": "one record",
}
LAYOUT = {
    "grains": {"qualifications": "one record per C59 program-season (<season>|org:<id>), all 1,760",
               "features": "one record per accepted 2016-2022 target view (<contest_key>|<view>)",
               "estimates": "one record per target, model and orientation (<contest_key>|<model>|<orientation>)",
               "parameters": "one record per model (<model>)",
               "scores": "one A-oriented record per target and model (<contest_key>|<model>)",
               "summary": "one record (summary)"},
    "ordering": ORDERING,
    "serialization": "canonical JSON lines (sorted keys, separators ',' ':', UTF-8, no ASCII escaping); one zlib "
                     "level-9 block per seasonal table and season, one GLOBAL block each for parameters and summary",
    "database": {"ddl": [["table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"],
                         ["table", "blocks", "CREATE TABLE blocks (ord INTEGER PRIMARY KEY, record_table TEXT NOT NULL, "
                                             "segment TEXT NOT NULL, records INTEGER NOT NULL, first_key TEXT, "
                                             "last_key TEXT, lines_sha256 TEXT NOT NULL, block BLOB NOT NULL)"]],
                 "block_layout": [*[[t, str(s)] for t in SEASONAL_TABLES for s in STUDY_SEASONS],
                                  ["parameters", "GLOBAL"], ["summary", "GLOBAL"]],
                 "page_size": 4096, "journal_mode": "OFF", "file": DB_FILE},
    "identity_documents": {
        "content": ["schema", "stage", "population", "contract_id", "contract_sha256", "inputs", "parent_contracts",
                    "rules_sha256", "payload_schema", "row_counts", "lines_sha256", "blocks"],
        "database": ["schema", "stage", "population", "contract_sha256", "content_identity", "db_schema_version",
                     "outputs", "table_counts"],
        "identity": "SHA-256 of the canonical JSON bytes of the document; compared as canonical bytes, never by Python "
                    "equality (an integral float, a boolean or an extra member differs)",
        "location": "<root>/canonical/national_personnel_association_2016_2022/sha256/<database identity>/"
                    "national_personnel_association.sqlite; manifest at <root>/manifests/"
                    "national_personnel_association_2016_2022/sha256/<database identity>/run_manifest.json with "
                    "members identity, identity_document, content_identity, content_document and provenance; "
                    "create-only (identical rebuild ALREADY_PRESENT_IDENTICAL, differing bytes "
                    "REFUSED_IMMUTABLE_COLLISION)"},
    "checkpoint_unit": "one study season: its qualification, feature, estimate and score lines; parameters and the "
                       "summary follow",
}
GRAINS = {"personnel-qualification": "qualifications", "personnel-feature": "features",
          "personnel-estimate": "estimates", "personnel-parameter": "parameters", "personnel-score": "scores",
          "personnel-summary": "summary"}
#: TP61 section 4: the complete applicable-selector matrix; any other selector on a grain is refused
#: (FILTER_NOT_APPLICABLE), never ignored.
SELECTOR_MATRIX = {
    "personnel-qualification": ["season", "team"],
    "personnel-feature": ["season", "team", "contest", "partition"],
    "personnel-estimate": ["season", "team", "contest", "model", "partition"],
    "personnel-parameter": ["model"],
    "personnel-score": ["season", "team", "contest", "model", "partition"],
    "personnel-summary": ["season", "team", "contest", "model", "partition"],
}
SELECTORS = {
    "season": "an integer; the study seasons are 2016-2022 (any other season serves no row with "
              "SEASON_OUTSIDE_RELEASE; 2023 is never a study season)",
    "team": "org:<1-12 digits> or bare digits (the accepted C56/C59 team key), or an exact team name the record's own "
            "season carries for that team (never borrowed across seasons); an unknown valid team serves no row",
    "contest": "an exact accepted contest key ncaa:<digits> (bare digits read as ncaa:<digits>); an unknown valid "
               "contest serves no row",
    "model": "one of NULL_HALF_V1, SMOOTHED_HISTORY_ODDS_V1, POSTHOC_HISTORY_L2_V1, POSTHOC_HISTORY_ROSTER_L2_V1",
    "partition": "FIT (2016-2020) or COMPARISON (2021-2022)",
    "paging": "--limit (default 50, non-negative), --offset (non-negative) or --all; exact totals in record order; "
              "summary paging follows its calculation",
    "intersection": "every applicable supplied selector applies and they intersect; an unknown or disjoint valid "
                    "selection serves no row, summaries included (never a fabricated zero-count summary)",
    "pit": "--require-pit is always refused; no historical as-of selector exists",
    "matrix": SELECTOR_MATRIX,
}
SCOPE = {
    "population": "all 5,087 accepted C56 2016-2022 targets (10,174 oriented views) and all 1,760 C59 2016-2022 "
                  "program-seasons; the common cohort is the games whose two participants both bind a same-season "
                  "summary",
    "fit_and_comparison": "FIT 2016-2020 (fitted-data summaries), COMPARISON 2021-2022 (already exposed)",
    "not_in_scope": "2023 study rows or scores, 2024/2025 protected seasons, prospective or production training, "
                    "forecasts, availability, talent, transfers, coaching, weather, film, market, NIL and A&M "
                    "specialization",
}
TABLE_LABELS = {"qualifications": "QUALIFICATION", "features": "FEATURE", "estimates": "ESTIMATE",
                "parameters": "PARAMETER", "scores": "SCORE", "summary": "SUMMARY"}
#: TP61 section 4 error semantics: every refusal is exit 2 with one JSON line {"refused": CODE, "error": text} on
#: stderr and no row; checks run in a fixed order so each forgery is refused for its own cause.
REFUSALS = {
    "exit_code": 2,
    "stderr": "one JSON object with members refused (the code) and error (the text); nothing on stdout",
    "selection": ["ARGUMENT_INVALID", "UNKNOWN_GRAIN", "FILTER_NOT_APPLICABLE", "SEASON_INVALID", "TEAM_INVALID",
                  "CONTEST_INVALID", "MODEL_INVALID", "PARTITION_INVALID", "LIMIT_INVALID", "OFFSET_INVALID",
                  "NEGATIVE_LIMIT", "NEGATIVE_OFFSET", "ASSOCIATION_PIT_NOT_ADMITTED", "ASSOCIATION_MODE_CONFLICT",
                  "STALE_ASSOCIATION_IDENTITY"],
    "location": ["DATABASE_LOCATION_UNSUPPORTED", "DATABASE_LOCATION_NOT_LITERAL",
                 "ASSOCIATION_MANIFEST_LOCATION_UNSUPPORTED", "ASSOCIATION_MANIFEST_LOCATION_NOT_LITERAL",
                 "ASSOCIATION_DATABASE_MISSING", "ASSOCIATION_LOCATION_INVALID", "ASSOCIATION_MANIFEST_MISSING",
                 "ASSOCIATION_DATABASE_UNREADABLE"],
    "manifest_and_identity": ["ASSOCIATION_MANIFEST_MALFORMED", "ASSOCIATION_IDENTITY_MISMATCH",
                              "ASSOCIATION_SCHEMA_UNSUPPORTED", "ASSOCIATION_IDENTITY_DOCUMENT_MISMATCH",
                              "ASSOCIATION_DATABASE_TAMPERED", "ASSOCIATION_CONTRACT_MISMATCH",
                              "ASSOCIATION_CONTENT_IDENTITY_MISMATCH", "ASSOCIATION_PROFILE_MISMATCH"],
    "meta": ["ASSOCIATION_META_MISMATCH", "ASSOCIATION_META_MALFORMED", "ASSOCIATION_PIT_CLAIM_INVALID",
             "ASSOCIATION_LABEL_CLAIM_INVALID", "ASSOCIATION_PARENT_MISMATCH", "ASSOCIATION_RULES_CLAIM_INVALID",
             "ASSOCIATION_COUNT_MISMATCH"],
    "blocks_and_records": ["ASSOCIATION_INDEX_MISMATCH", "ASSOCIATION_RECORD_TYPE_INVALID",
                           "ASSOCIATION_RECORD_MALFORMED", "ASSOCIATION_RECORD_SHAPE_INVALID",
                           "ASSOCIATION_FIELD_TYPE_INVALID", "ASSOCIATION_RECORD_NOT_CANONICAL"],
    "collections": ["ASSOCIATION_DUPLICATE_ROW", "ASSOCIATION_ORDER_MISMATCH",
                    *[f"ASSOCIATION_{label}_{kind}" for label in TABLE_LABELS.values()
                      for kind in ("ROW_MISSING", "ROW_EXTRA", "KEYS_MISMATCH")]],
    "rules": ["ASSOCIATION_KEY_MISMATCH", "ASSOCIATION_SEASON_OUT_OF_RANGE", "ASSOCIATION_PARTITION_MISMATCH",
              "ASSOCIATION_COUNT_OUT_OF_DOMAIN", "ASSOCIATION_PARENT_ELIGIBILITY_PROMOTED",
              "ASSOCIATION_SOURCE_CLOCK_INVALID", "ASSOCIATION_QUALIFICATION_STATE_INVALID",
              "ASSOCIATION_SET_COUNTS_INCOHERENT", "ASSOCIATION_RATE_MISMATCH", "ASSOCIATION_SIGNED_SHARE_CLIPPED",
              "ASSOCIATION_SHARE_SEMANTICS_INVALID", "ASSOCIATION_INVOLVEMENT_MISMATCH",
              "ASSOCIATION_HISTORY_INCOHERENT", "ASSOCIATION_HISTORY_LEAKAGE", "ASSOCIATION_LOG_ODDS_MISMATCH",
              "ASSOCIATION_ORIENTATION_MISMATCH", "ASSOCIATION_JOIN_MISMATCH", "ASSOCIATION_MISSING_AS_ZERO",
              "ASSOCIATION_SUPPORT_MISMATCH", "ASSOCIATION_DESIGN_MISMATCH", "ASSOCIATION_LABEL_INCONSISTENT",
              "ASSOCIATION_PARAMETER_MISMATCH", "ASSOCIATION_COMPLEMENT_INVALID", "ASSOCIATION_ESTIMATE_MISMATCH",
              "ASSOCIATION_SCORE_MISMATCH", "ASSOCIATION_SUMMARY_MISMATCH", "ASSOCIATION_COMMON_SUPPORT_INVALID"],
    "malformed_json_reasons": ["JSON_LONE_SURROGATE", "JSON_NESTING_TOO_DEEP", "JSON_NONFINITE_NUMBER",
                               "JSON_INTEGER_TOO_LONG"],
    "build_inputs": ["ASSOCIATION_DATA_ROOT_MISSING", "ASSOCIATION_DATA_ROOT_LOCATION_UNSUPPORTED",
                     "ASSOCIATION_DATA_ROOT_LOCATION_NOT_LITERAL", "ASSOCIATION_INPUT_LOCATION_UNSUPPORTED",
                     "ASSOCIATION_INPUT_LOCATION_NOT_LITERAL", "ASSOCIATION_INPUT_MISSING",
                     "ASSOCIATION_INPUT_TAMPERED", "ASSOCIATION_PARENT_REFUSED", "ASSOCIATION_PARENT_IDENTITY_MISMATCH",
                     "ASSOCIATION_INPUT_POPULATION_DRIFT", "ASSOCIATION_INPUT_INVALID"],
}


class AssociationError(ValueError):
    """A refused build input or a refused association release; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise AssociationError(code, message)


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


def _nesting_refusal(code: str, where: str) -> AssociationError:
    return AssociationError(code, f"{where}: {JSON_NESTING_TOO_DEEP} (deeper than the JSON decoder or encoder accepts)")


def loads_untrusted(text: Any, code: str, where: str, non_json_code: str | None = None) -> Any:
    """Decode JSON from the release: NaN, Infinity, a float literal beyond binary64 range and an integer beyond the
    interpreter's digit limit are malformed data refused with ``code`` and their reason (never a traceback); nesting
    beyond the decoder's depth is refused; other syntax errors are refused with ``non_json_code`` (default ``code``)."""
    try:
        return json.loads(text, parse_float=_finite_float, parse_constant=_no_constant)
    except _InvalidNumber as exc:
        raise AssociationError(code, f"{where}: {JSON_NONFINITE_NUMBER} ({exc})") from exc
    except RecursionError as exc:
        raise _nesting_refusal(code, where) from exc
    except ValueError as exc:
        if "integer string conversion" in str(exc) or "Exceeds the limit" in str(exc):
            raise AssociationError(code, f"{where}: {JSON_INTEGER_TOO_LONG}") from exc
        raise AssociationError(non_json_code or code, f"{where}: not JSON ({exc})") from exc


def _untrusted_canonical(value: Any, code: str, where: str) -> bytes:
    try:
        return canonical_json_bytes(value)
    except UnicodeEncodeError as exc:
        raise AssociationError(code, f"{where}: {JSON_LONE_SURROGATE} (U+{ord(exc.object[exc.start]):04X} is not "
                                     "Unicode text)") from exc
    except RecursionError as exc:
        raise _nesting_refusal(code, where) from exc
    except ValueError as exc:  # a non-finite float can only come from untrusted text the decoder already refused
        raise AssociationError(code, f"{where}: {JSON_NONFINITE_NUMBER} ({exc})") from exc


def _json_or_none(text: Any, name: str = "") -> Any:
    if not isinstance(text, (str, bytes)):
        return None
    try:
        return loads_untrusted(text, "ASSOCIATION_META_MALFORMED", f"meta {name}", non_json_code="NOT_JSON")
    except AssociationError as exc:
        if exc.code == "NOT_JSON":
            return None
        raise


# --------------------------------------------------------------------------------------------- numeric helpers

_QUANTUM = Decimal("0.000000000001")


def dec12(value: float) -> str:
    """A binary64 value's exact decimal expansion rounded half-even to 12 places (negative zero normalized)."""
    if type(value) is not float or not math.isfinite(value):
        _refuse("ASSOCIATION_DESIGN_MISMATCH", f"{value!r} is not a finite binary64 value")
    with localcontext() as ctx:
        ctx.prec = 80
        quantized = Decimal(value).quantize(_QUANTUM, rounding=ROUND_HALF_EVEN)
    if quantized == 0:
        quantized = abs(quantized)
    return format(quantized, "f")


def dec_complement(text: str) -> str:
    with localcontext() as ctx:
        ctx.prec = 80
        value = (Decimal(1) - Decimal(text)).quantize(_QUANTUM)
    return format(abs(value) if value == 0 else value, "f")


def dec_negation(text: str) -> str:
    with localcontext() as ctx:
        ctx.prec = 80
        value = (-Decimal(text)).quantize(_QUANTUM)
    return format(abs(value) if value == 0 else value, "f")


def dec_fraction(text: str) -> Fraction:
    return Fraction(Decimal(text))


def rational(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def frac(value: dict[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def decimal_text(value: Fraction) -> str:
    """An exact rational rounded half-even to 12 places by integer arithmetic (negative zero normalized)."""
    text = bm.decimal_text(value, 12)
    return "0.000000000000" if text == "-0.000000000000" else text


def history_log_odds(wins: int, losses: int, ties: int) -> float:
    """ell = log(2W + T + 2) - log(2L + T + 2): the smoothed C47 strength's logit in the pinned operation order."""
    return math.log(2 * wins + ties + 2) - math.log(2 * losses + ties + 2)


def strength_q(wins: int, ties: int, games: int) -> Fraction:
    """The unchanged C47 q = (2W + T + 2) / (2G + 4)."""
    return Fraction(2 * wins + ties + 2, 2 * games + 4)


def smoothed_probability(q_a: Fraction, q_b: Fraction) -> Fraction:
    numerator = q_a * (1 - q_b)
    return numerator / (numerator + q_b * (1 - q_a))


def log_loss_value(p_a: Fraction, y: int) -> float:
    q = p_a if y == 1 else 1 - p_a
    clipped = min(max(float(q), LOG_CLIP), 1.0 - LOG_CLIP)
    return -math.log(clipped)


def model_sha256(model_id: str) -> str:
    return sha256_bytes(canonical_json_bytes(MODELS[model_id]))


def partition_of(season: int) -> str:
    return "FIT" if season in FIT_SEASONS else "COMPARISON"


def sample_state(model_id: str, season: int) -> str:
    if model_id in FIXED_MODELS:
        return ESTIMATE_RULE["sample_state"]["fixed"]
    return ESTIMATE_RULE["sample_state"]["fit" if season in FIT_SEASONS else "comparison"]


def keys_sha256(keys: Iterable[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


def rules_document() -> dict[str, Any]:
    """Every frozen rule the contract restates (the meta ``rules`` claim and the content document's rules digest), as a
    fresh deep copy so no caller can alias and alter the module's frozen constants."""
    return copy.deepcopy({"labels": LABELS, "record_labels": list(RECORD_LABEL_KEYS), "seasons": {
        "study": list(STUDY_SEASONS), "fit": list(FIT_SEASONS), "comparison": list(COMPARISON_SEASONS)},
        "roster_source_known_at_utc": ROSTER_SOURCE_KNOWN_AT, "models": MODELS,
        "model_sha256": {m: model_sha256(m) for m in MODEL_IDS}, "columns": {m: list(c) for m, c in COLUMNS.items()},
        "design": DESIGN, "scaling": SCALING, "fit": FIT_RULE, "estimates": ESTIMATE_RULE, "scores": SCORE_RULE,
        "summary": SUMMARY_RULE, "numeric": NUMERIC_CONTRACT, "join": JOIN_RULE,
        "qualification_states": list(QUALIFICATION_STATES), "side_states": list(SIDE_STATES),
        "support_states": list(SUPPORT_STATES), "rate_fields": [list(r) for r in RATE_FIELDS],
        "share_fields": list(SHARE_FIELDS), "signed_share_fields": list(SIGNED_SHARE_FIELDS),
        "share_semantics": {"signed": SIGNED_SEMANTICS, "bounded": BOUNDED_SEMANTICS},
        "count_bounds": {"roster": COUNT_BOUND, "history": HISTORY_BOUND},
        "log_clip": repr(LOG_CLIP), "clip_convention": CLIP_CONVENTION, "layout": LAYOUT,
        "field_types": FIELD_TYPES, "subspecs": SUBSPECS, "record_types": RECORD_TYPES,
        "grains": GRAINS, "selectors": SELECTORS, "refusals": REFUSALS, "scope": SCOPE})


def rules_sha256() -> str:
    return sha256_bytes(canonical_json_bytes(rules_document()))


from aggie_analytics.retrospective_baseline.personnel_association_anchors import (  # noqa: E402
    ANCHORS, ASSOCIATION_PROFILE)

# --------------------------------------------------------------------------------------------- build inputs

INPUT_NAMES = ("reference_database", "reference_manifest", "history_database", "population_database",
               "personnel_database", "personnel_manifest")


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
        raise AssociationError(f"{code_prefix}_LOCATION_{suffix}", exc.detail) from exc


def resolve_inputs(data_root: Path, anchors: dict[str, Any]) -> dict[str, Path]:
    """Each pinned parent file under the explicitly named data root, refused unless present with its pinned SHA-256.
    The root and every resolved location pass the BAT-717 literal local-file policy before any access."""
    root = Path(_literal(Path(data_root), "ASSOCIATION_DATA_ROOT"))
    if not _io_path(root).is_dir():
        _refuse("ASSOCIATION_DATA_ROOT_MISSING", f"no data root directory at {data_root}")
    paths: dict[str, Path] = {}
    for name in INPUT_NAMES:
        spec = anchors["inputs"][name]
        location = Path(_literal(root / Path(*spec["relative_path"].split("/")), "ASSOCIATION_INPUT"))
        if not _io_path(location).is_file():
            _refuse("ASSOCIATION_INPUT_MISSING", f"{name}: no file at {location}")
        actual = sha256_file(_io_path(location))
        if actual != spec["sha256"]:
            _refuse("ASSOCIATION_INPUT_TAMPERED", f"{name}: bytes hash to {actual}, the contract pins {spec['sha256']}")
        paths[name] = location
    return paths


def load_inputs(data_root: Path, anchors: dict[str, Any], *, input_order: str = "natural") -> dict[str, Any]:
    """The accepted parents, each verified completely by its accepted reader (the C56 reader re-derives the reference
    from the history and population it binds; the C59 reader verifies every personnel record, collection, rule and
    identity) and pinned to the contract's identities; ``input_order`` permutes every loaded collection before the
    derivation (which indexes by key and orders canonically, so no variant may change a byte)."""
    from aggie_analytics.personnel_evidence import evidence as pe  # noqa: PLC0415 - build inputs only
    from aggie_analytics.retrospective_baseline import reference as rc  # noqa: PLC0415 - build inputs only

    paths = resolve_inputs(data_root, anchors)
    pins = anchors["inputs"]
    try:
        with rc.ReferenceComparison(paths["reference_database"], history_database=paths["history_database"],
                                    population_database=paths["population_database"],
                                    manifest=paths["reference_manifest"]) as reference:
            ref_identity = (reference.database_identity, reference.content_identity)
            derived = reference.derived
            lines = derived["lines"]
            features = [(r, l) for r, l in zip(derived["features"], lines["features"]) if r["season"] in STUDY_SEASONS]
            labels = [(r, l) for r, l in zip(derived["labels"], lines["labels"]) if r["season"] in STUDY_SEASONS]
            c47 = [(r, l) for r, l in zip(derived["estimates"], lines["estimates"])
                   if r["season"] in STUDY_SEASONS and r["model_id"] in FIXED_MODELS]
    except rc.ReferenceError as exc:
        raise AssociationError("ASSOCIATION_PARENT_REFUSED", f"the accepted C56 reader refused: {exc}") from exc
    try:
        with pe.PersonnelEvidence(paths["personnel_database"], manifest=paths["personnel_manifest"]) as personnel:
            per_identity = (personnel.database_identity, personnel.content_identity)
            records, plines = personnel.records, personnel.records["lines"]
            programs = list(zip(records["program_seasons"], plines["program_seasons"]))
            summaries = list(zip(records["summaries"], plines["summaries"]))
            components = list(zip(records["components"], plines["components"]))
    except pe.PersonnelError as exc:
        raise AssociationError("ASSOCIATION_PARENT_REFUSED", f"the accepted C59 reader refused: {exc}") from exc
    if ref_identity != (pins["reference_database"]["identity"], pins["reference_database"]["content_identity"]):
        _refuse("ASSOCIATION_PARENT_IDENTITY_MISMATCH", f"reference identity {ref_identity} is not the pinned parent")
    if per_identity != (pins["personnel_database"]["identity"], pins["personnel_database"]["content_identity"]):
        _refuse("ASSOCIATION_PARENT_IDENTITY_MISMATCH", f"personnel identity {per_identity} is not the pinned parent")
    return {"paths": {k: str(v) for k, v in paths.items()},
            "reference": {"identity": ref_identity[0], "content_identity": ref_identity[1],
                          "features": _ordered(features, input_order), "labels": _ordered(labels, input_order),
                          "c47_estimates": _ordered(c47, input_order)},
            "personnel": {"identity": per_identity[0], "content_identity": per_identity[1],
                          "program_seasons": _ordered(programs, input_order),
                          "summaries": _ordered(summaries, input_order),
                          "components": _ordered(components, input_order)}}


# --------------------------------------------------------------------------------------------- 1. qualification

def _org_number(team_key: str) -> int:
    match = TEAM_KEY_RE.match(team_key) if isinstance(team_key, str) else None
    if not match:
        _refuse("ASSOCIATION_INPUT_INVALID", f"team key {team_key!r} is not org:<digits>")
    return int(match.group(1))


def qualification_key(season: int, team_key: str) -> str:
    return f"{season}|{team_key}"


def _rate_exact(numerator: int, denominator: int) -> Fraction:
    return Fraction(numerator, denominator)


def _summary_block(summary: dict[str, Any], line: str, semantics: dict[str, str]) -> dict[str, Any]:
    counts = {k: summary[k] for k in ("prior_roster_count", "current_roster_count", "returning_roster_count",
                                      "departed_roster_count", "arrival_roster_count", "union_roster_count")}
    for name, value in counts.items():
        if not is_int(value) or not 0 <= value <= COUNT_BOUND:
            _refuse("ASSOCIATION_INPUT_INVALID", f"summary {summary['summary_key']}: {name} {value!r} is out of domain")
    rates, exact = {}, {}
    for field, num, den in RATE_FIELDS:
        if counts[den] <= 0:
            _refuse("ASSOCIATION_INPUT_INVALID", f"summary {summary['summary_key']}: {den} is not positive")
        rates[field] = counts[num] / counts[den]
        exact[f"{field}_exact"] = rational(_rate_exact(counts[num], counts[den]))
    equal = all(type(summary[f]) is float and summary[f] == rates[f] for f, _n, _d in RATE_FIELDS)
    shares = {f: summary[f] for f in SHARE_FIELDS}
    flags = {f: (None if shares[f] is None else not 0.0 <= shares[f] <= 1.0) for f in SHARE_FIELDS}
    return {"summary_key": summary["summary_key"], "prior_season": summary["prior_season"],
            "target_season": summary["target_season"], "canonical_team_id": summary["canonical_team_id"],
            "canonical_team_label": summary["canonical_team_label"], **counts, **rates, **exact,
            "parent_rates_equal_recomputed": equal,
            "partial_prior_metric_season": summary["partial_prior_metric_season"],
            "source_known_at_utc": summary["source_known_at_utc"], "shares": shares,
            "share_outside_unit_interval": flags, "share_semantics": semantics,
            "component_keys": list(summary["component_keys"]),
            "missing_component_pairs": list(summary["missing_component_pairs"]),
            "census_scope_state": summary["census_scope_state"],
            "target_game_feature_eligible": summary["target_game_feature_eligible"],
            "protected_eligible": summary["protected_eligible"],
            "original_transition_time_pit_eligible": summary["original_transition_time_pit_eligible"],
            "summary_record_sha256": sha256_bytes(line.encode("utf-8")),
            "original_feature_identity": summary["feature_identity"]}


def share_semantics() -> dict[str, str]:
    return {f: SIGNED_SEMANTICS if f in SIGNED_SHARE_FIELDS else BOUNDED_SEMANTICS for f in SHARE_FIELDS}


def qualify(personnel: dict[str, Any]) -> dict[tuple[int, str], dict[str, Any]]:
    """Every C59 program-season with its exact join state (no involvement counts yet)."""
    summaries = {}
    for record, line in personnel["summaries"]:
        if record["summary_key"] in summaries:
            _refuse("ASSOCIATION_INPUT_INVALID", f"summary {record['summary_key']} repeats")
        summaries[record["summary_key"]] = (record, line)
    out: dict[tuple[int, str], dict[str, Any]] = {}
    semantics = share_semantics()
    for program, line in personnel["program_seasons"]:
        key = (program["season"], program["team_key"])
        if key in out:
            _refuse("ASSOCIATION_INPUT_INVALID", f"program-season {key} repeats")
        _org_number(program["team_key"])
        reasons: list[str] = []
        summary_block = None
        target_key = program["returning_target_summary_key"]
        if program["chain_state"] != "QUALIFIED_EXACT_CHAIN":
            state = "CHAIN_NOT_QUALIFIED"
            reasons.append(f"CHAIN_STATE_{program['chain_state']}")
        elif target_key is None:
            state = "NO_SAME_SEASON_RETURNING_SUMMARY"
            reasons.append("NO_RETURNING_TARGET_SUMMARY_FOR_THIS_PROGRAM_SEASON")
        elif target_key not in summaries:
            state = "SUMMARY_LINK_MISMATCH"
            reasons.append("RETURNING_TARGET_SUMMARY_KEY_UNRESOLVED")
        else:
            summary, summary_line = summaries[target_key]
            if summary["target_season"] != program["season"] or \
                    summary["canonical_team_id"] != program["canonical_team_id"]:
                state = "SUMMARY_LINK_MISMATCH"
                reasons.append("SUMMARY_SEASON_OR_CANONICAL_TEAM_DIFFERS")
            else:
                state = "JOINABLE_SAME_SEASON_SUMMARY"
                summary_block = _summary_block(summary, summary_line, semantics)
                if summary_block["partial_prior_metric_season"]:
                    reasons.append("PARTIAL_PRIOR_METRIC_SEASON_KEPT")
        out[key] = {
            "record_type": RECORD_TYPES["qualifications"],
            "qualification_key": qualification_key(*key), "season": program["season"],
            "team_key": program["team_key"], "org_id": program["org_id"], "division": program["division"],
            "divisions": list(program["divisions"]), "team_names": list(program["team_names"]),
            "chain_state": program["chain_state"], "canonical_team_id": program["canonical_team_id"],
            "returning_target_summary_key": target_key, "coverage_state": program["coverage_state"],
            "roster_presence": program["roster_presence"], "transition_presence": program["transition_presence"],
            "qualification_state": state, "qualification_reasons": reasons, "summary": summary_block,
            "study_views": 0, "study_joined_views": 0, "study_common_support_games": 0, "study_fit_games": 0,
            "study_comparison_games": 0, "program_season_record_sha256": sha256_bytes(line.encode("utf-8")),
            "personnel_release_identity": personnel["identity"], **RECORD_LABELS}
    return out


# --------------------------------------------------------------------------------------------- 2. features

def _history(side: dict[str, Any], contest_key: str) -> dict[str, Any]:
    counts = {k: side[k] for k in ("games", "wins", "losses", "ties")}
    for name, value in counts.items():
        if not is_int(value) or not 0 <= value <= HISTORY_BOUND:
            _refuse("ASSOCIATION_INPUT_INVALID", f"{contest_key}: history {name} {value!r} is out of domain")
    keys = [c["contest_key"] for c in side["contributing"]]
    if counts["games"] != counts["wins"] + counts["losses"] + counts["ties"] or len(keys) != counts["games"]:
        _refuse("ASSOCIATION_INPUT_INVALID", f"{contest_key}: history counts are incoherent")
    if contest_key in keys:
        _refuse("ASSOCIATION_INPUT_INVALID", f"{contest_key}: the target contributes to its own history (leakage)")
    return {**counts, "cold_start": counts["games"] == 0, "contributing_contest_keys": keys,
            "log_odds": history_log_odds(counts["wins"], counts["losses"], counts["ties"])}


def _roster(qual: dict[str, Any]) -> dict[str, Any]:
    s = qual["summary"]
    return {"qualification_key": qual["qualification_key"], "summary_key": s["summary_key"],
            "prior_season": s["prior_season"], "partial_prior_metric_season": s["partial_prior_metric_season"],
            "source_known_at_utc": s["source_known_at_utc"],
            **{k: s[k] for k in ("prior_roster_count", "current_roster_count", "returning_roster_count",
                                 "arrival_roster_count", "union_roster_count")},
            **{f: s[f] for f, _n, _d in RATE_FIELDS}}


def side_state(qual: dict[str, Any] | None) -> str:
    return "NO_PROGRAM_SEASON" if qual is None else qual["qualification_state"]


def feature_record(ref: dict[str, Any], line: str, quals: dict[tuple[int, str], dict[str, Any]],
                   reference_identity: str) -> dict[str, Any]:
    key, season, view = ref["contest_key"], ref["season"], ref["view"]
    team, opponent = _history(ref["team"], key), _history(ref["opponent"], key)
    q_team, q_opp = quals.get((season, ref["team_key"])), quals.get((season, ref["opponent_key"]))
    states = (side_state(q_team), side_state(q_opp))
    supported = states == ("JOINABLE_SAME_SEASON_SUMMARY", "JOINABLE_SAME_SEASON_SUMMARY")
    t_roster = _roster(q_team) if states[0] == "JOINABLE_SAME_SEASON_SUMMARY" else None
    o_roster = _roster(q_opp) if states[1] == "JOINABLE_SAME_SEASON_SUMMARY" else None
    x_h = team["log_odds"] - opponent["log_odds"]
    diffs = [t_roster[f] - o_roster[f] for f, _n, _d in RATE_FIELDS] if supported else None
    reasons = [] if supported else [f"{side}_{state}" for side, state in (("TEAM", states[0]), ("OPPONENT", states[1]))
                                    if state != "JOINABLE_SAME_SEASON_SUMMARY"]
    excluded = key not in team["contributing_contest_keys"] and key not in opponent["contributing_contest_keys"]
    return {"record_type": RECORD_TYPES["features"], "feature_key": f"{key}|{view}", "contest_key": key,
            "season": season, "contest_date": ref["contest_date"], "partition": partition_of(season), "view": view,
            "team_key": ref["team_key"], "team_name": ref["team_name"], "team_org_id": ref["team_org_id"],
            "opponent_key": ref["opponent_key"], "opponent_name": ref["opponent_name"],
            "opponent_org_id": ref["opponent_org_id"], "team_history": team, "opponent_history": opponent,
            "history_log_odds_difference": x_h,
            "team_qualification_key": None if q_team is None else q_team["qualification_key"],
            "opponent_qualification_key": None if q_opp is None else q_opp["qualification_key"],
            "team_side_state": states[0], "opponent_side_state": states[1], "team_roster": t_roster,
            "opponent_roster": o_roster, "roster_rate_differences": diffs,
            "support_state": "COMMON_SUPPORT" if supported else "OUTSIDE_COMMON_SUPPORT",
            "abstention_reasons": reasons, "design_history": [x_h] if supported else None,
            "design_history_roster": [x_h, *diffs] if supported else None,
            "target_excluded_from_history": excluded,
            "reference_feature_record_sha256": sha256_bytes(line.encode("utf-8")),
            "reference_identity": reference_identity, **RECORD_LABELS}


def _game_order(record: dict[str, Any]) -> tuple[Any, ...]:
    return (record["season"], record["contest_date"], record["contest_key"])


def derive_features(reference: dict[str, Any], quals: dict[tuple[int, str], dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for ref, line in reference["features"]:
        if ref["season"] not in STUDY_SEASONS or ref["view"] not in VIEWS:
            _refuse("ASSOCIATION_INPUT_INVALID", f"{ref.get('contest_key')}: not a study view")
        rows.append(feature_record(ref, line, quals, reference["identity"]))
    rows.sort(key=lambda r: (*_game_order(r), r["view"]))
    keys = [r["feature_key"] for r in rows]
    if len(keys) != len(set(keys)):
        _refuse("ASSOCIATION_INPUT_INVALID", "a study view repeats")
    return rows


def involvement(features: list[dict[str, Any]], quals: dict[tuple[int, str], dict[str, Any]]) -> None:
    """Each program-season's study views, joined views and common-support games (counted once per game and side)."""
    for f in features:
        q = quals.get((f["season"], f["team_key"]))
        if q is None:
            continue
        q["study_views"] += 1
        if f["team_side_state"] == "JOINABLE_SAME_SEASON_SUMMARY":
            q["study_joined_views"] += 1
        if f["support_state"] == "COMMON_SUPPORT":
            q["study_common_support_games"] += 1
            q["study_fit_games" if f["season"] in FIT_SEASONS else "study_comparison_games"] += 1


# --------------------------------------------------------------------------------------------- 3. fits

def game_pairs(features: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    by_view = {(f["contest_key"], f["view"]): f for f in features}
    keys = sorted({(f["season"], f["contest_date"], f["contest_key"]) for f in features})
    out = []
    for _s, _d, key in keys:
        a, b = by_view.get((key, "A")), by_view.get((key, "B"))
        if a is None or b is None:
            _refuse("ASSOCIATION_ORIENTATION_MISMATCH", f"{key}: both views are required")
        out.append((a, b))
    return out


def fit_cohort(pairs: list[tuple[dict[str, Any], dict[str, Any]]], labels: dict[str, dict[str, Any]]
               ) -> tuple[list[tuple[dict[str, Any], int]], dict[str, int]]:
    cohort, excluded = [], {}
    for a, _b in pairs:
        if a["season"] not in FIT_SEASONS or a["support_state"] != "COMMON_SUPPORT":
            continue
        label = labels[a["contest_key"]]
        if label["label_state"] == "DECISIVE":
            cohort.append((a, label["y_a"]))
        else:
            excluded[label["label_state"]] = excluded.get(label["label_state"], 0) + 1
    return cohort, dict(sorted(excluded.items()))


def column_scales(cohort: list[tuple[dict[str, Any], int]]) -> tuple[list[float], list[str]]:
    """FIT-only paired RMS of the four-column augmented design (the history-only design uses its first scale)."""
    n = len(cohort)
    scales, constant = [], []
    names = COLUMNS[MODEL_ROSTER]
    for j in range(len(names)):
        if n == 0:
            scales.append(1.0)
            constant.append(names[j])
            continue
        terms = []
        for a, _y in cohort:
            x = a["design_history_roster"][j]
            for v in (x, -x):
                terms.append(0.5 * v * v)
        value = math.sqrt(math.fsum(terms) / n)
        if value == 0.0:
            scales.append(1.0)
            constant.append(names[j])
        else:
            scales.append(value)
    return scales, constant


def scaled_design(feature: dict[str, Any], model_id: str, scales: list[float]) -> tuple[float, ...]:
    x = feature["design_history"] if model_id == MODEL_HISTORY else feature["design_history_roster"]
    return tuple(v / s for v, s in zip(x, scales))


def derive_fits(features: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pairs = game_pairs(features)
    cohort, excluded = fit_cohort(pairs, labels)
    scales, constant = column_scales(cohort)
    fits: dict[str, Any] = {"scales": scales, "constant_columns": constant, "cohort_games": len(cohort),
                            "cohort_keys": [a["contest_key"] for a, _y in cohort], "excluded_by_label": excluded,
                            "models": {}}
    for model_id in FITTED_MODELS:
        width = len(COLUMNS[model_id])
        rows = []
        for a, y in cohort:
            z = scaled_design(a, model_id, scales[:width])
            rows.append(rf.Row(z, float(y), 0.5))
            rows.append(rf.Row(tuple(-v for v in z), 1.0 - float(y), 0.5))
        try:
            result = rf.fit_logistic(rows, width)
            fits["models"][model_id] = {"state": result.state, "result": result, "rows": len(rows), "error": None}
        except rf.ReferenceFitError as exc:
            fits["models"][model_id] = {"state": exc.code, "result": None, "rows": len(rows),
                                        "error": {"code": exc.code, "message": str(exc),
                                                  "trajectory": exc.record.get("trajectory", [])}}
    return fits


# --------------------------------------------------------------------------------------------- 4. estimates

def _estimate_base(f: dict[str, Any], model_id: str, orientation: str, a_line_sha: str, own_sha: str
                   ) -> dict[str, Any]:
    return {"record_type": RECORD_TYPES["estimates"], "estimate_key": f"{f['contest_key']}|{model_id}|{orientation}",
            "contest_key": f["contest_key"], "season": f["season"], "contest_date": f["contest_date"],
            "partition": f["partition"], "model_id": model_id, "model_sha256": model_sha256(model_id),
            "orientation": orientation, "team_key": f["team_key"], "team_name": f["team_name"],
            "opponent_key": f["opponent_key"], "opponent_name": f["opponent_name"],
            "sample_state": sample_state(model_id, f["season"]), "probability": None, "probability_exact": None,
            "opponent_probability": None, "opponent_probability_exact": None,
            "game_grain_probability_a_exact": None, "linear_predictor": None, "linear_predictor_repr": None,
            "probability_repr": None, "team_strength_q": None, "opponent_strength_q": None,
            "c47_estimate_record_sha256": None, "feature_record_sha256": own_sha,
            "game_feature_record_sha256": a_line_sha, **RECORD_LABELS}


def derive_estimates(features: list[dict[str, Any]], fits: dict[str, Any],
                     c47: dict[tuple[str, str, str], tuple[dict[str, Any], str]] | None) -> list[dict[str, Any]]:
    """Every target, model and orientation (A then B), the game-grain probability first. ``c47`` (the accepted C47
    estimate records by contest/model/orientation with their lines) is the builder's lineage source; the reader passes
    None and verifies the recorded lineage digests through the pinned content identity."""
    out = []
    lines = {f["feature_key"]: sha256_bytes(canonical_line(f).encode("utf-8")) for f in features}
    for a, b in game_pairs(features):
        key = a["contest_key"]
        a_sha = lines[a["feature_key"]]
        supported = a["support_state"] == "COMMON_SUPPORT"
        for model_id in MODEL_IDS:
            fit = fits["models"].get(model_id)
            failed = fit is not None and fit["result"] is None
            p_a: Fraction | None = None
            served_a: str | None = None
            eta = p_float = None
            q_pair = None
            if supported and not failed:
                if model_id == MODEL_NULL:
                    p_a = Fraction(1, 2)
                elif model_id == MODEL_SMOOTHED:
                    th, oh = a["team_history"], a["opponent_history"]
                    q_pair = (strength_q(th["wins"], th["ties"], th["games"]),
                              strength_q(oh["wins"], oh["ties"], oh["games"]))
                    p_a = smoothed_probability(*q_pair)
                else:
                    z = scaled_design(a, model_id, fits["scales"][:len(COLUMNS[model_id])])
                    eta = rf.linear(z, fit["result"].coefficients)
                    p_float = rf.sigmoid(eta)
                    served_a = dec12(p_float)
                    p_a = dec_fraction(served_a)
            for orientation, mine in (("A", a), ("B", b)):
                record = _estimate_base(mine, model_id, orientation, a_sha, lines[mine["feature_key"]])
                if p_a is None:
                    record.update(estimate_state="ABSTAINED", abstention_reason=(
                        "ABSTAIN_FIT_FAILED" if failed and supported else "ABSTAIN_OUTSIDE_COMMON_SUPPORT"))
                else:
                    p_mine = p_a if orientation == "A" else 1 - p_a
                    if model_id in FITTED_MODELS:
                        text = served_a if orientation == "A" else dec_complement(served_a)
                        lin = dec12(eta)
                        record.update(probability=text, opponent_probability=dec_complement(text),
                                      linear_predictor=lin if orientation == "A" else dec_negation(lin),
                                      linear_predictor_repr=repr(eta) if orientation == "A" else repr(-eta),
                                      probability_repr=repr(p_float) if orientation == "A" else repr(1.0 - p_float))
                    else:
                        record.update(probability=decimal_text(p_mine), opponent_probability=decimal_text(1 - p_mine))
                    record.update(estimate_state="SUPPORTED", abstention_reason=None,
                                  probability_exact=rational(p_mine), opponent_probability_exact=rational(1 - p_mine),
                                  game_grain_probability_a_exact=rational(p_a))
                    if model_id == MODEL_SMOOTHED:
                        mine_q = q_pair if orientation == "A" else (q_pair[1], q_pair[0])
                        record.update(team_strength_q=rational(mine_q[0]), opponent_strength_q=rational(mine_q[1]))
                    if model_id in FIXED_MODELS and c47 is not None:
                        found = c47.get((key, model_id, orientation))
                        if found is None:
                            _refuse("ASSOCIATION_INPUT_INVALID", f"{key}/{model_id}/{orientation}: no C47 record")
                        c47_record, c47_line = found
                        if c47_record["probability"] != record["probability_exact"]:
                            _refuse("ASSOCIATION_INPUT_INVALID", f"{key}/{model_id}: the unchanged C47 probability "
                                                                 "differs from the recomputed fixed model")
                        record["c47_estimate_record_sha256"] = sha256_bytes(c47_line.encode("utf-8"))
                out.append(record)
    return out


# --------------------------------------------------------------------------------------------- 5. scores

def derive_scores(estimates: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {e["estimate_key"]: e for e in estimates}
    out = []
    for e in estimates:
        if e["orientation"] != "A":
            continue
        b = by_key[f"{e['contest_key']}|{e['model_id']}|B"]
        label = labels[e["contest_key"]]
        record = {"record_type": RECORD_TYPES["scores"], "score_key": f"{e['contest_key']}|{e['model_id']}",
                  "contest_key": e["contest_key"], "season": e["season"], "contest_date": e["contest_date"],
                  "partition": e["partition"], "model_id": e["model_id"], "model_sha256": e["model_sha256"],
                  "orientation": "A", "a_key": e["team_key"], "b_key": b["team_key"], "a_team_name": e["team_name"],
                  "b_team_name": b["team_name"], "sample_state": e["sample_state"],
                  "estimate_state": e["estimate_state"], "label_state": label["label_state"], "y_a": label["y_a"],
                  "probability_a": e["probability"], "probability_a_exact": e["probability_exact"],
                  "log_loss_convention": CLIP_CONVENTION,
                  "estimate_record_sha256": sha256_bytes(canonical_line(e).encode("utf-8")),
                  "label_record_sha256": label["record_sha256"], **RECORD_LABELS}
        if e["estimate_state"] != "SUPPORTED":
            reason = "ABSTAINED_FIT_FAILED" if e["abstention_reason"] == "ABSTAIN_FIT_FAILED" else \
                "ABSTAINED_OUTSIDE_COMMON_SUPPORT"
        elif label["label_state"] == "DECISIVE":
            reason = None
        else:
            reason = {"TIE": "LABEL_TIE", "MISSING": "LABEL_MISSING"}.get(label["label_state"], "LABEL_UNSUPPORTED")
        if reason is None:
            p_a = frac(e["probability_exact"])
            brier = (p_a - label["y_a"]) ** 2
            record.update(score_state="SCORED", unscored_reason=None, brier=rational(brier),
                          brier_decimal=decimal_text(brier), log_loss=repr(log_loss_value(p_a, label["y_a"])))
        else:
            record.update(score_state="UNSCORED", unscored_reason=reason, brier=None, brier_decimal=None,
                          log_loss=None)
        out.append(record)
    return out


# --------------------------------------------------------------------------------------------- 6. summary

def _scopes(seasons_present: Iterable[int] | None = None) -> list[tuple[str, str, tuple[int, ...]]]:
    out = [("SEASON", str(s), (s,)) for s in STUDY_SEASONS]
    out += [("PARTITION", p, PARTITIONS[p]) for p in PARTITION_IDS]
    return out


def _mean(total: Fraction, count: int) -> tuple[dict[str, int] | None, str | None]:
    if not count:
        return None, None
    value = total / count
    return rational(value), decimal_text(value)


def summary_tables(scores: list[dict[str, Any]], *, selected_games_only: bool = False
                   ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Summary rows and descriptive comparisons over ``scores`` (one A-oriented record per canonical game and model)."""
    rows, comparisons = [], []
    for kind, scope_id, seasons in _scopes():
        chosen = [s for s in scores if s["season"] in seasons]
        if selected_games_only and not chosen:
            continue
        by_model: dict[str, dict[str, Any]] = {}
        keysets: dict[str, list[str]] = {}
        for model_id in MODEL_IDS:
            mine = [s for s in chosen if s["model_id"] == model_id]
            scored = [s for s in mine if s["score_state"] == "SCORED"]
            unscored: dict[str, int] = {}
            for s in mine:
                if s["score_state"] != "SCORED":
                    unscored[s["unscored_reason"]] = unscored.get(s["unscored_reason"], 0) + 1
            brier_total = sum((frac(s["brier"]) for s in scored), Fraction(0))
            log_total = math.fsum(float(s["log_loss"]) for s in scored)
            brier_mean, brier_mean_text = _mean(brier_total, len(scored))
            row = {"record_type": "PERSONNEL_SUMMARY_ROW", "scope_kind": kind, "scope_id": scope_id,
                   "seasons": list(seasons), "model_id": model_id, "model_sha256": model_sha256(model_id),
                   "summary_kind": ("FITTED_DATA_IN_SAMPLE_SUMMARY" if model_id in FITTED_MODELS and
                                    set(seasons) <= set(FIT_SEASONS) else
                                    "OUT_OF_FIT_EXPOSED_COMPARISON_SUMMARY" if model_id in FITTED_MODELS else
                                    "FIXED_MODEL_SUMMARY"),
                   "score_records": len(mine), "scored_games": len(scored), "unscored_games": len(mine) - len(scored),
                   "unscored_by_reason": dict(sorted(unscored.items())), "brier_total": rational(brier_total),
                   "brier_total_decimal": decimal_text(brier_total), "brier_mean": brier_mean,
                   "brier_mean_decimal": brier_mean_text, "log_loss_total": repr(log_total),
                   "log_loss_mean": repr(log_total / len(scored)) if scored else None,
                   "log_loss_convention": CLIP_CONVENTION}
            rows.append(row)
            by_model[model_id] = row
            keysets[model_id] = [s["contest_key"] for s in scored]
        first = keysets[MODEL_NULL]
        # a fitted model whose frozen fit failed abstains on every game (recorded, never a no-lift fit); every other
        # model scores exactly the same game keys
        failed = {m for m in FITTED_MODELS if "ABSTAINED_FIT_FAILED" in by_model[m]["unscored_by_reason"]}
        if any(keysets[m] != ([] if m in failed else first) for m in MODEL_IDS):
            _refuse("ASSOCIATION_COMMON_SUPPORT_INVALID", f"{kind} {scope_id}: the models differ in scored game keys")
        for model_id, baseline in SUMMARY_RULE["comparisons"]:
            other, base = by_model[model_id], by_model[baseline]
            entry = {"record_type": "PERSONNEL_COMPARISON_ROW", "scope_kind": kind, "scope_id": scope_id,
                     "seasons": list(seasons), "model_id": model_id, "baseline_model_id": baseline,
                     "scored_games": other["scored_games"],
                     "primary": (model_id, baseline, kind, scope_id) == (MODEL_ROSTER, MODEL_HISTORY, "PARTITION",
                                                                          "COMPARISON") and not selected_games_only}
            if other["brier_mean"] is not None and base["brier_mean"] is not None:
                diff = frac(other["brier_mean"]) - frac(base["brier_mean"])
                entry.update(brier_mean_difference=rational(diff), brier_mean_difference_decimal=decimal_text(diff),
                             direction=("NEGATIVE_LOWER_DESCRIPTIVE_BRIER" if diff < 0 else
                                        "ZERO_EQUAL_DESCRIPTIVE_BRIER" if diff == 0 else
                                        "POSITIVE_HIGHER_DESCRIPTIVE_BRIER"),
                             log_loss_mean_difference=repr(float(other["log_loss_mean"]) -
                                                           float(base["log_loss_mean"])),
                             reading="descriptive retrospective difference (model minus baseline) on identical "
                                     "game keys; no significance, calibration, causal, champion or predictive-skill "
                                     "claim; adverse and null results retained")
            else:
                entry.update(brier_mean_difference=None, brier_mean_difference_decimal=None, direction=None,
                             log_loss_mean_difference=None,
                             reading=("a compared model's frozen fit failed and it abstained on every game; no "
                                      "comparison" if {model_id, baseline} & failed else "no scored game in this scope"))
            comparisons.append(entry)
    return rows, comparisons


def population_counts(quals: list[dict[str, Any]], features: list[dict[str, Any]], estimates: list[dict[str, Any]],
                      scores: list[dict[str, Any]], fits: dict[str, Any]) -> dict[str, Any]:
    a = [f for f in features if f["view"] == "A"]
    supported = [f for f in a if f["support_state"] == "COMMON_SUPPORT"]
    missing: dict[str, int] = {}
    for f in features:
        state = f["team_side_state"]
        if state != "JOINABLE_SAME_SEASON_SUMMARY":
            missing[state] = missing.get(state, 0) + 1

    def count(items: Iterable[str]) -> dict[str, int]:
        out: dict[str, int] = {}
        for item in items:
            out[item] = out.get(item, 0) + 1
        return dict(sorted(out.items()))
    return {"targets": len(a), "views": len(features),
            "joined_views": sum(1 for f in features if f["team_side_state"] == "JOINABLE_SAME_SEASON_SUMMARY"),
            "missing_summary_views": len(features) - sum(1 for f in features
                                                           if f["team_side_state"] == "JOINABLE_SAME_SEASON_SUMMARY"),
            "missing_view_states": dict(sorted(missing.items())),
            "common_support_games": len(supported),
            "fit_games": sum(1 for f in supported if f["season"] in FIT_SEASONS),
            "comparison_games": sum(1 for f in supported if f["season"] in COMPARISON_SEASONS),
            "fit_cohort_games": fits["cohort_games"], "fit_excluded_by_label": fits["excluded_by_label"],
            "targets_by_season": count(str(f["season"]) for f in a),
            "common_support_games_by_season": count(str(f["season"]) for f in supported),
            "qualifications": len(quals), "qualification_states": count(q["qualification_state"] for q in quals),
            "qualification_states_by_division": count(f"{q['division']}|{q['qualification_state']}" for q in quals),
            "estimates": len(estimates), "estimate_states": count(e["estimate_state"] for e in estimates),
            "scores": len(scores), "score_states": count(s["score_state"] for s in scores),
            "unscored_reasons": count(s["unscored_reason"] for s in scores if s["unscored_reason"]),
            "label_states": count(s["label_state"] for s in scores if s["model_id"] == MODEL_NULL),
            "signed_shares_outside_unit_interval": sum(
                1 for q in quals if q["summary"] for f in SIGNED_SHARE_FIELDS
                if q["summary"]["share_outside_unit_interval"][f]),
            "fit_states": {m: fits["models"][m]["state"] for m in FITTED_MODELS}}


def derive_summary(quals: list[dict[str, Any]], features: list[dict[str, Any]], estimates: list[dict[str, Any]],
                   scores: list[dict[str, Any]], fits: dict[str, Any]) -> dict[str, Any]:
    rows, comparisons = summary_tables(scores)
    primary = next(c for c in comparisons if c["primary"])
    return {"record_type": RECORD_TYPES["summary"], "summary_key": "summary",
            "population": population_counts(quals, features, estimates, scores, fits), "rows": rows,
            "comparisons": comparisons, "primary_comparison": primary, **RECORD_LABELS}


# --------------------------------------------------------------------------------------------- parameters

def parameter_records(fits: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for model_id in MODEL_IDS:
        base = {"record_type": RECORD_TYPES["parameters"], "parameter_key": model_id, "model_id": model_id,
                "model_sha256": model_sha256(model_id), "definition": MODELS[model_id], **RECORD_LABELS}
        if model_id in FIXED_MODELS:
            base.update(fitted=False, parameter_state="FIXED_C47_DEFINITION_UNCHANGED", columns=[], coefficients=None,
                        coefficients_repr=None, scales=None, scales_repr=None, constant_columns=[], convergence=None,
                        training=None, penalty=None, trajectory=None)
            out.append(base)
            continue
        width = len(COLUMNS[model_id])
        fit = fits["models"][model_id]
        result = fit["result"]
        scales = fits["scales"][:width]
        base.update(fitted=True, parameter_state=fit["state"], columns=list(COLUMNS[model_id]),
                    coefficients=None if result is None else [dec12(b) for b in result.coefficients],
                    coefficients_repr=None if result is None else [repr(b) for b in result.coefficients],
                    scales=[dec12(s) for s in scales], scales_repr=[repr(s) for s in scales],
                    constant_columns=[c for c in fits["constant_columns"] if c in COLUMNS[model_id]],
                    convergence=None if result is None else {
                        "state": result.state, "newton_steps": result.iterations,
                        "objective_decimal": dec12(result.objective), "objective_repr": repr(result.objective),
                        "gradient_inf_norm_decimal": dec12(result.gradient_inf_norm),
                        "gradient_inf_norm_repr": repr(result.gradient_inf_norm)},
                    training={"seasons": list(FIT_SEASONS), "cohort": FIT_RULE["cohort"],
                              "games": fits["cohort_games"], "oriented_rows": fit["rows"],
                              "row_weight": {"numerator": 1, "denominator": 2},
                              "excluded_by_label_state": fits["excluded_by_label"],
                              "cohort_keys_sha256": keys_sha256(fits["cohort_keys"]),
                              "comparison_2021_2022": "never in the fit, the scales or any constant"},
                    penalty={"lambda": 1, "applies_to": "every column", "intercept": "NONE"},
                    trajectory=result.trajectory if result is not None else (fit["error"] or {}).get("trajectory"))
        if result is None:
            base["convergence"] = {"state": fit["state"], "failure": fit["error"]["message"]}
        out.append(base)
    return out


# --------------------------------------------------------------------------------------------- the whole derivation

def labels_by_contest(reference: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for record, line in reference["labels"]:
        key = record["contest_key"]
        if key in out:
            _refuse("ASSOCIATION_INPUT_INVALID", f"label {key} repeats")
        y = record["y_a"]
        if record["label_state"] == "DECISIVE" and (not is_int(y) or y not in (0, 1)):
            _refuse("ASSOCIATION_INPUT_INVALID", f"label {key}: a decisive label needs y_a 0 or 1")
        out[key] = {"label_state": record["label_state"], "y_a": y if record["label_state"] == "DECISIVE" else None,
                    "record_sha256": sha256_bytes(line.encode("utf-8"))}
    return out


def derive(inputs: dict[str, Any]) -> dict[str, Any]:
    reference, personnel = inputs["reference"], inputs["personnel"]
    quals = qualify(personnel)
    features = derive_features(reference, quals)
    involvement(features, quals)
    labels = labels_by_contest(reference)
    missing = sorted({f["contest_key"] for f in features} - set(labels))
    if missing:
        _refuse("ASSOCIATION_INPUT_INVALID", f"{len(missing)} study targets have no accepted label, e.g. {missing[:3]}")
    c47 = {(r["contest_key"], r["model_id"], r["orientation"]): (r, line) for r, line in reference["c47_estimates"]}
    fits = derive_fits(features, labels)
    estimates = derive_estimates(features, fits, c47)
    scores = derive_scores(estimates, labels)
    qual_list = [quals[k] for k in sorted(quals, key=lambda k: (k[0], _org_number(k[1])))]
    parameters = parameter_records(fits)
    estimates.sort(key=lambda r: (*_game_order(r), MODEL_IDS.index(r["model_id"]), r["orientation"]))
    scores.sort(key=lambda r: (*_game_order(r), MODEL_IDS.index(r["model_id"])))
    summary = derive_summary(qual_list, features, estimates, scores, fits)
    return {"qualifications": qual_list, "features": features, "estimates": estimates, "parameters": parameters,
            "scores": scores, "summary": [summary], "fits": fits}


# --------------------------------------------------------------------------------------------- storage

def record_key(table: str, record: dict[str, Any]) -> str:
    return str(record.get(KEY_FIELDS[table]))


def record_lines(derived: dict[str, Any]) -> dict[str, list[str]]:
    if "lines" not in derived:
        derived["lines"] = {table: [canonical_line(r) for r in derived[table]] for table in RECORD_TABLES}
    return derived["lines"]


def segment_of(table: str, record: dict[str, Any]) -> str:
    return str(record["season"]) if table in SEASONAL_TABLES else "GLOBAL"


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
    return {table: len(derived[table]) for table in RECORD_TABLES}


def inputs_claim(anchors: dict[str, Any]) -> dict[str, Any]:
    return {"inputs": anchors["inputs"], "expected": anchors["expected"]}


def content_document(anchors: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
    lines = record_lines(derived)
    return {"schema": CONTENT_SCHEMA, "stage": "personnel-association-content", "population": POPULATION,
            "contract_id": anchors["contract_id"], "contract_sha256": anchors["contract_sha256"],
            "inputs": inputs_claim(anchors), "parent_contracts": anchors["parent_contracts"],
            "rules_sha256": rules_sha256(), "payload_schema": PAYLOAD_SCHEMA, "row_counts": row_counts(derived),
            "lines_sha256": {table: lines_sha256(lines[table]) for table in RECORD_TABLES},
            "blocks": [[table, segment, len(block), lines_sha256(block)]
                       for table, segment, _records, block in block_lines(derived)]}


def database_document(contract_sha256: str, content_identity: str, database_sha256: str,
                      table_counts: dict[str, int]) -> dict[str, Any]:
    return {"schema": DATABASE_SCHEMA, "stage": "personnel-association-database", "population": POPULATION,
            "contract_sha256": contract_sha256, "content_identity": content_identity, "db_schema_version": DB_SCHEMA,
            "outputs": {DB_FILE: database_sha256}, "table_counts": dict(table_counts)}


def meta_values(anchors: dict[str, Any], content_identity: str, derived: dict[str, Any]) -> dict[str, str]:
    return {"schema_version": DB_SCHEMA, "contract_id": anchors["contract_id"],
            "contract_sha256": anchors["contract_sha256"], "content_identity": content_identity,
            "inputs": canonical_line(inputs_claim(anchors)), "parent_contracts": canonical_line(anchors["parent_contracts"]),
            "labels": canonical_line(LABELS), "rules": canonical_line(rules_document()),
            "row_counts": canonical_line(row_counts(derived)),
            "summary_sha256": sha256_bytes(canonical_json_bytes(derived["summary"][0]))}


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
_SCALAR_TYPES = {"s": (str,), "s?": (str, _NONE), "i": (int,), "i?": (int, _NONE), "b": (bool,), "b?": (bool, _NONE),
                 "f": (float,), "f?": (float, _NONE)}


def _is_rational(value: Any) -> bool:
    return (type(value) is dict and set(value) == {"numerator", "denominator"} and type(value["numerator"]) is int and
            type(value["denominator"]) is int and value["denominator"] > 0 and
            math.gcd(value["numerator"], value["denominator"]) == 1)


def _check_type(code: str, value: Any) -> bool:
    if code in _SCALAR_TYPES:
        return type(value) in _SCALAR_TYPES[code]
    if code.endswith("?") and value is None:
        return True
    base = code.rstrip("?")
    if base == "ls":
        return type(value) is list and all(type(x) is str for x in value)
    if base == "lf":
        return type(value) is list and all(type(x) is float for x in value)
    if base == "q":
        return _is_rational(value)
    if base == "d":
        return type(value) is str and bool(DEC12_RE.match(value))
    if base == "j":
        return True
    if base.startswith("@"):
        spec = SUBSPECS[base[1:]]
        return type(value) is dict and set(value) == set(spec) and all(_check_type(c, value[k]) for k, c in spec.items())
    return False


MANIFEST_MEMBERS = ("content_document", "content_identity", "identity", "identity_document", "provenance")

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
    """The native spelling of an existing local Windows file (MF61A01-01).

    ``location`` is the literal local path (:func:`aggie_analytics.readonly_sqlite.literal_path`: a drive path or its
    native extended-length form; network and device spellings were refused before any filesystem access). Each component
    after the drive becomes the name of the directory entry Windows resolves it to: an 8.3 short name becomes its long
    name and a case-equivalent spelling becomes the entry's own spelling, so the release layout and identity are
    checked on the genuine names of the file that is opened. A junction or link component keeps its own entry name (its
    target is never substituted). A component Windows cannot report, or one whose reported entry does not carry that
    spelling as its long or 8.3 name, keeps the spelling it was given (the literal rule). Every path the caller opened
    before keeps opening the same file; nothing is created. POSIX spellings are never rewritten here (callers keep the
    native case-sensitive POSIX rule)."""
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


class PersonnelAssociation:
    """A verified, read-only handle on one content-addressed national personnel association release.

    Construction refuses (AssociationError with a stable code) unless the release location, run manifest, database
    bytes, schema, meta claims, every record's exact members and JSON types, the complete expected collection of every
    grain, every qualification and feature rule the records can re-derive, a fresh refit with the unchanged accepted
    primitive and the complete re-derivation of every estimate, score, parameter and summary record, the content
    document, the contract-defined database identity document and (when the anchors pin one) the canonical profile
    verify. Each refusal is checked in a fixed order so that every forgery is refused for its own cause."""

    def __init__(self, database: Path, *, manifest: Path | None = None, expect_identity: str | None = None,
                 anchors: dict[str, Any] | None = None) -> None:
        self.anchors = anchors if anchors is not None else {**ANCHORS, "profile": ASSOCIATION_PROFILE}
        self.binding = self._verify_location_and_manifest(database, manifest, expect_identity)
        document = self.binding["identity_document"]
        if document.get("contract_sha256") != self.anchors["contract_sha256"]:
            _refuse("ASSOCIATION_CONTRACT_MISMATCH", f"the release names contract {document.get('contract_sha256')}, "
                                                     f"the reader binds {self.anchors['contract_sha256']}")
        try:
            location = readonly_sqlite.literal_path(self.binding["location"])
            self.conn = readonly_sqlite.connect_readonly(_io_path(Path(location)), immutable=False)
        except readonly_sqlite.DatabaseLocationError as exc:
            raise AssociationError(exc.code, exc.detail) from exc
        except sqlite3.Error as exc:
            raise AssociationError("ASSOCIATION_DATABASE_UNREADABLE", str(exc)) from exc
        try:
            self._verify_database()
        except sqlite3.DatabaseError as exc:
            self.conn.close()
            raise AssociationError("ASSOCIATION_SCHEMA_UNSUPPORTED", str(exc)) from exc
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
            raise AssociationError(exc.code, exc.detail) from exc
        manifest_path = None
        if manifest is not None:
            try:
                manifest_path = Path(readonly_sqlite.literal_path(manifest))
            except readonly_sqlite.DatabaseLocationError as exc:
                suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
                raise AssociationError(f"ASSOCIATION_MANIFEST_LOCATION_{suffix}", f"--manifest {manifest}: "
                                                                                 f"{exc.detail}") from exc
        db = Path(database)
        if not _io_path(db).is_file():
            _refuse("ASSOCIATION_DATABASE_MISSING", f"no personnel association database file at {db}")
        # MF61A01-01: on Windows the layout and identity are checked on the genuine names of the existing file (an 8.3
        # or case-equivalent spelling of the same release is that release); every later read uses that one location.
        # POSIX keeps its native, case-sensitive spelling rule unchanged.
        absolute = Path(native_location(literal)) if os.name == "nt" else Path(os.path.abspath(db))
        db = absolute
        if absolute.name != DB_FILE or absolute.parent.parent.name != "sha256" or \
                absolute.parent.parent.parent.name != POPULATION:
            _refuse("ASSOCIATION_LOCATION_INVALID", f"the release must sit at <root>/{POPULATION}/sha256/<id>/{DB_FILE}")
        identity = absolute.parent.name
        if not IDENTITY_RE.match(identity):
            _refuse("ASSOCIATION_LOCATION_INVALID", f"directory name {identity!r} is not an identity")
        if manifest_path is None:
            manifest_path = manifest_path_for(db)
        if not _io_path(manifest_path).is_file():
            _refuse("ASSOCIATION_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
        try:
            raw = _io_path(manifest_path).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise AssociationError("ASSOCIATION_MANIFEST_MALFORMED", str(exc)) from exc
        doc = loads_untrusted(raw, "ASSOCIATION_MANIFEST_MALFORMED", "run manifest")
        if not isinstance(doc, dict):
            _refuse("ASSOCIATION_MANIFEST_MALFORMED", "the run manifest is not a JSON object")
        if sorted(doc) != sorted(MANIFEST_MEMBERS):
            _refuse("ASSOCIATION_MANIFEST_MALFORMED", f"run manifest members {sorted(doc)} differ from "
                                                      f"{list(MANIFEST_MEMBERS)}")
        _untrusted_canonical(doc, "ASSOCIATION_MANIFEST_MALFORMED", "run manifest")
        identity_document = doc["identity_document"]
        computed = sha256_bytes(_untrusted_canonical(identity_document, "ASSOCIATION_MANIFEST_MALFORMED",
                                                     "run manifest identity document"))
        if computed != identity or doc.get("identity") != identity:
            _refuse("ASSOCIATION_IDENTITY_MISMATCH", f"manifest identity document hashes to {computed}, directory is "
                                                     f"{identity}, the manifest names {doc.get('identity')!r}")
        if not isinstance(identity_document, dict) or \
                (identity_document.get("stage"), identity_document.get("schema"),
                 identity_document.get("db_schema_version"), identity_document.get("population")) != \
                ("personnel-association-database", DATABASE_SCHEMA, DB_SCHEMA, POPULATION):
            _refuse("ASSOCIATION_SCHEMA_UNSUPPORTED", "not a national personnel association database manifest")
        outputs = identity_document.get("outputs")
        if not isinstance(outputs, dict):
            _refuse("ASSOCIATION_IDENTITY_DOCUMENT_MISMATCH", "the manifest identity document's outputs is not an "
                                                              "object")
        actual_sha = sha256_file(_io_path(db))
        if outputs.get(DB_FILE) != actual_sha:
            _refuse("ASSOCIATION_DATABASE_TAMPERED", f"release bytes hash to {actual_sha}, manifest names "
                                                     f"{outputs.get(DB_FILE)}")
        if expect_identity is not None and expect_identity != identity:
            _refuse("STALE_ASSOCIATION_IDENTITY", f"expected {expect_identity}, found {identity}")
        return {"identity": identity, "sha256": actual_sha, "location": str(db), "manifest": str(manifest_path),
                "identity_document": identity_document, "content_document": doc["content_document"],
                "content_identity_claim": doc.get("content_identity"), "provenance": doc.get("provenance")}

    # ---- schema, meta claims, records, rules and identities
    def _verify_database(self) -> None:
        a = self.anchors
        master = sorted((str(r[0]), str(r[1]), r[2]) for r in self.conn.execute(
            "SELECT type, name, sql FROM sqlite_master"))
        if master != sorted(DDL):
            _refuse("ASSOCIATION_SCHEMA_UNSUPPORTED", "the release schema differs from the contract")
        meta_rows = [(str(r[0]), r[1]) for r in self.conn.execute("SELECT key, value FROM meta ORDER BY rowid")]
        meta = dict(meta_rows)
        if len(meta) != len(meta_rows):
            _refuse("ASSOCIATION_META_MISMATCH", "duplicate meta keys")
        if meta.get("schema_version") != DB_SCHEMA:
            _refuse("ASSOCIATION_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}")
        if meta.get("contract_sha256") != a["contract_sha256"] or meta.get("contract_id") != a["contract_id"]:
            _refuse("ASSOCIATION_CONTRACT_MISMATCH", "the release meta names another contract")
        claims = {name: _json_or_none(meta.get(name), name) for name in ("inputs", "parent_contracts", "labels",
                                                                         "rules")}
        if claims["labels"] != LABELS or _untrusted_canonical(claims["labels"], "ASSOCIATION_META_MALFORMED",
                                                              "meta labels") != canonical_json_bytes(LABELS):
            labels = claims["labels"] if isinstance(claims["labels"], dict) else {}
            code = "ASSOCIATION_PIT_CLAIM_INVALID" if labels.get("pit_eligibility") != LABELS["pit_eligibility"] else \
                "ASSOCIATION_LABEL_CLAIM_INVALID"
            _refuse(code, "the release declares labels other than the contract's")
        if _untrusted_canonical(claims["inputs"], "ASSOCIATION_META_MALFORMED", "meta inputs") != \
                canonical_json_bytes(inputs_claim(a)):
            _refuse("ASSOCIATION_PARENT_MISMATCH", "the release was built from other inputs or expectations")
        if _untrusted_canonical(claims["parent_contracts"], "ASSOCIATION_META_MALFORMED", "meta parent_contracts") != \
                canonical_json_bytes(a["parent_contracts"]):
            _refuse("ASSOCIATION_PARENT_MISMATCH", "the release names other parent contracts")
        if _untrusted_canonical(claims["rules"], "ASSOCIATION_META_MALFORMED", "meta rules") != \
                canonical_json_bytes(rules_document()):
            _refuse("ASSOCIATION_RULES_CLAIM_INVALID", "the release declares other rules")
        counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        if counts != self.binding["identity_document"].get("table_counts"):
            _refuse("ASSOCIATION_COUNT_MISMATCH",
                    f"table counts {counts} != {self.binding['identity_document'].get('table_counts')}")
        present = self._read_blocks()
        records = {table: [r for _l, r in present[table]] for table in RECORD_TABLES}
        self._verify_collections(records)
        self._verify_labels(records)
        self._verify_qualifications(records["qualifications"])
        self._verify_features(records)
        rebuilt = self._rederive(records)
        derived = {table: records[table] for table in RECORD_TABLES}
        derived["lines"] = {table: [line for line, _r in present[table]] for table in RECORD_TABLES}
        document = content_document(a, derived)
        content_identity = sha256_bytes(canonical_json_bytes(document))
        if _untrusted_canonical(self.binding["content_document"], "ASSOCIATION_MANIFEST_MALFORMED",
                                "content document") != canonical_json_bytes(document) or \
                self.binding["content_identity_claim"] != content_identity or \
                meta.get("content_identity") != content_identity or \
                self.binding["identity_document"].get("content_identity") != content_identity:
            _refuse("ASSOCIATION_CONTENT_IDENTITY_MISMATCH", f"the rebuilt content identity is {content_identity}")
        expected_meta = meta_values(a, content_identity, derived)
        if meta != expected_meta:
            _refuse("ASSOCIATION_META_MISMATCH", "meta differs on " + str(sorted(
                k for k in set(meta) | set(expected_meta) if meta.get(k) != expected_meta.get(k))))
        identity_document = self.binding["identity_document"]
        expected_document = database_document(a["contract_sha256"], content_identity, self.binding["sha256"], counts)
        expected_bytes = canonical_json_bytes(expected_document)
        if _untrusted_canonical(identity_document, "ASSOCIATION_MANIFEST_MALFORMED", "identity document") != \
                expected_bytes:
            differing = sorted(k for k in set(identity_document) | set(expected_document)
                               if k not in identity_document or k not in expected_document
                               or canonical_json_bytes(identity_document[k]) !=
                               canonical_json_bytes(expected_document[k]))
            _refuse("ASSOCIATION_IDENTITY_DOCUMENT_MISMATCH", f"the manifest identity document is not the "
                                                              f"contract-defined database document (differs on "
                                                              f"{differing})")
        database_identity = sha256_bytes(expected_bytes)
        if database_identity != self.binding["identity"]:
            _refuse("ASSOCIATION_IDENTITY_DOCUMENT_MISMATCH", f"the location names {self.binding['identity']}, the "
                                                              f"contract-defined document is {database_identity}")
        profile = a.get("profile")
        if profile is not None and (profile.get("content_identity"), profile.get("database_identity")) != \
                (content_identity, database_identity):
            _refuse("ASSOCIATION_PROFILE_MISMATCH", f"the release ({database_identity} / {content_identity}) is not "
                                                    f"the pinned canonical profile ({profile.get('database_identity')} "
                                                    f"/ {profile.get('content_identity')})")
        self.database_identity = database_identity
        self.content_identity = content_identity
        self.meta = meta
        self.records = derived
        self.summary = records["summary"][0]
        self.fits = rebuilt
        self.names = self._name_index(records)

    def _read_blocks(self) -> dict[str, list[tuple[str, dict[str, Any]]]]:
        rows = [tuple(r) for r in self.conn.execute(
            "SELECT ord, record_table, segment, records, first_key, last_key, lines_sha256, block FROM blocks "
            "ORDER BY ord")]
        present: dict[str, list[tuple[str, dict[str, Any]]]] = {t: [] for t in RECORD_TABLES}
        layout = []
        for ord_, table, segment, records, first_key, last_key, lines_sha, blob in rows:
            if table not in present:
                _refuse("ASSOCIATION_SCHEMA_UNSUPPORTED", f"block {ord_} names table {table!r}")
            try:
                data = zlib.decompress(blob)
                lines = data.decode("utf-8").split("\n")
            except (zlib.error, TypeError, UnicodeDecodeError) as exc:
                raise AssociationError("ASSOCIATION_INDEX_MISMATCH", f"block {ord_} does not decompress: "
                                                                     f"{exc}") from exc
            if lines[-1] != "":
                _refuse("ASSOCIATION_INDEX_MISMATCH", f"block {ord_} does not end with a newline")
            parsed = []
            for line in lines[:-1]:
                record = loads_untrusted(line, "ASSOCIATION_RECORD_MALFORMED", f"block {ord_} ({table})",
                                         non_json_code="ASSOCIATION_RECORD_TYPE_INVALID")
                if not isinstance(record, dict):
                    _refuse("ASSOCIATION_RECORD_TYPE_INVALID", f"block {ord_} holds a non-object line")
                if not isinstance(record.get(KEY_FIELDS[table]), str):
                    _refuse("ASSOCIATION_RECORD_TYPE_INVALID", f"{table} record: {KEY_FIELDS[table]} is not a string")
                parsed.append((line, record))
            keys = [record_key(table, r) for _l, r in parsed]
            if sha256_bytes(data) != lines_sha or records != len(parsed) or \
                    first_key != (keys[0] if keys else None) or last_key != (keys[-1] if keys else None):
                _refuse("ASSOCIATION_INDEX_MISMATCH", f"block {ord_} index columns differ from its content")
            for _line, record in parsed:
                if table in SEASONAL_TABLES and str(record.get("season")) != segment:
                    _refuse("ASSOCIATION_INDEX_MISMATCH", f"block {ord_} ({table} {segment}) holds a record of "
                                                          f"season {record.get('season')!r}")
            layout.append((table, segment))
            present[table] += parsed
        if layout != list(BLOCK_LAYOUT):
            _refuse("ASSOCIATION_INDEX_MISMATCH", "the blocks do not follow the contract layout")
        for table in RECORD_TABLES:
            types = FIELD_TYPES[table]
            for line, record in present[table]:
                where = f"{table} record {record_key(table, record)}"
                if set(record) != set(types):
                    extra, missing = sorted(set(record) - set(types)), sorted(set(types) - set(record))
                    _refuse("ASSOCIATION_RECORD_SHAPE_INVALID", f"{where}: extra members {extra[:4]}, missing "
                                                                f"{missing[:4]}")
                for field, code in types.items():
                    if not _check_type(code, record[field]):
                        _refuse("ASSOCIATION_FIELD_TYPE_INVALID", f"{where}: {field} is a JSON "
                                                                  f"{type(record[field]).__name__} or nested value "
                                                                  f"outside the contract type {code}")
                if line != _untrusted_canonical(record, "ASSOCIATION_RECORD_MALFORMED", where).decode("utf-8"):
                    _refuse("ASSOCIATION_RECORD_NOT_CANONICAL", f"{where} is not its canonical JSON line")
        return present

    def _verify_collections(self, records: dict[str, list[dict[str, Any]]]) -> None:
        """Complete membership and multiplicity of every grain against the contract's expected collection (derived from
        the pinned target, program-season and model lists), then the contract order, then the exact key sequence."""
        expected = expected_keys(self.anchors["expected"])
        for table in RECORD_TABLES:
            label = TABLE_LABELS[table]
            keys = [record_key(table, r) for r in records[table]]
            if len(keys) != len(set(keys)):
                _refuse("ASSOCIATION_DUPLICATE_ROW", f"{table} repeats a record key")
            listed = expected[table]
            missing = sorted(set(listed) - set(keys))
            if missing:
                _refuse(f"ASSOCIATION_{label}_ROW_MISSING", f"{len(missing)} expected {table} keys absent, e.g. "
                                                            f"{missing[:3]}")
            extra = sorted(set(keys) - set(listed))
            if extra:
                _refuse(f"ASSOCIATION_{label}_ROW_EXTRA", f"{len(extra)} {table} keys outside the expected collection, "
                                                          f"e.g. {extra[:3]}")
            if keys != listed:
                _refuse("ASSOCIATION_ORDER_MISMATCH", f"{table} is not in the contract order")
            if keys_sha256(keys) != self.anchors["expected"]["keys_sha256"][table]:
                _refuse(f"ASSOCIATION_{label}_KEYS_MISMATCH", f"the {table} key sequence differs from the contract's "
                                                              "expected collection")

    @staticmethod
    def _verify_labels(records: dict[str, list[dict[str, Any]]]) -> None:
        for table in RECORD_TABLES:
            want = RECORD_TYPES[table]
            for record in records[table]:
                if record["record_type"] != want:
                    _refuse("ASSOCIATION_RECORD_TYPE_INVALID", f"{table} record {record_key(table, record)} is a "
                                                               f"{record['record_type']!r}")
                for k in RECORD_LABEL_KEYS:
                    if record[k] != LABELS[k]:
                        _refuse("ASSOCIATION_PIT_CLAIM_INVALID" if k == "pit_eligibility" else
                                "ASSOCIATION_LABEL_CLAIM_INVALID", f"{table} record {record_key(table, record)}: {k} "
                                                                   f"is {record[k]!r}")

    def _verify_qualifications(self, quals: list[dict[str, Any]]) -> None:
        expected = self.anchors["expected"]
        signed_outside = set(expected["signed_shares_outside_unit_interval"])
        found_outside = set()
        for q in quals:
            key = q["qualification_key"]
            if q["season"] not in STUDY_SEASONS:
                _refuse("ASSOCIATION_SEASON_OUT_OF_RANGE", f"{key}: season {q['season']}")
            if not TEAM_KEY_RE.match(q["team_key"]) or key != qualification_key(q["season"], q["team_key"]) or \
                    q["team_key"] != f"org:{q['org_id']}":
                _refuse("ASSOCIATION_KEY_MISMATCH", f"{key}: the key, team key and org id disagree")
            if q["personnel_release_identity"] != self.anchors["inputs"]["personnel_database"]["identity"]:
                _refuse("ASSOCIATION_PARENT_MISMATCH", f"{key}: names another personnel release")
            s = q["summary"]
            state = q["qualification_state"]
            if state not in QUALIFICATION_STATES:
                _refuse("ASSOCIATION_QUALIFICATION_STATE_INVALID", f"{key}: state {state!r}")
            joinable = state == "JOINABLE_SAME_SEASON_SUMMARY"
            want_state = ("CHAIN_NOT_QUALIFIED" if q["chain_state"] != "QUALIFIED_EXACT_CHAIN" else
                          "NO_SAME_SEASON_RETURNING_SUMMARY" if q["returning_target_summary_key"] is None else state)
            if state != want_state or joinable != (s is not None) or \
                    (state == "SUMMARY_LINK_MISMATCH" and q["returning_target_summary_key"] is None):
                _refuse("ASSOCIATION_QUALIFICATION_STATE_INVALID", f"{key}: state {state} does not follow its chain "
                                                                   "and summary link")
            if s is None:
                if q["study_joined_views"] or q["study_common_support_games"]:
                    _refuse("ASSOCIATION_MISSING_AS_ZERO", f"{key}: an unjoinable program-season supports games")
                continue
            if s["summary_key"] != q["returning_target_summary_key"] or s["target_season"] != q["season"] or \
                    s["canonical_team_id"] != q["canonical_team_id"] or not TEAM_ID_RE.match(s["canonical_team_id"]):
                _refuse("ASSOCIATION_JOIN_MISMATCH", f"{key}: the summary is not the same season's chain summary")
            if s["prior_season"] != s["target_season"] - 1:
                _refuse("ASSOCIATION_JOIN_MISMATCH", f"{key}: the prior season is not the preceding season")
            if s["target_game_feature_eligible"] is not False or s["protected_eligible"] is not False or \
                    s["original_transition_time_pit_eligible"] is not False:
                _refuse("ASSOCIATION_PARENT_ELIGIBILITY_PROMOTED", f"{key}: a parent eligibility flag is not false")
            if s["source_known_at_utc"] != ROSTER_SOURCE_KNOWN_AT:
                _refuse("ASSOCIATION_SOURCE_CLOCK_INVALID", f"{key}: roster source clock {s['source_known_at_utc']!r}")
            counts = {k: s[k] for k in ("prior_roster_count", "current_roster_count", "returning_roster_count",
                                        "departed_roster_count", "arrival_roster_count", "union_roster_count")}
            if not all(0 <= v <= COUNT_BOUND for v in counts.values()):
                _refuse("ASSOCIATION_COUNT_OUT_OF_DOMAIN", f"{key}: a roster count is outside [0, {COUNT_BOUND}]")
            if counts["returning_roster_count"] + counts["departed_roster_count"] != counts["prior_roster_count"] or \
                    counts["returning_roster_count"] + counts["arrival_roster_count"] != \
                    counts["current_roster_count"] or \
                    counts["prior_roster_count"] + counts["arrival_roster_count"] != counts["union_roster_count"] or \
                    min(counts["prior_roster_count"], counts["current_roster_count"]) <= 0:
                _refuse("ASSOCIATION_SET_COUNTS_INCOHERENT", f"{key}: roster set counts are incoherent")
            for field, num, den in RATE_FIELDS:
                if s[field] != counts[num] / counts[den] or \
                        s[f"{field}_exact"] != rational(Fraction(counts[num], counts[den])):
                    _refuse("ASSOCIATION_RATE_MISMATCH", f"{key}: {field} is not {num}/{den}")
            if s["parent_rates_equal_recomputed"] is not True:
                _refuse("ASSOCIATION_RATE_MISMATCH", f"{key}: the parent rates differ from the recomputation")
            if s["share_semantics"] != share_semantics():
                _refuse("ASSOCIATION_SHARE_SEMANTICS_INVALID", f"{key}: share semantics differ")
            for field in SHARE_FIELDS:
                value = s["shares"][field]
                flag = s["share_outside_unit_interval"][field]
                if (value is None) != (flag is None) or (value is not None and flag != (not 0.0 <= value <= 1.0)):
                    _refuse("ASSOCIATION_SHARE_SEMANTICS_INVALID", f"{key}: {field} flag does not describe its value")
                if value is not None and flag and field not in SIGNED_SHARE_FIELDS:
                    _refuse("ASSOCIATION_SHARE_SEMANTICS_INVALID", f"{key}: a bounded count share is outside [0, 1]")
                if flag:
                    found_outside.add(f"{s['summary_key']}|{field}")
        if found_outside != signed_outside:
            _refuse("ASSOCIATION_SIGNED_SHARE_CLIPPED", f"the signed shares outside [0, 1] differ from the contract's "
                                                        f"(missing {sorted(signed_outside - found_outside)[:3]}, extra "
                                                        f"{sorted(found_outside - signed_outside)[:3]})")

    def _verify_features(self, records: dict[str, list[dict[str, Any]]]) -> None:
        quals = {q["qualification_key"]: q for q in records["qualifications"]}
        latest = max(f["contest_date"] for f in records["features"]) if records["features"] else ""
        if latest and not ROSTER_SOURCE_KNOWN_AT[:10] > latest:
            _refuse("ASSOCIATION_SOURCE_CLOCK_INVALID", "the roster source clock is not after every study game")
        supported_games = set(self.anchors["expected"]["common_support_games"])
        by_key = {(f["contest_key"], f["view"]): f for f in records["features"]}
        ref_identity = self.anchors["inputs"]["reference_database"]["identity"]
        for f in records["features"]:
            key = f["feature_key"]
            if f["season"] not in STUDY_SEASONS or not CONTEST_KEY_RE.match(f["contest_key"]) or \
                    key != f"{f['contest_key']}|{f['view']}" or f["view"] not in VIEWS or \
                    not DATE_RE.match(f["contest_date"]) or \
                    f["contest_date"][:4] not in (str(f["season"]), str(f["season"] + 1)):
                _refuse("ASSOCIATION_KEY_MISMATCH", f"{key}: key, season, view or date is invalid")
            if f["partition"] != partition_of(f["season"]):
                _refuse("ASSOCIATION_PARTITION_MISMATCH", f"{key}: partition {f['partition']}")
            if f["reference_identity"] != ref_identity:
                _refuse("ASSOCIATION_PARENT_MISMATCH", f"{key}: names another reference release")
            for side in ("team", "opponent"):
                h = f[f"{side}_history"]
                if not all(0 <= h[k] <= HISTORY_BOUND for k in ("games", "wins", "losses", "ties")):
                    _refuse("ASSOCIATION_COUNT_OUT_OF_DOMAIN", f"{key}: {side} history counts are out of domain")
                if h["games"] != h["wins"] + h["losses"] + h["ties"] or len(h["contributing_contest_keys"]) != \
                        h["games"] or h["cold_start"] != (h["games"] == 0) or \
                        len(set(h["contributing_contest_keys"])) != h["games"]:
                    _refuse("ASSOCIATION_HISTORY_INCOHERENT", f"{key}: {side} history counts are incoherent")
                if f["contest_key"] in h["contributing_contest_keys"]:
                    _refuse("ASSOCIATION_HISTORY_LEAKAGE", f"{key}: the target contributes to its own history")
                if h["log_odds"] != history_log_odds(h["wins"], h["losses"], h["ties"]):
                    _refuse("ASSOCIATION_LOG_ODDS_MISMATCH", f"{key}: {side} log-odds is not the frozen formula")
            if f["target_excluded_from_history"] is not True:
                _refuse("ASSOCIATION_HISTORY_LEAKAGE", f"{key}: the target is not excluded from its history")
            if f["history_log_odds_difference"] != f["team_history"]["log_odds"] - f["opponent_history"]["log_odds"]:
                _refuse("ASSOCIATION_LOG_ODDS_MISMATCH", f"{key}: the history column is not team minus opponent")
            # each side's roster block is exactly its own same-season program-season's summary (never zeros)
            for side in ("team", "opponent"):
                qkey = qualification_key(f["season"], f[f"{side}_key"])
                q = quals.get(qkey)
                want_qkey = None if q is None else qkey
                state = side_state(q)
                if f[f"{side}_qualification_key"] != want_qkey or f[f"{side}_side_state"] != state:
                    _refuse("ASSOCIATION_JOIN_MISMATCH", f"{key}: {side} is not joined through its own season and team")
                roster = f[f"{side}_roster"]
                if state != "JOINABLE_SAME_SEASON_SUMMARY":
                    if roster is not None:
                        _refuse("ASSOCIATION_MISSING_AS_ZERO", f"{key}: {side} has no joinable summary but a roster "
                                                               "block")
                    continue
                if roster is None or canonical_json_bytes(roster) != canonical_json_bytes(_roster(q)):
                    _refuse("ASSOCIATION_JOIN_MISMATCH", f"{key}: {side} roster block differs from its program-season")
            supported = f["team_side_state"] == f["opponent_side_state"] == "JOINABLE_SAME_SEASON_SUMMARY"
            if f["support_state"] != ("COMMON_SUPPORT" if supported else "OUTSIDE_COMMON_SUPPORT") or \
                    supported != (f["contest_key"] in supported_games):
                _refuse("ASSOCIATION_SUPPORT_MISMATCH", f"{key}: support state disagrees with the joins or the "
                                                        "contract's common cohort")
            reasons = [] if supported else [f"{s.upper()}_{f[f'{s}_side_state']}" for s in ("team", "opponent")
                                            if f[f"{s}_side_state"] != "JOINABLE_SAME_SEASON_SUMMARY"]
            if f["abstention_reasons"] != reasons:
                _refuse("ASSOCIATION_SUPPORT_MISMATCH", f"{key}: abstention reasons differ")
            if supported:
                diffs = [f["team_roster"][r] - f["opponent_roster"][r] for r, _n, _d in RATE_FIELDS]
                x_h = f["history_log_odds_difference"]
                if f["roster_rate_differences"] != diffs or f["design_history"] != [x_h] or \
                        f["design_history_roster"] != [x_h, *diffs]:
                    _refuse("ASSOCIATION_DESIGN_MISMATCH", f"{key}: the design is not the frozen columns")
            elif f["roster_rate_differences"] is not None or f["design_history"] is not None or \
                    f["design_history_roster"] is not None:
                _refuse("ASSOCIATION_MISSING_AS_ZERO", f"{key}: an unsupported game carries a design")
        # orientation: B is A mirrored and every column negated exactly
        for (contest, view), f in by_key.items():
            if view != "A":
                continue
            b = by_key.get((contest, "B"))
            if b is None:
                _refuse("ASSOCIATION_ORIENTATION_MISMATCH", f"{contest}: no B view")
            same = ("season", "contest_date", "partition", "support_state", "reference_identity")
            swapped = (("team_key", "opponent_key"), ("team_name", "opponent_name"), ("team_org_id", "opponent_org_id"),
                       ("team_history", "opponent_history"), ("team_roster", "opponent_roster"),
                       ("team_qualification_key", "opponent_qualification_key"),
                       ("team_side_state", "opponent_side_state"))
            if any(f[k] != b[k] for k in same) or any(f[x] != b[y] or f[y] != b[x] for x, y in swapped) or \
                    b["history_log_odds_difference"] != -f["history_log_odds_difference"] or \
                    (f["design_history_roster"] is not None and
                     b["design_history_roster"] != [-v for v in f["design_history_roster"]]):
                _refuse("ASSOCIATION_ORIENTATION_MISMATCH", f"{contest}: the B view is not the exact mirror of A")
        # involvement counts of every qualification
        tallies: dict[str, list[int]] = {}
        for f in records["features"]:
            qkey = f["team_qualification_key"]
            if qkey is None:
                continue
            t = tallies.setdefault(qkey, [0, 0, 0, 0, 0])
            t[0] += 1
            if f["team_side_state"] == "JOINABLE_SAME_SEASON_SUMMARY":
                t[1] += 1
            if f["support_state"] == "COMMON_SUPPORT":
                t[2] += 1
                t[3 if f["season"] in FIT_SEASONS else 4] += 1
        for q in records["qualifications"]:
            want = tallies.get(q["qualification_key"], [0, 0, 0, 0, 0])
            got = [q["study_views"], q["study_joined_views"], q["study_common_support_games"], q["study_fit_games"],
                   q["study_comparison_games"]]
            if got != want:
                _refuse("ASSOCIATION_INVOLVEMENT_MISMATCH", f"{q['qualification_key']}: study involvement {got} != "
                                                            f"{want}")

    def _rederive(self, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """A fresh refit and the complete re-derivation of every estimate, score, parameter and summary record from
        the verified features and the score records' accepted label fields; each stored record must equal its
        re-derivation exactly (canonical JSON line)."""
        features = records["features"]
        labels: dict[str, dict[str, Any]] = {}
        for s in records["scores"]:
            entry = {"label_state": s["label_state"], "y_a": s["y_a"], "record_sha256": s["label_record_sha256"]}
            if s["label_state"] == "DECISIVE" and s["y_a"] not in (0, 1):
                _refuse("ASSOCIATION_LABEL_INCONSISTENT", f"{s['score_key']}: a decisive label needs y_a 0 or 1")
            if s["label_state"] != "DECISIVE" and s["y_a"] is not None:
                _refuse("ASSOCIATION_LABEL_INCONSISTENT", f"{s['score_key']}: a nondecisive label carries y_a")
            if labels.setdefault(s["contest_key"], entry) != entry:
                _refuse("ASSOCIATION_LABEL_INCONSISTENT", f"{s['contest_key']}: the models disagree on the label")
        # complements before the refit, so a lost complement is refused for its own cause
        for e in records["estimates"]:
            if e["estimate_state"] == "SUPPORTED":
                if e["probability_exact"] is None or e["opponent_probability_exact"] is None or \
                        frac(e["probability_exact"]) + frac(e["opponent_probability_exact"]) != 1 or \
                        e["opponent_probability"] is None or e["probability"] is None or \
                        dec_fraction(e["probability"]) + dec_fraction(e["opponent_probability"]) != 1:
                    _refuse("ASSOCIATION_COMPLEMENT_INVALID", f"{e['estimate_key']}: probabilities are not exact "
                                                              "complements")
        fits = derive_fits(features, labels)
        params = parameter_records(fits)
        for stored, want in zip(records["parameters"], params):
            if canonical_json_bytes(stored) != canonical_json_bytes(want):
                differing = sorted(k for k in want if canonical_json_bytes(stored.get(k)) !=
                                   canonical_json_bytes(want[k]))
                _refuse("ASSOCIATION_PARAMETER_MISMATCH", f"{stored['model_id']}: the stored parameters differ from "
                                                          f"the refit on {differing}")
        estimates = derive_estimates(features, fits, None)
        estimates.sort(key=lambda r: (*_game_order(r), MODEL_IDS.index(r["model_id"]), r["orientation"]))
        for stored, want in zip(records["estimates"], estimates):
            want = dict(want, c47_estimate_record_sha256=stored["c47_estimate_record_sha256"]
                        if want["model_id"] in FIXED_MODELS and want["estimate_state"] == "SUPPORTED" else None)
            if canonical_json_bytes(stored) != canonical_json_bytes(want):
                differing = sorted(k for k in want if canonical_json_bytes(stored.get(k)) !=
                                   canonical_json_bytes(want[k]))
                _refuse("ASSOCIATION_ESTIMATE_MISMATCH", f"{stored['estimate_key']}: differs on {differing}")
            if want["model_id"] in FIXED_MODELS and want["estimate_state"] == "SUPPORTED" and \
                    not (isinstance(stored["c47_estimate_record_sha256"], str) and
                         IDENTITY_RE.match(stored["c47_estimate_record_sha256"])):
                _refuse("ASSOCIATION_ESTIMATE_MISMATCH", f"{stored['estimate_key']}: no C47 lineage digest")
        scores = derive_scores(records["estimates"], labels)
        scores.sort(key=lambda r: (*_game_order(r), MODEL_IDS.index(r["model_id"])))
        for stored, want in zip(records["scores"], scores):
            if canonical_json_bytes(stored) != canonical_json_bytes(want):
                differing = sorted(k for k in want if canonical_json_bytes(stored.get(k)) !=
                                   canonical_json_bytes(want[k]))
                _refuse("ASSOCIATION_SCORE_MISMATCH", f"{stored['score_key']}: differs on {differing}")
        summary = derive_summary(records["qualifications"], features, records["estimates"], records["scores"], fits)
        if canonical_json_bytes(records["summary"][0]) != canonical_json_bytes(summary):
            differing = sorted(k for k in summary if canonical_json_bytes(records["summary"][0].get(k)) !=
                               canonical_json_bytes(summary[k]))
            _refuse("ASSOCIATION_SUMMARY_MISMATCH", f"the stored summary differs from its re-derivation on {differing}")
        return fits

    @staticmethod
    def _name_index(records: dict[str, list[dict[str, Any]]]) -> dict[tuple[int, str], frozenset[str]]:
        names: dict[tuple[int, str], set[str]] = {}
        for f in records["features"]:
            names.setdefault((f["season"], f["team_key"]), set()).add(f["team_name"].casefold())
        for q in records["qualifications"]:
            names.setdefault((q["season"], q["team_key"]), set()).update(n.casefold() for n in q["team_names"])
        return {k: frozenset(v) for k, v in names.items()}

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "PersonnelAssociation":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- serving
    @staticmethod
    def filters(grain: Any, *, season: Any = None, team: Any = None, contest: Any = None, model: Any = None,
                partition: Any = None) -> dict[str, Any]:
        """Validate a selection before any file is read: an unknown grain, a malformed or an inapplicable selector is
        refused with its own code (SELECTOR_MATRIX)."""
        if grain not in GRAINS:
            _refuse("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}")
        allowed = SELECTOR_MATRIX[grain]
        for name, value in (("season", season), ("team", team), ("contest", contest), ("model", model),
                            ("partition", partition)):
            if value is not None and name not in allowed:
                _refuse("FILTER_NOT_APPLICABLE", f"{name} does not apply to the {grain} grain (allowed: {allowed})")
        out: dict[str, Any] = {}
        if season is not None:
            if not is_int(season):
                _refuse("SEASON_INVALID", f"season must be an integer, got {season!r}")
            out["season"] = season
        if team is not None:
            text = team.strip() if isinstance(team, str) else None
            if not text or len(text) > 200 or any(ord(c) < 32 for c in text):
                _refuse("TEAM_INVALID", f"team must be org:<digits>, digits or a team name, got {team!r}")
            # MF61A01-02: a team name is Unicode text; a lone UTF-16 surrogate code point is not a Unicode scalar value
            # and is refused here, before any file is read (never echoed into an answer it cannot be encoded in).
            surrogate = next((c for c in text if 0xD800 <= ord(c) <= 0xDFFF), None)
            if surrogate is not None:
                _refuse("TEAM_INVALID", f"team must be Unicode text: U+{ord(surrogate):04X} is a lone surrogate, not a "
                                        f"Unicode scalar value, got {team!r}")
            match = TEAM_SELECTOR_RE.match(text)
            out["team"] = f"org:{int(match.group(1))}" if match else text
        if contest is not None:
            text = contest.strip() if isinstance(contest, str) else None
            match = CONTEST_SELECTOR_RE.match(text) if text else None
            if not match:
                _refuse("CONTEST_INVALID", f"contest must be an accepted contest key ncaa:<digits>, got {contest!r}")
            out["contest"] = f"ncaa:{match.group(1)}"
        if model is not None:
            if model not in MODEL_IDS:
                _refuse("MODEL_INVALID", f"model must be one of {list(MODEL_IDS)}")
            out["model"] = model
        if partition is not None:
            if partition not in PARTITION_IDS:
                _refuse("PARTITION_INVALID", f"partition must be one of {list(PARTITION_IDS)}")
            out["partition"] = partition
        return out

    def source_time(self) -> dict[str, Any]:
        latest = max(f["contest_date"] for f in self.records["features"]) if self.records["features"] else None
        return {"roster_source_known_at_utc": ROSTER_SOURCE_KNOWN_AT,
                "roster_clock_kind": "PUBLIC_REPOSITORY_COMMITTER_TIME_OBSERVED_AFTER_EVERY_STUDY_GAME",
                "latest_study_contest_date": latest,
                "history_clock": LABELS["history_clock"],
                "release_provenance_issued_at_utc": (self.binding.get("provenance") or {}).get("issued_at_utc")
                if isinstance(self.binding.get("provenance"), dict) else None,
                "release_provenance_note": "the run manifest's provenance build clock; not identity-bound"}

    def query(self, grain: str, *, season: Any = None, team: Any = None, contest: Any = None, model: Any = None,
              partition: Any = None, limit: int | None = 50, offset: int = 0, all_rows: bool = False
              ) -> dict[str, Any]:
        filters = self.filters(grain, season=season, team=team, contest=contest, model=model, partition=partition)
        if not is_int(offset) or offset < 0:
            _refuse("NEGATIVE_OFFSET", "offset must be a zero or positive integer")
        if limit is not None and (not is_int(limit) or limit < 0):
            _refuse("NEGATIVE_LIMIT", "limit must be a zero or positive integer")
        result: dict[str, Any] = {
            "release_identity": self.database_identity, "content_identity": self.content_identity,
            "contract_id": self.anchors["contract_id"], "contract_sha256": self.anchors["contract_sha256"],
            "population": POPULATION, "grain": grain, "filters": filters, "offset": offset,
            "limit": None if all_rows else limit, **LABELS, "source_time": self.source_time(),
            "parents": {"reference_identity": self.anchors["inputs"]["reference_database"]["identity"],
                        "personnel_identity": self.anchors["inputs"]["personnel_database"]["identity"]},
            "denominators": self.summary["population"],
            "verification": {**{f"{t}_verified": len(self.records[t]) for t in RECORD_TABLES},
                             "records_verified": True, "refit_rederived": True, "content_identity_rebuilt": True,
                             "database_document_rebuilt": True, "profile_pinned": self.anchors.get("profile") is not None}}
        if "season" in filters and filters["season"] not in STUDY_SEASONS:
            result.update(season_scope_state="SEASON_OUTSIDE_RELEASE", total=0, returned=0, rows=[],
                          next_offset=None, note="the study seasons are 2016-2022; no row is fabricated for another "
                                                 "season (2023 is never a study season)")
            return result
        if grain == "personnel-summary":
            rows, selection = self._summary_rows(filters)
            result["summary_selection"] = selection
        else:
            rows = [r for r in self.records[GRAINS[grain]] if self._match(grain, r, filters)]
        total = len(rows)
        page = rows[offset:] if all_rows else rows[offset:offset + (limit or 0)]
        result.update(season_scope_state="RETROSPECTIVE_STUDY_SEASONS_2016_2022", total=total, returned=len(page),
                      rows=page, next_offset=offset + len(page) if offset + len(page) < total else None)
        return result

    def _team_matches(self, value: str, season: int, team_key: str) -> bool:
        if TEAM_KEY_RE.match(value):
            return team_key == value
        return value.casefold() in self.names.get((season, team_key), frozenset())

    def _match(self, grain: str, record: dict[str, Any], filters: dict[str, Any]) -> bool:
        if grain == "personnel-parameter":
            return "model" not in filters or record["model_id"] == filters["model"]
        if "season" in filters and record["season"] != filters["season"]:
            return False
        if "partition" in filters and record["partition"] != filters["partition"]:
            return False
        if "model" in filters and record["model_id"] != filters["model"]:
            return False
        if "contest" in filters and record["contest_key"] != filters["contest"]:
            return False
        if "team" in filters:
            if grain == "personnel-qualification":
                sides = (record["team_key"],)
            elif grain == "personnel-score":
                sides = (record["a_key"], record["b_key"])
            else:
                sides = (record["team_key"],)
            if not any(self._team_matches(filters["team"], record["season"], side) for side in sides):
                return False
        return True

    def _summary_rows(self, filters: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        game_filters = {k: v for k, v in filters.items() if k in ("season", "team", "contest", "partition")}
        if not game_filters:
            rows = list(self.summary["rows"]) + list(self.summary["comparisons"])
            selection = {"rule": SUMMARY_RULE["selection"], "selected": "ALL_CANONICAL_GAMES",
                         "canonical_games": self.summary["population"]["targets"]}
        else:
            chosen = [s for s in self.records["scores"] if self._match("personnel-score", s,
                                                                       {**game_filters})]
            rows_, comparisons = summary_tables(chosen, selected_games_only=True)
            rows = rows_ + comparisons
            games = sorted({s["contest_key"] for s in chosen})
            by_season: dict[str, int] = {}
            for s in chosen:
                if s["model_id"] == MODEL_NULL:
                    by_season[str(s["season"])] = by_season.get(str(s["season"]), 0) + 1
            selection = {"rule": SUMMARY_RULE["selection"], "selected": "SELECTED_CANONICAL_GAMES",
                         "canonical_games": len(games), "canonical_games_by_season": dict(sorted(by_season.items()))}
        if "model" in filters:
            rows = [r for r in rows if r["model_id"] == filters["model"]]
        return rows, selection


# --------------------------------------------------------------------------------------------- expected collections

def expected_keys(expected: dict[str, Any]) -> dict[str, list[str]]:
    """The exact key sequence of every grain from the contract's pinned target and program-season lists."""
    targets = [(t["season"], t["contest_date"], t["contest_key"]) for t in expected["targets"]]
    games = sorted(targets)
    return {"qualifications": list(expected["qualification_keys"]),
            "features": [f"{k}|{v}" for _s, _d, k in games for v in VIEWS],
            "estimates": [f"{k}|{m}|{v}" for _s, _d, k in games for m in MODEL_IDS for v in VIEWS],
            "parameters": list(MODEL_IDS),
            "scores": [f"{k}|{m}" for _s, _d, k in games for m in MODEL_IDS],
            "summary": ["summary"]}
