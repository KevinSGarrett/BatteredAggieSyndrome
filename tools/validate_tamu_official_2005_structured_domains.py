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

from aggie_analytics.data.tamu_official_2005_structured_domains import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    compute_gate_identity,
    validate_artifact,
)
from aggie_analytics.data.tamu_official_html_table_classifier import classify_headers  # noqa: E402


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
    parser = argparse.ArgumentParser(description="Independently validate official 2005 structured domains.")
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
        counts = json.loads(json.dumps(gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        mutations.append(expect_rejection("ncaa_contest_ids_forged", lambda: _validate(_mutated_gate(gate, counts=counts))))
        counts2 = json.loads(json.dumps(gate["counts"]))
        counts2["pregame_availability_present"] = 1
        mutations.append(expect_rejection("availability_claimed", lambda: _validate(_mutated_gate(gate, counts=counts2))))
        upstream = json.loads(json.dumps(gate["upstream_identities"]))
        upstream["bat596_gate_identity"] = "0" * 64
        mutations.append(expect_rejection("bat596_rewrite", lambda: _validate(_mutated_gate(gate, upstream_identities=upstream))))
        upstream591 = json.loads(json.dumps(gate["upstream_identities"]))
        upstream591["bat591_gate_identity"] = "0" * 64
        mutations.append(expect_rejection("bat591_rewrite", lambda: _validate(_mutated_gate(gate, upstream_identities=upstream591))))
        html = json.loads(json.dumps(gate["html_table_classifications"]))
        html["texas_2006"]["domain_coverage"]["play_by_play"] = "PRESENT"
        mutations.append(expect_rejection("forged_html_pbp_presence", lambda: _validate(_mutated_gate(gate, html_table_classifications=html))))
        html2 = json.loads(json.dumps(gate["html_table_classifications"]))
        html2["texas_2006"]["rows_identity"] = "0" * 64
        mutations.append(expect_rejection("html_row_identity_tamper", lambda: _validate(_mutated_gate(gate, html_table_classifications=html2))))
        html3 = json.loads(json.dumps(gate["html_table_classifications"]))
        html3["texas_2006"]["source_sha256"] = "0" * 64
        mutations.append(expect_rejection("html_source_hash_tamper", lambda: _validate(_mutated_gate(gate, html_table_classifications=html3))))
        html4 = json.loads(json.dumps(gate["html_table_classifications"]))
        swapped = html4["texas_2006"]["rows_identity"]
        html4["texas_2006"]["rows_identity"] = html4["montana_state_2007"]["rows_identity"]
        html4["montana_state_2007"]["rows_identity"] = swapped
        mutations.append(expect_rejection("html_table_order_or_row_swap", lambda: _validate(_mutated_gate(gate, html_table_classifications=html4))))
        html5 = json.loads(json.dumps(gate["html_table_classifications"]))
        html5["texas_2006"]["availability_claim"] = True
        mutations.append(expect_rejection("participation_as_availability", lambda: _validate(_mutated_gate(gate, html_table_classifications=html5))))
        mutations.append(
            expect_rejection(
                "forged_completion_after_rehash",
                lambda: _validate(_mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")),
            )
        )
        if classify_headers([]) != "unknown":
            raise AssertionError("empty headers must fail closed as unknown")
        if classify_headers(["RUSHING", "No.", "Yds"]) == classify_headers(["Yds", "RUSHING", "No."]) and classify_headers(["Yds", "RUSHING", "No."]) == "individual_player_statistics":
            raise AssertionError("reordered headers must not keep a forged player-stat classification")
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
