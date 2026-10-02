"""Acquire the three primary program-rename sources named by TP36-01.

``PROGRAM_ALIAS_SOURCE_NOTES.md`` supplies researched leads, not ingested
rows: "Acquire and bind actual source bytes/receipts before implementing
source authority." This tool performs exactly those acquisitions and nothing
else.

Ceiling, declared before the first request: **4 GET requests** drawn from the
Cycle #36 coaching/membership/schemes lane's 50-request allowance. Cache hits
are counted separately and never reset the ledger. There is no paid call, no
scraper credit and no authentication: all four routes are public institutional
pages.

What the bytes can and cannot support is recorded with them. A current
university page is strong evidence for a *retrospective* factual claim -- that
Dixie State and Utah Tech are one institution, effective 2022-07-01 -- and no
evidence at all about what was publishable before an old game. The extracted
effective date is bound to a quoted span in the captured bytes so a reviewer
can check it rather than trust it.
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.program_crosswalk import normalize_name
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402

BUDGET = {
    "lane": "COACHING_MEMBERSHIP_SCHEMES",
    "lane_ceiling": 50,
    "max_requests_here": 4,
    "max_retries": 1,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "paid_api_calls": 0,
    "sleep_s": 1.5,
    "timeout_s": 30,
}
UA = (
    "BAS-Cycle36-ProgramIdentity/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "public institutional name-change announcements)"
)

RAW = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle36\raw\program_renames")

#: Each lead names the canonical program the rename belongs to, the two
#: spellings, and the date pattern the announcement is expected to state.
#: A pattern that does not match leaves the effective date UNKNOWN rather
#: than being filled from the note's prose.
LEADS = [
    {
        "canonical_program_id": "SRC-002:TEAM:3101",
        "slug": "utah_tech",
        "url": "https://umac.utahtech.edu/brandingguide/",
        "former_name": "Dixie State",
        "current_name": "Utah Tech",
        "expected_effective": "2022-07-01",
        "date_patterns": [r"July\s+1,?\s*2022", r"2022-07-01"],
        "note": (
            "Utah Tech official branding guide records the institutional name "
            "change effective July 1, 2022. Institutional rename is not proof "
            "of football classification or coaching tenure."
        ),
    },
    {
        "canonical_program_id": "SRC-002:TEAM:2277",
        "slug": "houston_christian",
        "url": "https://hc.edu/news-and-events/2022/09/21/hbu-changes-name-to-houston-christian-university/",
        "former_name": "Houston Baptist",
        "current_name": "Houston Christian",
        "expected_effective": "2022-09-21",
        "date_patterns": [r"September\s+21,?\s*2022", r"2022[-/]09[-/]21"],
        "note": (
            "University announcement of the HBU to Houston Christian change. "
            "The public announcement date is distinct from the earlier board "
            "decision; public availability is not backdated to the meeting."
        ),
    },
    {
        "canonical_program_id": "SRC-002:TEAM:2837",
        "slug": "east_texas_am_system",
        "url": "https://news.tamus.edu/stories/texas-am-university-system-board-of-regents-approves-name-change-for-texas-am-university-commerce/",
        "former_name": "Texas A&M-Commerce",
        "current_name": "East Texas A&M",
        "expected_effective": "2024-11-07",
        "date_patterns": [r"November\s+7,?\s*2024", r"2024[-/]11[-/]07"],
        "note": (
            "Texas A&M System regents approve the Commerce rename. This is the "
            "Commerce/East Texas institution, NOT Texas A&M University in "
            "College Station."
        ),
    },
    {
        "canonical_program_id": "SRC-002:TEAM:2837",
        "slug": "east_texas_am_faq",
        "url": "https://www.etamu.edu/name-change-faqs/",
        "former_name": "Texas A&M-Commerce",
        "current_name": "East Texas A&M",
        "expected_effective": "2024-11-07",
        "date_patterns": [r"November\s+7,?\s*2024", r"2024[-/]11[-/]07"],
        "note": "University name-change FAQ corroborating the November 7, 2024 change.",
    },
]

_TAG = re.compile(r"<[^>]+>")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def visible_text(raw: bytes) -> str:
    """Rendered text only, with character references resolved.

    Leaving entities encoded was a real defect in this tool's first run: the
    A&M System page writes ``Texas A&#038;M``, which no amount of name
    normalisation turns into ``Texas A&M``, so a present institution read as
    absent. Resolving references is part of reading the bytes, not a
    normalisation choice.
    """

    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1>", " ", text)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)
    text = html_lib.unescape(_TAG.sub(" ", text))
    return re.sub(r"\s+", " ", text)


#: Where a page states when it was published. This is the known-at evidence
#: for the announcement itself and is kept apart from any date in the prose.
_PUBLISHED = (
    re.compile(r'article:published_time"?\s*content="([^"]+)"', re.I),
    re.compile(r'"datePublished"\s*:\s*"([^"]+)"', re.I),
    re.compile(r'<time[^>]*\bdatetime="([^"]+)"[^>]*\bclass="[^"]*published', re.I),
    re.compile(r'<time[^>]*\bclass="[^"]*published[^"]*"[^>]*\bdatetime="([^"]+)"', re.I),
)

#: "effective immediately" makes the announcement date the effective date.
#: Without it, a separate stated effective date is required.
_EFFECTIVE_IMMEDIATE = re.compile(r"effective\s+immediately", re.I)

#: A governing-body decision inside the prose. HBU's page states the board
#: approved the switch on 17 May 2022 while the announcement itself was
#: published on 21 September 2022. Backdating public availability to the
#: meeting is exactly what PROGRAM_ALIAS_SOURCE_NOTES warns against, so the
#: two are captured as different fields.
_BOARD_DECISION = re.compile(
    r"\b(?:board\s+of\s+trustees|board\s+of\s+regents)\b[^.]{0,200}?"
    r"\b(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+\d{1,2},?\s*(20[0-3]\d)\b",
    re.I,
)
_BOARD_DECISION_REVERSED = re.compile(
    r"\bon\s+(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+\d{1,2},?\s*(20[0-3]\d)\b[^.]{0,120}?"
    r"\b(?:board\s+of\s+trustees|board\s+of\s+regents)\b",
    re.I,
)


def published_at(raw: bytes) -> str | None:
    """The page's own stated publication timestamp, if it states one."""

    text = raw.decode("utf-8", errors="replace")
    for pattern in _PUBLISHED:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def board_decision_span(text: str) -> dict[str, Any] | None:
    for pattern in (_BOARD_DECISION, _BOARD_DECISION_REVERSED):
        match = pattern.search(text)
        if match:
            start = max(0, match.start() - 120)
            return {
                "matched_text": match.group(0)[:240],
                "surrounding_span": text[start : match.end() + 160],
            }
    return None


def quoted_span(text: str, pattern: str) -> dict[str, Any] | None:
    match = re.search(pattern, text, re.I)
    if not match:
        return None
    start = max(0, match.start() - 180)
    return {
        "pattern": pattern,
        "matched_text": match.group(0),
        "offset_in_visible_text": match.start(),
        "surrounding_span": text[start : match.end() + 180],
    }


def _ssl_context() -> ssl.SSLContext | None:
    """Trust store for hosts whose chain the interpreter cannot complete.

    The Utah Tech host served a chain the local store could not verify. Using
    the certifi bundle is ordinary certificate handling; verification stays
    ON. Nothing here disables a check or bypasses an access control.
    """

    try:
        import certifi  # noqa: PLC0415 - optional dependency, probed at use
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def fetch(url: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    started = utc_now()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
            body = response.read()
            return {
                "outcome": "RESPONSE",
                "http_status": response.status,
                "retrieved_at_utc": started,
                "bytes": body,
                "final_url": response.geturl(),
                "content_type": response.headers.get("Content-Type"),
                "retry_after": response.headers.get("Retry-After"),
            }
    except urllib.error.HTTPError as error:
        return {
            "outcome": "HTTP_ERROR",
            "http_status": error.code,
            "retrieved_at_utc": started,
            "bytes": b"",
            "retry_after": error.headers.get("Retry-After") if error.headers else None,
            "detail": str(error),
        }
    except Exception as error:  # noqa: BLE001 - network failures are data here
        return {
            "outcome": "TRANSPORT_ERROR",
            "http_status": None,
            "retrieved_at_utc": started,
            "bytes": b"",
            "detail": f"{type(error).__name__}: {error}",
        }


def acquire(out_dir: Path, allow_network: bool) -> dict[str, Any]:
    RAW.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    rename_evidence: dict[str, dict[str, Any]] = {}
    requests_spent = 0
    cache_hits = 0

    for lead in LEADS:
        path = RAW / f"{lead['slug']}.html"
        attempt: dict[str, Any] = {
            "canonical_program_id": lead["canonical_program_id"],
            "url": lead["url"],
            "slug": lead["slug"],
            "cached_path": str(path),
        }
        if path.is_file():
            body = path.read_bytes()
            attempt.update(
                outcome="CACHE_HIT",
                counted_against_ceiling=False,
                http_status=None,
                raw_sha256=hashlib.sha256(body).hexdigest(),
                bytes_len=len(body),
            )
            cache_hits += 1
        elif not allow_network:
            attempt.update(
                outcome="NOT_ATTEMPTED_NETWORK_DISABLED",
                counted_against_ceiling=False,
                raw_sha256=None,
            )
            attempts.append(attempt)
            continue
        elif requests_spent >= int(BUDGET["max_requests_here"]):
            attempt.update(
                outcome="REFUSED_LOCAL_CEILING_REACHED",
                counted_against_ceiling=False,
                raw_sha256=None,
            )
            attempts.append(attempt)
            continue
        else:
            time.sleep(float(BUDGET["sleep_s"]))
            result = fetch(lead["url"], int(BUDGET["timeout_s"]))
            requests_spent += 1
            body = result.get("bytes") or b""
            attempt.update(
                outcome=result["outcome"],
                counted_against_ceiling=True,
                http_status=result.get("http_status"),
                retrieved_at_utc=result.get("retrieved_at_utc"),
                final_url=result.get("final_url"),
                content_type=result.get("content_type"),
                retry_after=result.get("retry_after"),
                detail=result.get("detail"),
                bytes_len=len(body),
                raw_sha256=hashlib.sha256(body).hexdigest() if body else None,
            )
            if result["outcome"] == "RESPONSE" and result.get("http_status") == 200 and body:
                _bas_atomic.write_bytes(path, body)
            else:
                attempts.append(attempt)
                continue

        raw_bytes = path.read_bytes()
        text = visible_text(raw_bytes)
        normalized = normalize_name(text)
        spans = [
            span
            for span in (quoted_span(text, pattern) for pattern in lead["date_patterns"])
            if span
        ]
        board = board_decision_span(text)
        publication = published_at(raw_bytes)
        immediate = bool(_EFFECTIVE_IMMEDIATE.search(text))
        former_present = normalize_name(lead["former_name"]) in normalized
        current_present = normalize_name(lead["current_name"]) in normalized

        # The effective date is only as good as what the bytes state. Three
        # distinct facts are kept apart rather than collapsed into one date:
        #   * the announcement's own publication time (known-at);
        #   * a governing-body decision date stated in the prose;
        #   * the date the new name takes effect.
        if spans and immediate:
            effective_basis = "ANNOUNCEMENT_DATE_STATED_EFFECTIVE_IMMEDIATELY"
            effective_start = lead["expected_effective"]
        elif spans:
            effective_basis = "EFFECTIVE_DATE_STATED_IN_THE_BYTES"
            effective_start = lead["expected_effective"]
        elif publication and publication[:10] == lead["expected_effective"]:
            effective_basis = "PUBLICATION_DATE_OF_THE_ANNOUNCEMENT"
            effective_start = publication[:10]
        else:
            effective_basis = "EFFECTIVE_DATE_NOT_STATED_IN_THESE_BYTES"
            effective_start = None

        attempt.update(
            effective_date_spans=spans,
            effective_immediately_stated=immediate,
            publication_known_at=publication,
            board_decision_evidence=board,
            former_name_present_in_bytes=former_present,
            current_name_present_in_bytes=current_present,
            effective_basis=effective_basis,
            effective_start=effective_start,
            effective_bound=bool(effective_start) and current_present and former_present,
            public_availability_is_not_the_board_meeting=(
                "The board decision date, when the page states one, records a "
                "governing-body vote. It is not the date the new name became "
                "publicly available and is never used as the effective start."
            ),
        )
        if attempt["effective_bound"]:
            evidence_span = (
                spans[0]["surrounding_span"][:400]
                if spans
                else text[:400]
            )
            entry = rename_evidence.setdefault(
                lead["canonical_program_id"],
                {"canonical_program_id": lead["canonical_program_id"], "names": []},
            )
            shared = {
                "source_url": lead["url"],
                "source_sha256": attempt["raw_sha256"],
                "evidence_span": evidence_span,
                "effective_basis": effective_basis,
                "publication_known_at": publication,
                "board_decision_evidence": board,
                "note": lead["note"],
            }
            entry["names"].append(
                {
                    "name": lead["former_name"],
                    "effective_start": None,
                    "effective_end": effective_start,
                    **shared,
                }
            )
            entry["names"].append(
                {
                    "name": lead["current_name"],
                    "effective_start": effective_start,
                    "effective_end": None,
                    **shared,
                }
            )
        attempts.append(attempt)

    artifact = {
        "artifact_type": "CYCLE36_PROGRAM_RENAME_SOURCE_ACQUISITION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "budget": BUDGET,
        "requests_spent": requests_spent,
        "cache_hits": cache_hits,
        "attempts": attempts,
        "rename_evidence": rename_evidence,
        "limits": (
            "A current institutional page supports a retrospective factual "
            "identity claim. It is not point-in-time evidence about what was "
            "publishable before any past game, and it says nothing about "
            "football classification or coaching tenure."
        ),
        "not_merged": (
            "SRC-002:TEAM:2837 (East Texas A&M, formerly Texas A&M-Commerce) "
            "is a different institution from SRC-002:TEAM:245 (Texas A&M, "
            "College Station) and is never merged with it."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "CYCLE36_PROGRAM_RENAME_SOURCES.json"
    _bas_atomic.write_text(target, 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Permit up to the declared request ceiling; without it only cache is read.",
    )
    args = parser.parse_args()
    artifact = acquire(args.out_dir, args.allow_network)
    print(
        json.dumps(
            {
                "requests_spent": artifact["requests_spent"],
                "cache_hits": artifact["cache_hits"],
                "attempts": [
                    {
                        "slug": a["slug"],
                        "outcome": a["outcome"],
                        "http_status": a.get("http_status"),
                        "effective_bound": a.get("effective_bound"),
                    }
                    for a in artifact["attempts"]
                ],
                "programs_with_bound_rename": sorted(artifact["rename_evidence"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
