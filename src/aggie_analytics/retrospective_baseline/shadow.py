r"""Explicit immutable UNTRUSTED_SHADOW provider-record prediction snapshot (BAT-725; TP53-A01 sections 1-3).

``bas-retrospective-baseline-query --prospective-shadow <...\sha256\<identity>\snapshot.json>
--grain shadow-prediction|shadow-summary --cutoff <instant with zone> [--season 2026] [--event espn:event:<id>]
[--team espn:team:<id>] [--model <model>] [--orientation home|away] [--limit 50] [--offset 0] [--all]``

One private, create-only, content-addressed snapshot freezes the accepted fixed provider-record calculations of the
accepted BAT-724 preview (25 provider events with provider-reported 2026-10-17 starts, 50 participant records and 100
oriented predictions from the two fixed models) as an UNTRUSTED_SHADOW prediction record, anchored by the actual
service-created time of a hash-only Jira comment on BAT-725. It is not a trusted operational forecast, not calibrated,
not PIT admitted, predictive skill is not established, inputs are provider claims and national coverage is unknown.

Two immutable stages avoid a circular timestamp identity. Stage one is the canonical prediction payload
(``payload.json``): every event, participant record and prediction re-derived from the verified preview (which the
accepted reader re-derives from the bundled accepted capsule and its retained raw response), with participant, role,
input and model identities, exact reduced fractions, 12-place decimals and the preview record each value freezes
(the preview keeps its PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST role as source provenance). Its exact SHA-256 is
posted in the hash-only C53-A01-M2 comment, whose body this module renders deterministically. Stage two is the
snapshot (``snapshot.json``) that binds the payload bytes, the exact raw Jira readback of that comment (the anchor
receipt, unedited: created equals updated), the per-event timing decision and every source/contract/model binding and
label; its directory is named by the SHA-256 of its identity document.

The anchor proves only that the payload bytes existed no later than the comment's service-created time. For each event
the basis is ``PRE_PROVIDER_REPORTED_START`` exactly when observation end <= anchor created < provider-reported start
and the event was pre-game at observation; any other key is retained with its ineligibility reasons, never dropped or
backdated, and never called an official kickoff.

Before any row is served the reader verifies the snapshot directory completely: the committed contract
(:data:`CONTRACT_SHA256`), the bundled preview through the accepted preview reader (pinned identity and contract), the
exact bundle membership, the payload re-derived and compared by canonical bytes (integer, float, boolean and string
identities differ; the first differing record family names the refusal), the anchor receipt (issue, comment id,
service time grammar, unedited, body equal to the rendered hash-only body), the snapshot document re-derived and
compared, the identity recomputed, and finally the actual anchor pinned by the packaged gate
(:data:`ANCHOR_PROFILE`), so that a self-consistent forged receipt never becomes profile authority. ``--cutoff`` is
required: before the anchor's service-created time the snapshot is refused; at or after it the same immutable snapshot
is served (also after a provider-reported start; nothing is refreshed, recomputed or written, and the current clock is
never read). ``--require-pit`` is always refused.

Imported only when ``--prospective-shadow`` is named; every other invocation of the query is unchanged.
"""
from __future__ import annotations

import datetime as _dt
import os
import random
import re
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics import readonly_sqlite
from aggie_analytics.national_source_time import prospective
from aggie_analytics.retrospective_baseline import benchmark as bm
from aggie_analytics.retrospective_baseline import preview as pv

SCHEMA = "BAS-PROVIDER-RECORD-SHADOW-SNAPSHOT-1"
PAYLOAD_SCHEMA = "BAS-PROVIDER-RECORD-SHADOW-PAYLOAD-1"
IDENTITY_SCHEMA = "BAS-PROVIDER-RECORD-SHADOW-SNAPSHOT-IDENTITY-1"
POPULATION = "provider_record_shadow_20261017"
CONTRACT_ID = "BAT-725-PROVIDER-RECORD-SHADOW-20261017-V1"
#: SHA-256 of the committed contract ``configs/provider_record_shadow_20261017_contract.json`` (the authority anchor;
#: a test requires it to equal the committed file).
CONTRACT_SHA256 = "2bbc6aa915169654b9dc7327c42f87306e0e0f137243b1852cc881cee0998d5c"
DESIGNATION = "UNTRUSTED_SHADOW"
SNAPSHOT_FILE = "snapshot.json"
PAYLOAD_FILE = "payload.json"
ANCHOR_MEMBER = "anchor/jira_comment.json"
CONTRACT_MEMBER = "inputs/contract.json"
PREVIEW_ROOT = "preview"
SEASON = 2026
GRAINS = ("shadow-prediction", "shadow-summary")
GRAIN_KEY = {"shadow-prediction": "prediction", "shadow-summary": "summary"}
APPLICABLE = {"shadow-prediction": ("season", "event", "team", "model", "orientation"),
              "shadow-summary": ("season", "event", "team", "model")}
OUT_OF_SCOPE_STATE = "NOT_YET_AUDITED"
IN_SCOPE_STATE = "PROSPECTIVE_2026_UNTRUSTED_SHADOW_SNAPSHOT"
ORIENTATIONS = pv.ORIENTATIONS
MODEL_IDS = pv.MODEL_IDS
SUPPORTED, UNSUPPORTED, ABSTAINED = pv.SUPPORTED, pv.UNSUPPORTED, pv.ABSTAINED
TIMING_BASIS = "PRE_PROVIDER_REPORTED_START"
ANCHORED = "ANCHORED_PRE_PROVIDER_REPORTED_START"
INELIGIBLE = "INELIGIBLE_NOT_PRE_PROVIDER_REPORTED_START"
UNAVAILABLE_STATE, AVAILABLE_STATE = "UNAVAILABLE_BEFORE_ANCHOR", "AVAILABLE_AT_OR_AFTER_ANCHOR"

#: Labels carried by the payload, the snapshot and every served response (equal to the committed contract's
#: ``labels``). The preview's own NOT_FORECAST label is kept as source provenance, not as this record's role.
LABELS = {
    "designation": "UNTRUSTED_SHADOW",
    "input_authority": "PROVIDER_CLAIM_INPUTS",
    "pit_admission": "PIT_NOT_ADMITTED",
    "calibration": "NOT_CALIBRATED",
    "predictive_skill": "PREDICTIVE_SKILL_NOT_ESTABLISHED",
    "national_coverage": "UNKNOWN",
    "record_role": "FROZEN_PRIVATE_SHADOW_PREDICTION_NOT_A_TRUSTED_OPERATIONAL_FORECAST",
    "source_preview_role": "SOURCE_PROVENANCE_PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST",
    "source_authority": "PROVIDER_CLAIM_ESPN_SCOREBOARD_NOT_OFFICIAL_NCAA_NOT_CORROBORATED",
    "timing_basis": "PRE_PROVIDER_REPORTED_START_NOT_OFFICIAL_KICKOFF_CONFIRMED",
    "evaluation": "NOT_SCORED_NO_OUTCOME_NOT_A_PROTECTED_EVALUATION",
    "publication": "PRIVATE_HASH_ONLY_ANCHOR_NO_PUBLIC_PREDICTION_VALUES",
    "home_away": "PROVIDER_HOMEAWAY_DESIGNATION_NOT_VENUE_NO_HOME_ADVANTAGE_APPLIED",
    "use": "NOT_A_BETTING_RECOMMENDATION_NOT_AN_OPERATIONAL_DEFAULT",
}
#: Labels carried by every individual payload record and served summary row (equal to the contract's
#: ``record_labels``).
RECORD_LABELS = {
    "designation": LABELS["designation"], "input_authority": LABELS["input_authority"],
    "pit_admission": LABELS["pit_admission"], "calibration": LABELS["calibration"],
    "predictive_skill": LABELS["predictive_skill"], "national_coverage": LABELS["national_coverage"],
    "source_preview_label": pv.LABELS["preview_status"],
}
#: The frozen numeric contract (equal to the committed contract's ``numeric_contract``).
NUMERIC_CONTRACT = {
    "integers": "JSON integers only; a boolean or an integral float is not an integer; no binary float appears in "
                "payload.json, snapshot.json, the identity document or a served row",
    "rationals": "{numerator, denominator} reduced JSON integers with denominator > 0 (exact fractions)",
    "decimal_display": "probability_decimal and opponent_probability_decimal: the exact rational rounded half-even "
                       "to 12 decimal places by the accepted C47 integer implementation, as the verified preview holds",
    "probability": "exact rational; 0 < p < 1 for the smoothed model; p_home + p_away = 1 exactly; probability + "
                   "opponent_probability = 1 exactly; the away orientation is derived from the game-grain home value",
    "identities": "event, team, comment and issue identities are JSON strings; an integer, float or boolean in their "
                  "place is a different value and is refused",
    "canonical_json": "json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) "
                      "as UTF-8; payload.json and snapshot.json are these bytes plus one LF",
}

EVENT_FIELDS = {
    "EVENT_IDENTITY": ("record_type", "event_key", "season", "provider_scheduled_utc", "event_state_at_observation",
                       "home_team_key", "away_team_key", "home_participant_pointer", "away_participant_pointer"),
    "EVENT_LINEAGE": ("home_feature_sha256", "away_feature_sha256", "preview_game_sha256"),
    "EVENT_LABELS": tuple(RECORD_LABELS),
}
PARTICIPANT_FIELDS = {
    "PARTICIPANT_IDENTITY": ("record_type", "event_key", "season", "side", "team_key", "source_competitor_id",
                             "source_team_id", "source_name", "participant_pointer", "event_role_bound"),
    "PARTICIPANT_RECORD": ("record_pointer", "candidate_record_pointers", "record_summary", "ties_rule", "wins",
                           "losses", "ties", "games", "cold_start"),
    "PARTICIPANT_SUPPORT": ("support_state", "unsupported_reasons"),
    "PARTICIPANT_LINEAGE": ("preview_feature_sha256",),
    "PARTICIPANT_LABELS": tuple(RECORD_LABELS),
}
PREDICTION_FIELDS = {
    "PREDICTION_IDENTITY": ("record_type", "event_key", "season", "model_id", "model_sha256", "orientation",
                            "team_key", "opponent_team_key", "provider_scheduled_utc"),
    "PREDICTION_VALUE": ("probability", "probability_decimal", "opponent_probability", "opponent_probability_decimal",
                         "game_home_probability", "team_strength_q", "opponent_strength_q", "team_cold_start",
                         "opponent_cold_start"),
    "PREDICTION_SUPPORT": ("support_state", "abstention_reasons"),
    "PREDICTION_LINEAGE": ("record_dependence", "team_feature_sha256", "opponent_feature_sha256",
                           "preview_estimate_sha256"),
    "PREDICTION_LABELS": tuple(RECORD_LABELS),
}
SUMMARY_FIELDS = ("record_type", "model_id", "model_sha256", "distinct_events", "participants",
                  "supported_participants", "unsupported_participants", "cold_start_participants", "predictions",
                  "predictions_per_game", "supported_predictions", "abstained_predictions", "supported_games",
                  "abstained_games", "abstention_reasons", *RECORD_LABELS)
#: A served summary adds the anchored/ineligible game counts of the snapshot's timing decisions.
SERVED_SUMMARY_TIMING_FIELDS = ("anchored_pre_provider_start_games", "ineligible_games")
PAYLOAD_TOP = ("schema", "population", "designation", "contract", "source", "models", "numeric_contract", "labels",
               "events", "participants", "predictions", "summary", "counts")
SNAPSHOT_TOP = ("schema", "population", "designation", "contract", "payload", "anchor", "timing", "labels", "counts",
                "bundle")
#: Comparison families in refusal order (the first differing family names the refusal code).
PAYLOAD_FAMILIES = ("SCHEMA", "DESIGNATION", "CONTRACT", "SOURCE", "MODELS", "NUMERIC_CONTRACT", "LABELS",
                    "EVENT_MEMBERSHIP", *EVENT_FIELDS, "PARTICIPANT_MEMBERSHIP", *PARTICIPANT_FIELDS,
                    "PREDICTION_MEMBERSHIP", *PREDICTION_FIELDS, "SUMMARY", "COUNTS", "CANONICAL_FORM")
SNAPSHOT_FAMILIES = ("SCHEMA", "DESIGNATION", "CONTRACT", "PAYLOAD", "ANCHOR", "TIMING", "LABELS", "COUNTS", "BUNDLE",
                     "CANONICAL_FORM")
#: Timing ineligibility reasons (the frozen vocabulary).
TIMING_REASONS = {
    "PROVIDER_START_MISSING": "the event has no valid provider-reported scheduled start",
    "EVENT_NOT_PRE_GAME_AT_OBSERVATION": "the event was not pre-game (state 'pre', not completed) at observation",
    "ANCHOR_BEFORE_OBSERVATION_END": "the anchor's service-created time precedes the retained observation end",
    "ANCHOR_AT_OR_AFTER_PROVIDER_REPORTED_START": "the anchor's service-created time is at or after the "
                                                 "provider-reported start",
}

#: The anchor as fixed by the committed contract (system, tenant, issue, marker and body heading).
ANCHOR_SPEC = {
    "system": "JIRA_CLOUD_REST_API_3",
    "tenant": "https://kevinsgarrett.atlassian.net",
    "issue_key": "BAT-725",
    "issue_id": "25892",
    "marker": "C53-A01-M2",
    "heading": "C53-A01-M2 — Cycle #53 — Attempt #1 — UNTRUSTED_SHADOW payload timestamp anchor (BAT-725)",
}
#: The actual anchor and snapshot pinned by the packaged final gate (``artifacts/data_lake/
#: provider_record_shadow_20261017_gate.json``); None until the real anchor exists and the gate is committed.
ANCHOR_PROFILE: dict[str, str] | None = None
PROFILE_FIELDS = ("snapshot_identity", "payload_sha256", "issue_key", "issue_id", "comment_id", "created", "updated",
                  "receipt_sha256", "body_text_sha256")

IDENTITY_RE = re.compile(r"^[0-9a-f]{64}\Z")
EVENT_KEY_RE = re.compile(r"^espn:event:[0-9]{1,15}\Z")
TEAM_KEY_RE = re.compile(r"^espn:team:[0-9]{1,15}\Z")
COMMENT_ID_RE = re.compile(r"^[0-9]{1,20}\Z")
#: The Jira service time grammar: milliseconds and a +hhmm/-hhmm offset (e.g. 2026-10-12T01:28:51.096-0500).
SERVICE_TIME_RE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})\.([0-9]{3})"
                             r"([+-])([0-9]{2})([0-9]{2})")
#: The strict cutoff grammar of this mode (whole-string match; the shared historical and preview parsers unchanged).
CUTOFF_RE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]{1,6})?"
                       r"(Z|[+-][0-9]{2}:[0-9]{2})")
NAIVE_OR_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}([T ][0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?)?")
UTC = _dt.timezone.utc
PINNED = object()


class ShadowError(ValueError):
    """A refused shadow build or query; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --------------------------------------------------------------------------------------------- canonical values

canonical_bytes = pv.canonical_bytes
sha256_hex = pv.sha256_hex


def file_bytes(document: dict[str, Any]) -> bytes:
    """payload.json and snapshot.json: the canonical bytes plus one LF."""
    return canonical_bytes(document) + b"\n"


def record_sha256(record: Any) -> str:
    return sha256_hex(canonical_bytes(record))


def strict_json(data: bytes, code: str) -> Any:
    try:
        return prospective.strict_json(data, code)
    except prospective.ProspectiveEvidenceError as exc:
        raise ShadowError(code, str(exc)) from exc


def iso_micro(moment: _dt.datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _fraction(value: Any) -> Fraction | None:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        return None
    n, d = value["numerator"], value["denominator"]
    if type(n) is not int or type(d) is not int or d <= 0:
        return None
    return Fraction(n, d)


def adf_text(node: Any) -> str:
    """The plain text of an Atlassian document: text nodes concatenated, a newline after each paragraph."""
    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("text") or "")
        return "".join(adf_text(c) for c in node.get("content") or []) + (
            "\n" if node.get("type") in {"paragraph", "heading", "listItem"} else "")
    if isinstance(node, list):
        return "".join(adf_text(c) for c in node)
    return ""


# --------------------------------------------------------------------------------------------- contract

def _models_document() -> dict[str, Any]:
    return {m: {"definition": pv.MODELS[m], "sha256": pv.model_sha256(m)} for m in MODEL_IDS}


def field_families() -> dict[str, Any]:
    """The record field families exactly as the committed contract states them."""
    return {"events": {k: list(v) for k, v in EVENT_FIELDS.items()},
            "participants": {k: list(v) for k, v in PARTICIPANT_FIELDS.items()},
            "predictions": {k: list(v) for k, v in PREDICTION_FIELDS.items()},
            "summary": list(SUMMARY_FIELDS), "served_summary_timing": list(SERVED_SUMMARY_TIMING_FIELDS)}


def _spec(contract: bytes, contract_sha256: str, chunk_size: int = 1 << 20) -> dict[str, Any]:
    if pv._hash_chunks(contract, chunk_size) != contract_sha256:
        raise ShadowError("CONTRACT_NOT_COMMITTED_AUTHORITY", f"the bundled contract hashes to {sha256_hex(contract)}, "
                                                              f"not the committed {contract_sha256}")
    spec = strict_json(contract, "CONTRACT_MALFORMED")
    if not isinstance(spec, dict) or spec.get("contract_id") != CONTRACT_ID or spec.get("population_id") != POPULATION:
        raise ShadowError("CONTRACT_MALFORMED", "the contract is not the provider-record shadow contract")
    for member, constant in (("models", _models_document()), ("labels", LABELS), ("record_labels", RECORD_LABELS),
                             ("numeric_contract", NUMERIC_CONTRACT), ("timing_reasons", TIMING_REASONS)):
        if canonical_bytes(spec.get(member)) != canonical_bytes(constant):
            raise ShadowError("CONTRACT_CODE_DISAGREEMENT", f"the contract's {member} differ from the frozen code")
    if canonical_bytes((spec.get("payload") or {}).get("fields")) != canonical_bytes(field_families()):
        raise ShadowError("CONTRACT_CODE_DISAGREEMENT", "the contract's payload field families differ from the code")
    anchor = spec.get("anchor")
    if not isinstance(anchor, dict) or any(anchor.get(k) != v for k, v in ANCHOR_SPEC.items()):
        raise ShadowError("CONTRACT_CODE_DISAGREEMENT", "the contract's anchor differs from the frozen code")
    pins = spec.get("input")
    if not isinstance(pins, dict) or not all(isinstance(pins.get(k), str) for k in (
            "preview_identity", "preview_sha256", "preview_contract_sha256", "capsule_identity", "capsule_sha256",
            "capsule_contract_sha256", "source_body_sha256", "receipt_sha256", "expected_cohort_sha256")) or \
            not all(type(pins.get(k)) is int for k in ("expected_events", "expected_participants",
                                                       "expected_predictions")):
        raise ShadowError("CONTRACT_MALFORMED", "the contract does not pin the shadow inputs")
    return spec


# --------------------------------------------------------------------------------------------- stage one: payload

def processing_order(count: int, order: str | None) -> list[int]:
    """The record processing order: natural, reversed or a seeded shuffle (the output never depends on it)."""
    indices = list(range(count))
    if order in (None, "natural"):
        return indices
    if order == "reversed":
        return indices[::-1]
    if isinstance(order, str) and order.startswith("shuffled:"):
        random.Random(order).shuffle(indices)
        return indices
    raise ShadowError("PROCESSING_ORDER_INVALID", f"unknown processing order {order!r}")


def _participant(feature: dict[str, Any]) -> dict[str, Any]:
    fields = [f for group in PARTICIPANT_FIELDS.values() for f in group if f not in RECORD_LABELS]
    out = {f: feature[f] for f in fields if f not in ("record_type", "preview_feature_sha256")}
    return {**out, "record_type": "participant", "preview_feature_sha256": record_sha256(feature), **RECORD_LABELS}


def _event(game: dict[str, Any]) -> dict[str, Any]:
    return {"record_type": "event", "event_key": game["event_key"], "season": game["season"],
            "provider_scheduled_utc": game["scheduled_utc"], "event_state_at_observation": game["event_state"],
            "home_team_key": game["home_team_key"], "away_team_key": game["away_team_key"],
            "home_participant_pointer": game["home_participant_pointer"],
            "away_participant_pointer": game["away_participant_pointer"],
            "home_feature_sha256": game["home_feature_sha256"], "away_feature_sha256": game["away_feature_sha256"],
            "preview_game_sha256": record_sha256(game), **RECORD_LABELS}


def _prediction(estimate: dict[str, Any], scheduled: Any) -> dict[str, Any]:
    keep = [f for group in PREDICTION_FIELDS.values() for f in group
            if f not in RECORD_LABELS and f not in ("record_type", "provider_scheduled_utc", "preview_estimate_sha256")]
    return {**{f: estimate[f] for f in keep}, "record_type": "prediction", "provider_scheduled_utc": scheduled,
            "preview_estimate_sha256": record_sha256(estimate), **RECORD_LABELS}


def _check_arithmetic(predictions: list[dict[str, Any]], participants: list[dict[str, Any]]) -> None:
    """Exact complements and paired orientations; smoothed strengths equal strength_q of the frozen participant's own
    W/L/T (never a borrowed record)."""
    by_feature = {p["preview_feature_sha256"]: p for p in participants}
    pairs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for x in predictions:
        pairs.setdefault((x["event_key"], x["model_id"]), []).append(x)
        if x["support_state"] != SUPPORTED:
            if x["probability"] is not None or x["opponent_probability"] is not None:
                raise ShadowError("SHADOW_ARITHMETIC_INCOHERENT", f"{x['event_key']}: an abstention carries a value")
            continue
        p, q = _fraction(x["probability"]), _fraction(x["opponent_probability"])
        if p is None or q is None or p + q != 1 or not 0 < p < 1:
            raise ShadowError("SHADOW_ARITHMETIC_INCOHERENT", f"{x['event_key']}: complements are not exact")
        if x["model_id"] == pv.MODEL_SMOOTHED:
            for side_q, side_feature in (("team_strength_q", "team_feature_sha256"),
                                         ("opponent_strength_q", "opponent_feature_sha256")):
                part = by_feature.get(x[side_feature])
                if part is None or _fraction(x[side_q]) != bm.strength_q(
                        {"wins": part["wins"], "ties": part["ties"], "games": part["games"]}):
                    raise ShadowError("SHADOW_ARITHMETIC_INCOHERENT", f"{x['event_key']}: a strength does not come "
                                                                      "from that side's own record")
    for (key, _model), rows in pairs.items():
        if sorted(r["orientation"] for r in rows) != sorted(ORIENTATIONS):
            raise ShadowError("SHADOW_ARITHMETIC_INCOHERENT", f"{key}: not exactly one prediction per orientation")
        home = next(r for r in rows if r["orientation"] == "home")
        away = next(r for r in rows if r["orientation"] == "away")
        if home["support_state"] == SUPPORTED and \
                _fraction(home["probability"]) + _fraction(away["probability"]) != 1:
            raise ShadowError("SHADOW_ARITHMETIC_INCOHERENT", f"{key}: the paired probabilities do not sum to one")


def summary_rows(payload: dict[str, Any], event_keys: Iterable[str], model_ids: Iterable[str] = MODEL_IDS,
                 timing: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Game-grain summaries (one row per selected model) of the selected events: exact distinct events (two
    orientations are not two games), the participant records and predictions of those games, supported/abstained games
    and predictions, abstention reasons counted once per game and, when served, the anchored/ineligible games."""
    selected = set(event_keys)
    participants = [p for p in payload["participants"] if p["event_key"] in selected]
    rows = []
    for model_id in model_ids:
        predictions = [x for x in payload["predictions"] if x["event_key"] in selected and x["model_id"] == model_id]
        games = {x["event_key"]: x for x in predictions if x["orientation"] == "home"}
        reasons: dict[str, int] = {}
        for x in games.values():
            for code in sorted({pv.reason_key(r) for r in x["abstention_reasons"]}):
                reasons[code] = reasons.get(code, 0) + 1
        row = {"record_type": "summary", "model_id": model_id, "model_sha256": pv.model_sha256(model_id),
               "distinct_events": len({x["event_key"] for x in predictions}), "participants": len(participants),
               "supported_participants": sum(p["support_state"] == SUPPORTED for p in participants),
               "unsupported_participants": sum(p["support_state"] != SUPPORTED for p in participants),
               "cold_start_participants": sum(p["cold_start"] is True for p in participants),
               "predictions": len(predictions), "predictions_per_game": len(ORIENTATIONS),
               "supported_predictions": sum(x["support_state"] == SUPPORTED for x in predictions),
               "abstained_predictions": sum(x["support_state"] != SUPPORTED for x in predictions),
               "supported_games": sum(x["support_state"] == SUPPORTED for x in games.values()),
               "abstained_games": sum(x["support_state"] != SUPPORTED for x in games.values()),
               "abstention_reasons": dict(sorted(reasons.items())), **RECORD_LABELS}
        if timing is not None:
            row["anchored_pre_provider_start_games"] = sum(timing[k]["decision"] == ANCHORED for k in games)
            row["ineligible_games"] = sum(timing[k]["decision"] != ANCHORED for k in games)
        rows.append(row)
    return rows


def derive_payload(preview_binding: dict[str, Any], spec: dict[str, Any], contract_sha256: str, *,
                   order: str | None = None) -> dict[str, Any]:
    """The complete canonical prediction payload from the verified preview binding and the contract (never a supplied
    summary). Every value is the verified preview's value; the population must equal the pinned cohort."""
    pins = spec["input"]
    doc = preview_binding["document"]
    if (preview_binding["preview_identity"], preview_binding["preview_sha256"], doc["contract"]["sha256"],
            doc["input"]["capsule_identity"], doc["input"]["capsule_sha256"],
            doc["input"]["capsule_contract_sha256"], doc["input"]["source_body_sha256"],
            doc["input"]["receipt_sha256"]) != (pins["preview_identity"], pins["preview_sha256"],
                                                pins["preview_contract_sha256"], pins["capsule_identity"],
                                                pins["capsule_sha256"], pins["capsule_contract_sha256"],
                                                pins["source_body_sha256"], pins["receipt_sha256"]):
        raise ShadowError("SHADOW_INPUT_NOT_PINNED", "the verified preview or its capsule is not the pinned input")
    cohort_name = f"{pv.CAPSULE_ROOT}/{pins['capsule_identity']}/{prospective.BUNDLE['expected']}"
    if (doc["bundle"].get(cohort_name) or {}).get("sha256") != pins["expected_cohort_sha256"]:
        raise ShadowError("SHADOW_INPUT_NOT_PINNED", "the bundled expected cohort is not the pinned cohort")
    if canonical_bytes(doc["models"]) != canonical_bytes(_models_document()):
        raise ShadowError("SHADOW_INPUT_MODELS_DIFFER", "the preview's models are not the frozen fixed models")
    games = doc["games"]
    scheduled = {g["event_key"]: g["scheduled_utc"] for g in games}
    events, participants, predictions = [], [], []
    for index in processing_order(len(games), order):
        events.append(_event(games[index]))
    for index in processing_order(len(doc["features"]), order):
        participants.append(_participant(doc["features"][index]))
    for index in processing_order(len(doc["estimates"]), order):
        estimate = doc["estimates"][index]
        predictions.append(_prediction(estimate, scheduled.get(estimate["event_key"])))
    rank = {"home": 0, "away": 1}
    events.sort(key=lambda e: e["event_key"])
    participants.sort(key=lambda p: (p["event_key"], rank.get(p["side"], 2), p["team_key"] or "",
                                     p["participant_pointer"] or ""))
    predictions.sort(key=lambda x: (x["event_key"], MODEL_IDS.index(x["model_id"]), rank[x["orientation"]]))
    _check_arithmetic(predictions, participants)
    keys = sorted(e["event_key"] for e in events)
    if (len(events), len(participants), len(predictions)) != (pins["expected_events"], pins["expected_participants"],
                                                              pins["expected_predictions"]) or \
            len(set(keys)) != len(keys) or len(predictions) != len(events) * len(MODEL_IDS) * len(ORIENTATIONS):
        raise ShadowError("SHADOW_INPUT_POPULATION_MISMATCH", "the derived population is not the pinned cohort")
    payload = {
        "schema": PAYLOAD_SCHEMA, "population": POPULATION, "designation": DESIGNATION,
        "contract": {"id": CONTRACT_ID, "sha256": contract_sha256},
        "source": {"preview_population": pv.POPULATION, "preview_identity": preview_binding["preview_identity"],
                   "preview_sha256": preview_binding["preview_sha256"], "preview_contract_id": doc["contract"]["id"],
                   "preview_contract_sha256": doc["contract"]["sha256"], "preview_role": LABELS["source_preview_role"],
                   "capsule_population": doc["input"]["capsule_population"],
                   "capsule_identity": doc["input"]["capsule_identity"],
                   "capsule_sha256": doc["input"]["capsule_sha256"],
                   "capsule_contract_id": doc["input"]["capsule_contract_id"],
                   "capsule_contract_sha256": doc["input"]["capsule_contract_sha256"],
                   "source_body_sha256": doc["input"]["source_body_sha256"],
                   "receipt_sha256": doc["input"]["receipt_sha256"],
                   "source_endpoint": doc["input"]["source_endpoint"],
                   "expected_cohort_sha256": pins["expected_cohort_sha256"],
                   "observation": doc["input"]["observation"]},
        "models": _models_document(), "numeric_contract": dict(NUMERIC_CONTRACT), "labels": dict(LABELS),
        "events": events, "participants": participants, "predictions": predictions}
    payload["summary"] = summary_rows(payload, keys)
    payload["counts"] = {
        "events": len(events), "participants": len(participants),
        "supported_participants": sum(p["support_state"] == SUPPORTED for p in participants),
        "unsupported_participants": sum(p["support_state"] != SUPPORTED for p in participants),
        "cold_start_participants": sum(p["cold_start"] is True for p in participants),
        "predictions": len(predictions),
        "supported_predictions": sum(x["support_state"] == SUPPORTED for x in predictions),
        "abstained_predictions": sum(x["support_state"] != SUPPORTED for x in predictions)}
    return payload


def anchor_body(payload: dict[str, Any], payload_sha256: str, payload_size: int) -> str:
    """The deterministic hash-only body of the C53-A01-M2 anchor comment (hashes and metadata only; no prediction
    value and no raw provider content)."""
    src, counts, models = payload["source"], payload["counts"], payload["models"]
    lines = [ANCHOR_SPEC["heading"],
             f"payload_sha256: {payload_sha256}",
             f"payload_bytes: {payload_size}",
             f"payload_schema: {PAYLOAD_SCHEMA}; population: {POPULATION}; designation: {DESIGNATION}",
             f"shadow_contract: {payload['contract']['id']} sha256 {payload['contract']['sha256']}",
             f"source_capsule: {src['capsule_identity']} (capsule.json sha256 {src['capsule_sha256']})",
             f"source_preview: {src['preview_identity']} (preview.json sha256 {src['preview_sha256']}; preview "
             f"contract sha256 {src['preview_contract_sha256']})",
             f"source_response_sha256: {src['source_body_sha256']}; source_receipt_sha256: {src['receipt_sha256']}; "
             f"expected_cohort_sha256: {src['expected_cohort_sha256']}",
             *(f"model: {m} sha256 {models[m]['sha256']}" for m in MODEL_IDS),
             f"cohort: {counts['events']} events; {counts['participants']} participant records; "
             f"{counts['predictions']} oriented predictions ({counts['supported_predictions']} supported, "
             f"{counts['abstained_predictions']} abstained)",
             "labels: UNTRUSTED_SHADOW; PROVIDER_CLAIM_INPUTS; PIT_NOT_ADMITTED; NOT_CALIBRATED; "
             "PREDICTIVE_SKILL_NOT_ESTABLISHED; national coverage UNKNOWN",
             "basis: this comment's service-created time bounds when these payload bytes existed "
             "(PRE_PROVIDER_REPORTED_START only; not an official kickoff or original provider publication)",
             "values: none published here (hashes and metadata only)"]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------------------------- stage two: snapshot

def parse_service_time(text: Any) -> _dt.datetime:
    """A Jira service-created time (milliseconds and a +hhmm/-hhmm offset) as an exact UTC instant."""
    match = SERVICE_TIME_RE.fullmatch(text) if isinstance(text, str) else None
    if not match:
        raise ShadowError("SHADOW_ANCHOR_TIME_INVALID", f"{text!r} is not the service time grammar")
    year, month, day, hour, minute, second, milli, sign, oh, om = match.groups()
    try:
        if int(oh) > 14 or int(om) > 59:
            raise ValueError("offset")
        tz = _dt.timezone((1 if sign == "+" else -1) * _dt.timedelta(hours=int(oh), minutes=int(om)))
        return _dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), int(milli) * 1000,
                            tzinfo=tz).astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise ShadowError("SHADOW_ANCHOR_TIME_INVALID", f"{text!r} is not a valid instant") from exc


def verify_anchor_receipt(receipt: bytes, expected_body: str) -> dict[str, Any]:
    """The anchor receipt (the exact raw readback of the comment) semantically verified: the issue's comment URL, a
    string comment id, the service time grammar, unedited (created equals updated) and a body equal to the rendered
    hash-only body. Returns the anchor record the snapshot binds."""
    doc = strict_json(receipt, "SHADOW_ANCHOR_RECEIPT_MALFORMED")
    if not isinstance(doc, dict):
        raise ShadowError("SHADOW_ANCHOR_RECEIPT_MALFORMED", "the anchor receipt is not a JSON object")
    cid = doc.get("id")
    if type(cid) is not str or not COMMENT_ID_RE.match(cid):
        raise ShadowError("SHADOW_ANCHOR_IDENTITY_INVALID", f"comment id {cid!r} is not a decimal string")
    expected_self = (f"{ANCHOR_SPEC['tenant']}/rest/api/3/issue/{ANCHOR_SPEC['issue_id']}/comment/{cid}")
    if doc.get("self") != expected_self:
        raise ShadowError("SHADOW_ANCHOR_ISSUE_MISMATCH", f"the comment is not on {ANCHOR_SPEC['issue_key']} "
                                                          f"({doc.get('self')!r})")
    created, updated = doc.get("created"), doc.get("updated")
    created_utc = parse_service_time(created)
    parse_service_time(updated)
    if created != updated:
        raise ShadowError("SHADOW_ANCHOR_EDITED", "the comment was edited (updated differs from created); its creation "
                                                  "time cannot prove the current body")
    text = adf_text(doc.get("body"))
    if not text.startswith(ANCHOR_SPEC["marker"] + " "):
        raise ShadowError("SHADOW_ANCHOR_MARKER_MISMATCH", "the comment does not carry the C53-A01-M2 marker")
    if text != expected_body:
        raise ShadowError("SHADOW_ANCHOR_BODY_MISMATCH", "the comment body is not the hash-only body of this payload")
    return {"system": ANCHOR_SPEC["system"], "tenant": ANCHOR_SPEC["tenant"], "issue_key": ANCHOR_SPEC["issue_key"],
            "issue_id": ANCHOR_SPEC["issue_id"], "comment_id": cid, "marker": ANCHOR_SPEC["marker"],
            "created": created, "updated": updated, "created_utc": iso_micro(created_utc), "edited": False,
            "body_text_sha256": sha256_hex(text.encode("utf-8")), "receipt_file": ANCHOR_MEMBER,
            "receipt_sha256": sha256_hex(receipt), "receipt_bytes": len(receipt),
            "proves": "THE_PAYLOAD_BYTES_EXISTED_NO_LATER_THAN_THE_SERVICE_CREATED_TIME",
            "does_not_prove": ["OFFICIAL_KICKOFF", "ORIGINAL_PROVIDER_PUBLICATION", "PIT_ADMISSION",
                               "PREDICTIVE_SKILL"]}


def _utc_text(text: Any, layout: str) -> _dt.datetime | None:
    if not isinstance(text, str):
        return None
    try:
        parsed = _dt.datetime.strptime(text, layout)
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.strftime(layout) == text else None


def timing_rows(payload: dict[str, Any], anchor_created_utc: str) -> list[dict[str, Any]]:
    """One decision per event: ANCHORED_PRE_PROVIDER_REPORTED_START exactly when observation end <= anchor created <
    provider-reported start and the event was pre-game at observation; otherwise INELIGIBLE with every reason."""
    end = _utc_text(payload["source"]["observation"]["request_end_utc"], "%Y-%m-%dT%H:%M:%S.%fZ")
    anchor = _utc_text(anchor_created_utc, "%Y-%m-%dT%H:%M:%S.%fZ")
    rows = []
    for event in payload["events"]:
        reasons = []
        start = _utc_text(event["provider_scheduled_utc"], "%Y-%m-%dT%H:%M:%SZ")
        state = event["event_state_at_observation"]
        if start is None:
            reasons.append("PROVIDER_START_MISSING")
        if not (isinstance(state, dict) and state.get("state") == "pre" and state.get("completed") is False):
            reasons.append("EVENT_NOT_PRE_GAME_AT_OBSERVATION")
        if end is None or anchor is None or anchor < end:
            reasons.append("ANCHOR_BEFORE_OBSERVATION_END")
        if start is not None and anchor is not None and anchor >= start:
            reasons.append("ANCHOR_AT_OR_AFTER_PROVIDER_REPORTED_START")
        rows.append({"event_key": event["event_key"], "provider_scheduled_utc": event["provider_scheduled_utc"],
                     "observation_end_utc": payload["source"]["observation"]["request_end_utc"],
                     "anchor_created_utc": anchor_created_utc, "decision": INELIGIBLE if reasons else ANCHORED,
                     "basis": TIMING_BASIS, "reasons": sorted(reasons)})
    return rows


def bundle_names(preview_identity: str, capsule_identity: str) -> list[str]:
    """Every member of a snapshot directory except snapshot.json (fixed relative names)."""
    base = f"{PREVIEW_ROOT}/{preview_identity}"
    return sorted([PAYLOAD_FILE, ANCHOR_MEMBER, CONTRACT_MEMBER, f"{base}/{pv.PREVIEW_FILE}",
                   *(f"{base}/{name}" for name in pv.bundle_names(capsule_identity))])


def derive_snapshot(spec: dict[str, Any], contract_sha256: str, payload: dict[str, Any], payload_bytes: bytes,
                    anchor: dict[str, Any], members: dict[str, bytes], chunk_size: int = 1 << 20) -> dict[str, Any]:
    """The complete expected snapshot document from the verified payload, the verified anchor record and the exact
    bundle member bytes."""
    pins = spec["input"]
    names = bundle_names(pins["preview_identity"], pins["capsule_identity"])
    if sorted(members) != names:
        raise ShadowError("SHADOW_BUNDLE_MEMBERSHIP_MISMATCH", f"bundle members {sorted(members)} != {names}")
    timing = timing_rows(payload, anchor["created_utc"])
    anchored = {t["event_key"] for t in timing if t["decision"] == ANCHORED}
    predictions = payload["predictions"]
    return {"schema": SCHEMA, "population": POPULATION, "designation": DESIGNATION,
            "contract": {"id": CONTRACT_ID, "sha256": contract_sha256},
            "payload": {"file": PAYLOAD_FILE, "schema": payload["schema"], "sha256": sha256_hex(payload_bytes),
                        "bytes": len(payload_bytes), "counts": payload["counts"]},
            "anchor": anchor,
            "timing": {"basis": TIMING_BASIS,
                       "rule": "ANCHORED exactly when observation end <= anchor service-created time < provider-"
                               "reported start and the event was pre-game at observation; otherwise INELIGIBLE with "
                               "every reason (retained, never dropped or backdated)",
                       "events": timing},
            "labels": dict(LABELS),
            "counts": {"events": len(payload["events"]), "participants": len(payload["participants"]),
                       "predictions": len(predictions), "anchored_events": len(anchored),
                       "ineligible_events": len(timing) - len(anchored),
                       "anchored_predictions": sum(x["event_key"] in anchored for x in predictions),
                       "ineligible_predictions": sum(x["event_key"] not in anchored for x in predictions),
                       "supported_predictions": sum(x["support_state"] == SUPPORTED for x in predictions),
                       "abstained_predictions": sum(x["support_state"] != SUPPORTED for x in predictions)},
            "bundle": {name: {"sha256": pv._hash_chunks(members[name], chunk_size), "bytes": len(members[name])}
                       for name in names}}


def identity_document(snapshot: dict[str, Any]) -> dict[str, Any]:
    """The identity document: the snapshot file hash, the bundle member hashes and the contract (no other member)."""
    return {"schema": IDENTITY_SCHEMA, "population": POPULATION, "contract_id": CONTRACT_ID,
            "contract_sha256": snapshot["contract"]["sha256"], "snapshot_file": SNAPSHOT_FILE,
            "snapshot_sha256": sha256_hex(file_bytes(snapshot)), "bundle": snapshot["bundle"]}


def snapshot_identity(snapshot: dict[str, Any]) -> str:
    return sha256_hex(canonical_bytes(identity_document(snapshot)))


def profile_of(snapshot: dict[str, Any]) -> dict[str, str]:
    """The pinnable profile of a verified snapshot (what the packaged gate pins for the actual anchor)."""
    a = snapshot["anchor"]
    return {"snapshot_identity": snapshot_identity(snapshot), "payload_sha256": snapshot["payload"]["sha256"],
            "issue_key": a["issue_key"], "issue_id": a["issue_id"], "comment_id": a["comment_id"],
            "created": a["created"], "updated": a["updated"], "receipt_sha256": a["receipt_sha256"],
            "body_text_sha256": a["body_text_sha256"]}


# --------------------------------------------------------------------------------------------- comparison

def _same(a: Any, b: Any) -> bool:
    try:
        return canonical_bytes(a) == canonical_bytes(b)
    except (TypeError, ValueError):
        return False


def first_payload_difference(expected: dict[str, Any], actual: Any) -> tuple[str, str] | None:
    """The first governed difference between the re-derived payload and a supplied one, by family order; every
    governed value is compared by its canonical serialized bytes (so 25, 25.0, true and "25" differ)."""
    if not isinstance(actual, dict) or set(actual) != set(PAYLOAD_TOP):
        extra = sorted(set(actual) - set(PAYLOAD_TOP)) if isinstance(actual, dict) else ["<not an object>"]
        missing = sorted(set(PAYLOAD_TOP) - set(actual)) if isinstance(actual, dict) else []
        return "SCHEMA", f"top-level members differ (extra {extra}, missing {missing})"
    if not _same(expected["schema"], actual["schema"]) or not _same(expected["population"], actual["population"]):
        return "SCHEMA", "schema or population differs"
    for family, member in (("DESIGNATION", "designation"), ("CONTRACT", "contract"), ("SOURCE", "source"),
                           ("MODELS", "models"), ("NUMERIC_CONTRACT", "numeric_contract"), ("LABELS", "labels")):
        if not _same(expected[member], actual[member]):
            return family, f"{member} differs"
    for name, key, fields, membership in (
            ("EVENT", "events", EVENT_FIELDS, lambda r: r.get("event_key")),
            ("PARTICIPANT", "participants", PARTICIPANT_FIELDS,
             lambda r: [r.get("event_key"), r.get("side"), r.get("team_key"), r.get("participant_pointer")]),
            ("PREDICTION", "predictions", PREDICTION_FIELDS,
             lambda r: [r.get("event_key"), r.get("model_id"), r.get("orientation")])):
        want, got = expected[key], actual[key]
        if not isinstance(got, list) or not all(isinstance(r, dict) for r in got):
            return f"{name}_MEMBERSHIP", f"{key} is not a list of records"
        if not _same([membership(r) for r in want], [membership(r) for r in got]):
            return f"{name}_MEMBERSHIP", f"{key} membership, multiplicity or order differs"
        allowed = {f for group in fields.values() for f in group}
        for index, (w, g) in enumerate(zip(want, got)):
            if set(g) != allowed:
                return f"{name}_IDENTITY", f"{key}[{index}] members differ"
            for family, names in fields.items():
                for field in names:
                    if not _same(w[field], g[field]):
                        return family, f"{key}[{index}].{field} differs"
    if not _same(expected["summary"], actual["summary"]):
        return "SUMMARY", "summary differs"
    if not _same(expected["counts"], actual["counts"]):
        return "COUNTS", "counts differ"
    return None


def first_snapshot_difference(expected: dict[str, Any], actual: Any) -> tuple[str, str] | None:
    if not isinstance(actual, dict) or set(actual) != set(SNAPSHOT_TOP):
        extra = sorted(set(actual) - set(SNAPSHOT_TOP)) if isinstance(actual, dict) else ["<not an object>"]
        missing = sorted(set(SNAPSHOT_TOP) - set(actual)) if isinstance(actual, dict) else []
        return "SCHEMA", f"top-level members differ (extra {extra}, missing {missing})"
    if not _same(expected["schema"], actual["schema"]) or not _same(expected["population"], actual["population"]):
        return "SCHEMA", "schema or population differs"
    for family, member in (("DESIGNATION", "designation"), ("CONTRACT", "contract"), ("PAYLOAD", "payload"),
                           ("ANCHOR", "anchor"), ("TIMING", "timing"), ("LABELS", "labels"), ("COUNTS", "counts"),
                           ("BUNDLE", "bundle")):
        if not _same(expected[member], actual[member]):
            return family, f"{member} differs"
    return None


# --------------------------------------------------------------------------------------------- reader

def literal_location(path: Path | str) -> str:
    try:
        return readonly_sqlite.literal_path(path)
    except readonly_sqlite.DatabaseLocationError as exc:
        code = {readonly_sqlite.LOCATION_UNSUPPORTED: "SHADOW_LOCATION_UNSUPPORTED",
                readonly_sqlite.LOCATION_NOT_LITERAL: "SHADOW_LOCATION_NOT_LITERAL"}.get(exc.code, exc.code)
        raise ShadowError(code, exc.detail) from exc


def _read(path: str, code: str) -> bytes:
    if not os.path.isfile(path):
        raise ShadowError(code, f"no file at {path}")
    with open(path, "rb") as handle:
        return handle.read()


def verify_preview_input(directory: str, spec: dict[str, Any]) -> dict[str, Any]:
    """The bundled preview verified completely by the accepted BAT-724 reader (pinned identity and contract; its
    refusals keep their codes under a SHADOW_INPUT_ prefix)."""
    pins = spec["input"]
    path = os.path.join(directory, PREVIEW_ROOT, pins["preview_identity"], pv.PREVIEW_FILE)
    try:
        binding = pv.verify_preview(path, contract_sha256=pins["preview_contract_sha256"],
                                    expect_identity=pins["preview_identity"])
    except pv.PreviewError as exc:
        raise ShadowError(f"SHADOW_INPUT_{exc.code}", str(exc)) from exc
    if binding["preview_sha256"] != pins["preview_sha256"]:
        raise ShadowError("SHADOW_INPUT_NOT_PINNED", "the bundled preview is not the pinned preview bytes")
    return binding


def verify_snapshot(path: Path | str, *, contract_sha256: str = CONTRACT_SHA256, expect_identity: str | None = None,
                    profile: Any = PINNED, require_pinned_profile: bool = True) -> dict[str, Any]:
    """Verify a snapshot directory completely and return its binding plus the verified payload and snapshot
    documents. ``profile`` is the pinned anchor profile (the packaged :data:`ANCHOR_PROFILE` unless a test passes a
    fixture profile); the builder alone verifies with ``require_pinned_profile=False`` before the gate is packaged."""
    location = literal_location(path)
    if not os.path.isfile(pv.io_path(location)):
        raise ShadowError("SHADOW_MISSING", f"no snapshot file at {location}")
    directory, name = os.path.split(location)
    if name != SNAPSHOT_FILE or not IDENTITY_RE.match(os.path.basename(directory)):
        raise ShadowError("SHADOW_LOCATION_INVALID", f"the snapshot must be <identity>/{SNAPSHOT_FILE} with a 64-hex "
                                                     "identity directory")
    io_directory = pv.io_path(directory)
    contract = _read(os.path.join(io_directory, *CONTRACT_MEMBER.split("/")), "SHADOW_BUNDLE_MEMBER_MISSING")
    spec = _spec(contract, contract_sha256)
    pins = spec["input"]
    binding = verify_preview_input(io_directory, spec)
    files = pv.directory_files(io_directory)
    got = files.pop(SNAPSHOT_FILE, None)
    if got is None:
        raise ShadowError("SHADOW_MISSING", f"no snapshot file at {location}")
    names = bundle_names(pins["preview_identity"], pins["capsule_identity"])
    if sorted(files) != names:
        raise ShadowError("SHADOW_BUNDLE_MEMBERSHIP_MISMATCH",
                          f"extra {sorted(set(files) - set(names))}, missing {sorted(set(names) - set(files))}")
    if files[CONTRACT_MEMBER] != contract:
        raise ShadowError("SHADOW_BUNDLE_MEMBERSHIP_MISMATCH", "the bundled contract differs")
    payload = derive_payload(binding, spec, contract_sha256)
    payload_bytes = file_bytes(payload)
    if files[PAYLOAD_FILE] != payload_bytes:
        supplied = strict_json(files[PAYLOAD_FILE], "SHADOW_PAYLOAD_MALFORMED")
        diff = first_payload_difference(payload, supplied)
        family, detail = diff if diff else ("CANONICAL_FORM", "the payload bytes are not the frozen canonical form")
        raise ShadowError(f"SHADOW_PAYLOAD_{family}_MISMATCH", detail)
    payload_sha = sha256_hex(payload_bytes)
    anchor = verify_anchor_receipt(files[ANCHOR_MEMBER], anchor_body(payload, payload_sha, len(payload_bytes)))
    expected = derive_snapshot(spec, contract_sha256, payload, payload_bytes, anchor, files)
    if got != file_bytes(expected):
        supplied = strict_json(got, "SHADOW_SNAPSHOT_MALFORMED")
        diff = first_snapshot_difference(expected, supplied)
        family, detail = diff if diff else ("CANONICAL_FORM", "the snapshot bytes are not the frozen canonical form")
        raise ShadowError(f"SHADOW_SNAPSHOT_{family}_MISMATCH", detail)
    identity = snapshot_identity(expected)
    if os.path.basename(directory) != identity:
        raise ShadowError("SHADOW_IDENTITY_MISMATCH", f"the identity document hashes to {identity}, the directory is "
                                                      f"{os.path.basename(directory)}")
    if expect_identity is not None and expect_identity != identity:
        raise ShadowError("STALE_SHADOW_IDENTITY", f"expected {expect_identity}, found {identity}")
    actual_profile = profile_of(expected)
    pinned = ANCHOR_PROFILE if profile is PINNED else profile
    if require_pinned_profile:
        if pinned is None:
            raise ShadowError("SHADOW_PROFILE_NOT_PINNED", "no actual anchor profile is packaged for this snapshot")
        if not isinstance(pinned, dict) or set(pinned) != set(PROFILE_FIELDS):
            raise ShadowError("SHADOW_PROFILE_NOT_PINNED", "the packaged anchor profile is malformed")
        anchor_fields = [k for k in PROFILE_FIELDS if k not in ("snapshot_identity", "payload_sha256")]
        if any(not _same(pinned[k], actual_profile[k]) for k in anchor_fields):
            raise ShadowError("SHADOW_ANCHOR_NOT_PINNED_PROFILE", "the snapshot's anchor is not the actual anchor the "
                                                                  "packaged gate pins")
        if not _same(pinned["payload_sha256"], actual_profile["payload_sha256"]) or \
                not _same(pinned["snapshot_identity"], identity):
            raise ShadowError("SHADOW_NOT_PINNED_SNAPSHOT", "the snapshot is not the one the packaged gate pins")
    return {"snapshot_identity": identity, "snapshot_sha256": sha256_hex(got), "location": location,
            "identity_document": identity_document(expected), "snapshot": expected, "payload": payload,
            "payload_sha256": payload_sha, "anchor": anchor, "profile": actual_profile,
            "profile_pinned": pinned is not None and isinstance(pinned, dict) and
            all(_same(pinned.get(k), actual_profile[k]) for k in PROFILE_FIELDS),
            "preview_identity": binding["preview_identity"], "capsule_identity": binding["capsule_identity"]}


def parse_cutoff(value: str | None) -> _dt.datetime:
    """The strict shadow cutoff: an ISO-8601 instant with seconds and an explicit zone, matched as a whole string; an
    instant outside the representable UTC range is refused cleanly (CUTOFF_OUT_OF_RANGE)."""
    if value is None:
        raise ShadowError("CUTOFF_REQUIRED", "the shadow grains need --cutoff <ISO-8601 instant with a zone>")
    text = str(value)
    match = CUTOFF_RE.fullmatch(text)
    if not match:
        if NAIVE_OR_DATE_RE.fullmatch(text):
            raise ShadowError("CUTOFF_TIMEZONE_REQUIRED", f"cutoff {text!r} has no explicit zone or seconds")
        raise ShadowError("CUTOFF_INVALID", f"cutoff {text!r} is not an ISO-8601 instant")
    year, month, day, hour, minute, second, fraction, zone = match.groups()
    try:
        if zone == "Z":
            tz = UTC
        else:
            hours, minutes = int(zone[1:3]), int(zone[4:6])
            if hours > 14 or minutes > 59:
                raise ValueError(zone)
            tz = _dt.timezone((1 if zone[0] == "+" else -1) * _dt.timedelta(hours=hours, minutes=minutes))
        micro = int(fraction[1:].ljust(6, "0")) if fraction else 0
        local = _dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), micro, tzinfo=tz)
    except ValueError as exc:
        raise ShadowError("CUTOFF_INVALID", f"cutoff {text!r} is not a valid instant") from exc
    try:
        return local.astimezone(UTC)
    except (OverflowError, ValueError) as exc:
        raise ShadowError("CUTOFF_OUT_OF_RANGE", f"cutoff {text!r} is outside the representable UTC range") from exc


def normalize_event(value: str) -> str:
    if not isinstance(value, str) or not EVENT_KEY_RE.match(value):
        raise ShadowError("EVENT_KEY_INVALID", f"event must be espn:event:<digits>, got {value!r}")
    return value


def normalize_team(value: str) -> str:
    if not isinstance(value, str) or not TEAM_KEY_RE.match(value):
        raise ShadowError("TEAM_KEY_INVALID", f"team must be espn:team:<digits>, got {value!r}")
    return value


def normalize_model(value: str) -> str:
    if value not in MODEL_IDS:
        raise ShadowError("SHADOW_MODEL_UNKNOWN", f"model must be one of {list(MODEL_IDS)}, got {value!r}")
    return value


def normalize_orientation(value: str) -> str:
    if value not in ORIENTATIONS:
        raise ShadowError("ORIENTATION_INVALID", f"orientation must be one of {list(ORIENTATIONS)}, got {value!r}")
    return value


class ShadowSnapshot:
    """A completely verified snapshot; rows come only from its re-derived documents."""

    def __init__(self, path: Path | str, *, contract_sha256: str = CONTRACT_SHA256, expect_identity: str | None = None,
                 profile: Any = PINNED) -> None:
        self.binding = verify_snapshot(path, contract_sha256=contract_sha256, expect_identity=expect_identity,
                                       profile=profile)
        self.payload = self.binding["payload"]
        self.snapshot = self.binding["snapshot"]
        self.timing = {t["event_key"]: t for t in self.snapshot["timing"]["events"]}

    def __enter__(self) -> "ShadowSnapshot":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    @staticmethod
    def filters(grain: str, *, season: int | None = None, event: str | None = None, team: str | None = None,
                model: str | None = None, orientation: str | None = None) -> dict[str, Any]:
        """The validated, applicable filters of one query (refused before any file is read)."""
        if grain not in GRAINS:
            raise ShadowError("SHADOW_GRAIN_REQUIRED", f"--prospective-shadow serves only {list(GRAINS)}, not "
                                                       f"{grain!r}")
        given = {"season": season, "event": event, "team": team, "model": model, "orientation": orientation}
        stray = [f"--{k}" for k, v in given.items() if v is not None and k not in APPLICABLE[grain]]
        if stray:
            raise ShadowError("FILTER_NOT_APPLICABLE", f"{stray} do not apply to the {grain} grain")
        out: dict[str, Any] = {}
        if season is not None:
            if isinstance(season, bool) or not isinstance(season, int):
                raise ShadowError("SEASON_INVALID", f"season must be an integer, got {season!r}")
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
        for p in self.payload["participants"]:
            teams.setdefault(p["event_key"], set()).add(p["team_key"])
        out = []
        for event in self.payload["events"]:
            key = event["event_key"]
            if "season" in filters and event["season"] != filters["season"]:
                continue
            if "event" in filters and key != filters["event"]:
                continue
            if "team" in filters and filters["team"] not in (teams.get(key, set()) |
                                                             {event["home_team_key"], event["away_team_key"]}):
                continue
            out.append(key)
        return out

    def query(self, grain: str, *, cutoff: str | None = None, season: int | None = None, event: str | None = None,
              team: str | None = None, model: str | None = None, orientation: str | None = None,
              limit: int | None = 50, offset: int = 0, all_rows: bool = False) -> dict[str, Any]:
        filters = self.filters(grain, season=season, event=event, team=team, model=model, orientation=orientation)
        if offset < 0:
            raise ShadowError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise ShadowError("NEGATIVE_LIMIT", "limit must be zero or positive")
        when = parse_cutoff(cutoff)
        anchor = self.snapshot["anchor"]
        created = _dt.datetime.strptime(anchor["created_utc"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
        if when < created:
            raise ShadowError("SHADOW_UNAVAILABLE_BEFORE_ANCHOR", f"the snapshot's anchor was service-created at "
                              f"{anchor['created_utc']}; nothing was frozen by {iso_micro(when)}")
        payload, identity = self.payload, self.binding["snapshot_identity"]
        result: dict[str, Any] = {
            "shadow_identity": identity, "payload_sha256": self.binding["payload_sha256"], "contract_id": CONTRACT_ID,
            "contract_sha256": self.snapshot["contract"]["sha256"], "population": POPULATION,
            "designation": DESIGNATION, "grain": grain, "filters": filters,
            "cutoff": {"literal": cutoff, "utc": iso_micro(when)},
            "anchor": {k: anchor[k] for k in ("issue_key", "comment_id", "marker", "created", "updated",
                                              "created_utc", "edited", "receipt_sha256", "body_text_sha256")},
            "anchor_at_cutoff": {"state": AVAILABLE_STATE, "reason": "CUTOFF_AT_OR_AFTER_SERVICE_CREATED_ANCHOR"},
            "timing_basis": TIMING_BASIS, "labels": self.snapshot["labels"],
            "models": {m: payload["models"][m]["sha256"] for m in MODEL_IDS},
            "source": {k: payload["source"][k] for k in ("preview_identity", "preview_sha256", "capsule_identity",
                                                         "source_body_sha256", "receipt_sha256", "source_endpoint",
                                                         "observation")},
            "offset": offset, "limit": None if all_rows else limit}
        if season is not None and season != SEASON:
            result.update(season_scope_state=OUT_OF_SCOPE_STATE, total=0, returned=0, rows=[], next_offset=None,
                          note="only the retained 2026 provider cohort is frozen; no row is fabricated")
            return result
        if grain == "shadow-summary":
            selected = self._selected_events(filters)
            items = summary_rows(payload, selected, [filters["model"]] if "model" in filters else MODEL_IDS,
                                 self.timing) if selected else []
        else:
            items = [x for x in payload["predictions"] if
                     filters.get("season", x["season"]) == x["season"] and
                     filters.get("event", x["event_key"]) == x["event_key"] and
                     filters.get("team", x["team_key"]) == x["team_key"] and
                     filters.get("model", x["model_id"]) == x["model_id"] and
                     filters.get("orientation", x["orientation"]) == x["orientation"]]
        total = len(items)
        stop = None if all_rows else offset + (limit or 0)
        key = GRAIN_KEY[grain]
        rows = []
        for item in items[offset:stop]:
            row = {key: item, "shadow_identity": identity, "anchor_created_utc": anchor["created_utc"]}
            if key == "prediction":
                t = self.timing[item["event_key"]]
                row["timing"] = {"decision": t["decision"], "basis": t["basis"], "reasons": t["reasons"]}
            rows.append(row)
        result.update(season_scope_state=IN_SCOPE_STATE, total=total, returned=len(rows), rows=rows,
                      next_offset=offset + len(rows) if offset + len(rows) < total else None)
        return result


# --------------------------------------------------------------------------------------------- build helpers

def payload_files(contract: bytes, preview_path: Path | str, *, contract_sha256: str = CONTRACT_SHA256,
                  order: str | None = None, chunk_size: int = 1 << 20) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    """Stage one: the spec, the canonical payload bytes and the payload document from the verified preview."""
    spec = _spec(contract, contract_sha256, chunk_size)
    location = pv.io_path(literal_location(preview_path))
    pins = spec["input"]
    try:
        binding = pv.verify_preview(location, contract_sha256=pins["preview_contract_sha256"],
                                    expect_identity=pins["preview_identity"])
    except pv.PreviewError as exc:
        raise ShadowError(f"SHADOW_INPUT_{exc.code}", str(exc)) from exc
    if binding["preview_sha256"] != pins["preview_sha256"]:
        raise ShadowError("SHADOW_INPUT_NOT_PINNED", "the preview is not the pinned preview bytes")
    payload = derive_payload(binding, spec, contract_sha256, order=order)
    return spec, file_bytes(payload), payload


def snapshot_files(contract: bytes, preview_path: Path | str, payload: bytes, receipt: bytes, *,
                   contract_sha256: str = CONTRACT_SHA256, order: str | None = None, chunk_size: int = 1 << 20
                   ) -> tuple[str, dict[str, bytes], dict[str, Any], dict[str, Any]]:
    """Stage two: the identity, the complete set of files of the snapshot directory, the identity document and the
    snapshot document. The supplied payload must be exactly the re-derived payload and the receipt must verify."""
    spec, expected_bytes, document = payload_files(contract, preview_path, contract_sha256=contract_sha256,
                                                   order=order, chunk_size=chunk_size)
    if payload != expected_bytes:
        supplied = strict_json(payload, "SHADOW_PAYLOAD_MALFORMED")
        diff = first_payload_difference(document, supplied)
        family, detail = diff if diff else ("CANONICAL_FORM", "the payload bytes are not the frozen canonical form")
        raise ShadowError(f"SHADOW_PAYLOAD_{family}_MISMATCH", detail)
    anchor = verify_anchor_receipt(receipt, anchor_body(document, sha256_hex(payload), len(payload)))
    pins = spec["input"]
    preview_dir = os.path.dirname(pv.io_path(literal_location(preview_path)))
    members = {CONTRACT_MEMBER: contract, PAYLOAD_FILE: payload, ANCHOR_MEMBER: receipt}
    for name, data in pv.directory_files(preview_dir).items():
        members[f"{PREVIEW_ROOT}/{pins['preview_identity']}/{name}"] = data
    snapshot = derive_snapshot(spec, contract_sha256, document, payload, anchor, members, chunk_size)
    files = {SNAPSHOT_FILE: file_bytes(snapshot), **members}
    return snapshot_identity(snapshot), files, identity_document(snapshot), snapshot


__all__ = ["ShadowSnapshot", "ShadowError", "anchor_body", "derive_payload", "derive_snapshot",
           "first_payload_difference", "first_snapshot_difference", "identity_document", "parse_cutoff",
           "payload_files", "profile_of", "snapshot_files", "snapshot_identity", "summary_rows", "timing_rows",
           "verify_anchor_receipt", "verify_snapshot", "ANCHOR_PROFILE", "ANCHOR_SPEC", "CONTRACT_SHA256", "GRAINS",
           "LABELS", "MODEL_IDS", "RECORD_LABELS"]
