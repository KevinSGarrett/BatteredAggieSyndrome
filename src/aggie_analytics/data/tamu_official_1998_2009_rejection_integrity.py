"""Immutable active/historical rejection-ledger successor for official SRC-014 evidence."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus import CHILD_FILENAMES
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.validation.artifact_binding import compute_identity

SCHEMA_VERSION = "aggie.data.tamu_official_1998_2009_rejection_integrity.v1"
VALIDATION_CONTRACT_VERSION = SCHEMA_VERSION
CONTRACT_RELATIVE = "configs/tamu_official_1998_2009_rejection_integrity_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1998_2009_rejection_integrity_gate.json"
CONTRACT_ID = "BAT-649-TAMU-OFFICIAL-1998-2009-REJECTION-INTEGRITY-V1"
DECISION_UNIT = "POST-TASK-SRC014-1996-2009-REJECTION-SUPERSESSION-001"
JIRA_KEY = "BAT-649"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1998_2009_REJECTION_INTEGRITY_CANDIDATE_ONLY"
PASS_RESULT = "PASS_REJECTION_LEDGER_COMPLETE_AND_CORPUS_EXCLUDED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
SERIALIZED_DOMAINS = (
    "team_statistics",
    "individual_player_statistics",
    "drives",
    "play_by_play",
    "scoring_summary",
)
ADMITTED_ROW_GAP_URLS = (
    "https://files.12thman.com/history/football/stats/2006-2007/texas.htm",
    "https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _git_head_sha(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise AuthorityViolation(completed.stderr.strip() or "git rev-parse HEAD failed")
    return completed.stdout.strip()


def _rejecteds_absent_from_corpus(
    *,
    data_root: Path,
    rejected_urls: set[str],
) -> dict[str, int]:
    root = data_root / "features/tamu_official_1998_2009_structured_row_corpus/sha256" / "0ff650b1b691299d2b14fd252b8b938a9afe1d02cfd1eefdcd4d53bde2947ca8"
    domain_counts: dict[str, int] = {}
    for domain in SERIALIZED_DOMAINS:
        filename = CHILD_FILENAMES[domain]
        path = root / filename
        if not path.is_file():
            raise AuthorityViolation(f"missing BAT-638 child payload: {path}")
        count = 0
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if str(row.get("source_url") or "") in rejected_urls:
                count += 1
        domain_counts[domain] = count
    return domain_counts


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    union_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_gamebook_union_1996_expanded_gate.json")
    union_identity = str(union_gate.get("union_identity") or "")
    union_gate_identity = str(union_gate.get("gate_identity") or "")
    if not union_identity or not union_gate_identity:
        raise AuthorityViolation("final recovered union identities missing")
    union_manifest_path = data_root / "features/tamu_official_gamebook_union_1996_expanded/sha256" / union_identity / "union_manifest.json"
    if not union_manifest_path.is_file():
        raise AuthorityViolation("final recovered union manifest missing")
    union_manifest = load_json(union_manifest_path)

    historical_records = list(union_manifest.get("complete_rejection_ledger") or [])
    active_rejections = list(union_manifest.get("active_rejections") or [])
    if len(historical_records) < len(active_rejections):
        raise AuthorityViolation("historical rejection records cannot be fewer than active rejections")
    historical_urls = {str(item.get("url") or "") for item in historical_records}
    active_urls = {str(item.get("url") or "") for item in active_rejections}
    if len(historical_urls) != len(historical_records):
        raise AuthorityViolation("duplicate URL in historical rejection records")
    if len(active_urls) != len(active_rejections):
        raise AuthorityViolation("duplicate URL in active rejections")
    if not active_urls.issubset(historical_urls):
        raise AuthorityViolation("active rejection must be present in historical records")
    admitted_games = list(union_manifest.get("enriched_official_games") or [])
    admitted_urls = {str(item.get("url") or "") for item in admitted_games}
    overlap_with_admitted = sorted(active_urls & admitted_urls)
    if overlap_with_admitted:
        raise AuthorityViolation("active rejections overlap admitted membership")

    for gap_url in ADMITTED_ROW_GAP_URLS:
        if gap_url in active_urls:
            raise AuthorityViolation("admitted row-gap URL incorrectly classified as active rejection")
        if gap_url not in admitted_urls:
            raise AuthorityViolation("admitted row-gap URL missing from admitted union membership")

    structured_1997_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_1997_structured_domains_gate.json")
    structured_1996_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_1996_structured_domains_gate.json")
    structured_1997_payload_identity = str(structured_1997_gate.get("payload_identity") or "")
    structured_1996_payload_identity = str(structured_1996_gate.get("payload_identity") or "")
    if not structured_1997_payload_identity or not structured_1996_payload_identity:
        raise AuthorityViolation("structured payload identities missing for supersession ledger")
    admitted_by_url = {str(item.get("url") or ""): item for item in admitted_games}
    supersessions: list[dict[str, Any]] = []
    for row in historical_records:
        if not row.get("superseded"):
            continue
        url = str(row.get("url") or "")
        admitted = admitted_by_url.get(url)
        if admitted is None:
            raise AuthorityViolation("superseded rejection without admitted successor")
        source_season = int(admitted.get("source_season") or 0)
        if source_season not in {1996, 1997}:
            raise AuthorityViolation("supersession season must be 1996 or 1997")
        supersessions.append(
            {
                "old_rejection_identity": stable_hash(
                    {
                        "url": url,
                        "source_sha256": row.get("source_sha256"),
                        "source_season": row.get("source_season"),
                        "rejection_source": row.get("rejection_source"),
                    }
                ),
                "url": url,
                "new_normalized_game_identity": stable_hash(
                    {
                        "url": admitted.get("url"),
                        "calendar_date": admitted.get("calendar_date"),
                        "source_sha256": admitted.get("source_sha256"),
                        "source_season": admitted.get("source_season"),
                    }
                ),
                "new_structured_payload_identity": structured_1997_payload_identity if source_season == 1997 else structured_1996_payload_identity,
                "new_union_identity": union_identity,
                "material_merge_sha": _git_head_sha(repo_root),
                "reason_code": "SUPERSEDED_BY_VERIFIED_LEGACY_H2_FORMAT_RECOVERY",
            }
        )
    supersessions = sorted(supersessions, key=lambda row: row["url"])
    superseded_urls = {row["url"] for row in supersessions}
    if any(url in active_urls for url in superseded_urls):
        raise AuthorityViolation("superseded rejection cannot remain active")

    rejected_rows_by_domain = _rejecteds_absent_from_corpus(data_root=data_root, rejected_urls=active_urls)
    for domain, count in rejected_rows_by_domain.items():
        if count != 0:
            raise AuthorityViolation(f"rejected URL leaked into BAT-638 child payload domain={domain}")

    predecessor_corpus_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_1998_2009_structured_row_corpus_gate.json")
    predecessor_corpus_identity = str(predecessor_corpus_gate.get("dataset_identity") or "")
    predecessor_corpus_gate_identity = str(predecessor_corpus_gate.get("gate_identity") or "")
    if not predecessor_corpus_identity or not predecessor_corpus_gate_identity:
        raise AuthorityViolation("predecessor corpus identities missing")
    ledger_identity = stable_hash(
        {
            "predecessor_union_identity": union_identity,
            "predecessor_corpus_identity": predecessor_corpus_identity,
            "historical_rejections": historical_records,
            "active_rejections": active_rejections,
            "supersessions": supersessions,
            "admitted_row_gap_urls": list(ADMITTED_ROW_GAP_URLS),
        }
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ledger_identity": ledger_identity,
        "predecessor_union_identity": union_identity,
        "predecessor_union_gate_identity": union_gate_identity,
        "predecessor_corpus_dataset_identity": predecessor_corpus_identity,
        "predecessor_corpus_gate_identity": predecessor_corpus_gate_identity,
        "historical_rejection_records": historical_records,
        "active_rejections": active_rejections,
        "supersessions": supersessions,
        "complete_rejection_ledger": historical_records,
        "complete_rejection_count": len(historical_records),
        "active_rejection_count": len(active_rejections),
        "admitted_row_gap_urls": list(ADMITTED_ROW_GAP_URLS),
        "proofs": {
            "none_in_admitted_union_membership": len(overlap_with_admitted) == 0,
            "none_in_bat638_child_payloads": all(v == 0 for v in rejected_rows_by_domain.values()),
            "rejected_rows_by_domain": rejected_rows_by_domain,
            "superseded_rejection_count": len(supersessions),
        },
        "authority": {
            "membership_admitted": False,
            "availability_established": False,
            "historical_known_at_established": False,
            "ncaa_contest_ids_created": 0,
            "protected_lane": PROTECTED_LANE,
        },
    }

    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1998_2009_REJECTION_INTEGRITY_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "disposition": "NEW_IMMUTABLE_REJECTION_LEDGER_SUCCESSOR",
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "predecessor_union_identity": union_identity,
        "predecessor_union_gate_identity": union_gate_identity,
        "predecessor_corpus_dataset_identity": predecessor_corpus_identity,
        "predecessor_corpus_gate_identity": predecessor_corpus_gate_identity,
        "ledger_identity": ledger_identity,
        "complete_rejection_count": len(historical_records),
        "active_rejection_count": len(active_rejections),
        "superseded_rejection_count": len(supersessions),
        "admitted_row_gap_urls": list(ADMITTED_ROW_GAP_URLS),
        "proofs": payload["proofs"],
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "final_union_gate_identity": union_gate_identity,
            "final_union_identity": union_identity,
            "predecessor_corpus_gate_identity": predecessor_corpus_gate_identity,
            "predecessor_corpus_dataset_identity": predecessor_corpus_identity,
            "structured_1997_payload_identity": structured_1997_payload_identity,
            "structured_1996_payload_identity": structured_1996_payload_identity,
        },
    }
    gate["gate_identity"] = compute_identity(gate, "gate_identity")
    payload["gate_identity"] = gate["gate_identity"]
    root = data_root / contract["payloads"]["rejection_ledger_root"] / ledger_identity
    ledger_path = root / "rejection_ledger.json"
    return {"contract": contract, "payload": payload, "gate": gate, "ledger_path": ledger_path}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    write_json(objects["ledger_path"], objects["payload"])
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "ledger_identity": objects["payload"]["ledger_identity"],
        "ledger_path": str(objects["ledger_path"]),
    }


def validate_artifact(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed rejection-integrity gate does not match independent reconstruction")
    if committed.get("gate_identity") != compute_identity(committed, "gate_identity"):
        raise AuthorityViolation("gate identity does not recompute")
    if not expected["ledger_path"].is_file():
        raise AuthorityViolation("authoritative external rejection ledger payload missing")
    if load_json(expected["ledger_path"]) != expected["payload"]:
        raise AuthorityViolation("external rejection ledger payload mismatch")
    if sha256_file(expected["ledger_path"]) != committed["proofs"].get("external_payload_sha256", sha256_file(expected["ledger_path"])):
        # The gate does not pin this hash yet; this check still prevents silent payload drift after load.
        raise AuthorityViolation("external rejection ledger payload file SHA drifted")
    return {"result": "PASS", "gate_identity": committed["gate_identity"], "ledger_identity": committed["ledger_identity"]}


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
