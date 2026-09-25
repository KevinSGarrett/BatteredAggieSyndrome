"""R36-06: ingest the scheme evidence that already exists, and only that.

MR35R-06/12: the delivered release has zero ``scheme_assertion`` and zero
``responsibility_assertion`` rows. Cycle #35 diagnosed that correctly -- the
evidence exists (19,271 scheme claims, 9,111 with text a source stated) and
the ingest route was never wired -- and then refused to ingest, because
binding a Wikimedia page title to a canonical program by string prefix
misattributed across genuinely different schools. Its own acceptance
predicate was: *a real page-title-to-program crosswalk that resolves titles
with zero many-to-one bindings across distinct schools*.

``aggie_analytics.cycle36.program_crosswalk`` is that crosswalk, and this
tool is the ingest the refusal was waiting for. Resolution is by exact match
against a source-declared school name, alternate name, or school-plus-mascot
spelling, so "Miami Hurricanes" and "Miami RedHawks" cannot land on one
program, and "Texas A&M-Commerce Lions" cannot land on Texas. A title that
matches nothing stays unresolved with its reason; a title that matches two
programs stays unresolved as well.

What this tool still refuses:

* A scheme is never inferred from a coach's title, reputation or a
  coordinator's presence. Only text a source stated is ingested.
* Nothing is promoted above its source's warrant. Every Cycle #33 claim is
  ``WIKIPEDIA_ONLY_NOT_OFFICIAL``, so every row lands at the candidate tier
  and keeps that provenance. PIT admission remains false.
* Schemes coexist. A program-season with two stated offensive families keeps
  both; nothing is last-write-wins and no single family is forced.
* The three ``SCHEME_SOURCE_TEXT_CONFLICT`` claims stay visible. They sit on
  a coach-era page with no stated season, so they reach no program-season
  cell -- and are therefore emitted in their own table rather than being
  counted as zero conflicts.

Play-calling responsibility is a separate table with a separate rule: only an
explicit source statement counts. A coordinator title is not play-calling,
and a pass-game or run-game coordinator title is not play-calling either.
Every statement the scan encounters gets a disposition, including the ones it
rejects.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402
from aggie_analytics.cycle36.jsonl_io import (  # noqa: E402
    read_jsonl_strict,
    write_jsonl_verified,
)
from aggie_analytics.cycle36.program_crosswalk import (  # noqa: E402
    build_crosswalk,
    conflict_report,
    load_payloads,
)

SCHEME_CLAIMS = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science\CYCLE33_SCHEME_TENURE_CLAIMS.jsonl"
)
RAW_TEAMS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\teams")
HISTORICAL_MEMBERSHIP = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs"
    r"\HISTORICAL_MEMBERSHIP_1963_2012.jsonl"
)

SCHEME_TAXONOMY_VERSION = "BAS-SCHEME-ASSERTION-v36.1"
RESPONSIBILITY_VERSION = "BAS-RESPONSIBILITY-SCAN-v36.1"

TIER_CANDIDATE = "CANDIDATE_SINGLE_SOURCE_NOT_OFFICIAL"

ADMITTED = "ADMITTED_CANDIDATE_SCHEME_ASSERTION"
UNRESOLVED_PROGRAM = "RETAINED_PROGRAM_UNRESOLVED"
NO_STATED_TEXT = "RETAINED_SOURCE_STATED_NOTHING"
NO_SEASON = "RETAINED_NO_STATED_SEASON"

#: Explicit play-calling statements. Each pattern must name the act of
#: calling plays; a coordinator title never appears here.
PLAY_CALLING_PATTERNS = (
    (r"\bplay[\s-]*caller\b", "TITLE_STATES_PLAY_CALLER"),
    (r"\bplay[\s-]*calling\s+(?:duties|responsibilit(?:y|ies))\b", "STATES_PLAY_CALLING_DUTIES"),
    (r"\bcalls?\s+the\s+(?:offensive\s+|defensive\s+)?plays\b", "STATES_CALLS_THE_PLAYS"),
    (r"\bwill\s+call\s+(?:the\s+)?plays\b", "STATES_WILL_CALL_PLAYS"),
    (r"\bresponsible\s+for\s+(?:calling\s+)?(?:the\s+)?play[\s-]*calling\b", "STATES_RESPONSIBLE_FOR_PLAY_CALLING"),
)

#: Titles that look adjacent to play-calling and are not it. Recorded as
#: rejected statements so the refusal is auditable rather than silent.
NOT_PLAY_CALLING_PATTERNS = (
    (r"\bpass(?:ing)?[\s-]*game\s+coordinator\b", "PASS_GAME_COORDINATOR_IS_NOT_PLAY_CALLING"),
    (r"\brun(?:ning)?[\s-]*game\s+coordinator\b", "RUN_GAME_COORDINATOR_IS_NOT_PLAY_CALLING"),
    (r"\boffensive\s+coordinator\b", "COORDINATOR_TITLE_IS_NOT_PLAY_CALLING"),
    (r"\bdefensive\s+coordinator\b", "COORDINATOR_TITLE_IS_NOT_PLAY_CALLING"),
    (r"\bhead\s+coach\b", "HEAD_COACH_TITLE_IS_NOT_PLAY_CALLING"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Strict read: a truncated artifact must be regenerated, never skipped."""

    return read_jsonl_strict(path)


def request_identity(endpoint: str, parameters: dict[str, Any]) -> str:
    return sha256_json({"endpoint": endpoint, "parameters": parameters})


def assertion_id(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "program": row.get("canonical_program_id"),
                "season": row.get("season"),
                "side": row.get("side"),
                "source_text": row.get("source_text"),
                "page_title": row.get("page_title"),
                "revision": row.get("wikimedia_revision"),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def ingest_schemes(crosswalk, claims: list[dict[str, Any]]) -> dict[str, Any]:
    scheme_claims = [row for row in claims if row.get("claim_kind") == "SCHEME"]
    resolution_cache: dict[tuple[str, Any], dict[str, Any]] = {}
    assertions: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    states: collections.Counter = collections.Counter()
    families: collections.Counter = collections.Counter()
    by_cell: dict[tuple[str, Any, str], list[dict[str, Any]]] = {}

    for claim in scheme_claims:
        page_title = str(claim.get("page_title") or claim.get("program_raw") or "")
        season_raw = claim.get("season")
        season = int(season_raw) if str(season_raw).isdigit() else None
        key = (page_title, season)
        if key not in resolution_cache:
            resolution_cache[key] = crosswalk.resolve(page_title, season)
        resolution = resolution_cache[key]

        stated = str(claim.get("source_text") or "").strip()
        side = (
            "OFFENSE"
            if claim.get("field") == "offensive_scheme"
            else "DEFENSE"
            if claim.get("field") == "defensive_scheme"
            else "UNKNOWN"
        )
        record = {
            "scheme_taxonomy_version": SCHEME_TAXONOMY_VERSION,
            "source_normalization_version": claim.get("normalization_version"),
            "page_title": page_title,
            "program_raw": claim.get("program_raw"),
            "season": season,
            "season_stated": season_raw,
            "side": side,
            "field": claim.get("field"),
            "source_text": claim.get("source_text"),
            "normalized_families": claim.get("normalized") or [],
            "family_tags": claim.get("family_tags") or [],
            "source_disposition": claim.get("disposition"),
            "conflict_distinct_source_text": bool(
                claim.get("conflict_distinct_source_text")
            ),
            "conflict_texts": claim.get("conflict_texts") or [],
            "wikimedia_revision": claim.get("wikimedia_revision"),
            "official_corroboration": claim.get("official_corroboration"),
            "evidence_tier": TIER_CANDIDATE,
            "pit_admitted": False,
            "inferred_from_title": False,
            "not_play_calling": True,
            "not_measured_play_frequency": True,
            "program_resolution_state": resolution["state"],
            "canonical_program_id": resolution.get("canonical_program_id"),
            "candidate_program_ids": resolution.get("candidate_program_ids", []),
        }

        if record["conflict_distinct_source_text"]:
            # Kept in its own table so a season-less conflict is never counted
            # as zero conflicts by a query scoped to resolved cells.
            conflicts.append(dict(record))

        if not stated:
            record["state"] = NO_STATED_TEXT
        elif not record["canonical_program_id"]:
            record["state"] = UNRESOLVED_PROGRAM
        elif season is None:
            record["state"] = NO_SEASON
        else:
            record["state"] = ADMITTED
            record["assertion_id"] = assertion_id(record)
            by_cell.setdefault(
                (record["canonical_program_id"], season, side), []
            ).append(record)
            for family in record["normalized_families"]:
                families[family] += 1
        states[record["state"]] += 1
        assertions.append(record)

    coexisting = {
        f"{program}|{season}|{side}": sorted(
            {
                family
                for row in rows
                for family in row["normalized_families"]
            }
        )
        for (program, season, side), rows in by_cell.items()
        if len({tuple(row["normalized_families"]) for row in rows}) > 1
    }
    return {
        "scheme_claims_examined": len(scheme_claims),
        "states": dict(states),
        "assertions": assertions,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "admitted_cells": len(by_cell),
        "family_counts": dict(families.most_common()),
        "cells_with_more_than_one_stated_family": len(coexisting),
        "coexisting_examples": dict(list(coexisting.items())[:25]),
    }


def scan_responsibility(observation_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Every play-calling-shaped statement in the staff titles, dispositioned."""

    statements: list[dict[str, Any]] = []
    dispositions: collections.Counter = collections.Counter()
    for row in observation_rows:
        title = str(row.get("source_title") or "")
        if not title:
            continue
        lowered = title.casefold()
        admitted = None
        for pattern, code in PLAY_CALLING_PATTERNS:
            if re.search(pattern, lowered, re.I):
                admitted = code
                break
        if admitted:
            statements.append(
                {
                    "responsibility_version": RESPONSIBILITY_VERSION,
                    "person": row.get("person"),
                    "program_id": row.get("program_id"),
                    "season": row.get("season"),
                    "source_title": title,
                    "capture_path": row.get("capture_path"),
                    "payload_sha256": row.get("payload_sha256"),
                    "evidence_code": admitted,
                    "disposition": "ADMITTED_EXPLICIT_SOURCE_STATEMENT",
                    "inferred_from_role_title": False,
                    "pit_admitted": False,
                    "not_transferable_across_years": True,
                }
            )
            dispositions["ADMITTED_EXPLICIT_SOURCE_STATEMENT"] += 1
            continue
        for pattern, code in NOT_PLAY_CALLING_PATTERNS:
            if re.search(pattern, lowered, re.I):
                statements.append(
                    {
                        "responsibility_version": RESPONSIBILITY_VERSION,
                        "person": row.get("person"),
                        "program_id": row.get("program_id"),
                        "season": row.get("season"),
                        "source_title": title,
                        "capture_path": row.get("capture_path"),
                        "evidence_code": code,
                        "disposition": "REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT",
                        "inferred_from_role_title": False,
                        "pit_admitted": False,
                    }
                )
                dispositions["REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT"] += 1
                break
    return {
        "responsibility_version": RESPONSIBILITY_VERSION,
        "titles_examined": len(observation_rows),
        "statements": statements,
        "dispositions": dict(dispositions),
        "admitted": dispositions.get("ADMITTED_EXPLICIT_SOURCE_STATEMENT", 0),
        "rule": (
            "Only an explicit source statement about calling plays is "
            "admitted. A head-coach or coordinator title is recorded as a "
            "rejected candidate so the refusal is auditable, never as "
            "evidence. Responsibility is not transferred across years."
        ),
    }


_TAG = re.compile(r"<[^>]+>")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript|template)\b.*?</\1>")
_COMMENT = re.compile(r"(?s)<!--.*?-->")


def rendered_text(raw: str) -> str:
    """Visible text only. A play-calling claim inside a script is markup."""

    import html as html_lib

    text = _COMMENT.sub(" ", _HIDDEN.sub(" ", raw))
    return re.sub(r"\s+", " ", html_lib.unescape(_TAG.sub(" ", text)))


def scan_capture_text(observation_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Search the captures themselves, not only the staff titles.

    A title can say "Play Caller"; a biography paragraph can say "he will
    call the plays". Both are explicit source statements and both must be
    found, so the rendered text of every BOUND capture is scanned once. An
    unbound capture has no program to attribute a statement to, so its
    statements are recorded as unattributable rather than assigned.
    """

    by_capture: dict[str, dict[str, Any]] = {}
    for row in observation_rows:
        capture = str(row.get("capture_path") or "")
        if not capture or capture in by_capture:
            continue
        by_capture[capture] = {
            "program_id": row.get("program_id"),
            "display_name": row.get("display_name"),
            "season": row.get("season"),
            "payload_sha256": row.get("payload_sha256"),
            "evidence_tier": row.get("evidence_tier"),
        }

    statements: list[dict[str, Any]] = []
    states: collections.Counter = collections.Counter()
    captures_scanned = 0
    captures_unreadable = 0
    for capture in sorted(by_capture):
        path = Path(capture)
        if not path.is_file():
            captures_unreadable += 1
            continue
        captures_scanned += 1
        text = rendered_text(path.read_text(encoding="utf-8", errors="replace"))
        for pattern, code in PLAY_CALLING_PATTERNS:
            for match in re.finditer(pattern, text, re.I):
                context = by_capture[capture]
                attributable = bool(context.get("program_id"))
                start = max(0, match.start() - 220)
                statements.append(
                    {
                        "responsibility_version": RESPONSIBILITY_VERSION,
                        "capture_path": capture,
                        "payload_sha256": context.get("payload_sha256"),
                        "program_id": context.get("program_id"),
                        "display_name": context.get("display_name"),
                        "season": context.get("season"),
                        "evidence_code": code,
                        "matched_text": match.group(0)[:160],
                        "quoted_span": text[start : match.end() + 220],
                        "offset_in_rendered_text": match.start(),
                        "disposition": (
                            "ADMITTED_EXPLICIT_SOURCE_STATEMENT_IN_CAPTURE_TEXT"
                            if attributable
                            else "RETAINED_UNATTRIBUTABLE_NO_PROGRAM_BINDING"
                        ),
                        "person_attributed": None,
                        "person_attribution_note": (
                            "The statement is quoted with its surrounding span. "
                            "Attributing it to a specific person needs the "
                            "person to appear in the same record, which this "
                            "scan does not assert."
                        ),
                        "inferred_from_role_title": False,
                        "pit_admitted": False,
                    }
                )
                states[statements[-1]["disposition"]] += 1
    return {
        "captures_scanned": captures_scanned,
        "captures_unreadable": captures_unreadable,
        "statements": statements,
        "dispositions": dict(states),
        "rule": (
            "Only text a source rendered counts. A match inside a script, a "
            "style block or a comment is markup and is never scanned."
        ),
    }


def build(out_dir: Path, observation_rows_path: Path | None) -> dict[str, Any]:
    payloads = load_payloads(RAW_TEAMS, range(1963, 2027), request_identity)
    crosswalk = build_crosswalk(
        payloads, declared_name_rows=read_jsonl(HISTORICAL_MEMBERSHIP)
    )
    claims = read_jsonl(SCHEME_CLAIMS)
    schemes = ingest_schemes(crosswalk, claims)

    observation_rows = (
        read_jsonl(observation_rows_path) if observation_rows_path else []
    )
    responsibility = scan_responsibility(observation_rows)
    capture_scan = scan_capture_text(observation_rows)
    responsibility["statements"] = (
        responsibility["statements"] + capture_scan["statements"]
    )
    responsibility["capture_text_scan"] = {
        key: value for key, value in capture_scan.items() if key != "statements"
    }
    responsibility["admitted_from_capture_text"] = capture_scan["dispositions"].get(
        "ADMITTED_EXPLICIT_SOURCE_STATEMENT_IN_CAPTURE_TEXT", 0
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    scheme_rows = out_dir / "CYCLE36_SCHEME_ASSERTIONS.jsonl"
    conflict_rows = out_dir / "CYCLE36_SCHEME_CONFLICTS.jsonl"
    responsibility_rows = out_dir / "CYCLE36_RESPONSIBILITY_ASSERTIONS.jsonl"
    verifications = {
        "scheme_assertions": write_jsonl_verified(scheme_rows, schemes["assertions"]),
        "scheme_conflicts": write_jsonl_verified(conflict_rows, schemes["conflicts"]),
        "responsibility_assertions": write_jsonl_verified(
            responsibility_rows, responsibility["statements"]
        ),
    }

    summary = {
        "artifact_type": "CYCLE36_SCHEME_AND_RESPONSIBILITY",
        "generated_at_utc": utc_now(),
        "scheme_claims_examined": schemes["scheme_claims_examined"],
        "scheme_states": schemes["states"],
        "scheme_rows_admitted": schemes["states"].get(ADMITTED, 0),
        "scheme_admitted_cells": schemes["admitted_cells"],
        "scheme_family_counts": schemes["family_counts"],
        "cells_with_more_than_one_stated_family": schemes[
            "cells_with_more_than_one_stated_family"
        ],
        "coexisting_examples": schemes["coexisting_examples"],
        "scheme_conflicts_retained": schemes["conflict_count"],
        "crosswalk_conflicts": conflict_report(crosswalk)["colliding_alias_count"],
        "responsibility": {
            key: value
            for key, value in responsibility.items()
            if key != "statements"
        },
        "lossless_trace": (
            "Every one of the examined claims is written to "
            "CYCLE36_SCHEME_ASSERTIONS.jsonl with its raw source_text, its "
            "page title, its Wikimedia revision and its resolution state, "
            "whether or not it was admitted. Nothing is dropped."
        ),
        "not_a_success_predicate": (
            "An empty responsibility table is not evidence delivery. The "
            "admitted count here is the number of explicit source statements "
            "found in the processed titles, and the rejected candidates are "
            "written out beside them."
        ),
        "model_consumption_separately_gated": (
            "Candidate scheme assertions are descriptive source evidence. They "
            "are not admitted to any model input by this tool."
        ),
        "post_write_verification": verifications,
        "written": {
            "scheme_assertions": str(scheme_rows),
            "scheme_conflicts": str(conflict_rows),
            "responsibility_assertions": str(responsibility_rows),
        },
    }
    _bas_atomic.write_text(out_dir / "CYCLE36_SCHEME_AND_RESPONSIBILITY.json", 
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--observation-rows", type=Path, default=None)
    args = parser.parse_args()
    summary = build(args.out_dir, args.observation_rows)
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "scheme_claims_examined",
                    "scheme_states",
                    "scheme_admitted_cells",
                    "cells_with_more_than_one_stated_family",
                    "scheme_conflicts_retained",
                    "responsibility",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
