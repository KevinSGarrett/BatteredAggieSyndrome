r"""National retrospective reference comparison over the accepted 2016-2023 targets (BAT-423 bounded research
contribution, Cycle #56 TP56-A01).

Every rule lives here, and the committed research contract
``configs/national_retrospective_reference_2016_2023_contract.json`` must equal these constants (the builder refuses
otherwise). The reader pins that contract's SHA-256 and the accepted parent identities (:data:`ANCHORS`).

Inputs, each verified and pinned before use:

* the accepted BAT-711 history-prefix database (targets, the two oriented views of each target, the separately
  classified target labels and the pool-member exclusions) through the accepted C47 loader, plus its out-of-scope
  payload naming the protected 2024/2025 contests by key and season only;
* the accepted BAT-710 parent population database (C38) for the 2016-2023 contest rows of the 11,528 eligible
  history-pool games (scores, dates, roles and contemporaneous division labels); rows outside 2016-2023 are never
  selected.

Derivation order (each step reads only what it names):

1. **pool** -- the parent's 2016-2023 contests through the seven frozen history predicates must equal the history's
   pool (targets plus pool-member exclusions) key for key.
2. **features** -- for each target and side, every pool game of that organization in the same season dated strictly
   before the target date, rederived from the parent rows (key, date, role, opponent, points) and required to equal the
   accepted history view's contributing contests and totals; games played, win rate with ties counting one half and
   the points-for, points-against and margin means; a missing rate is zero plus a missing indicator.
3. **Elo** -- the site-blind season Elo over every pool game exactly once: 1500 start per season and team, K 20, base
   10, scale 400, no site bonus, no offseason carry; games of one date use the ratings at the start of that date and
   their updates apply only afterward; a target's estimate precedes its own date's updates.
4. **estimates** -- the two unchanged C47 fixed models (their C47 records byte for byte), the Elo probability, and the
   paired zero-intercept L2 logistic probability and ridge expected margin fitted only on the 2016-2022 targets
   (training-only root-mean-square column scaling, every column the same penalty, weight 1/2 per orientation); one
   canonical game-grain value and its exact complement (probability) or negation (margin).
5. **labels** -- the C47 label records byte for byte (separate stage), the margin label their points difference.
6. **scores** -- one A-oriented record per target and model: Brier of the served probability, log loss with only its
   logarithm argument clipped to [1e-15, 1 - 1e-15]; ridge absolute and squared error of the served margin.
7. **parameters and summary** -- fitted coefficients, scales and convergence records; national, Texas A&M,
   first-four-team-games and cold-start slices by season, partition and pooled scope with fixed decile calibration
   tables and descriptive model-minus-null differences. Empty slices carry no fabricated mean.

Every record carries ``RETROSPECTIVE_REFERENCE_NOT_PIT_NOT_SKILL`` and ``UNTRUSTED_SHADOW``. Calendar order is not
publication time: nothing here is PIT eligible, a forecast, a calibration or evidence of predictive skill; 2023 is an
already-exposed out-of-fit development comparison, never blind; training-sample estimates are IN_SAMPLE and never BAS
label anchors.
"""
from __future__ import annotations

import gzip
import hashlib
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
from aggie_analytics.national_population import query as population_query
from aggie_analytics.retrospective_baseline import benchmark as bm
from aggie_analytics.retrospective_baseline import reference_fit as rf

# --------------------------------------------------------------------------------------------- identity and scope

POPULATION = "national_retrospective_reference_2016_2023"
DB_FILE = "national_retrospective_reference.sqlite"
CONTENT_SCHEMA = "BAS-RETROSPECTIVE-REFERENCE-CONTENT-1"
DATABASE_SCHEMA = "BAS-RETROSPECTIVE-REFERENCE-DATABASE-1"
DB_SCHEMA = "BAS-RETROSPECTIVE-REFERENCE-DB-1"
PAYLOAD_SCHEMA = "BAS-RETROSPECTIVE-REFERENCE-PAYLOAD-1"
CONTRACT_ID = "BAT-423-NATIONAL-RETROSPECTIVE-REFERENCE-2016-2023-V1.0"
TARGET_SEASONS = bm.TARGET_SEASONS
TRAINING_SEASONS = (2016, 2017, 2018, 2019, 2020, 2021, 2022)
COMPARISON_SEASONS = (2023,)
PROTECTED_SEASONS = bm.PROTECTED_SEASONS
FORWARD_SEASONS_FROM = bm.FORWARD_SEASONS_FROM
PARTITION_OF = bm.PARTITION_OF
SPLIT = bm.SPLIT
VIEWS = bm.VIEWS
EVIDENCE_LABEL = "RETROSPECTIVE_REFERENCE_NOT_PIT_NOT_SKILL"
PIT_STATE = bm.PIT_STATE
TRUST_STATE = "UNTRUSTED_SHADOW"
TAMU_KEY = "org:697"

#: Labels carried by the database meta and by every served response.
LABELS = {
    "evidence_label": EVIDENCE_LABEL,
    "observation_authority": "RETROSPECTIVE_OBSERVATION_ONLY",
    "pit_eligibility": PIT_STATE,
    "temporal_basis": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME",
    "forecast_status": "NOT_A_FORECAST_RETROSPECTIVE_RESEARCH_ONLY",
    "trust_state": TRUST_STATE,
    "predictive_skill": "NOT_ESTABLISHED",
    "calibration": "NOT_ESTABLISHED",
    "champion": "NO_CHAMPION_SELECTED",
    "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
    "fit_authority": "TP56_RESEARCH_AUTHORITY_2016_2022_DEVELOPMENT_FIT_ONLY",
    "comparison_2023": "ALREADY_EXPOSED_OUT_OF_FIT_DEVELOPMENT_COMPARISON_NOT_BLIND",
    "bas_label_anchor": "NOT_PERMITTED",
    "selection": "EXPLICIT_REFERENCE_SELECTION_ONLY_NEVER_A_DEFAULT",
}
#: Labels carried by every new record (the C47 records keep their own labels byte for byte).
RECORD_LABELS = {"evidence_label": EVIDENCE_LABEL, "pit_eligibility": PIT_STATE, "trust_state": TRUST_STATE}

MODEL_NULL = bm.MODEL_NULL
MODEL_SMOOTHED = bm.MODEL_SMOOTHED
MODEL_ELO = "SITE_BLIND_ELO_REFERENCE_V1"
MODEL_LOGISTIC = "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1"
MODEL_RIDGE = "PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1"
MODEL_IDS = (MODEL_NULL, MODEL_SMOOTHED, MODEL_ELO, MODEL_LOGISTIC, MODEL_RIDGE)
C47_MODELS = (MODEL_NULL, MODEL_SMOOTHED)
PROBABILITY_MODELS = (MODEL_NULL, MODEL_SMOOTHED, MODEL_ELO, MODEL_LOGISTIC)
MARGIN_MODELS = (MODEL_RIDGE,)
LEARNED_MODELS = (MODEL_LOGISTIC, MODEL_RIDGE)

SIDE_FIELDS = ("games", "win_rate", "points_for_mean", "points_against_mean", "margin_mean")
COLUMNS = tuple([f"{f}_difference" for f in SIDE_FIELDS] + [f"{f}_missing_difference" for f in SIDE_FIELDS])

ELO = {"initial_rating": 1500, "k_factor": 20, "logistic_base": 10, "scale": 400, "site_bonus": 0,
       "offseason_carry": "NONE_EVERY_SEASON_AND_TEAM_RESTARTS_AT_1500",
       "tie_score": {"numerator": 1, "denominator": 2}}

MODELS: dict[str, dict[str, Any]] = {
    MODEL_NULL: bm.MODELS[MODEL_NULL],
    MODEL_SMOOTHED: bm.MODELS[MODEL_SMOOTHED],
    MODEL_ELO: {
        "model_id": MODEL_ELO, "version": 1, "family": "SITE_BLIND_SEASON_ELO", "output": "WIN_PROBABILITY",
        "formula": "R starts at 1500 per season and organization; for a game of A and B, E_A = 1/(1 + 10^((R_B - R_A)/400)), "
                   "S_A = 1 win, 0 loss, 1/2 tie, delta_A = 20 (S_A - E_A), delta_B = -delta_A; every game of one date "
                   "uses the ratings at the start of that date and the updates (math.fsum per organization) apply "
                   "after the date; p_A of a target = E_A from the ratings at the start of its own date",
        "parameters": ELO, "inputs": ["every eligible same-season history-pool game: date, organizations, points"],
        "pool": "each of the 11,528 eligible 2016-2023 history-pool games exactly once within its own season label",
        "fitted": False, "home_advantage": None, "role": "FIXED_RATING_REFERENCE",
        "distinct_from": "the historical BAT-655 national_elo and the preliminary Elo challenger contracts "
                         "(configs/elo_*_contract.json); none of their artifacts is read or changed"},
    MODEL_LOGISTIC: {
        "model_id": MODEL_LOGISTIC, "version": 1, "family": "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC",
        "output": "WIN_PROBABILITY", "columns": list(COLUMNS),
        "formula": "p = sigmoid(z . beta), z the training-RMS-scaled team-minus-opponent design, zero intercept",
        "objective": "mean weighted binary cross-entropy over the paired oriented training rows (weight 1/2 each) plus "
                     "(1/2) sum(beta_j^2) (lambda 1, every column)",
        "solver": {"method": "Newton from zero with the C37 deterministic partial-pivot solve",
                   "max_newton_steps": 100, "gradient_inf_norm_tolerance": "1e-10",
                   "backtracking": "step 1 halved at most 30 times until the objective does not increase",
                   "failure": "exhausted backtracking or no convergence is a recorded failure, never accepted"},
        "fit_seasons": list(TRAINING_SEASONS), "labels_used": ["DECISIVE"], "fitted": True, "home_advantage": None,
        "role": "LEARNED_PROBABILITY_REFERENCE"},
    MODEL_RIDGE: {
        "model_id": MODEL_RIDGE, "version": 1, "family": "PAIRED_ZERO_INTERCEPT_RIDGE",
        "output": "EXPECTED_MARGIN_ONLY_NO_PROBABILITY", "columns": list(COLUMNS),
        "formula": "margin_A = z . beta (team-minus-opponent points), zero intercept; no probability link and no score "
                   "distribution are defined",
        "objective": "mean weighted squared margin error over the paired oriented training rows (weight 1/2 each) "
                     "divided by two plus (1/2) sum(beta_j^2) (lambda 1, every column)",
        "solver": {"method": "regularized normal equations with the C37 deterministic partial-pivot solve",
                   "residual_inf_norm_tolerance": "1e-8", "finite_coefficients": True},
        "fit_seasons": list(TRAINING_SEASONS), "labels_used": ["DECISIVE", "TIE"], "fitted": True,
        "home_advantage": None, "role": "LEARNED_MARGIN_REFERENCE"},
}

#: The frozen numerical rules (TP56 section 3).
NUMERIC_CONTRACT = {
    "arithmetic": "IEEE-754 binary64 in a fixed order; every reduction math.fsum; math.exp, math.log1p, math.log, "
                  "math.sqrt and float ** of the pinned CPython 3.12.10; stable sigmoid and cross-entropy",
    "features": "exact rationals in lowest terms {numerator, denominator}; a design value is the correctly rounded "
                "binary64 of the exact team-minus-opponent difference",
    "scaling": "column j scale = sqrt(fsum(x_ij^2) / n) over the 2016-2022 training oriented rows (no centering); "
               "a zero scale uses 1; z_ij = x_ij / scale_j",
    "decimal12": "every served binary64 value is its exact decimal expansion rounded half-even to 12 places, negative "
                 "zero normalized to 0.000000000000, serialized as a JSON string; a probability complement and a "
                 "margin negation are exact decimal operations on that string",
    "probability": "0 <= served p <= 1; p_A + p_B = 1 exactly in decimal; ridge serves no probability",
    "brier": "(p_served - y)^2 as an exact rational of the served decimal (C47 models: of their exact rational)",
    "log_loss": "-ln(clip(q)) with q = p_served when y = 1 and 1 - p_served when y = 0, q the correctly rounded "
                "binary64 of the exact value, clip to [1e-15, 1 - 1e-15] applied only to the logarithm argument "
                "(diagnostic convention CLIPPED_LOG_ARGUMENT_1E-15); repr() text; totals math.fsum in canonical target "
                "order, mean = total / count",
    "margin_errors": "absolute and squared error of the served margin against the integer label as exact rationals; "
                     "MAE and MSE exact rationals; RMSE = math.sqrt of the binary64 of the exact MSE (repr and decimal12)",
    "means_and_rates": "exact rationals with a 12-place half-even decimal display; an empty scope has null means",
    "counts": "JSON integers only; a boolean or an integral float is not a count",
    "unrounded_diagnostics": "fit objectives, gradient and residual norms, scales and coefficients are also kept as "
                             "repr() text in the parameter records' diagnostics (deterministic under the pinned "
                             "runtime, never served as rounded results)",
    "independent_tolerance": "an independent solver agrees within 1e-9 absolute on coefficients and predictions and "
                             "within 1e-8 on objective and gradient/residual; stored canonical payload bytes are exact "
                             "and deterministic under the pinned runtime",
    "canonical_json": "json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) as UTF-8",
}

SLICES = {
    "NATIONAL": "every accepted target",
    "TEXAS_AM": "targets with org:697 (Texas A&M) on either side",
    "FIRST_FOUR_TEAM_GAMES": "targets where either side has fewer than four eligible prior games",
    "COLD_START": "targets where either side has zero eligible prior games",
}
SLICE_IDS = tuple(SLICES)
DECILE_BINS = 10
CALIBRATION = {"orientation": "A (parent a side, the canonical game orientation)", "bins": DECILE_BINS,
               "rule": "bin i = min(floor(10 p), 9) of the served decimal probability; fixed edges i/10, the last bin "
                       "closed at 1; per bin count, exact mean served probability and exact observed A-win rate; "
                       "an empty bin has null means"}
LOG_CLIP = 1e-15
CLIP_CONVENTION = "CLIPPED_LOG_ARGUMENT_1E-15"

SCOPE = {
    "population": "ACCEPTED_BAT711_FBS_ESTIMAND_TARGETS_2016_2023",
    "target_seasons": list(TARGET_SEASONS), "training_seasons": list(TRAINING_SEASONS),
    "comparison_seasons": list(COMPARISON_SEASONS), "views_per_target": 2, "models": list(MODEL_IDS),
    "probability_models": list(PROBABILITY_MODELS), "margin_models": list(MARGIN_MODELS),
    "score_orientation": "A", "protected_seasons": list(PROTECTED_SEASONS),
    "forward_seasons_from": FORWARD_SEASONS_FROM, "slices": list(SLICE_IDS), "evidence_label": EVIDENCE_LABEL,
}

#: The accepted parents and the committed contract this reader binds (TP56 section 2, INPUT_BINDINGS).
ANCHORS: dict[str, Any] = {
    "contract_id": CONTRACT_ID,
    "contract_sha256": "3cfeff255bb29801b482b02611ad2c72c725d069e9f89d3911e86711af34bb31",
    "history": dict(bm.ANCHORS["history"]),
    "population": {
        "contract_id": "BAT-710-NATIONAL-DI-POPULATION-2016-2025-V1.3",
        "contract_sha256": "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903",
        "database_identity": "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27",
        "sqlite_sha256": "9c517af94b9e0c7105627397b8a8cd9f9fc0ee806493c126c842c5018c5ba172",
        "contest_identity": "ab4cdf1b0c1c06f20c9b143b9e0452fa71081670decc13c931830f50d140c4d8",
        "program_season_identity": "711e9dfcc35a181d51206099f41aa576424fc30ed61600811ab464074fb8f81e",
    },
    "benchmark": {
        "contract_id": bm.CONTRACT_ID,
        "contract_sha256": bm.ANCHORS["contract_sha256"],
        "database_identity": "627b25af33e6d920bce5612f5e9b9c411ce4b2a792e6ff9d53ab04cc7e5521a1",
        "sqlite_sha256": "b27a7eeb0eb5cba170e9a83cc71441547fb04f854779e5f8fe91e237addb77aa",
        "content_identity": "134c857ce6a2af0944438ad975249d386612d4468dbb3481be8f114e0ab19017",
    },
    "expected": {"targets": 5875, "views": 11750, "pool": 11528, "training_targets": 5087,
                 "comparison_targets": 788},
}

#: The materialized canonical reference this checkout pins (identities and counts only; the values stay in the private
#: data root), packaged with artifacts/data_lake/national_retrospective_reference_2016_2023_gate.json after the first
#: canonical write. None until then: the mounted genuine test skips.
REFERENCE_PROFILE: dict[str, Any] | None = None

IDENTITY_RE = bm.IDENTITY_RE
DEC12_RE = re.compile(r"-?(0|[1-9][0-9]*)\.[0-9]{12}\Z")
PREDICATES = ("DISPOSITION", "RECONCILIATION", "STATUS", "COMPETITIVE", "DATE", "ORG_KEYS", "SCORES")
LABEL_FIELDS = bm.LABEL_FIELDS + ("margin_label_a", "y")


class ReferenceError(ValueError):
    """A refused build input or a refused reference; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise ReferenceError(code, message)


# --------------------------------------------------------------------------------------------- canonical values

canonical_json_bytes = bm.canonical_json_bytes
canonical_line = bm.canonical_line
sha256_bytes = bm.sha256_bytes
sha256_file = bm.sha256_file
rational = bm.rational
decimal_text = bm.decimal_text
is_int = bm.is_int


def model_sha256(model_id: str) -> str:
    return sha256_bytes(canonical_json_bytes(MODELS[model_id]))


def numeric_contract_sha256() -> str:
    return sha256_bytes(canonical_json_bytes(NUMERIC_CONTRACT))


_QUANTUM = Decimal("0.000000000001")


def dec12(value: float) -> str:
    """A binary64 value's exact decimal expansion rounded half-even to 12 places (negative zero normalized)."""
    if not isinstance(value, float) or not math.isfinite(value):
        _refuse("REFERENCE_NONFINITE_VALUE", f"{value!r} is not a finite binary64 value")
    with localcontext() as ctx:
        ctx.prec = 80
        quantized = Decimal(value).quantize(_QUANTUM, rounding=ROUND_HALF_EVEN)
    if quantized == 0:
        quantized = abs(quantized)
    return format(quantized, "f")


def dec_complement(text: str) -> str:
    """``1 - p`` exactly for a 12-place decimal string."""
    with localcontext() as ctx:
        ctx.prec = 80
        value = (Decimal(1) - Decimal(text)).quantize(_QUANTUM)
    return format(abs(value) if value == 0 else value, "f")


def dec_negation(text: str) -> str:
    """``-x`` exactly for a 12-place decimal string (no negative zero)."""
    with localcontext() as ctx:
        ctx.prec = 80
        value = (-Decimal(text)).quantize(_QUANTUM)
    return format(abs(value) if value == 0 else value, "f")


def dec_fraction(text: str) -> Fraction:
    return Fraction(Decimal(text))


def frac(value: dict[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def rational_or_none(value: Fraction | None) -> dict[str, int] | None:
    return None if value is None else rational(value)


# --------------------------------------------------------------------------------------------- inputs

def _ordered(items: list[Any], order: str) -> list[Any]:
    if order == "natural":
        return list(items)
    if order == "reverse":
        return list(reversed(items))
    if order.startswith("shuffle:") and order[8:].isdigit():
        out = list(items)
        random.Random(int(order[8:])).shuffle(out)
        return out
    _refuse("INPUT_ORDER_INVALID", f"input order {order!r}")
    return []


def history_anchors(anchors: dict[str, Any]) -> dict[str, Any]:
    return {"contract_id": anchors["benchmark"]["contract_id"], "contract_sha256": anchors["benchmark"]["contract_sha256"],
            "history": anchors["history"]}


def _benchmark_error(exc: bm.BenchmarkError) -> ReferenceError:
    code = exc.code
    if code.startswith("BENCHMARK_HISTORY_") or code == "BENCHMARK_HISTORY_MISMATCH":
        code = "REFERENCE_" + code[len("BENCHMARK_"):]
    elif code.startswith("BENCHMARK_"):
        code = "REFERENCE_C47_" + code[len("BENCHMARK_"):]
    return ReferenceError(code, str(exc))


def _population_error(exc: population_query.NationalQueryError) -> ReferenceError:
    code = exc.code if exc.code.startswith("DATABASE_LOCATION_") else f"POPULATION_{exc.code}"
    return ReferenceError(code, str(exc))


def _valid_date(text: Any) -> bool:
    import datetime as _dt  # noqa: PLC0415
    try:
        return isinstance(text, str) and _dt.date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


def predicate_failures(row: dict[str, Any]) -> list[str]:
    """The seven frozen BAT-711 history-pool predicates of one parent contest row (an empty list passes)."""
    fail = []
    if row["disposition"] != "VERIFIED_PRESENT":
        fail.append("DISPOSITION")
    if row["reconciliation_state"] != "RECONCILED_2016_2023":
        fail.append("RECONCILIATION")
    if row["contest_status"] != "COMPLETED":
        fail.append("STATUS")
    if not (is_int(row["competitive"]) and row["competitive"] == 1):
        fail.append("COMPETITIVE")
    observed = None
    if row["contest_dates_observed"] is not None:
        try:
            observed = json.loads(row["contest_dates_observed"])
        except ValueError:
            observed = ["<invalid>"]
    if not _valid_date(row["contest_date"]) or (observed is not None and
                                                (not isinstance(observed, list) or
                                                 sorted(set(map(str, observed))) != [row["contest_date"]])):
        fail.append("DATE")
    a_key, b_key = row["a_key"], row["b_key"]
    if not (isinstance(a_key, str) and isinstance(b_key, str) and re.fullmatch(r"org:[0-9]+", a_key) and
            re.fullmatch(r"org:[0-9]+", b_key) and a_key == f"org:{row['a_org_id']}" and
            b_key == f"org:{row['b_org_id']}" and a_key != b_key):
        fail.append("ORG_KEYS")
    if not (is_int(row["a_points"]) and is_int(row["b_points"]) and row["a_points"] >= 0 and row["b_points"] >= 0):
        fail.append("SCORES")
    return fail


PARENT_COLUMNS = ("contest_key", "season", "term", "contest_date", "contest_status", "competitive", "disposition",
                  "reconciliation_state", "a_org_id", "b_org_id", "a_key", "b_key", "a_team_name", "b_team_name",
                  "a_division_label", "b_division_label", "a_points", "b_points", "contest_dates_observed",
                  "classification_pair")


def load_pool(population_database: Path, anchors: dict[str, Any], history: dict[str, Any],
              *, input_order: str = "natural") -> dict[str, Any]:
    """Verify the accepted parent population database (location, manifest identity, bytes, meta) through the accepted
    population reader, pin it to the anchored identities, read only its 2016-2023 contest rows, apply the seven frozen
    pool predicates and require the passing set to equal the history's pool key for key."""
    p = anchors["population"]
    try:
        handle = population_query.NationalPopulationDatabase(Path(population_database))
    except population_query.NationalQueryError as exc:
        raise _population_error(exc) from exc
    try:
        binding = handle.binding
        pinned = {"database_identity": binding["database_identity"], "sqlite_sha256": binding["database_sha256"],
                  "contract_sha256": binding["contract_sha256"],
                  "contest_identity": handle.meta.get("contest_identity"),
                  "program_season_identity": handle.meta.get("program_season_identity")}
        differing = sorted(k for k, v in pinned.items() if v != p.get(k))
        if differing:
            _refuse("REFERENCE_POPULATION_MISMATCH",
                    f"the population database differs from the bound accepted parent on {differing}")
        rows = [dict(zip(PARENT_COLUMNS, tuple(r))) for r in handle.conn.execute(
            f"SELECT {', '.join(PARENT_COLUMNS)} FROM contest WHERE season BETWEEN 2016 AND 2023 ORDER BY contest_key")]
    finally:
        handle.close()
    pool_keys = {t[1] for t in history["targets"]}
    for key, _season, text in history["exclusions"]:
        if json.loads(text).get("history_pool_member") is True:
            pool_keys.add(key)
    protected = history["protected"]
    passing: dict[str, dict[str, Any]] = {}
    for row in _ordered(rows, input_order):
        if row["contest_key"] in passing:
            _refuse("REFERENCE_POOL_MISMATCH", f"parent contest {row['contest_key']} repeats")
        if not predicate_failures(row):
            passing[row["contest_key"]] = row
    if set(passing) != pool_keys:
        missing = sorted(pool_keys - set(passing))
        extra = sorted(set(passing) - pool_keys)
        _refuse("REFERENCE_POOL_MISMATCH", f"parent predicates and history pool differ: {len(missing)} history pool "
                                           f"keys fail or are absent (e.g. {missing[:3]}), {len(extra)} passing parent "
                                           f"keys are outside the history pool (e.g. {extra[:3]})")
    if set(passing) & set(protected):
        _refuse("REFERENCE_PROTECTED_KEY", "a pool contest is a protected canonical contest")
    return {"binding": pinned, "rows": passing, "parent_rows_read": len(rows)}


def load_inputs(history_database: Path, population_database: Path, anchors: dict[str, Any], *,
                input_order: str = "natural") -> dict[str, Any]:
    try:
        history = bm.load_history(Path(history_database), history_anchors(anchors), input_order=input_order)
    except bm.BenchmarkError as exc:
        raise _benchmark_error(exc) from exc
    pool = load_pool(Path(population_database), anchors, history, input_order=input_order)
    return {"history": history, "pool": pool}


# --------------------------------------------------------------------------------------------- features

def _side_block(team_key: str, games: list[dict[str, Any]]) -> dict[str, Any]:
    """The side's prior aggregate and lineage from its parent pool rows (``games`` in (date, key) order)."""
    contributing, names = [], set()
    wins = losses = ties = pf = pa = 0
    for row in games:
        role = "A" if row["a_key"] == team_key else "B"
        mine, theirs = (row["a_points"], row["b_points"]) if role == "A" else (row["b_points"], row["a_points"])
        result = "W" if mine > theirs else "L" if mine < theirs else "T"
        wins += result == "W"
        losses += result == "L"
        ties += result == "T"
        pf += mine
        pa += theirs
        names.add(row["a_team_name"] if role == "A" else row["b_team_name"])
        contributing.append({"contest_key": row["contest_key"], "contest_date": row["contest_date"], "side": role,
                             "opponent_key": row["b_key"] if role == "A" else row["a_key"],
                             "opponent_division_label": row["b_division_label"] if role == "A"
                             else row["a_division_label"], "points_for": mine, "points_against": theirs,
                             "result": result})
    g = len(games)
    missing = 0 if g else 1
    return {"games": g, "wins": wins, "losses": losses, "ties": ties, "points_for_total": pf,
            "points_against_total": pa, "margin_total": pf - pa,
            "win_rate": rational(Fraction(2 * wins + ties, 2 * g)) if g else None,
            "points_for_mean": rational(Fraction(pf, g)) if g else None,
            "points_against_mean": rational(Fraction(pa, g)) if g else None,
            "margin_mean": rational(Fraction(pf - pa, g)) if g else None,
            "missing": {"games": 0, "win_rate": missing, "points_for_mean": missing,
                        "points_against_mean": missing, "margin_mean": missing},
            "cold_start": g == 0, "contributing": contributing,
            "source_names": sorted(n for n in names if isinstance(n, str))}


def side_value(block: dict[str, Any], name: str) -> Fraction:
    """A side's frozen feature value: games, or a rate (zero when missing)."""
    if name == "games":
        return Fraction(block["games"])
    value = block[name]
    return Fraction(0) if value is None else frac(value)


def _history_side_matches(history: Any, block: dict[str, Any], team_key: str, season: int) -> bool:
    """Whether an accepted history view block states exactly this rederived prior record."""
    if not isinstance(history, dict) or history.get("team_key") != team_key or history.get("season") != season:
        return False
    for name in ("games", "wins", "losses", "ties", "points_for_total", "points_against_total", "margin_total"):
        if not is_int(history.get(name)) or history.get(name) != block[name]:
            return False
    contributing = history.get("contributing")
    if not isinstance(contributing, list) or len(contributing) != len(block["contributing"]):
        return False
    for got, want in zip(contributing, block["contributing"]):
        if not isinstance(got, dict) or any(got.get(k) != want[k] for k in want):
            return False
    return history.get("contributing_contest_keys") == [c["contest_key"] for c in block["contributing"]]


def team_pool_index(pool: dict[str, dict[str, Any]]) -> dict[tuple[str, int], list[tuple[str, str]]]:
    index: dict[tuple[str, int], list[tuple[str, str]]] = {}
    for key, row in pool.items():
        for side in (row["a_key"], row["b_key"]):
            index.setdefault((side, row["season"]), []).append((row["contest_date"], key))
    for value in index.values():
        value.sort()
    return index


def derive_features(c47: dict[str, Any], inputs: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Both oriented feature records of every target, rederived from the parent pool rows and required to equal the
    accepted history views; plus the per-target side blocks for the models."""
    pool = inputs["pool"]["rows"]
    index = team_pool_index(pool)
    views = {(r[1], r[2]): (r[0], r[7]) for r in inputs["history"]["views"]}
    c47_features = {(f["contest_key"], f["view"]): line for f, line in zip(c47["features"], c47["lines"]["features"])}
    features, sides = [], {}
    for target in c47["targets"]:
        key, season, date = target["contest_key"], target["season"], target["contest_date"]
        blocks = {}
        for side_key in (target["a_key"], target["b_key"]):
            games = [pool[k] for d, k in index.get((side_key, season), []) if d < date]
            if any(g["contest_key"] == key for g in games):
                _refuse("REFERENCE_FEATURE_LEAKAGE", f"{key}: the target contributes to its own prior record")
            blocks[side_key] = _side_block(side_key, games)
        sides[key] = blocks
        for view in VIEWS:
            team_key, opponent_key = (target["a_key"], target["b_key"]) if view == "A" else \
                (target["b_key"], target["a_key"])
            ord_, text = views[(key, view)]
            record = json.loads(text)
            if not (_history_side_matches(record.get("team_history"), blocks[team_key], team_key, season) and
                    _history_side_matches(record.get("opponent_history"), blocks[opponent_key], opponent_key,
                                          season)):
                _refuse("REFERENCE_FEATURE_LINEAGE_MISMATCH",
                        f"{key}/{view}: the parent-rederived prior record differs from the accepted history view")
            team, opponent = blocks[team_key], blocks[opponent_key]
            names = (target["a_team_name"], target["b_team_name"]) if view == "A" else \
                (target["b_team_name"], target["a_team_name"])
            orgs = (target["a_org_id"], target["b_org_id"]) if view == "A" else (target["b_org_id"], target["a_org_id"])
            differences = [side_value(team, n) - side_value(opponent, n) for n in SIDE_FIELDS]
            missing = [team["missing"][n] - opponent["missing"][n] for n in SIDE_FIELDS]
            features.append({
                "record_type": "reference_feature", "contest_key": key, "season": season, "contest_date": date,
                "partition": PARTITION_OF[season], "fit_role": fit_role(season), "view": view,
                "team_key": team_key, "team_name": names[0], "team_org_id": orgs[0], "opponent_key": opponent_key,
                "opponent_name": names[1], "opponent_org_id": orgs[1], "target_site": target["site"],
                "team": team, "opponent": opponent,
                "differences": {"columns": [f"{n}_difference" for n in SIDE_FIELDS],
                                "values": [rational(v) for v in differences],
                                "missing_columns": [f"{n}_missing_difference" for n in SIDE_FIELDS],
                                "missing_values": missing},
                "first_four_team_games": min(team["games"], opponent["games"]) < 4,
                "cold_start": min(team["games"], opponent["games"]) == 0,
                "texas_am_target": TAMU_KEY in (target["a_key"], target["b_key"]),
                "prior_rule": "SAME_SEASON_DATE_STRICTLY_BEFORE_TARGET_DATE",
                "source_history": {"database_identity": inputs["history"]["binding"]["database_identity"],
                                   "history_ord": ord_, "record_sha256": sha256_bytes(str(text).encode("utf-8")),
                                   "target_record_sha256": target["record_sha256"]},
                "source_population": {"database_identity": inputs["pool"]["binding"]["database_identity"],
                                      "rule": "parent contest rows of the contributing keys"},
                "c47_feature_record_sha256": sha256_bytes(c47_features[(key, view)].encode("utf-8")),
                **RECORD_LABELS})
    return features, sides


def fit_role(season: int) -> str:
    return "TRAINING_2016_2022" if season in TRAINING_SEASONS else "OUT_OF_FIT_EXPOSED_2023_COMPARISON"


def design_row(feature: dict[str, Any]) -> list[float]:
    """The unscaled binary64 design of one oriented feature record (exact difference, rounded once)."""
    return [float(frac(v)) for v in feature["differences"]["values"]] + \
        [float(m) for m in feature["differences"]["missing_values"]]


# --------------------------------------------------------------------------------------------- Elo

def elo_expected(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + float(ELO["logistic_base"]) ** ((rating_b - rating_a) / float(ELO["scale"])))


def derive_elo(pool: dict[str, dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, Any]:
    """The site-blind season Elo: each pool game exactly once, same-date batching, the target state before its date."""
    by_season: dict[int, dict[str, list[dict[str, Any]]]] = {}
    for row in pool.values():
        by_season.setdefault(row["season"], {}).setdefault(row["contest_date"], []).append(row)
    wanted: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for target in targets:
        wanted.setdefault((target["season"], target["contest_date"]), []).append(target)
    state: dict[str, dict[str, Any]] = {}
    processed: dict[str, int] = {}
    dates_processed = 0
    initial, k_factor = float(ELO["initial_rating"]), float(ELO["k_factor"])
    for season in sorted(by_season):
        ratings: dict[str, float] = {}
        played: dict[str, int] = {}
        target_dates = sorted(d for s, d in wanted if s == season)
        game_dates = sorted(by_season[season])
        for date in sorted(set(game_dates) | set(target_dates)):
            for target in wanted.get((season, date), []):
                a, b = target["a_key"], target["b_key"]
                state[target["contest_key"]] = {"a_rating": ratings.get(a, initial), "b_rating": ratings.get(b, initial),
                                                "a_games": played.get(a, 0), "b_games": played.get(b, 0)}
            games = sorted(by_season[season].get(date, []), key=lambda r: r["contest_key"])
            if not games:
                continue
            deltas: dict[str, list[float]] = {}
            for row in games:
                ra, rb = ratings.get(row["a_key"], initial), ratings.get(row["b_key"], initial)
                score = 1.0 if row["a_points"] > row["b_points"] else 0.0 if row["a_points"] < row["b_points"] else 0.5
                delta = k_factor * (score - elo_expected(ra, rb))
                deltas.setdefault(row["a_key"], []).append(delta)
                deltas.setdefault(row["b_key"], []).append(-delta)
            for team in sorted(deltas):
                ratings[team] = ratings.get(team, initial) + math.fsum(deltas[team])
                played[team] = played.get(team, 0) + len(deltas[team])
            processed[str(season)] = processed.get(str(season), 0) + len(games)
            dates_processed += 1
    return {"targets": state, "games_by_season": dict(sorted(processed.items())),
            "games": sum(processed.values()), "dates": dates_processed}


# --------------------------------------------------------------------------------------------- fits

def column_scales(rows: list[list[float]]) -> list[float]:
    """Training-only root-mean-square of each column (no centering); a zero scale uses 1."""
    n = float(len(rows))
    scales = []
    for j in range(len(COLUMNS)):
        rms = math.sqrt(math.fsum(r[j] * r[j] for r in rows) / n)
        scales.append(rms if rms != 0.0 else 1.0)
    return scales


def scaled(row: list[float], scales: list[float]) -> tuple[float, ...]:
    return tuple(v / s for v, s in zip(row, scales))


def derive_fits(features: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Scales from the 2016-2022 training oriented rows only, then the paired logistic and ridge fits on those rows."""
    a_rows = {f["contest_key"]: f for f in features if f["view"] == "A"}
    training_raw: list[list[float]] = []
    logistic_rows, ridge_rows, used = [], [], {"logistic": 0, "ridge": 0}
    excluded: dict[str, int] = {}
    keys = [k for k, f in a_rows.items() if f["season"] in TRAINING_SEASONS]
    for key in keys:
        x = design_row(a_rows[key])
        training_raw.append(x)
        training_raw.append([-v for v in x])
    scales = column_scales(training_raw)
    for key in keys:
        z = scaled(design_row(a_rows[key]), scales)
        neg = tuple(-v for v in z)
        label = labels[key]
        if label["label_state"] == "DECISIVE":
            y = float(label["y_a"])
            logistic_rows += [rf.Row(z, y, 0.5), rf.Row(neg, 1.0 - y, 0.5)]
            used["logistic"] += 1
        else:
            excluded[f"logistic:{label['label_state']}"] = excluded.get(f"logistic:{label['label_state']}", 0) + 1
        if label["label_state"] in ("DECISIVE", "TIE"):
            m = float(label["a_points"] - label["b_points"])
            ridge_rows += [rf.Row(z, m, 0.5), rf.Row(neg, -m, 0.5)]
            used["ridge"] += 1
        else:
            excluded[f"ridge:{label['label_state']}"] = excluded.get(f"ridge:{label['label_state']}", 0) + 1
    try:
        logistic = rf.fit_logistic(logistic_rows, len(COLUMNS))
        ridge = rf.fit_ridge(ridge_rows, len(COLUMNS))
    except rf.ReferenceFitError as exc:
        _refuse(f"REFERENCE_{exc.code}", f"{exc} (recorded failure, never accepted)")
    return {"scales": scales, "logistic": logistic, "ridge": ridge, "training_targets": len(keys), "used": used,
            "excluded": dict(sorted(excluded.items())), "logistic_rows": len(logistic_rows),
            "ridge_rows": len(ridge_rows)}


# --------------------------------------------------------------------------------------------- estimates

def sample_state(model_id: str, season: int) -> str:
    if model_id not in LEARNED_MODELS:
        return "NOT_FITTED"
    return "IN_SAMPLE_TRAINING_NOT_A_LABEL_ANCHOR" if season in TRAINING_SEASONS else "OUT_OF_FIT_EXPOSED_2023"


def derive_estimates(c47: dict[str, Any], features: list[dict[str, Any]], elo: dict[str, Any],
                     fits: dict[str, Any], feature_lines: list[str]) -> list[tuple[dict[str, Any], str | None]]:
    """Every target's estimates in model order, A then B: the C47 records with their C47 lines, then the new ones.
    No label is in scope here."""
    by_view = {(f["contest_key"], f["view"]): (f, line) for f, line in zip(features, feature_lines)}
    c47_by_key: dict[str, list[tuple[dict[str, Any], str]]] = {}
    for record, line in zip(c47["estimates"], c47["lines"]["estimates"]):
        c47_by_key.setdefault(record["contest_key"], []).append((record, line))
    shas = {m: model_sha256(m) for m in MODEL_IDS}
    beta_l, beta_r, scales = fits["logistic"].coefficients, fits["ridge"].coefficients, fits["scales"]
    out: list[tuple[dict[str, Any], str | None]] = []
    for target in c47["targets"]:
        key = target["contest_key"]
        out += [(record, line) for record, line in c47_by_key[key]]
        (a, a_line), (b, b_line) = by_view[(key, "A")], by_view[(key, "B")]
        z = scaled(design_row(a), scales)
        state = elo["targets"][key]
        p_elo = dec12(elo_expected(state["a_rating"], state["b_rating"]))
        eta = rf.linear(z, beta_l)
        p_log = dec12(rf.sigmoid(eta))
        margin = dec12(rf.linear(z, beta_r))
        game_sha = sha256_bytes(a_line.encode("utf-8"))
        for model_id in (MODEL_ELO, MODEL_LOGISTIC, MODEL_RIDGE):
            for orientation, mine, line in (("A", a, a_line), ("B", b, b_line)):
                record: dict[str, Any] = {
                    "record_type": "reference_estimate", "contest_key": key, "season": a["season"],
                    "contest_date": a["contest_date"], "partition": a["partition"], "model_id": model_id,
                    "model_sha256": shas[model_id], "orientation": orientation, "team_key": mine["team_key"],
                    "team_name": mine["team_name"], "opponent_key": mine["opponent_key"],
                    "opponent_name": mine["opponent_name"], "sample_state": sample_state(model_id, a["season"]),
                    "feature_record_sha256": sha256_bytes(line.encode("utf-8")),
                    "game_feature_record_sha256": game_sha, **RECORD_LABELS}
                if model_id in PROBABILITY_MODELS:
                    p_a = p_elo if model_id == MODEL_ELO else p_log
                    mine_p = p_a if orientation == "A" else dec_complement(p_a)
                    record.update(output_kind="WIN_PROBABILITY", probability=mine_p,
                                  opponent_probability=dec_complement(mine_p), game_grain_probability_a=p_a)
                    if model_id == MODEL_ELO:
                        ratings = (state["a_rating"], state["b_rating"]) if orientation == "A" else \
                            (state["b_rating"], state["a_rating"])
                        games = (state["a_games"], state["b_games"]) if orientation == "A" else \
                            (state["b_games"], state["a_games"])
                        record.update(team_rating=dec12(ratings[0]), opponent_rating=dec12(ratings[1]),
                                      team_rating_games=games[0], opponent_rating_games=games[1],
                                      rating_state="START_OF_TARGET_DATE_BEFORE_ITS_UPDATES")
                    else:
                        lin = dec12(eta)
                        record.update(linear_predictor=lin if orientation == "A" else dec_negation(lin),
                                      parameter_model_id=MODEL_LOGISTIC)
                else:
                    mine_m = margin if orientation == "A" else dec_negation(margin)
                    record.update(output_kind="EXPECTED_MARGIN_ONLY_NO_PROBABILITY", margin=mine_m,
                                  opponent_margin=dec_negation(mine_m), game_grain_margin_a=margin,
                                  parameter_model_id=MODEL_RIDGE)
                out.append((record, None))
    return out


# --------------------------------------------------------------------------------------------- scores

def served_probability_a(record: dict[str, Any]) -> Fraction:
    """The served A-orientation probability of an A estimate record (exact)."""
    if record["model_id"] in C47_MODELS:
        return frac(record["probability"])
    return dec_fraction(record["probability"])


def log_loss_value(p_a: Fraction, y: int) -> float:
    q = p_a if y == 1 else 1 - p_a
    clipped = min(max(float(q), LOG_CLIP), 1.0 - LOG_CLIP)
    return -math.log(clipped)


def derive_scores(estimates: list[tuple[dict[str, Any], str]], labels: dict[str, tuple[dict[str, Any], str]],
                  features: dict[str, dict[str, Any]], c47_scores: dict[tuple[str, str], tuple[dict[str, Any], str]]
                  ) -> list[dict[str, Any]]:
    """One A-oriented score per target and model; the label joins by exact contest key."""
    out = []
    for record, line in estimates:
        if record["orientation"] != "A":
            continue
        key, model_id = record["contest_key"], record["model_id"]
        label, label_line = labels[key]
        feature = features[key]
        base = {"record_type": "reference_score", "contest_key": key, "season": record["season"],
                "contest_date": record["contest_date"], "partition": record["partition"], "model_id": model_id,
                "model_sha256": model_sha256(model_id), "orientation": "A", "a_key": label["a_key"],
                "b_key": label["b_key"], "a_team_name": record["team_name"], "b_team_name": record["opponent_name"],
                "sample_state": sample_state(model_id, record["season"]), "label_state": label["label_state"],
                "first_four_team_games": feature["first_four_team_games"], "cold_start": feature["cold_start"],
                "texas_am_target": feature["texas_am_target"],
                "estimate_record_sha256": sha256_bytes(line.encode("utf-8")),
                "label_record_sha256": sha256_bytes(label_line.encode("utf-8")), **RECORD_LABELS}
        if model_id in PROBABILITY_MODELS:
            p_a = served_probability_a(record)
            base.update(metric_kind="PROBABILITY", y_a=label["y_a"], probability_a=decimal_text(p_a),
                        probability_a_exact=rational(p_a))
            if label["y_a"] is None:
                base.update(score_state="UNSCORED", unscored_reason=label["unscored_reason"], brier=None,
                            brier_decimal=None, log_loss=None, log_loss_convention=CLIP_CONVENTION)
            else:
                brier = (p_a - label["y_a"]) ** 2
                base.update(score_state="SCORED", unscored_reason=None, brier=rational(brier),
                            brier_decimal=decimal_text(brier), log_loss=repr(log_loss_value(p_a, label["y_a"])),
                            log_loss_convention=CLIP_CONVENTION)
            if model_id in C47_MODELS:
                c47_record, c47_line = c47_scores[(key, model_id)]
                if (base["brier"], base["log_loss"]) != (c47_record["brier"], c47_record["log_loss"]):
                    _refuse("REFERENCE_C47_SCORE_MISMATCH", f"{key}/{model_id}: the common scorecard differs from C47")
                base["c47_score_record_sha256"] = sha256_bytes(c47_line.encode("utf-8"))
        else:
            margin = dec_fraction(record["margin"])
            base.update(metric_kind="MARGIN", margin_a=record["margin"])
            if label["label_state"] in ("DECISIVE", "TIE"):
                m = label["a_points"] - label["b_points"]
                error = Fraction(m) - margin
                base.update(score_state="SCORED", unscored_reason=None, margin_label_a=m,
                            absolute_error=rational(abs(error)), absolute_error_decimal=decimal_text(abs(error)),
                            squared_error=rational(error * error), squared_error_decimal=decimal_text(error * error))
            else:
                base.update(score_state="UNSCORED", unscored_reason=label["unscored_reason"], margin_label_a=None,
                            absolute_error=None, absolute_error_decimal=None, squared_error=None,
                            squared_error_decimal=None)
        out.append(base)
    return out


# --------------------------------------------------------------------------------------------- summary

def _scopes() -> list[tuple[str, str, tuple[int, ...]]]:
    scopes = [("SEASON", str(s), (s,)) for s in TARGET_SEASONS]
    scopes += [("PARTITION", p["split_id"], tuple(p["seasons"])) for p in SPLIT["partitions"]]
    scopes.append(("POOLED", "2016-2023", TARGET_SEASONS))
    return scopes


def in_slice(slice_id: str, score: dict[str, Any]) -> bool:
    if slice_id == "NATIONAL":
        return True
    if slice_id == "TEXAS_AM":
        return bool(score["texas_am_target"])
    if slice_id == "FIRST_FOUR_TEAM_GAMES":
        return bool(score["first_four_team_games"])
    return bool(score["cold_start"])


def _mean(total: Fraction, count: int) -> tuple[dict[str, int] | None, str | None]:
    if not count:
        return None, None
    value = total / count
    return rational(value), decimal_text(value)


def calibration_table(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bins: list[list[dict[str, Any]]] = [[] for _ in range(DECILE_BINS)]
    for s in scored:
        p = frac(s["probability_a_exact"])
        bins[min(int(p * DECILE_BINS), DECILE_BINS - 1)].append(s)
    table = []
    for index, members in enumerate(bins):
        p_total = sum((frac(s["probability_a_exact"]) for s in members), Fraction(0))
        wins = sum(1 for s in members if s["y_a"] == 1)
        mean_p, mean_p_text = _mean(p_total, len(members))
        rate, rate_text = _mean(Fraction(wins), len(members))
        table.append({"bin": index, "lower": rational(Fraction(index, DECILE_BINS)),
                      "upper": rational(Fraction(index + 1, DECILE_BINS)),
                      "upper_closed": index == DECILE_BINS - 1, "count": len(members), "a_wins": wins,
                      "mean_probability_a": mean_p, "mean_probability_a_decimal": mean_p_text,
                      "observed_a_win_rate": rate, "observed_a_win_rate_decimal": rate_text})
    return table


def derive_summary(scores: list[dict[str, Any]], features: list[dict[str, Any]], fits: dict[str, Any],
                   elo: dict[str, Any], c47: dict[str, Any]) -> dict[str, Any]:
    rows, comparisons = [], []
    for slice_id in SLICE_IDS:
        for kind, scope_id, seasons in _scopes():
            chosen = [s for s in scores if s["season"] in seasons and in_slice(slice_id, s)]
            by_model: dict[str, dict[str, Any]] = {}
            keysets: dict[str, list[str]] = {}
            for model_id in MODEL_IDS:
                mine = [s for s in chosen if s["model_id"] == model_id]
                scored = [s for s in mine if s["score_state"] == "SCORED"]
                unscored: dict[str, int] = {}
                for s in mine:
                    if s["score_state"] != "SCORED":
                        unscored[s["unscored_reason"]] = unscored.get(s["unscored_reason"], 0) + 1
                samples: dict[str, int] = {}
                for s in scored:
                    samples[s["sample_state"]] = samples.get(s["sample_state"], 0) + 1
                row: dict[str, Any] = {
                    "record_type": "reference_summary_row", "slice": slice_id, "scope_kind": kind,
                    "scope_id": scope_id, "seasons": list(seasons), "model_id": model_id,
                    "model_sha256": model_sha256(model_id), "score_records": len(mine), "scored_games": len(scored),
                    "unscored_games": len(mine) - len(scored), "unscored_by_reason": unscored,
                    "scored_by_sample_state": dict(sorted(samples.items()))}
                if model_id in PROBABILITY_MODELS:
                    brier_total = sum((frac(s["brier"]) for s in scored), Fraction(0))
                    log_total = math.fsum(float(s["log_loss"]) for s in scored)
                    brier_mean, brier_mean_text = _mean(brier_total, len(scored))
                    row.update(metric_kind="PROBABILITY", metric_scope="IDENTICAL_KEYS_ALL_FOUR_PROBABILITY_FAMILIES",
                               brier_total=rational(brier_total), brier_total_decimal=decimal_text(brier_total),
                               brier_mean=brier_mean, brier_mean_decimal=brier_mean_text,
                               log_loss_total=repr(log_total),
                               log_loss_mean=repr(log_total / len(scored)) if scored else None,
                               log_loss_convention=CLIP_CONVENTION, calibration=calibration_table(scored))
                    keysets[model_id] = [s["contest_key"] for s in scored]
                else:
                    abs_total = sum((frac(s["absolute_error"]) for s in scored), Fraction(0))
                    sq_total = sum((frac(s["squared_error"]) for s in scored), Fraction(0))
                    mae, mae_text = _mean(abs_total, len(scored))
                    mse, mse_text = _mean(sq_total, len(scored))
                    rmse = math.sqrt(float(sq_total / len(scored))) if scored else None
                    row.update(metric_kind="MARGIN", metric_scope="RIDGE_EXPECTED_MARGIN_DECISIVE_AND_TIE_LABELS",
                               mae=mae, mae_decimal=mae_text, mse=mse, mse_decimal=mse_text,
                               rmse=None if rmse is None else repr(rmse),
                               rmse_decimal=None if rmse is None else dec12(rmse))
                rows.append(row)
                by_model[model_id] = row
            first = keysets[MODEL_NULL]
            if any(keysets[m] != first for m in PROBABILITY_MODELS):
                _refuse("REFERENCE_COMMON_SUPPORT_INVALID", f"{slice_id}/{scope_id}: probability families differ "
                                                            "in scored game keys")
            null = by_model[MODEL_NULL]
            for model_id in (MODEL_SMOOTHED, MODEL_ELO, MODEL_LOGISTIC):
                other = by_model[model_id]
                entry = {"record_type": "reference_comparison_row", "slice": slice_id, "scope_kind": kind,
                         "scope_id": scope_id, "model_id": model_id, "baseline_model_id": MODEL_NULL,
                         "scored_games": other["scored_games"]}
                if other["brier_mean"] is not None and null["brier_mean"] is not None:
                    diff = frac(other["brier_mean"]) - frac(null["brier_mean"])
                    entry.update(brier_mean_difference=rational(diff), brier_mean_difference_decimal=decimal_text(diff),
                                 log_loss_mean_difference=repr(float(other["log_loss_mean"]) -
                                                               float(null["log_loss_mean"])),
                                 reading="descriptive retrospective difference (model minus NULL_HALF_V1) on identical "
                                         "game keys; negative favours the model, positive the null; no significance, "
                                         "skill, calibration or champion claim; adverse and null results retained")
                else:
                    entry.update(brier_mean_difference=None, brier_mean_difference_decimal=None,
                                 log_loss_mean_difference=None, reading="no scored game in this scope")
                comparisons.append(entry)
    label_states: dict[str, int] = {}
    for label in c47["labels"]:
        label_states[label["label_state"]] = label_states.get(label["label_state"], 0) + 1
    a_features = [f for f in features if f["view"] == "A"]
    return {"record_type": "reference_summary", "contract_id": CONTRACT_ID, "models": list(MODEL_IDS),
            "population": {"targets": len(a_features), "feature_views": len(features),
                           "estimates": len(c47["targets"]) * 2 * len(MODEL_IDS), "labels": len(c47["labels"]),
                           "scores": len(scores), "training_targets": fits["training_targets"],
                           "comparison_targets": len(a_features) - fits["training_targets"],
                           "pool_games": elo["games"], "pool_games_by_season": elo["games_by_season"],
                           "label_states": label_states,
                           "first_four_team_games_targets": sum(1 for f in a_features if f["first_four_team_games"]),
                           "cold_start_targets": sum(1 for f in a_features if f["cold_start"]),
                           "texas_am_targets": sum(1 for f in a_features if f["texas_am_target"])},
            "slices": SLICES, "calibration": CALIBRATION, "rows": rows, "comparisons": comparisons, **RECORD_LABELS}


# --------------------------------------------------------------------------------------------- parameters

def parameter_records(fits: dict[str, Any], elo: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for model_id in MODEL_IDS:
        base = {"record_type": "reference_parameter", "model_id": model_id, "model_sha256": model_sha256(model_id),
                "definition": MODELS[model_id], **RECORD_LABELS}
        if model_id in C47_MODELS:
            base.update(fitted=False, parameter_state="FIXED_C47_DEFINITION_UNCHANGED")
        elif model_id == MODEL_ELO:
            base.update(fitted=False, parameter_state="FIXED_DECLARED_PARAMETERS", parameters=ELO,
                        pool_games_processed=elo["games"], pool_games_by_season=elo["games_by_season"],
                        dates_processed=elo["dates"])
        else:
            fit = fits["logistic"] if model_id == MODEL_LOGISTIC else fits["ridge"]
            base.update(fitted=True, parameter_state=fit.state, columns=list(COLUMNS),
                        coefficients=[dec12(b) for b in fit.coefficients],
                        scales=[dec12(s) for s in fits["scales"]],
                        training={"seasons": list(TRAINING_SEASONS), "targets": fits["training_targets"],
                                  "games_used": fits["used"]["logistic" if model_id == MODEL_LOGISTIC else "ridge"],
                                  "oriented_rows": fits["logistic_rows" if model_id == MODEL_LOGISTIC else "ridge_rows"],
                                  "row_weight": {"numerator": 1, "denominator": 2},
                                  "excluded_by_label_state": {k.split(":", 1)[1]: v for k, v in fits["excluded"].items()
                                                              if k.startswith("logistic:" if model_id == MODEL_LOGISTIC
                                                                              else "ridge:")},
                                  "comparison_2023": "never in the fit, the scales or any tuning"},
                        penalty={"lambda": 1, "applies_to": "every column", "intercept": "NONE"},
                        convergence={"state": fit.state, "newton_steps": fit.iterations,
                                     "objective_decimal": dec12(fit.objective),
                                     "gradient_or_residual_inf_norm_decimal": dec12(fit.gradient_inf_norm)},
                        diagnostics={"coefficients_repr": [repr(b) for b in fit.coefficients],
                                     "scales_repr": [repr(s) for s in fits["scales"]],
                                     "objective_repr": repr(fit.objective),
                                     "gradient_or_residual_inf_norm_repr": repr(fit.gradient_inf_norm),
                                     "trajectory": fit.trajectory, "fit_interface": rf.VERSION,
                                     "rule": "unrounded diagnostics kept separately; served results are decimal12"})
        out.append(base)
    return out


# --------------------------------------------------------------------------------------------- the whole derivation

def derive(inputs: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    try:
        c47 = bm.derive(inputs["history"], history_anchors(anchors))
    except bm.BenchmarkError as exc:
        raise _benchmark_error(exc) from exc
    features, _sides = derive_features(c47, inputs)
    feature_lines = [canonical_line(r) for r in features]
    elo = derive_elo(inputs["pool"]["rows"], c47["targets"])
    if elo["games"] != len(inputs["pool"]["rows"]):
        _refuse("REFERENCE_POOL_MISMATCH", "Elo did not process every pool game exactly once")
    label_pairs = {lab["contest_key"]: (lab, line) for lab, line in zip(c47["labels"], c47["lines"]["labels"])}
    for key, (label, _line) in label_pairs.items():
        row = inputs["pool"]["rows"].get(key)
        if label["label_state"] in ("DECISIVE", "TIE") and (row is None or
                                                            (row["a_points"], row["b_points"]) !=
                                                            (label["a_points"], label["b_points"])):
            _refuse("REFERENCE_LABEL_INPUT_INVALID", f"label {key} contradicts the parent row")
    fits = derive_fits(features, {k: v[0] for k, v in label_pairs.items()})       # 2016-2022 labels only
    estimate_pairs = derive_estimates(c47, features, elo, fits, feature_lines)
    estimates = [record for record, _line in estimate_pairs]
    estimate_lines = [line if line is not None else canonical_line(record) for record, line in estimate_pairs]
    c47_scores = {(s["contest_key"], s["model_id"]): (s, line) for s, line in zip(c47["scores"], c47["lines"]["scores"])}
    a_features = {f["contest_key"]: f for f in features if f["view"] == "A"}
    scores = derive_scores(list(zip(estimates, estimate_lines)), label_pairs, a_features, c47_scores)
    parameters = parameter_records(fits, elo)
    summary = derive_summary(scores, features, fits, elo, c47)
    if bm.contains_float(summary) or any(bm.contains_float(p) for p in parameters):
        _refuse("REFERENCE_FLOAT_VALUE", "a derived summary or parameter carries a binary float")
    return {"targets": c47["targets"], "features": features, "estimates": estimates, "labels": c47["labels"],
            "parameters": parameters, "scores": scores, "summary": summary, "fits": fits, "elo": elo,
            "lines": {"features": feature_lines, "estimates": estimate_lines, "labels": c47["lines"]["labels"],
                      "parameters": [canonical_line(r) for r in parameters],
                      "scores": [canonical_line(r) for r in scores]}}


RECORD_TABLES = ("features", "estimates", "labels", "parameters", "scores")
SEASONAL_TABLES = ("features", "estimates", "labels", "scores")


def record_lines(derived: dict[str, Any]) -> dict[str, list[str]]:
    if "lines" in derived:
        return derived["lines"]
    return {table: [canonical_line(r) for r in derived[table]] for table in RECORD_TABLES}


def target_chunk(derived: dict[str, Any], keys: Iterable[str]) -> bytes:
    """The checkpoint unit: every seasonal record line of the given targets, table by table (deterministic)."""
    wanted = set(keys)
    lines = []
    for table in SEASONAL_TABLES:
        lines += [f"{table}\t{line}" for record, line in zip(derived[table], record_lines(derived)[table])
                  if record["contest_key"] in wanted]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _gzip(data: bytes) -> bytes:
    return gzip.compress(data, compresslevel=6, mtime=0)


def payloads(derived: dict[str, Any]) -> dict[str, bytes]:
    lines = record_lines(derived)
    out = {f"{table}.jsonl.gz": _gzip("".join(line + "\n" for line in lines[table]).encode("utf-8"))
           for table in RECORD_TABLES}
    out["summary.json"] = (canonical_line(derived["summary"]) + "\n").encode("utf-8")
    return out


def uncompressed_sha256(derived: dict[str, Any]) -> dict[str, str]:
    lines = record_lines(derived)
    return {f"{table}.jsonl": sha256_bytes("".join(line + "\n" for line in lines[table]).encode("utf-8"))
            for table in RECORD_TABLES}


def row_counts(derived: dict[str, Any]) -> dict[str, int]:
    return {**{f"{table}.jsonl.gz": len(derived[table]) for table in RECORD_TABLES}, "summary.json": 1}


def models_claim() -> dict[str, Any]:
    return {model_id: {"definition": MODELS[model_id], "sha256": model_sha256(model_id)} for model_id in MODEL_IDS}


def parent_binding(anchors: dict[str, Any]) -> dict[str, Any]:
    return {"history": dict(anchors["history"]), "population": dict(anchors["population"]),
            "benchmark": dict(anchors["benchmark"])}


def content_document(contract_id: str, contract_sha256: str, anchors: dict[str, Any],
                     payload_bytes: dict[str, bytes], counts: dict[str, int],
                     lines_sha256: dict[str, str]) -> dict[str, Any]:
    return {"schema": CONTENT_SCHEMA, "stage": "reference-content", "population": POPULATION,
            "contract_id": contract_id, "contract_sha256": contract_sha256, "parent": parent_binding(anchors),
            "models": {model_id: model_sha256(model_id) for model_id in MODEL_IDS},
            "numeric_contract_sha256": numeric_contract_sha256(), "payload_schema": PAYLOAD_SCHEMA,
            "outputs": {name: sha256_bytes(data) for name, data in sorted(payload_bytes.items())},
            "uncompressed_sha256": dict(sorted(lines_sha256.items())), "row_counts": dict(sorted(counts.items()))}


def database_document(contract_sha256: str, content_identity: str, database_sha256: str,
                      table_counts: dict[str, int]) -> dict[str, Any]:
    return {"schema": DATABASE_SCHEMA, "stage": "reference-database", "population": POPULATION,
            "contract_sha256": contract_sha256, "content_identity": content_identity, "db_schema_version": DB_SCHEMA,
            "outputs": {DB_FILE: database_sha256}, "table_counts": dict(table_counts)}


def meta_values(document: dict[str, Any], content_identity: str, summary: dict[str, Any],
                anchors: dict[str, Any]) -> dict[str, str]:
    return {"schema_version": DB_SCHEMA, "contract_id": document["contract_id"],
            "contract_sha256": document["contract_sha256"], "content_identity": content_identity,
            "payload_sha256": canonical_line(document["outputs"]),
            "uncompressed_sha256": canonical_line(document["uncompressed_sha256"]),
            "row_counts": canonical_line(document["row_counts"]), "parent": canonical_line(parent_binding(anchors)),
            "labels": canonical_line(LABELS), "split": canonical_line(SPLIT), "models": canonical_line(models_claim()),
            "numeric_contract": canonical_line(NUMERIC_CONTRACT), "scope": canonical_line(SCOPE),
            "slices": canonical_line(SLICES), "summary_sha256": sha256_bytes(canonical_json_bytes(summary))}


#: The exact database schema: one zlib block (level 9) per (record table, segment) -- a season for the seasonal
#: tables, GLOBAL for the parameters and the summary -- with its record count, first/last record key and the SHA-256 of
#: its uncompressed JSONL lines.
DDL = (
    ("table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"),
    ("table", "blocks", "CREATE TABLE blocks (ord INTEGER PRIMARY KEY, record_table TEXT NOT NULL, "
                        "segment TEXT NOT NULL, records INTEGER NOT NULL, first_key TEXT, last_key TEXT, "
                        "lines_sha256 TEXT NOT NULL, block BLOB NOT NULL)"),
)
TABLES = ("meta", "blocks")
BLOCK_LAYOUT = tuple([(table, str(season)) for table in SEASONAL_TABLES for season in TARGET_SEASONS] +
                     [("parameters", "GLOBAL"), ("summary", "GLOBAL")])


def record_key(table: str, record: dict[str, Any]) -> str:
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


def block_rows(derived: dict[str, Any]) -> list[tuple[Any, ...]]:
    lines = record_lines(derived)
    rows = []
    for ord_, (table, segment) in enumerate(BLOCK_LAYOUT):
        if table == "summary":
            records, chosen = [derived["summary"]], [canonical_line(derived["summary"])]
        elif table == "parameters":
            records, chosen = list(derived["parameters"]), list(lines["parameters"])
        else:
            pairs = [(r, l) for r, l in zip(derived[table], lines[table]) if str(r["season"]) == segment]
            records, chosen = [r for r, _l in pairs], [l for _r, l in pairs]
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

#: Which refusal a differing top-level record field gets (first match in this order).
RECORD_FIELD_CODES = (
    ("pit_eligibility", "REFERENCE_PIT_CLAIM_INVALID"), ("prior_rule", "REFERENCE_PIT_CLAIM_INVALID"),
    ("evidence_label", "REFERENCE_LABEL_CLAIM_INVALID"), ("trust_state", "REFERENCE_LABEL_CLAIM_INVALID"),
    ("partition", "REFERENCE_PARTITION_MISMATCH"), ("fit_role", "REFERENCE_PARTITION_MISMATCH"),
    ("sample_state", "REFERENCE_SAMPLE_STATE_MISMATCH"),
    ("model_id", "REFERENCE_MODEL_MISMATCH"), ("model_sha256", "REFERENCE_MODEL_MISMATCH"),
    ("definition", "REFERENCE_MODEL_MISMATCH"), ("output_kind", "REFERENCE_MODEL_MISMATCH"),
    ("metric_kind", "REFERENCE_MODEL_MISMATCH"), ("parameter_model_id", "REFERENCE_MODEL_MISMATCH"),
    ("orientation", "REFERENCE_ORIENTATION_MISMATCH"), ("view", "REFERENCE_ORIENTATION_MISMATCH"),
    ("team_key", "REFERENCE_TEAM_MAPPING_MISMATCH"), ("opponent_key", "REFERENCE_TEAM_MAPPING_MISMATCH"),
    ("team_name", "REFERENCE_TEAM_MAPPING_MISMATCH"), ("opponent_name", "REFERENCE_TEAM_MAPPING_MISMATCH"),
    ("team_org_id", "REFERENCE_TEAM_MAPPING_MISMATCH"), ("opponent_org_id", "REFERENCE_TEAM_MAPPING_MISMATCH"),
    ("a_key", "REFERENCE_TEAM_MAPPING_MISMATCH"), ("b_key", "REFERENCE_TEAM_MAPPING_MISMATCH"),
    ("a_team_name", "REFERENCE_TEAM_MAPPING_MISMATCH"), ("b_team_name", "REFERENCE_TEAM_MAPPING_MISMATCH"),
    ("label_state", "REFERENCE_LABEL_MISMATCH"), ("y_a", "REFERENCE_LABEL_MISMATCH"),
    ("a_result", "REFERENCE_LABEL_MISMATCH"), ("a_points", "REFERENCE_LABEL_MISMATCH"),
    ("b_points", "REFERENCE_LABEL_MISMATCH"), ("margin_label_a", "REFERENCE_LABEL_MISMATCH"),
    ("unscored_reason", "REFERENCE_LABEL_MISMATCH"), ("score_state", "REFERENCE_LABEL_MISMATCH"),
    ("label_record_sha256", "REFERENCE_LABEL_MISMATCH"),
    ("brier", "REFERENCE_METRIC_MISMATCH"), ("brier_decimal", "REFERENCE_METRIC_MISMATCH"),
    ("log_loss", "REFERENCE_METRIC_MISMATCH"), ("log_loss_convention", "REFERENCE_METRIC_MISMATCH"),
    ("absolute_error", "REFERENCE_METRIC_MISMATCH"), ("absolute_error_decimal", "REFERENCE_METRIC_MISMATCH"),
    ("squared_error", "REFERENCE_METRIC_MISMATCH"), ("squared_error_decimal", "REFERENCE_METRIC_MISMATCH"),
    ("probability", "REFERENCE_PROBABILITY_MISMATCH"), ("opponent_probability", "REFERENCE_PROBABILITY_MISMATCH"),
    ("probability_decimal", "REFERENCE_PROBABILITY_MISMATCH"),
    ("opponent_probability_decimal", "REFERENCE_PROBABILITY_MISMATCH"),
    ("game_grain_probability_a", "REFERENCE_PROBABILITY_MISMATCH"),
    ("probability_a", "REFERENCE_PROBABILITY_MISMATCH"), ("probability_a_exact", "REFERENCE_PROBABILITY_MISMATCH"),
    ("linear_predictor", "REFERENCE_PROBABILITY_MISMATCH"), ("team_rating", "REFERENCE_PROBABILITY_MISMATCH"),
    ("opponent_rating", "REFERENCE_PROBABILITY_MISMATCH"), ("team_strength_q", "REFERENCE_PROBABILITY_MISMATCH"),
    ("opponent_strength_q", "REFERENCE_PROBABILITY_MISMATCH"),
    ("margin", "REFERENCE_MARGIN_MISMATCH"), ("opponent_margin", "REFERENCE_MARGIN_MISMATCH"),
    ("game_grain_margin_a", "REFERENCE_MARGIN_MISMATCH"), ("margin_a", "REFERENCE_MARGIN_MISMATCH"),
    ("coefficients", "REFERENCE_PARAMETER_MISMATCH"), ("scales", "REFERENCE_PARAMETER_MISMATCH"),
    ("convergence", "REFERENCE_PARAMETER_MISMATCH"), ("diagnostics", "REFERENCE_PARAMETER_MISMATCH"),
    ("parameters", "REFERENCE_PARAMETER_MISMATCH"), ("training", "REFERENCE_PARAMETER_MISMATCH"),
    ("parameter_state", "REFERENCE_PARAMETER_MISMATCH"), ("penalty", "REFERENCE_PARAMETER_MISMATCH"),
    ("team", "REFERENCE_LINEAGE_MISMATCH"), ("opponent", "REFERENCE_LINEAGE_MISMATCH"),
    ("source_history", "REFERENCE_LINEAGE_MISMATCH"), ("source_population", "REFERENCE_LINEAGE_MISMATCH"),
    ("source_label", "REFERENCE_LINEAGE_MISMATCH"), ("c47_feature_record_sha256", "REFERENCE_LINEAGE_MISMATCH"),
    ("c47_score_record_sha256", "REFERENCE_LINEAGE_MISMATCH"),
    ("feature_record_sha256", "REFERENCE_LINEAGE_MISMATCH"), ("game_feature_record_sha256", "REFERENCE_LINEAGE_MISMATCH"),
    ("estimate_record_sha256", "REFERENCE_LINEAGE_MISMATCH"),
    ("differences", "REFERENCE_FEATURE_MISMATCH"), ("first_four_team_games", "REFERENCE_SLICE_MISMATCH"),
    ("cold_start", "REFERENCE_SLICE_MISMATCH"), ("texas_am_target", "REFERENCE_SLICE_MISMATCH"),
)
COUNT_FIELDS = ("games", "wins", "losses", "ties", "points_for_total", "points_against_total", "margin_total")
TABLE_LABELS = {"features": "FEATURE", "estimates": "ESTIMATE", "labels": "LABEL", "parameters": "PARAMETER",
                "scores": "SCORE"}


def _json_or_none(text: Any) -> Any:
    try:
        return json.loads(text) if isinstance(text, (str, bytes)) else None
    except ValueError:
        return None


_parse_marking_floats = bm._parse_marking_floats
_io_path = bm._io_path


def manifest_path_for(database: Path) -> Path:
    return bm.manifest_path_for(database)


#: Count members that must be JSON integers (``None`` allowed only where the rule says so), per record kind.
COUNT_PATHS: dict[str, tuple[tuple[str, bool], ...]] = {
    "estimates": (("team_rating_games", False), ("opponent_rating_games", False)),
    "scores": (("y_a", True), ("margin_label_a", True)),
    "parameters": (("pool_games_processed", False), ("dates_processed", False), ("training.targets", False),
                   ("training.games_used", False), ("training.oriented_rows", False),
                   ("convergence.newton_steps", False)),
}
SUMMARY_ROW_COUNTS = ("score_records", "scored_games", "unscored_games")
SUMMARY_POPULATION_COUNTS = ("targets", "feature_views", "estimates", "labels", "scores", "training_targets",
                             "comparison_targets", "pool_games", "first_four_team_games_targets", "cold_start_targets",
                             "texas_am_targets")


def _count_type_problems(table: str, record: dict[str, Any]) -> list[str]:
    """Count members of ``record`` that are not JSON integers (a boolean or an integral float is not a count)."""
    bad: list[str] = []

    def check(path: str, value: Any, nullable: bool = False) -> None:
        if value is None and nullable:
            return
        if not is_int(value):
            bad.append(path)

    if table == "features":
        for side in ("team", "opponent"):
            member = record.get(side) if isinstance(record.get(side), dict) else {}
            for i, item in enumerate(member.get("contributing") or []):
                if isinstance(item, dict):
                    check(f"{side}.contributing[{i}].points_for", item.get("points_for"))
                    check(f"{side}.contributing[{i}].points_against", item.get("points_against"))
            for name, value in (member.get("missing") or {}).items():
                check(f"{side}.missing.{name}", value)
        for i, value in enumerate((record.get("differences") or {}).get("missing_values") or []):
            check(f"differences.missing_values[{i}]", value)
    elif table in COUNT_PATHS:
        for path, nullable in COUNT_PATHS[table]:
            node: Any = record
            present = True
            for part in path.split("."):
                if isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    present = False
                    break
            if present:
                check(path, node, nullable)
    elif table == "summary":
        for name in SUMMARY_POPULATION_COUNTS:
            check(f"population.{name}", (record.get("population") or {}).get(name))
        for i, row in enumerate(record.get("rows") or []):
            for name in SUMMARY_ROW_COUNTS:
                check(f"rows[{i}].{name}", row.get(name))
            for b, entry in enumerate(row.get("calibration") or []):
                for name in ("bin", "count", "a_wins"):
                    check(f"rows[{i}].calibration[{b}].{name}", entry.get(name))
        for i, row in enumerate(record.get("comparisons") or []):
            check(f"comparisons[{i}].scored_games", row.get("scored_games"))
    return bad


def _coherent_pair(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Both oriented records of one game state one canonical value and its exact complement or negation."""
    if a.get("output_kind") == "WIN_PROBABILITY":
        values = (a.get("probability"), a.get("opponent_probability"), b.get("probability"),
                  b.get("opponent_probability"), a.get("game_grain_probability_a"), b.get("game_grain_probability_a"))
        if not all(isinstance(v, str) and DEC12_RE.match(v) for v in values):
            return False
        p = Decimal(a["probability"])
        return (Decimal(0) <= p <= Decimal(1) and dec_complement(a["probability"]) == a["opponent_probability"] ==
                b["probability"] and dec_complement(b["probability"]) == b["opponent_probability"] and
                a["game_grain_probability_a"] == b["game_grain_probability_a"] == a["probability"] and
                "margin" not in a and "margin" not in b)
    if a.get("output_kind") == "EXPECTED_MARGIN_ONLY_NO_PROBABILITY":
        values = (a.get("margin"), a.get("opponent_margin"), b.get("margin"), b.get("opponent_margin"))
        if not all(isinstance(v, str) and DEC12_RE.match(v) for v in values):
            return False
        return (dec_negation(a["margin"]) == a["opponent_margin"] == b["margin"] and
                dec_negation(b["margin"]) == b["opponent_margin"] and
                a.get("game_grain_margin_a") == b.get("game_grain_margin_a") == a["margin"] and
                not any(k in r for r in (a, b) for k in ("probability", "opponent_probability",
                                                          "game_grain_probability_a")))
    return False


class ReferenceComparison:
    """A verified, read-only handle on one content-addressed national retrospective reference comparison.

    Construction refuses (ReferenceError with a stable code) unless the accepted history and parent population verify
    and pin, the reference location, manifest identity, database bytes, schema and meta claims verify, and every record
    of every table, the summary, the content identity and the contract-defined database identity document equal what is
    re-derived from the accepted inputs, the frozen model rules and a fresh deterministic refit. Identity documents are
    compared as canonical bytes and the served identity is the digest of the rebuilt document. Each refusal is checked in
    a fixed order so that every forgery is refused for its own cause."""

    def __init__(self, database: Path, *, history_database: Path, population_database: Path,
                 manifest: Path | None = None, expect_identity: str | None = None,
                 anchors: dict[str, Any] | None = None) -> None:
        self.anchors = anchors if anchors is not None else ANCHORS
        inputs = load_inputs(Path(history_database), Path(population_database), self.anchors)
        self.binding = self._verify_location_and_manifest(database, manifest, expect_identity)
        document = self.binding["identity_document"]
        if document.get("contract_sha256") != self.anchors["contract_sha256"]:
            _refuse("REFERENCE_CONTRACT_MISMATCH", f"the reference names contract {document.get('contract_sha256')}, "
                                                   f"the reader binds {self.anchors['contract_sha256']}")
        try:
            self.conn = readonly_sqlite.connect_readonly(database)
        except readonly_sqlite.DatabaseLocationError as exc:
            raise ReferenceError(exc.code, exc.detail) from exc
        try:
            self._verify_database(inputs)
        except sqlite3.DatabaseError as exc:
            self.conn.close()
            raise ReferenceError("REFERENCE_SCHEMA_UNSUPPORTED", str(exc)) from exc
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
            raise ReferenceError(exc.code, exc.detail) from exc
        db = Path(database)
        if not _io_path(db).is_file():
            _refuse("REFERENCE_DATABASE_MISSING", f"no reference database file at {db}")
        absolute = Path(os.path.abspath(db))
        if absolute.name != DB_FILE or absolute.parent.parent.name != "sha256" or \
                absolute.parent.parent.parent.name != POPULATION:
            _refuse("REFERENCE_LOCATION_INVALID", f"the reference must sit at <root>/{POPULATION}/sha256/<id>/{DB_FILE}")
        identity = absolute.parent.name
        if not IDENTITY_RE.match(identity):
            _refuse("REFERENCE_LOCATION_INVALID", f"directory name {identity!r} is not an identity")
        manifest_path = Path(manifest) if manifest is not None else manifest_path_for(db)
        if not _io_path(manifest_path).is_file():
            _refuse("REFERENCE_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
        try:
            doc = json.loads(_io_path(manifest_path).read_text(encoding="utf-8"))
            identity_document = doc["identity_document"]
            computed = sha256_bytes(canonical_json_bytes(identity_document))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ReferenceError("REFERENCE_MANIFEST_MALFORMED", str(exc)) from exc
        if computed != identity or doc.get("identity") != identity:
            _refuse("REFERENCE_IDENTITY_MISMATCH", f"manifest identity document hashes to {computed}, directory is "
                                                   f"{identity}")
        if not isinstance(identity_document, dict) or \
                (identity_document.get("stage"), identity_document.get("schema"),
                 identity_document.get("db_schema_version"), identity_document.get("population")) != \
                ("reference-database", DATABASE_SCHEMA, DB_SCHEMA, POPULATION):
            _refuse("REFERENCE_SCHEMA_UNSUPPORTED", "not a national retrospective reference database manifest")
        outputs = identity_document.get("outputs")
        if outputs is not None and not isinstance(outputs, dict):
            _refuse("REFERENCE_IDENTITY_DOCUMENT_MISMATCH", "the manifest identity document's outputs is not an object")
        expected_sha = (outputs or {}).get(DB_FILE)
        actual_sha = sha256_file(_io_path(db))
        if expected_sha != actual_sha:
            _refuse("REFERENCE_DATABASE_TAMPERED", f"reference bytes hash to {actual_sha}, manifest names {expected_sha}")
        if expect_identity is not None and expect_identity != identity:
            _refuse("STALE_REFERENCE_IDENTITY", f"expected {expect_identity}, found {identity}")
        return {"identity": identity, "sha256": actual_sha, "manifest": str(manifest_path),
                "identity_document": identity_document}

    # ---- schema, meta claims and the complete re-derivation
    def _verify_database(self, inputs: dict[str, Any]) -> None:
        a = self.anchors
        master = sorted((str(r[0]), str(r[1]), r[2]) for r in self.conn.execute(
            "SELECT type, name, sql FROM sqlite_master"))
        if master != sorted(DDL):
            _refuse("REFERENCE_SCHEMA_UNSUPPORTED", "the reference schema differs from the contract")
        meta_rows = [(str(r[0]), r[1]) for r in self.conn.execute("SELECT key, value FROM meta ORDER BY rowid")]
        meta = dict(meta_rows)
        if len(meta) != len(meta_rows):
            _refuse("REFERENCE_META_MISMATCH", "duplicate meta keys")
        if meta.get("schema_version") != DB_SCHEMA:
            _refuse("REFERENCE_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}")
        if meta.get("contract_sha256") != a["contract_sha256"] or meta.get("contract_id") != a["contract_id"]:
            _refuse("REFERENCE_CONTRACT_MISMATCH", "the reference meta names another contract")
        claims = {name: _json_or_none(meta.get(name)) for name in
                  ("parent", "labels", "split", "models", "numeric_contract", "scope", "slices")}
        if canonical_json_bytes(claims["parent"]) != canonical_json_bytes(parent_binding(a)):
            _refuse("REFERENCE_PARENT_MISMATCH", "the reference was built for other parents")
        if claims["labels"] != LABELS:
            labels = claims["labels"] if isinstance(claims["labels"], dict) else {}
            code = ("REFERENCE_PIT_CLAIM_INVALID" if labels.get("pit_eligibility") != PIT_STATE or
                    labels.get("temporal_basis") != LABELS["temporal_basis"] else
                    "REFERENCE_PROTECTED_CLAIM_INVALID" if labels.get("protected_lane") != LABELS["protected_lane"]
                    else "REFERENCE_LABEL_CLAIM_INVALID")
            _refuse(code, "the reference declares labels other than the contract's")
        if canonical_json_bytes(claims["split"]) != canonical_json_bytes(SPLIT):
            _refuse("REFERENCE_SPLIT_CLAIM_INVALID", "the reference declares another split")
        if canonical_json_bytes(claims["models"]) != canonical_json_bytes(models_claim()):
            _refuse("REFERENCE_MODEL_MISMATCH", "the reference declares other model definitions")
        if canonical_json_bytes(claims["numeric_contract"]) != canonical_json_bytes(NUMERIC_CONTRACT):
            _refuse("REFERENCE_NUMERIC_CONTRACT_MISMATCH", "the reference declares another numeric contract")
        if canonical_json_bytes(claims["scope"]) != canonical_json_bytes(SCOPE):
            _refuse("REFERENCE_SCOPE_CLAIM_INVALID", "the reference declares another scope")
        if canonical_json_bytes(claims["slices"]) != canonical_json_bytes(SLICES):
            _refuse("REFERENCE_SLICE_CLAIM_INVALID", "the reference declares other slices")
        counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        # value equality keeps a fractional, string or boolean count here; an integral float count is equal by value
        # and is refused last by the canonical-bytes identity-document rule
        if counts != self.binding["identity_document"].get("table_counts"):
            _refuse("REFERENCE_COUNT_MISMATCH",
                    f"table counts {counts} != {self.binding['identity_document'].get('table_counts')}")
        present = self._read_blocks(inputs["history"]["protected"])
        derived = derive(inputs, a)
        lines = record_lines(derived)
        for table in RECORD_TABLES:
            self._compare(table, present[table], lines[table], derived[table])
        if len(present["summary"]) != 1:
            _refuse("REFERENCE_SUMMARY_MISMATCH", f"the summary block holds {len(present['summary'])} records")
        stored_summary = present["summary"][0][1]
        if present["summary"][0][0] != canonical_line(derived["summary"]):
            differing = sorted(k for k in set(derived["summary"]) | set(stored_summary or {})
                               if canonical_json_bytes((stored_summary or {}).get(k)) !=
                               canonical_json_bytes(derived["summary"].get(k)))
            code = ("REFERENCE_METRIC_MISMATCH" if set(differing) & {"rows", "comparisons"} else
                    "REFERENCE_SUMMARY_MISMATCH")
            _refuse(code, f"the stored summary differs from its records on {differing[:6]}")
        content_payloads = payloads(derived)
        document = content_document(a["contract_id"], a["contract_sha256"], a, content_payloads, row_counts(derived),
                                     uncompressed_sha256(derived))
        content_identity = sha256_bytes(canonical_json_bytes(document))
        if meta.get("content_identity") != content_identity or \
                self.binding["identity_document"].get("content_identity") != content_identity:
            _refuse("REFERENCE_CONTENT_IDENTITY_MISMATCH", f"the re-derived content identity is {content_identity}")
        expected_meta = meta_values(document, content_identity, derived["summary"], a)
        if meta != expected_meta:
            _refuse("REFERENCE_META_MISMATCH", "meta differs on " + str(sorted(
                k for k in set(meta) | set(expected_meta) if meta.get(k) != expected_meta.get(k))))
        identity_document = self.binding["identity_document"]
        expected_document = database_document(a["contract_sha256"], content_identity, self.binding["sha256"], counts)
        expected_bytes = canonical_json_bytes(expected_document)
        if canonical_json_bytes(identity_document) != expected_bytes:
            differing = sorted(k for k in set(identity_document) | set(expected_document)
                               if k not in identity_document or k not in expected_document
                               or canonical_json_bytes(identity_document[k]) !=
                               canonical_json_bytes(expected_document[k]))
            _refuse("REFERENCE_IDENTITY_DOCUMENT_MISMATCH",
                    f"the manifest identity document is not the contract-defined database document (differs on "
                    f"{differing})")
        database_identity = sha256_bytes(expected_bytes)
        if database_identity != self.binding["identity"]:
            _refuse("REFERENCE_IDENTITY_DOCUMENT_MISMATCH", f"the location names {self.binding['identity']}, the "
                                                            f"contract-defined document is {database_identity}")
        self.database_identity = database_identity
        self.content_identity = content_identity
        self.meta = meta
        self.derived = derived
        self.history_identity = inputs["history"]["binding"]["database_identity"]
        self.population_identity = inputs["pool"]["binding"]["database_identity"]
        self.names = bm.team_name_index(derived["targets"])

    def _read_blocks(self, protected: dict[str, int]) -> dict[str, list[tuple[str, dict[str, Any], bool]]]:
        """Every block's index columns against its own content, then each record's segment and protected membership,
        label leakage, count types, binary floats, mirrored score rows and game-grain pair coherence -- before any
        comparison with the re-derived records."""
        rows = [tuple(r) for r in self.conn.execute(
            "SELECT ord, record_table, segment, records, first_key, last_key, lines_sha256, block FROM blocks "
            "ORDER BY ord")]
        present: dict[str, list[tuple[str, dict[str, Any], bool]]] = {t: [] for t in (*RECORD_TABLES, "summary")}
        layout = []
        for ord_, table, segment, records, first_key, last_key, lines_sha, blob in rows:
            if table not in present:
                _refuse("REFERENCE_SCHEMA_UNSUPPORTED", f"block {ord_} names table {table!r}")
            seasonal = table in SEASONAL_TABLES
            if seasonal and (not isinstance(segment, str) or not segment.isdigit() or
                             int(segment) not in TARGET_SEASONS):
                _refuse("REFERENCE_PROTECTED_KEY", f"block {ord_} holds segment {segment!r} outside 2016-2023")
            try:
                data = zlib.decompress(blob)
                lines = data.decode("utf-8").split("\n")
            except (zlib.error, TypeError, UnicodeDecodeError) as exc:
                raise ReferenceError("REFERENCE_INDEX_MISMATCH", f"block {ord_} does not decompress: {exc}") from exc
            if lines[-1] != "":
                _refuse("REFERENCE_INDEX_MISMATCH", f"block {ord_} does not end with a newline")
            parsed = []
            for line in lines[:-1]:
                record, has_float = _parse_marking_floats(line)
                if not isinstance(record, dict):
                    _refuse("REFERENCE_RECORD_MISMATCH", f"block {ord_} holds a non-object line")
                parsed.append((line, record, has_float))
            keys = [record_key(table, r) for _l, r, _f in parsed]
            if sha256_bytes(data) != lines_sha or records != len(parsed) or \
                    first_key != (keys[0] if keys else None) or last_key != (keys[-1] if keys else None):
                _refuse("REFERENCE_INDEX_MISMATCH", f"block {ord_} index columns differ from its content")
            for _line, record, _f in parsed:
                if record.get("contest_key") in protected:
                    _refuse("REFERENCE_PROTECTED_KEY", f"{table} names protected contest {record.get('contest_key')}")
                if seasonal and str(record.get("season")) != segment:
                    code = "REFERENCE_PROTECTED_KEY" if record.get("season") not in TARGET_SEASONS else \
                        "REFERENCE_INDEX_MISMATCH"
                    _refuse(code, f"{table} record {record_key(table, record)} season {record.get('season')!r} in the "
                                  f"{segment} block")
            layout.append((table, segment))
            present[table] += parsed
        if layout != list(BLOCK_LAYOUT):
            _refuse("REFERENCE_INDEX_MISMATCH", "the blocks do not follow the contract layout")
        for table in ("features", "estimates"):
            for _line, record, _f in present[table]:
                leaked = sorted(f for f in LABEL_FIELDS if f in record)
                if leaked:
                    _refuse("REFERENCE_LABEL_LEAKAGE", f"{table} record {record_key(table, record)} carries label "
                                                       f"fields {leaked}")
        for _line, record, _f in present["features"]:
            for side in ("team", "opponent"):
                member = record.get(side)
                values = [member.get(k) for k in COUNT_FIELDS] if isinstance(member, dict) else [None]
                if not all(is_int(v) for v in values) or not all(v >= 0 for v in values[:6]) or \
                        values[1] + values[2] + values[3] != values[0]:
                    _refuse("REFERENCE_COUNT_TYPE_INVALID", f"feature {record_key('features', record)} {side} counts "
                                                            "are not integers with W + L + T = G")
        for table in (*RECORD_TABLES, "summary"):
            for _line, record, _f in present[table]:
                bad = _count_type_problems(table, record)
                if bad:
                    _refuse("REFERENCE_COUNT_TYPE_INVALID", f"{table} record {record_key(table, record)} carries "
                                                            f"non-integer counts {bad[:4]}")
        for table in ("estimates", "scores"):
            for _line, record, _f in present[table]:
                if record.get("model_id") in MARGIN_MODELS and any(
                        k in record for k in ("probability", "opponent_probability", "game_grain_probability_a",
                                              "probability_a", "probability_a_exact", "brier", "log_loss")):
                    _refuse("REFERENCE_RIDGE_PROBABILITY_INVENTED",
                            f"{table} {record_key(table, record)}: the ridge reference serves no probability")
        for table in (*RECORD_TABLES, "summary"):
            for _line, record, has_float in present[table]:
                if has_float:
                    _refuse("REFERENCE_FLOAT_VALUE", f"{table} record {record_key(table, record)} carries a binary "
                                                     "float")
        for _line, record, _f in present["scores"]:
            if record.get("orientation") != "A":
                _refuse("REFERENCE_MIRROR_DOUBLE_COUNT", f"score {record_key('scores', record)} is not the single "
                                                         "A-oriented record")
        pairs: dict[tuple[Any, Any], dict[str, dict[str, Any]]] = {}
        for _line, record, _f in present["estimates"]:
            if record.get("model_id") not in C47_MODELS:
                pairs.setdefault((record.get("contest_key"), record.get("model_id")), {})[
                    str(record.get("orientation"))] = record
        for (key, model_id), pair in pairs.items():
            if set(pair) == {"A", "B"} and not _coherent_pair(pair["A"], pair["B"]):
                _refuse("REFERENCE_PAIR_INCOHERENT", f"{key}/{model_id}: the oriented records are not one canonical "
                                                     "value and its exact complement or negation")
        return present

    @staticmethod
    def _compare(table: str, present: list[tuple[str, dict[str, Any], bool]], expected: list[str],
                 wanted_records: list[dict[str, Any]]) -> None:
        label = TABLE_LABELS[table]
        keys = [record_key(table, r) for _l, r, _f in present]
        if len(keys) != len(set(keys)):
            _refuse("REFERENCE_DUPLICATE_ROW", f"{table} repeats a record key")
        wanted = [record_key(table, r) for r in wanted_records]
        missing = sorted(set(wanted) - set(keys))
        if missing:
            _refuse(f"REFERENCE_{label}_ROW_MISSING", f"{len(missing)} expected {table} records absent, e.g. "
                                                      f"{missing[:3]}")
        extra = sorted(set(keys) - set(wanted))
        if extra:
            _refuse(f"REFERENCE_{label}_ROW_EXTRA", f"{len(extra)} {table} records outside the accepted population, "
                                                    f"e.g. {extra[:3]}")
        if keys != wanted:
            _refuse("REFERENCE_ORDER_MISMATCH", f"{table} is not in the contract order")
        for (line, got, _f), want_line, want in zip(present, expected, wanted_records):
            if line == want_line:
                continue
            differing = {f for f in set(want) | set(got)
                         if f not in want or f not in got or canonical_json_bytes(got[f]) != canonical_json_bytes(want[f])}
            code = next((c for f, c in RECORD_FIELD_CODES if f in differing), "REFERENCE_RECORD_MISMATCH")
            _refuse(code, f"{table} {record_key(table, want)} differs on {sorted(differing)[:6]}")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "ReferenceComparison":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- serving
    @staticmethod
    def filters(grain: str, *, season: int | None = None, team: str | None = None, contest: str | None = None,
                model: str | None = None, partition: str | None = None, slice_id: str | None = None
                ) -> dict[str, Any]:
        """Validate a selection before any file is read: unknown grains, malformed or inapplicable filters refuse."""
        if grain not in GRAINS:
            _refuse("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}")
        filters: dict[str, Any] = {}
        if season is not None:
            if not is_int(season):
                _refuse("SEASON_INVALID", f"season must be an integer, got {season!r}")
            if grain == "reference-parameter":
                _refuse("FILTER_NOT_APPLICABLE", "season does not apply to the parameter grain")
            filters["season"] = season
        if team is not None:
            if grain in ("reference-parameter", "reference-summary"):
                _refuse("FILTER_NOT_APPLICABLE", f"team does not apply to the {grain} grain")
            text = str(team).strip()
            if not text:
                _refuse("TEAM_INVALID", "team must be org:<digits>, digits or a team name")
            filters["team"] = text
        if contest is not None:
            if grain in ("reference-parameter", "reference-summary"):
                _refuse("FILTER_NOT_APPLICABLE", f"contest does not apply to the {grain} grain")
            text = str(contest).strip()
            filters["contest"] = f"ncaa:{text}" if text.isdigit() and len(text) <= 12 else text
            if not bm.CONTEST_KEY_RE.match(filters["contest"]):
                _refuse("CONTEST_KEY_INVALID", f"contest must be a parent contest key, got {contest!r}")
        if model is not None:
            if grain == "reference-feature":
                _refuse("FILTER_NOT_APPLICABLE", "model does not apply to the feature grain")
            if model not in MODEL_IDS:
                _refuse("MODEL_UNKNOWN", f"model must be one of {list(MODEL_IDS)}")
            filters["model"] = model
        if partition is not None:
            if grain == "reference-parameter":
                _refuse("FILTER_NOT_APPLICABLE", "partition does not apply to the parameter grain")
            if partition not in PARTITION_IDS:
                _refuse("PARTITION_UNKNOWN", f"partition must be one of {list(PARTITION_IDS)}")
            filters["partition"] = partition
        if slice_id is not None:
            if grain != "reference-summary":
                _refuse("FILTER_NOT_APPLICABLE", "slice applies only to the summary grain")
            if slice_id not in SLICE_IDS:
                _refuse("SLICE_UNKNOWN", f"slice must be one of {list(SLICE_IDS)}")
            filters["slice"] = slice_id
        return filters

    def query(self, grain: str, *, season: int | None = None, team: str | None = None, contest: str | None = None,
              model: str | None = None, partition: str | None = None, slice_id: str | None = None,
              limit: int | None = 50, offset: int = 0, all_rows: bool = False) -> dict[str, Any]:
        filters = self.filters(grain, season=season, team=team, contest=contest, model=model, partition=partition,
                               slice_id=slice_id)
        if offset < 0:
            _refuse("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            _refuse("NEGATIVE_LIMIT", "limit must be zero or positive")
        result: dict[str, Any] = {
            "reference_identity": self.database_identity, "content_identity": self.content_identity,
            "contract_sha256": self.anchors["contract_sha256"], "contract_id": self.anchors["contract_id"],
            "history_database_identity": self.history_identity,
            "population_database_identity": self.population_identity,
            "benchmark_identity": self.anchors["benchmark"]["database_identity"], "grain": grain, "filters": filters,
            "offset": offset, "limit": None if all_rows else limit, **LABELS,
            "denominators": self.derived["summary"]["population"],
            "verification": {"targets_verified": len(self.derived["targets"]),
                             "feature_records_verified": len(self.derived["features"]),
                             "estimate_records_verified": len(self.derived["estimates"]),
                             "label_records_verified": len(self.derived["labels"]),
                             "parameter_records_verified": len(self.derived["parameters"]),
                             "score_records_verified": len(self.derived["scores"]),
                             "pool_games_verified": self.derived["elo"]["games"],
                             "history_and_population_verified": True, "refit_rederived": True,
                             "content_identity_rederived": True, "database_document_rederived": True}}
        if season is not None and season not in TARGET_SEASONS:
            state = ("PROTECTED_SEASON_NOT_IN_REFERENCE" if season in PROTECTED_SEASONS else
                     "FORWARD_SEASON_NOT_IN_REFERENCE" if season >= FORWARD_SEASONS_FROM else
                     "OUTSIDE_REFERENCE_SCOPE")
            result.update(season_scope_state=state, total=0, returned=0, rows=[], next_offset=None,
                          note="season outside the retrospective 2016-2023 reference; no rows are fabricated")
            return result
        rows = [r for r in self._records(grain) if self._match(grain, r, filters)]
        total = len(rows)
        page = rows[offset:] if all_rows else rows[offset:offset + (limit or 0)]
        result.update(season_scope_state="RETROSPECTIVE_2016_2023", total=total, returned=len(page), rows=page,
                      next_offset=offset + len(page) if offset + len(page) < total else None)
        return result

    def _records(self, grain: str) -> list[dict[str, Any]]:
        if grain == "reference-summary":
            return list(self.derived["summary"]["rows"]) + list(self.derived["summary"]["comparisons"])
        return self.derived[GRAINS[grain]]

    def _match(self, grain: str, record: dict[str, Any], filters: dict[str, Any]) -> bool:
        if grain == "reference-parameter":
            return "model" not in filters or record["model_id"] == filters["model"]
        if grain == "reference-summary":
            if "season" in filters:
                if "partition" in filters and filters["season"] not in PARTITION_SEASONS[filters["partition"]]:
                    return False
                if record.get("scope_id") != str(filters["season"]):
                    return False
            elif "partition" in filters and record.get("scope_id") != filters["partition"]:
                return False
            if "model" in filters and record.get("model_id") != filters["model"]:
                return False
            if "slice" in filters and record.get("slice") != filters["slice"]:
                return False
            return True
        if "season" in filters and record["season"] != filters["season"]:
            return False
        if "partition" in filters and record["partition"] != filters["partition"]:
            return False
        if "model" in filters and record["model_id"] != filters["model"]:
            return False
        if "contest" in filters and record["contest_key"] != filters["contest"]:
            return False
        if "team" in filters:
            sides = (record["a_key"], record["b_key"]) if grain == "reference-score" else (record["team_key"],)
            if not any(bm.team_matches(filters["team"], record["season"], side, self.names) for side in sides):
                return False
        return True


GRAINS = {"reference-feature": "features", "reference-estimate": "estimates", "reference-parameter": "parameters",
          "reference-score": "scores", "reference-summary": "summary"}
PARTITION_IDS = bm.PARTITION_IDS
PARTITION_SEASONS = bm.PARTITION_SEASONS
