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


def discovery_manifest_core(item: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable identity payload used by NCAA discovery manifests."""
    return {
        key: value
        for key, value in item.items()
        if key not in {"discovery_identity", "issued_at_utc", "credentials_logged_or_persisted"}
    }


def acquisition_manifest_core(item: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable identity payload used by NCAA acquisition manifests."""
    return {
        key: value
        for key, value in item.items()
        if key not in {"acquisition_identity", "issued_at_utc", "credentials_logged_or_persisted"}
    }


def validation_report_core(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key != "validation_identity"}


def select_pass_validation(
    data_root: Path,
    acquisition_identity: str,
    manifest_sha256: str,
) -> tuple[Path, dict[str, Any]] | None:
    root = (
        data_root
        / "validation/POST-SUBTASK-197/ncaa-official-gamebooks"
        / acquisition_identity
        / "runs"
    )
    candidates: list[tuple[tuple[int, int, str, str], Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*/report.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        identity = str(item.get("validation_identity", ""))
        if identity != path.parent.name:
            raise ValueError(f"validation identity/path mismatch: {path}")
        if identity != hashlib.sha256(canonical_json(validation_report_core(item))).hexdigest():
            raise ValueError(f"validation content identity mismatch: {path}")
        if str(item.get("acquisition_identity")) != acquisition_identity:
            raise ValueError(f"validation acquisition identity mismatch: {path}")
        if str(item.get("manifest_sha256")) != manifest_sha256:
            raise ValueError(f"validation manifest hash mismatch: {path}")
        if item.get("result") != "PASS":
            continue
        rank = (
            int(item.get("check_count", 0)),
            int(item.get("mutation_control_count", 0)),
            str(item.get("validated_at_utc", "")),
            identity,
        )
        candidates.append((rank, path, item))
    if not candidates:
        return None
    _, path, item = max(candidates, key=lambda row: row[0])
    return path, item


def validated_acquisition_manifests(
    data_root: Path,
    season: int,
    reconciliation_identity: str,
) -> list[tuple[Path, dict[str, Any], Path, dict[str, Any]]]:
    root = data_root / "manifests/acquisition/BAT-554-NCAA-OFFICIAL-BOUNDED-V1/sha256"
    selected: list[tuple[Path, dict[str, Any], Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*/ncaa_official_gamebook_acquisition_manifest.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        selection = item.get("selection_evidence", {})
        if (
            item.get("artifact_type") != "NCAA_OFFICIAL_GAMEBOOK_ACQUISITION_MANIFEST"
            or int(selection.get("season", -1)) != season
            or str(selection.get("dataset_identity", "")) != reconciliation_identity
        ):
            continue
        identity = str(item.get("acquisition_identity", ""))
        if identity != path.parent.name:
            raise ValueError(f"acquisition identity/path mismatch: {path}")
        if identity != hashlib.sha256(canonical_json(acquisition_manifest_core(item))).hexdigest():
            raise ValueError(f"acquisition content identity mismatch: {path}")
        manifest_sha = sha256_file(path)
        validation = select_pass_validation(data_root, identity, manifest_sha)
        if validation is None:
            continue
        validation_path, validation_item = validation
        selected.append((path, item, validation_path, validation_item))
    return selected


def build_official_acquisition_rollup(
    data_root: Path,
    season: int,
    reconciliation_identity: str,
) -> dict[str, Any] | None:
    manifests = validated_acquisition_manifests(data_root, season, reconciliation_identity)
    if not manifests:
        return None
    best_by_request: dict[tuple[str, str], tuple[tuple[int, int, int, int, str], dict[str, Any]]] = {}
    observed_request_count = 0
    evidence: list[dict[str, Any]] = []
    for manifest_path, manifest, validation_path, validation in manifests:
        observed_request_count += int(manifest["request_count"])
        evidence.append({
            "acquisition_identity": manifest["acquisition_identity"],
            "manifest_sha256": sha256_file(manifest_path),
            "validation_identity": validation["validation_identity"],
            "validation_report_sha256": sha256_file(validation_path),
            "check_count": int(validation["check_count"]),
            "mutation_control_count": int(validation["mutation_control_count"]),
        })
        for request in manifest["captures"]:
            key = (str(request["contest_id"]), str(request["endpoint_id"]))
            parsed = [
                row for row in request.get("normalization", [])
                if row.get("state") == "PARSED_CANDIDATE"
            ]
            rank = (
                int(request.get("state") == "CAPTURED"),
                len(parsed),
                sum(int(row.get("row_count", 0)) for row in parsed),
                int(request.get("raw_bytes", 0)),
                str(request.get("request_identity_sha256", "")),
            )
            if key not in best_by_request or rank > best_by_request[key][0]:
                best_by_request[key] = (rank, request)
    selected_requests = [best_by_request[key][1] for key in sorted(best_by_request)]
    captured = [row for row in selected_requests if row.get("state") == "CAPTURED"]
    failed = [row for row in selected_requests if row.get("state") != "CAPTURED"]
    domain_capture_counts: dict[str, int] = {}
    normalized_row_counts: dict[str, int] = {}
    domain_contests: dict[str, set[str]] = {}
    for request in captured:
        for normalized in request.get("normalization", []):
            if normalized.get("state") != "PARSED_CANDIDATE":
                continue
            domain = str(normalized["domain"])
            domain_capture_counts[domain] = domain_capture_counts.get(domain, 0) + 1
            normalized_row_counts[domain] = normalized_row_counts.get(domain, 0) + int(normalized["row_count"])
            domain_contests.setdefault(domain, set()).add(str(request["contest_id"]))
    unresolved_endpoint_requests = [
        {
            "contest_id": str(request["contest_id"]),
            "endpoint_id": str(request["endpoint_id"]),
            "attempt_conditions": [str(row.get("condition", "UNKNOWN")) for row in request.get("attempts", [])],
        }
        for request in failed
    ]
    evidence.sort(key=lambda row: (row["acquisition_identity"], row["validation_identity"]))
    rollup_core = {
        "season": season,
        "reconciliation_identity": reconciliation_identity,
        "evidence": evidence,
        "selected_requests": [
            {
                "contest_id": str(row["contest_id"]),
                "endpoint_id": str(row["endpoint_id"]),
                "state": str(row["state"]),
                "request_identity_sha256": str(row.get("request_identity_sha256", "")),
                "raw_sha256": row.get("raw_sha256"),
                "normalization_identities": sorted(
                    str(item["normalization_identity"])
                    for item in row.get("normalization", [])
                    if item.get("state") == "PARSED_CANDIDATE"
                ),
            }
            for row in selected_requests
        ],
    }
    rollup_identity = hashlib.sha256(canonical_json(rollup_core)).hexdigest()
    contests = sorted({str(row["contest_id"]) for row in selected_requests})
    canonical_games = sorted({str(row["canonical_game_id"]) for row in selected_requests})
    return {
        "season": season,
        "season_type": "REGULAR_AND_POSTSEASON_COMBINED",
        "source": "NCAA_OFFICIAL_STATS",
        "endpoint": "RECONCILED_CONTEST_GAMEBOOK_ENDPOINTS",
        "domain": "OFFICIAL_GAMEBOOK_EQUIVALENT_ACQUISITION",
        "grain": "CANONICAL_GAME_ENDPOINT_AND_NORMALIZED_DOMAIN",
        "schema_version": "BAT-554-NCAA-OFFICIAL-ACQUISITION-ROLLUP-V1",
        "canonical_games": len(canonical_games),
        "canonical_teams": None,
        "official_contests": len(contests),
        "unique_endpoint_requests": len(selected_requests),
        "captured_endpoint_requests": len(captured),
        "unresolved_endpoint_requests": unresolved_endpoint_requests,
        "technical_failure_count": len(failed),
        "source_request_observations": observed_request_count,
        "duplicate_request_observations": observed_request_count - len(selected_requests),
        "validated_manifest_count": len(manifests),
        "validation_check_count": sum(int(row[3]["check_count"]) for row in manifests),
        "mutation_control_count": sum(int(row[3]["mutation_control_count"]) for row in manifests),
        "domain_capture_counts": dict(sorted(domain_capture_counts.items())),
        "domain_contest_counts": {key: len(value) for key, value in sorted(domain_contests.items())},
        "normalized_row_counts": dict(sorted(normalized_row_counts.items())),
        "normalized_rows": sum(normalized_row_counts.values()),
        "total_raw_bytes": sum(int(row.get("raw_bytes", 0)) for row in captured),
        "missingness": (
            f"{len(failed)} of {len(selected_requests)} unique contest-endpoint requests remain technically unavailable; "
            "each failed endpoint is preserved independently and does not invalidate other game domains."
        ),
        "reconciliation_quality": "EXACT_RECONCILIATION_DATASET_BOUND_NO_NAME_ONLY_PROMOTION",
        "capture_identity": rollup_identity,
        "provenance_identity": hashlib.sha256(canonical_json(evidence)).hexdigest(),
        "known_at_pit_eligibility": "CANDIDATE_ONLY_NOT_ADMITTED",
        "eligibility_tiers": [],
        "coverage_state": "PARTIAL_VALIDATED_OFFICIAL_DOMAIN_ACQUISITION",
        "authority": {
            "historical_pit_eligible": False,
            "training_eligible": False,
            "protected_evaluation_eligible": False,
            "production_eligible": False,
        },
    }


def select_strongest_discovery(data_root: Path, season: int) -> tuple[Path, dict[str, Any]]:
    root = (
        data_root
        / "manifests/acquisition/BAT-554-NCAA-OFFICIAL-BOUNDED-V1/discovery"
        / str(season)
        / "sha256"
    )
    candidates: list[tuple[tuple[int, int, int, int, int, str], Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*/ncaa_team_graph_discovery_manifest.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        identity = str(item.get("discovery_identity", ""))
        if identity != path.parent.name:
            raise ValueError(f"discovery identity/path mismatch: {path}")
        if identity != hashlib.sha256(canonical_json(discovery_manifest_core(item))).hexdigest():
            raise ValueError(f"discovery content identity mismatch: {path}")
        rank = (
            len(item.get("discovered_contest_ids", [])),
            int(item.get("legacy_schedule_record_count", 0)),
            int(item.get("team_page_capture_count", 0)),
            len(item.get("discovered_team_season_ids", [])),
            int(item.get("state") == "COMPLETE_GRAPH_EXHAUSTED"),
            -int(item.get("team_failure_count", 0)),
            identity,
        )
        candidates.append((rank, path, item))
    if not candidates:
        raise FileNotFoundError(f"no immutable NCAA discovery manifest for season {season}")
    _, path, item = max(candidates, key=lambda row: row[0])
    return path, item


def select_strongest_reconciliation(data_root: Path, season: int) -> tuple[Path, dict[str, Any]]:
    root = data_root / "manifests/ncaa_contest_reconciliation/sha256"
    candidates: list[tuple[tuple[int, int, int, int, int, str], Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*/run_manifest.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        identity = str(item.get("dataset_identity", ""))
        identity_core = item.get("identity_core")
        if not identity or not isinstance(identity_core, dict):
            continue
        if identity != path.parent.name:
            raise ValueError(f"reconciliation identity/path mismatch: {path}")
        if identity != hashlib.sha256(canonical_json(identity_core)).hexdigest():
            raise ValueError(f"reconciliation content identity mismatch: {path}")
        if int(identity_core.get("season", -1)) != season:
            continue
        population = identity_core.get("population", {})
        rank = (
            int(population.get("reconciled_contests", 0)) + int(population.get("reconciled_legacy_games", 0)),
            int(population.get("captured_team_pages", 0)),
            int(population.get("discovered_contests", 0)),
            -int(population.get("unresolved_contests", 0)),
            -int(population.get("unresolved_legacy_observations", 0)),
            identity,
        )
        candidates.append((rank, path, item))
    if not candidates:
        raise FileNotFoundError(f"no immutable NCAA reconciliation manifest for season {season}")
    _, path, item = max(candidates, key=lambda row: row[0])
    return path, item


def build_matrix(data_root: Path) -> dict[str, Any]:
    """Build tiered season/domain coverage without promoting candidate NCAA IDs."""
    data_root = data_root.resolve()
    event_path = data_root / "manifests/preliminary_event_chronology/sha256" / EVENT_RUN / "run_manifest.json"
    event = json.loads(event_path.read_text(encoding="utf-8"))
    target_counts = event["population"]["target_counts_by_season"]
    discoveries: dict[int, tuple[Path, dict[str, Any]]] = {}
    reconciliations: dict[int, tuple[Path, dict[str, Any]]] = {}
    for season in DISCOVERY_SEASONS:
        try:
            discoveries[season] = select_strongest_discovery(data_root, season)
        except FileNotFoundError:
            # Missing seasons are explicit NOT_STARTED rows below; partial
            # availability in one season never discards another season.
            continue
        try:
            reconciliations[season] = select_strongest_reconciliation(data_root, season)
        except FileNotFoundError:
            pass
    rows: list[dict[str, Any]] = []
    for season in DISCOVERY_SEASONS:
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
            failure_count = int(item["team_failure_count"])
            remaining_count = len(item["remaining_queue"])
            graph_exhausted = item["state"] == "COMPLETE_GRAPH_EXHAUSTED" and remaining_count == 0
            capture_complete = graph_exhausted and failure_count == 0
            if capture_complete:
                coverage_state = "COMPLETE_GRAPH_EXHAUSTED_CAPTURE_COMPLETE"
                missingness = "Graph exhausted with no unresolved team-page capture failures."
            elif graph_exhausted:
                coverage_state = "GRAPH_EXHAUSTED_WITH_QUARANTINED_FAILURES"
                missingness = (
                    f"Graph queue exhausted, but {failure_count} discovered team-season pages failed acquisition; "
                    "failed pages are quarantined and contest coverage is partial."
                )
            else:
                coverage_state = "PARTIAL_GRAPH_WITH_REMAINING_QUEUE"
                missingness = (
                    f"Partial source graph; {remaining_count} team-season IDs remain queued and "
                    f"{failure_count} page failures are preserved."
                )
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
                "legacy_schedule_records": int(item.get("legacy_schedule_record_count", 0)),
                "team_failure_count": failure_count,
                "remaining_queue": remaining_count,
                "missingness": missingness,
                "reconciliation_quality": "SOURCE_IDS_DISCOVERED_CANONICAL_GAME_TEAM_RECONCILIATION_PENDING",
                "capture_identity": item["discovery_identity"],
                "provenance_identity": sha256_file(path),
                "known_at_pit_eligibility": "CANDIDATE_ONLY_NOT_ADMITTED",
                "eligibility_tiers": [],
                "source_discovery_state": item["state"],
                "coverage_state": coverage_state,
            })
            reconciliation = reconciliations.get(season)
            if reconciliation:
                reconciliation_path, reconciliation_item = reconciliation
                core = reconciliation_item["identity_core"]
                population = core["population"]
                unresolved_reasons = reconciliation_item.get("unresolved_reason_counts", {})
                unresolved_legacy_reasons = reconciliation_item.get("unresolved_legacy_reason_counts", {})
                resolved = int(population["reconciled_contests"])
                unresolved = int(population["unresolved_contests"])
                legacy_resolved = int(population.get("reconciled_legacy_games", 0))
                legacy_unresolved = int(population.get("unresolved_legacy_observations", 0))
                parse_failures = int(population["page_parse_failures"])
                rows.append({
                    "season": season,
                    "season_type": "REGULAR_AND_POSTSEASON_COMBINED",
                    "source": "NCAA_OFFICIAL_STATS_PLUS_CANONICAL_OUTCOME_REFERENCE",
                    "endpoint": "TEAM_SEASON_SCHEDULE_TO_CANONICAL_GAME_RECONCILIATION",
                    "domain": "CANONICAL_CONTEST_RECONCILIATION",
                    "grain": "NCAA_CONTEST_OR_RECIPROCAL_LEGACY_SCHEDULE_PAIR_TO_CANONICAL_GAME",
                    "schema_version": reconciliation_item["schema_version"],
                    "canonical_games": resolved + legacy_resolved,
                    "canonical_teams": int(population["reconciled_team_seasons"]),
                    "discovered_contest_ids": int(population["discovered_contests"]),
                    "captured_team_pages": int(population["captured_team_pages"]),
                    "parsed_team_pages": int(population["parsed_team_pages"]),
                    "page_parse_failures": parse_failures,
                    "scored_schedule_observations": int(population["scored_schedule_observations"]),
                    "reconciled_contests": resolved,
                    "unresolved_contests": unresolved,
                    "legacy_schedule_observations": int(population.get("legacy_schedule_observations", 0)),
                    "reconciled_legacy_games": legacy_resolved,
                    "unresolved_legacy_observations": legacy_unresolved,
                    "unresolved_reason_counts": unresolved_reasons,
                    "unresolved_legacy_reason_counts": unresolved_legacy_reasons,
                    "missingness": (
                        f"{unresolved} discovered contests and {legacy_unresolved} legacy schedule observations remain unresolved; {parse_failures} captured "
                        "team-season pages failed deterministic parsing; all reasons remain explicit."
                    ),
                    "reconciliation_quality": "TWO_SIDED_EXACT_PARTICIPANTS_DATE_SCORE_CONTEXT_WITH_RECIPROCAL_LEGACY_TEAM_LINKS_NO_NAME_ONLY_PROMOTION_NO_CONTEST_ID_FABRICATION",
                    "capture_identity": core["inputs"]["discovery_manifest"]["sha256"],
                    "reconciliation_identity": reconciliation_item["dataset_identity"],
                    "provenance_identity": sha256_file(reconciliation_path),
                    "known_at_pit_eligibility": "CANDIDATE_ONLY_NOT_ADMITTED",
                    "eligibility_tiers": [],
                    "authority": reconciliation_item["authority"],
                    "coverage_state": "PARTIAL_RECONCILIATION_WITH_EXPLICIT_UNRESOLVED_REMAINDER",
                })
                acquisition_rollup = build_official_acquisition_rollup(
                    data_root,
                    season,
                    reconciliation_item["dataset_identity"],
                )
                if acquisition_rollup:
                    rows.append(acquisition_rollup)
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
                "team_failure_count": None,
                "remaining_queue": None,
                "missingness": "Season discovery tranche not yet executed.",
                "reconciliation_quality": "NOT_STARTED",
                "capture_identity": None,
                "provenance_identity": None,
                "known_at_pit_eligibility": "NOT_EVALUATED",
                "eligibility_tiers": [],
                "source_discovery_state": "NOT_STARTED",
                "coverage_state": "NOT_STARTED",
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
    complete_discovery_seasons = sorted(
        season for season, (_, item) in discoveries.items()
        if item.get("state") == "COMPLETE_GRAPH_EXHAUSTED"
        and not item.get("remaining_queue")
        and int(item.get("team_failure_count", 0)) == 0
    )
    graph_exhausted_with_failures = sorted(
        season for season, (_, item) in discoveries.items()
        if item.get("state") == "COMPLETE_GRAPH_EXHAUSTED"
        and not item.get("remaining_queue")
        and int(item.get("team_failure_count", 0)) > 0
    )
    partial_discovery_seasons = sorted(
        season for season, (_, item) in discoveries.items()
        if item.get("state") != "COMPLETE_GRAPH_EXHAUSTED" or item.get("remaining_queue")
    )
    not_started_discovery_seasons = sorted(set(DISCOVERY_SEASONS) - set(discoveries))
    reconciled_seasons = sorted(reconciliations)
    payload = {
        "schema_version": "1.4.0",
        "artifact_type": "HISTORICAL_SPINE_COVERAGE_AND_ELIGIBILITY_MATRIX",
        "classification": "MIXED_DOMAIN_TIERED_ELIGIBILITY",
        "rows": rows,
        "row_count": len(rows),
        "seasons": list(DISCOVERY_SEASONS),
        "spine_rule": "Outcomes, schedules, canonical identity, and known-at correctness are the spine; incomplete attached domains do not discard an otherwise useful season.",
        "discovery_summary": {
            "capture_complete_seasons": complete_discovery_seasons,
            "graph_exhausted_with_quarantined_failures": graph_exhausted_with_failures,
            "partial_graph_seasons": partial_discovery_seasons,
            "not_started_seasons": not_started_discovery_seasons,
            "reconciled_seasons": reconciled_seasons,
        },
        "negative_findings": [
            f"NCAA official contest discovery is capture-complete only for seasons {complete_discovery_seasons}.",
            f"NCAA discovery exhausted its graph but retained acquisition failures for seasons {graph_exhausted_with_failures}.",
            f"NCAA discovery remains bounded/partial for seasons {partial_discovery_seasons}.",
            f"NCAA discovery has not started for seasons {not_started_discovery_seasons}.",
            f"NCAA-to-canonical contest reconciliation artifacts are present only for seasons {reconciled_seasons}; every unresolved contest remains candidate-only.",
            "Validated official gamebook-equivalent acquisition rows remain partial, endpoint-specific candidate evidence and do not establish population completeness.",
            "No NCAA gamebook row currently has preliminary-training, protected, champion, or production authority.",
        ],
    }
    payload["matrix_identity"] = hashlib.sha256(canonical_json(payload)).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    payload = build_matrix(data_root)
    output = data_root / "manifests/historical_spine_coverage/sha256" / payload["matrix_identity"] / "coverage_matrix.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(payload) + b"\n")
    print(json.dumps({"result": "PASS", "matrix_identity": payload["matrix_identity"], "rows": len(payload["rows"]), "path": str(output), "sha256": sha256_file(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
