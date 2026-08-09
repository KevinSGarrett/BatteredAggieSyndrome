from __future__ import annotations
import argparse,csv,json
from pathlib import Path

def rows(path):
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def validate(root:Path):
    g=root/"governance"; findings=[]
    fp=rows(g/"FEATURE_TOURNAMENT_POLICY.csv"); mp=rows(g/"MODEL_TOURNAMENT_POLICY.csv")
    stages=rows(g/"TOURNAMENT_STAGE_CATALOG.csv"); comp=rows(g/"TOURNAMENT_COMPARISON_POLICY.csv")
    if len(fp)<8: findings.append("feature tournament missing stages")
    if len(mp)<6: findings.append("model tournament missing candidate groups")
    if not any(r["stage"]=="ABLATION" for r in fp): findings.append("feature tournament lacks ablation")
    if not any("TAMU-SP-00" in r["mandatory_comparators"] for r in mp): findings.append("model tournament lacks TAMU no-adjustment comparator")
    if any("PROMOTE" in r["allowed_outputs"].split(";") for r in fp): findings.append("feature tournament can promote")
    if any("PROMOTE" in r["allowed_decisions"].split(";") for r in mp): findings.append("model tournament can promote")
    if not any(r["name"]=="W17_PROMOTION_REVIEW" and r["promotion_authority"]=="W17_EXTERNAL" for r in stages):
        findings.append("external promotion stage missing")
    if len(comp)<5: findings.append("comparison compatibility policy incomplete")
    reg=json.loads((root/"configs/tournament_registry.json").read_text(encoding="utf-8"))
    if reg.get("protected_metrics_allowed") is not False: findings.append("protected metrics allowed in tournament")
    if reg.get("promotion_state_allowed") is not False: findings.append("promotion allowed in tournament")
    return findings

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",type=Path,default=Path.cwd());a=ap.parse_args()
    f=validate(a.repo_root.resolve())
    if f:
        print(f"FAIL: {len(f)} tournament finding(s)"); [print("-",x) for x in f]; return 1
    print("PASS: feature/model tournament governance")
    return 0
if __name__=="__main__": raise SystemExit(main())
