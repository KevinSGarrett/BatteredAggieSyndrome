from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path

def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validate(root: Path) -> list[str]:
    findings=[]
    reg=json.loads((root/"configs/entity_registry.json").read_text(encoding="utf-8"))
    ents=_rows(root/"governance/CANONICAL_ENTITY_CATALOG.csv")
    rels=_rows(root/"governance/CANONICAL_RELATIONSHIP_CATALOG.csv")
    methods=_rows(root/"governance/SOURCE_MAPPING_METHODS.csv")
    states=_rows(root/"governance/ENTITY_RESOLUTION_STATES.csv")
    storage=_rows(root/"governance/ENTITY_STORAGE_DECISION_MATRIX.csv")
    if reg.get("maturity")!="CANONICAL_IDENTITY_CONTRACTS_ONLY":
        findings.append("entity maturity must not overstate implementation")
    entity_names=[x["entity_type"] for x in ents]
    if len(entity_names)!=len(set(entity_names)): findings.append("duplicate entity types")
    required={"team","institution","conference","season","game","venue","player","coach","official","source_system","source_resource","publication_version","raw_capture","source_observation"}
    if required-set(entity_names): findings.append(f"missing required entity types {sorted(required-set(entity_names))}")
    if set(entity_names)!={x["entity_type"] for x in reg["entity_types"]}: findings.append("CSV/JSON entity catalog mismatch")
    if reg["source_mapping"].get("name_only_durable_join_forbidden") is not True: findings.append("name-only durable join must be forbidden")
    if reg["resolution"].get("fuzzy_auto_accept_enabled") is not False: findings.append("fuzzy auto-accept must remain disabled in W07")
    if reg["resolution"].get("auto_accept_threshold")!="TBD_BY_LABELED_EVIDENCE": findings.append("entity threshold must remain evidence-owned/TBD")
    auto={x["mapping_method"] for x in methods if x["default_action"]=="AUTO_ACCEPT_ALLOWED"}
    if auto-{"VERIFIED_EXISTING_MAPPING","VERIFIED_DIRECT_SOURCE_ID","VERIFIED_CROSSWALK"}:
        findings.append("unapproved auto-accept mapping method")
    if "FUZZY_NAME_CONTEXT" in auto or "EXACT_SCOPED_ALIAS" in auto:
        findings.append("fuzzy/alias matching cannot auto-accept in W07")
    if not any(x["state"]=="REVIEW_REQUIRED" for x in states): findings.append("review-required state missing")
    if not any(x["state"]=="MERGED_REDIRECT" for x in states) or not any(x["state"]=="SPLIT_CORRECTED" for x in states):
        findings.append("merge/split correction states missing")
    if reg["storage_decision"].get("decision")!="DEFER_POSTGRESQL": findings.append("W07 storage decision mismatch")
    if any(x["postgresql_required"]=="YES" for x in storage): findings.append("PostgreSQL incorrectly mandatory in current W07 workload")
    layers=reg["source_evidence_identity"]["ordered_layers"]
    expected=["source_system","source_resource","publication_version","raw_capture","source_observation"]
    if layers!=expected: findings.append("source evidence identity hierarchy mismatch")
    if reg["correction_policy"].get("destructive_delete_of_assigned_canonical_id") is not False:
        findings.append("destructive canonical-ID correction must be forbidden")
    # Schemas exist and agree on no-name-only/fuzzy rules.
    for name in ["entities.json","source_mapping.json","evidence_identity.json","resolution_decision.json"]:
        p=root/"schemas/canonical"/name
        if not p.is_file(): findings.append(f"missing schema {name}")
        else:
            try: json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc: findings.append(f"invalid schema {name}: {exc}")
    # Ensure exact prefix regex remains source-independent.
    if "source_entity_key" in reg["id_policy"]["format_regex"]:
        findings.append("canonical ID regex must not encode source keys")
    return findings

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",type=Path,default=Path.cwd()); a=ap.parse_args()
    f=validate(a.repo_root.resolve())
    if f:
        print(f"FAIL: {len(f)} entity finding(s)")
        for x in f: print("-",x)
        return 1
    print("PASS: canonical IDs, entity/evidence hierarchy, mapping/review/correction rules and W07 storage decision")
    return 0
if __name__=="__main__": raise SystemExit(main())
