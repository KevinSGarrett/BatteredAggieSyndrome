from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_2004_expanded import (  # noqa: E402
    PINNED_UNION_IDENTITY as PINNED_BAT607_UNION_IDENTITY,
    union_manifest_path as bat607_union_manifest_path,
    validate_artifact as validate_bat607,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_integrity_bound import (  # noqa: E402
    PINNED_UNION_IDENTITY as PINNED_BAT603_UNION_IDENTITY,
    union_manifest_path as bat603_union_manifest_path,
    validate_artifact as validate_bat603,
)
from aggie_analytics.data.tamu_official_gamebook_union_integrity_complete import (  # noqa: E402
    PRESERVED_REJECTION_URLS,
    AuthorityViolation,
    GATE_RELATIVE,
    compute_gate_identity,
    load_json,
    recompute_bat606_payload_identity,
    reconstruct_objects,
    union_manifest_path,
    validate_artifact,
    validate_bat606_raw_reconstruction,
    write_json,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, AuthorityViolation, FileNotFoundError, OSError, json.JSONDecodeError, AssertionError) as exc:
        return {
            "name": name,
            "result": "PASS_FAIL_CLOSED",
            "exception": type(exc).__name__,
            "message": str(exc)[:240],
        }
    raise AssertionError(f"mutation control did not reject: {name}")


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _mutated_gate(gate: dict[str, Any], **changes: Any) -> dict[str, Any]:
    tampered = _copy(gate)
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


@contextmanager
def _temporarily_moved(path: Path) -> Iterator[Path]:
    hidden = path.with_name(path.name + ".hidden_cycle15")
    if hidden.exists():
        hidden.unlink()
    path.replace(hidden)
    try:
        yield hidden
    finally:
        if path.exists():
            path.unlink()
        hidden.replace(path)


@contextmanager
def _temporarily_written(path: Path, payload: Any) -> Iterator[None]:
    original = path.read_bytes()
    if isinstance(payload, (bytes, bytearray)):
        path.write_bytes(payload)
    else:
        write_json(path, payload)
    try:
        yield
    finally:
        path.write_bytes(original)


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently validate the integrity-complete official union.")
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
        bat606 = _copy(objects["bat606"]["payload"])
        bat603_path = bat603_union_manifest_path(data_root)
        bat607_path = bat607_union_manifest_path(data_root)
        successor_path = union_manifest_path(data_root, str(gate["union_identity"]))

        def _validate(tampered: dict[str, Any], rebuild: bool = False) -> Any:
            return validate_artifact(
                repo_root=repo_root,
                data_root=data_root,
                gate=tampered,
                require_rebuild=rebuild,
            )

        def _hide_and_validate(path: Path, name: str, validator: Callable[[], Any]) -> None:
            mutations.append(
                expect_rejection(
                    name,
                    lambda: _run_hidden(path, validator),
                )
            )

        def _run_hidden(path: Path, validator: Callable[[], Any]) -> Any:
            with _temporarily_moved(path):
                return validator()

        _hide_and_validate(
            bat603_path,
            "missing_bat603_union_manifest",
            lambda: validate_bat603(repo_root=repo_root, data_root=data_root, require_rebuild=True),
        )
        _hide_and_validate(
            bat607_path,
            "missing_bat607_union_manifest",
            lambda: validate_bat607(repo_root=repo_root, data_root=data_root, require_rebuild=True),
        )
        _hide_and_validate(
            successor_path,
            "missing_successor_union_manifest",
            lambda: validate_artifact(repo_root=repo_root, data_root=data_root, require_rebuild=True),
        )

        substituted = _copy(load_json(bat607_path))
        substituted["counts"]["new_games_added"] = 99
        mutations.append(
            expect_rejection(
                "substituted_bat607_union_manifest",
                lambda: _run_written(
                    bat607_path,
                    substituted,
                    lambda: validate_bat607(repo_root=repo_root, data_root=data_root, require_rebuild=True),
                ),
            )
        )
        altered = _copy(load_json(bat607_path))
        altered["enriched_official_games"][0]["opponent_candidate"] = "ALTERED WHILE IDENTITY UNCHANGED"
        mutations.append(
            expect_rejection(
                "altered_bat607_manifest_declared_identity_unchanged",
                lambda: _run_written(
                    bat607_path,
                    altered,
                    lambda: validate_bat607(repo_root=repo_root, data_root=data_root, require_rebuild=True),
                ),
            )
        )
        extra_path = bat607_path.with_name("extra_manifest.json")
        extra_path.write_text("{}\n", encoding="utf-8")
        try:
            mutations.append(
                expect_rejection(
                    "extra_bat607_union_manifest",
                    lambda: validate_bat607(repo_root=repo_root, data_root=data_root, require_rebuild=True),
                )
            )
        finally:
            if extra_path.exists():
                extra_path.unlink()

        row_sha = _copy(bat606)
        if row_sha["rows"][0]:
            row_sha["rows"][0][0]["source_sha256"] = "0" * 64
        mutations.append(
            expect_rejection(
                "altered_bat606_row_source_sha",
                lambda: validate_artifact(repo_root=repo_root, data_root=data_root, bat606_payload=row_sha),
            )
        )
        season = _copy(bat606)
        season["games"][0]["source_season"] = 1999
        if season["rows"][0]:
            season["rows"][0][0]["source_season"] = 1999
        mutations.append(
            expect_rejection(
                "changed_source_season",
                lambda: validate_artifact(repo_root=repo_root, data_root=data_root, bat606_payload=season),
            )
        )
        parser = _copy(bat606)
        parser["games"][0]["parser_identity"] = "forged.parser.v0"
        if parser["rows"][0]:
            parser["rows"][0][0]["parser_identity"] = "forged.parser.v0"
        mutations.append(
            expect_rejection(
                "changed_parser_identity",
                lambda: validate_artifact(repo_root=repo_root, data_root=data_root, bat606_payload=parser),
            )
        )
        domain = _copy(bat606)
        if domain["rows"][0]:
            domain["rows"][0][0]["domain"] = "forged_domain"
            domain["rows"][0][0]["source_domain"] = "forged_domain"
        mutations.append(
            expect_rejection(
                "changed_domain",
                lambda: validate_artifact(repo_root=repo_root, data_root=data_root, bat606_payload=domain),
            )
        )
        duplicate = _copy(bat606)
        if duplicate["rows"][0]:
            duplicate["rows"][0] = list(duplicate["rows"][0]) + [_copy(duplicate["rows"][0][0])]
        mutations.append(
            expect_rejection(
                "duplicate_rows",
                lambda: validate_artifact(repo_root=repo_root, data_root=data_root, bat606_payload=duplicate),
            )
        )
        gapped = _copy(bat606)
        if gapped["rows"][0]:
            gapped["rows"][0] = gapped["rows"][0][1:]
        mutations.append(
            expect_rejection(
                "gapped_rows",
                lambda: validate_artifact(repo_root=repo_root, data_root=data_root, bat606_payload=gapped),
            )
        )
        reordered = _copy(bat606)
        if len(reordered["rows"][0]) > 1:
            reordered["rows"][0] = list(reversed(reordered["rows"][0]))
        mutations.append(
            expect_rejection(
                "reordered_rows",
                lambda: validate_artifact(repo_root=repo_root, data_root=data_root, bat606_payload=reordered),
            )
        )
        present_zero = _copy(bat606)
        present_zero["rows"][0] = []
        present_zero["games"][0]["team_statistics"] = []
        present_zero["games"][0]["domain_coverage"]["team_statistics"] = "PRESENT"
        mutations.append(
            expect_rejection(
                "present_with_zero_rows",
                lambda: validate_artifact(repo_root=repo_root, data_root=data_root, bat606_payload=present_zero),
            )
        )
        warnings = _copy(bat606)
        warnings["games"][0]["warnings"] = ["forged warning"]
        warnings["games"][0]["rich_structured"] = not bool(warnings["games"][0].get("rich_structured"))
        mutations.append(
            expect_rejection(
                "changed_warning_or_rich_classification",
                lambda: validate_artifact(repo_root=repo_root, data_root=data_root, bat606_payload=warnings),
            )
        )
        coordinated_606 = _copy(bat606)
        if coordinated_606["rows"][0]:
            coordinated_606["rows"][0][0]["source_label"] = "COORDINATED TAMPER"
        coordinated_606["payload_identity"] = recompute_bat606_payload_identity(coordinated_606)
        mutations.append(
            expect_rejection(
                "coordinated_bat606_mutation_plus_recomputed_identity",
                lambda: validate_artifact(repo_root=repo_root, data_root=data_root, bat606_payload=coordinated_606),
            )
        )
        mutations.append(
            expect_rejection(
                "coordinated_upstream_plus_recomputed_outer_identity",
                lambda: validate_artifact(
                    repo_root=repo_root,
                    data_root=data_root,
                    gate=_mutated_gate(gate, union_identity="0" * 64),
                    require_rebuild=True,
                    bat606_payload=coordinated_606,
                ),
            )
        )
        admitted = _copy(gate["enriched_official_games"])
        admitted.append(_copy(gate["preserved_rejections"][0]))
        mutations.append(expect_rejection("rejected_url_admitted", lambda: _validate(_mutated_gate(gate, enriched_official_games=admitted))))
        counts = _copy(gate["counts"])
        counts["ncaa_contest_ids_created"] = 1
        mutations.append(expect_rejection("ncaa_id_inserted", lambda: _validate(_mutated_gate(gate, counts=counts))))
        games = _copy(gate["enriched_official_games"])
        games[0]["ncaa_contest_id"] = "NCAA-FORGED-001"
        mutations.append(expect_rejection("ncaa_id_on_game", lambda: _validate(_mutated_gate(gate, enriched_official_games=games))))
        admissions = _copy(gate["admissions"])
        admissions["pregame_availability"] = "OPEN"
        mutations.append(expect_rejection("availability_promoted", lambda: _validate(_mutated_gate(gate, admissions=admissions))))
        mutations.append(expect_rejection("protected_lane_opened", lambda: _validate(_mutated_gate(gate, protected_lane="OPEN"))))
        mutations.append(
            expect_rejection(
                "forged_done_verified_completion",
                lambda: _validate(_mutated_gate(gate, result="DONE", classification="VERIFIED")),
            )
        )
        validate_bat606_raw_reconstruction(repo_root=repo_root, data_root=data_root)
        rejected = {item["url"] for item in gate["preserved_rejections"]}
        if rejected != set(PRESERVED_REJECTION_URLS):
            raise AssertionError("successor dropped a preserved rejection")
        if int(gate["counts"]["new_games_added"]) != 0:
            raise AssertionError("successor added games")
        if int(gate["counts"]["union_captured_games"]) != 273:
            raise AssertionError("successor did not preserve 273 union games")
        if gate["upstream_identities"]["bat603_union_identity"] != PINNED_BAT603_UNION_IDENTITY:
            raise AssertionError("successor must pin the BAT-603 union identity")
        if gate["upstream_identities"]["bat607_union_identity"] != PINNED_BAT607_UNION_IDENTITY:
            raise AssertionError("successor must pin the BAT-607 union identity")
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


def _run_written(path: Path, payload: Any, validator: Callable[[], Any]) -> Any:
    with _temporarily_written(path, payload):
        return validator()


if __name__ == "__main__":
    raise SystemExit(main())
