r"""National retrospective site/calendar association 2016-2023 (BAT-734 bounded research contribution to BAT-417,
BAT-419 and BAT-423, Cycle #63 TP63-A01).

Every rule lives here, and the committed research/data contract
``configs/national_site_calendar_association_2016_2023_contract.json`` must equal these constants (the builder refuses
otherwise). The reader pins that contract's SHA-256, every accepted parent identity, the expected collection of every
grain (the frozen common cohort included) and, once materialized, the canonical profile (:data:`ANCHORS`,
:data:`CONTEXT_PROFILE`).

Authority. This is separately authorized retrospective association research,
RETROSPECTIVE_SOURCE_CLAIM_SITE_CALENDAR_ASSOCIATION_NOT_FORECAST. Every record is RETROSPECTIVE_RESEARCH,
UNTRUSTED_SHADOW, PIT_NOT_ADMITTED, NOT_A_FORECAST, NOT_CALIBRATED and predictive skill NOT_ESTABLISHED. The 2023
comparison is ALREADY_EXPOSED_RETROSPECTIVE_2023_NOT_BLIND, and the complete-case support and the design were chosen
with the full 2016-2023 source census (2023 included) in view and frozen before any fit or metric: they are not
independent of that observed support. The agreed designated source site is a source-claim designation, never a physical
home field, stadium familiarity or causal bonus; a calendar interval is a date gap to the latest eligible accepted
prior, never physiological rest or actual travel; a provider start is a scheduled claim, never an actual kickoff; the
provider captures were retrieved in August 2026, after every target, and are no historical first-known evidence.
Adverse and null results are completed results; a numerical or integrity failure is a failure, never a null result.

Inputs (read only, each pinned by its whole-file SHA-256 under an explicitly named data root; see
:mod:`.context_association_build`): the accepted C38 parent population (contest rows and its participant identity
bindings), the accepted C39 history prefix (targets, the two oriented history views and their eligible same-season
priors), the accepted C56 national retrospective reference (its feature, label and five unchanged parent game-score
records) and the eight retained full FBS provider game captures 2016-2023 with their eight capture receipts.

Derivation order (each step reads only what it names):

1. **qualification** -- one record per accepted target: both participants' unique accepted provider bindings, the
   target's sole documented provider game in its own season's capture with typed id/season/participants/neutral/start
   claims, the provider source-site claim (neutral flag and bound home side) beside the accepted parent role and their
   agreement, the provider start claim against the accepted calendar date window [D-14h, D+36h), each side's accepted
   C56 history counts and its latest strictly earlier eligible same-season C39 prior (null with
   NO_ELIGIBLE_SAME_SEASON_PRIOR, AMBIGUOUS_LATEST_PRIOR or PRIOR_LINEAGE_INVALID, never zero), the source clocks and
   the common-support state with every reason.
2. **features** -- both oriented views of every target from its qualification alone: ``h = ell_A - ell_B`` with
   ``ell = log(2W + T + 2) - log(2L + T + 2)``, the agreed site code ``s`` (+1 agreed HOME of the view's team, -1 of
   its opponent, 0 NEUTRAL) and the exact integer calendar difference ``c``; view B is the exact negation of view A.
3. **fits** -- the FIT cohort is the common-support 2016-2022 games with a decisive label; paired FIT-only RMS scales
   (no centering, the history scale shared); CTX-HISTORY-LOGIT-V1 on (h) and CTX-SITE-CALENDAR-LOGIT-V1 on (h, s, c)
   with the unchanged accepted :func:`aggie_analytics.retrospective_baseline.reference_fit.fit_logistic` (zero
   intercept, lambda 1, paired rows of weight 1/2). A genuine fit failure is recorded and both of its rows abstain.
4. **estimates** -- every target, new model and orientation, the game-grain probability first, B its exact decimal
   complement; outside common support every new model abstains with the reasons.
5. **scores** -- one A-oriented new score per target and new model (exact rational Brier of the served probability,
   log loss with only its argument clipped to [1e-15, 1 - 1e-15]), and one unchanged C56 parent game-score witness per
   target and parent model (the exact accepted record, its line SHA-256 and metric kind; ridge stays margin-only).
6. **summary** -- 70 rows: every model over SEASON 2016..2023, PARTITION FIT (2016-2022, in-sample for the new fits)
   and PARTITION COMPARISON (2023, exposed), each over exactly the common-support games of its window; only the
   challenger row carries its delta to CTX-HISTORY-LOGIT-V1 on identical games. No significance, calibration,
   champion, causal or skill conclusion follows.

The reader (:class:`ContextAssociation`) needs no data root: before any row is served it verifies the location, the
run manifest, the database bytes, the schema and meta claims, every record's exact members and JSON types, the complete
expected collection of every grain, every qualification rule the records can re-derive, the frozen common cohort, the
features, a fresh refit and the complete re-derivation of every estimate, score, witness binding, summary and census
record, the content document, the contract-defined database identity document and the pinned canonical profile. The
query serves six grains through the explicit ``bas-retrospective-baseline-query --context-association`` mode only.
"""
from __future__ import annotations

import copy
import json
import math
import os
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

POPULATION = "national_site_calendar_association_2016_2023"
DB_FILE = "national_site_calendar_association.sqlite"
CONTRACT_ID = "BAT-734-NATIONAL-SITE-CALENDAR-ASSOCIATION-2016-2023-V1.0"
CONTRACT_REL = "configs/national_site_calendar_association_2016_2023_contract.json"
CONTENT_SCHEMA = "BAS-SITE-CALENDAR-ASSOCIATION-CONTENT-1"
DATABASE_SCHEMA = "BAS-SITE-CALENDAR-ASSOCIATION-DATABASE-1"
DB_SCHEMA = "BAS-SITE-CALENDAR-ASSOCIATION-DB-1"
PAYLOAD_SCHEMA = "BAS-SITE-CALENDAR-ASSOCIATION-PAYLOAD-1"
CONTENT_STAGE = "site-calendar-association-content"
DATABASE_STAGE = "site-calendar-association-database"

STUDY_SEASONS = (2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023)
FIT_SEASONS = (2016, 2017, 2018, 2019, 2020, 2021, 2022)
COMPARISON_SEASONS = (2023,)
PARTITIONS = {"FIT": FIT_SEASONS, "COMPARISON": COMPARISON_SEASONS}
PARTITION_IDS = tuple(PARTITIONS)
VIEWS = ("A", "B")
IDENTITY_RE = re.compile(r"[0-9a-f]{64}\Z")
TEAM_KEY_RE = re.compile(r"org:([1-9][0-9]{0,11})\Z")
TEAM_SELECTOR_RE = re.compile(r"(?:org:)?([0-9]{1,12})\Z")
CONTEST_SELECTOR_RE = re.compile(r"(?:ncaa:)?([0-9]{1,12})\Z")
CONTEST_KEY_RE = re.compile(r"ncaa:[0-9]{1,12}\Z")
SEASON_SELECTOR_RE = re.compile(r"[0-9]{4}\Z")
DATE_RE = re.compile(r"(19|20)[0-9]{2}-[01][0-9]-[0-3][0-9]\Z")
START_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z\Z")
DEC12_RE = re.compile(r"-?(0|[1-9][0-9]{0,15})\.[0-9]{12}\Z")
DIGITS_RE = re.compile(r"[0-9]{1,12}\Z")
#: Count fields are bounded to their natural domain before any arithmetic (a forged huge integer is refused, never
#: converted to binary64).
HISTORY_BOUND = 1_000
INTERVAL_BOUND = 400

LABELS = {
    "evidence_label": "RETROSPECTIVE_RESEARCH",
    "association_authority": "RETROSPECTIVE_SOURCE_CLAIM_SITE_CALENDAR_ASSOCIATION_NOT_FORECAST",
    "trust_state": "UNTRUSTED_SHADOW",
    "pit_eligibility": "PIT_NOT_ADMITTED",
    "calibration": "NOT_CALIBRATED",
    "predictive_skill": "NOT_ESTABLISHED",
    "forecast_status": "NOT_A_FORECAST",
    "site_meaning": "AGREED_DESIGNATED_SOURCE_SITE_NOT_PHYSICAL_HOME_FIELD_STADIUM_FAMILIARITY_OR_CAUSAL_BONUS",
    "calendar_meaning": "CALENDAR_DATE_GAP_TO_LATEST_ELIGIBLE_ACCEPTED_PRIOR_NOT_PHYSIOLOGICAL_REST_OR_ACTUAL_TRAVEL",
    "provider_start_meaning": "PROVIDER_SCHEDULED_START_CLAIM_NOT_ACTUAL_KICKOFF",
    "provider_clock": "PROVIDER_CAPTURES_RETRIEVED_AUGUST_2026_AFTER_EVERY_TARGET_NOT_HISTORICAL_FIRST_KNOWN",
    "provider_lineage": "CFBD_AGGREGATED_OR_DERIVED_RECORD_AGREEMENT_IS_NOT_INDEPENDENT_UPSTREAM_CONFIRMATION",
    "history_clock": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME",
    "parent_eligibility": "PARENT_ELIGIBILITY_FLAGS_AND_SCIENTIFIC_HOLDS_UNCHANGED",
    "comparison_2023": "ALREADY_EXPOSED_RETROSPECTIVE_2023_NOT_BLIND",
    "support_design_exposure": "SUPPORT_AND_DESIGN_INFORMED_BY_FULL_2016_2023_CENSUS_FROZEN_BEFORE_ANY_FIT_OR_METRIC",
    "fit_authority": "TP63_TWO_FROZEN_RETROSPECTIVE_FITS_2016_2022_ONLY",
    "parent_comparators": "FIVE_UNCHANGED_C56_GAME_SCORE_COMPARATORS_PROJECTED_ON_THE_COMMON_COHORT_CONTEXTUAL_ONLY",
    "champion": "NO_CHAMPION_SELECTED",
    "causal_interpretation": "NO_CAUSAL_SITE_REST_OR_TRAVEL_CONCLUSION",
    "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
    "selection": "EXPLICIT_CONTEXT_ASSOCIATION_SELECTION_ONLY_NEVER_A_DEFAULT",
}
#: Labels every record carries (the rest are release-level labels in meta and every response).
RECORD_LABEL_KEYS = ("evidence_label", "association_authority", "trust_state", "pit_eligibility", "predictive_skill")
RECORD_LABELS = {k: LABELS[k] for k in RECORD_LABEL_KEYS}

# --------------------------------------------------------------------------------------------- models

MODEL_HISTORY = "CTX-HISTORY-LOGIT-V1"
MODEL_SITE_CALENDAR = "CTX-SITE-CALENDAR-LOGIT-V1"
NEW_MODELS = (MODEL_HISTORY, MODEL_SITE_CALENDAR)
PARENT_NULL = "NULL_HALF_V1"
PARENT_SMOOTHED = "SMOOTHED_HISTORY_ODDS_V1"
PARENT_ELO = "SITE_BLIND_ELO_REFERENCE_V1"
PARENT_LOGISTIC = "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1"
PARENT_RIDGE = "PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1"
PARENT_MODELS = (PARENT_NULL, PARENT_SMOOTHED, PARENT_ELO, PARENT_LOGISTIC, PARENT_RIDGE)
#: The closed model namespace (TP63 section 12): the two new fits and the five unchanged C56 game-score comparators.
MODEL_IDS = (*NEW_MODELS, *PARENT_MODELS)
PROBABILITY_MODELS = MODEL_IDS[:-1]
MARGIN_MODELS = (PARENT_RIDGE,)
#: The accepted C56 model definition digests every parent witness must carry unchanged.
PARENT_MODEL_SHA256 = {
    PARENT_NULL: "c9f511c047ef9a24ff5873021660e2592e0fd6fa69865418696cbd2cdff6fe04",
    PARENT_SMOOTHED: "340128c116d4e5902f582827c0400bb63d8417973d63cd815481fc985126cbfa",
    PARENT_ELO: "8ed6384a46a630eb32d833ca508bbc6dca61e6e6fa4300f3e38fc8bf7eb7c73a",
    PARENT_LOGISTIC: "eb074c84ad3e50fd268d354904f6b11c23f6c3fc844b743fc112917adafd8bc5",
    PARENT_RIDGE: "619cbf736dad1f86efed4791b6537ccad11e546c24ab09de0a9c861797b64d30",
}
HISTORY_COLUMN = "history_log_odds_difference"
SITE_COLUMN = "agreed_designated_site_code"
CALENDAR_COLUMN = "calendar_interval_difference_days"
COLUMNS = {MODEL_HISTORY: (HISTORY_COLUMN,), MODEL_SITE_CALENDAR: (HISTORY_COLUMN, SITE_COLUMN, CALENDAR_COLUMN)}
LOG_CLIP = 1e-15
CLIP_CONVENTION = "CLIPPED_LOG_ARGUMENT_1E-15"
_SOLVER = {"interface": rf.VERSION,
           "function": "aggie_analytics.retrospective_baseline.reference_fit.fit_logistic (unchanged)",
           "lambda": 1, "max_newton_steps": rf.MAX_NEWTON_STEPS, "gradient_inf_norm_tolerance": "1e-10",
           "max_halvings": rf.MAX_HALVINGS, "start": "zero"}
_OBJECTIVE = ("mean weighted binary cross-entropy over the paired FIT rows (weight 1/2 each) plus (1/2) sum(beta_j^2) "
              "(lambda 1, every column, zero intercept)")
MODELS: dict[str, dict[str, Any]] = {
    MODEL_HISTORY: {
        "model_id": MODEL_HISTORY, "version": 1, "family": "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_RETROSPECTIVE_RESEARCH",
        "output": "WIN_PROBABILITY", "columns": list(COLUMNS[MODEL_HISTORY]),
        "formula": "p_A = sigmoid(z . beta), z the FIT-RMS-scaled A-minus-B design (h), zero intercept",
        "objective": _OBJECTIVE, "solver": _SOLVER, "fit_seasons": list(FIT_SEASONS), "labels_used": ["DECISIVE"],
        "fitted": True, "intercept": None, "role": "FROZEN_HISTORY_ONLY_CONTROL"},
    MODEL_SITE_CALENDAR: {
        "model_id": MODEL_SITE_CALENDAR, "version": 1,
        "family": "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_RETROSPECTIVE_RESEARCH", "output": "WIN_PROBABILITY",
        "columns": list(COLUMNS[MODEL_SITE_CALENDAR]),
        "formula": "p_A = sigmoid(z . beta), z the FIT-RMS-scaled A-minus-B design (h, s, c), zero intercept",
        "objective": _OBJECTIVE, "solver": _SOLVER, "fit_seasons": list(FIT_SEASONS), "labels_used": ["DECISIVE"],
        "fitted": True, "intercept": None, "role": "FROZEN_HISTORY_PLUS_SITE_AND_CALENDAR_CHALLENGER"},
}
PARENT_COMPARATORS = {
    "release": "the accepted C56 national retrospective reference (contract 3cfeff25..., identity ad01a42f...)",
    "models": {m: {"model_sha256": PARENT_MODEL_SHA256[m], "metric_kind": "MARGIN" if m in MARGIN_MODELS else
                   "PROBABILITY"} for m in PARENT_MODELS},
    "witness": "one record per accepted target and parent model holding the exact accepted C56 game-score record "
               "(parsed from its canonical line, which it must reproduce byte for byte), that line's SHA-256 and its "
               "metric kind; the 58,750 parent estimates stay in the accepted C56 release and are not duplicated",
    "unchanged": "parent raw values, equations, parameters and their fitting population (5,087 games) never change; "
                 "the projections are contextual benchmarks on the common cohort, not the two-model matched ablation",
    "ridge": "PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1 is margin-only: absolute and squared margin errors, never a "
             "probability, Brier or log loss",
}

# --------------------------------------------------------------------------------------------- frozen rules

ACCEPTED_BINDING_RULES = ("NAME_CONFIRMED_BY_SCHEDULE", "SCHEDULE_FINGERPRINT_ONLY")
PRIOR_RULE = "SAME_SEASON_DATE_STRICTLY_BEFORE_TARGET_DATE"
PARENT_SITES = ("HOME_A", "HOME_B", "NEUTRAL")
BINDING = {
    "input": "the accepted C38 participant identity bindings (identity_bindings.jsonl.gz of the pinned population)",
    "rule": "each target participant org_id maps to exactly one binding row whose cfbd_team_id is a digit string and "
            "whose rule is NAME_CONFIRMED_BY_SCHEDULE or SCHEDULE_FINGERPRINT_ONLY; otherwise the side is UNSUPPORTED "
            "with its reason (NO_ACCEPTED_PARTICIPANT_BINDING, BINDING_DUPLICATED, BINDING_NOT_CONFIRMED); two "
            "participants bound to one provider team are PARTICIPANT_BINDING_UNSUPPORTED",
    "accepted_rules": list(ACCEPTED_BINDING_RULES),
    "never": ["equal numeric IDs", "team names or abbreviations", "fuzzy matching", "another season's binding"],
}
PROVIDER_JOIN = {
    "capture": "the one pinned full FBS games capture of the target's own season",
    "documented_game_ids": "the accepted C39 target's cfbd_game_ids, equal to its C38 parent contest row's; exactly "
                           "one is required",
    "game_row": "the single capture row whose integer id equals that identifier; a duplicated id is ambiguous",
    "field_shapes": "id, season, homeId and awayId are JSON integers, neutralSite and startTimeTBD booleans and "
                    "startDate a string; any other shape is PROVIDER_FIELD_MALFORMED",
    "season": "the row's integer season equals the target's season",
    "participants": "the unordered pair of the row's homeId and awayId equals the two bound cfbd_team_id values",
    "site_claim": "neutralSite true claims NEUTRAL; false claims HOME for the side whose binding equals homeId "
                  "(HOME_A or HOME_B); the claim is kept beside the accepted parent role, with explicit agreement",
    "fields_read": ["id", "season", "homeId", "awayId", "neutralSite", "startDate", "startTimeTBD"],
    "never_read": "points, line scores, Elo, win probabilities, attendance, venue or any other outcome or context field",
}
DATE_WINDOW = {
    "rule": "the provider start instant is compatible with the accepted calendar date D when it lies in "
            "[D 00:00 at UTC+14:00, D 24:00 at UTC-12:00), i.e. [D-1 10:00Z, D+1 12:00Z); no timezone is inferred "
            "for D (the accepted C58 window)",
    "lower_offset_hours": -14,
    "upper_offset_hours": 36,
    "pattern": "YYYY-MM-DDTHH:MM:SS[.ffffff]Z (an explicit UTC instant)",
    "meaning": "a scheduled provider claim compatible with the calendar date; never an actual kickoff",
}
CALENDAR = {
    "prior_rule": PRIOR_RULE,
    "pool": "the accepted C39 history view's contributing contests of the side (the accepted eligible same-season "
            "prior pool), equal to the accepted C56 feature's contributing contests",
    "lineage": "every eligible prior joins its own C38 parent contest of the same season, with that side as a "
               "participant, the recorded date and a date strictly before the target's; otherwise "
               "PRIOR_LINEAGE_INVALID",
    "interval_days": "target date minus the unique latest eligible prior date, in days (an exact integer)",
    "intervening_calendar_days": "interval_days minus one (reported, never a fitted column)",
    "empty_pool": "null with NO_ELIGIBLE_SAME_SEASON_PRIOR; never zero, never a previous season",
    "tie": "several eligible prior keys on the latest date: null with AMBIGUOUS_LATEST_PRIOR and every key; never input "
           "order",
    "excluded": "excluded (ineligible) earlier same-season inputs are counted; those dated after the latest eligible "
                "prior are counted separately (the interval is to the latest eligible prior, not to every game "
                "played)",
    "never": ["physiological rest", "actual travel", "every game played", "a previous season", "zero imputation"],
}
CALENDAR_STATES = ("QUALIFIED_CALENDAR_INTERVAL", "NO_ELIGIBLE_SAME_SEASON_PRIOR", "AMBIGUOUS_LATEST_PRIOR",
                   "PRIOR_LINEAGE_INVALID")
SITE_RULE = {
    "agreement": "AGREE when the provider claim equals the accepted parent site (HOME_A, HOME_B or NEUTRAL); "
                 "DISAGREE otherwise; UNSUPPORTED when the provider game is not joined or the parent site is not one "
                 "of the three",
    "code": "s = +1 for agreed HOME of the view's team, -1 for agreed HOME of its opponent, 0 for agreed NEUTRAL; null "
            "unless AGREE",
    "neutral_swap": "a nominal home/away designation swap at an agreed NEUTRAL site keeps s = 0 and only reorients the "
                    "team-bound values",
    "meaning": LABELS["site_meaning"],
}
SUPPORT = {
    "rule": "COMMON_SUPPORT when both bindings are BOUND, the provider game is joined, the agreed site is AGREE, the "
            "start claim is COMPATIBLE_WITH_PARENT_LOCAL_DATE and both sides have QUALIFIED_CALENDAR_INTERVAL; "
            "otherwise OUTSIDE_COMMON_SUPPORT with every failing reason in a fixed order",
    "reason_order": ["A_<binding reason>", "B_<binding reason>", "PROVIDER_<join reason> (a reason already starting "
                     "PROVIDER_ is kept; PARTICIPANT_BINDING_UNSUPPORTED only when both bindings are BOUND)",
                     "SITE_DISAGREES_WITH_PARENT or SITE_PARENT_SITE_UNSUPPORTED", "DATE_<date reason>",
                     "A_CALENDAR_<state>", "B_CALENDAR_<state>"],
    "frozen": "the common cohort is the committed contract's expected collection (observed by the full source-only "
              "census before any fit); a derivation that differs is refused as population drift, never forced",
    "labels": "label identity is exact (the accepted C56 label of the same game); only DECISIVE labels enter the fit "
              "and the probability scores",
}
DESIGN = {
    "history_log_odds": "ell_s = math.log(2*wins_s + ties_s + 2) - math.log(2*losses_s + ties_s + 2) with the integer "
                        "arguments formed exactly and the two binary64 logarithms of the pinned CPython subtracted once",
    "history_counts": "the accepted C56 feature record's same-season, strictly earlier-date wins, losses, ties and "
                      "games of each side, the target excluded, with the contributing contest keys kept as lineage",
    "h": "ell_A - ell_B (one binary64 subtraction)",
    "s": "the agreed designated site code of view A as a binary64 (+1.0, -1.0 or 0.0)",
    "c": "interval_days_A - interval_days_B as an exact integer, converted once to binary64; no clipping or binning",
    "orientation": "view A is the canonical (parent a) side; view B's vector is the exact negation of view A's "
                   "(negative zero normalized to zero), never recomputed",
    "designs": {MODEL_HISTORY: ["h"], MODEL_SITE_CALENDAR: ["h", "s", "c"]},
    "missing": "outside common support the design is null, never zero; every model abstains",
    "excluded_from_design": ["intercept", "absolute or squared terms", "interactions", "intervening days column",
                             "manual A&M bonus", "travel distance", "weather", "personnel", "market"],
}
SCALING = {"rule": "scale_j = math.sqrt(math.fsum(0.5 * x_ij * x_ij for every paired FIT row i, A then B, in canonical "
                   "game order) / N_fit_games); no centering (odd orientation symmetry preserved); a zero scale is 1 "
                   "and the column is marked constant; z_ij = x_ij / scale_j",
           "rows": "the FIT cohort only (common-support 2016-2022 games with a DECISIVE label); never a 2023 game",
           "shared": "both models use the same history-column scale (the first scale of the three-column design)"}
FIT_RULE = {"cohort": "common-support games of 2016-2022 whose accepted label is DECISIVE, canonical (season, date, "
                      "contest key) order",
            "rows": "per game the A row (z, y_A) and the B row (-z, 1 - y_A), each of weight 1/2 (total weight = games)",
            "failure": "a refused fit (FIT_EMPTY, FIT_RAGGED, FIT_NONFINITE_INPUT, FIT_NONFINITE, FIT_NOT_CONVERGED, "
                       "FIT_SINGULAR, FIT_BACKTRACK_EXHAUSTED) is recorded with its trajectory as the parameter state; "
                       "that model then abstains on every game (ABSTAIN_FIT_FAILED); nothing is tuned afterwards",
            "comparison_2023": "never in the fit, the scales, early stopping, any constant or any selection",
            "no_search": "no penalty, column, transformation or cohort search; no change after any outcome"}
ESTIMATE_RULE = {
    "game_grain": "the A-orientation probability is built first; B is its exact decimal complement",
    "fitted": "p_A = decimal12(rf.sigmoid(rf.linear(z_A, beta))); p_B = 1 - p_A exactly in decimal; the linear predictor "
              "decimal12 and both unrounded values as repr() text are kept",
    "support": "only common-support games are estimated; every other game abstains for both new models with "
               "ABSTAIN_OUTSIDE_COMMON_SUPPORT and the support reasons",
    "sample_state": {"fit_cohort": "IN_SAMPLE_FIT_2016_2022_FITTED_DATA",
                     "fit_season_outside_cohort": "FIT_SEASON_GAME_OUTSIDE_FIT_COHORT",
                     "comparison": "OUT_OF_FIT_EXPOSED_2023_COMPARISON"},
}
SCORE_RULE = {
    "orientation": "A (the canonical game); each canonical game is counted once per model",
    "brier": "(p_A served - y_A)^2 as an exact rational of the served decimal probability",
    "log_loss": "-math.log(clip(q)) with q the correctly rounded binary64 of the exact served probability of the "
                "observed side, clip to [1e-15, 1 - 1e-15] applied only to the argument (CLIPPED_LOG_ARGUMENT_1E-15); "
                "repr() text",
    "unscored": {"ABSTAINED_OUTSIDE_COMMON_SUPPORT": "no estimate outside common support",
                 "ABSTAINED_FIT_FAILED": "a recorded fit failure", "LABEL_TIE": "a tie is never made decisive",
                 "LABEL_MISSING": "no accepted outcome", "LABEL_UNSUPPORTED": "an unsupported accepted label"},
    "grain": "the context-score grain serves the 11,750 new score records and the 29,375 unchanged parent witnesses "
             "together in (season, date, contest key, model) order, each with its score_source and metric_kind",
}
SUMMARY_RULE = {
    "windows": "SEASON 2016..2023, PARTITION FIT (2016-2022) and PARTITION COMPARISON (2023); the season 2023 and "
               "pooled COMPARISON windows are distinct scopes; no pooled in-sample plus comparison window",
    "rows": "one row per window and model, 70 canonical rows, in window then model order",
    "cohort": "every row of a window uses exactly the common-support games of that window (and of the selection); "
              "window targets, eligible games, excluded games and, for parents, their original scored games are "
              "separate counts",
    "probability_metrics": "scored and unscored games by reason, Brier total and mean (exact rationals with decimal12), "
                           "log loss total (math.fsum in canonical game order) and mean (repr)",
    "margin_metrics": "PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1: absolute and squared margin error totals, MAE and MSE "
                      "(exact rationals with decimal12) and RMSE = math.sqrt of the binary64 of the exact MSE; never a "
                      "probability metric",
    "fit_partition": "FIT-window rows of the new models are fitted-data (in-sample) summaries; COMPARISON rows are "
                     "exposed, out-of-fit and not blind",
    "challenger_delta": "only the CTX-SITE-CALENDAR-LOGIT-V1 row carries challenger-minus-CTX-HISTORY-LOGIT-V1 Brier "
                        "and log-loss mean differences on the identical scored games of the same window and selection; "
                        "the control is computed even when --model hides its row; every other row's delta is null and "
                        "NOT_CLAIMED; a failed fit leaves null differences with the failure reason",
    "primary": "the challenger row of the unfiltered PARTITION COMPARISON window: challenger minus control Brier mean "
               "over the common 2023 games (negative = lower descriptive Brier, zero = equal, positive = higher)",
    "common_scored_keys": "all probability models without a recorded fit failure score exactly the same game keys in a "
                          "window; the margin model scores the decisive and tied eligible games",
    "selection": "with any season/partition/team/contest selector the rows are re-derived over exactly the selected "
                 "eligible games before any model filter or paging; a window without a selected eligible game has no "
                 "row; an empty eligible selection returns rows = []; --model keeps that model's rows and never "
                 "changes the cohort or the hidden control",
    "no_inference": "no significance, bootstrap, calibration, champion, causal or predictive-skill conclusion",
}
NUMERIC_CONTRACT = {
    "arithmetic": "IEEE-754 binary64 in a fixed order; every reduction math.fsum; math.log, math.exp, math.log1p and "
                  "math.sqrt of the pinned CPython 3.12.10",
    "decimal12": "a served binary64 value is its exact decimal expansion rounded half-even to 12 places (negative zero "
                 "normalized) as a JSON string; complements and negations are exact decimal operations",
    "rationals": "{numerator, denominator} JSON integers in lowest terms, denominator > 0",
    "floats": "binary64 log-odds and design values are JSON numbers (finite; their repr round-trips exactly; negative "
              "zero normalized to zero)",
    "counts": "JSON integers only, within their domain; a boolean or an integral float is not a count",
    "independent_tolerance": "an independent oracle agrees within 1e-9 absolute on scales, coefficients and "
                             "probabilities and within 1e-8 on objective and gradients; keys, counts, states, "
                             "identities and exact rationals agree exactly; byte identity of rebuilds is a separate "
                             "property",
    "canonical_json": "json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) as UTF-8",
}
SUPPORT_STATES = ("COMMON_SUPPORT", "OUTSIDE_COMMON_SUPPORT")
BINDING_STATES = ("BOUND", "UNSUPPORTED")
PROVIDER_STATES = ("PROVIDER_GAME_JOINED", "UNSUPPORTED")
SITE_AGREEMENTS = ("AGREE", "DISAGREE", "UNSUPPORTED")
DATE_STATES = ("COMPATIBLE_WITH_PARENT_LOCAL_DATE", "INCOMPATIBLE_WITH_PARENT_LOCAL_DATE", "UNSUPPORTED")
LABEL_STATES = ("DECISIVE", "TIE", "MISSING")

# --------------------------------------------------------------------------------------------- record fields

#: Type codes: s str, s? str|null, i int, i? int|null, b bool, f float, f? float|null, ls list of str, lf list of float,
#: lf? list of float or null, q exact rational, q? rational|null, d decimal12 string, d? decimal12|null, j any JSON
#: value (only members re-derived or hash-bound wholesale), @name / @name? a nested object of that spec (or null).
_LABEL_TYPES = {k: "s" for k in RECORD_LABEL_KEYS}
SUBSPECS: dict[str, dict[str, str]] = {
    "binding": {"state": "s", "reason": "s?", "cfbd_team_id": "s?", "rule": "s?", "line_number": "i?",
                "line_sha256": "s?"},
    "provider": {"capture_season": "i", "capture_sha256": "s", "row_ordinal": "i", "game_id": "s", "season": "i",
                 "home_id": "s", "away_id": "s", "neutral_site": "b", "start_claim_utc": "s", "start_time_tbd": "b",
                 "row_sha256": "s"},
    "capture_clock": {"capture_id": "s", "receipt_sha256": "s", "response_sha256": "s", "capture_known_at_utc": "s",
                      "retrieved_at_utc": "s", "source_uri": "s", "upstream_lineage": "s",
                      "observed_after_target": "b"},
    "history": {"games": "i", "wins": "i", "losses": "i", "ties": "i", "cold_start": "b",
                "contributing_contest_keys": "ls", "log_odds": "f"},
    "calendar": {"state": "s", "latest_prior_date": "s?", "latest_prior_contest_keys": "ls", "interval_days": "i?",
                 "intervening_calendar_days": "i?", "eligible_prior_count": "i", "excluded_prior_count": "i",
                 "excluded_prior_after_latest_eligible": "i", "lineage_state": "s"},
}
FIELD_TYPES: dict[str, dict[str, str]] = {
    "qualifications": {
        "record_type": "s", "qualification_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
        "partition": "s", "a_key": "s", "b_key": "s", "a_org_id": "s", "b_org_id": "s", "a_team_name": "s",
        "b_team_name": "s", "parent_site": "s", "parent_neutral_site_text": "s?",
        "documented_provider_game_ids": "ls", "a_binding": "@binding", "b_binding": "@binding",
        "provider": "@provider?", "provider_state": "s", "provider_reason": "s?", "provider_home_side": "s?",
        "provider_site_claim": "s?", "site_agreement": "s", "agreed_site": "s?", "date_state": "s",
        "date_reason": "s?", "provider_utc_date_offset_days": "i?", "capture_clock": "@capture_clock?",
        "a_history": "@history", "b_history": "@history", "a_calendar": "@calendar", "b_calendar": "@calendar",
        "label_state": "s", "label_record_sha256": "s", "support_state": "s", "support_reasons": "ls",
        "support_pattern": "s", "target_record_sha256": "s", "parent_contest_sha256": "s",
        "history_view_sha256": "ls", "reference_feature_sha256": "ls", "history_identity": "s",
        "population_identity": "s", "reference_identity": "s", **_LABEL_TYPES},
    "features": {
        "record_type": "s", "feature_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
        "partition": "s", "view": "s", "team_key": "s", "team_name": "s", "team_org_id": "s", "opponent_key": "s",
        "opponent_name": "s", "opponent_org_id": "s", "team_history": "@history", "opponent_history": "@history",
        "team_calendar": "@calendar", "opponent_calendar": "@calendar", "history_log_odds_difference": "f",
        "agreed_site": "s?", "site_code": "i?", "calendar_interval_difference_days": "i?", "support_state": "s",
        "abstention_reasons": "ls", "design_history": "lf?", "design_site_calendar": "lf?",
        "target_excluded_from_history": "b", "qualification_record_sha256": "s", **_LABEL_TYPES},
    "parameters": {
        "record_type": "s", "parameter_key": "s", "model_id": "s", "model_sha256": "s", "definition": "j",
        "parameter_state": "s", "columns": "ls", "coefficients": "j", "coefficients_repr": "j", "scales": "j",
        "scales_repr": "j", "constant_columns": "ls", "convergence": "j", "training": "j", "penalty": "j",
        "trajectory": "j", **_LABEL_TYPES},
    "estimates": {
        "record_type": "s", "estimate_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
        "partition": "s", "model_id": "s", "model_sha256": "s", "orientation": "s", "team_key": "s",
        "team_name": "s", "opponent_key": "s", "opponent_name": "s", "estimate_state": "s", "abstention_reason": "s?",
        "abstention_detail": "ls", "sample_state": "s", "probability": "d?", "probability_exact": "q?",
        "opponent_probability": "d?", "opponent_probability_exact": "q?", "game_grain_probability_a_exact": "q?",
        "linear_predictor": "d?", "linear_predictor_repr": "s?", "probability_repr": "s?",
        "feature_record_sha256": "s", "game_feature_record_sha256": "s", **_LABEL_TYPES},
    "scores": {
        "record_type": "s", "score_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
        "partition": "s", "model_id": "s", "model_sha256": "s", "score_source": "s", "metric_kind": "s",
        "orientation": "s", "a_key": "s", "b_key": "s", "a_team_name": "s", "b_team_name": "s",
        "support_state": "s", "sample_state": "s", "estimate_state": "s", "label_state": "s", "y_a": "i?",
        "score_state": "s", "unscored_reason": "s?", "probability_a": "d?", "probability_a_exact": "q?",
        "brier": "q?", "brier_decimal": "d?", "log_loss": "s?", "log_loss_convention": "s",
        "estimate_record_sha256": "s", "label_record_sha256": "s", **_LABEL_TYPES},
    "witnesses": {
        "record_type": "s", "score_key": "s", "contest_key": "s", "season": "i", "contest_date": "s",
        "partition": "s", "model_id": "s", "model_sha256": "s", "score_source": "s", "metric_kind": "s",
        "a_key": "s", "b_key": "s", "support_state": "s", "parent_score_state": "s", "parent_score": "j",
        "parent_score_line_sha256": "s", "parent_release_identity": "s", **_LABEL_TYPES},
    "summary": {
        "record_type": "s", "summary_key": "s", "scope_kind": "s", "scope_id": "s", "seasons": "j",
        "model_id": "s", "model_sha256": "s", "metric_kind": "s", "score_source": "s", "summary_kind": "s",
        "window_targets": "i", "eligible_games": "i", "excluded_games": "i", "parent_original_scored_games": "i?",
        "score_records": "i", "scored_games": "i", "unscored_games": "i", "unscored_by_reason": "j",
        "brier_total": "q?", "brier_total_decimal": "d?", "brier_mean": "q?", "brier_mean_decimal": "d?",
        "log_loss_total": "s?", "log_loss_mean": "s?", "log_loss_convention": "s?", "absolute_error_total": "q?",
        "squared_error_total": "q?", "mae": "q?", "mae_decimal": "d?", "mse": "q?", "mse_decimal": "d?",
        "rmse": "s?", "rmse_decimal": "d?", "delta_state": "s", "delta_baseline_model_id": "s?",
        "delta_scored_games": "i?", "brier_mean_difference": "q?", "brier_mean_difference_decimal": "d?",
        "log_loss_mean_difference": "s?", "direction": "s?", "primary": "b", "reading": "s", **_LABEL_TYPES},
    "census": {"record_type": "s", "census_key": "s", "population": "j", **_LABEL_TYPES},
}
RECORD_TYPES = {"qualifications": "CONTEXT_QUALIFICATION", "features": "CONTEXT_FEATURE",
                "parameters": "CONTEXT_PARAMETER", "estimates": "CONTEXT_ESTIMATE", "scores": "CONTEXT_SCORE",
                "witnesses": "CONTEXT_PARENT_SCORE_WITNESS", "summary": "CONTEXT_SUMMARY", "census": "CONTEXT_CENSUS"}
RECORD_TABLES = ("qualifications", "features", "parameters", "estimates", "scores", "witnesses", "summary", "census")
SEASONAL_TABLES = ("qualifications", "features", "estimates", "scores", "witnesses")
KEY_FIELDS = {"qualifications": "qualification_key", "features": "feature_key", "parameters": "parameter_key",
              "estimates": "estimate_key", "scores": "score_key", "witnesses": "score_key", "summary": "summary_key",
              "census": "census_key"}
SCORE_SOURCES = {"scores": "NEW_FROZEN_CONTEXT_FIT", "witnesses": "UNCHANGED_C56_PARENT_GAME_SCORE"}
ORDERING = {
    "qualifications": "season, contest_date, contest_key",
    "features": "season, contest_date, contest_key, view (A then B)",
    "parameters": "model (CTX-HISTORY-LOGIT-V1, CTX-SITE-CALENDAR-LOGIT-V1)",
    "estimates": "season, contest_date, contest_key, model (the two new models), orientation (A then B)",
    "scores": "season, contest_date, contest_key, model (the two new models)",
    "witnesses": "season, contest_date, contest_key, model (the five parent models in registry order)",
    "summary": "window (SEASON 2016..2023, PARTITION FIT, PARTITION COMPARISON), model (registry order)",
    "census": "one record",
}
LAYOUT = {
    "grains": {"qualifications": "one record per accepted 2016-2023 target (<contest_key>), all 5,875",
               "features": "one record per target view (<contest_key>|<view>), all 11,750",
               "parameters": "one record per new model (<model>), 2",
               "estimates": "one record per target, new model and orientation (<contest_key>|<model>|<orientation>)",
               "scores": "one A-oriented new score per target and new model (<contest_key>|<model>)",
               "witnesses": "one unchanged C56 parent game-score witness per target and parent model "
                            "(<contest_key>|<model>)",
               "summary": "one row per window and model (<scope_kind>:<scope_id>|<model>), 70",
               "census": "one record (census)"},
    "ordering": ORDERING,
    "serialization": "canonical JSON lines (sorted keys, separators ',' ':', UTF-8, no ASCII escaping); one zlib "
                     "level-9 block per seasonal table and season, one GLOBAL block each for parameters, summary and "
                     "census",
    "database": {"ddl": [["table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"],
                         ["table", "blocks", "CREATE TABLE blocks (ord INTEGER PRIMARY KEY, record_table TEXT NOT NULL, "
                                             "segment TEXT NOT NULL, records INTEGER NOT NULL, first_key TEXT, "
                                             "last_key TEXT, lines_sha256 TEXT NOT NULL, block BLOB NOT NULL)"]],
                 "block_layout": [*[[t, str(s)] for t in SEASONAL_TABLES for s in STUDY_SEASONS],
                                  ["parameters", "GLOBAL"], ["summary", "GLOBAL"], ["census", "GLOBAL"]],
                 "page_size": 4096, "journal_mode": "OFF", "file": DB_FILE},
    "identity_documents": {
        "content": ["schema", "stage", "population", "contract_id", "contract_sha256", "inputs", "parent_contracts",
                    "rules_sha256", "payload_schema", "row_counts", "lines_sha256", "blocks"],
        "database": ["schema", "stage", "population", "contract_sha256", "content_identity", "db_schema_version",
                     "outputs", "table_counts"],
        "identity": "SHA-256 of the canonical JSON bytes of the document; compared as canonical bytes, never by Python "
                    "equality (an integral float, a boolean or an extra member differs)",
        "location": "<root>/canonical/national_site_calendar_association_2016_2023/sha256/<database identity>/"
                    "national_site_calendar_association.sqlite; manifest at <root>/manifests/"
                    "national_site_calendar_association_2016_2023/sha256/<database identity>/run_manifest.json with "
                    "members identity, identity_document, content_identity, content_document and provenance; "
                    "create-only (identical rebuild ALREADY_PRESENT_IDENTICAL, differing bytes "
                    "REFUSED_IMMUTABLE_COLLISION)"},
    "checkpoint_unit": "a run of consecutive canonical targets (--chunk-size targets): their qualification, feature, "
                       "estimate, score and witness lines; parameters, summary and census follow",
}
GRAINS = {"context-qualification": ("qualifications",), "context-feature": ("features",),
          "context-parameter": ("parameters",), "context-estimate": ("estimates",),
          "context-score": ("scores", "witnesses"), "context-summary": ("summary",)}
GAME_SELECTORS = ("season", "partition", "team", "contest")
#: TP63 section 12 (C63-SUMMARY-SELECTOR-03): the complete applicability matrix; an inapplicable supplied selector is
#: refused (SELECTOR_NOT_APPLICABLE) before any input access, never ignored.
SELECTOR_MATRIX = {
    "context-qualification": {"game_selectors": True, "models": []},
    "context-feature": {"game_selectors": True, "models": []},
    "context-parameter": {"game_selectors": False, "models": list(NEW_MODELS)},
    "context-estimate": {"game_selectors": True, "models": list(NEW_MODELS)},
    "context-score": {"game_selectors": True, "models": list(MODEL_IDS)},
    "context-summary": {"game_selectors": True, "models": list(MODEL_IDS)},
}
SELECTORS = {
    "season": "four ASCII digits; the study seasons are 2016-2023 (a well-formed other season selects no game and "
              "serves no row with SEASON_OUTSIDE_RELEASE)",
    "partition": "FIT (2016-2022) or COMPARISON (2023); with --season a compatible pair restricts to that season and an "
                 "incompatible pair selects no game",
    "team": "org:<1-12 digits> or bare digits (the accepted team key), or an exact team name the record's own season "
            "carries for that team (never borrowed across seasons); a well-formed unknown team selects no game",
    "contest": "an accepted contest key ncaa:<digits> (bare digits read as ncaa:<digits>); a well-formed unknown "
               "contest selects no game",
    "model": "one of the seven registered model IDs (closed namespace); applicability per grain follows the matrix",
    "paging": "--limit (default 50, non-negative integer) and --offset (default 0, non-negative integer), or --all; "
              "--all with an explicit --limit or --offset is PAGING_CONFLICT; exact totals in record order; filters "
              "and summary re-derivation precede paging",
    "intersection": "every applicable supplied selector applies and they intersect over canonical games; an unknown or "
                    "disjoint valid selection serves no row, summaries included (rows = [], never a fabricated "
                    "zero-count summary)",
    "explicit_empty": "an explicitly supplied empty value is never treated as absent: an empty model is MODEL_INVALID, "
                      "an empty season, partition, team or contest INVALID_SELECTOR, an empty limit or offset "
                      "LIMIT_INVALID or OFFSET_INVALID, an empty manifest a location refusal",
    "pit": "--require-pit is always refused; --cutoff and --as-of are TEMPORAL_FLAG_UNSUPPORTED; no historical as-of "
           "selector exists",
    "matrix": SELECTOR_MATRIX,
}
#: The frozen parser and refusal precedence of the explicit mode (TP63 sections 6 and 12).
PRECEDENCE = [
    "1 argument syntax (unknown option, missing value, missing --grain): ARGUMENT_INVALID",
    "2 --require-pit: CONTEXT_PIT_NOT_ADMITTED",
    "3 another mode's option: CONTEXT_MODE_CONFLICT",
    "4 --cutoff / --as-of: TEMPORAL_FLAG_UNSUPPORTED; --event / --orientation / --slice: SELECTOR_NOT_APPLICABLE",
    "5 grain: UNKNOWN_GRAIN",
    "6 paging: LIMIT_INVALID, OFFSET_INVALID, NEGATIVE_LIMIT, NEGATIVE_OFFSET, PAGING_CONFLICT",
    "7 model value: MODEL_INVALID",
    "8 game selector values in the order season, partition, team, contest: INVALID_SELECTOR",
    "9 applicability in the order season, partition, team, contest, model: SELECTOR_NOT_APPLICABLE",
    "10 --expect-identity: STALE_CONTEXT_IDENTITY when not a SHA-256 identity",
    "11 then (and only then) the database and manifest location policy and the complete release verification",
]
SCOPE = {
    "population": "all 5,875 accepted C39/C56 2016-2023 targets (11,750 oriented views); the common cohort is the "
                  "frozen complete-case support of the source qualification",
    "fit_and_comparison": "FIT 2016-2022 (fitted-data summaries), COMPARISON 2023 (already exposed, not blind)",
    "parent_reads": "read-only whole-file hashing of the accepted parents includes their 2024/2025 bytes; no "
                    "2024/2025 target, feature, label, design, fit, score or evaluation is selected or derived",
    "not_in_scope": "2024/2025 protected seasons, prospective or production training, forecasts, PIT admission, "
                    "calibration, actual venues, travel, rest, weather, personnel, markets, film and A&M "
                    "specialization",
}
TABLE_LABELS = {"qualifications": "QUALIFICATION", "features": "FEATURE", "parameters": "PARAMETER",
                "estimates": "ESTIMATE", "scores": "SCORE", "witnesses": "WITNESS", "summary": "SUMMARY",
                "census": "CENSUS"}
#: TP63 section 6 error semantics: every refusal is exit 2 with one JSON line {"refused": CODE, "error": text} on
#: stderr and no row; checks run in a fixed order so each forgery is refused for its own cause.
REFUSALS = {
    "exit_code": 2,
    "stderr": "one JSON object with members refused (the code) and error (the text); nothing on stdout",
    "selection": ["ARGUMENT_INVALID", "CONTEXT_PIT_NOT_ADMITTED", "CONTEXT_MODE_CONFLICT", "TEMPORAL_FLAG_UNSUPPORTED",
                  "UNKNOWN_GRAIN", "LIMIT_INVALID", "OFFSET_INVALID", "NEGATIVE_LIMIT", "NEGATIVE_OFFSET",
                  "PAGING_CONFLICT", "MODEL_INVALID", "INVALID_SELECTOR", "SELECTOR_NOT_APPLICABLE",
                  "STALE_CONTEXT_IDENTITY"],
    "location": ["DATABASE_LOCATION_UNSUPPORTED", "DATABASE_LOCATION_NOT_LITERAL",
                 "CONTEXT_MANIFEST_LOCATION_UNSUPPORTED", "CONTEXT_MANIFEST_LOCATION_NOT_LITERAL",
                 "CONTEXT_DATABASE_MISSING", "CONTEXT_LOCATION_INVALID", "CONTEXT_MANIFEST_MISSING",
                 "CONTEXT_DATABASE_UNREADABLE"],
    "manifest_and_identity": ["CONTEXT_MANIFEST_MALFORMED", "CONTEXT_IDENTITY_MISMATCH", "CONTEXT_SCHEMA_UNSUPPORTED",
                              "CONTEXT_IDENTITY_DOCUMENT_MISMATCH", "CONTEXT_DATABASE_TAMPERED",
                              "CONTEXT_CONTRACT_MISMATCH", "CONTEXT_CONTENT_IDENTITY_MISMATCH",
                              "CONTEXT_PROFILE_MISMATCH"],
    "meta": ["CONTEXT_META_MISMATCH", "CONTEXT_META_MALFORMED", "CONTEXT_PIT_CLAIM_INVALID",
             "CONTEXT_LABEL_CLAIM_INVALID", "CONTEXT_PARENT_MISMATCH", "CONTEXT_RULES_CLAIM_INVALID",
             "CONTEXT_COUNT_MISMATCH"],
    "blocks_and_records": ["CONTEXT_INDEX_MISMATCH", "CONTEXT_RECORD_TYPE_INVALID", "CONTEXT_RECORD_MALFORMED",
                           "CONTEXT_RECORD_SHAPE_INVALID", "CONTEXT_FIELD_TYPE_INVALID", "CONTEXT_RECORD_NOT_CANONICAL"],
    "collections": ["CONTEXT_DUPLICATE_ROW", "CONTEXT_ORDER_MISMATCH",
                    *[f"CONTEXT_{label}_{kind}" for label in TABLE_LABELS.values()
                      for kind in ("ROW_MISSING", "ROW_EXTRA", "KEYS_MISMATCH")]],
    "rules": ["CONTEXT_KEY_MISMATCH", "CONTEXT_SEASON_OUT_OF_RANGE", "CONTEXT_PARTITION_MISMATCH",
              "CONTEXT_COUNT_OUT_OF_DOMAIN", "CONTEXT_BINDING_INVALID", "CONTEXT_PROVIDER_CLAIM_INVALID",
              "CONTEXT_SITE_MISMATCH", "CONTEXT_DATE_STATE_INVALID", "CONTEXT_SOURCE_CLOCK_INVALID",
              "CONTEXT_HISTORY_INCOHERENT", "CONTEXT_HISTORY_LEAKAGE", "CONTEXT_LOG_ODDS_MISMATCH",
              "CONTEXT_CALENDAR_INVALID", "CONTEXT_MISSING_AS_ZERO", "CONTEXT_SUPPORT_MISMATCH",
              "CONTEXT_COMMON_COHORT_DRIFT", "CONTEXT_FEATURE_MISMATCH", "CONTEXT_ORIENTATION_MISMATCH",
              "CONTEXT_DESIGN_MISMATCH", "CONTEXT_LABEL_INCONSISTENT", "CONTEXT_PARAMETER_MISMATCH",
              "CONTEXT_COMPLEMENT_INVALID", "CONTEXT_ESTIMATE_MISMATCH", "CONTEXT_SCORE_MISMATCH",
              "CONTEXT_WITNESS_MISMATCH", "CONTEXT_PARENT_WITNESS_DRIFT", "CONTEXT_SUMMARY_MISMATCH",
              "CONTEXT_CENSUS_MISMATCH", "CONTEXT_COMMON_SUPPORT_INVALID"],
    "malformed_json_reasons": ["JSON_LONE_SURROGATE", "JSON_NESTING_TOO_DEEP", "JSON_NONFINITE_NUMBER",
                               "JSON_INTEGER_TOO_LONG"],
    "build_inputs": ["CONTEXT_DATA_ROOT_MISSING", "CONTEXT_DATA_ROOT_LOCATION_UNSUPPORTED",
                     "CONTEXT_DATA_ROOT_LOCATION_NOT_LITERAL", "CONTEXT_INPUT_LOCATION_UNSUPPORTED",
                     "CONTEXT_INPUT_LOCATION_NOT_LITERAL", "CONTEXT_INPUT_MISSING", "CONTEXT_INPUT_TAMPERED",
                     "CONTEXT_INPUT_MALFORMED", "CONTEXT_PARENT_IDENTITY_MISMATCH", "CONTEXT_INPUT_POPULATION_DRIFT",
                     "CONTEXT_INPUT_INVALID"],
}


class ContextError(ValueError):
    """A refused build input, selection or release; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise ContextError(code, message)


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


def _nesting_refusal(code: str, where: str) -> ContextError:
    return ContextError(code, f"{where}: {JSON_NESTING_TOO_DEEP} (deeper than the JSON decoder or encoder accepts)")


def loads_untrusted(text: Any, code: str, where: str, non_json_code: str | None = None) -> Any:
    """Decode JSON from the release: NaN, Infinity, a float literal beyond binary64 range and an integer beyond the
    interpreter's digit limit are malformed data refused with ``code`` and their reason (never a traceback); nesting
    beyond the decoder's depth is refused; other syntax errors are refused with ``non_json_code`` (default ``code``)."""
    try:
        return json.loads(text, parse_float=_finite_float, parse_constant=_no_constant)
    except _InvalidNumber as exc:
        raise ContextError(code, f"{where}: {JSON_NONFINITE_NUMBER} ({exc})") from exc
    except RecursionError as exc:
        raise _nesting_refusal(code, where) from exc
    except ValueError as exc:
        if "integer string conversion" in str(exc) or "Exceeds the limit" in str(exc):
            raise ContextError(code, f"{where}: {JSON_INTEGER_TOO_LONG}") from exc
        raise ContextError(non_json_code or code, f"{where}: not JSON ({exc})") from exc


def _untrusted_canonical(value: Any, code: str, where: str) -> bytes:
    try:
        return canonical_json_bytes(value)
    except UnicodeEncodeError as exc:
        raise ContextError(code, f"{where}: {JSON_LONE_SURROGATE} (U+{ord(exc.object[exc.start]):04X} is not "
                                 "Unicode text)") from exc
    except RecursionError as exc:
        raise _nesting_refusal(code, where) from exc
    except ValueError as exc:  # a non-finite float can only come from untrusted text the decoder already refused
        raise ContextError(code, f"{where}: {JSON_NONFINITE_NUMBER} ({exc})") from exc


def _json_or_none(text: Any, name: str = "") -> Any:
    if not isinstance(text, (str, bytes)):
        return None
    try:
        return loads_untrusted(text, "CONTEXT_META_MALFORMED", f"meta {name}", non_json_code="NOT_JSON")
    except ContextError as exc:
        if exc.code == "NOT_JSON":
            return None
        raise


# --------------------------------------------------------------------------------------------- numeric helpers

_QUANTUM = Decimal("0.000000000001")


def dec12(value: float) -> str:
    """A binary64 value's exact decimal expansion rounded half-even to 12 places (negative zero normalized)."""
    if type(value) is not float or not math.isfinite(value):
        _refuse("CONTEXT_DESIGN_MISMATCH", f"{value!r} is not a finite binary64 value")
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


def negate(value: float) -> float:
    """The exact binary64 negation with negative zero normalized to zero."""
    return -value + 0.0


def history_log_odds(wins: int, losses: int, ties: int) -> float:
    """ell = log(2W + T + 2) - log(2L + T + 2): the smoothed C47 strength's logit in the pinned operation order."""
    return math.log(2 * wins + ties + 2) - math.log(2 * losses + ties + 2)


def log_loss_value(p_a: Fraction, y: int) -> float:
    q = p_a if y == 1 else 1 - p_a
    clipped = min(max(float(q), LOG_CLIP), 1.0 - LOG_CLIP)
    return -math.log(clipped)


def model_sha256(model_id: str) -> str:
    if model_id in PARENT_MODEL_SHA256:
        return PARENT_MODEL_SHA256[model_id]
    return sha256_bytes(canonical_json_bytes(MODELS[model_id]))


def metric_kind(model_id: str) -> str:
    return "MARGIN" if model_id in MARGIN_MODELS else "PROBABILITY"


def partition_of(season: int) -> str:
    return "FIT" if season in FIT_SEASONS else "COMPARISON"


def keys_sha256(keys: Iterable[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


def lines_sha256(lines: list[str]) -> str:
    return sha256_bytes("".join(line + "\n" for line in lines).encode("utf-8"))


def rules_document() -> dict[str, Any]:
    """Every frozen rule the contract restates (the meta ``rules`` claim and the content document's rules digest), as a
    fresh deep copy so no caller can alias and alter the module's frozen constants."""
    return copy.deepcopy({
        "labels": LABELS, "record_labels": list(RECORD_LABEL_KEYS),
        "seasons": {"study": list(STUDY_SEASONS), "fit": list(FIT_SEASONS), "comparison": list(COMPARISON_SEASONS)},
        "models": MODELS, "model_ids": list(MODEL_IDS), "new_models": list(NEW_MODELS),
        "parent_models": list(PARENT_MODELS), "model_sha256": {m: model_sha256(m) for m in MODEL_IDS},
        "parent_comparators": PARENT_COMPARATORS, "columns": {m: list(c) for m, c in COLUMNS.items()},
        "binding": BINDING, "provider_join": PROVIDER_JOIN, "date_window": DATE_WINDOW, "calendar": CALENDAR,
        "calendar_states": list(CALENDAR_STATES), "site": SITE_RULE, "support": SUPPORT, "design": DESIGN,
        "scaling": SCALING, "fit": FIT_RULE, "estimates": ESTIMATE_RULE, "scores": SCORE_RULE, "summary": SUMMARY_RULE,
        "numeric": NUMERIC_CONTRACT, "support_states": list(SUPPORT_STATES), "binding_states": list(BINDING_STATES),
        "provider_states": list(PROVIDER_STATES), "site_agreements": list(SITE_AGREEMENTS),
        "date_states": list(DATE_STATES), "label_states": list(LABEL_STATES),
        "count_bounds": {"history": HISTORY_BOUND, "interval_days": INTERVAL_BOUND}, "log_clip": repr(LOG_CLIP),
        "clip_convention": CLIP_CONVENTION, "layout": LAYOUT, "field_types": FIELD_TYPES, "subspecs": SUBSPECS,
        "record_types": RECORD_TYPES, "score_sources": SCORE_SOURCES, "grains": {g: list(t) for g, t in GRAINS.items()},
        "selectors": SELECTORS, "precedence": PRECEDENCE, "refusals": REFUSALS, "scope": SCOPE})


def rules_sha256() -> str:
    return sha256_bytes(canonical_json_bytes(rules_document()))


# --------------------------------------------------------------------------------------------- shared qualification rules
# Pure functions of recorded values: the builder applies them to the raw inputs and the reader re-applies them to the
# stored records.

def parse_start(text: Any) -> Any:
    """The explicit UTC instant of a provider start claim, or None when the claim is not in the declared pattern."""
    import datetime as _dt  # noqa: PLC0415 - small helper

    if not isinstance(text, str) or not START_RE.match(text):
        return None
    try:
        return _dt.datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError:
        return None


def valid_date(text: Any) -> bool:
    import datetime as _dt  # noqa: PLC0415 - small helper

    if not isinstance(text, str) or not DATE_RE.match(text):
        return False
    try:
        return _dt.date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


def day_difference(later: str, earlier: str) -> int:
    import datetime as _dt  # noqa: PLC0415 - small helper

    return (_dt.date.fromisoformat(later) - _dt.date.fromisoformat(earlier)).days


def date_state(start: Any, contest_date: str) -> tuple[str, str | None, int | None]:
    """(state, reason, UTC date minus calendar date in days) under the declared calendar-date compatibility window."""
    import datetime as _dt  # noqa: PLC0415 - small helper

    instant = parse_start(start)
    if instant is None:
        return "UNSUPPORTED", "PROVIDER_START_MALFORMED", None
    day = _dt.date.fromisoformat(contest_date)
    base = _dt.datetime(day.year, day.month, day.day, tzinfo=_dt.timezone.utc)
    lower = base + _dt.timedelta(hours=DATE_WINDOW["lower_offset_hours"])
    upper = base + _dt.timedelta(hours=DATE_WINDOW["upper_offset_hours"])
    offset = (instant.date() - day).days
    if lower <= instant < upper:
        return "COMPATIBLE_WITH_PARENT_LOCAL_DATE", None, offset
    return "INCOMPATIBLE_WITH_PARENT_LOCAL_DATE", "PROVIDER_START_OUTSIDE_PARENT_DATE_WINDOW", offset


def site_claim(neutral: bool, home_side: str) -> str:
    return "NEUTRAL" if neutral else f"HOME_{home_side}"


def site_agreement(parent_site: str, claim: str | None) -> str:
    if claim is None or parent_site not in PARENT_SITES:
        return "UNSUPPORTED"
    return "AGREE" if claim == parent_site else "DISAGREE"


def site_code(agreed_site: str | None, view: str) -> int | None:
    """+1 when the view's team is the agreed designated home, -1 when its opponent is, 0 at an agreed neutral site."""
    if agreed_site is None:
        return None
    if agreed_site == "NEUTRAL":
        return 0
    return 1 if agreed_site == f"HOME_{view}" else -1


def calendar_block(contributing: list[tuple[str, str]], excluded_dates: list[str], target_date: str,
                   lineage_reason: str | None) -> dict[str, Any]:
    """A side's calendar input from its eligible prior pool ((contest key, date) pairs), its excluded earlier inputs'
    dates and the lineage verdict (None when every eligible prior joins its own parent contest)."""
    eligible, excluded = len(contributing), len(excluded_dates)
    base = {"latest_prior_date": None, "latest_prior_contest_keys": [], "interval_days": None,
            "intervening_calendar_days": None, "eligible_prior_count": eligible, "excluded_prior_count": excluded,
            "excluded_prior_after_latest_eligible": 0,
            "lineage_state": lineage_reason or "EVERY_ELIGIBLE_PRIOR_JOINS_ITS_PARENT_CONTEST"}
    if lineage_reason is not None:
        return {**base, "state": "PRIOR_LINEAGE_INVALID"}
    if not contributing:
        return {**base, "state": "NO_ELIGIBLE_SAME_SEASON_PRIOR"}
    latest = max(date for _key, date in contributing)
    keys = sorted(key for key, date in contributing if date == latest)
    after = sum(1 for date in excluded_dates if latest < date < target_date)
    base.update(latest_prior_date=latest, latest_prior_contest_keys=keys, excluded_prior_after_latest_eligible=after)
    if len(keys) > 1:
        return {**base, "state": "AMBIGUOUS_LATEST_PRIOR"}
    interval = day_difference(target_date, latest)
    return {**base, "state": "QUALIFIED_CALENDAR_INTERVAL", "interval_days": interval,
            "intervening_calendar_days": interval - 1}


def support_decision(q: dict[str, Any]) -> tuple[str, list[str], str]:
    """(support state, reasons in the fixed order, A/B calendar pattern) of one qualification record."""
    reasons: list[str] = []
    for side in ("a", "b"):
        binding = q[f"{side}_binding"]
        if binding["state"] != "BOUND":
            reasons.append(f"{side.upper()}_{binding['reason']}")
    reason = q["provider_reason"]
    token = None if reason is None else (reason if reason.startswith("PROVIDER_") else f"PROVIDER_{reason}")
    if q["provider_state"] != "PROVIDER_GAME_JOINED" and reason != "PARTICIPANT_BINDING_UNSUPPORTED":
        reasons.append(token)
    elif q["provider_state"] != "PROVIDER_GAME_JOINED" and not reasons:
        reasons.append(token)
    if q["provider_state"] == "PROVIDER_GAME_JOINED" and q["site_agreement"] != "AGREE":
        reasons.append("SITE_DISAGREES_WITH_PARENT" if q["site_agreement"] == "DISAGREE" else
                       "SITE_PARENT_SITE_UNSUPPORTED")
    if q["provider_state"] == "PROVIDER_GAME_JOINED" and q["date_state"] != "COMPATIBLE_WITH_PARENT_LOCAL_DATE":
        reasons.append(f"DATE_{q['date_reason']}")
    for side in ("a", "b"):
        state = q[f"{side}_calendar"]["state"]
        if state != "QUALIFIED_CALENDAR_INTERVAL":
            reasons.append(f"{side.upper()}_CALENDAR_{state}")
    pattern = f"{q['a_calendar']['state']},{q['b_calendar']['state']}"
    return ("COMMON_SUPPORT" if not reasons else "OUTSIDE_COMMON_SUPPORT"), reasons, pattern


def history_block(games: int, wins: int, losses: int, ties: int, keys: list[str]) -> dict[str, Any]:
    return {"games": games, "wins": wins, "losses": losses, "ties": ties, "cold_start": games == 0,
            "contributing_contest_keys": list(keys), "log_odds": history_log_odds(wins, losses, ties)}


# --------------------------------------------------------------------------------------------- 2. features

def _game_order(record: dict[str, Any]) -> tuple[Any, ...]:
    return (record["season"], record["contest_date"], record["contest_key"])


def feature_records(q: dict[str, Any]) -> list[dict[str, Any]]:
    """Both oriented views of one target, derived from its qualification record alone (view B is A negated)."""
    supported = q["support_state"] == "COMMON_SUPPORT"
    h_a = q["a_history"]["log_odds"] - q["b_history"]["log_odds"]
    s_a = site_code(q["agreed_site"], "A")
    cal_a, cal_b = q["a_calendar"], q["b_calendar"]
    c_a = cal_a["interval_days"] - cal_b["interval_days"] if \
        cal_a["state"] == cal_b["state"] == "QUALIFIED_CALENDAR_INTERVAL" else None
    design_a = [h_a + 0.0, float(s_a) + 0.0, float(c_a) + 0.0] if supported else None
    line_sha = sha256_bytes(canonical_line(q).encode("utf-8"))
    out = []
    for view in VIEWS:
        mine, other = ("a", "b") if view == "A" else ("b", "a")
        design = design_a if view == "A" or design_a is None else [negate(v) for v in design_a]
        out.append({
            "record_type": RECORD_TYPES["features"], "feature_key": f"{q['contest_key']}|{view}",
            "contest_key": q["contest_key"], "season": q["season"], "contest_date": q["contest_date"],
            "partition": q["partition"], "view": view, "team_key": q[f"{mine}_key"], "team_name": q[f"{mine}_team_name"],
            "team_org_id": q[f"{mine}_org_id"], "opponent_key": q[f"{other}_key"],
            "opponent_name": q[f"{other}_team_name"], "opponent_org_id": q[f"{other}_org_id"],
            "team_history": copy.deepcopy(q[f"{mine}_history"]), "opponent_history": copy.deepcopy(q[f"{other}_history"]),
            "team_calendar": copy.deepcopy(q[f"{mine}_calendar"]),
            "opponent_calendar": copy.deepcopy(q[f"{other}_calendar"]),
            "history_log_odds_difference": h_a + 0.0 if view == "A" else negate(h_a),
            "agreed_site": q["agreed_site"], "site_code": None if s_a is None else (s_a if view == "A" else -s_a),
            "calendar_interval_difference_days": None if c_a is None else (c_a if view == "A" else -c_a),
            "support_state": q["support_state"], "abstention_reasons": list(q["support_reasons"]),
            "design_history": None if design is None else design[:1],
            "design_site_calendar": None if design is None else list(design),
            "target_excluded_from_history": q["contest_key"] not in q[f"{mine}_history"]["contributing_contest_keys"]
            and q["contest_key"] not in q[f"{other}_history"]["contributing_contest_keys"],
            "qualification_record_sha256": line_sha, **RECORD_LABELS})
    return out


def derive_features(qualifications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for q in sorted(qualifications, key=_game_order):
        out += feature_records(q)
    return out


# --------------------------------------------------------------------------------------------- 3. fits

def game_pairs(features: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    by_view = {(f["contest_key"], f["view"]): f for f in features}
    keys = sorted({(f["season"], f["contest_date"], f["contest_key"]) for f in features})
    out = []
    for _s, _d, key in keys:
        a, b = by_view.get((key, "A")), by_view.get((key, "B"))
        if a is None or b is None:
            _refuse("CONTEXT_ORIENTATION_MISMATCH", f"{key}: both views are required")
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
    """FIT-only paired RMS of the three-column challenger design (the history-only control uses its first scale)."""
    n = len(cohort)
    names = COLUMNS[MODEL_SITE_CALENDAR]
    scales, constant = [], []
    for j in range(len(names)):
        if n == 0:
            scales.append(1.0)
            constant.append(names[j])
            continue
        terms = []
        for a, _y in cohort:
            x = a["design_site_calendar"][j]
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
    x = feature["design_history"] if model_id == MODEL_HISTORY else feature["design_site_calendar"]
    return tuple(v / s for v, s in zip(x, scales))


def derive_fits(features: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pairs = game_pairs(features)
    cohort, excluded = fit_cohort(pairs, labels)
    scales, constant = column_scales(cohort)
    fits: dict[str, Any] = {"scales": scales, "constant_columns": constant, "cohort_games": len(cohort),
                            "cohort_keys": [a["contest_key"] for a, _y in cohort], "excluded_by_label": excluded,
                            "models": {}}
    for model_id in NEW_MODELS:
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


def parameter_records(fits: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for model_id in NEW_MODELS:
        width = len(COLUMNS[model_id])
        fit = fits["models"][model_id]
        result = fit["result"]
        scales = fits["scales"][:width]
        record = {"record_type": RECORD_TYPES["parameters"], "parameter_key": model_id, "model_id": model_id,
                  "model_sha256": model_sha256(model_id), "definition": MODELS[model_id],
                  "parameter_state": fit["state"], "columns": list(COLUMNS[model_id]),
                  "coefficients": None if result is None else [dec12(b) for b in result.coefficients],
                  "coefficients_repr": None if result is None else [repr(b) for b in result.coefficients],
                  "scales": [dec12(s) for s in scales], "scales_repr": [repr(s) for s in scales],
                  "constant_columns": [c for c in fits["constant_columns"] if c in COLUMNS[model_id]],
                  "convergence": None if result is None else {
                      "state": result.state, "newton_steps": result.iterations,
                      "objective_decimal": dec12(result.objective), "objective_repr": repr(result.objective),
                      "gradient_inf_norm_decimal": dec12(result.gradient_inf_norm),
                      "gradient_inf_norm_repr": repr(result.gradient_inf_norm)},
                  "training": {"seasons": list(FIT_SEASONS), "cohort": FIT_RULE["cohort"],
                               "games": fits["cohort_games"], "oriented_rows": fit["rows"],
                               "row_weight": {"numerator": 1, "denominator": 2},
                               "total_weight_games": fits["cohort_games"],
                               "excluded_by_label_state": fits["excluded_by_label"],
                               "cohort_keys_sha256": keys_sha256(fits["cohort_keys"]),
                               "shared_history_scale": True,
                               "comparison_2023": "never in the fit, the scales or any constant"},
                  "penalty": {"lambda": 1, "applies_to": "every column", "intercept": "NONE"},
                  "trajectory": result.trajectory if result is not None else (fit["error"] or {}).get("trajectory"),
                  **RECORD_LABELS}
        if result is None:
            record["convergence"] = {"state": fit["state"], "failure": fit["error"]["message"]}
        out.append(record)
    return out


# --------------------------------------------------------------------------------------------- 4. estimates

def sample_state(season: int, contest_key: str, cohort: set[str]) -> str:
    if season in COMPARISON_SEASONS:
        return ESTIMATE_RULE["sample_state"]["comparison"]
    if contest_key in cohort:
        return ESTIMATE_RULE["sample_state"]["fit_cohort"]
    return ESTIMATE_RULE["sample_state"]["fit_season_outside_cohort"]


def derive_estimates(features: list[dict[str, Any]], fits: dict[str, Any]) -> list[dict[str, Any]]:
    """Every target, new model and orientation (A then B), the game-grain probability first."""
    out = []
    cohort = set(fits["cohort_keys"])
    lines = {f["feature_key"]: sha256_bytes(canonical_line(f).encode("utf-8")) for f in features}
    for a, b in game_pairs(features):
        key = a["contest_key"]
        supported = a["support_state"] == "COMMON_SUPPORT"
        for model_id in NEW_MODELS:
            fit = fits["models"][model_id]
            failed = fit["result"] is None
            served_a = eta = p_float = None
            if supported and not failed:
                z = scaled_design(a, model_id, fits["scales"][:len(COLUMNS[model_id])])
                eta = rf.linear(z, fit["result"].coefficients)
                p_float = rf.sigmoid(eta)
                served_a = dec12(p_float)
            for orientation, mine in (("A", a), ("B", b)):
                record = {
                    "record_type": RECORD_TYPES["estimates"], "estimate_key": f"{key}|{model_id}|{orientation}",
                    "contest_key": key, "season": mine["season"], "contest_date": mine["contest_date"],
                    "partition": mine["partition"], "model_id": model_id, "model_sha256": model_sha256(model_id),
                    "orientation": orientation, "team_key": mine["team_key"], "team_name": mine["team_name"],
                    "opponent_key": mine["opponent_key"], "opponent_name": mine["opponent_name"],
                    "estimate_state": "ABSTAINED", "abstention_reason": None, "abstention_detail": [],
                    "sample_state": sample_state(mine["season"], key, cohort), "probability": None,
                    "probability_exact": None, "opponent_probability": None, "opponent_probability_exact": None,
                    "game_grain_probability_a_exact": None, "linear_predictor": None, "linear_predictor_repr": None,
                    "probability_repr": None, "feature_record_sha256": lines[mine["feature_key"]],
                    "game_feature_record_sha256": lines[a["feature_key"]], **RECORD_LABELS}
                if served_a is None:
                    record.update(abstention_reason="ABSTAIN_FIT_FAILED" if supported and failed else
                                  "ABSTAIN_OUTSIDE_COMMON_SUPPORT",
                                  abstention_detail=[] if supported else list(a["abstention_reasons"]))
                else:
                    p_a = dec_fraction(served_a)
                    text = served_a if orientation == "A" else dec_complement(served_a)
                    p_mine = p_a if orientation == "A" else 1 - p_a
                    lin = dec12(eta)
                    record.update(estimate_state="SUPPORTED", probability=text,
                                  opponent_probability=dec_complement(text), probability_exact=rational(p_mine),
                                  opponent_probability_exact=rational(1 - p_mine),
                                  game_grain_probability_a_exact=rational(p_a),
                                  linear_predictor=lin if orientation == "A" else dec_negation(lin),
                                  linear_predictor_repr=repr(eta) if orientation == "A" else repr(-eta),
                                  probability_repr=repr(p_float) if orientation == "A" else repr(1.0 - p_float))
                out.append(record)
    return out


# --------------------------------------------------------------------------------------------- 5. scores

def derive_scores(estimates: list[dict[str, Any]], labels: dict[str, dict[str, Any]],
                  support: dict[str, str]) -> list[dict[str, Any]]:
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
                  "score_source": SCORE_SOURCES["scores"], "metric_kind": "PROBABILITY", "orientation": "A",
                  "a_key": e["team_key"], "b_key": b["team_key"], "a_team_name": e["team_name"],
                  "b_team_name": b["team_name"], "support_state": support[e["contest_key"]],
                  "sample_state": e["sample_state"], "estimate_state": e["estimate_state"],
                  "label_state": label["label_state"], "y_a": label["y_a"], "probability_a": e["probability"],
                  "probability_a_exact": e["probability_exact"], "log_loss_convention": CLIP_CONVENTION,
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


def witness_record(parent: dict[str, Any], line: str, q: dict[str, Any], parent_identity: str) -> dict[str, Any]:
    """One unchanged C56 parent game-score witness: the exact accepted record, its line digest and metric kind."""
    return {"record_type": RECORD_TYPES["witnesses"], "score_key": f"{q['contest_key']}|{parent['model_id']}",
            "contest_key": q["contest_key"], "season": q["season"], "contest_date": q["contest_date"],
            "partition": q["partition"], "model_id": parent["model_id"], "model_sha256": parent["model_sha256"],
            "score_source": SCORE_SOURCES["witnesses"], "metric_kind": parent["metric_kind"], "a_key": q["a_key"],
            "b_key": q["b_key"], "support_state": q["support_state"], "parent_score_state": parent["score_state"],
            "parent_score": copy.deepcopy(parent), "parent_score_line_sha256": sha256_bytes(line.encode("utf-8")),
            "parent_release_identity": parent_identity, **RECORD_LABELS}


def _score_order(record: dict[str, Any]) -> tuple[Any, ...]:
    return (*_game_order(record), MODEL_IDS.index(record["model_id"]))


def score_grain(scores: list[dict[str, Any]], witnesses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The context-score grain: new scores and parent witnesses together in (season, date, contest, model) order."""
    return sorted([*scores, *witnesses], key=_score_order)


# --------------------------------------------------------------------------------------------- 6. summary

WINDOWS = tuple([("SEASON", str(s), (s,)) for s in STUDY_SEASONS] +
                [("PARTITION", p, PARTITIONS[p]) for p in PARTITION_IDS])


def _mean(total: Fraction, count: int) -> tuple[dict[str, int] | None, str | None]:
    if not count:
        return None, None
    value = total / count
    return rational(value), decimal_text(value)


def _metrics(model_id: str, records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """Window metrics of one model over its eligible records (new scores or parent witnesses, canonical game order)."""
    unscored: dict[str, int] = {}
    scored = []
    for r in records:
        parent = r.get("parent_score")
        state = parent["score_state"] if parent is not None else r["score_state"]
        if state == "SCORED":
            scored.append(parent if parent is not None else r)
        else:
            reason = (parent if parent is not None else r)["unscored_reason"]
            unscored[str(reason)] = unscored.get(str(reason), 0) + 1
    out: dict[str, Any] = {"score_records": len(records), "scored_games": len(scored),
                           "unscored_games": len(records) - len(scored),
                           "unscored_by_reason": dict(sorted(unscored.items())), "brier_total": None,
                           "brier_total_decimal": None, "brier_mean": None, "brier_mean_decimal": None,
                           "log_loss_total": None, "log_loss_mean": None, "log_loss_convention": None,
                           "absolute_error_total": None, "squared_error_total": None, "mae": None,
                           "mae_decimal": None, "mse": None, "mse_decimal": None, "rmse": None, "rmse_decimal": None}
    if model_id in MARGIN_MODELS:
        absolute = sum((frac(s["absolute_error"]) for s in scored), Fraction(0))
        squared = sum((frac(s["squared_error"]) for s in scored), Fraction(0))
        mae, mae_text = _mean(absolute, len(scored))
        mse, mse_text = _mean(squared, len(scored))
        rmse = math.sqrt(float(frac(mse))) if mse is not None else None
        out.update(absolute_error_total=rational(absolute), squared_error_total=rational(squared), mae=mae,
                   mae_decimal=mae_text, mse=mse, mse_decimal=mse_text,
                   rmse=None if rmse is None else repr(rmse), rmse_decimal=None if rmse is None else dec12(rmse))
    else:
        brier_total = sum((frac(s["brier"]) for s in scored), Fraction(0))
        log_total = math.fsum(float(s["log_loss"]) for s in scored)
        brier_mean, brier_mean_text = _mean(brier_total, len(scored))
        out.update(brier_total=rational(brier_total), brier_total_decimal=decimal_text(brier_total),
                   brier_mean=brier_mean, brier_mean_decimal=brier_mean_text, log_loss_total=repr(log_total),
                   log_loss_mean=repr(log_total / len(scored)) if scored else None,
                   log_loss_convention=CLIP_CONVENTION)
    return out, [s["contest_key"] for s in scored]


def _summary_kind(model_id: str, seasons: tuple[int, ...]) -> str:
    if model_id in PARENT_MODELS:
        return "UNCHANGED_C56_PARENT_PROJECTION_ON_COMMON_COHORT"
    if set(seasons) <= set(FIT_SEASONS):
        return "FITTED_DATA_IN_SAMPLE_SUMMARY"
    return "OUT_OF_FIT_EXPOSED_2023_COMPARISON_SUMMARY"


_READINGS = {
    "CHALLENGER": "descriptive retrospective difference (CTX-SITE-CALENDAR-LOGIT-V1 minus CTX-HISTORY-LOGIT-V1) on the "
                  "identical scored common-support games of this window and selection; negative = lower descriptive "
                  "Brier; no significance, calibration, causal, champion or predictive-skill claim; adverse and null "
                  "results retained",
    "CONTROL": "the frozen history-only control on the common-support games of this window and selection; no delta is "
               "claimed for it",
    "PARENT": "an unchanged accepted C56 game-score comparator projected on the common-support games of this window "
              "and selection (its original fit used 5,087 games: a contextual benchmark, not the matched ablation); no "
              "delta is claimed",
}


def summary_rows(qualifications: list[dict[str, Any]], scores: list[dict[str, Any]],
                 witnesses: list[dict[str, Any]], fit_states: dict[str, str],
                 selected: set[str] | None = None) -> list[dict[str, Any]]:
    """The summary rows over the canonical games (``selected`` None: every window, 70 rows) or over exactly the
    selected canonical games (only windows holding a selected eligible game)."""
    games = sorted(qualifications, key=_game_order)
    records: dict[str, dict[str, dict[str, Any]]] = {m: {} for m in MODEL_IDS}
    for r in [*scores, *witnesses]:
        records[r["model_id"]][r["contest_key"]] = r
    failed = {m for m in NEW_MODELS if fit_states.get(m) != "CONVERGED"}
    rows = []
    for kind, scope_id, seasons in WINDOWS:
        window = [q for q in games if q["season"] in seasons and (selected is None or q["contest_key"] in selected)]
        eligible = [q["contest_key"] for q in window if q["support_state"] == "COMMON_SUPPORT"]
        if selected is not None and not eligible:
            continue
        computed: dict[str, tuple[dict[str, Any], list[str]]] = {}
        for model_id in MODEL_IDS:
            computed[model_id] = _metrics(model_id, [records[model_id][k] for k in eligible])
        keysets = {m: computed[m][1] for m in PROBABILITY_MODELS if m not in failed}
        if len({tuple(v) for v in keysets.values()}) > 1:
            _refuse("CONTEXT_COMMON_SUPPORT_INVALID", f"{kind} {scope_id}: the probability models score different "
                                                      "common-cohort games")
        for model_id in MODEL_IDS:
            metrics, keys = computed[model_id]
            row = {"record_type": RECORD_TYPES["summary"], "summary_key": f"{kind}:{scope_id}|{model_id}",
                   "scope_kind": kind, "scope_id": scope_id, "seasons": list(seasons), "model_id": model_id,
                   "model_sha256": model_sha256(model_id), "metric_kind": metric_kind(model_id),
                   "score_source": SCORE_SOURCES["witnesses" if model_id in PARENT_MODELS else "scores"],
                   "summary_kind": _summary_kind(model_id, seasons), "window_targets": len(window),
                   "eligible_games": len(eligible), "excluded_games": len(window) - len(eligible),
                   "parent_original_scored_games": None if model_id in NEW_MODELS else sum(
                       1 for q in window if records[model_id][q["contest_key"]]["parent_score_state"] == "SCORED"),
                   **metrics, "delta_state": "NOT_CLAIMED", "delta_baseline_model_id": None,
                   "delta_scored_games": None, "brier_mean_difference": None, "brier_mean_difference_decimal": None,
                   "log_loss_mean_difference": None, "direction": None,
                   "primary": False, "reading": _READINGS["CONTROL" if model_id == MODEL_HISTORY else
                                                          "PARENT" if model_id in PARENT_MODELS else "CHALLENGER"],
                   **RECORD_LABELS}
            if model_id == MODEL_SITE_CALENDAR:
                control, control_keys = computed[MODEL_HISTORY]
                row.update(delta_baseline_model_id=MODEL_HISTORY,
                           primary=selected is None and (kind, scope_id) == ("PARTITION", "COMPARISON"))
                if failed & set(NEW_MODELS):
                    row.update(delta_state="NULL_FIT_FAILED")
                elif not keys:
                    row.update(delta_state="NULL_NO_SCORED_GAME")
                else:
                    if keys != control_keys:
                        _refuse("CONTEXT_COMMON_SUPPORT_INVALID", f"{kind} {scope_id}: challenger and control score "
                                                                  "different games")
                    diff = frac(metrics["brier_mean"]) - frac(control["brier_mean"])
                    row.update(delta_state="COMPUTED_ON_IDENTICAL_SCORED_GAMES", delta_scored_games=len(keys),
                               brier_mean_difference=rational(diff), brier_mean_difference_decimal=decimal_text(diff),
                               log_loss_mean_difference=repr(float(metrics["log_loss_mean"]) -
                                                             float(control["log_loss_mean"])),
                               direction=("NEGATIVE_LOWER_DESCRIPTIVE_BRIER" if diff < 0 else
                                          "ZERO_EQUAL_DESCRIPTIVE_BRIER" if diff == 0 else
                                          "POSITIVE_HIGHER_DESCRIPTIVE_BRIER"))
            rows.append(row)
    return rows


# --------------------------------------------------------------------------------------------- census

def _count(items: Iterable[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        key = "null" if item is None else str(item)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def census_record(qualifications: list[dict[str, Any]], features: list[dict[str, Any]], fits: dict[str, Any],
                  estimates: list[dict[str, Any]], scores: list[dict[str, Any]],
                  witnesses: list[dict[str, Any]]) -> dict[str, Any]:
    supported = [q for q in qualifications if q["support_state"] == "COMMON_SUPPORT"]
    outside = [q for q in qualifications if q["support_state"] != "COMMON_SUPPORT"]
    calendars = [q[f"{s}_calendar"] for q in qualifications for s in ("a", "b")]
    intervals = [c["interval_days"] for c in calendars if c["interval_days"] is not None]
    differences = [f["calendar_interval_difference_days"] for f in features
                   if f["view"] == "A" and f["support_state"] == "COMMON_SUPPORT"]
    population = {
        "targets": len(qualifications), "views": len(features),
        "targets_by_season": _count(q["season"] for q in qualifications),
        "parent_site": _count(q["parent_site"] for q in qualifications),
        "binding_states": _count(q[f"{s}_binding"]["state"] for q in qualifications for s in ("a", "b")),
        "binding_reasons": _count(q[f"{s}_binding"]["reason"] for q in qualifications for s in ("a", "b")
                                  if q[f"{s}_binding"]["reason"]),
        "provider_states": _count(q["provider_state"] for q in qualifications),
        "provider_reasons": _count(q["provider_reason"] for q in qualifications if q["provider_reason"]),
        "provider_site_claims": _count(q["provider_site_claim"] for q in qualifications),
        "site_agreement": _count(q["site_agreement"] for q in qualifications),
        "agreed_site": _count(q["agreed_site"] for q in qualifications),
        "date_states": _count(q["date_state"] for q in qualifications),
        "provider_utc_date_offset_days": _count(q["provider_utc_date_offset_days"] for q in qualifications),
        "calendar_states_by_view": _count(c["state"] for c in calendars),
        "calendar_interval_days_range": [min(intervals), max(intervals)] if intervals else None,
        "calendar_interval_difference_range_common": [min(differences), max(differences)] if differences else None,
        "excluded_prior_after_latest_eligible_views": sum(1 for c in calendars
                                                          if c["excluded_prior_after_latest_eligible"]),
        "label_states": _count(q["label_state"] for q in qualifications),
        "common_support_games": len(supported), "outside_common_support_games": len(outside),
        "common_support_games_by_season": _count(q["season"] for q in supported),
        "outside_common_support_by_season": _count(q["season"] for q in outside),
        "outside_common_support_patterns": _count(q["support_pattern"] for q in outside),
        "outside_common_support_reasons": _count(r for q in outside for r in q["support_reasons"]),
        "agreed_site_common": _count(q["agreed_site"] for q in supported),
        "fit_cohort_games": fits["cohort_games"], "fit_cohort_keys_sha256": keys_sha256(fits["cohort_keys"]),
        "fit_excluded_by_label": fits["excluded_by_label"], "fit_oriented_rows": 2 * fits["cohort_games"],
        "comparison_common_support_games": sum(1 for q in supported if q["season"] in COMPARISON_SEASONS),
        "fit_states": {m: fits["models"][m]["state"] for m in NEW_MODELS},
        "estimates": len(estimates), "estimate_states": _count(e["estimate_state"] for e in estimates),
        "scores": len(scores), "score_states": _count(s["score_state"] for s in scores),
        "unscored_reasons": _count(s["unscored_reason"] for s in scores if s["unscored_reason"]),
        "witnesses": len(witnesses), "witnesses_by_model": _count(w["model_id"] for w in witnesses),
        "witness_parent_score_states": _count(f"{w['model_id']}|{w['parent_score_state']}" for w in witnesses),
        "score_grain_records": len(scores) + len(witnesses),
    }
    return {"record_type": RECORD_TYPES["census"], "census_key": "census", "population": population, **RECORD_LABELS}


def labels_from_scores(scores: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Each target's accepted label as every new score record states it; the records must agree."""
    labels: dict[str, dict[str, Any]] = {}
    for s in scores:
        entry = {"label_state": s["label_state"], "y_a": s["y_a"], "record_sha256": s["label_record_sha256"]}
        if s["label_state"] == "DECISIVE" and s["y_a"] not in (0, 1):
            _refuse("CONTEXT_LABEL_INCONSISTENT", f"{s['score_key']}: a decisive label needs y_a 0 or 1")
        if s["label_state"] != "DECISIVE" and s["y_a"] is not None:
            _refuse("CONTEXT_LABEL_INCONSISTENT", f"{s['score_key']}: a nondecisive label carries y_a")
        if labels.setdefault(s["contest_key"], entry) != entry:
            _refuse("CONTEXT_LABEL_INCONSISTENT", f"{s['contest_key']}: the models disagree on the label")
    return labels


def derive_from_qualifications(qualifications: list[dict[str, Any]], labels: dict[str, dict[str, Any]],
                               witnesses: list[dict[str, Any]]) -> dict[str, Any]:
    """Every derived grain from the qualification records, the accepted labels and the parent witnesses (the builder
    and the reader run exactly this)."""
    quals = sorted(qualifications, key=_game_order)
    features = derive_features(quals)
    fits = derive_fits(features, labels)
    parameters = parameter_records(fits)
    estimates = derive_estimates(features, fits)
    support = {q["contest_key"]: q["support_state"] for q in quals}
    scores = derive_scores(estimates, labels, support)
    fit_states = {m: fits["models"][m]["state"] for m in NEW_MODELS}
    summary = summary_rows(quals, scores, witnesses, fit_states)
    census = census_record(quals, features, fits, estimates, scores, witnesses)
    return {"qualifications": quals, "features": features, "parameters": parameters, "estimates": estimates,
            "scores": scores, "witnesses": sorted(witnesses, key=_score_order), "summary": summary,
            "census": [census], "fits": fits}


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


def target_chunk(derived: dict[str, Any], keys: Iterable[str]) -> bytes:
    """The checkpoint unit: every seasonal record line of the given targets, block by block (deterministic)."""
    wanted = set(keys)
    out = []
    for table, segment, records, lines in block_lines(derived):
        if segment == "GLOBAL":
            continue
        out += [f"{table}\t{segment}\t{line}" for record, line in zip(records, lines)
                if record["contest_key"] in wanted]
    return ("\n".join(out) + "\n").encode("utf-8")


def row_counts(derived: dict[str, Any]) -> dict[str, int]:
    return {table: len(derived[table]) for table in RECORD_TABLES}


def inputs_claim(anchors: dict[str, Any]) -> dict[str, Any]:
    return {"inputs": anchors["inputs"], "expected": anchors["expected"]}


def content_document(anchors: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
    lines = record_lines(derived)
    return {"schema": CONTENT_SCHEMA, "stage": CONTENT_STAGE, "population": POPULATION,
            "contract_id": anchors["contract_id"], "contract_sha256": anchors["contract_sha256"],
            "inputs": inputs_claim(anchors), "parent_contracts": anchors["parent_contracts"],
            "rules_sha256": rules_sha256(), "payload_schema": PAYLOAD_SCHEMA, "row_counts": row_counts(derived),
            "lines_sha256": {table: lines_sha256(lines[table]) for table in RECORD_TABLES},
            "blocks": [[table, segment, len(block), lines_sha256(block)]
                       for table, segment, _records, block in block_lines(derived)]}


def database_document(contract_sha256: str, content_identity: str, database_sha256: str,
                      table_counts: dict[str, int]) -> dict[str, Any]:
    return {"schema": DATABASE_SCHEMA, "stage": DATABASE_STAGE, "population": POPULATION,
            "contract_sha256": contract_sha256, "content_identity": content_identity, "db_schema_version": DB_SCHEMA,
            "outputs": {DB_FILE: database_sha256}, "table_counts": dict(table_counts)}


def meta_values(anchors: dict[str, Any], content_identity: str, derived: dict[str, Any]) -> dict[str, str]:
    return {"schema_version": DB_SCHEMA, "contract_id": anchors["contract_id"],
            "contract_sha256": anchors["contract_sha256"], "content_identity": content_identity,
            "inputs": canonical_line(inputs_claim(anchors)),
            "parent_contracts": canonical_line(anchors["parent_contracts"]), "labels": canonical_line(LABELS),
            "rules": canonical_line(rules_document()), "row_counts": canonical_line(row_counts(derived)),
            "summary_sha256": lines_sha256(record_lines(derived)["summary"]),
            "census_sha256": lines_sha256(record_lines(derived)["census"])}


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


# --------------------------------------------------------------------------------------------- record types

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
    """The native spelling of an existing local Windows file (the accepted C61 rule, MF61A01-01).

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


# --------------------------------------------------------------------------------------------- selection

_SELECTOR_LIMIT = 200


def _game_selector_values(season: Any, partition: Any, team: Any, contest: Any) -> dict[str, Any]:
    """Validate the supplied game selectors' values in the frozen order (season, partition, team, contest)."""
    out: dict[str, Any] = {}
    if season is not None:
        if is_int(season) and 1000 <= season <= 9999:
            out["season"] = season
        elif isinstance(season, str) and SEASON_SELECTOR_RE.match(season.strip()):
            out["season"] = int(season.strip())
        else:
            _refuse("INVALID_SELECTOR", f"season must be four ASCII digits, got {season!r}")
    if partition is not None:
        if partition not in PARTITION_IDS:
            _refuse("INVALID_SELECTOR", f"partition must be one of {list(PARTITION_IDS)}, got {partition!r}")
        out["partition"] = partition
    if team is not None:
        text = team.strip() if isinstance(team, str) else None
        if not text or len(text) > _SELECTOR_LIMIT or any(ord(c) < 32 or ord(c) == 127 for c in text):
            _refuse("INVALID_SELECTOR", f"team must be org:<digits>, digits or a team name, got {team!r}")
        surrogate = next((c for c in text if 0xD800 <= ord(c) <= 0xDFFF), None)
        if surrogate is not None:
            _refuse("INVALID_SELECTOR", f"team must be Unicode text: U+{ord(surrogate):04X} is a lone surrogate, not a "
                                        "Unicode scalar value")
        match = TEAM_SELECTOR_RE.match(text)
        if text.lower().startswith("org:") and not match:
            _refuse("INVALID_SELECTOR", f"team key must be org:<1-12 digits>, got {team!r}")
        out["team"] = f"org:{int(match.group(1))}" if match else text
    if contest is not None:
        text = contest.strip() if isinstance(contest, str) else None
        match = CONTEST_SELECTOR_RE.match(text) if text else None
        if not match:
            _refuse("INVALID_SELECTOR", f"contest must be an accepted contest key ncaa:<digits>, got {contest!r}")
        out["contest"] = f"ncaa:{match.group(1)}"
    return out


def validate_selection(grain: Any, *, season: Any = None, partition: Any = None, team: Any = None, contest: Any = None,
                       model: Any = None) -> dict[str, Any]:
    """Validate a selection before any file is read, in the frozen precedence: grain, model value, game selector values,
    then applicability (SELECTOR_MATRIX)."""
    if not isinstance(grain, str) or grain not in GRAINS:
        _refuse("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}, got {grain!r}")
    if model is not None and (not isinstance(model, str) or model not in MODEL_IDS):
        _refuse("MODEL_INVALID", f"model must be one of {list(MODEL_IDS)}, got {model!r}")
    out = _game_selector_values(season, partition, team, contest)
    matrix = SELECTOR_MATRIX[grain]
    for name in GAME_SELECTORS:
        if name in out and not matrix["game_selectors"]:
            _refuse("SELECTOR_NOT_APPLICABLE", f"--{name} does not apply to the {grain} grain (fit-global records)")
    if model is not None:
        if model not in matrix["models"]:
            _refuse("SELECTOR_NOT_APPLICABLE", f"--model {model} does not apply to the {grain} grain (applicable: "
                                               f"{matrix['models']})")
        out["model"] = model
    return out


def validate_paging(limit: Any, offset: Any, all_rows: bool, *, limit_given: bool, offset_given: bool
                    ) -> tuple[int | None, int]:
    """Exact bounded paging: integers of at most 12 digits, non-negative, and --all never combined with an explicit
    --limit or --offset."""
    def integer(text: Any, code: str, what: str) -> int:
        if is_int(text):
            return text
        value = str(text).strip() if isinstance(text, str) else None
        body = value[1:] if value and value.startswith("-") else value
        if not body or not body.isascii() or not body.isdigit() or len(body) > 12:
            _refuse(code, f"{what} must be an integer of at most 12 digits, got {text!r}")
        return int(value)

    lim = integer(limit, "LIMIT_INVALID", "limit")
    off = integer(offset, "OFFSET_INVALID", "offset")
    if lim < 0:
        _refuse("NEGATIVE_LIMIT", "limit must be zero or positive")
    if off < 0:
        _refuse("NEGATIVE_OFFSET", "offset must be zero or positive")
    if all_rows and (limit_given or offset_given):
        _refuse("PAGING_CONFLICT", "--all returns every row and cannot be combined with an explicit --limit or --offset")
    return (None if all_rows else lim), off


# --------------------------------------------------------------------------------------------- the reader

class ContextAssociation:
    """A verified, read-only handle on one content-addressed national site/calendar association release.

    Construction refuses (ContextError with a stable code) unless the release location, run manifest, database bytes,
    schema, meta claims, every record's exact members and JSON types, the complete expected collection of every grain,
    every qualification rule the records can re-derive, the frozen common cohort, the features, the parent witness
    bindings, a fresh refit with the unchanged accepted primitive and the complete re-derivation of every parameter,
    estimate, score, summary and census record, the content document, the contract-defined database identity document
    and (when the anchors pin one) the canonical profile verify. Each refusal is checked in a fixed order so that every
    forgery is refused for its own cause."""

    def __init__(self, database: Path, *, manifest: Path | None = None, expect_identity: str | None = None,
                 anchors: dict[str, Any] | None = None) -> None:
        self.anchors = anchors if anchors is not None else {**ANCHORS, "profile": CONTEXT_PROFILE}
        self.binding = self._verify_location_and_manifest(database, manifest, expect_identity)
        document = self.binding["identity_document"]
        if document.get("contract_sha256") != self.anchors["contract_sha256"]:
            _refuse("CONTEXT_CONTRACT_MISMATCH", f"the release names contract {document.get('contract_sha256')}, the "
                                                 f"reader binds {self.anchors['contract_sha256']}")
        try:
            location = readonly_sqlite.literal_path(self.binding["location"])
            self.conn = readonly_sqlite.connect_readonly(_io_path(Path(location)), immutable=False)
        except readonly_sqlite.DatabaseLocationError as exc:
            raise ContextError(exc.code, exc.detail) from exc
        except sqlite3.Error as exc:
            raise ContextError("CONTEXT_DATABASE_UNREADABLE", str(exc)) from exc
        try:
            self._verify_database()
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
            literal = readonly_sqlite.literal_path(database)
        except readonly_sqlite.DatabaseLocationError as exc:
            raise ContextError(exc.code, exc.detail) from exc
        manifest_path = None
        if manifest is not None:
            try:
                manifest_path = Path(readonly_sqlite.literal_path(manifest))
            except readonly_sqlite.DatabaseLocationError as exc:
                suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
                raise ContextError(f"CONTEXT_MANIFEST_LOCATION_{suffix}", f"--manifest {manifest}: "
                                                                          f"{exc.detail}") from exc
        db = Path(database)
        if not _io_path(Path(literal) if os.name == "nt" else db).is_file():
            _refuse("CONTEXT_DATABASE_MISSING", f"no site/calendar association database file at {db}")
        # On Windows the layout and identity are checked on the genuine names of the existing file (an 8.3 or
        # case-equivalent spelling of the same release is that release); every later read uses that one location.
        # POSIX keeps its native, case-sensitive spelling rule.
        absolute = Path(native_location(literal)) if os.name == "nt" else Path(os.path.abspath(db))
        db = absolute
        if absolute.name != DB_FILE or absolute.parent.parent.name != "sha256" or \
                absolute.parent.parent.parent.name != POPULATION:
            _refuse("CONTEXT_LOCATION_INVALID", f"the release must sit at <root>/{POPULATION}/sha256/<id>/{DB_FILE}")
        identity = absolute.parent.name
        if not IDENTITY_RE.match(identity):
            _refuse("CONTEXT_LOCATION_INVALID", f"directory name {identity!r} is not an identity")
        if manifest_path is None:
            manifest_path = manifest_path_for(db)
        if not _io_path(manifest_path).is_file():
            _refuse("CONTEXT_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
        try:
            raw = _io_path(manifest_path).read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ContextError("CONTEXT_MANIFEST_MALFORMED", str(exc)) from exc
        doc = loads_untrusted(raw, "CONTEXT_MANIFEST_MALFORMED", "run manifest")
        if not isinstance(doc, dict):
            _refuse("CONTEXT_MANIFEST_MALFORMED", "the run manifest is not a JSON object")
        if sorted(doc) != sorted(MANIFEST_MEMBERS):
            _refuse("CONTEXT_MANIFEST_MALFORMED", f"run manifest members {sorted(doc)} differ from "
                                                  f"{list(MANIFEST_MEMBERS)}")
        _untrusted_canonical(doc, "CONTEXT_MANIFEST_MALFORMED", "run manifest")
        identity_document = doc["identity_document"]
        computed = sha256_bytes(_untrusted_canonical(identity_document, "CONTEXT_MANIFEST_MALFORMED",
                                                     "run manifest identity document"))
        if computed != identity or doc.get("identity") != identity:
            _refuse("CONTEXT_IDENTITY_MISMATCH", f"manifest identity document hashes to {computed}, directory is "
                                                 f"{identity}, the manifest names {doc.get('identity')!r}")
        if not isinstance(identity_document, dict) or \
                (identity_document.get("stage"), identity_document.get("schema"),
                 identity_document.get("db_schema_version"), identity_document.get("population")) != \
                (DATABASE_STAGE, DATABASE_SCHEMA, DB_SCHEMA, POPULATION):
            _refuse("CONTEXT_SCHEMA_UNSUPPORTED", "not a national site/calendar association database manifest")
        outputs = identity_document.get("outputs")
        if not isinstance(outputs, dict):
            _refuse("CONTEXT_IDENTITY_DOCUMENT_MISMATCH", "the manifest identity document's outputs is not an object")
        actual_sha = sha256_file(_io_path(db))
        if outputs.get(DB_FILE) != actual_sha:
            _refuse("CONTEXT_DATABASE_TAMPERED", f"release bytes hash to {actual_sha}, manifest names "
                                                 f"{outputs.get(DB_FILE)}")
        if expect_identity is not None and expect_identity != identity:
            _refuse("STALE_CONTEXT_IDENTITY", f"expected {expect_identity}, found {identity}")
        return {"identity": identity, "sha256": actual_sha, "location": str(db), "manifest": str(manifest_path),
                "identity_document": identity_document, "content_document": doc["content_document"],
                "content_identity_claim": doc.get("content_identity"), "provenance": doc.get("provenance")}

    # ---- schema, meta claims, records, rules and identities
    def _verify_database(self) -> None:
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
        claims = {name: _json_or_none(meta.get(name), name) for name in ("inputs", "parent_contracts", "labels",
                                                                         "rules")}
        if claims["labels"] != LABELS or _untrusted_canonical(claims["labels"], "CONTEXT_META_MALFORMED",
                                                              "meta labels") != canonical_json_bytes(LABELS):
            labels = claims["labels"] if isinstance(claims["labels"], dict) else {}
            code = "CONTEXT_PIT_CLAIM_INVALID" if labels.get("pit_eligibility") != LABELS["pit_eligibility"] else \
                "CONTEXT_LABEL_CLAIM_INVALID"
            _refuse(code, "the release declares labels other than the contract's")
        if _untrusted_canonical(claims["inputs"], "CONTEXT_META_MALFORMED", "meta inputs") != \
                canonical_json_bytes(inputs_claim(a)):
            _refuse("CONTEXT_PARENT_MISMATCH", "the release was built from other inputs or expectations")
        if _untrusted_canonical(claims["parent_contracts"], "CONTEXT_META_MALFORMED", "meta parent_contracts") != \
                canonical_json_bytes(a["parent_contracts"]):
            _refuse("CONTEXT_PARENT_MISMATCH", "the release names other parent contracts")
        if _untrusted_canonical(claims["rules"], "CONTEXT_META_MALFORMED", "meta rules") != \
                canonical_json_bytes(rules_document()):
            _refuse("CONTEXT_RULES_CLAIM_INVALID", "the release declares other rules")
        counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        # value equality keeps a fractional, string or boolean count here; an integral float count is equal by value
        # and is refused last by the canonical-bytes identity-document rule
        if counts != self.binding["identity_document"].get("table_counts"):
            _refuse("CONTEXT_COUNT_MISMATCH",
                    f"table counts {counts} != {self.binding['identity_document'].get('table_counts')}")
        present = self._read_blocks()
        records = {table: [r for _l, r in present[table]] for table in RECORD_TABLES}
        self._verify_collections(records)
        self._verify_labels(records)
        self._verify_qualifications(records["qualifications"])
        self._verify_features(records)
        self._verify_witnesses(records)
        rebuilt = self._rederive(records)
        derived = {table: records[table] for table in RECORD_TABLES}
        derived["lines"] = {table: [line for line, _r in present[table]] for table in RECORD_TABLES}
        document = content_document(a, derived)
        content_identity = sha256_bytes(canonical_json_bytes(document))
        if _untrusted_canonical(self.binding["content_document"], "CONTEXT_MANIFEST_MALFORMED",
                                "content document") != canonical_json_bytes(document) or \
                self.binding["content_identity_claim"] != content_identity or \
                meta.get("content_identity") != content_identity or \
                self.binding["identity_document"].get("content_identity") != content_identity:
            _refuse("CONTEXT_CONTENT_IDENTITY_MISMATCH", f"the rebuilt content identity is {content_identity}")
        expected_meta = meta_values(a, content_identity, derived)
        if meta != expected_meta:
            _refuse("CONTEXT_META_MISMATCH", "meta differs on " + str(sorted(
                k for k in set(meta) | set(expected_meta) if meta.get(k) != expected_meta.get(k))))
        identity_document = self.binding["identity_document"]
        expected_document = database_document(a["contract_sha256"], content_identity, self.binding["sha256"], counts)
        expected_bytes = canonical_json_bytes(expected_document)
        if _untrusted_canonical(identity_document, "CONTEXT_MANIFEST_MALFORMED", "identity document") != \
                expected_bytes:
            differing = sorted(k for k in set(identity_document) | set(expected_document)
                               if k not in identity_document or k not in expected_document
                               or canonical_json_bytes(identity_document[k]) !=
                               canonical_json_bytes(expected_document[k]))
            _refuse("CONTEXT_IDENTITY_DOCUMENT_MISMATCH", f"the manifest identity document is not the contract-defined "
                                                          f"database document (differs on {differing})")
        database_identity = sha256_bytes(expected_bytes)
        if database_identity != self.binding["identity"]:
            _refuse("CONTEXT_IDENTITY_DOCUMENT_MISMATCH", f"the location names {self.binding['identity']}, the "
                                                          f"contract-defined document is {database_identity}")
        profile = a.get("profile")
        if profile is not None and (profile.get("content_identity"), profile.get("database_identity")) != \
                (content_identity, database_identity):
            _refuse("CONTEXT_PROFILE_MISMATCH", f"the release ({database_identity} / {content_identity}) is not the "
                                                f"pinned canonical profile ({profile.get('database_identity')} / "
                                                f"{profile.get('content_identity')})")
        self.database_identity = database_identity
        self.content_identity = content_identity
        self.meta = meta
        self.records = derived
        self.census = records["census"][0]["population"]
        self.fits = rebuilt
        self.score_grain = score_grain(records["scores"], records["witnesses"])
        self.names = self._name_index(records)

    def _read_blocks(self) -> dict[str, list[tuple[str, dict[str, Any]]]]:
        rows = [tuple(r) for r in self.conn.execute(
            "SELECT ord, record_table, segment, records, first_key, last_key, lines_sha256, block FROM blocks "
            "ORDER BY ord")]
        present: dict[str, list[tuple[str, dict[str, Any]]]] = {t: [] for t in RECORD_TABLES}
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
                record = loads_untrusted(line, "CONTEXT_RECORD_MALFORMED", f"block {ord_} ({table})",
                                         non_json_code="CONTEXT_RECORD_TYPE_INVALID")
                if not isinstance(record, dict):
                    _refuse("CONTEXT_RECORD_TYPE_INVALID", f"block {ord_} holds a non-object line")
                if not isinstance(record.get(KEY_FIELDS[table]), str):
                    _refuse("CONTEXT_RECORD_TYPE_INVALID", f"{table} record: {KEY_FIELDS[table]} is not a string")
                parsed.append((line, record))
            keys = [record_key(table, r) for _l, r in parsed]
            if sha256_bytes(data) != lines_sha or records != len(parsed) or \
                    first_key != (keys[0] if keys else None) or last_key != (keys[-1] if keys else None):
                _refuse("CONTEXT_INDEX_MISMATCH", f"block {ord_} index columns differ from its content")
            for _line, record in parsed:
                if table in SEASONAL_TABLES and str(record.get("season")) != segment:
                    _refuse("CONTEXT_INDEX_MISMATCH", f"block {ord_} ({table} {segment}) holds a record of season "
                                                      f"{record.get('season')!r}")
            layout.append((table, segment))
            present[table] += parsed
        if layout != list(BLOCK_LAYOUT):
            _refuse("CONTEXT_INDEX_MISMATCH", "the blocks do not follow the contract layout")
        for table in RECORD_TABLES:
            types = FIELD_TYPES[table]
            for line, record in present[table]:
                where = f"{table} record {record_key(table, record)}"
                if set(record) != set(types):
                    extra, missing = sorted(set(record) - set(types)), sorted(set(types) - set(record))
                    _refuse("CONTEXT_RECORD_SHAPE_INVALID", f"{where}: extra members {extra[:4]}, missing {missing[:4]}")
                for field, code in types.items():
                    if not _check_type(code, record[field]):
                        _refuse("CONTEXT_FIELD_TYPE_INVALID", f"{where}: {field} is a JSON "
                                                              f"{type(record[field]).__name__} or nested value outside "
                                                              f"the contract type {code}")
                if line != _untrusted_canonical(record, "CONTEXT_RECORD_MALFORMED", where).decode("utf-8"):
                    _refuse("CONTEXT_RECORD_NOT_CANONICAL", f"{where} is not its canonical JSON line")
        return present

    def _verify_collections(self, records: dict[str, list[dict[str, Any]]]) -> None:
        """Complete membership and multiplicity of every grain against the contract's expected collection (derived from
        the pinned target list and the closed model namespace), then the contract order, then the exact key sequence."""
        expected = expected_keys(self.anchors["expected"])
        for table in RECORD_TABLES:
            label = TABLE_LABELS[table]
            keys = [record_key(table, r) for r in records[table]]
            if len(keys) != len(set(keys)):
                _refuse("CONTEXT_DUPLICATE_ROW", f"{table} repeats a record key")
            listed = expected[table]
            missing = sorted(set(listed) - set(keys))
            if missing:
                _refuse(f"CONTEXT_{label}_ROW_MISSING", f"{len(missing)} expected {table} keys absent, e.g. "
                                                        f"{missing[:3]}")
            extra = sorted(set(keys) - set(listed))
            if extra:
                _refuse(f"CONTEXT_{label}_ROW_EXTRA", f"{len(extra)} {table} keys outside the expected collection, e.g. "
                                                      f"{extra[:3]}")
            if keys != listed:
                _refuse("CONTEXT_ORDER_MISMATCH", f"{table} is not in the contract order")
            if keys_sha256(keys) != self.anchors["expected"]["keys_sha256"][table]:
                _refuse(f"CONTEXT_{label}_KEYS_MISMATCH", f"the {table} key sequence differs from the contract's "
                                                          "expected collection")

    @staticmethod
    def _verify_labels(records: dict[str, list[dict[str, Any]]]) -> None:
        for table in RECORD_TABLES:
            want = RECORD_TYPES[table]
            for record in records[table]:
                if record["record_type"] != want:
                    _refuse("CONTEXT_RECORD_TYPE_INVALID", f"{table} record {record_key(table, record)} is a "
                                                           f"{record['record_type']!r}")
                for k in RECORD_LABEL_KEYS:
                    if record[k] != LABELS[k]:
                        _refuse("CONTEXT_PIT_CLAIM_INVALID" if k == "pit_eligibility" else
                                "CONTEXT_LABEL_CLAIM_INVALID", f"{table} record {record_key(table, record)}: {k} is "
                                                               f"{record[k]!r}")

    def _verify_qualifications(self, quals: list[dict[str, Any]]) -> None:
        a = self.anchors
        inputs = a["inputs"]
        excluded = a["expected"]["excluded_games"]
        for q in quals:
            key = q["qualification_key"]
            season = q["season"]
            if season not in STUDY_SEASONS:
                _refuse("CONTEXT_SEASON_OUT_OF_RANGE", f"{key}: season {season}")
            if key != q["contest_key"] or not CONTEST_KEY_RE.match(key) or not valid_date(q["contest_date"]) or \
                    q["contest_date"][:4] not in (str(season), str(season + 1)):
                _refuse("CONTEXT_KEY_MISMATCH", f"{key}: key, season or date is invalid")
            if q["partition"] != partition_of(season):
                _refuse("CONTEXT_PARTITION_MISMATCH", f"{key}: partition {q['partition']}")
            for side in ("a", "b"):
                if not TEAM_KEY_RE.match(q[f"{side}_key"]) or q[f"{side}_key"] != f"org:{q[f'{side}_org_id']}":
                    _refuse("CONTEXT_KEY_MISMATCH", f"{key}: the {side} team key and org id disagree")
            if (q["history_identity"], q["population_identity"], q["reference_identity"]) != \
                    (inputs["history_database"]["identity"], inputs["population_database"]["identity"],
                     inputs["reference_database"]["identity"]):
                _refuse("CONTEXT_PARENT_MISMATCH", f"{key}: names another parent release")
            for name in ("target_record_sha256", "parent_contest_sha256", "label_record_sha256"):
                if not IDENTITY_RE.match(q[name]):
                    _refuse("CONTEXT_KEY_MISMATCH", f"{key}: {name} is not a SHA-256")
            if len(q["history_view_sha256"]) != 2 or len(q["reference_feature_sha256"]) != 2 or \
                    not all(IDENTITY_RE.match(x) for x in (*q["history_view_sha256"], *q["reference_feature_sha256"])):
                _refuse("CONTEXT_KEY_MISMATCH", f"{key}: the per-view lineage digests are not two SHA-256s")
            cfbd = {}
            for side in ("a", "b"):
                b = q[f"{side}_binding"]
                if b["state"] == "BOUND":
                    if b["reason"] is not None or not (isinstance(b["cfbd_team_id"], str) and
                                                       DIGITS_RE.match(b["cfbd_team_id"])) or \
                            b["rule"] not in ACCEPTED_BINDING_RULES or not is_int(b["line_number"]) or \
                            not (isinstance(b["line_sha256"], str) and IDENTITY_RE.match(b["line_sha256"])):
                        _refuse("CONTEXT_BINDING_INVALID", f"{key}: a BOUND {side} binding is incomplete")
                    cfbd[side] = b["cfbd_team_id"]
                elif b["state"] == "UNSUPPORTED":
                    if b["reason"] not in ("NO_ACCEPTED_PARTICIPANT_BINDING", "BINDING_DUPLICATED",
                                           "BINDING_NOT_CONFIRMED") or b["cfbd_team_id"] is not None:
                        _refuse("CONTEXT_BINDING_INVALID", f"{key}: an UNSUPPORTED {side} binding is not one of the "
                                                           "declared reasons")
                else:
                    _refuse("CONTEXT_BINDING_INVALID", f"{key}: binding state {b['state']!r}")
            self._verify_provider(q, cfbd)
            for side in ("a", "b"):
                self._verify_history(key, side, q[f"{side}_history"])
                self._verify_calendar(q, side)
            if q["label_state"] not in LABEL_STATES:
                _refuse("CONTEXT_LABEL_INCONSISTENT", f"{key}: label state {q['label_state']!r}")
            state, reasons, pattern = support_decision(q)
            if (q["support_state"], q["support_reasons"], q["support_pattern"]) != (state, reasons, pattern):
                _refuse("CONTEXT_SUPPORT_MISMATCH", f"{key}: the support state, reasons or pattern does not follow "
                                                    "its qualification")
            frozen = excluded.get(key)
            if (frozen is None) != (state == "COMMON_SUPPORT") or (frozen is not None and frozen != reasons):
                _refuse("CONTEXT_COMMON_COHORT_DRIFT", f"{key}: the support state differs from the contract's frozen "
                                                       "common cohort")

    def _verify_provider(self, q: dict[str, Any], cfbd: dict[str, str]) -> None:
        key = q["qualification_key"]
        p = q["provider"]
        clock = q["capture_clock"]
        if q["provider_state"] == "PROVIDER_GAME_JOINED":
            if p is None or q["provider_reason"] is not None or len(q["documented_provider_game_ids"]) != 1 or \
                    p["game_id"] != q["documented_provider_game_ids"][0] or p["season"] != q["season"] or \
                    p["capture_season"] != q["season"] or len(cfbd) != 2 or cfbd["a"] == cfbd["b"] or \
                    {p["home_id"], p["away_id"]} != {cfbd["a"], cfbd["b"]}:
                _refuse("CONTEXT_PROVIDER_CLAIM_INVALID", f"{key}: a joined provider game does not join its "
                                                          "documented id, season and bound participants")
            side = "A" if p["home_id"] == cfbd["a"] else "B"
            claim = site_claim(p["neutral_site"], side)
            if (q["provider_home_side"], q["provider_site_claim"]) != (side, claim):
                _refuse("CONTEXT_PROVIDER_CLAIM_INVALID", f"{key}: the provider site claim does not follow its neutral "
                                                          "flag and bound home side")
            agreement = site_agreement(q["parent_site"], claim)
            if q["site_agreement"] != agreement or q["agreed_site"] != (q["parent_site"] if agreement == "AGREE"
                                                                         else None):
                _refuse("CONTEXT_SITE_MISMATCH", f"{key}: the site agreement does not follow the parent role and the "
                                                 "provider claim")
            if (q["date_state"], q["date_reason"], q["provider_utc_date_offset_days"]) != \
                    date_state(p["start_claim_utc"], q["contest_date"]):
                _refuse("CONTEXT_DATE_STATE_INVALID", f"{key}: the date state does not follow the start claim")
            receipts = self.anchors["inputs"]["capture_receipts"].get(str(q["season"]))
            games = self.anchors["inputs"]["provider_games"].get(str(q["season"]))
            if clock is None or receipts is None or games is None or \
                    (clock["capture_id"], clock["receipt_sha256"], clock["response_sha256"],
                     clock["capture_known_at_utc"], clock["retrieved_at_utc"]) != \
                    (receipts["capture_id"], receipts["sha256"], games["sha256"], receipts["capture_known_at_utc"],
                     receipts["retrieved_at_utc"]) or p["capture_sha256"] != games["sha256"] or \
                    clock["observed_after_target"] is not (clock["retrieved_at_utc"][:10] > q["contest_date"]):
                _refuse("CONTEXT_SOURCE_CLOCK_INVALID", f"{key}: the provider capture clock is not the pinned receipt's")
        elif q["provider_state"] == "UNSUPPORTED":
            if q["provider_reason"] is None or q["provider_home_side"] is not None or \
                    q["provider_site_claim"] is not None or q["site_agreement"] != "UNSUPPORTED" or \
                    q["agreed_site"] is not None or q["date_state"] != "UNSUPPORTED" or \
                    q["date_reason"] != "PROVIDER_GAME_NOT_JOINED" or q["provider_utc_date_offset_days"] is not None:
                _refuse("CONTEXT_PROVIDER_CLAIM_INVALID", f"{key}: an unjoined provider game carries a site or date "
                                                          "claim")
        else:
            _refuse("CONTEXT_PROVIDER_CLAIM_INVALID", f"{key}: provider state {q['provider_state']!r}")

    @staticmethod
    def _verify_history(key: str, side: str, h: dict[str, Any]) -> None:
        if not all(0 <= h[k] <= HISTORY_BOUND for k in ("games", "wins", "losses", "ties")):
            _refuse("CONTEXT_COUNT_OUT_OF_DOMAIN", f"{key}: {side} history counts are out of domain")
        if h["games"] != h["wins"] + h["losses"] + h["ties"] or len(h["contributing_contest_keys"]) != h["games"] or \
                h["cold_start"] != (h["games"] == 0) or len(set(h["contributing_contest_keys"])) != h["games"] or \
                not all(CONTEST_KEY_RE.match(k) for k in h["contributing_contest_keys"]):
            _refuse("CONTEXT_HISTORY_INCOHERENT", f"{key}: {side} history counts are incoherent")
        if key in h["contributing_contest_keys"]:
            _refuse("CONTEXT_HISTORY_LEAKAGE", f"{key}: the target contributes to its own history")
        if h["log_odds"] != history_log_odds(h["wins"], h["losses"], h["ties"]):
            _refuse("CONTEXT_LOG_ODDS_MISMATCH", f"{key}: {side} log-odds is not the frozen formula")

    @staticmethod
    def _verify_calendar(q: dict[str, Any], side: str) -> None:
        key = q["qualification_key"]
        c = q[f"{side}_calendar"]
        keys = q[f"{side}_history"]["contributing_contest_keys"]
        if c["state"] not in CALENDAR_STATES or not all(0 <= c[k] <= HISTORY_BOUND for k in (
                "eligible_prior_count", "excluded_prior_count", "excluded_prior_after_latest_eligible")) or \
                c["eligible_prior_count"] != len(keys) or \
                c["excluded_prior_after_latest_eligible"] > c["excluded_prior_count"]:
            _refuse("CONTEXT_CALENDAR_INVALID", f"{key}: {side} calendar state or counts are invalid")
        latest, latest_keys, interval = c["latest_prior_date"], c["latest_prior_contest_keys"], c["interval_days"]
        if c["state"] == "QUALIFIED_CALENDAR_INTERVAL":
            if not valid_date(latest) or not latest < q["contest_date"] or len(latest_keys) != 1 or \
                    latest_keys[0] not in keys or not is_int(interval) or not 1 <= interval <= INTERVAL_BOUND or \
                    interval != day_difference(q["contest_date"], latest) or \
                    c["intervening_calendar_days"] != interval - 1 or \
                    c["lineage_state"] != "EVERY_ELIGIBLE_PRIOR_JOINS_ITS_PARENT_CONTEST":
                _refuse("CONTEXT_CALENDAR_INVALID", f"{key}: {side} qualified interval does not follow its latest prior")
            return
        if interval is not None or c["intervening_calendar_days"] is not None:
            _refuse("CONTEXT_MISSING_AS_ZERO", f"{key}: an unqualified {side} calendar carries an interval")
        if c["state"] == "NO_ELIGIBLE_SAME_SEASON_PRIOR":
            if keys or latest is not None or latest_keys or c["excluded_prior_after_latest_eligible"]:
                _refuse("CONTEXT_CALENDAR_INVALID", f"{key}: a {side} side with priors is not NO_ELIGIBLE")
        elif c["state"] == "AMBIGUOUS_LATEST_PRIOR":
            if not valid_date(latest) or not latest < q["contest_date"] or len(latest_keys) < 2 or \
                    not set(latest_keys) <= set(keys) or latest_keys != sorted(latest_keys):
                _refuse("CONTEXT_CALENDAR_INVALID", f"{key}: a {side} latest-date tie is not recorded with every key")
        elif c["lineage_state"] == "EVERY_ELIGIBLE_PRIOR_JOINS_ITS_PARENT_CONTEST" or latest is not None:
            _refuse("CONTEXT_CALENDAR_INVALID", f"{key}: a {side} lineage failure carries no reason")

    def _verify_features(self, records: dict[str, list[dict[str, Any]]]) -> None:
        """Every feature equals its re-derivation from its qualification; the first difference is classified by
        cause (orientation, design, missing-as-zero, other)."""
        derived = derive_features(records["qualifications"])
        for stored, want in zip(records["features"], derived):
            if canonical_json_bytes(stored) == canonical_json_bytes(want):
                continue
            key = stored["feature_key"]
            differing = sorted(k for k in want if canonical_json_bytes(stored.get(k)) != canonical_json_bytes(want[k]))
            if want["design_site_calendar"] is None and stored["design_site_calendar"] is not None:
                _refuse("CONTEXT_MISSING_AS_ZERO", f"{key}: an unsupported game carries a design")
            if stored["view"] == "B" and set(differing) & {"history_log_odds_difference", "site_code",
                                                            "calendar_interval_difference_days"}:
                _refuse("CONTEXT_ORIENTATION_MISMATCH", f"{key}: the B view is not the exact negation of A on "
                                                        f"{differing}")
            if set(differing) & {"design_history", "design_site_calendar", "history_log_odds_difference",
                                 "site_code", "calendar_interval_difference_days"}:
                _refuse("CONTEXT_DESIGN_MISMATCH", f"{key}: the design is not the frozen columns ({differing})")
            _refuse("CONTEXT_FEATURE_MISMATCH", f"{key}: differs from its qualification on {differing}")

    def _verify_witnesses(self, records: dict[str, list[dict[str, Any]]]) -> None:
        quals = {q["contest_key"]: q for q in records["qualifications"]}
        expected = self.anchors["expected"]
        identity = self.anchors["inputs"]["reference_database"]["identity"]
        lines = []
        for w in records["witnesses"]:
            key = w["score_key"]
            q = quals[w["contest_key"]]
            parent = w["parent_score"]
            if not isinstance(parent, dict):
                _refuse("CONTEXT_WITNESS_MISMATCH", f"{key}: the parent score is not an object")
            line = _untrusted_canonical(parent, "CONTEXT_RECORD_MALFORMED", f"witness {key}").decode("utf-8")
            if sha256_bytes(line.encode("utf-8")) != w["parent_score_line_sha256"]:
                _refuse("CONTEXT_WITNESS_MISMATCH", f"{key}: the parent score does not reproduce its line digest")
            lines.append(line)
            model = w["model_id"]
            if model not in PARENT_MODELS or key != f"{w['contest_key']}|{model}" or \
                    (parent.get("contest_key"), parent.get("model_id"), parent.get("season"),
                     parent.get("contest_date"), parent.get("model_sha256"), parent.get("metric_kind"),
                     parent.get("orientation"), parent.get("a_key"), parent.get("b_key")) != \
                    (w["contest_key"], model, w["season"], w["contest_date"], PARENT_MODEL_SHA256[model],
                     metric_kind(model), "A", q["a_key"], q["b_key"]) or \
                    w["model_sha256"] != PARENT_MODEL_SHA256[model] or w["metric_kind"] != metric_kind(model) or \
                    w["score_source"] != SCORE_SOURCES["witnesses"] or w["parent_release_identity"] != identity or \
                    w["parent_score_state"] != parent.get("score_state"):
                _refuse("CONTEXT_WITNESS_MISMATCH", f"{key}: the witness does not bind its accepted parent record")
            if (w["season"], w["contest_date"], w["partition"], w["a_key"], w["b_key"], w["support_state"]) != \
                    (q["season"], q["contest_date"], q["partition"], q["a_key"], q["b_key"], q["support_state"]):
                _refuse("CONTEXT_WITNESS_MISMATCH", f"{key}: the witness game fields differ from its qualification")
            if parent.get("label_state") != q["label_state"] or \
                    parent.get("label_record_sha256") != q["label_record_sha256"]:
                _refuse("CONTEXT_LABEL_INCONSISTENT", f"{key}: the parent score names another label")
        if lines_sha256(lines) != expected["parent_witness_lines_sha256"]:
            _refuse("CONTEXT_PARENT_WITNESS_DRIFT", "the parent witnesses are not the contract's accepted C56 game "
                                                    "scores")

    def _rederive(self, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """A fresh refit and the complete re-derivation of every parameter, estimate, score, summary and census record
        from the verified qualifications, the score records' accepted label fields and the bound witnesses; each stored
        record must equal its re-derivation exactly (canonical JSON line)."""
        labels = labels_from_scores(records["scores"])
        quals = {q["contest_key"]: q for q in records["qualifications"]}
        for key, label in labels.items():
            if (label["label_state"], label["record_sha256"]) != (quals[key]["label_state"],
                                                                  quals[key]["label_record_sha256"]):
                _refuse("CONTEXT_LABEL_INCONSISTENT", f"{key}: the score label differs from the qualification's")
        for w in records["witnesses"]:
            label = labels[w["contest_key"]]
            if w["metric_kind"] == "PROBABILITY" and w["parent_score"].get("y_a") != label["y_a"]:
                _refuse("CONTEXT_LABEL_INCONSISTENT", f"{w['score_key']}: the parent outcome differs")
        # complements before the refit, so a lost complement is refused for its own cause
        for e in records["estimates"]:
            if e["estimate_state"] == "SUPPORTED":
                if e["probability_exact"] is None or e["opponent_probability_exact"] is None or \
                        frac(e["probability_exact"]) + frac(e["opponent_probability_exact"]) != 1 or \
                        e["opponent_probability"] is None or e["probability"] is None or \
                        dec_fraction(e["probability"]) + dec_fraction(e["opponent_probability"]) != 1:
                    _refuse("CONTEXT_COMPLEMENT_INVALID", f"{e['estimate_key']}: probabilities are not exact "
                                                          "complements")
        rebuilt = derive_from_qualifications(records["qualifications"], labels, records["witnesses"])
        for table, code in (("parameters", "CONTEXT_PARAMETER_MISMATCH"), ("estimates", "CONTEXT_ESTIMATE_MISMATCH"),
                            ("scores", "CONTEXT_SCORE_MISMATCH"), ("summary", "CONTEXT_SUMMARY_MISMATCH"),
                            ("census", "CONTEXT_CENSUS_MISMATCH")):
            for stored, want in zip(records[table], rebuilt[table]):
                if canonical_json_bytes(stored) != canonical_json_bytes(want):
                    differing = sorted(k for k in want if canonical_json_bytes(stored.get(k)) !=
                                       canonical_json_bytes(want[k]))
                    _refuse(code, f"{record_key(table, stored)}: the stored record differs from its re-derivation on "
                                  f"{differing[:6]}")
        return rebuilt["fits"]

    @staticmethod
    def _name_index(records: dict[str, list[dict[str, Any]]]) -> dict[tuple[int, str], frozenset[str]]:
        names: dict[tuple[int, str], set[str]] = {}
        for q in records["qualifications"]:
            for side in ("a", "b"):
                names.setdefault((q["season"], q[f"{side}_key"]), set()).add(q[f"{side}_team_name"].casefold())
        return {k: frozenset(v) for k, v in names.items()}

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "ContextAssociation":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- serving
    filters = staticmethod(validate_selection)

    def source_time(self) -> dict[str, Any]:
        clocks = self.anchors["inputs"]["capture_receipts"]
        latest = max((q["contest_date"] for q in self.records["qualifications"]), default=None)
        return {"provider_capture_clocks": {s: {"capture_known_at_utc": c["capture_known_at_utc"],
                                                "retrieved_at_utc": c["retrieved_at_utc"]}
                                            for s, c in sorted(clocks.items())},
                "provider_clock_kind": "RETAINED_CAPTURE_RECEIPT_TIME_OBSERVED_AFTER_EVERY_TARGET",
                "latest_target_contest_date": latest, "history_clock": LABELS["history_clock"],
                "release_provenance_issued_at_utc": (self.binding.get("provenance") or {}).get("issued_at_utc")
                if isinstance(self.binding.get("provenance"), dict) else None,
                "release_provenance_note": "the run manifest's provenance build clock; not identity-bound"}

    def query(self, grain: str, *, season: Any = None, partition: Any = None, team: Any = None, contest: Any = None,
              model: Any = None, limit: Any = 50, offset: Any = 0, all_rows: bool = False, limit_given: bool = False,
              offset_given: bool = False) -> dict[str, Any]:
        filters = validate_selection(grain, season=season, partition=partition, team=team, contest=contest,
                                     model=model)
        page_limit, page_offset = validate_paging(limit, offset, all_rows, limit_given=limit_given,
                                                  offset_given=offset_given)
        result: dict[str, Any] = {
            "release_identity": self.database_identity, "content_identity": self.content_identity,
            "contract_id": self.anchors["contract_id"], "contract_sha256": self.anchors["contract_sha256"],
            "population": POPULATION, "grain": grain, "filters": filters, "offset": page_offset,
            "limit": page_limit, **LABELS, "source_time": self.source_time(),
            "parents": {name: self.anchors["inputs"][name]["identity"]
                        for name in ("population_database", "history_database", "reference_database")},
            "denominators": self.census,
            "verification": {**{f"{t}_verified": len(self.records[t]) for t in RECORD_TABLES},
                             "records_verified": True, "refit_rederived": True, "content_identity_rebuilt": True,
                             "database_document_rebuilt": True, "profile_pinned": self.anchors.get("profile") is not None}}
        scope = "RETROSPECTIVE_STUDY_SEASONS_2016_2023"
        if "season" in filters and filters["season"] not in STUDY_SEASONS:
            scope = "SEASON_OUTSIDE_RELEASE"
        elif "season" in filters and "partition" in filters and \
                filters["season"] not in PARTITIONS[filters["partition"]]:
            scope = "SEASON_AND_PARTITION_DISJOINT"
        if scope != "RETROSPECTIVE_STUDY_SEASONS_2016_2023":
            rows: list[dict[str, Any]] = []
        elif grain == "context-summary":
            rows, selection = self._summary_rows(filters)
            result["summary_selection"] = selection
        elif grain == "context-score":
            rows = [r for r in self.score_grain if self._match(grain, r, filters)]
        else:
            rows = [r for r in self.records[GRAINS[grain][0]] if self._match(grain, r, filters)]
        total = len(rows)
        page = rows[page_offset:] if page_limit is None else rows[page_offset:page_offset + page_limit]
        result.update(season_scope_state=scope, total=total, returned=len(page), rows=page,
                      next_offset=page_offset + len(page) if page_offset + len(page) < total else None)
        return result

    def _team_matches(self, value: str, season: int, team_key: str) -> bool:
        if TEAM_KEY_RE.match(value):
            return team_key == value
        return value.casefold() in self.names.get((season, team_key), frozenset())

    def _game_match(self, record: dict[str, Any], filters: dict[str, Any], sides: tuple[str, ...]) -> bool:
        if "season" in filters and record["season"] != filters["season"]:
            return False
        if "partition" in filters and record["partition"] != filters["partition"]:
            return False
        if "contest" in filters and record["contest_key"] != filters["contest"]:
            return False
        if "team" in filters and not any(self._team_matches(filters["team"], record["season"], s) for s in sides):
            return False
        return True

    def _match(self, grain: str, record: dict[str, Any], filters: dict[str, Any]) -> bool:
        if "model" in filters and record["model_id"] != filters["model"]:
            return False
        if grain == "context-parameter":
            return True
        if grain in ("context-feature", "context-estimate"):
            return self._game_match(record, filters, (record["team_key"],))
        return self._game_match(record, filters, (record["a_key"], record["b_key"]))

    def _summary_rows(self, filters: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        game_filters = {k: v for k, v in filters.items() if k in GAME_SELECTORS}
        if not game_filters:
            rows = list(self.records["summary"])
            selection = {"rule": SUMMARY_RULE["selection"], "selected": "ALL_CANONICAL_GAMES",
                         "canonical_games": len(self.records["qualifications"]),
                         "eligible_common_support_games": self.census["common_support_games"]}
        else:
            chosen = [q for q in self.records["qualifications"] if self._game_match(q, game_filters, (q["a_key"],
                                                                                                       q["b_key"]))]
            keys = {q["contest_key"] for q in chosen}
            fit_states = {m: self.fits["models"][m]["state"] for m in NEW_MODELS}
            rows = summary_rows(self.records["qualifications"], self.records["scores"], self.records["witnesses"],
                                fit_states, selected=keys)
            by_season: dict[str, int] = {}
            for q in chosen:
                if q["support_state"] == "COMMON_SUPPORT":
                    by_season[str(q["season"])] = by_season.get(str(q["season"]), 0) + 1
            selection = {"rule": SUMMARY_RULE["selection"], "selected": "SELECTED_CANONICAL_GAMES",
                         "canonical_games": len(chosen), "eligible_common_support_games": sum(by_season.values()),
                         "eligible_games_by_season": dict(sorted(by_season.items()))}
        if "model" in filters:
            rows = [r for r in rows if r["model_id"] == filters["model"]]
        return rows, selection


# --------------------------------------------------------------------------------------------- expected collections

def expected_games(expected: dict[str, Any]) -> list[tuple[int, str, str]]:
    """The pinned targets in canonical (season, date, contest key) order."""
    games = []
    for season, dates in expected["targets"].items():
        for date, keys in dates.items():
            games += [(int(season), date, key) for key in keys]
    return sorted(games)


def expected_keys(expected: dict[str, Any]) -> dict[str, list[str]]:
    """The exact key sequence of every grain from the contract's pinned target list and the closed model namespace."""
    games = expected_games(expected)
    return {"qualifications": [k for _s, _d, k in games],
            "features": [f"{k}|{v}" for _s, _d, k in games for v in VIEWS],
            "parameters": list(NEW_MODELS),
            "estimates": [f"{k}|{m}|{v}" for _s, _d, k in games for m in NEW_MODELS for v in VIEWS],
            "scores": [f"{k}|{m}" for _s, _d, k in games for m in NEW_MODELS],
            "witnesses": [f"{k}|{m}" for _s, _d, k in games for m in PARENT_MODELS],
            "summary": [f"{kind}:{scope}|{m}" for kind, scope, _seasons in WINDOWS for m in MODEL_IDS],
            "census": ["census"]}


# ---- BEGIN GENERATED ANCHORS (tools/cycle63/make_site_calendar_contract.py; never hand edited) ----
#: The pinned authority of the reader: the committed contract SHA-256, every accepted parent input (relative locator
#: under the explicitly named data root, SHA-256, bytes, identities), the parent contracts and the expected collection
#: of every grain (the targets, the frozen excluded games with their reasons, the parent witness digest and every key
#: sequence digest). Generated from the accepted parents by the contract generator; never hand edited.
ANCHORS: dict[str, Any] = json.loads(r'''{
 "contract_id": "BAT-734-NATIONAL-SITE-CALENDAR-ASSOCIATION-2016-2023-V1.0",
 "contract_sha256": "9b74dfe73d9d4236752d2c173e0effe284044801ed73c7bf40082aa97a5677a5",
 "inputs": {
  "population_database": {
   "relative_path": "canonical/national_di_population_2016_2025/sha256/3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27/national_population.sqlite",
   "identity": "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27",
   "contract_sha256": "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903",
   "program_season_identity": "711e9dfcc35a181d51206099f41aa576424fc30ed61600811ab464074fb8f81e",
   "role": "ACCEPTED_C38_PARENT_POPULATION_CONTEST_ROWS_2016_2023",
   "sha256": "9c517af94b9e0c7105627397b8a8cd9f9fc0ee806493c126c842c5018c5ba172",
   "bytes": 17178624
  },
  "population_manifest": {
   "relative_path": "manifests/national_di_population_2016_2025/sha256/3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27/run_manifest.json",
   "identity": "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27",
   "role": "ACCEPTED_C38_POPULATION_RUN_MANIFEST",
   "sha256": "50f11d41e185aba463c92682a832c0785f8c7adb968bbdcf0bbd353acfe18bfa",
   "bytes": 902
  },
  "participant_bindings": {
   "relative_path": "canonical/national_di_population_2016_2025/sha256/711e9dfcc35a181d51206099f41aa576424fc30ed61600811ab464074fb8f81e/identity_bindings.jsonl.gz",
   "header_contract_sha256": "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903",
   "role": "ACCEPTED_C38_PARTICIPANT_PROVIDER_IDENTITY_BINDINGS",
   "sha256": "5d15acf7c12b94d5e7ad5fa2d22c60192aad0b4d6a48cecd66cab6835596dee9",
   "bytes": 9981
  },
  "history_database": {
   "relative_path": "canonical/national_history_prefix_2016_2023/sha256/aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b/national_history.sqlite",
   "identity": "aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b",
   "content_identity": "58c2bf7d6e9c70c2ba2a9e4dd583a89ace10062cc49aafe00d2f9675c84afe63",
   "contract_sha256": "2646a5cbe9a1daff7135671b85c98239b250d493c53c4bc066f57805e1e4f76c",
   "role": "ACCEPTED_C39_HISTORY_PREFIX_TARGETS_AND_ELIGIBLE_PRIORS",
   "sha256": "e137208cb3e9fec55c9b68e6af5c61e036ea7ea60a8973d9be9c35c358b17060",
   "bytes": 70189056
  },
  "history_manifest": {
   "relative_path": "manifests/national_history_prefix_2016_2023/sha256/aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b/run_manifest.json",
   "identity": "aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b",
   "role": "ACCEPTED_C39_HISTORY_RUN_MANIFEST",
   "sha256": "fa7680e33d11c439061a9a7fd3b7be8df124fb88679fae4b4a29d9808fbf2b20",
   "bytes": 2548
  },
  "reference_database": {
   "relative_path": "canonical/national_retrospective_reference_2016_2023/sha256/ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8/national_retrospective_reference.sqlite",
   "identity": "ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8",
   "content_identity": "fe303a90d8753956b914d3c7c2adfe2d33d9816bfb45689b0361f8e36e2e6cc0",
   "contract_sha256": "3cfeff255bb29801b482b02611ad2c72c725d069e9f89d3911e86711af34bb31",
   "role": "ACCEPTED_C56_REFERENCE_FEATURES_LABELS_AND_PARENT_GAME_SCORES",
   "sha256": "17a0776587eb30918903dc0d38c736958b1984feb4b40379bbfc80425035785d",
   "bytes": 10584064
  },
  "reference_manifest": {
   "relative_path": "manifests/national_retrospective_reference_2016_2023/sha256/ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8/run_manifest.json",
   "identity": "ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8",
   "role": "ACCEPTED_C56_REFERENCE_RUN_MANIFEST",
   "sha256": "cd2a7f22be95ab6dd7bfe737ce905bb15a9b93c42e6cf3e31f2b39a24704b1b8",
   "bytes": 3450
  },
  "provider_games": {
   "2016": {
    "relative_path": "raw/SRC-002/games/sha256_9bc85c6f9768a2469864cb844e6cc98cdfce06f23b02a8bfb8f03004cad12613.json",
    "sha256": "9bc85c6f9768a2469864cb844e6cc98cdfce06f23b02a8bfb8f03004cad12613",
    "bytes": 711750,
    "rows": 873,
    "role": "RETAINED_FULL_FBS_PROVIDER_GAME_CAPTURE_2016"
   },
   "2017": {
    "relative_path": "raw/SRC-002/games/sha256_6ca1a9cc367b6c70eb4fb2bd2a71fb83b05dc536028857f60b94fdd57062eda2.json",
    "sha256": "6ca1a9cc367b6c70eb4fb2bd2a71fb83b05dc536028857f60b94fdd57062eda2",
    "bytes": 715951,
    "rows": 874,
    "role": "RETAINED_FULL_FBS_PROVIDER_GAME_CAPTURE_2017"
   },
   "2018": {
    "relative_path": "raw/SRC-002/games/sha256_c96dbf7384af57300d6a3eb927ddb8fdc29e4e5d4bccd15babc4c32366829837.json",
    "sha256": "c96dbf7384af57300d6a3eb927ddb8fdc29e4e5d4bccd15babc4c32366829837",
    "bytes": 726690,
    "rows": 884,
    "role": "RETAINED_FULL_FBS_PROVIDER_GAME_CAPTURE_2018"
   },
   "2019": {
    "relative_path": "raw/SRC-002/games/sha256_b361354f331cd9a419ebec756833c65a480f2431fd6044fb9e96e06cf4b6f14f.json",
    "sha256": "b361354f331cd9a419ebec756833c65a480f2431fd6044fb9e96e06cf4b6f14f",
    "bytes": 731343,
    "rows": 888,
    "role": "RETAINED_FULL_FBS_PROVIDER_GAME_CAPTURE_2019"
   },
   "2020": {
    "relative_path": "raw/SRC-002/games/sha256_6fde848c1b58a2a0c2ca831bbf6f93e7bb5a4398c9746682438e96095846a63f.json",
    "sha256": "6fde848c1b58a2a0c2ca831bbf6f93e7bb5a4398c9746682438e96095846a63f",
    "bytes": 468707,
    "rows": 570,
    "role": "RETAINED_FULL_FBS_PROVIDER_GAME_CAPTURE_2020"
   },
   "2021": {
    "relative_path": "raw/SRC-002/games/sha256_09f2f4613dc4dc83d38e14757bb28695b4532463a0b788cb12c4d13347a2d19a.json",
    "sha256": "09f2f4613dc4dc83d38e14757bb28695b4532463a0b788cb12c4d13347a2d19a",
    "bytes": 695012,
    "rows": 887,
    "role": "RETAINED_FULL_FBS_PROVIDER_GAME_CAPTURE_2021"
   },
   "2022": {
    "relative_path": "raw/SRC-002/games/sha256_9c50d7465d2d74f6c0e9d9bf79c4b593a0b70db790207109d1c2f675e6e70fdf.json",
    "sha256": "9c50d7465d2d74f6c0e9d9bf79c4b593a0b70db790207109d1c2f675e6e70fdf",
    "bytes": 702663,
    "rows": 896,
    "role": "RETAINED_FULL_FBS_PROVIDER_GAME_CAPTURE_2022"
   },
   "2023": {
    "relative_path": "raw/SRC-002/games/sha256_ebf9ea175c3332102dd4555fd8cd126cbd2cbc6cef4aebe95c6c5ae7af1dea03.json",
    "sha256": "ebf9ea175c3332102dd4555fd8cd126cbd2cbc6cef4aebe95c6c5ae7af1dea03",
    "bytes": 713155,
    "rows": 910,
    "role": "RETAINED_FULL_FBS_PROVIDER_GAME_CAPTURE_2023"
   }
  },
  "capture_receipts": {
   "2016": {
    "relative_path": "manifests/captures/SRC-002/cap_7ba1e63b5c96b95ad908ac2e.json",
    "sha256": "1fdcfdbd704be01911a795607377d97cb9a407487691c5ff1d59d105d4a2c3ae",
    "bytes": 2677,
    "capture_id": "cap_7ba1e63b5c96b95ad908ac2e",
    "capture_known_at_utc": "2026-08-09T18:59:49Z",
    "retrieved_at_utc": "2026-08-09T18:59:49Z",
    "source_uri": "https://api.collegefootballdata.com/games?classification=fbs&year=2016",
    "upstream_lineage": "CFBD_AGGREGATED_OR_DERIVED_RECORD; NOT_AN_INDEPENDENT_CONFIRMATION_OF_ITS_UPSTREAM_SOURCE",
    "role": "RETAINED_PROVIDER_CAPTURE_RECEIPT_2016"
   },
   "2017": {
    "relative_path": "manifests/captures/SRC-002/cap_8c237a06fcc4fb0fa489e819.json",
    "sha256": "ade916cd58df441386aba943da313f977531dc7e63ec6805db6a07780c3c9ef5",
    "bytes": 2677,
    "capture_id": "cap_8c237a06fcc4fb0fa489e819",
    "capture_known_at_utc": "2026-08-09T18:59:49Z",
    "retrieved_at_utc": "2026-08-09T18:59:49Z",
    "source_uri": "https://api.collegefootballdata.com/games?classification=fbs&year=2017",
    "upstream_lineage": "CFBD_AGGREGATED_OR_DERIVED_RECORD; NOT_AN_INDEPENDENT_CONFIRMATION_OF_ITS_UPSTREAM_SOURCE",
    "role": "RETAINED_PROVIDER_CAPTURE_RECEIPT_2017"
   },
   "2018": {
    "relative_path": "manifests/captures/SRC-002/cap_fca8ffe34583265bdedb6a66.json",
    "sha256": "cbd6af47026645be0af1302c3c089db056e5628f6897bfff9b6a685f65bdc443",
    "bytes": 2677,
    "capture_id": "cap_fca8ffe34583265bdedb6a66",
    "capture_known_at_utc": "2026-08-09T18:59:49Z",
    "retrieved_at_utc": "2026-08-09T18:59:49Z",
    "source_uri": "https://api.collegefootballdata.com/games?classification=fbs&year=2018",
    "upstream_lineage": "CFBD_AGGREGATED_OR_DERIVED_RECORD; NOT_AN_INDEPENDENT_CONFIRMATION_OF_ITS_UPSTREAM_SOURCE",
    "role": "RETAINED_PROVIDER_CAPTURE_RECEIPT_2018"
   },
   "2019": {
    "relative_path": "manifests/captures/SRC-002/cap_1dc1b866dd56f02e217b6305.json",
    "sha256": "9b0ce0f089b00f5ea7246d92330b79e8ed186f0a3476661a0037682952772530",
    "bytes": 2677,
    "capture_id": "cap_1dc1b866dd56f02e217b6305",
    "capture_known_at_utc": "2026-08-09T18:59:50Z",
    "retrieved_at_utc": "2026-08-09T18:59:50Z",
    "source_uri": "https://api.collegefootballdata.com/games?classification=fbs&year=2019",
    "upstream_lineage": "CFBD_AGGREGATED_OR_DERIVED_RECORD; NOT_AN_INDEPENDENT_CONFIRMATION_OF_ITS_UPSTREAM_SOURCE",
    "role": "RETAINED_PROVIDER_CAPTURE_RECEIPT_2019"
   },
   "2020": {
    "relative_path": "manifests/captures/SRC-002/cap_b89826898fcbb575790bde15.json",
    "sha256": "80271030aef077af68b54fa067774e3e184f01a81eb7edc635c89ee23988041f",
    "bytes": 2677,
    "capture_id": "cap_b89826898fcbb575790bde15",
    "capture_known_at_utc": "2026-08-09T18:59:50Z",
    "retrieved_at_utc": "2026-08-09T18:59:50Z",
    "source_uri": "https://api.collegefootballdata.com/games?classification=fbs&year=2020",
    "upstream_lineage": "CFBD_AGGREGATED_OR_DERIVED_RECORD; NOT_AN_INDEPENDENT_CONFIRMATION_OF_ITS_UPSTREAM_SOURCE",
    "role": "RETAINED_PROVIDER_CAPTURE_RECEIPT_2020"
   },
   "2021": {
    "relative_path": "manifests/captures/SRC-002/cap_3c3beda43b160118d56777b1.json",
    "sha256": "9cf7fc691912e43be2822578a20460cd89ec2c3359aa175e24a701bbd61d4be5",
    "bytes": 2677,
    "capture_id": "cap_3c3beda43b160118d56777b1",
    "capture_known_at_utc": "2026-08-09T18:59:51Z",
    "retrieved_at_utc": "2026-08-09T18:59:51Z",
    "source_uri": "https://api.collegefootballdata.com/games?classification=fbs&year=2021",
    "upstream_lineage": "CFBD_AGGREGATED_OR_DERIVED_RECORD; NOT_AN_INDEPENDENT_CONFIRMATION_OF_ITS_UPSTREAM_SOURCE",
    "role": "RETAINED_PROVIDER_CAPTURE_RECEIPT_2021"
   },
   "2022": {
    "relative_path": "manifests/captures/SRC-002/cap_d8794bdadba655a1c4136e59.json",
    "sha256": "afd891fda2ac3e8d7e78b6a45ac9682e700de77fec5a8c4043f6d3946b855405",
    "bytes": 2671,
    "capture_id": "cap_d8794bdadba655a1c4136e59",
    "capture_known_at_utc": "2026-08-09T16:57:39Z",
    "retrieved_at_utc": "2026-08-09T16:57:39Z",
    "source_uri": "https://api.collegefootballdata.com/games?classification=fbs&year=2022",
    "upstream_lineage": "CFBD_AGGREGATED_OR_DERIVED_RECORD; NOT_AN_INDEPENDENT_CONFIRMATION_OF_ITS_UPSTREAM_SOURCE",
    "role": "RETAINED_PROVIDER_CAPTURE_RECEIPT_2022"
   },
   "2023": {
    "relative_path": "manifests/captures/SRC-002/cap_2c82aa5161f3ad63b5abb3c3.json",
    "sha256": "6598b949b38fc707831002bc202bbf060ff7faeaceea178fb1748b8d8dbea4f3",
    "bytes": 2671,
    "capture_id": "cap_2c82aa5161f3ad63b5abb3c3",
    "capture_known_at_utc": "2026-08-09T16:57:56Z",
    "retrieved_at_utc": "2026-08-09T16:57:56Z",
    "source_uri": "https://api.collegefootballdata.com/games?classification=fbs&year=2023",
    "upstream_lineage": "CFBD_AGGREGATED_OR_DERIVED_RECORD; NOT_AN_INDEPENDENT_CONFIRMATION_OF_ITS_UPSTREAM_SOURCE",
    "role": "RETAINED_PROVIDER_CAPTURE_RECEIPT_2023"
   }
  }
 },
 "parent_contracts": {
  "configs/national_di_population_2016_2025_contract.json": "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903",
  "configs/national_history_prefix_2016_2023_contract.json": "2646a5cbe9a1daff7135671b85c98239b250d493c53c4bc066f57805e1e4f76c",
  "configs/national_retrospective_reference_2016_2023_contract.json": "3cfeff255bb29801b482b02611ad2c72c725d069e9f89d3911e86711af34bb31"
 },
 "expected": {
  "targets": {
   "2016": {
    "2016-08-27": [
     "ncaa:196973"
    ],
    "2016-09-01": [
     "ncaa:196995",
     "ncaa:197023",
     "ncaa:197025",
     "ncaa:197026",
     "ncaa:197030",
     "ncaa:197031",
     "ncaa:197032"
    ],
    "2016-09-02": [
     "ncaa:197043",
     "ncaa:197046",
     "ncaa:197054",
     "ncaa:197060",
     "ncaa:197064"
    ],
    "2016-09-03": [
     "ncaa:197094",
     "ncaa:197106",
     "ncaa:197125",
     "ncaa:197132",
     "ncaa:197135",
     "ncaa:197140",
     "ncaa:197143",
     "ncaa:197146",
     "ncaa:197148",
     "ncaa:197164",
     "ncaa:197195",
     "ncaa:197201",
     "ncaa:197202",
     "ncaa:197225",
     "ncaa:197242",
     "ncaa:197243",
     "ncaa:197245",
     "ncaa:197255",
     "ncaa:197257",
     "ncaa:197265",
     "ncaa:197266",
     "ncaa:197267",
     "ncaa:197268",
     "ncaa:197269",
     "ncaa:197270"
    ],
    "2016-09-04": [
     "ncaa:197290"
    ],
    "2016-09-05": [
     "ncaa:197294"
    ],
    "2016-09-09": [
     "ncaa:197309",
     "ncaa:197310"
    ],
    "2016-09-10": [
     "ncaa:197314",
     "ncaa:197316",
     "ncaa:197332",
     "ncaa:197337",
     "ncaa:197339",
     "ncaa:197340",
     "ncaa:197347",
     "ncaa:197363",
     "ncaa:197365",
     "ncaa:197366",
     "ncaa:197367",
     "ncaa:197381",
     "ncaa:197382",
     "ncaa:197390",
     "ncaa:197391",
     "ncaa:197393",
     "ncaa:197394",
     "ncaa:197402",
     "ncaa:197410",
     "ncaa:197412",
     "ncaa:197414",
     "ncaa:197427",
     "ncaa:197464",
     "ncaa:197483",
     "ncaa:197484",
     "ncaa:197496",
     "ncaa:197502",
     "ncaa:197512",
     "ncaa:197515",
     "ncaa:197531",
     "ncaa:197532",
     "ncaa:197539",
     "ncaa:197555",
     "ncaa:197556",
     "ncaa:197558",
     "ncaa:197560",
     "ncaa:197568",
     "ncaa:197569",
     "ncaa:197572",
     "ncaa:197573",
     "ncaa:197587",
     "ncaa:197588"
    ],
    "2016-09-15": [
     "ncaa:197606"
    ],
    "2016-09-16": [
     "ncaa:197612",
     "ncaa:197614",
     "ncaa:197617"
    ],
    "2016-09-17": [
     "ncaa:197632",
     "ncaa:197638",
     "ncaa:197640",
     "ncaa:197659",
     "ncaa:197668",
     "ncaa:197670",
     "ncaa:197678",
     "ncaa:197679",
     "ncaa:197690",
     "ncaa:197699",
     "ncaa:197712",
     "ncaa:197719",
     "ncaa:197722",
     "ncaa:197733",
     "ncaa:197745",
     "ncaa:197748",
     "ncaa:197751",
     "ncaa:197760",
     "ncaa:197767",
     "ncaa:197777",
     "ncaa:197782",
     "ncaa:197794",
     "ncaa:197798",
     "ncaa:197801",
     "ncaa:197804",
     "ncaa:197805",
     "ncaa:197810",
     "ncaa:197822",
     "ncaa:197835",
     "ncaa:197836",
     "ncaa:197843",
     "ncaa:197844",
     "ncaa:197846",
     "ncaa:197847",
     "ncaa:197848",
     "ncaa:197849",
     "ncaa:197850",
     "ncaa:197856",
     "ncaa:197857",
     "ncaa:197869",
     "ncaa:197870",
     "ncaa:197874",
     "ncaa:197875",
     "ncaa:197878",
     "ncaa:197883",
     "ncaa:197884",
     "ncaa:197885",
     "ncaa:197887",
     "ncaa:197899",
     "ncaa:197900"
    ],
    "2016-09-22": [
     "ncaa:197923"
    ],
    "2016-09-23": [
     "ncaa:197927",
     "ncaa:197928",
     "ncaa:197929"
    ],
    "2016-09-24": [
     "ncaa:197936",
     "ncaa:197943",
     "ncaa:197945",
     "ncaa:197947",
     "ncaa:197952",
     "ncaa:197953",
     "ncaa:197957",
     "ncaa:197966",
     "ncaa:197970",
     "ncaa:197971",
     "ncaa:197972",
     "ncaa:197978",
     "ncaa:197979",
     "ncaa:197990",
     "ncaa:198015",
     "ncaa:198018",
     "ncaa:198020",
     "ncaa:198021",
     "ncaa:198025",
     "ncaa:198026",
     "ncaa:198035",
     "ncaa:198037",
     "ncaa:198038",
     "ncaa:198050",
     "ncaa:198069",
     "ncaa:198092",
     "ncaa:198101",
     "ncaa:198131",
     "ncaa:198132",
     "ncaa:198136",
     "ncaa:198137",
     "ncaa:198141",
     "ncaa:198142",
     "ncaa:198157",
     "ncaa:198158",
     "ncaa:198159",
     "ncaa:198164",
     "ncaa:198165",
     "ncaa:198174",
     "ncaa:198175",
     "ncaa:198176",
     "ncaa:198180",
     "ncaa:198182",
     "ncaa:198183",
     "ncaa:198202",
     "ncaa:198204"
    ],
    "2016-09-29": [
     "ncaa:198216",
     "ncaa:198217"
    ],
    "2016-09-30": [
     "ncaa:198220",
     "ncaa:198224"
    ],
    "2016-10-01": [
     "ncaa:198228",
     "ncaa:198229",
     "ncaa:198235",
     "ncaa:198237",
     "ncaa:198238",
     "ncaa:198239",
     "ncaa:198241",
     "ncaa:198242",
     "ncaa:198246",
     "ncaa:198259",
     "ncaa:198264",
     "ncaa:198266",
     "ncaa:198269",
     "ncaa:198270",
     "ncaa:198279",
     "ncaa:198281",
     "ncaa:198289",
     "ncaa:198292",
     "ncaa:198301",
     "ncaa:198303",
     "ncaa:198313",
     "ncaa:198315",
     "ncaa:198325",
     "ncaa:198330",
     "ncaa:198331",
     "ncaa:198334",
     "ncaa:198344",
     "ncaa:198369",
     "ncaa:198380",
     "ncaa:198392",
     "ncaa:198402",
     "ncaa:198414",
     "ncaa:198417",
     "ncaa:198420",
     "ncaa:198432",
     "ncaa:198435",
     "ncaa:198458",
     "ncaa:198459",
     "ncaa:198460",
     "ncaa:198467",
     "ncaa:198468",
     "ncaa:198483",
     "ncaa:198484",
     "ncaa:198486",
     "ncaa:198488",
     "ncaa:198489",
     "ncaa:198490",
     "ncaa:198496",
     "ncaa:198497",
     "ncaa:198498",
     "ncaa:198500",
     "ncaa:198509",
     "ncaa:198513"
    ],
    "2016-10-05": [
     "ncaa:198535"
    ],
    "2016-10-06": [
     "ncaa:198537",
     "ncaa:198541"
    ],
    "2016-10-07": [
     "ncaa:198544",
     "ncaa:198545",
     "ncaa:198549",
     "ncaa:198550"
    ],
    "2016-10-08": [
     "ncaa:198557",
     "ncaa:198559",
     "ncaa:198563",
     "ncaa:198573",
     "ncaa:198574",
     "ncaa:198576",
     "ncaa:198584",
     "ncaa:198588",
     "ncaa:198592",
     "ncaa:198593",
     "ncaa:198601",
     "ncaa:198614",
     "ncaa:198615",
     "ncaa:198629",
     "ncaa:198631",
     "ncaa:198634",
     "ncaa:198639",
     "ncaa:198650",
     "ncaa:198655",
     "ncaa:198656",
     "ncaa:198658",
     "ncaa:198667",
     "ncaa:198689",
     "ncaa:198692",
     "ncaa:198703",
     "ncaa:198709",
     "ncaa:198717",
     "ncaa:198719",
     "ncaa:198720",
     "ncaa:198730",
     "ncaa:198734",
     "ncaa:198737",
     "ncaa:198743",
     "ncaa:198749",
     "ncaa:198755",
     "ncaa:198758",
     "ncaa:198759",
     "ncaa:198760",
     "ncaa:198761",
     "ncaa:198762",
     "ncaa:198779",
     "ncaa:198783",
     "ncaa:198784",
     "ncaa:198801"
    ],
    "2016-10-09": [
     "ncaa:198826",
     "ncaa:198828"
    ],
    "2016-10-12": [
     "ncaa:198829"
    ],
    "2016-10-14": [
     "ncaa:198833",
     "ncaa:198834",
     "ncaa:198837",
     "ncaa:198838"
    ],
    "2016-10-15": [
     "ncaa:198843",
     "ncaa:198846",
     "ncaa:198848",
     "ncaa:198849",
     "ncaa:198854",
     "ncaa:198855",
     "ncaa:198856",
     "ncaa:198865",
     "ncaa:198870",
     "ncaa:198871",
     "ncaa:198873",
     "ncaa:198874",
     "ncaa:198877",
     "ncaa:198881",
     "ncaa:198882",
     "ncaa:198900",
     "ncaa:198908",
     "ncaa:198909",
     "ncaa:198918",
     "ncaa:198921",
     "ncaa:198929",
     "ncaa:198935",
     "ncaa:198938",
     "ncaa:198958",
     "ncaa:198959",
     "ncaa:198993",
     "ncaa:198994",
     "ncaa:198998",
     "ncaa:199007",
     "ncaa:199018",
     "ncaa:199028",
     "ncaa:199030",
     "ncaa:199035",
     "ncaa:199051",
     "ncaa:199068",
     "ncaa:199069",
     "ncaa:199070",
     "ncaa:199071",
     "ncaa:199078",
     "ncaa:199090",
     "ncaa:199093",
     "ncaa:199095",
     "ncaa:199096",
     "ncaa:199103",
     "ncaa:199105",
     "ncaa:199116"
    ],
    "2016-10-20": [
     "ncaa:199139",
     "ncaa:199140",
     "ncaa:199142"
    ],
    "2016-10-21": [
     "ncaa:199146",
     "ncaa:199147",
     "ncaa:199149"
    ],
    "2016-10-22": [
     "ncaa:199155",
     "ncaa:199165",
     "ncaa:199166",
     "ncaa:199168",
     "ncaa:199171",
     "ncaa:199176",
     "ncaa:199181",
     "ncaa:199218",
     "ncaa:199219",
     "ncaa:199220",
     "ncaa:199232",
     "ncaa:199235",
     "ncaa:199236",
     "ncaa:199239",
     "ncaa:199242",
     "ncaa:199243",
     "ncaa:199245",
     "ncaa:199250",
     "ncaa:199255",
     "ncaa:199267",
     "ncaa:199277",
     "ncaa:199289",
     "ncaa:199319",
     "ncaa:199330",
     "ncaa:199331",
     "ncaa:199332",
     "ncaa:199350",
     "ncaa:199351",
     "ncaa:199352",
     "ncaa:199353",
     "ncaa:199364",
     "ncaa:199365",
     "ncaa:199380",
     "ncaa:199387",
     "ncaa:199389",
     "ncaa:199390",
     "ncaa:199393",
     "ncaa:199394",
     "ncaa:199408",
     "ncaa:199409",
     "ncaa:199410",
     "ncaa:199411",
     "ncaa:199418",
     "ncaa:199419",
     "ncaa:199420",
     "ncaa:199435"
    ],
    "2016-10-27": [
     "ncaa:199455",
     "ncaa:199457",
     "ncaa:199458",
     "ncaa:199459",
     "ncaa:199460"
    ],
    "2016-10-28": [
     "ncaa:199462",
     "ncaa:199464"
    ],
    "2016-10-29": [
     "ncaa:199473",
     "ncaa:199476",
     "ncaa:199478",
     "ncaa:199483",
     "ncaa:199484",
     "ncaa:199492",
     "ncaa:199497",
     "ncaa:199501",
     "ncaa:199503",
     "ncaa:199504",
     "ncaa:199507",
     "ncaa:199510",
     "ncaa:199518",
     "ncaa:199520",
     "ncaa:199532",
     "ncaa:199533",
     "ncaa:199535",
     "ncaa:199542",
     "ncaa:199557",
     "ncaa:199558",
     "ncaa:199563",
     "ncaa:199565",
     "ncaa:199578",
     "ncaa:199591",
     "ncaa:199608",
     "ncaa:199632",
     "ncaa:199660",
     "ncaa:199665",
     "ncaa:199679",
     "ncaa:199698",
     "ncaa:199699",
     "ncaa:199700",
     "ncaa:199705",
     "ncaa:199713",
     "ncaa:199715",
     "ncaa:199717",
     "ncaa:199718",
     "ncaa:199722",
     "ncaa:199723",
     "ncaa:199724",
     "ncaa:199726",
     "ncaa:199738",
     "ncaa:199743"
    ],
    "2016-11-01": [
     "ncaa:199769",
     "ncaa:199770"
    ],
    "2016-11-02": [
     "ncaa:199771"
    ],
    "2016-11-03": [
     "ncaa:199772",
     "ncaa:199773",
     "ncaa:199774",
     "ncaa:199775"
    ],
    "2016-11-04": [
     "ncaa:199778",
     "ncaa:199779",
     "ncaa:199780"
    ],
    "2016-11-05": [
     "ncaa:199785",
     "ncaa:199790",
     "ncaa:199791",
     "ncaa:199798",
     "ncaa:199807",
     "ncaa:199824",
     "ncaa:199827",
     "ncaa:199848",
     "ncaa:199853",
     "ncaa:199873",
     "ncaa:199875",
     "ncaa:199881",
     "ncaa:199882",
     "ncaa:199883",
     "ncaa:199887",
     "ncaa:199898",
     "ncaa:199901",
     "ncaa:199902",
     "ncaa:199909",
     "ncaa:199910",
     "ncaa:199936",
     "ncaa:199949",
     "ncaa:199956",
     "ncaa:199957",
     "ncaa:199966",
     "ncaa:199968",
     "ncaa:199975",
     "ncaa:199984",
     "ncaa:199989",
     "ncaa:199993",
     "ncaa:199998",
     "ncaa:199999",
     "ncaa:200003",
     "ncaa:200014",
     "ncaa:200019",
     "ncaa:200020",
     "ncaa:200022",
     "ncaa:200023",
     "ncaa:200024",
     "ncaa:200025",
     "ncaa:200026",
     "ncaa:200027",
     "ncaa:200042",
     "ncaa:200050",
     "ncaa:200051",
     "ncaa:200052",
     "ncaa:200064",
     "ncaa:200068"
    ],
    "2016-11-08": [
     "ncaa:200092",
     "ncaa:200093"
    ],
    "2016-11-09": [
     "ncaa:200094",
     "ncaa:200095"
    ],
    "2016-11-10": [
     "ncaa:200096",
     "ncaa:200097",
     "ncaa:200098"
    ],
    "2016-11-11": [
     "ncaa:200101"
    ],
    "2016-11-12": [
     "ncaa:200107",
     "ncaa:200114",
     "ncaa:200117",
     "ncaa:200121",
     "ncaa:200125",
     "ncaa:200133",
     "ncaa:200136",
     "ncaa:200138",
     "ncaa:200141",
     "ncaa:200151",
     "ncaa:200158",
     "ncaa:200159",
     "ncaa:200160",
     "ncaa:200171",
     "ncaa:200172",
     "ncaa:200174",
     "ncaa:200182",
     "ncaa:200183",
     "ncaa:200188",
     "ncaa:200194",
     "ncaa:200198",
     "ncaa:200199",
     "ncaa:200200",
     "ncaa:200225",
     "ncaa:200234",
     "ncaa:200240",
     "ncaa:200263",
     "ncaa:200270",
     "ncaa:200273",
     "ncaa:200291",
     "ncaa:200293",
     "ncaa:200304",
     "ncaa:200307",
     "ncaa:200313",
     "ncaa:200329",
     "ncaa:200334",
     "ncaa:200347",
     "ncaa:200348",
     "ncaa:200349",
     "ncaa:200350",
     "ncaa:200352",
     "ncaa:200353",
     "ncaa:200358",
     "ncaa:200359",
     "ncaa:200360",
     "ncaa:200362",
     "ncaa:200373",
     "ncaa:200379"
    ],
    "2016-11-15": [
     "ncaa:200403",
     "ncaa:200404"
    ],
    "2016-11-16": [
     "ncaa:200405",
     "ncaa:200406"
    ],
    "2016-11-17": [
     "ncaa:200407",
     "ncaa:200409"
    ],
    "2016-11-18": [
     "ncaa:200412",
     "ncaa:200413"
    ],
    "2016-11-19": [
     "ncaa:200419",
     "ncaa:200420",
     "ncaa:200421",
     "ncaa:200422",
     "ncaa:200425",
     "ncaa:200427",
     "ncaa:200428",
     "ncaa:200429",
     "ncaa:200431",
     "ncaa:200434",
     "ncaa:200437",
     "ncaa:200440",
     "ncaa:200441",
     "ncaa:200442",
     "ncaa:200445",
     "ncaa:200446",
     "ncaa:200448",
     "ncaa:200451",
     "ncaa:200452",
     "ncaa:200453",
     "ncaa:200454",
     "ncaa:200456",
     "ncaa:200457",
     "ncaa:200458",
     "ncaa:200459",
     "ncaa:200462",
     "ncaa:200463",
     "ncaa:200464",
     "ncaa:200471",
     "ncaa:200475",
     "ncaa:200478",
     "ncaa:200481",
     "ncaa:200485",
     "ncaa:200489",
     "ncaa:200490",
     "ncaa:200491",
     "ncaa:200492",
     "ncaa:200493",
     "ncaa:200494",
     "ncaa:200497",
     "ncaa:200507",
     "ncaa:200508",
     "ncaa:200511",
     "ncaa:200515",
     "ncaa:200516",
     "ncaa:200517",
     "ncaa:200518",
     "ncaa:200521"
    ],
    "2016-11-22": [
     "ncaa:200560",
     "ncaa:200561",
     "ncaa:200562"
    ],
    "2016-11-24": [
     "ncaa:200564"
    ],
    "2016-11-25": [
     "ncaa:200565",
     "ncaa:200567",
     "ncaa:200568",
     "ncaa:200569",
     "ncaa:200570",
     "ncaa:200571",
     "ncaa:200572",
     "ncaa:200573",
     "ncaa:200574",
     "ncaa:200575",
     "ncaa:200576",
     "ncaa:200577",
     "ncaa:200578"
    ],
    "2016-11-26": [
     "ncaa:200579",
     "ncaa:200580",
     "ncaa:200581",
     "ncaa:200582",
     "ncaa:200583",
     "ncaa:200584",
     "ncaa:200585",
     "ncaa:200586",
     "ncaa:200587",
     "ncaa:200588",
     "ncaa:200589",
     "ncaa:200590",
     "ncaa:200591",
     "ncaa:200592",
     "ncaa:200593",
     "ncaa:200594",
     "ncaa:200595",
     "ncaa:200596",
     "ncaa:200597",
     "ncaa:200598",
     "ncaa:200599",
     "ncaa:200600",
     "ncaa:200603",
     "ncaa:200604",
     "ncaa:200605",
     "ncaa:200606",
     "ncaa:200607",
     "ncaa:200608",
     "ncaa:200609",
     "ncaa:200610",
     "ncaa:200611",
     "ncaa:200612",
     "ncaa:200613",
     "ncaa:200614",
     "ncaa:200615",
     "ncaa:200616",
     "ncaa:200617",
     "ncaa:200618",
     "ncaa:200619",
     "ncaa:200620",
     "ncaa:200621",
     "ncaa:200622"
    ],
    "2016-12-02": [
     "ncaa:200650",
     "ncaa:200651"
    ],
    "2016-12-03": [
     "ncaa:200652",
     "ncaa:200654",
     "ncaa:200655",
     "ncaa:200656",
     "ncaa:200657",
     "ncaa:200658",
     "ncaa:200659",
     "ncaa:200676",
     "ncaa:200677",
     "ncaa:200678",
     "ncaa:200682",
     "ncaa:200683",
     "ncaa:200685"
    ],
    "2016-12-10": [
     "ncaa:200694"
    ],
    "2016-12-17": [
     "ncaa:200699",
     "ncaa:200700",
     "ncaa:200704"
    ],
    "2016-12-19": [
     "ncaa:200705"
    ],
    "2016-12-20": [
     "ncaa:200706"
    ],
    "2016-12-21": [
     "ncaa:200707"
    ],
    "2016-12-22": [
     "ncaa:200708"
    ],
    "2016-12-23": [
     "ncaa:200709",
     "ncaa:200710",
     "ncaa:200711"
    ],
    "2016-12-26": [
     "ncaa:200713",
     "ncaa:200714",
     "ncaa:200715"
    ],
    "2016-12-27": [
     "ncaa:200716",
     "ncaa:200717",
     "ncaa:200718",
     "ncaa:200719"
    ],
    "2016-12-28": [
     "ncaa:200720",
     "ncaa:200721",
     "ncaa:200722",
     "ncaa:200723"
    ],
    "2016-12-29": [
     "ncaa:200724",
     "ncaa:200725",
     "ncaa:200726"
    ],
    "2016-12-30": [
     "ncaa:200727",
     "ncaa:200728",
     "ncaa:200729",
     "ncaa:200730"
    ],
    "2016-12-31": [
     "ncaa:200732",
     "ncaa:200733",
     "ncaa:200734",
     "ncaa:200735"
    ],
    "2017-01-02": [
     "ncaa:200736",
     "ncaa:200737",
     "ncaa:200738",
     "ncaa:200739"
    ],
    "2017-01-09": [
     "ncaa:200741"
    ]
   },
   "2017": {
    "2017-08-26": [
     "ncaa:60161",
     "ncaa:60163",
     "ncaa:60166"
    ],
    "2017-08-27": [
     "ncaa:60167"
    ],
    "2017-08-31": [
     "ncaa:60176",
     "ncaa:60178",
     "ncaa:60179",
     "ncaa:60214",
     "ncaa:60230",
     "ncaa:60235"
    ],
    "2017-09-01": [
     "ncaa:60252",
     "ncaa:60260",
     "ncaa:60262",
     "ncaa:60264",
     "ncaa:60265",
     "ncaa:60267"
    ],
    "2017-09-02": [
     "ncaa:60281",
     "ncaa:60302",
     "ncaa:60304",
     "ncaa:60313",
     "ncaa:60323",
     "ncaa:60330",
     "ncaa:60335",
     "ncaa:60336",
     "ncaa:60344",
     "ncaa:60347",
     "ncaa:60351",
     "ncaa:60355",
     "ncaa:60358",
     "ncaa:60375",
     "ncaa:60397",
     "ncaa:60424",
     "ncaa:60431",
     "ncaa:60432",
     "ncaa:60442",
     "ncaa:60445",
     "ncaa:60463",
     "ncaa:60464",
     "ncaa:60465",
     "ncaa:60466",
     "ncaa:60467",
     "ncaa:60469"
    ],
    "2017-09-03": [
     "ncaa:60484"
    ],
    "2017-09-04": [
     "ncaa:60486"
    ],
    "2017-09-08": [
     "ncaa:60503",
     "ncaa:60506"
    ],
    "2017-09-09": [
     "ncaa:60522",
     "ncaa:60532",
     "ncaa:60539",
     "ncaa:60551",
     "ncaa:60559",
     "ncaa:60566",
     "ncaa:60572",
     "ncaa:60575",
     "ncaa:60584",
     "ncaa:60589",
     "ncaa:60592",
     "ncaa:60596",
     "ncaa:60597",
     "ncaa:60601",
     "ncaa:60606",
     "ncaa:60607",
     "ncaa:60611",
     "ncaa:60615",
     "ncaa:60623",
     "ncaa:60627",
     "ncaa:60630",
     "ncaa:60632",
     "ncaa:60638",
     "ncaa:60644",
     "ncaa:60645",
     "ncaa:60649",
     "ncaa:60651",
     "ncaa:60657",
     "ncaa:60661",
     "ncaa:60668",
     "ncaa:60674",
     "ncaa:60675",
     "ncaa:60676",
     "ncaa:60696",
     "ncaa:60702",
     "ncaa:60706",
     "ncaa:60723",
     "ncaa:60733",
     "ncaa:60735",
     "ncaa:60740",
     "ncaa:60744",
     "ncaa:60747",
     "ncaa:60757"
    ],
    "2017-09-14": [
     "ncaa:60791"
    ],
    "2017-09-15": [
     "ncaa:60796",
     "ncaa:60798",
     "ncaa:60799"
    ],
    "2017-09-16": [
     "ncaa:60803",
     "ncaa:60819",
     "ncaa:60828",
     "ncaa:60834",
     "ncaa:60837",
     "ncaa:60843",
     "ncaa:60860",
     "ncaa:60862",
     "ncaa:60865",
     "ncaa:60868",
     "ncaa:60875",
     "ncaa:60876",
     "ncaa:60880",
     "ncaa:60884",
     "ncaa:60891",
     "ncaa:60893",
     "ncaa:60903",
     "ncaa:60908",
     "ncaa:60909",
     "ncaa:60919",
     "ncaa:60921",
     "ncaa:60922",
     "ncaa:60927",
     "ncaa:60934",
     "ncaa:60938",
     "ncaa:60944",
     "ncaa:60968",
     "ncaa:60969",
     "ncaa:60971",
     "ncaa:60972",
     "ncaa:60986",
     "ncaa:60992",
     "ncaa:60994",
     "ncaa:61002",
     "ncaa:61016",
     "ncaa:61028",
     "ncaa:61041",
     "ncaa:61046",
     "ncaa:61047",
     "ncaa:61048",
     "ncaa:61049",
     "ncaa:61050",
     "ncaa:61054",
     "ncaa:61055",
     "ncaa:61056",
     "ncaa:61066"
    ],
    "2017-09-21": [
     "ncaa:61098"
    ],
    "2017-09-22": [
     "ncaa:61101",
     "ncaa:61103"
    ],
    "2017-09-23": [
     "ncaa:61114",
     "ncaa:61118",
     "ncaa:61119",
     "ncaa:61121",
     "ncaa:61132",
     "ncaa:61141",
     "ncaa:61147",
     "ncaa:61149",
     "ncaa:61150",
     "ncaa:61157",
     "ncaa:61164",
     "ncaa:61168",
     "ncaa:61173",
     "ncaa:61191",
     "ncaa:61192",
     "ncaa:61195",
     "ncaa:61196",
     "ncaa:61203",
     "ncaa:61205",
     "ncaa:61213",
     "ncaa:61214",
     "ncaa:61217",
     "ncaa:61228",
     "ncaa:61238",
     "ncaa:61246",
     "ncaa:61249",
     "ncaa:61259",
     "ncaa:61260",
     "ncaa:61264",
     "ncaa:61266",
     "ncaa:61267",
     "ncaa:61268",
     "ncaa:61286",
     "ncaa:61297",
     "ncaa:61300",
     "ncaa:61307",
     "ncaa:61312",
     "ncaa:61317",
     "ncaa:61320",
     "ncaa:61325",
     "ncaa:61332",
     "ncaa:61333",
     "ncaa:61334",
     "ncaa:61347",
     "ncaa:61348",
     "ncaa:61351",
     "ncaa:61353",
     "ncaa:61354",
     "ncaa:61361",
     "ncaa:61363",
     "ncaa:61370"
    ],
    "2017-09-28": [
     "ncaa:61395"
    ],
    "2017-09-29": [
     "ncaa:61400",
     "ncaa:61401",
     "ncaa:61402",
     "ncaa:61404"
    ],
    "2017-09-30": [
     "ncaa:61407",
     "ncaa:61415",
     "ncaa:61416",
     "ncaa:61426",
     "ncaa:61427",
     "ncaa:61442",
     "ncaa:61443",
     "ncaa:61449",
     "ncaa:61456",
     "ncaa:61459",
     "ncaa:61474",
     "ncaa:61488",
     "ncaa:61493",
     "ncaa:61498",
     "ncaa:61500",
     "ncaa:61504",
     "ncaa:61508",
     "ncaa:61511",
     "ncaa:61512",
     "ncaa:61527",
     "ncaa:61529",
     "ncaa:61531",
     "ncaa:61538",
     "ncaa:61546",
     "ncaa:61562",
     "ncaa:61566",
     "ncaa:61583",
     "ncaa:61585",
     "ncaa:61603",
     "ncaa:61607",
     "ncaa:61611",
     "ncaa:61613",
     "ncaa:61617",
     "ncaa:61631",
     "ncaa:61636",
     "ncaa:61637",
     "ncaa:61638",
     "ncaa:61639",
     "ncaa:61640",
     "ncaa:61641",
     "ncaa:61645",
     "ncaa:61647",
     "ncaa:61648",
     "ncaa:61649",
     "ncaa:61650",
     "ncaa:61651",
     "ncaa:61652"
    ],
    "2017-10-04": [
     "ncaa:61701"
    ],
    "2017-10-05": [
     "ncaa:61703"
    ],
    "2017-10-06": [
     "ncaa:61708"
    ],
    "2017-10-07": [
     "ncaa:61735",
     "ncaa:61747",
     "ncaa:61753",
     "ncaa:61754",
     "ncaa:61756",
     "ncaa:61764",
     "ncaa:61765",
     "ncaa:61769",
     "ncaa:61770",
     "ncaa:61771",
     "ncaa:61775",
     "ncaa:61788",
     "ncaa:61792",
     "ncaa:61793",
     "ncaa:61795",
     "ncaa:61797",
     "ncaa:61802",
     "ncaa:61804",
     "ncaa:61810",
     "ncaa:61817",
     "ncaa:61818",
     "ncaa:61828",
     "ncaa:61829",
     "ncaa:61833",
     "ncaa:61834",
     "ncaa:61839",
     "ncaa:61841",
     "ncaa:61843",
     "ncaa:61847",
     "ncaa:61862",
     "ncaa:61863",
     "ncaa:61869",
     "ncaa:61896",
     "ncaa:61897",
     "ncaa:61901",
     "ncaa:61908",
     "ncaa:61914",
     "ncaa:61922",
     "ncaa:61923",
     "ncaa:61929",
     "ncaa:61934",
     "ncaa:61937",
     "ncaa:61943",
     "ncaa:61956",
     "ncaa:61957",
     "ncaa:61958",
     "ncaa:61959",
     "ncaa:61962",
     "ncaa:61965",
     "ncaa:61966",
     "ncaa:61967",
     "ncaa:61974"
    ],
    "2017-10-11": [
     "ncaa:62006"
    ],
    "2017-10-12": [
     "ncaa:62010"
    ],
    "2017-10-13": [
     "ncaa:62012",
     "ncaa:62013"
    ],
    "2017-10-14": [
     "ncaa:62016",
     "ncaa:62028",
     "ncaa:62032",
     "ncaa:62033",
     "ncaa:62037",
     "ncaa:62047",
     "ncaa:62056",
     "ncaa:62064",
     "ncaa:62065",
     "ncaa:62067",
     "ncaa:62075",
     "ncaa:62076",
     "ncaa:62085",
     "ncaa:62087",
     "ncaa:62094",
     "ncaa:62095",
     "ncaa:62100",
     "ncaa:62103",
     "ncaa:62108",
     "ncaa:62112",
     "ncaa:62117",
     "ncaa:62122",
     "ncaa:62124",
     "ncaa:62127",
     "ncaa:62136",
     "ncaa:62137",
     "ncaa:62139",
     "ncaa:62140",
     "ncaa:62159",
     "ncaa:62168",
     "ncaa:62191",
     "ncaa:62195",
     "ncaa:62206",
     "ncaa:62220",
     "ncaa:62221",
     "ncaa:62225",
     "ncaa:62226",
     "ncaa:62237",
     "ncaa:62244",
     "ncaa:62252",
     "ncaa:62253",
     "ncaa:62255",
     "ncaa:62257",
     "ncaa:62259",
     "ncaa:62266",
     "ncaa:62269",
     "ncaa:62270",
     "ncaa:62271",
     "ncaa:62272",
     "ncaa:62274",
     "ncaa:62277",
     "ncaa:62294"
    ],
    "2017-10-15": [
     "ncaa:62313"
    ],
    "2017-10-19": [
     "ncaa:62314",
     "ncaa:62316"
    ],
    "2017-10-20": [
     "ncaa:62317",
     "ncaa:62320",
     "ncaa:62321",
     "ncaa:62323"
    ],
    "2017-10-21": [
     "ncaa:62326",
     "ncaa:62340",
     "ncaa:62347",
     "ncaa:62348",
     "ncaa:62365",
     "ncaa:62372",
     "ncaa:62382",
     "ncaa:62385",
     "ncaa:62393",
     "ncaa:62394",
     "ncaa:62403",
     "ncaa:62404",
     "ncaa:62407",
     "ncaa:62411",
     "ncaa:62418",
     "ncaa:62420",
     "ncaa:62421",
     "ncaa:62427",
     "ncaa:62428",
     "ncaa:62430",
     "ncaa:62432",
     "ncaa:62436",
     "ncaa:62439",
     "ncaa:62444",
     "ncaa:62446",
     "ncaa:62453",
     "ncaa:62454",
     "ncaa:62455",
     "ncaa:62456",
     "ncaa:62457",
     "ncaa:62466",
     "ncaa:62484",
     "ncaa:62486",
     "ncaa:62521",
     "ncaa:62527",
     "ncaa:62534",
     "ncaa:62537",
     "ncaa:62539",
     "ncaa:62561",
     "ncaa:62568",
     "ncaa:62569",
     "ncaa:62572",
     "ncaa:62574",
     "ncaa:62575",
     "ncaa:62577",
     "ncaa:62578",
     "ncaa:62579",
     "ncaa:62589"
    ],
    "2017-10-26": [
     "ncaa:62624",
     "ncaa:62625",
     "ncaa:62626",
     "ncaa:62629"
    ],
    "2017-10-27": [
     "ncaa:62630",
     "ncaa:62631",
     "ncaa:62632"
    ],
    "2017-10-28": [
     "ncaa:62650",
     "ncaa:62660",
     "ncaa:62661",
     "ncaa:62668",
     "ncaa:62677",
     "ncaa:62686",
     "ncaa:62688",
     "ncaa:62706",
     "ncaa:62709",
     "ncaa:62716",
     "ncaa:62728",
     "ncaa:62731",
     "ncaa:62732",
     "ncaa:62734",
     "ncaa:62735",
     "ncaa:62741",
     "ncaa:62744",
     "ncaa:62745",
     "ncaa:62746",
     "ncaa:62747",
     "ncaa:62765",
     "ncaa:62770",
     "ncaa:62784",
     "ncaa:62789",
     "ncaa:62790",
     "ncaa:62792",
     "ncaa:62794",
     "ncaa:62815",
     "ncaa:62816",
     "ncaa:62822",
     "ncaa:62826",
     "ncaa:62836",
     "ncaa:62839",
     "ncaa:62844",
     "ncaa:62854",
     "ncaa:62859",
     "ncaa:62860",
     "ncaa:62878",
     "ncaa:62879",
     "ncaa:62880",
     "ncaa:62881",
     "ncaa:62882",
     "ncaa:62888",
     "ncaa:62894",
     "ncaa:62910",
     "ncaa:62928"
    ],
    "2017-10-31": [
     "ncaa:62935",
     "ncaa:62936"
    ],
    "2017-11-01": [
     "ncaa:62937"
    ],
    "2017-11-02": [
     "ncaa:62939",
     "ncaa:62941",
     "ncaa:62942",
     "ncaa:62943"
    ],
    "2017-11-03": [
     "ncaa:62944",
     "ncaa:62945",
     "ncaa:62948"
    ],
    "2017-11-04": [
     "ncaa:62960",
     "ncaa:62964",
     "ncaa:62970",
     "ncaa:62971",
     "ncaa:62978",
     "ncaa:62980",
     "ncaa:62988",
     "ncaa:62996",
     "ncaa:62997",
     "ncaa:63000",
     "ncaa:63003",
     "ncaa:63011",
     "ncaa:63015",
     "ncaa:63019",
     "ncaa:63025",
     "ncaa:63034",
     "ncaa:63035",
     "ncaa:63040",
     "ncaa:63046",
     "ncaa:63053",
     "ncaa:63056",
     "ncaa:63065",
     "ncaa:63074",
     "ncaa:63083",
     "ncaa:63092",
     "ncaa:63094",
     "ncaa:63095",
     "ncaa:63099",
     "ncaa:63104",
     "ncaa:63121",
     "ncaa:63128",
     "ncaa:63153",
     "ncaa:63154",
     "ncaa:63168",
     "ncaa:63176",
     "ncaa:63186",
     "ncaa:63187",
     "ncaa:63193",
     "ncaa:63195",
     "ncaa:63203",
     "ncaa:63204",
     "ncaa:63212",
     "ncaa:63213",
     "ncaa:63214",
     "ncaa:63215",
     "ncaa:63216",
     "ncaa:63217",
     "ncaa:63227",
     "ncaa:63228"
    ],
    "2017-11-07": [
     "ncaa:63260",
     "ncaa:63261"
    ],
    "2017-11-08": [
     "ncaa:63262",
     "ncaa:63263",
     "ncaa:63264"
    ],
    "2017-11-09": [
     "ncaa:63265",
     "ncaa:63267",
     "ncaa:63268"
    ],
    "2017-11-10": [
     "ncaa:63271",
     "ncaa:63272",
     "ncaa:63273"
    ],
    "2017-11-11": [
     "ncaa:63287",
     "ncaa:63289",
     "ncaa:63309",
     "ncaa:63311",
     "ncaa:63318",
     "ncaa:63326",
     "ncaa:63328",
     "ncaa:63330",
     "ncaa:63335",
     "ncaa:63342",
     "ncaa:63344",
     "ncaa:63351",
     "ncaa:63354",
     "ncaa:63360",
     "ncaa:63369",
     "ncaa:63372",
     "ncaa:63373",
     "ncaa:63376",
     "ncaa:63384",
     "ncaa:63386",
     "ncaa:63395",
     "ncaa:63401",
     "ncaa:63402",
     "ncaa:63410",
     "ncaa:63413",
     "ncaa:63425",
     "ncaa:63431",
     "ncaa:63432",
     "ncaa:63435",
     "ncaa:63457",
     "ncaa:63459",
     "ncaa:63466",
     "ncaa:63471",
     "ncaa:63477",
     "ncaa:63491",
     "ncaa:63495",
     "ncaa:63501",
     "ncaa:63508",
     "ncaa:63509",
     "ncaa:63510",
     "ncaa:63511",
     "ncaa:63515",
     "ncaa:63517",
     "ncaa:63518",
     "ncaa:63543",
     "ncaa:63566"
    ],
    "2017-11-14": [
     "ncaa:63567",
     "ncaa:63568"
    ],
    "2017-11-15": [
     "ncaa:63569",
     "ncaa:63570",
     "ncaa:63571"
    ],
    "2017-11-16": [
     "ncaa:63572",
     "ncaa:63573"
    ],
    "2017-11-17": [
     "ncaa:63577",
     "ncaa:63578"
    ],
    "2017-11-18": [
     "ncaa:63581",
     "ncaa:63585",
     "ncaa:63586",
     "ncaa:63587",
     "ncaa:63588",
     "ncaa:63590",
     "ncaa:63591",
     "ncaa:63593",
     "ncaa:63595",
     "ncaa:63598",
     "ncaa:63599",
     "ncaa:63600",
     "ncaa:63601",
     "ncaa:63603",
     "ncaa:63612",
     "ncaa:63615",
     "ncaa:63616",
     "ncaa:63617",
     "ncaa:63618",
     "ncaa:63623",
     "ncaa:63624",
     "ncaa:63627",
     "ncaa:63632",
     "ncaa:63633",
     "ncaa:63634",
     "ncaa:63635",
     "ncaa:63636",
     "ncaa:63643",
     "ncaa:63646",
     "ncaa:63647",
     "ncaa:63652",
     "ncaa:63654",
     "ncaa:63655",
     "ncaa:63656",
     "ncaa:63658",
     "ncaa:63660",
     "ncaa:63661",
     "ncaa:63663",
     "ncaa:63664",
     "ncaa:63668",
     "ncaa:63669",
     "ncaa:63670",
     "ncaa:63671",
     "ncaa:63672",
     "ncaa:63673",
     "ncaa:63674",
     "ncaa:63675",
     "ncaa:63678",
     "ncaa:63723"
    ],
    "2017-11-21": [
     "ncaa:63725",
     "ncaa:63726",
     "ncaa:63727"
    ],
    "2017-11-23": [
     "ncaa:63728"
    ],
    "2017-11-24": [
     "ncaa:63730",
     "ncaa:63731",
     "ncaa:63732",
     "ncaa:63733",
     "ncaa:63734",
     "ncaa:63735",
     "ncaa:63736",
     "ncaa:63737",
     "ncaa:63738",
     "ncaa:63739",
     "ncaa:63740",
     "ncaa:63741",
     "ncaa:63742",
     "ncaa:63743",
     "ncaa:63744"
    ],
    "2017-11-25": [
     "ncaa:63745",
     "ncaa:63746",
     "ncaa:63747",
     "ncaa:63748",
     "ncaa:63749",
     "ncaa:63750",
     "ncaa:63751",
     "ncaa:63752",
     "ncaa:63753",
     "ncaa:63754",
     "ncaa:63755",
     "ncaa:63756",
     "ncaa:63757",
     "ncaa:63758",
     "ncaa:63759",
     "ncaa:63760",
     "ncaa:63761",
     "ncaa:63762",
     "ncaa:63763",
     "ncaa:63766",
     "ncaa:63767",
     "ncaa:63768",
     "ncaa:63769",
     "ncaa:63770",
     "ncaa:63771",
     "ncaa:63772",
     "ncaa:63773",
     "ncaa:63774",
     "ncaa:63775",
     "ncaa:63776",
     "ncaa:63778",
     "ncaa:63779",
     "ncaa:63780",
     "ncaa:63781",
     "ncaa:63783",
     "ncaa:63784",
     "ncaa:63785",
     "ncaa:63786",
     "ncaa:63787",
     "ncaa:63788"
    ],
    "2017-12-01": [
     "ncaa:63814"
    ],
    "2017-12-02": [
     "ncaa:63815",
     "ncaa:63816",
     "ncaa:63817",
     "ncaa:63818",
     "ncaa:63819",
     "ncaa:63820",
     "ncaa:63833",
     "ncaa:63834",
     "ncaa:63835",
     "ncaa:63840",
     "ncaa:63841",
     "ncaa:63842",
     "ncaa:63844",
     "ncaa:63846",
     "ncaa:63848"
    ],
    "2017-12-09": [
     "ncaa:63859"
    ],
    "2017-12-16": [
     "ncaa:63863",
     "ncaa:63866",
     "ncaa:63867",
     "ncaa:63868",
     "ncaa:63869"
    ],
    "2017-12-19": [
     "ncaa:63870"
    ],
    "2017-12-20": [
     "ncaa:63871"
    ],
    "2017-12-21": [
     "ncaa:63872"
    ],
    "2017-12-22": [
     "ncaa:63873",
     "ncaa:63874"
    ],
    "2017-12-23": [
     "ncaa:63875",
     "ncaa:63876",
     "ncaa:63877"
    ],
    "2017-12-24": [
     "ncaa:63878"
    ],
    "2017-12-26": [
     "ncaa:63880",
     "ncaa:63881"
    ],
    "2017-12-27": [
     "ncaa:63882",
     "ncaa:63883",
     "ncaa:63884",
     "ncaa:63885"
    ],
    "2017-12-28": [
     "ncaa:63886",
     "ncaa:63887",
     "ncaa:63888",
     "ncaa:63889"
    ],
    "2017-12-29": [
     "ncaa:63890",
     "ncaa:63891",
     "ncaa:63892",
     "ncaa:63893",
     "ncaa:63894"
    ],
    "2017-12-30": [
     "ncaa:63895",
     "ncaa:63896",
     "ncaa:63897",
     "ncaa:63898"
    ],
    "2018-01-01": [
     "ncaa:63899",
     "ncaa:63900",
     "ncaa:63901",
     "ncaa:63902",
     "ncaa:63903"
    ],
    "2018-01-08": [
     "ncaa:63905"
    ]
   },
   "2018": {
    "2018-08-25": [
     "ncaa:1519847",
     "ncaa:1519850"
    ],
    "2018-08-30": [
     "ncaa:1519885",
     "ncaa:1519889",
     "ncaa:1519905",
     "ncaa:1519917"
    ],
    "2018-08-31": [
     "ncaa:1519934",
     "ncaa:1519935",
     "ncaa:1519936",
     "ncaa:1519939",
     "ncaa:1519940",
     "ncaa:1519941"
    ],
    "2018-09-01": [
     "ncaa:1520004",
     "ncaa:1520010",
     "ncaa:1520011",
     "ncaa:1520014",
     "ncaa:1520017",
     "ncaa:1520018",
     "ncaa:1520020",
     "ncaa:1520036",
     "ncaa:1520050",
     "ncaa:1520053",
     "ncaa:1520056",
     "ncaa:1520057",
     "ncaa:1520062",
     "ncaa:1520064",
     "ncaa:1520067",
     "ncaa:1520070",
     "ncaa:1520071",
     "ncaa:1520072",
     "ncaa:1520074",
     "ncaa:1520075",
     "ncaa:1520076",
     "ncaa:1520077",
     "ncaa:1520081",
     "ncaa:1520082",
     "ncaa:1520085",
     "ncaa:1520087",
     "ncaa:1520088",
     "ncaa:1520116",
     "ncaa:1520131",
     "ncaa:1520133",
     "ncaa:1520135"
    ],
    "2018-09-02": [
     "ncaa:1520165"
    ],
    "2018-09-03": [
     "ncaa:1520167"
    ],
    "2018-09-07": [
     "ncaa:1520183"
    ],
    "2018-09-08": [
     "ncaa:1520247",
     "ncaa:1520254",
     "ncaa:1520255",
     "ncaa:1520260",
     "ncaa:1520263",
     "ncaa:1520265",
     "ncaa:1520266",
     "ncaa:1520272",
     "ncaa:1520275",
     "ncaa:1520277",
     "ncaa:1520278",
     "ncaa:1520282",
     "ncaa:1520285",
     "ncaa:1520286",
     "ncaa:1520287",
     "ncaa:1520288",
     "ncaa:1520291",
     "ncaa:1520294",
     "ncaa:1520300",
     "ncaa:1520302",
     "ncaa:1520309",
     "ncaa:1520313",
     "ncaa:1520314",
     "ncaa:1520322",
     "ncaa:1520323",
     "ncaa:1520326",
     "ncaa:1520328",
     "ncaa:1520341",
     "ncaa:1520343",
     "ncaa:1520344",
     "ncaa:1520345",
     "ncaa:1520346",
     "ncaa:1520347",
     "ncaa:1520348",
     "ncaa:1520351",
     "ncaa:1520352",
     "ncaa:1520353",
     "ncaa:1520366",
     "ncaa:1520367",
     "ncaa:1520381",
     "ncaa:1520429",
     "ncaa:1520432",
     "ncaa:1520433",
     "ncaa:1520434",
     "ncaa:1520448",
     "ncaa:1520472",
     "ncaa:1520477"
    ],
    "2018-09-13": [
     "ncaa:1520481",
     "ncaa:1520586"
    ],
    "2018-09-14": [
     "ncaa:1520486"
    ],
    "2018-09-15": [
     "ncaa:1520546",
     "ncaa:1520550",
     "ncaa:1520554",
     "ncaa:1520555",
     "ncaa:1520558",
     "ncaa:1520564",
     "ncaa:1520568",
     "ncaa:1520570",
     "ncaa:1520573",
     "ncaa:1520574",
     "ncaa:1520580",
     "ncaa:1520583",
     "ncaa:1520585",
     "ncaa:1520596",
     "ncaa:1520605",
     "ncaa:1520608",
     "ncaa:1520609",
     "ncaa:1520611",
     "ncaa:1520614",
     "ncaa:1520616",
     "ncaa:1520635",
     "ncaa:1520636",
     "ncaa:1520637",
     "ncaa:1520638",
     "ncaa:1520639",
     "ncaa:1520640",
     "ncaa:1520641",
     "ncaa:1520642",
     "ncaa:1520647",
     "ncaa:1520648",
     "ncaa:1520649",
     "ncaa:1520654",
     "ncaa:1520655",
     "ncaa:1520665",
     "ncaa:1520732",
     "ncaa:1520758",
     "ncaa:1520760",
     "ncaa:1520767",
     "ncaa:1520775",
     "ncaa:1520778",
     "ncaa:1520780",
     "ncaa:1520781",
     "ncaa:1520788",
     "ncaa:1520796",
     "ncaa:1560670"
    ],
    "2018-09-20": [
     "ncaa:1520799"
    ],
    "2018-09-21": [
     "ncaa:1520803",
     "ncaa:1520804",
     "ncaa:1520809"
    ],
    "2018-09-22": [
     "ncaa:1520862",
     "ncaa:1520867",
     "ncaa:1520868",
     "ncaa:1520872",
     "ncaa:1520874",
     "ncaa:1520875",
     "ncaa:1520877",
     "ncaa:1520884",
     "ncaa:1520886",
     "ncaa:1520888",
     "ncaa:1520889",
     "ncaa:1520891",
     "ncaa:1520893",
     "ncaa:1520895",
     "ncaa:1520898",
     "ncaa:1520899",
     "ncaa:1520900",
     "ncaa:1520903",
     "ncaa:1520905",
     "ncaa:1520907",
     "ncaa:1520909",
     "ncaa:1520910",
     "ncaa:1520911",
     "ncaa:1520920",
     "ncaa:1520927",
     "ncaa:1520928",
     "ncaa:1520929",
     "ncaa:1520933",
     "ncaa:1520934",
     "ncaa:1520939",
     "ncaa:1520940",
     "ncaa:1520941",
     "ncaa:1520945",
     "ncaa:1520954",
     "ncaa:1520955",
     "ncaa:1520956",
     "ncaa:1520957",
     "ncaa:1520958",
     "ncaa:1520959",
     "ncaa:1520960",
     "ncaa:1520961",
     "ncaa:1520962",
     "ncaa:1520963",
     "ncaa:1520964",
     "ncaa:1520965",
     "ncaa:1520966",
     "ncaa:1520967",
     "ncaa:1521035",
     "ncaa:1521039",
     "ncaa:1521076",
     "ncaa:1521085"
    ],
    "2018-09-27": [
     "ncaa:1521087"
    ],
    "2018-09-28": [
     "ncaa:1521092",
     "ncaa:1521093"
    ],
    "2018-09-29": [
     "ncaa:1521096",
     "ncaa:1521161",
     "ncaa:1521167",
     "ncaa:1521171",
     "ncaa:1521172",
     "ncaa:1521174",
     "ncaa:1521176",
     "ncaa:1521177",
     "ncaa:1521178",
     "ncaa:1521180",
     "ncaa:1521182",
     "ncaa:1521184",
     "ncaa:1521186",
     "ncaa:1521190",
     "ncaa:1521193",
     "ncaa:1521194",
     "ncaa:1521195",
     "ncaa:1521196",
     "ncaa:1521197",
     "ncaa:1521199",
     "ncaa:1521201",
     "ncaa:1521204",
     "ncaa:1521206",
     "ncaa:1521207",
     "ncaa:1521215",
     "ncaa:1521218",
     "ncaa:1521220",
     "ncaa:1521221",
     "ncaa:1521222",
     "ncaa:1521225",
     "ncaa:1521228",
     "ncaa:1521235",
     "ncaa:1521236",
     "ncaa:1521237",
     "ncaa:1521238",
     "ncaa:1521244",
     "ncaa:1521251",
     "ncaa:1521253",
     "ncaa:1521254",
     "ncaa:1521255",
     "ncaa:1521256",
     "ncaa:1521257",
     "ncaa:1521258",
     "ncaa:1521259",
     "ncaa:1521261",
     "ncaa:1521262",
     "ncaa:1521263",
     "ncaa:1521264",
     "ncaa:1521273",
     "ncaa:1521367",
     "ncaa:1564057",
     "ncaa:1564083"
    ],
    "2018-10-04": [
     "ncaa:1521397",
     "ncaa:1521398"
    ],
    "2018-10-05": [
     "ncaa:1521401",
     "ncaa:1521403",
     "ncaa:1521404"
    ],
    "2018-10-06": [
     "ncaa:1521406",
     "ncaa:1521407",
     "ncaa:1521475",
     "ncaa:1521476",
     "ncaa:1521478",
     "ncaa:1521482",
     "ncaa:1521487",
     "ncaa:1521490",
     "ncaa:1521492",
     "ncaa:1521494",
     "ncaa:1521497",
     "ncaa:1521498",
     "ncaa:1521500",
     "ncaa:1521501",
     "ncaa:1521503",
     "ncaa:1521504",
     "ncaa:1521505",
     "ncaa:1521506",
     "ncaa:1521507",
     "ncaa:1521509",
     "ncaa:1521515",
     "ncaa:1521518",
     "ncaa:1521519",
     "ncaa:1521520",
     "ncaa:1521532",
     "ncaa:1521535",
     "ncaa:1521537",
     "ncaa:1521543",
     "ncaa:1521544",
     "ncaa:1521548",
     "ncaa:1521550",
     "ncaa:1521551",
     "ncaa:1521552",
     "ncaa:1521554",
     "ncaa:1521555",
     "ncaa:1521559",
     "ncaa:1521568",
     "ncaa:1521569",
     "ncaa:1521570",
     "ncaa:1521571",
     "ncaa:1521572",
     "ncaa:1521573",
     "ncaa:1521574",
     "ncaa:1521582",
     "ncaa:1521584",
     "ncaa:1521594",
     "ncaa:1521666",
     "ncaa:1521687",
     "ncaa:1521688",
     "ncaa:1521692",
     "ncaa:1569702"
    ],
    "2018-10-09": [
     "ncaa:1521703"
    ],
    "2018-10-11": [
     "ncaa:1521705",
     "ncaa:1521706"
    ],
    "2018-10-12": [
     "ncaa:1521707",
     "ncaa:1521709",
     "ncaa:1521710"
    ],
    "2018-10-13": [
     "ncaa:1521775",
     "ncaa:1521777",
     "ncaa:1521778",
     "ncaa:1521780",
     "ncaa:1521783",
     "ncaa:1521785",
     "ncaa:1521788",
     "ncaa:1521791",
     "ncaa:1521793",
     "ncaa:1521798",
     "ncaa:1521800",
     "ncaa:1521802",
     "ncaa:1521804",
     "ncaa:1521805",
     "ncaa:1521806",
     "ncaa:1521810",
     "ncaa:1521811",
     "ncaa:1521812",
     "ncaa:1521813",
     "ncaa:1521815",
     "ncaa:1521816",
     "ncaa:1521819",
     "ncaa:1521821",
     "ncaa:1521825",
     "ncaa:1521828",
     "ncaa:1521832",
     "ncaa:1521835",
     "ncaa:1521836",
     "ncaa:1521837",
     "ncaa:1521838",
     "ncaa:1521839",
     "ncaa:1521840",
     "ncaa:1521851",
     "ncaa:1521852",
     "ncaa:1521854",
     "ncaa:1521855",
     "ncaa:1521856",
     "ncaa:1521863",
     "ncaa:1521873",
     "ncaa:1521874",
     "ncaa:1521876",
     "ncaa:1521877",
     "ncaa:1521878",
     "ncaa:1521879",
     "ncaa:1521880",
     "ncaa:1521890",
     "ncaa:1521977"
    ],
    "2018-10-18": [
     "ncaa:1522013",
     "ncaa:1522014"
    ],
    "2018-10-19": [
     "ncaa:1522015",
     "ncaa:1522018"
    ],
    "2018-10-20": [
     "ncaa:1522076",
     "ncaa:1522080",
     "ncaa:1522085",
     "ncaa:1522086",
     "ncaa:1522087",
     "ncaa:1522088",
     "ncaa:1522094",
     "ncaa:1522099",
     "ncaa:1522102",
     "ncaa:1522103",
     "ncaa:1522105",
     "ncaa:1522107",
     "ncaa:1522108",
     "ncaa:1522109",
     "ncaa:1522110",
     "ncaa:1522111",
     "ncaa:1522113",
     "ncaa:1522130",
     "ncaa:1522132",
     "ncaa:1522135",
     "ncaa:1522137",
     "ncaa:1522138",
     "ncaa:1522139",
     "ncaa:1522143",
     "ncaa:1522146",
     "ncaa:1522147",
     "ncaa:1522149",
     "ncaa:1522150",
     "ncaa:1522154",
     "ncaa:1522155",
     "ncaa:1522163",
     "ncaa:1522164",
     "ncaa:1522165",
     "ncaa:1522166",
     "ncaa:1522167",
     "ncaa:1522168",
     "ncaa:1522169",
     "ncaa:1522170",
     "ncaa:1522171",
     "ncaa:1522172",
     "ncaa:1522173",
     "ncaa:1522174",
     "ncaa:1522175",
     "ncaa:1522182",
     "ncaa:1522288",
     "ncaa:1522290",
     "ncaa:1522292",
     "ncaa:1522309",
     "ncaa:1522310",
     "ncaa:1522321"
    ],
    "2018-10-23": [
     "ncaa:1522322"
    ],
    "2018-10-25": [
     "ncaa:1522323",
     "ncaa:1522324",
     "ncaa:1522326",
     "ncaa:1522327",
     "ncaa:1522328"
    ],
    "2018-10-26": [
     "ncaa:1522329",
     "ncaa:1522330",
     "ncaa:1522331",
     "ncaa:1522332",
     "ncaa:1522333"
    ],
    "2018-10-27": [
     "ncaa:1522334",
     "ncaa:1522335",
     "ncaa:1522401",
     "ncaa:1522404",
     "ncaa:1522405",
     "ncaa:1522406",
     "ncaa:1522408",
     "ncaa:1522413",
     "ncaa:1522416",
     "ncaa:1522417",
     "ncaa:1522420",
     "ncaa:1522421",
     "ncaa:1522423",
     "ncaa:1522424",
     "ncaa:1522426",
     "ncaa:1522427",
     "ncaa:1522430",
     "ncaa:1522431",
     "ncaa:1522432",
     "ncaa:1522433",
     "ncaa:1522436",
     "ncaa:1522438",
     "ncaa:1522440",
     "ncaa:1522441",
     "ncaa:1522449",
     "ncaa:1522451",
     "ncaa:1522452",
     "ncaa:1522453",
     "ncaa:1522466",
     "ncaa:1522467",
     "ncaa:1522468",
     "ncaa:1522473",
     "ncaa:1522478",
     "ncaa:1522480",
     "ncaa:1522481",
     "ncaa:1522494",
     "ncaa:1522495",
     "ncaa:1522496",
     "ncaa:1522497",
     "ncaa:1522498",
     "ncaa:1522499",
     "ncaa:1522510",
     "ncaa:1522511",
     "ncaa:1522624"
    ],
    "2018-10-30": [
     "ncaa:1522631",
     "ncaa:1522632"
    ],
    "2018-10-31": [
     "ncaa:1522633"
    ],
    "2018-11-01": [
     "ncaa:1522634",
     "ncaa:1522635",
     "ncaa:1522636"
    ],
    "2018-11-02": [
     "ncaa:1522637",
     "ncaa:1522638",
     "ncaa:1522641"
    ],
    "2018-11-03": [
     "ncaa:1522707",
     "ncaa:1522708",
     "ncaa:1522712",
     "ncaa:1522713",
     "ncaa:1522716",
     "ncaa:1522720",
     "ncaa:1522723",
     "ncaa:1522724",
     "ncaa:1522727",
     "ncaa:1522728",
     "ncaa:1522729",
     "ncaa:1522730",
     "ncaa:1522732",
     "ncaa:1522733",
     "ncaa:1522735",
     "ncaa:1522737",
     "ncaa:1522740",
     "ncaa:1522742",
     "ncaa:1522743",
     "ncaa:1522746",
     "ncaa:1522750",
     "ncaa:1522760",
     "ncaa:1522762",
     "ncaa:1522764",
     "ncaa:1522766",
     "ncaa:1522770",
     "ncaa:1522777",
     "ncaa:1522778",
     "ncaa:1522782",
     "ncaa:1522783",
     "ncaa:1522785",
     "ncaa:1522786",
     "ncaa:1522801",
     "ncaa:1522802",
     "ncaa:1522803",
     "ncaa:1522804",
     "ncaa:1522805",
     "ncaa:1522806",
     "ncaa:1522807",
     "ncaa:1522808",
     "ncaa:1522809",
     "ncaa:1522810",
     "ncaa:1522811",
     "ncaa:1522812",
     "ncaa:1522813",
     "ncaa:1522814",
     "ncaa:1522815",
     "ncaa:1522917",
     "ncaa:1522941",
     "ncaa:1522951",
     "ncaa:1636787"
    ],
    "2018-11-06": [
     "ncaa:1522954"
    ],
    "2018-11-07": [
     "ncaa:1522955",
     "ncaa:1522956"
    ],
    "2018-11-08": [
     "ncaa:1522957"
    ],
    "2018-11-09": [
     "ncaa:1522960",
     "ncaa:1522961"
    ],
    "2018-11-10": [
     "ncaa:1522963",
     "ncaa:1523041",
     "ncaa:1523044",
     "ncaa:1523046",
     "ncaa:1523047",
     "ncaa:1523048",
     "ncaa:1523049",
     "ncaa:1523053",
     "ncaa:1523056",
     "ncaa:1523058",
     "ncaa:1523059",
     "ncaa:1523064",
     "ncaa:1523066",
     "ncaa:1523067",
     "ncaa:1523069",
     "ncaa:1523073",
     "ncaa:1523075",
     "ncaa:1523077",
     "ncaa:1523078",
     "ncaa:1523079",
     "ncaa:1523080",
     "ncaa:1523082",
     "ncaa:1523083",
     "ncaa:1523084",
     "ncaa:1523092",
     "ncaa:1523093",
     "ncaa:1523094",
     "ncaa:1523106",
     "ncaa:1523107",
     "ncaa:1523108",
     "ncaa:1523110",
     "ncaa:1523111",
     "ncaa:1523112",
     "ncaa:1523116",
     "ncaa:1523118",
     "ncaa:1523121",
     "ncaa:1523122",
     "ncaa:1523123",
     "ncaa:1523124",
     "ncaa:1523126",
     "ncaa:1523129",
     "ncaa:1523130",
     "ncaa:1523131",
     "ncaa:1523138",
     "ncaa:1523139",
     "ncaa:1523140",
     "ncaa:1523141",
     "ncaa:1523142",
     "ncaa:1523143",
     "ncaa:1523144",
     "ncaa:1523145",
     "ncaa:1523146",
     "ncaa:1523147",
     "ncaa:1523264",
     "ncaa:1523268"
    ],
    "2018-11-13": [
     "ncaa:1523275"
    ],
    "2018-11-14": [
     "ncaa:1523276",
     "ncaa:1523277"
    ],
    "2018-11-15": [
     "ncaa:1523278",
     "ncaa:1523279",
     "ncaa:1523280"
    ],
    "2018-11-16": [
     "ncaa:1523284",
     "ncaa:1523286"
    ],
    "2018-11-17": [
     "ncaa:1523287",
     "ncaa:1523288",
     "ncaa:1523289",
     "ncaa:1523291",
     "ncaa:1523292",
     "ncaa:1523295",
     "ncaa:1523297",
     "ncaa:1523298",
     "ncaa:1523299",
     "ncaa:1523300",
     "ncaa:1523301",
     "ncaa:1523304",
     "ncaa:1523305",
     "ncaa:1523307",
     "ncaa:1523308",
     "ncaa:1523309",
     "ncaa:1523310",
     "ncaa:1523311",
     "ncaa:1523312",
     "ncaa:1523313",
     "ncaa:1523315",
     "ncaa:1523320",
     "ncaa:1523321",
     "ncaa:1523325",
     "ncaa:1523326",
     "ncaa:1523327",
     "ncaa:1523332",
     "ncaa:1523333",
     "ncaa:1523334",
     "ncaa:1523335",
     "ncaa:1523337",
     "ncaa:1523338",
     "ncaa:1523339",
     "ncaa:1523347",
     "ncaa:1523348",
     "ncaa:1523349",
     "ncaa:1523350",
     "ncaa:1523351",
     "ncaa:1523352",
     "ncaa:1523353",
     "ncaa:1523354",
     "ncaa:1523355",
     "ncaa:1523356",
     "ncaa:1523357",
     "ncaa:1523358",
     "ncaa:1523360",
     "ncaa:1523361",
     "ncaa:1523362",
     "ncaa:1523375",
     "ncaa:1523395",
     "ncaa:1523397",
     "ncaa:1523400"
    ],
    "2018-11-20": [
     "ncaa:1523401",
     "ncaa:1523402"
    ],
    "2018-11-22": [
     "ncaa:1523403",
     "ncaa:1523405"
    ],
    "2018-11-23": [
     "ncaa:1523406",
     "ncaa:1523407",
     "ncaa:1523408",
     "ncaa:1523409",
     "ncaa:1523410",
     "ncaa:1523411",
     "ncaa:1523412",
     "ncaa:1523413",
     "ncaa:1523414",
     "ncaa:1523415",
     "ncaa:1523416",
     "ncaa:1523417",
     "ncaa:1523418",
     "ncaa:1523419",
     "ncaa:1523420"
    ],
    "2018-11-24": [
     "ncaa:1523421",
     "ncaa:1523422",
     "ncaa:1523423",
     "ncaa:1523424",
     "ncaa:1523425",
     "ncaa:1523426",
     "ncaa:1523427",
     "ncaa:1523428",
     "ncaa:1523429",
     "ncaa:1523430",
     "ncaa:1523431",
     "ncaa:1523432",
     "ncaa:1523434",
     "ncaa:1523435",
     "ncaa:1523436",
     "ncaa:1523437",
     "ncaa:1523438",
     "ncaa:1523439",
     "ncaa:1523440",
     "ncaa:1523441",
     "ncaa:1523442",
     "ncaa:1523443",
     "ncaa:1523444",
     "ncaa:1523445",
     "ncaa:1523446",
     "ncaa:1523447",
     "ncaa:1523448",
     "ncaa:1523449",
     "ncaa:1523450",
     "ncaa:1523451",
     "ncaa:1523452",
     "ncaa:1523453",
     "ncaa:1523454",
     "ncaa:1523455",
     "ncaa:1523456",
     "ncaa:1523457",
     "ncaa:1523458",
     "ncaa:1523459",
     "ncaa:1523460",
     "ncaa:1523461",
     "ncaa:1523462",
     "ncaa:1523463",
     "ncaa:1523464",
     "ncaa:1523467",
     "ncaa:1646783"
    ],
    "2018-11-30": [
     "ncaa:1640722",
     "ncaa:1640741"
    ],
    "2018-12-01": [
     "ncaa:1523336",
     "ncaa:1569620",
     "ncaa:1636494",
     "ncaa:1640240",
     "ncaa:1640723",
     "ncaa:1640724",
     "ncaa:1640725",
     "ncaa:1640726",
     "ncaa:1640742",
     "ncaa:1640743",
     "ncaa:1640744",
     "ncaa:1640745"
    ],
    "2018-12-08": [
     "ncaa:1523468"
    ],
    "2018-12-15": [
     "ncaa:1641160",
     "ncaa:1641188",
     "ncaa:1641189",
     "ncaa:1641190",
     "ncaa:1641201"
    ],
    "2018-12-18": [
     "ncaa:1641191"
    ],
    "2018-12-19": [
     "ncaa:1641192"
    ],
    "2018-12-21": [
     "ncaa:1641199",
     "ncaa:1641205"
    ],
    "2018-12-22": [
     "ncaa:1641200",
     "ncaa:1641221",
     "ncaa:1641222"
    ],
    "2018-12-26": [
     "ncaa:1641212",
     "ncaa:1641224"
    ],
    "2018-12-27": [
     "ncaa:1641225",
     "ncaa:1641226",
     "ncaa:1641227"
    ],
    "2018-12-28": [
     "ncaa:1641213",
     "ncaa:1641214",
     "ncaa:1641228"
    ],
    "2018-12-29": [
     "ncaa:1641196",
     "ncaa:1641203",
     "ncaa:1641215",
     "ncaa:1641217",
     "ncaa:1641229"
    ],
    "2018-12-31": [
     "ncaa:1641218",
     "ncaa:1641219",
     "ncaa:1641220",
     "ncaa:1641230",
     "ncaa:1641241",
     "ncaa:1641242"
    ],
    "2019-01-01": [
     "ncaa:1641231",
     "ncaa:1641243",
     "ncaa:1641244",
     "ncaa:1641245",
     "ncaa:1641246"
    ],
    "2019-01-07": [
     "ncaa:1641204"
    ]
   },
   "2019": {
    "2019-08-24": [
     "ncaa:1735108",
     "ncaa:1735109"
    ],
    "2019-08-29": [
     "ncaa:1735118",
     "ncaa:1735121",
     "ncaa:1735123",
     "ncaa:1735135",
     "ncaa:1735138",
     "ncaa:1735139"
    ],
    "2019-08-30": [
     "ncaa:1735141",
     "ncaa:1735142",
     "ncaa:1735143",
     "ncaa:1735144",
     "ncaa:1735145",
     "ncaa:1735146",
     "ncaa:1735147",
     "ncaa:1735148"
    ],
    "2019-08-31": [
     "ncaa:1735149",
     "ncaa:1735150",
     "ncaa:1735151",
     "ncaa:1735156",
     "ncaa:1735158",
     "ncaa:1735159",
     "ncaa:1735160",
     "ncaa:1735162",
     "ncaa:1735169",
     "ncaa:1735176",
     "ncaa:1735179",
     "ncaa:1735180",
     "ncaa:1735183",
     "ncaa:1735187",
     "ncaa:1735188",
     "ncaa:1735193",
     "ncaa:1735201",
     "ncaa:1735210",
     "ncaa:1735211",
     "ncaa:1735212",
     "ncaa:1735215",
     "ncaa:1735217",
     "ncaa:1735223",
     "ncaa:1735224",
     "ncaa:1735225",
     "ncaa:1735226"
    ],
    "2019-09-01": [
     "ncaa:1735230"
    ],
    "2019-09-02": [
     "ncaa:1735231"
    ],
    "2019-09-06": [
     "ncaa:1735280",
     "ncaa:1735283"
    ],
    "2019-09-07": [
     "ncaa:1735294",
     "ncaa:1735295",
     "ncaa:1735296",
     "ncaa:1735297",
     "ncaa:1735298",
     "ncaa:1735310",
     "ncaa:1735311",
     "ncaa:1735313",
     "ncaa:1735314",
     "ncaa:1735321",
     "ncaa:1735327",
     "ncaa:1735399",
     "ncaa:1735403",
     "ncaa:1735421",
     "ncaa:1735423",
     "ncaa:1735424",
     "ncaa:1735425",
     "ncaa:1735426",
     "ncaa:1735428",
     "ncaa:1735429",
     "ncaa:1735435",
     "ncaa:1735437",
     "ncaa:1735454",
     "ncaa:1735471",
     "ncaa:1735473",
     "ncaa:1735491",
     "ncaa:1735500",
     "ncaa:1735501",
     "ncaa:1735503",
     "ncaa:1735504",
     "ncaa:1735516",
     "ncaa:1735519",
     "ncaa:1735520",
     "ncaa:1735528",
     "ncaa:1735532",
     "ncaa:1735533",
     "ncaa:1735534",
     "ncaa:1735535",
     "ncaa:1735536",
     "ncaa:1735538",
     "ncaa:1735541",
     "ncaa:1735542",
     "ncaa:1775433",
     "ncaa:1775441"
    ],
    "2019-09-13": [
     "ncaa:1735551",
     "ncaa:1735558",
     "ncaa:1735559"
    ],
    "2019-09-14": [
     "ncaa:1735563",
     "ncaa:1735566",
     "ncaa:1735567",
     "ncaa:1735585",
     "ncaa:1735586",
     "ncaa:1735587",
     "ncaa:1735588",
     "ncaa:1735590",
     "ncaa:1735601",
     "ncaa:1735679",
     "ncaa:1735685",
     "ncaa:1735695",
     "ncaa:1735702",
     "ncaa:1735703",
     "ncaa:1735704",
     "ncaa:1735705",
     "ncaa:1735706",
     "ncaa:1735707",
     "ncaa:1735710",
     "ncaa:1735711",
     "ncaa:1735715",
     "ncaa:1735718",
     "ncaa:1735719",
     "ncaa:1735720",
     "ncaa:1735723",
     "ncaa:1735729",
     "ncaa:1735730",
     "ncaa:1735735",
     "ncaa:1735737",
     "ncaa:1735738",
     "ncaa:1735751",
     "ncaa:1735765",
     "ncaa:1735766",
     "ncaa:1735768",
     "ncaa:1735772",
     "ncaa:1735773",
     "ncaa:1735809",
     "ncaa:1735827",
     "ncaa:1735829",
     "ncaa:1735841",
     "ncaa:1735844",
     "ncaa:1735845",
     "ncaa:1735847",
     "ncaa:1735848"
    ],
    "2019-09-19": [
     "ncaa:1735854"
    ],
    "2019-09-20": [
     "ncaa:1735857",
     "ncaa:1735860",
     "ncaa:1735861"
    ],
    "2019-09-21": [
     "ncaa:1735865",
     "ncaa:1735867",
     "ncaa:1735871",
     "ncaa:1735872",
     "ncaa:1735873",
     "ncaa:1735874",
     "ncaa:1735876",
     "ncaa:1735877",
     "ncaa:1735878",
     "ncaa:1735880",
     "ncaa:1735881",
     "ncaa:1735883",
     "ncaa:1735884",
     "ncaa:1735885",
     "ncaa:1735886",
     "ncaa:1735887",
     "ncaa:1735888",
     "ncaa:1735889",
     "ncaa:1735890",
     "ncaa:1735893",
     "ncaa:1735896",
     "ncaa:1735898",
     "ncaa:1735899",
     "ncaa:1735900",
     "ncaa:1735901",
     "ncaa:1735902",
     "ncaa:1735904",
     "ncaa:1735907",
     "ncaa:1735910",
     "ncaa:1735911",
     "ncaa:1735912",
     "ncaa:1735914",
     "ncaa:1735915",
     "ncaa:1735916",
     "ncaa:1735917",
     "ncaa:1735919",
     "ncaa:1735920",
     "ncaa:1736054",
     "ncaa:1736055",
     "ncaa:1736062",
     "ncaa:1736107",
     "ncaa:1736135",
     "ncaa:1736167",
     "ncaa:1736169",
     "ncaa:1778056"
    ],
    "2019-09-26": [
     "ncaa:1736172"
    ],
    "2019-09-27": [
     "ncaa:1736175",
     "ncaa:1736177",
     "ncaa:1736180",
     "ncaa:1736181"
    ],
    "2019-09-28": [
     "ncaa:1736184",
     "ncaa:1736187",
     "ncaa:1736189",
     "ncaa:1736190",
     "ncaa:1736191",
     "ncaa:1736192",
     "ncaa:1736194",
     "ncaa:1736197",
     "ncaa:1736198",
     "ncaa:1736199",
     "ncaa:1736200",
     "ncaa:1736202",
     "ncaa:1736203",
     "ncaa:1736204",
     "ncaa:1736205",
     "ncaa:1736207",
     "ncaa:1736208",
     "ncaa:1736210",
     "ncaa:1736211",
     "ncaa:1736213",
     "ncaa:1736218",
     "ncaa:1736220",
     "ncaa:1736221",
     "ncaa:1736222",
     "ncaa:1736223",
     "ncaa:1736224",
     "ncaa:1736228",
     "ncaa:1736233",
     "ncaa:1736234",
     "ncaa:1736235",
     "ncaa:1736236",
     "ncaa:1736237",
     "ncaa:1736383",
     "ncaa:1736385",
     "ncaa:1736387",
     "ncaa:1736401",
     "ncaa:1736402",
     "ncaa:1736404",
     "ncaa:1736421",
     "ncaa:1736423",
     "ncaa:1736427",
     "ncaa:1736429",
     "ncaa:1736430",
     "ncaa:1736431",
     "ncaa:1736445",
     "ncaa:1736456"
    ],
    "2019-10-03": [
     "ncaa:1736468",
     "ncaa:1736470"
    ],
    "2019-10-04": [
     "ncaa:1736472",
     "ncaa:1736474"
    ],
    "2019-10-05": [
     "ncaa:1736475",
     "ncaa:1736476",
     "ncaa:1736477",
     "ncaa:1736479",
     "ncaa:1736481",
     "ncaa:1736482",
     "ncaa:1736484",
     "ncaa:1736485",
     "ncaa:1736486",
     "ncaa:1736487",
     "ncaa:1736488",
     "ncaa:1736489",
     "ncaa:1736491",
     "ncaa:1736493",
     "ncaa:1736494",
     "ncaa:1736496",
     "ncaa:1736497",
     "ncaa:1736502",
     "ncaa:1736504",
     "ncaa:1736505",
     "ncaa:1736506",
     "ncaa:1736508",
     "ncaa:1736509",
     "ncaa:1736511",
     "ncaa:1736513",
     "ncaa:1736514",
     "ncaa:1736515",
     "ncaa:1736516",
     "ncaa:1736518",
     "ncaa:1736519",
     "ncaa:1736527",
     "ncaa:1736528",
     "ncaa:1736529",
     "ncaa:1736706",
     "ncaa:1736721",
     "ncaa:1736722",
     "ncaa:1736726",
     "ncaa:1736728",
     "ncaa:1736750",
     "ncaa:1736753",
     "ncaa:1736754",
     "ncaa:1736771",
     "ncaa:1736777",
     "ncaa:1736778"
    ],
    "2019-10-09": [
     "ncaa:1736779"
    ],
    "2019-10-10": [
     "ncaa:1736781",
     "ncaa:1736782"
    ],
    "2019-10-11": [
     "ncaa:1736783",
     "ncaa:1736785",
     "ncaa:1736787"
    ],
    "2019-10-12": [
     "ncaa:1736789",
     "ncaa:1736791",
     "ncaa:1736794",
     "ncaa:1736795",
     "ncaa:1736797",
     "ncaa:1736799",
     "ncaa:1736801",
     "ncaa:1736802",
     "ncaa:1736803",
     "ncaa:1736804",
     "ncaa:1736807",
     "ncaa:1736809",
     "ncaa:1736813",
     "ncaa:1736814",
     "ncaa:1736816",
     "ncaa:1736817",
     "ncaa:1736818",
     "ncaa:1736819",
     "ncaa:1736820",
     "ncaa:1736821",
     "ncaa:1736826",
     "ncaa:1736827",
     "ncaa:1736828",
     "ncaa:1736829",
     "ncaa:1736830",
     "ncaa:1736831",
     "ncaa:1736832",
     "ncaa:1736833",
     "ncaa:1736834",
     "ncaa:1736851",
     "ncaa:1736852",
     "ncaa:1736912",
     "ncaa:1737010",
     "ncaa:1737023",
     "ncaa:1737026",
     "ncaa:1737030",
     "ncaa:1737031",
     "ncaa:1737039",
     "ncaa:1737044",
     "ncaa:1737045",
     "ncaa:1737053",
     "ncaa:1737060",
     "ncaa:1737062",
     "ncaa:1737079",
     "ncaa:1737084",
     "ncaa:1737085"
    ],
    "2019-10-16": [
     "ncaa:1737087"
    ],
    "2019-10-17": [
     "ncaa:1737088",
     "ncaa:1737089"
    ],
    "2019-10-18": [
     "ncaa:1737091",
     "ncaa:1737092",
     "ncaa:1737093",
     "ncaa:1737095"
    ],
    "2019-10-19": [
     "ncaa:1737097",
     "ncaa:1737098",
     "ncaa:1737100",
     "ncaa:1737101",
     "ncaa:1737102",
     "ncaa:1737104",
     "ncaa:1737105",
     "ncaa:1737108",
     "ncaa:1737111",
     "ncaa:1737112",
     "ncaa:1737114",
     "ncaa:1737115",
     "ncaa:1737116",
     "ncaa:1737118",
     "ncaa:1737119",
     "ncaa:1737120",
     "ncaa:1737121",
     "ncaa:1737122",
     "ncaa:1737123",
     "ncaa:1737124",
     "ncaa:1737126",
     "ncaa:1737129",
     "ncaa:1737130",
     "ncaa:1737134",
     "ncaa:1737135",
     "ncaa:1737136",
     "ncaa:1737137",
     "ncaa:1737138",
     "ncaa:1737139",
     "ncaa:1737141",
     "ncaa:1737143",
     "ncaa:1737145",
     "ncaa:1737146",
     "ncaa:1737147",
     "ncaa:1737148",
     "ncaa:1737149",
     "ncaa:1737150",
     "ncaa:1737151",
     "ncaa:1737153",
     "ncaa:1737154",
     "ncaa:1737155",
     "ncaa:1737156",
     "ncaa:1737326",
     "ncaa:1737335",
     "ncaa:1737349",
     "ncaa:1737352",
     "ncaa:1737358",
     "ncaa:1737359",
     "ncaa:1737368",
     "ncaa:1737370",
     "ncaa:1737377",
     "ncaa:1737389",
     "ncaa:1737390",
     "ncaa:1737414"
    ],
    "2019-10-24": [
     "ncaa:1737417"
    ],
    "2019-10-25": [
     "ncaa:1737420"
    ],
    "2019-10-26": [
     "ncaa:1737423",
     "ncaa:1737424",
     "ncaa:1737425",
     "ncaa:1737427",
     "ncaa:1737428",
     "ncaa:1737429",
     "ncaa:1737430",
     "ncaa:1737432",
     "ncaa:1737433",
     "ncaa:1737436",
     "ncaa:1737438",
     "ncaa:1737439",
     "ncaa:1737440",
     "ncaa:1737441",
     "ncaa:1737443",
     "ncaa:1737444",
     "ncaa:1737446",
     "ncaa:1737447",
     "ncaa:1737449",
     "ncaa:1737450",
     "ncaa:1737452",
     "ncaa:1737453",
     "ncaa:1737454",
     "ncaa:1737457",
     "ncaa:1737458",
     "ncaa:1737459",
     "ncaa:1737460",
     "ncaa:1737461",
     "ncaa:1737462",
     "ncaa:1737463",
     "ncaa:1737464",
     "ncaa:1737465",
     "ncaa:1737467",
     "ncaa:1737468",
     "ncaa:1737471",
     "ncaa:1737473",
     "ncaa:1737475",
     "ncaa:1737476",
     "ncaa:1737478",
     "ncaa:1737488",
     "ncaa:1737489",
     "ncaa:1737491",
     "ncaa:1737506",
     "ncaa:1737664",
     "ncaa:1737687",
     "ncaa:1737688",
     "ncaa:1737689",
     "ncaa:1737690",
     "ncaa:1737706",
     "ncaa:1737707",
     "ncaa:1737730",
     "ncaa:1737732",
     "ncaa:1737739"
    ],
    "2019-10-31": [
     "ncaa:1737742",
     "ncaa:1737744"
    ],
    "2019-11-01": [
     "ncaa:1737747"
    ],
    "2019-11-02": [
     "ncaa:1737750",
     "ncaa:1737751",
     "ncaa:1737752",
     "ncaa:1737753",
     "ncaa:1737755",
     "ncaa:1737757",
     "ncaa:1737758",
     "ncaa:1737760",
     "ncaa:1737761",
     "ncaa:1737763",
     "ncaa:1737764",
     "ncaa:1737765",
     "ncaa:1737766",
     "ncaa:1737767",
     "ncaa:1737769",
     "ncaa:1737770",
     "ncaa:1737773",
     "ncaa:1737774",
     "ncaa:1737775",
     "ncaa:1737776",
     "ncaa:1737777",
     "ncaa:1737780",
     "ncaa:1737785",
     "ncaa:1737786",
     "ncaa:1737788",
     "ncaa:1737789",
     "ncaa:1737791",
     "ncaa:1737792",
     "ncaa:1737794",
     "ncaa:1737797",
     "ncaa:1737798",
     "ncaa:1737799",
     "ncaa:1737810",
     "ncaa:1737814",
     "ncaa:1737970",
     "ncaa:1738014",
     "ncaa:1738015",
     "ncaa:1738016",
     "ncaa:1738017",
     "ncaa:1738021",
     "ncaa:1738024",
     "ncaa:1738034",
     "ncaa:1738041",
     "ncaa:1738051"
    ],
    "2019-11-05": [
     "ncaa:1738053",
     "ncaa:1738054"
    ],
    "2019-11-06": [
     "ncaa:1738055"
    ],
    "2019-11-07": [
     "ncaa:1738058",
     "ncaa:1738059"
    ],
    "2019-11-08": [
     "ncaa:1738060",
     "ncaa:1738061"
    ],
    "2019-11-09": [
     "ncaa:1738064",
     "ncaa:1738066",
     "ncaa:1738069",
     "ncaa:1738070",
     "ncaa:1738071",
     "ncaa:1738072",
     "ncaa:1738074",
     "ncaa:1738076",
     "ncaa:1738078",
     "ncaa:1738079",
     "ncaa:1738082",
     "ncaa:1738083",
     "ncaa:1738085",
     "ncaa:1738087",
     "ncaa:1738089",
     "ncaa:1738090",
     "ncaa:1738091",
     "ncaa:1738098",
     "ncaa:1738100",
     "ncaa:1738101",
     "ncaa:1738102",
     "ncaa:1738103",
     "ncaa:1738105",
     "ncaa:1738106",
     "ncaa:1738107",
     "ncaa:1738109",
     "ncaa:1738110",
     "ncaa:1738112",
     "ncaa:1738115",
     "ncaa:1738116",
     "ncaa:1738118",
     "ncaa:1738120",
     "ncaa:1738146",
     "ncaa:1738250",
     "ncaa:1738321",
     "ncaa:1738342",
     "ncaa:1738343",
     "ncaa:1738344",
     "ncaa:1738358",
     "ncaa:1738368",
     "ncaa:1738371"
    ],
    "2019-11-12": [
     "ncaa:1738380",
     "ncaa:1738381"
    ],
    "2019-11-13": [
     "ncaa:1738382",
     "ncaa:1738383"
    ],
    "2019-11-14": [
     "ncaa:1738385",
     "ncaa:1738386"
    ],
    "2019-11-15": [
     "ncaa:1738387",
     "ncaa:1738388"
    ],
    "2019-11-16": [
     "ncaa:1738392",
     "ncaa:1738394",
     "ncaa:1738395",
     "ncaa:1738397",
     "ncaa:1738398",
     "ncaa:1738399",
     "ncaa:1738401",
     "ncaa:1738402",
     "ncaa:1738403",
     "ncaa:1738405",
     "ncaa:1738408",
     "ncaa:1738409",
     "ncaa:1738410",
     "ncaa:1738411",
     "ncaa:1738412",
     "ncaa:1738413",
     "ncaa:1738414",
     "ncaa:1738415",
     "ncaa:1738416",
     "ncaa:1738421",
     "ncaa:1738422",
     "ncaa:1738424",
     "ncaa:1738425",
     "ncaa:1738427",
     "ncaa:1738429",
     "ncaa:1738430",
     "ncaa:1738431",
     "ncaa:1738432",
     "ncaa:1738433",
     "ncaa:1738435",
     "ncaa:1738436",
     "ncaa:1738440",
     "ncaa:1738441",
     "ncaa:1738444",
     "ncaa:1738445",
     "ncaa:1738446",
     "ncaa:1738447",
     "ncaa:1738567",
     "ncaa:1738661",
     "ncaa:1738672",
     "ncaa:1738677",
     "ncaa:1738682",
     "ncaa:1816292"
    ],
    "2019-11-19": [
     "ncaa:1738686",
     "ncaa:1738687"
    ],
    "2019-11-20": [
     "ncaa:1738688",
     "ncaa:1738689"
    ],
    "2019-11-21": [
     "ncaa:1738692"
    ],
    "2019-11-22": [
     "ncaa:1738694"
    ],
    "2019-11-23": [
     "ncaa:1738148",
     "ncaa:1738700",
     "ncaa:1738701",
     "ncaa:1738703",
     "ncaa:1738706",
     "ncaa:1738707",
     "ncaa:1738708",
     "ncaa:1738709",
     "ncaa:1738710",
     "ncaa:1738711",
     "ncaa:1738712",
     "ncaa:1738713",
     "ncaa:1738714",
     "ncaa:1738716",
     "ncaa:1738718",
     "ncaa:1738719",
     "ncaa:1738721",
     "ncaa:1738722",
     "ncaa:1738724",
     "ncaa:1738726",
     "ncaa:1738728",
     "ncaa:1738733",
     "ncaa:1738734",
     "ncaa:1738735",
     "ncaa:1738738",
     "ncaa:1738739",
     "ncaa:1738742",
     "ncaa:1738744",
     "ncaa:1738745",
     "ncaa:1738746",
     "ncaa:1738749",
     "ncaa:1738752",
     "ncaa:1738753",
     "ncaa:1738758",
     "ncaa:1738759",
     "ncaa:1738760",
     "ncaa:1738762",
     "ncaa:1738780",
     "ncaa:1738803",
     "ncaa:1738807",
     "ncaa:1738811",
     "ncaa:1738812",
     "ncaa:1738813",
     "ncaa:1738814",
     "ncaa:1738817",
     "ncaa:1738818",
     "ncaa:1738819",
     "ncaa:1738820",
     "ncaa:1738821",
     "ncaa:1738822",
     "ncaa:1738824"
    ],
    "2019-11-26": [
     "ncaa:1738825",
     "ncaa:1738826"
    ],
    "2019-11-28": [
     "ncaa:1738828"
    ],
    "2019-11-29": [
     "ncaa:1738829",
     "ncaa:1738831",
     "ncaa:1738832",
     "ncaa:1738833",
     "ncaa:1738834",
     "ncaa:1738835",
     "ncaa:1738836",
     "ncaa:1738837",
     "ncaa:1738838",
     "ncaa:1738839",
     "ncaa:1738840",
     "ncaa:1738841",
     "ncaa:1738842",
     "ncaa:1738843",
     "ncaa:1738844"
    ],
    "2019-11-30": [
     "ncaa:1738845",
     "ncaa:1738847",
     "ncaa:1738848",
     "ncaa:1738849",
     "ncaa:1738850",
     "ncaa:1738853",
     "ncaa:1738854",
     "ncaa:1738855",
     "ncaa:1738856",
     "ncaa:1738857",
     "ncaa:1738858",
     "ncaa:1738859",
     "ncaa:1738860",
     "ncaa:1738861",
     "ncaa:1738862",
     "ncaa:1738863",
     "ncaa:1738864",
     "ncaa:1738865",
     "ncaa:1738866",
     "ncaa:1738868",
     "ncaa:1738869",
     "ncaa:1738870",
     "ncaa:1738871",
     "ncaa:1738873",
     "ncaa:1738874",
     "ncaa:1738875",
     "ncaa:1738876",
     "ncaa:1738877",
     "ncaa:1738879",
     "ncaa:1738880",
     "ncaa:1738881",
     "ncaa:1738882",
     "ncaa:1738883",
     "ncaa:1738884",
     "ncaa:1738885",
     "ncaa:1738886",
     "ncaa:1738887",
     "ncaa:1738888",
     "ncaa:1738889",
     "ncaa:1738890",
     "ncaa:1738891",
     "ncaa:1738892",
     "ncaa:1738893",
     "ncaa:1738895",
     "ncaa:1738896",
     "ncaa:1817565"
    ],
    "2019-12-06": [
     "ncaa:1817927"
    ],
    "2019-12-07": [
     "ncaa:1817890",
     "ncaa:1817928",
     "ncaa:1817929",
     "ncaa:1817930",
     "ncaa:1817931",
     "ncaa:1817932",
     "ncaa:1817933",
     "ncaa:1817934",
     "ncaa:1817935"
    ],
    "2019-12-14": [
     "ncaa:1738897"
    ],
    "2019-12-20": [
     "ncaa:1818272",
     "ncaa:1818288"
    ],
    "2019-12-21": [
     "ncaa:1818289",
     "ncaa:1818290",
     "ncaa:1818293",
     "ncaa:1818294",
     "ncaa:1818295",
     "ncaa:1821126"
    ],
    "2019-12-23": [
     "ncaa:1818273"
    ],
    "2019-12-26": [
     "ncaa:1818296",
     "ncaa:1818297"
    ],
    "2019-12-27": [
     "ncaa:1818275",
     "ncaa:1818276",
     "ncaa:1818298",
     "ncaa:1818299",
     "ncaa:1818300"
    ],
    "2019-12-28": [
     "ncaa:1818271",
     "ncaa:1818277",
     "ncaa:1818278",
     "ncaa:1818287"
    ],
    "2019-12-30": [
     "ncaa:1818279",
     "ncaa:1818280",
     "ncaa:1818281",
     "ncaa:1818301"
    ],
    "2019-12-31": [
     "ncaa:1818282",
     "ncaa:1818283",
     "ncaa:1818284",
     "ncaa:1818302",
     "ncaa:1818303"
    ],
    "2020-01-01": [
     "ncaa:1818285",
     "ncaa:1818305",
     "ncaa:1818306"
    ],
    "2020-01-02": [
     "ncaa:1818326",
     "ncaa:1818327"
    ],
    "2020-01-03": [
     "ncaa:1818307"
    ],
    "2020-01-04": [
     "ncaa:1818308"
    ],
    "2020-01-06": [
     "ncaa:1818328"
    ],
    "2020-01-13": [
     "ncaa:1818270"
    ]
   },
   "2020": {
    "2020-09-03": [
     "ncaa:1974069"
    ],
    "2020-09-05": [
     "ncaa:1974072",
     "ncaa:1974074",
     "ncaa:1974077"
    ],
    "2020-09-07": [
     "ncaa:1974079"
    ],
    "2020-09-10": [
     "ncaa:1974080"
    ],
    "2020-09-12": [
     "ncaa:1974082",
     "ncaa:1974083",
     "ncaa:1974085",
     "ncaa:1974088",
     "ncaa:1974089",
     "ncaa:1974095",
     "ncaa:1974096",
     "ncaa:1974099",
     "ncaa:1974100",
     "ncaa:1974101",
     "ncaa:1974102",
     "ncaa:3146400"
    ],
    "2020-09-19": [
     "ncaa:1974106",
     "ncaa:1974107",
     "ncaa:1974108",
     "ncaa:1974109",
     "ncaa:1974110",
     "ncaa:1974112",
     "ncaa:1974113",
     "ncaa:1974115",
     "ncaa:1974118",
     "ncaa:1974121",
     "ncaa:1974123",
     "ncaa:1974124",
     "ncaa:1974125",
     "ncaa:1976910",
     "ncaa:1976911"
    ],
    "2020-09-24": [
     "ncaa:1974156"
    ],
    "2020-09-25": [
     "ncaa:1974160"
    ],
    "2020-09-26": [
     "ncaa:1974094",
     "ncaa:1974131",
     "ncaa:1974133",
     "ncaa:1974134",
     "ncaa:1974136",
     "ncaa:1974137",
     "ncaa:1974138",
     "ncaa:1974139",
     "ncaa:1974142",
     "ncaa:1974143",
     "ncaa:1974144",
     "ncaa:1974145",
     "ncaa:1974149",
     "ncaa:1974150",
     "ncaa:1974151",
     "ncaa:1974152",
     "ncaa:1974153",
     "ncaa:1974165",
     "ncaa:1974383",
     "ncaa:1974640",
     "ncaa:1975988",
     "ncaa:1976751",
     "ncaa:1976890",
     "ncaa:1976912",
     "ncaa:1976933"
    ],
    "2020-10-02": [
     "ncaa:1976935"
    ],
    "2020-10-03": [
     "ncaa:1974166",
     "ncaa:1974167",
     "ncaa:1974168",
     "ncaa:1974169",
     "ncaa:1974170",
     "ncaa:1974171",
     "ncaa:1974172",
     "ncaa:1974173",
     "ncaa:1974174",
     "ncaa:1974175",
     "ncaa:1974176",
     "ncaa:1974177",
     "ncaa:1974178",
     "ncaa:1974180",
     "ncaa:1974181",
     "ncaa:1974183",
     "ncaa:1974184",
     "ncaa:1974185",
     "ncaa:1974186",
     "ncaa:1974188",
     "ncaa:1974189",
     "ncaa:1974191",
     "ncaa:1974192",
     "ncaa:1974193",
     "ncaa:1974195",
     "ncaa:1974200",
     "ncaa:1976753"
    ],
    "2020-10-08": [
     "ncaa:1974202"
    ],
    "2020-10-09": [
     "ncaa:1974204"
    ],
    "2020-10-10": [
     "ncaa:1974155",
     "ncaa:1974203",
     "ncaa:1974205",
     "ncaa:1974206",
     "ncaa:1974207",
     "ncaa:1974209",
     "ncaa:1974211",
     "ncaa:1974213",
     "ncaa:1974214",
     "ncaa:1974215",
     "ncaa:1974216",
     "ncaa:1974217",
     "ncaa:1974218",
     "ncaa:1974219",
     "ncaa:1974220",
     "ncaa:1974221",
     "ncaa:1974222",
     "ncaa:1974224",
     "ncaa:1974225",
     "ncaa:1974226",
     "ncaa:1974232",
     "ncaa:1977208",
     "ncaa:1977896",
     "ncaa:1977898"
    ],
    "2020-10-14": [
     "ncaa:1974242"
    ],
    "2020-10-15": [
     "ncaa:1974235"
    ],
    "2020-10-16": [
     "ncaa:1974237",
     "ncaa:1974260"
    ],
    "2020-10-17": [
     "ncaa:1974236",
     "ncaa:1974238",
     "ncaa:1974239",
     "ncaa:1974241",
     "ncaa:1974243",
     "ncaa:1974245",
     "ncaa:1974246",
     "ncaa:1974247",
     "ncaa:1974248",
     "ncaa:1974250",
     "ncaa:1974251",
     "ncaa:1974252",
     "ncaa:1974256",
     "ncaa:1974257",
     "ncaa:1974258",
     "ncaa:1974259",
     "ncaa:1974262",
     "ncaa:1974263",
     "ncaa:1974265",
     "ncaa:1974267",
     "ncaa:1977005",
     "ncaa:1977269",
     "ncaa:1977899"
    ],
    "2020-10-22": [
     "ncaa:1974299"
    ],
    "2020-10-23": [
     "ncaa:1974272",
     "ncaa:1974273",
     "ncaa:1976151"
    ],
    "2020-10-24": [
     "ncaa:1974234",
     "ncaa:1974271",
     "ncaa:1974274",
     "ncaa:1974275",
     "ncaa:1974276",
     "ncaa:1974278",
     "ncaa:1974280",
     "ncaa:1974281",
     "ncaa:1974282",
     "ncaa:1974283",
     "ncaa:1974284",
     "ncaa:1974285",
     "ncaa:1974286",
     "ncaa:1974287",
     "ncaa:1974288",
     "ncaa:1974289",
     "ncaa:1974290",
     "ncaa:1974291",
     "ncaa:1974293",
     "ncaa:1974295",
     "ncaa:1974296",
     "ncaa:1974297",
     "ncaa:1974298",
     "ncaa:1974300",
     "ncaa:1974301",
     "ncaa:1974302",
     "ncaa:1974323",
     "ncaa:1975265",
     "ncaa:1976128",
     "ncaa:1976161",
     "ncaa:1976256",
     "ncaa:1976319",
     "ncaa:1976331",
     "ncaa:1976689",
     "ncaa:1976731",
     "ncaa:1976928",
     "ncaa:1976995",
     "ncaa:1977268",
     "ncaa:1977897",
     "ncaa:1987800"
    ],
    "2020-10-29": [
     "ncaa:1974307",
     "ncaa:1976788"
    ],
    "2020-10-30": [
     "ncaa:1974305",
     "ncaa:1976690",
     "ncaa:1977808"
    ],
    "2020-10-31": [
     "ncaa:1974277",
     "ncaa:1974294",
     "ncaa:1974304",
     "ncaa:1974306",
     "ncaa:1974308",
     "ncaa:1974309",
     "ncaa:1974310",
     "ncaa:1974311",
     "ncaa:1974312",
     "ncaa:1974313",
     "ncaa:1974314",
     "ncaa:1974315",
     "ncaa:1974316",
     "ncaa:1974317",
     "ncaa:1974318",
     "ncaa:1974319",
     "ncaa:1974320",
     "ncaa:1974321",
     "ncaa:1974324",
     "ncaa:1974325",
     "ncaa:1974326",
     "ncaa:1974327",
     "ncaa:1974328",
     "ncaa:1974329",
     "ncaa:1974330",
     "ncaa:1974331",
     "ncaa:1974332",
     "ncaa:1974333",
     "ncaa:1974336",
     "ncaa:1976129",
     "ncaa:1976162",
     "ncaa:1976332",
     "ncaa:1976732",
     "ncaa:1976929",
     "ncaa:1977229",
     "ncaa:1977872",
     "ncaa:1993430"
    ],
    "2020-11-04": [
     "ncaa:1976946",
     "ncaa:1977048",
     "ncaa:1977171",
     "ncaa:1977533",
     "ncaa:1977695",
     "ncaa:1977708"
    ],
    "2020-11-05": [
     "ncaa:1976930",
     "ncaa:1977548"
    ],
    "2020-11-06": [
     "ncaa:1974340",
     "ncaa:1976733",
     "ncaa:1977232"
    ],
    "2020-11-07": [
     "ncaa:1974338",
     "ncaa:1974339",
     "ncaa:1974341",
     "ncaa:1974342",
     "ncaa:1974345",
     "ncaa:1974346",
     "ncaa:1974347",
     "ncaa:1974348",
     "ncaa:1974349",
     "ncaa:1974351",
     "ncaa:1974354",
     "ncaa:1974355",
     "ncaa:1974356",
     "ncaa:1974357",
     "ncaa:1974358",
     "ncaa:1974359",
     "ncaa:1974360",
     "ncaa:1974362",
     "ncaa:1974363",
     "ncaa:1974364",
     "ncaa:1974370",
     "ncaa:1974371",
     "ncaa:1976130",
     "ncaa:1976163",
     "ncaa:1976315",
     "ncaa:1976325",
     "ncaa:1976691",
     "ncaa:1976748",
     "ncaa:1976789",
     "ncaa:1976945",
     "ncaa:1976968",
     "ncaa:1977088",
     "ncaa:1977869",
     "ncaa:1987075",
     "ncaa:1987088",
     "ncaa:1987168",
     "ncaa:1993431"
    ],
    "2020-11-10": [
     "ncaa:1977049",
     "ncaa:1977534",
     "ncaa:1977768"
    ],
    "2020-11-11": [
     "ncaa:1976947",
     "ncaa:1977113",
     "ncaa:1977696"
    ],
    "2020-11-12": [
     "ncaa:1976710"
    ],
    "2020-11-13": [
     "ncaa:1974373",
     "ncaa:1974404",
     "ncaa:1976164"
    ],
    "2020-11-14": [
     "ncaa:1974353",
     "ncaa:1974374",
     "ncaa:1974377",
     "ncaa:1974378",
     "ncaa:1974379",
     "ncaa:1974380",
     "ncaa:1974381",
     "ncaa:1974384",
     "ncaa:1974386",
     "ncaa:1974387",
     "ncaa:1974388",
     "ncaa:1974390",
     "ncaa:1974391",
     "ncaa:1974393",
     "ncaa:1974395",
     "ncaa:1974397",
     "ncaa:1974398",
     "ncaa:1974399",
     "ncaa:1974402",
     "ncaa:1974405",
     "ncaa:1976154",
     "ncaa:1976252",
     "ncaa:1976268",
     "ncaa:1976326",
     "ncaa:1976692",
     "ncaa:1976768",
     "ncaa:1976790",
     "ncaa:1976941",
     "ncaa:1976969",
     "ncaa:1977070",
     "ncaa:1977156",
     "ncaa:1993432"
    ],
    "2020-11-15": [
     "ncaa:1989339"
    ],
    "2020-11-17": [
     "ncaa:1976998",
     "ncaa:1977535"
    ],
    "2020-11-18": [
     "ncaa:1977114",
     "ncaa:1977930",
     "ncaa:1991692"
    ],
    "2020-11-19": [
     "ncaa:1974429"
    ],
    "2020-11-20": [
     "ncaa:1974406",
     "ncaa:1976253",
     "ncaa:1976871",
     "ncaa:1990060"
    ],
    "2020-11-21": [
     "ncaa:1974408",
     "ncaa:1974409",
     "ncaa:1974410",
     "ncaa:1974411",
     "ncaa:1974413",
     "ncaa:1974414",
     "ncaa:1974417",
     "ncaa:1974419",
     "ncaa:1974420",
     "ncaa:1974422",
     "ncaa:1974423",
     "ncaa:1974424",
     "ncaa:1974425",
     "ncaa:1974426",
     "ncaa:1974427",
     "ncaa:1974431",
     "ncaa:1974432",
     "ncaa:1974434",
     "ncaa:1974435",
     "ncaa:1974437",
     "ncaa:1976132",
     "ncaa:1976155",
     "ncaa:1976165",
     "ncaa:1976201",
     "ncaa:1976694",
     "ncaa:1976749",
     "ncaa:1976931",
     "ncaa:1976937",
     "ncaa:1976956",
     "ncaa:1977089",
     "ncaa:1993779"
    ],
    "2020-11-26": [
     "ncaa:1976820"
    ],
    "2020-11-27": [
     "ncaa:1974442",
     "ncaa:1974443",
     "ncaa:1974448",
     "ncaa:1976166",
     "ncaa:1976939",
     "ncaa:1976953",
     "ncaa:1976989",
     "ncaa:1977158",
     "ncaa:1977353"
    ],
    "2020-11-28": [
     "ncaa:1974254",
     "ncaa:1974400",
     "ncaa:1974441",
     "ncaa:1974445",
     "ncaa:1974446",
     "ncaa:1974447",
     "ncaa:1974451",
     "ncaa:1974452",
     "ncaa:1974453",
     "ncaa:1974458",
     "ncaa:1974460",
     "ncaa:1974461",
     "ncaa:1974462",
     "ncaa:1974463",
     "ncaa:1974467",
     "ncaa:1974468",
     "ncaa:1974469",
     "ncaa:1974470",
     "ncaa:1974471",
     "ncaa:1974474",
     "ncaa:1976254",
     "ncaa:1976317",
     "ncaa:1976323",
     "ncaa:1976333",
     "ncaa:1976693",
     "ncaa:1977050",
     "ncaa:1977082",
     "ncaa:1977172",
     "ncaa:1977188",
     "ncaa:1977536",
     "ncaa:1977975",
     "ncaa:1993399",
     "ncaa:1993433",
     "ncaa:1993436"
    ],
    "2020-12-03": [
     "ncaa:1974352",
     "ncaa:1977230"
    ],
    "2020-12-04": [
     "ncaa:1974201"
    ],
    "2020-12-05": [
     "ncaa:1974190",
     "ncaa:1974361",
     "ncaa:1974396",
     "ncaa:1974401",
     "ncaa:1974457",
     "ncaa:1974465",
     "ncaa:1974476",
     "ncaa:1974477",
     "ncaa:1974478",
     "ncaa:1974479",
     "ncaa:1974481",
     "ncaa:1974482",
     "ncaa:1974483",
     "ncaa:1974484",
     "ncaa:1974485",
     "ncaa:1974487",
     "ncaa:1974489",
     "ncaa:1974491",
     "ncaa:1976134",
     "ncaa:1976167",
     "ncaa:1976168",
     "ncaa:1976250",
     "ncaa:1976316",
     "ncaa:1976628",
     "ncaa:1976793",
     "ncaa:1976940",
     "ncaa:1976944",
     "ncaa:1976954",
     "ncaa:1976990",
     "ncaa:1976999",
     "ncaa:1977155",
     "ncaa:1977189",
     "ncaa:1977250",
     "ncaa:1977722",
     "ncaa:1977991",
     "ncaa:1987128",
     "ncaa:1993591",
     "ncaa:1994247"
    ],
    "2020-12-06": [
     "ncaa:1974456",
     "ncaa:1976770"
    ],
    "2020-12-10": [
     "ncaa:1974208",
     "ncaa:1974382"
    ],
    "2020-12-11": [
     "ncaa:1974335",
     "ncaa:1977388"
    ],
    "2020-12-12": [
     "ncaa:1974116",
     "ncaa:1974119",
     "ncaa:1974227",
     "ncaa:1974233",
     "ncaa:1974244",
     "ncaa:1974255",
     "ncaa:1974392",
     "ncaa:1974394",
     "ncaa:1974459",
     "ncaa:1974480",
     "ncaa:1974486",
     "ncaa:1974488",
     "ncaa:1974495",
     "ncaa:1976157",
     "ncaa:1976202",
     "ncaa:1976251",
     "ncaa:1976318",
     "ncaa:1976696",
     "ncaa:1976736",
     "ncaa:1976771",
     "ncaa:1976943",
     "ncaa:1976970",
     "ncaa:1977000",
     "ncaa:1977028",
     "ncaa:1977115",
     "ncaa:1977173",
     "ncaa:1993407",
     "ncaa:1994020",
     "ncaa:1995153",
     "ncaa:1995237"
    ],
    "2020-12-18": [
     "ncaa:1976772",
     "ncaa:1995296",
     "ncaa:1995297",
     "ncaa:1995298"
    ],
    "2020-12-19": [
     "ncaa:1974368",
     "ncaa:1974376",
     "ncaa:1974493",
     "ncaa:1974494",
     "ncaa:1994305",
     "ncaa:1994306",
     "ncaa:1994815",
     "ncaa:1994833",
     "ncaa:1994834",
     "ncaa:1995226",
     "ncaa:1995538",
     "ncaa:1995539",
     "ncaa:1995541",
     "ncaa:1995550"
    ],
    "2020-12-21": [
     "ncaa:1995542"
    ],
    "2020-12-22": [
     "ncaa:1995581",
     "ncaa:1995582"
    ],
    "2020-12-23": [
     "ncaa:1995583",
     "ncaa:1995584"
    ],
    "2020-12-24": [
     "ncaa:1995608"
    ],
    "2020-12-25": [
     "ncaa:1995962"
    ],
    "2020-12-26": [
     "ncaa:1995558",
     "ncaa:1995609",
     "ncaa:1995964"
    ],
    "2020-12-29": [
     "ncaa:1995965",
     "ncaa:1995966"
    ],
    "2020-12-30": [
     "ncaa:1995967",
     "ncaa:1996505"
    ],
    "2020-12-31": [
     "ncaa:1995970",
     "ncaa:1995971",
     "ncaa:1995972"
    ],
    "2021-01-01": [
     "ncaa:1995939",
     "ncaa:1995959",
     "ncaa:1995961",
     "ncaa:1995973"
    ],
    "2021-01-02": [
     "ncaa:1995974",
     "ncaa:1995975",
     "ncaa:1995976",
     "ncaa:1995977"
    ],
    "2021-01-11": [
     "ncaa:1995960"
    ]
   },
   "2021": {
    "2021-08-28": [
     "ncaa:2081756",
     "ncaa:2081757",
     "ncaa:2081758",
     "ncaa:2081763"
    ],
    "2021-09-02": [
     "ncaa:2081806",
     "ncaa:2081809",
     "ncaa:2081830",
     "ncaa:2081834",
     "ncaa:2081835"
    ],
    "2021-09-03": [
     "ncaa:2081844",
     "ncaa:2081850",
     "ncaa:2081855",
     "ncaa:2081860"
    ],
    "2021-09-04": [
     "ncaa:2081755",
     "ncaa:2081798",
     "ncaa:2081865",
     "ncaa:2081866",
     "ncaa:2081867",
     "ncaa:2081868",
     "ncaa:2081870",
     "ncaa:2081871",
     "ncaa:2081888",
     "ncaa:2081898",
     "ncaa:2081959",
     "ncaa:2081968",
     "ncaa:2081971",
     "ncaa:2081972",
     "ncaa:2081973",
     "ncaa:2081975",
     "ncaa:2081976",
     "ncaa:2081977",
     "ncaa:2081978",
     "ncaa:2081982",
     "ncaa:2081991",
     "ncaa:2082003",
     "ncaa:2082031",
     "ncaa:2082039",
     "ncaa:2082042",
     "ncaa:2082056",
     "ncaa:2082062",
     "ncaa:2082063",
     "ncaa:2082068",
     "ncaa:2082069",
     "ncaa:2082071",
     "ncaa:2082072",
     "ncaa:2082073",
     "ncaa:2082074",
     "ncaa:2082075"
    ],
    "2021-09-05": [
     "ncaa:2082079"
    ],
    "2021-09-06": [
     "ncaa:2082080"
    ],
    "2021-09-10": [
     "ncaa:2082093",
     "ncaa:2082094"
    ],
    "2021-09-11": [
     "ncaa:2082096",
     "ncaa:2082102",
     "ncaa:2082107",
     "ncaa:2082109",
     "ncaa:2082110",
     "ncaa:2082112",
     "ncaa:2082115",
     "ncaa:2082118",
     "ncaa:2082120",
     "ncaa:2082146",
     "ncaa:2082199",
     "ncaa:2082225",
     "ncaa:2082236",
     "ncaa:2082238",
     "ncaa:2082245",
     "ncaa:2082248",
     "ncaa:2082254",
     "ncaa:2082256",
     "ncaa:2082257",
     "ncaa:2082258",
     "ncaa:2082259",
     "ncaa:2082260",
     "ncaa:2082261",
     "ncaa:2082265",
     "ncaa:2082274",
     "ncaa:2082277",
     "ncaa:2082279",
     "ncaa:2082287",
     "ncaa:2082295",
     "ncaa:2082315",
     "ncaa:2082323",
     "ncaa:2082325",
     "ncaa:2082359",
     "ncaa:2082364",
     "ncaa:2082365",
     "ncaa:2082373",
     "ncaa:2082374",
     "ncaa:2082375",
     "ncaa:2082378",
     "ncaa:2082381",
     "ncaa:2082383",
     "ncaa:2082384",
     "ncaa:2082386"
    ],
    "2021-09-16": [
     "ncaa:2082388"
    ],
    "2021-09-17": [
     "ncaa:2082393",
     "ncaa:2082394"
    ],
    "2021-09-18": [
     "ncaa:2082395",
     "ncaa:2082405",
     "ncaa:2082406",
     "ncaa:2082407",
     "ncaa:2082411",
     "ncaa:2082415",
     "ncaa:2082417",
     "ncaa:2082427",
     "ncaa:2082429",
     "ncaa:2082434",
     "ncaa:2082435",
     "ncaa:2082436",
     "ncaa:2082448",
     "ncaa:2082535",
     "ncaa:2082536",
     "ncaa:2082560",
     "ncaa:2082567",
     "ncaa:2082568",
     "ncaa:2082571",
     "ncaa:2082572",
     "ncaa:2082574",
     "ncaa:2082579",
     "ncaa:2082581",
     "ncaa:2082582",
     "ncaa:2082583",
     "ncaa:2082584",
     "ncaa:2082590",
     "ncaa:2082592",
     "ncaa:2082594",
     "ncaa:2082600",
     "ncaa:2082603",
     "ncaa:2082608",
     "ncaa:2082643",
     "ncaa:2082644",
     "ncaa:2082647",
     "ncaa:2082661",
     "ncaa:2082662",
     "ncaa:2082664",
     "ncaa:2082669",
     "ncaa:2082671",
     "ncaa:2082674",
     "ncaa:2082675",
     "ncaa:2082684",
     "ncaa:2082685",
     "ncaa:2082690",
     "ncaa:2082693",
     "ncaa:2082694",
     "ncaa:2082695",
     "ncaa:2082696"
    ],
    "2021-09-23": [
     "ncaa:2082698"
    ],
    "2021-09-24": [
     "ncaa:2082700",
     "ncaa:2082702",
     "ncaa:2082703",
     "ncaa:2082704"
    ],
    "2021-09-25": [
     "ncaa:2082705",
     "ncaa:2082706",
     "ncaa:2082707",
     "ncaa:2082708",
     "ncaa:2082711",
     "ncaa:2082712",
     "ncaa:2082713",
     "ncaa:2082714",
     "ncaa:2082715",
     "ncaa:2082717",
     "ncaa:2082718",
     "ncaa:2082719",
     "ncaa:2082720",
     "ncaa:2082721",
     "ncaa:2082722",
     "ncaa:2082723",
     "ncaa:2082724",
     "ncaa:2082725",
     "ncaa:2082726",
     "ncaa:2082727",
     "ncaa:2082729",
     "ncaa:2082733",
     "ncaa:2082734",
     "ncaa:2082735",
     "ncaa:2082738",
     "ncaa:2082740",
     "ncaa:2082742",
     "ncaa:2082743",
     "ncaa:2082744",
     "ncaa:2082749",
     "ncaa:2082750",
     "ncaa:2082751",
     "ncaa:2082752",
     "ncaa:2082753",
     "ncaa:2082754",
     "ncaa:2082756",
     "ncaa:2082757",
     "ncaa:2082762",
     "ncaa:2082764",
     "ncaa:2082765",
     "ncaa:2082767",
     "ncaa:2082774",
     "ncaa:2082917",
     "ncaa:2082918",
     "ncaa:2082931",
     "ncaa:2082934",
     "ncaa:2082940",
     "ncaa:2082948",
     "ncaa:2082974",
     "ncaa:2082985",
     "ncaa:2082988",
     "ncaa:2124241"
    ],
    "2021-09-30": [
     "ncaa:2082991"
    ],
    "2021-10-01": [
     "ncaa:2082992",
     "ncaa:2082994",
     "ncaa:2082995"
    ],
    "2021-10-02": [
     "ncaa:2082996",
     "ncaa:2082997",
     "ncaa:2082999",
     "ncaa:2083000",
     "ncaa:2083001",
     "ncaa:2083002",
     "ncaa:2083003",
     "ncaa:2083004",
     "ncaa:2083005",
     "ncaa:2083006",
     "ncaa:2083007",
     "ncaa:2083010",
     "ncaa:2083011",
     "ncaa:2083012",
     "ncaa:2083013",
     "ncaa:2083014",
     "ncaa:2083015",
     "ncaa:2083016",
     "ncaa:2083017",
     "ncaa:2083018",
     "ncaa:2083019",
     "ncaa:2083020",
     "ncaa:2083023",
     "ncaa:2083025",
     "ncaa:2083027",
     "ncaa:2083028",
     "ncaa:2083029",
     "ncaa:2083030",
     "ncaa:2083031",
     "ncaa:2083032",
     "ncaa:2083034",
     "ncaa:2083035",
     "ncaa:2083036",
     "ncaa:2083037",
     "ncaa:2083038",
     "ncaa:2083039",
     "ncaa:2083041",
     "ncaa:2083050",
     "ncaa:2083054",
     "ncaa:2083066",
     "ncaa:2083073",
     "ncaa:2083074",
     "ncaa:2083223",
     "ncaa:2083238",
     "ncaa:2083241",
     "ncaa:2083243",
     "ncaa:2083244",
     "ncaa:2083245",
     "ncaa:2083248",
     "ncaa:2083257",
     "ncaa:2083258",
     "ncaa:2083261",
     "ncaa:2083286",
     "ncaa:2083287",
     "ncaa:2083292",
     "ncaa:2083295",
     "ncaa:2083303"
    ],
    "2021-10-07": [
     "ncaa:2083304",
     "ncaa:2083305"
    ],
    "2021-10-08": [
     "ncaa:2083307",
     "ncaa:2083309",
     "ncaa:2083310"
    ],
    "2021-10-09": [
     "ncaa:2083312",
     "ncaa:2083313",
     "ncaa:2083314",
     "ncaa:2083315",
     "ncaa:2083317",
     "ncaa:2083318",
     "ncaa:2083319",
     "ncaa:2083320",
     "ncaa:2083322",
     "ncaa:2083323",
     "ncaa:2083324",
     "ncaa:2083325",
     "ncaa:2083326",
     "ncaa:2083327",
     "ncaa:2083328",
     "ncaa:2083329",
     "ncaa:2083330",
     "ncaa:2083332",
     "ncaa:2083336",
     "ncaa:2083337",
     "ncaa:2083338",
     "ncaa:2083339",
     "ncaa:2083341",
     "ncaa:2083342",
     "ncaa:2083344",
     "ncaa:2083345",
     "ncaa:2083346",
     "ncaa:2083347",
     "ncaa:2083348",
     "ncaa:2083349",
     "ncaa:2083350",
     "ncaa:2083353",
     "ncaa:2083354",
     "ncaa:2083360",
     "ncaa:2083361",
     "ncaa:2083363",
     "ncaa:2083394",
     "ncaa:2083522",
     "ncaa:2083538",
     "ncaa:2083546",
     "ncaa:2083549",
     "ncaa:2083551",
     "ncaa:2083561",
     "ncaa:2083563",
     "ncaa:2083575",
     "ncaa:2083589"
    ],
    "2021-10-12": [
     "ncaa:2083591"
    ],
    "2021-10-14": [
     "ncaa:2083593",
     "ncaa:2083594"
    ],
    "2021-10-15": [
     "ncaa:2083596",
     "ncaa:2083597",
     "ncaa:2083599",
     "ncaa:2083600"
    ],
    "2021-10-16": [
     "ncaa:2083602",
     "ncaa:2083603",
     "ncaa:2083604",
     "ncaa:2083605",
     "ncaa:2083606",
     "ncaa:2083607",
     "ncaa:2083609",
     "ncaa:2083610",
     "ncaa:2083612",
     "ncaa:2083613",
     "ncaa:2083614",
     "ncaa:2083615",
     "ncaa:2083616",
     "ncaa:2083617",
     "ncaa:2083619",
     "ncaa:2083623",
     "ncaa:2083624",
     "ncaa:2083625",
     "ncaa:2083626",
     "ncaa:2083627",
     "ncaa:2083628",
     "ncaa:2083629",
     "ncaa:2083630",
     "ncaa:2083632",
     "ncaa:2083633",
     "ncaa:2083634",
     "ncaa:2083635",
     "ncaa:2083636",
     "ncaa:2083637",
     "ncaa:2083638",
     "ncaa:2083640",
     "ncaa:2083641",
     "ncaa:2083645",
     "ncaa:2083665",
     "ncaa:2083828",
     "ncaa:2083829",
     "ncaa:2083839",
     "ncaa:2083841",
     "ncaa:2083842",
     "ncaa:2083856",
     "ncaa:2083862",
     "ncaa:2083863",
     "ncaa:2083882",
     "ncaa:2083891"
    ],
    "2021-10-20": [
     "ncaa:2083892"
    ],
    "2021-10-21": [
     "ncaa:2083893",
     "ncaa:2083894",
     "ncaa:2083895",
     "ncaa:2084196"
    ],
    "2021-10-22": [
     "ncaa:2083897",
     "ncaa:2083898",
     "ncaa:2083899",
     "ncaa:2083900"
    ],
    "2021-10-23": [
     "ncaa:2083901",
     "ncaa:2083902",
     "ncaa:2083903",
     "ncaa:2083905",
     "ncaa:2083906",
     "ncaa:2083907",
     "ncaa:2083909",
     "ncaa:2083910",
     "ncaa:2083911",
     "ncaa:2083912",
     "ncaa:2083913",
     "ncaa:2083914",
     "ncaa:2083915",
     "ncaa:2083916",
     "ncaa:2083917",
     "ncaa:2083918",
     "ncaa:2083919",
     "ncaa:2083921",
     "ncaa:2083923",
     "ncaa:2083924",
     "ncaa:2083925",
     "ncaa:2083927",
     "ncaa:2083929",
     "ncaa:2083930",
     "ncaa:2083931",
     "ncaa:2083932",
     "ncaa:2083933",
     "ncaa:2083935",
     "ncaa:2083936",
     "ncaa:2083938",
     "ncaa:2083939",
     "ncaa:2083940",
     "ncaa:2083941",
     "ncaa:2083944",
     "ncaa:2083970",
     "ncaa:2083976",
     "ncaa:2084103",
     "ncaa:2084152",
     "ncaa:2084167",
     "ncaa:2084175",
     "ncaa:2084176",
     "ncaa:2084193",
     "ncaa:2084197",
     "ncaa:2157399"
    ],
    "2021-10-28": [
     "ncaa:2084198",
     "ncaa:2084199"
    ],
    "2021-10-29": [
     "ncaa:2084201",
     "ncaa:2084202"
    ],
    "2021-10-30": [
     "ncaa:2084203",
     "ncaa:2084204",
     "ncaa:2084205",
     "ncaa:2084206",
     "ncaa:2084207",
     "ncaa:2084208",
     "ncaa:2084209",
     "ncaa:2084210",
     "ncaa:2084211",
     "ncaa:2084212",
     "ncaa:2084213",
     "ncaa:2084214",
     "ncaa:2084215",
     "ncaa:2084219",
     "ncaa:2084220",
     "ncaa:2084221",
     "ncaa:2084223",
     "ncaa:2084225",
     "ncaa:2084226",
     "ncaa:2084228",
     "ncaa:2084229",
     "ncaa:2084230",
     "ncaa:2084231",
     "ncaa:2084233",
     "ncaa:2084234",
     "ncaa:2084235",
     "ncaa:2084236",
     "ncaa:2084237",
     "ncaa:2084238",
     "ncaa:2084239",
     "ncaa:2084241",
     "ncaa:2084242",
     "ncaa:2084243",
     "ncaa:2084251",
     "ncaa:2084258",
     "ncaa:2084285",
     "ncaa:2084306",
     "ncaa:2084385",
     "ncaa:2084459",
     "ncaa:2084466",
     "ncaa:2084469",
     "ncaa:2084470",
     "ncaa:2084471",
     "ncaa:2084472",
     "ncaa:2084480",
     "ncaa:2084485",
     "ncaa:2084492",
     "ncaa:2084502",
     "ncaa:2084503"
    ],
    "2021-11-02": [
     "ncaa:2084504",
     "ncaa:2084505",
     "ncaa:2084506"
    ],
    "2021-11-03": [
     "ncaa:2084507",
     "ncaa:2084508"
    ],
    "2021-11-04": [
     "ncaa:2084509"
    ],
    "2021-11-05": [
     "ncaa:2084512",
     "ncaa:2084513"
    ],
    "2021-11-06": [
     "ncaa:2084515",
     "ncaa:2084516",
     "ncaa:2084517",
     "ncaa:2084518",
     "ncaa:2084519",
     "ncaa:2084520",
     "ncaa:2084521",
     "ncaa:2084522",
     "ncaa:2084523",
     "ncaa:2084526",
     "ncaa:2084527",
     "ncaa:2084528",
     "ncaa:2084529",
     "ncaa:2084530",
     "ncaa:2084531",
     "ncaa:2084532",
     "ncaa:2084534",
     "ncaa:2084537",
     "ncaa:2084538",
     "ncaa:2084539",
     "ncaa:2084540",
     "ncaa:2084542",
     "ncaa:2084544",
     "ncaa:2084546",
     "ncaa:2084547",
     "ncaa:2084549",
     "ncaa:2084550",
     "ncaa:2084551",
     "ncaa:2084552",
     "ncaa:2084553",
     "ncaa:2084554",
     "ncaa:2084555",
     "ncaa:2084556",
     "ncaa:2084557",
     "ncaa:2084558",
     "ncaa:2084562",
     "ncaa:2084563",
     "ncaa:2084569",
     "ncaa:2084570",
     "ncaa:2084619",
     "ncaa:2084765",
     "ncaa:2084768",
     "ncaa:2084772",
     "ncaa:2084801",
     "ncaa:2084802",
     "ncaa:2084806",
     "ncaa:2084809",
     "ncaa:2084812",
     "ncaa:2084815",
     "ncaa:2084820",
     "ncaa:2157980"
    ],
    "2021-11-09": [
     "ncaa:2084821",
     "ncaa:2084822",
     "ncaa:2084823"
    ],
    "2021-11-10": [
     "ncaa:2084824",
     "ncaa:2084825",
     "ncaa:2084826"
    ],
    "2021-11-11": [
     "ncaa:2084827"
    ],
    "2021-11-12": [
     "ncaa:2084828",
     "ncaa:2084830"
    ],
    "2021-11-13": [
     "ncaa:2084831",
     "ncaa:2084833",
     "ncaa:2084834",
     "ncaa:2084835",
     "ncaa:2084836",
     "ncaa:2084837",
     "ncaa:2084838",
     "ncaa:2084839",
     "ncaa:2084840",
     "ncaa:2084841",
     "ncaa:2084842",
     "ncaa:2084845",
     "ncaa:2084846",
     "ncaa:2084847",
     "ncaa:2084848",
     "ncaa:2084849",
     "ncaa:2084850",
     "ncaa:2084851",
     "ncaa:2084852",
     "ncaa:2084855",
     "ncaa:2084857",
     "ncaa:2084858",
     "ncaa:2084859",
     "ncaa:2084860",
     "ncaa:2084862",
     "ncaa:2084863",
     "ncaa:2084864",
     "ncaa:2084865",
     "ncaa:2084868",
     "ncaa:2084869",
     "ncaa:2084870",
     "ncaa:2084871",
     "ncaa:2084873",
     "ncaa:2084874",
     "ncaa:2084875",
     "ncaa:2084877",
     "ncaa:2084878",
     "ncaa:2084950",
     "ncaa:2084966",
     "ncaa:2085039",
     "ncaa:2085097",
     "ncaa:2085098",
     "ncaa:2085099",
     "ncaa:2085100",
     "ncaa:2085105",
     "ncaa:2085109",
     "ncaa:2085110",
     "ncaa:2085115",
     "ncaa:2085116",
     "ncaa:2085124",
     "ncaa:2159747"
    ],
    "2021-11-16": [
     "ncaa:2085125",
     "ncaa:2085126",
     "ncaa:2085127"
    ],
    "2021-11-17": [
     "ncaa:2085128",
     "ncaa:2085129"
    ],
    "2021-11-18": [
     "ncaa:2085130"
    ],
    "2021-11-19": [
     "ncaa:2085132",
     "ncaa:2085133",
     "ncaa:2085134",
     "ncaa:2085135",
     "ncaa:2085251"
    ],
    "2021-11-20": [
     "ncaa:2085137",
     "ncaa:2085138",
     "ncaa:2085139",
     "ncaa:2085140",
     "ncaa:2085141",
     "ncaa:2085143",
     "ncaa:2085144",
     "ncaa:2085146",
     "ncaa:2085147",
     "ncaa:2085148",
     "ncaa:2085150",
     "ncaa:2085151",
     "ncaa:2085153",
     "ncaa:2085154",
     "ncaa:2085155",
     "ncaa:2085157",
     "ncaa:2085158",
     "ncaa:2085159",
     "ncaa:2085160",
     "ncaa:2085162",
     "ncaa:2085163",
     "ncaa:2085165",
     "ncaa:2085168",
     "ncaa:2085169",
     "ncaa:2085170",
     "ncaa:2085171",
     "ncaa:2085172",
     "ncaa:2085173",
     "ncaa:2085174",
     "ncaa:2085175",
     "ncaa:2085176",
     "ncaa:2085179",
     "ncaa:2085180",
     "ncaa:2085181",
     "ncaa:2085182",
     "ncaa:2085183",
     "ncaa:2085184",
     "ncaa:2085185",
     "ncaa:2085192",
     "ncaa:2085194",
     "ncaa:2085207",
     "ncaa:2085231",
     "ncaa:2085237",
     "ncaa:2085238",
     "ncaa:2085240",
     "ncaa:2085242",
     "ncaa:2085243",
     "ncaa:2085245",
     "ncaa:2085247",
     "ncaa:2085249"
    ],
    "2021-11-23": [
     "ncaa:2085252",
     "ncaa:2085253"
    ],
    "2021-11-25": [
     "ncaa:2085255",
     "ncaa:2085256"
    ],
    "2021-11-26": [
     "ncaa:2085258",
     "ncaa:2085259",
     "ncaa:2085260",
     "ncaa:2085261",
     "ncaa:2085262",
     "ncaa:2085263",
     "ncaa:2085264",
     "ncaa:2085265",
     "ncaa:2085266",
     "ncaa:2085267",
     "ncaa:2085268",
     "ncaa:2085269",
     "ncaa:2085270",
     "ncaa:2085271",
     "ncaa:2085272",
     "ncaa:2085296"
    ],
    "2021-11-27": [
     "ncaa:2085257",
     "ncaa:2085273",
     "ncaa:2085274",
     "ncaa:2085275",
     "ncaa:2085276",
     "ncaa:2085277",
     "ncaa:2085278",
     "ncaa:2085279",
     "ncaa:2085280",
     "ncaa:2085281",
     "ncaa:2085282",
     "ncaa:2085283",
     "ncaa:2085284",
     "ncaa:2085285",
     "ncaa:2085286",
     "ncaa:2085287",
     "ncaa:2085288",
     "ncaa:2085289",
     "ncaa:2085290",
     "ncaa:2085291",
     "ncaa:2085292",
     "ncaa:2085293",
     "ncaa:2085294",
     "ncaa:2085295",
     "ncaa:2085297",
     "ncaa:2085298",
     "ncaa:2085299",
     "ncaa:2085300",
     "ncaa:2085301",
     "ncaa:2085302",
     "ncaa:2085303",
     "ncaa:2085304",
     "ncaa:2085305",
     "ncaa:2085306",
     "ncaa:2085307",
     "ncaa:2085308",
     "ncaa:2085309",
     "ncaa:2085310",
     "ncaa:2085311",
     "ncaa:2085312",
     "ncaa:2085313",
     "ncaa:2085315",
     "ncaa:2085316",
     "ncaa:2085318",
     "ncaa:2085319"
    ],
    "2021-12-03": [
     "ncaa:2160661",
     "ncaa:2160669"
    ],
    "2021-12-04": [
     "ncaa:2084861",
     "ncaa:2160578",
     "ncaa:2160662",
     "ncaa:2160671",
     "ncaa:2160672",
     "ncaa:2160673",
     "ncaa:2160674",
     "ncaa:2160680",
     "ncaa:2160686"
    ],
    "2021-12-17": [
     "ncaa:2160794",
     "ncaa:2160830"
    ],
    "2021-12-18": [
     "ncaa:2160795",
     "ncaa:2160800",
     "ncaa:2160801",
     "ncaa:2160831",
     "ncaa:2160832",
     "ncaa:2160833"
    ],
    "2021-12-20": [
     "ncaa:2160854"
    ],
    "2021-12-21": [
     "ncaa:2160802",
     "ncaa:2160855"
    ],
    "2021-12-23": [
     "ncaa:2160803",
     "ncaa:2160804",
     "ncaa:2160865"
    ],
    "2021-12-25": [
     "ncaa:2160857"
    ],
    "2021-12-27": [
     "ncaa:2160858"
    ],
    "2021-12-28": [
     "ncaa:2160859",
     "ncaa:2160869",
     "ncaa:2160870",
     "ncaa:2160871"
    ],
    "2021-12-29": [
     "ncaa:2160793",
     "ncaa:2160873",
     "ncaa:2160874"
    ],
    "2021-12-30": [
     "ncaa:2160861",
     "ncaa:2160875",
     "ncaa:2160876",
     "ncaa:2160877"
    ],
    "2021-12-31": [
     "ncaa:2160826",
     "ncaa:2160827",
     "ncaa:2160879",
     "ncaa:2163410"
    ],
    "2022-01-01": [
     "ncaa:2160862",
     "ncaa:2160867",
     "ncaa:2160881",
     "ncaa:2160882",
     "ncaa:2160883"
    ],
    "2022-01-04": [
     "ncaa:2160863"
    ],
    "2022-01-10": [
     "ncaa:2160828"
    ]
   },
   "2022": {
    "2022-08-27": [
     "ncaa:2276460",
     "ncaa:2276462",
     "ncaa:2276464",
     "ncaa:2276467",
     "ncaa:2276468",
     "ncaa:2276471",
     "ncaa:2276472"
    ],
    "2022-09-01": [
     "ncaa:2276504",
     "ncaa:2276522",
     "ncaa:2276541",
     "ncaa:2276546",
     "ncaa:2276554",
     "ncaa:2276555"
    ],
    "2022-09-02": [
     "ncaa:2276563",
     "ncaa:2276574",
     "ncaa:2276575",
     "ncaa:2276576",
     "ncaa:2276577"
    ],
    "2022-09-03": [
     "ncaa:2276578",
     "ncaa:2276584",
     "ncaa:2276594",
     "ncaa:2276595",
     "ncaa:2276600",
     "ncaa:2276601",
     "ncaa:2276605",
     "ncaa:2276616",
     "ncaa:2276681",
     "ncaa:2276690",
     "ncaa:2276693",
     "ncaa:2276694",
     "ncaa:2276695",
     "ncaa:2276697",
     "ncaa:2276699",
     "ncaa:2276703",
     "ncaa:2276708",
     "ncaa:2276717",
     "ncaa:2276733",
     "ncaa:2276744",
     "ncaa:2276760",
     "ncaa:2276763",
     "ncaa:2276764",
     "ncaa:2276766",
     "ncaa:2276767",
     "ncaa:2276769",
     "ncaa:2276771",
     "ncaa:2276775",
     "ncaa:2276785",
     "ncaa:2276786",
     "ncaa:2276787",
     "ncaa:2276788",
     "ncaa:2276790"
    ],
    "2022-09-04": [
     "ncaa:2276794"
    ],
    "2022-09-09": [
     "ncaa:2276808",
     "ncaa:2276810"
    ],
    "2022-09-10": [
     "ncaa:2276817",
     "ncaa:2276818",
     "ncaa:2276820",
     "ncaa:2276821",
     "ncaa:2276822",
     "ncaa:2276826",
     "ncaa:2276829",
     "ncaa:2276833",
     "ncaa:2276838",
     "ncaa:2276843",
     "ncaa:2276887",
     "ncaa:2276931",
     "ncaa:2276944",
     "ncaa:2276952",
     "ncaa:2276956",
     "ncaa:2276960",
     "ncaa:2276962",
     "ncaa:2276963",
     "ncaa:2276964",
     "ncaa:2276965",
     "ncaa:2276970",
     "ncaa:2276971",
     "ncaa:2276973",
     "ncaa:2276974",
     "ncaa:2276985",
     "ncaa:2276987",
     "ncaa:2277005",
     "ncaa:2277009",
     "ncaa:2277019",
     "ncaa:2277035",
     "ncaa:2277036",
     "ncaa:2277051",
     "ncaa:2277068",
     "ncaa:2277069",
     "ncaa:2277071",
     "ncaa:2277073",
     "ncaa:2277075",
     "ncaa:2277080",
     "ncaa:2277090",
     "ncaa:2277104",
     "ncaa:2277105",
     "ncaa:2277107",
     "ncaa:2277108",
     "ncaa:2277109",
     "ncaa:2316945"
    ],
    "2022-09-16": [
     "ncaa:2277113",
     "ncaa:2277118"
    ],
    "2022-09-17": [
     "ncaa:2277125",
     "ncaa:2277127",
     "ncaa:2277128",
     "ncaa:2277138",
     "ncaa:2277151",
     "ncaa:2277169",
     "ncaa:2277174",
     "ncaa:2277178",
     "ncaa:2277179",
     "ncaa:2277181",
     "ncaa:2277186",
     "ncaa:2277236",
     "ncaa:2277276",
     "ncaa:2277283",
     "ncaa:2277287",
     "ncaa:2277289",
     "ncaa:2277301",
     "ncaa:2277306",
     "ncaa:2277307",
     "ncaa:2277308",
     "ncaa:2277309",
     "ncaa:2277310",
     "ncaa:2277312",
     "ncaa:2277313",
     "ncaa:2277318",
     "ncaa:2277319",
     "ncaa:2277324",
     "ncaa:2277325",
     "ncaa:2277328",
     "ncaa:2277329",
     "ncaa:2277362",
     "ncaa:2277363",
     "ncaa:2277385",
     "ncaa:2277388",
     "ncaa:2277389",
     "ncaa:2277391",
     "ncaa:2277395",
     "ncaa:2277396",
     "ncaa:2277400",
     "ncaa:2277413",
     "ncaa:2277415",
     "ncaa:2277416",
     "ncaa:2277417",
     "ncaa:2277418",
     "ncaa:2277420",
     "ncaa:2277421",
     "ncaa:2277422",
     "ncaa:2277424"
    ],
    "2022-09-22": [
     "ncaa:2277425",
     "ncaa:2277426"
    ],
    "2022-09-23": [
     "ncaa:2277428",
     "ncaa:2277430",
     "ncaa:2277432"
    ],
    "2022-09-24": [
     "ncaa:2277433",
     "ncaa:2277434",
     "ncaa:2277435",
     "ncaa:2277436",
     "ncaa:2277437",
     "ncaa:2277438",
     "ncaa:2277439",
     "ncaa:2277441",
     "ncaa:2277442",
     "ncaa:2277444",
     "ncaa:2277445",
     "ncaa:2277446",
     "ncaa:2277448",
     "ncaa:2277449",
     "ncaa:2277450",
     "ncaa:2277451",
     "ncaa:2277452",
     "ncaa:2277453",
     "ncaa:2277454",
     "ncaa:2277455",
     "ncaa:2277456",
     "ncaa:2277457",
     "ncaa:2277458",
     "ncaa:2277459",
     "ncaa:2277460",
     "ncaa:2277461",
     "ncaa:2277462",
     "ncaa:2277463",
     "ncaa:2277464",
     "ncaa:2277465",
     "ncaa:2277466",
     "ncaa:2277468",
     "ncaa:2277469",
     "ncaa:2277470",
     "ncaa:2277472",
     "ncaa:2277473",
     "ncaa:2277475",
     "ncaa:2277476",
     "ncaa:2277477",
     "ncaa:2277478",
     "ncaa:2277480",
     "ncaa:2277481",
     "ncaa:2277482",
     "ncaa:2277483",
     "ncaa:2277486",
     "ncaa:2277508",
     "ncaa:2277512",
     "ncaa:2277633",
     "ncaa:2277657",
     "ncaa:2277663",
     "ncaa:2277699",
     "ncaa:2277701",
     "ncaa:2277706",
     "ncaa:2277717",
     "ncaa:2277718"
    ],
    "2022-09-29": [
     "ncaa:2277719"
    ],
    "2022-09-30": [
     "ncaa:2277720",
     "ncaa:2277721",
     "ncaa:2277722",
     "ncaa:2277725",
     "ncaa:2277726"
    ],
    "2022-10-01": [
     "ncaa:2277727",
     "ncaa:2277728",
     "ncaa:2277729",
     "ncaa:2277730",
     "ncaa:2277732",
     "ncaa:2277733",
     "ncaa:2277734",
     "ncaa:2277735",
     "ncaa:2277736",
     "ncaa:2277737",
     "ncaa:2277739",
     "ncaa:2277740",
     "ncaa:2277741",
     "ncaa:2277742",
     "ncaa:2277743",
     "ncaa:2277745",
     "ncaa:2277746",
     "ncaa:2277747",
     "ncaa:2277748",
     "ncaa:2277749",
     "ncaa:2277750",
     "ncaa:2277751",
     "ncaa:2277752",
     "ncaa:2277753",
     "ncaa:2277754",
     "ncaa:2277755",
     "ncaa:2277757",
     "ncaa:2277758",
     "ncaa:2277760",
     "ncaa:2277762",
     "ncaa:2277763",
     "ncaa:2277765",
     "ncaa:2277767",
     "ncaa:2277768",
     "ncaa:2277769",
     "ncaa:2277772",
     "ncaa:2277773",
     "ncaa:2277789",
     "ncaa:2277924",
     "ncaa:2277951",
     "ncaa:2277955",
     "ncaa:2277957",
     "ncaa:2277958",
     "ncaa:2277959",
     "ncaa:2277962",
     "ncaa:2277963",
     "ncaa:2277979",
     "ncaa:2277987",
     "ncaa:2278000",
     "ncaa:2278006",
     "ncaa:2278013"
    ],
    "2022-10-05": [
     "ncaa:2277744"
    ],
    "2022-10-07": [
     "ncaa:2278036",
     "ncaa:2278037",
     "ncaa:2278039",
     "ncaa:2278040"
    ],
    "2022-10-08": [
     "ncaa:2278041",
     "ncaa:2278042",
     "ncaa:2278043",
     "ncaa:2278044",
     "ncaa:2278045",
     "ncaa:2278046",
     "ncaa:2278047",
     "ncaa:2278049",
     "ncaa:2278050",
     "ncaa:2278051",
     "ncaa:2278052",
     "ncaa:2278053",
     "ncaa:2278054",
     "ncaa:2278055",
     "ncaa:2278056",
     "ncaa:2278057",
     "ncaa:2278058",
     "ncaa:2278059",
     "ncaa:2278060",
     "ncaa:2278061",
     "ncaa:2278062",
     "ncaa:2278063",
     "ncaa:2278064",
     "ncaa:2278065",
     "ncaa:2278066",
     "ncaa:2278067",
     "ncaa:2278068",
     "ncaa:2278069",
     "ncaa:2278070",
     "ncaa:2278071",
     "ncaa:2278072",
     "ncaa:2278073",
     "ncaa:2278074",
     "ncaa:2278075",
     "ncaa:2278076",
     "ncaa:2278078",
     "ncaa:2278090",
     "ncaa:2278244",
     "ncaa:2278262",
     "ncaa:2278263",
     "ncaa:2278270",
     "ncaa:2278271",
     "ncaa:2278272",
     "ncaa:2278286",
     "ncaa:2278290",
     "ncaa:2278291",
     "ncaa:2278293",
     "ncaa:2278302",
     "ncaa:2278305",
     "ncaa:2278319",
     "ncaa:2278322",
     "ncaa:2278325"
    ],
    "2022-10-12": [
     "ncaa:2278327"
    ],
    "2022-10-13": [
     "ncaa:2278330",
     "ncaa:2278331"
    ],
    "2022-10-14": [
     "ncaa:2278333",
     "ncaa:2278339"
    ],
    "2022-10-15": [
     "ncaa:2278340",
     "ncaa:2278341",
     "ncaa:2278342",
     "ncaa:2278343",
     "ncaa:2278344",
     "ncaa:2278345",
     "ncaa:2278346",
     "ncaa:2278349",
     "ncaa:2278350",
     "ncaa:2278351",
     "ncaa:2278352",
     "ncaa:2278353",
     "ncaa:2278354",
     "ncaa:2278355",
     "ncaa:2278356",
     "ncaa:2278357",
     "ncaa:2278358",
     "ncaa:2278359",
     "ncaa:2278360",
     "ncaa:2278361",
     "ncaa:2278362",
     "ncaa:2278363",
     "ncaa:2278364",
     "ncaa:2278365",
     "ncaa:2278366",
     "ncaa:2278367",
     "ncaa:2278369",
     "ncaa:2278370",
     "ncaa:2278371",
     "ncaa:2278374",
     "ncaa:2278377",
     "ncaa:2278379",
     "ncaa:2278380",
     "ncaa:2278381",
     "ncaa:2278384",
     "ncaa:2278559",
     "ncaa:2278560",
     "ncaa:2278563",
     "ncaa:2278568",
     "ncaa:2278576",
     "ncaa:2278577",
     "ncaa:2278588",
     "ncaa:2278613",
     "ncaa:2278618",
     "ncaa:2278624",
     "ncaa:2350980"
    ],
    "2022-10-19": [
     "ncaa:2278627"
    ],
    "2022-10-20": [
     "ncaa:2278628",
     "ncaa:2278631"
    ],
    "2022-10-21": [
     "ncaa:2278634",
     "ncaa:2278635"
    ],
    "2022-10-22": [
     "ncaa:2278636",
     "ncaa:2278637",
     "ncaa:2278638",
     "ncaa:2278639",
     "ncaa:2278640",
     "ncaa:2278641",
     "ncaa:2278642",
     "ncaa:2278643",
     "ncaa:2278644",
     "ncaa:2278645",
     "ncaa:2278646",
     "ncaa:2278648",
     "ncaa:2278649",
     "ncaa:2278650",
     "ncaa:2278651",
     "ncaa:2278652",
     "ncaa:2278653",
     "ncaa:2278654",
     "ncaa:2278656",
     "ncaa:2278658",
     "ncaa:2278659",
     "ncaa:2278660",
     "ncaa:2278661",
     "ncaa:2278662",
     "ncaa:2278663",
     "ncaa:2278664",
     "ncaa:2278665",
     "ncaa:2278666",
     "ncaa:2278668",
     "ncaa:2278669",
     "ncaa:2278670",
     "ncaa:2278672",
     "ncaa:2278698",
     "ncaa:2278701",
     "ncaa:2278703",
     "ncaa:2278837",
     "ncaa:2278849",
     "ncaa:2278866",
     "ncaa:2278872",
     "ncaa:2278873",
     "ncaa:2278874",
     "ncaa:2278888",
     "ncaa:2278893",
     "ncaa:2278900",
     "ncaa:2278907",
     "ncaa:2278930",
     "ncaa:2278931"
    ],
    "2022-10-27": [
     "ncaa:2278935",
     "ncaa:2278936",
     "ncaa:2278937"
    ],
    "2022-10-28": [
     "ncaa:2278938",
     "ncaa:2278941"
    ],
    "2022-10-29": [
     "ncaa:2278942",
     "ncaa:2278943",
     "ncaa:2278944",
     "ncaa:2278945",
     "ncaa:2278946",
     "ncaa:2278947",
     "ncaa:2278948",
     "ncaa:2278949",
     "ncaa:2278950",
     "ncaa:2278951",
     "ncaa:2278952",
     "ncaa:2278953",
     "ncaa:2278954",
     "ncaa:2278955",
     "ncaa:2278957",
     "ncaa:2278958",
     "ncaa:2278959",
     "ncaa:2278960",
     "ncaa:2278962",
     "ncaa:2278963",
     "ncaa:2278964",
     "ncaa:2278965",
     "ncaa:2278966",
     "ncaa:2278967",
     "ncaa:2278968",
     "ncaa:2278969",
     "ncaa:2278970",
     "ncaa:2278971",
     "ncaa:2278972",
     "ncaa:2278974",
     "ncaa:2278975",
     "ncaa:2278976",
     "ncaa:2278978",
     "ncaa:2279010",
     "ncaa:2279093",
     "ncaa:2279190",
     "ncaa:2279198",
     "ncaa:2279206",
     "ncaa:2279207",
     "ncaa:2279225",
     "ncaa:2279229",
     "ncaa:2279231"
    ],
    "2022-11-01": [
     "ncaa:2279232",
     "ncaa:2279233"
    ],
    "2022-11-02": [
     "ncaa:2279234",
     "ncaa:2279235"
    ],
    "2022-11-03": [
     "ncaa:2279237",
     "ncaa:2279239"
    ],
    "2022-11-04": [
     "ncaa:2279241",
     "ncaa:2279242",
     "ncaa:2279243"
    ],
    "2022-11-05": [
     "ncaa:2279244",
     "ncaa:2279245",
     "ncaa:2279246",
     "ncaa:2279247",
     "ncaa:2279248",
     "ncaa:2279250",
     "ncaa:2279251",
     "ncaa:2279252",
     "ncaa:2279253",
     "ncaa:2279254",
     "ncaa:2279255",
     "ncaa:2279256",
     "ncaa:2279257",
     "ncaa:2279258",
     "ncaa:2279259",
     "ncaa:2279262",
     "ncaa:2279263",
     "ncaa:2279264",
     "ncaa:2279265",
     "ncaa:2279266",
     "ncaa:2279267",
     "ncaa:2279268",
     "ncaa:2279269",
     "ncaa:2279270",
     "ncaa:2279271",
     "ncaa:2279272",
     "ncaa:2279273",
     "ncaa:2279274",
     "ncaa:2279276",
     "ncaa:2279277",
     "ncaa:2279278",
     "ncaa:2279281",
     "ncaa:2279282",
     "ncaa:2279283",
     "ncaa:2279284",
     "ncaa:2279285",
     "ncaa:2279286",
     "ncaa:2279287",
     "ncaa:2279288",
     "ncaa:2279290",
     "ncaa:2279291",
     "ncaa:2279293",
     "ncaa:2279302",
     "ncaa:2279464",
     "ncaa:2279495",
     "ncaa:2279510",
     "ncaa:2279512",
     "ncaa:2279516",
     "ncaa:2279523",
     "ncaa:2279526",
     "ncaa:2279545"
    ],
    "2022-11-08": [
     "ncaa:2279546",
     "ncaa:2279547",
     "ncaa:2279548"
    ],
    "2022-11-09": [
     "ncaa:2279549",
     "ncaa:2279550",
     "ncaa:2279551"
    ],
    "2022-11-10": [
     "ncaa:2279552",
     "ncaa:2279553"
    ],
    "2022-11-11": [
     "ncaa:2279554",
     "ncaa:2279555",
     "ncaa:2279559"
    ],
    "2022-11-12": [
     "ncaa:2279560",
     "ncaa:2279561",
     "ncaa:2279562",
     "ncaa:2279563",
     "ncaa:2279564",
     "ncaa:2279565",
     "ncaa:2279567",
     "ncaa:2279568",
     "ncaa:2279569",
     "ncaa:2279570",
     "ncaa:2279571",
     "ncaa:2279572",
     "ncaa:2279573",
     "ncaa:2279574",
     "ncaa:2279575",
     "ncaa:2279576",
     "ncaa:2279577",
     "ncaa:2279578",
     "ncaa:2279579",
     "ncaa:2279581",
     "ncaa:2279582",
     "ncaa:2279585",
     "ncaa:2279586",
     "ncaa:2279587",
     "ncaa:2279588",
     "ncaa:2279589",
     "ncaa:2279590",
     "ncaa:2279591",
     "ncaa:2279592",
     "ncaa:2279593",
     "ncaa:2279594",
     "ncaa:2279595",
     "ncaa:2279596",
     "ncaa:2279597",
     "ncaa:2279598",
     "ncaa:2279599",
     "ncaa:2279601",
     "ncaa:2279602",
     "ncaa:2279604",
     "ncaa:2279605",
     "ncaa:2279607",
     "ncaa:2279608",
     "ncaa:2279609",
     "ncaa:2279656",
     "ncaa:2279673",
     "ncaa:2279776",
     "ncaa:2279790",
     "ncaa:2279829",
     "ncaa:2279830",
     "ncaa:2279832",
     "ncaa:2279840",
     "ncaa:2279848",
     "ncaa:2279850"
    ],
    "2022-11-15": [
     "ncaa:2279851",
     "ncaa:2279852"
    ],
    "2022-11-16": [
     "ncaa:2279853",
     "ncaa:2279854",
     "ncaa:2279855"
    ],
    "2022-11-17": [
     "ncaa:2279856"
    ],
    "2022-11-18": [
     "ncaa:2279858",
     "ncaa:2279860"
    ],
    "2022-11-19": [
     "ncaa:2279862",
     "ncaa:2279864",
     "ncaa:2279866",
     "ncaa:2279867",
     "ncaa:2279868",
     "ncaa:2279869",
     "ncaa:2279870",
     "ncaa:2279871",
     "ncaa:2279872",
     "ncaa:2279873",
     "ncaa:2279874",
     "ncaa:2279875",
     "ncaa:2279876",
     "ncaa:2279877",
     "ncaa:2279878",
     "ncaa:2279879",
     "ncaa:2279880",
     "ncaa:2279881",
     "ncaa:2279882",
     "ncaa:2279883",
     "ncaa:2279884",
     "ncaa:2279885",
     "ncaa:2279887",
     "ncaa:2279888",
     "ncaa:2279889",
     "ncaa:2279890",
     "ncaa:2279891",
     "ncaa:2279892",
     "ncaa:2279893",
     "ncaa:2279894",
     "ncaa:2279895",
     "ncaa:2279896",
     "ncaa:2279898",
     "ncaa:2279899",
     "ncaa:2279900",
     "ncaa:2279901",
     "ncaa:2279902",
     "ncaa:2279903",
     "ncaa:2279904",
     "ncaa:2279905",
     "ncaa:2279906",
     "ncaa:2279907",
     "ncaa:2279908",
     "ncaa:2279922",
     "ncaa:2279924",
     "ncaa:2279959",
     "ncaa:2279965",
     "ncaa:2279966",
     "ncaa:2279968",
     "ncaa:2279970",
     "ncaa:2279972",
     "ncaa:2279974",
     "ncaa:2279976"
    ],
    "2022-11-22": [
     "ncaa:2279977",
     "ncaa:2279978"
    ],
    "2022-11-24": [
     "ncaa:2279980"
    ],
    "2022-11-25": [
     "ncaa:2279981",
     "ncaa:2279982",
     "ncaa:2279984",
     "ncaa:2279985",
     "ncaa:2279986",
     "ncaa:2279987",
     "ncaa:2279988",
     "ncaa:2279989",
     "ncaa:2279990",
     "ncaa:2279991",
     "ncaa:2279992",
     "ncaa:2279993",
     "ncaa:2280028"
    ],
    "2022-11-26": [
     "ncaa:2279983",
     "ncaa:2279994",
     "ncaa:2279996",
     "ncaa:2279997",
     "ncaa:2279998",
     "ncaa:2279999",
     "ncaa:2280000",
     "ncaa:2280001",
     "ncaa:2280002",
     "ncaa:2280003",
     "ncaa:2280004",
     "ncaa:2280005",
     "ncaa:2280006",
     "ncaa:2280007",
     "ncaa:2280008",
     "ncaa:2280009",
     "ncaa:2280010",
     "ncaa:2280011",
     "ncaa:2280012",
     "ncaa:2280013",
     "ncaa:2280014",
     "ncaa:2280015",
     "ncaa:2280016",
     "ncaa:2280017",
     "ncaa:2280018",
     "ncaa:2280019",
     "ncaa:2280020",
     "ncaa:2280021",
     "ncaa:2280022",
     "ncaa:2280023",
     "ncaa:2280024",
     "ncaa:2280025",
     "ncaa:2280026",
     "ncaa:2280027",
     "ncaa:2280029",
     "ncaa:2280030",
     "ncaa:2280031",
     "ncaa:2280032",
     "ncaa:2280033",
     "ncaa:2280034",
     "ncaa:2280036",
     "ncaa:2280037",
     "ncaa:2280038",
     "ncaa:2280039",
     "ncaa:2280040",
     "ncaa:2280041",
     "ncaa:2280042"
    ],
    "2022-12-02": [
     "ncaa:2279969",
     "ncaa:2354342",
     "ncaa:2354487"
    ],
    "2022-12-03": [
     "ncaa:2353729",
     "ncaa:2354148",
     "ncaa:2354149",
     "ncaa:2354173",
     "ncaa:2354343",
     "ncaa:2354424",
     "ncaa:2354425",
     "ncaa:2354442"
    ],
    "2022-12-10": [
     "ncaa:2280044"
    ],
    "2022-12-16": [
     "ncaa:2354488",
     "ncaa:2354676"
    ],
    "2022-12-17": [
     "ncaa:2354652",
     "ncaa:2354656",
     "ncaa:2354657",
     "ncaa:2354677",
     "ncaa:2354678",
     "ncaa:2354679"
    ],
    "2022-12-19": [
     "ncaa:2354658"
    ],
    "2022-12-20": [
     "ncaa:2354659",
     "ncaa:2354680"
    ],
    "2022-12-21": [
     "ncaa:2354700"
    ],
    "2022-12-22": [
     "ncaa:2354701"
    ],
    "2022-12-23": [
     "ncaa:2354702",
     "ncaa:2354703"
    ],
    "2022-12-24": [
     "ncaa:2354681"
    ],
    "2022-12-26": [
     "ncaa:2354683"
    ],
    "2022-12-27": [
     "ncaa:2354684",
     "ncaa:2354685",
     "ncaa:2354704",
     "ncaa:2354705"
    ],
    "2022-12-28": [
     "ncaa:2354706",
     "ncaa:2354707",
     "ncaa:2354708",
     "ncaa:2354709"
    ],
    "2022-12-29": [
     "ncaa:2354710",
     "ncaa:2354711",
     "ncaa:2354712"
    ],
    "2022-12-30": [
     "ncaa:2354650",
     "ncaa:2354713",
     "ncaa:2354714",
     "ncaa:2354715",
     "ncaa:2354716"
    ],
    "2022-12-31": [
     "ncaa:2354653",
     "ncaa:2354670",
     "ncaa:2354717",
     "ncaa:2354718"
    ],
    "2023-01-02": [
     "ncaa:2354668",
     "ncaa:2354719",
     "ncaa:2354720",
     "ncaa:2354721"
    ],
    "2023-01-09": [
     "ncaa:2354669"
    ]
   },
   "2023": {
    "2023-08-26": [
     "ncaa:3150887",
     "ncaa:3150889",
     "ncaa:3150890",
     "ncaa:3150891",
     "ncaa:3150892",
     "ncaa:3150893",
     "ncaa:3150896"
    ],
    "2023-08-31": [
     "ncaa:3146741",
     "ncaa:3150904",
     "ncaa:3150962",
     "ncaa:3150968"
    ],
    "2023-09-01": [
     "ncaa:3150971",
     "ncaa:3150982",
     "ncaa:3169707"
    ],
    "2023-09-02": [
     "ncaa:3146431",
     "ncaa:3146446",
     "ncaa:3146958",
     "ncaa:3147200",
     "ncaa:3150990",
     "ncaa:3150991",
     "ncaa:3150993",
     "ncaa:3151007",
     "ncaa:3151012",
     "ncaa:3151024",
     "ncaa:3151028",
     "ncaa:3151029",
     "ncaa:3151097",
     "ncaa:3151102",
     "ncaa:3151103",
     "ncaa:3151104",
     "ncaa:3151107",
     "ncaa:3151111",
     "ncaa:3151118",
     "ncaa:3151121",
     "ncaa:3151133",
     "ncaa:3151139",
     "ncaa:3151140",
     "ncaa:3151155",
     "ncaa:3151163",
     "ncaa:3151173",
     "ncaa:3151181",
     "ncaa:3151182",
     "ncaa:3151183",
     "ncaa:3151184",
     "ncaa:3154304",
     "ncaa:3169710",
     "ncaa:3728024"
    ],
    "2023-09-03": [
     "ncaa:3147123",
     "ncaa:3151185",
     "ncaa:3151189"
    ],
    "2023-09-04": [
     "ncaa:3151190"
    ],
    "2023-09-08": [
     "ncaa:3147180"
    ],
    "2023-09-09": [
     "ncaa:3146421",
     "ncaa:3146453",
     "ncaa:3146681",
     "ncaa:3146977",
     "ncaa:3146993",
     "ncaa:3147078",
     "ncaa:3147451",
     "ncaa:3147454",
     "ncaa:3151207",
     "ncaa:3151217",
     "ncaa:3151218",
     "ncaa:3151219",
     "ncaa:3151231",
     "ncaa:3151250",
     "ncaa:3151252",
     "ncaa:3151338",
     "ncaa:3151343",
     "ncaa:3151346",
     "ncaa:3151348",
     "ncaa:3151357",
     "ncaa:3151358",
     "ncaa:3151367",
     "ncaa:3151368",
     "ncaa:3151372",
     "ncaa:3151373",
     "ncaa:3151375",
     "ncaa:3151383",
     "ncaa:3151400",
     "ncaa:3151401",
     "ncaa:3151412",
     "ncaa:3151415",
     "ncaa:3151426",
     "ncaa:3151427",
     "ncaa:3151430",
     "ncaa:3151431",
     "ncaa:3151439",
     "ncaa:3151442",
     "ncaa:3151443",
     "ncaa:3151445",
     "ncaa:3151459",
     "ncaa:3151466",
     "ncaa:3151472",
     "ncaa:3151473",
     "ncaa:3151474",
     "ncaa:3151475",
     "ncaa:3169711"
    ],
    "2023-09-14": [
     "ncaa:3151476"
    ],
    "2023-09-15": [
     "ncaa:3147455",
     "ncaa:3151478",
     "ncaa:3151479"
    ],
    "2023-09-16": [
     "ncaa:3146427",
     "ncaa:3146432",
     "ncaa:3146440",
     "ncaa:3146746",
     "ncaa:3146979",
     "ncaa:3147033",
     "ncaa:3147081",
     "ncaa:3147124",
     "ncaa:3147201",
     "ncaa:3151490",
     "ncaa:3151492",
     "ncaa:3151507",
     "ncaa:3151514",
     "ncaa:3151518",
     "ncaa:3151532",
     "ncaa:3151535",
     "ncaa:3151632",
     "ncaa:3151650",
     "ncaa:3151651",
     "ncaa:3151653",
     "ncaa:3151657",
     "ncaa:3151659",
     "ncaa:3151660",
     "ncaa:3151661",
     "ncaa:3151662",
     "ncaa:3151669",
     "ncaa:3151676",
     "ncaa:3151688",
     "ncaa:3151691",
     "ncaa:3151724",
     "ncaa:3151725",
     "ncaa:3151728",
     "ncaa:3151729",
     "ncaa:3151741",
     "ncaa:3151742",
     "ncaa:3151746",
     "ncaa:3151747",
     "ncaa:3151754",
     "ncaa:3151760",
     "ncaa:3151764",
     "ncaa:3151765",
     "ncaa:3151766",
     "ncaa:3151767",
     "ncaa:3151768",
     "ncaa:3151769",
     "ncaa:3151770",
     "ncaa:3151771",
     "ncaa:3154299",
     "ncaa:3169708",
     "ncaa:3169712"
    ],
    "2023-09-21": [
     "ncaa:3151773"
    ],
    "2023-09-22": [
     "ncaa:3146433",
     "ncaa:3151776",
     "ncaa:3151777",
     "ncaa:3151778"
    ],
    "2023-09-23": [
     "ncaa:3146422",
     "ncaa:3146428",
     "ncaa:3146748",
     "ncaa:3147034",
     "ncaa:3147082",
     "ncaa:3147181",
     "ncaa:3147450",
     "ncaa:3151779",
     "ncaa:3151780",
     "ncaa:3151781",
     "ncaa:3151782",
     "ncaa:3151783",
     "ncaa:3151784",
     "ncaa:3151785",
     "ncaa:3151786",
     "ncaa:3151787",
     "ncaa:3151788",
     "ncaa:3151789",
     "ncaa:3151791",
     "ncaa:3151792",
     "ncaa:3151793",
     "ncaa:3151796",
     "ncaa:3151797",
     "ncaa:3151798",
     "ncaa:3151799",
     "ncaa:3151801",
     "ncaa:3151802",
     "ncaa:3151803",
     "ncaa:3151804",
     "ncaa:3151805",
     "ncaa:3151806",
     "ncaa:3151807",
     "ncaa:3151808",
     "ncaa:3151809",
     "ncaa:3151810",
     "ncaa:3151811",
     "ncaa:3151812",
     "ncaa:3151813",
     "ncaa:3151814",
     "ncaa:3151815",
     "ncaa:3151816",
     "ncaa:3151817",
     "ncaa:3151819",
     "ncaa:3151967",
     "ncaa:3151969",
     "ncaa:3151982",
     "ncaa:3151985",
     "ncaa:3151998",
     "ncaa:3152001",
     "ncaa:3152008",
     "ncaa:3152020",
     "ncaa:3152022",
     "ncaa:3152031",
     "ncaa:3152032",
     "ncaa:3152040",
     "ncaa:3152043",
     "ncaa:3152044",
     "ncaa:3154301"
    ],
    "2023-09-28": [
     "ncaa:3152045",
     "ncaa:3152046",
     "ncaa:3152047"
    ],
    "2023-09-29": [
     "ncaa:3152048",
     "ncaa:3152053",
     "ncaa:3152055",
     "ncaa:3152056"
    ],
    "2023-09-30": [
     "ncaa:3146423",
     "ncaa:3146749",
     "ncaa:3146986",
     "ncaa:3147035",
     "ncaa:3147083",
     "ncaa:3147452",
     "ncaa:3152058",
     "ncaa:3152059",
     "ncaa:3152061",
     "ncaa:3152062",
     "ncaa:3152063",
     "ncaa:3152065",
     "ncaa:3152066",
     "ncaa:3152067",
     "ncaa:3152068",
     "ncaa:3152069",
     "ncaa:3152071",
     "ncaa:3152072",
     "ncaa:3152073",
     "ncaa:3152074",
     "ncaa:3152075",
     "ncaa:3152076",
     "ncaa:3152077",
     "ncaa:3152079",
     "ncaa:3152080",
     "ncaa:3152083",
     "ncaa:3152084",
     "ncaa:3152085",
     "ncaa:3152086",
     "ncaa:3152087",
     "ncaa:3152088",
     "ncaa:3152089",
     "ncaa:3152090",
     "ncaa:3152091",
     "ncaa:3152092",
     "ncaa:3152093",
     "ncaa:3152094",
     "ncaa:3152095",
     "ncaa:3152096",
     "ncaa:3152104",
     "ncaa:3152135",
     "ncaa:3152221",
     "ncaa:3152261",
     "ncaa:3152274",
     "ncaa:3152275",
     "ncaa:3152298",
     "ncaa:3152318",
     "ncaa:3152330",
     "ncaa:3954422"
    ],
    "2023-10-04": [
     "ncaa:3152340",
     "ncaa:3152341"
    ],
    "2023-10-05": [
     "ncaa:3152342",
     "ncaa:3152344"
    ],
    "2023-10-06": [
     "ncaa:3147036",
     "ncaa:3152345"
    ],
    "2023-10-07": [
     "ncaa:3146434",
     "ncaa:3146441",
     "ncaa:3146447",
     "ncaa:3146758",
     "ncaa:3152349",
     "ncaa:3152350",
     "ncaa:3152351",
     "ncaa:3152354",
     "ncaa:3152355",
     "ncaa:3152356",
     "ncaa:3152357",
     "ncaa:3152359",
     "ncaa:3152360",
     "ncaa:3152361",
     "ncaa:3152362",
     "ncaa:3152363",
     "ncaa:3152364",
     "ncaa:3152365",
     "ncaa:3152366",
     "ncaa:3152368",
     "ncaa:3152369",
     "ncaa:3152371",
     "ncaa:3152372",
     "ncaa:3152373",
     "ncaa:3152374",
     "ncaa:3152375",
     "ncaa:3152376",
     "ncaa:3152377",
     "ncaa:3152378",
     "ncaa:3152379",
     "ncaa:3152380",
     "ncaa:3152381",
     "ncaa:3152382",
     "ncaa:3152383",
     "ncaa:3152386",
     "ncaa:3152405",
     "ncaa:3152563",
     "ncaa:3152565",
     "ncaa:3152566",
     "ncaa:3152567",
     "ncaa:3152568",
     "ncaa:3152569",
     "ncaa:3152604"
    ],
    "2023-10-10": [
     "ncaa:3152624",
     "ncaa:3152625",
     "ncaa:3152626"
    ],
    "2023-10-11": [
     "ncaa:3152627",
     "ncaa:3152628"
    ],
    "2023-10-12": [
     "ncaa:3152629",
     "ncaa:3152632"
    ],
    "2023-10-13": [
     "ncaa:3152633",
     "ncaa:3152634",
     "ncaa:3152635"
    ],
    "2023-10-14": [
     "ncaa:3146429",
     "ncaa:3146442",
     "ncaa:3147084",
     "ncaa:3147140",
     "ncaa:3147202",
     "ncaa:3147456",
     "ncaa:3152636",
     "ncaa:3152637",
     "ncaa:3152638",
     "ncaa:3152639",
     "ncaa:3152640",
     "ncaa:3152641",
     "ncaa:3152642",
     "ncaa:3152643",
     "ncaa:3152644",
     "ncaa:3152645",
     "ncaa:3152646",
     "ncaa:3152647",
     "ncaa:3152648",
     "ncaa:3152649",
     "ncaa:3152651",
     "ncaa:3152652",
     "ncaa:3152653",
     "ncaa:3152654",
     "ncaa:3152658",
     "ncaa:3152659",
     "ncaa:3152660",
     "ncaa:3152661",
     "ncaa:3152662",
     "ncaa:3152663",
     "ncaa:3152664",
     "ncaa:3152665",
     "ncaa:3152666",
     "ncaa:3152667",
     "ncaa:3152674",
     "ncaa:3152837",
     "ncaa:3152867",
     "ncaa:3152868",
     "ncaa:3152869",
     "ncaa:3152872",
     "ncaa:3152886",
     "ncaa:3152890",
     "ncaa:3152892",
     "ncaa:3152899",
     "ncaa:3152917"
    ],
    "2023-10-17": [
     "ncaa:3152918",
     "ncaa:3152919",
     "ncaa:3152920"
    ],
    "2023-10-18": [
     "ncaa:3152921",
     "ncaa:3152922"
    ],
    "2023-10-19": [
     "ncaa:3152923",
     "ncaa:3152925"
    ],
    "2023-10-20": [
     "ncaa:3152927"
    ],
    "2023-10-21": [
     "ncaa:3146435",
     "ncaa:3146443",
     "ncaa:3146448",
     "ncaa:3147037",
     "ncaa:3147085",
     "ncaa:3152929",
     "ncaa:3152930",
     "ncaa:3152931",
     "ncaa:3152934",
     "ncaa:3152935",
     "ncaa:3152936",
     "ncaa:3152937",
     "ncaa:3152938",
     "ncaa:3152939",
     "ncaa:3152940",
     "ncaa:3152941",
     "ncaa:3152942",
     "ncaa:3152943",
     "ncaa:3152944",
     "ncaa:3152945",
     "ncaa:3152947",
     "ncaa:3152948",
     "ncaa:3152949",
     "ncaa:3152950",
     "ncaa:3152951",
     "ncaa:3152952",
     "ncaa:3152953",
     "ncaa:3152954",
     "ncaa:3152955",
     "ncaa:3152956",
     "ncaa:3152957",
     "ncaa:3152958",
     "ncaa:3152959",
     "ncaa:3152960",
     "ncaa:3152961",
     "ncaa:3152962",
     "ncaa:3152963",
     "ncaa:3152964",
     "ncaa:3152994",
     "ncaa:3153126",
     "ncaa:3153172",
     "ncaa:3153177",
     "ncaa:3153185",
     "ncaa:3153186",
     "ncaa:3153207",
     "ncaa:3169709"
    ],
    "2023-10-24": [
     "ncaa:3153215",
     "ncaa:3153216"
    ],
    "2023-10-25": [
     "ncaa:3153217",
     "ncaa:3153218"
    ],
    "2023-10-26": [
     "ncaa:3153221",
     "ncaa:3153222"
    ],
    "2023-10-27": [
     "ncaa:3153225"
    ],
    "2023-10-28": [
     "ncaa:3146449",
     "ncaa:3146760",
     "ncaa:3147000",
     "ncaa:3147086",
     "ncaa:3153226",
     "ncaa:3153228",
     "ncaa:3153229",
     "ncaa:3153230",
     "ncaa:3153231",
     "ncaa:3153232",
     "ncaa:3153233",
     "ncaa:3153234",
     "ncaa:3153236",
     "ncaa:3153237",
     "ncaa:3153238",
     "ncaa:3153239",
     "ncaa:3153241",
     "ncaa:3153242",
     "ncaa:3153243",
     "ncaa:3153244",
     "ncaa:3153245",
     "ncaa:3153246",
     "ncaa:3153247",
     "ncaa:3153248",
     "ncaa:3153249",
     "ncaa:3153251",
     "ncaa:3153253",
     "ncaa:3153254",
     "ncaa:3153255",
     "ncaa:3153256",
     "ncaa:3153257",
     "ncaa:3153258",
     "ncaa:3153259",
     "ncaa:3153260",
     "ncaa:3153261",
     "ncaa:3153262",
     "ncaa:3153263",
     "ncaa:3153264",
     "ncaa:3153292",
     "ncaa:3153452",
     "ncaa:3153484",
     "ncaa:3153486",
     "ncaa:3153497",
     "ncaa:3153505",
     "ncaa:3153509",
     "ncaa:3153517",
     "ncaa:3154300"
    ],
    "2023-10-31": [
     "ncaa:3153518",
     "ncaa:3153519"
    ],
    "2023-11-01": [
     "ncaa:3153520",
     "ncaa:3153521"
    ],
    "2023-11-02": [
     "ncaa:3153522",
     "ncaa:3153523",
     "ncaa:3153526"
    ],
    "2023-11-03": [
     "ncaa:3153527",
     "ncaa:3153529"
    ],
    "2023-11-04": [
     "ncaa:3146436",
     "ncaa:3146450",
     "ncaa:3146763",
     "ncaa:3146994",
     "ncaa:3147001",
     "ncaa:3153530",
     "ncaa:3153531",
     "ncaa:3153533",
     "ncaa:3153534",
     "ncaa:3153535",
     "ncaa:3153536",
     "ncaa:3153537",
     "ncaa:3153538",
     "ncaa:3153539",
     "ncaa:3153540",
     "ncaa:3153541",
     "ncaa:3153542",
     "ncaa:3153543",
     "ncaa:3153545",
     "ncaa:3153546",
     "ncaa:3153547",
     "ncaa:3153548",
     "ncaa:3153549",
     "ncaa:3153550",
     "ncaa:3153551",
     "ncaa:3153554",
     "ncaa:3153556",
     "ncaa:3153557",
     "ncaa:3153558",
     "ncaa:3153559",
     "ncaa:3153560",
     "ncaa:3153561",
     "ncaa:3153562",
     "ncaa:3153563",
     "ncaa:3153564",
     "ncaa:3153565",
     "ncaa:3153566",
     "ncaa:3153567",
     "ncaa:3153568",
     "ncaa:3153569",
     "ncaa:3153570",
     "ncaa:3153571",
     "ncaa:3153630",
     "ncaa:3153714",
     "ncaa:3153807",
     "ncaa:3153811",
     "ncaa:3153813",
     "ncaa:3153816",
     "ncaa:3153824",
     "ncaa:3153826",
     "ncaa:3153827",
     "ncaa:3154302"
    ],
    "2023-11-07": [
     "ncaa:3153828",
     "ncaa:3153829",
     "ncaa:3153830"
    ],
    "2023-11-08": [
     "ncaa:3153831",
     "ncaa:3153832",
     "ncaa:3153833"
    ],
    "2023-11-09": [
     "ncaa:3153834",
     "ncaa:3153835"
    ],
    "2023-11-10": [
     "ncaa:3153839",
     "ncaa:3153840"
    ],
    "2023-11-11": [
     "ncaa:3146437",
     "ncaa:3146444",
     "ncaa:3146451",
     "ncaa:3146765",
     "ncaa:3147038",
     "ncaa:3147087",
     "ncaa:3153842",
     "ncaa:3153843",
     "ncaa:3153846",
     "ncaa:3153848",
     "ncaa:3153849",
     "ncaa:3153850",
     "ncaa:3153851",
     "ncaa:3153853",
     "ncaa:3153854",
     "ncaa:3153855",
     "ncaa:3153856",
     "ncaa:3153857",
     "ncaa:3153858",
     "ncaa:3153860",
     "ncaa:3153861",
     "ncaa:3153863",
     "ncaa:3153864",
     "ncaa:3153865",
     "ncaa:3153866",
     "ncaa:3153867",
     "ncaa:3153869",
     "ncaa:3153871",
     "ncaa:3153872",
     "ncaa:3153873",
     "ncaa:3153874",
     "ncaa:3153875",
     "ncaa:3153876",
     "ncaa:3153877",
     "ncaa:3153878",
     "ncaa:3153879",
     "ncaa:3153880",
     "ncaa:3153881",
     "ncaa:3153882",
     "ncaa:3153883",
     "ncaa:3153884",
     "ncaa:3153885",
     "ncaa:3153886",
     "ncaa:3153891",
     "ncaa:3154004",
     "ncaa:3154079",
     "ncaa:3154096",
     "ncaa:3154097",
     "ncaa:3154101",
     "ncaa:3154109",
     "ncaa:3154111",
     "ncaa:3154112",
     "ncaa:3154116",
     "ncaa:3169705"
    ],
    "2023-11-14": [
     "ncaa:3154117",
     "ncaa:3154118",
     "ncaa:3154119"
    ],
    "2023-11-15": [
     "ncaa:3154120",
     "ncaa:3154121"
    ],
    "2023-11-16": [
     "ncaa:3154123"
    ],
    "2023-11-17": [
     "ncaa:3154124",
     "ncaa:3154125"
    ],
    "2023-11-18": [
     "ncaa:3146425",
     "ncaa:3146452",
     "ncaa:3146454",
     "ncaa:3147002",
     "ncaa:3147088",
     "ncaa:3154126",
     "ncaa:3154128",
     "ncaa:3154129",
     "ncaa:3154130",
     "ncaa:3154131",
     "ncaa:3154132",
     "ncaa:3154133",
     "ncaa:3154134",
     "ncaa:3154135",
     "ncaa:3154136",
     "ncaa:3154137",
     "ncaa:3154139",
     "ncaa:3154140",
     "ncaa:3154141",
     "ncaa:3154143",
     "ncaa:3154144",
     "ncaa:3154145",
     "ncaa:3154146",
     "ncaa:3154147",
     "ncaa:3154148",
     "ncaa:3154150",
     "ncaa:3154151",
     "ncaa:3154152",
     "ncaa:3154153",
     "ncaa:3154154",
     "ncaa:3154155",
     "ncaa:3154156",
     "ncaa:3154157",
     "ncaa:3154158",
     "ncaa:3154159",
     "ncaa:3154160",
     "ncaa:3154161",
     "ncaa:3154162",
     "ncaa:3154163",
     "ncaa:3154164",
     "ncaa:3154172",
     "ncaa:3154180",
     "ncaa:3154181",
     "ncaa:3154185",
     "ncaa:3154199",
     "ncaa:3154203",
     "ncaa:3154209",
     "ncaa:3154210",
     "ncaa:3154216",
     "ncaa:3154227",
     "ncaa:3154228",
     "ncaa:3154231",
     "ncaa:3154235",
     "ncaa:3154236",
     "ncaa:3154298",
     "ncaa:3154303"
    ],
    "2023-11-21": [
     "ncaa:3154237",
     "ncaa:3154238"
    ],
    "2023-11-23": [
     "ncaa:3154240"
    ],
    "2023-11-24": [
     "ncaa:3146445",
     "ncaa:3154241",
     "ncaa:3154242",
     "ncaa:3154243",
     "ncaa:3154244",
     "ncaa:3154245",
     "ncaa:3154246",
     "ncaa:3154247",
     "ncaa:3154248",
     "ncaa:3154249",
     "ncaa:3154250",
     "ncaa:3154251",
     "ncaa:3169706"
    ],
    "2023-11-25": [
     "ncaa:3146430",
     "ncaa:3146438",
     "ncaa:3146987",
     "ncaa:3147125",
     "ncaa:3147182",
     "ncaa:3154252",
     "ncaa:3154253",
     "ncaa:3154254",
     "ncaa:3154255",
     "ncaa:3154256",
     "ncaa:3154257",
     "ncaa:3154258",
     "ncaa:3154259",
     "ncaa:3154260",
     "ncaa:3154261",
     "ncaa:3154262",
     "ncaa:3154263",
     "ncaa:3154264",
     "ncaa:3154265",
     "ncaa:3154266",
     "ncaa:3154267",
     "ncaa:3154268",
     "ncaa:3154269",
     "ncaa:3154270",
     "ncaa:3154271",
     "ncaa:3154272",
     "ncaa:3154273",
     "ncaa:3154274",
     "ncaa:3154275",
     "ncaa:3154276",
     "ncaa:3154277",
     "ncaa:3154278",
     "ncaa:3154279",
     "ncaa:3154280",
     "ncaa:3154281",
     "ncaa:3154282",
     "ncaa:3154283",
     "ncaa:3154284",
     "ncaa:3154285",
     "ncaa:3154286",
     "ncaa:3154287",
     "ncaa:3154288",
     "ncaa:3154290",
     "ncaa:3154291",
     "ncaa:3154292",
     "ncaa:3154293",
     "ncaa:3154294",
     "ncaa:3154295",
     "ncaa:3154296"
    ],
    "2023-12-01": [
     "ncaa:4471884",
     "ncaa:4472105"
    ],
    "2023-12-02": [
     "ncaa:4471886",
     "ncaa:4471887",
     "ncaa:4471888",
     "ncaa:4471889",
     "ncaa:4472106",
     "ncaa:4472251",
     "ncaa:4472252",
     "ncaa:4472267"
    ],
    "2023-12-09": [
     "ncaa:3154297"
    ],
    "2023-12-16": [
     "ncaa:4472584",
     "ncaa:4472585",
     "ncaa:4472586",
     "ncaa:4472588",
     "ncaa:4472589",
     "ncaa:4472590"
    ],
    "2023-12-18": [
     "ncaa:4472592"
    ],
    "2023-12-19": [
     "ncaa:4472593"
    ],
    "2023-12-21": [
     "ncaa:4472594"
    ],
    "2023-12-22": [
     "ncaa:4472595"
    ],
    "2023-12-23": [
     "ncaa:4472492",
     "ncaa:4472596",
     "ncaa:4472597",
     "ncaa:4472598",
     "ncaa:4472599",
     "ncaa:4472601"
    ],
    "2023-12-26": [
     "ncaa:4472602",
     "ncaa:4472603",
     "ncaa:4472606"
    ],
    "2023-12-27": [
     "ncaa:4472609",
     "ncaa:4472611",
     "ncaa:4472614",
     "ncaa:4472615"
    ],
    "2023-12-28": [
     "ncaa:4472616",
     "ncaa:4472617",
     "ncaa:4472618",
     "ncaa:4472619"
    ],
    "2023-12-29": [
     "ncaa:4472587",
     "ncaa:4472591",
     "ncaa:4472620"
    ],
    "2023-12-30": [
     "ncaa:4472622",
     "ncaa:4472623",
     "ncaa:4472624",
     "ncaa:4472625"
    ],
    "2024-01-01": [
     "ncaa:4472564",
     "ncaa:4472565",
     "ncaa:4472643",
     "ncaa:4472644",
     "ncaa:4472645"
    ],
    "2024-01-08": [
     "ncaa:4472563"
    ]
   }
  },
  "excluded_games": {
   "ncaa:1519847": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519850": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519885": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519889": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519905": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519917": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519934": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519935": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519936": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519939": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519940": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1519941": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520004": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520010": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520011": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520014": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520017": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520018": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520020": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520036": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520050": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520053": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520056": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520057": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520062": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520064": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520067": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520070": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520071": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520072": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520074": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520075": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520076": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520077": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520081": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520082": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520085": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520087": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520088": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520116": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520131": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520133": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520135": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520165": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520167": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520263": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520326": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1520345": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735108": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735109": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735118": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735121": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735123": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735135": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735138": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735139": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735141": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735142": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735143": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735144": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735145": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735146": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735147": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735148": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735149": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735150": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735151": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735156": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735158": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735159": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735160": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735162": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735169": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735176": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735179": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735180": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735183": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735187": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735188": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735193": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735201": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735210": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735211": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735212": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735215": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735217": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735223": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735224": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735225": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735226": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735230": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735231": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735421": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1735503": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:196973": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:196995": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197023": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197025": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197026": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197030": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197031": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197032": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197043": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197046": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197054": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197060": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197064": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197094": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197106": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197125": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197132": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197135": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197140": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197143": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197146": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197148": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197164": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197195": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197201": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197202": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197225": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197242": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197243": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197245": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197255": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197257": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197265": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197266": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197267": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197268": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197269": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197270": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197290": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197294": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197394": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974069": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974072": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974074": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974077": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974079": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974080": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974082": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974083": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974085": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974088": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974089": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974094": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974095": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974096": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974099": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974100": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974101": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974102": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974106": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974108": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974110": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974112": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974118": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:197412": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974123": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974125": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974131": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974134": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974138": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974139": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974143": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974149": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974150": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974151": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974152": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974153": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974155": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974192": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974195": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974202": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974302": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1974383": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976128": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976151": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976161": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976256": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976319": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976331": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976689": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976691": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976731": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976748": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976749": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976768": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976788": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976890": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976911": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976912": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976928": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976945": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976946": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976968": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976969": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1976995": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1977005": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1977048": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1977088": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1977171": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1977268": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1977533": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1977695": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1977708": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1987800": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:1989339": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081755": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081756": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081757": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081758": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081763": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081798": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081806": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081809": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081830": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081834": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081835": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081844": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081850": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081855": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081860": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081865": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081866": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081867": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081868": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081870": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081871": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081888": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081898": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081959": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081968": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081971": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081972": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081973": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081975": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081976": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081977": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081978": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081982": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2081991": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082003": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082031": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082039": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082042": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082056": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082062": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082063": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082068": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082069": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082071": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082072": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082073": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082074": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082075": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082079": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2082080": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276460": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276462": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276464": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276467": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276468": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276471": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276472": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276504": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276522": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276541": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276546": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276554": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276555": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276563": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276574": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276575": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276576": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276577": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276584": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276594": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276595": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276600": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276601": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276605": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276616": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276681": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276690": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276693": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276694": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276695": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276697": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276699": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276703": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276708": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276717": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276733": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276744": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276760": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276763": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276764": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276766": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276767": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276769": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276771": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276775": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276785": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276786": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276787": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276788": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276790": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:2276794": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3146400": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3146431": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3146446": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3146741": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3146958": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3147123": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3147200": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150887": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150889": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150890": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150891": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150892": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150893": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150896": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150904": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150962": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150968": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150971": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150982": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150990": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150991": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3150993": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151007": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151012": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151024": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151028": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151029": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151097": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151102": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151103": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151104": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151107": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151111": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151118": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151121": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151133": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151139": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151140": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151155": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151163": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151173": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151181": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151182": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151183": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151184": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151185": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151189": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151190": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3151348": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3154304": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3169707": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3169710": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:3728024": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60161": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60163": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60166": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60167": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60176": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60178": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60179": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60214": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60230": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60235": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60252": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60260": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60262": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60264": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60265": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60267": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60281": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60302": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60304": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60313": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60323": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60330": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60335": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60336": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60344": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60347": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60351": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60355": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60358": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60375": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60397": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60424": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60431": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60432": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60442": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60445": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60463": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60464": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60465": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60466": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60467": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60469": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60484": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60486": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR",
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60601": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60645": [
    "A_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ],
   "ncaa:60735": [
    "B_CALENDAR_NO_ELIGIBLE_SAME_SEASON_PRIOR"
   ]
  },
  "parent_witness_lines_sha256": "035d7717888c7529400942e4a0edd27726a9441d71ce6ce7cc9530f61f9da846",
  "counts": {
   "targets": 5875,
   "views": 11750,
   "common_support_games": 5465,
   "excluded_games": 410,
   "fit_season_common_support_games": 4729,
   "comparison_common_support_games": 736,
   "qualifications": 5875,
   "features": 11750,
   "parameters": 2,
   "estimates": 23500,
   "scores": 11750,
   "witnesses": 29375,
   "summary": 70,
   "census": 1
  },
  "keys_sha256": {
   "qualifications": "10771bd00e37f324a489ccce183a1d4ae3f7dad110306bea78b4a1cc06ea5b9f",
   "features": "231946b883512016bb5bb75a596134875283536e3c2f70cf302edc8d699a6ead",
   "parameters": "6491964542e7b9ceeaa4cf0d064fdb06760ffc16d2060874ed608945ac9d7ffc",
   "estimates": "b3b617d5899cfc67198ab8f054f8d55ddb52b7078ce0d8fb1bd51b186b79f171",
   "scores": "ae22bb178f5e1e14fe640bf84d085172421c74eb938c5fff4a223b92e68f3e3e",
   "witnesses": "651e6d7b922913674279e1a8aeaf07d70dd1280b24c6a1f6e7b68c309392eb55",
   "summary": "e360d7e588e85f55f01ead6bee5e68a4393b241b0c21304c3b879c771a6d378e",
   "census": "7969bf2d3a9ceff9f774531d05be1923d0719b2b75db0e145e8af7b149aaf71f"
  }
 }
}''')
#: The canonical release profile the create-only build reproduces (identities and counts only; None until the first
#: canonical write).
CONTEXT_PROFILE: dict[str, Any] | None = json.loads(r'''{
 "database_identity": "bb30768dc7279009c6abd41365d71ed9e6fc28f184c3328a67f68109cc5a2783",
 "content_identity": "1b7a8286d33a9a55a55bb67ddae2f6357d0c8ddff935d675ea735763c925e784",
 "database_sha256": "35f3ea2e56ed24fa1a6569e2db3e4200b02d635ff7d01889f26359a367ef725c",
 "database_bytes": 13619200,
 "contract_sha256": "9b74dfe73d9d4236752d2c173e0effe284044801ed73c7bf40082aa97a5677a5",
 "rules_sha256": "49018c0e54b83e05f166cdf6ea5dfa62ae79974c5ff41ea8cebab2d76d06c3bf",
 "row_counts": {
  "census": 1,
  "estimates": 23500,
  "features": 11750,
  "parameters": 2,
  "qualifications": 5875,
  "scores": 11750,
  "summary": 70,
  "witnesses": 29375
 },
 "table_counts": {
  "blocks": 43,
  "meta": 11
 },
 "lines_sha256": {
  "census": "7e52794c82e1c08bd4f666cf795c06f0587aee3882804d514bbb0f004284f62a",
  "estimates": "f514f5b22152ef039457dff7e1100090b23506f6f8990b56a057585a15ba9248",
  "features": "33f1b8b98b04ff1f9eab1a9caa847b1913b0870752af530e773698fbdfd132ee",
  "parameters": "d7b2f2735412bf8749005b807fe83409ae3d34f26d5cf07e6e0b312954ff01b7",
  "qualifications": "32c583fd8065c9f028ec87645b79bea2058c9aeb9609b8dbbae508d287b7fb52",
  "scores": "2d5bc18dd8289c6f9ea41943d74d2441969e30ba8d58026e9649409c26996ef3",
  "summary": "b4b98a4a05d78dfd54b939edfe9469a5b6188f1982a56e57489147892d2a11d8",
  "witnesses": "b2741c43a247a74a7d0758c3d578ffb7c81f8587556578ad2076d51500678339"
 },
 "summary_sha256": "b4b98a4a05d78dfd54b939edfe9469a5b6188f1982a56e57489147892d2a11d8",
 "census_sha256": "7e52794c82e1c08bd4f666cf795c06f0587aee3882804d514bbb0f004284f62a"
}''')
# ---- END GENERATED ANCHORS ----
