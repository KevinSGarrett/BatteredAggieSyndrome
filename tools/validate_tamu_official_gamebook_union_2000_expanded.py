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

from aggie_analytics.data.tamu_official_gamebook_union_2000_expanded import (  # noqa: E402
    FORBIDDEN_UNION_URLS,
    OFFICIAL_2000_INDEX_URL,
    OFFICIAL_2000_UNMATCHED_URLS,
    OKLAHOMA_2002_UNMATCHED_URL,
    PINNED_BAT602_UNION_IDENTITY,
    PINNED_BAT624_UNION_IDENTITY,
    PINNED_BAT627_PAYLOAD_IDENTITY,
    PRESERVED_REJECTION_URLS,
    AuthorityViolation,
    GATE_RELATIVE,
    compact_official_2000,
    compute_code_identity,
    compute_gate_identity,
    load_json,
    reconstruct_objects,
    recompute_bat622_identities,
    recompute_bat627_payload_identity,
    validate_artifact,
    validate_bat626_external_payload,
    validate_bat627_external_payload,
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
    parser = argparse.ArgumentParser(
        description="Independently validate the 2000-expanded official union."
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
        gate = load_json(repo_root / GATE_RELATIVE)
        objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
        bat622 = _copy(objects["bat622"]["payload"])
        bat623 = _copy(objects["bat623"]["payload"])
        official_index_urls = [
            str(item.get("url") or "") for item in objects["bat622"]["games"]
        ]

        def _validate(tampered: dict[str, Any], rebuild: bool = False) -> Any:
            return validate_artifact(
                repo_root=repo_root,
                data_root=data_root,
                gate=tampered,
                require_rebuild=rebuild,
            )

        def _validate_payloads(
            bat626_payload: dict[str, Any] | None = None,
            bat627_payload: dict[str, Any] | None = None,
        ) -> Any:
            return validate_artifact(
                repo_root=repo_root,
                data_root=data_root,
                require_rebuild=True,
                bat626_payload=bat626_payload,
                bat627_payload=bat627_payload,
            )

        mutations.append(
            expect_rejection(
                "protected_lane_opened",
                lambda: _validate(_mutated_gate(gate, protected_lane="OPEN")),
            )
        )
        mutations.append(
            expect_rejection(
                "forged_done_verified_completion",
                lambda: _validate(
                    _mutated_gate(gate, result="DONE", classification="VERIFIED")
                ),
            )
        )
        counts = _copy(gate["counts"])
        counts["ncaa_contest_ids_created"] = 1
        mutations.append(
            expect_rejection(
                "ncaa_contest_id_inserted",
                lambda: _validate(_mutated_gate(gate, counts=counts)),
            )
        )
        games = _copy(gate["enriched_official_games"])
        games[0]["ncaa_contest_id"] = "NCAA-FORGED-001"
        mutations.append(
            expect_rejection(
                "ncaa_id_on_game",
                lambda: _validate(_mutated_gate(gate, enriched_official_games=games)),
            )
        )
        admitted = _copy(gate["enriched_official_games"])
        admitted.append(_copy(gate["preserved_rejections"][0]))
        mutations.append(
            expect_rejection(
                "rejected_url_admitted",
                lambda: _validate(
                    _mutated_gate(gate, enriched_official_games=admitted)
                ),
            )
        )
        oklahoma = _copy(gate["enriched_official_games"])
        oklahoma.append(
            {
                "url": OKLAHOMA_2002_UNMATCHED_URL,
                "canonical_game_match_status": "UNMATCHED_STRONG_TUPLE",
                "availability": "NOT_ESTABLISHED",
                "availability_claim": False,
                "ncaa_contest_id": None,
            }
        )
        mutations.append(
            expect_rejection(
                "oklahoma_unmatched_admitted",
                lambda: _validate(
                    _mutated_gate(gate, enriched_official_games=oklahoma)
                ),
            )
        )
        unmatched_2000 = _copy(gate["enriched_official_games"])
        unmatched_2000.append(
            {
                "url": sorted(OFFICIAL_2000_UNMATCHED_URLS)[0],
                "canonical_game_match_status": "UNMATCHED_STRONG_TUPLE",
                "availability": "NOT_ESTABLISHED",
                "availability_claim": False,
                "ncaa_contest_id": None,
            }
        )
        mutations.append(
            expect_rejection(
                "unmatched_2000_url_admitted",
                lambda: _validate(
                    _mutated_gate(gate, enriched_official_games=unmatched_2000)
                ),
            )
        )
        admissions = _copy(gate["admissions"])
        admissions["pregame_availability"] = "OPEN"
        mutations.append(
            expect_rejection(
                "availability_promoted",
                lambda: _validate(_mutated_gate(gate, admissions=admissions)),
            )
        )
        admissions_429 = _copy(gate["admissions"])
        admissions_429["bat_429"] = "DONE_VERIFIED"
        mutations.append(
            expect_rejection(
                "bat_429_advanced",
                lambda: _validate(_mutated_gate(gate, admissions=admissions_429)),
            )
        )
        predecessor = _copy(gate)
        predecessor["predecessor_union_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat624_union_rewritten", lambda: _validate(_mutated_gate(predecessor))
            )
        )
        bat608 = _copy(gate["upstream_identities"])
        bat608["bat608_union_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat608_union_rewritten",
                lambda: _validate(_mutated_gate(gate, upstream_identities=bat608)),
            )
        )
        bat602 = _copy(gate["upstream_identities"])
        bat602["bat602_union_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat602_union_rewritten",
                lambda: _validate(_mutated_gate(gate, upstream_identities=bat602)),
            )
        )
        stale_code = _copy(gate)
        stale_code["validator_code_identity"] = "0" * 64
        mutations.append(
            expect_rejection(
                "stale_validator_code_identity",
                lambda: _validate(_mutated_gate(stale_code)),
            )
        )

        opponent = _copy(bat622)
        opponent["games"][0]["opponent_candidate"] = "FORGED OPPONENT"
        mutations.append(
            expect_rejection(
                "bat622_opponent_changed_identities_unchanged",
                lambda: _validate_payloads(bat626_payload=opponent),
            )
        )
        score = _copy(bat622)
        score["games"][0]["tamu_points"] = 99
        mutations.append(
            expect_rejection(
                "bat622_score_changed", lambda: _validate_payloads(bat626_payload=score)
            )
        )
        source_sha = _copy(bat622)
        source_sha["games"][0]["source_sha256"] = "0" * 64
        mutations.append(
            expect_rejection(
                "bat622_source_sha_changed",
                lambda: _validate_payloads(bat626_payload=source_sha),
            )
        )
        parent_removed = _copy(bat622)
        parent_removed["games"][0].pop("parent_url", None)
        mutations.append(
            expect_rejection(
                "bat622_parent_url_removed",
                lambda: _validate_payloads(bat626_payload=parent_removed),
            )
        )
        parent_sub = _copy(bat622)
        parent_sub["games"][0]["parent_url"] = (
            "https://files.12thman.com/history/football/years/2002.html"
        )
        mutations.append(
            expect_rejection(
                "bat622_parent_url_substituted",
                lambda: _validate_payloads(bat626_payload=parent_sub),
            )
        )
        captures = _copy(bat622)
        captures["captures"] = captures["captures"][1:]
        mutations.append(
            expect_rejection(
                "bat622_capture_membership_changed",
                lambda: _validate_payloads(bat626_payload=captures),
            )
        )
        name_only = _copy(bat622)
        name_only["games"][0]["canonical_game_match_status"] = (
            "MATCHED_OPPONENT_NAME_ONLY"
        )
        mutations.append(
            expect_rejection(
                "opponent_name_only_admission",
                lambda: _validate_payloads(bat626_payload=name_only),
            )
        )

        row_changed = _copy(bat623)
        if row_changed["rows"][0]:
            row_changed["rows"][0][0]["cells"] = ["FORGED"]
        mutations.append(
            expect_rejection(
                "bat623_row_changed",
                lambda: _validate_payloads(bat627_payload=row_changed),
            )
        )
        row_removed = _copy(bat623)
        row_removed["rows"][0] = row_removed["rows"][0][1:]
        mutations.append(
            expect_rejection(
                "bat623_row_removed",
                lambda: _validate_payloads(bat627_payload=row_removed),
            )
        )
        row_added = _copy(bat623)
        extra = (
            _copy(row_added["rows"][0][0])
            if row_added["rows"][0]
            else {"domain": "team_statistics", "cells": ["FORGED"]}
        )
        row_added["rows"][0] = list(row_added["rows"][0]) + [extra]
        mutations.append(
            expect_rejection(
                "bat623_row_added", lambda: _validate_payloads(bat627_payload=row_added)
            )
        )
        present_zero = _copy(bat623)
        present_zero["rows"][0] = []
        present_zero["games"][0]["team_statistics"] = []
        present_zero["games"][0]["domain_coverage"]["team_statistics"] = "PRESENT"
        mutations.append(
            expect_rejection(
                "bat623_present_with_zero_rows",
                lambda: _validate_payloads(bat627_payload=present_zero),
            )
        )
        missing_prov = _copy(bat623)
        if missing_prov["rows"][0]:
            missing_prov["rows"][0][0]["source_sha256"] = ""
        mutations.append(
            expect_rejection(
                "bat623_missing_row_provenance",
                lambda: _validate_payloads(bat627_payload=missing_prov),
            )
        )
        parser = _copy(bat623)
        parser["games"][0]["parser_identity"] = "forged.parser.v0"
        mutations.append(
            expect_rejection(
                "bat623_parser_identity_changed",
                lambda: _validate_payloads(bat627_payload=parser),
            )
        )
        availability = _copy(bat623)
        availability["availability_claim"] = True
        mutations.append(
            expect_rejection(
                "bat623_availability_promoted",
                lambda: _validate_payloads(bat627_payload=availability),
            )
        )

        compact = _copy(
            (
                load_json(
                    repo_root
                    / "artifacts/data_lake/tamu_official_2000_structured_domains_gate.json"
                )
            ).get("games")
            or []
        )
        compact[0]["row_counts"]["team_statistics"] = (
            int(compact[0]["row_counts"]["team_statistics"]) + 1
        )
        mutations.append(
            expect_rejection(
                "bat623_gate_row_count_changed",
                lambda: validate_bat627_external_payload(
                    repo_root=repo_root,
                    data_root=data_root,
                    payload=bat623,
                    compact_games=compact,
                ),
            )
        )

        coordinated = _copy(bat622)
        coordinated["games"][0]["opponent_candidate"] = "COORDINATED TAMPER"
        coordinated.update(recompute_bat622_identities(coordinated))
        coordinated_623 = _copy(bat623)
        if coordinated_623["rows"][0]:
            coordinated_623["rows"][0][0]["source_label"] = "COORDINATED TAMPER"
        coordinated_623["payload_identity"] = recompute_bat627_payload_identity(
            coordinated_623
        )
        mutations.append(
            expect_rejection(
                "coordinated_external_tamper_plus_recomputed_outer_identity",
                lambda: _validate_payloads(
                    bat626_payload=coordinated, bat627_payload=coordinated_623
                ),
            )
        )
        mutations.append(
            expect_rejection(
                "parent_url_fallback_direct",
                lambda: compact_official_2000(
                    {"url": "https://example.invalid/box"}, OFFICIAL_2000_INDEX_URL
                ),
            )
        )
        if (
            gate["upstream_identities"]["bat627_payload_identity"]
            != PINNED_BAT627_PAYLOAD_IDENTITY
        ):
            raise AssertionError(
                "successor must bind the pinned BAT-627 payload identity"
            )
        if gate["predecessor_union_identity"] != PINNED_BAT624_UNION_IDENTITY:
            raise AssertionError("successor must pin the BAT-624 predecessor union")
        if (
            gate["upstream_identities"]["bat602_union_identity"]
            != PINNED_BAT602_UNION_IDENTITY
        ):
            raise AssertionError(
                "successor must preserve the BAT-602 predecessor identity"
            )
        if gate["validator_code_identity"] != compute_code_identity(repo_root):
            raise AssertionError(
                "successor must bind a real computed code-bundle identity"
            )
        if any(
            not item.get("parent_url") for item in gate["admitted_official_2000_games"]
        ):
            raise AssertionError("successor admitted a 2000 game without parent_url")
        rejected = {item["url"] for item in gate["preserved_rejections"]}
        if rejected != set(PRESERVED_REJECTION_URLS):
            raise AssertionError("successor dropped a preserved rejection")
        admitted_urls = {item["url"] for item in gate["enriched_official_games"]}
        if admitted_urls & set(FORBIDDEN_UNION_URLS):
            raise AssertionError("a forbidden URL was admitted")
        if OKLAHOMA_2002_UNMATCHED_URL in admitted_urls:
            raise AssertionError("Oklahoma unmatched strong-tuple was admitted")
        if admitted_urls & set(OFFICIAL_2000_UNMATCHED_URLS):
            raise AssertionError("an unmatched official 2000 URL was admitted")
        validate_bat626_external_payload(
            repo_root=repo_root,
            data_root=data_root,
            allowed_urls=official_index_urls,
        )
    print(
        json.dumps(
            {"validation": result, "mutations": mutations}, indent=2, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
