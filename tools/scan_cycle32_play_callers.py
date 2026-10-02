"""Scan official current titles for separately sourced play-calling language.

Pass/run-game coordinator is not play-caller. Unsourced play-calling stays
unsourced. This does not infer play-calling from OC occupancy.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
_PLAY_CALL = re.compile(
    r"\bplay[\s-]?call(?:er|ing)\b|\bcalls?\s+plays\b|\bplaycaller\b",
    re.I,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    people = load_jsonl(OUT / "science" / "CYCLE32_OFFICIAL_STAFF_PARSED.jsonl")
    hits: list[dict[str, Any]] = []
    for row in people:
        title = str(row.get("title") or row.get("source_title") or "")
        if not _PLAY_CALL.search(title):
            continue
        hits.append(
            {
                "program_id": row.get("program_id"),
                "person": row.get("person"),
                "title": title,
                "stored_role": row.get("role"),
                "play_calling_inferred_from_oc": False,
            }
        )
    payload = {
        "artifact_type": "CYCLE32_PLAY_CALLER_TITLE_SCAN",
        "as_of_utc": utc_now(),
        "parsed_people": len(people),
        "play_caller_title_hits": len(hits),
        "rows": hits,
        "play_caller_sourced": bool(hits),
        "pass_or_run_game_is_not_play_caller": True,
        "pit_admitted": False,
    }
    out = OUT / "science" / "CYCLE32_PLAY_CALLER_TITLE_SCAN.json"
    _bas_atomic.write_text(out, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"hits": len(hits), "sourced": bool(hits)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
