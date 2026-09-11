"""Join current official occupants to cached wiki career pages.

Writes Cycle32 successors. Does not overwrite predecessor career files.
Wikipedia careers are retrospective candidates, not PIT or verification.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.coaching import career_episode_roundtrip  # noqa: E402

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _fold_name(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


def main() -> int:
    matrix = load_jsonl(OUT / "science" / "CYCLE32_CURRENT_HC_OC_DC_MATRIX.jsonl")
    careers = load_jsonl(PRED / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl")
    successor_pages = [
        page
        for page in load_jsonl(OUT / "science" / "CYCLE32_WIKI_CAREER_PAGES_SUCCESSOR.jsonl")
        if str(page.get("status") or "") == "REVISION_BOUND"
    ]
    careers = [*careers, *successor_pages]
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in careers:
        keys = {_fold_name(str(page.get("title") or ""))}
        for episode in page.get("episodes") or []:
            keys.add(_fold_name(str(episode.get("person") or "")))
        keys.discard("")
        for key in keys:
            by_name[key].append(page)
    occupants: dict[tuple[str, str], dict[str, Any]] = {}
    for cell in matrix:
        if not str(cell.get("disposition") or "").startswith("CONFIRMED"):
            continue
        pid = str(cell.get("program_id") or "")
        for episode in cell.get("episode_refs") or []:
            person = str(episode.get("person") or "")
            key = (pid, _fold_name(person))
            if not pid or not person:
                continue
            if key not in occupants:
                occupants[key] = {
                    "program_id": pid,
                    "person": person,
                    "person_id": episode.get("person_id"),
                    "roles": [],
                }
            role = str(cell.get("role") or "")
            if role and role not in occupants[key]["roles"]:
                occupants[key]["roles"].append(role)
    successors: list[dict[str, Any]] = []
    matched = 0
    missing_page = 0
    nonempty_careers = 0
    pit_true = 0
    for occupant in occupants.values():
        pages = by_name.get(_fold_name(occupant["person"])) or []
        episodes = []
        for page in pages:
            episodes.extend(page.get("episodes") or [])
        payload = career_episode_roundtrip(
            program_id=occupant["program_id"],
            person=occupant["person"],
            career_episodes=episodes,
            source_person_id=occupant.get("person_id"),
        )
        if not pages:
            missing_page += 1
            status = "NO_CACHED_CAREER_PAGE"
        else:
            matched += 1
            status = "CAREER_CANDIDATE_BOUND" if payload["episode_cardinality"] else "PAGE_WITHOUT_MATCHED_EPISODES"
        if payload["episode_cardinality"]:
            nonempty_careers += 1
        pit_true += sum(1 for row in payload["episodes"] if row.get("pit_admitted") is True)
        successors.append(
            {
                **payload,
                "official_roles": occupant["roles"],
                "cached_career_pages": len(pages),
                "status": status,
                "wikipedia_is_not_factual_verification": True,
                "artifact_class": "REAL_EVIDENCE",
                "as_of_utc": utc_now(),
            }
        )
    summary = {
        "artifact_type": "CYCLE32_CURRENT_STAFF_CAREER_ROUNDTRIP",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "confirmed_occupants": len(occupants),
        "cached_career_pages": len(careers),
        "matched_cached_pages": matched,
        "missing_cached_pages": missing_page,
        "nonempty_career_episodes": nonempty_careers,
        "string_or_true_pit_promotions": pit_true,
        "predecessor_career_file_not_overwritten": str(
            PRED / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl"
        ),
        "successor_career_pages": len(successor_pages),
        "pit_admitted": False,
        "wikipedia_is_not_factual_verification": True,
        "play_caller_sourced": bool(
            (load_json(OUT / "science" / "CYCLE32_PLAY_CALLER_TITLE_SCAN.json") or {}).get(
                "play_caller_title_hits"
            )
        ),
    }
    science = OUT / "science"
    write_jsonl(science / "CYCLE32_CURRENT_STAFF_CAREER_ROUNDTRIP.jsonl", successors)
    write_json(science / "CYCLE32_CURRENT_STAFF_CAREER_ROUNDTRIP.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
