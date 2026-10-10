"""BAT-721 (Cycle #49 — Attempt #1, TP49-A01): tiny owned worlds for the explicit official-site evidence sidecar.

Every fixture is real: a parent query database built and materialized by the accepted parent builder, a gzip crosswalk,
a canonical registry, two provider captures with their receipts, the accepted V1 builder's sidecar, the accepted alias
builder's successor (an empty alias universe: every name here is documented) and a retained evidence bundle of
synthetic NCAA directory records and official season schedule pages (devalue payloads). Nothing here is real-world
evidence: names and hosts only exercise the rules. The world's contests cover an alternate home venue, a genuinely
neutral event, conflicting official sources, a designated home team at the opponent's stadium, a January final of the
previous season, an unbindable opponent, a stale date, a denied host, a page no declared schema admits, a current
widget and another sport's record on the same date, and one agreeing contest outside the universe.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import national_reconciliation_aliases_fixture as afx

ROOT = afx.ROOT
pop = afx.pop
query = afx.query
PARENT_CONTRACT_SHA = afx.PARENT_CONTRACT_SHA
M1, M2 = afx.M1, afx.M2
ALIAS_POPULATION = afx.POPULATION
ALIAS_DB_NAME = afx.DB_NAME
POPULATION = "national_site_evidence_2024_2025"
DB_NAME = "national_site_evidence.sqlite"
BUILDER = ROOT / "tools" / "build_national_site_evidence.py"
ACQUISITION = "C49-A01 FIXTURE run fixture"

#: org -> (NCAA name, {season: division label}, provider team id, provider name, crosswalk rule)
TEAMS = {
    "811": ("Lakefront", {2024: "FBS", 2025: "FBS"}, "7811", "Lakefront", "NAME_CONFIRMED_BY_SCHEDULE"),
    "812": ("Prairie St.", {2024: "FBS", 2025: "FBS"}, "7812", "Prairie State", "NAME_CONFIRMED_BY_SCHEDULE"),
    "813": ("Harbor Tech", {2024: "FBS", 2025: "FBS"}, "7813", "Harbor Tech", "NAME_CONFIRMED_BY_SCHEDULE"),
    "814": ("Canyon A&M", {2024: "FBS", 2025: "FBS"}, "7814", "Canyon A&M", "NAME_CONFIRMED_BY_SCHEDULE"),
    "815": ("Delta", {2024: "FCS", 2025: "FCS"}, "7815", "Delta", "NAME_CONFIRMED_BY_SCHEDULE"),
    "816": ("Summit", {2024: "FBS", 2025: "FBS"}, "7816", "Summit", "NAME_CONFIRMED_BY_SCHEDULE"),
}
#: (contest key, season, final date, a, b, a points, b points, parent site, provider neutral flag, provider home org)
GAMES = [
    ("ncaa:9101", 2024, "2024-09-07", "812", "811", 10, 31, "HOME_B", True, "811"),
    ("ncaa:9102", 2024, "2024-09-14", "813", "814", 21, 24, "HOME_B", True, "814"),
    ("ncaa:9103", 2024, "2024-10-05", "815", "816", 14, 17, "HOME_A", True, "815"),
    ("ncaa:9105", 2024, "2024-11-02", "811", "812", 35, 3, "HOME_A", False, "811"),
    ("ncaa:9104", 2024, "2024-12-21", "816", "813", 27, 20, "HOME_A", False, "813"),
    ("ncaa:9202", 2025, "2025-09-13", "812", "815", 7, 28, "HOME_B", True, "815"),
    ("ncaa:9203", 2025, "2025-10-04", "813", "811", 13, 16, "HOME_B", True, "811"),
    ("ncaa:9201", 2025, "2026-01-19", "811", "814", 30, 27, "HOME_B", True, "811"),
]
#: The universe in predecessor order (season, date, key) and each contest's expected official disposition.
EXPECTED = {
    "ncaa:9101": "PARENT_CLAIM_SUPPORTED",          # alternate home venue: H and A agree, neutral false
    "ncaa:9102": "PROVIDER_CLAIM_SUPPORTED",        # genuinely neutral: N and N (designated home b by flag)
    "ncaa:9103": "OFFICIAL_SOURCES_CONFLICT",       # H against N
    "ncaa:9104": "PROVIDER_CLAIM_SUPPORTED",        # designated home b at the opponent's stadium (home orientation)
    "ncaa:9202": "UNSUPPORTED_NO_BOUND_RECORD",     # denied host; the other record names another opponent
    "ncaa:9203": "UNSUPPORTED_FIELD_NOT_STATED",    # a bound record without a designation; a stale date elsewhere
    "ncaa:9201": "PROVIDER_CLAIM_SUPPORTED",        # January final of season 2025, neutral with designated home a
}
#: org -> (institution name, published athletics URL value)
INSTITUTIONS = {
    "811": ("Lakefront University", "www.lakefrontathletics.example"),
    "812": ("Prairie State University", "prairiestatesports.example/"),
    "813": ("Harbor Institute of Technology", "harbortechsports.example"),
    "814": ("Canyon A&M University", "https://canyonaggies.example/"),
    "815": ("Delta College", "www.deltagators.example"),
    "816": ("Summit University", "summitathletics.example"),
}
HOSTS = {"811": "lakefrontathletics.example", "812": "prairiestatesports.example", "813": "harbortechsports.example",
         "814": "canyonaggies.example", "815": "deltagators.example", "816": "summitathletics.example"}
DIRECTORY_URL = "https://web3.ncaa.org/directory/api/directory/memberList?type=12&sportCode=MFB"


def contest(key: str, season: int, date: str, a: str, b: str, a_pts: int, b_pts: int, site: str) -> dict[str, Any]:
    def side(org: str) -> dict[str, Any]:
        return {"org_id": org, "team_season_id": f"ts{org}{season}", "team_name": TEAMS[org][0],
                "division_label": TEAMS[org][1][season], "membership": "DIVISION_I", "key": f"org:{org}"}
    sa, sb = side(a), side(b)
    row = {"contest_key": key, "ncaa_contest_id": key.split(":", 1)[1], "season": season, "term": "FALL",
           "contest_date": date, "contest_dates_observed": [date], "site": site, "neutral_site_text": None,
           "contest_status": "COMPLETED", "competitive": True,
           "classification_pair": "-".join(sorted((sa["division_label"], sb["division_label"]))),
           "mirror_observation_count": 2, "source": "NCAA_GRAPH", "cfbd_game_ids": [],
           "reconciliation_state": "SINGLE_SOURCE_UNRECONCILED", "disposition": "CANDIDATE_ONLY",
           "disposition_reason": "SINGLE_SOURCE_UNRECONCILED", "exposure": "EXPOSED_NOT_PROTECTED",
           "conflict_fields": [], "flags": [], "event_labels": [], "a_points": a_pts, "b_points": b_pts}
    for prefix, s in (("a", sa), ("b", sb)):
        for field in ("org_id", "team_season_id", "team_name", "division_label", "membership", "key"):
            row[f"{prefix}_{field}"] = s[field]
    return row


def game(gid: int, season: int, date: str, a: str, b: str, a_pts: int, b_pts: int, neutral: bool,
         home: str) -> dict[str, Any]:
    away = b if home == a else a
    points = {a: a_pts, b: b_pts}

    def cls(org: str) -> str:
        return "fbs" if TEAMS[org][1][season] == "FBS" else "fcs"
    return {"id": gid, "season": season, "week": 1, "seasonType": "regular", "startDate": f"{date}T19:00:00.000Z",
            "startTimeTBD": False, "completed": True, "neutralSite": neutral, "conferenceGame": False,
            "homeId": int(TEAMS[home][2]), "homeTeam": TEAMS[home][3], "homeClassification": cls(home),
            "homeConference": "X", "homePoints": points[home], "awayId": int(TEAMS[away][2]),
            "awayTeam": TEAMS[away][3], "awayClassification": cls(away), "awayConference": "Y",
            "awayPoints": points[away]}


def write_registry(path: Path) -> None:
    import csv  # noqa: PLC0415
    columns = ["schema_version", "record_type", "entity_type", "record_id", "canonical_id", "identity_key",
               "resolution_state", "alias", "effective_from", "effective_to_exclusive", "source_system_id"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for _org, (_n, _l, pid, pname, _r) in sorted(TEAMS.items()):
            canonical = f"team_{pid}"
            writer.writerow({"schema_version": "1.0.0", "record_type": "ENTITY", "entity_type": "team",
                             "record_id": f"ent_{pid}", "canonical_id": canonical, "identity_key": f"TEAM|SRC-002|{pid}",
                             "resolution_state": "AUTO_ACCEPTED_VERIFIED"})
            writer.writerow({"schema_version": "1.0.0", "record_type": "ALIAS", "entity_type": "team",
                             "record_id": f"obs_{pid}_name", "canonical_id": canonical,
                             "resolution_state": "AUTO_ACCEPTED_VERIFIED", "alias": pname,
                             "effective_from": "2021-01-01", "effective_to_exclusive": "2027-01-01",
                             "source_system_id": "SRC-002"})


def build_world(base: Path) -> dict[str, Any]:
    """The parent and every cached input under ``base``; return the bindings the contracts name."""
    rows = [contest(*g[:8]) for g in GAMES]
    provider = {2024: [], 2025: []}
    for number, (key, season, date, a, b, a_pts, b_pts, _site, neutral, home) in enumerate(GAMES, 1):
        provider[season].append(game(number, season, date, a, b, a_pts, b_pts, neutral, home))
    cells = []
    for org, (name, labels, _p, _n, _r) in sorted(TEAMS.items()):
        for season, label in labels.items():
            cells.append({"cell_key": f"org:{org}:{season}", "season": season, "ncaa_org_id": org, "team_name": name,
                          "ncaa_team_season_id": f"ts{org}{season}", "division_code_observed": "11",
                          "division_label": label, "division_authority": "GRAPH_PAGE", "disposition": "VERIFIED_PRESENT",
                          "in_division_i_population": True, "expected_sources": ["E1"], "flags": [], "observations": {}})
    data = pop.build_query_database(contract_sha256=PARENT_CONTRACT_SHA, m1_identity=M1, m2_identity=M2, cells=cells,
                                    contests=rows, orientations=[],
                                    subsets={"FBS_ESTIMAND_SUBSET": [], "FCS_SUBSET": []}, schedule=[])
    result = pop.materialize(canonical_root=base / "canonical" / "p", manifest_root=base / "manifests" / "p",
                             stage="query-db", contract_sha256=PARENT_CONTRACT_SHA, inputs={},
                             upstream={"program-season": M1, "contest": M2}, files={pop.DB_FILE_NAME: data},
                             manifest_extra={})
    parent_db = Path(result["data_dir"]) / pop.DB_FILE_NAME
    bindings = [{"_header": {"contract_sha256": PARENT_CONTRACT_SHA, "schema": "BAS-NATIONAL-DI-POPULATION-1",
                             "stage": "program-season"}}]
    for org, (_n, _l, pid, _pn, rule) in sorted(TEAMS.items()):
        bindings.append({"org_id": org, "cfbd_team_id": pid, "rule": rule, "reason": None})
    afx.write_gzip_jsonl(base / "canonical" / "p" / "sha256" / M1 / "identity_bindings.jsonl.gz", bindings)
    write_registry(base / "canonical" / "reg" / "canonical_core_registry.csv")
    captures = []
    for season, games in provider.items():
        raw = json.dumps(games).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        rel = f"raw/SRC-002/games/sha256_{digest}.json"
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        (base / rel).write_bytes(raw)
        receipt = {"response_sha256": digest, "row_count": len(games), "capture_id": f"cap_site_{season}",
                   "source_id": "SRC-002", "path": "/games", "parameters": {"classification": "fbs", "year": str(season)},
                   "immutable_path": rel, "http_status": 200, "result": "SUCCESS"}
        receipt_rel = f"manifests/captures/SRC-002/cap_site_{season}.json"
        (base / receipt_rel).parent.mkdir(parents=True, exist_ok=True)
        (base / receipt_rel).write_text(json.dumps(receipt, indent=1), encoding="utf-8")
        captures.append({"season": season, "relative_path": rel, "sha256": digest, "rows": len(games),
                         "receipt_relative_path": receipt_rel, "receipt_sha256": afx.sha(base / receipt_rel),
                         "capture_id": f"cap_site_{season}", "source_id": "SRC-002", "route_path": "/games",
                         "route_parameters": {"classification": "fbs", "year": str(season)}})
    counts = {"2024": sum(1 for g in GAMES if g[1] == 2024), "2025": sum(1 for g in GAMES if g[1] == 2025)}
    parent = {"query_db_identity": parent_db.parent.name, "sqlite_sha256": afx.sha(parent_db),
              "contract_sha256": PARENT_CONTRACT_SHA, "schema_version": pop.DB_SCHEMA_VERSION, "contest_identity": M2,
              "program_season_identity": M1, "expected_contests": counts}
    inputs = {"identity_bindings": {"relative_path": f"canonical/p/sha256/{M1}/identity_bindings.jsonl.gz",
                                    "sha256": afx.sha(base / "canonical" / "p" / "sha256" / M1 / "identity_bindings.jsonl.gz")},
              "registry": {"relative_path": "canonical/reg/canonical_core_registry.csv",
                           "sha256": afx.sha(base / "canonical" / "reg" / "canonical_core_registry.csv")},
              "provider_captures": captures}
    return {"parent_db": parent_db, "parent": parent, "inputs": inputs, "provider": provider}


def build_alias_successor(base: Path, world: dict[str, Any], v1: dict[str, Any], work: Path) -> dict[str, Any]:
    """The accepted alias builder's successor over this world (an empty alias universe: every name is documented)."""
    evidence = {"assertions": {"schema": query.ALIAS_ASSERTIONS_SCHEMA, "population": ALIAS_POPULATION, "universe": [],
                               "assertions": [], "documents": []}, "bodies": {}}
    pins = afx.write_evidence(work / "alias-ev", evidence)
    contract = work / "alias_contract.json"
    anchors = afx.successor_contract(contract, world, v1, pins, [])
    module = afx.load_module(afx.BUILDER, "build_national_reconciliation_aliases_site_fixture")
    code, built, err = afx.run_builder(module, [
        "--contract", str(contract), "--predecessor-contract", str(v1["contract"]),
        "--parent-database", str(world["parent_db"]), "--evidence-source", str(work / "alias-ev"),
        "--output-root", str(base / "canonical" / ALIAS_POPULATION),
        "--manifest-root", str(base / "manifests" / ALIAS_POPULATION)])
    if code != 0:
        raise AssertionError(f"alias fixture build refused: {err}")
    return {"contract": contract, "anchors": anchors, "built": built,
            "database": Path(built["database"]["data_dir"]) / ALIAS_DB_NAME}


# --------------------------------------------------------------------------------------------- evidence

class Wrap:
    """A reactive-state wrapper in a devalue payload (``["ShallowReactive", index]``)."""

    def __init__(self, name: str, value: Any) -> None:
        self.name, self.value = name, value


def devalue(root: Any) -> list[Any]:
    """A devalue payload: one array whose objects and arrays hold indexes into it."""
    data: list[Any] = []

    def add(value: Any) -> int:
        index = len(data)
        data.append(None)
        if isinstance(value, Wrap):
            data[index] = [value.name, add(value.value)]
        elif isinstance(value, dict):
            data[index] = {k: add(v) for k, v in value.items()}
        elif isinstance(value, list):
            data[index] = [add(v) for v in value]
        else:
            data[index] = value
        return index
    add(root)
    return data


def event(date: str, opponent: str, indicator: str | None, *, site: str | None = None, facility: str | None = None,
          location: str | None = None, neutral_home: bool = False, tournament: str | None = None,
          at_vs: str = "vs") -> dict[str, Any]:
    return {"id": int(date.replace("-", "")) % 100000, "date": f"{date}T18:00:00", "location": location,
            "location_indicator": indicator, "neutral_hometeam": neutral_home, "at_vs": at_vs,
            "opponent": {"title": opponent, "website": site},
            "facility": {"title": facility} if facility else None,
            "tournament": {"title": tournament} if tournament else None}


def schedule_page(org: str, season: int, games: list[dict[str, Any]], *, widget: list[dict[str, Any]] | None = None,
                  other_sport: list[dict[str, Any]] | None = None) -> bytes:
    """A synthetic official season schedule page holding a devalue (Nuxt) payload."""
    record = {"id": 1, "title": f"{season} Football Schedule", "school_name": TEAMS[org][0],
              "season": {"id": 2, "title": str(season)}, "games": games}
    schedules = {f"schedules-football,{season}": record}
    if other_sport:
        schedules[f"schedules-basketball,{season}"] = {"id": 3, "title": "Basketball",
                                                       "season": {"id": 4, "title": str(season)}, "games": other_sport}
    root = {"pinia": Wrap("ShallowReactive", {"schedule": {"schedules": schedules, "nextEvents": widget or []}})}
    text = ("<!DOCTYPE html><html lang=\"en\"><head><title>" + f"{season} Football Schedule</title></head><body>"
            "<script type=\"application/json\" id=\"__NUXT_DATA__\" data-ssr=\"true\">"
            + json.dumps(devalue(root), separators=(",", ":"), ensure_ascii=False) + "</script></body></html>")
    return text.encode("utf-8")


def classic_page(org: str, season: int, games: list[dict[str, Any]], title: str | None = None) -> bytes:
    """A synthetic classic (server-rendered) official season schedule page: one game <li> per game with its nested
    link list, plus a current-season ld+json widget that must never be read."""
    items = []
    for g in games:
        side = {"sidearm-schedule-away-game": "away"}.get(g["token"], "home")
        spans = "".join(f"<span>{s}</span>" for s in g.get("spans", []))
        href = f' href="{g["site"]}"' if g.get("site") else ""
        items.append(
            f'<li class="sidearm-schedule-game {g["token"]} sidearm-schedule-game-completed" data-game-id="1">'
            f'<div class="sidearm-schedule-game-opponent-date flex-item-1"><span>{g["date"]}</span><span>7:00 PM</span>'
            f'</div><span class="sidearm-schedule-game-conference-vs"><span class="sidearm-schedule-game-{side}">'
            f'{g.get("at_vs", "vs")}</span></span><div class="sidearm-schedule-game-opponent-name">'
            f'<a{href} target="_blank">{g["opponent"]}</a></div><ul class="noprint">'
            f'<li class="sidearm-schedule-game-links-boxscore"><a href="/box">Box Score</a></li></ul>'
            f'<div class="sidearm-schedule-game-location">{spans}</div></li>')
    widget = json.dumps([{"@type": "SportsEvent", "name": "Vs Elsewhere", "startDate": f"{season + 1}-10-05T18:00:00",
                          "location": {"name": "Neutral Dome"}}])
    text = (f"<!DOCTYPE html><html><head><title>{title or f'{season} Football Schedule - {TEAMS[org][0]}'}</title>"
            f'<script type="application/ld+json">{widget}</script></head><body><ul class="sidearm-schedule-games">'
            + "".join(items) + "</ul></body></html>")
    return text.encode("utf-8")


def wmt_page(org: str, season: int, games: list[dict[str, Any]], title: str | None = None) -> bytes:
    """A synthetic WMT schedule page: one server-rendered event element per game, the venue designation on its date
    element, an offset datetime, the divider, the opponent name and a 'City / Facility' location, plus a schema-org
    graph (never read)."""
    items = []
    for g in games:
        away = g["venue"] == "away"
        items.append(
            f'<div class="schedule-event-item{" schedule-event-item--away" if away else ""}" data-aos="fade-up">'
            f'<div class="schedule-event-item__top"><div class="schedule-event-date schedule-event-date--venue-'
            f'{g["venue"]}"><div class="schedule-event-date__items-wrapper"><strong class="schedule-event-date__time">'
            f'<time datetime="{g["datetime"]}" class="schedule-event-date__weekday">Sat</time>'
            f'<time datetime="{g["datetime"]}" class="schedule-event-date__day">Day</time></strong></div></div>'
            f'<div class="schedule-event-item__content"><div class="schedule-event-item__teams">'
            f'<strong class="schedule-event-item__divider">{"at" if away else "vs."}</strong>'
            f'<div class="schedule-event-item__team-content"><!----><strong class="schedule-event-item__opponent-name">'
            f'{g["opponent"]}</strong></div></div><div class="schedule-event-item__location">'
            f'<span class="schedule-event-location"><!--[-->{g["location"]}<!--]--></span></div></div></div>'
            f'<div class="schedule-event-item__bottom"><a href="/boxscore/1">Box Score</a></div></div>')
    graph = json.dumps({"@graph": [{"@type": "SportsEvent", "startDate": f"{season}-10-05T17:00:00Z",
                                    "location": {"name": "Neutral Dome"}}]})
    text = (f"<!DOCTYPE html><html><head><title>{title or f'{season} Football Schedule - {TEAMS[org][0]}'}</title>"
            f'<script type="application/ld+json">{graph}</script></head><body><div class="schedule">'
            + "".join(items) + "</div></body></html>")
    return text.encode("utf-8")


def plain_page(season: int) -> bytes:
    """An official page in a structure no declared schema admits (it is examined and reported, never unavailable)."""
    return (f"<!DOCTYPE html><html><body><h1>{season} Football</h1><table><tr><td>Jan 19</td><td>vs Lakefront</td>"
            f"<td>Metro Dome</td></tr></table></body></html>").encode("utf-8")


def directory() -> bytes:
    rows = [{"orgId": int(org), "nameOfficial": name, "athleticWebUrl": url, "division": 1}
            for org, (name, url) in sorted(INSTITUTIONS.items())]
    rows.append({"orgId": 999, "nameOfficial": "Elsewhere College", "athleticWebUrl": "elsewhere.example",
                 "division": 1})
    return json.dumps(rows, separators=(",", ":")).encode("utf-8")


def schedule_url(org: str, season: int, www: bool = False) -> str:
    return f"https://{'www.' if www else ''}{HOSTS[org]}/sports/football/schedule/{season}"


def site(org: str) -> str:
    return f"https://{HOSTS[org]}/"


def pages() -> list[tuple[str, int, bytes, bool]]:
    """(org, season, body, redirected from www) for every retained schedule document of the world."""
    return [
        ("811", 2024, schedule_page("811", 2024, [
            event("2024-09-07", "Prairie", "H", site=site("812"), facility="Lakefront Temporary Field",
                  location="Lakeside, ST"),
            event("2024-11-02", "Prairie State", "H", facility="Lakefront Stadium", location="Lakeside, ST")],
            widget=[event("2024-09-07", "Prairie", "N", site=site("812"), facility="Neutral Dome")],
            other_sport=[event("2024-09-07", "Prairie", "N", site=site("812"))]), False),
        ("812", 2024, schedule_page("812", 2024, [
            event("2024-09-07", "Lakefront", "A", facility="Lakefront Temporary Field", at_vs="at"),
            event("2024-11-02", "Lakefront", "A", facility="Lakefront Stadium", at_vs="at")]), False),
        ("813", 2024, schedule_page("813", 2024, [
            event("2024-09-14", "Canyon A&M", "N", facility="Metro Dome", location="Metro City, ST",
                  tournament="Metro Classic"),
            event("2024-12-21", "Summit", "N", site=site("816"), facility="Summit Stadium", neutral_home=True,
                  tournament="Lake Bowl")]), False),
        ("814", 2024, schedule_page("814", 2024, [
            event("2024-09-14", "Harbor Tech", "N", site=site("813"), facility="Metro Dome", neutral_home=True,
                  location="Metro City, ST", tournament="Metro Classic")]), False),
        ("815", 2024, classic_page("815", 2024, [
            {"date": "Oct 5 (Sat)", "token": "sidearm-schedule-home-game", "opponent": "Summit", "site": site("816"),
             "spans": ["Delta, ST", "Delta Field"]}]), False),
        ("816", 2024, wmt_page("816", 2024, [
            {"venue": "neutral", "datetime": "2024-10-05T13:00:00.000-05:00", "opponent": "Delta",
             "location": "Delta, ST / Delta Field"},
            {"venue": "neutral", "datetime": "2024-12-21T11:00:00.000-06:00", "opponent": "#18 Harbor Tech",
             "location": "Summit City, ST / Summit Stadium"}]), True),
        ("811", 2025, schedule_page("811", 2025, [
            event("2025-10-04", "Harbor Tech", None, site=site("813"), facility="Lakefront Temporary Field",
                  tournament="Lakefront Classic"),
            event("2026-01-19", "Canyon A&M", "N", site=site("814"), facility="Metro Dome", neutral_home=True,
                  tournament="National Final")]), False),
        ("814", 2025, plain_page(2025), False),
        ("813", 2025, schedule_page("813", 2025, [
            event("2025-10-03", "Lakefront", "A", site=site("811"), facility="Lakefront Temporary Field",
                  at_vs="at")]), False),
        ("815", 2025, schedule_page("815", 2025, [
            event("2025-09-13", "Summit", "H", site=site("816"), facility="Delta Field")]), False),
    ]


def _gz(data: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as gz:
        gz.write(data)
    return buffer.getvalue()


def _instant(n: int) -> str:
    return f"2026-10-10T02:{n // 60:02d}:{n % 60:02d}Z"


def evidence() -> dict[str, Any]:
    """The sources document and document bodies of the tiny world: the NCAA directory, every schedule document with its
    attempt, and one denied attempt without a document."""
    bodies: dict[str, bytes] = {}
    documents: dict[str, dict[str, Any]] = {}
    attempts: list[dict[str, Any]] = []
    clock = [0]

    def retain(request_id: str, role: str, org: str | None, season: int | None, urls: list[str], body: bytes,
               media_type: str) -> None:
        sha = hashlib.sha256(body).hexdigest()
        hops = []
        for i, url in enumerate(urls):
            clock[0] += 1
            last = i == len(urls) - 1
            hops.append({"url": url, "status": 200 if last else 301, "location": None if last else urls[i + 1],
                         "retrieved_at": _instant(clock[0]), "body_sha256": sha if last else hashlib.sha256(b"").hexdigest(),
                         "body_bytes": len(body) if last else 0, "error": None})
        attempts.append({"request_id": request_id, "role": role, "org_id": org, "season": season,
                         "request_url": urls[0], "outcome": "RETAINED_200", "acquisition": ACQUISITION, "hops": hops})
        bodies[sha] = body
        documents[sha] = {"sha256": sha, "file": sha + ".gz", "bytes": len(body), "media_type": media_type,
                          "role": role, "org_id": org, "season": season, "request_url": urls[0], "final_url": urls[-1],
                          "hops": [{"url": h["url"], "status": h["status"], "location": h["location"]} for h in hops],
                          "http_status": 200, "retrieved_at": hops[-1]["retrieved_at"], "acquisition": ACQUISITION}
    retain("C49-P01-R01", "NCAA_MEMBER_DIRECTORY", None, None, [DIRECTORY_URL], directory(), "application/json")
    for number, (org, season, body, www) in enumerate(pages(), 1):
        urls = [schedule_url(org, season, True), schedule_url(org, season)] if www else [schedule_url(org, season)]
        retain(f"C49-P02-R{number:02d}", "OFFICIAL_SEASON_SCHEDULE", org, season, urls, body, "text/html")
    clock[0] += 1
    denied = b"<html><body>Access denied</body></html>"
    attempts.append({"request_id": "C49-P02-R99", "role": "OFFICIAL_SEASON_SCHEDULE", "org_id": "812", "season": 2025,
                     "request_url": schedule_url("812", 2025), "outcome": "HOST_STOPPED_HTTP_403",
                     "acquisition": ACQUISITION,
                     "hops": [{"url": schedule_url("812", 2025), "status": 403, "location": None,
                               "retrieved_at": _instant(clock[0]), "body_sha256": hashlib.sha256(denied).hexdigest(),
                               "body_bytes": len(denied), "error": None}]})
    attempts.sort(key=lambda a: a["request_id"])
    sources = {"schema": query.SITE_SOURCES_SCHEMA, "population": POPULATION,
               "documents": [documents[sha] for sha in sorted(documents)], "attempts": attempts}
    return {"sources": sources, "bodies": bodies}


def write_evidence(directory_path: Path, ev: dict[str, Any]) -> dict[str, str]:
    """The evidence source directory (create-only): the sources document and one gzip body per document."""
    directory_path.mkdir(parents=True, exist_ok=False)
    data = (json.dumps(ev["sources"], indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    (directory_path / query.SITE_SOURCES_FILE).write_bytes(data)
    for doc in ev["sources"]["documents"]:
        (directory_path / doc["file"]).write_bytes(_gz(ev["bodies"][doc["sha256"]]))
    outputs = {p.name: afx.sha(p) for p in sorted(directory_path.iterdir())}
    identity = hashlib.sha256(query.canonical_json_bytes(
        query.site_bundle_document(outputs[query.SITE_SOURCES_FILE], outputs))).hexdigest()
    return {"bundle_identity": identity, "sources_sha256": outputs[query.SITE_SOURCES_FILE]}


def site_contract(path: Path, alias: dict[str, Any], pins: dict[str, str], keys: list[str],
                  **overrides: Any) -> dict[str, Any]:
    """A site-evidence contract over this world (written to ``path``) and the anchors it binds."""
    predecessor = {"population_id": ALIAS_POPULATION, "contract_sha256": alias["anchors"]["contract_sha256"],
                   "contract_id": alias["anchors"]["contract_id"], "content_identity": alias["built"]["content_identity"],
                   "database_identity": alias["built"]["database_identity"]}
    anchors = {"contract_sha256": None, "contract_id": "BAT-721-NATIONAL-SITE-EVIDENCE-2024-2025-V1",
               "predecessor": predecessor, "universe": {"keys": list(keys)}, "evidence": pins}
    contract = {"schema_version": "1.0.0", "contract_id": anchors["contract_id"], "jira_key": "BAT-721",
                "cycle_number": 49, "attempt_number": 1, "population_id": POPULATION, "seasons": [2024, 2025],
                "predecessor": predecessor, "universe": {"keys": list(keys)}, "evidence": pins,
                "labels": query.SITE_LABELS, "parameters": query.SITE_PARAMETERS,
                "content_scope": query.site_scope(anchors)}
    contract.update(overrides)
    path.write_text(json.dumps(contract, indent=1, ensure_ascii=False), encoding="utf-8")
    anchors["contract_sha256"] = afx.sha(path)
    anchors["contract_id"] = contract["contract_id"]
    return anchors


load_module = afx.load_module
run_builder = afx.run_builder
build_v1 = afx.build_v1
sha = afx.sha
