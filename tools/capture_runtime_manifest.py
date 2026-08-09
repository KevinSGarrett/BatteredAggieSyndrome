from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.dont_write_bytecode=True
if __package__ in {None,''}: sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from aggie_analytics.operations.environment import write_runtime_manifest

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--repo-root',type=Path,default=Path.cwd()); a=ap.parse_args(); p=write_runtime_manifest(a.output,repo_root=a.repo_root); print(json.dumps({'output':str(a.output),'manifest_sha256':p['manifest_sha256']},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
