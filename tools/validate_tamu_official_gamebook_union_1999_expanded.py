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

from aggie_analytics.data.tamu_official_gamebook_union_1999_expanded import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    OFFICIAL_1999_REJECTED_EXPECTED,
    PINNED_BAT631_GATE_IDENTITY,
    PINNED_BAT632_PAYLOAD_IDENTITY,
    compute_gate_identity,
    validate_artifact,
 )  # pylint: disable=import-error


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
        description="Independently validate the 1999-expanded official union."
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(
            os.environ.get(
                "AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"
            )
        ),
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    result = validate_artifact(repo_root=repo_root, data_root=data_root)
    mutations: list[dict[str, Any]] = []
    if not args.validate_only:
        gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8-sig"))

        def _validate(tampered: dict[str, Any]) -> Any:
            return validate_artifact(
                repo_root=repo_root, data_root=data_root, gate=tampered
            )

        mutations.append(
            expect_rejection(
                "protected_lane_opened",
                lambda: _validate(_mutated_gate(gate, protected_lane="OPEN")),
            )
        )
        counts = json.loads(json.dumps(gate["counts"]))
        counts["official_1999_rejected"] = OFFICIAL_1999_REJECTED_EXPECTED + 1
        mutations.append(
            expect_rejection(
                "official_1999_rejected_count_forged",
                lambda: _validate(_mutated_gate(gate, counts=counts)),
            )
        )
        up = json.loads(json.dumps(gate["upstream_identities"]))
        up["bat631_gate_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat631_identity_rewritten",
                lambda: _validate(_mutated_gate(gate, upstream_identities=up)),
            )
        )
        up2 = json.loads(json.dumps(gate["upstream_identities"]))
        up2["bat632_payload_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat632_payload_identity_rewritten",
                lambda: _validate(_mutated_gate(gate, upstream_identities=up2)),
            )
        )
        if gate["upstream_identities"]["bat631_gate_identity"] != PINNED_BAT631_GATE_IDENTITY:
            raise AssertionError("successor must bind pinned BAT-631 identity")
        if gate["upstream_identities"]["bat632_payload_identity"] != PINNED_BAT632_PAYLOAD_IDENTITY:
            raise AssertionError("successor must bind pinned BAT-632 payload identity")
    print(
        json.dumps(
            {"validation": result, "mutations": mutations}, indent=2, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
