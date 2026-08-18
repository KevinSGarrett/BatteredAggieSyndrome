from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_season_reconciliation import (  # noqa: E402
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


def _mutated(gate: dict[str, Any], **changes: Any) -> dict[str, Any]:
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate 2010-2011 TAMU season-level reconciliation.")
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
    result = validate_artifact(data_root=data_root, repo_root=repo_root, require_rebuild=True)
    mutations: list[dict[str, Any]] = []
    if not args.validate_only:
        gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8"))

        def _validate(tampered: dict[str, Any]) -> Any:
            return validate_artifact(data_root=data_root, repo_root=repo_root, require_rebuild=False, gate=tampered)

        identities = json.loads(json.dumps(gate["input_identities"]))
        identities["phase2_gate_identity"] = "00" * 32
        mutations.append(expect_rejection("changed_source_hash", lambda: _validate(_mutated(gate, input_identities=identities))))
        seeds = dict(gate["tamu_seeds"])
        seeds["2010"] = "000000"
        mutations.append(expect_rejection("changed_season_team_identity", lambda: _validate(_mutated(gate, tamu_seeds=seeds))))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["comparison_rows"] = int(counts["comparison_rows"]) + 1
        mutations.append(expect_rejection("altered_total", lambda: _validate(_mutated(gate, counts=counts))))
        conflict = json.loads(json.dumps(gate["texas_2011_conflict"]))
        conflict["resolved"] = False
        mutations.append(expect_rejection("dropped_conflict", lambda: _validate(_mutated(gate, texas_2011_conflict=conflict))))
        conflict = json.loads(json.dumps(gate["texas_2011_conflict"]))
        conflict["discrepancy_erased"] = True
        mutations.append(expect_rejection("erased_sidearm_conflict", lambda: _validate(_mutated(gate, texas_2011_conflict=conflict))))
        conflict = json.loads(json.dumps(gate["texas_2011_conflict"]))
        conflict["sidearm_or_gap_matrix_date"] = "2011-11-24"
        mutations.append(expect_rejection("erased_sidearm_date", lambda: _validate(_mutated(gate, texas_2011_conflict=conflict))))
        conflict = json.loads(json.dumps(gate["texas_2011_conflict"]))
        conflict["name_only_promotion"] = True
        mutations.append(expect_rejection("name_only_promotion", lambda: _validate(_mutated(gate, texas_2011_conflict=conflict))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["season_total_as_per_game_official"] = True
        mutations.append(expect_rejection("season_total_as_per_game", lambda: _validate(_mutated(gate, authority=authority))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["membership_as_availability"] = True
        mutations.append(expect_rejection("membership_promoted_to_availability", lambda: _validate(_mutated(gate, authority=authority))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["participation_as_availability"] = True
        mutations.append(expect_rejection("participation_promoted_to_availability", lambda: _validate(_mutated(gate, authority=authority))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["historical_known_at_from_capture_time"] = True
        mutations.append(expect_rejection("fabricated_known_at", lambda: _validate(_mutated(gate, authority=authority))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["protected_outcome_authority"] = True
        mutations.append(expect_rejection("protected_lane_authority", lambda: _validate(_mutated(gate, authority=authority))))
        forged = _mutated(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        mutations.append(expect_rejection("forged_completion_after_rehash", lambda: _validate(forged)))
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
