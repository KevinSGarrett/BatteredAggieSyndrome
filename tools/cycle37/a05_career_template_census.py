r"""Cycle #37 — Attempt #5 — independent census of date templates and nested career dates (TP37-A05-03/06).

    a05_career_template_census.py --out <new directory>

MF37A04-03 was a shared shortcut, not a single bad row: the v37.4 parser *and* the Attempt 4 raw census both
rendered any template whose first argument is a year as that year alone, so ``{{NFL Year|1987|1989}}`` became
1987 in the successor and the census never noticed. This census therefore reads the cached revisions with code
of its own and interprets nothing. For every career field of every infobox (numbered ``*_years``/``*_team``
pairs, their spelled-out variants, and the bulleted ``past*`` lists) it lists:

* every template occurrence, nested ones included, with its normalized name, every positional argument, every
  named argument and its character span -- whether or not a year appears in it;
* for every bulleted list item, its depth, whether it sits under a parent item, the date-bearing text written
  outside its employer link, and whether that text is inside balanced parentheses;
* counts by template name and arity, so each form the successor must read -- and each it must leave unresolved --
  is an enumerated class.

The parser (``aggie_analytics.cycle37.career_infobox``), the successor builder and the Attempt 4 census are not
imported; nothing here decides what a template means.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 5
CENSUS_VERSION = "BAS-C37A05-CAREER-TEMPLATE-CENSUS-v1"
CYCLE30 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
RAW_WIKIMEDIA = CYCLE30 / "raw" / "wikimedia"
CAREER_PAGES = CYCLE30 / "outputs" / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl"
NUMBERED = re.compile(r"^(coaching|coach|playing|player|administrating|admin|executive)_?(years|team)(\d+)$", re.I)
LIST_FIELDS = {"pastcoaching", "pastteams", "pastexecutive", "pastexecutives", "pastadmin"}
YEAR = re.compile(r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def closing(text: str, start: int, opening: str, closing_text: str) -> int:
    """Index after the delimiter closing the one opened at ``start`` (nesting counted); len(text) if unclosed."""

    depth, i = 0, start
    while i < len(text) - 1:
        two = text[i:i + 2]
        if two == opening:
            depth, i = depth + 1, i + 2
        elif two == closing_text:
            depth, i = depth - 1, i + 2
            if depth == 0:
                return i
        else:
            i += 1
    return len(text)


def infoboxes(text: str) -> Iterator[tuple[str, int, int]]:
    for match in re.finditer(r"\{\{\s*Infobox\s+([^|\n}]+)", text, re.I):
        yield match.group(1).strip(), match.end(), closing(text, match.start(), "{{", "}}") - 2


def split_top(text: str, start: int, end: int, separator: str = "|") -> list[tuple[int, int]]:
    """Spans of ``text[start:end]`` split at ``separator`` where no link or template is open."""

    spans, cut, links, templates, i = [], start, 0, 0, start
    while i < end:
        two = text[i:i + 2]
        if two == "[[":
            links, i = links + 1, i + 2
            continue
        if two == "]]" and links:
            links, i = links - 1, i + 2
            continue
        if two == "{{":
            templates, i = templates + 1, i + 2
            continue
        if two == "}}" and templates:
            templates, i = templates - 1, i + 2
            continue
        if text[i] == separator and not links and not templates:
            spans.append((cut, i))
            cut = i + 1
        i += 1
    spans.append((cut, end))
    return spans


def params(text: str, start: int, end: int) -> list[tuple[str, int, int]]:
    """(name, value start, value end) of every top-level infobox parameter."""

    out = []
    for a, b in split_top(text, start, end)[1:]:
        chunk = text[a:b]
        if "=" not in chunk:
            continue
        name, _, value = chunk.partition("=")
        lead = len(value) - len(value.lstrip())
        value_start = a + len(name) + 1 + lead
        out.append((name.strip().lower(), value_start, value_start + len(value.strip())))
    return out


def templates(text: str, start: int, end: int) -> Iterator[dict[str, Any]]:
    """Every template in ``text[start:end]``, outermost first then nested, with its arguments as written."""

    i = start
    while i < end - 1:
        if text[i:i + 2] != "{{":
            i += 1
            continue
        stop = min(closing(text, i, "{{", "}}"), end)
        body_start, body_end = i + 2, max(i + 2, stop - 2)
        parts = split_top(text, body_start, body_end)
        name = re.sub(r"[\s_]+", " ", text[parts[0][0]:parts[0][1]]).strip()
        positional, named = [], {}
        for a, b in parts[1:]:
            chunk = text[a:b]
            key, equals, value = chunk.partition("=")
            if equals and re.fullmatch(r"\s*[A-Za-z_][\w -]*\s*", key):
                named[key.strip().lower()] = value.strip()
            else:
                positional.append(chunk.strip())
        yield {"name": name, "name_key": name.casefold(), "positional": positional, "named": named,
               "span": [i, stop], "raw": text[i:stop], "closed": text[stop - 2:stop] == "}}",
               "year_bearing": bool(YEAR.search(text[i:stop]))}
        yield from templates(text, body_start, body_end)
        i = stop


def link_spans(value: str) -> list[tuple[int, int]]:
    spans, i = [], 0
    while i < len(value) - 1:
        if value[i:i + 2] == "[[":
            stop = closing(value, i, "[[", "]]")
            spans.append((i, stop))
            i = stop
        else:
            i += 1
    return spans


def list_items(value: str) -> list[dict[str, Any]]:
    """Every bullet line with its depth, its parent item and the date text written outside its links."""

    items, parent = [], None
    for number, match in enumerate(re.finditer(r"^(\*+)\s*(.+?)\s*$", value, re.M), start=1):
        depth = len(match.group(1))
        body = match.group(2)
        links = link_spans(body)
        outside = "".join(ch for index, ch in enumerate(body) if not any(a <= index < b for a, b in links))
        years_outside = YEAR.findall(outside)
        balanced = [m.group(0) for m in re.finditer(r"\(([^()]*)\)", body) if YEAR.search(m.group(1))]
        items.append({"item": number, "depth": depth, "parent_item": parent if depth > 1 else None,
                      "body": body, "years_outside_links": years_outside,
                      "dated_parenthetical_balanced": balanced,
                      "date_text_without_balanced_parentheses": bool(years_outside) and not balanced,
                      "opening_parentheses": body.count("("), "closing_parentheses": body.count(")")})
        if depth == 1:
            parent = number
    return items


def raw_index() -> dict[tuple[str, str], Path]:
    index: dict[tuple[str, str], Path] = {}
    for path in sorted(RAW_WIKIMEDIA.iterdir()):
        try:
            payload = json.loads(path.read_bytes())
        except (OSError, ValueError):
            continue
        for page in ((payload.get("query") or {}).get("pages") or {}).values():
            revisions = page.get("revisions") or []
            if revisions:
                index.setdefault((str(page.get("pageid")), str(revisions[0].get("revid"))), path)
    return index


def census(out: Path) -> dict[str, Any]:
    pages = [json.loads(line) for line in CAREER_PAGES.read_text(encoding="utf-8").splitlines() if line.strip()]
    index = raw_index()
    counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    missing, rows = [], 0
    template_rows = out / "CAREER_TEMPLATE_OCCURRENCES.jsonl"
    item_rows = out / "CAREER_LIST_ITEMS.jsonl"
    with template_rows.open("x", encoding="utf-8", newline="\n") as t_out, \
            item_rows.open("x", encoding="utf-8", newline="\n") as i_out:
        for page in pages:
            key = (str(page.get("pageid")), str(page.get("wikimedia_revision")))
            path = index.get(key)
            if path is None:
                missing.append(list(key))
                continue
            raw = path.read_bytes()
            record = next(iter(json.loads(raw)["query"]["pages"].values()))
            text = record["revisions"][0]["slots"]["main"]["*"]
            digest = sha256_bytes(raw)
            for box, start, end in infoboxes(text):
                for name, value_start, value_end in params(text, start, end):
                    numbered = NUMBERED.match(name)
                    if not numbered and name not in LIST_FIELDS:
                        continue
                    field_kind = "list" if name in LIST_FIELDS else numbered.group(2).lower()
                    for occurrence in templates(text, value_start, value_end):
                        row = {"pageid": key[0], "revision": key[1], "infobox": box, "field": name,
                               "field_kind": field_kind, "raw_file": str(path), "raw_file_sha256": digest,
                               **occurrence}
                        t_out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                        rows += 1
                        if occurrence["year_bearing"]:
                            arity = len(occurrence["positional"])
                            counts["year_bearing_template_name_and_arity"][
                                f"{occurrence['name_key']}|{arity}"] += 1
                            counts["year_bearing_template_named_argument"][
                                f"{occurrence['name_key']}|{','.join(sorted(occurrence['named'])) or '-'}"] += 1
                            counts["year_bearing_template_by_field_kind"][
                                f"{occurrence['name_key']}|{field_kind}"] += 1
                            if arity >= 2:
                                counts["year_bearing_second_positional_shape"][
                                    f"{occurrence['name_key']}|"
                                    + re.sub(r"\d", "9", occurrence["positional"][1])] += 1
                        counts["template_name"][occurrence["name_key"]] += 1
                    if name in LIST_FIELDS:
                        for item in list_items(text[value_start:value_end]):
                            item_row = {"pageid": key[0], "revision": key[1], "field": name, **item,
                                        "raw_file": str(path), "raw_file_sha256": digest}
                            i_out.write(json.dumps(item_row, ensure_ascii=False, sort_keys=True) + "\n")
                            counts["list_item_depth"][str(item["depth"])] += 1
                            if item["depth"] > 1:
                                counts["nested_item_date_form"][
                                    "BALANCED_PARENTHESES" if item["dated_parenthetical_balanced"] else
                                    "DATE_WITHOUT_BALANCED_PARENTHESES" if item["years_outside_links"] else
                                    "NO_DATE_OF_ITS_OWN"] += 1
    summary = {
        "label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — IN_PROGRESS — career date-template census",
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "census_version": CENSUS_VERSION,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {"career_pages": str(CAREER_PAGES), "career_pages_sha256": sha256_bytes(CAREER_PAGES.read_bytes()),
                   "raw_directory": str(RAW_WIKIMEDIA), "raw_page_revisions_indexed": len(index)},
        "pages": len(pages), "pages_missing_raw": missing, "template_occurrences": rows,
        "template_rows_file": str(template_rows), "template_rows_sha256": sha256_bytes(template_rows.read_bytes()),
        "list_items_file": str(item_rows), "list_items_sha256": sha256_bytes(item_rows.read_bytes()),
        "counts": {name: dict(counter.most_common()) for name, counter in sorted(counts.items())},
        "independence": ("Brace and link matching, parameter and argument splitting and list-item reading are "
                         "implemented here. Neither the parser nor the Attempt 4 census (which shared the parser's "
                         "first-year shortcut) is imported, and no template is given a meaning."),
    }
    (out / "CAREER_TEMPLATE_CENSUS.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                                                     encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=False)
    summary = census(args.out)
    counts = summary["counts"]
    print(json.dumps({"pages": summary["pages"], "missing": len(summary["pages_missing_raw"]),
                      "template_occurrences": summary["template_occurrences"],
                      "year_bearing_forms": counts.get("year_bearing_template_name_and_arity", {}),
                      "nested_item_date_form": counts.get("nested_item_date_form", {})}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
