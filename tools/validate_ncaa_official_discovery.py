"""Validate one immutable NCAA official team-season discovery population."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from aggie_analytics.data.adapters import AcquisitionFailure  # noqa: E402
from acquire_ncaa_official_gamebooks import (  # noqa: E402
    canonical_json_bytes,
    inspect_ncaa_team_page,
    load_optional_dotenv_value,
    sha256_file,
    stable_hash,
    validate_official_uri,
    write_immutable_json,
)


def discovery_manifest_core(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in manifest.items()
        if key
        not in {
            "discovery_identity",
            "issued_at_utc",
            "credentials_logged_or_persisted",
        }
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


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, AssertionError, AcquisitionFailure) as error:
        return {
            "name": name,
            "result": "PASS_FAIL_CLOSED",
            "exception": type(error).__name__,
        }
    raise AssertionError(f"mutation control did not reject: {name}")


def validate_discovery_population(
    *,
    discovery: dict[str, Any],
    contract: dict[str, Any],
    check: Callable[[str, bool, Any], None],
    prefix: str = "",
) -> tuple[list[str], list[str]]:
    """Validate successful and failed team pages as one honest population."""

    captures = discovery["captures"]
    failures = discovery["failures"]
    captured_team_ids = [str(row["team_season_id"]) for row in captures]
    failed_team_ids = [str(row["team_season_id"]) for row in failures]
    discovered_team_ids = [
        str(team_season_id)
        for team_season_id in discovery["discovered_team_season_ids"]
    ]

    check(
        f"{prefix}failure_conservation",
        discovery["team_failure_count"] == len(failures),
        discovery["team_failure_count"],
    )
    check(
        f"{prefix}capture_conservation",
        discovery["team_page_capture_count"] == len(captures),
        discovery["team_page_capture_count"],
    )
    check(
        f"{prefix}team_ids_unique",
        len(discovered_team_ids) == len(set(discovered_team_ids)),
        len(discovered_team_ids),
    )
    check(
        f"{prefix}capture_ids_unique",
        len(captured_team_ids) == len(set(captured_team_ids)),
        len(captured_team_ids),
    )
    check(
        f"{prefix}failure_ids_unique",
        len(failed_team_ids) == len(set(failed_team_ids)),
        len(failed_team_ids),
    )
    check(
        f"{prefix}capture_failure_disjoint",
        set(captured_team_ids).isdisjoint(failed_team_ids),
    )
    check(
        f"{prefix}team_population_conservation",
        set(discovered_team_ids) == set(captured_team_ids) | set(failed_team_ids),
        {
            "discovered": len(discovered_team_ids),
            "captured": len(captured_team_ids),
            "failed": len(failed_team_ids),
        },
    )

    expected_host = contract["source"]["official_host"]
    path_template = contract["discovery"]["path_template"]
    for row in failures:
        suffix = str(row["team_season_id"])
        check(f"{prefix}failure_team_id_numeric_{suffix}", suffix.isdigit())
        expected_uri = f"https://{expected_host}" + path_template.format(
            team_season_id=suffix
        )
        validate_official_uri(str(row["source_uri"]))
        check(
            f"{prefix}failure_source_binding_{suffix}",
            row["source_uri"] == expected_uri,
            row["source_uri"],
        )
        condition = row.get("condition")
        check(
            f"{prefix}failure_condition_{suffix}",
            isinstance(condition, str) and bool(condition.strip()),
            condition,
        )
        status_code = row.get("status_code")
        check(
            f"{prefix}failure_status_{suffix}",
            status_code is None
            or (
                isinstance(status_code, int)
                and not isinstance(status_code, bool)
                and 100 <= status_code <= 599
            ),
            status_code,
        )
        attempts = row.get("attempts")
        if attempts is not None:
            check(
                f"{prefix}failure_attempts_present_{suffix}",
                isinstance(attempts, list) and bool(attempts),
            )
            for index, attempt in enumerate(attempts):
                route_id = attempt.get("route_id")
                attempt_condition = attempt.get("condition")
                attempt_status = attempt.get("status_code")
                check(
                    f"{prefix}failure_attempt_route_{suffix}_{index}",
                    isinstance(route_id, str) and bool(route_id.strip()),
                    route_id,
                )
                check(
                    f"{prefix}failure_attempt_condition_{suffix}_{index}",
                    isinstance(attempt_condition, str)
                    and bool(attempt_condition.strip()),
                    attempt_condition,
                )
                check(
                    f"{prefix}failure_attempt_status_{suffix}_{index}",
                    attempt_status is None
                    or (
                        isinstance(attempt_status, int)
                        and not isinstance(attempt_status, bool)
                        and 100 <= attempt_status <= 599
                    ),
                    attempt_status,
                )
    check(
        f"{prefix}failures_preserved_as_quarantine",
        True,
        {
            "failed_team_pages": len(failures),
            "coverage_complete": not failures,
        },
    )
    return captured_team_ids, failed_team_ids


def validate_discovery(
    *,
    repo_root: Path,
    data_root: Path,
    contract_path: Path,
    discovery_path: Path,
    rebuild_root: Path,
    env_file: Path | None,
) -> tuple[dict[str, Any], Path]:
    repo_root = repo_root.resolve()
    data_root = data_root.resolve()
    contract_path = contract_path.resolve()
    discovery_path = discovery_path.resolve()
    rebuild_root = rebuild_root.resolve()
    if repo_root not in contract_path.parents:
        raise ValueError("contract must be versioned in the repository")
    if data_root != discovery_path and data_root not in discovery_path.parents:
        raise ValueError(
            "discovery manifest is outside the configured external data root"
        )
    if rebuild_root.exists():
        raise ValueError(f"rebuild root already exists: {rebuild_root}")

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check(
        "artifact_type",
        discovery["artifact_type"] == "NCAA_OFFICIAL_TEAM_GRAPH_DISCOVERY_MANIFEST",
    )
    check("schema_version", discovery["schema_version"] in {"1.0.0", "1.1.0"})
    check("decision_unit", discovery["decision_unit"] == contract["decision_unit"])
    check("jira_key", discovery["jira_key"] == contract["jira_key"])
    check("classification", discovery["classification"] == contract["classification"])
    check(
        "identity",
        discovery["discovery_identity"]
        == stable_hash(discovery_manifest_core(discovery)),
    )
    check(
        "identity_path_binding",
        discovery_path.parent.name == discovery["discovery_identity"],
    )
    season = str(discovery["season"])
    check("season_configured", season in contract["discovery"]["seed_team_season_ids"])
    check(
        "seed_identity",
        discovery["seed_team_season_id"]
        == str(contract["discovery"]["seed_team_season_ids"][season]),
    )
    check("graph_exhausted", discovery["state"] == "COMPLETE_GRAPH_EXHAUSTED")
    check("queue_empty", discovery["remaining_queue"] == [])
    validate_discovery_population(
        discovery=discovery,
        contract=contract,
        check=check,
    )
    discovered_contests = discovery["discovered_contest_ids"]
    check(
        "contest_ids_unique", len(discovered_contests) == len(set(discovered_contests))
    )
    validate_authority(contract["authority"])
    validate_authority(discovery["authority"])
    checks.append(
        {"name": "candidate_only_authority", "result": "PASS", "detail": None}
    )
    check(
        "credentials_not_persisted",
        discovery["credentials_logged_or_persisted"] is False,
    )

    replay_contests: set[str] = set()
    replay_legacy_schedule_count = 0
    target_season_label = f"{season}-{(int(season) + 1) % 100:02d}"
    for row in discovery["captures"]:
        suffix = row["team_season_id"]
        validate_official_uri(row["source_uri"])
        raw_path = data_root / row["raw_relative_path"]
        check(f"raw_exists_{suffix}", raw_path.is_file())
        check(f"raw_bytes_{suffix}", raw_path.stat().st_size == row["raw_bytes"])
        check(f"raw_hash_{suffix}", sha256_file(raw_path) == row["raw_sha256"])
        profile = inspect_ncaa_team_page(raw_path.read_bytes(), contract=contract)
        check(
            f"profile_team_links_{suffix}",
            profile["team_season_ids"] == row["team_season_ids"],
        )
        check(
            f"profile_contests_{suffix}", profile["contest_ids"] == row["contest_ids"]
        )
        check(
            f"profile_seasons_{suffix}",
            profile["season_options"] == row["season_options"],
        )
        if discovery["schema_version"] == "1.1.0":
            check(
                f"profile_legacy_schedule_{suffix}",
                profile["legacy_schedule_records"] == row["legacy_schedule_records"],
            )
            check(
                f"profile_legacy_schedule_count_{suffix}",
                profile["legacy_schedule_record_count"]
                == row["legacy_schedule_record_count"],
            )
            for legacy in row["legacy_schedule_records"]:
                legacy_suffix = f"{suffix}_{legacy['source_row_sha256'][:8]}"
                check(
                    f"legacy_contest_unresolved_{legacy_suffix}",
                    legacy["contest_id"] is None,
                )
                check(
                    f"legacy_canonical_game_unresolved_{legacy_suffix}",
                    legacy["canonical_game_id"] is None,
                )
                check(
                    f"legacy_candidate_only_{legacy_suffix}",
                    legacy["reconciliation_state"] == "SOURCE_LINKED_CANDIDATE_ONLY",
                )
            replay_legacy_schedule_count += profile["legacy_schedule_record_count"]
        selected_team = profile["season_options"].get(target_season_label)
        check(
            f"target_season_binding_{suffix}",
            selected_team is None or selected_team == suffix,
        )
        request_binding_path = (
            data_root
            / "request_cache"
            / row["request_identity_sha256"][:2]
            / f"{row['request_identity_sha256']}.json"
        )
        check(f"request_binding_exists_{suffix}", request_binding_path.is_file())
        request_binding = json.loads(request_binding_path.read_text(encoding="utf-8"))
        check(
            f"request_binding_identity_{suffix}",
            request_binding["request_identity_sha256"]
            == row["request_identity_sha256"],
        )
        check(
            f"request_binding_snapshot_{suffix}",
            request_binding["snapshot_id"] == row["snapshot_id"],
        )
        check(
            f"request_binding_hash_{suffix}",
            request_binding["raw_sha256"] == row["raw_sha256"],
        )
        replay_contests.update(profile["contest_ids"])
        destination = rebuild_root / row["raw_relative_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(raw_path, destination)
        check(
            f"byte_identical_raw_rebuild_{suffix}",
            destination.read_bytes() == raw_path.read_bytes(),
        )
    check("contest_population", replay_contests == set(discovered_contests))
    if discovery["schema_version"] == "1.1.0":
        check(
            "legacy_schedule_population",
            replay_legacy_schedule_count == discovery["legacy_schedule_record_count"],
        )

    rebuilt_manifest_path = rebuild_root / "discovery_manifest.json"
    write_immutable_json(rebuilt_manifest_path, discovery)
    check(
        "byte_identical_manifest_rebuild",
        rebuilt_manifest_path.read_bytes() == discovery_path.read_bytes(),
    )

    secret_names = ("SCRAPFLY_API_TOKEN", "SCRAPERAPI_API_TOKEN")
    serialized = canonical_json_bytes(discovery)
    checked_secret_count = 0
    if env_file:
        for name in secret_names:
            value = load_optional_dotenv_value(env_file.resolve(), name)
            if value:
                checked_secret_count += 1
                check(f"secret_absent_{name}", value.encode("utf-8") not in serialized)

    mutations = [
        expect_rejection(
            "unsafe_host", lambda: validate_official_uri("https://example.com/teams/1")
        ),
        expect_rejection(
            "credential_query",
            lambda: validate_official_uri(
                "https://stats.ncaa.org/teams/1?token=secret"
            ),
        ),
        expect_rejection(
            "historical_pit_authority_open",
            lambda: validate_authority(
                {**contract["authority"], "historical_pit_admission": True}
            ),
        ),
        expect_rejection(
            "canonical_mutation_authority_open",
            lambda: validate_authority(
                {**contract["authority"], "canonical_entity_mutation": True}
            ),
        ),
    ]
    checks.extend(mutations)
    report_core = {
        "schema_version": "1.1.0",
        "artifact_type": "NCAA_OFFICIAL_DISCOVERY_VALIDATION_REPORT",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "result": "PASS",
        "season": int(season),
        "discovery_identity": discovery["discovery_identity"],
        "manifest_path": str(discovery_path),
        "manifest_sha256": sha256_file(discovery_path),
        "team_page_capture_count": discovery["team_page_capture_count"],
        "discovered_contest_count": len(discovered_contests),
        "legacy_schedule_record_count": discovery.get(
            "legacy_schedule_record_count", 0
        ),
        "team_failure_count": discovery["team_failure_count"],
        "remaining_queue_count": len(discovery["remaining_queue"]),
        "coverage_disposition": (
            "GRAPH_EXHAUSTED_CAPTURE_COMPLETE"
            if not discovery["failures"]
            else "GRAPH_EXHAUSTED_WITH_QUARANTINED_FAILURES"
        ),
        "check_count": len(checks),
        "mutation_control_count": len(mutations),
        "configured_secret_values_checked_without_logging": checked_secret_count,
        "checks": checks,
    }
    report = {**report_core, "validation_identity": stable_hash(report_core)}
    report_path = (
        data_root
        / "validation"
        / contract["decision_unit"]
        / "discovery"
        / season
        / "sha256"
        / report["validation_identity"]
        / "validation_report.json"
    )
    write_immutable_json(report_path, report)
    return report, report_path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--contract", type=Path, required=True)
    result.add_argument("--discovery-manifest", type=Path, required=True)
    result.add_argument("--rebuild-root", type=Path, required=True)
    result.add_argument("--env-file", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    report, report_path = validate_discovery(
        repo_root=args.repo_root,
        data_root=args.data_root,
        contract_path=args.contract,
        discovery_path=args.discovery_manifest,
        rebuild_root=args.rebuild_root,
        env_file=args.env_file,
    )
    print(
        json.dumps(
            {
                "result": report["result"],
                "season": report["season"],
                "checks": report["check_count"],
                "mutation_controls": report["mutation_control_count"],
                "discovery_identity": report["discovery_identity"],
                "validation_identity": report["validation_identity"],
                "report_path": str(report_path),
                "report_sha256": sha256_file(report_path),
                "rebuild_root": str(args.rebuild_root.resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
