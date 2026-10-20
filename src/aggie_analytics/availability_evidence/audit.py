"""The qualified audit identity of the complete per-row qualification collection (BAT-733, TP62-A01 section 4).

``None`` until the first real qualification of the fixed profile: the rules, profile and reader are frozen and
committed before any substantive real qualification output exists. A later commit pins here exactly the identity the
qualification lane observed ({rules_sha256, database_sha256, rows, lines_sha256, summary}) without changing any rule;
from then on the reader refuses a qualification collection that differs (``QUALIFICATION_AUDIT_MISMATCH``).
"""
from __future__ import annotations

from typing import Any

QUALIFIED_AUDIT: dict[str, Any] | None = None
