"""Compare live OneDrive coaches CSVs to the preserved Cycle 33 snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

LIVE = Path(r"C:\Users\kevin\OneDrive\Documents\Coaches")
SNAP = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches"
    r"\20260914T051702Z\source_snapshot"
)
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science\CYCLE33_USER_COACHES_LIVE_DELTA.json"
)


def hashes(root: Path) -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("*.csv")
    }


def main() -> int:
    live_files = hashes(LIVE) if LIVE.is_dir() else {}
    snap_files = hashes(SNAP)
    only_live = sorted(set(live_files) - set(snap_files))
    only_snap = sorted(set(snap_files) - set(live_files))
    changed = sorted(
        n for n in live_files if n in snap_files and live_files[n] != snap_files[n]
    )
    payload = {
        "artifact_type": "CYCLE33_USER_COACHES_LIVE_DELTA",
        "live_root": str(LIVE),
        "snapshot_root": str(SNAP),
        "live_present": LIVE.is_dir(),
        "live_csv_count": len(live_files),
        "snap_csv_count": len(snap_files),
        "only_live": only_live,
        "only_snap": only_snap,
        "changed_bytes": changed,
        "identical": bool(live_files)
        and len(live_files) == len(snap_files)
        and not only_live
        and not only_snap
        and not changed,
        "live_is_intake_not_runtime_default": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
