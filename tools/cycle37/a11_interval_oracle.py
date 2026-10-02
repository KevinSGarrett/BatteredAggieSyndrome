r"""Cycle #37 — Attempt #11 — an independent source-cardinality oracle for career successors (MF37A10-01).

    a11_interval_oracle.py --successor SUCCESSOR.sqlite --a04 A04.sqlite --database DEFAULT.sqlite --out RESULT.json
                           [--label NAME] [--known-anomalies MANAGER_CENSUS.json]

The Attempt 10 oracle shared the consumer's exemption: it judged only entries holding two or more rows, and it counted
any all-to-all restructure as proven -- so the manager's count-changing collapse (Walter Camp's ``coachyears2 = 1892,
1894–1895`` left as one row claiming both parents) passed it with no invalid edge. This oracle starts from the source,
never from a restructure marker or a graph shape. It imports no project module and shares no code with the parser, the
verifier or ``career_interval``; it uses only the Attempt 8 oracle's raw-structure reader (fields, list lines and role
lines of a revision; ``a08_source_field_oracle``) and, on its own:

* **reads every field's periods from the raw revision** -- a numbered field's ``*_years`` value; for a list, nested or
  role line every top-level parenthetical of the line (link and template contents masked) that displays a year, in
  order (Cedric Scott's ``({{NFL Year|2002}}); ({{NFL Year|2004}})`` is two periods), else its employer line's --
  rendering season templates, splitting on top-level commas, semicolons and ``and`` and between complete periods
  written side by side;
* **judges every field the successor holds, single or multiple** (``cardinality``): the field must hold exactly as
  many rows as the source states periods (a field stating none is one row), with ordinals ``0..n-1``; each row's stated
  text (unless blank) must state the years of the period at its ordinal, in order, and its stated start and end must
  be that period's plain years (how a circa, a season template's ``present`` or a footnote mark is written is the
  parser's rendering, not this oracle's question).
  A count or ordinal the source does not state, a year the unit never states or a year of another period of the same
  field is ``INVALID``; the only other outcomes are named source classes, never a pass:
  ``KNOWN_PARSER_ANOMALY_EMPTY_TEMPLATE_ARGUMENT`` (a season template with an empty argument before ``–present``, split
  into a dateless second row), ``UNRESOLVED_MALFORMED_SYNTAX`` (a doubled dash or a slash year, left to a person),
  ``UNRESOLVED_READING_DIFFERS`` / ``UNRESOLVED_PERIOD_NOT_READ_BY_THIS_ORACLE`` (the stated years are the unit's, but
  this oracle's simple reading of a circa, a season template or unbalanced markup renders them otherwise -- the
  Attempt 4 file's documented first-year reading of two-year season templates among them), and, for the Attempt 4
  format, ``V374_LAST_PARENTHETICAL_ONLY`` (the v37.4 line rule);
* **judges every restructure claim against the source** (``restructure``): every parent of the re-read field is
  restructured and names one target set that is exactly the child field, the child field's count is the source's (or
  a named anomaly), and the parent field's count differs -- ``PROVEN_REREAD``; a partial, count-preserving or
  source-contradicting claim is ``INVALID``;
* **judges every ``NOT_PRODUCED`` claim and every cited capture's completeness**: a parent claimed not produced must
  name no field the successor-version splitting states a period in, and (Attempt 5 format) every field unit of a cited
  capture that states a period must be held.

Unrestructured edges inside one field keep the Attempt 10 rule (equal identity ordinals, equal counts). The classes
are raw-source readings, not biography truth: a PROVEN field is read faithfully, not verified as a fact.
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

ORACLE_VERSION = "BAS-C37A11-SOURCE-CARDINALITY-ORACLE-v1"
RESTRUCTURED, NOT_PRODUCED = "RESTRUCTURED_INTERVALS", "NOT_PRODUCED_BY_THE_SUCCESSOR_PARSER"
_IDENTITY = re.compile(r"^[A-Za-z0-9-]+:(\d+):(\d+):(COACHING|PLAYING|ADMINISTRATIVE):(\d+):(\d+)$")
_LITERAL = {"v37.2": True, "v37.4": True, "v37.5": False}
_YEAR = re.compile(r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)")
_DASHES = "‐‑‒–—−-"
_DASH = re.compile(r"\s*(?:[" + _DASHES + r"]|&ndash;|&mdash;)\s*")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_BREAK = re.compile(r"<br\s*/?\s*>", re.I)
_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_TEMPLATE = re.compile(r"\{\{([^{}]*)\}\}")
_SEPARATOR = re.compile(r"\s*(?:[,;]|\band\b|\n)\s*", re.I)
_SIDE_BY_SIDE = re.compile(r"(\d{4}|present|current|\?)\s+(?=(?:1[89]\d\d|20\d\d))", re.I)
_LIST_TEMPLATE = re.compile(r"^\s*\{\{\s*(?:ubl|unbulleted\s+list|plainlist|flatlist|nowrap)\s*\|(.*)\}\}\s*$",
                            re.I | re.S)
_EMPTY_ARGUMENT_PRESENT = re.compile(r"\|\s*\}\}\s*(?:[" + _DASHES + r"]|&ndash;)\s*present", re.I)
#: Templates that display their content (kept); every other non-season template -- notes, citations -- is dropped.
_DISPLAY = {"nowrap", "nobr", "small", "smaller", "big", "abbr", "tooltip"}
_COLUMNS = ("start", "end", "disposition", "predecessor_episode_ids", "a04_episode_ids", "a04_disposition",
            "person_display", "lineage_state")


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _render_template(match: re.Match[str]) -> str:
    parts = [p.strip() for p in match.group(1).split("|")]
    name = parts[0].lower()
    if name in ("circa", "c.", "ca", "ca.", "approx", "approx."):
        # {{circa|1900}} displays "c. 1900" (and {{circa}} alone "c.")
        positional = [p for p in parts[1:] if "=" not in p]
        return f"c. {positional[0]}" if positional and positional[0] else "c."
    if name in ("endash", "ndash", "snd", "spaced ndash", "spaced en dash"):
        return "–"
    years = [p for p in parts[1:] if _YEAR.fullmatch(p)]
    if years:
        return "–".join(years[:2])
    positional = [p for p in parts[1:] if "=" not in p]
    return positional[0] if positional and parts[0].strip().lower() in _DISPLAY else ""


def render(raw: str) -> str:
    """The displayed text of a wikitext fragment; a line break becomes a line boundary."""

    text = _REF.sub("", _COMMENT.sub("", raw))
    for _ in range(4):
        text = _TEMPLATE.sub(_render_template, text)
    text = _LINK.sub(lambda m: m.group(1), text)
    text = _TAG.sub(" ", _BREAK.sub("\n", html.unescape(text)))
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n"))


def periods(raw: str | None) -> list[str] | None:
    """This oracle's own periods of a years text, chronologically; None when it states none."""

    if raw is None:
        return None
    out: list[str] = []
    for piece in (p.strip(" ()") for p in _SEPARATOR.split(render(raw))):
        if not (_YEAR.search(piece) or "?" in piece):
            continue
        for part in _SIDE_BY_SIDE.sub(lambda m: m.group(1) + "\x00", piece).split("\x00"):
            if _YEAR.search(part) or "?" in part:
                out.append(part.strip())
    if not out:
        return None
    return sorted(out, key=lambda p: (_YEAR.search(p) is None, int(_YEAR.search(p).group(1)) if _YEAR.search(p) else 0))


def malformed(raw: str | None) -> bool:
    text = render(raw or "")
    return bool(re.search(r"[" + _DASHES + r"]\s*[" + _DASHES + r"]|\d/\d", text))


def plain_years(period: str) -> tuple[int | None, int | None] | None:
    """(start, end) of a period written as plain years (``1892``, ``1894–1895``, ``1946–51``, ``2009–present``,
    ``2009–?``); None when the period is not plain (circa, decades, questioned years)."""

    text = _DASH.sub("–", period.strip())
    match = re.fullmatch(r"(1[89]\d\d|20\d\d)", text)
    if match:
        return int(match.group(1)), int(match.group(1))
    match = re.fullmatch(r"(1[89]\d\d|20\d\d)–(1[89]\d\d|20\d\d|\d\d|present|current|\?)", text, re.I)
    if not match:
        return None
    start, end = int(match.group(1)), match.group(2)
    if end.isdigit():
        value = int(end) if len(end) == 4 else (start // 100) * 100 + int(end)
        if value < start:
            value += 100 if len(end) == 2 else 0
        return start, value
    return start, None


def normal(text: Any) -> str:
    return _DASH.sub("–", re.sub(r"\s+", "", str(text or ""))).casefold()


def years_of(text: Any) -> list[int]:
    """The four-digit years a text states, in order."""

    return [int(y) for y in _YEAR.findall(str(text or ""))]


def _unwrap(line: str) -> str:
    match = _LIST_TEMPLATE.match(line)
    return match.group(1) if match else line


def line_periods_text(line: str) -> str | None:
    """Every top-level parenthetical of a line that displays a year, in order, joined as one years text; link and
    template contents are masked so a link title's ``(2022)`` or a role list's items are not the line's periods."""

    line = _unwrap(line)
    masked = _REF.sub(lambda m: " " * len(m.group(0)), _COMMENT.sub(lambda m: " " * len(m.group(0)), line))
    for _ in range(4):
        masked = _TEMPLATE.sub(lambda m: "x" * len(m.group(0)), masked)
    masked = re.sub(r"\[\[[^\]]*\]\]", lambda m: "x" * len(m.group(0)), masked)
    found = [line[m.start(1):m.end(1)] for m in re.finditer(r"\(([^()]*)\)", masked)
             if _YEAR.search(render(line[m.start(1):m.end(1)]))]
    return ", ".join(found) if found else None


def last_parenthetical_text(line: str) -> str | None:
    found = None
    shown = _LINK.sub(lambda m: m.group(1), _REF.sub("", _COMMENT.sub("", _unwrap(line))))
    for paren in re.finditer(r"\(([^()]*)\)", shown):
        if _YEAR.search(render(paren.group(1))):
            found = paren.group(1)
    return found


def _head(line: str) -> str:
    return _BREAK.split(line, maxsplit=1)[0]


class Reader:
    def __init__(self) -> None:
        self.captures = structure.Captures()

    def units(self, row: dict[str, Any], version: str) -> dict[tuple[str, int], list[dict[str, Any]]] | None:
        text = self.captures.text(row)
        if text is None:
            return None
        key = (str(row.get("raw_file") or ""), _LITERAL[version])
        if key not in self.captures.structure:
            self.captures.structure[key] = structure.units(text, literal=_LITERAL[version])
        return (self.captures.structure[key] or {}).get("named", {})

    def field_years(self, row: dict[str, Any], version: str, *, last_only: bool = False) -> tuple[str, str | None]:
        """``(state, years text)`` of the field the row's identity names in its verified revision."""

        match = _IDENTITY.match(str(row.get("episode_id")))
        own = (str(row.get("pageid")), str(row.get("revision")), str(row.get("family")), str(row.get("row_index")),
               str(row.get("interval_index")))
        if match is None or tuple(match.groups()) != own:
            return "INVALID_IDENTITY_NOT_THE_ROW", None
        named = self.units(row, version)
        if named is None:
            return "UNRESOLVED_NO_CAPTURE", None
        found = named.get((str(row.get("family")), int(row.get("row_index"))), [])
        if not found:
            return "NO_UNIT", None
        if len(found) > 1:
            return "UNRESOLVED_AMBIGUOUS_UNIT", None
        return "UNIT", self.unit_years(self.captures.text(row), found[0], last_only=last_only)

    def unit_universe(self, row: dict[str, Any], version: str) -> set[int]:
        """Every four-digit year the raw text of the row's unit states anywhere (a field's years value; a line's whole
        text and its employer line's): a year outside it is a year the source never states for this job."""

        named = self.units(row, version) or {}
        found = named.get((str(row.get("family")), int(row.get("row_index"))), [])
        text = self.captures.text(row)
        if len(found) != 1 or text is None:
            return set()
        unit = found[0]
        spans = [unit.get("years")] if unit["form"] == "FIELD" else [unit.get("region"), unit.get("employer")]
        return {int(y) for span in spans if span for y in _YEAR.findall(text[span[0]:span[1]])}

    @staticmethod
    def unit_years(text: str, unit: dict[str, Any], *, last_only: bool = False) -> str | None:
        if unit["form"] == "FIELD":
            years = unit.get("years")
            return text[years[0]:years[1]] if years else None
        reader = last_parenthetical_text if last_only else line_periods_text
        line = text[unit["region"][0]:unit["region"][1]]
        own = reader(_head(line) if unit["form"] == "LIST_LINE" else line)
        if own is None and unit.get("employer") is not None:
            own = reader(_head(text[unit["employer"][0]:unit["employer"][1]]))
        return own


def _entries(rows: dict[str, dict[str, Any]]) -> dict[tuple[str, ...], list[str]]:
    out: dict[tuple[str, ...], list[str]] = collections.defaultdict(list)
    for identity, row in rows.items():
        out[(str(row["pageid"]), str(row["revision"]), str(row["family"]), str(row["row_index"]))].append(identity)
    return out


def judge_field(reader: Reader, rows: dict[str, dict[str, Any]], identities: list[str], version: str,
                fmt: str) -> dict[str, Any]:
    """One field of the successor: its rows against the periods the source states."""

    ordered = sorted(identities, key=lambda i: int(rows[i]["interval_index"]))
    first = rows[ordered[0]]
    state, years = reader.field_years(first, version)
    record: dict[str, Any] = {"rows": ordered, "years_text": years}
    if state != "UNIT":
        record["class"] = "INVALID_ROW_NAMES_NO_SOURCE_FIELD" if state in ("NO_UNIT",
                                                                         "INVALID_IDENTITY_NOT_THE_ROW") else state
        return record
    found = periods(years)
    record["periods"] = found
    expected = max(len(found or []), 1)
    ordinals = sorted(int(rows[i]["interval_index"]) for i in ordered)
    stated = [(rows[i].get("years_as_written"), rows[i].get("start"), rows[i].get("end")) for i in ordered]
    record["stated"] = stated
    if ordinals != list(range(len(ordered))) and len(ordered) == expected:
        record["class"] = "INVALID_ORDINAL_NOT_STATED"
        return record
    if len(ordered) != expected or ordinals != list(range(len(ordered))):
        if years and malformed(years):
            record["class"] = "UNRESOLVED_MALFORMED_SYNTAX"
        elif (years and _EMPTY_ARGUMENT_PRESENT.search(years) and len(found or []) == 1 and len(ordered) == 2
              and stated[1][1] is None and stated[1][2] is None and ordinals == [0, 1]):
            record["class"] = "KNOWN_PARSER_ANOMALY_EMPTY_TEMPLATE_ARGUMENT"
        elif fmt == "A04" and len(ordered) == 1:
            state_last, last = reader.field_years(first, version, last_only=True)
            record["class"] = ("V374_LAST_PARENTHETICAL_ONLY" if state_last == "UNIT"
                               and len(periods(last) or []) == 1 else "INVALID_CARDINALITY")
        else:
            record["class"] = "INVALID_CARDINALITY"
        record["held"], record["source_states"] = len(ordered), expected
        return record
    def stated_years(period: str | None) -> set[int]:
        """A period's four-digit years and its plain endpoints (``2003–06`` states 2006)."""

        plain = plain_years(period) if period else None
        return set(years_of(period)) | {y for y in (plain or ()) if isinstance(y, int)}

    universe = reader.unit_universe(first, version) | {y for p in (found or []) for y in stated_years(p)}
    problems, unresolved = [], []
    for ordinal, identity in enumerate(ordered):
        text, start, end = stated[ordinal]
        period = (found or [None])[ordinal] if found else None
        own = years_of(period)
        others = {y for j, p in enumerate(found or []) if j != ordinal for y in stated_years(p)} - stated_years(period)
        # What a row states against the period at its ordinal: a year the unit never states is fabricated; a year of
        # another period of the same field is a crossed, copied or enlarged period; anything else that differs is how
        # the parser rendered the unit (a circa, a season template, unbalanced markup) -- a reading to adjudicate.
        claimed = years_of(text) if not _blank(text) else []
        claimed += [value for value in (start, end) if isinstance(value, int)]
        if [y for y in claimed if y not in universe and y not in own]:
            problems.append((identity, "YEAR_NOT_IN_SOURCE", text, start, end, period))
        elif [y for y in claimed if y in others]:
            problems.append((identity, "ANOTHER_PERIODS_YEAR", text, start, end, period))
        elif not _blank(text) and years_of(text) != own:
            unresolved.append((identity, "TEXT_READS_DIFFERENTLY", text, period))
        else:
            plain = plain_years(period) if period else None
            if plain is not None and ((start is not None and start != plain[0])
                                      or (end is not None and plain[1] is not None and end != plain[1])):
                unresolved.append((identity, "DATES_READ_DIFFERENTLY", start, end, period))
    if problems:
        record["class"] = "INVALID_PERIOD_NOT_THE_SOURCES"
        record["problems"] = problems
    elif unresolved:
        record["class"] = ("UNRESOLVED_PERIOD_NOT_READ_BY_THIS_ORACLE" if not found
                           else "UNRESOLVED_READING_DIFFERS")
        record["problems"] = unresolved
    else:
        record["class"] = "PROVEN_TEXT_ABSENT" if all(_blank(s[0]) for s in stated) else "PROVEN"
    return record


def _load(path: Path, table: str) -> dict[str, dict[str, Any]]:
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        present = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        columns = [c for c in dict.fromkeys(structure.COLUMNS + _COLUMNS) if c in present]
        quoted = ",".join(f'"{c}"' for c in columns)
        return {r["episode_id"]: dict(r) for r in conn.execute(f"SELECT {quoted} FROM {table}")}
    finally:
        conn.close()


def _dispositions(path: Path, table: str, key: str, targets: str) -> dict[str, tuple[str, list[str]]]:
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        return {str(r[0]): (str(r[1]), json.loads(r[2] or "[]"))
                for r in conn.execute(f"SELECT {key}, disposition, {targets} FROM {table}")}
    finally:
        conn.close()


def judge_relation(name: str, children: dict[str, dict[str, Any]], parents: dict[str, dict[str, Any]], key: str,
                   dispositions: dict[str, tuple[str, list[str]]], fields: dict[tuple[str, ...], dict[str, Any]],
                   reader: Reader, version: str) -> dict[str, Any]:
    child_entries, parent_entries = _entries(children), _entries(parents)
    entry_of = {i: e for e, ids in child_entries.items() for i in ids}
    parent_entry_of = {i: e for e, ids in parent_entries.items() for i in ids}
    counts: collections.Counter = collections.Counter()
    examples: dict[str, list[Any]] = collections.defaultdict(list)
    claims: list[dict[str, Any]] = []

    def note(verdict: str, sample: Any) -> None:
        counts[verdict] += 1
        if not verdict.startswith("PROVEN") and len(examples[verdict]) < 8:
            examples[verdict].append(sample)

    # Restructure claims, judged against the source (never against the graph alone).
    for entry, ids in parent_entries.items():
        states = [dispositions.get(i) for i in ids]
        if not any(s and s[0] == RESTRUCTURED for s in states):
            continue
        targets = {tuple(sorted(s[1])) for s in states if s}
        named = list(next(iter(targets))) if len(targets) == 1 else []
        child_fields = {entry_of.get(t) for t in named}
        whole = sorted(i for e in child_fields if e for i in child_entries.get(e, []))
        field = fields.get(next(iter(child_fields))) if len(child_fields) == 1 else None
        klass = (field or {}).get("class", "")
        if not all(s and s[0] == RESTRUCTURED for s in states) or len(targets) != 1:
            verdict = "INVALID_RESTRUCTURE_NOT_ONE_CLAIM"
        elif len(child_fields) != 1 or sorted(named) != whole:
            verdict = "INVALID_RESTRUCTURE_NOT_THE_WHOLE_FIELD"
        elif len(named) == len(ids):
            verdict = "INVALID_RESTRUCTURE_COUNT_UNCHANGED"
        elif klass.startswith("PROVEN"):
            verdict = "PROVEN_REREAD"
        elif klass.startswith(("KNOWN_PARSER_ANOMALY", "UNRESOLVED_MALFORMED", "V374")):
            verdict = "REREAD_OF_A_NAMED_PARSER_ANOMALY"
        elif klass.startswith("UNRESOLVED"):
            verdict = "UNRESOLVED_REREAD_OF_A_FIELD_READ_DIFFERENTLY"
        else:
            verdict = "INVALID_RESTRUCTURE_CHILD_FIELD_NOT_THE_SOURCES"
        note(verdict, {"parents": ids, "targets": named})
        claims.append({"parent_field": list(entry), "parents": len(ids), "children": len(named), "verdict": verdict,
                       "child_field_class": klass})
    restructured = {tuple(c["parent_field"]) for c in claims}
    # Unrestructured edges inside one field: equal identity ordinals, equal counts (the Attempt 10 rule, kept).
    for cid, child in children.items():
        for pid in json.loads(child.get(key) or "[]"):
            if pid not in parents:
                note("INVALID_PARENT_ABSENT", [cid, pid])
                continue
            entry = parent_entry_of[pid]
            if entry in restructured or entry != entry_of[cid]:
                continue
            if len(parent_entries[entry]) < 2 and len(child_entries[entry]) < 2:
                continue
            if int(child["interval_index"]) != int(parents[pid]["interval_index"]):
                note("INVALID_CROSSED_INTERVAL", [cid, pid])
            elif len(parent_entries[entry]) != len(child_entries[entry]):
                note("INVALID_COUNT_CHANGED_WITHOUT_RESTRUCTURE", [cid, pid])
            else:
                note("PROVEN_SAME_INTERVAL", [cid, pid])
    # NOT_PRODUCED claims: the parent's field states no period in the successor's splitting.
    not_produced = [pid for pid, (state, _targets) in dispositions.items() if state == NOT_PRODUCED and pid in parents]
    for pid in not_produced:
        parent = parents[pid]
        named = reader.units(parent, version)
        unit = (named or {}).get((str(parent.get("family")), int(parent.get("row_index"))), [])
        text = reader.captures.text(parent)
        years = reader.unit_years(text, unit[0]) if len(unit) == 1 and text else None
        verdict = ("PROVEN_NOT_PRODUCED_NO_FIELD" if not unit else
                   "INVALID_NOT_PRODUCED_FIELD_STATES_A_PERIOD" if periods(years) else "PROVEN_NOT_PRODUCED_NO_PERIOD")
        note(verdict, pid)
    return {"relation": name, "counts": dict(counts), "examples": dict(examples),
            "proven": sum(v for k, v in counts.items() if k.startswith("PROVEN")),
            "named_anomalies": sum(v for k, v in counts.items() if k.startswith("REREAD_OF")),
            "unresolved": sum(v for k, v in counts.items() if k.startswith("UNRESOLVED")),
            "invalid": sum(v for k, v in counts.items() if k.startswith("INVALID")),
            "restructure_claims": claims, "not_produced_claims": len(not_produced)}


def completeness(reader: Reader, children: dict[str, dict[str, Any]], citing: list[dict[str, Any]],
                 version: str) -> dict[str, Any]:
    """Every field unit of a cited capture that states a period is held by the successor."""

    held = set(_entries(children))
    pages: dict[tuple[str, str], dict[str, Any]] = {}
    for row in citing:
        pages.setdefault((str(row["pageid"]), str(row["revision"])), row)
    omitted, fields = [], 0
    for (pageid, revision), row in pages.items():
        text = reader.captures.text(row)
        named = reader.units(row, version) or {}
        for (family, index), units in named.items():
            # Role lines become rows only where the parser splits a line's roles; their completeness is the
            # consumer's (v37.5's own production). A field, list line or nested line stating a period must be held.
            if len(units) != 1 or text is None or units[0]["form"] == "ROLE_LINE":
                continue
            fields += 1
            if (pageid, revision, str(family), str(index)) not in held and periods(reader.unit_years(text, units[0])):
                omitted.append(f"{pageid}:{revision}:{family}:{index}")
    return {"captures": len(pages), "field_units": fields, "units_stating_a_period_not_held": len(omitted),
            "examples": omitted[:10]}


def missing_periods(reader: Reader, rows: dict[str, dict[str, Any]], version: str) -> dict[str, Any]:
    counts: collections.Counter = collections.Counter()
    examples: dict[str, list[str]] = collections.defaultdict(list)
    for identity, row in rows.items():
        if not _blank(row.get("years_as_written")):
            continue
        state, years = reader.field_years(row, version)
        verdict = state if state != "UNIT" else ("NO_PERIOD_IN_SOURCE" if periods(years) is None
                                                  else "BLANK_WHERE_SOURCE_STATES_A_PERIOD")
        counts[verdict] += 1
        if verdict != "NO_PERIOD_IN_SOURCE" and len(examples[verdict]) < 8:
            examples[verdict].append(identity)
    return {"rows_stating_no_interval_text": sum(counts.values()), "counts": dict(counts), "examples": dict(examples)}


def oracle(successor: Path, a04: Path, database: Path, known: Path | None = None) -> dict[str, Any]:
    reader = Reader()
    default = _load(database, "career_episode_successor")
    conn = sqlite3.connect(Path(successor).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    fmt = "A05" if "career_episode_a05" in tables else "A04"
    version = "v37.5" if fmt == "A05" else "v37.4"
    children = _load(successor, "career_episode_a05" if fmt == "A05" else "career_episode_a04")
    fields = {entry: judge_field(reader, children, ids, version, fmt) for entry, ids in _entries(children).items()}
    classes = collections.Counter(f["class"] for f in fields.values())
    relations = []
    older: dict[str, dict[str, Any]] = {}
    if fmt == "A05":
        older = _load(a04, "career_episode_a04")
        relations.append(judge_relation("A5<-default", children, default, "predecessor_episode_ids",
                                        _dispositions(successor, "career_a05_disposition", "predecessor_episode_id",
                                                      "successor_episode_ids"), fields, reader, version))
        relations.append(judge_relation("A5<-A4", children, older, "a04_episode_ids",
                                        _dispositions(successor, "career_a05_from_a04", "a04_episode_id",
                                                      "a05_episode_ids"), fields, reader, version))
        complete = completeness(reader, children, list(children.values()) + list(default.values()), version)
    else:
        relations.append(judge_relation("A4<-default", children, default, "predecessor_episode_ids",
                                        _dispositions(successor, "career_a04_disposition", "predecessor_episode_id",
                                                      "successor_episode_ids"), fields, reader, version))
        complete = {"not_asserted": "the Attempt 4 format's field completeness is not judged (as in the consumer)"}
    anomalies = sorted([list(e) for e, f in fields.items()
                        if f["class"].startswith(("KNOWN_PARSER_ANOMALY", "UNRESOLVED_MALFORMED", "V374"))])
    multi = []

    def parent_rows(rows: list[str], relation: str) -> list[dict[str, Any]]:
        column, population = (("predecessor_episode_ids", default) if relation == "default"
                              else ("a04_episode_ids", older))
        named = sorted({p for i in rows for p in json.loads(children[i].get(column) or "[]")})
        return [{"id": p, "years_as_written": population.get(p, {}).get("years_as_written")} for p in named]

    for entry, field in sorted(fields.items()):
        if len(field["rows"]) < 2 and len(field.get("periods") or []) < 2:
            continue
        rows = field["rows"]
        multi.append({"entry": list(entry), "person": children[rows[0]].get("person_display"),
                      "years_text": field.get("years_text"), "periods": field.get("periods"), "class": field["class"],
                      "rows": [{"id": i, "years_as_written": children[i].get("years_as_written"),
                                "start": children[i].get("start"), "end": children[i].get("end"),
                                "disposition": children[i].get("disposition"),
                                "default_parents": json.loads(children[i].get("predecessor_episode_ids") or "[]"),
                                "a04_parents": json.loads(children[i].get("a04_episode_ids") or "[]"),
                                "a04_disposition": children[i].get("a04_disposition")} for i in rows],
                      "parents": {relation: parent_rows(rows, relation)
                                  for relation in (("default", "A4") if fmt == "A05" else ("default",))}})
    known_comparison = None
    if known is not None and Path(known).is_file():
        census = json.loads(Path(known).read_text(encoding="utf-8"))
        manager = sorted([list(map(str, r["entry"])) for r in census.get("records") or []
                          if r.get("state") != "PROVEN_INTERVALS"])
        mine = sorted(anomalies)
        known_comparison = {"path": str(known), "sha256": structure.sha256_file(known), "manager_non_proven": manager,
                            "oracle_named_anomalies": mine, "equal": manager == mine}
    invalid_fields = sum(v for k, v in classes.items() if k.startswith("INVALID"))
    invalid_relations = sum(r["invalid"] for r in relations)
    omitted = complete.get("units_stating_a_period_not_held", 0) if isinstance(complete, dict) else 0
    return {"oracle_version": ORACLE_VERSION, "format": fmt, "parser_splitting": version,
            "successor": str(successor), "successor_sha256": structure.sha256_file(successor), "a04": str(a04),
            "a04_sha256": structure.sha256_file(a04), "database": str(database),
            "database_sha256": structure.sha256_file(database),
            "rows": {"successor": len(children), "default": len(default)}, "fields": len(fields),
            "captures_read": len(reader.captures.texts), "field_classes": dict(classes),
            "invalid_fields": invalid_fields,
            "unresolved_fields": sum(v for k, v in classes.items() if k.startswith("UNRESOLVED")),
            "unresolved_field_examples": sorted([{"entry": list(e), **{k: f.get(k) for k in
                                                                       ("class", "rows", "years_text", "periods",
                                                                        "problems")}}
                                                 for e, f in fields.items() if f["class"].startswith("UNRESOLVED")],
                                                key=lambda r: r["entry"])[:40],
            "invalid_field_examples": sorted([{"entry": list(e), **{k: f.get(k) for k in
                                                                    ("class", "rows", "years_text", "periods",
                                                                     "held", "source_states", "problems")}}
                                              for e, f in fields.items() if f["class"].startswith("INVALID")],
                                             key=lambda r: r["entry"])[:20],
            "named_anomalies": anomalies, "known_anomaly_comparison": known_comparison,
            "multi_interval_fields": len(multi), "rows_in_multi_interval_fields": sum(len(g["rows"]) for g in multi),
            "multi_interval_groups": multi, "relations": relations, "invalid_relation_verdicts": invalid_relations,
            "completeness": complete, "missing_periods": missing_periods(reader, children, version),
            "invalid_total": invalid_fields + invalid_relations + omitted,
            "limits": ("A raw-source reading of every field's periods and every lineage claim about them, by this "
                       "oracle's own rules; named anomaly and malformed classes are left to a person, never passed; "
                       "PROVEN means read faithfully, not a verified biography fact; the delivered v37.2 readings are "
                       "judged only as parents")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--successor", type=Path, required=True)
    parser.add_argument("--a04", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", default="")
    parser.add_argument("--known-anomalies", type=Path, default=None)
    args = parser.parse_args(argv)
    result = oracle(args.successor, args.a04, args.database, args.known_anomalies)
    result["label"] = args.label
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({k: result[k] for k in ("format", "fields", "field_classes", "invalid_fields",
                                             "multi_interval_fields", "rows_in_multi_interval_fields",
                                             "named_anomalies", "invalid_relation_verdicts", "invalid_total")}
                     | {"relations": [{k: r[k] for k in ("relation", "counts", "invalid")} for r in result["relations"]],
                        "completeness": result["completeness"],
                        "known": (result["known_anomaly_comparison"] or {}).get("equal")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
