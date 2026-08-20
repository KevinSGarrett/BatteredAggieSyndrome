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

from aggie_analytics.data.tamu_official_2002_boxscores import (  # noqa: E402
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
    parser = argparse.ArgumentParser(description="Independently validate official 2002 box-score acquisition.")
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
    result = validate_artifact(repo_root=repo_root, data_root=data_root)
    mutations: list[dict[str, Any]] = []
    if not args.validate_only:
        gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8"))

        def _validate(tampered: dict[str, Any]) -> Any:
            return validate_artifact(repo_root=repo_root, data_root=data_root, gate=tampered)

        mutations.append(expect_rejection("protected_lane_opened", lambda: _validate(_mutated_gate(gate, protected_lane="OPEN"))))
        authority = json.loads(json.dumps(gate["authority"]))
        authority["historical_known_at_from_capture_time"] = True
        mutations.append(expect_rejection("retrieval_time_as_known_at", lambda: _validate(_mutated_gate(gate, authority=authority))))
        authority2 = json.loads(json.dumps(gate["authority"]))
        authority2["participation_as_availability"] = True
        mutations.append(expect_rejection("participation_as_availability", lambda: _validate(_mutated_gate(gate, authority=authority2))))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        mutations.append(expect_rejection("ncaa_contest_ids_forged", lambda: _validate(_mutated_gate(gate, counts=counts))))
        counts2 = json.loads(json.dumps(gate["counts"]))
        counts2["pregame_availability_present"] = 1
        mutations.append(expect_rejection("availability_claimed", lambda: _validate(_mutated_gate(gate, counts=counts2))))
        counts3 = json.loads(json.dumps(gate["counts"]))
        counts3["rich_structured_games"] = int(counts3.get("rich_structured_games") or 0) + 1
        mutations.append(expect_rejection("rich_count_tamper", lambda: _validate(_mutated_gate(gate, counts=counts3))))
        upstream = json.loads(json.dumps(gate["upstream_identities"]))
        upstream["bat600_gate_identity"] = "0" * 64
        mutations.append(expect_rejection("bat600_rewrite", lambda: _validate(_mutated_gate(gate, upstream_identities=upstream))))
        upstream2 = json.loads(json.dumps(gate["upstream_identities"]))
        upstream2["bat604_gate_identity"] = "0" * 64
        mutations.append(expect_rejection("bat604_rewrite", lambda: _validate(_mutated_gate(gate, upstream_identities=upstream2))))
        upstream3 = json.loads(json.dumps(gate["upstream_identities"]))
        upstream3["bat613_gate_identity"] = "0" * 64
        mutations.append(expect_rejection("bat613_rewrite", lambda: _validate(_mutated_gate(gate, upstream_identities=upstream3))))
        upstream5 = json.loads(json.dumps(gate["upstream_identities"]))
        upstream5["bat610_gate_identity"] = "0" * 64
        mutations.append(expect_rejection("bat610_rewrite", lambda: _validate(_mutated_gate(gate, upstream_identities=upstream5))))
        upstream4 = json.loads(json.dumps(gate["upstream_identities"]))
        upstream4["bat605_gate_identity"] = "0" * 64
        mutations.append(expect_rejection("bat605_rewrite", lambda: _validate(_mutated_gate(gate, upstream_identities=upstream4))))
        invented = json.loads(json.dumps(gate))
        invented["selected_seasons"] = [2005]
        invented["gate_identity"] = compute_gate_identity(invented)
        mutations.append(expect_rejection("selected_season_tamper", lambda: _validate(invented)))
        mutations.append(
            expect_rejection(
                "forged_completion_after_rehash",
                lambda: _validate(_mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")),
            )
        )
        mutations.append(
            expect_rejection(
                "acquisition_hash_tamper",
                lambda: _validate(_mutated_gate(gate, acquisition_identity="0" * 64)),
            )
        )
        mutations.append(
            expect_rejection(
                "games_identity_ordering_tamper",
                lambda: _validate(_mutated_gate(gate, games_identity="0" * 64)),
            )
        )
        counts4 = json.loads(json.dumps(gate["counts"]))
        counts4["normalized_games"] = 13
        counts4["metadata_only_games"] = 13
        mutations.append(expect_rejection("membership_row_inserted", lambda: _validate(_mutated_gate(gate, counts=counts4))))
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
