from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.openai_assist.controller import AssistiveController  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verified(path: Path, expected_sha256: str) -> Path:
    if not path.is_file():
        raise SystemExit(f"required external gamebook artifact is absent: {path}")
    actual = _sha(path)
    if actual != expected_sha256:
        raise SystemExit(f"gamebook artifact hash mismatch: {path} expected={expected_sha256} actual={actual}")
    return path


def _rows(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pyarrow is required to prepare the gamebook schema-mapping gold") from exc
    return pq.ParquetFile(path).read().to_pylist()


def _sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["season"], str(row["wmt_game_id"]), row["record_ordinal"], row["record_id"])


def _selected(row: dict[str, Any]) -> dict[str, Any]:
    return json.loads(row["selected_fields_json"])


def _nested(row: dict[str, Any], container: str) -> dict[str, Any]:
    value = json.loads(row["normalized_record_json"]).get(container)
    if not isinstance(value, dict):
        raise SystemExit(f"record lacks expected nested {container} object: {row['record_id']}")
    return value


def _expected(role: str, relation: str, destination: str) -> list[dict[str, Any]]:
    values: list[tuple[str, Any]] = [
        ("record_role", role),
        ("schema_relation", relation),
        ("mapping_destination", destination),
        ("canonical_authority", False),
        ("pit_authority", False),
        ("training_feature_authority", False),
    ]
    return [
        {"field": field, "value": value, "status": "SUPPORTED", "evidence_locators": ["evidence:1"]}
        for field, value in values
    ]


def _case(
    *,
    row: dict[str, Any],
    source_domain: str,
    nested_key: str,
    reference_keys: list[str],
    explicit_play_games: set[str],
    case_id: str,
    expected: list[dict[str, Any]],
    dataset_identity: str,
    payload_path: Path,
) -> dict[str, Any]:
    selected = _selected(row)
    nested_keys = sorted(_nested(row, nested_key))
    evidence = {
        "dataset_identity": dataset_identity,
        "source_domain": source_domain,
        "nested_container_key": nested_key,
        "nested_schema_keys": nested_keys,
        "reference_play_nested_schema_keys": reference_keys,
        "nested_schema_matches_reference_play_schema": nested_keys == reference_keys,
        "explicit_play_domain_present_for_game": str(row["wmt_game_id"]) in explicit_play_games,
        "season": row["season"],
        "wmt_game_id": str(row["wmt_game_id"]),
        "boxscore_id": str(row["boxscore_id"]),
        "source_json_pointer": row["source_json_pointer"],
        "source_response_sha256": row["source_response_sha256"],
        "source_record_sha256": row["source_record_sha256"],
        "source_record_evidence_sha256": row["source_record_evidence_sha256"],
        "selected_fields": {
            key: selected.get(key)
            for key in [
                "action_type",
                "action_sub_type",
                "play_id",
                "play_number",
                "play_text",
                "drive_number",
                "period_number",
                "down",
                "yards_to_go",
                "yard_line",
                "yards",
                "scoring_play",
            ]
        },
        "historical_known_at_state": row["historical_known_at_state"],
        "admission_state": row["admission_state"],
        "authority": "REVIEW_ONLY_NO_CANONICAL_PIT_TRAINING_OR_PROTECTED_AUTHORITY",
    }
    excerpt = json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    capture_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
    return {
        "case_id": case_id,
        "category": "gamebook_action_play_schema_mapping",
        "domains": ["official_structured_gamebook_equivalent", "schema_drift", source_domain],
        "instruction": "Classify this single structured record under the pinned action/play mapping rules.",
        "season": row["season"],
        "wmt_game_id": str(row["wmt_game_id"]),
        "source_url": payload_path.resolve().as_uri(),
        "source_payload_sha256": _sha(payload_path),
        "source_record_sha256": row["source_record_sha256"],
        "source_record_evidence_sha256": row["source_record_evidence_sha256"],
        "source_capture_sha256": capture_sha256,
        "source_locator": "evidence:1",
        "source_excerpt": excerpt,
        "historical_publication_time_state": row["historical_known_at_state"],
        "canonical_or_pit_admission": False,
        "training_feature_admission": False,
        "expected_facts": expected,
    }


def main() -> int:
    config = json.loads((ROOT / "configs" / "openai_gamebook_schema_mapping.json").read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    data_root = controller.store.root.parent
    source = config["source"]
    manifest_path = _verified(data_root / source["manifest_relative_path"], source["manifest_sha256"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_identity") != source["dataset_identity"]:
        raise SystemExit("gamebook source dataset identity mismatch")
    if manifest.get("honesty_boundary", {}).get("canonical_data_admitted") is not False:
        raise SystemExit("gamebook source honesty boundary unexpectedly permits canonical data")
    if manifest.get("honesty_boundary", {}).get("pit_state_admitted") is not False:
        raise SystemExit("gamebook source honesty boundary unexpectedly permits PIT state")

    payload_root = data_root / source["payload_root_relative_path"]
    action_spec = source["actions_payload"]
    play_spec = source["plays_payload"]
    actions_path = _verified(payload_root / action_spec["relative_path"], action_spec["sha256"])
    plays_path = _verified(payload_root / play_spec["relative_path"], play_spec["sha256"])
    actions = _rows(actions_path)
    plays = _rows(plays_path)
    if len(actions) != action_spec["rows"] or len(plays) != play_spec["rows"]:
        raise SystemExit("gamebook payload row count mismatch")

    actions.sort(key=_sort_key)
    plays.sort(key=_sort_key)
    explicit_play_games = {str(row["wmt_game_id"]) for row in plays}
    reference = next(
        row
        for row in plays
        if row["season"] == config["selection"]["native_play_comparator_season"]
        and isinstance(_selected(row).get("play_text"), str)
        and bool(_selected(row)["play_text"].strip())
    )
    reference_keys = sorted(_nested(reference, "play"))

    selected_action_rows: list[dict[str, Any]] = []
    for season in config["selection"]["action_candidate_seasons"]:
        candidates = []
        for row in actions:
            if row["season"] != season or str(row["wmt_game_id"]) in explicit_play_games:
                continue
            values = _selected(row)
            if (
                isinstance(values.get("play_text"), str)
                and bool(values["play_text"].strip())
                and isinstance(values.get("play_number"), int)
                and values["play_number"] > 0
                and values.get("drive_number") is not None
            ):
                candidates.append(row)
        if not candidates:
            raise SystemExit(f"no action-domain play-semantic candidate for season {season}")
        chosen = candidates[0]
        if sorted(_nested(chosen, "action")) != reference_keys:
            raise SystemExit(f"action/play nested schema mismatch for configured positive season {season}")
        selected_action_rows.append(chosen)

    first_game = str(selected_action_rows[0]["wmt_game_id"])
    non_play = next(
        row
        for row in actions
        if str(row["wmt_game_id"]) == first_game
        and (not _selected(row).get("play_text") or not _selected(row).get("play_number"))
    )

    gold: list[dict[str, Any]] = []
    for row in selected_action_rows:
        gold.append(
            _case(
                row=row,
                source_domain="actions",
                nested_key="action",
                reference_keys=reference_keys,
                explicit_play_games=explicit_play_games,
                case_id=f"ACTION_PLAY_{row['season']}",
                expected=_expected(
                    "PLAY_SEMANTIC_CANDIDATE",
                    "ACTION_SCHEMA_MATCHES_REFERENCE_PLAY_SCHEMA",
                    "PLAY_CANDIDATE_REVIEW",
                ),
                dataset_identity=source["dataset_identity"],
                payload_path=actions_path,
            )
        )
    gold.append(
        _case(
            row=non_play,
            source_domain="actions",
            nested_key="action",
            reference_keys=reference_keys,
            explicit_play_games=explicit_play_games,
            case_id="ACTION_NON_PLAY_2013",
            expected=_expected("NON_PLAY_ACTION", "NOT_A_PLAY_SCHEMA_CANDIDATE", "KEEP_ACTION_ONLY"),
            dataset_identity=source["dataset_identity"],
            payload_path=actions_path,
        )
    )
    gold.append(
        _case(
            row=reference,
            source_domain="plays",
            nested_key="play",
            reference_keys=reference_keys,
            explicit_play_games=explicit_play_games,
            case_id="NATIVE_PLAY_2018",
            expected=_expected("NATIVE_PLAY_RECORD", "NATIVE_PLAY_SCHEMA", "KEEP_NATIVE_PLAY"),
            dataset_identity=source["dataset_identity"],
            payload_path=plays_path,
        )
    )
    gold.sort(key=lambda row: row["case_id"])
    case_ids = {row["case_id"] for row in gold}
    routed_ids = {case_id for route in config["routes"] for case_id in route["case_ids"]}
    if routed_ids - case_ids:
        raise SystemExit(f"route references absent gold cases: {sorted(routed_ids - case_ids)}")

    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for row in gold
    ).encode("utf-8")
    artifact = controller.store.put_bytes("evals", payload, suffix=".gamebook-schema-mapping-gold.jsonl")
    missing_play_games = {str(row["wmt_game_id"]) for row in actions} - explicit_play_games
    season_counts = Counter(row["season"] for row in actions if str(row["wmt_game_id"]) in missing_play_games)
    manifest_artifact = controller.store.put_json(
        "evals",
        {
            "schema_version": 1,
            "artifact_type": "openai_gamebook_action_play_schema_mapping_gold",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "source_dataset_identity": source["dataset_identity"],
            "source_manifest_sha256": source["manifest_sha256"],
            "actions_payload_sha256": action_spec["sha256"],
            "plays_payload_sha256": play_spec["sha256"],
            "gold_sha256": artifact.sha256,
            "gold_bytes": artifact.bytes,
            "case_ids": sorted(case_ids),
            "sample_count": len(gold),
            "planned_jobs": sum(len(route["case_ids"]) for route in config["routes"]),
            "missing_explicit_play_domain_games_with_actions": len(missing_play_games),
            "missing_play_action_rows_by_season": {str(k): v for k, v in sorted(season_counts.items())},
            "reference_play_nested_schema_sha256": hashlib.sha256(
                json.dumps(reference_keys, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "historical_publication_time_state": "UNKNOWN",
            "canonical_or_pit_admission": False,
            "training_feature_admission": False,
            "raw_source_and_excerpts_outside_git": True,
            "final_disposition": "SHADOW_GOLD_READY_FOR_GOVERNED_COMPARISON",
        },
    )
    print(
        json.dumps(
            {
                "gold_path": str(artifact.path),
                "gold_sha256": artifact.sha256,
                "manifest_path": str(manifest_artifact.path),
                "manifest_sha256": manifest_artifact.sha256,
                "samples": len(gold),
                "planned_jobs": sum(len(route["case_ids"]) for route in config["routes"]),
                "missing_explicit_play_domain_games_with_actions": len(missing_play_games),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
