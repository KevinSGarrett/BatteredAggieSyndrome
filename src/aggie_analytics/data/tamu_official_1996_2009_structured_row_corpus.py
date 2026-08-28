"""Materialize immutable recovered 1996-2009 structured-row corpus successor."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus import CHILD_FILENAMES
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.validation.artifact_binding import compute_identity

SCHEMA_VERSION = "aggie.data.tamu_official_1996_2009_structured_row_corpus.v1"
CONTRACT_RELATIVE = "configs/tamu_official_1996_2009_structured_row_corpus_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1996_2009_structured_row_corpus_gate.json"
CONTRACT_ID = "BAT-649-TAMU-OFFICIAL-1996-2009-ROW-CORPUS-V1"
DECISION_UNIT = "POST-TASK-SRC014-1996-2009-RECOVERED-STRUCTURED-ROW-CORPUS-001"
JIRA_KEY = "BAT-649"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1996_2009_STRUCTURED_ROW_CORPUS_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1996_2009_STRUCTURED_ROW_CORPUS_SUCCESSOR"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
MANIFEST_NAME = "corpus_manifest.json"
SERIALIZED_DOMAINS = ("team_statistics", "individual_player_statistics", "drives", "play_by_play", "scoring_summary")
PREDECESSOR_1998_2009_DATASET_IDENTITY = "0ff650b1b691299d2b14fd252b8b938a9afe1d02cfd1eefdcd4d53bde2947ca8"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def compute_code_identity(repo_root: Path) -> str:
    path = repo_root / "src/aggie_analytics/data/tamu_official_1996_2009_structured_row_corpus.py"
    if not path.is_file():
        raise AuthorityViolation("code bundle member missing")
    hasher = hashlib.sha256()
    hasher.update(b"aggie.1996_2009.corpus.code_bundle.v1\n")
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8", newline="\n")


def _season_set(admitted_games: list[Mapping[str, Any]]) -> list[int]:
    values = {int(item.get("source_season") or item.get("season") or 0) for item in admitted_games if int(item.get("source_season") or item.get("season") or 0) > 0}
    return sorted(values)


def _row_identity(row: Mapping[str, Any]) -> str:
    return stable_hash(
        {
            "domain": row.get("domain"),
            "source_url": row.get("source_url"),
            "source_sha256": row.get("source_sha256"),
            "source_row_order": row.get("source_row_order"),
            "raw": row.get("raw"),
        }
    )


def _append_structured_rows(
    *,
    out_rows: dict[str, list[dict[str, Any]]],
    structured_payload: Mapping[str, Any],
    payload_identity: str,
    union_identity: str,
    admitted_urls: set[str],
    active_rejected_urls: set[str],
) -> None:
    for game_rows in structured_payload.get("rows") or []:
        for row in game_rows:
            domain = str(row.get("domain") or "")
            if domain not in SERIALIZED_DOMAINS:
                continue
            source_url = str(row.get("source_url") or "")
            if not source_url or source_url in active_rejected_urls or source_url not in admitted_urls:
                continue
            normalized = {
                "admitted_final_union_membership": True,
                "availability": "NOT_ESTABLISHED",
                "availability_claim": False,
                "classification": "POSTGAME_OFFICIAL_STRUCTURED_EVIDENCE_ONLY",
                "domain": domain,
                "domain_row_order": int(row.get("row_order") or 0),
                "identity_status": "SOURCE_TEXT_ONLY",
                "name_raw": None,
                "original_text": str(row.get("original_text") or ""),
                "parser_identity": str(row.get("parser_identity") or ""),
                "parser_identity_source": "ROW",
                "player_identity": "SOURCE_PLAYER_CANDIDATE",
                "quarter_raw": None,
                "season": int(row.get("source_season") or 0),
                "source_block": str(row.get("block_index") or "0"),
                "source_row_order": int(row.get("source_row_order") or 0),
                "source_sha256": str(row.get("source_sha256") or ""),
                "source_table": str(row.get("source_domain") or domain),
                "source_url": source_url,
                "stat_group": None,
                "team_raw": None,
                "union_identity": union_identity,
                "upstream_jira_key": JIRA_KEY,
                "upstream_payload_identity": payload_identity,
                "raw": dict(row.get("raw") or {}),
            }
            normalized["row_identity"] = _row_identity(normalized)
            out_rows[domain].append(normalized)


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    g638 = load_json(repo_root / "artifacts/data_lake/tamu_official_1998_2009_structured_row_corpus_gate.json")
    predecessor_gate_identity = str(g638.get("gate_identity") or "")
    predecessor_dataset_identity = str(g638.get("dataset_identity") or "")
    if not predecessor_gate_identity or not predecessor_dataset_identity:
        raise AuthorityViolation("predecessor corpus identities missing")
    rej_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_1998_2009_rejection_integrity_gate.json")
    rejection_gate_identity = str(rej_gate.get("gate_identity") or "")
    rejection_ledger_identity = str(rej_gate.get("ledger_identity") or "")
    if not rejection_gate_identity or not rejection_ledger_identity:
        raise AuthorityViolation("rejection ledger identities missing")
    union_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_gamebook_union_1996_expanded_gate.json")
    union_gate_identity = str(union_gate.get("gate_identity") or "")
    union_identity = str(union_gate.get("union_identity") or "")
    if not union_gate_identity or not union_identity:
        raise AuthorityViolation("final recovered union identities missing")
    structured_1997 = load_json(repo_root / "artifacts/data_lake/tamu_official_1997_structured_domains_gate.json")
    structured_1997_gate_identity = str(structured_1997.get("gate_identity") or "")
    structured_1997_payload_identity = str(structured_1997.get("payload_identity") or "")
    if not structured_1997_gate_identity or not structured_1997_payload_identity:
        raise AuthorityViolation("1997 structured identities missing")
    structured_1996 = load_json(repo_root / "artifacts/data_lake/tamu_official_1996_structured_domains_gate.json")
    structured_1996_gate_identity = str(structured_1996.get("gate_identity") or "")
    structured_1996_payload_identity = str(structured_1996.get("payload_identity") or "")
    if not structured_1996_gate_identity or not structured_1996_payload_identity:
        raise AuthorityViolation("1996 structured identities missing")
    union_root = data_root / "features/tamu_official_gamebook_union_1996_expanded/sha256" / union_identity / "union_manifest.json"
    if not union_root.is_file():
        raise AuthorityViolation("1996-expanded union manifest missing")
    union_payload = load_json(union_root)
    admitted_games = list(union_payload.get("enriched_official_games") or [])
    admitted_urls = {str(item.get("url") or "") for item in admitted_games if str(item.get("url") or "")}
    rejection_payload_path = data_root / "features/tamu_official_1998_2009_rejection_integrity/sha256" / rejection_ledger_identity / "rejection_ledger.json"
    if not rejection_payload_path.is_file():
        raise AuthorityViolation("rejection-ledger payload missing")
    rejection_payload = load_json(rejection_payload_path)
    active_rejections = list(rejection_payload.get("active_rejections") or [])
    rejected_urls = {str(item.get("url") or "") for item in active_rejections if str(item.get("url") or "")}
    if admitted_urls & rejected_urls:
        raise AuthorityViolation("rejection/admission overlap in final corpus predecessor")
    source_root = data_root / "features/tamu_official_1998_2009_structured_row_corpus/sha256" / predecessor_dataset_identity
    child_payloads: dict[str, dict[str, Any]] = {}
    rows_per_domain: dict[str, int] = {}
    games_present_by_domain: dict[str, int] = {}
    rejected_rows_by_domain: dict[str, int] = {}
    output_rows_by_domain: dict[str, list[dict[str, Any]]] = {}
    for domain in SERIALIZED_DOMAINS:
        filename = CHILD_FILENAMES[domain]
        path = source_root / filename
        if not path.is_file():
            raise AuthorityViolation(f"missing predecessor child payload: {filename}")
        rows = _read_jsonl(path)
        rejected_hits = 0
        kept: list[dict[str, Any]] = []
        for row in rows:
            url = str(row.get("source_url") or "")
            if url in rejected_urls:
                rejected_hits += 1
                continue
            if url and url not in admitted_urls:
                continue
            kept.append(row)
        output_rows_by_domain[domain] = kept
        rejected_rows_by_domain[domain] = rejected_hits
        rows_per_domain[domain] = len(kept)
        games_present_by_domain[domain] = len({str(row.get("source_url") or "") for row in kept if str(row.get("source_url") or "")})
        child_payloads[domain] = {
            "filename": filename,
            "row_count": len(kept),
            "source_filename": filename,
            "source_dataset_identity": predecessor_dataset_identity,
        }
    payload_1997_path = data_root / "features/tamu_official_1997_structured_domains/sha256" / structured_1997_payload_identity / "payload.json"
    payload_1996_path = data_root / "features/tamu_official_1996_structured_domains/sha256" / structured_1996_payload_identity / "payload.json"
    if not payload_1997_path.is_file() or not payload_1996_path.is_file():
        raise AuthorityViolation("recovered structured payload missing")
    _append_structured_rows(
        out_rows=output_rows_by_domain,
        structured_payload=load_json(payload_1997_path),
        payload_identity=structured_1997_payload_identity,
        union_identity=union_identity,
        admitted_urls=admitted_urls,
        active_rejected_urls=rejected_urls,
    )
    _append_structured_rows(
        out_rows=output_rows_by_domain,
        structured_payload=load_json(payload_1996_path),
        payload_identity=structured_1996_payload_identity,
        union_identity=union_identity,
        admitted_urls=admitted_urls,
        active_rejected_urls=rejected_urls,
    )
    for domain in SERIALIZED_DOMAINS:
        rows_per_domain[domain] = len(output_rows_by_domain[domain])
        games_present_by_domain[domain] = len({str(row.get("source_url") or "") for row in output_rows_by_domain[domain] if str(row.get("source_url") or "")})
    if any(rejected_rows_by_domain.values()):
        raise AuthorityViolation("active rejected URLs leaked into child payload rows")
    selected_seasons = _season_set(admitted_games)
    total_rows = sum(rows_per_domain.values())
    absent_domain_games = {domain: len(admitted_urls) - games_present_by_domain[domain] for domain in SERIALIZED_DOMAINS}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "predecessor_dataset_identity": predecessor_dataset_identity,
        "predecessor_gate_identity": predecessor_gate_identity,
        "union_identity": union_identity,
        "union_gate_identity": union_gate_identity,
        "rejection_integrity_gate_identity": rejection_gate_identity,
        "rejection_ledger_identity": rejection_ledger_identity,
        "upstream_structured_1997_gate_identity": structured_1997_gate_identity,
        "upstream_structured_1996_gate_identity": structured_1996_gate_identity,
        "selected_seasons": selected_seasons,
        "admitted_row_gap_urls": list(union_payload.get("admitted_row_gap_urls") or []),
        "child_payloads": child_payloads,
        "rows_per_domain": rows_per_domain,
        "games_present_by_domain": games_present_by_domain,
        "absent_domain_games": absent_domain_games,
        "rejected_rows_by_domain": rejected_rows_by_domain,
        "counts": {
            "seasons": len(selected_seasons),
            "games": len(admitted_urls),
            "serialized_rows_total": total_rows,
            "complete_rejection_count": int(rej_gate.get("complete_rejection_count") or len(rejection_payload.get("historical_rejection_records") or [])),
            "active_rejection_count": len(rejected_urls),
            "superseded_rejection_count": int(rej_gate.get("superseded_rejection_count") or 0),
            "ncaa_contest_ids_created": 0,
            "new_admissions": int((union_payload.get("counts") or {}).get("official_1996_admitted", 0)
                                  + (union_payload.get("counts") or {}).get("official_1997_admitted", 0)),
            "new_rejections": len(rejected_urls),
        },
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "availability_state": "NOT_ESTABLISHED",
        "protected_lane": PROTECTED_LANE,
        "validator_code_identity": compute_code_identity(repo_root),
    }
    manifest["dataset_identity"] = stable_hash(
        {
            "predecessor_dataset_identity": manifest["predecessor_dataset_identity"],
            "union_identity": manifest["union_identity"],
            "rejection_ledger_identity": manifest["rejection_ledger_identity"],
            "child_payloads": manifest["child_payloads"],
            "rows_per_domain": manifest["rows_per_domain"],
            "games_present_by_domain": manifest["games_present_by_domain"],
            "counts": manifest["counts"],
        }
    )
    out_root = data_root / contract["payloads"]["corpus_root"] / manifest["dataset_identity"]
    for domain in SERIALIZED_DOMAINS:
        _write_jsonl(out_root / CHILD_FILENAMES[domain], output_rows_by_domain[domain])
        child_payloads[domain]["sha256"] = sha256_file(out_root / CHILD_FILENAMES[domain])
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1996_2009_STRUCTURED_ROW_CORPUS_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "dataset_identity": manifest["dataset_identity"],
        "union_identity": manifest["union_identity"],
        "predecessor_dataset_identity": predecessor_dataset_identity,
        "predecessor_gate_identity": predecessor_gate_identity,
        "union_gate_identity": union_gate_identity,
        "rejection_integrity_gate_identity": rejection_gate_identity,
        "rejection_ledger_identity": rejection_ledger_identity,
        "upstream_structured_1997_gate_identity": structured_1997_gate_identity,
        "upstream_structured_1996_gate_identity": structured_1996_gate_identity,
        "selected_seasons": selected_seasons,
        "counts": manifest["counts"],
        "rows_per_domain": rows_per_domain,
        "games_present_by_domain": games_present_by_domain,
        "absent_domain_games": absent_domain_games,
        "admitted_row_gap_urls": manifest["admitted_row_gap_urls"],
        "child_payloads": child_payloads,
        "rejected_rows_by_domain": rejected_rows_by_domain,
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "availability_state": "NOT_ESTABLISHED",
        "protected_lane": PROTECTED_LANE,
    }
    gate["gate_identity"] = compute_identity(gate, "gate_identity")
    return {"contract": contract, "manifest": manifest, "gate": gate, "manifest_path": out_root / MANIFEST_NAME, "out_root": out_root}


def materialize_corpus(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    write_json(objects["manifest_path"], objects["manifest"])
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "dataset_identity": objects["manifest"]["dataset_identity"],
        "manifest_path": str(objects["manifest_path"]),
    }


def validate_artifact(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 1996-2009 corpus gate does not match independent reconstruction")
    if committed.get("gate_identity") != compute_identity(committed, "gate_identity"):
        raise AuthorityViolation("gate identity does not recompute")
    if not expected["manifest_path"].is_file():
        raise AuthorityViolation("external 1996-2009 corpus manifest missing")
    if load_json(expected["manifest_path"]) != expected["manifest"]:
        raise AuthorityViolation("external 1996-2009 corpus manifest mismatch")
    return {"result": "PASS", "dataset_identity": committed["dataset_identity"], "gate_identity": committed["gate_identity"]}


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
