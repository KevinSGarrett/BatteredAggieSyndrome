from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.dont_write_bytecode=True
if __package__ in {None,''}: sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from aggie_analytics.operations.backup import create_backup

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); m=create_backup(a.source,a.output); print(json.dumps({'output':str(a.output),'files':len(m['entries'])},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
