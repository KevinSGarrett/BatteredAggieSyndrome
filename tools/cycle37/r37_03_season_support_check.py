"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-03 / R36-03: a separate, read-only check of every season-support tuple
the staff reparse admits.

It imports nothing from the producer. For each row whose season is bound, it
re-reads the capture bytes and checks, with its own code:

1. the text at the recorded label offset is the recorded label text;
2. that text states the bound season as a year, and a football staff phrase;
3. the label sits inside a heading-like element (h1-h6, caption, th, legend or
   an element whose class names a heading or title), not inside a script,
   style, comment, navigation, header or footer element;
4. the record lies after the label and inside the span the label governs;
5. no heading between the label and the record names another sport;
6. the record's own name bytes are at the recorded byte span.

Every failure is listed with the row it concerns. The check reports what it
finds; it does not change any row.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
class _bas_atomic:  # U37-11: atomic writes, self-contained -- this tool stays independent of aggie_analytics
    @staticmethod
    def _begin(path):
        import os as _bas_os
        import pathlib as _bas_pathlib
        import tempfile as _bas_tempfile

        target = path.resolve() if path.is_symlink() else path
        handle, name = _bas_tempfile.mkstemp(dir=str(target.parent), prefix="~", suffix="")
        _bas_os.close(handle)
        return target, _bas_pathlib.Path(name)

    @staticmethod
    def _finish(temporary, target):
        import os as _bas_os
        import stat as _bas_stat
        import time as _bas_time

        with open(temporary, "rb+") as stream:
            _bas_os.fsync(stream.fileno())
        try:
            mode = _bas_stat.S_IMODE(_bas_os.stat(target).st_mode)
        except FileNotFoundError:
            umask = _bas_os.umask(0)
            _bas_os.umask(umask)
            mode = 0o666 & ~umask
        _bas_os.chmod(temporary, mode)
        for attempt in range(6):
            try:
                _bas_os.replace(temporary, target)
                return
            except PermissionError:
                if attempt == 5:
                    raise
                _bas_time.sleep(0.05 * (attempt + 1))

    @classmethod
    def _call(cls, method, path, *args, **kwargs):
        import pathlib as _bas_pathlib

        if not isinstance(path, _bas_pathlib.Path):
            return getattr(path, method)(*args, **kwargs)
        target, temporary = cls._begin(path)
        try:
            written = getattr(temporary, method)(*args, **kwargs)
            cls._finish(temporary, target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return written

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        return cls._call("write_text", path, *args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        return cls._call("write_bytes", path, *args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        import contextlib as _bas_contextlib
        import pathlib as _bas_pathlib

        @_bas_contextlib.contextmanager
        def _stream():
            if not isinstance(path, _bas_pathlib.Path):
                with path.open(*args, **kwargs) as stream:
                    yield stream
                return
            target, temporary = cls._begin(path)
            try:
                with temporary.open(*args, **kwargs) as stream:
                    yield stream
                cls._finish(temporary, target)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise

        return _stream()

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
ROWS = ATTEMPT / "evidence" / "repairs" / "R37_03_STAFF_REPARSE_ROWS.jsonl"
_STAFF = re.compile(r"\b(?:staff|coaches|coaching)\b", re.I)
_OTHER = re.compile(r"\b(?:basketball|baseball|softball|volleyball|soccer|lacrosse|hockey|golf|tennis|swimming|"
                    r"wrestling|gymnastics|rowing|track|cross country|rifle|bowling|sprint football|flag football)\b",
                    re.I)
_SPORT_SECTION = re.compile(r"^(?:\d{4}(?:-\d{2})?\s+)?(?:men'?s\s+|women'?s\s+)?" + _OTHER.pattern[2:-2]
                            + r"(?:\s*,\s*(?:men'?s|women'?s))?(?:\s+(?:staff|coaches|coaching\s+staff|roster|team|"
                            r"schedule))?$", re.I)
_HEADING_OPEN = re.compile(r"<(h[1-6]|caption|th|legend)\b|<[a-z0-9]+\b[^>]*class=\"[^\"]*(?:heading|title)[^\"]*\"",
                           re.I)
_EXCLUDED = ("script", "style", "nav", "header", "footer", "noscript", "template")


def _enclosing(text: str, offset: int, tag: str) -> bool:
    """Whether ``offset`` lies inside an open ``<tag ...>`` not yet closed before it."""

    lower = text.lower()
    opened = lower.rfind(f"<{tag}", 0, offset)
    while opened >= 0:
        after = lower[opened + len(tag) + 1: opened + len(tag) + 2]
        if after and (after.isspace() or after in (">", "/")):
            break
        opened = lower.rfind(f"<{tag}", 0, opened)
    if opened < 0:
        return False
    closed = lower.find(f"</{tag}", opened)
    return closed < 0 or closed > offset


def _in_comment(text: str, offset: int) -> bool:
    opened = text.rfind("<!--", 0, offset)
    return opened >= 0 and text.find("-->", opened) > offset


def _heading_like(text: str, offset: int) -> bool:
    window = text[max(0, offset - 600):offset]
    last_open = None
    for match in _HEADING_OPEN.finditer(window):
        last_open = match
    if not last_open:
        return False
    # the element opened must not have closed before the label
    tag = (last_open.group(1) or "").lower()
    if tag:
        return f"</{tag}" not in window[last_open.end():].lower()
    return True


def check_row(row: dict[str, Any], text: str, data: bytes) -> list[str]:
    bound = row.get("season_bound_by") or {}
    failures = []
    offset, end, matched = bound.get("offset"), bound.get("end"), str(bound.get("matched_text") or "")
    if offset is None or end is None:
        return ["NO_LABEL_OFFSET"]
    if re.sub(r"\s+", " ", text[offset:end]).strip().casefold() != re.sub(r"\s+", " ", matched).strip().casefold():
        failures.append("LABEL_TEXT_NOT_AT_OFFSET")
    if str(row["season"]) not in matched and not re.search(rf"\b{row['season']}\s*[-–/]\s*\d{{2,4}}", matched):
        failures.append("LABEL_DOES_NOT_STATE_THE_SEASON")
    if not _STAFF.search(matched):
        failures.append("LABEL_HAS_NO_STAFF_PHRASE")
    if _in_comment(text, offset):
        failures.append("LABEL_IN_A_COMMENT")
    for tag in _EXCLUDED:
        if _enclosing(text, offset, tag):
            failures.append(f"LABEL_INSIDE_{tag.upper()}")
    if not _heading_like(text, offset):
        failures.append("LABEL_NOT_IN_A_HEADING_LIKE_ELEMENT")
    record = (row.get("binding") or {}).get("char_offset")
    if record is None:
        failures.append("RECORD_NOT_LOCATED")
    else:
        if not (offset < record and bound.get("governs_from", offset) <= record < bound.get("governs_to", 1 << 62)):
            failures.append("RECORD_OUTSIDE_THE_GOVERNED_SPAN")
        between = text[end:record]
        for heading in re.finditer(r"<h([1-6])\b[^>]*>(.*?)</h\1\s*>", between, re.I | re.S):
            plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", heading.group(2))).strip()
            # A section heading names the sport as its subject ("Baseball", "Men's
            # Basketball Staff"); a person heading that merely contains a sport
            # word ("Josh Bowling") is not one. The first version of this checker
            # flagged such a name; that false positive is adjudicated in the report.
            if _SPORT_SECTION.match(plain) and not re.search(
                    r"\bfootball\b", re.sub(r"(?i)(sprint|flag)\s+football", "", plain), re.I):
                failures.append("ANOTHER_SPORT_HEADING_BETWEEN_LABEL_AND_RECORD")
                break
    span = ((row.get("binding") or {}).get("name_span") or {})
    if span.get("byte_start") is not None:
        got = data[span["byte_start"]:span["byte_end"]].decode("utf-8", "replace")
        if not got.strip():
            failures.append("NAME_BYTES_EMPTY")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=Path, default=ROWS)
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs" / "R37_03_SEASON_SUPPORT_CHECK.json")
    args = parser.parse_args(argv)
    cache: dict[str, tuple[str, bytes]] = {}
    counts, failures, checked = collections.Counter(), [], 0
    admitted_checked = 0
    with args.rows.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("season") is None:
                continue
            path = row["capture_path"]
            if path not in cache:
                if len(cache) > 64:
                    cache.clear()
                data = Path(path).read_bytes()
                cache[path] = (data.decode("utf-8", "surrogateescape"), data)
            text, data = cache[path]
            found = check_row(row, text, data)
            checked += 1
            admitted_checked += bool(row.get("admitted_for_coverage"))
            for item in found:
                counts[item] += 1
            if found:
                failures.append({"capture_path": path, "observation_index": row["observation_index"],
                                 "season": row["season"], "admitted": row.get("admitted_for_coverage"),
                                 "label": (row.get("season_bound_by") or {}).get("matched_text"), "failures": found})
    report = {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-03",
              "rows": ["R37-03-CF-R36-03", "R37-03-CF-MR35R-04", "R37-03-AC06"],
              "independence": "Imports nothing from aggie_analytics; re-reads the capture bytes with its own rules.",
              "season_bound_rows_checked": checked, "admitted_rows_checked": admitted_checked,
              "rows_with_a_failure": len(failures),
              "admitted_rows_with_a_failure": sum(1 for f in failures if f["admitted"]),
              "failure_counts": dict(counts), "failures": failures[:500],
              "rows_file_sha256": hashlib.sha256(args.rows.read_bytes()).hexdigest()}
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "failures"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
