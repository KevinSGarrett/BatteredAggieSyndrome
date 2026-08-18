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

from aggie_analytics.data.tamu_ncaa_contest_route_discovery import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    compute_gate_identity,
    reject_error_or_redirect_page,
    reject_guessed_numeric_id,
    reject_opponent_date_only_identity,
    reject_third_party_as_ncaa_id,
    reject_wrong_season_contest,
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
    parser = argparse.ArgumentParser(description="Validate 2010-2011 TAMU contest-route discovery.")
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

        mutations.append(expect_rejection("guessed_numeric_id", lambda: reject_guessed_numeric_id("9999999", set())))
        mutations.append(
            expect_rejection(
                "opponent_date_only_identity",
                lambda: reject_opponent_date_only_identity({"ncaa_contest_id": None, "promoted_from": "opponent_date_only"}),
            )
        )
        mutations.append(
            expect_rejection("third_party_as_ncaa_id", lambda: reject_third_party_as_ncaa_id("https://www.espn.com/college-football/game/_/gameId/312610245"))
        )
        mutations.append(expect_rejection("wrong_season_contest", lambda: reject_wrong_season_contest(b"<html>NCAA 2022 box</html>", 2010)))
        mutations.append(expect_rejection("redirect_error_page", lambda: reject_error_or_redirect_page(b"<html>Access Denied</html>", 403)))
        identities = json.loads(json.dumps(gate["input_identities"]))
        identities["phase2_gate_identity"] = "00" * 32
        mutations.append(expect_rejection("changed_source_hash", lambda: _validate(_mutated(gate, input_identities=identities))))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["id_range_sweeps"] = 1
        mutations.append(expect_rejection("id_range_sweep", lambda: _validate(_mutated(gate, counts=counts))))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["contest_endpoint_attempts"] = int(counts["contest_endpoint_attempts"]) + 3
        mutations.append(expect_rejection("zero_attempt_semantics", lambda: _validate(_mutated(gate, counts=counts))))
        mutated = json.loads(json.dumps(gate))
        mutated["discovered_contest_ids"] = ["999999"]
        mutated["counts"]["contest_ids_discovered"] = 1
        mutated["counts"]["contest_endpoint_attempts"] = 1
        mutated["gate_identity"] = compute_gate_identity(mutated)
        mutations.append(expect_rejection("bypass_c_fabricated_contest_id", lambda: _validate(mutated)))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["candidate_routes"] = 99
        mutations.append(expect_rejection("changed_candidate_count", lambda: _validate(_mutated(gate, counts=counts))))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["inspections"] = 99
        mutations.append(expect_rejection("changed_inspection_count", lambda: _validate(_mutated(gate, counts=counts))))
        success = json.loads(json.dumps(gate))
        success["disposition"] = "CONTEST_ROUTE_VERIFIED"
        success["result"] = "PASS_CONTEST_ROUTE_VERIFIED"
        success["discovered_contest_ids"] = ["999999"]
        success["counts"]["contest_ids_discovered"] = 1
        success["counts"]["contest_endpoint_attempts"] = 1
        success["gate_identity"] = compute_gate_identity(success)
        mutations.append(expect_rejection("fabricated_success_disposition", lambda: _validate(success)))
        forged = _mutated(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        mutations.append(expect_rejection("forged_success_after_rehash", lambda: _validate(forged)))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["protected_outcome_authority"] = True
        mutations.append(expect_rejection("protected_lane_authority", lambda: _validate(_mutated(gate, authority=authority))))
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
