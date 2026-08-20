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

from aggie_analytics.data.tamu_official_gamebook_union_2005_expanded import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    PINNED_BAT601_PAYLOAD_IDENTITY,
    PRESERVED_REJECTION_URLS,
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
    parser = argparse.ArgumentParser(description="Independently validate the 2005-expanded official union.")
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

        def _validate(tampered: dict[str, Any], rebuild: bool = False) -> Any:
            return validate_artifact(repo_root=repo_root, data_root=data_root, gate=tampered, require_rebuild=rebuild)

        mutations.append(expect_rejection("protected_lane_opened", lambda: _validate(_mutated_gate(gate, protected_lane="OPEN"))))
        mutations.append(expect_rejection("bat597_rewrite", lambda: _validate(_mutated_gate(gate, prior_union_identity="0" * 64))))
        upstream = json.loads(json.dumps(gate["upstream_identities"]))
        upstream["bat601_payload_identity"] = "0" * 64
        mutations.append(expect_rejection("bat601_row_payload_rewrite", lambda: _validate(_mutated_gate(gate, upstream_identities=upstream))))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        mutations.append(expect_rejection("ncaa_contest_ids_forged", lambda: _validate(_mutated_gate(gate, counts=counts))))
        counts2 = json.loads(json.dumps(gate["counts"]))
        counts2["new_games_added"] = 10
        mutations.append(expect_rejection("dropped_2005_admission", lambda: _validate(_mutated_gate(gate, counts=counts2))))
        counts3 = json.loads(json.dumps(gate["counts"]))
        counts3["rich_structured_games"] = int(counts3["rich_structured_games"]) + 1
        mutations.append(expect_rejection("coverage_arithmetic_tamper", lambda: _validate(_mutated_gate(gate, counts=counts3), rebuild=True)))
        rejected = json.loads(json.dumps(gate["preserved_rejections"]))
        rejected = [item for item in rejected if item.get("url") != next(iter(PRESERVED_REJECTION_URLS))]
        mutations.append(expect_rejection("dropped_rejection", lambda: _validate(_mutated_gate(gate, preserved_rejections=rejected))))
        admissions = json.loads(json.dumps(gate["admissions"]))
        admissions["pregame_availability"] = "OPEN"
        mutations.append(expect_rejection("availability_admitted", lambda: _validate(_mutated_gate(gate, admissions=admissions))))
        mutations.append(
            expect_rejection(
                "forged_completion_after_rehash",
                lambda: _validate(_mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")),
            )
        )
        if gate["upstream_identities"]["bat601_payload_identity"] != PINNED_BAT601_PAYLOAD_IDENTITY:
            raise AssertionError("union must bind BAT-601 structured-row payload identity")
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
