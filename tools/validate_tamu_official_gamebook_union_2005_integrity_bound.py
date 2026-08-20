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

from aggie_analytics.data.tamu_official_gamebook_union_2005_integrity_bound import (  # noqa: E402
    HARDCODED_PARENT_FALLBACK,
    OFFICIAL_2005_INDEX_URL,
    PINNED_BAT601_PAYLOAD_IDENTITY,
    PRESERVED_REJECTION_URLS,
    AuthorityViolation,
    GATE_RELATIVE,
    compact_official_2005,
    compute_gate_identity,
    load_json,
    reconstruct_objects,
    recompute_bat600_identities,
    recompute_bat601_payload_identity,
    validate_artifact,
    validate_bat600_external_payload,
    validate_bat601_external_payload,
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


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently validate the 2005 integrity-bound official union.")
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
        gate = load_json(repo_root / GATE_RELATIVE)
        objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
        bat600 = _copy(objects["bat600"]["payload"])
        bat601 = _copy(objects["bat601"]["payload"])

        def _validate(tampered: dict[str, Any], rebuild: bool = False) -> Any:
            return validate_artifact(
                repo_root=repo_root,
                data_root=data_root,
                gate=tampered,
                require_rebuild=rebuild,
            )

        def _validate_payloads(bat600_payload: dict[str, Any] | None = None, bat601_payload: dict[str, Any] | None = None) -> Any:
            return validate_artifact(
                repo_root=repo_root,
                data_root=data_root,
                require_rebuild=True,
                bat600_payload=bat600_payload,
                bat601_payload=bat601_payload,
            )

        mutations.append(expect_rejection("protected_lane_opened", lambda: _validate(_mutated_gate(gate, protected_lane="OPEN"))))
        mutations.append(
            expect_rejection(
                "forged_done_verified_completion",
                lambda: _validate(_mutated_gate(gate, result="DONE", classification="VERIFIED")),
            )
        )
        counts = _copy(gate["counts"])
        counts["ncaa_contest_ids_created"] = 1
        mutations.append(expect_rejection("ncaa_contest_id_inserted", lambda: _validate(_mutated_gate(gate, counts=counts))))
        games = _copy(gate["enriched_official_games"])
        games[0]["ncaa_contest_id"] = "NCAA-FORGED-001"
        mutations.append(expect_rejection("ncaa_id_on_game", lambda: _validate(_mutated_gate(gate, enriched_official_games=games))))
        admitted = _copy(gate["enriched_official_games"])
        admitted.append(_copy(gate["preserved_rejections"][0]))
        mutations.append(expect_rejection("rejected_url_admitted", lambda: _validate(_mutated_gate(gate, enriched_official_games=admitted))))
        admissions = _copy(gate["admissions"])
        admissions["pregame_availability"] = "OPEN"
        mutations.append(expect_rejection("availability_promoted", lambda: _validate(_mutated_gate(gate, admissions=admissions))))

        opponent = _copy(bat600)
        opponent["games"][0]["opponent_candidate"] = "FORGED OPPONENT"
        mutations.append(expect_rejection("bat600_opponent_changed_identities_unchanged", lambda: _validate_payloads(bat600_payload=opponent)))
        score = _copy(bat600)
        score["games"][0]["tamu_points"] = 99
        mutations.append(expect_rejection("bat600_score_changed", lambda: _validate_payloads(bat600_payload=score)))
        source_sha = _copy(bat600)
        source_sha["games"][0]["source_sha256"] = "0" * 64
        mutations.append(expect_rejection("bat600_source_sha_changed", lambda: _validate_payloads(bat600_payload=source_sha)))
        parent_removed = _copy(bat600)
        parent_removed["games"][0].pop("parent_url", None)
        mutations.append(expect_rejection("bat600_parent_url_removed", lambda: _validate_payloads(bat600_payload=parent_removed)))
        parent_sub = _copy(bat600)
        parent_sub["games"][0]["parent_url"] = "https://files.12thman.com/history/football/years/2004.html"
        mutations.append(expect_rejection("bat600_parent_url_substituted", lambda: _validate_payloads(bat600_payload=parent_sub)))
        captures = _copy(bat600)
        captures["captures"] = captures["captures"][1:]
        mutations.append(expect_rejection("bat600_capture_membership_changed", lambda: _validate_payloads(bat600_payload=captures)))
        conflict = _copy(bat600)
        conflict["conflicts"] = conflict["conflicts"][1:]
        mutations.append(expect_rejection("bat600_conflict_omitted", lambda: _validate_payloads(bat600_payload=conflict)))

        row_changed = _copy(bat601)
        if row_changed["rows"][0]:
            row_changed["rows"][0][0]["cells"] = ["FORGED"]
        mutations.append(expect_rejection("bat601_row_changed", lambda: _validate_payloads(bat601_payload=row_changed)))
        row_removed = _copy(bat601)
        row_removed["rows"][0] = row_removed["rows"][0][1:]
        mutations.append(expect_rejection("bat601_row_removed", lambda: _validate_payloads(bat601_payload=row_removed)))
        row_added = _copy(bat601)
        extra = _copy(row_added["rows"][0][0]) if row_added["rows"][0] else {"domain": "team_statistics", "cells": ["FORGED"]}
        row_added["rows"][0] = list(row_added["rows"][0]) + [extra]
        mutations.append(expect_rejection("bat601_row_added", lambda: _validate_payloads(bat601_payload=row_added)))
        present_zero = _copy(bat601)
        present_zero["rows"][0] = []
        present_zero["games"][0]["team_statistics"] = []
        present_zero["games"][0]["domain_coverage"]["team_statistics"] = "PRESENT"
        mutations.append(expect_rejection("bat601_present_with_zero_rows", lambda: _validate_payloads(bat601_payload=present_zero)))
        parser = _copy(bat601)
        parser["games"][0]["parser_identity"] = "forged.parser.v0"
        mutations.append(expect_rejection("bat601_parser_identity_changed", lambda: _validate_payloads(bat601_payload=parser)))
        availability = _copy(bat601)
        availability["availability_claim"] = True
        mutations.append(expect_rejection("bat601_availability_promoted", lambda: _validate_payloads(bat601_payload=availability)))

        compact = _copy((load_json(repo_root / "artifacts/data_lake/tamu_official_2005_structured_domains_gate.json")).get("games") or [])
        compact[0]["row_counts"]["team_statistics"] = int(compact[0]["row_counts"]["team_statistics"]) + 1
        mutations.append(
            expect_rejection(
                "bat601_gate_row_count_changed",
                lambda: validate_bat601_external_payload(
                    repo_root=repo_root,
                    data_root=data_root,
                    payload=bat601,
                    compact_games=compact,
                ),
            )
        )

        coordinated = _copy(bat600)
        coordinated["games"][0]["opponent_candidate"] = "COORDINATED TAMPER"
        coordinated.update(recompute_bat600_identities(coordinated))
        coordinated_601 = _copy(bat601)
        if coordinated_601["rows"][0]:
            coordinated_601["rows"][0][0]["source_label"] = "COORDINATED TAMPER"
        coordinated_601["payload_identity"] = recompute_bat601_payload_identity(coordinated_601)
        mutations.append(
            expect_rejection(
                "coordinated_external_tamper_plus_recomputed_outer_identity",
                lambda: _validate_payloads(bat600_payload=coordinated, bat601_payload=coordinated_601),
            )
        )
        mutations.append(
            expect_rejection(
                "parent_url_fallback_direct",
                lambda: compact_official_2005({"url": "https://example.invalid/box"}, OFFICIAL_2005_INDEX_URL),
            )
        )
        if gate["upstream_identities"]["bat601_payload_identity"] != PINNED_BAT601_PAYLOAD_IDENTITY:
            raise AssertionError("successor must bind the pinned BAT-601 payload identity")
        if HARDCODED_PARENT_FALLBACK not in OFFICIAL_2005_INDEX_URL and any(
            not item.get("parent_url") for item in gate["admitted_official_2005_games"]
        ):
            raise AssertionError("successor admitted a 2005 game without parent_url")
        rejected = {item["url"] for item in gate["preserved_rejections"]}
        if rejected != set(PRESERVED_REJECTION_URLS):
            raise AssertionError("successor dropped a preserved rejection")
        validate_bat600_external_payload(repo_root=repo_root, data_root=data_root)
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
