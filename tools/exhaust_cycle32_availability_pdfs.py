"""Exhaust public availability PDF/report links from cached conference pages.

Bounded live PDF fetches. Does not overwrite Cycle30 outputs. Name-only
candidates are not verified roster joins. Policy pages are not reports.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aggie_analytics.cycle30.availability import (  # noqa: E402
    PUBLIC_AVAILABILITY_ROUTES,
    availability_pdf_hrefs,
    extract_candidate_player_rows,
    pdf_plaintext,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402
from tools.acquire_cycle30_official_staff import BUDGET, fetch_html  # noqa: E402

RAW_HTML = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\availability")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
EXTRA = (
    {
        "source_id": "SRC-017-LIVE",
        "conference": "SEC",
        "uri": "https://www.secsports.com/fbreports",
    },
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_path(uri: str) -> Path:
    return RAW_HTML / f"{sha256_json({'url': uri})}.html"


def main() -> int:
    BUDGET["max_requests"] = 24
    ledger: list[dict[str, Any]] = []
    pdf_rows: list[dict[str, Any]] = []
    all_candidates: list[dict[str, Any]] = []
    seen_pdfs: set[str] = set()
    for route in [*PUBLIC_AVAILABILITY_ROUTES, *EXTRA]:
        uri = route["uri"]
        cache = cache_path(uri)
        if not cache.is_file():
            pdf_rows.append(
                {
                    "parent_uri": uri,
                    "source_id": route["source_id"],
                    "disposition": "PARENT_CACHE_MISS",
                    "artifact_class": "BLOCKER_METADATA",
                }
            )
            continue
        html = cache.read_bytes().decode("utf-8", "replace")
        for pdf_uri in availability_pdf_hrefs(html, page_uri=uri, limit=8):
            if pdf_uri.casefold() in seen_pdfs:
                continue
            seen_pdfs.add(pdf_uri.casefold())
            body, receipt = fetch_html(pdf_uri, ledger, BUDGET, cache_only=False)
            candidates: list[dict[str, Any]] = []
            if body.startswith(b"%PDF") or pdf_uri.casefold().endswith(".pdf"):
                text = pdf_plaintext(body) or body.decode("utf-8", "replace")
                candidates = extract_candidate_player_rows(
                    text, source_id=route["source_id"], uri=pdf_uri
                )
            elif body:
                candidates = extract_candidate_player_rows(
                    body.decode("utf-8", "replace"),
                    source_id=route["source_id"],
                    uri=pdf_uri,
                )
            all_candidates.extend(candidates)
            pdf_rows.append(
                {
                    "parent_uri": uri,
                    "pdf_uri": pdf_uri,
                    "source_id": route["source_id"],
                    "conference": route["conference"],
                    "disposition": receipt.get("status"),
                    "http_status": receipt.get("http_status"),
                    "cached": receipt.get("cached"),
                    "player_rows_extracted": len(candidates),
                    "candidate_player_rows": candidates,
                    "joined_to_verified_roster": False,
                    "private_medical_detail_ingested": False,
                    "no_report_means": "UNKNOWN",
                    "page_kind": (
                        "PARSED_PUBLIC_REPORT_OR_ARCHIVE"
                        if candidates
                        else "LINKED_ASSET_NO_PLAYER_ROWS"
                    ),
                    "artifact_class": "REAL_EVIDENCE",
                    "owner": "BAT-324",
                }
            )
    science = OUT / "science"
    science.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "CYCLE32_AVAILABILITY_PDF_EXHAUSTION",
        "as_of_utc": utc_now(),
        "unique_pdf_or_asset_uris": len(seen_pdfs),
        "candidate_player_rows": len(all_candidates),
        "rows": pdf_rows,
        "acquisition_complete": bool(all_candidates),
        "joined_to_verified_roster": False,
        "if_empty": "required acquisition remains BLOCKED, not locally complete",
        "predecessor_not_overwritten": True,
    }
    (science / "CYCLE32_AVAILABILITY_PDF_EXHAUSTION.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "assets": len(seen_pdfs),
                "candidates": len(all_candidates),
                "rows": len(pdf_rows),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
