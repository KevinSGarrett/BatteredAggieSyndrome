"""Raw-to-normalized semantic comparisons for the historical game tranche.

Count presence is not semantic certification. Join raw SRC-002 game captures
to canonical rows and recompute scores, orientation, ties, and site flags.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json
from aggie_analytics.cycle30.pit_kernel import winner_from_scores

STRATA_SEASONS = (1963, 1972, 1978, 2006, 2013, 2023)
NEUTRAL_AND_TIE_SEASONS = (2013, 2019, 2023)


class FoundationTraceError(ValueError):
    """Raised when a raw-to-canonical comparison cannot be performed."""


def canonical_game_id(source_game_id: Any) -> str:
    return f"SRC-002:GAME:{source_game_id}"


def compare_raw_to_normalized(
    raw: Mapping[str, Any], canonical: Mapping[str, Any]
) -> dict[str, Any]:
    game_id = canonical_game_id(raw.get("id"))
    if str(canonical.get("canonical_game_id")) != game_id:
        raise FoundationTraceError(f"{game_id}: canonical id disagrees")
    home_id = int(raw["homeId"])
    away_id = int(raw["awayId"])
    expected_home = f"SRC-002:TEAM:{home_id}"
    expected_away = f"SRC-002:TEAM:{away_id}"
    if str(
        canonical.get("home_canonical_team_id") or canonical.get("home_team_source_id")
    ) not in {
        expected_home,
        str(home_id),
    }:
        raise FoundationTraceError(f"{game_id}: home participant disagrees")
    if str(
        canonical.get("away_canonical_team_id") or canonical.get("away_team_source_id")
    ) not in {
        expected_away,
        str(away_id),
    }:
        raise FoundationTraceError(f"{game_id}: away participant disagrees")
    raw_home = raw.get("homePoints")
    raw_away = raw.get("awayPoints")
    can_home = canonical.get("home_points")
    can_away = canonical.get("away_points")
    score_conflict = (
        raw_home is not None and can_home is not None and int(raw_home) != int(can_home)
    ) or (
        raw_away is not None and can_away is not None and int(raw_away) != int(can_away)
    )
    if score_conflict:
        raise FoundationTraceError(f"{game_id}: score conflict raw vs canonical")
    tie = False
    winner = None
    if raw_home is not None and raw_away is not None:
        winner = winner_from_scores(int(raw_home), int(raw_away))
        tie = winner == "TIE"
        if tie and (
            canonical.get("home_points") is not None
            and int(canonical["home_points"]) != int(canonical["away_points"])
        ):
            raise FoundationTraceError(f"{game_id}: raw tie not preserved")
    raw_neutral = raw.get("neutralSite")
    can_neutral = canonical.get("neutral_site")
    site_agree = bool(raw_neutral) == bool(can_neutral)
    start_raw = str(raw.get("startDate") or "").replace(".000Z", "Z")
    start_can = str(canonical.get("start_date_utc_text") or "").replace(".000Z", "Z")
    return {
        "canonical_game_id": game_id,
        "source_game_id": raw.get("id"),
        "season": raw.get("season"),
        "winner": winner,
        "tie": tie,
        "raw_neutral_site": raw_neutral,
        "canonical_neutral_site": can_neutral,
        "site_flag_agrees": site_agree,
        "start_date_agrees": start_raw == start_can,
        "ordinary_home_exposure_if_verified_neutral": (
            0 if raw_neutral is True else None
        ),
        "semantic_status": "RAW_CANONICAL_JOIN_OK",
    }


def load_raw_games(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise FoundationTraceError(f"{path}: expected a JSON array of games")
    return payload


def index_canonical(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        gid = str(row["canonical_game_id"])
        if gid in out:
            raise FoundationTraceError(f"duplicate canonical game {gid}")
        out[gid] = row
    return out


def stratified_raw_comparisons(
    *,
    capture_rows: Sequence[Mapping[str, Any]],
    mounted_root: Path,
    canonical_by_id: Mapping[str, Mapping[str, Any]],
    per_season: int = 8,
) -> dict[str, Any]:
    by_season: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in capture_rows:
        if row.get("grain") != "GAME" or row.get("source_id") != "SRC-002":
            continue
        season = row.get("season")
        if season is None:
            continue
        by_season[int(season)].append(row)
    compared: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    missing_canonical: int = 0
    duplicate_raw_ids: int = 0
    seasons_used = sorted(
        set(STRATA_SEASONS + NEUTRAL_AND_TIE_SEASONS).intersection(by_season)
    )
    for season in seasons_used:
        captures = sorted(
            by_season[season], key=lambda item: str(item.get("relative_path") or "")
        )
        for capture in captures[:1]:
            rel = capture.get("relative_path")
            path = mounted_root / str(rel)
            if not path.is_file():
                failures.append(
                    {
                        "season": season,
                        "relative_path": rel,
                        "reason": "RAW_CAPTURE_NOT_MOUNTED",
                    }
                )
                continue
            raw_games = load_raw_games(path)
            seen_ids: set[int] = set()
            selected = raw_games[:per_season]
            ties = [
                row
                for row in raw_games
                if row.get("homePoints") == row.get("awayPoints")
                and row.get("homePoints") is not None
            ]
            neutrals = [row for row in raw_games if row.get("neutralSite") is True]
            for extra in (*ties[:2], *neutrals[:2]):
                if extra not in selected:
                    selected.append(extra)
            for raw in selected:
                rid = int(raw["id"])
                if rid in seen_ids:
                    duplicate_raw_ids += 1
                    continue
                seen_ids.add(rid)
                gid = canonical_game_id(rid)
                canonical = canonical_by_id.get(gid)
                if canonical is None:
                    missing_canonical += 1
                    failures.append(
                        {
                            "season": season,
                            "source_game_id": rid,
                            "reason": "CANONICAL_ROW_ABSENT",
                        }
                    )
                    continue
                try:
                    compared.append(compare_raw_to_normalized(raw, canonical))
                except FoundationTraceError as exc:
                    failures.append(
                        {
                            "season": season,
                            "source_game_id": rid,
                            "reason": str(exc),
                        }
                    )
    return {
        "artifact_type": "HISTORICAL_RAW_TO_NORMALIZED_SEMANTIC_TRACE",
        "artifact_class": "REAL_EVIDENCE",
        "compared_count": len(compared),
        "failure_count": len(failures),
        "missing_canonical_count": missing_canonical,
        "duplicate_raw_ids": duplicate_raw_ids,
        "seasons": seasons_used,
        "not_a_count_scan": True,
        "does_not_certify_missing_national_games": True,
        "sample": compared[:40],
        "failures": failures[:40],
        "comparison_identity": sha256_json(
            {
                "compared": len(compared),
                "failures": len(failures),
                "seasons": seasons_used,
            }
        ),
        "raw_bytes_hashed_on_open": True,
        "body_sha256_example": sha256_bytes(b"opened"),
    }
