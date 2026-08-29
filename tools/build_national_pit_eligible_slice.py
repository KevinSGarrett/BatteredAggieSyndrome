"""Materialize the first nonzero national point-in-time eligible feature slice.

The build is fully offline. It reads the tiered game spine's observations and outcome labels,
the admission matrix's contest start evidence, and the BAT-666 completion bound, then
recomputes every prior feature from bound-admissible evidence only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.national_pit_eligible_slice import (  # noqa: E402
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    PAYLOAD_NAME,
    PitSliceViolation,
    build_gate,
    build_rows,
    load_authority,
    load_contract,
    payload_lines,
    read_json,
    read_jsonl,
    validate_artifact,
)

SPINE_GATE_RELATIVE = "artifacts/data_lake/national_tiered_game_spine_gate.json"
MATRIX_GATE_RELATIVE = "artifacts/data_lake/national_pit_domain_admission_matrix_gate.json"
MATRIX_PAYLOAD = "national_pregame_team_features.jsonl"


def canonical_dir(data_root: Path, dataset: str, identity: str) -> Path:
    return data_root / "canonical" / dataset / "sha256" / identity


def require(path: Path) -> Path:
    if not path.exists():
        raise PitSliceViolation(f"a required payload is missing at {path}")
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


def load_inputs(repo_root: Path, data_root: Path) -> dict[str, Any]:
    spine_gate = read_json(repo_root / SPINE_GATE_RELATIVE)
    matrix_gate = read_json(repo_root / MATRIX_GATE_RELATIVE)
    spine_dir = canonical_dir(
        data_root, "national_tiered_game_spine", spine_gate["dataset_identity"]
    )
    matrix_dir = canonical_dir(
        data_root, "national_pit_domain_admission_matrix", matrix_gate["dataset_identity"]
    )
    spine_rows = read_jsonl(require(matrix_dir / MATRIX_PAYLOAD))
    return {
        "matrix_gate": matrix_gate,
        "observations": read_jsonl(require(spine_dir / "national_team_observations.jsonl")),
        "outcomes": read_jsonl(require(spine_dir / "national_team_outcome_labels.jsonl")),
        "spine_gate": spine_gate,
        "spine_rows": spine_rows,
        "starts": {
            str(row["canonical_game_id"]): str(row.get("start_date_utc_text") or "")
            for row in spine_rows
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Re-check the committed gate without writing anything.",
    )
    args = parser.parse_args()

    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    if args.validate_only:
        print(json.dumps(validate_artifact(repo_root), indent=2, sort_keys=True))
        return 0

    contract = load_contract(repo_root)
    authority = load_authority(repo_root)
    inputs = load_inputs(repo_root, data_root)

    rows = build_rows(
        inputs["observations"],
        inputs["outcomes"],
        inputs["starts"],
        contract,
        authority["conservative_bound_policy"],
    )
    gate = build_gate(
        rows,
        inputs["spine_rows"],
        contract,
        authority,
        {
            "national_pit_domain_admission_matrix_gate_identity": inputs["matrix_gate"].get(
                "gate_identity"
            ),
            "national_tiered_game_spine_gate_identity": inputs["spine_gate"].get("gate_identity"),
        },
    )

    payload_dir = canonical_dir(
        data_root, "national_pit_eligible_slice", gate["gate_identity"]
    )
    write_payload(payload_dir / PAYLOAD_NAME, payload_lines(rows))
    write_json(repo_root / GATE_RELATIVE, gate)
    write_json(
        repo_root / EVIDENCE_RELATIVE,
        {
            "artifact_type": "NATIONAL_PIT_ELIGIBLE_SLICE_REPLAY",
            "contract_id": gate["contract_id"],
            "gate_identity": gate["gate_identity"],
            "gate_relative_path": GATE_RELATIVE,
            "payload_relative_path": (
                f"canonical/national_pit_eligible_slice/sha256/{gate['gate_identity']}/"
                f"{PAYLOAD_NAME}"
            ),
            "payload_sha256": gate["payload"]["sha256"],
            "reproduction": [
                "python tools/build_national_pit_eligible_slice.py"
                " --repo-root . --data-root <data-root>",
                "python tools/validate_national_pit_eligible_slice.py"
                " --repo-root . --data-root <data-root>",
            ],
            "schema_version": "aggie.data.national_pit_eligible_slice_replay.v1",
        },
    )
    print(json.dumps(validate_artifact(repo_root, gate), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
