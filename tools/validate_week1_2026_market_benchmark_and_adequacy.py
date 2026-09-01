from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from validate_week1_2026_market_surfaces import main  # noqa: E402

SURFACE = "artifact"

if __name__ == "__main__":
    raise SystemExit(main(["--surface", SURFACE, *sys.argv[1:]]))
