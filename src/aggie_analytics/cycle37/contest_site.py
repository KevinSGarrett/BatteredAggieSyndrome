"""Contest site, neutral status, venue support and travel for one contest.

R37-09 successor to ``cycle36.venue_vintage``'s labelling, which called a
contest venue ``VENUE_INDEPENDENTLY_SUPPORTED`` whenever the provider's own
venue id resolved in the provider's own venue index (MF36-14). Two readings
from one publisher are one reading. This module keeps four things apart:

* **designation** -- which side the game feed calls home and away, which is
  administrative and says nothing about where the game was played;
* **neutral status** -- ``True`` / ``False`` from the feed, and *unknown*
  when the feed has no value; unknown never becomes ``False``;
* **venue support** -- a provider venue-index match is labelled exactly
  that, and a venue counts as independently confirmed only when a second
  publisher's contest record agrees on the date and the site city;
* **travel** -- two great-circle legs from each side's reference origin to
  the venue, each with its own time-zone shift, and ``None`` rather than
  zero when anything is missing.

The second publisher used here is a team-season schedule table
(``{{CFB schedule entry}}``) from a cached encyclopedia revision. It is a
secondary source retrieved long after the fact: it confirms location
independently of the game feed, it is not official, and it is not
point-in-time. Every label says which of those it is.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

SITE_VERSION = "BAS-CONTEST-SITE-v37.2"
#: The v37.1 comparator, named so a comparison can say which one it ran.
PRIOR_SITE_VERSION = "BAS-CONTEST-SITE-v37.1"
PREDECESSOR_SITE_VERSION = "BAS-VENUE-VINTAGE-v36.1"

EARTH_RADIUS_KM = 6371.0088
KM_PER_MILE = 1.609344

NEUTRAL_TRUE = "SOURCE_DESIGNATED_NEUTRAL"
NEUTRAL_FALSE = "SOURCE_DESIGNATED_NOT_NEUTRAL"
NEUTRAL_UNKNOWN = "NEUTRAL_STATUS_UNKNOWN"

VENUE_ABSENT = "VENUE_ID_ABSENT_IN_FEED"
VENUE_UNRESOLVED = "VENUE_ID_NOT_IN_PROVIDER_INDEX"
VENUE_PROVIDER_ONLY = "PROVIDER_VENUE_INDEX_MATCH_NOT_INDEPENDENT"
VENUE_CONFIRMED = "INDEPENDENTLY_CONFIRMED_BY_SECONDARY_SOURCE"
VENUE_CONFLICT = "SECONDARY_SOURCE_DISAGREES_ON_SITE"

CONFIRM_NO_PAGE = "NO_SECONDARY_TEAM_SEASON_PAGE"
CONFIRM_NO_ENTRY = "NO_SECONDARY_ENTRY_ON_THE_CONTEST_DATE"
CONFIRM_AMBIGUOUS = "MORE_THAN_ONE_SECONDARY_ENTRY_ON_THE_CONTEST_DATE"
CONFIRM_DATE_ONLY = "DATE_CONFIRMED_SITE_NOT_COMPARABLE"
CONFIRM_SITE = "DATE_AND_SITE_CITY_CONFIRMED"
CONFIRM_SITE_CONFLICT = "DATE_CONFIRMED_SITE_CITY_DISAGREES"

MONTHS = {name: number for number, name in enumerate(
    ("january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"), start=1)}

#: US state and province abbreviations the schedule template uses for
#: ``site_cityst``, mapped to the two-letter code the venue index uses.
STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC", "puerto rico": "PR",
}


# ------------------------------------------------------------------ markup
def strip_markup(value: str) -> str:
    """Wiki link/template/HTML markup removed, display text kept."""

    text = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", value, flags=re.S | re.I)
    # Display wrappers carry the value itself ({{dow tooltip|December 30, 2009}}
    # is the date); keep their first argument instead of dropping the value.
    text = re.sub(r"\{\{\s*(?:dow tooltip|nowrap|small|nobr)\s*\|([^{}|]*)[^{}]*\}\}", r"\1", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


MONTH_DAY = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\b",
    re.I,
)


def date_field_text(raw: str) -> str:
    """The first month-and-day in a date field, whatever wraps it.

    Dates arrive bare, linked, or inside display templates such as
    ``{{dow tooltip|December 30, 2009}}`` and ``{{tooltip|December 14|Tuesday}}``.
    Stripping templates drops the date with them, so the field is searched
    for the date itself; a citation's own date is removed first.
    """

    without_refs = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>|<ref.*", "", raw, flags=re.S | re.I)
    match = MONTH_DAY.search(without_refs)
    return f"{match.group(1)} {match.group(2)}" if match else strip_markup(without_refs)


def parse_schedule_entries(wikitext: str) -> list[dict[str, Any]]:
    """Every ``{{CFB schedule entry}}`` with its raw and cleaned fields."""

    entries = []
    # Entries are split at each entry's own start, not at a closing brace:
    # some tables close an entry with "|}}", and a closing-brace match then
    # runs on into the next entry and merges the two.
    starts = [m.start() for m in re.finditer(r"\{\{\s*CFB schedule entry", wikitext, flags=re.I)]
    for start, end in zip(starts, starts[1:] + [len(wikitext)]):
        fields: dict[str, str] = {}
        for line in wikitext[start:end].split("\n")[1:]:
            line = line.strip()
            if re.match(r"^\|?\s*\}\}", line):
                break
            if not line.startswith("|") or "=" not in line:
                continue
            key, _, value = line[1:].partition("=")
            fields[key.strip().lower()] = value.strip()
        entries.append({
            "date_text": date_field_text(fields.get("date", "")),
            "away": fields.get("away", "").strip().lower() in ("y", "yes"),
            "neutral": fields.get("neutral", "").strip().lower() in ("y", "yes"),
            "opponent": strip_markup(fields.get("opponent", "")),
            "site_stadium": strip_markup(fields.get("site_stadium", "")),
            "site_cityst": strip_markup(fields.get("site_cityst", "")),
        })
    return entries


def entry_date(entry: Mapping[str, Any], season: int) -> date | None:
    """Month-day text plus season, rolling January into the next year."""

    match = re.match(r"([A-Za-z]+)\s+(\d{1,2})", entry.get("date_text") or "")
    if not match:
        return None
    month = MONTHS.get(match.group(1).casefold())
    if month is None:
        return None
    year = season + 1 if month <= 6 else season
    try:
        return date(year, month, int(match.group(2)))
    except ValueError:
        return None


def city_state(entry_site: str) -> tuple[str, str | None]:
    """``"Lincoln, NE"``, ``"Lincoln, Nebraska"`` or ``"Columbia SC"`` -> (folded city, state code)."""

    city, comma, state = entry_site.partition(",")
    if not comma:
        match = re.match(r"^(.*\S)\s+([A-Z]{2})$", entry_site.strip())
        if match:
            city, state = match.group(1), match.group(2)
        else:
            # v37.2: "DeLand Florida" -- a full state name with no comma.
            for name in sorted(STATE_NAMES, key=len, reverse=True):
                if entry_site.strip().casefold().endswith(" " + name):
                    city, state = entry_site.strip()[: -len(name)], name
                    break
    state = state.strip()
    code = state.upper() if len(state) == 2 else STATE_NAMES.get(state.casefold())
    return fold(city), code


#: v37.2. City spellings that name the same place: a borough and its city,
#: an article, "Saint" and "St.". Declared, not inferred.
CITY_ALIASES = {
    "manhattan": "new york", "new york city": "new york", "the bronx": "bronx", "saint": "st",
}
#: Words a stadium name shares with unrelated stadiums. A name-token match
#: needs at least one word outside this list.
GENERIC_STADIUM_WORDS = frozenset({
    "stadium", "field", "memorial", "municipal", "park", "bowl", "dome", "the", "at", "of", "and", "university",
    "college", "alumni", "coliseum", "center", "centre", "arena", "complex", "sports", "athletic", "athletics",
    "football", "war", "veterans", "community", "city", "county", "high", "school",
})


def city_alias(folded_city: str) -> str:
    words = [CITY_ALIASES.get(w, w) for w in folded_city.split()]
    text = " ".join(words)
    return CITY_ALIASES.get(text, text).removeprefix("the ").strip()


def stadium_tokens_match(a: str, b: str) -> bool:
    """v37.2. One stadium name's words are all in the other's, with a
    non-generic word among them ("Coffey Field" in "Jack Coffey Field",
    "Lawrence A. Wien Stadium" in "Robert K. Kraft Field at Lawrence A. Wien
    Stadium"), or one is the other's initialism ("UB Stadium", "University
    at Buffalo Stadium"). Callers must also require the same state: "Aggie
    Stadium" in North Carolina is not "Aggie Memorial Stadium" in New Mexico.
    """

    ta, tb = set(stadium_key(a).split()), set(stadium_key(b).split())
    if not ta or not tb:
        return False
    small, large = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if small <= large and small - GENERIC_STADIUM_WORDS:
        return True

    def initialism(words: list[str]) -> str:
        return "".join(w[0] for w in words if w not in {"at", "of", "the", "and", "stadium", "field"})

    wa, wb = stadium_key(a).split(), stadium_key(b).split()
    for short, long_ in ((wa, wb), (wb, wa)):
        head = [w for w in short if w not in {"stadium", "field"}]
        if len(head) == 1 and len(head[0]) >= 2 and head[0] == initialism(long_):
            return True
    return False


def stadium_key(name: str) -> str:
    """A stadium name folded for exact comparison: parenthetical qualifiers
    and punctuation removed, nothing else. ``Memorial Stadium (Lincoln)`` and
    ``Memorial Stadium`` compare equal; different stadiums do not become
    equal by dropping words."""

    return fold(re.sub(r"\([^)]*\)", " ", name or ""))


# ------------------------------------------------------------- confirmation
def local_date(start_utc: str | None, tz_name: str | None) -> tuple[date | None, str]:
    """The contest's calendar date at the venue, and how it was read.

    Without a venue time zone the UTC date is used and said to be used; the
    one-day tolerance in ``confirm_contest`` then covers a late western
    kickoff. No zone is guessed.
    """

    instant = parse_instant(start_utc)
    if instant is None:
        return None, "NO_START_INSTANT"
    zone = zone_or_none(tz_name)
    if zone is None:
        return instant.astimezone(timezone.utc).date(), "UTC_DATE_NO_VENUE_TIMEZONE"
    return instant.astimezone(zone).date(), "VENUE_LOCAL_DATE"


def confirm_contest(
    *, season: int, start_utc: str | None, venue: Mapping[str, Any] | None,
    entries: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Compare one team-season page's entries with the feed's date and venue.

    The feed's instant is read in the venue's own time zone, because a late
    kickoff in the west is the next day in UTC. An entry one day either side
    is accepted only when it is the only candidate, and that tolerance is
    recorded.
    """

    if entries is None:
        return {"state": CONFIRM_NO_PAGE}
    target, basis = local_date(start_utc, (venue or {}).get("timezone"))
    if target is None:
        return {"state": CONFIRM_NO_ENTRY, "detail": "the feed has no usable start date"}
    exact = [e for e in entries if entry_date(e, season) == target]
    tolerance = 0
    if not exact:
        exact = [e for e in entries
                 if (d := entry_date(e, season)) is not None and abs((d - target).days) == 1]
        tolerance = 1
    if not exact:
        return {"state": CONFIRM_NO_ENTRY, "feed_local_date": target.isoformat()}
    if len(exact) > 1:
        return {"state": CONFIRM_AMBIGUOUS, "feed_local_date": target.isoformat(), "candidates": len(exact)}
    entry = exact[0]
    out = {"feed_local_date": target.isoformat(), "date_basis": basis, "date_tolerance_days": tolerance,
           "secondary_away": entry["away"], "secondary_neutral": entry["neutral"],
           "secondary_site_stadium": entry["site_stadium"], "secondary_site_cityst": entry["site_cityst"]}
    city, code = city_state(entry["site_cityst"])
    stadium = stadium_key(entry["site_stadium"])
    if not venue or not (city or stadium):
        out["state"] = CONFIRM_DATE_ONLY
        return out
    venue_city, venue_state = fold(str(venue.get("city") or "")), str(venue.get("state") or "").upper() or None
    same_state = code is not None and venue_state is not None and code == venue_state
    same_city = bool(city) and city == venue_city and (code is None or venue_state is None or code == venue_state)
    same_stadium = bool(stadium) and stadium == stadium_key(str(venue.get("name") or ""))
    # v37.2: declared spellings of one place, and one stadium named two
    # ways, each only within the same state. Recorded as their own basis so
    # a reader can separate them from exact matches.
    city_by_alias = (not same_city and bool(city) and same_state
                     and city_alias(city) == city_alias(venue_city))
    stadium_by_tokens = (not same_stadium and bool(stadium) and same_state
                         and stadium_tokens_match(entry["site_stadium"], str(venue.get("name") or "")))
    basis = [b for b, hit in (("CITY", same_city), ("STADIUM_NAME", same_stadium),
                              ("CITY_DECLARED_ALIAS_SAME_STATE", city_by_alias),
                              ("STADIUM_NAME_TOKENS_SAME_STATE", stadium_by_tokens)) if hit]
    out["site_match_basis"] = basis
    out["state"] = CONFIRM_SITE if basis else CONFIRM_SITE_CONFLICT
    return out


def venue_support(venue_id: Any, venue: Mapping[str, Any] | None, confirmation: Mapping[str, Any]) -> str:
    """The honest label for where the contest was played."""

    if venue_id is None:
        return VENUE_ABSENT
    if venue is None:
        return VENUE_UNRESOLVED
    if confirmation.get("state") == CONFIRM_SITE:
        return VENUE_CONFIRMED
    if confirmation.get("state") == CONFIRM_SITE_CONFLICT:
        return VENUE_CONFLICT
    return VENUE_PROVIDER_ONLY


def neutral_status(flag: Any) -> str:
    if flag is True:
        return NEUTRAL_TRUE
    if flag is False:
        return NEUTRAL_FALSE
    return NEUTRAL_UNKNOWN


def ordinary_home_term(status: str) -> dict[str, Any]:
    """Neutral removes the ordinary home term; it does not remove travel."""

    if status == NEUTRAL_TRUE:
        return {"ordinary_home_term_applies": False, "ordinary_home_term_magnitude": 0.0,
                "basis": "SOURCE_DESIGNATED_NEUTRAL_REMOVES_ORDINARY_HOME_TERM"}
    if status == NEUTRAL_FALSE:
        return {"ordinary_home_term_applies": True, "ordinary_home_term_magnitude": None,
                "basis": "ORDINARY_HOME_TERM_IS_A_SEPARATELY_VALIDATED_FEATURE"}
    return {"ordinary_home_term_applies": None, "ordinary_home_term_magnitude": None,
            "basis": "UNKNOWN_NEUTRAL_STATUS_FAILS_CLOSED"}


# ------------------------------------------------------------------ travel
def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


class TimeZoneDatabaseUnavailable(RuntimeError):
    """A venue declares an IANA zone and this interpreter has no zone database.

    That is not the same fact as "the venue has no zone". Treating it as one
    silently read every kickoff in UTC and dropped every time-zone shift in an
    interpreter without the tzdata package (Windows has no system IANA
    database), so it is refused instead, like the other temporal modules do.
    """


def zone_or_none(name: str | None) -> ZoneInfo | None:
    """The venue's zone; None only when it declares none or an unknown key."""

    if not name:
        return None
    try:
        return ZoneInfo(str(name))
    except ValueError:
        return None
    except ZoneInfoNotFoundError:
        if not available_timezones():
            raise TimeZoneDatabaseUnavailable(
                f"venue time zone {name!r} cannot be read: this interpreter has no IANA time-zone database "
                "(on Windows, install the tzdata package). A missing database is not a missing zone."
            ) from None
        return None


def utc_offset_hours(tz_name: str | None, at: datetime | None) -> float | None:
    zone = zone_or_none(tz_name)
    if zone is None or at is None:
        return None
    offset = at.astimezone(zone).utcoffset()
    return None if offset is None else offset.total_seconds() / 3600.0


@dataclass(frozen=True)
class Origin:
    """A side's reference origin: its current-vintage home venue."""

    latitude: float | None
    longitude: float | None
    timezone: str | None
    venue_id: Any = None


def leg(origin: Origin | None, venue: Mapping[str, Any] | None, kickoff: datetime | None) -> dict[str, Any]:
    if origin is None or origin.latitude is None or origin.longitude is None or not venue \
            or venue.get("latitude") is None or venue.get("longitude") is None:
        return {"km": None, "miles": None, "tz_shift_hours": None,
                "state": "UNKNOWN_MISSING_ORIGIN_OR_VENUE_COORDINATES"}
    points = (origin.latitude, origin.longitude, float(venue["latitude"]), float(venue["longitude"]))
    if not all(math.isfinite(value) for value in points) or abs(points[0]) > 90 or abs(points[2]) > 90:
        return {"km": None, "miles": None, "tz_shift_hours": None,
                "state": "UNKNOWN_NONFINITE_OR_OUT_OF_RANGE_COORDINATE"}
    km = great_circle_km(*points)
    at_venue = utc_offset_hours(venue.get("timezone"), kickoff)
    at_origin = utc_offset_hours(origin.timezone, kickoff)
    shift = None if at_venue is None or at_origin is None else at_venue - at_origin
    return {"km": km, "miles": km / KM_PER_MILE, "tz_shift_hours": shift,
            "same_venue_as_origin": origin.venue_id is not None and origin.venue_id == venue.get("id"),
            "state": "COMPUTED_FROM_CURRENT_VINTAGE_ORIGIN_NOT_PIT"}


def parse_instant(start_utc: str | None) -> datetime | None:
    if not start_utc:
        return None
    try:
        instant = datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
    except ValueError:
        return None
    return instant if instant.tzinfo else instant.replace(tzinfo=timezone.utc)


def rest_days(previous: Mapping[int, list[datetime]], team_id: int | None, kickoff: datetime | None) -> int | None:
    """Days since the team's previous contest in the same feed, or None."""

    if team_id is None or kickoff is None:
        return None
    earlier = [t for t in previous.get(int(team_id), []) if t < kickoff - timedelta(hours=6)]
    return (kickoff.date() - max(earlier).date()).days if earlier else None


def contest_row(
    *, game: Mapping[str, Any], venue: Mapping[str, Any] | None, home: Origin | None, away: Origin | None,
    confirmation: Mapping[str, Any], previous: Mapping[int, list[datetime]],
) -> dict[str, Any]:
    """The successor row for one contest. Swapping sides swaps the legs only."""

    kickoff = parse_instant(game.get("startDate"))
    status = neutral_status(game.get("neutralSite"))
    home_leg, away_leg = leg(home, venue, kickoff), leg(away, venue, kickoff)
    row = {
        "site_version": SITE_VERSION,
        "canonical_game_id": f"SRC-002:GAME:{game.get('id')}",
        "season": game.get("season"),
        "start_utc": game.get("startDate"),
        "designated_home_team_id": game.get("homeId"),
        "designated_away_team_id": game.get("awayId"),
        "designated_home_classification": game.get("homeClassification"),
        "designated_away_classification": game.get("awayClassification"),
        "designation_is_administrative_not_site_evidence": True,
        "source_neutral_flag": game.get("neutralSite"),
        "neutral_status": status,
        "venue_id": game.get("venueId"),
        "venue_name": (venue or {}).get("name"),
        "venue_timezone": (venue or {}).get("timezone"),
        "venue_support": venue_support(game.get("venueId"), venue, confirmation),
        "secondary_confirmation": dict(confirmation),
        "home_leg": home_leg,
        "away_leg": away_leg,
        "legs_computed": sum(1 for x in (home_leg, away_leg) if x["km"] is not None),
        "home_rest_days": rest_days(previous, game.get("homeId"), kickoff),
        "away_rest_days": rest_days(previous, game.get("awayId"), kickoff),
        "same_team_both_sides": game.get("homeId") is not None and game.get("homeId") == game.get("awayId"),
        "geometry_authority": "CURRENT_VINTAGE_DEVELOPMENT_ONLY_NOT_PIT",
        "pit_admitted": False,
    }
    row.update(ordinary_home_term(status))
    return row


def previous_contests(games: Iterable[Mapping[str, Any]]) -> dict[int, list[datetime]]:
    by_team: dict[int, list[datetime]] = {}
    for game in games:
        kickoff = parse_instant(game.get("startDate"))
        if kickoff is None:
            continue
        for side in ("homeId", "awayId"):
            if game.get(side) is not None:
                by_team.setdefault(int(game[side]), []).append(kickoff)
    return by_team
