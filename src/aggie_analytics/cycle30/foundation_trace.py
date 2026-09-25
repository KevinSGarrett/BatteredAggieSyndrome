"""Raw-to-normalized semantic comparisons for the historical game tranche.

Count presence is not semantic certification. Join raw SRC-002 game captures
to canonical rows and recompute scores, orientation, ties, and site flags.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_file, sha256_json
from aggie_analytics.cycle30.pit_kernel import winner_from_scores

STRATA_SEASONS = (1963, 1968, 1972, 1978, 1985, 1993, 2000, 2006, 2013, 2019, 2023)
NEUTRAL_AND_TIE_SEASONS = (2013, 2019, 2023)
KNOWN_PARENT_EXCLUSIONS = {
    312472199: {
        "canonical_game_id": "SRC-002:GAME:312472199",
        "finding_id": "C26-7A7-FALSE-QUARANTINE-312472199",
        "reason": "KNOWN_PARENT_EXCLUSION",
        "parent_present": False,
        "oriented_payload_present": False,
        "successor_dataset_identity": (
            "8a6f63d20c7d8d3059929088ced4041baca8503ba3b8039badba31ea0e84c52b"
        ),
        "successor_disposition": "RESTORE_FALSE_SUBSTRING_QUARANTINE",
        "pit_feature_eligible": False,
        "note": (
            "Predecessor 46,953-row foundation remains quarantined for this id. "
            "Cycle 26 structured-status successor restored the completed 2011 "
            "Eastern Michigan 41 Howard 9 game. Eligibility is not admission."
        ),
    }
}


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
    per_season: int | None = None,
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
    known_exclusions: int = 0
    duplicate_raw_ids: int = 0
    site_disagreements: int = 0
    body_sha256_example: str | None = None
    seasons_used = sorted(by_season)
    required = set(STRATA_SEASONS + NEUTRAL_AND_TIE_SEASONS)
    for required_season in sorted(required - set(seasons_used)):
        failures.append(
            {
                "season": required_season,
                "reason": "REQUIRED_STRATUM_CAPTURE_ABSENT",
            }
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
            if body_sha256_example is None:
                body_sha256_example = sha256_file(path)
            raw_games = load_raw_games(path)
            seen_ids: set[int] = set()
            if per_season is None:
                selected = list(raw_games)
            else:
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
                    known = KNOWN_PARENT_EXCLUSIONS.get(rid)
                    if known:
                        known_exclusions += 1
                        failures.append(
                            {
                                "season": season,
                                "source_game_id": rid,
                                **known,
                            }
                        )
                    else:
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
                    joined = compare_raw_to_normalized(raw, canonical)
                    if not joined.get("site_flag_agrees"):
                        site_disagreements += 1
                    compared.append(joined)
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
        "known_parent_exclusion_count": known_exclusions,
        "known_parent_exclusions": [
            dict(item) for item in KNOWN_PARENT_EXCLUSIONS.values()
        ],
        "duplicate_raw_ids": duplicate_raw_ids,
        "site_flag_disagreements": site_disagreements,
        "seasons": seasons_used,
        "not_a_count_scan": True,
        "does_not_certify_missing_national_games": True,
        "compared_every_mounted_raw_game_in_open_files": per_season is None,
        "sample": compared[:40],
        "failures": failures[:40],
        "comparison_identity": sha256_json(
            {
                "compared": len(compared),
                "failures": len(failures),
                "site_disagreements": site_disagreements,
                "seasons": seasons_used,
            }
        ),
        "raw_bytes_hashed_on_open": True,
        "body_sha256_example": body_sha256_example or sha256_bytes(b""),
    }


def parent_duplicate_conflict_audit(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Duplicate canonical IDs, pair+date collisions, and site/score conflicts."""

    by_id: dict[str, Mapping[str, Any]] = {}
    duplicate_ids: list[str] = []
    pair_date: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    outcome_failures: list[dict[str, Any]] = []
    for row in rows:
        gid = str(row.get("canonical_game_id") or "")
        if gid in by_id:
            duplicate_ids.append(gid)
        else:
            by_id[gid] = row
        home_pts = row.get("home_points")
        away_pts = row.get("away_points")
        if home_pts is not None and away_pts is not None:
            try:
                winner = winner_from_scores(int(home_pts), int(away_pts))
            except (TypeError, ValueError) as exc:
                outcome_failures.append({"canonical_game_id": gid, "reason": str(exc)})
            else:
                if winner == "TIE" and int(home_pts) != int(away_pts):
                    outcome_failures.append(
                        {"canonical_game_id": gid, "reason": "TIE_ARITHMETIC"}
                    )
        home = str(row.get("home_canonical_team_id") or row.get("home_team_source_id"))
        away = str(row.get("away_canonical_team_id") or row.get("away_team_source_id"))
        day = str(row.get("start_date_utc_text") or "")[:10]
        pair_date[(home, away, day)].append(row)
    groups: list[dict[str, Any]] = []
    site_conflicts = 0
    score_conflicts = 0
    for key, group in pair_date.items():
        ids = [str(item.get("canonical_game_id")) for item in group]
        if len(set(ids)) < 2:
            continue
        scores = {(item.get("home_points"), item.get("away_points")) for item in group}
        neutrals = {item.get("neutral_site") for item in group}
        score_conflict = len(scores) > 1
        site_conflict = len(neutrals) > 1
        if score_conflict:
            score_conflicts += 1
        if site_conflict:
            site_conflicts += 1
        groups.append(
            {
                "home": key[0],
                "away": key[1],
                "calendar_date": key[2],
                "canonical_game_ids": sorted(set(ids)),
                "scores": [list(item) for item in sorted(scores)],
                "neutral_site_values": sorted(str(item) for item in neutrals),
                "score_conflict": score_conflict,
                "site_class_conflict": site_conflict,
                "same_score_distinct_ids": not score_conflict,
            }
        )
    return {
        "artifact_type": "PARENT_DUPLICATE_CONFLICT_AUDIT",
        "artifact_class": "REAL_EVIDENCE",
        "parent_row_count": len(rows),
        "unique_canonical_game_ids": len(by_id),
        "duplicate_canonical_id_count": len(duplicate_ids),
        "pair_calendar_date_collision_groups": len(groups),
        "score_conflict_groups": score_conflicts,
        "site_class_conflict_groups": site_conflicts,
        "outcome_arithmetic_failures": len(outcome_failures),
        "groups": groups,
        "outcome_failures": outcome_failures[:20],
        "not_a_count_scan": True,
    }
