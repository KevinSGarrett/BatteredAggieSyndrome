"""Materialize immutable 1996-2009 structured-row corpus successor."""

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
CONTRACT_ID = "BAT-XXX-TAMU-OFFICIAL-1996-2009-ROW-CORPUS-V1"
DECISION_UNIT = "POST-TASK-SRC014-1996-2009-STRUCTURED-ROW-CORPUS-001"
JIRA_KEY = "BAT-XXX"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1996_2009_STRUCTURED_ROW_CORPUS_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1996_2009_STRUCTURED_ROW_CORPUS_SUCCESSOR"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PINNED_BAT638_GATE_IDENTITY = "a251b95714bed59de8aa593fe1466fce603858b30108c447c53fe6f3b8ee4e54"
PINNED_BAT638_DATASET_IDENTITY = "0ff650b1b691299d2b14fd252b8b938a9afe1d02cfd1eefdcd4d53bde2947ca8"
PINNED_REJECTION_GATE_IDENTITY = "326dae867a39852d51d7b6f6a87a8557a950f74cf498b81e44956b71e4d6378e"
PINNED_REJECTION_LEDGER_IDENTITY = "d88ccffcabb70cd218b0aa40d395dba49c5dca3bcbf9c9ed139422fe20dc3051"
PINNED_UNION_1996_GATE_IDENTITY = "a6ac7c237333febc5822a467b60be944af20190ddc203f8027f5aeaa61af7f90"
PINNED_STRUCTURED_1997_GATE_IDENTITY = "52f84f7bc0cf4de9fe07409db4037ee065176aec526efe7a1d995ccacf31a592"
PINNED_STRUCTURED_1996_GATE_IDENTITY = "2070b2816c6f01bded88dbd353a08cb4468fc4aa95338499ca7f2f0656a01661"
MANIFEST_NAME = "corpus_manifest.json"
SERIALIZED_DOMAINS = ("team_statistics", "individual_player_statistics", "drives", "play_by_play", "scoring_summary")


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


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    g638 = load_json(repo_root / "artifacts/data_lake/tamu_official_1998_2009_structured_row_corpus_gate.json")
    if g638.get("gate_identity") != PINNED_BAT638_GATE_IDENTITY or g638.get("dataset_identity") != PINNED_BAT638_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-638 corpus identities drifted")
    rej_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_1998_2009_rejection_integrity_gate.json")
    if rej_gate.get("gate_identity") != PINNED_REJECTION_GATE_IDENTITY or rej_gate.get("ledger_identity") != PINNED_REJECTION_LEDGER_IDENTITY:
        raise AuthorityViolation("rejection-integrity identities drifted")
    union_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_gamebook_union_1996_expanded_gate.json")
    if union_gate.get("gate_identity") != PINNED_UNION_1996_GATE_IDENTITY:
        raise AuthorityViolation("1996-expanded union gate identity drifted")
    structured_1997 = load_json(repo_root / "artifacts/data_lake/tamu_official_1997_structured_domains_gate.json")
    if structured_1997.get("gate_identity") != PINNED_STRUCTURED_1997_GATE_IDENTITY:
        raise AuthorityViolation("1997 structured identity drifted")
    structured_1996 = load_json(repo_root / "artifacts/data_lake/tamu_official_1996_structured_domains_gate.json")
    if structured_1996.get("gate_identity") != PINNED_STRUCTURED_1996_GATE_IDENTITY:
        raise AuthorityViolation("1996 structured identity drifted")
    union_root = data_root / "features/tamu_official_gamebook_union_1996_expanded/sha256" / str(union_gate.get("union_identity") or "") / "union_manifest.json"
    if not union_root.is_file():
        raise AuthorityViolation("1996-expanded union manifest missing")
    union_payload = load_json(union_root)
    admitted_games = list(union_payload.get("enriched_official_games") or [])
    admitted_urls = {str(item.get("url") or "") for item in admitted_games if str(item.get("url") or "")}
    rejection_ledger = list(union_payload.get("complete_rejection_ledger") or [])
    rejected_urls = {str(item.get("url") or "") for item in rejection_ledger if str(item.get("url") or "")}
    if admitted_urls & rejected_urls:
        raise AuthorityViolation("rejection/admission overlap in final corpus predecessor")
    source_root = data_root / "features/tamu_official_1998_2009_structured_row_corpus/sha256" / PINNED_BAT638_DATASET_IDENTITY
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
            "source_dataset_identity": PINNED_BAT638_DATASET_IDENTITY,
        }
    if any(rejected_rows_by_domain.values()):
        raise AuthorityViolation("rejected URLs leaked into child payload rows")
    selected_seasons = _season_set(admitted_games)
    total_rows = sum(rows_per_domain.values())
    absent_domain_games = {domain: len(admitted_urls) - games_present_by_domain[domain] for domain in SERIALIZED_DOMAINS}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "predecessor_dataset_identity": PINNED_BAT638_DATASET_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT638_GATE_IDENTITY,
        "union_identity": str(union_gate.get("union_identity") or ""),
        "union_gate_identity": PINNED_UNION_1996_GATE_IDENTITY,
        "rejection_integrity_gate_identity": PINNED_REJECTION_GATE_IDENTITY,
        "rejection_ledger_identity": PINNED_REJECTION_LEDGER_IDENTITY,
        "upstream_structured_1997_gate_identity": PINNED_STRUCTURED_1997_GATE_IDENTITY,
        "upstream_structured_1996_gate_identity": PINNED_STRUCTURED_1996_GATE_IDENTITY,
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
            "complete_rejection_count": len(rejected_urls),
            "ncaa_contest_ids_created": 0,
            "new_admissions": 0,
            "new_rejections": int((union_payload.get("counts") or {}).get("official_1996_rejected", 0)),
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
        "predecessor_dataset_identity": PINNED_BAT638_DATASET_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT638_GATE_IDENTITY,
        "union_gate_identity": PINNED_UNION_1996_GATE_IDENTITY,
        "rejection_integrity_gate_identity": PINNED_REJECTION_GATE_IDENTITY,
        "rejection_ledger_identity": PINNED_REJECTION_LEDGER_IDENTITY,
        "upstream_structured_1997_gate_identity": PINNED_STRUCTURED_1997_GATE_IDENTITY,
        "upstream_structured_1996_gate_identity": PINNED_STRUCTURED_1996_GATE_IDENTITY,
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
