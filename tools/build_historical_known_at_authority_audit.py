"""Materialize the historical known-at authority audit gate for GAP-002.

The build is offline. It reads the committed domain admission matrix, profiles the start-time
evidence the national spine already carries, and consumes a route capture manifest that the
explicit acquisition command produced earlier.
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

from aggie_analytics.data.historical_known_at_authority import (  # noqa: E402
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    MATRIX_GATE_RELATIVE,
    KnownAtAuthorityViolation,
    build_audit,
    load_contract,
    profile_start_evidence,
    read_json,
    validate_artifact,
)

ROUTE_MANIFEST_GLOB = (
    "manifests/known_at/historical_known_at_publication_routes/sha256/*/"
    "historical_known_at_publication_route_manifest.json"
)
SPINE_DATASET = "national_pregame_team_features.jsonl"


def latest_route_manifest(data_root: Path) -> Path:
    candidates = sorted(data_root.glob(ROUTE_MANIFEST_GLOB))
    if not candidates:
        raise KnownAtAuthorityViolation(
            "no publication-route capture manifest exists; run"
            " tools/acquire_historical_known_at_publication_routes.py first"
        )
    return max(candidates, key=lambda path: read_json(path)["issued_at_utc"])


def load_spine_rows(repo_root: Path, data_root: Path) -> list[dict[str, Any]]:
    """Read the national pregame spine rows the admission matrix already binds."""

    matrix = read_json(repo_root / MATRIX_GATE_RELATIVE)
    payload = next(row for row in matrix["payloads"] if row["name"] == SPINE_DATASET)
    path = (
        data_root
        / "canonical"
        / "national_pit_domain_admission_matrix"
        / "sha256"
        / matrix["dataset_identity"]
        / payload["name"]
    )
    if not path.exists():
        raise KnownAtAuthorityViolation(f"the national spine payload is missing at {path}")
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


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
    matrix = read_json(repo_root / MATRIX_GATE_RELATIVE)
    profile = profile_start_evidence(load_spine_rows(repo_root, data_root))
    manifest_path = latest_route_manifest(data_root)
    gate = build_audit(matrix, profile, read_json(manifest_path), contract)

    write_json(repo_root / GATE_RELATIVE, gate)
    write_json(
        repo_root / EVIDENCE_RELATIVE,
        {
            "artifact_type": "HISTORICAL_KNOWN_AT_AUTHORITY_REPLAY",
            "capture_identity": gate["capture_identity"],
            "contract_id": gate["contract_id"],
            "gate_identity": gate["gate_identity"],
            "gate_relative_path": GATE_RELATIVE,
            "matrix_gate_identity": matrix.get("gate_identity"),
            "reproduction": [
                "python tools/acquire_historical_known_at_publication_routes.py"
                " --repo-root . --data-root <data-root> --env-file <env> --issued-at-utc <now>",
                "python tools/build_historical_known_at_authority_audit.py"
                " --repo-root . --data-root <data-root>",
                "python tools/validate_historical_known_at_authority_audit.py --repo-root .",
            ],
            "route_manifest_relative_path": str(
                manifest_path.relative_to(data_root)
            ).replace("\\", "/"),
            "schema_version": "aggie.data.historical_known_at_authority_replay.v1",
        },
    )
    print(json.dumps(validate_artifact(repo_root, gate), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
