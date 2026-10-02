"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-15: the three-pass evidence for the three named units, with an
independence graph computed from the code that produced each pass.

Units: Cycle 30 membership/population, Cycle 33 staff admission (as
reparsed), Cycle 35 release/coverage (as corrected). For each unit:

* pass 1 traces claims and inputs to identified bytes;
* pass 2 reconstructs from raw with different logic;
* pass 3 attacks the invariants with deliberate counterexamples.

Independence is read from the producing tool's own imports (an AST scan):
a pass-2 tool that imports ``aggie_analytics`` is producer-dependent and
cannot count as an independent reconstruction; pass 3 is expected to drive
the producer (it attacks it). Every false-positive adjudication, changed
count and descendant made in this attempt is listed. The all-cycle 1-36
ledger stays explicit: a cycle this attempt did not review is
BLOCKED_NOT_REVIEWED, never passed by these three units. Nothing here awards
scientific acceptance; that is the manager's.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ROOT = Path(__file__).resolve().parents[2]
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
R = ATTEMPT / "evidence" / "repairs"
C36_MATRIX = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle36/runs/20260921T200027Z/implementation_output"
                  r"/CYCLE36_HISTORICAL_AUDIT_MATRIX.json")

UNITS = {
    "CYCLE30_MEMBERSHIP_POPULATION": {
        "pass1": [("tools/cycle37/r37_04_population_audit.py", R / "R37_04_POPULATION_AUDIT.json")],
        "pass2": [("tools/cycle37/r37_04_population_audit.py", R / "R37_04_POPULATION_AUDIT.json"),
                  ("tools/cycle37/r37_10_finals_reconstruction.py", R / "R37_10_FINALS_RECONSTRUCTION.json")],
        "pass3": [("tools/cycle37/mf36_05_membership_probe.py", R / "MF36_05_MEMBERSHIP_PROBE_AFTER.json")],
    },
    "CYCLE33_STAFF_ADMISSION": {
        "pass1": [("tools/cycle37/r37_03_staff_reparse.py", R / "R37_03_STAFF_REPARSE.json"),
                  ("tools/cycle37/r37_03_r35_02_reconciliation.py", R / "R37_03_R35_02_RECONCILIATION.json")],
        "pass2": [("tools/cycle37/r37_03_season_support_check.py", R / "R37_03_SEASON_SUPPORT_CHECK.json"),
                  ("tools/cycle37/r37_03_labelled_sample.py", R / "R37_03_HELDOUT_COMPARISON_V37_1_FROZEN_RULES.json"),
                  ("tools/cycle37/r37_03_historical_sample.py", R / "R37_03_HISTORICAL_COMPARISON_V37_1.json")],
        "pass3": [("tools/cycle37/r37_03_season_probes.py", R / "R37_03_SEASON_PROBES.json"),
                  ("tools/cycle37/mf36_admission_probe.py", R / "MF36_ADMISSION_PROBE_AFTER.json")],
    },
    "CYCLE35_RELEASE_COVERAGE": {
        "pass1": [("tools/cycle37/build_corrected_release.py", R / "R37_07_CORRECTED_RELEASE_V37_3.json"),
                  ("tools/cycle37/r37_03_release_diff.py", R / "R37_03_RELEASE_DIFF.json")],
        "pass2": [("tools/cycle37/delivered_db_review.py", ATTEMPT / "evidence" / "lanes" / "DELIVERED_DB_REVIEW.json")],
        "pass3": [("tests/test_cycle37_corrected_release.py", ATTEMPT / "evidence" / "lanes" / "focused.json")],
    },
}
ADJUDICATIONS = [
    {"id": "FP-01", "unit": "CYCLE33_STAFF_ADMISSION", "evidence": "R37_03_SEASON_SUPPORT_CHECK.json",
     "verdict": "RULE_DIFFERENCE_NOT_A_DEFECT",
     "detail": "339 unadmitted rows are dated by a '2026 Football Roster' heading, which the producer accepts and the "
               "independent checker's stricter staff-phrase rule does not; no admitted row fails."},
    {"id": "FP-02", "unit": "CYCLE33_STAFF_ADMISSION", "evidence": "R37_03_SEASON_SUPPORT_CHECK.json",
     "verdict": "CHECKER_FALSE_POSITIVE_FIXED",
     "detail": "The checker's first version read a person heading ('Josh Bowling') as a bowling section (16 rows); "
               "it now requires the sport to be the heading's subject."},
    {"id": "FP-03", "unit": "CYCLE33_STAFF_ADMISSION", "evidence": "R37_03_HELDOUT_ADJUDICATION.json",
     "verdict": "LABELLER_ERRORS", "detail": "Three held-out disagreements were the labeller reading title-first tables "
                                              "as name-first; the raw rows support the parser."},
    {"id": "FP-04", "unit": "CYCLE33_STAFF_ADMISSION", "evidence": "R37_03_R35_02_RECONCILIATION.json",
     "verdict": "PREDECESSOR_WRONG_SPORT", "detail": "The one R35-02 reference not found is a 'Defensive "
                                                      "Coordinator/Infield Coach' (baseball) R35 admitted as football."},
    {"id": "FP-05", "unit": "CYCLE30_MEMBERSHIP_POPULATION", "evidence": "R37_04_POPULATION_AUDIT.json",
     "verdict": "SOURCE_DISAGREEMENT_PUBLISHED", "detail": "Alcorn State is absent from the 2020 membership statement "
                                                          "while the results route records six spring-2021 games; kept "
                                                          "as a published disagreement, not resolved by assumption."},
]
DEFECTS_FOUND_BY_THE_PASSES = [
    ("W37R-38", "tuning blind sample", "nine season heading forms"),
    ("W37R-39", "held-out blind sample", "sprint-football table read as football"),
    ("W37R-40", "historical raw cases", "other sports' programmes as football careers"),
    ("W37R-41", "historical raw cases", "unstated list roles defaulted to head coach"),
    ("W37R-48", "independent season-support check", "titles zipped one row out of step"),
    ("W37R-49", "R35-02 reference reconciliation", "cross-segment qualifier unmade a head coach; executive director "
                                                   "read as head coach"),
]


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=R / "R37_15_THREE_PASS_LEDGER.json")
    args = parser.parse_args(argv)
    units, graph = {}, []
    for unit, passes in UNITS.items():
        units[unit] = {}
        for name, items in passes.items():
            rows = []
            for tool, evidence in items:
                tool_path = ROOT / tool
                imported = imports(tool_path)
                producer = [m for m in imported if m.startswith("aggie_analytics")]
                independent = not producer
                rows.append({"tool": tool, "tool_sha256": sha256_file(tool_path), "evidence": str(evidence),
                             "evidence_sha256": sha256_file(evidence), "evidence_exists": evidence.is_file(),
                             "producer_imports": producer, "independent_of_producer_code": independent})
                graph.append({"unit": unit, "pass": name, "tool": tool, "depends_on": producer or ["standard library"]})
            ok = all(r["evidence_exists"] for r in rows) and (
                name != "pass2" or any(r["independent_of_producer_code"] for r in rows))
            units[unit][name] = {"items": rows, "state": "PRESENT" if ok else "MISSING_OR_NOT_INDEPENDENT"}
    matrix = json.loads(C36_MATRIX.read_text(encoding="utf-8"))
    ledger = []
    for cycle in range(1, 37):
        reviewed = cycle in (30, 33, 35)
        ledger.append({"cycle": cycle, "state": ("NAMED_UNIT_THREE_PASS_EVIDENCE_SUBMITTED_NOT_ACCEPTED" if reviewed
                                                 else "BLOCKED_NOT_REVIEWED_IN_CYCLE37"),
                       "full_cycle_audit": False})
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-15",
        "units": units, "independence_graph": graph,
        "all_pass2_have_an_independent_reconstruction": all(
            units[u]["pass2"]["state"] == "PRESENT" for u in units),
        "false_positive_adjudications": ADJUDICATIONS,
        "defects_the_passes_found": [{"finding": f, "found_by": by, "what": what}
                                     for f, by, what in DEFECTS_FOUND_BY_THE_PASSES],
        "changed_counts": {"staff": json.loads((R / "R37_03_STAFF_REPARSE.json").read_text(encoding="utf-8"))["counts"]
                           ["row_diff"],
                           "release_diff": {k: v for k, v in json.loads((R / "R37_03_RELEASE_DIFF.json").read_text(
                               encoding="utf-8")).items() if k in ("diff_rows_written", "core_cells_changed")},
                           "career_predecessor": json.loads((R / "R37_05_CAREER_REPARSE.json").read_text(
                               encoding="utf-8"))["counts"]["predecessor_disposition"]},
        "impact_closure": json.loads((R / "R37_03_RELEASE_DIFF.json").read_text(encoding="utf-8"))["descendants"],
        "all_cycle_ledger": ledger,
        "cycle36_matrix_carried": {"path": str(C36_MATRIX), "sha256": sha256_file(C36_MATRIX),
                                   "audited_in_cycle36": matrix["all_cycle_ledger"].get("audited_in_cycle36")},
        "independence_limit": ("The blind labels are written by the same worker who wrote the parsers; they are a "
                               "raw reading, not an independent person's semantic adjudication."),
        "acceptance": "NOT_AWARDED: the worker submits evidence; scientific acceptance is the manager's.",
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({u: {p: v["state"] for p, v in d.items()} for u, d in units.items()}, indent=1))
    print("independent pass2 everywhere:", report["all_pass2_have_an_independent_reconstruction"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
