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

from aggie_analytics.data.tamu_official_2006_season_index import (  # noqa: E402
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
            "exception": type(exc).__name__,
            "message": str(exc)[:240],
            "name": name,
            "result": "PASS_FAIL_CLOSED",
        }
    raise AssertionError(f"mutation control did not reject: {name}")


def _mutated_gate(gate: dict[str, Any], **changes: Any) -> dict[str, Any]:
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently validate the official 2006 season-index capture.")
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

        mutations.append(
            expect_rejection(
                "guessed_url",
                lambda: _validate(
                    _mutated_gate(gate, official_index_url="https://files.12thman.com/history/football/years/2005.html")
                ),
            )
        )
        capture = json.loads(json.dumps(gate["capture"]))
        capture["raw_sha256"] = "0" * 64
        mutations.append(expect_rejection("changed_raw_sha", lambda: _validate(_mutated_gate(gate, capture=capture))))
        rows = json.loads(json.dumps(gate["game_rows"]))
        extra = json.loads(json.dumps(rows[0]))
        extra["source_row_order"] = len(rows) + 1
        extra["source_opponent"] = "Invented Opponent"
        mutations.append(
            expect_rejection("inserted_game", lambda: _validate(_mutated_gate(gate, game_rows=rows + [extra])))
        )
        mutations.append(expect_rejection("removed_game", lambda: _validate(_mutated_gate(gate, game_rows=rows[:-1]))))
        reordered = list(reversed(rows))
        mutations.append(expect_rejection("reordered_games", lambda: _validate(_mutated_gate(gate, game_rows=reordered))))
        invented = list(gate["box_score_urls"]) + [
            "https://files.12thman.com/history/football/stats/2006-2007/invented.html"
        ]
        mutations.append(expect_rejection("invented_box_url", lambda: _validate(_mutated_gate(gate, box_score_urls=invented))))
        duplicated = list(gate["box_score_urls"])
        if duplicated:
            duplicated.append(duplicated[0])
        mutations.append(
            expect_rejection("duplicate_admitted_url", lambda: _validate(_mutated_gate(gate, box_score_urls=duplicated)))
        )
        counts = json.loads(json.dumps(gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        mutations.append(expect_rejection("ncaa_contest_ids_created", lambda: _validate(_mutated_gate(gate, counts=counts))))
        mutations.append(
            expect_rejection(
                "forged_completion_after_rehash",
                lambda: _validate(_mutated_gate(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")),
            )
        )
        mutations.append(
            expect_rejection("inventory_rewrite", lambda: _validate(_mutated_gate(gate, inventory_identity="0" * 64)))
        )
        mutations.append(expect_rejection("protected_lane_opened", lambda: _validate(_mutated_gate(gate, protected_lane="OPEN"))))
    print(json.dumps({"mutations": mutations, "validation": result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
