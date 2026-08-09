from __future__ import annotations
import argparse,csv,json,re,sys
sys.dont_write_bytecode=True
from pathlib import Path

def rows(p):
    with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def validate(root:Path):
    out=[]
    cfg=json.loads((root/"configs/raw_feature_registry.json").read_text(encoding="utf-8"))
    raw=rows(root/"governance/RAW_FIELD_REGISTRY.csv")
    ds=rows(root/"governance/DATASET_SCHEMA_REGISTRY.csv")
    miss=rows(root/"governance/MISSINGNESS_EVIDENCE_REGISTRY.csv")
    joins=rows(root/"governance/JOIN_PATH_REGISTRY.csv")
    red=rows(root/"governance/REDUNDANCY_CLUSTER_REGISTRY.csv")
    if len(raw)!=cfg["counts"]["raw_fields"]:out.append("raw field count mismatch")
    ids=[r["raw_field_id"] for r in raw]
    exp=[f"RF-{i:06d}" for i in range(1,len(raw)+1)]
    if ids!=exp:out.append("raw_field_id sequence mismatch")
    key=[(r["source_id"],r["source"],r["dataset_or_model"],r["field_path"]) for r in raw]
    if len(key)!=len(set(key)):out.append("duplicate source-scoped raw field identity")
    allowed=set(cfg["allowed_temporal_classes"]); states=set(cfg["handoff_states"])
    for r in raw:
        if r["normalized_temporal_class"] not in allowed:out.append(f"unknown temporal class {r['raw_field_id']}")
        if r["handoff_state"] not in states:out.append(f"unknown handoff state {r['raw_field_id']}")
        if r["classification_preserved"]!="true":out.append(f"classification not preserved {r['raw_field_id']}")
        if r["population_missingness_status"]!="UNMEASURED_UNTIL_SOURCE_MATERIALIZATION":out.append(f"population missingness overclaimed {r['raw_field_id']}")
        if r["normalized_temporal_class"] in {"POSTGAME_OR_FUTURE_BANNED","REVIEW_REQUIRED"} and r["w10_candidate_experiment_allowed"]=="true":out.append(f"unsafe W10 handoff {r['raw_field_id']}")
    if len(ds)!=cfg["counts"]["dataset_endpoint_rows"]:out.append("dataset registry count mismatch")
    if any(r["schema_status"]=="SCHEMA_PENDING_MATERIALIZATION" and r["reconciled_raw_field_count"] not in {"0",""} for r in ds):out.append("pending schema has invented fields")
    if len(miss)!=cfg["counts"]["sample_missingness_evidence"]:out.append("missingness evidence count mismatch")
    if any(r["interpretation"]!="REPRESENTATIVE_SAMPLE_ONLY_NOT_POPULATION_STATISTIC" for r in miss):out.append("sample missingness overclaimed")
    if len(joins)!=cfg["counts"]["join_path_evidence"]:out.append("join evidence count mismatch")
    if any(r["semantic_validation_required"]!="true" for r in joins):out.append("join path semantic validation disabled")
    if len(red)!=cfg["counts"]["redundancy_clusters"]:out.append("redundancy count mismatch")
    if any(r["semantic_merge_allowed"]!="false" for r in red):out.append("automatic semantic merge allowed")
    wbs=rows(root/"governance/IMPLEMENTATION_WBS.csv"); by={r["task_id"]:r for r in wbs}
    for tid in ["TASK-019","TASK-020","TASK-021","TASK-022","TASK-023"]:
        if by.get(tid,{}).get("status")!="DONE":out.append(f"{tid} not DONE")
    
    if (root/"configs/feature_lifecycle_registry.json").exists():
        if by.get("TASK-024",{}).get("status")!="DONE":out.append("TASK-024 not DONE after W10")
    elif by.get("TASK-024",{}).get("status")!="READY":out.append("TASK-024 not READY")
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",type=Path,default=Path.cwd());a=ap.parse_args();f=validate(a.repo_root.resolve())
    if f:
        print(f"FAIL: {len(f)} finding(s)");[print('-',x) for x in f];return 1
    print("PASS: W09 raw-field registry, schema discovery, reconciliation and W10 handoff contracts")
    return 0
if __name__=="__main__":raise SystemExit(main())
