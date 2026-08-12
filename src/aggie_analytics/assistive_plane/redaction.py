from __future__ import annotations

import re


_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)\S+"),
    re.compile(r"(?i)((?:api[_-]?key|token|password)\s*[=:]\s*)\S+"),
    re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]+\b"),
)


def redact(text: str) -> str:
    value = text
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub(lambda match: (match.group(1) if match.lastindex else "") + "[REDACTED]", value)
    return value


def contains_secret(text: str) -> bool:
    return redact(text) != text
