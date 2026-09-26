r"""Cycle #37 — Attempt #9 — an independent identity-derived source-unit oracle for career lineage (MF37A08-01).

    a09_source_unit_oracle.py --successor A05.sqlite --a04 A04.sqlite --database DEFAULT.sqlite --out RESULT.json
                              [--label NAME]

The Attempt 8 oracle found the unit a row's recorded witness *is*; a row with no witness had no unit, and every edge
touching one was ``UNRESOLVED_NO_WITNESS`` -- honest, but it could not say whether the manager's NULL-span rows were
the jobs they claimed. This oracle derives each row's unit from its **identity** instead: the unit the data's identity
rule names for ``(family, row_index)`` in the row's own verified capture, whether or not the row records a witness.
It reuses only the Attempt 8 oracle's raw-structure reader (``a08_source_field_oracle``: sqlite3, json and re, no
project module; it shares no code with the parser or the verifier), and adds, on its own:

* **the row's identity**: its episode identity must be its own page, revision, family, row and interval;
* **its witness**: when it records one, the witness must be exactly the identity's unit (the Attempt 8 classes);
* **its unwitnessed text**: text it carries without a witness must be the unit's own -- a numbered field's value, or,
  for a line's years, text inside the line or its employer's line -- else ``TEXT_NOT_ITS_UNIT``;
* **its edges**: child and parent are the same source assertion when their identities name the same unit, or the child
  is a role line of the parent's line; another unit is ``CROSSED_ANOTHER_SOURCE_FIELD``; a side whose row is invalid is
  ``CROSSED_INVALID_ROW``.

Nothing is inferred where the raw text cannot decide: an identity naming no unit (``UNRESOLVED_NO_UNIT``), several
units and no witness (``UNRESOLVED_AMBIGUOUS``) or an unreadable capture (``UNRESOLVED_NO_STRUCTURE``) is counted as
unresolved, never as proof, and every edge touching one stays unresolved. Interval-level agreement inside one
multi-interval field is reported as not adjudicated (its text is normalized, not a source substring).
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a08_source_field_oracle as structure  # noqa: E402  (the raw-structure reader only)

ORACLE_VERSION = "BAS-C37A09-SOURCE-UNIT-ORACLE-v1"
_IDENTITY = re.compile(r"^[A-Za-z0-9-]+:(\d+):(\d+):(COACHING|PLAYING|ADMINISTRATIVE):(\d+):(\d+)$")
_LITERAL = {"v37.2": True, "v37.4": True, "v37.5": False}
VALID = ("UNIT_WITNESSED_EXACT", "UNIT_BY_IDENTITY_NO_WITNESS")
UNRESOLVED = ("UNRESOLVED_NO_UNIT", "UNRESOLVED_AMBIGUOUS", "UNRESOLVED_NO_STRUCTURE")


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


class Rows:
    def __init__(self) -> None:
        self.captures = structure.Captures()

    def derive(self, row: dict[str, Any], version: str) -> dict[str, Any]:
        """The unit ``row``'s identity names, and what the row records against it."""

        match = _IDENTITY.match(str(row.get("episode_id")))
        own = (str(row.get("pageid")), str(row.get("revision")), str(row.get("family")), str(row.get("row_index")),
               str(row.get("interval_index")))
        if match is None or tuple(match.groups()) != own:
            return {"class": "INVALID_IDENTITY_NOT_THE_ROW"}
        text = self.captures.text(row)
        if text is None:
            return {"class": "UNRESOLVED_NO_STRUCTURE"}
        team = structure._span(row.get("team_char_span"))
        years = structure._span(row.get("years_char_span"))
        if team is not None or years is not None:
            # A witness: the Attempt 8 classification, which also requires the unit to be the identity's.
            verdict = self.captures.classify(row, version)
            if verdict["class"] in ("EXACT_UNIT", "EXACT_UNIT_UNDER_THE_LITERAL_READING"):
                named = self._named(row, text, version, literal_first=verdict["class"].endswith("LITERAL_READING"))
                unit = next((u for u in named if u.get("region") == team or u.get("years") == years
                             or (years is not None and self._inside_line(years, u))), named[0] if named else None)
                return {"class": "UNIT_WITNESSED_EXACT", "unit": verdict["unit"], "form": verdict["form"],
                        "line_of": verdict.get("line_of"), "text_problems": self._text_problems(row, unit, text)}
            return {"class": f"INVALID_WITNESS_{verdict['class']}"}
        named = self._named(row, text, version)
        if not named:
            return {"class": "UNRESOLVED_NO_UNIT"} if _blank(row.get("team_raw")) and _blank(row.get("years_raw")) \
                else {"class": "INVALID_TEXT_WITHOUT_A_UNIT"}
        if len(named) > 1:
            return {"class": "UNRESOLVED_AMBIGUOUS"}
        unit = named[0]
        problems = self._text_problems(row, unit, text)
        # The unit is known from the identity even when the row's text is not its own: an edge is still judged by it.
        return {"class": "INVALID_TEXT_NOT_ITS_UNIT" if problems else "UNIT_BY_IDENTITY_NO_WITNESS",
                "problems": problems, "unit": unit["key"], "form": unit["form"], "line_of": unit.get("line_of")}

    def _named(self, row: dict[str, Any], text: str, version: str, literal_first: bool | None = None) -> list[dict]:
        literal = _LITERAL[version] if literal_first is None else literal_first
        key = (str(row.get("raw_file") or ""), literal)
        if key not in self.captures.structure:
            self.captures.structure[key] = structure.units(text, literal=literal)
        return list((self.captures.structure[key] or {}).get("named", {}).get(
            (str(row.get("family")), int(row.get("row_index"))), []))

    @staticmethod
    def _inside_line(years: tuple[int, int], unit: dict[str, Any]) -> bool:
        return any(region is not None and region[0] <= years[0] <= years[1] <= region[1]
                   for region in (unit.get("region"), unit.get("employer")))

    @staticmethod
    def _text_problems(row: dict[str, Any], unit: dict[str, Any] | None, text: str) -> list[str]:
        """Text a row carries for a field it records no witness for, against the unit."""

        problems = []
        if unit is None:
            return problems
        if structure._span(row.get("team_char_span")) is None and not _blank(row.get("team_raw")):
            region = unit.get("region")
            if region is None or str(row["team_raw"]) != text[region[0]:region[1]]:
                problems.append("TEAM_TEXT_NOT_ITS_UNIT")
        if structure._span(row.get("years_char_span")) is None and not _blank(row.get("years_raw")):
            value = str(row["years_raw"])
            if unit["form"] == "FIELD":
                region = unit.get("years")
                if region is None or value != text[region[0]:region[1]]:
                    problems.append("YEARS_TEXT_NOT_ITS_UNIT")
            elif not any(r is not None and value in text[r[0]:r[1]] for r in (unit.get("region"), unit.get("employer"))):
                problems.append("YEARS_TEXT_NOT_IN_ITS_LINE")
        return problems


def _verdict_of_row(verdict: dict[str, Any]) -> str:
    if verdict["class"] in VALID and verdict.get("text_problems"):
        return "INVALID_TEXT_NOT_ITS_UNIT"
    return verdict["class"]


def relation(name: str, children: dict[str, dict[str, Any]], parents: dict[str, dict[str, Any]], key: str,
             verdicts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    counts: collections.Counter = collections.Counter()
    examples: dict[str, list[Any]] = collections.defaultdict(list)
    for cid, child in children.items():
        for pid in json.loads(child.get(key) or "[]"):
            if pid not in parents:
                verdict = "PARENT_ABSENT"
            else:
                c, p = verdicts[cid], verdicts[pid]
                cls = (_verdict_of_row(c), _verdict_of_row(p))
                same = None
                if c.get("unit") is not None and p.get("unit") is not None:
                    same = ("SAME_SOURCE_UNIT" if c["unit"] == p["unit"] else
                            "SAME_SOURCE_UNIT_ROLE_LINE_OF_ITS_LINE" if c.get("line_of") == p["unit"] else None)
                    if same is None:
                        verdict = "CROSSED_ANOTHER_SOURCE_FIELD"     # the identities name two units
                if c.get("unit") is None or p.get("unit") is None or same is not None:
                    if any(x.startswith("INVALID") for x in cls):
                        verdict = "CROSSED_INVALID_ROW"
                    elif any(x in UNRESOLVED for x in cls):
                        verdict = "UNRESOLVED_" + "_AND_".join(sorted({x.replace("UNRESOLVED_", "") for x in cls
                                                                      if x in UNRESOLVED}))
                    else:
                        verdict = same
            counts[verdict] += 1
            if not verdict.startswith("SAME_") and len(examples[verdict]) < 5:
                examples[verdict].append([cid, pid])
    crossed = sum(v for k, v in counts.items() if k.startswith("CROSSED") or k == "PARENT_ABSENT")
    return {"relation": name, "edges": sum(counts.values()), "counts": dict(counts), "crossed_edges": crossed,
            "unresolved_edges": sum(v for k, v in counts.items() if k.startswith("UNRESOLVED")),
            "examples": dict(examples)}


def oracle(successor: Path, a04: Path, database: Path) -> dict[str, Any]:
    rows = Rows()
    default = structure._load(database, "career_episode_successor", ())
    older = structure._load(a04, "career_episode_a04", ("predecessor_episode_ids",))
    children = structure._load(successor, "career_episode_a05", ("predecessor_episode_ids", "a04_episode_ids"))
    verdicts: dict[str, dict[str, Any]] = {}
    for table, version in ((default, "v37.2"), (older, "v37.4"), (children, "v37.5")):
        for identity, row in table.items():
            verdicts[identity] = rows.derive(row, version)
    classes = {name: dict(collections.Counter(_verdict_of_row(verdicts[i]) for i in table))
               for name, table in (("default", default), ("A04", older), ("A05", children))}
    invalid = {name: sorted(i for i in table if _verdict_of_row(verdicts[i]).startswith("INVALID"))[:10]
               for name, table in (("default", default), ("A04", older), ("A05", children))}
    relations = [relation("A5<-default", children, default, "predecessor_episode_ids", verdicts),
                 relation("A5<-A4", children, older, "a04_episode_ids", verdicts),
                 relation("A4<-default", older, default, "predecessor_episode_ids", verdicts)]
    return {"oracle_version": ORACLE_VERSION, "successor": str(successor),
            "successor_sha256": structure.sha256_file(successor), "a04": str(a04),
            "a04_sha256": structure.sha256_file(a04), "database": str(database),
            "rows": {"default": len(default), "A04": len(older), "A05": len(children)},
            "captures_read": len(rows.captures.texts),
            "captures_unreadable_or_changed": sum(1 for _d, t in rows.captures.texts.values() if t is None),
            "row_classes": classes, "invalid_row_examples": invalid, "relations": relations,
            "crossed_edges": sum(r["crossed_edges"] for r in relations),
            "unresolved_edges": sum(r["unresolved_edges"] for r in relations),
            "limits": ("identity-derived units and unwitnessed text are adjudicated; interval agreement inside one "
                       "multi-interval field is not (interval text is normalized, not a source substring); an "
                       "absent contradiction is not a full semantic audit of the biography")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--successor", type=Path, required=True)
    parser.add_argument("--a04", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", default="")
    args = parser.parse_args(argv)
    result = oracle(args.successor, args.a04, args.database)
    result["label"] = args.label
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({k: result[k] for k in ("rows", "row_classes", "crossed_edges", "unresolved_edges")}, indent=1,
                     default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
