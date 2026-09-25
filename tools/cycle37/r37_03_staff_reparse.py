"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-03 AC03/AC06-AC11: reparse every capture in the official staff cache and
every observation in it, with the school binding from the R37-03 source
identity crosswalk, the v37 season scope, name cleaning, own-record binding
with byte offsets, the v37 role corrections and sport exclusion.

Cycle #36 bound captures to programs by the first attempt in file order and
dated records with the v36.1 binder; its 16,428 observation rows were never
reparsed after the school repair. This pass reads the raw bytes again. Each
output row keeps the Cycle #36 observation it corresponds to (capture path
and index) and a field-by-field diff, so the change is a row list rather
than a total. Newly discovered cache members (files not in the Cycle #36
inventory) are enumerated and parsed like the rest.

Nothing here is point-in-time admissible, and no row is a play-calling
claim. A row is admitted for coverage only when its capture's program is
confirmed by the page's own identity, the person is bound to its own record
with the title on that record, and the record is not another sport's.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    CoachingError,
    html_is_not_found_shell,
    html_is_waf_challenge,
    parse_official_staff_html,
)
from aggie_analytics import atomic_io as _bas_atomic
from aggie_analytics.cycle33 import span_locate  # noqa: E402
from aggie_analytics.cycle37 import staff_record, staff_season_scope  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
TOOL_VERSION = "BAS-STAFF-REPARSE-v37.2"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
CACHE = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/raw/official_staff")
CROSSWALK_ROWS = ATTEMPT / "evidence" / "repairs" / "R37_03_SOURCE_IDENTITY_ROWS.jsonl"
CYCLE36 = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle36/runs/20260921T200027Z/implementation_output")
CYCLE36_ROWS = CYCLE36 / "CYCLE36_STAFF_OBSERVATION_ROWS.jsonl"
CYCLE36_CAPTURES = CYCLE36 / "CYCLE36_STAFF_CAPTURE_INVENTORY.jsonl"
CONFIRMED = "CONFIRMED_BY_SOURCE_IDENTITY"
CORE = ("head_coach", "offensive_coordinator", "defensive_coordinator")

TIER_BOUND = "OFFICIAL_HTML_RECORD_BOUND"
TIER_NOT_BOUND = "OFFICIAL_HTML_NOT_BOUND_TO_OWN_RECORD"
TIER_CANDIDATE = "CANDIDATE_CAPTURE_PROGRAM_NOT_CONFIRMED"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify(path: Path, data: bytes) -> tuple[str, str | None]:
    """The capture's kind from its bytes, as the Cycle #36 inventory decided it."""

    if not data:
        return "UNREADABLE", "empty or unreadable file"
    if path.suffix.casefold() not in {".html", ".htm", ".bin", ".json", ""}:
        return "NON_HTML_PAYLOAD", f"unexpected suffix {path.suffix!r}"
    head = data[:2048].decode("utf-8", errors="replace").casefold()
    if path.suffix.casefold() == ".json" or head.lstrip().startswith(("{", "[")):
        return "NON_HTML_PAYLOAD", "payload is JSON, not a staff HTML directory"
    text = data.decode("utf-8", errors="replace")
    if html_is_not_found_shell(text):
        return "NOT_FOUND_SHELL", "server returned a not-found shell"
    if html_is_waf_challenge(text):
        return "BOT_CHALLENGE_OR_WAF_INTERSTITIAL", "server returned a bot-challenge interstitial"
    return "HTML", None


def _principal(assignments: Iterable[dict[str, Any]]) -> list[str]:
    return sorted({a["role"] for a in assignments
                   if a["role"] in CORE and a["occupancy"] in ("PRINCIPAL", "CO_SHARED")})


def reparse_capture(path: Path, data: bytes, crosswalk: dict[str, Any] | None,
                    page_url_c36: str | None, delivered_program: str | None = None
                    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    digest = sha256(data) if data else None
    kind, reason = classify(path, data)
    identity = (crosswalk or {}).get("page_identity") or {}
    state = (crosswalk or {}).get("state") or "NEW_CACHE_MEMBER_NOT_IN_CROSSWALK"
    program = (crosswalk or {}).get("admitted_program_id") if state == CONFIRMED else None
    capture = {"capture_path": str(path), "payload_sha256": digest, "bytes": len(data), "payload_kind": kind,
               "payload_reason": reason, "identity_state": state, "program_id": program,
               "page_title": identity.get("title"), "page_canonical": identity.get("canonical_href")}
    if kind != "HTML":
        return capture, []
    text = data.decode("utf-8", "surrogateescape")
    page_url = page_url_c36 or f"cache://{path.stem}"
    try:
        parsed = parse_official_staff_html(text, page_url=page_url)
        capture["parse_error"] = None
    except CoachingError as error:
        parsed, capture["parse_error"] = [], str(error)
    capture["parsed_rows"] = len(parsed)
    if not parsed:
        return capture, []
    scanned = staff_season_scope.scan(text)
    records = span_locate.iter_staff_records(text)
    surnames = collections.Counter(
        staff_season_scope._surname(staff_record.clean_person(str(r.get("person") or ""))[0]).lower()
        for r in records)
    capture["season_labels"] = len(scanned.labels)
    rows = []
    for index, row in enumerate(parsed):
        raw_person = str(row.get("person") or "")
        person, removed = staff_record.clean_person(raw_person)
        title = str(row.get("title") or "")
        binding = staff_record.bind_record(text, data, person, title, records)
        chosen_title = staff_record.title_for_row(binding, title)
        title = chosen_title["title"]
        binding = {**binding, "role_claim_supported": chosen_title["role_claim_supported"],
                   "title_source": chosen_title["title_source"]}
        parsed_person = person
        person = binding.get("person_as_on_page") or person
        located = binding["char_offset"] if binding["person_record_bound"] else None
        shared = surnames.get(staff_season_scope._surname(person).lower(), 0) > 1
        season = staff_season_scope.season_for_record(scanned, located, person=person,
                                                       surname_shared_on_page=shared)
        section = (season.get("sport_section") or {}).get("state")
        sport = staff_record.sport_scope(title, section, identity.get("canonical_href") or page_url,
                                         identity.get("title"))
        assignments = staff_record.assignments_v37(title)
        tier = (TIER_CANDIDATE if program is None else TIER_BOUND if binding["person_record_bound"]
                else TIER_NOT_BOUND)
        admitted = bool(program and binding["person_record_bound"] and binding["role_claim_supported"]
                        and sport["football_role_admissible"])
        rows.append({
            "capture_path": str(path), "observation_index": index, "payload_sha256": digest,
            "program_id": program, "identity_state": state, "page_url": page_url,
            "delivered_program_id": delivered_program,
            "person_raw": raw_person, "person_parsed": parsed_person, "person": person,
            "person_cleaning_removed": removed,
            "source_title": title, "cycle36_title": chosen_title["cycle36_title"],
            "title_source": chosen_title["title_source"], "binding": binding, "evidence_tier": tier,
            "season": season["bound_season"], "season_state": season["state"],
            "source_effective_season": season["source_effective_season"],
            "announcement_date": season.get("announcement_date"), "season_bound_by": season.get("bound_by"),
            "season_parser_version": staff_season_scope.PARSER_VERSION,
            "sport_scope": sport, "assignments": assignments, "principal_core_roles": _principal(assignments),
            "taxonomy_version": staff_record.TAXONOMY_VERSION, "admitted_for_coverage": admitted,
            "pit_admitted": False,
        })
    return capture, rows


def diff_row(new: dict[str, Any], old: dict[str, Any] | None) -> dict[str, Any]:
    if old is None:
        return {"state": "NEW_ROW_NOT_IN_CYCLE36"}
    old_principal = sorted({a["role"] for a in old.get("assignments") or []
                            if a["role"] in CORE and a["occupancy"] in ("PRINCIPAL", "CO_SHARED")})
    changes = {}
    for name, before, after in (
        ("person", old.get("person"), new["person"]),
        ("source_title", old.get("source_title"), new["source_title"]),
        ("admitted_program_id", old.get("program_id"), new["program_id"]),
        ("season", old.get("season"), new["season"]),
        ("season_state", old.get("season_state"), new["season_state"]),
        ("principal_core_roles", old_principal, new["principal_core_roles"]),
        ("person_record_bound", old.get("person_record_bound"), new["binding"]["person_record_bound"]),
        ("role_codes", sorted({a["role"] for a in old.get("assignments") or []}),
         sorted({a["role"] for a in new["assignments"]})),
    ):
        if before != after:
            changes[name] = {"cycle36": before, "cycle37": after}
    return {"state": "CHANGED" if changes else "UNCHANGED", "changes": changes}


def build(out_dir: Path, limit: int | None = None) -> dict[str, Any]:
    started = time.time()
    crosswalk = {row["capture_path"]: row for row in read_jsonl(CROSSWALK_ROWS)}
    c36_captures = {row["capture_path"]: row for row in read_jsonl(CYCLE36_CAPTURES)}
    c36_rows = {(row["capture_path"], row["observation_index"]): row for row in read_jsonl(CYCLE36_ROWS)}
    files = sorted(path for path in CACHE.iterdir() if path.is_file())
    new_members = [str(path) for path in files if str(path) not in c36_captures]
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "R37_03_STAFF_REPARSE_ROWS.jsonl"
    captures_path = out_dir / "R37_03_STAFF_REPARSE_CAPTURES.jsonl"
    counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    seen_old: set[tuple[str, int]] = set()
    written = 0
    with _bas_atomic.open_write(rows_path, "w", encoding="utf-8", newline="\n") as rows_out, \
            _bas_atomic.open_write(captures_path, "w", encoding="utf-8", newline="\n") as caps_out:
        for number, path in enumerate(files):
            if limit is not None and number >= limit:
                break
            try:
                data = path.read_bytes()
            except OSError:
                data = b""
            c36 = c36_captures.get(str(path)) or {}
            page_url = (c36.get("declared_attempt") or {}).get("page_url")
            delivered = (c36.get("declared_attempt") or {}).get("program_id")
            capture, rows = reparse_capture(path, data, crosswalk.get(str(path)), page_url, delivered)
            capture["cycle36_capture_state"] = c36.get("capture_state")
            capture["new_cache_member"] = str(path) in new_members
            caps_out.write(json.dumps(capture, sort_keys=True) + "\n")
            counts["capture_kind"][capture["payload_kind"]] += 1
            counts["identity_state"][capture["identity_state"]] += 1
            for row in rows:
                key = (row["capture_path"], row["observation_index"])
                old = c36_rows.get(key)
                if old is not None:
                    seen_old.add(key)
                    row["cycle36_observation"] = {"capture_path": key[0], "observation_index": key[1]}
                row["diff"] = diff_row(row, old)
                rows_out.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")
                written += 1
                counts["row_diff"][row["diff"]["state"]] += 1
                for name in row["diff"].get("changes") or {}:
                    counts["changed_field"][name] += 1
                counts["season_state"][row["season_state"]] += 1
                counts["tier"][row["evidence_tier"]] += 1
                counts["sport"][f"{row['sport_scope']['scope']}|{row['sport_scope']['basis']}"] += 1
                counts["binding"][row["binding"]["state"]] += 1
                counts["admitted"][str(row["admitted_for_coverage"])] += 1
                if row["person_cleaning_removed"]:
                    counts["name_cleaning"]["CLEANED"] += 1
                for assignment in row["assignments"]:
                    if assignment["taxonomy_correction"]:
                        counts["taxonomy_correction"][assignment["taxonomy_correction"]] += 1
                dom = row["binding"].get("dom_row")
                if dom is not None:
                    counts["dom_row"]["CONTAINS_PERSON" if dom["row_contains_person"] else "DOES_NOT"] += 1
                if row["binding"].get("person_record_bound"):
                    counts["bytes_verified"][str(row["binding"].get("bytes_at_offset_are_the_name"))] += 1
    not_reproduced = sorted(set(c36_rows) - seen_old) if limit is None else []
    summary = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "tool_version": TOOL_VERSION,
        "requirement": "R37-03",
        "versions": {"season": staff_season_scope.PARSER_VERSION, "record": staff_record.RECORD_VERSION,
                     "taxonomy": staff_record.TAXONOMY_VERSION},
        "cache": str(CACHE), "files_in_cache": len(files), "files_processed": min(len(files), limit or len(files)),
        "cycle36_capture_references": len(c36_captures), "cycle36_observations": len(c36_rows),
        "new_cache_members": new_members,
        "rows_written": written,
        "cycle36_rows_not_reproduced": [{"capture_path": k[0], "observation_index": k[1]} for k in not_reproduced],
        "counts": {name: dict(counter.most_common()) for name, counter in sorted(counts.items())},
        "inputs": {"crosswalk": {"path": str(CROSSWALK_ROWS), "sha256": sha256(CROSSWALK_ROWS.read_bytes())},
                   "cycle36_rows": {"path": str(CYCLE36_ROWS), "sha256": sha256(CYCLE36_ROWS.read_bytes())},
                   "cycle36_captures": {"path": str(CYCLE36_CAPTURES),
                                        "sha256": sha256(CYCLE36_CAPTURES.read_bytes())}},
        "written": {"rows": str(rows_path), "captures": str(captures_path),
                    "rows_sha256": sha256(rows_path.read_bytes())},
        "elapsed_seconds": round(time.time() - started, 1),
        "not_claimed": ("Descriptive observations of official pages. No row is point-in-time admissible, and no "
                        "row claims play-calling."),
    }
    _bas_atomic.write_text(out_dir / "R37_03_STAFF_REPARSE.json", json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    summary = build(args.out, args.limit)
    print(json.dumps({k: summary[k] for k in ("files_in_cache", "files_processed", "rows_written",
                                              "elapsed_seconds")} | {"counts": summary["counts"],
                                                                     "new_members": len(summary["new_cache_members"]),
                                                                     "not_reproduced": len(summary["cycle36_rows_not_reproduced"])},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
