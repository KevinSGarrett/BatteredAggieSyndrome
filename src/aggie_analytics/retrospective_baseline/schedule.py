r"""Explicit immutable official schedule evidence sidecar for the frozen October 17 shadow cohort (BAT-726; TP54-A01).

``bas-retrospective-baseline-query --prospective-shadow <...provider_record_shadow_20261017\sha256\<id>\snapshot.json>
--schedule-evidence <...official_shadow_schedule_20261017\sha256\<identity>\schedule.json>
--grain shadow-schedule|shadow-schedule-source --cutoff <instant with zone> [--season 2026] [--event espn:event:<id>]
[--team espn:team:<id>] [--limit 50] [--offset 0] [--all]``

One private, create-only, content-addressed sidecar holds the complete bounded acquisition of official 2026 football
schedule pages for all 25 events of the accepted BAT-725 UNTRUSTED_SHADOW snapshot: the exact acquisition journal (every
HTTP attempt, redirect hop, failure, stop and zero-request decision with its UTC interval and monotonic spacing), every
retained raw response body, the committed contract and ``schedule.json``, the per-event and per-request evidence the
reader re-derives from those bytes. The route for each event is the official athletics host family of the institution
the frozen provider names as home (selected once per event from the retained NCAA directory); that selection is not
proof of the official home role.

Each event keeps both sides: the frozen provider claims (scheduled instant, home/away keys, neutral flag, venue, names)
and the official observations, never overwriting either. Official values come only from a declared record structure's
own members (:data:`STRUCTURES`): SIDEARM season schedule records in the page's own Nuxt payload, the SIDEARM text-page
season table, and WMT season schedule list records. A document binds football season 2026 only through its own season
field; the institution only through its own team-name field equal to a frozen provider home name (or the NCAA official
name); the opponent only through a record's own opponent field equal to a frozen provider away name (display, short or
location name; never an abbreviation, mascot, number or fuzzy match). Opponent, event date, the owner's home/away or
neutral designation, venue and scheduled time are qualified separately; repeated equal witnesses support a value,
differing witnesses keep a CONFLICTING state with every value, and a record of the opponent on another date is a
retained date conflict, never borrowed. A scheduled instant is computed only from an explicit offset/Z or a stated US
zone designator bound to that event's own time field; naive local times, TBA and ambiguous designators stay as such.
Every scheduled instant is an OFFICIAL_SCHEDULE_CLAIM, never an actual kickoff.

Observations are LOCAL_CAPTURE_OBSERVATION bounds: the sidecar's availability bound is the maximum response end time of
all its attempts, re-derived from the journal. ``--cutoff`` is required; before that bound the sidecar is refused, at or
after it the same immutable evidence is served (nothing is refreshed and the current clock is never read). The bound is
later than the shadow anchor: no evidence is retroactively as of that anchor and the shadow's PRE_PROVIDER_REPORTED_START
claim and its 100 predictions are unchanged. Every served row carries UNTRUSTED_SHADOW, PIT_NOT_ADMITTED,
PREDICTIVE_SKILL_NOT_ESTABLISHED, SCHEDULE_NOT_ACTUAL_KICKOFF, CURRENT_OBSERVATION_NOT_ORIGINAL_PUBLICATION and
NO_RETROACTIVE_ANCHOR_AUTHORITY with national coverage UNKNOWN; ``--require-pit`` is always refused.

Before any row is served the reader verifies the selected shadow with the accepted BAT-725 reader, the committed
contract (:data:`CONTRACT_SHA256`), the exact bundle membership, every raw body against the journal, the journal against
the acquisition grant, re-derives ``schedule.json`` and compares it by canonical bytes (integer, float, boolean and
string identities differ; the first differing family names the refusal), recomputes the identity and finally requires
the sidecar pinned by the packaged gate (:data:`SCHEDULE_PROFILE`). Imported only when ``--schedule-evidence`` is named.
"""
from __future__ import annotations

import datetime as _dt
import gzip
import html
import html.parser
import json
import os
import random
import re
import urllib.parse
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics.retrospective_baseline import preview as pv
from aggie_analytics.retrospective_baseline import shadow as sh

SCHEMA = "BAS-OFFICIAL-SHADOW-SCHEDULE-1"
IDENTITY_SCHEMA = "BAS-OFFICIAL-SHADOW-SCHEDULE-IDENTITY-1"
JOURNAL_SCHEMA = "BAS-OFFICIAL-SCHEDULE-ACQUISITION-JOURNAL-1"
POPULATION = "official_shadow_schedule_20261017"
CONTRACT_ID = "BAT-726-OFFICIAL-SHADOW-SCHEDULE-20261017-V1"
#: SHA-256 of the committed contract ``configs/official_shadow_schedule_20261017_contract.json`` (the authority anchor;
#: a test requires it to equal the committed file).
CONTRACT_SHA256 = "ac521dc513f39ec247cc88324420c02fae3f3140874ef8de5bfe8ea518dd35e2"
SCHEDULE_FILE = "schedule.json"
CONTRACT_MEMBER = "inputs/contract.json"
JOURNAL_PREFIX = "acquisition/journal-"
RAW_PREFIX = "raw/"
SEASON = 2026
GRAINS = ("shadow-schedule", "shadow-schedule-source")
GRAIN_KEY = {"shadow-schedule": "schedule", "shadow-schedule-source": "source"}
APPLICABLE = ("season", "event", "team")
OUT_OF_SCOPE_STATE = "NOT_YET_AUDITED"
IN_SCOPE_STATE = "PROSPECTIVE_2026_OFFICIAL_SCHEDULE_OBSERVATION_SIDECAR"
AVAILABLE_STATE = "AVAILABLE_AT_OR_AFTER_OBSERVATION_BOUND"
DESIGNATION = "UNTRUSTED_SHADOW"

#: The accepted shadow the committed contract binds (TP54 section 1; the reader takes the binding from the hash-pinned
#: contract and verifies the selected snapshot with the accepted BAT-725 reader).
PRODUCTION_SHADOW = {
    "population": sh.POPULATION,
    "identity": "174f08610d5ab9a1f49a7c8e67b8a3540ebc0b7dece68e5988d677aa20faaf3e",
    "snapshot_sha256": "d5169fdd72b44bfc577178aa4243cbce3466695c8c638964bed95164dc360a4f",
    "payload_sha256": "fe4c96bcb7f010bf5c10a308cfd26963a58513a7715a8b84dbff0661af047bcb",
    "contract_sha256": sh.CONTRACT_SHA256,
}

#: Labels carried by schedule.json and every served response (equal to the committed contract's ``labels``).
LABELS = {
    "designation": "UNTRUSTED_SHADOW",
    "claim_class": "OFFICIAL_SCHEDULE_CLAIM",
    "schedule_authority": "SCHEDULE_NOT_ACTUAL_KICKOFF",
    "observation_authority": "CURRENT_OBSERVATION_NOT_ORIGINAL_PUBLICATION",
    "observation_clock": "LOCAL_CAPTURE_OBSERVATION",
    "anchor_authority": "NO_RETROACTIVE_ANCHOR_AUTHORITY",
    "pit_admission": "PIT_NOT_ADMITTED",
    "predictive_skill": "PREDICTIVE_SKILL_NOT_ESTABLISHED",
    "national_coverage": "UNKNOWN",
    "route_selection": "PROVIDER_HOME_INSTITUTION_ROUTE_NOT_PROOF_OF_OFFICIAL_HOME_ROLE",
    "predictions": "FROZEN_SHADOW_PREDICTIONS_UNCHANGED_NOT_REEVALUATED",
    "outcomes": "NO_OUTCOME_EXTRACTED_SCORED_OR_USED",
    "selection": "EXPLICIT_SIDECAR_SELECTION_ONLY_NEVER_A_DEFAULT",
}
#: Labels carried by every event record, source record and served row (equal to the contract's ``record_labels``).
RECORD_LABELS = {
    "designation": LABELS["designation"], "claim_class": LABELS["claim_class"],
    "schedule_authority": LABELS["schedule_authority"], "observation_authority": LABELS["observation_authority"],
    "anchor_authority": LABELS["anchor_authority"], "pit_admission": LABELS["pit_admission"],
    "predictive_skill": LABELS["predictive_skill"], "national_coverage": LABELS["national_coverage"],
}
NUMERIC_CONTRACT = {
    "integers": "JSON integers only; a boolean or an integral float is not an integer; no binary float appears in "
                "schedule.json, the identity document or a served row",
    "identities": "event, team, organization and request identities are JSON strings or integers exactly as frozen; "
                  "an integer, float, boolean or string in another's place is a different value and is refused",
    "instants": "UTC instants are strings YYYY-MM-DDTHH:MM:SS.ffffffZ; local dates YYYY-MM-DD; local times HH:MM",
    "monotonic": "journal monotonic stamps are integer nanoseconds (time.perf_counter_ns); spacing is their difference",
    "canonical_json": "json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) "
                      "as UTF-8; schedule.json is these bytes plus one LF",
    "raw_bodies": "raw/<sha256 of the exact body>.gz holds gzip.compress(body, mtime=0) of the exact received bytes",
}

#: TP54 section 2: the bounded public source grant (one cumulative counter across restarts and journal segments).
ACQUISITION = {
    "ceiling_attempts": 80,
    "counting": "every HTTP attempt: each redirect hop, failure, error, truncated and interrupted attempt counts",
    "method": "anonymous public GET; no credential, cookie replay, login, paid tool, archive, search API or crawl",
    "hosts": "only the selected owner institution's official athletics host family (bare and www forms of the NCAA "
             "directory athletics host)",
    "stop_statuses": [401, 403, 429, 451],
    "stop_rule": "a host family answering a stop status is stopped for the rest of the attempt (no retry, no "
                 "circumvention, no resumption); other host families may continue",
    "redirect_statuses": [301, 302, 303, 307, 308],
    "max_hops": 5,
    "redirect_rule": "a redirect is followed only to its Location inside the same host family; a Location outside the "
                     "family is recorded (REDIRECT_OUTSIDE_FAMILY_NOT_FOLLOWED) and not followed",
    "max_body_bytes": 12 * 1024 * 1024,
    "timeout_seconds": 60,
    "min_spacing_ns": 2_000_000_000,
    "spacing_rule": "at least 2 seconds between the starts of any two attempts, measured by the monotonic clock "
                    "(stricter than per host); no polling and no sleep on Retry-After",
    "retention": "every attempt keeps its URL, hop, status, headers, body digest/length, UTC start/end and raw bytes; "
                 "failed, stopped, redirected-outside, truncated, absent and ambiguous outcomes stay distinct",
}
ROUTES = {
    "INITIAL_SEASON_ROUTE": "https://<host family member>/sports/football/schedule/2026 (stage 1, every event)",
    "LINKED_SEASON_ROUTE": "an explicit same-family href found in a retained body of an earlier attempt of the same "
                           "event whose path has a 'schedule' segment, a 'football' or 'm-footbl' segment and a '2026' "
                           "segment (stage 2, only when no earlier document of the event qualified)",
    "LANDING_ROUTE": "https://<directory host>/sports/football/schedule (stage 3, only when no earlier document of the "
                     "event qualified)",
}
ROUTE_ORDER = ("INITIAL_SEASON_ROUTE", "LINKED_SEASON_ROUTE", "LANDING_ROUTE")
DECISIONS = ("NOT_REQUESTED_HOST_STOPPED", "NOT_REQUESTED_BUDGET_EXHAUSTED", "REDIRECT_OUTSIDE_FAMILY_NOT_FOLLOWED",
             "REDIRECT_LIMIT_REACHED")
REQUEST_OUTCOMES = ("RETAINED_200", "FAILED_HTTP", "FAILED_NO_RESPONSE", "HOST_STOPPED_HTTP", "TRUNCATED_BODY",
                    "REDIRECT_OUTSIDE_FAMILY_NOT_FOLLOWED", "REDIRECT_LIMIT_REACHED", "INTERRUPTED",
                    "NOT_REQUESTED_HOST_STOPPED", "NOT_REQUESTED_BUDGET_EXHAUSTED")

#: The declared record structures (TP54 section 2; frozen from the two retained manager structure probes before the
#: capture). Anything else in a page (other views, JSON-LD, widgets, navigation, titles) is retained as raw bytes only.
STRUCTURES = {
    "SIDEARM_NUXT_SCHEDULE": {
        "element": "the single <script id=\"__NUXT_DATA__\"> element: a devalue payload (every object member is an "
                   "index into the payload array; Reactive/ShallowReactive/Ref/ShallowRef wrappers unwrapped)",
        "season_record": "each value of pinia.schedule.schedules whose own sport.shortname is 'football'",
        "season_binding": "the record's own season.title equals '2026'",
        "owner_name": "the record's own school_name",
        "records": "the record's own games list",
        "members": {"event_date": "date (local date part)", "local_time": "date (time part, only when tbd is false)",
                    "time_text": "time", "tba": "tbd (true)", "designation": "location_indicator H/A/N",
                    "opponent": "opponent.title", "facility": "facility.title", "location": "location"},
    },
    "SIDEARM_TEXT_TABLE": {
        "element": "the <table> inside the element with id scheduleTextPage",
        "season_binding": "the first <h1> inside that element reads '2026 Football Schedule'",
        "header": ["Date", "Time", "At", "Opponent", "Location", "Tournament", "Result"],
        "owner_name": "none (owner verified by another declared structure of the same document)",
        "records": "each <tbody> row with exactly the header's seven cells",
        "members": {"event_date": "Date cell 'Mon D (Ddd)' (year: the season for March-December, the next year for "
                                  "January-February; the weekday must match)",
                    "time_text": "Time cell", "designation": "At cell Home/Away/Neutral", "opponent": "Opponent cell",
                    "location": "Location cell before ' (', or the whole cell",
                    "facility": "Location cell text inside a final '( ... )'"},
    },
    "WMT_SCHEDULE_LIST": {
        "element": "every <div> whose class tokens include schedule-event-item inside the element whose class tokens "
                   "include schedule__view-box--list",
        "season_binding": "the <h1> whose class tokens include schedule-hero__title reads '2026 Football Schedule'",
        "owner_name": "each record's element with class token schedule-event-default__name--current",
        "records": "each such list item",
        "members": {"event_date": "the datetime attribute of its <time> with class token schedule-event-date__day "
                                  "(local date part)",
                    "instant": "the datetime attribute of its <time> with class token schedule-event-date__clock "
                               "(explicit offset; not a statement when the date element has class token "
                               "schedule-event-date--time-tba)",
                    "tba": "class token schedule-event-date--time-tba on its schedule-event-date element",
                    "designation": "class token schedule-event-date--venue-home/away/neutral",
                    "opponent": "its schedule-event-default__name element without the --current token",
                    "location": "its schedule-event-item__location text before ' / '",
                    "facility": "that text after the first ' / '"},
    },
}
TEXT_RULE = "character references decoded, every whitespace run one space, stripped"
NAME_RULES = {
    "normalization": "text rule, then a leading poll rank '(#N)', '#N', '#N/M' or 'No. N' removed, then casefold",
    "owner": "a document's every own-team name statement binds the frozen provider home team (displayName, "
             "shortDisplayName or location) or the NCAA official name of the selected institution; one binding and no "
             "non-binding statement verifies the owner",
    "opponent": "a record's own opponent equals the frozen provider away team's displayName, shortDisplayName or "
                "location; abbreviations, mascots, numeric identifiers, substrings and fuzzy matches never bind",
}
FIELDS = ("season", "opponent", "event_date", "designation", "venue_facility", "venue_location", "scheduled_time")
FIELD_STATES = ("SUPPORTED", "CONFLICTING", "UNSUPPORTED")
TIME_STATES = ("SUPPORTED_INSTANT", "NAIVE_LOCAL_TIME_ONLY", "TBA", "AMBIGUOUS_TIMEZONE", "CONFLICTING",
               "UNSUPPORTED")
COMPARISONS = ("AGREES", "DISAGREES", "TEXT_DIFFERS", "NOT_COMPARABLE")
DISPOSITIONS = ("RECORD_BOUND", "SOURCE_NOT_RETRIEVED", "NO_DECLARED_STRUCTURE", "OWNER_NOT_VERIFIED",
                "NO_RECORD_FOR_EVENT", "OPPONENT_RECORD_ON_OTHER_DATE", "UNBOUND_OPPONENT_ON_EVENT_DATE")
FIELD_RULES = {
    "event_binding": "a record of a declared structure in a document with a verified owner and a 2026 season binding is "
                     "bound to the event when its own opponent binds the frozen away team and its own local date is in "
                     "the provider date set (the calendar dates of the provider instant at offsets -04:00 to -10:00)",
    "occurrences": "records of the bound opponent on other dates, records on the event date naming an unbound opponent "
                   "and records whose date cannot be determined are retained as occurrences, never as witnesses",
    "field_state": "SUPPORTED when every bound witness stating the field states the same value, CONFLICTING when "
                   "they differ (all values kept, never a majority vote), UNSUPPORTED when none states it",
    "opponent": "SUPPORTED by a bound record; CONFLICTING when a bound record and a record naming an unbound opponent "
                "share the event date; with no bound record an unbound opponent name on the event date stays "
                "UNSUPPORTED (an unbindable name may be another team or the same team; never fuzzy-resolved)",
    "event_date": "the bound witnesses' local dates; with no bound record, the bound opponent's other dates are "
                  "CONFLICTING with the provider date",
    "designation": "HOME/AWAY/NEUTRAL from the record's own designation member; the provider claim for the owner is "
                   "NEUTRAL when its neutralSite is true, otherwise HOME",
    "venue": "facility and location text from the record's own members; the facility is compared with the provider "
             "venue name (AGREES when equal after the text rule and casefold, otherwise TEXT_DIFFERS)",
    "scheduled_time": "see TIME_RULES",
    "season": "SUPPORTED when the bound record's structure binds football season 2026 by its own season member",
}
TIME_RULES = {
    "explicit": "an ISO-8601 local date-time with an explicit offset or Z in the record's own instant member",
    "stated_zone": "a time text whose final token is a US zone designator: generic ET/CT/PT resolved by the US daylight "
                   "rule (second Sunday of March 02:00 to first Sunday of November 02:00 local) on the record's own "
                   "local date; EDT/EST/CDT/CST/PDT/PST/MDT must agree with that rule's state; MST is a fixed -07:00; "
                   "generic MT is ambiguous; a local time in a transition gap or fold is ambiguous",
    "naive": "a time without offset or designator stays NAIVE_LOCAL_TIME (no zone is inferred from the campus or site)",
    "tba": "TBA/TBD text, a Nuxt tbd flag or a WMT time-tba token is TBA; the placeholder clock is not a statement",
    "resolution": "SUPPORTED_INSTANT when all instant statements agree and every naive local time and the instants' "
                  "own local times agree; TBA when every statement is TBA; NAIVE_LOCAL_TIME_ONLY when only equal naive "
                  "times exist; AMBIGUOUS_TIMEZONE when only ambiguous designators exist; CONFLICTING otherwise",
    "authority": "a supported instant is OFFICIAL_SCHEDULE_CLAIM, never ACTUAL_KICKOFF",
}
AVAILABILITY_RULE = ("the availability bound is the maximum response end UTC of every attempt in the journal (an "
                     "interrupted attempt uses its start); before it the sidecar is refused, at or after it the same "
                     "immutable evidence is served")
EVENT_FIELDS = ("record_type", "event_key", "season", "owner", "opponent", "provider_claims", "requests", "attempts",
                "documents", "disposition", "disposition_reasons", "fields", "occurrences", "labels")
SOURCE_FIELDS = ("record_type", "event_key", "logical", "route", "stage", "url", "outcome", "hops", "attempts",
                 "decision", "link_source", "document", "labels")
TOP_LEVEL = ("schema", "population", "designation", "contract", "shadow", "acquisition", "labels", "events",
             "sources", "summary", "counts")
FAMILIES = ("SCHEMA", "DESIGNATION", "CONTRACT", "SHADOW", "ACQUISITION", "LABELS", "EVENT_MEMBERSHIP",
            "EVENT_RECORD", "SOURCE_MEMBERSHIP", "SOURCE_RECORD", "SUMMARY", "COUNTS", "CANONICAL_FORM")

#: The actual sidecar pinned by the packaged final gate (``artifacts/data_lake/official_shadow_schedule_20261017_
#: gate.json``; a test requires equality). None until the sidecar exists (the contract is committed first).
SCHEDULE_PROFILE: dict[str, Any] | None = None
PROFILE_FIELDS = ("schedule_identity", "schedule_sha256", "journal_sha256", "attempts", "availability_bound_utc")

IDENTITY_RE = re.compile(r"^[0-9a-f]{64}\Z")
EVENT_KEY_RE = re.compile(r"^espn:event:[0-9]{1,15}\Z")
TEAM_KEY_RE = re.compile(r"^espn:team:[0-9]{1,15}\Z")
UTC_TEXT_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z")
JOURNAL_NAME_RE = re.compile(r"^acquisition/journal-([0-9]{2})\.jsonl\Z")
RAW_NAME_RE = re.compile(r"^raw/([0-9a-f]{64})\.gz\Z")
UTC = _dt.timezone.utc
PINNED = object()


class ScheduleError(ValueError):
    """A refused schedule build or query; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


canonical_bytes = pv.canonical_bytes
sha256_hex = pv.sha256_hex


def file_bytes(document: dict[str, Any]) -> bytes:
    return canonical_bytes(document) + b"\n"


def record_sha256(record: Any) -> str:
    return sha256_hex(canonical_bytes(record))


def _same(a: Any, b: Any) -> bool:
    try:
        return canonical_bytes(a) == canonical_bytes(b)
    except (TypeError, ValueError):
        return False


def strict_json(data: bytes, code: str) -> Any:
    try:
        return sh.strict_json(data, code)
    except sh.ShadowError as exc:
        raise ScheduleError(code, str(exc)) from exc


def iso_micro(moment: _dt.datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_utc_text(text: Any) -> _dt.datetime | None:
    if not isinstance(text, str) or not UTC_TEXT_RE.match(text):
        return None
    try:
        return _dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
    except ValueError:
        return None


# --------------------------------------------------------------------------------------------- text and names

_WS = re.compile(r"\s+")
_RANK = re.compile(r"^(?:\(\s*#\s*[0-9]{1,2}\s*\)|#[0-9]{1,2}(?:/[0-9]{1,2})?|No\.\s*[0-9]{1,2})\s+", re.IGNORECASE)


def clean_text(value: Any) -> str | None:
    """The text rule: character references decoded, every whitespace run one space, stripped (None stays None)."""
    if value is None:
        return None
    return _WS.sub(" ", html.unescape(str(value))).strip()


def name_key(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return _RANK.sub("", text).strip().casefold() or None


# --------------------------------------------------------------------------------------------- time

_TIME_TEXT = re.compile(r"^([0-9]{1,2})(?::([0-9]{2}))?\s*([ap])\.?\s*m\.?(?:\s+([A-Za-z][A-Za-z.]{0,5}))?\Z",
                        re.IGNORECASE)
_TBA_TEXT = {"tba", "tbd", "t.b.a.", "t.b.d."}
_GENERIC_ZONES = {"ET": (-5, -4), "CT": (-6, -5), "PT": (-8, -7)}
_SPECIFIC_ZONES = {"EDT": ("ET", True), "EST": ("ET", False), "CDT": ("CT", True), "CST": ("CT", False),
                   "PDT": ("PT", True), "PST": ("PT", False), "MDT": ("MT", True)}
_DST_FOR_MT = (-7, -6)


def _nth_sunday(year: int, month: int, nth: int) -> _dt.date:
    day = _dt.date(year, month, 1)
    offset = (6 - day.weekday()) % 7
    return day + _dt.timedelta(days=offset + 7 * (nth - 1))


def us_daylight_state(local: _dt.datetime) -> str:
    """'DAYLIGHT', 'STANDARD', 'GAP' or 'FOLD' for a naive local wall time under the US rule since 2007."""
    start = _dt.datetime.combine(_nth_sunday(local.year, 3, 2), _dt.time(2, 0))
    end = _dt.datetime.combine(_nth_sunday(local.year, 11, 1), _dt.time(2, 0))
    if start <= local < start + _dt.timedelta(hours=1):
        return "GAP"
    if end - _dt.timedelta(hours=1) <= local < end:
        return "FOLD"
    return "DAYLIGHT" if start <= local < end else "STANDARD"


def _offset_text(hours: int) -> str:
    return f"{'+' if hours >= 0 else '-'}{abs(hours):02d}:00"


def zone_offset(designator: str, local: _dt.datetime) -> tuple[str | None, str | None]:
    """(offset '+HH:MM', None) for a resolvable designator on that local wall time, else (None, reason)."""
    token = designator.replace(".", "").upper()
    if token == "MST":
        return "-07:00", None
    if token == "MT":
        return None, "GENERIC_MT_AMBIGUOUS_ARIZONA"
    state = us_daylight_state(local)
    if state in ("GAP", "FOLD"):
        return None, f"LOCAL_TIME_IN_DAYLIGHT_TRANSITION_{state}"
    if token in _GENERIC_ZONES:
        standard, daylight = _GENERIC_ZONES[token]
        return _offset_text(daylight if state == "DAYLIGHT" else standard), None
    if token in _SPECIFIC_ZONES:
        generic, daylight = _SPECIFIC_ZONES[token]
        if daylight != (state == "DAYLIGHT"):
            return None, "ZONE_DESIGNATOR_DISAGREES_WITH_DAYLIGHT_RULE"
        standard, summer = _GENERIC_ZONES.get(generic, _DST_FOR_MT)
        return _offset_text(summer if daylight else standard), None
    return None, "ZONE_DESIGNATOR_UNRECOGNIZED"


def parse_time_text(text: Any) -> dict[str, Any]:
    """One time-text statement: TBA, NAIVE (local HH:MM), ZONE (local HH:MM plus designator) or UNRECOGNIZED."""
    value = clean_text(text)
    if value is None or value == "":
        return {"kind": "NOT_STATED"}
    if value.casefold() in _TBA_TEXT:
        return {"kind": "TBA"}
    if value.casefold() == "noon":
        return {"kind": "NAIVE", "local_time": "12:00"}
    match = _TIME_TEXT.match(value)
    if not match:
        return {"kind": "UNRECOGNIZED", "text": value}
    hour, minute, half, zone = match.groups()
    hour_i, minute_i = int(hour), int(minute or "0")
    if not 1 <= hour_i <= 12 or minute_i > 59:
        return {"kind": "UNRECOGNIZED", "text": value}
    hour_i = hour_i % 12 + (12 if half.lower() == "p" else 0)
    local = f"{hour_i:02d}:{minute_i:02d}"
    if zone:
        return {"kind": "ZONE", "local_time": local, "designator": zone.replace(".", "").upper()}
    return {"kind": "NAIVE", "local_time": local}


def time_statement(local_date: str | None, parsed: dict[str, Any]) -> dict[str, Any]:
    """A witness statement of the scheduled time: SUPPORTED_INSTANT basis (utc), NAIVE, TBA or AMBIGUOUS."""
    kind = parsed["kind"]
    if kind in ("NOT_STATED", "TBA", "UNRECOGNIZED"):
        return {"kind": kind, **({"text": parsed["text"]} if kind == "UNRECOGNIZED" else {})}
    if kind == "NAIVE":
        return {"kind": "NAIVE", "local_time": parsed["local_time"]}
    if not local_date:
        return {"kind": "AMBIGUOUS", "local_time": parsed["local_time"], "designator": parsed["designator"],
                "reason": "LOCAL_DATE_UNDETERMINED"}
    local = _dt.datetime.strptime(f"{local_date} {parsed['local_time']}", "%Y-%m-%d %H:%M")
    offset, reason = zone_offset(parsed["designator"], local)
    if offset is None:
        return {"kind": "AMBIGUOUS", "local_time": parsed["local_time"], "designator": parsed["designator"],
                "reason": reason}
    sign = 1 if offset[0] == "+" else -1
    instant = local.replace(tzinfo=_dt.timezone(sign * _dt.timedelta(hours=int(offset[1:3]))))
    return {"kind": "INSTANT", "basis": "STATED_ZONE", "local_time": parsed["local_time"], "offset": offset,
            "designator": parsed["designator"], "utc": iso_micro(instant)}


_ISO_LOCAL = re.compile(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}):([0-9]{2})(?::[0-9]{2}(?:\.[0-9]{1,6})?)?"
                        r"(Z|[+-][0-9]{2}:[0-9]{2})?\Z")


def iso_parts(value: Any) -> dict[str, Any] | None:
    """Local date, local HH:MM and offset of an ISO-8601 local date-time member (offset None when naive)."""
    if not isinstance(value, str):
        return None
    match = _ISO_LOCAL.match(value.strip())
    if not match:
        return None
    date, hh, mm, zone = match.groups()
    try:
        _dt.date.fromisoformat(date)
        if int(hh) > 23 or int(mm) > 59:
            return None
        utc = None
        if zone:
            moment = _dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            utc = iso_micro(moment)
    except ValueError:
        return None
    return {"local_date": date, "local_time": f"{hh}:{mm}", "offset": None if not zone else
            ("+00:00" if zone == "Z" else zone), "utc": utc}


# --------------------------------------------------------------------------------------------- structures

_NUXT_RE = re.compile(rb'<script\b[^>]*\bid="__NUXT_DATA__"[^>]*>(.*?)</script>', re.S)
_WRAPPERS = ("Reactive", "ShallowReactive", "Ref", "ShallowRef")
_MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                       "dec"), 1)}
_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_TABLE_DATE = re.compile(r"^([A-Za-z]{3})[a-z]*\.?\s+([0-9]{1,2})\s*\(([A-Za-z]{3})[a-z]*\.?\)\Z")
_DESIGNATIONS = {"H": "HOME", "A": "AWAY", "N": "NEUTRAL"}
_TEXT_DESIGNATIONS = {"home": "HOME", "away": "AWAY", "neutral": "NEUTRAL"}
_WMT_DESIGNATIONS = {"schedule-event-date--venue-home": "HOME", "schedule-event-date--venue-away": "AWAY",
                     "schedule-event-date--venue-neutral": "NEUTRAL"}
SEASON_HEADING = f"{SEASON} Football Schedule"


def _decode(body: bytes) -> str | None:
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _devalue(data: list[Any], value: Any) -> Any:
    if type(value) is int:
        if value < 0 or value >= len(data):
            return None
        value = data[value]
    while isinstance(value, list) and len(value) == 2 and value[0] in _WRAPPERS and type(value[1]) is int:
        value = data[value[1]] if 0 <= value[1] < len(data) else None
    return value


def _member(data: list[Any], obj: Any, *path: str) -> Any:
    cur = obj
    for step in path:
        if not isinstance(cur, dict) or step not in cur:
            return None
        cur = _devalue(data, cur[step])
    return cur


def _scalar(value: Any) -> Any:
    return value if isinstance(value, (str, int, bool)) or value is None else None


def extract_sidearm_nuxt(body: bytes) -> list[dict[str, Any]]:
    """Every football season schedule record of the page's own Nuxt payload (one structure instance per record)."""
    match = _NUXT_RE.search(body)
    if not match:
        return []
    try:
        data = json.loads(match.group(1).decode("utf-8"), parse_constant=lambda c: None)
    except (UnicodeDecodeError, ValueError):
        return [{"structure": "SIDEARM_NUXT_SCHEDULE", "instance": 0, "matched": False,
                 "reason": "NUXT_PAYLOAD_NOT_JSON", "season_bound": False, "season_witness": None,
                 "owner_names": [], "records": []}]
    if not isinstance(data, list) or not data:
        return []
    schedules = _member(data, _devalue(data, 0), "pinia", "schedule", "schedules")
    if not isinstance(schedules, dict):
        return []
    out = []
    for key in sorted(schedules):
        rec = _devalue(data, schedules[key])
        if not isinstance(rec, dict) or _member(data, rec, "sport", "shortname") != "football":
            continue
        season_title = _scalar(_member(data, rec, "season", "title"))
        school = _scalar(_member(data, rec, "school_name"))
        games = _member(data, rec, "games")
        records = []
        for index, ref in enumerate(games if isinstance(games, list) else []):
            game = _devalue(data, ref)
            if not isinstance(game, dict):
                continue
            records.append({"index": index, "members": {
                "date": _scalar(_member(data, game, "date")), "time": _scalar(_member(data, game, "time")),
                "tbd": _scalar(_member(data, game, "tbd")),
                "location_indicator": _scalar(_member(data, game, "location_indicator")),
                "opponent.title": _scalar(_member(data, game, "opponent", "title")),
                "facility.title": _scalar(_member(data, game, "facility", "title")),
                "location": _scalar(_member(data, game, "location"))}})
        out.append({"structure": "SIDEARM_NUXT_SCHEDULE", "instance": len(out), "key": key, "matched": True,
                    "reason": None, "season_bound": season_title == str(SEASON),
                    "season_witness": {"member": "season.title", "raw": season_title},
                    "owner_names": [school] if isinstance(school, str) else [], "records": records})
    return out


class _Tree(html.parser.HTMLParser):
    """A tolerant element tree (tag, attrs, children, text) of one HTML document."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track",
            "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: dict[str, Any] = {"tag": "#root", "attrs": {}, "children": []}
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = {"tag": tag, "attrs": {k: (v or "") for k, v in attrs}, "children": []}
        self.stack[-1]["children"].append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack[-1]["children"].append({"tag": tag, "attrs": {k: (v or "") for k, v in attrs}, "children": []})

    def handle_endtag(self, tag: str) -> None:
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.stack[depth]["tag"] == tag:
                del self.stack[depth:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1]["children"].append(data)


def parse_tree(text: str) -> dict[str, Any]:
    tree = _Tree()
    tree.feed(text)
    tree.close()
    return tree.root


def _classes(node: dict[str, Any]) -> set[str]:
    return set((node.get("attrs", {}).get("class") or "").split())


def _walk(node: Any) -> Iterable[dict[str, Any]]:
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            yield cur
            stack.extend(reversed(cur.get("children") or []))


def _text(node: Any) -> str:
    parts: list[str] = []
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            parts.append(cur)
        elif isinstance(cur, dict) and cur.get("tag") not in ("script", "style"):
            stack.extend(reversed(cur.get("children") or []))
    return _WS.sub(" ", "".join(parts)).strip()


def _first(node: dict[str, Any], predicate: Any) -> dict[str, Any] | None:
    for item in _walk(node):
        if item is not node and predicate(item):
            return item
    return None


def _table_date(text: str) -> tuple[str | None, str | None]:
    match = _TABLE_DATE.match(text or "")
    if not match:
        return None, "DATE_TEXT_UNRECOGNIZED"
    month, day, weekday = match.group(1).lower(), int(match.group(2)), match.group(3).lower()
    if month not in _MONTHS or weekday not in _WEEKDAYS:
        return None, "DATE_TEXT_UNRECOGNIZED"
    year = SEASON if _MONTHS[month] >= 3 else SEASON + 1
    try:
        date = _dt.date(year, _MONTHS[month], day)
    except ValueError:
        return None, "DATE_TEXT_INVALID"
    if _WEEKDAYS[date.weekday()] != weekday:
        return None, "DATE_WEEKDAY_MISMATCH"
    return date.isoformat(), None


def extract_sidearm_text_table(root: dict[str, Any]) -> list[dict[str, Any]]:
    page = _first(root, lambda n: n.get("attrs", {}).get("id") == "scheduleTextPage")
    if page is None:
        return []
    heading = _first(page, lambda n: n.get("tag") == "h1")
    table = _first(page, lambda n: n.get("tag") == "table")
    head_text = _text(heading) if heading else None
    out = {"structure": "SIDEARM_TEXT_TABLE", "instance": 0, "matched": True, "reason": None,
           "season_bound": head_text == SEASON_HEADING, "season_witness": {"member": "h1", "raw": head_text},
           "owner_names": [], "records": []}
    if table is None:
        return [{**out, "matched": False, "reason": "TEXT_TABLE_MISSING"}]
    thead = _first(table, lambda n: n.get("tag") == "thead")
    header = [_text(c) for c in _walk(thead) if c.get("tag") == "th"] if thead else []
    if header != STRUCTURES["SIDEARM_TEXT_TABLE"]["header"]:
        return [{**out, "matched": False, "reason": "TEXT_TABLE_HEADER_DIFFERS"}]
    tbody = _first(table, lambda n: n.get("tag") == "tbody")
    rows = [n for n in (tbody or {}).get("children") or [] if isinstance(n, dict) and n.get("tag") == "tr"]
    for index, row in enumerate(rows):
        cells = [_text(c) for c in row.get("children") or [] if isinstance(c, dict) and c.get("tag") == "td"]
        if len(cells) != len(header):
            continue
        # the Result and Tournament cells are never extracted (past results stay raw page bytes only)
        out["records"].append({"index": index, "members": {k: v for k, v in zip(header, cells)
                                                           if k in ("Date", "Time", "At", "Opponent", "Location")}})
    return [out]


def extract_wmt_list(root: dict[str, Any]) -> list[dict[str, Any]]:
    view = _first(root, lambda n: "schedule__view-box--list" in _classes(n))
    if view is None:
        return []
    heading = _first(root, lambda n: n.get("tag") == "h1" and "schedule-hero__title" in _classes(n))
    head_text = _text(heading) if heading else None
    out = {"structure": "WMT_SCHEDULE_LIST", "instance": 0, "matched": True, "reason": None,
           "season_bound": head_text == SEASON_HEADING, "season_witness": {"member": "h1.schedule-hero__title",
                                                                           "raw": head_text},
           "owner_names": [], "records": []}
    items = [n for n in _walk(view) if n.get("tag") == "div" and "schedule-event-item" in _classes(n)]
    for index, item in enumerate(items):
        date_el = _first(item, lambda n: "schedule-event-date" in _classes(n))
        day = _first(item, lambda n: n.get("tag") == "time" and "schedule-event-date__day" in _classes(n))
        clock = _first(item, lambda n: n.get("tag") == "time" and "schedule-event-date__clock" in _classes(n))
        current = _first(item, lambda n: "schedule-event-default__name--current" in _classes(n))
        opponents = [n for n in _walk(item) if "schedule-event-default__name" in _classes(n) and
                     "schedule-event-default__name--current" not in _classes(n)]
        location = _first(item, lambda n: "schedule-event-item__location" in _classes(n))
        tokens = _classes(date_el) if date_el else set()
        venue = [t for t in sorted(tokens) if t in _WMT_DESIGNATIONS]
        own = _text(current) if current else None
        if own:
            out["owner_names"].append(own)
        out["records"].append({"index": index, "members": {
            "day.datetime": (day or {}).get("attrs", {}).get("datetime"),
            "clock.datetime": (clock or {}).get("attrs", {}).get("datetime"),
            "clock.text": _text(clock) if clock else None,
            "time_tba": "schedule-event-date--time-tba" in tokens,
            "venue_class": venue[0] if len(venue) == 1 else (None if not venue else "|".join(venue)),
            "own_name": own, "opponent_name": _text(opponents[0]) if len(opponents) == 1 else
            (None if not opponents else "|".join(_text(o) for o in opponents)),
            "location": _text(location) if location else None}})
    return [out]


def extract_document(body: bytes) -> dict[str, Any]:
    """Every declared structure instance of one retained document (no declared structure -> an empty list)."""
    structures = extract_sidearm_nuxt(body)
    text = _decode(body)
    if text is not None:
        root = parse_tree(text)
        structures += extract_sidearm_text_table(root)
        structures += extract_wmt_list(root)
    return {"utf8": text is not None, "structures": structures}


# --------------------------------------------------------------------------------------------- witnesses

def _split_location(text: str | None, separator: str) -> tuple[str | None, str | None]:
    value = clean_text(text)
    if not value:
        return None, None
    if separator == " / ":
        if " / " in value:
            location, facility = value.split(" / ", 1)
            return clean_text(location) or None, clean_text(facility) or None
        return value, None
    match = re.match(r"^(.*?)\s*\(([^()]*)\)\Z", value)
    if match:
        return clean_text(match.group(1)) or None, clean_text(match.group(2)) or None
    return value, None


def record_values(structure: str, members: dict[str, Any]) -> dict[str, Any]:
    """The field statements of one record from its own members only (each with its member name and raw value)."""
    out: dict[str, Any] = {}
    if structure == "SIDEARM_NUXT_SCHEDULE":
        parts = iso_parts(members.get("date"))
        tba = members.get("tbd") is True
        out["event_date"] = (parts or {}).get("local_date")
        out["event_date_member"] = "date"
        out["opponent"] = clean_text(members.get("opponent.title"))
        out["designation"] = _DESIGNATIONS.get(str(members.get("location_indicator")))
        out["facility"] = clean_text(members.get("facility.title")) or None
        out["location"] = clean_text(members.get("location")) or None
        statements = []
        if tba:
            statements.append({"member": "tbd", "raw": True, **{"kind": "TBA"}})
        else:
            if parts and parts["offset"] is None:
                statements.append({"member": "date", "raw": members.get("date"), "kind": "NAIVE",
                                   "local_time": parts["local_time"]})
            elif parts:
                statements.append({"member": "date", "raw": members.get("date"), "kind": "INSTANT",
                                   "basis": "EXPLICIT_OFFSET", "local_time": parts["local_time"],
                                   "offset": parts["offset"], "utc": parts["utc"]})
            statements.append({"member": "time", "raw": members.get("time"),
                               **time_statement(out["event_date"], parse_time_text(members.get("time")))})
        out["time"] = statements
    elif structure == "SIDEARM_TEXT_TABLE":
        date, reason = _table_date(members.get("Date") or "")
        out["event_date"], out["event_date_member"], out["event_date_reason"] = date, "Date", reason
        out["opponent"] = clean_text(members.get("Opponent"))
        out["designation"] = _TEXT_DESIGNATIONS.get((clean_text(members.get("At")) or "").casefold())
        out["location"], out["facility"] = _split_location(members.get("Location"), "(")
        out["time"] = [{"member": "Time", "raw": members.get("Time"),
                        **time_statement(date, parse_time_text(members.get("Time")))}]
    elif structure == "WMT_SCHEDULE_LIST":
        day = iso_parts(members.get("day.datetime"))
        out["event_date"], out["event_date_member"] = (day or {}).get("local_date"), "day.datetime"
        out["opponent"] = clean_text(members.get("opponent_name"))
        out["designation"] = _WMT_DESIGNATIONS.get(members.get("venue_class") or "")
        out["location"], out["facility"] = _split_location(members.get("location"), " / ")
        if members.get("time_tba") is True:
            out["time"] = [{"member": "time_tba", "raw": True, "kind": "TBA"}]
        else:
            clock = iso_parts(members.get("clock.datetime"))
            statements = []
            if clock and clock["offset"]:
                statements.append({"member": "clock.datetime", "raw": members.get("clock.datetime"),
                                   "kind": "INSTANT", "basis": "EXPLICIT_OFFSET", "local_time": clock["local_time"],
                                   "offset": clock["offset"], "utc": clock["utc"]})
            elif clock:
                statements.append({"member": "clock.datetime", "raw": members.get("clock.datetime"), "kind": "NAIVE",
                                   "local_time": clock["local_time"]})
            text = parse_time_text(members.get("clock.text"))
            if text["kind"] != "NOT_STATED":
                statements.append({"member": "clock.text", "raw": members.get("clock.text"),
                                   **time_statement(out["event_date"], text)})
            out["time"] = statements
    return out


def provider_date_set(scheduled_utc: str) -> list[str]:
    """The calendar dates of the provider instant at every US offset -04:00 through -10:00."""
    moment = _dt.datetime.strptime(scheduled_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return sorted({(moment + _dt.timedelta(hours=h)).date().isoformat() for h in range(-10, -3)})


def resolve_time(witnesses: list[dict[str, Any]]) -> dict[str, Any]:
    statements = [s for w in witnesses for s in w["time"] if s["kind"] not in ("NOT_STATED",)]
    if not statements:
        return {"state": "UNSUPPORTED", "value": None, "reasons": ["NO_TIME_STATEMENT"]}
    kinds = {s["kind"] for s in statements}
    instants = sorted({s["utc"] for s in statements if s["kind"] == "INSTANT"})
    locals_ = sorted({s["local_time"] for s in statements if s.get("local_time") and s["kind"] in ("NAIVE",
                                                                                                    "INSTANT")})
    reasons = sorted({s.get("reason") for s in statements if s["kind"] == "AMBIGUOUS" and s.get("reason")})
    unrecognized = sorted({s.get("text") for s in statements if s["kind"] == "UNRECOGNIZED"})
    if "TBA" in kinds and kinds - {"TBA", "UNRECOGNIZED", "AMBIGUOUS"}:
        return {"state": "CONFLICTING", "value": {"instants": instants, "local_times": locals_, "tba": True},
                "reasons": ["TBA_AND_TIME_STATED"]}
    if len(instants) > 1 or len(locals_) > 1:
        return {"state": "CONFLICTING", "value": {"instants": instants, "local_times": locals_, "tba": False},
                "reasons": ["DIFFERENT_TIME_STATEMENTS"]}
    if instants:
        bases = sorted({s["basis"] for s in statements if s["kind"] == "INSTANT"})
        return {"state": "SUPPORTED_INSTANT", "value": {"utc": instants[0], "local_time": locals_[0] if locals_ else
                                                        None, "bases": bases},
                "reasons": sorted(set(reasons) | ({"UNRECOGNIZED_TEXT_ALSO_PRESENT"} if unrecognized else set()))}
    if "TBA" in kinds:
        return {"state": "TBA", "value": {"tba": True}, "reasons": reasons}
    if locals_:
        return {"state": "NAIVE_LOCAL_TIME_ONLY", "value": {"local_time": locals_[0]},
                "reasons": sorted(set(reasons) | {"NO_EXPLICIT_OFFSET_OR_STATED_ZONE"})}
    if "AMBIGUOUS" in kinds:
        ambiguous = sorted({(s["local_time"], s["designator"]) for s in statements if s["kind"] == "AMBIGUOUS"})
        return {"state": "AMBIGUOUS_TIMEZONE" if len(ambiguous) == 1 else "CONFLICTING",
                "value": {"local_times": sorted({a[0] for a in ambiguous}), "designators": sorted({a[1] for a in
                                                                                                   ambiguous})},
                "reasons": reasons}
    return {"state": "UNSUPPORTED", "value": None, "reasons": ["TIME_TEXT_UNRECOGNIZED"]}


def _single(values: list[Any]) -> tuple[str, Any]:
    stated = sorted({v for v in values if v is not None})
    if not stated:
        return "UNSUPPORTED", None
    return ("SUPPORTED", stated[0]) if len(stated) == 1 else ("CONFLICTING", stated)


# --------------------------------------------------------------------------------------------- journal

def _family(host: str) -> set[str]:
    base = host[4:] if host.startswith("www.") else host
    return {base, "www." + base}


def _host(url: Any) -> str | None:
    if not isinstance(url, str):
        return None
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return None
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.port:
        return None
    return parts.hostname


def _path_segments(url: str) -> list[str]:
    return [s for s in urllib.parse.urlsplit(url).path.split("/") if s]


def explicit_links(body: bytes, family: set[str], base_url: str) -> list[str]:
    """Same-family hrefs of a retained body whose path names a football schedule of the season (document order)."""
    text = _decode(body)
    if text is None:
        return []
    found: list[str] = []
    for node in _walk(parse_tree(text)):
        href = node.get("attrs", {}).get("href") if node.get("tag") == "a" else None
        if not href:
            continue
        url = urllib.parse.urljoin(base_url, html.unescape(href.strip()))
        url = urllib.parse.urlunsplit(urllib.parse.urlsplit(url)._replace(fragment=""))
        host = _host(url)
        segments = _path_segments(url) if host else []
        if host in family and "schedule" in segments and str(SEASON) in segments and \
                ({"football", "m-footbl"} & set(segments)) and url not in found:
            found.append(url)
    return found


def _headers(value: Any) -> list[list[str]] | None:
    if not isinstance(value, list) or not all(isinstance(h, list) and len(h) == 2 and all(isinstance(x, str) for x in h)
                                              for h in value):
        return None
    return value


def _location(headers: list[list[str]], url: str) -> str | None:
    found = [v for k, v in headers if k.lower() == "location"]
    return urllib.parse.urljoin(url, found[0]) if len(found) == 1 else None


def read_journal(segments: dict[str, bytes]) -> list[dict[str, Any]]:
    """Every journal line of every segment in order (strict JSON objects; segment order by number)."""
    rows: list[dict[str, Any]] = []
    numbers = sorted(int(JOURNAL_NAME_RE.match(n).group(1)) for n in segments)
    if numbers != list(range(1, len(numbers) + 1)):
        raise ScheduleError("SCHEDULE_JOURNAL_SEGMENTS_INVALID", f"journal segments {numbers} are not 1..n")
    for number in numbers:
        data = segments[f"{JOURNAL_PREFIX}{number:02d}.jsonl"]
        if not data.endswith(b"\n") and data:
            raise ScheduleError("SCHEDULE_JOURNAL_MALFORMED", f"segment {number} does not end with a newline")
        for line_no, line in enumerate(data.split(b"\n")[:-1], 1):
            row = strict_json(line, "SCHEDULE_JOURNAL_MALFORMED")
            if not isinstance(row, dict) or row.get("record") not in ("capture_start", "intent", "result", "decision",
                                                                      "capture_end"):
                raise ScheduleError("SCHEDULE_JOURNAL_MALFORMED", f"segment {number} line {line_no} is not a record")
            rows.append({**row, "_segment": number})
    return rows


def verify_journal(segments: dict[str, bytes], raw: dict[str, bytes], expected: list[dict[str, Any]],
                   spec_acquisition: dict[str, Any], contract_sha256: str, shadow_identity: str) -> dict[str, Any]:
    """The complete acquisition re-derived from the journal and the retained raw bodies and checked against the grant:
    logical requests with every hop, zero-request decisions, stops, the attempt count and the availability bound."""
    rows = read_journal(segments)
    by_event = {e["event_key"]: e for e in expected}
    families = {e["event_key"]: set(e["owner"]["host_family"]) for e in expected}
    seq = 0
    attempts: list[dict[str, Any]] = []
    logical: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    decisions: list[dict[str, Any]] = []
    stopped: dict[str, int] = {}
    pending: dict[str, Any] | None = None
    last_start_ns: int | None = None
    starts = [r for r in rows if r["record"] == "capture_start"]
    if not starts or rows[0]["record"] != "capture_start":
        raise ScheduleError("SCHEDULE_JOURNAL_MALFORMED", "the journal does not start with capture_start")
    for start in starts:
        if start.get("schema") != JOURNAL_SCHEMA or start.get("contract_sha256") != contract_sha256 or \
                start.get("shadow_identity") != shadow_identity or \
                not _same(start.get("ceiling"), spec_acquisition["ceiling_attempts"]) or \
                not _same(start.get("min_spacing_ns"), spec_acquisition["min_spacing_ns"]) or \
                not _same(start.get("max_hops"), spec_acquisition["max_hops"]) or \
                not _same(start.get("max_body_bytes"), spec_acquisition["max_body_bytes"]):
            raise ScheduleError("SCHEDULE_JOURNAL_GRANT_MISMATCH", "a capture segment does not declare this contract's "
                                                                   "grant")
    used_bodies: set[str] = set()
    for row in rows:
        kind = row["record"]
        if kind in ("capture_start", "capture_end"):
            if pending is not None and kind == "capture_start":
                pending["result"] = None  # interrupted: the next segment starts without its result
                pending = None
            continue
        if kind == "intent":
            if pending is not None:
                raise ScheduleError("SCHEDULE_JOURNAL_ORDER_INVALID", f"intent {row.get('seq')} before the result of "
                                                                      f"{pending['seq']}")
            seq += 1
            if not _same(row.get("seq"), seq):
                raise ScheduleError("SCHEDULE_JOURNAL_SEQUENCE_INVALID", f"intent {row.get('seq')!r} is not {seq}")
            key, url, route = row.get("event_key"), row.get("url"), row.get("route")
            host = _host(url)
            if key not in by_event or route not in ROUTES or not isinstance(row.get("logical"), str) or \
                    type(row.get("hop")) is not int or not 1 <= row["hop"] <= spec_acquisition["max_hops"]:
                raise ScheduleError("SCHEDULE_JOURNAL_INTENT_INVALID", f"intent {seq} is malformed")
            if host is None or host not in families[key]:
                raise ScheduleError("SCHEDULE_UNAUTHORIZED_HOST", f"intent {seq} requests {host!r} outside the "
                                                                  f"event's official host family")
            family_key = sorted(families[key])[0]
            if family_key in stopped:
                raise ScheduleError("SCHEDULE_STOPPED_HOST_REQUESTED", f"intent {seq} requests a stopped host family")
            start_ns = row.get("start_ns")
            if type(start_ns) is not int or parse_utc_text(row.get("start_utc")) is None:
                raise ScheduleError("SCHEDULE_JOURNAL_INTENT_INVALID", f"intent {seq} has no valid start")
            if last_start_ns is not None and start_ns - last_start_ns < spec_acquisition["min_spacing_ns"]:
                raise ScheduleError("SCHEDULE_SPACING_VIOLATED", f"intent {seq} starts {start_ns - last_start_ns} ns "
                                                                 "after the previous attempt")
            last_start_ns = start_ns
            name = row["logical"]
            entry = logical.get(name)
            if entry is None:
                if row["hop"] != 1:
                    raise ScheduleError("SCHEDULE_REDIRECT_CHAIN_INVALID", f"{name} starts at hop {row['hop']}")
                entry = {"event_key": key, "logical": name, "route": route, "url": url, "hops": [],
                         "link_source": row.get("link_source"), "decision": None}
                logical[name] = entry
                order.append(name)
            elif entry["event_key"] != key or entry["route"] != route or row["hop"] != len(entry["hops"]) + 1:
                raise ScheduleError("SCHEDULE_REDIRECT_CHAIN_INVALID", f"{name} hop {row['hop']} does not continue "
                                                                       "its chain")
            else:
                prev = entry["hops"][-1]
                if prev.get("result") is None or prev["result"]["status"] not in spec_acquisition[
                        "redirect_statuses"] or prev["location"] != url:
                    raise ScheduleError("SCHEDULE_REDIRECT_CHAIN_INVALID", f"{name} hop {row['hop']} is not the "
                                                                           "previous hop's same-family Location")
            pending = {"seq": seq, "url": url, "host": host, "hop": row["hop"], "start_utc": row["start_utc"],
                       "start_ns": start_ns, "logical": name, "event_key": key, "segment": row["_segment"],
                       "result": None, "location": None}
            entry["hops"].append(pending)
            attempts.append(pending)
            continue
        if kind == "result":
            if pending is None or not _same(row.get("seq"), pending["seq"]):
                raise ScheduleError("SCHEDULE_JOURNAL_ORDER_INVALID", f"result {row.get('seq')!r} has no open intent")
            status = row.get("status")
            headers = _headers(row.get("headers"))
            body_sha, body_bytes = row.get("body_sha256"), row.get("body_bytes")
            end = parse_utc_text(row.get("end_utc"))
            if (status is not None and type(status) is not int) or headers is None or \
                    not isinstance(body_sha, str) or not IDENTITY_RE.match(body_sha) or type(body_bytes) is not int or \
                    type(row.get("truncated")) is not bool or end is None or type(row.get("end_ns")) is not int or \
                    not (row.get("error") is None or isinstance(row.get("error"), str)):
                raise ScheduleError("SCHEDULE_JOURNAL_RESULT_INVALID", f"result {pending['seq']} is malformed")
            body = raw.get(body_sha)
            if body is None:
                raise ScheduleError("SCHEDULE_RAW_BODY_MISSING", f"result {pending['seq']} names a body that is not "
                                                                 "retained")
            if len(body) != body_bytes or body_bytes > spec_acquisition["max_body_bytes"]:
                raise ScheduleError("SCHEDULE_RAW_BODY_MISMATCH", f"result {pending['seq']} body length differs")
            if end < parse_utc_text(pending["start_utc"]) or row["end_ns"] < pending["start_ns"]:
                raise ScheduleError("SCHEDULE_JOURNAL_RESULT_INVALID", f"result {pending['seq']} ends before it starts")
            if status is None and not row.get("error"):
                raise ScheduleError("SCHEDULE_JOURNAL_RESULT_INVALID", f"result {pending['seq']} has neither a status "
                                                                       "nor an error")
            used_bodies.add(body_sha)
            pending["result"] = {"status": status, "headers": headers, "body_sha256": body_sha,
                                 "body_bytes": body_bytes, "truncated": row["truncated"], "error": row["error"],
                                 "end_utc": row["end_utc"], "end_ns": row["end_ns"]}
            pending["location"] = _location(headers, pending["url"]) if status in spec_acquisition[
                "redirect_statuses"] else None
            if status in spec_acquisition["stop_statuses"]:
                stopped[sorted(families[pending["event_key"]])[0]] = pending["seq"]
            pending = None
            continue
        if kind == "decision":
            if pending is not None:
                raise ScheduleError("SCHEDULE_JOURNAL_ORDER_INVALID", "a decision interrupts an open attempt")
            key, name = row.get("event_key"), row.get("logical")
            if key not in by_event or row.get("decision") not in DECISIONS or not isinstance(name, str) or \
                    row.get("route") not in ROUTES:
                raise ScheduleError("SCHEDULE_JOURNAL_DECISION_INVALID", f"decision {row!r} is malformed")
            decisions.append({k: row.get(k) for k in ("event_key", "logical", "route", "url", "decision", "detail")})
            continue
    if pending is not None:
        pending["result"] = None
    if seq > spec_acquisition["ceiling_attempts"]:
        raise ScheduleError("SCHEDULE_CEILING_EXCEEDED", f"{seq} attempts exceed the grant of "
                                                         f"{spec_acquisition['ceiling_attempts']}")
    unused = sorted(set(raw) - used_bodies)
    if unused:
        raise ScheduleError("SCHEDULE_RAW_BODY_UNREFERENCED", f"retained bodies not named by the journal: {unused[:3]}")
    # attach decisions: a redirect decision closes an existing logical request; a not-requested decision is its own
    for d in decisions:
        if d["decision"] in ("REDIRECT_OUTSIDE_FAMILY_NOT_FOLLOWED", "REDIRECT_LIMIT_REACHED"):
            entry = logical.get(d["logical"])
            last = (entry or {}).get("hops", [{}])[-1] if entry else None
            if entry is None or not last or last.get("result") is None or last["result"]["status"] not in \
                    spec_acquisition["redirect_statuses"] or entry["decision"] is not None:
                raise ScheduleError("SCHEDULE_JOURNAL_DECISION_INVALID", f"{d['decision']} names no redirect")
            if d["decision"] == "REDIRECT_OUTSIDE_FAMILY_NOT_FOLLOWED" and \
                    (last["location"] is None or _host(last["location"]) in families[entry["event_key"]]):
                raise ScheduleError("SCHEDULE_JOURNAL_DECISION_INVALID", "a same-family redirect was not followed")
            if d["decision"] == "REDIRECT_LIMIT_REACHED" and len(entry["hops"]) != spec_acquisition["max_hops"]:
                raise ScheduleError("SCHEDULE_JOURNAL_DECISION_INVALID", "the redirect limit was not reached")
            entry["decision"] = d
        elif d["logical"] in logical:
            # only a budget stop may end a requested chain early: its last hop is a same-family redirect not followed
            entry = logical[d["logical"]]
            last = entry["hops"][-1] if entry["hops"] else None
            if d["decision"] != "NOT_REQUESTED_BUDGET_EXHAUSTED" or not last or last.get("result") is None or \
                    last["result"]["status"] not in spec_acquisition["redirect_statuses"] or \
                    entry["decision"] is not None or last["location"] != d["url"] or \
                    _host(d["url"]) not in families[entry["event_key"]]:
                raise ScheduleError("SCHEDULE_JOURNAL_DECISION_INVALID", f"{d['logical']} was requested")
            entry["decision"] = d
        else:
            if d["logical"] in logical:
                raise ScheduleError("SCHEDULE_JOURNAL_DECISION_INVALID", f"{d['logical']} was requested")
            logical[d["logical"]] = {"event_key": d["event_key"], "logical": d["logical"], "route": d["route"],
                                     "url": d["url"], "hops": [], "link_source": None, "decision": d}
            order.append(d["logical"])
    # every redirect that was not followed must carry its decision; outcomes
    for name in order:
        entry = logical[name]
        hops = entry["hops"]
        last = hops[-1] if hops else None
        if not hops:
            entry["outcome"] = entry["decision"]["decision"]
            continue
        res = last["result"]
        if res is None:
            entry["outcome"] = "INTERRUPTED"
        elif res["status"] in spec_acquisition["stop_statuses"]:
            entry["outcome"] = "HOST_STOPPED_HTTP"
        elif res["status"] in spec_acquisition["redirect_statuses"] and last["location"] is None:
            entry["outcome"] = "FAILED_HTTP"  # a redirect without exactly one Location cannot be followed
        elif res["status"] in spec_acquisition["redirect_statuses"]:
            if entry["decision"] is None and last is attempts[-1]:
                entry["outcome"] = "INTERRUPTED"
            elif entry["decision"] is None:
                raise ScheduleError("SCHEDULE_REDIRECT_CHAIN_INVALID", f"{name} ends at a redirect without a decision")
            else:
                entry["outcome"] = entry["decision"]["decision"]
        elif res["error"] and res["status"] is None:
            entry["outcome"] = "FAILED_NO_RESPONSE"
        elif res["truncated"]:
            entry["outcome"] = "TRUNCATED_BODY"
        elif res["status"] == 200 and not res["error"]:
            entry["outcome"] = "RETAINED_200"
        else:
            entry["outcome"] = "FAILED_HTTP"
    ends = []
    for attempt in attempts:
        ends.append(attempt["result"]["end_utc"] if attempt["result"] else attempt["start_utc"])
    bound = max(ends) if ends else None
    return {"attempts": attempts, "logical": logical, "order": order, "stopped_families": sorted(stopped),
            "availability_bound_utc": bound,
            "first_start_utc": attempts[0]["start_utc"] if attempts else None,
            "segments": len(set(r["_segment"] for r in rows))}


# --------------------------------------------------------------------------------------------- qualification

def _route_url_ok(entry: dict[str, Any], event: dict[str, Any], raw: dict[str, bytes],
                  attempts_by_seq: dict[int, dict[str, Any]]) -> bool:
    url, route = entry["url"], entry["route"]
    family = set(event["owner"]["host_family"])
    host = _host(url)
    if host not in family:
        return False
    if route == "INITIAL_SEASON_ROUTE":
        return url == f"https://{host}/sports/football/schedule/{SEASON}"
    if route == "LANDING_ROUTE":
        return url == f"https://{event['owner']['directory_host']}/sports/football/schedule"
    source = entry.get("link_source")
    if not isinstance(source, dict) or type(source.get("seq")) is not int:
        return False
    origin = attempts_by_seq.get(source["seq"])
    if origin is None or origin["event_key"] != entry["event_key"] or origin["result"] is None or \
            origin["result"]["body_sha256"] != source.get("body_sha256"):
        return False
    return url in explicit_links(raw[origin["result"]["body_sha256"]], family, origin["url"])


def _owner_state(structures: list[dict[str, Any]], owner: dict[str, Any]) -> dict[str, Any]:
    allowed = {name_key(owner["provider_names"][k]) for k in ("displayName", "shortDisplayName", "location")}
    allowed.add(name_key(owner["official_name"]))
    allowed.discard(None)
    names = sorted({n for s in structures if s["matched"] for n in s["owner_names"] if n})
    keys = {name_key(n) for n in names}
    binding = [n for n in names if name_key(n) in allowed]
    other = [n for n in names if name_key(n) not in allowed]
    if not names:
        state = "OWNER_NAME_NOT_STATED"
    elif other:
        state = "OWNER_NAME_DOES_NOT_BIND"
    else:
        state = "OWNER_VERIFIED"
    return {"state": state, "statements": names, "binding": binding, "non_binding": other,
            "distinct_keys": len(keys)}


def document_census(doc_sha: str, body: bytes, event: dict[str, Any]) -> dict[str, Any]:
    """One retained document's declared structures, season binding and owner verification for its event."""
    extracted = extract_document(body)
    structures = extracted["structures"]
    owner = _owner_state(structures, event["owner"])
    qualified = [s for s in structures if s["matched"] and s["season_bound"]]
    return {"document": doc_sha, "bytes": len(body), "utf8": extracted["utf8"],
            "structures": [{"structure": s["structure"], "instance": s["instance"], "matched": s["matched"],
                            "reason": s["reason"], "season_bound": s["season_bound"],
                            "season_witness": s["season_witness"], "records": len(s["records"]),
                            "owner_names": s["owner_names"]} for s in structures],
            "owner": owner, "qualified": bool(qualified) and owner["state"] == "OWNER_VERIFIED",
            "_structures": structures}


def qualify_event(event: dict[str, Any], docs: list[dict[str, Any]]) -> dict[str, Any]:
    """The event's dispositions and separate field states from its retained documents (never from the provider)."""
    claims = event["provider_claims"]
    dates = set(claims["local_date_set"])
    away = {name_key(event["opponent"]["provider_names"][k]) for k in ("displayName", "shortDisplayName",
                                                                       "location")}
    away.discard(None)
    bound, occurrences = [], []
    for doc in docs:
        if not doc["qualified"]:
            continue
        for s in doc["_structures"]:
            if not (s["matched"] and s["season_bound"]):
                continue
            for rec in s["records"]:
                values = record_values(s["structure"], rec["members"])
                base = {"document": doc["document"], "logical": doc["logical"], "structure": s["structure"],
                        "instance": s["instance"], "record_index": rec["index"],
                        "season_witness": s["season_witness"]}
                opponent_binds = name_key(values.get("opponent")) in away
                date = values.get("event_date")
                if date is None:
                    if opponent_binds:
                        occurrences.append({**base, "relation": "BOUND_OPPONENT_DATE_UNDETERMINED",
                                            "opponent": values.get("opponent"),
                                            "reason": values.get("event_date_reason") or "DATE_MEMBER_UNPARSED"})
                    continue
                if opponent_binds and date in dates:
                    bound.append({**base, "members": rec["members"], "values": values})
                elif opponent_binds:
                    occurrences.append({**base, "relation": "BOUND_OPPONENT_OTHER_DATE", "opponent":
                                        values.get("opponent"), "event_date": date})
                elif date in dates:
                    occurrences.append({**base, "relation": "UNBOUND_OPPONENT_ON_EVENT_DATE",
                                        "opponent": values.get("opponent"), "event_date": date})
    fields: dict[str, Any] = {}
    reasons: list[str] = []
    other_on_date = [o for o in occurrences if o["relation"] == "UNBOUND_OPPONENT_ON_EVENT_DATE"]
    other_dates = [o for o in occurrences if o["relation"] == "BOUND_OPPONENT_OTHER_DATE"]

    def witness(w: dict[str, Any], member: str, raw: Any, value: Any) -> dict[str, Any]:
        return {"document": w["document"], "logical": w["logical"], "structure": w["structure"],
                "instance": w["instance"], "record_index": w["record_index"], "member": member, "raw": raw,
                "value": value}
    member_names = {"SIDEARM_NUXT_SCHEDULE": {"opponent": "opponent.title", "designation": "location_indicator",
                                              "facility": "facility.title", "location": "location"},
                    "SIDEARM_TEXT_TABLE": {"opponent": "Opponent", "designation": "At", "facility": "Location",
                                           "location": "Location"},
                    "WMT_SCHEDULE_LIST": {"opponent": "opponent_name", "designation": "venue_class",
                                          "facility": "location", "location": "location"}}
    if bound:
        disposition = "RECORD_BOUND"
        season = [witness(w, w["season_witness"]["member"], w["season_witness"]["raw"], SEASON) for w in bound]
        fields["season"] = {"state": "SUPPORTED", "value": SEASON, "comparison": "AGREES", "witnesses": season}
        opp = [witness(w, member_names[w["structure"]]["opponent"],
                       w["members"][member_names[w["structure"]]["opponent"]], w["values"]["opponent"]) for w in bound]
        fields["opponent"] = {"state": "CONFLICTING" if other_on_date else "SUPPORTED",
                              "value": sorted({w["value"] for w in opp}) if not other_on_date else
                              sorted({w["value"] for w in opp} | {o["opponent"] or "" for o in other_on_date}),
                              "comparison": "AGREES" if not other_on_date else "NOT_COMPARABLE",
                              "witnesses": opp}
        dwit = [witness(w, w["values"]["event_date_member"], w["members"].get(w["values"]["event_date_member"]),
                        w["values"]["event_date"]) for w in bound]
        state, value = _single([w["value"] for w in dwit])
        fields["event_date"] = {"state": state, "value": value, "comparison": "AGREES" if state == "SUPPORTED" and
                                value in dates else "NOT_COMPARABLE", "witnesses": dwit}
        for field, key in (("designation", "designation"), ("venue_facility", "facility"),
                           ("venue_location", "location")):
            member = {"designation": "designation", "venue_facility": "facility", "venue_location": "location"}[field]
            wits = [witness(w, member_names[w["structure"]][member], w["members"].get(member_names[w["structure"]][
                member]), w["values"].get(key)) for w in bound if w["values"].get(key) is not None]
            state, value = _single([w["value"] for w in wits])
            if field == "designation":
                comparison = "NOT_COMPARABLE" if state != "SUPPORTED" else (
                    "AGREES" if value == claims["owner_designation"] else "DISAGREES")
            elif field == "venue_facility":
                provider = claims["venue"]["full_name"]
                comparison = "NOT_COMPARABLE" if state != "SUPPORTED" or not provider else (
                    "AGREES" if name_key(value) == name_key(provider) else "TEXT_DIFFERS")
            else:
                comparison = "NOT_COMPARABLE"
            fields[field] = {"state": state, "value": value, "comparison": comparison, "witnesses": wits}
        twits = [{"document": w["document"], "logical": w["logical"], "structure": w["structure"],
                  "instance": w["instance"], "record_index": w["record_index"], "statements": w["values"]["time"]}
                 for w in bound]
        resolved = resolve_time([{"time": w["values"]["time"]} for w in bound])
        comparison = "NOT_COMPARABLE"
        if resolved["state"] == "SUPPORTED_INSTANT":
            provider = claims["scheduled_utc"].replace("Z", ".000000Z")
            comparison = "AGREES" if resolved["value"]["utc"] == provider else "DISAGREES"
        fields["scheduled_time"] = {"state": resolved["state"], "value": resolved["value"],
                                    "reasons": resolved["reasons"], "comparison": comparison, "witnesses": twits}
    else:
        if not docs:
            disposition = "SOURCE_NOT_RETRIEVED"
        elif not any(any(s["matched"] and s["season_bound"] for s in d["_structures"]) for d in docs):
            disposition = "NO_DECLARED_STRUCTURE"
        elif not any(d["qualified"] for d in docs):
            disposition = "OWNER_NOT_VERIFIED"
        elif other_dates:
            disposition = "OPPONENT_RECORD_ON_OTHER_DATE"
        elif other_on_date:
            disposition = "UNBOUND_OPPONENT_ON_EVENT_DATE"
        else:
            disposition = "NO_RECORD_FOR_EVENT"
        reasons.append(disposition)
        for field in FIELDS:
            fields[field] = {"state": "UNSUPPORTED", "value": None, "comparison": "NOT_COMPARABLE", "witnesses": []}
        if disposition == "OPPONENT_RECORD_ON_OTHER_DATE":
            fields["event_date"] = {"state": "CONFLICTING", "value": sorted({o["event_date"] for o in other_dates}),
                                    "comparison": "DISAGREES", "witnesses": []}
        if disposition == "UNBOUND_OPPONENT_ON_EVENT_DATE":
            fields["opponent"] = {"state": "UNSUPPORTED", "value": None, "comparison": "NOT_COMPARABLE",
                                  "witnesses": [], "reasons": ["UNBOUND_OPPONENT_NAME_ON_EVENT_DATE"],
                                  "unbound_names": sorted({o["opponent"] or "" for o in other_on_date})}
        fields["scheduled_time"]["reasons"] = [disposition]
    return {"disposition": disposition, "disposition_reasons": reasons, "fields": fields,
            "occurrences": sorted(({k: v for k, v in o.items() if k != "season_witness"} for o in occurrences),
                                  key=lambda o: (o["logical"], o["structure"], o["instance"], o["record_index"]))}


def expected_events(spec: dict[str, Any], shadow_binding: dict[str, Any], raw_provider: dict[str, Any]
                    ) -> list[dict[str, Any]]:
    """The 25 expected events from the contract cohort checked against the verified shadow (event keys, teams,
    scheduled instants) with the frozen provider claims read from the shadow's bundled raw response."""
    payload = shadow_binding["payload"]
    shadow_events = {e["event_key"]: e for e in payload["events"]}
    cohort = spec["expected"]["events"]
    if sorted(c["event_key"] for c in cohort) != sorted(shadow_events) or \
            len(cohort) != spec["expected"]["expected_events"] or len(set(c["event_key"] for c in cohort)) != len(cohort):
        raise ScheduleError("SCHEDULE_COHORT_MISMATCH", "the contract cohort is not the shadow's event population")

    def pointer(doc: Any, text: str) -> Any:
        cur = doc
        for step in [s for s in text.split("/") if s]:
            cur = cur[int(step)] if isinstance(cur, list) else cur[step]
        return cur
    out = []
    for c in cohort:
        ev = shadow_events[c["event_key"]]
        if (ev["home_team_key"], ev["away_team_key"], ev["provider_scheduled_utc"]) != \
                (c["home_team_key"], c["away_team_key"], c["provider_scheduled_utc"]):
            raise ScheduleError("SCHEDULE_COHORT_MISMATCH", f"{c['event_key']} differs from the frozen shadow event")
        home = pointer(raw_provider, ev["home_participant_pointer"])
        away = pointer(raw_provider, ev["away_participant_pointer"])
        competition = pointer(raw_provider, ev["home_participant_pointer"].rsplit("/competitors/", 1)[0])
        names = ("displayName", "shortDisplayName", "name", "location", "abbreviation")
        venue = competition.get("venue") or {}
        neutral = competition.get("neutralSite")
        out.append({"event_key": c["event_key"], "season": ev["season"],
                    "owner": {"side": "home", "team_key": ev["home_team_key"], "ncaa_org_id": c["owner"]["ncaa_org_id"],
                              "official_name": c["owner"]["official_name"],
                              "directory_host": c["owner"]["directory_host"],
                              "host_family": sorted(_family(c["owner"]["directory_host"])),
                              "provider_names": {k: (home.get("team") or {}).get(k) for k in names}},
                    "opponent": {"side": "away", "team_key": ev["away_team_key"],
                                 "provider_names": {k: (away.get("team") or {}).get(k) for k in names}},
                    "provider_claims": {"scheduled_utc": ev["provider_scheduled_utc"],
                                        "local_date_set": provider_date_set(ev["provider_scheduled_utc"]),
                                        "neutral_site": neutral if isinstance(neutral, bool) else None,
                                        "owner_designation": "NEUTRAL" if neutral is True else "HOME",
                                        "venue": {"full_name": venue.get("fullName"),
                                                  "city": (venue.get("address") or {}).get("city"),
                                                  "state": (venue.get("address") or {}).get("state")},
                                        "source": "FROZEN_PROVIDER_CLAIM_FROM_THE_ACCEPTED_SHADOW"}})
    return out


def processing_order(count: int, order: str | None) -> list[int]:
    indices = list(range(count))
    if order in (None, "natural"):
        return indices
    if order == "reversed":
        return indices[::-1]
    if isinstance(order, str) and order.startswith("shuffled:"):
        random.Random(order).shuffle(indices)
        return indices
    raise ScheduleError("PROCESSING_ORDER_INVALID", f"unknown processing order {order!r}")


def derive_schedule(spec: dict[str, Any], contract_sha256: str, shadow_binding: dict[str, Any],
                    raw_provider: dict[str, Any], segments: dict[str, bytes], raw: dict[str, bytes], *,
                    order: str | None = None) -> dict[str, Any]:
    """The complete schedule document re-derived from the verified shadow, the contract, the journal and the bodies."""
    events = expected_events(spec, shadow_binding, raw_provider)
    # the capture names the contract committed before it; a successor contract may name its predecessor explicitly
    capture_contract = spec.get("capture_contract_sha256") or contract_sha256
    journal = verify_journal(segments, raw, events, spec["acquisition"], capture_contract, spec["shadow"]["identity"])
    by_event = {e["event_key"]: e for e in events}
    attempts_by_seq = {a["seq"]: a for a in journal["attempts"]}
    logical = journal["logical"]
    stage = {route: i + 1 for i, route in enumerate(ROUTE_ORDER)}
    sources: list[dict[str, Any]] = []
    docs_by_event: dict[str, list[dict[str, Any]]] = {k: [] for k in by_event}
    qualified_before: dict[str, bool] = {k: False for k in by_event}
    seen_routes: dict[tuple[str, str], int] = {}
    for name in journal["order"]:
        entry = logical[name]
        event = by_event[entry["event_key"]]
        route = entry["route"]
        count = seen_routes.get((entry["event_key"], route), 0)
        seen_routes[(entry["event_key"], route)] = count + 1
        if count:
            raise ScheduleError("SCHEDULE_ROUTE_POLICY_VIOLATED", f"{entry['event_key']} repeats route {route}")
        if route != "INITIAL_SEASON_ROUTE" and qualified_before[entry["event_key"]]:
            raise ScheduleError("SCHEDULE_ROUTE_POLICY_VIOLATED", f"{name}: a fallback after a qualified document")
        if entry["hops"] and not _route_url_ok(entry, event, raw, attempts_by_seq):
            raise ScheduleError("SCHEDULE_ROUTE_POLICY_VIOLATED", f"{name}: {entry['url']} is not its route")
        document = None
        if entry["outcome"] == "RETAINED_200":
            last = entry["hops"][-1]
            sha = last["result"]["body_sha256"]
            census = document_census(sha, raw[sha], event)
            census["logical"] = name
            docs_by_event[entry["event_key"]].append(census)
            if census["qualified"]:
                qualified_before[entry["event_key"]] = True
            document = {k: v for k, v in census.items() if not k.startswith("_") and k != "logical"}
        hops = [{"seq": h["seq"], "hop": h["hop"], "url": h["url"], "start_utc": h["start_utc"],
                 "start_ns": h["start_ns"], "status": (h["result"] or {}).get("status"),
                 "headers": (h["result"] or {}).get("headers"), "body_sha256": (h["result"] or {}).get("body_sha256"),
                 "body_bytes": (h["result"] or {}).get("body_bytes"), "truncated": (h["result"] or {}).get("truncated"),
                 "error": (h["result"] or {}).get("error"), "end_utc": (h["result"] or {}).get("end_utc"),
                 "end_ns": (h["result"] or {}).get("end_ns"), "location": h["location"],
                 "interrupted": h["result"] is None} for h in entry["hops"]]
        sources.append({"record_type": "source", "event_key": entry["event_key"], "logical": name, "route": route,
                        "stage": stage[route], "url": entry["url"], "outcome": entry["outcome"], "hops": hops,
                        "attempts": len(hops), "decision": entry["decision"], "link_source": entry["link_source"],
                        "document": document, **{"labels": dict(RECORD_LABELS)}})
    records = []
    for index in processing_order(len(events), order):
        event = events[index]
        key = event["event_key"]
        mine = [s for s in sources if s["event_key"] == key]
        result = qualify_event(event, docs_by_event[key])
        records.append({"record_type": "schedule_event", "event_key": key, "season": event["season"],
                        "owner": event["owner"], "opponent": event["opponent"],
                        "provider_claims": event["provider_claims"],
                        "requests": [s["logical"] for s in mine], "attempts": sum(s["attempts"] for s in mine),
                        "documents": [d["document"] for d in docs_by_event[key]],
                        "disposition": result["disposition"], "disposition_reasons": result["disposition_reasons"],
                        "fields": result["fields"], "occurrences": result["occurrences"],
                        "labels": dict(RECORD_LABELS)})
    records.sort(key=lambda r: r["event_key"])
    for key in by_event:
        if not any(s["event_key"] == key for s in sources):
            raise ScheduleError("SCHEDULE_EVENT_WITHOUT_SOURCE_RECORD", f"{key} has no request or decision")
    segment_rows = [{"file": n, "sha256": sha256_hex(segments[n]), "bytes": len(segments[n])}
                    for n in sorted(segments)]
    bound = journal["availability_bound_utc"]
    if bound is None:
        raise ScheduleError("SCHEDULE_JOURNAL_EMPTY", "the journal records no attempt")
    anchor_utc = shadow_binding["snapshot"]["anchor"]["created_utc"]
    if parse_utc_text(bound) <= parse_utc_text(anchor_utc):
        raise ScheduleError("SCHEDULE_RETROACTIVE_BOUND", "the availability bound does not follow the shadow anchor")
    summary = summary_document(records, sources)
    return {"schema": SCHEMA, "population": POPULATION, "designation": DESIGNATION,
            "contract": {"id": CONTRACT_ID, "sha256": contract_sha256},
            "shadow": {**spec["shadow"], "anchor_created_utc": anchor_utc,
                       "timing_basis": shadow_binding["snapshot"]["timing"]["basis"],
                       "unchanged": "the shadow's predictions, anchor and PRE_PROVIDER_REPORTED_START basis are not "
                                    "modified, re-evaluated or re-anchored by this evidence"},
            "acquisition": {"journal_segments": segment_rows, "attempts": len(journal["attempts"]),
                            "ceiling": spec["acquisition"]["ceiling_attempts"], "logical_requests": len(sources),
                            "documents": sum(1 for s in sources if s["document"]),
                            "stopped_host_families": journal["stopped_families"],
                            "first_start_utc": journal["first_start_utc"], "availability_bound_utc": bound,
                            "availability_rule": AVAILABILITY_RULE, "raw_bodies": len(raw)},
            "labels": dict(LABELS), "events": records, "sources": sources, "summary": summary,
            "counts": {"events": len(records), "participants": 2 * len(records), "sources": len(sources),
                       "attempts": len(journal["attempts"]), "documents": sum(1 for s in sources if s["document"]),
                       "record_bound_events": sum(r["disposition"] == "RECORD_BOUND" for r in records)}}


def summary_document(records: list[dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    dispositions = {d: sum(r["disposition"] == d for r in records) for d in DISPOSITIONS}
    fields = {}
    for field in FIELDS:
        states: dict[str, int] = {}
        comparisons: dict[str, int] = {}
        for r in records:
            f = r["fields"][field]
            states[f["state"]] = states.get(f["state"], 0) + 1
            comparisons[f["comparison"]] = comparisons.get(f["comparison"], 0) + 1
        fields[field] = {"states": dict(sorted(states.items())), "comparisons": dict(sorted(comparisons.items()))}
    outcomes: dict[str, int] = {}
    for s in sources:
        outcomes[s["outcome"]] = outcomes.get(s["outcome"], 0) + 1
    return {"dispositions": dispositions, "fields": fields, "request_outcomes": dict(sorted(outcomes.items())),
            "statuses": dict(sorted({str(h["status"]): sum(1 for s in sources for x in s["hops"] if
                                                            x["status"] == h["status"])
                                     for s in sources for h in s["hops"]}.items()))}


# --------------------------------------------------------------------------------------------- contract

def contract_code_document() -> dict[str, Any]:
    """Every rule member of the committed contract that must equal the frozen code."""
    return {"labels": LABELS, "record_labels": RECORD_LABELS, "numeric_contract": NUMERIC_CONTRACT,
            "acquisition": ACQUISITION, "routes": ROUTES, "route_order": list(ROUTE_ORDER),
            "decisions": list(DECISIONS), "request_outcomes": list(REQUEST_OUTCOMES), "structures": STRUCTURES,
            "text_rule": TEXT_RULE, "name_rules": NAME_RULES, "fields": list(FIELDS), "field_states": list(FIELD_STATES),
            "time_states": list(TIME_STATES), "comparisons": list(COMPARISONS), "dispositions": list(DISPOSITIONS),
            "field_rules": FIELD_RULES, "time_rules": TIME_RULES, "availability_rule": AVAILABILITY_RULE,
            "grains": list(GRAINS), "event_fields": list(EVENT_FIELDS),
            "source_fields": list(SOURCE_FIELDS), "top_level": list(TOP_LEVEL), "families": list(FAMILIES),
            "journal_schema": JOURNAL_SCHEMA, "profile_fields": list(PROFILE_FIELDS)}


def _spec(contract: bytes, contract_sha256: str, chunk_size: int = 1 << 20) -> dict[str, Any]:
    if pv._hash_chunks(contract, chunk_size) != contract_sha256:
        raise ScheduleError("CONTRACT_NOT_COMMITTED_AUTHORITY", f"the bundled contract hashes to {sha256_hex(contract)},"
                                                                f" not the committed {contract_sha256}")
    spec = strict_json(contract, "CONTRACT_MALFORMED")
    if not isinstance(spec, dict) or spec.get("contract_id") != CONTRACT_ID or spec.get("population_id") != POPULATION:
        raise ScheduleError("CONTRACT_MALFORMED", "the contract is not the official shadow schedule contract")
    for member, constant in contract_code_document().items():
        if not _same(spec.get(member), constant):
            raise ScheduleError("CONTRACT_CODE_DISAGREEMENT", f"the contract's {member} differ from the frozen code")
    pins = spec.get("shadow")
    if not isinstance(pins, dict) or set(pins) != set(PRODUCTION_SHADOW) or pins.get("population") != sh.POPULATION or \
            not all(isinstance(pins.get(k), str) and IDENTITY_RE.match(pins[k]) for k in (
                "identity", "snapshot_sha256", "payload_sha256", "contract_sha256")):
        raise ScheduleError("CONTRACT_MALFORMED", "the contract does not pin the accepted shadow")
    expected = spec.get("expected")
    if not isinstance(expected, dict) or not isinstance(expected.get("events"), list) or \
            type(expected.get("expected_events")) is not int or type(expected.get("expected_participants")) is not int:
        raise ScheduleError("CONTRACT_MALFORMED", "the contract does not pin the expected cohort")
    for row in expected["events"]:
        owner = row.get("owner") if isinstance(row, dict) else None
        if not isinstance(owner, dict) or not all(isinstance(owner.get(k), str) for k in (
                "official_name", "directory_host", "directory_pointer")) or type(owner.get("ncaa_org_id")) is not int \
                or not EVENT_KEY_RE.match(str(row.get("event_key"))):
            raise ScheduleError("CONTRACT_MALFORMED", "an expected event does not pin its owner institution")
    return spec


# --------------------------------------------------------------------------------------------- identity

def bundle_names(segments: Iterable[str], raw: Iterable[str]) -> list[str]:
    return sorted([CONTRACT_MEMBER, *segments, *(f"{RAW_PREFIX}{sha}.gz" for sha in raw)])


def identity_document(schedule: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    return {"schema": IDENTITY_SCHEMA, "population": POPULATION, "contract_id": CONTRACT_ID,
            "contract_sha256": schedule["contract"]["sha256"], "shadow_identity": schedule["shadow"]["identity"],
            "schedule_file": SCHEDULE_FILE, "schedule_sha256": sha256_hex(file_bytes(schedule)), "bundle": bundle}


def schedule_identity(schedule: dict[str, Any], bundle: dict[str, Any]) -> str:
    return sha256_hex(canonical_bytes(identity_document(schedule, bundle)))


def profile_of(schedule: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    segments = schedule["acquisition"]["journal_segments"]
    return {"schedule_identity": schedule_identity(schedule, bundle),
            "schedule_sha256": sha256_hex(file_bytes(schedule)),
            "journal_sha256": sha256_hex(canonical_bytes([[s["file"], s["sha256"]] for s in segments])),
            "attempts": schedule["acquisition"]["attempts"],
            "availability_bound_utc": schedule["acquisition"]["availability_bound_utc"]}


def first_difference(expected: dict[str, Any], actual: Any) -> tuple[str, str] | None:
    if not isinstance(actual, dict) or set(actual) != set(TOP_LEVEL):
        extra = sorted(set(actual) - set(TOP_LEVEL)) if isinstance(actual, dict) else ["<not an object>"]
        missing = sorted(set(TOP_LEVEL) - set(actual)) if isinstance(actual, dict) else []
        return "SCHEMA", f"top-level members differ (extra {extra}, missing {missing})"
    if not _same(expected["schema"], actual["schema"]) or not _same(expected["population"], actual["population"]):
        return "SCHEMA", "schema or population differs"
    for family, member in (("DESIGNATION", "designation"), ("CONTRACT", "contract"), ("SHADOW", "shadow"),
                           ("ACQUISITION", "acquisition"), ("LABELS", "labels")):
        if not _same(expected[member], actual[member]):
            return family, f"{member} differs"
    for name, key, fields, ident in (("EVENT", "events", EVENT_FIELDS, lambda r: r.get("event_key")),
                                     ("SOURCE", "sources", SOURCE_FIELDS, lambda r: r.get("logical"))):
        want, got = expected[key], actual[key]
        if not isinstance(got, list) or not all(isinstance(r, dict) for r in got) or \
                not _same([ident(r) for r in want], [ident(r) for r in got]):
            return f"{name}_MEMBERSHIP", f"{key} membership, multiplicity or order differs"
        for index, (w, g) in enumerate(zip(want, got)):
            if set(g) != set(fields):
                return f"{name}_RECORD", f"{key}[{index}] members differ"
            for field in fields:
                if not _same(w[field], g[field]):
                    return f"{name}_RECORD", f"{key}[{index}].{field} differs"
    if not _same(expected["summary"], actual["summary"]):
        return "SUMMARY", "summary differs"
    if not _same(expected["counts"], actual["counts"]):
        return "COUNTS", "counts differ"
    return None


# --------------------------------------------------------------------------------------------- reader

def literal_location(path: Path | str) -> str:
    try:
        return sh.literal_location(path)
    except sh.ShadowError as exc:
        code = exc.code.replace("SHADOW_", "SCHEDULE_", 1)
        raise ScheduleError(code, str(exc)) from exc


def _shadow(shadow_path: Path | str, spec: dict[str, Any], shadow_profile: Any) -> dict[str, Any]:
    pins = spec["shadow"]
    kwargs = {} if shadow_profile is PINNED else {"profile": shadow_profile}
    try:
        binding = sh.verify_snapshot(shadow_path, contract_sha256=pins["contract_sha256"],
                                     expect_identity=pins["identity"], **kwargs)
    except sh.ShadowError as exc:
        raise ScheduleError(f"SCHEDULE_SHADOW_{exc.code}", str(exc)) from exc
    if binding["snapshot_sha256"] != pins["snapshot_sha256"] or binding["payload_sha256"] != pins["payload_sha256"]:
        raise ScheduleError("SCHEDULE_SHADOW_NOT_PINNED", "the selected shadow is not the pinned accepted snapshot")
    return binding


def _raw_provider(binding: dict[str, Any]) -> dict[str, Any]:
    directory = os.path.dirname(pv.io_path(binding["location"]))
    payload = binding["payload"]
    rel = (f"{sh.PREVIEW_ROOT}/{binding['preview_identity']}/{pv.CAPSULE_ROOT}/{binding['capsule_identity']}/raw/"
           "provider-response.json")
    data = sh._read(os.path.join(directory, *rel.split("/")), "SCHEDULE_SHADOW_RAW_MISSING")
    if sha256_hex(data) != payload["source"]["source_body_sha256"]:
        raise ScheduleError("SCHEDULE_SHADOW_RAW_MISMATCH", "the shadow's bundled raw response is not its source body")
    return strict_json(data, "SCHEDULE_SHADOW_RAW_MALFORMED")


def split_members(files: dict[str, bytes]) -> tuple[dict[str, bytes], dict[str, bytes]]:
    segments, raw = {}, {}
    for name, data in files.items():
        if JOURNAL_NAME_RE.match(name):
            segments[name] = data
        elif RAW_NAME_RE.match(name):
            sha = RAW_NAME_RE.match(name).group(1)
            try:
                body = gzip.decompress(data)
            except (OSError, EOFError) as exc:
                raise ScheduleError("SCHEDULE_RAW_BODY_MALFORMED", f"{name} is not gzip") from exc
            if sha256_hex(body) != sha:
                raise ScheduleError("SCHEDULE_RAW_BODY_MISMATCH", f"{name} does not hash to its name")
            if gzip.compress(body, mtime=0) != data:
                raise ScheduleError("SCHEDULE_RAW_BODY_NOT_CANONICAL", f"{name} is not the canonical gzip encoding")
            raw[sha] = body
        elif name != CONTRACT_MEMBER:
            raise ScheduleError("SCHEDULE_BUNDLE_MEMBERSHIP_MISMATCH", f"unexpected member {name}")
    if not segments:
        raise ScheduleError("SCHEDULE_BUNDLE_MEMBERSHIP_MISMATCH", "no acquisition journal segment")
    return segments, raw


def verify_sidecar(path: Path | str, shadow_path: Path | str, *, contract_sha256: str = CONTRACT_SHA256,
                   expect_identity: str | None = None, profile: Any = PINNED, shadow_profile: Any = PINNED,
                   require_pinned_profile: bool = True) -> dict[str, Any]:
    """Verify a sidecar directory completely against the selected accepted shadow and return its binding."""
    location = literal_location(path)
    if not os.path.isfile(pv.io_path(location)):
        raise ScheduleError("SCHEDULE_MISSING", f"no schedule file at {location}")
    directory, name = os.path.split(location)
    if name != SCHEDULE_FILE or not IDENTITY_RE.match(os.path.basename(directory)):
        raise ScheduleError("SCHEDULE_LOCATION_INVALID", f"the sidecar must be <identity>/{SCHEDULE_FILE} with a 64-hex "
                                                         "identity directory")
    io_directory = pv.io_path(directory)
    files = pv.directory_files(io_directory)
    got = files.pop(SCHEDULE_FILE, None)
    if got is None:
        raise ScheduleError("SCHEDULE_MISSING", f"no schedule file at {location}")
    contract = files.get(CONTRACT_MEMBER)
    if contract is None:
        raise ScheduleError("SCHEDULE_BUNDLE_MEMBERSHIP_MISMATCH", "the bundled contract is missing")
    spec = _spec(contract, contract_sha256)
    shadow_binding = _shadow(shadow_path, spec, shadow_profile)
    segments, raw = split_members(files)
    expected = derive_schedule(spec, contract_sha256, shadow_binding, _raw_provider(shadow_binding), segments, raw)
    if got != file_bytes(expected):
        supplied = strict_json(got, "SCHEDULE_MALFORMED")
        diff = first_difference(expected, supplied)
        family, detail = diff if diff else ("CANONICAL_FORM", "the schedule bytes are not the frozen canonical form")
        raise ScheduleError(f"SCHEDULE_{family}_MISMATCH", detail)
    bundle = {n: {"sha256": sha256_hex(files[n]), "bytes": len(files[n])} for n in sorted(files)}
    if sorted(bundle) != bundle_names(segments, raw):
        raise ScheduleError("SCHEDULE_BUNDLE_MEMBERSHIP_MISMATCH", "the bundle members differ from the journal")
    identity = schedule_identity(expected, bundle)
    if os.path.basename(directory) != identity:
        raise ScheduleError("SCHEDULE_IDENTITY_MISMATCH", f"the identity document hashes to {identity}, the directory "
                                                          f"is {os.path.basename(directory)}")
    if expect_identity is not None and expect_identity != identity:
        raise ScheduleError("STALE_SCHEDULE_IDENTITY", f"expected {expect_identity}, found {identity}")
    actual_profile = profile_of(expected, bundle)
    pinned = SCHEDULE_PROFILE if profile is PINNED else profile
    if require_pinned_profile:
        if pinned is None:
            raise ScheduleError("SCHEDULE_PROFILE_NOT_PINNED", "no actual sidecar profile is packaged")
        if not isinstance(pinned, dict) or set(pinned) != set(PROFILE_FIELDS):
            raise ScheduleError("SCHEDULE_PROFILE_NOT_PINNED", "the packaged sidecar profile is malformed")
        if any(not _same(pinned[k], actual_profile[k]) for k in PROFILE_FIELDS):
            raise ScheduleError("SCHEDULE_NOT_PINNED_SIDECAR", "the sidecar is not the one the packaged gate pins")
    return {"schedule_identity": identity, "schedule_sha256": sha256_hex(got), "location": location,
            "identity_document": identity_document(expected, bundle), "schedule": expected, "bundle": bundle,
            "profile": actual_profile, "profile_pinned": isinstance(pinned, dict) and
            all(_same(pinned.get(k), actual_profile[k]) for k in PROFILE_FIELDS),
            "shadow_identity": shadow_binding["snapshot_identity"]}


def parse_cutoff(value: str | None) -> _dt.datetime:
    """The strict cutoff of the accepted shadow mode (whole-string grammar; clean CUTOFF_OUT_OF_RANGE refusal)."""
    try:
        return sh.parse_cutoff(value)
    except sh.ShadowError as exc:
        raise ScheduleError(exc.code, str(exc).split(": ", 1)[-1]) from exc


def normalize_event(value: str) -> str:
    if not isinstance(value, str) or not EVENT_KEY_RE.match(value):
        raise ScheduleError("EVENT_KEY_INVALID", f"event must be espn:event:<digits>, got {value!r}")
    return value


def normalize_team(value: str) -> str:
    if not isinstance(value, str) or not TEAM_KEY_RE.match(value):
        raise ScheduleError("TEAM_KEY_INVALID", f"team must be espn:team:<digits>, got {value!r}")
    return value


class ScheduleEvidence:
    """A completely verified sidecar; rows come only from its re-derived document."""

    def __init__(self, path: Path | str, shadow_path: Path | str, *, contract_sha256: str = CONTRACT_SHA256,
                 expect_identity: str | None = None, profile: Any = PINNED, shadow_profile: Any = PINNED) -> None:
        self.binding = verify_sidecar(path, shadow_path, contract_sha256=contract_sha256,
                                      expect_identity=expect_identity, profile=profile, shadow_profile=shadow_profile)
        self.schedule = self.binding["schedule"]

    def __enter__(self) -> "ScheduleEvidence":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    @staticmethod
    def filters(grain: str, *, season: int | None = None, event: str | None = None,
                team: str | None = None) -> dict[str, Any]:
        if grain not in GRAINS:
            raise ScheduleError("SCHEDULE_GRAIN_REQUIRED", f"--schedule-evidence serves only {list(GRAINS)}, not "
                                                           f"{grain!r}")
        out: dict[str, Any] = {}
        if season is not None:
            if isinstance(season, bool) or not isinstance(season, int):
                raise ScheduleError("SEASON_INVALID", f"season must be an integer, got {season!r}")
            out["season"] = season
        if event is not None:
            out["event"] = normalize_event(event)
        if team is not None:
            out["team"] = normalize_team(team)
        return out

    def query(self, grain: str, *, cutoff: str | None = None, season: int | None = None, event: str | None = None,
              team: str | None = None, limit: int | None = 50, offset: int = 0,
              all_rows: bool = False) -> dict[str, Any]:
        filters = self.filters(grain, season=season, event=event, team=team)
        if offset < 0:
            raise ScheduleError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise ScheduleError("NEGATIVE_LIMIT", "limit must be zero or positive")
        when = parse_cutoff(cutoff)
        acquisition = self.schedule["acquisition"]
        bound = parse_utc_text(acquisition["availability_bound_utc"])
        if when < bound:
            raise ScheduleError("SCHEDULE_UNAVAILABLE_BEFORE_OBSERVATION_BOUND",
                                f"the sidecar's observations end at {acquisition['availability_bound_utc']}; nothing "
                                f"was observed by {iso_micro(when)}")
        identity = self.binding["schedule_identity"]
        result: dict[str, Any] = {
            "schedule_identity": identity, "schedule_sha256": self.binding["schedule_sha256"],
            "contract_id": CONTRACT_ID, "contract_sha256": self.schedule["contract"]["sha256"],
            "population": POPULATION, "designation": DESIGNATION, "shadow_identity": self.binding["shadow_identity"],
            "grain": grain, "filters": filters, "cutoff": {"literal": cutoff, "utc": iso_micro(when)},
            "availability": {"bound_utc": acquisition["availability_bound_utc"], "state": AVAILABLE_STATE,
                             "rule": AVAILABILITY_RULE},
            "acquisition": {k: acquisition[k] for k in ("attempts", "ceiling", "logical_requests", "documents",
                                                        "stopped_host_families", "first_start_utc")},
            "labels": self.schedule["labels"], "offset": offset, "limit": None if all_rows else limit}
        if season is not None and season != SEASON:
            result.update(season_scope_state=OUT_OF_SCOPE_STATE, total=0, returned=0, rows=[], next_offset=None,
                          note="only the frozen 2026 October 17 shadow cohort has official schedule evidence; no row "
                               "is fabricated")
            return result
        teams = {e["event_key"]: {e["owner"]["team_key"], e["opponent"]["team_key"]} for e in self.schedule["events"]}
        source = self.schedule["events"] if grain == "shadow-schedule" else self.schedule["sources"]
        items = [x for x in source if filters.get("event", x["event_key"]) == x["event_key"] and
                 ("team" not in filters or filters["team"] in teams.get(x["event_key"], set()))]
        total = len(items)
        stop = None if all_rows else offset + (limit or 0)
        key = GRAIN_KEY[grain]
        rows = [{key: item, "schedule_identity": identity,
                 "availability_bound_utc": acquisition["availability_bound_utc"], "labels": dict(RECORD_LABELS)}
                for item in items[offset:stop]]
        result.update(season_scope_state=IN_SCOPE_STATE, total=total, returned=len(rows), rows=rows,
                      next_offset=offset + len(rows) if offset + len(rows) < total else None)
        return result


# --------------------------------------------------------------------------------------------- build helpers

def read_acquisition(directory: Path | str) -> tuple[dict[str, bytes], dict[str, bytes]]:
    """The journal segments (``journal-NN.jsonl``) and retained bodies (``bodies/<sha256>.gz``) of one capture."""
    root = Path(directory)
    segments = {f"{JOURNAL_PREFIX}{p.name[len('journal-'):]}": p.read_bytes()
                for p in sorted(root.glob("journal-*.jsonl"))}
    bodies = {}
    for p in sorted((root / "bodies").glob("*.gz")):
        bodies[f"{RAW_PREFIX}{p.name}"] = gzip.compress(gzip.decompress(p.read_bytes()), mtime=0)
    return segments, bodies


def sidecar_files(contract: bytes, shadow_path: Path | str, segments: dict[str, bytes], raw_members: dict[str, bytes],
                  *, contract_sha256: str = CONTRACT_SHA256, order: str | None = None, chunk_size: int = 1 << 20,
                  shadow_profile: Any = PINNED) -> tuple[str, dict[str, bytes], dict[str, Any], dict[str, Any]]:
    """The identity, every file of the sidecar directory, the identity document and the schedule document."""
    spec = _spec(contract, contract_sha256, chunk_size)
    shadow_binding = _shadow(shadow_path, spec, shadow_profile)
    members = {CONTRACT_MEMBER: contract, **segments, **raw_members}
    seg, raw = split_members(members)
    names = sorted(raw)
    shuffled = {names[i]: raw[names[i]] for i in processing_order(len(names), order)}
    schedule = derive_schedule(spec, contract_sha256, shadow_binding, _raw_provider(shadow_binding), seg, shuffled,
                               order=order)
    bundle = {n: {"sha256": pv._hash_chunks(members[n], chunk_size), "bytes": len(members[n])} for n in sorted(members)}
    files = {SCHEDULE_FILE: file_bytes(schedule), **members}
    return schedule_identity(schedule, bundle), files, identity_document(schedule, bundle), schedule


__all__ = ["ScheduleEvidence", "ScheduleError", "derive_schedule", "document_census", "expected_events",
           "extract_document", "first_difference", "identity_document", "parse_cutoff", "parse_time_text",
           "profile_of", "qualify_event", "read_acquisition", "record_values", "resolve_time", "schedule_identity",
           "sidecar_files", "verify_journal", "verify_sidecar", "zone_offset", "CONTRACT_SHA256", "GRAINS", "LABELS",
           "RECORD_LABELS", "SCHEDULE_PROFILE", "STRUCTURES"]
