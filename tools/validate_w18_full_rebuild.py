from __future__ import annotations
import argparse,csv,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))

def rows(p):
    with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def validate(root:Path):
    f=[];g=root/"governance"
    req=rows(g/"REQUIREMENTS_INDEX.csv");acs=rows(g/"ACCEPTANCE_CONTROL_CATALOG.csv");wbs=rows(g/"IMPLEMENTATION_WBS.csv")
    ids={r["requirement_id"] for r in req}
    for n in range(603,701):
        if f"REQ-{n:03d}" not in ids:f.append(f"missing W18 requirement REQ-{n:03d}")
    cids={r["control_id"] for r in acs}
    for n in range(177,229):
        if f"AC-{n:03d}" not in cids:f.append(f"missing W18 acceptance control AC-{n:03d}")
    owner=[r for r in wbs if r["owner_wave"]=="W18"]
    if not owner:f.append("no W18-owned tasks")
    for r in owner:
        if r["status"]!="DONE":f.append(f"{r['task_id']} W18-owned task not DONE")
    if "TASK-164" not in {r["task_id"] for r in owner}:f.append("TASK-164 advanced challenger task missing")
    docs=[root/f"docs/{n:02d}_{slug}" for n,slug in []]
    required=[
      "src/aggie_analytics/experimentation/store.py",
      "src/aggie_analytics/experimentation/scheduler.py",
      "src/aggie_analytics/experimentation/feature_tournament.py",
      "src/aggie_analytics/experimentation/model_tournament.py",
      "src/aggie_analytics/experimentation/replay_engine.py",
      "src/aggie_analytics/experimentation/artifacts_v2.py",
      "src/aggie_analytics/experimentation/promotion_bridge.py",
      "docs/96_W18_OPERATOR_RUNBOOK.md",
      "governance/EXPERIMENT_STORE_SCHEMA_CATALOG.csv",
      "governance/W18_FULL_REQUIREMENT_TO_ARTIFACT_MATRIX.csv",
      "governance/W18_TASK_TO_TEST_MATRIX.csv",
    ]
    for rel in required:
        p=root/rel
        if not p.exists() or p.stat().st_size<100:f.append(f"missing/thin full-rebuild artifact {rel}")
    version=json.loads((root/"configs/experiment_research_registry.json").read_text()).get("version")
    if version!="w18-v2.0-full-rebuild":f.append("experiment registry is not full rebuild v2")
    return f

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",type=Path,default=Path.cwd());a=ap.parse_args()
    f=validate(a.repo_root.resolve())
    if f:
        print(f"FAIL: {len(f)} W18 full-rebuild finding(s)");[print("-",x) for x in f];return 1
    print("PASS: W18 full-rebuild subsystem, W18-owned-task, coverage and artifact gate");return 0
if __name__=="__main__":raise SystemExit(main())
