from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.dont_write_bytecode=True
if __package__ in {None,''}: sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from aggie_analytics.operations.benchmark import run_benchmark

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--profile',choices=['smoke','representative'],default='smoke'); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); p=run_benchmark(profile=a.profile); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(p,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps({'output':str(a.output),'target_match':p['target_match'],'authoritative':p['authoritative_for_thr_011_012']},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
