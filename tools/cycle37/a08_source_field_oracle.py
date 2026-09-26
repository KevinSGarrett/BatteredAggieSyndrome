r"""Cycle #37 — Attempt #8 — an independent source-field oracle for career lineage (MF37A07-01).

    a08_source_field_oracle.py --successor A05.sqlite --a04 A04.sqlite --database DEFAULT.sqlite --out RESULT.json
                               [--label NAME]

The Attempt 7 worker oracle judged an edge by the same overlap/containment of recorded spans the verifier used, so an
enlarged witness satisfied both. This oracle never compares two recorded spans with each other. It reads each raw
capture's revision text itself and derives the source structure from it -- sqlite3, json and re only, no project
module, sharing no code with the parser or the verifier:

* **Fields.** Every ``{{Infobox ...}}`` template is closed by a bracket stack (a ``]]`` closes only an open ``[[``,
  a ``}}`` only an open ``{{``), and split at its top-level bars into ``name = value`` fields; a value is the text
  after ``=`` with its surrounding whitespace removed. HTML comments and ``<nowiki>`` are opaque to the structure
  (the wiki's own reading); rows the v37.2/v37.4 parsers read with a bar inside a comment as a separator are
  recognized separately as that *literal* reading and counted as such, never silently.
* **Lines.** A career list field is split into its lines: bullet lines (depth = number of ``*``), then the items of
  a list template written as a block; a nested line belongs to the last top-level line before it. A top-level line
  (or the one list template it consists of) is split at ``<br>`` and, inside an item-list template, at its
  top-level bars into role lines.
* **Identity.** The data's identity rule names each unit: numbered fields by family and number (the spelled-out
  ``coaching_``-style names from 2001), list lines by the field's base and ordinal, role lines by line index * 100
  + line number.

For every row of the delivered release, the Attempt 4 file and the successor it then finds the unit whose text
*is* the row's recorded team witness (else its years witness), classifies the witness (exact unit; a date inside its
line or its employer's line; crossing a field boundary; inside a field but not a unit; exactly another unit; no
witness; no structure), and requires that unit to be the one the row's identity names. An edge is the same source
assertion when child and parent are the same unit, or the child is a role line of the parent's line. Everything the
oracle cannot adjudicate is counted under an explicit ``UNRESOLVED_*`` class, never as proof. Interval-level
agreement inside one multi-interval field is reported as not independently adjudicated.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

ORACLE_VERSION = "BAS-C37A08-SOURCE-FIELD-ORACLE-v1"
_OPAQUE = re.compile(r"<!--.*?-->|<nowiki\b[^>]*>.*?</nowiki\s*>", re.S | re.I)
_TOKEN = re.compile(r"\{\{|\}\}|\[\[|\]\]|\|")
_INFOBOX_OPEN = re.compile(r"\{\{\s*infobox[\s_]", re.I)
_NUMBERED = re.compile(r"^(coach|coaching|player|playing|admin|administrating|executive)_?(team|years)([0-9]+)$")
_FAMILY = {"coach": "COACHING", "coaching": "COACHING", "player": "PLAYING", "playing": "PLAYING",
           "admin": "ADMINISTRATIVE", "administrating": "ADMINISTRATIVE", "executive": "ADMINISTRATIVE"}
_SPELLED = {"coaching", "playing", "administrating"}
_LISTS = {"pastcoaching": ("COACHING", 1000), "pastteams": ("PLAYING", 1000), "pastexecutive": ("ADMINISTRATIVE", 1000),
          "pastexecutives": ("ADMINISTRATIVE", 1000), "pastadmin": ("ADMINISTRATIVE", 3000)}
_LIST_TEMPLATE = re.compile(r"\{\{\s*(ubl|unbulleted[ _]list|plainlist|flatlist|nowrap|bulleted[ _]list|blist)\s*\|",
                            re.I)
_ITEM_TEMPLATES = {"ubl", "unbulleted list", "unbulleted_list", "bulleted list", "bulleted_list", "blist"}
_BREAK = re.compile(r"<br\s*/?\s*>", re.I)
_LEAD = re.compile(r"[\s\-–—•·:]*")
_BULLET = re.compile(r"[ \t]*(\*+)[ \t]*")
_NAMED_ARG = re.compile(r"\s*[A-Za-z_][\w -]*=")
COLUMNS = ("episode_id", "pageid", "revision", "family", "row_index", "interval_index", "raw_file", "raw_file_sha256",
           "wikitext_sha256", "team_char_span", "years_char_span", "team_raw", "years_raw", "years_as_written")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _span(value: Any) -> tuple[int, int] | None:
    if value in (None, ""):
        return None
    try:
        decoded = json.loads(value) if isinstance(value, str) else value
    except ValueError:
        return (-1, -1)
    if decoded is None or decoded == [None, None]:
        return None
    if isinstance(decoded, list) and len(decoded) == 2 and all(type(v) is int for v in decoded) and 0 <= decoded[0] <= decoded[1]:
        return decoded[0], decoded[1]
    return (-1, -1)


# ---------------------------------------------------------------------------------------------- raw structure


def _masked(text: str) -> str:
    return _OPAQUE.sub(lambda m: " " * len(m.group(0)), text)


def _close(scan: str, start: int) -> int:
    """Index just past the ``}}`` that closes the template opened at ``start`` (bracket stack; mismatches ignored)."""

    stack: list[str] = []
    for token in _TOKEN.finditer(scan, start):
        value = token.group()
        if value in ("{{", "[["):
            stack.append(value)
        elif value == "}}" and stack and stack[-1] == "{{":
            stack.pop()
            if not stack:
                return token.end()
        elif value == "]]" and stack and stack[-1] == "[[":
            stack.pop()
    return len(scan)


def _top_bars(scan: str, start: int, end: int, depth: int) -> list[int]:
    """Positions of the bars at bracket depth ``depth`` (1 = directly inside the template opened at ``start``)."""

    stack: list[str] = []
    bars = []
    for token in _TOKEN.finditer(scan, start, end):
        value = token.group()
        if value in ("{{", "[["):
            stack.append(value)
        elif value == "}}" and stack and stack[-1] == "{{":
            stack.pop()
        elif value == "]]" and stack and stack[-1] == "[[":
            stack.pop()
        elif value == "|" and len(stack) == depth:
            bars.append(token.start())
    return bars


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def fields(text: str, *, literal: bool) -> list[tuple[str, int, int, int]]:
    """``(name, value start, value end, infobox ordinal)`` of every named top-level field of every infobox. With
    ``literal`` a comment or nowiki is read as ordinary text (the v37.2/v37.4 parsers' reading)."""

    scan = text if literal else _masked(text)
    out = []
    for ordinal, opened in enumerate(_INFOBOX_OPEN.finditer(scan)):
        end = _close(scan, opened.start())
        inner_end = end - 2 if scan[end - 2:end] == "}}" else end
        bars = _top_bars(scan, opened.start(), inner_end, 1)
        for left, right in zip(bars, bars[1:] + [inner_end]):
            chunk = scan[left + 1:right]
            if "=" not in chunk:
                continue
            name = chunk.split("=", 1)[0].strip().lower()
            value_start, value_end = _trim(text, left + 1 + chunk.index("=") + 1, right)
            out.append((name, value_start, value_end, ordinal))
    return out


def _list_lines(text: str, scan: str, start: int, end: int) -> list[tuple[int, int, int]]:
    """``(depth, line start, line end)`` of a list field's entries: bullet lines outside list-template blocks, then
    the items of each block (depth 1), in that order."""

    blocks = []
    position = start
    while position < end:
        newline = scan.find("\n", position, end)
        line_end = end if newline < 0 else newline
        stripped = scan[position:line_end].lstrip(" \t")
        opened = position + len(scan[position:line_end]) - len(stripped)
        # The template's name and first bar may be on different lines ("| pastexecutive={{bulleted list\n| ...").
        template = _LIST_TEMPLATE.match(scan, opened) if stripped.startswith("{{") else None
        if template:
            closed = _close(scan, opened)
            rest_end = scan.find("\n", closed, end)
            name = template.group(1).lower()
            if closed <= end and not scan[closed:(end if rest_end < 0 else rest_end)].strip() and \
                    name.replace("_", " ") in {"ubl", "unbulleted list", "bulleted list", "blist"}:
                blocks.append((opened, closed))
        position = line_end + 1
    entries = []
    position = start
    while position < end:
        newline = text.find("\n", position, end)
        line_end = end if newline < 0 else newline
        bullet = _BULLET.match(scan, position, line_end)
        if bullet and not any(a <= position < b for a, b in blocks):
            content_start, content_end = _trim(text, bullet.end(), line_end)
            if content_end > content_start:
                entries.append((len(bullet.group(1)), content_start, content_end))
        position = line_end + 1
    for opened, closed in blocks:
        bars = _top_bars(scan, opened, closed - 2, 1)
        for left, right in zip(bars, bars[1:] + [closed - 2]):
            item_start, item_end = _trim(text, left + 1, right)
            if item_end > item_start and not _NAMED_ARG.match(scan[left + 1:right]):
                entries.append((1, item_start, item_end))
    return entries


def _role_lines(text: str, scan: str, start: int, end: int) -> list[tuple[int, int, int]]:
    """``(line number, start, end)`` of the lines after each break of one top-level entry."""

    body_start, body_end = start, end
    breaks: list[tuple[int, int]] = []
    template = _LIST_TEMPLATE.match(scan, start)
    if template and _close(scan, start) == end:
        body_start, body_end = _trim(text, template.end(), end - 2)
        if template.group(1).lower().replace("_", " ") in {"ubl", "unbulleted list", "bulleted list", "blist"}:
            breaks += [(bar, bar + 1) for bar in _top_bars(scan, start, end - 2, 1)]
    breaks += [(m.start(), m.end()) for m in _BREAK.finditer(scan, body_start, body_end)]
    breaks.sort()
    lines = []
    for number, (_, after) in enumerate(breaks, start=1):
        stop = breaks[number][0] if number < len(breaks) else body_end
        lead = _LEAD.match(text, after, stop)
        line_start = lead.end() if lead else after
        line_end = stop
        while line_end > line_start and text[line_end - 1].isspace():
            line_end -= 1
        lines.append((number, line_start, line_end))
    return lines


def units(text: str, *, literal: bool) -> dict[str, Any]:
    """Every unit the identity rule names, from the raw text alone: ``{(family, index): [unit, ...]}`` and a flat list."""

    scan = text if literal else _masked(text)
    named: dict[tuple[str, int], list[dict[str, Any]]] = collections.defaultdict(list)
    pairs: dict[tuple[str, int], dict[str, tuple[int, int, str]]] = {}
    for name, start, end, ordinal in fields(text, literal=literal):
        match = _NUMBERED.match(name)
        if match:
            word, kind, number = match.group(1), match.group(2), int(match.group(3))
            key = (_FAMILY[word], number + (2000 if word in _SPELLED else 0))
            pairs.setdefault(key + (word,), {}).setdefault(kind, (start, end, name))
            continue
        if name in _LISTS:
            family, base = _LISTS[name]
            employer = None
            for ordinal_in_list, (depth, line_start, line_end) in enumerate(_list_lines(text, scan, start, end), 1):
                index = base + ordinal_in_list
                unit = {"key": (family, index), "form": "LIST_LINE", "field": name, "region": (line_start, line_end)}
                if depth > 1 and employer is not None:
                    unit.update(form="NESTED_LINE", employer=employer["region"])
                    named[(family, index)].append(unit)
                    continue
                named[(family, index)].append(unit)
                employer = unit
                for number, role_start, role_end in _role_lines(text, scan, line_start, line_end):
                    named[(family, index * 100 + number)].append(
                        {"key": (family, index * 100 + number), "form": "ROLE_LINE", "field": name,
                         "region": (role_start, role_end), "employer": (line_start, line_end), "line_of": (family, index)})
    for (family, index, word), both in pairs.items():
        team, years = both.get("team"), both.get("years")
        named[(family, index)].append({"key": (family, index), "form": "FIELD", "field": (team or years)[2],
                                       "region": (team[0], team[1]) if team else None,
                                       "years": (years[0], years[1]) if years else None})
    regions = [(start, end) for _, start, end, _ in fields(text, literal=literal)]
    return {"named": dict(named), "field_regions": regions}


# ---------------------------------------------------------------------------------------------- per row


def _inside(inner: tuple[int, int], outer: tuple[int, int] | None) -> bool:
    return outer is not None and outer[0] <= inner[0] <= inner[1] <= outer[1]


def classify(row: dict[str, Any], structure: dict[str, Any] | None) -> dict[str, Any]:
    """The row's witness against the raw structure: the unit it is, and whether its identity names that unit."""

    team, years = _span(row.get("team_char_span")), _span(row.get("years_char_span"))
    if team is None and years is None:
        return {"class": "NO_WITNESS"}
    if structure is None:
        return {"class": "UNRESOLVED_NO_STRUCTURE"}
    key = (str(row.get("family")), int(row.get("row_index")))
    named = structure["named"]
    everything = [unit for units_ in named.values() for unit in units_]
    witness, field = (team, "team") if team is not None else (years, "years")
    if witness == (-1, -1):
        return {"class": f"{field.upper()}_MALFORMED"}
    match = None
    for unit in everything:
        region = unit["region"] if field == "team" else unit.get("years")
        if region == witness:
            match = unit
            if unit["key"] == key:
                break
    if match is None:
        in_field = any(_inside(witness, region) for region in structure["field_regions"])
        return {"class": f"{field.upper()}_INSIDE_A_FIELD_BUT_NOT_A_UNIT" if in_field
                else f"{field.upper()}_CROSSES_A_FIELD_BOUNDARY"}
    if match["key"] != key:
        return {"class": f"{field.upper()}_IS_ANOTHER_UNIT", "unit": match["key"]}
    if team is not None and years is not None:
        if match["form"] == "FIELD":
            if years != match.get("years"):
                return {"class": "YEARS_NOT_THE_YEARS_FIELD", "unit": match["key"]}
        elif not (_inside(years, match["region"]) or _inside(years, match.get("employer"))):
            return {"class": "YEARS_OUTSIDE_ITS_LINE", "unit": match["key"]}
    return {"class": "EXACT_UNIT", "form": match["form"], "unit": match["key"], "line_of": match.get("line_of")}


# ---------------------------------------------------------------------------------------------- relations


class Captures:
    def __init__(self) -> None:
        self.texts: dict[str, tuple[str | None, str | None]] = {}
        self.structure: dict[tuple[str, bool], dict[str, Any] | None] = {}

    def text(self, row: dict[str, Any]) -> str | None:
        path = str(row.get("raw_file") or "")
        if path not in self.texts:
            try:
                data = Path(path).read_bytes()
                page = next(iter((json.loads(data).get("query") or {}).get("pages", {}).values()))
                self.texts[path] = (hashlib.sha256(data).hexdigest(), page["revisions"][0]["slots"]["main"]["*"])
            except (OSError, ValueError, KeyError, IndexError, StopIteration, AttributeError, TypeError):
                self.texts[path] = (None, None)
        digest, text = self.texts[path]
        return text if digest == row.get("raw_file_sha256") else None

    def classify(self, row: dict[str, Any], version: str) -> dict[str, Any]:
        text = self.text(row)
        path = str(row.get("raw_file") or "")
        for literal in (False, True):
            if literal and version == "v37.5":
                break
            key = (path, literal)
            if key not in self.structure:
                self.structure[key] = units(text, literal=literal) if text is not None else None
            verdict = classify(row, self.structure[key])
            if verdict["class"] == "EXACT_UNIT":
                if literal:
                    verdict["class"] = "EXACT_UNIT_UNDER_THE_LITERAL_READING"
                return verdict
            if literal or version == "v37.5":
                return verdict
            first = verdict
        return first


def _load(path: Path, table: str, extra: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        present = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        columns = [c for c in COLUMNS + extra if c in present]
        return {r["episode_id"]: dict(r) for r in conn.execute(f"SELECT {','.join(columns)} FROM {table}")}
    finally:
        conn.close()


def _dispositions(path: Path, sql: str) -> dict[str, tuple[str, list[str]]]:
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        return {str(r[0]): (str(r[1]), json.loads(r[2] or "[]")) for r in conn.execute(sql)}
    finally:
        conn.close()


_VALID = ("EXACT_UNIT", "EXACT_UNIT_UNDER_THE_LITERAL_READING")


def relation(name: str, children: dict[str, dict[str, Any]], parents: dict[str, dict[str, Any]], key: str,
             verdicts: dict[str, dict[str, Any]], dispositions: dict[str, tuple[str, list[str]]]) -> dict[str, Any]:
    counts: collections.Counter = collections.Counter()
    examples: dict[str, list[Any]] = collections.defaultdict(list)
    for cid, child in children.items():
        for pid in json.loads(child.get(key) or "[]"):
            parent = parents.get(pid)
            if parent is None:
                verdict = "PARENT_ABSENT"
            else:
                c, p = verdicts[cid], verdicts[pid]
                if c["class"] not in _VALID + ("NO_WITNESS",) or p["class"] not in _VALID + ("NO_WITNESS",):
                    verdict = "CROSSED_WITNESS_IS_NOT_ITS_SOURCE_FIELD"
                elif c["class"] == "NO_WITNESS" or p["class"] == "NO_WITNESS":
                    verdict = ("UNRESOLVED_NO_WITNESS_ON_EITHER_SIDE" if c["class"] == p["class"]
                               else "UNRESOLVED_NO_WITNESS_ON_ONE_SIDE")
                elif c["unit"] == p["unit"]:
                    verdict = "SAME_SOURCE_FIELD"
                elif c.get("line_of") == p["unit"]:
                    verdict = "SAME_SOURCE_FIELD_ROLE_LINE_OF_ITS_LINE"
                else:
                    verdict = "CROSSED_ANOTHER_SOURCE_FIELD"
            counts[verdict] += 1
            if not verdict.startswith("SAME_") and len(examples[verdict]) < 5:
                examples[verdict].append([cid, pid])
    crossed = sum(v for k, v in counts.items() if k.startswith("CROSSED") or k == "PARENT_ABSENT")
    # Interval grain: a same-field edge inside a field of several intervals is not independently adjudicated here.
    entries: dict[tuple[Any, ...], int] = collections.Counter(
        (r["pageid"], r["revision"], r["family"], r["row_index"]) for r in parents.values())
    multi = sum(1 for cid, child in children.items() for pid in json.loads(child.get(key) or "[]")
                if pid in parents and entries[(parents[pid]["pageid"], parents[pid]["revision"], parents[pid]["family"],
                                              parents[pid]["row_index"])] > 1)
    restructured = sum(1 for state, _ in dispositions.values() if state == "RESTRUCTURED_INTERVALS")
    return {"relation": name, "edges": sum(counts.values()), "counts": dict(counts), "crossed_edges": crossed,
            "examples": dict(examples),
            "edges_into_multi_interval_fields_not_interval_adjudicated": multi,
            "restructured_dispositions": restructured}


def oracle(successor: Path, a04: Path, database: Path, captures: Captures | None = None) -> dict[str, Any]:
    captures = captures or Captures()
    default = _load(database, "career_episode_successor", ())
    older = _load(a04, "career_episode_a04", ("predecessor_episode_ids",))
    children = _load(successor, "career_episode_a05", ("predecessor_episode_ids", "a04_episode_ids"))
    verdicts: dict[str, dict[str, Any]] = {}
    for rows, version in ((default, "v37.2"), (older, "v37.4"), (children, "v37.5")):
        for identity, row in rows.items():
            verdicts[identity] = captures.classify(row, version)
    classes = {name: dict(collections.Counter(verdicts[i]["class"] for i in rows))
               for name, rows in (("default", default), ("A04", older), ("A05", children))}
    forms = {name: dict(collections.Counter(verdicts[i].get("form") for i in rows if verdicts[i].get("form")))
             for name, rows in (("default", default), ("A04", older), ("A05", children))}
    invalid = {name: sorted(i for i in rows if verdicts[i]["class"] not in _VALID + ("NO_WITNESS",))[:10]
               for name, rows in (("default", default), ("A04", older), ("A05", children))}
    relations = [
        relation("A5<-default", children, default, "predecessor_episode_ids", verdicts,
                 _dispositions(successor, "SELECT predecessor_episode_id, disposition, successor_episode_ids "
                                          "FROM career_a05_disposition")),
        relation("A5<-A4", children, older, "a04_episode_ids", verdicts,
                 _dispositions(successor, "SELECT a04_episode_id, disposition, a05_episode_ids FROM career_a05_from_a04")),
        relation("A4<-default", older, default, "predecessor_episode_ids", verdicts,
                 _dispositions(a04, "SELECT predecessor_episode_id, disposition, successor_episode_ids "
                                    "FROM career_a04_disposition")),
    ]
    triangle = []
    for cid, child in children.items():
        through: set[str] = set()
        for aid in json.loads(child.get("a04_episode_ids") or "[]"):
            through.update(json.loads((older.get(aid) or {}).get("predecessor_episode_ids") or "[]"))
        if through != set(json.loads(child.get("predecessor_episode_ids") or "[]")):
            triangle.append(cid)
    return {"oracle_version": ORACLE_VERSION, "successor": str(successor), "successor_sha256": sha256_file(successor),
            "a04": str(a04), "a04_sha256": sha256_file(a04), "database": str(database),
            "rows": {"default": len(default), "A04": len(older), "A05": len(children)},
            "captures_read": len(captures.texts),
            "captures_unreadable_or_changed": sum(1 for d, t in captures.texts.values() if t is None),
            "witness_classes": classes, "unit_forms": forms, "invalid_witness_examples": invalid,
            "relations": relations, "crossed_edges": sum(r["crossed_edges"] for r in relations),
            "triangle_mismatches": len(triangle), "triangle_examples": triangle[:5],
            "unresolved": {r["relation"]: {k: v for k, v in r["counts"].items() if k.startswith("UNRESOLVED")}
                           for r in relations}}


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
    print(json.dumps({k: result[k] for k in ("rows", "witness_classes", "crossed_edges", "triangle_mismatches",
                                             "unresolved")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
