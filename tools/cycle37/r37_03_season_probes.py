"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-03 AC06 / MR35R-04 / MF36-02: run every manager season probe through the
v37 staff season scope and record the verdict beside the manager's expected
one.

* MR35R-04 (Cycle #35 review): five synthetic captures on disk -- a positive
  heading and four negatives (an HTML comment, a script string, archive
  navigation and a biography sentence), each of which the Cycle #35 binder
  dated 2026.
* MF36-02 (Cycle #36 review): seven cases the v36.1 binder got wrong or was
  asked to keep right, with the expected result the finding states.

A probe without a staff record is dated at the end of the page, where a record
following its heading would sit; that is the most permissive place for a
label to govern, so a refusal there is a refusal anywhere after the label.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37 import staff_season_scope as scope
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
MR35R = Path(r"C:/BatteredAggieSyndrome.data/ops/manager_reviews/cycle35/20260921T131038Z")
MF36 = Path(r"C:/BatteredAggieSyndrome.data/ops/manager_reviews/cycle36/20260922T022500Z/ADVERSARIAL_SEMANTIC_PROBES.json")

#: The season each probe should bind, or None when it must bind nothing.
MR35R_EXPECTED = {"positive": 2026, "comment_only": None, "script_only": None, "archive_navigation": None,
                  "biography": None}
MF36_EXPECTED = {"positive": 2026, "other_person_announcement": None, "nonrole_announcement": None,
                 "adjacent_basketball_section": None, "hidden_heading": None, "historical_1999": 1999,
                 "future_appointment": 2026}


def record_offset(source: str) -> tuple[int, str | None]:
    for person in ("A Person", "Alex Reed"):
        if person in source:
            return source.find(person), person
    return max(len(source) - 1, 0), None


def probe(name: str, source: str, expected: int | None) -> dict[str, Any]:
    offset, person = record_offset(source)
    verdict = scope.season_for_record(scope.scan(source), offset, person=person)
    return {"case": name, "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "record_offset": offset, "expected_season": expected, "bound_season": verdict["bound_season"],
            "state": verdict["state"], "announcement_date": verdict.get("announcement_date"),
            "passes": verdict["bound_season"] == expected}


def run(out: Path) -> dict[str, Any]:
    mr35r = [probe(name, (MR35R / "synthetic_source_probes" / f"{name}.html").read_text(encoding="utf-8"), expected)
             for name, expected in MR35R_EXPECTED.items()]
    cases = {case["case"]: case["source"] for case in json.loads(MF36.read_text(encoding="utf-8"))["season_cases"]}
    mf36 = [probe(name, cases[name], expected) for name, expected in MF36_EXPECTED.items()]
    report = {"label": LABEL, "cycle_number": 37, "attempt_number": 2,
              "rows": ["R37-03-AC06", "R37-03-CF-MR35R-04", "R37-03-CF-MF36-02"],
              "parser_version": scope.PARSER_VERSION,
              "mr35r_04": mr35r, "mf36_02": mf36,
              "all_pass": all(item["passes"] for item in mr35r + mf36),
              "sources": {"mr35r_04": str(MR35R / "synthetic_source_probes"), "mf36_02": str(MF36),
                          "mf36_02_sha256": hashlib.sha256(MF36.read_bytes()).hexdigest()}}
    _bas_atomic.write_text(out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs" / "R37_03_SEASON_PROBES.json")
    args = parser.parse_args(argv)
    report = run(args.out)
    for item in report["mr35r_04"] + report["mf36_02"]:
        print(f"{item['case']:28} expected={item['expected_season']} bound={item['bound_season']} {item['state']}"
              f"{'' if item['passes'] else '  <-- FAILS'}")
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
