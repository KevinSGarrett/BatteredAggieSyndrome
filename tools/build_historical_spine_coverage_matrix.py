from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EVENT_RUN = "a3914e3f5b3fa95c81b7ee08338e27901ac07da870277967234dbe1fb7cd2080"
DISCOVERY_SEASONS = tuple(range(2010, 2026))


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def select_strongest_discovery(data_root: Path, season: int) -> tuple[Path, dict[str, Any]]:
    root = (
        data_root
        / "manifests/acquisition/BAT-554-NCAA-OFFICIAL-BOUNDED-V1/discovery"
        / str(season)
        / "sha256"
    )
    candidates: list[tuple[tuple[int, int, int, int, str], Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*/ncaa_team_graph_discovery_manifest.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        identity = str(item.get("discovery_identity", ""))
        if identity != path.parent.name:
            raise ValueError(f"discovery identity/path mismatch: {path}")
        rank = (
            int(item.get("state") == "COMPLETE_GRAPH_EXHAUSTED"),
            int(item.get("team_page_capture_count", 0)),
            len(item.get("discovered_contest_ids", [])),
            -int(item.get("team_failure_count", 0)),
            identity,
        )
        candidates.append((rank, path, item))
    if not candidates:
        raise FileNotFoundError(f"no immutable NCAA discovery manifest for season {season}")
    _, path, item = max(candidates, key=lambda row: row[0])
    return path, item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    event_path = data_root / "manifests/preliminary_event_chronology/sha256" / EVENT_RUN / "run_manifest.json"
    event = json.loads(event_path.read_text(encoding="utf-8"))
    target_counts = event["population"]["target_counts_by_season"]
    discoveries: dict[int, tuple[Path, dict[str, Any]]] = {}
    for season in DISCOVERY_SEASONS:
        try:
            discoveries[season] = select_strongest_discovery(data_root, season)
        except FileNotFoundError:
            # Missing seasons are explicit NOT_STARTED rows below; partial
            # availability in one season never discards another season.
            continue
    rows: list[dict[str, Any]] = []
    for season in range(2010, 2026):
        rows.append({
            "season": season,
            "season_type": "REGULAR_AND_POSTSEASON_COMBINED",
            "source": "CFBD_PLUS_CANONICAL_RECONCILIATION",
            "endpoint": "COMPLETED_GAME_OUTCOME_SPINE",
            "domain": "SCHEDULES_AND_OFFICIAL_OUTCOMES",
            "grain": "CANONICAL_GAME",
            "schema_version": "expanded-event-chronology-week-batched-v1",
            "canonical_games": int(target_counts[str(season)]),
            "canonical_teams": None,
            "missingness": "170 cold-start prior-feature rows across the full 2010-2025 matrix; outcome target rows are present for this season.",
            "reconciliation_quality": "EXACT_CANONICAL_GAME_IDENTITY_IN_ACCEPTED_PRELIMINARY_EVENT_MATRIX",
            "capture_identity": event["dataset_identity"],
            "provenance_identity": sha256_file(event_path),
            "known_at_pit_eligibility": "PRELIMINARY_UNPROTECTED_EVENT_CHRONOLOGY_ONLY",
            "eligibility_tiers": ["OUTCOME_ELO", "TEAM_STRENGTH_PRELIMINARY"],
        })
        discovery = discoveries.get(season)
        if discovery:
            path, item = discovery
            rows.append({
                "season": season,
                "season_type": "SOURCE_TEAM_SEASON_GRAPH",
                "source": "NCAA_OFFICIAL_STATS",
                "endpoint": "stats.ncaa.org/teams/{team_season_id}",
                "domain": "OFFICIAL_CONTEST_DISCOVERY",
                "grain": "TEAM_SEASON_AND_CONTEST_ID",
                "schema_version": item["schema_version"],
                "canonical_games": None,
                "canonical_teams": None,
                "team_pages": item["team_page_capture_count"],
                "discovered_team_seasons": len(item["discovered_team_season_ids"]),
                "discovered_contest_ids": len(item["discovered_contest_ids"]),
                "remaining_queue": len(item["remaining_queue"]),
                "missingness": "Graph exhausted" if not item["remaining_queue"] else "Partial source graph; remaining team-season queue preserved.",
                "reconciliation_quality": "SOURCE_IDS_DISCOVERED_CANONICAL_GAME_TEAM_RECONCILIATION_PENDING",
                "capture_identity": item["discovery_identity"],
                "provenance_identity": sha256_file(path),
                "known_at_pit_eligibility": "CANDIDATE_ONLY_NOT_ADMITTED",
                "eligibility_tiers": [],
                "state": item["state"],
            })
        else:
            rows.append({
                "season": season,
                "season_type": "SOURCE_TEAM_SEASON_GRAPH",
                "source": "NCAA_OFFICIAL_STATS",
                "endpoint": "stats.ncaa.org/teams/{team_season_id}",
                "domain": "OFFICIAL_CONTEST_DISCOVERY",
                "grain": "TEAM_SEASON_AND_CONTEST_ID",
                "schema_version": "BAT-554-NCAA-OFFICIAL-BOUNDED-V1",
                "canonical_games": None,
                "canonical_teams": None,
                "team_pages": 0,
                "discovered_team_seasons": 0,
                "discovered_contest_ids": 0,
                "remaining_queue": None,
                "missingness": "Season discovery tranche not yet executed.",
                "reconciliation_quality": "NOT_STARTED",
                "capture_identity": None,
                "provenance_identity": None,
                "known_at_pit_eligibility": "NOT_EVALUATED",
                "eligibility_tiers": [],
                "state": "NOT_STARTED",
            })
    rows.append({
        "season": 2024,
        "season_type": "BOUNDED_SAMPLE_ONLY",
        "source": "NCAA_OFFICIAL_STATS",
        "endpoint": "contest/5362283/*",
        "domain": "GAMEBOOK_EQUIVALENT_LINESCORE_GAME_INFO_VENUE_ATTENDANCE_OFFICIALS_DRIVES_TEAM_STATS_PLAYER_STATS_PLAY_BY_PLAY",
        "grain": "CONTEST_DOMAIN_RECORD",
        "schema_version": "BAT-554-NCAA-OFFICIAL-BOUNDED-V1",
        "canonical_games": 1,
        "canonical_teams": 2,
        "normalized_rows": 406,
        "missingness": "Bounded parser/transport validation sample only; no national completeness claim.",
        "reconciliation_quality": "BOUNDED_EXACT_CONTEST_SAMPLE",
        "capture_identity": "b58e69d2df9531d25ac252b5b2edd19102df4b8506c2f3b4529c9f6f842cf9ca",
        "provenance_identity": "6f8f5f01c34a32533dadb273813bb99fb50c56711426e27cd6752cd958270ee5",
        "known_at_pit_eligibility": "CANDIDATE_ONLY_NOT_ADMITTED",
        "eligibility_tiers": [],
        "state": "BOUNDED_SAMPLE_VALIDATED",
    })
    payload = {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_SPINE_COVERAGE_AND_ELIGIBILITY_MATRIX",
        "classification": "MIXED_DOMAIN_TIERED_ELIGIBILITY",
        "rows": rows,
        "row_count": len(rows),
        "seasons": list(range(2010, 2026)),
        "spine_rule": "Outcomes, schedules, canonical identity, and known-at correctness are the spine; incomplete attached domains do not discard an otherwise useful season.",
        "negative_findings": [
            "NCAA official contest discovery is complete only for 2024.",
            "The 2025 NCAA graph remains partial at the 250-page checkpoint.",
            "NCAA discovery for 2010-2022 has not yet executed; 2023 is a bounded partial tranche.",
            "Only one bounded 2024 contest has validated all eight parser-domain groups; this is not population coverage.",
            "No NCAA gamebook row currently has preliminary-training, protected, champion, or production authority."
        ],
    }
    payload["matrix_identity"] = hashlib.sha256(canonical_json(payload)).hexdigest()
    output = data_root / "manifests/historical_spine_coverage/sha256" / payload["matrix_identity"] / "coverage_matrix.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(payload) + b"\n")
    print(json.dumps({"result": "PASS", "matrix_identity": payload["matrix_identity"], "rows": len(rows), "path": str(output), "sha256": sha256_file(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
