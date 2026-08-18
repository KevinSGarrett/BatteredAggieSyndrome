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

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash  # noqa: E402
from aggie_analytics.data.tamu_official_historical_boxscores import (  # noqa: E402
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
    if "games" in changes:
        tampered["games_identity"] = stable_hash(tampered.get("games"))
    if "domain_coverage" in changes or "games" in changes:
        tampered["coverage_identity"] = stable_hash(tampered.get("domain_coverage"))
    if "counts" in changes or "games" in changes:
        tampered["dataset_identity"] = stable_hash(
            {
                "games": tampered.get("games"),
                "counts": tampered.get("counts"),
                "domain_coverage": tampered.get("domain_coverage"),
            }
        )
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently validate official Texas A&M box-score normalization.")
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
    lake_ready = (data_root / "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/box_scores").is_dir()
    result = validate_artifact(data_root=data_root, repo_root=repo_root, require_rebuild=lake_ready)
    mutations: list[dict[str, Any]] = []
    if not args.validate_only:
        gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8"))

        def _validate(tampered: dict[str, Any]) -> Any:
            return validate_artifact(data_root=data_root, repo_root=repo_root, require_rebuild=False, gate=tampered)

        games = json.loads(json.dumps(gate["games"]))
        games[0]["tamu_points"] = 999
        mutations.append(expect_rejection("altered_score", lambda: _validate(_mutated_gate(gate, games=games))))
        games = json.loads(json.dumps(gate["games"]))
        games[0]["opponent_candidate"] = "Fabricated State"
        games[0]["opponent_normalized"] = "fabricated state"
        mutations.append(expect_rejection("altered_opponent", lambda: _validate(_mutated_gate(gate, games=games))))
        games = json.loads(json.dumps(gate["games"]))
        games[0]["calendar_date"] = "1999-01-01"
        mutations.append(expect_rejection("altered_date", lambda: _validate(_mutated_gate(gate, games=games))))
        games = json.loads(json.dumps(gate["games"]))
        games[0]["source_sha256"] = "00" * 32
        mutations.append(expect_rejection("changed_raw_hash", lambda: _validate(_mutated_gate(gate, games=games))))
        games = json.loads(json.dumps(gate["games"]))
        games.append(json.loads(json.dumps(games[0])))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["captured_pages_total"] = 27
        mutations.append(expect_rejection("duplicate_page", lambda: _validate(_mutated_gate(gate, games=games, counts=counts))))
        games = json.loads(json.dumps(gate["games"]))
        games[0]["domain_coverage"]["officials"] = "ABSENT"
        mutations.append(expect_rejection("missing_officials_reclassified", lambda: _validate(_mutated_gate(gate, games=games))))
        games = json.loads(json.dumps(gate["games"]))
        games[0]["domain_coverage"]["invented_domain"] = "PRESENT"
        mutations.append(expect_rejection("fabricated_domain", lambda: _validate(_mutated_gate(gate, games=games))))
        games = json.loads(json.dumps(gate["games"]))
        games[0]["availability_claim"] = True
        mutations.append(expect_rejection("participation_to_availability", lambda: _validate(_mutated_gate(gate, games=games))))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        mutations.append(expect_rejection("invented_ncaa_contest_id", lambda: _validate(_mutated_gate(gate, counts=counts))))
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
