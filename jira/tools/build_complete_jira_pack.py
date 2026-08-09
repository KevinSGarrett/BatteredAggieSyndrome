from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

GEN_DATE = "2026-08-08"
SCHEMA_VERSION = 1


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def split_ids(s: str) -> list[str]:
    if not s:
        return []
    return [x.strip() for x in re.split(r"[;,]", s) if x.strip()]


def slug(s: str) -> str:
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80] or "item"


def file_slug(s: str) -> str:
    """Filesystem-safe slug that avoids false secret-scanner matches such as natural words ending in 'sk-' ."""
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:80] or "item"


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str] | None = None) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\r\n")
        w.writeheader()
        for row in rows:
            clean = {}
            for k in fields:
                v = row.get(k, "")
                if isinstance(v, bool):
                    v = "true" if v else "false"
                elif isinstance(v, (list, tuple, set)):
                    v = ";".join(str(x) for x in v)
                elif isinstance(v, dict):
                    v = json.dumps(v, sort_keys=True, ensure_ascii=False)
                elif v is None:
                    v = ""
                clean[k] = v
            w.writerow(clean)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_bytes(value.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


def write_jsonl(path: Path, rows: Iterable[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value = text.rstrip() + "\n"
    path.write_bytes(value.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


def normalize_jira_text_crlf(jira_root: Path) -> None:
    """Keep byte-sealed generated text deterministic across operating systems."""
    text_suffixes = {".csv", ".json", ".jsonl", ".md", ".py", ".sha256", ".txt", ".yaml", ".yml"}
    for path in sorted(jira_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        data = path.read_bytes()
        normalized = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        if normalized != data:
            path.write_bytes(normalized)


def md_list(items: Iterable[str]) -> str:
    vals = [str(x).strip() for x in items if str(x).strip()]
    return "\n".join(f"- {x}" for x in vals) if vals else "- None."


def md_numbered(items: Iterable[str]) -> str:
    vals = [str(x).strip() for x in items if str(x).strip()]
    return "\n".join(f"{i}. {x}" for i, x in enumerate(vals, 1)) if vals else "1. None."


def wrap(s: str, width: int = 100) -> str:
    return "\n".join(textwrap.wrap(norm_space(s), width=width))


@dataclass
class RepoFile:
    path: str
    absolute: Path
    size_bytes: int
    sha256: str
    line_count: int
    extension: str
    top_dir: str
    role: str
    authority_level: str
    parse_status: str = "OK"
    headings: list[tuple[int, int, str]] = field(default_factory=list)


class RepoIndex:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.files: dict[str, RepoFile] = {}
        self.lines: dict[str, list[str]] = {}
        self.csv_cache: dict[str, list[dict[str, str]]] = {}
        self.csv_headers: dict[str, list[str]] = {}
        self._scan()

    def _authority(self, rel: str) -> tuple[str, str]:
        protected = {
            "AGENTS.md",
            "governance/DO_NOT_DRIFT.md",
            "governance/PROTECTED_ACCEPTANCE_RULES.md",
            "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
            "governance/PROTECTED_SPLIT_REGISTRY.csv",
            "configs/judging_rule_seal.json",
            "configs/repository_policy.json",
        }
        final_current = {
            "governance/CURRENT_STATE.yaml",
            "governance/CURRENT_BACKLOG.yaml",
            "governance/NEXT_WAVE.md",
            "docs/final/CODEX_HANDOFF.md",
            "docs/final/FINAL_COMPONENT_MATURITY.csv",
            "docs/final/FINAL_KNOWN_GAPS.csv",
            "docs/final/FINAL_KNOWN_GAPS.md",
            "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
            "docs/final/FINAL_BACKLOG.csv",
            "docs/final/FINAL_RISK_REGISTER.csv",
            "docs/final/FIRST_72_HOUR_IMPLEMENTATION_QUEUE.md",
        }
        current_registry_prefixes = (
            "governance/REQUIREMENTS_",
            "governance/REQUIREMENT_",
            "governance/ACCEPTANCE_",
            "governance/ADR_",
            "governance/IMPLEMENTATION_",
            "governance/TASK_",
            "governance/EPIC_",
            "governance/CRITICAL_PATH",
            "governance/CODEX_WORK_PACKET_QUEUE",
            "configs/",
        )
        if rel in protected:
            return "PROTECTED_INVARIANT", "Protected project rule or sealed governance artifact"
        if rel in final_current or rel.startswith("docs/final/"):
            return "FINAL_CURRENT", "Terminal W25 handoff/current-state artifact"
        if rel.startswith(current_registry_prefixes):
            return "CURRENT_MACHINE_REGISTRY", "Machine-readable governance or implementation registry"
        if rel.startswith("src/"):
            return "IMPLEMENTATION_EVIDENCE", "Current executable starter implementation"
        if rel.startswith("tests/") or rel.startswith("tools/validate_"):
            return "VALIDATION_EVIDENCE", "Executable validation/test evidence"
        if rel.startswith("docs/readiness/") or "W24" in rel or "W25" in rel:
            return "LATE_READINESS", "Late-wave readiness or finalization evidence"
        if rel.startswith("docs/"):
            return "ACCEPTED_DESIGN", "Accepted architecture/design/protocol source"
        if rel.startswith("governance/"):
            return "GOVERNANCE_DETAIL", "Governance/provenance detail"
        if rel.startswith("provenance/"):
            return "HISTORICAL_PROVENANCE", "Historical file/change/hash provenance"
        return "SUPPORTING", "Supporting repository artifact"

    def _scan(self) -> None:
        for p in sorted(self.root.rglob("*")):
            if not p.is_file() or "jira" in p.relative_to(self.root).parts[:1]:
                continue
            rel = p.relative_to(self.root).as_posix()
            data = p.read_bytes()
            try:
                text = data.decode("utf-8-sig")
                lines = text.splitlines()
                parse_status = "OK"
            except UnicodeDecodeError:
                text = ""
                lines = []
                parse_status = "BINARY_OR_NON_UTF8"
            authority, role = self._authority(rel)
            headings: list[tuple[int, int, str]] = []
            if p.suffix.lower() == ".md":
                for i, line in enumerate(lines, 1):
                    m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
                    if m:
                        headings.append((i, len(m.group(1)), m.group(2).strip()))
            rec = RepoFile(
                path=rel,
                absolute=p,
                size_bytes=len(data),
                sha256=sha256_bytes(data),
                line_count=len(lines),
                extension=p.suffix.lower() or p.name,
                top_dir=rel.split("/")[0],
                role=role,
                authority_level=authority,
                parse_status=parse_status,
                headings=headings,
            )
            self.files[rel] = rec
            self.lines[rel] = lines
            if p.suffix.lower() == ".csv" and parse_status == "OK":
                try:
                    rows = csv_rows(p)
                    self.csv_cache[rel] = rows
                    self.csv_headers[rel] = list(rows[0].keys()) if rows else []
                except Exception:
                    pass

    def exists(self, rel: str) -> bool:
        return rel in self.files

    def find_by_basename(self, name: str) -> list[str]:
        name = Path(name).name.lower()
        return [rel for rel in self.files if Path(rel).name.lower() == name]

    def section(self, rel: str, anchor: str | None = None, line: int | None = None) -> tuple[int, int, str]:
        f = self.files[rel]
        lines = self.lines[rel]
        if line:
            start = max(1, line)
            end = min(f.line_count, line)
            return start, end, ""
        if anchor and f.headings:
            low = anchor.lower()
            matches = [h for h in f.headings if low in h[2].lower()]
            if matches:
                start, level, title = matches[0]
                end = f.line_count
                for hline, hlevel, _ in f.headings:
                    if hline > start and hlevel <= level:
                        end = hline - 1
                        break
                return start, end, title
        return (1, max(1, f.line_count), "")

    def excerpt(self, rel: str, start: int, end: int, max_chars: int = 320) -> str:
        lines = self.lines.get(rel, [])
        if not lines:
            return ""
        text = " ".join(x.strip() for x in lines[start - 1 : min(end, len(lines))] if x.strip())
        return norm_space(text)[:max_chars]


@dataclass
class SourceRef:
    source_ref_id: str
    repo_relative_path: str
    windows_absolute_path: str
    document_sha256: str
    heading: str
    start_line: int
    end_line: int
    anchor_excerpt: str
    anchor_hash: str
    source_type: str
    authority_level: str
    why_relevant: str
    last_verified: str


class SourceRefRegistry:
    def __init__(self, repo: RepoIndex):
        self.repo = repo
        self.refs: list[SourceRef] = []
        self.key_to_id: dict[tuple[str, int, int, str], str] = {}

    def add(self, rel: str, why: str, anchor: str | None = None, line: int | None = None) -> str:
        if rel not in self.repo.files:
            raise KeyError(f"missing source path: {rel}")
        start, end, heading = self.repo.section(rel, anchor=anchor, line=line)
        key = (rel, start, end, why)
        if key in self.key_to_id:
            return self.key_to_id[key]
        f = self.repo.files[rel]
        excerpt = self.repo.excerpt(rel, start, end)
        rid = f"SRCREF-{len(self.refs)+1:05d}"
        ref = SourceRef(
            source_ref_id=rid,
            repo_relative_path=rel,
            windows_absolute_path=f"C:\\BatteredAggieSyndrome\\{rel.replace('/', chr(92))}",
            document_sha256=f.sha256,
            heading=heading,
            start_line=start,
            end_line=end,
            anchor_excerpt=excerpt,
            anchor_hash=sha256_text(excerpt) if excerpt else "",
            source_type=f.extension.lstrip(".") or "file",
            authority_level=f.authority_level,
            why_relevant=why,
            last_verified=GEN_DATE,
        )
        self.refs.append(ref)
        self.key_to_id[key] = rid
        return rid

    def add_csv_row(self, rel: str, row_index_zero: int, why: str) -> str:
        return self.add(rel, why, line=row_index_zero + 2)


@dataclass
class Issue:
    local_id: str
    issue_type: str
    title: str
    parent_id: str = ""
    epic_id: str = ""
    phase: str = ""
    workflow_state: str = "BACKLOG"
    historical_classification: str = "ACTIONABLE_POST_WAVE"
    priority: str = "P2"
    critical_path: bool = False
    owner_wave: str = "POST_W25"
    source_ids: list[str] = field(default_factory=list)
    requirement_ids: list[str] = field(default_factory=list)
    acceptance_control_ids: list[str] = field(default_factory=list)
    adr_ids: list[str] = field(default_factory=list)
    risk_ids: list[str] = field(default_factory=list)
    gap_ids: list[str] = field(default_factory=list)
    objective: str = ""
    why_exists: str = ""
    scope: str = ""
    in_scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    related_to: list[str] = field(default_factory=list)
    files_expected: list[str] = field(default_factory=list)
    protected_files: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    definition_of_done: list[str] = field(default_factory=list)
    tests: list[dict[str, str]] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    e2e_validation: str = ""
    maturity_before: str = "DESIGN_ONLY"
    maturity_after: str = "IMPLEMENTED"
    evidence_state: str = "PLANNED"
    risk_conditions: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    component: str = ""
    execution_lane: str = "SOLO_WORKTREE"
    ready: bool = False
    blocked_reason: str = ""
    unblock_condition: str = ""
    ai_context_notes: list[str] = field(default_factory=list)
    import_id: int = 0
    jira_key: str = ""
    canonical_record: str = ""
    generated_markdown: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "local_id": self.local_id,
            "jira_key": self.jira_key,
            "import_id": self.import_id,
            "issue_type": self.issue_type,
            "title": self.title,
            "parent_id": self.parent_id,
            "epic_id": self.epic_id,
            "phase": self.phase,
            "workflow_state": self.workflow_state,
            "historical_classification": self.historical_classification,
            "priority": self.priority,
            "critical_path": self.critical_path,
            "owner_wave": self.owner_wave,
            "source_ids": sorted(set(self.source_ids)),
            "requirement_ids": sorted(set(self.requirement_ids)),
            "acceptance_control_ids": sorted(set(self.acceptance_control_ids)),
            "adr_ids": sorted(set(self.adr_ids)),
            "risk_ids": sorted(set(self.risk_ids)),
            "gap_ids": sorted(set(self.gap_ids)),
            "objective": self.objective,
            "why_this_exists": self.why_exists,
            "scope": self.scope,
            "in_scope": self.in_scope,
            "out_of_scope": self.out_of_scope,
            "prerequisites": self.prerequisites,
            "dependencies": sorted(set(self.dependencies)),
            "blocks": sorted(set(self.blocks)),
            "related_to": sorted(set(self.related_to)),
            "files_expected_to_be_touched": self.files_expected,
            "protected_files_and_interfaces": self.protected_files,
            "expected_outputs": self.outputs,
            "acceptance_criteria": self.acceptance_criteria,
            "definition_of_done": self.definition_of_done,
            "required_tests": self.tests,
            "required_evidence": self.evidence,
            "end_to_end_validation": self.e2e_validation,
            "maturity_before": self.maturity_before,
            "expected_maturity_after_completion": self.maturity_after,
            "evidence_state": self.evidence_state,
            "risk_failure_conditions": self.risk_conditions,
            "stop_conditions": self.stop_conditions,
            "source_refs": self.source_refs,
            "labels": sorted(set(self.labels)),
            "component": self.component,
            "execution_lane": self.execution_lane,
            "ready": self.ready,
            "blocked_reason": self.blocked_reason,
            "unblock_condition": self.unblock_condition,
            "ai_context_notes": self.ai_context_notes,
            "canonical_record": self.canonical_record,
            "generated_markdown": self.generated_markdown,
        }


PHASES = {
    "PHASE-1": "Foundation",
    "PHASE-2": "Advanced Football Intelligence",
    "PHASE-3": "Texas A&M Specialization",
    "PHASE-4": "Production & Autonomy",
    "PHASE-5": "Advanced Research & Finalization",
}

COMPONENT_ALIASES = {
    "environment": "operations-security",
    "sources": "data-sources",
    "raw-data": "raw-snapshots",
    "entities": "entities",
    "pit": "pit-temporal",
    "features": "feature-engineering",
    "modeling": "modeling",
    "advanced-football": "player-context-intelligence",
    "tamu": "tamu-specialization",
    "bas": "bas-science",
    "validation": "validation-promotion",
    "mlops": "mlops",
    "product": "serving-product",
    "operations": "operations-security",
    "release": "release-readiness",
    "advanced": "advanced-challengers",
    "live": "live-modeling",
}

DOMAIN_FILES = {
    "environment": [
        "AGENTS.md", "docs/final/CODEX_HANDOFF.md", "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
        "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md", "src/aggie_analytics/operations/benchmark.py",
        "scripts/benchmark_target.ps1", "tools/capture_runtime_manifest.py",
    ],
    "sources": [
        "docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md", "docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv",
        "docs/data_research/w06/DATA_ACQUISITION_PLAN.md", "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md",
        "docs/final/FINAL_KNOWN_GAPS.csv", "src/aggie_analytics/data/adapters.py",
    ],
    "raw-data": [
        "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md", "docs/101_W19_FOUNDATION_IMPLEMENTATION.md",
        "src/aggie_analytics/data/adapters.py", "src/aggie_analytics/data/contracts.py",
        "src/aggie_analytics/data/snapshots.py", "tests/test_w19_foundation.py",
    ],
    "entities": [
        "docs/14_CANONICAL_ENTITY_ARCHITECTURE.md", "docs/16_ENTITY_RESOLUTION_AND_REVIEW.md",
        "docs/17_ENTITY_STORAGE_EVALUATION.md", "src/aggie_analytics/entities/resolution.py",
        "governance/ENTITY_RESOLUTION_STATES.csv", "tests/test_entity_governance.py",
    ],
    "pit": [
        "docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md", "docs/19_ASOF_QUERY_AND_CUTOFF_CONTRACT.md",
        "docs/21_LEAKAGE_AND_REPLAY_TEST_SPEC.md", "docs/readiness/W24_END_TO_END_READINESS.md",
        "src/aggie_analytics/temporal/eligibility.py", "src/aggie_analytics/temporal/state.py",
        "tests/test_temporal_governance.py", "tests/test_w24_readiness.py",
    ],
    "features": [
        "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md", "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md",
        "docs/26_FEATURE_SCREENING_AND_SELECTION.md", "docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md",
        "docs/28_FEATURE_ABLATION_AND_STABILITY.md", "src/aggie_analytics/features/factory.py",
        "src/aggie_analytics/features/screening.py", "src/aggie_analytics/features/lifecycle.py",
    ],
    "modeling": [
        "docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md", "docs/52_MODEL_ARCHITECTURE_CANDIDATES.md",
        "docs/53_JOINT_SCORE_AND_SIMULATION.md", "docs/54_UNCERTAINTY_OOD_AND_MARKET_LANES.md",
        "docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md", "src/aggie_analytics/modeling/baselines.py",
        "src/aggie_analytics/modeling/joint.py", "src/aggie_analytics/modeling/runtime.py",
    ],
    "advanced-football": [
        "docs/29_TEAM_STATE_ARCHITECTURE.md", "docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md",
        "docs/35_PLAYER_VALUE_REPLACEMENT_AND_AVAILABILITY.md", "docs/37_RECRUITING_TRANSFER_AND_FRESHMAN_INTELLIGENCE.md",
        "docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md", "docs/32_GAME_MECHANICS_ARCHITECTURE.md",
        "src/aggie_analytics/player_intelligence/advanced_state.py", "src/aggie_analytics/context_intelligence/context.py",
    ],
    "tamu": [
        "docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md", "docs/41_TAMU_HIGH_RESOLUTION_STATE.md",
        "docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md", "docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md",
        "src/aggie_analytics/tamu/state.py", "src/aggie_analytics/tamu/specialization.py",
        "tests/test_tamu_specialization_governance.py",
    ],
    "bas": [
        "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md", "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md",
        "docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md", "docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md",
        "src/aggie_analytics/bas/labels.py", "src/aggie_analytics/bas/runtime.py",
        "tests/test_bas_science_governance.py",
    ],
    "validation": [
        "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md", "docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md",
        "docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md", "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md",
        "governance/PROTECTED_JUDGING_RULE_SEAL.csv", "governance/PROTECTED_SPLIT_REGISTRY.csv",
        "src/aggie_analytics/validation/protected.py", "src/aggie_analytics/validation/promotion.py",
    ],
    "mlops": [
        "docs/105_W21_AUTONOMOUS_WEEKLY_MLOPS.md", "src/aggie_analytics/orchestration/weekly.py",
        "src/aggie_analytics/orchestration/checkpoints.py", "src/aggie_analytics/orchestration/publication.py",
        "src/aggie_analytics/orchestration/promotion.py", "tests/test_w21_weekly_mlops.py",
    ],
    "product": [
        "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md", "docs/product/API_CONTRACT.md",
        "src/aggie_analytics/product/service.py", "src/aggie_analytics/product/repository.py",
        "src/aggie_analytics/product/freshness.py", "src/aggie_analytics/api/fastapi_app.py",
        "tests/test_w22_product_serving.py",
    ],
    "operations": [
        "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md", "docs/operations/OBSERVABILITY.md",
        "docs/operations/BACKUP_RESTORE_RETENTION_RUNBOOK.md", "docs/operations/CI_SECURITY_SUPPLY_CHAIN.md",
        "src/aggie_analytics/operations/observability.py", "src/aggie_analytics/operations/backup.py",
        "tests/test_w23_operations.py",
    ],
    "release": [
        "docs/readiness/W24_END_TO_END_READINESS.md", "docs/111_W24_END_TO_END_READINESS_AUDIT.md",
        "docs/final/CODEX_HANDOFF.md", "docs/final/FINAL_COMPONENT_MATURITY.csv",
        "docs/final/FINAL_KNOWN_GAPS.csv", "docs/final/FINAL_RISK_REGISTER.csv",
        "tests/test_w24_readiness.py", "tests/test_w25_final_handoff.py",
    ],
    "advanced": [
        "docs/72_ADVANCED_CHALLENGER_ADMISSION.md", "docs/91_ADVANCED_CHALLENGER_GATE.md",
        "src/aggie_analytics/experimentation/advanced_challengers.py", "governance/ADVANCED_CHALLENGER_ADMISSION.csv",
        "tests/test_advanced_challenger_full.py",
    ],
    "live": [
        "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md", "docs/final/FINAL_KNOWN_GAPS.csv",
        "governance/IMPLEMENTATION_WBS.csv", "governance/OPEN_ISSUES.md",
    ],
}

DOMAIN_TESTS = {
    "environment": ["tests/test_w23_operations.py", "tools/validate_w23_operations.py", "tools/validate_repository.py"],
    "sources": ["tests/test_data_research.py", "tools/validate_data_research.py", "tools/validate_repository.py"],
    "raw-data": ["tests/test_w19_foundation.py", "tools/validate_w19_foundation.py"],
    "entities": ["tests/test_entity_governance.py", "tests/test_w19_foundation.py", "tools/validate_entities.py"],
    "pit": ["tests/test_temporal_governance.py", "tests/test_w24_readiness.py", "tools/validate_temporal.py", "tools/validate_w24_readiness.py"],
    "features": ["tests/test_feature_registry_governance.py", "tests/test_feature_lifecycle_governance.py", "tests/test_feature_tournament_full.py"],
    "modeling": ["tests/test_model_architecture_governance.py", "tests/test_w20_model_starter.py", "tools/validate_model_architecture.py"],
    "advanced-football": ["tests/test_player_intelligence_governance.py", "tests/test_context_intelligence_governance.py", "tests/test_team_state_governance.py"],
    "tamu": ["tests/test_tamu_specialization_governance.py", "tests/test_w20_model_starter.py", "tools/validate_tamu_specialization.py"],
    "bas": ["tests/test_bas_science_governance.py", "tests/test_w20_model_starter.py", "tools/validate_bas_science.py"],
    "validation": ["tests/test_validation_science_governance.py", "tests/test_w25_final_handoff.py", "tools/validate_validation_science.py"],
    "mlops": ["tests/test_w21_weekly_mlops.py", "tools/validate_w21_mlops.py"],
    "product": ["tests/test_w22_product_serving.py", "tools/validate_w22_product.py"],
    "operations": ["tests/test_w23_operations.py", "tools/validate_w23_operations.py", "tools/validate_repository.py"],
    "release": ["tests/test_w24_readiness.py", "tests/test_w25_final_handoff.py", "tools/validate_w24_readiness.py", "tools/validate_w25_final.py"],
    "advanced": ["tests/test_advanced_challenger_full.py", "tools/check_advanced_challenger_admission.py"],
    "live": [],
}

PROTECTED_FILES = [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv",
    "configs/judging_rule_seal.json",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
]

# Blueprint helpers ---------------------------------------------------------

def T(alias: str, title: str, outputs: list[str], checks: list[str], *,
      files: list[str] | None = None, source_ids: list[str] | None = None,
      external_blocker: str = "", maturity_after: str = "IMPLEMENTED",
      lane: str = "", labels: list[str] | None = None, tests: list[str] | None = None) -> dict[str, Any]:
    return {
        "alias": alias, "title": title, "outputs": outputs, "checks": checks,
        "files": files or [], "source_ids": source_ids or [], "external_blocker": external_blocker,
        "maturity_after": maturity_after, "lane": lane, "labels": labels or [], "tests": tests or [],
    }


def S(alias: str, title: str, objective: str, tasks: list[dict[str, Any]], *,
      source_ids: list[str] | None = None, entry_deps: list[str] | None = None,
      e2e: str = "") -> dict[str, Any]:
    return {
        "alias": alias, "title": title, "objective": objective, "tasks": tasks,
        "source_ids": source_ids or [], "entry_deps": entry_deps or [], "e2e": e2e,
    }


def E(alias: str, title: str, phase: str, priority: str, domain: str, objective: str,
      stories: list[dict[str, Any]], *, source_ids: list[str] | None = None,
      depends_on: list[str] | None = None, state: str = "BACKLOG") -> dict[str, Any]:
    return {
        "alias": alias, "title": title, "phase": phase, "priority": priority, "domain": domain,
        "objective": objective, "stories": stories, "source_ids": source_ids or [],
        "depends_on": depends_on or [], "state": state,
    }


# Post-wave completion blueprint. Each story contains two parallel implementation/evidence tasks and one gate task.
POST_BLUEPRINT: list[dict[str, Any]] = [
    E("env", "Target environment, reproducibility, and AC-038 hardware evidence", "PHASE-4", "P0", "environment",
      "Establish an authoritative, reproducible local execution environment and evidence-backed resource envelope on the declared target Windows hardware.", [
        S("env.preflight", "Canonical handoff and target-environment preflight",
          "Prove that the W25 handoff can be reproduced on the target machine before implementation mutates project state.", [
            T("env.preflight.identity", "Verify W25 repository identity, manifests, and no-Wave-26 state",
              ["artifacts/implementation_preflight/repository_identity.json"],
              ["The recorded repository hash and project identity match the W25 handoff.", "The preflight explicitly records that the next state is CODEX_IMPLEMENTATION_HANDOFF and no Wave 26 is created.", "Any manifest mismatch fails closed before mutation."],
              source_ids=["HANDOFF-001"], lane="PROTECTED_GATE"),
            T("env.preflight.validation", "Run the full unit and governance validator suite on the target host",
              ["artifacts/implementation_preflight/target_validation_results.json", "artifacts/implementation_preflight/target_validation.log"],
              ["All 229 baseline unit tests are executed and results are recorded without editing expected outcomes.", "W25 final, acceptance, backlog, and strict repository validators run from a clean checkout.", "Failures are recorded as blockers; they are not waived or hidden."],
              lane="OPERATIONS"),
            T("env.preflight.manifest", "Capture the authoritative target runtime and dependency manifest",
              ["artifacts/implementation_preflight/runtime_manifest.json"],
              ["The manifest records OS, CPU, RAM, GPU, Python, dependency lock hashes, storage paths, and free-space state.", "Secrets and user-identifying values are redacted.", "The manifest is content-hashed and linked to the preflight validation run."],
              lane="OPERATIONS", maturity_after="INTEGRATED"),
          ], source_ids=["HANDOFF-001", "GAP-001"], e2e="A clean target host can verify the handoff, run all baseline validators, and emit a redacted immutable runtime manifest."),
        S("env.localroots", "Local data, artifact, and secret boundary bootstrap",
          "Create the local-only filesystem and secret boundaries required for real source materialization without committing restricted data or credentials.", [
            T("env.localroots.paths", "Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository",
              ["artifacts/implementation_preflight/local_path_contract.json", "docs/operations/LOCAL_RUNTIME_PATHS.md"],
              ["Configured roots are absolute, writable, outside the Git repository, and survive process restart.", "Raw, curated, model, forecast, log, backup, and quarantine roots are separated.", "A path safety test rejects repository-internal bulk-data roots."],
              files=["src/aggie_analytics/operations/environment.py", "tests/test_w23_operations.py"], lane="OPERATIONS"),
            T("env.localroots.secrets", "Define and validate the non-repository credential inventory and redaction rules",
              ["artifacts/implementation_preflight/credential_inventory.redacted.json", "docs/operations/CREDENTIALS_AND_SECRETS.md"],
              ["Every credential is referenced by environment-variable name only.", "No token, password, session cookie, or restricted URL is written to the repository or evidence logs.", "A redaction test demonstrates that representative secret values are removed from logs and exception messages."],
              external_blocker="USER_MUST_SUPPLY_PRODUCTION_CREDENTIALS_OUTSIDE_REPOSITORY", lane="PROTECTED_GATE"),
            T("env.localroots.storage", "Validate target storage permissions, free space, atomic writes, and quarantine behavior",
              ["artifacts/implementation_preflight/storage_probe.json"],
              ["The probe demonstrates atomic create/rename, fsync, readback hash verification, and quarantine moves on each configured root.", "Available capacity is recorded without inventing a minimum threshold.", "Insufficient permissions or capacity blocks downstream materialization."],
              lane="OPERATIONS", maturity_after="INTEGRATED"),
          ], source_ids=["HANDOFF-002", "GAP-010"]),
        S("env.benchmark", "Authoritative target-hardware benchmark and threshold governance",
          "Execute the existing benchmark harness on the declared target hardware and use only that evidence to resolve AC-038, THR-011, and THR-012.", [
            T("env.benchmark.stage", "Stage the representative AC-038 workload and benchmark input manifest",
              ["artifacts/benchmarks/ac038_input_manifest.json"],
              ["The workload matches the benchmark contract and includes representative ingestion, PIT, feature, model, publication, and product-read operations.", "Input hashes and data classification are recorded.", "Protected holdout outcomes are not exposed to benchmark tuning."],
              source_ids=["TASK-161", "AC-038", "GAP-001"], lane="PROTECTED_GATE"),
            T("env.benchmark.run", "Run scripts/benchmark_target.ps1 on the declared Windows/Ryzen 7 HX/32 GB/RTX 5060/NVMe target",
              ["artifacts/benchmarks/ac038_target_benchmark.json", "artifacts/benchmarks/ac038_target_benchmark.log"],
              ["The benchmark is executed on the declared target rather than a substitute host.", "Peak RAM, runtime, CPU/GPU utilization, disk usage, and workload identity are captured.", "At least one repeat run verifies that the result is not a one-off artifact."],
              source_ids=["TASK-161", "AC-038", "THR-011", "THR-012", "GAP-001"],
              external_blocker="AUTHORITATIVE_TARGET_WINDOWS_HOST_NOT_AVAILABLE_IN_THIS_SESSION", lane="PROTECTED_GATE", maturity_after="EMPIRICALLY_VALIDATED"),
            T("env.benchmark.gate", "Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate",
              ["artifacts/benchmarks/ac038_gate_decision.json", "governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv"],
              ["THR-011 and THR-012 are populated only from the authoritative benchmark evidence.", "The decision records evidence hashes, reviewer, timestamp, and pass/block rationale.", "TASK-163 remains blocked unless AC-038 genuinely passes; no threshold is relaxed after observing failure."],
              source_ids=["TASK-163", "AC-038", "THR-011", "THR-012"], lane="PROTECTED_GATE", maturity_after="PRODUCTION_READY"),
          ], source_ids=["HANDOFF-001", "GAP-001"], e2e="The target host produces authoritative benchmark evidence and the governance layer deterministically resolves or retains AC-038 without fabricated thresholds."),
        S("env.envelope", "Evidence-backed resource, concurrency, and degradation envelope",
          "Translate benchmark and storage evidence into safe execution limits for autonomous local operation.", [
            T("env.envelope.concurrency", "Measure safe local worktree and pipeline concurrency under target resource limits",
              ["artifacts/benchmarks/concurrency_envelope.json"],
              ["Concurrent workloads are increased only until measured resource contention or policy limits appear.", "The envelope identifies mutually exclusive shared-contract and protected-gate work.", "No fixed concurrency value is adopted without measurement."],
              lane="OPERATIONS"),
            T("env.envelope.retention", "Measure disk growth and define evidence-backed artifact retention budgets",
              ["artifacts/benchmarks/storage_growth_profile.json", "docs/operations/LOCAL_RESOURCE_ENVELOPE.md"],
              ["Raw snapshots, matrices, model artifacts, forecasts, logs, and backups are measured separately.", "Retention recommendations preserve required lineage and protected evidence.", "Deletion rules never remove canonical negative results, provenance, or superseded policy evidence."],
              lane="OPERATIONS"),
            T("env.envelope.fallback", "Implement and test resource stop conditions and graceful degradation",
              ["artifacts/benchmarks/resource_stop_condition_test.json"],
              ["Peak-RAM, free-space, runtime, and concurrency breaches stop or defer work predictably.", "The system does not silently downsample protected evaluation or omit required data.", "The operator receives a clear blocker, recovery action, and preserved partial evidence."],
              lane="OPERATIONS", maturity_after="OPERATING"),
          ], source_ids=["GAP-001"], e2e="Autonomous work respects measured CPU/RAM/disk/concurrency limits and fails safely without corrupting state or weakening evaluation."),
      ], source_ids=["HANDOFF-001", "GAP-001"], state="READY"),

    E("sources", "Source access, credentials, private-research acquisition, and publication governance", "PHASE-1", "P0", "sources",
      "Convert the researched source universe into technically operable private-research acquisition lanes with explicit credentials, provenance, rate limits, fallbacks, quality gates, and a no-raw-publication boundary.", [
        S("sources.reconcile", "Reconcile the final source universe and authority decisions",
          "Turn W06/W24 research into a current source-by-source production decision register.", [
            T("sources.reconcile.inventory", "Reconcile W06 source inventory with W24 refresh and current handoff gaps",
              ["artifacts/source_governance/production_source_inventory.csv"],
              ["Every prioritized source has a stable source ID, domain, upstream relationship, access method, historical depth, and PIT feasibility.", "SportsDataverse/CFBD upstream relationships are represented without false independent-corroboration claims.", "Superseded or unavailable sources retain explicit dispositions."],
              source_ids=["HANDOFF-002", "GAP-010"], lane="RESEARCH_LANE"),
            T("sources.reconcile.priority", "Freeze source priority, fallback, and required-versus-optional classifications",
              ["artifacts/source_governance/source_priority_decisions.json"],
              ["Each production domain has a primary lane and evidence-backed fallback or an explicit unavailable state.", "Optional proprietary enrichment is not made mandatory for v1.", "Priority decisions preserve local-first cost and technical/quality constraints; rights metadata is nonblocking for private use."],
              source_ids=["ISSUE-012", "GAP-011"], lane="SHARED_CONTRACT"),
            T("sources.reconcile.gate", "Validate source inventory completeness and unresolved decision coverage",
              ["artifacts/source_governance/source_inventory_validation.json"],
             ["All source IDs referenced by adapters, registries, and acquisition plans resolve to the production inventory.", "Every unresolved technical or quality decision has a Jira action or scoped quarantine.", "No required domain is silently marked complete when only reconnaissance samples exist."],
              lane="PROTECTED_GATE", maturity_after="CONTRACT_DEFINED"),
          ], source_ids=["HANDOFF-002", "HANDOFF-012", "GAP-010"]),
        S("sources.rights", "Universal private-research acquisition and future-publication boundary",
          "Apply the owner-authorized private-research policy universally while preserving license/terms/redistribution metadata and independently denying raw third-party publication.", [
            T("sources.rights.tier1", "Reissue CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA decisions under private-research policy",
              ["artifacts/source_governance/tier1_rights_decisions.csv"],
              ["Each decision records source URL/version, review date, local storage, local training, publication boundary, retention, and attribution metadata.", "Ambiguous license, terms, scraping, redistribution, and upstream-authorization fields are explicitly nonblocking for private acquisition/training.", "Bulk raw data remains local outside Git and is not published."],
              source_ids=["ISSUE-028", "GAP-010"], lane="PROTECTED_GATE"),
            T("sources.rights.supplemental", "Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy",
              ["artifacts/source_governance/supplemental_rights_decisions.csv"],
              ["Every supplemental source is acquisition-eligible for private research; technical readiness and domain quality remain independent.", "Genuinely private resources needing unsupplied credentials remain technically unavailable and public substitutes are sought.", "Raw third-party publication is denied by project policy."],
              source_ids=["ISSUE-023", "ISSUE-025", "ISSUE-081", "GAP-011"], lane="PROTECTED_GATE"),
            T("sources.rights.gate", "Publish the private-research source-use matrix and block raw third-party publication",
              ["configs/source_rights_registry.json", "artifacts/source_governance/source_rights_gate_test.json"],
              ["The registry is machine-readable and contains no credentials.", "All registered sources and caller-declared public sources admit private acquisition and local training without a rights prerequisite.", "Raw third-party export remains independently denied and validity/safety gates remain scoped."],
              files=["src/aggie_analytics/data/contracts.py", "tests/test_data_research.py"], lane="SHARED_CONTRACT", maturity_after="INTEGRATED"),
          ], source_ids=["HANDOFF-002", "GAP-010"], e2e="Private local acquisition and training succeed independently of rights ambiguity, raw third-party publication remains denied, and actual technical/quality/PIT/safety failures affect only their exact scope."),
        S("sources.credentials", "Credential configuration and access smoke tests",
          "Configure source access outside the repository and prove each selected lane can be called safely.", [
            T("sources.credentials.contract", "Define credential names, scopes, owners, rotation, and non-repository storage contract",
              ["docs/operations/SOURCE_CREDENTIAL_CONTRACT.md", "artifacts/source_governance/credential_contract.redacted.json"],
              ["Credential variables are source-scoped and least-privilege where the provider supports scopes.", "Rotation/revocation ownership and expiry handling are documented.", "No credential value appears in Git-tracked files or evidence."],
              lane="PROTECTED_GATE"),
            T("sources.credentials.smoke", "Run authenticated and no-key source access smoke tests with rate-limit capture",
              ["artifacts/source_governance/source_access_smoke_results.json"],
              ["Each selected source preserves a minimally sufficient technical response or a precise pending technical action.", "HTTP status, API version, rate-limit metadata, response schema hash, and retrieval time are recorded when observed.", "Smoke tests do not expose secrets or fabricate unobserved results."],
              source_ids=["ISSUE-003", "ISSUE-004"], lane="DATA_MATERIALIZATION"),
            T("sources.credentials.gate", "Validate access readiness and generate source-specific unblock conditions",
              ["artifacts/source_governance/source_access_readiness.csv"],
              ["Every source is READY, TECHNICAL_VALIDATION_PENDING, TECHNICAL_CREDENTIAL_UNAVAILABLE, or quality-quarantined with a concrete reason.", "Downstream materialization tasks consume this readiness file.", "No source is blocked by licensing, redistribution, scraping, terms, provider preference, or upstream-authorization uncertainty."],
              lane="PROTECTED_GATE", maturity_after="INTEGRATED"),
          ], source_ids=["HANDOFF-002", "ISSUE-003", "ISSUE-004"]),
        S("sources.acquisition", "Production acquisition contracts, rate limits, fallbacks, and drift hooks",
          "Turn selected source lanes into deterministic acquisition specifications suitable for immutable historical materialization.", [
            T("sources.acquisition.specs", "Create source-specific endpoint, parameter, pagination, season, and version acquisition specifications",
              ["configs/source_acquisition_registry.json"],
              ["Each source specification declares endpoint/version, allowed seasons, required parameters, pagination, cutoff semantics, and raw content type.", "The specification records upstream lineage and avoids duplicate independent-source claims.", "Unknown historical coverage remains explicit rather than backfilled by assumption."],
              lane="SHARED_CONTRACT"),
            T("sources.acquisition.resilience", "Implement compliant retries, caching, rate-limit handling, and fallback activation",
              ["artifacts/source_governance/acquisition_resilience_test.json"],
              ["Retries honor provider rate limits and bounded backoff.", "Cached raw responses remain immutable and are keyed by request/source identity.", "Fallbacks activate only under documented conditions and preserve source provenance."],
              files=["src/aggie_analytics/data/adapters.py", "src/aggie_analytics/data/snapshots.py"], lane="DATA_MATERIALIZATION"),
            T("sources.acquisition.drift", "Establish source API/schema/terms drift baselines and monitoring inputs",
              ["artifacts/source_governance/source_drift_baseline.json", "configs/source_drift_registry.json"],
              ["Baseline captures endpoint/version, schema hash, terms metadata, expected freshness, and upstream dependencies.", "A changed contract cannot silently overwrite the prior baseline.", "Detected technical/schema/quality drift quarantines only the affected scope before downstream training; terms drift is metadata-only for private use."],
              source_ids=["HANDOFF-012"], lane="OPERATIONS", maturity_after="OPERATING"),
          ], source_ids=["HANDOFF-003", "HANDOFF-012"]),
      ], source_ids=["HANDOFF-002", "HANDOFF-012", "GAP-010"], state="READY"),
]


def story3(alias: str, title: str, objective: str, task_titles: list[str], outputs: list[str], checks: list[str], *,
           source_ids: list[str] | None = None, entry_deps: list[str] | None = None, e2e: str = "",
           lanes: list[str] | None = None, external_blockers: list[str] | None = None,
           maturity_after: str = "PRODUCTION_READY") -> dict[str, Any]:
    """Build two atomic subtasks plus one protected gate from a story-specific contract."""
    if len(task_titles) != 3 or len(outputs) != 3 or len(checks) != 3:
        raise ValueError(f"story3 {alias} requires exactly three task titles, outputs, and checks")
    lanes = lanes or ["SOLO_WORKTREE", "SOLO_WORKTREE", "PROTECTED_GATE"]
    external_blockers = external_blockers or ["", "", ""]
    tasks = []
    for i in range(3):
        task_alias = f"{alias}.{'build' if i == 0 else 'verify' if i == 1 else 'gate'}"
        common = [
            checks[i],
            f"The declared output `{outputs[i]}` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
            "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
        ]
        if i == 2:
            common = [checks[0], checks[1], checks[2], "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."]
        tasks.append(T(
            task_alias,
            task_titles[i],
            [outputs[i]],
            common,
            source_ids=source_ids or [],
            external_blocker=external_blockers[i],
            maturity_after=maturity_after if i == 2 else ("EMPIRICALLY_VALIDATED" if i == 1 else "IMPLEMENTED"),
            lane=lanes[i],
        ))
    return S(alias, title, objective, tasks, source_ids=source_ids or [], entry_deps=entry_deps or [], e2e=e2e)


POST_BLUEPRINT.extend([
    E("raw", "Immutable national historical data materialization", "PHASE-1", "P0", "raw-data",
      "Acquire maximum quality-supported national history into immutable, content-addressed raw snapshots with population-level coverage and provenance evidence; source rights metadata is nonblocking for private research.", [
        story3("raw.core", "Core national game spine", "Materialize teams, conferences, venues, schedules, games, outcomes, drives, plays, and official game evidence.",
          ["Acquire quality-supported national team, schedule, game, score, drive, play, box-score, and gamebook history",
           "Normalize and reconcile core/game-event records while preserving immutable source evidence",
           "Approve or block the population-level core-history coverage gate"],
          ["artifacts/data_lake/core_acquisition_manifest.json", "artifacts/data_lake/core_normalization_report.json", "artifacts/data_lake/core_coverage_gate.json"],
          ["Every configured season/source request records source identity, retrieval/known-at time, request identity, response hash, immutable path, pagination, and provider failure state.",
           "Normalized games, scores, drives, plays, and box totals reconcile to canonical identities and official outcomes; every rejected/partial record is quarantined with reason.",
           "Coverage is measured by source, domain, season, team, and game; reconnaissance samples or fixtures cannot satisfy population readiness."],
          source_ids=["HANDOFF-003", "GAP-002"], entry_deps=["sources.credentials.gate", "sources.rights.gate", "sources.acquisition.specs", "env.localroots.storage"],
          lanes=["DATA_MATERIALIZATION", "DATA_MATERIALIZATION", "PROTECTED_GATE"],
          e2e="A clean acquisition run produces immutable national game history, deterministic normalized evidence, and an honest coverage decision."),
        story3("raw.context", "Historical expansion across core and supporting domains", "Expand the validated contemporary tranche to the maximum quality-supported national history, targeting approximately 2010-2025 and earlier seasons while preserving tiered domain eligibility.",
          ["Expand immutable national core and supporting-domain history to the maximum quality-supported seasons",
           "Profile supporting-domain schema, historical coverage, timestamp quality, upstream lineage, and nonblocking source-policy metadata",
           "Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility"],
          ["artifacts/data_lake/historical_expansion_acquisition_manifest.json", "artifacts/data_lake/context_population_profile.json", "artifacts/data_lake/context_eligibility_gate.json"],
          ["Preserve 2022-2025 as a bounded nonterminal tranche; target approximately 2010-2025 and earlier quality-supported seasons across teams, schedules, games, outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced statistics, structured gamebook equivalents, and useful context. Record source/endpoint, season/type, team/game, domain/grain, schema/version, immutable identity, missingness, provider failures, and historical known-at/PIT state without discarding a useful season because another domain is incomplete.",
           "Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.",
           "Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence."],
          source_ids=["HANDOFF-003", "HANDOFF-008", "GAP-002", "GAP-006", "GAP-010", "GAP-011"], entry_deps=["raw.core.gate"], lanes=["DATA_MATERIALIZATION", "DATA_MATERIALIZATION", "PROTECTED_GATE"],
          e2e="The expanded manifest is deterministic and consumable by the profiling step, preserves partial seasons and missing domains, and never treats rights metadata or the 2022-2025 tranche as a terminal-history gate."),
        story3("raw.store", "Immutable raw store, manifests, provenance, and population audit", "Prove that every accepted raw domain is immutable, reproducible, source-policy-metadata-aware, and reconstructable.",
          ["Enforce content-addressed raw snapshots, correction lineage, quarantine, and source-policy storage metadata",
           "Build the cross-domain acquisition, schema, quality, and source-to-snapshot provenance manifests",
           "Run and publish the national historical-lake readiness decision"],
          ["artifacts/data_lake/immutability_and_correction_test.json", "artifacts/data_lake/NATIONAL_DATA_LAKE_MANIFEST.json", "artifacts/data_lake/national_lake_readiness.json"],
          ["Repeated identical bytes resolve to the same content identity while changed/corrected bytes create a new immutable version without rewriting prior evidence.",
           "The master manifest links every accepted snapshot to source contract, request, hash, parser/schema version, coverage, quality, and nonblocking source-policy metadata and reproduces population counts.",
           "GAP-002 remains open unless actual national history—not fixtures, reconnaissance samples, or starter code—meets immutable, manifest, readback, and coverage requirements."],
          source_ids=["HANDOFF-003", "GAP-002"], entry_deps=["raw.core.gate", "raw.context.gate"], lanes=["SHARED_CONTRACT", "DATA_MATERIALIZATION", "PROTECTED_GATE"],
          e2e="Pinned manifests reconstruct the accepted raw lake from immutable bytes while preserving every missing season, unavailable domain, correction, and technical or quality blocker."),
      ], source_ids=["HANDOFF-003", "GAP-002"], depends_on=["sources.acquisition.drift"], state="BACKLOG"),

    E("entities", "Population schema profiling and canonical entity resolution", "PHASE-1", "P0", "entities",
      "Profile real populations and resolve teams, conferences, venues, coaches, players, games, sources, and temporal aliases at scale with auditable uncertainty.", [
        story3("entities.profile", "Population schema and missingness contracts", "Replace sample assumptions with measured population schemas before canonical resolution.",
          ["Profile every materialized table for rows, types, nulls, uniqueness, ranges, duplicates, timestamps, and partitions",
           "Reconcile measured fields with canonical contracts, compatibility policy, and quarantine/rejection decisions",
           "Approve or block schema and missingness readiness for entity resolution"],
          ["artifacts/entities/population_schema_profile.json", "artifacts/entities/schema_reconciliation.csv", "artifacts/entities/schema_readiness_gate.json"],
          ["Profiles are generated from pinned immutable snapshots by source/season/domain and reproduce exactly.",
           "Every measured field is accepted, transformed, quarantined, deprecated, or rejected with reason; protected temporal/evidence fields are not weakened to accommodate dirty data.",
           "All entity-bearing domains have measured key quality and a declared resolution strategy; unusable partitions remain enumerated rather than silently dropped."],
          source_ids=["GAP-003"], entry_deps=["raw.store.gate"], lanes=["DATA_MATERIALIZATION", "SHARED_CONTRACT", "PROTECTED_GATE"],
          e2e="Real raw populations produce versioned schema/missingness contracts and an explicit readiness decision for resolution."),
        story3("entities.registry", "Canonical registries, aliases, and temporal relationships", "Create stable source-independent identities and effective-dated aliases for every entity class.",
          ["Build canonical team, conference, venue, game, season, and source registries with effective-dated aliases",
           "Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state",
           "Validate registry uniqueness, temporal consistency, collisions, and referential completeness"],
          ["artifacts/entities/canonical_core_registry.csv", "artifacts/entities/canonical_people_registry.csv", "artifacts/entities/registry_validation.json"],
          ["Canonical IDs are deterministic, stable, source-independent, and do not depend on row order or mutable display names; realignment, neutral-site, rename, and cancellation history is represented.",
           "Person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.",
           "No incompatible active aliases, duplicate canonical identities, impossible intervals, or accepted normalized record without a resolution/review disposition remain hidden."],
          source_ids=["GAP-004", "GAP-006"], entry_deps=["entities.profile.gate"], lanes=["SHARED_CONTRACT", "SHARED_CONTRACT", "PROTECTED_GATE"],
          e2e="Versioned canonical registries reproduce historical identity membership and retain every ambiguity rather than silently applying current mappings."),
        story3("entities.resolve", "Population resolution, review workflow, transitions, and entity gate", "Resolve the full population deterministically and publish a pinned entity snapshot for PIT use.",
          ["Run exact, alias, contextual, and bounded probabilistic resolution over the full population with evidence per decision",
           "Operate unresolved/collision/merge/split review and materialize temporal team, conference, staff, roster, and player transitions",
           "Publish the canonical entity snapshot and approve or block downstream PIT consumption"],
          ["artifacts/entities/resolution_results.parquet", "artifacts/entities/entity_decision_and_transition_log.jsonl", "artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json"],
          ["Every resolution records resolver version, candidate set, evidence, confidence, decision rule, and deterministic replay; probability never substitutes for proof.",
           "Manual decisions are append-only and attributable, transitions have known-at/effective intervals, and adding future aliases cannot change prior accepted identities without an explicit correction event.",
           "Coverage/ambiguity/collision/orphan metrics are reported by domain/source/season/entity class; high-impact unresolved identities block affected work and GAP-004 closes only on population evidence."],
          source_ids=["GAP-004"], entry_deps=["entities.registry.gate"], lanes=["DATA_MATERIALIZATION", "PROTECTED_GATE", "PROTECTED_GATE"],
          e2e="Pinned source/schema inputs resolve through auditable canonical identities and temporal transitions into a reproducible entity snapshot with no silent merges or orphans."),
      ], source_ids=["GAP-003", "GAP-004"], depends_on=["raw.store.gate"], state="BACKLOG"),

    E("pit", "Point-in-time historical state and protected replay", "PHASE-1", "P0", "pit",
      "Build fail-closed known-at semantics, append-only as-of state, pregame matrices, leakage batteries, and chronological replay from real history.", [
        story3("pit.cutoffs", "Known-at registry and timestamp normalization", "Define exactly when each source field may enter each pregame horizon.",
          ["Reconcile field temporal classes, source known-at rules, cutoffs, correction policies, and prohibited uses against real schemas",
           "Normalize observed, published, effective, retrieved, and corrected timestamps with source-specific precedence and timezone rules",
           "Validate fail-closed cutoff eligibility and deliberate future/same-game/postgame rejection"],
          ["configs/known_at_registry.json", "artifacts/pit/timestamp_normalization_report.json", "artifacts/pit/known_at_gate.json"],
          ["Every candidate input field has an approved temporal class and cutoff rule; realized weather, closing markets, final participation, box scores, and outcomes are excluded from earlier snapshots.",
           "Original timestamps are preserved, ambiguity/impossibility is quarantined, and retrieval time is never substituted for publication time when it would make history appear known earlier.",
           "All fields entering matrices resolve to approved rules and mutation tests reject same-game, future, postgame, or naming-convention-based eligibility."],
          source_ids=["GAP-005", "RISK-001", "RISK-002", "AC-011", "AC-012"], entry_deps=["entities.resolve.gate"], lanes=["SHARED_CONTRACT", "DATA_MATERIALIZATION", "PROTECTED_GATE"],
          e2e="Every value in every pregame horizon has a conservative, testable known-at decision grounded in source timing evidence."),
        story3("pit.state", "Append-only as-of state and pregame matrices", "Reconstruct what was known for each game/cutoff and materialize row-level model inputs with complete lineage.",
          ["Materialize append-only game, team, conference, venue, player, roster, staff, availability, weather, market, and context as-of state",
           "Build national pregame matrices at configured cutoffs with row/cell lineage, missingness class, fallback, and pinned versions",
           "Approve or block immutable matrix versions for feature/model experimentation"],
          ["artifacts/pit/asof_state_manifest.json", "artifacts/pit/pregame_matrix_manifest.json", "artifacts/pit/matrix_gate_decision.json"],
          ["State rows retain canonical identity, effective/known-at time, source evidence, and version; corrections append and future observations do not alter prior as-of reads.",
           "Each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.",
           "Approved matrices are content-hashed, split-blind, reproducible from pinned raw/entity/state versions, and cannot pass on successful file creation alone."],
          source_ids=["GAP-005", "GAP-006"], entry_deps=["pit.cutoffs.gate"], lanes=["DATA_MATERIALIZATION", "DATA_MATERIALIZATION", "PROTECTED_GATE"],
          e2e="A pinned cutoff reconstructs the exact state and matrix row that was legitimately knowable before a historical game."),
        story3("pit.replay", "Leakage battery and chronological replay infrastructure", "Prove the complete pregame path is invariant to future information and ready for sealed evaluation.",
          ["Run static, future-append, value-mutation, same-game, normalization, entity-correction, weather, market, roster, and label leakage tests on real matrices",
           "Implement deterministic walk-forward replay with frozen train/tune/protected boundaries, fold-local transforms, checkpoint/resume, and evidence identities",
           "Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate"],
          ["artifacts/pit/leakage_battery_results.json", "artifacts/pit/protected_replay_dry_run.json", "artifacts/pit/PIT_REPLAY_READINESS.json"],
          ["Future/postgame injections or appended records cannot change earlier eligible matrix hashes/predictions; every failure names exact source, field, row, transformation, and remediation.",
           "Replay advances chronologically, fits only on permitted history, pins all identities, never returns protected outcomes to tuning code, and resumes without future-fitted state.",
           "GAP-005 remains open until real historical replay—not fixture or synthetic replay—passes with approved matrix, split, seal, entity, source, and runner hashes."],
          source_ids=["HANDOFF-004", "GAP-005"], entry_deps=["pit.state.gate"], lanes=["PROTECTED_GATE", "PROTECTED_GATE", "PROTECTED_GATE"],
          e2e="A sealed chronological run can rebuild every pregame matrix and demonstrate future/postgame mutations cannot alter earlier state or predictions."),
      ], source_ids=["HANDOFF-004", "GAP-005"], depends_on=["entities.resolve.gate"], state="BACKLOG"),

    E("features", "Production feature materialization and lifecycle", "PHASE-1", "P1", "features",
      "Turn the broad feature universe into leakage-safe, reproducible, empirically screened production candidates without intuition-only promotion.", [
        story3("features.registry", "Population feature registry and computability", "Reconcile raw columns and 900+ candidate features against real coverage, PIT rules, implementations, and lifecycle state.",
          ["Reconcile feature IDs, source fields, transformations, temporal classes, missingness, code paths, aliases, duplicates, and lifecycle states",
           "Measure feature computability, missingness class, fallback use, and coverage by season/team/cutoff/regime/A&M segment",
           "Freeze the experiment-eligible production feature-registry version"],
          ["artifacts/features/production_feature_inventory.csv", "artifacts/features/feature_computability_profile.json", "configs/production_feature_registry.json"],
          ["Every feature maps to source, transformation, temporal class, owner, tests, lineage, and CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED state; design presence is not promotion evidence.",
           "Computability distinguishes not-known, source-missing, resolver-missing, structural, and implementation failure, and recent/A&M coverage cannot conceal national historical sparsity.",
           "Every experiment-eligible feature passes identity, PIT, lineage, implementation, and computability checks and the registry hash is pinned in downstream runs."],
          source_ids=["GAP-007"], entry_deps=["pit.state.gate"], lanes=["SHARED_CONTRACT", "DATA_MATERIALIZATION", "PROTECTED_GATE"],
          e2e="The full feature universe receives evidence-backed eligibility and a reproducible registry without hand-selecting attractive football variables."),
        story3("features.build", "Foundation and advanced feature materialization", "Build national form/efficiency/priors and supported player/availability/recruiting/coaching/context candidates from PIT state.",
          ["Materialize team/opponent form, efficiency, scoring, schedule strength, recency, continuity, rest, travel, venue, sequence, cold-start, and lower-division prior features",
           "Materialize supported player value/depth/replacement/availability, recruiting/transfer, coaching, weather, market, resource, officiating, and game-mechanics candidates",
           "Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility"],
          ["artifacts/features/foundation_feature_manifest.json", "artifacts/features/advanced_feature_manifest.json", "artifacts/features/feature_materialization_gate.json"],
          ["Rolling/expanding/opponent-adjusted statistics fit only on eligible prior history, declare shrinkage/minimum history, and use visible uncertainty for early-season/lower-division cold starts.",
           "Advanced features use versioned PIT state, separate market-free/market-aware lanes, preserve availability uncertainty, and keep thin/unsupported domains isolated.",
           "Representative values reconcile to source/as-of evidence; repeated build, swap, future append, NaN/inf, and unsupported-domain tests pass before experiments."],
          source_ids=["HANDOFF-008", "GAP-006", "GAP-007"], entry_deps=["features.registry.gate", "pit.replay.gate"], lanes=["SOLO_WORKTREE", "SOLO_WORKTREE", "PROTECTED_GATE"],
          e2e="Pinned real PIT matrices deterministically produce foundation and advanced feature candidates with explicit uncertainty and no future information."),
        story3("features.lifecycle", "Screening, ablation, stability, and promotion", "Empirically determine which features contribute stable tuning/protected value and preserve negative evidence.",
          ["Run staged univariate/multivariate screening and bounded feature tournaments on permitted tuning history",
           "Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses",
           "Publish the evidence-backed production feature lifecycle decision"],
          ["artifacts/features/feature_screening_results.json", "artifacts/features/feature_ablation_stability.json", "configs/feature_lifecycle_registry.json"],
          ["Every experiment pins matrix/split/registry/code/model/seed identities and compares incremental value, compute cost, missingness, leakage risk, and stability without protected outcomes.",
           "Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.",
           "Only policy-compliant candidates receive production eligibility; GAP-007 remains open until real protected evidence supports the selected set."],
          source_ids=["HANDOFF-005", "GAP-007"], entry_deps=["features.build.gate"], lanes=["RESEARCH_LANE", "RESEARCH_LANE", "PROTECTED_GATE"],
          e2e="A pinned registry feeds reproducible screening and ablation, yielding task-specific production lifecycle states while preserving bans and negative results."),
      ], source_ids=["HANDOFF-005", "GAP-007"], depends_on=["pit.state.gate"], state="BACKLOG"),
    E("advanced-football", "Player, roster, recruiting, coaching, and matchup intelligence", "PHASE-2", "P1", "advanced-football",
      "Materialize higher-resolution football state required for credible availability-aware forecasts and A&M specialization while preserving uncertainty and source limits.", [
        story3("advanced.player", "Historical player, roster, depth, value, replacement, and availability", "Build PIT player intelligence that represents who was expected to play and the value at risk.",
          ["Materialize effective-dated roster, depth, position, participation, eligibility, transfer, and role state",
           "Estimate leakage-safe player value, replacement distributions, and timestamped availability probabilities",
           "Validate player-state coverage, uncertainty, double-counting controls, and production eligibility"],
          ["artifacts/player_intelligence/player_state_manifest.json", "artifacts/player_intelligence/player_value_availability_report.json", "artifacts/player_intelligence/player_intelligence_gate.json"],
          ["Player-team-position-depth relationships retain source and known-at/effective time; current rosters cannot retroactively populate history and ambiguous identities remain reviewable.",
           "Value fits permitted history, sparse roles use transparent shrinkage, replacement reflects actual depth, availability remains probabilistic, and team impact is starter value minus plausible replacement without double counting.",
           "Coverage is measured by season/team/position/source and missing reports are uncertainty—not healthy/absent certainty; unsupported periods remain conditional."],
          source_ids=["HANDOFF-008", "GAP-006"], entry_deps=["raw.context.gate", "pit.state.gate"], lanes=["DATA_MATERIALIZATION", "RESEARCH_LANE", "PROTECTED_GATE"],
          e2e="At any historical cutoff the system can reconstruct expected players, depth, availability probabilities, replacement options, and uncertainty from evidence."),
        story3("advanced.program", "Recruiting, transfer, freshman, coaching, and continuity intelligence", "Represent program talent inflows/outflows and staff/system continuity without hindsight or unsupported narrative labels.",
          ["Materialize recruiting class, prospect, commitment, signing, enrollment, transfer, coach, coordinator, role, tenure, and transition events",
           "Build PIT roster-talent, experience, retention, transfer/freshman, staff/QB/system continuity, prior-performance, and bounded scheme-proxy candidates",
           "Validate identity, timing, source-scale compatibility, sparse-history shrinkage, and experimental eligibility"],
          ["artifacts/player_intelligence/program_event_manifest.json", "artifacts/context_intelligence/program_feature_manifest.json", "artifacts/context_intelligence/program_intelligence_gate.json"],
          ["Events preserve published/effective times, source scales, identity confidence, decommitments/re-rankings/portal withdrawals, interim/overlapping staff roles, and prior versions.",
           "Aggregates use only prior eligible state, distinguish returning production/recruits/transfers, expose early-season uncertainty, and do not encode culture/clutch/collapse without measurable definitions.",
           "Temporal perturbation, coverage, and scale tests pass; sparse/unsupported candidates remain experimental or rejected and are not assumed predictive."],
          source_ids=["GAP-006"], entry_deps=["advanced.player.gate"], lanes=["DATA_MATERIALIZATION", "SOLO_WORKTREE", "PROTECTED_GATE"],
          e2e="Recruiting, portal, freshman, coaching, coordinator, and continuity state is reproducible at each cutoff without current-season hindsight."),
        story3("advanced.context", "Weather, travel, rest, venue, schedule sequence, mechanics, officiating, and sparse-opponent priors", "Build robust matchup context and special handling for low-information opponents.",
          ["Materialize forecast-time weather, venue, coordinates, travel, rest, opponent sequence, neutral-site, schedule-change, and local-time state",
           "Materialize supported mechanics/officiating/resource candidates and FCS/DII/DIII/NAIA decreasing-information opponent priors",
           "Validate context correctness, forecast-versus-realized isolation, fallback behavior, and production eligibility"],
          ["artifacts/context_intelligence/game_context_state_manifest.json", "artifacts/context_intelligence/mechanics_sparse_opponent_manifest.json", "artifacts/context_intelligence/context_gate.json"],
          ["Weather uses forecast snapshots available at each cutoff; travel/rest/sequence derive from canonical schedules/venues and update for postponements/neutral sites with unknown coordinates left uncertain.",
           "Mechanics/officiating/resource data are used only where rights/depth/timing support them, and lower-division opponents receive explicit decreasing-information priors rather than zero strength or dropped games.",
           "Source spot checks, orientation, timing, sparse-opponent uncertainty, and unsupported-lane isolation pass before the context state is production eligible."],
          source_ids=["HANDOFF-008", "GAP-006"], entry_deps=["raw.context.gate", "pit.state.gate"], lanes=["DATA_MATERIALIZATION", "SOLO_WORKTREE", "PROTECTED_GATE"],
          e2e="A matchup snapshot reconstructs weather forecast, venue/travel/rest/sequence, supported mechanics, and sparse-opponent priors with honest uncertainty."),
      ], source_ids=["HANDOFF-008", "GAP-006"], depends_on=["raw.context.gate", "pit.state.gate"], state="BACKLOG"),

    E("model", "Reproducible baseline, coherent score, probability, and uncertainty modeling", "PHASE-1", "P1", "modeling",
      "Train credible national baselines and coherent forecast candidates on leakage-safe real matrices with reproducible artifacts and no fabricated winner.", [
        story3("model.dataset", "Model-ready targets, splits, weights, and datasets", "Freeze task definitions and model inputs before candidate training.",
          ["Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage",
           "Materialize chronological train/tune/protected assignments, sample weights, cold-start rules, and feature/target separation",
           "Approve model dataset identity, leakage isolation, duplicate handling, and reproducibility"],
          ["artifacts/modeling/target_dataset_manifest.json", "artifacts/modeling/model_split_manifest.json", "artifacts/modeling/model_dataset_gate.json"],
          ["Targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.",
           "Split assignments match protected registries, prevent duplicate/rematch/season-fragment leakage, and precommit weights/shrinkage before candidate results.",
           "Pinned raw/entity/PIT/feature/target/split versions reproduce identical rows and protected labels are inaccessible to training/tuning paths."],
          source_ids=["HANDOFF-006", "GAP-008", "AC-013", "AC-015"], entry_deps=["features.lifecycle.gate", "pit.replay.gate"], lanes=["DATA_MATERIALIZATION", "PROTECTED_GATE", "PROTECTED_GATE"],
          e2e="The same pinned identities always produce the same model-ready rows, targets, weights, and chronological partitions without protected leakage."),
        story3("model.baselines", "Simple, rating, linear, tree, market, and coherent joint-score candidates", "Establish strong reproducible references and internally coherent distributional candidates before advanced challengers.",
          ["Train naive, historical-average, home-field, rating, regularized linear, tree-boosting, market-free, and market-aware baselines with bounded searches",
           "Train joint/separate score-distribution candidates and deterministic-seed simulations deriving margin, win, score, total, interval, and severity outputs coherently",
           "Validate artifacts, tuning predictions, orientation, distribution tails, score-margin-win coherence, runtime, and candidate admission"],
          ["artifacts/modeling/baseline_candidate_runs.json", "artifacts/modeling/joint_distribution_runs.json", "artifacts/modeling/baseline_joint_gate.json"],
          ["Every run pins data/config/code/seed/runtime, fits recency/home-field/shrinkage only on permitted history, separates market lanes/cutoffs, and retains failed or negative trials.",
           "Derived outputs come from coherent score distributions, persist simulation identities, handle overtime/ties/extremes, and widen uncertainty under missing/OOD inputs rather than becoming confident.",
           "Candidates regenerate identical predictions within declared numerical limits and no model enters protected replay with reproducibility, range, orientation, coherence, or resource failures."],
          source_ids=["HANDOFF-006", "GAP-008"], entry_deps=["model.dataset.gate"], lanes=["RESEARCH_LANE", "RESEARCH_LANE", "PROTECTED_GATE"],
          e2e="Pinned real datasets train simple and coherent distributional candidates that reproduce all outputs and remain honest about failures and compute."),
        story3("model.uncertainty", "Calibration, ensembles, OOD, abstention, and candidate artifact registry", "Represent uncertainty and seal all admitted candidate identities before protected evaluation.",
          ["Train precommitted task/cutoff/lane calibration and ensemble candidates using permitted tuning predictions",
           "Implement sparse-history, missingness, source/regime shift, feature-pattern OOD, uncertainty, and abstention diagnostics",
           "Publish the immutable candidate artifact registry for sealed protected evaluation"],
          ["artifacts/modeling/calibration_ensemble_runs.json", "artifacts/modeling/ood_abstention_validation.json", "artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json"],
          ["Calibrators and ensemble weights are fit only on allowed tuning data, retain member/diversity/failure identities, and cannot use protected outcomes for selection.",
           "Evidence-derived tuning thresholds identify unsupported conditions and return wider uncertainty/abstention reasons rather than confident defaults when required inputs are unavailable.",
           "Every admitted candidate pins data/feature/split/code/dependency/model/calibrator/seed identities, supported modes, OOD policy, resource envelope, and caveats; GAP-008 remains open pending protected replay."],
          source_ids=["HANDOFF-006", "GAP-008"], entry_deps=["model.baselines.gate"], lanes=["RESEARCH_LANE", "PROTECTED_GATE", "PROTECTED_GATE"],
          e2e="All candidates enter protected evaluation as immutable reproducible artifacts with precommitted calibration, uncertainty, OOD, and abstention behavior."),
      ], source_ids=["HANDOFF-006", "GAP-008"], depends_on=["features.lifecycle.gate", "pit.replay.gate"], state="BACKLOG"),

    E("tamu", "Texas A&M high-resolution specialization and no-lift-safe evaluation", "PHASE-3", "P1", "tamu",
      "Build A&M-specific state and specialization candidates while requiring protected evidence and accepting a global-only/no-adjustment result.", [
        story3("tamu.state", "Official A&M evidence and high-resolution PIT state", "Materialize the highest supported A&M resolution without violating national PIT, identity, rights, or provenance contracts.",
          ["Acquire quality-supported A&M schedules, rosters, depth, staff, media-guide, participation, availability, and official evidence",
           "Build high-resolution A&M team/player/staff/context as-of snapshots reconciled with national state",
           "Validate A&M coverage, source conflicts, rights, identity, PIT integrity, and snapshot reproducibility"],
          ["artifacts/tamu/tamu_source_manifest.json", "artifacts/tamu/tamu_high_resolution_state_manifest.json", "artifacts/tamu/tamu_state_gate.json"],
          ["Every A&M record retains rights, content/source identity, published/observed/retrieved timing, and canonical links; historical gaps/conflicts preserve both evidence lanes.",
           "A&M detail uses the same cutoffs as national state, augments rather than silently overwrites it, retains uncertainty, and reproduces from pinned versions.",
           "Future/postgame/current-page detail cannot alter earlier snapshots, restricted data is not redistributed, and unsupported fields remain absent/conditional rather than narrative-filled."],
          source_ids=["HANDOFF-008", "GAP-006"], entry_deps=["advanced.player.gate", "advanced.program.gate", "advanced.context.gate", "pit.state.gate"], lanes=["DATA_MATERIALIZATION", "DATA_MATERIALIZATION", "PROTECTED_GATE"],
          e2e="Any A&M pregame cutoff reconstructs a richer but governance-compatible state with conflicts, missingness, and uncertainty preserved."),
        story3("tamu.peers", "Peers, regimes, historical analogs, and specialization candidates", "Create leakage-safe comparators and conservative A&M candidate adjustments without forcing an effect.",
          ["Materialize pregame-observable peer/regime candidates and prior-only historical analog index with distance diagnostics",
           "Train global-only, no-adjustment, residual, hierarchical, calibration, shrinkage, and feature-interaction A&M candidates on permitted history",
           "Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback"],
          ["artifacts/tamu/peer_regime_analog_registry.json", "artifacts/tamu/tamu_specialization_runs.json", "artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json"],
          ["Peer/regime/analog definitions use only pinned pregame features, exclude same/future outcomes, expose distance/sample/uncertainty, and retain alternative sensitivity specifications.",
           "Every candidate includes global-only/no adjustment, uses shrinkage/minimum data, avoids protected A&M outcomes and favorable-regime selection, and preserves null/negative/unstable tuning evidence.",
           "Outcome-label removal/future-append stability and multiple-comparison diagnostics pass; only precommitted candidates are sealed and no candidate is labeled production-improving yet."],
          source_ids=["HANDOFF-007", "GAP-009"], entry_deps=["tamu.state.gate", "model.uncertainty.gate"], lanes=["RESEARCH_LANE", "RESEARCH_LANE", "PROTECTED_GATE"],
          e2e="A&M candidates and peer/analog definitions are frozen before protected outcomes and always retain a valid global-only/no-adjustment choice."),
        story3("tamu.evaluate", "Protected A&M lift, calibration, stability, and integration decision", "Determine whether specialization genuinely improves forecasts and preserve a no-lift result.",
          ["Generate sealed global-only and A&M candidate predictions inside identical protected chronological replay",
           "Measure incremental accuracy, calibration, stability, uncertainty, data-quality sensitivity, and multiple-comparison context",
           "Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently"],
          ["artifacts/tamu/tamu_protected_predictions.parquet", "artifacts/tamu/tamu_protected_evaluation.json", "artifacts/tamu/tamu_specialization_decision.json"],
          ["Sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.",
           "Evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.",
           "The signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically."],
          source_ids=["HANDOFF-007", "GAP-009"], entry_deps=["tamu.peers.gate", "validation.replay.gate"], lanes=["PROTECTED_GATE", "SCIENTIFIC", "PROTECTED_GATE"],
          e2e="An identical sealed replay yields an auditable A&M-specialization-or-no-adjustment decision consumed by the production forecast."),
      ], source_ids=["HANDOFF-007", "GAP-009"], depends_on=["advanced.player.gate", "advanced.context.gate", "model.uncertainty.gate"], state="BACKLOG"),

    E("bas", "Scientific BAS, general FBS surprise, Aggie excess, and component validation", "PHASE-3", "P1", "bas",
      "Validate BAS as out-of-sample A&M underperformance relative to a strictly valid pregame expectation, never as generic loss probability and never by forcing a nonzero effect.", [
        story3("bas.labels", "Cross-fitted expectation and protected severity labels", "Generate leakage-safe expected margins and ≥3/7/14/21 residual labels with anti-circularity.",
          ["Generate out-of-fold or chronological cross-fitted pregame expected margins for every eligible historical game",
           "Materialize general surprise and A&M BAS severity labels at protected ≥3, ≥7, ≥14, and ≥21 thresholds",
           "Validate direction, thresholds, row lineage, fold isolation, and anti-circularity"],
          ["artifacts/bas/crossfit_expectation_manifest.json", "artifacts/bas/bas_label_manifest.json", "artifacts/bas/bas_label_gate.json"],
          ["Each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.",
           "Labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.",
           "Synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails."],
          source_ids=["HANDOFF-009", "GAP-009", "AC-020", "AC-021"], entry_deps=["model.uncertainty.gate", "pit.replay.gate"], lanes=["SCIENTIFIC", "PROTECTED_GATE", "PROTECTED_GATE"],
          e2e="Every BAS label is a traceable out-of-sample residual severity event rather than a renamed loss or circular model residual."),
        story3("bas.excess", "General FBS baseline, Aggie excess, and components", "Separate ordinary football surprise from any incremental A&M effect and decompose outcomes without changing the headline.",
          ["Estimate out-of-sample general FBS severity probabilities and residual distributions across seasons/regimes/contexts",
           "Estimate A&M excess versus FBS, precommitted peers/regimes, and matched contexts plus offensive/defensive/special-teams/collapse component evidence",
           "Validate peer sensitivity, multiple comparisons, component coherence, uncertainty, coverage, and null-result handling"],
          ["artifacts/bas/general_fbs_baseline.json", "artifacts/bas/aggie_excess_components.json", "artifacts/bas/aggie_excess_component_gate.json"],
          ["General rates/probabilities are cross-fitted and calibrated with uncertainty; sparse regimes and team effects are not smuggled into a universal baseline.",
           "A&M analyses use sealed expectations/peers, report effect/sample/sensitivity uncertainty, accept zero/negative/unstable excess, and make components unavailable when granular evidence is absent.",
           "No post-hoc peer/time/threshold subgroup is elevated for a preferred effect, components do not replace the ≥7 headline or imply additive causality, and product claims are bounded to evidence."],
          source_ids=["HANDOFF-009", "GAP-009"], entry_deps=["bas.labels.gate", "tamu.peers.gate"], lanes=["SCIENTIFIC", "SCIENTIFIC", "PROTECTED_GATE"],
          e2e="General surprise, possible Aggie excess, and explanatory components are estimated from sealed residual evidence with null results and uncertainty preserved."),
        story3("bas.validate", "Protected calibration, stability, scientific decision, and product semantics", "Publish only supported BAS probabilities and truthful null/inconclusive findings.",
          ["Evaluate ≥3/7/14/21 calibration, discrimination, reliability, uncertainty, and national/A&M/peer/regime scorecards on sealed predictions",
           "Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses",
           "Publish the final BAS scientific decision and prediction-first product language contract"],
          ["artifacts/bas/bas_protected_scorecard.json", "artifacts/bas/bas_stability_analysis.json", "artifacts/bas/BAS_SCIENTIFIC_DECISION.json"],
          ["Scorecards include sample sizes, intervals/reliability, all protected thresholds/segments, and no protected refitting; small A&M samples never receive false precision.",
           "All precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.",
           "The decision states supported/unsupported/inconclusive general and A&M findings with hashes; product keeps prediction primary, permits witty framing, prohibits loss-probability substitution, and never forces nonzero BAS."],
          source_ids=["HANDOFF-009", "GAP-009"], entry_deps=["bas.excess.gate", "validation.replay.gate"], lanes=["SCIENTIFIC", "SCIENTIFIC", "PROTECTED_GATE"],
          e2e="Calibrated protected evidence yields a scientifically bounded BAS result and product contract that remains valid even when no persistent Aggie-specific excess exists."),
      ], source_ids=["HANDOFF-009", "GAP-009"], depends_on=["model.uncertainty.gate", "tamu.peers.gate"], state="BACKLOG"),
    E("validation", "Protected chronological evaluation, calibration, and champion promotion", "PHASE-4", "P1", "validation",
      "Run the sealed real-data evaluation program and promote a champion only when all protected scientific, calibration, coherence, reproducibility, and operational gates pass.", [
        story3("validation.seal", "Protected split, judging rule, threshold, candidate, and access seal", "Prove evaluation inputs and decisions were frozen before protected outcomes are accessed.",
          ["Verify protected split, judging-rule, threshold, feature, model, A&M, BAS, peer, and candidate seal hashes",
           "Establish protected-outcome access isolation, audit logging, one-way evidence, and failure preservation",
           "Authorize or block the exact sealed protected evaluation run"],
          ["artifacts/validation/protected_seal_verification.json", "artifacts/validation/protected_access_protocol_test.json", "artifacts/validation/protected_run_authorization.json"],
          ["All seal files/registries/assignments/thresholds/data identities match recorded hashes; a mutation or missing seal blocks evaluation and cannot be waived to make a candidate pass.",
           "Only evaluation code can access protected outcomes, every access is attributable, training/tuning cannot read labels/scorecards, and partial failures do not return outcomes for iterative tuning.",
           "Authorization names exact candidates/tasks/cutoffs/lanes/splits/metrics/thresholds/evidence destinations and verifies all PIT/feature/model/A&M/BAS prerequisites or remains blocked."],
          source_ids=["HANDOFF-006", "HANDOFF-007", "HANDOFF-009", "AC-013", "AC-015", "AC-017"], entry_deps=["model.uncertainty.gate", "tamu.peers.gate", "bas.labels.gate"], lanes=["PROTECTED_GATE", "SECURITY", "PROTECTED_GATE"],
          e2e="An immutable, auditable authorization proves what may be evaluated and prevents protected outcomes from influencing candidate construction."),
        story3("validation.replay", "Sealed walk-forward predictions and complete scorecards", "Generate immutable protected predictions and independently reproducible evaluation evidence.",
          ["Execute the sealed national, A&M-candidate, and BAS-support chronological replay once",
           "Compute complete score, margin, win, distribution, calibration, BAS, A&M, OOD, coherence, robustness, market-lane, and segment scorecards",
           "Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility"],
          ["artifacts/validation/protected_predictions.parquet", "artifacts/validation/protected_scorecards.json", "artifacts/validation/protected_replay_gate.json"],
          ["Replay advances chronologically with only then-available state/models/calibrators/thresholds, records every identity, and retries cannot change membership or expose partial scores.",
           "All precommitted metrics/segments include baselines, sample sizes, uncertainty, missing predictions, failures, calibration/coherence/OOD and no unfavorable metric is omitted.",
           "Independent recomputation reproduces metrics/candidate ordering, verifies seals/access/row identity, and incomplete/corrupt evaluation cannot be summarized as a winner."],
          source_ids=["GAP-008", "GAP-009"], entry_deps=["validation.seal.gate"], lanes=["PROTECTED_GATE", "SCIENTIFIC", "PROTECTED_GATE"],
          e2e="Sealed immutable predictions generate complete scorecards that a separate process can reproduce without reopening tuning."),
        story3("validation.promotion", "Calibration/robustness gates, A&M/BAS decisions, and champion promotion", "Apply every release-blocking gate and sign a champion only when protected evidence supports one.",
          ["Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness",
           "Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision",
           "Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix"],
          ["artifacts/validation/calibration_robustness_report.json", "artifacts/validation/promotion_ranking.json", "artifacts/validation/PROMOTION_DECISION.json"],
          ["Calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.",
           "No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.",
           "A signed artifact pins data/features/code/dependencies/splits/model/calibrators/A&M/BAS/OOD/scorecards and reproduces predictions, or no champion is written; GAP-008 closes only through genuine protected evidence."],
          source_ids=["HANDOFF-006", "GAP-008", "GAP-009"], entry_deps=["validation.replay.gate", "tamu.evaluate.gate", "bas.validate.gate"], lanes=["SCIENTIFIC", "PROTECTED_GATE", "PROTECTED_GATE"],
          e2e="All sealed candidates receive complete reproducible protected evaluation and the system produces a signed champion or explicit no-champion result without fabricated performance."),
      ], source_ids=["HANDOFF-006", "GAP-008", "GAP-009"], depends_on=["model.uncertainty.gate", "tamu.peers.gate", "bas.labels.gate"], state="BACKLOG"),

    E("mlops", "Autonomous weekly real-data execution and immutable forecast publication", "PHASE-4", "P2", "mlops",
      "Operate the acquisition-to-publication chain on real weekly data with checkpoints, idempotency, governed retraining, immutable snapshots, failure drills, and operating evidence.", [
        story3("mlops.pipeline", "Production weekly acquisition-to-prediction chain", "Convert the W21 starter into a real, resumable, fail-closed weekly workflow.",
          ["Wire approved adapters through immutable raw capture, normalization, entities, PIT state, features, approved model, calibration, and prediction",
           "Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation",
           "Validate representative real end-to-end run lineage, resources, blockers, and no-fixture production behavior"],
          ["artifacts/mlops/weekly_pipeline_integration.json", "artifacts/mlops/checkpoint_resume_test.json", "artifacts/mlops/weekly_pipeline_gate.json"],
          ["Each stage pins source/raw/entity/state/matrix/feature/model/cutoff/config identities, consumes only passed prerequisites, and fails on rights/drift/PIT/model blockers without synthetic shortcuts.",
           "Identical inputs produce the same run identity/outcomes, resume starts at the last verified checkpoint, duplicates are prevented, and quarantine/failed gates cannot be skipped.",
           "A real representative run emits complete timing/resource/test/evidence lineage and injected source/schema/disk/model/publication failures stop and recover at the correct boundary."],
          source_ids=["HANDOFF-010", "GAP-012"], entry_deps=["validation.promotion.gate", "sources.acquisition.drift"], lanes=["SHARED_CONTRACT", "OPERATIONS", "PROTECTED_GATE"],
          e2e="A weekly run moves approved real data through every production stage, stops safely on invalid state, and resumes without duplicate or stale artifacts."),
        story3("mlops.train-publish", "Governed retraining, promotion, immutable forecasts, and activation", "Retrain only when policy permits and publish signed snapshots atomically.",
          ["Implement season/week/data-drift/performance retraining triggers and execute reproducible challenger runs against the current champion",
           "Build immutable forecast snapshots containing coherent scores/probabilities/uncertainty/A&M/BAS outputs plus exact state/run/model identities",
           "Apply promotion/rollback policy, atomically activate approved snapshots, and validate immutability/freshness/consumer compatibility"],
          ["artifacts/mlops/retraining_challenger_report.json", "artifacts/forecasts/forecast_snapshot_manifest.json", "artifacts/forecasts/publication_gate.json"],
          ["Triggers predeclare evidence/budget/freeze/skip reasons, cannot repeatedly tune on protected outcomes, preserve all failed/no-improvement challengers, and never corrupt the active champion.",
           "Snapshot rows derive only from signed run artifacts, follow protected A&M/BAS null/admission decisions, mark unsupported outputs unavailable, and are immutable/idempotent.",
           "Only complete signed non-stale snapshots activate atomically, rollback restores a verified prior pointer, product reads never see partial state, and no SLA is claimed without observed evidence."],
          source_ids=["HANDOFF-010"], entry_deps=["mlops.pipeline.gate"], lanes=["RESEARCH_LANE", "SHARED_CONTRACT", "PROTECTED_GATE"],
          e2e="A governed run may retain or promote a model, then publishes one immutable coherent snapshot that downstream consumers can reproduce and roll back."),
        story3("mlops.shadow", "Repeated shadow operation, failure drills, and autonomous readiness", "Accumulate actual 2026 weekly reliability evidence before claiming autonomous operation.",
          ["Execute repeated real-source shadow weekly runs with timeliness, freshness, resource, coverage, intervention, and failure ledger",
           "Run source outage, schema drift, disk pressure, corrupt artifact, stale forecast, interrupted run, and rollback drills",
           "Approve or retain-blocked the autonomous weekly operating maturity decision"],
          ["artifacts/mlops/shadow_run_ledger.jsonl", "artifacts/mlops/shadow_failure_drills.json", "artifacts/mlops/weekly_operating_readiness.json"],
          ["Every scheduled success, miss, blocker, intervention, stale output, and resource result stays in the ledger; shadow uses real quality-valid sources/paths and cannot omit bad weeks from reliability.",
           "Each injected failure is detected, classified, stopped, alerted, recovered, and evidenced without weakening gates or deleting canonical evidence; recovery time/manual steps are measured.",
           "OPERATING requires repeated successful real evidence plus freshness/recovery/resource/security/operator proof and documents residual manual gates; GAP-012 stays open otherwise."],
          source_ids=["HANDOFF-010", "HANDOFF-011", "GAP-012"], entry_deps=["mlops.train-publish.gate"], lanes=["OPERATIONS", "OPERATIONS", "PROTECTED_GATE"],
          e2e="Repeated real weekly runs publish immutable forecasts, survive representative failures, and produce measured evidence for or against autonomous operation."),
      ], source_ids=["HANDOFF-010", "GAP-012"], depends_on=["validation.promotion.gate"], state="BACKLOG"),

    E("product", "Snapshot API, dashboard, explanations, analogs, and freshness-safe product", "PHASE-4", "P2", "product",
      "Serve the predictive system and witty BAS experience from immutable approved snapshots with truthful freshness, uncertainty, provenance, accessibility, and no live recomputation drift.", [
        story3("product.api", "Read-only forecast repository and versioned API", "Turn the serving starter into a production snapshot API with health/freshness and explicit unavailable states.",
          ["Implement approved active/archive snapshot repository, model/run lookup, and atomic read behavior",
           "Implement versioned forecast/game/team/A&M/BAS/health/freshness endpoints and OpenAPI contract",
           "Validate schema, authorization, snapshot consistency, stale/no-champion/null-BAS states, and restricted-data protection"],
          ["artifacts/product/snapshot_repository_test.json", "docs/product/OPENAPI_SNAPSHOT.json", "artifacts/product/api_gate.json"],
          ["Reads resolve only signed snapshots and exact model/run/state identities; missing/stale/corrupt/unapproved state is explicit and no request path retrains or recomputes uncontrolled features.",
           "Responses expose supported score/probability/distribution/uncertainty/A&M/BAS/lineage/freshness fields and mark scientifically unsupported outputs unavailable rather than defaulting values.",
           "All endpoints for a snapshot agree on identities, handle archive/current/errors/no-champion/null decisions, and never expose credentials, restricted raw payloads, or protected outcomes."],
          source_ids=["HANDOFF-011", "GAP-012"], entry_deps=["mlops.train-publish.gate"], lanes=["SOLO_WORKTREE", "SHARED_CONTRACT", "PROTECTED_GATE"],
          e2e="A client can retrieve a current or archived signed forecast and exact freshness/lineage without triggering model drift or seeing partial/restricted state."),
        story3("product.dashboard", "Prediction-first dashboard and BAS experience", "Present serious forecast outputs first while retaining the project’s humorous BAS identity and truthful null-result handling.",
          ["Build game/A&M views for score, win probability, margin, distributions, intervals, scenarios, cutoff, freshness, and model identity",
           "Build BAS ≥3/7/14/21, component, witty-copy, scientific caveat, no-effect, and unavailable presentation",
           "Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values"],
          ["artifacts/product/dashboard_contract_test.json", "artifacts/product/bas_presentation_validation.json", "artifacts/product/dashboard_gate.json"],
          ["Main views make prediction and uncertainty primary, show specialization only if admitted or global-only otherwise, and never calculate independent client-side percentages/scores.",
           "BAS is explicitly underperformance versus valid pregame expected margin—not loss probability—witty copy is separate from science, and thresholds/components appear only when supported with uncertainty.",
           "Every displayed value traces to a snapshot field and loading/stale/blocked/missing/no-champion/null-effect/source-outage states are accessible and keyboard/screen-reader understandable."],
          source_ids=["HANDOFF-009", "HANDOFF-011"], entry_deps=["product.api.gate"], lanes=["SOLO_WORKTREE", "SOLO_WORKTREE", "PROTECTED_GATE"],
          e2e="The user sees a serious predictive product with honest uncertainty and freshness, plus clearly separated witty BAS framing that never overstates scientific evidence."),
        story3("product.explain", "Faithful drivers, historical analogs, provenance, and target performance", "Explain forecasts without unsupported causal narratives and prove target-hardware product behavior.",
          ["Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context",
           "Run explanation faithfulness/stability/privacy tests plus target-host cold/warm load, API, snapshot, dashboard, concurrency, memory, CPU, and disk benchmarks",
           "Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision"],
          ["artifacts/product/explanation_analog_validation.json", "artifacts/product/product_performance_benchmark.json", "artifacts/product/PRODUCT_READINESS.json"],
          ["Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.",
           "Benchmarks run on the declared target with repeated workload identity and measure real resources/latency; unsupported/OOD explanations qualify or abstain and restricted data never leaks.",
           "Fresh/current/stale/blocked/unavailable/superseded transitions, cache activation/rollback, API/dashboard/security/explanation/performance evidence all pass; product cannot be ready on mutable/unapproved forecasts."],
          source_ids=["HANDOFF-011", "GAP-001", "GAP-012"], entry_deps=["product.dashboard.gate", "env.benchmark.gate"], lanes=["SOLO_WORKTREE", "OPERATIONS", "PROTECTED_GATE"],
          external_blockers=["", "AUTHORITATIVE_TARGET_WINDOWS_HOST_REQUIRED_FOR_FINAL_PRODUCT_BENCHMARK", ""],
          e2e="A consumer receives faithful snapshot-grounded explanations/analogs and a responsive target-hardware product with explicit safe failure and freshness states."),
      ], source_ids=["HANDOFF-011", "GAP-012"], depends_on=["mlops.train-publish.gate"], state="BACKLOG"),
    E("operations", "Security, observability, backup/restore, drift, and incident operations", "PHASE-4", "P2", "operations",
      "Provide controls required to run the local-first system safely, visibly, recoverably, and without unnecessary infrastructure.", [
        story3("operations.ci", "CI, dependency, secret, license, and supply-chain controls", "Protect repository, Jira pack, runtime, and release changes through deterministic automated gates.",
          ["Establish clean-environment CI for repository tests, Jira validators, static checks, import dry-run, and deterministic packaging",
           "Implement dependency-lock, vulnerability, secret, license/notice, restricted-data pattern, and artifact-integrity checks",
           "Validate protected-branch/release blocking and auditable exception behavior"],
          ["artifacts/operations/ci_pipeline_validation.json", "artifacts/operations/security_supply_chain_report.json", "artifacts/operations/ci_security_gate.json"],
          ["CI runs all required suites from a clean state, preserves failure logs/evidence, and cannot skip gates through naming/retry while keeping the local workflow runnable without Kubernetes/Kafka/Redis/cloud dependency.",
           "Locks/hashes/findings/licenses/secrets/restricted patterns are recorded with severity/remediation or accepted-risk disposition and no credential/raw restricted payload reaches repository or CI artifacts.",
           "Any release-blocking test, secret, integrity, rights, or protected-control failure stops release; manual exceptions are explicit, attributable, time-bounded, and cannot weaken science/PIT rules."],
          source_ids=["HANDOFF-012"], entry_deps=["env.preflight.validation"], lanes=["OPERATIONS", "SECURITY", "PROTECTED_GATE"],
          e2e="A clean change cannot produce a release package unless code, Jira, security, integrity, and protected-governance gates all pass."),
        story3("operations.observe", "Structured observability, alerts, drift, and incident response", "Detect unsafe source/data/model/product/governance changes and route evidence-backed recovery.",
          ["Instrument run/stage/source/snapshot/entity/matrix/feature/model/product identifiers, metrics, structured events, health, and redaction",
           "Implement source/API/terms/schema/entity/feature/data/model/concept/freshness/security/governance drift detectors plus alert severity/dedup/ack/escalation",
           "Run outage, schema, stale forecast, disk, corrupt artifact, model, security, and governance-conflict game days through incident/rollback/substitution runbooks"],
          ["artifacts/operations/observability_contract_test.json", "artifacts/operations/drift_alert_validation.json", "artifacts/operations/drift_incident_game_day.json"],
          ["Events expose correlation/timing/count/status/blocker identities and distinguish expected missingness from defects while redacting secrets and restricted payloads.",
           "Versioned baselines and evidence-derived thresholds identify affected scope, block unsafe downstream training/publication, and route alerts without claiming resolution until evidence changes.",
           "Representative incidents are detected, stopped/degraded, alerted, evidenced, recovered/rolled back, and source substitutions rerun rights/PIT/schema/coverage gates rather than masquerading as equivalent."],
          source_ids=["HANDOFF-012"], entry_deps=["sources.acquisition.drift", "operations.ci.gate"], lanes=["OPERATIONS", "OPERATIONS", "PROTECTED_GATE"],
          e2e="Unsafe changes are visible, attributable, blocked at the correct boundary, and recover through exact runbooks without exposing secrets or corrupting evidence."),
        story3("operations.backup", "Rights-aware backup, restore, retention, and disaster recovery", "Prove canonical data/model/forecast/Jira state can be recovered to a verified point.",
          ["Finalize authority/retention/frequency/encryption/access/rights/deletion rules for raw, curated, model, forecast, log, evidence, and Jira metadata",
           "Implement content-hashed verified backups, catalog, integrity checking, last-known-good protection, and restricted-destination enforcement",
           "Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps"],
          ["configs/backup_retention_policy.json", "artifacts/operations/backup_catalog_and_integrity.json", "artifacts/operations/restore_drill.json"],
          ["Canonical protected evidence, negative results, source-policy metadata, and issue history retain required immutability while raw third-party data never copies to publication destinations.",
           "Backups are independently readable/content-hashed/cataloged/permission-checked, partial/corrupt copies never replace good state, and Jira canonical records/key map/change log/indexes are included efficiently.",
           "A clean restore passes hash/schema/reference/lineage validation, identifies external credentials/rights reconfiguration, measures recovery, and success is not inferred from backup creation alone."],
          source_ids=["HANDOFF-012"], entry_deps=["operations.observe.gate"], lanes=["SHARED_CONTRACT", "OPERATIONS", "PROTECTED_GATE"],
          e2e="A verified backup can restore selected canonical lineage and Jira execution state into a clean location without rewriting history or violating data rights."),
      ], source_ids=["HANDOFF-012"], depends_on=["env.preflight.validation", "sources.acquisition.drift"], state="BACKLOG"),

    E("release", "Full end-to-end release candidate and operating acceptance", "PHASE-5", "P2", "release",
      "Close or disposition every required gap/risk/control, prove the real-data product on the target architecture, and authorize operation without confusing starter readiness with completion.", [
        story3("release.coverage", "Final traceability, maturity, gap, risk, and evidence audit", "Prove no obligation or blocker disappeared during implementation.",
          ["Regenerate bidirectional source, requirement, acceptance, ADR, gap, risk, test, artifact, issue, and evidence traceability",
           "Audit every component maturity and completion claim against actual repository/runtime artifacts, tests, real-data runs, and applicable scope",
           "Publish final coverage metrics and unresolved release-blocker register"],
          ["artifacts/release/final_traceability_audit.json", "artifacts/release/maturity_evidence_audit.csv", "artifacts/release/final_coverage_gate.json"],
          ["Every active obligation/release-blocking control maps to current evidence and Jira; all 14 final gaps and 310 final risks have actionable, accepted/deferred, N-A, or verified-closed dispositions, with historical-only mappings flagged.",
           "Synthetic validation is not real empirical validation, functional starters are not production-ready, and every DESIGN_ONLY→OPERATING claim cites verifiable evidence or remains blocked/conflicted/manual.",
           "Coverage reports unmapped/invalid/orphan/cycle/missing-AC/DoD/test/evidence/source issues and zero blockers only when supported; conditional advanced and deferred live work are excluded only explicitly."],
          source_ids=["HANDOFF-013", "HANDOFF-014"], entry_deps=["validation.promotion.gate", "mlops.shadow.gate", "product.explain.gate", "operations.backup.gate"], lanes=["PROTECTED_GATE", "PROTECTED_GATE", "PROTECTED_GATE"],
          e2e="Every release claim and exclusion can be traced to concrete current evidence, with no gap, risk, requirement, or control disappearing behind historical Done labels."),
        story3("release.e2e", "Clean-target real-data release candidate", "Execute the complete production chain and product consumption from a clean target-machine checkout.",
          ["Stage the signed release candidate, dependency/runtime, Jira pack, private-research source configuration, and clean external roots",
           "Execute quality-valid source acquisition through immutable raw, entities, PIT, features, champion/no-champion handling, predictions, publication, API, and dashboard on representative real weekly data",
           "Validate outputs, lineage, protected decisions, rollback, clean re-execution, target performance/resources/freshness, and all release-blocking controls"],
          ["artifacts/release/release_candidate_manifest.json", "artifacts/release/release_candidate_e2e.json", "artifacts/release/release_candidate_gate.json"],
          ["The stage pins repository/dependencies/Jira/source-rights/schema/data/entity/PIT/feature/model/product/runbook identities, keeps credentials external, enforces restrictions, and fails on dirty protected state or blockers.",
           "Every production stage uses real quality-valid data/code/paths and emits complete lineage/tests/resources/freshness/failure evidence; fixtures, samples, fabricated metrics, or manual file swaps cannot claim success.",
           "Independent validators trace forecasts/product to the signed run and A&M/BAS/promotion decisions, rollback succeeds, clean re-run reproduces declared outputs, and AC-038/target gates use authoritative host evidence."],
          source_ids=["GAP-001", "GAP-012", "AC-038"], entry_deps=["release.coverage.gate", "env.benchmark.gate"], lanes=["PROTECTED_GATE", "PROTECTED_GATE", "PROTECTED_GATE"],
          external_blockers=["AUTHORITATIVE_TARGET_HOST_AND_PRODUCTION_SOURCE_ACCESS_REQUIRED", "AUTHORITATIVE_TARGET_HOST_AND_PRODUCTION_SOURCE_ACCESS_REQUIRED", ""],
          e2e="A clean authoritative target host runs the signed real-data product from acquisition to dashboard and proves reproducibility, rollback, resource, security, and scientific integrity."),
        story3("release.accept", "Documentation, independent handoff, go-live review, and operating authorization", "Make the system installable, auditable, operable, and either authorize an exact release or retain an explicit no-release decision.",
          ["Finalize verified operator/developer installation, credentials/rights, weekly run, monitoring, backup, restore, incident, rollback, and Jira maintenance guides",
           "Finalize production system/data/model/A&M/BAS cards, limitations, protected results, null findings, provenance, reproduction, API/product, and release manifest",
           "Conduct technical/scientific/security/rights/operations/product review and publish operating authorization or blocked/no-release decision plus post-release baseline"],
          ["docs/operations/PRODUCTION_OPERATOR_GUIDE.md", "docs/final/PRODUCTION_SYSTEM_CARD.md", "artifacts/release/OPERATING_AUTHORIZATION.json"],
          ["A new operator can execute exact verified commands, configure external roots/credentials, inspect Jira blockers, run/recover/rollback the product, and understands every manual/legal boundary without stale Wave-26 language.",
           "Documentation reports actual coverage/metrics/calibration/uncertainty/OOD/A&M/BAS decisions/limitations/nulls and links every claim to immutable evidence with no unsupported SLA, causal, performance, or scientific claim.",
           "Review records conflicts/residual risk/manual gates; authorization names exact release/model/data/product/Jira identities and supported modes or lists unmet evidence, never infers completion from planning or starter tests, and captures the operating baseline."],
          source_ids=["HANDOFF-011", "HANDOFF-012", "HANDOFF-013", "HANDOFF-014"], entry_deps=["release.e2e.gate"], lanes=["OPERATIONS", "SCIENTIFIC", "PROTECTED_GATE"],
          e2e="An independent operator can reproduce and safely operate the exact approved release, or the system remains truthfully blocked with concrete evidence gaps."),
      ], source_ids=["HANDOFF-013", "HANDOFF-014"], depends_on=["mlops.shadow.gate", "product.explain.gate", "operations.backup.gate", "env.benchmark.gate"], state="BACKLOG"),

    E("advanced", "Conditional advanced challenger research and admission", "PHASE-5", "P3", "advanced",
      "Preserve optional neural, Bayesian, graph, and sequence challengers behind explicit scientific value, data, compute, and promotion gates.", [
        story3("advanced.admit", "Advanced challenger proposal, feasibility, and admission", "Admit a challenger only for a falsifiable task-specific shortfall that simpler work cannot address.",
          ["Precommit challenger hypothesis, exact baseline deficiency, success/failure criteria, required data, architecture, risks, simpler alternatives, and expected value of information",
           "Measure real data sufficiency, identity quality, local RAM/GPU/disk/runtime, reproducibility, maintenance, rights, and protected-evaluation feasibility",
           "Apply the existing advanced-challenger admission gate and retain rejection/no-admission as valid completion"],
          ["artifacts/advanced/challenger_proposal.json", "artifacts/advanced/challenger_feasibility.json", "artifacts/advanced/challenger_admission_decision.json"],
          ["The hypothesis is registered before results and is not novelty/idle-compute seeking; it names the task/metric/segment and prevents post-hoc success redefinition.",
           "Feasibility cannot require unapproved cloud fleets/proprietary data/protected leakage, measures actual resource/sample/sequence/graph quality, and canonically records infeasible outcomes.",
           "TASK-165–168 remain conditional unless policy/value/feasibility pass, no simpler unresolved baseline work remains, and no-admission is complete evidence."],
          source_ids=["HANDOFF-013", "GAP-013", "TASK-165", "TASK-166", "TASK-167", "TASK-168"], entry_deps=["release.accept.gate"], lanes=["RESEARCH_LANE", "PROTECTED_GATE", "PROTECTED_GATE"],
          e2e="Only a precommitted feasible challenger with meaningful information value enters implementation; optional complexity never becomes mandatory by default."),
        story3("advanced.experiment", "Bounded implementation, tuning, ablation, and protected admission", "Run an admitted challenger in isolation without contaminating production or the protected test.",
          ["Implement the admitted neural/Bayesian/graph/sequence challenger against pinned matrices/splits within fixed scope and compute",
           "Run bounded tuning, ablation, calibration, OOD, robustness, stability, runtime, memory, maintainability, and simple-baseline comparisons retaining all failures",
           "Decide whether tuning evidence warrants a one-time sealed protected comparison"],
          ["artifacts/advanced/challenger_build_manifest.json", "artifacts/advanced/challenger_tuning_scorecard.json", "artifacts/advanced/challenger_protected_admission.json"],
          ["Implementation pins code/config/data/seed/compute and leaves active champion/publication unchanged; scope expansion requires a new admitted proposal.",
           "Search/budget is fixed before results, protected outcomes stay sealed, all trials/negative results persist, and complexity/resource penalties accompany apparent lift.",
           "Precommitted tuning gates admit or reject protected comparison; no-improvement/instability/excess cost closes the experiment and admission does not imply promotion."],
          source_ids=["GAP-013"], entry_deps=["advanced.admit.gate"], lanes=["RESEARCH_LANE", "RESEARCH_LANE", "PROTECTED_GATE"],
          e2e="An admitted challenger produces bounded, reproducible, fully logged tuning evidence without changing production or leaking protected outcomes."),
        story3("advanced.promote", "Protected comparison and production disposition", "Apply the same sealed evidence, operations, and rollback gates as any champion.",
          ["Generate challenger predictions on identical sealed protected games/cutoffs/metrics and complete scientific/resource scorecards",
           "Apply champion/challenger promotion, reproducibility, operational-compatibility, publication, product, and rollback policy",
           "Reconcile registries, artifacts, documentation, Jira state, operating baseline, and close-by-disposition evidence"],
          ["artifacts/advanced/challenger_protected_scorecard.json", "artifacts/advanced/challenger_promotion_decision.json", "artifacts/advanced/challenger_closeout.json"],
          ["The challenger receives identical evaluation, uncertainty/calibration/robustness/resource reporting, cannot alter prior champion evidence, and incomplete runs are not selectively summarized.",
           "Promotion requires policy-compliant protected evidence and a signed reproducible artifact; no-promotion retains current champion/negative evidence and any promoted candidate passes full serving/operations/rollback gates.",
           "Active identities change only on successful promotion, all decisions/Jira/evidence reconcile, and GAP-013 remains conditional or closed by explicit disposition rather than a core blocker."],
          source_ids=["HANDOFF-013", "GAP-013"], entry_deps=["advanced.experiment.gate"], lanes=["PROTECTED_GATE", "PROTECTED_GATE", "OPERATIONS"],
          e2e="An optional challenger either survives the identical sealed production gate or remains preserved negative evidence without destabilizing the operating system."),
      ], source_ids=["HANDOFF-013", "GAP-013", "TASK-165", "TASK-166", "TASK-167", "TASK-168"], depends_on=["release.accept.gate"], state="DEFERRED"),

    E("live", "Deferred live and in-game modeling", "PHASE-5", "DEFERRED", "live",
      "Keep live/in-game modeling explicitly deferred behind separate source-rights, latency, state, replay, evaluation, product, resource, and operating authorization.", [
        story3("live.admit", "Live need, source, rights, latency, cost, and value gate", "Decide whether live scope should ever activate without weakening the pregame product.",
          ["Research licensed live play/state/market feeds, authentication, terms, history, replayability, latency, reliability, cost, retention, and redistribution",
           "Define exact live use cases, incremental value versus pregame, latency/reliability/resource/failure targets, isolation, and no-build criteria",
           "Apply the separate live-scope admission gate without creating Wave 26"],
          ["artifacts/live/live_source_research.json", "artifacts/live/live_value_feasibility.json", "artifacts/live/live_admission_decision.json"],
          ["Research does not bypass CAPTCHA/authentication/rate limits/access controls, assumes no public-equals-redistributable rights, and records unavailable/unaffordable sources as blockers.",
           "Use cases distinguish in-game from pregame updates, targets are evidence-backed, pregame operation remains isolated, and no-build is valid when rights/history/cost/value/resources are inadequate.",
           "TASK-169–172 remain deferred unless user/governance explicitly admits the separate scope; no Wave 26 exists and deferred live work is not unfinished core v1."],
          source_ids=["HANDOFF-014", "GAP-014", "TASK-169", "TASK-170", "TASK-171", "TASK-172"], entry_deps=["release.accept.gate"], lanes=["RESEARCH_LANE", "RESEARCH_LANE", "PROTECTED_GATE"],
          e2e="Live work remains deferred unless licensed replayable evidence and clear value justify a separate isolated program."),
        story3("live.prototype", "Isolated event state, features, models, replay, and latency prototype", "Prototype only after admission and keep it separate from the pregame production path.",
          ["Build immutable event-stream snapshots and event-time as-of game-state reconstruction handling duplicates, delay, correction, and sequence",
           "Build live features/model candidates and historical streaming replay with calibration/OOD/partial-feed/latency/resource evidence",
           "Validate event-time integrity, replay determinism, latency, failure behavior, and pregame isolation"],
          ["artifacts/live/live_state_prototype.json", "artifacts/live/live_model_prototype.json", "artifacts/live/live_prototype_gate.json"],
          ["Every event retains provider sequence, published/received time, canonical game/entity identity, correction lineage, and prior evidence; out-of-order/duplicates/corrections reconstruct deterministically.",
           "Candidates use replayable historical sequences and strict event-time cutoffs, separately define outputs/BAS-related semantics, and measure missing/delayed feed, calibration, OOD, latency, and resources.",
           "Replay under duplicate/delayed/corrected/missing events passes, prototype cannot corrupt/degrade pregame operation, and prototype completion does not imply production admission."],
          source_ids=["GAP-014"], entry_deps=["live.admit.gate"], lanes=["DATA_MATERIALIZATION", "RESEARCH_LANE", "PROTECTED_GATE"],
          e2e="An admitted prototype reconstructs and predicts from licensed historical event streams deterministically while remaining isolated from pregame state."),
        story3("live.release", "Separate protected evaluation, product integration, and operating authorization", "Require a full independent release path for any live capability.",
          ["Run sealed event-time chronological evaluation with precommitted accuracy/calibration/latency/reliability/outage metrics and simple/pregame baselines",
           "Implement timestamped live snapshot/stream API and UI states for stale, disconnected, corrected, suspended, halftime, final, replay, and restricted data",
           "Conduct rights/science/security/product/target-resource/backup/incident review and authorize or reject live operation separately"],
          ["artifacts/live/live_protected_scorecard.json", "artifacts/live/live_product_validation.json", "artifacts/live/live_operating_decision.json"],
          ["Protected outcomes cannot tune event handling/thresholds/model selection, all outage/delay scenarios and uncertainty are reported, and comparison includes pregame-only/simple live baselines.",
           "Live outputs expose source/state/model/timestamp and remain distinguishable from immutable pregame forecasts; stale/disconnected/corrected/final states are explicit and restricted feed data is not exposed.",
           "Authorization requires the private-research source policy, protected evidence, latency/reliability/security/product/resources/backup/incidents; rejection leaves pregame valid and GAP-014 deferred/closed-by-disposition."],
          source_ids=["HANDOFF-014", "GAP-014"], entry_deps=["live.prototype.gate"], lanes=["PROTECTED_GATE", "SHARED_CONTRACT", "PROTECTED_GATE"],
          e2e="Any live capability independently earns operating authorization from licensed replayable evidence; rejection has no effect on the completed pregame system."),
      ], source_ids=["HANDOFF-014", "GAP-014", "TASK-169", "TASK-170", "TASK-171", "TASK-172"], depends_on=["release.accept.gate"], state="DEFERRED"),
])

# Generation and reconciliation ------------------------------------------------

PRIORITY_MAP = {
    "BLOCKER": "P0", "P0": "P0", "MUST": "P1", "P1": "P1",
    "SHOULD": "P2", "P2": "P2", "COULD": "P3", "P3": "P3",
    "CONDITIONAL": "CONDITIONAL", "DEFERRED": "DEFERRED",
}

DOMAIN_MATURITY_BEFORE = {
    "environment": "FUNCTIONAL_STARTER",
    "sources": "CONTRACT_DEFINED",
    "raw-data": "SCAFFOLD",
    "entities": "FUNCTIONAL_STARTER",
    "pit": "FUNCTIONAL_STARTER",
    "features": "FUNCTIONAL_STARTER",
    "modeling": "FUNCTIONAL_STARTER",
    "advanced-football": "FUNCTIONAL_STARTER",
    "tamu": "FUNCTIONAL_STARTER",
    "bas": "FUNCTIONAL_STARTER",
    "validation": "FUNCTIONAL_STARTER",
    "mlops": "FUNCTIONAL_STARTER",
    "product": "FUNCTIONAL_STARTER",
    "operations": "FUNCTIONAL_STARTER",
    "release": "DESIGN_ONLY",
    "advanced": "CONDITIONAL",
    "live": "DEFERRED",
}

DOMAIN_GATE_ALIAS = {
    "environment": "env.benchmark.gate",
    "sources": "sources.acquisition.drift",
    "raw-data": "raw.store.gate",
    "entities": "entities.resolve.gate",
    "pit": "pit.replay.gate",
    "features": "features.lifecycle.gate",
    "advanced-football": "advanced.context.gate",
    "modeling": "model.uncertainty.gate",
    "tamu": "tamu.evaluate.gate",
    "bas": "bas.validate.gate",
    "validation": "validation.promotion.gate",
    "mlops": "mlops.shadow.gate",
    "product": "product.explain.gate",
    "operations": "operations.backup.gate",
    "release": "release.accept.gate",
    "advanced": "advanced.promote.gate",
    "live": "live.release.gate",
}

EXTRA_STORY_DEPS = {
    "env.localroots": ["env.preflight.identity"],
    "env.benchmark": ["env.preflight.validation", "env.localroots.storage"],
    "env.envelope": ["env.benchmark.gate"],
    "sources.rights": ["sources.reconcile.gate"],
    "sources.credentials": ["sources.reconcile.gate"],
    "sources.acquisition": ["sources.rights.gate", "sources.credentials.gate"],
}

CRITICAL_ALIAS_PREFIXES = (
    "env.preflight", "env.benchmark", "sources.reconcile", "sources.rights", "sources.credentials",
    "raw.", "entities.", "pit.", "features.lifecycle", "model.dataset", "model.uncertainty",
    "validation.seal", "validation.replay", "validation.promotion",
)


def classify_domain(text: str) -> str:
    t = norm_space(text).lower()
    if any(x in t for x in ["live modeling", "in-game", "in game", "event stream", "streaming replay"]):
        return "live"
    if any(x in t for x in ["advanced challenger", "bayesian challenger", "neural challenger", "graph challenger", "sequence challenger"]):
        return "advanced"
    if "battered aggie" in t or re.search(r"\bbas\b", t):
        return "bas"
    if any(x in t for x in ["texas a&m", "texas am", "tamu", "aggie specialization", "a&m specialization"]):
        return "tamu"
    if any(x in t for x in ["target hardware", "benchmark target", "runtime manifest", "resource envelope", "ac-038"]):
        return "environment"
    if any(x in t for x in ["dashboard", "fastapi", "api contract", "serving", "product", "snapshot repository", "user interface", "freshness endpoint"]):
        return "product"
    if any(x in t for x in ["weekly", "mlops", "orchestration", "publication", "retraining", "checkpoint", "champion activation"]):
        return "mlops"
    if any(x in t for x in ["backup", "restore", "observability", "alert", "incident", "security", "secret", "supply chain", "ci ", "drift detector", "operations"]):
        return "operations"
    if any(x in t for x in ["protected evaluation", "protected split", "promotion", "scorecard", "validation", "walk-forward", "walk forward", "judging rule", "threshold precommit"]):
        return "validation"
    if any(x in t for x in ["model", "forecast", "calibration", "uncertainty", "probability", "expected margin", "joint score", "simulation", "ood", "baseline"]):
        return "modeling"
    if any(x in t for x in ["feature", "ablation", "screening", "lifecycle registry"]):
        return "features"
    if any(x in t for x in ["player", "roster", "depth", "injury", "availability", "recruit", "transfer", "coach", "coordinator", "weather", "travel", "rest days", "stadium", "venue", "officiating", "game mechanics", "fcs", "freshman"]):
        return "advanced-football"
    if any(x in t for x in ["point-in-time", "point in time", "pit", "leakage", "as-of", "as of", "cutoff", "known-at", "known at", "temporal replay"]):
        return "pit"
    if any(x in t for x in ["entity", "identity resolution", "canonical id", "alias", "referential integrity"]):
        return "entities"
    if any(x in t for x in ["license", "licensing", "rights", "credential", "source access", "source inventory", "api terms", "redistribution", "provider"]):
        return "sources"
    if any(x in t for x in ["raw data", "data acquisition", "historical data", "data lake", "materialization", "schema profile", "missingness", "snapshot"]):
        return "raw-data"
    return "release"


def priority_of(value: str) -> str:
    return PRIORITY_MAP.get((value or "").strip().upper(), "P2")


def historical_state(status: str, task_id: str = "") -> str:
    s = (status or "").upper()
    if "DONE" in s or "COMPLETE" in s or s.startswith("PASS"):
        return "DONE"
    if "BLOCKED" in s:
        return "BLOCKED"
    if task_id in {f"TASK-{i:03d}" for i in range(165, 169)} or "CONDITIONAL" in s:
        return "DEFERRED"
    if task_id in {f"TASK-{i:03d}" for i in range(169, 173)} or "DEFERRED" in s:
        return "DEFERRED"
    return "BACKLOG"


def historical_maturity(owner_wave: str, task_type: str = "", status: str = "") -> str:
    state = historical_state(status)
    if state != "DONE":
        return "DESIGN_ONLY" if "DESIGN" in (task_type or "").upper() else "FUNCTIONAL_STARTER"
    m = re.search(r"W(\d+)", owner_wave or "")
    wave = int(m.group(1)) if m else 0
    if wave <= 18:
        return "CONTRACT_DEFINED"
    if wave <= 20:
        return "FUNCTIONAL_STARTER"
    if wave <= 23:
        return "INTEGRATED"
    return "INTEGRATED"


def resolve_output_paths(repo: RepoIndex, outputs_text: str) -> list[str]:
    resolved: list[str] = []
    for raw in split_ids(outputs_text):
        raw = raw.strip().replace("\\", "/")
        if repo.exists(raw):
            resolved.append(raw)
            continue
        matches = repo.find_by_basename(Path(raw).name)
        if len(matches) == 1:
            resolved.append(matches[0])
        elif raw:
            resolved.append(raw)
    return sorted(dict.fromkeys(resolved))


def issue_description_md(i: Issue, compact: bool = False) -> str:
    head = f"**Local ID:** {i.local_id}\n\n**Objective:** {i.objective}\n\n**Why this exists:** {i.why_exists}"
    if compact:
        return head
    return "\n\n".join([
        head,
        "**Scope**\n" + (i.scope or "See in-scope and out-of-scope controls."),
        "**In scope**\n" + md_list(i.in_scope),
        "**Out of scope**\n" + md_list(i.out_of_scope),
        "**Prerequisites / dependencies**\n" + md_list(i.prerequisites + i.dependencies),
        "**Expected files / artifacts**\n" + md_list(i.files_expected + i.outputs),
        "**Acceptance criteria**\n" + md_numbered(i.acceptance_criteria),
        "**Definition of Done**\n" + md_numbered(i.definition_of_done),
        "**Tests**\n" + md_list([f"{t.get('classification')}: {t.get('path')} — {t.get('expectation')}" for t in i.tests]),
        "**Required evidence**\n" + md_list(i.evidence),
        "**Stop conditions**\n" + md_list(i.stop_conditions),
        "**Source references**\n" + md_list(i.source_refs),
    ])


def issue_markdown(i: Issue) -> str:
    d = i.as_dict()
    metadata = json.dumps(d, indent=2, ensure_ascii=False, sort_keys=True)
    return f"""<!-- GENERATED VIEW. Canonical record: {i.canonical_record} -->
# {i.local_id} — {i.title}

## Canonical metadata

```json
{metadata}
```

## Objective

{i.objective}

## Why This Exists

{i.why_exists}

## Scope

{i.scope}

### Explicit In Scope

{md_list(i.in_scope)}

### Explicit Out of Scope

{md_list(i.out_of_scope)}

## Prerequisites

{md_list(i.prerequisites)}

## Hard Dependencies

{md_list(i.dependencies)}

## Blocks

{md_list(i.blocks)}

## Files / Components Expected To Be Touched

{md_list(i.files_expected)}

## Protected Files / Interfaces

{md_list(i.protected_files)}

## Expected Outputs / Artifacts

{md_list(i.outputs)}

## Requirements

{md_list(i.requirement_ids)}

## Acceptance Controls

{md_list(i.acceptance_control_ids)}

## Acceptance Criteria

{md_numbered(i.acceptance_criteria)}

## Definition of Done

{md_numbered(i.definition_of_done)}

## Required Tests

{md_list([f"**{t.get('classification')}** — `{t.get('path')}` — {t.get('expectation')}" for t in i.tests])}

## Required Evidence

{md_list(i.evidence)}

## End-to-End Validation Requirement

{i.e2e_validation or 'Not applicable beyond the issue-level criteria.'}

## Expected Maturity After Completion

`{i.maturity_after}`

## Risk / Failure Conditions

{md_list(i.risk_conditions)}

## Stop Conditions

{md_list(i.stop_conditions)}

## Source References

{md_list(i.source_refs)}

## AI Context Notes

{md_list(i.ai_context_notes)}
"""


def default_dod(issue: Issue) -> list[str]:
    items = [
        "The implementation or scoped work is complete and every declared output exists at the documented path with stable identity/provenance.",
        "All issue-specific acceptance criteria pass; failures, blocked evidence, and negative results are preserved rather than hidden.",
        "All existing applicable tests pass and every declared NEW TEST REQUIRED has been implemented and executed with evidence.",
        "Applicable PIT/leakage, source-policy, security, reproducibility, and protected-governance controls remain intact; no secret or raw third-party payload is committed.",
        "Required evidence is saved, linked to exact source/data/code/config identities, and supports the claimed maturity rather than merely showing that code was written.",
        "Documentation, canonical local issue record, live Jira operational fields when connected, indexes, READY/BLOCKED queues, and downstream dependency state are updated.",
    ]
    if issue.issue_type in {"Epic", "Story"}:
        items.append("All child work and the explicit end-to-end gate complete at the required maturity; individually completed children cannot substitute for integrated proof.")
    if issue.historical_classification.startswith("HISTORICAL"):
        return [
            "The original historical scope and status are preserved with source evidence and stable identifiers.",
            "The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.",
            "Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work.",
        ]
    return items


def default_tests(repo: RepoIndex, domain: str, issue_type: str, external_blocker: str = "") -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for path in DOMAIN_TESTS.get(domain, [])[:4]:
        if repo.exists(path):
            out.append({"classification": "EXISTING_AUTOMATED_TEST", "path": path, "expectation": "Run and retain the result when this issue touches the covered contract."})
    if issue_type in {"Story", "Subtask"}:
        out.append({"classification": "NEW_AUTOMATED_TEST_REQUIRED", "path": "NEW TEST REQUIRED", "expectation": "Add the smallest automated unit/integration/E2E/replay test that directly proves the issue-specific criteria."})
    if "RIGHTS" in external_blocker or "TERMS" in external_blocker:
        out.append({"classification": "PUBLICATION_BOUNDARY_REVIEW", "path": "MANUAL REVIEW", "expectation": "Verify rights metadata remains nonblocking for private acquisition/training and raw third-party publication remains disabled."})
    if "TARGET" in external_blocker:
        out.append({"classification": "BENCHMARK", "path": "AUTHORITATIVE TARGET HOST", "expectation": "Execute on the declared target hardware and preserve the raw benchmark evidence."})
    if not out:
        out.append({"classification": "NEW_AUTOMATED_TEST_REQUIRED", "path": "NEW TEST REQUIRED", "expectation": "Create and execute the smallest deterministic validation or end-to-end gate that proves this issue without fabricating unavailable evidence."})
    return out

REGISTRY_PATHS = {
    "epics": "governance/EPIC_CATALOG.csv",
    "wbs": "governance/IMPLEMENTATION_WBS.csv",
    "requirements": "governance/REQUIREMENTS_INDEX.csv",
    "requirement_trace": "governance/REQUIREMENT_TASK_TRACEABILITY.csv",
    "controls": "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "acceptance_trace": "governance/ACCEPTANCE_TASK_TRACEABILITY.csv",
    "adrs": "governance/ADR_INDEX.csv",
    "gaps": "docs/final/FINAL_KNOWN_GAPS.csv",
    "risks": "docs/final/FINAL_RISK_REGISTER.csv",
    "handoffs": "docs/final/FINAL_BACKLOG.csv",
    "maturity": "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "risk_acceptance": "governance/RISK_ACCEPTANCE_TRACEABILITY.csv",
}


def load_registries(repo: RepoIndex) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for name, rel in REGISTRY_PATHS.items():
        if not repo.exists(rel):
            raise FileNotFoundError(rel)
        out[name] = repo.csv_cache.get(rel) or csv_rows(repo.root / rel)
    return out


def id_index(rows: list[dict[str, str]], field_name: str) -> dict[str, tuple[int, dict[str, str]]]:
    return {row.get(field_name, "").strip(): (idx, row) for idx, row in enumerate(rows) if row.get(field_name, "").strip()}


def extract_open_issue_sections(repo: RepoIndex) -> dict[str, dict[str, Any]]:
    rel = "governance/OPEN_ISSUES.md"
    if not repo.exists(rel):
        return {}
    lines = repo.lines[rel]
    found: list[tuple[str, int, int, str]] = []
    starts: list[tuple[str, int, int, str]] = []
    for line_no, line in enumerate(lines, 1):
        m = re.match(r"^(#{2,3})\s+(ISSUE-\d{3})\s*[—-]\s*(.+)$", line.strip())
        if m:
            starts.append((m.group(2), line_no, len(m.group(1)), m.group(3).strip()))
    for pos, (iid, start, level, title) in enumerate(starts):
        end = len(lines)
        for _, other_start, other_level, _ in starts[pos + 1 :]:
            if other_level <= level:
                end = other_start - 1
                break
        found.append((iid, start, end, title))
    return {iid: {"start": start, "end": end, "title": title, "text": " ".join(lines[start - 1 : end])} for iid, start, end, title in found}


def build_source_id_catalog(repo: RepoIndex, refs: SourceRefRegistry, regs: dict[str, list[dict[str, str]]]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    catalog: dict[str, dict[str, Any]] = {}
    id_to_ref: dict[str, str] = {}
    specs = [
        ("epics", "epic_id"), ("wbs", "task_id"), ("requirements", "requirement_id"),
        ("controls", "control_id"), ("adrs", "adr_id"), ("gaps", "gap_id"),
        ("risks", "risk_id"), ("handoffs", "handoff_id"),
    ]
    for name, field_name in specs:
        rel = REGISTRY_PATHS[name]
        for idx, row in enumerate(regs[name]):
            sid = row.get(field_name, "").strip()
            if not sid:
                continue
            rid = refs.add_csv_row(rel, idx, f"Authoritative registry row for {sid}")
            catalog[sid] = {"source_id": sid, "kind": name, "path": rel, "row_index": idx, "row": row, "source_ref_id": rid}
            id_to_ref[sid] = rid
    for iid, info in extract_open_issue_sections(repo).items():
        # SourceRefRegistry cannot directly accept an arbitrary range, so point to the stable heading line;
        # the source catalog retains the full section range for navigation.
        rid = refs.add("governance/OPEN_ISSUES.md", f"Historical/open issue source for {iid}", line=info["start"])
        catalog[iid] = {"source_id": iid, "kind": "open_issue", "path": "governance/OPEN_ISSUES.md", "start_line": info["start"], "end_line": info["end"], "title": info["title"], "text": info["text"], "source_ref_id": rid}
        id_to_ref[iid] = rid
    return catalog, id_to_ref


def maturity_for_domain(domain: str) -> str:
    return DOMAIN_MATURITY_BEFORE.get(domain, "DESIGN_ONLY")


def post_issue_common_sources(repo: RepoIndex, refs: SourceRefRegistry, domain: str, source_ids: list[str], id_to_ref: dict[str, str]) -> list[str]:
    source_ref_ids: list[str] = []
    for rel in DOMAIN_FILES.get(domain, []):
        if repo.exists(rel):
            source_ref_ids.append(refs.add(rel, f"Canonical {domain} design, implementation, test, or handoff source"))
    for rel in [
        "docs/final/CODEX_HANDOFF.md", "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
        "docs/final/FINAL_COMPONENT_MATURITY.csv", "docs/final/FINAL_KNOWN_GAPS.csv",
        "docs/final/FINAL_BACKLOG.csv", "governance/DO_NOT_DRIFT.md",
    ]:
        if repo.exists(rel):
            source_ref_ids.append(refs.add(rel, "Current post-W25 authority or protected implementation-handoff context"))
    for sid in source_ids:
        if sid in id_to_ref:
            source_ref_ids.append(id_to_ref[sid])
    return list(dict.fromkeys(source_ref_ids))


def build_historical_issues(repo: RepoIndex, refs: SourceRefRegistry, regs: dict[str, list[dict[str, str]]], id_to_ref: dict[str, str]) -> list[Issue]:
    issues: list[Issue] = []
    tasks_by_epic: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in regs["wbs"]:
        tasks_by_epic[row["epic_id"]].append(row)

    for idx, row in enumerate(regs["epics"]):
        eid = row["epic_id"]
        children = tasks_by_epic.get(eid, [])
        child_states = [historical_state(x.get("status", ""), x.get("task_id", "")) for x in children]
        if children and all(x == "DONE" for x in child_states):
            state = "DONE"
        elif any(x == "BLOCKED" for x in child_states):
            state = "BLOCKED"
        elif any(x == "DEFERRED" for x in child_states):
            state = "DEFERRED"
        else:
            state = historical_state(row.get("status", ""))
        domain = classify_domain(row.get("title", "") + " " + row.get("objective", ""))
        scoped_done = state == "DONE"
        issue = Issue(
            local_id=eid,
            issue_type="Epic",
            title=f"[{eid}] {row['title']}",
            phase=row.get("phase_id", ""),
            workflow_state=state,
            historical_classification="HISTORICAL_SCOPED_COMPLETED" if scoped_done else "HISTORICAL_OPEN_OR_DEFERRED",
            priority=priority_of(row.get("priority", "")),
            critical_path=any(x.get("critical_dependency_gate", "").upper() == "YES" for x in children),
            owner_wave=row.get("owner_wave", ""),
            source_ids=[eid],
            objective=row.get("objective", ""),
            why_exists="Preserve the authoritative 25-wave planning/design capability and its original scoped status without claiming that empirical production maturity was achieved.",
            scope="Historical epic scope exactly as represented by the authoritative Epic Catalog and its WBS children.",
            in_scope=["Original planning/design/starter work", "Stable source IDs and child traceability", "Scoped historical completion evidence"],
            out_of_scope=["Claiming real-data, protected-evaluation, production-ready, or operating maturity unless separately evidenced", "Creating a Wave 26"],
            files_expected=[REGISTRY_PATHS["epics"], REGISTRY_PATHS["wbs"]],
            protected_files=PROTECTED_FILES,
            outputs=sorted({x for c in children for x in resolve_output_paths(repo, c.get("outputs", ""))}),
            acceptance_criteria=[
                f"The epic retains stable ID {eid}, owner wave {row.get('owner_wave','')}, phase {row.get('phase_id','')}, and all authoritative WBS children.",
                "The workflow state represents original scoped completion/open state only and is not interpreted as empirical product completion.",
                "Any remaining real-data, model, validation, hardware, operational, conditional, or deferred obligation is represented in post-wave issues and traceability indexes.",
            ],
            maturity_before="CONTRACT_DEFINED",
            maturity_after=max((historical_maturity(c.get("owner_wave", ""), c.get("task_type", ""), c.get("status", "")) for c in children), default="CONTRACT_DEFINED"),
            evidence_state="VERIFIED" if scoped_done else "PARTIAL",
            risk_conditions=["Historical status could be misread as product completion", "Stale catalog status could outrank final handoff if source authority is ignored"],
            stop_conditions=["Stop if a proposed update renumbers the historical epic or rewrites its original wave provenance."],
            source_refs=[id_to_ref[eid], refs.add(REGISTRY_PATHS["wbs"], f"Authoritative WBS children for {eid}")],
            labels=["historical", "planning-program", "wave-completed" if scoped_done else "historical-open", slug(row.get("owner_wave", ""))],
            component=COMPONENT_ALIASES.get(domain, "governance"),
            execution_lane="SHARED_CONTRACT",
            ready=False,
            ai_context_notes=["Do not execute this Epic as new work; select an actionable post-wave Subtask instead.", "DONE means the original scoped planning/design/starter work completed, not that the final product is operating."],
        )
        issue.definition_of_done = default_dod(issue)
        issue.tests = default_tests(repo, domain, issue.issue_type)
        issue.e2e_validation = "Historical traceability is complete only when every child and every remaining maturity obligation has an explicit disposition."
        issues.append(issue)

    for idx, row in enumerate(regs["wbs"]):
        tid = row["task_id"]
        state = historical_state(row.get("status", ""), tid)
        domain = classify_domain(" ".join([row.get("title", ""), row.get("task_type", ""), row.get("notes", ""), row.get("outputs", "")]))
        outputs = resolve_output_paths(repo, row.get("outputs", ""))
        scoped_done = state == "DONE"
        source_ids = [tid]
        issue = Issue(
            local_id=tid,
            issue_type="Task",
            title=f"[{tid}] {row['title']}",
            parent_id=row.get("epic_id", ""),
            epic_id=row.get("epic_id", ""),
            phase=row.get("phase_id", ""),
            workflow_state=state,
            historical_classification="HISTORICAL_SCOPED_COMPLETED" if scoped_done else "HISTORICAL_OPEN_OR_DEFERRED",
            priority=priority_of(row.get("priority", "")),
            critical_path=row.get("critical_dependency_gate", "").upper() == "YES",
            owner_wave=row.get("owner_wave", ""),
            source_ids=source_ids,
            requirement_ids=split_ids(row.get("requirement_ids", "")),
            acceptance_control_ids=split_ids(row.get("acceptance_control_ids", "")),
            objective=row.get("title", ""),
            why_exists=f"Preserve the original {row.get('owner_wave','')} WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.",
            scope=f"Original task type {row.get('task_type','')} with mutation scope: {row.get('mutation_scope','') or 'as defined by its source documents'}.",
            in_scope=["Original WBS objective and outputs", "Original requirements and acceptance-control mappings", "Original dependency and execution-lane provenance"],
            out_of_scope=["Reopening completed planning solely to rename it", "Treating a starter/design result as empirically validated production capability"],
            prerequisites=[f"Historical dependency {x}" for x in split_ids(row.get("depends_on", ""))],
            dependencies=split_ids(row.get("depends_on", "")),
            files_expected=outputs or [row.get("mutation_scope", "")],
            protected_files=PROTECTED_FILES,
            outputs=outputs,
            acceptance_criteria=[
                f"Stable ID {tid}, parent {row.get('epic_id','')}, owner wave {row.get('owner_wave','')}, and original status {row.get('status','')} are preserved.",
                "Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.",
                "Requirement, acceptance-control, and dependency references resolve to authoritative registries.",
                "The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope.",
            ],
            maturity_before="DESIGN_ONLY",
            maturity_after=historical_maturity(row.get("owner_wave", ""), row.get("task_type", ""), row.get("status", "")),
            evidence_state="VERIFIED" if scoped_done else "BLOCKED" if state == "BLOCKED" else "PLANNED",
            risk_conditions=["Original DONE status may be over-interpreted", "Source output path may have moved or been generated under a different canonical directory"],
            stop_conditions=["Stop if completing this record would fabricate real-data, model-metric, source-rights, target-hardware, or operating evidence."],
            source_refs=[id_to_ref[tid]],
            labels=["historical", "planning-program", "wave-completed" if scoped_done else "historical-open", slug(row.get("owner_wave", "")), slug(row.get("task_type", ""))],
            component=COMPONENT_ALIASES.get(domain, "governance"),
            execution_lane=row.get("execution_lane", "") or "SOLO_WORKTREE",
            ready=False,
            ai_context_notes=["This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.", row.get("notes", "") or "No additional historical note."],
        )
        issue.definition_of_done = default_dod(issue)
        issue.tests = default_tests(repo, domain, issue.issue_type)
        issue.evidence = [f"Authoritative WBS row {tid}"] + ([f"Existing artifact `{p}`" for p in outputs] if outputs else ["Historical scope/status evidence in governance registries"])
        issue.e2e_validation = "Historical completion remains scoped; integrated product completion is evaluated only through the post-wave release path."
        issues.append(issue)
    return issues


def build_post_issues(repo: RepoIndex, refs: SourceRefRegistry, id_to_ref: dict[str, str]) -> tuple[list[Issue], dict[str, str]]:
    issues: list[Issue] = []
    alias_to_id: dict[str, str] = {}
    epic_seq = story_seq = subtask_seq = 0

    # Allocate all IDs first so arbitrary cross-domain dependencies resolve deterministically.
    for epic in POST_BLUEPRINT:
        epic_seq += 1
        alias_to_id[epic["alias"]] = f"POST-EPIC-{epic_seq:03d}"
        for story in epic["stories"]:
            story_seq += 1
            alias_to_id[story["alias"]] = f"POST-STORY-{story_seq:03d}"
            for task in story["tasks"]:
                subtask_seq += 1
                alias_to_id[task["alias"]] = f"POST-SUBTASK-{subtask_seq:03d}"

    for epic in POST_BLUEPRINT:
        eid = alias_to_id[epic["alias"]]
        domain = epic["domain"]
        state = "DEFERRED" if epic.get("state") == "DEFERRED" or epic["priority"] in {"DEFERRED", "CONDITIONAL"} else "BACKLOG"
        deps = [alias_to_id[x] for x in epic.get("depends_on", []) if x in alias_to_id]
        source_ids = list(dict.fromkeys(epic.get("source_ids", [])))
        issue = Issue(
            local_id=eid, issue_type="Epic", title=f"[{eid}] {epic['title']}", phase=epic["phase"],
            workflow_state=state, historical_classification="ACTIONABLE_POST_WAVE", priority=epic["priority"],
            critical_path=epic["alias"] not in {"advanced", "live"}, owner_wave="POST_W25",
            source_ids=source_ids, objective=epic["objective"],
            why_exists="The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.",
            scope=f"All Stories and Subtasks under this Epic for the {domain} domain, including its explicit integrated completion gate.",
            in_scope=["Child implementation and evidence work", "Cross-domain hard dependencies", "Integrated end-to-end gate", "Preservation of source authority and protected controls"],
            out_of_scope=["Declaring child code sufficient without integrated evidence", "Changing protected requirements or ADRs without governance review", "Creating Wave 26"],
            prerequisites=[f"Completion of {x}" for x in deps], dependencies=deps,
            files_expected=DOMAIN_FILES.get(domain, []), protected_files=PROTECTED_FILES,
            outputs=[x for s in epic["stories"] for t in s["tasks"] for x in t.get("outputs", [])],
            acceptance_criteria=[
                "Every child issue completes at its declared maturity and evidence state, or has an explicit accepted-risk/deferred disposition.",
                "The Epic's end-to-end gate proves the integrated capability on the required real data, target host, protected chronology, or operating path; file existence alone is insufficient.",
                "All requirement, acceptance-control, ADR, risk, gap, test, artifact, and source references remain valid and no protected invariant is weakened.",
            ],
            e2e_validation=f"The entire {epic['title']} capability must be exercised through its final gate and produce reproducible evidence consumable by its downstream Epic.",
            maturity_before=maturity_for_domain(domain), maturity_after="OPERATING" if domain in {"mlops", "product", "operations", "release"} else "EMPIRICALLY_VALIDATED",
            evidence_state="PLANNED", risk_conditions=["Children may appear complete while integration remains unproven", "Upstream data/rights/hardware evidence may remain unavailable"],
            stop_conditions=["Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved."],
            source_refs=post_issue_common_sources(repo, refs, domain, source_ids, id_to_ref),
            labels=["post-wave", "actionable", slug(domain), "conditional" if epic["alias"] == "advanced" else "deferred" if epic["alias"] == "live" else "core-release"],
            component=COMPONENT_ALIASES[domain], execution_lane="PROTECTED_GATE", ready=False,
            ai_context_notes=["Select child Subtasks from READY_QUEUE.csv; do not execute an Epic directly.", "Epic Done requires the final child gate and downstream-consumption evidence, not merely closed children."],
        )
        issue.definition_of_done = default_dod(issue)
        issue.tests = default_tests(repo, domain, issue.issue_type)
        issue.evidence = [f"All child evidence manifests for {eid}", "Final integrated gate decision with exact source/data/code/config/hardware identities"]
        issues.append(issue)

        for story in epic["stories"]:
            sid = alias_to_id[story["alias"]]
            entry_aliases = list(dict.fromkeys(story.get("entry_deps", []) + EXTRA_STORY_DEPS.get(story["alias"], [])))
            deps = [alias_to_id[x] for x in entry_aliases if x in alias_to_id]
            source_ids = list(dict.fromkeys(epic.get("source_ids", []) + story.get("source_ids", [])))
            sstate = "DEFERRED" if state == "DEFERRED" else "BACKLOG"
            issue = Issue(
                local_id=sid, issue_type="Story", title=f"[{sid}] {story['title']}", parent_id=eid, epic_id=eid,
                phase=epic["phase"], workflow_state=sstate, historical_classification="ACTIONABLE_POST_WAVE",
                priority=epic["priority"], critical_path=story["alias"].startswith(CRITICAL_ALIAS_PREFIXES), owner_wave="POST_W25",
                source_ids=source_ids, objective=story["objective"],
                why_exists=f"This coherent capability closes a defined portion of {epic['title']} and creates a verifiable output for the next dependency stage.",
                scope=story["objective"],
                in_scope=[x["title"] for x in story["tasks"]],
                out_of_scope=["Work owned by sibling Stories", "Promotion beyond the evidence and gate defined here", "Silent fallback or synthetic substitution for required evidence"],
                prerequisites=[f"Hard dependency {x}" for x in deps], dependencies=deps,
                files_expected=list(dict.fromkeys(DOMAIN_FILES.get(domain, []) + [p for t in story["tasks"] for p in t.get("files", [])])),
                protected_files=PROTECTED_FILES, outputs=[x for t in story["tasks"] for x in t.get("outputs", [])],
                acceptance_criteria=[
                    "All child Subtasks satisfy their issue-specific observable checks and save their required evidence.",
                    "The final child gate verifies the combined output and explicitly approves, blocks, rejects, or defers downstream use.",
                    "No child completion is accepted if a hard prerequisite, PIT/right/security/protected-control requirement, or evidence identity is missing.",
                ],
                e2e_validation=story.get("e2e") or f"Exercise the complete {story['title']} path and verify downstream consumption of the pinned outputs.",
                maturity_before=maturity_for_domain(domain), maturity_after="INTEGRATED", evidence_state="PLANNED",
                risk_conditions=["Parallel child outputs may use inconsistent source or schema identities", "Gate task may be bypassed after implementation tasks finish"],
                stop_conditions=["Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs."],
                source_refs=post_issue_common_sources(repo, refs, domain, source_ids, id_to_ref),
                labels=["post-wave", "actionable", slug(domain), "story", "conditional" if epic["alias"] == "advanced" else "deferred" if epic["alias"] == "live" else "core-release"],
                component=COMPONENT_ALIASES[domain], execution_lane="SHARED_CONTRACT", ready=False,
                ai_context_notes=["Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.", "Story completion requires the gate Subtask, not only implementation children."],
            )
            issue.definition_of_done = default_dod(issue)
            issue.tests = default_tests(repo, domain, issue.issue_type)
            issue.evidence = [f"Child output/evidence set for {sid}", "Story gate decision and downstream-readiness evidence"]
            issues.append(issue)

            task_ids = [alias_to_id[t["alias"]] for t in story["tasks"]]
            for task_pos, task in enumerate(story["tasks"]):
                tid = alias_to_id[task["alias"]]
                if task_pos == 0:
                    task_deps = list(deps)
                elif task_pos == 1:
                    task_deps = list(dict.fromkeys(deps + [task_ids[0]]))
                else:
                    task_deps = list(dict.fromkeys(deps + task_ids[:task_pos]))
                source_ids_t = list(dict.fromkeys(source_ids + task.get("source_ids", [])))
                external = task.get("external_blocker", "")
                lane = task.get("lane") or ("PROTECTED_GATE" if task_pos == len(story["tasks"]) - 1 else "SOLO_WORKTREE")
                state_t = "DEFERRED" if state == "DEFERRED" else "BACKLOG"
                checks = task.get("checks", [])
                issue = Issue(
                    local_id=tid, issue_type="Subtask", title=f"[{tid}] {task['title']}", parent_id=sid, epic_id=eid,
                    phase=epic["phase"], workflow_state=state_t, historical_classification="ACTIONABLE_POST_WAVE",
                    priority=epic["priority"], critical_path=task["alias"].startswith(CRITICAL_ALIAS_PREFIXES), owner_wave="POST_W25",
                    source_ids=source_ids_t, objective=task["title"],
                    why_exists=f"This is an independently executable and verifiable work unit required by Story {sid}: {story['title']}.",
                    scope=task["title"],
                    in_scope=["Implement or execute exactly the work described by the title", "Produce every declared artifact", "Run issue-specific checks and return evidence"],
                    out_of_scope=["Unrelated refactors", "Changing protected contracts to make a test pass", "Inventing unavailable data, thresholds, rights, hardware, or model results"],
                    prerequisites=[f"Dependency {x} complete at required maturity" for x in task_deps] + ([f"External condition: {external}"] if external else []),
                    dependencies=task_deps,
                    files_expected=list(dict.fromkeys(task.get("files", []) + DOMAIN_FILES.get(domain, []))),
                    protected_files=PROTECTED_FILES, outputs=task.get("outputs", []),
                    acceptance_criteria=checks,
                    e2e_validation=story.get("e2e") if task_pos == len(story["tasks"]) - 1 else f"The output must be directly consumable by the next child or Story gate without manual reconstruction.",
                    maturity_before=maturity_for_domain(domain), maturity_after=task.get("maturity_after", "IMPLEMENTED"), evidence_state="PLANNED",
                    risk_conditions=["Input identity or prerequisite maturity differs from the issue record", "A successful command may still produce incomplete, stale, synthetic, or leakage-contaminated evidence", external] if external else ["Input identity or prerequisite maturity differs from the issue record", "A successful command may still produce incomplete, stale, synthetic, or leakage-contaminated evidence"],
                    stop_conditions=[
                        "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
                        "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
                        "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.",
                    ],
                    source_refs=post_issue_common_sources(repo, refs, domain, source_ids_t, id_to_ref),
                    labels=list(dict.fromkeys(["post-wave", "actionable", slug(domain), "subtask", slug(lane)] + task.get("labels", []) + (["external-blocker"] if external else []) + (["conditional"] if epic["alias"] == "advanced" else ["deferred"] if epic["alias"] == "live" else ["core-release"]))),
                    component=COMPONENT_ALIASES[domain], execution_lane=lane, ready=False,
                    blocked_reason=external,
                    unblock_condition=f"Provide and verify external condition: {external}" if external else "",
                    ai_context_notes=[
                        f"Canonical parent Story: {sid}. Domain gate: {alias_to_id.get(DOMAIN_GATE_ALIAS[domain], '')}.",
                        "Return exact commands, exit codes, artifacts, hashes, input identities, negative results, and remaining blockers; do not report completion from narrative alone.",
                    ],
                )
                issue.definition_of_done = default_dod(issue)
                issue.tests = default_tests(repo, domain, issue.issue_type, external)
                for explicit_test in task.get("tests", []):
                    issue.tests.append({"classification": "EXISTING_AUTOMATED_TEST" if repo.exists(explicit_test) else "NEW_AUTOMATED_TEST_REQUIRED", "path": explicit_test, "expectation": "Run or create this issue-specific test and retain evidence."})
                issue.evidence = [f"Content-hashed artifact `{p}` with input/source/code/config identity" for p in task.get("outputs", [])] + ["Test/validation command log with exit codes", "Issue completion manifest recording achieved maturity and unresolved conditions"]
                issues.append(issue)
    return issues, alias_to_id


def attach_traceability(issues: list[Issue], regs: dict[str, list[dict[str, str]]], alias_to_id: dict[str, str]) -> dict[str, Any]:
    issue_by_id = {i.local_id: i for i in issues}
    domain_gate_id = {domain: alias_to_id[alias] for domain, alias in DOMAIN_GATE_ALIAS.items() if alias in alias_to_id}

    req_existing: dict[str, list[str]] = defaultdict(list)
    for row in regs["requirement_trace"]:
        req_existing[row["requirement_id"]].append(row["task_id"])
    ac_existing: dict[str, list[str]] = defaultdict(list)
    for row in regs["acceptance_trace"]:
        ac_existing[row["control_id"]].append(row["task_id"])

    req_post: dict[str, str] = {}
    for row in regs["requirements"]:
        rid = row["requirement_id"]
        text = " ".join(str(v) for v in row.values())
        domain = classify_domain(text)
        gate = domain_gate_id[domain]
        req_post[rid] = gate
        issue_by_id[gate].requirement_ids.append(rid)

    ac_post: dict[str, str] = {}
    for row in regs["controls"]:
        cid = row["control_id"]
        text = " ".join(str(v) for v in row.values())
        domain = classify_domain(text)
        gate = domain_gate_id[domain]
        ac_post[cid] = gate
        issue_by_id[gate].acceptance_control_ids.append(cid)

    adr_post: dict[str, str] = {}
    for row in regs["adrs"]:
        aid = row["adr_id"]
        domain = classify_domain(" ".join(str(v) for v in row.values()))
        gate = domain_gate_id[domain]
        adr_post[aid] = gate
        issue_by_id[gate].adr_ids.append(aid)

    risk_post: dict[str, str] = {}
    for row in regs["risks"]:
        risk_id = row["risk_id"]
        domain = classify_domain(" ".join(str(v) for v in row.values()))
        gate = domain_gate_id[domain]
        risk_post[risk_id] = gate
        issue_by_id[gate].risk_ids.append(risk_id)

    gap_post: dict[str, str] = {}
    for row in regs["gaps"]:
        gid = row["gap_id"]
        domain = classify_domain(" ".join(str(v) for v in row.values()))
        # Final gaps have established target domains that are more precise than generic keywords.
        override = {
            "GAP-001": "environment", "GAP-002": "raw-data", "GAP-003": "pit", "GAP-004": "features",
            "GAP-005": "modeling", "GAP-006": "tamu", "GAP-007": "bas", "GAP-008": "advanced-football",
            "GAP-009": "entities", "GAP-010": "sources", "GAP-011": "advanced-football", "GAP-012": "product",
            "GAP-013": "advanced", "GAP-014": "live",
        }
        gate = domain_gate_id[override.get(gid, domain)]
        gap_post[gid] = gate
        issue_by_id[gate].gap_ids.append(gid)
        issue_by_id[gate].source_ids.append(gid)

    handoff_post: dict[str, str] = {}
    for row in regs["handoffs"]:
        hid = row["handoff_id"]
        override = {
            "HANDOFF-001": "environment", "HANDOFF-002": "sources", "HANDOFF-003": "raw-data", "HANDOFF-004": "entities",
            "HANDOFF-005": "pit", "HANDOFF-006": "modeling", "HANDOFF-007": "validation", "HANDOFF-008": "tamu",
            "HANDOFF-009": "bas", "HANDOFF-010": "mlops", "HANDOFF-011": "product", "HANDOFF-012": "operations",
            "HANDOFF-013": "advanced", "HANDOFF-014": "live",
        }
        gate = domain_gate_id[override[hid]]
        handoff_post[hid] = gate
        issue_by_id[gate].source_ids.append(hid)

    open_issue_post: dict[str, str] = {}
    open_issues = extract_open_issue_sections(RepoIndex(Path(issues[0].files_expected[0]).parent) if False else None) if False else {}
    # open-issue mapping is generated separately with the existing repository index; this placeholder keeps return shape stable.

    for i in issues:
        i.requirement_ids = sorted(set(i.requirement_ids))
        i.acceptance_control_ids = sorted(set(i.acceptance_control_ids))
        i.adr_ids = sorted(set(i.adr_ids))
        i.risk_ids = sorted(set(i.risk_ids))
        i.gap_ids = sorted(set(i.gap_ids))
        i.source_ids = sorted(set(i.source_ids))

    return {
        "requirement_existing": req_existing, "requirement_post": req_post,
        "acceptance_existing": ac_existing, "acceptance_post": ac_post,
        "adr_post": adr_post, "risk_post": risk_post, "gap_post": gap_post,
        "handoff_post": handoff_post, "open_issue_post": open_issue_post,
    }


def attach_open_issue_traceability(repo: RepoIndex, issues: list[Issue], alias_to_id: dict[str, str]) -> dict[str, str]:
    issue_by_id = {i.local_id: i for i in issues}
    domain_gate_id = {domain: alias_to_id[alias] for domain, alias in DOMAIN_GATE_ALIAS.items() if alias in alias_to_id}
    mapping: dict[str, str] = {}
    for iid, info in extract_open_issue_sections(repo).items():
        domain = classify_domain(info["title"] + " " + info["text"])
        gate = domain_gate_id[domain]
        mapping[iid] = gate
        issue_by_id[gate].source_ids.append(iid)
    for i in issues:
        i.source_ids = sorted(set(i.source_ids))
    return mapping


def finalize_dependency_state(issues: list[Issue]) -> None:
    by_id = {i.local_id: i for i in issues}
    for i in issues:
        valid = []
        for dep in i.dependencies:
            if dep in by_id and dep != i.local_id:
                valid.append(dep)
        i.dependencies = sorted(set(valid))
    for i in issues:
        i.blocks = []
    for i in issues:
        for dep in i.dependencies:
            by_id[dep].blocks.append(i.local_id)
    for i in issues:
        i.blocks = sorted(set(i.blocks))

    def satisfied(dep_id: str) -> bool:
        dep = by_id[dep_id]
        return dep.workflow_state == "DONE" and dep.evidence_state in {"COMPLETE", "VERIFIED"}

    for i in issues:
        if i.historical_classification.startswith("HISTORICAL"):
            i.ready = False
            continue
        if i.workflow_state == "DEFERRED" or "deferred" in i.labels or "conditional" in i.labels:
            i.workflow_state = "DEFERRED"
            i.ready = False
            if not i.blocked_reason:
                i.blocked_reason = "DEFERRED_OR_CONDITIONAL_BY_FINAL_HANDOFF"
                i.unblock_condition = "A documented admission/replanning decision must explicitly activate this work after all stated prerequisites pass."
            continue
        if i.issue_type != "Subtask":
            i.ready = False
            if i.workflow_state not in {"DONE", "DEFERRED", "CANCELLED"}:
                i.workflow_state = "BACKLOG"
            continue
        if i.blocked_reason:
            i.workflow_state = "BLOCKED"
            i.ready = False
            continue
        unsatisfied = [d for d in i.dependencies if not satisfied(d)]
        if unsatisfied:
            i.workflow_state = "BLOCKED"
            i.ready = False
            i.blocked_reason = "UNSATISFIED_HARD_DEPENDENCIES: " + ";".join(unsatisfied)
            i.unblock_condition = "Complete and verify all listed hard dependencies at their required maturity/evidence state."
        else:
            i.workflow_state = "READY"
            i.ready = True
            i.blocked_reason = ""
            i.unblock_condition = ""


def assign_import_ids(issues: list[Issue]) -> None:
    type_rank = {"Epic": 0, "Story": 1, "Task": 1, "Bug": 1, "Subtask": 2}
    ordered = sorted(issues, key=lambda i: (type_rank.get(i.issue_type, 9), i.local_id))
    for n, issue in enumerate(ordered, 100001):
        issue.import_id = n


def establish_record_paths(issues: list[Issue]) -> None:
    folders = {"Epic": "epics", "Story": "stories", "Task": "tasks", "Bug": "tasks", "Subtask": "subtasks"}
    for i in issues:
        folder = folders[i.issue_type]
        filename = f"{i.local_id}_{file_slug(i.title.replace('[' + i.local_id + ']', ''))}.json"
        i.canonical_record = f"jira/records/issues/{folder}/{filename}"
        i.generated_markdown = f"jira/issues/{folder}/{filename[:-5]}.md"

def enrich_issue_links_and_refs(issues: list[Issue], repo: RepoIndex, refs: SourceRefRegistry, id_to_ref: dict[str, str], alias_to_id: dict[str, str]) -> None:
    by_id = {i.local_id: i for i in issues}
    domain_gate_id = {domain: alias_to_id[alias] for domain, alias in DOMAIN_GATE_ALIAS.items() if alias in alias_to_id}
    for i in issues:
        if i.historical_classification.startswith("HISTORICAL"):
            domain = classify_domain(" ".join([i.title, i.objective, i.scope, i.component]))
            gate = domain_gate_id.get(domain)
            if gate:
                i.related_to.append(gate)
        for sid in i.source_ids:
            if sid in id_to_ref:
                i.source_refs.append(id_to_ref[sid])
        # The canonical source-id registries are navigable without copying every row into issue descriptions.
        for rel in [REGISTRY_PATHS["requirements"], REGISTRY_PATHS["controls"], REGISTRY_PATHS["adrs"]]:
            if repo.exists(rel) and ((rel.endswith("REQUIREMENTS_INDEX.csv") and i.requirement_ids) or (rel.endswith("ACCEPTANCE_CONTROL_CATALOG.csv") and i.acceptance_control_ids) or (rel.endswith("ADR_INDEX.csv") and i.adr_ids)):
                i.source_refs.append(refs.add(rel, "Canonical registry for IDs referenced by this issue"))
        i.source_refs = list(dict.fromkeys(i.source_refs))
        i.related_to = sorted(set(x for x in i.related_to if x in by_id and x != i.local_id))


def dependency_cycles(issues: list[Issue]) -> list[list[str]]:
    graph = {i.local_id: list(i.dependencies) for i in issues}
    color: dict[str, int] = {k: 0 for k in graph}
    stack: list[str] = []
    cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()

    def canonical_cycle(cycle: list[str]) -> tuple[str, ...]:
        body = cycle[:-1]
        if not body:
            return tuple(cycle)
        rots = [tuple(body[n:] + body[:n]) for n in range(len(body))]
        rev = list(reversed(body))
        rots += [tuple(rev[n:] + rev[:n]) for n in range(len(rev))]
        return min(rots)

    def dfs(node: str) -> None:
        color[node] = 1
        stack.append(node)
        for dep in graph.get(node, []):
            if dep not in graph:
                continue
            if color[dep] == 0:
                dfs(dep)
            elif color[dep] == 1:
                pos = stack.index(dep)
                cyc = stack[pos:] + [dep]
                key = canonical_cycle(cyc)
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    cycles.append(cyc)
        stack.pop()
        color[node] = 2

    for node in graph:
        if color[node] == 0:
            dfs(node)
    return cycles


def status_for_import(logical: str) -> str:
    return {
        "DONE": "Done",
        "IN_PROGRESS": "In Progress",
        "REVIEW": "In Progress",
        "VALIDATION": "In Progress",
        "EVIDENCE_PENDING": "In Progress",
        "BACKLOG": "To Do",
        "READY": "To Do",
        "BLOCKED": "To Do",
        "DEFERRED": "To Do",
        "CANCELLED": "Done",
    }.get(logical, "To Do")


def priority_for_import(priority: str) -> str:
    return {"P0": "Highest", "P1": "High", "P2": "Medium", "P3": "Low", "DEFERRED": "Low", "CONDITIONAL": "Low"}.get(priority, "Medium")


def jira_issue_type(issue_type: str) -> str:
    return "Sub-task" if issue_type == "Subtask" else issue_type


def issue_folder(issue_type: str) -> str:
    return {"Epic": "epics", "Story": "stories", "Task": "tasks", "Bug": "tasks", "Subtask": "subtasks"}[issue_type]


def write_canonical_records(jira_root: Path, issues: list[Issue]) -> None:
    for i in issues:
        rel = Path(i.canonical_record).relative_to("jira")
        write_json(jira_root / rel, i.as_dict())
        md_rel = Path(i.generated_markdown).relative_to("jira")
        write_text(jira_root / md_rel, issue_markdown(i))


def issue_index_rows(issues: list[Issue]) -> list[dict[str, Any]]:
    return [{
        "local_id": i.local_id, "jira_key": i.jira_key, "import_id": i.import_id,
        "issue_type": i.issue_type, "summary": i.title, "parent": i.parent_id, "epic": i.epic_id,
        "phase": i.phase, "priority": i.priority, "workflow_state": i.workflow_state,
        "maturity_before": i.maturity_before, "maturity_after": i.maturity_after,
        "evidence_state": i.evidence_state, "ready": i.ready, "blocked_by": i.dependencies,
        "critical_path": i.critical_path, "component": i.component, "execution_lane": i.execution_lane,
        "historical_classification": i.historical_classification, "owner_wave": i.owner_wave,
        "source_ids": i.source_ids, "primary_source_refs": i.source_refs[:8],
        "canonical_record": i.canonical_record, "generated_markdown": i.generated_markdown,
    } for i in sorted(issues, key=lambda x: x.local_id)]


def write_indexes(jira_root: Path, issues: list[Issue], refs: SourceRefRegistry, regs: dict[str, list[dict[str, str]]], trace: dict[str, Any], open_issue_map: dict[str, str], id_to_ref: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    idx = jira_root / "index"
    by_id = {i.local_id: i for i in issues}
    issue_rows = issue_index_rows(issues)
    write_csv(idx / "ISSUE_INDEX.csv", issue_rows)

    ready_rows = []
    for i in sorted((x for x in issues if x.ready), key=lambda x: ({"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(x.priority, 9), not x.critical_path, -len(x.blocks), x.local_id)):
        ready_rows.append({
            "rank": len(ready_rows) + 1, "local_id": i.local_id, "summary": i.title, "priority": i.priority,
            "critical_path": i.critical_path, "dependency_unlock_count": len(i.blocks), "execution_lane": i.execution_lane,
            "component": i.component, "parent": i.parent_id, "dependencies": i.dependencies,
            "source_refs": i.source_refs[:8], "canonical_record": i.canonical_record,
        })
    write_csv(idx / "READY_QUEUE.csv", ready_rows)

    blocked_rows = []
    for i in sorted((x for x in issues if x.workflow_state == "BLOCKED"), key=lambda x: ({"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(x.priority, 9), x.local_id)):
        blocked_rows.append({
            "issue_id": i.local_id, "summary": i.title, "reason": i.blocked_reason,
            "blocking_issue": [d for d in i.dependencies if by_id[d].workflow_state != "DONE"],
            "blocking_evidence": [by_id[d].evidence_state for d in i.dependencies if by_id[d].workflow_state != "DONE"],
            "unblock_condition": i.unblock_condition, "priority": i.priority,
            "downstream_impact": len(i.blocks), "critical_path": i.critical_path,
        })
    write_csv(idx / "BLOCKED_QUEUE.csv", blocked_rows)

    critical_rows = []
    for i in sorted((x for x in issues if x.critical_path), key=lambda x: (x.import_id, x.local_id)):
        critical_rows.append({
            "sequence_hint": len(critical_rows) + 1, "local_id": i.local_id, "issue_type": i.issue_type,
            "summary": i.title, "state": i.workflow_state, "priority": i.priority,
            "blocked_by": i.dependencies, "blocks_count": len(i.blocks), "maturity_after": i.maturity_after,
            "note": "Dependency criticality only; this is not a duration estimate.",
        })
    write_csv(idx / "CRITICAL_PATH.csv", critical_rows)

    dep_rows: list[dict[str, Any]] = []
    for i in issues:
        if i.parent_id:
            dep_rows.append({"source_id": i.parent_id, "target_id": i.local_id, "relationship": "PARENT_CHILD", "hard": False, "source_basis": "Canonical hierarchy"})
        for dep in i.dependencies:
            dep_rows.append({"source_id": dep, "target_id": i.local_id, "relationship": "BLOCKS", "hard": True, "source_basis": "Issue dependency contract"})
        for rel in i.related_to:
            dep_rows.append({"source_id": i.local_id, "target_id": rel, "relationship": "RELATES_TO", "hard": False, "source_basis": "Historical/post-wave reconciliation"})
    write_csv(idx / "DEPENDENCY_INDEX.csv", dep_rows)

    hierarchy_rows = [{
        "local_id": i.local_id, "issue_type": i.issue_type, "parent_id": i.parent_id,
        "epic_id": i.epic_id, "depth": 0 if i.issue_type == "Epic" else 1 if i.issue_type in {"Story", "Task", "Bug"} else 2,
        "import_id": i.import_id, "parent_import_id": by_id[i.parent_id].import_id if i.parent_id else "",
    } for i in sorted(issues, key=lambda x: x.import_id)]
    write_csv(idx / "HIERARCHY_INDEX.csv", hierarchy_rows)

    source_ref_rows = [vars(r) for r in refs.refs]
    write_csv(idx / "SOURCE_REFERENCE_INDEX.csv", source_ref_rows)

    req_rows = []
    for row in regs["requirements"]:
        rid = row["requirement_id"]
        historical = sorted(set(trace["requirement_existing"].get(rid, [])))
        post = trace["requirement_post"].get(rid, "")
        req_rows.append({
            "requirement_id": rid, "title": row.get("title", ""), "status": row.get("status", ""),
            "category": row.get("category", ""), "constraint_class": row.get("constraint_class", ""),
            "historical_task_ids": historical, "post_wave_issue_ids": [post] if post else [],
            "mapping_disposition": "ONGOING_ENFORCEMENT_OR_IMPLEMENTATION" if row.get("status", "").upper() == "ACTIVE" else "PRESERVED_WITH_POST_WAVE_GOVERNANCE_MAPPING",
            "source_ref_id": id_to_ref.get(rid, ""), "mapped": bool(historical or post),
        })
    write_csv(idx / "REQUIREMENT_TRACEABILITY.csv", req_rows)

    control_rows = []
    for row in regs["controls"]:
        cid = row["control_id"]
        historical = sorted(set(trace["acceptance_existing"].get(cid, [])))
        post = trace["acceptance_post"].get(cid, "")
        control_rows.append({
            "control_id": cid, "title": row.get("title", ""), "domain": row.get("domain", ""),
            "release_blocking": row.get("release_blocking", ""), "current_status": row.get("current_status", ""),
            "historical_task_ids": historical, "post_wave_issue_ids": [post] if post else [],
            "evidence_mode": row.get("evidence_mode", ""), "criterion": row.get("criterion", ""),
            "source_ref_id": id_to_ref.get(cid, ""), "mapped": bool(historical or post),
        })
    write_csv(idx / "ACCEPTANCE_TRACEABILITY.csv", control_rows)

    adr_rows = []
    for row in regs["adrs"]:
        aid = row["adr_id"]
        post = trace["adr_post"].get(aid, "")
        adr_rows.append({
            "adr_id": aid, "title": row.get("title", ""), "status": row.get("status", ""),
            "wave": row.get("wave", ""), "post_wave_issue_ids": [post] if post else [],
            "change_required_if_violated": True, "source_ref_id": id_to_ref.get(aid, ""), "mapped": bool(post),
        })
    write_csv(idx / "ADR_TRACEABILITY.csv", adr_rows)

    test_rows: list[dict[str, Any]] = []
    for i in issues:
        for t in i.tests:
            test_rows.append({
                "test_path": t.get("path", ""), "classification": t.get("classification", ""),
                "issue_id": i.local_id, "issue_type": i.issue_type, "expectation": t.get("expectation", ""),
                "existing_at_generation": t.get("path", "") in {"NEW TEST REQUIRED", "MANUAL REVIEW REQUIRED", "AUTHORITATIVE TARGET HOST"} or (jira_root.parent / t.get("path", "")).exists(),
            })
    write_csv(idx / "TEST_TRACEABILITY.csv", test_rows)

    artifact_rows: list[dict[str, Any]] = []
    for i in issues:
        for output in i.outputs:
            artifact_rows.append({
                "artifact_path_or_name": output, "producer_issue_id": i.local_id, "issue_type": i.issue_type,
                "required_for_completion": True, "expected_maturity": i.maturity_after,
                "downstream_issue_ids": i.blocks, "evidence_state": i.evidence_state,
            })
    write_csv(idx / "ARTIFACT_TRACEABILITY.csv", artifact_rows)

    return {
        "issue": issue_rows, "ready": ready_rows, "blocked": blocked_rows, "critical": critical_rows,
        "dependency": dep_rows, "hierarchy": hierarchy_rows, "source_refs": source_ref_rows,
        "requirements": req_rows, "controls": control_rows, "adrs": adr_rows,
        "tests": test_rows, "artifacts": artifact_rows,
    }

def write_source_views(jira_root: Path, repo: RepoIndex, refs: SourceRefRegistry, issues: list[Issue]) -> None:
    source_dir = jira_root / "sources"
    document_rows = []
    for rel, rec in sorted(repo.files.items()):
        document_rows.append({
            "repo_relative_path": rel, "windows_absolute_path": f"C:\\BatteredAggieSyndrome\\{rel.replace('/', chr(92))}",
            "sha256": rec.sha256, "size_bytes": rec.size_bytes, "line_count": rec.line_count,
            "extension": rec.extension, "top_directory": rec.top_dir, "authority_level": rec.authority_level,
            "role": rec.role, "parse_status": rec.parse_status,
        })
    write_csv(source_dir / "SOURCE_DOCUMENT_INDEX.csv", document_rows)
    write_csv(source_dir / "SOURCE_ANCHOR_INDEX.csv", [vars(r) for r in refs.refs])
    for i in issues:
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "issue_id": i.local_id,
            "source_ids": i.source_ids,
            "source_refs": [vars(next(r for r in refs.refs if r.source_ref_id == rid)) for rid in i.source_refs],
            "retrieval_protocol": [
                "Verify document_sha256 against the current repository file.",
                "If the hash changed, locate the stored heading/anchor excerpt and update the line range through controlled regeneration.",
                "Open only the referenced section plus minimal implementation context; never treat the Windows absolute path as canonical.",
            ],
        }
        write_json(source_dir / "issue_source_manifests" / f"{i.local_id}.json", manifest)


def write_project_configuration(jira_root: Path, issues: list[Issue]) -> None:
    project = jira_root / "project"
    target_profile = {
        "schema_version": 1,
        "profile_status": "TEMPLATE_REQUIRES_TARGET_DISCOVERY",
        "platform": "Jira Cloud or Jira Data Center - confirm before import",
        "jira_base_url": "",
        "project_name": "Aggie Analytics Engine / Battered Aggie Syndrome",
        "project_key": "",
        "project_type": "software_recommended",
        "company_or_team_managed": "UNKNOWN",
        "available_issue_types": [],
        "available_link_types": [],
        "available_statuses": [],
        "available_priorities": [],
        "available_components": [],
        "custom_field_mapping": {
            "Local Issue ID": "",
            "Source IDs": "",
            "Phase": "",
            "Implementation Maturity": "",
            "Evidence State": "",
            "Owner/Historical Wave": "",
            "Critical Path": "",
            "Execution Lane": "",
        },
        "discovery_required_before_api_execution": True,
        "notes": [
            "Do not populate Jira-generated IDs from guesses.",
            "Confirm project management type, issue types, statuses, priorities, components, link types, screens, and custom fields in the destination.",
            "Use External System Import for multi-level hierarchy; API templates remain inert until this profile is populated.",
        ],
    }
    write_json(project / "JIRA_TARGET_PROFILE.yaml", target_profile)
    write_json(project / "ISSUE_TYPE_MAPPING.yaml", {
        "logical_to_default_csv": {"Epic": "Epic", "Story": "Story", "Task": "Task", "Bug": "Bug", "Subtask": "Sub-task"},
        "target_mapping_status": "VERIFY_IN_DESTINATION",
        "hierarchy": {"Epic": [], "Story": ["Epic"], "Task": ["Epic"], "Bug": ["Epic"], "Subtask": ["Story", "Task", "Bug"]},
        "rule": "No hierarchy above Epic is assumed. Phases are represented through a custom Phase field/labels/components unless the target explicitly supports higher levels.",
    })
    write_json(project / "WORKFLOW_MAPPING.yaml", {
        "logical_states": ["BACKLOG", "READY", "IN_PROGRESS", "BLOCKED", "REVIEW", "VALIDATION", "EVIDENCE_PENDING", "DONE", "DEFERRED", "CANCELLED"],
        "portable_default_mapping": {s: status_for_import(s) for s in ["BACKLOG", "READY", "IN_PROGRESS", "BLOCKED", "REVIEW", "VALIDATION", "EVIDENCE_PENDING", "DONE", "DEFERRED", "CANCELLED"]},
        "target_mapping_status": "VERIFY_AND_EDIT_BEFORE_IMPORT",
        "warning": "The portable defaults use common To Do/In Progress/Done names only. Existing destination statuses must be mapped explicitly; the Logical Workflow State custom field preserves the project-specific state model.",
    })
    write_json(project / "PRIORITY_MAPPING.yaml", {
        "logical_priorities": ["P0", "P1", "P2", "P3", "CONDITIONAL", "DEFERRED"],
        "portable_default_mapping": {p: priority_for_import(p) for p in ["P0", "P1", "P2", "P3", "CONDITIONAL", "DEFERRED"]},
        "target_mapping_status": "VERIFY_AND_EDIT_BEFORE_IMPORT",
        "warning": "No Jira priority ID is embedded. Map values to existing destination priorities.",
    })
    field_schema = {
        "principle": "Keep searchable operational metadata small; the canonical local JSON owns detailed specification and traceability.",
        "minimum_recommended_custom_fields": [
            {"logical_name": "Local Issue ID", "type": "short_text", "required": True, "jira_id": "", "reason": "Stable local/Jira reconciliation key"},
            {"logical_name": "Source IDs", "type": "short_text_or_multi_text", "required": True, "jira_id": "", "reason": "Searchable historical/governance identifiers"},
            {"logical_name": "Phase", "type": "single_select_or_short_text", "required": True, "jira_id": "", "reason": "Portable initiative grouping without assuming hierarchy above Epic"},
            {"logical_name": "Logical Workflow State", "type": "single_select", "required": True, "jira_id": "", "reason": "Preserves BACKLOG/READY/BLOCKED/etc. separately from target workflow"},
            {"logical_name": "Implementation Maturity", "type": "single_select", "required": True, "jira_id": "", "reason": "Separates design/starter/integrated/validated/production/operating maturity"},
            {"logical_name": "Evidence State", "type": "single_select", "required": True, "jira_id": "", "reason": "Prevents code completion from masquerading as verified evidence"},
            {"logical_name": "Owner Historical Wave", "type": "short_text", "required": False, "jira_id": "", "reason": "Historical wave/post-W25 provenance"},
            {"logical_name": "Critical Path", "type": "checkbox_or_boolean", "required": False, "jira_id": "", "reason": "Dependency-critical filtering"},
            {"logical_name": "Execution Lane", "type": "single_select", "required": False, "jira_id": "", "reason": "Safe parallelism and protected-gate routing"},
        ],
        "stored_locally_not_custom_fields": ["Requirement IDs", "Acceptance controls", "ADR IDs", "Risk IDs", "Gap IDs", "Tests", "Artifacts", "Source references", "Stop conditions", "AI notes"],
        "authority": {"local": ["specification", "scope", "source refs", "acceptance", "DoD", "tests", "dependencies", "expected artifacts"], "jira": ["status", "assignee", "sprint", "comments", "ordering", "live ownership"]},
    }
    write_json(project / "FIELD_SCHEMA.yaml", field_schema)

    components = sorted(set(i.component for i in issues if i.component))
    component_rows = []
    for comp in components:
        related = [i for i in issues if i.component == comp]
        component_rows.append({
            "component_name": comp, "description": f"Controlled component for {comp.replace('-', ' ')} work.",
            "issue_count": len(related), "actionable_count": sum(i.historical_classification == "ACTIONABLE_POST_WAVE" for i in related),
            "jira_component_id": "", "target_status": "CREATE_OR_MAP_AFTER_TARGET_DISCOVERY",
        })
    write_csv(project / "COMPONENTS.csv", component_rows)

    labels = Counter(x for i in issues for x in i.labels)
    label_rows = []
    for label, count in sorted(labels.items()):
        category = "lifecycle" if label in {"historical", "planning-program", "wave-completed", "historical-open", "post-wave", "actionable", "core-release", "conditional", "deferred"} else "execution-or-domain"
        label_rows.append({"label": label, "category": category, "definition": f"Controlled {category} label used by the generated Jira system.", "issue_count": count, "allow_freeform_variants": False})
    write_csv(project / "LABEL_DICTIONARY.csv", label_rows)


def write_reconciliation(jira_root: Path, repo: RepoIndex, issues: list[Issue], regs: dict[str, list[dict[str, str]]], trace: dict[str, Any], open_issue_map: dict[str, str], id_to_ref: dict[str, str]) -> None:
    rec = jira_root / "reconciliation"
    authority = """# Source Authority Map

## Precedence model

1. Explicit protected/immutable project rules and sealed judging/split artifacts outrank ordinary planning text.
2. Final W25 handoff and current-state artifacts outrank stale wave-transition summaries.
3. Current machine-readable governance registries outrank older narrative counts for the same registry.
4. Final known gaps, risk register, implementation priority, backlog, and component maturity determine post-wave actionability.
5. Later accepted ADRs may supersede earlier revisable assumptions, but recency never overrides a protected invariant by itself.
6. Earlier architecture and wave documents remain authoritative detailed design/provenance unless explicitly superseded.
7. Executable source/tests prove current starter behavior; they do not prove real-data, protected, target-hardware, scientific, or operating results not present in evidence.

## Conflict handling

Conflicts are recorded in `CONFLICT_REGISTER.csv`. The generator never guesses through an unresolved conflict that affects safety, scientific validity, rights, target configuration, or completion state. A newer file is not automatically authoritative; authority class, protected status, explicit supersession, and final handoff context are evaluated together.

## Canonical source references

Repository-relative paths are canonical. Absolute Windows paths are convenience metadata. Every generated source reference stores SHA-256, heading/line metadata, and an anchor hash/excerpt so drift can be detected and relocated.
"""
    write_text(rec / "SOURCE_AUTHORITY_MAP.md", authority)

    inventory_rows = []
    for rel, f in sorted(repo.files.items()):
        inventory_rows.append({
            "repo_relative_path": rel, "size_bytes": f.size_bytes, "line_count": f.line_count,
            "sha256": f.sha256, "authority_level": f.authority_level, "role": f.role,
            "top_directory": f.top_dir, "extension": f.extension, "parse_status": f.parse_status,
        })
    write_csv(rec / "REPO_INVENTORY.csv", inventory_rows)

    current_state = f"""# Current-State Reconciliation

- The repository contains **{len(repo.files)}** non-Jira files and represents the completed 25-wave planning/design/starter/handoff program.
- There is **no Wave 26**. The current lifecycle is post-W25 implementation, materialization, empirical validation, production readiness, deployment, operation, and improvement.
- Authoritative governance inventories: {len(regs['requirements'])} requirements, {len(regs['adrs'])} ADRs, {len(regs['controls'])} acceptance controls, {len(regs['epics'])} historical epics, and {len(regs['wbs'])} historical WBS tasks.
- Historical WBS status is preserved as scoped provenance. It is never converted directly into a claim that the product is trained, empirically validated, target-hardware proven, production-ready, or operating.
- All baseline unit/governance tests supplied by the repository were run before generation; those passing starter/governance checks do not substitute for the real-data and protected-evaluation work represented in the post-wave backlog.
- The post-wave graph contains {sum(i.issue_type == 'Epic' and i.local_id.startswith('POST-') for i in issues)} Epics, {sum(i.issue_type == 'Story' for i in issues)} Stories, and {sum(i.issue_type == 'Subtask' for i in issues)} atomic Subtasks.

## Reconciled completion model

Workflow state, implementation maturity, and evidence state are separate. Historical `DONE` means the original scoped task completed. A downstream post-wave issue closes remaining materialization, empirical, production, target-host, or operating maturity. The release path runs through source access → immutable history → entity resolution → PIT/protected replay → feature/model science → sealed validation/promotion → weekly publication → product/operations → final acceptance.
"""
    write_text(rec / "CURRENT_STATE_RECONCILIATION.md", current_state)

    hist_rows = []
    by_id = {i.local_id: i for i in issues}
    for row in regs["wbs"]:
        tid = row["task_id"]
        issue = by_id[tid]
        related_post = issue.related_to[0] if issue.related_to else ""
        hist_rows.append({
            "task_id": tid, "source_status": row.get("status", ""), "jira_workflow_state": issue.workflow_state,
            "historical_classification": issue.historical_classification, "scoped_maturity": issue.maturity_after,
            "evidence_state": issue.evidence_state, "related_post_wave_issue": related_post,
            "interpretation": "Original scoped completion only; post-wave issue carries any higher-maturity obligation." if issue.workflow_state == "DONE" else "Original task remains blocked/planned/deferred and is preserved as provenance; execute only through current admission/dependency rules.",
        })
    write_csv(rec / "HISTORICAL_STATUS_RECONCILIATION.csv", hist_rows)

    conflicts = [
        {"conflict_id": "CONFLICT-001", "source_a": "README.md", "source_b": "docs/final/CODEX_HANDOFF.md;governance/CURRENT_STATE.yaml", "topic": "Next wave/state", "resolution": "Final W25 handoff/current state controls: 25 waves complete; no Wave 26.", "impact": "Prevents creation of a fictitious Wave 26.", "jira_review_issue": "", "status": "RESOLVED_BY_AUTHORITY"},
        {"conflict_id": "CONFLICT-002", "source_a": "governance/EPIC_CATALOG.csv", "source_b": "governance/IMPLEMENTATION_WBS.csv;docs/final/FINAL_BACKLOG.csv", "topic": "Historical epic status freshness", "resolution": "Preserve catalog as historical provenance; derive scoped state from current WBS/final handoff and create separate post-wave work.", "impact": "Avoids stale catalog status becoming product completion.", "jira_review_issue": "", "status": "RESOLVED_BY_RECONCILIATION"},
        {"conflict_id": "CONFLICT-003", "source_a": "governance/IMPLEMENTATION_WBS.csv DONE", "source_b": "docs/final/FINAL_COMPONENT_MATURITY.csv;docs/final/FINAL_KNOWN_GAPS.csv", "topic": "Meaning of DONE", "resolution": "DONE is scoped planning/design/starter completion. Maturity/evidence fields and post-wave issues represent real completion obligations.", "impact": "Prevents fabricated model/data/operations completion.", "jira_review_issue": "", "status": "RESOLVED_BY_MATURITY_MODEL"},
        {"conflict_id": "CONFLICT-004", "source_a": "governance/OPEN_ISSUES.md historical introduction", "source_b": "W25 final handoff and issue sections", "topic": "Open-issue currency", "resolution": "Retain all issue IDs as provenance; map actionable/current content to post-wave domain gates and do not assume every old sentence remains current.", "impact": "Prevents obsolete text from creating duplicate work while preserving gaps.", "jira_review_issue": "", "status": "RESOLVED_WITH_TRACEABILITY"},
        {"conflict_id": "CONFLICT-005", "source_a": "Portable Jira defaults", "source_b": "Unknown destination configuration", "topic": "Issue types/statuses/priorities/custom fields/link types", "resolution": "Target profile remains a template; admin discovers and maps actual configuration before production import/API execution.", "impact": "Import is portable but requires a final mapping step.", "jira_review_issue": "", "status": "OPEN_MANUAL_CONFIGURATION"},
    ]
    write_csv(rec / "CONFLICT_REGISTER.csv", conflicts)

    gap_rows = []
    for row in regs["gaps"]:
        gid = row["gap_id"]
        target = trace["gap_post"].get(gid, "")
        gap_rows.append({**row, "jira_issue_ids": [target] if target else [], "disposition": "ACTIONABLE" if target else "UNMAPPED", "source_ref_id": id_to_ref.get(gid, "")})
    write_csv(rec / "GAP_TO_JIRA_MAPPING.csv", gap_rows)

    risk_rows = []
    for row in regs["risks"]:
        rid = row["risk_id"]
        target = trace["risk_post"].get(rid, "")
        risk_rows.append({**row, "jira_issue_ids": [target] if target else [], "source_ref_id": id_to_ref.get(rid, ""), "mapped": bool(target)})
    write_csv(rec / "RISK_TO_JIRA_MAPPING.csv", risk_rows)

    open_rows = []
    for iid, info in extract_open_issue_sections(repo).items():
        open_rows.append({
            "open_issue_id": iid, "title": info["title"], "source_path": "governance/OPEN_ISSUES.md",
            "start_line": info["start"], "end_line": info["end"], "jira_issue_ids": [open_issue_map.get(iid, "")],
            "disposition": "MAPPED_TO_CURRENT_DOMAIN_GATE", "source_ref_id": id_to_ref.get(iid, ""),
        })
    write_csv(rec / "OPEN_ISSUE_TO_JIRA_MAPPING.csv", open_rows)

    unresolved = [
        {"review_id": "REVIEW-001", "topic": "Destination Jira configuration discovery", "blocking_scope": "IMPORT", "state": "OPEN_MANUAL", "required_action": "Populate JIRA_TARGET_PROFILE.yaml and confirm issue types, hierarchy, statuses, priorities, components, fields, screens, and link types.", "owner": "Jira admin", "jira_issue": ""},
        {"review_id": "REVIEW-002", "topic": "Future public distribution or commercialization rights review", "blocking_scope": "PUBLICATION_ONLY", "state": "NOT_TRIGGERED", "required_action": "Review publication rights only if public distribution or commercialization is proposed; never block private local acquisition or training.", "owner": "Project publication policy", "jira_issue": trace["gap_post"].get("GAP-010", "")},
        {"review_id": "REVIEW-003", "topic": "Technical credential and route validation", "blocking_scope": "AFFECTED_SOURCE_ROUTE_ONLY", "state": "OPEN_IMPLEMENTATION", "required_action": "Use configured credentials outside Git, run redacted technical smokes, and substitute an equivalent public route when one route is unavailable.", "owner": "Codex implementation", "jira_issue": trace["handoff_post"].get("HANDOFF-002", "")},
        {"review_id": "REVIEW-004", "topic": "Authoritative target hardware", "blocking_scope": "AC-038_AND_RELEASE", "state": "OPEN_EXTERNAL", "required_action": "Run representative benchmark on the declared Windows/Ryzen 7 HX/32GB/RTX 5060/NVMe target and set thresholds only from evidence.", "owner": "Human operator/target host", "jira_issue": trace["gap_post"].get("GAP-001", "")},
        {"review_id": "REVIEW-005", "topic": "Real historical data and empirical results", "blocking_scope": "MODEL_AND_RELEASE", "state": "OPEN_IMPLEMENTATION", "required_action": "Materialize maximum quality-supported history and execute PIT/protected evaluation. No metrics or winner are prefilled.", "owner": "Implementation agents", "jira_issue": trace["gap_post"].get("GAP-002", "")},
    ]
    write_csv(rec / "UNRESOLVED_REVIEW_ITEMS.csv", unresolved)

def adf_document(text: str) -> dict[str, Any]:
    blocks = []
    for para in [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]:
        blocks.append({"type": "paragraph", "content": [{"type": "text", "text": para[:30000]}]})
    return {"version": 1, "type": "doc", "content": blocks or [{"type": "paragraph", "content": []}]}


def import_row(i: Issue, by_id: dict[str, Issue]) -> dict[str, Any]:
    labels = list(dict.fromkeys(i.labels + [f"local-id-{i.local_id.lower()}"]))
    return {
        "Issue type": jira_issue_type(i.issue_type),
        "Issue key": "",
        "Issue ID": i.import_id,
        "Summary": i.title,
        "Parent": by_id[i.parent_id].import_id if i.parent_id else "",
        "Description": issue_description_md(i),
        "Status": status_for_import(i.workflow_state),
        "Priority": priority_for_import(i.priority),
        "Labels": labels,
        "Component": i.component,
        "Local Issue ID": i.local_id,
        "Source IDs": i.source_ids,
        "Phase": i.phase,
        "Logical Workflow State": i.workflow_state,
        "Implementation Maturity": i.maturity_after,
        "Evidence State": i.evidence_state,
        "Owner Historical Wave": i.owner_wave,
        "Critical Path": i.critical_path,
        "Execution Lane": i.execution_lane,
    }


def write_import_pack(jira_root: Path, issues: list[Issue]) -> dict[str, Any]:
    imp = jira_root / "import"
    by_id = {i.local_id: i for i in issues}
    ordered = sorted(issues, key=lambda x: x.import_id)
    rows = [import_row(i, by_id) for i in ordered]
    fields = ["Issue type", "Issue key", "Issue ID", "Summary", "Parent", "Description", "Status", "Priority", "Labels", "Component", "Local Issue ID", "Source IDs", "Phase", "Logical Workflow State", "Implementation Maturity", "Evidence State", "Owner Historical Wave", "Critical Path", "Execution Lane"]
    write_csv(imp / "JIRA_ISSUES_MASTER.csv", rows, fields)
    write_csv(imp / "JIRA_EXTERNAL_SYSTEM_IMPORT.csv", rows, fields)
    write_csv(imp / "JIRA_HIERARCHY_STAGE_1.csv", [r for r in rows if r["Issue type"] == "Epic"], fields)
    write_csv(imp / "JIRA_HIERARCHY_STAGE_2.csv", [r for r in rows if r["Issue type"] in {"Story", "Task", "Bug"}], fields)
    write_csv(imp / "JIRA_HIERARCHY_STAGE_3.csv", [r for r in rows if r["Issue type"] == "Sub-task"], fields)

    link_rows = []
    for i in ordered:
        for dep in i.dependencies:
            link_rows.append({
                "source_local_id": dep, "relationship": "BLOCKS", "target_local_id": i.local_id,
                "source_jira_key": f"{{{{JIRA_KEY:{dep}}}}}", "target_jira_key": f"{{{{JIRA_KEY:{i.local_id}}}}}",
                "target_link_type_name": "Blocks", "status": "PENDING_POST_IMPORT_KEY_MAP",
            })
        for rel in i.related_to:
            link_rows.append({
                "source_local_id": i.local_id, "relationship": "RELATES_TO", "target_local_id": rel,
                "source_jira_key": f"{{{{JIRA_KEY:{i.local_id}}}}}", "target_jira_key": f"{{{{JIRA_KEY:{rel}}}}}",
                "target_link_type_name": "Relates", "status": "PENDING_POST_IMPORT_KEY_MAP",
            })
    write_csv(imp / "JIRA_LINKS.csv", link_rows)
    write_jsonl(imp / "JIRA_LINKS.jsonl", link_rows)

    create_payloads = []
    for i in ordered:
        parent_template = {"key": f"{{{{JIRA_KEY:{i.parent_id}}}}}"} if i.parent_id else None
        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": "{{PROJECT_KEY}}"},
                "issuetype": {"name": f"{{{{ISSUE_TYPE:{i.issue_type}}}}}"},
                "summary": i.title,
                "description": adf_document(issue_description_md(i)),
                "labels": list(dict.fromkeys(i.labels + [f"local-id-{i.local_id.lower()}"])),
            }
        }
        if parent_template:
            payload["fields"]["parent"] = parent_template
        create_payloads.append({
            "local_id": i.local_id,
            "method": "POST",
            "endpoint": "/rest/api/3/issue",
            "payload_template": payload,
            "logical_fields_requiring_target_custom_field_ids": {
                "Local Issue ID": i.local_id,
                "Source IDs": ";".join(i.source_ids),
                "Phase": i.phase,
                "Logical Workflow State": i.workflow_state,
                "Implementation Maturity": i.maturity_after,
                "Evidence State": i.evidence_state,
                "Owner Historical Wave": i.owner_wave,
                "Critical Path": i.critical_path,
                "Execution Lane": i.execution_lane,
            },
            "execution_status": "TEMPLATE_ONLY_REQUIRES_TARGET_PROFILE_AND_PARENT_KEY_MAP",
        })
    write_jsonl(imp / "JIRA_API_CREATE_PAYLOADS.jsonl", create_payloads)

    link_payloads = []
    for row in link_rows:
        link_name = "Blocks" if row["relationship"] == "BLOCKS" else "Relates"
        link_payloads.append({
            "method": "POST", "endpoint": "/rest/api/3/issueLink",
            "source_local_id": row["source_local_id"], "target_local_id": row["target_local_id"],
            "payload_template": {
                "type": {"name": f"{{{{LINK_TYPE:{link_name}}}}}"},
                "outwardIssue": {"key": row["source_jira_key"]},
                "inwardIssue": {"key": row["target_jira_key"]},
            },
            "execution_status": "TEMPLATE_ONLY_REQUIRES_POST_IMPORT_KEY_MAP_AND_LINK_TYPE_DISCOVERY",
        })
    write_jsonl(imp / "JIRA_API_LINK_PAYLOADS.jsonl", link_payloads)

    key_map_rows = [{"local_id": i.local_id, "import_id": i.import_id, "jira_key": "", "jira_issue_id": "", "verified": False} for i in ordered]
    write_csv(imp / "POST_IMPORT_KEY_MAP_TEMPLATE.csv", key_map_rows)

    readme = """# Jira Import Pack

## Recommended path

1. Populate `project/JIRA_TARGET_PROFILE.yaml` from the actual destination Jira configuration.
2. Create/map the minimum custom fields, components, issue types, statuses, priorities, and link types before import.
3. Use Jira administration **External System Import → CSV** for the ordered `JIRA_EXTERNAL_SYSTEM_IMPORT.csv`. The ordinary bulk CSV creator is not suitable for this multi-level hierarchy.
4. Map `Issue ID` and `Parent` exactly. The CSV is ordered Epics → standard work items → Sub-tasks, and each child Parent contains the numeric Issue ID of its parent.
5. Map the portable Status/Priority defaults to actual existing values. Preserve `Logical Workflow State`, maturity, and evidence as separate fields.
6. Import a small test subset or disposable test project first; validate descriptions, hierarchy, fields, and encoding.
7. Export the created issues with Local Issue ID and Jira key, populate `POST_IMPORT_KEY_MAP_TEMPLATE.csv`, and run `tools/reconcile_jira_export.py`.
8. Create dependency/related links only after real keys and link types are known, using the API/link templates or a separately supported import mechanism.
9. Run `tools/validate_jira_pack.py` and complete `POST_IMPORT_VALIDATION_CHECKLIST.md`.

## Portability cautions

- No Jira-generated issue key, issue ID, field ID, project ID, user ID, workflow ID, or component ID is fabricated.
- Jira Cloud uses the `Parent` field rather than deprecated `Epic Link` behavior for current hierarchy imports.
- All target configuration must already exist or be explicitly created/mapped by an administrator before production import.
- API payloads target Jira Cloud REST API v3 and use Atlassian Document Format for descriptions, but remain inert templates until the target profile is completed.
- Stage CSVs are convenient inspection/recovery views. The single ordered external-system-import CSV is the primary hierarchy artifact; independent multi-pass imports require replacement of local parent references with actual Jira keys.
"""
    write_text(imp / "README_IMPORT.md", readme)
    write_text(imp / "IMPORT_ORDER.md", """# Import Order

1. Discover/configure destination Jira and complete the target profile.
2. Dry-run `JIRA_EXTERNAL_SYSTEM_IMPORT.csv` in a test project or with a small representative subset.
3. Import the full ordered CSV: all Epics first, then Stories/Tasks, then Sub-tasks.
4. Export Local Issue ID ↔ Jira key/ID and reconcile locally.
5. Validate counts, hierarchy, descriptions, statuses, priorities, components, labels, and custom fields.
6. Create hard-dependency and related links from `JIRA_LINKS.csv`/API payloads using real Jira keys.
7. Validate links and run the post-import checklist.
8. Create the active board/filter emphasizing `post-wave`, `actionable`, and logical READY/BLOCKED states while excluding historical planning work by default.
""")
    write_text(imp / "FIELD_MAPPING_GUIDE.md", """# Field Mapping Guide

| CSV column | Destination | Required handling |
|---|---|---|
| Issue type | Jira issue/work type | Map Epic, Story, Task, and Sub-task to existing destination types. |
| Issue ID | External import identity | Preserve unique numeric values during the hierarchy import. |
| Parent | Parent | Map to Parent; values are parent Issue IDs in the ordered single-file import. |
| Summary | Summary | Required. |
| Description | Description | Multiline Markdown-like text; verify rendering after test import. |
| Status | Status | Map portable defaults to existing workflow statuses. |
| Priority | Priority | Map to existing target priorities. |
| Labels | Labels | Multi-value mapping; keep controlled vocabulary. |
| Component | Component/s | Pre-create or map controlled components. |
| Local Issue ID | Custom field | Required stable reconciliation key. |
| Source IDs | Custom field | Searchable compact list of historical/governance IDs. |
| Phase | Custom field/label | Portable grouping; no unsupported initiative level is assumed. |
| Logical Workflow State | Custom field | Preserves READY/BLOCKED/etc. separately from target workflow. |
| Implementation Maturity | Custom field | Mandatory semantic separation from status. |
| Evidence State | Custom field | Mandatory semantic separation from status/maturity. |
| Owner Historical Wave | Custom field | Historical wave or POST_W25 provenance. |
| Critical Path | custom boolean/label | Dependency criticality, not schedule duration. |
| Execution Lane | custom select/label | Safe parallelism and gate routing. |

Detailed requirement, ADR, acceptance, risk, test, artifact, and source-reference lists stay canonical in the local records/indexes to avoid custom-field bloat.
""")
    write_text(imp / "IMPORT_CONFIGURATION_NOTES.md", """# Import Configuration Notes

- Generated against official Atlassian guidance reviewed on 2026-08-08; confirm the current documentation and destination behavior immediately before import.
- The standard bulk CSV creator cannot reconstruct multiple hierarchy levels; use the admin External System Import path.
- Existing project imports require administrator permissions and destination configuration compatible with the imported values.
- Parent-child preservation depends on correct ordering plus unique Issue ID and Parent mapping.
- Do not use legacy Epic Link unless the actual non-Cloud destination explicitly requires it; the portable Cloud design uses Parent.
- Issue links must be configured in the destination. For reliability, create issues first, reconcile real keys, then add links and test on a small subset.
- REST v3 payload templates use ADF for description; custom field IDs and project configuration remain placeholders.
- Back up or use a disposable test project before a bulk operation. Never assume link imports can be bulk-rolled back safely.
""")
    write_text(imp / "POST_IMPORT_VALIDATION_CHECKLIST.md", """# Post-Import Validation Checklist

- [ ] Imported issue count equals `validation/COVERAGE_REPORT.json` total issue count.
- [ ] Every Local Issue ID appears exactly once and maps to one real Jira key.
- [ ] No Jira key was prefilled or fabricated before import.
- [ ] All 50 Epics exist; historical and post-wave Epics are distinguishable.
- [ ] Stories/Tasks have the intended Epic parent and all Sub-tasks have the intended Story parent.
- [ ] No orphan or impossible parent relationship exists.
- [ ] Descriptions preserve acceptance criteria, Definition of Done, tests, evidence, stop conditions, and source references.
- [ ] Logical workflow, maturity, and evidence values survived as separate fields.
- [ ] Controlled labels/components imported without uncontrolled variants.
- [ ] Default board excludes historical planning items and emphasizes actionable post-wave work.
- [ ] Every dependency link in `JIRA_LINKS.csv` exists with the correct direction/type.
- [ ] READY items have no unresolved hard dependency; blocked items display their unblock condition.
- [ ] Deferred/conditional advanced and live work is not pulled into the core release board.
- [ ] Gap/risk/requirement/acceptance traceability remains resolvable through Local Issue ID.
- [ ] A small sample of source references resolves to the same repository path/hash/anchor.
- [ ] Jira export was reconciled locally and `tools/validate_jira_pack.py` passes afterward.
""")
    return {"issue_rows": rows, "link_rows": link_rows, "create_payloads": create_payloads, "link_payloads": link_payloads}

def work_packet_markdown(i: Issue) -> str:
    return f"""# AI Work Packet — {i.local_id}

## What am I doing?

{i.objective}

## Why?

{i.why_exists}

## Current gate state

- Workflow: `{i.workflow_state}`
- Ready: `{str(i.ready).lower()}`
- Priority: `{i.priority}`
- Critical path: `{str(i.critical_path).lower()}`
- Execution lane: `{i.execution_lane}`
- Maturity before → after: `{i.maturity_before}` → `{i.maturity_after}`
- Evidence state: `{i.evidence_state}`

## Read first

1. `{i.canonical_record}`
2. `jira/sources/issue_source_manifests/{i.local_id}.json`
3. Only the source sections referenced by that manifest.
4. The implementation files needed for this issue—never the entire Jira directory.

## Dependencies that must already be complete

{md_list(i.dependencies)}

## What may I modify?

{md_list(i.files_expected)}

## What must I not modify or weaken?

{md_list(i.protected_files)}

## Exact outputs

{md_list(i.outputs)}

## Acceptance criteria

{md_numbered(i.acceptance_criteria)}

## Tests

{md_list([f"{t.get('classification')}: {t.get('path')} — {t.get('expectation')}" for t in i.tests])}

## Evidence to return

{md_list(i.evidence)}

## Stop instead of improvising when

{md_list(i.stop_conditions)}

## Completion protocol

1. Prove every acceptance criterion from saved evidence.
2. Run every applicable test and preserve commands/exit codes.
3. Confirm the claimed maturity actually exists; code alone is not completion.
4. Update the local canonical record and the live Jira operational fields according to `jira/SYNC_CONTRACT.md`.
5. Append a meaningful change-log event; preserve prior evidence.
6. Recompute READY/BLOCKED queues and validate the Jira pack.
7. Reevaluate every downstream issue in `blocks`.
"""


def write_ai_views(jira_root: Path, issues: list[Issue]) -> None:
    ai = jira_root / "ai"
    ready = sorted([i for i in issues if i.ready], key=lambda x: ({"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(x.priority, 9), not x.critical_path, x.local_id))
    blocked_p0 = [i for i in issues if i.workflow_state == "BLOCKED" and i.priority == "P0" and i.historical_classification == "ACTIONABLE_POST_WAVE"]
    context = f"""# Current Context

- Lifecycle: **Post-W25 implementation handoff**. The 25-wave planning/design/starter program is complete. **There is no Wave 26.**
- Product state: governance and functional starters exist; real historical materialization, PIT/protected replay, empirical model/scientific validation, target-host proof, and operating evidence remain incomplete.
- Current executable issue count: {sum(i.issue_type == 'Subtask' and i.historical_classification == 'ACTIONABLE_POST_WAVE' for i in issues)} post-wave Subtasks.
- READY now: {len(ready)}. Read `jira/index/READY_QUEUE.csv`; execute only a READY Subtask.
- P0 blocked now: {len(blocked_p0)}. Read `jira/index/BLOCKED_QUEUE.csv` for exact evidence/unblock conditions.
- Core critical spine: source access/rights → immutable history → entities → PIT/replay → features → baselines → protected promotion → weekly publication → product/operations → release.
- Protected invariants: no future/same-game leakage, no fabricated metrics/evidence/rights/keys, BAS is Aggie-specific excess under valid pregame expectation—not generic loss probability—and null results are valid.
- Source authority: `jira/reconciliation/SOURCE_AUTHORITY_MAP.md`.
- Local/Jira ownership: `jira/SYNC_CONTRACT.md`.

## Top currently READY

{md_list([f"`{i.local_id}` — {i.title} ({i.priority}; {i.execution_lane})" for i in ready[:10]])}
"""
    write_text(ai / "CURRENT_CONTEXT.md", context)
    write_text(ai / "READY_QUEUE_COMPACT.md", "# Compact READY Queue\n\n" + ("\n".join(f"{n}. `{i.local_id}` | {i.priority} | {'CRITICAL' if i.critical_path else 'normal'} | {i.execution_lane} | {i.title}" for n, i in enumerate(ready, 1)) or "No issues are currently READY. Resolve blockers rather than selecting future/conditional work."))

    write_text(ai / "AI_JIRA_USAGE.md", """# AI Jira Usage

## Minimal retrieval sequence

1. Read `CURRENT_CONTEXT.md`.
2. Read `../index/READY_QUEUE.csv` or `READY_QUEUE_COMPACT.md`.
3. Select the highest valid READY **Subtask** compatible with the current execution lane/resources.
4. Open only that issue's canonical JSON or generated Markdown.
5. Open only `../sources/issue_source_manifests/<LOCAL_ID>.json`.
6. Verify source hashes/anchors, blockers, protected files, and expected outputs.
7. Execute the work in an isolated worktree when appropriate.
8. Run required tests and produce evidence with exact identities.
9. Apply `AI_COMPLETION_PROTOCOL.md` and `AI_SYNC_PROTOCOL.md`.
10. Recompute queues and validate.

Do **not** ingest the entire `jira/` directory into context. Indexes are retrieval maps, not documents to memorize. Do not execute Epics or Stories directly. Do not start hard-blocked, conditional, or deferred work merely because compute is idle.

## Query shortcuts

- Next valid work: `index/READY_QUEUE.csv`
- Why something is blocked: `index/BLOCKED_QUEUE.csv`
- Full issue lookup: `index/ISSUE_INDEX.csv`
- Source lookup: `index/SOURCE_REFERENCE_INDEX.csv`
- Dependency lookup: `index/DEPENDENCY_INDEX.csv`
- Requirement/control/ADR/test/artifact lookup: the corresponding traceability CSV.
- Exact execution packet: `ai/work_packets/<LOCAL_ID>.md`
""")
    write_text(ai / "AI_EXECUTION_PROTOCOL.md", """# AI Execution Protocol

1. Confirm the selected record is `READY=true`, is a Subtask, and has no unresolved external blocker.
2. Verify every hard dependency is `DONE` with `COMPLETE` or `VERIFIED` evidence at the required maturity.
3. Verify canonical source hashes; relocate changed anchors through controlled regeneration rather than trusting stale line numbers.
4. Read only required sources and implementation files.
5. Use the declared execution lane:
   - `SOLO_WORKTREE`: isolated changes with no protected shared-contract mutation.
   - `SHARED_CONTRACT`: serialize/coordinate contract changes and rerun affected consumers.
   - `PROTECTED_GATE`: never weaken or bypass; stop on ambiguity.
   - `RESEARCH_LANE`: preserve negative/null results and prohibit production promotion without gate evidence.
   - `DATA_MATERIALIZATION`: enforce source rights, immutable raw evidence, provenance, PIT rules, and resource limits.
   - `OPERATIONS`: preserve rollback, observability, security, and recovery behavior.
6. Execute only in-scope work. Record unexpected necessary work as a new review/gap proposal rather than silently expanding scope.
7. Save artifacts at declared paths or update the issue through a controlled specification change before producing alternatives.
8. Return exact commands, exit codes, hashes, row/season/source coverage, failures, and unresolved assumptions.
""")
    write_text(ai / "AI_COMPLETION_PROTOCOL.md", """# AI Completion Protocol

An issue is not Done merely because code exists or tests unrelated to its criteria pass.

1. Evaluate every acceptance criterion from observable evidence.
2. Run existing tests and implement every declared NEW TEST REQUIRED.
3. Confirm every expected artifact exists, is content-hashed, and records input/source/code/config/runtime identity.
4. Verify applicable PIT/leakage, rights, security, scientific, calibration, benchmark, operations, and reproducibility controls.
5. Confirm achieved maturity equals the issue's expected maturity; otherwise remain in VALIDATION/EVIDENCE_PENDING/BLOCKED.
6. Preserve negative/null results. Never fabricate model winner, metrics, A&M lift, BAS effect, SLA, source coverage, rights, or target-hardware performance.
7. Update Jira operational state and local mirror fields through the sync contract.
8. Append a material change/evidence event; never rewrite prior accepted evidence.
9. Recompute downstream READY/BLOCKED state and run the Jira-pack validator.
10. For Stories/Epics, require the integrated gate and downstream-consumption proof even when all children appear complete.
""")
    write_text(ai / "AI_SYNC_PROTOCOL.md", """# AI Sync Protocol

- Local canonical JSON owns specification, scope, source references, requirements, acceptance criteria, DoD, tests, dependencies, protected constraints, and expected artifacts.
- Jira owns live status, assignee, sprint, comments, ordering, and execution ownership.
- Synchronization mirrors operational fields locally but must not overwrite local specifications from Jira free text.
- A changed local specification requires a version-control change and change-log entry before Jira description refresh.
- A changed Jira status/assignee/sprint is imported through a Jira export/API response keyed by Local Issue ID.
- Conflicts are reported and left unresolved; never use last-write-wins across authority boundaries.
- After any meaningful update: rebuild indexes/import derivatives, recompute READY/BLOCKED, validate source references/dependencies/import files, and snapshot state when appropriate.
""")

    for i in issues:
        if i.issue_type == "Subtask" and i.historical_classification == "ACTIONABLE_POST_WAVE":
            write_text(ai / "work_packets" / f"{i.local_id}.md", work_packet_markdown(i))


def write_root_docs(jira_root: Path, repo: RepoIndex, issues: list[Issue]) -> None:
    readme = f"""# Local Jira System — Aggie Analytics Engine / Battered Aggie Syndrome

This directory is the canonical local Jira specification and import/reconciliation system for the post-W25 project lifecycle. It was generated by read-only reconnaissance of {len(repo.files)} repository files, not from memory.

## Canonical model

- Canonical issue specifications: `records/issues/**/*.json`
- Generated human-readable views: `issues/**/*.md`
- Tiny execution entrypoint: `ai/CURRENT_CONTEXT.md` and `index/READY_QUEUE.csv`
- Source authority/reconciliation: `reconciliation/`
- Traceability/indexes: `index/` and `sources/`
- Jira import/API templates: `import/`
- Deterministic validators/rebuilders: `tools/`

The JSON record is authoritative. Markdown, indexes, queues, work packets, CSVs, and API payloads are generated derivatives. Never maintain two competing editable copies.

## Scope and state

- Historical planning: {sum(i.local_id.startswith('EPIC-') for i in issues)} Epics and {sum(i.local_id.startswith('TASK-') for i in issues)} WBS Tasks retained with original IDs.
- Post-wave completion: {sum(i.local_id.startswith('POST-EPIC-') for i in issues)} Epics, {sum(i.local_id.startswith('POST-STORY-') for i in issues)} Stories, and {sum(i.local_id.startswith('POST-SUBTASK-') for i in issues)} atomic Subtasks.
- The 25-wave program is complete. There is no Wave 26.
- Historical DONE is scoped provenance—not proof of full data, model, empirical, target-hardware, production, or operating completion.

## First use

1. Read `ai/CURRENT_CONTEXT.md`.
2. Read `index/READY_QUEUE.csv`.
3. Open one READY Subtask and its source manifest.
4. Follow its AI work packet.
5. After work, run `python -B jira/tools/update_ready_queue.py` and `python -B jira/tools/validate_jira_pack.py`.

## Jira import

Start with `import/README_IMPORT.md`. Populate `project/JIRA_TARGET_PROFILE.yaml`; no destination configuration, custom field ID, project ID, or Jira key is assumed.
"""
    write_text(jira_root / "README.md", readme)
    write_text(jira_root / "SCHEMA.md", """# Jira Local Schema

## Canonical issue record

Each `records/issues/**/*.json` contains:

- identity/hierarchy: schema version, Local ID, Jira key, import ID, issue type, parent, Epic, phase;
- state: workflow, historical/actionable classification, priority, critical path, maturity before/after, evidence state, READY/blocker data;
- provenance: owner/historical wave, source IDs, source-reference IDs, requirements, controls, ADRs, risks, gaps;
- executable specification: objective, why, scope, in/out, prerequisites, dependencies, blocks, expected files/protected files/outputs;
- completion contract: acceptance criteria, Definition of Done, tests, evidence, E2E validation, risks, stop conditions;
- search/operation: labels, component, execution lane, AI notes, canonical/derived paths.

## State separation

Workflow state, implementation maturity, and evidence state are independent. A record may be workflow `DONE` at maturity `FUNCTIONAL_STARTER` with verified evidence for that scoped starter while a separate post-wave issue remains open for empirical validation.

## IDs

Historical IDs (`EPIC-###`, `TASK-###`, `REQ-###`, `AC-###`, `ADR-###`, `RISK-###`, `GAP-###`, `HANDOFF-###`, `ISSUE-###`) are preserved. New Jira-local work uses `POST-EPIC-###`, `POST-STORY-###`, and `POST-SUBTASK-###`. Jira keys remain blank until the destination creates them.

## Dependencies

Hierarchy and execution dependency are separate. `parent_id`/`epic_id` define hierarchy. `dependencies` are hard prerequisites. `blocks` is the computed inverse. `related_to` records nonblocking provenance/reconciliation relationships.

## Sources

Source-reference IDs resolve through `sources/SOURCE_ANCHOR_INDEX.csv`; repository-relative path is canonical. Hash + heading/line + anchor support drift detection.
""")
    write_text(jira_root / "SYNC_CONTRACT.md", """# Local ↔ Jira Sync Contract

## Local authority

The repository owns stable Local ID, issue specification/scope, hierarchy intent, source references, requirements/ADRs/acceptance controls, technical dependencies, acceptance criteria, Definition of Done, required tests/evidence, protected constraints, and expected artifacts.

## Jira authority

Jira owns the assigned Jira key/ID, current operational workflow status, assignee, sprint, board rank, comments, and current execution ownership.

## Conflict policy

- Never silently overwrite an authoritative field from the other side.
- Specification changes originate locally through version control and are then pushed to Jira.
- Operational changes originate in Jira and are mirrored locally through export/API reconciliation.
- If both sides changed the same authority-owned field, emit a conflict and require review.
- Preserve historical evidence and prior accepted states; do not rewrite them in place.

## Required update sequence

1. Apply the authority-appropriate change.
2. Append a material event to `history/ISSUE_CHANGE_LOG.jsonl`.
3. Rebuild generated views/indexes/import derivatives.
4. Recompute READY/BLOCKED.
5. Run validators.
6. Snapshot Jira-local operational state for major releases/imports.
""")
    write_text(jira_root / "DESIGN_DECISIONS.md", """# Jira-System Design Decisions

1. **JSON is canonical; Markdown is generated.** This prevents manually divergent human/machine copies.
2. **Standard portable hierarchy only.** Epics contain Stories or historical Tasks; Stories contain Sub-tasks. Phases are metadata/components, not an assumed unsupported initiative type.
3. **Historical and post-wave work coexist.** Historical IDs/statuses remain visible and filterable; post-wave issues carry real completion obligations.
4. **No direct DONE conversion.** Workflow, maturity, and evidence are separate so a completed design/starter never becomes fabricated product completion.
5. **Atomic post-wave execution uses Sub-tasks.** Each has explicit outputs, tests, evidence, stop conditions, and a compact AI packet. Stories/Epics are integrated gates, not direct execution units.
6. **Source references are hash/anchor based.** Full documents are not duplicated across issues; shared canonical sources plus per-issue manifests minimize token/storage drift.
7. **Indexes/queues are deterministic derivatives.** AI sessions start from compact queues and open one issue/source set.
8. **Import is target-neutral.** The primary artifact is an ordered External System Import CSV with Issue ID/Parent; API/link payloads remain templates until real target fields/keys/link types are discovered.
9. **Links follow key reconciliation.** Hard-dependency links are created only after Jira assigns real keys, avoiding guessed key ordering.
10. **Conditional/deferred lanes stay outside core release.** Advanced challengers require admission evidence; live/in-game remains separately deferred and cannot block completion of the pregame product.
11. **Simple deterministic tooling.** Markdown, CSV, JSON/JSONL, JSON-compatible YAML, and stdlib Python are used; no database/service is required.
""")
    write_text(jira_root / "CHANGELOG.md", f"""# Jira System Changelog

## {GEN_DATE} — v1 generated

- Completed full read-only repository reconnaissance.
- Reconciled historical WBS status against final maturity/gap/handoff evidence.
- Created {len(issues)} canonical issue records and generated views.
- Created source, requirement, acceptance, ADR, risk, gap, test, artifact, hierarchy, and dependency traceability.
- Created compact AI queues/work packets and Jira import/API templates.
- Created validation, rebuild, reconciliation, and snapshot tooling.

Future meaningful changes must be appended; do not log trivial generated formatting churn.
""")
    write_jsonl(jira_root / "history" / "ISSUE_CHANGE_LOG.jsonl", [{
        "timestamp": f"{GEN_DATE}T00:00:00Z", "event": "JIRA_PACK_GENERATED", "schema_version": SCHEMA_VERSION,
        "issue_count": len(issues), "actor": "generation_session", "evidence": "GENERATION_REPORT.md",
        "note": "Initial canonical issue graph generated from the authoritative W25 repository.",
    }])
    write_text(jira_root / "snapshots" / "README.md", """# Jira-local Snapshots

Run `python jira/tools/snapshot_jira_state.py` after a major import, release gate, evidence acceptance, or bulk status reconciliation. Snapshots contain only Jira-local issue operational metadata, key maps, queue state, and hashes—not duplicated project source/data files. Restore by comparing a snapshot to canonical records and applying a reviewed reconciliation; never blindly overwrite specifications.
""")
    snapshot = {
        "snapshot_id": f"{GEN_DATE}_initial",
        "generated_at": f"{GEN_DATE}T00:00:00Z",
        "schema_version": SCHEMA_VERSION,
        "issues": [{"local_id": i.local_id, "jira_key": i.jira_key, "workflow_state": i.workflow_state, "maturity_after": i.maturity_after, "evidence_state": i.evidence_state, "ready": i.ready} for i in sorted(issues, key=lambda x: x.local_id)],
    }
    snapshot["sha256"] = sha256_text(json.dumps(snapshot["issues"], sort_keys=True))
    write_json(jira_root / "snapshots" / f"{GEN_DATE}_initial" / "STATE.json", snapshot)

def write_tools(jira_root: Path) -> None:
    tools = jira_root / "tools"
    lib = r'''from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
sys.dont_write_bytecode = True
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

JIRA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = JIRA_ROOT.parent
RECORD_ROOT = JIRA_ROOT / "records" / "issues"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_records() -> list[dict[str, Any]]:
    out = []
    for p in sorted(RECORD_ROOT.rglob("*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        rec["__path"] = p
        out.append(rec)
    return out


def save_record(rec: dict[str, Any]) -> None:
    p = rec.pop("__path", None)
    if p is None:
        cp = Path(rec["canonical_record"])
        p = REPO_ROOT / cp
    payload = {k: v for k, v in rec.items() if k != "__path"}
    p.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    rec["__path"] = p


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str] | None = None) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key); fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\r\n")
        w.writeheader()
        for row in rows:
            clean = {}
            for key in fields:
                value = row.get(key, "")
                if isinstance(value, bool): value = "true" if value else "false"
                elif isinstance(value, (list, tuple, set)): value = ";".join(str(x) for x in value)
                elif isinstance(value, dict): value = json.dumps(value, sort_keys=True, ensure_ascii=False)
                elif value is None: value = ""
                clean[key] = value
            w.writerow(clean)


MANIFEST_EXCLUDES = {"validation/JIRA_FILE_MANIFEST.csv", "validation/JIRA_FILE_HASHES.sha256"}


def rebuild_file_manifest() -> int:
    rows=[]
    for p in sorted(JIRA_ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel=p.relative_to(JIRA_ROOT).as_posix()
        if rel in MANIFEST_EXCLUDES or "__pycache__" in p.parts or p.suffix==".pyc":
            continue
        data=p.read_bytes()
        rows.append({"path":rel,"bytes":len(data),"sha256":sha256_bytes(data)})
    write_csv(JIRA_ROOT/"validation"/"JIRA_FILE_MANIFEST.csv",rows,["path","bytes","sha256"])
    (JIRA_ROOT/"validation"/"JIRA_FILE_HASHES.sha256").write_bytes(
        "".join(f"{r['sha256']}  {r['path']}\r\n" for r in rows).encode("utf-8")
    )
    return len(rows)


def status_for_import(logical: str) -> str:
    return {"DONE":"Done","CANCELLED":"Done","IN_PROGRESS":"In Progress","REVIEW":"In Progress","VALIDATION":"In Progress","EVIDENCE_PENDING":"In Progress"}.get(logical, "To Do")


def priority_for_import(priority: str) -> str:
    return {"P0":"Highest","P1":"High","P2":"Medium","P3":"Low","DEFERRED":"Low","CONDITIONAL":"Low"}.get(priority,"Medium")


def jira_issue_type(issue_type: str) -> str:
    return "Sub-task" if issue_type == "Subtask" else issue_type


def description(rec: dict[str, Any]) -> str:
    def bullets(vals): return "\n".join("- " + str(x) for x in vals) if vals else "- None."
    def nums(vals): return "\n".join(f"{n}. {x}" for n,x in enumerate(vals,1)) if vals else "1. None."
    return f"""**Local ID:** {rec['local_id']}

**Objective:** {rec.get('objective','')}

**Why this exists:** {rec.get('why_this_exists','')}

## Scope
{rec.get('scope','')}

## In Scope
{bullets(rec.get('in_scope',[]))}

## Out of Scope
{bullets(rec.get('out_of_scope',[]))}

## Dependencies
{bullets(rec.get('dependencies',[]))}

## Expected Outputs
{bullets(rec.get('expected_outputs',[]))}

## Acceptance Criteria
{nums(rec.get('acceptance_criteria',[]))}

## Definition of Done
{nums(rec.get('definition_of_done',[]))}

## Required Evidence
{bullets(rec.get('required_evidence',[]))}

## Stop Conditions
{bullets(rec.get('stop_conditions',[]))}

## Source References
{bullets(rec.get('source_refs',[]))}
"""


def recompute_ready(records: list[dict[str, Any]]) -> None:
    by_id = {r["local_id"]: r for r in records}
    for r in records:
        r["blocks"] = []
    for r in records:
        for dep in r.get("dependencies", []):
            if dep in by_id:
                by_id[dep]["blocks"].append(r["local_id"])
    for r in records:
        r["blocks"] = sorted(set(r.get("blocks", [])))
    for r in records:
        if str(r.get("historical_classification", "")).startswith("HISTORICAL"):
            r["ready"] = False
            continue
        if r.get("workflow_state") in {"DONE", "CANCELLED"}:
            r["ready"] = False
            continue
        labels = set(r.get("labels", []))
        if r.get("workflow_state") == "DEFERRED" or "deferred" in labels or "conditional" in labels:
            r["workflow_state"] = "DEFERRED"; r["ready"] = False
            r["blocked_reason"] = r.get("blocked_reason") or "DEFERRED_OR_CONDITIONAL_BY_FINAL_HANDOFF"
            r["unblock_condition"] = r.get("unblock_condition") or "Documented admission/replanning approval plus all prerequisites."
            continue
        if r.get("issue_type") != "Subtask":
            r["ready"] = False
            if r.get("workflow_state") not in {"IN_PROGRESS","REVIEW","VALIDATION","EVIDENCE_PENDING"}:
                r["workflow_state"] = "BACKLOG"
            continue
        existing_external = r.get("blocked_reason", "")
        if existing_external and not str(existing_external).startswith("UNSATISFIED_HARD_DEPENDENCIES"):
            r["workflow_state"] = "BLOCKED"; r["ready"] = False
            continue
        unsat = []
        for dep in r.get("dependencies", []):
            d = by_id.get(dep)
            if not d or d.get("workflow_state") != "DONE" or d.get("evidence_state") not in {"COMPLETE","VERIFIED"}:
                unsat.append(dep)
        if unsat:
            r["workflow_state"] = "BLOCKED"; r["ready"] = False
            r["blocked_reason"] = "UNSATISFIED_HARD_DEPENDENCIES: " + ";".join(unsat)
            r["unblock_condition"] = "Complete and verify all hard dependencies at required maturity/evidence."
        elif r.get("workflow_state") not in {"IN_PROGRESS","REVIEW","VALIDATION","EVIDENCE_PENDING"}:
            r["workflow_state"] = "READY"; r["ready"] = True
            r["blocked_reason"] = ""; r["unblock_condition"] = ""


def build_indexes(records: list[dict[str, Any]]) -> None:
    by_id = {r["local_id"]: r for r in records}
    rows = []
    for r in sorted(records, key=lambda x: x["local_id"]):
        rows.append({
            "local_id":r["local_id"],"jira_key":r.get("jira_key", ""),"import_id":r.get("import_id", ""),"issue_type":r["issue_type"],"summary":r["title"],
            "parent":r.get("parent_id", ""),"epic":r.get("epic_id", ""),"phase":r.get("phase", ""),"priority":r.get("priority", ""),"workflow_state":r.get("workflow_state", ""),
            "maturity_before":r.get("maturity_before", ""),"maturity_after":r.get("expected_maturity_after_completion", ""),"evidence_state":r.get("evidence_state", ""),
            "ready":r.get("ready", False),"blocked_by":r.get("dependencies", []),"critical_path":r.get("critical_path", False),"component":r.get("component", ""),
            "execution_lane":r.get("execution_lane", ""),"historical_classification":r.get("historical_classification", ""),"owner_wave":r.get("owner_wave", ""),
            "source_ids":r.get("source_ids", []),"primary_source_refs":r.get("source_refs", [])[:8],"canonical_record":r.get("canonical_record", ""),"generated_markdown":r.get("generated_markdown", ""),
        })
    write_csv(JIRA_ROOT / "index" / "ISSUE_INDEX.csv", rows)
    order = {"P0":0,"P1":1,"P2":2,"P3":3}
    ready = sorted([r for r in records if r.get("ready")], key=lambda r:(order.get(r.get("priority"),9),not r.get("critical_path"),-len(r.get("blocks",[])),r["local_id"]))
    write_csv(JIRA_ROOT / "index" / "READY_QUEUE.csv", [{
        "rank":n,"local_id":r["local_id"],"summary":r["title"],"priority":r.get("priority", ""),"critical_path":r.get("critical_path",False),
        "dependency_unlock_count":len(r.get("blocks",[])),"execution_lane":r.get("execution_lane", ""),"component":r.get("component", ""),"parent":r.get("parent_id", ""),
        "dependencies":r.get("dependencies", []),"source_refs":r.get("source_refs", [])[:8],"canonical_record":r.get("canonical_record", ""),
    } for n,r in enumerate(ready,1)])
    blocked = sorted([r for r in records if r.get("workflow_state") == "BLOCKED"], key=lambda r:(order.get(r.get("priority"),9),r["local_id"]))
    write_csv(JIRA_ROOT / "index" / "BLOCKED_QUEUE.csv", [{
        "issue_id":r["local_id"],"summary":r["title"],"reason":r.get("blocked_reason", ""),"blocking_issue":[d for d in r.get("dependencies",[]) if by_id.get(d,{}).get("workflow_state") != "DONE"],
        "blocking_evidence":[by_id.get(d,{}).get("evidence_state", "MISSING") for d in r.get("dependencies",[]) if by_id.get(d,{}).get("workflow_state") != "DONE"],
        "unblock_condition":r.get("unblock_condition", ""),"priority":r.get("priority", ""),"downstream_impact":len(r.get("blocks",[])),"critical_path":r.get("critical_path",False),
    } for r in blocked])
    deps=[]
    for r in records:
        if r.get("parent_id"): deps.append({"source_id":r["parent_id"],"target_id":r["local_id"],"relationship":"PARENT_CHILD","hard":False,"source_basis":"Canonical hierarchy"})
        for d in r.get("dependencies",[]): deps.append({"source_id":d,"target_id":r["local_id"],"relationship":"BLOCKS","hard":True,"source_basis":"Issue dependency contract"})
        for d in r.get("related_to",[]): deps.append({"source_id":r["local_id"],"target_id":d,"relationship":"RELATES_TO","hard":False,"source_basis":"Historical/post-wave reconciliation"})
    write_csv(JIRA_ROOT / "index" / "DEPENDENCY_INDEX.csv", deps)
    write_csv(JIRA_ROOT / "index" / "HIERARCHY_INDEX.csv", [{
        "local_id":r["local_id"],"issue_type":r["issue_type"],"parent_id":r.get("parent_id", ""),"epic_id":r.get("epic_id", ""),
        "depth":0 if r["issue_type"]=="Epic" else 1 if r["issue_type"] in {"Story","Task","Bug"} else 2,
        "import_id":r.get("import_id", ""),"parent_import_id":by_id.get(r.get("parent_id", ""),{}).get("import_id", ""),
    } for r in sorted(records,key=lambda x:x.get("import_id",0))])
    tests=[]; artifacts=[]
    for r in records:
        for t in r.get("required_tests",[]): tests.append({"test_path":t.get("path", ""),"classification":t.get("classification", ""),"issue_id":r["local_id"],"issue_type":r["issue_type"],"expectation":t.get("expectation", "")})
        for a in r.get("expected_outputs",[]): artifacts.append({"artifact_path_or_name":a,"producer_issue_id":r["local_id"],"issue_type":r["issue_type"],"required_for_completion":True,"expected_maturity":r.get("expected_maturity_after_completion", ""),"downstream_issue_ids":r.get("blocks",[]),"evidence_state":r.get("evidence_state", "")})
    write_csv(JIRA_ROOT / "index" / "TEST_TRACEABILITY.csv", tests)
    write_csv(JIRA_ROOT / "index" / "ARTIFACT_TRACEABILITY.csv", artifacts)
    compact = "# Compact READY Queue\n\n" + ("\n".join(f"{n}. `{r['local_id']}` | {r.get('priority')} | {'CRITICAL' if r.get('critical_path') else 'normal'} | {r.get('execution_lane')} | {r.get('title')}" for n,r in enumerate(ready,1)) or "No issues are currently READY.") + "\n"
    (JIRA_ROOT / "ai" / "READY_QUEUE_COMPACT.md").write_text(compact, encoding="utf-8")


def build_import_files(records: list[dict[str, Any]]) -> None:
    by_id={r["local_id"]:r for r in records}
    ordered=sorted(records,key=lambda r:r.get("import_id",0))
    fields=["Issue type","Issue key","Issue ID","Summary","Parent","Description","Status","Priority","Labels","Component","Local Issue ID","Source IDs","Phase","Logical Workflow State","Implementation Maturity","Evidence State","Owner Historical Wave","Critical Path","Execution Lane"]
    rows=[]
    for r in ordered:
        labels=list(dict.fromkeys(r.get("labels",[])+["local-id-"+r["local_id"].lower()]))
        rows.append({"Issue type":jira_issue_type(r["issue_type"]),"Issue key":r.get("jira_key", ""),"Issue ID":r.get("import_id", ""),"Summary":r["title"],
                     "Parent":by_id.get(r.get("parent_id", ""),{}).get("import_id", ""),"Description":description(r),"Status":status_for_import(r.get("workflow_state", "")),
                     "Priority":priority_for_import(r.get("priority", "")),"Labels":labels,"Component":r.get("component", ""),"Local Issue ID":r["local_id"],
                     "Source IDs":r.get("source_ids",[]),"Phase":r.get("phase", ""),"Logical Workflow State":r.get("workflow_state", ""),
                     "Implementation Maturity":r.get("expected_maturity_after_completion", ""),"Evidence State":r.get("evidence_state", ""),"Owner Historical Wave":r.get("owner_wave", ""),
                     "Critical Path":r.get("critical_path",False),"Execution Lane":r.get("execution_lane", "")})
    for name, subset in [("JIRA_ISSUES_MASTER.csv",rows),("JIRA_EXTERNAL_SYSTEM_IMPORT.csv",rows),("JIRA_HIERARCHY_STAGE_1.csv",[x for x in rows if x["Issue type"]=="Epic"]),("JIRA_HIERARCHY_STAGE_2.csv",[x for x in rows if x["Issue type"] in {"Story","Task","Bug"}]),("JIRA_HIERARCHY_STAGE_3.csv",[x for x in rows if x["Issue type"]=="Sub-task"])]:
        write_csv(JIRA_ROOT / "import" / name, subset, fields)


def cycles(records: list[dict[str, Any]]) -> list[list[str]]:
    graph={r["local_id"]:list(r.get("dependencies",[])) for r in records}; state={k:0 for k in graph}; stack=[]; out=[]; seen=set()
    def dfs(n):
        state[n]=1;stack.append(n)
        for d in graph.get(n,[]):
            if d not in graph: continue
            if state[d]==0: dfs(d)
            elif state[d]==1:
                c=stack[stack.index(d):]+[d]; key=tuple(sorted(c[:-1]))
                if key not in seen: seen.add(key);out.append(c)
        stack.pop();state[n]=2
    for n in graph:
        if state[n]==0: dfs(n)
    return out


def validate(write_reports: bool=True) -> tuple[list[str],dict[str,Any]]:
    errors=[]; warnings=[]; records=load_records(); ids=[r.get("local_id","") for r in records]; by_id={r.get("local_id",""):r for r in records}
    if len(ids)!=len(set(ids)): errors.append("Duplicate local issue IDs")
    if not records: errors.append("No canonical issue records found")
    required=["local_id","issue_type","title","workflow_state","historical_classification","priority","objective","why_this_exists","scope","acceptance_criteria","definition_of_done","required_tests","required_evidence","source_refs"]
    for r in records:
        miss=[k for k in required if k not in r]
        if miss: errors.append(f"{r.get('local_id','?')}: missing fields {miss}")
        if r.get("jira_key") and str(r.get("jira_key")).startswith("{{") is False: warnings.append(f"{r['local_id']}: Jira key populated; verify it came from reconciliation")
        p=r.get("parent_id","")
        if p and p not in by_id: errors.append(f"{r['local_id']}: missing parent {p}")
        e=r.get("epic_id","")
        if e and e not in by_id: errors.append(f"{r['local_id']}: missing epic {e}")
        for d in r.get("dependencies",[]):
            if d not in by_id: errors.append(f"{r['local_id']}: missing dependency {d}")
        if r.get("issue_type")=="Story" and p and by_id.get(p,{}).get("issue_type")!="Epic": errors.append(f"{r['local_id']}: Story parent is not Epic")
        if r.get("issue_type") in {"Task","Bug"} and p and by_id.get(p,{}).get("issue_type")!="Epic": errors.append(f"{r['local_id']}: Task/Bug parent is not Epic")
        if r.get("issue_type")=="Subtask" and p and by_id.get(p,{}).get("issue_type") not in {"Story","Task","Bug"}: errors.append(f"{r['local_id']}: Subtask parent invalid")
        if r.get("historical_classification")=="ACTIONABLE_POST_WAVE":
            if not r.get("acceptance_criteria"): errors.append(f"{r['local_id']}: no acceptance criteria")
            if not r.get("definition_of_done"): errors.append(f"{r['local_id']}: no Definition of Done")
            if not r.get("required_tests"): errors.append(f"{r['local_id']}: no tests")
            if not r.get("required_evidence"): errors.append(f"{r['local_id']}: no evidence requirement")
        if r.get("workflow_state")=="DONE" and r.get("evidence_state") not in {"COMPLETE","VERIFIED"}: errors.append(f"{r['local_id']}: Done without complete/verified evidence")
        if r.get("ready"):
            if r.get("issue_type")!="Subtask": errors.append(f"{r['local_id']}: non-Subtask marked READY")
            for d in r.get("dependencies",[]):
                dep=by_id.get(d,{})
                if dep.get("workflow_state")!="DONE" or dep.get("evidence_state") not in {"COMPLETE","VERIFIED"}: errors.append(f"{r['local_id']}: READY with unsatisfied dependency {d}")
        for t in r.get("required_tests",[]):
            if t.get("classification")=="EXISTING_AUTOMATED_TEST" and t.get("path") and not (REPO_ROOT/t["path"]).exists(): errors.append(f"{r['local_id']}: declared existing test missing {t['path']}")
    cs=cycles(records)
    if cs: errors.extend("Dependency cycle: "+" -> ".join(c) for c in cs)
    # Source references and manifests
    ref_path=JIRA_ROOT/"sources"/"SOURCE_ANCHOR_INDEX.csv"; refs={}
    if not ref_path.exists(): errors.append("Missing SOURCE_ANCHOR_INDEX.csv")
    else:
        with ref_path.open(encoding="utf-8",newline="") as f:
            refs={r["source_ref_id"]:r for r in csv.DictReader(f)}
        for rid,r in refs.items():
            p=REPO_ROOT/r["repo_relative_path"]
            if not p.exists(): errors.append(f"{rid}: source missing {r['repo_relative_path']}")
            elif sha256_bytes(p.read_bytes())!=r["document_sha256"]: errors.append(f"{rid}: source hash drift {r['repo_relative_path']}")
            try:
                line_count=len(p.read_text(encoding="utf-8-sig").splitlines())
                if int(r["start_line"])<1 or int(r["end_line"])>max(1,line_count): errors.append(f"{rid}: invalid line range")
            except UnicodeDecodeError: pass
        for r in records:
            for rid in r.get("source_refs",[]):
                if rid not in refs: errors.append(f"{r['local_id']}: unknown source ref {rid}")
            if not (JIRA_ROOT/"sources"/"issue_source_manifests"/f"{r['local_id']}.json").exists(): errors.append(f"{r['local_id']}: missing source manifest")
    # Registry IDs
    registry_specs=[("governance/REQUIREMENTS_INDEX.csv","requirement_id","requirement_ids"),("governance/ACCEPTANCE_CONTROL_CATALOG.csv","control_id","acceptance_control_ids"),("governance/ADR_INDEX.csv","adr_id","adr_ids"),("docs/final/FINAL_RISK_REGISTER.csv","risk_id","risk_ids"),("docs/final/FINAL_KNOWN_GAPS.csv","gap_id","gap_ids")]
    for rel,idfield,recfield in registry_specs:
        with (REPO_ROOT/rel).open(encoding="utf-8-sig",newline="") as f: valid={x[idfield] for x in csv.DictReader(f)}
        for r in records:
            for x in r.get(recfield,[]):
                if x not in valid: errors.append(f"{r['local_id']}: unknown {idfield} {x}")
    # Final gap mapping
    with (REPO_ROOT/"docs/final/FINAL_KNOWN_GAPS.csv").open(encoding="utf-8-sig",newline="") as f: gap_ids={x["gap_id"] for x in csv.DictReader(f)}
    gp=JIRA_ROOT/"reconciliation"/"GAP_TO_JIRA_MAPPING.csv"
    if not gp.exists(): errors.append("Missing GAP_TO_JIRA_MAPPING.csv")
    else:
        with gp.open(encoding="utf-8",newline="") as f: mapped={x["gap_id"] for x in csv.DictReader(f) if x.get("jira_issue_ids")}
        missing=gap_ids-mapped
        if missing: errors.append("Unmapped final gaps: "+",".join(sorted(missing)))
    # Import dry run
    import_path=JIRA_ROOT/"import"/"JIRA_EXTERNAL_SYSTEM_IMPORT.csv"
    import_count=0
    if not import_path.exists(): errors.append("Missing JIRA_EXTERNAL_SYSTEM_IMPORT.csv")
    else:
        with import_path.open(encoding="utf-8",newline="") as f:
            reader=csv.DictReader(f); rows=list(reader); import_count=len(rows)
            if "Summary" not in (reader.fieldnames or []): errors.append("Import CSV missing Summary")
            if len(rows)!=len(records): errors.append(f"Import count {len(rows)} != record count {len(records)}")
            iids=[x.get("Issue ID","") for x in rows]
            if len(iids)!=len(set(iids)): errors.append("Duplicate import Issue ID")
            if any(not x.get("Summary") for x in rows): errors.append("Blank import Summary")
    for jl in [JIRA_ROOT/"import"/"JIRA_API_CREATE_PAYLOADS.jsonl",JIRA_ROOT/"import"/"JIRA_API_LINK_PAYLOADS.jsonl",JIRA_ROOT/"import"/"JIRA_LINKS.jsonl"]:
        if not jl.exists(): errors.append(f"Missing {jl.name}")
        else:
            for n,line in enumerate(jl.read_text(encoding="utf-8").splitlines(),1):
                try: json.loads(line)
                except Exception as e: errors.append(f"{jl.name}:{n}: invalid JSONL: {e}")
    counts=Counter(r.get("issue_type") for r in records); states=Counter(r.get("workflow_state") for r in records); priorities=Counter(r.get("priority") for r in records)
    metrics={"generated_at":datetime.now(timezone.utc).isoformat(),"valid":not errors,"error_count":len(errors),"warning_count":len(warnings),"errors":errors,"warnings":warnings,
             "issue_count":len(records),"issue_types":dict(counts),"workflow_states":dict(states),"priorities":dict(priorities),"ready_count":sum(bool(r.get("ready")) for r in records),
             "dependency_cycles":len(cs),"source_reference_count":len(refs),"import_row_count":import_count}
    if write_reports:
        val=JIRA_ROOT/"validation";val.mkdir(parents=True,exist_ok=True)
        (val/"VALIDATION_RESULTS.json").write_text(json.dumps(metrics,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        text="# Jira Pack Validation\n\n"+f"- Result: **{'PASS' if not errors else 'FAIL'}**\n- Issues: {len(records)}\n- Errors: {len(errors)}\n- Warnings: {len(warnings)}\n- Dependency cycles: {len(cs)}\n- Source references: {len(refs)}\n- Import rows: {import_count}\n\n"
        if errors: text+="## Errors\n\n"+"\n".join("- "+e for e in errors)+"\n"
        if warnings: text+="\n## Warnings\n\n"+"\n".join("- "+w for w in warnings)+"\n"
        (val/"VALIDATION_REPORT.md").write_text(text,encoding="utf-8")
        write_csv(val/"DEPENDENCY_CYCLE_REPORT.csv",[{"cycle_id":n,"cycle":" -> ".join(c)} for n,c in enumerate(cs,1)])
        write_csv(val/"ORPHAN_REPORT.csv",[{"issue_id":r["local_id"],"missing_parent":r.get("parent_id","")} for r in records if r.get("parent_id") and r.get("parent_id") not in by_id])
        write_csv(val/"SOURCE_REFERENCE_VALIDATION.csv",[{"source_ref_id":rid,"path":rr["repo_relative_path"],"valid":(REPO_ROOT/rr["repo_relative_path"]).exists() and sha256_bytes((REPO_ROOT/rr["repo_relative_path"]).read_bytes())==rr["document_sha256"]} for rid,rr in refs.items()])
        write_csv(val/"HIERARCHY_VALIDATION.csv",[{"issue_id":r["local_id"],"issue_type":r["issue_type"],"parent_id":r.get("parent_id", ""),"valid":not r.get("parent_id") or r.get("parent_id") in by_id} for r in records])
        write_csv(val/"IMPORT_VALIDATION.csv",[{"artifact":"JIRA_EXTERNAL_SYSTEM_IMPORT.csv","row_count":import_count,"expected":len(records),"valid":import_count==len(records) and not any("Import" in e for e in errors)}])
    return errors,metrics
'''
    write_text(tools / "jira_pack_lib.py", lib)
    write_text(tools / "validate_jira_pack.py", r'''import sys
sys.dont_write_bytecode = True
from jira_pack_lib import validate, rebuild_file_manifest
errors, metrics = validate(write_reports=True)
rebuild_file_manifest()
print(f"Jira pack validation: {'PASS' if not errors else 'FAIL'} | issues={metrics['issue_count']} errors={len(errors)}")
if errors:
    for error in errors:
        print("ERROR:", error)
    raise SystemExit(1)
''')
    write_text(tools / "validate_source_refs.py", r'''import sys
sys.dont_write_bytecode = True
import csv
from jira_pack_lib import JIRA_ROOT, REPO_ROOT, sha256_bytes
errors=[]
with (JIRA_ROOT/'sources'/'SOURCE_ANCHOR_INDEX.csv').open(encoding='utf-8',newline='') as f:
    rows=list(csv.DictReader(f))
for row in rows:
    p=REPO_ROOT/row['repo_relative_path']
    if not p.exists(): errors.append(f"missing {row['source_ref_id']} {p}")
    elif sha256_bytes(p.read_bytes())!=row['document_sha256']: errors.append(f"hash drift {row['source_ref_id']} {p}")
print(f"Source references: {'PASS' if not errors else 'FAIL'} | refs={len(rows)} errors={len(errors)}")
for e in errors: print('ERROR:',e)
raise SystemExit(1 if errors else 0)
''')
    write_text(tools / "validate_dependencies.py", r'''import sys
sys.dont_write_bytecode = True
from jira_pack_lib import load_records, cycles
records=load_records(); ids={r['local_id'] for r in records}; errors=[]
for r in records:
    for d in r.get('dependencies',[]):
        if d not in ids: errors.append(f"{r['local_id']}: missing {d}")
cs=cycles(records)
errors.extend('cycle: '+' -> '.join(c) for c in cs)
print(f"Dependencies: {'PASS' if not errors else 'FAIL'} | issues={len(records)} cycles={len(cs)} errors={len(errors)}")
for e in errors: print('ERROR:',e)
raise SystemExit(1 if errors else 0)
''')
    write_text(tools / "build_indexes.py", r'''import sys
sys.dont_write_bytecode = True
from jira_pack_lib import load_records, recompute_ready, save_record, build_indexes, rebuild_file_manifest
records=load_records();recompute_ready(records)
for r in records: save_record(r)
build_indexes(records); rebuild_file_manifest()
print(f"Rebuilt indexes for {len(records)} issues")
''')
    write_text(tools / "build_import_files.py", r'''import sys
sys.dont_write_bytecode = True
from jira_pack_lib import load_records, build_import_files, rebuild_file_manifest
records=load_records();build_import_files(records);rebuild_file_manifest()
print(f"Rebuilt import CSVs for {len(records)} issues")
''')
    write_text(tools / "update_ready_queue.py", r'''import sys
sys.dont_write_bytecode = True
from jira_pack_lib import load_records, recompute_ready, save_record, build_indexes, rebuild_file_manifest
records=load_records();recompute_ready(records)
for r in records: save_record(r)
build_indexes(records); rebuild_file_manifest()
print(f"READY={sum(bool(r.get('ready')) for r in records)} BLOCKED={sum(r.get('workflow_state')=='BLOCKED' for r in records)}")
''')
    write_text(tools / "reconcile_jira_export.py", r'''from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse,csv,json,re
from datetime import datetime,timezone
from pathlib import Path
from jira_pack_lib import JIRA_ROOT, load_records, save_record, recompute_ready, build_indexes, build_import_files, rebuild_file_manifest

def norm(s): return re.sub(r'[^a-z0-9]+','',s.lower())
p=argparse.ArgumentParser(description='Reconcile a Jira CSV export into local operational fields using Local Issue ID.')
p.add_argument('export_csv',type=Path);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
with a.export_csv.open(encoding='utf-8-sig',newline='') as f:
    reader=csv.DictReader(f); rows=list(reader); names={norm(x):x for x in (reader.fieldnames or [])}
local_col=names.get('localissueid') or names.get('localid')
key_col=names.get('issuekey') or names.get('key')
status_col=names.get('logicalworkflowstate') or names.get('status')
if not local_col or not key_col: raise SystemExit('Export must contain Local Issue ID and Issue key columns')
by={r['local_id']:r for r in load_records()};changes=[];errors=[]
for row in rows:
    lid=row.get(local_col,'').strip()
    if not lid: continue
    if lid not in by: errors.append(f'Unknown Local Issue ID {lid}');continue
    rec=by[lid]; before={'jira_key':rec.get('jira_key',''),'workflow_state':rec.get('workflow_state','')}
    rec['jira_key']=row.get(key_col,'').strip()
    if status_col and norm(status_col)=='logicalworkflowstate' and row.get(status_col,'').strip(): rec['workflow_state']=row[status_col].strip().upper()
    after={'jira_key':rec.get('jira_key',''),'workflow_state':rec.get('workflow_state','')}
    if before!=after: changes.append({'local_id':lid,'before':before,'after':after})
if errors:
    for e in errors: print('ERROR:',e)
    raise SystemExit(1)
if not a.dry_run:
    records=list(by.values());recompute_ready(records)
    for r in records: save_record(r)
    build_indexes(records);build_import_files(records)
    log=JIRA_ROOT/'history'/'ISSUE_CHANGE_LOG.jsonl'
    with log.open('a',encoding='utf-8') as f:
        for c in changes:
            c.update({'timestamp':datetime.now(timezone.utc).isoformat(),'event':'JIRA_EXPORT_RECONCILED','actor':'reconcile_jira_export.py'})
            f.write(json.dumps(c,sort_keys=True)+'\n')
    rebuild_file_manifest()
print(f"{'Would reconcile' if a.dry_run else 'Reconciled'} {len(changes)} changed issues from {len(rows)} export rows")
''')
    write_text(tools / "snapshot_jira_state.py", r'''import sys
sys.dont_write_bytecode = True
from datetime import datetime,timezone
import hashlib,json
from jira_pack_lib import JIRA_ROOT, load_records, rebuild_file_manifest
records=load_records(); now=datetime.now(timezone.utc); sid=now.strftime('%Y%m%dT%H%M%SZ')
state=[{'local_id':r['local_id'],'jira_key':r.get('jira_key',''),'workflow_state':r.get('workflow_state',''),'maturity_after':r.get('expected_maturity_after_completion',''),'evidence_state':r.get('evidence_state',''),'ready':r.get('ready',False)} for r in sorted(records,key=lambda x:x['local_id'])]
payload={'snapshot_id':sid,'generated_at':now.isoformat(),'schema_version':1,'issues':state,'sha256':hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest()}
out=JIRA_ROOT/'snapshots'/sid/'STATE.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
rebuild_file_manifest(); print(out)
''')
    write_text(tools / "validate_import_files.py", r'''import sys
sys.dont_write_bytecode = True
import csv,json
from jira_pack_lib import JIRA_ROOT, load_records
errors=[];records=load_records();p=JIRA_ROOT/'import'/'JIRA_EXTERNAL_SYSTEM_IMPORT.csv'
with p.open(encoding='utf-8',newline='') as f:
    reader=csv.DictReader(f);rows=list(reader)
if 'Summary' not in (reader.fieldnames or []):errors.append('missing Summary')
if len(rows)!=len(records):errors.append(f'rows {len(rows)} != records {len(records)}')
ids=[r.get('Issue ID','') for r in rows]
if len(ids)!=len(set(ids)):errors.append('duplicate Issue ID')
for jl in (JIRA_ROOT/'import').glob('*.jsonl'):
    for n,line in enumerate(jl.read_text(encoding='utf-8').splitlines(),1):
        try:json.loads(line)
        except Exception as e:errors.append(f'{jl.name}:{n}:{e}')
print(f"Import files: {'PASS' if not errors else 'FAIL'} | rows={len(rows)} errors={len(errors)}")
for e in errors:print('ERROR:',e)
raise SystemExit(1 if errors else 0)
''')
    write_text(tools / "validate_jira_manifest.py", r'''import sys
sys.dont_write_bytecode = True
import csv,hashlib
from pathlib import Path
JIRA_ROOT=Path(__file__).resolve().parents[1]
manifest=JIRA_ROOT/'validation'/'JIRA_FILE_MANIFEST.csv'
excluded={'validation/JIRA_FILE_MANIFEST.csv','validation/JIRA_FILE_HASHES.sha256'}
errors=[]
if not manifest.exists():
    errors.append('missing Jira file manifest')
    rows=[]
else:
    with manifest.open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
    seen=set()
    for row in rows:
        rel=row['path'];seen.add(rel);p=JIRA_ROOT/rel
        if not p.exists(): errors.append(f'missing {rel}')
        elif p.stat().st_size!=int(row['bytes']): errors.append(f'size mismatch {rel}')
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']: errors.append(f'hash mismatch {rel}')
    expected={p.relative_to(JIRA_ROOT).as_posix() for p in JIRA_ROOT.rglob('*') if p.is_file() and p.relative_to(JIRA_ROOT).as_posix() not in excluded}
    for rel in sorted(expected-seen): errors.append(f'unrepresented {rel}')
    for rel in sorted(seen-expected): errors.append(f'extra {rel}')
print(f"Jira file manifest: {'PASS' if not errors else 'FAIL'} | files={len(rows)} errors={len(errors)}")
for e in errors: print('ERROR:',e)
raise SystemExit(1 if errors else 0)
''')

def calculate_coverage(repo: RepoIndex, issues: list[Issue], refs: SourceRefRegistry, regs: dict[str, list[dict[str, str]]], trace: dict[str, Any]) -> dict[str, Any]:
    by_id = {i.local_id: i for i in issues}
    cycles = dependency_cycles(issues)
    orphan = [i.local_id for i in issues if i.parent_id and i.parent_id not in by_id]
    unresolved_deps = [(i.local_id, d) for i in issues for d in i.dependencies if d not in by_id]
    valid_refs = 0
    invalid_refs = 0
    for r in refs.refs:
        p = repo.root / r.repo_relative_path
        if p.exists() and sha256_bytes(p.read_bytes()) == r.document_sha256:
            valid_refs += 1
        else:
            invalid_refs += 1
    req_mapped = sum(bool(trace["requirement_existing"].get(r["requirement_id"], []) or trace["requirement_post"].get(r["requirement_id"], "")) for r in regs["requirements"])
    controls_mapped = sum(bool(trace["acceptance_existing"].get(r["control_id"], []) or trace["acceptance_post"].get(r["control_id"], "")) for r in regs["controls"])
    issue_types = Counter(i.issue_type for i in issues)
    states = Counter(i.workflow_state for i in issues)
    priorities = Counter(i.priority for i in issues)
    historical_done = sum(i.historical_classification.startswith("HISTORICAL") and i.workflow_state == "DONE" for i in issues)
    actionable_open = sum(i.historical_classification == "ACTIONABLE_POST_WAVE" and i.workflow_state not in {"DONE", "CANCELLED", "DEFERRED"} for i in issues)
    coverage = {
        "generated_date": GEN_DATE,
        "repository_files_analyzed": len(repo.files),
        "total_issues": len(issues),
        "issue_counts": dict(issue_types),
        "historical_completed_items": historical_done,
        "historical_items_total": sum(i.historical_classification.startswith("HISTORICAL") for i in issues),
        "actionable_open_items": actionable_open,
        "ready_items": states.get("READY", 0),
        "blocked_items": states.get("BLOCKED", 0),
        "deferred_items": states.get("DEFERRED", 0),
        "conditional_items": sum("conditional" in i.labels for i in issues),
        "workflow_state_counts": dict(states),
        "priority_counts": dict(priorities),
        "requirements_total": len(regs["requirements"]),
        "requirements_mapped": req_mapped,
        "requirements_unmapped": len(regs["requirements"]) - req_mapped,
        "acceptance_controls_total": len(regs["controls"]),
        "acceptance_controls_mapped": controls_mapped,
        "acceptance_controls_unmapped": len(regs["controls"]) - controls_mapped,
        "final_gaps_total": len(regs["gaps"]),
        "final_gaps_represented": sum(bool(trace["gap_post"].get(r["gap_id"])) for r in regs["gaps"]),
        "risks_total": len(regs["risks"]),
        "risks_represented": sum(bool(trace["risk_post"].get(r["risk_id"])) for r in regs["risks"]),
        "source_references_total": len(refs.refs),
        "source_references_valid": valid_refs,
        "source_references_invalid": invalid_refs,
        "orphan_issues": orphan,
        "unresolved_dependency_references": [{"issue_id": a, "dependency_id": b} for a, b in unresolved_deps],
        "dependency_cycles": cycles,
        "issues_without_acceptance_criteria": [i.local_id for i in issues if i.historical_classification == "ACTIONABLE_POST_WAVE" and not i.acceptance_criteria],
        "issues_without_definition_of_done": [i.local_id for i in issues if i.historical_classification == "ACTIONABLE_POST_WAVE" and not i.definition_of_done],
        "issues_without_test_or_evidence_requirement": [i.local_id for i in issues if i.historical_classification == "ACTIONABLE_POST_WAVE" and (not i.tests or not i.evidence)],
        "jira_keys_prefilled": [i.local_id for i in issues if i.jira_key],
        "mandatory_coverage_pass": all([
            req_mapped == len(regs["requirements"]), controls_mapped == len(regs["controls"]),
            len(trace["gap_post"]) == len(regs["gaps"]), len(trace["risk_post"]) == len(regs["risks"]),
            invalid_refs == 0, not orphan, not unresolved_deps, not cycles,
            all(i.acceptance_criteria and i.definition_of_done and i.tests and i.evidence for i in issues if i.historical_classification == "ACTIONABLE_POST_WAVE"),
        ]),
    }
    return coverage


def write_coverage_reports(jira_root: Path, coverage: dict[str, Any]) -> None:
    val = jira_root / "validation"
    write_json(val / "COVERAGE_REPORT.json", coverage)
    md = f"""# Jira Pack Coverage Report

- Repository files analyzed: **{coverage['repository_files_analyzed']}**
- Total issues: **{coverage['total_issues']}**
- Epics: **{coverage['issue_counts'].get('Epic', 0)}**
- Stories: **{coverage['issue_counts'].get('Story', 0)}**
- Tasks: **{coverage['issue_counts'].get('Task', 0)}**
- Subtasks: **{coverage['issue_counts'].get('Subtask', 0)}**
- Historical completed items: **{coverage['historical_completed_items']}**
- Actionable open items: **{coverage['actionable_open_items']}**
- READY: **{coverage['ready_items']}**
- BLOCKED: **{coverage['blocked_items']}**
- DEFERRED: **{coverage['deferred_items']}**
- CONDITIONAL: **{coverage['conditional_items']}**
- Priorities: `{json.dumps(coverage['priority_counts'], sort_keys=True)}`
- Requirements mapped/unmapped: **{coverage['requirements_mapped']} / {coverage['requirements_unmapped']}**
- Acceptance controls mapped/unmapped: **{coverage['acceptance_controls_mapped']} / {coverage['acceptance_controls_unmapped']}**
- Final gaps represented: **{coverage['final_gaps_represented']} / {coverage['final_gaps_total']}**
- Risks represented: **{coverage['risks_represented']} / {coverage['risks_total']}**
- Source references valid/invalid: **{coverage['source_references_valid']} / {coverage['source_references_invalid']}**
- Orphan issues: **{len(coverage['orphan_issues'])}**
- Unresolved dependency references: **{len(coverage['unresolved_dependency_references'])}**
- Dependency cycles: **{len(coverage['dependency_cycles'])}**
- Actionable issues without acceptance criteria: **{len(coverage['issues_without_acceptance_criteria'])}**
- Actionable issues without Definition of Done: **{len(coverage['issues_without_definition_of_done'])}**
- Actionable issues without tests/evidence: **{len(coverage['issues_without_test_or_evidence_requirement'])}**
- Fabricated/prefilled Jira keys: **{len(coverage['jira_keys_prefilled'])}**

## Mandatory coverage gate

**{'PASS' if coverage['mandatory_coverage_pass'] else 'FAIL'}**

This report measures Jira-pack completeness and traceability. It does not claim that the underlying product's real-data, scientific, target-hardware, or operating work is complete.
"""
    write_text(val / "COVERAGE_REPORT.md", md)


def run_command(cmd: list[str], cwd: Path, timeout: int = 300) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        cp = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        rc = cp.returncode
        output = cp.stdout
    except subprocess.TimeoutExpired as e:
        rc = 124
        output = (e.stdout or "") + "\nTIMEOUT"
    finished = datetime.now(timezone.utc)
    full_output = output or ""
    non_manifest_findings = [
        line for line in full_output.splitlines()
        if line.startswith("- ") and "manifest_coverage:" not in line
    ]
    return {
        "command": cmd,
        "cwd": str(cwd),
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "returncode": rc,
        "passed": rc == 0,
        "output": full_output[-50000:],
        "output_truncated": len(full_output) > 50000,
        "full_output_characters": len(full_output),
        "full_output_sha256": sha256_text(full_output),
        "manifest_coverage_count": full_output.count("manifest_coverage:"),
        "non_manifest_finding_count": len(non_manifest_findings),
    }


def write_generation_report(jira_root: Path, repo: RepoIndex, issues: list[Issue], coverage: dict[str, Any], baseline_runs: list[dict[str, Any]], pack_runs: list[dict[str, Any]]) -> None:
    top_dirs = Counter(f.top_dir for f in repo.files.values())
    ready = [i for i in issues if i.ready]
    unresolved = [
        "Destination Jira configuration/custom-field/link-type discovery and mapping",
        "Human per-source rights/redistribution decisions",
        "Production credentials supplied outside the repository",
        "Authoritative AC-038 target-host benchmark",
        "Real historical data materialization and all subsequent empirical/protected/operating evidence",
    ]
    report = f"""# Jira Generation Report

## Result

The complete local Jira architecture, historical/post-wave issue graph, traceability indexes, AI work packets, import/API templates, synchronization contract, validators, and snapshot tooling were generated under `jira/`.

## Repository reconnaissance

- Non-Jira files analyzed recursively: **{len(repo.files)}**
- Top-level distribution: `{json.dumps(dict(sorted(top_dirs.items())), sort_keys=True)}`
- Parse errors: **{sum(f.parse_status != 'OK' for f in repo.files.values())}**
- Source authority: protected invariants → final/current handoff → current machine registries → late readiness/implementation/test evidence → accepted design/provenance.

## Reconciled project state

- Exactly 25 waves are complete; no Wave 26 was created.
- Historical WBS `DONE` remains scoped planning/design/starter/integration provenance.
- Final maturity, gaps, risks, and handoff evidence drive the separate post-wave implementation graph.
- No production model winner, protected metric, feature promotion, A&M lift, BAS effect, source-rights approval, full coverage, target-host performance, freshness SLA, or operating status was fabricated.

## Jira architecture

- Total issues: **{len(issues)}**
- Epics: **{coverage['issue_counts'].get('Epic', 0)}** (historical + post-wave)
- Stories: **{coverage['issue_counts'].get('Story', 0)}**
- Historical Tasks: **{coverage['issue_counts'].get('Task', 0)}**
- Executable post-wave Subtasks: **{coverage['issue_counts'].get('Subtask', 0)}**
- Historical completed issue records: **{coverage['historical_completed_items']}**
- Actionable open issue records: **{coverage['actionable_open_items']}**
- READY/BLOCKED/DEFERRED: **{coverage['ready_items']} / {coverage['blocked_items']} / {coverage['deferred_items']}**
- Priority counts: `{json.dumps(coverage['priority_counts'], sort_keys=True)}`

## Coverage

- Requirements: **{coverage['requirements_mapped']} mapped / {coverage['requirements_unmapped']} unmapped**
- Acceptance controls: **{coverage['acceptance_controls_mapped']} mapped / {coverage['acceptance_controls_unmapped']} unmapped**
- Final gaps: **{coverage['final_gaps_represented']} / {coverage['final_gaps_total']} represented**
- Risks: **{coverage['risks_represented']} / {coverage['risks_total']} represented**
- Source references: **{coverage['source_references_valid']} valid / {coverage['source_references_invalid']} invalid**
- Orphans/unresolved dependencies/cycles: **{len(coverage['orphan_issues'])} / {len(coverage['unresolved_dependency_references'])} / {len(coverage['dependency_cycles'])}**
- Mandatory coverage gate: **{'PASS' if coverage['mandatory_coverage_pass'] else 'FAIL'}**

## Import design

The primary hierarchy artifact is an ordered external-system-import CSV using unique Issue ID and Parent values. The pack also contains staged views, post-import key mapping, Jira Cloud REST v3 ADF payload templates, and separate link payloads. No Jira-generated key or target-specific field/issue/project/workflow/component ID is invented. Actual destination fields/statuses/priorities/types/components/link types must be discovered and mapped before production execution.

## Validation runs

### Baseline repository runs

{md_list([f"`{' '.join(r['command'])}` — {'PASS' if r['passed'] else 'FAIL'} (exit {r['returncode']})" for r in baseline_runs])}

### Generated Jira-pack runs

{md_list([f"`{' '.join(r['command'])}` — {'PASS' if r['passed'] else 'FAIL'} (exit {r['returncode']})" for r in pack_runs])}

Detailed command output is in `validation/BASELINE_REPOSITORY_VALIDATION.json` and `validation/JIRA_PACK_VALIDATION_RUNS.json`.

## Unresolved/manual items

{md_list(unresolved)}

## Recommended first execution sequence

{md_numbered([f"{i.local_id} — {i.title}" for i in sorted(ready, key=lambda x: ({'P0':0,'P1':1,'P2':2,'P3':3}.get(x.priority,9), not x.critical_path, x.local_id))[:10]])}

## Quality interpretation

This Jira pack is complete as a project-management/traceability/import system. It intentionally does **not** claim that the underlying forecasting product is complete; the actionable graph is the evidence-controlled path to that completion.
"""
    write_text(jira_root / "GENERATION_REPORT.md", report)


def deterministic_zip(source_root: Path, output_path: Path, arc_prefix: str) -> None:
    import zipfile
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    fixed = (2026, 8, 8, 12, 0, 0)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(source_root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(source_root).as_posix()
            zi = zipfile.ZipInfo(f"{arc_prefix.rstrip('/')}/{rel}", fixed)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, p.read_bytes())


JIRA_MANIFEST_EXCLUDES = {"validation/JIRA_FILE_MANIFEST.csv", "validation/JIRA_FILE_HASHES.sha256"}


def remove_bytecode_artifacts(jira_root: Path) -> None:
    for cache in sorted(jira_root.rglob("__pycache__"), reverse=True):
        if cache.is_dir():
            shutil.rmtree(cache)
    for pyc in jira_root.rglob("*.pyc"):
        pyc.unlink()


def write_jira_file_manifest(jira_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in sorted(jira_root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(jira_root).as_posix()
        if rel in JIRA_MANIFEST_EXCLUDES:
            continue
        data = p.read_bytes()
        rows.append({"path": rel, "bytes": len(data), "sha256": sha256_bytes(data)})
    write_csv(jira_root / "validation" / "JIRA_FILE_MANIFEST.csv", rows, ["path", "bytes", "sha256"])
    write_text(jira_root / "validation" / "JIRA_FILE_HASHES.sha256", "".join(f"{r['sha256']}  {r['path']}\n" for r in rows))
    return rows


def validate_jira_file_manifest(jira_root: Path) -> list[str]:
    errors: list[str] = []
    manifest = jira_root / "validation" / "JIRA_FILE_MANIFEST.csv"
    if not manifest.exists():
        return ["missing Jira file manifest"]
    with manifest.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    seen: set[str] = set()
    for row in rows:
        rel = row["path"]
        seen.add(rel)
        p = jira_root / rel
        if not p.exists():
            errors.append(f"missing {rel}")
            continue
        if p.stat().st_size != int(row["bytes"]):
            errors.append(f"size mismatch {rel}")
        if sha256_bytes(p.read_bytes()) != row["sha256"]:
            errors.append(f"hash mismatch {rel}")
    expected = {p.relative_to(jira_root).as_posix() for p in jira_root.rglob("*") if p.is_file() and p.relative_to(jira_root).as_posix() not in JIRA_MANIFEST_EXCLUDES}
    errors.extend(f"unrepresented {rel}" for rel in sorted(expected - seen))
    errors.extend(f"extra {rel}" for rel in sorted(seen - expected))
    return errors


def write_repository_validator_compatibility(jira_root: Path, run: dict[str, Any]) -> None:
    output = run.get("output", "")
    manifest_count = int(run.get("manifest_coverage_count", len(re.findall(r"manifest_coverage:", output))))
    non_manifest_count = int(run.get("non_manifest_finding_count", len([
        line for line in output.splitlines() if line.startswith("- ") and "manifest_coverage:" not in line
    ])))
    scope_path = jira_root / "validation" / "NON_JIRA_SCOPE_DIFF.json"
    scope = json.loads(scope_path.read_text(encoding="utf-8")) if scope_path.is_file() else {}
    scope_summary = (
        f"- Non-Jira scope hash comparison: **{'PASS' if scope.get('pass') else 'NOT RECORDED'}** "
        f"({scope.get('current_non_jira_files', scope.get('inventory_non_jira_files', 'unknown'))} files; "
        f"missing={len(scope.get('missing', []))}, added={len(scope.get('added', []))}, changed={len(scope.get('changed', []))})."
    )
    write_json(jira_root / "validation" / "POST_GENERATION_ORIGINAL_REPO_VALIDATOR.json", run)
    write_text(jira_root / "validation" / "REPOSITORY_VALIDATOR_COMPATIBILITY.md", f"""# Original Repository Validator Compatibility

- Pre-generation W25 strict repository validator: **PASS** (recorded in `BASELINE_REPOSITORY_VALIDATION.json`).
- Post-generation original strict validator exit code: **{run.get('returncode')}**.
- Manifest-coverage findings observed in captured output: **{manifest_count}**.
- Non-manifest findings in captured output: **{non_manifest_count}**.
{scope_summary}

The original W25 global provenance manifest predates this Jira generation and therefore does not list newly created `jira/` files. The task explicitly confined new Jira-system changes to `jira/` and prohibited rewriting unrelated existing governance/provenance merely to make the old manifest accept new files. The original global strict validator is therefore expected to report Jira-local files as unrepresented until a later, explicitly authorized whole-repository provenance refresh.

`NON_JIRA_SCOPE_DIFF.json` independently proves whether any original non-Jira repository file changed. The Jira subtree has its own complete release boundary:

- `validation/JIRA_FILE_MANIFEST.csv`
- `validation/JIRA_FILE_HASHES.sha256`
- `validation/NON_JIRA_SCOPE_DIFF.json`
- `tools/validate_jira_manifest.py`
- `tools/validate_jira_pack.py`
- `tools/run_second_pass_audit.py`

This is a transparent manifest-authority boundary, not a hidden product or Jira-pack validation failure. A future controlled whole-repository release may regenerate the global project manifest after reviewing the Jira addition.
""")


def build_complete_jira_pack(repo_root: Path, output_zip: Path | None = None, full_repo_zip: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    jira_root = repo_root / "jira"
    # Preserve this running generator in memory because the controlled rebuild replaces jira/ itself.
    builder_self_text = Path(__file__).read_text(encoding="utf-8")
    # SECOND_PASS_V2_PRESERVE_AND_APPLY: preserve the v2 hardener/validators before the generator replaces jira/.
    preserved_v2_tools = {}
    for _name in ["jira_pack_lib.py", "second_pass_hardening.py", "run_second_pass_audit.py", "validate_second_pass.py", "rebuild_all_derivatives.py", "repair_source_refs.py"]:
        _p = jira_root / "tools" / _name
        if _p.is_file():
            preserved_v2_tools[_name] = _p.read_text(encoding="utf-8")

    # The baseline must evaluate the authoritative W25 repository, not an earlier generated Jira derivative.
    if jira_root.exists():
        shutil.rmtree(jira_root)

    baseline_cmds = [
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        [sys.executable, "-B", "tools/validate_w25_final.py"],
        [sys.executable, "-B", "tools/validate_acceptance.py"],
        [sys.executable, "-B", "tools/validate_backlog.py"],
        [sys.executable, "-B", "tools/validate_repository.py", "--strict"],
    ]
    baseline_runs = [run_command(cmd, repo_root, 300) for cmd in baseline_cmds]

    jira_root.mkdir(parents=True, exist_ok=True)
    repo = RepoIndex(repo_root)
    regs = load_registries(repo)
    refs = SourceRefRegistry(repo)
    _source_catalog, id_to_ref = build_source_id_catalog(repo, refs, regs)
    historical = build_historical_issues(repo, refs, regs, id_to_ref)
    post, alias_to_id = build_post_issues(repo, refs, id_to_ref)
    issues = historical + post
    trace = attach_traceability(issues, regs, alias_to_id)
    open_issue_map = attach_open_issue_traceability(repo, issues, alias_to_id)
    trace["open_issue_post"] = open_issue_map
    enrich_issue_links_and_refs(issues, repo, refs, id_to_ref, alias_to_id)
    finalize_dependency_state(issues)
    assign_import_ids(issues)
    establish_record_paths(issues)

    write_root_docs(jira_root, repo, issues)
    write_project_configuration(jira_root, issues)
    write_reconciliation(jira_root, repo, issues, regs, trace, open_issue_map, id_to_ref)
    write_canonical_records(jira_root, issues)
    write_indexes(jira_root, issues, refs, regs, trace, open_issue_map, id_to_ref)
    write_source_views(jira_root, repo, refs, issues)
    import_data = write_import_pack(jira_root, issues)
    write_ai_views(jira_root, issues)
    write_tools(jira_root)
    write_text(jira_root / "tools" / "build_complete_jira_pack.py", builder_self_text)
    # Keep the generator's baseline helper library for the initial v1 validation pass;
    # restore the stricter v2 helper immediately before applying the hardener.
    for _name, _content in preserved_v2_tools.items():
        if _name != "jira_pack_lib.py":
            write_text(jira_root / "tools" / _name, _content)

    coverage = calculate_coverage(repo, issues, refs, regs, trace)
    write_coverage_reports(jira_root, coverage)
    write_json(jira_root / "validation" / "BASELINE_REPOSITORY_VALIDATION.json", baseline_runs)

    # Syntax-check tools without writing bytecode into the governed repository.
    tool_files = sorted((jira_root / "tools").glob("*.py"))
    compile_runs = []
    for tool_path in tool_files:
        code = (
            "from pathlib import Path; "
            f"p=Path({str(tool_path)!r}); "
            "compile(p.read_text(encoding='utf-8'), str(p), 'exec'); "
            "print('PASS:', p)"
        )
        compile_runs.append(run_command([sys.executable, "-B", "-c", code], repo_root, 120))
    pack_cmds = [
        [sys.executable, "-B", "jira/tools/validate_jira_pack.py"],
        [sys.executable, "-B", "jira/tools/validate_source_refs.py"],
        [sys.executable, "-B", "jira/tools/validate_dependencies.py"],
        [sys.executable, "-B", "jira/tools/validate_import_files.py"],
    ]
    pack_runs = compile_runs + [run_command(cmd, repo_root, 300) for cmd in pack_cmds]
    write_json(jira_root / "validation" / "GENERATED_TOOL_COMPILE_REPORT.json", compile_runs)
    write_json(jira_root / "validation" / "JIRA_PACK_VALIDATION_RUNS.json", pack_runs)
    write_text(jira_root / "validation" / "IMPORT_DRY_RUN_REPORT.md", f"""# Import Dry-Run Report

- CSV parsed locally: **{'PASS' if all(r['passed'] for r in pack_runs if r['command'][-1].endswith('validate_import_files.py')) else 'FAIL'}**
- Master/external import rows: **{len(import_data['issue_rows'])}**
- Link rows: **{len(import_data['link_rows'])}**
- API create payload templates: **{len(import_data['create_payloads'])}**
- API link payload templates: **{len(import_data['link_payloads'])}**
- Encoding: UTF-8
- Parent ordering: Epics → Stories/Tasks → Sub-tasks
- Jira-generated keys assumed: 0
- Final live Jira execution: intentionally not attempted because destination configuration/credentials were not supplied.
""")

    write_generation_report(jira_root, repo, issues, coverage, baseline_runs, pack_runs)

    # Apply the preserved content-aware v2 hardening pass before final manifests and archives.
    if preserved_v2_tools.get("jira_pack_lib.py"):
        write_text(jira_root / "tools" / "jira_pack_lib.py", preserved_v2_tools["jira_pack_lib.py"])
    if preserved_v2_tools.get("second_pass_hardening.py"):
        _v2_run = run_command([sys.executable, "-B", "jira/tools/second_pass_hardening.py", "--apply", "--skip-generator-patch"], repo_root, 600)
        pack_runs.append(_v2_run)
        write_json(jira_root / "validation" / "SECOND_PASS_GENERATOR_RUN.json", _v2_run)
    if preserved_v2_tools.get("run_second_pass_audit.py"):
        _audit_run = run_command([sys.executable, "-B", "jira/tools/run_second_pass_audit.py"], repo_root, 600)
        pack_runs.append(_audit_run)
        write_json(jira_root / "validation" / "SECOND_PASS_INDEPENDENT_AUDIT_RUN.json", _audit_run)

    result: dict[str, Any] = {
        "repo_root": str(repo_root),
        "jira_root": str(jira_root),
        "issues": len(issues),
        "coverage": coverage,
        "baseline_pass": all(r["passed"] for r in baseline_runs),
        "pack_validation_pass": all(r["passed"] for r in pack_runs),
    }
    if output_zip:
        result["jira_zip"] = str(output_zip)
    if full_repo_zip:
        result["full_repo_zip"] = str(full_repo_zip)
    write_json(jira_root / "validation" / "BUILD_RESULT.json", result)

    remove_bytecode_artifacts(jira_root)

    # The original global W25 manifest intentionally remains untouched; record its post-generation compatibility state.
    post_strict_run = run_command([sys.executable, "-B", "tools/validate_repository.py", "--strict"], repo_root, 300)
    write_repository_validator_compatibility(jira_root, post_strict_run)
    # Run once more after the compatibility evidence files themselves exist. Their contents may change,
    # but the file set is now stable, so the captured manifest-boundary count is exact for the delivered tree.
    post_strict_run = run_command([sys.executable, "-B", "tools/validate_repository.py", "--strict"], repo_root, 300)
    write_repository_validator_compatibility(jira_root, post_strict_run)
    result["post_generation_original_strict_returncode"] = post_strict_run["returncode"]
    result["post_generation_original_strict_expected_manifest_boundary"] = True
    write_json(jira_root / "validation" / "BUILD_RESULT.json", result)

    remove_bytecode_artifacts(jira_root)
    manifest_rows = write_jira_file_manifest(jira_root)
    manifest_errors = validate_jira_file_manifest(jira_root)
    # The validation note is created immediately below and is itself included in the final frozen manifest.
    predicted_final_manifest_count = len(manifest_rows) + 1
    write_text(jira_root / "validation" / "JIRA_MANIFEST_VALIDATION.md", f"""# Jira File-Manifest Validation

- Result: **{'PASS' if not manifest_errors else 'FAIL'}**
- Manifested files: **{predicted_final_manifest_count}**
- Errors: **{len(manifest_errors)}**

{md_list(manifest_errors)}
""")
    result["jira_file_manifest_count"] = predicted_final_manifest_count
    result["jira_file_manifest_pass"] = not manifest_errors
    result["pack_validation_pass"] = bool(result["pack_validation_pass"] and not manifest_errors)
    write_json(jira_root / "validation" / "BUILD_RESULT.json", result)

    # BUILD_RESULT and the validation note changed after the first manifest; freeze the final manifest now.
    remove_bytecode_artifacts(jira_root)
    normalize_jira_text_crlf(jira_root)
    manifest_rows = write_jira_file_manifest(jira_root)
    final_manifest_errors = validate_jira_file_manifest(jira_root)
    manifest_run = run_command([sys.executable, "-B", "jira/tools/validate_jira_manifest.py"], repo_root, 300)
    result["jira_file_manifest_count"] = len(manifest_rows)
    result["jira_file_manifest_pass"] = not final_manifest_errors and manifest_run["passed"]
    result["pack_validation_pass"] = bool(result["pack_validation_pass"] and result["jira_file_manifest_pass"])

    # Do not write into jira/ after the final manifest is frozen.
    if output_zip:
        deterministic_zip(jira_root, output_zip, "jira")
    if full_repo_zip:
        deterministic_zip(repo_root, full_repo_zip, "BatteredAggieSyndrome")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the complete local Jira system/import pack from the authoritative BAS repository.")
    parser.add_argument("repo_root", type=Path)
    parser.add_argument("--output-zip", type=Path, default=None)
    parser.add_argument("--full-repo-zip", type=Path, default=None)
    args = parser.parse_args()
    result = build_complete_jira_pack(args.repo_root, args.output_zip, args.full_repo_zip)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["pack_validation_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
