r"""Explicit prospective provider-observation capsule (BAT-723; TP51-A01 sections 1-3).

``bas-source-time-query --prospective-evidence <...\sha256\<identity>\capsule.json> --grain prospective-event
--cutoff 2026-10-12T00:00:00Z [--season 2026] [--event espn:event:<id>] [--team espn:team:<id>] [--limit 50]``

One immutable JSON capsule makes the single retained ESPN scoreboard observation of 2026-10-11 usable: its exact 25
provider event keys and 50 participant overall records, each derived from its own raw fields, with the real
observation bound of the retained request. It is a provider claim, never an official NCAA result, corroboration,
first-publication proof or PIT admission, and its coverage beyond the retained response is unknown.

Authority is the exact raw response plus the retained capture receipt, the manager-frozen expected cohort and the
committed data contract (``configs/prospective_provider_observation_20261011_contract.json``). The capsule's portable
bundle holds byte copies of those four inputs beside ``capsule.json``; the reader needs no manager directory. Before any
row is served the reader:

* resolves the given path through the accepted literal-location rules (a network, device or non-literal location is
  refused before any access; a missing file is never created) and requires ``capsule.json`` in a directory named by a
  64-hex identity, with the four bundle members at their fixed relative names;
* requires the bundled contract to be byte-identical to the committed contract this package pins
  (:data:`CONTRACT_SHA256`), and the bundled raw response, receipt and cohort to hash to that contract's pins;
* re-derives the complete expected capsule from those inputs (:func:`derive`: every event, participant, record,
  pointer, collection multiplicity, count, label and the observation interval, never a supplied summary), compares the
  canonical serialized bytes of every governed field (numeric and boolean types included; a string comparison of
  canonical JSON, not Python equality) and refuses the first difference under its family's code;
* recomputes the identity document and requires the directory name to equal its SHA-256.

Rows are served only from the verified re-derived document. Every served row carries the source-observation-only,
PIT-not-admitted, provider-claim and coverage labels. Both grains need an explicit timezone-aware ``--cutoff``: the
observation is unavailable before the retained request start, indeterminate within the request interval and available
at or after its end; a later cutoff never refreshes the snapshot and nothing reads the current clock.

Standard library only apart from the accepted literal-location helper and the base query's shared parsers. Imported
only when ``--prospective-evidence`` is named; every other invocation is unchanged.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import random
import re
import urllib.parse
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics import readonly_sqlite
from aggie_analytics.national_source_time import query as base

SCHEMA = "BAS-PROSPECTIVE-PROVIDER-OBSERVATION-CAPSULE-1"
IDENTITY_SCHEMA = "BAS-PROSPECTIVE-PROVIDER-OBSERVATION-IDENTITY-1"
POPULATION = "prospective_provider_observation_20261011"
CONTRACT_ID = "BAT-723-PROSPECTIVE-PROVIDER-OBSERVATION-20261011-V1"
#: SHA-256 of the committed contract ``configs/prospective_provider_observation_20261011_contract.json`` (the authority
#: anchor; a test requires it to equal the committed file).
CONTRACT_SHA256 = "f407155bfd540c309b8d8b7b6868e8c1215789f962bc4c707e680e0b7dc2df9a"
CAPSULE_FILE = "capsule.json"
BUNDLE = {"raw": "raw/provider-response.json", "receipt": "raw/provider-receipt.json",
          "expected": "inputs/EXPECTED_COHORT.json", "contract": "inputs/contract.json"}
SEASON = 2026
GRAINS = ("prospective-event", "prospective-team-record")
APPLICABLE = {"prospective-event": {"season", "event", "team"},
              "prospective-team-record": {"season", "event", "team"}}
OUT_OF_SCOPE_STATE = "NOT_YET_AUDITED"
IN_SCOPE_STATE = "PROSPECTIVE_2026_RETAINED_OBSERVATION"
TOP_LEVEL = ("schema", "population", "contract", "source", "observation", "labels", "bundle", "events",
             "participants", "counts")
LABELS = {"evidence_authority": "SOURCE_OBSERVATION_ONLY",
          "pit_admission": "PIT_NOT_ADMITTED",
          "source_authority": "PROVIDER_CLAIM_ESPN_SCOREBOARD_NOT_OFFICIAL_NCAA_NOT_CORROBORATED",
          "coverage": "RETAINED_SINGLE_RESPONSE_ONLY_COMPLETENESS_UNKNOWN_NOT_NATIONAL_NOT_REPRESENTATIVE",
          "identity": "PROVIDER_NAMESPACED_ONLY_NO_NCAA_OR_CFBD_CROSSWALK",
          "schedule_status": "SOURCE_REPORTED_NOT_PROOF_OF_KICKOFF_OR_OF_RECORD_COMPLETENESS_AT_A_LATER_CUTOFF",
          "home_away": "PROVIDER_HOMEAWAY_DESIGNATION_NOT_VENUE_OR_NEUTRAL_SITE",
          "first_publication": "NOT_INFERRED"}
ODDS_PROVIDER_ROLE = "ODDS_PROVIDER_OBJECT_NOT_SCOREBOARD_PROVENANCE"
UNAVAILABLE, INDETERMINATE, AVAILABLE = ("UNAVAILABLE_BEFORE_REQUEST_START", "INDETERMINATE_WITHIN_REQUEST_INTERVAL",
                                         "AVAILABLE_AT_OR_AFTER_REQUEST_END")
TIES_ZERO_RULE = "TWO_INTEGER_FORM_TIES_ZERO_BY_RULE"
TIES_STATED_RULE = "THREE_INTEGER_FORM_TIES_STATED"
#: Comparison families in refusal order (the first differing family names the refusal code).
FAMILIES = ("SCHEMA", "CONTRACT", "SOURCE", "OBSERVATION", "LABELS", "BUNDLE", "EVENT_MEMBERSHIP", "EVENT_IDENTITY",
            "EVENT_SEASON", "EVENT_SCHEDULE", "EVENT_STATUS", "EVENT_ROLES", "EVENT_SUPPORT", "PARTICIPANT_MEMBERSHIP",
            "PARTICIPANT_IDENTITY", "PARTICIPANT_RECORD", "PARTICIPANT_SUPPORT", "COUNTS", "CANONICAL_FORM")
EVENT_FIELDS = {"EVENT_IDENTITY": ("event_key", "source_event_id", "source_pointer", "competition_count",
                                   "competition_pointer", "source_competition_id"),
                "EVENT_SEASON": ("season_year", "season_type"),
                "EVENT_SCHEDULE": ("scheduled_utc", "scheduled_literal", "time_valid"),
                "EVENT_STATUS": ("event_status", "competition_status"),
                "EVENT_ROLES": ("home", "away"),
                "EVENT_SUPPORT": ("support_state", "unsupported_reasons")}
PARTICIPANT_FIELDS = {"PARTICIPANT_IDENTITY": ("event_key", "side", "team_key", "source_competitor_id",
                                               "source_team_id", "source_name", "participant_pointer"),
                      "PARTICIPANT_RECORD": ("record_pointer", "candidate_record_pointers", "overall_record"),
                      "PARTICIPANT_SUPPORT": ("support_state", "unsupported_reasons")}
EVENT_ID_RE = re.compile(r"^[0-9]{1,15}$")
TEAM_ID_RE = re.compile(r"^[0-9]{1,15}$")
EVENT_KEY_RE = re.compile(r"^espn:event:([0-9]{1,15})$")
TEAM_KEY_RE = re.compile(r"^espn:team:([0-9]{1,15})$")
SCHEDULE_RE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?Z$")
RECORD_TWO_RE = re.compile(r"^(0|[1-9][0-9]{0,2})-(0|[1-9][0-9]{0,2})$")
RECORD_THREE_RE = re.compile(r"^(0|[1-9][0-9]{0,2})-(0|[1-9][0-9]{0,2})-(0|[1-9][0-9]{0,2})$")
IDENTITY_RE = re.compile(r"^[0-9a-f]{64}$")
SUPPORTED, UNSUPPORTED = "SUPPORTED", "UNSUPPORTED"


class ProspectiveEvidenceError(base.SourceTimeQueryError):
    """A refused capsule or prospective query; ``code`` is a stable machine-readable reason."""


def canonical_bytes(value: object) -> bytes:
    """The frozen canonical serialization (sorted keys, compact separators, UTF-8, no ASCII escaping)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def capsule_file_bytes(document: dict[str, Any]) -> bytes:
    return canonical_bytes(document) + b"\n"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate member {key!r}")
        out[key] = value
    return out


def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-finite number {name}")


def strict_json(data: bytes, code: str) -> Any:
    """UTF-8 (no byte-order mark) JSON with no duplicate member and no NaN/Infinity, or a refusal under ``code``."""
    try:
        if data.startswith(b"\xef\xbb\xbf"):
            raise ValueError("byte-order mark")
        return json.loads(data.decode("utf-8"), object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProspectiveEvidenceError(code, str(exc)) from exc


def _iso_utc(value: _dt.datetime) -> str:
    return value.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _aware(text: Any, code: str, what: str) -> _dt.datetime:
    try:
        moment = _dt.datetime.fromisoformat(str(text))
    except ValueError as exc:
        raise ProspectiveEvidenceError(code, f"{what} {text!r} is not an ISO-8601 instant") from exc
    if moment.utcoffset() is None:
        raise ProspectiveEvidenceError(code, f"{what} {text!r} has no timezone")
    return moment.astimezone(_dt.timezone.utc)


# --------------------------------------------------------------------------------------------- derivation

def _status(node: Any) -> dict[str, Any] | None:
    kind = (node or {}).get("type") if isinstance(node, dict) else None
    if not isinstance(kind, dict):
        return None
    name, state, completed = kind.get("name"), kind.get("state"), kind.get("completed")
    if not isinstance(name, str) or not isinstance(state, str) or not isinstance(completed, bool):
        return None
    return {"name": name, "state": state, "completed": completed}


def _schedule(text: Any) -> _dt.datetime | None:
    if not isinstance(text, str):
        return None
    match = SCHEDULE_RE.match(text)
    if not match:
        return None
    year, month, day, hour, minute, second = match.groups()
    try:
        return _dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0),
                            tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def _int_value(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def derive_participant(event_key: str, event_index: int, competitor_index: int, competitor: Any) -> dict[str, Any]:
    """One participant record from its own competitor object and nothing else (TP51 section 3)."""
    reasons: list[str] = []
    pointer = f"/events/{event_index}/competitions/0/competitors/{competitor_index}"
    node = competitor if isinstance(competitor, dict) else {}
    if not isinstance(competitor, dict):
        reasons.append("PARTICIPANT_NOT_AN_OBJECT")
    competitor_id = node.get("id")
    team = node.get("team") if isinstance(node.get("team"), dict) else {}
    team_id = team.get("id")
    team_key = None
    if isinstance(competitor_id, str) and TEAM_ID_RE.match(competitor_id):
        team_key = f"espn:team:{competitor_id}"
    else:
        reasons.append("PARTICIPANT_ID_INVALID")
    if not isinstance(team_id, str) or team_id != competitor_id:
        reasons.append("TEAM_ID_DISAGREEMENT")
    side = node.get("homeAway")
    if side not in ("home", "away"):
        reasons.append("SIDE_INVALID")
    name = team.get("displayName")
    if not isinstance(name, str) or not name:
        reasons.append("SOURCE_NAME_MISSING")
        name = None
    records = node.get("records")
    candidates = []
    if isinstance(records, list):
        candidates = [k for k, row in enumerate(records)
                      if isinstance(row, dict) and row.get("name") == "overall" and row.get("type") == "total"]
    record, record_pointer = None, None
    if not candidates:
        reasons.append("RECORD_OVERALL_TOTAL_MISSING")
    elif len(candidates) > 1:
        reasons.append("RECORD_OVERALL_TOTAL_MULTIPLE")
    else:
        k = candidates[0]
        record_pointer = f"{pointer}/records/{k}"
        summary = records[k].get("summary")
        record = {"name": "overall", "type": "total", "summary": summary if isinstance(summary, str) else None,
                  "wins": None, "losses": None, "ties": None, "ties_rule": None}
        if not isinstance(summary, str):
            reasons.append("RECORD_SUMMARY_MISSING")
        else:
            two, three = RECORD_TWO_RE.match(summary), RECORD_THREE_RE.match(summary)
            if two:
                record.update(wins=int(two.group(1)), losses=int(two.group(2)), ties=0, ties_rule=TIES_ZERO_RULE)
            elif three:
                record.update(wins=int(three.group(1)), losses=int(three.group(2)), ties=int(three.group(3)),
                              ties_rule=TIES_STATED_RULE)
            else:
                reasons.append("RECORD_SUMMARY_MALFORMED")
    reasons = sorted(set(reasons))
    return {"event_key": event_key, "side": side if isinstance(side, str) else None, "team_key": team_key,
            "source_competitor_id": competitor_id if isinstance(competitor_id, str) else None,
            "source_team_id": team_id if isinstance(team_id, str) else None, "source_name": name,
            "participant_pointer": pointer, "record_pointer": record_pointer,
            "candidate_record_pointers": [f"{pointer}/records/{k}" for k in candidates],
            "overall_record": record, "support_state": UNSUPPORTED if reasons else SUPPORTED,
            "unsupported_reasons": reasons}


def derive_event(event_index: int, event: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """One event record and its participant records from the event's own raw fields (TP51 section 3)."""
    if not isinstance(event, dict):
        raise ProspectiveEvidenceError("RAW_EVENT_INVALID", f"/events/{event_index} is not an object")
    source_id = event.get("id")
    if not isinstance(source_id, str) or not EVENT_ID_RE.match(source_id):
        raise ProspectiveEvidenceError("RAW_EVENT_ID_INVALID", f"/events/{event_index}/id is {source_id!r}")
    key = f"espn:event:{source_id}"
    reasons: list[str] = []
    competitions = event.get("competitions") if isinstance(event.get("competitions"), list) else []
    competition = competitions[0] if len(competitions) == 1 and isinstance(competitions[0], dict) else None
    if competition is None:
        reasons.append("COMPETITION_COUNT_NOT_ONE")
    season = event.get("season") if isinstance(event.get("season"), dict) else {}
    year, season_type = _int_value(season.get("year")), _int_value(season.get("type"))
    if year is None:
        reasons.append("SEASON_YEAR_INVALID")
    if season_type is None:
        reasons.append("SEASON_TYPE_INVALID")
    comp = competition or {}
    competition_id = comp.get("id") if isinstance(comp.get("id"), str) else None
    if competition is not None and competition_id is None:
        reasons.append("COMPETITION_ID_INVALID")
    event_date, comp_date = event.get("date"), comp.get("date")
    literal = {"event_date": event_date if isinstance(event_date, str) else None,
               "competition_date": comp_date if isinstance(comp_date, str) else None}
    time_valid = comp.get("timeValid") if isinstance(comp.get("timeValid"), bool) else None
    scheduled = None
    event_instant, comp_instant = _schedule(event_date), _schedule(comp_date)
    if event_instant is None or (competition is not None and comp_instant is None):
        reasons.append("SCHEDULED_TIME_NO_VALID_ZONE")
    elif competition is not None and event_instant != comp_instant:
        reasons.append("EVENT_COMPETITION_DATE_CONTRADICTION")
    elif time_valid is None:
        reasons.append("TIME_VALID_MISSING")
    elif time_valid is not True:
        reasons.append("SCHEDULED_TIME_NOT_VALID_PER_SOURCE")
    elif competition is not None:
        scheduled = event_instant.strftime("%Y-%m-%dT%H:%M:%SZ")
    event_status, comp_status = _status(event.get("status")), _status(comp.get("status"))
    if event_status is None or (competition is not None and comp_status is None):
        reasons.append("STATUS_MISSING")
    elif competition is not None and event_status != comp_status:
        reasons.append("EVENT_COMPETITION_STATUS_CONTRADICTION")
    competitors = comp.get("competitors") if isinstance(comp.get("competitors"), list) else []
    participants = [derive_participant(key, event_index, j, c) for j, c in enumerate(competitors)]
    roles: dict[str, dict[str, Any] | None] = {"home": None, "away": None}
    if competition is not None:
        if len(competitors) != 2:
            reasons.append("COMPETITOR_COUNT_NOT_TWO")
        if any(p["side"] not in ("home", "away") for p in participants):
            reasons.append("ROLE_VALUE_INVALID")
        for side in ("home", "away"):
            matched = [p for p in participants if p["side"] == side]
            if not matched:
                reasons.append(f"ROLE_{side.upper()}_MISSING")
            elif len(matched) > 1:
                reasons.append(f"ROLE_{side.upper()}_DUPLICATE")
            elif matched[0]["team_key"] is None:
                reasons.append(f"ROLE_{side.upper()}_ID_INVALID")
        if not any(r.startswith(("ROLE_", "COMPETITOR_COUNT")) for r in reasons):
            for side in ("home", "away"):
                p = next(x for x in participants if x["side"] == side)
                roles[side] = {"team_key": p["team_key"], "source_name": p["source_name"],
                               "participant_pointer": p["participant_pointer"]}
    reasons = sorted(set(reasons))
    record = {"event_key": key, "source_event_id": source_id, "source_pointer": f"/events/{event_index}",
              "competition_count": len(competitions),
              "competition_pointer": f"/events/{event_index}/competitions/0" if competition is not None else None,
              "source_competition_id": competition_id, "season_year": year, "season_type": season_type,
              "scheduled_utc": scheduled, "scheduled_literal": literal, "time_valid": time_valid,
              "event_status": event_status, "competition_status": comp_status,
              "home": roles["home"], "away": roles["away"],
              "support_state": UNSUPPORTED if reasons else SUPPORTED, "unsupported_reasons": reasons}
    return record, participants


def _participant_order(p: dict[str, Any]) -> tuple[str, str, str, str]:
    return (p["event_key"], p["team_key"] or "", p["side"] or "", p["participant_pointer"])


def _membership_tuple(p: dict[str, Any]) -> list[Any]:
    return [p["event_key"], p["side"], p["team_key"]]


def _sorted_tuples(rows: Iterable[list[Any]]) -> list[list[Any]]:
    """Membership tuples in a total order (a null side or team sorts as the empty string; values stay null)."""
    return sorted(rows, key=lambda t: [("" if x is None else str(x)) for x in t])


def _hash_chunks(data: bytes, chunk_size: int) -> str:
    digest = hashlib.sha256()
    for start in range(0, len(data), max(1, chunk_size)):
        digest.update(data[start:start + max(1, chunk_size)])
    return digest.hexdigest()


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
    raise ProspectiveEvidenceError("PROCESSING_ORDER_INVALID", f"unknown processing order {order!r}")


def derive(raw: bytes, receipt: bytes, expected: bytes, contract: bytes, *, contract_sha256: str = CONTRACT_SHA256,
           order: str | None = None, chunk_size: int = 1 << 20) -> dict[str, Any]:
    """The complete expected capsule document from the four authority inputs (never a supplied summary)."""
    if _hash_chunks(contract, chunk_size) != contract_sha256:
        raise ProspectiveEvidenceError("CONTRACT_NOT_COMMITTED_AUTHORITY",
                                       f"the bundled contract hashes to {sha256_hex(contract)}, not the committed "
                                       f"{contract_sha256}")
    spec = strict_json(contract, "CONTRACT_MALFORMED")
    try:
        pins = spec["source"]
        raw_pin, receipt_pin, expected_pin = pins["raw_sha256"], pins["receipt_sha256"], pins["expected_cohort_sha256"]
        member_events = spec["membership"]["event_keys"]
        member_participants = spec["membership"]["participants"]
        endpoint = pins["endpoint"]
        provider = pins["provider"]
    except (KeyError, TypeError) as exc:
        raise ProspectiveEvidenceError("CONTRACT_MALFORMED", f"missing contract member {exc}") from exc
    if spec.get("contract_id") != CONTRACT_ID or spec.get("population_id") != POPULATION:
        raise ProspectiveEvidenceError("CONTRACT_MALFORMED", "the contract is not the prospective observation contract")
    raw_sha = _hash_chunks(raw, chunk_size)
    if raw_sha != raw_pin:
        raise ProspectiveEvidenceError("RAW_NOT_PINNED_ORIGINAL", f"the raw response hashes to {raw_sha}, the contract "
                                                                  f"pins {raw_pin}")
    receipt_sha = _hash_chunks(receipt, chunk_size)
    if receipt_sha != receipt_pin:
        raise ProspectiveEvidenceError("RECEIPT_NOT_PINNED_ORIGINAL", f"the receipt hashes to {receipt_sha}, the "
                                                                      f"contract pins {receipt_pin}")
    expected_sha = _hash_chunks(expected, chunk_size)
    if expected_sha != expected_pin:
        raise ProspectiveEvidenceError("COHORT_NOT_PINNED_ORIGINAL", f"the cohort hashes to {expected_sha}, the "
                                                                     f"contract pins {expected_pin}")
    rec = strict_json(receipt, "RECEIPT_MALFORMED")
    cohort = strict_json(expected, "COHORT_MALFORMED")
    try:
        headers = rec["headers"]
        start = _aware(rec["started"], "RECEIPT_INVALID", "request start")
        end = _aware(rec["ended"], "RECEIPT_INVALID", "request end")
        server = _dt.datetime.strptime(headers["Date"], "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=_dt.timezone.utc)
        receipt_ok = (rec["status"] == 200 and rec["requests"] == 1 and rec["sha256"] == raw_sha and
                      rec["bytes"] == len(raw) and rec["url"] == endpoint and start < end and
                      start.replace(microsecond=0) <= server <= end.replace(microsecond=0) + _dt.timedelta(seconds=1))
        cohort_ok = cohort["source_sha256"] == raw_sha and cohort["receipt_sha256"] == receipt_sha
    except (KeyError, TypeError, ValueError) as exc:
        raise ProspectiveEvidenceError("RECEIPT_INVALID", f"the receipt or cohort lacks a required fact: {exc}") from exc
    if not receipt_ok:
        raise ProspectiveEvidenceError("RECEIPT_INVALID", "the receipt is not one HTTP 200 request for exactly these "
                                                          "bytes within an ordered interval agreeing with its Date")
    if not cohort_ok:
        raise ProspectiveEvidenceError("COHORT_INVALID", "the cohort does not name this raw response and receipt")
    doc = strict_json(raw, "RAW_MALFORMED")
    events = doc.get("events") if isinstance(doc, dict) else None
    if not isinstance(events, list):
        raise ProspectiveEvidenceError("RAW_MALFORMED", "the raw response has no events list")
    event_rows: list[dict[str, Any]] = []
    participant_rows: list[dict[str, Any]] = []
    for index in processing_order(len(events), order):
        record, participants = derive_event(index, events[index])
        event_rows.append(record)
        participant_rows.extend(participants)
    event_rows.sort(key=lambda r: r["event_key"])
    participant_rows.sort(key=_participant_order)
    keys = [r["event_key"] for r in event_rows]
    if keys != sorted(member_events) or len(set(keys)) != len(keys):
        raise ProspectiveEvidenceError("COHORT_MEMBERSHIP_MISMATCH", "the raw event keys differ from the contract's "
                                                                     "frozen event membership")
    try:
        tuples = _sorted_tuples(_membership_tuple(p) for p in participant_rows)
        wanted = _sorted_tuples([p["event_key"], p["side"], p["team_key"]] for p in member_participants)
        frozen = _sorted_tuples([p.get("event_key"), p.get("side"), p.get("team_key")]
                                for p in cohort.get("participants") or [])
        frozen_keys = sorted(cohort.get("event_keys") or [])
    except (KeyError, TypeError, AttributeError) as exc:
        raise ProspectiveEvidenceError("COHORT_MEMBERSHIP_MISMATCH", f"malformed membership: {exc}") from exc
    if tuples != wanted:
        raise ProspectiveEvidenceError("COHORT_MEMBERSHIP_MISMATCH", "the raw participants differ from the contract's "
                                                                     "frozen participant membership")
    if frozen_keys != keys or frozen != tuples:
        raise ProspectiveEvidenceError("COHORT_MEMBERSHIP_MISMATCH", "the frozen cohort membership differs")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(endpoint).query, keep_blank_values=True)
    odds = doc.get("provider") if isinstance(doc.get("provider"), dict) else None
    reasons: dict[str, int] = {}
    for row in event_rows + participant_rows:
        for reason in row["unsupported_reasons"]:
            reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "schema": SCHEMA, "population": POPULATION, "contract": {"id": CONTRACT_ID, "sha256": contract_sha256},
        "source": {"provider": provider, "endpoint": endpoint,
                   "request_parameters": {k: v for k, v in sorted(query.items())},
                   "http_status": rec["status"], "request_count": rec["requests"],
                   "content_type": headers.get("Content-Type"), "server_date_header": headers["Date"],
                   "server_date_utc": server.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "body_sha256": raw_sha, "body_bytes": len(raw), "receipt_sha256": receipt_sha,
                   "odds_provider_object": None if odds is None else {
                       "pointer": "/provider", "id": odds.get("id") if isinstance(odds.get("id"), str) else None,
                       "name": odds.get("name") if isinstance(odds.get("name"), str) else None,
                       "role": ODDS_PROVIDER_ROLE}},
        "observation": {"request_start_utc": _iso_utc(start), "request_end_utc": _iso_utc(end),
                        "unavailable_before_utc": _iso_utc(start), "available_at_or_after_utc": _iso_utc(end),
                        "indeterminate_interval": [_iso_utc(start), _iso_utc(end)],
                        "first_publication": "NOT_INFERRED",
                        "snapshot_refresh": "NONE_A_LATER_CUTOFF_DOES_NOT_REFRESH_THIS_SNAPSHOT"},
        "labels": dict(LABELS),
        "bundle": {BUNDLE["raw"]: {"sha256": raw_sha, "bytes": len(raw)},
                   BUNDLE["receipt"]: {"sha256": receipt_sha, "bytes": len(receipt)},
                   BUNDLE["expected"]: {"sha256": expected_sha, "bytes": len(expected)},
                   BUNDLE["contract"]: {"sha256": contract_sha256, "bytes": len(contract)}},
        "events": event_rows, "participants": participant_rows,
        "counts": {"events": len(event_rows), "participants": len(participant_rows),
                   "supported_events": sum(r["support_state"] == SUPPORTED for r in event_rows),
                   "unsupported_events": sum(r["support_state"] == UNSUPPORTED for r in event_rows),
                   "supported_participants": sum(r["support_state"] == SUPPORTED for r in participant_rows),
                   "unsupported_participants": sum(r["support_state"] == UNSUPPORTED for r in participant_rows),
                   "unsupported_reasons": dict(sorted(reasons.items()))}}


def identity_document(document: dict[str, Any]) -> dict[str, Any]:
    """The identity document: the capsule file hash, the bundle member hashes and the contract (no other member)."""
    return {"schema": IDENTITY_SCHEMA, "population": POPULATION, "contract_id": CONTRACT_ID,
            "contract_sha256": document["contract"]["sha256"], "capsule_file": CAPSULE_FILE,
            "capsule_sha256": sha256_hex(capsule_file_bytes(document)), "bundle": document["bundle"]}


def capsule_identity(document: dict[str, Any]) -> str:
    return sha256_hex(canonical_bytes(identity_document(document)))


# --------------------------------------------------------------------------------------------- comparison

def first_difference(expected: dict[str, Any], actual: Any) -> tuple[str, str] | None:
    """The first governed difference between the re-derived document and a supplied capsule, by family order; the
    comparison of every governed value is by its canonical serialized bytes (so 25, 25.0 and true differ)."""
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
    for family, member in (("CONTRACT", "contract"), ("SOURCE", "source"), ("OBSERVATION", "observation"),
                           ("LABELS", "labels"), ("BUNDLE", "bundle")):
        if not same(expected[member], actual[member]):
            return family, f"{member} differs"
    for name, key, fields, membership in (
            ("EVENT", "events", EVENT_FIELDS, lambda r: r.get("event_key") if isinstance(r, dict) else None),
            ("PARTICIPANT", "participants", PARTICIPANT_FIELDS,
             lambda r: [r.get("event_key"), r.get("side"), r.get("team_key"), r.get("participant_pointer")]
             if isinstance(r, dict) else None)):
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
    if not same(expected["counts"], actual["counts"]):
        return "COUNTS", "counts differ"
    return None


# --------------------------------------------------------------------------------------------- reader

def literal_location(path: Path | str) -> str:
    try:
        return readonly_sqlite.literal_path(path)
    except readonly_sqlite.DatabaseLocationError as exc:
        code = {readonly_sqlite.LOCATION_UNSUPPORTED: "EVIDENCE_LOCATION_UNSUPPORTED",
                readonly_sqlite.LOCATION_NOT_LITERAL: "EVIDENCE_LOCATION_NOT_LITERAL"}.get(exc.code, exc.code)
        raise ProspectiveEvidenceError(code, exc.detail) from exc


def _read(path: str, code: str) -> bytes:
    if not os.path.isfile(path):
        raise ProspectiveEvidenceError(code, f"no file at {path}")
    with open(path, "rb") as handle:
        return handle.read()


def verify_capsule(path: Path | str, *, contract_sha256: str = CONTRACT_SHA256,
                   expect_identity: str | None = None) -> dict[str, Any]:
    """Verify a capsule bundle completely and return its binding plus the re-derived (verified) document."""
    location = literal_location(path)
    if not os.path.isfile(location):
        raise ProspectiveEvidenceError("EVIDENCE_MISSING", f"no capsule file at {location}")
    directory, name = os.path.split(location)
    if name != CAPSULE_FILE or not IDENTITY_RE.match(os.path.basename(directory)):
        raise ProspectiveEvidenceError("EVIDENCE_LOCATION_INVALID", f"the capsule must be <identity>/{CAPSULE_FILE} "
                                                                    "with a 64-hex identity directory")
    members = {role: _read(os.path.join(directory, *rel.split("/")), "BUNDLE_MEMBER_MISSING")
               for role, rel in BUNDLE.items()}
    expected = derive(members["raw"], members["receipt"], members["expected"], members["contract"],
                      contract_sha256=contract_sha256)
    want = capsule_file_bytes(expected)
    got = _read(location, "EVIDENCE_MISSING")
    if got != want:
        supplied = strict_json(got, "CAPSULE_MALFORMED")
        diff = first_difference(expected, supplied)
        family, detail = diff if diff else ("CANONICAL_FORM", "the capsule bytes are not the frozen canonical form")
        raise ProspectiveEvidenceError(f"CAPSULE_{family}_MISMATCH", detail)
    identity = capsule_identity(expected)
    if os.path.basename(directory) != identity:
        raise ProspectiveEvidenceError("CAPSULE_IDENTITY_MISMATCH", f"the identity document hashes to {identity}, the "
                                                                    f"directory is {os.path.basename(directory)}")
    if expect_identity is not None and expect_identity != identity:
        raise ProspectiveEvidenceError("STALE_CAPSULE_IDENTITY", f"expected {expect_identity}, found {identity}")
    return {"capsule_identity": identity, "capsule_sha256": sha256_hex(got), "location": location,
            "identity_document": identity_document(expected), "document": expected}


def observation_at(cutoff: _dt.datetime, observation: dict[str, Any]) -> tuple[str, str]:
    start = _dt.datetime.strptime(observation["request_start_utc"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
        tzinfo=_dt.timezone.utc)
    end = _dt.datetime.strptime(observation["request_end_utc"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
        tzinfo=_dt.timezone.utc)
    if cutoff < start:
        return UNAVAILABLE, "CUTOFF_BEFORE_RETAINED_REQUEST_START"
    if cutoff < end:
        return INDETERMINATE, "CUTOFF_WITHIN_RETAINED_REQUEST_INTERVAL"
    return AVAILABLE, "CUTOFF_AT_OR_AFTER_RETAINED_REQUEST_END"


def normalize_event(value: str) -> str:
    if not isinstance(value, str) or not EVENT_KEY_RE.match(value):
        raise ProspectiveEvidenceError("EVENT_KEY_INVALID", f"event must be espn:event:<digits>, got {value!r}")
    return value


def normalize_provider_team(value: str) -> str:
    if not isinstance(value, str) or not TEAM_KEY_RE.match(value):
        raise ProspectiveEvidenceError("TEAM_KEY_INVALID", f"team must be espn:team:<digits>, got {value!r}")
    return value


class ProspectiveEvidence:
    """A completely verified capsule; rows come only from its re-derived document."""

    def __init__(self, path: Path | str, *, contract_sha256: str = CONTRACT_SHA256,
                 expect_identity: str | None = None) -> None:
        self.binding = verify_capsule(path, contract_sha256=contract_sha256, expect_identity=expect_identity)
        self.document = self.binding["document"]

    def __enter__(self) -> "ProspectiveEvidence":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def query(self, grain: str, *, cutoff: str | None = None, season: int | None = None, event: str | None = None,
              team: str | None = None, limit: int | None = 50, offset: int = 0,
              all_rows: bool = False) -> dict[str, Any]:
        if grain not in GRAINS:
            raise ProspectiveEvidenceError("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}")
        if offset < 0:
            raise ProspectiveEvidenceError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise ProspectiveEvidenceError("NEGATIVE_LIMIT", "limit must be zero or positive")
        filters: dict[str, Any] = {}
        if season is not None:
            if isinstance(season, bool) or not isinstance(season, int):
                raise ProspectiveEvidenceError("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if event is not None:
            filters["event"] = normalize_event(event)
        if team is not None:
            filters["team"] = normalize_provider_team(team)
        when = base.parse_cutoff(cutoff)
        state, reason = observation_at(when, self.document["observation"])
        doc = self.document
        result: dict[str, Any] = {
            "capsule_identity": self.binding["capsule_identity"], "contract_id": CONTRACT_ID,
            "contract_sha256": doc["contract"]["sha256"], "population": POPULATION, "grain": grain,
            "filters": filters, "cutoff": {"literal": cutoff, "utc": base._fmt(when)}, "offset": offset,
            "limit": None if all_rows else limit, "observation": doc["observation"],
            "observation_at_cutoff": {"state": state, "reason": reason}, "labels": doc["labels"],
            "source": {"provider": doc["source"]["provider"], "endpoint": doc["source"]["endpoint"],
                       "body_sha256": doc["source"]["body_sha256"],
                       "odds_provider_object": doc["source"]["odds_provider_object"]}}
        if season is not None and season != SEASON:
            result.update(season_scope_state=OUT_OF_SCOPE_STATE, total=0, returned=0, rows=[], next_offset=None,
                          note="only the retained 2026 provider observation is audited; no row is fabricated")
            return result
        if grain == "prospective-event":
            items = [r for r in doc["events"] if self._event_matches(r, filters)]
            wrap = self._event_row
        else:
            seasons = {r["event_key"]: r["season_year"] for r in doc["events"]}
            items = [p for p in doc["participants"] if (filters.get("event") in (None, p["event_key"]) and
                                                       filters.get("team") in (None, p["team_key"]) and
                                                       ("season" not in filters or
                                                        seasons.get(p["event_key"]) == filters["season"]))]
            wrap = self._participant_row
        total = len(items)
        stop = None if all_rows else offset + (limit or 0)
        rows = [wrap(item, state) for item in items[offset:stop]]
        result.update(season_scope_state=IN_SCOPE_STATE, total=total, returned=len(rows), rows=rows,
                      next_offset=offset + len(rows) if offset + len(rows) < total else None)
        return result

    @staticmethod
    def _event_matches(record: dict[str, Any], filters: dict[str, Any]) -> bool:
        if "season" in filters and record["season_year"] != filters["season"]:
            return False
        if "event" in filters and record["event_key"] != filters["event"]:
            return False
        if "team" in filters:
            keys = {(record.get(side) or {}).get("team_key") for side in ("home", "away")}
            return filters["team"] in keys
        return True

    def _common(self, state: str) -> dict[str, Any]:
        doc = self.document
        return {"observation_at_cutoff": state, "labels": doc["labels"],
                "observation_interval": [doc["observation"]["request_start_utc"],
                                         doc["observation"]["request_end_utc"]],
                "source_body_sha256": doc["source"]["body_sha256"]}

    def _event_row(self, record: dict[str, Any], state: str) -> dict[str, Any]:
        return {"event": record, **self._common(state)}

    def _participant_row(self, record: dict[str, Any], state: str) -> dict[str, Any]:
        return {"participant": record, **self._common(state)}


# --------------------------------------------------------------------------------------------- build helpers

def bundle_files(raw: bytes, receipt: bytes, expected: bytes, contract: bytes) -> dict[str, bytes]:
    return {BUNDLE["raw"]: raw, BUNDLE["receipt"]: receipt, BUNDLE["expected"]: expected,
            BUNDLE["contract"]: contract}


def build_capsule(raw: bytes, receipt: bytes, expected: bytes, contract: bytes, *,
                  contract_sha256: str = CONTRACT_SHA256, order: str | None = None,
                  chunk_size: int = 1 << 20) -> tuple[str, dict[str, bytes], dict[str, Any]]:
    """The identity, the complete set of files of the capsule directory and the identity document."""
    document = derive(raw, receipt, expected, contract, contract_sha256=contract_sha256, order=order,
                      chunk_size=chunk_size)
    files = {CAPSULE_FILE: capsule_file_bytes(document), **bundle_files(raw, receipt, expected, contract)}
    return capsule_identity(document), files, identity_document(document)


__all__ = ["ProspectiveEvidence", "ProspectiveEvidenceError", "build_capsule", "capsule_identity", "derive",
           "first_difference", "identity_document", "verify_capsule", "CONTRACT_SHA256", "GRAINS"]
