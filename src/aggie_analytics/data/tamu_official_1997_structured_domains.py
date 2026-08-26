"""Parse source-labeled structured domains from normalized official 1997 boxscore payloads."""

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
CONTRACT_ID = "BAT-XXX-TAMU-OFFICIAL-1997-STRUCTURED-DOMAINS-V1"
DECISION_UNIT = "POST-TASK-SRC014-1997-STRUCTURED-DOMAINS-001"
JIRA_KEY = "BAT-XXX"
SOURCE_ID = "SRC-014"
SEASON = 1997
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PINNED_1997_BOXSCORE_GATE_IDENTITY = "09a0c2cc295c1b8c5cb03e392e7bb38d637f48b4d7090b69766e69b89ca808f3"
PINNED_1997_BOXSCORE_DATASET_IDENTITY = "ca7bbf2e78dd028d647ff3abc77392c91d956c96ab7d9a93b2ca6f5e8953598a"
DOMAINS = ("team_statistics", "individual_player_statistics", "drives", "play_by_play", "scoring_summary")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def compute_code_identity(repo_root: Path) -> str:
    path = repo_root / "src/aggie_analytics/data/tamu_official_1997_structured_domains.py"
    if not path.is_file():
        raise AuthorityViolation("code bundle member missing")
    hasher = hashlib.sha256()
    hasher.update(b"aggie.1997.structured_domains.code_bundle.v1\n")
    hasher.update(path.read_bytes())
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
        "parser_identity": str(game.get("parser_identity") or "tamu.official.statcrew.preformatted.v1"),
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
    if gate1997.get("gate_identity") != PINNED_1997_BOXSCORE_GATE_IDENTITY:
        raise AuthorityViolation("1997 boxscore gate identity drifted")
    if gate1997.get("dataset_identity") != PINNED_1997_BOXSCORE_DATASET_IDENTITY:
        raise AuthorityViolation("1997 boxscore dataset identity drifted")
    payload_path = data_root / contract["upstream"]["normalized_root"] / PINNED_1997_BOXSCORE_DATASET_IDENTITY / "payload.json"
    if not payload_path.is_file():
        raise AuthorityViolation("1997 normalized payload missing")
    payload = load_json(payload_path)
    normalized_rows = list(payload.get("normalized_rows") or [])
    games = list(payload.get("games") or [])
    by_url = {str(game.get("url") or ""): game for game in games}
    rows_groups: list[list[dict[str, Any]]] = []
    game_surfaces: list[dict[str, Any]] = []
    domain_totals = {domain: 0 for domain in DOMAINS}
    for entry in normalized_rows:
        game = dict(entry.get("game") or {})
        if not game:
            continue
        url = str(game.get("url") or "")
        if url not in by_url:
            raise AuthorityViolation("normalized game missing from payload games list")
        domain_rows: list[dict[str, Any]] = []
        coverage: dict[str, str] = {}
        for domain in DOMAINS:
            source_rows = entry.get(domain) or []
            for idx, source_row in enumerate(source_rows):
                domain_rows.append(_row(domain, source_row, game, idx))
            coverage[domain] = "PRESENT" if source_rows else "ABSENT"
            domain_totals[domain] += len(source_rows)
        rows_groups.append(domain_rows)
        game_surfaces.append(
            {
                "url": url,
                "source_sha256": str(game.get("source_sha256") or ""),
                "source_season": SEASON,
                "domain_coverage": coverage,
                "row_counts": {domain: len(entry.get(domain) or []) for domain in DOMAINS},
                "warnings": list(game.get("warnings") or []),
                "parser_identity": str(game.get("parser_identity") or "tamu.official.statcrew.preformatted.v1"),
            }
        )
    for group in rows_groups:
        for r in group:
            if r["availability"] != "NOT_ESTABLISHED" or r["availability_claim"]:
                raise AuthorityViolation("participation promoted to availability")
    counts = {
        "games_total": len(games),
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
        "upstream_boxscore_gate_identity": PINNED_1997_BOXSCORE_GATE_IDENTITY,
        "upstream_boxscore_dataset_identity": PINNED_1997_BOXSCORE_DATASET_IDENTITY,
        "games": game_surfaces,
        "rows": rows_groups,
        "counts": counts,
        "protected_lane": PROTECTED_LANE,
        "validator_code_identity": compute_code_identity(repo_root),
    }
    payload_out["payload_identity"] = stable_hash(
        {
            "season": SEASON,
            "upstream_boxscore_dataset_identity": PINNED_1997_BOXSCORE_DATASET_IDENTITY,
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
        "upstream_boxscore_gate_identity": PINNED_1997_BOXSCORE_GATE_IDENTITY,
        "upstream_boxscore_dataset_identity": PINNED_1997_BOXSCORE_DATASET_IDENTITY,
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
