"""Adjudicate predecessor suspicious wiki person strings. Not blanket rejection."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
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

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
TITLE_TOKENS = re.compile(
    r"(?i)\b(?:head coach|offensive coordinator|defensive coordinator|"
    r"coordinator|coach|infobox|template|\|\s*\w+\s*=)"
)
WIKITEXT_NOISE = re.compile(r"[\[\]{}|=]|Infobox|Category:")
NAME_OK = re.compile(
    r"^[A-Z][A-Za-z.'\-]+(?:\s+(?:[A-Z][A-Za-z.'\-]+|Jr\.?|Sr\.?|II|III|IV)){0,4}$"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def classify_person(person: str) -> str:
    text = str(person or "").strip()
    if not text:
        return "EMPTY"
    if WIKITEXT_NOISE.search(text) or TITLE_TOKENS.search(text):
        return "TITLE_OR_TEMPLATE_CONTAMINATED"
    if re.search(r"\d", text):
        return "DIGIT_IN_NAME_CANDIDATE"
    if len(text) > 80:
        return "TOO_LONG"
    if NAME_OK.fullmatch(text):
        return "PLAUSIBLE_PERSON_NAME_NOT_VERIFIED"
    return "SUSPECT_UNRESOLVED"


def main() -> int:
    predecessor = load_jsonl(PRED / "WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl")
    suspects: list[dict[str, Any]] = []
    counts = Counter()
    seen: set[str] = set()
    for row in predecessor:
        for episode in row.get("episodes") or []:
            person = str(episode.get("person") or "")
            key = person
            if not key or key in seen:
                continue
            label = classify_person(person)
            counts[label] += 1
            if label == "PLAUSIBLE_PERSON_NAME_NOT_VERIFIED":
                continue
            seen.add(key)
            suspects.append(
                {
                    "person": person,
                    "program": row.get("school"),
                    "season": row.get("season"),
                    "title": row.get("title"),
                    "disposition": label,
                    "preserved": True,
                    "not_automatically_wrong": label
                    in {"DIGIT_IN_NAME_CANDIDATE", "SUSPECT_UNRESOLVED"},
                    "pit_admitted": False,
                }
            )
    payload = {
        "artifact_type": "CYCLE32_WIKI_NAME_SUSPECT_READJUDICATION",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "predecessor_rows": len(predecessor),
        "unique_nonplausible_names": len(suspects),
        "class_counts": dict(counts),
        "blanket_rejection": False,
        "wikipedia_is_not_factual_verification": True,
        "sample": suspects[:200],
    }
    out = OUT / "science" / "CYCLE32_WIKI_NAME_SUSPECT_READJUDICATION.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "unique_nonplausible_names": len(suspects),
                "class_counts": dict(counts),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
