"""Materialize the 2018-2023 expanding chronological national walk-forward.

The build is fully offline. It reads the chronological development matrix, loads the frozen
Cycle #20 candidate list verbatim, and refits every candidate once per evaluation season on
strictly preceding seasons only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.modeling.national_multi_year_walk_forward import (  # noqa: E402
    AUTHORITY_GATE_RELATIVE,
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    MATRIX_GATE_RELATIVE,
    PAYLOAD_NAME,
    WalkForwardViolation,
    build_gate,
    canonical_json_bytes,
    load_candidates,
    load_contract,
    read_json,
    read_jsonl,
    run_walk_forward,
    summarize_candidates,
    validate_artifact,
)

MATRIX_DATASET = "national_chronological_development_matrix"


def matrix_dir(data_root: Path, identity: str) -> Path:
    return data_root / "canonical" / MATRIX_DATASET / "sha256" / identity


def require(path: Path) -> Path:
    if not path.exists():
        raise WalkForwardViolation(f"a required payload is missing at {path}")
    return path


def write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_payload(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(body)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    if args.validate_only:
        print(json.dumps(validate_artifact(repo_root), indent=2, sort_keys=True))
        return 0

    contract = load_contract(repo_root)
    candidates, candidate_sha = load_candidates(repo_root, contract)
    matrix_gate = read_json(repo_root / MATRIX_GATE_RELATIVE)
    authority_gate = read_json(repo_root / AUTHORITY_GATE_RELATIVE)

    base = matrix_dir(data_root, matrix_gate["dataset_identity"])
    matrix = read_jsonl(require(base / "national_development_matrix_features.jsonl"))
    labels = read_jsonl(require(base / "national_development_matrix_labels.jsonl"))

    predictions, folds = run_walk_forward(
        matrix=matrix, labels=labels, candidates=candidates, contract=contract
    )
    summaries = summarize_candidates(predictions, candidates, contract)
    gate = build_gate(
        summaries=summaries,
        folds=folds,
        predictions=predictions,
        contract=contract,
        candidate_sha256=candidate_sha,
        predecessor_identities={
            "historical_known_at_authority_gate_identity": authority_gate.get("gate_identity"),
            "national_chronological_development_matrix_gate_identity": matrix_gate.get(
                "gate_identity"
            ),
        },
    )

    payload_dir = (
        data_root
        / "canonical"
        / "national_multi_year_walk_forward"
        / "sha256"
        / gate["gate_identity"]
    )
    write_payload(
        payload_dir / PAYLOAD_NAME,
        b"".join(canonical_json_bytes(row) + b"\n" for row in predictions),
    )
    write_json(repo_root / GATE_RELATIVE, gate)
    write_json(
        repo_root / EVIDENCE_RELATIVE,
        {
            "artifact_type": "NATIONAL_MULTI_YEAR_WALK_FORWARD_REPLAY",
            "candidate_set_sha256": gate["candidate_set_sha256"],
            "contract_id": gate["contract_id"],
            "gate_identity": gate["gate_identity"],
            "gate_relative_path": GATE_RELATIVE,
            "payload_relative_path": (
                f"canonical/national_multi_year_walk_forward/sha256/{gate['gate_identity']}/"
                f"{PAYLOAD_NAME}"
            ),
            "payload_sha256": gate["payload"]["sha256"],
            "reproduction": [
                "python tools/build_national_multi_year_walk_forward.py"
                " --repo-root . --data-root <data-root>",
                "python tools/validate_national_multi_year_walk_forward.py"
                " --repo-root . --data-root <data-root>",
            ],
            "schema_version": "aggie.models.national_multi_year_walk_forward_replay.v1",
        },
    )
    print(json.dumps(validate_artifact(repo_root, gate), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
