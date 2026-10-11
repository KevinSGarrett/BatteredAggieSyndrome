r"""Explicit provider-record baseline preview over the accepted Cycle 51 capsule (BAT-724; TP52-A01 sections 1-4).

``bas-retrospective-baseline-query --prospective-preview <...\sha256\<identity>\preview.json>
--grain preview-feature|preview-estimate|preview-summary --cutoff 2026-10-12T00:00:00Z [--season 2026]
[--event espn:event:<id>] [--team espn:team:<id>] [--model <preview model>] [--orientation home|away] [--limit 50]``

One immutable, content-addressed JSON preview turns the accepted BAT-723 provider observation (25 provider events, 50
participant overall records observed 2026-10-11) into an illustrative fixed calculation: 50 source-bound participant
features, 25 game-grain rows and 100 oriented estimates (25 events x 2 fixed models x 2 sides), with complete support
and abstention accounting. It is ``PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST``: not an issued or frozen forecast, not
PIT admitted, not calibrated, no predictive-skill claim, no outcome, score or evaluation; the provider's reported counts
are claims, not reconstructed game histories, and opponent strength is not established.

Two fixed models, nothing fitted or chosen after results, no home advantage, margin, score or interval:

* ``PROVIDER_PREVIEW_NULL_HALF_V1``: p_home = p_away = 1/2 (needs only supported event and participant identity).
* ``PROVIDER_RECORD_SMOOTHED_ODDS_PREVIEW_V1``: q_X = (W_X + T_X/2 + 1)/(G_X + 2) from each side's own provider-reported
  overall/total record (G = W + L + T), p_home = q_home(1-q_away) / (q_home(1-q_away) + q_away(1-q_home)),
  p_away = 1 - p_home exactly. It reuses only the accepted C47 pure arithmetic
  (:func:`aggie_analytics.retrospective_baseline.benchmark.strength_q`, ``smoothed_probability`` and ``decimal_text``);
  no C47 model identity, label, score or database is read. A supported 0-0 record is a labelled cold start (q = 1/2).

Estimates are built at game grain in home orientation and derived into both orientations. A missing, ambiguous or
unsupported input never becomes a zero: the affected model abstains with the input and reason.

Authority is the accepted capsule (verified by the accepted reader
:func:`aggie_analytics.national_source_time.prospective.verify_capsule`, pinned to the identity, file hash and
observation contract the committed preview contract names) plus the committed preview contract
``configs/provider_record_baseline_preview_20261011_contract.json`` (:data:`CONTRACT_SHA256`). The preview directory
holds ``preview.json``, the contract bytes and a byte copy of the capsule directory, so a rehoused genuine bundle needs no
other directory. Before any row is served the reader re-derives the complete expected preview from the verified capsule
and contract, compares canonical serialized bytes (integer, float and boolean differ), checks the exact bundle
membership and recomputes the identity. ``--cutoff`` is required: before the retained request start the preview is
refused as unavailable, within the request interval as indeterminate; at or after its end the same retained snapshot is
served (a later cutoff never refreshes it, and nothing reads the current clock). ``--require-pit`` is always refused.

Imported only when ``--prospective-preview`` is named; every other invocation of the query is unchanged.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import random
import re
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics import readonly_sqlite
from aggie_analytics.national_source_time import prospective
from aggie_analytics.retrospective_baseline import benchmark as bm

SCHEMA = "BAS-PROVIDER-RECORD-BASELINE-PREVIEW-1"
IDENTITY_SCHEMA = "BAS-PROVIDER-RECORD-BASELINE-PREVIEW-IDENTITY-1"
POPULATION = "provider_record_baseline_preview_20261011"
CONTRACT_ID = "BAT-724-PROVIDER-RECORD-BASELINE-PREVIEW-20261011-V1"
#: SHA-256 of the committed contract ``configs/provider_record_baseline_preview_20261011_contract.json`` (the authority
#: anchor; a test requires it to equal the committed file).
CONTRACT_SHA256 = "330d8972c3763f7ac1d7c9b668aba4e20adddb2c31340aef60972988c3117092"
PREVIEW_FILE = "preview.json"
CONTRACT_MEMBER = "inputs/contract.json"
CAPSULE_ROOT = "capsule"
SEASON = 2026
GRAINS = ("preview-feature", "preview-estimate", "preview-summary")
GRAIN_KEY = {"preview-feature": "feature", "preview-estimate": "estimate", "preview-summary": "summary"}
APPLICABLE = {"preview-feature": ("season", "event", "team", "orientation"),
              "preview-estimate": ("season", "event", "team", "model", "orientation"),
              "preview-summary": ("season", "event", "team", "model")}
OUT_OF_SCOPE_STATE = "NOT_YET_AUDITED"
IN_SCOPE_STATE = "PROSPECTIVE_2026_RETAINED_OBSERVATION_PREVIEW"
ORIENTATIONS = ("home", "away")
SUPPORTED, UNSUPPORTED, ABSTAINED = "SUPPORTED", "UNSUPPORTED", "ABSTAINED"
UNAVAILABLE, INDETERMINATE, AVAILABLE = ("UNAVAILABLE_BEFORE_REQUEST_START", "INDETERMINATE_WITHIN_REQUEST_INTERVAL",
                                         "AVAILABLE_AT_OR_AFTER_REQUEST_END")

MODEL_NULL = "PROVIDER_PREVIEW_NULL_HALF_V1"
MODEL_SMOOTHED = "PROVIDER_RECORD_SMOOTHED_ODDS_PREVIEW_V1"
MODEL_IDS = (MODEL_NULL, MODEL_SMOOTHED)
#: The two frozen model definitions (equal to the committed contract's ``models``); each estimate names the SHA-256 of
#: its canonical definition.
MODELS: dict[str, dict[str, Any]] = {
    MODEL_NULL: {
        "model_id": MODEL_NULL, "version": 1, "family": "FIXED_CONSTANT", "formula": "p_home = p_away = 1/2",
        "inputs": [], "record_dependence": "NONE",
        "parameters": {"probability": {"numerator": 1, "denominator": 2}},
        "support_rule": "supported exactly when the event and both role participants have supported identity; no "
                        "record is read",
        "fitted": False, "home_advantage": None, "margin": None, "score": None, "interval": None,
        "calibration": "NOT_CALIBRATED", "role": "NULL_COMPARISON_PROVIDER_PREVIEW"},
    MODEL_SMOOTHED: {
        "model_id": MODEL_SMOOTHED, "version": 1, "family": "FIXED_SMOOTHED_PROVIDER_RECORD_ODDS_RATIO",
        "formula": "q_X = (W_X + T_X/2 + 1)/(G_X + 2) with G_X = W_X + L_X + T_X from side X's own provider-reported "
                   "overall/total record; p_home = q_home(1-q_away) / (q_home(1-q_away) + q_away(1-q_home)); "
                   "p_away = 1 - p_home",
        "inputs": ["wins", "losses", "ties", "games"],
        "input_semantics": "PROVIDER_REPORTED_OVERALL_TOTAL_RECORD_COUNTS_NOT_RECONSTRUCTED_GAME_HISTORY",
        "record_dependence": "OWN_OVERALL_TOTAL_RECORD_OF_EACH_SIDE",
        "parameters": {"pseudo_wins": 1, "pseudo_games": 2, "tie_weight": {"numerator": 1, "denominator": 2}},
        "cold_start": "a supported 0-0 record (G = 0) gives q = 1/2, labelled cold_start; the estimate is kept",
        "support_rule": "supported exactly when the null model is supported, both role participants' records are "
                        "supported and the event is pre-game at observation (state 'pre', not completed)",
        "arithmetic": {"source": "aggie_analytics.retrospective_baseline.benchmark",
                       "functions": ["strength_q", "smoothed_probability", "decimal_text"],
                       "contract_id": "BAT-719-NATIONAL-RETROSPECTIVE-BASELINE-2016-2023-V1.0",
                       "contract_sha256": "32a2ffb6c55d5fda37e06a75847ab3c21345205524ca5a7f60a2ef99b8142ee4",
                       "reuse": "the accepted C47 pure arithmetic only; no C47 model identity, label, score or "
                                "database"},
        "fitted": False, "home_advantage": None, "margin": None, "score": None, "interval": None,
        "calibration": "NOT_CALIBRATED", "role": "FIXED_PROVIDER_RECORD_COMPARISON"},
}

#: The frozen numeric contract (equal to the committed contract's ``numeric_contract``).
NUMERIC_CONTRACT = {
    "integers": "JSON integers only; a boolean or an integral float is not an integer; no binary float appears in "
                "preview.json, the identity document or a served row",
    "rationals": "{numerator, denominator} reduced JSON integers with denominator > 0 (exact fractions)",
    "decimal_display": "probability_decimal and opponent_probability_decimal: the exact rational rounded half-even "
                       "to 12 decimal places by the accepted C47 integer implementation (decimal_text)",
    "probability": "exact rational; 0 < p < 1 for the smoothed model; p_home + p_away = 1 exactly; the away "
                   "orientation is derived from the game-grain home value",
    "canonical_json": "json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) "
                      "as UTF-8; preview.json is these bytes plus one LF",
}
DISPLAY_PLACES = 12

#: Labels carried by the document and by every served row (equal to the committed contract's ``labels``).
LABELS = {
    "preview_status": "PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST",
    "pit_admission": "PIT_NOT_ADMITTED",
    "predictive_skill": "PREDICTIVE_SKILL_NOT_ESTABLISHED",
    "calibration": "NOT_CALIBRATED",
    "source_authority": "PROVIDER_CLAIM_ESPN_SCOREBOARD_NOT_OFFICIAL_NCAA_NOT_CORROBORATED",
    "national_coverage": "UNKNOWN_RETAINED_SINGLE_RESPONSE_NOT_NATIONAL_NOT_REPRESENTATIVE",
    "record_semantics": "PROVIDER_REPORTED_OVERALL_RECORD_COUNTS_NOT_RECONSTRUCTED_HISTORY_OPPONENT_STRENGTH_UNKNOWN",
    "forecast_issuance": "NONE_NOT_AN_ISSUED_OR_FROZEN_FORECAST",
    "evaluation": "NOT_SCORED_NO_OUTCOME_NOT_A_PROTECTED_EVALUATION",
    "home_away": "PROVIDER_HOMEAWAY_DESIGNATION_NOT_VENUE_NO_HOME_ADVANTAGE_APPLIED",
    "use": "ILLUSTRATIVE_FIXED_CALCULATION_NOT_A_BETTING_RECOMMENDATION",
    "temporal_basis": "RETAINED_OBSERVATION_INTERVAL_ONLY_A_LATER_CUTOFF_NEVER_REFRESHES",
}
#: Labels carried by every individual record.
RECORD_LABELS = {"preview_label": LABELS["preview_status"], "pit_admission": LABELS["pit_admission"]}

#: Capsule participant reasons that concern the record (every other participant reason concerns identity).
RECORD_REASONS = frozenset({"RECORD_OVERALL_TOTAL_MISSING", "RECORD_OVERALL_TOTAL_MULTIPLE", "RECORD_SUMMARY_MISSING",
                            "RECORD_SUMMARY_MALFORMED"})
TIES_RULES = frozenset({"TWO_INTEGER_FORM_TIES_ZERO_BY_RULE", "THREE_INTEGER_FORM_TIES_STATED"})
#: Abstention reason codes (the frozen vocabulary; ``detail`` carries the capsule reason or observed value).
REASONS = {
    "EVENT_UNSUPPORTED_IN_CAPSULE": "the capsule event is unsupported (detail: its capsule reason); both models abstain",
    "EVENT_SEASON_NOT_IN_SCOPE": "the event's season is not 2026 (detail: the season); both models abstain",
    "ROLE_UNRESOLVED": "the event names no participant for this side; both models abstain",
    "ROLE_PARTICIPANT_NOT_BOUND": "not exactly one participant record matches the event's role block (detail: the "
                                  "number found); both models abstain",
    "PARTICIPANT_IDENTITY_UNSUPPORTED": "the role participant has an identity reason in the capsule (detail); both "
                                        "models abstain",
    "RECORD_UNSUPPORTED": "the role participant's own overall/total record is unsupported (detail: the capsule "
                          "reason); the smoothed model abstains",
    "RECORD_COUNTS_INVALID": "a supported record's W/L/T are not non-negative JSON integers with a known ties rule; "
                             "the smoothed model abstains",
    "EVENT_NOT_PRE_GAME_AT_OBSERVATION": "the event or competition status was not 'pre' and not completed at "
                                         "observation, so the record may already contain the target game (detail: "
                                         "state:completed); the smoothed model abstains",
}

FEATURE_FIELDS = {
    "FEATURE_IDENTITY": ("record_type", "event_key", "season", "side", "team_key", "source_competitor_id",
                         "source_team_id", "source_name", "participant_pointer", "event_role_bound"),
    "FEATURE_RECORD": ("record_pointer", "candidate_record_pointers", "record_summary", "ties_rule", "wins", "losses",
                       "ties", "games", "cold_start"),
    "FEATURE_SUPPORT": ("support_state", "unsupported_reasons"),
    "FEATURE_PROVENANCE": ("capsule_identity", "source_body_sha256", "observation_interval"),
    "FEATURE_LABELS": ("preview_label", "pit_admission"),
}
GAME_FIELDS = {
    "GAME_IDENTITY": ("record_type", "event_key", "season", "scheduled_utc", "event_state", "home_team_key",
                      "away_team_key", "home_participant_pointer", "away_participant_pointer"),
    "GAME_MODELS": ("models",),
    "GAME_LINEAGE": ("home_feature_sha256", "away_feature_sha256"),
    "GAME_LABELS": ("preview_label", "pit_admission"),
}
ESTIMATE_FIELDS = {
    "ESTIMATE_IDENTITY": ("record_type", "event_key", "season", "model_id", "model_sha256", "orientation",
                          "team_key", "opponent_team_key"),
    "ESTIMATE_VALUE": ("probability", "probability_decimal", "opponent_probability", "opponent_probability_decimal",
                       "game_home_probability", "team_strength_q", "opponent_strength_q", "team_cold_start",
                       "opponent_cold_start"),
    "ESTIMATE_SUPPORT": ("support_state", "abstention_reasons"),
    "ESTIMATE_LINEAGE": ("record_dependence", "team_feature_sha256", "opponent_feature_sha256"),
    "ESTIMATE_LABELS": ("preview_label", "pit_admission"),
}
SUMMARY_FIELDS = ("record_type", "model_id", "model_sha256", "distinct_events", "features", "supported_features",
                  "unsupported_features", "cold_start_features", "estimates", "estimates_per_game",
                  "supported_estimates", "abstained_estimates", "supported_games", "abstained_games",
                  "abstention_reasons", "preview_label", "pit_admission")
TOP_LEVEL = ("schema", "population", "contract", "input", "models", "numeric_contract", "labels", "bundle", "features",
             "games", "estimates", "summary", "counts")
#: Comparison families in refusal order (the first differing family names the refusal code).
FAMILIES = ("SCHEMA", "CONTRACT", "INPUT", "MODELS", "NUMERIC_CONTRACT", "LABELS", "BUNDLE", "FEATURE_MEMBERSHIP",
            *FEATURE_FIELDS, "GAME_MEMBERSHIP", *GAME_FIELDS, "ESTIMATE_MEMBERSHIP", *ESTIMATE_FIELDS, "SUMMARY",
            "COUNTS", "CANONICAL_FORM")

IDENTITY_RE = re.compile(r"^[0-9a-f]{64}\Z")
EVENT_KEY_RE = re.compile(r"^espn:event:[0-9]{1,15}\Z")
TEAM_KEY_RE = re.compile(r"^espn:team:[0-9]{1,15}\Z")
#: The strict preview cutoff grammar (whole-string match; the shared historical parser is not changed).
CUTOFF_RE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]{1,6})?"
                       r"(Z|[+-][0-9]{2}:[0-9]{2})")
NAIVE_OR_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}([T ][0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?)?")
UTC = _dt.timezone.utc


class PreviewError(ValueError):
    """A refused preview build or query; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --------------------------------------------------------------------------------------------- canonical values

def canonical_bytes(value: object) -> bytes:
    """The frozen canonical serialization (sorted keys, compact separators, UTF-8, no ASCII escaping, no NaN)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def preview_file_bytes(document: dict[str, Any]) -> bytes:
    return canonical_bytes(document) + b"\n"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def model_sha256(model_id: str) -> str:
    return sha256_hex(canonical_bytes(MODELS[model_id]))


def _rational(value: Fraction) -> dict[str, int]:
    """Reduced numerator/denominator with a positive denominator (a Fraction is always normalized)."""
    return {"numerator": value.numerator, "denominator": value.denominator}


def _is_count(value: Any) -> bool:
    return type(value) is int and value >= 0


def strict_json(data: bytes, code: str) -> Any:
    """UTF-8 (no byte-order mark) JSON with no duplicate member and no NaN/Infinity, or a refusal under ``code``."""
    try:
        return prospective.strict_json(data, code)
    except prospective.ProspectiveEvidenceError as exc:
        raise PreviewError(code, str(exc)) from exc


def processing_order(count: int, order: str | None) -> list[int]:
    """The event processing order: natural, reversed or a seeded shuffle (the output never depends on it)."""
    indices = list(range(count))
    if order in (None, "natural"):
        return indices
    if order == "reversed":
        return indices[::-1]
    if isinstance(order, str) and order.startswith("shuffled:"):
        random.Random(order).shuffle(indices)
        return indices
    raise PreviewError("PROCESSING_ORDER_INVALID", f"unknown processing order {order!r}")


def _hash_chunks(data: bytes, chunk_size: int) -> str:
    digest = hashlib.sha256()
    for start in range(0, len(data), max(1, chunk_size)):
        digest.update(data[start:start + max(1, chunk_size)])
    return digest.hexdigest()


# --------------------------------------------------------------------------------------------- derivation

def _reason(source: str, team_key: str | None, code: str, detail: str | None = None) -> dict[str, Any]:
    return {"input": source, "team_key": team_key, "reason": code, "detail": detail}


def _reason_order(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (row["input"], row["team_key"] or "", row["reason"], row["detail"] or "")


def reason_key(row: dict[str, Any]) -> str:
    return row["reason"] + (f":{row['detail']}" if row["detail"] else "")


def _side_rank(side: Any) -> int:
    return ORIENTATIONS.index(side) if side in ORIENTATIONS else len(ORIENTATIONS)


def derive_feature(participant: dict[str, Any], event: dict[str, Any], capsule_identity: str, body_sha256: str,
                   interval: list[str]) -> dict[str, Any]:
    """One participant feature from the participant's own overall/total record only (TP52 section 3)."""
    record = participant.get("overall_record") or {}
    reasons = list(participant.get("unsupported_reasons") or [])
    counts_ok = all(_is_count(record.get(k)) for k in ("wins", "losses", "ties")) and \
        record.get("ties_rule") in TIES_RULES and record.get("name") == "overall" and record.get("type") == "total"
    if participant.get("support_state") == SUPPORTED and not reasons and not counts_ok:
        reasons.append("RECORD_COUNTS_INVALID")
    supported = participant.get("support_state") == SUPPORTED and not reasons
    wins = record.get("wins") if supported else None
    losses = record.get("losses") if supported else None
    ties = record.get("ties") if supported else None
    games = wins + losses + ties if supported else None
    side = participant.get("side")
    role = event.get(side) if side in ORIENTATIONS else None
    bound = isinstance(role, dict) and role.get("team_key") == participant.get("team_key") and \
        role.get("participant_pointer") == participant.get("participant_pointer")
    return {"record_type": "feature", "event_key": participant["event_key"], "season": event.get("season_year"),
            "side": side, "team_key": participant.get("team_key"),
            "source_competitor_id": participant.get("source_competitor_id"),
            "source_team_id": participant.get("source_team_id"), "source_name": participant.get("source_name"),
            "participant_pointer": participant.get("participant_pointer"), "event_role_bound": bool(bound),
            "record_pointer": participant.get("record_pointer"),
            "candidate_record_pointers": list(participant.get("candidate_record_pointers") or []),
            "record_summary": record.get("summary"), "ties_rule": record.get("ties_rule") if supported else None,
            "wins": wins, "losses": losses, "ties": ties, "games": games,
            "cold_start": (games == 0) if supported else None,
            "support_state": SUPPORTED if supported else UNSUPPORTED, "unsupported_reasons": sorted(set(reasons)),
            "capsule_identity": capsule_identity, "source_body_sha256": body_sha256,
            "observation_interval": list(interval), **RECORD_LABELS}


def _feature_order(f: dict[str, Any]) -> tuple[str, int, str, str]:
    return (f["event_key"], _side_rank(f["side"]), f["team_key"] or "", f["participant_pointer"] or "")


def _pre_game(event: dict[str, Any]) -> tuple[bool, str]:
    states = [event.get("event_status"), event.get("competition_status")]
    if not all(isinstance(s, dict) for s in states):
        return False, "STATUS_MISSING"
    ok = all(s.get("state") == "pre" and s.get("completed") is False for s in states)
    first = states[0]
    return ok, f"{first.get('state')}:{str(first.get('completed')).lower()}"


def derive_game(event: dict[str, Any], features: list[dict[str, Any]], feature_sha: dict[int, str],
                capsule_participants: dict[int, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The game-grain row of one event (both models in home orientation) and its four oriented estimates."""
    key = event["event_key"]
    common: list[dict[str, Any]] = []
    if event.get("support_state") != SUPPORTED:
        common += [_reason("event", None, "EVENT_UNSUPPORTED_IN_CAPSULE", r) for r in event.get("unsupported_reasons")
                   or ["UNSPECIFIED"]]
    if event.get("season_year") != SEASON:
        common.append(_reason("event", None, "EVENT_SEASON_NOT_IN_SCOPE", str(event.get("season_year"))))
    record_reasons: list[dict[str, Any]] = []
    bound: dict[str, dict[str, Any] | None] = {}
    for side in ORIENTATIONS:
        role = event.get(side)
        bound[side] = None
        if not isinstance(role, dict):
            if event.get("support_state") == SUPPORTED:
                common.append(_reason(side, None, "ROLE_UNRESOLVED"))
            continue
        matches = [f for f in features if f["side"] == side and f["team_key"] == role.get("team_key") and
                   f["participant_pointer"] == role.get("participant_pointer")]
        if len(matches) != 1:
            common.append(_reason(side, role.get("team_key"), "ROLE_PARTICIPANT_NOT_BOUND", str(len(matches))))
            continue
        feature = matches[0]
        source = capsule_participants[id(feature)]
        identity = sorted(r for r in source.get("unsupported_reasons") or [] if r not in RECORD_REASONS)
        common += [_reason(side, feature["team_key"], "PARTICIPANT_IDENTITY_UNSUPPORTED", r) for r in identity]
        for r in feature["unsupported_reasons"]:
            if r in RECORD_REASONS:
                record_reasons.append(_reason(side, feature["team_key"], "RECORD_UNSUPPORTED", r))
            elif r == "RECORD_COUNTS_INVALID":
                record_reasons.append(_reason(side, feature["team_key"], "RECORD_COUNTS_INVALID"))
        bound[side] = feature
    pre, state = _pre_game(event)
    smoothed_extra = list(record_reasons)
    if not pre:
        smoothed_extra.append(_reason("event", None, "EVENT_NOT_PRE_GAME_AT_OBSERVATION", state))
    home, away = bound["home"], bound["away"]
    home_key = (event.get("home") or {}).get("team_key") if isinstance(event.get("home"), dict) else None
    away_key = (event.get("away") or {}).get("team_key") if isinstance(event.get("away"), dict) else None
    models: list[dict[str, Any]] = []
    estimates: list[dict[str, Any]] = []
    for model_id in MODEL_IDS:
        reasons = sorted(common if model_id == MODEL_NULL else common + smoothed_extra, key=_reason_order)
        p_home = q_home = q_away = None
        if not reasons:
            if model_id == MODEL_NULL:
                p_home = Fraction(1, 2)
            else:
                q_home = bm.strength_q({"wins": home["wins"], "ties": home["ties"], "games": home["games"]})
                q_away = bm.strength_q({"wins": away["wins"], "ties": away["ties"], "games": away["games"]})
                p_home = bm.smoothed_probability(q_home, q_away)
                if bm.smoothed_probability(q_away, q_home) != 1 - p_home or not 0 < p_home < 1:
                    raise PreviewError("PREVIEW_ARITHMETIC_INCOHERENT", f"{key}: the two orientations disagree")
        state_value = SUPPORTED if p_home is not None else ABSTAINED
        models.append({"model_id": model_id, "model_sha256": model_sha256(model_id), "support_state": state_value,
                       "abstention_reasons": reasons,
                       "home_probability": _rational(p_home) if p_home is not None else None,
                       "away_probability": _rational(1 - p_home) if p_home is not None else None,
                       "home_strength_q": _rational(q_home) if q_home is not None else None,
                       "away_strength_q": _rational(q_away) if q_away is not None else None})
        uses_records = model_id == MODEL_SMOOTHED
        for orientation in ORIENTATIONS:
            mine, other = (home, away) if orientation == "home" else (away, home)
            q_self, q_other = (q_home, q_away) if orientation == "home" else (q_away, q_home)
            p = None if p_home is None else (p_home if orientation == "home" else 1 - p_home)
            estimates.append({
                "record_type": "estimate", "event_key": key, "season": event.get("season_year"),
                "model_id": model_id, "model_sha256": model_sha256(model_id), "orientation": orientation,
                "team_key": home_key if orientation == "home" else away_key,
                "opponent_team_key": away_key if orientation == "home" else home_key,
                "support_state": state_value, "abstention_reasons": reasons,
                "probability": _rational(p) if p is not None else None,
                "probability_decimal": bm.decimal_text(p) if p is not None else None,
                "opponent_probability": _rational(1 - p) if p is not None else None,
                "opponent_probability_decimal": bm.decimal_text(1 - p) if p is not None else None,
                "game_home_probability": _rational(p_home) if p_home is not None else None,
                "team_strength_q": _rational(q_self) if q_self is not None else None,
                "opponent_strength_q": _rational(q_other) if q_other is not None else None,
                "team_cold_start": mine["cold_start"] if uses_records and q_self is not None else None,
                "opponent_cold_start": other["cold_start"] if uses_records and q_other is not None else None,
                "record_dependence": MODELS[model_id]["record_dependence"],
                "team_feature_sha256": feature_sha[id(mine)] if uses_records and mine is not None else None,
                "opponent_feature_sha256": feature_sha[id(other)] if uses_records and other is not None else None,
                **RECORD_LABELS})
    status = event.get("event_status") if isinstance(event.get("event_status"), dict) else {}
    game = {"record_type": "game", "event_key": key, "season": event.get("season_year"),
            "scheduled_utc": event.get("scheduled_utc"),
            "event_state": {"name": status.get("name"), "state": status.get("state"),
                            "completed": status.get("completed")} if status else None,
            "home_team_key": home_key, "away_team_key": away_key,
            "home_participant_pointer": (event.get("home") or {}).get("participant_pointer")
            if isinstance(event.get("home"), dict) else None,
            "away_participant_pointer": (event.get("away") or {}).get("participant_pointer")
            if isinstance(event.get("away"), dict) else None,
            "models": models,
            "home_feature_sha256": feature_sha[id(home)] if home is not None else None,
            "away_feature_sha256": feature_sha[id(away)] if away is not None else None, **RECORD_LABELS}
    return game, estimates


def summary_rows(document: dict[str, Any], event_keys: Iterable[str],
                 model_ids: Iterable[str] = MODEL_IDS) -> list[dict[str, Any]]:
    """Game-grain summaries (one row per selected model) of the selected events: exact distinct events, the features
    and estimates of those games, supported/abstained games and estimates, and abstention reasons counted per game."""
    selected = set(event_keys)
    features = [f for f in document["features"] if f["event_key"] in selected]
    rows = []
    for model_id in model_ids:
        games = [(g, m) for g in document["games"] if g["event_key"] in selected for m in g["models"]
                 if m["model_id"] == model_id]
        estimates = [e for e in document["estimates"] if e["event_key"] in selected and e["model_id"] == model_id]
        reasons: dict[str, int] = {}
        for _game, model in games:
            for code in sorted({reason_key(r) for r in model["abstention_reasons"]}):
                reasons[code] = reasons.get(code, 0) + 1
        rows.append({"record_type": "summary", "model_id": model_id, "model_sha256": model_sha256(model_id),
                     "distinct_events": len({g["event_key"] for g, _m in games}), "features": len(features),
                     "supported_features": sum(f["support_state"] == SUPPORTED for f in features),
                     "unsupported_features": sum(f["support_state"] != SUPPORTED for f in features),
                     "cold_start_features": sum(f["cold_start"] is True for f in features),
                     "estimates": len(estimates), "estimates_per_game": len(ORIENTATIONS),
                     "supported_estimates": sum(e["support_state"] == SUPPORTED for e in estimates),
                     "abstained_estimates": sum(e["support_state"] != SUPPORTED for e in estimates),
                     "supported_games": sum(m["support_state"] == SUPPORTED for _g, m in games),
                     "abstained_games": sum(m["support_state"] != SUPPORTED for _g, m in games),
                     "abstention_reasons": dict(sorted(reasons.items())), **RECORD_LABELS})
    return rows


def _spec(contract: bytes, contract_sha256: str, chunk_size: int = 1 << 20) -> dict[str, Any]:
    if _hash_chunks(contract, chunk_size) != contract_sha256:
        raise PreviewError("CONTRACT_NOT_COMMITTED_AUTHORITY", f"the bundled contract hashes to {sha256_hex(contract)}, "
                                                               f"not the committed {contract_sha256}")
    spec = strict_json(contract, "CONTRACT_MALFORMED")
    if not isinstance(spec, dict) or spec.get("contract_id") != CONTRACT_ID or spec.get("population_id") != POPULATION:
        raise PreviewError("CONTRACT_MALFORMED", "the contract is not the provider-record baseline preview contract")
    for member, constant in (("models", MODELS), ("labels", LABELS), ("numeric_contract", NUMERIC_CONTRACT)):
        if canonical_bytes(spec.get(member)) != canonical_bytes(constant):
            raise PreviewError("CONTRACT_CODE_DISAGREEMENT", f"the contract's {member} differ from the frozen code")
    pins = spec.get("input")
    if not isinstance(pins, dict) or not all(isinstance(pins.get(k), str) for k in (
            "capsule_identity", "capsule_sha256", "capsule_contract_sha256")):
        raise PreviewError("CONTRACT_MALFORMED", "the contract does not pin the input capsule")
    return spec


def bundle_names(capsule_identity: str) -> list[str]:
    """Every member of a preview directory except preview.json (fixed relative names)."""
    base = f"{CAPSULE_ROOT}/{capsule_identity}"
    return sorted([CONTRACT_MEMBER, f"{base}/{prospective.CAPSULE_FILE}",
                   *(f"{base}/{rel}" for rel in prospective.BUNDLE.values())])


def derive(capsule_binding: dict[str, Any], contract: bytes, members: dict[str, bytes], *,
           contract_sha256: str = CONTRACT_SHA256, order: str | None = None,
           chunk_size: int = 1 << 20) -> dict[str, Any]:
    """The complete expected preview document from the verified capsule binding, the contract and the exact bundle
    member bytes (never a supplied summary)."""
    spec = _spec(contract, contract_sha256, chunk_size)
    pins = spec["input"]
    identity = capsule_binding["capsule_identity"]
    capsule = capsule_binding["document"]
    if (identity, capsule_binding["capsule_sha256"], capsule["contract"]["sha256"]) != (
            pins["capsule_identity"], pins["capsule_sha256"], pins["capsule_contract_sha256"]):
        raise PreviewError("INPUT_NOT_PINNED_CAPSULE", "the verified capsule is not the one the contract pins")
    names = bundle_names(identity)
    if sorted(members) != names:
        raise PreviewError("PREVIEW_BUNDLE_MEMBERSHIP_MISMATCH", f"bundle members {sorted(members)} != {names}")
    if members[CONTRACT_MEMBER] != contract:
        raise PreviewError("PREVIEW_BUNDLE_MEMBERSHIP_MISMATCH", "the bundled contract differs")
    observation = capsule["observation"]
    interval = [observation["request_start_utc"], observation["request_end_utc"]]
    body = capsule["source"]["body_sha256"]
    events = capsule["events"]
    participants = capsule["participants"]
    by_event: dict[str, list[dict[str, Any]]] = {}
    for p in participants:
        by_event.setdefault(p["event_key"], []).append(p)
    features: list[dict[str, Any]] = []
    games: list[dict[str, Any]] = []
    estimates: list[dict[str, Any]] = []
    for index in processing_order(len(events), order):
        event = events[index]
        own = [(derive_feature(p, event, identity, body, interval), p) for p in by_event.get(event["event_key"], [])]
        local = [f for f, _p in own]
        sha = {id(f): sha256_hex(canonical_bytes(f)) for f in local}
        source = {id(f): p for f, p in own}
        game, rows = derive_game(event, local, sha, source)
        features.extend(local)
        games.append(game)
        estimates.extend(rows)
    known = {e["event_key"] for e in events}
    if any(p["event_key"] not in known for p in participants):
        raise PreviewError("INPUT_PARTICIPANT_WITHOUT_EVENT", "a capsule participant names no capsule event")
    features.sort(key=_feature_order)
    games.sort(key=lambda g: g["event_key"])
    estimates.sort(key=lambda e: (e["event_key"], MODEL_IDS.index(e["model_id"]), ORIENTATIONS.index(e["orientation"])))
    document = {
        "schema": SCHEMA, "population": POPULATION, "contract": {"id": CONTRACT_ID, "sha256": contract_sha256},
        "input": {"capsule_population": prospective.POPULATION, "capsule_identity": identity,
                  "capsule_sha256": capsule_binding["capsule_sha256"],
                  "capsule_contract_id": capsule["contract"]["id"],
                  "capsule_contract_sha256": capsule["contract"]["sha256"],
                  "capsule_location": f"{CAPSULE_ROOT}/{identity}/{prospective.CAPSULE_FILE}",
                  "source_body_sha256": body, "receipt_sha256": capsule["source"]["receipt_sha256"],
                  "source_endpoint": capsule["source"]["endpoint"], "observation": observation,
                  "capsule_counts": capsule["counts"]},
        "models": {m: {"definition": MODELS[m], "sha256": model_sha256(m)} for m in MODEL_IDS},
        "numeric_contract": NUMERIC_CONTRACT, "labels": dict(LABELS),
        "bundle": {name: {"sha256": _hash_chunks(members[name], chunk_size), "bytes": len(members[name])}
                   for name in names},
        "features": features, "games": games, "estimates": estimates}
    document["summary"] = summary_rows(document, known)
    document["counts"] = {
        "events": len(events), "games": len(games), "features": len(features),
        "supported_features": sum(f["support_state"] == SUPPORTED for f in features),
        "unsupported_features": sum(f["support_state"] != SUPPORTED for f in features),
        "cold_start_features": sum(f["cold_start"] is True for f in features),
        "estimates": len(estimates), "supported_estimates": sum(e["support_state"] == SUPPORTED for e in estimates),
        "abstained_estimates": sum(e["support_state"] != SUPPORTED for e in estimates)}
    return document


def identity_document(document: dict[str, Any]) -> dict[str, Any]:
    """The identity document: the preview file hash, the bundle member hashes and the contract (no other member)."""
    return {"schema": IDENTITY_SCHEMA, "population": POPULATION, "contract_id": CONTRACT_ID,
            "contract_sha256": document["contract"]["sha256"], "preview_file": PREVIEW_FILE,
            "preview_sha256": sha256_hex(preview_file_bytes(document)), "bundle": document["bundle"]}


def preview_identity(document: dict[str, Any]) -> str:
    return sha256_hex(canonical_bytes(identity_document(document)))


# --------------------------------------------------------------------------------------------- comparison

def first_difference(expected: dict[str, Any], actual: Any) -> tuple[str, str] | None:
    """The first governed difference between the re-derived document and a supplied preview, by family order; every
    governed value is compared by its canonical serialized bytes (so 25, 25.0 and true differ)."""
    def same(a: Any, b: Any) -> bool:
        try:
            return canonical_bytes(a) == canonical_bytes(b)
        except (TypeError, ValueError):
            return False
    if not isinstance(actual, dict) or set(actual) != set(TOP_LEVEL):
        extra = sorted(set(actual) - set(TOP_LEVEL)) if isinstance(actual, dict) else ["<not an object>"]
        missing = sorted(set(TOP_LEVEL) - set(actual)) if isinstance(actual, dict) else []
        return "SCHEMA", f"top-level members differ (extra {extra}, missing {missing})"
    if not same(expected["schema"], actual["schema"]) or not same(expected["population"], actual["population"]):
        return "SCHEMA", "schema or population differs"
    for family, member in (("CONTRACT", "contract"), ("INPUT", "input"), ("MODELS", "models"),
                           ("NUMERIC_CONTRACT", "numeric_contract"), ("LABELS", "labels"), ("BUNDLE", "bundle")):
        if not same(expected[member], actual[member]):
            return family, f"{member} differs"
    for name, key, fields, membership in (
            ("FEATURE", "features", FEATURE_FIELDS,
             lambda r: [r.get("event_key"), r.get("side"), r.get("team_key"), r.get("participant_pointer")]),
            ("GAME", "games", GAME_FIELDS, lambda r: r.get("event_key")),
            ("ESTIMATE", "estimates", ESTIMATE_FIELDS,
             lambda r: [r.get("event_key"), r.get("model_id"), r.get("orientation")])):
        want, got = expected[key], actual[key]
        if not isinstance(got, list) or not all(isinstance(r, dict) for r in got):
            return f"{name}_MEMBERSHIP", f"{key} is not a list of records"
        if not same([membership(r) for r in want], [membership(r) for r in got]):
            return f"{name}_MEMBERSHIP", f"{key} membership, multiplicity or order differs"
        allowed = {f for group in fields.values() for f in group}
        for index, (w, g) in enumerate(zip(want, got)):
            if set(g) != allowed:
                return f"{name}_IDENTITY", f"{key}[{index}] members differ"
            for family, names in fields.items():
                for field in names:
                    if not same(w[field], g[field]):
                        return family, f"{key}[{index}].{field} differs"
    if not same(expected["summary"], actual["summary"]):
        return "SUMMARY", "summary differs"
    if not same(expected["counts"], actual["counts"]):
        return "COUNTS", "counts differ"
    return None


# --------------------------------------------------------------------------------------------- reader

def literal_location(path: Path | str) -> str:
    try:
        return readonly_sqlite.literal_path(path)
    except readonly_sqlite.DatabaseLocationError as exc:
        code = {readonly_sqlite.LOCATION_UNSUPPORTED: "PREVIEW_LOCATION_UNSUPPORTED",
                readonly_sqlite.LOCATION_NOT_LITERAL: "PREVIEW_LOCATION_NOT_LITERAL"}.get(exc.code, exc.code)
        raise PreviewError(code, exc.detail) from exc


_DRIVE_PATH = re.compile(r"[A-Za-z]:\\")


def io_path(location: str) -> str:
    """The spelling every file API opens for a literal location: on Windows the extended-length form of an absolute
    drive path, so that the nested bundle members (about 100 characters below the preview directory) stay readable
    beyond the classic 260-character limit; an extended-length location is kept verbatim. Never re-normalized: the
    literal location has already been validated."""
    if os.name == "nt" and not location.startswith(readonly_sqlite.EXTENDED_PREFIX) and _DRIVE_PATH.match(location):
        return readonly_sqlite.EXTENDED_PREFIX + location
    return location


def _read(path: str, code: str) -> bytes:
    if not os.path.isfile(path):
        raise PreviewError(code, f"no file at {path}")
    with open(path, "rb") as handle:
        return handle.read()


def directory_files(directory: str) -> dict[str, bytes]:
    """Every regular file below ``directory`` by its '/'-separated relative name (links and junctions are not
    followed)."""
    out: dict[str, bytes] = {}
    for root, dirs, names in os.walk(directory):
        dirs[:] = sorted(d for d in dirs if not (os.path.islink(os.path.join(root, d)) or
                                                 os.path.isjunction(os.path.join(root, d))))
        for name in sorted(names):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, directory).replace(os.sep, "/")
            with open(full, "rb") as handle:
                out[rel] = handle.read()
    return out


def verify_input_capsule(path: str, spec: dict[str, Any]) -> dict[str, Any]:
    """The pinned capsule verified completely by the accepted BAT-723 reader (its refusals keep their codes)."""
    pins = spec["input"]
    try:
        binding = prospective.verify_capsule(path, contract_sha256=pins["capsule_contract_sha256"],
                                             expect_identity=pins["capsule_identity"])
    except prospective.ProspectiveEvidenceError as exc:
        raise PreviewError(f"INPUT_{exc.code}", str(exc)) from exc
    if binding["capsule_sha256"] != pins["capsule_sha256"]:
        raise PreviewError("INPUT_NOT_PINNED_CAPSULE", "the capsule file is not the pinned capsule bytes")
    return binding


def verify_preview(path: Path | str, *, contract_sha256: str = CONTRACT_SHA256,
                   expect_identity: str | None = None) -> dict[str, Any]:
    """Verify a preview directory completely and return its binding plus the re-derived (verified) document."""
    location = literal_location(path)
    if not os.path.isfile(io_path(location)):
        raise PreviewError("PREVIEW_MISSING", f"no preview file at {location}")
    directory, name = os.path.split(location)
    if name != PREVIEW_FILE or not IDENTITY_RE.match(os.path.basename(directory)):
        raise PreviewError("PREVIEW_LOCATION_INVALID", f"the preview must be <identity>/{PREVIEW_FILE} with a 64-hex "
                                                       "identity directory")
    io_directory = io_path(directory)
    contract = _read(os.path.join(io_directory, *CONTRACT_MEMBER.split("/")), "BUNDLE_MEMBER_MISSING")
    spec = _spec(contract, contract_sha256)
    capsule_path = os.path.join(io_directory, CAPSULE_ROOT, spec["input"]["capsule_identity"], prospective.CAPSULE_FILE)
    binding = verify_input_capsule(capsule_path, spec)
    files = directory_files(io_directory)
    got = files.pop(PREVIEW_FILE, None)
    if got is None:
        raise PreviewError("PREVIEW_MISSING", f"no preview file at {location}")
    names = bundle_names(spec["input"]["capsule_identity"])
    if sorted(files) != names:
        raise PreviewError("PREVIEW_BUNDLE_MEMBERSHIP_MISMATCH",
                           f"extra {sorted(set(files) - set(names))}, missing {sorted(set(names) - set(files))}")
    expected = derive(binding, contract, files, contract_sha256=contract_sha256)
    if got != preview_file_bytes(expected):
        supplied = strict_json(got, "PREVIEW_MALFORMED")
        diff = first_difference(expected, supplied)
        family, detail = diff if diff else ("CANONICAL_FORM", "the preview bytes are not the frozen canonical form")
        raise PreviewError(f"PREVIEW_{family}_MISMATCH", detail)
    identity = preview_identity(expected)
    if os.path.basename(directory) != identity:
        raise PreviewError("PREVIEW_IDENTITY_MISMATCH", f"the identity document hashes to {identity}, the directory "
                                                        f"is {os.path.basename(directory)}")
    if expect_identity is not None and expect_identity != identity:
        raise PreviewError("STALE_PREVIEW_IDENTITY", f"expected {expect_identity}, found {identity}")
    return {"preview_identity": identity, "preview_sha256": sha256_hex(got), "location": location,
            "identity_document": identity_document(expected), "document": expected,
            "capsule_identity": binding["capsule_identity"]}


def parse_cutoff(value: str | None) -> _dt.datetime:
    """The strict preview cutoff: an ISO-8601 instant with seconds and an explicit zone, matched as a whole string."""
    if value is None:
        raise PreviewError("CUTOFF_REQUIRED", "the preview grains need --cutoff <ISO-8601 instant with a zone>")
    text = str(value)
    match = CUTOFF_RE.fullmatch(text)
    if not match:
        if NAIVE_OR_DATE_RE.fullmatch(text):
            raise PreviewError("CUTOFF_TIMEZONE_REQUIRED", f"cutoff {text!r} has no explicit zone or seconds")
        raise PreviewError("CUTOFF_INVALID", f"cutoff {text!r} is not an ISO-8601 instant")
    year, month, day, hour, minute, second, fraction, zone = match.groups()
    try:
        if zone == "Z":
            tz = UTC
        else:
            hours, minutes = int(zone[1:3]), int(zone[4:6])
            if hours > 14 or minutes > 59:
                raise ValueError(zone)
            sign = 1 if zone[0] == "+" else -1
            tz = _dt.timezone(sign * _dt.timedelta(hours=hours, minutes=minutes))
        micro = int(fraction[1:].ljust(6, "0")) if fraction else 0
        return _dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), micro,
                            tzinfo=tz).astimezone(UTC)
    except ValueError as exc:
        raise PreviewError("CUTOFF_INVALID", f"cutoff {text!r} is not a valid instant") from exc


def _utc(text: str) -> _dt.datetime:
    return _dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)


def observation_at(cutoff: _dt.datetime, observation: dict[str, Any]) -> tuple[str, str]:
    start, end = _utc(observation["request_start_utc"]), _utc(observation["request_end_utc"])
    if cutoff < start:
        return UNAVAILABLE, "CUTOFF_BEFORE_RETAINED_REQUEST_START"
    if cutoff < end:
        return INDETERMINATE, "CUTOFF_WITHIN_RETAINED_REQUEST_INTERVAL"
    return AVAILABLE, "CUTOFF_AT_OR_AFTER_RETAINED_REQUEST_END"


def normalize_event(value: str) -> str:
    if not isinstance(value, str) or not EVENT_KEY_RE.match(value):
        raise PreviewError("EVENT_KEY_INVALID", f"event must be espn:event:<digits>, got {value!r}")
    return value


def normalize_team(value: str) -> str:
    if not isinstance(value, str) or not TEAM_KEY_RE.match(value):
        raise PreviewError("TEAM_KEY_INVALID", f"team must be espn:team:<digits>, got {value!r}")
    return value


def normalize_model(value: str) -> str:
    if value not in MODEL_IDS:
        raise PreviewError("PREVIEW_MODEL_UNKNOWN", f"model must be one of {list(MODEL_IDS)}, got {value!r}")
    return value


def normalize_orientation(value: str) -> str:
    if value not in ORIENTATIONS:
        raise PreviewError("ORIENTATION_INVALID", f"orientation must be one of {list(ORIENTATIONS)}, got {value!r}")
    return value


class ProviderRecordPreview:
    """A completely verified preview; rows come only from its re-derived document."""

    def __init__(self, path: Path | str, *, contract_sha256: str = CONTRACT_SHA256,
                 expect_identity: str | None = None) -> None:
        self.binding = verify_preview(path, contract_sha256=contract_sha256, expect_identity=expect_identity)
        self.document = self.binding["document"]

    def __enter__(self) -> "ProviderRecordPreview":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    @staticmethod
    def filters(grain: str, *, season: int | None = None, event: str | None = None, team: str | None = None,
                model: str | None = None, orientation: str | None = None) -> dict[str, Any]:
        """The validated, applicable filters of one query (refused before any file is read)."""
        if grain not in GRAINS:
            raise PreviewError("PREVIEW_GRAIN_REQUIRED", f"--prospective-preview serves only {list(GRAINS)}, not "
                                                         f"{grain!r}")
        given = {"season": season, "event": event, "team": team, "model": model, "orientation": orientation}
        stray = [f"--{k}" for k, v in given.items() if v is not None and k not in APPLICABLE[grain]]
        if stray:
            raise PreviewError("FILTER_NOT_APPLICABLE", f"{stray} do not apply to the {grain} grain")
        out: dict[str, Any] = {}
        if season is not None:
            if isinstance(season, bool) or not isinstance(season, int):
                raise PreviewError("SEASON_INVALID", f"season must be an integer, got {season!r}")
            out["season"] = season
        if event is not None:
            out["event"] = normalize_event(event)
        if team is not None:
            out["team"] = normalize_team(team)
        if model is not None:
            out["model"] = normalize_model(model)
        if orientation is not None:
            out["orientation"] = normalize_orientation(orientation)
        return out

    def _selected_events(self, filters: dict[str, Any]) -> list[str]:
        teams: dict[str, set[str]] = {}
        for f in self.document["features"]:
            teams.setdefault(f["event_key"], set()).add(f["team_key"])
        out = []
        for game in self.document["games"]:
            key = game["event_key"]
            if "season" in filters and game["season"] != filters["season"]:
                continue
            if "event" in filters and key != filters["event"]:
                continue
            if "team" in filters and filters["team"] not in (teams.get(key, set()) |
                                                             {game["home_team_key"], game["away_team_key"]}):
                continue
            out.append(key)
        return out

    def query(self, grain: str, *, cutoff: str | None = None, season: int | None = None, event: str | None = None,
              team: str | None = None, model: str | None = None, orientation: str | None = None,
              limit: int | None = 50, offset: int = 0, all_rows: bool = False) -> dict[str, Any]:
        filters = self.filters(grain, season=season, event=event, team=team, model=model, orientation=orientation)
        if offset < 0:
            raise PreviewError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise PreviewError("NEGATIVE_LIMIT", "limit must be zero or positive")
        when = parse_cutoff(cutoff)
        doc = self.document
        state, reason = observation_at(when, doc["input"]["observation"])
        if state == UNAVAILABLE:
            raise PreviewError("PREVIEW_UNAVAILABLE_BEFORE_OBSERVATION", f"the retained observation started at "
                               f"{doc['input']['observation']['request_start_utc']}; nothing was observed by "
                               f"{when.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}")
        if state == INDETERMINATE:
            raise PreviewError("PREVIEW_INDETERMINATE_WITHIN_OBSERVATION", "the cutoff falls inside the retained "
                                                                           "request interval")
        result: dict[str, Any] = {
            "preview_identity": self.binding["preview_identity"], "contract_id": CONTRACT_ID,
            "contract_sha256": doc["contract"]["sha256"], "population": POPULATION, "grain": grain,
            "filters": filters, "cutoff": {"literal": cutoff, "utc": when.strftime("%Y-%m-%dT%H:%M:%S.%fZ")},
            "observation": doc["input"]["observation"], "observation_at_cutoff": {"state": state, "reason": reason},
            "labels": doc["labels"], "models": {m: doc["models"][m]["sha256"] for m in MODEL_IDS},
            "input": {k: doc["input"][k] for k in ("capsule_identity", "capsule_sha256", "source_body_sha256",
                                                   "source_endpoint")},
            "offset": offset, "limit": None if all_rows else limit}
        if season is not None and season != SEASON:
            result.update(season_scope_state=OUT_OF_SCOPE_STATE, total=0, returned=0, rows=[], next_offset=None,
                          note="only the retained 2026 provider observation is previewed; no row is fabricated")
            return result
        if grain == "preview-summary":
            items = summary_rows(doc, self._selected_events(filters),
                                 [filters["model"]] if "model" in filters else MODEL_IDS)
        elif grain == "preview-feature":
            items = [f for f in doc["features"] if
                     filters.get("season", f["season"]) == f["season"] and
                     filters.get("event", f["event_key"]) == f["event_key"] and
                     filters.get("team", f["team_key"]) == f["team_key"] and
                     filters.get("orientation", f["side"]) == f["side"]]
        else:
            items = [e for e in doc["estimates"] if
                     filters.get("season", e["season"]) == e["season"] and
                     filters.get("event", e["event_key"]) == e["event_key"] and
                     filters.get("team", e["team_key"]) == e["team_key"] and
                     filters.get("model", e["model_id"]) == e["model_id"] and
                     filters.get("orientation", e["orientation"]) == e["orientation"]]
        total = len(items)
        stop = None if all_rows else offset + (limit or 0)
        key = GRAIN_KEY[grain]
        common = {"observation_at_cutoff": state, "labels": doc["labels"],
                  "observation_interval": [doc["input"]["observation"]["request_start_utc"],
                                           doc["input"]["observation"]["request_end_utc"]],
                  "capsule_identity": doc["input"]["capsule_identity"],
                  "preview_identity": self.binding["preview_identity"]}
        rows = [{key: item, **common} for item in items[offset:stop]]
        result.update(season_scope_state=IN_SCOPE_STATE, total=total, returned=len(rows), rows=rows,
                      next_offset=offset + len(rows) if offset + len(rows) < total else None)
        return result


# --------------------------------------------------------------------------------------------- build helpers

def read_chunked(path: Path | str, chunk_size: int) -> bytes:
    """The exact bytes of ``path`` read in ``chunk_size`` blocks (a chunking variant never changes the result)."""
    parts = []
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(max(1, chunk_size)), b""):
            parts.append(block)
    return b"".join(parts)


def build_preview(capsule: Path | str, contract: bytes, *, contract_sha256: str = CONTRACT_SHA256,
                  order: str | None = None, chunk_size: int = 1 << 20
                  ) -> tuple[str, dict[str, bytes], dict[str, Any], dict[str, Any]]:
    """The identity, the complete set of files of the preview directory, the identity document and the document."""
    spec = _spec(contract, contract_sha256, chunk_size)
    location = io_path(literal_location(capsule))
    binding = verify_input_capsule(location, spec)
    directory = os.path.dirname(location)
    identity = binding["capsule_identity"]
    members = {CONTRACT_MEMBER: contract}
    capsule_names = [prospective.CAPSULE_FILE, *prospective.BUNDLE.values()]
    for rel in capsule_names:
        members[f"{CAPSULE_ROOT}/{identity}/{rel}"] = read_chunked(os.path.join(directory, *rel.split("/")), chunk_size)
    document = derive(binding, contract, members, contract_sha256=contract_sha256, order=order, chunk_size=chunk_size)
    files = {PREVIEW_FILE: preview_file_bytes(document), **members}
    return preview_identity(document), files, identity_document(document), document


__all__ = ["ProviderRecordPreview", "PreviewError", "build_preview", "derive", "first_difference",
           "identity_document", "preview_identity", "summary_rows", "verify_preview", "CONTRACT_SHA256", "GRAINS",
           "MODEL_IDS", "MODELS"]
