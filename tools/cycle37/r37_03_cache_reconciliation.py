"""Cycle #37 - Attempt #2 - ACTUAL_STATE

W37R-04 / R37-03: reconcile the official-staff capture cache with the ledgers
that should explain it.

The cache names every file by its request identity, sha256 of the canonical
JSON {"url": url} (tools/acquire_cycle30_official_staff.py). The Cycle 30
acquisition ledger declares 1,098 of those identities. The other 1,042 files
carry no declared identity. The file dates (2026-09-07 to 09-11) span several
runs of the same acquisition tool, and each run rewrote the ledger, so the
receipts of earlier runs are gone.

A file name is a one-way hash, so a URL can be recovered only by hashing
candidates and finding an exact match. The candidates are:

1. every route and final URL in the ledger;
2. the tool's own candidate staff URLs for every declared website and every
   host the ledger or the attempts name;
3. every link in every cached page, including the PDF links the tool follows,
   iterated until no new file is identified.

An exact hash match identifies the URL cryptographically, however the
candidate was produced. Each undeclared file ends in exactly one of these
states:

* URL_RECOVERED_ROUTE_CANDIDATE: a staff route the tool itself generates, from
  an earlier run whose receipt was overwritten;
* URL_RECOVERED_FROM_THE_PAGE_S_OWN_CANONICAL_URL: the page's canonical link
  or og:url (or a scheme/www/slash spelling of it) reproduces the name;
* URL_RECOVERED_LINKED_FROM_A_CACHED_PAGE: a page or PDF another capture
  links to;
* UNIDENTIFIED: no candidate reproduces the name.

Byte-identical duplicates are listed separately. A recovered URL identifies a
request; it does not make the capture evidence for any program, and no program
is assigned here.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import html as htmllib
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    html_is_not_found_shell,
    official_staff_candidate_urls,
    staff_pdf_hrefs,
)
from aggie_analytics import atomic_io as _bas_atomic
from aggie_analytics.cycle30.hashing import sha256_json  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
WORK = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work")
CACHE = WORK / "raw" / "official_staff"
LEDGER = WORK / "outputs" / "CYCLE30_OFFICIAL_STAFF_LEDGER.json"
ATTEMPTS = WORK / "outputs" / "OFFICIAL_STAFF_HTTP_ATTEMPTS.jsonl"
WIKIDATA = WORK / "outputs" / "WIKIDATA_P856_WEBSITES.jsonl"
HREF = re.compile(r"""(?:href|src)\s*=\s*["']([^"'#\s]+)""", re.I)
SELF_URL = re.compile(
    r"""<link[^>]+rel=["']canonical["'][^>]*href=["']([^"']+)|<meta[^>]+property=["']og:url["'][^>]*content=["']([^"']+)""",
    re.I)


def jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def absolute(href: str, page_url: str) -> str | None:
    href = htmllib.unescape(href.strip())
    if href.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None
    if href.startswith("//"):
        href = "https:" + href
    url = urllib.parse.urljoin(page_url, href) if page_url else href
    return url if url.startswith("http") else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence/repairs/R37_03_CACHE_RECONCILIATION.json")
    args = parser.parse_args(argv)
    files = {p.stem: p for p in CACHE.iterdir() if p.is_file()}
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))["attempts"]
    attempts = jsonl(ATTEMPTS)
    declared = {row["request_identity_sha256"]: row for row in ledger}

    url_of: dict[str, tuple[str, str]] = {}

    def offer(url: str | None, how: str) -> None:
        if not url:
            return
        stem = sha256_json({"url": url})
        if stem in files and stem not in url_of:
            url_of[stem] = (url, how)

    for row in ledger:
        offer(row.get("route"), "LEDGER_ROUTE")
        offer(row.get("final_url"), "LEDGER_FINAL_URL")
    websites: set[str] = set()
    for row in ledger + attempts:
        for key in ("route", "final_url", "page_url"):
            parsed = urllib.parse.urlparse(str(row.get(key) or ""))
            if parsed.scheme and parsed.netloc:
                websites.add(f"{parsed.scheme}://{parsed.netloc}")
                websites.add(urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", "")))
    for row in jsonl(WIKIDATA):
        for key in ("website", "url", "p856", "value"):
            value = str(row.get(key) or "")
            if value.startswith("http"):
                websites.add(value.rstrip("/"))
    # A page often names itself: its canonical link or og:url. Those hosts
    # widen the website set, and small spelling variants of the self-named
    # URL are hashed too (scheme, www, trailing slash).
    self_named: dict[str, list[str]] = {}
    linked_hosts: set[str] = set()
    for stem, path in files.items():
        if path.suffix != ".html":
            continue
        text = path.read_bytes()[:400_000].decode("utf-8", "replace")
        names = [htmllib.unescape(a or b) for a, b in SELF_URL.findall(text)]
        self_named[stem] = names
        # Every host any cached page links to is a website the tool might
        # have been given in an earlier run.
        for href in HREF.findall(text):
            parsed = urllib.parse.urlparse(htmllib.unescape(href))
            if parsed.scheme in ("http", "https") and parsed.netloc:
                linked_hosts.add(f"{parsed.scheme}://{parsed.netloc}")
        for name in names:
            parsed = urllib.parse.urlparse(name)
            if parsed.scheme and parsed.netloc:
                websites.add(f"{parsed.scheme}://{parsed.netloc}")
    for website in sorted(websites):
        for url in official_staff_candidate_urls(website):
            offer(url, "ROUTE_CANDIDATE")
    for website in sorted(linked_hosts - websites):
        for url in official_staff_candidate_urls(website):
            offer(url, "ROUTE_CANDIDATE_FOR_A_LINKED_HOST")
    for stem, names in self_named.items():
        for name in names:
            parsed = urllib.parse.urlparse(name)
            if not (parsed.scheme and parsed.netloc):
                continue
            hosts = {parsed.netloc, parsed.netloc.removeprefix("www."), "www." + parsed.netloc.removeprefix("www.")}
            paths = {parsed.path, parsed.path.rstrip("/"), parsed.path.rstrip("/") + "/"}
            for scheme in ("https", "http"):
                for host in hosts:
                    for path_ in paths:
                        offer(urllib.parse.urlunparse((scheme, host, path_, "", parsed.query, "")), "SELF_NAMED_URL")
    # Links, to a fixpoint: a newly identified page can link to another file.
    scanned: set[str] = set()
    while True:
        before = len(url_of)
        for stem, path in files.items():
            if stem in scanned or path.suffix != ".html":
                continue
            page_url = (url_of.get(stem) or (None, None))[0]
            if page_url is None:
                continue
            scanned.add(stem)
            text = path.read_bytes().decode("utf-8", "replace")
            for href in HREF.findall(text):
                offer(absolute(href, page_url), "LINKED_FROM_A_CACHED_PAGE")
            for href in staff_pdf_hrefs(text, page_url=page_url, limit=1000):
                offer(href, "LINKED_FROM_A_CACHED_PAGE")
        if len(url_of) == before:
            break

    # Why only a few declared captures carry a program claim: the tool tries
    # several candidate routes per program and records one chosen capture in
    # the attempts file; the others stay in the ledger unclaimed.
    chosen_receipts = {a.get("receipt_identity") for a in attempts if a.get("program_id")}
    attempt_hosts = {urllib.parse.urlparse(str(a.get("page_url") or "")).netloc.removeprefix("www.")
                     for a in attempts if a.get("page_url")}

    def declared_role(row: dict[str, Any]) -> str:
        if row.get("receipt_identity") in chosen_receipts and row.get("status") != "HTTP_ERROR":
            return "CHOSEN_CAPTURE_OF_A_PROGRAM_ATTEMPT"
        host = urllib.parse.urlparse(str(row.get("final_url") or row.get("route") or "")).netloc.removeprefix("www.")
        if host in attempt_hosts:
            return "CANDIDATE_TRIED_FOR_AN_ATTEMPTED_PROGRAM_NOT_CHOSEN"
        return "CANDIDATE_ON_A_HOST_NO_ATTEMPT_NAMES"

    content = {stem: hashlib.sha256(path.read_bytes()).hexdigest() for stem, path in files.items()}
    by_content: dict[str, list[str]] = collections.defaultdict(list)
    for stem, digest in content.items():
        by_content[digest].append(stem)
    rows, states = [], collections.Counter()
    for stem, path in sorted(files.items()):
        is_declared = stem in declared
        recovered = url_of.get(stem)
        if is_declared:
            state = "DECLARED_BY_THE_CYCLE30_LEDGER"
        elif recovered and recovered[1] in ("ROUTE_CANDIDATE", "ROUTE_CANDIDATE_FOR_A_LINKED_HOST",
                                            "LEDGER_ROUTE", "LEDGER_FINAL_URL"):
            state = "URL_RECOVERED_ROUTE_CANDIDATE"
        elif recovered and recovered[1] == "SELF_NAMED_URL":
            state = "URL_RECOVERED_FROM_THE_PAGE_S_OWN_CANONICAL_URL"
        elif recovered:
            state = "URL_RECOVERED_LINKED_FROM_A_CACHED_PAGE"
        else:
            state = "UNIDENTIFIED"
        twins = [s for s in by_content[content[stem]] if s != stem]
        body = path.read_bytes()
        kind = ("NON_HTML" if path.suffix != ".html" else
                "NOT_FOUND_SHELL" if html_is_not_found_shell(body.decode("utf-8", "replace")) else "HTML")
        states[state] += 1
        title = re.search(rb"<title[^>]*>(.*?)</title>", body[:200_000], re.S | re.I)
        rows.append({"file": path.name, "request_identity": stem, "state": state,
                     "declared_role": declared_role(declared[stem]) if is_declared else None,
                     "page_title": htmllib.unescape(title.group(1).decode("utf-8", "replace")).strip()[:160]
                     if title else None,
                     "url": recovered[0] if recovered else (declared.get(stem) or {}).get("route"),
                     "recovered_by": recovered[1] if recovered and not is_declared else None,
                     "content_sha256": content[stem], "bytes": len(body), "kind": kind,
                     "byte_identical_to": twins,
                     "mtime_date": __import__("datetime").date.fromtimestamp(path.stat().st_mtime).isoformat()})
    undeclared = [r for r in rows if r["state"] != "DECLARED_BY_THE_CYCLE30_LEDGER"]
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-03", "finding": "W37R-04",
        "cache": str(CACHE), "files": len(files), "declared_identities": len(declared),
        "declared_files_present": sum(1 for s in declared if s in files),
        "states": dict(states),
        "declared_by_role": dict(collections.Counter(r["declared_role"] for r in rows if r["declared_role"])),
        "undeclared_by_kind": dict(collections.Counter(f'{r["state"]}|{r["kind"]}' for r in undeclared).most_common()),
        "undeclared_by_date": dict(sorted(collections.Counter(r["mtime_date"] for r in undeclared).items())),
        "undeclared_with_a_byte_identical_twin": sum(1 for r in undeclared if r["byte_identical_to"]),
        "undeclared_hosts": dict(collections.Counter(
            urllib.parse.urlparse(r["url"]).netloc for r in undeclared if r["url"]).most_common(40)),
        "program_claims_before": {"attempt_records": len(attempts),
                                  "distinct_payloads_claimed": len({a.get("receipt_identity") for a in attempts
                                                                    if a.get("program_id")})},
        "rule": "An exact hash match identifies a request. It is not evidence for any program; none is assigned.",
        "rows": rows,
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("rows", "undeclared_hosts")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
