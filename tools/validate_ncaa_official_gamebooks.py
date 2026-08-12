from __future__ import annotations

"""Validate NCAA official captures, provenance, authority, and deterministic rebuild."""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from aggie_analytics.data.adapters import AcquisitionFailure  # noqa: E402
from acquire_ncaa_official_gamebooks import (  # noqa: E402
    build_gate,
    canonical_json_bytes,
    inspect_ncaa_html,
    inspect_ncaa_team_page,
    load_optional_dotenv_value,
    sha256_file,
    stable_hash,
    validate_official_uri,
    write_immutable_json,
    write_json,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, RuntimeError, AssertionError, AcquisitionFailure) as error:
        return {"name": name, "result": "PASS_FAIL_CLOSED", "exception": type(error).__name__}
    raise AssertionError(f"mutation control did not reject: {name}")


def manifest_core(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in manifest.items()
        if key not in {"acquisition_identity", "issued_at_utc", "credentials_logged_or_persisted"}
    }


def discovery_manifest_core(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in manifest.items()
        if key not in {"discovery_identity", "issued_at_utc", "credentials_logged_or_persisted"}
    }


def validate_authority(authority: dict[str, Any]) -> None:
    if authority.get("immutable_private_raw_archive") is not True:
        raise ValueError("immutable private raw authority must remain enabled")
    if authority.get("candidate_normalization_and_reconciliation") is not True:
        raise ValueError("candidate processing authority must remain enabled")
    for key in (
        "canonical_entity_mutation",
        "historical_pit_admission",
        "preliminary_training_admission",
        "protected_training_or_evaluation",
        "champion_or_production_promotion",
        "forecast_publication",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"unsafe NCAA authority is open: {key}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--contract", type=Path, required=True)
    result.add_argument("--gate", type=Path, required=True)
    result.add_argument("--rebuild-root", type=Path, required=True)
    result.add_argument("--env-file", type=Path)
    result.add_argument("--discovery-manifest", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    contract_path = args.contract.resolve()
    gate_path = args.gate.resolve()
    rebuild_root = args.rebuild_root.resolve()
    if repo_root not in contract_path.parents or repo_root not in gate_path.parents:
        raise ValueError("contract and gate must be versioned in the repository")
    if rebuild_root.exists():
        raise ValueError(f"rebuild root already exists: {rebuild_root}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    manifest_path = Path(gate["manifest"]["path"]).resolve()
    if data_root != manifest_path and data_root not in manifest_path.parents:
        raise ValueError("manifest is outside the configured external data root")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-197")
    check("jira_key", manifest["jira_key"] == "BAT-554")
    check("classification", manifest["classification"] == contract["classification"])
    check("contract_hash", manifest["contract_sha256"] == sha256_file(contract_path))
    check("manifest_hash", gate["manifest"]["sha256"] == sha256_file(manifest_path))
    check("manifest_identity", manifest["acquisition_identity"] == stable_hash(manifest_core(manifest)))
    check("gate_identity", gate["manifest"]["acquisition_identity"] == manifest["acquisition_identity"])
    check("request_conservation", manifest["request_count"] == len(manifest["captures"]))
    captured = [row for row in manifest["captures"] if row["state"] == "CAPTURED"]
    failed = [row for row in manifest["captures"] if row["state"] != "CAPTURED"]
    check("capture_conservation", manifest["captured_count"] == len(captured))
    check("failure_conservation", manifest["technical_failure_count"] == len(failed))
    check("bounded_real_capture", len(captured) > 0, len(captured))
    check("gate_result", gate["result"] == "PASS_BOUNDED_CANDIDATE_CAPTURE")
    validate_authority(contract["authority"])
    validate_authority(manifest["authority"])
    validate_authority(gate["authority"])
    checks.append({"name": "candidate_only_authority", "result": "PASS"})
    check("canonical_identity_closed", gate["identity_gate"]["canonical_game_identity_promoted"] is False)
    check("name_only_merge_closed", gate["identity_gate"]["name_only_match_promoted"] is False)
    check("historical_pit_closed", gate["pit_gate"]["historical_pit_eligible"] is False)
    check("same_game_pregame_closed", gate["pit_gate"]["same_game_pregame_eligible"] is False)
    check("target_outcome_excluded", gate["pit_gate"]["target_game_outcome_excluded"] is True)
    check("national_scaleout_closed", gate["scale_out_gate"]["automatic_national_scale_out_enabled"] is False)
    check("partial_domain_independence", gate["scale_out_gate"]["partial_domain_does_not_block_unrelated_valid_domains"] is True)
    for key, value in gate["scientific_nonclaims"].items():
        check(f"scientific_nonclaim_{key}", value is False)

    payload_profiles: list[dict[str, Any]] = []
    normalized_domain_counts: dict[str, int] = {}
    normalized_row_counts: dict[str, int] = {}
    for row in captured:
        validate_official_uri(row["source_uri"])
        raw_path = data_root / row["raw_relative_path"]
        check(f"raw_exists_{row['contest_id']}_{row['endpoint_id']}", raw_path.is_file())
        check(f"raw_bytes_{row['contest_id']}_{row['endpoint_id']}", raw_path.stat().st_size == row["raw_bytes"])
        check(f"raw_hash_{row['contest_id']}_{row['endpoint_id']}", sha256_file(raw_path) == row["raw_sha256"])
        profile = inspect_ncaa_html(
            raw_path.read_bytes(),
            contest_id=row["contest_id"],
            endpoint_id=row["endpoint_id"],
            contract=contract,
        )
        check(
            f"row_count_{row['contest_id']}_{row['endpoint_id']}",
            int(profile["row_count"]) == int(row["row_count"]),
        )
        check(
            f"schema_{row['contest_id']}_{row['endpoint_id']}",
            profile["schema_fields"] == row["schema_fields"],
        )
        check(f"canonical_unpromoted_{row['contest_id']}_{row['endpoint_id']}", row["canonical_game_id"] is None)
        destination = rebuild_root / row["raw_relative_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(raw_path, destination)
        check(
            f"byte_identical_rebuild_{row['contest_id']}_{row['endpoint_id']}",
            destination.read_bytes() == raw_path.read_bytes(),
        )
        payload_profiles.append(profile)
        for normalized in row.get("normalization", []):
            domain = normalized["domain"]
            normalized_path = data_root / normalized["payload_relative_path"]
            check(f"normalized_exists_{row['contest_id']}_{domain}", normalized_path.is_file())
            check(
                f"normalized_bytes_{row['contest_id']}_{domain}",
                normalized_path.stat().st_size == normalized["payload_bytes"],
            )
            check(
                f"normalized_hash_{row['contest_id']}_{domain}",
                sha256_file(normalized_path) == normalized["payload_sha256"],
            )
            payload = json.loads(normalized_path.read_text(encoding="utf-8"))
            payload_core = {key: value for key, value in payload.items() if key != "normalization_identity"}
            check(
                f"normalized_identity_{row['contest_id']}_{domain}",
                payload["normalization_identity"] == stable_hash(payload_core) == normalized["normalization_identity"],
            )
            check(f"normalized_source_{row['contest_id']}_{domain}", payload["source_raw_sha256"] == row["raw_sha256"])
            check(
                f"normalized_rows_{row['contest_id']}_{domain}",
                int(payload["row_count"]) == len(payload["records"]) == int(normalized["row_count"]),
            )
            check(
                f"normalized_parser_pin_{row['contest_id']}_{domain}",
                payload["parser"]["repository_commit"] == contract["source"]["upstream_parser_commit"],
            )
            check(f"normalized_pit_closed_{row['contest_id']}_{domain}", payload["historical_pit_eligible"] is False)
            check(
                f"normalized_canonical_closed_{row['contest_id']}_{domain}",
                payload["canonical_identity_promoted"] is False,
            )
            rebuilt_normalized = rebuild_root / normalized["payload_relative_path"]
            rebuilt_normalized.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(normalized_path, rebuilt_normalized)
            check(
                f"byte_identical_normalized_{row['contest_id']}_{domain}",
                rebuilt_normalized.read_bytes() == normalized_path.read_bytes(),
            )
            if normalized["state"] == "PARSED_CANDIDATE":
                normalized_domain_counts[domain] = normalized_domain_counts.get(domain, 0) + 1
                normalized_row_counts[domain] = normalized_row_counts.get(domain, 0) + int(normalized["row_count"])

    check("normalized_domain_counts", normalized_domain_counts == manifest["normalized_domain_counts"])
    check("normalized_row_counts", normalized_row_counts == manifest["normalized_row_counts"])
    check("all_contract_domains_nonempty", set(normalized_domain_counts) == set(contract["domain_grain"]))
    check(
        "gate_normalized_domain_counts",
        gate["bounded_population"]["normalized_domain_counts"] == manifest["normalized_domain_counts"],
    )

    discovery_summary: dict[str, Any] | None = None
    if args.discovery_manifest:
        discovery_path = args.discovery_manifest.resolve()
        check("discovery_external_boundary", data_root == discovery_path or data_root in discovery_path.parents)
        discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
        gate_discovery = gate.get("discovery_population")
        check("gate_discovery_present", isinstance(gate_discovery, dict))
        check("discovery_artifact_type", discovery["artifact_type"] == "NCAA_OFFICIAL_TEAM_GRAPH_DISCOVERY_MANIFEST")
        check("discovery_decision_unit", discovery["decision_unit"] == contract["decision_unit"])
        check("discovery_jira_key", discovery["jira_key"] == contract["jira_key"])
        check("discovery_classification", discovery["classification"] == contract["classification"])
        check(
            "discovery_identity",
            discovery["discovery_identity"] == stable_hash(discovery_manifest_core(discovery)),
        )
        check("discovery_season_configured", str(discovery["season"]) in contract["discovery"]["seed_team_season_ids"])
        check(
            "discovery_seed_identity",
            discovery["seed_team_season_id"]
            == str(contract["discovery"]["seed_team_season_ids"][str(discovery["season"])]),
        )
        check("discovery_graph_exhausted", discovery["state"] == "COMPLETE_GRAPH_EXHAUSTED")
        check("discovery_queue_empty", discovery["remaining_queue"] == [])
        check("discovery_no_unresolved_failures", discovery["failures"] == [])
        check("discovery_failure_conservation", discovery["team_failure_count"] == len(discovery["failures"]))
        check("discovery_capture_conservation", discovery["team_page_capture_count"] == len(discovery["captures"]))
        captured_team_ids = [row["team_season_id"] for row in discovery["captures"]]
        discovered_team_ids = discovery["discovered_team_season_ids"]
        check("discovery_team_ids_unique", len(discovered_team_ids) == len(set(discovered_team_ids)))
        check("discovery_capture_ids_unique", len(captured_team_ids) == len(set(captured_team_ids)))
        check("discovery_capture_population", set(captured_team_ids) == set(discovered_team_ids))
        discovered_contests = discovery["discovered_contest_ids"]
        check("discovery_contest_ids_unique", len(discovered_contests) == len(set(discovered_contests)))
        replay_contests: set[str] = set()
        target_season_label = f"{discovery['season']}-{(int(discovery['season']) + 1) % 100:02d}"
        for row in discovery["captures"]:
            validate_official_uri(row["source_uri"])
            raw_path = data_root / row["raw_relative_path"]
            suffix = row["team_season_id"]
            check(f"discovery_raw_exists_{suffix}", raw_path.is_file())
            check(f"discovery_raw_bytes_{suffix}", raw_path.stat().st_size == row["raw_bytes"])
            check(f"discovery_raw_hash_{suffix}", sha256_file(raw_path) == row["raw_sha256"])
            profile = inspect_ncaa_team_page(raw_path.read_bytes(), contract=contract)
            check(f"discovery_profile_team_links_{suffix}", profile["team_season_ids"] == row["team_season_ids"])
            check(f"discovery_profile_contests_{suffix}", profile["contest_ids"] == row["contest_ids"])
            check(f"discovery_profile_seasons_{suffix}", profile["season_options"] == row["season_options"])
            selected_team = profile["season_options"].get(target_season_label)
            check(
                f"discovery_target_season_binding_{suffix}",
                selected_team is None or selected_team == row["team_season_id"],
            )
            request_binding_path = (
                data_root
                / "request_cache"
                / row["request_identity_sha256"][:2]
                / f"{row['request_identity_sha256']}.json"
            )
            check(f"discovery_request_binding_exists_{suffix}", request_binding_path.is_file())
            request_binding = json.loads(request_binding_path.read_text(encoding="utf-8"))
            check(
                f"discovery_request_binding_identity_{suffix}",
                request_binding["request_identity_sha256"] == row["request_identity_sha256"],
            )
            check(
                f"discovery_request_binding_snapshot_{suffix}",
                request_binding["snapshot_id"] == row["snapshot_id"],
            )
            check(
                f"discovery_request_binding_hash_{suffix}",
                request_binding["raw_sha256"] == row["raw_sha256"],
            )
            replay_contests.update(profile["contest_ids"])
        check("discovery_contest_population", replay_contests == set(discovered_contests))
        validate_authority(discovery["authority"])
        check("discovery_credentials_not_persisted", discovery["credentials_logged_or_persisted"] is False)
        check("gate_discovery_season", gate_discovery["season"] == discovery["season"])
        check("gate_discovery_state", gate_discovery["state"] == discovery["state"])
        check(
            "gate_discovery_identity",
            gate_discovery["manifest"]["discovery_identity"] == discovery["discovery_identity"],
        )
        check("gate_discovery_hash", gate_discovery["manifest"]["sha256"] == sha256_file(discovery_path))
        check("gate_discovery_path", Path(gate_discovery["manifest"]["path"]).resolve() == discovery_path)
        check(
            "gate_discovery_counts",
            gate_discovery["team_page_capture_count"] == discovery["team_page_capture_count"]
            and gate_discovery["team_failure_count"] == discovery["team_failure_count"]
            and gate_discovery["discovered_contest_count"] == len(discovered_contests)
            and gate_discovery["remaining_queue_count"] == len(discovery["remaining_queue"]),
        )
        check("gate_discovery_canonical_closed", gate_discovery["canonical_identity_promoted"] is False)
        check("gate_discovery_pit_closed", gate_discovery["historical_pit_eligible"] is False)
        rebuilt_discovery_path = rebuild_root / "discovery_manifest.json"
        write_immutable_json(rebuilt_discovery_path, discovery)
        check(
            "byte_identical_discovery_manifest_rebuild",
            rebuilt_discovery_path.read_bytes() == discovery_path.read_bytes(),
        )
        discovery_summary = {
            "season": discovery["season"],
            "state": discovery["state"],
            "discovery_identity": discovery["discovery_identity"],
            "manifest_path": str(discovery_path),
            "manifest_sha256": sha256_file(discovery_path),
            "team_page_capture_count": discovery["team_page_capture_count"],
            "discovered_contest_count": len(discovered_contests),
            "team_failure_count": discovery["team_failure_count"],
            "remaining_queue_count": len(discovery["remaining_queue"]),
        }

    rebuilt_manifest_path = rebuild_root / "manifest.json"
    write_immutable_json(rebuilt_manifest_path, manifest)
    check("byte_identical_manifest_rebuild", rebuilt_manifest_path.read_bytes() == manifest_path.read_bytes())
    rebuilt_gate = build_gate(
        contract=contract,
        manifest=manifest,
        manifest_path=manifest_path,
        manifest_sha256=sha256_file(manifest_path),
        discovery_manifest=(
            json.loads(args.discovery_manifest.resolve().read_text(encoding="utf-8"))
            if args.discovery_manifest
            else None
        ),
        discovery_manifest_path=args.discovery_manifest.resolve() if args.discovery_manifest else None,
        discovery_manifest_sha256=(sha256_file(args.discovery_manifest.resolve()) if args.discovery_manifest else None),
    )
    rebuilt_gate_path = rebuild_root / "gate.json"
    write_json(rebuilt_gate_path, rebuilt_gate)
    check("byte_identical_gate_rebuild", rebuilt_gate_path.read_bytes() == gate_path.read_bytes())

    serialized_evidence = canonical_json_bytes({"manifest": manifest, "gate": gate})
    secret_names = ("SCRAPFLY_API_TOKEN", "SCRAPERAPI_API_TOKEN")
    checked_secret_count = 0
    if args.env_file:
        for name in secret_names:
            credential_value = load_optional_dotenv_value(args.env_file.resolve(), name)
            if credential_value:
                checked_secret_count += 1
                check(f"secret_absent_{name}", credential_value.encode("utf-8") not in serialized_evidence)
    check("credential_persistence_flag", manifest["credentials_logged_or_persisted"] is False)

    first_endpoint = contract["endpoints"][0]["endpoint_id"]
    mutations = [
        expect_rejection(
            "anti_bot_interstitial",
            lambda: inspect_ncaa_html(
                b"<html><body>NCAA bm-verify _abck</body></html>",
                contest_id="5362283",
                endpoint_id=first_endpoint,
                contract=contract,
            ),
        ),
        expect_rejection(
            "thin_payload",
            lambda: inspect_ncaa_html(
                b"<html><body>NCAA Box Score</body></html>",
                contest_id="5362283",
                endpoint_id=first_endpoint,
                contract=contract,
            ),
        ),
        expect_rejection(
            "unsafe_host",
            lambda: validate_official_uri("https://example.com/contests/5362283/box_score"),
        ),
        expect_rejection(
            "credential_query",
            lambda: validate_official_uri("https://stats.ncaa.org/contests/5362283/box_score?token=secret"),
        ),
        expect_rejection(
            "historical_pit_authority_open",
            lambda: validate_authority({**contract["authority"], "historical_pit_admission": True}),
        ),
        expect_rejection(
            "canonical_mutation_authority_open",
            lambda: validate_authority({**contract["authority"], "canonical_entity_mutation": True}),
        ),
    ]
    checks.extend(mutations)
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "NCAA_OFFICIAL_GAMEBOOK_VALIDATION_REPORT",
        "decision_unit": "POST-SUBTASK-197",
        "jira_key": "BAT-554",
        "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "result": "PASS",
        "acquisition_identity": manifest["acquisition_identity"],
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "gate_path": str(gate_path),
        "gate_sha256": sha256_file(gate_path),
        "captured_count": len(captured),
        "technical_failure_count": len(failed),
        "payload_profiles": payload_profiles,
        "check_count": len(checks),
        "mutation_control_count": len(mutations),
        "configured_secret_values_checked_without_logging": checked_secret_count,
        "discovery": discovery_summary,
        "checks": checks,
    }
    report_root = data_root / "validation" / "POST-SUBTASK-197"
    report_path = report_root / "ncaa_official_gamebook_validation.json"
    write_json(report_path, report)
    print(
        json.dumps(
            {
                "result": "PASS",
                "checks": len(checks),
                "mutation_controls": len(mutations),
                "captured_count": len(captured),
                "technical_failure_count": len(failed),
                "report_path": str(report_path),
                "report_sha256": sha256_file(report_path),
                "rebuild_root": str(rebuild_root),
                "discovery": discovery_summary,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
