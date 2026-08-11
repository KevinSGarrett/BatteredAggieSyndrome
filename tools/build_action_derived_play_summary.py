from __future__ import annotations

"""Build immutable action-derived play-summary candidates for WMT action-only games."""

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.action_play_summary import (  # noqa: E402
    POLICY_VERSION,
    action_record,
    classify_summary_pair,
    stable_hash,
    summary_group_key,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ordered_hash(values: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def immutable_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable JSON collision: {path}")
        return
    path.write_bytes(payload)


def immutable_parquet(path: Path, rows: list[dict[str, Any]]) -> pa.Table:
    if not rows:
        raise RuntimeError(f"refusing to write empty payload: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".candidate.tmp")
    if temporary.exists():
        temporary.unlink()
    table = pa.Table.from_pylist(rows)
    pq.write_table(
        table,
        temporary,
        compression="zstd",
        compression_level=9,
        use_dictionary=True,
        write_statistics=True,
        data_page_version="1.0",
    )
    if path.exists():
        if path.read_bytes() != temporary.read_bytes():
            temporary.unlink()
            raise RuntimeError(f"immutable Parquet collision: {path}")
        temporary.unlink()
    else:
        temporary.replace(path)
    return table


def read_parquet(path: Path, expected_sha: str, expected_rows: int) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    if sha256_file(path) != expected_sha:
        raise RuntimeError(f"source payload SHA-256 drift: {path}")
    table = pq.ParquetFile(path).read()
    if table.num_rows != expected_rows:
        raise RuntimeError(f"source payload row-count drift: {path}")
    return table.to_pylist()


def payload_contract(path: Path, root: Path, table: pa.Table, *, role: str, season: int) -> dict[str, Any]:
    return {
        "role": role,
        "season": season,
        "rows": table.num_rows,
        "columns": table.num_columns,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "path": path.relative_to(root).as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-data-root", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--issued-at-utc", required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    output_data_root = (args.output_data_root or data_root).resolve()
    config_path = args.config.resolve()
    if repo_root not in config_path.parents:
        raise RuntimeError("contract must be versioned inside the repository")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["decision_unit"] != "POST-SUBTASK-175":
        raise RuntimeError("decision unit drift")
    seasons = [int(value) for value in config["selected_seasons"]]
    if seasons != [2013, 2014, 2015, 2016, 2017]:
        raise RuntimeError("selected season scope drift")

    source = config["source_dataset"]
    source_manifest_path = data_root / Path(*source["manifest_relative_path"].split("/"))
    if sha256_file(source_manifest_path) != source["manifest_sha256"]:
        raise RuntimeError("source manifest SHA-256 drift")
    source_payload_root = data_root / Path(*source["payload_root_relative_path"].split("/"))
    actions_path = source_payload_root / Path(*source["actions_relative_path"].split("/"))
    plays_path = source_payload_root / Path(*source["plays_relative_path"].split("/"))
    actions = read_parquet(actions_path, source["actions_sha256"], int(source["actions_rows"]))
    plays = read_parquet(plays_path, source["plays_sha256"], int(source["plays_rows"]))

    native_play_games = {str(row["wmt_game_id"]) for row in plays}
    action_only = [
        row for row in actions
        if str(row["wmt_game_id"]) not in native_play_games and int(row["season"]) in seasons
    ]
    action_only_games = {str(row["wmt_game_id"]) for row in action_only}
    if len(action_only_games) != 50:
        raise RuntimeError("action-only game population drift")

    grouped: dict[tuple[str, int | None, int | None], dict[str, dict[str, Any]]] = defaultdict(dict)
    non_summary_by_season: Counter[int] = Counter()
    summary_action_rows_by_season: Counter[int] = Counter()
    for row in action_only:
        action = action_record(row)
        if action.get("play_action_type") != "play":
            non_summary_by_season[int(row["season"])] += 1
            continue
        subtype = action.get("play_action_sub_type")
        key = summary_group_key(row)
        if subtype in grouped[key]:
            raise RuntimeError(f"duplicate summary subtype for group: {key} {subtype}")
        grouped[key][str(subtype)] = row
        summary_action_rows_by_season[int(row["season"])] += 1

    builder_path = Path(__file__).resolve()
    normalizer_path = repo_root / "src" / "aggie_analytics" / "data" / "action_play_summary.py"
    identity_contract = {
        "schema_version": "1.0.0",
        "dataset_version": config["dataset_version"],
        "decision_unit": config["decision_unit"],
        "selected_seasons": seasons,
        "source_dataset_identity": source["identity"],
        "source_manifest_sha256": source["manifest_sha256"],
        "source_actions_sha256": source["actions_sha256"],
        "source_plays_sha256": source["plays_sha256"],
        "contract_sha256": sha256_file(config_path),
        "builder_sha256": sha256_file(builder_path),
        "normalizer_sha256": sha256_file(normalizer_path),
        "policy_version": POLICY_VERSION,
    }
    dataset_identity = stable_hash(identity_contract)
    output_root = (
        output_data_root / "quarantine" / "historical_known_at" / "sha256"
        / dataset_identity / "action_derived_play_summary"
    )

    candidate_by_season: dict[int, list[dict[str, Any]]] = defaultdict(list)
    excluded_by_season: dict[int, list[dict[str, Any]]] = defaultdict(list)
    reason_counts: Counter[str] = Counter()
    for key in sorted(grouped, key=lambda item: (int(item[0]), item[1] or -1, item[2] or -1)):
        pair = grouped[key]
        disposition, row = classify_summary_pair(pair.get("start"), pair.get("end"))
        season = int(row["season"])
        if disposition == "CANDIDATE":
            candidate_by_season[season].append(row)
        else:
            excluded_by_season[season].append(row)
            reason_counts.update(row["reason_codes"])

    payloads: list[dict[str, Any]] = []
    population_by_season: dict[str, Any] = {}
    candidate_lineages: list[str] = []
    exclusion_lineages: list[str] = []
    expected = config["expected_population"]
    for season in seasons:
        candidates = sorted(
            candidate_by_season[season],
            key=lambda row: (int(row["wmt_game_id"]), row["period_number"], row["play_number"]),
        )
        exclusions = sorted(
            excluded_by_season[season],
            key=lambda row: (int(row["wmt_game_id"]), row["period_number"] or -1, row["play_number"] or -1),
        )
        candidate_path = output_root / f"season={season}" / "candidate_play_summaries.parquet"
        exclusion_path = output_root / f"season={season}" / "excluded_summary_groups.parquet"
        candidate_table = immutable_parquet(candidate_path, candidates)
        exclusion_table = immutable_parquet(exclusion_path, exclusions)
        payloads.append(payload_contract(candidate_path, output_data_root, candidate_table, role="ACTION_DERIVED_PLAY_SUMMARY_CANDIDATES", season=season))
        payloads.append(payload_contract(exclusion_path, output_data_root, exclusion_table, role="ACTION_PLAY_SUMMARY_EXCLUSIONS", season=season))

        season_rows = [row for row in action_only if int(row["season"]) == season]
        season_groups = [key for key in grouped if int(grouped[key].get("start", grouped[key].get("end"))["season"]) == season]
        metrics = {
            "games": len({str(row["wmt_game_id"]) for row in season_rows}),
            "action_rows": len(season_rows),
            "non_summary_action_rows": non_summary_by_season[season],
            "summary_action_rows": summary_action_rows_by_season[season],
            "summary_groups": len(season_groups),
            "candidate_rows": len(candidates),
            "excluded_groups": len(exclusions),
            "play_number_not_positive": sum("PLAY_NUMBER_NOT_POSITIVE" in row["reason_codes"] for row in exclusions),
            "drive_number_missing": sum("DRIVE_NUMBER_MISSING" in row["reason_codes"] for row in exclusions),
        }
        if metrics != expected[str(season)]:
            raise RuntimeError(f"season population drift: {season}: {metrics}")
        population_by_season[str(season)] = metrics
        candidate_lineages.extend(row["row_lineage_sha256"] for row in candidates)
        exclusion_lineages.extend(row["exclusion_lineage_sha256"] for row in exclusions)

    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "TAMU_ACTION_DERIVED_PLAY_SUMMARY_RECONCILIATION_MANIFEST",
        "decision_unit": "POST-SUBTASK-175",
        "dataset_identity": dataset_identity,
        "issued_at_utc": args.issued_at_utc,
        "identity_contract": identity_contract,
        "source_population": {
            "actions_rows": len(actions),
            "native_plays_rows": len(plays),
            "native_play_games": len(native_play_games),
            "action_only_games": len(action_only_games),
            "action_rows_in_action_only_games": len(action_only),
        },
        "population": {
            "by_season": population_by_season,
            "candidate_rows": sum(len(rows) for rows in candidate_by_season.values()),
            "excluded_groups": sum(len(rows) for rows in excluded_by_season.values()),
            "non_summary_action_rows": sum(non_summary_by_season.values()),
            "summary_action_rows": sum(summary_action_rows_by_season.values()),
            "summary_groups": len(grouped),
            "candidate_games": len({row["wmt_game_id"] for rows in candidate_by_season.values() for row in rows}),
            "reason_counts": dict(sorted(reason_counts.items())),
            "ordered_candidate_lineage_sha256": ordered_hash(candidate_lineages),
            "ordered_exclusion_lineage_sha256": ordered_hash(exclusion_lineages),
        },
        "grain_contract": {
            "output_grain": "GAME_PERIOD_PLAY_NUMBER_ACTION_DERIVED_SUMMARY",
            "native_play_relation_equivalence": False,
            "paired_start_end_required": True,
            "source_action_detail_rows_promoted": False,
        },
        "authority": config["authority"],
        "negative_findings": config["required_negative_findings"],
        "payloads": payloads,
    }
    manifest_path = (
        output_data_root / "manifests" / "historical_known_at" / "sha256"
        / dataset_identity / "action_derived_play_summary_reconciliation.json"
    )
    immutable_json(manifest_path, manifest)
    print(json.dumps({
        "dataset_identity": dataset_identity,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "population": manifest["population"],
        "payloads": payloads,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
