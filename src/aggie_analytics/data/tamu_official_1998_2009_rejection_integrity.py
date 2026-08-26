"""Immutable rejection-integrity successor for 1998-2009 official SRC-014 evidence."""

from __future__ import annotations

import json
import os
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
CONTRACT_ID = "BAT-XXX-TAMU-OFFICIAL-1998-2009-REJECTION-INTEGRITY-V1"
DECISION_UNIT = "POST-TASK-SRC014-1998-2009-REJECTION-INTEGRITY-001"
JIRA_KEY = "BAT-XXX"
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
PINNED_BAT633_GATE_IDENTITY = "a8d0a6594cfdf4557e2ef743983d64531474410fde6795fe4400441d11555403"
PINNED_BAT637_GATE_IDENTITY = "c1d2220943342e02bd55efdac6bf3a4992f5fcd4a00059e94cc21ea56581db4a"
PINNED_BAT638_GATE_IDENTITY = "a251b95714bed59de8aa593fe1466fce603858b30108c447c53fe6f3b8ee4e54"
PINNED_BAT638_DATASET_IDENTITY = "0ff650b1b691299d2b14fd252b8b938a9afe1d02cfd1eefdcd4d53bde2947ca8"
ADMITTED_ROW_GAP_URLS = (
    "https://files.12thman.com/history/football/stats/2006-2007/texas.htm",
    "https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _build_record(
    *,
    item: Mapping[str, Any],
    origin_issue: str,
    origin_gate_identity: str,
    source_season: int | None,
    rejection_source: str,
) -> dict[str, Any]:
    url = str(item.get("url") or "")
    if not url:
        raise AuthorityViolation("rejection entry missing URL")
    return {
        "url": url,
        "origin_issue": origin_issue,
        "origin_gate_identity": origin_gate_identity,
        "origin_decision_unit": str(item.get("decision_unit") or ""),
        "source_season": source_season,
        "source_url": url,
        "source_sha256": str(item.get("source_sha256") or "") or None,
        "match_status": str(item.get("canonical_game_match_status") or "") or None,
        "rejection_reason": str(item.get("conflict_status") or item.get("canonical_game_match_status") or "UNMATCHED_OR_REJECTED"),
        "rejection_source": rejection_source,
        "capture_disposition": "REJECTED_URL_RETAINED_ONLY",
        "membership_admitted": False,
        "availability": "NOT_ESTABLISHED",
        "availability_claim": False,
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_id": None,
    }


def _collect_rejections(
    *,
    g633: Mapping[str, Any],
    g637: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in g633.get("preserved_rejections") or []:
        rows.append(
            _build_record(
                item=item,
                origin_issue="BAT-633",
                origin_gate_identity=PINNED_BAT633_GATE_IDENTITY,
                source_season=None,
                rejection_source="BAT-633.preserved_rejections",
            )
        )
    for item in g633.get("rejected_official_1999_games") or []:
        rows.append(
            _build_record(
                item=item,
                origin_issue="BAT-633",
                origin_gate_identity=PINNED_BAT633_GATE_IDENTITY,
                source_season=1999,
                rejection_source="BAT-633.rejected_official_1999_games",
            )
        )
    for item in g637.get("rejected_official_1998_games") or []:
        rows.append(
            _build_record(
                item=item,
                origin_issue="BAT-637",
                origin_gate_identity=PINNED_BAT637_GATE_IDENTITY,
                source_season=1998,
                rejection_source="BAT-637.rejected_official_1998_games",
            )
        )
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        url = row["url"]
        if url in unique:
            raise AuthorityViolation(f"duplicate rejected URL in reconstructed ledger: {url}")
        unique[url] = row
    return sorted(unique.values(), key=lambda row: row["url"])


def _rejecteds_absent_from_corpus(
    *,
    data_root: Path,
    rejected_urls: set[str],
) -> dict[str, int]:
    root = data_root / "features/tamu_official_1998_2009_structured_row_corpus/sha256" / PINNED_BAT638_DATASET_IDENTITY
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
    g633 = load_json(repo_root / "artifacts/data_lake/tamu_official_gamebook_union_1999_expanded_gate.json")
    g637 = load_json(repo_root / "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json")
    g638 = load_json(repo_root / "artifacts/data_lake/tamu_official_1998_2009_structured_row_corpus_gate.json")
    if g633.get("gate_identity") != PINNED_BAT633_GATE_IDENTITY:
        raise AuthorityViolation("BAT-633 gate identity drifted")
    if g637.get("gate_identity") != PINNED_BAT637_GATE_IDENTITY:
        raise AuthorityViolation("BAT-637 gate identity drifted")
    if g638.get("gate_identity") != PINNED_BAT638_GATE_IDENTITY:
        raise AuthorityViolation("BAT-638 gate identity drifted")
    if g638.get("dataset_identity") != PINNED_BAT638_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-638 dataset identity drifted")

    ledger = _collect_rejections(g633=g633, g637=g637)
    rejected_urls = {item["url"] for item in ledger}
    if len(ledger) != 17:
        raise AuthorityViolation("complete rejection set must contain exactly 17 unique URLs")

    admitted_urls = {str(item.get("url") or "") for item in g637.get("enriched_official_games") or []}
    overlap_with_admitted = sorted(rejected_urls & admitted_urls)
    if overlap_with_admitted:
        raise AuthorityViolation("rejected URLs overlap admitted membership")

    for gap_url in ADMITTED_ROW_GAP_URLS:
        if gap_url in rejected_urls:
            raise AuthorityViolation("admitted row-gap URL incorrectly classified as rejected")
        if gap_url not in admitted_urls:
            raise AuthorityViolation("admitted row-gap URL missing from admitted union membership")

    rejected_rows_by_domain = _rejecteds_absent_from_corpus(data_root=data_root, rejected_urls=rejected_urls)
    for domain, count in rejected_rows_by_domain.items():
        if count != 0:
            raise AuthorityViolation(f"rejected URL leaked into BAT-638 child payload domain={domain}")

    dropped_1999_urls = sorted(
        {str(item.get("url") or "") for item in g633.get("rejected_official_1999_games") or []}
        - {str(item.get("url") or "") for item in g637.get("preserved_rejections") or []}
        - {str(item.get("url") or "") for item in g637.get("rejected_official_1998_games") or []}
    )
    if len(dropped_1999_urls) != 5:
        raise AuthorityViolation("expected exactly five BAT-633/1999 URLs dropped from BAT-637 successor surfaces")

    predecessor_union_identity = str(g637.get("union_identity") or "")
    predecessor_corpus_identity = str(g638.get("dataset_identity") or "")
    ledger_identity = stable_hash(
        {
            "predecessor_union_identity": predecessor_union_identity,
            "predecessor_corpus_identity": predecessor_corpus_identity,
            "rejected_urls": sorted(rejected_urls),
            "ledger": ledger,
            "admitted_row_gap_urls": list(ADMITTED_ROW_GAP_URLS),
        }
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ledger_identity": ledger_identity,
        "predecessor_union_identity": predecessor_union_identity,
        "predecessor_union_gate_identity": PINNED_BAT637_GATE_IDENTITY,
        "predecessor_corpus_dataset_identity": predecessor_corpus_identity,
        "predecessor_corpus_gate_identity": PINNED_BAT638_GATE_IDENTITY,
        "complete_rejection_ledger": ledger,
        "complete_rejection_count": len(ledger),
        "admitted_row_gap_urls": list(ADMITTED_ROW_GAP_URLS),
        "proofs": {
            "none_in_admitted_union_membership": len(overlap_with_admitted) == 0,
            "none_in_bat638_child_payloads": all(v == 0 for v in rejected_rows_by_domain.values()),
            "rejected_rows_by_domain": rejected_rows_by_domain,
            "dropped_bat633_1999_urls_in_bat637_surfaces": dropped_1999_urls,
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
        "predecessor_union_identity": predecessor_union_identity,
        "predecessor_union_gate_identity": PINNED_BAT637_GATE_IDENTITY,
        "predecessor_corpus_dataset_identity": predecessor_corpus_identity,
        "predecessor_corpus_gate_identity": PINNED_BAT638_GATE_IDENTITY,
        "ledger_identity": ledger_identity,
        "complete_rejection_count": len(ledger),
        "admitted_row_gap_urls": list(ADMITTED_ROW_GAP_URLS),
        "proofs": payload["proofs"],
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "bat633_gate_identity": PINNED_BAT633_GATE_IDENTITY,
            "bat637_gate_identity": PINNED_BAT637_GATE_IDENTITY,
            "bat638_gate_identity": PINNED_BAT638_GATE_IDENTITY,
            "bat638_dataset_identity": PINNED_BAT638_DATASET_IDENTITY,
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
