from __future__ import annotations

"""Build immutable timestamped SEC/A&M availability candidate evidence."""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.sec_availability import (  # noqa: E402
    canonical_bytes,
    extract_candidate_rows,
    sha256_bytes,
    stable_hash,
    utc_now,
)


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write(path: Path, body: bytes) -> None:
    if path.is_file():
        if path.read_bytes() != body:
            raise RuntimeError(f"immutable payload collision: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(body)
        os.replace(temporary, path)
    finally:
        if temporary.is_file():
            temporary.unlink()


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_bytes(row) + b"\n" for row in rows)


def payload_contract(data_root: Path, path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "path": path.relative_to(data_root).as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "rows": len(rows),
    }


def capture_for(record: dict[str, Any]) -> dict[str, Any] | None:
    captures = record.get("captures") or []
    return captures[0] if len(captures) == 1 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=REPO_ROOT / "configs" / "sec_tamu_availability_recovery_contract.json")
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    acquisition_path = args.acquisition_manifest.resolve()
    contract_path = args.contract.resolve()
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if acquisition["contract_sha256"] != sha256_file(contract_path):
        raise RuntimeError("acquisition contract hash mismatch")
    source_config = {source["source_record_id"]: source for source in contract["sources"]}
    candidates: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    source_coverage: list[dict[str, Any]] = []
    for record in acquisition["sources"]:
        source = source_config[record["source_record_id"]]
        if source["route_type"] != "TIMESTAMPED_ARTICLE_TABLE":
            source_coverage.append(
                {
                    "source_record_id": source["source_record_id"],
                    "route_type": source["route_type"],
                    "acquisition_state": record["state"],
                    "candidate_rows": 0,
                    "quarantine_rows": 0,
                }
            )
            continue
        capture = capture_for(record)
        if record["state"] != "CAPTURED" or capture is None:
            finding = {
                "reason": "SOURCE_NOT_CAPTURED",
                "source_record_id": source["source_record_id"],
                "acquisition_state": record["state"],
            }
            quarantine.append(finding)
            source_coverage.append(
                {
                    "source_record_id": source["source_record_id"],
                    "route_type": source["route_type"],
                    "acquisition_state": record["state"],
                    "candidate_rows": 0,
                    "quarantine_rows": 1,
                }
            )
            continue
        source_path = data_root / Path(*capture["immutable_path"].split("/"))
        if sha256_file(source_path) != capture["response_sha256"]:
            raise RuntimeError(f"source hash mismatch: {source['source_record_id']}")
        rows, findings, article = extract_candidate_rows(
            document=source_path.read_text(encoding="utf-8", errors="replace"),
            source=source,
            capture_sha256=capture["response_sha256"],
            captured_at_utc=capture["captured_at_utc"],
        )
        candidates.extend(rows)
        quarantine.extend(findings)
        source_coverage.append(
            {
                "source_record_id": source["source_record_id"],
                "route_type": source["route_type"],
                "acquisition_state": record["state"],
                "candidate_rows": len(rows),
                "quarantine_rows": len(findings),
                "article": article,
            }
        )
    candidates.sort(
        key=lambda row: (
            row["season"],
            row["target_game_date"],
            row["report_version"],
            row["player_name_normalized"],
            row["availability_candidate_id"],
        )
    )
    quarantine.sort(key=lambda row: (row["source_record_id"], row["reason"], stable_hash(row)))
    source_coverage.sort(key=lambda row: row["source_record_id"])
    core = {
        "schema_version": "1.0.0",
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256_file(contract_path),
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "domain": "SEC_TAMU_TIMESTAMPED_AVAILABILITY_EVIDENCE",
        "grain": "SOURCE_REPORT_VERSION_PLAYER_ROW",
        "acquisition_identity": acquisition["acquisition_identity"],
        "acquisition_manifest_sha256": sha256_file(acquisition_path),
        "producer_sha256": sha256_file(Path(__file__)),
        "candidate_row_hashes": [stable_hash(row) for row in candidates],
        "quarantine_row_hashes": [stable_hash(row) for row in quarantine],
        "source_coverage": source_coverage,
        "candidate_rows": len(candidates),
        "quarantine_rows": len(quarantine),
        "seasons": sorted({row["season"] for row in candidates}),
        "games": sorted({row["game_label"] for row in candidates}),
        "game_seasons": sorted({f"{row['season']}::{row['game_label']}" for row in candidates}),
        "report_sources": sorted({row["source_record_id"] for row in candidates}),
        "status_counts": dict(sorted(Counter(row["status"] for row in candidates).items())),
        "chronology_pass_rows": sum(bool(row["chronology_pass"]) for row in candidates),
        "authority": {
            "candidate_layer": True,
            "canonical_admission": False,
            "pit_state_admission": False,
            "training_feature_admission": False,
            "protected_evaluation_admission": False,
            "name_only_player_merge": False,
            "absence_means_available": False,
        },
    }
    identity = stable_hash(core)
    output_root = data_root / "quarantine" / "historical_known_at" / "sha256" / identity / "sec_tamu_availability"
    candidates_path = output_root / "availability_candidates.jsonl"
    quarantine_path = output_root / "availability_quarantine.jsonl"
    atomic_write(candidates_path, jsonl_bytes(candidates))
    atomic_write(quarantine_path, jsonl_bytes(quarantine))
    payloads = {
        "candidates": payload_contract(data_root, candidates_path, candidates),
        "quarantine": payload_contract(data_root, quarantine_path, quarantine),
    }
    manifest = {
        **core,
        "dataset_identity": identity,
        "issued_at_utc": utc_now(),
        "payloads": payloads,
    }
    manifest_path = data_root / "manifests" / "historical_known_at" / "sha256" / identity / "sec_tamu_availability_candidate_manifest.json"
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        stable_existing = {key: value for key, value in existing.items() if key not in {"issued_at_utc", "payloads", "dataset_identity"}}
        if stable_existing != core or existing.get("dataset_identity") != identity or existing.get("payloads") != payloads:
            raise RuntimeError(f"immutable candidate manifest collision: {manifest_path}")
        manifest = existing
    else:
        atomic_write(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(
        json.dumps(
            {
                "dataset_identity": identity,
                "manifest_path": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "candidate_rows": len(candidates),
                "quarantine_rows": len(quarantine),
                "seasons": core["seasons"],
                "games": core["games"],
                "status_counts": core["status_counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
