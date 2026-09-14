"""Cache-first scheme/tenure extraction from existing Wikimedia raw files.

Does not infer missing schemes or compute tenure from incomplete careers.
Wikipedia is attributed retrospective text, not official confirmation or PIT.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.cycle33.scheme_tenure import (
    extract_scheme_tenure_claims,
    summarize_claims,
)
from aggie_analytics.cycle33.wikimedia_raw import WikimediaRawError, wikitext_from_path

CENSUS = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle32\20260911T214000Z"
    r"\science\RAW_SCHEME_TENURE_REFERENCE.json"
)
DEFAULT_OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z\implementation_output\science"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def season_from_title(title: str) -> str | None:
    for token in str(title or "").split():
        if token.isdigit() and len(token) == 4:
            year = int(token)
            if 1869 <= year <= 2026:
                return str(year)
    return None


def main() -> int:
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    rows = census.get("rows") or census.get("observations") or census
    if isinstance(rows, dict):
        rows = rows.get("rows") or []
    claims: list[dict[str, Any]] = []
    page_errors: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    era_counts: Counter[str] = Counter()
    nonempty_scheme_pages = 0
    nonempty_tenure_pages = 0
    for row in rows:
        raw_path = str(row.get("raw_path") or "")
        if not raw_path or raw_path in seen_paths:
            continue
        seen_paths.add(raw_path)
        path = Path(raw_path)
        title = str(row.get("title") or "")
        revision = str(row.get("revision") or "")
        if not path.is_file():
            page_errors.append(
                {"title": title, "raw_path": raw_path, "error": "RAW_MISSING"}
            )
            continue
        try:
            text, revid, page_title = wikitext_from_path(path)
        except (OSError, json.JSONDecodeError, WikimediaRawError) as exc:
            page_errors.append(
                {"title": title, "raw_path": raw_path, "error": str(exc)}
            )
            continue
        season = season_from_title(page_title or title)
        extracted = extract_scheme_tenure_claims(
            text,
            page_title=page_title or title,
            revision_id=revid or revision,
            season=season,
            program_raw=page_title or title,
        )
        if any(
            item.get("claim_kind") == "SCHEME" and item.get("source_text")
            for item in extracted
        ):
            nonempty_scheme_pages += 1
            if season and int(season) < 2013:
                era_counts["pre_2013_scheme_pages"] += 1
            elif season:
                era_counts["2013_or_later_scheme_pages"] += 1
        if any(
            item.get("claim_kind") == "TENURE" and item.get("source_text")
            for item in extracted
        ):
            nonempty_tenure_pages += 1
        claims.extend(extracted)
    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
    jsonl = DEFAULT_OUT / "CYCLE33_SCHEME_TENURE_CLAIMS.jsonl"
    jsonl.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in claims) + "\n",
        encoding="utf-8",
    )
    summary = {
        "artifact_type": "CYCLE33_SCHEME_TENURE_CLAIMS",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "pages_attempted": len(seen_paths),
        "page_errors": len(page_errors),
        "nonempty_scheme_pages": nonempty_scheme_pages,
        "nonempty_tenure_pages": nonempty_tenure_pages,
        "era_counts": dict(era_counts),
        "claims": summarize_claims(claims),
        "wikipedia_is_not_factual_verification": True,
        "not_film_inferred": True,
        "not_causal_coach_effect": True,
        "not_full_national_verification": True,
        "pit_admitted": False,
        "sample_page_errors": page_errors[:20],
    }
    (DEFAULT_OUT / "CYCLE33_SCHEME_TENURE_CLAIMS.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "pages_attempted": summary["pages_attempted"],
                "nonempty_scheme_pages": nonempty_scheme_pages,
                "nonempty_tenure_pages": nonempty_tenure_pages,
                "claim_count": summary["claims"]["claim_count"],
                "nonempty_scheme_count": summary["claims"]["nonempty_scheme_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
