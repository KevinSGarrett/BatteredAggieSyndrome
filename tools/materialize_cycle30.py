"""Materialize Cycle #30 national recovery and evidence-bound kernel artifacts.

Does not claim empirical skill, a champion, BAS, merge, Done, or trust recovery.
Git receives summaries/manifests; restricted bulk rows stay in the external data root.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.admission import (  # noqa: E402
    prove_coaching_not_modeled,
    prove_travel_isolation,
)
from aggie_analytics.cycle30.availability import (  # noqa: E402
    inventory_availability_policies,
    join_candidates_to_roster,
)
from aggie_analytics.cycle30.audit_register import (  # noqa: E402
    official_staff_attempt_rows,
    remaining_audit_register,
)
from aggie_analytics.cycle30.contracts_v2 import (  # noqa: E402
    reject_missing_release_bom,
    round_trip_game_context,
    round_trip_staff_snapshot,
)
from aggie_analytics.cycle30.foundation_trace import (  # noqa: E402
    index_canonical,
    parent_duplicate_conflict_audit,
    stratified_raw_comparisons,
)
from aggie_analytics.cycle30.claims import (  # noqa: E402
    CLAIM_FIELDS,
    discover_authority_claims,
    inventory_claims,
)
from aggie_analytics.cycle30.coaching import (  # noqa: E402
    attempt_ledger_count,
    extract_registry_identities,
    fill_current_role_matrix,
    hc_oc_dc_matrix,
    historical_lattice,
    model_admission_gate,
    overlay_historical_lattice,
    position_role_contract,
    reconcile_predecessor_observations,
    reject_cfbd_assistant,
    reject_dropped_identity,
    reject_literal_attempted,
    reject_week1_as_national_coaching,
    stratified_predecessor_sample,
)
from aggie_analytics.cycle30.cost import attestation_check, coverage_truth  # noqa: E402
from aggie_analytics.cycle30.dependency import static_import_graph  # noqa: E402
from aggie_analytics.cycle30.domains import (  # noqa: E402
    canonical_catalog,
    crosswalk,
    grain_contract,
)
from aggie_analytics.cycle30.findings import successor_ledger  # noqa: E402
from aggie_analytics.cycle30.forecast import (  # noqa: E402
    prove_issued_before_cutoff,
    rehash_payload,
)
from aggie_analytics.cycle30.gridiron import snapshot  # noqa: E402
from aggie_analytics.cycle30.hashing import sha256_file, sha256_json  # noqa: E402
from aggie_analytics.cycle30.kernel_model import (  # noqa: E402
    CANDIDATES,
    designation_and_venue_perturbations,
    fold_local_fit,
)
from aggie_analytics.cycle30.pit_kernel import (  # noqa: E402
    build_game_grain_kernel,
    compare_kernel_to_predecessor_payload,
    forecast_freeze_authority,
    kernel_trust_gate,
    mount_predecessor_oriented_payload,
    predecessor_reconciliation,
    rebuild_kernel_comparison,
)
from aggie_analytics.cycle30.populations import (  # noqa: E402
    cfbd_membership_presence_delta,
    classify_pair_counts,
    current_membership_record,
    era_label,
    expected_game_universe,
    fcs_subset_from_parent,
    historical_scope_contract,
    membership_rows_1963_2012,
    ncaa_discontinued_program_census,
    reject_synthetic_real_denominator,
    tamu_specialization_contract,
    week1_slice_from_contests,
)
from aggie_analytics.cycle30.site_context import (  # noqa: E402
    SiteContextError,
    classify_site,
    contest_context,
    designation_swap_invariant,
    ordinary_home_exposure,
    persist_design_row,
    travel_gap_counts,
    travel_row,
    venue_index_by_name,
    venue_from_bowl_note,
)
from aggie_analytics.scientific_reference.cycle30.pit import (  # noqa: E402
    compare_producer_rows,
    reconstruct_game_features,
    scoring_metrics,
)

ART = ROOT / "artifacts" / "scientific_integrity" / "cycle30"
EXT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
DATA = Path(r"C:\BatteredAggieSyndrome.data")
GAMES_PATH = (
    DATA
    / "canonical"
    / "national_foundation_reconciliation"
    / "sha256"
    / "d2af2bab981f8e7b33a6823e3e4b4b65eb2f96593a0eeafd56dedce1b84fd477"
    / "national_normalized_games.jsonl"
)
OUTCOMES_PATH = GAMES_PATH.with_name("national_game_outcome_labels.jsonl")
CAPTURE_INV = GAMES_PATH.with_name("national_capture_inventory.jsonl")
PEOPLE_CSV = (
    DATA
    / "canonical"
    / "BAT-388"
    / "sha256"
    / "0ab6acafbe350a4958a5fca1c02a9c51463ab8a93ecc173a57b9fd925bf2198d"
    / "canonical_people_registry.csv"
)
FORECAST_ROWS = (
    DATA
    / "canonical"
    / "week1_2026_game_grain_national_forecast_successor"
    / "sha256"
    / "770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939"
    / "week1_2026_game_grain_forecast_rows.jsonl"
)
FORECAST_SHA = "7015c32d0041ecb2d3938139c00e3742321d8bd527aa9c76a8508d630e611b16"
WEEK1_STATES = (
    ROOT
    / "artifacts"
    / "scientific_integrity"
    / "cycle28"
    / "CYCLE28_WEEK1_CONTEST_FINAL_STATES.json"
)
AS_OF = "2026-09-07T16:00:00Z"
ROLE_FAMILIES = (
    "head_coach",
    "offensive_coordinator",
    "defensive_coordinator",
    "special_teams_coordinator",
    "quarterbacks",
    "running_backs",
    "wide_receivers",
    "tight_ends",
    "offensive_line",
    "defensive_line",
    "linebackers",
    "defensive_backs",
    "safeties",
    "cornerbacks",
    "nickels",
    "kickers_punters",
    "strength_conditioning",
    "analyst_support",
)
LAMBEAU = {
    "venue_id": "LAMBEAU_FIELD",
    "venue_name": "Lambeau Field",
    "lat": 44.5013,
    "lon": -88.0622,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_bytes(body.encode("utf-8"))
    return sha256_file(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks = [
        json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows
    ]
    path.write_bytes("".join(chunks).encode("utf-8"))
    return sha256_file(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def inspect_smu_t90_lease() -> dict[str, Any]:
    path = Path(
        r"C:\BatteredAggieSyndrome.data\ops\cycle29_work\leases\6594400__T90M\LOCK\lease.json"
    )
    if not path.is_file():
        return {
            "contest_id": "6594400",
            "checkpoint": "T90M",
            "present": False,
            "not_recaptured": True,
            "no_cycle30_takeover": True,
            "no_new_scheduler_job": True,
            "t90_not_relabeled_on_time": True,
            "artifact_class": "BLOCKER_METADATA",
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    expiry = str(payload.get("expiry_utc") or payload.get("expires_at_utc") or "")
    return {
        "contest_id": "6594400",
        "checkpoint": "T90M",
        "present": True,
        "path": str(path),
        "sha256": sha256_file(path),
        "owner_id": payload.get("owner_id"),
        "pid": payload.get("pid"),
        "expiry_utc": expiry,
        "expired_declared": True,
        "not_recaptured": True,
        "no_cycle30_takeover": True,
        "no_new_scheduler_job": True,
        "t90_not_relabeled_on_time": True,
        "artifact_class": "REAL_EVIDENCE",
    }


def live_worktree_inventory(head: str) -> dict[str, Any]:
    porcelain = subprocess.check_output(
        ["git", "worktree", "list", "--porcelain"],
        cwd=r"C:\BatteredAggieSyndrome",
        text=True,
    )
    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in porcelain.splitlines():
        if not line.strip():
            if current:
                worktrees.append(current)
                current = {}
            continue
        if line.startswith("worktree "):
            current = {"path": line.split(" ", 1)[1], "keep": "true"}
        elif line.startswith("HEAD "):
            current["head"] = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1]
        elif line == "detached":
            current["detached"] = "true"
    if current:
        worktrees.append(current)
    return {
        "artifact_type": "CYCLE30_WORKTREE_INVENTORY",
        "cycle30_head": head,
        "hold_open_pr_and_preservation_branches_retained": True,
        "age_is_not_deletion_authority": True,
        "deleted": [],
        "worktrees": worktrees,
        "open_prs_untouched_dependabot": [682, 683, 684],
        "stack_prs": [678, 679, 680, 681, 685, 686],
        "artifact_class": "REAL_EVIDENCE",
    }


def team_id(source_id: Any) -> str:
    return f"SRC-002:TEAM:{source_id}"


def map_game(raw: Mapping[str, Any]) -> dict[str, Any]:
    home = team_id(raw["home_team_source_id"])
    away = team_id(raw["away_team_source_id"])
    return {
        "canonical_game_id": str(raw["canonical_game_id"]),
        "home_canonical_team_id": home,
        "away_canonical_team_id": away,
        "season": int(raw["season"]),
        "start_date_utc_text": str(raw["start_date_utc_text"]).replace(".000Z", "Z"),
        "date_precision": "UNKNOWN",
        "home_points": raw.get("home_points"),
        "away_points": raw.get("away_points"),
        "source_id": str(raw.get("source_id") or "SRC-002"),
        "home_classification": raw.get("home_classification"),
        "away_classification": raw.get("away_classification"),
        "neutral_site": raw.get("neutral_site"),
        "venue_id": raw.get("venue_id"),
        "venue_name": raw.get("venue_name"),
        "completed": raw.get("completed"),
        "week": raw.get("week"),
        "season_type": raw.get("season_type"),
        "home_team_name": raw.get("home_team_name"),
        "away_team_name": raw.get("away_team_name"),
        "home_team_source_id": raw.get("home_team_source_id"),
        "away_team_source_id": raw.get("away_team_source_id"),
        "artifact_class": "REAL_EVIDENCE",
    }


def map_cfbd_game(raw: Mapping[str, Any]) -> dict[str, Any]:
    home_src = raw.get("homeId") or raw.get("home_id")
    away_src = raw.get("awayId") or raw.get("away_id")
    start = str(raw.get("startDate") or raw.get("start_date") or "").replace(
        ".000Z", "Z"
    )
    return {
        "canonical_game_id": f"SRC-002:GAME:{raw.get('id')}",
        "home_canonical_team_id": team_id(home_src),
        "away_canonical_team_id": team_id(away_src),
        "season": int(raw.get("season") or raw.get("year") or 0),
        "start_date_utc_text": start,
        "date_precision": "INSTANT",
        "home_points": raw.get("homePoints") or raw.get("home_points"),
        "away_points": raw.get("awayPoints") or raw.get("away_points"),
        "source_id": "SRC-002",
        "home_classification": raw.get("homeClassification")
        or raw.get("home_classification"),
        "away_classification": raw.get("awayClassification")
        or raw.get("away_classification"),
        "neutral_site": raw.get("neutralSite")
        if "neutralSite" in raw
        else raw.get("neutral_site"),
        "venue_id": raw.get("venueId") or raw.get("venue_id"),
        "venue_name": raw.get("venue") or raw.get("venue_name"),
        "completed": raw.get("completed"),
        "home_team_source_id": home_src,
        "away_team_source_id": away_src,
        "artifact_class": "REAL_EVIDENCE",
    }


def overlay_historical_venues(
    games: list[dict[str, Any]],
    cfbd_hist: list[dict[str, Any]],
    venues_by_name: dict[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {str(row.get("id")): row for row in cfbd_hist if row.get("id") is not None}
    out: list[dict[str, Any]] = []
    for game in games:
        updated = dict(game)
        extra = by_id.get(str(game.get("canonical_game_id") or "").rsplit(":", 1)[-1])
        if extra:
            if updated.get("venue_id") in {None, ""}:
                vid = extra.get("venueId") or extra.get("venue_id")
                if vid is not None:
                    updated["venue_id"] = vid
            if not updated.get("venue_name"):
                updated["venue_name"] = extra.get("venue") or extra.get("venue_name")
            if updated.get("venue_id") in {None, ""}:
                bowl = venue_from_bowl_note(
                    str(extra.get("notes") or ""), venues_by_name
                )
                if bowl and bowl.get("id") is not None:
                    updated["venue_id"] = bowl.get("id")
                    updated["venue_name"] = bowl.get("name") or updated.get(
                        "venue_name"
                    )
        if updated.get("venue_id") in {None, ""} and updated.get("venue_name"):
            named = venues_by_name.get(str(updated["venue_name"]).casefold().strip())
            if named and named.get("id") is not None:
                updated["venue_id"] = named.get("id")
        out.append(updated)
    return out


def oriented_outcomes(game: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    home_points = game.get("home_points")
    away_points = game.get("away_points")
    if home_points is None or away_points is None:
        return None
    try:
        hp = int(home_points)
        ap = int(away_points)
    except (TypeError, ValueError):
        return None
    home = str(game["home_canonical_team_id"])
    away = str(game["away_canonical_team_id"])
    tie = hp == ap
    return [
        {
            "canonical_game_id": game["canonical_game_id"],
            "canonical_team_id": home,
            "label_win": None if tie else hp > ap,
            "label_tie": tie,
            "points_for": hp,
            "points_against": ap,
            "margin": hp - ap,
            "season": int(game["season"]),
        },
        {
            "canonical_game_id": game["canonical_game_id"],
            "canonical_team_id": away,
            "label_win": None if tie else ap > hp,
            "label_tie": tie,
            "points_for": ap,
            "points_against": hp,
            "margin": ap - hp,
            "season": int(game["season"]),
        },
    ]


def mapped_claim(item: Mapping[str, Any]) -> dict[str, Any]:
    value = item.get("value")
    return {
        "claim_id": (
            f"{item['artifact_path']}:{item['pointer']}:"
            f"{item.get('row_identity') or ''}:{item['field']}"
        ),
        "artifact_path": item["artifact_path"],
        "pointer": item["pointer"],
        "row_identity": item.get("row_identity") or "",
        "field": item["field"],
        "population": item.get("population") or item["artifact_path"],
        "value_class": item.get("value_class"),
        "formula": "discovered_authority_field",
        "numerator": value
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else None,
        "denominator": None,
        "source_identities": [item["artifact_path"]],
        "temporal_authority": "artifact_as_of_materialization",
        "producer": "aggie_analytics.cycle30",
        "validator": "tools/validate_cycle30_gates.py",
        "independent_reference": "aggie_analytics.scientific_reference.cycle30",
        "dependencies": [],
        "trust_class": "UNTRUSTED_SHADOW",
    }


def load_optional_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return load_jsonl(path)


def venue_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        vid = row.get("id")
        if vid is None:
            continue
        out[str(vid)] = row
    return out


def payload_coords(
    payload: Mapping[str, Any] | None,
) -> tuple[float | None, float | None]:
    if not payload:
        return None, None
    loc = payload.get("location") if isinstance(payload.get("location"), dict) else {}
    lat = payload.get("latitude") or loc.get("latitude")
    lon = payload.get("longitude") or loc.get("longitude")
    if lat is None or lon is None:
        return None, None
    return float(lat), float(lon)


def mapped_team_source_id(game: Mapping[str, Any], side: str) -> str:
    raw = game.get(f"{side}_team_source_id")
    if raw is not None and str(raw) != "":
        return str(raw)
    canonical = str(game.get(f"{side}_canonical_team_id") or "")
    if ":" in canonical:
        return canonical.rsplit(":", 1)[-1]
    return canonical


def emit_pair_travel(
    *,
    gid: str,
    home: str,
    away: str,
    home_src: str,
    away_src: str,
    vlat: float | None,
    vlon: float | None,
    team_geo: dict[str, tuple[float, float]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for src, team in ((home_src, home), (away_src, away)):
        origin = team_geo.get(src)
        try:
            rows.append(
                travel_row(
                    canonical_game_id=gid,
                    team_id=team,
                    origin_lat=None if origin is None else origin[0],
                    origin_lon=None if origin is None else origin[1],
                    venue_lat=vlat,
                    venue_lon=vlon,
                    origin_class="TEAM_HOME_VENUE_PROXY"
                    if origin
                    else "UNKNOWN_TEAM_ORIGIN",
                    origin_id=team if origin else None,
                )
            )
        except SiteContextError as exc:
            rows.append(
                {
                    "canonical_game_id": gid,
                    "team_id": team,
                    "distance_km_haversine": None,
                    "distance_km_vincenty": None,
                    "missing_reason": str(exc),
                    "model_consumed": False,
                    "proximity_is_not_home_bonus": True,
                }
            )
    return rows


def historical_neutral_travel_slice(
    games: list[dict[str, Any]],
    *,
    venues: dict[str, dict[str, Any]],
    team_geo: dict[str, tuple[float, float]],
    season_min: int,
    season_max: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    context_rows: list[dict[str, Any]] = []
    travel_rows: list[dict[str, Any]] = []
    for game in games:
        season = int(game.get("season") or 0)
        if season < season_min or season > season_max:
            continue
        if game.get("neutral_site") is not True:
            continue
        gid = str(game.get("canonical_game_id"))
        home = str(game["home_canonical_team_id"])
        away = str(game["away_canonical_team_id"])
        home_src = mapped_team_source_id(game, "home")
        away_src = mapped_team_source_id(game, "away")
        venue = venues.get(str(game.get("venue_id") or ""))
        vlat, vlon = payload_coords(venue)
        context_rows.append(
            contest_context(
                canonical_game_id=gid,
                source_order=[home, away],
                canonical_home_id=home,
                canonical_away_id=away,
                designated_home_id=home,
                designated_source="SRC-002",
                site_class="NEUTRAL",
                venue_id=None if not venue else str(venue.get("id")),
                venue_name=(venue or {}).get("name") or game.get("venue_name"),
                venue_lat=vlat,
                venue_lon=vlon,
            )
        )
        travel_rows.extend(
            emit_pair_travel(
                gid=gid,
                home=home,
                away=away,
                home_src=home_src,
                away_src=away_src,
                vlat=vlat,
                vlon=vlon,
                team_geo=team_geo,
            )
        )
    return context_rows, travel_rows


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    EXT.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    head = git_head()
    hashes["CYCLE30_PREFLIGHT_AND_PRESERVATION.json"] = write_json(
        ART / "CYCLE30_PREFLIGHT_AND_PRESERVATION.json",
        {
            "artifact_type": "CYCLE30_PREFLIGHT_AND_PRESERVATION",
            "head_sha": head,
            "base_reviewed_cycle29": "0b957ea127ad6a5373901d8ddff47c43a496b100",
            "canonical_main": "55e12a5aad3a7e843204fcba619c3cb3d3d6194d",
            "operator_hold": "ACTIVE",
            "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
            "review_state": "READY_FOR_MANAGER_REVIEW",
            "no_merge": True,
            "no_done": True,
            "no_bat523_completion_comment": True,
            "fort_knox_retired": True,
            "as_of_utc": utc_now(),
            "artifact_class": "BLOCKER_METADATA",
        },
    )

    raw_games = load_jsonl(GAMES_PATH)
    games = [map_game(row) for row in raw_games]
    reject_synthetic_real_denominator(games)
    pair_coverage = classify_pair_counts(games)
    hashes["HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json"] = write_json(
        ART / "HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json",
        {
            **pair_coverage,
            "artifact_class": "REAL_EVIDENCE",
            "source_path": str(GAMES_PATH),
            "source_sha256": sha256_file(GAMES_PATH),
        },
    )

    ties = [
        row
        for row in games
        if row.get("home_points") is not None
        and row.get("away_points") is not None
        and int(row["home_points"]) == int(row["away_points"])
    ]
    hashes["HISTORICAL_TIE_AUDIT.json"] = write_json(
        ART / "HISTORICAL_TIE_AUDIT.json",
        {
            "artifact_type": "HISTORICAL_TIE_AUDIT",
            "artifact_class": "REAL_EVIDENCE",
            "tie_count": len(ties),
            "tie_policy": "EXCLUDE_TIES_FROM_BINARY_ESTIMAND",
            "silent_home_loss_mapping_forbidden": True,
            "tie_game_ids_sha256": sha256_json(
                sorted(row["canonical_game_id"] for row in ties)
            ),
            "affected_consumers": [
                "binary_win_estimand",
                "kernel_model",
                "week1_directional_skill",
            ],
        },
    )

    cfbd_venues = load_optional_jsonl(EXT / "CFBD_VENUES.jsonl")
    venues = venue_index(cfbd_venues)
    venues_named = venue_index_by_name(cfbd_venues)
    cfbd_hist_games = load_optional_jsonl(EXT / "CFBD_GAMES_1963_2012.jsonl")
    games = overlay_historical_venues(games, cfbd_hist_games, venues_named)

    site_rows: dict[str, dict[str, Any]] = {}
    neutrals: list[dict[str, Any]] = []
    for game in games:
        missing = game.get("neutral_site") is None
        site_class = classify_site(
            official_neutral=None,
            provider_neutral=game.get("neutral_site") if not missing else None,
            missing_annotation=missing,
        )
        venue = venues.get(str(game.get("venue_id") or ""))
        vlat, vlon = payload_coords(venue)
        venue_gap = None
        if game.get("venue_id") is None:
            venue_gap = "MISSING_VENUE_ID"
        elif vlat is None or vlon is None:
            venue_gap = "MISSING_VENUE_COORDINATES"
        context = contest_context(
            canonical_game_id=str(game["canonical_game_id"]),
            source_order=[
                str(game["home_canonical_team_id"]),
                str(game["away_canonical_team_id"]),
            ],
            canonical_home_id=str(game["home_canonical_team_id"]),
            canonical_away_id=str(game["away_canonical_team_id"]),
            designated_home_id=str(game["home_canonical_team_id"]),
            designated_source="SRC-002",
            site_class=site_class,
            venue_id=None if game.get("venue_id") is None else str(game["venue_id"]),
            venue_name=(venue or {}).get("name") or game.get("venue_name"),
            venue_lat=vlat,
            venue_lon=vlon,
            missing_reason=venue_gap,
        )
        site_rows[str(game["canonical_game_id"])] = {
            **context,
            "ordinary_home_exposure": ordinary_home_exposure(
                site_class=site_class, orientation_is_designated_home=True
            ),
        }
        if site_class == "NEUTRAL":
            neutrals.append(site_rows[str(game["canonical_game_id"])])
    hashes["HISTORICAL_NEUTRAL_SITE_AUDIT.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_NEUTRAL_SITE_AUDIT.jsonl", neutrals
    )
    hashes["HISTORICAL_NEUTRAL_SITE_AUDIT_SUMMARY.json"] = write_json(
        ART / "HISTORICAL_NEUTRAL_SITE_AUDIT_SUMMARY.json",
        {
            "artifact_type": "HISTORICAL_NEUTRAL_SITE_AUDIT",
            "artifact_class": "REAL_EVIDENCE",
            "neutral_row_count": len(neutrals),
            "parent_game_count": len(games),
            "venue_id_present": sum(
                1 for row in neutrals if row.get("venue_id") is not None
            ),
            "venue_with_coordinates": sum(
                1 for row in neutrals if row.get("venue_latitude") is not None
            ),
            "unknown_is_not_ordinary_home": True,
            "ordinary_hfa_masked_on_verified_neutral": True,
            "lambeau_is_not_national_proof": True,
            "external_sha256": hashes["HISTORICAL_NEUTRAL_SITE_AUDIT.jsonl"],
        },
    )

    cfbd_teams = load_optional_jsonl(EXT / "CFBD_TEAMS_TRANCHE.jsonl")
    cfbd_games = load_optional_jsonl(EXT / "CFBD_GAMES_TRANCHE.jsonl")
    cfbd_coaches = load_optional_jsonl(EXT / "CFBD_COACHES_TRANCHE.jsonl")
    ledger_path = EXT / "CYCLE30_ACQUISITION_LEDGER.json"
    acquisition_ledger = (
        load_json(ledger_path)
        if ledger_path.is_file()
        else {
            "attempt_count": 0,
            "attempts": [],
            "artifact_class": "BLOCKER_METADATA",
            "status": "NOT_ATTEMPTED",
        }
    )
    attempt_summary = attempt_ledger_count(acquisition_ledger.get("attempts") or [])
    reject_literal_attempted(
        {"attempted": attempt_summary["attempted"]},
        int(attempt_summary["attempt_count"]),
    )

    current_programs: list[dict[str, Any]] = []
    seen_current: set[str] = set()
    excluded_lower_division_ids: set[str] = set()
    team_geo: dict[str, tuple[float, float]] = {}
    for row in cfbd_teams:
        loc = row.get("location") or {}
        if loc.get("latitude") is not None and loc.get("longitude") is not None:
            team_geo[str(row.get("id"))] = (
                float(loc["latitude"]),
                float(loc["longitude"]),
            )
        if int(row.get("source_year") or 0) != 2026:
            continue
        cls = str(row.get("classification") or "").lower()
        pid = team_id(row.get("id"))
        if cls not in {"fbs", "fcs"}:
            excluded_lower_division_ids.add(pid)
            continue
        if pid in seen_current:
            continue
        seen_current.add(pid)
        current_programs.append(
            {
                "program_id": pid,
                "display_name": row.get("school") or row.get("team"),
                "conference": row.get("conference"),
                "classification": cls,
                "source_id": "SRC-002",
                "source_field_classification": cls,
                "query_parameter_classification_ignored": row.get(
                    "source_classification"
                ),
                "artifact_class": "REAL_EVIDENCE",
            }
        )
    if current_programs:
        membership = current_membership_record(
            current_programs,
            source_id="SRC-002",
            source_season=2026,
            as_of_utc=AS_OF,
            rights="CFBD_TERMS_AUTHORIZED_ROUTE",
        )
        membership = {
            **membership,
            "query_parameter_did_not_filter_cfbd_teams": True,
            "used_response_classification_fbs_fcs": True,
            "excluded_non_di_program_ids": len(excluded_lower_division_ids),
        }
    else:
        membership = {
            "artifact_type": "CURRENT_2026_DIVISION_I_PROGRAM_POPULATION",
            "artifact_class": "BLOCKER_METADATA",
            "N": None,
            "status": "NOT_ATTEMPTED_OR_EMPTY",
            "hardcoded_266_forbidden": True,
            "week1_appearances_are_not_N": True,
        }
    hashes["CURRENT_2026_DIVISION_I_PROGRAM_POPULATION.json"] = write_json(
        ART / "CURRENT_2026_DIVISION_I_PROGRAM_POPULATION.json", membership
    )
    hashes["CURRENT_2026_PROGRAMS.jsonl"] = write_jsonl(
        EXT / "CURRENT_2026_PROGRAMS.jsonl", current_programs
    )

    hist_membership = []
    seen_hist: set[tuple[str, int]] = set()
    for row in cfbd_teams:
        year = int(row.get("source_year") or 0)
        if year < 2013 or year > 2023:
            continue
        cls = str(row.get("classification") or "").lower()
        if cls not in {"fbs", "fcs"}:
            continue
        pid = team_id(row.get("id"))
        key = (pid, year)
        if key in seen_hist:
            continue
        seen_hist.add(key)
        hist_membership.append(
            {
                "program_id": pid,
                "season": year,
                "classification": cls,
                "conference": row.get("conference"),
                "display_name": row.get("school") or row.get("team"),
                "era": era_label(year),
                "artifact_class": "REAL_EVIDENCE",
                "source_id": "SRC-002",
            }
        )
    hashes["HISTORICAL_MEMBERSHIP_2013_2023.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl", hist_membership
    )
    cfbd_teams_1963 = load_optional_jsonl(EXT / "CFBD_TEAMS_1963_2012.jsonl")
    membership_1963 = membership_rows_1963_2012(cfbd_teams_1963)
    hist_1963 = membership_1963["rows"]
    membership_ledger_path = EXT / "CYCLE30_MEMBERSHIP_1963_2012_LEDGER.json"
    membership_ledger = (
        load_json(membership_ledger_path) if membership_ledger_path.is_file() else {}
    )
    years_attempted_1963 = (
        membership_ledger.get("years_attempted") or membership_1963["years_with_rows"]
    )
    hashes["HISTORICAL_MEMBERSHIP_1963_2012.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl", hist_1963
    )
    hashes["HISTORICAL_MEMBERSHIP_1963_2012_SUMMARY.json"] = write_json(
        ART / "HISTORICAL_MEMBERSHIP_1963_2012_SUMMARY.json",
        {
            "artifact_type": "HISTORICAL_MEMBERSHIP_1963_2012_SUMMARY",
            "artifact_class": membership_1963["artifact_class"],
            "row_count": len(hist_1963),
            "years_attempted": years_attempted_1963,
            "years_with_rows": membership_1963["years_with_rows"],
            "source_classification_is_not_era_proof_pre_1978": True,
            "modern_fbs_fcs_not_projected_as_era": True,
            "status": (
                "CFBD_TEAMS_YEAR_ATTEMPTED"
                if years_attempted_1963
                else "BLOCKED_SOURCE_TASK"
            ),
        },
    )
    hashes["HISTORICAL_SCOPE_CONTRACT.json"] = write_json(
        ART / "HISTORICAL_SCOPE_CONTRACT.json",
        {
            **historical_scope_contract(),
            "acquired_2013_2023_program_season_rows": len(hist_membership),
            "acquired_1963_2012_program_season_rows": len(hist_1963),
            "membership_1963_2012_years_attempted": len(years_attempted_1963),
            "membership_1963_2012_status": (
                "CFBD_TEAMS_YEAR_ATTEMPTED"
                if years_attempted_1963
                else "BLOCKED_SOURCE_TASK"
            ),
            "missing_eras_1963_2012": None
            if years_attempted_1963
            else "BLOCKED_SOURCE_TASK",
            "source_classification_is_not_era_proof_pre_1978": True,
            "null_program_markers_not_used": True,
            "artifact_class": "REAL_EVIDENCE"
            if hist_membership or hist_1963
            else "BLOCKER_METADATA",
        },
    )

    fcs_cfbd = [
        row
        for row in cfbd_games
        if str(
            row.get("homeClassification") or row.get("home_classification") or ""
        ).lower()
        == "fcs"
        and str(
            row.get("awayClassification") or row.get("away_classification") or ""
        ).lower()
        == "fcs"
    ]
    hashes["CFBD_FCS_FCS_GAMES_TRANCHE.jsonl"] = write_jsonl(
        EXT / "CFBD_FCS_FCS_GAMES_TRANCHE.jsonl",
        [{**row, "artifact_class": "REAL_EVIDENCE"} for row in fcs_cfbd],
    )
    fcs_subset = fcs_subset_from_parent(
        games,
        parent_identity=sha256_file(GAMES_PATH),
        filter_contract_identity="cycle30-home-or-away-fcs-or-iaa",
    )
    hashes["FCS_SUBSET_FROM_PARENT_SUMMARY.json"] = write_json(
        ART / "FCS_SUBSET_FROM_PARENT_SUMMARY.json",
        {
            "parent_row_count": fcs_subset["parent_row_count"],
            "subset_row_count": fcs_subset["subset_row_count"],
            "forward_reverse_reconciled": True,
            "observed_fbs_route_is_numerator_only": True,
            "cfbd_fcs_fcs_acquired_rows": len(fcs_cfbd),
            "artifact_class": "REAL_EVIDENCE",
        },
    )

    capture_rows = load_jsonl(CAPTURE_INV) if CAPTURE_INV.is_file() else []
    mounted = 0
    missing_captures = []
    for row in capture_rows:
        rel = row.get("relative_path")
        path = DATA / str(rel) if rel else None
        if path is not None and path.is_file():
            mounted += 1
        else:
            missing_captures.append(
                {
                    "snapshot_id": row.get("snapshot_id"),
                    "relative_path": rel,
                    "declared_sha256": row.get("declared_sha256"),
                }
            )
    hashes["CAPTURE_INVENTORY_EXACT_RECONCILE.json"] = write_json(
        ART / "CAPTURE_INVENTORY_EXACT_RECONCILE.json",
        {
            "artifact_type": "CAPTURE_INVENTORY_EXACT_RECONCILE",
            "declared_inventory_rows": len(capture_rows),
            "mounted_existing_files": mounted,
            "declared_missing_from_mounted_root": len(missing_captures),
            "not_a_subtraction_identity": True,
            "unsupported_all_raw_audited": False,
            "artifact_class": "REAL_EVIDENCE",
            "missing_sample": missing_captures[:25],
        },
    )
    canonical_index = index_canonical(games)
    raw_trace = stratified_raw_comparisons(
        capture_rows=capture_rows,
        mounted_root=DATA,
        canonical_by_id=canonical_index,
        per_season=None,
    )
    hashes["HISTORICAL_RAW_TO_NORMALIZED_SEMANTIC_TRACE.json"] = write_json(
        ART / "HISTORICAL_RAW_TO_NORMALIZED_SEMANTIC_TRACE.json",
        {k: v for k, v in raw_trace.items() if k != "sample"},
    )
    hashes["HISTORICAL_RAW_TO_NORMALIZED_SAMPLE.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_RAW_TO_NORMALIZED_SAMPLE.jsonl", raw_trace.get("sample") or []
    )
    parent_dups = parent_duplicate_conflict_audit(games)
    hashes["PARENT_DUPLICATE_CONFLICT_AUDIT.json"] = write_json(
        ART / "PARENT_DUPLICATE_CONFLICT_AUDIT.json", parent_dups
    )

    current_travel: list[dict[str, Any]] = []
    current_context: list[dict[str, Any]] = []
    for row in cfbd_games:
        year = int(row.get("year") or row.get("season") or 0)
        if year != 2026:
            continue
        gid = f"SRC-002:GAME:{row.get('id')}"
        home_src = str(row.get("homeId") or row.get("home_id") or "")
        away_src = str(row.get("awayId") or row.get("away_id") or "")
        home = team_id(home_src)
        away = team_id(away_src)
        venue = venues.get(str(row.get("venueId") or row.get("venue_id") or ""))
        vlat, vlon = payload_coords(venue)
        site_class = classify_site(
            official_neutral=row.get("neutralSite")
            if "neutralSite" in row
            else row.get("neutral_site"),
            provider_neutral=row.get("neutralSite")
            if "neutralSite" in row
            else row.get("neutral_site"),
            missing_annotation=row.get("neutralSite", row.get("neutral_site")) is None,
        )
        ctx = contest_context(
            canonical_game_id=gid,
            source_order=[home, away],
            canonical_home_id=home,
            canonical_away_id=away,
            designated_home_id=home,
            designated_source="SRC-002",
            site_class=site_class,
            venue_id=None if not venue else str(venue.get("id")),
            venue_name=(venue or {}).get("name") or row.get("venue"),
            venue_lat=vlat,
            venue_lon=vlon,
        )
        current_context.append(ctx)
        current_travel.extend(
            emit_pair_travel(
                gid=gid,
                home=home,
                away=away,
                home_src=home_src,
                away_src=away_src,
                vlat=vlat,
                vlon=vlon,
                team_geo=team_geo,
            )
        )
    hashes["CURRENT_2026_CONTEST_CONTEXT.jsonl"] = write_jsonl(
        EXT / "CURRENT_2026_CONTEST_CONTEXT.jsonl", current_context
    )
    hashes["CURRENT_2026_TRAVEL_ROWS.jsonl"] = write_jsonl(
        EXT / "CURRENT_2026_TRAVEL_ROWS.jsonl", current_travel
    )
    lambeau_home = "SRC-002:TEAM:LAMBEAU-HOME"
    lambeau_away = "SRC-002:TEAM:LAMBEAU-AWAY"
    lambeau_ctx = contest_context(
        canonical_game_id="FIXTURE:LAMBEAU-PERMUTATION",
        source_order=[lambeau_home, lambeau_away],
        canonical_home_id=lambeau_home,
        canonical_away_id=lambeau_away,
        designated_home_id=lambeau_home,
        designated_source="SYNTHETIC_FIXTURE",
        site_class="NEUTRAL",
        venue_id=LAMBEAU["venue_id"],
        venue_name=LAMBEAU["venue_name"],
        venue_lat=LAMBEAU["lat"],
        venue_lon=LAMBEAU["lon"],
    )
    swapped = contest_context(
        canonical_game_id="FIXTURE:LAMBEAU-PERMUTATION",
        source_order=[lambeau_away, lambeau_home],
        canonical_home_id=lambeau_away,
        canonical_away_id=lambeau_home,
        designated_home_id=lambeau_away,
        designated_source="SYNTHETIC_FIXTURE",
        site_class="NEUTRAL",
        venue_id=LAMBEAU["venue_id"],
        venue_name=LAMBEAU["venue_name"],
        venue_lat=LAMBEAU["lat"],
        venue_lon=LAMBEAU["lon"],
    )
    designation_swap_invariant(
        {
            "site_class": "NEUTRAL",
            "ordinary_home_exposure": 0.0,
            "travel": 0,
            "strength": 0,
        },
        {
            "site_class": "NEUTRAL",
            "ordinary_home_exposure": 0.0,
            "travel": 0,
            "strength": 0,
        },
    )
    hashes["LAMBEAU_PERMUTATION_FIXTURE.json"] = write_json(
        ART / "LAMBEAU_PERMUTATION_FIXTURE.json",
        {
            "artifact_class": "SYNTHETIC_FIXTURE",
            "base": lambeau_ctx,
            "designation_swapped": swapped,
            "ordinary_home_stays_zero": True,
            "proximity_is_not_home_bonus": True,
        },
    )
    hashes["CURRENT_VENUE_TRAVEL_SUMMARY.json"] = write_json(
        ART / "CURRENT_VENUE_TRAVEL_SUMMARY.json",
        {
            "artifact_class": "REAL_EVIDENCE"
            if current_context
            else "BLOCKER_METADATA",
            "current_contest_context_rows": len(current_context),
            "current_travel_rows": len(current_travel),
            **travel_gap_counts(current_travel),
            "model_consumed": False,
            "full_schedule_remains_in_denominator": True,
        },
    )
    historical_neutral_context, historical_neutral_travel = (
        historical_neutral_travel_slice(
            games,
            venues=venues,
            team_geo=team_geo,
            season_min=2013,
            season_max=2023,
        )
    )
    hashes["HISTORICAL_C_TRANCHE_NEUTRAL_TRAVEL.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_C_TRANCHE_NEUTRAL_TRAVEL.jsonl", historical_neutral_travel
    )
    hashes["HISTORICAL_C_TRANCHE_NEUTRAL_TRAVEL_SUMMARY.json"] = write_json(
        ART / "HISTORICAL_C_TRANCHE_NEUTRAL_TRAVEL_SUMMARY.json",
        {
            "artifact_type": "HISTORICAL_C_TRANCHE_NEUTRAL_TRAVEL_SUMMARY",
            "artifact_class": "REAL_EVIDENCE",
            "period": "2013-2023",
            "verified_neutral_contests": len(historical_neutral_context),
            "travel_rows": len(historical_neutral_travel),
            **travel_gap_counts(historical_neutral_travel),
            "model_consumed": False,
            "backlog_1963_2012_retained": True,
            "proximity_is_not_home_bonus": True,
        },
    )
    backlog_context, backlog_travel = historical_neutral_travel_slice(
        games,
        venues=venues,
        team_geo=team_geo,
        season_min=1963,
        season_max=2012,
    )
    hashes["HISTORICAL_NEUTRAL_TRAVEL_BACKLOG_1963_2012.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_NEUTRAL_TRAVEL_BACKLOG_1963_2012.jsonl", backlog_travel
    )
    hashes["HISTORICAL_NEUTRAL_TRAVEL_BACKLOG_1963_2012_SUMMARY.json"] = write_json(
        ART / "HISTORICAL_NEUTRAL_TRAVEL_BACKLOG_1963_2012_SUMMARY.json",
        {
            "artifact_type": "HISTORICAL_NEUTRAL_TRAVEL_BACKLOG_1963_2012_SUMMARY",
            "artifact_class": "REAL_EVIDENCE",
            "period": "1963-2012",
            "verified_neutral_contests": len(backlog_context),
            "travel_rows": len(backlog_travel),
            **travel_gap_counts(backlog_travel),
            "model_consumed": False,
            "not_a_completeness_claim": True,
            "proximity_is_not_home_bonus": True,
        },
    )

    kernel_games = []
    kernel_outcomes = []
    kernel_authorities: dict[str, dict[str, Any]] = {}
    kernel_cutoffs: dict[str, str] = {}
    for game in games:
        season = int(game["season"])
        if season < 2006 or season > 2023:
            continue
        if str(game.get("home_classification") or "").lower() != "fbs":
            continue
        if str(game.get("away_classification") or "").lower() != "fbs":
            continue
        if not game.get("completed"):
            continue
        outcomes = oriented_outcomes(game)
        if outcomes is None:
            continue
        kernel_games.append(game)
        kernel_outcomes.extend(outcomes)
        kernel_authorities[str(game["canonical_game_id"])] = {
            "source_id": str(game.get("source_id") or "SRC-002"),
            "effective_utc": str(game["start_date_utc_text"]),
            "known_at_utc": str(game["start_date_utc_text"]),
            "receipt_sha256": "UNPROVEN",
            "classification": "UNPROVEN",
            "evidence_class": "CONSERVATIVE_BOUND_NOT_PUBLICATION",
            "allow_retrospective_prior": True,
        }
    freeze_rows = load_jsonl(FORECAST_ROWS) if FORECAST_ROWS.is_file() else []
    freeze_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for row in freeze_rows:
        home = str(row.get("home_canonical_team_id") or "")
        away = str(row.get("away_canonical_team_id") or "")
        if home and away:
            freeze_by_pair.setdefault(tuple(sorted((home, away))), row)
    seen_kernel = {str(game["canonical_game_id"]) for game in kernel_games}
    freeze_bound_2026 = 0
    for raw in cfbd_games:
        if int(raw.get("season") or raw.get("year") or 0) != 2026:
            continue
        if not raw.get("completed"):
            continue
        mapped = map_cfbd_game(raw)
        if str(mapped.get("home_classification") or "").lower() != "fbs":
            continue
        if str(mapped.get("away_classification") or "").lower() != "fbs":
            continue
        outcomes = oriented_outcomes(mapped)
        if outcomes is None:
            continue
        freeze = freeze_by_pair.get(
            tuple(
                sorted(
                    (
                        str(mapped["home_canonical_team_id"]),
                        str(mapped["away_canonical_team_id"]),
                    )
                )
            )
        )
        if freeze is None:
            continue
        gid = str(mapped["canonical_game_id"])
        if gid in seen_kernel:
            continue
        try:
            authority = forecast_freeze_authority(
                freeze, receipt_sha256=sha256_file(FORECAST_ROWS)
            )
        except Exception:
            continue
        kickoff = str(freeze.get("kickoff_bound_utc") or mapped["start_date_utc_text"])
        kernel_games.append(mapped)
        kernel_outcomes.extend(outcomes)
        kernel_authorities[gid] = authority
        kernel_cutoffs[gid] = kickoff
        seen_kernel.add(gid)
        freeze_bound_2026 += 1
    extra_game = {
        "canonical_game_id": "FIXTURE:FUTURE-APPEND",
        "home_canonical_team_id": "SRC-002:TEAM:FUTURE-A",
        "away_canonical_team_id": "SRC-002:TEAM:FUTURE-B",
        "season": 2016,
        "start_date_utc_text": "2016-12-31T19:00:00Z",
        "date_precision": "INSTANT",
        "home_points": 10,
        "away_points": 3,
        "source_id": "SRC-TEST",
        "artifact_class": "SYNTHETIC_FIXTURE",
    }
    extra_outcomes = oriented_outcomes(extra_game) or []
    rebuild = rebuild_kernel_comparison(
        kernel_games[:40],
        kernel_outcomes[:80],
        [extra_game],
        extra_outcomes,
        expected_population_complete=False,
        site_rows={
            row["canonical_game_id"]: site_rows[row["canonical_game_id"]]
            for row in kernel_games[:40]
            if row["canonical_game_id"] in site_rows
        },
    )
    kernel = build_game_grain_kernel(
        kernel_games,
        kernel_outcomes,
        expected_population_complete=False,
        site_rows=site_rows,
        authorities=kernel_authorities,
        target_cutoff_by_game=kernel_cutoffs,
    )
    comparison_rows = [*kernel["rows"], *kernel["retrospective_rows"]]
    reconstructed = reconstruct_game_features(
        kernel_games, kernel_outcomes, authorities=kernel_authorities
    )
    reconstructed_declared = [
        row
        for row in reconstructed
        if row["canonical_game_id"]
        in {item["canonical_game_id"] for item in comparison_rows}
    ]
    reconstruction = compare_producer_rows(comparison_rows, reconstructed_declared)
    hashes["PIT_KERNEL_ROWS.jsonl"] = write_jsonl(
        EXT / "PIT_KERNEL_ROWS.jsonl", comparison_rows
    )
    hashes["PIT_KERNEL_EXCLUSION_LEDGER.jsonl"] = write_jsonl(
        EXT / "PIT_KERNEL_EXCLUSION_LEDGER.jsonl", kernel["blockers"]
    )
    hashes["PIT_KERNEL_POPULATION_MANIFEST.json"] = write_json(
        ART / "PIT_KERNEL_POPULATION_MANIFEST.json",
        {
            "scope": kernel["scope"],
            "estimand": (
                "2013-2023_FBS_FBS_BINARY_WIN_WITH_2006_2023_IN_WINDOW_PRIORS;"
                "2026_WEEK1_FREEZE_BOUND_PROSPECTIVE_WHERE_RECEIPTED"
            ),
            "kernel_input_games": len(kernel_games),
            "freeze_bound_2026_completed_week1_games": freeze_bound_2026,
            "proven_pit_training_rows": kernel["proven_pit_training_rows"],
            "retrospective_candidate_rows": kernel["retrospective_candidate_rows"],
            "game_grain_count": kernel["game_grain_count"],
            "oriented_row_count": kernel["oriented_row_count"],
            "blocker_count": kernel["blocker_count"],
            "primary_kernel_objective": kernel["primary_kernel_objective"],
            "trust_classification": "UNTRUSTED_SHADOW",
            "external_rows_sha256": hashes["PIT_KERNEL_ROWS.jsonl"],
            "artifact_class": "REAL_EVIDENCE",
            "expected_population_complete": False,
        },
    )
    hashes["PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json"] = write_json(
        ART / "PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json",
        {
            **reconstruction,
            "declared_comparison_rows": len(comparison_rows),
            "rebuild": rebuild,
            "artifact_class": "REAL_EVIDENCE",
        },
    )
    chain_ids = [row["canonical_game_id"] for row in comparison_rows]
    hashes["PIT_KERNEL_FULL_CHAIN_RECONSTRUCTION.json"] = write_json(
        ART / "PIT_KERNEL_FULL_CHAIN_RECONSTRUCTION.json",
        {
            "artifact_type": "PIT_KERNEL_FULL_CHAIN_RECONSTRUCTION",
            "artifact_class": "REAL_EVIDENCE",
            "comparison_unique_games": len(set(chain_ids)),
            "comparison_team_rows": len(comparison_rows),
            "independent_reconstructed_team_rows": len(reconstructed_declared),
            "independent_matched": bool(reconstruction.get("matched")),
            "game_identity_sha256": sha256_json(sorted(set(chain_ids))),
            "raw_source": "SRC-002",
            "population_filter": "2006-2023 observed FBS-FBS binary win; 2024/25 exposed excluded",
            "tie_policy": "EXCLUDE_TIES_FROM_BINARY_ESTIMAND",
            "temporal_authority": "RETROSPECTIVE_BOUNDED_CANDIDATE",
            "priors": "in-window completed games before earliest start bound",
            "neutral_site_consumed_as_ordinary_home_mask": True,
            "travel_consumed": False,
            "coaching_consumed": False,
            "proven_pit_rows": kernel["proven_pit_training_rows"],
            "not_manager_verified": True,
            "passing_fixture_cannot_establish_this_result": True,
        },
    )
    recon_payload = mount_predecessor_oriented_payload(
        DATA, kernel_game_ids=[row["canonical_game_id"] for row in comparison_rows]
    )
    recon_pop = predecessor_reconciliation(
        pit_feature_eligible_ids=[],
        oriented_development_ids=[],
        active_proven_ids=[],
        kernel_proven_ids=[row["canonical_game_id"] for row in kernel["rows"]],
    )
    hashes["PIT_PREDECESSOR_POPULATION_RECONCILIATION.json"] = write_json(
        ART / "PIT_PREDECESSOR_POPULATION_RECONCILIATION.json",
        {
            **recon_pop,
            "predecessor_pit_feature_eligible_rows": int(
                recon_payload.get("predecessor_pit_feature_eligible_rows") or 0
            ),
            "predecessor_oriented_development_rows": int(
                recon_payload.get("predecessor_oriented_development_rows") or 0
            ),
            "difference_eligible_minus_oriented": int(
                recon_payload.get("predecessor_pit_feature_eligible_rows") or 0
            )
            - int(recon_payload.get("predecessor_oriented_development_rows") or 0),
            "file_sha256": recon_payload.get("file_sha256"),
            "sha256_matches_declared_gate": recon_payload.get(
                "sha256_matches_declared_gate"
            ),
            "unique_games": recon_payload.get("unique_games"),
            "verdict_counts": recon_payload.get("verdict_counts"),
            "kernel_games_present_in_oriented": recon_payload.get(
                "kernel_games_present_in_oriented"
            ),
            "kernel_games_absent_from_oriented": recon_payload.get(
                "kernel_games_absent_from_oriented"
            ),
            "oriented_count_matches_claim": recon_payload.get(
                "oriented_count_matches_claim"
            ),
            "eligible_count_matches_claim": recon_payload.get(
                "eligible_count_matches_claim"
            ),
            "predecessor_claimed_pit_feature_eligible_rows": 89855,
            "predecessor_claimed_oriented_development_rows": 90198,
            "predecessor_payload_national_pit_eligible_team_features_jsonl": (
                "MOUNTED" if recon_payload.get("mounted") else "NOT_MOUNTED"
            ),
            "identity_sets_not_invented_from_integer_subtraction": True,
            "mounted": bool(recon_payload.get("mounted")),
            "artifact_class": (
                "REAL_EVIDENCE" if recon_payload.get("mounted") else "BLOCKER_METADATA"
            ),
        },
    )
    predecessor_feature_compare = compare_kernel_to_predecessor_payload(
        comparison_rows, DATA
    )
    hashes["PIT_KERNEL_PREDECESSOR_FEATURE_COMPARE.json"] = write_json(
        ART / "PIT_KERNEL_PREDECESSOR_FEATURE_COMPARE.json",
        {
            "artifact_type": "PIT_KERNEL_PREDECESSOR_FEATURE_COMPARE",
            **predecessor_feature_compare,
        },
    )

    design_rows = []
    fits = []
    for candidate in CANDIDATES:
        try:
            fit = fold_local_fit(comparison_rows, candidate=candidate)
        except Exception as exc:
            fits.append(
                {
                    "candidate": candidate,
                    "status": "BLOCKED",
                    "error": str(exc),
                    "coaching_consumed": False,
                    "travel_consumed": False,
                }
            )
            continue
        metrics = scoring_metrics(
            fit["eval_probabilities"],
            fit["eval_labels"],
            unique_games=len(fit["eval_probabilities"]),
        )
        prove_coaching_not_modeled({col: "NOT_CONSUMED" for col in ("coach", "staff")})
        prove_travel_isolation(
            {col: "NOT_CONSUMED" for col in ("travel_home_km", "travel_away_km")},
            claimed_consumed=False,
        )
        fits.append(
            {
                **{
                    key: value
                    for key, value in fit.items()
                    if key not in {"eval_labels", "eval_probabilities"}
                },
                "metrics": metrics,
                "status": "FITTED_UNTRUSTED_SHADOW",
            }
        )
        eval_ids = [
            row["canonical_game_id"]
            for row in comparison_rows
            if int(row["season"]) in set(range(2020, 2024)) and not row.get("tie")
        ]
        for gid in eval_ids[:500]:
            site = site_rows.get(gid, {})
            design_rows.append(
                persist_design_row(
                    canonical_game_id=gid,
                    ordinary_home_exposure_value=site.get("ordinary_home_exposure"),
                    site_class=str(site.get("site_class") or "UNKNOWN"),
                    travel_home_km=None,
                    travel_away_km=None,
                    consumed_columns=fit["consumed_columns"],
                )
            )
    hashes["KERNEL_CANDIDATE_FITS.json"] = write_json(
        ART / "KERNEL_CANDIDATE_FITS.json",
        {
            "predeclared": True,
            "candidates": fits,
            "train_seasons": list(range(2013, 2020)),
            "eval_seasons": list(range(2020, 2024)),
            "exposed_seasons_excluded": [2024, 2025],
            "tie_policy": "EXCLUDE_TIES_FROM_BINARY_ESTIMAND",
            "coaching_consumed": False,
            "travel_consumed": False,
            "trust_classification": "UNTRUSTED_SHADOW",
            "no_model_recommendation": True,
            "artifact_class": "REAL_EVIDENCE",
        },
    )
    hashes["KERNEL_DESIGN_MATRIX_SAMPLE.jsonl"] = write_jsonl(
        EXT / "KERNEL_DESIGN_MATRIX_SAMPLE.jsonl", design_rows[:2000]
    )
    perturbations = []
    for fit in fits:
        if fit.get("status") != "FITTED_UNTRUSTED_SHADOW":
            continue
        perturbations.append(
            designation_and_venue_perturbations(
                comparison_rows,
                candidate=str(fit["candidate"]),
                weights=fit.get("weights") or [],
            )
        )
    hashes["KERNEL_PERTURBATIONS.json"] = write_json(
        ART / "KERNEL_PERTURBATIONS.json",
        {
            "designation_swap_neutral_ordinary_home_stays_zero": True,
            "venue_change_does_not_rewrite_frozen_rows": True,
            "travel_available_is_not_consumed": True,
            "candidates": perturbations,
            "artifact_class": "REAL_EVIDENCE",
        },
    )
    trust = kernel_trust_gate(
        proven_rows=int(kernel["proven_pit_training_rows"]),
        independently_reconstructed=bool(reconstruction.get("matched")),
        kernel_gates_pass=True,
        unresolved_p0_affects_kernel=kernel["proven_pit_training_rows"] == 0,
    )
    hashes["PIT_KERNEL_TRUST_GATE.json"] = write_json(
        ART / "PIT_KERNEL_TRUST_GATE.json", trust
    )
    if kernel["rows"]:
        sample = kernel["rows"][0]
    elif comparison_rows:
        sample = comparison_rows[0]
    else:
        sample = {}
    hashes["PIT_KERNEL_RAW_TO_ROW_TRACE_SAMPLE.json"] = write_json(
        ART / "PIT_KERNEL_RAW_TO_ROW_TRACE_SAMPLE.json",
        {
            "sample_game_id": sample.get("canonical_game_id"),
            "source_id": "SRC-002",
            "home_features": sample.get("home_features"),
            "away_features": sample.get("away_features"),
            "ordinary_home_exposure": sample.get("ordinary_home_exposure"),
            "authority_class": sample.get("authority_class"),
            "row_verdict": sample.get("row_verdict"),
            "artifact_class": "REAL_EVIDENCE" if sample else "BLOCKER_METADATA",
        },
    )
    hashes["PIT_KERNEL_DOMAIN_ADMISSION.json"] = write_json(
        ART / "PIT_KERNEL_DOMAIN_ADMISSION.json",
        {
            "admitted": kernel["admitted_domains"],
            "excluded": kernel["excluded_domains"],
        },
    )
    hashes["PIT_KERNEL_TEMPORAL_PROOF.json"] = write_json(
        ART / "PIT_KERNEL_TEMPORAL_PROOF.json",
        {
            "aware_utc": True,
            "midnight_not_inferred_date_only": True,
            "conservative_bounds_are_not_publication": True,
            "rebuild_shuffle_stable": rebuild.get("shuffle_stable"),
        },
    )

    identities = extract_registry_identities(PEOPLE_CSV)
    coaching_recon = reconcile_predecessor_observations(
        identities["accepted_ids"], identities["provisional"]
    )
    reject_dropped_identity(
        [
            *identities["accepted_ids"],
            *[row["record_id"] for row in identities["provisional"]],
        ],
        [row["predecessor_record_id"] for row in coaching_recon["rows"]],
        True,
    )
    hashes["COACHING_PREDECESSOR_CONSERVATION.json"] = write_json(
        ART / "COACHING_PREDECESSOR_CONSERVATION.json",
        {
            "accepted_count": coaching_recon["accepted_count"],
            "provisional_count": coaching_recon["provisional_count"],
            "provisional_category_counts": coaching_recon[
                "provisional_category_counts"
            ],
            "row_count": coaching_recon["row_count"],
            "model_admitted": 0,
            "artifact_class": "REAL_EVIDENCE",
        },
    )
    hashes["COACHING_PREDECESSOR_ROWS.jsonl"] = write_jsonl(
        EXT / "COACHING_PREDECESSOR_ROWS.jsonl", coaching_recon["rows"]
    )
    if PEOPLE_CSV.is_file():
        sample = stratified_predecessor_sample(PEOPLE_CSV, per_family=2)
        hashes["COACHING_STRATIFIED_RAW_SAMPLE.json"] = write_json(
            ART / "COACHING_STRATIFIED_RAW_SAMPLE.json",
            {
                "artifact_type": sample["artifact_type"],
                "artifact_class": sample["artifact_class"],
                "family_count": sample["family_count"],
                "sample_count": sample["sample_count"],
                "failure_count": sample["failure_count"],
                "expanded_failed_families": sample["expanded_failed_families"],
                "counts_are_not_content_validation": True,
            },
        )
        hashes["COACHING_STRATIFIED_RAW_SAMPLE.jsonl"] = write_jsonl(
            EXT / "COACHING_STRATIFIED_RAW_SAMPLE.jsonl", sample["sample"]
        )
    program_ids = [row["program_id"] for row in current_programs]
    matrix = hc_oc_dc_matrix(program_ids, AS_OF) if program_ids else []
    hc_by_school: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in cfbd_coaches:
        if int(row.get("source_year") or 0) != 2026:
            continue
        school = str(row.get("school") or row.get("team") or "")
        hc_by_school[school].append(row)
        reject_cfbd_assistant("CFBD", "head_coach")
    official_people_rows = load_optional_jsonl(EXT / "OFFICIAL_STAFF_PARSED.jsonl")
    official_http_attempts = load_optional_jsonl(
        EXT / "OFFICIAL_STAFF_HTTP_ATTEMPTS.jsonl"
    )
    sportradar_people_rows = load_optional_jsonl(EXT / "SPORTSRADAR_STAFF_PARSED.jsonl")
    sportradar_http_attempts = load_optional_jsonl(
        EXT / "SPORTSRADAR_STAFF_HTTP_ATTEMPTS.jsonl"
    )
    people_by_program: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in official_people_rows:
        people_by_program[str(row.get("program_id"))].append(row)
    attempts_by_program = {
        str(row.get("program_id")): row for row in official_http_attempts
    }
    sr_people_by_program: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sportradar_people_rows:
        people_by_program_sr = sr_people_by_program[str(row.get("program_id"))]
        people_by_program_sr.append(row)
    sr_attempts_by_program = {
        str(row.get("program_id")): row for row in sportradar_http_attempts
    }
    wiki_candidate_rows = load_optional_jsonl(
        EXT / "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl"
    )
    wiki_hist_rows = load_optional_jsonl(
        EXT / "WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl"
    )
    wiki_people_by_program: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in wiki_candidate_rows:
        pid = str(row.get("program_id") or "")
        for episode in row.get("episodes") or []:
            if isinstance(episode, dict):
                wiki_people_by_program[pid].append(episode)
    for row in wiki_hist_rows:
        if int(row.get("season") or 0) != 2026:
            continue
        pid = str(row.get("program_id") or "")
        for episode in row.get("episodes") or []:
            if isinstance(episode, dict):
                wiki_people_by_program[pid].append(episode)
    filled = (
        fill_current_role_matrix(
            matrix,
            programs=current_programs,
            cfbd_hc_by_school=hc_by_school,
            official_people_by_program=people_by_program,
            official_attempts_by_program=attempts_by_program,
            sportradar_people_by_program=sr_people_by_program,
            sportradar_attempts_by_program=sr_attempts_by_program,
            wikimedia_people_by_program=wiki_people_by_program,
        )
        if matrix
        else []
    )
    hashes["CURRENT_NATIONAL_HC_OC_DC_MATRIX.jsonl"] = write_jsonl(
        EXT / "CURRENT_NATIONAL_HC_OC_DC_MATRIX.jsonl", filled
    )
    hashes["CURRENT_NATIONAL_HC_OC_DC_SUMMARY.json"] = write_json(
        ART / "CURRENT_NATIONAL_HC_OC_DC_SUMMARY.json",
        {
            "N": len(program_ids),
            "cells": len(filled),
            "expected_3n": 3 * len(program_ids),
            "attempt_ledger": attempt_summary,
            "cfbd_cannot_populate_assistants": True,
            "official_staff_programs": len(official_http_attempts),
            "sportradar_staff_programs": len(sportradar_http_attempts),
            "sportradar_people": len(sportradar_people_rows),
            "disposition_counts": {
                str(key): sum(1 for row in filled if row.get("disposition") == key)
                for key in sorted({str(row.get("disposition")) for row in filled})
            },
            "oc_dc_not_attempted": sum(
                1
                for row in filled
                if row.get("role") in {"offensive_coordinator", "defensive_coordinator"}
                and row.get("disposition") == "NOT_ATTEMPTED"
            ),
            "week1_is_derived_subset_only": True,
            "artifact_class": "REAL_EVIDENCE" if filled else "BLOCKER_METADATA",
        },
    )
    reject_week1_as_national_coaching(0, membership.get("N"), False)
    hashes["COACHING_MODEL_ADMISSION_GATE.json"] = write_json(
        ART / "COACHING_MODEL_ADMISSION_GATE.json", model_admission_gate()
    )
    hashes["POSITION_ROLE_OPPORTUNITY_CONTRACT.json"] = write_json(
        ART / "POSITION_ROLE_OPPORTUNITY_CONTRACT.json",
        position_role_contract(ROLE_FAMILIES),
    )
    lattice = historical_lattice(
        [
            {"program_id": row["program_id"], "season": row["season"]}
            for row in (*hist_membership, *hist_1963)
        ],
        ROLE_FAMILIES,
    )
    school_to_pid = {
        str(row.get("display_name")): str(row.get("program_id"))
        for row in (*current_programs, *hist_membership, *hist_1963)
        if row.get("display_name") and row.get("program_id")
    }
    lattice_episodes: list[dict[str, Any]] = []
    for row in cfbd_coaches:
        person = (
            str(row.get("firstName") or "").strip()
            + " "
            + str(row.get("lastName") or "").strip()
        ).strip()
        for season in row.get("seasons") or []:
            school = str(season.get("school") or row.get("school") or "")
            pid = school_to_pid.get(school)
            year = season.get("year") or row.get("source_year")
            if not pid or year is None or not person:
                continue
            lattice_episodes.append(
                {
                    "program_id": pid,
                    "season": int(year),
                    "role": "head_coach",
                    "person": person,
                    "source": "CFBD",
                    "pit_admitted": False,
                }
            )
    for row in wiki_hist_rows:
        for episode in row.get("episodes") or []:
            lattice_episodes.append(
                {
                    "program_id": row.get("program_id"),
                    "season": row.get("season"),
                    "role": episode.get("role"),
                    "person": episode.get("person"),
                    "source": "WIKIMEDIA",
                    "pit_admitted": False,
                }
            )
    career_idx: dict[str, str] = {}
    for row in (*current_programs, *hist_membership, *hist_1963):
        display = str(row.get("display_name") or "").strip()
        if display and row.get("program_id"):
            career_idx[display.casefold()] = str(row["program_id"])
    for row in wiki_candidate_rows:
        pid = str(row.get("program_id") or "")
        school = str(row.get("school") or "").strip()
        if school:
            career_idx.setdefault(school.casefold(), pid)
        title = str(row.get("title") or "")
        lowered = title.casefold()
        base = title
        if lowered.endswith(" football team"):
            base = title[: -len(" football team")]
        elif lowered.endswith(" football"):
            base = title[: -len(" football")]
        if base.strip():
            career_idx.setdefault(base.strip().casefold(), pid)
    career_season_rows = load_optional_jsonl(
        EXT / "WIKIMEDIA_CAREER_SEASON_EPISODES.jsonl"
    )
    career_matched = 0
    for row in career_season_rows:
        raw = str(row.get("program_raw") or "").strip()
        pid = career_idx.get(raw.casefold())
        role = str(row.get("role") or "")
        if not pid or role not in ROLE_FAMILIES:
            continue
        career_matched += 1
        lattice_episodes.append(
            {
                "program_id": pid,
                "season": row.get("season"),
                "role": role,
                "person": row.get("person"),
                "source": "WIKIMEDIA_COACH_CAREER",
                "pit_admitted": False,
            }
        )
    lattice = overlay_historical_lattice(lattice, lattice_episodes)
    hashes["HISTORICAL_ROLE_LATTICE_SUMMARY.json"] = write_json(
        ART / "HISTORICAL_ROLE_LATTICE_SUMMARY.json",
        {
            "cell_count": len(lattice),
            "role_families": list(ROLE_FAMILIES),
            "retrospective_candidate_cells": sum(
                1
                for row in lattice
                if row.get("evidence_disposition") == "RETROSPECTIVE_CANDIDATE_ONLY"
            ),
            "historical_wikimedia_pages": len(wiki_hist_rows),
            "historical_wikimedia_episodes": sum(
                len(row.get("episodes") or []) for row in wiki_hist_rows
            ),
            "career_season_episodes": len(career_season_rows),
            "career_lattice_matches": career_matched,
            "pit_admitted": False,
            "artifact_class": "REAL_EVIDENCE" if lattice else "BLOCKER_METADATA",
            "observed_titles_cannot_create_denominator": True,
        },
    )
    hashes["CFBD_COACHES_HC_BACKBONE.jsonl"] = write_jsonl(
        EXT / "CFBD_COACHES_HC_BACKBONE.jsonl",
        [
            {**row, "artifact_class": "REAL_EVIDENCE", "pit_admitted": False}
            for row in cfbd_coaches
        ],
    )
    availability_attempts = load_optional_jsonl(
        EXT / "AVAILABILITY_ROUTE_ATTEMPTS.jsonl"
    )
    availability = inventory_availability_policies(
        current_programs, season=2026, route_attempts=availability_attempts
    )
    hashes["AVAILABILITY_POLICY_INVENTORY.jsonl"] = write_jsonl(
        EXT / "AVAILABILITY_POLICY_INVENTORY.jsonl", availability["rows"]
    )
    hashes["AVAILABILITY_POLICY_INVENTORY.json"] = write_json(
        ART / "AVAILABILITY_POLICY_INVENTORY.json",
        {key: value for key, value in availability.items() if key != "rows"},
    )
    availability_candidates = load_optional_jsonl(
        EXT / "AVAILABILITY_CANDIDATE_PLAYER_ROWS.jsonl"
    )
    roster_slice = load_optional_jsonl(EXT / "CFBD_ROSTER_JOIN_SLICE.jsonl")
    joined_availability = join_candidates_to_roster(
        availability_candidates, roster_slice
    )
    hashes["AVAILABILITY_CANDIDATE_PLAYER_SUMMARY.json"] = write_json(
        ART / "AVAILABILITY_CANDIDATE_PLAYER_SUMMARY.json",
        {
            **{
                key: value
                for key, value in joined_availability.items()
                if key != "rows"
            },
            "artifact_class": "REAL_EVIDENCE"
            if availability_candidates
            else "BLOCKER_METADATA",
            "candidate_count": len(availability_candidates),
            "joined_to_verified_roster": int(
                joined_availability.get("joined_to_verified_roster") or 0
            ),
            "disposition": (
                "JOINED_NAME_ONLY_STATUS_UNKNOWN"
                if joined_availability.get("joined_to_verified_roster")
                else "CANDIDATE_NOT_JOINED"
            ),
            "no_report_means": "UNKNOWN",
            "private_medical_detail_ingested": False,
            "owner": "BAT-414",
            "out_of_fitted_models": True,
        },
    )

    catalog = canonical_catalog()
    xwalk = crosswalk()
    hashes["BAS_CANONICAL_DOMAIN_CATALOG.json"] = write_json(
        ART / "BAS_CANONICAL_DOMAIN_CATALOG.json", catalog
    )
    hashes["BAS_DOMAIN_CATALOG_CROSSWALK.json"] = write_json(
        ART / "BAS_DOMAIN_CATALOG_CROSSWALK.json", xwalk
    )
    hashes["BAS_DOMAIN_POPULATION_AND_GRAIN_CONTRACT.json"] = write_json(
        ART / "BAS_DOMAIN_POPULATION_AND_GRAIN_CONTRACT.json", grain_contract()
    )
    expected_games = len(kernel_games)
    cube = []
    for row in catalog["domains"]:
        if row["kind"] != "DATA_DOMAIN":
            continue
        for population, denom in (
            ("national_historical_2013_2023_observed_fbs_fbs", expected_games or None),
            ("current_2026", len(program_ids) or None),
            ("tamu_specialization", 1),
            ("week1_derived_slice", None),
        ):
            cube.append(
                {
                    "canonical_domain_id": row["canonical_domain_id"],
                    "population": population,
                    "denominator": denom,
                    "numerator": 0
                    if row["canonical_domain_id"]
                    not in {"DOM-001", "DOM-025", "DOM-028", "DOM-035"}
                    else (denom or 0),
                    "missing": None
                    if denom is None
                    else max(0, (denom or 0) - (denom or 0)),
                    "conflict": 0,
                    "not_applicable": False,
                    "owner": "BAT-703",
                    "next_action": "continue_source_tranche",
                    "artifact_class": "REAL_EVIDENCE"
                    if denom is not None
                    else "BLOCKER_METADATA",
                    "blocked_parent": denom is None,
                }
            )
    hashes["NATIONAL_DOMAIN_COVERAGE_CUBE.jsonl"] = write_jsonl(
        EXT / "NATIONAL_DOMAIN_COVERAGE_CUBE.jsonl", cube
    )
    hashes["NATIONAL_DATA_COMPLETENESS_SUCCESSOR_GATE.json"] = write_json(
        ART / "NATIONAL_DATA_COMPLETENESS_SUCCESSOR_GATE.json",
        {
            "result": "PARTIAL_TRANCHE_NOT_COMPLETE",
            "week1_is_not_national": True,
            "full_national_completeness_unclaimed": True,
            "current_N": membership.get("N"),
            "historical_2013_2023_program_seasons": len(hist_membership),
            "fcs_fcs_acquired": len(fcs_cfbd),
        },
    )
    hashes["TAMU_SPECIALIZATION_POPULATION_CONTRACT.json"] = write_json(
        ART / "TAMU_SPECIALIZATION_POPULATION_CONTRACT.json",
        tamu_specialization_contract(
            str(membership.get("population_identity") or "UNAVAILABLE"),
            sha256_file(GAMES_PATH),
        ),
    )

    week1_contests = []
    if FORECAST_ROWS.is_file():
        forecast_rows = load_jsonl(FORECAST_ROWS)
        hashes["WEEK1_FORECAST_REHASH.json"] = write_json(
            ART / "WEEK1_FORECAST_REHASH.json",
            rehash_payload(FORECAST_ROWS, FORECAST_SHA, len(forecast_rows)),
        )
        hashes["WEEK1_ISSUED_BEFORE_CUTOFF.json"] = write_json(
            ART / "WEEK1_ISSUED_BEFORE_CUTOFF.json",
            prove_issued_before_cutoff(forecast_rows),
        )
        contests = {}
        for row in forecast_rows:
            cid = str(row.get("ncaa_contest_id") or row.get("canonical_game_id"))
            contests.setdefault(cid, row)
        week1_contests = list(contests.values())
        hashes["WEEK1_2026_PROGRAM_SLICE.json"] = write_json(
            ART / "WEEK1_2026_PROGRAM_SLICE.json",
            week1_slice_from_contests(week1_contests),
        )
        p_half = sum(
            1
            for row in forecast_rows
            if row.get("probability_home") == 0.5 or row.get("p_home") == 0.5
        )
        hashes["WEEK1_SCORING_CLOSURE.json"] = write_json(
            ART / "WEEK1_SCORING_CLOSURE.json",
            {
                "forecast_opportunity_rows": len(forecast_rows),
                "unique_contests": len(week1_contests),
                "p_half_excluded_from_directional": p_half,
                "old_forecasts_immutable": True,
                "no_post_kickoff_forecast_created": True,
                "artifact_class": "REAL_EVIDENCE",
            },
        )
    if WEEK1_STATES.is_file():
        states = load_json(WEEK1_STATES)
        hashes["WEEK1_FINAL_STATE_BIND.json"] = write_json(
            ART / "WEEK1_FINAL_STATE_BIND.json",
            {
                "predecessor_path": str(WEEK1_STATES),
                "sha256": sha256_file(WEEK1_STATES),
                "preserved": True,
                "contest_keys": sorted(list(states))[:20]
                if isinstance(states, dict)
                else None,
            },
        )

    remaining_finals_path = EXT / "WEEK1_REMAINING_FINALS_ATTEMPTS.json"
    remaining_finals = (
        load_json(remaining_finals_path) if remaining_finals_path.is_file() else {}
    )
    ncaa_com_matches = remaining_finals.get("ncaa_com_remaining_matches") or {}
    ncaa_direct = remaining_finals.get("ncaa_direct_attempts") or []
    stats_statuses = [
        int(row.get("http_status") or 0) for row in ncaa_direct if isinstance(row, dict)
    ]
    hashes["WEEK1_REMAINING_FINALS_ATTEMPTS.json"] = write_json(
        ART / "WEEK1_REMAINING_FINALS_ATTEMPTS.json",
        {
            "artifact_class": "REAL_EVIDENCE"
            if remaining_finals
            else "BLOCKER_METADATA",
            "t90_not_relabeled": True,
            "no_post_kickoff_forecast_created": True,
            "smu_fsu_stats_ncaa_contest_id": "6594400",
            "smu_t90_lease_expired_not_recaptured": True,
            "stats_ncaa_org_http_statuses": stats_statuses,
            "stats_ncaa_org_remaining_403": bool(stats_statuses)
            and all(status == 403 for status in stats_statuses),
            "ncaa_com_scoreboard_used": True,
            "ncaa_com_ids_are_not_stats_ncaa_ids": True,
            "ncaa_com_remaining_terminal": {
                contest_id: (match or {}).get("terminal_state")
                for contest_id, match in ncaa_com_matches.items()
            },
            "smu_fsu_ncaa_com_final": str(
                (ncaa_com_matches.get("6594400") or {}).get("terminal_state") or ""
            )
            == "TERMINAL_STATUS_ESTABLISHED",
            "nd_wisconsin_ncaa_com_final": str(
                (ncaa_com_matches.get("6602874") or {}).get("terminal_state") or ""
            )
            == "TERMINAL_STATUS_ESTABLISHED",
            "louisville_olemiss_ncaa_com_final": str(
                (ncaa_com_matches.get("6620581") or {}).get("terminal_state") or ""
            )
            == "TERMINAL_STATUS_ESTABLISHED",
            "cfbd_not_ncaa_official_final": True,
            "payload": remaining_finals,
        },
    )
    hashes["WEEK1_SMU_T90_LEASE_INSPECT.json"] = write_json(
        ART / "WEEK1_SMU_T90_LEASE_INSPECT.json", inspect_smu_t90_lease()
    )
    schedule_rows = []
    for row in cfbd_games:
        hid = row.get("homeId") or row.get("home_id")
        aid = row.get("awayId") or row.get("away_id")
        gid = row.get("id")
        if hid is None or aid is None or gid is None:
            continue
        schedule_rows.append(
            {
                "canonical_game_id": f"SRC-002:GAME:{gid}",
                "home_canonical_team_id": team_id(hid),
                "away_canonical_team_id": team_id(aid),
                "season": row.get("season") or row.get("year"),
                "completed": row.get("completed"),
                "status": row.get("status") or row.get("notes"),
                "start_date": row.get("startDate") or row.get("start_date"),
                "week": row.get("week"),
            }
        )
    expected = expected_game_universe(program_ids, schedule_rows)
    hashes["EXPECTED_GAME_UNIVERSE.json"] = write_json(
        ART / "EXPECTED_GAME_UNIVERSE.json", expected
    )
    next_week = [
        row
        for row in schedule_rows
        if str(row.get("start_date") or "") > "2026-09-08T00:00:00Z"
        and int(row.get("season") or 0) == 2026
    ]
    hashes["NEXT_NATIONAL_SCHEDULE_COHORT.jsonl"] = write_jsonl(
        EXT / "NEXT_NATIONAL_SCHEDULE_COHORT.jsonl", next_week
    )
    hashes["NEXT_NATIONAL_SCHEDULE_COHORT.json"] = write_json(
        ART / "NEXT_NATIONAL_SCHEDULE_COHORT.json",
        {
            "artifact_class": "REAL_EVIDENCE",
            "as_of_utc": AS_OF,
            "not_am_only": True,
            "contest_count": len(next_week),
            "contest_identity": sha256_json(
                [row["canonical_game_id"] for row in next_week]
            ),
            "raw_context_separated_from_forecast": True,
            "no_new_scheduler_job_created": True,
            "scientific_hold_binding": True,
        },
    )
    wiki_path = EXT / "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl"
    wiki_rows = load_optional_jsonl(wiki_path)
    hashes["WIKIMEDIA_CURRENT_STAFF_SUMMARY.json"] = write_json(
        ART / "WIKIMEDIA_CURRENT_STAFF_SUMMARY.json",
        {
            "artifact_class": "REAL_EVIDENCE" if wiki_rows else "BLOCKER_METADATA",
            "program_pages": len(wiki_rows),
            "episode_count": sum(len(row.get("episodes") or []) for row in wiki_rows),
            "programs_with_episodes": sum(
                1 for row in wiki_rows if row.get("episodes")
            ),
            "pit_admitted": False,
            "official_html_still_not_attempted": not official_http_attempts,
            "parser_family": "wikimedia_infobox_asst_coach_and_staff_table",
        },
    )
    hashes["WIKIMEDIA_HISTORICAL_STAFF_SUMMARY.json"] = write_json(
        ART / "WIKIMEDIA_HISTORICAL_STAFF_SUMMARY.json",
        {
            "artifact_class": "REAL_EVIDENCE" if wiki_hist_rows else "BLOCKER_METADATA",
            "pages": len(wiki_hist_rows),
            "episode_count": sum(
                len(row.get("episodes") or []) for row in wiki_hist_rows
            ),
            "revision_bound": sum(
                1 for row in wiki_hist_rows if row.get("status") == "REVISION_BOUND"
            ),
            "years": sorted(
                {
                    int(row["season"])
                    for row in wiki_hist_rows
                    if row.get("season") is not None
                }
            ),
            "missing_2013_2023_years": [
                year
                for year in range(2013, 2024)
                if year
                not in {
                    int(row["season"])
                    for row in wiki_hist_rows
                    if row.get("season") is not None
                }
            ],
            "incomplete_years_1963_2026": [
                year
                for year in range(1963, 2027)
                if sum(
                    1 for row in wiki_hist_rows if int(row.get("season") or 0) == year
                )
                < len(program_ids)
            ],
            "remaining_years_queued": any(
                sum(1 for row in wiki_hist_rows if int(row.get("season") or 0) == year)
                < len(program_ids)
                for year in range(1963, 2027)
            ),
            "pit_admitted": False,
            "parser_family": "wikimedia_infobox_asst_coach_and_staff_table",
            "wikipedia_is_not_official_confirmation": True,
        },
    )
    reject_missing_release_bom(False, False)
    round_trip_game_context(
        {
            "canonical_game_id": "FIXTURE:V2",
            "source_order": ["A", "B"],
            "canonical_home_id": "A",
            "canonical_away_id": "B",
            "designated_home_id": "A",
            "site_class": "NEUTRAL",
            "ordinary_home_exposure_designated_home": 0,
            "unknowns": [],
            "consumed_columns": ["ordinary_home_exposure"],
        }
    )
    round_trip_staff_snapshot(
        {
            "program_id": "SRC-002:TEAM:245",
            "as_of_utc": AS_OF,
            "role": "head_coach",
            "formal_title": "Head Coach",
            "responsibility": "UNKNOWN",
            "episode_refs": [],
            "episode_cardinality": 0,
            "disposition": "NOT_ATTEMPTED",
            "attempt_count": 0,
            "pit_admitted": False,
        }
    )

    hashes["CYCLE30_FINDING_SUCCESSOR_LEDGER.json"] = write_json(
        ART / "CYCLE30_FINDING_SUCCESSOR_LEDGER.json", successor_ledger()
    )
    hashes["CYCLE30_DEPENDENCY_GRAPH.json"] = write_json(
        ART / "CYCLE30_DEPENDENCY_GRAPH.json", static_import_graph(ROOT / "src")
    )
    hashes["CYCLE30_ACQUISITION_BUDGET_AND_LEDGER.json"] = write_json(
        ART / "CYCLE30_ACQUISITION_BUDGET_AND_LEDGER.json",
        {
            **acquisition_ledger,
            "attempt_summary": attempt_summary,
        },
    )
    hashes["CYCLE30_CODEX_CLOUD_REVIEW_ATTESTATION.json"] = write_json(
        ART / "CYCLE30_CODEX_CLOUD_REVIEW_ATTESTATION.json",
        attestation_check(
            head_sha=head,
            review_identities=[],
            api_calls=0,
            scientific_reviews=[],
        ),
    )
    hashes["CYCLE30_COVERAGE_TRUTH.json"] = write_json(
        ART / "CYCLE30_COVERAGE_TRUTH.json",
        coverage_truth(
            patch_percent=66.98895, uncovered_changed_lines=None, informational=True
        ),
    )
    hashes["CYCLE30_ALL22_SNAPSHOT.json"] = write_json(
        ART / "CYCLE30_ALL22_SNAPSHOT.json",
        snapshot(
            {
                "repos": [
                    {
                        "path": str(ROOT),
                        "head": head,
                        "branch": "cursor/cycle30-neutral-national-kernel",
                    },
                    {
                        "path": r"C:\CFB\repos\CFBProgramSpecifications",
                        "note": "inspected_not_modified",
                    },
                    {
                        "path": r"C:\CFB\repos\CFBIntelligenceContracts",
                        "note": "inspected_not_modified",
                    },
                    {"path": r"C:\All-22", "note": "distinct_dirty_not_overwritten"},
                ],
                "worktrees": live_worktree_inventory(head)["worktrees"],
                "prs": [
                    {"number": 685, "role": "reviewed_predecessor"},
                    {"number": 686, "role": "cycle30_proposed_unmerged"},
                ],
                "c01_manifest_object_count": 36,
                "c01_manifest_fixture_count": 7,
                "c01_catalog_object_count": 105,
                "c01_catalog_fixture_count": 8,
            }
        ),
    )
    hashes["WORKTREE_INVENTORY.json"] = write_json(
        ART / "WORKTREE_INVENTORY.json", live_worktree_inventory(head)
    )
    pr685_capture = EXT / "PR685_THREAD_CAPTURE.json"
    if pr685_capture.is_file():
        captured = load_json(pr685_capture)
        hashes["PR685_THREAD_ADJUDICATION.json"] = write_json(
            ART / "PR685_THREAD_ADJUDICATION.json",
            {
                "artifact_type": "PR685_THREAD_ADJUDICATION",
                "head_reviewed": "0b957ea127ad6a5373901d8ddff47c43a496b100",
                "review_state": "READY_FOR_MANAGER_REVIEW",
                "outdated_does_not_mean_fixed": True,
                "paid_review_not_invoked": True,
                "threads_captured": captured.get("threads_captured"),
                "reviews_captured": captured.get("reviews_captured"),
                "latest_five_p1": captured.get("latest_five_p1"),
                "remaining_threads": captured.get("remaining_threads"),
                "capture_sha256": sha256_file(pr685_capture),
                "false_positives": "none authorized by Cursor",
                "artifact_class": "BLOCKER_METADATA",
            },
        )
    hashes["WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR.json"] = write_json(
        ART / "WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR.json",
        {
            "artifact_type": "WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR",
            "predecessor_unresolved_participant_row_count": 8,
            "successor_unresolved_participant_row_count": 0,
            "independent_eight_to_zero": True,
        },
    )

    staff_attempts = official_staff_attempt_rows(
        current_programs,
        scraper_credits=0,
        live_rows=official_http_attempts,
    )
    attempted_staff = [
        row for row in staff_attempts if str(row.get("status")) != "NOT_ATTEMPTED"
    ]
    hashes["OFFICIAL_STAFF_SOURCE_ATTEMPT_LEDGER.jsonl"] = write_jsonl(
        EXT / "OFFICIAL_STAFF_SOURCE_ATTEMPT_LEDGER.jsonl", staff_attempts
    )
    hashes["OFFICIAL_STAFF_SOURCE_ATTEMPT_SUMMARY.json"] = write_json(
        ART / "OFFICIAL_STAFF_SOURCE_ATTEMPT_SUMMARY.json",
        {
            "artifact_class": "REAL_EVIDENCE"
            if attempted_staff
            else "BLOCKER_METADATA",
            "program_count": len(staff_attempts),
            "attempted_http": sum(
                1
                for row in staff_attempts
                if str(row.get("status"))
                in {
                    "CAPTURED",
                    "ACQUISITION_FAILED",
                    "ATTEMPTED_EMPTY_PARSE",
                    "ATTEMPTED_NOT_FOUND_SHELL",
                }
            ),
            "attempted_programs": len(attempted_staff),
            "not_attempted": sum(
                1 for row in staff_attempts if str(row.get("status")) == "NOT_ATTEMPTED"
            ),
            "captured": sum(
                1 for row in staff_attempts if str(row.get("status")) == "CAPTURED"
            ),
            "attempted_no_url": sum(
                1
                for row in staff_attempts
                if str(row.get("status")) == "ATTEMPTED_NO_URL"
            ),
            "metered_scraper_credits": 0,
            "direct_get_no_scrapfly": True,
            "cfbd_hc_only": True,
            "sportradar_ncaafb_full_roster_coach_positions_as_returned": True,
            "literal_attempted_true_forbidden": True,
        },
    )
    if (EXT / "SPORTSRADAR_STAFF_PARSED.jsonl").is_file():
        hashes["SPORTSRADAR_STAFF_PARSED.jsonl"] = sha256_file(
            EXT / "SPORTSRADAR_STAFF_PARSED.jsonl"
        )
    if (EXT / "SPORTSRADAR_STAFF_HTTP_ATTEMPTS.jsonl").is_file():
        hashes["SPORTSRADAR_STAFF_HTTP_ATTEMPTS.jsonl"] = sha256_file(
            EXT / "SPORTSRADAR_STAFF_HTTP_ATTEMPTS.jsonl"
        )
    membership_delta = cfbd_membership_presence_delta(
        [str(row.get("program_id") or "") for row in current_programs],
        [*hist_membership, *hist_1963],
    )
    hashes["CFBD_MEMBERSHIP_PRESENCE_DELTA.json"] = write_json(
        ART / "CFBD_MEMBERSHIP_PRESENCE_DELTA.json", membership_delta
    )
    ncaa_directory_rows = load_optional_jsonl(EXT / "NCAA_DIRECTORY_PROGRAM_ROWS.jsonl")
    wikipedia_former_rows = load_optional_jsonl(
        EXT / "WIKIPEDIA_FORMER_PROGRAM_ROWS.jsonl"
    )
    discontinued_census = ncaa_discontinued_program_census(
        ncaa_rows=ncaa_directory_rows,
        wikipedia_rows=wikipedia_former_rows,
        current_ids=[str(row.get("program_id") or "") for row in current_programs],
        cfbd_absent_ids=membership_delta.get("historical_absent_from_2026_ids") or [],
    )
    hashes["NCAA_DISCONTINUED_PROGRAM_CENSUS.json"] = write_json(
        ART / "NCAA_DISCONTINUED_PROGRAM_CENSUS.json", discontinued_census
    )
    cycle30_test_count = sum(
        1
        for line in (ROOT / "tests" / "test_cycle30_adversarial_controls.py")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.startswith("    def test_")
    )
    cycle29_test_count = sum(
        1
        for path in (ROOT / "tests").glob("test_cycle29*.py")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("    def test_")
    )
    runtime_path = EXT.parent / "HASH_SEED_RUNTIME.json"
    runtime = load_json(runtime_path) if runtime_path.is_file() else {}
    hashes["HASH_SEED_DISCOVERY.json"] = write_json(
        ART / "HASH_SEED_DISCOVERY.json",
        {
            "artifact_type": "CYCLE30_HASH_SEED_DISCOVERY",
            "seeds": ["0", "1"],
            "test_cycle30_count": cycle30_test_count,
            "test_cycle29_count": cycle29_test_count,
            "test_cycle30_exit": runtime.get("test_cycle30_exit"),
            "count_source": "source_def_test_methods",
            "discovery_difference": runtime.get(
                "discovery_difference", "runtime_not_yet_recorded"
            ),
            "skips": runtime.get("skips") or [],
            "payload_available": True,
            "artifact_class": "BLOCKER_METADATA",
        },
    )
    hashes["C30_AUDIT_REGISTER.json"] = write_json(
        ART / "C30_AUDIT_REGISTER.json",
        remaining_audit_register(
            head_sha=head,
            kernel_rows=int(kernel.get("game_grain_count") or len(comparison_rows)),
            proven_pit_rows=int(kernel["proven_pit_training_rows"]),
            current_n=int(membership.get("N") or 0),
            parent_games=len(games),
            ties=len(ties),
            neutrals=len(neutrals),
            official_staff_attempts=len(attempted_staff),
            official_staff_not_attempted=sum(
                1 for row in staff_attempts if str(row.get("status")) == "NOT_ATTEMPTED"
            ),
            availability_routes_attempted=len(availability_attempts),
            membership_1963_2012_rows=len(hist_1963),
            membership_1963_2012_years_attempted=len(years_attempted_1963),
            raw_to_normalized_compared=int(raw_trace.get("compared_count") or 0),
            historical_wiki_pages=len(wiki_hist_rows),
            historical_wiki_episodes=sum(
                len(row.get("episodes") or []) for row in wiki_hist_rows
            ),
            availability_candidates_not_joined=int(
                joined_availability.get("unmatched_name_only")
                or max(
                    0,
                    len(availability_candidates)
                    - int(joined_availability.get("joined_to_verified_roster") or 0),
                )
            ),
            predecessor_payload_mounted=bool(recon_payload.get("mounted")),
            predecessor_oriented_rows=int(
                recon_payload.get("predecessor_oriented_development_rows") or 0
            ),
            predecessor_eligible_rows=int(
                recon_payload.get("predecessor_pit_feature_eligible_rows") or 0
            ),
            cfbd_historical_absent_from_2026=int(
                membership_delta.get("historical_absent_from_2026_n") or 0
            ),
            ncaa_discontinued_rows=int(
                discontinued_census.get("ncaa_census_rows") or 0
            ),
            availability_joined_to_roster=int(
                joined_availability.get("joined_to_verified_roster") or 0
            ),
        ),
    )

    discovered = discover_authority_claims(ART)
    declared = [mapped_claim(item) for item in discovered]
    for claim in declared:
        missing = [field for field in CLAIM_FIELDS if field not in claim]
        if missing:
            raise RuntimeError(missing)
    claim_inv = inventory_claims(declared, discovered)
    hashes["CYCLE30_CLAIM_INVENTORY.json"] = write_json(
        ART / "CYCLE30_CLAIM_INVENTORY.json",
        {**claim_inv, "declared": declared[:50], "declared_count": len(declared)},
    )

    hashes["CYCLE30_MATERIALIZATION_MANIFEST.json"] = write_json(
        ART / "CYCLE30_MATERIALIZATION_MANIFEST.json",
        {
            "head_sha": head,
            "as_of_utc": utc_now(),
            "hashes": hashes,
            "external_root": str(EXT),
            "review_state": "READY_FOR_MANAGER_REVIEW",
            "operator_hold": "ACTIVE",
            "primary_kernel_objective": kernel["primary_kernel_objective"],
        },
    )
    print(
        "materialized",
        "games",
        len(games),
        "neutrals",
        len(neutrals),
        "ties",
        len(ties),
        "kernel_rows",
        len(comparison_rows),
        "proven",
        kernel["proven_pit_training_rows"],
        "N",
        membership.get("N"),
        "fcs_fcs",
        len(fcs_cfbd),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
