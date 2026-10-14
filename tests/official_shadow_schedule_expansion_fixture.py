"""Synthetic fixtures for the BAT-727 official schedule expansion successor (no real pages, no network, no capture).

An expansion world reuses the BAT-726 schedule world (a synthetic BAT-725 shadow, a three-event fixture schedule
contract with reserved ``*.example`` host families and a synthetic capture journal), builds the synthetic V1 sidecar with
the accepted builder, and derives a successor contract from the committed successor contract with the fixture pins
(predecessor, shadow, cohort, fixture institution decisions and a fixture policy-frozen time after the fixture capture).
Its SHA-256 and the fixture V1/successor profiles are the authorities the tests pass explicitly; the committed contract
SHA-256 and the packaged profiles stay the only defaults. Pages are synthetic copies of the successor's declared layouts
(Sidearm Nuxt with site settings and a documented owner name, the classic SIDEARM schedule object with JSON-LD, the WMT
event-block, team-default and default-event views) and keep the V1 layouts for the preserved event.
"""
from __future__ import annotations

import datetime as dt
import json
from argparse import Namespace
from pathlib import Path
from typing import Any

import official_shadow_schedule_fixture as fx

sfx = fx.sfx
REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "configs" / "official_shadow_schedule_expansion_20261017_contract.json"
K1, K2, K3 = "espn:event:900000001", "espn:event:900000002", "espn:event:900000003"


# --------------------------------------------------------------------------------------------- pages

def nuxt_sidearm_page(school: str, games: list[dict[str, Any]], *, site_name: str | None = None,
                      mascot: str | None = None, og: str | None = None, season: str = "2026") -> bytes:
    """A Sidearm Nuxt page whose payload also carries the site-config settings (site name and mascot)."""
    record = {"id": 9, "title": f"{season} Football Schedule", "school_name": school,
              "sport": {"id": 4, "title": "Football", "shortname": "football"},
              "season": {"id": 1, "title": season, "startdate": f"{season}-01-01T00:00:00"}, "games": games}
    settings = {"bucketName": "fixture.example", "siteName": site_name, "mascotPlural": mascot,
                "mascotSingular": "Fixture"}
    payload = fx.devalue({"state": {}, "pinia": {"site-config": {"siteSettings": settings},
                                                 "schedule": {"schedules": {"schedules-football,2026": record}}}})
    meta = f'<meta property="og:site_name" content="{og}">' if og is not None else ""
    return ("<!DOCTYPE html><html><head><title>2026 Football Schedule</title>" + meta + "</head><body>"
            '<script type="application/json" data-nuxt-data="nuxt-app" id="__NUXT_DATA__">' + json.dumps(payload) +
            "</script></body></html>").encode("utf-8")


def classic_page(school: str, games: list[dict[str, Any]], *, season: str = "2026", sport: str = "football",
                 ld: list[dict[str, Any]] | None = None, og: str | None = None, register: bool = True) -> bytes:
    """A classic SIDEARM page: the schedule object inside the inline script that registers 'vue-schedules'."""
    schedule = {"id": 1204, "title": f"{season} Football Schedule", "school_name": school,
                "season": {"id": 53, "title": season}, "sport": {"id": 2, "shortname": sport,
                                                                 "season": {"id": 51, "title": "2025"}},
                "games": games}
    script = ("<script>\r\n var schedule_id = 1204;\r\n require(['vue'], function (Vue) {\r\n"
              + (" Vue.component('vue-schedules', {\r\n" if register else " Vue.component('vue-other', {\r\n")
              + "  data: () => ({\r\n   settings : {\"schedule_score_display\":\"standard\"},\r\n   schedule : "
              + json.dumps(schedule) + "\r\n  })\r\n });\r\n });\r\n</script>")
    head = '<script type="application/ld+json">' + json.dumps(ld) + "</script>" if ld is not None else ""
    meta = f'<meta property="og:site_name" content="{og}">' if og is not None else ""
    return ("<!DOCTYPE html><html><head><title>\r\n\t2026 Football Schedule\r\n</title>" + meta + head +
            "</head><body>" + script + "</body></html>").encode("utf-8")


def classic_game(date: str, time: str, indicator: str, opponent: str, *, facility: str | None = "Fixture Stadium",
                 location: str = "Here, St.") -> dict[str, Any]:
    return {"id": 6927, "date": date, "enddate": None, "time": time, "location": location,
            "location_indicator": indicator, "at_vs": "vs" if indicator == "H" else "at",
            "opponent": {"id": 105, "title": opponent, "mascot": "Fixture", "image": {"alt": opponent.split()[0]}},
            "facility": {"id": 1, "title": facility} if facility else None, "result": None}


def ld_event(start: str, home: str, away: str) -> dict[str, Any]:
    return {"@context": "https://schema.org/", "@type": "SportsEvent", "name": f"{home} Vs {away}",
            "homeTeam": {"@type": "SportsTeam", "name": home}, "awayTeam": {"@type": "SportsTeam", "name": away},
            "startDate": start}


def event_block(datetime: str, venue: str, opponent: str, *, facility: str = "2 Field", location: str = "Gamma City",
                label: str = "12:00PM CDT", divider: str = "vs.", row: bool = False) -> str:
    """One WMT event-block record (a list-view block, or a table-view row with row=True)."""
    date = (f'<div class="schedule-event-date schedule-event-date--venue-{venue}"><strong class="schedule-event-'
            f'date__time"><time datetime="{datetime}" class="schedule-event-date__weekday">Sat</time><time datetime="'
            f'{datetime}" class="schedule-event-date__day">Oct 17</time></strong></div>')
    team = (f'<div class="schedule-default-team"><strong class="schedule-default-team__divider">{divider}</strong>'
            f'<img alt="logo"><strong class="schedule-default-team__opponent-name"> {opponent}</strong><span class="'
            f'schedule-default-team__venue">{facility}</span></div>')
    result = f'<strong class="schedule-event-item-result__label">{label}</strong>'
    if row:
        return (f'<tr class="schedule-item-table"><th>{date}</th><td>{team}</td><td><span class="schedule-event-'
                f'location">{location} / {facility}</span></td><td>{result}</td></tr>')
    return (f'<div class="schedule-event-block"><div class="schedule-event-block__top">{date}</div>{team}'
            f'<span class="schedule-event-location">{location}</span>{result}</div>')


def team_default(date_text: str, venue_type: str, opponent: str, *, location: str = "Gamma City / 2 Field",
                 label: str = "12:00 PM EDT", divider: str = "vs.", row: bool = False) -> str:
    """One WMT team-default record (logo-only teams; a grid item, or a table row with row=True)."""
    inner = (f'<div class="schedule-event-date"><strong class="schedule-event-date__time"><time>{date_text}</time>'
             f'</strong><strong class="schedule-event-date__venue-type">{venue_type}</strong></div>'
             f'<div class="schedule-event-default"><div class="schedule-event-default__teams"><div class="schedule-'
             f'event-team-default"><img alt="OwnerLogo"></div><strong class="schedule-event-default__divider">'
             f'{divider}</strong><div class="schedule-event-team-default"><img alt="OpponentLogo"></div></div>'
             f'<strong class="schedule-event-default__name">{opponent}</strong></div>'
             f'<span class="schedule-event-location">{location}</span>'
             f'<strong class="schedule-event-item-result__label">{label}</strong>')
    if row:
        return f'<tr class="schedule-table-item"><td>{inner}</td></tr>'
    return f'<div class="schedule-event-item">{inner}</div>'


def default_event(weekday: str, month_day: str, divider: str, opponent: str, *, rank: str = "",
                  location: str = "Gamma City, St. (2 Field)", label: str = "11:00 AM CT", row: bool = False,
                  current: str = "#22") -> str:
    """One WMT default-event record (the current-team element states no name; a grid item or a table row)."""
    ranking = f'<span class="schedule-default-event__ranking">{rank}</span>' if rank else ""
    inner = (f'<div class="schedule-event-date"><strong class="schedule-event-date__time"><time class="schedule-event'
             f'-date__weekday">{weekday}</time><time class="schedule-event-date__month-day">{month_day}</time></strong>'
             f'</div><div class="schedule-default-event"><div class="schedule-default-event__team schedule-default-'
             f'event__team--current"><strong class="schedule-default-event__team-ranking">{current}</strong><img '
             f'alt="hashed0label"></div><strong class="schedule-default-event__divider">{divider}</strong><div '
             f'class="schedule-default-event__team"><span class="schedule-default-event__name"><strong class="'
             f'schedule-default-event__divider-mobile">{divider}</strong>{ranking}<span>{opponent}</span></span><span '
             f'class="schedule-event-location">{location}</span></div></div>'
             f'<span class="schedule-event-location">{location}</span>'
             f'<strong class="schedule-event-item-result__label">{label}</strong>')
    if row:
        return f'<tr class="schedule-table-event"><th>{inner}</th></tr>'
    return f'<div class="schedule-event-item">{inner}</div>'


def wmt_variant_page(records: list[str], *, heading: str = "Football 2026 Schedule Schedule",
                     heading_class: str = "schedule-hero-block__title", og: str | None = None) -> bytes:
    meta = f'<meta property="og:site_name" content="{og}">' if og is not None else ""
    return ("<!DOCTYPE html><html><head><title>Football 2026 Schedule</title>" + meta + "</head><body>"
            f'<h1 class="{heading_class}">{heading}</h1><div class="schedule__view-box--active schedule__view-box '
            f'schedule__view-box--grid">{"".join(r for r in records if not r.startswith("<tr"))}</div>'
            f'<div class="schedule__view-box schedule__view-box--table"><table><tbody>'
            f'{"".join(r for r in records if r.startswith("<tr"))}</tbody></table></div></body></html>'
            ).encode("utf-8")


# --------------------------------------------------------------------------------------------- decisions

def alpha_decision(**overrides: Any) -> dict[str, Any]:
    decision = {"id": "ALPHA_ATHLETICS_OWNER_NAME", "ncaa_org_id": 9101, "official_name": "University of Alpha",
                "directory_host": "www.alpha.example", "kind": "OWNER_STATEMENT",
                "owner_statements": [{"member": "school_name", "value": "Alpha State Athletics",
                                      "basis": "PROVIDER_LOCATION_PLUS_ATHLETICS"}],
                "identity_members": [{"member": "siteSettings.siteName", "value": "Fixture Alpha Owls",
                                      "basis": "PROVIDER_DISPLAY_NAME"},
                                     {"member": "siteSettings.mascotPlural", "value": "Owls",
                                      "basis": "PROVIDER_TEAM_NAME"},
                                     {"member": "og:site_name", "value": "Fixture Alpha Owls",
                                      "basis": "PROVIDER_DISPLAY_NAME"}],
                "witness_documents": [], "alternatives_examined": "fixture", "rationale": "fixture"}
    decision.update(overrides)
    return decision


def gamma_decision(**overrides: Any) -> dict[str, Any]:
    decision = {"id": "GAMMA_PAGE_IDENTITY", "ncaa_org_id": 9103, "official_name": "Gamma A&M University",
                "directory_host": "gamma.example", "kind": "PAGE_IDENTITY", "owner_statements": [],
                "identity_members": [{"member": "og:site_name", "value": "Gamma A&M University Athletics",
                                      "basis": "OFFICIAL_NAME_PLUS_ATHLETICS"}],
                "witness_documents": [], "alternatives_examined": "fixture", "rationale": "fixture"}
    decision.update(overrides)
    return decision


def genuine_decisions() -> list[dict[str, Any]]:
    return [alpha_decision(), gamma_decision()]


# --------------------------------------------------------------------------------------------- world

class ExpansionWorld:
    """The schedule world plus a successor contract that pins its V1 sidecar and the fixture decisions."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.v1 = fx.ScheduleWorld(self.root / "w")

    # pages ------------------------------------------------------------------------------------
    def genuine_pages(self) -> dict[str, bytes]:
        """Event 1: Sidearm Nuxt with a documented owner name and a decorated opponent; event 2: WMT event-block
        list and table views owned by page identity; event 3: the V1 Nuxt page (preserved V1 binding)."""
        alpha = nuxt_sidearm_page("Alpha State Athletics", [
            fx.nuxt_game("2026-09-05T15:00:00", "3:00 p.m.", "A", "Zeta", location="Zeta, St."),
            fx.nuxt_game("2026-10-17T11:00:00", "11:00 a.m. CT", "H", "#13 Beta Tech (Homecoming)",
                         facility="1 Field", location="Alpha, St.")],
            site_name="Fixture Alpha Owls", mascot="Owls", og="Fixture Alpha Owls")
        gamma = wmt_variant_page([event_block("2026-10-17T12:00:00.000-05:00", "home", "Delta College"),
                                  event_block("2026-10-17T12:00:00.000-05:00", "home", "Delta College", row=True)],
                                 og="Gamma A&M University Athletics")
        epsilon = fx.sidearm_page("Epsilon City", [
            fx.nuxt_game("2026-10-17T15:30:00", "3:30 p.m. ET", "H", "Zeta Southern", facility="3 Field")])
        return {K1: alpha, K2: gamma, K3: epsilon}

    # contract -----------------------------------------------------------------------------------
    def contract(self, v1_built: dict[str, Any], *, decisions: list[dict[str, Any]] | None = None,
                 policy_frozen_utc: str | None = None, edit: Any = None) -> bytes:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        profile = v1_built["profile"]
        v1_contract = json.loads(self.v1.contract.decode("utf-8"))
        contract["predecessor"] = {"population": "official_shadow_schedule_20261017",
                                   "identity": profile["schedule_identity"],
                                   "schedule_sha256": profile["schedule_sha256"],
                                   "contract_id": "BAT-726-OFFICIAL-SHADOW-SCHEDULE-20261017-V1",
                                   "contract_sha256": self.v1.authority, "journal_sha256": profile["journal_sha256"],
                                   "attempts": profile["attempts"],
                                   "availability_bound_utc": profile["availability_bound_utc"]}
        contract["shadow"] = {k: v1_contract["shadow"][k] for k in ("population", "identity", "snapshot_sha256",
                                                                   "payload_sha256", "contract_sha256")}
        contract["expected"] = {"source": "fixture", "events": [
            {"event_key": row["event_key"], "ncaa_org_id": row["owner"]["ncaa_org_id"],
             "official_name": row["owner"]["official_name"], "directory_host": row["owner"]["directory_host"]}
            for row in sorted(v1_contract["expected"]["events"], key=lambda r: r["event_key"])],
            "expected_events": len(v1_contract["expected"]["events"])}
        contract["institution_decisions"] = genuine_decisions() if decisions is None else decisions
        if policy_frozen_utc is None:
            bound = dt.datetime.strptime(profile["availability_bound_utc"], "%Y-%m-%dT%H:%M:%S.%fZ")
            policy_frozen_utc = (bound + dt.timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        contract["policy_frozen_utc"] = policy_frozen_utc
        if edit is not None:
            edit(contract)
        return (json.dumps(contract, indent=1, ensure_ascii=False) + "\n").encode("utf-8")

    # build --------------------------------------------------------------------------------------
    def build(self, out: Path, *, pages: dict[str, bytes] | None = None, decisions: list[dict[str, Any]] | None = None,
              policy_frozen_utc: str | None = None, edit: Any = None, v1_built: dict[str, Any] | None = None,
              **overrides: Any) -> dict[str, Any]:
        """Build the V1 sidecar (unless given) from the capture of ``pages`` and the successor from it."""
        from tools import build_official_shadow_schedule as builder  # noqa: PLC0415

        out = Path(out)
        if v1_built is None:
            v1_built = self.v1.build(out / "v1", self.v1.genuine_capture(pages or self.genuine_pages()))
        contract = self.contract(v1_built, decisions=decisions, policy_frozen_utc=policy_frozen_utc, edit=edit)
        authority = sfx.sha256(contract)
        contract_path = out / "expansion-contract.json"
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_bytes(contract)
        values = {"stage": "build-expansion", "contract": contract_path, "shadow": self.v1.shadow,
                  "predecessor": v1_built["path"], "output_root": out / "x", "manifest_root": out / "xm",
                  "processing_order": None, "chunk_size": str(1 << 20), "stop_after_members": None,
                  "successor_of": None}
        values.update(overrides)
        result = builder.build_expansion(Namespace(**values), contract_authority=authority,
                                         predecessor_profile=v1_built["profile"],
                                         shadow_profile=self.v1.shadow_profile)
        result.update(path=Path(result["schedule"]), authority=authority, v1=v1_built, contract_path=contract_path)
        return result

    # query --------------------------------------------------------------------------------------
    def query(self, built: dict[str, Any], *args: str, path: Path | None = None, profile: Any = "pinned",
              authority: str | None = None) -> tuple[int, Any, str]:
        """One in-process query through the real console entry point with every fixture authority."""
        import contextlib  # noqa: PLC0415
        import io  # noqa: PLC0415

        from aggie_analytics.retrospective_baseline import query  # noqa: PLC0415

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = query.main(["--prospective-shadow", str(self.v1.shadow), "--schedule-evidence",
                               str(path or built["path"]), *args],
                              schedule_contract_sha256=self.v1.authority, schedule_profile=built["v1"]["profile"],
                              shadow_profile=self.v1.shadow_profile,
                              expansion_contract_sha256=authority or built["authority"],
                              expansion_profile=built["profile"] if profile == "pinned" else profile,
                              predecessor_profile=built["v1"]["profile"])
        text = out.getvalue()
        return code, json.loads(text) if code == 0 and text else None, err.getvalue()


def refusal(stderr: str) -> str | None:
    return fx.refusal(stderr)


def forge(sidecar: Path, work: Path, *, schedule_edit: Any = None, file_edit: Any = None) -> Path:
    """A coordinated forgery of a genuine successor copy: members and/or schedule.json are edited and the directory is
    renamed to the recomputed identity, so every outer hash is consistent and only a semantic rule can refuse it."""
    from aggie_analytics.retrospective_baseline import schedule_expansion as sx  # noqa: PLC0415

    files = sfx.read_tree(sidecar.parent)
    doc = json.loads(files.pop(sx.SCHEDULE_FILE).decode("utf-8"))
    if file_edit is not None:
        file_edit(files)
    if schedule_edit is not None:
        schedule_edit(doc)
    bundle = {n: {"sha256": sfx.sha256(files[n]), "bytes": len(files[n])} for n in sorted(files)}
    identity = sx.schedule_identity(doc, bundle)
    target = Path(work) / identity
    sfx.write_tree(target, {**files, sx.SCHEDULE_FILE: sx.file_bytes(doc)})
    return target / sx.SCHEDULE_FILE


def rehouse(sidecar: Path, target_parent: Path) -> Path:
    return fx.rehouse(sidecar, target_parent)
