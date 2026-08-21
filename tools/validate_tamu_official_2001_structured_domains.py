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

from aggie_analytics.data.tamu_official_2001_structured_domains import (  # noqa: E402
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
        description="Independently validate official 2001 structured domains."
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
        gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8"))

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
        authority = json.loads(json.dumps(gate["authority"]))
        authority["participation_as_availability"] = True
        mutations.append(
            expect_rejection(
                "participation_as_availability",
                lambda: _validate(_mutated_gate(gate, authority=authority)),
            )
        )
        counts = json.loads(json.dumps(gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        mutations.append(
            expect_rejection(
                "ncaa_contest_ids_forged",
                lambda: _validate(_mutated_gate(gate, counts=counts)),
            )
        )
        counts2 = json.loads(json.dumps(gate["counts"]))
        counts2["pregame_availability_present"] = 1
        mutations.append(
            expect_rejection(
                "availability_claimed",
                lambda: _validate(_mutated_gate(gate, counts=counts2)),
            )
        )
        counts3 = json.loads(json.dumps(gate["counts"]))
        counts3["team_statistics_serialized_rows"] = 0
        counts3["team_statistics_present_games"] = 12
        mutations.append(
            expect_rejection(
                "coverage_without_rows",
                lambda: _validate(_mutated_gate(gate, counts=counts3)),
            )
        )
        upstream = json.loads(json.dumps(gate["upstream_identities"]))
        upstream["bat622_gate_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat622_rewrite",
                lambda: _validate(_mutated_gate(gate, upstream_identities=upstream)),
            )
        )
        upstream = json.loads(json.dumps(gate["upstream_identities"]))
        upstream["bat621_gate_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat621_rewrite",
                lambda: _validate(_mutated_gate(gate, upstream_identities=upstream)),
            )
        )
        upstream = json.loads(json.dumps(gate["upstream_identities"]))
        upstream["bat617_gate_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat617_rewrite",
                lambda: _validate(_mutated_gate(gate, upstream_identities=upstream)),
            )
        )
        upstream = json.loads(json.dumps(gate["upstream_identities"]))
        upstream["bat615_gate_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat615_rewrite",
                lambda: _validate(_mutated_gate(gate, upstream_identities=upstream)),
            )
        )
        upstream = json.loads(json.dumps(gate["upstream_identities"]))
        upstream["bat611_gate_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat611_rewrite",
                lambda: _validate(_mutated_gate(gate, upstream_identities=upstream)),
            )
        )
        upstream2 = json.loads(json.dumps(gate["upstream_identities"]))
        upstream2["html_table_classifier_identity"] = "forged.classifier.v9"
        mutations.append(
            expect_rejection(
                "classifier_identity_mutated",
                lambda: _validate(_mutated_gate(gate, upstream_identities=upstream2)),
            )
        )
        mutations.append(
            expect_rejection(
                "forged_completion_after_rehash",
                lambda: _validate(
                    _mutated_gate(
                        gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"
                    )
                ),
            )
        )
        mutations.append(
            expect_rejection(
                "payload_identity_tamper",
                lambda: _validate(_mutated_gate(gate, payload_identity="0" * 64)),
            )
        )
        mutations.append(
            expect_rejection(
                "stale_code_identity",
                lambda: _validate(
                    _mutated_gate(gate, validator_code_identity="0" * 64)
                ),
            )
        )
        counts4 = json.loads(json.dumps(gate["counts"]))
        counts4["scoring_summary_serialized_rows"] = 0
        counts4["scoring_summary_present_games"] = 12
        mutations.append(
            expect_rejection(
                "scoring_invented_from_flag",
                lambda: _validate(_mutated_gate(gate, counts=counts4)),
            )
        )
    print(
        json.dumps(
            {"validation": result, "mutations": mutations}, indent=2, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
