"""Identity-bound official staff fetch for named programs. Cycle32 successors only."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    CoachingError,
    PROGRAM_ATHLETICS_ORIGINS,
    official_staff_candidate_urls,
    parse_official_staff_html,
    parse_official_staff_json,
    primary_role_coverage,
    PRIMARY_ROLES,
    redact_personal_contact,
)
from aggie_analytics.cycle30.hashing import sha256_bytes  # noqa: E402
from tools.acquire_cycle30_official_staff import (  # noqa: E402
    BUDGET,
    fetch_html,
    useful_people,
)

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
PROGRAM_ID = "SRC-002:TEAM:3101"
DISPLAY = "Utah Tech"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-id", default=PROGRAM_ID)
    parser.add_argument("--display", default=DISPLAY)
    args = parser.parse_args()
    program_id = str(args.program_id)
    display = str(args.display)
    origin = PROGRAM_ATHLETICS_ORIGINS[program_id]
    ledger: list[dict[str, Any]] = []
    parsed_people: list[dict[str, str]] = []
    chosen_url = None
    last_receipt: dict[str, Any] | None = None
    for url in official_staff_candidate_urls(origin):
        body, receipt = fetch_html(url, ledger, BUDGET, cache_only=False)
        last_receipt = receipt
        if int(receipt.get("http_status") or 0) >= 400 or not body:
            continue
        html = redact_personal_contact(body.decode("utf-8", "replace"))
        people: list[dict[str, str]] = []
        stripped = body.lstrip()
        if stripped.startswith(b"{") or stripped.startswith(b"["):
            try:
                payload = json.loads(html)
            except json.JSONDecodeError:
                payload = None
            if payload is not None:
                people = parse_official_staff_json(payload, page_url=url)
        if not people:
            try:
                people = parse_official_staff_html(
                    html, page_url=url, program_name=display
                )
            except CoachingError:
                continue
        if useful_people(people) or (
            people
            and len(primary_role_coverage(people))
            > len(primary_role_coverage(parsed_people))
        ):
            parsed_people = people
            chosen_url = url
        if set(PRIMARY_ROLES) <= primary_role_coverage(people):
            break
    science = OUT / "science"
    attempts = [
        row
        for row in load_jsonl(science / "CYCLE32_REPAIRED_STAFF_ATTEMPTS.jsonl")
        if str(row.get("program_id")) != program_id
    ]
    people_rows = [
        row
        for row in load_jsonl(science / "CYCLE32_REPAIRED_STAFF_PEOPLE.jsonl")
        if str(row.get("program_id")) != program_id
    ]
    if parsed_people and chosen_url:
        attempts.append(
            {
                "program_id": program_id,
                "display_name": display,
                "status": "CAPTURED",
                "website": origin,
                "page_url": chosen_url,
                "parser": "parse_official_staff_html",
                "http_status": (last_receipt or {}).get("http_status"),
                "receipt_identity": sha256_bytes(
                    json.dumps(parsed_people, sort_keys=True).encode("utf-8")
                ),
                "attempt_count": 1,
                "artifact_class": "REAL_EVIDENCE",
                "as_of_utc": utc_now(),
                "identity_origin": "PROGRAM_ATHLETICS_ORIGINS",
            }
        )
        for person in parsed_people:
            people_rows.append(
                {
                    **person,
                    "program_id": program_id,
                    "display_name": display,
                    "page_url": chosen_url,
                    "artifact_class": "REAL_EVIDENCE",
                    "pit_admitted": False,
                }
            )
        status = "CAPTURED"
    else:
        attempts.append(
            {
                "program_id": program_id,
                "display_name": display,
                "status": "QUARANTINED_IDENTITY_OR_PARSE",
                "website": origin,
                "page_url": chosen_url or (last_receipt or {}).get("route"),
                "http_status": (last_receipt or {}).get("http_status"),
                "attempt_count": 1,
                "artifact_class": "REAL_EVIDENCE",
                "as_of_utc": utc_now(),
                "identity_origin": "PROGRAM_ATHLETICS_ORIGINS",
            }
        )
        status = "QUARANTINED_IDENTITY_OR_PARSE"
    write_jsonl(science / "CYCLE32_REPAIRED_STAFF_ATTEMPTS.jsonl", attempts)
    write_jsonl(science / "CYCLE32_REPAIRED_STAFF_PEOPLE.jsonl", people_rows)
    summary = {
        "artifact_type": "CYCLE32_PROGRAM_STAFF_FETCH",
        "program_id": program_id,
        "origin": origin,
        "status": status,
        "page_url": chosen_url,
        "people": len(parsed_people),
        "roles": sorted(primary_role_coverage(parsed_people)),
        "ledger": ledger,
        "predecessor_not_overwritten": True,
        "as_of_utc": utc_now(),
    }
    slug = display.replace(" ", "_").upper()
    (science / f"CYCLE32_{slug}_STAFF_FETCH.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
