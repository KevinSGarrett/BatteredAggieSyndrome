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

from aggie_analytics.data.tamu_ncaa_team_season_evidence import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    compute_gate_identity,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, AuthorityViolation, FileNotFoundError, AssertionError) as exc:
        return {
            "name": name,
            "result": "PASS_FAIL_CLOSED",
            "exception": type(exc).__name__,
            "message": str(exc)[:240],
        }
    raise AssertionError(f"mutation control did not reject: {name}")


def _mutated_gate(gate: dict[str, Any], **changes: Any) -> dict[str, Any]:
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently validate 2010-2011 Texas A&M NCAA team-season evidence."
    )
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

        def _validate(tampered_gate: dict[str, Any]) -> Any:
            return validate_artifact(
                data_root=data_root,
                repo_root=repo_root,
                require_rebuild=True,
                gate=tampered_gate,
            )

        seeds = json.loads(json.dumps(gate["tamu_seeds"]))
        seeds["2010"] = "000000"
        mutations.append(expect_rejection("changed_season_team_identity", lambda: _validate(_mutated_gate(gate, tamu_seeds=seeds))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["availability_claim"] = True
        mutations.append(expect_rejection("membership_promoted_to_availability", lambda: _validate(_mutated_gate(gate, authority=authority))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["season_total_as_per_game_official"] = True
        mutations.append(expect_rejection("season_total_as_per_game", lambda: _validate(_mutated_gate(gate, authority=authority))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["protected_outcome_authority"] = True
        mutations.append(expect_rejection("protected_lane_authority", lambda: _validate(_mutated_gate(gate, authority=authority))))
        nonclaims = json.loads(json.dumps(gate["scientific_nonclaims"]))
        nonclaims["roster_membership_used_as_availability"] = True
        mutations.append(
            expect_rejection(
                "roster_used_as_availability",
                lambda: _validate(_mutated_gate(gate, scientific_nonclaims=nonclaims)),
            )
        )
        counts = json.loads(json.dumps(gate["counts"]))
        counts["contest_ids_fabricated"] = 1
        mutations.append(expect_rejection("fabricated_contest_ids", lambda: _validate(_mutated_gate(gate, counts=counts))))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["official_routes_attempted"] = 999
        mutations.append(expect_rejection("bypass_a_changed_official_routes_attempted", lambda: _validate(_mutated_gate(gate, counts=counts))))
        domains = json.loads(json.dumps(gate["domains"]))
        domains["points_for_against"]["2010"]["value"]["points_for"] = 999
        mutations.append(expect_rejection("bypass_b_changed_2010_points_for", lambda: _validate(_mutated_gate(gate, domains=domains))))
        domains = json.loads(json.dumps(gate["domains"]))
        domains["wins_losses_ties"]["2010"]["value"]["wins"] = 13
        mutations.append(expect_rejection("changed_wlt", lambda: _validate(_mutated_gate(gate, domains=domains))))
        attempts = json.loads(json.dumps(gate["attempts"]))
        attempts[0]["status"] = 200
        mutations.append(expect_rejection("changed_status_403_to_200", lambda: _validate(_mutated_gate(gate, attempts=attempts))))
        attempts = json.loads(json.dumps(gate["attempts"]))
        attempts[0]["url"] = "https://stats.ncaa.org/teams/137387/box_score"
        mutations.append(expect_rejection("changed_attempt_url", lambda: _validate(_mutated_gate(gate, attempts=attempts))))
        attempts = json.loads(json.dumps(gate["attempts"]))
        attempts[0]["timestamp"] = "1999-01-01T00:00:00Z"
        mutations.append(expect_rejection("changed_attempt_timestamp", lambda: _validate(_mutated_gate(gate, attempts=attempts))))
        attempts = json.loads(json.dumps(gate["attempts"]))
        attempts[0]["raw_sha256"] = "00" * 32
        attempts[0]["response_sha256"] = "00" * 32
        mutations.append(expect_rejection("changed_raw_hash", lambda: _validate(_mutated_gate(gate, attempts=attempts))))
        attempts = json.loads(json.dumps(gate["attempts"]))
        attempts[0]["raw_relative_path"] = "raw/SRC-015/ncaa_team_season_evidence/" + ("ab" * 32) + ".html"
        mutations.append(expect_rejection("missing_raw_payload", lambda: _validate(_mutated_gate(gate, attempts=attempts))))
        forged = _mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        mutations.append(expect_rejection("forged_completion_after_rehash", lambda: _validate(forged)))
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
