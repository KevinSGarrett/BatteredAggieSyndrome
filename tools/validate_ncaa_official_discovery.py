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
    check("no_unresolved_failures", discovery["failures"] == [])
    check(
        "failure_conservation",
        discovery["team_failure_count"] == len(discovery["failures"]),
    )
    check(
        "capture_conservation",
        discovery["team_page_capture_count"] == len(discovery["captures"]),
    )
    captured_team_ids = [row["team_season_id"] for row in discovery["captures"]]
    discovered_team_ids = discovery["discovered_team_season_ids"]
    check("team_ids_unique", len(discovered_team_ids) == len(set(discovered_team_ids)))
    check("capture_ids_unique", len(captured_team_ids) == len(set(captured_team_ids)))
    check("capture_population", set(captured_team_ids) == set(discovered_team_ids))
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
        "schema_version": "1.0.0",
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
        "team_failure_count": discovery["team_failure_count"],
        "remaining_queue_count": len(discovery["remaining_queue"]),
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
