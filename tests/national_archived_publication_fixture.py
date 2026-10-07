"""Synthetic archive world for the BAT-713 archived-publication tests (Cycle #41 TP41-A01). Not a test module.

The parent is the synthetic source-time database built by ``national_source_time_fixture`` with the accepted BAT-712
producer. On top of it this module writes a six-key synthetic 2019 tranche, manager-style source bindings, a retained
route control (qualification document, raw receipt and archived page bytes) and archived game pages that copy the
structure of the 2019 ESPN game page (main ``custom-nav`` element, team blocks, scores, status, game information and
``espn.gamepackage`` assignments) next to a decoy global scoreboard that repeats the requested game. A fake archive
transport answers availability and replay requests from per-key scenarios, so the capture stage, its limits, retries,
redirect refusals and journal run offline. Every value here is fictional; nothing is real evidence.
"""
from __future__ import annotations

import contextlib
import copy
import datetime as dt
import gzip
import hashlib
import io
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import national_source_time_fixture as stfx  # noqa: E402

CONTRACT_PATH = ROOT / "configs" / "national_archived_publication_2019_contract_v1_2.json"
PREDECESSOR_CONTRACT_PATH = ROOT / "configs" / "national_archived_publication_2019_contract.json"
V1_1_CONTRACT_PATH = ROOT / "configs" / "national_archived_publication_2019_contract_v1_1.json"
BUILDER_PATH = ROOT / "tools" / "build_national_archived_publication.py"
VALIDATOR_PATH = ROOT / "tools" / "validate_national_archived_publication.py"
#: synthetic tranche: (contest key, selection role, stratum); ncaa:1003 is the retained route control
TRANCHE = [("ncaa:1001", "STRATIFIED_COHORT", "FBS-FCS-EARLY"), ("ncaa:1002", "STRATIFIED_COHORT", "FBS-FBS-EARLY"),
           ("ncaa:1004", "STRATIFIED_COHORT", "FBS-FBS-EARLY"), ("ncaa:1005", "STRATIFIED_COHORT", "FBS-FBS-MIDDLE"),
           ("ncaa:1007", "STRATIFIED_COHORT", "FBS-FBS-MIDDLE"),
           ("ncaa:1003", "SEPARATE_PREQUALIFIED_ROUTE_CONTROL", "POSITIVE_CONTROL")]
#: ESPN team id actually shown on the page for each synthetic org (Echo, org 5, shows another number: namespace case)
ESPN_IDS = {"1": "101", "2": "102", "3": "103", "4": "104", "5": "99105", "6": "106"}
CONTROL_TS = "20190908013000"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, data: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def builder() -> Any:
    return stfx.load_tool(BUILDER_PATH, "bas_archived_publication_builder")


def validator() -> Any:
    return stfx.load_tool(VALIDATOR_PATH, "bas_archived_publication_validator")


def http_date(ts14: str, plus_seconds: int = 0) -> str:
    when = dt.datetime.strptime(ts14, "%Y%m%d%H%M%S").replace(tzinfo=dt.timezone.utc) + dt.timedelta(
        seconds=plus_seconds)
    return when.strftime("%a, %d %b %Y %H:%M:%S GMT")


def game_url(game: str, scheme: str = "https") -> str:
    return f"{scheme}://www.espn.com/college-football/game/_/gameId/{game}"


def espn_page(game: str, home: str, away: str, home_score: Any, away_score: Any, *, status: str = "post",
              detail: str = "Final", kickoff: str = "2019-08-31T23:30Z", nav_game: str | None = None,
              js_game: str | None = None, info_date: str | None = None, home_href: str | None = None,
              home_name: str | None = None, away_name: str | None = None,
              decoy: list[tuple[str, str, str]] | None = None, extra_script: str = "") -> bytes:
    """A 2019-style archived ESPN game page; ``decoy`` games fill a global scoreboard that the extractor must ignore.
    Each team block shows its ESPN location name (``home_name``/``away_name``, default ``T<id>``)."""
    def team(side: str, team_id: str, href_id: str, score: Any, name: str | None) -> str:
        score_div = "" if score is None else f'<div class="score-container"><div class="score icon-font-after">' \
                                             f'{score}</div></div>'
        return (f'<div class="team {side}"><div class="team__content"><div class="team-container">'
                f'<div class="team-info"><div class="team-info-wrapper"><span class="rank">9</span>'
                f'<a name="&amp;lpos=ncf:game:game:clubhouse:team" class="team-name" '
                f'href="/college-football/team/_/id/{href_id}/team-{href_id}"><span class="long-name">'
                f'{name or "T" + team_id}</span><span class="short-name">Fixture</span></a></div>'
                f'<div class="record">1-0</div></div><div class="team-info-logo"><div class="logo">'
                f'<a href="/college-football/team/_/id/{href_id}/team-{href_id}"><img class="team-logo" '
                f'src="https://a.example.invalid/{href_id}.png"/></a></div></div></div>{score_div}</div></div>')
    board = "".join(f'<a href="/college-football/game/_/gameId/{g}"><div class="score">{s}</div>'
                    f'<span class="status-detail">Final</span><span>{label}</span></a>' for g, s, label in decoy or [])
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f'<title>T{away} vs. T{home} - Game Summary - ESPN</title>\n'
        f'<link rel="canonical" href="https://www.espn.com/college-football/game?gameId={game}" /></head>\n<body>\n'
        f'<section id="global-scoreboard"><div class="scoreboard-content">{board}</div></section>\n'
        f'<section id="pane-main" class="{status} details-header">\n'
        f'<div id="custom-nav" data-id="gamepackage-{nav_game or game}"><div id="gamepackage-header-wrap">'
        f'<div id="gamepackage-matchup-wrap"><header class="game-strip game-package college-football {status}">'
        f'<div class="game-details header">FIXTURE KICKOFF</div><div class="competitors">'
        + team("away", away, away, away_score, away_name)
        + f'<div class="game-status"><span class="game-time status-detail">{detail}</span></div>'
        + team("home", home, home_href or home, home_score, home_name)
        + '</div></header></div></div></div>\n</section>\n<section id="main-container">'
        '<div id="gamepackage-game-information" data-module="gameInformation"><article class="sub-module '
        'game-information"><div class="game-field"><div class="game-details"><div class="game-location">Fixture Field'
        '</div><div class="game-date-time">'
        f'<span data-date="{info_date or kickoff}" data-behavior="date_time"><span class="game-date"></span></span>'
        '</div></div></div></article></div>\n<div class="top-stories"><span class="timestamp" '
        'data-behavior="date_time" data-date="2019-09-01T03:57:34Z">8/31/2019</span></div></section>\n'
        '<script>\n'
        f'espn.gamepackage.gameId = "{js_game or game}";\nespn.gamepackage.type = "game";\n'
        f'espn.gamepackage.timestamp = "{kickoff}";\nespn.gamepackage.status = "{status}";\n'
        f'espn.gamepackage.awayTeamId = "{away}";\nespn.gamepackage.homeTeamId = "{home}";\n{extra_script}'
        '</script>\n'
        f'<script>window.scoreboardData = {{"events":[{{"id":"{game}","score":"{home_score}-{away_score}"}}]}};'
        '</script>\n</body></html>\n').encode("utf-8")


def replay_headers(ts: str, original: str, *, memento: str | None = "DEFAULT", origin_date: str | None = "DEFAULT",
                   link_original: str | None = None, content_type: str = "text/html;charset=UTF-8") -> list[list[str]]:
    headers = [["Server", "nginx"], ["Content-Type", content_type]]
    if origin_date is not None:
        headers.append(["x-archive-orig-date", http_date(ts) if origin_date == "DEFAULT" else origin_date])
    headers.append(["x-archive-orig-set-cookie", "edition=fixture; path=/"])
    if memento is not None:
        headers.append(["memento-datetime", http_date(ts) if memento == "DEFAULT" else memento])
    headers.append(["link", f'<{link_original or original}>; rel="original", '
                            f'<https://web.archive.org/web/timemap/link/{original}>; rel="timemap"'])
    headers.append(["x-archive-src", "fixture-crawl/IA-FIXTURE.warc.gz"])
    headers.append(["set-cookie", "wb-p-SERVER=fixture; path=/"])
    return headers


class FakeArchive:
    """Offline availability/replay answers. ``meta`` maps (game, probe ts) -> closest timestamp, ``None`` (no
    capture), an int HTTP status or a callable; ``replay`` maps (ts, game) -> (status, headers, body) or a callable."""

    def __init__(self) -> None:
        self.meta: dict[tuple[str, str], Any] = {}
        self.replay: dict[tuple[str, str], Any] = {}
        self.calls: list[str] = []

    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> Any:
        build = builder()
        self.calls.append(url)
        parts = urllib.parse.urlsplit(url)
        if parts.hostname == "archive.org":
            query = urllib.parse.parse_qs(parts.query)
            original, ts = query["url"][0], query["timestamp"][0]
            game = original.rsplit("/", 1)[1]
            answer = self.meta.get((game, ts), self.meta.get((game, "*")))
            if callable(answer):
                answer = answer(url)
            if isinstance(answer, int):
                return build.Response(answer, "fixture", [["Retry-After", "2"]] if answer == 429 else [], b"busy")
            if answer is None:
                body = {"url": original, "archived_snapshots": {}, "timestamp": ts}
            else:
                closest_ts, status = (answer, "200") if isinstance(answer, str) else answer
                body = {"url": original, "archived_snapshots": {"closest": {
                    "status": status, "available": True, "timestamp": closest_ts,
                    "url": f"http://web.archive.org/web/{closest_ts}/{original}"}}, "timestamp": ts}
            return build.Response(200, "OK", [["Content-Type", "application/json"]], json.dumps(body).encode())
        replay = build.replay_parts(url)
        if replay is None:
            raise AssertionError(f"fixture transport saw a non-archive URL {url}")
        game = replay[1].rsplit("/", 1)[1]
        answer = self.replay.get((replay[0], game))
        if callable(answer):
            answer = answer(url)
        if answer is None:
            return build.Response(404, "Not Found", [["Content-Type", "text/html"]], b"<html>not archived</html>")
        status, headers, body = answer
        return build.Response(status, "fixture", headers, body)


def tranche_rows(st_db: Path, tranche: list[tuple[str, str, str]] | None = None) -> list[dict[str, Any]]:
    import sqlite3  # noqa: PLC0415
    import zlib  # noqa: PLC0415

    conn = sqlite3.connect(Path(st_db).resolve().as_uri() + "?mode=ro", uri=True)
    rows = []
    try:
        for key, role, stratum in tranche or TRANCHE:
            record_text, blob = conn.execute("SELECT record, assertions FROM contests WHERE contest_key = ?",
                                             (key,)).fetchone()
            record = json.loads(record_text)
            values = {}
            for line in zlib.decompress(blob).decode("utf-8").splitlines():
                item = json.loads(line)
                values[item["field"]] = item["parent_value"]
            game = record["cfbd_game_id"]["value"]
            probe = record["contest_date"].replace("-", "") + "235959"
            rows.append({"contest_key": key, "season": record["season"], "contest_date": record["contest_date"],
                         "classification_pair": "FBS-FBS", "a_key": record["a_key"], "b_key": record["b_key"],
                         "a_team": record["a_team_name"], "b_team": record["b_team_name"],
                         "a_points": values["a_points"], "b_points": values["b_points"], "roles": record["roles"],
                         "cfbd_game_id": record["cfbd_game_id"], "selection_role": role, "stratum": stratum,
                         "rank": None if role != "STRATIFIED_COHORT" else sha(key.encode()),
                         "candidate_espn_url": game_url(game), "namespace_limit": "fixture",
                         "metadata_probe_timestamp": probe, "_record": record})
    finally:
        conn.close()
    return rows


def side_ids(record: dict[str, Any]) -> tuple[str, str]:
    """(home ESPN id, away ESPN id) for a synthetic contest from its parent site (HOME_B puts b at home)."""
    a_org, b_org = record["a_org_id"], record["b_org_id"]
    if record["parent_site"] == "HOME_B":
        return ESPN_IDS[b_org], ESPN_IDS[a_org]
    return ESPN_IDS[a_org], ESPN_IDS[b_org]


def side_names(record: dict[str, Any]) -> tuple[str, str]:
    """(home, away) documented team names of a synthetic contest (the parent's CFBD route and NCAA names)."""
    if record["parent_site"] == "HOME_B":
        return record["b_team_name"], record["a_team_name"]
    return record["a_team_name"], record["b_team_name"]


def page_for(row: dict[str, Any], *, status: str = "post", detail: str = "Final", swap_scores: bool = False,
             ids: tuple[str, str] | None = None, **kw: Any) -> bytes:
    """``ids`` overrides the (home, away) ESPN team ids shown by both the JS assignments and the team-name hrefs."""
    record = row["_record"]
    home, away = ids or side_ids(record)
    names = side_names(record)
    kw.setdefault("home_name", names[0])
    kw.setdefault("away_name", names[1])
    home_is_a = record["parent_site"] != "HOME_B"
    home_score, away_score = (row["a_points"], row["b_points"]) if home_is_a else (row["b_points"], row["a_points"])
    if swap_scores:
        home_score, away_score = away_score, home_score
    if status != "post":
        home_score = away_score = None
    game = row["cfbd_game_id"]["value"]
    decoy = [(game, f"{row['a_points']}", "decoy repeat of the requested game"), ("990001", "77", "other game")]
    kw.setdefault("kickoff", row["contest_date"] + "T23:30Z")
    return espn_page(game, home, away, home_score, away_score, status=status, detail=detail, decoy=decoy, **kw)


def build_world(base: Path, scenarios: dict[str, Callable[[FakeArchive, dict[str, Any]], None]] | None = None,
                tranche: list[tuple[str, str, str]] | None = None) -> dict[str, Any]:
    """Source-time parent, synthetic tranche/bindings/control and a fake archive for the six tranche keys (or the
    given subset ``tranche``, as the BAT-715 expansion fixture uses; default scenarios cover only its keys)."""
    base = Path(base)
    st_world = stfx.build_world(base / "w")
    code, st_result, err = stfx.run_build(st_world, base / "o")
    assert code == 0, err
    st_db = stfx.database_path(st_result)
    rows = tranche_rows(st_db, tranche)
    prep = base / "p"
    public = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    tranche = {"cycle_number": 41, "attempt_number": 1, "state": "FIXTURE", "selection_revision": "fixture",
               "parent_source_time_content": st_result["content_identity"],
               "parent_source_time_database": st_result["database_identity"], "expected_universe_2019": 6,
               "selection": "fixture", "strata": {}, "selected": public, "count": len(public),
               "selection_not_national_completeness": True, "unselected_remain": "fixture"}
    tranche_path = write(prep / "ARCHIVE_TRANCHE.json", json.dumps(tranche, indent=2).encode("utf-8"))
    control_row = next(r for r in rows if r["selection_role"] == "SEPARATE_PREQUALIFIED_ROUTE_CONTROL")
    control_game = control_row["cfbd_game_id"]["value"]
    control_page = page_for(control_row)
    control_page_path = write(prep / "preflight" / f"archive-positive-{CONTROL_TS}.html", control_page)
    original = game_url(control_game)
    control_url = f"https://web.archive.org/web/{CONTROL_TS}id_/{original}"
    control_headers = {k: v for k, v in replay_headers(CONTROL_TS, original)}
    raw_receipt = {"cycle_number": 40, "attempt_number": 1, "observed_at": "2026-10-03T02:02:06.567721+00:00",
                   "url": control_url, "final_url": control_url, "status": 200, "headers": control_headers,
                   "capture": CONTROL_TS, "path": str(control_page_path), "sha256": sha(control_page),
                   "bytes": len(control_page)}
    raw_receipt_path = write(prep / "preflight" / "ARCHIVE_POSITIVE_RAW.json",
                             json.dumps(raw_receipt, indent=2).encode("utf-8"))
    capture_utc = dt.datetime.strptime(CONTROL_TS, "%Y%m%d%H%M%S").strftime("%Y-%m-%dT%H:%M:%SZ")
    route = {"cycle_number": 41, "attempt_number": 1, "state": "FIXTURE_ROUTE_CONTROL",
             "contest_key": control_row["contest_key"], "archive_capture_utc": capture_utc,
             "conservative_upper_bound": capture_utc[:-1] + ".999999Z", "original_url": original,
             "archive_receipt": dict(raw_receipt, path=str(control_page_path))}
    route_path = write(prep / "ARCHIVE_ROUTE_QUALIFICATION.json", json.dumps(route, indent=2).encode("utf-8"))
    bindings = {"cycle_number": 41, "attempt_number": 1,
                "source_time_database": {"path": str(st_db), "sha256": st_result["database_sha256"],
                                         "identity": st_result["database_identity"]},
                "tranche": {"path": str(tranche_path), "sha256": sha(tranche_path.read_bytes()), "count": len(rows)},
                "control": {"path": str(route_path), "sha256": sha(route_path.read_bytes())}}
    bindings_path = write(prep / "INPUT_BINDINGS.json", json.dumps(bindings, indent=2).encode("utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["parent_binding"]["source_time"].update(
        contract_sha256=st_result["contract_sha256"], content_identity=st_result["content_identity"],
        database_identity=st_result["database_identity"], sqlite_sha256=st_result["database_sha256"])
    contract["parent_binding"]["source_bindings"]["sha256"] = sha(bindings_path.read_bytes())
    contract["parent_binding"]["route_control"].update(
        sha256=sha(route_path.read_bytes()), raw_receipt_sha256=sha(raw_receipt_path.read_bytes()),
        raw_payload=f"preflight/archive-positive-{CONTROL_TS}.html", raw_payload_sha256=sha(control_page),
        raw_payload_bytes=len(control_page), contest_key=control_row["contest_key"],
        archive_capture_utc=route["archive_capture_utc"], conservative_upper_bound=route["conservative_upper_bound"])
    contract["scope"].update(
        tranche_sha256=sha(tranche_path.read_bytes()), tranche_count=len(rows), stratified_count=len(rows) - 1,
        control_contest_key=control_row["contest_key"], expected_universe_2019=6, strata={},
        keys=[{"contest_key": r["contest_key"], "selection_role": r["selection_role"], "stratum": r["stratum"],
               "candidate_url": r["candidate_espn_url"], "game_id_literal": r["cfbd_game_id"]["value"],
               "probe_1_timestamp": r["metadata_probe_timestamp"]} for r in rows])
    contract_path = write(prep / "contract.json", (json.dumps(contract, indent=2) + "\n").encode("utf-8"))
    archive = FakeArchive()
    by_key = {r["contest_key"]: r for r in rows}
    default_scenarios(archive, by_key)
    for key, scenario in (scenarios or {}).items():
        scenario(archive, by_key[key])
    return {"base": base, "st_world": st_world, "st_result": st_result, "st_db": st_db, "rows": rows,
            "by_key": by_key, "tranche": tranche_path, "bindings": bindings_path, "route": route_path,
            "contract": contract_path, "contract_doc": contract, "archive": archive, "control_page": control_page,
            "out": base / "a" / "canonical" / "ap", "manifests": base / "a" / "manifests" / "ap"}


def default_scenarios(archive: FakeArchive, by_key: dict[str, dict[str, Any]]) -> None:
    """1001 qualifies fully; 1002 is first archived before kickoff then after the game; 1004 is a pre-game version
    whose Echo block shows an ESPN team id (99105) that differs from Echo's CFBD id (105), mapped only through the
    documented names, CFBD role and date; 1005 has no capture; 1007 meets a 503 then a redirect to the live host."""
    def set_capture(row: dict[str, Any], probe: str, ts: str, page: bytes) -> None:
        game = row["cfbd_game_id"]["value"]
        archive.meta[(game, probe)] = ts
        archive.replay[(ts, game)] = (200, replay_headers(ts, game_url(game)), page)
    if set(by_key) != {key for key, _role, _stratum in TRANCHE}:
        subset_scenarios(archive, by_key, set_capture)
        return
    r1 = by_key["ncaa:1001"]
    set_capture(r1, r1["metadata_probe_timestamp"], "20190901041500", page_for(r1))
    r2 = by_key["ncaa:1002"]
    game2 = r2["cfbd_game_id"]["value"]
    set_capture(r2, r2["metadata_probe_timestamp"], "20190831120000", page_for(r2, status="pre", detail="7:30 PM ET"))
    probe2 = (dt.date.fromisoformat(r2["contest_date"]) + dt.timedelta(days=3)).strftime("%Y%m%d") + "235959"
    archive.meta[(game2, probe2)] = "20190902100000"
    archive.replay[("20190902100000", game2)] = (200, replay_headers("20190902100000", game_url(game2)), page_for(r2))
    r4 = by_key["ncaa:1004"]
    set_capture(r4, r4["metadata_probe_timestamp"], "20190906030000", page_for(r4, status="pre", detail="7:30 PM ET"))
    r5 = by_key["ncaa:1005"]
    archive.meta[(r5["cfbd_game_id"]["value"], "*")] = None
    r7 = by_key["ncaa:1007"]
    game7 = r7["cfbd_game_id"]["value"]
    answers = iter([503, "20190922050000"])
    archive.meta[(game7, r7["metadata_probe_timestamp"])] = lambda url: next(answers)
    archive.replay[("20190922050000", game7)] = (
        302, [["Location", game_url(game7)], ["Content-Type", "text/html"]], b"")


def subset_scenarios(archive: FakeArchive, by_key: dict[str, dict[str, Any]], set_capture: Callable) -> None:
    """The default answers of the keys present in a tranche subset (BAT-715 expansion fixture): 1001 qualifies; 1002
    is archived before kickoff, then after the game at probe 2; 1005 has no capture."""
    if "ncaa:1001" in by_key:
        r1 = by_key["ncaa:1001"]
        set_capture(r1, r1["metadata_probe_timestamp"], "20190901041500", page_for(r1))
    if "ncaa:1002" in by_key:
        r2 = by_key["ncaa:1002"]
        game2 = r2["cfbd_game_id"]["value"]
        set_capture(r2, r2["metadata_probe_timestamp"], "20190831120000",
                    page_for(r2, status="pre", detail="7:30 PM ET"))
        probe2 = (dt.date.fromisoformat(r2["contest_date"]) + dt.timedelta(days=3)).strftime("%Y%m%d") + "235959"
        archive.meta[(game2, probe2)] = "20190902100000"
        archive.replay[("20190902100000", game2)] = (200, replay_headers("20190902100000", game_url(game2)),
                                                     page_for(r2))
    if "ncaa:1005" in by_key:
        archive.meta[(by_key["ncaa:1005"]["cfbd_game_id"]["value"], "*")] = None


def run_capture(world: dict[str, Any], *, transport: Any = None, contract: dict[str, Any] | None = None,
                rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    build = builder()
    contract = contract or world["contract_doc"]
    rows_public = rows or [{k: v for k, v in r.items() if not k.startswith("_")} for r in world["rows"]]
    control = build.verify_control(contract, world["route"])
    clock = {"t": 0.0}
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        clock["t"] += seconds

    def monotonic() -> float:
        clock["t"] += 0.25
        return clock["t"]

    def now() -> str:
        when = dt.datetime(2026, 10, 3, 4, 0, tzinfo=dt.timezone.utc) + dt.timedelta(seconds=clock["t"])
        return when.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    result = build.capture(contract, rows_public, world["out"], control, transport=transport or world["archive"],
                           sleep=sleep, monotonic=monotonic, now=now, audit=False)
    result["slept"] = slept
    return result


def run_build(world: dict[str, Any], *extra: str, out: Path | None = None, manifests: Path | None = None,
              contract: Path | None = None, database: Path | None = None, bindings: Path | None = None,
              tranche: Path | None = None) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract or world["contract"]), "--source-database", str(database or world["st_db"]),
            "--source-bindings", str(bindings or world["bindings"]), "--tranche", str(tranche or world["tranche"]),
            "--output-root", str(out or world["out"]), "--manifest-root", str(manifests or world["manifests"]),
            *extra]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = builder().main(argv)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


def patched_contract(world: dict[str, Any], path: Path, mutate) -> Path:
    contract = copy.deepcopy(world["contract_doc"])
    mutate(contract)
    return write(Path(path), (json.dumps(contract, indent=2) + "\n").encode("utf-8"))


def refusal(stderr: str) -> str | None:
    for line in reversed(stderr.strip().splitlines()):
        try:
            return json.loads(line).get("refused")
        except ValueError:
            continue
    return None


def read_payload(result: dict[str, Any], name: str) -> list[dict[str, Any]]:
    data = gzip.decompress((Path(result["content"]["data_dir"]) / f"{name}.gz").read_bytes())
    return [json.loads(line) for line in data.decode("utf-8").splitlines()]


def database_path(result: dict[str, Any]) -> Path:
    return Path(result["database"]["data_dir"]) / "national_archived_publication.sqlite"


def issued_authority(world: dict[str, Any]) -> Any:
    """The synthetic world's issued authority (its patched contract, exact tranche bytes, its one finalized
    acquisition, parent binding and route control) for in-process registration with
    ``archive.registered_authority``; the console and module fronts serve only the packaged V1.2 authority."""
    from aggie_analytics.national_source_time import archive  # noqa: PLC0415

    contract = world["contract_doc"]
    found = sorted(Path(world["out"]).glob("acquisition/sha256/*/acquisition.json"))
    assert len(found) == 1, found
    route = contract["parent_binding"]["route_control"]
    parent = contract["parent_binding"]["source_time"]
    return archive.IssuedAuthority(
        contract_id=contract["contract_id"], contract_sha256=sha(Path(world["contract"]).read_bytes()),
        tranche_bytes=Path(world["tranche"]).read_bytes(), tranche_sha256=contract["scope"]["tranche_sha256"],
        acquisition_identity=found[0].parent.name,
        parent={"source_time": {k: parent[k] for k in ("content_identity", "contract_sha256", "database_identity",
                                                        "sqlite_sha256")}},
        control={"contest_key": route["contest_key"], "payload_sha256": route["raw_payload_sha256"],
                 "raw_receipt_sha256": route["raw_receipt_sha256"], "route_qualification_sha256": route["sha256"]})


#: ``python -c BOOTSTRAP <authority json> <query argv...>``: registers one synthetic authority in-process, then runs the
#: query module as ``__main__`` exactly as ``python -m`` does (the module-front delegation path).
BOOTSTRAP = ("import json, runpy, sys\n"
             "from aggie_analytics.national_source_time import archive\n"
             "spec = json.loads(sys.argv.pop(1))\n"
             "data = open(spec.pop('tranche_path'), 'rb').read()\n"
             "with archive.registered_authority(archive.IssuedAuthority(tranche_bytes=data, **spec)):\n"
             "    sys.argv[0] = 'aggie_analytics.national_source_time.query'\n"
             "    runpy.run_module('aggie_analytics.national_source_time.query', run_name='__main__', alter_sys=True)\n")


def authority_spec(world: dict[str, Any]) -> str:
    authority = issued_authority(world)
    return json.dumps({"contract_id": authority.contract_id, "contract_sha256": authority.contract_sha256,
                       "tranche_path": str(world["tranche"]), "tranche_sha256": authority.tranche_sha256,
                       "acquisition_identity": authority.acquisition_identity, "parent": authority.parent,
                       "control": authority.control})
