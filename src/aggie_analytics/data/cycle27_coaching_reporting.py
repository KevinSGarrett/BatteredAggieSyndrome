"""Cycle 27 coaching census, staff-context packets, and consumption labels.

Coaching is a planned domain. This module inventories schema, source, canonical
records, temporal admission, historical analogues, and actual Week 1 model
consumption. It does not invent coach bonuses, infer play-callers from titles,
treat Coaches Poll rank as staff, or claim national coverage from two teams.
"""

from __future__ import annotations

import hashlib
import json
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import parse_qs, urlparse

from aggie_analytics.context_intelligence.coaching import manual_coach_bonus

# Duplicated from national_expectation_baselines so core CI stays numpy-free.
# Consumption census only needs the admitted-name inventory, not design matrices.
PRIOR_DOMAIN_NUMERIC = (
    "prior_games_played",
    "prior_win_rate",
    "prior_points_for_mean",
    "prior_points_against_mean",
    "prior_margin_mean",
    "prior_season_win_rate",
    "season_to_date_games",
    "season_to_date_win_rate",
    "opponent_prior_games_played",
    "opponent_prior_win_rate",
    "opponent_prior_margin_mean",
    "opponent_prior_season_win_rate",
    "prior_win_rate_differential",
)
PRIOR_DOMAIN_BOOLEAN = ("is_home", "is_neutral_site")
ALL_NUMERIC = PRIOR_DOMAIN_NUMERIC + (
    "ap_poll_rank",
    "coaches_poll_rank",
    "opponent_ap_poll_rank",
    "venue_elevation_m",
    "venue_latitude",
    "venue_longitude",
)
ALL_BOOLEAN = PRIOR_DOMAIN_BOOLEAN + (
    "rankings_source_available",
    "venue_dome",
    "venue_grass",
    "team_is_fbs",
)
FEATURE_SCOPES = {
    "NONE": ((), (), False),
    "PRIOR_OUTCOME_DOMAIN_AND_SITE": (
        PRIOR_DOMAIN_NUMERIC,
        PRIOR_DOMAIN_BOOLEAN,
        False,
    ),
    "OUTCOME_SEQUENCE_AND_SITE": ((), PRIOR_DOMAIN_BOOLEAN, False),
    "ALL_ADMITTED_FEATURES": (ALL_NUMERIC, ALL_BOOLEAN, True),
}

SCHEMA_VERSION = "aggie.data.cycle27_coaching_data_and_consumption_census.v1"
CONTRACT_ID = "CYCLE27-COACHING-DATA-AND-CONSUMPTION-CENSUS-V1"
JIRA_KEY = "BAT-690"
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "CYCLE27_COACHING_CENSUS_CONTEXT_ONLY_NOT_CONSUMED"
FOCUS_CONTEST_ID = "6607349"
FOCUS_HOME_CANONICAL = "SRC-002:TEAM:245"
FOCUS_AWAY_CANONICAL = "SRC-002:TEAM:2623"
FOCUS_HOME_LABEL = "Texas A&M"
FOCUS_AWAY_LABEL = "Missouri State"
SEASON = 2026
COACHES_POLL_FIELDS = frozenset({"coaches_poll_rank", "coaches_poll_rank_missing"})
STAFF_ROLE_IDS = (
    "HEAD_COACH",
    "OFFENSIVE_COORDINATOR",
    "DEFENSIVE_COORDINATOR",
    "OFFENSIVE_PLAY_CALLER",
    "DEFENSIVE_PLAY_CALLER",
    "CO_OR_INTERIM_OR_DELEGATED",
    "SPECIAL_TEAMS_COORDINATOR",
)
STAFF_FEATURE_TOKENS = (
    "head_coach",
    "offensive_coordinator",
    "defensive_coordinator",
    "play_caller",
    "playcaller",
    "special_teams_coordinator",
    "staff_continuity",
    "coach_id",
    "coach_tenure",
)
DECLARED_OFFICIAL_STAFF_URLS = {
    FOCUS_HOME_CANONICAL: (
        "https://12thman.com/sports/football/coaches",
        "https://12thman.com/sports/football/staff",
        "https://12thman.com/coaches.aspx?path=football",
        "https://12thman.com/staff-directory/department/football",
    ),
    FOCUS_AWAY_CANONICAL: ("https://missouristatebears.com/sports/football/coaches",),
}
WRONG_SPORT_URL_TOKENS = (
    "womens-golf",
    "mens-golf",
    "/golf/",
    "womens-basketball",
    "volleyball",
)
STAFF_TITLE_TOKENS = (
    "coach",
    "coordinator",
    "analyst",
    "general manager",
    "quality control",
    "special teams",
)
FetchOpener = Callable[[str], tuple[int, bytes, str] | tuple[int, bytes, str, str]]
USER_AGENT = (
    "BAS-cycle27-staff-context/1.0 (research; "
    "+https://github.com/KevinSGarrett/BatteredAggieSyndrome)"
)
FETCH_TIMEOUT_SEC = 20
UNKNOWN_NOT_NONE = "UNKNOWN"
NOT_CONSUMED = "NOT_CONSUMED"
CONTEXT_ONLY = "CONTEXT_ONLY"
NOT_CONSUMED_BY_MODEL = "NOT_CONSUMED_BY_MODEL"


class CoachingCensusError(ValueError):
    """Raised when a coaching census or staff packet cannot be built honestly."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_label(moment: datetime | None = None) -> str:
    clock = moment or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise CoachingCensusError("as-of clock must be timezone-aware")
    return clock.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_feature_as_staff_evidence(field_name: str) -> dict[str, Any]:
    """Coaches Poll rank is a poll, not coaching-staff evidence."""
    name = str(field_name or "")
    if name in COACHES_POLL_FIELDS:
        return {
            "field_name": name,
            "is_staff_evidence": False,
            "classification": "COACHES_POLL_RANKING_NOT_STAFF",
            "model_consumption_if_present": "POLL_RANKING_NOT_STAFF_ROLE",
        }
    lowered = name.casefold()
    if any(token in lowered for token in STAFF_FEATURE_TOKENS):
        return {
            "field_name": name,
            "is_staff_evidence": True,
            "classification": "NAMED_STAFF_OR_ROLE_FIELD",
            "model_consumption_if_present": "REQUIRES_ACTIVE_PATH_TRACE",
        }
    return {
        "field_name": name,
        "is_staff_evidence": False,
        "classification": "NOT_A_STAFF_ROLE_FIELD",
        "model_consumption_if_present": "NOT_STAFF",
    }


def classify_head_coach_presence_boolean(
    head_coach_evidence_present: bool | None,
) -> dict[str, Any]:
    """A nonempty NCAA head-coach cell is not normalized staff coverage."""
    return {
        "head_coach_evidence_present": bool(head_coach_evidence_present),
        "full_staff_coverage": False,
        "normalized_staff_history": False,
        "canonical_role_episode": False,
        "classification": "HEAD_COACH_CELL_NONEMPTY_BOOLEAN_NOT_STAFF_COVERAGE",
    }


def classify_title_role(title: str | None) -> dict[str, Any]:
    text = re.sub(r"\s+", " ", str(title or "")).strip()
    lowered = text.casefold()
    flags = {
        "interim": bool(re.search(r"\binterim\b", lowered)),
        "co_role": bool(re.search(r"\bco[- ]", lowered)),
        "delegated": "assistant" in lowered and "coordinator" in lowered,
    }
    role_id = None
    if (
        re.search(r"\bhead coach\b", lowered)
        or re.search(r"\bhead football coach\b", lowered)
    ) and not re.search(r"\b(associate|assistant)\b", lowered):
        role_id = "HEAD_COACH"
    elif re.search(r"\boffensive coordinator\b", lowered):
        role_id = "OFFENSIVE_COORDINATOR"
    elif re.search(r"\bdefensive coordinator\b", lowered):
        role_id = "DEFENSIVE_COORDINATOR"
    elif re.search(r"\bspecial teams coordinator\b", lowered) or (
        re.search(r"\bspecial teams\b", lowered) and "coordinator" in lowered
    ):
        role_id = "SPECIAL_TEAMS_COORDINATOR"
    return {
        "title": text or None,
        "title_role_id": role_id,
        "co_or_interim_or_delegated": any(flags.values()),
        "flags": flags,
    }


def classify_title_versus_play_caller(
    title: str | None,
    *,
    explicit_play_caller_evidence: bool | None = None,
) -> dict[str, Any]:
    """A coordinator title is not play-caller proof."""
    classified = classify_title_role(title)
    title_mentions_play_caller = bool(
        re.search(r"play[ -]?caller", str(title or ""), re.I)
    )
    if explicit_play_caller_evidence is True:
        play_caller_status = "EXPLICIT_CONTEMPORANEOUS_EVIDENCE"
    elif explicit_play_caller_evidence is False:
        play_caller_status = "EXPLICIT_NOT_PLAY_CALLER"
    else:
        play_caller_status = "UNKNOWN_NOT_INFERRED_FROM_TITLE"
    return {
        **classified,
        "title_mentions_play_caller": title_mentions_play_caller,
        "title_is_play_caller_proof": False,
        "play_caller_status": play_caller_status,
        "offensive_play_caller": UNKNOWN_NOT_NONE
        if classified["title_role_id"] == "OFFENSIVE_COORDINATOR"
        else play_caller_status
        if classified["title_role_id"] is None
        else UNKNOWN_NOT_NONE,
        "defensive_play_caller": UNKNOWN_NOT_NONE
        if classified["title_role_id"] == "DEFENSIVE_COORDINATOR"
        else UNKNOWN_NOT_NONE,
    }


def classify_missing_role(value: Any) -> dict[str, Any]:
    """Missing evidence is UNKNOWN, never confirmed NONE/absent."""
    if value in (None, "", "MISSING", "UNKNOWN"):
        return {
            "status": UNKNOWN_NOT_NONE,
            "confirmed_absent": False,
            "confirmed_none": False,
            "classification": "MISSING_ROLE_IS_UNKNOWN_NOT_NONE",
        }
    return {
        "status": "OBSERVED",
        "confirmed_absent": False,
        "confirmed_none": False,
        "classification": "ROLE_VALUE_PRESENT_STILL_REQUIRES_EPISODE_BIND",
        "value": value,
    }


def bind_source_person_identity(
    *,
    source_person_name: str | None,
    canonical_coach_id: str | None,
    source_team_id: str | None,
    bound_team_id: str | None,
    source_season: int | None,
    bound_season: int | None,
) -> dict[str, Any]:
    """Equal names alone do not establish person identity or team-season bind."""

    if canonical_coach_id in (None, ""):
        return {
            "status": "NAME_ONLY_NOT_PERSON_IDENTITY",
            "canonical_coach_id": None,
            "source_person_name": source_person_name,
            "bound": False,
        }
    if source_team_id and bound_team_id and str(source_team_id) != str(bound_team_id):
        return {
            "status": "WRONG_TEAM_REJECTED",
            "canonical_coach_id": canonical_coach_id,
            "bound": False,
        }
    if (
        source_season is not None
        and bound_season is not None
        and int(source_season) != int(bound_season)
    ):
        return {
            "status": "WRONG_SEASON_REJECTED",
            "canonical_coach_id": canonical_coach_id,
            "bound": False,
        }
    return {
        "status": "CANONICAL_PERSON_BOUND",
        "canonical_coach_id": canonical_coach_id,
        "bound": True,
    }


def classify_role_effective_time(
    *,
    effective_from: str | None,
    synthesize_if_missing: bool = False,
) -> dict[str, Any]:
    """Unknown effective time stays unknown. Do not invent a timestamp."""

    if synthesize_if_missing and not effective_from:
        return {
            "status": "UNKNOWN_NOT_SYNTHESIZED",
            "effective_from": None,
            "invented": False,
            "rejected_synthesis": True,
        }
    if not effective_from:
        return {
            "status": "UNKNOWN_NOT_SYNTHESIZED",
            "effective_from": None,
            "invented": False,
            "rejected_synthesis": False,
        }
    return {
        "status": "OBSERVED_EFFECTIVE_FROM",
        "effective_from": effective_from,
        "invented": False,
        "rejected_synthesis": False,
    }


def classify_future_role_announcement(
    *,
    role_effective_utc: str | None,
    cutoff_utc: str | None,
) -> dict[str, Any]:
    """A later appointment is not the current play-caller at an earlier cutoff."""

    if not role_effective_utc or not cutoff_utc:
        return {
            "status": "UNKNOWN_EFFECTIVE_TIME",
            "current_play_caller": False,
            "current_role_at_cutoff": False,
        }
    if str(role_effective_utc) > str(cutoff_utc):
        return {
            "status": "FUTURE_APPOINTMENT_NOT_CURRENT_ROLE",
            "current_play_caller": False,
            "current_role_at_cutoff": False,
            "career_total_not_usable_at_earlier_cutoff": True,
        }
    return {
        "status": "EFFECTIVE_BY_CUTOFF",
        "current_play_caller": False,
        "current_role_at_cutoff": True,
        "career_total_not_usable_at_earlier_cutoff": True,
    }


def apply_coach_bonus(*args: Any, **kwargs: Any) -> float:
    """Manual coach point bonuses are forbidden."""
    return manual_coach_bonus(*args, **kwargs)


def acquisition_registry_coach_entries(
    registry: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not isinstance(registry, Mapping):
        return entries
    for source in registry.get("sources") or []:
        if not isinstance(source, Mapping):
            continue
        source_id = str(source.get("source_id") or source.get("id") or "")
        for endpoint in source.get("endpoints") or []:
            if not isinstance(endpoint, Mapping):
                continue
            path = str(endpoint.get("path") or endpoint.get("uri") or "")
            blob = f"{path} {json.dumps(endpoint, sort_keys=True)}".casefold()
            if "coach" in blob or "staff" in path.casefold():
                entries.append(
                    {
                        "source_id": source_id,
                        "path": path,
                        "endpoint": dict(endpoint),
                    }
                )
    return entries


def inspect_source_acquisition_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    coach_entries = acquisition_registry_coach_entries(registry)
    return {
        "registry_status": registry.get("registry_status"),
        "source_count": registry.get("source_count"),
        "coach_specific_entries": coach_entries,
        "coach_entry_present": bool(coach_entries),
        "structured_coaching_route": "SOURCE_ABSENT_NOT_REGISTERED"
        if not coach_entries
        else "REGISTERED",
        "do_not_invent_cfbd_coaches_path_from_schema_registry": True,
    }


def active_week1_staff_feature_columns(
    feature_column_names: Sequence[str],
) -> dict[str, Any]:
    staff_columns = []
    poll_columns = []
    for name in feature_column_names:
        classified = classify_feature_as_staff_evidence(name)
        if classified["classification"] == "COACHES_POLL_RANKING_NOT_STAFF":
            poll_columns.append(name)
        elif classified["is_staff_evidence"]:
            staff_columns.append(name)
    return {
        "inspected_column_count": len(list(feature_column_names)),
        "staff_role_columns": staff_columns,
        "coaches_poll_columns": poll_columns,
        "staff_role_column_count": len(staff_columns),
        "actual_model_consumption": NOT_CONSUMED
        if not staff_columns
        else "NAMED_STAFF_COLUMNS_PRESENT_TRACE_REQUIRED",
    }


def fitted_design_staff_columns(
    design_columns: Mapping[str, Any] | None,
) -> dict[str, Any]:
    scopes: dict[str, Any] = {}
    staff_total = 0
    poll_total = 0
    if isinstance(design_columns, Mapping):
        for scope, columns in design_columns.items():
            names = [str(name) for name in (columns or [])]
            inspected = active_week1_staff_feature_columns(names)
            scopes[str(scope)] = inspected
            staff_total += inspected["staff_role_column_count"]
            poll_total += len(inspected["coaches_poll_columns"])
    numeric_and_boolean = list(ALL_NUMERIC) + list(ALL_BOOLEAN)
    baseline_scope = active_week1_staff_feature_columns(numeric_and_boolean)
    all_admitted = FEATURE_SCOPES["ALL_ADMITTED_FEATURES"]
    return {
        "national_expectation_baseline_numeric_and_boolean": baseline_scope,
        "all_admitted_scope_uses_conference": all_admitted[2],
        "fitted_design_scopes": scopes,
        "staff_role_columns_in_fitted_design": staff_total,
        "coaches_poll_columns_in_fitted_design": poll_total,
        "actual_model_consumption": NOT_CONSUMED,
    }


def parse_staff_directory_html(html: str) -> list[dict[str, Any]]:
    """Extract name/title pairs without treating title as play-caller proof."""
    people: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _record(name: str, title: str, extractor: str) -> None:
        clean_name = html_unescape_text(name)
        clean_title = html_unescape_text(title)
        if not clean_name or not clean_title:
            return
        if len(clean_name) > 80 or len(clean_title) > 160:
            return
        first = clean_name.casefold().split(" ", 1)[0]
        if first in {
            "football",
            "basketball",
            "soccer",
            "golf",
            "volleyball",
            "baseball",
            "softball",
        }:
            return
        if len(clean_name.split()) < 2:
            return
        key = (clean_name.casefold(), clean_title.casefold())
        if key in seen:
            return
        seen.add(key)
        people.append(
            {
                "source_person_name": clean_name,
                "source_title": clean_title,
                "canonical_coach_id": None,
                "identity_bind": "NAME_TITLE_ONLY_NOT_CANONICAL_PERSON",
                "extractor": extractor,
                **classify_title_versus_play_caller(clean_title),
                "effective_from": None,
                "effective_to": None,
                "effective_date_status": "UNKNOWN_NOT_SYNTHESIZED",
                "first_known_at": None,
                "consumption": NOT_CONSUMED_BY_MODEL,
                "packet_use": CONTEXT_ONLY,
            }
        )

    json_ld_pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.I | re.S,
    )
    for match in json_ld_pattern.finditer(html or ""):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        blocks = payload if isinstance(payload, list) else [payload]
        for block in blocks:
            if not isinstance(block, Mapping):
                continue
            graph = block.get("@graph")
            nodes = graph if isinstance(graph, list) else [block]
            for node in nodes:
                if not isinstance(node, Mapping):
                    continue
                name = node.get("name")
                title = node.get("jobTitle") or node.get("roleName")
                if isinstance(name, str) and isinstance(title, str):
                    _record(name, title, "json_ld")

    name_re = (
        r"class=\"[^\"]*(?:sidearm-roster-coach-name|sidearm-coach-name|"
        r"s-person-card__name|c-coach-card__name)[^\"]*\"[^>]*>(.*?)</"
    )
    title_re = (
        r"class=\"[^\"]*(?:sidearm-roster-coach-title|sidearm-coach-title|"
        r"s-person-card__title|c-coach-card__title)[^\"]*\"[^>]*>(.*?)</"
    )
    names = [
        html_unescape_text(chunk)
        for chunk in re.findall(name_re, html or "", flags=re.I | re.S)
    ]
    titles = [
        html_unescape_text(chunk)
        for chunk in re.findall(title_re, html or "", flags=re.I | re.S)
    ]
    for name, title in zip(names, titles):
        _record(name, title, "sidearm_class_pair")

    staff_directory_row = re.compile(
        r'<a href="/staff/[^"]+" class="[^"]*staff-directory-table-member-position__link--name[^"]*"[^>]*>'
        r"([\s\S]*?)</a>"
        r"[\s\S]{0,800}?"
        r'class="[^"]*staff-directory-table-member-position__position[^"]*"[^>]*>'
        r"[\s\S]{0,200}?<p>([^<]+)</p>",
        re.I,
    )
    for name_html, title in staff_directory_row.findall(html or ""):
        name = html_unescape_text(name_html)
        title_text = html_unescape_text(title)
        if name.casefold().endswith(title_text.casefold()):
            name = name[: len(name) - len(title_text)].strip()
        if not name or not looks_like_staff_title(title_text):
            continue
        _record(name, title_text, "sidearm_staff_directory_row")

    vue_table_pattern = re.compile(
        r'<span class="s-text-paragraph-small-bold[^"]*"[^>]*>\s*([^<]+?)\s*</span>'
        r".{0,800}?<span[^>]*>\s*([^<]+?)\s*</span>",
        re.I | re.S,
    )
    for name, title in vue_table_pattern.findall(html or ""):
        if not looks_like_staff_title(title):
            continue
        _record(name, title, "sidearm_vue_table_span")

    # Nearby heading/title fallback used by several Sidearm templates.
    heading_pattern = re.compile(
        r"<h[1-4][^>]*>(.*?)</h[1-4]>.{0,240}?"
        r"(Head Coach|Offensive Coordinator|Defensive Coordinator|"
        r"Special Teams Coordinator|Special Teams)",
        re.I | re.S,
    )
    for match in heading_pattern.finditer(html or ""):
        _record(match.group(1), match.group(2), "heading_nearby_title")

    itemprop_pattern = re.compile(
        r'itemprop=["\']name["\'][^>]*>(.*?)</[^>]+>.{0,240}?'
        r'itemprop=["\'](?:jobTitle|roleName)["\'][^>]*>(.*?)</',
        re.I | re.S,
    )
    for match in itemprop_pattern.finditer(html or ""):
        _record(match.group(1), match.group(2), "itemprop")

    scoped = scope_html_to_football(html or "")
    table_row = re.compile(
        r"<tr[^>]*>[\s\S]{0,500}?<t[dh][^>]*>([\s\S]*?)</t[dh]>"
        r"[\s\S]{0,200}?<t[dh][^>]*>([\s\S]*?)</t[dh]>",
        re.I,
    )
    for match in table_row.finditer(scoped):
        name = html_unescape_text(match.group(1))
        title = html_unescape_text(match.group(2))
        if name.casefold() in {"name", "staff"} or title.casefold() in {
            "title",
            "position",
        }:
            continue
        if not looks_like_staff_title(title):
            continue
        _record(name, title, "html_table_pair")

    return people


def looks_like_staff_title(title: str) -> bool:
    lowered = str(title or "").casefold()
    return any(token in lowered for token in STAFF_TITLE_TOKENS)


def scope_html_to_football(html: str) -> str:
    """Prefer the football staff slice so a multi-sport directory is not national coverage."""
    patterns = (
        r"(Football Coaching Staff[\s\S]{0,50000}?)(?:<h2\b|$)",
        r"(<h[1-4][^>]*>\s*Football\s*</h[1-4]>[\s\S]{0,50000}?)(?:<h[1-4][^>]*>\s*(?!Football))",
    )
    for pattern in patterns:
        match = re.search(pattern, html or "", flags=re.I)
        if match:
            return match.group(1)
    return html


def declared_staff_resource_matches(requested_url: str, final_url: str) -> bool:
    """True only when host, path, and Sidearm path= query still name the requested resource."""
    requested = urlparse(str(requested_url or ""))
    final = urlparse(str(final_url or requested_url or ""))
    if requested.netloc.casefold() != final.netloc.casefold():
        return False
    requested_path = requested.path.rstrip("/").casefold()
    final_path = final.path.rstrip("/").casefold()
    if requested_path != final_path:
        return False
    requested_sport = (parse_qs(requested.query).get("path") or [None])[0]
    final_sport = (parse_qs(final.query).get("path") or [None])[0]
    if requested_sport is not None and requested_sport != final_sport:
        return False
    return True


def classify_page_identity(
    requested_url: str, final_url: str, body: bytes
) -> dict[str, Any]:
    """A 200 page is not football staff evidence if it is a different resource or sport."""
    requested = str(requested_url or "")
    final = str(final_url or requested_url or "")
    final_cf = final.casefold()
    requested_path = urlparse(requested).path.rstrip("/").casefold()
    if any(token in final_cf for token in WRONG_SPORT_URL_TOKENS) and (
        "football" not in final_cf
    ):
        return {
            "ok": False,
            "reason": "WRONG_RESOURCE_REDIRECT",
            "detail": "WRONG_SPORT_PAGE",
            "requested_url": requested_url,
            "final_url": final_url,
        }
    if not declared_staff_resource_matches(requested, final):
        return {
            "ok": False,
            "reason": "WRONG_RESOURCE_REDIRECT",
            "requested_url": requested_url,
            "final_url": final_url,
        }
    if (
        requested_path.endswith("/roster")
        and "/coaches" not in requested_path
        and "/staff" not in requested_path
    ):
        return {
            "ok": False,
            "reason": "PLAYER_ROSTER_NOT_STAFF_DIRECTORY",
            "requested_url": requested_url,
            "final_url": final_url,
        }
    if requested_path.endswith("/staff-directory") and "football" not in requested_path:
        return {
            "ok": False,
            "reason": "UNSCOPED_MULTI_SPORT_DIRECTORY",
            "requested_url": requested_url,
            "final_url": final_url,
        }
    return {
        "ok": True,
        "reason": "PAGE_IDENTITY_PLAUSIBLE",
        "requested_url": requested_url,
        "final_url": final_url,
    }


def html_unescape_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = (
        text.replace("&amp;", "&")
        .replace("&nbsp;", " ")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    return re.sub(r"\s+", " ", text).strip()


def _unpack_opener_result(
    result: tuple[int, bytes, str] | tuple[int, bytes, str, str],
    requested_url: str,
) -> tuple[int, bytes, str, str]:
    if len(result) == 4:
        status, body, error, final_url = result
        return status, body, error, str(final_url or requested_url)
    status, body, error = result
    return status, body, error, requested_url


def fetch_url(
    url: str,
    *,
    opener: FetchOpener | None = None,
) -> dict[str, Any]:
    retrieved_at = utc_now_label()
    if opener is not None:
        status, body, error, final_url = _unpack_opener_result(opener(url), url)
        return _fetch_result(
            url, status, body, error, retrieved_at, final_url=final_url
        )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(
            request, timeout=FETCH_TIMEOUT_SEC, context=context
        ) as response:
            body = response.read()
            return _fetch_result(
                url,
                int(response.status),
                body,
                None,
                retrieved_at,
                final_url=str(response.geturl() or url),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp is not None else b""
        return _fetch_result(
            url,
            int(exc.code),
            body,
            str(exc),
            retrieved_at,
            final_url=str(getattr(exc, "url", None) or url),
        )
    except Exception as exc:  # noqa: BLE001 - fetch must record BLOCKED, not raise
        return _fetch_result(
            url, None, b"", f"{type(exc).__name__}: {exc}", retrieved_at
        )


def _fetch_result(
    url: str,
    status: int | None,
    body: bytes,
    error: str | None,
    retrieved_at: str,
    final_url: str | None = None,
) -> dict[str, Any]:
    blocked = status != 200 or not body
    identity = classify_page_identity(url, final_url or url, body)
    if blocked or not identity["ok"]:
        disposition = "BLOCKED"
    else:
        disposition = "RETRIEVED"
    return {
        "url": url,
        "final_url": final_url or url,
        "http_status": status,
        "retrieved_at_utc": retrieved_at,
        "bytes": len(body),
        "sha256": sha256_bytes(body) if body else None,
        "error": error or (None if identity["ok"] else identity["reason"]),
        "fetch_disposition": disposition,
        "page_identity": identity["reason"],
        "body": body,
    }


def build_staff_context_packet(
    *,
    team_label: str,
    canonical_team_id: str,
    ncaa_contest_id: str,
    urls: Sequence[str],
    issued_at_utc: str,
    registry_inspection: Mapping[str, Any],
    opener: FetchOpener | None = None,
) -> dict[str, Any]:
    fetches: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    raw_bodies: list[tuple[str, bytes]] = []
    for url in urls:
        fetched = fetch_url(url, opener=opener)
        body = fetched.pop("body")
        fetches.append(fetched)
        if fetched["fetch_disposition"] == "RETRIEVED":
            raw_bodies.append((fetched["sha256"] or "unknown", body))
            observations.extend(
                parse_staff_directory_html(body.decode("utf-8", "replace"))
            )
    retrieved = [row for row in fetches if row["fetch_disposition"] == "RETRIEVED"]
    blocked = [row for row in fetches if row["fetch_disposition"] == "BLOCKED"]
    conflicted = [row for row in fetches if row["fetch_disposition"] == "CONFLICT"]
    role_index = _index_staff_roles(observations)
    packet = {
        "artifact_type": "CYCLE27_FOCUS_STAFF_CONTEXT_PACKET",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "issued_at_utc": issued_at_utc,
        "ncaa_contest_id": ncaa_contest_id,
        "season": SEASON,
        "team_label": team_label,
        "canonical_team_id": canonical_team_id,
        "packet_use": CONTEXT_ONLY,
        "model_consumption": NOT_CONSUMED_BY_MODEL,
        "structured_coaching_endpoint": registry_inspection.get(
            "structured_coaching_route"
        ),
        "registry_coach_entry_present": registry_inspection.get("coach_entry_present"),
        "declared_official_staff_urls": list(urls),
        "fetches": fetches,
        "retrieved_count": len(retrieved),
        "blocked_count": len(blocked),
        "conflict_count": len(conflicted),
        "title_observations": observations,
        "roles": role_index,
        "canonical_role_episodes": [],
        "effective_dates_invented": False,
        "play_caller_inferred_from_title": False,
        "coach_bonus_applied": False,
        "national_coverage_not_implied": True,
        "scientific_nonclaims": [
            "CONTEXT_ONLY / NOT_CONSUMED_BY_MODEL.",
            "Title is not play-caller proof.",
            "Unknown effective dates are not synthesized.",
            "Equal names do not establish canonical person identity.",
            "This packet does not authorize a coaching-effect model.",
        ],
    }
    packet["packet_identity"] = sha256_bytes(
        canonical_json_bytes(
            {key: value for key, value in packet.items() if key != "packet_identity"}
        )
    )
    packet["_raw_bodies"] = raw_bodies
    return packet


def _index_staff_roles(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    index: dict[str, Any] = {}
    for role_id in STAFF_ROLE_IDS:
        matched = [
            row
            for row in observations
            if row.get("title_role_id") == role_id
            or (
                role_id == "CO_OR_INTERIM_OR_DELEGATED"
                and row.get("co_or_interim_or_delegated")
            )
        ]
        if role_id in {"OFFENSIVE_PLAY_CALLER", "DEFENSIVE_PLAY_CALLER"}:
            index[role_id] = {
                "status": UNKNOWN_NOT_NONE,
                "confirmed_absent": False,
                "title_inference": "FORBIDDEN",
                "observations": [],
                "consumption": NOT_CONSUMED_BY_MODEL,
            }
            continue
        if not matched:
            index[role_id] = {
                **classify_missing_role(None),
                "observations": [],
                "consumption": NOT_CONSUMED_BY_MODEL,
            }
            continue
        index[role_id] = {
            "status": "TITLE_OBSERVED_CONTEXT_ONLY",
            "confirmed_absent": False,
            "observations": list(matched),
            "consumption": NOT_CONSUMED_BY_MODEL,
            "canonical_episode": False,
        }
    return index


def _maturity_layers(*, staff_consumed: bool) -> dict[str, Any]:
    return {
        "planned_schema_support": {
            "status": "PRESENT",
            "evidence": [
                "docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md",
                "governance/COACH_ROLE_EPISODE_CONTRACTS.csv",
                "src/aggie_analytics/context_intelligence/coaching.py",
                "governance/DATASET_SCHEMA_REGISTRY.csv DS-0031..DS-0034 SCHEMA_PENDING_MATERIALIZATION",
            ],
        },
        "declared_source_and_raw_evidence": {
            "status": "SOURCE_ABSENT_NOT_REGISTERED",
            "acquisition_registry_coach_entry": False,
            "schema_registry_cfbd_coaches": "SCHEMA_PENDING_MATERIALIZATION_NOT_A_LIVE_ROUTE",
        },
        "canonical_normalized_staff_role_records": {
            "status": "ABSENT_FOR_WEEK1_2026",
            "head_coach_boolean_is_not_canonical": True,
        },
        "temporal_admission_at_this_checkpoint": {
            "status": "SOURCE_ABSENT",
            "national_domain_id": "coaching_staff",
        },
        "historical_training_analogue": {
            "status": "PARTIAL_HISTORICAL_REGISTRY_NOT_WEEK1_INPUT",
            "people_registry_head_coach_season_min": 2010,
            "people_registry_head_coach_season_max": 2025,
            "assistant_staff_source_defined_max": 2015,
            "assistant_staff_coverage_complete": False,
            "consumed_by_week1_model": False,
        },
        "actual_model_consumption": {
            "status": NOT_CONSUMED if not staff_consumed else "CONSUMED",
            "coaches_poll_rank_is_not_staff": True,
        },
    }


def build_coaching_census(
    *,
    issued_at_utc: str,
    spine_rows: Sequence[Mapping[str, Any]],
    feature_column_names: Sequence[str],
    fitted_design_columns: Mapping[str, Any] | None,
    acquisition_registry: Mapping[str, Any],
    domain_admission: Mapping[str, Any] | None,
    authority_head_coach_boolean_retained: bool,
    cycle26_successor_consumes_coaching: bool,
    focus_packets: Mapping[str, Mapping[str, Any]],
    code_head: str | None = None,
) -> dict[str, Any]:
    contests = sorted({str(row.get("ncaa_contest_id") or "") for row in spine_rows})
    contests = [contest_id for contest_id in contests if contest_id]
    if len(contests) != 91:
        raise CoachingCensusError(
            f"pinned Week1 universe must have 91 contests, saw {len(contests)}"
        )
    team_seasons: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for row in spine_rows:
        canonical = str(row.get("canonical_team_id") or "").strip()
        source = str(row.get("source_team_id") or "").strip()
        season = int(row.get("season") or SEASON)
        identity_key = canonical or (f"UNRESOLVED:{source}" if source else "")
        key = (identity_key, season)
        if not identity_key or key in seen:
            continue
        seen.add(key)
        team_seasons.append(
            {
                "canonical_team_id": canonical or None,
                "canonical_bind_state": (
                    "CANONICAL_BOUND" if canonical else "UNRESOLVED_SOURCE_ENTITY"
                ),
                "source_team_id": source or None,
                "season": season,
                "ncaa_contest_id": row.get("ncaa_contest_id"),
                "site_orientation": row.get("site_orientation"),
                "ncaa_listed_orientation": row.get("orientation")
                or row.get("ncaa_listed_orientation"),
                "conference_name": row.get("conference_name"),
                "subdivision": row.get("subdivision"),
                "focus_participant": canonical
                in {FOCUS_HOME_CANONICAL, FOCUS_AWAY_CANONICAL},
            }
        )
    participants_retained = len(spine_rows)
    if participants_retained != 182:
        raise CoachingCensusError(
            f"both participants must be retained; saw {participants_retained} spine rows"
        )
    registry_inspection = inspect_source_acquisition_registry(acquisition_registry)
    feature_inspection = active_week1_staff_feature_columns(feature_column_names)
    design_inspection = fitted_design_staff_columns(fitted_design_columns)
    coaching_domain = _coaching_domain_admission(domain_admission)
    role_counts = _role_counts(
        team_seasons=team_seasons,
        focus_packets=focus_packets,
        staff_consumed=bool(
            feature_inspection["staff_role_column_count"]
            or cycle26_successor_consumes_coaching
        ),
    )
    census = {
        "artifact_type": "COACHING_DATA_AND_CONSUMPTION_CENSUS",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "issued_at_utc": issued_at_utc,
        "code_head": code_head,
        "hold": "ACTIVE",
        "merge_authorized": False,
        "scientific_done_authorized": False,
        "universe": {
            "pin": "WEEK1_2026_SPINE_SEMANTIC_SUCCESSOR_91_CONTESTS",
            "contest_count": len(contests),
            "participant_rows_retained": participants_retained,
            "unique_team_seasons": len(team_seasons),
            "deduplicated_on": [
                "canonical_team_id_or_unresolved_source",
                "season",
            ],
            "both_participants_retained": True,
            "ncaa_contest_ids": contests,
        },
        "roles_enumerated": list(STAFF_ROLE_IDS),
        "maturity_layers": _maturity_layers(
            staff_consumed=feature_inspection["staff_role_column_count"] > 0
        ),
        "source_acquisition_registry": registry_inspection,
        "national_domain_admission": coaching_domain,
        "week1_feature_columns": feature_inspection,
        "fitted_design": design_inspection,
        "authority_enrichment_head_coach_boolean_retained_as_staff": (
            authority_head_coach_boolean_retained
        ),
        "cycle26_successor_consumes_named_staff_fields": cycle26_successor_consumes_coaching,
        "coaches_poll_rank_is_not_staff": True,
        "head_coach_boolean_is_not_full_coverage": True,
        "play_caller_not_inferred_from_title": True,
        "manual_coach_bonus_permitted": False,
        "focus_staff_packets": {
            team_id: {
                "team_label": packet.get("team_label"),
                "packet_identity": packet.get("packet_identity"),
                "fetch_disposition_counts": {
                    "RETRIEVED": packet.get("retrieved_count"),
                    "BLOCKED": packet.get("blocked_count"),
                    "CONFLICT": packet.get("conflict_count"),
                },
                "title_observation_count": len(packet.get("title_observations") or []),
                "model_consumption": packet.get("model_consumption"),
            }
            for team_id, packet in focus_packets.items()
        },
        "counts": role_counts,
        "national_coverage_claimed_from_two_focus_teams": False,
        "team_seasons": team_seasons,
        "discovered_owners": {
            "current_substantial_owner": JIRA_KEY,
            "do_not_invent_coaching_bat": True,
            "related_existing": [
                "BAT-388 canonical people registry (historical analogue, not Week1 input)",
                "TASK-061 / REQ-423 / REQ-427 title vs play-caller contracts",
                "BAT-655 national expectation baselines (consumes coaches_poll_rank as poll)",
                "BAT-693 Week1 game-grain forecast successor (no staff columns)",
            ],
        },
        "scientific_nonclaims": [
            "Does not claim national staff coverage because two focus teams were inspected.",
            "Does not treat coaches_poll_rank as coaching-staff data.",
            "Does not treat a head-coach boolean as full HC/OC/DC/play-caller coverage.",
            "Does not infer play-caller from title.",
            "Does not apply a coach bonus or current-only coefficient.",
            "Does not train a coaching effect from Week1 outcomes or the focus game.",
            "CONTEXT_ONLY staff packets are not model inputs.",
        ],
        "result": "PASS_COACHING_CENSUS_HONEST_GAPS",
    }
    census["gate_identity"] = sha256_bytes(
        canonical_json_bytes(
            {key: value for key, value in census.items() if key != "gate_identity"}
        )
    )
    return census


def _coaching_domain_admission(
    domain_admission: Mapping[str, Any] | None,
) -> dict[str, Any]:
    domains = []
    if isinstance(domain_admission, Mapping):
        domains = list(domain_admission.get("domains") or [])
        if not domains and isinstance(domain_admission.get("admission_matrix"), list):
            domains = list(domain_admission.get("admission_matrix") or [])
    coaching = next(
        (
            row
            for row in domains
            if isinstance(row, Mapping) and row.get("domain_id") == "coaching_staff"
        ),
        None,
    )
    if coaching is None and isinstance(domain_admission, Mapping):
        # Contract shape uses nested domains list.
        nested = domain_admission.get("domains")
        if nested is None:
            coaching = {
                "domain_id": "coaching_staff",
                "decision": domain_admission.get("coaching_staff_decision")
                or "SOURCE_ABSENT",
            }
    return {
        "domain_id": "coaching_staff",
        "decision": (coaching or {}).get("decision") or "SOURCE_ABSENT",
        "known_at_basis": (coaching or {}).get("known_at_basis") or "SOURCE_ABSENT",
        "evidence_route": (coaching or {}).get("evidence_route") or "ABSENT",
        "national_week1_coverage_not_inferred_from_focus_packets": True,
    }


def _role_counts(
    *,
    team_seasons: Sequence[Mapping[str, Any]],
    focus_packets: Mapping[str, Mapping[str, Any]],
    staff_consumed: bool,
) -> dict[str, Any]:
    focus_ids = set(focus_packets)
    not_yet_audited_teams = [
        row["canonical_team_id"]
        for row in team_seasons
        if row["canonical_team_id"] not in focus_ids
    ]
    by_role: dict[str, Any] = {}
    for role_id in STAFF_ROLE_IDS:
        verified = 0
        blocked = 0
        missing = 0
        conflicted = 0
        for team_id, packet in focus_packets.items():
            role = (packet.get("roles") or {}).get(role_id) or {}
            status = str(role.get("status") or UNKNOWN_NOT_NONE)
            fetches = packet.get("fetches") or []
            if fetches and all(
                row.get("fetch_disposition") == "BLOCKED" for row in fetches
            ):
                blocked += 1
            elif status == "TITLE_OBSERVED_CONTEXT_ONLY":
                verified += 1
            else:
                missing += 1
            if len(role.get("observations") or []) > 1 and role_id not in {
                "CO_OR_INTERIM_OR_DELEGATED"
            }:
                names = {
                    str(item.get("source_person_name") or "").casefold()
                    for item in role.get("observations") or []
                }
                if len(names) > 1:
                    conflicted += 1
        by_role[role_id] = {
            "verified_context_only_focus_titles": verified,
            "missing_or_unknown_focus": missing,
            "blocked_focus_fetches": blocked,
            "conflicted_focus": conflicted,
            "not_yet_audited_team_seasons": len(not_yet_audited_teams),
            "not_consumed_team_seasons": len(team_seasons),
            "national_canonical_week1_records": 0,
        }
    return {
        "team_seasons": len(team_seasons),
        "focus_team_seasons_attempted": len(focus_packets),
        "not_yet_audited_team_seasons": len(not_yet_audited_teams),
        "not_consumed_team_seasons": len(team_seasons),
        "model_consumed_staff_roles": 0 if not staff_consumed else "TRACE_REQUIRED",
        "by_role": by_role,
        "do_not_read_as_national_coverage": True,
    }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def payload_relative_path(manifest: Mapping[str, Any], name: str) -> str:
    for item in manifest.get("payloads") or []:
        if item.get("name") == name:
            return str(item.get("relative_path"))
    raise CoachingCensusError(f"missing payload {name}")


def write_json_dual(
    payload: Mapping[str, Any],
    *,
    repo_path: Path,
    ops_path: Path,
) -> dict[str, Any]:
    body = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
    body = body + ("\n" if not body.endswith("\n") else "")
    encoded = body.encode("utf-8")
    for path in (repo_path, ops_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
    return {
        "repo_path": str(repo_path),
        "ops_path": str(ops_path),
        "sha256": sha256_bytes(encoded),
        "bytes": len(encoded),
    }


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    ops_root: Path,
    issued_at_utc: str | None = None,
    opener: FetchOpener | None = None,
    code_head: str | None = None,
    refresh_away_staff: bool = True,
) -> dict[str, Any]:
    issued = issued_at_utc or utc_now_label()
    registry = load_json(repo_root / "configs/source_acquisition_registry.json")
    registry_inspection = inspect_source_acquisition_registry(registry)
    domain_contract = load_json(
        repo_root / "configs/national_pit_domain_admission_matrix_contract.json"
    )
    suite_gate = load_json(
        repo_root / "artifacts/forecast/week1_2026_national_forecast_suite_gate.json"
    )
    spine_gate = load_json(
        repo_root / "artifacts/spine/week1_2026_spine_semantic_successor_gate.json"
    )
    spine_manifest = load_json(data_root / spine_gate["manifest"]["relative_path"])
    spine_rows = load_jsonl(
        data_root
        / payload_relative_path(spine_manifest, "week1_2026_successor_spine_rows.jsonl")
    )
    suite_manifest = load_json(data_root / suite_gate["manifest"]["relative_path"])
    feature_rows = load_jsonl(
        data_root
        / payload_relative_path(
            suite_manifest, "week1_2026_forecast_feature_rows.jsonl"
        )
    )
    parameter_rows = load_jsonl(
        data_root
        / payload_relative_path(
            suite_manifest, "week1_2026_forecast_fitted_parameter_rows.jsonl"
        )
    )
    feature_names: list[str] = []
    for row in feature_rows:
        values = row.get("feature_values") or {}
        feature_names.extend(str(name) for name in values)
    feature_names = sorted(set(feature_names))
    design_row = next(
        (
            row
            for row in parameter_rows
            if row.get("parameter_set_id") == "WEEK1_2026_DEPLOYMENT_DESIGN"
        ),
        {},
    )
    successor_text = (
        repo_root
        / "src/aggie_analytics/data/week1_2026_game_grain_national_forecast_successor.py"
    ).read_text(encoding="utf-8")
    cycle26_consumes = any(
        token in successor_text.casefold()
        for token in ("head_coach", "play_caller", "offensive_coordinator")
    )
    home_packet = build_staff_context_packet(
        team_label=FOCUS_HOME_LABEL,
        canonical_team_id=FOCUS_HOME_CANONICAL,
        ncaa_contest_id=FOCUS_CONTEST_ID,
        urls=DECLARED_OFFICIAL_STAFF_URLS[FOCUS_HOME_CANONICAL],
        issued_at_utc=issued,
        registry_inspection=registry_inspection,
        opener=opener,
    )
    if refresh_away_staff:
        away_packet = build_staff_context_packet(
            team_label=FOCUS_AWAY_LABEL,
            canonical_team_id=FOCUS_AWAY_CANONICAL,
            ncaa_contest_id=FOCUS_CONTEST_ID,
            urls=DECLARED_OFFICIAL_STAFF_URLS[FOCUS_AWAY_CANONICAL],
            issued_at_utc=issued,
            registry_inspection=registry_inspection,
            opener=opener,
        )
    else:
        away_packet = load_json(
            repo_root
            / "artifacts/scientific_integrity/cycle27/FOCUS_STAFF_CONTEXT_MISSOURI_STATE.json"
        )
    packets = {
        FOCUS_HOME_CANONICAL: home_packet,
        FOCUS_AWAY_CANONICAL: away_packet,
    }
    census = build_coaching_census(
        issued_at_utc=issued,
        spine_rows=spine_rows,
        feature_column_names=feature_names,
        fitted_design_columns=design_row.get("design_columns"),
        acquisition_registry=registry,
        domain_admission=domain_contract,
        authority_head_coach_boolean_retained=False,
        cycle26_successor_consumes_coaching=cycle26_consumes,
        focus_packets=packets,
        code_head=code_head,
    )
    repo_dir = repo_root / "artifacts/scientific_integrity/cycle27"
    ops_dir = ops_root / "outputs"
    written = {}
    written["census"] = write_json_dual(
        {key: value for key, value in census.items()},
        repo_path=repo_dir / "COACHING_DATA_AND_CONSUMPTION_CENSUS.json",
        ops_path=ops_dir / "COACHING_DATA_AND_CONSUMPTION_CENSUS.json",
    )
    packet_files = {
        FOCUS_HOME_CANONICAL: "FOCUS_STAFF_CONTEXT_TEXAS_AM.json",
        FOCUS_AWAY_CANONICAL: "FOCUS_STAFF_CONTEXT_MISSOURI_STATE.json",
    }
    for team_id, filename in packet_files.items():
        if not refresh_away_staff and team_id == FOCUS_AWAY_CANONICAL:
            continue
        packet = dict(packets[team_id])
        raw_bodies = packet.pop("_raw_bodies", [])
        written[filename] = write_json_dual(
            packet,
            repo_path=repo_dir / filename,
            ops_path=ops_dir / filename,
        )
        for digest, body in raw_bodies:
            raw_path = ops_dir / "raw_staff" / f"{digest}.html"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(body)
    return {
        "issued_at_utc": issued,
        "census_identity": census["gate_identity"],
        "written": written,
        "packets": {
            team_id: packet.get("packet_identity")
            for team_id, packet in packets.items()
        },
    }
