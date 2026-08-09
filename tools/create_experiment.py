from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aggie_analytics.experimentation.contracts import ExperimentSpec

def main() -> int:
    ap=argparse.ArgumentParser(description="Create/validate a canonical W18 experiment spec from JSON.")
    ap.add_argument("spec_json", type=Path)
    ap.add_argument("--output", type=Path)
    args=ap.parse_args()
    data=json.loads(args.spec_json.read_text(encoding="utf-8"))
    spec=ExperimentSpec(**data)
    payload=spec.identity_payload()
    payload["experiment_id"]=spec.experiment_id
    text=json.dumps(payload,indent=2,sort_keys=True)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(text,encoding="utf-8")
    else:
        print(text,end="")
    return 0
if __name__=="__main__": raise SystemExit(main())
