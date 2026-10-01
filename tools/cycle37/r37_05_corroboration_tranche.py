"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-05 AC07-AC10: a deterministic 120-episode corroboration tranche of the
reparsed Wikimedia career episodes, checked first against every local cache
and then, only for what the caches cannot answer, against official athletics
pages the revision itself cites, within the attempt's coaching request
ceiling.

``select`` stratifies eligible episodes (coaching rows of an FBS or FCS
program overlapping 2000-2026) by division, era (2000-09, 2010-19, 2020-26)
and role group (HC, OC, DC, position), and takes five per stratum by a
seeded digest rank, or all when fewer exist. For each it searches:

* the R37-03 official staff reparse, rows of the same program whose page
  identity confirms that program (official, independent of Wikimedia);
* the CFBD ``/coaches`` cache (head coaches by team id and season): an
  independent secondary source, reported as such and never as official.

``fetch`` then reads official pages cited by the episode's own revision for
episodes still unanswered: a GET per URL, at most the remaining coaching
ceiling, two tries at most for a failing host. Each response is stored
privately with its digest and entered in the cost ledger.

Every episode ends with an outcome and, where it is not corroborated, the
exact fact that remains unconfirmed. No success rate is targeted and none is
manufactured; a wikitext mention is not independent of the revision it is in.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37 import staff_record
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
REPAIRS = ATTEMPT / "evidence" / "repairs"
EPISODES = REPAIRS / "R37_05_CAREER_EPISODES.jsonl"
STAFF = REPAIRS / "R37_03_STAFF_REPARSE_ROWS.jsonl"
CROSSWALK_ROWS = REPAIRS / "R37_03_SOURCE_IDENTITY_ROWS.jsonl"
CFBD_COACHES = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/raw/coaches")
SEED = "R37-05-AC08"
PER_STRATUM = 5
PAGES_PER_EPISODE = 1
ERAS = (("2000-09", 2000, 2009), ("2010-19", 2010, 2019), ("2020-26", 2020, 2026))
GROUPS = ("HC", "OC", "DC", "POSITION")
_URL = re.compile(r"https?://[^\s|\]}<>\"']+", re.I)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def role_group(episode: dict[str, Any]) -> str | None:
    roles = {(a["role"], a.get("occupancy")) for a in episode["assignments"]}
    if ("head_coach", "PRINCIPAL") in roles:
        return "HC"
    if any(role == "offensive_coordinator" and occ in ("PRINCIPAL", "CO_SHARED") for role, occ in roles):
        return "OC"
    if any(role == "defensive_coordinator" and occ in ("PRINCIPAL", "CO_SHARED") for role, occ in roles):
        return "DC"
    coaching = {role for role, _ in roles} - {"player", "administrator", "graduate_assistant", "analyst", "role_not_stated",
                                              "unmapped_title_review_required"}
    return "POSITION" if coaching else None


def stratum(episode: dict[str, Any]) -> tuple[str, str, str] | None:
    if episode["family"] != "COACHING" or episode["population_state"] != "IN_POPULATION_CANDIDATE_EPISODE":
        return None
    start = max(episode["start"], 2000)
    end = episode["end"] if episode["end"] is not None else 2026
    if end < 2000 or start > 2026:
        return None
    division = (episode.get("classification") or {}).get("by_season", {}).get(str(start))
    if division not in ("fbs", "fcs"):
        return None
    era = next(name for name, low, high in ERAS if low <= start <= high)
    group = role_group(episode)
    return (division.upper(), era, group) if group else None


def rank(episode: dict[str, Any]) -> str:
    return sha256_bytes(f"{SEED}|{episode['episode_id']}".encode())


def cfbd_head_coaches() -> dict[tuple[str, int], list[dict[str, Any]]]:
    seasons: dict[tuple[str, int], list[dict[str, Any]]] = collections.defaultdict(list)
    for path in sorted(CFBD_COACHES.iterdir()):
        payload = json.loads(path.read_bytes())
        for coach in payload:
            name = f"{coach.get('firstName') or ''} {coach.get('lastName') or ''}".strip()
            for season in coach.get("seasons") or []:
                seasons[(f"SRC-002:TEAM:{season.get('teamId')}", int(season["year"]))].append(
                    {"name": name, "file": str(path), "file_sha256": sha256_bytes(path.read_bytes()),
                     "school": season.get("school")})
    return seasons


def _person_key(name: str) -> str:
    return staff_record.fold_name(re.sub(r"\s*\(.*\)$", "", name or ""))


def local_evidence(episode: dict[str, Any], staff: dict[tuple[str, str], list[dict[str, Any]]],
                   cfbd: dict[tuple[str, int], list[dict[str, Any]]]) -> dict[str, Any]:
    program = episode["resolution"]["program_id"]
    person = _person_key(episode["person_display"])
    start, end = episode["start"], episode["end"] if episode["end"] is not None else 2026
    roles = {a["role"] for a in episode["assignments"]}
    official, other_role = [], []
    for row in staff.get((program, person), []):
        if row["season"] is None or not start <= row["season"] <= end:
            continue
        hit = {"capture_path": row["capture_path"], "observation_index": row["observation_index"],
               "season": row["season"], "title": row["source_title"],
               "name_byte_span": [(row["binding"].get("name_span") or {}).get("byte_start"),
                                  (row["binding"].get("name_span") or {}).get("byte_end")]}
        (official if roles & {a["role"] for a in row["assignments"]} else other_role).append(hit)
    secondary = []
    if "head_coach" in roles:
        for year in range(start, end + 1):
            for coach in cfbd.get((program, year), []):
                if staff_record.fold_name(coach["name"]) == person:
                    secondary.append({"source": "CFBD /coaches", "year": year, "file": coach["file"],
                                      "file_sha256": coach["file_sha256"]})
    if official:
        outcome = "CORROBORATED_BY_CACHED_OFFICIAL_STAFF_PAGE"
    elif other_role:
        outcome = "OFFICIAL_PAGE_NAMES_THE_PERSON_IN_A_DIFFERENT_ROLE"
    elif secondary:
        outcome = "INDEPENDENT_SECONDARY_ONLY_CFBD_HEAD_COACH_SEASON"
    else:
        outcome = "NOT_FOUND_IN_ANY_LOCAL_CACHE"
    return {"outcome": outcome, "official": official[:5], "official_other_role": other_role[:5],
            "secondary": secondary[:5],
            "searched": ["R37-03 official staff reparse, confirmed-program captures", "CFBD /coaches cache"]}


def select(out: Path) -> dict[str, Any]:
    episodes = read_jsonl(EPISODES)
    pools: dict[tuple[str, str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for episode in episodes:
        key = stratum(episode)
        if key:
            pools[key].append(episode)
    staff: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in read_jsonl(STAFF):
        if row.get("identity_state") == "CONFIRMED_BY_SOURCE_IDENTITY" and row.get("program_id"):
            staff[(row["program_id"], staff_record.fold_name(row["person"]))].append(row)
    cfbd = cfbd_head_coaches()
    tranche, shortfall = [], {}
    for division in ("FBS", "FCS"):
        for era, _, _ in ERAS:
            for group in GROUPS:
                pool = sorted(pools.get((division, era, group), []), key=rank)
                if len(pool) < PER_STRATUM:
                    shortfall[f"{division}|{era}|{group}"] = len(pool)
                for episode in pool[:PER_STRATUM]:
                    tranche.append({
                        "tranche_id": len(tranche) + 1, "stratum": f"{division}|{era}|{group}",
                        "episode_id": episode["episode_id"], "person": episode["person_display"],
                        "page_title": episode["page_title"], "revision": episode["revision"],
                        "program_id": episode["resolution"]["program_id"],
                        "employer_as_written": episode["employer_display"], "role_text": episode["role_text"],
                        "role_basis": episode["role_basis"], "roles": sorted({a["role"] for a in episode["assignments"]}),
                        "interval": [episode["start"], episode["end"]], "raw_file": episode["raw_file"],
                        "local": local_evidence(episode, staff, cfbd),
                    })
    report = {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-05",
              "rows": ["R37-05-AC07", "R37-05-AC08", "R37-05-AC09"], "seed": SEED,
              "eligible_by_stratum": {"|".join(k): len(v) for k, v in sorted(pools.items())},
              "tranche_size": len(tranche), "stratum_shortfall": shortfall,
              "local_outcomes": dict(collections.Counter(item["local"]["outcome"] for item in tranche)),
              "tranche": tranche,
              "independence": ("Official staff captures and CFBD are separate publishers from Wikimedia. A team-season "
                               "article or any other Wikimedia page is the same publisher and is not counted."),
              "inputs": {"episodes_sha256": sha256_bytes(EPISODES.read_bytes()),
                         "staff_sha256": sha256_bytes(STAFF.read_bytes())}}
    _bas_atomic.write_text(out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _official_hosts() -> set[str]:
    hosts = set()
    for row in read_jsonl(CROSSWALK_ROWS):
        identity = row.get("page_identity") or {}
        for url in (identity.get("canonical_href"), row.get("route")):
            host = urlparse(str(url or "")).netloc.lower().removeprefix("www.")
            if host:
                hosts.add(host)
        if identity.get("route_host"):
            hosts.add(str(identity["route_host"]).lower().removeprefix("www."))
    return hosts


def cited_official_urls(raw_file: str, hosts: set[str]) -> list[str]:
    payload = json.loads(Path(raw_file).read_bytes())
    page = next(iter(payload["query"]["pages"].values()))
    text = page["revisions"][0]["slots"]["main"]["*"]
    urls = []
    for url in _URL.findall(text):
        url = url.rstrip(".,;)")
        host = (urlparse(url).hostname or "").lower().rstrip(".").removeprefix("www.")
        if host == "archive.org" or host.endswith(".archive.org"):
            continue  # an archive is a different provider; not used
        # Only an official athletics host or a university domain is official; a
        # staff-looking path on a news or statistics site is not.
        if host in hosts or host.endswith(".edu"):
            urls.append(url)
    return list(dict.fromkeys(urls))


def _promise(url: str, surname: str) -> tuple[int, int]:
    """Try first a page that names the person in its address, then a staff or bio page."""

    lower = url.lower()
    return (0 if surname and surname.lower() in lower else 1,
            0 if re.search(r"/(?:coaches|staff|bio|roster)", lower) else 1)


def fetch(report_path: Path, out: Path, ceiling_remaining: int) -> dict[str, Any]:
    """Read cited official pages through the shared receipted fetcher.

    The fetcher enforces the coaching ceiling in the ledger and the two-try
    rule per route; ``ceiling_remaining`` additionally caps this run.
    """

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import r37_fetch

    report = json.loads(report_path.read_text(encoding="utf-8"))
    hosts = _official_hosts()
    used = 0
    records = []
    for item in report["tranche"]:
        if item["local"]["outcome"] in ("CORROBORATED_BY_CACHED_OFFICIAL_STAFF_PAGE",):
            item["final_outcome"] = item["local"]["outcome"]
            continue
        urls = cited_official_urls(item["raw_file"], hosts)
        item["cited_official_urls"] = urls
        outcome = "NO_OFFICIAL_URL_CITED_BY_THE_REVISION" if not urls else "CITED_OFFICIAL_PAGES_DO_NOT_STATE_IT"
        surname = item["person"].split()[-1] if item["person"].split() else ""
        # The ceiling is spread across episodes: one page each, the most promising.
        tried = sorted(urls, key=lambda u: _promise(u, surname))[:PAGES_PER_EPISODE]
        item["cited_official_urls_tried"] = tried
        if urls and len(tried) < len(urls):
            outcome = "CITED_OFFICIAL_PAGE_TRIED_DOES_NOT_STATE_IT_OTHERS_NOT_TRIED"
        for url in tried:
            if used >= ceiling_remaining:
                outcome = "CEILING_REACHED_BEFORE_THIS_EPISODE"
                break
            try:
                receipt = r37_fetch.fetch(url, "coaching", f"R37-05-AC08 tranche {item['tranche_id']}: page cited by "
                                                           f"{item['page_title']} revision {item['revision']}")
            except r37_fetch.FetchRefused as refused:
                records.append({"url": url, "tranche_id": item["tranche_id"], "result": f"REFUSED: {refused}"})
                if "ceiling" in str(refused):
                    outcome = "CEILING_REACHED_BEFORE_THIS_EPISODE"
                    break
                continue
            used += 1
            if not receipt["http_status"] or not 200 <= receipt["http_status"] < 300:
                records.append({"url": url, "tranche_id": item["tranche_id"], "http_status": receipt["http_status"],
                                "result": f"FAILED: {receipt['error']}"})
                continue
            body = Path(receipt["stored"]).read_bytes()
            digest = receipt["sha256"]
            status = receipt["http_status"]
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body.decode("utf-8", "replace")))
            person = item["person"]
            surname = person.split()[-1] if person.split() else person
            states_person = bool(re.search(re.escape(surname), text, re.I))
            states_years = any(str(year) in text for year in range(item["interval"][0],
                                                                 (item["interval"][1] or 2026) + 1))
            states_employer = bool(re.search(re.escape(item["employer_as_written"].split(" (")[0]), text, re.I))
            records.append({"url": url, "tranche_id": item["tranche_id"], "status": status, "sha256": digest,
                            "states_person": states_person, "states_employer": states_employer,
                            "states_a_year_of_the_interval": states_years})
            if states_person and states_employer and states_years:
                outcome = "CANDIDATE_OFFICIAL_PAGE_STATES_PERSON_EMPLOYER_AND_YEARS"
                item["fetched_evidence"] = {"url": url, "sha256": digest}
                break
        item["final_outcome"] = (item["local"]["outcome"] if item["local"]["outcome"] != "NOT_FOUND_IN_ANY_LOCAL_CACHE"
                                 and outcome.startswith(("NO_OFFICIAL", "CITED_OFFICIAL")) else outcome)
        if item["final_outcome"] not in ("CORROBORATED_BY_CACHED_OFFICIAL_STAFF_PAGE",
                                         "CANDIDATE_OFFICIAL_PAGE_STATES_PERSON_EMPLOYER_AND_YEARS"):
            role = item["role_text"] or ("head coach (infobox convention)"
                                         if item["role_basis"] == "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL"
                                         else "a role the row does not state")
            item["remaining_fact"] = (f"{item['person']} as {role} at {item['employer_as_written']} "
                                      f"{item['interval']}: no independent official statement located")
        time.sleep(1.0)
    report["fetch"] = {"requests_used": used, "ceiling_remaining_before": ceiling_remaining,
                       "records": records, "fetched_at_utc": datetime.now(timezone.utc).isoformat()}
    report["final_outcomes"] = dict(collections.Counter(item.get("final_outcome") for item in report["tranche"]))
    _bas_atomic.write_text(out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("select")
    s.add_argument("--out", type=Path, default=REPAIRS / "R37_05_CORROBORATION_TRANCHE.json")
    f = sub.add_parser("fetch")
    f.add_argument("--report", type=Path, default=REPAIRS / "R37_05_CORROBORATION_TRANCHE.json")
    f.add_argument("--out", type=Path, default=REPAIRS / "R37_05_CORROBORATION_TRANCHE.json")
    f.add_argument("--ceiling-remaining", type=int, required=True)
    args = parser.parse_args(argv)
    result = select(args.out) if args.command == "select" else fetch(args.report, args.out, args.ceiling_remaining)
    print(json.dumps({k: v for k, v in result.items() if k not in ("tranche", "fetch")}, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
