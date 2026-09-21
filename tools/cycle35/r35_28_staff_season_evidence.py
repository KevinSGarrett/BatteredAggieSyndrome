"""R35-28 (Cycle #35 continuation, 20260921T055921Z), section 3.

"For each confirmed current staff episode, inspect the source's staff-season
label, dated announcement, media guide, or other actual season/effective-time
evidence. Bind the season only when supported. Keep genuinely unspecified
episodes unspecified... Do not simply assign all `CURRENT` episodes to 2026."

Every one of the 1,398 confirmed role assertions hangs off an employment
episode whose season reads `CURRENT` at SEASON_UNSPECIFIED precision, so none
can be placed in a program-season-role cell.

The tempting repair is to date them 2026, since the captures were retrieved
in September 2026. That is the forbidden one. A retrieval timestamp records
WHEN A PAGE WAS READ, not WHICH SEASON ITS STAFF LIST DESCRIBES -- the whole
acquisition ran inside a thirteen-minute window on 2026-09-09, and the
`/staff` route carries no year parameter at all, so retrieval time cannot
distinguish a page showing the 2026 staff from one left stale at 2024.

What can settle it is the page's own text. This module extracts season
evidence and binds ONLY on unanimity:

* every staff-season label on the page must agree on one year;
* a page whose labels disagree is AMBIGUOUS and binds nothing, because
  choosing between them would be the guess this exists to avoid;
* a page with no label at all stays unspecified, which is the honest state
  for a staff directory that never says which season it is for.

Roster labels and media-guide years are collected as corroboration and
reported, but they never override or substitute for a staff-season label: a
page can carry a 2026 roster beside a staff list it never dates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CYCLE30 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
REBUILD_ROWS = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
    / "20260920T172801Z"
    / "implementation_output"
    / "R35_02_STAFF_REBUILD_ROWS.jsonl"
)

#: Only years a college football staff page could plausibly label itself
#: with. A four-digit number elsewhere in the markup (a phone number, an
#: asset hash, a copyright year) is not a staff-season label.
SEASON_RANGE = (2000, 2030)

#: Sports that share these sites. A capture is a FOOTBALL staff directory,
#: so "2025 Women's Basketball Staff" says nothing about the football staff
#: season -- it is a sibling section on the same page.
OTHER_SPORTS = (
    r"basketball|baseball|softball|volleyball|soccer|hockey|lacrosse|"
    r"tennis|golf|swimming|diving|track|cross\s*country|wrestling|rowing|"
    r"gymnastics|water\s*polo|field\s*hockey|bowling|rifle|equestrian"
)

#: Only explicit season labels, never prose. The first pattern allowed up to
#: three arbitrary words between the year and "staff", which matched
#: "2019 on staff" inside a biography, "2022 University of Miami staff"
#: inside a sentence, and "2025 Women's Basketball Staff" from another
#: sport's section -- three captures bound to the wrong season until they
#: were checked by hand. A label now has to name football, coaching, or a
#: staff directory outright.
STAFF_LABEL = re.compile(
    r"\b(20[0-3]\d)\s+(?:football\s+coaching\s+staff"
    r"|football\s+staff\s+directory"
    r"|football\s+staff"
    r"|coaching\s+staff"
    r"|staff\s+directory)\b",
    re.I,
)
_OTHER_SPORT_LABEL = re.compile(
    r"\b20[0-3]\d\s+(?:[A-Za-z&.'’-]+\s+){0,3}?(?:" + OTHER_SPORTS + r")\b",
    re.I,
)
ROSTER_LABEL = re.compile(r"\b(20[0-3]\d)\s+football\s+roster\b", re.I)
MEDIA_GUIDE = re.compile(r"\b(20[0-3]\d)\s+(?:football\s+)?media\s+guide\b", re.I)

BOUND = "SEASON_BOUND_BY_UNANIMOUS_STAFF_LABEL"
AMBIGUOUS = "AMBIGUOUS_STAFF_LABELS_DISAGREE"
NO_EVIDENCE = "NO_SEASON_EVIDENCE_IN_THE_CAPTURE"
UNREADABLE = "CAPTURE_UNREADABLE"


def in_range(year: str) -> bool:
    low, high = SEASON_RANGE
    return low <= int(year) <= high


def names_another_sport(text: str, start: int, end: int) -> bool:
    """Whether a match sits inside another sport's heading.

    These sites host every sport, so a football staff capture also carries
    "2025 Women's Basketball Coaching Staff". That phrase matches the
    coaching-staff form and says nothing about the football staff season.
    """

    window = text[max(0, start - 60) : end + 20]
    return bool(_OTHER_SPORT_LABEL.search(window))


def find_labels(text: str, pattern: re.Pattern[str], kind: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        year = match.group(1)
        if not in_range(year):
            continue
        if kind == "STAFF_SEASON_LABEL" and names_another_sport(
            text, match.start(), match.end()
        ):
            continue
        out.append(
            {
                "kind": kind,
                "season": int(year),
                "matched_text": match.group(0).strip()[:120],
                "offset": match.start(),
            }
        )
    return out


def season_evidence(path: Path) -> dict[str, Any]:
    """Locatable season evidence for one capture, or an honest absence."""

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return {
            "capture": str(path),
            "state": UNREADABLE,
            "detail": str(error),
            "bound_season": None,
        }

    staff = find_labels(text, STAFF_LABEL, "STAFF_SEASON_LABEL")
    roster = find_labels(text, ROSTER_LABEL, "ROSTER_SEASON_LABEL")
    guide = find_labels(text, MEDIA_GUIDE, "MEDIA_GUIDE_YEAR")

    staff_years = sorted({item["season"] for item in staff})
    record: dict[str, Any] = {
        "capture": str(path),
        "capture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "staff_label_matches": staff[:12],
        "staff_label_match_count": len(staff),
        "staff_label_years": staff_years,
        "corroboration": {
            "roster_label_years": sorted({item["season"] for item in roster}),
            "media_guide_years": sorted({item["season"] for item in guide}),
        },
    }

    if not staff:
        record.update(
            state=NO_EVIDENCE,
            bound_season=None,
            detail="The capture carries no staff-season label. A staff "
            "directory that never states its season leaves the episode "
            "unspecified; the retrieval time cannot supply one.",
        )
        return record

    if len(staff_years) > 1:
        # Describe the disagreement without settling it. A reviewer can see
        # that one year appears repeatedly and early while another appears
        # once and late -- the shape of a heading beside a biography -- but
        # deciding a season from layout would be a guess about the page, not
        # evidence from it.
        by_year: dict[int, list[int]] = {}
        for item in staff:
            by_year.setdefault(item["season"], []).append(item["offset"])
        record.update(
            state=AMBIGUOUS,
            bound_season=None,
            disagreement_shape={
                str(year): {
                    "matches": len(offsets),
                    "first_offset": min(offsets),
                    "last_offset": max(offsets),
                }
                for year, offsets in sorted(by_year.items())
            },
            detail=f"Staff-season labels disagree ({staff_years}). Choosing "
            "between them would be a guess, so nothing is bound. The match "
            "counts and offsets per year are recorded so a reviewer can see "
            "the shape of the disagreement.",
        )
        return record

    record.update(
        state=BOUND,
        bound_season=staff_years[0],
        detail=f"Every staff-season label on the page reads {staff_years[0]}, "
        f"across {len(staff)} match(es). The season comes from the page's own "
        "text, not from when it was retrieved.",
    )
    return record


def build(rebuild_rows: Path = REBUILD_ROWS) -> dict[str, Any]:
    if not rebuild_rows.is_file():
        return {
            "artifact_type": "CYCLE35_STAFF_SEASON_EVIDENCE",
            "state": "REBUILD_ROWS_ABSENT",
            "rebuild_rows": str(rebuild_rows),
        }

    rows = [
        json.loads(line)
        for line in rebuild_rows.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    captures: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        raw = str(row.get("raw_path") or "")
        if raw:
            captures.setdefault(raw, []).append(row)

    evidence = {}
    for raw in sorted(captures):
        evidence[raw] = season_evidence(Path(raw))

    states = Counter(item["state"] for item in evidence.values())
    bound_years = Counter(
        item["bound_season"] for item in evidence.values() if item["bound_season"]
    )

    rows_by_state: Counter[str] = Counter()
    for raw, group in captures.items():
        rows_by_state[evidence[raw]["state"]] += len(group)

    return {
        "artifact_type": "CYCLE35_STAFF_SEASON_EVIDENCE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rebuild_rows": str(rebuild_rows),
        "rebuild_row_count": len(rows),
        "distinct_captures": len(captures),
        "captures_by_state": dict(states),
        "rebuild_rows_by_capture_state": dict(rows_by_state),
        "bound_seasons": {str(k): v for k, v in sorted(bound_years.items())},
        "evidence": evidence,
        "retrieval_time_is_not_season_evidence": (
            "The /staff route carries no year parameter and the whole "
            "acquisition ran inside a thirteen-minute window on 2026-09-09. "
            "Retrieval time records when a page was read, not which season its "
            "staff list describes, so it is never used to bind a season."
        ),
        "unanimity_is_required": (
            "A capture binds a season only when every staff-season label on it "
            "agrees. Disagreement is reported as ambiguous rather than "
            "resolved, and roster or media-guide years never substitute for a "
            "staff label."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Staff season evidence.")
    parser.add_argument("--rebuild-rows", type=Path, default=REBUILD_ROWS)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    result = build(args.rebuild_rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / "CYCLE35_STAFF_SEASON_EVIDENCE.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "distinct_captures": result.get("distinct_captures"),
                "captures_by_state": result.get("captures_by_state"),
                "rebuild_rows_by_capture_state": result.get(
                    "rebuild_rows_by_capture_state"
                ),
                "bound_seasons": result.get("bound_seasons"),
                "artifact": str(out_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
