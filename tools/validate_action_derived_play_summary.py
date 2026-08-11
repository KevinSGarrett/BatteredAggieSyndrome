from __future__ import annotations

"""Independently validate and replay the POST-SUBTASK-175 candidate layer."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.action_play_summary import (  # noqa: E402
    SEMANTIC_PAIR_FIELDS,
    action_record,
    stable_hash,
)


EXPECTED_DATASET_ID = "9ea078e06300ee2d6fe2c50857986fd29a46d1d3a3513b28cca74bd499ae8451"
EXPECTED_MANIFEST_SHA256 = "f48cac4cd3c42adaa1cd59ee70b96df9ca6fe372808fcd614e75a6de27c04429"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def immutable_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != payload:
        raise RuntimeError(f"immutable validation report collision: {path}")
    if not path.exists():
        path.write_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    root = args.data_root.resolve()
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    checks: list[str] = []

    def check(name: str, condition: bool) -> None:
        if not condition:
            raise RuntimeError(f"validation failed: {name}")
        checks.append(name)

    def require(name: str, condition: bool) -> None:
        if not condition:
            raise RuntimeError(f"validation failed: {name}")

    source = config["source_dataset"]
    manifest_path = (
        root / "manifests" / "historical_known_at" / "sha256" / EXPECTED_DATASET_ID
        / "action_derived_play_summary_reconciliation.json"
    )
    check("manifest_exists", manifest_path.is_file())
    check("manifest_sha256", sha256_file(manifest_path) == EXPECTED_MANIFEST_SHA256)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    check("dataset_identity", manifest["dataset_identity"] == EXPECTED_DATASET_ID)
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-175")
    check("artifact_type", manifest["artifact_type"] == "TAMU_ACTION_DERIVED_PLAY_SUMMARY_RECONCILIATION_MANIFEST")

    source_manifest = root / Path(*source["manifest_relative_path"].split("/"))
    source_root = root / Path(*source["payload_root_relative_path"].split("/"))
    actions_path = source_root / Path(*source["actions_relative_path"].split("/"))
    plays_path = source_root / Path(*source["plays_relative_path"].split("/"))
    check("source_manifest_sha256", sha256_file(source_manifest) == source["manifest_sha256"])
    check("source_actions_sha256", sha256_file(actions_path) == source["actions_sha256"])
    check("source_plays_sha256", sha256_file(plays_path) == source["plays_sha256"])
    actions = pq.ParquetFile(actions_path).read().to_pylist()
    plays = pq.ParquetFile(plays_path).read().to_pylist()
    check("source_action_rows", len(actions) == 147381)
    check("source_play_rows", len(plays) == 41453)
    native_games = {str(row["wmt_game_id"]) for row in plays}
    action_only = [row for row in actions if str(row["wmt_game_id"]) not in native_games]
    check("native_play_games", len(native_games) == 109)
    check("action_only_games", len({str(row["wmt_game_id"]) for row in action_only}) == 50)
    check("action_only_rows", len(action_only) == 48598)

    source_by_record_id = {row["record_id"]: row for row in action_only}
    check("source_record_identity_unique", len(source_by_record_id) == len(action_only))
    groups: dict[tuple[str, int | None, int | None], dict[str, dict[str, Any]]] = defaultdict(dict)
    non_summary_rows = 0
    for row in action_only:
        action = action_record(row)
        if action.get("play_action_type") != "play":
            non_summary_rows += 1
            continue
        key = (str(row["wmt_game_id"]), action.get("period_number"), action.get("play_number"))
        subtype = str(action.get("play_action_sub_type"))
        require(f"unique_pair_subtype:{row['record_id']}", subtype not in groups[key])
        groups[key][subtype] = row
    check("summary_groups", len(groups) == 11599)
    check("summary_action_rows", sum(len(pair) for pair in groups.values()) == 23198)
    check("non_summary_action_rows", non_summary_rows == 25400)

    candidates: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for payload in manifest["payloads"]:
        path = root / Path(*payload["path"].split("/"))
        check(f"payload_exists:{payload['season']}:{payload['role']}", path.is_file())
        check(f"payload_sha256:{payload['season']}:{payload['role']}", sha256_file(path) == payload["sha256"])
        check(f"payload_bytes:{payload['season']}:{payload['role']}", path.stat().st_size == int(payload["bytes"]))
        table = pq.ParquetFile(path).read()
        check(f"payload_rows:{payload['season']}:{payload['role']}", table.num_rows == int(payload["rows"]))
        rows = table.to_pylist()
        if payload["role"] == "ACTION_DERIVED_PLAY_SUMMARY_CANDIDATES":
            candidates.extend(rows)
        elif payload["role"] == "ACTION_PLAY_SUMMARY_EXCLUSIONS":
            exclusions.extend(rows)
        else:
            raise RuntimeError(f"unknown payload role: {payload['role']}")

    check("payload_count", len(manifest["payloads"]) == 10)
    check("candidate_rows", len(candidates) == 11529)
    check("excluded_groups", len(exclusions) == 70)
    check("candidate_games", len({row["wmt_game_id"] for row in candidates}) == 50)
    check("candidate_id_unique", len({row["candidate_id"] for row in candidates}) == len(candidates))
    candidate_keys = {(row["wmt_game_id"], row["period_number"], row["play_number"]) for row in candidates}
    exclusion_keys = {(row["wmt_game_id"], row["period_number"], row["play_number"]) for row in exclusions}
    check("candidate_key_unique", len(candidate_keys) == len(candidates))
    check("exclusion_key_unique", len(exclusion_keys) == len(exclusions))
    check("candidate_exclusion_disjoint", candidate_keys.isdisjoint(exclusion_keys))
    check("full_summary_group_coverage", candidate_keys | exclusion_keys == set(groups))
    check("native_games_excluded", not ({row["wmt_game_id"] for row in candidates + exclusions} & native_games))

    for row in candidates:
        key = (row["wmt_game_id"], row["period_number"], row["play_number"])
        pair = groups[key]
        require(f"pair_complete:{row['candidate_id']}", set(pair) == {"start", "end"})
        source_start = source_by_record_id[row["source_start"]["record_id"]]
        source_end = source_by_record_id[row["source_end"]["record_id"]]
        start = action_record(source_start)
        end = action_record(source_end)
        require(f"start_pointer:{row['candidate_id']}", row["source_start"]["json_pointer"] == source_start["source_json_pointer"])
        require(f"end_pointer:{row['candidate_id']}", row["source_end"]["json_pointer"] == source_end["source_json_pointer"])
        require(f"start_evidence:{row['candidate_id']}", row["source_start"]["record_evidence_sha256"] == source_start["source_record_evidence_sha256"])
        require(f"end_evidence:{row['candidate_id']}", row["source_end"]["record_evidence_sha256"] == source_end["source_record_evidence_sha256"])
        require(f"positive_play_number:{row['candidate_id']}", int(start["play_number"]) > 0)
        require(f"nonempty_text:{row['candidate_id']}", isinstance(start["play_by_play_text"], str) and bool(start["play_by_play_text"].strip()))
        require(f"drive_present:{row['candidate_id']}", start["game_drive_number"] is not None)
        require(f"pair_link:{row['candidate_id']}", str(end["play_by_play_id"]) == str(start["id"]))
        require(f"pair_semantics:{row['candidate_id']}", all(start.get(field) == end.get(field) for field in SEMANTIC_PAIR_FIELDS))
        require(f"play_text_exact:{row['candidate_id']}", row["play_text"] == start["play_by_play_text"].strip())
        require(f"drive_exact:{row['candidate_id']}", row["drive_number"] == int(start["game_drive_number"]))
        require(f"candidate_no_native_claim:{row['candidate_id']}", row["native_play_collection_present"] is False)
        require(f"candidate_authority_closed:{row['candidate_id']}", all(row[field] is False for field in (
            "historical_known_at_eligible", "canonical_admission", "pit_state_admission",
            "feature_or_training_admission", "protected_evaluation_admission",
            "forecast_or_publication_admission",
        )))
        lineage = row.pop("row_lineage_sha256")
        require(f"candidate_lineage:{row['candidate_id']}", stable_hash(row) == lineage)
        row["row_lineage_sha256"] = lineage
    check("candidate_row_full_scan", True)

    recomputed_reasons: Counter[str] = Counter()
    for row in exclusions:
        key = (row["wmt_game_id"], row["period_number"], row["play_number"])
        pair = groups[key]
        start_row = pair.get("start")
        end_row = pair.get("end")
        expected: list[str] = []
        if start_row is None:
            expected.append("START_RECORD_MISSING")
        if end_row is None:
            expected.append("END_RECORD_MISSING")
        if start_row is not None:
            start = action_record(start_row)
            if not isinstance(start.get("play_by_play_text"), str) or not start["play_by_play_text"].strip():
                expected.append("PLAY_TEXT_MISSING_OR_EMPTY")
            try:
                if int(start.get("play_number")) <= 0:
                    expected.append("PLAY_NUMBER_NOT_POSITIVE")
            except (TypeError, ValueError):
                expected.append("PLAY_NUMBER_NOT_POSITIVE")
            if start.get("game_drive_number") is None:
                expected.append("DRIVE_NUMBER_MISSING")
        require(f"exclusion_reasons:{key}", row["reason_codes"] == expected)
        recomputed_reasons.update(expected)
        require(f"exclusion_authority_closed:{key}", row["feature_or_training_admission"] is False and row["protected_evaluation_admission"] is False)
        lineage = row.pop("exclusion_lineage_sha256")
        require(f"exclusion_lineage:{key}", stable_hash(row) == lineage)
        row["exclusion_lineage_sha256"] = lineage
    check("exclusion_row_full_scan", True)
    check("reason_counts", dict(sorted(recomputed_reasons.items())) == {"DRIVE_NUMBER_MISSING": 70, "PLAY_NUMBER_NOT_POSITIVE": 50})
    check("manifest_authority_closed", all(value is False for key, value in manifest["authority"].items() if key != "candidate_only"))
    check("candidate_only_true", manifest["authority"]["candidate_only"] is True)
    check("no_training_payload_written", not (root / "training" / EXPECTED_DATASET_ID).exists())

    # Keep the rebuild path short enough for default Windows MAX_PATH while
    # retaining it under the standardized external validation root.
    rebuild_root = root / "validation" / "p175r"
    allowed_parent = (root / "validation").resolve()
    check("rebuild_path_bounded", rebuild_root.resolve().parent == allowed_parent)
    if rebuild_root.exists():
        raise RuntimeError(f"stale deterministic rebuild root requires review: {rebuild_root}")
    command = [
        sys.executable,
        str(repo / "tools" / "build_action_derived_play_summary.py"),
        "--repo-root", str(repo),
        "--data-root", str(root),
        "--output-data-root", str(rebuild_root),
        "--config", str(args.config.resolve()),
        "--issued-at-utc", manifest["issued_at_utc"],
    ]
    completed = subprocess.run(command, cwd=repo, text=True, capture_output=True, check=False)
    if completed.returncode:
        detail = (completed.stdout + "\n" + completed.stderr).strip()[-4000:]
        raise RuntimeError(f"validation failed: rebuild_process: {detail}")
    checks.append("rebuild_process")
    rebuilt_manifest = (
        rebuild_root / "manifests" / "historical_known_at" / "sha256" / EXPECTED_DATASET_ID
        / "action_derived_play_summary_reconciliation.json"
    )
    check("rebuild_manifest_byte_identical", rebuilt_manifest.read_bytes() == manifest_path.read_bytes())
    compared = 1
    for payload in manifest["payloads"]:
        original = root / Path(*payload["path"].split("/"))
        rebuilt = rebuild_root / Path(*payload["path"].split("/"))
        check(f"rebuild_payload_byte_identical:{payload['season']}:{payload['role']}", rebuilt.read_bytes() == original.read_bytes())
        compared += 1
    shutil.rmtree(rebuild_root)
    check("rebuild_cleanup", not rebuild_root.exists())

    report = {
        "schema_version": "1.0.0",
        "decision_unit": "POST-SUBTASK-175",
        "status": "PASS",
        "dataset_identity": EXPECTED_DATASET_ID,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "checks_passed": len(checks),
        "checks": checks,
        "population": manifest["population"],
        "source_population": manifest["source_population"],
        "payloads_compared_byte_identical": compared,
        "target_and_future_leakage_gate": {
            "historical_known_at_eligible": False,
            "feature_or_training_admission": False,
            "protected_evaluation_admission": False,
            "target_game_state_present_only_as_postgame_candidate_evidence": True,
            "target_game_state_allowed_in_pregame_features": False,
        },
        "cleanup": {
            "deterministic_rebuild_removed": True,
            "reconstructible_files_remaining": 0,
        },
    }
    report_path = args.report or (root / "validation" / "POST-SUBTASK-175" / "action_derived_play_summary_validation.json")
    immutable_json(report_path.resolve(), report)
    print(json.dumps({
        "status": "PASS",
        "checks_passed": len(checks),
        "dataset_identity": EXPECTED_DATASET_ID,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "report": str(report_path.resolve()),
        "report_sha256": sha256_file(report_path.resolve()),
        "payloads_compared_byte_identical": compared,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
