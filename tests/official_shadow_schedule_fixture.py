"""Synthetic fixtures for the BAT-726 official schedule evidence sidecar (no real pages, no network, no real capture).

A schedule world builds a synthetic BAT-725 shadow (the shadow fixture's synthetic preview and capsule, a fixture-only
anchor receipt) over three synthetic events whose teams carry distinctive display, short and location names, and derives
a schedule contract from the committed contract with the fixture shadow's pins and a three-event fixture cohort whose
owner institutions use reserved ``*.example`` host families. Its SHA-256 is the fixture authority tests pass explicitly
(the committed contract SHA-256 and the packaged sidecar profile remain the only defaults). Pages are synthetic copies of
the declared structures (SIDEARM Nuxt season record, SIDEARM text table, WMT list items); the acquisition journal is a
synthetic capture with explicit UTC intervals and monotonic stamps two seconds apart.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
from argparse import Namespace
from pathlib import Path
from typing import Any, Callable

import provider_record_shadow_fixture as sfx

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "configs" / "official_shadow_schedule_20261017_contract.json"
#: Fixture capture instants: after the fixture shadow anchor (2026-10-12T06:30:00Z).
CAPTURE_START = "2026-10-12T18:00:00.000000Z"
SEP = 2_000_000_000

TEAMS = {"9001": ("Fixture Alpha Owls", "Alpha", "Alpha State", "Owls", "ALP"),
         "9002": ("Fixture Beta Hawks", "Beta", "Beta Tech", "Hawks", "BET"),
         "9003": ("Fixture Gamma Lions", "Gamma", "Gamma A&M", "Lions", "GAM"),
         "9004": ("Fixture Delta Wolves", "Delta", "Delta College", "Wolves", "DEL"),
         "9005": ("Fixture Epsilon Bears", "Epsilon", "Epsilon City", "Bears", "EPS"),
         "9006": ("Fixture Zeta Foxes", "Zeta", "Zeta Southern", "Foxes", "ZET")}
#: Owner institutions of the three fixture events (home team -> fixture NCAA row and host).
OWNERS = {"espn:event:900000001": (9101, "University of Alpha", "www.alpha.example"),
          "espn:event:900000002": (9103, "Gamma A&M University", "gamma.example"),
          "espn:event:900000003": (9105, "Epsilon City University", "www.epsilon.example")}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def named_events() -> list[dict[str, Any]]:
    def mutate(events: list[dict[str, Any]]) -> None:
        for event in events:
            for competitor in event["competitions"][0]["competitors"]:
                display, short, location, mascot, abbreviation = TEAMS[competitor["id"]]
                competitor["team"].update(displayName=display, shortDisplayName=short, location=location,
                                          name=mascot, abbreviation=abbreviation)
            event["competitions"][0]["venue"] = {"id": "1", "fullName": f"{event['id'][-1]} Field",
                                                 "address": {"city": "Fixture City", "state": "TX"}}
    return sfx.copy_events(mutate)


# --------------------------------------------------------------------------------------------- pages

def devalue(root: Any) -> list[Any]:
    """A devalue payload (every object member and list item an index into the array; reactive root wrappers)."""
    data: list[Any] = []

    def add(value: Any) -> int:
        index = len(data)
        data.append(None)
        if isinstance(value, dict):
            data[index] = {k: add(v) for k, v in value.items()}
        elif isinstance(value, list):
            data[index] = [add(v) for v in value]
        else:
            data[index] = value
        return index
    data.append(["Reactive", 1])
    add(root)
    return data


def nuxt_game(date: str, time: str, indicator: str, opponent: str, *, tbd: bool = False, location: str = "Here, St.",
              facility: str | None = "Fixture Stadium", result: Any = None) -> dict[str, Any]:
    return {"id": 1, "date": date, "time": time, "tbd": tbd, "location": location, "location_indicator": indicator,
            "neutral_hometeam": None, "at_vs": "vs" if indicator == "H" else "at",
            "opponent": {"id": 2, "title": opponent, "website": "https://opponent.example/"},
            "facility": {"id": 3, "title": facility} if facility else None, "result": result,
            "media": {"tv": "FIXTURE TV", "video": {"label": f"Video for Football vs {opponent} on headline 2026"}}}


def nuxt_script(school: str, games: list[dict[str, Any]], *, season: str = "2026", sport: str = "football") -> str:
    record = {"id": 9, "title": f"{season} Football Schedule", "school_name": school,
              "sport": {"id": 4, "title": "Football", "shortname": sport},
              "season": {"id": 1, "title": season, "startdate": f"{season}-01-01T00:00:00"}, "games": games}
    payload = devalue({"state": {}, "pinia": {"schedule": {"schedules": {f"schedules-{sport},": record},
                                                           "nextEvents": {}}}})
    return ('<script type="application/json" data-nuxt-data="nuxt-app" id="__NUXT_DATA__">' +
            json.dumps(payload) + "</script>")


def text_table(rows: list[tuple[str, str, str, str, str, str]], *, heading: str = "2026 Football Schedule") -> str:
    head = "".join(f"<th class=\"p-2\"> {h} </th>" for h in ("Date", "Time", "At", "Opponent", "Location",
                                                                 "Tournament", "Result"))
    body = "".join("<tr>" + "".join(f"<td class=\"p-2\">{c}</td>" for c in (date, time, f"<span>{at}</span>",
                                                                            opponent, location, "", result))
                   + "</tr>" for date, time, at, opponent, location, result in rows)
    return (f'<div id="scheduleTextPage"><h1 class="py-2">{heading}</h1><table><thead><tr>{head}</tr></thead>'
            f"<tbody><!--[-->{body}<!--]--></tbody></table></div>")


def sidearm_page(school: str, games: list[dict[str, Any]], *, table: list[tuple] | None = None,
                 season: str = "2026", chrome: str = "") -> bytes:
    parts = ["<!DOCTYPE html><html><head><title>Fixture Athletics</title></head><body>", chrome,
             '<main id="main-content">', text_table(table, heading=f"{season} Football Schedule")
             if table is not None else "", "</main>",
             nuxt_script(school, games, season=season), "</body></html>"]
    return "".join(parts).encode("utf-8")


def wmt_item(owner: str, opponent: str, datetime: str, venue: str = "home", *, tba: bool = False,
             location: str = "Fixture City / Fixture Stadium", clock_text: str = "12:00 PM",
             rank: str = "") -> str:
    tba_token = " schedule-event-date--time-tba" if tba else ""
    current = f"<span>{rank}</span> {owner}" if rank else f" {owner}"
    return (f'<div class="schedule-event-item"><div class="schedule-event-item__top"><div class="schedule-event-date'
            f'{tba_token} schedule-event-date--venue-{venue} schedule-event-date--with-time"><strong class="schedule-'
            f'event-date__time"><time datetime="{datetime}" class="schedule-event-date__weekday">Sat</time>'
            f'<time datetime="{datetime}" class="schedule-event-date__day">Oct 17</time><time datetime="{datetime}"'
            f' class="schedule-event-date__clock">{clock_text}</time></strong></div></div><div class="schedule-event-'
            f'item__content"><strong class="schedule-event-default__name schedule-event-default__name--current">'
            f'{current}</strong><strong class="schedule-event-default__name"> {opponent}</strong>'
            f'<div class="schedule-event-item__location"><span class="schedule-event-location">{location}</span>'
            f'</div></div></div>')


def wmt_page(items: list[str], *, heading: str = '<span class="schedule-hero__season">2026</span> Football Schedule',
             table_view: str = "") -> bytes:
    return ("<!DOCTYPE html><html><head><title>2026 Football Schedule - Fixture</title></head><body>"
            f'<h1 class="schedule-hero__title">{heading}</h1>'
            f'<div class="schedule__view-box--active schedule__view-box schedule__view-box--list">{"".join(items)}'
            f'</div><div class="schedule__view-box schedule__view-box--table">{table_view}</div></body></html>'
            ).encode("utf-8")


# --------------------------------------------------------------------------------------------- journal

class Capture:
    """A synthetic acquisition: attempts appended in order with UTC intervals and monotonic stamps."""

    def __init__(self, contract_sha256: str, shadow_identity: str, *, start: str = CAPTURE_START) -> None:
        import datetime as dt  # noqa: PLC0415
        self._dt = dt
        self.moment = dt.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=dt.timezone.utc)
        self.ns = 10 ** 12
        self.seq = 0
        self.lines: list[dict[str, Any]] = [{
            "record": "capture_start", "schema": "BAS-OFFICIAL-SCHEDULE-ACQUISITION-JOURNAL-1", "segment": 1,
            "contract_sha256": contract_sha256, "shadow_identity": shadow_identity, "ceiling": 80,
            "min_spacing_ns": SEP, "max_hops": 5, "max_body_bytes": 12 * 1024 * 1024, "timeout_seconds": 60,
            "user_agent": "BAS-C54-FIXTURE", "request_headers": {}, "started_utc": start}]
        self.bodies: dict[str, bytes] = {}

    def _utc(self) -> str:
        return self.moment.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def attempt(self, event_key: str, logical: str, route: str, hop: int, url: str, status: int | None,
                body: bytes = b"", *, headers: list[list[str]] | None = None, error: str | None = None,
                truncated: bool = False, link_source: dict[str, Any] | None = None, spacing: int = SEP,
                result: bool = True) -> int:
        self.seq += 1
        self.ns += spacing
        self.moment += self._dt.timedelta(seconds=2)
        intent = {"record": "intent", "seq": self.seq, "event_key": event_key, "logical": logical, "route": route,
                  "hop": hop, "url": url, "start_utc": self._utc(), "start_ns": self.ns}
        if link_source is not None:
            intent["link_source"] = link_source
        self.lines.append(intent)
        if result:
            self.moment += self._dt.timedelta(milliseconds=400)
            self.bodies[sha256(body)] = body
            self.lines.append({"record": "result", "seq": self.seq, "status": status,
                               "headers": headers if headers is not None else [["Content-Type", "text/html"]],
                               "body_sha256": sha256(body), "body_bytes": len(body), "truncated": truncated,
                               "error": error, "end_utc": self._utc(), "end_ns": self.ns + 400_000_000})
        return self.seq

    def decision(self, event_key: str, logical: str, route: str, url: str | None, decision: str,
                 detail: str = "") -> None:
        self.lines.append({"record": "decision", "event_key": event_key, "logical": logical, "route": route,
                           "url": url, "decision": decision, "detail": detail})

    def journal_bytes(self, *, end: bool = True) -> bytes:
        lines = list(self.lines)
        if end:
            lines.append({"record": "capture_end", "segment": 1, "attempts": self.seq, "ended_utc": self._utc()})
        return b"".join(json.dumps(line, sort_keys=True).encode("utf-8") + b"\n" for line in lines)

    def write(self, directory: Path, *, end: bool = True) -> Path:
        directory = Path(directory)
        (directory / "bodies").mkdir(parents=True, exist_ok=True)
        (directory / "journal-01.jsonl").write_bytes(self.journal_bytes(end=end))
        for digest, body in self.bodies.items():
            (directory / "bodies" / f"{digest}.gz").write_bytes(gzip.compress(body, mtime=0))
        return directory


# --------------------------------------------------------------------------------------------- world

class ScheduleWorld:
    """One synthetic shadow plus the schedule contract that pins it and its three-event fixture cohort."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.shadow_world = sfx.ShadowWorld(self.root / "sw", named_events())
        built = self.shadow_world.build(self.root / "sb")
        self.shadow = built["path"]
        self.shadow_profile = built["profile"]
        snapshot = json.loads(self.shadow.read_bytes().decode("utf-8"))
        payload = json.loads(sfx.read_tree(self.shadow.parent)["payload.json"].decode("utf-8"))
        self.events = {e["event_key"]: e for e in payload["events"]}
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        contract["shadow"] = {"population": "provider_record_shadow_20261017",
                              "identity": self.shadow.parent.name, "snapshot_sha256": sha256(self.shadow.read_bytes()),
                              "payload_sha256": snapshot["payload"]["sha256"],
                              "contract_sha256": self.shadow_world.authority}
        rows = []
        for key in sorted(self.events):
            ev = self.events[key]
            org, name, host = OWNERS[key]
            rows.append({"event_key": key, "home_team_key": ev["home_team_key"], "away_team_key": ev["away_team_key"],
                         "provider_scheduled_utc": ev["provider_scheduled_utc"],
                         "owner": {"side": "home", "ncaa_org_id": org, "official_name": name,
                                   "directory_pointer": f"/{org}", "directory_athletic_site": host,
                                   "directory_host": host}})
        contract["expected"].update(events=rows, expected_events=len(rows), expected_participants=2 * len(rows))
        self.contract = (json.dumps(contract, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
        self.authority = sha256(self.contract)
        self.contract_path = self.root / "schedule-contract.json"
        self.contract_path.write_bytes(self.contract)
        self.anchor_utc = snapshot["anchor"]["created_utc"]

    def bare(self, key: str) -> str:
        host = OWNERS[key][2]
        return host[4:] if host.startswith("www.") else host

    def initial(self, key: str, host: str | None = None) -> str:
        return f"https://{host or self.bare(key)}/sports/football/schedule/2026"

    def capture(self) -> Capture:
        return Capture(self.authority, self.shadow.parent.name)

    def genuine_pages(self) -> dict[str, bytes]:
        """Event 1: SIDEARM Nuxt + text table (naive time, home); event 2: WMT explicit offset; event 3: SIDEARM
        Nuxt with an 'ET' time (stated zone)."""
        alpha = sidearm_page("Alpha State", [
            nuxt_game("2026-09-05T15:00:00", "3:00 p.m.", "A", "Zeta", location="Zeta, St."),
            nuxt_game("2026-10-17T11:00:00", "11:00 a.m.", "H", "Beta Tech", facility="1 Field",
                      location="Alpha, St.")],
            table=[("Sep 5 (Sat)", "3:00 p.m.", "Away", "Zeta", "Zeta, St.", "W 10-3"),
                   ("Oct 17 (Sat)", "11:00 a.m.", "Home", "Beta Tech", "Alpha, St. (1 Field)", " -")])
        gamma = wmt_page([wmt_item("Gamma A&M", "Delta College", "2026-10-17T12:00:00.000-05:00",
                                   location="Gamma City / 2 Field", rank="(#8)")])
        epsilon = sidearm_page("Epsilon City", [
            nuxt_game("2026-10-17T15:30:00", "3:30 p.m. ET", "H", "Zeta Southern", facility="3 Field")])
        return {"espn:event:900000001": alpha, "espn:event:900000002": gamma, "espn:event:900000003": epsilon}

    def genuine_capture(self, pages: dict[str, bytes] | None = None) -> Capture:
        pages = pages or self.genuine_pages()
        cap = self.capture()
        k1, k2, k3 = sorted(self.events)
        # event 1: www -> bare redirect then 200; event 2: 200; event 3: 404 then the landing route 200
        cap.attempt(k1, "900000001-1", "INITIAL_SEASON_ROUTE", 1, self.initial(k1, "www.alpha.example"), 301, b"",
                    headers=[["Location", self.initial(k1)]])
        cap.attempt(k1, "900000001-1", "INITIAL_SEASON_ROUTE", 2, self.initial(k1), 200, pages[k1])
        cap.attempt(k2, "900000002-1", "INITIAL_SEASON_ROUTE", 1, self.initial(k2), 200, pages[k2])
        cap.attempt(k3, "900000003-1", "INITIAL_SEASON_ROUTE", 1, self.initial(k3), 404, b"<html>not found</html>")
        cap.attempt(k3, "900000003-3", "LANDING_ROUTE", 1, "https://www.epsilon.example/sports/football/schedule",
                    200, pages[k3])
        return cap

    def build_args(self, acquisition: Path, out: Path, **overrides: Any) -> Namespace:
        values = {"stage": "build", "contract": self.contract_path, "shadow": self.shadow,
                  "acquisition": Path(acquisition), "output_root": Path(out) / "c", "manifest_root": Path(out) / "m",
                  "processing_order": None, "chunk_size": str(1 << 20), "stop_after_members": None,
                  "successor_of": None}
        values.update(overrides)
        return Namespace(**values)

    def build(self, out: Path, capture: Capture | None = None, **overrides: Any) -> dict[str, Any]:
        from tools import build_official_shadow_schedule as builder  # noqa: PLC0415

        capture = capture or self.genuine_capture()
        acquisition = capture.write(Path(out) / "acq")
        result = builder.build_sidecar(self.build_args(acquisition, out, **overrides),
                                       contract_authority=self.authority, shadow_profile=self.shadow_profile)
        result["path"] = Path(result["schedule"])
        return result

    def query(self, sidecar: Path, *args: str, profile: Any = None) -> tuple[int, Any, str]:
        """One in-process query through the real console entry point with the fixture authorities."""
        import contextlib  # noqa: PLC0415
        import io  # noqa: PLC0415

        from aggie_analytics.retrospective_baseline import query  # noqa: PLC0415

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = query.main(["--prospective-shadow", str(self.shadow), "--schedule-evidence", str(sidecar),
                               *args], schedule_contract_sha256=self.authority,
                              schedule_profile=profile, shadow_profile=self.shadow_profile)
        text = out.getvalue()
        return code, json.loads(text) if code == 0 and text else None, err.getvalue()


def refusal(stderr: str) -> str | None:
    for line in reversed(stderr.strip().splitlines()):
        try:
            return json.loads(line).get("refused")
        except (ValueError, AttributeError):
            continue
    return None


def forge(sidecar: Path, work: Path, *, schedule_edit: Callable[[dict], None] | None = None,
          file_edit: Callable[[dict[str, bytes]], None] | None = None) -> Path:
    """A coordinated forgery of a genuine sidecar copy: members and/or schedule.json are edited and the directory is
    renamed to the recomputed identity, so every outer hash is consistent and only a semantic rule can refuse it."""
    from aggie_analytics.retrospective_baseline import schedule  # noqa: PLC0415

    files = sfx.read_tree(sidecar.parent)
    doc = json.loads(files.pop(schedule.SCHEDULE_FILE).decode("utf-8"))
    if file_edit is not None:
        file_edit(files)
    if schedule_edit is not None:
        schedule_edit(doc)
    bundle = {n: {"sha256": sha256(files[n]), "bytes": len(files[n])} for n in sorted(files)}
    identity = schedule.schedule_identity(doc, bundle)
    target = Path(work) / identity
    sfx.write_tree(target, {**files, schedule.SCHEDULE_FILE: schedule.file_bytes(doc)})
    return target / schedule.SCHEDULE_FILE


def rehouse(sidecar: Path, target_parent: Path) -> Path:
    target = Path(target_parent) / sidecar.parent.name
    sfx.write_tree(target, sfx.read_tree(sidecar.parent))
    return target / sidecar.name


def deep(value: Any) -> Any:
    return copy.deepcopy(value)
