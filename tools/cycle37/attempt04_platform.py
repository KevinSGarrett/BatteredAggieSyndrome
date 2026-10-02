r"""Cycle #37 — Attempt #4 — platform lifecycle reads, counted, and the two granted Jira comment targets.

R37A04-07-B. This is the Attempt 3 platform route (``attempt03_platform``) rebound to the Attempt 4 identity; it
does not fork its request, comment or private-successor logic. What changes is only what must change:

* the numeric identity (``attempt_number`` 4) and the report label every receipt carries;
* the ledger and receipts live under the Attempt 4 evidence root the caller passes -- a fresh ledger, so the
  issued ceilings (``GITHUB_METADATA`` 90, ``JIRA_METADATA_AND_ALLOWED_COMMENTS`` 100, ``SOURCE_ACQUISITION`` 0)
  are counted for this attempt alone, every failure and retry included, before a request is dispatched;
* the private Jira successor root is ``C:\BatteredAggieSyndrome.validation\c37a04\jira``;
* the pack tools of the private successor run under the v37.4 canonical write guard, whose Git children are
  confined to exact read forms, with a Git scratch root that is this attempt's own temporary folder.

Mutation remains confined to ``post_comment``: exactly BAT-706 and BAT-708, a deterministic marker, a duplicate
check against the complete comment history and a readback. There is no status, label, owner, board, PR,
branch or owner-repository write. The credential is read from the authoritative project ``.env``, held only
for the Authorization header and never printed, logged or written.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt03_platform as base  # noqa: E402  (the preserved Attempt 3 route this module rebinds)

ATTEMPT_NUMBER = 4
LABEL = "Cycle #37 — Attempt #4 — IN_PROGRESS_LOCAL_WORK_REMAINS"
PRIVATE_JIRA_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a04\jira")
#: Temporary files and the guard's Git scratch root for the private successor's children: an Attempt 4 root.
SCRATCH_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a04\tmp")


class Jira(base.Jira):
    def __init__(self, ledger: base.Ledger) -> None:
        super().__init__(ledger)
        self._headers["User-Agent"] = "BAS-Cycle37-Attempt4/1.0"


def rebind() -> None:
    """Point the preserved Attempt 3 route at the Attempt 4 identity, roots and ledger."""

    base.ATTEMPT_NUMBER = ATTEMPT_NUMBER
    base.LABEL = LABEL
    base.PRIVATE_JIRA_ROOT = PRIVATE_JIRA_ROOT
    base.Jira = Jira
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    # The private successor passes TEMP/TMP through to its guarded children; the v37.4 guard takes its default
    # Git scratch root from TEMP, so both land in this attempt's own folder rather than the user profile.
    os.environ["TEMP"] = os.environ["TMP"] = str(SCRATCH_ROOT)


def main(argv: list[str] | None = None) -> int:
    rebind()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
