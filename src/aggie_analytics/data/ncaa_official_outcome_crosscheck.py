from __future__ import annotations

from collections import Counter
import hashlib
import html
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _identity_core(value: Mapping[str, Any], identity_field: str) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key not in {identity_field, "issued_at_utc", "credentials_logged_or_persisted"}
    }


def _write_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable cross-check collision: {path}")
        return
    temporary = path.with_name(f".tmp-{os.getpid()}-{hashlib.sha256(payload).hexdigest()[:8]}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(dict(row)) + b"\n" for row in rows)


def _normalized_team_label(value: object) -> str:
    return " ".join(html.unescape(str(value)).strip().casefold().split())


def _validated_acquisition_manifests(
    data_root: Path, season: int, reconciliation_identity: str
) -> list[tuple[Path, dict[str, Any], Path, dict[str, Any]]]:
    root = data_root / "manifests/acquisition/BAT-554-NCAA-OFFICIAL-BOUNDED-V1/sha256"
    selected: list[tuple[Path, dict[str, Any], Path, dict[str, Any]]] = []
    for manifest_path in sorted(root.glob("*/ncaa_official_gamebook_acquisition_manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        selection = manifest.get("selection_evidence", {})
        if (
            manifest.get("artifact_type") != "NCAA_OFFICIAL_GAMEBOOK_ACQUISITION_MANIFEST"
            or int(selection.get("season", -1)) != season
            or str(selection.get("dataset_identity", "")) != reconciliation_identity
        ):
            continue
        identity = str(manifest.get("acquisition_identity", ""))
        if identity != manifest_path.parent.name:
            raise ValueError(f"acquisition identity/path mismatch: {manifest_path}")
        if stable_hash(_identity_core(manifest, "acquisition_identity")) != identity:
            raise ValueError(f"acquisition content identity mismatch: {manifest_path}")
        manifest_sha = sha256_file(manifest_path)
        validation_root = (
            data_root
            / "validation/POST-SUBTASK-197/ncaa-official-gamebooks"
            / identity
            / "runs"
        )
        passing: list[tuple[tuple[int, int, str, str], Path, dict[str, Any]]] = []
        for validation_path in sorted(validation_root.glob("*/report.json")):
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            validation_identity = str(validation.get("validation_identity", ""))
            validation_core = {
                key: value for key, value in validation.items() if key != "validation_identity"
            }
            if validation_identity != validation_path.parent.name or stable_hash(validation_core) != validation_identity:
                raise ValueError(f"validation identity mismatch: {validation_path}")
            if (
                validation.get("result") == "PASS"
                and str(validation.get("acquisition_identity")) == identity
                and str(validation.get("manifest_sha256")) == manifest_sha
            ):
                rank = (
                    int(validation.get("check_count", 0)),
                    int(validation.get("mutation_control_count", 0)),
                    str(validation.get("validated_at_utc", "")),
                    validation_identity,
                )
                passing.append((rank, validation_path, validation))
        if not passing:
            continue
        _, validation_path, validation = max(passing, key=lambda row: row[0])
        selected.append((manifest_path, manifest, validation_path, validation))
    return selected


def _acquisition_rollup(
    data_root: Path, season: int, reconciliation_identity: str
) -> tuple[str, dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]]]:
    manifests = _validated_acquisition_manifests(data_root, season, reconciliation_identity)
    if not manifests:
        raise ValueError(f"no validated acquisition manifests for season {season}")
    evidence: list[dict[str, Any]] = []
    best: dict[tuple[str, str], tuple[tuple[int, int, int, int, str], dict[str, Any]]] = {}
    for manifest_path, manifest, validation_path, validation in manifests:
        evidence.append(
            {
                "acquisition_identity": manifest["acquisition_identity"],
                "manifest_sha256": sha256_file(manifest_path),
                "validation_identity": validation["validation_identity"],
                "validation_report_sha256": sha256_file(validation_path),
                "check_count": int(validation["check_count"]),
                "mutation_control_count": int(validation["mutation_control_count"]),
            }
        )
        for request in manifest["captures"]:
            key = (str(request["contest_id"]), str(request["endpoint_id"]))
            parsed = [row for row in request.get("normalization", []) if row.get("state") == "PARSED_CANDIDATE"]
            rank = (
                int(request.get("state") == "CAPTURED"),
                len(parsed),
                sum(int(row.get("row_count", 0)) for row in parsed),
                int(request.get("raw_bytes", 0)),
                str(request.get("request_identity_sha256", "")),
            )
            if key not in best or rank > best[key][0]:
                best[key] = (rank, request)
    selected = {key: best[key][1] for key in sorted(best)}
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
            for row in selected.values()
        ],
    }
    return stable_hash(rollup_core), selected, evidence


def _verified_linescore_payload(data_root: Path, request: Mapping[str, Any]) -> dict[str, Any] | None:
    if request.get("state") != "CAPTURED":
        return None
    candidates = [
        row
        for row in request.get("normalization", [])
        if row.get("domain") == "linescore_game_info" and row.get("state") == "PARSED_CANDIDATE"
    ]
    if len(candidates) != 1:
        return None
    evidence = candidates[0]
    relative = Path(str(evidence["payload_relative_path"]))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("normalized payload path escapes external data root")
    path = data_root / relative
    if not path.is_file() or sha256_file(path) != evidence["payload_sha256"]:
        raise ValueError(f"normalized payload hash mismatch: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    identity = str(evidence["normalization_identity"])
    core = {key: value for key, value in payload.items() if key != "normalization_identity"}
    if (
        payload.get("normalization_identity") != identity
        or path.parent.name != identity
        or stable_hash(core) != identity
        or payload.get("contest_id") != str(request["contest_id"])
        or payload.get("endpoint_id") != "box_score"
        or payload.get("domain") != "linescore_game_info"
        or payload.get("canonical_identity_promoted") is not False
        or payload.get("historical_pit_eligible") is not False
    ):
        raise ValueError(f"normalized payload identity or authority mismatch: {path}")
    return {"payload": payload, "evidence": evidence}


def compare_mapping(
    mapping: Mapping[str, Any],
    payload_bundle: Mapping[str, Any] | None,
    team_mappings: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    base = {
        "season": int(mapping["season"]),
        "season_type": str(mapping["season_type"]),
        "canonical_game_id": str(mapping["canonical_game_id"]),
        "ncaa_contest_id": str(mapping["ncaa_contest_id"]),
        "canonical_home_team_id": str(mapping["canonical_home_team_id"]),
        "canonical_away_team_id": str(mapping["canonical_away_team_id"]),
        "canonical_home_points": int(mapping["canonical_home_points"]),
        "canonical_away_points": int(mapping["canonical_away_points"]),
        "mapping_method": str(mapping["mapping_method"]),
        "name_only_promotion": bool(mapping["name_only_promotion"]),
        "historical_pit_eligible": False,
        "training_eligible": False,
        "protected_evaluation_eligible": False,
        "production_eligible": False,
    }
    if payload_bundle is None:
        return {**base, "status": "MISSING_OFFICIAL_LINESCORE", "official_home_points": None, "official_away_points": None}
    payload = payload_bundle["payload"]
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        return {**base, "status": "INVALID_OFFICIAL_LINESCORE", "official_home_points": None, "official_away_points": None}
    parsed: dict[str, tuple[int, str]] = {}
    valid = True
    for side in ("away", "home"):
        side_rows = [row for row in records if row.get("home_away") == side]
        finals = {row.get("final") for row in side_rows}
        teams = {str(row.get("team", "")).strip() for row in side_rows}
        points = [row.get("points") for row in side_rows]
        if (
            len(finals) != 1
            or len(teams) != 1
            or "" in teams
            or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in finals | set(points))
        ):
            valid = False
            continue
        final = next(iter(finals))
        if sum(points) != final:
            valid = False
            continue
        parsed[side] = (final, next(iter(teams)))
    if not valid or set(parsed) != {"away", "home"}:
        return {**base, "status": "INVALID_OFFICIAL_LINESCORE", "official_home_points": None, "official_away_points": None}
    away_points, away_label = parsed["away"]
    home_points, home_label = parsed["home"]
    source_team_season_ids = {
        value for value in str(mapping.get("source_team_season_ids", "")).split(";") if value
    }
    participant_mappings = [team_mappings[value] for value in sorted(source_team_season_ids) if value in team_mappings]
    label_to_team_ids: dict[str, set[str]] = {}
    valid_identity = len(source_team_season_ids) == 2 and len(participant_mappings) == 2
    for participant in participant_mappings:
        label = _normalized_team_label(participant.get("source_team_name"))
        canonical_team_id = str(participant.get("canonical_team_id", ""))
        if (
            not label
            or not canonical_team_id
            or participant.get("name_only_promotion") is not False
            or participant.get("mapping_method") != "CONSISTENT_ACCEPTED_TWO_SIDED_CONTEST_CONTEXT"
        ):
            valid_identity = False
        label_to_team_ids.setdefault(label, set()).add(canonical_team_id)
    resolved: dict[str, str] = {}
    for side, label in (("away", away_label), ("home", home_label)):
        candidates = label_to_team_ids.get(_normalized_team_label(label), set())
        if len(candidates) != 1:
            valid_identity = False
        else:
            resolved[side] = next(iter(candidates))
    canonical_participants = {base["canonical_home_team_id"], base["canonical_away_team_id"]}
    if not valid_identity or set(resolved.values()) != canonical_participants:
        return {
            **base,
            "status": "INVALID_OFFICIAL_TEAM_IDENTITY",
            "official_home_points": None,
            "official_away_points": None,
            "source_reported_home_points": home_points,
            "source_reported_away_points": away_points,
            "source_reported_home_team_label": home_label,
            "source_reported_away_team_label": away_label,
        }
    points_by_team = {resolved["home"]: home_points, resolved["away"]: away_points}
    official_home_points = points_by_team[base["canonical_home_team_id"]]
    official_away_points = points_by_team[base["canonical_away_team_id"]]
    side_alignment = (
        "DIRECT"
        if resolved["home"] == base["canonical_home_team_id"]
        else "REVERSED_SOURCE_ORIENTATION"
    )
    status = (
        "AGREEMENT"
        if (official_home_points, official_away_points)
        == (base["canonical_home_points"], base["canonical_away_points"])
        else "CONFLICT_FINAL_SCORE"
    )
    return {
        **base,
        "status": status,
        "official_home_points": official_home_points,
        "official_away_points": official_away_points,
        "official_home_team_label": next(
            label for side, label in (("home", home_label), ("away", away_label))
            if resolved[side] == base["canonical_home_team_id"]
        ),
        "official_away_team_label": next(
            label for side, label in (("home", home_label), ("away", away_label))
            if resolved[side] == base["canonical_away_team_id"]
        ),
        "source_reported_home_points": home_points,
        "source_reported_away_points": away_points,
        "source_reported_home_team_label": home_label,
        "source_reported_away_team_label": away_label,
        "source_side_alignment": side_alignment,
        "team_identity_resolution_method": "EXACT_CONTEXT_RECONCILED_SOURCE_TEAM_LABEL",
        "normalization_identity": payload["normalization_identity"],
        "normalized_payload_sha256": payload_bundle["evidence"]["payload_sha256"],
        "source_raw_sha256": payload["source_raw_sha256"],
        "source_uri": payload["source_uri"],
    }


def _validate_authority(contract: Mapping[str, Any]) -> None:
    authority = contract["authority"]
    if authority.get("official_postgame_crosscheck_candidate") is not True:
        raise ValueError("official postgame candidate authority is not enabled")
    if any(value is not False for key, value in authority.items() if key != "official_postgame_crosscheck_candidate"):
        raise ValueError("cross-check authority is open beyond candidate postgame evidence")


def build_crosscheck(
    *, data_root: Path, output_data_root: Path, repo_root: Path, contract_path: Path, issued_at_utc: str
) -> dict[str, Any]:
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    _validate_authority(contract)
    required_method = contract["identity"]["required_mapping_method"]
    rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for season_config in contract["source_seasons"]:
        season = int(season_config["season"])
        identity = season_config["reconciliation_dataset_identity"]
        reconciliation_path = data_root / "manifests/ncaa_contest_reconciliation/sha256" / identity / "run_manifest.json"
        if not reconciliation_path.is_file() or sha256_file(reconciliation_path) != season_config["reconciliation_manifest_sha256"]:
            raise ValueError(f"season {season} reconciliation manifest drift")
        reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
        core = reconciliation.get("identity_core", {})
        mappings = core.get("mapping_records", [])
        team_mapping_records = core.get("team_mapping_records", [])
        if (
            reconciliation.get("dataset_identity") != identity
            or stable_hash(core) != identity
            or int(core.get("season", -1)) != season
            or len(mappings) != int(season_config["expected_mapping_count"])
        ):
            raise ValueError(f"season {season} reconciliation identity or population drift")
        team_mappings = {
            str(row["source_team_season_id"]): row for row in team_mapping_records
        }
        if len(team_mappings) != len(team_mapping_records):
            raise ValueError(f"season {season} duplicate team-season mapping identity")
        if any(
            mapping.get("mapping_method") != required_method
            or mapping.get("name_only_promotion") is not False
            or mapping.get("historical_pit_eligible") is not False
            or mapping.get("training_eligible") is not False
            or mapping.get("protected_eligible") is not False
            for mapping in mappings
        ):
            raise ValueError(f"season {season} mapping authority or method drift")
        rollup_identity, requests, evidence = _acquisition_rollup(data_root, season, identity)
        if rollup_identity != season_config["expected_acquisition_rollup_identity"]:
            raise ValueError(f"season {season} acquisition rollup drift")
        linescore_requests = {
            contest_id: request
            for (contest_id, endpoint), request in requests.items()
            if endpoint == contract["score_rules"]["endpoint_id"]
            and any(
                item.get("domain") == contract["score_rules"]["domain"]
                and item.get("state") == "PARSED_CANDIDATE"
                for item in request.get("normalization", [])
            )
        }
        if len(linescore_requests) != int(season_config["expected_linescore_contest_count"]):
            raise ValueError(f"season {season} linescore population drift")
        for mapping in sorted(mappings, key=lambda row: str(row["ncaa_contest_id"])):
            request = linescore_requests.get(str(mapping["ncaa_contest_id"]))
            rows.append(
                compare_mapping(
                    mapping,
                    _verified_linescore_payload(data_root, request) if request else None,
                    team_mappings,
                )
            )
        sources.append(
            {
                "season": season,
                "reconciliation_dataset_identity": identity,
                "reconciliation_manifest_sha256": season_config["reconciliation_manifest_sha256"],
                "acquisition_rollup_identity": rollup_identity,
                "validated_acquisition_evidence_identity": stable_hash(evidence),
                "validated_acquisition_manifest_count": len(evidence),
                "mapping_count": len(mappings),
                "team_mapping_count": len(team_mapping_records),
                "team_mapping_record_sha256": stable_hash(team_mapping_records),
                "linescore_contest_count": len(linescore_requests),
            }
        )
    rows.sort(key=lambda row: (row["season"], row["ncaa_contest_id"], row["canonical_game_id"]))
    if len(rows) != int(contract["acceptance"]["expected_mapping_rows"]):
        raise ValueError("cross-check mapping population drift")
    comparisons_bytes = _jsonl_bytes(rows)
    exceptions = [row for row in rows if row["status"] != "AGREEMENT"]
    exceptions_bytes = _jsonl_bytes(exceptions)
    status_counts = dict(sorted(Counter(row["status"] for row in rows).items()))
    by_season: dict[str, dict[str, Any]] = {}
    for season in sorted({row["season"] for row in rows}):
        season_rows = [row for row in rows if row["season"] == season]
        by_season[str(season)] = {
            "mapping_rows": len(season_rows),
            "status_counts": dict(sorted(Counter(row["status"] for row in season_rows).items())),
            "valid_comparisons": sum(row["status"] in {"AGREEMENT", "CONFLICT_FINAL_SCORE"} for row in season_rows),
            "agreements": sum(row["status"] == "AGREEMENT" for row in season_rows),
            "conflicts": sum(row["status"] == "CONFLICT_FINAL_SCORE" for row in season_rows),
            "missing_or_invalid": sum(row["status"] in {"MISSING_OFFICIAL_LINESCORE", "INVALID_OFFICIAL_LINESCORE"} for row in season_rows),
        }
    module_path = Path(__file__).resolve()
    builder_path = repo_root / "tools/build_ncaa_official_outcome_crosscheck.py"
    identity_core = {
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "producer": {"module_sha256": sha256_file(module_path), "builder_sha256": sha256_file(builder_path)},
        "sources": sources,
        "comparison_record_sha256": hashlib.sha256(comparisons_bytes).hexdigest(),
        "exception_record_sha256": hashlib.sha256(exceptions_bytes).hexdigest(),
        "status_counts": status_counts,
        "classification": contract["classification"],
    }
    dataset_identity = stable_hash(identity_core)
    artifact_root = output_data_root / "quarantine/ncaa_official_outcome_crosscheck/sha256" / dataset_identity
    comparison_path = artifact_root / "comparisons.jsonl"
    exception_path = artifact_root / "exceptions.jsonl"
    _write_immutable(comparison_path, comparisons_bytes)
    _write_immutable(exception_path, exceptions_bytes)
    manifest = {
        "schema_version": contract["schema_version"],
        "artifact_type": "NCAA_OFFICIAL_OUTCOME_CROSSCHECK",
        "classification": contract["classification"],
        "dataset_identity": dataset_identity,
        "issued_at_utc": issued_at_utc,
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "identity_core": identity_core,
        "population": {"mapping_rows": len(rows), "status_counts": status_counts, "by_season": by_season},
        "payloads": [
            {"name": "comparisons.jsonl", "relative_path": comparison_path.relative_to(output_data_root).as_posix(), "rows": len(rows), "bytes": len(comparisons_bytes), "sha256": sha256_file(comparison_path)},
            {"name": "exceptions.jsonl", "relative_path": exception_path.relative_to(output_data_root).as_posix(), "rows": len(exceptions), "bytes": len(exceptions_bytes), "sha256": sha256_file(exception_path)},
        ],
        "authority": contract["authority"],
        "nonclaims": {
            "historical_population_ready": False,
            "historical_pit_admission": False,
            "training_or_protected_evaluation_admission": False,
            "production_or_champion_readiness": False,
            "tamu_lift_bas_or_aggie_excess": False,
        },
    }
    manifest_path = output_data_root / "manifests/ncaa_official_outcome_crosscheck/sha256" / dataset_identity / "run_manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("identity_core") != identity_core:
            raise ValueError("existing cross-check manifest identity core drift")
        manifest = existing
    else:
        _write_immutable(manifest_path, canonical_json_bytes(manifest) + b"\n")
    return {
        "dataset_identity": dataset_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "population": manifest["population"],
        "payloads": manifest["payloads"],
        "manifest": manifest,
    }
