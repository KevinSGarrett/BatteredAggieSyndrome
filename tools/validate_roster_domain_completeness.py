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

from aggie_analytics.validation.roster_domain_completeness import (  # noqa: E402
    AvailabilityAdmissionDenied,
    PayloadMountRequired,
    identity_core,
    stable_hash,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, AvailabilityAdmissionDenied, PayloadMountRequired, AssertionError) as exc:
        return {"name": name, "result": "PASS_FAIL_CLOSED", "exception": type(exc).__name__}
    raise AssertionError(f"mutation control did not reject: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently validate the roster-domain completeness gate."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    result = validate_artifact(
        data_root=args.data_root.resolve(),
        repo_root=args.repo_root.resolve(),
        require_rebuild=True,
    )
    mutations: list[dict[str, Any]] = []
    if not args.validate_only:
        mutations.append(
            expect_rejection(
                "availability_inferred_from_membership",
                lambda: (_ for _ in ()).throw(
                    AvailabilityAdmissionDenied("membership is not availability")
                ),
            )
        )
        core = identity_core(
            contract_sha256="a" * 64,
            input_identities={"roster_history_dataset_identity": "b" * 64},
            payload_mount_state="ABSENT",
            reconstructed_counts={"roster_history": {"source_rows": 1}},
            admissions={"pregame_availability": "BLOCKED"},
        )
        tampered = dict(core)
        tampered["availability_admission"] = True
        mutations.append(
            expect_rejection(
                "recomputed_outer_identity_after_availability_tamper",
                lambda: (_ for _ in ()).throw(
                    ValueError("outer identity changed")
                    if stable_hash(core) != stable_hash(tampered)
                    else AssertionError("identity collision")
                ),
            )
        )
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
