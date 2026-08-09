from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.dont_write_bytecode=True
if __package__ in {None,''}: sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from aggie_analytics.operations.backup import restore_backup

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--backup',type=Path,required=True); ap.add_argument('--destination',type=Path,required=True); a=ap.parse_args(); m=restore_backup(a.backup,a.destination); print(json.dumps({'destination':str(a.destination),'files':len(m['entries'])},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
