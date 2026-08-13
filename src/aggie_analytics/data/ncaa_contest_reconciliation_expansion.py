from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .historical_game_outcome_spine import canonical_json_bytes
from .ncaa_contest_reconciliation import (
    _alias_index,
    _candidate_games,
    _outcomes,
    parse_team_page,
    reconcile,
    sha256_file,
    stable_hash,
)


def _write_json_immutable(value: Mapping[str, Any], path: Path) -> str:
    payload = canonical_json_bytes(value) + b"\n"
    identity = hashlib.sha256(payload).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable reconciliation evidence collision: {path}")
        return identity
    temporary = path.with_name(f".tmp-{os.getpid()}-{identity[:8]}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return identity


def _duplicate_contest_alias_groups(
    *, data_root: Path, discovery: Mapping[str, Any], registry_path: Path, outcome_path: Path
) -> list[dict[str, Any]]:
    season = int(discovery["season"])
    aliases = _alias_index(registry_path, season)
    outcomes = _outcomes(outcome_path, season)
    outcome_by_id = {row["target_game_id"]: row for row in outcomes}
    observations: list[dict[str, Any]] = []
    for capture in sorted(discovery["captures"], key=lambda row: row["team_season_id"]):
        raw_path = data_root / capture["raw_relative_path"]
        if sha256_file(raw_path) != capture["raw_sha256"]:
            raise ValueError("discovery capture drift during duplicate-contest preflight")
        _, rows = parse_team_page(
            raw_path.read_text(encoding="utf-8", errors="replace"),
            team_season_id=capture["team_season_id"],
            raw_sha256=capture["raw_sha256"],
        )
        observations.extend(rows)
    by_contest: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        candidates, source_id, opponent_id = _candidate_games(
            observation, aliases, outcomes, maximum_date_delta=1
        )
        by_contest[observation["contest_id"]].append(
            {
                **observation,
                "candidates": candidates,
                "source_id": source_id,
                "opponent_id": opponent_id,
            }
        )
    candidate_mappings: list[tuple[str, str]] = []
    for contest_id in sorted((str(value) for value in discovery["discovered_contest_ids"]), key=int):
        rows = by_contest.get(contest_id, [])
        candidates = sorted({candidate for row in rows for candidate in row["candidates"]})
        matched = [row for row in rows if len(row["candidates"]) == 1]
        pages = {row["source_team_season_id"] for row in matched}
        if len(candidates) != 1 or len(matched) < 2 or len(pages) < 2:
            continue
        game = outcome_by_id[candidates[0]]
        owner_ids = {row["source_id"] for row in matched}
        if owner_ids == {game["home_team_id"], game["away_team_id"]}:
            candidate_mappings.append((contest_id, candidates[0]))
    by_game: dict[str, list[str]] = defaultdict(list)
    for contest_id, game_id in candidate_mappings:
        by_game[game_id].append(contest_id)
    return [
        {
            "canonical_game_id": game_id,
            "ncaa_contest_ids": sorted(contest_ids, key=int),
            "contest_count": len(contest_ids),
            "disposition": "QUARANTINE_ALL_SOURCE_CONTEST_ALIASES_NO_ARBITRARY_WINNER",
            "reason": "MULTIPLE_NCAA_CONTEST_IDS_SAME_EXACT_CANONICAL_GAME",
            "canonical_game_evidence": outcome_by_id[game_id],
        }
        for game_id, contest_ids in sorted(by_game.items())
        if len(contest_ids) > 1
    ]


def build_resolved_contract(
    *,
    base_contract: Mapping[str, Any],
    policy: Mapping[str, Any],
    season: int,
    discovery_relative_path: str,
    discovery_sha256: str,
    discovery_identity: str,
    wrapper_identities: Mapping[str, str],
) -> dict[str, Any]:
    if not policy["admitted_season_min"] <= season <= policy["admitted_season_max"]:
        raise ValueError("season is outside the admitted reconciliation expansion interval")
    resolved = deepcopy(dict(base_contract))
    adapter = policy["outcome_adapter"]
    registry = policy["canonical_registry"]
    resolved.update(
        {
            "schema_version": "2.0.0",
            "contract_id": f"BAT-554-NCAA-CONTEST-RECONCILIATION-{season}-RESOLVED-V2",
            "decision_unit": policy["decision_unit"],
            "jira_key": policy["jira_key"],
        }
    )
    resolved["source_contract"] = {
        "season": season,
        "discovery_manifest": discovery_relative_path,
        "discovery_manifest_sha256": discovery_sha256,
        "canonical_registry": registry["relative_path"],
        "canonical_registry_sha256": registry["sha256"],
        "outcome_targets": adapter["payload"],
        "outcome_targets_sha256": adapter["payload_sha256"],
    }
    resolved["resolution_evidence"] = {
        "policy_id": policy["policy_id"],
        "base_contract_sha256": policy["base_contract"]["sha256"],
        "discovery_identity": discovery_identity,
        "outcome_adapter_dataset_identity": adapter["dataset_identity"],
        "outcome_adapter_manifest_sha256": adapter["manifest_sha256"],
        **dict(wrapper_identities),
    }
    resolved["authority"] = deepcopy(base_contract["authority"])
    resolved["authority"]["historical_pit_eligible"] = False
    resolved["authority"]["training_eligible"] = False
    resolved["authority"]["protected_evaluation_eligible"] = False
    resolved["authority"]["production_eligible"] = False
    return resolved


def resolve_and_reconcile(
    *,
    input_data_root: Path,
    output_data_root: Path,
    repo_root: Path,
    policy_path: Path,
    discovery_manifest_path: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    if input_data_root.resolve() != output_data_root.resolve():
        raise ValueError("resolved reconciliation contracts and views require one external data root")
    policy_bytes = policy_path.read_bytes()
    policy = json.loads(policy_bytes)
    authority = policy["authority"]
    if authority["resolved_contract_materialization"] is not True or any(
        authority[key] is not False
        for key in (
            "canonical_registry_write", "historical_pit_admission", "training_admission",
            "protected_evaluation_admission", "production_admission",
        )
    ):
        raise ValueError("reconciliation expansion policy authority is open beyond candidate resolution")
    base_path = repo_root / policy["base_contract"]["relative_path"]
    if sha256_file(base_path) != policy["base_contract"]["sha256"]:
        raise ValueError("base NCAA reconciliation contract identity drift")
    adapter = policy["outcome_adapter"]
    adapter_manifest_path = input_data_root / adapter["manifest"]
    if sha256_file(adapter_manifest_path) != adapter["manifest_sha256"]:
        raise ValueError("outcome adapter manifest identity drift")
    adapter_manifest = json.loads(adapter_manifest_path.read_text(encoding="utf-8"))
    if adapter_manifest["dataset_identity"] != adapter["dataset_identity"]:
        raise ValueError("outcome adapter dataset identity drift")
    if sha256_file(input_data_root / adapter["payload"]) != adapter["payload_sha256"]:
        raise ValueError("outcome adapter payload identity drift")
    registry = policy["canonical_registry"]
    if sha256_file(input_data_root / registry["relative_path"]) != registry["sha256"]:
        raise ValueError("canonical registry identity drift")
    discovery_manifest_path = discovery_manifest_path.resolve()
    try:
        discovery_manifest_path.relative_to(input_data_root.resolve())
    except ValueError as exc:
        raise ValueError("discovery manifest must remain under the external data root") from exc
    discovery = json.loads(discovery_manifest_path.read_text(encoding="utf-8"))
    season = int(discovery["season"])
    if discovery["state"] != policy["required_discovery_state"]:
        raise ValueError("discovery population is not graph exhausted")
    original_discovery_sha256 = sha256_file(discovery_manifest_path)
    module_path = Path(__file__).resolve()
    builder_path = repo_root / "tools/build_ncaa_contest_reconciliation_expansion.py"
    wrapper_identities = {
        "policy_sha256": hashlib.sha256(policy_bytes).hexdigest(),
        "wrapper_module_sha256": sha256_file(module_path),
        "wrapper_builder_sha256": sha256_file(builder_path),
    }
    duplicate_alias_groups = _duplicate_contest_alias_groups(
        data_root=input_data_root,
        discovery=discovery,
        registry_path=input_data_root / registry["relative_path"],
        outcome_path=input_data_root / adapter["payload"],
    )
    excluded_contest_ids = sorted(
        {
            contest_id
            for group in duplicate_alias_groups
            for contest_id in group["ncaa_contest_ids"]
        },
        key=int,
    )
    quarantine_core = {
        "schema_version": "1.0.0",
        "artifact_type": "NCAA_DUPLICATE_SOURCE_CONTEST_ALIAS_QUARANTINE",
        "season": season,
        "original_discovery_identity": discovery["discovery_identity"],
        "original_discovery_sha256": original_discovery_sha256,
        "group_count": len(duplicate_alias_groups),
        "contest_count": len(excluded_contest_ids),
        "groups": duplicate_alias_groups,
        "authority": {
            "canonical_identity_mutation": False,
            "source_alias_auto_selection": False,
            "historical_pit_admission": False,
            "training_admission": False,
        },
    }
    quarantine_identity = stable_hash(quarantine_core)
    quarantine_path = output_data_root / "quarantine/ncaa_contest_reconciliation_source_aliases" / str(season) / "sha256" / quarantine_identity / "duplicate_contest_aliases.json"
    quarantine_sha256 = _write_json_immutable(quarantine_core, quarantine_path)
    view = deepcopy(discovery)
    view["artifact_type"] = "NCAA_OFFICIAL_TEAM_GRAPH_DISCOVERY_RECONCILIATION_VIEW"
    view["original_discovery_identity"] = discovery["discovery_identity"]
    view["original_discovery_sha256"] = original_discovery_sha256
    view["source_duplicate_contest_alias_quarantine"] = {
        "relative_path": str(quarantine_path.relative_to(output_data_root)).replace("\\", "/"),
        "sha256": quarantine_sha256,
        "identity": quarantine_identity,
        "group_count": len(duplicate_alias_groups),
        "contest_count": len(excluded_contest_ids),
    }
    excluded = set(excluded_contest_ids)
    view["discovered_contest_ids"] = [
        value for value in discovery["discovered_contest_ids"] if str(value) not in excluded
    ]
    view["reconciliation_view_disposition"] = (
        "GRAPH_EXHAUSTED_WITH_DUPLICATE_SOURCE_CONTEST_ALIASES_QUARANTINED"
        if excluded_contest_ids
        else "GRAPH_EXHAUSTED_NO_DUPLICATE_SOURCE_CONTEST_ALIAS_CONFLICTS"
    )
    view_identity_core = {
        "original_discovery_identity": discovery["discovery_identity"],
        "original_discovery_sha256": original_discovery_sha256,
        "included_contest_ids": view["discovered_contest_ids"],
        "quarantine_identity": quarantine_identity,
        "policy_sha256": wrapper_identities["policy_sha256"],
        "wrapper_module_sha256": wrapper_identities["wrapper_module_sha256"],
    }
    view_identity = stable_hash(view_identity_core)
    view["discovery_identity"] = view_identity
    view["reconciliation_view_identity_core"] = view_identity_core
    view_path = output_data_root / "manifests/ncaa_contest_reconciliation_discovery_views" / str(season) / "sha256" / view_identity / "discovery_view.json"
    view_sha256 = _write_json_immutable(view, view_path)
    wrapper_identities.update(
        {
            "original_discovery_identity": discovery["discovery_identity"],
            "original_discovery_sha256": original_discovery_sha256,
            "reconciliation_discovery_view_identity": view_identity,
            "reconciliation_discovery_view_sha256": view_sha256,
            "duplicate_contest_alias_quarantine_identity": quarantine_identity,
            "duplicate_contest_alias_quarantine_sha256": quarantine_sha256,
        }
    )
    resolved = build_resolved_contract(
        base_contract=json.loads(base_path.read_text(encoding="utf-8")),
        policy=policy,
        season=season,
        discovery_relative_path=str(view_path.relative_to(input_data_root)).replace("\\", "/"),
        discovery_sha256=view_sha256,
        discovery_identity=view_identity,
        wrapper_identities=wrapper_identities,
    )
    contract_identity = stable_hash(resolved)
    contract_path = output_data_root / "manifests/ncaa_contest_reconciliation_contracts" / str(season) / "sha256" / contract_identity / "resolved_contract.json"
    contract_bytes = canonical_json_bytes(resolved) + b"\n"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    if contract_path.exists() and contract_path.read_bytes() != contract_bytes:
        raise ValueError("immutable resolved reconciliation contract collision")
    if not contract_path.exists():
        temporary = contract_path.with_name(f".tmp-{os.getpid()}-{contract_identity[:8]}")
        try:
            with temporary.open("xb") as handle:
                handle.write(contract_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, contract_path)
        finally:
            temporary.unlink(missing_ok=True)
    result = reconcile(
        input_data_root=input_data_root,
        output_data_root=output_data_root,
        repo_root=repo_root,
        contract_path=contract_path,
        issued_at_utc=issued_at_utc,
    )
    result.update(
        {
            "resolved_contract_identity": contract_identity,
            "resolved_contract_path": str(contract_path),
            "resolved_contract_sha256": sha256_file(contract_path),
            "season": season,
        }
    )
    return result
