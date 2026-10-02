r"""Cycle #37 — Attempt #9 — every Git command an Attempt 9 helper builds, with automatic housekeeping suppressed.

A plain ``git commit`` in Attempt 8 ran ``gc --auto`` in the shared Git store (about 7,000 loose objects packed; the fate
of older unreachable objects is unknown, W37A08-07). The issued rule for Attempt 9: every mutating Git command and
subprocess carries the command-scoped settings ``-c gc.auto=0 -c maintenance.auto=false``; no repository configuration
is changed and no gc, maintenance, prune, repack or clean is run.

:func:`command` builds every Git command line an Attempt 9 helper runs -- mutating or not -- with both settings first,
and :func:`install` routes the preserved candidate-append chain (``attempt05_candidate.git``, which the Attempt 6, 7
and 8 append procedures call) through it. The settings are proved on owned fixtures before any real commit
(``C:\BatteredAggieSyndrome.validation\c37a09\gitpreflight``): a plain commit there packs the loose objects, the
command-scoped commit leaves them loose.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

#: Placed before every subcommand; a command-scoped setting, never written to any configuration file.
SUPPRESS = ("-c", "gc.auto=0", "-c", "maintenance.auto=false")


def command(*args: Any, repo: Path | str | None = None) -> list[str]:
    """``git -c gc.auto=0 -c maintenance.auto=false --no-optional-locks [-C repo] <args>``."""

    return ["git", *SUPPRESS, "--no-optional-locks", *(["-C", str(repo)] if repo is not None else []),
            *(str(a) for a in args)]


def git(*args: Any, repo: Path | str | None = None, env: dict[str, str] | None = None, check: bool = True,
        stdin: str | None = None) -> str:
    """Run one Git command through :func:`command`; return its stripped stdout, raising on failure when ``check``."""

    completed = subprocess.run(command(*args, repo=repo), capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=env, check=False, input=stdin)
    if check and completed.returncode != 0:
        raise SystemExit(f"git {' '.join(str(a) for a in args)} failed ({completed.returncode}): "
                         f"{completed.stderr.strip()}")
    return completed.stdout.strip()


def install() -> None:
    """Route the preserved append procedure's Git wrapper (Attempts 5 to 8) through :func:`git`."""

    import attempt05_candidate as a5c  # noqa: PLC0415

    def routed(*args: str, repo: Path | None = None, env: dict[str, str] | None = None, check: bool = True,
               stdin: str | None = None) -> str:
        return git(*args, repo=repo or a5c.REPO, env=env, check=check, stdin=stdin)

    a5c.git = routed
