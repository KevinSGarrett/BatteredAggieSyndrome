"""Tiny owned worlds and coordinated forgeries for the BAT-735 national recruiting evidence tests (Cycle #64 TP64-A01).

Not a test module (no ``test`` prefix). Nothing here is real data. A world is a complete retained-source closure in the
real layouts: the acquisition request ledger (34 requested cells: 8 recruiting and 7 portal captures, 19 quota-missing
requests including the two minYear/maxYear coach ranges), one capture receipt per captured cell equal to its manifest
entry, eight small recruiting arrays and seven byte-identical empty portal arrays, a BAT-388-shaped people registry and a
BAT-387-shaped core registry whose record hashes are computed here by an independent restatement of the legacy formulas
(never by the module under test), the two registry manifests, the SRC-002 rights row and a legacy builder stand-in. The
world plants every person class (qualified athlete and recruit-only namespaces, a signed negative athlete ID, no person,
two persons, no mapping, a conflicting mapping, a shared slot, a tampered person record), every program class (an exact
alias with two same-team witnesses, a null label, an absent member, an unmapped label, a case-variant and a
leading-space label, an ambiguous label, a non-source-backed alias, a tampered alias and a team without an entity row),
every value class (an integer rating, float ratings, a joint-null triplet, a mixed triplet, out-of-domain values) and
legacy witnesses that agree, disagree, are absent or name another team. Forged releases are coordinated: database bytes,
table counts, identity documents, identity directories and manifests are rewritten consistently, so each must be
refused by its own semantic rule (or, when fully coordinated, by the pinned profile), never by a stale outer hash.
"""
from __future__ import annotations

import contextlib
import copy
import csv
import hashlib
import io
import json
import shutil
import sqlite3
import sys
import uuid
import zlib
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.personnel_evidence import query as pq  # noqa: E402
from aggie_analytics.personnel_evidence import recruiting as rc  # noqa: E402
from aggie_analytics.personnel_evidence import recruiting_build as rb  # noqa: E402

FROZEN = "2026-10-23T00:00:00Z"
POP = rc.POPULATION
ABSENT = object()
#: Independent restatements of the accepted registry constants (never read from the module under test).
PEOPLE_NS = uuid.UUID("0b9087ea-43c1-5f46-a133-63cc34d403c4")
PEOPLE_OBS_NS = uuid.UUID("e2c44387-e588-579b-86b3-eeb22436d1d0")
CORE_NS = uuid.UUID("a4cfb063-a2ab-5b3d-8a9b-39af49c66e36")
CORE_RECORD_NS = uuid.UUID("bb6c5227-80dd-54f4-b392-a69a23aaab68")
NAME_UNICODE = "J" + chr(0xF3) + "se" + chr(0x301) + " " + chr(0x1F3C8) + " Jr" + chr(0x200D) + "."
NAME_DIACRITIC = "Zo" + chr(0xEB) + " " + chr(0xDC) + "n" + chr(0xEF) + "code"
TEAMS = {"alpha": 1, "beta": 2, "delta1": 3, "delta2": 4, "epsilon": 5, "zeta": 6, "eta": 7}
#: (team, source system, alias, start, end, variant): eta has no team entity row.
ALIASES = [("alpha", "SRC-002", "Alpha State", None, None, "ok"),
           ("alpha", "SRC-001", "Alpha State", 2010, 2016, "ok"),
           ("beta", "SRC-002", "Beta Tech", None, None, "ok"),
           ("delta1", "SRC-002", "Delta College", None, None, "ok"),
           ("delta2", "SRC-001", "Delta College", 2012, 2014, "ok"),
           ("epsilon", "SRC-002", "Epsilon", None, None, "review"),
           ("zeta", "SRC-002", "Zeta A&M", None, None, "tampered"),
           ("eta", "SRC-002", "Eta", None, None, "ok")]
#: (season, tag, recruit id, athleteId, name, committedTo, rating, ranking, stars, person plan, legacy team, legacy plan,
#: extra raw members)
RECRUITS = [
    (2010, "A", "100001", "1001", "Ann Able", "Alpha State", 0.9512, 10, 4, "ok", "alpha", "agree", {}),
    (2010, "B", "100002", "-2002", "Ben Bold", None, None, None, None, "ok", "", "agree", {}),
    (2011, "C", "300003", None, "Cal Cruz", "Beta Tech", 1, 1, 5, "ok", "beta", "agree", {}),
    (2011, "D", "400004", "4004", "Dee Dunn", "Gamma U", 0.85, 100, 3, "none", "", "absent", {}),
    (2012, "E", "500005", "5005", "Eve Eng", "Delta College", 0.88, 50, 3, "multi", "", "agree", {}),
    (2012, "F", "600006", None, "Fay Fox", "Epsilon", 0.8, 200, 3, "nomap", "", "agree", {}),
    (2013, "G", "700007", "7007", "Gus Gray", "Zeta A&M", 0.9, 20, 4, "conflict", "", "agree", {}),
    (2013, "H", "800008", "8008", "Hal Hart", "Eta", 0.91, 15, 4, "slot_shared", "", "agree", {}),
    (2014, "I", "900009", ABSENT, "Ira Ives", ABSENT, 0.83, 300, 3, "ok", "", "agree", {}),
    (2014, "J", "101010", "1010", NAME_UNICODE, "alpha state", 1.5, 0, 6, "ok", "alpha", "agree", {}),
    (2015, "K", "111111", "1111", "Kai Kim", "Alpha State", 0.97, 5, 5, "ok", "alpha", "disagree", {}),
    (2015, "L", "121212", "1212", "Lou Lane", "Beta Tech", None, 5, 3, "ok", "beta", "absent", {"year": 2016}),
    (2016, "M", "131313", "1313", "Max Moe", "Beta Tech", 0.86, 40, 3, "tampered", "", "agree", {}),
    (2016, "N", "1400014", "-1414", "Ned Nye", " Alpha State", 0.84, 60, 3, "ok", "", "agree", {}),
    (2017, "O", "151515", "1515", "Oz Ott", "Alpha State", 0.95, 8, 4, "ok", "beta", "agree", {}),
    (2017, "P", "161616", "1616", NAME_DIACRITIC, "Alpha State", 0.92, 12, 4, "ok", "alpha", "agree",
     {"recruitType": None, "position": None, "school": None}),
]
PORTAL_SEASONS = (2010, 2011, 2012, 2013, 2014, 2015, 2016)
MISSING = ([("transfer_portal", {"year": 2017})] +
           [(d, {"year": y}) for y in range(2018, 2026) for d in ("recruiting_players", "transfer_portal")] +
           [("coaches", {"minYear": 2010, "maxYear": 2025}), ("coach_seasons", {"minYear": 2010, "maxYear": 2025})])


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def capture_id(dataset: str, year: int) -> str:
    return "cap_" + sha(f"{dataset}|{year}".encode("utf-8"))[:24]


def person_id(slot: str) -> str:
    return "player_" + uuid.uuid5(PEOPLE_NS, slot).hex


def team_id(name: str) -> str:
    return "team_" + uuid.uuid5(CORE_NS, f"core-v1:team:{TEAMS[name]:08d}").hex


def people_finalize(row: dict[str, str]) -> dict[str, str]:
    """The legacy BAT-388 builder's finalize(), restated independently."""
    provenance = {k: row[k] for k in rc.PEOPLE_COLUMNS if k not in {"provenance_sha256", "record_sha256"}}
    row["provenance_sha256"] = sha(json.dumps(provenance, sort_keys=True, separators=(",", ":")).encode())
    record = {k: row[k] for k in rc.PEOPLE_COLUMNS if k != "record_sha256"}
    row["record_sha256"] = sha(json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
    return row


def core_finalize(row: dict[str, str]) -> dict[str, str]:
    """The legacy BAT-387 builder's finalize_row(), restated independently."""
    evidence = "|".join([row["source_system_id"], row["source_entity_key"], row["source_snapshot_ids"],
                         row["source_payload_sha256s"], row["mapping_method"], row["resolution_state"]])
    row["provenance_sha256"] = sha(evidence.encode("utf-8"))
    row["record_sha256"] = sha("\x1f".join(row[c] for c in rc.CORE_COLUMNS if c != "record_sha256").encode("utf-8"))
    return row


def people_row(**values: Any) -> dict[str, str]:
    row = {c: "" for c in rc.PEOPLE_COLUMNS}
    row.update({k: "" if v is None else str(v) for k, v in values.items()})
    row["schema_version"], row["dataset_version"] = "1.0.0", "bat388-people-registry-v1"
    return people_finalize(row)


def core_row(**values: Any) -> dict[str, str]:
    row = {c: "" for c in rc.CORE_COLUMNS}
    row.update({k: "" if v is None else str(v) for k, v in values.items()})
    row["schema_version"], row["dataset_version"] = "1.0.0", "bat387-core-registry-v1"
    return core_finalize(row)


def _csv(columns: tuple[str, ...], rows: list[dict[str, str]]) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(columns), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def raw_row(season: int, tag: str, rid: str, athlete: Any, name: str, committed: Any, rating: Any, ranking: Any,
            stars: Any, extra: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {"id": rid, "name": name, "recruitType": "HighSchool", "year": season,
                           "position": "WR", "school": f"{tag} High", "rating": rating, "ranking": ranking,
                           "stars": stars, "city": "Private City", "stateProvince": "TX", "country": "USA",
                           "height": 72.5, "weight": 190,
                           "hometownInfo": {"latitude": 30.1, "longitude": -96.3, "fipsCode": "48041"}}
    if athlete is not ABSENT:
        row["athleteId"] = athlete
    if committed is not ABSENT:
        row["committedTo"] = committed
    row.update(extra)
    return row


def build_world(base: Path) -> dict[str, Any]:
    data, repo = base / "data", base / "repo"
    data.mkdir(parents=True)
    repo.mkdir(parents=True)
    writes: dict[str, bytes] = {}
    captures, cells = [], []
    arrays: dict[int, list[dict[str, Any]]] = {}
    for season, tag, rid, athlete, name, committed, rating, ranking, stars, *_rest, extra in RECRUITS:
        arrays.setdefault(season, []).append(raw_row(season, tag, rid, athlete, name, committed, rating, ranking,
                                                     stars, extra))
    for dataset, years in (("recruiting_players", sorted(arrays)), ("transfer_portal", PORTAL_SEASONS)):
        for year in years:
            rows = arrays[year] if dataset == "recruiting_players" else []
            payload = json.dumps(rows, ensure_ascii=False).encode("utf-8") if rows else b"[]"
            digest = sha(payload)
            rel = f"raw/SRC-002/bat388-people/{dataset}/{year}/sha256_{digest}.json"
            writes[rel] = payload
            cid = capture_id(dataset, year)
            path = "/recruiting/players" if dataset == "recruiting_players" else "/player/portal"
            receipt = {"attempts": 1, "canonical_request_sha256": sha(cid.encode()), "capture_id": cid,
                       "capture_known_at_utc": "2026-08-10T01:48:07Z", "dataset": dataset,
                       "endpoint_id": "CFBD-GetRecruitingPlayers" if rows or dataset == "recruiting_players"
                       else "CFBD-GetTransferPortal",
                       "historical_coverage_status": "CAPTURED_REQUESTED_PARTITION", "http_status": 200,
                       "immutable_path": rel, "method": "GET", "parameters": {"year": year}, "path": path,
                       "pit_eligibility": "CAPTURE_KNOWN_AT_RECORDED; EVENT_TIME_NORMALIZATION_REQUIRED_BEFORE_PREGAME_USE",
                       "prior_attempt_failures": [], "provider_failure_state": "NONE",
                       "raw_content_type": "application/json; charset=utf-8", "request_id": "req_" + cid[4:],
                       "response_bytes": len(payload),
                       "response_headers": {"content-length": str(len(payload)),
                                            "content-type": "application/json; charset=utf-8",
                                            "date": "Mon, 10 Aug 2026 01:48:07 GMT", "etag": "W/\"x\""},
                       "response_sha256": digest, "result": "SUCCESS", "retrieval_started_at_utc":
                           "2026-08-10T01:48:07Z", "retrieved_at_utc": "2026-08-10T01:48:07Z",
                       "row_count": len(rows), "run_id": "bat388-people-sources-v1", "source_id": "SRC-002",
                       "source_uri": f"https://api.example.invalid{path}?year={year}",
                       "top_level_schema_fields": sorted({k for r in rows for k in r}),
                       "upstream_lineage": "CFBD_PUBLIC_API_RECORD; SOURCE_URL_AND_CAPTURE_ID_PRESERVED"}
            receipt_rel = f"manifests/captures/SRC-002/{cid}.json"
            writes[receipt_rel] = json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8")
            captures.append({**receipt, "capture_manifest_path": receipt_rel})
    acquisition = {"capture_count": len(captures), "captures": captures,
                   "completion_state": "PARTIAL_PROVIDER_QUOTA_PRESERVED", "created_at_utc": "2026-08-10T02:13:51Z",
                   "missing_request_count": len(MISSING),
                   "missing_requests": [{"dataset": d, "parameters": p, "reason": "PROVIDER_MONTHLY_CALL_QUOTA_EXCEEDED"}
                                        for d, p in MISSING],
                   "row_count": sum(len(v) for v in arrays.values()), "run_id": "bat388-people-sources-v1",
                   "schema_version": "1.0.0", "season_max": 2025, "season_min": 2010, "source_id": "SRC-002"}
    writes[rb.ACQUISITION_REL] = json.dumps(acquisition, indent=2, sort_keys=True).encode("utf-8")
    # ---- people registry
    people: list[dict[str, str]] = []
    slot_no = [0]
    plan: dict[str, dict[str, Any]] = {}

    def next_slot() -> str:
        slot_no[0] += 1
        return f"people-v1:player:{slot_no[0]:08d}"
    other_slot = next_slot()
    other_id = person_id(other_slot)
    people.append(people_row(record_type="PERSON", person_type="player", record_id=other_id, canonical_id=other_id,
                             identity_key="PLAYER|SRC-001|99999", assignment_slot=other_slot,
                             mapping_method="OPAQUE_APPEND_ONLY_ASSIGNMENT", resolution_state="AUTO_ACCEPTED_VERIFIED",
                             display_name="Other Person", quality_state="VERIFIED_SOURCE_PERSON_ID",
                             eligibility="CANONICAL_PERSON"))
    for season, tag, rid, athlete, name, committed, *_values, person_plan, legacy_team, legacy_plan, _extra in RECRUITS:
        has_athlete = athlete is not ABSENT and athlete is not None
        key = f"PLAYER|SRC-002|{athlete}" if has_athlete else f"PLAYER|SRC-002|RECRUIT|{rid}"
        entity = athlete if has_athlete else f"RECRUIT:{rid}"
        cid = capture_id("recruiting_players", season)
        slot = next_slot()
        canonical = person_id(slot)
        qualified = person_plan == "ok"
        plan[tag] = {"identity_key": key, "entity_key": entity, "slot": slot, "canonical": canonical,
                     "person_plan": person_plan, "qualified": qualified, "capture_id": cid, "recruit_id": rid}
        if person_plan != "none":
            row = people_row(record_type="PERSON", person_type="player", record_id=canonical, canonical_id=canonical,
                             identity_key=key, assignment_slot=slot, mapping_method="OPAQUE_APPEND_ONLY_ASSIGNMENT",
                             resolution_state="AUTO_ACCEPTED_VERIFIED", display_name=name,
                             quality_state="VERIFIED_SOURCE_PERSON_ID", eligibility="CANONICAL_PERSON")
            if person_plan == "tampered":
                row["record_sha256"] = "0" * 64
            people.append(row)
        if person_plan == "multi":
            second = next_slot()
            people.append(people_row(record_type="PERSON", person_type="player", record_id=person_id(second),
                                     canonical_id=person_id(second), identity_key=key, assignment_slot=second,
                                     mapping_method="OPAQUE_APPEND_ONLY_ASSIGNMENT",
                                     resolution_state="AUTO_ACCEPTED_VERIFIED", display_name=name))
        if person_plan == "slot_shared":
            people.append(people_row(record_type="PERSON", person_type="player", record_id=canonical,
                                     canonical_id=canonical, identity_key="PLAYER|SRC-001|88888", assignment_slot=slot,
                                     mapping_method="OPAQUE_APPEND_ONLY_ASSIGNMENT",
                                     resolution_state="AUTO_ACCEPTED_VERIFIED", display_name="Slot Sharer"))
        if person_plan not in ("none", "nomap"):
            m_canonical, m_slot = (other_id, other_slot) if person_plan == "conflict" else (canonical, slot)
            people.append(people_row(record_type="SOURCE_MAPPING", person_type="player",
                                     record_id="map_" + uuid.uuid5(PEOPLE_OBS_NS,
                                                                    f"SRC-002|{entity}|{m_canonical}").hex,
                                     canonical_id=m_canonical, identity_key=key if person_plan != "conflict" else
                                     "PLAYER|SRC-001|99999", assignment_slot=m_slot, source_system_id="SRC-002",
                                     source_entity_key=entity, mapping_method="RECRUITING_SOURCE_ID",
                                     resolution_state="AUTO_ACCEPTED_VERIFIED", quality_state="VERIFIED_SOURCE_ID_MAPPING",
                                     eligibility="IDENTITY_MAPPING"))
        if legacy_plan != "absent":
            legacy_canonical = canonical if qualified else ""
            legacy_slot = slot if qualified else ""
            if legacy_plan == "disagree":
                legacy_canonical = other_id
            payload_sha = sha(json.dumps(arrays[season], ensure_ascii=False).encode("utf-8"))
            people.append(people_row(record_type="RECRUITING_OBSERVATION", person_type="player",
                                     record_id="obs_" + uuid.uuid5(PEOPLE_OBS_NS, f"recruit|{cid}|{rid}").hex,
                                     canonical_id=legacy_canonical, identity_key=key, assignment_slot=legacy_slot,
                                     source_system_id="SRC-002", source_entity_key=rid,
                                     mapping_method="DIRECT_ATHLETE_OR_RECRUIT_SOURCE_ID",
                                     resolution_state="AUTO_ACCEPTED_VERIFIED", display_name=name,
                                     team_canonical_id=team_id(legacy_team) if legacy_team else "",
                                     team_label="" if committed is ABSENT or committed is None else committed,
                                     season=season, source_capture_ids=cid, source_payload_sha256s=payload_sha))
    coach_slot = "people-v1:coach:00000001"
    people.append(people_row(record_type="PERSON", person_type="coach", record_id="coach_x", canonical_id="coach_x",
                             identity_key="COACH|SRC-002|1", assignment_slot=coach_slot,
                             mapping_method="OPAQUE_APPEND_ONLY_ASSIGNMENT", resolution_state="AUTO_ACCEPTED_VERIFIED"))
    people.append(people_row(record_type="ROSTER_MEMBERSHIP", person_type="player", record_id="obs_roster",
                             canonical_id=plan["A"]["canonical"], season=2024, team_label="Alpha State"))
    people.sort(key=lambda r: (r["record_type"], r["person_type"], r["canonical_id"], r["record_id"]))
    people_bytes = _csv(rc.PEOPLE_COLUMNS, people)
    people_rel = f"canonical/BAT-388/sha256/{sha(people_bytes)}/canonical_people_registry.csv"
    writes[people_rel] = people_bytes
    # ---- core registry
    core: list[dict[str, str]] = []
    for name, number in TEAMS.items():
        if name == "eta":
            continue
        slot = f"core-v1:team:{number:08d}"
        core.append(core_row(record_type="ENTITY", entity_type="team", record_id=team_id(name), canonical_id=team_id(name),
                             identity_key=f"TEAM|SRC-002|{number}", assignment_slot=slot, source_system_id="SRC-002",
                             source_entity_key=str(number),
                             mapping_method="INTERNAL_ASSIGNMENT_LEDGER_FROM_VERIFIED_SOURCE_IDENTITY",
                             resolution_state="AUTO_ACCEPTED_VERIFIED", source_snapshot_ids="snap_teams",
                             source_payload_sha256s="ab" * 32, quality_state="VERIFIED_SOURCE_SCOPED_IDENTITY",
                             eligibility="CORE_REGISTRY"))
    for team, source, alias, start, end, variant in ALIASES:
        canonical = team_id(team)
        normalized = " ".join(alias.lower().replace("&", " ").split())
        key = f"team-alias|{canonical}|{source}|{alias}|{normalized}|{start}|{end}"
        row = core_row(record_type="ALIAS", entity_type="team",
                       record_id="obs_" + uuid.uuid5(CORE_RECORD_NS, key).hex, canonical_id=canonical,
                       source_system_id=source, relationship_type="TEAM_ALIAS", alias=alias, alias_normalized=normalized,
                       effective_from=f"{start:04d}-01-01" if start else "",
                       effective_to_exclusive=f"{end:04d}-01-01" if end else "", season=start or "",
                       mapping_method="VERIFIED_SOURCE_ID_LINKED_ALIAS",
                       resolution_state="REVIEW_REQUIRED" if variant == "review" else "AUTO_ACCEPTED_VERIFIED",
                       source_snapshot_ids=f"snap_{team}", source_payload_sha256s="cd" * 32,
                       quality_state="VERIFIED_ALIAS_OBSERVATION", eligibility="CORE_REGISTRY_HISTORY")
        if variant == "tampered":
            row["record_sha256"] = "1" * 64
        core.append(row)
    core.append(core_row(record_type="ALIAS", entity_type="conference", record_id="obs_conf", canonical_id="conf_x",
                         source_system_id="SRC-002", relationship_type="CONFERENCE_ALIAS", alias="Alpha State",
                         alias_normalized="alpha state", mapping_method="COMPOSITE_CONTEXT",
                         resolution_state="REVIEW_REQUIRED"))
    core_bytes = _csv(rc.CORE_COLUMNS, core)
    core_rel = f"canonical/BAT-387/sha256/{sha(core_bytes)}/canonical_core_registry.csv"
    writes[core_rel] = core_bytes
    writes[rb.LEGACY_BUILDER_REL] = b"# legacy builder stand-in (lineage only)\n"
    for rel, payload in writes.items():
        target = data / Path(*rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    repo_writes = {
        rb.PEOPLE_MANIFEST_REL: json.dumps({"payload": {"external_relative_path": people_rel,
                                                        "sha256": sha(people_bytes), "bytes": len(people_bytes)}},
                                           indent=2, sort_keys=True).encode("utf-8"),
        rb.CORE_MANIFEST_REL: json.dumps({"payload": {"external_relative_path": core_rel, "sha256": sha(core_bytes),
                                                      "bytes": len(core_bytes)}}, indent=2, sort_keys=True).encode(),
        rb.RIGHTS_REL: _csv(("schema_version", *rb.RIGHTS_FIELDS),
                            [{"schema_version": "2.0.0", **{k: "x" for k in rb.RIGHTS_FIELDS},
                              "decision_id": rb.RIGHTS_DECISION_ID, "source_id": "SRC-002",
                              "redistribution_decision": "DO_NOT_PUBLISH_OR_REDISTRIBUTE_RAW_THIRD_PARTY_PAYLOADS"},
                             {"schema_version": "2.0.0", **{k: "y" for k in rb.RIGHTS_FIELDS},
                              "decision_id": "PRIVATE-RESEARCH-SRC-001", "source_id": "SRC-001"}])}
    for rel, payload in repo_writes.items():
        target = repo / Path(*rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return {"base": base, "data": data, "repo": repo, "plan": plan, "people_rel": people_rel, "core_rel": core_rel,
            "teams": {name: team_id(name) for name in TEAMS}, "arrays": arrays}


def contract_for(world: dict[str, Any]) -> dict[str, Any]:
    return rb.make_contract(world["data"], world["repo"], FROZEN)


def write_contract(path: Path, contract: dict[str, Any]) -> Path:
    path.write_bytes(rb.contract_bytes(contract))
    return path


def contract_anchors(path: Path) -> dict[str, Any]:
    _contract, _sha, anchors = rb.load_contract(path)
    return {**anchors, "profile": None}


@contextlib.contextmanager
def captured():
    """stdout as UTF-8 bytes (through a text wrapper with a binary buffer, as the console has) and stderr as text."""
    holder: dict[str, Any] = {"err": io.StringIO()}
    out_buffer = io.BytesIO()
    wrapper = io.TextIOWrapper(out_buffer, encoding="utf-8")
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = wrapper, holder["err"]
    try:
        yield holder
    finally:
        wrapper.flush()
        holder["out"] = out_buffer.getvalue()
        wrapper.detach()
        sys.stdout, sys.stderr = old_out, old_err


def run_build(contract: Path, world: dict[str, Any], out: Path, *extra: str) -> tuple[int, Any, str]:
    argv = ["--contract", str(contract), "--data-root", str(world["data"]), "--repo-root", str(world["repo"]),
            "--output-root", str(out / "canonical" / POP), "--manifest-root", str(out / "manifests" / POP), *extra]
    with captured() as holder:
        code = rb.main(argv, repo_root=world["repo"])
    text = holder["out"].decode("utf-8")
    return code, (json.loads(text) if text.strip() else None), holder["err"].getvalue()


def database_of(result: dict[str, Any]) -> Path:
    return Path(result["release"]["data_dir"]) / rc.DB_FILE


def query(anchors: dict[str, Any] | None, db: Any, *argv: str) -> tuple[int, Any, str]:
    tokens = ["--recruiting-evidence", str(db), *argv] if db is not None else list(argv)
    with captured() as holder:
        code = pq.main(tokens, recruiting_anchors=anchors)
    text = holder["out"].decode("utf-8")
    return code, (json.loads(text) if text.strip() else None), holder["err"].getvalue()


def refusal(err: str) -> str | None:
    for line in reversed(err.strip().splitlines()):
        try:
            value = json.loads(line).get("refused")
        except (ValueError, AttributeError):
            continue
        if value:
            return value
    return None


# --------------------------------------------------------------------------------------------- coordinated forgeries

def read_release(db: Path) -> tuple[dict[str, str], dict[str, list[dict[str, Any]]]]:
    conn = sqlite3.connect(db)
    try:
        meta = dict(conn.execute("SELECT key, value FROM meta"))
        records: dict[str, list[dict[str, Any]]] = {t: [] for t in rc.RECORD_TABLES}
        for table, blob in conn.execute("SELECT record_table, block FROM blocks ORDER BY ord"):
            records[table] += [json.loads(line) for line in zlib.decompress(blob).decode("utf-8").splitlines() if line]
    finally:
        conn.close()
    return meta, records


def rederive(records: dict[str, list[dict[str, Any]]], anchors: dict[str, Any]) -> None:
    """Make a forged release fully coordinated: every qualification re-derived from its (possibly forged) observation
    and its stored witnesses, then the summary and census."""
    sources = {s["source_key"]: s for s in records["sources"]}
    quals = []
    for o, q in zip(records["observations"], records["qualifications"]):
        aliases = [rc.alias_view(v["source_key"], sources[v["source_key"]]["registry_row"],
                                 sources[v["source_key"]]["row"]) for v in q["alias_witnesses"]]
        teams = [rc.team_view(v["source_key"], sources[v["source_key"]]["registry_row"],
                              sources[v["source_key"]]["row"]) for v in q["team_witnesses"]]
        quals.append(rc.qualification_record(o, rc.canonical_line(o), anchors["expected"]["captures"][o["capture_id"]],
                                             q["person_witnesses"], q["mapping_witnesses"],
                                             q["legacy_observation_witnesses"], aliases, teams))
    records["qualifications"] = quals
    records["summary"] = rc.summary_rows(records["observations"], records["qualifications"])
    records["census"] = [rc.census_record(records)]


def forge(db: Path, root: Path, anchors: dict[str, Any], mutate: Callable[[dict[str, list[dict[str, Any]]]], None],
          *, coordinate: bool = False, meta_edit: Callable[[dict[str, str]], None] | None = None,
          raw_lines: Callable[[str, list[str]], list[str]] | None = None) -> Path:
    """A forged release written consistently (new database bytes, table counts, identity document, identity directory
    and manifest) under ``root``; ``coordinate`` re-derives the qualifications, summary and census after ``mutate``."""
    _meta, records = read_release(db)
    records = copy.deepcopy(records)
    mutate(records)
    if coordinate:
        rederive(records, anchors)
    derived = {t: records[t] for t in rc.RECORD_TABLES}
    lines = {t: [rc.canonical_line(r) for r in derived[t]] for t in rc.RECORD_TABLES}
    if raw_lines is not None:
        lines = {t: raw_lines(t, v) for t, v in lines.items()}
    derived["lines"] = lines
    document = rc.content_document(anchors, derived)
    content_identity = sha(rc.canonical_json_bytes(document))
    meta = rc.meta_values(anchors, content_identity, derived)
    if meta_edit is not None:
        meta_edit(meta)
    work = root / "work"
    work.mkdir(parents=True, exist_ok=True)
    temp = work / rc.DB_FILE
    if temp.exists():
        temp.unlink()
    conn = sqlite3.connect(temp)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA journal_mode = OFF")
        for _kind, _name, ddl in rc.DDL:
            conn.execute(ddl)
        conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", sorted(meta.items()))
        rows = []
        grouped: dict[tuple[str, str], tuple[list, list]] = {}
        for table in rc.RECORD_TABLES:
            for record, line in zip(derived[table], lines[table]):
                segment = rc.segment_of(table, record) if isinstance(record.get("request_season"), int) or \
                    table not in rc.SEASONAL_TABLES else str(record.get("request_season"))
                bucket = grouped.setdefault((table, segment), ([], []))
                bucket[0].append(record)
                bucket[1].append(line)
        for ord_, (table, segment) in enumerate(rc.BLOCK_LAYOUT):
            recs, block = grouped.get((table, segment), ([], []))
            data = "".join(line + "\n" for line in block).encode("utf-8")
            rows.append((ord_, table, segment, len(block), rc.record_key(table, recs[0]) if recs else None,
                         rc.record_key(table, recs[-1]) if recs else None, sha(data), zlib.compress(data, 9)))
        conn.executemany("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in rc.TABLES}
    finally:
        conn.close()
    database_doc = rc.database_document(anchors["contract_sha256"], content_identity, sha(temp.read_bytes()), counts)
    identity = sha(rc.canonical_json_bytes(database_doc))
    target = root / "canonical" / POP / "sha256" / identity
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(temp, target / rc.DB_FILE)
    temp.unlink()
    manifest = root / "manifests" / POP / "sha256" / identity / "run_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"identity": identity, "identity_document": database_doc,
                                    "content_identity": content_identity, "content_document": document,
                                    "provenance": {"forged": True}}, indent=1, sort_keys=True, ensure_ascii=False),
                        encoding="utf-8")
    return target / rc.DB_FILE


def find(records: list[dict[str, Any]], **match: Any) -> dict[str, Any]:
    return next(r for r in records if all(r.get(k) == v for k, v in match.items()))
