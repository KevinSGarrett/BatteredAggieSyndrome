r"""Cycle #37 — Attempt #11 — platform lifecycle reads, counted, and the two granted Jira comment targets.

R37A11-05-B. The Attempt 3 platform route (``attempt03_platform``) rebound to the Attempt 11 identity, as Attempts 5
through 10 rebound it; the request, comment and private-successor logic is not forked:

* the numeric identity (``attempt_number`` 11) and the report label every receipt carries;
* a fresh request ledger under the Attempt 11 evidence root the caller passes, so the issued ceilings
  (``GITHUB_METADATA`` 90, ``JIRA_METADATA_AND_ALLOWED_COMMENTS`` 100, ``SOURCE_ACQUISITION`` 0) are counted for
  this attempt alone, every failure and retry included, before a request is dispatched;
* the private Jira successor root is ``C:\BatteredAggieSyndrome.validation\c37a11\jira``; the canonical pack is
  never written and a private successor is never adopted.

Mutation remains confined to ``post_comment``: exactly BAT-706 and BAT-708, a deterministic ``C37-A11`` marker, a
duplicate check against the complete comment history and a readback. There is no status, label, owner, board,
PR, branch or owner-repository write, and no Git mutation (every Git call of the route reads). The credential is
read from the authoritative project ``.env``, held only for the Authorization header and never printed, logged or
written.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt03_platform as base  # noqa: E402  (the preserved Attempt 3 route)

ATTEMPT_NUMBER = 11
LABEL = "Cycle #37 — Attempt #11 — IN_PROGRESS_LOCAL_WORK_REMAINS"
PRIVATE_JIRA_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a11\jira")
#: Temporary files for the private successor's children: an Attempt 11 root, never the user profile.
SCRATCH_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a11\tmp")


class Jira(base.Jira):
    def __init__(self, ledger: base.Ledger) -> None:
        super().__init__(ledger)
        self._headers["User-Agent"] = "BAS-Cycle37-Attempt11/1.0"


def rebind() -> None:
    """Point the preserved Attempt 3 route at the Attempt 11 identity, roots and ledger."""

    base.ATTEMPT_NUMBER = ATTEMPT_NUMBER
    base.LABEL = LABEL
    base.PRIVATE_JIRA_ROOT = PRIVATE_JIRA_ROOT
    base.Jira = Jira
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(SCRATCH_ROOT)


def main(argv: list[str] | None = None) -> int:
    rebind()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
