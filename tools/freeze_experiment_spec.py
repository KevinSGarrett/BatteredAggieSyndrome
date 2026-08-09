from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aggie_analytics.experimentation.lineage import assert_result_independent_identity,canonical_json,content_id

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("spec",type=Path);ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    spec=json.loads(a.spec.read_text(encoding="utf-8"))
    assert_result_independent_identity(spec)
    eid=content_id("EXP",spec)
    out={"experiment_id":eid,"canonical_spec":spec}
    text=json.dumps(out,indent=2,sort_keys=True)+"\n"
    if a.output:a.output.write_text(text,encoding="utf-8")
    else:print(text,end="")
    return 0
if __name__=="__main__":raise SystemExit(main())
