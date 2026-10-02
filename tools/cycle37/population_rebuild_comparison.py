r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Compare the national population rebuilt at two source trees, file by file.

MF36-05 strengthens the membership prover. A strengthened validator is only
a repair if it refuses what should be refused *and* still admits what was
genuinely earned, so this records the second half: the same builder, run
from the predecessor export and from the repaired head over the same
declared inputs, must produce the same national rows.

It reads the two output directories a caller has already built and reports
every file's digest, the row counts inside the membership file, and the
lineage record from each side so the difference between them is visible
rather than asserted. It builds nothing and writes only ``--out``.
"""

from __future__ import annotations

import argparse
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

#: Fields that legitimately differ between two runs and are reported apart
#: from a content difference. A build clock reading is not a change in the
#: national population.
VOLATILE_TOP_LEVEL = ("generated_at_utc",)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def digests(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def jsonl_rows(path: Path) -> int:
    return len(read_jsonl(path))


def membership_field_diff(
    baseline: list[dict[str, Any]], head: list[dict[str, Any]]
) -> dict[str, Any]:
    """Which fields changed, on how many rows, keyed by program-season.

    A digest difference says only that the file is not the same file. For a
    membership population the useful question is which rows changed and in
    which field, so that adding an era label to 266 rows reads as exactly
    that rather than as an unexplained rebuild.
    """

    def key(row: dict[str, Any]) -> tuple[str, Any]:
        return (str(row.get("program_id")), row.get("season"))

    left = {key(row): row for row in baseline}
    right = {key(row): row for row in head}
    changed: dict[str, int] = {}
    examples: dict[str, dict[str, Any]] = {}
    for identity in set(left) & set(right):
        a, b = left[identity], right[identity]
        for field in set(a) | set(b):
            if a.get(field) != b.get(field):
                changed[field] = changed.get(field, 0) + 1
                examples.setdefault(
                    field,
                    {
                        "program_id": identity[0],
                        "season": identity[1],
                        "baseline": a.get(field),
                        "head": b.get(field),
                    },
                )
    return {
        "keys_only_at_baseline": sorted(
            [list(k) for k in set(left) - set(right)][:50]
        ),
        "keys_only_at_head": sorted([list(k) for k in set(right) - set(left)][:50]),
        "keys_only_at_baseline_count": len(set(left) - set(right)),
        "keys_only_at_head_count": len(set(right) - set(left)),
        "changed_fields": dict(sorted(changed.items())),
        "changed_field_examples": examples,
        "rows_with_any_change": sum(
            1
            for identity in set(left) & set(right)
            if left[identity] != right[identity]
        ),
    }


def differences(left: Any, right: Any, path: str = "") -> list[dict[str, Any]]:
    """Every leaf that differs, named by its path through the document."""

    found: list[dict[str, Any]] = []
    if type(left) is not type(right):
        return [{"path": path, "kind": "TYPE", "baseline": str(type(left).__name__),
                 "head": str(type(right).__name__)}]
    if isinstance(left, dict):
        for key in sorted(set(left) | set(right)):
            where = f"{path}/{key}"
            if key not in left:
                found.append({"path": where, "kind": "ONLY_AT_HEAD",
                              "head": json.dumps(right[key], default=str)[:400]})
            elif key not in right:
                found.append({"path": where, "kind": "ONLY_AT_BASELINE",
                              "baseline": json.dumps(left[key], default=str)[:400]})
            else:
                found.extend(differences(left[key], right[key], where))
        return found
    if isinstance(left, list):
        if len(left) != len(right):
            return [{"path": path, "kind": "LENGTH", "baseline": len(left),
                     "head": len(right)}]
        for index, (a, b) in enumerate(zip(left, right)):
            found.extend(differences(a, b, f"{path}[{index}]"))
        return found
    if left != right:
        found.append({"path": path, "kind": "CHANGED",
                      "baseline": json.dumps(left, default=str)[:300],
                      "head": json.dumps(right, default=str)[:300]})
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--baseline-label", required=True)
    parser.add_argument("--head-label", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    left, right = digests(args.baseline), digests(args.head)
    names = sorted(set(left) | set(right))
    files = [
        {
            "file": name,
            "baseline_sha256": left.get(name),
            "head_sha256": right.get(name),
            "identical": left.get(name) is not None and left.get(name) == right.get(name),
        }
        for name in names
    ]

    coverage_name = "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json"
    document_diff: list[dict[str, Any]] = []
    volatile: list[dict[str, Any]] = []
    lineage = {}
    if coverage_name in left and coverage_name in right:
        a = json.loads((args.baseline / coverage_name).read_text(encoding="utf-8"))
        b = json.loads((args.head / coverage_name).read_text(encoding="utf-8"))
        for row in differences(a, b):
            target = (
                volatile
                if row["path"].lstrip("/") in VOLATILE_TOP_LEVEL
                else document_diff
            )
            target.append(row)
        lineage = {
            "baseline": [
                {"derivative": d.get("derivative"),
                 "season_authority": d.get("season_authority"),
                 "lineage": d.get("lineage")}
                for d in a.get("derivatives", [])
                if d.get("lineage")
            ],
            "head": [
                {"derivative": d.get("derivative"),
                 "season_authority": d.get("season_authority"),
                 "lineage": d.get("lineage")}
                for d in b.get("derivatives", [])
                if d.get("lineage")
            ],
        }

    membership = "CYCLE36_NATIONAL_MEMBERSHIP_ROWS.jsonl"
    baseline_rows = read_jsonl(args.baseline / membership)
    head_rows = read_jsonl(args.head / membership)
    rows = {"baseline": len(baseline_rows), "head": len(head_rows)}
    field_diff = membership_field_diff(baseline_rows, head_rows)

    # A difference confined to the lineage record is the repair. A difference
    # anywhere else would mean the strengthened prover changed the national
    # population, which it must not.
    outside_lineage = [
        row for row in document_diff if "/lineage" not in row["path"]
    ]

    receipt = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-04",
        "finding": "MF36-05",
        "baseline_tree_label": args.baseline_label,
        "head_tree_label": args.head_label,
        "baseline_out_dir": str(args.baseline),
        "head_out_dir": str(args.head),
        "files": files,
        "files_identical": sum(1 for f in files if f["identical"]),
        "files_compared": len(files),
        "membership_rows": rows,
        "membership_rows_equal": rows["baseline"] == rows["head"],
        "membership_field_differences": field_diff,
        "document_differences": document_diff,
        "differences_outside_the_lineage_record": outside_lineage,
        "volatile_differences": volatile,
        "lineage_records": lineage,
        "national_population_unchanged": (
            rows["baseline"] == rows["head"]
            and not outside_lineage
            and not field_diff["changed_fields"]
            and not field_diff["keys_only_at_baseline_count"]
            and not field_diff["keys_only_at_head_count"]
        ),
        "not_established": (
            "Producing the same rows is not evidence that the rows are correct. "
            "It is evidence that strengthening the prover did not silently move "
            "the national population, which is the only claim made here."
        ),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, 
        json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    print("files identical            :",
          f"{receipt['files_identical']}/{receipt['files_compared']}")
    print("membership rows            :", rows)
    print("changed membership fields  :", field_diff["changed_fields"] or "none")
    print("differences outside lineage:", len(outside_lineage) or "none")
    print("national population changed:", not receipt["national_population_unchanged"])
    return 0 if receipt["national_population_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
