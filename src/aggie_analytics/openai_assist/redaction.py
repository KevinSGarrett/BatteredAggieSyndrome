from __future__ import annotations

import re
from typing import Any


class RedactionError(ValueError):
    pass


_FORBIDDEN_KEYS = re.compile(
    r"(^|_)(api_?key|authorization|cookie|password|secret|token)(_|$)", re.IGNORECASE
)
_KEY_LIKE = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")
_AUTH_LIKE = re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9+/=_-]{8,}\b", re.IGNORECASE)


def assert_prompt_safe(value: Any, *, known_secret: str | None = None, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if _FORBIDDEN_KEYS.search(str(key)):
                raise RedactionError(f"forbidden secret-bearing field at {path}.{key}")
            assert_prompt_safe(child, known_secret=known_secret, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            assert_prompt_safe(child, known_secret=known_secret, path=f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    if known_secret and known_secret in value:
        raise RedactionError(f"configured credential appears in request material at {path}")
    if _KEY_LIKE.search(value) or _AUTH_LIKE.search(value):
        raise RedactionError(f"credential-like content appears in request material at {path}")
    if "OPENAI_API_KEY=" in value or "SCRAPFLY_API_TOKEN=" in value or "JIRA_API_KEY=" in value:
        raise RedactionError(f"environment-file content appears in request material at {path}")
