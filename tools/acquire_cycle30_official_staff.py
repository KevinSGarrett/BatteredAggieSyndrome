"""Direct GET of official athletics football staff/coaches HTML.

No scrapfly. Website discovery uses already-cached Wikimedia wikitext.
Ceiling is declared before any request. Personal email/phone is not stored.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    extract_athletics_website_from_wikitext,
    html_is_not_found_shell,
    html_is_waf_challenge,
    match_wikidata_website,
    official_staff_candidate_urls,
    parse_official_staff_html,
    parse_official_staff_json,
    redact_personal_contact,
    role_families_from_title,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402

BUDGET = {
    "max_requests": 900,
    "max_retries": 1,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "sleep_s": 0.2,
    "timeout_s": 15,
}
UA = (
    "BAS-Cycle30-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "official public football staff directories)"
)
UA_BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
WORK = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
RAW = WORK / "raw" / "official_staff"
WIKI = WORK / "raw" / "wikimedia"
OUT = WORK / "outputs"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


API = "https://en.wikipedia.org/w/api.php"


def load_current_wikitext(titles: Sequence[str]) -> dict[str, str]:
    indexed: dict[str, str] = {}
    for title in titles:
        if not title:
            continue
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "ids|timestamp|content",
            "rvslots": "main",
            "titles": title,
            "format": "json",
        }
        url = f"{API}?{urllib.parse.urlencode(params)}"
        cache = WIKI / f"{sha256_json({'url': url})}.json"
        if not cache.is_file():
            continue
        try:
            payload = json.loads(cache.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        pages = (payload.get("query") or {}).get("pages") or {}
        for page in pages.values():
            revisions = page.get("revisions") or []
            if not revisions:
                continue
            text = ((revisions[0].get("slots") or {}).get("main") or {}).get("*") or ""
            text = redact_personal_contact(str(text))
            indexed[title] = text
            indexed[str(page.get("title") or title)] = text
    return indexed


def _staff_request(url: str, user_agent: str, timeout_s: int) -> tuple[bytes, int, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = response.read()
            status = int(response.status)
            final_url = str(response.geturl() or url)
    except urllib.error.HTTPError as exc:
        body = exc.read() or b""
        status = int(exc.code)
        final_url = url
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
        body = b""
        status = 0
        final_url = url
    return body, status, final_url


def fetch_html(
    url: str,
    ledger: list[dict[str, Any]],
    budget: dict[str, Any],
    *,
    cache_only: bool = False,
) -> tuple[bytes, dict[str, Any]]:
    cache = RAW / f"{sha256_json({'url': url})}.html"
    if cache.is_file() and cache.stat().st_size > 0:
        cached_body = cache.read_bytes()
        cached_html = cached_body.decode("utf-8", "replace")
        if not html_is_waf_challenge(cached_html):
            receipt = {
                "route": url,
                "status": "CACHE_HIT",
                "http_status": 200,
                "request_identity_sha256": sha256_json({"url": url}),
                "receipt_identity": sha256_bytes(cached_body),
                "raw_sha256": sha256_bytes(cached_body),
                "cached": True,
                "retrieved_at_utc": utc_now(),
            }
            ledger.append(receipt)
            return cached_body, receipt
    if cache_only:
        receipt = {
            "route": url,
            "status": "CACHE_MISS_SKIPPED",
            "http_status": 0,
            "request_identity_sha256": sha256_json({"url": url}),
            "receipt_identity": sha256_json({"url": url, "cache_only": True}),
            "raw_sha256": "empty",
            "cached": False,
            "retrieved_at_utc": utc_now(),
        }
        ledger.append(receipt)
        return b"", receipt
    live = sum(1 for row in ledger if row.get("status") in {"HTTP_OK", "HTTP_ERROR"})
    if live >= int(budget["max_requests"]):
        raise RuntimeError("official staff request ceiling reached")
    start = utc_now()
    body, status, final_url = _staff_request(url, UA, int(budget["timeout_s"]))
    html = body.decode("utf-8", "replace") if body else ""
    if html_is_waf_challenge(html) or not body:
        retry_body, retry_status, retry_final = _staff_request(
            url, UA_BROWSER, int(budget["timeout_s"])
        )
        time.sleep(float(budget["sleep_s"]))
        if retry_body and not html_is_waf_challenge(
            retry_body.decode("utf-8", "replace")
        ):
            body, status, final_url = retry_body, retry_status, retry_final
    else:
        time.sleep(float(budget["sleep_s"]))
    end = utc_now()
    html = body.decode("utf-8", "replace") if body else ""
    if html_is_waf_challenge(html):
        receipt = {
            "route": url,
            "final_url": final_url,
            "status": "HTTP_WAF_CHALLENGE",
            "http_status": status,
            "request_identity_sha256": sha256_json({"url": url}),
            "receipt_identity": sha256_json(
                {"start": start, "end": end, "status": "waf"}
            ),
            "raw_sha256": "waf_challenge_not_cached",
            "cached": False,
            "retrieved_at_utc": end,
        }
        ledger.append(receipt)
        return b"", receipt
    raw_hash = sha256_bytes(body) if body else "empty"
    receipt = {
        "route": url,
        "final_url": final_url,
        "status": "HTTP_OK" if 200 <= status < 300 else "HTTP_ERROR",
        "http_status": status,
        "request_identity_sha256": sha256_json({"url": url}),
        "receipt_identity": sha256_json(
            {"start": start, "end": end, "raw_sha256": raw_hash, "status": status}
        ),
        "raw_sha256": raw_hash,
        "cached": False,
        "retrieved_at_utc": end,
    }
    ledger.append(receipt)
    RAW.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    return body, receipt


def useful_people(people: list[dict[str, str]]) -> bool:
    return any(
        person.get("role")
        in {"head_coach", "offensive_coordinator", "defensive_coordinator"}
        or role_families_from_title(str(person.get("title") or ""))
        for person in people
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument(
        "--uncaptured-only",
        action="store_true",
        help="Reuse prior CAPTURED rows and live-fetch only remaining programs",
    )
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (WORK / "CYCLE30_OFFICIAL_STAFF_BUDGET.json").write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    programs = load_jsonl(OUT / "CURRENT_2026_PROGRAMS.jsonl")
    wiki_rows = load_jsonl(OUT / "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl")
    wiki_by_program = {str(row.get("program_id")): row for row in wiki_rows}
    if args.limit:
        programs = programs[: args.limit]
    if args.dry_run:
        print("BUDGET_DECLARED", BUDGET["max_requests"], "programs", len(programs))
        return 0
    prior_attempts = {
        str(row.get("program_id")): row
        for row in load_jsonl(OUT / "OFFICIAL_STAFF_HTTP_ATTEMPTS.jsonl")
    }
    prior_people_by_program: dict[str, list[dict[str, Any]]] = {}
    for row in load_jsonl(OUT / "OFFICIAL_STAFF_PARSED.jsonl"):
        prior_people_by_program.setdefault(str(row.get("program_id")), []).append(row)
    titles = [str(row.get("title") or "") for row in wiki_rows]
    wikitext_by_title = load_current_wikitext(titles)
    wikidata_rows = load_jsonl(OUT / "WIKIDATA_P856_WEBSITES.jsonl")
    ledger: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    people_out: list[dict[str, Any]] = []
    try:
        for program in programs:
            pid = str(program.get("program_id") or "")
            if (
                args.uncaptured_only
                and str((prior_attempts.get(pid) or {}).get("status") or "")
                == "CAPTURED"
                and useful_people(prior_people_by_program.get(pid, []))
            ):
                attempts.append(prior_attempts[pid])
                people_out.extend(prior_people_by_program.get(pid, []))
                continue
            wiki = wiki_by_program.get(pid) or {}
            title = str(wiki.get("title") or "")
            wikitext = wikitext_by_title.get(title, "")
            website = (
                extract_athletics_website_from_wikitext(wikitext) if wikitext else None
            )
            if not website:
                website = match_wikidata_website(
                    str(program.get("display_name") or ""), wikidata_rows
                )
            if not website:
                prior = prior_attempts.get(pid) or {}
                if str(prior.get("status") or "") == "CAPTURED":
                    prior_url = str(prior.get("page_url") or "")
                    if prior_url.startswith("http"):
                        parsed_prior = urllib.parse.urlparse(prior_url)
                        website = f"{parsed_prior.scheme}://{parsed_prior.netloc}"
            discovery_receipt = sha256_json(
                {
                    "program_id": pid,
                    "wiki_title": title,
                    "website": website,
                    "wikimedia_revision": wiki.get("wikimedia_revision"),
                }
            )
            if not website:
                attempts.append(
                    {
                        "program_id": pid,
                        "display_name": program.get("display_name"),
                        "classification": program.get("classification"),
                        "declared_route": "official_staff_directory_or_media_guide",
                        "status": "ATTEMPTED_NO_URL",
                        "http_status": None,
                        "receipt_identity": discovery_receipt,
                        "parser": None,
                        "page_url": None,
                        "attempt_count": 1,
                        "reason": "no athletics WebsiteURL in cached Wikimedia wikitext",
                        "artifact_class": "REAL_EVIDENCE",
                    }
                )
                continue
            parsed_people: list[dict[str, str]] = []
            chosen: dict[str, Any] | None = None
            last_receipt: dict[str, Any] | None = None
            for url in official_staff_candidate_urls(website):
                body, receipt = fetch_html(
                    url, ledger, BUDGET, cache_only=args.cache_only
                )
                if int(receipt.get("http_status") or 0) >= 400 or not body:
                    if last_receipt is None:
                        last_receipt = receipt
                    continue
                html = redact_personal_contact(body.decode("utf-8", "replace"))
                if html_is_waf_challenge(html) or html_is_not_found_shell(html):
                    if last_receipt is None or html_is_waf_challenge(html):
                        last_receipt = {
                            **receipt,
                            "status": (
                                "HTTP_WAF_CHALLENGE"
                                if html_is_waf_challenge(html)
                                else "HTTP_NOT_FOUND_SHELL"
                            ),
                        }
                    continue
                last_receipt = receipt
                people: list[dict[str, str]] = []
                stripped = body.lstrip()
                if stripped.startswith(b"{") or stripped.startswith(b"["):
                    try:
                        payload = json.loads(html)
                    except json.JSONDecodeError:
                        payload = None
                    if payload is not None:
                        people = parse_official_staff_json(payload, page_url=url)
                if not people:
                    people = parse_official_staff_html(html, page_url=url)
                if useful_people(people):
                    parsed_people = people
                    chosen = receipt
                    break
                if people and chosen is None:
                    parsed_people = people
                    chosen = receipt
            if chosen and useful_people(parsed_people):
                for person in parsed_people:
                    people_out.append(
                        {
                            "program_id": pid,
                            "display_name": program.get("display_name"),
                            **person,
                            "artifact_class": "REAL_EVIDENCE",
                            "pit_admitted": False,
                        }
                    )
                attempts.append(
                    {
                        "program_id": pid,
                        "display_name": program.get("display_name"),
                        "classification": program.get("classification"),
                        "declared_route": "official_staff_directory_or_media_guide",
                        "status": "CAPTURED",
                        "http_status": chosen.get("http_status"),
                        "receipt_identity": chosen.get("receipt_identity"),
                        "parser": "parse_official_staff_html",
                        "page_url": chosen.get("route"),
                        "attempt_count": 1,
                        "people_count": len(parsed_people),
                        "reason": None,
                        "artifact_class": "REAL_EVIDENCE",
                    }
                )
                continue
            failed_status = int((last_receipt or {}).get("http_status") or 0)
            shell = (
                str((last_receipt or {}).get("status") or "") == "HTTP_NOT_FOUND_SHELL"
            )
            attempts.append(
                {
                    "program_id": pid,
                    "display_name": program.get("display_name"),
                    "classification": program.get("classification"),
                    "declared_route": "official_staff_directory_or_media_guide",
                    "status": (
                        "ATTEMPTED_NOT_FOUND_SHELL"
                        if shell
                        else (
                            "ACQUISITION_FAILED"
                            if failed_status >= 400 or failed_status == 0
                            else "ATTEMPTED_EMPTY_PARSE"
                        )
                    ),
                    "http_status": (last_receipt or {}).get("http_status"),
                    "receipt_identity": (last_receipt or {}).get("receipt_identity")
                    or discovery_receipt,
                    "parser": "parse_official_staff_html",
                    "page_url": (last_receipt or {}).get("route") or website,
                    "attempt_count": 1,
                    "reason": "official HTML attempted; no row-bound HC/OC/DC parse",
                    "artifact_class": "REAL_EVIDENCE",
                }
            )
    except RuntimeError as exc:
        print("CEILING", exc)
    (OUT / "CYCLE30_OFFICIAL_STAFF_LEDGER.json").write_text(
        json.dumps(
            {
                "budget": BUDGET,
                "attempt_count": len(ledger),
                "attempts": ledger,
                "artifact_class": "REAL_EVIDENCE",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT / "OFFICIAL_STAFF_HTTP_ATTEMPTS.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in attempts),
        encoding="utf-8",
    )
    (OUT / "OFFICIAL_STAFF_PARSED.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in people_out),
        encoding="utf-8",
    )
    print(
        "official_staff",
        "programs",
        len(attempts),
        "http_attempts",
        len(ledger),
        "captured",
        sum(1 for row in attempts if row["status"] == "CAPTURED"),
        "people",
        len(people_out),
        "no_url",
        sum(1 for row in attempts if row["status"] == "ATTEMPTED_NO_URL"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
