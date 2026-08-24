from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_protected_split_exposure import AUDIT_PATH, validate_audit  # noqa: E402
from tools.repo_integrity import (  # noqa: E402
    INTRINSIC_VCS_METADATA,
    scan_forbidden,
    scan_secrets,
    validate_manifest,
    validate_required_structure,
)
from tools.validate_acceptance import validate as validate_acceptance  # noqa: E402
from tools.validate_architecture import validate_registry  # noqa: E402
from tools.validate_entities import validate as validate_entities  # noqa: E402
from tools.validate_execution_focus import validate as validate_execution_focus  # noqa: E402
from tools.validate_external_storage_policy import validate as validate_external_storage_policy  # noqa: E402
from tools.validate_feature_lifecycle import validate as validate_feature_lifecycle  # noqa: E402
from tools.validate_feature_registry import validate as validate_feature_registry  # noqa: E402
from tools.validate_model_architecture import validate as validate_model_architecture  # noqa: E402
from tools.validate_openai_assist import validate as validate_openai_assist  # noqa: E402
from tools.validate_openrouter_assist import validate as validate_openrouter_assist  # noqa: E402
from tools.validate_team_state import validate as validate_team_state  # noqa: E402
from tools.validate_temporal import validate as validate_temporal  # noqa: E402


def validate_live_verification_histogram_surface(root: Path) -> list[str]:
    """Read-only live-verifier histogram contract; does not call Jira."""
    module_path = root / "jira" / "tools" / "import_bat_live.py"
    spec = importlib.util.spec_from_file_location(
        "aggie_analytics_jira_live_verification_histograms_strict",
        module_path,
    )
    if spec is None or spec.loader is None:
        return ["unable to load jira/tools/import_bat_live.py for histogram validation"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.validate_static_live_verification_histogram_surface(root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the canonical Aggie Analytics Engine repository.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    findings = []
    findings += validate_required_structure(root)
    findings += scan_forbidden(root)
    findings += scan_secrets(root)
    findings += validate_manifest(root)


    architecture_registry = root / "configs/architecture_registry.json"
    if architecture_registry.exists():
        architecture_findings = validate_registry(json.loads(architecture_registry.read_text(encoding="utf-8")))
        for detail in architecture_findings:
            findings.append(type("F", (), {"kind":"architecture", "path":str(architecture_registry.relative_to(root)), "detail":detail})())

    entity_registry = root / "configs/entity_registry.json"
    if entity_registry.exists():
        for detail in validate_entities(root):
            findings.append(type("F", (), {"kind":"entity_contract", "path":str(entity_registry.relative_to(root)), "detail":detail})())

    temporal_registry = root / "configs/temporal_registry.json"
    if temporal_registry.exists():
        for detail in validate_temporal(root):
            findings.append(type("F", (), {"kind":"temporal_contract", "path":str(temporal_registry.relative_to(root)), "detail":detail})())

    feature_registry = root / "configs/raw_feature_registry.json"
    if feature_registry.exists():
        for detail in validate_feature_registry(root):
            findings.append(type("F", (), {"kind":"feature_registry", "path":str(feature_registry.relative_to(root)), "detail":detail})())

    feature_lifecycle_registry = root / "configs/feature_lifecycle_registry.json"
    if feature_lifecycle_registry.exists():
        for detail in validate_feature_lifecycle(root):
            findings.append(type("F", (), {"kind":"feature_lifecycle", "path":str(feature_lifecycle_registry.relative_to(root)), "detail":detail})())

    team_state_registry = root / "configs/team_state_registry.json"
    if team_state_registry.exists():
        for detail in validate_team_state(root):
            findings.append(type("F", (), {"kind":"team_state", "path":str(team_state_registry.relative_to(root)), "detail":detail})())

    acceptance_registry = root / "configs/acceptance_registry.json"
    if acceptance_registry.exists():
        for detail in validate_acceptance(root):
            findings.append(type("F", (), {"kind":"acceptance", "path":str(acceptance_registry.relative_to(root)), "detail":detail})())

    model_architecture_registry = root / "configs/model_architecture_registry.json"
    if model_architecture_registry.exists():
        for detail in validate_model_architecture(root):
            findings.append(type("F", (), {"kind":"model_architecture", "path":str(model_architecture_registry.relative_to(root)), "detail":detail})())

    external_storage_policy = root / "configs/external_storage_policy.json"
    if external_storage_policy.exists():
        for detail in validate_external_storage_policy(root):
            findings.append(type("F", (), {"kind":"external_storage", "path":str(external_storage_policy.relative_to(root)), "detail":detail})())

    openai_assist_policy = root / "configs/openai_assist_policy.json"
    if openai_assist_policy.exists():
        for detail in validate_openai_assist(root):
            findings.append(type("F", (), {"kind":"openai_assist", "path":str(openai_assist_policy.relative_to(root)), "detail":detail})())

    openrouter_assist_policy = root / "configs/openrouter_assist_policy.json"
    if openrouter_assist_policy.exists():
        for detail in validate_openrouter_assist(root):
            findings.append(type("F", (), {"kind":"openrouter_assist", "path":str(openrouter_assist_policy.relative_to(root)), "detail":detail})())

    execution_focus_policy = root / "instructions/policies/execution_focus_policy.json"
    if execution_focus_policy.exists():
        for detail in validate_execution_focus(root):
            findings.append(type("F", (), {"kind":"execution_focus", "path":str(execution_focus_policy.relative_to(root)), "detail":detail})())

    # Lightweight governance integrity checks.
    req_path = root / "governance/REQUIREMENTS_INDEX.csv"
    trace_path = root / "governance/REQUIREMENTS_TRACEABILITY.csv"
    adr_path = root / "governance/ADR_INDEX.csv"
    risk_path = root / "governance/RISK_REGISTER.csv"
    def ids(path: Path, column: str) -> list[str]:
        with path.open(newline="", encoding="utf-8") as fh:
            return [row[column] for row in csv.DictReader(fh)]
    req_ids = ids(req_path, "requirement_id")
    trace_ids = ids(trace_path, "requirement_id")
    adr_ids = ids(adr_path, "adr_id")
    risk_ids = ids(risk_path, "risk_id")
    if len(req_ids) != len(set(req_ids)):
        findings.append(type("F", (), {"kind":"duplicate_req", "path":str(req_path), "detail":"duplicate requirement IDs"})())
    if set(req_ids) != set(trace_ids):
        findings.append(type("F", (), {"kind":"traceability", "path":str(trace_path), "detail":"traceability does not cover exactly all requirements"})())
    if len(adr_ids) != len(set(adr_ids)):
        findings.append(type("F", (), {"kind":"duplicate_adr", "path":str(adr_path), "detail":"duplicate ADR IDs"})())
    if len(risk_ids) != len(set(risk_ids)):
        findings.append(type("F", (), {"kind":"duplicate_risk", "path":str(risk_path), "detail":"duplicate risk IDs"})())
    # Open-issue references are human-facing but must remain unique to avoid ambiguous carry-forward.
    issue_path = root / "governance/OPEN_ISSUES.md"
    if issue_path.exists():
        issue_ids = re.findall(r"ISSUE-(\d+)", issue_path.read_text(encoding="utf-8"))
        duplicates = sorted({x for x in issue_ids if issue_ids.count(x) > 1})
        if duplicates:
            findings.append(type("F", (), {"kind":"duplicate_issue", "path":str(issue_path), "detail":f"duplicate issue IDs {duplicates}"})())

    # Check explicit numeric requirement/ADR references across text files.
    known_req = set(req_ids)
    known_adr = set(adr_ids)
    text_suffixes = {".md", ".txt", ".csv", ".yaml", ".yml", ".json", ".toml", ".py", ".ps1"}
    for path in root.rglob("*"):
        if any(part in INTRINSIC_VCS_METADATA for part in path.relative_to(root).parts):
            continue
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for ref in set(re.findall(r"REQ-\d{3}", text)) - known_req:
            findings.append(type("F", (), {"kind":"dangling_req_ref", "path":str(path.relative_to(root)), "detail":ref})())
        for ref in set(re.findall(r"ADR-\d{3}", text)) - known_adr:
            findings.append(type("F", (), {"kind":"dangling_adr_ref", "path":str(path.relative_to(root)), "detail":ref})())

    if args.strict:
        try:
            for detail in validate_live_verification_histogram_surface(root):
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "jira_live_verification_histograms",
                            "path": "jira/tools/import_bat_live.py",
                            "detail": detail,
                        },
                    )()
                )
            convergence_path = root / "jira" / "tools" / "validate_jira_live_convergence.py"
            convergence_spec = importlib.util.spec_from_file_location(
                "aggie_analytics_jira_live_convergence_strict",
                convergence_path,
            )
            if convergence_spec is None or convergence_spec.loader is None:
                raise FileNotFoundError("unable to load jira/tools/validate_jira_live_convergence.py")
            convergence_module = importlib.util.module_from_spec(convergence_spec)
            convergence_spec.loader.exec_module(convergence_module)
            for detail in convergence_module.validate_committed_jira_live_convergence(root):
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "jira_live_convergence",
                            "path": "jira/tools/validate_jira_live_convergence.py",
                            "detail": detail,
                        },
                    )()
                )
        except (ValueError, FileNotFoundError, OSError, json.JSONDecodeError, AttributeError) as exc:
            findings.append(
                type(
                    "F",
                    (),
                    {
                        "kind": "jira_live_verification_histograms",
                        "path": "jira/tools/import_bat_live.py",
                        "detail": str(exc),
                    },
                )()
            )

        audit_path = root / AUDIT_PATH
        try:
            if not audit_path.is_file():
                raise FileNotFoundError(f"missing committed audit: {AUDIT_PATH}")
            committed = json.loads(audit_path.read_text(encoding="utf-8"))
            validate_audit(committed, root)
        except (ValueError, FileNotFoundError, OSError, json.JSONDecodeError) as exc:
            findings.append(
                type(
                    "F",
                    (),
                    {
                        "kind": "protected_split_audit",
                        "path": str(AUDIT_PATH),
                        "detail": str(exc),
                    },
                )()
            )

        contract_path = root / "configs" / "artifact_binding_contract.json"
        module_path = root / "src" / "aggie_analytics" / "validation" / "artifact_binding.py"
        if contract_path.is_file() or module_path.is_file():
            if not module_path.is_file():
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "artifact_binding",
                            "path": "src/aggie_analytics/validation/artifact_binding.py",
                            "detail": "missing artifact-binding validator module",
                        },
                    )()
                )
            else:

                spec = importlib.util.spec_from_file_location(
                    "aggie_analytics_artifact_binding_strict",
                    module_path,
                )
                if spec is None or spec.loader is None:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "artifact_binding",
                                "path": str(module_path.relative_to(root)),
                                "detail": "unable to load artifact-binding validator module",
                            },
                        )()
                    )
                else:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    try:
                        module.validate_artifact_bindings(root)
                    except module.ArtifactBindingError as exc:
                        findings.append(
                            type(
                                "F",
                                (),
                                {
                                    "kind": "artifact_binding",
                                    "path": exc.path or "configs/artifact_binding_contract.json",
                                    "detail": str(exc),
                                },
                            )()
                        )

        team_season_gate = root / "artifacts" / "data_lake" / "tamu_2010_2011_ncaa_team_season_evidence_gate.json"
        team_season_module = root / "src" / "aggie_analytics" / "data" / "tamu_ncaa_team_season_evidence.py"
        if team_season_gate.is_file() and team_season_module.is_file():

            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_team_season_evidence_strict",
                team_season_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_team_season_evidence",
                            "path": "src/aggie_analytics/data/tamu_ncaa_team_season_evidence.py",
                            "detail": "unable to load team-season evidence validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = (
                    (data_root / "raw/SRC-015/ncaa_team_season_discovery").is_dir()
                    and (data_root / "features/tamu_2010_2011_ncaa_team_season_evidence").is_dir()
                )
                try:
                    # Compact semantic binding always runs. External reconstruction
                    # is required when the data root is mounted and is reported as
                    # not mounted otherwise; it is never silently skipped.
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_team_season_evidence",
                                "path": "artifacts/data_lake/tamu_2010_2011_ncaa_team_season_evidence_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        season_gate = root / "artifacts" / "data_lake" / "tamu_2010_2011_season_reconciliation_gate.json"
        season_module = root / "src" / "aggie_analytics" / "data" / "tamu_season_reconciliation.py"
        if season_gate.is_file() and season_module.is_file():

            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_season_reconciliation_strict",
                season_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_season_reconciliation",
                            "path": "src/aggie_analytics/data/tamu_season_reconciliation.py",
                            "detail": "unable to load season reconciliation validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = (data_root / "features/tamu_2010_2011_season_reconciliation").is_dir()
                try:
                    module.validate_artifact(data_root=data_root, repo_root=root, require_rebuild=lake_ready)
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_season_reconciliation",
                                "path": "artifacts/data_lake/tamu_2010_2011_season_reconciliation_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        contest_gate = root / "artifacts" / "data_lake" / "tamu_2010_2011_ncaa_contest_route_discovery_gate.json"
        contest_module = root / "src" / "aggie_analytics" / "data" / "tamu_ncaa_contest_route_discovery.py"
        if contest_gate.is_file() and contest_module.is_file():

            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_contest_route_discovery_strict",
                contest_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_contest_route_discovery",
                            "path": "src/aggie_analytics/data/tamu_ncaa_contest_route_discovery.py",
                            "detail": "unable to load contest-route discovery validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = (data_root / "features/tamu_2010_2011_ncaa_contest_route_discovery").is_dir()
                try:
                    # Compact identities, counts, and nonclaims are always bound.
                    # External reconstruction runs whenever the data root is mounted.
                    module.validate_artifact(data_root=data_root, repo_root=root, require_rebuild=lake_ready)
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_contest_route_discovery",
                                "path": "artifacts/data_lake/tamu_2010_2011_ncaa_contest_route_discovery_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        archive_gate = root / "artifacts" / "data_lake" / "tamu_official_historical_archive_gate.json"
        archive_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_historical_archive.py"
        if archive_gate.is_file() and archive_module.is_file():

            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_historical_archive_strict",
                archive_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_historical_archive",
                            "path": "src/aggie_analytics/data/tamu_official_historical_archive.py",
                            "detail": "unable to load official historical-archive validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = (data_root / "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/season_index").is_dir()
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_historical_archive",
                                "path": "artifacts/data_lake/tamu_official_historical_archive_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        boxscore_gate = root / "artifacts" / "data_lake" / "tamu_official_historical_boxscore_gate.json"
        boxscore_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_historical_boxscores.py"
        if boxscore_gate.is_file() and boxscore_module.is_file():

            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_historical_boxscores_strict",
                boxscore_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_historical_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_historical_boxscores.py",
                            "detail": "unable to load official historical-boxscore validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = (data_root / "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/box_scores").is_dir()
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_historical_boxscores",
                                "path": "artifacts/data_lake/tamu_official_historical_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        union_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_gate.json"
        union_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union.py"
        if union_gate.is_file() and union_module.is_file():

            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_strict",
                union_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union.py",
                            "detail": "unable to load official gamebook-union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = (
                    data_root
                    / "quarantine/historical_known_at/sha256/76c3b366431d5085588d07df7d8db77348ac737dc57538befe26c7080150f010/tamu_official_gamebooks/domain=game/candidate_records.parquet"
                ).is_file()
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        inventory_gate = root / "artifacts" / "data_lake" / "tamu_official_historical_coverage_inventory_gate.json"
        inventory_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_historical_coverage_inventory.py"
        if inventory_gate.is_file() and inventory_module.is_file():

            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_historical_coverage_inventory_strict",
                inventory_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_historical_coverage_inventory",
                            "path": "src/aggie_analytics/data/tamu_official_historical_coverage_inventory.py",
                            "detail": "unable to load official historical-coverage-inventory validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = (
                    data_root
                    / "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/history_index"
                ).is_dir()
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_historical_coverage_inventory",
                                "path": "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        pre2010_gate = root / "artifacts" / "data_lake" / "tamu_official_pre2010_boxscore_gate.json"
        pre2010_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_pre2010_boxscores.py"
        if pre2010_gate.is_file() and pre2010_module.is_file():

            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_pre2010_boxscores_strict",
                pre2010_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_pre2010_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_pre2010_boxscores.py",
                            "detail": "unable to load official pre-2010 box-score validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = (
                    data_root / "features/tamu_official_pre2010_boxscores/capture_index.json"
                ).is_file()
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_pre2010_boxscores",
                                "path": "artifacts/data_lake/tamu_official_pre2010_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        expanded_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_expanded_gate.json"
        expanded_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_expanded.py"
        if expanded_gate.is_file() and expanded_module.is_file():

            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_expanded_strict",
                expanded_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_expanded",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_expanded.py",
                            "detail": "unable to load expanded official gamebook-union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = (
                    data_root
                    / "features/tamu_official_pre2010_boxscores/sha256"
                    / "1858893908f59afc8f6e88fea46764666869d7c809ddf2b3fedbdfcea02b6b59"
                    / "payload.json"
                ).is_file()
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_expanded",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_expanded_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )


        season_2007_gate = root / "artifacts" / "data_lake" / "tamu_official_2007_season_index_gate.json"
        season_2007_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2007_season_index.py"
        if season_2007_gate.is_file() and season_2007_module.is_file():

            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2007_season_index_strict",
                season_2007_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2007_season_index",
                            "path": "src/aggie_analytics/data/tamu_official_2007_season_index.py",
                            "detail": "unable to load official 2007 season-index validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = module.lake_is_ready(data_root, root)
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2007_season_index",
                                "path": "artifacts/data_lake/tamu_official_2007_season_index_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        season_2006_gate = root / "artifacts" / "data_lake" / "tamu_official_2006_season_index_gate.json"
        season_2006_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2006_season_index.py"
        if season_2006_gate.is_file() and season_2006_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2006_season_index_strict",
                season_2006_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2006_season_index",
                            "path": "src/aggie_analytics/data/tamu_official_2006_season_index.py",
                            "detail": "unable to load official 2006 season-index validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = module.lake_is_ready(data_root, root)
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2006_season_index",
                                "path": "artifacts/data_lake/tamu_official_2006_season_index_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        season_2005_gate = root / "artifacts" / "data_lake" / "tamu_official_2005_season_index_gate.json"
        season_2005_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2005_season_index.py"
        if season_2005_gate.is_file() and season_2005_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2005_season_index_strict",
                season_2005_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2005_season_index",
                            "path": "src/aggie_analytics/data/tamu_official_2005_season_index.py",
                            "detail": "unable to load official 2005 season-index validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = module.lake_is_ready(data_root, root)
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2005_season_index",
                                "path": "artifacts/data_lake/tamu_official_2005_season_index_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        season_2004_gate = root / "artifacts" / "data_lake" / "tamu_official_2004_season_index_gate.json"
        season_2004_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2004_season_index.py"
        if season_2004_gate.is_file() and season_2004_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2004_season_index_strict",
                season_2004_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2004_season_index",
                            "path": "src/aggie_analytics/data/tamu_official_2004_season_index.py",
                            "detail": "unable to load official 2004 season-index validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = module.lake_is_ready(data_root, root)
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2004_season_index",
                                "path": "artifacts/data_lake/tamu_official_2004_season_index_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        season_2003_gate = root / "artifacts" / "data_lake" / "tamu_official_2003_season_index_gate.json"
        season_2003_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2003_season_index.py"
        if season_2003_gate.is_file() and season_2003_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2003_season_index_strict",
                season_2003_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2003_season_index",
                            "path": "src/aggie_analytics/data/tamu_official_2003_season_index.py",
                            "detail": "unable to load official 2003 season-index validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = module.lake_is_ready(data_root, root)
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2003_season_index",
                                "path": "artifacts/data_lake/tamu_official_2003_season_index_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        season_2002_gate = root / "artifacts" / "data_lake" / "tamu_official_2002_season_index_gate.json"
        season_2002_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2002_season_index.py"
        if season_2002_gate.is_file() and season_2002_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2002_season_index_strict",
                season_2002_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2002_season_index",
                            "path": "src/aggie_analytics/data/tamu_official_2002_season_index.py",
                            "detail": "unable to load official 2002 season-index validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = module.lake_is_ready(data_root, root)
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2002_season_index",
                                "path": "artifacts/data_lake/tamu_official_2002_season_index_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        season_2000_gate = root / "artifacts" / "data_lake" / "tamu_official_2000_season_index_gate.json"
        season_2000_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2000_season_index.py"
        if season_2000_gate.is_file() and season_2000_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2000_season_index_strict",
                season_2000_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2000_season_index",
                            "path": "src/aggie_analytics/data/tamu_official_2000_season_index.py",
                            "detail": "unable to load official 2000 season-index validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = module.lake_is_ready(data_root, root)
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2000_season_index",
                                "path": "artifacts/data_lake/tamu_official_2000_season_index_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        season_1999_gate = root / "artifacts" / "data_lake" / "tamu_official_1999_season_index_gate.json"
        season_1999_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_1999_season_index.py"
        if season_1999_gate.is_file() and season_1999_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_1999_season_index_strict",
                season_1999_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_1999_season_index",
                            "path": "src/aggie_analytics/data/tamu_official_1999_season_index.py",
                            "detail": "unable to load official 1999 season-index validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = module.lake_is_ready(data_root, root)
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_1999_season_index",
                                "path": "artifacts/data_lake/tamu_official_1999_season_index_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        season_2001_gate = root / "artifacts" / "data_lake" / "tamu_official_2001_season_index_gate.json"
        season_2001_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2001_season_index.py"
        if season_2001_gate.is_file() and season_2001_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2001_season_index_strict",
                season_2001_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2001_season_index",
                            "path": "src/aggie_analytics/data/tamu_official_2001_season_index.py",
                            "detail": "unable to load official 2001 season-index validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                lake_ready = module.lake_is_ready(data_root, root)
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=lake_ready,
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2001_season_index",
                                "path": "artifacts/data_lake/tamu_official_2001_season_index_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2000_gate = root / "artifacts" / "data_lake" / "tamu_official_2000_boxscore_gate.json"
        box_2000_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2000_boxscores.py"
        if box_2000_gate.is_file() and box_2000_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2000_boxscores_strict",
                box_2000_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2000_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_2000_boxscores.py",
                            "detail": "unable to load official 2000 box-score validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2000_boxscores",
                                "path": "artifacts/data_lake/tamu_official_2000_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2000_structured_gate = root / "artifacts" / "data_lake" / "tamu_official_2000_structured_domains_gate.json"
        box_2000_structured_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2000_structured_domains.py"
        if box_2000_structured_gate.is_file() and box_2000_structured_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2000_structured_domains_strict",
                box_2000_structured_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2000_structured_domains",
                            "path": "src/aggie_analytics/data/tamu_official_2000_structured_domains.py",
                            "detail": "unable to load official 2000 structured-domain validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2000_structured_domains",
                                "path": "artifacts/data_lake/tamu_official_2000_structured_domains_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_1999_gate = root / "artifacts" / "data_lake" / "tamu_official_1999_boxscore_gate.json"
        box_1999_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_1999_boxscores.py"
        if box_1999_gate.is_file() and box_1999_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_1999_boxscores_strict",
                box_1999_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_1999_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_1999_boxscores.py",
                            "detail": "unable to load official 1999 box-score validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_1999_boxscores",
                                "path": "artifacts/data_lake/tamu_official_1999_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        domains_1999_gate = root / "artifacts" / "data_lake" / "tamu_official_1999_structured_domains_gate.json"
        domains_1999_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_1999_structured_domains.py"
        if domains_1999_gate.is_file() and domains_1999_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_1999_structured_domains_strict",
                domains_1999_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_1999_structured_domains",
                            "path": "src/aggie_analytics/data/tamu_official_1999_structured_domains.py",
                            "detail": "unable to load official 1999 structured-domain validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_1999_structured_domains",
                                "path": "artifacts/data_lake/tamu_official_1999_structured_domains_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        union_1999_expanded_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_1999_expanded_gate.json"
        union_1999_expanded_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_1999_expanded.py"
        if union_1999_expanded_gate.is_file() and union_1999_expanded_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_1999_expanded_strict",
                union_1999_expanded_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_1999_expanded",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_1999_expanded.py",
                            "detail": "unable to load 1999-expanded official union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_1999_expanded",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_1999_expanded_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        index_1998_gate = root / "artifacts" / "data_lake" / "tamu_official_1998_season_index_gate.json"
        index_1998_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_1998_season_index.py"
        if index_1998_gate.is_file() and index_1998_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_1998_season_index_strict",
                index_1998_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_1998_season_index",
                            "path": "src/aggie_analytics/data/tamu_official_1998_season_index.py",
                            "detail": "unable to load official 1998 season-index validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root, root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_1998_season_index",
                                "path": "artifacts/data_lake/tamu_official_1998_season_index_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_1998_gate = root / "artifacts" / "data_lake" / "tamu_official_1998_boxscore_gate.json"
        box_1998_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_1998_boxscores.py"
        if box_1998_gate.is_file() and box_1998_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_1998_boxscores_strict",
                box_1998_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type("F", (), {
                        "kind": "tamu_official_1998_boxscores",
                        "path": "src/aggie_analytics/data/tamu_official_1998_boxscores.py",
                        "detail": "unable to load official 1998 box-score validator",
                    })()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type("F", (), {
                            "kind": "tamu_official_1998_boxscores",
                            "path": "artifacts/data_lake/tamu_official_1998_boxscore_gate.json",
                            "detail": str(exc),
                        })()
                    )

        box_2001_gate = root / "artifacts" / "data_lake" / "tamu_official_2001_boxscore_gate.json"
        box_2001_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2001_boxscores.py"
        if box_2001_gate.is_file() and box_2001_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2001_boxscores_strict",
                box_2001_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2001_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_2001_boxscores.py",
                            "detail": "unable to load official 2001 box-score validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2001_boxscores",
                                "path": "artifacts/data_lake/tamu_official_2001_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2001_structured_gate = root / "artifacts" / "data_lake" / "tamu_official_2001_structured_domains_gate.json"
        box_2001_structured_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2001_structured_domains.py"
        if box_2001_structured_gate.is_file() and box_2001_structured_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2001_structured_domains_strict",
                box_2001_structured_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2001_structured_domains",
                            "path": "src/aggie_analytics/data/tamu_official_2001_structured_domains.py",
                            "detail": "unable to load official 2001 structured-domain validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2001_structured_domains",
                                "path": "artifacts/data_lake/tamu_official_2001_structured_domains_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2002_gate = root / "artifacts" / "data_lake" / "tamu_official_2002_boxscore_gate.json"
        box_2002_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2002_boxscores.py"
        if box_2002_gate.is_file() and box_2002_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2002_boxscores_strict",
                box_2002_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2002_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_2002_boxscores.py",
                            "detail": "unable to load official 2002 box-score validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2002_boxscores",
                                "path": "artifacts/data_lake/tamu_official_2002_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2002_structured_gate = root / "artifacts" / "data_lake" / "tamu_official_2002_structured_domains_gate.json"
        box_2002_structured_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2002_structured_domains.py"
        if box_2002_structured_gate.is_file() and box_2002_structured_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2002_structured_domains_strict",
                box_2002_structured_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2002_structured_domains",
                            "path": "src/aggie_analytics/data/tamu_official_2002_structured_domains.py",
                            "detail": "unable to load official 2002 structured-domain validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2002_structured_domains",
                                "path": "artifacts/data_lake/tamu_official_2002_structured_domains_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        rich_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_rich_structure.py"
        if rich_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_rich_structure_strict",
                rich_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_rich_structure",
                            "path": "src/aggie_analytics/data/tamu_official_rich_structure.py",
                            "detail": "unable to load official rich-structure validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                try:
                    module.validate_rich_structure_artifacts(repo_root=root)
                except (module.RichStructureViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_rich_structure",
                                "path": "src/aggie_analytics/data/tamu_official_rich_structure.py",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2004_gate = root / "artifacts" / "data_lake" / "tamu_official_2004_boxscore_gate.json"
        box_2004_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2004_boxscores.py"
        if box_2004_gate.is_file() and box_2004_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2004_boxscores_strict",
                box_2004_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2004_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_2004_boxscores.py",
                            "detail": "unable to load official 2004 box-score validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2004_boxscores",
                                "path": "artifacts/data_lake/tamu_official_2004_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2003_gate = root / "artifacts" / "data_lake" / "tamu_official_2003_boxscore_gate.json"
        box_2003_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2003_boxscores.py"
        if box_2003_gate.is_file() and box_2003_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2003_boxscores_strict",
                box_2003_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2003_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_2003_boxscores.py",
                            "detail": "unable to load official 2003 box-score validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2003_boxscores",
                                "path": "artifacts/data_lake/tamu_official_2003_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2003_structured_gate = root / "artifacts" / "data_lake" / "tamu_official_2003_structured_domains_gate.json"
        box_2003_structured_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2003_structured_domains.py"
        if box_2003_structured_gate.is_file() and box_2003_structured_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2003_structured_domains_strict",
                box_2003_structured_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2003_structured_domains",
                            "path": "src/aggie_analytics/data/tamu_official_2003_structured_domains.py",
                            "detail": "unable to load official 2003 structured-domain validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2003_structured_domains",
                                "path": "artifacts/data_lake/tamu_official_2003_structured_domains_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2004_structured_gate = root / "artifacts" / "data_lake" / "tamu_official_2004_structured_domains_gate.json"
        box_2004_structured_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2004_structured_domains.py"
        if box_2004_structured_gate.is_file() and box_2004_structured_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2004_structured_domains_strict",
                box_2004_structured_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2004_structured_domains",
                            "path": "src/aggie_analytics/data/tamu_official_2004_structured_domains.py",
                            "detail": "unable to load official 2004 structured-domain validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2004_structured_domains",
                                "path": "artifacts/data_lake/tamu_official_2004_structured_domains_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2005_gate = root / "artifacts" / "data_lake" / "tamu_official_2005_boxscore_gate.json"
        box_2005_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2005_boxscores.py"
        if box_2005_gate.is_file() and box_2005_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2005_boxscores_strict",
                box_2005_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2005_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_2005_boxscores.py",
                            "detail": "unable to load official 2005 box-score validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2005_boxscores",
                                "path": "artifacts/data_lake/tamu_official_2005_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2005_structured_gate = root / "artifacts" / "data_lake" / "tamu_official_2005_structured_domains_gate.json"
        box_2005_structured_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2005_structured_domains.py"
        if box_2005_structured_gate.is_file() and box_2005_structured_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2005_structured_domains_strict",
                box_2005_structured_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2005_structured_domains",
                            "path": "src/aggie_analytics/data/tamu_official_2005_structured_domains.py",
                            "detail": "unable to load official 2005 structured-domain validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2005_structured_domains",
                                "path": "artifacts/data_lake/tamu_official_2005_structured_domains_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2006_gate = root / "artifacts" / "data_lake" / "tamu_official_2006_boxscore_gate.json"
        box_2006_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2006_boxscores.py"
        if box_2006_gate.is_file() and box_2006_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2006_boxscores_strict",
                box_2006_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2006_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_2006_boxscores.py",
                            "detail": "unable to load official 2006 box-score validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2006_boxscores",
                                "path": "artifacts/data_lake/tamu_official_2006_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        box_2007_gate = root / "artifacts" / "data_lake" / "tamu_official_2007_boxscore_gate.json"
        box_2007_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2007_boxscores.py"
        if box_2007_gate.is_file() and box_2007_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2007_boxscores_strict",
                box_2007_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2007_boxscores",
                            "path": "src/aggie_analytics/data/tamu_official_2007_boxscores.py",
                            "detail": "unable to load official 2007 box-score validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2007_boxscores",
                                "path": "artifacts/data_lake/tamu_official_2007_boxscore_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        union_2007_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_2007_gate.json"
        union_2007_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_2007.py"
        if union_2007_gate.is_file() and union_2007_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_2007_strict",
                union_2007_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_2007",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_2007.py",
                            "detail": "unable to load official 2007 union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_2007",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_2007_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        domains_2006_gate = root / "artifacts" / "data_lake" / "tamu_official_2006_structured_domains_gate.json"
        domains_2006_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2006_structured_domains.py"
        if domains_2006_gate.is_file() and domains_2006_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2006_structured_domains_strict",
                domains_2006_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2006_structured_domains",
                            "path": "src/aggie_analytics/data/tamu_official_2006_structured_domains.py",
                            "detail": "unable to load official 2006 structured-domain validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2006_structured_domains",
                                "path": "artifacts/data_lake/tamu_official_2006_structured_domains_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        statcrew_gate = root / "artifacts" / "data_lake" / "tamu_official_statcrew_preformatted_gate.json"
        statcrew_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_statcrew_preformatted.py"
        if statcrew_gate.is_file() and statcrew_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_statcrew_preformatted_strict",
                statcrew_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_statcrew_preformatted",
                            "path": "src/aggie_analytics/data/tamu_official_statcrew_preformatted.py",
                            "detail": "unable to load StatCrew preformatted validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_statcrew_preformatted",
                                "path": "artifacts/data_lake/tamu_official_statcrew_preformatted_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        expanded_2006_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_2006_expanded_gate.json"
        expanded_2006_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_2006_expanded.py"
        if expanded_2006_gate.is_file() and expanded_2006_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_2006_expanded_strict",
                expanded_2006_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_2006_expanded",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_2006_expanded.py",
                            "detail": "unable to load 2006-expanded union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_2006_expanded",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_2006_expanded_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        expanded_2005_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_2005_expanded_gate.json"
        expanded_2005_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_2005_expanded.py"
        if expanded_2005_gate.is_file() and expanded_2005_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_2005_expanded_strict",
                expanded_2005_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_2005_expanded",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_2005_expanded.py",
                            "detail": "unable to load 2005-expanded union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_2005_expanded",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_2005_expanded_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        integrity_2005_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_2005_integrity_bound_gate.json"
        integrity_2005_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_2005_integrity_bound.py"
        if integrity_2005_gate.is_file() and integrity_2005_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_2005_integrity_bound_strict",
                integrity_2005_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_2005_integrity_bound",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_2005_integrity_bound.py",
                            "detail": "unable to load 2005 integrity-bound union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.upstream_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_2005_integrity_bound",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_2005_integrity_bound_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        expanded_2004_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_2004_expanded_gate.json"
        expanded_2004_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_2004_expanded.py"
        if expanded_2004_gate.is_file() and expanded_2004_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_2004_expanded_strict",
                expanded_2004_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_2004_expanded",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_2004_expanded.py",
                            "detail": "unable to load 2004-expanded union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.upstream_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_2004_expanded",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_2004_expanded_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        integrity_complete_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_integrity_complete_gate.json"
        integrity_complete_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_integrity_complete.py"
        if integrity_complete_gate.is_file() and integrity_complete_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_integrity_complete_strict",
                integrity_complete_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_integrity_complete",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_integrity_complete.py",
                            "detail": "unable to load integrity-complete union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.upstream_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_integrity_complete",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_integrity_complete_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        expanded_2003_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_2003_expanded_gate.json"
        expanded_2003_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_2003_expanded.py"
        if expanded_2003_gate.is_file() and expanded_2003_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_2003_expanded_strict",
                expanded_2003_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_2003_expanded",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_2003_expanded.py",
                            "detail": "unable to load 2003-expanded union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.upstream_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_2003_expanded",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_2003_expanded_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        row_corpus_gate = root / "artifacts" / "data_lake" / "tamu_official_2002_2009_structured_row_corpus_gate.json"
        row_corpus_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2002_2009_structured_row_corpus.py"
        if row_corpus_gate.is_file() and row_corpus_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2002_2009_structured_row_corpus_strict",
                row_corpus_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2002_2009_structured_row_corpus",
                            "path": "src/aggie_analytics/data/tamu_official_2002_2009_structured_row_corpus.py",
                            "detail": "unable to load 2002-2009 structured row-corpus validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.upstream_is_ready(data_root, root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2002_2009_structured_row_corpus",
                                "path": "artifacts/data_lake/tamu_official_2002_2009_structured_row_corpus_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        integrity_row_corpus_gate = root / "artifacts" / "data_lake" / "tamu_official_2002_2009_structured_row_corpus_integrity_gate.json"
        integrity_row_corpus_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2002_2009_structured_row_corpus_integrity.py"
        if integrity_row_corpus_gate.is_file() and integrity_row_corpus_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2002_2009_structured_row_corpus_integrity_strict",
                integrity_row_corpus_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2002_2009_structured_row_corpus_integrity",
                            "path": "src/aggie_analytics/data/tamu_official_2002_2009_structured_row_corpus_integrity.py",
                            "detail": "unable to load 2002-2009 structured row-corpus integrity validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.upstream_is_ready(data_root, root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2002_2009_structured_row_corpus_integrity",
                                "path": "artifacts/data_lake/tamu_official_2002_2009_structured_row_corpus_integrity_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        corpus_2000_2009_gate = root / "artifacts" / "data_lake" / "tamu_official_2000_2009_structured_row_corpus_gate.json"
        corpus_2000_2009_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_2000_2009_structured_row_corpus.py"
        if corpus_2000_2009_gate.is_file() and corpus_2000_2009_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_2000_2009_structured_row_corpus_strict",
                corpus_2000_2009_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_2000_2009_structured_row_corpus",
                            "path": "src/aggie_analytics/data/tamu_official_2000_2009_structured_row_corpus.py",
                            "detail": "unable to load 2000-2009 structured row-corpus validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.upstream_is_ready(data_root, root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_2000_2009_structured_row_corpus",
                                "path": "artifacts/data_lake/tamu_official_2000_2009_structured_row_corpus_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        expanded_2000_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_2000_expanded_gate.json"
        expanded_2000_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_2000_expanded.py"
        if expanded_2000_gate.is_file() and expanded_2000_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_2000_expanded_strict",
                expanded_2000_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_2000_expanded",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_2000_expanded.py",
                            "detail": "unable to load 2000-expanded union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.upstream_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_2000_expanded",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_2000_expanded_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        expanded_2001_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_2001_expanded_gate.json"
        expanded_2001_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_2001_expanded.py"
        if expanded_2001_gate.is_file() and expanded_2001_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_2001_expanded_strict",
                expanded_2001_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_2001_expanded",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_2001_expanded.py",
                            "detail": "unable to load 2001-expanded union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.upstream_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_2001_expanded",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_2001_expanded_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        expanded_2002_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_2002_expanded_gate.json"
        expanded_2002_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_2002_expanded.py"
        if expanded_2002_gate.is_file() and expanded_2002_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_2002_expanded_strict",
                expanded_2002_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_2002_expanded",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_2002_expanded.py",
                            "detail": "unable to load 2002-expanded union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.upstream_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_2002_expanded",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_2002_expanded_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

        enriched_gate = root / "artifacts" / "data_lake" / "tamu_official_gamebook_union_enriched_gate.json"
        enriched_module = root / "src" / "aggie_analytics" / "data" / "tamu_official_gamebook_union_enriched.py"
        if enriched_gate.is_file() and enriched_module.is_file():
            spec = importlib.util.spec_from_file_location(
                "aggie_analytics_tamu_official_gamebook_union_enriched_strict",
                enriched_module,
            )
            if spec is None or spec.loader is None:
                findings.append(
                    type(
                        "F",
                        (),
                        {
                            "kind": "tamu_official_gamebook_union_enriched",
                            "path": "src/aggie_analytics/data/tamu_official_gamebook_union_enriched.py",
                            "detail": "unable to load enriched-union validator",
                        },
                    )()
                )
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
                try:
                    module.validate_artifact(
                        data_root=data_root,
                        repo_root=root,
                        require_rebuild=module.lake_is_ready(data_root),
                    )
                except (module.AuthorityViolation, FileNotFoundError, OSError, ValueError) as exc:
                    findings.append(
                        type(
                            "F",
                            (),
                            {
                                "kind": "tamu_official_gamebook_union_enriched",
                                "path": "artifacts/data_lake/tamu_official_gamebook_union_enriched_gate.json",
                                "detail": str(exc),
                            },
                        )()
                    )

    if findings:
        print(f"FAIL: {len(findings)} finding(s)")
        for finding in findings:
            print(f"- {finding.kind}: {finding.path}: {finding.detail}")
        return 1
    print("PASS: repository structure, manifests, governance IDs, secret scan and forbidden-artifact scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
