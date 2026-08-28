"""Parse source-labeled structured domains from admitted official 1997 games."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.validation.artifact_binding import compute_identity

SCHEMA_VERSION = "aggie.data.tamu_official_1997_structured_domains.v1"
CONTRACT_RELATIVE = "configs/tamu_official_1997_structured_domains_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1997_structured_domains_gate.json"
CONTRACT_ID = "BAT-649-TAMU-OFFICIAL-1997-STRUCTURED-DOMAINS-V1"
DECISION_UNIT = "POST-TASK-SRC014-1997-STRUCTURED-DOMAINS-SUCCESSOR-001"
JIRA_KEY = "BAT-649"
SOURCE_ID = "SRC-014"
SEASON = 1997
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
DOMAINS = ("team_statistics", "individual_player_statistics", "drives", "play_by_play", "scoring_summary")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def compute_code_identity(repo_root: Path) -> str:
    members = (
        "src/aggie_analytics/data/tamu_official_1997_structured_domains.py",
        "src/aggie_analytics/data/tamu_official_1997_boxscores.py",
    )
    hasher = hashlib.sha256()
    hasher.update(b"aggie.1997.structured_domains.code_bundle.v2\n")
    for relative in members:
        path = repo_root / relative
        if not path.is_file():
            raise AuthorityViolation("code bundle member missing")
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\n")
        hasher.update(path.read_bytes())
        hasher.update(b"\n")
    return hasher.hexdigest()


def _row(domain: str, source_row: Mapping[str, Any], game: Mapping[str, Any], row_order: int) -> dict[str, Any]:
    return {
        "domain": domain,
        "source_domain": domain,
        "source_url": str(game.get("url") or ""),
        "source_sha256": str(game.get("source_sha256") or ""),
        "source_season": SEASON,
        "source_row_order": row_order,
        "row_order": row_order,
        "block_index": 0,
        "parser_identity": str(game.get("parser_identity") or ""),
        "availability": "NOT_ESTABLISHED",
        "availability_claim": False,
        "player_identity": "SOURCE_PLAYER_CANDIDATE",
        "identity_status": "SOURCE_TEXT_ONLY",
        "original_text": str(source_row),
        "raw": dict(source_row),
    }


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    gate1997 = load_json(repo_root / "artifacts/data_lake/tamu_official_1997_boxscore_gate.json")
    dataset_identity = str(gate1997.get("dataset_identity") or "")
    if not dataset_identity:
        raise AuthorityViolation("1997 boxscore dataset identity missing")
    payload_path = data_root / contract["upstream"]["normalized_root"] / dataset_identity / "payload.json"
    if not payload_path.is_file():
        raise AuthorityViolation("1997 normalized payload missing")
    payload = load_json(payload_path)
    normalized_rows = list(payload.get("normalized_rows") or [])
    games = list(payload.get("games") or [])
    admitted_games = [
        game
        for game in games
        if str(game.get("canonical_game_match_status") or "")
        in {"MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE", "OFFICIAL_INDEX_DATE_CONFLICT"}
        and str(game.get("conflict_status") or "")
        in {"NONE", "SEASON_INDEX_DATE_VS_BOX_PLAYED_DATE"}
    ]
    admitted_urls = {str(game.get("url") or "") for game in admitted_games}
    rows_groups: list[list[dict[str, Any]]] = []
    game_surfaces: list[dict[str, Any]] = []
    domain_totals = {domain: 0 for domain in DOMAINS}
    for entry in normalized_rows:
        game = dict(entry.get("game") or {})
        if not game:
            continue
        url = str(game.get("url") or "")
        if url not in admitted_urls:
            continue
        domain_rows: list[dict[str, Any]] = []
        coverage: dict[str, str] = {}
        for domain in DOMAINS:
            source_rows = list(entry.get(domain) or [])
            if not source_rows and domain == "individual_player_statistics":
                source_rows = list(entry.get("player_stat_candidates") or [])
            if source_rows:
                for idx, source_row in enumerate(source_rows):
                    domain_rows.append(_row(domain, source_row, game, idx))
            coverage[domain] = "PRESENT" if source_rows else "ABSENT"
            if coverage[domain] == "PRESENT" and not source_rows:
                raise AuthorityViolation(f"PRESENT coverage without serialized rows for {domain}")
            domain_totals[domain] += len(source_rows)
        rows_groups.append(domain_rows)
        game_surfaces.append(
            {
                "url": url,
                "source_sha256": str(game.get("source_sha256") or ""),
                "source_season": SEASON,
                "domain_coverage": coverage,
                "row_counts": {domain: len([row for row in domain_rows if row["domain"] == domain]) for domain in DOMAINS},
                "warnings": list(game.get("warnings") or []),
                "parser_identity": str(game.get("parser_identity") or ""),
            }
        )
    if len(game_surfaces) != len(admitted_games):
        raise AuthorityViolation("admitted game/structured row mismatch")
    for group in rows_groups:
        for row in group:
            if row["availability"] != "NOT_ESTABLISHED" or row["availability_claim"]:
                raise AuthorityViolation("participation promoted to availability")
    counts = {
        "games_total": len(admitted_games),
        "games_with_structured_rows": len(game_surfaces),
        "serialized_rows_total": sum(domain_totals.values()),
        "ncaa_contest_ids_created": 0,
    }
    counts.update({f"{domain}_rows": domain_totals[domain] for domain in DOMAINS})
    payload_out = {
        "schema_version": SCHEMA_VERSION,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "season": SEASON,
        "upstream_boxscore_gate_identity": str(gate1997.get("gate_identity") or ""),
        "upstream_boxscore_dataset_identity": dataset_identity,
        "games": game_surfaces,
        "rows": rows_groups,
        "counts": counts,
        "protected_lane": PROTECTED_LANE,
        "validator_code_identity": compute_code_identity(repo_root),
    }
    payload_out["payload_identity"] = stable_hash(
        {
            "season": SEASON,
            "upstream_boxscore_dataset_identity": dataset_identity,
            "games": game_surfaces,
            "counts": counts,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1997_STRUCTURED_DOMAINS_GATE",
        "result": "PASS_OFFICIAL_1997_STRUCTURED_DOMAINS" if counts["games_with_structured_rows"] > 0 else "PARTIAL_OFFICIAL_1997_STRUCTURED_DOMAINS",
        "classification": "TAMU_SRC014_OFFICIAL_1997_STRUCTURED_DOMAINS_CANDIDATE_ONLY",
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "payload_identity": payload_out["payload_identity"],
        "upstream_boxscore_gate_identity": payload_out["upstream_boxscore_gate_identity"],
        "upstream_boxscore_dataset_identity": payload_out["upstream_boxscore_dataset_identity"],
        "counts": counts,
        "protected_lane": PROTECTED_LANE,
        "validator_code_identity": payload_out["validator_code_identity"],
    }
    gate["gate_identity"] = compute_identity(gate, "gate_identity")
    return {"contract": contract, "payload": payload_out, "gate": gate}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    root = data_root / objects["contract"]["payloads"]["enriched_root"] / payload["payload_identity"]
    write_json(root / "payload.json", payload)
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "payload_identity": payload["payload_identity"],
        "games_with_structured_rows": payload["counts"]["games_with_structured_rows"],
        "serialized_rows_total": payload["counts"]["serialized_rows_total"],
    }


def validate_artifact(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 1997 structured-domains gate does not match independent reconstruction")
    if committed.get("gate_identity") != compute_identity(committed, "gate_identity"):
        raise AuthorityViolation("gate identity does not recompute")
    payload_path = data_root / expected["contract"]["payloads"]["enriched_root"] / expected["payload"]["payload_identity"] / "payload.json"
    if not payload_path.is_file():
        raise AuthorityViolation("external 1997 structured payload missing")
    if load_json(payload_path) != expected["payload"]:
        raise AuthorityViolation("external 1997 structured payload mismatch")
    return {"result": "PASS", "gate_identity": committed["gate_identity"], "payload_identity": committed["payload_identity"]}


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
