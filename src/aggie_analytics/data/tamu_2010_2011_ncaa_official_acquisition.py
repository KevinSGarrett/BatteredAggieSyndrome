"""Bounded 2010-2011 Texas A&M NCAA official acquisition (candidate-only)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.adapters import AcquisitionFailure, AcquisitionRequest
from aggie_analytics.data.ncaa_contest_reconciliation import (
    canonical_json_bytes,
    normalize_team_name,
    sha256_file,
    stable_hash,
)


SCHEMA_VERSION = "aggie.data.tamu_2010_2011_ncaa_official_acquisition.v1"
CONTRACT_RELATIVE = "configs/tamu_2010_2011_ncaa_official_acquisition_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_2010_2011_ncaa_official_acquisition_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-TAMU-2010-2011-NCAA-OFFICIAL-ACQUISITION-001.json"
CONTRACT_ID = "BAT-571-TAMU-2010-2011-NCAA-OFFICIAL-ACQUISITION-V1"
PASS_CLASSIFICATION = "TAMU_2010_2011_NCAA_OFFICIAL_CANDIDATE_ONLY"
HONEST_NEGATIVE = "LEGACY_SCHEDULE_ONLY_NO_CONTEST_ENDPOINTS"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
AUBURN_SEEDS = frozenset({"136982", "16591"})
TAMU_SEEDS = {"2010": "137387", "2011": "137872"}
PHASE3_MATRIX_IDENTITY = "1e191204aea9c008e708f367fd36352298a3af8b129af6d0fb03b11247c3fffa"
PHASE3_GATE_IDENTITY = "6a88922c727a34772224ef176aebd4930815dde533893204cbca42402376da93"
NCAA_ENDPOINTS = (
    "box_score",
    "play_by_play",
    "drives",
    "team_stats",
    "individual_stats",
    "officials",
)
GATE_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "disposition",
    "phase3_identities",
    "tamu_seeds",
    "excluded_auburn_seeds",
    "bat_554_policy",
    "acquisition_identity",
    "discovery_identities",
    "counts",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "contest_ids_fabricated",
    "protected_lane",
)


class AuthorityViolation(ValueError):
    """Raised when the acquisition is asked to invent identity or reopen BAT-554."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _acquire_mod() -> Any:
    path = Path(__file__).resolve().parents[3] / "tools" / "acquire_ncaa_official_gamebooks.py"
    spec = importlib.util.spec_from_file_location("acquire_ncaa_official_gamebooks", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load acquire_ncaa_official_gamebooks.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expected_authority() -> dict[str, bool]:
    return {
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "name_only_promotion": False,
        "national_crawl": False,
        "id_range_sweep": False,
        "historical_known_at_from_capture_time": False,
        "historical_pit_admission": False,
        "preliminary_training_admission": False,
        "protected_training_admission": False,
        "protected_evaluation_admission": False,
        "protected_outcome_authority": False,
        "champion_or_production_promotion": False,
        "forecast_publication": False,
        "availability_claim": False,
        "tamu_specialization_lift_claims": False,
        "bas_or_aggie_excess_claims": False,
        "bat_554_reopen": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "completeness_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "pregame_availability_admitted": False,
        "protected_lane_opened": False,
        "protected_evaluation_admitted": False,
        "protected_outcome_authority": False,
        "protected_performance_claimed": False,
        "champion_or_production_promotion": False,
        "tamu_specialization_lift_claimed": False,
        "bas_or_aggie_excess_result_claimed": False,
        "trained_production_champion": False,
        "availability_claimed": False,
        "contest_ids_fabricated": False,
        "bat_554_reopened": False,
    }


def expected_admissions(disposition: str) -> dict[str, str]:
    return {
        "acquisition_admission": "CANDIDATE_ONLY",
        "disposition": disposition,
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
        "bat_554": "RELATES_ONLY_DO_NOT_REOPEN",
    }


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("TAMU 2010-2011 acquisition contract identity drift")
    if contract.get("bat_554_policy") != "RELATES_ONLY_DO_NOT_REOPEN":
        raise AuthorityViolation("BAT-554 reopen is forbidden")
    if contract.get("tamu_seeds") != TAMU_SEEDS:
        raise AuthorityViolation("TAMU seeds drifted from the pinned 137387/137872 pair")
    if set(contract.get("excluded_auburn_seeds") or []) != AUBURN_SEEDS:
        raise AuthorityViolation("Auburn exclusion set drifted")
    if set(contract["tamu_seeds"].values()) & AUBURN_SEEDS:
        raise AuthorityViolation("Auburn seed labeled as TAMU")
    for key, expected in expected_authority().items():
        if (contract.get("authority") or {}).get(key) is not expected:
            raise AuthorityViolation(f"contract authority {key} is not fail-closed")
    phase3 = contract.get("phase3") or {}
    if phase3.get("matrix_identity") != PHASE3_MATRIX_IDENTITY:
        raise AuthorityViolation("Phase 3 matrix identity drift")
    if phase3.get("gate_identity") != PHASE3_GATE_IDENTITY:
        raise AuthorityViolation("Phase 3 gate identity drift")
    return contract


def load_transport_contract(repo_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    reuse = contract["transport_reuse"]
    path = repo_root / reuse["contract_relative_path"]
    transport = load_json(path)
    if transport.get("jira_key") != reuse["national_jira_key"]:
        raise AuthorityViolation("BAT-554 national contract jira key drifted")
    if transport.get("run_id") != reuse["national_run_id"]:
        raise AuthorityViolation("BAT-554 national run identity drifted")
    seeds = (transport.get("discovery") or {}).get("seed_team_season_ids") or {}
    if str(seeds.get("2010")) != "136982" or str(seeds.get("2011")) != "16591":
        raise AuthorityViolation("BAT-554 Auburn seeds were mutated")
    if str(seeds.get("2010")) in TAMU_SEEDS.values() or str(seeds.get("2011")) in TAMU_SEEDS.values():
        raise AuthorityViolation("BAT-554 seeds were rewritten to TAMU")
    return transport


def runtime_inspect_contract(transport: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content_validation": transport["content_validation"],
        "discovery": transport["discovery"],
        "source": transport["source"],
        "transport": transport["transport"],
        "endpoints": transport["endpoints"],
    }


def verify_protected_registry(repo_root: Path, contract: Mapping[str, Any]) -> None:
    digest = sha256_file(repo_root / contract["protected_split_registry_relative_path"])
    if digest != contract["protected_split_registry_sha256"]:
        raise AuthorityViolation("PROTECTED_SPLIT_REGISTRY.csv hash drift; lane stays blocked")


def verify_phase3_population(data_root: Path, repo_root: Path, contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    gate = load_json(repo_root / contract["phase3"]["gate_relative_path"])
    if gate.get("gate_identity") != PHASE3_GATE_IDENTITY:
        raise AuthorityViolation("live Phase 3 gate identity drifted")
    if gate.get("matrix_identity") != PHASE3_MATRIX_IDENTITY:
        raise AuthorityViolation("live Phase 3 matrix identity drifted")
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("Phase 3 population load requires the optional data-engineering environment") from exc
    payload = data_root / contract["phase3"]["payload_relative_path"]
    if not payload.is_file():
        raise FileNotFoundError(f"Phase 3 matrix payload missing: {payload}")
    frame = polars.read_parquet(payload)
    rows = [
        dict(row)
        for row in frame.filter(polars.col("season").is_in([2010, 2011])).to_dicts()
    ]
    if len(rows) != 26:
        raise AuthorityViolation(f"Phase 3 2010-2011 population is {len(rows)}, expected 26")
    if any(row.get("contest_id") for row in rows):
        raise AuthorityViolation("Phase 3 population unexpectedly carries contest IDs")
    if any(row.get("name_only_promotion") for row in rows):
        raise AuthorityViolation("Phase 3 population silently promoted a name-only match")
    for row in rows:
        season = str(int(row["season"]))
        if str(row.get("ncaa_team_season_id")) != TAMU_SEEDS[season]:
            raise AuthorityViolation(f"Phase 3 row is not bound to TAMU seed {TAMU_SEEDS[season]}")
    return sorted(rows, key=lambda row: (int(row["season"]), str(row["game_date"]), str(row["opponent_name"])))


def _write_bytes_immutable(payload: bytes, path: Path, *, artifact: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable {artifact} collision: {path}")
        return
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def inspect_team_page(body: bytes, transport: Mapping[str, Any]) -> dict[str, Any]:
    return _acquire_mod().inspect_ncaa_team_page(body, contract=runtime_inspect_contract(transport))


def load_lake_html(data_root: Path, spec: Mapping[str, Any]) -> dict[str, Any]:
    path = data_root / spec["raw_relative_path"]
    if not path.is_file():
        raise FileNotFoundError(f"lake HTML missing for {spec['team_season_id']}: {path}")
    digest = sha256_file(path)
    if digest != spec["raw_sha256"]:
        raise AuthorityViolation(f"lake HTML hash drift for {spec['team_season_id']}: {digest}")
    return {
        "raw_relative_path": spec["raw_relative_path"],
        "raw_sha256": digest,
        "raw_bytes": path.stat().st_size,
        "body": path.read_bytes(),
        "source": "EXISTING_LAKE_HTML",
    }


def attempt_live_team_page(
    *,
    team_season_id: str,
    transport: Mapping[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    acquire = _acquire_mod()
    source_uri = f"https://{transport['source']['official_host']}/teams/{team_season_id}"
    acquire.validate_official_uri(source_uri)
    request = AcquisitionRequest(
        source_id=transport["source"]["capture_source_id"],
        dataset="ncaa_team_season_discovery",
        source_uri=source_uri,
        identity_components={
            "decision_unit": "POST-TASK-TAMU-2010-2011-NCAA-OFFICIAL-ACQUISITION-001",
            "team_season_id": team_season_id,
            "discovery_contract": "TAMU_DEDICATED_TEAM_PAGE_V1",
        },
        extension=".html",
    )
    try:
        response = acquire.DirectHTTPTransport(timeout_seconds=timeout_seconds)(request)
        if not 200 <= int(response.status_code) < 300:
            raise AcquisitionFailure("HTTP_STATUS", "live team page was not successful", status_code=response.status_code)
        profile = inspect_team_page(response.body, transport)
        return {
            "state": "LIVE_CAPTURED",
            "status_code": int(response.status_code),
            "raw_sha256": hashlib.sha256(response.body).hexdigest(),
            "raw_bytes": len(response.body),
            "body": response.body,
            "profile": profile,
            "source_uri": source_uri,
        }
    except AcquisitionFailure as error:
        return {
            "state": "LIVE_UNAVAILABLE",
            "condition": error.condition,
            "status_code": error.status_code,
            "source_uri": source_uri,
        }


def discovery_core(
    *,
    contract: Mapping[str, Any],
    season: int,
    spec: Mapping[str, Any],
    lake: Mapping[str, Any],
    profile: Mapping[str, Any],
    live: Mapping[str, Any] | None,
) -> dict[str, Any]:
    contest_ids = list(profile.get("contest_ids") or [])
    if any(not str(item).isdigit() for item in contest_ids):
        raise AuthorityViolation("non-numeric contest ID is treated as invented")
    records = list(profile.get("legacy_schedule_records") or [])
    if any(record.get("contest_id") for record in records):
        raise AuthorityViolation("legacy schedule row unexpectedly carries a contest ID")
    return {
        "schema_version": "1.0.0",
        "artifact_type": "TAMU_DEDICATED_TEAM_PAGE_DISCOVERY_MANIFEST",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": contract["classification"],
        "season": season,
        "seed_team_season_id": spec["team_season_id"],
        "team_season_id": spec["team_season_id"],
        "organization": "Texas A&M",
        "state": "DEDICATED_TAMU_SEED_NO_GRAPH_CRAWL",
        "link_schema": profile.get("link_schema"),
        "contest_ids": contest_ids,
        "contest_link_count": int(profile.get("contest_link_count") or 0),
        "legacy_schedule_record_count": int(profile.get("legacy_schedule_record_count") or len(records)),
        "legacy_schedule_records": records,
        "raw_relative_path": lake["raw_relative_path"],
        "raw_sha256": lake["raw_sha256"],
        "raw_bytes": lake["raw_bytes"],
        "prior_graph_discovery_identity": spec["prior_graph_discovery_identity"],
        "prior_capture_class": spec["prior_capture_class"],
        "first_class_required": bool(spec["first_class_required"]),
        "auburn_seeds_excluded": sorted(AUBURN_SEEDS),
        "bat_554_policy": contract["bat_554_policy"],
        "phase3_matrix_identity": PHASE3_MATRIX_IDENTITY,
        "phase3_gate_identity": PHASE3_GATE_IDENTITY,
        "authority": expected_authority(),
    }


def reconcile_target(phase3: Mapping[str, Any], ncaa_records: list[Mapping[str, Any]]) -> dict[str, Any]:
    date_hits = [row for row in ncaa_records if str(row.get("game_date") or "") == str(phase3["game_date"])]
    name_hits = [
        row
        for row in ncaa_records
        if normalize_team_name(str(row.get("opponent_display_name") or ""))
        == normalize_team_name(str(phase3.get("opponent_name") or ""))
    ]
    chosen = date_hits[0] if len(date_hits) == 1 else None
    if chosen is not None and chosen.get("contest_id"):
        raise AuthorityViolation("NCAA legacy row unexpectedly carries a contest ID")
    name_only = bool(name_hits) and chosen is None
    if name_only and phase3.get("name_only_promotion"):
        raise AuthorityViolation("name-only promotion is forbidden")
    return {
        "season": int(phase3["season"]),
        "game_date": phase3["game_date"],
        "opponent_name": phase3.get("opponent_name"),
        "phase3_reconciliation_state": phase3.get("reconciliation_state"),
        "phase3_ncaa_contest_exposure": phase3.get("ncaa_contest_exposure"),
        "ncaa_game_date": None if chosen is None else chosen.get("game_date"),
        "ncaa_opponent_display_name": None if chosen is None else chosen.get("opponent_display_name"),
        "ncaa_opponent_team_season_id": None if chosen is None else chosen.get("opponent_team_season_id"),
        "ncaa_source_row_sha256": None if chosen is None else chosen.get("source_row_sha256"),
        "contest_id": None,
        "name_only_promotion": False,
        "name_only_unpromoted": name_only,
        "endpoint_attempts": [],
    }


def decide_disposition(discoveries: Mapping[int, Mapping[str, Any]]) -> str:
    schemas = {int(season): row["link_schema"] for season, row in discoveries.items()}
    contest_ids = [item for row in discoveries.values() for item in row["contest_ids"]]
    if any(schemas.get(season) != "LEGACY_SCHEDULE_RESULT_ROW" for season in (2010, 2011)):
        if contest_ids:
            return "MODERN_CONTEST_LINKS_PRESENT"
        return "NON_LEGACY_SCHEMA_NO_CONTEST_ENDPOINTS"
    if contest_ids:
        return "LEGACY_AND_CONTEST_LINKS_PRESENT"
    return HONEST_NEGATIVE


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate})


def summarize(
    *,
    targets: list[Mapping[str, Any]],
    discoveries: Mapping[int, Mapping[str, Any]],
    disposition: str,
) -> dict[str, Any]:
    contests_2010 = list(discoveries[2010]["contest_ids"])
    contests_2011 = list(discoveries[2011]["contest_ids"])
    return {
        "phase3_targets": len(targets),
        "games_2010": sum(1 for row in targets if int(row["season"]) == 2010),
        "games_2011": sum(1 for row in targets if int(row["season"]) == 2011),
        "contest_ids_2010": len(contests_2010),
        "contest_ids_2011": len(contests_2011),
        "contest_ids_present": len(contests_2010) + len(contests_2011),
        "contest_ids_fabricated": 0,
        "name_only_promotions": sum(1 for row in targets if row.get("name_only_promotion")),
        "name_only_unpromoted": sum(1 for row in targets if row.get("name_only_unpromoted")),
        "endpoint_attempts": sum(len(row.get("endpoint_attempts") or []) for row in targets),
        "legacy_schedule_records_2010": discoveries[2010]["legacy_schedule_record_count"],
        "legacy_schedule_records_2011": discoveries[2011]["legacy_schedule_record_count"],
        "disposition": disposition,
    }


def acquisition_core(
    *,
    contract: Mapping[str, Any],
    discoveries: Mapping[int, Mapping[str, Any]],
    discovery_identities: Mapping[int, str],
    targets: list[Mapping[str, Any]],
    disposition: str,
) -> dict[str, Any]:
    counts = summarize(targets=targets, discoveries=discoveries, disposition=disposition)
    if counts["contest_ids_fabricated"] or any(row.get("contest_id") for row in targets):
        raise AuthorityViolation("invented contest IDs are forbidden")
    if counts["name_only_promotions"]:
        raise AuthorityViolation("name-only promotion is forbidden")
    if disposition == HONEST_NEGATIVE and counts["contest_ids_present"]:
        raise AuthorityViolation("honest-negative disposition cannot carry contest IDs")
    if counts["phase3_targets"] != 26:
        raise AuthorityViolation("not every Phase 3 2010-2011 target was reconciled")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_2010_2011_NCAA_OFFICIAL_ACQUISITION_MANIFEST",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": PASS_CLASSIFICATION,
        "contract_id": contract["contract_id"],
        "run_id": contract["run_id"],
        "bat_554_policy": contract["bat_554_policy"],
        "tamu_seeds": dict(TAMU_SEEDS),
        "excluded_auburn_seeds": sorted(AUBURN_SEEDS),
        "phase3_identities": {
            "matrix_identity": PHASE3_MATRIX_IDENTITY,
            "gate_identity": PHASE3_GATE_IDENTITY,
        },
        "discovery_identities": {
            "2010": discovery_identities[2010],
            "2011": discovery_identities[2011],
        },
        "disposition": disposition,
        "counts": counts,
        "targets": targets,
        "admissions": expected_admissions(disposition),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "contest_ids_fabricated": False,
        "protected_lane": PROTECTED_LANE,
    }


def expected_gate_document(
    *,
    contract: Mapping[str, Any],
    core: Mapping[str, Any],
    acquisition_identity: str,
) -> dict[str, Any]:
    if core["authority"] != expected_authority():
        raise AuthorityViolation("authority block is not fail-closed")
    if core["scientific_nonclaims"] != expected_scientific_nonclaims():
        raise AuthorityViolation("scientific nonclaims inverted")
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_2010_2011_NCAA_OFFICIAL_ACQUISITION_GATE",
        "result": f"PASS_{core['disposition']}",
        "classification": PASS_CLASSIFICATION,
        "contract_id": contract["contract_id"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "disposition": core["disposition"],
        "phase3_identities": core["phase3_identities"],
        "tamu_seeds": core["tamu_seeds"],
        "excluded_auburn_seeds": core["excluded_auburn_seeds"],
        "bat_554_policy": core["bat_554_policy"],
        "acquisition_identity": acquisition_identity,
        "discovery_identities": core["discovery_identities"],
        "counts": core["counts"],
        "admissions": core["admissions"],
        "authority": core["authority"],
        "scientific_nonclaims": core["scientific_nonclaims"],
        "contest_ids_fabricated": False,
        "protected_lane": PROTECTED_LANE,
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return gate


def _install_discovery(
    data_root: Path,
    contract: Mapping[str, Any],
    season: int,
    core: Mapping[str, Any],
    issued_at_utc: str,
) -> tuple[str, Path]:
    identity = stable_hash(core)
    path = (
        data_root
        / contract["payloads"]["acquisition_root"]
        / "discovery"
        / str(season)
        / "sha256"
        / identity
        / "ncaa_tamu_team_page_discovery_manifest.json"
    )
    manifest = {**core, "discovery_identity": identity, "issued_at_utc": issued_at_utc}
    _write_bytes_immutable(canonical_json_bytes(manifest) + b"\n", path, artifact=f"{season} dedicated discovery")
    return identity, path


def rebuild_expected(
    *,
    data_root: Path,
    repo_root: Path,
    allow_live: bool = False,
    live_timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    contract = load_contract(repo_root)
    transport = load_transport_contract(repo_root, contract)
    verify_protected_registry(repo_root, contract)
    phase3_rows = verify_phase3_population(data_root, repo_root, contract)
    discoveries: dict[int, dict[str, Any]] = {}
    discovery_identities: dict[int, str] = {}
    live_evidence: dict[int, dict[str, Any]] = {}
    for season, seed in ((2010, TAMU_SEEDS["2010"]), (2011, TAMU_SEEDS["2011"])):
        if seed in AUBURN_SEEDS:
            raise AuthorityViolation(f"refusing Auburn seed {seed}")
        spec = contract["lake_html"][str(season)]
        if spec["team_season_id"] != seed:
            raise AuthorityViolation("lake HTML seed drifted from TAMU pin")
        lake = load_lake_html(data_root, spec)
        profile = inspect_team_page(lake["body"], transport)
        live = None
        if allow_live:
            live = attempt_live_team_page(
                team_season_id=seed,
                transport=transport,
                timeout_seconds=live_timeout_seconds,
            )
            live_evidence[season] = {key: value for key, value in live.items() if key != "body"}
            if live.get("state") == "LIVE_CAPTURED":
                live_profile = live["profile"]
                if live_profile.get("contest_ids"):
                    profile = live_profile
        core = discovery_core(
            contract=contract,
            season=season,
            spec=spec,
            lake=lake,
            profile=profile,
            live=None,
        )
        discoveries[season] = core
        discovery_identities[season] = stable_hash(core)
    disposition = decide_disposition(discoveries)
    if disposition == HONEST_NEGATIVE:
        endpoint_attempts: list[dict[str, Any]] = []
    else:
        endpoint_attempts = []
        for season, core in discoveries.items():
            for contest_id in core["contest_ids"]:
                for endpoint_id in NCAA_ENDPOINTS:
                    endpoint_attempts.append(
                        {
                            "season": season,
                            "contest_id": contest_id,
                            "endpoint_id": endpoint_id,
                            "state": "NOT_EXECUTED_IN_REBUILD",
                        }
                    )
        if allow_live and (discoveries[2010]["contest_ids"] or discoveries[2011]["contest_ids"]):
            acquire = _acquire_mod()
            store = acquire.RawSnapshotStore(data_root)
            retrieved_at = datetime.now(timezone.utc)
            overlay = {
                **runtime_inspect_contract(transport),
                "decision_unit": contract["decision_unit"],
                "jira_key": contract["jira_key"],
                "classification": contract["classification"],
                "authority": transport["authority"],
                "source": transport["source"],
            }
            env_file = repo_root / ".env"
            runtime_root = data_root / "runtime" / "BAT-571"
            for season, core in discoveries.items():
                for contest_id in core["contest_ids"]:
                    contest = {
                        "contest_id": contest_id,
                        "season": season,
                        "canonical_game_id": None,
                        "identity_state": "OFFICIAL_CONTEST_ID_FROM_TAMU_TEAM_PAGE",
                    }
                    for endpoint in overlay["endpoints"]:
                        capture, _states = acquire.acquire_contest_endpoint(
                            store=store,
                            contest=contest,
                            endpoint=endpoint,
                            contract=overlay,
                            env_file=env_file,
                            runtime_root=runtime_root,
                            data_root=data_root,
                            retrieved_at=retrieved_at,
                            maximum_attempts=1,
                            selected_route_ids=list(overlay["transport"]["route_order"]),
                        )
                        endpoint_attempts.append(
                            {
                                "season": season,
                                "contest_id": contest_id,
                                "endpoint_id": capture.get("endpoint_id"),
                                "state": capture.get("state"),
                                "failure_condition": capture.get("failure_condition"),
                            }
                        )
    by_season_records = {
        season: list(discoveries[season]["legacy_schedule_records"]) for season in (2010, 2011)
    }
    targets = [reconcile_target(row, by_season_records[int(row["season"])]) for row in phase3_rows]
    if disposition == HONEST_NEGATIVE:
        for row in targets:
            row["endpoint_attempts"] = []
            row["contest_id"] = None
    elif endpoint_attempts:
        for row in targets:
            row["endpoint_attempts"] = [
                item
                for item in endpoint_attempts
                if item.get("contest_id") and item.get("contest_id") == row.get("contest_id")
            ]
    core = acquisition_core(
        contract=contract,
        discoveries=discoveries,
        discovery_identities=discovery_identities,
        targets=targets,
        disposition=disposition,
    )
    identity = stable_hash(core)
    return {
        "contract": contract,
        "transport": transport,
        "discoveries": discoveries,
        "discovery_identities": discovery_identities,
        "core": core,
        "acquisition_identity": identity,
        "gate": expected_gate_document(contract=contract, core=core, acquisition_identity=identity),
        "live_evidence": live_evidence,
        "phase3_rows": phase3_rows,
    }


def materialize(
    *,
    data_root: Path,
    repo_root: Path,
    issued_at_utc: str,
    allow_live: bool = True,
) -> dict[str, Any]:
    expected = rebuild_expected(
        data_root=data_root,
        repo_root=repo_root,
        allow_live=allow_live,
    )
    contract = expected["contract"]
    discovery_paths: dict[str, str] = {}
    for season, core in expected["discoveries"].items():
        _identity, path = _install_discovery(data_root, contract, season, core, issued_at_utc)
        discovery_paths[str(season)] = str(path)
    identity = expected["acquisition_identity"]
    manifest_path = (
        data_root
        / contract["payloads"]["acquisition_root"]
        / "sha256"
        / identity
        / "tamu_2010_2011_ncaa_official_acquisition_manifest.json"
    )
    manifest = {
        **expected["core"],
        "acquisition_identity": identity,
        "issued_at_utc": issued_at_utc,
        "live_evidence": expected["live_evidence"],
        "credentials_logged_or_persisted": False,
    }
    _write_bytes_immutable(canonical_json_bytes(manifest) + b"\n", manifest_path, artifact="acquisition manifest")
    normalized_root = data_root / contract["payloads"]["normalized_root"] / identity
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_2010_2011_NCAA_OFFICIAL_NORMALIZED_CANDIDATE",
        "acquisition_identity": identity,
        "disposition": expected["core"]["disposition"],
        "contest_ids_2010": expected["discoveries"][2010]["contest_ids"],
        "contest_ids_2011": expected["discoveries"][2011]["contest_ids"],
        "targets": expected["core"]["targets"],
        "historical_known_at_established": False,
        "protected_lane": PROTECTED_LANE,
    }
    normalized_path = normalized_root / "reconciled_targets.json"
    _write_bytes_immutable(canonical_json_bytes(normalized) + b"\n", normalized_path, artifact="normalized targets")
    gate = dict(expected["gate"])
    gate["issued_at_utc"] = issued_at_utc
    gate["payload"] = {
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "normalized": str(normalized_path),
        "normalized_sha256": sha256_file(normalized_path),
        "discovery": discovery_paths,
    }
    write_json(repo_root / GATE_RELATIVE, gate)
    evidence = _evidence_packet(repo_root, gate, expected)
    write_json(repo_root / EVIDENCE_RELATIVE, evidence)
    return {
        "gate_path": str(repo_root / GATE_RELATIVE),
        "gate_identity": gate["gate_identity"],
        "acquisition_identity": identity,
        "disposition": expected["core"]["disposition"],
        "counts": expected["core"]["counts"],
        "payload": gate["payload"],
    }


def _evidence_packet(repo_root: Path, gate: Mapping[str, Any], expected: Mapping[str, Any]) -> dict[str, Any]:
    outputs = []
    for relative in (
        GATE_RELATIVE,
        CONTRACT_RELATIVE,
        "src/aggie_analytics/data/tamu_2010_2011_ncaa_official_acquisition.py",
        "tools/build_tamu_2010_2011_ncaa_official_acquisition.py",
        "tools/validate_tamu_2010_2011_ncaa_official_acquisition.py",
        "tests/test_tamu_2010_2011_ncaa_official_acquisition.py",
    ):
        path = repo_root / relative
        if path.is_file():
            outputs.append(
                {
                    "path": relative.replace("\\", "/"),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return {
        "schema_version": "2.1.0",
        "evidence_manifest_type": "jira_issue_completion_evidence",
        "jira_key": "BAT-571",
        "local_issue_id": "POST-TASK-TAMU-2010-2011-NCAA-OFFICIAL-ACQUISITION-001",
        "parent_jira_key": "BAT-523",
        "related_jira_keys": ["BAT-570", "BAT-523", "BAT-429", "BAT-554"],
        "new_issue_decision": "CREATE",
        "workflow_state": "IN_PROGRESS",
        "evidence_state": "VERIFIED",
        "issue_complete": True,
        "acquisition_gaps_remain": gate["disposition"] == HONEST_NEGATIVE,
        "completeness_claimed": False,
        "contest_ids_fabricated": False,
        "observable_outcome": (
            "Cycle #7 Phase 4 acquired dedicated 2010-2011 Texas A&M NCAA official team-page evidence "
            "for seeds 137387 and 137872, reconciled all 26 Phase 3 scheduled games, and did not invent "
            f"contest IDs. Disposition {gate['disposition']}. BAT-554 remains relates-only. "
            "Protected lane stays RETAIN_PROTECTED_LANE_BLOCKED. Candidate-only."
        ),
        "outputs": outputs,
        "gate_identity": gate["gate_identity"],
        "acquisition_identity": gate["acquisition_identity"],
        "disposition": gate["disposition"],
        "counts": gate["counts"],
        "phase3_identities": gate["phase3_identities"],
        "admissions": gate["admissions"],
        "protected_nonclaims": expected["core"]["scientific_nonclaims"],
    }


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    expected = dict(expected) if expected is not None else rebuild_expected(
        data_root=data_root,
        repo_root=repo_root,
        allow_live=False,
    )
    rebuilt = expected_gate_document(
        contract=expected["contract"],
        core=expected["core"],
        acquisition_identity=expected["acquisition_identity"],
    )
    live_artifact = gate is None
    if live_artifact:
        gate = load_json(repo_root / GATE_RELATIVE)
    observed = {key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate}
    desired = {key: rebuilt[key] for key in GATE_IDENTITY_FIELDS}
    if observed != desired:
        raise AuthorityViolation("acquisition gate drifted from rebuilt identity-bound document")
    if gate.get("gate_identity") != compute_gate_identity(gate):
        raise AuthorityViolation("forged terminal state after rehash")
    if gate.get("contest_ids_fabricated") is not False:
        raise AuthorityViolation("contest IDs were fabricated")
    if gate.get("counts", {}).get("contest_ids_present") and gate.get("disposition") == HONEST_NEGATIVE:
        raise AuthorityViolation("honest-negative gate reports contest IDs")
    if gate.get("scientific_nonclaims", {}).get("contest_ids_fabricated"):
        raise AuthorityViolation("scientific nonclaim inverted")
    if gate.get("scientific_nonclaims", {}).get("bat_554_reopened"):
        raise AuthorityViolation("BAT-554 was reopened")
    if gate.get("authority", {}).get("bat_554_reopen"):
        raise AuthorityViolation("BAT-554 reopen authority was granted")
    if gate.get("authority", {}).get("protected_outcome_authority"):
        raise AuthorityViolation("protected outcome authority is not granted")
    if gate.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("capture time is not historical known-at")
    if gate.get("authority", {}).get("completeness_claim"):
        raise AuthorityViolation("completeness was claimed")
    if gate.get("admissions", {}).get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane must remain blocked")
    if set(map(str, (gate.get("tamu_seeds") or {}).values())) & AUBURN_SEEDS:
        raise AuthorityViolation("Auburn seed treated as TAMU")
    if str((gate.get("tamu_seeds") or {}).get("2010")) != "137387":
        raise AuthorityViolation("2010 TAMU seed drifted")
    if str((gate.get("tamu_seeds") or {}).get("2011")) != "137872":
        raise AuthorityViolation("2011 TAMU seed drifted")
    if require_rebuild and expected.get("acquisition_identity") != rebuilt["acquisition_identity"]:
        raise AuthorityViolation("acquisition identity rebuild mismatch")
    load_transport_contract(repo_root, expected["contract"])
    return {
        "result": "PASS",
        "gate_identity": rebuilt["gate_identity"],
        "acquisition_identity": rebuilt["acquisition_identity"],
        "disposition": rebuilt["disposition"],
    }
