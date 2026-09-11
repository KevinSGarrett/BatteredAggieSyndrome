"""Cache-first availability successor. Does not overwrite Cycle30 outputs."""

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

from aggie_analytics.cycle30.availability import (  # noqa: E402
    PUBLIC_AVAILABILITY_ROUTES,
    availability_pdf_hrefs,
    extract_candidate_player_rows,
    pdf_plaintext,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402

RAW = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\availability")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_path(uri: str) -> Path:
    return RAW / f"{sha256_json({'url': uri})}.html"


def main() -> int:
    rows: list[dict[str, Any]] = []
    all_candidates: list[dict[str, Any]] = []
    missing_cache: list[str] = []
    extra = (
        {
            "source_id": "SRC-017-LIVE",
            "conference": "SEC",
            "uri": "https://www.secsports.com/fbreports",
        },
    )
    for route in [*PUBLIC_AVAILABILITY_ROUTES, *extra]:
        uri = route["uri"]
        cache = cache_path(uri)
        if not cache.is_file():
            missing_cache.append(uri)
            rows.append(
                {
                    "source_id": route["source_id"],
                    "conference": route["conference"],
                    "uri": uri,
                    "disposition": "CACHE_MISS_NOT_FETCHED",
                    "player_rows_extracted": 0,
                    "page_kind": "POLICY_OR_ARCHIVE_PAGE",
                    "artifact_class": "BLOCKER_METADATA",
                }
            )
            continue
        body = cache.read_bytes()
        decoded = body.decode("utf-8", "replace")
        candidates = extract_candidate_player_rows(
            decoded, source_id=route["source_id"], uri=uri
        )
        for pdf_uri in availability_pdf_hrefs(decoded, page_uri=uri, limit=8):
            pdf_cache = cache_path(pdf_uri)
            if not pdf_cache.is_file():
                continue
            pdf_body = pdf_cache.read_bytes()
            text = pdf_plaintext(pdf_body) or pdf_body.decode("utf-8", "replace")
            candidates.extend(
                extract_candidate_player_rows(
                    text, source_id=route["source_id"], uri=pdf_uri
                )
            )
        all_candidates.extend(candidates)
        looks_like_report = any(
            token in decoded.casefold()
            for token in (
                "availability report",
                "player availability",
                "gameday availability",
                "fb reports",
                "fbreports",
            )
        )
        rows.append(
            {
                "source_id": route["source_id"],
                "conference": route["conference"],
                "uri": uri,
                "disposition": "CACHE_HIT_PARSED",
                "http_status": 200,
                "receipt_identity": sha256_bytes(body),
                "player_rows_extracted": len(candidates),
                "candidate_player_rows": candidates,
                "looks_like_availability_surface": looks_like_report,
                "page_kind": "POLICY_OR_ARCHIVE_PAGE"
                if not candidates
                else "PARSED_PUBLIC_REPORT_OR_ARCHIVE",
                "joined_to_verified_roster": False,
                "private_medical_detail_ingested": False,
                "no_report_means": "UNKNOWN",
                "artifact_class": "REAL_EVIDENCE",
                "owner": "BAT-324",
            }
        )
    science = OUT / "science"
    science.mkdir(parents=True, exist_ok=True)
    (science / "CYCLE32_AVAILABILITY_CACHE_PARSE.json").write_text(
        json.dumps(
            {
                "artifact_type": "CYCLE32_AVAILABILITY_CACHE_PARSE",
                "as_of_utc": utc_now(),
                "route_count": len(rows),
                "candidate_player_rows": len(all_candidates),
                "cache_misses": missing_cache,
                "rows": rows,
                "predecessor_not_overwritten": True,
                "acquisition_complete": bool(all_candidates) and not missing_cache,
                "if_empty": "required acquisition remains BLOCKED, not locally complete",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidates": len(all_candidates),
                "cache_misses": len(missing_cache),
                "routes": len(rows),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
