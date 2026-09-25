"""Cycle #37 - Attempt #2: install the BAS canonical write guard in a canonical-mounted lane's children.

Python imports ``sitecustomize`` at start-up from the path the lane prepends. It does nothing unless
``BAS_CANONICAL_WRITE_GUARD`` is set (W37R-66/67/68 prevention; see bas_canonical_write_guard).
"""

import os

if os.environ.get("BAS_CANONICAL_WRITE_GUARD"):
    import bas_canonical_write_guard

    bas_canonical_write_guard.install()
