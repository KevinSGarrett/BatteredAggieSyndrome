r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-06-AC09: compare the responsibility successor's dispositions with blind
labels on a stratified sample of real mentions across sources and eras.

Imports nothing from ``aggie_analytics``. It reads the labels and the
successor rows by key and reports three things, because they answer
different questions:

* **safety** -- did any mention become a current responsibility that the
  label says is not one (or the reverse)? AC03 requires zero.
* **admission** -- among college statements that a named person held the
  job (historical, about the page subject or another person), how many did
  the rules admit as candidates, and how many admitted rows are not such a
  statement?
* **exact agreement** -- the fine label, with every disagreement listed
  beside its sentence, so a reader can see which rule missed and why.

A disagreement is reported, not hidden, and none is resolved by editing a
label after the comparison.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
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
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")

#: Producer disposition -> label vocabulary. Declared, so an unknown
#: disposition fails rather than being counted as a disagreement.
MAP = {
    "ADMITTED_CURRENT_OFFICIAL_TITLE_STATEMENT": "CURRENT",
    "CANDIDATE_HISTORICAL_EXPLICIT_STATEMENT": "HIST_SUBJECT",
    "CANDIDATE_STATEMENT_ABOUT_ANOTHER_PERSON": "HIST_OTHER",
    "CANDIDATE_FUTURE_OR_ANNOUNCED_NOT_REALIZED": "FUTURE",
    "REJECTED_NEGATED": "NEGATED",
    "REJECTED_RELINQUISHED_OR_REMOVED": "RELINQUISHED",
    "REJECTED_HYPOTHETICAL": "HYPOTHETICAL",
    "REJECTED_EVALUATIVE_MENTION_NOT_AN_ASSIGNMENT": "EVALUATIVE",
    "REJECTED_NOT_A_RESPONSIBILITY_SENSE": "OTHER_SENSE",
    "REJECTED_NON_COLLEGE_CONTEXT": "NON_COLLEGE",
    "REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT": "TITLE_NOT",
    "RETAINED_UNNAMED_PERSON": "UNNAMED",
    "RETAINED_UNATTRIBUTABLE_NO_PROGRAM_BINDING": "UNATTRIBUTABLE",
    "RETAINED_MENTION_WITHOUT_ASSIGNMENT_VERB": "MENTION_ONLY",
    "RETAINED_TEXT_COPY_OF_A_TITLE_STATEMENT": "TEXT_COPY",
}
ADMITTED_STATEMENT = {"HIST_SUBJECT", "HIST_OTHER"}


def compare(gold_path: Path, rows_path: Path) -> dict[str, Any]:
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    labels = {g["successor_key"]: g for g in gold["labels"]}
    produced: dict[str, dict[str, Any]] = {}
    with rows_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["successor_key"] in labels:
                produced[row["successor_key"]] = row
    missing = sorted(set(labels) - set(produced))
    unknown = sorted({r["disposition"] for r in produced.values()} - set(MAP))
    if unknown:
        raise SystemExit(f"dispositions with no declared label: {unknown}")

    exact, safety, confusion = 0, [], collections.Counter()
    admission = collections.Counter()
    disagreements = []
    by_basis = collections.defaultdict(lambda: [0, 0])
    for key, gold_row in labels.items():
        if key not in produced:
            continue
        predicted = MAP[produced[key]["disposition"]]
        truth = gold_row["label"]
        confusion[(truth, predicted)] += 1
        by_basis[gold_row["basis"]][1] += 1
        if predicted == truth:
            exact += 1
            by_basis[gold_row["basis"]][0] += 1
        else:
            disagreements.append({"successor_key": key, "label": truth, "predicted": predicted,
                                  "confidence": gold_row["confidence"], "basis": gold_row["basis"],
                                  "rationale": gold_row["rationale"], "page_title": gold_row.get("page_title"),
                                  "text": gold_row.get("text"), "reasons": produced[key].get("reasons")})
        if (predicted == "CURRENT") != (truth == "CURRENT"):
            safety.append(key)
        admission[("label_statement" if truth in ADMITTED_STATEMENT else "label_other",
                   "admitted" if predicted in ADMITTED_STATEMENT else "not_admitted")] += 1
    compared = sum(confusion.values())
    tp = admission[("label_statement", "admitted")]
    fp = admission[("label_other", "admitted")]
    fn = admission[("label_statement", "not_admitted")]
    return {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-06-AC09",
        "independence": "Imports no aggie_analytics module; compares stored labels with stored rows by key.",
        "labels": {"path": str(gold_path), "sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
                   "count": len(labels), "labeller": gold.get("labeller"),
                   "independence_limit": gold.get("independence_limit")},
        "rows": {"path": str(rows_path), "sha256": hashlib.sha256(rows_path.read_bytes()).hexdigest()},
        "compared": compared, "missing_from_rows": missing,
        "safety_current_responsibility_mismatches": safety,
        "admission": {"statements_admitted": tp, "non_statements_admitted": fp, "statements_missed": fn,
                      "precision": round(tp / (tp + fp), 4) if tp + fp else None,
                      "recall": round(tp / (tp + fn), 4) if tp + fn else None},
        "exact_agreement": {"agree": exact, "of": compared, "rate": round(exact / compared, 4) if compared else None,
                            "by_label_basis": {k: {"agree": v[0], "of": v[1]} for k, v in by_basis.items()}},
        "confusion": {f"{t} -> {p}": n for (t, p), n in sorted(confusion.items())},
        "disagreements": disagreements,
        "schools_and_eras": {"pages": len({g.get("page_title") for g in labels.values()})},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gold", type=Path, default=ATTEMPT / "evidence/repairs/R37_06_CONTEXT_GOLD.json")
    parser.add_argument("--rows", type=Path, default=ATTEMPT / "evidence/repairs/R37_06_RESPONSIBILITY_ROWS.jsonl")
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence/repairs/R37_06_CONTEXT_CHECK.json")
    args = parser.parse_args(argv)
    receipt = compare(args.gold, args.rows)
    _bas_atomic.write_text(args.out, json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("compared:", receipt["compared"], "| missing:", len(receipt["missing_from_rows"]),
          "| safety mismatches:", receipt["safety_current_responsibility_mismatches"])
    print("admission:", receipt["admission"])
    print("exact:", receipt["exact_agreement"])
    for d in receipt["disagreements"]:
        print(f"  {d['label']:>14} <- {d['predicted']:<14} [{d['basis'][:5]}] {str(d['text'])[:110]}")
    return 1 if receipt["safety_current_responsibility_mismatches"] or receipt["missing_from_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
