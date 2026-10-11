"""Synthetic fixtures for the BAT-723 prospective provider-observation capsule (no real provider bytes).

A fixture world is a scoreboard-shaped JSON response with clearly synthetic event/team IDs and names, a receipt for it,
a frozen expected cohort and a contract derived from the committed contract with the fixture's own pins and
membership. Its SHA-256 is the fixture authority that tests pass explicitly to the reader and builder (the committed
contract SHA-256 remains the only default authority).
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
from argparse import Namespace
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "configs" / "prospective_provider_observation_20261011_contract.json"
FIXTURE_URL = ("https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=20261017&"
               "groups=80&limit=1000")
STARTED = "2026-10-11T18:15:55.264959+00:00"
ENDED = "2026-10-11T18:15:55.744674+00:00"
SERVER_DATE = "Sun, 11 Oct 2026 18:15:55 GMT"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def competitor(team_id: str, side: str, name: str, summary: str = "3-2", **extra: Any) -> dict[str, Any]:
    node = {"id": team_id, "uid": f"s:20~l:23~t:{team_id}", "type": "team", "order": 0 if side == "home" else 1,
            "homeAway": side, "team": {"id": team_id, "displayName": name, "location": name.split()[0],
                                       "abbreviation": name[:3].upper()},
            "score": "0", "curatedRank": {"current": 99},
            "records": [{"name": "overall", "abbreviation": "overall", "type": "total", "summary": summary},
                        {"name": "Home", "abbreviation": "Home", "type": "homerecord", "summary": "2-0"},
                        {"name": "Away", "abbreviation": "Away", "type": "awayrecord", "summary": "1-2"},
                        {"name": "vs. Conf.", "abbreviation": "CONF", "type": "vsconf", "summary": "1-1"}]}
    node.update(extra)
    return node


def status(name: str = "STATUS_SCHEDULED", state: str = "pre", completed: bool = False) -> dict[str, Any]:
    return {"clock": 0.0, "displayClock": "0:00", "period": 0,
            "type": {"id": "1", "name": name, "state": state, "completed": completed, "description": "Scheduled"}}


def event(event_id: str, home: dict[str, Any], away: dict[str, Any], date: str = "2026-10-17T16:00Z",
          **extra: Any) -> dict[str, Any]:
    node = {"id": event_id, "uid": f"s:20~l:23~e:{event_id}", "date": date, "name": "Fixture at Fixture",
            "shortName": "FX @ FX", "season": {"year": 2026, "type": 2, "slug": "regular-season"},
            "week": {"number": 7}, "status": status(), "links": [], "weather": {},
            "competitions": [{"id": event_id, "uid": f"s:20~l:23~e:{event_id}~c:{event_id}", "date": date,
                              "attendance": 0, "type": {"id": "1", "abbreviation": "STD"}, "timeValid": True,
                              "dateValid": True, "neutralSite": False, "venue": {"id": "1", "fullName": "Fixture Field"},
                              "competitors": [home, away], "status": status(),
                              "odds": [{"provider": {"name": "FixtureOdds"}, "details": "FX -3.5"}],
                              "leaders": [], "broadcasts": []}]}
    node.update(extra)
    return node


def genuine_events() -> list[dict[str, Any]]:
    """Three clean synthetic events (six participants)."""
    return [event("900000001", competitor("9001", "home", "Fixture Alpha Owls", "4-1"),
                  competitor("9002", "away", "Fixture Beta Hawks", "2-3")),
            event("900000003", competitor("9005", "home", "Fixture Epsilon Bears", "5-0-1"),
                  competitor("9006", "away", "Fixture Zeta Foxes", "0-6"), date="2026-10-17T19:30Z"),
            event("900000002", competitor("9003", "home", "Fixture Gamma Lions", "3-3"),
                  competitor("9004", "away", "Fixture Delta Wolves", "6-0"), date="2026-10-17T17:00Z")]


def scoreboard(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {"leagues": [{"id": "23", "name": "NCAA - Football", "season": {"year": 2026}}], "groups": ["80"],
            "events": events, "provider": {"id": "100", "name": "FixtureOdds", "priority": 1}, "week": {"number": 7}}


def membership(raw_doc: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    keys = sorted(f"espn:event:{e['id']}" for e in raw_doc["events"])
    participants = []
    for i, e in enumerate(raw_doc["events"]):
        competitions = e.get("competitions") or []
        if len(competitions) != 1:
            continue
        for j, c in enumerate(competitions[0].get("competitors") or []):
            cid = c.get("id")
            participants.append({"event_key": f"espn:event:{e['id']}",
                                 "team_key": f"espn:team:{cid}" if isinstance(cid, str) and cid.isdigit() else None,
                                 "side": c.get("homeAway") if isinstance(c.get("homeAway"), str) else None,
                                 "raw_pointer": f"/events/{i}/competitions/0/competitors/{j}"})
    participants.sort(key=lambda p: (p["event_key"], p["team_key"] or "", p["side"] or "", p["raw_pointer"]))
    return keys, participants


class World:
    """Raw, receipt, cohort and contract bytes of one fixture plus its authority."""

    def __init__(self, events: list[dict[str, Any]] | None = None, *, raw_doc: dict[str, Any] | None = None,
                 started: str = STARTED, ended: str = ENDED) -> None:
        self.raw_doc = raw_doc if raw_doc is not None else scoreboard(events if events is not None
                                                                      else genuine_events())
        self.raw = (json.dumps(self.raw_doc, ensure_ascii=False) + "\n").encode("utf-8")
        receipt = {"cycle_number": 51, "attempt_number": 1, "url": FIXTURE_URL, "started": started, "ended": ended,
                   "status": 200, "headers": {"Content-Type": "application/json;charset=UTF-8", "Date": SERVER_DATE},
                   "body": "synthetic fixture", "sha256": sha256(self.raw), "bytes": len(self.raw), "events": [],
                   "requests": 1, "limits": "synthetic fixture; no request was made"}
        self.receipt = json.dumps(receipt, indent=2).encode("utf-8")
        keys, participants = membership(self.raw_doc)
        cohort = {"cycle_number": 51, "attempt_number": 1, "state": "SYNTHETIC_FIXTURE_COHORT",
                  "source_sha256": sha256(self.raw), "receipt_sha256": sha256(self.receipt), "event_keys": keys,
                  "participants": participants, "expected_events": len(keys),
                  "expected_participants": len(participants), "observation_start": started, "observation_end": ended}
        self.expected = json.dumps(cohort, indent=2).encode("utf-8")
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        contract["source"].update(endpoint=FIXTURE_URL, raw_sha256=sha256(self.raw), raw_bytes=len(self.raw),
                                  receipt_sha256=sha256(self.receipt), receipt_bytes=len(self.receipt),
                                  expected_cohort_sha256=sha256(self.expected), expected_cohort_bytes=len(self.expected))
        contract["membership"].update(event_keys=keys, participants=[
            {"event_key": p["event_key"], "side": p["side"], "team_key": p["team_key"]} for p in participants],
            expected_events=len(keys), expected_participants=len(participants))
        self.contract = (json.dumps(contract, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
        self.authority = sha256(self.contract)

    def write_inputs(self, root: Path) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        paths = {"raw": root / "provider-response.json", "receipt": root / "provider-receipt.json",
                 "expected": root / "EXPECTED_COHORT.json", "contract": root / "contract.json"}
        for key, path in paths.items():
            path.write_bytes(getattr(self, key))
        return paths

    def build_args(self, root: Path, **overrides: Any) -> Namespace:
        paths = self.write_inputs(root / "inputs")
        values = {"contract": paths["contract"], "raw": paths["raw"], "receipt": paths["receipt"],
                  "expected": paths["expected"], "output_root": root / "canonical", "manifest_root": root / "manifests",
                  "processing_order": None, "chunk_size": str(1 << 20), "stop_after_members": None,
                  "contract_authority": self.authority}
        values.update(overrides)
        return Namespace(**values)


def mutate_events(mutator: Callable[[list[dict[str, Any]]], None]) -> list[dict[str, Any]]:
    events = genuine_events()
    mutator(events)
    return events


def rehouse(capsule: Path, target_parent: Path) -> Path:
    """A byte copy of the whole capsule directory under another parent (same identity directory name)."""
    target = target_parent / capsule.parent.name
    shutil.copytree(capsule.parent, target)
    return target / capsule.name


def forge(capsule: Path, edit: Callable[[dict[str, Any]], None], work: Path, *, identity_of: Callable[[dict], str]
          ) -> Path:
    """A coordinated forgery: the capsule document is edited, re-serialized canonically and housed in a directory named
    by the recomputed identity of the edited document, with the genuine bundle members copied beside it."""
    from aggie_analytics.national_source_time import prospective  # noqa: PLC0415

    doc = json.loads(capsule.read_bytes().decode("utf-8"))
    forged = copy.deepcopy(doc)
    edit(forged)
    if prospective.capsule_file_bytes(forged) == prospective.capsule_file_bytes(doc):
        raise AssertionError("the forgery edit changed nothing (a no-op is not a forgery)")
    identity = identity_of(forged)
    target = work / identity
    shutil.copytree(capsule.parent, target)
    (target / prospective.CAPSULE_FILE).write_bytes(prospective.capsule_file_bytes(forged))
    return target / prospective.CAPSULE_FILE
