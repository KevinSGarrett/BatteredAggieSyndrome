"""R35-24 (Cycle #35 closeout review, 20260921T025300Z), section 7.

"Complete the originally required source-span/semantic review with independent
labels and positive/negative controls. Author-side secondary checks do not
confer manager scientific acceptance. If a clause explicitly requires an
independent owner/reviewer decision, prepare its complete evidence queue
instead of relabeling every unfinished local task as external review."

The review splits in two, and the split is the point.

The SPAN question -- does this person's name and this exact title text
actually occur in the raw bytes the claim cites -- is mechanical, so it is
answered here and answered independently. The label comes from
`span_locate.locate_string`, a plain substring locator over the raw HTML with
its unescape and <br> coordinate maps. It is NOT the role-admission parser
(`bind_person_role` / `iter_staff_records`) that produced the claim under
review, so the claim is not grading itself.

The SEMANTIC question -- given that the span is there, is this the role this
person actually held for this program -- is not mechanical. It stays
PENDING_INDEPENDENT_ADJUDICATION, and what this tool produces for it is a
complete evidence queue: raw path and digest, byte interval, the surrounding
context a reviewer needs, the parser's claim and the independent span verdict,
so the decision can be made without re-deriving anything.

Every run carries positive and negative controls. A positive control is a
string lifted verbatim out of the raw file, so a working locator must find it.
A negative control is a string built to be absent. If any control comes back
the wrong way the instrument is broken and the run is marked INVALID, because
span verdicts from a locator that cannot tell present from absent are worth
nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33.span_locate import locate_string  # noqa: E402

CYCLE_RUNS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
REVIEW_SAMPLE = (
    CYCLE_RUNS
    / "20260920T172801Z"
    / "implementation_output"
    / "R35_02_STRATIFIED_REVIEW_SAMPLE.json"
)

SPAN_PRESENT = "SPAN_PRESENT_IN_RAW_SOURCE"
SPAN_ABSENT = "SPAN_ABSENT_FROM_RAW_SOURCE"
SPAN_UNCHECKABLE = "RAW_SOURCE_UNREADABLE"

SEMANTIC_PENDING = "PENDING_INDEPENDENT_ADJUDICATION"

#: How an independent span label can differ from the parser's own support
#: flag. These are not the same defect and must not be summed into one
#: "disagreement" count: the first is a recall gap in the reparse, the last
#: is a claim resting on evidence that is not there.
DISAGREE_NO_RECORD = "PARSER_FOUND_NO_RECORD_BUT_BOTH_SPANS_PRESENT"
DISAGREE_OTHER_TITLE = "PARSER_FOUND_A_DIFFERENT_TITLE_FOR_THIS_PERSON"
DISAGREE_UNSUPPORTED_CLAIM = "PARSER_CLAIMED_SUPPORT_BUT_A_SPAN_IS_ABSENT"

CONTEXT_CHARS = 240

#: A negative control has to be absent for a reason that would not also make a
#: real title absent. Reversing the token order keeps every character and every
#: word of a real title while making the string itself one the page does not
#: contain, so a locator that "finds" it is matching loosely rather than
#: matching the span it claims.
def negative_control_text(title: str) -> str:
    tokens = [token for token in re.split(r"(\s+)", title) if token.strip()]
    if len(tokens) < 2:
        return f"{title} \u00a7NOT-IN-SOURCE\u00a7"
    return " ".join(reversed(tokens))


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def read_html(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def context_around(html: str, start: int, end: int) -> str:
    low = max(0, start - CONTEXT_CHARS)
    high = min(len(html), end + CONTEXT_CHARS)
    return html[low:high]


def span_verdict(html: str | None, needle: str) -> dict[str, Any]:
    """The independent label. Nothing here consults the parser's opinion."""

    if html is None:
        return {"label": SPAN_UNCHECKABLE, "needle": needle}
    located = locate_string(html, needle)
    if located is None:
        return {"label": SPAN_ABSENT, "needle": needle}
    # locate_string reports the interval as body_offset/body_end_offset. A
    # span verdict with no interval is not a located span, so a missing offset
    # raises instead of defaulting to -1 and handing a reviewer an empty
    # evidence queue that still reads as SPAN_PRESENT.
    start = located.get("body_offset")
    end = located.get("body_end_offset")
    if start is None or end is None:
        raise ValueError(f"locate_string returned no interval for {needle!r}")
    start, end = int(start), int(end)
    return {
        "label": SPAN_PRESENT,
        "needle": needle,
        "raw_start": start,
        "raw_end": end,
        "evidence_text": located.get("evidence_text"),
        "matched_variant": located.get("variant"),
        "coordinate_system": located.get("coordinate_system"),
        "transformations": located.get("transformations", []),
        "context": context_around(html, start, end),
    }


def run_controls(html: str | None, title: str, raw_path: str) -> list[dict[str, Any]]:
    """Positive and negative controls for one raw document."""

    controls: list[dict[str, Any]] = []
    if html is None:
        return [
            {
                "control": "POSITIVE_VERBATIM_SUBSTRING",
                "expected": SPAN_PRESENT,
                "observed": SPAN_UNCHECKABLE,
                "passed": False,
                "raw_path": raw_path,
            }
        ]

    # Positive: a slice lifted out of the middle of the document itself. A
    # locator that cannot find this cannot find anything.
    midpoint = len(html) // 2
    verbatim = html[midpoint : midpoint + 60].strip()
    if verbatim:
        observed = span_verdict(html, verbatim)["label"]
        controls.append(
            {
                "control": "POSITIVE_VERBATIM_SUBSTRING",
                "expected": SPAN_PRESENT,
                "observed": observed,
                "passed": observed == SPAN_PRESENT,
                "raw_path": raw_path,
            }
        )

    # Negative: a string assembled from the real title's own words in an order
    # the page does not contain.
    scrambled = negative_control_text(title)
    if scrambled and scrambled != title:
        observed = span_verdict(html, scrambled)["label"]
        controls.append(
            {
                "control": "NEGATIVE_TOKEN_ORDER_SCRAMBLE",
                "expected": SPAN_ABSENT,
                "observed": observed,
                "passed": observed == SPAN_ABSENT,
                "raw_path": raw_path,
                "needle": scrambled,
            }
        )

    # Negative: a name nobody on any staff page carries.
    sentinel = "Zzyzx Qvortrup-Nonexistent"
    observed = span_verdict(html, sentinel)["label"]
    controls.append(
        {
            "control": "NEGATIVE_ABSENT_SENTINEL_NAME",
            "expected": SPAN_ABSENT,
            "observed": observed,
            "passed": observed == SPAN_ABSENT,
            "raw_path": raw_path,
            "needle": sentinel,
        }
    )
    return controls


def disagreement_kind(
    row: dict[str, Any], both_present: bool, supported: Any
) -> str | None:
    """Name the direction of a disagreement, or None when there is none."""

    if supported is None or bool(supported) == both_present:
        return None
    if supported:
        return DISAGREE_UNSUPPORTED_CLAIM
    if row.get("rebuilt_record_person") is None and row.get("rebuilt_record_title") is None:
        return DISAGREE_NO_RECORD
    return DISAGREE_OTHER_TITLE


def review_row(row: dict[str, Any]) -> dict[str, Any]:
    raw_path = Path(str(row.get("raw_path") or ""))
    html = read_html(raw_path) if raw_path.is_file() else None
    person = str(row.get("person") or "")
    title = str(row.get("source_title") or "")

    person_span = span_verdict(html, person)
    title_span = span_verdict(html, title)

    both_present = (
        person_span["label"] == SPAN_PRESENT and title_span["label"] == SPAN_PRESENT
    )
    return {
        "episode_key": row.get("episode_key"),
        "program_id": row.get("program_id"),
        "person": person,
        "source_title": title,
        "stratum": row.get("stratum"),
        "raw_source": {
            "path": str(raw_path),
            "sha256": sha256_file(raw_path),
            "bytes": raw_path.stat().st_size if raw_path.is_file() else None,
        },
        "independent_span_label": {
            "person": person_span,
            "title": title_span,
            "both_present": both_present,
            "label_authority": (
                "aggie_analytics.cycle33.span_locate.locate_string -- a plain "
                "substring locator over the raw bytes. Not the role-admission "
                "parser whose claim is under review."
            ),
        },
        "parser_claim": {
            "recorded_role_claim_supported": row.get("recorded_role_claim_supported"),
            "rebuilt_role_claim_supported": row.get("rebuilt_role_claim_supported"),
            "rebuilt_record_person": row.get("rebuilt_record_person"),
            "rebuilt_record_title": row.get("rebuilt_record_title"),
        },
        "span_label_agrees_with_parser_support": (
            None
            if row.get("rebuilt_role_claim_supported") is None
            else bool(row.get("rebuilt_role_claim_supported")) == both_present
        ),
        "disagreement_kind": disagreement_kind(
            row, both_present, row.get("rebuilt_role_claim_supported")
        ),
        "semantic_review": {
            "label": SEMANTIC_PENDING,
            "why_not_decided_here": (
                "Whether this is the role this person actually held is a "
                "judgement about the world, not about the bytes. An author-side "
                "check cannot confer it. Everything a reviewer needs to decide "
                "is attached above."
            ),
        },
    }


def build(sample_path: Path) -> dict[str, Any]:
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    rows = payload.get("sample", [])

    reviewed = [review_row(row) for row in rows]

    controls: list[dict[str, Any]] = []
    seen_documents: set[str] = set()
    for row in rows:
        raw_path = Path(str(row.get("raw_path") or ""))
        key = str(raw_path)
        if key in seen_documents:
            continue
        seen_documents.add(key)
        controls.extend(
            run_controls(
                read_html(raw_path) if raw_path.is_file() else None,
                str(row.get("source_title") or ""),
                key,
            )
        )

    failed_controls = [control for control in controls if not control["passed"]]
    instrument_valid = not failed_controls

    span_labels = Counter(
        (
            SPAN_PRESENT
            if item["independent_span_label"]["both_present"]
            else item["independent_span_label"]["person"]["label"]
        )
        for item in reviewed
    )
    agreement = Counter(
        str(item["span_label_agrees_with_parser_support"]) for item in reviewed
    )
    disagreements = [
        {
            "episode_key": item["episode_key"],
            "person": item["person"],
            "source_title": item["source_title"],
            "kind": item["disagreement_kind"],
            "disposition": (item.get("stratum") or {}).get("disposition"),
            "parser_said_supported": item["parser_claim"]["rebuilt_role_claim_supported"],
            "independent_span_both_present": item["independent_span_label"][
                "both_present"
            ],
            "raw_path": item["raw_source"]["path"],
        }
        for item in reviewed
        if item["span_label_agrees_with_parser_support"] is False
    ]
    by_kind = Counter(item["kind"] for item in disagreements)

    return {
        "artifact_type": "CYCLE35_SOURCE_SPAN_SEMANTIC_REVIEW",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_artifact": str(sample_path),
        "sample_sha256": sha256_file(sample_path),
        "rows_reviewed": len(reviewed),
        "instrument": {
            "valid": instrument_valid,
            "status": "CONTROLS_PASSED" if instrument_valid else "INVALID_CONTROLS_FAILED",
            "documents_controlled": len(seen_documents),
            "control_count": len(controls),
            "failed_controls": failed_controls,
            "why_controls": (
                "A span verdict from a locator that cannot separate a present "
                "string from an absent one carries no information. Positive and "
                "negative controls are run on every distinct raw document in the "
                "sample, and a single failure invalidates the run rather than "
                "being averaged away."
            ),
        },
        "independent_span_labels": dict(span_labels),
        "span_label_vs_parser_support": dict(agreement),
        "disagreements": disagreements,
        "disagreements_by_kind": dict(by_kind),
        "no_claim_rests_on_an_absent_span": by_kind.get(DISAGREE_UNSUPPORTED_CLAIM, 0) == 0,
        "disagreement_reading": (
            "A row in "
            + DISAGREE_NO_RECORD
            + " is a reparse recall gap: the person's name and the exact title "
            "text are both in the raw bytes, and the reparse returned no record "
            "at all. That is not evidence the source fails to support the claim, "
            "so the quarantine disposition should not be read as one. Nothing is "
            "re-promoted here on the strength of this -- the direction of the "
            "gap is reported and the decision is left to the reviewer."
        ),
        "semantic_review_queue": {
            "pending": sum(
                1 for item in reviewed if item["semantic_review"]["label"] == SEMANTIC_PENDING
            ),
            "decided_here": 0,
            "requires": "INDEPENDENT_REVIEWER",
            "queue_is_complete": all(
                item["raw_source"]["sha256"] is not None for item in reviewed
            ),
            "author_side_checks_do_not_confer_acceptance": True,
        },
        "rows": reviewed,
        "controls": controls,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent source-span review.")
    parser.add_argument("--sample", type=Path, default=REVIEW_SAMPLE)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.sample.is_file():
        print(f"no review sample at {args.sample}", file=sys.stderr)
        return 2

    result = build(args.sample)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / "CYCLE35_SOURCE_SPAN_SEMANTIC_REVIEW.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "rows_reviewed": result["rows_reviewed"],
                "instrument": result["instrument"]["status"],
                "control_count": result["instrument"]["control_count"],
                "independent_span_labels": result["independent_span_labels"],
                "span_label_vs_parser_support": result["span_label_vs_parser_support"],
                "disagreements": len(result["disagreements"]),
                "disagreements_by_kind": result["disagreements_by_kind"],
                "semantic_pending": result["semantic_review_queue"]["pending"],
                "artifact": str(out_path),
            },
            indent=2,
        )
    )
    # A broken instrument is a failure, not a footnote.
    return 0 if result["instrument"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
