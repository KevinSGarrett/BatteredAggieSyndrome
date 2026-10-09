"""BAT-720 (Cycle #48 — Attempt #1, TP48-A01): tiny owned worlds for the explicit alias successor.

Every fixture is real: a parent query database built and materialized by the accepted parent builder, a gzip crosswalk
with the parent's program-season header, a canonical registry CSV, two provider captures with their receipts, the
accepted V1 builder's sidecar (the predecessor) and a retained evidence bundle of synthetic NCAA organization records
and official season documents with exact byte witnesses. Nothing here is real-world evidence; names only exercise the
rules (a supported alias, an apostrophe form, a season-scoped 2025-only provider, an unsupported alias, a supported
2024 season beside an unsupported 2025 season, and two collision controls that must never be linked).
"""
from __future__ import annotations

import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data import national_di_population as pop  # noqa: E402
from aggie_analytics.national_population import query  # noqa: E402

PARENT_CONTRACT_SHA = "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903"
M1, M2 = "1" * 64, "2" * 64
V1_POPULATION = "national_population_reconciliation_2024_2025"
V1_DB_NAME = "national_population_reconciliation.sqlite"
POPULATION = "national_reconciliation_aliases_2024_2025"
DB_NAME = "national_reconciliation_aliases.sqlite"
V1_CONTRACT = ROOT / "configs" / "national_population_reconciliation_2024_2025_contract.json"
V1_BUILDER = ROOT / "tools" / "build_national_population_reconciliation.py"
BUILDER = ROOT / "tools" / "build_national_reconciliation_aliases.py"
OKINA = "ʻ"
RETRIEVED = "2026-10-09T20:00:00Z"

#: org -> (NCAA name, {season: division label}, provider team id, provider display name, crosswalk rule)
TEAMS = {
    "100": ("Alpha St.", {2024: "FBS", 2025: "FBS"}, "9001", "Alpha State", "NAME_CONFIRMED_BY_SCHEDULE"),
    "657": ("Southern California", {2024: "FBS", 2025: "FBS"}, "9030", "USC", "SCHEDULE_FINGERPRINT_ONLY"),
    "648": ("South Carolina", {2024: "FBS", 2025: "FBS"}, "9579", "South Carolina", "NAME_CONFIRMED_BY_SCHEDULE"),
    "277": ("Hawaii", {2024: "FBS", 2025: "FBS"}, "9062", "Hawai'i", "SCHEDULE_FINGERPRINT_ONLY"),
    "725": ("Army West Point", {2024: "FBS", 2025: "FBS"}, "9349", "Army", "NAME_CONFIRMED_BY_SCHEDULE"),
    "655": ("Southeastern La.", {2024: "FCS", 2025: "FCS"}, "9545", "SE Louisiana", "NAME_CONFIRMED_BY_SCHEDULE"),
    "665": ("Southern U.", {2024: "FCS", 2025: "FCS"}, "9582", "Southern", "NAME_CONFIRMED_BY_SCHEDULE"),
    "253": ("Georgia Southern", {2024: "FBS", 2025: "FBS"}, "9290", "Georgia Southern", "NAME_CONFIRMED_BY_SCHEDULE"),
}
#: (contest key, season, date, a, b, a points, b points); every contest has one dated provider row
GAMES = [
    ("ncaa:3001", 2024, "2024-09-07", "100", "657", 21, 14),
    ("ncaa:3002", 2024, "2024-09-14", "657", "648", 30, 20),
    ("ncaa:3003", 2024, "2024-09-21", "277", "100", 17, 24),
    ("ncaa:3004", 2024, "2024-09-28", "725", "253", 28, 7),
    ("ncaa:3005", 2024, "2024-10-05", "655", "100", 3, 45),
    ("ncaa:3006", 2024, "2024-10-12", "253", "648", 10, 13),
    ("ncaa:4001", 2025, "2025-09-06", "665", "253", 14, 31),
    ("ncaa:4002", 2025, "2025-09-13", "657", "277", 41, 38),
    ("ncaa:4003", 2025, "2025-09-20", "725", "100", 24, 10),
    ("ncaa:4004", 2025, "2025-09-27", "100", "655", 35, 0),
]
PROVIDER_ONLY_2025 = ("665",)  # Southern is observed by the provider in 2025 only (no 2024 game here)


def contest(key: str, season: int, date: str, a: str, b: str, a_pts: int, b_pts: int) -> dict[str, Any]:
    def side(org: str) -> dict[str, Any]:
        label = TEAMS[org][1][season]
        return {"org_id": org, "team_season_id": f"ts{org}{season}", "team_name": TEAMS[org][0], "division_label": label,
                "membership": "DIVISION_I", "key": f"org:{org}"}
    sa, sb = side(a), side(b)
    row = {"contest_key": key, "ncaa_contest_id": key.split(":", 1)[1], "season": season, "term": "FALL",
           "contest_date": date, "contest_dates_observed": [date], "site": "HOME_A", "neutral_site_text": None,
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


def game(gid: int, season: int, date: str, home: str, away: str, home_pts: int, away_pts: int) -> dict[str, Any]:
    def cls(org: str) -> str:
        return "fbs" if TEAMS[org][1][season] == "FBS" else "fcs"
    return {"id": gid, "season": season, "week": 1, "seasonType": "regular", "startDate": f"{date}T19:00:00.000Z",
            "startTimeTBD": False, "completed": True, "neutralSite": False, "conferenceGame": False,
            "homeId": int(TEAMS[home][2]), "homeTeam": TEAMS[home][3], "homeClassification": cls(home),
            "homeConference": "X", "homePoints": home_pts, "awayId": int(TEAMS[away][2]), "awayTeam": TEAMS[away][3],
            "awayClassification": cls(away), "awayConference": "Y", "awayPoints": away_pts}


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_gzip_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows).encode("utf-8")
    with path.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        gz.write(payload)


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
                             "effective_from": "2021-01-01", "effective_to_exclusive": "2026-01-01",
                             "source_system_id": "SRC-002"})


def build_world(base: Path) -> dict[str, Any]:
    """The parent and every cached input under ``base``; return the bindings the V1 and successor contracts name."""
    rows = [contest(*g) for g in GAMES]
    provider = {2024: [], 2025: []}
    for number, (key, season, date, a, b, a_pts, b_pts) in enumerate(GAMES, 1):
        provider[season].append(game(number, season, date, a, b, a_pts, b_pts))
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
    write_gzip_jsonl(base / "canonical" / "p" / "sha256" / M1 / "identity_bindings.jsonl.gz", bindings)
    write_registry(base / "canonical" / "reg" / "canonical_core_registry.csv")
    captures = []
    for season, games in provider.items():
        raw = json.dumps(games).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        rel = f"raw/SRC-002/games/sha256_{digest}.json"
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        (base / rel).write_bytes(raw)
        receipt = {"response_sha256": digest, "row_count": len(games), "capture_id": f"cap_alias_{season}",
                   "source_id": "SRC-002", "path": "/games", "parameters": {"classification": "fbs", "year": str(season)},
                   "immutable_path": rel, "http_status": 200, "result": "SUCCESS"}
        receipt_rel = f"manifests/captures/SRC-002/cap_alias_{season}.json"
        (base / receipt_rel).parent.mkdir(parents=True, exist_ok=True)
        (base / receipt_rel).write_text(json.dumps(receipt, indent=1), encoding="utf-8")
        captures.append({"season": season, "relative_path": rel, "sha256": digest, "rows": len(games),
                         "receipt_relative_path": receipt_rel, "receipt_sha256": sha(base / receipt_rel),
                         "capture_id": f"cap_alias_{season}", "source_id": "SRC-002", "route_path": "/games",
                         "route_parameters": {"classification": "fbs", "year": str(season)}})
    counts = {"2024": sum(1 for g in GAMES if g[1] == 2024), "2025": sum(1 for g in GAMES if g[1] == 2025)}
    parent = {"query_db_identity": parent_db.parent.name, "sqlite_sha256": sha(parent_db),
              "contract_sha256": PARENT_CONTRACT_SHA, "schema_version": pop.DB_SCHEMA_VERSION, "contest_identity": M2,
              "program_season_identity": M1, "expected_contests": counts}
    inputs = {"identity_bindings": {"relative_path": f"canonical/p/sha256/{M1}/identity_bindings.jsonl.gz",
                                    "sha256": sha(base / "canonical" / "p" / "sha256" / M1 / "identity_bindings.jsonl.gz")},
              "registry": {"relative_path": "canonical/reg/canonical_core_registry.csv",
                           "sha256": sha(base / "canonical" / "reg" / "canonical_core_registry.csv")},
              "provider_captures": captures}
    return {"parent_db": parent_db, "parent": parent, "inputs": inputs, "provider": provider}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_builder(module, argv: list[str]) -> tuple[int, dict, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = module.main(argv)
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else {}), stderr.getvalue()


def build_v1(base: Path, world: dict[str, Any], work: Path) -> dict[str, Any]:
    """The predecessor: the accepted V1 builder over this world with the committed V1 contract (bindings replaced)."""
    contract = json.loads(V1_CONTRACT.read_text(encoding="utf-8"))
    contract["parent"], contract["inputs"] = world["parent"], world["inputs"]
    contract["content_scope"] = query.reconciliation_scope(world)
    path = work / "v1_contract.json"
    path.write_text(json.dumps(contract, indent=1), encoding="utf-8")
    module = load_module(V1_BUILDER, "build_national_population_reconciliation_alias_fixture")
    code, built, err = run_builder(module, ["--contract", str(path), "--parent-database", str(world["parent_db"]),
                                            "--output-root", str(base / "canonical" / V1_POPULATION),
                                            "--manifest-root", str(base / "manifests" / V1_POPULATION)])
    if code != 0:
        raise AssertionError(f"V1 fixture build refused: {err}")
    anchors = {"contract_sha256": sha(path), "contract_id": contract["contract_id"], "parent": world["parent"],
               "inputs": world["inputs"]}
    return {"contract": path, "built": built, "anchors": anchors,
            "database": Path(built["database"]["data_dir"]) / V1_DB_NAME}


# --------------------------------------------------------------------------------------------- evidence

def _gz(data: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as gz:
        gz.write(data)
    return buffer.getvalue()


#: org -> (institution name, official domain, published athletics URL value, NCAA short name)
INSTITUTIONS = {
    "657": ("University of Southern California", "usctrojans.com", "usctrojans.com", "Southern California"),
    "277": ("University of Hawaii, Manoa", "hawaiiathletics.com", "https://hawaiiathletics.com/", "Hawaii"),
    "665": ("Southern University and A&M College", "gojagsports.com", "gojagsports.com", "Southern U."),
    "725": ("U.S. Military Academy", "goarmywestpoint.com", "www.goarmywestpoint.com", "Army West Point"),
    "655": ("Southeastern Louisiana University", "lionsports.net", "lionsports.net", "Southeastern La."),
    "253": ("Georgia Southern University", "gseagles.com", "gseagles.com", "Georgia Southern"),
}


def ncaa_directory() -> bytes:
    """A synthetic NCAA directory list (JSON, one object per organization)."""
    rows = [{"orgId": int(org), "nameOfficial": name, "athleticWebUrl": url, "nameShort": short, "division": 1}
            for org, (name, _d, url, short) in sorted(INSTITUTIONS.items(), key=lambda kv: int(kv[0]))]
    return json.dumps(rows, separators=(",", ":")).encode("utf-8")


def devalue_season_page(season: int, school: str, title_school: str) -> bytes:
    """A synthetic official season page holding a devalue (Nuxt) payload: schedule object 2 names its school and its
    season object 6 its title; the HTML title names the institution."""
    payload = [["ShallowReactive", 1], {"schedule": 2},
               {"id": 3, "title": 4, "school_name": 5, "season": 6, "games": 9}, 185,
               f"{season} Football Schedule", school, {"id": 7, "title": 8}, 51, str(season), []]
    text = ("<!DOCTYPE html><html lang=\"en\"><head><title>" + f"{season} Football Schedule - {title_school}"
            + "</title></head><body><h1>Schedule</h1>"
            "<script type=\"application/json\" id=\"__NUXT_DATA__\" data-ssr=\"true\">"
            + json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "</script></body></html>")
    return text.encode("utf-8")


def span_season_page(season: int, school: str) -> bytes:
    """A synthetic official season page whose school and season are plain delimited HTML element texts."""
    text = (f"<!DOCTYPE html><html><head><title>{season} Football Schedule</title></head><body>"
            f"<span class=\"school-name\">{school}</span><span class=\"season\">{season}</span>"
            f"<p>Football at {school} and Georgia {school}</p></body></html>")
    return text.encode("utf-8")


def json_span(body: bytes) -> tuple[int, int, str, str]:
    """The byte span, prefix and suffix of the embedded __NUXT_DATA__ element (or the whole document when JSON)."""
    marker = b'data-ssr="true">'
    at = body.find(marker)
    if at < 0:
        return 0, len(body), "", ""
    start = at + len(marker)
    end = body.find(b"</script>", start)
    return start, end, 'data-ssr="true">', "</script>"


def json_witness(doc: str, body: bytes, role: str, path: list[Any], devalue: bool, field: str) -> dict[str, Any]:
    start, end, prefix, suffix = json_span(body)
    value = query._json_resolve(json.loads(body[start:end].decode("utf-8")), path, devalue)
    return {"document": doc, "role": role, "kind": "JSON_PATH", "field": field, "byte_start": start, "byte_end": end,
            "prefix": prefix, "suffix": suffix, "value": str(value), "path": path, "devalue": devalue}


def field_witness(doc: str, body: bytes, role: str, prefix: str, value: str, suffix: str, field: str,
                  occurrence: int = 0) -> dict[str, Any]:
    needle = (prefix + value + suffix).encode("utf-8")
    at = -1
    for _ in range(occurrence + 1):
        at = body.find(needle, at + 1)
    start = at + len(prefix.encode("utf-8"))
    return {"document": doc, "role": role, "kind": "DELIMITED_FIELD", "field": field, "byte_start": start,
            "byte_end": start + len(value.encode("utf-8")), "prefix": prefix, "suffix": suffix, "value": value,
            "decoding": "NONE"}


def document_entry(body: bytes, role: str, url: str, hops: list[dict[str, Any]] | None = None,
                   media_type: str = "text/html") -> dict[str, Any]:
    digest = hashlib.sha256(body).hexdigest()
    hops = hops or [{"url": url, "status": 200, "location": None}]
    return {"sha256": digest, "file": digest + ".gz", "bytes": len(body), "media_type": media_type, "role": role,
            "request_url": hops[0]["url"], "final_url": hops[-1]["url"], "hops": hops, "http_status": 200,
            "retrieved_at": RETRIEVED, "acquisition": {"lane": "FIXTURE", "run": "fixture", "sequence": 0}}


def evidence() -> dict[str, Any]:
    """The assertions document and document bodies of the tiny world (a valid, complete universe)."""
    bodies: dict[str, bytes] = {}
    documents: list[dict[str, Any]] = []

    def add(body: bytes, role: str, url: str, **kw: Any) -> str:
        entry = document_entry(body, role, url, **kw)
        if entry["sha256"] not in bodies:
            bodies[entry["sha256"]] = body
            documents.append(entry)
        return entry["sha256"]
    directory = ncaa_directory()
    ncaa_doc = add(directory, "NCAA_ORGANIZATION_RECORD",
                   "https://web3.ncaa.org/directory/api/directory/memberList?type=12&sportCode=MFB",
                   media_type="application/json")
    order = [org for org, _v in sorted(INSTITUTIONS.items(), key=lambda kv: int(kv[0]))]

    def ncaa_witnesses(org: str, with_short: bool = True) -> list[dict[str, Any]]:
        i = order.index(org)
        out = [json_witness(ncaa_doc, directory, "NCAA_ORGANIZATION_ID", [i, "orgId"], False, "orgId"),
               json_witness(ncaa_doc, directory, "NCAA_INSTITUTION_NAME", [i, "nameOfficial"], False, "nameOfficial"),
               json_witness(ncaa_doc, directory, "NCAA_OFFICIAL_ATHLETICS_URL", [i, "athleticWebUrl"], False,
                            "athleticWebUrl")]
        if with_short:
            out.append(json_witness(ncaa_doc, directory, "NCAA_PROGRAM_NAME", [i, "nameShort"], False, "nameShort"))
        return out

    def assertion(aid: str, org: str, season: int, witnesses: list[dict[str, Any]], equivalence: str = "EXACT"):
        name, domain, _url, _short = INSTITUTIONS[org]
        return {"assertion_id": aid, "org_id": org, "provider_team_id": TEAMS[org][2], "season": season,
                "parent_name": TEAMS[org][0], "provider_name": TEAMS[org][3], "name_equivalence": equivalence,
                "institution": {"name": name, "official_domain": domain}, "witnesses": witnesses}
    assertions, universe = [], []
    # USC 2024 and 2025: devalue payload, exact name
    for season in (2024, 2025):
        body = devalue_season_page(season, "USC", "USC Athletics")
        doc = add(body, "OFFICIAL_SEASON_DOCUMENT", f"https://usctrojans.com/sports/football/schedule/{season}")
        assertions.append(assertion(f"A-657-9030-{season}", "657", season, ncaa_witnesses("657") + [
            json_witness(doc, body, "OFFICIAL_SEASON", [2, "season", "title"], True, "schedule season title"),
            json_witness(doc, body, "OFFICIAL_PROGRAM_NAME", [2, "school_name"], True, "schedule school_name")]))
    # Hawaii 2024 and 2025: delimited element text with the okina (declared apostrophe forms)
    for season in (2024, 2025):
        body = span_season_page(season, f"Hawai{OKINA}i")
        doc = add(body, "OFFICIAL_SEASON_DOCUMENT", f"https://hawaiiathletics.com/sports/football/schedule/{season}")
        assertions.append(assertion(f"A-277-9062-{season}", "277", season, ncaa_witnesses("277", False) + [
            field_witness(doc, body, "OFFICIAL_SEASON", '<span class="season">', str(season), "</span>", "season"),
            field_witness(doc, body, "OFFICIAL_PROGRAM_NAME", '<span class="school-name">', f"Hawai{OKINA}i", "</span>",
                          "school name")], "APOSTROPHE_FORMS"))
    # Southern 2025 only (the provider observes it only in 2025)
    body = devalue_season_page(2025, "Southern", "Southern University Athletics")
    doc = add(body, "OFFICIAL_SEASON_DOCUMENT", "https://gojagsports.com/sports/football/schedule/2025")
    assertions.append(assertion("A-665-9582-2025", "665", 2025, ncaa_witnesses("665") + [
        json_witness(doc, body, "OFFICIAL_SEASON", [2, "season", "title"], True, "schedule season title"),
        json_witness(doc, body, "OFFICIAL_PROGRAM_NAME", [2, "school_name"], True, "schedule school_name")]))
    # Army 2024 supported (after a www redirect); 2025 unsupported (its season document names another form)
    body = devalue_season_page(2024, "Army", "Army West Point Athletics")
    hops = [{"url": "https://www.goarmywestpoint.com/sports/football/schedule/2024", "status": 301,
             "location": "https://goarmywestpoint.com/sports/football/schedule/2024"},
            {"url": "https://goarmywestpoint.com/sports/football/schedule/2024", "status": 200, "location": None}]
    doc = add(body, "OFFICIAL_SEASON_DOCUMENT", hops[0]["url"], hops=hops)
    assertions.append(assertion("A-725-9349-2024", "725", 2024, ncaa_witnesses("725") + [
        json_witness(doc, body, "OFFICIAL_SEASON", [2, "season", "title"], True, "schedule season title"),
        json_witness(doc, body, "OFFICIAL_PROGRAM_NAME", [2, "school_name"], True, "schedule school_name")]))
    army_2025 = add(devalue_season_page(2025, "Army West Point", "Army West Point Athletics"), "ATTEMPTED_DOCUMENT",
                    "https://goarmywestpoint.com/sports/football/schedule/2025")
    # SE Louisiana: its official pages name "Southeastern Louisiana", never the provider's "SE Louisiana"
    sela = {season: add(devalue_season_page(season, "Southeastern Louisiana", "Southeastern Louisiana University"),
                        "ATTEMPTED_DOCUMENT", f"https://lionsports.net/sports/football/schedule/{season}")
            for season in (2024, 2025)}
    for a in assertions:
        universe.append({"key": query.alias_key(a["org_id"], a["provider_team_id"], a["season"]), "org_id": a["org_id"],
                         "provider_team_id": a["provider_team_id"], "season": a["season"],
                         "parent_name": a["parent_name"], "provider_name": a["provider_name"],
                         "disposition": "SUPPORTED", "assertion_id": a["assertion_id"], "reason": None,
                         "attempted_documents": []})
    unsupported = [("725", 2025, "PROVIDER_NAME_NOT_IN_OFFICIAL_SEASON_DOCUMENT", [army_2025]),
                   ("655", 2024, "PROVIDER_NAME_NOT_IN_OFFICIAL_SEASON_DOCUMENT", [sela[2024]]),
                   ("655", 2025, "PROVIDER_NAME_NOT_IN_OFFICIAL_SEASON_DOCUMENT", [sela[2025]])]
    for org, season, reason, attempted in unsupported:
        universe.append({"key": query.alias_key(org, TEAMS[org][2], season), "org_id": org,
                         "provider_team_id": TEAMS[org][2], "season": season, "parent_name": TEAMS[org][0],
                         "provider_name": TEAMS[org][3], "disposition": "UNSUPPORTED", "assertion_id": None,
                         "reason": reason, "attempted_documents": attempted})
    universe.sort(key=lambda r: r["key"])
    doc = {"schema": query.ALIAS_ASSERTIONS_SCHEMA, "population": POPULATION, "universe": universe,
           "assertions": assertions, "documents": documents}
    return {"assertions": doc, "bodies": bodies}


def write_evidence(directory: Path, ev: dict[str, Any]) -> dict[str, str]:
    """The evidence source directory (create-only): the assertions document and one gzip body per document."""
    directory.mkdir(parents=True, exist_ok=False)
    data = (json.dumps(ev["assertions"], indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    (directory / query.ALIAS_ASSERTIONS_FILE).write_bytes(data)
    for doc in ev["assertions"]["documents"]:
        (directory / doc["file"]).write_bytes(_gz(ev["bodies"][doc["sha256"]]))
    outputs = {p.name: sha(p) for p in sorted(directory.iterdir())}
    identity = hashlib.sha256(query.canonical_json_bytes(
        query.alias_evidence_document(outputs[query.ALIAS_ASSERTIONS_FILE], outputs))).hexdigest()
    return {"bundle_identity": identity, "assertions_sha256": outputs[query.ALIAS_ASSERTIONS_FILE]}


def successor_contract(path: Path, world: dict[str, Any], v1: dict[str, Any], pins: dict[str, str],
                       universe: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    """A successor contract over this world (written to ``path``) and the anchors it binds."""
    predecessor = {"population_id": V1_POPULATION, "contract_sha256": v1["anchors"]["contract_sha256"],
                   "contract_id": v1["anchors"]["contract_id"], "content_identity": v1["built"]["content_identity"],
                   "database_identity": v1["built"]["database_identity"]}
    anchors = {"contract_sha256": None, "contract_id": "BAT-720-NATIONAL-RECONCILIATION-ALIASES-2024-2025-V1",
               "parent": world["parent"], "inputs": world["inputs"], "alias_evidence": pins, "predecessor": predecessor}
    contract = {"schema_version": "1.0.0", "contract_id": anchors["contract_id"], "jira_key": "BAT-720",
                "cycle_number": 48, "attempt_number": 1, "population_id": POPULATION, "seasons": [2024, 2025],
                "predecessor": predecessor,
                "parent_contract": {"repository_path": "configs/national_di_population_2016_2025_contract.json",
                                    "sha256": PARENT_CONTRACT_SHA},
                "parent": world["parent"], "inputs": world["inputs"], "alias_evidence": pins,
                "alias_universe": universe, "labels": query.ALIAS_LABELS, "parameters": query.ALIAS_PARAMETERS,
                "content_scope": query.alias_scope(anchors)}
    contract.update(overrides)
    path.write_text(json.dumps(contract, indent=1, ensure_ascii=False), encoding="utf-8")
    anchors["contract_sha256"] = sha(path)
    anchors["contract_id"] = contract["contract_id"]
    return anchors


def copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target)
