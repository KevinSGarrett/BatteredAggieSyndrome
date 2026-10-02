r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Build the corrected national release (R37-07) from the selected worktree's
source. The command line lives in the package
(``aggie_analytics.cycle37.release_cli``) so a clean installed wheel can run
the same build with ``python -I -m aggie_analytics.cycle37.release_cli``; this
wrapper only puts the worktree's ``src`` first on the path and calls it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

WORKTREE = Path(__file__).resolve().parents[2]
if str(WORKTREE / "src") not in sys.path:
    sys.path.insert(0, str(WORKTREE / "src"))

from aggie_analytics.cycle37.release_cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
