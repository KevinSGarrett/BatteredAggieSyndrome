"""Independent discontinued-program census from NCAA directory and Wikipedia.

CFBD presence delta is not this census.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402
from aggie_analytics.cycle30.populations import (  # noqa: E402
    ncaa_directory_item_is_discontinued,
    ncaa_directory_item_name,
)


BUDGET = {
    "max_requests": 12,
    "max_retries": 0,
    "concurrency": 1,
    "metered_scraper_credits": 0,
}
UA = (
    "BAS-Cycle30-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "discontinued Division I football census)"
)
NCAA_URLS = (
    "https://web3.ncaa.org/directory/api/directory/memberList?type=12&sportCode=MFB",
    "https://web3.ncaa.org/directory/api/directory/memberList?type=12&sportCode=MFB&division=1",
    "https://web3.ncaa.org/directory/api/directory/memberList?type=12&sportCode=MFB&deactive=Y",
    "https://web3.ncaa.org/directory/api/directory/memberList?sportCode=MFB&status=2",
    "https://web3.ncaa.org/directory/api/directory/memberList?type=17&sportCode=MFB",
    "https://www.ncaa.com/schools-index",
)
WIKI_PAGES = (
    "List of defunct college football teams",
    "List of NCAA Division I FBS football programs",
    "List of NCAA Division I FCS football programs",
    "List of NCAA Division I institutions",
    "List of colleges and universities that have dropped football",
)


WORK = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
RAW = WORK / "raw" / "discontinued"
OUT = WORK / "outputs"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(url: str, ledger: list[dict[str, object]], dest: Path) -> tuple[int, bytes]:
    if dest.is_file():
        body = dest.read_bytes()
        ledger.append(
            {
                "route": url,
                "http_status": 200,
                "cached": True,
                "receipt_identity": sha256_bytes(body),
                "retrieved_at_utc": utc_now(),
            }
        )
        return 200, body
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    start = utc_now()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = int(response.status)
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        body = exc.read() or b""
    except Exception as exc:  # noqa: BLE001
        status = 0
        body = str(exc).encode("utf-8")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    ledger.append(
        {
            "route": url,
            "http_status": status,
            "cached": False,
            "receipt_identity": sha256_bytes(body),
            "retrieved_at_utc": utc_now(),
            "start": start,
        }
    )
    return status, body


def wiki_list_names(wikitext: str) -> list[str]:
    names: list[str] = []
    skip_tokens = ("list of", "category:", "file:", "image:", "wikipedia:")
    for match in re.finditer(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]", wikitext or ""):
        title = match.group(1).strip()
        folded = title.casefold()
        if any(token in folded for token in skip_tokens):
            continue
        if title not in names:
            names.append(title)
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (WORK / "CYCLE30_DISCONTINUED_CENSUS_BUDGET.json").write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.dry_run:
        print("BUDGET_DECLARED", BUDGET["max_requests"])
        return 0
    ledger: list[dict[str, object]] = []
    ncaa_rows: list[dict[str, str]] = []
    for url in NCAA_URLS:
        dest = RAW / f"{sha256_json({'url': url})}.bin"
        status, body = fetch(url, ledger, dest)
        text = body.decode("utf-8", "replace")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("results") or payload.get("orgs") or []
        else:
            items = []
        if not isinstance(items, list):
            items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if not ncaa_directory_item_is_discontinued(item):
                continue
            name = ncaa_directory_item_name(item)
            if name:
                ncaa_rows.append(
                    {
                        "program_name": name,
                        "deactive": str(item.get("deactive") or ""),
                        "reclass_year": str(item.get("reclassYear") or ""),
                        "source_id": "SRC-NCAA-DIRECTORY",
                        "http_status": str(status),
                    }
                )
    wiki_rows: list[dict[str, str]] = []
    for title in WIKI_PAGES:
        params = {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json",
        }
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
        dest = RAW / f"{sha256_json({'url': url})}.json"
        status, body = fetch(url, ledger, dest)
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            continue
        wikitext = ((payload.get("parse") or {}).get("wikitext") or {}).get("*") or ""
        kind = (
            "defunct"
            if "defunct" in title.casefold()
            else "current_fbs_list_not_discontinued"
        )
        for name in wiki_list_names(wikitext):
            wiki_rows.append(
                {
                    "program_name": name,
                    "wikipedia_page": title,
                    "list_kind": kind,
                    "source_id": "SRC-WIKIMEDIA",
                    "http_status": str(status),
                }
            )
    (OUT / "NCAA_DIRECTORY_PROGRAM_ROWS.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in ncaa_rows),
        encoding="utf-8",
    )
    (OUT / "WIKIPEDIA_FORMER_PROGRAM_ROWS.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in wiki_rows),
        encoding="utf-8",
    )
    (OUT / "CYCLE30_DISCONTINUED_CENSUS_LEDGER.json").write_text(
        json.dumps(
            {
                "budget": BUDGET,
                "attempt_count": len(ledger),
                "attempts": ledger,
                "ncaa_rows": len(ncaa_rows),
                "wikipedia_rows": len(wiki_rows),
                "artifact_class": "REAL_EVIDENCE",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        "discontinued",
        "ncaa",
        len(ncaa_rows),
        "wiki",
        len(wiki_rows),
        "attempts",
        len(ledger),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
