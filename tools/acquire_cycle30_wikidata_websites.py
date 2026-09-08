"""Wikidata P856 official-website discovery for current programs missing WebsiteURL.

SPARQL plus per-program search. Cached. No scrapfly.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    extract_official_website_from_wikidata_entity,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402

BUDGET = {
    "max_requests": 50,
    "max_retries": 0,
    "concurrency": 1,
    "metered_scraper_credits": 0,
}
QUERIES = (
    """
SELECT ?itemLabel ?website WHERE {
  ?item wdt:P31 wd:Q6979593 .
  ?item wdt:P856 ?website .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
""",
)
UA = (
    "BAS-Cycle30-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "Wikidata P856 official websites)"
)
WORK = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
RAW = WORK / "raw" / "wikidata"
OUT = WORK / "outputs"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(url: str, ledger: list[dict[str, Any]], accept: str) -> tuple[int, bytes]:
    cache = RAW / f"{sha256_json({'url': url})}.json"
    if cache.is_file():
        body = cache.read_bytes()
        ledger.append(
            {
                "route": url.split("?", 1)[0],
                "http_status": 200,
                "cached": True,
                "receipt_identity": sha256_bytes(body),
                "request_identity_sha256": sha256_json({"url": url}),
                "retrieved_at_utc": utc_now(),
            }
        )
        return 200, body
    if len([row for row in ledger if not row.get("cached")]) >= int(
        BUDGET["max_requests"]
    ):
        raise RuntimeError("Wikidata request ceiling reached")
    request = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": accept}
    )
    start = utc_now()
    with urllib.request.urlopen(request, timeout=60) as response:
        status = int(response.status)
        body = response.read()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    ledger.append(
        {
            "route": url.split("?", 1)[0],
            "http_status": status,
            "cached": False,
            "receipt_identity": sha256_bytes(body),
            "request_identity_sha256": sha256_json({"url": url}),
            "start": start,
            "retrieved_at_utc": utc_now(),
        }
    )
    return status, body


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (WORK / "CYCLE30_WIKIDATA_WEBSITE_BUDGET.json").write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.dry_run:
        print("BUDGET_DECLARED", BUDGET["max_requests"])
        return 0
    ledger: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    status = 0
    try:
        for query in QUERIES:
            params = {"query": query, "format": "json"}
            url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(params)
            status, body = fetch(
                url, ledger, "application/sparql-results+json"
            )
            payload = json.loads(body.decode("utf-8"))
            for row in ((payload.get("results") or {}).get("bindings")) or []:
                label = ((row.get("itemLabel") or {}).get("value")) or ""
                website = ((row.get("website") or {}).get("value")) or ""
                lowered = label.casefold()
                if any(
                    token in lowered
                    for token in (
                        "footballer",
                        "soccer",
                        "national football team",
                        "football club",
                    )
                ):
                    continue
                key = (label.casefold(), website.casefold())
                if label and website and key not in seen:
                    seen.add(key)
                    rows.append(
                        {
                            "itemLabel": label,
                            "website": website,
                            "source_id": "SRC-WIKIDATA-P856",
                            "artifact_class": "REAL_EVIDENCE",
                        }
                    )
        missing = [
            row
            for row in load_jsonl(OUT / "OFFICIAL_STAFF_HTTP_ATTEMPTS.jsonl")
            if str(row.get("status") or "") == "ATTEMPTED_NO_URL"
        ]
        for program in missing:
            name = str(program.get("display_name") or "").strip()
            if not name:
                continue
            website = None
            label = name
            for suffix in (" college football", " athletics"):
                search = urllib.parse.urlencode(
                    {
                        "action": "wbsearchentities",
                        "search": f"{name}{suffix}",
                        "language": "en",
                        "format": "json",
                        "type": "item",
                        "limit": 5,
                    }
                )
                search_url = f"https://www.wikidata.org/w/api.php?{search}"
                status, body = fetch(search_url, ledger, "application/json")
                hits = json.loads(body.decode("utf-8")).get("search") or []
                qid = None
                for hit in hits:
                    hit_label = str(hit.get("label") or "").casefold()
                    description = str(hit.get("description") or "").casefold()
                    if any(
                        token in hit_label
                        for token in ("footballer", "soccer", "football club")
                    ):
                        continue
                    if "soccer" in description:
                        continue
                    if name.casefold() in hit_label or "football" in hit_label or "athletics" in hit_label:
                        qid = hit.get("id")
                        break
                if not qid:
                    continue
                entity_url = (
                    "https://www.wikidata.org/wiki/Special:EntityData/"
                    f"{qid}.json"
                )
                status, body = fetch(entity_url, ledger, "application/json")
                entities = (json.loads(body.decode("utf-8")).get("entities") or {})
                entity = entities.get(qid) or {}
                website = extract_official_website_from_wikidata_entity(entity)
                label = ((entity.get("labels") or {}).get("en") or {}).get("value") or name
                if website:
                    break
            if not website:
                continue
            key = (label.casefold(), website.casefold())
            if key not in seen:
                seen.add(key)
                rows.append(
                    {
                        "itemLabel": label,
                        "website": website,
                        "program_id": program.get("program_id"),
                        "source_id": "SRC-WIKIDATA-P856",
                        "artifact_class": "REAL_EVIDENCE",
                    }
                )
    except RuntimeError as exc:
        print("CEILING", exc)
    (OUT / "WIKIDATA_P856_WEBSITES.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (OUT / "CYCLE30_WIKIDATA_WEBSITE_LEDGER.json").write_text(
        json.dumps(
            {
                "budget": BUDGET,
                "attempt_count": len(ledger),
                "attempts": ledger,
                "row_count": len(rows),
                "artifact_class": "REAL_EVIDENCE",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print("wikidata_p856", len(rows), "attempts", len(ledger), "status", status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
