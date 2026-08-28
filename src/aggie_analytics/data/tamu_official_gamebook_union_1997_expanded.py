"""Immutable 1997 recovered-union successor from Cycle #18 predecessor."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.validation.artifact_binding import compute_identity

SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_1997_expanded.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_1997_expanded_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_1997_expanded_gate.json"
CONTRACT_ID = "BAT-649-TAMU-OFFICIAL-1997-EXPANDED-UNION-V1"
DECISION_UNIT = "POST-TASK-SRC014-1997-RECOVERED-UNION-001"
JIRA_KEY = "BAT-649"
SOURCE_ID = "SRC-014"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PINNED_CYCLE18_PREDECESSOR_UNION_IDENTITY = "e85b9b1d420f07204c55a8f82989f4cde99e8a2c151e1bce4ca5ae68ef3f6fe8"
PINNED_CYCLE18_PREDECESSOR_GATE_IDENTITY = "a6ac7c237333febc5822a467b60be944af20190ddc203f8027f5aeaa61af7f90"
UNION_MANIFEST_NAME = "union_manifest.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _build_enriched_from_recovered(game: Mapping[str, Any], structured: Mapping[str, Any]) -> dict[str, Any]:
    coverage = dict(structured.get("domain_coverage") or {})
    coverage.update(
        {
            "game_identity_metadata": "PRESENT",
            "season": "PRESENT",
            "played_date": "PRESENT",
            "teams": "PRESENT",
            "scores": "PRESENT",
            "site_venue": "PRESENT" if game.get("site") else "ABSENT",
            "quarter_scoring": "PRESENT",
        }
    )
    return {
        "availability_claim": False,
        "calendar_date": game.get("calendar_date"),
        "canonical_game_id": None,
        "canonical_game_match_status": "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE",
        "conflict_status": "NONE",
        "domain_coverage": coverage,
        "football_season": game.get("football_season"),
        "historical_publication_time": None,
        "index_date_candidate": game.get("index_date_candidate"),
        "ncaa_contest_id": None,
        "opponent_candidate": game.get("opponent_candidate"),
        "opponent_normalized": game.get("opponent_normalized"),
        "opponent_points": game.get("opponent_points"),
        "overlay_applied": True,
        "overlay_source": "POST-TASK-SRC014-1997-STRUCTURED-DOMAINS-SUCCESSOR-001",
        "prior_rich_structured": False,
        "rich_structured": bool((structured.get("row_counts") or {}).get("team_statistics", 0)),
        "site": game.get("site"),
        "source_season": 1997,
        "source_sha256": game.get("source_sha256"),
        "stadium": game.get("stadium"),
        "tamu_points": game.get("tamu_points"),
        "url": game.get("url"),
        "venue_state": game.get("venue_state"),
    }


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    predecessor_manifest = (
        data_root / "features/tamu_official_gamebook_union_1996_expanded/sha256" / PINNED_CYCLE18_PREDECESSOR_UNION_IDENTITY / UNION_MANIFEST_NAME
    )
    if not predecessor_manifest.is_file():
        raise AuthorityViolation("cycle18 predecessor union manifest missing")
    predecessor_payload = load_json(predecessor_manifest)
    if predecessor_payload.get("union_identity") != PINNED_CYCLE18_PREDECESSOR_UNION_IDENTITY:
        raise AuthorityViolation("predecessor union payload identity drifted")
    boxscore_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_1997_boxscore_gate.json")
    boxscore_gate_identity = str(boxscore_gate.get("gate_identity") or "")
    boxscore_dataset_identity = str(boxscore_gate.get("dataset_identity") or "")
    if not boxscore_gate_identity or not boxscore_dataset_identity:
        raise AuthorityViolation("1997 boxscore gate identities missing")
    boxscore_payload_path = data_root / contract["upstream"]["boxscore_root"] / boxscore_dataset_identity / "payload.json"
    if not boxscore_payload_path.is_file():
        raise AuthorityViolation("1997 boxscore payload missing")
    boxscore_payload = load_json(boxscore_payload_path)
    structured_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_1997_structured_domains_gate.json")
    structured_gate_identity = str(structured_gate.get("gate_identity") or "")
    structured_payload_identity = str(structured_gate.get("payload_identity") or "")
    if not structured_gate_identity or not structured_payload_identity:
        raise AuthorityViolation("1997 structured gate identities missing")
    structured_payload_path = data_root / "features/tamu_official_1997_structured_domains/sha256" / structured_payload_identity / "payload.json"
    if not structured_payload_path.is_file():
        raise AuthorityViolation("1997 structured payload missing")
    structured_payload = load_json(structured_payload_path)
    structured_games = {str(item.get("url") or ""): item for item in (structured_payload.get("games") or [])}
    recovered_1997_games: list[dict[str, Any]] = []
    for game in boxscore_payload.get("games") or []:
        if str(game.get("canonical_game_match_status") or "") not in {
            "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE",
            "OFFICIAL_INDEX_DATE_CONFLICT",
        }:
            continue
        if str(game.get("conflict_status") or "") not in {"NONE", "SEASON_INDEX_DATE_VS_BOX_PLAYED_DATE"}:
            continue
        url = str(game.get("url") or "")
        structured = structured_games.get(url)
        if structured is None:
            raise AuthorityViolation(f"1997 structured payload missing admitted game {url}")
        recovered_1997_games.append(_build_enriched_from_recovered(game, structured))
    if len(recovered_1997_games) != 12:
        raise AuthorityViolation(f"expected 12 recovered 1997 games, found {len(recovered_1997_games)}")
    preserved_members = list(predecessor_payload.get("enriched_official_games") or [])
    combined_members = sorted(preserved_members + recovered_1997_games, key=lambda row: (str(row.get("calendar_date") or ""), str(row.get("url") or "")))
    combined_urls = [str(item.get("url") or "") for item in combined_members]
    if len(set(combined_urls)) != len(combined_urls):
        raise AuthorityViolation("duplicate admitted URLs in 1997 recovered union")

    historical_ledger = list(predecessor_payload.get("complete_rejection_ledger") or [])
    recovered_urls = {str(item.get("url") or "") for item in recovered_1997_games}
    active_rejections: list[dict[str, Any]] = []
    superseded_count = 0
    for row in historical_ledger:
        if str(row.get("source_season") or "") == "1997" and str(row.get("url") or "") in recovered_urls:
            row["rejection_reason"] = "SUPERSEDED_BY_VERIFIED_LEGACY_H2_FORMAT_RECOVERY"
            row["superseded"] = True
            superseded_count += 1
            continue
        active_rejections.append(row)
    active_rejections = sorted(active_rejections, key=lambda row: str(row.get("url") or ""))
    admitted_urls = set(combined_urls)
    active_urls = {str(item.get("url") or "") for item in active_rejections}
    if admitted_urls & active_urls:
        raise AuthorityViolation("active rejection/admission overlap in 1997 recovered union")
    for gap_url in predecessor_payload.get("admitted_row_gap_urls") or []:
        if str(gap_url) in active_urls:
            raise AuthorityViolation("admitted row-gap URL cannot be active rejection")

    counts = dict(predecessor_payload.get("counts") or {})
    counts["predecessor_membership_preserved"] = len(preserved_members)
    counts["official_1997_admitted"] = len(recovered_1997_games)
    counts["official_1997_rejected"] = len(active_rejections)
    counts["new_games_added"] = len(recovered_1997_games)
    counts["games_admitted_to_union"] = len(combined_members)
    counts["superseded_rejections"] = superseded_count
    counts["active_rejections"] = len(active_rejections)
    counts["rejected_urls_complete"] = len(historical_ledger)
    counts["unmatched_rejected"] = len(active_rejections)
    counts["ncaa_contest_ids_created"] = 0
    payload = {
        "schema_version": SCHEMA_VERSION,
        "predecessor_union_identity": PINNED_CYCLE18_PREDECESSOR_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_CYCLE18_PREDECESSOR_GATE_IDENTITY,
        "upstream_1997_boxscore_gate_identity": boxscore_gate_identity,
        "upstream_1997_boxscore_dataset_identity": boxscore_dataset_identity,
        "upstream_1997_structured_gate_identity": structured_gate_identity,
        "enriched_official_games": combined_members,
        "admitted_official_1997_games": recovered_1997_games,
        "active_rejections": active_rejections,
        "complete_rejection_ledger": historical_ledger,
        "admitted_row_gap_urls": list(predecessor_payload.get("admitted_row_gap_urls") or []),
        "counts": counts,
        "protected_lane": PROTECTED_LANE,
    }
    payload["union_identity"] = stable_hash(
        {
            "predecessor_union_identity": payload["predecessor_union_identity"],
            "admitted_urls": sorted(admitted_urls),
            "active_rejections": sorted(active_urls),
            "historical_rejections": sorted({str(row.get("url") or "") for row in historical_ledger}),
            "counts": counts,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_1997_EXPANDED_GATE",
        "result": "PASS_OFFICIAL_1997_RECOVERED_UNION_SUCCESSOR",
        "classification": "TAMU_OFFICIAL_GAMEBOOK_UNION_1997_EXPANDED_CANDIDATE_ONLY",
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "disposition": "PRESERVE_PREDECESSOR_MEMBERS_AND_ADMIT_RECOVERED_1997_GAMES",
        "predecessor_union_identity": PINNED_CYCLE18_PREDECESSOR_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_CYCLE18_PREDECESSOR_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "counts": counts,
        "admitted_row_gap_urls": payload["admitted_row_gap_urls"],
        "active_rejection_count": len(active_rejections),
        "historical_rejection_count": len(historical_ledger),
        "upstream_1997_boxscore_gate_identity": boxscore_gate_identity,
        "upstream_1997_boxscore_dataset_identity": boxscore_dataset_identity,
        "upstream_1997_structured_gate_identity": structured_gate_identity,
        "protected_lane": PROTECTED_LANE,
        "validation_contract_version": SCHEMA_VERSION,
    }
    gate["gate_identity"] = compute_identity(gate, "gate_identity")
    root = data_root / contract["payloads"]["union_root"] / payload["union_identity"]
    return {"contract": contract, "payload": payload, "gate": gate, "manifest_path": root / UNION_MANIFEST_NAME}


def materialize_union(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    write_json(objects["manifest_path"], objects["payload"])
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "union_identity": objects["payload"]["union_identity"],
        "manifest_path": str(objects["manifest_path"]),
        "official_1997_rejected": objects["payload"]["counts"]["official_1997_rejected"],
    }


def validate_artifact(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 1997-expanded union gate does not match independent reconstruction")
    if committed.get("gate_identity") != compute_identity(committed, "gate_identity"):
        raise AuthorityViolation("gate identity does not recompute")
    if not expected["manifest_path"].is_file():
        raise AuthorityViolation("external 1997 union manifest missing")
    if load_json(expected["manifest_path"]) != expected["payload"]:
        raise AuthorityViolation("external 1997 union manifest mismatch")
    return {"result": "PASS", "gate_identity": committed["gate_identity"], "union_identity": committed["union_identity"]}


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
