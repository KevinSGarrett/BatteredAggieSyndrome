from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.openai_assist.controller import AssistiveController  # noqa: E402


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _paths(controller: AssistiveController, config: dict[str, Any]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for key, spec in config["sources"].items():
        path = controller.store.root.parent / spec["external_relative_path"]
        if not path.is_file():
            raise SystemExit(f"entity pilot source is absent: {key}")
        if path.stat().st_size != int(spec["bytes"]) or _sha(path) != spec["sha256"]:
            raise SystemExit(f"entity pilot source identity mismatch: {key}")
        result[key] = path
    return result


def _resolution_rows(path: Path, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pyarrow is required to prepare the entity-review gold corpus") from exc
    wanted = set(config["positive_resolution_ids"] + config["ambiguous_resolution_ids"])
    columns = [
        "resolution_id", "input_record_id", "entity_type", "source_system_id",
        "source_entity_key", "observed_label", "observed_label_normalized",
        "team_canonical_id", "season", "output_resolution_state",
        "selected_canonical_id", "candidate_canonical_ids", "candidate_scores",
        "candidate_evidence_classes", "confidence_semantics", "decision_rule",
    ]
    table = pq.read_table(path, columns=columns)
    rows = {row["resolution_id"]: row for row in table.to_pylist() if row["resolution_id"] in wanted}
    if set(rows) != wanted:
        raise SystemExit(f"configured entity cases absent: {sorted(wanted - set(rows))}")
    return rows


def _people_candidates(path: Path, positive_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    wanted_names = {row["observed_label_normalized"] for row in positive_rows}
    people: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    mappings: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["record_type"] == "PERSON" and row["display_name_normalized"] in wanted_names:
                people[row["display_name_normalized"]][row["canonical_id"]] = {
                    "canonical_id": row["canonical_id"],
                    "display_name": row["display_name"],
                    "person_type": row["person_type"],
                }
            elif row["record_type"] == "SOURCE_MAPPING" and row["canonical_id"]:
                mappings[row["canonical_id"]].append(
                    {
                        "source_system_id": row["source_system_id"],
                        "source_entity_key": row["source_entity_key"],
                        "quality_state": row["quality_state"],
                    }
                )
    result: dict[str, list[dict[str, Any]]] = {}
    for observation in positive_rows:
        name = observation["observed_label_normalized"]
        expected = observation["selected_canonical_id"]
        candidates = people.get(name, {})
        if expected not in candidates or len(candidates) < 2:
            raise SystemExit(f"positive case lacks a same-name ambiguity set: {observation['resolution_id']}")
        chosen_ids = [expected] + [cid for cid in sorted(candidates) if cid != expected][:4]
        chosen_ids = sorted(chosen_ids)
        payload: list[dict[str, Any]] = []
        for cid in chosen_ids:
            item = dict(candidates[cid])
            item["source_mappings"] = sorted(
                mappings.get(cid, []), key=lambda x: (x["source_system_id"], x["source_entity_key"])
            )[:6]
            payload.append(item)
        result[observation["resolution_id"]] = payload
    return result


def _core_candidates(path: Path, ambiguous_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    wanted = {cid for row in ambiguous_rows for cid in row["candidate_canonical_ids"]}
    result: dict[str, dict[str, Any]] = {
        cid: {"canonical_id": cid, "aliases": [], "source_mappings": []} for cid in wanted
    }
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cid = row["canonical_id"]
            if cid not in wanted:
                continue
            if row["alias"] and row["alias"] not in result[cid]["aliases"]:
                result[cid]["aliases"].append(row["alias"])
            if row["source_entity_key"]:
                mapping = {
                    "source_system_id": row["source_system_id"],
                    "source_entity_key": row["source_entity_key"],
                    "quality_state": row["quality_state"],
                }
                if mapping not in result[cid]["source_mappings"]:
                    result[cid]["source_mappings"].append(mapping)
    for item in result.values():
        item["aliases"] = sorted(item["aliases"])[:6]
        item["source_mappings"] = sorted(
            item["source_mappings"], key=lambda x: (x["source_system_id"], x["source_entity_key"])
        )[:6]
    return result


def _supported(field: str, value: Any) -> dict[str, Any]:
    return {"field": field, "value": value, "status": "SUPPORTED", "evidence_locators": ["text:1"]}


def _unknown(field: str) -> dict[str, Any]:
    return {"field": field, "value": None, "status": "UNKNOWN", "evidence_locators": []}


def _mapping_matches(observation: dict[str, Any], candidate: dict[str, Any]) -> bool:
    source = observation["source_system_id"]
    key = observation["source_entity_key"]
    return any(
        mapping["source_system_id"] == source
        and (mapping["source_entity_key"] == key or mapping["source_entity_key"].endswith(":" + key))
        for mapping in candidate["source_mappings"]
    )


def _positive_case(row: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    expected = row["selected_canonical_id"]
    matches = [candidate["canonical_id"] for candidate in candidates if _mapping_matches(row, candidate)]
    if matches != [expected]:
        raise SystemExit(f"positive case does not have exactly one independently mapped candidate: {row['resolution_id']}")
    evidence = {
        "case_kind": "POSITIVE_SOURCE_SCOPED_ID",
        "observation": {
            "input_record_id": row["input_record_id"],
            "entity_type": row["entity_type"],
            "source_system_id": row["source_system_id"],
            "source_entity_key": row["source_entity_key"],
            "observed_label": row["observed_label"],
            "team_canonical_id": row["team_canonical_id"],
            "season": row["season"],
        },
        "candidates": candidates,
        "evidence_rule": "A source-system/key mapping is independent identity proof; a shared display name is not.",
    }
    excerpt = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True)
    capture = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
    input_order = [item["canonical_id"] for item in candidates]
    expected_order = [expected] + [cid for cid in input_order if cid != expected]
    return {
        "case_id": "entity-positive-" + row["resolution_id"].removeprefix("resolution_"),
        "category": "positive_same_name_source_id",
        "source_url": f"file:external/BAT-390#{row['resolution_id']}",
        "source_capture_sha256": capture,
        "source_excerpt": excerpt,
        "allowed_candidate_ids": input_order,
        "expected_entity_top_k": expected_order,
        "entity_expected_id": expected,
        "entity_merge_expected": False,
        "expected_facts": [
            _supported("resolution_action", "RANK_FOR_REVIEW"),
            _supported("selected_candidate_id", expected),
            _supported("evidence_class", "SOURCE_SCOPED_ID_MATCH"),
            _supported("authority", "REVIEW_ONLY"),
        ],
    }


def _ambiguous_case(row: dict[str, Any], core: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ordered_ids = list(row["candidate_canonical_ids"])
    candidates = []
    for cid, score, evidence_class in zip(
        ordered_ids, row["candidate_scores"], row["candidate_evidence_classes"]
    ):
        candidates.append({**core[cid], "retrieval_score": score, "retrieval_evidence_class": evidence_class})
    evidence = {
        "case_kind": "NEGATIVE_NAME_OR_FUZZY_ONLY",
        "observation": {
            "input_record_id": row["input_record_id"],
            "entity_type": row["entity_type"],
            "source_system_id": row["source_system_id"],
            "source_entity_key": row["source_entity_key"],
            "observed_label": row["observed_label"],
            "team_canonical_id": row["team_canonical_id"],
            "season": row["season"],
        },
        "candidates": candidates,
        "confidence_semantics": row["confidence_semantics"],
        "decision_rule": row["decision_rule"],
        "evidence_rule": "No durable source key or contextual proof is present; aliases and retrieval scores cannot prove identity.",
    }
    excerpt = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True)
    capture = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
    return {
        "case_id": "entity-ambiguous-" + row["resolution_id"].removeprefix("resolution_"),
        "category": "negative_name_or_fuzzy_only",
        "source_url": f"file:external/BAT-390#{row['resolution_id']}",
        "source_capture_sha256": capture,
        "source_excerpt": excerpt,
        "allowed_candidate_ids": ordered_ids,
        "expected_entity_top_k": ordered_ids,
        "entity_merge_expected": False,
        "expected_facts": [
            _supported("resolution_action", "ABSTAIN_UNRESOLVED"),
            _unknown("selected_candidate_id"),
            _supported("evidence_class", "INSUFFICIENT_INDEPENDENT_PROOF"),
            _supported("authority", "REVIEW_ONLY"),
        ],
    }


def main() -> int:
    config = json.loads((ROOT / "configs" / "openai_entity_review_pilot.json").read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    paths = _paths(controller, config)
    rows = _resolution_rows(paths["resolution_results"], config)
    positives = [rows[rid] for rid in config["positive_resolution_ids"]]
    ambiguous = [rows[rid] for rid in config["ambiguous_resolution_ids"]]
    if any(row["output_resolution_state"] != "AUTO_ACCEPTED_VERIFIED" for row in positives):
        raise SystemExit("positive entity-review gold contains a non-verified source row")
    if any(row["output_resolution_state"] != "UNRESOLVED" for row in ambiguous):
        raise SystemExit("ambiguous entity-review gold contains a promoted source row")
    people = _people_candidates(paths["people_registry"], positives)
    core = _core_candidates(paths["core_registry"], ambiguous)
    gold = [_positive_case(row, people[row["resolution_id"]]) for row in positives]
    gold.extend(_ambiguous_case(row, core) for row in ambiguous)
    payload = "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for item in gold
    ).encode("utf-8")
    artifact = controller.store.put_bytes("evals", payload, suffix=".entity-review-gold.jsonl")
    manifest = controller.store.put_json(
        "evals",
        {
            "schema_version": 1,
            "artifact_type": "openai_entity_review_pilot_gold",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "source_identities": [
                {"source_key": key, "sha256": spec["sha256"], "bytes": spec["bytes"]}
                for key, spec in sorted(config["sources"].items())
            ],
            "gold_sha256": artifact.sha256,
            "gold_bytes": artifact.bytes,
            "sample_count": len(gold),
            "positive_cases": len(positives),
            "ambiguous_cases": len(ambiguous),
            "case_ids": [item["case_id"] for item in gold],
            "source_excerpts_in_git": False,
            "canonical_write_authority": False,
            "final_disposition": "SHADOW_GOLD_ONLY",
        },
    )
    print(json.dumps({"gold_path": str(artifact.path), "gold_sha256": artifact.sha256, "manifest_path": str(manifest.path), "manifest_sha256": manifest.sha256, "samples": len(gold), "positive_cases": len(positives), "ambiguous_cases": len(ambiguous)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
