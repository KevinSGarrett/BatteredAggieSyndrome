r"""Fixed retrospective games-only baseline benchmark over the accepted 2016-2023 national history prefix (BAT-719,
Cycle #47 TP47-A01).

Every rule of the benchmark lives here, and the committed contract
``configs/national_retrospective_baseline_2016_2023_contract.json`` must equal these constants (the producer refuses
otherwise). The reader pins that contract's SHA-256 and the accepted history identities (:data:`ANCHORS`).

Inputs are only the accepted BAT-711 history-prefix database (its targets, the two oriented history views of each
target and the separately classified target labels) plus its own accepted out-of-scope payload, which names the
protected 2024/2025 canonical contests by key and season only. Nothing else is read: no ranking, venue, market,
fitted parameter, held model output or protected/forward outcome.

Derivation order (each step reads only what it names):

1. **features** -- one record per target and view (A = parent a side, B = parent b side): each side's accepted
   same-season strictly earlier-date games, wins, losses and ties, the exact contributing contest keys and the retained
   excluded inputs with their reasons. The accepted counts are re-verified against the contributing contests, the
   accepted pool and the accepted target dates before use (count types, sums, leakage, completeness, mirror coherence).
2. **estimates** -- from the features and the two frozen model definitions only, at game grain in A orientation, then
   derived into both oriented rows (p_B = 1 - p_A exactly). No label is in scope.
3. **labels** -- from the accepted target-label table only, separately classified: decisive (y = 1 when A wins, 0 when A
   loses), tie, missing or unsupported.
4. **scores** -- one A-oriented record per target and model, joining the estimate and the label by exact key: Brier
   (exact rational) and log loss (binary64) for decisive labels; every other label stays explicitly UNSCORED.
5. **summary** -- per model: population, scored and unscored denominators and the Brier/log-loss totals and means by
   season, by development partition (SPLIT-DEV-HIST 2016-2022, SPLIT-DEV-SEL 2023) and pooled 2016-2023.

The two models are fixed: NULL_HALF_V1 (p_A = p_B = 1/2) and SMOOTHED_HISTORY_ODDS_V1
(q = (W + T/2 + 1)/(G + 2) per side, p_A = q_A(1-q_B) / (q_A(1-q_B) + q_B(1-q_A))). Nothing is fitted, tuned,
calibrated or selected after results; there is no home bonus. A cold start (G = 0) gives q = 1/2 and is flagged.

Every record carries ``RETROSPECTIVE_DATE_ORDER_ONLY_NOT_PIT_NOT_SKILL``. Calendar order is not publication time, so
nothing here is PIT eligible, a forecast, calibrated uncertainty or evidence of predictive skill.
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
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics import readonly_sqlite
from aggie_analytics.national_history import query as history_query

# --------------------------------------------------------------------------------------------- identity and scope

POPULATION = "national_retrospective_baseline_2016_2023"
DB_FILE = "national_retrospective_baseline.sqlite"
CONTENT_SCHEMA = "BAS-RETROSPECTIVE-BASELINE-CONTENT-1"
DATABASE_SCHEMA = "BAS-RETROSPECTIVE-BASELINE-DATABASE-1"
DB_SCHEMA = "BAS-RETROSPECTIVE-BASELINE-DB-1"
PAYLOAD_SCHEMA = "BAS-RETROSPECTIVE-BASELINE-PAYLOAD-1"
PAYLOADS = ("features.jsonl", "estimates.jsonl", "labels.jsonl", "scores.jsonl", "summary.json")
CONTRACT_ID = "BAT-719-NATIONAL-RETROSPECTIVE-BASELINE-2016-2023-V1.0"
TARGET_SEASONS = (2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023)
PROTECTED_SEASONS = (2024, 2025)
FORWARD_SEASONS_FROM = 2026
VIEWS = ("A", "B")
EVIDENCE_LABEL = "RETROSPECTIVE_DATE_ORDER_ONLY_NOT_PIT_NOT_SKILL"
PIT_STATE = "PIT_ELIGIBILITY_NOT_ESTABLISHED"

#: Labels carried by the database meta and by every served response.
LABELS = {
    "evidence_label": EVIDENCE_LABEL,
    "observation_authority": "RETROSPECTIVE_OBSERVATION_ONLY",
    "pit_eligibility": PIT_STATE,
    "temporal_basis": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME",
    "forecast_status": "NOT_A_FORECAST_RETROSPECTIVE_DIAGNOSTIC_ONLY",
    "predictive_skill": "NOT_ESTABLISHED",
    "calibration": "NOT_ESTABLISHED",
    "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
    "selection": "EXPLICIT_BENCHMARK_SELECTION_ONLY_NEVER_A_DEFAULT",
}
#: Labels carried by every individual record.
RECORD_LABELS = {"evidence_label": EVIDENCE_LABEL, "pit_eligibility": PIT_STATE}

#: The governing split (governance/PROTECTED_SPLIT_REGISTRY.csv, sha256 bound by the contract): development
#: historical through 2022, development selection 2023; 2024-2025 protected and 2026+ forward never enter.
SPLIT = {
    "registry_path": "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "registry_sha256": "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764",
    "partitions": [{"split_id": "SPLIT-DEV-HIST", "role": "DEVELOPMENT", "seasons": [2016, 2017, 2018, 2019, 2020,
                                                                                     2021, 2022]},
                   {"split_id": "SPLIT-DEV-SEL", "role": "DEVELOPMENT_SELECTION", "seasons": [2023]}],
    "excluded": [{"split_id": "SPLIT-PROTECTED", "role": "PROTECTED_TEST", "seasons": [2024, 2025]},
                 {"split_id": "SPLIT-FORWARD", "role": "FORWARD_SHADOW", "seasons_from": 2026}],
    "rule": "actual canonical-game membership outranks any supplied season label: a contest named by the accepted "
            "out-of-scope (2024/2025) payload is refused wherever it appears",
}
PARTITION_OF = {season: ("SPLIT-DEV-SEL" if season == 2023 else "SPLIT-DEV-HIST") for season in TARGET_SEASONS}

MODEL_NULL = "NULL_HALF_V1"
MODEL_SMOOTHED = "SMOOTHED_HISTORY_ODDS_V1"
MODEL_IDS = (MODEL_NULL, MODEL_SMOOTHED)
#: The two frozen model definitions; each estimate names the SHA-256 of its canonical definition.
MODELS = {
    MODEL_NULL: {"model_id": MODEL_NULL, "version": 1, "family": "FIXED_CONSTANT",
                 "formula": "p_A = p_B = 1/2", "inputs": [],
                 "parameters": {"probability": {"numerator": 1, "denominator": 2}},
                 "fitted": False, "home_advantage": None, "role": "NULL_COMPARISON"},
    MODEL_SMOOTHED: {"model_id": MODEL_SMOOTHED, "version": 1, "family": "FIXED_SMOOTHED_RECORD_ODDS_RATIO",
                     "formula": "q_X = (W_X + T_X/2 + 1)/(G_X + 2) for each side X; "
                                "p_A = q_A(1-q_B) / (q_A(1-q_B) + q_B(1-q_A)); p_B = 1 - p_A",
                     "inputs": ["games", "wins", "losses", "ties"],
                     "parameters": {"pseudo_wins": 1, "pseudo_games": 2,
                                    "tie_weight": {"numerator": 1, "denominator": 2}},
                     "cold_start": "G = 0 gives q = 1/2 (flagged; the target is kept)",
                     "fitted": False, "home_advantage": None, "role": "FIXED_HISTORY_COMPARISON"},
}

#: The frozen numeric contract (TP47 section 3).
NUMERIC_CONTRACT = {
    "integers": "JSON integers only; a boolean or an integral float is not an integer; no binary float appears in "
                "any payload, record, meta value or identity document",
    "rationals": "{numerator, denominator} JSON integers in lowest terms with denominator > 0",
    "decimal_display": "probability_decimal and brier_decimal: the exact rational rounded half-even to 12 decimal "
                       "places by integer arithmetic",
    "probability": "exact rational; 0 < p < 1 always (smoothing); p_A + p_B = 1 exactly",
    "brier": "(p_A - y)^2 exact rational; totals are exact rational sums and means are total / scored count",
    "log_loss": "-ln(p_A) when y = 1 and -ln(1 - p_A) when y = 0, with p the correctly rounded binary64 of the exact "
                "rational and math.log of pinned CPython 3.12; serialized as repr() text",
    "log_loss_aggregation": "math.fsum of the per-game binary64 values in canonical target order; mean = fsum / "
                            "scored count (binary64); serialized as repr() text",
    "independent_tolerance": "an independent recomputation of a transcendental (log-loss) value agrees within 1E-12 "
                             "absolute; never applied to identity bytes, classification or rational fields",
    "canonical_json": "json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) as UTF-8",
}
DISPLAY_PLACES = 12

SCOPE = {
    "population": "ACCEPTED_BAT711_FBS_ESTIMAND_TARGETS_2016_2023",
    "target_seasons": list(TARGET_SEASONS),
    "views_per_target": 2,
    "models": list(MODEL_IDS),
    "score_orientation": "A",
    "protected_seasons": list(PROTECTED_SEASONS),
    "forward_seasons_from": FORWARD_SEASONS_FROM,
    "evidence_label": EVIDENCE_LABEL,
}

#: The accepted history and the committed contract this reader binds (TP47 section 2, INPUT_BINDINGS).
ANCHORS: dict[str, Any] = {
    "contract_id": CONTRACT_ID,
    "contract_sha256": "32a2ffb6c55d5fda37e06a75847ab3c21345205524ca5a7f60a2ef99b8142ee4",
    "history": {
        "contract_id": "BAT-711-NATIONAL-HISTORY-PREFIX-2016-2023-V1.0",
        "contract_sha256": "2646a5cbe9a1daff7135671b85c98239b250d493c53c4bc066f57805e1e4f76c",
        "database_identity": "aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b",
        "sqlite_sha256": "e137208cb3e9fec55c9b68e6af5c61e036ea7ea60a8973d9be9c35c358b17060",
        "content_identity": "58c2bf7d6e9c70c2ba2a9e4dd583a89ace10062cc49aafe00d2f9675c84afe63",
        "out_of_scope_sha256": "3dce4920fe878f696df99f923d082faa02a0c22f96aebf559b779488d807039e",
        "out_of_scope_rows": 3360,
        "expected_targets": {"2016": 733, "2017": 753, "2018": 766, "2019": 769, "2020": 524, "2021": 767,
                             "2022": 775, "2023": 788},
    },
}

IDENTITY_RE = re.compile(r"^[0-9a-f]{64}$")
ORG_KEY_RE = re.compile(r"^(?:org:)?([0-9]{1,12})$")
CONTEST_KEY_RE = re.compile(r"^(?:ncaa|nolink|cfbd):[^\x00-\x1f]{1,200}$")
LABEL_FIELDS = ("y_a", "label_state", "a_result", "b_result", "a_points", "b_points", "a_margin", "outcome",
                "unscored_reason")


class BenchmarkError(ValueError):
    """A refused build input or a refused benchmark; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --------------------------------------------------------------------------------------------- canonical values

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


def model_sha256(model_id: str) -> str:
    return sha256_bytes(canonical_json_bytes(MODELS[model_id]))


def numeric_contract_sha256() -> str:
    return sha256_bytes(canonical_json_bytes(NUMERIC_CONTRACT))


def rational(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def decimal_text(value: Fraction, places: int = DISPLAY_PLACES) -> str:
    """The exact rational rounded half-even to ``places`` decimals by integer arithmetic."""
    sign = "-" if value < 0 else ""
    n, d = abs(value.numerator), value.denominator
    scaled, rem = divmod(n * 10 ** places, d)
    if rem * 2 > d or (rem * 2 == d and scaled % 2 == 1):
        scaled += 1
    whole, frac = divmod(scaled, 10 ** places)
    return f"{sign}{whole}.{frac:0{places}d}"


def is_int(value: Any) -> bool:
    """A JSON integer for this contract: neither a boolean nor an integral float."""
    return type(value) is int


def contains_float(value: Any) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(contains_float(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_float(v) for v in value)
    return False


# --------------------------------------------------------------------------------------------- accepted inputs

def _ordered(items: list[Any], order: str) -> list[Any]:
    if order == "natural":
        return list(items)
    if order == "reverse":
        return list(reversed(items))
    if order.startswith("shuffle:") and order[8:].isdigit():
        out = list(items)
        random.Random(int(order[8:])).shuffle(out)
        return out
    raise BenchmarkError("INPUT_ORDER_INVALID", f"input order {order!r}")


def _history_error(exc: history_query.HistoryQueryError) -> BenchmarkError:
    code = exc.code if exc.code.startswith("DATABASE_LOCATION_") else f"HISTORY_{exc.code}"
    return BenchmarkError(code, str(exc))


def history_binding(anchors: dict[str, Any]) -> dict[str, Any]:
    """The parent claim every benchmark carries: exactly the anchored history binding."""
    return dict(anchors["history"])


def load_history(history_database: Path, anchors: dict[str, Any], *, input_order: str = "natural") -> dict[str, Any]:
    """Verify the accepted history database (location, manifest identity, bytes, meta, counts) through the accepted
    history reader, pin it to the anchored identities, read the protected out-of-scope membership from its own content
    payload, and return every target, view, label and pool contest in ``input_order``."""
    h = anchors["history"]
    try:
        handle = history_query.NationalHistoryDatabase(Path(history_database))
    except history_query.HistoryQueryError as exc:
        raise _history_error(exc) from exc
    try:
        binding = handle.binding
        pinned = {"database_identity": binding["database_identity"], "sqlite_sha256": binding["database_sha256"],
                  "content_identity": binding["content_identity"], "contract_sha256": binding["contract_sha256"],
                  "contract_id": handle.meta.get("contract_id")}
        differing = sorted(k for k, v in pinned.items() if v != h.get(k))
        if differing:
            raise BenchmarkError("BENCHMARK_HISTORY_MISMATCH",
                                 f"the history database differs from the bound accepted history on {differing}")
        try:
            payload_sha = json.loads(handle.meta.get("payload_sha256") or "null")
        except ValueError:
            payload_sha = None
        if not isinstance(payload_sha, dict) or payload_sha.get("out_of_scope.jsonl") != h["out_of_scope_sha256"]:
            raise BenchmarkError("BENCHMARK_HISTORY_MISMATCH", "the history names another out-of-scope payload")
        conn = handle.conn
        targets = [(int(r[0]), r[1], r[2], r[3], r[4], r[5], r[6]) for r in conn.execute(
            "SELECT ord, contest_key, season, contest_date, a_key, b_key, record FROM targets ORDER BY ord")]
        views = [(int(r[0]), r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in conn.execute(
            "SELECT ord, target_contest_key, view, season, target_date, team_key, opponent_key, record FROM history "
            "ORDER BY ord")]
        labels = [(int(r[0]), r[1], r[2]) for r in conn.execute(
            "SELECT ord, contest_key, record FROM target_labels ORDER BY ord")]
        exclusions = [(r[0], r[1], r[2]) for r in conn.execute(
            "SELECT contest_key, season, record FROM exclusions ORDER BY ord")]
    finally:
        handle.close()
    content = Path(history_database).resolve().parent.parent / h["content_identity"] / "out_of_scope.jsonl"
    try:
        raw = content.read_bytes()
    except OSError as exc:
        raise BenchmarkError("BENCHMARK_HISTORY_CONTENT_MISSING",
                             f"the history's protected out-of-scope payload is unreadable at {content}: {exc}") from exc
    if sha256_bytes(raw) != h["out_of_scope_sha256"]:
        raise BenchmarkError("BENCHMARK_HISTORY_MISMATCH", "the out-of-scope payload bytes differ from the binding")
    protected: dict[str, int] = {}
    for line in raw.decode("utf-8").splitlines():
        row = json.loads(line)
        protected[row["contest_key"]] = row["season"]
    if len(protected) != h["out_of_scope_rows"] or set(protected.values()) - set(PROTECTED_SEASONS):
        raise BenchmarkError("BENCHMARK_HISTORY_MISMATCH", "the out-of-scope payload is not the protected membership")
    return {"binding": pinned, "protected": protected,
            "targets": _ordered(targets, input_order), "views": _ordered(views, input_order),
            "labels": _ordered(labels, input_order), "exclusions": _ordered(exclusions, input_order)}


# --------------------------------------------------------------------------------------------- 1. features

def _refuse(code: str, message: str) -> None:
    raise BenchmarkError(code, message)


def _json(text: Any, code: str, what: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise BenchmarkError(code, f"{what} is not JSON: {exc}") from exc
    if not isinstance(value, dict):
        _refuse(code, f"{what} is not a JSON object")
    return value


def target_order_key(target: dict[str, Any]) -> tuple[int, str, str]:
    return (target["season"], target["contest_date"], target["contest_key"])


def _targets(inputs: dict[str, Any], anchors: dict[str, Any]) -> list[dict[str, Any]]:
    protected = inputs["protected"]
    out, seen = [], set()
    for ord_, key, season, date, a_key, b_key, text in inputs["targets"]:
        if key in protected:
            _refuse("BENCHMARK_PROTECTED_KEY", f"target {key} is a protected {protected[key]} canonical contest")
        if not is_int(season) or season not in TARGET_SEASONS:
            _refuse("BENCHMARK_PROTECTED_KEY", f"target {key} season {season!r} is outside 2016-2023")
        record = _json(text, "BENCHMARK_HISTORY_INPUT_INVALID", f"target {key}")
        if (record.get("contest_key"), record.get("season"), record.get("contest_date"), record.get("a_key"),
                record.get("b_key"), record.get("record_type")) != (key, season, date, a_key, b_key, "target"):
            _refuse("BENCHMARK_HISTORY_INPUT_INVALID", f"target {key} record differs from its index columns")
        if key in seen:
            _refuse("BENCHMARK_HISTORY_COLLECTION_MISMATCH", f"target {key} repeats")
        seen.add(key)
        out.append({"ord": ord_, "contest_key": key, "season": season, "contest_date": date, "a_key": a_key,
                    "b_key": b_key, "a_team_name": record.get("a_team_name"), "b_team_name": record.get("b_team_name"),
                    "a_org_id": record.get("a_org_id"), "b_org_id": record.get("b_org_id"),
                    "site": record.get("parent_site"), "record_sha256": sha256_bytes(str(text).encode("utf-8"))})
    counts: dict[str, int] = {}
    for t in out:
        counts[str(t["season"])] = counts.get(str(t["season"]), 0) + 1
    if counts != anchors["history"]["expected_targets"]:
        _refuse("BENCHMARK_HISTORY_COLLECTION_MISMATCH",
                f"targets by season {counts} != accepted {anchors['history']['expected_targets']}")
    return sorted(out, key=target_order_key)


def _pool(inputs: dict[str, Any], targets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Every accepted history-pool contest (targets plus pool-member exclusions): key -> season, date, sides."""
    pool = {t["contest_key"]: {"season": t["season"], "date": t["contest_date"], "sides": (t["a_key"], t["b_key"])}
            for t in targets}
    for key, season, text in inputs["exclusions"]:
        record = _json(text, "BENCHMARK_HISTORY_INPUT_INVALID", f"exclusion {key}")
        if record.get("history_pool_member") is True:
            if key in pool:
                _refuse("BENCHMARK_HISTORY_COLLECTION_MISMATCH", f"pool contest {key} repeats")
            pool[key] = {"season": season, "date": record.get("contest_date"),
                         "sides": (record.get("a_key"), record.get("b_key"))}
    return pool


def _team_pool_index(pool: dict[str, dict[str, Any]]) -> dict[tuple[str, int], list[tuple[str, str]]]:
    index: dict[tuple[str, int], list[tuple[str, str]]] = {}
    for key, row in pool.items():
        for side in row["sides"]:
            if side:
                index.setdefault((side, row["season"]), []).append((row["date"], key))
    return index


def _side(history: Any, *, team_key: str, target: dict[str, Any], pool: dict[str, dict[str, Any]],
          team_pool: dict[tuple[str, int], list[tuple[str, str]]], protected: dict[str, int],
          observed: dict[tuple[str, str], tuple[int, int, Any]], where: str) -> dict[str, Any]:
    """Verify one side's accepted same-season prior history and return its feature member. Each contributing
    contest's points as this team saw them are recorded in ``observed`` (one value per contest and team)."""
    if not isinstance(history, dict):
        _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: history is not an object")
    if history.get("team_key") != team_key or history.get("season") != target["season"]:
        _refuse("BENCHMARK_ORIENTATION_INVALID", f"{where}: history names another team or season")
    counts = {k: history.get(k) for k in ("games", "wins", "losses", "ties")}
    if not all(is_int(v) and v >= 0 for v in counts.values()):
        _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: counts are not nonnegative integers: {counts}")
    if counts["wins"] + counts["losses"] + counts["ties"] != counts["games"]:
        _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: W + L + T != G")
    contributing = history.get("contributing")
    if not isinstance(contributing, list) or len(contributing) != counts["games"]:
        _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: contributing contests do not number G")
    tally = {"W": 0, "L": 0, "T": 0}
    keys = []
    for item in contributing:
        if not isinstance(item, dict):
            _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: a contributing contest is not an object")
        key, date = item.get("contest_key"), item.get("contest_date")
        pf, pa, result = item.get("points_for"), item.get("points_against"), item.get("result")
        if key in protected:
            _refuse("BENCHMARK_PROTECTED_KEY", f"{where}: contributing {key} is a protected canonical contest")
        if key == target["contest_key"]:
            _refuse("BENCHMARK_FEATURE_LEAKAGE", f"{where}: the target contest contributes to its own features")
        if not isinstance(date, str) or date >= target["contest_date"]:
            _refuse("BENCHMARK_FEATURE_LEAKAGE", f"{where}: contributing {key} is not strictly earlier ({date})")
        member = pool.get(key)
        if member is None or member["season"] != target["season"] or member["date"] != date or \
                team_key not in member["sides"]:
            _refuse("BENCHMARK_FEATURE_LEAKAGE", f"{where}: contributing {key} is not an accepted same-season prior")
        if not (is_int(pf) and is_int(pa) and pf >= 0 and pa >= 0):
            _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: contributing {key} points are not integers")
        expected = "W" if pf > pa else "L" if pf < pa else "T"
        if result != expected:
            _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: contributing {key} result {result!r} != {expected}")
        seen = observed.setdefault((key, team_key), (pf, pa, item.get("opponent_key")))
        if seen != (pf, pa, item.get("opponent_key")):
            _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: contributing {key} differs between histories")
        tally[expected] += 1
        keys.append(key)
    if (tally["W"], tally["L"], tally["T"]) != (counts["wins"], counts["losses"], counts["ties"]):
        _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: W/L/T differ from the contributing results")
    if history.get("contributing_contest_keys") != keys or len(set(keys)) != len(keys):
        _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: contributing keys differ from the contributing contests")
    eligible = sorted(k for d, k in team_pool.get((team_key, target["season"]), []) if d < target["contest_date"])
    if sorted(keys) != eligible:
        _refuse("BENCHMARK_FEATURE_INPUT_INVALID",
                f"{where}: contributing contests differ from the accepted same-season earlier pool")
    state = "COLD_START" if counts["games"] == 0 else "HAS_PRIOR_CONTESTS"
    if history.get("history_state") != state:
        _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: history_state differs from G")
    excluded = []
    for item in history.get("excluded_inputs") or []:
        if not isinstance(item, dict) or not isinstance(item.get("contest_key"), str) or \
                not isinstance(item.get("reasons"), list) or not item["reasons"] or \
                not all(isinstance(r, str) for r in item["reasons"]) or item["contest_key"] in keys:
            _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: an excluded input is malformed")
        if item["contest_key"] in protected:
            _refuse("BENCHMARK_PROTECTED_KEY", f"{where}: excluded input {item['contest_key']} is protected")
        excluded.append({"contest_key": item["contest_key"], "contest_date": item.get("contest_date"),
                         "reasons": list(item["reasons"])})
    if not isinstance(history.get("excluded_inputs"), list):
        _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"{where}: excluded inputs are not a list")
    return {"games": counts["games"], "wins": counts["wins"], "losses": counts["losses"], "ties": counts["ties"],
            "cold_start": counts["games"] == 0, "contributing_contest_keys": keys, "excluded_inputs": excluded}


def derive_features(inputs: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    """Targets and both oriented feature records of every target, verified against the accepted history."""
    targets = _targets(inputs, anchors)
    by_key = {t["contest_key"]: t for t in targets}
    pool = _pool(inputs, targets)
    team_pool = _team_pool_index(pool)
    protected = inputs["protected"]
    observed: dict[tuple[str, str], tuple[int, int, Any]] = {}
    views: dict[tuple[str, str], tuple[int, str, dict[str, Any]]] = {}
    for ord_, key, view, season, date, team_key, opponent_key, text in inputs["views"]:
        if key in protected:
            _refuse("BENCHMARK_PROTECTED_KEY", f"view of {key}: a protected canonical contest")
        target = by_key.get(key)
        if target is None:
            _refuse("BENCHMARK_HISTORY_COLLECTION_MISMATCH", f"history view of {key} names no accepted target")
        if (key, view) in views:
            _refuse("BENCHMARK_HISTORY_COLLECTION_MISMATCH", f"view {key}/{view} repeats")
        record = _json(text, "BENCHMARK_HISTORY_INPUT_INVALID", f"view {key}/{view}")
        expected = (target["a_key"], target["b_key"]) if view == "A" else (target["b_key"], target["a_key"]) \
            if view == "B" else None
        if expected is None or (team_key, opponent_key) != expected or \
                (record.get("team_key"), record.get("opponent_key"), record.get("view"),
                 record.get("target_contest_key")) != (team_key, opponent_key, view, key):
            _refuse("BENCHMARK_ORIENTATION_INVALID", f"view {key}/{view} is not the target's {view} orientation")
        names = (target["a_team_name"], target["b_team_name"]) if view == "A" else \
            (target["b_team_name"], target["a_team_name"])
        if (record.get("team_name"), record.get("opponent_name")) != names:
            _refuse("BENCHMARK_ORIENTATION_INVALID", f"view {key}/{view} names other teams than its source season")
        if (season, date, record.get("season"), record.get("target_date")) != \
                (target["season"], target["contest_date"], target["season"], target["contest_date"]):
            _refuse("BENCHMARK_HISTORY_INPUT_INVALID", f"view {key}/{view} season/date differ from the target")
        views[(key, view)] = (ord_, str(text), record)
    if len(views) != 2 * len(targets) or any((t["contest_key"], v) not in views for t in targets for v in VIEWS):
        _refuse("BENCHMARK_HISTORY_COLLECTION_MISMATCH", "every target needs exactly its two oriented views")
    features: list[dict[str, Any]] = []
    for target in targets:
        a_ord, a_text, a_rec = views[(target["contest_key"], "A")]
        b_ord, b_text, b_rec = views[(target["contest_key"], "B")]
        sides = {}
        for view, rec in (("A", a_rec), ("B", b_rec)):
            team_key, opponent_key = (target["a_key"], target["b_key"]) if view == "A" else \
                (target["b_key"], target["a_key"])
            where = f"{target['contest_key']}/{view}"
            sides[view] = (_side(rec.get("team_history"), team_key=team_key, target=target, pool=pool,
                                 team_pool=team_pool, protected=protected, observed=observed, where=where + "/team"),
                           _side(rec.get("opponent_history"), team_key=opponent_key, target=target, pool=pool,
                                 team_pool=team_pool, protected=protected, observed=observed,
                                 where=where + "/opponent"))
        # every side verifies first, so a defect in one view is refused for its own cause, then the views must mirror
        if canonical_json_bytes(a_rec.get("team_history")) != canonical_json_bytes(b_rec.get("opponent_history")) or \
                canonical_json_bytes(a_rec.get("opponent_history")) != canonical_json_bytes(b_rec.get("team_history")):
            _refuse("BENCHMARK_ORIENTATION_INVALID", f"views of {target['contest_key']} are not mirror images")
        for view, ord_, text, rec in (("A", a_ord, a_text, a_rec), ("B", b_ord, b_text, b_rec)):
            team_key, opponent_key = (target["a_key"], target["b_key"]) if view == "A" else \
                (target["b_key"], target["a_key"])
            team_name, opponent_name = (target["a_team_name"], target["b_team_name"]) if view == "A" else \
                (target["b_team_name"], target["a_team_name"])
            team_org, opponent_org = (target["a_org_id"], target["b_org_id"]) if view == "A" else \
                (target["b_org_id"], target["a_org_id"])
            team, opponent = sides[view]
            features.append({
                "record_type": "feature", "contest_key": target["contest_key"], "season": target["season"],
                "contest_date": target["contest_date"], "partition": PARTITION_OF[target["season"]], "view": view,
                "team_key": team_key, "team_name": team_name, "team_org_id": team_org,
                "opponent_key": opponent_key, "opponent_name": opponent_name, "opponent_org_id": opponent_org,
                "target_site": target["site"], "team": team, "opponent": opponent,
                "prior_rule": "SAME_SEASON_DATE_STRICTLY_BEFORE_TARGET_DATE",
                "source_history": {"database_identity": inputs["binding"]["database_identity"], "history_ord": ord_,
                                   "record_sha256": sha256_bytes(text.encode("utf-8")),
                                   "target_record_sha256": target["record_sha256"]},
                **RECORD_LABELS})
    for (key, team), (pf, pa, opponent) in observed.items():
        mirror = observed.get((key, opponent))
        if mirror is not None and (mirror[0], mirror[1], mirror[2]) != (pa, pf, team):
            _refuse("BENCHMARK_FEATURE_INPUT_INVALID", f"contributing {key} is not mirrored between its two teams")
    return {"targets": targets, "features": features, "pool": pool, "observed": observed}


# --------------------------------------------------------------------------------------------- 2. estimates

def strength_q(side: dict[str, Any]) -> Fraction:
    """q = (W + T/2 + 1) / (G + 2), exactly; a cold start (G = 0) gives 1/2."""
    return Fraction(2 * side["wins"] + side["ties"] + 2, 2 * side["games"] + 4)


def smoothed_probability(q_a: Fraction, q_b: Fraction) -> Fraction:
    numerator = q_a * (1 - q_b)
    return numerator / (numerator + q_b * (1 - q_a))


def derive_estimates(features: list[dict[str, Any]], feature_lines: list[str] | None = None) -> list[dict[str, Any]]:
    """Both models at game grain in A orientation from the A-view features only, then both oriented rows. No label is
    read here: the arguments hold only feature records (and their canonical lines)."""
    lines = feature_lines if feature_lines is not None else [canonical_line(f) for f in features]
    by_view = {(f["contest_key"], f["view"]): (f, line) for f, line in zip(features, lines)}
    shas = {model_id: model_sha256(model_id) for model_id in MODEL_IDS}
    out: list[dict[str, Any]] = []
    for feature in features:
        if feature["view"] != "A":
            continue
        (a, a_line), (b, b_line) = by_view[(feature["contest_key"], "A")], by_view[(feature["contest_key"], "B")]
        for model_id in MODEL_IDS:
            if model_id == MODEL_NULL:
                q_a = q_b = None
                p_a = Fraction(1, 2)
            else:
                q_a, q_b = strength_q(a["team"]), strength_q(a["opponent"])
                if (strength_q(b["team"]), strength_q(b["opponent"])) != (q_b, q_a):
                    _refuse("BENCHMARK_ORIENTATION_INVALID", f"{a['contest_key']}: B view strengths differ")
                p_a = smoothed_probability(q_a, q_b)
            if not 0 < p_a < 1:
                _refuse("BENCHMARK_ESTIMATE_INVALID", f"{a['contest_key']}: p_A {p_a} outside (0, 1)")
            for orientation, mine, line, q_self, q_other in (("A", a, a_line, q_a, q_b), ("B", b, b_line, q_b, q_a)):
                p = p_a if orientation == "A" else 1 - p_a
                out.append({
                    "record_type": "estimate", "contest_key": a["contest_key"], "season": a["season"],
                    "contest_date": a["contest_date"], "partition": a["partition"], "model_id": model_id,
                    "model_sha256": shas[model_id], "orientation": orientation,
                    "team_key": mine["team_key"], "team_name": mine["team_name"],
                    "opponent_key": mine["opponent_key"], "opponent_name": mine["opponent_name"],
                    "probability": rational(p), "probability_decimal": decimal_text(p),
                    "opponent_probability": rational(1 - p), "opponent_probability_decimal": decimal_text(1 - p),
                    "team_strength_q": rational(q_self) if q_self is not None else None,
                    "opponent_strength_q": rational(q_other) if q_other is not None else None,
                    "team_cold_start": mine["team"]["cold_start"],
                    "opponent_cold_start": mine["opponent"]["cold_start"],
                    "game_grain_probability_a": rational(p_a),
                    "feature_record_sha256": sha256_bytes(line.encode("utf-8")),
                    "game_feature_record_sha256": sha256_bytes(a_line.encode("utf-8")),
                    **RECORD_LABELS})
    return out


# --------------------------------------------------------------------------------------------- 3. labels

def _label_state(target: dict[str, Any], record: dict[str, Any] | None) -> tuple[str, int | None, str | None]:
    if record is None:
        return "MISSING", None, "LABEL_MISSING"
    a_pts, b_pts, a_res, b_res = (record.get("a_points"), record.get("b_points"), record.get("a_result"),
                                  record.get("b_result"))
    consistent = (record.get("record_type") == "target_label" and
                  (record.get("contest_key"), record.get("season"), record.get("contest_date"), record.get("a_key"),
                   record.get("b_key")) == (target["contest_key"], target["season"], target["contest_date"],
                                            target["a_key"], target["b_key"]) and
                  is_int(a_pts) and is_int(b_pts) and a_pts >= 0 and b_pts >= 0)
    if consistent:
        expected = ("W", "L") if a_pts > b_pts else ("L", "W") if a_pts < b_pts else ("T", "T")
        consistent = (a_res, b_res) == expected
    if not consistent:
        return "UNSUPPORTED", None, "LABEL_UNSUPPORTED"
    if a_res == "T":
        return "TIE", None, "LABEL_TIE"
    return "DECISIVE", 1 if a_res == "W" else 0, None


def derive_labels(inputs: dict[str, Any], targets: list[dict[str, Any]],
                  observed: dict[tuple[str, str], tuple[int, int, Any]]) -> list[dict[str, Any]]:
    """One separately classified label per target from the accepted target-label table only; it never feeds a
    feature or an estimate. ``observed`` (the points each team's later accepted history counted for a contest) is used
    only to refuse a label that contradicts the same accepted history."""
    by_key = {t["contest_key"]: t for t in targets}
    rows: dict[str, tuple[int, str]] = {}
    for ord_, key, text in inputs["labels"]:
        if key not in by_key:
            _refuse("BENCHMARK_HISTORY_COLLECTION_MISMATCH", f"label {key} names no accepted target")
        if key in rows:
            _refuse("BENCHMARK_HISTORY_COLLECTION_MISMATCH", f"label {key} repeats")
        rows[key] = (ord_, str(text))
    out = []
    for target in targets:
        found = rows.get(target["contest_key"])
        record = None
        if found is not None:
            try:
                parsed = json.loads(found[1])
                record = parsed if isinstance(parsed, dict) else {}
            except ValueError:
                record = {}
        state, y, reason = _label_state(target, record)
        out.append({
            "record_type": "label", "contest_key": target["contest_key"], "season": target["season"],
            "contest_date": target["contest_date"], "partition": PARTITION_OF[target["season"]],
            "a_key": target["a_key"], "b_key": target["b_key"],
            "a_points": record.get("a_points") if state in ("DECISIVE", "TIE") else None,
            "b_points": record.get("b_points") if state in ("DECISIVE", "TIE") else None,
            "a_result": record.get("a_result") if state in ("DECISIVE", "TIE") else None,
            "label_state": state, "y_a": y, "unscored_reason": reason,
            "label_authority": "POSTGAME_OUTCOME_SEPARATED_FROM_FEATURES_AND_ESTIMATES",
            "source_label": None if found is None else {"history_ord": found[0],
                                                        "record_sha256": sha256_bytes(found[1].encode("utf-8"))},
            **RECORD_LABELS})
    _check_label_consistency(out, observed)
    return out


def _check_label_consistency(labels: list[dict[str, Any]], observed: dict[tuple[str, str], tuple[int, int, Any]]
                             ) -> None:
    """A decisive or tied label must agree with the same contest's points wherever the accepted history later counts
    it as a contributing prior (either team): a contradiction is a refused input, never a label choice."""
    for label in labels:
        if label["label_state"] not in ("DECISIVE", "TIE"):
            continue
        for team, points in ((label["a_key"], (label["a_points"], label["b_points"])),
                             (label["b_key"], (label["b_points"], label["a_points"]))):
            seen = observed.get((label["contest_key"], team))
            if seen is not None and (seen[0], seen[1]) != points:
                _refuse("BENCHMARK_LABEL_INPUT_INVALID",
                        f"label {label['contest_key']} contradicts the accepted history's later count for {team}")


# --------------------------------------------------------------------------------------------- 4. scores

def log_loss_value(p_a: Fraction, y: int) -> float:
    q = p_a if y == 1 else 1 - p_a
    return -math.log(q.numerator / q.denominator)


def derive_scores(estimates: list[dict[str, Any]], labels: list[dict[str, Any]],
                  estimate_lines: list[str] | None = None, label_lines: list[str] | None = None
                  ) -> list[dict[str, Any]]:
    """One A-oriented score per target and model; the label joins by exact contest key."""
    est_lines = estimate_lines if estimate_lines is not None else [canonical_line(e) for e in estimates]
    lab_lines = label_lines if label_lines is not None else [canonical_line(lab) for lab in labels]
    by_key = {lab["contest_key"]: (lab, line) for lab, line in zip(labels, lab_lines)}
    out = []
    for est, est_line in zip(estimates, est_lines):
        if est["orientation"] != "A":
            continue
        label, label_line = by_key[est["contest_key"]]
        p_a = Fraction(est["probability"]["numerator"], est["probability"]["denominator"])
        record = {"record_type": "score", "contest_key": est["contest_key"], "season": est["season"],
                  "contest_date": est["contest_date"], "partition": est["partition"], "model_id": est["model_id"],
                  "model_sha256": est["model_sha256"], "orientation": "A", "a_key": label["a_key"],
                  "b_key": label["b_key"], "a_team_name": est["team_name"], "b_team_name": est["opponent_name"],
                  "probability_a": rational(p_a), "probability_a_decimal": decimal_text(p_a),
                  "label_state": label["label_state"], "y_a": label["y_a"],
                  "estimate_record_sha256": sha256_bytes(est_line.encode("utf-8")),
                  "label_record_sha256": sha256_bytes(label_line.encode("utf-8")), **RECORD_LABELS}
        if label["y_a"] is None:
            record.update(score_state="UNSCORED", unscored_reason=label["unscored_reason"], brier=None,
                          brier_decimal=None, log_loss=None)
        else:
            brier = (p_a - label["y_a"]) ** 2
            record.update(score_state="SCORED", unscored_reason=None, brier=rational(brier),
                          brier_decimal=decimal_text(brier), log_loss=repr(log_loss_value(p_a, label["y_a"])))
        out.append(record)
    return out


# --------------------------------------------------------------------------------------------- 5. summary

def _scopes() -> list[tuple[str, str, tuple[int, ...]]]:
    scopes = [("SEASON", str(s), (s,)) for s in TARGET_SEASONS]
    scopes += [("PARTITION", p["split_id"], tuple(p["seasons"])) for p in SPLIT["partitions"]]
    scopes.append(("POOLED", "2016-2023", TARGET_SEASONS))
    return scopes


def derive_summary(features: list[dict[str, Any]], estimates: list[dict[str, Any]], labels: list[dict[str, Any]],
                   scores: list[dict[str, Any]]) -> dict[str, Any]:
    rows, comparisons = [], []
    for kind, scope_id, seasons in _scopes():
        scope_labels = [lab for lab in labels if lab["season"] in seasons]
        scope_features = [f for f in features if f["season"] in seasons and f["view"] == "A"]
        by_model = {}
        for model_id in MODEL_IDS:
            chosen = [s for s in scores if s["model_id"] == model_id and s["season"] in seasons]
            scored = [s for s in chosen if s["score_state"] == "SCORED"]
            unscored: dict[str, int] = {}
            for s in chosen:
                if s["score_state"] != "SCORED":
                    unscored[s["unscored_reason"]] = unscored.get(s["unscored_reason"], 0) + 1
            brier_total = sum((Fraction(s["brier"]["numerator"], s["brier"]["denominator"]) for s in scored),
                              Fraction(0))
            log_values = [float(s["log_loss"]) for s in scored]
            log_total = math.fsum(log_values)
            row = {"model_id": model_id, "model_sha256": model_sha256(model_id), "scope_kind": kind,
                   "scope_id": scope_id, "seasons": list(seasons), "population_targets": len(scope_labels),
                   "score_records": len(chosen), "scored_targets": len(scored),
                   "unscored_targets": len(chosen) - len(scored), "unscored_by_reason": unscored,
                   "brier_total": rational(brier_total), "brier_total_decimal": decimal_text(brier_total),
                   "brier_mean": rational(brier_total / len(scored)) if scored else None,
                   "brier_mean_decimal": decimal_text(brier_total / len(scored)) if scored else None,
                   "log_loss_total": repr(log_total), "log_loss_mean": repr(log_total / len(scored)) if scored else None,
                   "targets_team_a_cold_start": sum(1 for f in scope_features if f["team"]["cold_start"]),
                   "targets_team_b_cold_start": sum(1 for f in scope_features if f["opponent"]["cold_start"]),
                   "targets_both_cold_start": sum(1 for f in scope_features
                                                  if f["team"]["cold_start"] and f["opponent"]["cold_start"])}
            if len(chosen) != len(scope_labels):
                _refuse("BENCHMARK_SUMMARY_INVALID", f"{model_id} {scope_id}: score records != population")
            rows.append(row)
            by_model[model_id] = row
        null, smoothed = by_model[MODEL_NULL], by_model[MODEL_SMOOTHED]
        if null["brier_mean"] is not None and smoothed["brier_mean"] is not None:
            diff = Fraction(smoothed["brier_mean"]["numerator"], smoothed["brier_mean"]["denominator"]) - \
                Fraction(null["brier_mean"]["numerator"], null["brier_mean"]["denominator"])
            log_diff = repr(float(smoothed["log_loss_mean"]) - float(null["log_loss_mean"]))
            comparisons.append({"scope_kind": kind, "scope_id": scope_id, "scored_targets": smoothed["scored_targets"],
                                "brier_mean_difference_smoothed_minus_null": rational(diff),
                                "brier_mean_difference_decimal": decimal_text(diff),
                                "log_loss_mean_difference_smoothed_minus_null": log_diff,
                                "reading": "descriptive retrospective difference only; negative favours the "
                                           "smoothed comparison, positive the null; no significance, skill or "
                                           "calibration claim"})
        else:
            comparisons.append({"scope_kind": kind, "scope_id": scope_id, "scored_targets": 0,
                                "brier_mean_difference_smoothed_minus_null": None,
                                "brier_mean_difference_decimal": None,
                                "log_loss_mean_difference_smoothed_minus_null": None,
                                "reading": "no scored target in this scope"})
    label_states: dict[str, int] = {}
    for lab in labels:
        label_states[lab["label_state"]] = label_states.get(lab["label_state"], 0) + 1
    targets_by_season: dict[str, int] = {}
    for lab in labels:
        targets_by_season[str(lab["season"])] = targets_by_season.get(str(lab["season"]), 0) + 1
    return {"record_type": "summary", "contract_id": CONTRACT_ID, "models": list(MODEL_IDS),
            "population": {"targets": len(labels), "feature_views": len(features), "estimates": len(estimates),
                           "labels": len(labels), "scores": len(scores), "targets_by_season": targets_by_season,
                           "label_states": label_states,
                           "team_cold_start_views": sum(1 for f in features if f["team"]["cold_start"]),
                           "opponent_cold_start_views": sum(1 for f in features if f["opponent"]["cold_start"])},
            "rows": rows, "comparisons": comparisons, **RECORD_LABELS}


# --------------------------------------------------------------------------------------------- the whole derivation

def derive(inputs: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    built = derive_features(inputs, anchors)
    targets, features = built["targets"], built["features"]
    feature_lines = [canonical_line(r) for r in features]
    estimates = derive_estimates(features, feature_lines)          # before any label is read
    estimate_lines = [canonical_line(r) for r in estimates]
    labels = derive_labels(inputs, targets, built["observed"])
    label_lines = [canonical_line(r) for r in labels]
    scores = derive_scores(estimates, labels, estimate_lines, label_lines)
    score_lines = [canonical_line(r) for r in scores]
    summary = derive_summary(features, estimates, labels, scores)
    # every derived number is an int or an exact rational and every log loss is text, so only the summary is scanned
    if contains_float(summary):
        _refuse("BENCHMARK_FLOAT_VALUE", "the derived summary carries a binary float")
    return {"targets": targets, "features": features, "estimates": estimates, "labels": labels, "scores": scores,
            "summary": summary, "lines": {"features": feature_lines, "estimates": estimate_lines,
                                          "labels": label_lines, "scores": score_lines}}


RECORD_TABLES = ("features", "estimates", "labels", "scores")


def record_lines(derived: dict[str, Any]) -> dict[str, list[str]]:
    """The canonical record lines of each record table, in payload order (target order, then view/model/orientation)."""
    if "lines" in derived:
        return derived["lines"]
    return {table: [canonical_line(r) for r in derived[table]] for table in RECORD_TABLES}


def target_chunk(derived: dict[str, Any], keys: Iterable[str]) -> bytes:
    """The checkpoint unit: every record line of the given targets, table by table (deterministic)."""
    wanted = set(keys)
    lines = []
    for table in RECORD_TABLES:
        lines += [f"{table}\t{canonical_line(r)}" for r in derived[table] if r["contest_key"] in wanted]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _gzip(data: bytes) -> bytes:
    """Deterministic gzip (no file name, mtime 0, level 6) under the pinned zlib."""
    return gzip.compress(data, compresslevel=6, mtime=0)


def payloads(derived: dict[str, Any]) -> dict[str, bytes]:
    """The five immutable content payloads: one gzip JSONL file per record kind plus the summary document."""
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


def content_document(contract_id: str, contract_sha256: str, anchors: dict[str, Any],
                     payload_bytes: dict[str, bytes], counts: dict[str, int],
                     lines_sha256: dict[str, str]) -> dict[str, Any]:
    """The complete contract-defined content identity document."""
    return {"schema": CONTENT_SCHEMA, "stage": "benchmark-content", "population": POPULATION,
            "contract_id": contract_id, "contract_sha256": contract_sha256, "parent": history_binding(anchors),
            "models": {model_id: model_sha256(model_id) for model_id in MODEL_IDS},
            "numeric_contract_sha256": numeric_contract_sha256(), "payload_schema": PAYLOAD_SCHEMA,
            "outputs": {name: sha256_bytes(data) for name, data in sorted(payload_bytes.items())},
            "uncompressed_sha256": dict(sorted(lines_sha256.items())), "row_counts": dict(sorted(counts.items()))}


def database_document(contract_sha256: str, content_identity: str, database_sha256: str,
                      table_counts: dict[str, int]) -> dict[str, Any]:
    """The complete contract-defined database identity document: exactly these members."""
    return {"schema": DATABASE_SCHEMA, "stage": "benchmark-database", "population": POPULATION,
            "contract_sha256": contract_sha256, "content_identity": content_identity, "db_schema_version": DB_SCHEMA,
            "outputs": {DB_FILE: database_sha256}, "table_counts": dict(table_counts)}


def meta_values(document: dict[str, Any], content_identity: str, summary: dict[str, Any],
                anchors: dict[str, Any]) -> dict[str, str]:
    return {"schema_version": DB_SCHEMA, "contract_id": document["contract_id"],
            "contract_sha256": document["contract_sha256"], "content_identity": content_identity,
            "payload_sha256": canonical_line(document["outputs"]),
            "uncompressed_sha256": canonical_line(document["uncompressed_sha256"]),
            "row_counts": canonical_line(document["row_counts"]),
            "parent": canonical_line(history_binding(anchors)), "labels": canonical_line(LABELS),
            "split": canonical_line(SPLIT), "models": canonical_line(models_claim()),
            "numeric_contract": canonical_line(NUMERIC_CONTRACT), "scope": canonical_line(SCOPE),
            "summary": canonical_line(summary)}


#: The exact database schema (every sqlite_master entry carries its statement; no automatic index exists). Each
#: record table is stored as one zlib block per season (level 9, pinned zlib): the block's index columns name its
#: table, season, record count, first and last record key and the SHA-256 of its uncompressed JSONL lines.
DDL = (
    ("table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"),
    ("table", "blocks", "CREATE TABLE blocks (ord INTEGER PRIMARY KEY, record_table TEXT NOT NULL, "
                        "season INTEGER NOT NULL, records INTEGER NOT NULL, first_key TEXT, last_key TEXT, "
                        "lines_sha256 TEXT NOT NULL, block BLOB NOT NULL)"),
)
TABLES = ("meta", "blocks")
BLOCK_LAYOUT = tuple((table, season) for table in RECORD_TABLES for season in TARGET_SEASONS)


def record_key(table: str, record: dict[str, Any]) -> str:
    """The exact key of a record in its table."""
    if table == "features":
        return f"{record.get('contest_key')}|{record.get('view')}"
    if table == "estimates":
        return f"{record.get('contest_key')}|{record.get('model_id')}|{record.get('orientation')}"
    if table == "scores":
        return f"{record.get('contest_key')}|{record.get('model_id')}"
    return str(record.get("contest_key"))


def block_rows(derived: dict[str, Any]) -> list[tuple[Any, ...]]:
    """One row per (record table, season) in the fixed layout order; payload order within a block."""
    rows = []
    for ord_, (table, season) in enumerate(BLOCK_LAYOUT):
        records = [r for r in derived[table] if r["season"] == season]
        lines = "".join(canonical_line(r) + "\n" for r in records).encode("utf-8")
        rows.append((ord_, table, season, len(records), record_key(table, records[0]) if records else None,
                     record_key(table, records[-1]) if records else None, sha256_bytes(lines),
                     zlib.compress(lines, 9)))
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
    ("pit_eligibility", "BENCHMARK_PIT_CLAIM_INVALID"), ("forecast_cutoff", "BENCHMARK_PIT_CLAIM_INVALID"),
    ("known_at", "BENCHMARK_PIT_CLAIM_INVALID"), ("training_cutoff", "BENCHMARK_PIT_CLAIM_INVALID"),
    ("prior_rule", "BENCHMARK_PIT_CLAIM_INVALID"), ("evidence_label", "BENCHMARK_LABEL_CLAIM_INVALID"),
    ("protected_lane", "BENCHMARK_PROTECTED_CLAIM_INVALID"), ("partition", "BENCHMARK_SPLIT_CLAIM_INVALID"),
    ("model_id", "BENCHMARK_MODEL_MISMATCH"), ("model_sha256", "BENCHMARK_MODEL_MISMATCH"),
    ("orientation", "BENCHMARK_ORIENTATION_MISMATCH"), ("view", "BENCHMARK_ORIENTATION_MISMATCH"),
    ("team_key", "BENCHMARK_TEAM_MAPPING_MISMATCH"), ("opponent_key", "BENCHMARK_TEAM_MAPPING_MISMATCH"),
    ("team_name", "BENCHMARK_TEAM_MAPPING_MISMATCH"), ("opponent_name", "BENCHMARK_TEAM_MAPPING_MISMATCH"),
    ("team_org_id", "BENCHMARK_TEAM_MAPPING_MISMATCH"), ("opponent_org_id", "BENCHMARK_TEAM_MAPPING_MISMATCH"),
    ("a_key", "BENCHMARK_TEAM_MAPPING_MISMATCH"), ("b_key", "BENCHMARK_TEAM_MAPPING_MISMATCH"),
    ("a_team_name", "BENCHMARK_TEAM_MAPPING_MISMATCH"), ("b_team_name", "BENCHMARK_TEAM_MAPPING_MISMATCH"),
    ("label_state", "BENCHMARK_LABEL_MISMATCH"), ("y_a", "BENCHMARK_LABEL_MISMATCH"),
    ("a_result", "BENCHMARK_LABEL_MISMATCH"), ("a_points", "BENCHMARK_LABEL_MISMATCH"),
    ("b_points", "BENCHMARK_LABEL_MISMATCH"), ("unscored_reason", "BENCHMARK_LABEL_MISMATCH"),
    ("score_state", "BENCHMARK_LABEL_MISMATCH"), ("label_record_sha256", "BENCHMARK_LABEL_MISMATCH"),
    ("brier", "BENCHMARK_SCORE_MISMATCH"), ("brier_decimal", "BENCHMARK_SCORE_MISMATCH"),
    ("log_loss", "BENCHMARK_SCORE_MISMATCH"),
    ("probability", "BENCHMARK_ESTIMATE_MISMATCH"), ("probability_decimal", "BENCHMARK_ESTIMATE_MISMATCH"),
    ("opponent_probability", "BENCHMARK_ESTIMATE_MISMATCH"),
    ("opponent_probability_decimal", "BENCHMARK_ESTIMATE_MISMATCH"),
    ("team_strength_q", "BENCHMARK_ESTIMATE_MISMATCH"), ("opponent_strength_q", "BENCHMARK_ESTIMATE_MISMATCH"),
    ("game_grain_probability_a", "BENCHMARK_ESTIMATE_MISMATCH"), ("probability_a", "BENCHMARK_ESTIMATE_MISMATCH"),
    ("probability_a_decimal", "BENCHMARK_ESTIMATE_MISMATCH"), ("team_cold_start", "BENCHMARK_ESTIMATE_MISMATCH"),
    ("opponent_cold_start", "BENCHMARK_ESTIMATE_MISMATCH"), ("estimate_record_sha256", "BENCHMARK_ESTIMATE_MISMATCH"),
    ("team", "BENCHMARK_FEATURE_MISMATCH"), ("opponent", "BENCHMARK_FEATURE_MISMATCH"),
    ("source_history", "BENCHMARK_SOURCE_MISMATCH"), ("source_label", "BENCHMARK_SOURCE_MISMATCH"),
    ("feature_record_sha256", "BENCHMARK_SOURCE_MISMATCH"), ("game_feature_record_sha256", "BENCHMARK_SOURCE_MISMATCH"),
)


def _json_or_none(text: Any) -> Any:
    try:
        return json.loads(text) if isinstance(text, (str, bytes)) else None
    except ValueError:
        return None


def _parse_marking_floats(line: str) -> tuple[Any, bool]:
    """A JSON line and whether any number in it was written as a binary float (13.0 is not the integer 13)."""
    floats: list[str] = []

    def mark(text: str) -> float:
        floats.append(text)
        return float(text)
    try:
        return json.loads(line, parse_float=mark), bool(floats)
    except ValueError:
        return None, False


def manifest_path_for(database: Path) -> Path:
    """``<data>/canonical/<population>/sha256/<id>/<db>`` -> ``<data>/manifests/<population>/sha256/<id>/run_manifest.json``."""
    db = Path(os.path.abspath(database))
    population_root = db.parent.parent.parent
    return population_root.parent.parent / "manifests" / population_root.name / "sha256" / db.parent.name / \
        "run_manifest.json"


def _io_path(path: Path) -> Path:
    """A path every file API can open: the extended form beyond the classic Windows limit (never re-normalized)."""
    text = os.fspath(path)
    if os.name == "nt" and not text.startswith("\\\\?\\") and len(os.path.abspath(text)) >= 250:
        return Path("\\\\?\\" + os.path.abspath(text))
    return Path(text)


class RetrospectiveBenchmark:
    """A verified, read-only handle on one content-addressed retrospective benchmark database.

    Construction refuses (BenchmarkError with a stable code) unless the accepted history verifies and pins, the
    benchmark location, manifest identity, database bytes, schema and meta claims verify, and every record of every
    table, the summary, the content identity and the contract-defined database identity document equal what is
    re-derived from the accepted history and the frozen model definitions. Identity documents are compared as
    canonical bytes (an integral float count is another document) and the served identity is the digest of the
    rebuilt document. Each refusal is checked in a fixed order so that every forgery is refused for its own cause."""

    def __init__(self, database: Path, *, history_database: Path, manifest: Path | None = None,
                 expect_identity: str | None = None, anchors: dict[str, Any] | None = None) -> None:
        self.anchors = anchors if anchors is not None else ANCHORS
        a = self.anchors
        inputs = load_history(Path(history_database), a)
        self.binding = self._verify_location_and_manifest(database, manifest, expect_identity)
        document = self.binding["identity_document"]
        if document.get("contract_sha256") != a["contract_sha256"]:
            raise BenchmarkError("BENCHMARK_CONTRACT_MISMATCH",
                                 f"the benchmark names contract {document.get('contract_sha256')}, the reader binds "
                                 f"{a['contract_sha256']}")
        try:
            self.conn = readonly_sqlite.connect_readonly(database)
        except readonly_sqlite.DatabaseLocationError as exc:
            raise BenchmarkError(exc.code, exc.detail) from exc
        try:
            self._verify_database(inputs)
        except sqlite3.DatabaseError as exc:
            self.conn.close()
            raise BenchmarkError("BENCHMARK_SCHEMA_UNSUPPORTED", str(exc)) from exc
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
            raise BenchmarkError(exc.code, exc.detail) from exc
        db = Path(database)
        if not _io_path(db).is_file():
            raise BenchmarkError("BENCHMARK_DATABASE_MISSING", f"no benchmark database file at {db}")
        absolute = Path(os.path.abspath(db))
        if absolute.name != DB_FILE or absolute.parent.parent.name != "sha256" or \
                absolute.parent.parent.parent.name != POPULATION:
            raise BenchmarkError("BENCHMARK_LOCATION_INVALID",
                                 f"the benchmark must sit at <root>/{POPULATION}/sha256/<id>/{DB_FILE}")
        identity = absolute.parent.name
        if not IDENTITY_RE.match(identity):
            raise BenchmarkError("BENCHMARK_LOCATION_INVALID", f"directory name {identity!r} is not an identity")
        manifest_path = Path(manifest) if manifest is not None else manifest_path_for(db)
        if not _io_path(manifest_path).is_file():
            raise BenchmarkError("BENCHMARK_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
        try:
            document = json.loads(_io_path(manifest_path).read_text(encoding="utf-8"))
            identity_document = document["identity_document"]
            computed = sha256_bytes(canonical_json_bytes(identity_document))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise BenchmarkError("BENCHMARK_MANIFEST_MALFORMED", str(exc)) from exc
        if computed != identity or document.get("identity") != identity:
            raise BenchmarkError("BENCHMARK_IDENTITY_MISMATCH",
                                 f"manifest identity document hashes to {computed}, directory is {identity}")
        if not isinstance(identity_document, dict) or \
                (identity_document.get("stage"), identity_document.get("schema"),
                 identity_document.get("db_schema_version"), identity_document.get("population")) != \
                ("benchmark-database", DATABASE_SCHEMA, DB_SCHEMA, POPULATION):
            raise BenchmarkError("BENCHMARK_SCHEMA_UNSUPPORTED", "not a retrospective benchmark database manifest")
        outputs = identity_document.get("outputs")
        if outputs is not None and not isinstance(outputs, dict):
            raise BenchmarkError("BENCHMARK_IDENTITY_DOCUMENT_MISMATCH",
                                 "the manifest identity document's outputs member is not an object")
        expected_sha = (outputs or {}).get(DB_FILE)
        actual_sha = sha256_file(_io_path(db))
        if expected_sha != actual_sha:
            raise BenchmarkError("BENCHMARK_DATABASE_TAMPERED",
                                 f"benchmark bytes hash to {actual_sha}, manifest names {expected_sha}")
        if expect_identity is not None and expect_identity != identity:
            raise BenchmarkError("STALE_BENCHMARK_IDENTITY", f"expected {expect_identity}, found {identity}")
        return {"identity": identity, "sha256": actual_sha, "manifest": str(manifest_path),
                "identity_document": identity_document}

    # ---- schema, meta claims and the complete re-derivation
    def _verify_database(self, inputs: dict[str, Any]) -> None:
        a = self.anchors
        master = sorted((str(r[0]), str(r[1]), r[2]) for r in self.conn.execute(
            "SELECT type, name, sql FROM sqlite_master"))
        if master != sorted(DDL):
            raise BenchmarkError("BENCHMARK_SCHEMA_UNSUPPORTED", "the benchmark schema differs from the contract")
        meta_rows = [(str(r[0]), r[1]) for r in self.conn.execute("SELECT key, value FROM meta ORDER BY rowid")]
        meta = dict(meta_rows)
        if len(meta) != len(meta_rows):
            raise BenchmarkError("BENCHMARK_META_MISMATCH", "duplicate meta keys")
        if meta.get("schema_version") != DB_SCHEMA:
            raise BenchmarkError("BENCHMARK_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}")
        if meta.get("contract_sha256") != a["contract_sha256"] or meta.get("contract_id") != a["contract_id"]:
            raise BenchmarkError("BENCHMARK_CONTRACT_MISMATCH", "the benchmark meta names another contract")
        claims = {name: _json_or_none(meta.get(name)) for name in
                  ("parent", "labels", "split", "models", "numeric_contract", "scope")}
        if claims["parent"] != history_binding(a):
            raise BenchmarkError("BENCHMARK_PARENT_MISMATCH", "the benchmark was built for another history")
        if claims["labels"] != LABELS:
            labels = claims["labels"] if isinstance(claims["labels"], dict) else {}
            code = ("BENCHMARK_PIT_CLAIM_INVALID" if labels.get("pit_eligibility") != PIT_STATE or
                    labels.get("temporal_basis") != LABELS["temporal_basis"] else
                    "BENCHMARK_PROTECTED_CLAIM_INVALID" if labels.get("protected_lane") != LABELS["protected_lane"]
                    else "BENCHMARK_LABEL_CLAIM_INVALID")
            raise BenchmarkError(code, "the benchmark declares labels other than the contract's")
        if canonical_json_bytes(claims["split"]) != canonical_json_bytes(SPLIT):
            raise BenchmarkError("BENCHMARK_SPLIT_CLAIM_INVALID", "the benchmark declares another split")
        if canonical_json_bytes(claims["models"]) != canonical_json_bytes(models_claim()):
            raise BenchmarkError("BENCHMARK_MODEL_MISMATCH", "the benchmark declares other model definitions")
        if canonical_json_bytes(claims["numeric_contract"]) != canonical_json_bytes(NUMERIC_CONTRACT):
            raise BenchmarkError("BENCHMARK_NUMERIC_CONTRACT_MISMATCH", "the benchmark declares another numeric contract")
        if canonical_json_bytes(claims["scope"]) != canonical_json_bytes(SCOPE):
            raise BenchmarkError("BENCHMARK_SCOPE_CLAIM_INVALID", "the benchmark declares another scope")
        counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        # value equality here keeps a fractional, string or boolean count on this code; an integral float count is
        # equal by value and is refused last, by the canonical-bytes identity-document rule
        if counts != self.binding["identity_document"].get("table_counts"):
            raise BenchmarkError("BENCHMARK_COUNT_MISMATCH",
                                 f"table counts {counts} != {self.binding['identity_document'].get('table_counts')}")
        present = self._read_blocks(inputs["protected"])
        derived = derive(inputs, a)
        for table in RECORD_TABLES:
            self._compare(table, present[table], record_lines(derived)[table], derived[table])
        content_payloads = payloads(derived)
        document = content_document(a["contract_id"], a["contract_sha256"], a, content_payloads, row_counts(derived),
                                    uncompressed_sha256(derived))
        content_identity = sha256_bytes(canonical_json_bytes(document))
        summary = _json_or_none(meta.get("summary"))
        if canonical_json_bytes(summary) != canonical_json_bytes(derived["summary"]):
            raise BenchmarkError("BENCHMARK_SUMMARY_MISMATCH", "the benchmark summary differs from its records")
        if meta.get("content_identity") != content_identity or \
                self.binding["identity_document"].get("content_identity") != content_identity:
            raise BenchmarkError("BENCHMARK_CONTENT_IDENTITY_MISMATCH",
                                 f"the re-derived content identity is {content_identity}")
        expected_meta = meta_values(document, content_identity, derived["summary"], a)
        if meta != expected_meta:
            raise BenchmarkError("BENCHMARK_META_MISMATCH", "meta differs on " + str(sorted(
                k for k in set(meta) | set(expected_meta) if meta.get(k) != expected_meta.get(k))))
        identity_document = self.binding["identity_document"]
        expected_document = database_document(a["contract_sha256"], content_identity, self.binding["sha256"], counts)
        expected_bytes = canonical_json_bytes(expected_document)
        if canonical_json_bytes(identity_document) != expected_bytes:
            differing = sorted(k for k in set(identity_document) | set(expected_document)
                               if k not in identity_document or k not in expected_document
                               or canonical_json_bytes(identity_document[k]) !=
                               canonical_json_bytes(expected_document[k]))
            raise BenchmarkError("BENCHMARK_IDENTITY_DOCUMENT_MISMATCH",
                                 f"the manifest identity document is not the contract-defined database document "
                                 f"(differs on {differing})")
        database_identity = sha256_bytes(expected_bytes)
        if database_identity != self.binding["identity"]:
            raise BenchmarkError("BENCHMARK_IDENTITY_DOCUMENT_MISMATCH",
                                 f"the location names {self.binding['identity']}, the contract-defined document is "
                                 f"{database_identity}")
        self.database_identity = database_identity
        self.content_identity = content_identity
        self.meta = meta
        self.derived = derived
        self.history_identity = inputs["binding"]["database_identity"]
        self.names = team_name_index(derived["targets"])

    def _read_blocks(self, protected: dict[str, int]) -> dict[str, list[tuple[str, dict[str, Any], bool]]]:
        """Every block's index columns against its own content, then each record's season and protected membership,
        label leakage, count types and binary floats -- before any comparison with the re-derived records."""
        rows = [tuple(r) for r in self.conn.execute(
            "SELECT ord, record_table, season, records, first_key, last_key, lines_sha256, block FROM blocks ORDER BY ord")]
        present: dict[str, list[tuple[str, dict[str, Any], bool]]] = {table: [] for table in RECORD_TABLES}
        layout = []
        for ord_, table, season, records, first_key, last_key, lines_sha, blob in rows:
            if table not in RECORD_TABLES:
                raise BenchmarkError("BENCHMARK_SCHEMA_UNSUPPORTED", f"block {ord_} names table {table!r}")
            if not is_int(season) or season not in TARGET_SEASONS:
                raise BenchmarkError("BENCHMARK_PROTECTED_KEY", f"block {ord_} holds season {season!r} outside 2016-2023")
            try:
                data = zlib.decompress(blob)
                lines = data.decode("utf-8").split("\n")
            except (zlib.error, TypeError, UnicodeDecodeError) as exc:
                raise BenchmarkError("BENCHMARK_INDEX_MISMATCH", f"block {ord_} does not decompress: {exc}") from exc
            if lines[-1] != "":
                raise BenchmarkError("BENCHMARK_INDEX_MISMATCH", f"block {ord_} does not end with a newline")
            lines = lines[:-1]
            parsed = []
            for line in lines:
                record, has_float = _parse_marking_floats(line)
                if not isinstance(record, dict):
                    raise BenchmarkError("BENCHMARK_RECORD_MISMATCH", f"block {ord_} holds a non-object line")
                parsed.append((line, record, has_float))
            keys = [record_key(table, r) for _l, r, _f in parsed]
            if sha256_bytes(data) != lines_sha or records != len(parsed) or \
                    first_key != (keys[0] if keys else None) or last_key != (keys[-1] if keys else None):
                raise BenchmarkError("BENCHMARK_INDEX_MISMATCH", f"block {ord_} index columns differ from its content")
            for _line, record, _f in parsed:
                if record.get("contest_key") in protected:
                    raise BenchmarkError("BENCHMARK_PROTECTED_KEY",
                                         f"{table} names protected canonical contest {record.get('contest_key')}")
                if record.get("season") != season:
                    code = "BENCHMARK_PROTECTED_KEY" if record.get("season") not in TARGET_SEASONS else \
                        "BENCHMARK_INDEX_MISMATCH"
                    raise BenchmarkError(code, f"{table} record {record_key(table, record)} season "
                                               f"{record.get('season')!r} in the {season} block")
            layout.append((table, season))
            present[table] += parsed
        if layout != list(BLOCK_LAYOUT):
            raise BenchmarkError("BENCHMARK_INDEX_MISMATCH", "the blocks do not follow the contract layout")
        for table in ("features", "estimates"):
            for _line, record, _f in present[table]:
                leaked = sorted(f for f in LABEL_FIELDS if f in record)
                if leaked:
                    raise BenchmarkError("BENCHMARK_LABEL_LEAKAGE",
                                         f"{table} record {record_key(table, record)} carries label fields {leaked}")
        for _line, record, _f in present["features"]:
            for side in ("team", "opponent"):
                member = record.get(side)
                counts = [member.get(k) for k in ("games", "wins", "losses", "ties")] if isinstance(member, dict) \
                    else [None]
                if not all(is_int(v) and v >= 0 for v in counts) or counts[1] + counts[2] + counts[3] != counts[0]:
                    raise BenchmarkError("BENCHMARK_FEATURE_COUNT_INVALID",
                                         f"feature {record_key('features', record)} {side} counts are not "
                                         f"nonnegative integers with W + L + T = G")
        for table in RECORD_TABLES:
            for _line, record, has_float in present[table]:
                if has_float:
                    raise BenchmarkError("BENCHMARK_FLOAT_VALUE",
                                         f"{table} record {record_key(table, record)} carries a binary float")
        for _line, record, _f in present["scores"]:
            if record.get("orientation") != "A":
                raise BenchmarkError("BENCHMARK_MIRROR_DOUBLE_COUNT",
                                     f"score {record_key('scores', record)} is not the single A-oriented record")
        return present

    @staticmethod
    def _compare(table: str, present: list[tuple[str, dict[str, Any], bool]], expected: list[str],
                 wanted_records: list[dict[str, Any]]) -> None:
        label = TABLE_LABELS[table]
        keys = [record_key(table, r) for _l, r, _f in present]
        if len(keys) != len(set(keys)):
            raise BenchmarkError("BENCHMARK_DUPLICATE_ROW", f"{table} repeats a record key")
        wanted = [record_key(table, r) for r in wanted_records]
        missing = sorted(set(wanted) - set(keys))
        if missing:
            raise BenchmarkError(f"BENCHMARK_{label}_ROW_MISSING",
                                 f"{len(missing)} expected {table} records absent, e.g. {missing[:3]}")
        extra = sorted(set(keys) - set(wanted))
        if extra:
            raise BenchmarkError(f"BENCHMARK_{label}_ROW_EXTRA",
                                 f"{len(extra)} {table} records outside the accepted population, e.g. {extra[:3]}")
        if keys != wanted:
            raise BenchmarkError("BENCHMARK_ORDER_MISMATCH", f"{table} is not in the contract order")
        for (line, got, _f), want_line, want in zip(present, expected, wanted_records):
            if line == want_line:
                continue
            differing = {f for f in set(want) | set(got)
                         if f not in want or f not in got or canonical_json_bytes(got[f]) != canonical_json_bytes(want[f])}
            code = next((c for f, c in RECORD_FIELD_CODES if f in differing), "BENCHMARK_RECORD_MISMATCH")
            raise BenchmarkError(code, f"{table} {record_key(table, want)} differs on {sorted(differing)[:6]}")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "RetrospectiveBenchmark":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- serving
    def query(self, grain: str, *, season: int | None = None, team: str | None = None, contest: str | None = None,
              model: str | None = None, partition: str | None = None, limit: int | None = 50, offset: int = 0,
              all_rows: bool = False) -> dict[str, Any]:
        if grain not in GRAINS:
            raise BenchmarkError("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}")
        if offset < 0:
            raise BenchmarkError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise BenchmarkError("NEGATIVE_LIMIT", "limit must be zero or positive")
        filters: dict[str, Any] = {}
        if season is not None:
            if not is_int(season):
                raise BenchmarkError("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if team is not None:
            if grain == "summary":
                raise BenchmarkError("FILTER_NOT_APPLICABLE", "team does not apply to the summary grain")
            filters["team"] = str(team).strip()
        if contest is not None:
            if grain == "summary":
                raise BenchmarkError("FILTER_NOT_APPLICABLE", "contest does not apply to the summary grain")
            text = str(contest).strip()
            filters["contest"] = f"ncaa:{text}" if text.isdigit() and len(text) <= 12 else text
            if not CONTEST_KEY_RE.match(filters["contest"]):
                raise BenchmarkError("CONTEST_KEY_INVALID", f"contest must be a parent contest key, got {contest!r}")
        if model is not None:
            if grain == "feature":
                raise BenchmarkError("FILTER_NOT_APPLICABLE", "model does not apply to the feature grain")
            if model not in MODEL_IDS:
                raise BenchmarkError("MODEL_UNKNOWN", f"model must be one of {list(MODEL_IDS)}")
            filters["model"] = model
        if partition is not None:
            if partition not in PARTITION_IDS:
                raise BenchmarkError("PARTITION_UNKNOWN", f"partition must be one of {list(PARTITION_IDS)}")
            filters["partition"] = partition
        result: dict[str, Any] = {"benchmark_identity": self.database_identity,
                                  "content_identity": self.content_identity,
                                  "contract_sha256": self.anchors["contract_sha256"],
                                  "contract_id": self.anchors["contract_id"],
                                  "history_database_identity": self.history_identity, "grain": grain,
                                  "filters": filters, "offset": offset, "limit": None if all_rows else limit, **LABELS,
                                  "denominators": self.derived["summary"]["population"],
                                  "verification": {"targets_verified": len(self.derived["targets"]),
                                                   "feature_records_verified": len(self.derived["features"]),
                                                   "estimate_records_verified": len(self.derived["estimates"]),
                                                   "label_records_verified": len(self.derived["labels"]),
                                                   "score_records_verified": len(self.derived["scores"]),
                                                   "history_verified": True, "content_identity_rederived": True,
                                                   "database_document_rederived": True}}
        if season is not None and season not in TARGET_SEASONS:
            state = ("PROTECTED_SEASON_NOT_IN_BENCHMARK" if season in PROTECTED_SEASONS else
                     "FORWARD_SEASON_NOT_IN_BENCHMARK" if season >= FORWARD_SEASONS_FROM else
                     "OUTSIDE_BENCHMARK_SCOPE")
            result.update(season_scope_state=state, total=0, returned=0, rows=[], next_offset=None,
                          note="season outside the retrospective 2016-2023 benchmark; no rows are fabricated")
            return result
        rows = [r for r in self._records(grain) if self._match(grain, r, filters)]
        total = len(rows)
        page = rows[offset:] if all_rows else rows[offset:offset + (limit or 0)]
        result.update(season_scope_state="RETROSPECTIVE_2016_2023", total=total, returned=len(page), rows=page,
                      next_offset=offset + len(page) if offset + len(page) < total else None)
        return result

    def _records(self, grain: str) -> list[dict[str, Any]]:
        if grain == "summary":
            return list(self.derived["summary"]["rows"]) + list(self.derived["summary"]["comparisons"])
        return self.derived[GRAINS[grain]]

    def _match(self, grain: str, record: dict[str, Any], filters: dict[str, Any]) -> bool:
        if grain == "summary":
            # A summary record describes one scope. A season selects its own season scope; a partition given with it
            # only has to contain that season under the frozen split (otherwise nothing is selected), and a partition
            # given alone selects its own partition scope.
            if "season" in filters:
                if "partition" in filters and filters["season"] not in PARTITION_SEASONS[filters["partition"]]:
                    return False
                if record.get("scope_id") != str(filters["season"]):
                    return False
            elif "partition" in filters and record.get("scope_id") != filters["partition"]:
                return False
            if "model" in filters and record.get("model_id") != filters["model"]:
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
            sides = (record["team_key"],) if grain in ("feature", "estimate") else (record["a_key"], record["b_key"])
            if not any(team_matches(filters["team"], record["season"], side, self.names) for side in sides):
                return False
        return True


GRAINS = {"feature": "features", "estimate": "estimates", "score": "scores", "summary": "summary"}
PARTITION_IDS = tuple(p["split_id"] for p in SPLIT["partitions"])
PARTITION_SEASONS = {p["split_id"]: frozenset(p["seasons"]) for p in SPLIT["partitions"]}
TABLE_LABELS = {"features": "FEATURE", "estimates": "ESTIMATE", "labels": "LABEL", "scores": "SCORE"}


def team_name_index(targets: list[dict[str, Any]]) -> dict[tuple[int, str], frozenset[str]]:
    """Each organization's own source names by season (casefolded), from the accepted target records of that season
    only: a name never resolves through another season or a global alias."""
    index: dict[tuple[int, str], set[str]] = {}
    for target in targets:
        for key, name in ((target["a_key"], target["a_team_name"]), (target["b_key"], target["b_team_name"])):
            if isinstance(name, str) and name:
                index.setdefault((target["season"], key), set()).add(name.casefold())
    return {k: frozenset(v) for k, v in index.items()}


def team_matches(value: str, season: int, team_key: str, names: dict[tuple[int, str], frozenset[str]]) -> bool:
    match = ORG_KEY_RE.match(value)
    if match:
        return team_key == f"org:{int(match.group(1))}"
    return value.casefold() in names.get((season, team_key), frozenset())
