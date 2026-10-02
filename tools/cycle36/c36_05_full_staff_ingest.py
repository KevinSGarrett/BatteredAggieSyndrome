"""R36-05: every cached staff capture and every row it contains.

MR35R-06: Cycle #35 delivered an 880-row HC/OC/DC reference slice. The
requirement is the whole cache -- position coaches, special teams, analysts,
strength staff, general managers, recruiting and player-personnel staff --
each with its exact source title, each with a disposition, and none of them
promoted into HC/OC/DC or given an invented position.

This tool makes one pass over the mounted official-staff cache and answers
three questions per capture and per row:

1. **What is this file?**  Every file in the cache is inventoried, hashed,
   and classified: bound to a declared acquisition attempt, an unbound
   candidate capture from a URL that was tried and not adopted, a
   not-found shell, a bot challenge, or non-HTML. An unbound capture has no
   program binding, so its rows are *retained as candidates* and never
   counted as program evidence. That is a disposition, not a deletion.

2. **What does the row claim?**  The raw title is preserved verbatim and
   decomposed by the existing versioned taxonomy
   (``aggie_analytics.cycle33.role_taxonomy.assignments_from_title``), which
   already distinguishes principal from assistant, keeps co-roles, and emits
   ``unmapped_title_review_required`` rather than guessing. Nothing here
   invents a role the title does not contain.

3. **Is the claim supported by the same record?**  Person and title are
   bound through ``aggie_analytics.cycle33.span_locate.bind_person_role``,
   and the record's offset is then handed to the Cycle #36 record-scoped
   season binder, so a season is attached only when a heading that governs
   *that record* states one.

Counts are published by program, season, role family, source class and
evidence tier, with unknown cells kept visible. The predecessor's 8,371
parsed rows and 880-row slice are reconciled against this pass rather than
used as a target.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    CoachingError,
    html_is_not_found_shell,
    html_is_waf_challenge,
    parse_official_staff_html,
)
from aggie_analytics import atomic_io as _bas_atomic
from aggie_analytics.cycle33.role_taxonomy import (  # noqa: E402
    TAXONOMY_VERSION,
    assignments_from_title,
)
from aggie_analytics.cycle33.span_locate import bind_person_role  # noqa: E402
from aggie_analytics.cycle36.source_scoped_season import (  # noqa: E402
    PARSER_VERSION as SEASON_PARSER_VERSION,
)
from aggie_analytics.cycle36.source_scoped_season import (  # noqa: E402
    scan_capture,
    season_for_record,
)

CYCLE30 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
STAFF_CACHE = CYCLE30 / "raw" / "official_staff"
ATTEMPTS = CYCLE30 / "outputs" / "OFFICIAL_STAFF_HTTP_ATTEMPTS.jsonl"
PREDECESSOR_PARSED = CYCLE30 / "outputs" / "OFFICIAL_STAFF_PARSED.jsonl"
PREDECESSOR_SLICE = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260920T172801Z"
    r"\implementation_output\R35_02_STAFF_REBUILD_ROWS.jsonl"
)

CAPTURE_BOUND = "BOUND_TO_A_DECLARED_ACQUISITION_ATTEMPT"
CAPTURE_UNBOUND = "UNBOUND_CANDIDATE_CAPTURE_NO_DECLARED_ATTEMPT"
CAPTURE_NOT_FOUND = "NOT_FOUND_SHELL"
CAPTURE_CHALLENGE = "BOT_CHALLENGE_OR_WAF_INTERSTITIAL"
CAPTURE_NON_HTML = "NON_HTML_PAYLOAD"
CAPTURE_UNREADABLE = "UNREADABLE"
CAPTURE_EMPTY = "PARSED_ZERO_STAFF_ROWS"

TIER_OFFICIAL_BOUND = "OFFICIAL_HTML_RECORD_BOUND"
TIER_OFFICIAL_STRING = "OFFICIAL_HTML_STRING_LOCATED_ONLY"
TIER_CANDIDATE_UNBOUND_CAPTURE = "CANDIDATE_FROM_UNBOUND_CAPTURE"

#: Role families that may never be produced by promotion. A row whose
#: decomposition contains none of these keeps its own codes.
CORE_FAMILIES = ("head_coach", "offensive_coordinator", "defensive_coordinator")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_jsonl(path: Path, expected_rows: int) -> dict[str, Any]:
    """Re-read a written JSONL and prove every row survived the write.

    A 35 MB artifact written once and never read back is not evidence. This
    run produced a file whose row count matched while eleven records were
    truncated mid-value, which only a post-write parse could catch. The
    verification is therefore part of producing the artifact, not an optional
    check afterwards.
    """

    text = path.read_text(encoding="utf-8")
    parsed = 0
    broken: list[int] = []
    for index, line in enumerate(text.split("\n")):
        if not line.strip():
            continue
        try:
            json.loads(line)
            parsed += 1
        except ValueError:
            broken.append(index)
    # ``splitlines`` breaks on separators ``split`` does not; a disagreement
    # means a record contains a raw line separator, which is itself a defect.
    separator_disagreement = len(
        [line for line in text.splitlines() if line.strip()]
    ) - parsed - len(broken)
    return {
        "path": str(path),
        "expected_rows": expected_rows,
        "parsed_rows": parsed,
        "broken_line_indexes": broken[:20],
        "broken_lines": len(broken),
        "separator_disagreement": separator_disagreement,
        "verified": (
            parsed == expected_rows and not broken and separator_disagreement == 0
        ),
        "sha256": digest_bytes(path.read_bytes()),
    }


def classify_capture(path: Path, data: bytes) -> tuple[str, str | None]:
    """A capture's kind, decided from its bytes rather than its extension."""

    if path.suffix.casefold() not in {".html", ".htm", ".bin", ".json", ""}:
        return CAPTURE_NON_HTML, f"unexpected suffix {path.suffix!r}"
    head = data[:2048].decode("utf-8", errors="replace").casefold()
    if path.suffix.casefold() == ".json" or head.lstrip().startswith(("{", "[")):
        return CAPTURE_NON_HTML, "payload is JSON, not a staff HTML directory"
    text = data.decode("utf-8", errors="replace")
    if html_is_not_found_shell(text):
        return CAPTURE_NOT_FOUND, "server returned a not-found shell"
    if html_is_waf_challenge(text):
        return CAPTURE_CHALLENGE, "server returned a bot-challenge interstitial"
    return "HTML", None


def iterate_captures(directory: Path) -> Iterable[tuple[Path, bytes]]:
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        try:
            yield path, path.read_bytes()
        except OSError:
            yield path, b""


def ingest(
    out_dir: Path,
    cache: Path = STAFF_CACHE,
    limit: int | None = None,
) -> dict[str, Any]:
    attempts = read_jsonl(ATTEMPTS)
    by_receipt: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        identity = str(attempt.get("receipt_identity") or "")
        if identity:
            by_receipt.setdefault(identity, attempt)

    out_dir.mkdir(parents=True, exist_ok=True)
    capture_path = out_dir / "CYCLE36_STAFF_CAPTURE_INVENTORY.jsonl"
    rows_path = out_dir / "CYCLE36_STAFF_OBSERVATION_ROWS.jsonl"
    # Written to a temporary name, flushed to disk, then renamed into place,
    # so a reader never sees a partially written artifact.
    capture_tmp = capture_path.with_suffix(".jsonl.partial")
    rows_tmp = rows_path.with_suffix(".jsonl.partial")

    capture_states: collections.Counter = collections.Counter()
    role_counts: collections.Counter = collections.Counter()
    occupancy_counts: collections.Counter = collections.Counter()
    tier_counts: collections.Counter = collections.Counter()
    season_states: collections.Counter = collections.Counter()
    by_program_season: collections.Counter = collections.Counter()
    unmapped_titles: collections.Counter = collections.Counter()
    duplicate_digests: collections.Counter = collections.Counter()
    rows_written = 0
    captures_seen = 0
    bytes_seen = 0

    with _bas_atomic.open_write(capture_tmp, "w", encoding="utf-8", newline="\n") as captures_out, \
            _bas_atomic.open_write(rows_tmp, "w", encoding="utf-8", newline="\n") as rows_out:
        for path, data in iterate_captures(cache):
            if limit is not None and captures_seen >= limit:
                break
            captures_seen += 1
            bytes_seen += len(data)
            digest = digest_bytes(data) if data else None
            if digest:
                duplicate_digests[digest] += 1
            attempt = by_receipt.get(digest or "")
            kind, reason = classify_capture(path, data)
            record: dict[str, Any] = {
                "capture_path": str(path),
                "request_identity_from_filename": path.stem,
                "bytes": len(data),
                "payload_sha256": digest,
                "payload_kind": kind,
                "payload_reason": reason,
                "declared_attempt": (
                    {
                        "program_id": attempt.get("program_id"),
                        "display_name": attempt.get("display_name"),
                        "page_url": attempt.get("page_url"),
                        "classification": attempt.get("classification"),
                        "http_status": attempt.get("http_status"),
                        "receipt_identity": attempt.get("receipt_identity"),
                    }
                    if attempt
                    else None
                ),
            }
            if not data:
                record["capture_state"] = CAPTURE_UNREADABLE
                capture_states[CAPTURE_UNREADABLE] += 1
                captures_out.write(json.dumps(record, sort_keys=True) + "\n")
                continue
            if kind != "HTML":
                record["capture_state"] = kind
                capture_states[kind] += 1
                captures_out.write(json.dumps(record, sort_keys=True) + "\n")
                continue

            text = data.decode("utf-8", errors="replace")
            page_url = (attempt or {}).get("page_url") or f"cache://{path.stem}"
            try:
                parsed = parse_official_staff_html(text, page_url=page_url)
                parse_error = None
            except CoachingError as error:
                parsed = []
                parse_error = str(error)
            record["parse_error"] = parse_error
            record["parsed_rows"] = len(parsed)

            binding_state = CAPTURE_BOUND if attempt else CAPTURE_UNBOUND
            if not parsed:
                record["capture_state"] = CAPTURE_EMPTY
                record["binding_state"] = binding_state
                capture_states[CAPTURE_EMPTY] += 1
                captures_out.write(json.dumps(record, sort_keys=True) + "\n")
                continue

            record["capture_state"] = binding_state
            record["binding_state"] = binding_state
            capture_states[binding_state] += 1

            scanned = scan_capture(text)
            record["admissible_season_labels"] = len(scanned.admissible())
            captures_out.write(json.dumps(record, sort_keys=True) + "\n")

            for index, row in enumerate(parsed):
                person = str(row.get("person") or "")
                title = str(row.get("title") or "")
                binding = bind_person_role(text, person=person, title=title)
                offset = binding.get("body_offset")
                season = season_for_record(scanned, offset)
                assignments = assignments_from_title(title)
                families = sorted({a["role"] for a in assignments})
                tier = (
                    TIER_CANDIDATE_UNBOUND_CAPTURE
                    if not attempt
                    else (
                        TIER_OFFICIAL_BOUND
                        if binding.get("person_record_bound")
                        else TIER_OFFICIAL_STRING
                    )
                )
                observation = {
                    "observation_index": index,
                    "capture_path": str(path),
                    "payload_sha256": digest,
                    "program_id": (attempt or {}).get("program_id"),
                    "display_name": (attempt or {}).get("display_name"),
                    "classification": (attempt or {}).get("classification"),
                    "page_url": page_url,
                    "person": person,
                    "source_title": title,
                    "predecessor_role_label": row.get("role"),
                    "span_id": row.get("span_id"),
                    "assignments": assignments,
                    "role_codes": families,
                    "is_core_family": any(f in CORE_FAMILIES for f in families),
                    "taxonomy_version": TAXONOMY_VERSION,
                    "person_record_bound": binding.get("person_record_bound"),
                    "role_claim_supported": binding.get("role_claim_supported"),
                    "reject_reason": binding.get("reject_reason"),
                    "record_selector": binding.get("record_selector"),
                    "record_title": binding.get("record_title"),
                    "record_person": binding.get("record_person"),
                    "record_kind": binding.get("record_kind"),
                    "string_located": binding.get("string_located"),
                    "person_body_offset": offset,
                    "contrary_records": binding.get("contrary_records") or [],
                    "evidence_tier": tier,
                    "season_state": season["state"],
                    "season": season["bound_season"],
                    "season_parser_version": SEASON_PARSER_VERSION,
                    "season_bound_by": season.get("bound_by"),
                    "source_class": "OFFICIAL_STAFF_HTML",
                    "pit_admitted": False,
                    "admission_note": (
                        "Descriptive source observation. Not a point-in-time "
                        "admissible input and not a play-calling claim."
                    ),
                }
                rows_out.write(json.dumps(observation, sort_keys=True) + "\n")
                rows_written += 1
                tier_counts[tier] += 1
                season_states[season["state"]] += 1
                for assignment in assignments:
                    role_counts[assignment["role"]] += 1
                    occupancy_counts[assignment["occupancy"]] += 1
                    if assignment["role"] == "unmapped_title_review_required":
                        unmapped_titles[title[:120]] += 1
                if observation["program_id"]:
                    by_program_season[
                        (observation["program_id"], observation["season"])
                    ] += 1

        captures_out.flush()
        os.fsync(captures_out.fileno())
        rows_out.flush()
        os.fsync(rows_out.fileno())
    os.replace(capture_tmp, capture_path)
    os.replace(rows_tmp, rows_path)
    capture_verification = verify_jsonl(capture_path, captures_seen)
    rows_verification = verify_jsonl(rows_path, rows_written)

    predecessor_parsed = read_jsonl(PREDECESSOR_PARSED)
    predecessor_slice = read_jsonl(PREDECESSOR_SLICE)
    predecessor_roles = collections.Counter(
        str(row.get("role")) for row in predecessor_parsed
    )

    summary = {
        "artifact_type": "CYCLE36_FULL_STAFF_INGEST",
        "generated_at_utc": utc_now(),
        "cache": str(cache),
        "captures_examined": captures_seen,
        "capture_bytes": bytes_seen,
        "capture_states": dict(capture_states),
        "distinct_payload_digests": len(duplicate_digests),
        "captures_sharing_a_digest": sum(
            count for count in duplicate_digests.values() if count > 1
        ),
        "declared_attempts": len(attempts),
        "declared_attempts_matched_by_digest": len(
            {
                digest
                for digest in duplicate_digests
                if digest in by_receipt
            }
        ),
        "observation_rows": rows_written,
        "role_code_counts": dict(role_counts.most_common()),
        "occupancy_counts": dict(occupancy_counts),
        "evidence_tier_counts": dict(tier_counts),
        "season_states": dict(season_states),
        "program_season_cells": len(by_program_season),
        "cells_with_unknown_season": sum(
            1 for (_program, season) in by_program_season if season is None
        ),
        "rows_by_program_season": [
            {"program_id": program, "season": season, "rows": count}
            for (program, season), count in sorted(
                by_program_season.items(),
                key=lambda item: (str(item[0][0]), item[0][1] or 0),
            )
        ],
        "unmapped_title_examples": dict(unmapped_titles.most_common(40)),
        "unmapped_title_total": sum(unmapped_titles.values()),
        "predecessor_reconciliation": {
            "OFFICIAL_STAFF_PARSED.jsonl": {
                "rows": len(predecessor_parsed),
                "roles": dict(predecessor_roles),
                "relationship": (
                    "Predecessor observation count to reconcile, not a target. "
                    "It labelled every non-core row OTHER_POSITION; this pass "
                    "replaces that single bucket with the versioned taxonomy's "
                    "own codes and keeps the raw title on every row."
                ),
            },
            "R35_02_STAFF_REBUILD_ROWS.jsonl": {
                "rows": len(predecessor_slice),
                "relationship": (
                    "The 880-row HC/OC/DC reference slice. It is a subset of "
                    "this pass, not its scope."
                ),
            },
        },
        "no_promotion": (
            "A row whose title decomposes to no core family keeps its own "
            "codes. Nothing is promoted to head coach, offensive coordinator "
            "or defensive coordinator, and no generic position is invented for "
            "an unmapped title."
        ),
        "written": {
            "captures": str(capture_path),
            "observations": str(rows_path),
        },
        "post_write_verification": {
            "captures": capture_verification,
            "observations": rows_verification,
            "both_verified": (
                capture_verification["verified"] and rows_verification["verified"]
            ),
            "why": (
                "Every written row is parsed back from the file on disk. A row "
                "count that matches while a record is truncated mid-value is "
                "exactly the failure this catches."
            ),
        },
    }
    _bas_atomic.write_text(out_dir / "CYCLE36_FULL_STAFF_INGEST.json", 
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=STAFF_CACHE)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    summary = ingest(args.out_dir, args.cache, args.limit)
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "captures_examined",
                    "capture_states",
                    "observation_rows",
                    "evidence_tier_counts",
                    "season_states",
                    "program_season_cells",
                    "cells_with_unknown_season",
                    "unmapped_title_total",
                )
            }
            | {
                "post_write_verified": summary["post_write_verification"][
                    "both_verified"
                ],
                "broken_lines": summary["post_write_verification"]["observations"][
                    "broken_lines"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
