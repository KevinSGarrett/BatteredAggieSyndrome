from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_gamebook_union import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    compute_gate_identity,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, AuthorityViolation, FileNotFoundError, AssertionError) as exc:
        return {"name": name, "result": "PASS_FAIL_CLOSED", "exception": type(exc).__name__, "message": str(exc)[:240]}
    raise AssertionError(f"mutation control did not reject: {name}")


def _mutated_gate(gate: dict[str, Any], **changes: Any) -> dict[str, Any]:
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently validate the official gamebook union.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    lake_ready = (
        data_root
        / "quarantine/historical_known_at/sha256/76c3b366431d5085588d07df7d8db77348ac737dc57538befe26c7080150f010/tamu_official_gamebooks/domain=game/candidate_records.parquet"
    ).is_file()
    result = validate_artifact(data_root=data_root, repo_root=repo_root, require_rebuild=lake_ready)
    mutations: list[dict[str, Any]] = []
    if not args.validate_only:
        gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8"))

        def _validate(tampered: dict[str, Any]) -> Any:
            return validate_artifact(data_root=data_root, repo_root=repo_root, require_rebuild=False, gate=tampered)

        counts = json.loads(json.dumps(gate["counts"]))
        counts["union_captured_games"] = 999
        mutations.append(expect_rejection("changed_union_total", lambda: _validate(_mutated_gate(gate, counts=counts))))
        games = json.loads(json.dumps(gate["official_games"]))
        games[0]["ncaa_contest_id"] = "999999"
        mutations.append(expect_rejection("invented_ncaa_contest_id", lambda: _validate(_mutated_gate(gate, official_games=games))))
        texas = json.loads(json.dumps(gate["texas_2011"]))
        texas["name_only_promotion"] = True
        mutations.append(expect_rejection("texas_name_only", lambda: _validate(_mutated_gate(gate, texas_2011=texas))))
        texas = json.loads(json.dumps(gate["texas_2011"]))
        texas["discrepancy_erased"] = True
        mutations.append(expect_rejection("texas_conflict_erased", lambda: _validate(_mutated_gate(gate, texas_2011=texas))))
        lsu = json.loads(json.dumps(gate["lsu_2010"]))
        lsu["silently_normalized"] = True
        mutations.append(expect_rejection("lsu_silently_normalized", lambda: _validate(_mutated_gate(gate, lsu_2010=lsu))))
        wmt = json.loads(json.dumps(gate["wmt_layer"]))
        wmt["dataset_identity"] = "00" * 32
        mutations.append(expect_rejection("wmt_identity_rewritten", lambda: _validate(_mutated_gate(gate, wmt_layer=wmt))))
        mutations.append(expect_rejection("protected_lane_opened", lambda: _validate(_mutated_gate(gate, protected_lane="OPEN"))))
        mutations.append(
            expect_rejection(
                "forged_completion",
                lambda: _validate(_mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")),
            )
        )
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
