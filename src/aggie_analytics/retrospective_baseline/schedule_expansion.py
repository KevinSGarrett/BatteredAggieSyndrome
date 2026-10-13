r"""Explicit immutable successor ("expansion") of the BAT-726 official schedule evidence (BAT-727; TP55-A01).

``bas-retrospective-baseline-query --prospective-shadow <...provider_record_shadow_20261017\sha256\<id>\snapshot.json>
--schedule-evidence <...official_shadow_schedule_expansion_20261017\sha256\<identity>\schedule.json>
--grain shadow-schedule|shadow-schedule-source --cutoff <instant with zone> [--season 2026] [--event espn:event:<id>]
[--team espn:team:<id>] [--limit 50] [--offset 0] [--all]``

One private, create-only, content-addressed successor sidecar re-qualifies the accepted BAT-726 evidence (V1 identity
``a99d7076...``) for all 25 events of the accepted BAT-725 October 17 UNTRUSTED_SHADOW snapshot under a separately
frozen and disclosed policy, using only the retained Cycle 54 capture: the complete V1 sidecar (its journal of 46
attempts, its 40 raw bodies, its contract and schedule.json) is bundled byte for byte under
``predecessor/<V1 identity>/`` and verified at every read by the accepted BAT-726 reader with its own pinned profile.
Nothing is requested, refetched or retried; the original URL, host, status, redirect, error, time and body identities
stay exactly as captured. The V1 policy, its sidecar and every default are unchanged; V1 sidecars keep being served by
:mod:`aggie_analytics.retrospective_baseline.schedule` and a successor is selected only when its bundled contract names
this profile (:func:`selects`).

The successor policy was authored after a disclosed inspection of the retained pages and frozen in the committed
contract (:data:`CONTRACT_SHA256`) at ``policy_frozen_utc`` before any successor decision was derived. It adds exactly:

* documented institution identity (:data:`OWNER_RULES`): an own-team name statement that the V1 rule does not bind (an
  athletics brand or a truncated school name) verifies the owner only through an exact contract decision for that NCAA
  institution whose same-document identity members (the Sidearm site name and mascot, the page's og:site_name) are
  present with their decided values, each bound to the institution by a declared basis; a page whose declared records
  state no owner name (logo-only WMT views) is owned through an exact page-identity decision. Identity members never
  supply an opponent, date, role, venue or time;
* one opponent transformation (:data:`NAME_RULES`): after the V1 leading poll rank, a final separately delimited known
  event annotation (only ``(Homecoming)``) is removed in the opponent field only when the remaining exact name binds the
  event's own provider opponent; unknown parentheticals (``Miami (OH)``) are never removed;
* four declared layouts (:data:`STRUCTURES`): the classic SIDEARM schedule data object, and the WMT default-event,
  team-default and event-block views, each with its exact season heading rule (:data:`SEASON_HEADINGS`) and own members.

Every qualified field is entailed by its own record member; a time is an instant only from an explicit offset or a
stated zone designator on the record's own time member; a WMT result label is a time statement only when it reads as a
time or TBA (a past result is never retained). Embedded JSON-LD is never a field source; its role orientation is
censused and a disagreement with a bound record's designation on the event date leaves the designation CONFLICTING.

Timing: the original LOCAL_CAPTURE_OBSERVATION bound (re-derived by the V1 reader) and the successor's own
policy_frozen_utc are kept separately; the effective availability is the later of the two (:data:`AVAILABILITY_RULE`),
so nothing claims the successor interpretation existed at the original capture or the shadow anchor. Every served row
carries the V1 labels plus SUCCESSOR_POLICY_NOT_ORIGINAL_INTERPRETATION. Imported only when ``--schedule-evidence`` is
named.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics.retrospective_baseline import preview as pv
from aggie_analytics.retrospective_baseline import schedule as v1

ScheduleError = v1.ScheduleError
SCHEMA = "BAS-OFFICIAL-SHADOW-SCHEDULE-EXPANSION-1"
IDENTITY_SCHEMA = "BAS-OFFICIAL-SHADOW-SCHEDULE-EXPANSION-IDENTITY-1"
POPULATION = "official_shadow_schedule_expansion_20261017"
CONTRACT_ID = "BAT-727-OFFICIAL-SHADOW-SCHEDULE-EXPANSION-20261017-V2"
#: SHA-256 of the committed contract ``configs/official_shadow_schedule_expansion_20261017_contract.json`` (the
#: authority anchor; a test requires it to equal the committed file).
CONTRACT_SHA256 = "bee7c37be078f0a3b65e9a0410d2caab24856e507b07a5a8d6bfa9606d8018aa"
SCHEDULE_FILE = "schedule.json"
CONTRACT_MEMBER = "inputs/contract.json"
PREDECESSOR_ROOT = "predecessor"
SEASON = v1.SEASON
GRAINS = v1.GRAINS
GRAIN_KEY = v1.GRAIN_KEY
OUT_OF_SCOPE_STATE = v1.OUT_OF_SCOPE_STATE
IN_SCOPE_STATE = "PROSPECTIVE_2026_OFFICIAL_SCHEDULE_EXPANSION_SIDECAR"
AVAILABLE_STATE = "AVAILABLE_AT_OR_AFTER_OBSERVATION_BOUND_AND_POLICY_FROZEN_TIME"
DESIGNATION = "UNTRUSTED_SHADOW"
PINNED = v1.PINNED

#: Labels carried by schedule.json and every served response (equal to the committed contract's ``labels``).
LABELS = {**v1.LABELS,
          "policy_authority": "SUCCESSOR_POLICY_NOT_ORIGINAL_INTERPRETATION",
          "policy_timing": "POLICY_FROZEN_AFTER_ORIGINAL_CAPTURE_NOT_RETROACTIVE",
          "acquisition_authority": "RETAINED_CYCLE54_CAPTURE_ZERO_NEW_REQUESTS",
          "predecessor": "ORIGINAL_V1_EVIDENCE_PRESERVED_AND_REVERIFIED_UNCHANGED"}
#: Labels carried by every event record, source record and served row (equal to the contract's ``record_labels``).
RECORD_LABELS = {**v1.RECORD_LABELS, "policy_authority": LABELS["policy_authority"]}
NUMERIC_CONTRACT = {**v1.NUMERIC_CONTRACT,
                    "policy_time": "policy_frozen_utc is a string YYYY-MM-DDTHH:MM:SS.ffffffZ frozen in the contract; "
                                   "rebuilds reuse it and never read the current clock"}

#: The V1 structures unchanged plus the four layouts the successor declares (TP55 section 2; actual retained structures).
STRUCTURES = {
    **v1.STRUCTURES,
    "SIDEARM_CLASSIC_SCHEDULE_DATA": {
        "element": "the JSON object literal assigned to the member schedule (``schedule : {``) inside an inline <script> "
                   "that registers the Vue component 'vue-schedules' (the classic SIDEARM schedule template); parsed "
                   "strictly from its opening brace to its matching close",
        "season_binding": "the object's own season.title equals '2026' and its own sport.shortname equals 'football'",
        "owner_name": "the object's own school_name",
        "records": "the object's own games list",
        "members": {"event_date": "date (local date part)", "local_time": "date (time part)", "time_text": "time",
                    "designation": "location_indicator H/A/N", "opponent": "opponent.title",
                    "facility": "facility.title", "location": "location"},
    },
    "WMT_DEFAULT_EVENT_VIEW": {
        "element": "every <div> with class token schedule-event-item and every <tr> with class token "
                   "schedule-table-event that contains an element with class token schedule-default-event",
        "season_binding": "the page's <h1> with class token schedule-hero__title or schedule-hero-block__title reads "
                          "a declared season heading (SEASON_HEADINGS)",
        "owner_name": "none: the record's owner side is its schedule-default-event__team--current element, which "
                      "states no name (the owner is verified only by a page-identity decision)",
        "records": "each such element (both views)",
        "members": {"event_date": "the texts of its <time> schedule-event-date__weekday ('Ddd') and "
                                  "schedule-event-date__month-day ('Mon D'); year by the season-year rule; the weekday "
                                  "must match",
                    "opponent": "its schedule-default-event__name text without its schedule-default-event__divider-"
                                "mobile and schedule-default-event__ranking descendants",
                    "designation": "AWAY only when its schedule-default-event__divider reads 'at'; 'vs.' does not "
                                   "distinguish HOME from NEUTRAL and states no designation",
                    "location": "its schedule-event-location text before a final '( ... )'",
                    "facility": "the text inside that final '( ... )'",
                    "time_text": "its schedule-event-item-result__label text only when it reads as a time or TBA"},
    },
    "WMT_TEAM_DEFAULT_VIEW": {
        "element": "every <div> with class token schedule-event-item and every <tr> with class token "
                   "schedule-table-item that contains a schedule-event-team-default element and no "
                   "schedule-event-default__name--current element",
        "season_binding": "the page's <h1> with class token schedule-hero__title or schedule-hero-block__title reads "
                          "a declared season heading (SEASON_HEADINGS)",
        "owner_name": "none: logo-only team components (the owner is verified only by a page-identity decision)",
        "records": "each such element (both views)",
        "members": {"event_date": "the text of the <time> inside its schedule-event-date__time ('Ddd, Mon D'); year by "
                                  "the season-year rule; the weekday must match",
                    "designation": "its schedule-event-date__venue-type text home/away/neutral",
                    "opponent": "its schedule-event-default__name text",
                    "location": "its schedule-event-location text before ' / '",
                    "facility": "that text after the first ' / '",
                    "time_text": "its schedule-event-item-result__label text only when it reads as a time or TBA"},
    },
    "WMT_EVENT_BLOCK_VIEW": {
        "element": "every <div> with class token schedule-event-block and every <tr> with class token "
                   "schedule-item-table",
        "season_binding": "the page's <h1> with class token schedule-hero__title or schedule-hero-block__title reads "
                          "a declared season heading (SEASON_HEADINGS)",
        "owner_name": "none: the record names only the opponent (the owner is verified only by a page-identity "
                      "decision)",
        "records": "each such element (both views)",
        "members": {"event_date": "the datetime attribute of its <time> schedule-event-date__day (local date part "
                                  "only; its clock is a placeholder for TBA events and states no time)",
                    "designation": "class token schedule-event-date--venue-home/away/neutral on its "
                                   "schedule-event-date element",
                    "opponent": "its schedule-default-team__opponent-name text",
                    "facility": "its schedule-default-team__venue text",
                    "location": "its schedule-event-location text before ' / '",
                    "time_text": "its schedule-event-item-result__label text only when it reads as a time or TBA"},
    },
}
NEW_STRUCTURES = ("SIDEARM_CLASSIC_SCHEDULE_DATA", "WMT_DEFAULT_EVENT_VIEW", "WMT_TEAM_DEFAULT_VIEW",
                  "WMT_EVENT_BLOCK_VIEW")
#: The exact retained season headings the WMT views accept (TP55 section 2: an explicit recorded season rule).
SEASON_HEADINGS = {
    "2026 Football Schedule": {"season_label": "2026", "rule": "the heading names football season 2026"},
    "2026-27 Football Schedule": {"season_label": "2026-27",
                                  "rule": "a 2026-27 label denotes football season 2026 (its first calendar year) and "
                                          "binds only records with a complete own date (month, day and matching "
                                          "weekday) resolved by the season-year rule"},
    "Football 2026 Schedule Schedule": {"season_label": "2026",
                                        "rule": "the retained heading text exactly as published (a repeated word); "
                                                "names football season 2026"},
}
SEASON_YEAR_RULE = ("a month-day text without a year takes the season year for March-December and the next year for "
                    "January-February; the stated weekday must equal that date's weekday, otherwise no date")
TEXT_RULE = v1.TEXT_RULE
KNOWN_EVENT_ANNOTATIONS = ("Homecoming",)
NAME_RULES = {
    **v1.NAME_RULES,
    "opponent_annotation": "in the opponent field only, after the leading poll rank: a final separately delimited "
                           "' (<annotation>)' whose text is exactly a known event annotation (KNOWN_EVENT_ANNOTATIONS) is "
                           "removed, and only when the remaining exact name binds the event's own provider opponent; "
                           "unknown parentheticals are never removed; the original string and every transformation are "
                           "kept with the witness",
}
IDENTITY_MEMBERS = {
    "siteSettings.siteName": "the Sidearm Nuxt payload's pinia.site-config.siteSettings.siteName",
    "siteSettings.mascotPlural": "the Sidearm Nuxt payload's pinia.site-config.siteSettings.mascotPlural",
    "og:site_name": "the content of every <meta property=\"og:site_name\"> element of the page",
}
DECISION_KINDS = {
    "OWNER_STATEMENT": "the document's own-team name statements that the V1 rule does not bind are each exactly one of "
                       "the decision's owner statements, and every identity member of the decision is present in the "
                       "same document with exactly its decided value (every occurrence equal)",
    "PAGE_IDENTITY": "the document's declared records state no owner name, and every identity member of the decision is "
                     "present in the same document with exactly its decided value (every occurrence equal)",
}
DECISION_BASES = {
    "OFFICIAL_NAME_PLUS_ATHLETICS": "value == NCAA official name + ' Athletics'",
    "OFFICIAL_LEADING_CLAUSE": "value == the NCAA official name's text before its first ','",
    "OFFICIAL_NAME_WITHOUT_FINAL_WORD": "value == the NCAA official name without its final word",
    "OFFICIAL_LEADING_CLAUSE_WITHOUT_FIRST_WORD": "value == that leading clause without its first word",
    "PROVIDER_DISPLAY_NAME": "value == the frozen provider owner displayName",
    "PROVIDER_LOCATION_PLUS_ATHLETICS": "value == the frozen provider owner location + ' Athletics'",
    "PROVIDER_LOCATION_OFFICIAL_WEBSITE_TITLE": "value ends with 'The Official Website of ' + the frozen provider owner "
                                                "location + ' Athletics'",
    "PROVIDER_TEAM_NAME": "value == the frozen provider owner name (team nickname)",
    "DIRECTORY_ATHLETICS_HOST_BRAND": "value without spaces, casefolded, is contained in the NCAA directory athletics "
                                      "host of the institution, and its first word equals the frozen provider owner "
                                      "location",
}
OWNER_RULES = {
    "provider_or_official_name": "the V1 rule: every own-team name statement binds the frozen provider home names or "
                                 "the NCAA official name (OWNER_VERIFIED)",
    "documented_identity": "an OWNER_STATEMENT decision for the event's own NCAA institution holds in the same document "
                           "(OWNER_VERIFIED_DOCUMENTED_IDENTITY)",
    "page_identity": "a PAGE_IDENTITY decision for the event's own NCAA institution holds in a document whose declared "
                     "records state no owner name (OWNER_VERIFIED_PAGE_IDENTITY)",
    "scope": "a decision applies only to its own NCAA organization id; every basis is checked against the frozen "
             "official name, provider names and directory host at derivation; identity members establish who owns the "
             "schedule and never supply an opponent, date, role, venue or time",
}
OWNER_STATES = ("OWNER_VERIFIED", "OWNER_VERIFIED_DOCUMENTED_IDENTITY", "OWNER_VERIFIED_PAGE_IDENTITY",
                "OWNER_NAME_DOES_NOT_BIND", "OWNER_NAME_NOT_STATED")
VERIFIED_OWNER_STATES = OWNER_STATES[:3]
FIELDS = v1.FIELDS
FIELD_STATES = v1.FIELD_STATES
TIME_STATES = v1.TIME_STATES
COMPARISONS = v1.COMPARISONS
DISPOSITIONS = v1.DISPOSITIONS
FIELD_RULES = {
    **v1.FIELD_RULES,
    "opponent_binding": "a record's own opponent binds when its normalized name (NAME_RULES) equals the frozen provider "
                        "away displayName, shortDisplayName or location",
    "designation_views": "WMT default-event views state AWAY only by an 'at' divider ('vs.' states nothing); "
                         "team-default views by their venue-type text; event-block views by their venue class token",
    "json_ld": "embedded JSON-LD is never a field source; its SportsEvent role orientation is censused per document, "
               "and a JSON-LD event on the event date (its startDate's own date part when naive, otherwise the "
               "calendar dates of its explicit instant at offsets -04:00 to -10:00, intersecting the provider date "
               "set) naming the bound opponent on the side opposite the bound designation leaves the designation "
               "CONFLICTING with both values",
}
TIME_RULES = {
    **v1.TIME_RULES,
    "result_label": "a WMT result label is a time statement only when it reads as a clock time (optionally with a zone "
                    "designator) or TBA; any other text (a past result) is not a statement and is never retained",
    "event_block_clock": "the clock part of an event-block view's day datetime is not a time statement (a placeholder "
                         "for TBA events)",
}
AVAILABILITY_RULE = ("the effective availability is the later of the retained capture's observation bound (the maximum "
                     "response end UTC of every attempt, re-derived by the accepted BAT-726 reader) and this contract's "
                     "policy_frozen_utc; before the observation bound the sidecar is refused "
                     "SCHEDULE_UNAVAILABLE_BEFORE_OBSERVATION_BOUND, before the policy-frozen time "
                     "SCHEDULE_UNAVAILABLE_BEFORE_POLICY_FROZEN; at or after both the same immutable evidence is served")
EVENT_MOVEMENTS = ("PRESERVED_RECORD_BOUND", "RECORD_BOUND_FIELDS_CHANGED", "NEWLY_RECORD_BOUND",
                   "STILL_UNSUPPORTED_SAME_DISPOSITION", "STILL_UNSUPPORTED_DISPOSITION_REFINED", "SUPPORT_LOST")
FIELD_MOVEMENTS = ("UNCHANGED", "NEWLY_STATED", "STATE_CHANGED")
EVENT_FIELDS = ("record_type", "event_key", "season", "owner", "opponent", "provider_claims", "requests", "attempts",
                "documents", "disposition", "disposition_reasons", "fields", "occurrences", "predecessor", "movement",
                "labels")
SOURCE_FIELDS = ("record_type", "event_key", "logical", "route", "stage", "url", "outcome", "hops", "attempts",
                 "decision", "link_source", "document", "predecessor_document", "labels")
TOP_LEVEL = ("schema", "population", "designation", "contract", "predecessor", "shadow", "acquisition", "policy",
             "availability", "labels", "events", "sources", "summary", "counts")
FAMILIES = ("SCHEMA", "DESIGNATION", "CONTRACT", "PREDECESSOR", "SHADOW", "ACQUISITION", "POLICY", "AVAILABILITY",
            "LABELS", "EVENT_MEMBERSHIP", "EVENT_RECORD", "SOURCE_MEMBERSHIP", "SOURCE_RECORD", "SUMMARY", "COUNTS",
            "CANONICAL_FORM")
PROFILE_FIELDS = ("schedule_identity", "schedule_sha256", "predecessor_identity", "policy_frozen_utc",
                  "effective_availability_utc")
PREDECESSOR_PINS = ("population", "identity", "schedule_sha256", "contract_id", "contract_sha256", "journal_sha256",
                    "attempts", "availability_bound_utc")
SHADOW_PINS = ("population", "identity", "snapshot_sha256", "payload_sha256", "contract_sha256")

#: The actual successor sidecar pinned by the packaged final gate (``artifacts/data_lake/official_shadow_schedule_
#: expansion_20261017_gate.json``; a test requires equality). None until the sidecar exists (the contract is first).
EXPANSION_PROFILE: dict[str, Any] | None = None

IDENTITY_RE = v1.IDENTITY_RE
UTC = v1.UTC


# --------------------------------------------------------------------------------------------- selection

def selects(path: Path | str) -> bool:
    """Whether ``path`` names a sidecar whose bundled contract names this successor profile. Read-only and lexical
    first: a location the V1 rule refuses (network/device namespace) or a missing/unreadable/malformed contract member
    leaves the V1 reader to answer with its own unchanged refusal."""
    try:
        location = v1.literal_location(path)
    except ScheduleError:
        return False
    member = os.path.join(pv.io_path(os.path.dirname(location)), *CONTRACT_MEMBER.split("/"))
    try:
        if not os.path.isfile(member):
            return False
        with open(member, "rb") as handle:
            document = json.loads(handle.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    return isinstance(document, dict) and document.get("contract_id") == CONTRACT_ID


# --------------------------------------------------------------------------------------------- names and dates

_ANNOTATION = re.compile(r"^(.*\S)\s+\(([^()]*)\)\Z")


def opponent_name(value: Any) -> dict[str, Any]:
    """The opponent field's normalized name: V1 rank removal, then a known final event annotation (never another
    parenthetical). Returns the key with and without the annotation step so binding can require the exact remainder."""
    text = v1.clean_text(value)
    if not text:
        return {"text": text, "key": None, "annotation_key": None, "rank_removed": False, "annotation": None}
    ranked = v1._RANK.sub("", text).strip()
    match = _ANNOTATION.match(ranked)
    annotation = match.group(2) if match and match.group(2) in KNOWN_EVENT_ANNOTATIONS else None
    return {"text": text, "key": ranked.casefold() or None, "rank_removed": ranked != text,
            "annotation": annotation, "annotation_key": match.group(1).casefold() if annotation else None}


def binds_opponent(value: Any, away: set[str]) -> tuple[bool, list[str], str | None]:
    """(binds, transformations, normalized name) for one opponent statement against the provider away names."""
    parsed = opponent_name(value)
    steps = ["LEADING_POLL_RANK_REMOVED"] if parsed["rank_removed"] else []
    if parsed["key"] in away:
        return True, steps, parsed["key"]
    if parsed["annotation_key"] is not None and parsed["annotation_key"] in away:
        return True, steps + [f"EVENT_ANNOTATION_REMOVED:{parsed['annotation']}"], parsed["annotation_key"]
    return False, [], None


_MONTH_DAY = re.compile(r"^([A-Za-z]{3})[a-z]*\.?\s+([0-9]{1,2})\Z")
_WEEKDAY = re.compile(r"^([A-Za-z]{3})[a-z]*\.?\Z")
_WEEKDAY_MONTH_DAY = re.compile(r"^([A-Za-z]{3})[a-z]*\.?,\s*([A-Za-z]{3})[a-z]*\.?\s+([0-9]{1,2})\Z")


def season_date(month: str, day: str, weekday: str) -> tuple[str | None, str | None]:
    """The complete own date of a month-day-weekday text under the season-year rule (None plus a reason otherwise)."""
    month, weekday = month.lower(), weekday.lower()
    if month not in v1._MONTHS or weekday not in v1._WEEKDAYS:
        return None, "DATE_TEXT_UNRECOGNIZED"
    year = SEASON if v1._MONTHS[month] >= 3 else SEASON + 1
    try:
        date = _dt.date(year, v1._MONTHS[month], int(day))
    except ValueError:
        return None, "DATE_TEXT_INVALID"
    if v1._WEEKDAYS[date.weekday()] != weekday:
        return None, "DATE_WEEKDAY_MISMATCH"
    return date.isoformat(), None


def split_date(weekday_text: Any, month_day_text: Any) -> tuple[str | None, str | None]:
    wd = _WEEKDAY.match(v1.clean_text(weekday_text) or "")
    md = _MONTH_DAY.match(v1.clean_text(month_day_text) or "")
    if not wd or not md:
        return None, "DATE_TEXT_UNRECOGNIZED"
    return season_date(md.group(1), md.group(2), wd.group(1))


def joined_date(text: Any) -> tuple[str | None, str | None]:
    match = _WEEKDAY_MONTH_DAY.match(v1.clean_text(text) or "")
    if not match:
        return None, "DATE_TEXT_UNRECOGNIZED"
    return season_date(match.group(2), match.group(3), match.group(1))


# --------------------------------------------------------------------------------------------- structures

def _cls(node: Any) -> set[str]:
    return v1._classes(node) if isinstance(node, dict) else set()


def _all(node: dict[str, Any], token: str) -> list[dict[str, Any]]:
    return [n for n in v1._walk(node) if n is not node and token in _cls(n)]


def _texts(nodes: Iterable[dict[str, Any]]) -> str | None:
    """One statement from every node carrying the member: their common text, '|'-joined when they differ."""
    values = []
    for node in nodes:
        text = v1._text(node)
        if text not in values:
            values.append(text)
    if not values:
        return None
    return values[0] if len(values) == 1 else "|".join(values)


def _text_without(node: dict[str, Any], skip: set[str]) -> str:
    parts: list[str] = []
    stack: list[Any] = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            parts.append(cur)
        elif isinstance(cur, dict) and cur.get("tag") not in ("script", "style") and not (_cls(cur) & skip):
            stack.extend(reversed(cur.get("children") or []))
    return v1._WS.sub(" ", "".join(parts)).strip()


def season_heading(root: dict[str, Any]) -> dict[str, Any]:
    heading = v1._first(root, lambda n: n.get("tag") == "h1" and bool(
        _cls(n) & {"schedule-hero__title", "schedule-hero-block__title"}))
    text = v1._text(heading) if heading else None
    member = None if heading is None else ("h1.schedule-hero__title" if "schedule-hero__title" in _cls(heading)
                                           else "h1.schedule-hero-block__title")
    rule = SEASON_HEADINGS.get(text or "")
    return {"bound": rule is not None, "witness": {"member": member, "raw": text,
                                                   "season_label": rule["season_label"] if rule else None}}


def _wmt_instance(structure: str, heading: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    return {"structure": structure, "instance": 0, "matched": True, "reason": None, "season_bound": heading["bound"],
            "season_witness": heading["witness"], "owner_names": [], "records": records}


def extract_wmt_default_event(root: dict[str, Any], heading: dict[str, Any]) -> list[dict[str, Any]]:
    items = [n for n in v1._walk(root) if ((n.get("tag") == "div" and "schedule-event-item" in _cls(n)) or
                                          (n.get("tag") == "tr" and "schedule-table-event" in _cls(n))) and
             _all(n, "schedule-default-event")]
    if not items:
        return []
    records = []
    for index, item in enumerate(items):
        names = _all(item, "schedule-default-event__name")
        ranks = [r for nm in names for r in _all(nm, "schedule-default-event__ranking")]
        opponent = None
        if names:
            texts = []
            for nm in names:
                text = _text_without(nm, {"schedule-default-event__divider-mobile", "schedule-default-event__ranking"})
                if text not in texts:
                    texts.append(text)
            opponent = texts[0] if len(texts) == 1 else "|".join(texts)
        records.append({"index": index, "view": item.get("tag"), "members": {
            "weekday": _texts(n for n in _all(item, "schedule-event-date__weekday") if n.get("tag") == "time"),
            "month_day": _texts(n for n in _all(item, "schedule-event-date__month-day") if n.get("tag") == "time"),
            "divider": _texts(_all(item, "schedule-default-event__divider")),
            "opponent": opponent, "opponent_rank": _texts(ranks),
            "owner_side_present": bool(_all(item, "schedule-default-event__team--current")),
            "location": _texts(_all(item, "schedule-event-location")),
            "result_label": _texts(_all(item, "schedule-event-item-result__label"))}})
    return [_wmt_instance("WMT_DEFAULT_EVENT_VIEW", heading, records)]


def extract_wmt_team_default(root: dict[str, Any], heading: dict[str, Any]) -> list[dict[str, Any]]:
    items = [n for n in v1._walk(root) if ((n.get("tag") == "div" and "schedule-event-item" in _cls(n)) or
                                          (n.get("tag") == "tr" and "schedule-table-item" in _cls(n))) and
             _all(n, "schedule-event-team-default") and not _all(n, "schedule-event-default__name--current")]
    if not items:
        return []
    records = []
    for index, item in enumerate(items):
        times = [t for box in _all(item, "schedule-event-date__time") for t in v1._walk(box)
                 if t is not box and t.get("tag") == "time"]
        records.append({"index": index, "view": item.get("tag"), "members": {
            "date_text": _texts(times),
            "venue_type": _texts(_all(item, "schedule-event-date__venue-type")),
            "divider": _texts(_all(item, "schedule-event-default__divider")),
            "opponent": _texts(_all(item, "schedule-event-default__name")),
            "location": _texts(_all(item, "schedule-event-location")),
            "result_label": _texts(_all(item, "schedule-event-item-result__label"))}})
    return [_wmt_instance("WMT_TEAM_DEFAULT_VIEW", heading, records)]


_VENUE_CLASSES = {"schedule-event-date--venue-home": "HOME", "schedule-event-date--venue-away": "AWAY",
                  "schedule-event-date--venue-neutral": "NEUTRAL"}


def extract_wmt_event_block(root: dict[str, Any], heading: dict[str, Any]) -> list[dict[str, Any]]:
    items = [n for n in v1._walk(root) if (n.get("tag") == "div" and "schedule-event-block" in _cls(n)) or
             (n.get("tag") == "tr" and "schedule-item-table" in _cls(n))]
    if not items:
        return []
    records = []
    for index, item in enumerate(items):
        days = [n for n in _all(item, "schedule-event-date__day") if n.get("tag") == "time"]
        stamps = []
        for day in days:
            stamp = day.get("attrs", {}).get("datetime")
            if stamp not in stamps:
                stamps.append(stamp)
        tokens = sorted({t for d in _all(item, "schedule-event-date") for t in _cls(d) if t in _VENUE_CLASSES})
        records.append({"index": index, "view": item.get("tag"), "members": {
            "day.datetime": stamps[0] if len(stamps) == 1 else (None if not stamps else "|".join(map(str, stamps))),
            "venue_class": tokens[0] if len(tokens) == 1 else (None if not tokens else "|".join(tokens)),
            "divider": _texts(_all(item, "schedule-default-team__divider")),
            "opponent": _texts(_all(item, "schedule-default-team__opponent-name")),
            "venue": _texts(_all(item, "schedule-default-team__venue")),
            "location": _texts(_all(item, "schedule-event-location")),
            "result_label": _texts(_all(item, "schedule-event-item-result__label"))}})
    return [_wmt_instance("WMT_EVENT_BLOCK_VIEW", heading, records)]


_SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.S | re.I)
_CLASSIC_REGISTRATION = re.compile(r"Vue\.component\(\s*'vue-schedules'")
_CLASSIC_MEMBER = re.compile(r"\bschedule\s*:\s*\{")


def extract_classic(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    decoder = json.JSONDecoder(parse_constant=lambda c: None)
    for script in _SCRIPT_RE.finditer(text):
        body = script.group(1)
        if not _CLASSIC_REGISTRATION.search(body):
            continue
        for member in _CLASSIC_MEMBER.finditer(body):
            base = {"structure": "SIDEARM_CLASSIC_SCHEDULE_DATA", "instance": len(out), "matched": True,
                    "reason": None, "season_bound": False, "season_witness": None, "owner_names": [], "records": []}
            try:
                obj, _end = decoder.raw_decode(body, member.end() - 1)
            except ValueError:
                out.append({**base, "matched": False, "reason": "CLASSIC_OBJECT_NOT_JSON"})
                continue
            if not isinstance(obj, dict):
                out.append({**base, "matched": False, "reason": "CLASSIC_OBJECT_NOT_AN_OBJECT"})
                continue
            season = obj.get("season") if isinstance(obj.get("season"), dict) else {}
            sport = obj.get("sport") if isinstance(obj.get("sport"), dict) else {}
            title, shortname = v1._scalar(season.get("title")), v1._scalar(sport.get("shortname"))
            school = v1._scalar(obj.get("school_name"))
            records = []
            for index, game in enumerate(obj.get("games") if isinstance(obj.get("games"), list) else []):
                if not isinstance(game, dict):
                    continue
                opponent = game.get("opponent") if isinstance(game.get("opponent"), dict) else {}
                facility = game.get("facility") if isinstance(game.get("facility"), dict) else {}
                records.append({"index": index, "members": {
                    "date": v1._scalar(game.get("date")), "time": v1._scalar(game.get("time")),
                    "tbd": v1._scalar(game.get("tbd")),
                    "location_indicator": v1._scalar(game.get("location_indicator")),
                    "opponent.title": v1._scalar(opponent.get("title")),
                    "facility.title": v1._scalar(facility.get("title")),
                    "location": v1._scalar(game.get("location"))}})
            out.append({**base, "season_bound": title == str(SEASON) and shortname == "football",
                        "season_witness": {"member": "season.title", "raw": title, "sport_shortname": shortname},
                        "owner_names": [school] if isinstance(school, str) else [], "records": records})
    return out


def page_identity(body: bytes, root: dict[str, Any] | None) -> dict[str, list[str]]:
    """Every identity member statement of one document (IDENTITY_MEMBERS), each list in document order."""
    out: dict[str, list[str]] = {k: [] for k in IDENTITY_MEMBERS}
    if root is not None:
        for node in v1._walk(root):
            attrs = node.get("attrs") or {}
            if node.get("tag") == "meta" and attrs.get("property") == "og:site_name":
                out["og:site_name"].append(v1.clean_text(attrs.get("content")) or "")
    match = v1._NUXT_RE.search(body)
    if match:
        try:
            data = json.loads(match.group(1).decode("utf-8"), parse_constant=lambda c: None)
        except (UnicodeDecodeError, ValueError):
            data = None
        if isinstance(data, list) and data:
            settings = v1._member(data, v1._devalue(data, 0), "pinia", "site-config", "siteSettings")
            if isinstance(settings, dict):
                for key, name in (("siteName", "siteSettings.siteName"), ("mascotPlural", "siteSettings.mascotPlural")):
                    value = v1._scalar(v1._member(data, settings, key))
                    if isinstance(value, str):
                        out[name].append(v1.clean_text(value) or "")
    return out


_LD_RE = re.compile(r"<script\b[^>]*type=\"application/ld\+json\"[^>]*>(.*?)</script>", re.S | re.I)


def ld_dates(start: Any) -> list[str]:
    """A JSON-LD startDate's calendar dates: its own date part when naive, otherwise the dates of its explicit instant
    at every US offset -04:00 through -10:00."""
    parts = v1.iso_parts(start)
    if parts is None:
        return []
    if parts["offset"] is None:
        return [parts["local_date"]]
    moment = v1.parse_utc_text(parts["utc"])
    return sorted({(moment + _dt.timedelta(hours=h)).date().isoformat() for h in range(-10, -3)})


def json_ld_events(text: str) -> list[dict[str, Any]]:
    """Every embedded JSON-LD SportsEvent (census only; never a field source)."""
    events: list[dict[str, Any]] = []
    for block in _LD_RE.finditer(text):
        try:
            value = json.loads(block.group(1), parse_constant=lambda c: None)
        except ValueError:
            continue
        stack = [value]
        while stack:
            cur = stack.pop(0)
            if isinstance(cur, list):
                stack[:0] = cur
            elif isinstance(cur, dict):
                if cur.get("@type") == "SportsEvent":
                    home = cur.get("homeTeam") if isinstance(cur.get("homeTeam"), dict) else {}
                    away = cur.get("awayTeam") if isinstance(cur.get("awayTeam"), dict) else {}
                    start = v1._scalar(cur.get("startDate"))
                    events.append({"start": start, "dates": ld_dates(start),
                                   "home": v1.clean_text(v1._scalar(home.get("name"))),
                                   "away": v1.clean_text(v1._scalar(away.get("name")))})
                elif isinstance(cur.get("@graph"), list):
                    stack[:0] = cur["@graph"]
    return events


def extract_document(body: bytes) -> dict[str, Any]:
    """Every V1 structure instance (the accepted V1 extraction, unchanged) plus every successor structure instance,
    the identity members and the JSON-LD SportsEvent census of one retained document."""
    structures = v1.extract_sidearm_nuxt(body)
    text = v1._decode(body)
    root = None
    ld: list[dict[str, Any]] = []
    if text is not None:
        root = v1.parse_tree(text)
        structures += v1.extract_sidearm_text_table(root)
        structures += v1.extract_wmt_list(root)
        structures += extract_classic(text)
        heading = season_heading(root)
        structures += extract_wmt_default_event(root, heading)
        structures += extract_wmt_team_default(root, heading)
        structures += extract_wmt_event_block(root, heading)
        ld = json_ld_events(text)
    return {"utf8": text is not None, "structures": structures, "identity": page_identity(body, root),
            "json_ld": ld}


# --------------------------------------------------------------------------------------------- witnesses

_TEXT_DESIGNATIONS = {"home": "HOME", "away": "AWAY", "neutral": "NEUTRAL"}


def _result_label_statement(label: Any, local_date: str | None) -> list[dict[str, Any]]:
    parsed = v1.parse_time_text(label)
    if parsed["kind"] not in ("TBA", "NAIVE", "ZONE"):
        return []  # not a time statement: a past result or other text is never retained
    return [{"member": "result_label", "raw": label, **v1.time_statement(local_date, parsed)}]


def record_values(structure: str, members: dict[str, Any]) -> dict[str, Any]:
    """The field statements of one record from its own members only (each with its member name and raw value)."""
    if structure in v1.STRUCTURES:
        return v1.record_values(structure, members)
    if structure == "SIDEARM_CLASSIC_SCHEDULE_DATA":
        return v1.record_values("SIDEARM_NUXT_SCHEDULE", members)
    out: dict[str, Any] = {}
    if structure == "WMT_DEFAULT_EVENT_VIEW":
        date, reason = split_date(members.get("weekday"), members.get("month_day"))
        out["event_date"], out["event_date_member"], out["event_date_reason"] = date, "month_day+weekday", reason
        out["opponent"] = v1.clean_text(members.get("opponent"))
        divider = (v1.clean_text(members.get("divider")) or "").casefold()
        out["designation"] = "AWAY" if divider == "at" else None
        out["location"], out["facility"] = v1._split_location(members.get("location"), "(")
        out["time"] = _result_label_statement(members.get("result_label"), date)
    elif structure == "WMT_TEAM_DEFAULT_VIEW":
        date, reason = joined_date(members.get("date_text"))
        out["event_date"], out["event_date_member"], out["event_date_reason"] = date, "date_text", reason
        out["opponent"] = v1.clean_text(members.get("opponent"))
        out["designation"] = _TEXT_DESIGNATIONS.get((v1.clean_text(members.get("venue_type")) or "").casefold())
        out["location"], out["facility"] = v1._split_location(members.get("location"), " / ")
        out["time"] = _result_label_statement(members.get("result_label"), date)
    elif structure == "WMT_EVENT_BLOCK_VIEW":
        day = v1.iso_parts(members.get("day.datetime"))
        date = (day or {}).get("local_date")
        out["event_date"], out["event_date_member"] = date, "day.datetime"
        out["event_date_reason"] = None if date else "DATE_MEMBER_UNPARSED"
        out["opponent"] = v1.clean_text(members.get("opponent"))
        out["designation"] = _VENUE_CLASSES.get(members.get("venue_class") or "")
        out["facility"] = v1.clean_text(members.get("venue")) or None
        out["location"] = v1._split_location(members.get("location"), " / ")[0]
        out["time"] = _result_label_statement(members.get("result_label"), date)
    return out


MEMBER_NAMES = {
    "SIDEARM_NUXT_SCHEDULE": {"opponent": "opponent.title", "designation": "location_indicator",
                              "facility": "facility.title", "location": "location"},
    "SIDEARM_TEXT_TABLE": {"opponent": "Opponent", "designation": "At", "facility": "Location",
                           "location": "Location"},
    "WMT_SCHEDULE_LIST": {"opponent": "opponent_name", "designation": "venue_class", "facility": "location",
                          "location": "location"},
    "SIDEARM_CLASSIC_SCHEDULE_DATA": {"opponent": "opponent.title", "designation": "location_indicator",
                                      "facility": "facility.title", "location": "location"},
    "WMT_DEFAULT_EVENT_VIEW": {"opponent": "opponent", "designation": "divider", "facility": "location",
                               "location": "location"},
    "WMT_TEAM_DEFAULT_VIEW": {"opponent": "opponent", "designation": "venue_type", "facility": "location",
                              "location": "location"},
    "WMT_EVENT_BLOCK_VIEW": {"opponent": "opponent", "designation": "venue_class", "facility": "venue",
                             "location": "location"},
}


# --------------------------------------------------------------------------------------------- owner identity

def basis_value(basis: str, owner: dict[str, Any]) -> Any:
    official = owner["official_name"]
    clause = official.split(",")[0].strip()
    names = owner["provider_names"]
    if basis == "OFFICIAL_NAME_PLUS_ATHLETICS":
        return official + " Athletics"
    if basis == "OFFICIAL_LEADING_CLAUSE":
        return clause
    if basis == "OFFICIAL_NAME_WITHOUT_FINAL_WORD":
        return " ".join(official.split()[:-1])
    if basis == "OFFICIAL_LEADING_CLAUSE_WITHOUT_FIRST_WORD":
        return " ".join(clause.split()[1:])
    if basis == "PROVIDER_DISPLAY_NAME":
        return names.get("displayName")
    if basis == "PROVIDER_LOCATION_PLUS_ATHLETICS":
        return f"{names.get('location')} Athletics"
    if basis == "PROVIDER_TEAM_NAME":
        return names.get("name")
    return None


def basis_holds(basis: str, value: Any, owner: dict[str, Any]) -> bool:
    """Whether one decided value is bound to the event's own institution by its declared basis (DECISION_BASES)."""
    if not isinstance(value, str) or not value or basis not in DECISION_BASES:
        return False
    location = owner["provider_names"].get("location") or ""
    if basis == "PROVIDER_LOCATION_OFFICIAL_WEBSITE_TITLE":
        return bool(location) and value.endswith(f"The Official Website of {location} Athletics")
    if basis == "DIRECTORY_ATHLETICS_HOST_BRAND":
        brand = value.replace(" ", "").casefold()
        words = value.split()
        return bool(brand) and brand in owner["directory_host"].casefold() and bool(words) and words[0] == location
    return value == basis_value(basis, owner)


def owner_state(structures: list[dict[str, Any]], identity: dict[str, list[str]], event: dict[str, Any],
                decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """The document's owner verification: the V1 rule first, then an exact decision for the event's own institution."""
    owner = event["owner"]
    base = v1._owner_state(structures, owner)
    out = {"state": base["state"], "statements": base["statements"], "binding": base["binding"],
           "non_binding": base["non_binding"], "distinct_keys": base["distinct_keys"], "decision": None,
           "decision_checks": []}
    if base["state"] == "OWNER_VERIFIED":
        return out
    mine = [d for d in decisions if d["ncaa_org_id"] == owner["ncaa_org_id"]]
    for decision in mine:
        kind = decision["kind"]
        if kind == "OWNER_STATEMENT" and base["state"] != "OWNER_NAME_DOES_NOT_BIND":
            continue
        if kind == "PAGE_IDENTITY" and base["state"] != "OWNER_NAME_NOT_STATED":
            continue
        allowed = {s["value"] for s in decision.get("owner_statements") or []}
        statements_ok = kind == "PAGE_IDENTITY" or all(n in allowed for n in base["non_binding"])
        members = []
        for item in decision["identity_members"]:
            present = identity.get(item["member"]) or []
            members.append({"member": item["member"], "decided": item["value"], "present": present,
                            "holds": bool(present) and all(p == item["value"] for p in present)})
        holds = statements_ok and all(m["holds"] for m in members)
        out["decision_checks"].append({"decision": decision["id"], "kind": kind, "statements_ok": statements_ok,
                                       "members": members, "holds": holds})
        if holds:
            out["state"] = "OWNER_VERIFIED_DOCUMENTED_IDENTITY" if kind == "OWNER_STATEMENT" else \
                "OWNER_VERIFIED_PAGE_IDENTITY"
            out["decision"] = decision["id"]
            return out
    return out


def check_decisions(decisions: list[dict[str, Any]], owners: dict[int, dict[str, Any]]) -> None:
    """Every frozen decision names an expected owner institution and every basis holds for that institution."""
    for decision in decisions:
        owner = owners.get(decision["ncaa_org_id"])
        if owner is None:
            raise ScheduleError("SCHEDULE_EXPANSION_DECISION_INVALID", f"{decision['id']} names no expected owner")
        if owner["official_name"] != decision["official_name"] or owner["directory_host"] != decision["directory_host"]:
            raise ScheduleError("SCHEDULE_EXPANSION_DECISION_INVALID", f"{decision['id']} differs from its institution")
        for item in list(decision.get("owner_statements") or []) + list(decision["identity_members"]):
            if not basis_holds(item["basis"], item["value"], owner):
                raise ScheduleError("SCHEDULE_EXPANSION_DECISION_BASIS_INVALID",
                                    f"{decision['id']} {item.get('member', 'statement')} {item['value']!r} does not "
                                    f"hold by {item['basis']}")


def document_census(doc_sha: str, body: bytes, event: dict[str, Any], decisions: list[dict[str, Any]]
                    ) -> dict[str, Any]:
    """One retained document's declared structures (V1 and successor), season binding, owner verification, identity
    members and JSON-LD census for its event."""
    extracted = extract_document(body)
    structures = extracted["structures"]
    owner = owner_state(structures, extracted["identity"], event, decisions)
    qualified = [s for s in structures if s["matched"] and s["season_bound"]]
    ld = extracted["json_ld"]
    declared = [record_values(s["structure"], rec["members"]) for s in qualified for rec in s["records"]]
    return {"document": doc_sha, "bytes": len(body), "utf8": extracted["utf8"],
            "structures": [{"structure": s["structure"], "instance": s["instance"], "matched": s["matched"],
                            "reason": s["reason"], "season_bound": s["season_bound"],
                            "season_witness": s["season_witness"], "records": len(s["records"]),
                            "owner_names": s["owner_names"]} for s in structures],
            "identity": extracted["identity"], "owner": owner,
            "qualified": bool(qualified) and owner["state"] in VERIFIED_OWNER_STATES,
            "json_ld": {"sports_events": len(ld), "admitted": False,
                        "dates": sorted({d for e in ld for d in e["dates"]}),
                        "orientation_vs_declared_records": json_ld_orientation(ld, declared)},
            "_structures": structures, "_json_ld": ld}


# --------------------------------------------------------------------------------------------- qualification

def json_ld_orientation(ld: list[dict[str, Any]], declared: list[dict[str, Any]]) -> dict[str, int]:
    """JSON-LD role orientation against the document's declared season-bound records of the same date whose own
    opponent text equals a JSON-LD team name exactly (census only: JSON-LD is never a field source)."""
    agree = disagree = 0
    for item in ld:
        for values in declared:
            if values.get("event_date") not in item["dates"] or values.get("designation") not in ("HOME", "AWAY"):
                continue
            opponent = (v1.clean_text(values.get("opponent")) or "").casefold()
            if opponent and (item["away"] or "").casefold() == opponent:
                stated = "HOME"
            elif opponent and (item["home"] or "").casefold() == opponent:
                stated = "AWAY"
            else:
                continue
            agree += stated == values["designation"]
            disagree += stated != values["designation"]
    return {"agree": agree, "disagree": disagree}


def qualify_event(event: dict[str, Any], docs: list[dict[str, Any]]) -> dict[str, Any]:
    """The event's disposition and separate field states from its retained documents under the successor policy."""
    claims = event["provider_claims"]
    dates = set(claims["local_date_set"])
    away = {v1.name_key(event["opponent"]["provider_names"][k]) for k in ("displayName", "shortDisplayName",
                                                                          "location")}
    away.discard(None)
    bound, occurrences, ld_statements = [], [], []
    for doc in docs:
        if not doc["qualified"]:
            continue
        for s in doc["_structures"]:
            if not (s["matched"] and s["season_bound"]):
                continue
            for rec in s["records"]:
                values = record_values(s["structure"], rec["members"])
                base ={"document": doc["document"], "logical": doc["logical"], "structure": s["structure"],
                        "instance": s["instance"], "record_index": rec["index"],
                        "season_witness": s["season_witness"]}
                binds, steps, normalized = binds_opponent(values.get("opponent"), away)
                date = values.get("event_date")
                if date is None:
                    if binds:
                        occurrences.append({**base, "relation": "BOUND_OPPONENT_DATE_UNDETERMINED",
                                            "opponent": values.get("opponent"),
                                            "reason": values.get("event_date_reason") or "DATE_MEMBER_UNPARSED"})
                    continue
                if binds and date in dates:
                    bound.append({**base, "members": rec["members"], "values": values, "transformations": steps,
                                  "normalized": normalized})
                elif binds:
                    occurrences.append({**base, "relation": "BOUND_OPPONENT_OTHER_DATE",
                                        "opponent": values.get("opponent"), "event_date": date})
                elif date in dates:
                    occurrences.append({**base, "relation": "UNBOUND_OPPONENT_ON_EVENT_DATE",
                                        "opponent": values.get("opponent"), "event_date": date})
        for item in doc["_json_ld"]:
            if not set(item["dates"]) & dates:
                continue
            for side, other in (("away", "home"), ("home", "away")):
                if binds_opponent(item[side], away)[0]:
                    ld_statements.append({"document": doc["document"], "logical": doc["logical"],
                                          "start": item["start"], "opponent_side": side,
                                          "owner_designation": "HOME" if side == "away" else "AWAY",
                                          "owner_side_name": item[other]})
    fields: dict[str, Any] = {}
    reasons: list[str] = []
    other_on_date = [o for o in occurrences if o["relation"] == "UNBOUND_OPPONENT_ON_EVENT_DATE"]
    other_dates = [o for o in occurrences if o["relation"] == "BOUND_OPPONENT_OTHER_DATE"]

    def witness(w: dict[str, Any], member: str, raw: Any, value: Any) -> dict[str, Any]:
        return {"document": w["document"], "logical": w["logical"], "structure": w["structure"],
                "instance": w["instance"], "record_index": w["record_index"], "member": member, "raw": raw,
                "value": value}
    if bound:
        disposition = "RECORD_BOUND"
        season = [witness(w, w["season_witness"]["member"], w["season_witness"]["raw"], SEASON) for w in bound]
        fields["season"] = {"state": "SUPPORTED", "value": SEASON, "comparison": "AGREES", "witnesses": season}
        opp = [{**witness(w, MEMBER_NAMES[w["structure"]]["opponent"],
                          w["members"][MEMBER_NAMES[w["structure"]]["opponent"]], w["values"]["opponent"]),
                "normalized": w["normalized"], "transformations": w["transformations"]} for w in bound]
        fields["opponent"] = {"state": "CONFLICTING" if other_on_date else "SUPPORTED",
                              "value": sorted({w["value"] for w in opp}) if not other_on_date else
                              sorted({w["value"] for w in opp} | {o["opponent"] or "" for o in other_on_date}),
                              "comparison": "AGREES" if not other_on_date else "NOT_COMPARABLE",
                              "witnesses": opp}
        dwit = [witness(w, w["values"]["event_date_member"], w["members"].get(w["values"]["event_date_member"])
                        if w["values"]["event_date_member"] in w["members"] else
                        [w["members"].get("weekday"), w["members"].get("month_day")], w["values"]["event_date"])
                for w in bound]
        state, value = v1._single([w["value"] for w in dwit])
        fields["event_date"] = {"state": state, "value": value, "comparison": "AGREES" if state == "SUPPORTED" and
                                value in dates else "NOT_COMPARABLE", "witnesses": dwit}
        for field, key in (("designation", "designation"), ("venue_facility", "facility"),
                           ("venue_location", "location")):
            member = {"designation": "designation", "venue_facility": "facility", "venue_location": "location"}[field]
            wits = [witness(w, MEMBER_NAMES[w["structure"]][member],
                            w["members"].get(MEMBER_NAMES[w["structure"]][member]), w["values"].get(key))
                    for w in bound if w["values"].get(key) is not None]
            state, value = v1._single([w["value"] for w in wits])
            extra: dict[str, Any] = {}
            if field == "designation":
                conflicts = [s for s in ld_statements if state == "SUPPORTED" and s["owner_designation"] != value]
                if conflicts:
                    extra["json_ld_conflicts"] = conflicts
                    state, value = "CONFLICTING", sorted({value} | {s["owner_designation"] for s in conflicts})
                comparison = "NOT_COMPARABLE" if state != "SUPPORTED" else (
                    "AGREES" if value == claims["owner_designation"] else "DISAGREES")
            elif field == "venue_facility":
                provider = claims["venue"]["full_name"]
                comparison = "NOT_COMPARABLE" if state != "SUPPORTED" or not provider else (
                    "AGREES" if v1.name_key(value) == v1.name_key(provider) else "TEXT_DIFFERS")
            else:
                comparison = "NOT_COMPARABLE"
            fields[field] = {"state": state, "value": value, "comparison": comparison, "witnesses": wits, **extra}
        twits = [{"document": w["document"], "logical": w["logical"], "structure": w["structure"],
                  "instance": w["instance"], "record_index": w["record_index"], "statements": w["values"]["time"]}
                 for w in bound]
        resolved = v1.resolve_time([{"time": w["values"]["time"]} for w in bound])
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


def _field_view(field: dict[str, Any]) -> dict[str, Any]:
    return {"state": field["state"], "value": field["value"], "comparison": field["comparison"]}


def movement(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """The event's and every field's movement from the verified V1 record to the successor record."""
    per_field = {}
    for field in FIELDS:
        before, after = _field_view(previous["fields"][field]), _field_view(current["fields"][field])
        if v1._same(before, after):
            per_field[field] = "UNCHANGED"
        elif before["state"] == "UNSUPPORTED" and after["state"] != "UNSUPPORTED":
            per_field[field] = "NEWLY_STATED"
        else:
            per_field[field] = "STATE_CHANGED"
    was, now = previous["disposition"] == "RECORD_BOUND", current["disposition"] == "RECORD_BOUND"
    if was and now:
        event = "PRESERVED_RECORD_BOUND" if all(v == "UNCHANGED" for v in per_field.values()) else \
            "RECORD_BOUND_FIELDS_CHANGED"
    elif now:
        event = "NEWLY_RECORD_BOUND"
    elif was:
        event = "SUPPORT_LOST"
    else:
        event = "STILL_UNSUPPORTED_SAME_DISPOSITION" if previous["disposition"] == current["disposition"] else \
            "STILL_UNSUPPORTED_DISPOSITION_REFINED"
    return {"event": event, "fields": per_field}


def processing_order(count: int, order: str | None) -> list[int]:
    return v1.processing_order(count, order)


def derive_expansion(spec: dict[str, Any], contract_sha256: str, predecessor: dict[str, Any], raw: dict[str, bytes],
                     *, order: str | None = None) -> dict[str, Any]:
    """The complete successor document re-derived from the verified predecessor (its events, sources and bodies), the
    frozen successor contract and the retained raw bodies; the predecessor document is never edited."""
    previous = predecessor["schedule"]
    events = previous["events"]
    cohort = [{"event_key": e["event_key"], "ncaa_org_id": e["owner"]["ncaa_org_id"],
               "official_name": e["owner"]["official_name"], "directory_host": e["owner"]["directory_host"]}
              for e in events]
    if not v1._same(cohort, spec["expected"]["events"]) or spec["expected"]["expected_events"] != len(events):
        raise ScheduleError("SCHEDULE_EXPANSION_COHORT_MISMATCH", "the contract cohort is not the predecessor's "
                                                                  "verified event population")
    if not v1._same(spec.get("shadow"), {k: previous["shadow"].get(k) for k in SHADOW_PINS}):
        raise ScheduleError("SCHEDULE_EXPANSION_SHADOW_MISMATCH", "the contract's shadow is not the predecessor's "
                                                                  "verified shadow")
    decisions = spec["institution_decisions"]
    check_decisions(decisions, {e["owner"]["ncaa_org_id"]: e["owner"] for e in events})
    by_event = {e["event_key"]: e for e in events}
    docs_by_event: dict[str, list[dict[str, Any]]] = {k: [] for k in by_event}
    sources = []
    for src in previous["sources"]:
        event = by_event[src["event_key"]]
        document = None
        if src["document"] is not None:
            sha = src["document"]["document"]
            census = document_census(sha, raw[sha], event, decisions)
            census["logical"] = src["logical"]
            docs_by_event[src["event_key"]].append(census)
            document = census
        sources.append(src)
    records = []
    for index in processing_order(len(events), order):
        event = events[index]
        key = event["event_key"]
        result = qualify_event(event, docs_by_event[key])
        owners = [{"document": d["document"], "state": d["owner"]["state"], "decision": d["owner"]["decision"]}
                  for d in docs_by_event[key]]
        current = {"disposition": result["disposition"], "fields": result["fields"]}
        records.append({"record_type": "schedule_event", "event_key": key, "season": event["season"],
                        "owner": {**event["owner"], "identity": owners}, "opponent": event["opponent"],
                        "provider_claims": event["provider_claims"], "requests": event["requests"],
                        "attempts": event["attempts"], "documents": event["documents"],
                        "disposition": result["disposition"], "disposition_reasons": result["disposition_reasons"],
                        "fields": result["fields"], "occurrences": result["occurrences"],
                        "predecessor": {"disposition": event["disposition"],
                                        "disposition_reasons": event["disposition_reasons"],
                                        "fields": {f: _field_view(event["fields"][f]) for f in FIELDS}},
                        "movement": movement(event, current), "labels": dict(RECORD_LABELS)})
    records.sort(key=lambda r: r["event_key"])
    census_by_logical = {d["logical"]: d for docs in docs_by_event.values() for d in docs}
    out_sources = []
    for src in sources:
        census = census_by_logical.get(src["logical"])
        document = None if census is None else {k: v for k, v in census.items()
                                                if not k.startswith("_") and k != "logical"}
        out_sources.append({**{k: src[k] for k in v1.SOURCE_FIELDS if k not in ("document", "labels")},
                            "document": document,
                            "predecessor_document": None if src["document"] is None else
                            {"qualified": src["document"]["qualified"], "owner_state": src["document"]["owner"]["state"]},
                            "labels": dict(RECORD_LABELS)})
    acquisition = previous["acquisition"]
    bound = acquisition["availability_bound_utc"]
    frozen = spec["policy_frozen_utc"]
    effective = max(bound, frozen)
    summary = summary_document(records, out_sources)
    return {"schema": SCHEMA, "population": POPULATION, "designation": DESIGNATION,
            "contract": {"id": CONTRACT_ID, "sha256": contract_sha256},
            "predecessor": {**{k: spec["predecessor"][k] for k in PREDECESSOR_PINS},
                            "verified_by": "the accepted BAT-726 reader (schedule.verify_sidecar) with its own pinned "
                                           "contract and profile, at every read",
                            "bundled_at": f"{PREDECESSOR_ROOT}/{spec['predecessor']['identity']}/"},
            "shadow": previous["shadow"],
            "acquisition": {**acquisition, "new_requests": 0, "source": "RETAINED_CYCLE54_CAPTURE_NOT_NEW_ACQUISITION"},
            "policy": {"policy_frozen_utc": frozen, "authored": spec["policy"]["authored"],
                       "decisions": [d["id"] for d in decisions]},
            "availability": {"observation_bound_utc": bound, "policy_frozen_utc": frozen, "effective_utc": effective,
                             "rule": AVAILABILITY_RULE},
            "labels": dict(LABELS), "events": records, "sources": out_sources, "summary": summary,
            "counts": {"events": len(records), "participants": 2 * len(records), "sources": len(out_sources),
                       "attempts": acquisition["attempts"], "documents": sum(1 for s in out_sources if s["document"]),
                       "record_bound_events": sum(r["disposition"] == "RECORD_BOUND" for r in records),
                       "newly_record_bound_events": sum(r["movement"]["event"] == "NEWLY_RECORD_BOUND"
                                                        for r in records),
                       "preserved_record_bound_events": sum(r["movement"]["event"] == "PRESERVED_RECORD_BOUND"
                                                            for r in records),
                       "new_requests": 0}}


def summary_document(records: list[dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    base = v1.summary_document(records, sources)
    owners: dict[str, int] = {}
    for src in sources:
        if src["document"]:
            state = src["document"]["owner"]["state"]
            owners[state] = owners.get(state, 0) + 1
    movements = {m: sum(r["movement"]["event"] == m for r in records) for m in EVENT_MOVEMENTS}
    fields = {f: {m: sum(r["movement"]["fields"][f] == m for r in records) for m in FIELD_MOVEMENTS} for f in FIELDS}
    return {**base, "owner_states": dict(sorted(owners.items())), "movements": movements, "field_movements": fields}


# --------------------------------------------------------------------------------------------- contract

def contract_code_document() -> dict[str, Any]:
    """Every rule member of the committed contract that must equal the frozen code."""
    return {"labels": LABELS, "record_labels": RECORD_LABELS, "numeric_contract": NUMERIC_CONTRACT,
            "structures": STRUCTURES, "new_structures": list(NEW_STRUCTURES), "season_headings": SEASON_HEADINGS,
            "season_year_rule": SEASON_YEAR_RULE, "text_rule": TEXT_RULE, "name_rules": NAME_RULES,
            "known_event_annotations": list(KNOWN_EVENT_ANNOTATIONS), "identity_members": IDENTITY_MEMBERS,
            "decision_kinds": DECISION_KINDS, "decision_bases": DECISION_BASES, "owner_rules": OWNER_RULES,
            "owner_states": list(OWNER_STATES), "fields": list(FIELDS), "field_states": list(FIELD_STATES),
            "time_states": list(TIME_STATES), "comparisons": list(COMPARISONS), "dispositions": list(DISPOSITIONS),
            "field_rules": FIELD_RULES, "time_rules": TIME_RULES, "availability_rule": AVAILABILITY_RULE,
            "event_movements": list(EVENT_MOVEMENTS), "field_movements": list(FIELD_MOVEMENTS),
            "grains": list(GRAINS), "event_fields": list(EVENT_FIELDS), "source_fields": list(SOURCE_FIELDS),
            "top_level": list(TOP_LEVEL), "families": list(FAMILIES), "profile_fields": list(PROFILE_FIELDS),
            "predecessor_pins": list(PREDECESSOR_PINS), "shadow_pins": list(SHADOW_PINS)}


def _spec(contract: bytes, contract_sha256: str, chunk_size: int = 1 << 20) -> dict[str, Any]:
    if pv._hash_chunks(contract, chunk_size) != contract_sha256:
        raise ScheduleError("SCHEDULE_EXPANSION_CONTRACT_NOT_COMMITTED_AUTHORITY",
                            f"the bundled contract hashes to {v1.sha256_hex(contract)}, not the committed "
                            f"{contract_sha256}")
    spec = v1.strict_json(contract, "SCHEDULE_EXPANSION_CONTRACT_MALFORMED")
    if not isinstance(spec, dict) or spec.get("contract_id") != CONTRACT_ID or spec.get("population_id") != POPULATION:
        raise ScheduleError("SCHEDULE_EXPANSION_CONTRACT_MALFORMED", "the contract is not the schedule expansion "
                                                                     "contract")
    for member, constant in contract_code_document().items():
        if not v1._same(spec.get(member), constant):
            raise ScheduleError("SCHEDULE_EXPANSION_CONTRACT_CODE_DISAGREEMENT",
                                f"the contract's {member} differ from the frozen code")
    pred = spec.get("predecessor")
    if not isinstance(pred, dict) or set(pred) != set(PREDECESSOR_PINS) or pred.get("population") != v1.POPULATION or \
            pred.get("contract_id") != v1.CONTRACT_ID or type(pred.get("attempts")) is not int or \
            not all(isinstance(pred.get(k), str) and IDENTITY_RE.match(pred[k]) for k in (
                "identity", "schedule_sha256", "contract_sha256", "journal_sha256")) or \
            v1.parse_utc_text(pred.get("availability_bound_utc")) is None:
        raise ScheduleError("SCHEDULE_EXPANSION_CONTRACT_MALFORMED", "the contract does not pin the predecessor")
    frozen = v1.parse_utc_text(spec.get("policy_frozen_utc"))
    if frozen is None:
        raise ScheduleError("SCHEDULE_EXPANSION_CONTRACT_MALFORMED", "policy_frozen_utc is not a UTC instant")
    if frozen < v1.parse_utc_text(pred["availability_bound_utc"]):
        raise ScheduleError("SCHEDULE_EXPANSION_RETROACTIVE_POLICY_TIME",
                            "the successor policy cannot be frozen before the retained capture it interprets ended")
    policy = spec.get("policy")
    if not isinstance(policy, dict) or not isinstance(policy.get("authored"), str):
        raise ScheduleError("SCHEDULE_EXPANSION_CONTRACT_MALFORMED", "the contract does not disclose its authoring")
    expected = spec.get("expected")
    if not isinstance(expected, dict) or not isinstance(expected.get("events"), list) or \
            type(expected.get("expected_events")) is not int:
        raise ScheduleError("SCHEDULE_EXPANSION_CONTRACT_MALFORMED", "the contract does not pin the expected cohort")
    decisions = spec.get("institution_decisions")
    if not isinstance(decisions, list):
        raise ScheduleError("SCHEDULE_EXPANSION_CONTRACT_MALFORMED", "the contract has no institution decisions list")
    seen = set()
    for decision in decisions:
        ok = isinstance(decision, dict) and isinstance(decision.get("id"), str) and decision["id"] not in seen and \
            type(decision.get("ncaa_org_id")) is int and decision.get("kind") in DECISION_KINDS and \
            isinstance(decision.get("official_name"), str) and isinstance(decision.get("directory_host"), str) and \
            isinstance(decision.get("identity_members"), list) and decision["identity_members"] and \
            all(isinstance(m, dict) and m.get("member") in IDENTITY_MEMBERS and isinstance(m.get("value"), str) and
                m.get("basis") in DECISION_BASES for m in decision["identity_members"])
        statements = decision.get("owner_statements") if isinstance(decision, dict) else None
        if ok and decision["kind"] == "OWNER_STATEMENT":
            ok = isinstance(statements, list) and bool(statements) and all(
                isinstance(s, dict) and isinstance(s.get("value"), str) and s.get("basis") in DECISION_BASES
                for s in statements)
        elif ok:
            ok = statements in (None, [])
        if not ok:
            raise ScheduleError("SCHEDULE_EXPANSION_CONTRACT_MALFORMED", f"an institution decision is malformed: "
                                                                         f"{str(decision)[:120]}")
        seen.add(decision["id"])
    return spec


# --------------------------------------------------------------------------------------------- identity

def file_bytes(document: dict[str, Any]) -> bytes:
    return v1.file_bytes(document)


def identity_document(schedule: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    return {"schema": IDENTITY_SCHEMA, "population": POPULATION, "contract_id": CONTRACT_ID,
            "contract_sha256": schedule["contract"]["sha256"], "predecessor_identity": schedule["predecessor"]["identity"],
            "shadow_identity": schedule["shadow"]["identity"],
            "policy_frozen_utc": schedule["policy"]["policy_frozen_utc"], "schedule_file": SCHEDULE_FILE,
            "schedule_sha256": v1.sha256_hex(file_bytes(schedule)), "bundle": bundle}


def schedule_identity(schedule: dict[str, Any], bundle: dict[str, Any]) -> str:
    return v1.sha256_hex(v1.canonical_bytes(identity_document(schedule, bundle)))


def profile_of(schedule: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    return {"schedule_identity": schedule_identity(schedule, bundle),
            "schedule_sha256": v1.sha256_hex(file_bytes(schedule)),
            "predecessor_identity": schedule["predecessor"]["identity"],
            "policy_frozen_utc": schedule["policy"]["policy_frozen_utc"],
            "effective_availability_utc": schedule["availability"]["effective_utc"]}


def first_difference(expected: dict[str, Any], actual: Any) -> tuple[str, str] | None:
    if not isinstance(actual, dict) or set(actual) != set(TOP_LEVEL):
        extra = sorted(set(actual) - set(TOP_LEVEL)) if isinstance(actual, dict) else ["<not an object>"]
        missing = sorted(set(TOP_LEVEL) - set(actual)) if isinstance(actual, dict) else []
        return "SCHEMA", f"top-level members differ (extra {extra}, missing {missing})"
    if not v1._same(expected["schema"], actual["schema"]) or not v1._same(expected["population"],
                                                                           actual["population"]):
        return "SCHEMA", "schema or population differs"
    for family, member in (("DESIGNATION", "designation"), ("CONTRACT", "contract"), ("PREDECESSOR", "predecessor"),
                           ("SHADOW", "shadow"), ("ACQUISITION", "acquisition"), ("POLICY", "policy"),
                           ("AVAILABILITY", "availability"), ("LABELS", "labels")):
        if not v1._same(expected[member], actual[member]):
            return family, f"{member} differs"
    for name, key, fields, ident in (("EVENT", "events", EVENT_FIELDS, lambda r: r.get("event_key")),
                                     ("SOURCE", "sources", SOURCE_FIELDS, lambda r: r.get("logical"))):
        want, got = expected[key], actual[key]
        if not isinstance(got, list) or not all(isinstance(r, dict) for r in got) or \
                not v1._same([ident(r) for r in want], [ident(r) for r in got]):
            return f"{name}_MEMBERSHIP", f"{key} membership, multiplicity or order differs"
        for index, (w, g) in enumerate(zip(want, got)):
            if set(g) != set(fields):
                return f"{name}_RECORD", f"{key}[{index}] members differ"
            for field in fields:
                if not v1._same(w[field], g[field]):
                    return f"{name}_RECORD", f"{key}[{index}].{field} differs"
    if not v1._same(expected["summary"], actual["summary"]):
        return "SUMMARY", "summary differs"
    if not v1._same(expected["counts"], actual["counts"]):
        return "COUNTS", "counts differ"
    return None


# --------------------------------------------------------------------------------------------- reader

def _predecessor(path: str, shadow_path: Path | str, spec: dict[str, Any], predecessor_profile: Any,
                 shadow_profile: Any) -> dict[str, Any]:
    """The bundled predecessor verified completely by the accepted BAT-726 reader (its own pinned contract and profile
    unless a test passes fixture authorities); its refusals keep their codes under a SCHEDULE_EXPANSION_PREDECESSOR_
    prefix."""
    pins = spec["predecessor"]
    kwargs: dict[str, Any] = {}
    if predecessor_profile is PINNED:
        if pins["contract_sha256"] != v1.CONTRACT_SHA256:
            raise ScheduleError("SCHEDULE_EXPANSION_PREDECESSOR_NOT_PINNED", "the contract's predecessor contract is "
                                                                             "not the accepted V1 authority")
    else:
        kwargs["profile"] = predecessor_profile
    if shadow_profile is not PINNED:
        kwargs["shadow_profile"] = shadow_profile
    try:
        binding = v1.verify_sidecar(path, shadow_path, contract_sha256=pins["contract_sha256"],
                                    expect_identity=pins["identity"], **kwargs)
    except ScheduleError as exc:
        raise ScheduleError(f"SCHEDULE_EXPANSION_PREDECESSOR_{exc.code}", str(exc)) from exc
    profile = binding["profile"]
    if binding["schedule_sha256"] != pins["schedule_sha256"] or profile["journal_sha256"] != pins["journal_sha256"] or \
            not v1._same(profile["attempts"], pins["attempts"]) or \
            profile["availability_bound_utc"] != pins["availability_bound_utc"]:
        raise ScheduleError("SCHEDULE_EXPANSION_PREDECESSOR_NOT_PINNED", "the bundled predecessor is not the pinned "
                                                                         "accepted evidence")
    return binding


def _split(files: dict[str, bytes], identity: str) -> tuple[dict[str, bytes], dict[str, bytes]]:
    prefix = f"{PREDECESSOR_ROOT}/{identity}/"
    predecessor = {n[len(prefix):]: b for n, b in files.items() if n.startswith(prefix)}
    others = sorted(n for n in files if n != CONTRACT_MEMBER and not n.startswith(prefix))
    if others:
        raise ScheduleError("SCHEDULE_EXPANSION_BUNDLE_MEMBERSHIP_MISMATCH", f"unexpected members {others[:3]}")
    if v1.SCHEDULE_FILE not in predecessor:
        raise ScheduleError("SCHEDULE_EXPANSION_BUNDLE_MEMBERSHIP_MISMATCH", "the predecessor sidecar is missing")
    return predecessor, {n: b for n, b in predecessor.items() if n != v1.SCHEDULE_FILE}


def verify_expansion(path: Path | str, shadow_path: Path | str, *, contract_sha256: str = CONTRACT_SHA256,
                     expect_identity: str | None = None, profile: Any = PINNED, predecessor_profile: Any = PINNED,
                     shadow_profile: Any = PINNED, require_pinned_profile: bool = True) -> dict[str, Any]:
    """Verify a successor sidecar directory completely (its predecessor through the accepted V1 reader) and return
    its binding."""
    location = v1.literal_location(path)
    if not os.path.isfile(pv.io_path(location)):
        raise ScheduleError("SCHEDULE_MISSING", f"no schedule file at {location}")
    directory, name = os.path.split(location)
    if name != SCHEDULE_FILE or not IDENTITY_RE.match(os.path.basename(directory)):
        raise ScheduleError("SCHEDULE_LOCATION_INVALID", f"the sidecar must be <identity>/{SCHEDULE_FILE} with a 64-hex "
                                                         "identity directory")
    files = pv.directory_files(pv.io_path(directory))
    got = files.pop(SCHEDULE_FILE, None)
    contract = files.get(CONTRACT_MEMBER)
    if got is None or contract is None:
        raise ScheduleError("SCHEDULE_EXPANSION_BUNDLE_MEMBERSHIP_MISMATCH", "the schedule or the contract is missing")
    spec = _spec(contract, contract_sha256)
    pred_files, members = _split(files, spec["predecessor"]["identity"])
    pred_path = os.path.join(directory, PREDECESSOR_ROOT, spec["predecessor"]["identity"], v1.SCHEDULE_FILE)
    predecessor = _predecessor(pred_path, shadow_path, spec, predecessor_profile, shadow_profile)
    _segments, raw = v1.split_members(members)
    expected = derive_expansion(spec, contract_sha256, predecessor, raw)
    if got != file_bytes(expected):
        supplied = v1.strict_json(got, "SCHEDULE_EXPANSION_MALFORMED")
        diff = first_difference(expected, supplied)
        family, detail = diff if diff else ("CANONICAL_FORM", "the schedule bytes are not the frozen canonical form")
        raise ScheduleError(f"SCHEDULE_EXPANSION_{family}_MISMATCH", detail)
    bundle = {n: {"sha256": v1.sha256_hex(files[n]), "bytes": len(files[n])} for n in sorted(files)}
    identity = schedule_identity(expected, bundle)
    if os.path.basename(directory) != identity:
        raise ScheduleError("SCHEDULE_EXPANSION_IDENTITY_MISMATCH", f"the identity document hashes to {identity}, the "
                                                                    f"directory is {os.path.basename(directory)}")
    if expect_identity is not None and expect_identity != identity:
        raise ScheduleError("STALE_SCHEDULE_IDENTITY", f"expected {expect_identity}, found {identity}")
    actual_profile = profile_of(expected, bundle)
    pinned = EXPANSION_PROFILE if profile is PINNED else profile
    if require_pinned_profile:
        if pinned is None:
            raise ScheduleError("SCHEDULE_EXPANSION_PROFILE_NOT_PINNED", "no actual successor profile is packaged")
        if not isinstance(pinned, dict) or set(pinned) != set(PROFILE_FIELDS):
            raise ScheduleError("SCHEDULE_EXPANSION_PROFILE_NOT_PINNED", "the packaged successor profile is malformed")
        if any(not v1._same(pinned[k], actual_profile[k]) for k in PROFILE_FIELDS):
            raise ScheduleError("SCHEDULE_EXPANSION_NOT_PINNED_SIDECAR", "the sidecar is not the one the packaged gate "
                                                                         "pins")
    return {"schedule_identity": identity, "schedule_sha256": v1.sha256_hex(got), "location": location,
            "identity_document": identity_document(expected, bundle), "schedule": expected, "bundle": bundle,
            "profile": actual_profile, "profile_pinned": isinstance(pinned, dict) and
            all(v1._same(pinned.get(k), actual_profile[k]) for k in PROFILE_FIELDS),
            "predecessor_identity": predecessor["schedule_identity"], "shadow_identity": predecessor["shadow_identity"]}


class ExpansionEvidence:
    """A completely verified successor sidecar; rows come only from its re-derived document."""

    def __init__(self, path: Path | str, shadow_path: Path | str, *, contract_sha256: str = CONTRACT_SHA256,
                 expect_identity: str | None = None, profile: Any = PINNED, predecessor_profile: Any = PINNED,
                 shadow_profile: Any = PINNED) -> None:
        self.binding = verify_expansion(path, shadow_path, contract_sha256=contract_sha256,
                                        expect_identity=expect_identity, profile=profile,
                                        predecessor_profile=predecessor_profile, shadow_profile=shadow_profile)
        self.schedule = self.binding["schedule"]

    def __enter__(self) -> "ExpansionEvidence":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def query(self, grain: str, *, cutoff: str | None = None, season: int | None = None, event: str | None = None,
              team: str | None = None, limit: int | None = 50, offset: int = 0,
              all_rows: bool = False) -> dict[str, Any]:
        filters = v1.ScheduleEvidence.filters(grain, season=season, event=event, team=team)
        if offset < 0:
            raise ScheduleError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise ScheduleError("NEGATIVE_LIMIT", "limit must be zero or positive")
        when = v1.parse_cutoff(cutoff)
        availability = self.schedule["availability"]
        bound = v1.parse_utc_text(availability["observation_bound_utc"])
        frozen = v1.parse_utc_text(availability["policy_frozen_utc"])
        if when < bound:
            raise ScheduleError("SCHEDULE_UNAVAILABLE_BEFORE_OBSERVATION_BOUND",
                                f"the retained observations end at {availability['observation_bound_utc']}; nothing "
                                f"was observed by {v1.iso_micro(when)}")
        if when < frozen:
            raise ScheduleError("SCHEDULE_UNAVAILABLE_BEFORE_POLICY_FROZEN",
                                f"the successor policy was frozen at {availability['policy_frozen_utc']}; its "
                                f"interpretation did not exist at {v1.iso_micro(when)}")
        identity = self.binding["schedule_identity"]
        acquisition = self.schedule["acquisition"]
        result: dict[str, Any] = {
            "schedule_identity": identity, "schedule_sha256": self.binding["schedule_sha256"],
            "contract_id": CONTRACT_ID, "contract_sha256": self.schedule["contract"]["sha256"],
            "population": POPULATION, "designation": DESIGNATION, "shadow_identity": self.binding["shadow_identity"],
            "predecessor_identity": self.binding["predecessor_identity"], "grain": grain, "filters": filters,
            "cutoff": {"literal": cutoff, "utc": v1.iso_micro(when)},
            "availability": {"observation_bound_utc": availability["observation_bound_utc"],
                             "policy_frozen_utc": availability["policy_frozen_utc"],
                             "effective_utc": availability["effective_utc"], "state": AVAILABLE_STATE,
                             "rule": AVAILABILITY_RULE},
            "acquisition": {k: acquisition[k] for k in ("attempts", "ceiling", "logical_requests", "documents",
                                                        "stopped_host_families", "first_start_utc", "new_requests")},
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
        rows = [{key: item, "schedule_identity": identity, "availability_effective_utc": availability["effective_utc"],
                 "labels": dict(RECORD_LABELS)} for item in items[offset:stop]]
        result.update(season_scope_state=IN_SCOPE_STATE, total=total, returned=len(rows), rows=rows,
                      next_offset=offset + len(rows) if offset + len(rows) < total else None)
        return result


# --------------------------------------------------------------------------------------------- build helper

def expansion_files(contract: bytes, shadow_path: Path | str, predecessor_path: Path | str, *,
                    contract_sha256: str = CONTRACT_SHA256, order: str | None = None, chunk_size: int = 1 << 20,
                    predecessor_profile: Any = PINNED, shadow_profile: Any = PINNED
                    ) -> tuple[str, dict[str, bytes], dict[str, Any], dict[str, Any]]:
    """The identity, every file of the successor directory, the identity document and the schedule document."""
    spec = _spec(contract, contract_sha256, chunk_size)
    location = v1.literal_location(predecessor_path)
    if os.path.basename(os.path.dirname(location)) != spec["predecessor"]["identity"]:
        raise ScheduleError("SCHEDULE_EXPANSION_PREDECESSOR_NOT_PINNED", "the named predecessor is not the pinned "
                                                                         "identity directory")
    predecessor = _predecessor(location, shadow_path, spec, predecessor_profile, shadow_profile)
    pred_files = pv.directory_files(pv.io_path(os.path.dirname(location)))
    members = {CONTRACT_MEMBER: contract, **{f"{PREDECESSOR_ROOT}/{spec['predecessor']['identity']}/{n}": b
                                             for n, b in pred_files.items()}}
    _segments, raw = v1.split_members({n: b for n, b in pred_files.items() if n != v1.SCHEDULE_FILE})
    names = sorted(raw)
    shuffled = {names[i]: raw[names[i]] for i in processing_order(len(names), order)}
    document = derive_expansion(spec, contract_sha256, predecessor, shuffled, order=order)
    bundle = {n: {"sha256": pv._hash_chunks(members[n], chunk_size), "bytes": len(members[n])} for n in sorted(members)}
    files = {SCHEDULE_FILE: file_bytes(document), **members}
    return schedule_identity(document, bundle), files, identity_document(document, bundle), document


__all__ = ["ExpansionEvidence", "ScheduleError", "binds_opponent", "derive_expansion", "document_census",
           "expansion_files", "extract_document", "first_difference", "identity_document", "joined_date",
           "opponent_name", "owner_state", "profile_of", "qualify_event", "record_values", "schedule_identity",
           "season_date", "selects", "split_date", "verify_expansion", "CONTRACT_SHA256", "EXPANSION_PROFILE",
           "LABELS", "RECORD_LABELS", "STRUCTURES"]
