from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate(root: Path) -> list[str]:
    root = Path(root).resolve()
    g = root / "governance"
    findings: list[str] = []

    required = [
        "docs/113_W25_FINAL_CONSOLIDATION_AND_CODEX_HANDOFF.md",
        "docs/final/CODEX_HANDOFF.md",
        "docs/final/FINAL_ARCHITECTURE_RATIONALE.md",
        "docs/final/FINAL_REJECTED_ALTERNATIVES.md",
        "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
        "docs/final/FIRST_72_HOUR_IMPLEMENTATION_QUEUE.md",
        "docs/final/FINAL_COMPONENT_MATURITY.csv",
        "docs/final/FINAL_KNOWN_GAPS.md",
        "docs/final/FINAL_KNOWN_GAPS.csv",
        "docs/final/FINAL_RISK_REGISTER.csv",
        "docs/final/FINAL_BACKLOG.csv",
        "docs/data_research/w25/FINAL_DATA_SOURCE_AUDIT.md",
        "governance/W25_ADAPTIVE_REVIEW.md",
        "governance/W25_FINAL_GOVERNANCE_AUDIT.json",
        "governance/W25_FINAL_TECHNICAL_AUDIT.json",
        "governance/W25_VALIDATION_REPORT.md",
        "governance/W25_W24_PARENT_PRESERVATION.csv",
    ]
    for rel in required:
        if not (root / rel).is_file():
            findings.append(f"missing {rel}")

    identity = _text(g / "PROJECT_IDENTITY.yaml")
    for phrase in (
        "current_wave: W25",
        "next_wave: CODEX_IMPLEMENTATION_HANDOFF",
        "exact_wave_count: 25",
        "project_version: 0.25.0-w25-final-handoff",
    ):
        if phrase not in identity:
            findings.append(f"PROJECT_IDENTITY missing {phrase}")

    state = _text(g / "CURRENT_STATE.yaml")
    for phrase in (
        "current_wave: W25",
        "next_wave: CODEX_IMPLEMENTATION_HANDOFF",
        "wave_program_complete: true",
        "w26_allowed: false",
        "target_benchmark_authoritative: false",
        "empirical_historical_replay_completed: false",
        "trained_production_champion_selected: false",
        "production_feature_set_selected: false",
        "tamu_specialization_lift_claimed: false",
        "aggie_excess_claimed: false",
        "bas_empirical_effect_claimed: false",
        "serving_mode: IMMUTABLE_PUBLISHED_SNAPSHOT_ONLY",
    ):
        if phrase not in state:
            findings.append(f"CURRENT_STATE missing {phrase}")

    tasks = {r["task_id"]: r for r in _rows(g / "IMPLEMENTATION_WBS.csv")}
    for tid in [f"TASK-{i:03d}" for i in range(179, 190)]:
        if tasks.get(tid, {}).get("status") != "DONE":
            findings.append(f"{tid} not DONE")
    if tasks.get("TASK-161", {}).get("status") != "BLOCKED_TARGET_HARDWARE":
        findings.append("TASK-161 target-hardware blocker lost")
    if tasks.get("TASK-163", {}).get("status") != "BLOCKED_AC038_TARGET_HARDWARE":
        findings.append("TASK-163 AC-038 blocker lost")
    for tid in [f"TASK-{i:03d}" for i in range(165, 173)]:
        if tasks.get(tid, {}).get("status") != "PLANNED":
            findings.append(f"{tid} must remain PLANNED/deferred research")
    counts = Counter(r["status"] for r in tasks.values())
    if counts.get("DONE") != 191 or counts.get("PLANNED") != 8:
        findings.append(f"unexpected final task status counts: {dict(counts)}")

    req_rows = _rows(g / "REQUIREMENTS_INDEX.csv")
    req_ids = [r["requirement_id"] for r in req_rows]
    if len(req_rows) != 745 or len(req_ids) != len(set(req_ids)):
        findings.append("requirements must be 745 unique IDs")
    req130 = next((r for r in req_rows if r["requirement_id"] == "REQ-130"), None)
    if not req130 or req130.get("status") != "COMPLETE_W25":
        findings.append("REQ-130 is not COMPLETE_W25")
    acc_rows = _rows(g / "REQUIREMENT_ACCEPTANCE_MATRIX.csv")
    if len(acc_rows) != 745:
        findings.append("requirement acceptance matrix row count != 745")
    acc130 = next((r for r in acc_rows if r["requirement_id"] == "REQ-130"), None)
    if not acc130 or acc130.get("acceptance_state") != "VERIFIED_W25_FINAL":
        findings.append("REQ-130 final acceptance state missing")

    adr_rows = _rows(g / "ADR_INDEX.csv")
    adr_ids = [r["adr_id"] for r in adr_rows]
    if len(adr_rows) != 349 or len(adr_ids) != len(set(adr_ids)):
        findings.append("ADRs must be 349 unique IDs")
    for aid in ("ADR-347", "ADR-348", "ADR-349"):
        if aid not in adr_ids:
            findings.append(f"missing {aid}")
    adr_map = {r["adr_id"]: r for r in _rows(g / "ADR_ACCEPTANCE_TRACEABILITY.csv")}
    for aid in ("ADR-347", "ADR-348", "ADR-349"):
        if adr_map.get(aid, {}).get("status") != "MAPPED":
            findings.append(f"{aid} not acceptance-mapped")

    maturity_rows = _rows(root / "docs/final/FINAL_COMPONENT_MATURITY.csv")
    maturity_text = "\n".join("|".join(r.values()) for r in maturity_rows)
    for phrase in (
        "AWAITING_TARGET_HARDWARE_VALIDATION",
        "AWAITING_DATA_AND_EXECUTION",
        "DEFERRED_CONDITIONAL",
    ):
        if phrase not in maturity_text:
            findings.append(f"final maturity missing {phrase}")

    gap_ids = {r["gap_id"] for r in _rows(root / "docs/final/FINAL_KNOWN_GAPS.csv")}
    if not {f"GAP-{i:03d}" for i in range(1, 15)}.issubset(gap_ids):
        findings.append("final known-gap register incomplete")
    handoff_ids = {r["handoff_id"] for r in _rows(root / "docs/final/FINAL_BACKLOG.csv")}
    if not {f"HANDOFF-{i:03d}" for i in range(1, 15)}.issubset(handoff_ids):
        findings.append("final handoff backlog incomplete")


    preservation = _rows(g / "W25_W24_PARENT_PRESERVATION.csv")
    if len(preservation) != 844:
        findings.append(f"W24 parent preservation row count != 844: {len(preservation)}")
    missing_parent = [r["path"] for r in preservation if r.get("status") == "MISSING"]
    if missing_parent:
        findings.append(f"W24 parent paths missing in W25: {missing_parent[:5]}")

    source_audit = _text(root / "docs/data_research/w25/FINAL_DATA_SOURCE_AUDIT.md")
    for phrase in ("CollegeFootballData", "cfbfastR-cfb-data", "cfbfastR-cfb-raw", "Open-Meteo", "SEC", "ACC", "Big 12", "NCAA"):
        if phrase not in source_audit:
            findings.append(f"final data-source audit missing {phrase}")

    rationale = _text(root / "docs/final/FINAL_ARCHITECTURE_RATIONALE.md")
    for phrase in ("local-first modular monolith", "point-in-time", "Texas A&M", "BAS"):
        if phrase.lower() not in rationale.lower():
            findings.append(f"architecture rationale missing {phrase}")
    rejected = _text(root / "docs/final/FINAL_REJECTED_ALTERNATIVES.md")
    for phrase in ("Kubernetes", "A&M-only", "Closing market lines", "Research automation"):
        if phrase.lower() not in rejected.lower():
            findings.append(f"rejected-alternatives record missing {phrase}")

    wave_plan = _text(g / "WAVE_PLAN.md")
    if "W25" not in wave_plan or "TERMINAL" not in wave_plan.upper():
        findings.append("WAVE_PLAN does not mark W25 terminal")
    next_text = _text(g / "NEXT_WAVE.md")
    if "Wave Program Complete" not in next_text or "CODEX_IMPLEMENTATION_HANDOFF" not in next_text:
        findings.append("NEXT_WAVE does not transition to implementation handoff")

    return findings


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = ap.parse_args()
    findings = validate(args.repo_root)
    if findings:
        print(f"FAIL: {len(findings)} W25 finding(s)")
        for item in findings:
            print("-", item)
        return 1
    print("PASS: W25 final consolidation, terminal-wave governance, maturity honesty and Codex handoff controls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
