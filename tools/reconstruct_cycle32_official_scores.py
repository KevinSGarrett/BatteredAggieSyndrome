"""Reconstruct remaining Week 1 official finals from cached NCAA.com scoreboards.

Independent of WEEK1_REMAINING_FINALS_ATTEMPTS.json keying. stats.ncaa.org
contest IDs are not ncaa.com contest IDs. 403 game pages remain fail-closed.
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

from aggie_analytics.cycle30.acquisition import (  # noqa: E402
    match_ncaa_com_contest,
    parse_ncaa_com_scoreboard_contests,
)
from aggie_analytics.cycle30.hashing import sha256_bytes  # noqa: E402
from aggie_analytics.cycle30.scoring import (  # noqa: E402
    ScoringError,
    _bind_scores_from_same_page,
)

RAW = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\ncaa")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
SCOREBOARDS = (
    ("2026/00", RAW / "scoreboard-2026-00.html"),
    ("2026/01", RAW / "scoreboard-2026-01.html"),
    ("2026/02", RAW / "scoreboard-2026-02.html"),
    ("2026/03", RAW / "scoreboard-2026-03.html"),
)
REMAINING = (
    {
        "stats_ncaa_org_contest_id": "6594400",
        "home_names": ("florida st", "florida st.", "florida state", "florida-st"),
        "away_names": ("smu",),
        "label": "SMU at Florida St.",
    },
    {
        "stats_ncaa_org_contest_id": "6602874",
        "home_names": ("wisconsin", "wisconsin badgers"),
        "away_names": ("notre dame", "notre-dame", "notre dame fighting irish"),
        "label": "Notre Dame at Wisconsin",
    },
    {
        "stats_ncaa_org_contest_id": "6620581",
        "home_names": ("ole miss", "ole-miss", "mississippi"),
        "away_names": ("louisville",),
        "label": "Louisville at Ole Miss",
    },
)
ERROR_PAGES = {
    "6594400": RAW / "6594400.error-403.html",
    "6602874": RAW / "6602874.error-403.html",
    "6620581": RAW / "6620581.error-403.html",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parsed_pages: list[dict[str, Any]] = []
    all_contests: list[dict[str, Any]] = []
    for week, path in SCOREBOARDS:
        if not path.is_file():
            parsed_pages.append(
                {"week": week, "path": str(path), "status": "RAW_CAPTURE_MISSING"}
            )
            continue
        body = path.read_bytes()
        text = body.decode("utf-8", "replace")
        contests = parse_ncaa_com_scoreboard_contests(text)
        all_contests.extend(contests)
        parsed_pages.append(
            {
                "week": week,
                "path": str(path),
                "raw_sha256": sha256_bytes(body),
                "contest_count": len(contests),
                "terminal_count": sum(
                    1
                    for row in contests
                    if row.get("terminal_state") == "TERMINAL_STATUS_ESTABLISHED"
                ),
            }
        )
    reconstructed: list[dict[str, Any]] = []
    for item in REMAINING:
        stats_id = item["stats_ncaa_org_contest_id"]
        found = None
        source_week = None
        source_body = b""
        source_text = ""
        for week, path in SCOREBOARDS:
            if not path.is_file():
                continue
            body = path.read_bytes()
            text = body.decode("utf-8", "replace")
            contests = parse_ncaa_com_scoreboard_contests(text)
            matched = match_ncaa_com_contest(
                contests,
                home_names=item["home_names"],
                away_names=item["away_names"],
            )
            if matched is None:
                swapped = match_ncaa_com_contest(
                    contests,
                    home_names=item["away_names"],
                    away_names=item["home_names"],
                )
                if swapped is not None:
                    matched = {**swapped, "orientation_note": "PAGE_HOME_AWAY_NOT_HINT"}
            if matched is not None:
                found = matched
                source_week = week
                source_body = body
                source_text = text
                break
        error_page = ERROR_PAGES.get(stats_id)
        error_403 = bool(error_page and error_page.is_file())
        bind_ok = False
        bind_error = None
        stats_id_on_page = False
        if found is not None:
            page_id = str(found.get("ncaa_com_contest_id") or "")
            try:
                _bind_scores_from_same_page(
                    page_text=source_text,
                    contest_id=page_id,
                    home_points=int(found["home_points"]),
                    away_points=int(found["away_points"]),
                    body=source_body,
                )
                bind_ok = True
            except ScoringError as exc:
                bind_error = str(exc)
            try:
                _bind_scores_from_same_page(
                    page_text=source_text,
                    contest_id=stats_id,
                    home_points=int(found["home_points"]),
                    away_points=int(found["away_points"]),
                    body=source_body,
                )
                stats_id_on_page = True
            except ScoringError:
                stats_id_on_page = False
        reconstructed.append(
            {
                "label": item["label"],
                "stats_ncaa_org_contest_id": stats_id,
                "stats_ncaa_org_page": "HTTP_403_CAPTURED" if error_403 else "MISSING",
                "ncaa_com_week": source_week,
                "ncaa_com_contest": found,
                "bind_scores_from_same_page": bind_ok,
                "bind_error": bind_error,
                "stats_ncaa_org_id_present_on_ncaa_com_page": stats_id_on_page,
                "trust_classification": "UNTRUSTED_SHADOW",
                "operator_hold": "SCIENTIFIC_OPERATOR_HOLD_ACTIVE",
                "artifact_class": "REAL_EVIDENCE",
            }
        )
    science = OUT / "science"
    science.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "CYCLE32_OFFICIAL_FINAL_RECONSTRUCTION",
        "as_of_utc": utc_now(),
        "scoreboard_pages": parsed_pages,
        "ncaa_com_contests_parsed": len(all_contests),
        "remaining_denominator": len(REMAINING),
        "reconstructed_bind_ok": sum(
            1 for row in reconstructed if row.get("bind_scores_from_same_page")
        ),
        "stats_ncaa_org_ids_are_not_ncaa_com_ids": all(
            not row.get("stats_ncaa_org_id_present_on_ncaa_com_page")
            for row in reconstructed
            if row.get("ncaa_com_contest")
        ),
        "rows": reconstructed,
        "predecessor_attempts_not_overwritten": str(
            Path(
                r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs\WEEK1_REMAINING_FINALS_ATTEMPTS.json"
            )
        ),
        "all_affected_rows_reconstructed": all(
            row.get("bind_scores_from_same_page") for row in reconstructed
        ),
    }
    (science / "CYCLE32_OFFICIAL_FINAL_RECONSTRUCTION.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "contests_parsed": len(all_contests),
                "remaining": len(REMAINING),
                "bind_ok": payload["reconstructed_bind_ok"],
                "stats_ids_on_ncaa_com": payload["stats_ncaa_org_ids_are_not_ncaa_com_ids"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
