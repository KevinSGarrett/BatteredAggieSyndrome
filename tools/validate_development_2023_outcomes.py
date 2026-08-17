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

from aggie_analytics.data.development_2023_outcomes import (  # noqa: E402
    PASS_RESULT,
    compute_gate_identity,
    expected_scientific_nonclaims,
    load_contract,
    rebuild_expected,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, FileNotFoundError, AssertionError) as exc:
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
        description="Independently validate the 2023 development-outcome identity."
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
        expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
        gate = json.loads((repo_root / "artifacts/pit/development_2023_outcome_gate.json").read_text(encoding="utf-8"))
        manifest_path = (
            data_root
            / "manifests"
            / "development_outcomes"
            / "sha256"
            / expected["dataset_identity"]
            / "development_2023_outcome_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        load_contract(repo_root)

        def _validate(tampered_gate: dict[str, Any], tampered_manifest: dict[str, Any] | None = None) -> Any:
            return validate_artifact(
                data_root=data_root,
                repo_root=repo_root,
                require_rebuild=True,
                gate=tampered_gate,
                manifest=tampered_manifest if tampered_manifest is not None else manifest,
                expected=expected,
            )

        mutations.append(
            expect_rejection(
                "altered_result_after_identity_recompute",
                lambda: _validate(_mutated_gate(gate, result="PASS_PRODUCTION_READY")),
            )
        )
        mutations.append(
            expect_rejection(
                "altered_classification_after_identity_recompute",
                lambda: _validate(_mutated_gate(gate, classification="PROTECTED_PERFORMANCE")),
            )
        )
        mutations.append(
            expect_rejection(
                "altered_parent_identity_after_identity_recompute",
                lambda: _validate(
                    _mutated_gate(
                        gate,
                        input_identities={
                            **gate["input_identities"],
                            "parent_identities": {
                                **gate["input_identities"]["parent_identities"],
                                "BAT-523_replay": "0" * 64,
                            },
                        },
                    )
                ),
            )
        )
        mutations.append(
            expect_rejection(
                "altered_source_identity_after_identity_recompute",
                lambda: _validate(
                    _mutated_gate(
                        gate,
                        input_identities={
                            **gate["input_identities"],
                            "source_payload_sha256": "1" * 64,
                        },
                    )
                ),
            )
        )
        nonclaims = dict(expected_scientific_nonclaims())
        nonclaims["protected_performance_claimed"] = True
        mutations.append(
            expect_rejection(
                "altered_protected_nonclaims_after_identity_recompute",
                lambda: _validate(_mutated_gate(gate, scientific_nonclaims=nonclaims)),
            )
        )
        completion = dict(gate["issue_completion"])
        completion["issue_complete"] = False
        mutations.append(
            expect_rejection(
                "altered_issue_completion_after_identity_recompute",
                lambda: _validate(_mutated_gate(gate, issue_completion=completion)),
            )
        )
        semantics = dict(gate["label_semantics"])
        semantics["availability_boundary_strictly_after_kickoff"] = False
        mutations.append(
            expect_rejection(
                "altered_completion_semantics_after_identity_recompute",
                lambda: _validate(_mutated_gate(gate, label_semantics=semantics)),
            )
        )
        omitted = dict(manifest)
        omitted["payloads"] = list(manifest["payloads"][1:])
        mutations.append(
            expect_rejection(
                "missing_payload_after_identity_recompute",
                lambda: _validate(_mutated_gate(gate), omitted),
            )
        )
        substituted = json.loads(json.dumps(manifest))
        substituted["payloads"][0]["sha256"] = "2" * 64
        mutations.append(
            expect_rejection(
                "substituted_payload_after_identity_recompute",
                lambda: _validate(_mutated_gate(gate, payloads=[{**gate["payloads"][0], "sha256": "2" * 64}, *gate["payloads"][1:]]), substituted),
            )
        )
        forged = _mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        if forged["gate_identity"] == gate["gate_identity"]:
            raise AssertionError("forged terminal state failed to recompute a distinct outer identity")
        mutations.append(
            expect_rejection(
                "forged_terminal_state_after_identity_recompute",
                lambda: _validate(forged),
            )
        )
        if result.get("result") != "PASS" or result.get("dataset_identity") == gate.get("supersession", {}).get("dataset_identity"):
            raise AssertionError("active identity must not remain the superseded kickoff identity")
        if PASS_RESULT != "PASS_DEVELOPMENT_ONLY_2023_LABELS":
            raise AssertionError("pass result constant drifted")
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
