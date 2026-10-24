r"""National frozen shallow-tree comparison over the accepted 2016-2023 C56 targets (BAT-736, a bounded BAT-423 research
contribution, Cycle #65 TP65-A01).

Every rule lives here, and the committed research contract
``configs/national_shallow_boosting_comparison_2016_2023_contract.json`` must equal these constants (the contract
generator ``tools/cycle65/make_shallow_boosting_contract.py --check`` refuses otherwise). The reader pins that
contract's SHA-256, the exact accepted C56 parent (database bytes, identities, witness collections) and, once the first
authorized build is pinned, the canonical profile (:data:`ANCHORS`, :data:`BOOSTING_PROFILE`).

What the release holds (one create-only SQLite file in ``<data>/canonical/national_shallow_boosting_comparison_2016_2023
/sha256/<identity>/national_shallow_boosting_comparison.sqlite`` with its run manifest):

* ``parent_reference`` -- the complete accepted C56 reference database, byte for byte, as one BLOB. The reader checks its
  storage type, byte count and full SHA-256 against the committed pin before any parse, deserializes it in memory with
  the standard library only (fixed whitelisted SELECTs, ``query_only``, no extension and no stored SQL), checks its
  exact schema, meta claims and 34 blocks with bounded decompression, and reads its six complete witness collections
  (features, labels, estimates, parameters, scores, summary). It never constructs the old reader or refits its models.
* ``features`` -- both oriented views of every one of the 5,875 targets: the ten unchanged C56 difference columns as
  exact rationals and their binary64 values (each rational converted once), the canonical participants, the frozen
  partition (FIT_2016_2022 or COMPARISON_EXPOSED_2023) and the parent partition witness, the prior-game counts and the
  game slice flags (independently re-derived and required to equal the parent's).
* ``labels`` -- the parent label of every target (all accepted targets are decisive; a TIE stays unscored for the
  probability families and is never invented as 0.5).
* ``parameters`` -- exactly two frozen HistGradientBoosting definitions (depth 2 and depth 3, 100 stages each, every
  constructor option explicit), fitted once each on the 10,174 oriented rows of the 5,087 decisive 2016-2022 games with
  weight 1/2 per row, exported as finite plain-data trees (13 typed fields per node; no executable serialization).
* ``estimates`` -- per game, model and orientation: the canonical stdlib traversal margins and raw probabilities of
  both views (``raw_z_*_repr``, ``raw_q_*_repr``) and the served paired probability
  ``p_A = (q_A + (1 - q_B)) / 2`` quantized half-even to 12 places in a fixed decimal context, with its exact complement.
* ``scores`` -- seven per game: the five unchanged C56 families (their parent score records embedded byte for byte) and
  the two trees (exact rational Brier of the served probability, log loss with only its argument clipped to
  [1e-15, 1 - 1e-15]).
* ``summary`` -- every nonempty slice (NATIONAL, TEXAS_AM, FIRST_FOUR_TEAM_GAMES, COLD_START) x scope (POOLED,
  FIT_2016_2022, COMPARISON_EXPOSED_2023, each season) x model row with Brier/log-loss or ridge MAE/MSE/RMSE, fixed
  decile calibration tables (descriptive only) and, for the trees, model-minus-control differences on identical games.

Every record carries RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED and predictive skill NOT_ESTABLISHED.
2023 is an already exposed descriptive comparison, never a blind test; nothing here is PIT eligible, a forecast, a
calibration or a skill, champion or causal claim, and an adverse result is a valid result.

The reader (:class:`BoostingComparison`) verifies the location, manifest, schema, parent BLOB, every record's exact
members and JSON types, every collection's membership and order, the tree structures, a fresh stdlib traversal of every
view (margins exact, probabilities within 1e-12 of the stored witnesses), the served pairs, every score and summary
(floating log-loss values numerically within 1e-12, every exact field exactly), the content and database identities
and the pinned profile, then serves the five grains with exact selector and paging rules. It imports no modeling
package.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import sqlite3
import zlib
from decimal import (ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, InvalidOperation, Overflow,
                     localcontext)
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics import readonly_sqlite

# --------------------------------------------------------------------------------------------- identity and scope

POPULATION = "national_shallow_boosting_comparison_2016_2023"
DB_FILE = "national_shallow_boosting_comparison.sqlite"
CONTRACT_ID = "BAT-736-NATIONAL-SHALLOW-BOOSTING-COMPARISON-2016-2023-V1.0"
CONTRACT_REL = "configs/national_shallow_boosting_comparison_2016_2023_contract.json"
CONTENT_SCHEMA = "BAS-SHALLOW-BOOSTING-COMPARISON-CONTENT-1"
DATABASE_SCHEMA = "BAS-SHALLOW-BOOSTING-COMPARISON-DATABASE-1"
DB_SCHEMA = "BAS-SHALLOW-BOOSTING-COMPARISON-DB-1"
EXPORT_SCHEMA = "BAS-SHALLOW-BOOSTING-TREE-EXPORT-1"
CONTENT_STAGE = "shallow-boosting-comparison-content"
DATABASE_STAGE = "shallow-boosting-comparison-database"
PARENT_POPULATION = "national_retrospective_reference_2016_2023"
PARENT_DB_FILE = "national_retrospective_reference.sqlite"

STUDY_SEASONS = (2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023)
FIT_SEASONS = (2016, 2017, 2018, 2019, 2020, 2021, 2022)
COMPARISON_SEASONS = (2023,)
PARTITION_FIT = "FIT_2016_2022"
PARTITION_COMPARISON = "COMPARISON_EXPOSED_2023"
PARTITIONS = {PARTITION_FIT: FIT_SEASONS, PARTITION_COMPARISON: COMPARISON_SEASONS}
PARTITION_IDS = tuple(PARTITIONS)
#: The parent's own partition of each frozen partition (preserved separately as a witness, never served as ours).
PARENT_PARTITIONS = {PARTITION_FIT: "SPLIT-DEV-HIST", PARTITION_COMPARISON: "SPLIT-DEV-SEL"}
VIEWS = ("A", "B")
TAMU_KEY = "org:697"

LABELS = {
    "evidence_label": "RETROSPECTIVE_RESEARCH",
    "trust_state": "UNTRUSTED_SHADOW",
    "pit_eligibility": "PIT_NOT_ADMITTED",
    "predictive_skill": "NOT_ESTABLISHED",
    "calibration": "NOT_ESTABLISHED_DESCRIPTIVE_DECILE_TABLES_ONLY",
    "forecast_status": "NOT_A_FORECAST",
    "champion": "NO_CHAMPION_SELECTED",
    "causal_claim": "NONE",
    "comparison_2023": "ALREADY_EXPOSED_DESCRIPTIVE_COMPARISON_NOT_BLIND",
    "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
    "fit_authority": "TP65_RESEARCH_AUTHORITY_TWO_FROZEN_DEFINITIONS_FIT_2016_2022_ONLY",
    "temporal_basis": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME",
    "backend": "SCIKIT_LEARN_1_9_0_BUILD_ONLY_EXPORTED_PLAIN_DATA_TREES",
    "selection": "EXPLICIT_BOOSTING_COMPARISON_SELECTION_ONLY_NEVER_A_DEFAULT",
}
RECORD_LABEL_KEYS = ("evidence_label", "trust_state", "pit_eligibility", "predictive_skill")
RECORD_LABELS = {k: LABELS[k] for k in RECORD_LABEL_KEYS}

# --------------------------------------------------------------------------------------------- models

PARENT_NULL = "NULL_HALF_V1"
PARENT_SMOOTHED = "SMOOTHED_HISTORY_ODDS_V1"
PARENT_ELO = "SITE_BLIND_ELO_REFERENCE_V1"
PARENT_LOGISTIC = "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1"
PARENT_RIDGE = "PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1"
PARENT_MODELS = (PARENT_NULL, PARENT_SMOOTHED, PARENT_ELO, PARENT_LOGISTIC, PARENT_RIDGE)
PARENT_PROBABILITY_MODELS = PARENT_MODELS[:4]
TREE_DEPTH2 = "HIST_GB_DEPTH2_V1"
TREE_DEPTH3 = "HIST_GB_DEPTH3_V1"
TREE_MODELS = (TREE_DEPTH2, TREE_DEPTH3)
MODEL_IDS = (*PARENT_MODELS, *TREE_MODELS)
PROBABILITY_MODELS = (*PARENT_PROBABILITY_MODELS, *TREE_MODELS)
MARGIN_MODELS = (PARENT_RIDGE,)

SIDE_FIELDS = ("games", "win_rate", "points_for_mean", "points_against_mean", "margin_mean")
DIFFERENCE_COLUMNS = tuple(f"{f}_difference" for f in SIDE_FIELDS)
MISSING_COLUMNS = tuple(f"{f}_missing_difference" for f in SIDE_FIELDS)
COLUMNS = (*DIFFERENCE_COLUMNS, *MISSING_COLUMNS)

_BASE_PARAMS = {"loss": "log_loss", "learning_rate": 0.05, "max_iter": 100, "max_leaf_nodes": 8,
                "min_samples_leaf": 20, "l2_regularization": 1.0, "max_features": 1.0, "max_bins": 255,
                "categorical_features": None, "monotonic_cst": None, "interaction_cst": None, "warm_start": False,
                "early_stopping": False, "scoring": "loss", "validation_fraction": 0.1, "n_iter_no_change": 10,
                "tol": 1e-07, "verbose": 0, "random_state": 0, "class_weight": None}
#: The two frozen constructor option sets (TP65 Candidates): every HistGradientBoostingClassifier 1.9.0 option explicit.
TREE_PARAMS = {TREE_DEPTH2: {**_BASE_PARAMS, "max_depth": 2}, TREE_DEPTH3: {**_BASE_PARAMS, "max_depth": 3}}
BACKEND = {"distribution": "scikit-learn", "version": "1.9.0",
           "estimator": "sklearn.ensemble.HistGradientBoostingClassifier",
           "python": "CPython 3.12.10 (the pinned offline build runtime; build only, never imported by a reader)",
           "dependencies": {"numpy": "2.5.1", "scipy": "1.18.0", "joblib": "1.5.3", "threadpoolctl": "3.6.0",
                            "narwhals": "2.24.0"},
           "threads": "OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1 (frozen reproducibility setting)"}
TRAINING_RULE = {
    "games": "every FIT_2016_2022 canonical game whose parent label is DECISIVE (no 2023 game, no TIE)",
    "rows": "two oriented rows per game in canonical (season, contest key) order, view A then view B",
    "x": "the ten parent difference columns in contract order, each exact rational converted once to binary64 "
         "(float(Fraction)); the missing-indicator differences are integers; known redundant columns are retained",
    "y": "view A: y_A; view B: 1 - y_A (classes [0, 1])",
    "sample_weight": "1/2 for every oriented row",
    "fit": "HistGradientBoostingClassifier(**constructor).fit(X, y, sample_weight=w): no early stopping, no "
           "validation split, no search, no calibration, no refit, no winner selection",
    "repeats": "the same exact definition may be executed again only to prove determinism or to reproduce it "
               "independently; every execution is counted and must export identical bytes",
}
MODELS: dict[str, dict[str, Any]] = {
    model_id: {"model_id": model_id, "version": 1, "family": "SHALLOW_HISTOGRAM_GRADIENT_BOOSTING",
               "output": "WIN_PROBABILITY", "backend": BACKEND, "constructor": TREE_PARAMS[model_id],
               "columns": list(COLUMNS), "fit_seasons": list(FIT_SEASONS), "training": TRAINING_RULE,
               "role": "FROZEN_RESEARCH_DEFINITION_FIXED_BEFORE_ANY_REAL_FIT_NOT_SELECTED_AFTER_RESULTS"}
    for model_id in TREE_MODELS}

# --------------------------------------------------------------------------------------------- frozen rules

#: The plain-data export of one fitted ensemble (TP65 Tree schema).
NODE_FIELDS = {"value": "f", "count": "i", "feature_idx": "i", "num_threshold": "f", "missing_go_to_left": "b",
               "left": "i", "right": "i", "gain": "f", "depth": "i", "is_leaf": "b", "bin_threshold": "i",
               "is_categorical": "b", "bitset_idx": "i"}
TREE_EXPORT = {
    "schema": EXPORT_SCHEMA,
    "content": "baseline (the backend's binary64 _baseline_prediction) and 100 stages in fit order, one binary tree per "
               "stage, each a list of nodes with the 13 typed node fields of the backend's predictor node record",
    "node_fields": NODE_FIELDS,
    "rules": ["baseline, every value, num_threshold and gain is a finite binary64 (JSON number); every index, count, "
              "feature, depth and bin field is a JSON integer (never a boolean); every flag is a JSON boolean",
              "node 0 is the root at depth 0; an internal node has feature_idx 0..9, a finite threshold, children in "
              "range, distinct and at depth + 1; a leaf has left = right = 0",
              "every node is reachable from the root exactly once (no cycle, no dangling or shared node)",
              "no categorical split and no bitset (is_categorical false, bitset_idx 0); depth <= the model's "
              "max_depth; at most max_leaf_nodes leaves; exactly max_iter stages",
              "a leaf value already includes the learning rate; it is never multiplied again",
              "no pickle, plugin, callable or executable serialization; the export SHA-256 is the canonical JSON of "
              "{baseline, stages}"],
}
INFERENCE_RULE = ("z starts at the finite binary64 baseline; in each of the 100 stages in contract order the tree is "
                  "traversed from node 0: left when x[feature_idx] <= num_threshold, otherwise right (a NaN, which "
                  "no real feature is, follows missing_go_to_left); z = z + leaf value in binary64 and math.isfinite(z) "
                  "is checked after every addition and again before the sigmoid (a nonfinite intermediate is "
                  "TREE_ESTIMATE_MISMATCH reason TREE_MARGIN_NONFINITE); stable sigmoid: z >= 0: 1/(1 + exp(-z)), "
                  "z < 0: e = exp(z), e/(1 + e); q is finite in [0, 1]")
RAW_Q_RULE = ("the build derives q_A and q_B of every canonical game by the stdlib traversal of its A and B feature "
              "views and stores them once as canonical repr strings raw_q_a_repr / raw_q_b_repr (with the exact "
              "margins raw_z_a_repr / raw_z_b_repr) on both oriented estimate records; repr(float(text)) equals the "
              "text, finite, in [0, 1]; the build-only backend predict_proba agrees within 1e-12; a reader "
              "recomputes the margins exactly and the probabilities within absolute 1e-12 and derives the served "
              "pair from the stored q values, never from a fresh libm recomputation; tolerance never permits "
              "altering a stored value or skipping the profile pin")
#: The fixed decimal context of the served pair (TP65 Serving probability rule).
DECIMAL_CONTEXT = {"prec": 50, "rounding": "ROUND_HALF_EVEN", "Emin": -999999, "Emax": 999999, "capitals": 1,
                   "clamp": 0, "flags": [], "traps": ["InvalidOperation", "DivisionByZero", "Overflow"]}
SERVING_RULE = ("q_A = float(raw_q_a_repr), q_B = float(raw_q_b_repr), both finite in [0, 1]; p_A = (q_A + (1.0 - "
                "q_B)) / 2.0 in binary64 with the inner subtraction first, finite in [0, 1]; within decimal.localcontext("
                "the fixed DECIMAL_CONTEXT): served_A = Decimal.from_float(p_A).quantize(Decimal('0.000000000001'), "
                "rounding=ROUND_HALF_EVEN), served_B = Decimal(1) - served_A exactly; both serialized with 12 fixed "
                "places, zero normalized; the ambient decimal context, flags and traps are never read or changed; B "
                "is never rounded independently and A is never replaced")
LOG_CLIP = 1e-15
CLIP_CONVENTION = "CLIPPED_LOG_ARGUMENT_1E-15"
SCORE_RULE = {
    "parent_families": "the five unchanged C56 game scores (one A-oriented record per game and model) embedded byte for "
                       "byte (parent_score, its line SHA-256) with their metric fields copied unchanged",
    "trees": "Brier = (Fraction(served decimal p_A) - y_A)^2 as an exact rational; log loss: q = p_A if y_A = 1 else "
             "1 - p_A (exact), converted once to binary64, only the logarithm argument clipped to [1e-15, 1 - 1e-15], "
             "-math.log, repr text; served probabilities, Brier and calibration are never clipped",
    "ties": "a TIE label (none among the accepted targets) keeps label_state TIE, y_A null and unscored_reason "
            "LABEL_TIE: the probability families are unscored with null metrics and explicit support counts, the record "
            "is never dropped and no 0.5 target is invented; the unchanged parent RIDGE keeps its valid tied margin "
            "metrics; half credit belongs only to the parent's prior win rates and Elo updates",
    "reader_portability": "a reader recomputes each tree log loss on its own host and compares it numerically within "
                          "absolute 1e-12 (never demanding repr text equality); aggregates are checked from the stored "
                          "canonical per-game values in frozen game order with math.fsum within the same tolerance; "
                          "Brier values, totals and means, counts, cohort keys, served decimals and calibration stay "
                          "exact",
}
SLICES = {
    "NATIONAL": "every accepted selected canonical game",
    "TEXAS_AM": "exact org:697 on either parent participant key (never a name proxy)",
    "FIRST_FOUR_TEAM_GAMES": "either parent feature side has fewer than 4 eligible prior games (the parent per-game flag, "
                             "independently re-derived and required equal)",
    "COLD_START": "either parent feature side has 0 eligible prior games (the parent per-game flag, independently "
                  "re-derived and required equal)",
}
SLICE_IDS = tuple(SLICES)
SCOPES = (("POOLED", STUDY_SEASONS), (PARTITION_FIT, FIT_SEASONS), (PARTITION_COMPARISON, COMPARISON_SEASONS),
          *[(f"SEASON_{s}", (s,)) for s in STUDY_SEASONS])
SCOPE_IDS = tuple(scope for scope, _seasons in SCOPES)
DECILE_BINS = 10
CALIBRATION = {"orientation": "canonical parent A", "families": "the six probability families (four unchanged C56 "
                                                                "probability controls and the two trees); ridge has no "
                                                                "probability or calibration",
               "bins": DECILE_BINS, "edges": "i/10 for i = 0..10; bin i = min(floor(10 p_exact_served), 9); intervals "
                                             "[i/10, (i+1)/10), the last closed at 1",
               "per_bin": "integer count, a_wins, exact rational mean served probability and exact observed A win rate "
                          "of the scored decisive games; an empty bin has count 0 and null means and rates",
               "interpretation": "fixed descriptive tables only, no calibrated-forecast or skill claim; POOLED, FIT, "
                                 "COMPARISON and season summaries overlap descriptively and never sum as partitions"}
SUMMARY_RULE = {
    "rows": "one row per frozen slice x scope x model in the order slices, scopes (POOLED, FIT_2016_2022, "
            "COMPARISON_EXPOSED_2023, SEASON_2016..SEASON_2023), models (five parent then two trees); a slice and scope "
            "without a selected game has no row (never a fabricated zero-count mean)",
    "probability_metrics": "brier total and mean (exact rationals), log-loss total (math.fsum of the stored per-game "
                           "values in canonical game order) and mean (total / count), the fixed decile calibration",
    "margin_metrics": "parent ridge only: MAE and MSE (exact rationals), RMSE = math.sqrt(float(MSE)) (repr)",
    "comparisons": "tree rows carry the model-minus-control differences against each of the four C56 probability "
                   "controls on identical scored game keys (brier mean difference exact, log-loss mean difference "
                   "binary64); no significance, lift threshold, selection or champion",
    "selection": "applicable filters intersect canonical game keys first; the summary is re-derived over exactly the "
                 "selected games with the frozen slice, scope, metric and calibration rules",
    "parent_witness": "the parent-family rows of the canonical summary must equal the parent's own summary rows "
                      "(scope POOLED = POOLED 2016-2023, FIT_2016_2022 = SPLIT-DEV-HIST, COMPARISON_EXPOSED_2023 = "
                      "SPLIT-DEV-SEL, SEASON_s = season s)",
}
FOREKNOWLEDGE = {
    "exposure": "2016-2023 outcomes, the C56 parent scores and summaries (2023 included) were published before these two "
                "definitions were frozen by the manager's TP65 v6 design; the worker read the parent summary values "
                "while qualifying the parent before any real fit; no tree result was known before the rules were "
                "committed",
    "comparison_2023": "already exposed descriptive comparison, never a blind or protected test",
    "protected": "no 2024, 2025 or 2026 outcome is selected, read for modeling or scored; the parent holds only "
                 "2016-2023 targets",
    "adverse_results": "both trees losing to the controls is a valid completed result; integrity and runtime failures "
                       "remain failures",
}
TIME_RULE = {"query_state": "no as-of, cutoff, effective or known-at query state exists: every provided --as-of is "
                            "refused (AS_OF_STATE_NOT_SUPPORTED) before parsing and --require-pit is refused "
                            "(TREE_PIT_NOT_ADMITTED)",
             "source_clock": "calendar date order of the accepted C56 targets only; not publication time",
             "build_clock": "the run manifest provenance issued_at_utc is the build time, never identity-bound"}
NUMERIC_CONTRACT = {
    "arithmetic": "IEEE-754 binary64; every reduction math.fsum; math.exp, math.log and math.sqrt of the pinned "
                  "CPython 3.12.10 at build time",
    "rationals": "exact {numerator, denominator} in lowest terms; integers are JSON integers only (a boolean or an "
                 "integral float is not an integer)",
    "decimal12": "12 fixed places, half-even, zero normalized; exact rationals by integer arithmetic; a served "
                 "probability by the fixed DECIMAL_CONTEXT",
    "canonical_json": "json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) as UTF-8",
    "tolerances": {"backend_predict_proba_vs_stdlib_q": "1e-12 (build only)", "reader_q_recomputation": "1e-12",
                   "reader_log_loss_and_aggregates": "1e-12", "margins": "exact", "every other field": "exact"},
}

# --------------------------------------------------------------------------------------------- query contract

GRAINS = {"tree-feature": "features", "tree-parameter": "parameters", "tree-estimate": "estimates",
          "tree-score": "scores", "tree-summary": "summary"}
SELECTOR_NAMES = ("season", "team", "contest", "model", "partition", "slice")
APPLICABILITY = {"tree-feature": ("season", "team", "contest", "partition"),
                 "tree-parameter": ("model",),
                 "tree-estimate": ("season", "team", "contest", "model", "partition"),
                 "tree-score": ("season", "team", "contest", "model", "partition"),
                 "tree-summary": ("season", "team", "contest", "model", "partition", "slice")}
#: The model namespace each grain's collection carries (a grammar-valid model outside it matches zero rows).
GRAIN_MODELS = {"tree-parameter": TREE_MODELS, "tree-estimate": TREE_MODELS, "tree-score": MODEL_IDS,
                "tree-summary": MODEL_IDS}
SEASON_RE = re.compile(r"[0-9]{4}\Z")
TEAM_KEY_RE = re.compile(r"org:[0-9]{1,12}\Z")
TEAM_DIGITS_RE = re.compile(r"[0-9]{1,12}\Z")
CONTEST_KEY_RE = re.compile(r"ncaa:[0-9]{1,12}\Z")
MODEL_RE = re.compile(r"[A-Z][A-Z0-9_]{0,99}\Z")
PAGE_RE = re.compile(r"-?[0-9]{1,12}\Z")
IDENTITY_RE = re.compile(r"[0-9a-f]{64}\Z")
DEC12_RE = re.compile(r"-?(0|[1-9][0-9]*)\.[0-9]{12}\Z")
PAGE_BOUND = 10 ** 12
DEFAULT_LIMIT = 50
TEAM_TEXT_LIMIT = 200
SELECTORS = {
    "season": "string ASCII [0-9]{4} after U+0020-only trimming, or a typed int 1000..9999 (never a boolean); raw "
              "Unicode Cc controls and lone surrogates refused before trimming; a valid unknown year selects no game",
    "team": "exact org:<1-12 ASCII digits>, bare 1-12 ASCII digits (org:<digits>, no numeric normalization) or a parent "
            "source team name of the game's own season, matched by the committed parent rule (casefolded); a name "
            "matching two keys in one season is TEAM_AMBIGUOUS; a well-formed unknown team selects no game; matches "
            "either participant",
    "contest": "exact ncaa:<1-12 ASCII digits>; no bare digits and no numeric normalization; a valid unknown key "
               "selects no game",
    "model": "a str fullmatching [A-Z][A-Z0-9_]{0,99} after U+0020-only trimming (otherwise MODEL_INVALID with a "
             "type-only diagnostic); a grammar-valid model outside the grain's collection matches zero rows",
    "partition": "exactly FIT_2016_2022 or COMPARISON_EXPOSED_2023",
    "slice": "summary only: NATIONAL, TEXAS_AM, FIRST_FOUR_TEAM_GAMES or COLD_START (default NATIONAL); frozen per "
             "canonical game",
    "applicability": {grain: list(names) for grain, names in APPLICABILITY.items()},
    "selection": "applicable filters intersect canonical game keys before record selection, summaries or paging; an "
                 "unknown or disjoint selection gives zero rows, total 0, returned 0, next_offset null",
    "paging": "default limit 50 / offset 0; --all conflicts with any explicitly supplied limit or offset, zero included "
              "(PAGING_CONFLICT); strings: raw Cc and lone surrogates refused before U+0020 trimming, then an optional "
              "minus and 1-12 ASCII digits; typed ints with absolute value < 10**12 (bool, float and objects invalid; "
              "bounds compared before any text conversion); negative values NEGATIVE_LIMIT / NEGATIVE_OFFSET; limit 0 "
              "is count-only (rows [], returned 0, next_offset = offset when offset < total else null); a positive page "
              "advances to offset + returned while rows remain, else null",
    "expect_identity": "--expect-identity: [0-9a-f]{64} or STALE_TREE_IDENTITY before any file access; omitted means "
                       "the committed profile pin applies; no --expected-identity alias",
}
PRECEDENCE = ["parser_mode_conflict", "require_pit", "provided_as_of", "grain", "season", "team", "contest", "model",
              "partition", "slice", "selector_applicability", "all_explicit_paging_conflict",
              "limit_type_and_bound_then_negative", "offset_type_and_bound_then_negative", "expected_identity_grammar",
              "database_literal_spelling", "manifest_literal_spelling", "native_existence_names_layout",
              "manifest_identity_schema_hash", "parent_BLOB_exacttype_bytecount_SHA_beforeparse",
              "parent_expected_schema_bounded_completecollections",
              "complete_record_collection_and_semantic_validation"]
CODES = {"argument": "ARGUMENT_INVALID", "mode_conflict": "TREE_MODE_CONFLICT", "pit": "TREE_PIT_NOT_ADMITTED",
         "asof": "AS_OF_STATE_NOT_SUPPORTED", "grain": "UNKNOWN_GRAIN", "season": "SEASON_INVALID",
         "team": "TEAM_INVALID", "team_ambiguous": "TEAM_AMBIGUOUS", "contest": "CONTEST_INVALID",
         "model": "MODEL_INVALID", "partition": "PARTITION_INVALID", "slice": "SLICE_INVALID",
         "applicability": "FILTER_NOT_APPLICABLE", "paging_conflict": "PAGING_CONFLICT", "limit": "LIMIT_INVALID",
         "offset": "OFFSET_INVALID", "negative_limit": "NEGATIVE_LIMIT", "negative_offset": "NEGATIVE_OFFSET",
         "expected_identity": "STALE_TREE_IDENTITY",
         "database_spelling_unsupported": "TREE_DATABASE_LOCATION_UNSUPPORTED",
         "database_spelling_not_literal": "TREE_DATABASE_LOCATION_NOT_LITERAL",
         "manifest_spelling_unsupported": "TREE_MANIFEST_LOCATION_UNSUPPORTED",
         "manifest_spelling_not_literal": "TREE_MANIFEST_LOCATION_NOT_LITERAL",
         "database_missing": "TREE_DATABASE_MISSING", "layout": "TREE_LOCATION_INVALID",
         "manifest_missing": "TREE_MANIFEST_MISSING", "manifest": "TREE_MANIFEST_MALFORMED",
         "meta": "TREE_META_MALFORMED", "record": "TREE_RECORD_MALFORMED", "tree": "TREE_STRUCTURE_MISMATCH",
         "features": "TREE_FEATURE_MISMATCH", "labels": "TREE_LABEL_MISMATCH", "fit": "TREE_FIT_MISMATCH",
         "estimate": "TREE_ESTIMATE_MISMATCH", "score": "TREE_SCORE_MISMATCH", "summary": "TREE_SUMMARY_MISMATCH",
         "collection": "TREE_COLLECTION_MISMATCH", "parent": "TREE_PARENT_REFERENCE_MISMATCH",
         "parent_schema": "TREE_PARENT_SCHEMA_MISMATCH", "parent_block": "TREE_PARENT_BLOCK_MALFORMED"}
JSON_BOUNDARY = ("every stored JSON text is decoded with NaN, Infinity, a float literal beyond binary64 range, an "
                 "integer beyond the interpreter's digit limit and nesting beyond the decoder's depth refused by the "
                 "stage's own code (manifest, meta or record) and reason (JSON_NONFINITE_NUMBER, "
                 "JSON_INTEGER_TOO_LONG, JSON_NESTING_TOO_DEEP, JSON_LONE_SURROGATE); a boolean is never an integer "
                 "or a float; rationals are bounded and checked before any float conversion; ordinary Unicode and the "
                 "exact allowed JSON types are preserved; cross-field and collection authority outranks a merely "
                 "self-consistent hash; no error message stringifies an oversized integer, a nested object or a lone "
                 "surrogate")
ERROR_ENVELOPE = ("controlled exit 2, stdout empty, stderr one UTF-8 JSON object {refused: <code>, error: <detail>} and a "
                  "newline; no traceback, no catch-all, no change of Python's integer-to-text or recursion limits")
PATH_RULE = ("the database and an explicit manifest each pass the BAT-717 literal local-file spelling check before any "
             "filesystem access (UNC, device and namespace spellings refused on Windows; POSIX backslashes are "
             "ordinary characters); on Windows each component is respelled with the genuine on-disk long name of the "
             "entry it resolves to (8.3 and case-equivalent spellings validate the actual population/sha256/identity/"
             "basename layout, a junction keeps its own name and its target never names the identity); long, "
             "relative, Unicode, extended and junction spellings of the genuine release serve identical bytes; a "
             "missing path creates nothing; the default manifest is <data>/manifests/" + POPULATION + "/sha256/"
             "<identity>/run_manifest.json; an explicit manifest may be a genuine copy but must bind this database")

# --------------------------------------------------------------------------------------------- layout

RECORD_TABLES = ("features", "labels", "parameters", "estimates", "scores", "summary")
SEASONAL_TABLES = ("features", "labels", "estimates", "scores")
KEY_FIELDS = {"features": "feature_key", "labels": "label_key", "parameters": "parameter_key",
              "estimates": "estimate_key", "scores": "score_key", "summary": "summary_key"}
RECORD_TYPES = {"features": "TREE_FEATURE", "labels": "TREE_LABEL", "parameters": "TREE_PARAMETER",
                "estimates": "TREE_ESTIMATE", "scores": "TREE_SCORE", "summary": "TREE_SUMMARY"}
BLOCK_LAYOUT = tuple([(table, str(season)) for table in SEASONAL_TABLES for season in STUDY_SEASONS] +
                     [("parameters", "GLOBAL"), ("summary", "GLOBAL")])
DDL = (
    ("table", "blocks", "CREATE TABLE blocks (ord INTEGER PRIMARY KEY, record_table TEXT NOT NULL, segment TEXT NOT "
                        "NULL, records INTEGER NOT NULL, first_key TEXT, last_key TEXT, lines_sha256 TEXT NOT NULL, "
                        "block BLOB NOT NULL)"),
    ("table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"),
    ("table", "parent_reference", "CREATE TABLE parent_reference (singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
                                  "byte_count INTEGER NOT NULL, sha256 TEXT NOT NULL, snapshot BLOB NOT NULL)"),
)
TABLES = ("meta", "blocks", "parent_reference")
META_KEYS = ("schema_version", "contract_id", "contract_sha256", "rules_sha256", "content_identity", "labels",
             "parent", "row_counts", "lines_sha256")
RECORD_ORDER = {
    "features": "(season, contest_key, view A then B)", "labels": "(season, contest_key)",
    "parameters": "declared tree model order", "estimates": "(season, contest_key, view A then B, declared tree "
                                                              "model order)",
    "scores": "(season, contest_key, the five parent models in order then the two trees)",
    "summary": "(frozen slice order, scope order POOLED / FIT_2016_2022 / COMPARISON_EXPOSED_2023 / SEASON_2016.."
               "SEASON_2023, declared seven-model order)",
    "sort": "canonical binary Unicode code-point order of the key strings, never a locale",
    "parent_witnesses": "the parent's exact lines keep their original parent order inside the embedded BLOB",
}
LAYOUT = {"database": {"file": DB_FILE, "page_size": 4096, "journal_mode": "OFF", "ddl": [list(d) for d in DDL],
                       "tables": list(TABLES), "meta_keys": list(META_KEYS),
                       "block_layout": [list(b) for b in BLOCK_LAYOUT],
                       "blocks": "one zlib (level 9) block per (record table, segment): a season for the seasonal "
                                 "tables, GLOBAL for parameters and summary; records, first/last key and the SHA-256 "
                                 "of the uncompressed JSONL lines",
                       "parent_reference": "exactly one row: singleton 1, byte_count, sha256 and the byte-exact "
                                           "parent database as a BLOB"},
          "location": f"<data>/canonical/{POPULATION}/sha256/<database identity>/{DB_FILE}; manifest at <data>/"
                      f"manifests/{POPULATION}/sha256/<database identity>/run_manifest.json with members identity, "
                      "identity_document, content_identity, content_document and provenance; create-only (an "
                      "identical rebuild is ALREADY_PRESENT_IDENTICAL, differing bytes REFUSED_IMMUTABLE_COLLISION)",
          "record_order": RECORD_ORDER,
          "checkpoint_unit": "a run of consecutive canonical games (--chunk-size games): their feature, label, estimate "
                             "and score lines; parameters and summary follow"}
PARENT_RULE = {
    "representation": "one byte-exact complete C56 SQLite snapshot BLOB inside the private release; never base64, "
                      "executable serialization or Git data",
    "serving": "verify the BLOB storage type, exact byte count and full SHA-256 against the committed pin before any "
               "SQLite parse; standard-library in-memory deserialize, query_only ON, fixed whitelisted SELECTs, no "
               "extension and no stored SQL; exact schema, meta keys and 34 blocks; bounded decompression (8 MiB per "
               "block), complete stream, no trailing data, the exact total and six collection counts; every per-table "
               "line digest equals the parent's own meta claim; all records read and every witness validated",
    "identity": "the new content and database identity documents bind the parent BLOB SHA-256, byte count, identities "
                "and complete witness counts as well as every new record",
    "copy_precondition": "before the copy the original passes the literal local-file spelling, existence, layout and "
                         "hash checks; the exact bytes are copied create-only and the original is never written",
}


def rules_document() -> dict[str, Any]:
    """Every frozen rule the contract restates (meta ``rules_sha256`` and the content document), as a fresh deep copy so
    no caller can alias and alter the module's frozen constants."""
    return copy.deepcopy({
        "contract_id": CONTRACT_ID, "population": POPULATION, "labels": LABELS, "record_labels": list(RECORD_LABEL_KEYS),
        "seasons": {"study": list(STUDY_SEASONS), "fit": list(FIT_SEASONS), "comparison": list(COMPARISON_SEASONS)},
        "partitions": {k: list(v) for k, v in PARTITIONS.items()}, "parent_partitions": PARENT_PARTITIONS,
        "models": MODELS, "model_ids": list(MODEL_IDS), "tree_models": list(TREE_MODELS),
        "parent_models": list(PARENT_MODELS), "probability_models": list(PROBABILITY_MODELS),
        "margin_models": list(MARGIN_MODELS), "columns": list(COLUMNS), "tree_export": TREE_EXPORT,
        "inference": INFERENCE_RULE, "raw_q": RAW_Q_RULE, "decimal_context": DECIMAL_CONTEXT, "serving": SERVING_RULE,
        "log_clip": repr(LOG_CLIP), "clip_convention": CLIP_CONVENTION, "scores": SCORE_RULE, "slices": SLICES,
        "scopes": [[scope, list(seasons)] for scope, seasons in SCOPES], "calibration": CALIBRATION,
        "summary": SUMMARY_RULE, "foreknowledge": FOREKNOWLEDGE, "time": TIME_RULE, "numeric": NUMERIC_CONTRACT,
        "grains": GRAINS, "selectors": SELECTORS, "precedence": PRECEDENCE, "codes": CODES,
        "json_boundary": JSON_BOUNDARY, "error_envelope": ERROR_ENVELOPE, "paths": PATH_RULE, "layout": LAYOUT,
        "parent": PARENT_RULE, "field_types": FIELD_TYPES, "subspecs": SUBSPECS, "record_types": RECORD_TYPES,
        "key_fields": KEY_FIELDS})


# --------------------------------------------------------------------------------------------- errors

class BoostingError(ValueError):
    """A refused build input, selection or release; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise BoostingError(code, message)


def describe(value: Any) -> str:
    """A bounded diagnostic of an untrusted value: never the text of an oversized integer, a nested object or a lone
    surrogate (only short printable ASCII strings and small integers are quoted)."""
    if type(value) is str:
        if len(value) <= 64 and all(0x20 <= ord(c) < 0x7F for c in value):
            return repr(value)
        return f"<str of {len(value)} characters>"
    if type(value) is int:
        if -10 ** 18 < value < 10 ** 18:
            return str(value)
        return f"<{'negative ' if value < 0 else ''}int of {value.bit_length()} bits>"
    return f"<{type(value).__name__}>"


# --------------------------------------------------------------------------------------------- canonical values

def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_line(value: Any) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def lines_sha256(lines: Iterable[str]) -> str:
    return sha256_bytes("".join(line + "\n" for line in lines).encode("utf-8"))


def keys_sha256(keys: Iterable[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


def rules_sha256() -> str:
    return sha256_bytes(canonical_json_bytes(rules_document()))


def model_sha256(model_id: str) -> str:
    return sha256_bytes(canonical_json_bytes(MODELS[model_id]))


def is_int(value: Any) -> bool:
    return type(value) is int


def rational(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def frac(value: dict[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def decimal_text(value: Fraction) -> str:
    """An exact rational rounded half-even to 12 places by integer arithmetic (negative zero normalized)."""
    sign = "-" if value < 0 else ""
    n, d = abs(value.numerator), value.denominator
    scaled, rem = divmod(n * 10 ** 12, d)
    if rem * 2 > d or (rem * 2 == d and scaled % 2 == 1):
        scaled += 1
    whole, part = divmod(scaled, 10 ** 12)
    text = f"{sign}{whole}.{part:012d}"
    return "0.000000000000" if text == "-0.000000000000" else text


_DEC12_CONTEXT = Context(prec=80, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999, capitals=1, clamp=0, flags=[],
                         traps=[InvalidOperation, DivisionByZero, Overflow])
_QUANTUM = Decimal("0.000000000001")


def dec12(value: float) -> str:
    """A finite binary64's exact decimal expansion rounded half-even to 12 places in a fixed context (zero normalized)."""
    if type(value) is not float or not math.isfinite(value):
        _refuse("TREE_SUMMARY_MISMATCH", "a decimal display needs a finite binary64 value")
    with localcontext(_DEC12_CONTEXT):
        quantized = Decimal(value).quantize(_QUANTUM, rounding=ROUND_HALF_EVEN)
    if quantized == 0:
        return "0.000000000000"
    return format(quantized, "f")


def _serving_context() -> Context:
    return Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999, capitals=1, clamp=0, flags=[],
                   traps=[InvalidOperation, DivisionByZero, Overflow])


def served_pair(q_a: float, q_b: float) -> tuple[str, str]:
    """The served paired probability of A and its exact complement from the stored raw witnesses (SERVING_RULE)."""
    for name, q in (("q_A", q_a), ("q_B", q_b)):
        if type(q) is not float or not math.isfinite(q) or not 0.0 <= q <= 1.0:
            _refuse("TREE_ESTIMATE_MISMATCH", f"{name} is not a finite binary64 in [0, 1]")
    p_a = (q_a + (1.0 - q_b)) / 2.0
    if not math.isfinite(p_a) or not 0.0 <= p_a <= 1.0:
        _refuse("TREE_ESTIMATE_MISMATCH", "the paired probability is not finite in [0, 1]")
    with localcontext(_serving_context()):
        served_a = Decimal.from_float(p_a).quantize(_QUANTUM, rounding=ROUND_HALF_EVEN)
        served_b = Decimal(1) - served_a
    return _fixed12(served_a), _fixed12(served_b)


def _fixed12(value: Decimal) -> str:
    if value == 0:
        return "0.000000000000"
    text = format(value, "f")
    if not DEC12_RE.match(text):
        _refuse("TREE_ESTIMATE_MISMATCH", "a served probability is not a 12-place decimal")
    return text


def dec_fraction(text: str) -> Fraction:
    """The exact value of a 12-place decimal string (Decimal construction from text is exact and context free)."""
    return Fraction(Decimal(text))


def log_loss_value(p_a: Fraction, y: int) -> float:
    q = p_a if y == 1 else 1 - p_a
    clipped = min(max(float(q), LOG_CLIP), 1.0 - LOG_CLIP)
    return -math.log(clipped)


def repr_float(text: Any) -> float | None:
    """The float of a canonical repr string (repr(float(text)) == text, finite), or None."""
    if type(text) is not str or len(text) > 32:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value) or repr(value) != text:
        return None
    return value


def sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def partition_of(season: int) -> str:
    return PARTITION_FIT if season in FIT_SEASONS else PARTITION_COMPARISON


def sample_state(season: int) -> str:
    return "IN_SAMPLE_FIT_2016_2022_NOT_A_LABEL_ANCHOR" if season in FIT_SEASONS else \
        "OUT_OF_FIT_EXPOSED_2023_COMPARISON"


def metric_kind(model_id: str) -> str:
    return "MARGIN" if model_id in MARGIN_MODELS else "PROBABILITY"


def scope_of(scope_id: str) -> tuple[int, ...]:
    return dict(SCOPES)[scope_id]


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
        raise _InvalidNumber("a float literal beyond binary64 range")
    return value


def _no_constant(text: str) -> Any:
    raise _InvalidNumber("NaN or Infinity is not a JSON number")


def loads_untrusted(text: Any, code: str, where: str) -> Any:
    """Decode stored JSON: NaN, Infinity, a float literal beyond binary64 range, an integer beyond the interpreter's
    digit limit and nesting beyond the decoder's depth are refused with ``code`` and their reason (never a
    traceback); other syntax errors are refused with ``code`` too."""
    try:
        return json.loads(text, parse_float=_finite_float, parse_constant=_no_constant)
    except _InvalidNumber as exc:
        raise BoostingError(code, f"{where}: {JSON_NONFINITE_NUMBER} ({exc})") from None
    except RecursionError:
        raise BoostingError(code, f"{where}: {JSON_NESTING_TOO_DEEP}") from None
    except ValueError as exc:
        if "integer string conversion" in str(exc) or "Exceeds the limit" in str(exc):
            raise BoostingError(code, f"{where}: {JSON_INTEGER_TOO_LONG}") from None
        raise BoostingError(code, f"{where}: not JSON") from None
    except TypeError:
        raise BoostingError(code, f"{where}: not JSON text") from None


def untrusted_canonical(value: Any, code: str, where: str) -> bytes:
    try:
        return canonical_json_bytes(value)
    except UnicodeEncodeError:
        raise BoostingError(code, f"{where}: {JSON_LONE_SURROGATE} (not Unicode scalar text)") from None
    except RecursionError:
        raise BoostingError(code, f"{where}: {JSON_NESTING_TOO_DEEP}") from None
    except ValueError:
        raise BoostingError(code, f"{where}: {JSON_NONFINITE_NUMBER}") from None


# --------------------------------------------------------------------------------------------- record types

_NONE = type(None)
SUBSPECS: dict[str, dict[str, str]] = {
    "training": {"seasons": "li", "games": "i", "oriented_rows": "i", "positive_rows": "i", "row_weight": "q",
                 "excluded_tie_games": "i", "comparison_games_excluded": "i", "rows_sha256": "s"},
    "agreement": {"state": "s", "views": "i", "max_abs_difference_repr": "s", "tolerance_repr": "s", "repeat_fits": "i",
                  "repeat_exports_identical": "b", "rule": "s"},
}
FIELD_TYPES: dict[str, dict[str, str]] = {
    "features": {"record_type": "s", "feature_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
                 "partition": "s", "parent_partition": "s", "view": "s", "team_key": "s", "team_name": "s",
                 "opponent_key": "s", "opponent_name": "s", "a_key": "s", "b_key": "s", "team_prior_games": "i",
                 "opponent_prior_games": "i", "texas_am_game": "b", "first_four_team_games": "b", "cold_start": "b",
                 "design_rational": "lq", "design": "lf", "parent_feature_line_sha256": "s",
                 **{k: "s" for k in RECORD_LABEL_KEYS}},
    "labels": {"record_type": "s", "label_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
               "partition": "s", "a_key": "s", "b_key": "s", "a_points": "i", "b_points": "i", "label_state": "s",
               "y_a": "i?", "unscored_reason": "s?", "label_use": "s", "parent_label_line_sha256": "s",
               **{k: "s" for k in RECORD_LABEL_KEYS}},
    "parameters": {"record_type": "s", "parameter_key": "s", "model_id": "s", "model_sha256": "s", "definition": "j",
                   "training": "@training", "baseline": "f", "stages": "j", "stage_count": "i", "node_count": "i",
                   "leaf_count": "i", "max_depth_seen": "i", "export_sha256": "s", "backend_agreement": "@agreement",
                   **{k: "s" for k in RECORD_LABEL_KEYS}},
    "estimates": {"record_type": "s", "estimate_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
                  "partition": "s", "model_id": "s", "model_sha256": "s", "orientation": "s", "team_key": "s",
                  "team_name": "s", "opponent_key": "s", "opponent_name": "s", "a_key": "s", "b_key": "s",
                  "sample_state": "s", "raw_z_a_repr": "s", "raw_z_b_repr": "s", "raw_q_a_repr": "s",
                  "raw_q_b_repr": "s", "game_grain_probability_a": "d", "probability": "d",
                  "opponent_probability": "d", "feature_record_sha256": "s", "parameter_record_sha256": "s",
                  **{k: "s" for k in RECORD_LABEL_KEYS}},
    "scores": {"record_type": "s", "score_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
               "partition": "s", "model_id": "s", "model_sha256": "s", "metric_kind": "s", "score_source": "s",
               "a_key": "s", "b_key": "s", "a_team_name": "s", "b_team_name": "s", "label_state": "s", "y_a": "i?",
               "score_state": "s", "unscored_reason": "s?", "sample_state": "s", "texas_am_game": "b",
               "first_four_team_games": "b", "cold_start": "b", "probability_a": "d?", "probability_a_exact": "q?",
               "brier": "q?", "brier_decimal": "s?", "log_loss": "s?", "log_loss_convention": "s?", "margin_a": "d?",
               "margin_label_a": "i?", "absolute_error": "q?", "absolute_error_decimal": "s?", "squared_error": "q?",
               "squared_error_decimal": "s?", "estimate_record_sha256": "s", "label_record_sha256": "s",
               "parent_score": "j", "parent_score_line_sha256": "s?", **{k: "s" for k in RECORD_LABEL_KEYS}},
    "summary": {"record_type": "s", "summary_key": "s", "slice": "s", "scope": "s", "seasons": "li", "model_id": "s",
                "model_sha256": "s", "metric_kind": "s", "score_source": "s", "games": "i", "scored_games": "i",
                "unscored_games": "i", "unscored_by_reason": "j", "scored_by_sample_state": "j",
                "game_keys_sha256": "s", "brier_total": "q?", "brier_total_decimal": "s?", "brier_mean": "q?",
                "brier_mean_decimal": "s?", "log_loss_total": "s?", "log_loss_mean": "s?", "calibration": "j",
                "mae": "q?", "mae_decimal": "s?", "mse": "q?", "mse_decimal": "s?", "rmse": "s?", "rmse_decimal": "s?",
                "comparisons": "j", **{k: "s" for k in RECORD_LABEL_KEYS}},
}
_SCALAR_TYPES = {"s": (str,), "s?": (str, _NONE), "i": (int,), "i?": (int, _NONE), "b": (bool,), "f": (float,)}
RATIONAL_BOUND = 10 ** 400


def is_rational(value: Any) -> bool:
    if type(value) is not dict or set(value) != {"numerator", "denominator"}:
        return False
    n, d = value["numerator"], value["denominator"]
    if type(n) is not int or type(d) is not int or d <= 0 or abs(n) >= RATIONAL_BOUND or d >= RATIONAL_BOUND:
        return False
    return math.gcd(n, d) == 1


def check_type(code: str, value: Any) -> bool:
    if code in _SCALAR_TYPES:
        if code == "f":
            return type(value) is float and math.isfinite(value)
        return type(value) in _SCALAR_TYPES[code]
    if code.endswith("?") and value is None:
        return True
    base = code.rstrip("?")
    if base == "li":
        return type(value) is list and all(type(x) is int for x in value)
    if base == "lf":
        return type(value) is list and all(type(x) is float and math.isfinite(x) for x in value)
    if base == "lq":
        return type(value) is list and all(is_rational(x) for x in value)
    if base == "q":
        return is_rational(value)
    if base == "d":
        return type(value) is str and bool(DEC12_RE.match(value))
    if base == "j":
        return True
    if base.startswith("@"):
        spec = SUBSPECS[base[1:]]
        return type(value) is dict and set(value) == set(spec) and all(check_type(c, value[k]) for k, c in spec.items())
    return False


# --------------------------------------------------------------------------------------------- the parent witness

PARENT_RECORD_TABLES = ("features", "estimates", "labels", "parameters", "scores", "summary")
PARENT_SEASONAL = ("features", "estimates", "labels", "scores")
PARENT_DDL = (
    ("table", "blocks", "CREATE TABLE blocks (ord INTEGER PRIMARY KEY, record_table TEXT NOT NULL, segment TEXT NOT "
                        "NULL, records INTEGER NOT NULL, first_key TEXT, last_key TEXT, lines_sha256 TEXT NOT NULL, "
                        "block BLOB NOT NULL)"),
    ("table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"),
)
PARENT_META_KEYS = ("content_identity", "contract_id", "contract_sha256", "labels", "models", "numeric_contract",
                    "parent", "payload_sha256", "row_counts", "schema_version", "scope", "slices", "split",
                    "summary_sha256", "uncompressed_sha256")
PARENT_BLOCK_LAYOUT = tuple([(t, str(s)) for t in PARENT_SEASONAL for s in STUDY_SEASONS] +
                            [("parameters", "GLOBAL"), ("summary", "GLOBAL")])
MAX_PARENT_BLOCK = 8 * 1024 * 1024


def _parent_key(table: str, record: dict[str, Any]) -> str:
    if table == "features":
        return f"{record.get('contest_key')}|{record.get('view')}"
    if table == "estimates":
        return f"{record.get('contest_key')}|{record.get('model_id')}|{record.get('orientation')}"
    if table == "scores":
        return f"{record.get('contest_key')}|{record.get('model_id')}"
    if table == "parameters":
        return str(record.get("model_id"))
    if table == "summary":
        return "summary"
    return str(record.get("contest_key"))


def _bounded_decompress(blob: Any, where: str) -> bytes:
    if type(blob) is not bytes:
        _refuse("TREE_PARENT_BLOCK_MALFORMED", f"{where} is not a BLOB")
    stream = zlib.decompressobj()
    try:
        data = stream.decompress(blob, MAX_PARENT_BLOCK + 1)
    except zlib.error:
        raise BoostingError("TREE_PARENT_BLOCK_MALFORMED", f"{where} does not decompress") from None
    if len(data) > MAX_PARENT_BLOCK or stream.unconsumed_tail:
        _refuse("TREE_PARENT_BLOCK_MALFORMED", f"{where} decompresses beyond {MAX_PARENT_BLOCK} bytes")
    if not stream.eof or stream.unused_data:
        _refuse("TREE_PARENT_BLOCK_MALFORMED", f"{where} is not one complete zlib stream")
    return data


def read_parent(snapshot: bytes, pin: dict[str, Any]) -> dict[str, Any]:
    """The verified witness collections of the embedded parent: the bytes are checked against ``pin`` (byte count and
    SHA-256) before any parse, then deserialized in memory and read with fixed SELECTs only."""
    if type(snapshot) is not bytes:
        _refuse("TREE_PARENT_REFERENCE_MISMATCH", "the parent snapshot is not a BLOB")
    if len(snapshot) != pin["bytes"]:
        _refuse("TREE_PARENT_REFERENCE_MISMATCH", f"the parent snapshot holds {len(snapshot)} bytes, the pin "
                                                  f"{pin['bytes']}")
    if sha256_bytes(snapshot) != pin["sqlite_sha256"]:
        _refuse("TREE_PARENT_REFERENCE_MISMATCH", "the parent snapshot SHA-256 differs from the committed pin")
    conn = sqlite3.connect(":memory:")
    try:
        try:
            conn.deserialize(snapshot)
            conn.execute("PRAGMA query_only = ON")
            master = sorted((str(r[0]), str(r[1]), str(r[2])) for r in conn.execute(
                "SELECT type, name, sql FROM sqlite_master"))
            if master != sorted(PARENT_DDL):
                _refuse("TREE_PARENT_SCHEMA_MISMATCH", "the parent schema differs from the accepted C56 schema")
            meta_rows = [(r[0], r[1]) for r in conn.execute("SELECT key, value FROM meta ORDER BY rowid")]
            rows = [tuple(r) for r in conn.execute(
                "SELECT ord, record_table, segment, records, first_key, last_key, lines_sha256, block FROM blocks "
                "ORDER BY ord")]
        except sqlite3.DatabaseError:
            raise BoostingError("TREE_PARENT_SCHEMA_MISMATCH", "the parent snapshot is not a readable database") \
                from None
    finally:
        conn.close()
    meta = {}
    for key, value in meta_rows:
        if type(key) is not str or type(value) is not str or key in meta:
            _refuse("TREE_PARENT_SCHEMA_MISMATCH", "the parent meta rows are malformed or repeated")
        meta[key] = value
    if tuple(sorted(meta)) != PARENT_META_KEYS:
        _refuse("TREE_PARENT_SCHEMA_MISMATCH", "the parent meta keys differ from the accepted C56 keys")
    if (meta["content_identity"], meta["contract_id"], meta["contract_sha256"], meta["schema_version"]) != \
            (pin["content_identity"], pin["contract_id"], pin["contract_sha256"], pin["schema_version"]):
        _refuse("TREE_PARENT_SCHEMA_MISMATCH", "the parent meta names another identity, contract or schema")
    claimed = loads_untrusted(meta["uncompressed_sha256"], "TREE_PARENT_SCHEMA_MISMATCH", "parent meta digests")
    counts_claim = loads_untrusted(meta["row_counts"], "TREE_PARENT_SCHEMA_MISMATCH", "parent meta row counts")
    if len(rows) != len(PARENT_BLOCK_LAYOUT):
        _refuse("TREE_PARENT_SCHEMA_MISMATCH", f"the parent holds {len(rows)} blocks, not {len(PARENT_BLOCK_LAYOUT)}")
    lines: dict[str, list[str]] = {t: [] for t in PARENT_RECORD_TABLES}
    records: dict[str, list[dict[str, Any]]] = {t: [] for t in PARENT_RECORD_TABLES}
    total = 0
    for index, (row, (table, segment)) in enumerate(zip(rows, PARENT_BLOCK_LAYOUT)):
        ord_, rtable, rsegment, count, first_key, last_key, lines_sha, blob = row
        where = f"parent block {index}"
        if (ord_, rtable, rsegment) != (index, table, segment):
            _refuse("TREE_PARENT_BLOCK_MALFORMED", f"{where} is not ({table}, {segment})")
        data = _bounded_decompress(blob, where)
        total += len(data)
        if sha256_bytes(data) != lines_sha:
            _refuse("TREE_PARENT_BLOCK_MALFORMED", f"{where} lines differ from its digest")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise BoostingError("TREE_PARENT_BLOCK_MALFORMED", f"{where} is not UTF-8") from None
        if text and not text.endswith("\n"):
            _refuse("TREE_PARENT_BLOCK_MALFORMED", f"{where} does not end with a newline")
        block_lines = text[:-1].split("\n") if text else []
        parsed = []
        for line in block_lines:
            record = loads_untrusted(line, "TREE_PARENT_BLOCK_MALFORMED", where)
            if type(record) is not dict or line != canonical_line(record):
                _refuse("TREE_PARENT_BLOCK_MALFORMED", f"{where} holds a non-canonical or non-object line")
            parsed.append(record)
        keys = [_parent_key(table, r) for r in parsed]
        if count != len(parsed) or first_key != (keys[0] if keys else None) or \
                last_key != (keys[-1] if keys else None):
            _refuse("TREE_PARENT_BLOCK_MALFORMED", f"{where} index columns differ from its content")
        if table in PARENT_SEASONAL and any(r.get("season") != int(segment) for r in parsed):
            _refuse("TREE_PARENT_BLOCK_MALFORMED", f"{where} holds a record of another season")
        lines[table] += block_lines
        records[table] += parsed
    if total != pin["total_decompressed_bytes"]:
        _refuse("TREE_PARENT_BLOCK_MALFORMED", f"the parent decompresses to {total} bytes, the pin "
                                               f"{pin['total_decompressed_bytes']}")
    for table in PARENT_RECORD_TABLES:
        if len(records[table]) != pin["record_counts"][table]:
            _refuse("TREE_PARENT_SCHEMA_MISMATCH", f"the parent holds {len(records[table])} {table}")
        if table != "summary":
            if type(claimed) is not dict or claimed.get(f"{table}.jsonl") != lines_sha256(lines[table]):
                _refuse("TREE_PARENT_BLOCK_MALFORMED", f"the parent {table} lines differ from its meta digest")
            if type(counts_claim) is not dict or counts_claim.get(f"{table}.jsonl.gz") != len(records[table]):
                _refuse("TREE_PARENT_SCHEMA_MISMATCH", f"the parent {table} count differs from its meta claim")
    if meta["summary_sha256"] != sha256_bytes(canonical_json_bytes(records["summary"][0])):
        _refuse("TREE_PARENT_BLOCK_MALFORMED", "the parent summary differs from its meta digest")
    return {"meta": meta, "records": records, "lines": lines}


def _check_parent_witnesses(parent: dict[str, Any], pin: dict[str, Any]) -> None:
    """Every parent witness the comparison consumes: model identities, complete per-game collections, the score ->
    estimate and score -> label line bindings and the per-game slice flags."""
    recs, lines = parent["records"], parent["lines"]
    params = {p.get("model_id"): p for p in recs["parameters"]}
    if [p.get("model_id") for p in recs["parameters"]] != list(PARENT_MODELS) or \
            {m: params[m].get("model_sha256") for m in PARENT_MODELS} != pin["model_sha256"]:
        _refuse("TREE_PARENT_REFERENCE_MISMATCH", "the parent parameters are not the five accepted definitions")
    label_sha = {r.get("contest_key"): sha256_bytes(l.encode("utf-8")) for r, l in zip(recs["labels"], lines["labels"])}
    estimate_sha = {(r.get("contest_key"), r.get("model_id"), r.get("orientation")): sha256_bytes(l.encode("utf-8"))
                    for r, l in zip(recs["estimates"], lines["estimates"])}
    if len(label_sha) != len(recs["labels"]) or len(estimate_sha) != len(recs["estimates"]):
        _refuse("TREE_PARENT_REFERENCE_MISMATCH", "the parent repeats a label or estimate key")
    keys = list(label_sha)
    for key in keys:
        for model in PARENT_MODELS:
            for view in VIEWS:
                if (key, model, view) not in estimate_sha:
                    _refuse("TREE_PARENT_REFERENCE_MISMATCH", "the parent estimate collection is incomplete")
    seen = set()
    for score in recs["scores"]:
        key, model = score.get("contest_key"), score.get("model_id")
        if (key, model) in seen or key not in label_sha or model not in PARENT_MODELS:
            _refuse("TREE_PARENT_REFERENCE_MISMATCH", "the parent score collection is not one per game and model")
        seen.add((key, model))
        if score.get("estimate_record_sha256") != estimate_sha[(key, model, "A")] or \
                score.get("label_record_sha256") != label_sha[key] or score.get("orientation") != "A" or \
                score.get("model_sha256") != pin["model_sha256"][model]:
            _refuse("TREE_PARENT_REFERENCE_MISMATCH", "a parent score does not bind its parent estimate and label")
    if len(seen) != len(keys) * len(PARENT_MODELS):
        _refuse("TREE_PARENT_REFERENCE_MISMATCH", "the parent score collection is incomplete")


def _side_value(block: dict[str, Any], name: str) -> Fraction:
    if name == "games":
        return Fraction(block["games"])
    value = block.get(name)
    return Fraction(0) if value is None else frac(value)


def games_from_parent(parent: dict[str, Any]) -> list[dict[str, Any]]:
    """Every accepted parent target as one canonical game (season, contest key order) with its two parent feature
    records and lines, its label and its five parent score records and lines; the feature differences, pair negation,
    participants, partitions and slice flags are re-derived and required to equal the parent's."""
    recs, lines = parent["records"], parent["lines"]
    features = {}
    for record, line in zip(recs["features"], lines["features"]):
        features[(record.get("contest_key"), record.get("view"))] = (record, line)
    scores: dict[str, dict[str, tuple[dict[str, Any], str]]] = {}
    for record, line in zip(recs["scores"], lines["scores"]):
        scores.setdefault(record.get("contest_key"), {})[record.get("model_id")] = (record, line)
    games = []
    for label, label_line in zip(recs["labels"], lines["labels"]):
        key, season = label.get("contest_key"), label.get("season")
        if type(key) is not str or not CONTEST_KEY_RE.match(key) or season not in STUDY_SEASONS:
            _refuse("TREE_FEATURE_MISMATCH", "a parent label carries an invalid contest key or season")
        (a, a_line), (b, b_line) = features.get((key, "A"), (None, None)), features.get((key, "B"), (None, None))
        if a is None or b is None:
            _refuse("TREE_FEATURE_MISMATCH", f"{key}: the parent feature views are incomplete")
        game = _parent_game(label, label_line, a, a_line, b, b_line, scores.get(key, {}))
        games.append(game)
    if len({g["contest_key"] for g in games}) != len(games) or len(features) != 2 * len(games):
        _refuse("TREE_FEATURE_MISMATCH", "the parent features and labels do not pair one game per key")
    games.sort(key=lambda g: (g["season"], g["contest_key"]))
    return games


def _parent_game(label: dict[str, Any], label_line: str, a: dict[str, Any], a_line: str, b: dict[str, Any],
                 b_line: str, scores: dict[str, tuple[dict[str, Any], str]]) -> dict[str, Any]:
    key, season = label["contest_key"], label["season"]
    partition = partition_of(season)
    if label.get("partition") != PARENT_PARTITIONS[partition] or a.get("partition") != PARENT_PARTITIONS[partition] \
            or b.get("partition") != PARENT_PARTITIONS[partition]:
        _refuse("TREE_FEATURE_MISMATCH", f"{key}: the parent partition differs from the frozen season partition")
    if (a.get("team_key"), a.get("opponent_key")) != (label.get("a_key"), label.get("b_key")) or \
            (b.get("team_key"), b.get("opponent_key")) != (label.get("b_key"), label.get("a_key")):
        _refuse("TREE_FEATURE_MISMATCH", f"{key}: the parent views do not orient the label's participants")
    for side in ("a_key", "b_key"):
        if type(label.get(side)) is not str or not TEAM_KEY_RE.match(label[side]):
            _refuse("TREE_FEATURE_MISMATCH", f"{key}: a participant key is not org:<digits>")
    if label["a_key"] == label["b_key"]:
        _refuse("TREE_FEATURE_MISMATCH", f"{key}: both participants are the same organization")
    designs = []
    for view in (a, b):
        diff = view.get("differences") or {}
        if diff.get("columns") != list(DIFFERENCE_COLUMNS) or diff.get("missing_columns") != list(MISSING_COLUMNS):
            _refuse("TREE_FEATURE_MISMATCH", f"{key}: the parent difference columns differ from the contract columns")
        values, missing = diff.get("values"), diff.get("missing_values")
        if type(values) is not list or len(values) != 5 or not all(is_rational(v) for v in values) or \
                type(missing) is not list or len(missing) != 5 or not all(type(m) is int and -1 <= m <= 1
                                                                         for m in missing):
            _refuse("TREE_FEATURE_MISMATCH", f"{key}: the parent difference values are not exact rationals")
        team, opponent = view.get("team") or {}, view.get("opponent") or {}
        for side in (team, opponent):
            if type(side.get("games")) is not int or not 0 <= side["games"] <= 1000:
                _refuse("TREE_FEATURE_MISMATCH", f"{key}: a parent prior game count is out of domain")
        recomputed = [_side_value(team, n) - _side_value(opponent, n) for n in SIDE_FIELDS]
        recomputed_missing = [team["missing"][n] - opponent["missing"][n] for n in SIDE_FIELDS]
        if recomputed != [frac(v) for v in values] or recomputed_missing != missing:
            _refuse("TREE_FEATURE_MISMATCH", f"{key}: the parent differences do not follow their side blocks")
        designs.append([frac(v) for v in values] + [Fraction(m) for m in missing])
    if designs[1] != [-v for v in designs[0]]:
        _refuse("TREE_FEATURE_MISMATCH", f"{key}: the B view is not the exact negation of the A view")
    team_games, opponent_games = a["team"]["games"], a["opponent"]["games"]
    flags = {"texas_am_game": TAMU_KEY in (label["a_key"], label["b_key"]),
             "first_four_team_games": min(team_games, opponent_games) < 4,
             "cold_start": min(team_games, opponent_games) == 0}
    for view in (a, b):
        if (view.get("texas_am_target"), view.get("first_four_team_games"), view.get("cold_start")) != \
                (flags["texas_am_game"], flags["first_four_team_games"], flags["cold_start"]):
            _refuse("TREE_FEATURE_MISMATCH", f"{key}: the parent slice flags differ from their re-derivation")
    state = label.get("label_state")
    for name in ("a_points", "b_points"):
        if type(label.get(name)) is not int or not 0 <= label[name] <= 1000:
            _refuse("TREE_LABEL_MISMATCH", f"{key}: parent {name} is not a game score")
    if state == "DECISIVE":
        if type(label.get("y_a")) is not int or label["y_a"] not in (0, 1) or label.get("unscored_reason") is not None:
            _refuse("TREE_LABEL_MISMATCH", f"{key}: a decisive parent label has no binary outcome")
        if (label["y_a"] == 1) != (label["a_points"] > label["b_points"]) or label["a_points"] == label["b_points"]:
            _refuse("TREE_LABEL_MISMATCH", f"{key}: the parent outcome contradicts its points")
    elif state == "TIE":
        if label.get("y_a") is not None or label["a_points"] != label["b_points"]:
            _refuse("TREE_LABEL_MISMATCH", f"{key}: a tied parent label is not a tie")
    else:
        _refuse("TREE_LABEL_MISMATCH", f"{key}: parent label state {describe(state)} is not DECISIVE or TIE")
    if sorted(scores) != sorted(PARENT_MODELS):
        _refuse("TREE_SCORE_MISMATCH", f"{key}: the parent scores are not the five families")
    for model, (score, _line) in scores.items():
        if (score.get("season"), score.get("a_key"), score.get("b_key"), score.get("label_state"),
                score.get("texas_am_target"), score.get("first_four_team_games"), score.get("cold_start")) != \
                (season, label["a_key"], label["b_key"], state, flags["texas_am_game"],
                 flags["first_four_team_games"], flags["cold_start"]):
            _refuse("TREE_SCORE_MISMATCH", f"{key}/{model}: the parent score differs from its game")
    return {"contest_key": key, "season": season, "contest_date": label.get("contest_date"), "partition": partition,
            "parent_partition": PARENT_PARTITIONS[partition], "a_key": label["a_key"], "b_key": label["b_key"],
            "a_name": a.get("team_name"), "b_name": b.get("team_name"), "a_points": label["a_points"],
            "b_points": label["b_points"], "label_state": state, "y_a": label.get("y_a"),
            "design_a": designs[0], "design_b": designs[1], "x_a": [float(v) for v in designs[0]],
            "x_b": [float(v) for v in designs[1]], "team_games": team_games, "opponent_games": opponent_games,
            **flags, "feature_lines": {"A": a_line, "B": b_line}, "label_line": label_line,
            "parent_scores": {m: scores[m] for m in PARENT_MODELS}}


# --------------------------------------------------------------------------------------------- derivation

def feature_records(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for g in games:
        for view in VIEWS:
            design = g["design_a"] if view == "A" else g["design_b"]
            team, opponent = (g["a_key"], g["b_key"]) if view == "A" else (g["b_key"], g["a_key"])
            names = (g["a_name"], g["b_name"]) if view == "A" else (g["b_name"], g["a_name"])
            counts = (g["team_games"], g["opponent_games"]) if view == "A" else (g["opponent_games"], g["team_games"])
            out.append({"record_type": RECORD_TYPES["features"], "feature_key": f"{g['contest_key']}|{view}",
                        "contest_key": g["contest_key"], "season": g["season"], "contest_date": g["contest_date"],
                        "partition": g["partition"], "parent_partition": g["parent_partition"], "view": view,
                        "team_key": team, "team_name": names[0], "opponent_key": opponent, "opponent_name": names[1],
                        "a_key": g["a_key"], "b_key": g["b_key"], "team_prior_games": counts[0],
                        "opponent_prior_games": counts[1], "texas_am_game": g["texas_am_game"],
                        "first_four_team_games": g["first_four_team_games"], "cold_start": g["cold_start"],
                        "design_rational": [rational(v) for v in design], "design": [float(v) for v in design],
                        "parent_feature_line_sha256": sha256_bytes(g["feature_lines"][view].encode("utf-8")),
                        **RECORD_LABELS})
    return out


def label_records(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for g in games:
        decisive = g["label_state"] == "DECISIVE"
        out.append({"record_type": RECORD_TYPES["labels"], "label_key": g["contest_key"],
                    "contest_key": g["contest_key"], "season": g["season"], "contest_date": g["contest_date"],
                    "partition": g["partition"], "a_key": g["a_key"], "b_key": g["b_key"], "a_points": g["a_points"],
                    "b_points": g["b_points"], "label_state": g["label_state"], "y_a": g["y_a"],
                    "unscored_reason": None if decisive else "LABEL_TIE",
                    "label_use": ("PROBABILITY_TRAINING_AND_SCORING" if g["partition"] == PARTITION_FIT else
                                  "EXPOSED_2023_COMPARISON_SCORING_ONLY") if decisive else
                    "UNSCORED_FOR_PROBABILITY_FAMILIES_RIDGE_MARGIN_ONLY",
                    "parent_label_line_sha256": sha256_bytes(g["label_line"].encode("utf-8")), **RECORD_LABELS})
    return out


def training_rows(games: list[dict[str, Any]]) -> list[tuple[list[float], int, float]]:
    """The frozen training rows: every decisive FIT game, A then B, weight 1/2 (TRAINING_RULE)."""
    rows = []
    for g in games:
        if g["partition"] != PARTITION_FIT or g["label_state"] != "DECISIVE":
            continue
        rows.append((list(g["x_a"]), g["y_a"], 0.5))
        rows.append((list(g["x_b"]), 1 - g["y_a"], 0.5))
    return rows


def training_census(games: list[dict[str, Any]]) -> dict[str, Any]:
    rows = training_rows(games)
    return {"seasons": list(FIT_SEASONS), "games": len(rows) // 2, "oriented_rows": len(rows),
            "positive_rows": sum(1 for _x, y, _w in rows if y == 1), "row_weight": rational(Fraction(1, 2)),
            "excluded_tie_games": sum(1 for g in games if g["partition"] == PARTITION_FIT and
                                      g["label_state"] != "DECISIVE"),
            "comparison_games_excluded": sum(1 for g in games if g["partition"] == PARTITION_COMPARISON),
            "rows_sha256": sha256_bytes(canonical_json_bytes([[x, y] for x, y, _w in rows]))}


def export_sha256(export: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes({"baseline": export["baseline"], "stages": export["stages"]}))


def compile_trees(model_id: str, baseline: Any, stages: Any) -> tuple[float, list[tuple[tuple[Any, ...], ...]],
                                                                       dict[str, int]]:
    """Validate one exported ensemble against TREE_EXPORT and return it compiled for traversal (refused with
    TREE_STRUCTURE_MISMATCH and its reason)."""
    params = TREE_PARAMS[model_id]
    if type(baseline) is not float or not math.isfinite(baseline):
        _refuse("TREE_STRUCTURE_MISMATCH", f"{model_id}: the baseline is not a finite binary64")
    if type(stages) is not list or len(stages) != params["max_iter"]:
        _refuse("TREE_STRUCTURE_MISMATCH", f"{model_id}: the export does not hold exactly {params['max_iter']} stages")
    compiled = []
    nodes_total = leaves_total = deepest = 0
    for s, nodes in enumerate(stages):
        where = f"{model_id} stage {s}"
        if type(nodes) is not list or not 1 <= len(nodes) <= 2 * params["max_leaf_nodes"] - 1:
            _refuse("TREE_STRUCTURE_MISMATCH", f"{where}: not a list of 1..{2 * params['max_leaf_nodes'] - 1} nodes")
        for i, node in enumerate(nodes):
            if type(node) is not dict or set(node) != set(NODE_FIELDS) or \
                    not all(check_type(code, node[name]) for name, code in NODE_FIELDS.items()):
                _refuse("TREE_STRUCTURE_MISMATCH", f"{where} node {i}: not the 13 typed node fields")
        seen = [False] * len(nodes)
        stack = [(0, 0)]
        leaves = 0
        while stack:
            index, depth = stack.pop()
            if seen[index]:
                _refuse("TREE_STRUCTURE_MISMATCH", f"{where}: node {index} is reached twice (a cycle or shared node)")
            seen[index] = True
            node = nodes[index]
            if node["depth"] != depth or node["is_categorical"] or node["bitset_idx"] != 0 or node["count"] < 0 or \
                    not 0 <= node["bin_threshold"] <= params["max_bins"]:
                _refuse("TREE_STRUCTURE_MISMATCH", f"{where} node {index}: depth, categorical or count fields differ")
            if depth > params["max_depth"]:
                _refuse("TREE_STRUCTURE_MISMATCH", f"{where}: a node is deeper than max_depth {params['max_depth']}")
            deepest = max(deepest, depth)
            if node["is_leaf"]:
                if node["left"] != 0 or node["right"] != 0:
                    _refuse("TREE_STRUCTURE_MISMATCH", f"{where} node {index}: a leaf has children")
                leaves += 1
                continue
            left, right = node["left"], node["right"]
            if not 0 <= node["feature_idx"] < len(COLUMNS) or not (1 <= left < len(nodes)) or \
                    not (1 <= right < len(nodes)) or left == right:
                _refuse("TREE_STRUCTURE_MISMATCH", f"{where} node {index}: feature or children out of range")
            stack.append((right, depth + 1))
            stack.append((left, depth + 1))
        if not all(seen):
            _refuse("TREE_STRUCTURE_MISMATCH", f"{where}: a node is not reachable from the root (dangling)")
        if leaves > params["max_leaf_nodes"]:
            _refuse("TREE_STRUCTURE_MISMATCH", f"{where}: more than {params['max_leaf_nodes']} leaves")
        nodes_total += len(nodes)
        leaves_total += leaves
        compiled.append(tuple((n["is_leaf"], n["feature_idx"], n["num_threshold"], n["missing_go_to_left"], n["left"],
                               n["right"], n["value"]) for n in nodes))
    return baseline, compiled, {"node_count": nodes_total, "leaf_count": leaves_total, "max_depth_seen": deepest}


def traverse(baseline: float, compiled: list[tuple[tuple[Any, ...], ...]], x: list[float]) -> tuple[float, float]:
    """The canonical stdlib inference of one design row: (z, q) per INFERENCE_RULE."""
    z = baseline
    for nodes in compiled:
        node = nodes[0]
        while not node[0]:
            v = x[node[1]]
            if v != v:
                node = nodes[node[4]] if node[3] else nodes[node[5]]
            elif v <= node[2]:
                node = nodes[node[4]]
            else:
                node = nodes[node[5]]
        z = z + node[6]
        if not math.isfinite(z):
            _refuse("TREE_ESTIMATE_MISMATCH", "TREE_MARGIN_NONFINITE: a leaf addition left a nonfinite margin")
    if not math.isfinite(z):
        _refuse("TREE_ESTIMATE_MISMATCH", "TREE_MARGIN_NONFINITE: the margin is not finite")
    q = sigmoid(z)
    if not math.isfinite(q) or not 0.0 <= q <= 1.0:
        _refuse("TREE_ESTIMATE_MISMATCH", "the raw probability is not finite in [0, 1]")
    return z, q


def parameter_record(model_id: str, export: dict[str, Any], census: dict[str, Any],
                     agreement: dict[str, Any]) -> dict[str, Any]:
    _baseline, _compiled, counts = compile_trees(model_id, export["baseline"], export["stages"])
    return {"record_type": RECORD_TYPES["parameters"], "parameter_key": model_id, "model_id": model_id,
            "model_sha256": model_sha256(model_id), "definition": copy.deepcopy(MODELS[model_id]), "training": census,
            "baseline": export["baseline"], "stages": export["stages"], "stage_count": len(export["stages"]),
            **counts, "export_sha256": export_sha256(export), "backend_agreement": agreement, **RECORD_LABELS}


def raw_witnesses(games: list[dict[str, Any]], parameters: list[dict[str, Any]]
                  ) -> dict[tuple[str, str], tuple[float, float, float, float]]:
    """(z_A, z_B, q_A, q_B) of every game and tree by the canonical stdlib traversal of the stored exports."""
    out = {}
    for p in parameters:
        baseline, compiled, _counts = compile_trees(p["model_id"], p["baseline"], p["stages"])
        for g in games:
            z_a, q_a = traverse(baseline, compiled, g["x_a"])
            z_b, q_b = traverse(baseline, compiled, g["x_b"])
            out[(g["contest_key"], p["model_id"])] = (z_a, z_b, q_a, q_b)
    return out


def estimate_records(games: list[dict[str, Any]], features: list[dict[str, Any]], parameters: list[dict[str, Any]],
                     witnesses: dict[tuple[str, str], tuple[str, str, str, str]]) -> list[dict[str, Any]]:
    """Both oriented estimates of every game and tree from the stored raw witness texts (repr strings)."""
    feature_sha = {f["feature_key"]: sha256_bytes(canonical_line(f).encode("utf-8")) for f in features}
    parameter_sha = {p["model_id"]: sha256_bytes(canonical_line(p).encode("utf-8")) for p in parameters}
    out = []
    for g in games:
        for view in VIEWS:
            for model_id in TREE_MODELS:
                z_a, z_b, q_a, q_b = witnesses[(g["contest_key"], model_id)]
                served_a, served_b = served_pair(float(q_a), float(q_b))
                mine, other = (served_a, served_b) if view == "A" else (served_b, served_a)
                team, opponent = (g["a_key"], g["b_key"]) if view == "A" else (g["b_key"], g["a_key"])
                names = (g["a_name"], g["b_name"]) if view == "A" else (g["b_name"], g["a_name"])
                out.append({"record_type": RECORD_TYPES["estimates"],
                            "estimate_key": f"{g['contest_key']}|{model_id}|{view}", "contest_key": g["contest_key"],
                            "season": g["season"], "contest_date": g["contest_date"], "partition": g["partition"],
                            "model_id": model_id, "model_sha256": model_sha256(model_id), "orientation": view,
                            "team_key": team, "team_name": names[0], "opponent_key": opponent,
                            "opponent_name": names[1], "a_key": g["a_key"], "b_key": g["b_key"],
                            "sample_state": sample_state(g["season"]), "raw_z_a_repr": z_a, "raw_z_b_repr": z_b,
                            "raw_q_a_repr": q_a, "raw_q_b_repr": q_b, "game_grain_probability_a": served_a,
                            "probability": mine, "opponent_probability": other,
                            "feature_record_sha256": feature_sha[f"{g['contest_key']}|{view}"],
                            "parameter_record_sha256": parameter_sha[model_id], **RECORD_LABELS})
    return out


_PARENT_SCORE_FIELDS = ("probability_a", "probability_a_exact", "brier", "brier_decimal", "log_loss",
                        "log_loss_convention", "margin_a", "margin_label_a", "absolute_error", "absolute_error_decimal",
                        "squared_error", "squared_error_decimal")


def score_records(games: list[dict[str, Any]], labels: list[dict[str, Any]],
                  estimates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Seven per game: the five parent families copied unchanged, then the two trees scored from the served A
    probability (SCORE_RULE)."""
    label_sha = {r["label_key"]: sha256_bytes(canonical_line(r).encode("utf-8")) for r in labels}
    estimate_a = {(e["contest_key"], e["model_id"]): e for e in estimates if e["orientation"] == "A"}
    out = []
    for g in games:
        key = g["contest_key"]
        base = {"record_type": RECORD_TYPES["scores"], "contest_key": key, "season": g["season"],
                "contest_date": g["contest_date"], "partition": g["partition"], "a_key": g["a_key"],
                "b_key": g["b_key"], "a_team_name": g["a_name"], "b_team_name": g["b_name"],
                "label_state": g["label_state"], "y_a": g["y_a"], "texas_am_game": g["texas_am_game"],
                "first_four_team_games": g["first_four_team_games"], "cold_start": g["cold_start"],
                "label_record_sha256": label_sha[key]}
        for model_id in PARENT_MODELS:
            parent, line = g["parent_scores"][model_id]
            record = {**base, "score_key": f"{key}|{model_id}", "model_id": model_id,
                      "model_sha256": parent.get("model_sha256"), "metric_kind": metric_kind(model_id),
                      "score_source": "UNCHANGED_C56_PARENT_GAME_SCORE", "score_state": parent.get("score_state"),
                      "unscored_reason": parent.get("unscored_reason"), "sample_state": parent.get("sample_state"),
                      **{f: parent.get(f) for f in _PARENT_SCORE_FIELDS},
                      "estimate_record_sha256": parent.get("estimate_record_sha256"), "parent_score": parent,
                      "parent_score_line_sha256": sha256_bytes(line.encode("utf-8")), **RECORD_LABELS}
            out.append(record)
        for model_id in TREE_MODELS:
            estimate = estimate_a[(key, model_id)]
            p_text = estimate["game_grain_probability_a"]
            p = dec_fraction(p_text)
            record = {**base, "score_key": f"{key}|{model_id}", "model_id": model_id,
                      "model_sha256": model_sha256(model_id), "metric_kind": "PROBABILITY",
                      "score_source": "NEW_FROZEN_TREE_FIT", "sample_state": sample_state(g["season"]),
                      "probability_a": p_text, "probability_a_exact": rational(p), "log_loss_convention": CLIP_CONVENTION,
                      "margin_a": None, "margin_label_a": None, "absolute_error": None, "absolute_error_decimal": None,
                      "squared_error": None, "squared_error_decimal": None,
                      "estimate_record_sha256": sha256_bytes(canonical_line(estimate).encode("utf-8")),
                      "parent_score": None, "parent_score_line_sha256": None, **RECORD_LABELS}
            if g["label_state"] == "DECISIVE":
                brier = (p - g["y_a"]) ** 2
                record.update(score_state="SCORED", unscored_reason=None, brier=rational(brier),
                              brier_decimal=decimal_text(brier), log_loss=repr(log_loss_value(p, g["y_a"])))
            else:
                record.update(score_state="UNSCORED", unscored_reason="LABEL_TIE", brier=None, brier_decimal=None,
                              log_loss=None)
            out.append(record)
    return out


def _mean(total: Fraction, count: int) -> tuple[dict[str, int] | None, str | None]:
    if not count:
        return None, None
    value = total / count
    return rational(value), decimal_text(value)


def calibration_table(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bins: list[list[tuple[Fraction, int]]] = [[] for _ in range(DECILE_BINS)]
    for s in scored:
        p = frac(s["probability_a_exact"])
        bins[min(int(p * DECILE_BINS), DECILE_BINS - 1)].append((p, s["y_a"]))
    table = []
    for index, members in enumerate(bins):
        p_total = sum((p for p, _y in members), Fraction(0))
        wins = sum(1 for _p, y in members if y == 1)
        mean_p, mean_p_text = _mean(p_total, len(members))
        rate, rate_text = _mean(Fraction(wins), len(members))
        table.append({"a_wins": wins, "bin": index, "count": len(members),
                      "lower": rational(Fraction(index, DECILE_BINS)), "mean_probability_a": mean_p,
                      "mean_probability_a_decimal": mean_p_text, "observed_a_win_rate": rate,
                      "observed_a_win_rate_decimal": rate_text,
                      "upper": rational(Fraction(index + 1, DECILE_BINS)), "upper_closed": index == DECILE_BINS - 1})
    return table


def in_slice(slice_id: str, score: dict[str, Any]) -> bool:
    if slice_id == "NATIONAL":
        return True
    if slice_id == "TEXAS_AM":
        return bool(score["texas_am_game"])
    if slice_id == "FIRST_FOUR_TEAM_GAMES":
        return bool(score["first_four_team_games"])
    return bool(score["cold_start"])


def _summary_row(slice_id: str, scope: str, seasons: tuple[int, ...], model_id: str,
                 mine: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [s for s in mine if s["score_state"] == "SCORED"]
    unscored: dict[str, int] = {}
    for s in mine:
        if s["score_state"] != "SCORED":
            unscored[str(s["unscored_reason"])] = unscored.get(str(s["unscored_reason"]), 0) + 1
    samples: dict[str, int] = {}
    for s in scored:
        samples[s["sample_state"]] = samples.get(s["sample_state"], 0) + 1
    row: dict[str, Any] = {
        "record_type": RECORD_TYPES["summary"], "summary_key": f"{slice_id}|{scope}|{model_id}", "slice": slice_id,
        "scope": scope, "seasons": list(seasons), "model_id": model_id,
        "model_sha256": model_sha256(model_id) if model_id in TREE_MODELS else mine[0]["model_sha256"],
        "metric_kind": metric_kind(model_id),
        "score_source": "NEW_FROZEN_TREE_FIT" if model_id in TREE_MODELS else "UNCHANGED_C56_PARENT_GAME_SCORE",
        "games": len(mine), "scored_games": len(scored), "unscored_games": len(mine) - len(scored),
        "unscored_by_reason": dict(sorted(unscored.items())), "scored_by_sample_state": dict(sorted(samples.items())),
        "game_keys_sha256": keys_sha256(s["contest_key"] for s in scored), "brier_total": None,
        "brier_total_decimal": None, "brier_mean": None, "brier_mean_decimal": None, "log_loss_total": None,
        "log_loss_mean": None, "calibration": None, "mae": None, "mae_decimal": None, "mse": None, "mse_decimal": None,
        "rmse": None, "rmse_decimal": None, "comparisons": None, **RECORD_LABELS}
    if model_id in PROBABILITY_MODELS:
        brier_total = sum((frac(s["brier"]) for s in scored), Fraction(0))
        log_total = math.fsum(float(s["log_loss"]) for s in scored)
        brier_mean, brier_mean_text = _mean(brier_total, len(scored))
        row.update(brier_total=rational(brier_total), brier_total_decimal=decimal_text(brier_total),
                   brier_mean=brier_mean, brier_mean_decimal=brier_mean_text, log_loss_total=repr(log_total),
                   log_loss_mean=repr(log_total / len(scored)) if scored else None,
                   calibration=calibration_table(scored))
    else:
        abs_total = sum((frac(s["absolute_error"]) for s in scored), Fraction(0))
        sq_total = sum((frac(s["squared_error"]) for s in scored), Fraction(0))
        mae, mae_text = _mean(abs_total, len(scored))
        mse, mse_text = _mean(sq_total, len(scored))
        rmse = math.sqrt(float(sq_total / len(scored))) if scored else None
        row.update(mae=mae, mae_decimal=mae_text, mse=mse, mse_decimal=mse_text,
                   rmse=None if rmse is None else repr(rmse), rmse_decimal=None if rmse is None else dec12(rmse))
    return row


def summary_records(scores: list[dict[str, Any]], selected: set[str] | None = None) -> list[dict[str, Any]]:
    """Every nonempty frozen slice x scope x model row over ``scores`` (one per game and model, canonical order),
    restricted to the ``selected`` game keys when given (SUMMARY_RULE)."""
    by_game: dict[str, dict[str, dict[str, Any]]] = {}
    order: list[str] = []
    for s in scores:
        if selected is not None and s["contest_key"] not in selected:
            continue
        if s["contest_key"] not in by_game:
            by_game[s["contest_key"]] = {}
            order.append(s["contest_key"])
        by_game[s["contest_key"]][s["model_id"]] = s
    rows = []
    for slice_id in SLICE_IDS:
        for scope, seasons in SCOPES:
            chosen = [k for k in order if by_game[k][PARENT_NULL]["season"] in seasons and
                      in_slice(slice_id, by_game[k][PARENT_NULL])]
            if not chosen:
                continue
            by_model = {}
            for model_id in MODEL_IDS:
                row = _summary_row(slice_id, scope, seasons, model_id, [by_game[k][model_id] for k in chosen])
                by_model[model_id] = row
            first = by_model[PARENT_NULL]["game_keys_sha256"]
            if any(by_model[m]["game_keys_sha256"] != first for m in PROBABILITY_MODELS):
                _refuse("TREE_SUMMARY_MISMATCH", f"{slice_id}/{scope}: the probability families differ in scored games")
            for model_id in TREE_MODELS:
                tree = by_model[model_id]
                comparisons = []
                for control in PARENT_PROBABILITY_MODELS:
                    other = by_model[control]
                    entry: dict[str, Any] = {"control_model_id": control, "games": tree["scored_games"]}
                    if tree["brier_mean"] is not None and other["brier_mean"] is not None:
                        diff = frac(tree["brier_mean"]) - frac(other["brier_mean"])
                        entry.update(brier_mean_difference=rational(diff),
                                     brier_mean_difference_decimal=decimal_text(diff),
                                     log_loss_mean_difference=repr(float(tree["log_loss_mean"]) -
                                                                   float(other["log_loss_mean"])),
                                     reading="descriptive retrospective difference (tree minus control) on identical "
                                             "game keys; negative favours the tree, positive the control; no "
                                             "significance, skill, calibration or champion claim; adverse results "
                                             "retained")
                    else:
                        entry.update(brier_mean_difference=None, brier_mean_difference_decimal=None,
                                     log_loss_mean_difference=None, reading="no scored game in this scope")
                    comparisons.append(entry)
                tree["comparisons"] = comparisons
            rows += [by_model[m] for m in MODEL_IDS]
    return rows


_PARENT_SCOPE = {"POOLED": ("POOLED", "2016-2023"), PARTITION_FIT: ("PARTITION", PARENT_PARTITIONS[PARTITION_FIT]),
                 PARTITION_COMPARISON: ("PARTITION", PARENT_PARTITIONS[PARTITION_COMPARISON]),
                 **{f"SEASON_{s}": ("SEASON", str(s)) for s in STUDY_SEASONS}}
_PARENT_SUMMARY_FIELDS = ("scored_games", "brier_total", "brier_total_decimal", "brier_mean", "brier_mean_decimal",
                          "log_loss_total", "log_loss_mean", "calibration", "mae", "mae_decimal", "mse", "mse_decimal",
                          "rmse", "rmse_decimal")


def parent_summary_witness(rows: list[dict[str, Any]], parent_summary: dict[str, Any]) -> None:
    """The parent-family rows of the canonical summary equal the parent's own summary rows (SUMMARY_RULE
    parent_witness): an independent check of the copied scores, the slices and the scope mapping."""
    parent_rows = parent_summary.get("rows") if type(parent_summary) is dict else None
    if type(parent_rows) is not list:
        _refuse("TREE_PARENT_REFERENCE_MISMATCH", "the parent summary has no rows")
    index = {}
    for r in parent_rows:
        if type(r) is dict:
            index[(r.get("slice"), r.get("scope_kind"), r.get("scope_id"), r.get("model_id"))] = r
    for row in rows:
        if row["model_id"] not in PARENT_MODELS:
            continue
        kind, scope_id = _PARENT_SCOPE[row["scope"]]
        parent = index.get((row["slice"], kind, scope_id, row["model_id"]))
        if parent is None or any(canonical_json_bytes(parent.get(f)) != canonical_json_bytes(row[f])
                                 for f in _PARENT_SUMMARY_FIELDS if f in parent or row[f] is not None):
            _refuse("TREE_SUMMARY_MISMATCH", f"{row['summary_key']}: the parent-family row differs from the parent's "
                                             "own summary row")


def derive(games: list[dict[str, Any]], parameters: list[dict[str, Any]],
           witnesses: dict[tuple[str, str], tuple[str, str, str, str]]) -> dict[str, Any]:
    """Every record from the verified parent games, the two parameter records and the stored raw witness texts."""
    features = feature_records(games)
    labels = label_records(games)
    estimates = estimate_records(games, features, parameters, witnesses)
    scores = score_records(games, labels, estimates)
    summary = summary_records(scores)
    return {"features": features, "labels": labels, "parameters": parameters, "estimates": estimates,
            "scores": scores, "summary": summary}


def witness_texts(raw: dict[tuple[str, str], tuple[float, float, float, float]]
                  ) -> dict[tuple[str, str], tuple[str, str, str, str]]:
    return {key: tuple(repr(v) for v in values) for key, values in raw.items()}


# --------------------------------------------------------------------------------------------- expected collections

def record_key(table: str, record: dict[str, Any]) -> str:
    value = record.get(KEY_FIELDS[table])
    return value if type(value) is str else "<invalid key>"


def expected_keys(games: list[dict[str, Any]]) -> dict[str, list[str]]:
    """The complete key inventory of every table, from the verified parent games only (never from delivered rows)."""
    keys: dict[str, list[str]] = {"features": [], "labels": [], "parameters": list(TREE_MODELS), "estimates": [],
                                  "scores": [], "summary": []}
    for g in games:
        k = g["contest_key"]
        keys["features"] += [f"{k}|A", f"{k}|B"]
        keys["labels"].append(k)
        keys["estimates"] += [f"{k}|{m}|{v}" for v in VIEWS for m in TREE_MODELS]
        keys["scores"] += [f"{k}|{m}" for m in MODEL_IDS]
    for slice_id in SLICE_IDS:
        for scope, seasons in SCOPES:
            if any(g["season"] in seasons and in_slice(slice_id, g) for g in games):
                keys["summary"] += [f"{slice_id}|{scope}|{m}" for m in MODEL_IDS]
    return keys


def expected_inventory(games: list[dict[str, Any]]) -> dict[str, Any]:
    keys = expected_keys(games)
    by_season: dict[str, int] = {}
    for g in games:
        by_season[str(g["season"])] = by_season.get(str(g["season"]), 0) + 1
    return {"counts": {t: len(v) for t, v in keys.items()}, "keys_sha256": {t: keys_sha256(v) for t, v in keys.items()},
            "games": len(games), "games_by_season": dict(sorted(by_season.items())),
            "fit_games": sum(1 for g in games if g["partition"] == PARTITION_FIT),
            "comparison_games": sum(1 for g in games if g["partition"] == PARTITION_COMPARISON),
            "label_states": {s: sum(1 for g in games if g["label_state"] == s) for s in ("DECISIVE", "TIE")},
            "y_a_counts": {"1": sum(1 for g in games if g["y_a"] == 1), "0": sum(1 for g in games if g["y_a"] == 0)},
            "slice_games": {s: sum(1 for g in games if in_slice(s, g)) for s in SLICE_IDS}}


# --------------------------------------------------------------------------------------------- database layout

def record_lines(derived: dict[str, Any]) -> dict[str, list[str]]:
    return {table: [canonical_line(r) for r in derived[table]] for table in RECORD_TABLES}


def block_lines(derived: dict[str, Any], lines: dict[str, list[str]] | None = None
                ) -> list[tuple[str, str, list[dict[str, Any]], list[str]]]:
    lines = lines or record_lines(derived)
    out = []
    for table, segment in BLOCK_LAYOUT:
        if segment == "GLOBAL":
            chosen = list(zip(derived[table], lines[table]))
        else:
            chosen = [(r, line) for r, line in zip(derived[table], lines[table]) if str(r["season"]) == segment]
        out.append((table, segment, [r for r, _l in chosen], [line for _r, line in chosen]))
    return out


def game_chunk(derived: dict[str, Any], keys: Iterable[str], lines: dict[str, list[str]] | None = None) -> bytes:
    """The checkpoint unit: every seasonal record line of the given games, table by table (deterministic)."""
    wanted = set(keys)
    lines = lines or record_lines(derived)
    out = []
    for table in SEASONAL_TABLES:
        out += [f"{table}\t{r['season']}\t{line}" for r, line in zip(derived[table], lines[table])
                if r["contest_key"] in wanted]
    return ("\n".join(out) + "\n").encode("utf-8")


def row_counts(derived: dict[str, Any]) -> dict[str, int]:
    return {table: len(derived[table]) for table in RECORD_TABLES}


def parent_binding(anchors: dict[str, Any]) -> dict[str, Any]:
    pin = anchors["parent"]
    return {"population": PARENT_POPULATION, "database_identity": pin["database_identity"],
            "content_identity": pin["content_identity"], "sqlite_sha256": pin["sqlite_sha256"], "bytes": pin["bytes"],
            "contract_id": pin["contract_id"], "contract_sha256": pin["contract_sha256"],
            "record_counts": pin["record_counts"], "blocks": len(PARENT_BLOCK_LAYOUT),
            "total_decompressed_bytes": pin["total_decompressed_bytes"]}


def content_document(anchors: dict[str, Any], derived: dict[str, Any],
                     lines: dict[str, list[str]] | None = None) -> dict[str, Any]:
    lines = lines or record_lines(derived)
    return {"schema": CONTENT_SCHEMA, "stage": CONTENT_STAGE, "population": POPULATION,
            "contract_id": anchors["contract_id"], "contract_sha256": anchors["contract_sha256"],
            "rules_sha256": rules_sha256(), "parent": parent_binding(anchors),
            "lines_sha256": {t: lines_sha256(lines[t]) for t in RECORD_TABLES}, "row_counts": row_counts(derived)}


def database_document(contract_sha256: str, content_identity: str, database_sha256: str,
                      table_counts: dict[str, int]) -> dict[str, Any]:
    return {"schema": DATABASE_SCHEMA, "stage": DATABASE_STAGE, "population": POPULATION,
            "contract_sha256": contract_sha256, "content_identity": content_identity, "db_schema_version": DB_SCHEMA,
            "outputs": {DB_FILE: database_sha256}, "table_counts": dict(table_counts)}


def meta_values(anchors: dict[str, Any], content_identity: str, derived: dict[str, Any],
                lines: dict[str, list[str]] | None = None) -> dict[str, str]:
    lines = lines or record_lines(derived)
    return {"schema_version": DB_SCHEMA, "contract_id": anchors["contract_id"],
            "contract_sha256": anchors["contract_sha256"], "rules_sha256": rules_sha256(),
            "content_identity": content_identity, "labels": canonical_line(LABELS),
            "parent": canonical_line(parent_binding(anchors)), "row_counts": canonical_line(row_counts(derived)),
            "lines_sha256": canonical_line({t: lines_sha256(lines[t]) for t in RECORD_TABLES})}


def block_rows(derived: dict[str, Any], built: dict[tuple[str, str], list[str]] | None = None) -> list[tuple[Any, ...]]:
    rows = []
    blocks = {(t, s): (records, lines) for t, s, records, lines in block_lines(derived)}
    for ord_, (table, segment) in enumerate(BLOCK_LAYOUT):
        records, lines = blocks[(table, segment)]
        if built is not None:
            lines = built[(table, segment)]
        data = "".join(line + "\n" for line in lines).encode("utf-8")
        rows.append((ord_, table, segment, len(lines), record_key(table, records[0]) if records else None,
                     record_key(table, records[-1]) if records else None, sha256_bytes(data), zlib.compress(data, 9)))
    return rows


def build_database(path: Path, derived: dict[str, Any], meta: dict[str, str], snapshot: bytes,
                   built: dict[tuple[str, str], list[str]] | None = None) -> dict[str, int]:
    """A fresh deterministic SQLite file: page size 4096, no journal, rows inserted in layout order, no deletes, the
    parent snapshot as one BLOB."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA journal_mode = OFF")
        for _kind, _name, ddl in DDL:
            conn.execute(ddl)
        conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", sorted(meta.items()))
        conn.executemany("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", block_rows(derived, built))
        conn.execute("INSERT INTO parent_reference VALUES (1, ?, ?, ?)",
                     (len(snapshot), sha256_bytes(snapshot), sqlite3.Binary(snapshot)))
        conn.commit()
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
    finally:
        conn.close()
    return counts


# --------------------------------------------------------------------------------------------- locations

MANIFEST_MEMBERS = ("content_document", "content_identity", "identity", "identity_document", "provenance")
_VERBATIM_ROOT = re.compile(r"\\\\\?\\[A-Za-z]:\\")
_DRIVE_ROOT = re.compile(r"[A-Za-z]:\\")
_FIND_PATTERN_CHARACTERS = frozenset('*?<>"')


def io_path(path: Path) -> Path:
    """A path every file API can open: the extended form beyond the classic Windows limit (never re-normalized)."""
    text = os.fspath(path)
    if os.name == "nt" and not text.startswith("\\\\?\\") and len(os.path.abspath(text)) >= 250:
        return Path("\\\\?\\" + os.path.abspath(text))
    return Path(text)


def manifest_path_for(database: Path) -> Path:
    """``<data>/canonical/<population>/sha256/<id>/<db>`` -> ``<data>/manifests/<population>/sha256/<id>/
    run_manifest.json``."""
    db = Path(database)
    population_root = db.parent.parent.parent
    return population_root.parent.parent / "manifests" / population_root.name / "sha256" / db.parent.name / \
        "run_manifest.json"


def _directory_entry_names(query: str) -> tuple[str, str] | None:
    """The long and 8.3 names of the one directory entry Windows resolves the last component of ``query`` to
    (FindFirstFileW: the entry's own name in its parent directory, never the target of a junction or link)."""
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
    """The native spelling of an existing local Windows file (the accepted C61/C63 rule): each component after the
    drive becomes the name of the directory entry Windows resolves it to (8.3 and case-equivalent spellings become the
    entry's own long name; a junction or link keeps its own entry name); POSIX spellings are never rewritten."""
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


def _literal(value: Any, prefix: str) -> str:
    """The BAT-717 literal local path of a supplied database or manifest location, refused by the stage's own code."""
    if not isinstance(value, (str, os.PathLike)):
        _refuse(f"TREE_{prefix}_LOCATION_UNSUPPORTED", f"the {prefix.lower()} location is a {describe(value)}, not a "
                                                       "path")
    try:
        return readonly_sqlite.literal_path(value)
    except readonly_sqlite.DatabaseLocationError as exc:
        suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
        raise BoostingError(f"TREE_{prefix}_LOCATION_{suffix}", f"the {prefix.lower()} location is not a literal "
                                                                 "local file spelling") from None
    except (TypeError, ValueError):
        raise BoostingError(f"TREE_{prefix}_LOCATION_UNSUPPORTED", f"the {prefix.lower()} location is not a "
                                                                   "filesystem path") from None


# --------------------------------------------------------------------------------------------- selection

def _raw_control(text: str) -> bool:
    """A raw Unicode Cc control (C0, DEL or C1) or a lone surrogate anywhere in the raw supplied text."""
    return any(ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F or 0xD800 <= ord(c) <= 0xDFFF for c in text)


def _clean(value: Any) -> str | None:
    """The U+0020-trimmed text of a supplied string selector, or None when it is not a string or holds a raw control
    or lone surrogate (checked before trimming)."""
    if type(value) is not str or _raw_control(value):
        return None
    return value.strip(" ")


def _season(value: Any) -> int:
    if type(value) is int:
        if 1000 <= value <= 9999:
            return value
        _refuse("SEASON_INVALID", f"season must be 1000..9999, got {describe(value)}")
    text = _clean(value)
    if text is None or not SEASON_RE.match(text):
        _refuse("SEASON_INVALID", f"season must be four ASCII digits or an int 1000..9999, got a "
                                  f"<{type(value).__name__}>")
    return int(text)


def _team(value: Any) -> str:
    text = _clean(value)
    if text is None or not text or len(text) > TEAM_TEXT_LIMIT:
        _refuse("TEAM_INVALID", f"team must be org:<digits>, digits or a team name, got a <{type(value).__name__}>")
    if text.lower().startswith("org:"):
        if not TEAM_KEY_RE.match(text):
            _refuse("TEAM_INVALID", "a team key must be org:<1-12 ASCII digits>")
        return text
    if TEAM_DIGITS_RE.match(text):
        return f"org:{text}"
    return text


def _contest(value: Any) -> str:
    text = _clean(value)
    if text is None or not CONTEST_KEY_RE.match(text):
        _refuse("CONTEST_INVALID", "contest must be ncaa:<1-12 ASCII digits>")
    return text


def _model(value: Any) -> str:
    if type(value) is not str:
        _refuse("MODEL_INVALID", f"model must be a string, got a <{type(value).__name__}>")
    text = _clean(value)
    if text is None or not MODEL_RE.match(text):
        _refuse("MODEL_INVALID", "model must match [A-Z][A-Z0-9_]{0,99}")
    return text


def _partition(value: Any) -> str:
    if type(value) is not str or value not in PARTITION_IDS:
        _refuse("PARTITION_INVALID", f"partition must be one of {list(PARTITION_IDS)}")
    return value


def _slice(value: Any) -> str:
    if type(value) is not str or value not in SLICE_IDS:
        _refuse("SLICE_INVALID", f"slice must be one of {list(SLICE_IDS)}")
    return value


def validate_selection(grain: Any, *, season: Any = None, team: Any = None, contest: Any = None, model: Any = None,
                       partition: Any = None, slice_id: Any = None) -> dict[str, Any]:
    """Validate a selection before any file is read, in the frozen precedence: grain, season, team, contest, model,
    partition, slice, then applicability. None means not supplied; an explicit empty value is refused by its rule."""
    if type(grain) is not str or grain not in GRAINS:
        _refuse("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}")
    supplied = {"season": season, "team": team, "contest": contest, "model": model, "partition": partition,
                "slice": slice_id}
    out: dict[str, Any] = {}
    validators = {"season": _season, "team": _team, "contest": _contest, "model": _model, "partition": _partition,
                  "slice": _slice}
    for name in SELECTOR_NAMES:
        if supplied[name] is not None:
            out[name] = validators[name](supplied[name])
    for name in SELECTOR_NAMES:
        if name in out and name not in APPLICABILITY[grain]:
            _refuse("FILTER_NOT_APPLICABLE", f"--{name} does not apply to the {grain} grain")
    return out


def _page(value: Any, code: str, negative: str, what: str) -> int:
    if type(value) is int:
        if not -PAGE_BOUND < value < PAGE_BOUND:
            _refuse(code, f"{what} must have an absolute value below 10**12")
        number = value
    else:
        text = _clean(value)
        if text is None or not PAGE_RE.match(text):
            _refuse(code, f"{what} must be an integer of at most 12 ASCII digits, got a <{type(value).__name__}>")
        number = int(text)
    if number < 0:
        _refuse(negative, f"{what} must be zero or positive")
    return number


def validate_paging(limit: Any = None, offset: Any = None, all_rows: bool = False) -> tuple[int | None, int]:
    """Exact bounded paging: --all with any explicit limit or offset (zero included) is PAGING_CONFLICT; then the limit
    and the offset by type and bound, then sign. None means not supplied (defaults 50 and 0)."""
    if all_rows is not False and all_rows is not True:
        _refuse("ARGUMENT_INVALID", "all_rows must be a boolean")
    if all_rows and (limit is not None or offset is not None):
        _refuse("PAGING_CONFLICT", "--all returns every row and cannot be combined with an explicit --limit or --offset")
    lim = DEFAULT_LIMIT if limit is None else _page(limit, "LIMIT_INVALID", "NEGATIVE_LIMIT", "limit")
    off = 0 if offset is None else _page(offset, "OFFSET_INVALID", "NEGATIVE_OFFSET", "offset")
    return (None if all_rows else lim), off


def validate_identity(expect_identity: Any) -> str | None:
    if expect_identity is None:
        return None
    if type(expect_identity) is not str or _raw_control(expect_identity) or not IDENTITY_RE.match(expect_identity):
        _refuse("STALE_TREE_IDENTITY", "--expect-identity must be a lowercase SHA-256 identity")
    return expect_identity


# --------------------------------------------------------------------------------------------- the reader

class BoostingComparison:
    """A verified, read-only handle on one content-addressed shallow-tree comparison release.

    Construction refuses (BoostingError with a stable code) unless the release location, run manifest, database bytes,
    schema, meta claims, the embedded parent (type, bytes and SHA-256 before any parse, then its schema, blocks and six
    witness collections), every record's exact members and JSON types, the complete expected collection of every
    table, the features and labels re-derived from the parent, both tree structures, a fresh traversal of every view,
    every served pair, score and summary, the content document, the contract-defined database identity document and the
    pinned profile verify. Each refusal is checked in a fixed order so that every forgery is refused for its own
    cause."""

    def __init__(self, database: Any, *, manifest: Any = None, expect_identity: Any = None,
                 anchors: dict[str, Any] | None = None) -> None:
        self.anchors = anchors if anchors is not None else {**ANCHORS, "profile": BOOSTING_PROFILE}
        self.expect_identity = validate_identity(expect_identity)
        self.binding = self._verify_location_and_manifest(database, manifest)
        try:
            conn = readonly_sqlite.connect_readonly(io_path(Path(self.binding["location"])), immutable=False)
        except readonly_sqlite.DatabaseLocationError:
            raise BoostingError("TREE_DATABASE_LOCATION_NOT_LITERAL", "the release could not be opened as its literal "
                                                                      "file") from None
        except sqlite3.Error:
            raise BoostingError("TREE_META_MALFORMED", "the release is not a readable database") from None
        try:
            conn.execute("PRAGMA query_only = ON")
            self._verify_database(conn)
        except sqlite3.DatabaseError:
            raise BoostingError("TREE_META_MALFORMED", "the release database is malformed") from None
        finally:
            conn.close()

    # ---- outer identity
    def _verify_location_and_manifest(self, database: Any, manifest: Any) -> dict[str, Any]:
        literal = _literal(database, "DATABASE")
        manifest_literal = None if manifest is None else _literal(manifest, "MANIFEST")
        if not io_path(Path(literal)).is_file():
            _refuse("TREE_DATABASE_MISSING", "no shallow-tree comparison database file at the given location")
        absolute = Path(native_location(literal)) if os.name == "nt" else Path(literal)
        if absolute.name != DB_FILE or absolute.parent.parent.name != "sha256" or \
                absolute.parent.parent.parent.name != POPULATION:
            _refuse("TREE_LOCATION_INVALID", f"the release must sit at <root>/{POPULATION}/sha256/<id>/{DB_FILE}")
        identity = absolute.parent.name
        if not IDENTITY_RE.match(identity):
            _refuse("TREE_LOCATION_INVALID", "the release directory name is not a SHA-256 identity")
        manifest_path = manifest_path_for(absolute) if manifest_literal is None else Path(manifest_literal)
        if not io_path(manifest_path).is_file():
            _refuse("TREE_MANIFEST_MISSING", "no run manifest at the release's manifest location")
        try:
            raw = io_path(manifest_path).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            raise BoostingError("TREE_MANIFEST_MALFORMED", "the run manifest is not UTF-8 text") from None
        doc = loads_untrusted(raw, "TREE_MANIFEST_MALFORMED", "run manifest")
        if type(doc) is not dict or sorted(doc) != sorted(MANIFEST_MEMBERS):
            _refuse("TREE_MANIFEST_MALFORMED", f"the run manifest members are not {list(MANIFEST_MEMBERS)}")
        untrusted_canonical(doc, "TREE_MANIFEST_MALFORMED", "run manifest")
        identity_document = doc["identity_document"]
        if type(identity_document) is not dict:
            _refuse("TREE_MANIFEST_MALFORMED", "the identity document is not an object")
        computed = sha256_bytes(canonical_json_bytes(identity_document))
        if computed != identity or doc["identity"] != identity:
            _refuse("TREE_MANIFEST_MALFORMED", "IDENTITY_MISMATCH: the manifest identity document does not hash to the "
                                               "release directory identity")
        if (identity_document.get("stage"), identity_document.get("schema"), identity_document.get("db_schema_version"),
                identity_document.get("population")) != (DATABASE_STAGE, DATABASE_SCHEMA, DB_SCHEMA, POPULATION):
            _refuse("TREE_MANIFEST_MALFORMED", "SCHEMA_UNSUPPORTED: not a shallow-tree comparison database manifest")
        outputs = identity_document.get("outputs")
        actual_sha = sha256_file(io_path(absolute))
        if type(outputs) is not dict or outputs.get(DB_FILE) != actual_sha:
            _refuse("TREE_MANIFEST_MALFORMED", "DATABASE_TAMPERED: the release bytes differ from the manifest hash")
        return {"identity": identity, "sha256": actual_sha, "location": str(absolute), "manifest": str(manifest_path),
                "identity_document": identity_document, "content_document": doc["content_document"],
                "content_identity_claim": doc["content_identity"], "provenance": doc["provenance"]}

    # ---- schema, parent, records, rules and identities
    def _verify_database(self, conn: sqlite3.Connection) -> None:
        a = self.anchors
        master = sorted((str(r[0]), str(r[1]), str(r[2])) for r in conn.execute(
            "SELECT type, name, sql FROM sqlite_master"))
        if master != sorted(DDL):
            _refuse("TREE_META_MALFORMED", "the release schema differs from the contract")
        parent_rows = [tuple(r) for r in conn.execute(
            "SELECT singleton, byte_count, sha256, typeof(snapshot), length(snapshot) FROM parent_reference")]
        pin = a["parent"]
        if len(parent_rows) != 1 or parent_rows[0][0] != 1 or parent_rows[0][3] != "blob" or \
                parent_rows[0][1] != pin["bytes"] or parent_rows[0][4] != pin["bytes"] or \
                parent_rows[0][2] != pin["sqlite_sha256"]:
            _refuse("TREE_PARENT_REFERENCE_MISMATCH", "the parent reference row is not the pinned byte-exact BLOB")
        snapshot = conn.execute("SELECT snapshot FROM parent_reference WHERE singleton = 1").fetchone()[0]
        parent = read_parent(snapshot, pin)
        _check_parent_witnesses(parent, pin)
        meta_rows = [(r[0], r[1]) for r in conn.execute("SELECT key, value FROM meta ORDER BY rowid")]
        meta: dict[str, str] = {}
        for key, value in meta_rows:
            if type(key) is not str or type(value) is not str or key in meta:
                _refuse("TREE_META_MALFORMED", "the meta rows are malformed or repeated")
            meta[key] = value
        if tuple(sorted(meta)) != tuple(sorted(META_KEYS)):
            _refuse("TREE_META_MALFORMED", "the meta keys differ from the contract")
        if meta["schema_version"] != DB_SCHEMA or meta["contract_id"] != a["contract_id"] or \
                meta["contract_sha256"] != a["contract_sha256"] or meta["rules_sha256"] != rules_sha256():
            _refuse("TREE_META_MALFORMED", "the release meta names another schema, contract or rule set")
        labels = loads_untrusted(meta["labels"], "TREE_META_MALFORMED", "meta labels")
        if labels != LABELS or meta["labels"] != canonical_line(LABELS):
            _refuse("TREE_META_MALFORMED", "the release declares labels other than the contract's (PIT/skill claims "
                                           "included)")
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        present = self._read_blocks(conn)
        games = games_from_parent(parent)
        expected = expected_keys(games)
        records = {t: [r for _l, r in present[t]] for t in RECORD_TABLES}
        stored_lines = {t: [line for line, _r in present[t]] for t in RECORD_TABLES}
        self._verify_collections(records, expected)
        self._verify_record_labels(records)
        derived = self._verify_semantics(games, records, parent)
        document = content_document(a, derived, stored_lines)
        content_identity = sha256_bytes(canonical_json_bytes(document))
        if untrusted_canonical(self.binding["content_document"], "TREE_MANIFEST_MALFORMED", "content document") != \
                canonical_json_bytes(document) or self.binding["content_identity_claim"] != content_identity or \
                self.binding["identity_document"].get("content_identity") != content_identity:
            _refuse("TREE_MANIFEST_MALFORMED", "CONTENT_IDENTITY_MISMATCH: the manifest content document or identity "
                                               "differs from the rebuilt content")
        expected_meta = meta_values(a, content_identity, derived, stored_lines)
        if meta != expected_meta:
            _refuse("TREE_META_MALFORMED", "meta differs on " + str(sorted(
                k for k in set(meta) | set(expected_meta) if meta.get(k) != expected_meta.get(k))))
        expected_document = database_document(a["contract_sha256"], content_identity, self.binding["sha256"], counts)
        if untrusted_canonical(self.binding["identity_document"], "TREE_MANIFEST_MALFORMED", "identity document") != \
                canonical_json_bytes(expected_document):
            _refuse("TREE_MANIFEST_MALFORMED", "IDENTITY_DOCUMENT_MISMATCH: the identity document is not the "
                                               "contract-defined database document")
        database_identity = sha256_bytes(canonical_json_bytes(expected_document))
        if database_identity != self.binding["identity"]:
            _refuse("TREE_MANIFEST_MALFORMED", "IDENTITY_DOCUMENT_MISMATCH: the location names another identity")
        profile = a.get("profile")
        if self.expect_identity is not None and self.expect_identity != database_identity:
            _refuse("STALE_TREE_IDENTITY", "the release is not the expected identity")
        if self.expect_identity is None and profile is not None and \
                (profile.get("database_identity"), profile.get("content_identity"), profile.get("database_sha256")) \
                != (database_identity, content_identity, self.binding["sha256"]):
            _refuse("STALE_TREE_IDENTITY", "the release is not the committed canonical profile")
        self.database_identity = database_identity
        self.content_identity = content_identity
        self.games = games
        self.records = derived
        self.meta = meta
        self.names = self._name_index(derived["features"])

    def _read_blocks(self, conn: sqlite3.Connection) -> dict[str, list[tuple[str, dict[str, Any]]]]:
        rows = [tuple(r) for r in conn.execute(
            "SELECT ord, record_table, segment, records, first_key, last_key, lines_sha256, block FROM blocks "
            "ORDER BY ord")]
        if len(rows) != len(BLOCK_LAYOUT):
            _refuse("TREE_RECORD_MALFORMED", f"the release holds {len(rows)} blocks, not {len(BLOCK_LAYOUT)}")
        present: dict[str, list[tuple[str, dict[str, Any]]]] = {t: [] for t in RECORD_TABLES}
        for index, (row, (table, segment)) in enumerate(zip(rows, BLOCK_LAYOUT)):
            ord_, rtable, rsegment, count, first_key, last_key, lines_sha, blob = row
            where = f"block {index} ({table} {segment})"
            if (ord_, rtable, rsegment) != (index, table, segment):
                _refuse("TREE_RECORD_MALFORMED", f"block {index} does not follow the contract layout")
            if type(blob) is not bytes:
                _refuse("TREE_RECORD_MALFORMED", f"{where} is not a BLOB")
            try:
                data = zlib.decompress(blob)
                text = data.decode("utf-8")
            except (zlib.error, UnicodeDecodeError):
                raise BoostingError("TREE_RECORD_MALFORMED", f"{where} does not decompress to UTF-8") from None
            if text and not text.endswith("\n"):
                _refuse("TREE_RECORD_MALFORMED", f"{where} does not end with a newline")
            lines = text[:-1].split("\n") if text else []
            parsed = []
            for line in lines:
                record = loads_untrusted(line, "TREE_RECORD_MALFORMED", where)
                if type(record) is not dict:
                    _refuse("TREE_RECORD_MALFORMED", f"{where} holds a non-object line")
                parsed.append((line, record))
            keys = [record_key(table, r) for _l, r in parsed]
            if sha256_bytes(data) != lines_sha or count != len(parsed) or \
                    first_key != (keys[0] if keys else None) or last_key != (keys[-1] if keys else None):
                _refuse("TREE_RECORD_MALFORMED", f"{where} index columns differ from its content")
            types = FIELD_TYPES[table]
            for line, record in parsed:
                at = f"{table} record {describe(record.get(KEY_FIELDS[table]))}"
                if set(record) != set(types):
                    _refuse("TREE_RECORD_MALFORMED", f"{at}: members differ from the contract schema")
                for field, code in types.items():
                    if not check_type(code, record[field]):
                        _refuse("TREE_RECORD_MALFORMED", f"{at}: {field} is not the contract type {code}")
                if line != untrusted_canonical(record, "TREE_RECORD_MALFORMED", at).decode("utf-8"):
                    _refuse("TREE_RECORD_MALFORMED", f"{at} is not its canonical JSON line")
                if table in SEASONAL_TABLES and str(record["season"]) != segment:
                    _refuse("TREE_RECORD_MALFORMED", f"{where} holds a record of another season")
            present[table] += parsed
        return present

    @staticmethod
    def _verify_collections(records: dict[str, list[dict[str, Any]]], expected: dict[str, list[str]]) -> None:
        for table in RECORD_TABLES:
            keys = [record_key(table, r) for r in records[table]]
            if len(keys) != len(set(keys)):
                _refuse("TREE_COLLECTION_MISMATCH", f"{table} repeats a record key")
            listed = expected[table]
            if set(keys) != set(listed):
                _refuse("TREE_COLLECTION_MISMATCH", f"{table} holds {len(set(listed) - set(keys))} missing and "
                                                    f"{len(set(keys) - set(listed))} extra keys")
            if keys != listed:
                _refuse("TREE_COLLECTION_MISMATCH", f"{table} is not in the contract order")

    @staticmethod
    def _verify_record_labels(records: dict[str, list[dict[str, Any]]]) -> None:
        for table in RECORD_TABLES:
            for record in records[table]:
                if record["record_type"] != RECORD_TYPES[table] or \
                        any(record[k] != LABELS[k] for k in RECORD_LABEL_KEYS):
                    _refuse("TREE_RECORD_MALFORMED", f"{table} record {describe(record[KEY_FIELDS[table]])}: record "
                                                     "type or label claim (PIT/skill) differs from the contract")

    def _verify_semantics(self, games: list[dict[str, Any]], records: dict[str, list[dict[str, Any]]],
                          parent: dict[str, Any]) -> dict[str, Any]:
        """Features and labels re-derived from the parent; parameters and tree structures; a fresh traversal of every
        view against the stored witnesses; every estimate, score and summary re-derived from stored canonical values
        (floating log-loss values numerically within 1e-12, every other field exactly)."""
        for table, code, rebuilt in (("features", "TREE_FEATURE_MISMATCH", feature_records(games)),
                                     ("labels", "TREE_LABEL_MISMATCH", label_records(games))):
            for stored, want in zip(records[table], rebuilt):
                if canonical_json_bytes(stored) != canonical_json_bytes(want):
                    differing = sorted(k for k in want if canonical_json_bytes(stored.get(k)) !=
                                       canonical_json_bytes(want[k]))
                    _refuse(code, f"{record_key(table, stored)}: differs from the parent on {differing[:6]}")
        census = training_census(games)
        compiled = {}
        for p in records["parameters"]:
            model_id = p["model_id"]
            if model_id not in TREE_MODELS or p["parameter_key"] != model_id:
                _refuse("TREE_FIT_MISMATCH", "a parameter record names another model")
            if canonical_json_bytes(p["definition"]) != canonical_json_bytes(MODELS[model_id]) or \
                    p["model_sha256"] != model_sha256(model_id):
                _refuse("TREE_FIT_MISMATCH", f"{model_id}: the definition differs from the frozen definition")
            if canonical_json_bytes(p["training"]) != canonical_json_bytes(census):
                _refuse("TREE_FIT_MISMATCH", f"{model_id}: the training census differs from the frozen 2016-2022 rows")
            agreement = p["backend_agreement"]
            if agreement["state"] != "BUILD_ONLY_BACKEND_AGREEMENT_ATTESTATION_NOT_READER_VERIFIED" or \
                    agreement["views"] != 2 * len(games) or agreement["tolerance_repr"] != "1e-12" or \
                    repr_float(agreement["max_abs_difference_repr"]) is None or \
                    not repr_float(agreement["max_abs_difference_repr"]) <= 1e-12 or \
                    agreement["repeat_exports_identical"] is not True or agreement["repeat_fits"] < 1:
                _refuse("TREE_FIT_MISMATCH", f"{model_id}: the build-only backend agreement attestation is not within "
                                             "its rule")
            baseline, trees, counts = compile_trees(model_id, p["baseline"], p["stages"])
            if (p["stage_count"], p["node_count"], p["leaf_count"], p["max_depth_seen"]) != \
                    (len(p["stages"]), counts["node_count"], counts["leaf_count"], counts["max_depth_seen"]) or \
                    p["export_sha256"] != export_sha256(p):
                _refuse("TREE_STRUCTURE_MISMATCH", f"{model_id}: the export counts or digest differ from its trees")
            compiled[model_id] = (baseline, trees)
        witnesses: dict[tuple[str, str], tuple[str, str, str, str]] = {}
        estimates_by_key = {e["estimate_key"]: e for e in records["estimates"]}
        for g in games:
            for model_id in TREE_MODELS:
                a = estimates_by_key[f"{g['contest_key']}|{model_id}|A"]
                b = estimates_by_key[f"{g['contest_key']}|{model_id}|B"]
                stored = (a["raw_z_a_repr"], a["raw_z_b_repr"], a["raw_q_a_repr"], a["raw_q_b_repr"])
                where = f"{g['contest_key']}|{model_id}"
                if stored != (b["raw_z_a_repr"], b["raw_z_b_repr"], b["raw_q_a_repr"], b["raw_q_b_repr"]):
                    _refuse("TREE_ESTIMATE_MISMATCH", f"{where}: the two orientations carry different raw witnesses")
                values = [repr_float(t) for t in stored]
                if any(v is None for v in values) or not all(0.0 <= v <= 1.0 for v in values[2:]):
                    _refuse("TREE_ESTIMATE_MISMATCH", f"{where}: a raw witness is not a canonical finite repr "
                                                      "(q in [0, 1])")
                baseline, trees = compiled[model_id]
                z_a, q_a = traverse(baseline, trees, g["x_a"])
                z_b, q_b = traverse(baseline, trees, g["x_b"])
                if (z_a, z_b) != (values[0], values[1]):
                    _refuse("TREE_ESTIMATE_MISMATCH", f"{where}: the stored margins differ from the traversal of the "
                                                      "stored trees")
                if abs(q_a - values[2]) > 1e-12 or abs(q_b - values[3]) > 1e-12:
                    _refuse("TREE_ESTIMATE_MISMATCH", f"{where}: a stored raw probability differs from the traversal "
                                                      "by more than 1e-12")
                witnesses[(g["contest_key"], model_id)] = stored
        features = records["features"]
        labels = records["labels"]
        estimates = estimate_records(games, features, records["parameters"], witnesses)
        self._compare("estimates", records["estimates"], estimates, "TREE_ESTIMATE_MISMATCH")
        scores = self._verify_scores(games, labels, records["estimates"], records["scores"])
        summary = summary_records(records["scores"])
        self._verify_summary(records["summary"], summary)
        parent_summary_witness(summary, parent["records"]["summary"][0])
        return {"features": features, "labels": labels, "parameters": records["parameters"],
                "estimates": records["estimates"], "scores": scores, "summary": records["summary"]}

    @staticmethod
    def _compare(table: str, stored: list[dict[str, Any]], rebuilt: list[dict[str, Any]], code: str) -> None:
        for have, want in zip(stored, rebuilt):
            if canonical_json_bytes(have) != canonical_json_bytes(want):
                differing = sorted(k for k in want if canonical_json_bytes(have.get(k)) !=
                                   canonical_json_bytes(want[k]))
                _refuse(code, f"{record_key(table, have)}: the stored record differs from its re-derivation on "
                              f"{differing[:6]}")

    def _verify_scores(self, games: list[dict[str, Any]], labels: list[dict[str, Any]],
                       estimates: list[dict[str, Any]], stored: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rebuilt = score_records(games, labels, estimates)
        for have, want in zip(stored, rebuilt):
            where = record_key("scores", have)
            if want["parent_score"] is not None:
                line = untrusted_canonical(have["parent_score"], "TREE_RECORD_MALFORMED", f"score {where}")
                if line != canonical_json_bytes(want["parent_score"]):
                    _refuse("TREE_SCORE_MISMATCH", f"{where}: the embedded parent score is not the parent's bytes")
            if want["score_source"] == "NEW_FROZEN_TREE_FIT" and want["log_loss"] is not None and \
                    have["log_loss"] is not None:
                stored_value = repr_float(have["log_loss"])
                if stored_value is None or abs(stored_value - float(want["log_loss"])) > 1e-12:
                    _refuse("TREE_SCORE_MISMATCH", f"{where}: the stored log loss is not a canonical finite value within "
                                                   "1e-12 of the host recomputation")
                want = {**want, "log_loss": have["log_loss"]}
            if canonical_json_bytes(have) != canonical_json_bytes(want):
                differing = sorted(k for k in want if canonical_json_bytes(have.get(k)) != canonical_json_bytes(want[k]))
                _refuse("TREE_SCORE_MISMATCH", f"{where}: the stored score differs from its re-derivation on "
                                               f"{differing[:6]}")
        return stored

    @staticmethod
    def _verify_summary(stored: list[dict[str, Any]], rebuilt: list[dict[str, Any]]) -> None:
        float_fields = ("log_loss_total", "log_loss_mean")
        for have, want in zip(stored, rebuilt):
            where = record_key("summary", have)
            patched = dict(want)
            for name in float_fields:
                if want[name] is not None and have[name] is not None:
                    value = repr_float(have[name])
                    if value is None or abs(value - float(want[name])) > 1e-12:
                        _refuse("TREE_SUMMARY_MISMATCH", f"{where}: {name} differs from the stored per-game values by "
                                                         "more than 1e-12")
                    patched[name] = have[name]
            if want["comparisons"] is not None and type(have["comparisons"]) is list and \
                    len(have["comparisons"]) == len(want["comparisons"]):
                comparisons = []
                for have_c, want_c in zip(have["comparisons"], want["comparisons"]):
                    entry = dict(want_c)
                    if type(have_c) is dict and want_c.get("log_loss_mean_difference") is not None:
                        value = repr_float(have_c.get("log_loss_mean_difference"))
                        if value is None or abs(value - float(want_c["log_loss_mean_difference"])) > 1e-12:
                            _refuse("TREE_SUMMARY_MISMATCH", f"{where}: a log-loss difference differs by more than "
                                                             "1e-12")
                        entry["log_loss_mean_difference"] = have_c["log_loss_mean_difference"]
                    comparisons.append(entry)
                patched["comparisons"] = comparisons
            if canonical_json_bytes(have) != canonical_json_bytes(patched):
                differing = sorted(k for k in patched if canonical_json_bytes(have.get(k)) !=
                                   canonical_json_bytes(patched[k]))
                _refuse("TREE_SUMMARY_MISMATCH", f"{where}: the stored summary differs from its re-derivation on "
                                                 f"{differing[:6]}")

    @staticmethod
    def _name_index(features: list[dict[str, Any]]) -> dict[tuple[int, str], set[str]]:
        """The committed parent rule: each season's source team name of each key, casefolded."""
        names: dict[tuple[int, str], set[str]] = {}
        for f in features:
            names.setdefault((f["season"], f["team_key"]), set()).add(f["team_name"].casefold())
        return names

    def close(self) -> None:
        """Nothing stays open: the release and the in-memory parent are closed after verification."""

    def __enter__(self) -> "BoostingComparison":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- serving
    filters = staticmethod(validate_selection)

    def _team_keys(self, value: str) -> dict[int, set[str]]:
        """The team keys a team selector names in each season (org keys directly; names by the parent rule)."""
        if value.startswith("org:"):
            return {s: {value} for s in STUDY_SEASONS}
        folded = value.casefold()
        out: dict[int, set[str]] = {}
        for (season, key), names in self.names.items():
            if folded in names:
                out.setdefault(season, set()).add(key)
        return out

    def selected_games(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        team_keys = self._team_keys(filters["team"]) if "team" in filters else None
        if team_keys is not None and any(len(keys) > 1 for season, keys in team_keys.items()
                                         if "season" not in filters or season == filters["season"]):
            _refuse("TEAM_AMBIGUOUS", "the team name matches more than one parent team key in a season")
        out = []
        for g in self.games:
            if "season" in filters and g["season"] != filters["season"]:
                continue
            if "partition" in filters and g["partition"] != filters["partition"]:
                continue
            if "contest" in filters and g["contest_key"] != filters["contest"]:
                continue
            if team_keys is not None and not ({g["a_key"], g["b_key"]} & team_keys.get(g["season"], set())):
                continue
            out.append(g)
        return out

    def query(self, grain: Any, *, season: Any = None, team: Any = None, contest: Any = None, model: Any = None,
              partition: Any = None, slice_id: Any = None, limit: Any = None, offset: Any = None,
              all_rows: Any = False) -> dict[str, Any]:
        filters = validate_selection(grain, season=season, team=team, contest=contest, model=model,
                                     partition=partition, slice_id=slice_id)
        page_limit, page_offset = validate_paging(limit, offset, all_rows)
        result: dict[str, Any] = {
            "release_identity": self.database_identity, "content_identity": self.content_identity,
            "contract_id": self.anchors["contract_id"], "contract_sha256": self.anchors["contract_sha256"],
            "population": POPULATION, "grain": grain, "filters": dict(filters), "offset": page_offset,
            "limit": page_limit, **LABELS,
            "parent": {"database_identity": self.anchors["parent"]["database_identity"],
                       "content_identity": self.anchors["parent"]["content_identity"],
                       "sqlite_sha256": self.anchors["parent"]["sqlite_sha256"], "embedded": True},
            "verification": {**{f"{t}_verified": len(self.records[t]) for t in RECORD_TABLES},
                             "parent_blob_verified_before_parse": True, "trees_traversed": True,
                             "content_identity_rebuilt": True, "database_document_rebuilt": True,
                             "profile_pinned": self.anchors.get("profile") is not None,
                             "expected_identity_given": self.expect_identity is not None}}
        if grain == "tree-parameter":
            rows = [r for r in self.records["parameters"] if "model" not in filters or r["model_id"] == filters["model"]]
        else:
            chosen = self.selected_games(filters)
            keys = {g["contest_key"] for g in chosen}
            if grain == "tree-summary":
                slice_id = filters.get("slice", "NATIONAL")
                result["filters"]["slice"] = slice_id
                game_filtered = any(k in filters for k in ("season", "team", "contest", "partition"))
                rows = summary_records(self.records["scores"], keys) if game_filtered else self.records["summary"]
                rows = [r for r in rows if r["slice"] == slice_id and
                        ("model" not in filters or r["model_id"] == filters["model"])]
                result["summary_selection"] = {"rule": SUMMARY_RULE["selection"], "selected_games": len(chosen),
                                               "selected": "SELECTED_CANONICAL_GAMES" if game_filtered else
                                               "ALL_CANONICAL_GAMES"}
            else:
                table = GRAINS[grain]
                rows = [r for r in self.records[table] if r["contest_key"] in keys and
                        ("model" not in filters or r["model_id"] == filters["model"])]
        total = len(rows)
        if page_limit is None:
            page = rows[page_offset:]
        else:
            page = rows[page_offset:page_offset + page_limit]
        if page_limit == 0:
            next_offset = page_offset if page_offset < total else None
        else:
            next_offset = page_offset + len(page) if page_offset + len(page) < total else None
        result.update(total=total, returned=len(page), rows=page, next_offset=next_offset)
        return result


def query(database: Any, grain: Any, *, manifest: Any = None, expect_identity: Any = None, season: Any = None,
          team: Any = None, contest: Any = None, model: Any = None, partition: Any = None, slice_id: Any = None,
          limit: Any = None, offset: Any = None, all_rows: Any = False,
          anchors: dict[str, Any] | None = None) -> dict[str, Any]:
    """The direct Python interface: every selection, paging and identity refusal precedes any file access (frozen
    PRECEDENCE), then the release is verified completely and queried."""
    validate_selection(grain, season=season, team=team, contest=contest, model=model, partition=partition,
                       slice_id=slice_id)
    validate_paging(limit, offset, all_rows)
    validate_identity(expect_identity)
    with BoostingComparison(database, manifest=manifest, expect_identity=expect_identity, anchors=anchors) as reader:
        return reader.query(grain, season=season, team=team, contest=contest, model=model, partition=partition,
                            slice_id=slice_id, limit=limit, offset=offset, all_rows=all_rows)


# ---- BEGIN GENERATED ANCHORS (tools/cycle65/make_shallow_boosting_contract.py; never hand edited) ----
#: The pinned authority of the reader: the committed contract SHA-256, the exact accepted C56 parent (bytes, SHA-256,
#: identities, witness counts and digests) and the expected key inventory generated from that parent before any fit.
ANCHORS: dict[str, Any] = json.loads(r'''{
 "contract_id": "BAT-736-NATIONAL-SHALLOW-BOOSTING-COMPARISON-2016-2023-V1.0",
 "contract_sha256": "be9b82c48bbeff21e012370c31bdbaa8cbfcc66e9051562c3d6ba2501b055a76",
 "expected": {
  "comparison_games": 788,
  "counts": {
   "estimates": 23500,
   "features": 11750,
   "labels": 5875,
   "parameters": 2,
   "scores": 41125,
   "summary": 308
  },
  "fit_games": 5087,
  "games": 5875,
  "games_by_season": {
   "2016": 733,
   "2017": 753,
   "2018": 766,
   "2019": 769,
   "2020": 524,
   "2021": 767,
   "2022": 775,
   "2023": 788
  },
  "keys_sha256": {
   "estimates": "c7082cfed6153aa14e0278f0bcbdb5c4b93491a9bcf45fe00901089b8fc01f7a",
   "features": "1ed268adf813b641c1f3192ed6486c515dc7b2182410f1e1fb72ef79e7915865",
   "labels": "0405bc1908928050630aa3c5e2f97430a8724c72bb48cfc4f9ae179ec1de6367",
   "parameters": "0aed033adbc3c458dc61523717f848bc45f29931d2a57994fea24beb5a7427ae",
   "scores": "c8a9302ef2b3473fb8c2c68924faa2ee4d41f739f5358d7731373b35a67b1ed9",
   "summary": "961f7a361b76ffeb7794c0d6d095be1a98baab7c8fc940a176d7ef8ad29b3015"
  },
  "label_states": {
   "DECISIVE": 5875,
   "TIE": 0
  },
  "slice_games": {
   "COLD_START": 410,
   "FIRST_FOUR_TEAM_GAMES": 1819,
   "NATIONAL": 5875,
   "TEXAS_AM": 91
  },
  "y_a_counts": {
   "0": 3032,
   "1": 2843
  }
 },
 "frozen_at_utc": "2026-10-24T17:49:32Z",
 "parent": {
  "blocks": 34,
  "bytes": 10584064,
  "content_identity": "fe303a90d8753956b914d3c7c2adfe2d33d9816bfb45689b0361f8e36e2e6cc0",
  "contract_id": "BAT-423-NATIONAL-RETROSPECTIVE-REFERENCE-2016-2023-V1.0",
  "contract_sha256": "3cfeff255bb29801b482b02611ad2c72c725d069e9f89d3911e86711af34bb31",
  "database_identity": "ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8",
  "model_sha256": {
   "NULL_HALF_V1": "c9f511c047ef9a24ff5873021660e2592e0fd6fa69865418696cbd2cdff6fe04",
   "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1": "eb074c84ad3e50fd268d354904f6b11c23f6c3fc844b743fc112917adafd8bc5",
   "PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1": "619cbf736dad1f86efed4791b6537ccad11e546c24ab09de0a9c861797b64d30",
   "SITE_BLIND_ELO_REFERENCE_V1": "8ed6384a46a630eb32d833ca508bbc6dca61e6e6fa4300f3e38fc8bf7eb7c73a",
   "SMOOTHED_HISTORY_ODDS_V1": "340128c116d4e5902f582827c0400bb63d8417973d63cd815481fc985126cbfa"
  },
  "population": "national_retrospective_reference_2016_2023",
  "record_counts": {
   "estimates": 58750,
   "features": 11750,
   "labels": 5875,
   "parameters": 5,
   "scores": 29375,
   "summary": 1
  },
  "schema_version": "BAS-RETROSPECTIVE-REFERENCE-DB-1",
  "sqlite_sha256": "17a0776587eb30918903dc0d38c736958b1984feb4b40379bbfc80425035785d",
  "total_decompressed_bytes": 156335348
 }
}''')
#: The canonical profile of the first authorized build (None until that build is pinned by --profile).
BOOSTING_PROFILE: dict[str, Any] | None = None
# ---- END GENERATED ANCHORS ----
