"""Cache-only Cycle32 reparse of official staff HTML with program identity.

Writes private successors. Does not overwrite Cycle30 predecessor files.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

JsonRow = dict[str, Any]

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    CoachingError,
    PRIMARY_ROLES,
    excluded_official_role_spans,
    fill_current_role_matrix,
    html_is_not_found_shell,
    html_is_waf_challenge,
    parse_official_staff_html,
    parse_official_staff_json,
    redact_personal_contact,
    role_families_from_title,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402

WORK = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
RAW = WORK / "raw" / "official_staff"
PRED_OUT = WORK / "outputs"
DEFAULT_OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[JsonRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")



def cache_file(url: str) -> Path:
    return RAW / f"{sha256_json({'url': url})}.html"


def parse_cached(
    body: bytes,
    *,
    page_url: str,
    program_name: str,
    excluded_spans: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    html = redact_personal_contact(body.decode("utf-8", "replace"))
    if html_is_waf_challenge(html) or html_is_not_found_shell(html):
        raise CoachingError("cached page is a WAF or not-found shell")
    stripped = body.lstrip()
    people: list[dict[str, str]] = []
    if stripped.startswith(b"{") or stripped.startswith(b"["):
        try:
            payload = json.loads(html)
        except json.JSONDecodeError:
            payload = None
        if payload is not None:
            people = parse_official_staff_json(payload, page_url=page_url)
    if not people:
        people = parse_official_staff_html(
            html,
            page_url=page_url,
            program_name=program_name,
            excluded_spans=excluded_spans,
        )
    return people


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--reuse-parsed",
        action="store_true",
        help="Rebuild the matrix from existing Cycle32 parsed people; skip HTML.",
    )
    args = parser.parse_args()
    out = Path(args.out_root)
    as_of = utc_now()
    programs = load_jsonl(PRED_OUT / "CURRENT_2026_PROGRAMS.jsonl")
    attempts = load_jsonl(PRED_OUT / "OFFICIAL_STAFF_HTTP_ATTEMPTS.jsonl")
    repaired = load_jsonl(DEFAULT_OUT / "science" / "CYCLE32_REPAIRED_STAFF_ATTEMPTS.jsonl")
    predecessor_cells = load_jsonl(PRED_OUT / "CURRENT_NATIONAL_HC_OC_DC_MATRIX.jsonl")
    predecessor_people = load_jsonl(PRED_OUT / "OFFICIAL_STAFF_PARSED.jsonl")
    attempt_by_program = {str(row["program_id"]): row for row in attempts}
    for row in repaired:
        if str(row.get("status") or "") == "CAPTURED" and row.get("page_url"):
            attempt_by_program[str(row["program_id"])] = row
    people_by_program: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_bindings: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    excluded_spans: list[dict[str, Any]] = []
    parse_failures = 0
    missing_cache = 0
    if args.reuse_parsed:
        prior_excluded = out / "science" / "CYCLE32_EXCLUDED_SPANS.jsonl"
        if prior_excluded.is_file():
            excluded_spans.extend(
                row
                for row in load_jsonl(prior_excluded)
                if str(row.get("reason_code") or "")
                not in {
                    "HEAD_COACH_DUPLICATE_COORDINATOR_TITLE",
                    "VUE_ZIP_OPPOSITE_COORDINATOR",
                    "BARE_HEAD_COACH_ON_EXCLUSIVE_COORDINATOR",
                }
            )
        for person in load_jsonl(out / "science" / "CYCLE32_OFFICIAL_STAFF_PARSED.jsonl"):
            title = str(person.get("title") or "")
            families = role_families_from_title(title)
            if families:
                person["role"] = families[0]
            elif person.get("role") in PRIMARY_ROLES:
                person["role"] = "OTHER_POSITION"
            people_by_program[str(person.get("program_id") or "")].append(person)
        source_bindings = load_jsonl(out / "science" / "CYCLE32_SOURCE_BINDINGS.jsonl")
        quarantined = list(
            (
                json.loads(
                    (out / "science" / "CYCLE32_QUARANTINED_BINDINGS.json").read_text(
                        encoding="utf-8"
                    )
                )
                or {}
            ).get("rows")
            or []
        ) if (out / "science" / "CYCLE32_QUARANTINED_BINDINGS.json").is_file() else []
    else:
        for program in programs:
            pid = str(program["program_id"])
            display = str(program.get("display_name") or "")
            attempt = attempt_by_program.get(pid)
            url = str((attempt or {}).get("page_url") or "")
            binding = {
                "program_id": pid,
                "display_name": display,
                "classification": program.get("classification"),
                "page_url": url or None,
                "status": "NO_CAPTURE_ATTEMPT",
            }
            if not attempt or not url:
                binding["status"] = str((attempt or {}).get("status") or "NO_CAPTURE_ATTEMPT")
                source_bindings.append(binding)
                continue
            cache = cache_file(url)
            if not cache.is_file() or cache.stat().st_size == 0:
                missing_cache += 1
                binding["status"] = "CACHE_MISSING"
                source_bindings.append(binding)
                continue
            body = cache.read_bytes()
            binding["raw_sha256"] = sha256_bytes(body)
            parse_excluded: list[dict[str, Any]] = []
            try:
                people = parse_cached(
                    body,
                    page_url=url,
                    program_name=display,
                    excluded_spans=parse_excluded,
                )
            except CoachingError as exc:
                parse_failures += 1
                reason = str(exc)
                binding["status"] = "QUARANTINED_IDENTITY_OR_PARSE"
                binding["reason"] = reason
                quarantined.append({**binding, "reason": reason})
                source_bindings.append(binding)
                continue
            for person in people:
                people_by_program[pid].append(
                    {
                        **person,
                        "program_id": pid,
                        "display_name": display,
                        "artifact_class": "REAL_EVIDENCE",
                        "pit_admitted": False,
                    }
                )
            for row in parse_excluded:
                excluded_spans.append(
                    {
                        **row,
                        "program_id": pid,
                        "display_name": display,
                    }
                )
            binding["status"] = "VERIFIED_BINDING" if people else "CAPTURED_EMPTY_PARSE"
            binding["people_count"] = len(people)
            source_bindings.append(binding)

    empty_cells = [
        {
            "program_id": row["program_id"],
            "role": row["role"],
            "as_of_utc": as_of,
        }
        for row in predecessor_cells
    ]
    filled = fill_current_role_matrix(
        empty_cells,
        programs=programs,
        cfbd_hc_by_school={},
        official_people_by_program=people_by_program,
        official_attempts_by_program=attempt_by_program,
        sportradar_people_by_program={},
        sportradar_attempts_by_program={},
        wikimedia_people_by_program={},
    )
    all_people = [row for rows in people_by_program.values() for row in rows]
    display_by_id = {
        str(row["program_id"]): str(row.get("display_name") or "") for row in programs
    }
    for pid, people in people_by_program.items():
        for row in excluded_official_role_spans(people, program_id=pid):
            excluded_spans.append({**row, "display_name": display_by_id.get(pid)})
    role_counts = Counter(str(row.get("role") or "") for row in all_people)
    unique_people = {(row.get("program_id"), str(row.get("person") or "").casefold()) for row in all_people}
    disp_counts = Counter(str(row.get("disposition") or "") for row in filled)
    pred_disp = Counter(str(row.get("disposition") or "") for row in predecessor_cells)
    pred_confirmed = [
        row
        for row in predecessor_cells
        if str(row.get("disposition") or "").startswith("CONFIRMED")
    ]
    re_adjudicated = []
    for old in pred_confirmed:
        key = (str(old["program_id"]), str(old["role"]))
        new = next(
            (
                row
                for row in filled
                if str(row["program_id"]) == key[0] and str(row["role"]) == key[1]
            ),
            None,
        )
        old_people = tuple(
            str(item.get("person") or "")
            for item in (old.get("episode_refs") or [])
        )
        new_people = tuple(
            str(item.get("person") or "")
            for item in ((new or {}).get("episode_refs") or [])
        )
        re_adjudicated.append(
            {
                "program_id": key[0],
                "role": key[1],
                "predecessor_disposition": old.get("disposition"),
                "successor_disposition": (new or {}).get("disposition"),
                "predecessor_people": list(old_people),
                "successor_people": list(new_people),
                "people_changed": old_people != new_people,
            }
        )
    wrong_school_names = (
        "Arizona",
        "Illinois",
        "Kansas",
        "Louisiana",
        "New Mexico",
        "Ohio",
        "Southern",
        "Tennessee State",
        "Utah",
    )
    name_by_id = {str(row["program_id"]): str(row.get("display_name") or "") for row in programs}
    wrong_school_cells = [
        row
        for row in filled
        if name_by_id.get(str(row["program_id"])) in wrong_school_names
    ]
    asu = next((row for row in programs if row.get("display_name") == "Arizona State"), None)
    clemson = next((row for row in programs if row.get("display_name") == "Clemson"), None)
    asu_people = people_by_program.get(str((asu or {}).get("program_id") or ""), [])
    clemson_people = people_by_program.get(str((clemson or {}).get("program_id") or ""), [])
    asu_hc = [row for row in asu_people if row.get("role") == "head_coach"]
    clemson_hc = [row for row in clemson_people if row.get("role") == "head_coach"]
    washington = next(
        (row for row in programs if row.get("display_name") == "Washington"),
        None,
    )
    washington_id = str((washington or {}).get("program_id") or "")
    washington_cells = [
        row for row in filled if str(row.get("program_id") or "") == washington_id
    ]
    summary = {
        "artifact_type": "CYCLE32_OFFICIAL_STAFF_REPARSE_SUMMARY",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": as_of,
        "predecessor_as_of_utc": "2026-09-07T16:00:00Z",
        "predecessor_not_overwritten": True,
        "current_expected_programs": len(programs),
        "source_bindings": len(source_bindings),
        "verified_bindings": sum(
            1 for row in source_bindings if row.get("status") == "VERIFIED_BINDING"
        ),
        "quarantined_bindings": len(quarantined),
        "missing_cache": missing_cache,
        "parse_failures": parse_failures,
        "raw_people_rows": len(all_people),
        "unique_people": len(unique_people),
        "appointments": len(all_people),
        "role_counts": dict(role_counts),
        "predecessor_people_rows": len(predecessor_people),
        "matrix_cells": len(filled),
        "successor_disposition_counts": dict(disp_counts),
        "predecessor_disposition_counts": dict(pred_disp),
        "predecessor_confirmed_cells": len(pred_confirmed),
        "re_adjudicated_confirmed_cells": len(re_adjudicated),
        "confirmed_people_changed": sum(1 for row in re_adjudicated if row["people_changed"]),
        "wrong_school_named_programs": wrong_school_names,
        "wrong_school_successor_dispositions": dict(
            Counter(str(row.get("disposition") or "") for row in wrong_school_cells)
        ),
        "arizona_state_head_coach_count": len(asu_hc),
        "arizona_state_head_coach_people": [row.get("person") for row in asu_hc],
        "clemson_head_coach_count": len(clemson_hc),
        "clemson_head_coach_people": [row.get("person") for row in clemson_hc],
        "washington_role_dispositions": {
            str(row.get("role")): {
                "disposition": row.get("disposition"),
                "people": [
                    item.get("person") for item in (row.get("episode_refs") or [])
                ],
                "source": (
                    (row.get("episode_refs") or [{}])[0].get("source")
                    if row.get("episode_refs")
                    else None
                ),
                "dual_occupancy_with": (
                    (row.get("episode_refs") or [{}])[0].get("dual_occupancy_with")
                    if row.get("episode_refs")
                    else None
                ),
            }
            for row in washington_cells
        },
        "unknown_head_coaches": [
            {
                "program_id": row.get("program_id"),
                "display_name": name_by_id.get(str(row.get("program_id"))),
            }
            for row in filled
            if row.get("role") == "head_coach"
            and row.get("disposition") == "UNKNOWN_NOT_LISTED"
        ],
        "model_admission": "NOT_ADMITTED",
        "trust_classification": "UNTRUSTED_SHADOW",
        "excluded_span_count": len(excluded_spans),
        "excluded_reason_counts": dict(
            Counter(str(row.get("reason_code") or "") for row in excluded_spans)
        ),
    }
    write_jsonl(out / "science" / "CYCLE32_OFFICIAL_STAFF_PARSED.jsonl", all_people)
    write_jsonl(out / "science" / "CYCLE32_SOURCE_BINDINGS.jsonl", source_bindings)
    write_jsonl(out / "science" / "CYCLE32_CURRENT_HC_OC_DC_MATRIX.jsonl", filled)
    write_jsonl(
        out / "science" / "CYCLE32_CONFIRMED_CELL_READJUDICATION.jsonl", re_adjudicated
    )
    write_json(out / "science" / "CYCLE32_OFFICIAL_STAFF_REPARSE_SUMMARY.json", summary)
    write_json(out / "science" / "CYCLE32_QUARANTINED_BINDINGS.json", {"rows": quarantined})
    write_jsonl(out / "science" / "CYCLE32_EXCLUDED_SPANS.jsonl", excluded_spans)
    print(json.dumps({k: summary[k] for k in (
        "current_expected_programs",
        "verified_bindings",
        "quarantined_bindings",
        "raw_people_rows",
        "unique_people",
        "successor_disposition_counts",
        "arizona_state_head_coach_count",
        "clemson_head_coach_count",
        "confirmed_people_changed",
        "washington_role_dispositions",
        "unknown_head_coaches",
        "excluded_span_count",
        "excluded_reason_counts",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
