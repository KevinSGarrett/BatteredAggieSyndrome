"""Materialize Cycle 27 pinned Week 1 official-final scoring.

Pin creation may snapshot an explicit file list once. Scoring and replay read
only the pin. This tool never writes into the original scoreboard directory and
never rewrites the Cycle 26 scoring gate or dataset.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.week1_2026_cycle27_official_final_scoring import (  # noqa: E402
    PARSER_MODULE_RELATIVE,
    PREDECESSOR_SCORING_DATASET_IDENTITY,
    PREDECESSOR_SCORING_GATE_IDENTITY,
    WEEK1_GATE_RELATIVE,
    Week1Cycle27OfficialFinalScoringError,
    build_pinned_input_manifest,
    capture_record_from_file,
    materialize,
    parser_module_sha256,
    read_json,
    sha256_file,
    write_hashed_acquisition_receipt,
)

SCOREBOARD_RELATIVE = "raw/SRC-NCAA-OFFICIAL-STATS/ncaa_week1_2026_schedule_scoreboard"
FORBIDDEN_DATASET_DIR = (
    "canonical/week1_2026_official_final_scoring_successor/sha256/"
    + PREDECESSOR_SCORING_DATASET_IDENTITY
)
FORBIDDEN_GATE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_WEEK1_OFFICIAL_FINAL_SCORING.json"
)


def _explicit_scoreboard_paths(directory: Path) -> list[Path]:
    """Pin-creation snapshot only. Scoring must not call this."""
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".html"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root",
        default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", ""),
    )
    parser.add_argument(
        "--execution-time-utc",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    parser.add_argument(
        "--pin-manifest",
        default="",
        help="existing pinned manifest JSON; replay path, never globs",
    )
    parser.add_argument(
        "--snapshot-scoreboard",
        action="store_true",
        help="create a NEW pin from an explicit snapshot of current HTML files",
    )
    args = parser.parse_args()
    if not args.data_root:
        print(json.dumps({"result": "FAIL", "findings": ["DATA_ROOT_REQUIRED"]}))
        return 1
    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root)
    forbidden_dataset = data_root / FORBIDDEN_DATASET_DIR
    forbidden_gate = repo_root / FORBIDDEN_GATE
    predecessor_gate_before = (
        forbidden_gate.read_bytes() if forbidden_gate.is_file() else None
    )
    predecessor_dataset_before = (
        (
            forbidden_dataset / "week1_2026_official_final_scoring_rows.jsonl"
        ).read_bytes()
        if (
            forbidden_dataset / "week1_2026_official_final_scoring_rows.jsonl"
        ).is_file()
        else None
    )
    try:
        if args.pin_manifest:
            manifest = read_json(Path(args.pin_manifest))
        elif args.snapshot_scoreboard:
            week1 = read_json(repo_root / WEEK1_GATE_RELATIVE)
            freeze_utc = str(week1.get("issued_at_utc") or "")
            forecast_rel = week1["payloads"]["forecast_rows"]["relative_path"]
            forecast_path = data_root / forecast_rel
            forecast_bytes = forecast_path.read_bytes()
            directory = data_root / SCOREBOARD_RELATIVE
            captures = []
            for path in _explicit_scoreboard_paths(directory):
                relative = str(path.relative_to(data_root)).replace("\\", "/")
                record = capture_record_from_file(
                    data_root=data_root,
                    relative_path=relative,
                )
                receipt = write_hashed_acquisition_receipt(
                    data_root=data_root,
                    html_relative_path=relative,
                    html_sha256=str(record["sha256"]),
                    html_bytes=int(record["bytes"]),
                    retrieved_at_utc=args.execution_time_utc,
                )
                record["acquisition_receipt_relative_path"] = receipt[
                    "acquisition_receipt_relative_path"
                ]
                record["acquisition_receipt_sha256"] = receipt[
                    "acquisition_receipt_sha256"
                ]
                captures.append(record)
            manifest = build_pinned_input_manifest(
                captures=captures,
                forecast_payload={
                    "relative_path": str(forecast_rel).replace("\\", "/"),
                    "sha256": sha256_file(forecast_path),
                    "bytes": len(forecast_bytes),
                },
                as_of_utc=args.execution_time_utc,
                parser_module_sha256_hex=parser_module_sha256(repo_root),
                freeze_utc=freeze_utc,
            )
        else:
            print(
                json.dumps(
                    {
                        "result": "FAIL",
                        "findings": ["PIN_MANIFEST_OR_SNAPSHOT_REQUIRED"],
                    }
                )
            )
            return 1
        gate = materialize(
            repo_root=repo_root,
            data_root=data_root,
            manifest=manifest,
            issued_at_utc=args.execution_time_utc,
        )
    except Week1Cycle27OfficialFinalScoringError as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    if predecessor_gate_before is not None and forbidden_gate.read_bytes() != (
        predecessor_gate_before
    ):
        print(
            json.dumps(
                {
                    "result": "FAIL",
                    "findings": ["PREDECESSOR_SCORING_GATE_OVERWRITE"],
                    "predecessor_scoring_gate_identity": PREDECESSOR_SCORING_GATE_IDENTITY,
                }
            )
        )
        return 1
    if predecessor_dataset_before is not None:
        after = (
            forbidden_dataset / "week1_2026_official_final_scoring_rows.jsonl"
        ).read_bytes()
        if after != predecessor_dataset_before:
            print(
                json.dumps(
                    {
                        "result": "FAIL",
                        "findings": ["PREDECESSOR_SCORING_DATASET_OVERWRITE"],
                        "predecessor_scoring_dataset_identity": (
                            PREDECESSOR_SCORING_DATASET_IDENTITY
                        ),
                    }
                )
            )
            return 1
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "dataset_identity": gate["dataset_identity"],
                "schema_identity": gate["schema_identity"],
                "code_identity": gate["code_identity"],
                "input_manifest_identity": gate["input_manifest_identity"],
                "parser_version": gate["parser_version"],
                "summary": gate["summary"],
                "primary_trust_recovery": gate["primary_trust_recovery"],
                "parser_module": PARSER_MODULE_RELATIVE,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
