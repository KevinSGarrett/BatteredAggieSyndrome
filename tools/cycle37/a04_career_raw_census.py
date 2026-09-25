r"""Cycle #37 — Attempt #4 — independent census of raw career-infobox syntax (TP37-A04-06, R37A04-06-A).

    a04_career_raw_census.py --out <new directory>

MF37A03-04/05 were found by reading raw bytes, not delivered rows: an unknown role code (``Rutgers (DFO)``)
became an employer qualifier and then a head-coach default, and ``2009–?`` became a closed single year. The
343 role-code and 312 question-mark candidates were screens over the *delivered* database; they cannot show
what the delivered rows never carried. This census reads every cached revision the career population was built
from and enumerates, without importing the producer's parser or its vocabularies:

* every numbered ``*_years``/``*_team`` parameter and every other infobox parameter whose name looks like a
  career field (so a naming variant the producer's pattern misses is visible, not silently absent);
* every top-level parenthetical in a team value, outside the employer link, as raw text and as plain text --
  including ones whose plain text is empty because it is a template;
* every years value's *shape* (digits as 9, dashes as ``-``), so each uncertain-date syntax is a counted class.

Its brace matching, parameter splitting and parenthetical extraction are written here, not imported, so a
defect in the producer's parser cannot hide the rows it mishandles. Nothing is resolved or interpreted; the
census states what the revisions say and where, and the successor builder reconciles every row it lists.
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
ATTEMPT_NUMBER = 4
CENSUS_VERSION = "BAS-C37A04-CAREER-RAW-CENSUS-v1"
CYCLE30 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
RAW_WIKIMEDIA = CYCLE30 / "raw" / "wikimedia"
CAREER_PAGES = CYCLE30 / "outputs" / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl"

#: Career fields as the numbered infobox parameters name them.
#: The spelled-out variants (``coaching_years1``) are career fields too; the census names them as written.
NUMBERED = re.compile(r"^(coaching|coach|playing|player|administrating|admin|executive)_?(years|team)(\d+)$", re.I)
#: Any other parameter a career could hide in (a variant the numbered pattern would miss).
CAREER_LIKE = re.compile(r"(years|team|coach|position|past|career|stint)", re.I)
LIST_FIELDS = {"pastcoaching", "pastteams", "pastexecutive", "pastexecutives", "pastadmin"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def closing_braces(text: str, start: int) -> int:
    """Index after the ``}}`` that closes the template beginning at ``start`` (independent brace counting)."""

    depth, i = 0, start
    while i < len(text) - 1:
        two = text[i:i + 2]
        if two == "{{":
            depth, i = depth + 1, i + 2
        elif two == "}}":
            depth, i = depth - 1, i + 2
            if depth == 0:
                return i
        else:
            i += 1
    return len(text)


def infobox_bodies(text: str) -> Iterator[tuple[str, int, int]]:
    for match in re.finditer(r"\{\{\s*Infobox\s+([^|\n}]+)", text, re.I):
        yield match.group(1).strip(), match.end(), closing_braces(text, match.start()) - 2


def top_level_params(text: str, start: int, end: int) -> list[tuple[str, str, int]]:
    """(name, value, value offset) for each ``|name=value`` not nested in a link or template."""

    out, cut, links, templates, i = [], None, 0, 0, start
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
        if text[i] == "|" and not links and not templates:
            if cut is not None:
                out.append((cut, i))
            cut = i + 1
        i += 1
    if cut is not None:
        out.append((cut, end))
    params = []
    for a, b in out:
        chunk = text[a:b]
        if "=" not in chunk:
            continue
        name, _, value = chunk.partition("=")
        offset = a + len(name) + 1 + (len(value) - len(value.lstrip()))
        params.append((name.strip(), value.strip(), offset))
    return params


def strip_markup(value: str) -> str:
    """Plain text: refs and comments removed, links to their display, templates removed, whitespace folded."""

    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    value = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", value, flags=re.S | re.I)
    value = re.sub(r"\[\[([^\]|]+)\|([^\]]*)\]\]", r"\2", value)
    value = re.sub(r"\[\[([^\]]+)\]\]", r"\1", value)
    # A circa template displays "c. <year>" and a season template its year; deleting them as markup would hide
    # an approximate or a stated year from the shape census.
    value = re.sub(r"\{\{\s*(?:circa|c\.|ca\.?)\s*(?:\|([^{}|]*))?[^{}]*\}\}",
                   lambda m: re.sub(r"(\d{4})", r"c. \1", m.group(1) or "") or "c.", value, flags=re.I)
    # A display template shows its first argument ("{{abbr|OC|Offensive coordinator}}" displays "OC").
    value = re.sub(r"\{\{\s*(?:abbr|abbrlink|tooltip|tip|hover title|nowrap)\s*\|([^{}|]*)(?:\|[^{}]*)?\}\}", r"\1",
                   value, flags=re.I)
    value = re.sub(r"\{\{\s*[A-Za-z][^|{}]*\|\s*(\d{4})\s*(?:\|[^{}]*)?\}\}", r"\1", value)
    previous = None
    while previous != value:
        previous = value
        value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"'{2,}", "", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parentheticals(team: str) -> list[dict[str, Any]]:
    """Top-level ``(...)`` groups of a team value that lie outside every ``[[...]]`` link."""

    clean = re.sub(r"<!--.*?-->", "", team, flags=re.S)
    clean = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", clean, flags=re.S | re.I)
    links = [(m.start(), m.end()) for m in re.finditer(r"\[\[.*?\]\]", clean, re.S)]
    groups, depth, begin = [], 0, None
    for i, ch in enumerate(clean):
        if ch == "(":
            if depth == 0:
                begin = i
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0 and begin is not None:
                if not any(a < begin < b for a, b in links):
                    inner = clean[begin + 1:i]
                    groups.append({"raw": inner, "plain": strip_markup(inner),
                                   "template_only": bool(inner.strip()) and not strip_markup(inner)})
                begin = None
    return groups


def years_shape(value: str) -> str:
    text = strip_markup(value)
    text = re.sub(r"\d", "9", text)
    text = re.sub(r"[‐‑‒–—−]", "-", text)
    return re.sub(r"\s+", " ", text).strip()


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
    missing: list[list[str]] = []
    rows_path = out / "CAREER_RAW_CENSUS_ROWS.jsonl"
    total_rows = 0
    with rows_path.open("x", encoding="utf-8", newline="\n") as rows_out:
        for page in pages:
            key = (str(page.get("pageid")), str(page.get("wikimedia_revision")))
            path = index.get(key)
            if path is None:
                missing.append(list(key))
                continue
            raw = path.read_bytes()
            record = next(iter(json.loads(raw)["query"]["pages"].values()))
            text = record["revisions"][0]["slots"]["main"]["*"]
            for template, start, end in infobox_bodies(text):
                counts["infobox_template"][template.lower()] += 1
                pairs: dict[tuple[str, int], dict[str, Any]] = {}
                for name, value, offset in top_level_params(text, start, end):
                    lowered = name.lower()
                    match = NUMBERED.match(lowered)
                    if match:
                        family, kind, number = match.group(1), match.group(2), int(match.group(3))
                        slot = pairs.setdefault((family, number), {})
                        slot.setdefault(kind, {"value": value, "offset": offset, "name": name})
                    elif lowered in LIST_FIELDS:
                        counts["list_field"][lowered] += 1
                        for item in re.finditer(r"^\*+\s*(.+?)\s*$", value, re.M):
                            for group in parentheticals(item.group(1)):
                                counts["list_item_parenthetical_plain"][group["plain"]] += 1
                    elif CAREER_LIKE.search(lowered):
                        counts["other_career_like_parameter"][re.sub(r"\d+", "N", lowered)] += 1
                for (family, number), slot in sorted(pairs.items()):
                    years = slot.get("years", {}).get("value")
                    team = slot.get("team", {}).get("value")
                    groups = parentheticals(team) if team else []
                    row = {"pageid": key[0], "revision": key[1], "infobox": template, "family": family,
                           "index": number, "years_raw": years, "years_offset": slot.get("years", {}).get("offset"),
                           "team_raw": team, "team_offset": slot.get("team", {}).get("offset"),
                           "years_shape": years_shape(years) if years is not None else None,
                           "parentheticals": groups, "raw_file": str(path), "raw_file_sha256": sha256_bytes(raw)}
                    rows_out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                    total_rows += 1
                    counts["numbered_row_family"][family] += 1
                    if years is not None:
                        counts["years_shape"][row["years_shape"]] += 1
                        if "?" in years:
                            counts["years_with_question_mark_shape"][row["years_shape"]] += 1
                    for group in groups:
                        counts["team_parenthetical_plain"][group["plain"]] += 1
                        if group["template_only"]:
                            counts["team_parenthetical_template_only_raw"][group["raw"]] += 1
                    counts["team_parenthetical_count_per_row"][len(groups)] += 1
    summary = {
        "label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — IN_PROGRESS — raw career-infobox census",
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "census_version": CENSUS_VERSION,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {"career_pages": str(CAREER_PAGES), "career_pages_sha256": sha256_bytes(CAREER_PAGES.read_bytes()),
                   "raw_directory": str(RAW_WIKIMEDIA), "raw_page_revisions_indexed": len(index)},
        "pages": len(pages), "pages_missing_raw": missing, "numbered_rows": total_rows,
        "rows_file": str(rows_path), "rows_sha256": sha256_bytes(rows_path.read_bytes()),
        "counts": {name: dict(counter.most_common()) for name, counter in sorted(counts.items())},
        "independence": ("Brace matching, parameter splitting, markup stripping and parenthetical extraction are "
                         "implemented in this file; aggie_analytics.cycle37.career_infobox and the reparse tool are "
                         "not imported."),
        "not_claimed": "A syntax census states what the revisions contain; it assigns no meaning to any code.",
    }
    (out / "CAREER_RAW_CENSUS.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                                                encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=False)
    summary = census(args.out)
    print(json.dumps({k: summary[k] for k in ("pages", "numbered_rows", "rows_sha256")}
                     | {"missing": len(summary["pages_missing_raw"]),
                        "distinct_parentheticals": len(summary["counts"].get("team_parenthetical_plain", {})),
                        "distinct_year_shapes": len(summary["counts"].get("years_shape", {}))}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
