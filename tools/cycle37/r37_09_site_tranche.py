"""Cycle #37 - Attempt #2 - ACTUAL_STATE

W37R-30 third-source tranche: adjudicate contest-site conflicts between the game
feed and the secondary source with the programs' own official schedule pages.

The conflict population is the R37-09 rows in DATE_CONFIRMED_SITE_CITY_DISAGREES
(the feed venue's city and the secondary source's city differ on a date both
confirm). One official season schedule page covers every conflict of that
team-season, so pages are chosen by a deterministic greedy cover: most
still-uncovered conflicts first, ties by team id then season. That makes the
tranche a coverage sample, not a random one; its agreement rates describe the
covered contests and are not population estimates.

A site whose archive does not hold the requested season answers the season URL
with its current schedule. Such a page is recorded as SEASON_NOT_ARCHIVED, and
the season list every fetched page publishes is used to skip that host's other
unarchived seasons before a request is spent. ``run`` therefore re-plans after
every page: plan, fetch the best page not yet read (cache first, otherwise one
ledgered game request through r37_fetch, whose ceiling and two-tries rule
apply), learn the host's archive, repeat. ``adjudicate`` compares the official
city on each contest's local date with the feed venue's city and the secondary
source's city.
"""

from __future__ import annotations

import argparse
import collections
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
R = ATTEMPT / "evidence" / "repairs"
SITE_ROWS = R / "R37_09_CONTEST_SITE_ROWS.jsonl"
VENUES = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/outputs/CFBD_VENUES.jsonl")
IDENTITY_ROWS = R / "R37_03_SOURCE_IDENTITY_ROWS.jsonl"
GAMES_CACHE = ATTEMPT / "private" / "acquisition" / "games"
PLAN = R / "R37_09_SITE_TRANCHE_PLAN.json"
FETCH_LOG = R / "R37_09_SITE_TRANCHE_FETCH.json"
OUT = R / "R37_09_SITE_TRANCHE.json"
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                      "dec"], start=1)}
PURPOSE = "W37R-30: official season schedule page, the third source for contest-site conflicts (read-only)"


def norm_city(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(str(text or "")).casefold()).strip()


def schedule_url(host: str, season: int) -> str:
    return f"https://{host}/sports/football/schedule/{season}"


def conflicts() -> list[dict[str, Any]]:
    rows = []
    with SITE_ROWS.open(encoding="utf-8") as handle:
        for line in handle:
            if "DATE_CONFIRMED_SITE_CITY_DISAGREES" not in line:
                continue
            row = json.loads(line)
            if (row.get("secondary_confirmation") or {}).get("state") == "DATE_CONFIRMED_SITE_CITY_DISAGREES":
                rows.append(row)
    return rows


def cover_sets(rows: list[dict[str, Any]]) -> dict[tuple[int, int], set[str]]:
    cover: dict[tuple[int, int], set[str]] = collections.defaultdict(set)
    for row in rows:
        for side in ("designated_home_team_id", "designated_away_team_id"):
            cover[(int(row[side]), int(row["season"]))].add(row["canonical_game_id"])
    return cover


def official_hosts() -> dict[int, str]:
    """Each program's official athletics host, from captures its page identity confirmed."""

    hosts: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
    with IDENTITY_ROWS.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            pid = row.get("admitted_program_id")
            if row.get("state") != "CONFIRMED_BY_SOURCE_IDENTITY" or not pid:
                continue
            host = urlparse(str(row.get("route") or "")).netloc.lower()
            if host:
                hosts[int(str(pid).rsplit(":", 1)[1])][host] += 1
    return {team: counter.most_common(1)[0][0] for team, counter in hosts.items() if len(counter) == 1}


def cached(url: str) -> dict[str, Any] | None:
    if not GAMES_CACHE.is_dir():
        return None
    for meta in sorted(GAMES_CACHE.glob("*.meta.json")):
        record = json.loads(meta.read_text(encoding="utf-8"))
        if record.get("url") == url and record.get("stored") and (record.get("http_status") or 0) < 300 \
                and record.get("bytes"):
            return record
    return None


def served_requested_season(record: dict[str, Any]) -> bool:
    return urlparse(str(record.get("final_url") or "")).path.rstrip("/") == urlparse(record["url"]).path.rstrip("/")


def archived_seasons(text: str) -> set[int]:
    return {int(y[:4]) for y in re.findall(r"/sports/football/schedule/(\d{4})(?:-\d{2,4})?\b", text)}


def knowledge() -> tuple[dict[str, set[int]], set[tuple[str, int]]]:
    """Per host, the seasons its fetched pages list; and every (host, season) already read or refused."""

    archives: dict[str, set[int]] = {}
    tried: set[tuple[str, int]] = set()
    log = json.loads(FETCH_LOG.read_text(encoding="utf-8")) if FETCH_LOG.is_file() else []
    for item in log:
        tried.add((item["host"], int(item["season"])))
        record = item.get("record") or {}
        if record.get("stored"):
            text = Path(record["stored"]).read_bytes().decode("utf-8", "replace")
            archives.setdefault(item["host"], set()).update(archived_seasons(text))
    return archives, tried


def plan(max_pages: int) -> dict[str, Any]:
    rows = conflicts()
    cover = cover_sets(rows)
    hosts = official_hosts()
    archives, tried = knowledge()
    left = {row["canonical_game_id"] for row in rows}
    pages, skipped = [], collections.defaultdict(list)
    while left and len(pages) < max_pages:
        candidates = sorted(((len(games & left), key) for key, games in cover.items() if games & left),
                            key=lambda item: (-item[0], item[1]))
        chosen = None
        for count, (team, season) in candidates:
            host = hosts.get(team)
            if not host:
                reason = "NO_CONFIRMED_OFFICIAL_HOST"
            elif host in archives and season not in archives[host]:
                reason = "HOST_ARCHIVE_DOES_NOT_LIST_THE_SEASON"
            else:
                chosen = (team, season, host)
                break
            if [team, season] not in skipped[reason]:
                skipped[reason].append([team, season])
        if chosen is None:
            break
        team, season, host = chosen
        games = sorted(cover[(team, season)] & left)
        pages.append({"team_id": team, "season": season, "host": host, "url": schedule_url(host, season),
                      "covers": games, "already_read": (host, season) in tried})
        left -= set(games)
    report = {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "finding": "W37R-30",
              "population": len(rows), "pages": pages, "covered": sum(len(p["covers"]) for p in pages),
              "left_uncovered": len(left), "selection": "deterministic greedy cover; a coverage sample, not random",
              "skipped": {k: v for k, v in skipped.items()},
              "known_host_archives": {h: sorted(s) for h, s in archives.items()},
              "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    _bas_atomic.write_text(PLAN, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def run(budget: int) -> list[dict[str, Any]]:
    """Re-plan after every page; stop at the request budget, the ceiling or an exhausted plan."""

    import r37_fetch

    log = json.loads(FETCH_LOG.read_text(encoding="utf-8")) if FETCH_LOG.is_file() else []
    spent = 0
    while spent < budget:
        report = plan(budget)
        page = next((p for p in report["pages"] if not p["already_read"]), None)
        if page is None:
            break
        item = {"team_id": page["team_id"], "season": page["season"], "host": page["host"], "url": page["url"]}
        hit = cached(page["url"])
        if hit:
            item.update(source="CACHE", record=hit)
        else:
            try:
                item.update(source="REQUEST", record=r37_fetch.fetch(page["url"], "games", PURPOSE))
                spent += 1
            except r37_fetch.FetchRefused as refused:
                item.update(source="REFUSED", error=str(refused))
                log.append(item)
                break
        log.append(item)
        _bas_atomic.write_text(FETCH_LOG, json.dumps(log, indent=2) + "\n", encoding="utf-8")
    _bas_atomic.write_text(FETCH_LOG, json.dumps(log, indent=2) + "\n", encoding="utf-8")
    return log


def _entry(month_text: str, day: int, season: int, where: str, side: str, opponent: str | None) -> dict[str, Any]:
    month = MONTHS[month_text.casefold()[:3]]
    year = season + 1 if month < 7 else season
    where = html.unescape(where).strip()
    return {"date": f"{year:04d}-{month:02d}-{day:02d}", "location": where,
            "city": norm_city(where.split(",")[0]) if where else "", "side": side, "opponent": opponent}


def parse_game_cards(text: str, season: int) -> list[dict[str, Any]]:
    """Newer Sidearm pages: one ``s-game-card`` per game; the location follows the card's location icon.

    The same pages carry sliders of the current season's events; those are not game cards and are not read.
    """

    starts = [m.start() for m in re.finditer(r'<div[^>]*class="s-game-card[ "]', text)]
    entries = []
    for start, end in zip(starts, starts[1:] + [len(text)]):
        card = text[start:end]
        plain = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", card)))
        date = re.search(r"\b([A-Z][a-z]{2})[a-z]*\.?\s+(\d{1,2})\b", plain)
        icon = card.find("s-icon-location")
        where = ""
        if icon >= 0:
            after = re.sub(r"<svg\b.*?</svg>", " ", card[icon:], flags=re.S)
            for chunk in re.split(r"<[^>]+>", after):
                chunk = html.unescape(chunk).strip()
                if chunk and not chunk.startswith(("s-icon", '"')) and "=" not in chunk:
                    where = chunk
                    break
        if not date or date.group(1).casefold()[:3] not in MONTHS:
            continue
        side = "AWAY" if re.search(r"\b(at|@)\s", plain[date.end():date.end() + 40]) else \
            "HOME" if re.search(r"\bvs\.?\s", plain[date.end():date.end() + 40]) else "UNSTATED"
        entries.append(_entry(date.group(1), int(date.group(2)), season, where, side, None))
    return entries


def parse_sidearm(text: str, season: int) -> list[dict[str, Any]]:
    """Classic Sidearm schedule entries: date, location, home/away/neutral class, opponent.

    An entry carries a mobile and a desktop block; the first block's location can be empty for home games,
    so the first non-empty location of the entry is read. Pages in the newer card layout go to
    parse_game_cards.
    """

    if "sidearm-schedule-game" not in text and "s-game-card" in text:
        return parse_game_cards(text, season)

    entries = []
    # An entry runs from its own <li class="sidearm-schedule-game ..."> to the next entry's, because an entry
    # nests lists of its own and a closing </ul> inside it is not the end of the entry.
    starts = list(re.finditer(r'<li[^>]*class="(sidearm-schedule-game(?:\s[^"]*)?)"', text))
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        classes, body = match.group(1), text[match.end():end]
        date = re.search(r'sidearm-schedule-game-opponent-date[^>]*>\s*<span>\s*([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})',
                         body)
        locations = [html.unescape(v).strip() for v in
                     re.findall(r'sidearm-schedule-game-location[^>]*>\s*<span>([^<]*)</span>', body)]
        location = next((v for v in locations if v), "")
        opponent = re.search(r'sidearm-schedule-game-opponent-name[^>]*>\s*(?:<a[^>]*>)?\s*([^<]+)', body)
        if not date or date.group(1).casefold()[:3] not in MONTHS:
            continue
        month, day = MONTHS[date.group(1).casefold()[:3]], int(date.group(2))
        year = season + 1 if month < 7 else season
        side = ("HOME" if "sidearm-schedule-home-game" in classes else "AWAY" if "sidearm-schedule-away-game" in classes
                else "NEUTRAL" if "sidearm-schedule-neutral-game" in classes else "UNSTATED")
        where = location
        entries.append({"date": f"{year:04d}-{month:02d}-{day:02d}", "location": where,
                        "city": norm_city(where.split(",")[0]) if where else "", "side": side,
                        "opponent": html.unescape(opponent.group(1)).strip() if opponent else None})
    return entries


def adjudicate() -> dict[str, Any]:
    rows = {row["canonical_game_id"]: row for row in conflicts()}
    cover = cover_sets(list(rows.values()))
    venues = {}
    with VENUES.open(encoding="utf-8") as handle:
        for line in handle:
            venue = json.loads(line)
            venues[venue.get("id")] = venue
    log = json.loads(FETCH_LOG.read_text(encoding="utf-8")) if FETCH_LOG.is_file() else []
    results, states, pages = [], collections.Counter(), []
    seen: set[str] = set()
    for item in log:
        record = item.get("record") or {}
        text = Path(record["stored"]).read_bytes().decode("utf-8", "replace") if record.get("stored") else ""
        served = bool(text) and served_requested_season(record)
        entries = parse_sidearm(text, int(item["season"])) if served else []
        page_state = ("REFUSED" if item.get("source") == "REFUSED" else "FETCH_FAILED" if not text else
                      "SEASON_NOT_ARCHIVED" if not served else "NO_SIDEARM_ENTRIES" if not entries else "READ")
        pages.append({"url": item["url"], "source": item.get("source"), "state": page_state,
                      "final_url": record.get("final_url"), "sha256": record.get("sha256"), "entries": len(entries)})
        for game in sorted(cover.get((int(item["team_id"]), int(item["season"])), set())):
            if game in seen and page_state != "READ":
                continue
            row = rows[game]
            second = row["secondary_confirmation"]
            feed_city = norm_city((venues.get(row.get("venue_id")) or {}).get("city"))
            secondary_city = norm_city(str(second.get("secondary_site_cityst") or "").split(",")[0])
            on_date = [e for e in entries if e["date"] == second.get("feed_local_date")]
            if page_state != "READ":
                state = f"PAGE_{page_state}"
            elif len(on_date) != 1:
                state = "NO_SINGLE_OFFICIAL_ENTRY_ON_THE_DATE"
            elif not on_date[0]["city"]:
                state = "OFFICIAL_ENTRY_STATES_NO_LOCATION"
            else:
                official = on_date[0]["city"]
                feed, sec = official == feed_city, official == secondary_city
                state = ("OFFICIAL_CITY_MATCHES_BOTH" if feed and sec else "OFFICIAL_CITY_MATCHES_FEED" if feed
                         else "OFFICIAL_CITY_MATCHES_SECONDARY" if sec else "OFFICIAL_CITY_MATCHES_NEITHER")
            results = [r for r in results if r["canonical_game_id"] != game]
            seen.add(game)
            results.append({"canonical_game_id": game, "team_id": item["team_id"], "season": item["season"],
                            "page": item["url"], "page_sha256": record.get("sha256"),
                            "contest_local_date": second.get("feed_local_date"),
                            "feed_venue": row.get("venue_name"), "feed_city": feed_city,
                            "secondary_city": secondary_city, "secondary_revision": second.get("secondary_revision"),
                            "official_entries_on_date": on_date, "state": state})
    states = collections.Counter(r["state"] for r in results)
    adjudicated = [r for r in results if r["state"].startswith("OFFICIAL_CITY_MATCHES")]
    feed_cities = collections.Counter((r["feed_venue"], r["feed_city"], r["secondary_city"]) for r in results)
    summary = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "finding": "W37R-30", "requirement": "R37-09",
        "population_conflicts": len(rows), "pages": pages,
        "requests_spent": sum(1 for item in log if item.get("source") == "REQUEST"),
        "cache_hits": sum(1 for item in log if item.get("source") == "CACHE"),
        "conflicts_reached": len(results), "adjudicated": len(adjudicated), "states": dict(states),
        "among_adjudicated": {
            "official_agrees_with_secondary_only": states["OFFICIAL_CITY_MATCHES_SECONDARY"],
            "official_agrees_with_feed_only": states["OFFICIAL_CITY_MATCHES_FEED"],
            "official_agrees_with_both": states["OFFICIAL_CITY_MATCHES_BOTH"],
            "official_agrees_with_neither": states["OFFICIAL_CITY_MATCHES_NEITHER"]},
        "feed_venue_city_versus_secondary_city_on_reached_conflicts": [
            {"feed_venue": v, "feed_city": f, "secondary_city": s, "contests": n}
            for (v, f, s), n in feed_cities.most_common()],
        "not_a_population_estimate": ("Pages were chosen to cover the most conflicts, so the reached contests "
                                      "cluster in a few programs; the rates describe them only."),
        "rows_are_evidence_not_release_rows": True,
        "rows": results,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _bas_atomic.write_text(OUT, json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    parser.add_argument("step", choices=["plan", "run", "adjudicate"])
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--budget", type=int, default=0, help="request budget for this run (0 reads cache only)")
    args = parser.parse_args(argv)
    if args.step == "plan":
        report = plan(args.max_pages)
        print(json.dumps({k: report[k] for k in ("population", "covered", "left_uncovered")}),
              [(p["team_id"], p["season"], p["host"], len(p["covers"])) for p in report["pages"]])
    elif args.step == "run":
        log = run(args.budget)
        print([(i["url"], i["source"], (i.get("record") or {}).get("http_status")) for i in log])
    else:
        summary = adjudicate()
        print(json.dumps({k: summary[k] for k in ("requests_spent", "conflicts_reached", "adjudicated", "states")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
