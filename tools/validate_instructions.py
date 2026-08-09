from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_autonomous_controls import main


if __name__ == "__main__":
    raise SystemExit(main())
