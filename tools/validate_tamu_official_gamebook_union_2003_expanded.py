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

from aggie_analytics.data.tamu_official_gamebook_union_2003_expanded import (  # noqa: E402
    OFFICIAL_2003_INDEX_URL,
    PINNED_BAT602_UNION_IDENTITY,
    PINNED_BAT608_UNION_IDENTITY,
    PINNED_BAT611_PAYLOAD_IDENTITY,
    PRESERVED_REJECTION_URLS,
    AuthorityViolation,
    GATE_RELATIVE,
    compact_official_2003,
    compute_gate_identity,
    load_json,
    reconstruct_objects,
    recompute_bat610_identities,
    recompute_bat611_payload_identity,
    validate_artifact,
    validate_bat610_external_payload,
    validate_bat611_external_payload,
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
    parser = argparse.ArgumentParser(description="Independently validate the 2003-expanded official union.")
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
        bat610 = _copy(objects["bat610"]["payload"])
        bat611 = _copy(objects["bat611"]["payload"])

        def _validate(tampered: dict[str, Any], rebuild: bool = False) -> Any:
            return validate_artifact(
                repo_root=repo_root,
                data_root=data_root,
                gate=tampered,
                require_rebuild=rebuild,
            )

        def _validate_payloads(
            bat610_payload: dict[str, Any] | None = None,
            bat611_payload: dict[str, Any] | None = None,
        ) -> Any:
            return validate_artifact(
                repo_root=repo_root,
                data_root=data_root,
                require_rebuild=True,
                bat610_payload=bat610_payload,
                bat611_payload=bat611_payload,
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
        admissions_429 = _copy(gate["admissions"])
        admissions_429["bat_429"] = "DONE_VERIFIED"
        mutations.append(expect_rejection("bat_429_advanced", lambda: _validate(_mutated_gate(gate, admissions=admissions_429))))
        predecessor = _copy(gate)
        predecessor["predecessor_union_identity"] = "0" * 64
        mutations.append(expect_rejection("bat608_union_rewritten", lambda: _validate(_mutated_gate(predecessor))))
        bat607 = _copy(gate["upstream_identities"])
        bat607["bat607_union_identity"] = "0" * 64
        mutations.append(expect_rejection("bat607_union_rewritten", lambda: _validate(_mutated_gate(gate, upstream_identities=bat607))))
        bat602 = _copy(gate["upstream_identities"])
        bat602["bat602_union_identity"] = "0" * 64
        mutations.append(expect_rejection("bat602_union_rewritten", lambda: _validate(_mutated_gate(gate, upstream_identities=bat602))))

        opponent = _copy(bat610)
        opponent["games"][0]["opponent_candidate"] = "FORGED OPPONENT"
        mutations.append(expect_rejection("bat610_opponent_changed_identities_unchanged", lambda: _validate_payloads(bat610_payload=opponent)))
        score = _copy(bat610)
        score["games"][0]["tamu_points"] = 99
        mutations.append(expect_rejection("bat610_score_changed", lambda: _validate_payloads(bat610_payload=score)))
        source_sha = _copy(bat610)
        source_sha["games"][0]["source_sha256"] = "0" * 64
        mutations.append(expect_rejection("bat610_source_sha_changed", lambda: _validate_payloads(bat610_payload=source_sha)))
        parent_removed = _copy(bat610)
        parent_removed["games"][0].pop("parent_url", None)
        mutations.append(expect_rejection("bat610_parent_url_removed", lambda: _validate_payloads(bat610_payload=parent_removed)))
        parent_sub = _copy(bat610)
        parent_sub["games"][0]["parent_url"] = "https://files.12thman.com/history/football/years/2004.html"
        mutations.append(expect_rejection("bat610_parent_url_substituted", lambda: _validate_payloads(bat610_payload=parent_sub)))
        captures = _copy(bat610)
        captures["captures"] = captures["captures"][1:]
        mutations.append(expect_rejection("bat610_capture_membership_changed", lambda: _validate_payloads(bat610_payload=captures)))
        name_only = _copy(bat610)
        name_only["games"][0]["canonical_game_match_status"] = "MATCHED_OPPONENT_NAME_ONLY"
        mutations.append(expect_rejection("opponent_name_only_admission", lambda: _validate_payloads(bat610_payload=name_only)))

        row_changed = _copy(bat611)
        if row_changed["rows"][0]:
            row_changed["rows"][0][0]["cells"] = ["FORGED"]
        mutations.append(expect_rejection("bat611_row_changed", lambda: _validate_payloads(bat611_payload=row_changed)))
        row_removed = _copy(bat611)
        row_removed["rows"][0] = row_removed["rows"][0][1:]
        mutations.append(expect_rejection("bat611_row_removed", lambda: _validate_payloads(bat611_payload=row_removed)))
        row_added = _copy(bat611)
        extra = _copy(row_added["rows"][0][0]) if row_added["rows"][0] else {"domain": "team_statistics", "cells": ["FORGED"]}
        row_added["rows"][0] = list(row_added["rows"][0]) + [extra]
        mutations.append(expect_rejection("bat611_row_added", lambda: _validate_payloads(bat611_payload=row_added)))
        present_zero = _copy(bat611)
        present_zero["rows"][0] = []
        present_zero["games"][0]["team_statistics"] = []
        present_zero["games"][0]["domain_coverage"]["team_statistics"] = "PRESENT"
        mutations.append(expect_rejection("bat611_present_with_zero_rows", lambda: _validate_payloads(bat611_payload=present_zero)))
        parser = _copy(bat611)
        parser["games"][0]["parser_identity"] = "forged.parser.v0"
        mutations.append(expect_rejection("bat611_parser_identity_changed", lambda: _validate_payloads(bat611_payload=parser)))
        availability = _copy(bat611)
        availability["availability_claim"] = True
        mutations.append(expect_rejection("bat611_availability_promoted", lambda: _validate_payloads(bat611_payload=availability)))

        compact = _copy((load_json(repo_root / "artifacts/data_lake/tamu_official_2003_structured_domains_gate.json")).get("games") or [])
        compact[0]["row_counts"]["team_statistics"] = int(compact[0]["row_counts"]["team_statistics"]) + 1
        mutations.append(
            expect_rejection(
                "bat611_gate_row_count_changed",
                lambda: validate_bat611_external_payload(
                    repo_root=repo_root,
                    data_root=data_root,
                    payload=bat611,
                    compact_games=compact,
                ),
            )
        )

        coordinated = _copy(bat610)
        coordinated["games"][0]["opponent_candidate"] = "COORDINATED TAMPER"
        coordinated.update(recompute_bat610_identities(coordinated))
        coordinated_611 = _copy(bat611)
        if coordinated_611["rows"][0]:
            coordinated_611["rows"][0][0]["source_label"] = "COORDINATED TAMPER"
        coordinated_611["payload_identity"] = recompute_bat611_payload_identity(coordinated_611)
        mutations.append(
            expect_rejection(
                "coordinated_external_tamper_plus_recomputed_outer_identity",
                lambda: _validate_payloads(bat610_payload=coordinated, bat611_payload=coordinated_611),
            )
        )
        mutations.append(
            expect_rejection(
                "parent_url_fallback_direct",
                lambda: compact_official_2003({"url": "https://example.invalid/box"}, OFFICIAL_2003_INDEX_URL),
            )
        )
        if gate["upstream_identities"]["bat611_payload_identity"] != PINNED_BAT611_PAYLOAD_IDENTITY:
            raise AssertionError("successor must bind the pinned BAT-611 payload identity")
        if gate["predecessor_union_identity"] != PINNED_BAT608_UNION_IDENTITY:
            raise AssertionError("successor must pin the BAT-608 predecessor union")
        if gate["upstream_identities"]["bat602_union_identity"] != PINNED_BAT602_UNION_IDENTITY:
            raise AssertionError("successor must preserve the BAT-602 predecessor identity")
        if any(not item.get("parent_url") for item in gate["admitted_official_2003_games"]):
            raise AssertionError("successor admitted a 2003 game without parent_url")
        rejected = {item["url"] for item in gate["preserved_rejections"]}
        if rejected != set(PRESERVED_REJECTION_URLS):
            raise AssertionError("successor dropped a preserved rejection")
        validate_bat610_external_payload(
            repo_root=repo_root,
            data_root=data_root,
            allowed_urls=[item["url"] for item in gate["admitted_official_2003_games"]],
        )
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
