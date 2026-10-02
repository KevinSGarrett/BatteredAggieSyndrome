r"""Cycle #37 — Attempt #10 — an independent interval oracle for career lineage inside one source field (MF37A09-01).

    a10_interval_oracle.py --successor A05.sqlite --a04 A04.sqlite --database DEFAULT.sqlite --out RESULT.json
                           [--label NAME]

The Attempt 9 oracle stopped at the source unit: two rows of one field (Walter Camp's ``coachyears2 = 1892,
1894–1895``) name the same unit, so a crossed pair of their edges looked like two ``SAME_SOURCE_UNIT`` edges. This
oracle goes one grain further, without the production predicate: it imports no project module and shares no code with
the parser, the verifier or ``career_interval``. It reuses only the Attempt 8 oracle's raw-structure reader (fields,
list lines and role lines of a revision; ``a08_source_field_oracle``) and, on its own:

* **reads the unit's years text from the raw revision** -- a numbered field's ``*_years`` value; for a list, nested or
  role line, the last parenthetical of the line that holds a year (else, for a nested or role line, its employer
  line's) -- decoding HTML entities, rendering a season template ``{{X|1956|1961}}`` as ``1956–1961``;
* **splits it into intervals itself**: top-level pieces separated by commas, semicolons or ``and``, each holding a
  year or a question mark, ordered chronologically by their first year (a piece without one last) -- the order every
  parser version numbers its intervals in;
* **binds each identity to the raw interval at its ordinal**, and adjudicates each row and each edge:

  - a row is ``PROVEN`` when the field splits into as many intervals as the entry holds rows and what the row states
    (its ``years_as_written``, unless blank) is that interval's text, spaces and dash spellings aside
    (``PROVEN_TEXT_ABSENT`` when it states none); ``INVALID_TEXT_IS_ANOTHER_INTERVAL`` when its text is a different
    interval of the same field; ``UNRESOLVED_*`` when this oracle's own split cannot decide (another count, text it
    cannot place, an identity naming no unit or several);
  - an edge inside one field is ``PROVEN_SAME_INTERVAL`` when the two identities name the same ordinal and neither row
    is invalid, ``PROVEN_RESTRUCTURE_ALL_TO_ALL`` for a restructured field whose every row names every parent row,
    ``INVALID_CROSSED_INTERVAL`` for another ordinal, ``INVALID_ROW`` when a side is invalid, and
    ``UNRESOLVED_ROW`` when a side is unresolved;

* **classifies every row that states no interval text** (the missing-period rows) by whether its source unit states a
  period at all (``NO_PERIOD_IN_SOURCE``) or does (``BLANK_WHERE_SOURCE_STATES_A_PERIOD`` -- absent text, which grants
  nothing; the row's lineage is still its identity's).

Nothing is inferred where the raw text cannot decide; an unresolved row or edge is counted, never called proven. The
delivered (v37.2) parser read some fields differently (bare years for ``1990–?``, two years for ``1911&ndash;1916``); a
delivered entry whose count this oracle's split does not reproduce is unresolved at row grain, and its edges are then
judged by ordinal and restructure structure only. This is an independent check at interval grain, not a full semantic
audit of any biography.
"""

from __future__ import annotations

import argparse
import collections
import html
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a08_source_field_oracle as structure  # noqa: E402  (the raw-structure reader only)

ORACLE_VERSION = "BAS-C37A10-INTERVAL-ORACLE-v1"
_IDENTITY = re.compile(r"^[A-Za-z0-9-]+:(\d+):(\d+):(COACHING|PLAYING|ADMINISTRATIVE):(\d+):(\d+)$")
_LITERAL = {"v37.2": True, "v37.4": True, "v37.5": False}
_COLUMNS = ("start", "end", "disposition", "predecessor_episode_ids", "a04_episode_ids", "a04_disposition")
_YEAR = re.compile(r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_BREAK = re.compile(r"<br\s*/?\s*>", re.I)
_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_TEMPLATE = re.compile(r"\{\{([^{}]*)\}\}")
_DASH = re.compile(r"\s*(?:[‐‑‒–—−-]|&ndash;|&mdash;)\s*")
_SEPARATOR = re.compile(r"\s*(?:[,;]|\band\b|\n)\s*", re.I)
#: Templates that display their content (kept); every other non-season template -- notes, citations -- is dropped.
_DISPLAY = {"nowrap", "nobr", "small", "smaller", "big", "abbr", "tooltip"}


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _render_template(match: re.Match[str]) -> str:
    """A season template shows its years (``{{NFL Year|1956|1961}}`` -> ``1956–1961``); a display template its first
    argument; a note or citation nothing."""

    parts = [p.strip() for p in match.group(1).split("|")]
    years = [p for p in parts[1:] if _YEAR.fullmatch(p)]
    if years:
        return "–".join(years[:2])
    positional = [p for p in parts[1:] if "=" not in p]
    return positional[0] if positional and parts[0].strip().lower() in _DISPLAY else ""


def render(raw: str) -> str:
    """The displayed text of a wikitext fragment; a line break becomes a line boundary."""

    text = _REF.sub("", _COMMENT.sub("", raw))
    for _ in range(4):                      # nested templates, innermost first
        text = _TEMPLATE.sub(_render_template, text)
    text = _LINK.sub(lambda m: m.group(1), text)
    text = _TAG.sub(" ", _BREAK.sub("\n", html.unescape(text)))
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n"))


def split(raw: str | None) -> list[str] | None:
    """This oracle's own intervals of a years text, chronologically; None when it states no period at all."""

    if raw is None:
        return None
    text = render(raw)
    pieces = [p.strip(" ()") for p in _SEPARATOR.split(text)]
    pieces = [p for p in pieces if _YEAR.search(p) or "?" in p]
    if not pieces:
        return None
    return sorted(pieces, key=lambda p: (_YEAR.search(p) is None, int(_YEAR.search(p).group(1)) if _YEAR.search(p)
                                         else 0))


def normal(text: Any) -> str:
    return _DASH.sub("–", re.sub(r"\s+", "", str(text or ""))).casefold()


def _line_years(line: str) -> str | None:
    """The last parenthetical of a line that displays a year (notes, citations and link targets removed first)."""

    found = None
    shown = _LINK.sub(lambda m: m.group(1), _REF.sub("", _COMMENT.sub("", line)))
    for paren in re.finditer(r"\(([^()]*)\)", shown):
        if _YEAR.search(render(paren.group(1))):
            found = paren.group(1)
    return found


def _head(line: str) -> str:
    """A list line up to its first break: what follows is its role lines, each a unit of its own."""

    return _BREAK.split(line, maxsplit=1)[0]


class Oracle:
    def __init__(self) -> None:
        self.captures = structure.Captures()

    def unit_years(self, row: dict[str, Any], version: str) -> tuple[str, str | None]:
        """``(state, years text)`` of the unit ``row``'s identity names in its verified revision."""

        match = _IDENTITY.match(str(row.get("episode_id")))
        own = (str(row.get("pageid")), str(row.get("revision")), str(row.get("family")), str(row.get("row_index")),
               str(row.get("interval_index")))
        if match is None or tuple(match.groups()) != own:
            return "INVALID_IDENTITY_NOT_THE_ROW", None
        text = self.captures.text(row)
        if text is None:
            return "UNRESOLVED_NO_CAPTURE", None
        key = (str(row.get("raw_file") or ""), _LITERAL[version])
        if key not in self.captures.structure:
            self.captures.structure[key] = structure.units(text, literal=_LITERAL[version])
        named = (self.captures.structure[key] or {}).get("named", {}).get(
            (str(row.get("family")), int(row.get("row_index"))), [])
        if not named:
            return "UNRESOLVED_NO_UNIT", None
        if len(named) > 1:
            return "UNRESOLVED_AMBIGUOUS_UNIT", None
        unit = named[0]
        if unit["form"] == "FIELD":
            years = unit.get("years")
            return "UNIT", (text[years[0]:years[1]] if years else None)
        line = text[unit["region"][0]:unit["region"][1]]
        # A list line's own period is in its head; a nested or role line's in itself, else its employer line's head.
        own_years = _line_years(_head(line) if unit["form"] == "LIST_LINE" else line)
        if own_years is None and unit.get("employer") is not None:
            own_years = _line_years(_head(text[unit["employer"][0]:unit["employer"][1]]))
        return "UNIT", own_years


def _entries(rows: dict[str, dict[str, Any]]) -> dict[tuple[str, ...], list[str]]:
    out: dict[tuple[str, ...], list[str]] = collections.defaultdict(list)
    for identity, row in rows.items():
        out[(str(row["pageid"]), str(row["revision"]), str(row["family"]), str(row["row_index"]))].append(identity)
    return out


def adjudicate_rows(oracle: Oracle, rows: dict[str, dict[str, Any]], version: str,
                    entries: dict[tuple[str, ...], list[str]]) -> dict[str, dict[str, Any]]:
    verdicts = {}
    for entry, identities in entries.items():
        if len(identities) < 2:
            continue
        for identity in identities:
            row = rows[identity]
            state, years = oracle.unit_years(row, version)
            if state != "UNIT":
                verdicts[identity] = {"class": state}
                continue
            pieces = split(years)
            ordinal = int(row["interval_index"])
            stated = row.get("years_as_written")
            if pieces is None or len(pieces) != len(identities):
                verdicts[identity] = {"class": "UNRESOLVED_SPLIT_COUNT_DIFFERS", "pieces": pieces,
                                      "rows": len(identities), "years_raw": years}
                continue
            if _blank(stated):
                verdicts[identity] = {"class": "PROVEN_TEXT_ABSENT", "interval": pieces[ordinal]}
            elif normal(stated) == normal(pieces[ordinal]):
                verdicts[identity] = {"class": "PROVEN", "interval": pieces[ordinal]}
            elif any(normal(stated) == normal(p) for j, p in enumerate(pieces) if j != ordinal):
                verdicts[identity] = {"class": "INVALID_TEXT_IS_ANOTHER_INTERVAL", "interval": pieces[ordinal],
                                      "stated": stated}
            else:
                verdicts[identity] = {"class": "UNRESOLVED_TEXT_NOT_PLACED", "interval": pieces[ordinal],
                                      "stated": stated}
    return verdicts


def adjudicate_edges(name: str, children: dict[str, dict[str, Any]], parents: dict[str, dict[str, Any]], key: str,
                     child_verdicts: dict[str, dict[str, Any]], parent_verdicts: dict[str, dict[str, Any]],
                     parent_dispositions: dict[str, str]) -> dict[str, Any]:
    child_entries, parent_entries = _entries(children), _entries(parents)
    entry_of = {i: e for e, ids in child_entries.items() for i in ids}
    parent_entry_of = {i: e for e, ids in parent_entries.items() for i in ids}
    counts: collections.Counter = collections.Counter()
    examples: dict[str, list[Any]] = collections.defaultdict(list)
    for cid, child in children.items():
        for pid in json.loads(child.get(key) or "[]"):
            if pid not in parents:
                verdict = "INVALID_PARENT_ABSENT"
            else:
                entry = parent_entry_of[pid]
                if entry != entry_of[cid]:
                    continue                                   # another unit (a role line of its line): not interval grain
                if len(parent_entries[entry]) < 2 and len(child_entries[entry]) < 2:
                    continue                                   # one interval on both sides: field grain only
                restructured = any(parent_dispositions.get(p) == "RESTRUCTURED_INTERVALS" for p in parent_entries[entry])
                c, p = child_verdicts.get(cid, {"class": "SINGLE"}), parent_verdicts.get(pid, {"class": "SINGLE"})
                if restructured:
                    every = all(set(parent_entries[entry]) <= set(json.loads(children[x].get(key) or "[]"))
                                for x in child_entries[entry])
                    verdict = "PROVEN_RESTRUCTURE_ALL_TO_ALL" if every else "INVALID_RESTRUCTURE_NOT_ALL_TO_ALL"
                elif int(child["interval_index"]) != int(parents[pid]["interval_index"]):
                    verdict = "INVALID_CROSSED_INTERVAL"
                elif c["class"].startswith("INVALID") or p["class"].startswith("INVALID"):
                    verdict = "INVALID_ROW"
                elif len(parent_entries[entry]) != len(child_entries[entry]):
                    verdict = "INVALID_COUNT_CHANGED_WITHOUT_RESTRUCTURE"
                elif c["class"].startswith("UNRESOLVED"):
                    verdict = "UNRESOLVED_ROW"
                else:
                    verdict = "PROVEN_SAME_INTERVAL"
            counts[verdict] += 1
            if not verdict.startswith("PROVEN") and len(examples[verdict]) < 8:
                examples[verdict].append([cid, pid])
    return {"relation": name, "interval_grain_edges": sum(counts.values()), "counts": dict(counts),
            "proven": sum(v for k, v in counts.items() if k.startswith("PROVEN")),
            "unresolved": sum(v for k, v in counts.items() if k.startswith("UNRESOLVED")),
            "invalid": sum(v for k, v in counts.items() if k.startswith("INVALID")), "examples": dict(examples)}


def _load(path: Path, table: str) -> dict[str, dict[str, Any]]:
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        present = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        columns = [c for c in structure.COLUMNS + _COLUMNS if c in present]
        quoted = ",".join(f'"{c}"' for c in columns)
        return {r["episode_id"]: dict(r) for r in conn.execute(f"SELECT {quoted} FROM {table}")}
    finally:
        conn.close()


def _dispositions(path: Path, table: str, key: str) -> dict[str, str]:
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        return {str(r[0]): str(r[1]) for r in conn.execute(f"SELECT {key}, disposition FROM {table}")}
    finally:
        conn.close()


def missing_periods(oracle: Oracle, rows: dict[str, dict[str, Any]], version: str) -> dict[str, Any]:
    counts: collections.Counter = collections.Counter()
    examples: dict[str, list[str]] = collections.defaultdict(list)
    for identity, row in rows.items():
        if not _blank(row.get("years_as_written")):
            continue
        state, years = oracle.unit_years(row, version)
        if state != "UNIT":
            verdict = state
        elif split(years) is None:
            verdict = "NO_PERIOD_IN_SOURCE"
        else:
            verdict = "BLANK_WHERE_SOURCE_STATES_A_PERIOD"
        counts[verdict] += 1
        if verdict != "NO_PERIOD_IN_SOURCE" and len(examples[verdict]) < 8:
            examples[verdict].append(identity)
    return {"rows_stating_no_interval_text": sum(counts.values()), "counts": dict(counts), "examples": dict(examples)}


def oracle(successor: Path, a04: Path, database: Path) -> dict[str, Any]:
    runner = Oracle()
    default = _load(database, "career_episode_successor")
    older = _load(a04, "career_episode_a04")
    children = _load(successor, "career_episode_a05")
    verdicts = {name: adjudicate_rows(runner, rows, version, _entries(rows))
                for name, rows, version in (("default", default, "v37.2"), ("A04", older, "v37.4"),
                                            ("A05", children, "v37.5"))}
    a05_disp = _dispositions(successor, "career_a05_disposition", "predecessor_episode_id")
    a05_map = _dispositions(successor, "career_a05_from_a04", "a04_episode_id")
    a04_disp = _dispositions(a04, "career_a04_disposition", "predecessor_episode_id")
    relations = [adjudicate_edges("A5<-default", children, default, "predecessor_episode_ids", verdicts["A05"],
                                  verdicts["default"], a05_disp),
                 adjudicate_edges("A5<-A4", children, older, "a04_episode_ids", verdicts["A05"], verdicts["A04"],
                                  a05_map),
                 adjudicate_edges("A4<-default", older, default, "predecessor_episode_ids", verdicts["A04"],
                                  verdicts["default"], a04_disp)]
    groups = {name: {"multi_interval_entries": sum(1 for ids in _entries(rows).values() if len(ids) > 1),
                     "rows_in_them": sum(len(ids) for ids in _entries(rows).values() if len(ids) > 1),
                     "row_classes": dict(collections.Counter(v["class"] for v in verdicts[name].values()))}
              for name, rows in (("default", default), ("A04", older), ("A05", children))}
    for name in groups:
        classes = groups[name]["row_classes"]
        groups[name].update(proven=sum(v for k, v in classes.items() if k.startswith("PROVEN")),
                            unresolved=sum(v for k, v in classes.items() if k.startswith("UNRESOLVED")),
                            invalid=sum(v for k, v in classes.items() if k.startswith("INVALID")),
                            invalid_examples=sorted(i for i, v in verdicts[name].items()
                                                    if v["class"].startswith("INVALID"))[:10],
                            unresolved_examples=sorted(i for i, v in verdicts[name].items()
                                                       if v["class"].startswith("UNRESOLVED"))[:10])
    a05_groups = [{"entry": list(entry), "rows": sorted(ids),
                   "classes": {i: verdicts["A05"][i]["class"] for i in sorted(ids)},
                   "intervals": {i: verdicts["A05"][i].get("interval") for i in sorted(ids)},
                   "stated": {i: children[i].get("years_as_written") for i in sorted(ids)},
                   "default_parents": {i: json.loads(children[i].get("predecessor_episode_ids") or "[]")
                                       for i in sorted(ids)},
                   "a04_parents": {i: json.loads(children[i].get("a04_episode_ids") or "[]") for i in sorted(ids)}}
                  for entry, ids in sorted(_entries(children).items()) if len(ids) > 1]
    return {"oracle_version": ORACLE_VERSION, "successor": str(successor),
            "successor_sha256": structure.sha256_file(successor), "a04": str(a04),
            "a04_sha256": structure.sha256_file(a04), "database": str(database),
            "database_sha256": structure.sha256_file(database),
            "rows": {"default": len(default), "A04": len(older), "A05": len(children)},
            "captures_read": len(runner.captures.texts),
            "groups": groups, "relations": relations,
            "invalid_edges": sum(r["invalid"] for r in relations),
            "unresolved_edges": sum(r["unresolved"] for r in relations),
            "missing_periods": {"A05": missing_periods(runner, children, "v37.5"),
                                "A04": missing_periods(runner, older, "v37.4")},
            "a05_multi_interval_groups": a05_groups,
            "limits": ("interval grain only: this oracle's own split of a unit's raw years text, chronological ordinals "
                       "and the rows' identities; a row it cannot place stays unresolved; it adjudicates no employer, "
                       "role or biography truth, and the delivered v37.2 readings it cannot reproduce stay unresolved "
                       "at row grain")}


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
    print(json.dumps({"groups": {k: {kk: v[kk] for kk in ("multi_interval_entries", "rows_in_them", "proven",
                                                          "unresolved", "invalid")} for k, v in result["groups"].items()},
                      "relations": [{k: r[k] for k in ("relation", "interval_grain_edges", "proven", "unresolved",
                                                       "invalid")} for r in result["relations"]],
                      "missing_periods": {k: v["counts"] for k, v in result["missing_periods"].items()}}, indent=1,
                     default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
