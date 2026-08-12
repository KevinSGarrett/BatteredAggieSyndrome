from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json
from aggie_analytics.assistive_plane.redaction import contains_secret


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("EMBEDDING_DIMENSION_INVALID")
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    denominator = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    if denominator == 0:
        raise ValueError("EMBEDDING_ZERO_NORM")
    return numerator / denominator


def record(local_id: str) -> tuple[Path, dict[str, Any]]:
    matches = list((ROOT / "jira/records/issues").rglob(f"{local_id}_*.json"))
    if len(matches) != 1:
        raise RuntimeError(f"EMBEDDING_SOURCE_NOT_UNIQUE:{local_id}")
    return matches[0], json.loads(matches[0].read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/local_embedding_shadow_qualification.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    with urllib.request.urlopen(f"{config['endpoint']}/api/tags", timeout=30) as response:
        tags = json.loads(response.read().decode("utf-8"))
    models = [item for item in tags["models"] if item.get("name") == config["model"]]
    if len(models) != 1 or models[0].get("digest") != config["expected_digest"]:
        raise RuntimeError("LOCAL_EMBEDDING_EXACT_DIGEST_MISMATCH")
    corpus = []
    for local_id in config["corpus_local_ids"]:
        path, payload = record(local_id)
        text = f"{payload['objective']}\n{payload['scope']}"
        if contains_secret(text):
            raise RuntimeError("LOCAL_EMBEDDING_SOURCE_SECRET_DETECTED")
        corpus.append({"local_id": local_id, "text": text, "source_sha256": sha256(path)})
    inputs = [item["text"] for item in corpus] + [item["text"] for item in config["queries"]]
    started = time.perf_counter()
    first = request_json(f"{config['endpoint']}/api/embed", {"model": config["model"], "input": inputs, "truncate": False, "keep_alive": "5m"})
    repeated = request_json(f"{config['endpoint']}/api/embed", {"model": config["model"], "input": [inputs[0]], "truncate": False, "keep_alive": 0})
    wall_seconds = time.perf_counter() - started
    vectors = first.get("embeddings", [])
    if len(vectors) != len(inputs):
        raise RuntimeError("LOCAL_EMBEDDING_OUTPUT_COUNT_INVALID")
    corpus_vectors = vectors[: len(corpus)]
    query_vectors = vectors[len(corpus):]
    results = []
    for query, vector in zip(config["queries"], query_vectors, strict=True):
        ranking = sorted(
            ({"local_id": item["local_id"], "cosine": cosine(vector, candidate)} for item, candidate in zip(corpus, corpus_vectors, strict=True)),
            key=lambda item: (-item["cosine"], item["local_id"]),
        )
        expected = query["expected_local_id"]
        results.append({
            "query_id": query["query_id"],
            "query_sha256": hashlib.sha256(query["text"].encode("utf-8")).hexdigest(),
            "expected_local_id": expected,
            "top3": ranking[:3],
            "top1_correct": ranking[0]["local_id"] == expected,
            "top3_correct": expected in {item["local_id"] for item in ranking[:3]},
        })
    repeat_cosine = cosine(corpus_vectors[0], repeated["embeddings"][0])
    metrics = {
        "corpus_records": len(corpus),
        "query_count": len(results),
        "embedding_dimensions": len(corpus_vectors[0]),
        "top1_recall": sum(item["top1_correct"] for item in results) / len(results),
        "top3_recall": sum(item["top3_correct"] for item in results) / len(results),
        "exact_repeat_cosine": repeat_cosine,
        "prompt_tokens": first.get("prompt_eval_count", 0) + repeated.get("prompt_eval_count", 0),
        "wall_seconds": round(wall_seconds, 6),
        "model_size_bytes": models[0].get("size"),
        "review_time_saved_seconds": 0.0,
        "canonical_writes": 0,
        "protected_decisions": 0,
    }
    acceptance = config["acceptance"]
    passed = (
        metrics["query_count"] >= acceptance["query_count_min"]
        and metrics["top1_recall"] >= acceptance["top1_recall_min"]
        and metrics["top3_recall"] >= acceptance["top3_recall_min"]
        and metrics["exact_repeat_cosine"] >= acceptance["exact_repeat_cosine_min"]
        and metrics["canonical_writes"] <= acceptance["canonical_writes_max"]
        and metrics["protected_decisions"] <= acceptance["protected_decisions_max"]
    )
    raw_record = {
        "schema_version": 1,
        "qualification_id": config["qualification_id"],
        "model": config["model"],
        "model_digest": config["expected_digest"],
        "corpus": [{"local_id": item["local_id"], "source_sha256": item["source_sha256"]} for item in corpus],
        "vectors": vectors,
        "repeat_vector": repeated["embeddings"][0],
    }
    _, vectors_sha256 = write_content_addressed_json(Path(config["storage_root"]), "responses", raw_record)
    evaluation = {
        "schema_version": 1,
        "qualification_id": config["qualification_id"],
        "jira_unit": config["jira_unit"],
        "authority": config["authority"],
        "config_sha256": sha256(args.config),
        "model": config["model"],
        "model_digest": config["expected_digest"],
        "vectors_sha256": vectors_sha256,
        "metrics": metrics,
        "acceptance": acceptance,
        "results": results,
        "qualification_disposition": "PASS_CANDIDATE_RETRIEVAL_ONLY" if passed else "FAIL_PRESERVE_NEGATIVE_EVIDENCE",
        "canonical_or_protected_authority": False,
    }
    path, digest = write_content_addressed_json(Path(config["storage_root"]), "evals", evaluation)
    print(json.dumps({"status": evaluation["qualification_disposition"], "path": str(path), "sha256": digest, **metrics}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
