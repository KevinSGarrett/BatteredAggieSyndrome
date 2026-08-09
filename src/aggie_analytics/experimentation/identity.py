from __future__ import annotations
from hashlib import sha256
import json
from typing import Any

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def content_id(prefix: str, payload: Any, length: int = 24) -> str:
    digest = sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:length]}"
